"""Bounded daemon workers: deadlines return control, never imply cancellation."""
from concurrent.futures import Future
from queue import Queue
from threading import Thread


class BoundedWorkers:
    def __init__(self, count):
        self.queue = Queue()
        self.closed = False
        self.threads = [Thread(target=self._worker, daemon=True) for _ in range(count)]
        for thread in self.threads:
            thread.start()

    def _worker(self):
        while True:
            task = self.queue.get()
            if task is None:
                return
            future, function, arguments = task
            if future.set_running_or_notify_cancel():
                try:
                    future.set_result(function(*arguments))
                except BaseException as error:
                    future.set_exception(error)

    def submit(self, function, *arguments):
        if self.closed:
            raise RuntimeError('Worker pool closed')
        future = Future()
        self.queue.put((future, function, arguments))
        return future

    def close(self):
        self.closed = True
        for _ in self.threads:
            self.queue.put(None)


def bounded_call(function, argument, seconds):
    pool = BoundedWorkers(1)
    try:
        return pool.submit(function, argument).result(timeout=seconds)
    finally:
        pool.close()
