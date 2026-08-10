#!/usr/bin/env python3
"""shrink_state_md.py -- split docs/STATE.md into a CURRENT file and a verbatim ARCHIVE.

STATE.md had grown to 506 KB / 6,114 lines across 53 level-2 sections -- past the 256 KB Read
limit, so no agent could read it in one call and the tail was silently invisible. Most of the
bulk is superseded: old headlines about flights that BUILD-LINEAGE.md and the HANDOFF-*.md chain
already record per build.

This script is the reproducible record of what moved where. It NEVER deletes: every archived
section is written verbatim to docs/STATE-ARCHIVE-pre-V89.md with its original line numbers.

Run from the repo root.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "docs" / "STATE.md"
ARCHIVE = ROOT / "docs" / "STATE-ARCHIVE-pre-V89.md"

# Sections kept in the live STATE.md, matched on a distinctive prefix of the heading.
# Everything else is archived verbatim.
KEEP_PREFIXES = [
    "## ★★★★★ HEADLINE, 2026-08-09 latest — V88 FLEW",
    "## 🛑 STANDING INSTRUMENT CORRECTIONS",
    "## 🛑 METHODOLOGY",
    "## Signal-identity corrections of record",
    "## ✅ The tyre line",
    "## Still-standing results worth not re-deriving",
]


def split(text: str):
    lines = text.split("\n")
    heads = [(i, l) for i, l in enumerate(lines) if l.startswith("## ")]
    preamble = lines[:heads[0][0]] if heads else lines
    out = []
    for k, (i, l) in enumerate(heads):
        j = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        out.append({"line": i + 1, "head": l, "body": lines[i:j]})
    return preamble, out


def main():
    src = STATE.read_text(encoding="utf-8")
    before = len(src.encode("utf-8"))
    preamble, secs = split(src)

    keep, arch = [], []
    for s in secs:
        if any(s["head"].startswith(p) for p in KEEP_PREFIXES):
            keep.append(s)
        else:
            arch.append(s)

    kb = lambda n: f"{n/1024:.1f} KB"
    print(f"STATE.md in : {before} B ({kb(before)}), {len(secs)} sections")
    print(f"  keep    : {len(keep)}")
    for s in keep:
        print(f"      L{s['line']:5d}  {s['head'][:88]}")
    print(f"  archive : {len(arch)} sections -> {ARCHIVE.name}")

    arch_txt = [
        "# STATE ARCHIVE — superseded sections, split out of `docs/STATE.md` on 2026-08-09",
        "",
        "🛑 **This file is a RECORD, not an instruction.** Every section below was live in",
        "`docs/STATE.md` and was superseded by a later flight or a later correction. It is kept",
        "verbatim so no result is lost, and so a claim can be traced to the form it was made in.",
        "",
        "**Do not reason from this file.** The authorities are, in order:",
        "`docs/STATE.md` (current state) · `docs/BUILD-LINEAGE.md` (per-lever, per-build, on-car",
        "results) · the latest `docs/HANDOFF-*.md` · `memory/`.",
        "",
        f"Split by `analysis-2020accord/shrink_state_md.py`. Source was {before} B / "
        f"{src.count(chr(10))} lines / {len(secs)} sections.",
        "",
        "---",
        "",
        "## Contents",
        "",
    ]
    for s in arch:
        arch_txt.append(f"- (orig. line {s['line']}) {s['head'][3:][:120]}")
    arch_txt += ["", "---", ""]
    for s in arch:
        arch_txt.append(f"<!-- original STATE.md line {s['line']} -->")
        arch_txt += s["body"]
        arch_txt.append("")

    ARCHIVE.write_text("\n".join(arch_txt), encoding="utf-8")
    a = len(ARCHIVE.read_bytes())
    print(f"  archive written: {a} B ({kb(a)})")

    new = list(preamble)
    for s in keep:
        new += s["body"]
    new_txt = "\n".join(new)
    STATE.write_text(new_txt, encoding="utf-8")
    after = len(STATE.read_bytes())
    print(f"STATE.md out: {after} B ({kb(after)})  "
          f"[{'OK' if after < 256*1024 else 'STILL TOO BIG'} vs the 256 KB Read limit]")
    print(f"  nothing lost: {before} in -> {after} + {a} archived")


if __name__ == "__main__":
    main()
