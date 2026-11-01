"""Install test tripwires even when executor tests are invoked without the wrapper."""
import os
from pathlib import Path
from .sitecustomize import install as install_hook


def install():
    install_hook()
    os.environ['FEJES_ISOLATED_TEST']='1'
    support=str(Path(__file__).resolve().parent)
    paths=os.environ.get('PYTHONPATH','').split(os.pathsep)
    if support not in paths:os.environ['PYTHONPATH']=os.pathsep.join([support,*paths])
