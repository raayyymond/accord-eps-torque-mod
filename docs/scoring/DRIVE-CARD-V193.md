# DRIVE CARD — V193, open the detector's frequency window

**File:** `39990-TVA,A160-V193-V192BASE-DETECTOR-DWELL-WIDENED-0x13000-0x100000.rwd`
**Image SHA256** `0f1a7bb6849f17824cbc9fa7e8a6aeeb40e8fe4bb548fc7310fa4e17052b7992`
🛑 Nothing is flashed until you name the file and the bus and I read them back to you.

## The finding behind it
Honda's firmware has an oscillation detector, and it **counts reversals only if the opposite peak
arrives within 50 ms** — so it can only see oscillations **above 10 Hz**. Your ratchet is
**7.3–8.6 Hz**. It falls outside the window, so the detector never fires for it, and every
detector-gated lever built so far (V191, V192) is **inert for the ratchet**.

V193 changes one byte: dwell 50 → 100 ms, so the window opens to **above 5 Hz** and the whole
ratchet band is inside it. The damping responses V191 and V192 installed can then actually act.

| | |
|---|---|
| `0xC64DD` HYST | **50 → 100** (dwell 50 ms → 100 ms) |
| window | f > 10.0 Hz → **f > 5.0 Hz** |
| `0xC620A` T | **deliberately unchanged** — amplitude is not the binding constraint |
| carried | grind notch · inertia revert · 2nd accel off · osc fallback 0 · osc slew tightened |

## ⚠ This is the first build in the chain that can change normal driving
V189–V192 are all conditional on a state that never occurs, so they cannot be felt on a calm road.
**V193 makes that state reachable.** A spurious detection tightens the steering slew limit for a
hold period and may read as brief heaviness. It still needs a large acceleration excursion
(|gp-0x6c2c| > 12800) on both sides, so it is bounded — but it is a real change.
⇒ **If you would rather not accept that, fly V192 instead** — but know that its detector-gated
levers cannot reach the ratchet.

## The drive — two passes, ~30 s
1. **1a — 15 s engaged creep, 1–24 km/h, driven HOW YOU NORMALLY DO.** Scoreable today.
   **1b — the same again HANDS ON.** Baseline-building; thresholds UNKNOWN.
2. `python rlog-tools/score/score_band_excess.py <route-tag>`

## 🛑 Pre-registered
```
   ratchet excess falls toward the manual floor 2.8x (null ~3.9)  => RATCHET GONE, and the
                                                                     detector route is the reason
   brief HEAVINESS or hesitation on a calm road                   => spurious detection; drop HYST
                                                                     to ~75 (window f > 6.7 Hz)
   nothing changes at all                                         => |gp-0x6c2c| never reaches
                                                                     T=12800; amplitude, not
                                                                     frequency, is the blocker, and
                                                                     T becomes the next lever
   grind absolute falls ~10-14x                                   => the notch worked (independent
                                                                     of all of this)
```
🛑 **Read the ABSOLUTE column, not the control-band ratio.**
