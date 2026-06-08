#!/usr/bin/env bash
# Capture the 10 user-manual screenshots from the research_tree editor.
# Starts a dedicated server on port 8124, hits deterministic hash-URLs, and
# saves PNGs to ./screenshots/.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
RT_DIR="$(cd "$HERE/.." && pwd)"
PORT=8124
PID_FILE="/tmp/research_tree_manual_server.pid"
SHOT_DIR="$HERE/screenshots"
mkdir -p "$SHOT_DIR"

# Pick a Chromium binary. Prefer google-chrome (no snap sandbox quirks).
if command -v google-chrome >/dev/null 2>&1; then
  CHROME=google-chrome
elif command -v chromium >/dev/null 2>&1; then
  CHROME=chromium
elif command -v chromium-browser >/dev/null 2>&1; then
  CHROME=chromium-browser
else
  echo "No chromium / google-chrome binary found." >&2
  exit 1
fi

start_server() {
  if curl -fsS "http://127.0.0.1:$PORT/api/git/status" >/dev/null 2>&1; then
    echo "Server already responding on $PORT — reusing."
    return 0
  fi
  echo "Starting serve.py on port $PORT…"
  ( cd "$RT_DIR" && nohup python3 serve.py --port "$PORT" >/tmp/research_tree_manual_server.log 2>&1 & echo $! >"$PID_FILE" )
  for _ in $(seq 1 25); do
    if curl -fsS "http://127.0.0.1:$PORT/api/git/status" >/dev/null 2>&1; then
      echo "Server up."
      return 0
    fi
    sleep 0.2
  done
  echo "Server did not start within 5s." >&2
  cat /tmp/research_tree_manual_server.log >&2 || true
  exit 1
}

stop_server() {
  if [ -f "$PID_FILE" ]; then
    PID="$(cat "$PID_FILE" || true)"
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
      kill "$PID" 2>/dev/null || true
      sleep 0.2
      kill -9 "$PID" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
  fi
}

trap stop_server EXIT

start_server

# Shots: filename | hash (without leading #)
SHOTS=(
  "01-tree-overview.png|"
  "02-node-anatomy.png|node=p1-ag1-h50"
  "03-side-panel-empty.png|node=p1-no-duct-spacing"
  "04-edit-mode.png|edit&node=p2-1d-build"
  "05-help.png|help"
  "06-git-panel.png|git"
  "07-git-history.png|git=history"
  "08-search.png|search=duct"
  "09-decision-node.png|node=p1s-gap-rod-tradeoff"
  "10-phase3-branch.png|node=p3-material-rig"
)

shoot() {
  local out="$1"
  local hash="$2"
  local budget="${3:-2500}"
  local url="http://127.0.0.1:$PORT/"
  if [ -n "$hash" ]; then url="${url}#${hash}"; fi
  local tmpdir
  tmpdir="$(mktemp -d -t rt-shot.XXXXXX)"
  "$CHROME" \
    --headless=new \
    --disable-gpu \
    --no-sandbox \
    --hide-scrollbars \
    --window-size=1600,1000 \
    --user-data-dir="$tmpdir" \
    --virtual-time-budget="$budget" \
    --screenshot="$SHOT_DIR/$out" \
    "$url" >/dev/null 2>&1 || true
  rm -rf "$tmpdir"
}

is_blank() {
  # Treat empty/tiny PNGs as failed. < 4KB is suspicious for a 1600x1000 screenshot.
  local f="$1"
  if [ ! -s "$f" ]; then return 0; fi
  local sz
  sz="$(stat -c '%s' "$f" 2>/dev/null || echo 0)"
  [ "$sz" -lt 4096 ]
}

count_ok=0
for entry in "${SHOTS[@]}"; do
  name="${entry%%|*}"
  hash="${entry#*|}"
  echo "  shooting $name  (hash='$hash')"
  shoot "$name" "$hash" 2500
  if is_blank "$SHOT_DIR/$name"; then
    echo "    retrying $name with longer budget…"
    shoot "$name" "$hash" 5000
  fi
  if [ -f "$SHOT_DIR/$name" ]; then
    count_ok=$((count_ok + 1))
  fi
done

echo "$count_ok screenshots written to screenshots/"
