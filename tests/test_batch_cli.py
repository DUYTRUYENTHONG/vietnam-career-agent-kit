import unittest
from scripts.kit import parser, execute
from unittest.mock import patch
from core.contracts import Outcome

class BatchCLITests(unittest.TestCase):
    def test_commands_and_worker_default(self):
        args=parser().parse_args(['start-parallel-execution','--fingerprint','f','--bridge-id','b','--runtime-minutes','30'])
        self.assertEqual(args.workers,10)
        for name in ['parallel-status','parallel-cleanup']:
            self.assertEqual(parser().parse_args([name,'--run-id','r']).run_id,'r')
        args=parser().parse_args(['record-parallel-cleanup','--run-id','r','--receipt','receipt.json'])
        self.assertEqual(str(args.receipt),'receipt.json')

    def test_tinyfish_preview_requires_no_workspace(self):
        args=parser().parse_args(['tinyfish-fetch','--plan','public.json'])
        with patch('scripts.kit.load_input',return_value={}), patch('adapters.providers.tinyfish_research.preview',return_value=Outcome('ok',{'network_calls':0},[])) as preview:
            self.assertEqual(execute(args).data['network_calls'],0)
            preview.assert_called_once_with({})
