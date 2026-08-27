---
name: accord-two-ratchets-micro-is-the-779hz-line
description: There are TWO ratchets. MACRO is what the operator reports fixed and is unmeasurable; MICRO IS the 7.79 Hz line, unattenuated on V72, and inaudible by physics.
metadata:
  type: reference
---

🛑 **THERE ARE TWO RATCHETS. The operator settled this himself when asked directly** (2026-08-05):
> *"I think 7 Hz and micro ratcheting could be the same thing. **Macro ratcheting was fixed.**"*

## ✅ 2026-08-08 — THE TERMINOLOGY, RESTATED SO IT STOPS DRIFTING

**This is the kit's naming of record. Use these two words and no others:**
- **MICRO = the 7.79 Hz line.** The operator named it at V72: *"not audible, only felt in the column."*
- **MACRO = the large hard-turn symptom.** It **has never been successfully instrumented** — two
  purpose-built detectors returned **64 of 65 comparisons inside their own split-half nulls** and
  **both failed their own positive control** (detail below, unchanged).

⇒ A statement about "the ratchet" with no MICRO/MACRO qualifier is **not a verdict**. A stale snapshot of
this memory drifts the terminology back; see [[feedback-read-the-repo-memory-not-the-stale-snapshot]].

| | what it is | status after V72 |
|---|---|---|
| **MACRO** | the large-scale symptom he reports fixed | **fixed per operator — but UNMEASURED and UNATTRIBUTED** |
| **MICRO == the 7.79 Hz line** | *"not audible, not mechanically heavy, felt in the steering column and wheel"* | **STILL PRESENT, attenuation factor 1.0** |

★ **His description is exactly right and physics explains it: 7.7 Hz is BELOW the ~20 Hz hearing
threshold**, so it is felt as discrete steps and never heard. 20.4 Hz (grind #1) sits on the threshold
with an audible 40 Hz harmonic. That single fact identifies which symptom is which.

## MICRO IS NOT GRIND #1 AT LOWER AMPLITUDE — six independent tests, all the same way
The operator explicitly asked for frequency analysis to confirm equivalence. **The answer is NO:**
1. **Tracking slope** d(f_hi)/d(f_lo) = **-0.0024 [-0.277, +0.312]**, 2.0 excluded — with a **working
   positive control** (an injected line that genuinely tracks at 2.0 is recovered as 1.544).
2. **Ratio reproduces under shuffled pairing** (2.514 observed vs 2.572 [2.465, 2.660] shuffled) ⇒ carries
   no pairing information.
3. **Co-occurrence is generic** — r(6-9, 18-22) = +0.67 but the control bands give +0.59 / +0.57; the
   paired within-episode excess over control **includes 0**.
4. **They dissociate** — 13% of engaged-creep windows are loud in one band and quiet in the other.
5. **Amplitude kills "lower-amplitude continuation" outright** — the 7.8 Hz line moves the rim
   **FURTHER** (1.90 vs 1.43 deg p-p). It is not the quiet one.
6. **Opposite-signed dependence on steering position** (see [[accord-grind1-is-a-limit-cycle]]).
   **Two amplitudes of one oscillation cannot move in opposite directions across the same boundary.**

## MICRO WAS NOT FIXED BY V72 — three independent instruments
D3 **1.269 [0.176, 1.936]** · D4 **0.80–1.18, every ratio inside its own split-half null** · D1 **1,261
p-p / 54% hit rate** vs the **stock pool's 1,267 / 51%**. The column moves **2.1–2.5x FURTHER** on V72
than on V71B/V71C. Two escape hatches closed: **48/48 hits in DRIVE** (not reverse), and the raw
unfiltered waveform shows bar torque −2,701 to +2,634 counts with 15 zero crossings in 2.56 s, hands-off.
⇒ **`docs/specs/design/V72-DESIGN.md`'s "the ratchet is fixed" must not be carried forward. It was never fixed** —
and per [[accord-damper-is-mode-table-selected]] the damping lever aimed at it **was never in force.**

## MACRO IS UNMEASURED, AND THE INSTRUMENTS FAILED THEIR OWN POSITIVE CONTROL
Two purpose-built detectors (an unwind detector on literal *steps per second* in the return velocity, and
a wind-up detector matched to the state-4 governor's "forbids magnitude increase" behaviour) returned
**64 of 65 comparisons inside their own split-half nulls.** But the operator reports macro **present on
V71B/V71C and absent on V72** — an A/B — and **both instruments show V72 ≈ V71B ≈ V71C on every
statistic.**
> **An instrument that cannot separate the arm the operator separates is not measuring the thing.**
⇒ The null is **uninterpretable in BOTH directions**: it is not evidence macro is unfixed, and the flat
r26 dose-response across it is **not** evidence against Lever A. Same failure class as V72's `bit4`.
⚠ **Therefore macro is UNATTRIBUTED, and V73 carries all of V72 byte-identically and only ADDS.**
🛑 To build a working macro instrument, the trigger must come from the operator first: **how big a
steering input, at what road speed, and does it happen turning in, holding, or coming back?**
