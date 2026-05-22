#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

# Activate Python venv
source "$ROOT/.venv/bin/activate"

echo "Starting FastAPI on :8000 ..."
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

echo "Starting React dev server on :5173 ..."
cd "$ROOT/web" && npm run dev &
WEB_PID=$!

# Kill both on Ctrl-C
trap "kill $API_PID $WEB_PID 2>/dev/null; exit 0" INT TERM
echo ""
echo "  Backend  → http://localhost:8000"
echo "  Frontend → http://localhost:5173"
echo ""
echo "Press Ctrl-C to stop both servers."
wait
