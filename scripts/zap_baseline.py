#!/usr/bin/env python3
"""Run OWASP ZAP baseline scan against the local server."""
import subprocess
import sys

cmd = [
    "zap-baseline.py",
    "-t",
    "http://localhost:8000",
    "-r",
    "zap_report.html",
]

try:
    subprocess.run(cmd, check=True)
except subprocess.CalledProcessError as exc:
    print(f"ZAP baseline scan failed: {exc}")
    sys.exit(exc.returncode)
