"""Build a private, offline HTML report from owner-collected GitHub snapshots.

Counts only release assets named fejes.mover.monitor.plg. The first observation is
an unknown historical baseline; monthly changes become available over time.
"""
import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import tempfile
import os
from github_downloads import snapshot


def record(history, current, now):
    if not isinstance(history, list):
        raise ValueError('Invalid history')
    total = current['total']
    if type(total) is not int or total < 0:
        raise ValueError('Invalid total')
    day = now.astimezone(timezone.utc).date().isoformat()
    out = list(history)
    if out and day < out[-1]['date']:
        raise ValueError('Clock moved backwards')
    row = {'date': day, 'total': total}
    if out and out[-1]['date'] == day:
        out[-1] = row
    else:
        out.append(row)
    return out


def render(history):
    rows = []
    for item in history:
        d, n = item['date'], item['total']
        datetime.strptime(d, '%Y-%m-%d')
        if type(n) is not int or n < 0:
            raise ValueError('Invalid history value')
        rows.append((d, n))
    if any(rows[i][0] >= rows[i+1][0] for i in range(len(rows)-1)):
        raise ValueError('History dates must increase')
    latest = rows[-1][1] if rows else '–'
    ymax = max((n for _, n in rows), default=0) or 1
    points = ' '.join(f'{30 + i*700/max(len(rows)-1,1):.1f},{185 - n*145/ymax:.1f}' for i,(_,n) in enumerate(rows))
    table = ''.join(f'<tr><td>{html.escape(d)}</td><td>{n}</td></tr>' for d,n in reversed(rows))
    chart = f'<svg viewBox="0 0 760 220" role="img" aria-label="Összes letöltés időbeli alakulása"><line x1="30" y1="185" x2="730" y2="185" stroke="currentColor" opacity=".3"/><polyline points="{points}" fill="none" stroke="#ff8c24" stroke-width="4"/><text x="30" y="210" fill="currentColor">{html.escape(rows[0][0])}</text><text x="730" y="210" text-anchor="end" fill="currentColor">{html.escape(rows[-1][0])}</text></svg>' if rows else '<p>Még nincs adat.</p>'
    monthly = []
    for i in range(1, len(rows)):
        # Only compare actual observations; no claim of a full calendar month.
        start, end = rows[i-1], rows[i]
        monthly.append(f'<tr><td>{html.escape(start[0])} – {html.escape(end[0])}</td><td>{end[1]-start[1]:+d}</td></tr>')
    intervals = ''.join(reversed(monthly)) or '<tr><td colspan="2">Legalább két külön napi mérés szükséges.</td></tr>'
    return f'''<!doctype html><html lang="hu"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fejes Mover · Letöltési trend</title><style>:root{{color-scheme:light dark;font-family:system-ui,sans-serif}}body{{max-width:900px;margin:2rem auto;padding:0 1rem}}section{{border:1px solid #8886;border-radius:14px;padding:1.2rem;margin:1rem 0}}strong{{font-size:2.4rem;color:#e87300}}svg{{width:100%;height:auto}}table{{border-collapse:collapse;width:100%}}td,th{{padding:.5rem;text-align:left;border-bottom:1px solid #8885}}.muted{{opacity:.8}}</style><h1>Fejes Mover · Letöltési trend</h1><p class="muted">GitHub-kiadások telepítőfájljai · privát, helyi jelentés</p><section><div>Összes mért telepítőletöltés</div><strong>{latest}</strong><p>Letöltések, nem egyedi telepítések. A Community Applications és más források adatai nem szerepelnek itt.</p></section><section><h2>Összes letöltés alakulása</h2>{chart}<p>Az első mérés a korábbi összesítés; a korábbi hónapok nem állíthatók vissza ebből. Csökkenés lehetséges, ha egy kiadási fájlt törölnek.</p></section><section><h2>Változás a mérések között</h2><p>Az időszakok a tényleges mérési napokhoz igazodnak; nem jelentenek teljes naptári hónapot.</p><table><thead><tr><th>Időszak (UTC)</th><th>Változás</th></tr></thead><tbody>{intervals}</tbody></table></section><section><h2>Mérések</h2><table><thead><tr><th>Dátum (UTC)</th><th>Összesen</th></tr></thead><tbody>{table}</tbody></table></section></html>'''


def atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.trends-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--history', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.history.resolve() == args.output.resolve():
        p.error('History and output must be different files')
    import fcntl
    args.history.parent.mkdir(parents=True, exist_ok=True)
    with open(str(args.history)+'.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            history = json.loads(args.history.read_text(encoding='utf-8'))
        except FileNotFoundError:
            history = []
        updated = record(history, snapshot(), datetime.now(timezone.utc))
        page = render(updated)
        atomic(args.history, json.dumps(updated, ensure_ascii=False, indent=2)+'\n')
        atomic(args.output, page)


if __name__ == '__main__':
    main()
