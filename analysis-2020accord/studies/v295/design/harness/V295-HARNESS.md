# V295 closed-loop design harness: what it is, and where it can and cannot be trusted

Subagent `harness`, 2026-09-30. **Design only.**
- Nothing was built, flashed or sent, and no CAN traffic was generated.
- The fork was only read: a `git archive` of `20d24ab79` went into `_scratch/`, and the operator's clone was never checked out or written.
- No firmware artifact, STATE, memory, lineage or golden-model file was edited, and nothing was committed.

Every decision-bearing claim is marked **[E]** EVIDENCE (with its method) or **[B]** BELIEF. Symptoms are the operator's to score; everything here is a band, a transfer function or a simulation.
Pre-registered gates and tolerances: `CRITERIA-HARNESS.md` (written before any harness number).

The harness proposes **no lever**. The candidates in the tests (b 1134, Ki 8, Kd 128) exercise code paths; they are not recommendations.

---

## 0. Bottom line, for the four designers (read this first)

1. **The harness CANNOT retrodict r71b's 1–8 Hz wheel motion from the plant alone. By the pre-registered rule, every speed band is NOT FIT** under both independent disturbance models (`c0`, `lp`). [E] `h4_retrodict_out.txt`.
   - The identified plant family makes only **6–26 % of the drive's 1–3 Hz wheel-rate rms** (nominal: 0.17–1.27 deg/s against 1.06–8.83; up to 40 % on `b_lo` at 0–5 m/s).
   - It makes **2–9 % of the hard-turn 1.6–3 Hz level**, and a trim/FF ratio **×0.07–0.47** of the drive's.
   - The light-damping prior `light_b` [B] makes 41–132 % of it, but with the wrong timing: per-chunk rate R² ≤ 0, and the plant study found the same.
   - Under the identified family the drive's 1–8 Hz wheel motion is mostly **road/tyre disturbance, not loop-generated**. That is [B]: it inherits the plant fit's heavy damping (ζ_open 1.3–4.0).
2. **Its OUTER-LOOP numbers do retrodict, under `dist="lp"`.** Only the drive's own 0.1 Hz residual is injected (road bank/crown plus slow model error). [E] same file.

   | metric | FIT | DIRECTIONAL | other |
   |---|---|---|---|
   | tracking gain | 4/5 bands | 15–22 m/s: 0.764 vs 0.830 | |
   | command rms | 5/5 bands | | |
   | integrator share | 5/5 bands | | |
   | turn-hold | 3 of 4 testable bands | 10–15 m/s: 0.59 vs 0.51 | |

   Under `dist="c0"` (one constant per chunk) the 15–22 m/s band collapses: tracking gain 0.475 against 0.830. The **static** plant at 15–22 m/s is wrong. Its dynamic k of 80 T/deg is too stiff for the hold.
3. **With the drive's disturbance replayed (`dist="full"`), every band is FIT**, on every member. Per-chunk angle R² is 0.999 and rate R² 0.967. [E]
   - This is a **consistency check** of the loop assembly (fork, pipeline, lane, plant inversion). It is **not** independent evidence for the plant.
   - It is also the basis for **counterfactuals**: the same road with different cells.
   - Such a counterfactual is **biased toward "no change"** wherever the real steering has feedback-dependent dynamics the model lacks. The replayed residual still carries V294's version of them [B].
   - Bracket every counterfactual with `light_b`.
4. **The lane and the fork are EVIDENCE-exact.**
   - The lane equals the golden model on 90,000 random ticks, including Ki and Kd live and V282-class cells: 0 mismatches.
   - It is bit-exact to the plant study's march on all 1,020,390 r71b ticks.
   - Its tap residual is 3.64 counts, the same as plib's G1.
   - The REAL `LatControlTorque` at `20d24ab79` reproduces r71b's torqueState. Output R² is 0.9999989 as pre-registered, and output rms is 1.8e-7 once the input alignment is identified.
   - The vectorised port is bit-identical to the real code, on the replay and on closed-loop trajectories.
5. **The pre-registered H3a FAILED on one clause, and I report it as failed.** The 0xE4 count was within ±1 on **98.24 %** of frames against the ≥ 99 % I wrote.
   - Cause [E]: on 4.1 % of frames controlsd still held the previous liveParameters message (20 Hz). My previous-value alignment used the newer one.
   - Identifying the message the controller actually used, from its own logged `actualLateralAccel` (100 % of active frames match exactly), gives 99.96 % within ±1. All clauses then pass.
   - The alignment was changed **after** the result (POST-HOC). The controller itself was never the issue.
6. **The V294 trim does nothing to the outer-loop under-delivery.** [E for the simulation, B for the car] In the harness counterfactual (V293 = C 0 against V294 on r71b's own road):
   - tracking gain, turn-hold and integrator share differ by ≤ 0.004, and command rms by ≤ 0.4 %, in every band, on every member;
   - "loose / understeer" (tracking gain 0.76–0.92) is **not a property of the inner trim**. It is the fork law (r1, LAF 14) on this plant;
   - what the trim does move is the 1–8 Hz wheel motion: hard-turn 1.6–3 Hz rate ×0.77 at 5–10 m/s and ×0.93 at 15–22 (nominal, `full`); ×0.56 / ×0.43 on `light_b`.
   - The drive against r75/r76 read ×0.56–0.91 in matched hard-turn cells. That is directional agreement, but **confounded**: those reference routes also ran a different fork config.
7. **The inner trim loop is WEAK on the identified plant.** [E, linear 1 kHz analysis]
   - |L| is 0.05–0.41 in 1–3 Hz (nominal 0.06–0.30) and 0.05–0.31 in 3–8 Hz across the identified family (0.68–0.80 / 0.29–0.36 on `light_b`).
   - The plant's own damping (b 5–26 T/(deg/s)) dwarfs the trim's 1.8.
   - "Tracking α needs |L| ≫ 1" is one to two orders of magnitude away on this family. Nothing is near instability: Ms ≤ 1.14, and rigid-member GM ≥ 16 even at 9 ms delay.
   - The **outer** loop is where the worlds disagree. Identified family: Ms 1.05–1.29, GM 7.7–29. `light_b`: Ms 1.7–**3.1**, GM down to **1.7 at 27 m/s** [B].
   - So any candidate that raises the lane's forward gain must be checked on `light_b` at highway speed.
8. **Do not use the simulated dwells/min.** The sim's dwell count is set by the sensor-noise model: 19–50 /min at zero noise, 2–63 at the measured 1.93 counts, and 0 at 4 counts [E, `h6`].
9. **Nothing above about 8 Hz is identified.** Every high-frequency statement rests on the stress members `mode13`, `mode20` and `mode20_lo` [B].

---

## 1. Pre-registered gates and what fired (`CRITERIA-HARNESS.md`)

| gate | criterion | result |
|---|---|---|
| H1a | lane == golden model tick for tick (T, E, I, P, D, S, y), ≥ 50,000 random ticks, 9+ cell sets incl. Ki/Kd live | **PASS**: 90,000 ticks, 0 mismatches. The 10 sets include V294, Ki 8, Ki 64, Kd 128/Dcl 10240, a Ki+Kd schedule, V282 (sum op, shl 5, C 46080, Kd 128), V293 (C 0), random banks with e_shift 3, e_shift 0 with the sum op, and e_shift 5 with Kd. A batched lane with all 10 sets matches as well |
| H1b | the int32 guard raises on constructed overflows and not on V294 over the whole r71b replay | **PASS**. Controls raised at `a*s` (b 2361 > b_max 2301), `E*Kp` (−3.02e9) and the 16-bit `sxh` of y (32805). V294 is clean over 1.02 M ticks |
| H1c | bit-exact to `plib.march` on r71b; tap ≤ 10 counts rms hands-off | **PASS**: 0 / 0 mismatches (live / null); tap 3.64 counts (plib G1 3.64) |
| H2a | PlantBatch == `v294_plant.simulate` to ≤ 1e-9, open and closed loop | **PASS**: 0.0 on every tick, across 6 members × 3 speeds open loop and 3 members closed loop with x noise |
| H2b | kappa map: 1.16 ± 0.03 on centre, 0.965 ± 0.02 beyond 160° | **PASS**: 1.146 / 0.963 |
| H3a | REAL fork replay: output R² ≥ 0.999, rms ≤ 0.003; p/i/f R² ≥ 0.995; carOutput R² ≥ 0.999; 0xE4 ±1 on ≥ 99 % | **FAIL as written, on one clause**: 0xE4 ±1 on 98.24 %. Every other clause passes (output R² 0.9999989, rms 1.3e-4). **POST-HOC** with the identified liveParameters message: **PASS** on every clause (output rms 1.8e-7, 0xE4 ±1 on 99.96 %, exact on 99.94 %) |
| H3b | port == real, ≤ 1e-9, on the replay and in closed loop | **PASS**: worst 5.6e-17 (one ulp in `f`). Closed loop 0.0 on 8 lanes with the real code driving |
| H4 | retrodiction per band: FIT / DIRECTIONAL / NOT FIT; plus the harness-FAIL sentence | **Plant alone: NOT FIT in every band. Disturbance replay: FIT in every band.** The pre-registered harness-FAIL sentence ("sim tracking gain ≥ 0.95 where the drive read 0.80–0.83, or cmd rms off > ×1.5 in two bands, or divergence") **does not fire**. §6 |
| H5 | determinism; V293 control; anchors | **PASS**. Score hash is identical on a re-run and the sim is bit-identical. V293 has \|T − T_null\| = 0 on every frame and \|L\| = 0. V294 rail +2461, b_max 2301.1, T at zero command 616 |

---

## 2. The lane (`Lane`, `Cells`)

**Parameters.** Every knob of the census is a field of `Cells`, read **by address** from the image and hash-checked for V294:

| group | knobs |
|---|---|
| fb lag | `fb_a` 0xC63E8, `fb_b` 0xC63EA, `fb_clamp` 0xC62E6 |
| opcodes | `fb_op` (0x28FA4 add/subr), `e_shift` (0x29D76 shl imm5) |
| P and D banks | Kp bank 0xCB994 (X and Y), Kd bank 0xCB7D4, `d_clamp` 0xC61B6 |
| I | `ki` 0xC63E6, `deadband` 0xC62E4, `i_clamp` 0xC61BA |
| clamps | `p_clamp` 0xC61BC, `sum_clamp` 0xC61BE, lane clamp `t_clamp` 0xC61B4 |
| output | output lag `lag_a` 0xC63EC / `lag_b` 0xC63EE, `gain` (via the displacement at 0x2A1F0) |
| demand map | 0xC9A88, `idx_clamp` 0xC64F0 |
| tapers | the demand arms G_same 0xCB924 and G_opp 0xCB8B4; the post-PID tapers B 0xCBC34 (on gp-0x6830) and D 0xCBBC4 (on \|bar>>5\|) |

- Knot counts are fixed by code, as in the census.
- [E] `Cells.from_image` equals the kit reader on every shared field.
- Its V294 dead band (4) and I clamp (10240) match the census.
- `Cells.problems()` flags static latent defects: b > b_max, map Y > 32767, a taper product > 65535, sum/lane clamp > 32767, knot order.

**Arithmetic.**
- It mirrors `lkas_fb_lag` + `lkas_rate_pid_tick` line for line, with the addresses in the docstring.
- Bails mirror the firmware: at |x| > 12000, r26 = 0, I = 0, E_prev is poisoned, S = 0, and the next tick restarts the fb state from 0.
- The int32 guard checks every 32-bit product and sum, and the 16-bit `sxh` of y.

**Sign convention.** [E] It is the kit's validated march: sp = sign(wire)·map(idx), x = +raw 0x18F rate, output in the tap's sign.
- [B] The firmware's own polarity cancels in the loop.
- The two conventions can differ by floor asymmetry at 1 LSB, which the 8-count tap cannot see.

**Speed.** One `Lane.tick` over a batch of B costs 45–90 µs with the guard on, roughly flat up to B ≈ 300: 1.02 M ticks for B = 2 took 88 s through `Lane.march`.

**Demand-chain note [E, a report].** The harness's integer demand chain (the census arithmetic) and the kit's float `demand_live` / `fade_multiplier` (raw bar ×1.024, `|bar|//32`, float interpolation) disagree on engaged frames:
- idx on 0.75 %;
- the taper m on 4.5 %.

All of these are driver-torque frames. Hands-off, with bar ≈ 0, both give m = 254. The simulation has no driver, so this does not bear on anything here.

---

## 3. The plant (`family()`, `PlantBatch`)

**Members** (all speed-scheduled, from `v294_plant.family()` unless marked):
- `nominal` (J 0.2, the identified b/k/F);
- `J_lo` 0.1, `J_hi` 0.5 and `J_hi2` 0.8, each refitted;
- `J_0.3` (harness: nominal b/k/F at J 0.3, not refitted);
- `b_lo`, `b_hi`, `F_lo` and `F_hi` (the G3a-bias corners);
- `tau0` and `tau6`, plus `tau9` (harness: delay ×1.5 of 6 ms);
- `ms_free`;
- `light_b` (the prior, [B]);
- two-mass stress members (harness): `mode13` (13 Hz, ζ 0.1, r2 0.2), `mode20` (20 Hz, ζ 0.05), `mode20_lo` (20 Hz, ζ 0.02, r2 0.5);
- `nominal_kappa` (harness: the rack→wheel map on the reported angle).

**Kappa.** [E, the metric agent's 7-route table] dW/dθ = κ(W): 1.148 → 0.963 by \|angle\| bin, applied to the angle the fork sees. The dynamics stay in the fit's own angle.
- [B] Which angle the identified spring acts on is ambiguous: the fit used the 0x14A wheel angle with θ' = x/8.
- That is why `kappa` is a member, not the default.

**Karnopp stick-slip, delay, the 3 ms rate former, x noise.** These are exactly `v294_plant.simulate`'s (H2a is bit-identical).

---

## 4. The fork outer loop (`fork_real.py`, `ForkPort`)

- **The real code.** `fork_real.RealController` imports the fork's own `LatControlTorque`, `PIDController`, `FirstOrderFilter`, `get_friction`, `VehicleModel`, the Accord steer-ratio map and the friction-threshold tables from the extract. It runs them in controlsd's order:
  1. `pid._k_p ← SteerKP`;
  2. `VM.update_params(stiffness, SR map(angle − offset) × 16.84/16.88)`;
  3. `update_live_torque_params(LAF 14, learned offset, friction 0.011)`, which are capnp Float32 fields;
  4. `update(...)`.

  CarParams are rebuilt from r71b's logged carParams plus the Honda interface's own scalings. There are three stubs, none on the torque path: setproctitle, the tici hardware layer and `Pose`.
- **Three quirks the real code has, each EVIDENCE and each mirrored.**
  1. The PID is fed `pid_log.error`, the value **read back from a capnp Float32 field** (`latcontrol_torque.py` `self.pid.update(pid_log.error, ...)`). P and I therefore see a float32-rounded error, while the friction relay sees the float64 one. The port was 2.6e-8 relative off until this was mirrored.
  2. The r1 friction threshold is 0.30 flat at every speed (`get_standard_friction_threshold`, asserted on a 0–40 m/s grid).
  3. The latAccelOffset, friction and LAF are float32 after `update_live_torque_params`.
- **The pipeline, measured from the log timestamps** [E]:
  - 0x14A arrival → carState 2.6 ms → controlsState +4.4 → carOutput of the **next** frame +15.4. Card applies the carControl of the previous controlsd frame: pairing with it reproduces carOutput on 99.94 % of frames, pairing with the newest one on 0.4 %.
  - The 0xE4 TX echo leads the carOutput log by 2.5 ms.
  - Total 0x14A arrival → 0xE4 on the bus ≈ 20 ms. The harness uses `pipe_ms` 22, with ~2 ms EPS-internal sample age as [B].
  - `h6` shows every retrodicted metric moves < 1 % over 2–62 ms.
- **Inputs the fork sees in closed loop.** The simulated angle is quantised to 0.1° with `steeringPressed` False. Everything else is exogenous from r71b: recorded vEgo, roll, angle offset, learned latAccelOffset, lat_delay (liveDelay 0.326 + 0.1), and `controlsState.desiredCurvature` (the clipped curvature controlsd passed). `steer_limited_by_safety` follows controlsd's own rule and is updated only while selfdriveState is active.
- **Honda limiter.** It clips ±0.03 per frame, and the count is `int(−limited × 4096)`.
- **Warm start per chunk.**
  - The port replays the logged inputs for the 1.5 s before the chunk (the 1 s request buffer and filters), then takes the logged integrator value.
  - Each lane warms up on its **own cells** over the same 1.5 s from the recorded 0xE4 and 0x18F rate, so a candidate does not inherit V294's filter state.
  - The plant starts from the measured angle and rate.

---

## 5. The closed loop (`simulate`)

- Mode A plays the recorded 0xE4 at its frames, optionally with an exogenous probe band-limited to 0.3–8 Hz.
- Mode B runs the fork port at 100 Hz on the recorded planner demand. The command becomes effective at tick 10k + `pipe_ms` and is held (ZOH) at 1 kHz into the lane.
- In both modes the lane and plant tick at 1 kHz, with x from the plant's rate former plus white noise of 1.93 counts rms (the plant study's standstill measurement).
- A `C = 0` **null shadow** of every lane runs on the same command, which gives the FF/trim split.
- The batch covers every (cells × member × chunk) combination; the chunks are hands-off laterally engaged runs of 10 s or more, cut to ≤ 60 s. r71b gives **21 chunks, 608 s**.
- Everything is deterministic; seeds are fixed.

**Disturbance models** (`SimOpts.dist`):

| name | what is injected | what it tests / is for |
|---|---|---|
| `c0` | one constant torque per chunk: the mean equation residual under the member (the plant study's per-window offset) | the plant alone |
| `lp` | that residual low-passed at 0.1 Hz | the plant above 0.1 Hz; the **outer-loop** metrics |
| `full` | the residual at full bandwidth (disturbance replay) | consistency; **counterfactuals relative to V294** |

---

## 6. Retrodiction on r71b (H4): `h4_retrodict_out.txt`

**The measured side, second method** [E]. My metric code on the bands report's own band edges reproduces the S2 numbers:

| band | tracking gain, mine / report | turn-hold, mine / report |
|---|---|---|
| 1–8 m/s | 0.831 / 0.836 | 0.838 / 0.81 |
| 8–15 m/s | 0.796 / 0.800 | 0.691 / 0.69 |
| 15–22 m/s | 0.831 / 0.831 | 0.673 / 0.67 |
| > 22 m/s | 0.934 / 0.934 | 0.943 / 0.94 |

Integrator share is 0.03–0.08 higher than the report's, because my mask is the hands-off chunks and S5's is all engaged frames.

**Nominal member, three disturbance models, grades by the pre-registered tolerances.** Each cell is measured / sim → grade.

| band | model | tracking gain | turn hold | i-share | cmd rms | trim/FF | rate 1–3 Hz | hard 1.6–3 Hz | **verdict** |
|---|---|---|---|---|---|---|---|---|---|
| 0–5 | c0 | .873/.806 DIR | n/t | .509/.511 FIT | 550/633 DIR | .057/.025 NOT | 4.84/1.27 NOT | n/t | **NOT FIT** |
| 0–5 | lp | .873/.840 FIT | n/t | FIT | 550/603 FIT | .057/.027 NOT | 4.84/1.15 NOT | n/t | **NOT FIT** |
| 0–5 | full | .873/.874 FIT | n/t | FIT | 550/551 FIT | .057/.057 FIT | 4.84/4.94 FIT | n/t | FIT |
| 5–10 | c0 | .871/.837 FIT | .796/.733 DIR | FIT | 514/578 FIT | NOT | 8.83/1.14 NOT | 14.9/1.1 NOT | **NOT FIT** |
| 5–10 | lp | .871/.865 FIT | .796/.780 FIT | FIT | 514/524 FIT | NOT | 8.83/1.10 NOT | 14.9/1.2 NOT | **NOT FIT** |
| 5–10 | full | FIT | FIT | FIT | FIT | .063/.063 FIT | 8.83/8.83 FIT | 14.9/14.9 FIT | FIT |
| 10–15 | c0 | .583/.564 FIT | .505/.529 FIT | FIT | 247/239 FIT | NOT | 2.68/.28 NOT | n/t | **NOT FIT** |
| 10–15 | lp | .583/.586 FIT | .505/.592 DIR | FIT | 247/242 FIT | NOT | 2.68/.26 NOT | n/t | **NOT FIT** |
| 10–15 | full | FIT | FIT | FIT | FIT | FIT | FIT | n/t | FIT |
| 15–22 | c0 | .830/.475 **NOT** | .673/.381 **NOT** | FIT | 326/473 DIR | NOT | 3.14/.18 NOT | 7.6/.2 NOT | **NOT FIT** |
| 15–22 | lp | .830/.764 DIR | .673/.636 FIT | FIT | 326/350 FIT | NOT | 3.14/.19 NOT | 7.6/.2 NOT | **NOT FIT** |
| 15–22 | full | FIT | FIT | FIT | FIT | FIT | FIT | 7.6/7.5 FIT | FIT |
| 22+ | c0 | .924/.830 DIR | .943/.870 DIR | .256/.350 DIR | 281/340 DIR | NOT | 1.06/.17 NOT | 1.77/.16 NOT | **NOT FIT** |
| 22+ | lp | .924/.917 FIT | .943/.941 FIT | FIT | 281/283 FIT | NOT | 1.06/.17 NOT | 1.77/.16 NOT | **NOT FIT** |
| 22+ | full | FIT | FIT | FIT | FIT | FIT | FIT | FIT | FIT |

Exposure by band: 41 / 154 / 182 / 158 / 71 s. Turn-hold at 0–5 m/s and hard turns at 0–5 and 10–15 m/s are NOT TESTABLE (under 200 frames or under 5 s). Dwells are FIT/DIR everywhere but carry no weight (§0.8).

**All members** (`h4` verdict matrix):
- Under `c0` and `lp`, every member except `light_b` is NOT FIT in every band, and for the same reason: the 1–8 Hz wheel motion.
- `light_b` is FIT at 0–5 m/s and DIRECTIONAL at 22+, but its per-chunk rate R² is ≤ 0.
- Under `full`, every member is FIT in every band, except `J_lo` at 22+ and `nominal_kappa` at 15–22, which are DIRECTIONAL.

**Mode A literal metric** (cmd → α gain-phase fit, per-chunk medians, `full`). The sim equals the drive in 0.3–1 and 1–3 Hz. In 3–8 Hz the phase is +66° in the sim against +39° on the drive [E].

| band | drive R² | drive \|G\| | drive phase | sim R² | sim \|G\| | sim phase |
|---|---|---|---|---|---|---|
| 0.3–1 Hz | 0.21 | 0.13 | +83° | 0.25 | 0.12 | +83° |
| 1–3 Hz | 0.32 | 1.42 | +20° | 0.33 | 1.44 | +30° |
| 3–8 Hz | 0.21 | 3.77 | +39° | 0.18 | 3.31 | +66° |

These medians are not the metric agent's pooled numbers (0.37 / 0.55 / 0.16). The method differs (per-chunk, α from the rate derivative, a different hands-off mask); sim and drive here use one code.

**Sensitivity (`h6`):**
- `pipe_ms` from 2 to 62 ms moves nothing more than 1 %. The command R² under `full` peaks weakly at 22 ms (0.9991).
- The sim's dwell count is set by `x_noise`.
- The slew-limit share is 0.29 % at 0–5 m/s (sim 0.22–0.29 %) and about 0 elsewhere [E].

---

## 7. The scoring API: how to use it

```python
import sys; sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness")
import v295_harness as H
base = H.Cells.v294()                         # every knob read from the V294 image (hash-checked)
cand = base.replace(fb_b=1134, name="b1134")  # any knob; give every candidate a distinct name
cand.problems(); cand.edit_class(base)        # static checks; "cal-only" / "opcode" / "opcode+cal"
r = H.score(cand)                             # ~80-100 s: candidate + V294 in ONE batch
H.print_score(r)
q = H.score(cand, quick=True)                 # ~5-12 s: M_SAFE, M_LOOP, M_HF (linear), closed-form M_TRACK, outer loop
S = H.sweep_drive([c1, c2, c3], plants=("nominal", "light_b"), dists=("full", "lp"))   # ~20 s per dist, many candidates
json.dump(H.to_jsonable(r), open(path, "w"))  # score dicts have tuple keys
```

**`score(cells, plants=DEFAULT_PLANTS, modes=("A","B"), dists=("full","lp"), quick=False, probe=0.10)` returns:**

| block | contents |
|---|---|
| `meta` | cells, the diff vs V294, edit class, `problems()`, harness file sha256, runtime, a deterministic hash |
| `M_SAFE` | rail ± (sign-asymmetric: +2461 / −2463 on V294); sub-rail slope (0.6409 T per wire count); trim cap / T at zero command (616, 25.0 % of the rail; **with Ki > 0 a lower bound, see `cap_note`**); int32 worst-case margins (V294 minimum 4.06, at `a*s`); b / b_max (0.246); restart pulse at 10 / 30 / 100 / 300 deg/s (V294: 14 / 43 / 144 / 419 T, above 50 T for 0 / 0 / 159 / 252 ms, lane only with the wheel held: the worst case); `soft_eme` (the lane alone cannot reach 5120–5325; base assist is not modelled, [B]) |
| `M_LOOP[(plant, v)]` | \|L\| in 1–3 and 3–8 Hz, Ms (and its frequency), minimum PM, minimum GM, crossovers, Ms and GM at delay ×1.5, the closed-loop modes, and stability (True / "marginal" / False). Computed for the scored plants **and** the stress members |
| `M_HF` | \|T/x\| and \|P/x\| at 5–30 Hz against V294 and V282 (V294 \|P/x\| at 20 Hz = **2.079**, V282 **44.90**: the record's numbers exactly [E]); stress-mode damping against V294 and against open; staircase HF; simulated 1 kHz delivered torque in 5–9 / 9–13 / 13–17 / 17–23 / 23–30 Hz in modes A (`full`) and B |
| `M_TRACK` | closed-form α/cmd per plant (0.3–8 Hz); mode A literal gain-phase fits (`full`); exogenous-probe transfer (`lp`, 10 % probe). **Coherence is 0.33–0.49 at 1–3 Hz and 0.56–0.77 at 3–8 Hz, but under 0.13 at 0.3–1 Hz: do not read 0.3–1 Hz.** Also amplitude flatness, \|α/cmd\| at 1–3 Hz for 30 / 100 / 300 counts rms |
| `M_DRIVE` | the outer-loop linearisation (Ms, PM, GM, \|T(0.2 Hz)\|, with and without the friction relay's small-signal slope); mode-B metrics per band per (dist, cells, plant): tracking gain, turn-hold, straight delivery, J-style error rms (0.15–2.4 Hz), integrator share, cmd rms, slew share, trim/FF, rate rms at 0.3–1 / 1–3 / 3–8 Hz, hard-turn 1.6–3 Hz, dwells, and a 1–5 Hz limit-cycle peak; plus `measured` (the drive, same code) |

**Rules I recommend the orchestrator give every designer. These are BELIEF about good use, grounded in §6.**
1. Report a candidate as a **difference from V294 in the same batch**, never as an absolute sim number, except for the outer-loop metrics under `lp`, which retrodict.
2. Always show **both** `full` (the counterfactual on r71b's road) and `lp` (the loop's own behaviour), on **nominal and `light_b`**.
   - A ranking that flips between them is not supported by this drive.
   - The plant study's rule is the same: prefer candidates whose ranking holds across the family.
3. Any claim above 8 Hz must quote the stress members (`mode13` / `mode20` / `mode20_lo`) and say that they are stress cases.
4. Never quote simulated dwells/min.
5. A candidate that raises the lane's forward gain must quote `M_DRIVE["outer"]` on `light_b` at 17–27 m/s (V294 already sits at GM 1.7–2.6 there on that prior).
6. With Ki or Kd live, the rail is 2481; the trim cap is not C-bounded (see `cap_note`); and no wire instrument sees I or D (census).

---

## 8. Baseline: V294 (as built) and V293 (C = 0, the control) (`h5_baseline_out.txt`, `h5_baseline_full_out.txt`)

**M_DRIVE, nominal member** (measured / V294 sim / V293 sim):

| model | band | tracking gain | turn-hold | i-share | cmd rms | trim/FF | rate 1–3 Hz | hard 1.6–3 Hz |
|---|---|---|---|---|---|---|---|---|
| lp | 0–5 | .873 / .840 / .840 | – | .509 / .513 / .515 | 550 / 603 / 602 | .057 / .028 / 0 | 4.84 / 1.15 / 1.39 | – |
| lp | 5–10 | .871 / .865 / .864 | .796 / .780 / .783 | .379 / .388 / .388 | 514 / 524 / 524 | .063 / .025 / 0 | 8.83 / 1.10 / 1.32 | 14.9 / 1.26 / 1.68 |
| lp | 10–15 | .583 / .586 / .586 | .505 / .592 / .591 | .373 / .395 / .395 | 247 / 242 / 243 | .034 / .010 / 0 | 2.68 / .26 / .28 | – |
| lp | 15–22 | .830 / .764 / .763 | .673 / .636 / .636 | .415 / .436 / .435 | 326 / 350 / 350 | .031 / .004 / 0 | 3.14 / .19 / .19 | 7.62 / .17 / .17 |
| lp | 22+ | .924 / .917 / .916 | .943 / .940 / .938 | .256 / .284 / .282 | 281 / 283 / 283 | .015 / .004 / 0 | 1.06 / .17 / .18 | 1.77 / .17 / .18 |
| full | 5–10 | .871 / .872 / .872 | .796 / .788 / .790 | .379 / .380 / .379 | 514 / 517 / 518 | .063 / .063 / 0 | 8.83 / 8.83 / 10.88 | 14.9 / 14.9 / 19.3 |
| full | 15–22 | .830 / .830 / .830 | .673 / .670 / .672 | .415 / .424 / .424 | 326 / 328 / 328 | .031 / .031 / 0 | 3.14 / 3.13 / 3.33 | 7.62 / 7.52 / 8.11 |

**Across the family, V294 vs V293:**
- Tracking gain is equal to within 0.004 on every member, band and model.
- Hard-turn 1.6–3 Hz under `full`, V294 / V293:

  | member | 5–10 m/s | 15–22 m/s |
  |---|---|---|
  | nominal | 14.9 / 19.3 | 7.52 / 8.11 |
  | b_lo | 14.9 / 21.5 | |
  | light_b | 14.9 / 26.7 | 7.17 / 16.55 |

- The 1–5 Hz limit-cycle line under `lp`: V294 −4.6 dB (nominal) and +0.7 dB (`light_b`); V293 −4.1 dB and **+5.8 dB at 1.27 Hz** (`light_b`).

**M_LOOP, V294:**
- \|L\| in 1–3 Hz: nominal 0.30 / 0.30 / 0.16 / 0.07 / 0.06 at 3 / 8 / 12 / 17 / 27 m/s; b_lo up to 0.41; light_b 0.68–0.80.
- Ms: 1.01–1.10 on the identified and delay members (`tau9` 1.10) and 1.12–1.14 on light_b.
- GM: 16–201 (minimum 16.3, `tau9` at 3 m/s).
- Every member is stable, with delay ×1.5 included.
- Closed-loop pair at 2.2–5.6 Hz, ζ 0.71–0.89, ordered by J (J_hi 2.2–2.8 Hz; nominal 3.9–4.2; J_lo 5.4–5.6): the lane's lags against J, as the plant study found.

**Stress modes, V294 against open** (the trim's |P/x| at 20 Hz is 2.079, so V294 barely touches them):

| mode | 5 m/s | 12 m/s | 25 m/s |
|---|---|---|---|
| 13 Hz | ζ 0.145 vs 0.139 | ζ 0.171 vs 0.162 | ζ 0.146 vs 0.145 |
| 20 Hz | ζ 0.076 vs 0.076 | ζ 0.099 vs 0.097 | ζ 0.115 vs 0.113 |

**M_HF.**
- Delivered torque rms at 5–9 / 9–13 / 13–17 / 17–23 / 23–30 Hz, mode A `full`:

  | build | 5–9 | 9–13 | 13–17 | 17–23 | 23–30 |
  |---|---|---|---|---|---|
  | V294 | 1.74 | 1.11 | 0.65 | 0.53 | 0.23 |
  | V293 | 1.42 | 0.85 | 0.40 | 0.48 | 0.21 |

  Units are T counts. V293's values are identical across members, as they must be with C = 0.
- The staircase response is 21.3 / 7.5 / 2.7 / 1.5 / 0.8 T rms (a ±2000 triangle at the slew cap).

**M_TRACK.**
- Closed-form \|α/cmd\| on nominal at 12 m/s: 0.075 / 0.164 / 0.365 / 0.644 / 0.859 / 1.154 / 1.250 deg/s² per count at 0.3 / 0.5 / 1 / 2 / 3 / 5 / 8 Hz. V294 and V293 are indistinguishable to 3 digits in the closed form, because |L| is small.
- Probe at 1–3 Hz (nominal): V294 0.64 at +44° against V293 0.75 at +39°.
- Flatness, \|α/cmd\| at 1–3 Hz for 30 / 100 / 300 counts rms:

  | member | V294 | V293 |
  |---|---|---|
  | nominal | 0.21 / 0.50 / 0.59 | 0.24 / 0.57 / 0.68 |
  | F_hi | 0.03 / 0.37 / 0.54 | 0.03 / 0.42 / 0.62 (the wheel barely leaves stick at 30 counts) |

  This is the friction deficit, the same shape as the drive's 0.37 against 0.89 (and not the same numbers).

---

## 9. Where it can and cannot be trusted

| use | trust | why |
|---|---|---|
| lane arithmetic, overflow, clamps, rail, sub-rail slope, trim cap, restart pulse, int32 margins | **EVIDENCE** | golden-model equality (H1a), the drive's tap (H1c) |
| the fork's command for a given angle history | **EVIDENCE** | the real code and a bit-identical port (H3) |
| outer-loop metrics under `lp` (tracking gain, turn-hold, integrator share, cmd rms, J error) | **DIRECTIONAL / FIT** at 0–15 and 22+ m/s; **DIRECTIONAL** at 15–22 | H4. Under `c0` the 15–22 band is NOT FIT: the static plant there is wrong |
| 1–8 Hz wheel motion, hard-turn 1.6–3 Hz, trim/FF, from the plant alone | **NOT FIT** | H4, all bands |
| the same as counterfactuals under `full` (difference from V294) | **BELIEF**, bracketed | consistency passes, but the answer is biased toward "no change" and depends on the member; bracket with `light_b` |
| M_LOOP margins on the identified family | EVIDENCE for the model; **BELIEF for the car** | the plant is not identified above ~8 Hz; b and friction at speed carry the estimator's G3a bias |
| the outer loop on `light_b` (GM 1.7–4.4) | **BELIEF** (the prior world) | it predicts this drive worse (plant study), but it is the pessimistic corner |
| HF (> 8 Hz) statements | **BELIEF**, stress members only | nothing identified above ~8 Hz |
| simulated dwells/min | **not usable** | set by the noise model (h6) |
| engage / hands-on / driver-override behaviour | **not modelled** | the sim has no driver: steeringPressed False, bar 0, taper 254 |
| the planner's reaction to a changed car | **not modelled** | the planner demand is exogenous (recorded). A car that delivers more would, on the road, receive a different plan |

---

## 10. Defects, surprises and reports (nothing outside this folder was edited)

1. **H3a failed as pre-registered** (§0.5): a liveParameters message-age alignment, found and handled post hoc.
2. **The fork's PID sees a float32 error** (§4). It is a real property of the flown code: harmless, but any offline port must mirror it.
3. **Card uses the previous controlsd frame.** This is a 10 ms step that the "20 ms to the bus" figure already includes.
4. **The census c6 T/ω table omits the 3 ms rate-former window.** Magnitudes agree to 0.01. Phase differs by 2° at 2.5 Hz and 11° at 20 Hz; the harness includes the window [E: two implementations].
5. **The kit's float demand chain differs from the integer firmware arithmetic** on 0.75 % (idx) and 4.5 % (taper) of engaged frames, all driver-torque frames (§2).
6. **The identified plant's static behaviour at 15–22 m/s is wrong** (`c0` tracking gain 0.475 against 0.830). The dynamic k (80 T/deg) is stiffer than the hold.
7. **The two plant worlds disagree most in the operator's "jerky on hard turns" band and in the outer loop at highway speed** (§0.1, §0.7). This drive cannot pick between them in closed loop.
8. **The plant study's trim/FF targets** (0.080 / 0.063 / 0.047 / 0.027 / 0.016) differ from the chunk-set values used here (0.057 / 0.063 / 0.034 / 0.031 / 0.015). The masks differ. Sim and drive here share one mask.
9. With **Ki > 0** the M_SAFE "trim cap" is a lower bound. With Ki on the difference operand the linear map has a neutral eigenvalue, reported as "marginal" rather than unstable.

---

## 11. Files (all in `analysis-2020accord/studies/v295/design/harness/`)

**Design and criteria**
- `v295_harness.py`: the harness, with the README in its docstring.
- `fork_real.py`: the real-fork runner and the read-only extract.
- `CRITERIA-HARNESS.md`: pre-registered.

**Gate scripts and their outputs**

| script | output(s) |
|---|---|
| `h1_lane_gate.py` | `h1_lane_gate_out.txt` |
| `h2_plant_gate.py` | `h2_plant_gate_out.txt` |
| `h3_fork_replay.py` | `h3_fork_replay_out.txt` |
| `h3b_port_gate.py` | `h3b_port_gate_out.txt` |
| `h4_retrodict.py` | `h4_retrodict_out.txt` |
| `h5_baseline.py` | `h5_baseline_out.txt`, `h5_baseline_full_out.txt` (the full `print_score` of V293 vs V294 and V294 quick) |
| `h6_sensitivity.py` | `h6_sensitivity_out.txt` |

**Regenerable** (gitignored `_scratch/`):
- `fork_20d24ab79/`: the git-archive extract, rebuilt by `fork_real.ensure_extract()`.
- `h3_replay.npz` / `.json`.
- `h4_retrodict.json`.
- `h5_baseline.json`.

**Run order for a fresh checkout:** `h3_fork_replay.py` first (h3b reads its npz); the others are independent.
- Total about 10 minutes: h1 ~2 min, h2 ~1 min, h3 + h3b ~1 min, h4 ~1.5 min, h5 ~2.5 min, h6 ~5 min.
