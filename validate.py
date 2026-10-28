#!/usr/bin/env python3
"""Board front-matter validator — enforces RULES.md / TEMPLATES.md.

Checks per artifact type: required fields present, status in allowed set, id
prefix matches folder, and back-references (source_*) point to files that exist.
Zero deps (minimal YAML front-matter parse). Both the artifact server and agents
(KiroCrew/agy) call this before committing a board file.

Usage:
    python3 validate.py <path-to-file>        # validate one file, exit 0/1
    python3 validate.py --all                 # validate the whole board
    from validate import validate_text, validate_file
"""
import json
import re
import sys
from pathlib import Path

BOARD = Path(__file__).resolve().parent
STAGES = {
    "stories":  {"prefix": "US",   "type": "story",   "status": ["draft","ready","in-backlog","done"],
                 "req": ["id","type","title","status","author","created"], "refs": []},
    "backlog":  {"prefix": "BL",   "type": "backlog", "status": ["todo","refined","in-progress","review","done"],
                 "req": ["id","type","title","status","source_story","author","created"],
                 "refs": [("source_story","stories","US")]},
    "prd":      {"prefix": "PRD",  "type": "prd",     "status": ["draft","in-review","approved"],
                 "req": ["id","type","title","status","owner","author","created"], "refs": []},
    "specs":    {"prefix": "SPEC", "type": "spec",    "status": ["draft","approved","implemented"],
                 "req": ["id","type","spec_kind","title","status","author","created"],
                 "refs": [("source_prd","prd","PRD")]},
    "tasks":    {"prefix": "TASK", "type": "task",    "status": ["todo","in-progress","blocked","review","done"],
                 "req": ["id","type","title","status","assignee","description","created"],
                 "refs": [("source_spec","specs","SPEC"),("source_backlog","backlog","BL")], "json": True},
    "reports":  {"prefix": "RPT",  "type": "report",  "status": ["done","partial","failed"],
                 "req": ["id","type","title","status","source_task","author","created"],
                 "refs": [("source_task","tasks","TASK")]},
}
ASSIGNEES = {"kirocrew", "agy", "unassigned", "achmad"}

def parse_frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.S)
    if not m:
        return None
    out = {}
    for line in m.group(1).splitlines():
        line = line.split("#", 1)[0].rstrip()
        if not line.strip() or ":" not in line:
            continue
        k, v = line.split(":", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out

def _ref_exists(stage, prefix, value):
    if not value:
        return True
    ext = ".json" if stage == "tasks" else ".md"
    # stage folders now live under product-backlog/<stage> or sprints/<sprint>/<stage>;
    # a referenced ID may live in any sprint, the product backlog, or archive -> search board-wide.
    for f in BOARD.rglob(f"{value}*{ext}"):
        # Exact match on stem (filename without extension), not prefix
        if f.stem == value and f.parent.name == stage:
            return True
    return False

def validate_text(stage, text, filename=""):
    spec = STAGES.get(stage)
    if not spec:
        return False, [f"folder tidak dikenal: {stage}"]
    errs = []
    if spec.get("json"):
        try:
            meta = json.loads(text)
        except Exception as e:
            return False, [f"JSON tidak valid: {e}"]
    else:
        meta = parse_frontmatter(text)
        if meta is None:
            return False, ["front-matter YAML (--- ... ---) tidak ditemukan"]
    for f in spec["req"]:
        if not meta.get(f):
            errs.append(f"field wajib hilang/kosong: {f}")
    if meta.get("type") and meta["type"] != spec["type"]:
        errs.append(f"type harus '{spec['type']}', bukan '{meta.get('type')}'")
    rid = str(meta.get("id", ""))
    if rid and not re.match(rf"^{spec['prefix']}-\d{{3,}}$", rid):
        errs.append(f"id harus '{spec['prefix']}-NNN' (3+ digit), dapat '{rid}'")
    if meta.get("status") and meta["status"] not in spec["status"]:
        errs.append(f"status '{meta['status']}' tidak sah; sah: {', '.join(spec['status'])}")
    if meta.get("assignee") and meta["assignee"] not in ASSIGNEES:
        errs.append(f"assignee '{meta['assignee']}' tidak sah; sah: {', '.join(sorted(ASSIGNEES))}")
    if stage == "specs" and meta.get("spec_kind") not in ("tech", "api"):
        errs.append("spec_kind harus 'tech' atau 'api'")
    if stage == "specs" and meta.get("spec_kind") == "api" \
       and "api design" not in text.lower() and "desain api" not in text.lower():
        errs.append("spec_kind=api wajib punya bagian 'Desain API (API Design)'")
    if stage == "reports" and meta.get("status") == "done":
        low = text.lower()
        if "acceptance check" not in low and "cek penerimaan" not in low:
            errs.append("report 'done' wajib punya bagian 'Cek Penerimaan (Acceptance Check)'")
    for field, refstage, refprefix in spec["refs"]:
        val = meta.get(field)
        if val and not _ref_exists(refstage, refprefix, val):
            errs.append(f"{field}={val} merujuk file yang TIDAK ADA di {refstage}/")
    # Optional field validation: notes, carried_from, report (only if present, no required check)
    if meta.get("report") and not re.match(r"^RPT-\d{3,}$", str(meta["report"])):
        errs.append(f"report format salah: '{meta['report']}' (harus RPT-NNN)")
    if meta.get("carried_from") and not re.match(r"^sprint-\d{2}$", str(meta["carried_from"])):
        errs.append(f"carried_from format salah: '{meta['carried_from']}' (harus sprint-NN)")
    return (len(errs) == 0), errs

def validate_file(path):
    path = Path(path)
    stage = path.parent.name
    text = path.read_text(encoding="utf-8", errors="replace")
    return validate_text(stage, text, path.name)

def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--all":
        bad = 0
        for f in sorted(BOARD.rglob("*")):
            if not f.is_file():
                continue
            # skip embedded git worktrees / build dirs (e.g. agy's *-wt, .git) —
            # these are not board data and must not be validated.
            parts = f.relative_to(BOARD).parts
            if any(p == ".git" or p.endswith("-wt") for p in parts):
                continue
            stage = f.parent.name
            if stage not in STAGES:
                continue
            if (stage == "tasks") != (f.suffix == ".json"):
                continue
            ok, errs = validate_file(f)
            rel = f.relative_to(BOARD)
            if not ok:
                bad += 1; print(f"✗ {rel}")
                for e in errs: print(f"    - {e}")
            else:
                print(f"✓ {rel}")
        print(f"\n{'ALL VALID' if bad==0 else str(bad)+' file tidak valid'}")
        sys.exit(0 if bad == 0 else 1)
    if len(sys.argv) != 2:
        print("usage: validate.py <file> | --all"); sys.exit(2)
    ok, errs = validate_file(sys.argv[1])
    if ok:
        print("✓ VALID"); sys.exit(0)
    print("✗ TIDAK VALID:")
    for e in errs: print(f"  - {e}")
    sys.exit(1)

if __name__ == "__main__":
    main()
