"""Same-origin UI gateway. Only forwards fixed API paths; no credentials in browser."""
import os,urllib.request,urllib.error
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,status,body,kind):
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; frame-ancestors 'none'");self.end_headers();self.wfile.write(body)
    def handle_request(self):
        path=self.path.split('?')[0]
        if self.command=='GET' and path=='/':return self.send(200,Path('/app/index.html').read_bytes(),'text/html; charset=utf-8')
        if self.command=='GET' and path=='/healthz':return self.send(200,b'{"alive":true}','application/json')
        if path not in ['/api/products','/api/orders','/api/status'] or (self.command=='POST' and path!='/api/orders'):return self.send(404,b'{}','application/json')
        data=None
        if self.command=='POST':
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<=4096:raise ValueError()
                data=self.rfile.read(n)
            except ValueError:return self.send(400,b'{"error":"Invalid request size"}','application/json')
        try:
            req=urllib.request.Request(os.getenv('API_URL','http://orders-api:8080')+path,data=data,method=self.command,headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=12) as response:return self.send(response.status,response.read(),'application/json')
        except urllib.error.HTTPError as e:return self.send(e.code,e.read(),'application/json')
        except Exception:return self.send(503,b'{"error":"Orders API unavailable. Please retry shortly."}','application/json')
    do_GET=handle_request
    do_POST=handle_request
if __name__=='__main__':ThreadingHTTPServer(('0.0.0.0',8080),Handler).serve_forever()
