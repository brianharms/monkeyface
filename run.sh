#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3.11 -m venv .venv
  ./.venv/bin/pip install -q -r requirements.txt
fi
echo "monkeyface running at http://localhost:8000  (Ctrl-C to stop)"
( sleep 1 && open http://localhost:8000 ) &
exec ./.venv/bin/uvicorn monkeyface.app:app --port 8000 --reload
