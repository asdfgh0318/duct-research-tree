#!/usr/bin/env bash
# Stops the Research Tree local server.
cd "$(dirname "$0")"
./research_tree --stop
echo "Done. You can close this window."
