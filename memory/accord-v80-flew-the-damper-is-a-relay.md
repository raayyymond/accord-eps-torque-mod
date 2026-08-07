---
name: accord-v80-flew-the-damper-is-a-relay
description: V80 flew route 66 and produced the worst grinding the car has ever made — without faulting. Its damper surface is a near-bang-bang Coulomb relay (495 counts flat over a 34x rate range at 97% of the ceiling), and every build-time gate was blind to it because it clips 0.00%.
metadata:
  type: reference
---

# ★★★★★ V80 FLEW — AND THE DAMPER SURFACE IS A COULOMB RELAY

**Route `75604b0a432fdc89|00000066--276b942769`**, 15 segments, **901.71 s / 89,997 frames @ 100.0 Hz**,
engaged (`carControl.latActive`) **30,260 frames = 302.6 s = 33.62%**, 9 engaged episodes ≥ 2 s, speed
−0.09 … 31.34 m/s (112.8 km/h).

**Operator's verdict: the WORST grinding the car has ever produced** — loud, strong, felt through the
whole car, **~90% of LKAS-engaged time**, at both low *and* high speed, causing noticeable vehicle
instability.

🛑 **V80 DID NOT FAULT.** `0x1AB` DTC-active: **0 transitions, 0.000% duty**, 0 × `0x7FFF` sentinels;
STEER_STATUS histogram `{0: 63,861, 3: 26,136}`, same shape as route 65.
⇒ **A STABILITY failure, not a fault-class failure.** [EVIDENCE]

⊕ `build_v80_tva.py`'s own header said verbatim *"GATE 2 (magnitude AND phase) is NOT satisfied by
argument. **V80 IS NOT CLEARED TO FLY.**"* It was flown anyway.

## Build identity (hashes re-verified from disk 2026-08-07)
`39990-TVA,A160-V80-V79BASE-flatC566-ratchet454FE-dose412-probe-6bd0-63fd-67fa-0x13000-0x100000.rwd`
sha `3ea81bd734e6845393d09099754eccb7a0b5682ce147d65d26511c29d37e230d` ·
`_v80_v79base_flatC566_ratchet454FE_dose412_plain_image.bin`
sha `2606d557da9c3a09de6f2b63bd74308e8d6023c3d423e64d9a3b90a3e66211e7`.
Three edits: `0x454FE 0xBA→0xB5` (V42's macro-ratchet fix restored) · FactorC m26 `Y[3]` 908→566 ⇒ flat
`[566,566,566,566]` · FactorE `Y=[0,897,912,927]`.
⚠ **V80's probe cannot distinguish V80 from V78/V79** — byte-identical cave, identical trip rates below
80 km/h. Identity rests on the `.rwd` filename plus the absolute exclusion of V76-V38BASE (13,183 frames
set bit6 with bit5 clear, structurally impossible on that cave). Route 66's `0x14A` byte4 took only
{`0x0F`,`0x1F`,`0x5F`,`0xDF`}; bit5 0/89,997; bit3 positive control **100.000%**.

## ★★★★ THE ROOT CAUSE — the surface, recomputed from the shipped plain images
Records dereferenced through their pointer arrays (FactorC `0xC9E9C`, FactorE `0xC9F84`, ceiling
`0xC77A0`, friction `0xCBE74`), **mode 26** (the car is `TVCA4`: 26 engaged / 24 manual). Dose vs motor
rate **at 5 km/h — and identical at EVERY speed on V80, because its FactorC is flat**:

| rate (ct) | 20 | 40 | 99 | **119** | 150 | 255 | 530 | 1000 | 1941 | 4000 |
|---|---|---|---|---|---|---|---|---|---|---|
| ≈ °/s (4.7121 ct per °/s) | 4 | 8 | 21 | **25** | 32 | 54 | 112 | 212 | 412 | 849 |
| **V75** | 12 | 44 | 137 | 169 | 218 | 297 | 297 | 297 | 297 | 512 |
| **V80** | 82 | 166 | 412 | **495** | 495 | 495 | 496 | 498 | 501 | 512 |

⇒ **V80 emits a constant 495 counts — 3.4% variation across a 34× rate range — at 97% of the 512
ceiling, above only ~25 °/s, at every speed.** V75 plateaus at 297 (58%) and only above 54 °/s.
With `sign(gp-0x6bd0) = −sign(motor rate)` ([[accord-fun3a382-is-a-torque-tracking-pid]]), constant
magnitude + sign-following **is** a Coulomb relay. [EVIDENCE, orchestrator's own LE read of the images]

## 🛑🛑 WHY EVERY BUILD-TIME GATE WAS BLIND — the durable lesson
Every no-clip guard in this kit tests `product > ceiling`. **V80's supremum is `(566*927)>>10 = 512` =
the ceiling EXACTLY**, so it clips **0.00%** and passes. The flat-FactorC edit did not remove the relay —
it **moved it from the ceiling clamp to FactorE's own knee, 17 counts under the rail** (slope drops
~1200× at `X[1]=119`).

> **"DOES NOT CLIP" AND "IS NOT A RELAY" ARE DIFFERENT STATEMENTS, AND ONLY THE FIRST WAS EVER CHECKED.**

📋 **RULE: every damper-surface gate must test the SHAPE (dose(2r)/dose(r), or the describing-function
ratio), not only the ceiling.** ⇒ this is the exact failure [[accord-relu-plan-inverts-at-the-ceiling]]
warned about, arriving through a door that memory did not cover.

## ★★ Describing-function analysis (numerically integrated)
`N(R)` = fundamental-harmonic gain of `force = −sign(rate)·M(|rate|)`. Constant `N` = viscous =
stabilising; `N` rising as amplitude falls = relay = **limit-cycle generator**.

| R (ct) | 25 | 50 | **99** | 150 | 250 | 500 | 1000 |
|---|---|---|---|---|---|---|---|
| V75 @creep | 0.580 | 1.065 | **1.319** | 1.410 | 1.317 | 0.734 | 0.375 |
| V80 @creep | 4.007 | 4.087 | **4.127** | 3.698 | 2.421 | 1.250 | 0.632 |

**Relay-ness `N(50)/N(500)`: V75 1.45× (creep) / 1.43× (60 km/h) · V80 3.27× at both.**
Small-signal loop gain `k`: **V74 0.5799 · V76 1.3866 · V75 1.5798 · V80 4.1597** (2.63× V75, 3.00× V76,
extrapolating 2.6× beyond the last measured point).
🛑 **Modelling note: `k` is a frequency-INDEPENDENT scalar on the whole damper path**, so it *is* the loop
gain at every frequency — two builds differing only in `k` can be compared with no plant model.

## ★★ THE MEASUREMENT THAT SETTLES IT — both builds' own cave probes
`|gp-0x6bd0| ≥ 448 counts`, engaged:

| | duty |
|---|---|
| **V75** (route 5e, 28,317 pre-fault frames) | **0.000%** — never above 128 counts *at all* over 40 km/h |
| **V80** (route 66) | **19.4%** overall · 32.7% above 15 m/s · **71% through the worst 29 s event** |

V75's engaged level census: L0 (dead) 56.8% · L1 (1–127) 25.3% · L2 (128–287) 9.3% · L3 (288–447) 8.6% ·
**L4 (≥448) 0.000%**. ⇒ **V75's damper never entered its saturated regime; V80's lives there.**
[EVIDENCE — the single cleanest statement of the root cause]

## ★ WHAT THE ROUTE SHOWS: a broadband HF FLOOR LIFT, not a new peak
Median engaged periodogram, **V80 − V76**, matched 10–40 km/h stratum:
`7.8 Hz −6.03 · 12.1 −0.20 · 18.0 +0.05 · 21.9 −0.58 · 26.2 +3.75 · 30.1 +5.70 · 35.9 +10.41 ·
44.2 +8.49 · 48.1 +11.47 dB.` **Grind #1's own band is unchanged; the ratchet is 6 dB DOWN; everything
above ~24 Hz lifts by a flat, prominence-neutral offset.** Cell-stratified V80/V76 on the 30–49 Hz floor
= **2.09× [1.46, 2.70]**, and a **pre-declared 32–38 Hz negative control fails identically (2.035)** ⇒
the whole HF region moved together. **This is NOT "grind #2 got worse".** [EVIDENCE]

**Falsifiers (all cell-stratified V80/V76):** torsion bar 30–49 Hz **2.09 [1.40, 2.71]** · steering angle
(a *different* CAN message, `0x14A`) **1.60 [1.26, 2.03]** · **IMU vertical 20–49 Hz 1.07 [0.92, 1.33] ⇒
NOT a rougher road** · openpilot `0x0E4` command 1.25 [1.12, 1.44] · 1–4 Hz driver-input exposure 1.14
[0.88, 1.47].

★ **FFT-FREE CONFIRMATION** — sample-to-sample sign reversals, immune to spectral leakage. Engaged
windows containing ≥1 reversal of `|step| > 300` counts: **V75 3.0% · V74 22.0% · V76 22.0% · V80 73.0%**;
at `|step| > 800`: **V75 0.0% · V74 0.5% · V76 0.6% · V80 23.3%.** Exactly the near-Nyquist chatter a
bang-bang relay injects. [EVIDENCE]

## ★★ A SUSTAINED ~27.4 Hz LIMIT CYCLE THAT NO OTHER BUILD PRODUCES
Engaged windows with 26–31 Hz envelope > 1000 counts: **V74 0/413 · V76 0/328 · V75 0/133 · V80 32/215
(14.9%)**, in segments 8/12/13 at 54–104 km/h.

**Worst event — segment 8, route-global t ≈ 500.9–530.3 s, 99–104 km/h, ~30 s unbroken:** Welch peak
**27.56 Hz at ×92 over the in-band median** (manual at the same speed ×3.1); torsion bar **6,830 counts
p-p**, σ = 1,059; at 10.24 s resolution **27.344 Hz, prominence 292, Q ≈ 140**; steering angle 1.92° p-p,
angle rate 234 °/s p-p; damper ≥448 duty **71%**; `sstat`=0, `sca`=1, `cc_lat`=1 throughout — **no fault,
no lockout.** Envelope rises 50 → 3000+ counts within ~1.5 s of engagement and collapses to ~150 the
instant LKAS disengages.

**Relay tests:** amplitude clamped ±15% over 30 s ✅ · crest factor **1.838** (sine 1.414, square 1.000) =
near-sinusoidal limit cycle ✅ · **NOT wheel order 2** — measured `df/dv` = **−0.131 [−0.231, −0.016]** Hz
per m/s where order 2 demands **+0.961**, and at 54–62 km/h the line sits at 28.7–30.1 Hz where order 2
would be 14.4–16.7 Hz ❌. Speed sweep (engaged, 26–30 Hz peak): 1–5 m/s → 30.3 Hz ×2.1 · 10–15 → 26.2 Hz
×1.6 · 15–20 → 29.1 Hz ×10.3 · **24–32 → 27.6 Hz ×94.9** ⇒ **frequency pinned across a 20× speed range,
amplitude exploding with speed.**

⚠ **The mode is NOT new to V80 — it is the kit's own ~28 Hz line, amplified.** V74's strongest windows
29.4–29.5 Hz at e = 450–531 ct @106–114 km/h; V76's 28.3–28.9 Hz at 815–920; **V80's 26.8–28.2 Hz at
1759–2686**. V80 raised it ~2.7×, dropped `f0` by 1–2 Hz and turned intermittent episodes into a
sustained limit cycle. [BELIEF] the `f0` drop with loop gain is what a control-loop mode does and a fixed
mechanical resonance does not.

## Damper-saturation dose-response, and the "~90%" quantified
17–30 Hz band power by the fraction of each engaged 2.56 s window spent ≥448 counts:
`0–5% → 1.1e3 · 5–20% → 9.2e3 · 20–40% → 3.0e4 · 40–60% → 2.1e5 · 60–80% → 1.4e6` — **three orders of
magnitude, monotone.** ⚠ speed and saturation duty are mutually confounded ⇒ [EVIDENCE] on the
association, [BELIEF] on causal direction.

Scored on the band that MOVED (30–49 Hz), thresholds from V76's own engaged distribution (so V76 reads
50/25/10% by construction): at V76-p50 **V74 42.9% · V76 50.0% · V75 42.9% · V80 79.5% [70.3, 87.7]**; at
p90 **6.8 / 10.1 / 4.5 / 64.7% [52.8, 74.9]**. Per stratum at p50: creep 37.1% · **10–40 km/h 93.9%** ·
**40–80 km/h 80.0%** · **>80 km/h 100%**. Independently, **89.1% of engaged windows ≥100 ct p-p on
17–30 Hz**, and **17.1% of engaged time >1,500 ct p-p — an amplitude reached in ZERO of 432 manual
windows.** Engagement test: median per-edge ratio **×2476** (18–22 Hz) within 4 s of the `latActive`
rising edge, 6/7 edges up; falling edges ×0.34 ⇒ **engagement-conditional, switches on within seconds.**
[EVIDENCE]

⚠ **Command caveat:** openpilot's `0x0E4` carries 25–30 Hz at rms 45.8 ct, correlated **+0.93 at lag 0**
with the bar; bar/command at 27 Hz is **15.8×**. [BELIEF] an echo, not a cause — the EPS LKAS lane is a
~1–5 Hz low-pass on standing EVIDENCE, so a 27 Hz command component cannot reach the motor that way.
Settling it needs a **phase-resolved coherence**, not the lag-0 correlation that was run.
⚠ **Aliasing (common mode):** fs ≈ 100.0 Hz, so 27.344 Hz is indistinguishable from 72.66/127.34 Hz —
identical on all four routes, so it cannot affect the contrast, only the identification.

Related: [[accord-grind1-is-inert-to-the-damper-dose]] ·
[[reference-accord-v74-v75-damper-is-a-sampled-relay]] · [[accord-relu-plan-inverts-at-the-ceiling]] ·
[[accord-damper-evaluator-fun34350-ceiling-clamp]] · [[accord-v81-built-c407e511-friction-stock]]
