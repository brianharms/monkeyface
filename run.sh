#!/usr/bin/env bash
# Run Project Monkeyface locally. Creates a virtualenv on first run, installs
# deps, and serves the tool at http://localhost:8000.
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  # The pinned numpy/pandas need Python 3.11 or 3.12 (no wheels for 3.13/3.14
  # yet). Pick the newest compatible interpreter that's installed.
  PY=""
  for cand in python3.12 python3.11; do
    if command -v "$cand" >/dev/null 2>&1; then PY="$cand"; break; fi
  done
  # Fall back to plain python3 only if it's 3.11 or 3.12.
  if [ -z "$PY" ] && command -v python3 >/dev/null 2>&1; then
    ver="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
    case "$ver" in 3.11|3.12) PY="python3" ;; esac
  fi
  if [ -z "$PY" ]; then
    echo "ERROR: need Python 3.11 or 3.12 (the pinned numpy/pandas don't build on 3.13+)."
    echo "Install one, e.g.:  brew install python@3.12   (macOS)"
    echo "Then re-run ./run.sh"
    exit 1
  fi
  echo "Creating virtualenv with $PY ..."
  "$PY" -m venv .venv
  ./.venv/bin/pip install -q --upgrade pip
  ./.venv/bin/pip install -q -r requirements.txt
fi

echo "Project Monkeyface running at http://localhost:8000  (Ctrl-C to stop)"
# Open a browser if we can (macOS = open, Linux = xdg-open); harmless if neither.
( sleep 1
  if command -v open >/dev/null 2>&1; then open http://localhost:8000
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open http://localhost:8000
  fi ) &
exec ./.venv/bin/uvicorn monkeyface.app:app --port 8000 --reload
