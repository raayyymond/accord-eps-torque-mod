---
name: accord-lanechange-ring-is-the-outer-loop-the-map-never-touches-the-eps-rate-feedback-gain
description: 2026-09-02, routes r32/r33 (TAP-ATTRIBUTED to V280 rev 2 -- the lane pushes at 143-155 deg/s where rev 3 brakes above 44.5; operator confirmation pending). The highway lane-change oscillation (7.0-7.8 Hz, 5-15 deg/s, >= 17.7 m/s, 6 of 6 hands-light lane changes, absent on V112/stock) is the OUTER loop (openpilot <-> EPS): the 0xE4 command carries the line at coherence 1.00, nothing in the EPS is railed, openpilot's block/tune/commit are identical across routes. From the decompile: Kp/Kd are indexed by the cmd-derived idx (same register as the map), so the map multiplies cmd->rate ONLY and leaves the EPS rate-feedback gain at exactly 1.00x V112; the inner loop measured from the tap crosses at 13-15 Hz with ~50 deg PM on the highway. In the lane-change regime (idx 2-12, first map segment) rev 3 and V280 are within 8 % (slopes 4.0 vs 4.33 vs V112 2.0); outer |L| at 2 Hz, 24 m/s ~1.0-1.1 vs V112 0.5, scales with v^2. V268's damper flatten is a NO-OP below 85 deg/s (Honda's curve already flat there). Strong-turn ripple on V280 = the servo hunting AT its reference with P linear (stalled class gone, 0 of 7). Discriminator, no build: lower SteerFriction (72 % of K_op) / SteerKP and re-drive lane changes at 25-30 m/s.
metadata:
  type: reference
---

# The lane-change ring is the OUTER loop; the map never touches the EPS rate-feedback gain -- 2026-09-02

Studies: `rlog-tools/studies/osc-highangle/{LANECHANGE-V278R3-2026-09-02.md, HIGHANGLE-r32-r33-2026-09-02.md}`,
`analysis-2020accord/studies/v280/{LOWCMD-LOOPGAIN-V112-V278-V280-2026-09-02.md (A1-A6 = plant + margins),
V268-DAMPER-DELTA-AT-HIGHWAY-2026-09-02.md}`. Handoff `docs/handoffs/2026-09/HANDOFF-2026-09-02-two-loops.md`.

| claim | status | method |
|---|---|---|
| r32/r33 were driven on V280 rev 2, not rev 3 | EVIDENCE (orchestrator re-checked) | hands-light idx>=200 rate p90 143-155 deg/s with the lane PUSHING 64-69 % above 60 deg/s; rev 3 brakes above 44.5 (r31 0.63-0.83). Chain mirror: line corr 0.89-0.92, x2 0.28-0.46 |
| the map multiplies cmd->rate only; EPS rate-feedback gain 1.00x in V112/rev 3/V280 | EVIDENCE | idx = f(cmd, taper, speed) stored at 0x29D14; Kp LERP (0xCB994[sel]) and Kd LERP (0xCB7D4) walk the SAME register; E = 32*sp - fb, dE/dfb = -1 |
| lane-change ring is openpilot <-> EPS | EVIDENCE for the wire, BELIEF by elimination for the loop | cmd coherence 1.00 with rate at f0, cmd rings at 25-40 % of the excursion; P-rail/fb-clamp/sat 0.000; openpilot H1 cmd/angle 635-875 counts/deg on every route incl. V112/stock, same tune (friction 0.212, LAF 1.689), same commit |
| inner EPS loop well damped on the highway | EVIDENCE (coh 0.7-0.9) | plant G from the tap: 21/35/41/53 e-3 deg/s per count at 2/4/6/8 Hz, ~0 phase (stiff, below resonance); L_in crossover 13-15 Hz, PM ~50 deg, no -180 below 15 Hz |
| outer loop at 24 m/s: V112 0.51 / rev 3 1.02 / V280 1.10 at 2 Hz | BELIEF (kinematic vehicle; a 1.2 Hz yaw mode makes rev 3/V280 GM 0.6x) | K_op = 4096*[(0.6+0.15/s)/2.196 + 0.212/0.3]; v^2 scaling; unity at 2 Hz near 34 / 24 / 23 m/s |
| V268's base-assist edit is inert here | EVIDENCE (bytes re-read by the orchestrator) | all four speed records of the rate-lane damper: Y[0]==Y[1] over 0-400 ct (85 deg/s) in V112 already; V268 only flattens knots above |
| strong-turn ripple on V280 = at-reference hunting | EVIDENCE (open-loop chain) | 7 F7 episodes, wheel at 0.6-1.2x reference, P linear 62-79 %, no clamp/cliff; stalled class 0 of 7 (r31 7 of 10); a 14 s stall with P railed rippled 0.02 |

**Two loops, two levers.** The strong-turn ripple is the EPS inner loop at its crossover (levers: Kp table at idx 68-136, D as
lead -- both need a drive). The lane-change ring is the outer loop's magnitude (levers: openpilot friction/kp, or the map's
X 0-12 segment). V280 neither fixes nor much worsens the lane change vs rev 3 (8 %). **No highway data exists on rev 3.**

Related: [[accord-v278r3-high-angle-stutter-is-p-desaturating-on-a-stalled-wheel]], [[accord-v276-mechanism-is-a-matter-of-degree]],
[[accord-starpilot-torque-controller-the-033-multiplier-was-inert]], [[feedback-attribute-the-build-from-the-tap-not-from-the-label]].
