# -*- coding: utf-8 -*-
"""
Lvl1 LABELED builder (Mongo truth for lvl1) + PATCH join by hunk_oid

- Labeled hunks: Mongo `hunk` documents where `lines_manual` exists.
- Lvl1 commits: commit has exactly 1 file and 1 hunk (computed from ALL hunks).
- Output rows ONLY for lvl1 commits where the single hunk is labeled.
- Participants: write ONLY labelers (no 64 empty keys).
- Patch join: reads projects_patches/<project>/<revision_hash>/<hunk_oid>.patch
  to add:
    - context_code_patch (diff body after +++ line; fallback: changed +/- lines)
  and to FIX file_path when Mongo path is missing/FILE_ID:
    - file_path taken from patch header `file_path:`

Outputs:
- out/lvl1_labeled_only_labelers_grouped.json
- out/lvl1_labeled_only_labelers.jsonl
- out/lvl1_labeled_only_labelers.parquet   (participants stored as JSON string column)
"""

from __future__ import annotations

import json
import time
import re
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Any, Tuple

import pandas as pd
from pymongo import MongoClient


# ===================== CONFIG =====================

ROOT = Path(r"C:\Users\ahmad\Desktop\Bilkent\5th year\1st sem\SDP - CS491\dataset_of_tangled_commits\Project's commits")

# Patch export root (NEW hunk layout):
#   projects_patches/<project>/<revision_hash>/<hunk_oid>.patch
PATCHES_DIR = ROOT / "projects_patches"

OUT_DIR = ROOT / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_GROUPED_JSON = OUT_DIR / "lvl1_labeled_only_labelers_grouped.json"
OUT_JSONL        = OUT_DIR / "lvl1_labeled_only_labelers.jsonl"
OUT_PARQUET      = OUT_DIR / "lvl1_labeled_only_labelers.parquet"

HUNK_COL = "hunk"  # SmartSHARK collection

PRINT_EVERY_STAGE1 = 20000
PRINT_EVERY_STAGE2 = 2000
BATCH = 5000

# Mongo
MONGO_DB   = "smartshark_1_2"
MONGO_HOST = "localhost"
MONGO_PORT = 27017
MONGO_USER = None
MONGO_PASS = None
MONGO_AUTH_DB = None


# ===================== HELPERS =====================

RE_PATCH_FILE_PATH = re.compile(r"^\s*file_path:\s*(.+?)\s*$", re.IGNORECASE)

def sanitize_name(name: str) -> str:
    bad_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for ch in bad_chars:
        name = name.replace(ch, "_")
    return name.replace(" ", "_")

def canonicalize_file_path_keep_trailing_slash(p: str) -> str:
    """
    User preference: output file_path like ".../File.java/" (trailing slash).
    - remove leading slashes
    - collapse trailing slashes to exactly ONE
    """
    p = (p or "").strip()
    while p.startswith("/"):
        p = p[1:]
    while p.endswith("/"):
        p = p[:-1]
    return (p + "/") if p else ""

def is_missing_or_fileid(p: str) -> bool:
    p = (p or "").strip()
    return (not p) or p.startswith("FILE_ID:")

def mongo_client() -> MongoClient:
    if MONGO_USER and MONGO_PASS:
        uri = f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/"
        return MongoClient(uri, authSource=(MONGO_AUTH_DB or MONGO_DB), serverSelectionTimeoutMS=8000)
    return MongoClient(MONGO_HOST, MONGO_PORT, serverSelectionTimeoutMS=8000)


# ===================== CONSENSUS =====================

def normalize_label(lab: str) -> str:
    return "bugfix" if lab == "bug" else lab

def compute_line_votes(lines_manual: Dict[str, Dict[str, List[int]]]) -> Dict[int, Counter]:
    votes: Dict[int, Counter] = defaultdict(Counter)
    for _, user_labels in lines_manual.items():
        if not isinstance(user_labels, dict):
            continue
        for label_type, line_list in user_labels.items():
            lt = normalize_label(str(label_type))
            if not isinstance(line_list, list):
                continue
            for li in line_list:
                if isinstance(li, int):
                    votes[li][lt] += 1
    return votes

def compute_line_consensus(votes: Dict[int, Counter], threshold: int = 3) -> Dict[int, str]:
    out: Dict[int, str] = {}
    for li, c in votes.items():
        ok = [(lab, cnt) for lab, cnt in c.items() if cnt >= threshold]
        if not ok:
            continue
        ok.sort(key=lambda x: (-x[1], x[0]))
        out[li] = ok[0][0]
    return out

def compute_hunk_consensus_from_line_consensus(line_consensus: Dict[int, str]) -> str:
    if not line_consensus:
        return "no_agreement"
    c = Counter(line_consensus.values())
    top = c.most_common()
    if not top:
        return "no_agreement"
    if len(top) > 1 and top[1][1] == top[0][1]:
        return "no_agreement"
    return top[0][0]


# ===================== PATCH JOIN =====================

def extract_patch_body_after_plusplus(patch_text: str) -> str:
    """
    Prefer: all lines after the first '+++ ' line.
    Fallback: only changed +/- lines (excluding ---/+++ headers).
    """
    lines = patch_text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith("+++ "):
            start = i + 1
            break
    if start is not None and start < len(lines):
        body = "\n".join(lines[start:]).rstrip()
        return (body + "\n") if body else ""

    out = []
    for ln in lines:
        if ln.startswith("+++ ") or ln.startswith("--- "):
            continue
        if ln.startswith("+") or ln.startswith("-"):
            out.append(ln)
    body = "\n".join(out).rstrip()
    return (body + "\n") if body else ""

def read_patch_for_hunk(project: str, revision_hash: str, hunk_oid: str) -> Tuple[str, bool]:
    """
    Returns (file_path_from_patch_header, ok).
    """
    if not PATCHES_DIR.exists():
        return "", "", False

    proj_candidates = [
        PATCHES_DIR / project,
        PATCHES_DIR / sanitize_name(project),
    ]
    proj_dir = next((p for p in proj_candidates if p.exists() and p.is_dir()), None)
    if proj_dir is None:
        return "", "", False

    patch_path = proj_dir / revision_hash / f"{hunk_oid}.patch"
    if not patch_path.exists():
        return "", "", False

    try:
        txt = patch_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "", "", False

    file_path_patch = ""
    for ln in txt.splitlines()[:120]:
        m = RE_PATCH_FILE_PATH.match(ln)
        if m:
            file_path_patch = canonicalize_file_path_keep_trailing_slash(m.group(1))
            break
    return file_path_patch, True


# ===================== STAGE 1: LVL1 COMMIT IDS (Mongo truth) =====================

def compute_commit_totals_and_lvl1_commit_ids(db) -> Tuple[Dict[str, int], List[Any]]:
    """
    Commit-level truth from ALL hunks:
      - n_hunks per commit_id
      - n_files per commit_id (unique file_id from file_action)

    lvl1 = n_hunks == 1 and n_files == 1
    """
    col = db[HUNK_COL]

    pipeline = [
        {"$match": {"file_action_id": {"$exists": True, "$ne": None}}},
        {"$project": {"file_action_id": 1}},
        {"$lookup": {"from": "file_action", "localField": "file_action_id", "foreignField": "_id", "as": "fa"}},
        {"$unwind": "$fa"},
        {"$match": {"fa.commit_id": {"$ne": None}, "fa.file_id": {"$ne": None}}},
        {"$group": {
            "_id": "$fa.commit_id",
            "n_hunks": {"$sum": 1},
            "files": {"$addToSet": "$fa.file_id"},
        }},
        {"$project": {
            "commit_id": "$_id",
            "_id": 0,
            "n_hunks": 1,
            "n_files": {"$size": "$files"},
        }},
    ]

    totals = {
        "mongo_commits_total": 0,
        "mongo_single_file_commits": 0,
        "mongo_single_hunk_commits": 0,
        "mongo_single_file_and_single_hunk_commits": 0,
    }
    lvl1_commit_ids: List[Any] = []

    t0 = time.time()
    for i, doc in enumerate(col.aggregate(pipeline, allowDiskUse=True), start=1):
        if PRINT_EVERY_STAGE1 and i % PRINT_EVERY_STAGE1 == 0:
            print(f"[STAGE1] commits_processed={i:,} elapsed={(time.time()-t0):.1f}s", flush=True)

        totals["mongo_commits_total"] += 1
        nf = int(doc.get("n_files", 0))
        nh = int(doc.get("n_hunks", 0))

        if nf == 1:
            totals["mongo_single_file_commits"] += 1
        if nh == 1:
            totals["mongo_single_hunk_commits"] += 1
        if nf == 1 and nh == 1:
            totals["mongo_single_file_and_single_hunk_commits"] += 1
            lvl1_commit_ids.append(doc["commit_id"])

    return totals, lvl1_commit_ids


# ===================== STAGE 2: LABELED HUNKS FOR LVL1 (efficient) =====================

def fetch_labeled_hunks_for_lvl1_commit_batch(db, commit_ids: List[Any]) -> List[Dict[str, Any]]:
    """
    Efficient pattern:
      file_action (commit_id in batch) -> lookup hunk by file_action_id -> match lines_manual
      then join commit/vcs/project + file for file_path
    """
    fa = db["file_action"]

    pipeline = [
        {"$match": {"commit_id": {"$in": commit_ids}, "file_id": {"$ne": None}}},
        {"$project": {"commit_id": 1, "file_id": 1}},
        {"$lookup": {"from": HUNK_COL, "localField": "_id", "foreignField": "file_action_id", "as": "h"}},
        {"$unwind": "$h"},
        {"$match": {"h.lines_manual": {"$type": "object"}}},

        {"$lookup": {"from": "commit", "localField": "commit_id", "foreignField": "_id", "as": "c"}},
        {"$unwind": "$c"},
        {"$lookup": {"from": "vcs_system", "localField": "c.vcs_system_id", "foreignField": "_id", "as": "vs"}},
        {"$unwind": {"path": "$vs", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "project", "localField": "vs.project_id", "foreignField": "_id", "as": "p"}},
        {"$unwind": {"path": "$p", "preserveNullAndEmptyArrays": True}},

        {"$lookup": {"from": "file", "localField": "file_id", "foreignField": "_id", "as": "f"}},
        {"$unwind": {"path": "$f", "preserveNullAndEmptyArrays": True}},

        {"$project": {
            "_id": "$h._id",
            "lines_manual": "$h.lines_manual",
            "content": {"$ifNull": ["$h.content", ""]},
            "old_start": "$h.old_start",
            "old_lines": "$h.old_lines",
            "new_start": "$h.new_start",
            "new_lines": "$h.new_lines",

            "revision_hash": {"$ifNull": ["$c.revision_hash", ""]},
            "project": {"$ifNull": ["$p.name", ""]},

            "file_path": {
                "$cond": [
                    {"$and": [{"$ne": ["$f.name", None]}, {"$ne": ["$f.name", ""]}]},
                    {"$concat": [
                        {"$cond": [{"$or": [{"$eq": ["$f.path", None]}, {"$eq": ["$f.path", ""]}]}, "", "$f.path"]},
                        {"$cond": [{"$or": [{"$eq": ["$f.path", None]}, {"$eq": ["$f.path", ""]}]}, "", "/"]},
                        "$f.name"
                    ]},
                    {"$concat": ["FILE_ID:", {"$toString": "$file_id"}]}
                ]
            }
        }},
        {"$match": {"project": {"$ne": ""}, "revision_hash": {"$ne": ""}}},
    ]

    return list(fa.aggregate(pipeline, allowDiskUse=True))


def build_context_code_from_mongo(doc: Dict[str, Any]) -> str:
    """Prefer hunk.content; fallback to minimal @@ header if content missing."""
    content = doc.get("content") or ""
    if isinstance(content, str) and content.strip():
        return content.rstrip() + "\n"

    os_ = doc.get("old_start", "?")
    ol_ = doc.get("old_lines", "?")
    ns_ = doc.get("new_start", "?")
    nl_ = doc.get("new_lines", "?")
    return f"@@ -{os_},{ol_} +{ns_},{nl_} @@\n"


# ===================== MAIN =====================

def main() -> None:
    t_start = time.time()

    print("[START] connecting MongoDB...", flush=True)
    client = mongo_client()
    client.admin.command("ping")
    db = client[MONGO_DB]
    print(f"[MONGO] connected. using collection: {HUNK_COL}", flush=True)

    # Stage 1
    print("[STAGE1] computing commit-level totals + lvl1 commit list (Mongo truth)...", flush=True)
    totals, lvl1_commit_ids = compute_commit_totals_and_lvl1_commit_ids(db)
    print(f"[STAGE1] done. lvl1_commits_total={len(lvl1_commit_ids):,}", flush=True)

    # Stage 2
    print("[STAGE2] fetching LABELED hunks for lvl1 commits (batched)...", flush=True)
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    parquet_rows: List[Dict[str, Any]] = []

    t0 = time.time()
    n_batches = (len(lvl1_commit_ids) + BATCH - 1) // BATCH
    rows_out = 0

    patch_ok = 0
    patch_miss = 0
    file_path_filled_from_patch = 0

    for bi in range(n_batches):
        chunk = lvl1_commit_ids[bi * BATCH:(bi + 1) * BATCH]
        docs = fetch_labeled_hunks_for_lvl1_commit_batch(db, chunk)

        for doc in docs:
            project = (doc.get("project") or "").strip()
            rev = (doc.get("revision_hash") or "").strip()

            # file_path: Mongo first, otherwise patch header
            mongo_fp_raw = (doc.get("file_path") or "").strip()
            mongo_fp = canonicalize_file_path_keep_trailing_slash(mongo_fp_raw) if mongo_fp_raw else ""

            hunk_oid = str(doc.get("_id"))

            lines_manual = doc.get("lines_manual") if isinstance(doc.get("lines_manual"), dict) else {}

            # consensus
            votes = compute_line_votes(lines_manual)
            line_cons = compute_line_consensus(votes, threshold=3)
            hunk_cons = compute_hunk_consensus_from_line_consensus(line_cons)

            # contexts
            context_code_mongo = build_context_code_from_mongo(doc)

            fp_patch, ok = read_patch_for_hunk(project, rev, hunk_oid)
            if ok:
                patch_ok += 1
            else:
                patch_miss += 1

            final_fp = mongo_fp
            if is_missing_or_fileid(mongo_fp_raw) or not mongo_fp:
                if fp_patch:
                    final_fp = fp_patch
                    file_path_filled_from_patch += 1

            # JSON row: include ONLY labelers as keys
            row = {
                "project": project,
                "commit_hash": rev,
                "num_files_per_commit": 1,
                "num_hunks_per_commit": 1,
                "file_path": final_fp,
                "hunk_oid": hunk_oid,
                "context_code": context_code_mongo,
                "line_consensus": json.dumps(line_cons, ensure_ascii=False, sort_keys=True),
                "hunk_consensus": hunk_cons,
            }

            # Add ONLY the people who labeled
            for person, person_labels in lines_manual.items():
                if not isinstance(person_labels, dict):
                    continue
                normalized = {}
                for lab, idxs in person_labels.items():
                    if isinstance(idxs, list):
                        normalized[normalize_label(str(lab))] = idxs
                row[str(person)] = json.dumps(normalized, ensure_ascii=False, sort_keys=True)

            grouped[project].append(row)
            rows_out += 1

            # Parquet: keep participants in one JSON column
            parquet_rows.append({
                "project": project,
                "commit_hash": rev,
                "num_files_per_commit": 1,
                "num_hunks_per_commit": 1,
                "file_path": final_fp,
                "hunk_oid": hunk_oid,
                "context_code": context_code_mongo,
                "line_consensus": json.dumps(line_cons, ensure_ascii=False, sort_keys=True),
                "hunk_consensus": hunk_cons,
                "labelers": json.dumps(sorted(list(lines_manual.keys())), ensure_ascii=False),
                "participants": json.dumps(lines_manual, ensure_ascii=False, sort_keys=True),
            })

        if PRINT_EVERY_STAGE2:
            print(
                f"[STAGE2] batch={bi+1}/{n_batches} docs_in_batch={len(docs):,} "
                f"rows_out={rows_out:,} patch_ok={patch_ok:,} patch_miss={patch_miss:,} "
                f"elapsed={(time.time()-t0):.1f}s",
                flush=True
            )

    # TOTAL block
    grouped["_TOTAL"] = {
        "commits_total": totals["mongo_commits_total"],
        "single_file_commits": totals["mongo_single_file_commits"],
        "single_hunk_commits": totals["mongo_single_hunk_commits"],
        "single_file_and_single_hunk_commits": totals["mongo_single_file_and_single_hunk_commits"],
        "lvl1_commits_total": len(lvl1_commit_ids),
        "lvl1_labeled_rows_output": rows_out,
        "collection_used": HUNK_COL,
        "patch_join_ok": int(patch_ok),
        "patch_join_miss": int(patch_miss),
        "file_path_filled_from_patch": int(file_path_filled_from_patch),
        "note": (
            "Lvl1 computed from ALL hunks (Mongo truth). Rows output only for LABELED hunks (lines_manual). "
            "file_path prefers Mongo; if missing/FILE_ID then patch header file_path is used. "
            "context_code from hunk.content; context_code_patch joined by hunk_oid -> <hunk_oid>.patch."
        )
    }

    # Save grouped JSON
    print(f"[SAVE] grouped JSON -> {OUT_GROUPED_JSON}", flush=True)
    OUT_GROUPED_JSON.write_text(json.dumps(grouped, ensure_ascii=False, indent=2), encoding="utf-8")

    # Save JSONL
    print(f"[SAVE] JSONL ({rows_out:,} rows) -> {OUT_JSONL}", flush=True)
    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for proj, rows in grouped.items():
            if proj == "_TOTAL":
                continue
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Save Parquet
    print(f"[SAVE] Parquet ({len(parquet_rows):,} rows) -> {OUT_PARQUET}", flush=True)
    df = pd.DataFrame(parquet_rows).fillna("")
    df.to_parquet(OUT_PARQUET, index=False)

    print(
        f"[DONE] lvl1_commits={len(lvl1_commit_ids):,} | labeled_rows={rows_out:,} | "
        f"time={(time.time()-t_start):.1f}s",
        flush=True
    )


if __name__ == "__main__":
    main()
