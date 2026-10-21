"""Read-only local capability diagnosis, not a native integration certificate."""
import platform
import shutil
import sqlite3
import sys
from importlib.metadata import PackageNotFoundError, version

from .contracts import Outcome


def diagnose(runtime: str = 'generic') -> Outcome:
    document_dependencies={}
    for package in ['python-docx','lxml','typing_extensions','pypdf','pypdfium2','Pillow']:
        try:document_dependencies[package]=version(package)
        except PackageNotFoundError:document_dependencies[package]=None
    recorded_matrix=(platform.system() in {'Windows','Linux'} and sys.version_info[:2] in {(3,11),(3,12)})
    labels={'generic':'Verified' if recorded_matrix else 'Experimental',
            'codex':'Experimental','claude':'Instruction-only','grok':'Unsupported'}
    return Outcome('ok',{'runtime':runtime,'native_compatibility':labels[runtime],
        'interface':'local Python CLI; agent can read shared instructions',
        'python_version':platform.python_version(),'operating_system':platform.system(),
        'sqlite_version':sqlite3.sqlite_version,'python_executable':sys.executable,
        'agent_executable_present':bool(shutil.which({'codex':'codex','claude':'claude'}.get(runtime,'__not_an_agent__'))),
        'skill_discovery':'Shared project skills; native loading must be verified in the named host',
        'hooks_trusted_or_tested':False,'browser_execution':False,'network_execution':False,
        'execution_engine':{'available':True,'interface':'Host-mediated request/receipt CLI; no browser acquired','standalone_browser_worker':False},
        'model_api_required':False,'document_formats':['UTF-8 TXT CV import','Markdown CV draft'],
        'optional_document_pipeline':{'formats':['DOCX','PDF','PNG previews'],
            'dependency_versions':document_dependencies,'libreoffice_on_path':bool(shutil.which('soffice')),
            'configuration':'Requires optional locked dependencies, trusted LibreOffice executable and DejaVu Sans fonts. No automatic install; every page needs review.'},
        'limitations':['Executable presence is not account access, native skill execution or hook enforcement.',
            'Generic verification covers the recorded OS/Python test matrix only; this command does not rerun integration tests.',
            'No browser/paid model call is made by this diagnostic.',
            'Grok product/runtime is not identified; use generic instructions without native capability claims.']},[])
