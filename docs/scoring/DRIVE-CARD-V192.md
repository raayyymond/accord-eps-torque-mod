# DRIVE CARD — V192, close the gap in Honda's own oscillation response

**File:** `39990-TVA,A160-V192-V191BASE-OSC-SLEW-CURVE-TIGHTENED-0x13000-0x100000.rwd`
**Image SHA256** `c36b6ca12e27633f6a52a9a0d8c32feab71e08606fb253d4ef96cf3a17d5cdc1`
🛑 Nothing is flashed until you name the file and the bus and I read them back to you.

## What it is
**V191 plus four halfwords.** Honda already tightens the steering slew limit when its own
oscillation detector fires — but **only at higher index; at the low end its "oscillating" curve is
identical to the normal one.** V192 scales that oscillating curve by Honda's own 0.60 ratio, so the
tightening applies everywhere.

| | |
|---|---|
| when the detector is quiet | **the curve is never read — nothing changes at all** |
| when it fires | slew limit `[358, 307, 307, 307]` → **`[215, 184, 184, 184]`** |
| direction | **set by Honda's own two curves**, not by a sign assumption |
| carried | grind notch 19.40 Hz · inertia revert · 2nd accel term off · osc fallback zeroed |

## The drive — two passes, ~30 s
1. **1a — 15 s engaged creep, 1–24 km/h, driven HOW YOU NORMALLY DO.** Scoreable today.
   **1b — the same again HANDS ON.** Baseline-building; thresholds UNKNOWN.
2. `python rlog-tools/score/score_band_excess.py <route-tag>`

## 🛑 Pre-registered
```
   ratchet excess falls toward the manual floor 2.8x (null ~3.9)  => RATCHET GONE
   ratchet EPISODES get shorter                                   => the detector response is now
                                                                     biting; tighten further
   a brief HESITATION replaces the ratchet                        => the slew limit is too tight
                                                                     during events; back off to
                                                                     ~0.8 instead of 0.60
   nothing changes                                                => the counter never saturates on
                                                                     your drives; the detector is
                                                                     not reached and this whole
                                                                     branch is moot
   grind absolute falls ~10-14x                                   => the notch worked
```
🛑 **Read the ABSOLUTE column, not the control-band ratio.**

## ⚠ Stop conditions
- **Ratcheting noticeably worse** ⇒ revert to V189 (that is the V190/V191 sign risk, not this edit).
- **A new high note or whine WHILE ENGAGED** ⇒ the 55 Hz null. Manual driving is stock.
