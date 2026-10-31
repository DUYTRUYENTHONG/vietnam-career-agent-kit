"""Bounded tab-close callbacks; only the caller validates and records receipts."""
import copy
import json
import time

from .bounded_workers import BoundedWorkers
from .ledger import canonical_hash


class ParallelCleanup:
    def __init__(self, work, run_id, bridge, workers, timeout):
        self.work, self.run_id = work, run_id
        self.handler = getattr(bridge, 'close_application_tab', None)
        self.pool = BoundedWorkers(workers) if callable(self.handler) else None
        self.capacity, self.timeout = workers, min(timeout, 30)
        self.pending, self.quarantined = {}, []
        self.attempted, self.issues = set(), []

    def _perform(self, item):
        return self.handler(copy.deepcopy(item)), time.monotonic()

    def schedule(self):
        if self.pool is None:
            return
        available = self.capacity - len(self.pending) - len(self.quarantined)
        if available <= 0:
            return
        for item in self.work.parallel_cleanup(self.run_id).data['requests']:
            if item['request_id'] in self.attempted:
                continue
            self.attempted.add(item['request_id'])
            # Revalidate immutable evidence and current ownership on the writer
            # thread immediately before dispatch; the host also checks ownership.
            current = self.work.parallel_cleanup(self.run_id).data['requests']
            if not any(canonical_hash(item) == canonical_hash(row) for row in current):
                self.issues.append('Tab cleanup deferred: evidence or binding changed; preserve the current tab.')
                continue
            intent = self.work.inside('execution/cleanup-intents/' + self.run_id +
                                      '/' + item['request_id'] + '.json')
            intent.parent.mkdir(parents=True, exist_ok=True)
            try:
                with intent.open('x', encoding='utf8') as stream:
                    json.dump({'request': item, 'request_sha256': canonical_hash(item)}, stream)
            except FileExistsError:
                self.quarantined.append({'job_id': item['job_id'], 'request_id': item['request_id'],
                                         'remote_termination_confirmed': False})
                self.issues.append('Tab cleanup deferred: an earlier close intent has no successful receipt. '
                                   'Reconcile through the existing cleanup receipt API; never replay the close.')
                available -= 1
                if available == 0:
                    break
                continue
            deadline = time.monotonic() + self.timeout
            self.pending[self.pool.submit(self._perform, item)] = (item, deadline)
            available -= 1
            if available == 0:
                break

    def _quarantine(self, item):
        self.quarantined.append({'job_id': item['job_id'], 'request_id': item['request_id'],
                                 'remote_termination_confirmed': False})
        self.issues.append('Tab cleanup failed (TimeoutError); close outcome is unknown. '
                           'Reconcile the owned binding before another cleanup attempt; no receipt is inferred.')

    def collect(self):
        for future, (item, deadline) in list(self.pending.items()):
            if not future.done():
                if time.monotonic() < deadline:
                    continue
                self.pending.pop(future)
                future.cancel()  # Running host callbacks are not killed.
                self._quarantine(item)
                continue
            self.pending.pop(future)
            try:
                receipt, finished = future.result()
                if finished > deadline:
                    self._quarantine(item)
                    continue
                if not isinstance(receipt, dict) or any(
                        receipt.get(key) != item[key]
                        for key in ('request_id', 'bridge_id', 'binding_id')):
                    raise ValueError('Cleanup receipt belongs to another request or binding')
                self.work.record_parallel_cleanup(self.run_id, receipt)
            except Exception as error:
                self.issues.append('Tab cleanup failed (' + type(error).__name__ +
                                   '); preserve the confirmation and reconcile cleanup separately.')

    def close(self):
        if self.pool is not None:
            self.pool.close()
