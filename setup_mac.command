#!/usr/bin/env bash
# One-time macOS setup for the Research Tree.
#
# Run it by pasting this line into Terminal (Cmd+Space, type "Terminal", Enter):
#
#   curl -fsSL https://raw.githubusercontent.com/asdfgh0318/duct-research-tree/main/setup_mac.command | bash
#
# What it does:
#   1. Makes sure Apple's command line tools (git + python3) are installed.
#   2. Downloads the Research Tree into ~/ResearchTree (or updates it).
#   3. Puts "Research Tree" and "Stop Research Tree" launchers on your Desktop.
#   4. Opens the tree in your browser.
#
# Safe to run again any time — it just updates.

set -e

REPO_URL="https://github.com/asdfgh0318/duct-research-tree.git"
DEST="$HOME/ResearchTree"

echo "== Research Tree setup =="

# 1. Command line tools (provides git and python3).
if ! xcode-select -p >/dev/null 2>&1; then
  echo
  echo "Apple's command line tools are needed first (free, official, ~5 min)."
  echo "A window will pop up — click 'Install', wait for it to finish,"
  echo "then run this setup line again."
  xcode-select --install >/dev/null 2>&1 || true
  exit 0
fi

# 2. Get or update the tree.
if [ -d "$DEST/.git" ]; then
  echo "Updating existing copy in $DEST ..."
  git -C "$DEST" pull --ff-only || {
    echo "Update failed (maybe local edits conflict). Your copy still works as-is."
  }
else
  echo "Downloading into $DEST ..."
  git clone "$REPO_URL" "$DEST"
fi

chmod +x "$DEST/research_tree" "$DEST"/*.command 2>/dev/null || true

# Local git identity so the editor's Commit button works on this machine.
if ! git -C "$DEST" config user.name >/dev/null 2>&1; then
  git -C "$DEST" config user.name "$(id -F 2>/dev/null || whoami)"
  git -C "$DEST" config user.email "$(whoami)@$(hostname -s).local"
fi

# 3. Desktop launchers (plain wrappers, written locally → no Gatekeeper fuss).
DESKTOP="$HOME/Desktop"
if [ -d "$DESKTOP" ]; then
  cat >"$DESKTOP/Research Tree.command" <<EOF
#!/usr/bin/env bash
exec "$DEST/Research Tree.command"
EOF
  cat >"$DESKTOP/Stop Research Tree.command" <<EOF
#!/usr/bin/env bash
exec "$DEST/Stop Research Tree.command"
EOF
  chmod +x "$DESKTOP/Research Tree.command" "$DESKTOP/Stop Research Tree.command"
  echo "Desktop launchers created."
fi

# 4. Launch it.
echo
"$DEST/research_tree"
echo
echo "All set! From now on just double-click 'Research Tree' on your Desktop."
