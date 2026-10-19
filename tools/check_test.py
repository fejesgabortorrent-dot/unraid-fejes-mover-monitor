"""Corrupt generated artifacts only in a disposable copy and require rejection."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='fejes-stale-check-') as directory:
    lab = Path(directory)
    for name in ['src', 'tools']:
        shutil.copytree(root / name, lab / name)
    for name in ['fejes.mover.monitor.plg', 'SHA256SUMS', 'icon.svg', 'icon.png']:
        shutil.copy2(root / name, lab / name)
    originals = {name: (lab / name).read_bytes() for name in ['fejes.mover.monitor.plg', 'SHA256SUMS']}
    for name in originals:
        target = lab / name
        target.write_bytes(originals[name] + b'corrupt\n')
        before = {p: (lab / p).read_bytes() for p in originals}
        result = subprocess.run([sys.executable, str(lab / 'tools/check.py')], capture_output=True, text=True)
        assert result.returncode != 0 and f'Generated {name} is stale' in result.stderr, result.stderr
        assert before == {p: (lab / p).read_bytes() for p in originals}, 'Check must preserve input evidence'
        target.write_bytes(originals[name])
        print(f'PASS: stale {name} rejected and both original artifacts preserved')
