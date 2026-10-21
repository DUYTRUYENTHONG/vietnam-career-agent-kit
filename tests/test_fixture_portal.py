import hashlib
from http.server import ThreadingHTTPServer
import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request,urlopen

from scripts.serve_fixture import Portal


class FixturePortalTests(unittest.TestCase):
    def test_fixture_accepts_only_fixed_fictional_values_and_one_submission(self):
        class IsolatedPortal(Portal):submissions=0
        server=ThreadingHTTPServer(('127.0.0.1',0),IsolatedPortal)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base='http://127.0.0.1:'+str(server.server_port)
        try:
            with urlopen(base+'/',timeout=5) as result:self.assertIn(b'LOCAL TEST ONLY',result.read())
            data={'salary':'Negotiable','privacy':True,'document_sha256':hashlib.sha256(b'%PDF-1.4\nFictional upload fixture only\n%%EOF\n').hexdigest()}
            def post(data):return urlopen(Request(base+'/submit',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'}),timeout=5)
            with self.assertRaises(HTTPError) as error:post({**data,'salary':'Other'})
            self.assertEqual(error.exception.code,400)
            with post(data) as result:self.assertTrue(json.loads(result.read())['fictional'])
            with self.assertRaises(HTTPError) as error:post(data)
            self.assertEqual(error.exception.code,409)
        finally:server.shutdown();thread.join(timeout=5);server.server_close()
