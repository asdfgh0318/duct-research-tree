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
  the editor (top toolbar, git panel). Do this whenever you want to see the
  newest state — that's all there is to it.
- **Make a PDF report**: click **Report** in the toolbar, then
  **Save as PDF / Print** — a one-page summary with progress and the whole
  tree.
- **Stop it**: double-click **Stop Research Tree** (optional — it uses almost
  no resources while running).

Your copy is for **viewing**. Don't worry about the Save / Commit / Push
buttons — changes to the tree are made on the other end, and **Pull** brings
them to you. If you accidentally changed something and **Pull** starts
complaining, just delete the `ResearchTree` folder from your home folder and
run the setup line again — you'll get a fresh copy.

## If something looks stuck

Double-click **Stop Research Tree**, then **Research Tree** again. If the
browser shows "can't connect", wait two seconds and reload the page.
