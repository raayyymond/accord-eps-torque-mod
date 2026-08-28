---
name: accord-we-add-a-new-7to9hz-antidamped-feature
description: "Fine Re(Z) against the STOCK arm: above 12 Hz our firmware is essentially stock (ratios 1.04-1.28), but below 12 Hz it is 2-5.5x worse, peaking at 5.48x in the 8-9 Hz band. The SHAPE moves too - stock's worst point is 12.9 Hz at -60, ours is 8.6 Hz at -90. So we do not merely scale Honda's anti-damping; we ADD a localized feature at 7-9 Hz, exactly where the peak-turn oscillation lives."
metadata:
  node_type: memory
  type: reference
---

# 🛑🛑★★★★★ WE **ADD** A NEW ANTI-DAMPED FEATURE AT 7–9 Hz — ABOVE 12 Hz WE ARE STOCK

2026-08-27. `Re(Z)` = `Re(H1[rate → column torque])`, Welch 2048-pt, engaged & low-torque & moving.
**STOCK = route 97, 573 s engaged. V112 = routes 22+23, 809 s engaged.** Same estimator both arms.

```
     Hz     STOCK   coh2  |   V112   coh2  |  V112/STOCK
    7- 8    -12.0  0.281  |  -43.1  0.545  |    3.58
    8- 9    -14.1  0.286  |  -77.2  0.730  |    5.48   <- the peak
    9-10    -31.5  0.541  |  -67.4  0.672  |    2.14
   10-12    -31.8  0.409  |  -66.1  0.571  |    2.08
   12-14    -45.4  0.454  |  -57.3  0.491  |    1.26
   14-16    -27.1  0.457  |  -33.1  0.441  |    1.22
   16-19    -13.6  0.332  |  -14.8  0.477  |    1.06   <- essentially STOCK
```
🛑 **Above ~12 Hz our firmware is INDISTINGUISHABLE FROM STOCK (1.04–1.28).**
🛑 **Below 12 Hz it is 2–5.5× worse, and the feature MOVES:**
**stock's most anti-damped point is 12.9 Hz at −60.2; V112's is 8.6 Hz at −89.9.**
⇒ **This is not a scaling of Honda's anti-damping. It is a NEW, localized feature at 7–9 Hz** —
exactly where the peak-turn oscillation sits (7.42 Hz, rising into the 8 Hz peak).

⊕ **The estimator is corroborated**: f0 moves **21.03 Hz (stock) → 22.89 Hz (V112)**, reproducing the
kit's independently published **21.90 → 24.90 Hz** shift with gain
([[accord-f0-crossover-is-the-endpoint]]). Two methods, same direction and scale.

## ⭐ THE LEADING CANDIDATE — **UNCONFIRMED**
Among the 29 live V112-vs-stock calibration edits, **`0xC649B` 0 → 1** is the only one that is
simultaneously **engagement-gated, command-independent, and frequency-localized**: it **ARMS Honda's
dormant biquad, engaged-only** (`BUILD-LINEAGE-PART1` — the real gate is
`cal(0xC649B)==1 AND cal(0xC64FA) ≤ gp-0x671a`, opened by a code patch at `0x35A12`).
🛑 **The biquad's COEFFICIENTS (`0xC60A8`–`0xC60B7`) are BYTE-IDENTICAL to stock on V112** (V108's
"NOTCH.HONDA" revert). **We do not reshape Honda's filter — we switch it on where Honda leaves it
off.** A filter armed only when engaged is exactly the shape of an engagement-conditional,
command-independent, band-localized change.
⚠ **NOT CONFIRMED.** A first attempt to compute the filter's response guessed the coefficient
grouping (b0,b1,b2,a1,a2) and produced a nonsense answer (peak 20× at 49 Hz); the real grouping and
the filter's sample rate are **not established**, so **no claim is made that its peak is at 7–9 Hz.**
Settling it needs the actual `FUN_00035a08` arithmetic read in order, not a guessed layout.

## ✅ THE ONE-BYTE FALSIFICATION TEST
**`0xC649B` 1 → 0 disarms it.** One payload byte on the V112 base, single-variable, no cave edit,
trivially reversible. If the 7–9 Hz excess collapses toward stock, the mechanism is found; if it
does not, this candidate dies cleanly and the search moves on.
⚠ Arming the biquad was deliberate (V103 "BIQUAD.ENGAGED"), so disarming is a further revert and its
on-car effect is **untested in either direction**.

Related: [[accord-two-symptoms-two-mechanisms-rez-spectrum]] ·
[[accord-the-742hz-mode-is-stocks-and-our-q-is-lower]]

## 🛑🛑 THE BIQUAD CANDIDATE IS **REFUTED** — by a natural experiment in the existing corpus
The biquad is armed from **V103** onward (`0xC649B` 0→1 **plus** two code edits, both verified from the
images: `0x35A08` `e798`→`fb97`, which **repoints the gate's input from `gp-0x671a` to `gp-0x6806`**,
and `0x35A12` `ec`→`e0`, `cmp r12,r9`→`cmp r0,r9`). **V88 and everything before it has `0xC649B` = 0
and stock code there.** That splits the corpus into a clean before/after.
```
   7-9 Hz Re(Z)     biquad OFF (9 routes)              biquad ON (8 routes)
   values           -13 -36 -38 -50 -74 -64 -38 -42 -32   -63 -57 -54 -50 -34 -57 -50 -75
   median                    -37.7                              -55.4
   P(ON more anti-damped than OFF) = 0.722   (chance = 0.5)
```
🛑 **The feature is already at −32 to −50 on V90/V91/V92/V96 — builds with NO biquad.** 0.722 with
n = 9/8 and heavily overlapping ranges is not separable. **The biquad does not create it.**

## 🛑 AND THE "LINEAR IN GAIN" LAW I NEARLY RECORDED IS **NOT SUPPORTED**
The medians looked beautifully linear — stock 1× −13.1, 4× −37.7, 6× −56.8, 8× −73.9, i.e.
`Re(Z) ≈ −13 − 8.7·(gain−1)` — and `Re(Z)` being a **ratio** (torque÷rate, in which excitation
cancels) would have made that a **loop-gain** signature, overturning the kit's standing *"the gain
scales EXCITATION, not loop gain"*. **It does not hold:**
```
   gain 4x  n=6  median -37.7  spread 18.2
   gain 6x  n=9  median -56.8  spread 41.2
   between-gain step (4x -> 6x) = 19.1   |   within-gain spread at 6x = 41.2  (2.2x larger)
```
⇒ **route-to-route variation swamps the gain step. Do not claim a gain law**, and the kit's
excitation-not-loop-gain position is **not** overturned by this data.

## ✅ WHAT SURVIVES, AND IT IS ROBUST
**STOCK −13.1 lies OUTSIDE the entire modified range (−31.9 … −74.8), across 16 modified routes
spanning V90→V112 and 4×/6×/8×.** Every single build we have made is more anti-damped at 7–9 Hz
than Honda. **That the excess is OURS is solid; WHICH edit causes it is still unknown**, and the two
best-shaped candidates (the biquad; the gain) are now both eliminated.
