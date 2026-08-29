# DRIVE CARD — V191, stop feeding the oscillation

**File:** `39990-TVA,A160-V191-V190BASE-OSCILLATION-FALLBACK-ZEROED-0x13000-0x100000.rwd`
**Image SHA256** `82ce1db4e73099377c61a78c1b5033b5ca3ba3368062761e8836c709b0c29f4b`
🛑 Nothing is flashed until you name the file and the bus and I read them back to you.

## What it is
**V190 plus one halfword.** Honda's firmware has its own oscillation detector (a hard-reversal
counter). When that counter saturates, the anti-damping acceleration gain switches to a fixed
−8192 — **4.2× stronger than the weak end of the curve it replaces.** V191 sets that fallback to 0,
so detecting an oscillation removes the term instead of boosting it.

| | |
|---|---|
| when the detector is quiet | **the cell is never read — nothing changes at all** |
| when it saturates | anti-damping acceleration term → 0 instead of −8192 |
| carried | grind notch 19.40 Hz · inertia revert · 2nd accel term off · FactorC m27 stock |

## The drive — two passes, ~30 s
1. **1a — 15 s engaged creep, 1–24 km/h, driven HOW YOU NORMALLY DO.** Scoreable today.
   **1b — the same again HANDS ON.** Baseline-building; thresholds UNKNOWN.
2. `python rlog-tools/score/score_band_excess.py <route-tag>`

## 🛑 Pre-registered
```
   ratchet excess falls toward the manual floor 2.8x (null ~3.9)  => RATCHET GONE
   ratchet EPISODES get shorter but not smaller                   => the sustain mechanism was
                                                                     real; the trigger is elsewhere
   ratchet gets WORSE                                             => the anti-damping sign is
                                                                     inverted. Revert to V189.
   grind absolute falls ~10-14x                                   => the notch worked
```
🛑 **Read the ABSOLUTE column, not the control-band ratio.**

## ⚠ Stop conditions
- **Ratcheting noticeably worse** ⇒ inverted sign. Reflash V189.
- **A new high note or whine WHILE ENGAGED** ⇒ the 55 Hz null. Manual driving is stock.
