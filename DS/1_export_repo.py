# -*- coding: utf-8 -*-
"""
Export SmartSHARK commits into:

OUTPUT_ROOT/
  <project_name_sanitized>/
    <revision_hash>/
      <hunk_oid>.txt   (one file per hunk)
      ...

Each hunk file contains:
- Project / VCS info
- Commit hash
- hunk_oid
- file_path
- n_files_per_commit
- file_i_out_of_N: FILE_ID:<...>
- n_hunks_per_file_i
- Parents
- git_used: yes/no
- Subject (+ optional message body)
- Diff excerpt:
    Prefer from git (like GitHub, with context lines)
    Fallback to Mongo hunk content if git not available.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from pymongo import MongoClient


# ====================== CONFIG ======================

MONGO_DB   = "smartshark_1_2"
MONGO_HOST = "localhost"
MONGO_PORT = 27017

MONGO_USER = None
MONGO_PASS = None
MONGO_AUTH_DB = None  # e.g. "admin" or "smartshark", else None

# Root folder where everything will be written
OUTPUT_ROOT = Path(
    r"C:\Users\ahmad\Desktop\Bilkent\5th year\1st sem\SDP - CS491\dataset_of_tangled_commits\Project's commits\projects_patches"
)

# Where local git repos live (used to get GitHub-like diffs).
# Suggested: keep them next to output.
REPO_ROOT = OUTPUT_ROOT.parent / "_repos"

# If repo folder not found, auto-clone from vcs_system.url (can be big).
AUTO_CLONE_IF_MISSING = True

# If commit is missing locally, try "git fetch --all --tags"
FETCH_IF_COMMIT_MISSING = True

# Unified context lines (GitHub default-like is 3)
GIT_UNIFIED = 3

# Timeouts (seconds)
GIT_SHOW_TIMEOUT = 60
GIT_CLONE_TIMEOUT = 60 * 30
GIT_FETCH_TIMEOUT = 60 * 10

# Optional: limit while testing
MAX_PROJECTS = None
MAX_COMMITS_PER_VCS = None

# ====================================================


# ------------------ helpers ------------------

RE_DIFF_GIT = re.compile(r"^diff --git a/(.*?) b/(.*?)\s*$")
RE_HUNK_HDR = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

def get_mongo_client():
    if MONGO_USER and MONGO_PASS:
        auth_db = MONGO_AUTH_DB or MONGO_DB
        uri = f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/{auth_db}"
        return MongoClient(uri)
    return MongoClient(MONGO_HOST, MONGO_PORT)


def sanitize_name(name: str) -> str:
    bad_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for ch in bad_chars:
        name = name.replace(ch, "_")
    name = name.replace(" ", "_")
    return name


def format_datetime(dt) -> str:
    if isinstance(dt, datetime):
        return dt.isoformat()
    if dt is None:
        return ""
    return str(dt)


def normalize_repo_path(p: str) -> str:
    # Ensure forward slashes for matching git output
    return (p or "").replace("\\", "/").lstrip("/")


def build_full_path(file_doc: Optional[Dict[str, Any]]) -> str:
    if not file_doc:
        return "(unknown file)"
    path = file_doc.get("path") or ""
    name = file_doc.get("name") or ""
    path = normalize_repo_path(path)
    if path and not path.endswith("/"):
        path += "/"
    return f"{path}{name}" if name else path


def extract_subject_and_body(message: str) -> Tuple[str, List[str]]:
    msg = (message or "").splitlines()
    if not msg:
        return "(no commit message)", []
    subject = msg[0]
    body = msg[1:] if len(msg) > 1 else []
    return subject, body


def run_git(args: List[str], cwd: Path, timeout: int) -> Tuple[int, str, str]:
    """
    Run git command, return (returncode, stdout, stderr).
    """
    try:
        p = subprocess.run(
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return p.returncode, p.stdout, p.stderr
    except Exception as e:
        return 999, "", f"{type(e).__name__}: {e}"


def repo_dir_guess(vcs_url: str, project_name: str) -> Path:
    """
    Decide local folder name for this repo. Tries:
    1) sanitized project name
    2) last URL component (minus .git)
    """
    safe_proj = sanitize_name(project_name or "unknown_project")
    candidate1 = REPO_ROOT / safe_proj

    tail = (vcs_url or "").rstrip("/").split("/")[-1]
    if tail.endswith(".git"):
        tail = tail[:-4]
    safe_tail = sanitize_name(tail or safe_proj)
    candidate2 = REPO_ROOT / safe_tail

    # Prefer existing
    if candidate1.exists():
        return candidate1
    if candidate2.exists():
        return candidate2

    # Default to project-based
    return candidate1


def ensure_repo_present(vcs_url: str, repo_path: Path) -> bool:
    """
    Ensure repo exists locally at repo_path. If not and AUTO_CLONE_IF_MISSING, clone it.
    """
    if repo_path.exists() and (repo_path / ".git").exists():
        return True

    if repo_path.exists() and any(repo_path.iterdir()):
        # Non-empty but not a normal repo
        return False

    if not AUTO_CLONE_IF_MISSING:
        return False

    REPO_ROOT.mkdir(parents=True, exist_ok=True)

    # Clone without checkout (fast-ish, still can be big)
    cmd = ["git", "clone", "--no-checkout", vcs_url, str(repo_path)]
    rc, out, err = run_git(cmd, cwd=REPO_ROOT, timeout=GIT_CLONE_TIMEOUT)
    return rc == 0


def git_has_commit(repo_path: Path, revision: str) -> bool:
    # git cat-file -e <rev>^{commit}
    rc, _, _ = run_git(["git", "cat-file", "-e", f"{revision}^{{commit}}"], cwd=repo_path, timeout=20)
    return rc == 0


def git_fetch_all(repo_path: Path) -> bool:
    rc, _, _ = run_git(["git", "fetch", "--all", "--tags"], cwd=repo_path, timeout=GIT_FETCH_TIMEOUT)
    return rc == 0


def git_show_diff(repo_path: Path, revision: str) -> Optional[str]:
    """
    Return `git show` diff output (no commit header), or None if not possible.
    """
    if not git_has_commit(repo_path, revision):
        if FETCH_IF_COMMIT_MISSING:
            ok = git_fetch_all(repo_path)
            if ok and not git_has_commit(repo_path, revision):
                return None
        else:
            return None

    cmd = [
        "git", "show",
        "--no-color",
        f"--unified={GIT_UNIFIED}",
        "--pretty=format:",   # no commit header, only diff
        revision
    ]
    rc, out, _ = run_git(cmd, cwd=repo_path, timeout=GIT_SHOW_TIMEOUT)
    if rc != 0:
        return None
    return out


def parse_git_diff(diff_text: str) -> Dict[str, Dict[str, Any]]:
    """
    Parse git show diff into per-file sections:
    returns mapping path -> {
        "a_path", "b_path",
        "header_lines": [...],
        "hunks": [ {"old_start","old_len","new_start","new_len","lines":[...]} ... ]
    }

    We index both a_path and b_path in the returned dict for easier matching.
    """
    lines = (diff_text or "").splitlines()
    sections: List[Dict[str, Any]] = []

    cur = None
    for ln in lines:
        m = RE_DIFF_GIT.match(ln)
        if m:
            if cur:
                sections.append(cur)
            a_path = normalize_repo_path(m.group(1))
            b_path = normalize_repo_path(m.group(2))
            cur = {
                "a_path": a_path,
                "b_path": b_path,
                "raw_lines": [ln],
            }
        else:
            if cur is not None:
                cur["raw_lines"].append(ln)

    if cur:
        sections.append(cur)

    out: Dict[str, Dict[str, Any]] = {}

    for sec in sections:
        raw = sec["raw_lines"]
        header_lines: List[str] = []
        hunks: List[Dict[str, Any]] = []

        i = 0
        # header is from 'diff --git' up to first '@@' (exclusive)
        while i < len(raw) and not raw[i].startswith("@@ "):
            header_lines.append(raw[i])
            i += 1

        # parse hunks
        cur_hunk = None
        while i < len(raw):
            line = raw[i]
            mh = RE_HUNK_HDR.match(line)
            if mh:
                if cur_hunk:
                    hunks.append(cur_hunk)
                old_start = int(mh.group(1))
                old_len = int(mh.group(2)) if mh.group(2) else 1
                new_start = int(mh.group(3))
                new_len = int(mh.group(4)) if mh.group(4) else 1
                cur_hunk = {
                    "old_start": old_start,
                    "old_len": old_len,
                    "new_start": new_start,
                    "new_len": new_len,
                    "lines": [line],
                }
            else:
                if cur_hunk is not None:
                    cur_hunk["lines"].append(line)
                else:
                    # still header-ish lines (rare), keep them in header
                    header_lines.append(line)
            i += 1

        if cur_hunk:
            hunks.append(cur_hunk)

        parsed = {
            "a_path": sec["a_path"],
            "b_path": sec["b_path"],
            "header_lines": header_lines,
            "hunks": hunks,
        }

        # index by both paths
        out[sec["a_path"]] = parsed
        out[sec["b_path"]] = parsed

    return out


def pick_git_hunk(parsed_by_path: Dict[str, Dict[str, Any]],
                 candidate_paths: List[str],
                 old_start: Optional[int],
                 old_len: Optional[int],
                 new_start: Optional[int],
                 new_len: Optional[int]) -> Optional[Tuple[List[str], List[str]]]:
    """
    Return (file_header_lines, hunk_lines) from git parsed diff if match found.
    Matching strategy:
      1) exact match on (old_start, old_len, new_start, new_len)
      2) fallback match on (old_start, new_start)
    """
    for p in candidate_paths:
        p = normalize_repo_path(p)
        sec = parsed_by_path.get(p)
        if not sec:
            continue

        hunks = sec.get("hunks") or []
        # exact
        if old_start and new_start and old_len and new_len:
            for h in hunks:
                if (h["old_start"] == old_start and h["new_start"] == new_start
                    and h["old_len"] == old_len and h["new_len"] == new_len):
                    return sec["header_lines"], h["lines"]

        # fallback starts-only
        if old_start and new_start:
            for h in hunks:
                if h["old_start"] == old_start and h["new_start"] == new_start:
                    return sec["header_lines"], h["lines"]

    return None


def preload_people(db):
    print("Preloading people collection...")
    people_map = {}
    cursor = db.people.find({}, {"_id": 1, "name": 1, "email": 1})
    for p in cursor:
        people_map[p["_id"]] = {"name": p.get("name"), "email": p.get("email")}
    print(f"  loaded {len(people_map)} people")
    return people_map


def main():
    client = get_mongo_client()
    db = client[MONGO_DB]

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    REPO_ROOT.mkdir(parents=True, exist_ok=True)

    people_map = preload_people(db)

    # simple caches to reduce repeated lookups
    file_cache: Dict[Any, Optional[Dict[str, Any]]] = {}

    def get_file_doc(file_id):
        if file_id in file_cache:
            return file_cache[file_id]
        doc = db.file.find_one({"_id": file_id}) if file_id is not None else None
        file_cache[file_id] = doc
        return doc

    projects = list(db.project.find({}, {"_id": 1, "name": 1}))
    if MAX_PROJECTS is not None:
        projects = projects[:MAX_PROJECTS]

    print(f"\nFound {len(projects)} projects in DB '{MONGO_DB}'")

    for p_idx, project in enumerate(projects, start=1):
        project_id = project["_id"]
        project_name = project.get("name", str(project_id))
        safe_project = sanitize_name(project_name)

        project_dir = OUTPUT_ROOT / safe_project
        project_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n[{p_idx}/{len(projects)}] Project: {project_name} ({project_id})")
        print(f"  -> folder: {project_dir}")

        vcs_systems = list(db.vcs_system.find(
            {"project_id": project_id},
            {"_id": 1, "url": 1, "repository_type": 1, "project_id": 1}
        ))
        print(f"  VCS systems: {len(vcs_systems)}")
        if not vcs_systems:
            continue

        for vcs_idx, vcs in enumerate(vcs_systems, start=1):
            vcs_id = vcs["_id"]
            vcs_url = vcs.get("url") or ""
            vcs_type = (vcs.get("repository_type") or "").lower()

            print(f"  [{vcs_idx}/{len(vcs_systems)}] VCS {vcs_id} ({vcs_type}): {vcs_url}")

            repo_path = None
            repo_ready = False
            if vcs_type == "git" and vcs_url:
                repo_path = repo_dir_guess(vcs_url, project_name)
                repo_ready = ensure_repo_present(vcs_url, repo_path)

            commit_projection = {
                "_id": 1,
                "vcs_system_id": 1,
                "revision_hash": 1,
                "author_id": 1,
                "author_date": 1,
                "committer_date": 1,
                "message": 1,
                "parents": 1,
            }

            commits_cursor = db.commit.find({"vcs_system_id": vcs_id}, commit_projection)
            if MAX_COMMITS_PER_VCS is not None:
                commits_cursor = commits_cursor.limit(MAX_COMMITS_PER_VCS)

            commit_count = 0
            for commit in commits_cursor:
                commit_count += 1
                revision = commit.get("revision_hash") or str(commit["_id"])
                commit_dir = project_dir / revision
                commit_dir.mkdir(parents=True, exist_ok=True)

                # --- gather file_actions and hunks for this commit ---
                file_actions = list(db.file_action.find(
                    {"commit_id": commit["_id"]},
                    {"_id": 1, "file_id": 1, "old_file_id": 1, "change_type": 1, "mode": 1}
                ))

                if not file_actions:
                    # still keep the folder, but nothing to write
                    continue

                # stable ordering
                fa_infos = []
                for fa in file_actions:
                    file_id = fa.get("file_id")
                    old_file_id = fa.get("old_file_id")

                    file_doc = get_file_doc(file_id)
                    old_file_doc = get_file_doc(old_file_id) if old_file_id else None

                    full_path = build_full_path(file_doc) or "(unknown file)"
                    old_full_path = build_full_path(old_file_doc) if old_file_doc else ""

                    change_type = fa.get("change_type") or fa.get("mode") or "change"

                    hunks = list(db.hunk.find(
                        {"file_action_id": fa["_id"]},
                        {"_id": 1, "content": 1, "old_start": 1, "old_lines": 1, "new_start": 1, "new_lines": 1}
                    ))

                    fa_infos.append({
                        "fa": fa,
                        "file_id": file_id,
                        "full_path": normalize_repo_path(full_path),
                        "old_full_path": normalize_repo_path(old_full_path),
                        "change_type": change_type,
                        "hunks": hunks,
                    })

                # sort files by path for deterministic file_i numbering
                fa_infos.sort(key=lambda x: (x["full_path"], str(x["file_id"])))
                n_files = len(fa_infos)

                # --- try load git diff once per commit ---
                git_diff_text = None
                parsed_git = None
                if repo_ready and repo_path is not None:
                    git_diff_text = git_show_diff(repo_path, revision)
                    if git_diff_text:
                        parsed_git = parse_git_diff(git_diff_text)

                # --- write one file per hunk ---
                author_info = people_map.get(commit.get("author_id"), {})
                author_name = author_info.get("name") or "unknown"
                author_email = author_info.get("email") or "unknown"

                author_date = commit.get("author_date") or commit.get("committer_date")
                author_date_str = format_datetime(author_date)

                parents = commit.get("parents") or []
                if isinstance(parents, (list, tuple)):
                    parents_str = " ".join(str(p) for p in parents)
                else:
                    parents_str = str(parents) if parents else ""

                subject, body_lines = extract_subject_and_body(commit.get("message") or "")

                for file_idx, info in enumerate(fa_infos, start=1):
                    full_path = info["full_path"]
                    old_full_path = info["old_full_path"]
                    file_id = info["file_id"]
                    hunks = info["hunks"]
                    n_hunks_this_file = len(hunks)

                    if n_hunks_this_file == 0:
                        continue

                    for h in hunks:
                        hunk_oid = str(h["_id"])
                        out_path = commit_dir / f"{hunk_oid}.patch"

                        # try match git hunk
                        git_used = "no"
                        diff_excerpt_lines: List[str] = []

                        old_start = h.get("old_start")
                        old_len   = h.get("old_lines")
                        new_start = h.get("new_start")
                        new_len   = h.get("new_lines")

                        candidate_paths = [full_path]
                        if old_full_path and old_full_path != full_path:
                            candidate_paths.append(old_full_path)

                        if parsed_git:
                            picked = pick_git_hunk(
                                parsed_git,
                                candidate_paths=candidate_paths,
                                old_start=int(old_start) if old_start is not None else None,
                                old_len=int(old_len) if old_len is not None else None,
                                new_start=int(new_start) if new_start is not None else None,
                                new_len=int(new_len) if new_len is not None else None,
                            )
                            if picked:
                                file_header, hunk_lines = picked
                                diff_excerpt_lines = file_header + hunk_lines
                                git_used = "yes"

                        # fallback to mongo content if git not used
                        if git_used == "no":
                            # minimal diff header + mongo hunk content
                            diff_excerpt_lines.append(f"diff --git a/{full_path} b/{full_path}")
                            diff_excerpt_lines.append(f"--- a/{full_path}")
                            diff_excerpt_lines.append(f"+++ b/{full_path}")
                            content = h.get("content")
                            if content:
                                diff_excerpt_lines.extend(content.splitlines())
                            else:
                                os_ = old_start if old_start is not None else "?"
                                ol_ = old_len if old_len is not None else "?"
                                ns_ = new_start if new_start is not None else "?"
                                nl_ = new_len if new_len is not None else "?"
                                diff_excerpt_lines.append(f"@@ -{os_},{ol_} +{ns_},{nl_} @@")

                        # build output text
                        out_lines: List[str] = []
                        out_lines.append(f"Project: {project_name}")
                        if vcs_url:
                            out_lines.append(f"VCS URL: {vcs_url}")
                        if vcs_type:
                            out_lines.append(f"VCS type: {vcs_type}")
                        out_lines.append(f"Commit: {revision}")
                        out_lines.append(f"hunk_oid: {hunk_oid}")
                        out_lines.append(f"file_path: {full_path}")
                        out_lines.append("")
                        out_lines.append(f"n_files_per_commit: {n_files}")
                        out_lines.append(f"file_{file_idx}_out_of_{n_files}: FILE_ID:{file_id}")
                        out_lines.append(f"n_hunks_per_file_{file_idx}: {n_hunks_this_file}")
                        out_lines.append("")
                        if parents_str:
                            out_lines.append(f"Parents: {parents_str}")
                        out_lines.append(f"git_used: {git_used}")
                        out_lines.append("")
                        out_lines.append(f"Subject: {subject}")
                        if body_lines:
                            out_lines.append("")
                            out_lines.extend(body_lines)
                        out_lines.append("")
                        out_lines.extend(diff_excerpt_lines)
                        out_lines.append("")

                        out_text = "\n".join(out_lines)

                        with out_path.open("w", encoding="utf-8", errors="replace") as f:
                            f.write(out_text)

                if commit_count % 100 == 0:
                    print(f"    processed {commit_count} commits...")

            print(f"  -> total commits processed from this VCS: {commit_count}")

    print("\nAll done.")
    print(f"Output written under: {OUTPUT_ROOT}")
    print(f"Repos expected under: {REPO_ROOT} (AUTO_CLONE_IF_MISSING={AUTO_CLONE_IF_MISSING})")


if __name__ == "__main__":
    main()
