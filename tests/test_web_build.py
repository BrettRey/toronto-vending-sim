"""The committed web page must match what scripts/build_web.py produces from data/."""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class WebBuildTests(unittest.TestCase):
    def test_index_html_is_current(self):
        if not (ROOT / "web" / "template.html").exists():
            self.skipTest("no web template yet")
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_web.py"), "--check"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
