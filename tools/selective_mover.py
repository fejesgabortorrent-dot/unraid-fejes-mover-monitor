#!/usr/bin/env python3
"""Age-filtered native Unraid movement. No global mover invocation.

Production scope is fixed to cache/Filmek -> the array with unchanged user-share
paths. Global maintenance guards remain mandatory; torrent exclusions are per
content path. All actions fail closed when their required evidence is missing.
"""
import argparse
from collections import Counter
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import traceback

import selective_preview as inventory_adapter
from selective_preview import canonical, read_json, atomic_json
from selection_policy import plan, age_days, within, waiting_table, ratio_target, prioritize, batch_bytes
from torrent_preflight import read_snapshot, host_path, assess
from fejes_service import dry_run

BASE = Path('/boot/config/plugins/fejes.mover.monitor')
CONFIG = BASE/'selective.json'
INVENTORY = BASE/'selective-inventory.json'
LAST = BASE/'selective-last.json'
FORECAST = BASE/'selective-forecast.json'
SOURCE = Path('/mnt/cache/Filmek')
ROOT = '/mnt/user/Filmek'
ENGINE = '/usr/libexec/unraid/move'
PID = Path('/var/run/mover.pid')
ATTEMPT = Path('/var/run/fejes-selective-last-attempt')
MAX_FILES = 8
MAX_BYTES = 16*1024**3
ERRORS = (OSError, ValueError, TypeError, KeyError, AttributeError, RuntimeError,
          subprocess.SubprocessError)


def signature(info):
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def valid_file(path):
    """Reject escaping parents, native stdin ambiguity and non-regular objects."""
    path = Path(path)
    if path == SOURCE or not path.is_relative_to(SOURCE):
        raise ValueError('Source outside fixed share')
    if any(c in str(path) for c in ("'", '\n', '\r', '\x00')):
        raise ValueError('Unsupported native pathname')
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError('Symlink source or parent')
        if parent == Path('/mnt/cache'): break
    info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_dev!=SOURCE.stat().st_dev:
        raise ValueError('Unsupported source file')
    return info


def sha256(path):
    fd=os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
    with os.fdopen(fd, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def destinations(path):
    relative=Path(path).relative_to('/mnt/cache')
    return [disk/relative for disk in array_disks() if (disk/relative).exists() or (disk/relative).is_symlink()]


def array_disks():
    md=dict(line.split('=',1) for line in Path('/proc/mdstat').read_text().splitlines() if '=' in line)
    if md.get('mdState')!='STARTED' or md.get('mdResync')!='0':
        raise ValueError('Array maintenance or unavailable')
    disks=[]
    for key,value in md.items():
        if re.fullmatch(r'rdevName\.\d+',key) and value:
            number=key.split('.')[1]
            if md.get('rdevStatus.'+number)!='DISK_OK' or md.get('rdevNumErrors.'+number)!='0':
                raise ValueError('Assigned disk health not verified')
            if int(number) not in (0,29):
                disk=Path('/mnt/disk'+number)
                if not os.path.ismount(disk): raise ValueError('Array disk not mounted')
                disks.append(disk)
    if not disks: raise ValueError('No array disks')
    return disks


def torrent_snapshot():
    items,mounts=read_snapshot('binhex-qbittorrentvpn',5)
    assess(items,mounts)  # Includes errored/unknown-state and missing-data rejection.
    converted=[]
    for mount in mounts:
        if mount.get('Type')=='bind' and mount.get('Source','').startswith('/mnt/'):
            # Physical cache bindings would break seed paths after movement.
            original=mount['Source']
            normalized=canonical(original)
            if within(ROOT,normalized) or within(normalized,ROOT):
                if not (original=='/mnt/user' or original.startswith('/mnt/user/')):
                    raise ValueError('Torrent uses a physical storage binding')
            mount=dict(mount,Source=normalized)
        converted.append(mount)
    for item in items:
        resolved=host_path(item.get('content_path'),converted)
        if canonical(resolved)!=resolved: raise ValueError('Unknown torrent namespace')
    return items,converted


def guards(owned=False):
    prior=read_json(LAST,{})
    if (prior.get('requires_inspection') is True or
        (not owned and (prior.get('state')=='running' or prior.get('active_file_started') is True))):
        raise ValueError('Previous movement requires inspection')
    runtime=read_json(BASE/'settings.json',{})
    if runtime.get('version')!=1 or runtime.get('mode')!='advanced' or runtime.get('pool')!='cache':
        raise ValueError('Advanced cache mode required')
    if not os.path.ismount('/mnt/cache') or not os.path.ismount('/mnt/user'):
        raise ValueError('Storage mount unavailable')
    if SOURCE.is_symlink() or not SOURCE.is_dir(): raise ValueError('Share unavailable')
    cfg=Path('/boot/config/shares/Filmek.cfg').read_text()
    for key,expected in [('shareUseCache','yes'),('shareCachePool','cache'),('shareCachePool2','')]:
        values=re.findall(r'^'+key+r'="([^"]*)"\s*$',cfg,re.M)
        if values!=[expected]: raise ValueError('Share direction changed')
    settings=Path('/boot/config/share.cfg').read_text()
    if re.findall(r'^shareUserEmptying="([^"]*)"\s*$',settings,re.M)!=['']:
        raise ValueError('Array emptying enabled or unverifiable')
    disks=array_disks()
    report=dry_run()
    checks={x['key']:x['state'] for x in report['dry_run']['checks']}
    result={key:checks.get(key,'unknown') for key in ('backup','parity','mover','cooldown','capacity')}
    if owned and PID.exists() and PID.read_text()==str(os.getpid()): result['mover']='pass'
    if checks.get('launcher')!='pass': raise ValueError('Legacy safety settings unavailable')
    launcher=Path('/boot/config/plugins/user.scripts/scripts/Filmek_Mover_Threshold/script').read_text()
    wait=re.findall(r'^UJRA_PROBALKOZAS_MP=([0-9]+)$',launcher,re.M)
    if len(wait)!=1: raise ValueError('Cooldown unavailable')
    if not owned and ATTEMPT.exists():
        last=ATTEMPT.read_text().strip()
        if not last.isdigit() or int(last)>time.time(): raise ValueError('Invalid selective timestamp')
        if time.time()-int(last)<int(wait[0])*60: result['cooldown']='wait'
    scrub=subprocess.check_output(['btrfs','scrub','status','/mnt/cache'],text=True,timeout=10)
    if not re.search(r'^Status:\s+finished$',scrub,re.M) or 'no errors found' not in scrub:
        raise ValueError('Cache scrub active or unhealthy')
    stats=subprocess.check_output(['btrfs','device','stats','/mnt/cache'],text=True,timeout=10)
    if not stats.strip() or any(not line.split()[-1].isdigit() or int(line.split()[-1]) for line in stats.splitlines()):
        raise ValueError('Cache device errors or unavailable')
    args=[]; integrity_scanning=False
    for entry in Path('/proc').glob('[0-9]*/cmdline'):
        try: values=entry.read_bytes().split(b'\0')
        except FileNotFoundError: continue
        if any(v.endswith(b'/bunker') for v in values):
            if owned: raise ValueError('Integrity hashing active')
            integrity_scanning=True
        args.append(values)
    watcher=b'/usr/local/emhttp/plugins/dynamix.file.integrity/scripts/watcher'
    for disk in disks:
        pipe=Path('/var/run/hash.pipe.'+disk.name)
        if not stat.S_ISFIFO(pipe.lstat().st_mode): raise ValueError('Integrity event pipe missing')
        if not any(watcher in a and disk.name.encode() in a for a in args):
            raise ValueError('Integrity listener missing')
        if not any(a and a[0].endswith(b'inotifywait') and str(pipe).encode() in a and str(disk).encode() in a for a in args):
            raise ValueError('Integrity event source missing')
    wired=report.get('integrity_config')=='wired' and report.get('integrity_active')=='wired'
    result.update(integrity=('wait' if integrity_scanning else 'pass') if wired else 'unknown',mount='pass',namespace='pass',open_files='pass')
    return result


def collect(update=False,owned=False):
    settings=read_json(CONFIG,{'version':1,'age_days':7})
    if settings.get('version')!=1: raise ValueError('Unknown configuration')
    days=age_days(settings.get('age_days'))
    target=ratio_target(settings.get('ratio_target',0))
    limit=batch_bytes(settings.get('batch_gib',16))
    previous=read_json(INVENTORY,{'version':1,'files':{}})
    if previous.get('version')!=1 or not isinstance(previous.get('files'),dict):
        raise ValueError('Unknown inventory')
    now=time.time()
    inventory_adapter.SOURCE=SOURCE
    files,current=inventory_adapter.inventory(now,previous['files'])
    items,mounts=torrent_snapshot()
    protection=guards(owned)
    selection=plan(files,items,mounts,protection,days=days,now=time.time(),observed_at=now,root=ROOT)
    selection['ratio_target']=target
    selection['max_bytes']=limit
    selection['candidates']=prioritize(selection['candidates'],items,mounts,target,
                                         sizes={key:current[key]['signature'][2] for key in selection['candidates']})
    if update:
        atomic_json(INVENTORY,{'version':1,'files':current})
        atomic_json(FORECAST,waiting_table(files,items,mounts,current,protection,
                                          days=days,now=time.time(),root=ROOT,target_ratio=target,max_bytes=limit))
    return selection,files,current,items,mounts,protection


def preview(update=False):
    selection,files,current,items,mounts,protection=collect(update)
    return {'execution_allowed':False,'live_movement':'available','age_days':selection['age_days'],
            'decision':selection['decision'],'candidate_count':len(selection['candidates']),
            'file_count':len(files),'skipped_counts':dict(Counter(x['reason'] for x in selection['skipped'])),
            'blockers':selection['blockers'],'guards':protection,'inventory_updated':update,
            'forecast':waiting_table(files,items,mounts,current,protection,
                                     days=selection['age_days'],now=time.time(),root=ROOT,target_ratio=selection['ratio_target'],max_bytes=selection['max_bytes'])}


def fresh_candidate(key,expected,days,owned=True):
    path=SOURCE/Path(key).relative_to(ROOT)
    info=valid_file(path)
    if signature(info)!=expected['signature']: raise ValueError('Source changed')
    opened=inventory_adapter.open_paths()
    items,mounts=torrent_snapshot()
    protection=guards(owned)
    now=time.time()
    item=dict(path=key,regular=True,symlink=False,nlink=info.st_nlink,open=key in opened,
              stable=True,mtime=info.st_mtime,first_seen=expected['first_seen'])
    selection=plan([item],items,mounts,protection,days=days,now=now,observed_at=now,root=ROOT)
    return path,selection['candidates']==[key]


def log(message):
    subprocess.run(['logger','-t','mover','Fejes selective: '+message],check=True,timeout=5)


def failure_code(error):
    """Expose a bounded failure category, never command arguments or private paths."""
    if isinstance(error, subprocess.CalledProcessError):
        command=error.cmd
        if (isinstance(command,(list,tuple)) and len(command)>=5 and
                command[:4]==['docker','exec','binhex-qbittorrentvpn','curl'] and
                command[-1]=='http://127.0.0.1:8080/api/v2/torrents/info'):
            return 'torrent_snapshot_unavailable'
    return 'required_state_unverified'


def record_failure(report, active_key=None):
    """Keep private exception evidence without weakening the inspection latch."""
    try:
        fd=os.open(str(LAST.parent/'selective-error.log'),os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'a') as stream:
            os.fchmod(stream.fileno(),0o600)
            stream.write('\nRun started='+str(report.get('started'))+' stage='+str(report.get('stage','preflight'))+'\n')
            if active_key is not None:
                stream.write('Active file='+json.dumps(active_key,ensure_ascii=True)+'\n')
            error=sys.exc_info()[1]
            code=getattr(error,'returncode',None)
            if isinstance(code,int):stream.write('Process exit='+str(code)+'\n')
            stderr=getattr(error,'stderr',None)
            if isinstance(stderr,bytes):stderr=stderr.decode('utf-8','replace')
            if isinstance(stderr,str) and stderr:stream.write('Process stderr='+json.dumps(stderr[-4096:],ensure_ascii=True)+'\n')
            traceback.print_exc(file=stream)
            stream.flush();os.fsync(stream.fileno())
    except (OSError,ValueError):
        # Diagnostic failure must never clear a failed movement or its latch.
        pass


class NativeMoveError(RuntimeError):
    """Keep native exit evidence private; callers still fail closed."""
    def __init__(self, returncode, stderr):
        super().__init__('Native movement failed; inspect private diagnostic log')
        self.returncode=returncode
        self.stderr=stderr


def execute_file(key,expected,days):
    path,eligible=fresh_candidate(key,expected,days)
    if not eligible: return {'state':'skipped','reason':'fresh_conditions_changed'}
    if destinations(path): return {'state':'skipped','reason':'existing_array_copy'}
    before=valid_file(path)
    attrs={key:os.getxattr(path,key) for key in os.listxattr(path)}
    checksum=sha256(path)
    path,eligible=fresh_candidate(key,expected,days)
    if not eligible: return {'state':'skipped','reason':'fresh_conditions_changed'}
    if destinations(path) or signature(path.stat())!=signature(before):
        return {'state':'skipped','reason':'source_or_destination_changed'}
    opened=subprocess.run(['fuser','-s',str(path)],capture_output=True)
    if opened.returncode==0: return {'state':'skipped','reason':'open_file'}
    if opened.returncode!=1: raise ValueError('Open-file state unavailable')
    # Exact single-file stdin; no find, shell expansion, user-share copy or rm.
    result=subprocess.run([ENGINE],input=str(path)+'\n',text=True,capture_output=True)
    if result.returncode!=0: raise NativeMoveError(result.returncode,result.stderr)
    if path.exists():
        if signature(path.stat())!=signature(before): raise RuntimeError('Retained source changed')
        return {'state':'skipped','reason':'native_retained_source'}
    targets=destinations(path)
    if len(targets)!=1: raise RuntimeError('Movement target could not be verified')
    target=targets[0]
    after=target.lstat()
    if not stat.S_ISREG(after.st_mode) or target.is_symlink(): raise RuntimeError('Invalid target')
    fd=os.open(target,os.O_RDONLY|os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)
    if sha256(target)!=checksum or sha256(Path(key))!=checksum:
        raise RuntimeError('Checksum mismatch; retained destination requires inspection')
    if (after.st_size,after.st_mtime_ns,after.st_uid,after.st_gid,stat.S_IMODE(after.st_mode))!=(
            before.st_size,before.st_mtime_ns,before.st_uid,before.st_gid,stat.S_IMODE(before.st_mode)):
        raise RuntimeError('Metadata mismatch; destination retained')
    if any(os.getxattr(target,key)!=value for key,value in attrs.items()):
        raise RuntimeError('Extended metadata mismatch; destination retained')
    return {'state':'moved','bytes':after.st_size,'sha256':checksum}


def run():
    report={'version':1,'state':'checking','started':time.time(),'moved_files':0,'moved_bytes':0,
            'skipped':{},'scope':'cache/Filmek -> Array; selected files only',
            'requires_inspection':False}
    locks=[]; own_pid=False; coordinated=False
    try:
        # Same ordering for every executor; no cron/settings rewrites.
        for name in ('fejes-mover-launch.lock','fejes-integrity-cron.lock','fejes-selective-inventory.lock'):
            lock=open('/var/run/'+name,'a'); locks.append(lock)
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        config_lock=open('/var/run/fejes-mover-config.lock','a');locks.append(config_lock)
        fcntl.flock(config_lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        coordinated=True
        # Read only after the previous owner has released all coordination locks.
        # A pre-lock snapshot could otherwise erase its newly recorded failure.
        prior=read_json(LAST,{})
        report['requires_inspection']=bool(prior.get('requires_inspection') or prior.get('state')=='running' or prior.get('active_file_started'))
        if report['requires_inspection']:
            raise ValueError('Previous movement requires inspection')
        if PID.exists(): raise ValueError('Mover PID already present')
        report['stage']='preflight_collection'
        selection,_,current,items,_,_=collect(True)
        report.update(age_days=selection['age_days'],candidate_count=len(selection['candidates']),blockers=selection['blockers'],
                      skipped=dict(Counter(x['reason'] for x in selection['skipped'])))
        if selection['blockers']:
            report['state']='deferred'; return report
        if not selection['candidates']:
            report['state']='nothing_eligible'; return report
        # Establish a real, observable selective wrapper process with native child.
        fd=os.open(PID,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        os.write(fd,str(os.getpid()).encode()); os.close(fd);own_pid=True
        report['state']='running';atomic_json(LAST,report)
        log(f'started; age={selection["age_days"]} days, candidates={len(selection["candidates"])}')
        limit=selection.get('max_bytes',MAX_BYTES)
        report['batch_bytes_limit']=limit
        skips=Counter(report['skipped'])
        for key in selection['candidates']:
            size=current[key]['signature'][2]
            if size>limit:
                skips['file_exceeds_batch_limit']+=1;continue
            if report['moved_files']>=MAX_FILES:
                skips['batch_file_limit']+=1;continue
            if report['moved_bytes']+size>limit:
                skips['batch_size_limit']+=1;continue
            report['stage']='file_verification_or_move'
            report['active_file_started']=True
            atomic_json(LAST,report)  # Durable intent before any native file operation.
            outcome=execute_file(key,current[key],selection['age_days'])
            report['active_file_started']=False
            if outcome['state']=='moved':
                report['moved_files']+=1;report['moved_bytes']+=outcome['bytes']
                log(f'verified file #{report["moved_files"]}, bytes={outcome["bytes"]}, sha256={outcome["sha256"]}')
            else: skips[outcome['reason']]+=1
            report['skipped']=dict(skips);atomic_json(LAST,report)
        # Trailing limit skips never reach the per-file write above.
        report['skipped']=dict(skips)
        final,_=torrent_snapshot()
        # Names/hashes remain private; publish only continuity booleans.
        pre={x['hash']:x for x in items};post={x['hash']:x for x in final}
        report['torrent_continuity']={'same_torrents':pre.keys()==post.keys(),
            'completed_still_complete':all(h in post and post[h]['progress']==1 for h,x in pre.items() if x['progress']==1),
            'completed_in_seed_states':all(h in post and post[h]['state'] in {'uploading','stalledUP','queuedUP','forcedUP','stoppedUP','pausedUP'} for h,x in pre.items() if x['progress']==1),
            'paths_unchanged':all(h in post and post[h]['content_path']==x['content_path'] for h,x in pre.items())}
        if not all(report['torrent_continuity'].values()): raise RuntimeError('Torrent continuity changed; inspect before next run')
        report['state']='completed' if report['moved_files'] else 'no_files_moved'
        if report['moved_files']: atomic_json(ATTEMPT,int(time.time()))
        log(f'finished; verified files={report["moved_files"]}, bytes={report["moved_bytes"]}')
    except BlockingIOError:
        record_failure(report, locals().get('key'))
        # Lock contention before launch is different from EAGAIN during file I/O.
        if report['state']=='checking':
            return {'state':'deferred','reason':'another_operation_active','moved_files':0}
        report['state']='error'
        report['error']='File operation unavailable; inspect before another run.'
        report['requires_inspection']=bool(report['requires_inspection'] or report.get('active_file_started') or report['moved_files'])
    except ERRORS as error:
        report['error_code']=failure_code(error)
        record_failure(report, locals().get('key'))
        report['state']='error';report['error']='Required state changed or could not be verified. No further files will be started; inspect selective-error.log in the private plugin configuration directory.'
        report['requires_inspection']=bool(report['requires_inspection'] or report.get('active_file_started') or report['moved_files'])
    finally:
        if own_pid and PID.exists() and PID.read_text()==str(os.getpid()): PID.unlink()
        report['finished']=time.time()
        if coordinated and report['state']!='checking': atomic_json(LAST,report)
        for lock in reversed(locks): lock.close()
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['preview','observe','start','run','status'])
    args=parser.parse_args()
    try:
        if args.action=='start':
            fd=os.open('/var/log/fejes-mover-selective.log',os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'a') as logfile:
                child=subprocess.Popen([os.sys.executable,str(Path(__file__).resolve()),'run'],
                    stdin=subprocess.DEVNULL,stdout=logfile,stderr=subprocess.STDOUT,
                    start_new_session=True,close_fds=True)
            output={'state':'requested','pid':child.pid,'message':'The worker will recheck every guard before movement.'}
        elif args.action=='run': output=run()
        elif args.action=='status': output=read_json(LAST,{'state':'not_run'})
        else:
            with open('/var/run/fejes-selective-inventory.lock','a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                output=preview(args.action=='observe')
        print(json.dumps(output,allow_nan=False))
        return 20 if output.get('state')=='error' else 0
    except ERRORS:
        print(json.dumps({'execution_allowed':False,'decision':'unknown','error':'Required state could not be verified'}))
        return 20


if __name__=='__main__': raise SystemExit(main())
