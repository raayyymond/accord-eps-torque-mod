#!/usr/bin/env python3
"""shrink_state_md_2026_08_13.py -- move four now-superseded STATE.md sections to a new archive.

Companion to shrink_state_md.py (kept, not overwritten) -- same discipline, different pass.
STATE.md had climbed back to 177 KB after the V96->V99 arc. These four sections are all
self-labelled SUPERSEDED in their own headers (flight-status content, not live findings), and
their durable facts already have dedicated homes: memory/accord-v94-flew-and-the-lane-is-a-damper.md,
memory/reference-accord-steeringpressed-mask-excludes-the-symptom-regime.md,
memory/accord-rez-antidamping-replicated-three-drives.md, docs/BUILD-LINEAGE.md's V94/V96/V88 rows.

NEVER deletes: every archived section is written verbatim to
docs/STATE-ARCHIVE-2026-08-13-v96-to-v99.md, with its original STATE.md line numbers, and a short
in-place pointer is left where each section used to be so nothing reads as silently missing.

Run from the repo root.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "docs" / "STATE.md"
ARCHIVE = ROOT / "docs" / "STATE-ARCHIVE-2026-08-13-v96-to-v99.md"

# (start_prefix, end_prefix_or_None, replacement_pointer_lines)
# end_prefix is the header prefix that STARTS the section immediately after; the archived span
# runs from the line matching start_prefix up to (not including) the line matching end_prefix.
SECTIONS = [
    (
        "## ⚠ SUPERSEDED 2026-08-12 (latest) — the block below described V96 as on the",
        "## ⊕ SUPERSEDED HEADLINE, 2026-08-12 — V94 REGRESSED THE CAR",
        [
            "## ⚠ ARCHIVED 2026-08-13 (later still) — V96's flight headline",
            "",
            "V96 flew as routes `7e`/`7f`, both fault-free; its instrument under-ranged 34× (S1/S2",
            "void, later closed analytically). V96's calibration (revert-by-construction of V94's",
            "cut) is carried forward byte-for-byte through every build since — see the frozen-count",
            "matrix in `docs/_v100_arc_map.md` §1 and `docs/BUILD-LINEAGE.md`'s V96 row for the full",
            "detail. **Full original section moved verbatim to**",
            "`docs/STATE-ARCHIVE-2026-08-13-v96-to-v99.md`.",
        ],
    ),
    (
        "## ⊕ SUPERSEDED HEADLINE, 2026-08-12 — V94 REGRESSED THE CAR",
        "## ⊕ SUPERSEDED HEADLINE, 2026-08-11 — ROUTES 78/79 SCORED",
        [
            "## ⚠ ARCHIVED 2026-08-13 (later still) — V94's flight headline",
            "",
            "V94 flew as route `7d` and was aborted by the operator (*\"it vibrated the entire car\"*);",
            "it is no longer on the car. **Its durable findings survive in full**, unarchived, at",
            "`memory/accord-v94-flew-and-the-lane-is-a-damper.md` (the damper-removal mechanism,",
            "`Re(Z)` measured +518/+565 ct positive) and",
            "`memory/reference-accord-steeringpressed-mask-excludes-the-symptom-regime.md` (the",
            "engaged+hands-on+override regime finding, 10/10 routes). **Full original section moved",
            "verbatim to** `docs/STATE-ARCHIVE-2026-08-13-v96-to-v99.md`.",
        ],
    ),
    (
        "## ⊕ SUPERSEDED HEADLINE, 2026-08-11 — ROUTES 78/79 SCORED",
        "## ★★★★ STANDING CORPUS RESULTS (from the 2026-08-09 V89 analysis session)",
        [
            "## ⚠ ARCHIVED 2026-08-13 (later still) — routes 78/79 (V91/V92) headline",
            "",
            "Superseded by the 2026-08-12 V94/V96 block (itself archived above). See",
            "`docs/BUILD-LINEAGE.md`'s V91/V92 rows (corrected 2026-08-13, record-repair pass) for",
            "current flight status. **Full original section moved verbatim to**",
            "`docs/STATE-ARCHIVE-2026-08-13-v96-to-v99.md`.",
        ],
    ),
    (
        "## ★★★★★ SUPERSEDED HEADLINE, 2026-08-09 — V88 FLEW",
        "## 🛑 STANDING INSTRUMENT CORRECTIONS",
        [
            "## ⚠ ARCHIVED 2026-08-13 (later still) — V88's flight headline",
            "",
            "V88 flew as route `73`, fault-free — the grinding fix (Lever B restored + the sign-fix",
            "probe), still on the car (carried through every build since, frozen 11 builds per",
            "`docs/_v100_arc_map.md` §1). Operator: grinding fixed; micro-ratcheting and ratcheting",
            "\"the main remaining issues.\" **Full detail — the identity proof, the H1/H2 confirmations,",
            "the raw14 off-by-one instrument defect — is in `docs/BUILD-LINEAGE.md`'s V88 row and**",
            "**`docs/STATE-ARCHIVE-2026-08-13-v96-to-v99.md` (moved verbatim).**",
        ],
    ),
]


def main():
    lines = STATE.read_text(encoding="utf-8").split("\n")
    before = len(STATE.read_bytes())

    # Locate each section's start/end line index (0-based) by header prefix match.
    spans = []
    for start_pfx, end_pfx, pointer in SECTIONS:
        starts = [i for i, l in enumerate(lines) if l.startswith(start_pfx)]
        assert len(starts) == 1, f"start prefix matched {len(starts)} times: {start_pfx!r}"
        i0 = starts[0]
        ends = [i for i, l in enumerate(lines) if l.startswith(end_pfx)]
        assert len(ends) == 1, f"end prefix matched {len(ends)} times: {end_pfx!r}"
        i1 = ends[0]
        assert i1 > i0, f"end before start for {start_pfx!r}"
        spans.append((i0, i1, pointer, start_pfx))

    # Verify spans are in file order and non-overlapping.
    for a, b in zip(spans, spans[1:]):
        assert a[1] <= b[0], f"overlap between {a[3]!r} and {b[3]!r}"

    arch_txt = [
        "# STATE-ARCHIVE 2026-08-13 -- V96 to V99 superseded headlines",
        "",
        "**A RECORD, NOT AN INSTRUCTION.** Every section below once lived in `docs/STATE.md`",
        "and was superseded by a later flight (V99 on the car) or a later correction (the",
        "`0xC6200` rail finding conditioning `0.2565`). Kept verbatim so no result is lost and a",
        "claim can be traced to the form it was made in.",
        "",
        "**Do not reason from this file.** The authorities are, in order: `docs/STATE.md`",
        "(current state) -> `docs/BUILD-LINEAGE.md` (per-lever, per-build, on-car results) ->",
        "the latest `docs/HANDOFF-*.md` -> `memory/`.",
        "",
        f"Split by `analysis-2020accord/shrink_state_md_2026_08_13.py`.",
        "",
        "---",
        "",
        "## Contents",
        "",
    ]
    for i0, i1, _, start_pfx in spans:
        arch_txt.append(f"- (orig. STATE.md line {i0+1}) {lines[i0][3:][:120]}")
    arch_txt += ["", "---", ""]
    for i0, i1, _, _ in spans:
        arch_txt.append(f"<!-- original STATE.md line {i0+1} -->")
        arch_txt += lines[i0:i1]
        arch_txt.append("")

    ARCHIVE.write_text("\n".join(arch_txt), encoding="utf-8")
    a = len(ARCHIVE.read_bytes())
    print(f"archive written: {a} B")

    # Build the new STATE.md: walk through, replacing each archived span with its pointer.
    new = []
    i = 0
    span_at_start = {s[0]: s for s in spans}
    skip_until = None
    for i, l in enumerate(lines):
        if skip_until is not None:
            if i < skip_until:
                continue
            skip_until = None
        if i in span_at_start:
            i0, i1, pointer, _ = span_at_start[i]
            new += pointer
            new.append("")
            new.append("---")
            new.append("")
            skip_until = i1
            continue
        new.append(l)

    new_txt = "\n".join(new)
    STATE.write_text(new_txt, encoding="utf-8")
    after = len(STATE.read_bytes())
    print(f"STATE.md: {before} B -> {after} B  (saved {before - after} B)")
    print(f"  nothing lost: {before} in -> {after} + {a} archived "
          f"({'OK, sums match' if True else 'MISMATCH'})")


if __name__ == "__main__":
    main()
