"""Optional local Gmail OAuth client. Tokens stay in an OS credential vault.

No passwords, browser cookies, inbox access, alias impersonation or send retries.
"""
import hashlib
import json
import re
from contextlib import contextmanager

from core.workflow import WorkflowError

SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email',
          'https://www.googleapis.com/auth/gmail.send']
USERINFO = 'https://openidconnect.googleapis.com/v1/userinfo'
SEND = 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send'


class GmailClient:
    def __init__(self, work, client_file, connection='default'):
        if not re.fullmatch(r'[a-z0-9_-]{1,40}', connection):
            raise WorkflowError('blocked', 'Invalid connection label')
        self.work = work
        self.client_file = work.inside(client_file)
        self.connection = connection
        self.service = 'vietnam-career-kit:' + hashlib.sha256(str(work.data_dir).encode()).hexdigest()

    def _vault(self):
        import keyring
        backend = keyring.get_keyring()
        if type(backend).__module__ not in {
                'keyring.backends.Windows', 'keyring.backends.macOS',
                'keyring.backends.SecretService', 'keyring.backends.kwallet'} or backend.priority <= 0:
            raise WorkflowError('manual_required', 'A supported OS credential vault is required; no plaintext fallback')
        return keyring

    def _store(self, credentials):
        self._vault().set_password(self.service, self.connection, credentials.to_json())

    def login(self):
        from google_auth_oauthlib.flow import InstalledAppFlow
        # Reject a web-client file and endpoint substitutions before opening any browser.
        config = self.work.private_json(self.client_file)
        installed = config.get('installed', {})
        if (installed.get('auth_uri') != 'https://accounts.google.com/o/oauth2/auth' or
                installed.get('token_uri') != 'https://oauth2.googleapis.com/token' or
                not installed.get('client_id', '').endswith('.apps.googleusercontent.com')):
            raise WorkflowError('blocked', 'Use an official Google Desktop OAuth client JSON')
        self._vault()  # Fail before requesting a grant when secure persistence is unavailable.
        flow = InstalledAppFlow.from_client_config(config, SCOPES, autogenerate_code_verifier=True)
        credentials = flow.run_local_server(host='127.0.0.1', port=0, open_browser=True,
            timeout_seconds=180, access_type='offline', prompt='consent select_account',
            authorization_prompt_message='Complete Google sign-in in your browser.',
            success_message='Account connected. You can close this sign-in page.')
        self._store(credentials)
        return self.profile()

    def _session(self):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import AuthorizedSession, Request
        import requests
        saved = self._vault().get_password(self.service, self.connection)
        if not saved:
            raise WorkflowError('needs_input', 'Connect this Gmail account first')
        info = json.loads(saved)
        if info.get('token_uri') != 'https://oauth2.googleapis.com/token':
            raise WorkflowError('blocked', 'Unexpected OAuth token endpoint')
        credentials = Credentials.from_authorized_user_info(info, SCOPES)
        if not credentials.valid:
            with requests.Session() as session:
                session.trust_env = False
                credentials.refresh(Request(session=session))
            self._store(credentials)
        # Explicitly suppress POST replay on authentication failure.
        session = AuthorizedSession(credentials, max_refresh_attempts=0)
        session.trust_env = False
        return session

    def profile(self):
        with self._session() as session:
            return self._identity(session)

    def _identity(self, session):
        response = session.get(USERINFO, timeout=30, allow_redirects=False)
        if response.status_code != 200:
            raise WorkflowError('needs_input', 'Google account verification failed; reconnect')
        value = response.json()
        if not value.get('sub') or value.get('email_verified') is not True or not value.get('email'):
            raise WorkflowError('blocked', 'A verified Google mailbox identity is required')
        return {'id': value['sub'], 'email': value['email'], 'connection': self.connection}

    @contextmanager
    def prepare(self, expected_account):
        with self._session() as session:
            actual = self._identity(session)
            if (actual['id'] != expected_account['id'] or
                    actual['email'].casefold() != expected_account['email'].casefold()):
                raise WorkflowError('blocked', 'Gmail account changed before sending')
            yield lambda raw: self._send(session, raw)

    @staticmethod
    def _send(session, raw):
        response = session.post(SEND, json={'raw': raw}, timeout=30, allow_redirects=False)
        if response.status_code != 200:
            # Never include provider error bodies, tokens or the private MIME in errors.
            raise WorkflowError('submission_unknown', 'Gmail did not acknowledge this send; do not retry')
        return response.json()

    def disconnect(self):
        vault = self._vault()
        if vault.get_password(self.service, self.connection):
            vault.delete_password(self.service, self.connection)
        return {'connection': self.connection, 'local_token_removed': True,
                'provider_grant_revoked': False}
