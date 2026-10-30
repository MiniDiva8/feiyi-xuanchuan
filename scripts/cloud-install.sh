#!/usr/bin/env bash
# Paste "bash scripts/cloud-install.sh" into the environment install instructions.
# This is a repo script, not an automatic Cloud provisioning API.
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
python3 -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ is required"; print("Python runtime ready")'
git --version
python3 -c 'import re,subprocess; v=tuple(map(int,re.search(r"(\d+)\.(\d+)",subprocess.check_output(["git","--version"],text=True)).groups())); assert v >= (2,38), "Git 2.38+ is required"; print("Git merge-tree supported")'
if command -v gh >/dev/null 2>&1; then
  gh --version
else
  echo "GitHub CLI is unavailable: use native GitHub/PR tools, or install CLI from its official source."
fi
python3 -m unittest discover -s tests -v
