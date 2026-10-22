"""Local monotonic stage measurements. No telemetry or inferred host usage."""
from contextlib import contextmanager
import time


class Trace:
    def __init__(self, clock=time.perf_counter_ns):
        self.clock = clock
        self.stages = []

    @contextmanager
    def stage(self, name, category='machine'):
        started = self.clock()
        status = 'ok'
        try:
            yield
        except BaseException:
            status = 'failed'
            raise
        finally:
            self.stages.append({'name': name, 'category': category, 'status': status,
                                'duration_ms': round((self.clock()-started)/1_000_000, 3)})

    def report(self, **observed):
        return {'schema_version': '1.0', 'clock': 'perf_counter_ns', 'stages': list(self.stages),
            'observed': observed, 'unavailable': ['host_model_calls', 'host_tokens', 'host_tool_calls',
                'host_context_tokens', 'human_wait', 'provider_cost'],
            'scope': 'Only named local stages; absence of a measurement is not zero.'}
