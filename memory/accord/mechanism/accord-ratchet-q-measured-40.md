---
name: accord-ratchet-q-measured-40
description: "★★★ 2026-08-04 route 50: the ratchet's Q is measured — Q ≈ 40 at f0 = 7.793 Hz, from a 12.81 s provoked episode, confirmed by a window-cap invariance test (39.0 at cap 54, 40.0 at cap 111). ✅ CONFIRMS the record's Q ≈ 36; what it supersedes is only 'Q is not measurable at NFFT 256'. ⚠ ONE episode; f0 drift would deflate it, so 40 is a LOWER BOUND."
metadata:
  type: reference
---

> 🛑 **AMENDED 2026-08-05 — READ THIS FIRST.** 🛑 **Q ~= 40 is SUPERSEDED — the measured value is Q ~= 14**, and the mode is a **ring-down** with **load-dependent f0**. See [[reference-accord-78hz-mode-characterisation]].

# ★★★ THE RATCHET'S Q IS MEASURED — Q ≈ 40 at f0 = 7.793 Hz

**[EVIDENCE]** From a **12.81 s provoked episode** on route `50--50f2e00e8f`.

★ **The invariance test is what makes it real.** Q reads **39.0 with a window cap of 54** and **40.0
with a cap of 111**. A window-limited estimate would have **doubled** when the cap doubled. It did not.
⇒ **ζ ≈ 0.0125 — about 3× more lightly damped than the 21 Hz mode.**

✅ **Q ≈ 40 CONFIRMS the record's Q ≈ 36.** 🛑 **The ONLY thing superseded is *"Q is not measurable at
NFFT 256"*** ([[accord-ratchet-characterised-on-route-4f]], corrected in place) — **the claim that it
could not be measured, not the value.**
✅ **And it was measured on the RIGHT data — not contaminated by the driver's input.** The episode
reconciles exactly with the transition trace in [[accord-ratchet-is-engagement-required]]
(envelope-based p-p, 2 × 2,452 = 4,904 ≈ 4,894; speed span matches seg1 `t` ≈ 33–46, the
**post-engagement** window, **not** the cranking). **That was the one real risk in the 6,502-vs-591
instrument discrepancy, and it is closed.**
⚠ **It rests on ONE episode.** A second ≥10 s episode would make it two.
⚠ **f0 drift inside the window would DEFLATE Q**, so **40 is a LOWER BOUND**, not a point estimate.

## Everything else route 50 says about the ratchet [EVIDENCE]
- **10 windows / 25.6 s at ≥1200 counts p-p, max 4,894.** Zero-crossing f0 **7.75 Hz**.
- **Speed-invariant** — Theil-Sen **+0.068 [+0.005, +0.247]** Hz per m/s vs wheel-order-1's **0.482**.
- **Engagement-REQUIRED** — see [[accord-ratchet-is-engagement-required]]: with the grip confound
  removed and pooled over four routes, **73/88 = 83.0% engaged hands-off vs 0/118 = 0.0% manual
  hands-off, p = 3.8e-41**, and the rate is **build-independent**. (Route 50 alone read 9/28 vs 1/41,
  Fisher p = 8.7e-4.)
- **In the bar (prom 59), angle-rate (22), angle (15) — NOT in openpilot's command (1.25)**
  ⇒ **the loop closes inside the EPS + plant.** Replicates route `4f`.
- **Per-engaged-window ratchet rate is identical across builds** — V70 **32.1%**, V69 **34.4%**,
  V62 **32.8%** ⇒ **V70 did not add ratchet events.**

★ **The operator's account is corroborated** — the ratchet arrives within a second of the first
engagement. 🛑 **But the causal order in his framing is the other way round:** his hard *manual*
provocation produced **no** ratchet at all; the manoeuvres **set up** the condition and the ratchet
fires **when LKAS engages and he lets go**
([[accord-ratchet-is-engagement-required]]). [BELIEF] the ratchet is also the likeliest referent for his
*"stiffer"* report, since no bus-side instrument detects a stiffness change (effort/impedance
0.79–0.97× every predecessor, all CIs containing 1).

## ⚠ THE LEVER THIS RE-OPENS — the most under-examined result in the archive
**Base-assist damping is EXACTLY ZERO below ~35 km/h** (FactorC `0xD27BC` Y[0] = 0, multiplicative)
while **the ratchet lives at 4.9–8.0 km/h with Q ≈ 40.** And **V47 raised FactorC and FactorE
TOGETHER and reported *"marginally quieter at 5 mph"*** — filed **null against the 21 Hz vibration**.
🛑 **That positive whisper has never been evaluated against the RATCHET.**
★★ **And it is now materially more compelling:** *engagement-required* + *hands-off-conditional* +
*Q ≈ 40* + *damping exactly zero below ~35 km/h* ⇒ **at creep, the driver's hand is the only damping in
the system** ([[accord-ratchet-is-engagement-required]]).
Deferred to V72; **do not stack it on V71.** See [[project_v46_falsified_v47_dampers_only]],
[[reference-accord-damper-two-deadzones-factorC-factorE]].

See [[accord-ratchet-characterised-on-route-4f]], [[accord-ratchet-is-a-saturated-resonance]],
[[accord-state4-cadence-refuted-state-is-sticky]], [[accord-v70-flew-grind1-back-at-stock]].
