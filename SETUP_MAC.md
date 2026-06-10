# Research Tree on a Mac — setup guide

This gets the Research Tree running on a MacBook in a few minutes. No accounts
needed, nothing to configure.

## One-time setup

1. Open **Terminal**: press `Cmd + Space`, type `Terminal`, press `Enter`.
2. Copy-paste this line and press `Enter`:

   ```
   curl -fsSL https://raw.githubusercontent.com/asdfgh0318/duct-research-tree/main/setup_mac.command | bash
   ```

3. If a window pops up asking to install **command line tools**, click
   **Install**, wait for it to finish (~5 min), then run the same line again.
4. The Research Tree opens in your browser, and two icons appear on your
   Desktop: **Research Tree** and **Stop Research Tree**.

## Everyday use

- **Open the tree**: double-click **Research Tree** on the Desktop. A small
  Terminal window appears (you can close it) and the tree opens in your
  browser at `http://127.0.0.1:8123/`.
- **Get the latest version of the tree**: click the **Pull** button inside
  the editor (top toolbar, git panel).
- **Save your edits**: click **Save**. You can also click **Commit** with a
  short message — this records your change in the local history.
- **Stop it**: double-click **Stop Research Tree** (optional — it uses almost
  no resources while running).

## Sending your changes back

The **Push** button will not work on this machine (it needs a GitHub
account). To share your edits:

1. Click **Save** in the editor.
2. Send the file `ResearchTree/data.json` (in your home folder) back by
   AirDrop / email / chat.

Heads-up: clicking **Pull** after you've made local edits may fail with a
conflict message. If that happens, send your `data.json` back first, then ask
for a fresh copy (or just delete the `ResearchTree` folder and run the setup
line again).

## If something looks stuck

Double-click **Stop Research Tree**, then **Research Tree** again. If the
browser shows "can't connect", wait two seconds and reload the page.
