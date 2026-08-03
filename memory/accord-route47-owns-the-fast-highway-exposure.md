---
name: accord-route47-owns-the-fast-highway-exposure
description: 79.8% of all corpus exposure above 28 m/s is route 47 alone, so above 28 m/s the rate-lane dose is confounded 1:1 with route
metadata:
  type: reference
---

🛑 **Above 28 m/s, DOSE IS CONFOUNDED 1:1 WITH ROUTE.** Engaged exposure above 28 m/s, whole corpus:

| route | build | Kd (highway) | seconds | share |
|---|---|---|---|---|
| `47` | V67 | 2.44× | **623.8** | **79.8 %** |
| `3b` | V65 | 2.00× | 99.8 | 12.8 % |
| `2b` | V58 | 1.00× | **39.2** | **5.0 %** |
| `37` | V62 | 2.00× | 18.5 | 2.4 % |
| `2c`, `3a`, `4a` | — | — | 0.0 | 0 % |

Total **781.2 s**. Pools: **Kd=1.00 39.2 s · Kd=2.00 118.3 s · Kd=2.44 623.8 s.**

**Consequence.** Any ">28 m/s dose effect" is also a *route* comparison with **one route per arm** for
two of the three doses — different road surface, tyres, weather and date. A split-half null computed
inside a single route cannot see any of that; it measures within-route sampling noise only. This bit
during the 2026-08-03 highway session: an IMU 41–44 Hz amplitude ratio of **1.484 [1.295, 1.617]**
(Kd 2.44/1) looked decisive until the pre-declared **33–36 Hz negative control moved with it (1.185)**,
identifying most of it as a route-level broadband offset.

**The only between-route control at constant dose** is route `37` vs `3b` (both Kd=2, control path
byte-identical): **0.958 [0.836, 1.112]** on the 41–44 Hz envelope. Useful, but **one degree of
freedom** — do not treat it as a general floor.

## Fuller exposure picture, so nobody re-derives it
Engaged seconds by speed band, 12–17 / 17–22 / 22–28 / >28 m/s:
- **Kd = 1.00** (V58 `r2b`, V59 `r2c`): 255.6 / 129.4 / 175.1 / 39.2
- **Kd = 2.00** (V62 `r37`, V65 `r3a`,`r3b`): 316.2 / 166.7 / 201.9 / 118.3
- **Kd = 2.44** (V67 `r47`, `r4a`): 123.2 / 59.4 / 195.2 / 623.8

⚠ Route `4a` is V67 but has **zero highway seconds** (max 13.92 m/s) — it adds nothing to any highway
population. Its caches carry a `probe` field the older caches lack.

⇒ **Rules to apply.** State this confound in any >28 m/s dose claim. Always run a **pre-declared
adjacent-band negative control** so a route-level broadband offset cannot pass as a band effect. The
cheapest fix is a drive: **~4 min of engaged highway above 28 m/s on a non-V67 build** closes both this
confound and the power gap in [[accord-highway-event-rate-null-with-power]].

Related: [[accord-segs2b-bug-hid-the-kd1-highway-baseline]],
[[feedback-episodes-not-windows-and-the-noise-floor]],
[[feedback-check-the-data-exists-before-concluding-it-doesnt]], [[accord-v67-flew-both-grinds-fixed]].
