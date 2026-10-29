"""Run a Python test entry point with disposable temp storage and audit tripwires."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    if len(sys.argv)<2:raise SystemExit('Usage: isolated_test.py <script.py | -m module> [args]')
    with tempfile.TemporaryDirectory(prefix='fejes-isolated-') as directory:
        env=dict(os.environ,FEJES_ISOLATED_TEST='1',TMPDIR=directory,TEMP=directory,TMP=directory)
        support=str(Path(__file__).resolve().parent/'test_support')
        env['PYTHONPATH']=support+os.pathsep+env.get('PYTHONPATH','')
        return subprocess.run([sys.executable,*sys.argv[1:]],env=env).returncode


if __name__=='__main__':raise SystemExit(main())
