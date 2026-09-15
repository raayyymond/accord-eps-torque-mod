---
name: accord-v293-rev4-flew-r75-rev5-disturbance-observer-shipped
description: V293 REV 4 FLEW 2026-09-14 (route 75 --6c8687d5bd): Ki schedule fixed the gain at speed (0.74-0.80 -> 0.97-0.98) but 20-30 % error remains, 50-70 % below 0.3 Hz, integrator carries a third; hard-turn jerk = the lightly damped 2-2.7 Hz closed-loop wheel mode; REV 5 SHIPPED + DEPLOYED (Dom e44b6cd31 + toggle-config r5): disturbance observer AccordDobHz 0.6 on the feedforward, Ki 0.3 flat, Kp 1.0, Kv 1e-3, rate filter 0.01 s, observer on the wire; predictor rejected as divergent; SteerFriction flipped to 0.212 again at an onroad boot (mechanism open)
metadata:
  type: project
---

**V293 rev 4 flew on route `75604b0a432fdc89_00000075--6c8687d5bd` (2026-09-14 22:43, 803 s engaged, `Dom 08a5a706`, Kp 0.85 / LAF 14 on the
wire).** Rev 3 → rev 4 tracking gain at 15–22 / >22 m/s **0.80/0.74 → 0.98/0.97**; still rms error 0.19–0.30 of the signal, **49–69 % below 0.3 Hz,
17–34 % in 0.3–1 Hz**, integrator share 0.29–0.33. Operator: loose, jerky on hard turns, not confident, "command has to overshoot to get over
friction". **Jerk = the lightly damped 2–2.7 Hz closed-loop wheel mode** (v<10: rate bursts every 0.53 s, command +6.9 dB at 1.95 Hz; 10–20 m/s:
des→act |H| 2.28 at 2 Hz, coh 0.99). Free-fit plant b **0.0005–0.0009 torque/(deg/s) below 15 m/s on both drives** (mode world), ~0.004 only >22;
the 09-13 ident's b is BELIEF below 20. **A 100 Hz loop cannot linearise friction because of the ~60 ms round trip, not the rate**: static stiffness
1 + Kp_t/k = 1.7; a rate damper damps below ≈2.8 Hz (RC 0.03) and pumps 3–5 Hz.

**REV 5 (fork `e44b6cd31`, `toggle-config_V293_torque_mode_r5.json`, deployed + rebooted 2026-09-15 00:38):** `HondaAccordDisturbanceObserver`
w = hold(θ)+b(v)θ'+Jθ''−u(t−0.06), two poles at `AccordDobHz` 0.6, clip 0.3, fade 3→6 m/s, held while safety-limited/pressed, ADDED to the FF;
model b = the fork's 1/G(v) ON PURPOSE (wrong-high installs damping below the corner; wrong-low strips the hold — sim hold error 0.5–0.8);
Ki 0.3 flat (`AccordTorqueKiHigh 0`), Kp 1.0, Kv 1e-3, `HONDA_ACCORD_RATE_LOOP_RC` 0.01. Sim: planner-step overshoot 0.51→0.20, disturbance
|e|@1 s 0.074→0.029, hard-turn hold error 0.219→0.086; cost +9..+22 % 1.6–3 Hz rate energy in the lightly damped world. Wire:
`starpilotLateralState.accordObserverTorque/.accordObserverFrozen` (@8/@9). **REJECTED: a model-PREDICTED rate damper — DIVERGENT at 26 m/s under
b mismatch (T3 179–462°) and biased in stiction; Kp 1.2/DOB 0.8 (rang with delays ×1.5); notch ×1.35 (unstable); dither (7 Hz ripple).**

**Why:** the operator wants desired = actual lat accel without variable delay (Ki); the observer is the fastest delay-free structure the round trip allows.
**How to apply:** next drive → `v293_flight_read.py <tag> --config …_r5.decoded.json` then `v293r5_observer_read.py <tag> r75_v293r4` (O1–O5);
if O2/O3 pass and O4 (jerk) fails → `AccordDobHz 0.4` / `SteerKP 0.85` by CONFIG; revert `_r5_REVERT_to_r4`. **Canary:** `SteerFriction` read 0.212
on route 75 after 0.0 on route 74 (both post-fix) — rewritten ~30 s into an ONROAD boot (boot-time mtimes on this device read 2026-07-28 08:05 =
the unsynced clock); an offroad reboot did NOT back-fill; no writer found by trace — check initData first. Wrong-route lesson: `00000075` exists
twice on connect (counter reset 2026-09-13); take routes from the device's realdata. See [[accord-v293-rev3-flew-r72-r73-loose-is-slow-loop-r73-hidden-relay-rev4-shipped]].
