# HANDOFF 2026-09-23 — V294 redone and re-verified by four fresh Opus agents; all pass; the record corrected

**Operator's instruction:** *"Redo and verify all work using Opus 5.5 subagents … the work of using both LKAS PID on
acceleration and torque mode feedforward and StarPilot corresponding updates."* Four Opus agents on disjoint surfaces,
each writing its FAIL criteria before running and re-deriving from the images / the fork source, never from the build
script's constants. Nothing was re-cut: **V294 (image `3143616d…`, rwd `a2b418f0…`) stands as built, NOT FLOWN.**
Reports and scripts: `analysis-2020accord/studies/v294/redo_2026-09-23/{build,ghidra,physics,fork}/`. Page v3:
https://claude.ai/artifact/BcuAb3dgHP84oasqeadVBs

## Verdicts
| agent | surface | verdict |
|---|---|---|
| redo-build | bytes · CRC · ISA decode · independent rebuild · rwd codec · assertion census · Kp records · cell readers | **PASS — flash-eligible** |
| redo-ghidra | decompiler structure · sign through the chain · x scale · cell privacy · interlocks (governor/EME/lockstep/DTC) · cave/tap | **PASS — flash-eligible** |
| redo-physics | exact closed loops (1 kHz discrete + continuous) · 3,456 plant variants · 1,008 outer-loop variants · instrument replayed on real null routes | **PASS on the image; two FAIL criteria fired as written (ζ× at low speed; the instrument)** |
| redo-fork | every torque-mode-era change and its gate · param wiring · codec · the real controller run under r1 and REVERT · tests | **deployable with two conditions; 7 defects, 2 fixed** |

## What the redo confirmed (EVIDENCE)
- The six edits, byte for byte: own CRC walker (50/50 stock and V294), both opcodes hand-decoded from the ISA and read back
  in Ghidra, an independent rebuild from V293 reproducing the shipped hash, an independent rwd decoder returning the image
  bit-for-bit, 314 diff bytes (2 code, 4 fb cal, 280 Kp, 28 CRC over 7 trailers — 0xC4FFC is the main block's trailer, which
  is why it changes with no other byte in 0xC4000–0xC4FFB).
- r26 = s_new − s_old from the decompile and the listing (r26 loads s_old at 0x28F7C, r9 becomes s_new at 0x28FA2; the fb
  state is gp-0x3d30). E = 4·sp − r26. The FF identity holds for every 32-bit sp; the surface at r26 = 0 equals V293's in
  154 k full-chain cases. The operand settles to exactly 0 at every constant x (24,001 values, monotone map), dither < 2 counts.
- Negative feedback: the polarity flag multiplies both the rate input and the output, so it cancels; the same path was a
  stable rate servo on stock/V282/V292.
- x = 8.00 counts per deg/s: 0x55B48 writes (−x)>>3 into 0x14A, the Accord DBC factor there is −1, and d(steeringAngleDeg)/dt ÷
  steeringRateDeg = 1.002–1.007 on three V292 routes. (`x_scale_from_v292_wire.py` is CIRCULAR for the unit — it divides by
  carState rate, which is x/8 by construction — the scale rests on the bytes and the angle-derivative check.)
- Cell privacy: Ghidra xrefs = raw Python scan on every changed cell, the Kp table, the fb state; no governor, EME, lockstep or
  DTC reader; the 0x14A cave and the 427 tap read the delivered torque gp-0x6b38. 1874/1874 instruction boundaries identical.
- 20 Hz: −26.69 dB vs V282 (2.079 vs 44.90 P-counts per x-count); V294's controller is 4–6 % of V282's from 1 to 60 Hz.
  |L| = 0.023 at the 20.8 Hz −180° crossing; zero unstable closed loops in 3,456 variants. Outer loop: V294 never
  destabilised a loop that was stable on V293 and stabilised 247 that were not.
- Fork: the real `LatControlTorque` at HEAD + the r1 config is bit-identical to the pre-V293 base and to the generic torque
  path on two 12,000-frame scenarios (0 calls of plant FF / hysteresis / rate loop / observer; notch and dither inert; jerk
  LPF 1.2 Hz; Ki 0.3 flat). HEAD + the REVERT file is bit-identical to rev 6.4. Every param default = get_value default =
  getattr fallback; the codec re-encodes all 22 configs byte-identically; SteerFriction 0.011 / SteerLatAccel 14 cannot be
  back-filled by either sync logic.

## What the redo corrected (each now on the page, in STATE, PART6 and the memory)
1. **ζ× was a quasi-static estimate.** Exact closed-loop poles: ×0.89 / 1.00 / 1.29 / 1.43 / 1.73 at 5 / 8 / 12.5 / 19 / 26
   m/s (map k), ×0.92 / 1.05 / 1.38 / 1.79 / 2.25 on the design's levelled k — the orchestrator's own 4th-order roots
   reproduce these. **Below ~8 m/s the wheel mode is slightly less damped and slower** (a heavier wheel in car parks); the
   decay rate falls at every speed below ~21 m/s. Never unstable. BELIEF plant. Lever: the pole cell 0xC63E8 (a 1018 = 0.94
   Hz restores ×1.07 at 5 m/s, costing outer-loop margin at 26 m/s, +34° → +18°). `v294_design.py` now prints the exact table
   (`mode_zeta_exact`) and marks `mode_analysis` superseded for ζ.
2. **The pre-registered instrument failed on real data.** As written it read +0.021 (−0.027 … +0.087) on twenty 20 s hands-off
   windows of the V293 null routes 70–75, overlapping a live +0.067; wrong units (1.85 is |T/rate| at 2.4 Hz). **Replaced:**
   byte-exact 1 kHz predictor on the route's own command (fade + 5.05 Hz output lag, ms-aligned tap), regressor = the
   output-lag replica of −d/dt LPF_2.03(rate) in deg/s², nuisance FF + dFF/dt; null +0.004 vs synthetic-live +0.196, 20/20:
   **β > +0.10 T counts per deg/s² = LIVE (expected +0.21), |β| < 0.04 = NOT LIVE, between = inconclusive.**
3. **Sign hazard in the kit's caches.** The v280 cache `rate` column is the RAW 0x18F field = −8 × carState.steeringRateDeg
   (measured −8.00 on r6d/e/f; the firmware writes −x at full resolution there, DBC factor −0.1 reads 0.8×). On that column
   the old rule would have called a correct build "inverted". Calibrate the regressor's sign against the feedforward on the
   same route; prefer carState.steeringRateDeg.
4. **Every filter restart is an 80–400 ms braking pulse**, not one tick: the lag state is forced to 0 at each gate re-open and
   rebuilds on the 2 Hz pole; peak 15 / 73 / 128 / 336 counts at 10 / 50 / 88 / 231 deg/s, ≤ 615, always opposing motion.
5. 180° crossing 19–24 Hz for a 2–3 ms transport delay (delay-dependent; not ~26 or ~40 Hz), negligible in size; max |L|
   1.1–1.2 (not 1.7); the trim goes one-sided from demand index 236 (P clamp; circle criterion clears it).
6. **"PID on acceleration" is a misnomer.** It is P-only on 2 Hz-lagged acceleration plus feedforward. Ki must be 0 because E
   carries the feedforward (I would integrate the command); Kd must be 0 because D carries a setpoint kick on every 0xE4 step
   and jerk feedback anti-damps below 3.2 Hz. "I on this operand = V282's class" holds as a class, not as a gain.
7. Two derived RAM cells change value (gp-0x6a34 = |r26|>>5, gp-0x6cf8 = E_prev = 4·sp − r26); every reader is the zeroed D
   path, the unreachable gp-0x680a lane or an uncalled twin of the PID. "Four bytes below 0xC0000" = four written, two differ.
   The build script's substantive-assertion count is 32 by an independent census (its own label says 66).
8. **Secondary signature:** the r1 fork config is route 71's config (Kp 0.9 for 0.85); on the V293 plant the model reproduces
   route 71's 2.34 Hz limit cycle above 19 m/s. **If the trim is not live, expect that limit cycle on hard curves at ≥ 19 m/s.**

## Fork: conditions and defects
- **(a) Import the r1 config PARKED.** Galaxy restore allows the keys onroad, and the plant-FF → generic switch steps the law
  (up to 0.46 torque in the synthetic run).
- **(b) Run Rebuild Params after pulling.** The committed params library knows no Accord keys; without a rebuild the REVERT
  file silently loses AccordJerkLpHz 4.0 (r1 is immune — its Accord values equal the get_value defaults).
- **Fixed (in the operator's working tree; the agent's commit and push were blocked by the permission classifier):** five
  Accord tests in `selfdrive/controls/tests/test_latcontrol.py` broke on 54ff1ea39 because they exercised the rev-6.4 law
  through the old fallbacks — they now set those toggles explicitly (`TestLatControl._rev64_accord_toggles`), 25/25 Accord
  pass, layout 25/25 and safe_mode 13/13 unchanged, the 14 remaining failures are the parent's pre-existing Windows encoding
  failures on Hyundai/Kia/GM paths. `LaneChangeTurnGate` is read with the `known()` guard the Accord keys have.
- **Left as is, stated:** LaneChangeTurnGate (rev 6.2) stays ON by default — a lane-change smoothing gate, not a torque-mode
  term; UseAutoSteerDelay stays true — the operator's own setting, not V282-era (the reference routes flew 0 with SteerDelay
  0.2); SteerDelay 0.2 and LaneChangeSmoothing 4 match pre-V293.
- **Known stale:** `toggle-config_V282_rate_servo_REVERT.json` turns the plant FF on, which now runs V293's G/K tables
  (hold ×2.3, move ×0.35 at 12.5 m/s vs V282) — matters only if the car goes back to a V282-class image.
  `studies/v294/fork_revert_patch.py` is a partial replay of 54ff1ea39 (header note added).

## Not verified / BELIEF
J 8e-5, the light-b world, the hold-map k, the 2–3 ms transport delay, the 3 ms rate-former window, the vehicle model; the
motor-resolver origin of the rate; two register-indirect residuals (a .data pointer 16 B from gp-0x680a; a pointer family
0x78 below 0xC62E6); the EME consequence of 616 counts at zero command (taken from adversary B, 2026-09-20).

## Next
Operator's: pull Dom (working-tree fix to commit), Rebuild Params, import `toggle-config_V294_accel-trim_r1.json` parked,
confirm SteerFriction 0.011 / SteerLatAccel 14 in initData, kill openpilot, flash the V294 rwd only when its file and bus are
named, drive one symptomatic episode. Analysis: run the FIXED instrument (`redo_2026-09-23/physics/rp7b_dynamic_pred.py`
pattern) on the route from the device's realdata; β > +0.10 = live.
