"""Small stateless retail demo. Python stdlib only; arbitrary UID compatible."""
import json
import os
from pathlib import Path
import random
import ssl
import time
import urllib.request
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODE = os.getenv('MODE', 'catalog')
CLUSTER = os.getenv('CLUSTER_NAME', 'local')
VERSION = '1.0.0'
TRAFFIC = Path(os.getenv('TRAFFIC_FILE', '/traffic/config.json'))
SSL = ssl.create_default_context(cafile=os.getenv('UPSTREAM_CA_FILE') or None)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(newurl,code,'Redirect refused for authenticated backend',headers,fp)


def fetch(url, auth=None):
    # No automatic retry or fallback: failures remain visible to the continuity probe.
    if auth and auth.get('token_file'):
        if not url.startswith('https://'):raise ValueError('Authenticated transport requires TLS')
        req=urllib.request.Request(url,headers={'Authorization':'Bearer '+Path(auth['token_file']).read_text().strip()})
        opener=urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=auth['ca_file'])),NoRedirect())
        with opener.open(req,timeout=4) as r:return json.load(r)
    with urllib.request.urlopen(url, context=SSL, timeout=4) as r:
        return json.load(r)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(json.dumps({'time':time.time(), 'component':MODE, 'peer':self.client_address[0], 'message':fmt % args}), flush=True)

    def reply(self, data, status=200, content_type='application/json'):
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            if path == '/healthz':
                return self.reply({'healthy':True, 'component':MODE})
            if MODE == 'gateway' and path == '/status':
                return self.reply(json.loads(TRAFFIC.read_text()))
            if path == '/experience':
                # Public presentation data only; backend URLs and auth paths stay out.
                if MODE != 'gateway':
                    return self.reply({'mode':MODE})
                cfg = json.loads(TRAFFIC.read_text())
                return self.reply({'mode':MODE, 'profile':cfg['profile'],
                    'backends':{role:{'weight':cfg['backends'][role]['weight'],
                        'cluster':os.getenv(role.upper() + '_CLUSTER_NAME', '')}
                        for role in ('source', 'destination')}})
            if path == '/':
                return self.reply(Path(__file__).with_name('index.html').read_bytes(), content_type='text/html; charset=utf-8')
            if MODE == 'catalog' and path == '/catalog':
                return self.reply({'sku':'aro-coffee', 'description':'Fleet blend coffee', 'unit_price':12.50, 'currency':'EUR'})
            if path == '/quote':
                if MODE == 'gateway':
                    cfg = json.loads(TRAFFIC.read_text())
                    eligible = [(k,v) for k,v in cfg['backends'].items() if v['weight'] > 0]
                    key, target = random.choices(eligible, weights=[x[1]['weight'] for x in eligible])[0]
                    response = fetch(target['url'] + '/quote', target)
                    response.update({'traffic_profile':cfg['profile'], 'backend_role':key, 'traffic_revision':cfg['revision']})
                    return self.reply(response)
                if MODE == 'storefront':
                    return self.reply(fetch(os.getenv('QUOTE_URL', 'http://order-quote:8080') + '/quote'))
                if MODE == 'quote':
                    item = fetch(os.getenv('CATALOG_URL', 'http://catalog:8080') + '/catalog')
                    return self.reply({'request_id':str(uuid.uuid4()), 'cluster':CLUSTER, 'version':VERSION,
                        'sku':item['sku'], 'quantity':2, 'total':round(item['unit_price'] * 2, 2),
                        'currency':item['currency'], 'timestamp':time.time()})
            self.reply({'error':'Not found'}, 404)
        except Exception as e:
            self.log_message('upstream request failed: %s', type(e).__name__)
            self.reply({'error':'upstream unavailable', 'component':MODE}, 503)


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', int(os.getenv('PORT', '8080'))), Handler).serve_forever()
