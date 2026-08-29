# DRIVE CARD — V194, V193 plus the instrument that settles it

**File:** `39990-TVA,A160-V194-V193BASE-PROBE-THE-DETECTOR-INPUT-0x13000-0x100000.rwd`
**Image SHA256** `2adde4ec37be9150b3d501bcd61b7d11a33e49e839c944622474c1d368db0f10`
🛑 Nothing is flashed until you name the file and the bus and I read them back to you.

## What it is
**Everything in V193, plus a repointed CAN probe.** The 427 channel now carries **`gp-0x6c2c`, the
oscillation detector's own input** — the number that decides whether the whole detector route
(V191, V192, V193) can act at all.

| | |
|---|---|
| probe source | `gp-0x6ac0` → **`gp-0x6c2c`** |
| pack shift | sar 4 → **sar 6** (the source is signed; this makes the 10-bit field carry the sign) |
| decode | `x = (raw < 512 ? raw : raw - 1024) * 64` |
| the threshold | **T = 12800 reads as raw 200** |
| carried | grind notch · inertia revert · 2nd accel off · osc fallback 0 · osc slew tightened · dwell 100 |

⚠ Same caveat as V193: this is the first chain that can change normal driving, because the dwell
widening makes the detector state reachable. **V192** is the conservative alternative.

## The drive — two passes, ~30 s
1. **1a — 15 s engaged creep, 1–24 km/h, driven HOW YOU NORMALLY DO.** Scoreable today.
   **1b — the same again HANDS ON.**
2. `python rlog-tools/score/score_band_excess.py <route-tag>`
3. `python rlog-tools/probe/decode_v194_detector_input.py <route-tag>`

## 🛑 Pre-registered — step 3 decides the next build on its own
```
   |x| peaks well past 12800  => amplitude fine; the detector route is LIVE, V193's fix is operative
   peaks below 12800          => T IS THE BLOCKER; V191/V192/V193 all inert; next build lowers T
   peaks near 12800           => marginal; T needs a modest reduction
```
