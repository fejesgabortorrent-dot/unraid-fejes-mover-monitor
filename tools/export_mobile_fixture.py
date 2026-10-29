"""Render actual localized pages with the existing disposable browser fixtures."""
from pathlib import Path
import sys
import tempfile
from browser_demo import Demo

destination=Path(sys.argv[1]);destination.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='fejes-mobile-') as folder:
    demo=Demo(Path(folder))
    for language in ('hu','en','de'):
        for name in ('FejesMover.page','FejesMoverSelective.page','FejesMoverSettings.page','FejesMoverSetup.page'):
            body=demo.render(name,'idle',language,None)
            document='<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;font:16px Arial}</style>'+body+'</html>'
            (destination/(language+'-'+name+'.html')).write_text(document,encoding='utf-8')
