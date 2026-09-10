---
name: accord-design-must-state-which-placement-it-built
description: V289's design memo tabulated TWO filter placements (loop-output sum vs feedback operand) with identical loop metrics but different authority (0.92/0.93 vs 1.03/1.00), preferred the feedback row's authority numbers in its own pre-registration, then the build shipped the loop-output placement -- no blocker was ever recorded for the feedback row, and no one re-derived the authority number for the placement actually shipped. Caught after the fact by an adversarial pass. 2026-09-09.
metadata:
  type: feedback
---

# When a design tables two placements, the build must state which one it took, and re-derive that row's numbers

**What happened.** `docs/specs/design/DESIGN-20HZ-DAMPING-LOOPSHAPE-2026-09-08.md` §5b carried both a
`(d-out)` row (notch on the PID sum, forward path) and a `(d-fb)` row (notch on the feedback operand) on
the same axes — identical on every loop metric (ζ, min|1+L|, Ms, LF gain, 7 Hz gate), differing only in
authority: **1.03/1.00 (feedback) vs 0.92/0.93 (sum)**. The design's own §9 left the feedback hook
**explicitly open** ("chain from the fb-operand site … then the notch is on r26, the forward path stays
unfiltered — 5b's d-fb row"). V289 then **built and shipped the sum/forward placement**, but its
pre-registration (`ADV-V289-B`) was written citing the ×1.00/×1.00 authority figure — **the feedback
row's number, not the sum row's**. `ADV-V289-B` §B3, run *after* the build, caught the mismatch: the
build's actual authority (×0.890/×0.934 by the design's own method) failed the pre-registered figure.
The operator accepted the resulting authority hit as his own call, but the process gap — a design scoring
one placement and citing its number for a different, shipped placement — was never itself corrected until
a later adversarial pass named it explicitly.

**Why:** the stated reason for preferring the sum placement ("the setpoint's 20 Hz kick still reaches the
motor" in the feedback case — a real but narrow physics argument, not an engineering blocker) is a
*preference*, and preferences are exactly the kind of decision that silently drifts between the design doc
and the build script if nobody re-checks which branch the code actually took. See
[[accord-filter-placement-decides-authority-not-the-filter]] for why the two placements' loop metrics look
identical enough to make this mistake easy — everything except authority matches to machine precision, so
skimming the loop-metric columns gives no warning that the authority column came from the other row.

**How to apply:** whenever a design memo scores more than one placement/topology for the same edit,
the build script (or its adversarial pass) must explicitly state which row it took, and **re-derive that
row's authority/cost numbers against the actual built image** rather than quoting the design memo's
number for either row on trust. Do this before pre-registering anything the build will be judged against.
