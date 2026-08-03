---
name: accord-highway-trichannel-coincidence-is-dose-independent
description: A real tri-channel coincidence DOES exist at highway — chassis on 4/4 routes, sound on 2/4 — but it is dose-independent and is the already-characterised manoeuvre-loading tail; it does NOT revive the rate lane
metadata:
  type: reference
---

⚠ **SOMEONE WILL BE TEMPTED BY THIS. DO NOT BE.**

The joint tri-channel view **does** find something at highway that the single-channel analyses did
not emphasise. Top-decile 40–49 Hz blocks vs the rest, speed-matched, against a **circular-shift
null** (shift the selection variable against the others — destroys any real coincidence, preserves
every marginal and all within-channel autocorrelation). Null ≈ 0.8–1.2 in every cell; **bold clears**:

| route | build | Kd@hwy | IMU `ay` | IMU `gz` | sound | soundA |
|---|---|---|---|---|---|---|
| r2b | V58 | 1.00 | **1.347** | **1.435** | **1.205** | 1.089 |
| r37 | V62 | 2.00 | **1.866** | **1.608** | 1.111 | 1.142 |
| r3b | V65 | 2.00 | **1.372** | **1.348** | 1.042 | 1.074 |
| r47 | V67 | 2.44 | **1.437** | **1.405** | **1.254** | 1.141 |

**The coincidence is real** — the chassis clears its null on **4/4** routes and the microphone on
**2/4**. When the 40–49 Hz torsion-bar tail rises at highway, the body moves and (sometimes) the
cabin gets louder.

🛑 **BUT IT IS DOSE-INDEPENDENT.** `ay` reads 1.347 / 1.866 / 1.372 / 1.437 across Kd = 1.00 / 2.00 /
2.00 / 2.44 — **not monotone, and the two Kd = 2 routes straddle the stock lane**, which is itself
not the lowest. There is no dose ordering to find.

⇒ **This is the already-characterised MANOEUVRE-LOADING TAIL**
([[accord-highway-events-are-the-loading-tail]]): a ~1.5 s steering-rate transient loads the rack,
which shakes the chassis and makes noise. It is a property of the car and the driver, not of the
firmware.

🛑🛑 **IT DOES NOT REVIVE THE RATE LANE.** The r24 rate lane has now been tested at three doses by
three independent statistics — pooled level, event rate, and this tri-channel coincidence — with the
power stated, both positive controls firing, and all three returning null at highway. Adding a
fourth channel did not change the answer; it only made the null better characterised. See
[[accord-highway-event-rate-null-with-power]] and [[accord-highway-30-49hz-has-no-line]].

⇒ `analysis-2020accord/grind2_trichannel.py` §6(3) · `_grind2_trichannel.json`.
