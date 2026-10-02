# DESIGN V299 — D3 AUTHORITY-FIRST (2026-10-02)

**Status: DESIGN ONLY.** No image built, nothing flashed or sent, the fork was not touched. Ghidra was used read-only
(`disassemble_bytes dry_run` on `ADVIG_V298_177abf04.bin`; function bounds and callers on `code.bin`); nothing saved.
**Author:** designer D3 (authority-first), a SUBAGENT in the V299 judge panel. **Labels:** EVIDENCE = image bytes,
route-79 caches, or an executed common scorer (method named); BELIEF = a model or an inherited record.
**Scripts** (all under `analysis-2020accord/studies/angle_loop/v299_design/D3-authority-first/`; outputs in
`_scratch/angle_loop/v299-D3/`; wall times measured): `d3_common.py` (V298 cells read from the image and asserted),
`d3_gate2.py` (gain-headroom scan, 21.6 s), `d3_gate2_final.py` (GATE 2 on the exact D3 table + op-points, 17.9 s),
`d3_time.py A` (goal criteria, panel-2 common time scorer, 13.1 s), `d3_time.py B` (hands-off turns through a fork
model with the reaction twist, 8.2 s), `d3_r79.py` (route-79 counterfactuals, 5.4 s), `d3_h1.py` (the patched cave
bytes executed by the kit's V850E2 interpreter, 6.4 s), `d3_scl_census.py` (rail-cell consumers, 0.5 s).

---

## 0. The answer on one page

**What "6×" is in this architecture (EVIDENCE: image reads).** The lane's output clamp OCL `0xC61B4` is **512 in stock
`code.bin` and 3072 in V298**, and the forward gain `0xC6CD0` is 5346 (stock 891 per the record; the stock dump's cell
reads 0xFFFF here because the cal moved in the V57 migration). Both are ×6.000. With SCL 15360 the lane's rail is
**2462 T = 307.8 tap LSB** (stock about 410–417 T, from the record's fwd 891). So "6×" is **a ceiling on lane torque**. It is not a gain. It does not
multiply angle rate, acceleration or jerk. Those are set by:
- the setpoint the fork allows: a 120 deg/s cap, a 3.589 m/s³ VM jerk limit, and the error clip;
- the loop's stiffness and damping, which GATE 2 bounds;
- the plant's own damping: b ≈ 5 T per deg/s at low speed, so a 300 deg/s slew alone needs about 1500 T.

On route 79 the tap peaked at **183 LSB (59 % of the rail)** and the wheel at about 140 deg/s.

**What is reachable (EVIDENCE: the time scorer, BELIEF: its plant and twist models).** A hands-off 90° turn at 3 m/s
against a 300 deg/s planner gives:

| | wheel peak | time to 90 % of the turn | tap peak | max lag |
|---|---|---|---|---|
| V298 + V298 fork, sim | 127–130 deg/s | 1.07–1.13 s | 117–123 LSB | 66–68° |
| D3 (a), sim | 245–261 deg/s (about 2×) | 0.56–0.58 s (the plan's own is 0.37 s) | 181–187 LSB (59–61 % of the rail) | 37–39° |

The 6× lane allows roughly 350–400 deg/s before the rail binds. Getting there would need cap 450, clip 40 and the full
D-cancel. That buys about 5 % more rate for 2–3× the overshoot (§3.3).

**Four findings decide this design. Each one moved the design away from "turn the gains up".**
1. **Stiffness is nearly exhausted by GATE 2** (EVIDENCE: `d3_gate2.py` on the independent refuter model `c3r1_model`
   that cleared V298). The largest G multiplier that passes every gated member, frame and hold age is:
   - **×1.25 at ≤ 8 m/s and ×1.0 above.** The ms_free family binds at 9–30 m/s; b_lo×J_hi binds at low speed.
   - Raising Kd to 64 buys ×1.5 at ≤ 6 m/s, but moves |L(20 Hz)|/V295 from 0.96 to 1.28. That breaks the goal's
     20 Hz bar.
   - A flat ×1.2 at the 8 m/s knot fails the **operating-point** GATE 2 on a credible member (b_lo×J_hi @ 8 m/s,
     a_lat 2.5: PM 25.5 against a bar of 30).
   - **D3 therefore raises G by ×1.20 at 3.1 m/s, tapering to ×1.00 at 8 m/s.**
2. **The rail never binds** (EVIDENCE: the time scorer, D3a against D3b). The rail-raised build delivers the same tap
   to ±1 LSB in every planner-driven case, and +18 LSB at most with cap 400 deg/s, clip 40° and the P clamp raised.
   The binders are the fork's error clip, the D brake on the measured rate, and the plant's damping. **(b) is
   specified (§2.2) and not recommended.**
3. **The reaction twist grows with authority, and V298's thresholds sit inside it.**
   - EVIDENCE, r79: the hands-off |gp-0x4f68| p99 is 879 / 755 at 0–5 / 5–8 m/s. It rises 0.40 per deg/s² of |α|.
     It crosses 300 / 512 / 800 / 1229 at **382 / 199 / 65 / 0 per minute** of hands-off turning below 10 m/s.
   - BELIEF, sim: a faster slew raises the twist peak to 1000–1230.
   - So **the D3 firmware with V298's fork trips O1 on the twist** (sim: O1 on for 0–120 ms per turn at ≤ 8 m/s; the sent setpoint's 4–8 Hz content rises 3–5×).
   - **Authority and the override/freeze thresholds must move together.** That coupling is the core of this design.
4. **A rate-qualified freeze (no freeze while the wheel moves toward the setpoint) is REJECTED on real data**
   (EVIDENCE: `d3_r79.py`). Under O1 the setpoint leads the wheel, so a real hand steering a turn is "moving toward the
   setpoint" on 83 % of its frames. The I would wind under real hands: real-hand freeze coverage falls from 0.997 to
   0.174. **Raising the thresholds keeps 0.988.**

**The recommendation: implementation (a).** It is **8 cave bytes + 1 version byte + 1 CRC trailer, with no new
instruction, no relink and no new RAM**, plus five fork changes, each behind a param.

| layer | change | loop term | evidence |
|---|---|---|---|
| fw (cave immediate) | hard hand freeze 512 → **1229** (= Honda steeringPressed 1200 raw × 1.024) | I keeps integrating on the hands-off twist | r79: hands-off hand-freeze duty 0.073 → 0.003; integration discarded below 8 m/s 0.278 → 0.029; real-hand coverage 0.997 → 0.988 |
| fw (cave immediate) | opposing freeze 300 → **800** | same; real opposing hands above 800 still freeze | r79 crossings 382 → 65 /min |
| fw (cave table) | G row 0: 1178 → **1414**, slope 1041 → 185 (×1.20 @ 3.1 → ×1.00 @ 8.0 m/s) | P and I stiffness +20/+11/+7/0 % at 3.1/5/6/8 m/s | GATE 2: 0 fails, worst margin +7.3°, op-points 3–8 m/s 0 fails |
| fw (version) | F181 `A16A` → `A16B` | attribution | — |
| fork K1 | rate cap 120 → **300 deg/s ≤ 5 m/s, 200 @ 8, 120 ≥ 10**; clip 17 → **30°** @ 3.1, 15.5 → **25°** @ 8 | setpoint authority | wheel ×1.9–2.0 (sim) |
| fork K2 | O1 600/500 → **1200 for > 100 ms, or > 2500 at once; OFF 1000** | stops the twist relay; override at Honda's threshold | r79: 415 → 39 episodes, 345 → 0 twist trips, latency p50 80 / p90 100 ms |
| fork K3 | **D-cancel lead**, gain 0.5: the setpoint gets + 0.5·τ_D(v)·ṡ, τ_D = c_D/c_P(v) ≈ 0.036 s ≤ 8 m/s | half of the D brake on commanded motion moves to P | wheel 212 → 252 deg/s (sim) |
| fork K4 | after an O1 release, re-slew at 120 deg/s for 0.5 s | keeps V298's release feel | BELIEF (not simulated) |
| fork K5 | accept `39990-TVA,A16B` | interlock | — |

**Predicted against today, compared like with like** (EVIDENCE for the replay and the sims as computed; BELIEF for
the closed-loop truth):
- **Route-79 replay, open loop, the tap on the recorded errors.**
  - Peak 199 → **257** LSB (measured 183).
  - Engaged p99 119 → **161**.
  - Hard hands-off p99 165 → **217**.
  - 0 frames ≥ 300 and 0 SCL clamp.
  - This over-states a stiffer loop, which would have closed the errors faster.
- **Sim, hands-off big turns** (D3 against V298 in the same manoeuvre):

  | speed | tap peak (LSB) | wheel rate (deg/s) |
  |---|---|---|
  | 3 m/s | 181–187 against 117–123 | 245–261 against 127–130 |
  | 5 m/s | 181–185 against 123–127 | 193–200 against 100–104 |
  | 8 m/s | 149–159 against 101–108 | 154–165 against 76–81 |
  | ≥ 17.5 m/s | unchanged (fork VM jerk cap; firmware identical ≥ 10 m/s) | unchanged |

---

## 1. Mechanisms addressed

| # | mechanism (r79 evidence) | measured on r79 | D3 lever | D3 predicted | method |
|---|---|---|---|---|---|
| M1 | Hand-on yield by design during intersection turns: O1 + fade ×0.30 + I frozen. The hard manoeuvres were hand-steered. | O1 on 63.8 % of hard time. 70 pressed episodes = 86.9 s. 345 twist trips = 12.3–13.8 s. | K2: O1 at Honda's 1200 (persistent) | Twist trips 345 → **0**. A light hand (600–1200) no longer makes the system yield: the lane keeps its plan with fade ≥ 0.85. A firm hand (> 1200, or > 2500 instantly) yields as before. | EVIDENCE `d3_r79` §2 |
| M2 | The firmware's slew follow-up: D on the measured rate brakes 43–62 LSB while P gives 30–45. The wheel runs 5–8° behind a 120 deg/s setpoint. | Cap runs: wheel 0.37 of the setpoint travel, error p50 5.5–7.7°, tap 14–97 LSB | K3 lead (half D-cancel) + G ×1.2 at ≤ 5 m/s | max lag 66 → **37°** at 3 m/s; t90 1.07 → **0.56 s** | EVIDENCE `d3_time B` (sim) |
| M3 | The fork's 120 deg/s cap. 73 % of it is the re-slew after an O1 release. | Binds on 17 % of hard time (50 % of hands-off hard time) | K1 cap 300 ≤ 5 m/s; K4 keeps 120 for 0.5 s after a release | Wheel peak ×1.9–2.0 | sim |
| M4 | The integral discarded by the hand freezes firing on the twist (the ratchet's measured mechanism, stall-surge enrichment near \|bar\| 300/512) | 27.8 % of integration discarded below 8 m/s. Freeze duty 7.3 % hands-off. Effective c_I 1.0–1.2 /s below 8 m/s. | Thresholds 1229 / 800 | Discarded **2.9 %**, duty **0.3 %**; effective c_I/c_P below 8 m/s ≥ 2.3 /s (BELIEF) | EVIDENCE `d3_r79` §3, integer replay |
| M5 | The error clip as the next binder: P ≤ 35–40 % of the rail below 8 m/s | Demand beyond the clip on 49–55 % of hands-off hard frames below 8 m/s | K1 clip 30° / 25° | P cap 36 / 40 → **75 / 65 %** of the rail at 3.1 / 8 m/s (+ lead ≤ 0.5·τ_D·cap ≈ 11° → P clamp = rail) | arithmetic, image cells |
| M6 | The A3 low-speed I cap of 4096 S (27 % of the rail) | I at A3 on 7.6 % of manoeuvre frames | **Unchanged** (deliberately) | Raising it to 8192 (variant X8192) adds **+8 to +12° turn-in overshoot** at 3–5 m/s (sim), while 4096 S already covers the 90° hold at 3 m/s (spring ≈ 3437 S) | EVIDENCE `d3_time` A/B |
| M7 | The rail | Peak 59 %, 0 frames ≥ 250 | (b) only | Not binding (finding 2) | sim |

---

## 2. Implementations

### 2.1 Implementation (a): gains and bounds only, rail untouched (RECOMMENDED)

**Firmware bytes.** EVIDENCE: the byte diff and the cave sha come from `d3_h1.py`, built from the V298 image (sha
`177abf04…`). The instruction decodes are Ghidra's dry run of `0xC4C00..0xC4CD9` on `ADVIG_V298_177abf04.bin`.

| addr | V298 | new | instruction / cell | loop term |
|---|---|---|---|---|
| `0xC4C64` | `00 02` | `cd 04` | imm16 of `movea 0x200,r0,r13` @0xC4C62 → `movea 0x4CD` | hard hand freeze: \|gp-0x4f68\| > 1229 (`bh` @0xC4C68, unsigned on `ld.hu`) |
| `0xC4C6C` | `2c 01` | `20 03` | imm16 of `movea 0x12c,r0,r13` @0xC4C6A → `movea 0x320` | opposing freeze: \|tq\| > 800 and sign(gp-0x4f60) ≠ sign(E′) (`bnh` @0xC4C70, `xor`/`blt` @0xC4C76) |
| `0xC4CDC` | `9a 04` | `86 05` | table row 0 G (u16) 1178 → 1414 | G(v ≤ 3.1 m/s) ×1.20 |
| `0xC4CDE` | `11 04` | `b9 00` | table row 0 S (i16) 1041 → 185 | G walks 1414 → 1465 at X 1843 (×1.00 @ 8.0 m/s); rows 1–6 byte-identical |
| `0x1310D` | `41` | `42` | F181 `39990-TVA,A16A` → `…A16B` | the fork interlock and attribution |
| `0xC4FFC` | trailer | recomputed | main-block CRC [0x13000, 0xC4FFC) | — |

The cave keeps its 260 B, sha `ef1861e1…` → `83b9799b…`. No other block changes. The cal and record blocks are
untouched: Ki 40, ICL 8192, Kp 112, Kd 48, A3 (sh 4/6, B 1250, vcap 1382, cap 4096), SCL / PCL / OCL.

**Integer-exact mirror.** This is design §1.4's `c3rev2p_tick` with D3's three constants. The executed cave is checked
against it by `d3_h1.py`.

```python
GB_D3 = ((714, 1414, 185), (1843, 1465, -6264), (2304, 760, -2033), (2707, 560, 1570), (4032, 1068, 2118),
         (6198, 2188, 0), (0xFFFF, 2188, 0))                       # @0xC4CDA, 7 x (X u16, G u16, S i16)
G  = walk(GB_D3, v6a5e)                                             # v <= X0 -> G0 ; else G(i) + ((v - X(i)) S(i) >> 12)
Ep = s32(E * G) >> 8                                                # 0xC4C54 mul ; 0xC4C58 sar 8
frozen = tq4f68 > 1229                                              # 0xC4C62 movea 0x4CD ; cmp r13,r8 ; bh FRZ
if not frozen and tq4f68 > 800 and (s16(tq4f60) ^ Ep) < 0:         # 0xC4C6A movea 0x320 ; bnh ; ld.h ; xor ; blt FRZ
    frozen = True
# ... A3 bound, ramp freeze, Ki 40, ICL 8192, P = (Ep*112)>>8 (PCL 15360), D = (48*abe)>>3 (DCL 10240): V298 unchanged
```

**H1** (EVIDENCE: `d3_h1.py`; the flight cave executed by `nl_cave.Cpu` + `score_time.Cpu2` against
`CandLane.cave_stage`):

| run | valid rate | rate-invalid op-skip → 0x2A164, no RAM written | camera r25 = 0: inert exit |
|---|---|---|---|
| D3 bytes against the D3 mirror | **0 / 5748** | **0 / 5516** | **0 / 736** |
| control: V298 bytes against the V298 mirror | 0 / 712 | — | — |
| negative control: either cross pairing | **244 / 712 mismatches** | — | — |

The negative controls show the check can fail.

**GATE 1.** No RAM word is added and no store is added. The cave still has zero `st.*` (re-asserted by H1: no RAM
written on any path). The I state gp-0x6dd0 keeps its two Honda writers. No new reads.

**Fork changes** (Dom, on the operator's fork; each gated by a new param that defaults to V298 behaviour; code
required; once the code is in, a Galaxy toggle config expresses the whole set):

| id | file / function | the diff in words | param | toggle config |
|---|---|---|---|---|
| K1 | `honda/values.py` + `carcontroller.py` `_update_angle` | Add `ANGLE_RATE_BOOST_BP = [0, 5, 8, 10]`, `_V = [3.0, 3.0, 2.0, 1.2]` deg/frame. Set `MAX_ANGLE_RATE = 3.0` and clamp the limiter's step by `interp(v, BP, V)` after `apply_steer_angle_limits_vm` (the VM jerk limit still applies and binds above about 9 m/s). `ANGLE_ERROR_MAX_V` becomes [**30, 25**, 19.5, 17, 8.5, 4.5] when the boost is on; the highway knots are unchanged (untested on r79). Update the values test to accept both tables. | `AccordAngleRateBoost` (bool) | yes, once the code exists |
| K2 | `carcontroller.py` `_update_angle` | Count frames with \|steeringTorque\| > 1200. O1 turns on when the count > 10 **or** \|τ\| > 2500. It turns off at ≤ 1000. The count resets below 1200. | `AccordAngleO1Stock` (bool) | yes |
| K3 | `carcontroller.py` `_update_angle` | `ṡ = (apply − apply_last)/DT_CTRL` → first-order filter, 30 ms. `lead = clip(g·τ_D(v)·ṡ_f, ±g·τ_D(v)·cap(v))`. τ_D(v) = 4.532 / c_P(v), and c_P(v) = 160·G(v)·112/65536·0.16029 T/deg from the A16B table copied into `values.py` (0.0732 / 0.0721 / 0.0706 s at 3.1 / 5 / 8 m/s; 0.136 @ 10; 0.185 @ 11.75; 0.097 @ 17.5; 0.047 @ 26.9). `lead = 0` under O1 and for 0.3 s after a release. raw = floor(−10·(apply + lead) + 0.5). **carOutput keeps `apply`**, so the lead is −raw/10 − co_ang on the wire. | `AccordAngleLeadGain` (float, default 0.0, D3 = 0.5) | yes |
| K4 | `_update_angle` | For 0.5 s after an O1 release, the rate limit is 120 deg/s (V298's). | under K1 | yes |
| K5 | `honda/values.py` | `HONDA_ACCORD_EPS_ANGLE_LOOP_FW` accepts `39990-TVA,A16B`. | — | no (one line of code) |

**Instruments.** No new state word, so no new bit. Every edit is read from signals already on the wire or in the
fork log; the instrument repairs of C13 come first.
- **I1. P stiffness per band.** The tap regression on (raw − 10θ), with the corrected dir-2 ramp and the +10-tick timing
  (C13). Image arithmetic: P slope **7.74 / 7.84 / 7.90 / 8.01** tap/deg at 3.1 / 5 / 6 / 8 m/s (V298 6.45 / 7.05 / 7.37
  / 8.01). V298 delivered 0.93–0.96 of its arithmetic.
- **I2. The freeze rule.** Replay the lane on the flight's wire inputs under both rules (512/300 against 1229/800) and
  compare R² against the tap in hands-off windows whose |bar| visits 512–1229. M3's method separated rules at R² 0.93
  against 0.44 on r79.
- **I3. Effective c_I/c_P below 8 m/s, hands-off.** Predicted ≥ 2.3 /s. V298 measured 1.0–1.2.
- **I4. The fork terms.**
  - The lead is −raw/10 − co_ang.
  - O1 is reconstructed with the K2 rule and checked against co_ang on 100 % of frames (the refuter's method).
- **I5. Authority.** Over hands-off hard frames, compare against r79:
  - the tap p99 (r79 135 LSB);
  - the wheel rate p99 (r79 140 deg/s);
  - t90 and max lag of each hands-off turn-in.
- **What a null licenses.**
  - *If a hands-off 60–90° turn-in at ≤ 5 m/s shows the sent setpoint slewing above 250 deg/s while the wheel peaks
    below 160 deg/s, the authority did not arrive.*
  - *If c_I/c_P below 8 m/s stays at 1.0–1.2 and the 512/300 replay still wins I2, the threshold bytes are not live, or
    the twist exceeds 800/1229 at the new authority.* Either is a decisive read from one episode of hard hands-off
    turns, about 15–30 s.

### 2.2 Implementation (b): the rail raised, every consumer enumerated (SPECIFIED, NOT RECOMMENDED)

(b) is (a) plus the following. The fork for (b) uses cap 400 deg/s ≤ 5 m/s and clip 40 / 30° at 3.1 / 8 m/s, so P can
reach the raised clamps.

| addr | V298 | (b) | cell | why |
|---|---|---|---|---|
| `0xC61BE` | 15360 (`00 3c`) | **19072** (`80 4a`) | SCL, the PID-sum clamp | rail 2462 → **3057 T** (99.5 % of OCL 3072; tap ≤ 382 LSB) |
| `0xC61BC` | 15360 | **19072** | PCL, the P clamp | P alone could never pass the old rail otherwise |
| `0xC6FFC` | trailer | recomputed | cal-block CRC | — |

**Consumer census.** Rows are EVIDENCE unless marked.

| consumer | evidence | result under (b) |
|---|---|---|
| SCL readers | Python LE scan `d3_scl_census.py`: 8 loads, **0 stores, 0 literal addresses**. 4 at `0x2A13E–0x2A156` in the live lane `FUN_00028ea6` (Ghidra: called by `FUN_0002214a`). 4 at `0x2B024–0x2B03C` in `FUN_0002a93a` (0 callers in Ghidra, 0 function-pointer literals). | Only the live sum clamp changes. `ld.h` @`0x2A146` sign-extends: 19072 < 32768 is safe (the record's sign-extension defect). |
| PCL readers | 7 loads: 4 live `0x29E3A–0x29E58`, 3 in the uncalled twin `0x2AD2C–0x2AD44` | Only the live P clamp changes |
| OCL `0xC61B4` = 3072 | 8 loads (`0x2A1F8–0x2A21C` lane output, `0x2A910–` the uncalled `FUN_0002a892`); unchanged | 3057 < 3072: OCL never binds. **A rail above 3072 is impossible without OCL** |
| forward clamp ±3072 `0x2B42A–0x2B45C` and the plausibility monitor `FUN_0002b57a` (record `0x434E`, ±3.0 ± 0.003) | inherited V295 ADV-D | The value is clamped to ±3072 before the monitor, so the monitor cannot trip (BELIEF on the inherited trace) |
| reversal detector `FUN_000428d4` (\|gp-0x6c2c\| beyond 12800) | inherited | Range not relevant. It watches the motor-rate derivative; the lane bound rises 2462 → 3057, still 4.2× below 12800 (BELIEF) |
| soft-EME integrator `gp-0x3570` (excess of \|cmd\| above max(corridor, IIR, **5120**)) | inherited V293 D1 | **NOT CLEARED.** The lane plus base assist can now enter 5120 < \|cmd\| ≤ ~5900, above V293's 5325. **A replay of the integrator on r71b/r79 inputs is a (b) prerequisite.** |
| governor slots / lockstep | inherited: governor slots MIN-fold scales; the aggregator lockstep compares RAM, value-independent | unchanged (BELIEF) |
| 0x1AB tap (±511×8) | packer bytes | holds 3057 (382 LSB) |
| override effort | arithmetic | The hand must beat 3057 T instead of 2462 (+24 %) before the Honda fade. At \|bar\| 2289 (×0.30) the residual is 917 T instead of 739. |

**(b) predicted** (sim, EVIDENCE as computed). With the (b) fork, D3b against D3a with the same fork:
- tap 203–233 LSB against 203–222, at 3–5 m/s and 300–450 deg/s plans;
- wheel 297–308 deg/s, the same as D3a.

The extra rail is **reached on 0 ms** of every case. Even the most demanding case gains ≤ 18 LSB: the heavy member at a
450 deg/s plan and 3 m/s.

**Verdict:** (b) costs override effort, an open soft-EME census and two cal cells for no measured benefit. Build it only
if a flight of (a) shows the tap ≥ 290 LSB on more than 1 % of hands-off hard frames.

---

## 3. GATE 2 and the time criteria (run; wall times above)

### 3.1 GATE 2: θ = 0 and operating points

Model and set:
- **Model:** `c3r1_model`, unchanged; it is the model V298 was cleared on.
- **Grid:** 96 speeds from 1.0 to 10.5 m/s; D3's table equals V298's at ≥ 10.0 m/s.
- **Members:** 19 = SINGLE + COMBINED, including the ms_free products.
- **Frames, ages, states:** 5 frames, hold offsets e ∈ {−1, 0, 10}, PID and PD (I frozen).

| | V298 | **D3 (a)** | D3-flat ×1.2 (rejected) | bar |
|---|---|---|---|---|
| θ=0 fails | 0 / 1824 | **0 / 1824** | 0 / 1824 | 0 |
| worst PM margin | +9.1° (b_lo×ms_free @10.5) | **+7.3° (b_lo×J_hi @1.0, FB.83, e10)** | +2.8° (b_lo×ms_free @8.45) | ≥ 0 |
| worst margin by speed 1 / 3.1 / 5 / 8 m/s | +15.3 / +15.3 / +15.5 / +14.0 | **+7.3 / +7.3 / +10.1 / +14.0** | — | — |
| min GM↑ / max 5–30 Hz peak | 13.6 dB / +0.2 dB | **13.4 dB / +0.2 dB** | 12.9 / +1.1 | ≥ 6 / ≤ +3 |
| max \|L(20 Hz)\|/V295 | 0.966 | **0.966** | 0.966 | ≤ 1 |
| op-point GATE 2, 3.1–8 m/s (new range) | 0 fails, min PM 34.0 | **0 fails, min PM 32.3** | **23 fails (b_lo×J_hi 26.8)** | 30 (tier B) / 45 (tier A) |
| op-point GATE 2, 8–10 m/s | 92 fails, all ms_free (declared M-F1) | **92, identical** | 168 (14 non-ms_free: b_lo×J_hi @8 25.5) | — |

**Headroom scan** (`d3_gate2.py`, G×m at fixed Kd 48; worst PM margin over the gated set):

| m | 3.1 m/s | 8 m/s | 9–15 m/s | 17–30 m/s |
|---|---|---|---|---|
| 1.25 | +5.5 | +1.8 | **−0.6 to −4.1** (ms_free) | 17 m/s +2.5; 20–30 m/s −0.4 to −3.8 |
| 1.5 | −2.7 | −7.6 | — | — |

Kd 64 raises the margins at 9–30 m/s (+17 to +26° at m 1; slightly lower at ≤ 8 m/s) but moves |L20|/V295 to 1.28 (the goal fails). Kd 32 fails at 9–15 m/s at
m = 1. **The small-signal loop cannot be the 6×.**

### 3.2 Goal criteria: the common time scorer (`panel2/score_time.py`, its `metrics()`, the 'ff' fork)

Column order is 3 / 5 / 8 / 10 / 11.9 / 17 / 26.9 m/s. Members are nominal and b_lo×J_hi, plus meas = nominal with
r79's Fc.

| criterion | V298 nominal | **D3 nominal** | V298 b_lo×J_hi | **D3 b_lo×J_hi** |
|---|---|---|---|---|
| step settle (s) | 1.08 / 1.05 / 0.25 / … | **0.92 / 0.96 / 0.25** / = | 0.68 / 0.62 / 0.44 | **0.54 / 0.54 / 0.44** |
| step overshoot (%) | 8.9 / 10.0 / 3.2 | **7.9 / 9.6 / 3.2** | 15.2 / 17.8 / 15.1 | **19.3 / 20.7 / 15.2** |
| ±1° 0.5 Hz gain | 0.06 / 0.93 / 1.07 | **0.71 / 1.01 / 1.07** | 1.03 / 1.13 / 1.06 | 1.22 / 1.14 / 1.06 |
| light hand 1000 release lurch (°) | 4.0 / 2.3 / 1.0 | **3.6 / 2.6 / 1.3** | 7.0 / 4.6 / 3.3 | **9.5 / 6.5 / 3.8** |
| light hand 511 lurch | 4.0 / 2.6 / 1.3 | 3.6 / 2.7 / 1.3 | 7.4 / 5.6 / 3.9 | **9.5 / 6.6 / 3.9** |
| firm 2400 lurch | 4.0 / 2.6 / 1.1 | 3.6 / 2.5 / 1.1 | 6.8 / 4.5 / 2.9 | **8.7 / 5.3 / 3.1** |
| co-steer droop / lurch | ≤ 0.28 / ≤ 1.9 | **≤ 1.7 / ≤ 0.2** | ≤ 0.9 / ≤ 2.2 | **≤ 2.8 / ≤ 0.2** |
| hard turn overshoot (°) | 0.4 / 0.6 / 1.3 | 0.4 / 0.6 / 1.3 | 0.5 / 2.2 / 2.7 | **2.9 / 3.1 / 2.7** |
| hard-turn 1.6–3 Hz ratio | 0.70 / 0.75 / 0.72 | 0.81 / 0.82 / 0.72 | 0.80 / 0.92 / 1.01 | 0.93 / 1.04 / 1.01 |

At ≥ 10 m/s every metric is within +0.7° of V298 (the worst is the 511-hand lurch at 26.9 m/s: 0.74–0.86° against 0.17–0.21°, because a light hand below 800 no longer freezes the I). The ≥ 8 m/s bar on the light-hand lurch (≤ 8°) passes. Below 8 m/s
the heavy member rises 7.0 → 9.5° (declared M-D3-2).

### 3.3 Hands-off turns through the fork model, with the reaction twist (`d3_time.py B`)

The table below is at 3 m/s and 90°, member nominal / meas / b_lo×J_hi, with a 300 deg/s raised-cosine planner.

| config | wheel peak | t90 (plan 0.37) | max lag | turn-in overshoot | unwind overshoot past centre | O1 ms | hand-freeze onsets | tap peak | twist peak (BELIEF) |
|---|---|---|---|---|---|---|---|---|---|
| V298 + V298 fork | 130 / 127 / 127 | 1.07 / 1.13 / 1.11 | 66 / 68 / 67 | +0.4 / −0.7 / −1.8 | 7.8 / 7.1 / 9.1 | 0 | 1 | 117 / 123 / 123 | 541 / 578 / 497 |
| V298 + D3 fork | 194 / 187 / 199 | 0.64 / 0.66 / 0.65 | 44 / 46 / 47 | ≈0 | 4.7 / 4.2 / 8.6 | 0 | **4 / 4 / 2** | 167 / 171 / 168 | 877–970 |
| D3 fw + V298 fork | 135 | 1.12 / 1.26 / 1.08 | 78–80 | ≈0 | 7.3 / 6.4 / 9.5 | **80 / 120 / 20** | 1 | 124–129 | 621–660 |
| **D3 (a) = D3 fw + D3 fork (lead 0.5)** | **252 / 245 / 261** | **0.56 / 0.58 / 0.57** | **37 / 39 / 39** | +0.4 / −0.6 / **+2.3** | 7.7 / 6.7 / **15.4** | **0** | **1** | **181 / 186 / 187** | 1041 / 1088 / 1030 |
| D3 fw + full lead (1.0) | 305 / 297 / 312 | 0.48–0.50 | 28–32 | +1.3 / +0.2 / **+7.2** | 10.7 / 9.5 / **20.1** | 0 | 1 | 212–219 | 1239–1607 |
| D3 fw + no lead | 212 / 206 / 220 | 0.66–0.68 | 45–47 | ≈0 | 7.2 / 6.4 / 12.7 | 0 | 1 | 158–164 | 899–995 |
| X8192 (A3 cap 8192; rejected) | 261 | 0.53–0.54 | 37–39 | **+8.2 / +7.3 / +12.2** | 9.6 / 9.0 / 16.0 | 0 | — | 223–227 | — |

The same set at 5 / 8 m/s for D3 (a) against V298:

| speed | wheel (deg/s) | t90 (s) | tap (LSB) | turn-in overshoot | unwind overshoot |
|---|---|---|---|---|---|
| 5 m/s | 193–200 against 100–104 | 0.44–0.45 against 0.79–0.83 | 181–185 against 123–127 | ≤ +2.2° | ≤ 8.1° (heavy member) |
| 8 m/s | 154–165 against 76–81 | 0.30–0.32 against 0.49–0.51 | 149–159 against 101–108 | ≤ +3.0° | ≤ 2.5° |

At 17.5 and 26.9 m/s the change is under 4 %: the VM jerk cap governs.

An asymmetric unwind cap (180 deg/s) was tested and **not adopted**. The unwind overshoot is firmware dynamics (I + the
spring), not the unwind rate: heavy member 14.2 against 15.4°, and 5 m/s got worse.

---

## 4. Route-79 counterfactuals (`d3_r79.py`, EVIDENCE as computed on the caches)

| quantity | V298 (r79) | D3 (a) |
|---|---|---|
| O1 episodes / time | 415 / 100.8 s | **39 / 73.1 s** |
| O1 twist trips (never pressed) | 345 (13.8 s) | **0** |
| O1 recognition latency on real-hand episodes | — | p50 80 / p90 100 / max 250 ms |
| \|bar\| threshold crossings per min of hands-off turning < 10 m/s | 382 (300) and 199 (512) | **65 (800) and 0 (1229)** |
| hands-off hand-freeze duty | 0.073 | **0.003** |
| commanded integration discarded hands-off < 8 m/s | 0.278 | **0.029** |
| real-hand (pressed) freeze coverage, the N1 protection kept | 0.997 | **0.988** |
| replay tap: peak / p99 / p99.9 / hard hands-off p99 (LSB) | 199 / 119 / 156 / 165 (R² vs the wire 0.918) | **257 / 161 / 204 / 217** (open loop, over-states) |
| replay frames ≥ 250 / ≥ 300; SCL clamp active | 0 / 0; 0 | 5 / 0; 0 |
| (b) on the same replay | — | identical to (a) to the LSB |

The rate-qualified freeze is rejected on real hands: real-hand coverage 0.174. Of V298's hands-off hand-frozen ticks,
52 % had the wheel slow (< 6.8 deg/s) and 46 % had it moving toward the setpoint.

---

## 5. Hazards and fail-safe paths

| path | behaviour under D3 (a) | fails safe? |
|---|---|---|
| engage / disengage / bail | No new state word. The I (gp-0x6dd0) and the first-tick sentinel are reset by Honda's epilogue `0x2A164` on every A2/B2/op-skip path (H1: unchanged bytes, 0 / 5516 op-skip mismatches). Fork lead filter: reset when not latActive, under O1, and for 0.3 s after a release. | yes |
| release to the driver | Fork O1 at Honda's steeringPressed level (1200 raw) after 100 ms, or at once above 2500. The firmware's Honda fade is **unchanged** and acts immediately (×0.85 at 1216, ×0.30 at 2289). The hard freeze now sits at the same 1229. A hand of 600–1200 no longer makes the setpoint follow the wheel: **the driver feels the lane hold its plan more firmly under a light hand.** | yes, at the Honda threshold. **Declared feel change.** |
| 0xE4 timeout / sentinel | unchanged (510 ms hold → sentinel → A2 → 0.1 s decay) | yes (= V298) |
| request drop | unchanged (B2 skip, dir-2 ramp-out 0.5 s) | yes |
| real hand, light and opposing (≥ 800) | I frozen (as V298 above 300) | yes |
| real hand, light and aiding (512–1229) | **The I now integrates** (V298 froze it). Error shrinks as the hand helps; A3 bounds the I. Sim lurch at ≥ 8 m/s ≤ 3.9°; below 8 m/s ≤ 9.5° (heavy member). | bounded; declared M-D3-2 |
| wrong or garbage setpoint | P-demand bound c_P·clip rises to 75 % (3.1 m/s) / 65 % (8 m/s) of the rail, plus the lead, and the P clamp = rail. Highway unchanged (16–18 %). | bounded by PCL/SCL (= V298 rail) |
| the twist above 1229 at the new authority | BELIEF sim peak 1030–1230 at 3–5 m/s, so a single freeze or O1 onset per turn is possible. The ratchet could reappear at the higher threshold. | stop criterion F6 |
| D3 firmware flown with V298's fork | sim: O1 trips on the twist (0–120 ms per turn at ≤ 8 m/s) and the setpoint's 4–8 Hz content rises 3–5× (the relay) | **flight prerequisite: K2 live (A16B accepted only with the D3 config)** |
| pol = −1, camera interlock | inherited unchanged (V298's declared prerequisites) | as V298 |

---

## 6. Pre-registered FAIL criteria for one short drive ("do not fly again if …")

The drive: hands-off 60–90° turns at ≤ 8 m/s (an empty lot, or quiet intersections with the hands verifiably off), one
light-hand hold and release, and normal cruising.
- **F1.** A 0.25–5.5 Hz oscillation that grows, or ≥ 4 cycles with ζ < 0.25, at ≤ 8 m/s (R3\*, with the reversal clause
  of C13).
- **F2.** A new 5–30 Hz line (R4), or 18–22 Hz engaged/disengaged > 2.2 (V298 1.83) in the 0–8 m/s bands.
- **F3.** Unwind overshoot past centre > 10° on ≥ 2 hands-off returns at ≤ 8 m/s. Predicted 6.7–7.7°; heavy member
  15.4°.
- **F4.** Release lurch after a light-hand hold > 8° at ≥ 8 m/s, or > 12° below 8 m/s.
- **F5.** Any O1 episode that never reaches 1200 raw, or a real-hand O1 recognised more than 250 ms after \|τ\| > 1200.
- **F6.** Stall-surges enriched by more than 2× within ±0.25 s of an \|bar\| 800 or 1229 crossing. That is the
  refuter's split; it would mean the freeze ratchet moved up instead of away.
- **F7.** \|tap\| ≥ 300 LSB hands-off for > 0.3 s (R2). Not predicted under (a).
- **F8 (null = design failure, revert).** On a hands-off turn-in where the sent setpoint slews above 250 deg/s, the
  wheel peaks below 160 deg/s; **or** I1 shows the P slope at 0–5 m/s within 5 % of V298's; **or** I2 still selects
  the 512/300 rule.
- **F9.** The operator reports stutter or ratcheting, a lurch, or "fights my hands" (R9).

---

## 7. Declared misses

- **M-D3-1.** GATE 2 margin at ≤ 3 m/s falls from +15.3° to +7.3°. Every bar passes.
- **M-D3-2.** Light-hand release lurch below 8 m/s rises in the heavy member (b_lo×J_hi): 7.0 → 9.5° at 3 m/s.
  Co-steer droop rises to ≤ 2.8°.
- **M-D3-3.** Heavy-member unwind overshoot at 3 m/s is 15.4° (V298 9.1°) and turn-in overshoot +2.3°. Nominal and meas
  are unchanged.
- **M-D3-4.** **Small-correction stick (note 4 #2) is not addressed.** With r79's measured friction, ±1° commands do
  not break away at 3 m/s or at 10–17 m/s in the sim, for V298 or D3. That is another designer's lever.
- **M-D3-5.** **Highway authority is unchanged and untested.** The clip, VM jerk cap and firmware are identical at
  ≥ 10 m/s. r79 has 6 s of hard frames above 12.5 m/s.
- **M-D3-6.** The twist model, its extrapolation above |α| 1000, and the plant's b, J and Fc are BELIEF. r79's Fc at
  8–25 m/s (74–94 T) is 3–6× the plant family's. The 'meas' member uses r79's values.
- **M-D3-7.** **Note 3, the indicator, is not fixed by (a).** See the graft in §8.
- **M-D3-8.** The O1 persistence adds ≤ 100 ms (p90) before the fork yields to a real hand. The Honda fade is immediate.
- **M-D3-9.** K4 (release re-slew) and the lead's interaction with the 20 Hz model staircase are not simulated.

## 8. Grafts I would take from the other angles

- **Indicator.** Parse 0x1AB in carstate, without a checksum requirement, because C12 is unresolved. Show
  \|tap\|/307.8 as the angle-mode bar. This makes the new authority visible, and closes note 3.
- **Smoothness / ratchet.** If F6 fires, add a sustained-torque freeze: a debounce counter. That needs one RAM word, so
  GATE 1 applies. It is the only clean way to separate a held hand from a 50 ms twist inside the firmware. Also fix the
  small-correction stick (M-D3-4).
- **Fork-first.** Derive the lead from the planner's desired-curvature rate instead of the limited setpoint, which
  avoids the 20 Hz staircase. Also the planner/clip_curvature limits, if the 300 deg/s cap moves the binder upstream.
- **Firmware-minimal.** Agrees with the byte budget: (a) is 8 cave bytes and adds no code.

---

## Appendix A: variants considered and rejected (all scored, scripts above)

| variant | why rejected (EVIDENCE) |
|---|---|
| G ×1.25–1.5, any speed | GATE 2 θ=0 fails at m 1.5 (≤ 8 m/s) and at m 1.25 (≥ 9 m/s) |
| G ×1.2 flat to 8 m/s | op-point GATE 2: 23 + 14 credible non-ms_free fails |
| Kd 64 (+ G ×1.5) | \|L20\|/V295 1.28 > 1 (goal bar) |
| A3 cap 4096 → 8192 (X8192) | turn-in overshoot +8 to +12° at 3–5 m/s; step overshoot 12.9 % |
| rate-qualified freeze (+16 B cave) | real-hand freeze coverage 0.174 on r79 |
| full D-cancel lead (1.0) | heavy-member overshoot +7.2° / unwind 20°, for +20 % rate |
| asymmetric unwind cap | no reduction in unwind overshoot |
| (b) SCL/PCL 19072 | rail reached on 0 ms in every case; open soft-EME census; +24 % override effort |
