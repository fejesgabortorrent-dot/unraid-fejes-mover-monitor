#!/usr/bin/env python3
"""Private read-only qBittorrent demand sampler. Never changes torrents or files."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time
import fcntl
from torrent_preflight import read_snapshot, assess
from selective_preview import read_json, atomic_json

WINDOW=1800
MAX_GAP=3600
HISTORY=86400
MIN_BYTES=64*1024**2


def advance(state,torrents,mounts,generation,now):
    """Non-overlapping windows. Return new state only after full validation."""
    assess(torrents,mounts)
    if type(now) not in (int,float) or not math.isfinite(now) or now<0:
        raise ValueError('Invalid observation time')
    if not isinstance(generation,str) or not generation or not isinstance(state,dict) or state.get('version')!=1 or not isinstance(state.get('items'),dict):
        raise ValueError('Unknown observation state')
    result={'version':1,'observed_at':now,'items':{}}
    for torrent in torrents:
        identity=torrent.get('hash');uploaded=torrent.get('uploaded')
        if not isinstance(identity,str) or len(identity) not in (40,64) or any(c not in '0123456789abcdefABCDEF' for c in identity):
            raise ValueError('Unknown torrent identity')
        if type(uploaded) is not int or uploaded<0:raise ValueError('Unknown upload counter')
        key=hashlib.sha256(identity.lower().encode()).hexdigest()
        if key in result['items']:raise ValueError('Duplicate identity')
        old=state['items'].get(key)
        fresh={'generation':generation,'anchor_at':now,'anchor_uploaded':uploaded,'last_at':now,'last_uploaded':uploaded,'windows':[]}
        if old is not None:
            if not isinstance(old,dict):raise ValueError('Invalid saved item')
            for field in ('anchor_at','anchor_uploaded','last_at','last_uploaded'):
                value=old.get(field)
                if type(value) not in (int,float) or not math.isfinite(value) or value<0:raise ValueError('Invalid saved counter')
            if not isinstance(old.get('windows'),list):raise ValueError('Invalid saved windows')
            windows=[]
            for event in old['windows']:
                if not isinstance(event,dict) or type(event.get('at')) not in (int,float) or not math.isfinite(event['at']) or type(event.get('bytes')) is not int or event['bytes']<0 or not 0<=event['at']<=now:
                    raise ValueError('Invalid saved window')
                if now-event['at']<=HISTORY:windows.append(event)
            gap=now-old['last_at'];elapsed=now-old['anchor_at']
            if old.get('generation')==generation and 0<=gap<=MAX_GAP and 0<=elapsed<=MAX_GAP and uploaded>=old['last_uploaded']>=old['anchor_uploaded']:
                fresh.update(anchor_at=old['anchor_at'],anchor_uploaded=old['anchor_uploaded'],windows=windows)
                if elapsed>=WINDOW:
                    fresh['windows'].append({'at':now,'bytes':uploaded-old['anchor_uploaded']})
                    fresh.update(anchor_at=now,anchor_uploaded=uploaded)
        result['items'][key]=fresh
    return result


def summary(state):
    counts=[sum(w['bytes']>=MIN_BYTES for w in item['windows']) for item in state['items'].values()]
    return {'read_only':True,'execution_allowed':False,'observed_at':state['observed_at'],
            'observed_torrents':len(counts),'recurring_demand_torrents':sum(n>=2 for n in counts),
            'minimum_window_bytes':MIN_BYTES,'window_seconds':WINDOW,
            'note':'Demand only; not a file placement or tracker-compliance decision.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state',type=Path,required=True,help='Private persistent state file; no names or paths are retained')
    args=parser.parse_args()
    try:
        if args.state.is_symlink() or not args.state.parent.is_dir():raise ValueError('Unsafe state location')
        with open(str(args.state)+'.lock','a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            generation=subprocess.check_output(['docker','inspect','--format','{{.State.StartedAt}}','binhex-qbittorrentvpn'],text=True,timeout=5).strip()
            torrents,mounts=read_snapshot('binhex-qbittorrentvpn',5)
            state=advance(read_json(args.state,{'version':1,'items':{}}),torrents,mounts,generation,time.time())
            atomic_json(args.state,state)
            print(json.dumps(summary(state),allow_nan=False))
        return 0
    except (OSError,ValueError,TypeError,KeyError,AttributeError,subprocess.SubprocessError):
        print(json.dumps({'read_only':True,'execution_allowed':False,'state':'unknown','state_updated':False}))
        return 20

if __name__=='__main__':raise SystemExit(main())
