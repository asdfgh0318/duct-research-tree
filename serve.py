#!/usr/bin/env python3
"""Local research-tree editor server.

Serves the script's directory over HTTP on 127.0.0.1 and exposes a tiny
git API (status / pull / commit / push / log) used by the in-browser editor.

Standard library only. No third-party dependencies.
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _git(repo, *args):
    """Run `git -C <repo> <args>` and return (returncode, stdout, stderr)."""
    cmd = ["git", "-C", repo, *args]
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return cp.returncode, cp.stdout, cp.stderr
    except FileNotFoundError:
        return 127, "", "git executable not found"


def git_status(repo):
    rc_b, out_b, _ = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    branch = out_b.strip() if rc_b == 0 else ""

    # Upstream ahead/behind (gracefully tolerate "no upstream")
    ahead, behind = 0, 0
    rc_ab, out_ab, _ = _git(repo, "rev-list", "--left-right", "--count", "@{u}...HEAD")
    if rc_ab == 0 and out_ab.strip():
        parts = out_ab.strip().split()
        if len(parts) == 2:
            try:
                behind = int(parts[0])
                ahead = int(parts[1])
            except ValueError:
                pass

    rc_st, out_st, _ = _git(repo, "status", "--porcelain=v1")
    dirty_files = []
    if rc_st == 0:
        for line in out_st.splitlines():
            if not line:
                continue
            # Porcelain v1: first two chars are status, then space, then path.
            # Paths may include rename arrow ' -> '. Take the last component.
            path = line[3:]
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            dirty_files.append(path)

    rc_log, out_log, _ = _git(repo, "log", "-1", "--format=%h%n%s")
    head, head_msg = "", ""
    if rc_log == 0:
        bits = out_log.splitlines()
        if bits:
            head = bits[0].strip()
            if len(bits) > 1:
                head_msg = bits[1].strip()

    return {
        "branch": branch,
        "ahead": ahead,
        "behind": behind,
        "dirty_files": dirty_files,
        "head": head,
        "head_msg": head_msg,
    }


def git_pull(repo):
    rc, out, err = _git(repo, "pull", "--ff-only")
    if rc == 0:
        return {"ok": True, "output": (out + err).strip()}
    return {"ok": False, "error": err.strip() or out.strip() or "pull failed",
            "output": (out + err).strip()}


def git_commit(repo, message, paths):
    if not isinstance(message, str) or not message.strip():
        return {"ok": False, "error": "commit message is required"}
    if not paths:
        return {"ok": False, "error": "no paths to commit"}

    safe_paths = []
    for p in paths:
        ok, norm = _safe_repo_path(repo, p)
        if not ok:
            return {"ok": False, "error": f"rejected path: {p}"}
        safe_paths.append(norm)

    rc_add, out_add, err_add = _git(repo, "add", "--", *safe_paths)
    if rc_add != 0:
        return {"ok": False, "error": (err_add or out_add).strip() or "git add failed"}

    # Detect "nothing to commit" before invoking commit (cleaner UX).
    rc_diff, out_diff, _ = _git(repo, "diff", "--cached", "--name-only", "--", *safe_paths)
    if rc_diff == 0 and not out_diff.strip():
        return {"ok": False, "error": "nothing to commit"}

    rc_c, out_c, err_c = _git(repo, "commit", "-m", message)
    if rc_c != 0:
        combined = (err_c + out_c).strip()
        if "nothing to commit" in combined.lower():
            return {"ok": False, "error": "nothing to commit"}
        return {"ok": False, "error": combined or "commit failed"}

    rc_h, out_h, _ = _git(repo, "rev-parse", "--short", "HEAD")
    commit_hash = out_h.strip() if rc_h == 0 else ""

    return {"ok": True, "commit": commit_hash, "output": (out_c + err_c).strip()}


def git_push(repo):
    # Pre-check upstream so we can give a useful error.
    rc_up, _, err_up = _git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if rc_up != 0:
        rc_b, out_b, _ = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
        branch = out_b.strip() if rc_b == 0 else "<branch>"
        return {
            "ok": False,
            "error": f"no upstream configured. Run `git push -u origin {branch}` from a terminal.",
            "output": err_up.strip(),
        }

    rc, out, err = _git(repo, "push")
    if rc == 0:
        return {"ok": True, "output": (out + err).strip()}
    return {"ok": False, "error": err.strip() or out.strip() or "push failed",
            "output": (out + err).strip()}


def git_log(repo, path, limit):
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 20
    if limit < 1:
        limit = 1
    if limit > 200:
        limit = 200

    args = ["log", f"--pretty=format:%h%x00%an%x00%aI%x00%s", "-n", str(limit)]
    if path:
        ok, norm = _safe_repo_path(repo, path)
        if not ok:
            return {"entries": [], "error": "rejected path"}
        args += ["--", norm]

    rc, out, err = _git(repo, *args)
    if rc != 0:
        return {"entries": [], "error": err.strip() or "log failed"}

    entries = []
    for line in out.split("\n"):
        if not line:
            continue
        parts = line.split("\x00")
        if len(parts) < 4:
            continue
        entries.append({
            "hash": parts[0],
            "author": parts[1],
            "date": parts[2],
            "subject": parts[3],
        })
    return {"entries": entries}


# ---------------------------------------------------------------------------
# Path safety
# ---------------------------------------------------------------------------

def _safe_repo_path(repo, raw):
    """Validate `raw` as a repo-relative path. Returns (ok, normalized).

    Rejects absolute paths and any traversal escaping the repo root.
    """
    if not isinstance(raw, str) or not raw:
        return False, ""
    if raw.startswith("/") or raw.startswith("\\"):
        return False, ""
    if ".." in raw.replace("\\", "/").split("/"):
        return False, ""
    norm = os.path.normpath(raw)
    if norm.startswith("..") or os.path.isabs(norm):
        return False, ""
    abs_repo = os.path.abspath(repo)
    abs_target = os.path.abspath(os.path.join(abs_repo, norm))
    if abs_target != abs_repo and not abs_target.startswith(abs_repo + os.sep):
        return False, ""
    return True, norm


# ---------------------------------------------------------------------------
# Node patch (loopback-only writer, used by sound-visualizer-style integrations)
# ---------------------------------------------------------------------------

_NODE_WRITABLE_FIELDS = {"soundVisualizerLink", "status", "notes"}
_NODE_VALID_STATUSES = {"planned", "in-progress", "done", "blocked"}


def _patch_node(serve_dir, repo_root, node_id, body):
    """Update a node's writable fields in data.json + auto-commit.

    Only `soundVisualizerLink`, `status`, `notes` are settable here — schema
    surgery (id/parents/geometry/etc.) belongs in the browser editor where
    the user can see the layout impact. Returns (http_status, json_payload).
    """
    if not isinstance(body, dict):
        return 400, {"ok": False, "error": "body must be a JSON object"}
    bad = [k for k in body if k not in _NODE_WRITABLE_FIELDS]
    if bad:
        return 400, {"ok": False, "error": f"unsupported fields: {sorted(bad)}"}
    if "status" in body and body["status"] not in _NODE_VALID_STATUSES:
        return 400, {"ok": False, "error": f"status must be one of {sorted(_NODE_VALID_STATUSES)}"}
    for k in ("soundVisualizerLink", "notes"):
        if k in body and not isinstance(body[k], str):
            return 400, {"ok": False, "error": f"{k} must be a string"}

    data_path = os.path.join(serve_dir, "data.json")
    if not os.path.exists(data_path):
        return 500, {"ok": False, "error": "data.json not found"}
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)
    nodes = data.get("nodes") or []
    target = next((n for n in nodes if n.get("id") == node_id), None)
    if target is None:
        return 404, {"ok": False, "error": f"no node with id {node_id!r}"}

    changed = {k: v for k, v in body.items() if target.get(k) != v}
    if not changed:
        return 200, {"ok": True, "node_id": node_id, "changed": {}}
    target.update(changed)

    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    rel = os.path.relpath(data_path, repo_root)
    msg = f"tree: link sound-vis data for {node_id}"
    commit_result = git_commit(repo_root, msg, [rel])
    return 200, {"ok": True, "node_id": node_id, "changed": changed, "git": commit_result}


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class GitAwareHandler(SimpleHTTPRequestHandler):
    # Populated at server construction time.
    repo_root = ""
    serve_dir = ""

    # Silence the default per-request log line; we emit our own to stderr.
    def log_message(self, format, *args):
        return

    # ---- response helpers ----
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ValueError("invalid JSON body: " + str(e))
        if not isinstance(data, dict):
            raise ValueError("expected JSON object body")
        return data

    # Make sure even static responses are uncached (avoid stale data.json).
    def end_headers(self):
        # Only inject cache header for non-API static paths (API sets its own).
        if not self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    # ---- request log ----
    def _log_req(self, status, started_ms):
        elapsed = int((time.monotonic() - started_ms) * 1000)
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        sys.stderr.write(f"[{ts}] {self.command} {self.path} -> {status} ({elapsed}ms)\n")
        sys.stderr.flush()

    # ---- dispatch ----
    def do_GET(self):
        started = time.monotonic()
        try:
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/"):
                self._handle_api_get(parsed)
            else:
                # Delegate to the static file server (it will call end_headers,
                # which injects no-store for non-API paths).
                return super().do_GET()
        except Exception as e:
            self._send_json(500, {"ok": False, "error": str(e)})
        finally:
            # The static path logs through SimpleHTTPRequestHandler's own
            # default; we still want a unified line, so emit here.
            try:
                self._log_req(getattr(self, "_last_status", 200), started)
            except Exception:
                pass

    def do_POST(self):
        started = time.monotonic()
        try:
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/"):
                self._handle_api_post(parsed)
            else:
                self._send_json(404, {"ok": False, "error": "not found"})
        except Exception as e:
            self._send_json(500, {"ok": False, "error": str(e)})
        finally:
            try:
                self._log_req(getattr(self, "_last_status", 200), started)
            except Exception:
                pass

    # Track status for our unified log line.
    def send_response(self, code, message=None):
        self._last_status = code
        super().send_response(code, message)

    # ---- API endpoints ----
    def _handle_api_get(self, parsed):
        path = parsed.path
        if path == "/api/git/status":
            status = git_status(self.repo_root)
            status["data_json_rel"] = self._default_data_json_rel()
            self._send_json(200, status)
            return
        if path == "/api/git/log":
            qs = parse_qs(parsed.query)
            rel = (qs.get("path") or [""])[0]
            limit = (qs.get("limit") or ["20"])[0]
            self._send_json(200, git_log(self.repo_root, rel, limit))
            return
        self._send_json(404, {"ok": False, "error": "unknown endpoint"})

    def _handle_api_post(self, parsed):
        path = parsed.path
        try:
            body = self._read_json_body() if path != "/api/git/pull" and path != "/api/git/push" else {}
        except ValueError as e:
            self._send_json(400, {"ok": False, "error": str(e)})
            return

        if path == "/api/git/pull":
            self._send_json(200, git_pull(self.repo_root))
            return
        if path == "/api/git/push":
            self._send_json(200, git_push(self.repo_root))
            return
        # Node-write endpoint (loopback-only): patches a node's editable fields.
        # Designed for external tools (e.g. sound-visualizer) to push the
        # `soundVisualizerLink` + status flip after a successful capture.
        # Refuses any non-loopback caller so the LAN can read the tree but not edit it.
        if path.startswith("/api/node/"):
            client_ip = self.client_address[0]
            if client_ip not in ("127.0.0.1", "::1", "::ffff:127.0.0.1"):
                self._send_json(403, {"ok": False, "error": "node-write is loopback-only"})
                return
            node_id = path[len("/api/node/"):]
            if not node_id or "/" in node_id:
                self._send_json(400, {"ok": False, "error": "node id required"})
                return
            self._send_json(*_patch_node(self.serve_dir, self.repo_root, node_id, body))
            return

        if path == "/api/git/commit":
            message = body.get("message")
            paths = body.get("paths")
            if not isinstance(message, str) or not message.strip():
                self._send_json(400, {"ok": False, "error": "message is required"})
                return
            if paths is None:
                # Default: stage research_tree/data.json relative to repo root,
                # if that path exists.
                default_rel = self._default_data_json_rel()
                if not default_rel:
                    self._send_json(400, {"ok": False,
                                          "error": "no paths and default data.json not found"})
                    return
                paths = [default_rel]
            if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
                self._send_json(400, {"ok": False, "error": "paths must be a list of strings"})
                return
            self._send_json(200, git_commit(self.repo_root, message, paths))
            return

        self._send_json(404, {"ok": False, "error": "unknown endpoint"})

    def _default_data_json_rel(self):
        """Find the repo-relative path to this script's neighbouring data.json."""
        candidate = os.path.join(self.serve_dir, "data.json")
        if not os.path.exists(candidate):
            return ""
        rel = os.path.relpath(candidate, self.repo_root)
        if rel.startswith(".."):
            return ""
        # Normalize to forward slashes for git.
        return rel.replace(os.sep, "/")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _resolve_repo_root(serve_dir):
    rc, out, _ = _git(serve_dir, "rev-parse", "--show-toplevel")
    if rc == 0 and out.strip():
        return out.strip()
    # Fall back to serve_dir if not in a git repo.
    return serve_dir


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description="Local research-tree editor server with git API.")
    parser.add_argument("--port", type=int, default=8123, help="TCP port (default 8123)")
    parser.add_argument("--repo", default=None, help="Git repo root (default: auto-detect)")
    parser.add_argument(
        "--bind",
        default="127.0.0.1",
        help="Bind address. Default 127.0.0.1 (local only). Use 0.0.0.0 to expose on LAN. "
             "The /api/node/<id> write endpoint is loopback-only regardless of --bind.",
    )
    args = parser.parse_args(argv)

    serve_dir = here
    repo_root = args.repo or _resolve_repo_root(serve_dir)
    repo_root = os.path.abspath(repo_root)

    # Bind handler class attributes.
    GitAwareHandler.repo_root = repo_root
    GitAwareHandler.serve_dir = serve_dir

    # SimpleHTTPRequestHandler serves files from cwd; chdir for reliability.
    os.chdir(serve_dir)

    bind = args.bind
    httpd = ThreadingHTTPServer((bind, args.port), GitAwareHandler)
    print(f"serving {serve_dir}  ·  repo {repo_root}  ·  http://{bind}:{args.port}/")
    sys.stdout.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
