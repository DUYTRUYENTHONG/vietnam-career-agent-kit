"""Local CV-first intake packet; never launches models or application workers."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile

from .contracts import Outcome
from .workflow import WorkflowError

DEFAULT_TARGET = 100


def start_campaign(work, cv: str | Path, *, target: int = DEFAULT_TARGET,
                   language: str = 'en') -> Outcome:
    """Create one private, resumable packet without importing or approving facts."""
    if type(target) is not int or not 1 <= target <= 10_000:
        raise ValueError('target must be a finite integer between 1 and 10000')
    if language not in {'en', 'vi'}:
        raise ValueError('language must be en or vi')
    source = Path(cv).expanduser().resolve(strict=True)
    if source.suffix.lower() not in {'.pdf', '.docx', '.txt', '.md'}:
        raise ValueError('Attach a PDF, DOCX, TXT or Markdown CV; export legacy formats first')
    if not source.is_file() or not 0 < source.stat().st_size <= 10_000_000:
        raise ValueError('CV must be a nonempty file of at most 10 MB')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    folder = work.inside('starter')
    config = {
        'schema_version': '1.0', 'language': language, 'mode': 'PREPARE',
        'cv': {'path': str(source), 'sha256': digest, 'imported_as_evidence': False,
               'extraction': 'Use the host extraction tool, verify against the original, then import UTF-8 evidence.'},
        'goal': {'target_confirmed': target, 'qualifying_fit': ['Strong fit', 'Plausible fit'],
                 'counting': 'Unique new observed confirmations only; no prior, draft, failed, unknown or stretch inflation.',
                 'persistent_host_goal_created': False, 'background_work_started': False},
        'required_information': {key: None for key in (
            'roles_and_seniority', 'cities_and_remote_eligibility', 'employment_types_and_exclusions',
            'start_date_notice_and_work_authorization', 'salary_or_negotiable_with_basis',
            'current_cv_contacts_and_application_mailbox', 'prior_applications_or_none')},
        'execution_authorized': False,
    }
    if folder.exists():
        old = json.loads((folder / 'intake.json').read_text(encoding='utf8'))
        if (old['cv']['path'], old['cv']['sha256'], old['goal']['target_confirmed'], old['language']) != (
                str(source), digest, target, language):
            raise WorkflowError('needs_input', 'Existing starter differs: resume it; review CV/goal changes explicitly without overwriting it')
        if not (folder / 'GOAL.md').is_file() or not work.db_path.is_file():
            raise WorkflowError('needs_input', 'Starter is incomplete: inspect and recover the existing workspace; do not reset it')
        return Outcome('ok', {'reused': True, 'starter': str(folder),
                              'target_confirmed': target, 'execution_authorized': False}, [])
    work.init(language)
    goal = f'''# Private campaign goal

Target: {target} new, best-fit, confirmed job applications in the user's confirmed scope.
This note is an intake checkpoint, not a running host goal or execution permission.

Give your tool-enabled agent the attached CV, this packet and the repository's
prompts/COMMUNITY_START.md. Ask only for missing material information in intake.json;
reuse confirmed CV facts and answers. Use one canonical workflow.sqlite3 here.
Extract PDF/DOCX through a supported host tool and verify the text; this command
does not extract, import, confirm, tailor or send the CV. TXT/Markdown evidence can
use import-cv after source checking. Never manufacture confirmations.

On your explicit job-seeker request, create/reuse a supported persistent host goal;
otherwise maintain this private note. Rank complete current JDs by Strong fit and
Plausible fit. Do not lower the standard to fill the target. A stretch requires
an explicit scope change and remains separate from the default best-fit count.

Tailor supported evidence, render and inspect documents, deduplicate, and use
permitted tools with current finite authority. The target is not a cap grant or
permission to share CVs with arbitrary recipients. Host confirmations still apply.
Count only unique observed confirmations; keep interviews, rejections and offers
separate. Record attempts before submission; uncertain outcomes never auto-retry.
Close completed owned tabs after saving receipts. Keep working through authorized
batches; stop only at the target, actual limits or required user steps. Save a
checkpoint rather than inventing missing answers or pretending to run in background.

Completion: qualifying receipts reconciled and the private tracker exported.
An application success means confirmed submission, not an interview or job offer.
'''
    # Publish both files together; never overwrite an existing user-edited packet.
    with tempfile.TemporaryDirectory(prefix='.starter-', dir=work.data_dir) as temporary:
        staged = Path(temporary) / 'packet'
        staged.mkdir()
        (staged / 'intake.json').write_text(json.dumps(config, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
        (staged / 'GOAL.md').write_text(goal, encoding='utf8')
        os.rename(staged, folder)
    return Outcome('ok', {'reused': False, 'starter': str(folder), 'target_confirmed': target,
                          'cv_extracted': False, 'execution_authorized': False},
                   ['Give the agent the starter packet and your CV; complete missing information before dependent actions.'])
