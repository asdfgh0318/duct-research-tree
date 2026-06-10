# research_tree — Claude context

A left-to-right research tree editor for the Shroud_Comparison duct/shroud testing program. Single-file HTML editor + JSON data + tiny git-aware Python server.

## Files

- `index.html` — vanilla-JS single-file editor. Pan/zoom canvas, click node → side panel, full editing (add/delete/duplicate, connect parents, drag-reorder). Loads `./data.json` via `fetch` on startup; falls back to `showOpenFilePicker` when opened on `file://`.
- `data.json` — the tree (6 phases, ~28 starting nodes). This is the source of truth. Commit it for history; `git log -p data.json` reads the changelog.
- `serve.py` — optional local server. Adds `/api/git/{status,pull,commit,push}` endpoints so the editor's "Pull / Commit / Push" buttons work end-to-end without leaving the page.
- `1.md` — original user brief that produced the tree.

## Data schema (must stay stable — both index.html and any future tools depend on it)

```json
{
  "title": "Duct Structure Test Research Tree",
  "phases": [
    {"id": "phase1",        "title": "Phase 1 — Foundation Tests",   "color": "#4a9eff"},
    {"id": "phase1_synth",  "title": "Phase 1 — Synthesis",          "color": "#4a9eff"},
    {"id": "phase2",        "title": "Phase 2 — Drone Builds",       "color": "#5cd97a"},
    {"id": "phase2_synth",  "title": "Phase 2 — Synthesis",          "color": "#5cd97a"},
    {"id": "phase3",        "title": "Phase 3 — Acoustic Materials", "color": "#ff9c4a"},
    {"id": "final",         "title": "Final",                        "color": "#d97aff"}
  ],
  "nodes": [
    {
      "id": "kebab-slug",
      "phaseId": "phase1",
      "title": "Short title",
      "description": "1–3 sentences.",
      "type": "test | build | synthesis | decision",
      "status": "planned | in-progress | done | blocked",
      "parents": ["other-id"],
      "geometry": {
        "airGapMm": null, "ductHeightMm": null,
        "rodCountTop": null, "rodCountBottom": null,
        "weightG": null, "propellerInches": null, "motorSpacingMm": null
      },
      "soundVisualizerLink": "",
      "notes": ""
    }
  ]
}
```

Rules: kebab-case unique IDs, parents reference IDs only (no orphans), all geometry keys present (use `null`), nodes start `"planned"` with empty `soundVisualizerLink` and `notes`. Layout is implicit — column = `1 + max(depth(p))`, so structure is purely a function of parent links.

## How to use

- **Just launch it**: `research_tree` (no flag) or `research_tree -duct` — both resolve to this folder; starts (or reuses) the server and opens the browser. `research_tree --stop` to stop, `research_tree --list` to see registered trees. The launcher lives next to this file (`./research_tree`) and is symlinked into `~/bin/`. It auto-discovers its own folder as `-self`; additional trees come from `~/.config/research_tree/trees.conf` (one row per line: `<flag>  <absolute-path>  <port>`). The `-duct` flag on this machine is defined there.
- **Read/view only**: open `index.html` directly in a browser (file://). Editor loads `data.json` via fetch — works in Chrome/Edge; on Firefox the fetch may be blocked and the empty-state "Open data.json" button kicks in. Git buttons are disabled on file://.
- **Manually serve**: `python3 serve.py` (defaults to port 8123). `--port N` and `--repo PATH` flags supported.
- **Pure file:// editing**: still works — Save uses the File System Access API to write `data.json`. After saving, commit manually via the terminal.

## Shared repo (Mac collaborator)

The folder is mirrored to a small **public** repo so a collaborator without a
GitHub account can run and pull it: `https://github.com/asdfgh0318/duct-research-tree`
(remote `shared` in the ŻYCIE repo). It was created with `git subtree split`,
so the folder's history carried over.

- **Publish local changes to the shared repo** (after committing in ŻYCIE):
  `git -C /home/adam/ŻYCIE subtree push --prefix='PRACA/Shroud_Comparison/research_tree' shared main`
- The collaborator installs via `setup_mac.command` (one curl line, see
  `SETUP_MAC.md`), gets Desktop launchers, and **Pull**s updates from the
  editor. He is a **view/pull-only supervisor** — he has no GitHub account,
  doesn't push, and isn't expected to edit. All edits happen here.
- Mac specifics live in: `Research Tree.command`, `Stop Research Tree.command`,
  `setup_mac.command`, `SETUP_MAC.md`. The `research_tree` launcher handles
  Darwin (`open`, `lsof` fallback).

## Git conventions

- One commit per meaningful tree change. Suggested message: `tree: <what changed>` (e.g. `tree: fill ag1×h50 acoustic results`).
- `data.json` is pretty-printed (`JSON.stringify(state, null, 2)`) so diffs are line-by-line readable.
- Don't squash these commits — the per-edit history *is* the research log.

## Sound visualizer integration

Each node carries a `soundVisualizerLink` URL. It points into the (separate) sound visualizer project where acoustic + performance numbers live. This tree only carries geometry/build state — the heavy data stays in the visualizer's DB. When that project gets a deeplink scheme, the link field can hold `soundviz://session/abc123`-style URIs.

## Gotchas

- Adding a `parents` link that would create a cycle is rejected by the editor with a toast — keep it that way; layout assumes a DAG.
- Phase color changes need to update CSS variables AND any per-node phase pills — `index.html` does this via inline `style` props, so re-rendering nodes is enough; no global stylesheet rebuild.
- The File System Access API only works in Chromium-family browsers. Firefox falls back to download — fine for one-off backups, awkward for everyday editing. Use `serve.py` on Firefox.
- `serve.py` runs `git` commands as the user that started the process. If you start it from elsewhere, pass `--repo /home/adam/ŻYCIE/PRACA/Shroud_Comparison` so the git ops land in the right repo.

## Manual

Illustrated user manual for newcomers lives in `manual/`:

- `manual/manual.pdf` — A4, ~19 pages, 10 captioned screenshots. The thing you hand to a green team-member.
- `manual/manual.html` — source. Inline CSS + SVG; references the PNGs in `manual/screenshots/`.
- `manual/make_screenshots.sh` — re-captures all 10 screenshots. Boots `serve.py` on port 8124 (so it never clashes with the user's running 8123), drives Chromium with deterministic `#node=`/`#edit`/`#git`/`#help`/`#search=` URL hashes, then stops the server.
- `manual/build.sh` — runs `make_screenshots.sh` then renders `manual.html` to `manual.pdf` via headless Chromium. This is the one-shot rebuild command.

`index.html` exposes the URL-hash hooks the screenshot script relies on (`#node=<id>`, `#edit`, `#git`, `#git=history`, `#help`, `#search=<text>`, joined with `&`). They re-apply on `hashchange`, so you can navigate the same window between deterministic states without reloading. They're also useful as deep links from external docs.

The Help overlay (`?` button in the toolbar) carries a footer link to `manual/manual.pdf`.

## Original brief

See `1.md` for the user's original message and the clarifying answers that shaped the initial tree.
