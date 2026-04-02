# -*- coding: utf-8 -*-
"""
LVL1 LABELED builder (Mongo truth for lvl1) + PATCH join by hunk_oid
+ full_context from lvl1_patches_1/<project>/<commit_hash>/<hunk_oid>.txt

full_context rules:
- If annotated file exists: full_context = everything AFTER the Legend line.
- If annotated content is missing (repo missing, etc.):
  full_context = "<all NOTES bullet lines> <first meaningful line after Legend>"

IMPORTANT CHANGE REQUEST (this version):
- Replace _TOTAL block with an "export-style" summary at the end that matches:
  Input rows (lvl1)
  Exported files
  Missing repo rows
  Missing parent rows
  Missing BEFORE file
  Missing AFTER file
  Missing diff/hunk
  lvl1_labeled_rows_output
  collection_used
  patch_join_ok
  patch_join_miss
  file_path_filled_from_patch
  full_context_ok
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

PATCHES_DIR = ROOT / "projects_patches"
LVL1_PATCHES_1_DIR = ROOT / "lvl1_patches_1"

OUT_DIR = ROOT / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_GROUPED_JSON = OUT_DIR / "lvl1_labeled_patches_1_grouped.json"
OUT_JSONL        = OUT_DIR / "lvl1_labeled_patches_1.jsonl"
OUT_PARQUET      = OUT_DIR / "lvl1_labeled_patches_1.parquet"
OUT_CSV          = OUT_DIR / "lvl1_labeled_patches_1.csv"
OUT_XLSX         = OUT_DIR / "lvl1_labeled_patches_1.xlsx"

HUNK_COL = "hunk"

PRINT_EVERY_STAGE1 = 20000
PRINT_EVERY_STAGE2 = 2000
BATCH = 5000

MONGO_DB   = "smartshark_1_2"
MONGO_HOST = "localhost"
MONGO_PORT = 27017
MONGO_USER = None
MONGO_PASS = None
MONGO_AUTH_DB = None

EXCEL_CELL_MAX = 32000

# ===================== HELPERS =====================

RE_PATCH_FILE_PATH = re.compile(r"^\s*file_path:\s*(.+?)\s*$", re.IGNORECASE)

LEGEND_PREFIX = "Legend: deleted lines prefixed with '- ' ; added lines prefixed with '+ ' ; unchanged lines have no prefix."
NOTES_HEADER = "===== NOTES ====="

def sanitize_name(name: str) -> str:
    bad_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for ch in bad_chars:
        name = name.replace(ch, "_")
    return name.replace(" ", "_")

def canonicalize_file_path_keep_trailing_slash(p: str) -> str:
    p = (p or "").strip()
    while p.startswith("/"):
        p = p[1:]
    while p.endswith("/"):
        p = p[:-1]
    return (p + "/") if p else ""

def is_missing_or_fileid(p: str) -> bool:
    p = (p or "").strip()
    return (not p) or p.startswith("FILE_ID:")

def normalize_text_for_json(s: Any) -> str:
    if not isinstance(s, str):
        return ""
    return (
        s.replace("\r\n", "\n")
         .replace("\r", "\n")
         .replace("\u2028", "\n")
         .replace("\u2029", "\n")
    )

def truncate_for_excel(s: str, limit: int = EXCEL_CELL_MAX) -> str:
    if not isinstance(s, str):
        return ""
    if len(s) <= limit:
        return s
    return s[:limit] + "\n...<TRUNCATED_FOR_EXCEL>..."

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

# ===================== PATCH JOIN (file_path only) =====================

def read_patch_for_hunk(project: str, revision_hash: str, hunk_oid: str) -> Tuple[str, bool]:
    if not PATCHES_DIR.exists():
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

    file_path_patch = ""
    for ln in txt.splitlines()[:160]:
        m = RE_PATCH_FILE_PATH.match(ln)
        if m:
            file_path_patch = canonicalize_file_path_keep_trailing_slash(m.group(1))
            break

    return file_path_patch, True

# ===================== FULL_CONTEXT PARSER + MISSING COUNTERS =====================

def _extract_notes_and_body_from_lvl1_txt(txt: str) -> Tuple[List[str], List[str]]:
    lines = normalize_text_for_json(txt).splitlines()

    # notes bullets
    notes_bullets: List[str] = []
    in_notes = False
    for ln in lines:
        if ln.strip() == NOTES_HEADER:
            in_notes = True
            continue
        if in_notes and ln.strip().startswith("====="):
            in_notes = False
        if in_notes:
            s = ln.strip()
            if s.startswith("- "):
                notes_bullets.append(s)

    # body after legend
    legend_idx = None
    for i, ln in enumerate(lines):
        if LEGEND_PREFIX in ln:
            legend_idx = i
            break

    body_after_legend: List[str] = []
    if legend_idx is not None:
        body_after_legend = lines[legend_idx + 1 :]
        while body_after_legend and body_after_legend[0].strip() == "":
            body_after_legend.pop(0)

    return notes_bullets, body_after_legend

def build_full_context_from_lvl1_patches_1(project: str, revision_hash: str, hunk_oid: str) -> Tuple[str, bool, Dict[str, int]]:
    """
    Returns:
      (full_context, ok, miss_flags)

    miss_flags counts per-row (0/1):
      missing_repo
      missing_parent
      missing_before
      missing_after
      missing_diff
    """
    miss_flags = {
        "missing_repo": 0,
        "missing_parent": 0,
        "missing_before": 0,
        "missing_after": 0,
        "missing_diff": 0,
    }

    if not LVL1_PATCHES_1_DIR.exists():
        return "", False, miss_flags

    safe_proj = sanitize_name(project)
    path = LVL1_PATCHES_1_DIR / safe_proj / revision_hash / f"{hunk_oid}.txt"
    if not path.exists():
        # If the file doesn't exist, we can't parse notes; treat as "missing repo-like" unknown.
        # But you said full_context_miss should be tracked separately, not as repo/parent/etc.
        return "", False, miss_flags

    try:
        txt = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return "", False, miss_flags

    # detect missing reasons from NOTES bullets
    # (these strings match what export_repo_lvl1_inline.py writes)
    normalized_txt = normalize_text_for_json(txt)
    if "Repo not found locally under _repos/_repo_cache" in normalized_txt:
        miss_flags["missing_repo"] = 1
    if "Could not determine parent commit" in normalized_txt:
        miss_flags["missing_parent"] = 1
    if "BEFORE file not available at parent" in normalized_txt:
        miss_flags["missing_before"] = 1
    if "AFTER file not available at commit" in normalized_txt:
        miss_flags["missing_after"] = 1
    if "Unified diff not available" in normalized_txt or "Could not extract a hunk from diff output" in normalized_txt:
        miss_flags["missing_diff"] = 1

    notes_bullets, body = _extract_notes_and_body_from_lvl1_txt(txt)

    if not body:
        if notes_bullets:
            return " ".join(notes_bullets).strip(), True, miss_flags
        return "", True, miss_flags

    first_line = ""
    for ln in body:
        if ln.strip():
            first_line = ln.strip()
            break

    if first_line.startswith("(no content available"):
        note_part = " ".join(notes_bullets).strip()
        if note_part:
            return f"{note_part} {first_line}".strip(), True, miss_flags
        return first_line, True, miss_flags

    out = "\n".join(body).rstrip() + "\n"
    return out, True, miss_flags

# ===================== STAGE 1: LVL1 COMMIT IDS =====================

def compute_commit_totals_and_lvl1_commit_ids(db) -> Tuple[Dict[str, int], List[Any]]:
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

# ===================== STAGE 2: LABELED HUNKS FOR LVL1 =====================

def fetch_labeled_hunks_for_lvl1_commit_batch(db, commit_ids: List[Any]) -> List[Dict[str, Any]]:
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
    content = doc.get("content") or ""
    if isinstance(content, str) and content.strip():
        return normalize_text_for_json(content.rstrip() + "\n")

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

    print("[STAGE1] computing commit-level totals + lvl1 commit list (Mongo truth)...", flush=True)
    totals, lvl1_commit_ids = compute_commit_totals_and_lvl1_commit_ids(db)
    print(f"[STAGE1] done. lvl1_commits_total={len(lvl1_commit_ids):,}", flush=True)

    print("[STAGE2] fetching LABELED hunks for lvl1 commits (batched)...", flush=True)

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    parquet_rows: List[Dict[str, Any]] = []

    n_batches = (len(lvl1_commit_ids) + BATCH - 1) // BATCH
    rows_out = 0

    patch_ok = 0
    patch_miss = 0
    file_path_filled_from_patch = 0

    fullctx_ok = 0
    fullctx_miss = 0

    # NEW: "export_repo_lvl1_inline style" missing counters (derived from NOTES)
    missing_repo_rows = 0
    missing_parent_rows = 0
    missing_before_rows = 0
    missing_after_rows = 0
    missing_diff_rows = 0

    t0 = time.time()
    with OUT_JSONL.open("w", encoding="utf-8") as jsonl:
        for bi in range(n_batches):
            chunk = lvl1_commit_ids[bi * BATCH:(bi + 1) * BATCH]
            docs = fetch_labeled_hunks_for_lvl1_commit_batch(db, chunk)

            for doc in docs:
                project = (doc.get("project") or "").strip()
                rev = (doc.get("revision_hash") or "").strip()
                hunk_oid = str(doc.get("_id"))

                lines_manual = doc.get("lines_manual") if isinstance(doc.get("lines_manual"), dict) else {}
                if not lines_manual:
                    continue

                mongo_fp_raw = (doc.get("file_path") or "").strip()
                mongo_fp = canonicalize_file_path_keep_trailing_slash(mongo_fp_raw) if mongo_fp_raw else ""

                votes = compute_line_votes(lines_manual)
                line_cons = compute_line_consensus(votes, threshold=3)
                hunk_cons = compute_hunk_consensus_from_line_consensus(line_cons)

                context_code_mongo = build_context_code_from_mongo(doc)

                fp_patch, ok_patch = read_patch_for_hunk(project, rev, hunk_oid)
                if ok_patch:
                    patch_ok += 1
                else:
                    patch_miss += 1

                final_fp = mongo_fp
                if is_missing_or_fileid(mongo_fp_raw) or not mongo_fp:
                    if fp_patch:
                        final_fp = fp_patch
                        file_path_filled_from_patch += 1

                # full_context + missing flags
                full_context, ok_full, flags = build_full_context_from_lvl1_patches_1(project, rev, hunk_oid)
                if ok_full:
                    fullctx_ok += 1
                    missing_repo_rows += flags["missing_repo"]
                    missing_parent_rows += flags["missing_parent"]
                    missing_before_rows += flags["missing_before"]
                    missing_after_rows += flags["missing_after"]
                    missing_diff_rows += flags["missing_diff"]
                else:
                    fullctx_miss += 1
                    full_context = ""

                row: Dict[str, Any] = {
                    "project": project,
                    "commit_hash": rev,
                    "num_files_per_commit": 1,
                    "num_hunks_per_commit": 1,
                    "file_path": final_fp,
                    "hunk_oid": hunk_oid,
                    "full_context": full_context,
                    "context_code": context_code_mongo,
                    "line_consensus": json.dumps(line_cons, ensure_ascii=False, sort_keys=True),
                    "hunk_consensus": hunk_cons,
                }

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
                    "commit_hash": rev,
                    "num_files_per_commit": 1,
                    "num_hunks_per_commit": 1,
                    "file_path": final_fp,
                    "hunk_oid": hunk_oid,
                    "full_context": full_context,
                    "context_code": context_code_mongo,
                    "line_consensus": json.dumps(line_cons, ensure_ascii=False, sort_keys=True),
                    "hunk_consensus": hunk_cons,
                    "labelers": json.dumps(sorted(list(lines_manual.keys())), ensure_ascii=False),
                    "participants": json.dumps(lines_manual, ensure_ascii=False, sort_keys=True),
                })

                rows_out += 1

            if PRINT_EVERY_STAGE2:
                print(
                    f"[STAGE2] batch={bi+1}/{n_batches} docs_in_batch={len(docs):,} "
                    f"rows_out={rows_out:,} patch_ok={patch_ok:,} patch_miss={patch_miss:,} "
                    f"fullctx_ok={fullctx_ok:,} fullctx_miss={fullctx_miss:,} "
                    f"elapsed={(time.time()-t0):.1f}s",
                    flush=True
                )

    # REPLACE _TOTAL with your requested export-style summary
    grouped["_TOTAL"] = {
        "Input rows (lvl1)": int(rows_out),  # matches the dataset rows we output (lvl1 labeled)
        "Exported files": int(rows_out),     # same meaning here: 1 output row per exported item

        "Missing repo rows": int(missing_repo_rows),
        "Missing parent rows": int(missing_parent_rows),
        "Missing BEFORE file": int(missing_before_rows),
        "Missing AFTER file": int(missing_after_rows),
        "Missing diff/hunk": int(missing_diff_rows),

        "lvl1_labeled_rows_output": int(rows_out),
        "collection_used": HUNK_COL,

        "patch_join_ok": int(patch_ok),
        "patch_join_miss": int(patch_miss),
        "file_path_filled_from_patch": int(file_path_filled_from_patch),

        "full_context_ok": int(fullctx_ok),
        "full_context_miss": int(fullctx_miss),
    }

    print(f"[SAVE] grouped JSON -> {OUT_GROUPED_JSON}", flush=True)
    OUT_GROUPED_JSON.write_text(json.dumps(grouped, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[SAVE] Parquet ({len(parquet_rows):,} rows) -> {OUT_PARQUET}", flush=True)
    df = pd.DataFrame(parquet_rows).fillna("")
    df.to_parquet(OUT_PARQUET, index=False)

    print(f"[SAVE] CSV ({len(df):,} rows) -> {OUT_CSV}", flush=True)
    df.to_csv(OUT_CSV, index=False, encoding="utf-8")

    print(f"[SAVE] XLSX ({len(df):,} rows) -> {OUT_XLSX}", flush=True)
    df_xlsx = df.copy()
    if "full_context" in df_xlsx.columns:
        df_xlsx["full_context"] = df_xlsx["full_context"].map(lambda s: truncate_for_excel(s, EXCEL_CELL_MAX))
    df_xlsx.to_excel(OUT_XLSX, index=False)

    print(
        f"[DONE] input_rows={rows_out:,} exported_files={rows_out:,} "
        f"missing_repo={missing_repo_rows:,} missing_parent={missing_parent_rows:,} "
        f"missing_before={missing_before_rows:,} missing_after={missing_after_rows:,} "
        f"missing_diff={missing_diff_rows:,} "
        f"time={(time.time()-t_start):.1f}s",
        flush=True
    )
    print("[OUTPUTS]")
    print(f"  {OUT_GROUPED_JSON}")
    print(f"  {OUT_JSONL}")
    print(f"  {OUT_PARQUET}")
    print(f"  {OUT_CSV}")
    print(f"  {OUT_XLSX}")


if __name__ == "__main__":
    main()