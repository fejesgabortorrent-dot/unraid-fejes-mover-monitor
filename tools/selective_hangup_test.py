"""A directly launched worker must survive loss of its diagnostic terminal."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import unittest


@unittest.skipUnless(hasattr(signal, 'SIGHUP'), 'POSIX terminal hangup required')
class TerminalHangup(unittest.TestCase):
    def test_owned_worker_ignores_hangup_before_dispatch(self):
        program = '''
from test_support import install
install()
import selective_mover as n
import os,signal,sys
def work():
    os.kill(os.getpid(),signal.SIGHUP)
    return {'state':'completed','hangup_survived':True}
n.run_configured=work
sys.argv=['selective_mover.py','run']
raise SystemExit(n.main())
'''
        result = subprocess.run([sys.executable,'-B','-c',program],
            cwd=Path(__file__).resolve().parent, capture_output=True,text=True,
            timeout=10,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('"hangup_survived": true',result.stdout)
