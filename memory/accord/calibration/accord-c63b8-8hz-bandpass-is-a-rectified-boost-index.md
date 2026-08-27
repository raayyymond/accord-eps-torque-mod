---
name: accord-c63b8-8hz-bandpass-is-a-rectified-boost-index
description: "FUN_0003b66a holds a real 8.13 Hz band-pass (Q 0.501) whose cals were never touched in 88 images — but it is RECTIFIED into a boost-gain LERP index, not a damper. Refuted five ways; do not build it."
metadata:
  node_type: memory
  type: reference
---

🛑 **A REAL STRUCTURE, THE WRONG CLASS.** `FUN_0003b66a` (task 1, 1 kHz) contains a backward-difference
derivative → **two cascaded first-order EMAs sharing one alpha** → output gain → clamp ±10 → ×1024.
Derivative × 2 poles = a **band-pass**, and four independent agents reproduce its response:
**peak 8.13–8.14 Hz · Q 0.501 · phase +1.44° · −3 dB 3.38–19.64 Hz.**
Cals `0xC63B4` = 51 (α = 51/1024, pole corner 8.133 Hz) and `0xC63B8` = 41. **Byte-identical to stock in
all 88 build images** — never touched, ever.

⚠ **The centring is not a tuned resonator.** `|jω/(1+jω/ω_c)²|` ALWAYS peaks at ω_c and ALWAYS has
Q = 0.5. "Peak at 8.13 Hz" restates "the LP corner is 8.13 Hz". At Q = 0.5, 7.79 / 21.09 / 27.4 Hz all
sit within ~3.5 dB of the peak — it is a broad rate smoother.

## 🛑 REFUTED FIVE WAYS — do NOT build `0xC63B8` in either direction
1. **FULL-WAVE RECTIFIED.** `gp-0x6ba6 = |gp-0x6b9a|` (`subr r0,r13` @`0x3b87a`). All 7 readers of the
   signed cell are `|x| ≤ 25600` plausibility windows and the value dies in a register two instructions
   later. **There is no summing junction. `abs()` destroys the phase**, so "in phase with rate ⇒ viscous
   damping" does not apply — the live path is a **LERP INDEX into the boost amplitude tables**.
2. **FactorB is flat `[1024,1024,1024,1024]` in ALL 34 records** ⇒ the damper arm is inert at any gain.
3. **FactorC `Y[0]` = 0 below 35 km/h** zeroes the whole five-factor damper product at creep anyway.
4. **The boost arm is the V58/V59/V60 parametric pump — FLASHED and NULL.** `BUILD-LINEAGE.md` marks
   that arc CLOSED and says *"do not propose it as a grinding fix"* of the neighbouring cal `0xC63BA`.
5. **No headroom, wrong dose curve.** Stock already sits at **37.8 % of clamp at max** (NOT 1–6 %); 4×
   reaches **151 %** and clips — the V80 relay regime. Raising it costs up to **46.9 % of parking
   assist** for a **0.01 %** change in the ratchet's decay rate: **185× below the Mathieu threshold**.
   The clamp is BEFORE the ×1024, so raising the gain does not raise the ceiling — only the dwell at it.

★ **The parametric framing is structurally subordinate.** `|cos t|` = 2/π (DC) + 4/3π (2f) …; in the
cycle-energy integral the 2f term enters at weight **0.2122** against DC's **0.6366** — **3.00:1, and
`cos θ ≤ 1` means no phase (including the 100 Hz ZOH's 28.8° at 2f) can overturn it.**

## ⊕ IT IS AN EXCELLENT *SENSOR*
`gp-0x6de8` (the band-pass output ×1024), `gp-0x6de4`, `gp-0x6d04`, `gp-0x6d00` are each **1 writer /
0 readers** — a free, already-tuned, frequency-selective ratchet-amplitude instrument with **zero blast
radius**, and the strongest cave-state RAM class in the image (a dedicated `st.w` is POSITIVE evidence
the compiler allocated a named scalar, which a buffer slot can never show).

## 🛑 THE SIZING FIGURE THAT MISLED THE ORCHESTRATOR
`STATE.md`'s *"1–6 % of its ±10 clamp"* is about **`0xC646E`**, not this cell, and its own source memory
says **"(prior-session estimate)"** — never measured for either. The two cells differ in scale by
**16,384×** (`0xC646E` 2⁻²⁴ vs `0xC63B8` 2⁻¹⁰) and live in different functions
(`0x3bb92` vs `0x3b80a`), one access each, **disjoint — they do not compound.**

Related: [[accord-v87-built-measurement-on-v38-base]], [[accord-v59-parametric-pump-marginal]],
[[accord-v80-damper-relay-and-grind1-inert]], [[feedback-run-the-control-before-the-measurement]].
