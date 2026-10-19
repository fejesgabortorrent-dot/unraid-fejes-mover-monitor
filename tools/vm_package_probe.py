"""Alpine guest only: simulate Unraid package boot paths without real Mover."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as ET

assert Path('/etc/alpine-release').is_file(),'Run only inside the disposable Alpine guest'
assert Path('/etc/fejes-mover-disposable-lab').read_text().strip()=='FEJES_MOVER_DISPOSABLE_LAB','Explicit disposable-guest marker required'
LAB=Path('/opt/fejeslab')
SAVED=Path('/boot/config/plugins/fejes.mover.monitor.plg')
RUNTIME=Path('/usr/local/emhttp/plugins/fejes.mover.monitor')
CONFIG=Path('/boot/config/plugins/fejes.mover.monitor/settings.json')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def setup():
    for directory in ['/boot/config/plugins','/boot/config/pools','/usr/local/emhttp','/mnt/cache','/mnt/user/Filmek','/var/local/emhttp']:
        Path(directory).mkdir(parents=True,exist_ok=True)
    Path('/etc/unraid-version').write_text('version="7.3.3"\n# Simulated marker in Alpine test guest only\n')
    Path('/boot/config/pools/cache.cfg').write_text('# synthetic pool definition\n')
    Path('/var/local/emhttp/var.ini').write_text('csrf_token="vm-test-token"\n')
    for mount in ['/usr/local/emhttp','/mnt/cache']:
        if subprocess.run(['mountpoint','-q',mount]).returncode!=0:
            subprocess.run(['mount','-t','tmpfs','-o','size=64m','tmpfs',mount],check=True)
def install(source):
    setup()
    tree=ET.parse(source).getroot()
    for node in tree.findall('FILE'):
        if 'Name' in node.attrib:
            path=Path(node.attrib['Name'])
            assert str(path).startswith('/tmp/fejes-mover-monitor-')
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(node.findtext('INLINE'),encoding='utf-8')
    script=next(n.findtext('INLINE') for n in tree.findall('FILE') if n.attrib.get('Run')=='/bin/bash' and not n.attrib.get('Method'))
    subprocess.run(['bash'],input=script,text=True,check=True,stdout=subprocess.DEVNULL)
    if source!=SAVED:SAVED.write_bytes(source.read_bytes())
def verify():
    tree=ET.parse(SAVED).getroot();count=0
    for node in tree.findall('FILE'):
        if 'Name' not in node.attrib:continue
        name=Path(node.attrib['Name']).name
        target=(CONFIG.parent/'tools' if name.endswith('.py') else RUNTIME)/name
        assert target.read_text()==node.findtext('INLINE'),name
        if name.endswith(('.page','.php')):subprocess.run(['php','-l',str(target)],check=True,stdout=subprocess.DEVNULL)
        count+=1
    assert count==11
    assert json.loads(CONFIG.read_text())=={'version':1,'mode':'demo','pool':'cache'}
    assert not Path('/usr/local/sbin/mover').exists(),'Real Mover must not exist'
    page=(RUNTIME/'FejesMoverProtection.page').read_text().split('---\n',1)[1]
    runner=LAB/'render.php'
    runner.write_text('<?php $_SERVER["REQUEST_METHOD"]="POST"; $_POST=["fp_csrf"=>"vm-test-token","fp_action"=>"dry-run"]; eval(substr(file_get_contents('+json.dumps(str(LAB/'body.php'))+'),5));')
    (LAB/'body.php').write_text(page)
    html=subprocess.check_output(['php',str(runner)],text=True)
    assert 'Szimulált állapot' in html and 'Most várakozna' in html
    return {'version':tree.attrib['version'],'exact_files':count,'demo_post_renders':True,'settings_hash':digest(CONFIG),'runtime_hashes':{p.name:digest(p) for p in RUNTIME.iterdir() if p.suffix in ('.page','.php')},'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
def main(action):
    if action=='init':
        setup();install(LAB/'fejes.mover.monitor.plg')
        CONFIG.write_text(json.dumps({'version':1,'mode':'demo','pool':'cache'})+'\n')
        startup=Path('/etc/local.d/fejes-mover-lab.start')
        startup.write_text('#!/bin/sh\n/usr/bin/python3 /opt/fejeslab/vm_package_probe.py restore >> /var/log/fejes-mover-lab-boot.log 2>&1\n')
        startup.chmod(0o755)
        subprocess.run(['rc-update','add','local','default'],check=True,stdout=subprocess.DEVNULL)
        result=verify();(LAB/'before-reboot.json').write_text(json.dumps(result))
    elif action=='restore':
        setup()
        if SAVED.exists():install(SAVED)
        return
    elif action=='verify':
        result=verify();before=json.loads((LAB/'before-reboot.json').read_text())
        assert result['boot_id']!=before['boot_id'],'Guest did not reboot'
        assert result['settings_hash']==before['settings_hash']
        assert result['runtime_hashes']==before['runtime_hashes']
        result={'guest_reboot_verified':True,'runtime_restored_from_tmpfs':True,'settings_preserved':True,'demo_post_renders':True,'exact_files':result['exact_files']}
    elif action=='remove':
        tree=ET.parse(SAVED).getroot()
        before={'settings_hash':digest(CONFIG),'helpers':{p.name:digest(p) for p in (CONFIG.parent/'tools').glob('*.py')},'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
        script=next(n.findtext('INLINE') for n in tree.findall('FILE') if n.attrib.get('Method')=='remove')
        subprocess.run(['bash'],input=script,text=True,check=True,stdout=subprocess.DEVNULL)
        SAVED.unlink()  # only this lab copy; source package remains in /opt
        assert not RUNTIME.exists() or not list(RUNTIME.glob('*.page'))
        (LAB/'before-remove-reboot.json').write_text(json.dumps(before))
        result={'uninstall_passed':True,'settings_retained':digest(CONFIG)==before['settings_hash']}
    elif action=='verify-removed':
        before=json.loads((LAB/'before-remove-reboot.json').read_text())
        assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=before['boot_id']
        assert not SAVED.exists() and not list(RUNTIME.glob('*.page'))
        assert digest(CONFIG)==before['settings_hash']
        assert {p.name:digest(p) for p in (CONFIG.parent/'tools').glob('*.py')}==before['helpers']
        result={'second_guest_reboot_verified':True,'uninstalled_plugin_stays_absent':True,'settings_and_helpers_retained':True}
    else:raise ValueError(action)
    print(json.dumps(result))
if __name__=='__main__':main(sys.argv[1])
