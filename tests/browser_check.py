"""Smoke checks in installed Microsoft Edge through CDP. No server or extra JS packages.
Run: python tests/browser_check.py (requires Python websocket-client).
"""
import base64
import os
import contextlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.request
import websocket

ROOT = Path(__file__).resolve().parents[1]
CHROME = Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')

TEST_BASE = os.environ.get('SKVOZ_TEST_BASE', ROOT.as_uri()).rstrip('/')
profile_directory = os.environ.get('SKVOZ_BROWSER_PROFILE')
profile_context = contextlib.nullcontext(profile_directory) if profile_directory else tempfile.TemporaryDirectory(prefix='skvoz-browser-', ignore_cleanup_errors=True)
with profile_context as profile:
    stale_port = Path(profile) / 'DevToolsActivePort'
    if stale_port.exists(): stale_port.unlink()
    process = subprocess.Popen([str(CHROME), '--headless=new', '--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage', '--disable-crash-reporter',
        '--ignore-certificate-errors', '--no-first-run', '--no-default-browser-check', '--remote-allow-origins=*',
        '--remote-debugging-port=0', '--user-data-dir=' + profile, 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        port_file = Path(profile) / 'DevToolsActivePort'
        for _ in range(100):
            if port_file.exists(): break
            time.sleep(.1)
        port = port_file.read_text().splitlines()[0]
        tabs = json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json'))
        ws = websocket.create_connection(next(tab for tab in tabs if tab['type']=='page')['webSocketDebuggerUrl'], timeout=15)
        sequence = 0
        errors = []
        def call(method, params=None):
            global sequence
            sequence += 1
            request_id = sequence
            ws.send(json.dumps({'id': request_id, 'method': method, 'params': params or {}}))
            while True:
                reply = json.loads(ws.recv())
                if reply.get('method') == 'Runtime.exceptionThrown': errors.append(reply['params'])
                if reply.get('id') == request_id:
                    assert 'error' not in reply, reply
                    return reply.get('result', {})
        def js(expression):
            reply = call('Runtime.evaluate', {'expression': expression, 'returnByValue': True})
            assert 'exceptionDetails' not in reply, reply
            return reply.get('result', {}).get('value')
        def navigate(name):
            js("window.__skvozNavigationMarker=true")
            target_url = TEST_BASE + '/' + name
            navigation = call('Page.navigate', {'url': target_url})
            new_document = 'loaderId' in navigation
            for _ in range(150):
                ready = js("document.readyState==='complete' && typeof items!=='undefined'" + (" && !window.__skvozNavigationMarker" if new_document else ''))
                if ready: break
                time.sleep(.1)
            assert js("typeof cardMarkup==='function'"), (js('location.href'),js('document.body.innerText.slice(0,500)'),errors)
        def click(selector):
            point = js(f"(()=>{{const e=document.querySelector({json.dumps(selector)});e.scrollIntoView({{block:'center',behavior:'instant'}});const r=e.getBoundingClientRect();return {{x:r.x+r.width/2,y:r.y+r.height/2}}}})()")
            time.sleep(.12)  # Settle scroll before measuring the physical click point.
            point = js(f"(()=>{{const r=document.querySelector({json.dumps(selector)}).getBoundingClientRect();return {{x:r.x+r.width/2,y:r.y+r.height/2}}}})()")
            for kind in ['mousePressed', 'mouseReleased']:
                call('Input.dispatchMouseEvent', {'type':kind, **point, 'button':'left', 'clickCount':1})
        call('Runtime.enable')
        call('Page.enable')
        exec(compile((ROOT / 'tests' / os.environ.get('SKVOZ_SCENARIO', 'browser_scenarios.py')).read_text(encoding='utf-8'), os.environ.get('SKVOZ_SCENARIO', 'browser_scenarios.py'), 'exec'))
    finally:
        try:
            version = json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/version'))
            shutdown = websocket.create_connection(version['webSocketDebuggerUrl'], timeout=5)
            shutdown.send(json.dumps({'id':999999,'method':'Browser.close'}))
            shutdown.close()
            process.wait(timeout=10)
        except Exception:
            process.terminate()
            process.wait(timeout=15)
