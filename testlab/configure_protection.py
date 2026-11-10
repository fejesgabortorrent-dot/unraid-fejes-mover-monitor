#!/usr/bin/env python3
"""Configure actual protection in the disposable VM using upstream handlers."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import seed_acceptance as lab
lab.environment()
lab.container(lab.SEED);lab.container(lab.PEER)
root=Path('/mnt/disk1/fm-acceptance/guarded')
if not (root/'boot-before-guarded.tgz').is_file():raise SystemExit('Guarded boot backup required')
stamp=str(time.time_ns())
backup=root/('boot-before-protection-'+stamp+'.tgz')
subprocess.run(['tar','-czf',str(backup),'-C','/boot','config'],check=True)
backup.chmod(0o600)
# Persist the exact existing 4 GiB image. Never create another image.
image=Path('/mnt/disk1/system/docker/docker.img')
if image.is_symlink() or image.stat().st_size!=4*1024**3:raise SystemExit('Expected existing 4 GiB lab image')
loops=json.loads(lab.command(['losetup','--json','--list','--output','BACK-FILE']))['loopdevices']
if not any(x.get('back-file')==str(image) for x in loops):raise SystemExit('Lab image not attached')
p=Path('/boot/config/docker.cfg');text=p.read_text()
for key,value in dict(DOCKER_ENABLED='yes',DOCKER_IMAGE_SIZE='4',DOCKER_IMAGE_FILE=str(image)).items():
    text,count=re.subn(r'^'+key+r'="[^"\n]*"$',key+'="'+value+'"',text,flags=re.M)
    if count!=1:raise SystemExit('Ambiguous Docker configuration')
tmp=p.with_name('docker.cfg.fm-tmp');tmp.write_text(text);tmp.chmod(0o600);tmp.replace(p)
lab.command(['docker','update','--restart','unless-stopped',lab.SEED,lab.PEER])
# Use File Integrity's own settings handler to generate watcher and schedule.
plugin=Path('/usr/local/emhttp/plugins/dynamix.file.integrity')
config=Path('/boot/config/plugins/dynamix.file.integrity/dynamix.file.integrity.cfg')
if config.exists():raise SystemExit('Expected unconfigured lab File Integrity')
php='''<?php
$keys=parse_ini_file('/usr/local/emhttp/plugins/dynamix.file.integrity/default.cfg');
$_POST=array_merge($keys,['service'=>'1','schedule'=>'3','dotm'=>'1','hour'=>'3','min'=>'17','priority'=>'','parity'=>'1','exclude'=>'system,appdata','folders'=>'fm-peer,fm-acceptance','disk1-0'=>'1']);
include '/usr/local/emhttp/plugins/dynamix.file.integrity/include/update.watcher.php';
$lines=[];
foreach ($_POST as $k=>$v) {$lines[]=$k.'="'.$v.'"';}
file_put_contents('/boot/config/plugins/dynamix.file.integrity/dynamix.file.integrity.cfg',implode("\\n",$lines)."\\n");
?>'''
subprocess.run(['php','-d','short_open_tag=1'],input=php,text=True,check=True)
config.chmod(0o600)
lab.authenticate(lab.SEED)
sys.path.insert(0,'/boot/config/plugins/fejes.mover.monitor/tools')
import wire_integrity_cron
wire_integrity_cron.main()
# A real completed scrub is required by the mover. Tiny disposable cache only.
subprocess.run(['btrfs','scrub','start','-B','/mnt/cache'],check=True)
print('PASS: real watcher, gated monthly integrity schedule, scrub and 4 GiB Docker persistence configured')
