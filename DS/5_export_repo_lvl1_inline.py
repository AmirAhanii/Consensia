# -*- coding: utf-8 -*-
"""
LVL1 "ANNOTATED FULL FILE" EXPORT (robust; never skips writing)

Fixes vs previous script:
- Computes total_rows UPFRONT (progress is stable).
- NEVER skips writing an output file.
- If repo/parent/before/diff is missing, it still writes the .txt and explains why.
- Best-effort annotation:
    * If BEFORE + DIFF hunk available: annotate BEFORE file by applying hunk (desired behavior).
    * If BEFORE missing but AFTER available and DIFF available: output AFTER file, prefix '+' for added lines when possible.
    * If DIFF missing: output AFTER if available else BEFORE else placeholder.
    * If repo missing: placeholder only.

Output:
  ROOT/lvl1_patches_1/<project>/<commit>/<hunk_oid>.txt
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List


# ====================== CONFIG ======================

ROOT = Path(r"C:\Users\ahmad\Desktop\Bilkent\5th year\1st sem\SDP - CS491\dataset_of_tangled_commits\Project's commits")
INPUT_GROUPED_JSON = ROOT / "out" / "lvl1_labeled_only_labelers_grouped.json"
OUTPUT_ROOT = ROOT / "lvl1_patches_1"

REPO_ROOTS = [
    ROOT / "_repos",
    ROOT / "_repo_cache",
]

GIT_UNIFIED = 3
GIT_SHOW_TIMEOUT = 60
PRINT_EVERY = 100

# ====================================================


def sanitize_name(name: str) -> str:
    bad_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for ch in bad_chars:
        name = name.replace(ch, "_")
    return name.replace(" ", "_")


def canonicalize_file_path(p: str) -> str:
    """Your JSON uses trailing '/', remove it so git show works."""
    p = (p or "").strip()
    while p.startswith("/"):
        p = p[1:]
    while p.endswith("/"):
        p = p[:-1]
    return p


def run_git(args: List[str], cwd: Path, timeout: int) -> Tuple[int, str, str]:
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


def find_local_repo(project_name: str) -> Optional[Path]:
    candidates = []
    for rr in REPO_ROOTS:
        candidates.append(rr / project_name)
        candidates.append(rr / sanitize_name(project_name))

    for c in candidates:
        if c.exists() and (c / ".git").exists():
            return c
    return None


def git_get_parents(repo_path: Path, revision: str) -> List[str]:
    rc, out, _ = run_git(["git", "show", "-s", "--format=%P", revision], cwd=repo_path, timeout=GIT_SHOW_TIMEOUT)
    if rc != 0:
        return []
    return [p for p in out.strip().split() if p.strip()]


def git_show_file_lines(repo_path: Path, revision: str, file_path: str) -> Optional[List[str]]:
    """
    git show <rev>:<path>
    Returns list of lines (no trailing '\n').
    """
    spec = f"{revision}:{file_path}"
    rc, out, _ = run_git(["git", "show", "--no-color", spec], cwd=repo_path, timeout=GIT_SHOW_TIMEOUT)
    if rc != 0:
        return None
    return out.splitlines()


def git_show_diff_for_file(repo_path: Path, revision: str, file_path: str) -> Optional[str]:
    cmd = [
        "git", "show",
        "--no-color",
        "--pretty=format:",
        f"--unified={GIT_UNIFIED}",
        revision,
        "--",
        file_path
    ]
    rc, out, _ = run_git(cmd, cwd=repo_path, timeout=GIT_SHOW_TIMEOUT)
    if rc != 0 or not out.strip():
        return None
    return out


def extract_first_hunk_lines(diff_text: str) -> Optional[List[str]]:
    """
    Extract first hunk from git unified diff (for a single file).
    """
    lines = (diff_text or "").splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith("@@ "):
            start = i
            break
    if start is None:
        return None

    out = [lines[start]]
    for j in range(start + 1, len(lines)):
        ln = lines[j]
        if ln.startswith("@@ "):
            break
        if ln.startswith((" ", "+", "-", "\\")):
            out.append(ln)
        else:
            out.append(ln)
    return out


def build_annotated_from_before(before_lines: List[str], hunk_lines: List[str]) -> List[str]:
    """
    Desired behavior:
    - unchanged => as-is
    - deleted   => "- " + text
    - added     => "+ " + text
    Applies hunk sequentially anchored by first context line.
    """
    if not hunk_lines or not hunk_lines[0].startswith("@@ "):
        return list(before_lines)

    body = [ln for ln in hunk_lines[1:] if not ln.startswith("\\ No newline")]
    context = [ln[1:] for ln in body if ln.startswith(" ")]

    anchor_idx = 0
    if context:
        first_ctx = context[0]
        found = None
        for i, bl in enumerate(before_lines):
            if bl == first_ctx:
                found = i
                break
        anchor_idx = found if found is not None else 0

    out: List[str] = []
    out.extend(before_lines[:anchor_idx])

    cur = anchor_idx
    for ln in body:
        if not ln:
            continue
        prefix = ln[0]
        text = ln[1:] if len(ln) > 1 else ""

        if prefix == " ":
            out.append(text)
            cur += 1
        elif prefix == "-":
            out.append("- " + text)
            cur += 1
        elif prefix == "+":
            out.append("+ " + text)
        else:
            out.append(ln)

    if cur < len(before_lines):
        out.extend(before_lines[cur:])

    return out


def build_annotated_from_after(after_lines: List[str], hunk_lines: Optional[List[str]]) -> List[str]:
    """
    Fallback when BEFORE is missing but AFTER exists.
    We still want to show '+ ' lines when we can.

    Strategy:
    - If we have hunk_lines: collect added lines from the hunk ('+').
      When printing AFTER file, if a line equals one of the added lines, prefix '+ '.
      Otherwise print as-is.
    - If no hunk_lines: print AFTER as-is.
    """
    if not hunk_lines or not hunk_lines[0].startswith("@@ "):
        return list(after_lines)

    body = [ln for ln in hunk_lines[1:] if not ln.startswith("\\ No newline")]
    added = [ln[1:] for ln in body if ln.startswith("+") and not ln.startswith("+++")]
    added_set = set(added)

    out: List[str] = []
    for ln in after_lines:
        if ln in added_set:
            out.append("+ " + ln)
        else:
            out.append(ln)
    return out


def main() -> None:
    if not INPUT_GROUPED_JSON.exists():
        raise FileNotFoundError(f"Input JSON not found: {INPUT_GROUPED_JSON}")

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    grouped = json.loads(INPUT_GROUPED_JSON.read_text(encoding="utf-8", errors="replace"))

    # ---------- stable total upfront ----------
    total_rows = 0
    for proj, rows in grouped.items():
        if proj == "_TOTAL":
            continue
        if isinstance(rows, list):
            total_rows += len(rows)

    exported = 0

    # stats
    missing_repo = 0
    missing_parent = 0
    missing_before = 0
    missing_after = 0
    missing_diff = 0

    for proj, rows in grouped.items():
        if proj == "_TOTAL":
            continue
        if not isinstance(rows, list):
            continue

        repo_path = find_local_repo(proj)

        for row in rows:
            project = (row.get("project") or proj).strip()
            revision = (row.get("commit_hash") or "").strip()
            hunk_oid = (row.get("hunk_oid") or "").strip()
            file_path_raw = (row.get("file_path") or "").strip()

            safe_project = sanitize_name(project)
            commit_dir = OUTPUT_ROOT / safe_project / (revision or "UNKNOWN_COMMIT")
            commit_dir.mkdir(parents=True, exist_ok=True)
            out_path = commit_dir / f"{(hunk_oid or 'UNKNOWN_HUNK')}.txt"

            file_path = canonicalize_file_path(file_path_raw)

            notes: List[str] = []
            annotated_lines: List[str] = []

            if repo_path is None:
                missing_repo += 1
                notes.append("Repo not found locally under _repos/_repo_cache. Cannot run git show.")
                annotated_lines = ["(no content available: missing local repo)"]
            else:
                if not revision:
                    notes.append("Missing commit_hash in JSON row; cannot run git.")
                    annotated_lines = ["(no content available: missing commit hash)"]
                elif not file_path:
                    notes.append("Missing file_path in JSON row; cannot run git show <rev>:<path>.")
                    annotated_lines = ["(no content available: missing file_path)"]
                else:
                    parents = git_get_parents(repo_path, revision)
                    parent = parents[0] if parents else ""
                    if not parent:
                        missing_parent += 1
                        notes.append("Could not determine parent commit (git show -s --format=%P failed or empty).")

                    before_lines = git_show_file_lines(repo_path, parent, file_path) if parent else None
                    if before_lines is None:
                        if parent:
                            missing_before += 1
                            notes.append("BEFORE file not available at parent (file may be added/renamed, or parent missing locally).")

                    after_lines = git_show_file_lines(repo_path, revision, file_path)
                    if after_lines is None:
                        missing_after += 1
                        notes.append("AFTER file not available at commit (file may be deleted/renamed, or commit missing locally).")

                    diff_text = git_show_diff_for_file(repo_path, revision, file_path)
                    if diff_text is None:
                        missing_diff += 1
                        notes.append("Unified diff not available (git show -- <file> returned empty or failed).")

                    hunk_lines = extract_first_hunk_lines(diff_text) if diff_text else None
                    if diff_text and not hunk_lines:
                        missing_diff += 1
                        notes.append("Could not extract a hunk from diff output (no @@ found).")

                    # Choose best-effort build:
                    if before_lines is not None and hunk_lines is not None:
                        annotated_lines = build_annotated_from_before(before_lines, hunk_lines)
                    elif after_lines is not None:
                        # fallback: print after, and mark added lines if we can
                        annotated_lines = build_annotated_from_after(after_lines, hunk_lines)
                    elif before_lines is not None:
                        annotated_lines = list(before_lines)
                    else:
                        annotated_lines = ["(no content available: git show failed for both parent and commit)"]

            # Write output
            out_lines: List[str] = []
            out_lines.append(f"Project: {project}")
            out_lines.append(f"Commit: {revision or '(missing)'}")
            out_lines.append(f"hunk_oid: {hunk_oid or '(missing)'}")
            out_lines.append(f"file_path: {file_path or '(missing)'}")
            if repo_path is not None:
                out_lines.append(f"repo_path: {repo_path}")
            out_lines.append("")

            out_lines.append("===== NOTES =====")
            if notes:
                for n in notes:
                    out_lines.append(f"- {n}")
            else:
                out_lines.append("(none)")
            out_lines.append("")

            out_lines.append("===== ANNOTATED FULL FILE =====")
            out_lines.append("Legend: deleted lines prefixed with '- ' ; added lines prefixed with '+ ' ; unchanged lines have no prefix.")
            out_lines.append("")
            out_lines.extend(annotated_lines)
            out_lines.append("")

            out_path.write_text("\n".join(out_lines), encoding="utf-8", errors="replace")

            exported += 1
            if PRINT_EVERY and exported % PRINT_EVERY == 0:
                print(f"[PROGRESS] exported={exported:,}/{total_rows:,}", flush=True)

    print("\n[DONE]")
    print(f"Input rows (lvl1)     : {total_rows:,}")
    print(f"Exported files        : {exported:,}")
    print(f"Missing repo rows     : {missing_repo:,}")
    print(f"Missing parent rows   : {missing_parent:,}")
    print(f"Missing BEFORE file   : {missing_before:,}")
    print(f"Missing AFTER file    : {missing_after:,}")
    print(f"Missing diff/hunk     : {missing_diff:,}")
    print(f"Output root           : {OUTPUT_ROOT}")


if __name__ == "__main__":
    main()