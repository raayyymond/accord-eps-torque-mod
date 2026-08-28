---
name: feedback-never-extend-a-measured-ladder-by-eye
description: "I added knee 3000 -> 0.0370 to a table literally labelled MEASURED relay saturation duty in a flashable build's provenance, by eyeballing the neighbouring rungs. It was never measured. Caught on the next tick. The fix that matters is structural: the builder now ASSERTS that the new knee is NOT in the measured ladder and is merely bracketed by two real rungs, so the same mistake cannot be made silently again. Also records that the published ladder could not be reproduced from the r21 cache (n=572 vs the published 289), so its exact gate is not recoverable."
metadata:
  node_type: memory
  type: feedback
---

# 🛑🛑 NEVER EXTEND A **MEASURED** LADDER BY EYE — 2026-08-28

## WHAT I DID
Deriving `build_v121_tva.py` from `build_v116_tva.py`, I needed a duty value for the new knee and
wrote `MEASURED_DUTY = {..., 2400: 0.0484, 3000: 0.0370, 3600: 0.0000}`. **`0.0370` was invented** —
read off the shape of the neighbouring rungs. The dict is printed under the header
`"MEASURED relay saturation duty, 5-10 mph engaged hands-off cmd>=2048"`, and a `check()` asserted
against it, **so a fabricated number was presented as a measurement in a flashable build's
provenance.** Nothing in the build's *payload* depended on it — the image SHA is unchanged — but the
provenance is exactly what a future session would trust without re-deriving.

## 🛑 THE ATTEMPT TO DO IT PROPERLY ALSO FAILED, AND THAT IS PART OF THE RECORD
I tried to recompute the ladder from route 21's cache on the published gate
(5-10 mph, engaged, hands-off, `|cmd| >= 2048`). **It did not reproduce:** my gate gave **n = 572**
against the published **n = 289**, and the duties missed on both candidate sources
(`cs_rate`: 0.9178/0.4493/0.1171/0.0087 vs 0.7439/0.4810/0.2353/0.0484; the `raw14_b4` tap was worse).
⇒ **the ladder's exact gate is NOT recoverable from the cache alone** — the hands-off or command
definition differs from what I reconstructed. **OPEN.** Anyone extending this ladder must first
reproduce the five published rungs; if they cannot, they must not add a sixth.

## ✅ THE FIX IS STRUCTURAL, NOT A RESOLUTION TO BE CAREFUL
Following [[feedback-float-spec-must-be-the-formula]]'s principle — *assert against the mistake so it
cannot be forgotten* — `build_v121_tva.py` now carries:
```
   check(KNEE_NEW not in MEASURED_DUTY,
         "no interpolated duty is asserted for this knee -- the ladder carries MEASURED values only")
   check(2400 < KNEE_NEW < 3600,
         "knee 3000 lies strictly between two MEASURED rungs of the ladder")
```
⇒ **the build now FAILS if anyone adds an unmeasured rung for its own knee**, and it states its
position as *bracketed by 0.0484 and 0.0000* rather than claiming a value. 40/40 assertions.

## ⭐ THE GENERAL RULE
**A table labelled MEASURED may contain only measured values.** If a new dose needs a number:
1. reproduce the existing rungs from data — if they do not reproduce, **stop**;
2. if they do, measure the new one and quote its CI and n;
3. if you cannot, **assert the bracket instead of inventing the point**, and say so in the header.
⚠ This is the second time this session that a plausible-looking interpolation nearly entered the
record as fact; the first was the `0xC64DE` "re-engage ramp" label. ⊕ See
[[accord-headerless-scratch-blob-offsets-are-not-addresses]] — same failure class: **the wrong answer
is specific, plausible, and lands somewhere real.**
