#!/usr/bin/env bash
# HomeAuto runner for Raspberry Pi OS.
# Builds the React UI (if needed) and serves UI + API from ONE process on port 8000.
#
# Usage:  ./runner.sh              real GPIO, serves on 0.0.0.0:8000 (reachable from your LAN)
#         ./runner.sh --mock       fake GPIO (no wiring needed; UI shows Trigger/Clear buttons)
#         ./runner.sh --rebuild    force a frontend rebuild
#         PORT=8080 ./runner.sh    use another port
# First time:  chmod +x runner.sh
# Stop with Ctrl+C.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${PORT:-8000}"
MOCK=0
REBUILD=0
for arg in "$@"; do
  case "$arg" in
    --mock)    MOCK=1 ;;
    --rebuild) REBUILD=1 ;;
    -h|--help) sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "[error] unknown option: $arg (try --help)" >&2; exit 1 ;;
  esac
done

command -v python3 >/dev/null || { echo "[error] python3 not found" >&2; exit 1; }

# ---- backend environment ---------------------------------------------------
# --system-site-packages lets the venv use Raspberry Pi OS's own python3-lgpio
# (the Pi 5 GPIO backend), which is hard to build with pip.
VENV="$ROOT/backend/.venv"
if [ ! -x "$VENV/bin/python" ]; then
  echo "[setup] creating backend virtual environment..."
  python3 -m venv --system-site-packages "$VENV"
  "$VENV/bin/python" -m pip install -q -r "$ROOT/backend/requirements.txt"
fi

if [ "$MOCK" -eq 0 ] && ! "$VENV/bin/python" -c "import lgpio" 2>/dev/null; then
  echo "[error] lgpio (Pi 5 GPIO backend) is missing. Run:" >&2
  echo "        sudo apt install python3-lgpio" >&2
  echo "        rm -rf backend/.venv && ./runner.sh" >&2
  exit 1
fi

# ---- frontend build --------------------------------------------------------
DIST="$ROOT/frontend/dist"
needs_build() {
  [ "$REBUILD" -eq 1 ] && return 0
  [ -f "$DIST/index.html" ] || return 0
  # any source newer than the last build?
  find "$ROOT/frontend/src" "$ROOT/frontend/index.html" "$ROOT/frontend/package.json" \
       -newer "$DIST/index.html" 2>/dev/null | grep -q .
}

if needs_build; then
  if command -v npm >/dev/null; then
    echo "[build] building frontend..."
    ( cd "$ROOT/frontend"
      [ -d node_modules ] || npm install
      npm run build )
  elif [ -f "$DIST/index.html" ]; then
    echo "[warn] npm not found; serving the existing frontend/dist"
  else
    echo "[error] no frontend/dist and npm is not installed." >&2
    echo "        Either: sudo apt install nodejs npm   (then rerun)" >&2
    echo "        or build on your PC (npm run build) and copy frontend/dist here." >&2
    exit 1
  fi
fi

# ---- run -------------------------------------------------------------------
if [ "$MOCK" -eq 1 ]; then
  export HOMEAUTO_MOCK=1
  echo "[mode] MOCK GPIO (no real sensors)"
else
  echo "[mode] real GPIO"
fi

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo "[start] http://localhost:$PORT${IP:+   or   http://$IP:$PORT (from your network)}"
echo "[note]  no authentication: only use on a trusted network"

cd "$ROOT/backend"
exec "$VENV/bin/python" -m uvicorn homeauto.api:app --host 0.0.0.0 --port "$PORT"
