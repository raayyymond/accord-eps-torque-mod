# DRIVE CARD — V188, the notch on the grind

**File:** `39990-TVA,A160-V188-V185BASE-NOTCH.ON.THE.GRIND-0x13000-0x100000.rwd`
**Image SHA256** `81c0845fdf22c3af8a164c56240acfd3be2467705997f2f299b29fe560be3279`
🛑 Nothing is flashed until you name the file and the bus and I read them back to you.

## What it changes
Four float32 cells. Honda's notch moves from **55.226 Hz** onto the **grind at 19.40 Hz**.
Everything else is V185; every carried lever is asserted.

| f | effect |
|---|---|
| DC | **unchanged (1.000002)** — assist you feel is identical |
| 1 Hz | **−1.25°** — LKAS band essentially untouched |
| 3 Hz | **−3.84°** — a third of V187's cost |
| 8.8 Hz | −1.2 dB — helps the ratchet slightly too |
| 15–23 Hz | **−6.2 to −15.3 dB** — the grind |
| 55.2 Hz | **+98 dB — Honda's null is given up** |

## Why this and not V187
One biquad = one notch. The grind is a **closed-loop instability** (9,200× less power with LKAS
off), so a notch in the loop at that frequency is a **cure**. The ratchet is a **plant resonance**,
where a notch only reduces excitation — and the ratchet already has its own lever on this build
(the engaged inertia revert). A middle notch was tested and is **worse than both**.

## The drive — two passes, ~30 s
1. **1a — 15 s engaged creep, 1–24 km/h, driven HOW YOU NORMALLY DO.** Scoreable today.
   **1b — the same again HANDS ON.** Baseline-building; thresholds UNKNOWN.
   Don't break either pass up — the analysis window is 5.12 s.
2. `python rlog-tools/score/score_band_excess.py <route-tag>`

## 🛑 Pre-registered
```
   grind ABSOLUTE power falls ~10-14x and the 15-25 excess drops   => THE GRIND IS GONE
   grind peak MOVES to ~24-28 Hz                                   => notch displaced it, re-centre
   grind unchanged                                                 => the assist section is not the path
   the ratchet should improve only slightly (~1.3x) -- it is NOT what this build targets
```
🛑 **Read the ABSOLUTE column, not the control-band ratio** — the ratio divides by 30–40 Hz,
which this notch also attenuates.

## ⚠ Stop conditions
- **A new high note or whine** ⇒ the 55 Hz null we gave up. Stop; reflashing V185 restores it.
- Grinding that feels **higher in pitch** ⇒ the notch displaced it rather than removing it.
  That is a real result, not a failure.
