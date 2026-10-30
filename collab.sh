#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
# Windows can expose a python3 app-execution alias that exists but cannot run Python.
if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1; then
  exec python3 scripts/collab.py "$@"
fi
if command -v python >/dev/null 2>&1 && python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1; then
  exec python scripts/collab.py "$@"
fi
printf '%s\n' 'A working Python 3.11+ interpreter is required.' >&2
exit 2
