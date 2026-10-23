"""Render actual compiled pages with isolated, synthetic English GET fixtures.

Serve the exported HTML only on loopback and capture with the browser tool.
There are no credentials, production paths, helper execution or POST actions.
"""
import argparse
import ast
import json
from pathlib import Path
import tempfile

from browser_demo import Demo

ROOT=Path(__file__).resolve().parents[1]

def export(target):
    target.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.render-',dir=target.resolve()) as folder:
        lab=Path(folder)
        demo=Demo(lab)
        # Read only trusted fixture literals; importing the Linux launch helper
        # would require fcntl on the Windows screenshot host.
        names={'START','STAMP','LOCK_BLOCK','GATE_BLOCK','DISPATCH_BLOCK'}
        constants={node.targets[0].id:ast.literal_eval(node.value)
                   for node in ast.parse((ROOT/'tools/wire_mover_gate.py').read_text(encoding='utf-8')).body
                   if isinstance(node,ast.Assign) and isinstance(node.targets[0],ast.Name)
                   and node.targets[0].id in names}
        launcher=(ROOT/'tests/fixtures/threshold-reviewed.sh').read_text(encoding='utf-8')
        launcher=launcher.replace(constants['START'],constants['DISPATCH_BLOCK']+constants['LOCK_BLOCK']+constants['START'],1)
        launcher=launcher.replace(constants['STAMP'],constants['GATE_BLOCK']+constants['STAMP'],1)
        (lab/'automation/script').write_text(launcher,newline='\n')
        views=[('monitor','FejesMover.page','observer','Live activity monitor'),
               ('dashboard','FejesMover.Dashboard.page','observer','Dashboard card'),
               ('settings','FejesMoverSettings.page','advanced','Threshold and cooldown settings'),
               ('selective','FejesMoverSelective.page','advanced','Age-filtered selective movement')]
        for slug,page,mode,title in views:
            (lab/'config/settings.json').write_text(json.dumps({'version':1,'mode':mode,'pool':'cache'}))
            body=demo.render(page,'idle','en',None)
            # Synthetic wrapper, actual compiled product controls below it.
            wrapper='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fejes Mover Monitor — TITLE</title><style>
body{margin:0;background:#1b1b1b;color:#e3e3e3;font:15px/1.5 Arial,sans-serif}a{color:#ef9b4f}button{cursor:pointer}select{padding:7px;background:#292929;color:#fff;border:1px solid #777;border-radius:3px}header{max-width:1160px;margin:0 auto;padding:28px 20px 20px;border-bottom:2px solid #ef7d00}header strong{font-size:25px}header p{margin:7px 0 0;color:#bbb}header span{float:right;border:1px solid #777;padding:5px 10px;border-radius:4px;font-size:12px}body>table{width:min(700px,95%);margin:35px auto}fieldset{border:1px solid #777;padding:16px}input{accent-color:#ef7d00}#fms button{background:#292929;color:#eee;border:1px solid #888;padding:8px 12px;border-radius:3px;margin:4px}#fms small{color:#bbb}
</style></head><body><header><span>ENGLISH · SIMULATED DATA</span><strong>Fejes Mover Monitor</strong><p>TITLE · Unraid 7.x · Preview of the actual plugin interface</p></header>BODY</body></html>'''
            document=wrapper.replace('TITLE',title).replace('BODY',body)
            # The static preview must not poll the host or contain any private lab path.
            document=document.replace(str(lab).replace('\\','/'),'[preview]')
            document=document.replace(str(lab),'[preview]')
            (target/(slug+'.html')).write_text(document,encoding='utf-8',newline='\n')
    print('Exported four English views to '+str(target))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path)
    export(parser.parse_args().output)
