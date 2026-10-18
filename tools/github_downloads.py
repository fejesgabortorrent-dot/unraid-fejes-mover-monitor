"""Owner-side GitHub release asset counter. No public NAS endpoint or secrets."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import urllib.request

REPO = 'fejesgabortorrent-dot/unraid-fejes-mover-monitor'
ASSET = 'fejes.mover.monitor.plg'


def fetch_page(page):
    request = urllib.request.Request(
        f'https://api.github.com/repos/{REPO}/releases?per_page=100&page={page}',
        headers={'Accept':'application/vnd.github+json','User-Agent':'FejesMover-download-counter'})
    with urllib.request.urlopen(request, timeout=15) as response:
        body = response.read(2_000_001)
        if len(body)>2_000_000:
            raise ValueError('Response too large')
        return json.loads(body)


def snapshot(fetch=fetch_page):
    assets = {}
    for page in range(1,11):
        releases = fetch(page)
        if not isinstance(releases,list):
            raise ValueError('Invalid releases')
        for release in releases:
            if release.get('draft'):
                continue
            for asset in release.get('assets',[]):
                if asset.get('name') != ASSET:
                    continue
                ident,count = asset.get('id'),asset.get('download_count')
                if type(ident) is not int or type(count) is not int or count<0:
                    raise ValueError('Invalid asset count')
                assets[str(ident)] = count
        if len(releases)<100:
            return {'assets':assets,'total':sum(assets.values())}
    raise ValueError('Pagination limit reached; refusing partial total')


def notify(total, delta, test=False, run=subprocess.run):
    subject = 'Fejes Mover: letöltésszámláló próba' if test else 'Fejes Mover: új GitHub-letöltés'
    description = f'Összes telepítőletöltés: {total}; növekedés: +{delta}. Letöltések, nem egyedi telepítések.'
    run(['/usr/local/emhttp/plugins/dynamix/scripts/notify', '-e','FejesMover GitHub Downloads',
         '-s',subject,'-d',description,'-i','normal 4'], check=True,timeout=45,capture_output=True)


def update(state_path, fetch=fetch_page, send=notify, test=False):
    import fcntl
    path=Path(state_path)
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    with open(str(path)+'.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        current=snapshot(fetch)
        try:
            previous=json.loads(path.read_text())
            if not isinstance(previous,dict) or type(previous.get('total')) is not int:
                raise ValueError('Invalid saved baseline')
        except FileNotFoundError:
            previous=None
        delta=max(0,current['total']-previous['total']) if previous else 0
        if test or delta:
            send(current['total'],delta,test=test)
        # On API/notify failure keep baseline unchanged, so the next run retries.
        fd,tmp=tempfile.mkstemp(prefix='.downloads-',dir=path.parent)
        try:
            with os.fdopen(fd,'w') as out:
                json.dump(current,out)
                out.flush()
                os.fsync(out.fileno())
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return dict(current,delta=delta,baseline=previous is None)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--state',default='/boot/config/plugins/fejes.mover.monitor/github-downloads.json')
    parser.add_argument('--test',action='store_true',help='Send one clearly labelled test notice')
    args=parser.parse_args()
    try:
        result=update(args.state,test=args.test)
        print('GitHub installer downloads:',result['total'],'change:',result['delta'])
    except Exception:
        raise SystemExit('Download counter failed; baseline not advanced. Check connectivity/configuration.')
