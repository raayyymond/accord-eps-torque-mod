---
name: reference-accord-demand-index-distribution-on-the-wire
description: MEASURED demand-index distribution engaged on V289 (r62+r63, 1207 s) and V288 (r5e) -- p50 = 5, p90 = 58, so 91% of engaged time and 100% of 25 m/s cruise sit in the Kp record's FIRST segment [0,68); Kd's knots 0/11/22/32 straddle the busy zone instead. The Kp schedule has no resolution where the car lives.
metadata:
  type: reference
---

Measured 2026-09-09 from the route caches (`analysis-2020accord/_scratch/cache/v280/{r62_v289,r63_v289,r5e_v288}.npz`)
by mirroring the firmware index arithmetic frame by frame — reproduces the kit's independent
`grind_incident_r35.demand_live` to **1.0000 agreement**. Script:
`rlog-tools/studies/grind/kpkd_axis_r62_r63.py`. Axis definition: [[reference-accord-kp-kd-schedule-axis-is-the-demand-index]].

## Pooled V289 (r62 + r63), 1207 s engaged

idx percentiles: p5 0 · p10 1 · p25 2 · **p50 5** · p75 15 · **p90 58** · p95 118 · p99 239.

| Kp knot interval | share | | Kd knot interval | share |
|---|---|---|---|---|
| `[0, 68)` | **91.1 %** | | `[0, 11)` | 67.9 % |
| `[68, 112)` | 3.5 % | | `[11, 22)` | 11.7 % |
| `[112, 136)` | 1.3 % | | `[22, 32)` | 4.6 % |
| `[136, 208)` | 2.5 % | | `[32, →]` (clamped) | 15.8 % |
| `[208, →]` | 1.6 % | | | |

## By regime — idx p50 (r62 / r63 / r5e_v288)

| regime | seconds | idx p50 | Kp `[0,68)` share |
|---|---|---|---|
| all engaged | 619 / 588 / 642 | 5 / 5 / 6 | 90.6 / 91.6 / 88.4 % |
| capped step (\|Δcmd\| ≥ 122) | 27 / 26 / 29 | **110 / 86 / 88** | 28 / 40 / 38 % |
| low-speed full-lock turn (2–5 m/s, \|ang\| 70–140°) | 17 / 7 / 11 | **123 / 74 / 98** | 27 / 47 / 31 % |
| 25 m/s cruise (v ≥ 22, \|ang\| < 5°) | 233 / 146 / 144 | **3 / 3 / 3** | **100 / 100 / 100 %** |
| census grinding episodes | 12.5 / 13.0 / 97.5 | **8 / 46 / 37** | 75 / 69 / 70 % |

## What follows

1. **A Y-only edit on the Kp record acts almost only through Y[0] and Y[1].** Y[2..4] touch < 5 % of engaged
   time. A low-demand gain change at usable resolution needs X[1] moved down (as V284 and V281 rev 2 did).
2. **Kd is the table with usable low-demand resolution as shipped** — its knots split engaged time
   68/12/5/16 %. It has been flat 128 on every FLOWN build in the arc.
3. **The regimes separate on the axis.** Cruise is entirely idx < 68; capped-step (the pkR transient-authority
   operating point) and the operator's full-lock bookmarks are p50 74–123. A schedule confined to idx < ~68
   therefore leaves both authority yardsticks structurally untouched.
4. ⚠ **Grinding episodes are NOT a high-demand population** (p50 8–46, 70–75 % of their time in `[0,68)`),
   and the two V289 routes disagree badly (p50 8 vs 46, n = 12 and 15). Do not lean on either alone;
   r5e_v288 (n = 46, p50 37) is the better-powered estimate of where grinding sits on the axis.
5. Census episode line frequency, independently reproduced here: r62 p50 **15.8 Hz**, r63 **16.7 Hz**,
   r5e_v288 **20.0 Hz** — the V289 downward move, seen from a different script.
