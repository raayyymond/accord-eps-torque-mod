---
name: feedback-check-build-scripts-before-proposing-cal-edit
description: Before recommending any calibration address as a "new" lever, grep analysis-2020accord/build_v*_tva.py for that address — it may already be flashed and falsified.
metadata:
  type: feedback
---

Never propose a calibration-only test address without first grepping `analysis-2020accord/build_v*_tva.py`
for it. On 2026-07-26 I recommended `0xC6450` (tp+0x7450, `FUN_0003a382` Stage A pole) `1024→32` as a
"never flashed" cal-only test — team-lead corrected me: it is `build_v46_tva.py` verbatim (same address,
same values, same predicted effect, `_v46_plain_image.bin` confirms `0xC6450=32`), **flashed and
falsified** ("V46 FLASHED... vibration UNCHANGED... LEVER A FALSIFIED", already recorded in CLAUDE.md).
This was the **second time** an agent in this kit independently re-proposed `0xC6450` as a "new" lever —
CLAUDE.md already carried a standing warning about the first occurrence, and I still hit it, because I
was reasoning purely from structural/decompile evidence (single reader, no lockstep, clean gain math)
without checking whether the edit had already been tried. The sibling constant `0xC644A` is the same trap
(V43, also flashed, also null).

**Why:** structural cleanliness (single reader, no lockstep pair, safe cal-block location) proves an edit
is SAFE to flash, not that it's NEW or UNTESTED. Those are separate questions, and only the build-script
record answers the second one. A confident, well-evidenced recommendation that turns out to be a rerun of
a known-null experiment wastes a flash cycle and erodes trust in the analysis, even though the underlying
trace was itself correct.

**How to apply:** before writing any sentence recommending a cal address as a test candidate — anywhere,
in any report — run `grep -rniE "0xADDR" analysis-2020accord/build_v*_tva.py` (or the tp-relative
equivalent) for that exact address AND its known aliases (tp-offset form, absolute form). If a build
script already touches it, read that script's docstring for what it changed it to and what the on-car
result was (check CLAUDE.md's "Current builds" section too) before saying anything else about it. This
check takes one Bash call and should happen before, not after, a recommendation goes out. See
[[reference_accord_fun3a382_engagement_gated_residual_loop]] for the specific incident and the corrected
finding it led to (authority-gated output bound in the same function, a genuinely untested lever).
