---
name: accord-v96-flew-as-7e-7f-and-the-record-said-v94
description: V96 flew as routes 7e/7f (both fault-free, identity proven single-frame) while STATE.md and BUILD-LINEAGE.md both said V94 was on the car — the seventh instance of the stale-flash-status defect, and the first that demonstrably cost work. Also: V96's regressor was 34x over-range, so S1 AND S2 are void.
metadata:
  type: reference
---

**V96 IS ON THE CAR.** Routes **`7e`** (806 s, 76.4 % engaged) and **`7f`** (838 s, 82.4 % engaged),
2026-08-12, **both fault-free** — DTC-active duty 0.000000, zero sentinels, `OUTPUT_DISABLED` duty
0.0001, `STEER_STATUS` clean.

**IDENTITY, PROVEN SINGLE-FRAME [EVIDENCE]:** `0x14A` byte7 bit 6 = **1 on 100.0000 % of 164,096
frames** across both routes. V94 carries the 74-byte V90 cave and **cannot write byte 7 at all**.
`byte7[7:6] ∈ {1,3}` on every frame (the map validator); byte4 b3 constant (the `gp-0x674e < 28` rung,
true on every frame — the first direct on-car read of that byte, settling RULE 7 for the authority curve).
⊕ **Separation from V92 is now EVIDENCE, not BELIEF**: V92's byte7 b6 is the dwell-snap rung, measured
**0.0000 engaged AND manual over 87,317 frames**; V96's is a hard-wired constant 1, and a
164,096-frame unbroken rail is a reading V92's rung has never produced one frame of.

## 🛑🛑 THE RECORD SAID V94 FOR A FULL SESSION AFTER V96 FLEW — AND IT COST WORK
`STATE.md` lines 6–9 read **"ON THE CAR: V94 … It is still flashed"** and `BUILD-LINEAGE.md` Part 4
agreed. **Seventh instance** of the "row says UNFLASHED after it flew" defect — and the first where
the cost is documented: it sent the session's strongest analyst to close its final verdict with
*"fly V96, S2 answers it, no flash needed."* **V96 had already flown**, so that recommendation was
void, and an hour of the session's best analysis was spent reasoning toward a measurement that did not
exist.

⇒ **MECHANICAL CLOSE-OUT GATE — run it every time, it fails loudly:**
```
grep -n "ON THE CAR\|UNFLASHED\|never flashed" docs/STATE.md docs/BUILD-LINEAGE.md
```
reconciled against the identity bit from the most recent route. The previous rule (*"write the flight
result in the same pass that scores the flight"*) depends on someone remembering to touch two other
files, and has now been violated twice since it was written. **A rule that only fires if someone
remembers is not a control.**

⇒ **And a rule for agents:** an agent's first act in a firmware session should be to **verify the
on-car build from a FLIGHT ARTEFACT, not from the record.**

## 🛑 V96'S INSTRUMENT FAILED — S1 AND S2 ARE BOTH VOID
`gp-0x374c`'s magnitude code **M is pinned at 0** on 99.904 % (7e) / 99.965 % (7f) of frames, and
**100 %** of route 7f's engaged elicitation time ⇒ `|gp-0x374c>>4| < 2048` essentially always, against
a field sized off a structural bound of ~68,600 — a **34× over-range**. The entire signal sits inside
**one LSB of a 2048-LSB field**; saturation duty 0.00 % (the guard fired the wrong way).
**S1 and S2 regress the SAME pair, so both are void. `f′` was NOT resolved by this flight** — it was
later closed analytically instead ([[accord-ram-lerp-is-flash-derived-and-fprime-is-nonneg]]).
⇒ **Next regressor LSB: 128–256, not 2048.** Size probes off MEASURED distributions, never structural
bounds. The primary channel was healthy — `gp-0x6b70` p50 ~154 ct, max ~3520 against ±8192, **zero
clipping** — which is what later made `|Q|` measurable without another flight.

Links: [[accord-v97-is-a-loop-pole-and-the-direction-is-measured]] ·
[[accord-recut-overwrites-the-previous-plain-image]] · [[accord-v64-null-is-on-the-gate]]
