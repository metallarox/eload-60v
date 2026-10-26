#!/usr/bin/env python3
"""Simulated load for developing the web page without hardware: python3 mock_server.py [port]
Serves firmware/web/index.html and the same /api endpoints as the firmware (a 12.6 V battery with 50 mOhm)."""
import json, math, os, sys, time, random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
HERE = os.path.dirname(os.path.abspath(__file__))
S = dict(out=0, mode='CC', set=2.0, mask=15, vcut=10.5, trim=1, trip='', wh=0.0, ah=0.0, t=28.0, log_on=0, lines=0)
T0 = time.time(); hist = []
def chlim(v): return min(5.0, 75.0 / max(v, .1))
def step():
    up = int(time.time() - T0)
    soc_v = 12.6 - 0.002 * S['ah'] * 100
    want = 0
    if S['out']:
        v0 = soc_v
        want = S['set'] if S['mode'] == 'CC' else (S['set'] / v0 if S['mode'] == 'CP' else v0 / S['set'])
    n = bin(S['mask']).count('1') or 1
    ich = [min(want / n, chlim(soc_v)) if S['mask'] & (1 << c) and S['out'] else 0 for c in range(4)]
    i = sum(ich); v = soc_v - 0.05 * i
    S['ah'] += i / 3600 / 2; S['wh'] += i * v / 3600 / 2
    S['t'] += (25 + 0.12 * i * v - S['t']) * 0.02
    return up, v, ich
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, body, ctype='application/json'):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path == '/':
            return self.send(200, open(os.path.join(HERE, '..', 'web', 'index.html'), 'rb').read(), 'text/html')
        if self.path.startswith('/api/status'):
            up, v, ich = step(); p = [x * v for x in ich]
            if len(hist) == 0 or hist[-1][4] != up: hist.append([round(v * 100), round(sum(ich) * 1000), round(sum(p) * 10), round(S['t']), up])
            if S['log_on']: S['lines'] = up
            return self.send(200, json.dumps(dict(fw='0.1.0-mock', up=up, time=time.strftime('%Y-%m-%d %H:%M:%S'), v=v, i=sum(ich), p=sum(p),
                ich=[x * (1 + random.uniform(-.001, .001)) for x in ich], pch=p, icmd=[max(x, .01) if S['out'] and S['mask'] >> c & 1 else 0 for c, x in enumerate(ich)],
                tdie=[S['t'] - 3 + c for c in range(4)], ina=[1, 1, 1, 1], t=S['t'], fan=min(1, .25 + sum(p) / 300), rpm=1200 if S['out'] else 600,
                wh=S['wh'], ah=S['ah'], out=S['out'], mode=S['mode'], set=S['set'], setmax=20 if S['mode'] == 'CC' else (300 if S['mode'] == 'CP' else 10000),
                mask=S['mask'], vcut=S['vcut'], trim=S['trim'], gain=[1.0012, .9987, 1.0005, 1.0021], trip=S['trip'], tripch=-1,
                log=dict(on=S['log_on'], lines=S['lines'], bytes=S['lines'] * 92, int=1, free=14_000_000),
                wifi=dict(ap=0, ssid='Lab', rssi=-58, ip='192.168.1.42', host='eload'))))
        if self.path.startswith('/api/history'):
            return self.send(200, json.dumps(dict(t0=0, dt=1, s=[h[:4] for h in hist[-600:]])))
        return self.send(404, 'not found', 'text/plain')
    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0)); q = {k: v[0] for k, v in parse_qs(self.rfile.read(n).decode()).items()}
        if self.path == '/api/set':
            if 'clear' in q: S['trip'] = ''
            if 'mode' in q:
                if S['out'] and q['mode'] != S['mode']: return self.send(400, json.dumps(dict(ok=False, msg='turn the output off before changing mode')))
                S['mode'] = q['mode']; S['set'] = 0
            for k in ('set', 'vcut'):
                if k in q: S[k] = float(q[k])
            for k in ('mask', 'trim', 'out'):
                if k in q: S[k] = int(q[k])
            if 'reset' in q: S['wh'] = S['ah'] = 0
        elif self.path == '/api/log':
            S['log_on'] = 1 if q.get('action') == 'start' else 0
        return self.send(200, json.dumps(dict(ok=True, msg='ok')))
# pre-fill 8 minutes of history (a 3 A discharge started 6 minutes ago)
for k in range(480):
    i = 3.0 if k > 120 else 0; v = 12.6 - 0.05 * i - 0.0006 * max(0, k - 120)
    hist.append([round(v * 100), round(i * 1000), round(i * v * 10), round(28 + (6 if k > 120 else 0) * (1 - math.exp(-(k - 120) / 90)) if k > 120 else 28), k - 480])
ThreadingHTTPServer(('127.0.0.1', int(sys.argv[1]) if len(sys.argv) > 1 else 8080), H).serve_forever()
