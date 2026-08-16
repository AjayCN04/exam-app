#!/usr/bin/env bash
# Starts the exam app locally and opens a public ngrok tunnel to it.
# Usage: scripts/local_start.sh
set -euo pipefail
cd "$(dirname "$0")/.."

RUN_DIR=".run"
mkdir -p "$RUN_DIR"

is_running() {
  [ -f "$RUN_DIR/$1.pid" ] && kill -0 "$(cat "$RUN_DIR/$1.pid")" 2>/dev/null
}

if is_running gunicorn || is_running ngrok || lsof -i :5000 >/dev/null 2>&1; then
  echo "Something is already using port 5000 or a previous run is still active."
  echo "Run scripts/local_stop.sh first, then try again."
  exit 1
fi

if ! command -v ngrok >/dev/null 2>&1; then
  echo "ngrok is not installed. Install it with: brew install ngrok"
  exit 1
fi

# Start ngrok FIRST. It opens the tunnel and hands out a public URL immediately,
# even before the local app is listening — it just returns 502s until the app
# comes up. This avoids ever having to restart gunicorn to fix up BASE_URL.
echo "Opening ngrok tunnel ..."
: > "$RUN_DIR/ngrok.log"
nohup ngrok http 127.0.0.1:5000 --log=stdout >> "$RUN_DIR/ngrok.log" 2>&1 &
echo $! > "$RUN_DIR/ngrok.pid"

PUBLIC_URL=""
for _ in $(seq 1 15); do
  PUBLIC_URL=$(curl -sS http://127.0.0.1:4040/api/tunnels 2>/dev/null \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['tunnels'][0]['public_url'])" 2>/dev/null || true)
  [ -n "$PUBLIC_URL" ] && break
  sleep 1
done

if [ -z "$PUBLIC_URL" ]; then
  echo "Could not read the ngrok URL — check .run/ngrok.log"
  exit 1
fi

echo "Starting app server on 0.0.0.0:5000 (localhost + LAN + ngrok) ..."
: > "$RUN_DIR/gunicorn.log"
BASE_URL="$PUBLIC_URL" nohup .venv/bin/gunicorn "app:create_app()" --bind 0.0.0.0:5000 --workers 3 \
  --log-level info >> "$RUN_DIR/gunicorn.log" 2>&1 &
echo $! > "$RUN_DIR/gunicorn.pid"

# Confirm the app actually came up before declaring success.
UP=""
for _ in $(seq 1 15); do
  if curl -sS -m 2 -o /dev/null http://127.0.0.1:5000/admin/login 2>/dev/null; then
    UP=1
    break
  fi
  sleep 1
done

if [ -z "$UP" ]; then
  echo "App did not come up — check .run/gunicorn.log"
  exit 1
fi

echo "$PUBLIC_URL" > "$RUN_DIR/public_url.txt"

LAN_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)

echo ""
echo "================================================================"
echo " Exam app is live."
echo " Public URL (ngrok, share anywhere): $PUBLIC_URL"
echo " Admin login:                        $PUBLIC_URL/admin/login"
if [ -n "$LAN_IP" ]; then
echo " LAN URL (same WiFi/network only):   http://$LAN_IP:5000"
echo " LAN admin login:                    http://$LAN_IP:5000/admin/login"
else
echo " LAN URL: could not detect a LAN IP (no en0/en1 interface found)"
fi
echo "================================================================"
echo "Run scripts/local_stop.sh to shut it down."
