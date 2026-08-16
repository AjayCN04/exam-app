#!/usr/bin/env bash
# Stops the local app server and ngrok tunnel started by scripts/local_start.sh.
set -euo pipefail
cd "$(dirname "$0")/.."

RUN_DIR=".run"

stop_pid() {
  local name="$1"
  local pid_file="$RUN_DIR/$name.pid"
  if [ ! -f "$pid_file" ]; then
    echo "$name was not running"
    return
  fi
  local pid
  pid=$(cat "$pid_file")
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "$name was not running"
    rm -f "$pid_file"
    return
  fi
  kill "$pid" 2>/dev/null || true
  # Wait for a graceful exit (gunicorn drains workers) before giving up.
  for _ in $(seq 1 10); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 1
  done
  if kill -0 "$pid" 2>/dev/null; then
    echo "$name (pid $pid) did not stop gracefully, forcing it"
    kill -9 "$pid" 2>/dev/null || true
  fi
  echo "Stopped $name (pid $pid)"
  rm -f "$pid_file"
}

stop_pid gunicorn
stop_pid ngrok

# Belt and suspenders: nothing should be left on port 5000.
if lsof -i :5000 >/dev/null 2>&1; then
  echo "Warning: something is still listening on port 5000 — check manually with: lsof -i :5000"
fi

rm -f "$RUN_DIR/public_url.txt"
echo "Done."
