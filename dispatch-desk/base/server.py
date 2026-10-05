"""Stateless delivery quotes; synthetic data, standard-library only."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlparse, parse_qs


def quote(zone, weight):
    rates = {'local': 4, 'regional': 8, 'international': 16}
    if zone not in rates or not 1 <= weight <= 100:
        raise ValueError('Choose a valid zone and weight between 1 and 100 kg')
    return {'zone': zone, 'weight_kg': weight, 'price_eur': rates[zone] + weight * 2,
            'rule_version': '2026.10', 'persistent_data': False}


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, data, content_type='application/json'):
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/healthz':
            return self.respond(200, {'healthy': True})
        if parsed.path == '/api/location':
            return self.respond(200, {'cluster': os.getenv('CLUSTER_NAME', 'unconfigured'),
                                      'location': os.getenv('DEPLOYMENT_LOCATION', 'OpenShift')})
        if parsed.path == '/' and os.getenv('MODE') == 'frontend':
            return self.respond(200, Path(__file__).with_name('index.html').read_bytes(), 'text/html; charset=utf-8')
        if parsed.path != '/api/quote':
            return self.respond(404, {'error': 'Not found'})
        try:
            if os.getenv('MODE') == 'frontend':
                # Fixed internal destination; never proxy arbitrary URLs.
                with urlopen('http://quote-engine:8080' + self.path, timeout=4) as upstream:
                    return self.respond(200, upstream.read())
            args = parse_qs(parsed.query)
            result = quote(args.get('zone', ['regional'])[0], int(args.get('weight', ['3'])[0]))
            result.update(location=os.getenv('DEPLOYMENT_LOCATION', 'OpenShift'), cluster=os.getenv('CLUSTER_NAME', 'unconfigured'), pod=os.getenv('HOSTNAME', 'local'))
            return self.respond(200, result)
        except (ValueError, TypeError):
            return self.respond(400, {'error': 'Invalid quote parameters'})
        except Exception:
            return self.respond(503, {'error': 'Quote engine unavailable; inspect workload health'})


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
