"""Loopback-only browser demo of actual compiled pages using disposable fixtures.

Run with PHP and Bash on PATH. No production paths are read or written.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import argparse
import base64
import html
import json
import os
import shutil
import subprocess
import tempfile
import threading
from localize import compile_page

ROOT = Path(__file__).resolve().parents[1]
PAGES = {'/Tools/FejesMover':'FejesMover.page', '/Tools/FejesMoverSettings':'FejesMoverSettings.page', '/Tools/FejesMoverSetup':'FejesMoverSetup.page', '/Tools/FejesMoverSelective':'FejesMoverSelective.page', '/Dashboard':'FejesMover.Dashboard.page'}
STATES = {'idle':'Várakozik', 'running':'Mover fut', 'full':'Cache megtelt', 'missing':'Cache nincs csatolva', 'stale':'Bizonytalan PID'}

class Demo:
    def __init__(self, lab):
        self.lab = lab
        (lab/'automation').mkdir()
        (lab/'automation/script').write_text('#!/bin/bash\nKUSZOB_GIB=300\nUJRA_PROBALKOZAS_MP=360\n# Disposable browser fixture. Never execute.\n', newline='\n')
        (lab/'var.ini').write_text('csrf_token="demo-only-token"\n')
        (lab/'syslog').write_text('Oct 18 12:00:00 demo mover: Simulated Mover status; no real transfers.\n')
        proc=lab/'proc/4242';proc.mkdir(parents=True)
        (proc/'status').write_text('Pid:\t4242\nPPid:\t1\n')
        (proc/'cmdline').write_bytes(b'/usr/local/sbin/mover\0')
        (lab/'cache').mkdir()
        (lab/'pools').mkdir()
        (lab/'pools/cache.cfg').write_text('fixture\n')
        (lab/'config').mkdir()
        (lab/'config/selective.json').write_text('{"version":1,"age_days":7}')
        (lab/'config/selective-last.json').write_text(json.dumps({
            'state':'completed','moved_files':3,'moved_bytes':12*1073741824,
            'skipped':{'too_young':18,'protected_content':4,'busy_or_unverified':1}}))

    def render(self, name, state, language, post):
        lab=self.lab
        pid=lab/'mover.pid'
        if state in ('running','stale'):pid.write_text('4242' if state=='running' else '9999')
        elif pid.exists():pid.unlink()
        (lab/'mountinfo').write_text('1 0 0:1 / '+(lab/'cache').as_posix()+' rw - btrfs /dev/demo rw\n' if state!='missing' else '')
        source=compile_page((ROOT/'src'/name).read_text(encoding='utf-8')).split('---\n',1)[1]
        source=source.replace('<?php','<?php namespace BrowserDemo; use \\RuntimeException; use \\Throwable;',1)
        free=0 if state=='full' else 350*1073741824
        source=source.replace('namespace BrowserDemo;',f'namespace BrowserDemo; function disk_total_space($p){{return {1000*1073741824};}} function disk_free_space($p){{return {free};}}',1)
        replacements={
            '/usr/local/emhttp/plugins/fejes.mover.monitor/FejesMoverRuntime.php':lab/'FejesMoverRuntime.php',
            '/boot/config/plugins/fejes.mover.monitor/settings.json':lab/'config/settings.json',
            '/boot/config/plugins/fejes.mover.monitor/selective.json':lab/'config/selective.json',
            '/boot/config/plugins/fejes.mover.monitor/selective-last.json':lab/'config/selective-last.json',
            '/var/run/fejes-selective-inventory.lock':lab/'selective.lock',
            '/boot/config/pools/':str(lab/'pools')+'/',
            '/var/run/fejes-mover-config.lock':lab/'mode.lock',
            '/proc/self/mountinfo':lab/'mountinfo', '/var/local/emhttp/var.ini':lab/'var.ini',
            '/var/run/mover.pid':pid, '/var/run/fejes-mover-settings.lock':lab/'settings.lock',
            '/boot/config/plugins/user.scripts/scripts/Filmek_Mover_Threshold/script':lab/'automation/script',
            '/boot/config/plugins/fejes.mover.monitor/backups':lab/'backups',
            '/var/log/syslog':lab/'syslog',
            '/tmp/user.scripts/tmpScripts/Filmek_Mover_Threshold/log.txt':lab/'script.log',
            '/mnt/cache':lab/'cache', '/proc/':str(lab/'proc')+'/',
        }
        runtime=(ROOT/'src/FejesMoverRuntime.php').read_text(encoding='utf-8')
        for old,new in replacements.items():
            source=source.replace(old,str(new).replace('\\','/'))
            runtime=runtime.replace(old,str(new).replace('\\','/'))
        runtime=runtime.replace("'/mnt/'",json.dumps(lab.as_posix()+'/'))
        (lab/'FejesMoverRuntime.php').write_text(runtime,encoding='utf-8',newline='\n')
        if os.name=='nt':source=source.replace('/bin/bash -n ','bash -n ')
        page=lab/name;page.write_text(source,encoding='utf-8',newline='\n')
        encoded=base64.b64encode(json.dumps(post or {}).encode()).decode()
        wrapper=lab/'run.php'
        wrapper.write_text('<?php $_COOKIE["fejes_mover_lang"]='+json.dumps(language)+'; $_SERVER["REQUEST_METHOD"]='+json.dumps('POST' if post is not None else 'GET')+'; $_POST=json_decode(base64_decode('+json.dumps(encoded)+'),true); ob_start(); include '+json.dumps(str(page))+'; $out=ob_get_clean(); if(isset($mytiles)){echo "<table>".$mytiles["fejes.mover.monitor"]["column2"]."</table>".$out;}else{echo $out;}',encoding='utf-8')
        result=subprocess.run(['php','-d','display_errors=stderr','-d','error_reporting=32767',str(wrapper)],capture_output=True,text=True,encoding='utf-8',timeout=15)
        if result.returncode or result.stderr.strip():raise RuntimeError(result.stderr)
        return result.stdout

def run(port):
    if not shutil.which('php') or not shutil.which('bash'):raise SystemExit('PHP and Bash must be on PATH')
    with tempfile.TemporaryDirectory(prefix='fejes-browser-demo-') as directory:
        demo=Demo(Path(directory))
        render_lock=threading.Lock()
        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(15)
            def do_GET(self):self.handle_page(False)
            def do_POST(self):self.handle_page(True)
            def handle_page(self, is_post):
                route=urlsplit(self.path)
                if route.path=='/':
                    self.send_response(302);self.send_header('Location','/Tools/FejesMover');self.end_headers();return
                if route.path not in PAGES:
                    self.send_error(404);return
                if self.headers.get('Host') not in (f'127.0.0.1:{port}',f'localhost:{port}'):
                    self.send_error(403);return
                cookies=SimpleCookie(self.headers.get('Cookie',''))
                state=parse_qs(route.query).get('state',[cookies.get('fm_demo_state').value if cookies.get('fm_demo_state') else 'idle'])[0]
                if state not in STATES:state='idle'
                language=cookies.get('fejes_mover_lang').value if cookies.get('fejes_mover_lang') else 'hu'
                if language not in ('hu','en','de'):language='hu'
                post=None
                if is_post:
                    length=int(self.headers.get('Content-Length','0'))
                    if length>16384:self.send_error(413);return
                    post={k:v[-1] for k,v in parse_qs(self.rfile.read(length).decode(),keep_blank_values=True).items()}
                try:
                    with render_lock:
                        body=demo.render(PAGES[route.path],state,language,post)
                except Exception as error:self.send_error(500,str(error));return
                options=''.join(f'<option value="{key}"'+(' selected' if key==state else '')+f'>{label}</option>' for key,label in STATES.items())
                banner='<aside><strong>🧪 TESZTFELÜLET / DEMO / TESTUMGEBUNG</strong><p>Szimulált adatok · Simulated data · Simulierte Daten</p><nav><a href="/Tools/FejesMover">Figyelő / Monitor</a><a href="/Dashboard">Dashboard</a><a href="/Tools/FejesMoverSettings">Beállítások / Settings</a></nav><label>Tesztállapot: <select aria-label="Tesztállapot" onchange="location.assign(location.pathname+\'?state=\'+this.value)">'+options+'</select></label><small>A mentés kizárólag a tesztpéldányt módosítja. / Saves affect demo files only.</small></aside>'
                document='<!doctype html><html lang="'+language+'"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fejes Mover · DEMO</title><style>body{margin:0;background:#1b1b1b;color:#e3e3e3;font:15px/1.5 Arial,sans-serif}a{color:#ef9b4f}aside{padding:14px 20px;background:#252525;border-bottom:2px solid #ef7d00}aside p{margin:6px 0}nav{display:flex;gap:20px;flex-wrap:wrap;margin:10px 0}select{padding:7px;background:#292929;color:#fff;border:1px solid #777;border-radius:3px}aside small{display:block;margin-top:8px;opacity:.8}body>table{width:min(700px,95%);margin:30px auto}button{cursor:pointer}</style>'+banner+body+'</html>'
                data=document.encode('utf-8');self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('Set-Cookie',f'fm_demo_state={state}; Path=/; SameSite=Lax; HttpOnly');self.end_headers();self.wfile.write(data)
        server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
        print(f'Demo ready: http://127.0.0.1:{port}/Tools/FejesMover',flush=True)
        try:server.serve_forever()
        finally:server.server_close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765)
    run(parser.parse_args().port)
