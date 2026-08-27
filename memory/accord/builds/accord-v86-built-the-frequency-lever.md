---
name: accord-v86-built-the-frequency-lever
description: "V86 = flown V85 + one cell 0xC40D4 573->286; the kit's first PHASE/LAG lever, pre-registered as a FREQUENCY ratio f(V86)/f(V85) in [0.797, 0.875], with a proof that an EMA cannot limit max angle rate."
metadata:
  node_type: memory
  type: project
---

★★★★ **V86 IS BUILT AND UNFLASHED.** Base = the flown **V85**. **ONE control cell, TWO bytes**, plus a
probe cave. Builder `analysis-2020accord/builds/v80_v107/build_v86_tva.py`; gate checker
`analysis-2020accord/verify/verify_v86_gates.py`.
🛑 **Artefact names and SHA256s must be read from disk, never from a report.**

**THE ONE CELL: `0xC40D4` (`tp+0x50D4`) 573 → 286**, bytes `3D 02` → `1E 01`.
It is the **command-branch EMA** inside `FUN_0003b8f6`: **α = 0.1399 → 0.0698.**

## IT IS A FREQUENCY EXPERIMENT, PRE-REGISTERED AS A RATIO
It moves the loop's **−180° crossing from 7.79 Hz to 6.2–6.9 Hz**.
**`f(V86)/f(V85) ∈ [0.797, 0.875]`** — median **0.843**, min/max over Q ∈ [2, 40] × delay ∈ [0, 10] ms.
That is **3.3 FFT bins at NFFT 256 / fs 100 Hz**.
- ✅ **CONFIRMED** if the peak lands in **[6.2, 6.9] Hz** with the ratio CI excluding 1.00.
- 🛑 **FALSIFIED — [[accord-ratchet-is-a-linear-loop-oscillation]] DIES — if it stays at 7.79 Hz.**
- ⚠ **AMBIGUOUS, and explicitly NOT a null**, if the ratcheting is too weak to locate a peak.

**Why a frequency claim at all:** amplitude ratios have **failed four builds running**, and the
split-half null is **[0.63, 1.50]** wide. A frequency shift is the one prediction this instrument can
resolve.

**Why 286 and not 1146** (the same swing, other direction): 286 moves **away** from the 12.8 Hz plant
mode — conservative on the **unpinned** Q — and it **LOWERS** estimator HF gain to **0.650× @20 Hz /
0.585× @28 Hz**, where 1146 would **raise** it 1.216× / 1.355×.

## 🛑 IT CANNOT LIMIT MAX LKAS ANGLE RATE, AND THIS IS PROVED
An EMA has **`|H(0)| = α / (1 − (1 − α)) = 1` EXACTLY, for every α** — verified numerically at
α ∈ {0.0349 … 0.9998} → **1.000000000000**. **Only transient tracking changes.** The operator's standing
hard constraint is satisfied **by construction**, not by argument.

## MODE PROOF (RULE 7)
**573 appears exactly once in `[0xC4000, 0xC4200)`**, and **no stride S ∈ [2, 0x400) repeats it**
(contrast FactorC's stride `0x14`). It is a bare `tp` scalar.

## THE PROBE — `0x14A` byte 4
`b7` = `gp-0x6b70 < 0` · `b6` = `gp-0x6b70 != 0` · `b5` = `|gp-0x6b70| ≥ 512` ·
`b4` = `gp-0x67ab < 2` (**the aggregator gate**) · `b3` = 1 fingerprint.
**`b7⇒b6` and `b5⇒b6` are EXACT — the DUALS of V85's `b6⇒b7`** ⇒ **one `b6 ∧ ¬b7` frame refutes V85 and
one `b7 ∧ ¬b6` frame refutes V86.** Identity is free, with no free parameter.
⊕ **`b7` + `b6` is a free RELAY-vs-LINEAR discriminator:** a linear term must pass through zero at every
sign change (`b6` clears near `b7` transitions); a relay jumps (`b6` stays set).

## ⚠ V86B WAS DESIGNED AND IS ON HOLD
A damper creep re-open (**FactorE `X[0]` 60 → 12**). The cross-build dose-response is **3.2× with
rho = −0.679** and the dose crosses build order twice — **but** the within-route engaged/manual test
shows **no separation**, **V83a is a counterexample**, and the test **cannot run on V84 at all**.
`[BELIEF]`, not established.
📋 **What settles it costs ZERO BYTES: a creep protocol alternating engaged and manual over the same
stretch at 2–9 m/s.** Run that before spending a build.

## WHAT CLASS OF BUILD THIS IS, AGAINST THE ARC SINCE V38
V38 authority · V39–V52c rate guards / slew caps / EMA poles as attenuators / notch biquads (V40 and
V48B bricked) · V53–V61 telemetry and lane mutes · V62–V73 the rate lane · V74–V83a the base-assist
damper · V84 damper reverted to Honda · V85 **nonlinearity SHAPE** (relay → viscous) ·
**V86 PHASE / LAG — move a loop mode's FREQUENCY. Nothing in the arc has ever done this.**
`0xC40D4` has **never been written by any build**, and the *dimension* has never been an arm.
⚠ The honest caveat: its target, **ratcheting, has no instrumented history**, and the claim rests on a
frequency shift a weak ring may not resolve — which is why **AMBIGUOUS** is pre-declared as its own
outcome and not folded into "null".

Related: [[accord-ratchet-is-a-linear-loop-oscillation]],
[[accord-v85-flew-lever-delivered-bands-are-null]], [[accord-plant-model-residual-aggregator-chain]],
[[feedback-a-falsifier-only-fires-if-it-could-have-fired]].
