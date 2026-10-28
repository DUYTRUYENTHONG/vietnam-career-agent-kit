"""Optional LCEL retrieval -> host draft -> current-evidence validation.

The explicitly supplied Python callback owns inference. No provider is chosen,
no remote model is created and no callback result grants execution authority.
"""
from copy import deepcopy
import os
from time import perf_counter

from core.career_drafting import writing_brief, check_draft
from core.contracts import ContractError, Outcome
from core.workflow import WorkflowError


def _private_runtime():
    for name in ('LANGSMITH_TRACING', 'LANGCHAIN_TRACING_V2', 'LANGCHAIN_TRACING'):
        if os.environ.get(name, '').strip().lower() not in ('', 'false', '0'):
            raise ContractError('Disable LangChain/LangSmith environment tracing before processing private evidence')


def run_drafting(work, request: dict, generate) -> Outcome:
    """Run one bounded draft. Callback must accept a brief and return a draft dict.

    No automatic retries or parallel jobs. Callback/network deadlines and costs
    belong to the trusted host; it must enforce its own timeout and disclosure.
    """
    _private_runtime()
    if not callable(generate):
        raise ContractError('generate: supply an explicit trusted host callback')
    from langchain_core.runnables import RunnableLambda
    from langsmith import tracing_context

    # The callback cannot mutate the request used for post-generation validation.
    request = deepcopy(request)
    timings = []

    def timed(name, function):
        def call(value):
            started = perf_counter()
            try:
                return function(value)
            finally:
                timings.append({'stage': name, 'duration_ms': (perf_counter()-started)*1000})
        return call

    def retrieve(_):
        from core.contracts import object_fields
        object_fields(request, {'job_id', 'kind', 'language', 'limit'}, set(), 'writing request')
        return writing_brief(work, **request)

    def draft(result):
        if result.outcome != 'ok' or not result.data['context']['facts']:
            raise WorkflowError('needs_input', 'No usable confirmed evidence; host generation was not invoked.')
        # Copy before handing private context to explicitly configured host code.
        return generate(deepcopy(result.data))

    def validate(result):
        return check_draft(work, request, result)

    chain = (RunnableLambda(timed('retrieve', retrieve))
             | RunnableLambda(timed('host_draft', draft))
             | RunnableLambda(timed('revalidate', validate)))
    # Disable ambient tracing even when this code is embedded in a traced host.
    with tracing_context(enabled=False):
        result = chain.invoke(None, config={'callbacks': [], 'max_concurrency': 1})
    data = deepcopy(result.data)
    data['orchestration'] = {
        'backend': 'langchain-core-lcel', 'stages': timings,
        'host_tokens': None, 'host_cost': None, 'host_usage_observed': False,
        'generation_source': 'explicit-host-callback', 'training_performed': False,
    }
    # model_api_calls in the core packet describes core validation only.
    data.pop('model_api_calls', None)
    return Outcome(result.outcome, data, result.issues)
