#!/usr/bin/env bash
# Rebuild the user manual: refresh screenshots + render manual.html to manual.pdf.

set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

# Pick chrome/chromium binary the same way make_screenshots.sh does.
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

echo "[1/2] Refreshing screenshots…"
"$HERE/make_screenshots.sh"

echo "[2/2] Rendering manual.html -> manual.pdf…"
TMPPROFILE="$(mktemp -d -t rt-manual-pdf.XXXXXX)"
"$CHROME" \
  --headless=new \
  --disable-gpu \
  --no-sandbox \
  --no-pdf-header-footer \
  --user-data-dir="$TMPPROFILE" \
  --virtual-time-budget=5000 \
  --print-to-pdf="$HERE/manual.pdf" \
  "file://$HERE/manual.html" >/dev/null 2>&1
rm -rf "$TMPPROFILE"

if [ ! -s "$HERE/manual.pdf" ]; then
  echo "manual.pdf was not produced." >&2
  exit 1
fi

echo
echo "Result:"
ls -lh "$HERE/manual.pdf"
if command -v pdfinfo >/dev/null 2>&1; then
  echo
  pdfinfo "$HERE/manual.pdf" | head -20
fi
