---
name: accord-kp-kd-schedule-x-axis-is-demand-index-16-125736-per-lsb
description: The Kp (0xE5378) and Kd (0xE511C) LERP schedules on the LKAS rate loop share ONE X axis -- the rectified, taper-scaled, +-240-clamped openpilot 0xE4 STEER_TORQUE demand index, exactly 16.125736 wire counts per index LSB -- and 91% of engaged time (100% of highway cruise) sits inside Kp's first segment [0,68), so all four of Kp's non-zero knots sit above the p90 of engaged demand and a Y-only edit barely touches usable time; Kd's knots (0/11/22/32) straddle the busy zone instead. Record layout and a x4-is-not-a-multiply trap documented. 2026-09-09.
metadata:
  type: reference
---

# The Kp/Kd schedule X axis is the demand index, exactly 16.125736 wire counts/LSB — 2026-09-09

**The axis.** Both `0xE5378` (Kp, slot 7, n=5, `X=[0,68,112,136,208]`) and `0xE511C` (Kd, slot 7, n=4,
`X=[0,11,22,32]`) — and the assist map `0xE502C` — are indexed by the SAME quantity: `idx`, the
rectified, taper-scaled, ±240-clamped openpilot 0xE4 STEER_TORQUE demand (map uses `idx & 0xFF`, Kp uses
`idx & 0xFFFF`, Kd uses `idx & 0xFF`; the ±240 clamp makes the three ranges identical). It is an ABSOLUTE
VALUE — sign is split off before the LERP and reapplied only to the map output. It is NOT the post-map
setpoint, NOT |E|, NOT feedback, NOT speed. One selector (`gp-0x674e`, slot 7 confirmed as live, memory
`accord-the-live-variant-selector-is-7-tvca4-measured-on-the-wire`) indexes all three banks.

**Exact scale, EVIDENCE not empirical:** `1 idx LSB = 2²² / G / 4 = 4,194,304 / 65,025 / 4 = 16.125736`
wire counts of 0xE4 STEER_TORQUE, at G = 255×255 = 65025 (the taper, which is 255 on ≥97 % of engaged
frames). Confirmed twice independently (`reqaxis` then `scalecheck`, byte-identical result both times).
`idx = 240` is reached at 3870 wire counts — just past the 0xE4 field's own ±3840 saturation, so the ±240
clamp effectively never binds before the wire does. openpilot's 123-count/frame slew cap is 7.63 idx per
100 Hz frame.

🛑 **The ×4 in the 0xE4 handler is `shl 0x2` + `subr r0`, NOT a `mul`** (`FUN_00052676`:
`sxh r6; shl 0x2,r6; subr r0,r6` ⇒ `−4·raw`) — **an operand-text search for `mul` returns a false zero**
on this cell. Confirmed from `decompile_function`/`disassemble_function 0x52676`.

🛑 **Record layout trap.** The record is `n`(u16) · `X[0..n-1]`(u16) · `Y[0..n-1]`(u16) · pad, i.e.
`X[0]` at `rec+0x02`, `Y[0]` at `rec+0x02+2n`. This is NOT inferred from the byte pattern — a naive
"u32 header, then X, then Y" split also fits the same bytes and gives a **different, wrong** answer. It
was read from the instructions (`sld.hu 0x2,ep,r9` = X[0]; `add 0xc,r10` = `&Y[0]` = rec+0x0C, which bakes
in n=5). Confirm the layout from the LERP's own instructions before trusting a byte-offset guess on any
similar record.

**Where the car actually lives, pooled V289 (r62+r63), engaged, 1207 s:**

| Kp interval | share | | Kd interval | share |
|---|---|---|---|---|
| `[0, 68)` | **91.1 %** | | `[0, 11)` | **67.9 %** |
| `[68, 112)` | 3.5 % | | `[11, 22)` | 11.7 % |
| `[112, 136)` | 1.3 % | | `[22, 32)` | 4.6 % |
| `[136, 208)` | 2.5 % | | `[32, →)` (clamped) | 15.8 % |
| `[208, →)` | 1.6 % | | | |

idx percentiles engaged: p50 = 5, p90 = 58, p95 = 118, p99 = 239. Highway cruise (v≥22, |angle|<5°) is
**100 % inside Kp's `[0,68)` segment** on every route (idx p50 = 3). The capped-step operating point and
the operator's full-lock strong-turn bookmarks both sit at idx p50 74–123 — a schedule cutting gain below
idx≈30 and returning to 248 by idx≈68 would touch ~85% of engaged time and 100% of cruise while leaving
those authority-floor operating points almost untouched.

**Consequence:** all four of Kp's non-zero knots (68/112/136/208) sit **at or above the p90 of engaged
demand**. **A Y-only edit on the Kp record acts almost exclusively through Y[0]/Y[1]; Y[2..4] touches
<5% of engaged time** — a low-demand Kp gain cut is not reachable by Y alone at usable resolution, it
requires moving X[1] down (as V284 / V281 rev 2 did). **Kd's knots (0/11/22/32) straddle the busy zone**
(68/12/5/16% split) and have usable low-demand resolution as shipped — Kd has shipped flat 128 on every
flown build in the arc. The grinding episodes themselves are NOT a high-demand population (idx p50 8/46/37
on r62/r5e_v288/r63, 70–75% of episode time in `[0,68)`) — the symptom and the transient-authority
operating point sit in different parts of the axis, which is what makes the schedule a real, usable degree
of freedom.

Sources: `docs/traces/TRACE-2026-09-09-kp-kd-schedule-axis.md` (agents `reqaxis` + verification pass
`scalecheck`).

**How to apply:** any future Kp/Kd schedule edit must be checked against this idx-time distribution before
being called "low-demand" or "high-demand" — a Y-edit at a high knot is nearly inert by construction. See
[[accord-honda-kp-ki-scale-never-acted-kp-is-0600-on-all-60-routes]] (a different Kp, the Honda/openpilot
scale, not this firmware schedule) and
[[accord-the-override-taper-arm-is-selected-by-a-0xe4-field-openpilot-sends-0-the-live-post-pid-fade-is-0xcbbc4]]
(the `gp-0x6803` finding this trace independently re-confirmed).
