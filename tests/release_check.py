"""Isolated immutable-cache update and clean-route integration checks."""
import os, shutil, subprocess, tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='skvoz-release-',ignore_cleanup_errors=True) as temp:
    site=Path(temp)
    for p in root.iterdir():
        if p.is_file() and p.suffix in ['.js','.html','.css','.ico','.png','.webp']: shutil.copy2(p,site/p.name)
    shutil.copytree(root/'assets',site/'assets')
    subprocess.run(['python',str(root/'tests/cart_order_check.py')],check=True,env=dict(os.environ,SKVOZ_SITE_ROOT=temp,SKVOZ_ORDER_SCENARIO='release_scenarios.py'))
