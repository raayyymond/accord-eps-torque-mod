# HANDOFF 2026-09-14 — V293 rev 2 FLEW (route 71): a 2.3 Hz limit cycle at speed, stiction rings at low speed, the hold map is wrong twice; rev 3 = measured hold map + hysteresis friction FF + 100 Hz rate loop + error notch + reference shaping (fork code + toggle config)

> **Status.** V293 is on the car, unchanged (nothing was built, flashed or sent this session — the operator said
> *"this is not a firmware iteration session"*). The operator drove the **rev-2** fork package (fork `Dom`
> `66cf4454a` + `toggle-config_V293_torque_mode_r2.json`) on route `75604b0a432fdc89_00000071--f2c9d073a3`
> (18 segments, 1,028 s, 883 s laterally engaged, 2026-09-13 evening) and scored it: *"does not feel like
> StarPilot has accurately modeled my EPS + car dynamics; loose on most straights or slight bends; on hard
> curves at low speed the wheel jerks to correct itself rather than smoothly following; on hard curves at
> high speed like low speed but worse, with more oscillation/resonance."* He asked for the route data to be
> read for symptoms and discrepancies beyond his words, and for a 100 Hz inner loop in StarPilot if necessary.
> **Delivered: fork commit `e8e62f0e1` on `Dom` (rev 3) + `toggle-config_V293_torque_mode_r3.json`.**
> **Page:** https://claude.ai/code/artifact/08d2f4e0-44b8-43a0-9fb8-128eedef58e0 (signal flow, LERPs before/after, simulated consequences, risk).
> Previous narrative: `HANDOFF-2026-09-13-v293-flew-plant-is-a-spring.md`.

---

## 1. Attribution — rev 2 ran exactly as written [EVIDENCE]

`initData.params`: `GitCommit 66cf4454a`, `AccordRatePlantFF 1`, `SteerFriction 0.011`, `SteerLatAccel 14.0`,
`SteerKP 0.85`, `AccordTorqueKi 0.3`, `AccordFFRateGain 0.5`, `KeepLearnedLatAccelOffset 0`, `SteerDelay 0.2`.
Wire reads at 100 Hz: `p/error` = **0.8500** (IQR 0.8500–0.8500, n 87,896); `−(p+i+f)/output` = **14.0000**
(n 87,013). Exposure by band: 1–8 m/s 244 s · 8–15 349 s · 15–22 183 s · >22 100 s (max 30.5). Hands-off
834 s. Driver pressed 49 s in 68 episodes (route 70: 175). Torque rail duty at 0–5 m/s **0.26 %** (route 70: 4.4 %).

Scorer v2 (`_scratch/v293_flight_read_r71_v293r2.txt`): **two REVERT triggers** — the 1–4 Hz outer-loop line
(cmd AND angle at 5–10 m/s) and the **ratchet trigger** (dwells/min at 0.25 deg/s above route 70's in two
bands: 10–20 m/s **9.12** vs 4.56, >20 **4.30** vs 1.24). Rate-magnitude concentration q75–90 **0.562** (r70
0.468, V282 0.33–0.35) while the command's stayed 0.454 — the car got snappier, the command did not.
Tracking gain **0.827 / 0.932 / 0.988 / 1.116** (<8 / 8–15 / 15–22 / >22; r70 —/0.884/1.020/1.123). Turn-hold
actual/desired at 10–20 **0.868**; by demand 0.5–0.8 **0.88**, 0.8–1.2 **0.77** (under-turning). Step overshoot
0.20 / 0.39 / 0.43 (5–10 / 10–20 / >20). Straight-line loop stiffness 0.011 / 0.0164 torque/deg (5–10 / 10–20)
— HIGHER than route 70's, so *"loose"* is not P-stiffness on straights (see §3).

## 2. What the data showed that the operator's words did not name [EVIDENCE — `v293r2_read.py`, `_scratch/v293r2_read_r71_v293r2.txt`]

**2a. A 2.34 Hz limit cycle on hard curves above 20 m/s — the "oscillation/resonance".** On the sustained
left curve at t = 630–638 s (21.8 m/s, demand −2.7 m/s²) the angle swings 16 ↔ 29° (±6°), the rate ±80 deg/s,
the command −600 ↔ −1200 counts, the error −0.5 ↔ +1.3 m/s², and the friction relay flips ±0.011 every half
cycle. Spectral prominence at 2.34 Hz: rate **+22.5 dB**, cmd **+18.1 dB**, angle **+20.5 dB**, error +23 dB.
Band-passed 0.5–3 Hz rms on >20 m/s curves: rate **27 deg/s**, angle **2.3°**, cmd **108 counts**. On
straights at the same speed: rate 1.1 deg/s. The 10–20 m/s "all" stratum carries the same line at 2.34 Hz
(+12 dB on the rate); 5–10 m/s at 1.7–2.2 Hz.

**2b. The mechanism: a lightly damped steering mode + a ~60 ms loop + the friction relay.** Fitting
`u − relay = a·θ + b·θ' + J·θ''` on hands-off data band-passed 0.1–5 Hz gives **J = 7.2e-5 … 9.1e-5
torque/(deg/s²)** in every band, **ζ = 0.18–0.38**, ω_n = 1.17 / 1.76 / 2.01 Hz at 8–15 / 15–22 / >22 m/s. At
the observed cycle the direct ratio angle/command reads 68–104 deg/torque at −150…−165° (15–22 and >22 m/s,
coherence 0.75–0.85) — the closed-loop condition P·C = −1, from which a second-order plant with the DC gain
1/a gives ω_n ≈ 1.85–1.9 Hz, ζ ≈ 0.2–0.35, J ≈ 9e-5…1e-4. Two methods, one plant. Loop delay from the
timestamps: 0x14A → carState **3 ms**, controlsState → 0xE4 **13 ms**, 0xE4 → delivered torque **30–45 ms**
(cmd→tap step correlation 30 ms, ncc 45 ms); direct xcorr command → wheel rate 85–126 ms at 0.3–4 Hz (includes
the plant's phase). Linear loop model (`v293r2_loop.py`, plant e^{−0.06s}/(k(v)+0.0006s+8e-5s²)): rev 2 with
the relay counted as its small-amplitude gain has **PM −5° to −28°, crossover 2.5–3.0 Hz at 18.9–28 m/s** — the
cycle; without the relay Ms 4–30 (marginal); the same loop in the time-domain simulation with the relay
blows up at 22.8 m/s for b ≤ 0.0004 or delays ×1.5 and is stable without it. **The `SteerFriction` relay was the
trigger; the P gain at speed was already marginal.** Route 70 (rev 1, no relay) had the same mode as a damped
+6 dB ring at 1.2–1.9 Hz — the "1–4 Hz line" the scorer flagged then.

**2c. Low-speed "jerks": stiction plus the lsf-inflated P plus the honda limiter.** Eight rate bursts of
84–442 deg/s at 2.4–9.5 m/s are traced in `v293r2_read` §S6. Pattern: the wheel sits still (rate 0) while the
command ramps 1082 → 2748 counts over 0.4 s (t = 470.3 s, 5.3 m/s, |angle| 147°, lsf-inflated error 4.0 = 63°
of angle error), breaks away at 315 deg/s, overshoots 80°, the command collapses to 613 and reverses; at
t = 965–968 s the cycle repeats three times with the command swinging −3248 → +853 in 0.5 s at the 123
counts/frame cap (6 % of frames capped at 0–5 m/s). Bursts 20.5/min in the low-speed hard-curve stratum.

**2d. The hold torque is a SATURATING spring and the linear tables are wrong in both directions.** Measured
hands-off, wheel still (|rate| < 15 deg/s, 1 Hz LPF), median torque per (|angle|, speed) cell, routes 70+71
pooled (`_scratch/r70r71_hold_map.txt`, `_scratch/r70r71_hold_joint_fit.txt`):

| v (m/s) | measured at 8° / 27° / 55° | rev-2 table at the same angles | ratio |
|---|---|---|---|
| 4–8 (6.1) | 0.059 / 0.104 / 0.197 | 0.010 / 0.031 / 0.064 | ×5.9 / ×3.4 / ×3.1 |
| 9–11 (9.6) | 0.083 / 0.178 / 0.303 | 0.030 / 0.095 / 0.224 | ×2.8 / ×1.9 / ×1.4 |
| 16–19 (17.3) | 0.099 / 0.227 (29°) / — | 0.079 / 0.311 | ×1.25 / **×0.73** |
| 25–31 (28) | 0.106 / 0.165 (12°) / — | 0.167 / 0.268 | **×0.63 / ×0.62** |

Joint fit `hold = 0.020·(1−e^{−θ/3}) + k(v)·sat(v)·tanh(θ/sat(v))`, sat(v) = 19.3 + 546·e^{−v/3.01} deg,
k = [0.0021 … 0.0134] at v = [2 … 28] (weighted rms 0.0085 torque; the 0.020 intercept is the static
friction — creeping outward vs inward the torque differs by 2 × 0.02–0.04, part of which is b·θ'). At 10 m/s the
hold saturates at ~0.30 torque above 55° (two cells at 0.303). **This is why "loose on slight bends" and the
under-turning at <15 m/s: the feedforward supplied 20–35 % of the hold on 5–35° bends, the integrator (Ki
0.30/14, time constant ~3 s) did the rest late.** It is also why >22 m/s over-turns (tables ×1.6).

**2e. Rev 2's feedforward replay against the plant's need (§S9)**: ff/need gain 0.48 / 0.81 / 0.85 at 1–8 /
8–15 / 15–22 m/s; the whole command 0.91 / 1.01 / 1.00 — the loop made up the difference. Integrator share
0.35 / 0.31 / 0.21 / 0.31 (r70 0.35–0.38): fell only at 15–22. The relay was saturated 53 % / 43 % / 15 % / 11 %
of engaged time by speed band and flipped sign 60–110 times per minute.

**2f. Nulls.** Vehicle model: gyro·v vs the controller's lateral accel slope 0.993–1.010 in every band — the
steer-ratio map is not a cause. `liveParameters.roll` +1.74° median (0.30 m/s² of feedforward; r70 +2.4°).
Learned offset effective −0.052 m/s² (toggle 0 removed the published one; the residual is the fit's own).
Reference path: setpoint vs command |H| 1.30 at 1 Hz, −150° at 2 Hz (the complementary filter + 0.3 s delay)
— not in the loop, but every fast step arrives through it.

## 3. The diagnosis, in the operator's three sentences

| his words | what the wire says | cause |
|---|---|---|
| "loose on straights or slight bends" | tracking gain 0.83/0.93 below 15 m/s, turn-hold 0.77–0.88, integrator carrying 31–35 % | the hold feedforward ×0.2–0.35 of the need at 5–35°, a 3 s integral time; on straights the disturbance recovery is the integrator's alone |
| "hard curves at low speed: jerks to correct itself" | 20 bursts/min of 84–442 deg/s with the command ramping through stiction and the honda limiter capped | stiction + the lsf-driven P (Kp_eff 5.4 at 5 m/s) + no damping; the relay is bang-bang there (δ = 0.044 m/s²) |
| "hard curves at high speed: worse, oscillation/resonance" | a 2.34 Hz, ±6° limit cycle, +20 dB, on every sustained curve above 20 m/s | the 2 Hz steering mode (J 8e-5, ζ 0.2–0.35) pumped by the ~60 ms-delayed P + the SteerFriction relay |

## 4. Rev 3 — what shipped (fork `e8e62f0e1` on `Dom`, config `toggle-config_V293_torque_mode_r3.json`)

**Fork code, five new `Accord*` params (each 0/off restores rev 2's code path; Safe Mode = all off):**

| param | default | what it does | why |
|---|---|---|---|
| `AccordHoldMap` | 1 | `get_honda_accord_hold_torque(angle, v)` — the measured saturating map replaces the linear k(v)/G(v) hold term in `get_honda_accord_rate_plant_ff` | §2d: ×3–5 too small below 10 m/s, ×0.6 too large above 20 |
| `AccordFrictionHyst` | 0.015 | a hysteresis operator on the DESIRED angle supplies ±F in the direction the wheel last had to move (3° band) — pure feedforward, no loop gain | the static friction the map was fitted without; replaces the relay, which had loop gain |
| `AccordRateLoopGain` | 0.0006 | torque = Kv·(angle_des_rate − `carState.steeringRateDeg` through a 0.03 s filter), Kv tapered by min(1, 12/v) | the 100 Hz inner loop: the electronic damper the EPS lost; brakes the low-speed snap; GM 2 at 3.5–4 Hz where the delayed loop's phase passes −180° |
| `AccordErrorNotchQ` | 1.0 | a speed-scheduled notch at `get_honda_accord_mode_hz(v)` = √(k(v)/J)/2π on the P/I error (1.0 Hz at 4.5 m/s → 2.1 Hz above 20) | keeps the delayed P from pumping the mode; linear Ms 4–30 → 1.9–2.6 at 15–28 m/s (Td 0.06), 2.6–3.5 at Td 0.09 |
| `AccordRefFilter` | 0.12 | two cascaded 0.12 s filters on the Accord setpoint (feedforward and P/I both see it; logged `desiredLateralAccel` is the shaped one) | simulated 1 m/s² step overshoot 80–110 % → 30–45 % at ~0.25 s extra lag |

**Config (delta, 20 keys):** `SteerFriction 0.011 → 0.0` (the relay off), `AccordTorqueKi 0.3 → 0.6` (5 s
disturbance deflection halves, margins unchanged), the five new keys at their defaults, and rev 2's
`SteerKP 0.85 / SteerLatAccel 14 / AccordFFRateGain 0.5 / SteerDelay 0.2 / KeepLearnedLatAccelOffset 0` plus the
pins. Revert file: `toggle-config_V293_torque_mode_r3_REVERT_to_r2.json` (the five new keys to 0/off, the rest
to rev 2). Generator `tools/make_galaxy_toggle_config.py` (now tolerates keys newer than the 2026-09-10 backup).

**Simulated on the identified plant** (`v293r2_design.py`, `_scratch/design_notch_sim.txt`; plant = the measured
hold map + J 8e-5 + b 0.0006 + Coulomb 0.015 + 0.04 s EPS delay + 0.02 s measurement delay; the fork chain
transcribed line for line, honda limiter included), rev 2 → rev 3:

| test | rev 2 | rev 3 (R3n-tap) |
|---|---|---|
| hard-curve hold + kick, tail pk-pk angle | 0.25–1.2° (unstable at 22.8 m/s if b 0.0004 or delays ×1.5: rails) | 0.05–0.37°, stable over b 0.0004–0.0008, J 6e-5–1e-4, delays ×1.5, spring ×0.7–1.4 |
| 1 m/s² step overshoot / settle | +68…+112 % / 1.4–4.4 s | +33…+48 % / 1.1–2.3 s |
| 0.05-torque disturbance, deflection at 1 s / 5 s (18.9 m/s) | 2.02° / 1.13° | 2.34° / 0.67° |
| 5 m/s 200° entry | peak +40 %, rate 514 deg/s | +26 %, 434 deg/s |

Linear check (`_scratch/design_notch_linear.txt`): Q1 notch + tapered Kv, Kp 0.85, Ki 0.6 → Ms 1.87 / 1.97 /
2.15 / 1.96 / 1.95 / 2.05 at 4.5 / 8 / 12 / 18.9 / 22.8 / 28 m/s (Td 0.06); 2.6–3.5 at Td 0.09. Raising
`SteerKP` to 1.5–2.0 fails at 22.8–28 m/s (Ms 5–18; the sim rails at 28 with delays ×1.5) — **do not raise Kp**.

**What rev 3 does NOT do.** The mode's damping ratio in the sim rises only from 0.05–0.15 to 0.1–0.25 — with a
~60 ms delay a rate loop cannot damp a 2 Hz mode much (cos(ωTd) ≈ 0.5, and it adds negative stiffness). Fast
transients will still ring the mode; the reference filter avoids exciting it. `SteerDelay` was left at 0.2:
the filter's 0.24 s group delay is not compensated in the planner look-ahead — a lever if turn-in feels late.

## 5. How to fly it (order binds)

1. Fork `e8e62f0e1` on the device (`git pull` on `Dom`), then **Rebuild Params** (Galaxy → System Tools; the five
   new keys must be in `common/params_pyx.so` or Galaxy's restore cannot write them — `known()` gates every read).
2. Restore `toggle-config_V293_torque_mode_r3.json` through Galaxy's toggle backup → Restore. Restart openpilot.
3. Attribute the first minute on the wire: `p/error` = 0.85, `−(p+i+f)/output` = 14, `GitCommit` e8e62f0e1, and
   `initData` carries the five new keys (absent = the declared defaults, which are the same values — but then
   check the commit).
4. Score with `python rlog-tools/studies/grind/v293_flight_read.py <route> --config
   analysis-2020accord/reference/toggle-config_V293_torque_mode_r3.decoded.json` (the scorer knows the new keys and
   the commit gate), then `python rlog-tools/studies/grind/v293r2_read.py <tag>` after
   `v293r2_extract.py <tag>=<route>` for the S5/S7 spectra and the S6 burst traces.

**Pre-registered falsifiers (rev 3 vs route 71):** the 2.34 Hz line on >20 m/s curves (rate +22.5 dB, rms 27
deg/s) must fall below +6 dB / 8 deg/s; low-speed bursts 20.5/min → below r70's 18/min and the 470 s-type
ramp-then-snap trace absent; tracking gain 0.83/0.93/0.99/1.12 → all within 0.95–1.05; turn-hold at 10–20
0.87 → ≥ 0.95; dwells/min at 0.25 deg/s below r70's in every band (the rev-2 ratchet trigger un-fired);
integrator share < 0.25 in every band. **Revert triggers:** a new line at 3–4 Hz (the rate loop's own phase
crossover) → `AccordRateLoopGain` 0.0003 or 0; a darty or late turn-in → `AccordRefFilter` 0.08, or `SteerDelay`
0.3; over-holding into low-speed turns → `AccordEpsSpringScale` 0.8 (it scales the map); anything else → the
REVERT file.

## 6. Files

**Fork (`raayyymond-StarPilot/StarPilot` @ `Dom` `e8e62f0e1`)**: `selfdrive/controls/lib/latcontrol_vehicle_tunes.py`
(constants, `get_honda_accord_hold_torque`, `get_honda_accord_mode_hz`, `get_honda_accord_rate_loop_gain`,
`honda_accord_friction_hysteresis`, `HondaAccordErrorNotch`, `hold_map=` on `get_honda_accord_rate_plant_ff`),
`selfdrive/controls/lib/latcontrol_torque.py` (the Accord branch), `common/params_keys.h`,
`starpilot/common/starpilot_variables.py`, `starpilot/common/safe_mode.py`,
`starpilot/common/assets/device_settings_layout.json`, both test files. ⚠ The openpilot test runtime is not
importable on this host (cereal aborts); the tune functions were executed on a stubbed mirror
(`C:/Users/dudei/.claude/jobs/ad52c287/tmp/validate_tunes.py`, all checks pass) and the controller-level test
is reasoned, not run — **run `pytest selfdrive/controls/tests/test_latcontrol.py -k accord` on the device or a
laptop build before the drive.**

**Kit reports (tracked)**: `rlog-tools/studies/grind/V293-REV2-READ-r71-2026-09-14.txt` (the §2 read), `V293-FLIGHT-READ-r71-2026-09-14.txt` (scorer v2), `V293-HOLD-MAP-2026-09-14.txt` (+ `.params.json`, the map and fits), `V293-REV3-DESIGN-SWEEP-2026-09-14.txt` (delay/second-order fit, candidate sweeps, linear margins).

**Kit**: `rlog-tools/studies/grind/v293r2_extract.py` (extractor + `cs_jerk`, `lpar_roll`), `v293r2_read.py`
(the S0–S13 read), `v293r2_simlib.py` (the transcribed fork chain on the plant; inertia, delays, hold map,
hysteresis, rate loop, notch, reference filter), `v293r2_loop.py` (linear margins), `v293r2_design.py` (the
candidate sweep), `_scratch/*` outputs (route-71 read, hold map, fits, sweeps), `v293_flight_read.py` (the five
keys' defaults + the rev-3 commit gate), `tools/make_galaxy_toggle_config.py`, the rev-3 config pair + revert
pair in `analysis-2020accord/reference/`, this handoff, `docs/STATE.md`, memory.

## 7. Open

- The mode's damping is the residual: a firmware-side damper (a −c·ω term at 1 kHz, no delay) would do what the
  fork's delayed rate loop cannot. Not this session (the operator's call); it is the next rung if rev 3 leaves
  the ring.
- The hold map above 15 m/s beyond 25° and at 12–15 m/s beyond 30° is extrapolated (BELIEF); 4–8 m/s beyond 150°
  rests on two cells.
- `b` (the low-frequency viscous term, 0.0015–0.004) and the mode's damping (0.0006) are different quantities; the
  simulation carries only the mode's. The move term (`AccordFFRateGain` 0.5 on 1/G) is unchanged.
- The scorer's ratchet instruments count the limit cycle's zero crossings as dwells; on rev 3 read §7.1 beside
  the 2.34 Hz line, not alone.
- The subagents' final reports never arrived this session (both agents went idle without messaging); their
  outputs were read from disk. `fetch-rlogs` and the scorer did their jobs.
