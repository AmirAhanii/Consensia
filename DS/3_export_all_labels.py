# -*- coding: utf-8 -*-
"""
EXPORT ALL LABELED HUNKS (Mongo) + commit-level distributions + optional PATCH fallback.

UPDATED:
- Exports ALL labeled hunks (lines_manual exists) across all commits (any #files/#hunks).
- Row fields include true commit totals when available (Mongo truth from ALL hunks):
    num_files_per_commit, num_hunks_per_commit
  If commit totals cannot be computed (rare join issues), they are set to -1 and counted.
- Removes is_lvl1 entirely (not written).
- file_path is SINGLE field:
    prefer Mongo file_path; if missing/FILE_ID then fallback to patch header file_path
    (trailing slashes removed)
- ONLY labelers are written as keys (no 64 empty participants).
- _TOTAL includes:
    commits_total
    labeled_hunks_total
    labeled_rows_output
    collection_used
    distributions:
      {n}_file_commits
      {n}_file_{m}_hunk_commits
    patch stats + join-missing stats

Outputs:
- out/all_labeled_only_labelers_grouped.json
- out/all_labeled_only_labelers.jsonl
- out/all_labeled_only_labelers.parquet
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

PATCHES_DIR = ROOT / "projects_patches"   # NEW hunk layout: <project>/<revision>/<hunk>.patch
USE_PATCH_JOIN = True                    # set False for Mongo-only

OUT_DIR = ROOT / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_GROUPED_JSON = OUT_DIR / "all_labeled_only_labelers_grouped.json"
OUT_JSONL        = OUT_DIR / "all_labeled_only_labelers.jsonl"
OUT_PARQUET      = OUT_DIR / "all_labeled_only_labelers.parquet"

HUNK_COL = "hunk"

PRINT_EVERY_STAGE1 = 20000
PRINT_EVERY_STAGE2 = 2000

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

def canonicalize_file_path(p: str) -> str:
    p = (p or "").strip()
    while p.startswith("/"):
        p = p[1:]
    while p.endswith("/"):
        p = p[:-1]
    return p

def is_missing_or_fileid(p: str) -> bool:
    p = (p or "").strip()
    return (not p) or p.startswith("FILE_ID:")

def normalize_text_for_json(s: Any) -> str:
    """Normalize CRLF/CR and remove LS/PS to keep JSONL + VSCode happy."""
    if not isinstance(s, str):
        return ""
    return (
        s.replace("\r\n", "\n")
         .replace("\r", "\n")
         .replace("\u2028", "\n")  # LS
         .replace("\u2029", "\n")  # PS
    )

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


# ===================== PATCH FALLBACK (file_path only) =====================

def read_patch_file_path(project: str, revision_hash: str, hunk_oid: str) -> Tuple[str, bool]:
    """Returns (file_path_patch, ok). Only reads patch header (fast)."""
    if not PATCHES_DIR.exists():
        return "", False

    if not project or not revision_hash:
        return "", False

    proj_candidates = [
        PATCHES_DIR / project,
        PATCHES_DIR / sanitize_name(project),
    ]
    proj_dir = next((p for p in proj_candidates if p.exists() and p.is_dir()), None)
    if proj_dir is None:
        return "", False

    patch_path = proj_dir / revision_hash / f"{hunk_oid}.patch"
    if not patch_path.exists():
        return "", False

    try:
        txt = patch_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "", False

    for ln in txt.splitlines()[:120]:
        m = RE_PATCH_FILE_PATH.match(ln)
        if m:
            return canonicalize_file_path(m.group(1)), True

    return "", True  # patch exists but no header match


# ===================== STAGE1: COMMIT COUNTS + DISTRIBUTIONS (ALL HUNKS) =====================

def build_commit_counts_and_distributions(db) -> Tuple[
    Dict[Any, Tuple[int, int]],
    int,
    Counter,
    Counter,
    Counter,
    int
]:
    """
    Returns:
      commit_counts: commit_id -> (n_files, n_hunks)
      commits_total
      files_dist: nf -> count
      hunks_dist: nh -> count
      joint_dist: (nf, nh) -> count
      violations_hunks_lt_files: count of commits where nh < nf
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

    commits_total = 0
    commit_counts: Dict[Any, Tuple[int, int]] = {}
    files_dist = Counter()
    hunks_dist = Counter()
    joint_dist = Counter()
    violations_hunks_lt_files = 0

    t0 = time.time()
    for i, doc in enumerate(col.aggregate(pipeline, allowDiskUse=True), start=1):
        if PRINT_EVERY_STAGE1 and i % PRINT_EVERY_STAGE1 == 0:
            print(f"[STAGE1] commits_processed={i:,} elapsed={(time.time()-t0):.1f}s", flush=True)

        cid = doc["commit_id"]
        nf = int(doc.get("n_files", 0))
        nh = int(doc.get("n_hunks", 0))

        commits_total += 1
        commit_counts[cid] = (nf, nh)

        files_dist[nf] += 1
        hunks_dist[nh] += 1
        joint_dist[(nf, nh)] += 1

        if nh < nf:
            violations_hunks_lt_files += 1

    return commit_counts, commits_total, files_dist, hunks_dist, joint_dist, violations_hunks_lt_files


def flatten_distributions(files_dist: Counter, joint_dist: Counter) -> Dict[str, int]:
    """
    Produces keys like:
      1_file_commits
      4024_file_commits
      42_file_292_hunk_commits
    """
    out: Dict[str, int] = {}

    for nf in sorted(files_dist.keys()):
        out[f"{nf}_file_commits"] = int(files_dist[nf])

    by_nf: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
    for (nf, nh), cnt in joint_dist.items():
        by_nf[nf].append((nh, int(cnt)))

    for nf in sorted(by_nf.keys()):
        for nh, cnt in sorted(by_nf[nf], key=lambda x: x[0]):
            out[f"{nf}_file_{nh}_hunk_commits"] = int(cnt)

    return out


# ===================== STAGE2: STREAM ALL LABELED HUNKS =====================

def build_labeled_hunks_cursor(db):
    """
    preserveNullAndEmptyArrays=True so we don't DROP labeled hunks if a join is missing.
    We'll output placeholders and count them.
    """
    hunk = db[HUNK_COL]
    pipeline = [
        {"$match": {
            "file_action_id": {"$exists": True, "$ne": None},
            "lines_manual": {"$type": "object"},
        }},
        {"$project": {
            "lines_manual": 1, "file_action_id": 1, "content": 1,
            "old_start": 1, "old_lines": 1, "new_start": 1, "new_lines": 1
        }},
        {"$lookup": {"from": "file_action", "localField": "file_action_id", "foreignField": "_id", "as": "fa"}},
        {"$unwind": {"path": "$fa", "preserveNullAndEmptyArrays": True}},

        {"$lookup": {"from": "commit", "localField": "fa.commit_id", "foreignField": "_id", "as": "c"}},
        {"$unwind": {"path": "$c", "preserveNullAndEmptyArrays": True}},

        {"$lookup": {"from": "vcs_system", "localField": "c.vcs_system_id", "foreignField": "_id", "as": "vs"}},
        {"$unwind": {"path": "$vs", "preserveNullAndEmptyArrays": True}},

        {"$lookup": {"from": "project", "localField": "vs.project_id", "foreignField": "_id", "as": "p"}},
        {"$unwind": {"path": "$p", "preserveNullAndEmptyArrays": True}},

        {"$lookup": {"from": "file", "localField": "fa.file_id", "foreignField": "_id", "as": "f"}},
        {"$unwind": {"path": "$f", "preserveNullAndEmptyArrays": True}},

        {"$project": {
            "_id": 1,
            "lines_manual": 1,
            "content": {"$ifNull": ["$content", ""]},
            "old_start": 1, "old_lines": 1, "new_start": 1, "new_lines": 1,

            "commit_id": {"$ifNull": ["$fa.commit_id", None]},
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
                    {"$cond": [
                        {"$ne": ["$fa.file_id", None]},
                        {"$concat": ["FILE_ID:", {"$toString": "$fa.file_id"}]},
                        ""
                    ]}
                ]
            }
        }},
    ]
    return hunk.aggregate(pipeline, allowDiskUse=True)

def build_context_code_from_mongo(doc: Dict[str, Any]) -> str:
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

    labeled_hunks_total = db[HUNK_COL].count_documents({
        "lines_manual": {"$type": "object"},
        "file_action_id": {"$exists": True, "$ne": None}
    })
    print(f"[INFO] labeled_hunks_total={labeled_hunks_total:,}", flush=True)

    print("[STAGE1] building commit-level counts + distributions (ALL hunks)...", flush=True)
    (
        commit_counts,
        commits_total,
        files_dist,
        hunks_dist,
        joint_dist,
        violations_hunks_lt_files
    ) = build_commit_counts_and_distributions(db)
    print(f"[STAGE1] done. commits_total={commits_total:,} | violations_hunks_lt_files={violations_hunks_lt_files:,}", flush=True)

    dist_flat = flatten_distributions(files_dist, joint_dist)

    print("[STAGE2] streaming ALL labeled hunks + joins...", flush=True)
    cursor = build_labeled_hunks_cursor(db)

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    parquet_rows: List[Dict[str, Any]] = []

    processed = 0
    rows_written = 0

    # join-quality counters
    missing_commit_totals = 0
    missing_project = 0
    missing_revision_hash = 0
    missing_file_action = 0

    patch_ok = 0
    patch_miss = 0
    file_path_filled_from_patch = 0

    with OUT_JSONL.open("w", encoding="utf-8") as jsonl:
        t0 = time.time()
        for doc in cursor:
            processed += 1

            project = normalize_text_for_json((doc.get("project") or "").strip())
            revision_hash = normalize_text_for_json((doc.get("revision_hash") or "").strip())

            if not project:
                project = "UNKNOWN_PROJECT"
                missing_project += 1

            if not revision_hash:
                missing_revision_hash += 1

            commit_id = doc.get("commit_id")
            if commit_id is None:
                missing_file_action += 1

            # commit totals (nf/nh)
            nf = nh = -1
            if commit_id is not None and commit_id in commit_counts:
                nf, nh = commit_counts[commit_id]
            else:
                missing_commit_totals += 1

            lines_manual = doc.get("lines_manual") if isinstance(doc.get("lines_manual"), dict) else {}
            if not lines_manual:
                continue

            # consensus
            votes = compute_line_votes(lines_manual)
            line_cons = compute_line_consensus(votes, threshold=3)
            hunk_cons = compute_hunk_consensus_from_line_consensus(line_cons)

            # context
            context_code = normalize_text_for_json(build_context_code_from_mongo(doc))

            # file_path (single field)
            mongo_fp = canonicalize_file_path(normalize_text_for_json(doc.get("file_path") or ""))
            final_fp = mongo_fp

            hunk_oid = str(doc.get("_id"))

            # patch fallback only if mongo file_path missing/FILE_ID
            if USE_PATCH_JOIN and is_missing_or_fileid(final_fp) and project != "UNKNOWN_PROJECT" and revision_hash:
                fp_patch, ok = read_patch_file_path(project, revision_hash, hunk_oid)
                if ok:
                    patch_ok += 1
                    if fp_patch:
                        fp_patch = canonicalize_file_path(fp_patch)
                        if fp_patch and fp_patch != final_fp:
                            final_fp = fp_patch
                            file_path_filled_from_patch += 1
                else:
                    patch_miss += 1

            # if revision_hash missing, fall back to commit_id for traceability
            commit_hash_out = revision_hash if revision_hash else (f"COMMIT_ID:{commit_id}" if commit_id is not None else "")

            row = {
                "project": project,
                "commit_hash": commit_hash_out,
                "num_files_per_commit": int(nf),
                "num_hunks_per_commit": int(nh),
                "file_path": final_fp,
                "hunk_oid": hunk_oid,
                "context_code": context_code,
                "line_consensus": json.dumps(line_cons, ensure_ascii=False, sort_keys=True),
                "hunk_consensus": hunk_cons,
            }

            # ONLY labelers as keys
            for person, person_labels in lines_manual.items():
                if not isinstance(person_labels, dict):
                    continue
                normalized = {}
                for lab, idxs in person_labels.items():
                    if isinstance(idxs, list):
                        normalized[normalize_label(str(lab))] = idxs
                row[str(person)] = json.dumps(normalized, ensure_ascii=False, sort_keys=True)

            grouped[project].append(row)
            jsonl.write(json.dumps(row, ensure_ascii=False) + "\n")

            parquet_rows.append({
                "project": project,
                "commit_hash": commit_hash_out,
                "num_files_per_commit": int(nf),
                "num_hunks_per_commit": int(nh),
                "file_path": final_fp,
                "hunk_oid": hunk_oid,
                "context_code": context_code,
                "line_consensus": json.dumps(line_cons, ensure_ascii=False, sort_keys=True),
                "hunk_consensus": hunk_cons,
                "labelers": json.dumps(sorted(list(lines_manual.keys())), ensure_ascii=False),
                "participants": json.dumps(lines_manual, ensure_ascii=False, sort_keys=True),
            })

            rows_written += 1

            if PRINT_EVERY_STAGE2 and processed % PRINT_EVERY_STAGE2 == 0:
                pct = (processed / labeled_hunks_total * 100.0) if labeled_hunks_total else 0.0
                print(
                    f"[STAGE2] processed={processed:,}/{labeled_hunks_total:,} ({pct:.1f}%) "
                    f"rows_written={rows_written:,} "
                    f"patch_attempts={(patch_ok+patch_miss):,} ok={patch_ok:,} miss={patch_miss:,} "
                    f"elapsed={(time.time()-t0):.1f}s",
                    flush=True
                )

    print(f"[SAVE] jsonl ({rows_written:,} rows) -> {OUT_JSONL}", flush=True)

    # _TOTAL (no 'mongo_' prefix, no lvl1/single-file stuff)
    total_block: Dict[str, Any] = {
        "commits_total": int(commits_total),
        "labeled_hunks_total": int(labeled_hunks_total),
        "labeled_rows_output": int(rows_written),
        "collection_used": HUNK_COL,

        "violations_hunks_lt_files_commits": int(violations_hunks_lt_files),

        "patch_join_enabled": bool(USE_PATCH_JOIN),
        "patch_join_attempts": int(patch_ok + patch_miss),
        "patch_join_ok": int(patch_ok),
        "patch_join_miss": int(patch_miss),
        "file_path_filled_from_patch": int(file_path_filled_from_patch),

        # join-quality visibility
        "missing_commit_totals_rows": int(missing_commit_totals),
        "missing_project_rows": int(missing_project),
        "missing_revision_hash_rows": int(missing_revision_hash),
        "missing_file_action_rows": int(missing_file_action),

        "note": (
            "All labeled hunks = hunk docs where lines_manual exists (and file_action_id exists for the count). "
            "Commit distributions are computed from ALL hunks (Mongo truth). "
            "Rows output include ONLY labelers as keys. "
            "file_path prefers Mongo; if missing/FILE_ID then patch header file_path is used. "
            "Text normalized to remove LS/PS separators for JSONL safety."
        ),
    }

    # add distributions (keys like 4024_file_commits, 42_file_292_hunk_commits)
    total_block.update(dist_flat)
    grouped["_TOTAL"] = total_block

    if rows_written != labeled_hunks_total:
        print(
            f"[WARN] labeled_hunks_total={labeled_hunks_total:,} but labeled_rows_output={rows_written:,}. "
            f"See missing_* counters in _TOTAL.",
            flush=True
        )

    print(f"[SAVE] grouped JSON -> {OUT_GROUPED_JSON}", flush=True)
    OUT_GROUPED_JSON.write_text(json.dumps(grouped, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[SAVE] parquet ({len(parquet_rows):,} rows) -> {OUT_PARQUET}", flush=True)
    df = pd.DataFrame(parquet_rows).fillna("")
    df.to_parquet(OUT_PARQUET, index=False)

    print(
        f"[DONE] labeled_hunks_total={labeled_hunks_total:,} | rows_output={rows_written:,} | "
        f"time={(time.time()-t_start):.1f}s",
        flush=True
    )


if __name__ == "__main__":
    main()
