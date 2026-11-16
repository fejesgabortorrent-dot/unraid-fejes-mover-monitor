#!/usr/bin/env python3
import ast
from pathlib import Path
import re
import unittest

src=Path(__file__).with_name('selective_mover.py')
tree=ast.parse(src.read_text())
functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='cooldown_duration_seconds']
assert len(functions)==1
ns={'re':re}
exec(compile(ast.Module(body=functions,type_ignores=[]),str(src),'exec'),ns)
cooldown=ns['cooldown_duration_seconds']

class CooldownUnits(unittest.TestCase):
    def test_legacy_seconds(self):
        self.assertEqual(cooldown(None,'UJRA_PROBALKOZAS_MP=360\n'),360)
        self.assertEqual(cooldown(None,'UJRA_PROBALKOZAS_MP=900\n'),900)
    def test_managed_minutes(self):
        self.assertEqual(cooldown({'enabled':True,'cooldown_minutes':6},None),360)
    def test_invalid_configuration_fails_closed(self):
        for x in ('','UJRA_PROBALKOZAS_MP=360\nUJRA_PROBALKOZAS_MP=60\n','UJRA_PROBALKOZAS_MP=999999\n'):
            with self.subTest(x=x),self.assertRaises(ValueError):cooldown(None,x)
        for x in (True,6.5,-1,2000):
            with self.subTest(x=x),self.assertRaises(ValueError):
                cooldown({'enabled':True,'cooldown_minutes':x},None)
        with self.assertRaises(ValueError):
            cooldown({'enabled':False,'cooldown_minutes':6},None)

if __name__=='__main__':
    unittest.main()
