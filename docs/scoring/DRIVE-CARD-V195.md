# DRIVE CARD — V195, the notch re-fitted on steering rate

**File:** `39990-TVA,A160-V195-V189BASE-NOTCH.REFIT.ON.RATE-0x13000-0x100000.rwd`
**Image SHA256** `a3ea8683df48c6b3f40e8ba8ac879047da6aec62fedc8d56cf9f1dc83f7b610b`
🛑 Nothing is flashed until you name the file and the bus and I read them back to you.

## What it is
**V189 with a better-aimed notch.** The grind was measured in the driver-torque channel when it
actually lives in the steering-RATE channel; re-fitting there removes **1.43× more grind power**
for 0.8° more phase.

| | |
|---|---|
| notch | 19.40 Hz r 0.9300 → **19.75 Hz r 0.9000** (wider) |
| grind removed (open-loop score) | 15.0× → **21.5×** median — ⚠ **the honest CLOSED-loop prediction is ~7.7×, ceiling 11.3×**; the ranking still holds |
| DC assist | **unchanged** (1.000003) |
| phase @1 Hz / @3 Hz | **−0.27° / −0.77°** vs V189 |
| manual driving | **bit-for-bit stock** — the section is engagement-gated |
| carried | inertia revert · K1 → Honda · accel alpha → Honda · w[3] halved · FactorC m27 stock |

## The drive — two passes, ~30 s
1. **1a — 15 s engaged creep, 1–24 km/h, driven HOW YOU NORMALLY DO.** Scoreable today.
   **1b — the same again HANDS ON.** Baseline-building; thresholds UNKNOWN.
2. `python rlog-tools/score/score_band_excess.py <route-tag>`
3. `python rlog-tools/score/cross_channel_band_excess.py`   — the grind should fall most in `cs_rate`

## 🛑 Pre-registered
```
   cs_rate grind excess 7.3x -> below the ~3.9 null      => THE GRIND IS GONE
   grind falls in cs_tq but NOT in cs_rate               => the notch is acting somewhere other
                                                            than where I think it is
   grind peak MOVES to ~24-28 Hz                         => the notch displaced it; re-centre
   ratchet largely unchanged                             => expected; the notch is not aimed at it.
                                                            The ratchet rests on the inertia and K1
                                                            reverts, which V195 carries.
```
🛑 **Read the ABSOLUTE column, not the control-band ratio.**

## ⚠ Stop conditions
- **A new high note or whine WHILE ENGAGED** ⇒ the 55 Hz null. Manual driving is stock.
- Grinding **higher in pitch** ⇒ the notch displaced it rather than removing it. A real result.
