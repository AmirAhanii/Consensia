# -*- coding: utf-8 -*-
"""
PATCHES-ONLY + MONGO-ONLY + RESULTS summary (one .txt output)

UPDATED:
- Works with BOTH patch layouts:
    NEW (hunk layout):
        PATCHES_DIR/<project>/<revision_hash>/<hunk_oid>.patch
    OLD (commit layout):
        PATCHES_DIR/<project>/<revision_hash>.patch
- For NEW layout, computes UNIQUE HUNKS on disk EXACTLY by counting distinct <hunk_oid>
  filenames using an external merge-sort (memory-safe for millions of hunks).
- Includes your explanations inline in the PATCHES-ONLY summary.

Output:
  ROOT/out/summary_patches_only_mongo_only_results.txt
"""

from __future__ import annotations

import re
import time
import heapq
import tempfile
from pathlib import Path
from collections import Counter
from typing import Dict, Any, List, Tuple, Optional, Set, Iterator

from pymongo import MongoClient


# ====================== CONFIG ======================

ROOT = Path(r"C:\Users\ahmad\Desktop\Bilkent\5th year\1st sem\SDP - CS491\dataset_of_tangled_commits\Project's commits")

# >>> IMPORTANT: point this to your export root <<<
PATCHES_DIR = ROOT / "projects_patches"

OUT_DIR = ROOT / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_TXT = OUT_DIR / "summary_patches_only_mongo_only_results.txt"

PRINT_TOP_N = 20
PRINT_FIRST_N_DIST_ROWS = 30
PRINT_PROGRESS_EVERY_COMMITS = 2000

MAX_LINES_PER_PATCH_SCAN = 250  # scan window per patch file (fast)

# Exact unique hunks (NEW layout only):
COMPUTE_UNIQUE_HUNKS_EXACT = True
UNIQUE_HUNK_CHUNK_LINES = 500_000  # external sort chunk size (lines)

# Mongo
MONGO_DB   = "smartshark_1_2"
MONGO_HOST = "localhost"
MONGO_PORT = 27017
MONGO_USER = None
MONGO_PASS = None
MONGO_AUTH_DB = None

FORCE_HUNK_COLLECTION: Optional[str] = None
FORCE_HUNK_ID_FIELD: Optional[str] = None  # usually None -> _id

# ====================================================


# ===================== REGEX (PATCH HEADER) =====================

RE_VCS_URL   = re.compile(r"^\s*VCS URL:\s*(.+?)\s*$")
RE_COMMIT    = re.compile(r"^\s*Commit:\s*([0-9a-fA-F]+)\s*$")
RE_FILE_PATH = re.compile(r"^\s*file_path:\s*(.+?)\s*$")
RE_ATAT      = re.compile(r"^\s*@@")  # unified-diff hunk header line


# ===================== COMMON HELPERS =====================

def sanitize_name(name: str) -> str:
    bad_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for ch in bad_chars:
        name = name.replace(ch, "_")
    name = name.replace(" ", "_")
    return name

def tlog(msg: str) -> None:
    print(msg, flush=True)

def stats_from_dist(counter: Counter) -> Tuple[int, float, int, float]:
    if not counter:
        return 0, 0.0, 0, 0.0

    total = sum(counter.values())
    keys = sorted(counter.keys())
    mn = keys[0]
    mx = keys[-1]
    mean = sum(k * v for k, v in counter.items()) / total

    mid1 = (total - 1) // 2
    mid2 = total // 2
    cum = 0
    m1 = None
    m2 = None
    for k in keys:
        cum += counter[k]
        if m1 is None and cum > mid1:
            m1 = k
        if m2 is None and cum > mid2:
            m2 = k
            break
    med = (m1 + m2) / 2.0
    return mn, med, mx, mean

def format_dist(title: str, counter: Counter, first_n: int = 30, dash_len: int = 40) -> str:
    lines = []
    lines.append(title)
    lines.append("-" * dash_len)
    for k, v in sorted(counter.items(), key=lambda x: x[0])[:first_n]:
        lines.append(f"{k:>6} : {v:>8}")
    if len(counter) > first_n:
        lines.append(f"... ({len(counter) - first_n} more rows)")
    lines.append("")
    return "\n".join(lines)


# ===================== PATCH LAYOUT DETECTION =====================

def detect_patch_layout(patches_dir: Path) -> str:
    """
    Returns:
      - "hunk"   if patches_dir/<project>/<commit>/<hunk>.patch exists
      - "commit" if patches_dir/<project>/<commit>.patch exists
      - "unknown"
    """
    if not patches_dir.exists():
        return "unknown"

    # Try NEW hunk layout first
    for proj in patches_dir.iterdir():
        if not proj.is_dir():
            continue
        for commit_dir in proj.iterdir():
            if commit_dir.is_dir():
                for f in commit_dir.iterdir():
                    if f.is_file() and f.suffix.lower() == ".patch":
                        return "hunk"

    # Try OLD commit layout
    for proj in patches_dir.iterdir():
        if not proj.is_dir():
            continue
        for f in proj.iterdir():
            if f.is_file() and f.suffix.lower() == ".patch":
                return "commit"

    return "unknown"


# ===================== EXACT UNIQUE (external merge sort) =====================

def count_unique_lines_external(input_path: Path, chunk_lines: int) -> int:
    """
    Counts unique lines in input_path using external sort:
      1) read chunks, sort, write temp chunk files
      2) merge sorted chunks and count distinct
    Memory-safe for millions of lines.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="unique_hunks_"))
    chunk_files: List[Path] = []

    def write_chunk(sorted_lines: List[str], idx: int) -> Path:
        outp = tmp_dir / f"chunk_{idx:05d}.txt"
        outp.write_text("\n".join(sorted_lines) + "\n", encoding="utf-8")
        return outp

    # 1) create sorted chunks
    tlog("[UNIQUE] creating sorted chunks...")
    idx = 0
    buf: List[str] = []
    with input_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            buf.append(s)
            if len(buf) >= chunk_lines:
                buf.sort()
                chunk_files.append(write_chunk(buf, idx))
                idx += 1
                buf = []
    if buf:
        buf.sort()
        chunk_files.append(write_chunk(buf, idx))
        buf = []

    if not chunk_files:
        try:
            tmp_dir.rmdir()
        except Exception:
            pass
        return 0

    def iter_chunk(p: Path) -> Iterator[str]:
        with p.open("r", encoding="utf-8", errors="replace") as f:
            for ln in f:
                s = ln.strip()
                if s:
                    yield s

    # 2) merge + count uniques
    tlog(f"[UNIQUE] merging {len(chunk_files)} chunks to count uniques...")
    iters = [iter_chunk(p) for p in chunk_files]
    merged = heapq.merge(*iters)

    uniq = 0
    prev = None
    for s in merged:
        if s != prev:
            uniq += 1
            prev = s

    # cleanup
    try:
        for p in chunk_files:
            p.unlink(missing_ok=True)
        tmp_dir.rmdir()
    except Exception:
        pass

    return uniq


# ===================== PATCH PARSING =====================

def parse_patch_file_fast(patch_path: Path, max_lines: int) -> Tuple[str, str, str, bool]:
    """
    Returns (vcs_url, commit_hash, file_path, has_atat) scanning only first max_lines.
    """
    vcs_url = ""
    commit_hash = ""
    file_path = ""
    has_atat = False

    try:
        with patch_path.open("r", encoding="utf-8", errors="replace") as f:
            for _ in range(max_lines):
                ln = f.readline()
                if not ln:
                    break
                s = ln.rstrip("\n")

                if not vcs_url:
                    m = RE_VCS_URL.match(s)
                    if m:
                        vcs_url = m.group(1).strip()

                if not commit_hash:
                    m = RE_COMMIT.match(s)
                    if m:
                        commit_hash = m.group(1).strip()

                if not file_path:
                    m = RE_FILE_PATH.match(s)
                    if m:
                        file_path = m.group(1).strip()

                if not has_atat and RE_ATAT.match(s):
                    has_atat = True

                if vcs_url and commit_hash and file_path and has_atat:
                    break

    except Exception:
        return "", "", "", False

    return vcs_url, commit_hash, file_path, has_atat


# ===================== PATCHES-ONLY SCAN (NEW layout) =====================

def scan_patches_only_hunk_layout(patches_dir: Path) -> Dict[str, Any]:
    """
    NEW layout:
      patches_dir/<project>/<revision_hash>/<hunk_oid>.patch

    Commit-level:
      n_hunks = number of patch files in commit folder
      n_files = number of unique file_path across those hunks
      has_atat = ANY hunk file contains '@@' within scan window
    """
    patch_projects = sorted([d.name for d in patches_dir.iterdir() if d.is_dir()])

    patch_commit_rows: List[Dict[str, Any]] = []
    patch_keys: Set[Tuple[str, str]] = set()
    patch_commit_stats: Dict[Tuple[str, str], Dict[str, Any]] = {}

    commits_scanned = 0
    empty_commit_dirs = 0
    total_patch_files = 0
    commits_with_0_atat = 0

    files_dist = Counter()
    hunks_dist = Counter()
    single_file = single_hunk = single_both = 0

    repo_urls: Set[str] = set()
    repo_file_pairs: Set[Tuple[str, str]] = set()  # (repo_url, file_path)

    # for EXACT unique hunks
    unique_id_list_path: Optional[Path] = None
    unique_writer = None
    if COMPUTE_UNIQUE_HUNKS_EXACT:
        import os
        fd, tmp = tempfile.mkstemp(prefix="hunk_ids_", suffix=".txt")
        os.close(fd)
        unique_id_list_path = Path(tmp)
        unique_writer = unique_id_list_path.open("w", encoding="utf-8", errors="replace")
        tlog(f"[UNIQUE] writing all hunk_oids to temp list: {unique_id_list_path}")

    t0 = time.time()

    for proj_name in patch_projects:
        proj_dir = patches_dir / proj_name
        if not proj_dir.is_dir():
            continue

        for commit_dir in proj_dir.iterdir():
            if not commit_dir.is_dir():
                continue

            rev = commit_dir.name
            key = (proj_name, rev)

            patch_files = [f for f in commit_dir.iterdir() if f.is_file() and f.suffix.lower() == ".patch"]
            if not patch_files:
                empty_commit_dirs += 1
                continue

            commits_scanned += 1
            total_patch_files += len(patch_files)
            patch_keys.add(key)

            file_paths: Set[str] = set()
            repo_url = ""
            any_atat = False

            # write hunk ids for exact unique count
            if unique_writer is not None:
                for pf in patch_files:
                    unique_writer.write(pf.stem + "\n")

            for pf in patch_files:
                vcs_url, _, file_path, has_atat = parse_patch_file_fast(pf, MAX_LINES_PER_PATCH_SCAN)

                if not repo_url and vcs_url:
                    repo_url = vcs_url.strip()

                if file_path:
                    file_paths.add(file_path.strip())

                if has_atat:
                    any_atat = True

                if vcs_url and file_path:
                    repo_file_pairs.add((vcs_url.strip(), file_path.strip()))

            if repo_url:
                repo_urls.add(repo_url)

            n_hunks = len(patch_files)
            n_files = len(file_paths)

            if not any_atat:
                commits_with_0_atat += 1

            hunks_dist[n_hunks] += 1
            files_dist[n_files] += 1

            if n_files == 1:
                single_file += 1
            if n_hunks == 1:
                single_hunk += 1
            if n_files == 1 and n_hunks == 1:
                single_both += 1

            patch_commit_stats[key] = {
                "repository_url": repo_url,
                "revision_hash": rev,
                "project": proj_name,
                "n_hunks": n_hunks,
                "n_files": n_files,
                "has_atat": any_atat,
            }

            patch_commit_rows.append({
                "repository_url": repo_url,
                "revision_hash": rev,
                "n_hunks": n_hunks,
                "n_files": n_files,
                "project": proj_name,
                "issue_id": "",
            })

            if PRINT_PROGRESS_EVERY_COMMITS and commits_scanned % PRINT_PROGRESS_EVERY_COMMITS == 0:
                tlog(f"[PATCHES] commits_scanned={commits_scanned:,} | patch_files={total_patch_files:,} | elapsed={time.time()-t0:.1f}s")

    if unique_writer is not None:
        unique_writer.close()

    top_by_hunks = sorted(patch_commit_rows, key=lambda x: (-x["n_hunks"], -x["n_files"]))[:PRINT_TOP_N]
    top_by_files = sorted(patch_commit_rows, key=lambda x: (-x["n_files"], -x["n_hunks"]))[:PRINT_TOP_N]

    # exact unique hunks on disk
    unique_hunks_exact = None
    if unique_id_list_path is not None:
        tlog("[UNIQUE] counting exact unique hunks on disk...")
        unique_hunks_exact = count_unique_lines_external(unique_id_list_path, UNIQUE_HUNK_CHUNK_LINES)
        try:
            unique_id_list_path.unlink(missing_ok=True)
        except Exception:
            pass

    return {
        "layout": "hunk",
        "patch_projects": set(patch_projects),
        "commits_scanned": commits_scanned,
        "empty_commit_dirs": empty_commit_dirs,
        "total_patch_files": total_patch_files,
        "unique_hunks_exact": unique_hunks_exact,
        "commits_with_0_atat": commits_with_0_atat,
        "repo_urls": repo_urls,
        "repo_file_pairs_count": len(repo_file_pairs),
        "hunks_dist": hunks_dist,
        "files_dist": files_dist,
        "single_file": single_file,
        "single_hunk": single_hunk,
        "single_both": single_both,
        "top_by_hunks": top_by_hunks,
        "top_by_files": top_by_files,
        "commit_stats": patch_commit_stats,
        "keys": patch_keys,
    }


# ===================== PATCHES-ONLY SCAN (OLD layout) =====================

def scan_patches_only_commit_layout(patches_dir: Path) -> Dict[str, Any]:
    """
    OLD layout:
      patches_dir/<project>/<revision_hash>.patch
    """
    RE_DIFF_GIT = re.compile(r"^\s*diff --git a/(.*?) b/(.*?)\s*$")
    RE_FILE_HDR = re.compile(r"^(---|\+\+\+)\s")
    RE_CHANGE   = re.compile(r"^[+-]")

    def parse_commit_patch_counts(text: str) -> Tuple[int, int, bool]:
        n_files = 0
        implied = 0
        has_atat = False

        in_file = False
        file_has_change = False

        for ln in text.splitlines():
            if RE_DIFF_GIT.match(ln):
                if in_file and file_has_change:
                    implied += 1
                n_files += 1
                in_file = True
                file_has_change = False
                continue

            if RE_ATAT.match(ln):
                has_atat = True

            if not in_file:
                continue

            if RE_CHANGE.match(ln) and not RE_FILE_HDR.match(ln):
                file_has_change = True

        if in_file and file_has_change:
            implied += 1

        return n_files, implied, has_atat

    patch_projects = sorted([d.name for d in patches_dir.iterdir() if d.is_dir()])

    commits_scanned = 0
    total_patch_files = 0
    commits_with_0_atat = 0

    hunks_dist = Counter()
    files_dist = Counter()

    single_file = single_hunk = single_both = 0
    repo_urls: Set[str] = set()

    patch_commit_rows: List[Dict[str, Any]] = []
    patch_keys: Set[Tuple[str, str]] = set()
    patch_commit_stats: Dict[Tuple[str, str], Dict[str, Any]] = {}

    t0 = time.time()

    for proj_name in patch_projects:
        proj_dir = patches_dir / proj_name
        if not proj_dir.is_dir():
            continue

        for pf in proj_dir.iterdir():
            if not pf.is_file() or pf.suffix.lower() != ".patch":
                continue

            commits_scanned += 1
            total_patch_files += 1

            rev = pf.stem
            key = (proj_name, rev)
            patch_keys.add(key)

            # quick read VCS URL from header
            repo_url = ""
            try:
                with pf.open("r", encoding="utf-8", errors="replace") as f:
                    for _ in range(80):
                        ln = f.readline()
                        if not ln:
                            break
                        m = RE_VCS_URL.match(ln.rstrip("\n"))
                        if m:
                            repo_url = m.group(1).strip()
                            break
                        if ln.startswith("diff --git "):
                            break
            except Exception:
                repo_url = ""
            if repo_url:
                repo_urls.add(repo_url)

            try:
                text = pf.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            n_files, n_hunks, has_atat = parse_commit_patch_counts(text)
            if not has_atat:
                commits_with_0_atat += 1

            hunks_dist[n_hunks] += 1
            files_dist[n_files] += 1

            if n_files == 1:
                single_file += 1
            if n_hunks == 1:
                single_hunk += 1
            if n_files == 1 and n_hunks == 1:
                single_both += 1

            patch_commit_stats[key] = {
                "repository_url": repo_url,
                "revision_hash": rev,
                "project": proj_name,
                "n_hunks": n_hunks,
                "n_files": n_files,
                "has_atat": has_atat,
            }

            patch_commit_rows.append({
                "repository_url": repo_url,
                "revision_hash": rev,
                "n_hunks": n_hunks,
                "n_files": n_files,
                "project": proj_name,
                "issue_id": "",
            })

            if PRINT_PROGRESS_EVERY_COMMITS and commits_scanned % PRINT_PROGRESS_EVERY_COMMITS == 0:
                tlog(f"[PATCHES] commits_scanned={commits_scanned:,} | elapsed={time.time()-t0:.1f}s")

    top_by_hunks = sorted(patch_commit_rows, key=lambda x: (-x["n_hunks"], -x["n_files"]))[:PRINT_TOP_N]
    top_by_files = sorted(patch_commit_rows, key=lambda x: (-x["n_files"], -x["n_hunks"]))[:PRINT_TOP_N]

    return {
        "layout": "commit",
        "patch_projects": set(patch_projects),
        "commits_scanned": commits_scanned,
        "empty_commit_dirs": 0,
        "total_patch_files": total_patch_files,
        "unique_hunks_exact": None,
        "commits_with_0_atat": commits_with_0_atat,
        "repo_urls": repo_urls,
        "repo_file_pairs_count": 0,
        "hunks_dist": hunks_dist,
        "files_dist": files_dist,
        "single_file": single_file,
        "single_hunk": single_hunk,
        "single_both": single_both,
        "top_by_hunks": top_by_hunks,
        "top_by_files": top_by_files,
        "commit_stats": patch_commit_stats,
        "keys": patch_keys,
    }


# ===================== MONGO HELPERS =====================

def mongo_client() -> MongoClient:
    if MONGO_USER and MONGO_PASS:
        uri = f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/"
        return MongoClient(uri, authSource=(MONGO_AUTH_DB or MONGO_DB), serverSelectionTimeoutMS=8000)
    return MongoClient(MONGO_HOST, MONGO_PORT, serverSelectionTimeoutMS=8000)

def pick_hunk_collection(db) -> str:
    if FORCE_HUNK_COLLECTION:
        return FORCE_HUNK_COLLECTION

    names = db.list_collection_names()
    likely = [n for n in names if n.lower() in ("hunk", "hunks", "hunk_labels", "hunklabels", "annotation", "annotations")]
    rest = [n for n in names if n not in likely]

    for col_name in (likely + rest):
        col = db[col_name]
        doc = col.find_one({"lines_manual": {"$exists": True}}, {"_id": 1})
        if doc is not None:
            return col_name

    raise RuntimeError("Could not auto-detect hunk/annotation collection (no docs with lines_manual). Set FORCE_HUNK_COLLECTION.")

def normalize_label(lab: str) -> str:
    return "bugfix" if lab == "bug" else lab

def mongo_annotators_and_labels(db, hunk_col_name: str) -> Tuple[List[str], List[str]]:
    col = db[hunk_col_name]

    annot_pipeline = [
        {"$match": {"lines_manual": {"$type": "object"}}},
        {"$project": {"pairs": {"$objectToArray": "$lines_manual"}}},
        {"$unwind": "$pairs"},
        {"$group": {"_id": "$pairs.k"}},
    ]
    annotators = [str(d["_id"]) for d in col.aggregate(annot_pipeline, allowDiskUse=True)]

    label_pipeline = [
        {"$match": {"lines_manual": {"$type": "object"}}},
        {"$project": {"pairs": {"$objectToArray": "$lines_manual"}}},
        {"$unwind": "$pairs"},
        {"$match": {"pairs.v": {"$type": "object"}}},
        {"$project": {"labpairs": {"$objectToArray": "$pairs.v"}}},
        {"$unwind": "$labpairs"},
        {"$group": {"_id": "$labpairs.k"}},
    ]
    labels = [normalize_label(str(d["_id"])) for d in col.aggregate(label_pipeline, allowDiskUse=True)]

    return sorted(set(annotators)), sorted(set(labels))

def mongo_entries_and_unique_hunks(db, hunk_col_name: str) -> Tuple[int, int]:
    col = db[hunk_col_name]
    entries = col.count_documents({"lines_manual": {"$exists": True}})

    hunk_id_field = FORCE_HUNK_ID_FIELD or "_id"
    pipeline = [
        {"$match": {"lines_manual": {"$exists": True}}},
        {"$group": {"_id": f"${hunk_id_field}"}},
        {"$count": "n"},
    ]
    out = list(col.aggregate(pipeline, allowDiskUse=True))
    unique_hunks = int(out[0]["n"]) if out else 0
    return entries, unique_hunks

def mongo_commit_level_counts_smartshark(
    db, hunk_col_name: str
) -> Tuple[int, Counter, Counter, int, int, int, List[Dict[str, Any]]]:
    hunk_col = db[hunk_col_name]

    pipeline = [
        {"$match": {"file_action_id": {"$exists": True, "$ne": None}}},
        {"$project": {"file_action_id": 1}},
        {"$lookup": {"from": "file_action", "localField": "file_action_id", "foreignField": "_id", "as": "fa"}},
        {"$unwind": "$fa"},
        {"$project": {"commit_id": "$fa.commit_id", "file_id": "$fa.file_id"}},
        {"$match": {"commit_id": {"$ne": None}}},
        {"$group": {"_id": "$commit_id", "n_hunks": {"$sum": 1}, "files": {"$addToSet": "$file_id"}}},
        {"$project": {
            "commit_id": "$_id",
            "n_hunks": 1,
            "n_files": {"$size": {"$filter": {"input": "$files", "as": "f", "cond": {"$ne": ["$$f", None]}}}},
        }},
        {"$lookup": {"from": "commit", "localField": "commit_id", "foreignField": "_id", "as": "c"}},
        {"$unwind": "$c"},
        {"$lookup": {"from": "vcs_system", "localField": "c.vcs_system_id", "foreignField": "_id", "as": "vs"}},
        {"$unwind": {"path": "$vs", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "project", "localField": "vs.project_id", "foreignField": "_id", "as": "p"}},
        {"$unwind": {"path": "$p", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "revision_hash": {"$ifNull": ["$c.revision_hash", ""]},
            "repository_url": {"$ifNull": ["$vs.url", ""]},
            "project": {"$ifNull": ["$p.name", ""]},
            "n_hunks": 1,
            "n_files": 1,
        }},
    ]

    hunks_dist = Counter()
    files_dist = Counter()
    single_file = single_hunk = single_both = 0
    rows: List[Dict[str, Any]] = []

    n_commits = 0
    for doc in hunk_col.aggregate(pipeline, allowDiskUse=True):
        n_commits += 1
        nh = int(doc.get("n_hunks", 0))
        nf = int(doc.get("n_files", 0))

        hunks_dist[nh] += 1
        files_dist[nf] += 1

        if nf == 1:
            single_file += 1
        if nh == 1:
            single_hunk += 1
        if nf == 1 and nh == 1:
            single_both += 1

        rows.append({
            "repository_url": (doc.get("repository_url") or "").strip(),
            "revision_hash": (doc.get("revision_hash") or "").strip(),
            "project": (doc.get("project") or "").strip(),
            "n_hunks": nh,
            "n_files": nf,
            "issue_id": "",
        })

    return n_commits, hunks_dist, files_dist, single_file, single_hunk, single_both, rows

def mongo_unique_repo_file_pairs(db, hunk_col_name: str) -> int:
    hunk_col = db[hunk_col_name]
    names = set(db.list_collection_names())
    if "file_action" not in names or "commit" not in names or "vcs_system" not in names:
        return 0
    have_file = "file" in names

    pipeline: List[Dict[str, Any]] = [
        {"$match": {"file_action_id": {"$exists": True, "$ne": None}}},
        {"$project": {"file_action_id": 1}},
        {"$lookup": {"from": "file_action", "localField": "file_action_id", "foreignField": "_id", "as": "fa"}},
        {"$unwind": "$fa"},
        {"$lookup": {"from": "commit", "localField": "fa.commit_id", "foreignField": "_id", "as": "c"}},
        {"$unwind": "$c"},
        {"$lookup": {"from": "vcs_system", "localField": "c.vcs_system_id", "foreignField": "_id", "as": "vs"}},
        {"$unwind": {"path": "$vs", "preserveNullAndEmptyArrays": True}},
    ]

    if have_file:
        pipeline += [
            {"$lookup": {"from": "file", "localField": "fa.file_id", "foreignField": "_id", "as": "fd"}},
            {"$unwind": {"path": "$fd", "preserveNullAndEmptyArrays": True}},
            {"$project": {
                "repo": {"$ifNull": ["$vs.url", ""]},
                "file_id": "$fa.file_id",
                "path": {"$ifNull": ["$fd.path", ""]},
                "name": {"$ifNull": ["$fd.name", ""]},
            }},
            {"$project": {
                "repo": 1,
                "file_key": {
                    "$cond": [
                        {"$and": [{"$ne": ["$name", ""]}, {"$ne": ["$name", None]}]},
                        {"$concat": [
                            {"$cond": [{"$or": [{"$eq": ["$path", ""]}, {"$eq": ["$path", None]}]}, "", "$path"]},
                            {"$cond": [{"$or": [{"$eq": ["$path", ""]}, {"$eq": ["$path", None]}]}, "", "/"]},
                            "$name"
                        ]},
                        {"$toString": "$file_id"}
                    ]
                }
            }},
        ]
    else:
        pipeline += [
            {"$project": {
                "repo": {"$ifNull": ["$vs.url", ""]},
                "file_key": {"$toString": "$fa.file_id"},
            }},
        ]

    pipeline += [
        {"$match": {"repo": {"$type": "string", "$ne": ""}, "file_key": {"$type": "string", "$ne": ""}}},
        {"$group": {"_id": {"repo": "$repo", "file": "$file_key"}}},
        {"$count": "n"},
    ]
    out = list(hunk_col.aggregate(pipeline, allowDiskUse=True))
    return int(out[0]["n"]) if out else 0


# ===================== MAIN =====================

def main() -> None:
    if not PATCHES_DIR.exists():
        raise FileNotFoundError(f"PATCHES_DIR not found: {PATCHES_DIR}")

    tlog(f"[START] PATCHES_DIR = {PATCHES_DIR}")
    layout = detect_patch_layout(PATCHES_DIR)
    tlog(f"[PATCHES] detected layout = {layout}")

    if layout == "hunk":
        patch = scan_patches_only_hunk_layout(PATCHES_DIR)
        patch_hunk_definition = "1-hunk = exactly 1 exported hunk file in the commit folder."
    elif layout == "commit":
        patch = scan_patches_only_commit_layout(PATCHES_DIR)
        patch_hunk_definition = "1-hunk = implied_hunks = number of changed file-blocks (old commit.patch format)."
    else:
        raise RuntimeError(
            "Could not detect patch layout. Ensure PATCHES_DIR points to your export root.\n"
            "Expected either:\n"
            "  - NEW: projects_patches/<project>/<commit>/<hunk>.patch\n"
            "  - OLD: projects_patches/<project>/<commit>.patch"
        )

    # ---- Mongo-only ----
    tlog("[MONGO] connecting...")
    client = mongo_client()
    client.admin.command("ping")
    db = client[MONGO_DB]
    tlog("[MONGO] connected + ping ok")

    hunk_col_name = pick_hunk_collection(db)
    tlog(f"[MONGO] using hunk collection: {hunk_col_name}")

    tlog("[MONGO] computing entries + unique annotated hunks...")
    mongo_entries, mongo_unique_hunks_annot = mongo_entries_and_unique_hunks(db, hunk_col_name)

    tlog("[MONGO] extracting annotators + labels...")
    annotators, labels = mongo_annotators_and_labels(db, hunk_col_name)

    tlog("[MONGO] computing commit-level counts (can take a while)...")
    (
        n_mongo_commits,
        mongo_hunks_dist,
        mongo_files_dist,
        mongo_single_file,
        mongo_single_hunk,
        mongo_single_both,
        mongo_rows
    ) = mongo_commit_level_counts_smartshark(db, hunk_col_name)

    mongo_repo_urls = set(r["repository_url"] for r in mongo_rows if (r.get("repository_url") or "").strip())
    mongo_projects_raw = set(r["project"] for r in mongo_rows if (r.get("project") or "").strip())
    mongo_projects = set(sanitize_name(p) for p in mongo_projects_raw)

    tlog("[MONGO] computing unique (repo,file) pairs...")
    mongo_repo_file_pairs = mongo_unique_repo_file_pairs(db, hunk_col_name)

    # top tables (Mongo)
    top_mongo_by_hunks = sorted(mongo_rows, key=lambda x: (-x["n_hunks"], -x["n_files"]))[:PRINT_TOP_N]
    top_mongo_by_files = sorted(mongo_rows, key=lambda x: (-x["n_files"], -x["n_hunks"]))[:PRINT_TOP_N]

    # ---- PATCHES derived stats ----
    patch_hunks_dist = patch["hunks_dist"]
    patch_files_dist = patch["files_dist"]

    ph_mn, ph_med, ph_mx, ph_mean = stats_from_dist(patch_hunks_dist)
    pf_mn, pf_med, pf_mx, pf_mean = stats_from_dist(patch_files_dist)
    mh_mn, mh_med, mh_mx, mh_mean = stats_from_dist(mongo_hunks_dist)
    mf_mn, mf_med, mf_mx, mf_mean = stats_from_dist(mongo_files_dist)

    # ---- RESULTS overlap ----
    patch_keys: Set[Tuple[str, str]] = patch["keys"]

    mongo_commit_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
    mongo_keys: Set[Tuple[str, str]] = set()
    for r in mongo_rows:
        proj = sanitize_name((r.get("project") or "").strip())
        rev  = (r.get("revision_hash") or "").strip()
        if not proj or not rev:
            continue
        k = (proj, rev)
        mongo_keys.add(k)
        mongo_commit_map[k] = r

    both_keys = patch_keys & mongo_keys
    patch_only_keys = patch_keys - mongo_keys
    mongo_only_keys = mongo_keys - patch_keys

    patch_commit_stats = patch["commit_stats"]

    def is_1file1hunk_patch(k: Tuple[str, str]) -> bool:
        d = patch_commit_stats.get(k)
        return bool(d) and int(d.get("n_files", 0)) == 1 and int(d.get("n_hunks", 0)) == 1

    def is_1file1hunk_mongo(k: Tuple[str, str]) -> bool:
        d = mongo_commit_map.get(k)
        return bool(d) and int(d.get("n_files", 0)) == 1 and int(d.get("n_hunks", 0)) == 1

    shared_patch_yes_mongo_no = [k for k in both_keys if is_1file1hunk_patch(k) and not is_1file1hunk_mongo(k)]
    shared_mongo_yes_patch_no = [k for k in both_keys if is_1file1hunk_mongo(k) and not is_1file1hunk_patch(k)]

    shared_patch_yes_mongo_no_atat0 = 0
    for k in shared_patch_yes_mongo_no:
        d = patch_commit_stats.get(k)
        if d and not bool(d.get("has_atat", False)):
            shared_patch_yes_mongo_no_atat0 += 1

    # ---- Write report ----
    with OUT_TXT.open("w", encoding="utf-8") as f:
        def w(line: str = ""):
            f.write(line + "\n")

        # PATCHES-ONLY summary with your explanations
        w("=== Dataset summary (PATCHES-ONLY; from projects_patches export) ===")
        w(f"Patch layout detected               : {patch['layout']}")
        w(f"Projects (patch folders)            : {len(patch['patch_projects']):,}")
        w(f"Commits scanned                     : {patch['commits_scanned']:,}")

        if patch["layout"] == "hunk":
            w(f"Empty commit folders (no .patch)    : {patch['empty_commit_dirs']:,} (empty commit folder = “commit is known, but SmartSHARK has no hunks to export for it.”)")
            w(f"Entries (patch files; 1 per hunk)   : {patch['total_patch_files']:,} (Entries ≈ total number of hunks exported)")
            if patch.get("unique_hunks_exact") is not None:
                uniq = int(patch["unique_hunks_exact"])
                dup = int(patch["total_patch_files"]) - uniq
                w(f"Unique hunks (exact)                : {uniq:,} (distinct <hunk_oid>.patch filenames across all commits; duplicates={dup:,})")
            else:
                w(f"Unique hunks (exact)                : N/A (COMPUTE_UNIQUE_HUNKS_EXACT=False)")
            w(f"Repositories (unique VCS URL)       : {len(patch['repo_urls']):,}")
            w(f"Unique (repo,file) pairs            : {patch['repo_file_pairs_count']:,} (from VCS URL + file_path header) (across all repos, you saw {patch['repo_file_pairs_count']:,} distinct file paths (deduplicated per repo))")
        else:
            w("Empty commit folders (no .patch)    : N/A (old commit.patch layout has no commit folders)")
            w(f"Entries (patch files; 1 per commit) : {patch['total_patch_files']:,}")
            w("Unique hunks (exact)                : N/A (old commit.patch layout stores one patch per commit)")
            w(f"Repositories (unique VCS URL)       : {len(patch['repo_urls']):,}")
            w("Unique (repo,file) pairs            : N/A (old commit.patch layout has no stable file_path header)")
        w("")

        w("=== Commit-level counts (PATCHES-ONLY) ===")
        w(f"Definition: {patch_hunk_definition}")
        w(f"Patches/commits with 0 '@@' lines    : {patch['commits_with_0_atat']:,} (commit folder where NONE of its .patch files contains a unified-diff hunk header '@@' within the first {MAX_LINES_PER_PATCH_SCAN} lines scanned)")
        w(f"Patch 1-file commits                 : {patch['single_file']:,}")
        w(f"Patch 1-hunk commits                 : {patch['single_hunk']:,}")
        w(f"Patch 1-file AND 1-hunk commits      : {patch['single_both']:,}")
        w("")
        w(format_dist("Distribution: hunks per commit (patch)", patch_hunks_dist, PRINT_FIRST_N_DIST_ROWS, dash_len=40))
        w(f"min={ph_mn}  median={ph_med:.2f}  max={ph_mx}  mean={ph_mean:.2f}\n")
        w(format_dist("Distribution: files per commit (patch)", patch_files_dist, PRINT_FIRST_N_DIST_ROWS, dash_len=40))
        w(f"min={pf_mn}  median={pf_med:.2f}  max={pf_mx}  mean={pf_mean:.2f}\n")

        # MONGO-ONLY
        w("=== Dataset summary (MONGO-ONLY; from MongoDB joins) ===")
        w(f"Entries (rows in JSON-style)        : {mongo_entries:,}  (Mongo: hunks with lines_manual)")
        w(f"Unique hunks (annotated)            : {mongo_unique_hunks_annot:,}  (Mongo distinct among annotated docs)")
        w(f"Commits (unique repo+revision_hash) : {n_mongo_commits:,}  (SmartSHARK joins from '{hunk_col_name}')")
        w(f"Projects (Mongo join project.name)  : {len(mongo_projects):,}  (sanitized for comparison)")
        w(f"Repositories (unique repository_url): {len(mongo_repo_urls):,}")
        w(f"Unique (repo,file) pairs            : {mongo_repo_file_pairs:,}")
        w("")

        w("=== Annotators / labels (MONGO-ONLY) ===")
        w(f"Unique annotators seen              : {len(annotators):,}  (Mongo lines_manual keys)")
        w(f"Annotator IDs (first 20)            : " + ", ".join(annotators[:20]))
        w(f"Unique label names seen             : {len(labels):,}  (Mongo lines_manual.<ann>.<label> keys)")
        w("Labels                              : " + ", ".join(labels))
        w("")

        # RESULTS block
        w("")
        w("==================== RESULTS ====================")
        w("")
        w("--- Option A (Mongo-truth) ---")
        w(f"Mongo commits (from hunks join)        : {n_mongo_commits:,}")
        w(f"Mongo 1-file commits                  : {mongo_single_file:,}")
        w(f"Mongo 1-hunk commits                  : {mongo_single_hunk:,}")
        w(f"Mongo 1-file AND 1-hunk commits       : {mongo_single_both:,}")
        w("Definition: 1-hunk = exactly 1 SmartSHARK hunk document in that commit.")
        w("")
        w("--- Option B (Patch-truth) ---")
        w(f"Patch commits scanned                 : {patch['commits_scanned']:,}")
        w(f"Patches/commits with 0 '@@' lines     : {patch['commits_with_0_atat']:,}")
        w(f"Patch 1-file AND 1-hunk               : {patch['single_both']:,}")
        w(f"Definition: {patch_hunk_definition}")
        w("")
        w("--- Cross-source overlap (key = (project, revision_hash)) ---")
        w(f"Keys in both patch & mongo            : {len(both_keys):,}")
        w(f"Patch-only keys (no mongo match)      : {len(patch_only_keys):,}")
        w(f"Mongo-only keys (no patch match)      : {len(mongo_only_keys):,}")
        w("")
        w("--- Where the mismatch comes from (on shared keys) ---")
        w(f"Patch says 1file1hunk BUT Mongo says NOT : {len(shared_patch_yes_mongo_no):,}")
        w(f"  of those, patch has 0 '@@' lines       : {shared_patch_yes_mongo_no_atat0:,}")
        w(f"Mongo says 1file1hunk BUT Patch says NOT : {len(shared_mongo_yes_patch_no):,}")
        w("")
        w("--- Interpretation note ---")
        w("If your export has almost no '@@', most diff excerpts are not true unified-diff hunks.")
        w("That is not necessarily a problem if you only need +/- lines, but it limits Git-like hunk parsing.")
        w("")
        w("[DEBUG]")
        w(f"Mongo hunk collection used: {hunk_col_name}")
        w(f"Patch folder projects: {len(patch['patch_projects']):,}")
        w(f"Mongo projects (from join, sanitized): {len(mongo_projects):,}")

    tlog(f"\n[SAVED] Report written to:\n  {OUT_TXT}")


if __name__ == "__main__":
    main()
