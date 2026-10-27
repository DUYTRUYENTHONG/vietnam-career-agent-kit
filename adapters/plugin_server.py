"""Optional stdio MCP entry points. No HTTP listener, remote shell or approval tool."""
import threading

from core.workflow import WorkflowError


def make_server(work, kind, *, client=None):
    if kind == 'career':
        from .career_mcp import make_career_server
        return make_career_server(work)
    from mcp.server.fastmcp import FastMCP
    server = FastMCP('career-kit-' + kind, instructions=
        'Use one explicit private workspace. Login grants access, not application approval. '
        'Only existing reviewed finite manifests may execute. Never retry uncertain sends/submits. '
        'Stop on challenges/new terms. No approval-creation tool is provided.')
    lock = threading.Lock()
    bridges = {}

    def safe(function, *args):
        try:
            with lock:
                value = function(*args)
            return value.json() if hasattr(value, 'json') else value
        except WorkflowError as error:
            return {'outcome': error.outcome, 'data': {}, 'issues': [str(error)]}
        except Exception:
            return {'outcome': 'manual_required', 'data': {},
                    'issues': ['Operation failed; inspect private state. Never replay a possible mutation.']}

    @server.tool(annotations={'readOnlyHint': True, 'openWorldHint': False})
    def campaign_tracker() -> dict:
        """Read this workspace's canonical application tracker. No account action."""
        return safe(work.tracker)

    if kind == 'email':
        from .email_execution import EmailExecution
        engine = EmailExecution(work, client)

        @server.tool(annotations={'readOnlyHint': False, 'openWorldHint': True})
        def email_connect() -> dict:
            """Open Google OAuth in the user's browser; user selects/signs in. No password input tool."""
            return safe(client.login)

        @server.tool(annotations={'readOnlyHint': True, 'openWorldHint': True})
        def email_account() -> dict:
            """Verify the connected Google account; return stable ID and mailbox, never tokens."""
            return safe(client.profile)

        @server.tool(annotations={'readOnlyHint': False, 'openWorldHint': False})
        def email_disconnect() -> dict:
            """Remove the local vault credential; does not revoke the provider's grant."""
            return safe(client.disconnect)

        @server.tool(annotations={'readOnlyHint': False, 'openWorldHint': True})
        def email_start(manifest_fingerprint: str) -> dict:
            """Start only an existing approved gmail-api-local finite manifest. Does not approve or send."""
            return safe(engine.start, manifest_fingerprint)

        @server.tool(annotations={'readOnlyHint': False, 'destructiveHint': True, 'openWorldHint': True})
        def email_send_next(run_id: str) -> dict:
            """Send exactly the next approved CV/email once. Gmail acknowledgement proves sending, not delivery."""
            return safe(engine.send_next, run_id)

    elif kind == 'browser':
        from .local_browser import BRIDGE, LocalBrowserBridge, validate_plans
        from core.parallel_execution import run_parallel_with_bridge

        def start(fingerprint, forms_path, workers):
            forms = work.private_json(work.inside(forms_path))
            manifest = validate_plans(work, fingerprint, forms)
            result = work.start_parallel_execution(fingerprint, BRIDGE,
                manifest['execution']['runtime_minutes'], workers)
            run = result.data['run_id']
            bridges[run] = LocalBrowserBridge(work, run, forms)
            return result

        @server.tool(annotations={'readOnlyHint': False, 'openWorldHint': False})
        def browser_start(manifest_fingerprint: str, forms_path: str, workers: int = 3) -> dict:
            """Start an approved local-playwright batch with exact private form mappings; no browser opened yet."""
            return safe(start, manifest_fingerprint, forms_path, workers)

        @server.tool(annotations={'readOnlyHint': False, 'openWorldHint': True})
        def browser_open_login(run_id: str, job_id: int) -> dict:
            """Open the approved employer in an isolated visible window. User logs in directly if needed."""
            return safe(lambda: bridges[run_id].open(job_id))

        @server.tool(annotations={'readOnlyHint': False, 'destructiveHint': True, 'openWorldHint': True})
        def browser_execute(run_id: str) -> dict:
            """Execute an approved batch after all windows are opened/logged in. Stops challenges/new fields; no replay."""
            return safe(lambda: run_parallel_with_bridge(work, run_id, bridges[run_id]))

        @server.tool(annotations={'readOnlyHint': True, 'openWorldHint': False})
        def browser_status(run_id: str) -> dict:
            """Read canonical lane/pending-action status without browser mutation."""
            return safe(work.parallel_status, run_id)
    else:
        raise ValueError('Unknown plugin kind')
    return server
