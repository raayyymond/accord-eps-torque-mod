---
name: feedback-evaluate-clip-rules-on-the-observed-envelope
description: State the ENVELOPE before quoting a clip fraction. A no-clip rule scored on a rectangular grid assumes a worst corner (849 deg/s) the car never visits; route 5d's max was 330 deg/s. Three analysts reached different conclusions from identical arithmetic purely by policing different envelopes.
metadata:
  type: feedback
---

# 🛑 Evaluate a no-clip rule on the OBSERVED envelope — and say which envelope you used

**Three analysts reached three different conclusions from identical arithmetic in one session, purely
because each policed a different envelope.** That is not a disagreement about the firmware; it is an
unstated premise.

## The concrete case
The damper's no-clip rule is `(FactorC(speed) × FactorE(rate)) >> 10 ≤ ceiling_floor = 512`.

- **On a rectangular (speed × rate) grid**, the worst corner is `FactorE X[3] = 4000` counts =
  **849 deg/s** of column rate. Almost any dose increase fails there.
- **On route 5d's observed envelope**, `|column rate|` **max was 330 deg/s** (p99 188.7, p99.9 274.0),
  and **zero frames** exceeded 2000 counts. The grid's worst corner is a place the car does not go.

Same inequality, opposite verdicts.

## How to apply
1. **Name the envelope in the same sentence as the clip fraction.** *"3 % of the grid clips"* and *"0 of
   101,118 frames clip"* are both true and mean different things. A number without an envelope is not a
   result.
2. **Quote the measured quantiles, not just the max** — p99 and p99.9 are what a rule should be sized
   against; the max is one frame and may be a sensor artefact.
3. **Keep the grid rule as the SAFETY floor, the envelope as the DESIGN target.** A lever that passes
   both is unambiguous — which is why `FactorE X[1]` is the preferred dose lever: it raises the operating
   point while leaving the surface maximum untouched, so it passes the grid rule *by construction*
   ([[reference-accord-factore-x1-is-the-free-dose-lever]]).
4. **A structural argument beats both.** "The peak is unchanged" needs no envelope at all.
5. ⚠ **The envelope is route-specific.** Route 5d had 9 engagement episodes and only 78 s of engaged
   creep; it is not a licence to assume 330 deg/s is the car's lifetime maximum. Widen deliberately, and
   say by how much.

## Why this recurs
The rectangular grid is the *easy* thing to compute — you already have the table — so it becomes the
default without anyone choosing it. The observed envelope needs a drive. When the two disagree the grid
always looks more conservative, which makes it feel like the safe answer, and the cost is invisible:
**levers get refused that the car would never have exercised.**

Related: [[reference-accord-factore-x1-is-the-free-dose-lever]] ·
[[feedback-size-probe-rungs-against-lane-reachable-output]] ·
[[feedback-cave-two-gates-ram-ownership-and-closed-loop]] · [[accord-v74-flew-damper-is-in-force]]
