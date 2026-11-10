"""The suite must fail rather than hide test tracebacks in the production log."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


class IsolationTripwire(unittest.TestCase):
    def test_production_writes_and_commands_are_rejected_in_child(self):
        wrapper=Path(__file__).with_name('isolated_test.py')
        for source in ("open('/boot/config/plugins/fejes.mover.monitor/selective-error.log','a')",
                       "import os;os.rename('/tmp/fixture','/mnt/cache/fixture')",
                       "import subprocess;subprocess.run(['docker','ps'])",
                       "import subprocess;subprocess.run(['/usr/libexec/unraid/move'])"):
            result=subprocess.run([sys.executable,str(wrapper),'-c',source],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('TestIsolationViolation',result.stderr)

    def test_diagnostic_exceptions_cannot_swallow_the_tripwire(self):
        source="""import sys
sys.path.insert(0,'tools')
import selective_mover as mover
try:raise ValueError('fixture')
except ValueError:mover.record_failure({})
"""
        if os.name=='nt':self.skipTest('Linux fcntl required')
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('isolated_test.py')),'-c',source],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('TestIsolationViolation',result.stderr)


if __name__=='__main__':unittest.main()
