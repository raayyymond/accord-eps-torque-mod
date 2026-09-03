# HANDOFF 2026-09-02 (late) — two loops: the lane-change ring is openpilot's, the strong-turn ripple is the EPS's

Session: the operator added routes r32 `75604b0a432fdc89_00000032--33a5dbbcb3` and r33 `…_00000033--1948a2c354`, filed as "driven on V278",
with two reports: a slight oscillation riding on strong turns, and a NEW oscillation on highway lane changes that was smooth on V112
("seems like an LKAS PID loop tuning issue, I don't think openpilot is in the loop"). Two exact examples: 09:39:25 seg 5 and 09:42:41 seg 9 of r32.
Four subagents (lanechange, strongturn, loopgain, v268damper); every decision-bearing crux re-checked by the orchestrator from the images or the cache.
No build was cut. Nothing flashed by this session.

## 1. The routes were driven on V280 rev 2, not rev 3 — EVIDENCE, orchestrator-verified
At idx ≥ 200, hands-light, |rate| > 60 deg/s, the lane pushes WITH the wheel 64–69 % of frames and the hands-light p90 rate is 143–155 deg/s.
Under rev 3's ×2 map (reference 44.5 deg/s) the lane brakes there, as r31 showed (0.63–0.83). Chain mirror on the tap: rev 2 line corr 0.89–0.92,
×2 0.28–0.46. **Operator confirmation of the flash is pending.** Consequence: no rev 3 data above 20 m/s exists; rev 3's highway behaviour is predicted only.
Memory: `feedback-attribute-the-build-from-the-tap-not-from-the-label`.

## 2. The comparison "smooth on V112" had two deltas — and one is inert
Full-file diff (orchestrator): V112 → V268 = 1026 B / 284 runs, all 0xCE5BE–0xD9FFF (V268's base-assist "both pumps flattened, all 34 modes");
V268 → rev 3 = 438 B (28 map records, `0xC62E7`, the 32-B tap, CRCs). V268 never flew alone. **But the V268 edit is a no-op in the lane-change
regime:** all four speed records of the wheel-rate damper lane have Y[0] == Y[1] over 0–400 counts (85 deg/s) in V112 already (bytes re-read:
99.9 km/h record 2150,2150,2049,1947 → 2150×4); V268 only flattens the knots above. The boost-amplitude lane it also touches is torque-indexed,
capped ±512, mean-preserving. `studies/v280/V268-DAMPER-DELTA-AT-HIGHWAY-2026-09-02.md`.

## 3. The map never touches the EPS rate loop's own gain — EVIDENCE from the decompile
`idx = f(cmd, driver-torque taper, speed)` is stored at 0x29D14; the Kp LERP (`0xCB994[sel]`, walked 0x29DE8–0x29E12) and the Kd LERP
(`0xCB7D4`) index on that same register as the map. `E = 32·sp − fb`, dE/dfb = −1. So doubling the map doubles dT/dcmd exactly (2.00 at every idx)
and leaves dT/drate at exactly 1.00× V112 (45.6–73.2 counts per deg/s at idx 12–58). The inner loop has identical gain AND phase in V112, rev 3 and
V280. Second-order: at a matched setpoint rev 3/V280 land on a lower idx → 8–29 % lower Kp → slightly LESS inner damping. The D term adds 15–25° of
lead at 3–8 Hz; firmware alone reaches −180° only at 58 Hz (P-only) / 171 Hz (P+D). `studies/v280/LOWCMD-LOOPGAIN-V112-V278-V280-2026-09-02.md`.

## 4. The lane-change ring — `LANECHANGE-V278R3-2026-09-02.md`
- Both operator examples anchor (unix = mono + 1788366773.363 s from GPS; route t0 = 09:33:26 PDT): 09:39:25 → t 358.5 seg 5, left lane change at
  27–28 m/s, ring 358.2–359.2 s at 7.45 Hz, 14.6 deg/s, 5.8° swing, cmd peak 849 (idx 52), driver torque 1736 raw (below the cliff); T 17 % of rail,
  damping 0.31; cmd-vs-rate coherence 1.00 at +35°. 09:42:41 → t 554.5 seg 9, right lane change at 20 m/s, two rings 7.3 / 9.1 deg/s at 8–9 Hz.
- Gated on `modelV2.meta.laneChangeState`: 11 windows; **every hands-light lane change ≥ 17.7 m/s rang (6/6)** at 7.0–7.8 Hz; the one that did not
  was hand-steered above the cliff; four are low-speed blinker turns (r31's regime). Three r33 episodes ring during plain lane keeping at 25–30 m/s.
- V112 (r22) 0 episodes in 78 s of highway; stock (r97) one 19.5 Hz event. At matched speed/|cmd| the 4–8 Hz rate power is 20–45× V112's.
- **The 0xE4 command carries the line at coherence 1.00**, ringing at 25–40 % of the excursion peak, while desired lateral accel is flat.
  openpilot's block (H1 cmd/angle at 7.8 Hz: 866/875/635/792 counts/deg on r32/r33/V112/stock), tune (friction 0.212, LAF 1.689) and commit
  (75577ecf) are identical. The EPS block (rate/cmd) is what differs: 0.27–0.47 vs 0.23 (V112) vs 0.11 (stock). Nothing railed anywhere.
- Verdict: EVIDENCE for the wire; BELIEF by elimination that it is the outer loop's magnitude at the column's ~7.5 Hz resonance.

## 5. Plant and margins — `LOWCMD-LOOPGAIN-…` A1–A6
Plant G = rate/T from the tap (cmd-instrumented, coh 0.7–0.9), highway hands-light: 21/35/41/53 ×10⁻³ deg/s per count at 2/4/6/8 Hz with
+14/0/−12/−19° — stiff, below resonance. **Inner loop:** crossover 13–15 Hz, PM ~50°, no −180° below 15 Hz on the highway; only the stalled
high-angle regime is near the edge (PM ~15° near 9 Hz = the 7 Hz stutter). **Outer loop** (BELIEF: K_op = 4096·[(0.6+0.15/s)/2.196 + 0.212/0.3],
friction = 72 % of it; kinematic vehicle, v²): |L| at 2 Hz, 24 m/s = V112 0.51 / rev 3 1.02 / V280 1.10; PM 96° / 70° / 73°; a generic 1.2 Hz yaw
mode gives GM 1.29× / 0.64× / 0.59×. Unity at 2 Hz near 34 / 24 / 23 m/s. **In the lane-change regime the measured idx is 2–12 (first map segment,
slopes 2.0 / 4.0 / 4.33), so rev 3 and V280 are within 8 % — V280 neither fixes nor much worsens this vs rev 3.** The 1.8× V280/rev 3 factor lives at
idx 24–58 only.

## 6. The strong-turn ripple — `HIGHANGLE-r32-r33-2026-09-02.md`
7 F7 episodes (6.5–7.4 Hz) at |angle| ≥ 30°, all with the wheel MOVING at 0.6–1.2× the new reference, mid-command (idx 26–173), P linear 62–79 %,
D rail ≤ 0.06, fb clamp ≤ 0.02, no output cap, cliff grazed 2–11 %, saturation 0.000. Stalled class 0 of 7 (r31: 7 of 10). A 14 s stall (r33 t 250–264,
P railed 0.77–1.00) rippled 0.02–0.03 — deep P saturation does not ripple, on the car. Episodes per 100 s 9.8 → 8.1 / 4.3, amplitude held. Open-loop,
Kd = 0 changes nothing and Kp × 0.5 RAISES ripple/level: a closed-loop crossover limit cycle. Next levers: the Kp LERP at idx 68–136, or D as phase lead.
Full-demand rate 125/150 & 123/142 deg/s (93 % of 133.6). Prereg: (i) 0.03 PASS · (iv) PASS · (vi) 0.37 PASS · (viii) PASS · (iii) marginal · (v) borderline · (vii) open.

## 7. What to do next
1. **No build:** lower SteerFriction 0.212 → ~0.08 (and/or halve SteerKP) on the build on the car; repeat hands-light lane changes at 25–30 m/s.
   Read with `lanechange_windows.py`: ring count over lane-change windows (now 6/6) and 4–8 Hz rate power at matched speed/|cmd| (now 210–320 vs V112 7–10).
   Softens → the outer loop is confirmed; keep the linear map and size the openpilot tune against the outer margin. Survives → the verdict is wrong;
   the map's X 0–12 segment comes down (convex map: stock slope to idx ~60, ×6 top).
2. The inner-loop ripple needs a drive-based lever (Kp idx 68–136 or D lead) — with its instrument on the wire (the tap already is).
3. Record the operator's confirmation of what was flashed before r32.

## Files
`rlog-tools/studies/osc-highangle/`: `LANECHANGE-V278R3-2026-09-02.md`, `lanechange_{osc,loop,chain,windows}.py` + txt/json, `HIGHANGLE-r32-r33-2026-09-02.md`,
`strongturn_r32_r33.py`, `HIGHANGLE-r32.txt`, `HIGHANGLE-r33.txt`. `analysis-2020accord/studies/v280/`: `LOWCMD-LOOPGAIN-V112-V278-V280-2026-09-02.md`,
`lowcmd_loopgain_v112_v278_v280.py`, `plant_id_v278r3_tap.py`, `V268-DAMPER-DELTA-AT-HIGHWAY-2026-09-02.md`, `v268_damper_delta_highway.py`.
Caches: `analysis-2020accord/_scratch/cache/v280/r32.npz`, `r33.npz`. Memories: `accord-lanechange-ring-is-the-outer-loop-…`, `feedback-attribute-the-build-from-the-tap-…`.

## 8. ADDENDUM 2026-09-03 — the StarPilot tune, back-calculated (operator: "I am suspicious of the recommended steer friction")
Convention from now on: **"openpilot" = StarPilot, the normal one on branch `Dom`** (`openpilots/StarPilot`, HEAD 3d4c625de), not the operator's fork.
Toggles decoded from `analysis-2020accord/reference/toggle-backup(2).json` (XOR key + base64, `the_galaxy/utilities.py`): ForceTorqueController ON,
**ForceAutoTune ON**, Steer* all stock (KP 0.6, friction 0.2120, LAF 1.6893), SteerDelay 0.2, NudgelessLaneChange ON. Studies: `analysis-2020accord/studies/optune/`
(`STARPILOT-DOM-TORQUE-MATH-2026-09-02.md`, `BACKCALC-LAF-FRICTION-2026-09-02.md` + scripts).
- **What the controller used (EVIDENCE, orchestrator-verified on r32 seg 5):** `liveValid` 0 on every tick of r31/r32/r33, filtered = 1.689/0.212,
  −(p+i+d+f)/output = 1.689 at p5/p50. torqued cannot validate on the modded EPS: engaged |torque| p90 0.06–0.12 vs buckets needing |x| up to 0.5;
  `totalBucketPoints` frozen at 6653; its raw LAF ~5.0 is this build's centre + a stale cache — not a measurement. The earlier memory's "raw 4.5–5.2
  clipped to 2.196" is corrected: nothing was applied.
- **The law (EVIDENCE, source):** T = [kp·e' + I + FF]/LAF + friction·sat((e' + 0.22·j_f)/0.30); kp = SteerKP 0.6 flat, ki 0.15, kd 0; m from the steering
  angle via the vehicle model; friction term LAF-independent; FRICTION_THRESHOLD 0.30 m/s². Small-signal Gc = (kp+lsf)/LAF + friction/0.30 (friction 64 % at 25 m/s).
- **The car (EVIDENCE, IV fits lag 0.2 s, closed-loop caveat):** V280 rev 2 lat-accel/torque 8.3–9.4 (|P| 11/5/2.5 at 0.1/0.3/1 Hz — integrator-like, the EPS
  is a rate servo), hysteresis half-width 0.013–0.030 tq (coulomb ~0). Stock 1.13 / 0.116; V112 6.0 / 0.054. The live 0.212 friction kick = 868 counts = 1.8× the p90 command.
- **Back-calculated:** friction ≈ 0.025 (the measured deadband; the asserted 0.08 was 3–4× the car) → Gc 0.43×; with SteerLatAccel at the toggle max 2.53 → 0.32×;
  the true LAF 5–10 needs `torque_data/params.toml` (re-bases torqued's caps and the toggle range). torqued's caps are outside the car in both parameters, so
  auto-tune can never reach it: **ForceAutoTune OFF, then SteerFriction ≈ 0.025–0.03 and SteerLatAccel 2.53.** BELIEF: the Gc ratio carries to |L(7.5 Hz)|.
  Predicted outer |L| at 2 Hz, 24 m/s: 1.10 × 0.32 ≈ 0.35 (V112 sat at 0.51). Instrument for the drive: `lanechange_windows.py` ring count (now 6/6) and 4–8 Hz rate power.
