---
name: accord-filter-placement-decides-authority-not-the-filter
description: In the LKAS rate loop, the SAME filter on the loop OUTPUT vs on the FEEDBACK OPERAND has an algebraically identical return ratio (poles, zeta, Ms, phase margin, gate73 all identical to machine precision) but only the forward placement costs transient authority (pkR); a search space that fixes the placement is not a search of the loop. 2026-09-09.
metadata:
  type: reference
---

# A filter's PLACEMENT decides authority, not the filter — 2026-09-09

**EVIDENCE.** `design290b_candidates.py` builds every sum-filter inside `Elec.bracket()`, and `bracket()`
feeds **both** `R()` (the return ratio) **and** `fwd()` (the reference transfer) — but `poles_of`/`Sfun`/
`crossover`/`unst`/`gate73` all read only `Lpoly = R × plant`. **Only `step_lin` (`pkR`, `pkA`, `t90`)
reads `fwd()`.** So the identical filter, placed on the PID sum `S` (forward/command path) vs on the
feedback operand `r26` (return path, multiplying `F` instead of `Hlag`), yields poles/ζ/Ms/PM/GM/`gate73`
**identical to machine precision** — max |pole difference| = 0.000e+00 on 121 linear-stable fits;
`gate73` fwd = fb = 1.009167 exactly. The filter only "costs" transient authority (`pkR`) when it sits in
the forward/command path, because `pkR` measures how much 15–25 Hz command energy the filter removes on
a step — that is a *topology* statement, not a *damping* statement.

Measured consequence, notch 21.5 Hz Q1.5 + fb pole 40 Hz, forward vs feedback placement, same 121-fit
family: ζ_worst identical **+0.021** either way, `gate73` identical **1.009**, but `pkR_worst/pkR_med`
= **0.66/0.80** (forward) vs **0.93/0.97** (feedback), `t90` 18 ms vs 13 ms. **Even V289 as built
(notch 20.04 Hz Q3 + fb 25 Hz) would have cost `pkR` 0.98 instead of 0.79 in the feedback placement, at
IDENTICAL ζ** — the 0.91 transient-authority price the operator accepted for V289 was a price for the
*forward-path topology*, not for the damping it bought.

Search-space consequence: in the same grid with the same fits and scoring, **30 of 384 combos are
feasible in the feedback placement vs 0 of 384 forward** (a follow-up adversarial pass found 41/735
feasible in a wider feedback-placement grid). A search that only tries the forward path is not exploring
the loop's actual design space — it is exploring one topology's cost.

**Caveats, both real:** (1) `pkR` is not vacuous — it is right that a forward-path filter also scrubs the
D-kick's 20 Hz content out of the *command*, which a feedback-path filter does not; that's a genuine,
separate argument, not a blocker. (2) the feedback placement gives the command path its 20 Hz content
back (the notch no longer attenuates openpilot's own echo on the way to the motor) — bounded, not
eliminated, by V288 rev 2 (a reference-side filter that halved the command's 20 Hz content and left the
grinding unchanged).

Sources: `docs/review/ADV-V290-NULL-2026-09-09.md`, `docs/review/V290-DECISION-TABLE-2026-09-09.md`,
`rlog-tools/studies/grind/reconcile_v290.py`.

**How to apply:** whenever a design tables a linear in-loop filter, score BOTH the forward and feedback
placements before ranking on `pkR`/authority alone — a search that fixes the placement is not a search of
the loop. See [[accord-design-must-state-which-placement-it-built]] for the process failure this caused
in V289, and [[accord-v289r1-flew-the-ring-moved-to-16hz-revert-signature]] for what actually flew.
