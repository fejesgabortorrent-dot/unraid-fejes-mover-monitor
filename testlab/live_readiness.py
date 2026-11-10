#!/usr/bin/env python3
"""Read-only prerequisites for the disposable FejesMover-Test VM; no repair."""
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys

if socket.gethostname()!='FejesMover-Test':
    raise SystemExit('Refusing: this diagnostic is restricted to FejesMover-Test')
base=Path('/boot/config/plugins/fejes.mover.monitor')
sys.path.insert(0,str(base/'tools'))
import selective_mover as mover
report={'hostname':socket.gethostname(),'read_only':True,
        'pool_mounted':os.path.ismount('/mnt/cache'),
        'array_mounted':os.path.ismount('/mnt/disk1'),
        'advanced_settings_present':(base/'settings.json').is_file(),
        'profile_present':(base/'selective-profile.json').is_file(),
        'integrity_installed':Path('/usr/local/emhttp/plugins/dynamix.file.integrity').is_dir(),
        'integrity_pipe_present':Path('/var/run/hash.pipe.disk1').exists(),
        'launcher_present':mover.PROFILE.launcher.is_file()}
for key,name in [('runtime_version','/var/log/plugins/fejes.mover.monitor.plg'),('boot_version','/boot/config/plugins/fejes.mover.monitor.plg')]:
    p=Path(name)
    match=re.search(r'<PLUGIN[^>]*\bversion="([^"]+)"',p.read_text()) if p.is_file() else None
    report[key]=match[1] if match else None
try:
    report['guards']=mover.guards()
except mover.ERRORS as error:
    report['guard_failure']={'type':type(error).__name__,'detail':str(error)}
try:
    p=subprocess.run(['docker','ps','--format','{{.Names}}'],capture_output=True,text=True,timeout=10,check=True)
    report['lab_containers_running']={name:name in p.stdout.splitlines() for name in ('fm-qbit','fm-peer')}
except (OSError,subprocess.SubprocessError):
    report['docker_readable']=False
p=Path('/boot/config/docker.cfg')
if p.is_file():
    cfg=dict(re.findall(r'^([A-Za-z0-9_]+)="([^"]*)"',p.read_text(),re.M))
    report['docker_persistent_enabled']=cfg.get('DOCKER_ENABLED')=='yes'
    report['docker_persistent_image_gib']=cfg.get('DOCKER_IMAGE_SIZE')
    report['docker_persistent_path_is_lab_image']=cfg.get('DOCKER_IMAGE_FILE')=='/mnt/disk1/system/docker/docker.img'
print(json.dumps(report,indent=2,sort_keys=True))
