---
name: accord-fun38148-weights-have-an-unresolved-sign
description: "gp-0x6b70 is a PID REFERENCE, not an aggregator addend — so the SIGN of any FUN_00038148 lane-weight change depends on the sign of iVar6 and the local slope of a RAM-resident LERP, neither of which is known. This strikes 0xC63A6 and blocks all six weights until the slope is measured."
metadata:
  type: reference
---

# 🛑🛑★★★★★ THE SIX `FUN_00038148` WEIGHTS ARE BLOCKED BY AN UNRESOLVED **SIGN**, NOT BY MAGNITUDE

Traced 2026-08-12 to a **NO-GO** verdict on `0xC63A6`, and the reason generalises to all six weights.

## WHY `0xC63A6` LOOKED LIKE THE BEST LEVER IN THE KIT

`0xC63A6` is `w[3]` in `FUN_00038148`, **stock 1024 (Q10 = ×1.000)**, sitting directly on the
`gp-0x6b26` lane, and **VIRGIN across all 85 build images**. Meanwhile:
- `gp-0x6b26`'s direction is **measured** — V94 cut it 6× and the operator judged the car unsafe to
  drive ⇒ [[accord-v94-flew-and-the-lane-is-a-damper]];
- the usual route up, `0xCBE74`, is **exhausted** — ×1.5 is ≈94 % of its range before int32 wraparound
  at 1.6005×.

So it read as a second, independent multiplier on the one signal whose sign we actually know.

## Q1 — IT IS A CLEAN, SINGLE-READER CELL [EVIDENCE, three methods]

`0xC63A6` weights **only** `gp-0x6b26`, through exactly **one** instruction:
`ld.hu 0x73a6,tp,r15 @ 0x381ca` in `FUN_00038148`. **Zero writers.** Path 1 (`FUN_0003aa2c`) never
reads it.

🛑 **`get_xrefs_to(0xC63A6)` returned "No references found" — a FALSE ZERO.** That is the Ghidra
**tp-relative xref blind spot**, and taking it at face value would have concluded the cell was dead.
It was overridden by `search_instructions` **and** a raw Python LE scan (disp16, LE32 absolute,
`movea` lower-half). Two false positives — `be 0x000473a6` (branch-target text collision) and a `jarl`
displacement coincidence at `0x652aa` — were each **disassembled and excluded**, not hand-waved.
⇒ add to [[accord-v850-scan-traps-formatv-and-storezero]].

## 🛑 Q2 — WHAT KILLED IT: `gp-0x6b70` IS A **PID REFERENCE**, NOT AN ADDEND

```
sum6 = w6b4e + w6b4c + w6b26 + w6b46 + w6bd0 + w6bbe        # 0xC63A6 scales ONE of six
target = ((sum6 * polarity * 2639) >> 10) * 16               # 0xC6468 = 2639  ~= x2.578 net
gp-0x374c += ((target - gp-0x374c) * 102) >> 10              # 0xC63AC = 102, IIR pole
iVar6  = gp-0x6bfe + gated(gp-0x6bfa, +-20000) - (gp-0x374c >> 4)
gp-0x6b70 = sign(iVar6) * RAM_LERP(|iVar6| * 1024 >> 10)     # <-- THE UNKNOWN LOCAL SLOPE
            clamp(+-8192)                                     # 0xC6200 = 8192
         -> gp-0x6ad6 -> error = measured_torque - reference -> PID -> aggregator
```

**Path 2 is NOT negligible** — so this is *not* a magnitude-based kill. It is worse: because
`gp-0x6b70` becomes a **reference that is subtracted**, the sign of the whole path's contribution
depends on **(a)** the sign of `iVar6` at the operating point (`gp-0x6bfe` / `gp-0x6bfa` untraced) and
**(b)** the **local slope of a RAM-resident LERP** there. Neither is known.

Phase, for scale: the IIR alone is **|H| = 0.94/0.91/0.88 at −18.7°/−23.6°/−26.8°** for 6/7.79/9 Hz;
stacked on the PID's own −11° to −27° at that band
([[reference-accord-fun3a382-pid-phase-6to9hz-standing-correction]]), **Path 2 runs ≈ −30° to −54° of
lag against Path 1's 0°, unity, unconditional.**

## ★★ Q3 — THE STRUCTURAL RESULT, AND IT SPLITS. This is the reusable part.

**(a) The FORWARD-PATH (open-loop) small-signal sign IS determinate.** [EVIDENCE, derived]
Because `gp-0x6b70 = sign(iVar6)·f(|iVar6|)` is the natural **odd** continuation of `f`, its derivative
w.r.t. anything upstream of the sign-split is `f'(|iVar6|)` **regardless of `sign(iVar6)`** — the two
`sign(iVar6)` factors in the chain rule (one from `d|iVar6|/d(gp-0x374c)`, one from re-applying the
sign) **square to +1 and cancel exactly.** ⇒ **the unknown sign of `iVar6` does NOT actually matter for
the open-loop direction.**
Combined with `FUN_00037fe6` (weight `0xC64B0` = 1, **no negation** on this term — ⚠ unlike the sibling
`gp-0x6b4a` term, which IS negated) and the PID sign chain, the open-loop forward sign of
`d(aggregator via Path 2)/d(0xC63A6)` is **`+sign(gp-0x6b26)`** ⇒ it would **REINFORCE** Path 1's
already-measured-dissipative delivery — *if* the LERP is monotone-non-decreasing (`f' ≥ 0`, plausible
for a calibration curve but **unconfirmed**) and polarity is +1.

**(b) 🛑 BUT PATH 2 IS A REAL CLOSED LOOP, AND THAT IS WHAT KILLS IT.** [EVIDENCE for the topology]
`gp-0x6bfe` is derived from **the aggregator's OWN previous-cycle output** —
`gp-0x6b98[n−1] → FUN_0003b8f6 → gp-0x6bfc → FUN_0003bc20 → gp-0x6bfe`. That is a **genuine 1 kHz
digital feedback loop with one sample of delay**, not a feedforward chain. Closed-loop behaviour is
governed by a loop gain `L` — `FUN_0003b8f6`'s float EMA cascade, **eight coefficients at `tp+0x50d4`,
`0x50d8`, `0x504c`, `0x5050`, `0x50bc`, `0x50d0`, `0x50d2`, `0x50d6`** — **never byte-read by any
session** — crossed with the LERP's local slope. **Two separate attempts to extract the LERP knots
from `FUN_000389ec` (a 200-line per-vehicle normalisation / median-of-3 / shadow-lockstep state
machine) have failed.**

**Linear-sub-path phase, from the image's own IIR pole (`a = 102/1024`):**

| Hz | 6 | 7.79 | 9 | 18 | 21 | 26 | 31 |
|---|---|---|---|---|---|---|---|
| \|H\| | 0.94 | 0.91 | 0.88 | 0.68 | 0.62 | 0.54 | 0.48 |
| phase | −18.7° | −23.6° | −26.8° | −44.0° | −47.8° | −52.7° | −56.2° |

Stacked on the PID's own lag, Path 2's linear portion runs **≈ −30° to −56°** across the band, against
Path 1's **0°, unity, unconditional**. ⚠ **This describes the LINEAR sub-path only and says nothing
about the loop-gain crossing in (b), which is what dominates the direction question.**

## ✅ Q4 / Q5 — one clean result each
- **Q5 CLOSED [EVIDENCE]: `0xC63A6` is a FLAT, NON-mode-indexed scalar** — one fixed `tp+0x73a6`
  displacement, one occurrence image-wide, no per-mode record. **RULE 7 is satisfied** and the
  mode-10-vs-TVCA4 trap does not apply. ⊕ Structural distinction worth keeping: `FUN_00038148`'s
  caller gate `uVar4 = uVar2 & 0x830` is a **`gp-0x67fa` STATE gate**, not a **`gp+0x63fd` MODE gate** —
  the two are different things in this firmware and are routinely conflated.
- **Q4 partial:** the **±1024 gate on `gp-0x6b26` inside `FUN_00038148` is evaluated on the RAW,
  pre-weight value**, so changing `0xC63A6` **cannot** interact with it. No gate-based clip risk from
  the weight change itself. Downstream headroom to the ±8192 clamp is **unmeasured** — no build has
  ever telemetered `gp-0x374c` or `gp-0x6b70`, so the RULE-8 observed-envelope check cannot be run.

## 🛑 THE RULE

**A lever whose SIGN is unresolved is not a lever — it is a coin flip.** That is exactly how V94
reached the car: a direction reasoned to rather than measured.
⇒ **No `FUN_00038148` weight may be moved until the LERP's local slope at the real operating point is
MEASURED.** This blocks all six, not just `0xC63A6`.

## 🛑🛑 THE INVERSION FIGURES ARE A **SWEPT GUESS MISLABELLED AS A CENTRAL ESTIMATE** [EVIDENCE — read at source]

The 0.59/0.56 → 1.18/1.12 "inversion boundary" that gets cited for this architecture comes from
`analysis-2020accord/studies/sessions/v77/v77_gate2_loop_and_friction.py` §3:
```
K   = (W/1024) * (2639/1024) * EMA(f, alpha=102/1024) * g4
L   = PID(f) * K
net = 1 - L
```
`PID(f)` and the IIR are built from **genuinely byte-read cals**. **`g4` is not.** The script's own
line 87 says, verbatim:

> `g4 is presented as a SWEEP, not a guess.`

and line 93 sweeps `g4 ∈ (0.25, 0.5, 1.0, 2.0)`. **A later session lifted the `g4 = 1.0` row out of
that bracket and relabelled it "the central estimate." The script never claimed it.**

🛑 **And the topology is feed-forward only.** The header states the damper *"reaches the motor by TWO
parallel FEED-FORWARD paths and closes only through the **PHYSICAL plant**"* — so `net = 1 − L`
**contains no firmware-side feedback at all**, and in particular does not contain the
`gp-0x6b98[n−1] → gp-0x6bfe` path documented above. **Two compounding sources of uncertainty, not one.**

⇒ **The qualitative claim "an inversion boundary exists somewhere" survives** — `net = 1 − L` genuinely
can cross zero. **The specific numbers, and the claim that W = 1024→2048 straddles it, do not.**
⇒ **Cite those figures only with this marker attached.**

⊕ **This is a recurring failure shape in this kit and it is worth naming: a bracketing SWEEP becomes a
central estimate becomes a fact, and nobody re-reads the header.** Same shape as the two `gp-0x6b26`
phase figures and the retracted task-5 rate. ⇒ [[feedback-a-count-is-not-a-physical-fact]] ·
[[feedback-run-the-control-before-the-measurement]]

⊕ **The NO-GO does not depend on any of this.** It rests on the sign being *unmeasured*, and the
provenance audit makes it **stronger**: *nobody has a trustworthy model **or** a measurement* beats
*the model says invert*.

## ⚠ AN OPEN CONTRADICTION — do not treat the inversion model as settled

A claimed inversion boundary at `0xC63A0` 1024→2048 (combined stage1+PID magnitude **0.59/0.56
"damping" → 1.18/1.12 "INVERTED"**, at 7.79 and 21 Hz) is the reason the sign risk is taken seriously.
**But `0xC63A0` = 2048 has FLOWN four times — V72, V73, V76g, V81 — and measured INERT**, with V81
fault-free on route 67. A model predicting a damping→inverted transition at exactly that value should
not produce four inert flights. Either the model is wrong, or "inert" was measured **hands-off, in the
wrong regime** ([[reference-accord-steeringpressed-mask-excludes-the-symptom-regime]]), or Path 2 is
small at the flown operating point — which would contradict Q2. **Unreconciled.**

## ⇒ WHAT THIS MADE V95

**V95 was re-scoped to measure the blocking unknown instead of guessing past it**: it puts
**`gp-0x374c` (the LERP input) and `gp-0x6b70` (its output)** on the wire simultaneously, which yields
the LERP's **local transfer at the real operating point**. That unblocks the whole weight class rather
than ranking six lanes.

Links: [[accord-v94-flew-and-the-lane-is-a-damper]] · [[accord-gp6b26-is-a-real-6to9hz-damper]] ·
[[feedback-reducing-a-gain-is-not-a-safety-class]] · [[accord-friction-polarity-more-assist]] ·
[[accord-v80-damper-relay-and-grind1-inert]] · [[accord-v64-null-is-on-the-gate]] ·
[[accord-aggregator-reaches-motor-via-gp6acc-bridge]]
