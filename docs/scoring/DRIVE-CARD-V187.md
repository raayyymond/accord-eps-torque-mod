# DRIVE CARD — V187, the notch on the ratchet

**File:** `39990-TVA,A160-V187-V185BASE-NOTCH.MINIMAX.OVER.ROUTES-0x13000-0x100000.rwd`
**Image SHA256** `105238993346f0e7e792e418c808d6ddf3f42504fb8bf2705c1eb7e0cad045ab`
🛑 Nothing is flashed until you name the file and the bus and I read them back to you.

## What it changes
Four float32 cells. Honda's notch is moved from **55.226 Hz** onto the **ratchet at 8.80 Hz**.
Nothing else moves; every V185 lever is carried and asserted.

| f | what it does |
|---|---|
| DC | **unchanged (0.999972)** — assist level you feel is identical |
| 1 Hz | −0.4 dB, **−2.97°** — LKAS band essentially untouched |
| 3 Hz | **−9.95°** — vs V184's −40.5° |
| 8.0–8.6 Hz | **−11.4 to −23.2 dB** — the ratchet |
| 55.2 Hz | **+97 dB — Honda's null is given up** |

## The drive — same two passes, ~30 s
1. **1a — 15 s engaged creep, 1–24 km/h, driven HOW YOU NORMALLY DO.** Scoreable today.
   **1b — the same again HANDS ON.** Baseline-building; its thresholds are UNKNOWN.
   Don't break either pass up — the analysis window is 5.12 s.
2. `python rlog-tools/score/score_band_excess.py <route-tag>`

## 🛑 Pre-registered, so it cannot be read after the fact
```
   peak stays ~8 Hz and ratchet excess FALLS  => THE RATCHET IS GONE
   peak MOVES DOWN to ~6.5-7.5 Hz             => the notch DISPLACED it, re-centre or widen
   peak and excess both unchanged             => the assist section is not the path
```
Expect **ratchet absolute power to fall ~4–6x**. Unlike a low-pass, a notch removes a *peak*, so
the excess endpoint **can** see it.

## ⚠ Stop conditions
- **A new high-pitched note or whine** ⇒ that is the 55 Hz null we gave up. Stop and say so;
  reflashing V185 restores it. This is cal-only — caves are the bricking class, not this.
- Ratcheting that feels **lower in pitch** than before ⇒ the notch displaced it rather than
  removing it. That is a real result, not a failure — it tells us to re-centre.
