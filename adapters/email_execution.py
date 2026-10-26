"""Gmail API delivery using the existing manifest, attempt and tracker tables.

OAuth grants mailbox access, never application authority. An accepted API send
is evidence of sending, not employer delivery. No retry/reconciliation write is
offered by this adapter after an uncertain result.
"""
import base64
from email.message import EmailMessage
import hashlib
import json
import re
import uuid

from core.contracts import Outcome
from core.ledger import canonical_hash, utc_now
from core.manifests import now_utc, timestamp
from core.workflow import WorkflowError

BRIDGE = 'gmail-api-local'
FIELDS = {'sender', 'to', 'subject', 'body'}


def mailbox(value):
    if not isinstance(value, str) or len(value) > 254 or not re.fullmatch(
            r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?', value):
        raise WorkflowError('blocked', 'Use one explicit mailbox, without display names or headers')
    return value


def message(entry, content):
    answers = entry['answers']
    if set(answers) != FIELDS or entry['consents']:
        raise WorkflowError('blocked', 'Email requires exactly sender/to/subject/body and no consent acceptance')
    values = {key: answers[key]['value'] for key in FIELDS}
    mailbox(values['sender']); mailbox(values['to'])
    subject, body = values['subject'], values['body']
    if (not isinstance(subject, str) or not 1 <= len(subject) <= 250 or
            any(ord(c) < 32 or ord(c) == 127 for c in subject) or
            not isinstance(body, str) or not body.strip() or len(body.encode('utf8')) > 65536):
        raise WorkflowError('blocked', 'Invalid subject or message body')
    if (entry['format'] != 'pdf' or not content.startswith(b'%PDF-') or
            len(content) > 20 * 1024 * 1024 or hashlib.sha256(content).hexdigest() != entry['document_sha256']):
        raise WorkflowError('blocked', 'Email attachment must be the exact reviewed PDF, at most 20 MiB')
    mail = EmailMessage()
    mail['From'] = values['sender']; mail['To'] = values['to']; mail['Subject'] = subject
    mail.set_content(body)
    # Only the basename is transmitted. No arbitrary file reads or extra attachments.
    from pathlib import PurePath
    mail.add_attachment(content, maintype='application', subtype='pdf',
                        filename=PurePath(entry['document']['path']).name)
    return values, base64.urlsafe_b64encode(mail.as_bytes()).decode('ascii')


class EmailExecution:
    def __init__(self, work, client):
        self.work, self.client = work, client

    def start(self, fingerprint):
        self.work.check_manifest(fingerprint)
        manifest = self.work.current_manifest(fingerprint)
        if (manifest['mode'] != 'APPROVED_BATCH' or
                manifest.get('execution', {}).get('bridge_id') != BRIDGE):
            raise WorkflowError('blocked', 'An approved Gmail-specific execution manifest is required')
        account = self.client.profile()
        for entry in manifest['entries']:
            path = self.work.inside(entry['document']['path'])
            values, _ = message(entry, path.read_bytes())
            if values['sender'].casefold() != account['email'].casefold():
                raise WorkflowError('blocked', 'Approved sender differs from the authenticated Gmail account')
        return self.work.start_execution(fingerprint, BRIDGE, manifest['execution']['runtime_minutes'],
            _flow_factory=lambda db, m, flow: {**flow, 'transport': 'email', 'step': 'email_send',
                                               'account_id': account['id']})

    def send_next(self, run_id):
        # All reads, OAuth refresh and MIME validation precede the final claim.
        account = self.client.profile()
        with self.work._db() as db:
            run, flow = self.work._run(db, run_id)
        if flow.get('transport') != 'email' or flow.get('bridge_id') != BRIDGE:
            raise WorkflowError('blocked', 'Not a Gmail execution run')
        if run['state'] != 'active':
            return Outcome('submission_unknown' if run['state'] in {'submission_unknown', 'sending'} else 'ok',
                           {'run_id': run_id, 'state': run['state'], 'sent_again': False}, [])
        manifest = self.work.current_manifest(run['fingerprint'])
        entry = manifest['entries'][flow['entry_index']]
        frozen = self.work._frozen_document(entry)
        values, raw = message(entry, self.work.inside(frozen['path']).read_bytes())
        if account['id'] != flow['account_id'] or values['sender'].casefold() != account['email'].casefold():
            raise WorkflowError('blocked', 'Connected account changed; no send')
        intent = {k: entry[k] for k in ('job_id','destination','document_sha256','answers_sha256','consents_sha256')}
        intent.update(schema_version='1.0', action='submit')
        # Verify one live session before claiming. The bound sender cannot reload
        # a switched credential or fail a new identity lookup after the claim.
        with self.client.prepare(account) as sender:
            return self._deliver(run_id, run, flow, manifest, entry, frozen, values, raw, intent, account, sender)

    def _deliver(self, run_id, run, flow, manifest, entry, frozen, values, raw, intent, account, sender):
        with self.work._db() as db:
            db.execute('BEGIN IMMEDIATE')
            run, current = self.work._run(db, run_id)
            if run['state'] != 'active' or current != flow:
                raise WorkflowError('blocked', 'Concurrent or stale Gmail operation')
            self.work.check_manifest(run['fingerprint'], intent)
            if now_utc() >= timestamp(run['deadline_utc'], 'runtime deadline'):
                raise WorkflowError('blocked', 'Gmail run expired')
            count = db.execute('SELECT count(*) FROM execution_attempts WHERE fingerprint=?',
                               (run['fingerprint'],)).fetchone()[0]
            if count >= manifest['submission_limit'] or db.execute(
                    'SELECT 1 FROM execution_attempts WHERE job_id=?', (entry['job_id'],)).fetchone():
                raise WorkflowError('blocked', 'Application cap reached or vacancy already attempted; never resend')
            snapshot = {'manifest_fingerprint': run['fingerprint'], 'entry': entry,
                        'binding_id': BRIDGE + ':' + account['id'], 'actor': self.work.actor,
                        'document': frozen, 'fit_classification': self.work.current_draft(entry['job_id'])['classification']}
            attempt = uuid.uuid4().hex
            db.execute('INSERT INTO execution_attempts VALUES(?,?,?,?,?,?,?)',
                (attempt, run_id, entry['job_id'], run['fingerprint'], json.dumps(snapshot, ensure_ascii=False),
                 canonical_hash(snapshot), utc_now()))
            self.work._job_state(db, entry['job_id'], 'submission_uncertain')
            flow['attempt_id'] = attempt
            self.work._save(db, run, flow, 'sending')
            self.work._event(db, 'email_send_claimed', attempt, 'Gmail send; no automatic retry')
            db.commit()
        # The durable claim above survives process termination, timeout and lost responses.
        try:
            response = sender(raw)
            if (not isinstance(response, dict) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', response.get('id', '')) or
                    not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', response.get('threadId', ''))):
                raise ValueError('Missing provider acknowledgement')
        except Exception:
            with self.work._db() as db:
                db.execute('BEGIN IMMEDIATE')
                self.work._save(db, run, flow, 'submission_unknown')
                self.work._event(db, 'email_send_uncertain', attempt, 'Verify read-only; never retry')
                db.commit()
            return Outcome('submission_unknown', {'run_id': run_id, 'attempt_id': attempt,
                           'state': 'submission_unknown'}, ['Send may have occurred; no automatic retry.'])
        receipt = {'provider': 'gmail', 'message_id': response['id'], 'thread_id': response['threadId'],
                   'account_id': account['id'], 'sender': values['sender'], 'to': values['to'],
                   'evidence_kind': 'observed_gmail_api_send', 'employer_delivery_verified': False,
                   'recorded_utc': utc_now()}
        with self.work._db() as db:
            db.execute('BEGIN IMMEDIATE')
            snapshot.update(evidence=receipt, evidence_kind=receipt['evidence_kind'], recorded_utc=utc_now())
            db.execute('INSERT INTO execution_submissions VALUES(?,?,?,?,?,?)',
                (uuid.uuid4().hex, attempt, entry['job_id'], json.dumps(snapshot, ensure_ascii=False),
                 canonical_hash(snapshot), utc_now()))
            self.work._job_state(db, entry['job_id'], 'confirmed_submitted')
            flow.update(entry_index=flow['entry_index'] + 1, attempt_id=None)
            state = ('completed' if flow['entry_index'] >= len(manifest['entries']) or
                     count + 1 >= manifest['submission_limit'] else 'active')
            self.work._save(db, run, flow, state)
            self.work._event(db, 'email_send_confirmed', attempt, response['id'])
            db.commit()
        return Outcome('ok', {'run_id': run_id, 'job_id': entry['job_id'], 'state': state, 'receipt': receipt},
                       ['Gmail accepted this send; employer delivery and later bounces are unverified.'])
