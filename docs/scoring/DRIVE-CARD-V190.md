# 🛑 NOT RECOMMENDED — THE SIGN WAS VERIFIED AND IT WENT THE OTHER WAY

**Do not fly this build to fix the ratchet. Fly V189 instead.**

`FUN_0003a382` was decompiled after this card was written. The chain is now proven:
`gp-0x6bc2 ~ -a` → `gp-0x6ad6` ↓ → `error = measured - reference` ↑ → `gp-0x6ad4 = -K*error`
↓ → the aggregator sum **OPPOSES acceleration** = **positive damping, stabilising**.
Disabling it would most likely make the ratchet **WORSE** — the inverted-sign outcome this
card itself pre-registered. Honda ships the flag enabled, which agrees.

The artifact is kept: it remains a legitimate **deliberate probe** of this term if V189
leaves ratchet behind — but it is a probe expected to worsen it, not a fix.

---

# DRIVE CARD — V190, the untouched acceleration feedback

**File:** `39990-TVA,A160-V190-V189BASE-ACCEL-REFERENCE-TERM-OFF-0x13000-0x100000.rwd`
**Image SHA256** `ab75a383fad5c65ad03645daffa8d3a93d15916040b438d3a01275e82196744f`
🛑 Nothing is flashed until you name the file and the bus and I read them back to you.

## What it is
**V189 plus one byte.** `0xC64AE` 1→0 disables a second acceleration feedback that runs into the
torque-tracking reference — a path **never touched in the whole arc since V38**.

| | |
|---|---|
| scaling | **ω²** — 66× stronger at 8.2 Hz than 1 Hz |
| speed weighting | **64 at 1 km/h → 41 at 24 → 32 above 40** — peaks at creep |
| DC / LKAS authority | **zero effect** — acceleration is 0 in steady state |
| carried from V189 | grind notch at 19.40 Hz, inertia revert, FactorC m27 stock |

## The drive — two passes, ~30 s
1. **1a — 15 s engaged creep, 1–24 km/h, driven HOW YOU NORMALLY DO.** Scoreable today.
   **1b — the same again HANDS ON.** Baseline-building; thresholds UNKNOWN.
2. `python rlog-tools/score/score_band_excess.py <route-tag>`

## 🛑 Pre-registered — including the way this can BACKFIRE
```
   ratchet excess falls toward the manual floor 2.8x (null ~3.9)   => RATCHET GONE
   grind absolute falls ~10-14x                                    => the notch worked
   ** ratchet gets WORSE **                                        => the sign was inverted; the
                                                                      term was DAMPING.  Revert to
                                                                      V189, one byte.  This is a
                                                                      real possibility, not a
                                                                      formality -- the sign is
                                                                      BELIEF, not EVIDENCE.
```
🛑 **Read the ABSOLUTE column, not the control-band ratio.**

## ⚠ Stop conditions
- **Ratcheting noticeably worse** ⇒ stop, that is the inverted-sign outcome. Reflash V189.
- **A new high note or whine WHILE ENGAGED** ⇒ the 55 Hz null. Manual driving is stock.
