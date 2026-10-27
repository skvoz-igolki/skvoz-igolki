"""Run compact layout and atomic cart-clear scenarios over file:// and local HTTPS."""
import os
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
subprocess.run([sys.executable,str(root/'tests/cart_order_check.py')],cwd=root,
    env=dict(os.environ,SKVOZ_ORDER_SCENARIO='responsive_scenarios.py'),check=True)
