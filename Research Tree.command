#!/usr/bin/env bash
# Research Tree — double-clickable macOS launcher.
# Starts the local server (if needed) and opens the editor in the browser.
cd "$(dirname "$0")"
./research_tree
echo
echo "The Research Tree is now open in your browser."
echo "You can close this window — the tree keeps running."
echo "(To stop it completely: double-click 'Stop Research Tree.command'.)"
