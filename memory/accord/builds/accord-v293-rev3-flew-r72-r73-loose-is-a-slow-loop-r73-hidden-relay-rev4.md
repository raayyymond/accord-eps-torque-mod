---
name: accord-v293-rev3-flew-r72-r73-loose-is-a-slow-loop-r73-hidden-relay-rev4
description: V293 rev 3 FLEW 2026-09-14 on routes 72+73 — "loose" at speed is the LOOP (Ki 0.6/LAF 14, ~1.4 s) failing to absorb a hold feedforward that is wrong by 20–70 % from road to road; route 73 secretly ran SteerFriction 0.212 (the fork back-filled an explicit 0.0 with stock) = a 10×-Kp relay that tracked 2.5× better and chattered at 4 Hz; REV 4 = speed-scheduled Ki (0.6 → 2.5 by 18 m/s), relay off under the hysteresis FF, stock-sync fix, 28 m/s knot ×1.2
metadata:
  type: project
---

**Flew (2026-09-14 afternoon):** fork `Dom e8e62f0e1` + rev-3 config, routes `75604b0a432fdc89_00000072--8001fc3048` (627 s
engaged) and `_00000073--79fd149dd8` (599 s). Operator: *"better than rev 2; still a little loose; still jerky on hard turns;
not as good as the 1 kHz inner loop."* He turned live delay learning ON himself (`UseAutoSteerDelay 1`, liveDelay 0.274 s).

**EVIDENCE (kit `v293r3_read.py`, `v293r3_ffneed.py`, `v293r3_holdlevel.py`):**
- Route 72 (rev 3 exactly): planner-tracking gain **0.80 / 0.74** at 15–22 / >22 m/s, lag **0.46 / 0.52 s**, |H|(0.2 Hz)
  0.66 / 0.76, 79–83 % of the error below 0.3 Hz; the feedforward supplied 68–76 % of the low-frequency torque, P+I the rest
  in the SAME direction → the map under-delivers and the I loop (time constant ~1.4 s) is too slow. Route 71 (rev 2 linear
  tables) had f/u 1.23 at >22 (over-delivery, gain 1.12).
- The hold map's level error is ROUTE-DEPENDENT: total torque vs map(angle) ×1.10–1.25 on routes 70/71 (its own fitting
  routes), ×1.57–1.71 on route 72, ×1.29–2.07 on 73 with left 3.0 vs right 0.9. A static map cannot be right to ±30–70 % at
  small angles at speed; the integrator has to do it.
- **Route 73 ran `SteerFriction = 0.2120497` (stock).** `_sync_stock_param` treated an explicit 0.0 as UNSET and back-filled
  it at a restart. Relay rms 0.095 torque, 239 flips/min, small-signal gain 9.9 vs Kp 0.85 → tracking rms 0.043–0.054 (r72:
  0.107–0.138) but a 3.8–4.7 Hz rate line +5.6…+9.6 dB, 66 reversals/min and 21 % of hard-turn frames at the Honda rate cap
  = "jerky on hard turns". The device still held 0.212 when the session began.
- Rev 3 did what it was for: no 2.34 Hz cycle, no 2 Hz line on straights, low-speed hard-turn rate rms 47 (rev 2 60, rev 1 86).
  Unchanged: low-speed bursts 81/min (stiction + delayed P).

**Rev 4 shipped** (fork `f4e314da6` + `08a5a7064`, `toggle-config_V293_torque_mode_r4.json`, device pulled/rebuilt/params
written/rebooted, tests pass on the comma 72 + 193/195): `AccordTorqueKiHigh 2.5` (schedule 0.6 below 8 m/s → 2.5 from 18;
Ki 2.5 at 5 m/s would ring the 1 Hz mode 16–36° pk-pk because the lsf already ×7), relay gated off under
`AccordFrictionHyst > 0`, stock-sync fix, `HOLD_K_V[28]` 0.0134 → 0.0160. Simulated: 2 s residual of a 0.03-torque bias at
19–26 m/s 0.11–0.12 → 0.005–0.013 m/s², Ms 1.75 unchanged. Rejected: Kp 1.1/1.6, Ki 2.5 flat, ref 0.08, map ×1.3, hyst 0.020.

**Why:** the goal metric is planner desire vs actual; rev 3's low-frequency loop gain was the limiter, not the map's shape.
**How to apply:** score the next drive with `v293_flight_read.py … --config …_r4.decoded.json` (commit gate wants 08a5a7064 or
f4e314da6) and `v293r3_read.py <tag> r72_v293r3`; **check `SteerFriction 0.0` in initData first**. The residual after rev 4
(the first 0.5 s after a disturbance, delay-limited) is the 1 kHz EPS loop's territory — a firmware damper/inner loop with
V293's map as FF is the next lever if he still says "not confident". Page: https://claude.ai/artifact/MS72a2oMecgGmj4x2yqsGg.
Related: [[accord-v293-rev2-flew-route71-2hz-limit-cycle-hold-map-wrong-twice]], [[feedback-fork-side-experiments-are-toggle-configs-not-code]].
