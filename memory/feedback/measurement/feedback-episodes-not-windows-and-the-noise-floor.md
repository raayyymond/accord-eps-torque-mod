---
name: feedback-episodes-not-windows-and-the-noise-floor
description: 🛑 Bootstrap over EPISODES, never windows, and establish the noise floor with a split-half null BEFORE quoting any ratio. This session's 2.2x floor retracted three of the orchestrator's own claims.
metadata:
  type: feedback
---

# 🛑 EPISODES, NOT WINDOWS — and measure the noise floor before quoting a ratio

**Why:** windows inside one contiguous run are correlated. Bootstrapping over windows shrinks every CI by
roughly `sqrt(windows_per_episode)` (~√28 on route 37) and **manufactures significance**. Shrinking NFFT
does not buy resolution either: 256/128/64 gave 266/537/1086 windows but **18/19/19 episodes**.
**Episodes are the binding constraint.**

**How to apply:**
1. **Run a split-half-by-episode null first** (parity split, same statistic). On route 37 this returned a
   median CI width of 4.9–7.8× ⇒ **a resolution floor of 2.2–2.8×. Any ratio inside [0.45, 2.21] is
   indistinguishable from noise.** Judge every result against that, not against 1.0.
2. **Run a negative-band control** — a band where neither effect lives (30–40 Hz here). It came back at
   ~1.0, which is what makes a band-specific claim defensible rather than a route/gain offset.
3. **Run a true cross-route null** (V59 vs V64, spectrally identical builds). ⚠ **V64 cannot serve as a
   control for stratified work** — 3 episodes, CIs [0.14, 61], and a very different drive profile
   (|rate| p50 17.8 vs 2.9). It IS usable as a cross-route null for the rate statistic (0.87–0.92).
4. **Speed-standardise** every ratio (compute per speed sub-bin, combine as a weighted geometric mean) so
   a route speed-distribution difference cannot masquerade as the effect under test.
5. **Count distinct BURSTS, not crossings.** V62's 43 excursions >2000 were **one 0.92 s burst**;
   treating them as independent is wrong by ~43×.
6. **Pool a WITHIN-route contrast across routes** when you need power — each route contributes its own
   internal engaged-vs-manual comparison, so cross-route exposure weakness does not apply. That is how the
   ratchet's LKAS gating reached p = 1.09e-08 from routes that were individually p = 0.10.

**What it cost when skipped, this session — three of the orchestrator's own claims, all retracted:**
- *"V62 amplified the ratchet 2–3×, gated on driver effort"* — inside the noise floor; every CI covers 1.
- *"Band power tracks driver effort"* — it tracks **motor rate**. Partial ρ(effort|rate) is **negative**
  in both builds (−0.13…−0.39) while ρ(rate|effort) is **+0.57…+0.70**. Effort was only ever a proxy.
- *"The ratchet's f0 moved 8.18 → 7.71 Hz"* — **Simpson's paradox.** Speed-matched there is no consistent
  shift; f0 rises with speed on every build (ρ +0.36…+0.59). (V61 IS genuinely down, 6.51–6.75.)

★ **Prefer the transient statistic `|d(tq)|` for CROSS-ROUTE comparison.** Its true cross-route null is
**0.87–0.92** (within 13% of 1.0) versus 0.63–1.23 for band power. ⚠ But it is a high-pass of `tq`, so it
is **partly the same measurement** as 18–22 Hz band power — do not double-count "cleaner everywhere" as
an independent win. The genuinely new information is the **shape** (monotone with threshold).

⚠ **Two more traps hit this session:** averaging overlapping-window spectra and then taking prominence of
the average invented a "41–48 Hz line" that no per-window presence test supports; and a u32 read of a LERP
record whose `count` is **u16** shifted every field by 2 bytes.

Pairs with [[feedback-probe-the-gate-not-just-the-output]] and
[[accord-check-build-lineage-before-proposing-lever]].
