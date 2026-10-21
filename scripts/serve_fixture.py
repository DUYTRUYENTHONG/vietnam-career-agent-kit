#!/usr/bin/env python3
"""Loopback-only fictional browser smoke fixture, independent of the live engine.

No production HTTP exception, approval shortcut, browser driver or real candidate
input. POST accepts only three fixed fictional values; nothing persists to disk.
"""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class Portal(BaseHTTPRequestHandler):
    submissions=0

    def log_message(self,*args):pass

    def reply(self,status,body,kind='application/json'):
        self.send_response(status);self.send_header('Content-Type',kind)
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers();self.wfile.write(body)

    def do_GET(self):
        if self.path=='/':return self.reply(200,(ROOT/'tests/fixtures/application.html').read_bytes(),'text/html; charset=utf-8')
        if self.path=='/status':return self.reply(200,json.dumps({'fictional_submissions':self.submissions}).encode())
        self.reply(404,b'{}')

    def do_POST(self):
        if self.path!='/submit':return self.reply(404,b'{}')
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 1<=length<=1024:raise ValueError('Invalid size')
            payload=json.loads(self.rfile.read(length))
            if (set(payload)!={'salary','privacy','document_sha256'} or
                    payload['salary']!='Negotiable' or payload['privacy'] is not True or
                    payload['document_sha256']!=hashlib.sha256(b'%PDF-1.4\nFictional upload fixture only\n%%EOF\n').hexdigest()):
                raise ValueError('Only fixed fictional data accepted')
        except (ValueError,TypeError):return self.reply(400,b'{"error":"fictional fixture only"}')
        if type(self).submissions:return self.reply(409,b'{"error":"duplicate fictional submission"}')
        type(self).submissions+=1
        self.reply(200,b'{"fictional":true,"confirmed":true}')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    if not 1024<=args.port<=65535:parser.error('Use an unprivileged port')
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Portal)
    print(f'Fictional UI smoke fixture: http://127.0.0.1:{args.port}/',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__=='__main__':main()
