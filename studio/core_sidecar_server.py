#!/usr/bin/env python3
"""Long-lived loopback API process used by the Tauri thin host."""
from __future__ import annotations
import argparse,hmac,json,sys
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
from host_bridge import invoke
MAX_BYTES=48*1024*1024
class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,token):super().__init__(address,Handler);self.token=token
class Handler(BaseHTTPRequestHandler):
    server:Server
    def log_message(self,*_):pass
    def do_POST(self):
        if self.path!="/api/bridge/invoke":return self.send_error(404)
        if not hmac.compare_digest(self.headers.get("X-Quillframe-Sidecar-Token",""),self.server.token):return self._json(401,{"schema":"quillframe_sidecar_error_v1","code":"unauthorized","authority":False})
        try:n=int(self.headers.get("Content-Length","0"))
        except ValueError:n=-1
        if n<0 or n>MAX_BYTES:return self._json(413,{"schema":"quillframe_sidecar_error_v1","code":"request_too_large","authority":False})
        try:req=json.loads(self.rfile.read(n));req["surface"]="tauri_local";req["authority"]=False;out=invoke(req);self._json(200,out)
        except Exception as exc:self._json(400,{"schema":"quillframe_sidecar_error_v1","code":"invalid_request","message":f"{type(exc).__name__}: {exc}","authority":False})
    def _json(self,status,value):
        body=(json.dumps(value,ensure_ascii=False,separators=(",",":"))+"\n").encode();self.send_response(status);self.send_header("Content-Type","application/json");self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
def main():
    p=argparse.ArgumentParser();p.add_argument("--port",type=int,default=0);p.add_argument("--token",required=True);a=p.parse_args();s=Server(("127.0.0.1",a.port),a.token);print(json.dumps({"schema":"quillframe_sidecar_ready_v1","host":"127.0.0.1","port":s.server_port,"authority":False}),flush=True);s.serve_forever()
if __name__=="__main__":main()
