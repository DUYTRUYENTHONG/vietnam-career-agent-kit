import threading
import time
import unittest
from unittest.mock import patch
import test_parallel_execution as fixtures
from core.parallel_execution import run_parallel_with_bridge
from core.workflow import WorkflowError


class DeadlineTests(unittest.TestCase):
    setUp=fixtures.ParallelExecutionTests.setUp
    tearDown=fixtures.ParallelExecutionTests.tearDown
    start=fixtures.ParallelExecutionTests.start
    receipt=fixtures.ParallelExecutionTests.receipt
    plan=fixtures.ParallelExecutionTests.plan
    approve=fixtures.ParallelExecutionTests.approve

    def test_stalled_lane_returns_pending_and_other_lane_completes(self):
        run=self.start(2);release=threading.Event();test=self
        class Bridge:
            def perform(self,request):
                if request['job_id']==1:
                    release.wait(10)
                return test.receipt(request)
        try:
            result=run_parallel_with_bridge(self.work,run,Bridge(),action_timeout_seconds=1)
            self.assertEqual(result.outcome,'needs_input')
            self.assertEqual(result.data['quarantined_requests'][0]['job_id'],1)
            status=self.work.parallel_status(run).data
            self.assertEqual(len(status['pending']),1)
            self.assertEqual(status['lanes'][1]['state'],'completed')
            with self.assertRaises(WorkflowError):run_parallel_with_bridge(self.work,run,Bridge())
            with self.work._db() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM execution_submissions').fetchone()[0],1)
        finally:release.set()

    def test_stalled_submit_keeps_unique_attempt_and_ignores_late_result(self):
        run=self.start(1);release=threading.Event();test=self;calls=[]
        class Bridge:
            def perform(self,request):
                calls.append(request['action'])
                if request['action']=='submit':release.wait(10)
                return test.receipt(request)
        try:
            result=run_parallel_with_bridge(self.work,run,Bridge(),action_timeout_seconds=1)
            self.assertEqual(result.outcome,'needs_input')
            self.assertEqual(calls.count('submit'),1)
            self.assertEqual(self.work.parallel_status(run).data['pending'][0]['action'],'submit')
            with self.work._db() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM execution_attempts').fetchone()[0],1)
                self.assertEqual(db.execute('SELECT count(*) FROM execution_submissions').fetchone()[0],0)
        finally:release.set()

    def test_invalid_timeouts_fail_before_work(self):
        for value in [0,-1,True,float('nan'),float('inf'),3601]:
            with self.assertRaises(ValueError):run_parallel_with_bridge(None,'none',None,action_timeout_seconds=value)

    def test_already_completed_but_late_receipt_is_quarantined(self):
        run=self.start(1);test=self
        class Bridge:
            def perform(self,request):time.sleep(.05);return test.receipt(request)
        def delayed_poll(futures,**kwargs):
            for future in futures:future.result()
            return set(futures),set()
        with patch('core.parallel_execution.wait',side_effect=delayed_poll):
            result=run_parallel_with_bridge(self.work,run,Bridge(),action_timeout_seconds=.01)
        self.assertEqual(result.outcome,'needs_input')
        self.assertEqual(self.work.parallel_status(run).data['pending'][0]['action'],'inspect')

    def test_expired_run_still_performs_only_read_only_recovery(self):
        run=self.start(1);test=self;calls=[]
        for action in ['inspect','fill','upload','review','submit']:
            request=self.work.next_parallel_action(run,1).data['request']
            self.assertEqual(request['action'],action)
            self.work.record_parallel_action(run,self.receipt(request))
        self.work.stop_parallel_lane(run,1,'Fictional lost confirmation')
        with self.work._db() as db:
            db.execute("UPDATE execution_runs SET deadline_utc='2000-01-01T00:00:00+00:00' WHERE id=?",(run,))
        self.work.recover_parallel_execution(run,1)
        class Bridge:
            def perform(self,request):calls.append(request['action']);return test.receipt(request)
        result=run_parallel_with_bridge(self.work,run,Bridge(),action_timeout_seconds=1)
        self.assertEqual(calls,['verify'])
        self.assertEqual(result.data['state'],'completed')
