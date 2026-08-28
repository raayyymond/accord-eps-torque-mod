---
name: accord-the-7to9hz-mode-is-nonlinearly-excited-harmonics
description: "The 7-9 Hz oscillation radiates real harmonics at 2f0 and 3f0 - prominence ratio 1.233 against a non-oscillating-window control, route-level bootstrap CI [1.060, 1.503], excluding 1.0. But f0 = 7.81 Hz puts 2f0 at 15.62 and 3f0 at 23.44, so NEITHER lands in the 18-22 or 26-31 Hz grind bands. That resolves two open contradictions at once: the symptoms stay TWO mechanisms (their rate co-location is shared exposure), and a linear resonance driven through a nonlinear element explains both the ring-down and the harmonics. It points at the Coulomb relay as the excitation path."
metadata:
  node_type: memory
  type: reference
---

# ⭐⭐ THE 7-9 Hz MODE IS **NONLINEARLY EXCITED** — real harmonics, but NOT in the grind bands

## [EVIDENCE] The measurement, with its control run first
17 routes, 3,986 engaged windows, NW = 512 (df = 0.195 Hz). For each window take the 6-9 Hz peak
`f0`, then the peak prominence over local shoulders at `2f0`/`3f0` versus **off-multiple controls at
`2.37f0`/`2.63f0`** — positions no harmonic process can populate.
```
   window class     harmonic ratio     median f0
   OSCILLATING          1.308            7.81 Hz
   NON-OSCILLATING      1.061            7.52 Hz     <- THE REAL CONTROL

   OSC / NON-OSC = 1.233     ROUTE-level bootstrap 95 % CI [1.060, 1.503]
```
✅ **The CI excludes 1.0 with the DRIVE as the resampling unit**
([[feedback-one-route-per-build-cannot-resolve-band-ratios]]). ⇒ the 7-9 Hz mode genuinely radiates
harmonics; **something in its excitation path is a hard nonlinearity.**
⚠ The off-multiple controls sat at ~2.0 on their own, so the first pass (1.49×) overstated it.
**The non-oscillating-window control is the one that counts, and it cuts the effect to 1.233×.**

## ✅ RESOLVES CONTRADICTION 1 — THE SYMPTOMS STAY **TWO**
```
   f0 = 7.81 Hz  ->  2f0 = 15.62 Hz     3f0 = 23.44 Hz
   grind bands   :   18-22 Hz           26-31 Hz
   2f0 in 18-22? NO      3f0 in 18-22? NO      3f0 in 26-31? NO
```
🛑 **Neither harmonic lands in either grind band.** ⇒ the harmonic hypothesis **fails**, and
[[accord-18to22hz-grind-is-rate-colocated-with-the-oscillation]]'s 0.2-percentage-point co-location
is **shared exposure, not shared mechanism.**
✅ **[[accord-two-symptoms-two-mechanisms-rez-spectrum]] WINS the disagreement.** The two records are
now reconciled, in its favour. ⇒ **Fixing the 7-9 Hz oscillation will NOT fix grind #1.** Budget for
two fixes.

## ✅ RESOLVES CONTRADICTION 2 — RESONANCE *AND* NONLINEARITY ARE BOTH TRUE
[[accord-ratchet-is-a-lightly-damped-resonance]] excluded a limit cycle on a ring-down
(ζ 0.017-0.036, Q 14-29). Harmonics are usually read as evidence *for* a limit cycle, so this looks
like a fresh conflict. **It is not.** A **linear resonance driven THROUGH a nonlinear element**
produces exactly this: a clean ring-down when the drive stops, and harmonics while it is driven.
⇒ **The coherent picture: a lightly-damped mechanical mode at ~7.8 Hz, excited through a hard
nonlinearity.** Both records stand as written.

## ⭐ WHERE IT POINTS
The hard nonlinearity in this chain with the right character is the **command-proportional Coulomb
relay** in `FUN_0003b8f6` — `fVar13 = clamp(POL·gp-0x6abc·12/knee, ±1)`, a **signum**, the textbook
harmonic generator ⊕ [[accord-engagement-amplifies-6-9hz]] already measured engagement multiplying
this band **2.8×** via that relay.
✅ ⇒ **This strengthens V120's rationale** (`0xC40D2` K1 612→306): if the relay is the nonlinear
excitation path, halving its gain reduces the drive into the resonance. **V120 was recommended on
reasoning alone; it now has a measured mechanism pointing the same way.**
🛑 Still **not** a demonstrated fix — nothing here shows the relay is *the* path rather than *a*
nonlinearity, and [[accord-cbe74-dose-measured-inert-wrong-mode-record]] is a standing reminder that
a relay dose can measure inert. **[BELIEF, one converging line of evidence.]**
Tool: `rlog-tools/studies/peakturn/harmonic_structure_test.py`.
