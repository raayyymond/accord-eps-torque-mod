# DRIVE CARD — V189, the grind notch + the relay removed

**File:** `39990-TVA,A160-V189-V188BASE-FACTORC.M27.RELAY.REMOVED-0x13000-0x100000.rwd`
**Image SHA256** `71a7032a485ec8253cd46c2532adcf0331382b5b8c374fb204b9fc9d07e9240b`
🛑 Nothing is flashed until you name the file and the bus and I read them back to you.

## What it is
**V188 plus a two-byte revert.** V188 moved Honda's notch onto the grind at 19.40 Hz; V189 also
removes an engaged-only damper **relay** that our own build chain created by accident and that the
build you are driving today does **not** have.

| | |
|---|---|
| DC assist | **unchanged** |
| 1 Hz / 3 Hz phase | **−1.25° / −3.84°** |
| 15–23 Hz (the grind) | **−6.2 to −15.3 dB** |
| 8.8 Hz (the ratchet) | −1.2 dB |
| FactorC m27 `Y[0]` | **426 → 0**, back to Honda — removes the relay |
| 55.2 Hz | **+98 dB — Honda's null is given up** |

## The drive — two passes, ~30 s
1. **1a — 15 s engaged creep, 1–24 km/h, driven HOW YOU NORMALLY DO.** Scoreable today.
   **1b — the same again HANDS ON.** Baseline-building; thresholds UNKNOWN.
   Don't break either pass up — the analysis window is 5.12 s.
2. `python rlog-tools/score/score_band_excess.py <route-tag>`

## 🛑 Pre-registered
```
   grind ABSOLUTE falls ~10-14x and the 15-25 excess drops  => THE GRIND IS GONE
   grind peak MOVES to ~24-28 Hz                            => the notch displaced it
   a NEW peak appears at 13-16 Hz                           => the notch's low-shoulder lag grew a
                                                               mode; back the pole radius off
   ratchet improves only slightly (~1.3x) unless mode 27 was live, in which case removing the
   relay may do considerably more -- that is the part we cannot predict
```
🛑 **Read the ABSOLUTE column, not the control-band ratio.**

## ⚠ Stop conditions
- **A new high note or whine** ⇒ the 55 Hz null we gave up. Stop; reflashing V185 restores it.
- Grinding **higher in pitch** ⇒ the notch displaced it rather than removing it. A real result.
