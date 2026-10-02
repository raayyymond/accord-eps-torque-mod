# DESIGN V299 — D5 END-TO-END ARCHITECT (2026-10-02): allocate each fix to the layer that owns it

**Status: DESIGN ONLY.** Nothing built, flashed, sent or committed; the fork was not edited; Ghidra read-only
(`disassemble_bytes dry_run:true` on `ADVIG_V298_177abf04.bin`). Author: designer D5-architect, a SUBAGENT of the
orchestrator's judge panel. Python = `bin_decompile`. **EVIDENCE** = measured on route 79's wire / fork logs, read from
the V298 image (sha `177abf04…`), or computed by a cited script; **BELIEF** = modelled. I score bands; the operator
scores symptoms.

**Scripts** (`analysis-2020accord/studies/angle_loop/v299_design/D5-architect/`; outputs `_scratch/out/v299_D5/`):

| script | what | engine reused | wall |
|---|---|---|---|
| `s1_hands_freeze_o1.py` | twist distribution; freeze-rule and O1-rule counterfactuals; fork limiter on hard windows | `m3_lane`, `m4_common` | 1.6 s |
| `s2_replay_tap.py` | open-loop lane replays vs the 0x1AB tap (control R² 0.927 = M3's 0.928) | `m3_lane` | 2.3 s |
| `s2b_washout_instrument.py` | can the wire see (a)'s washout D | `s2` | 2.4 s |
| `s3_bar.py` | the proposed bar on r79 | `m3_lane` | 3.5 s |
| `s4_closed_loop.py` | closed loop: lane + **fork model** (staircase, i−1, cap, clip, O1, lead) on the panel-2 common engine | `panel2/score_time.py` (CandLane, plant) | 20.9 s (5 procs) |
| `s4b_slew_attrib.py` | one-element-at-a-time attribution of the slew/drift results | `s4` | 10.4 s |
| `s5_gate2.py` | GATE 2 on the panel-2 common frequency scorer (control reproduces SCORE-FREQ C3B-P) | `panel2/score_freq.py` | 23.9 s |
| `s5b_kf_sweep.py` | the largest (a) friction gain GATE 2 allows | `s5` | 13.6 s |
| `s6_check_1ab.py` | is V298's 0x1AB a valid Honda frame (checksum, counter) | rlog seg 6 / 14 | 1.0 s |
| `s7_kick_rate.py` | how often a fork "breakaway kick" would fire on r79's real plan | fork cache | 0.1 s |

---

## 0. The answer in one page

**Architecture rule (BELIEF, the design principle):** *feedback lives in the firmware (1 kHz, torque domain:
stiffness, I, D, freeze); the reference and everything keyed on the driver's intent lives in the fork (it owns the
plan, the 20 Hz staircase, the hand detector at 100 Hz with debounce, the bar).* V298 put a hand detector in BOTH
layers (firmware freeze 300/512, fork O1 600/500), both keyed on a torsion-bar word that the loop's own acceleration
twists hands-off. That duplication is the measured ratchet mechanism. V299 makes the fork the hand detector and leaves
the firmware a backstop at Honda's own threshold.

**PRIMARY = implementation (b), "fork-owned feedforward".** The smallest combined change:

| layer | change | bytes / params | notes addressed |
|---|---|---|---|
| firmware | hard freeze 512 → **1229** (= 1200 raw, Honda STEER_THRESHOLD) | cave imm `0xC4C64` `00 02`→`cd 04` | 4, 2 |
| firmware | opposing-hand freeze 300 → **removed** (threshold 1229, made unreachable) | cave imm `0xC4C6C` `2c 01`→`cd 04` | 4, 2 |
| firmware | F181 `A16A`→`A16B`; CRC `0xC4FFC` recomputed | `0x1310D` `41`→`42` | attribution |
| fork | O1: **immediate at > 1200 raw**, else > 600 raw **held ≥ 6 frames** (60 ms); off ≤ 500 (unchanged) | `AccordAngleOverrideDebounce` 0→6 | 4, 2 |
| fork | rate cap 120 → **250 deg/s** (the VM jerk limit binds above ≈ 6.2 m/s anyway) | `AccordAngleRateCap` 120→250 | 2 |
| fork | error clip at ≤ 8 m/s 17 / 15.5° → **35 / 32°** (unchanged ≥ 10 m/s) | `AccordAngleClipLowScale` 1→2.06 | 2 |
| fork | **lead** τ_L(v)·ω_f: 0.5 × the firmware's own D/P ratio; ω_f = 5-frame boxcar slope (nulls the 20 Hz staircase) + 30 ms pole | `AccordAngleLeadGain` 0→0.5 | 2, 1 |
| fork | **bar** = −(0x1AB lane torque) / 2461 T | `AccordAngleBarFromEps` 0→1 | 3 |

Firmware: **4 bytes in the existing cave + 1 version byte + CRC; 0 new instructions; 0 RAM; the linear loop
byte-identical to V298** (GATE 2 = V298's by identity). Every fork change ships behind a param whose default reproduces
V298, so a Galaxy toggle config turns V299-b on and the existing REVERT config turns it off.

**Predicted numbers (BELIEF unless marked; method in §1/§3/§4):**

| note | measure (r79) | predicted V299-b |
|---|---|---|
| 4 | stall-surges near a 300/512 crossing 80.7 vs 30.3 /min (5–10 m/s), 47.4 vs 8.4 (0–5) | **no hands-off crossing exists** (1108 → 0 crossings/min of hands-off turning, EVIDENCE s1); pooled stall-surge rate falls to the away-from-crossing rate: **≤ 35 /min (5–10), ≤ 12 (0–5)** |
| 4 | freeze duty hands-off 7.2 % (26 % of hands-off hard), integration discarded 17.8 % (27 % < 8 m/s) | **0.0 % / 0.0 %** on r79's wire (EVIDENCE s1: hands-off \|bar\| max 1212 < 1229) |
| 4/2 | O1 episodes 415 (345 twist, 70 hand) | **88** (18 twist, 70 hand; every hand caught, onset +20 ms p50 / +50 ms p90) (EVIDENCE s1) |
| 2 | hands-off 90° turn-in at 3–5 m/s: t90 | **0.90–1.13 s → 0.54–0.65 s**; wheel peak 136–164 → 257–276 deg/s; overshoot ≤ 0.5 % (s4) |
| 2 | 45° at 8 m/s: t90 | 0.53–0.55 → 0.40–0.41 s; 120 → 167 deg/s; overshoot 5.4–5.9 % → 6.3–7.2 % (s4) |
| 2 | tap peak 183 / hard p99 135 LSB | **220–260 / 160–190** on hands-off ≤ 8 m/s turns (sim ratio ×1.19–1.41 applied to r79); unchanged under a hand (yields by design) |
| 1 | closed-loop lag at 0.5 Hz (C8 260–440 ms) | −7 to −26 % (model: 141→105 ms @3.1, 298→243 @10, 399→325 @11.9, 273→253 @26.9) |
| 3 | bar \|corr\| with the delivered torque 0.135, pinned 59.7 % | **0.96–0.97, pinned 0 %** (EVIDENCE: s3 computed on r79's wire with the proposed formula) |
| 4 | dwells/min 4.70/1.16/4.47/3.53 | **≈ unchanged** (stuck fraction ×0.80–0.97 in sim): **declared miss** (§7) |

**Re-asked: is each V298 term still necessary?**

| V298 term | verdict | why (EVIDENCE unless marked) |
|---|---|---|
| opposing-hand freeze \|tq\| > 300 | **REMOVE** | fires on the loop's own reaction: 83.9 % of frozen hands-off frames at \|α\| > 100 have the wheel accelerating TOWARD the setpoint (s1); it is the ratchet's measured trigger (refute). Its N1 job moves to the fork's debounced O1; N1 release lurch is unchanged in sim (≤ 2.6° vs 2.9°, s4) |
| hard freeze \|tq\| > 512 | **RAISE to 1229** | 512 sits inside the hands-off twist (p90 450 / p99 897 at 0–5 m/s; max 1212 anywhere); hands sit far above (pressed p10 1579) (s1). 1229 = the Honda threshold, so the stock-recognised hand still freezes the I |
| A3 θ-bound + 4096 low-speed cap | **KEEP both** | removing the cap gave **+10 % turn-in overshoot at 3 m/s** once the setpoint is faster (s4b `A3cap removed`: +0.103 vs +0.004) |
| Kd 48 (fresh, on measurement) | **KEEP** | it is the loop's damping (GATE 2 PM); its slew drag is cancelled by the fork lead instead. (a)'s washout of D costs +5–6 % turn-in overshoot and +0.5–1° lurch (s4) |
| error clip | **KEEP, re-size ≤ 8 m/s ×2.06** | with the cap lifted it becomes the authority bound (clip binds 8.8 % of hard frames in the recompute, s1-D) |
| 120 deg/s cap | **RAISE to 250** | cap bound on 43.9 % of hands-off hard frames (s1-D V298 recompute; refute 50 %) |
| O1 at 600 raw | **KEEP the level, ADD a 60 ms hold below 1200** | 345 of 415 episodes were ≤ 50 ms twist (refute); deb60 keeps 70/70 hands, fires on 18/345 twists (s1) |

---

## 1. Mechanisms addressed: the measured number each must move, and my prediction

| # | mechanism (owner) | measured on r79 (source) | V299-b moves it by | predicted |
|---|---|---|---|---|
| M1 | freeze toggling at the 300/512 crossings lengthens stalls (firmware) | stall-surges 80.7 near / 30.3 away /min at 5–10 m/s; V282/V294 no enrichment (REFUTE-inference V6) | thresholds above every hands-off \|bar\| (max 1212) | crossings 1108 → 0 /min turning; stall-surge ≤ 35 /min (5–10) |
| M2 | O1 trips on the hands-off reaction twist (fork) | 345/415 episodes, 12.3–13.8 s; 4–8 Hz rate 6.99 near O1 vs 3.06 away (REFUTE-data #18) | 60 ms hold below 1200 raw | 345 → 18 twist episodes; near-O1 4–8 Hz → ≤ 4.1 deg/s (ref band) |
| M3 | post-O1 re-slew under the cap (fork) | 73 % of cap frames in the 0.3 s after an O1 release (REFUTE-data #7) | −95 % of the twist releases | cap-bound hands-off hard frames 43.9 % → 29.7 % (s1-D, open-loop recompute) |
| M4 | rate cap 120 deg/s (fork) | binds 50–53 % of hands-off hard (C2) | 250 deg/s | hands-off turn-in t90 −40 % at 3–5 m/s (s4) |
| M5 | D on the measured rate brakes slews; wheel 4–6° behind yet lane opposes motion on 66–81 % of fast returns (REFUTE-inference 2c) | lane net drive along motion −26 / −37 LSB p50 | lead = 0.5 × D/P: P(τ_L ω_ref) ≈ ½ D ω | t90 −5 to −9 % more (s4b `lead0` vs final), 0.5 Hz lag −7 to −26 % (s5) |
| M6 | P capped by the clip at 35–40 % of rail ≤ 8 m/s (C3) | — | clip ×2.06 | P ceiling 73 % (3.1 m/s) / 83 % (8 m/s) of rail; sim tap peak 179–208 LSB (58–68 %) |
| M7 | bar = a_lat request / 0.3247 (fork UI) | \|corr\| 0.135, pinned 59.7 % (C12) | bar from the EPS's own 0x1AB | \|corr\| 0.97, pinned 0 % (EVIDENCE s3) |
| M8 | small-correction stick (friction vs low small-signal stiffness) | dwells/min 4.70/1.16/4.47/3.53, V282 0.24–0.84 | **not moved** (§7) | ×0.80–0.97 |

Note 2 under a hand: the 116.5 s of hard frames on r79 were hand-steered (steeringPressed 53 %, sd_enabled 0 %).
**V299 keeps yielding under a hand by design** (O1 immediate at > 1200 raw, firmware freeze at 1229, Honda fade ×0.30
at \|bar\| 2289). It will not feel stronger in a hand-steered intersection turn. It is designed to make the hands-off
turn strong enough that the hand is not needed. That the operator grabbed because the system was slow is NOT
supported by r79 (pre-grab gap 16.2° vs 12.9° base, REFUTE-inference 2a); the drive card tests it directly.

---

## 2. The two implementations

### 2(b) PRIMARY — fork-owned feedforward, firmware backstop only

#### 2(b).1 Firmware bytes (read from the V298 image; Ghidra dry-run + Python LE, EVIDENCE)

| id | addr | V298 bytes | V299-b bytes | instruction | loop term |
|---|---|---|---|---|---|
| FZ1 | `0xC4C62` | `20 6e 00 02` | `20 6e cd 04` | `movea 0x200,r0,r13` → `movea 0x4cd,r0,r13` | hard freeze: `cmp r13,r8 ; bh 0xC4CC2` freezes iff gp-0x4f68 > **1229** |
| FZ2 | `0xC4C6A` | `20 6e 2c 01` | `20 6e cd 04` | `movea 0x12c,r0,r13` → `movea 0x4cd,r0,r13` | opposing freeze `cmp r13,r8 ; bnh 0xC4C7A`: reached only when r8 ≤ 1229, so bnh is always taken: **dead** |
| V1 | `0x1310D` | `41` | `42` | F181 `39990-TVA,A16A` → `…A16B` | attribution in carFw |
| CRC | `0xC4FFC` | `f3 d8 7c 6b` | recomputed | main-block trailer (both edits and V1 are in [0x13000, 0xC4FFC)) | — |

Census (EVIDENCE, Python LE scan of the V298 image): `20 6e 2c 01` occurs once (`0xC4C6A`); `20 6e 00 02` occurs at
`0xC4C62` and at `0x6271E` (Honda code, **not touched**). The cave writes no RAM and its read set is unchanged (the
dead branch's `ld.h -0x4f60` stops executing). Cal blocks `0xC6000`/`0xE5000` byte-identical to V298.

**Integer-exact mirror of the changed decision** (the rest is `DESIGN-ANGLE-LOOP-C3-rev2` §1.4 unchanged):

```python
def v299b_frozen(tq4f68, tq4f60, Ep, I8, theta, v6a5e, ramp):          # cave 0xC4C5E..0xC4CC0
    if tq4f68 > 1229: return True                    # 0xC4C62 movea 0x4cd ; 0xC4C66 cmp r13,r8 ; 0xC4C68 bh FRZ (V298: 512)
    if tq4f68 > 1229 and (s16(tq4f60) ^ Ep) < 0:     # 0xC4C6A movea 0x4cd ; 0xC4C70 bnh 0xC4C7A  (V298: 300) -> never true
        return True
    sh = 4 if v6a5e <= 2880 else 6                   # A3, unchanged (0xC4C7A..0xC4CAA)
    bound = (abs(s16(theta)) << sh) + 1250
    if v6a5e <= 1382: bound = min(bound, 4096)       # low-speed cap KEPT (s4b)
    t = (I8 >> 10) if Ep >= 0 else -(I8 >> 10)
    return t >= bound or (ramp & 0x8000) == 0        # 0xC4CB8 bge FRZ ; 0xC4CBC andi 0x8000 ; bne DONE
```

**GATE 1:** no RAM word is added, read or written that V298 did not (EVIDENCE by the decode). **Instrument (inert, on
the wire now):** the 0x1AB tap + the replay. On r79's V298 wire the V298-rule replay scores R² 0.927 against the tap,
and the V299-rule replay 0.128; on the frames where the rules differ (hands-off, 300 < \|bar\| < 500) 0.956 vs 0.400
(EVIDENCE, s2). On a V299 wire the order must invert. That is the attribution test (FAIL F3).

#### 2(b).2 Fork changes (raayyymond-StarPilot / StarPilot, branch Dom; every one behind a param, default = V298)

| file / function | change in words | param (default → drive-1) | toggle config? |
|---|---|---|---|
| `opendbc_repo/opendbc/car/honda/values.py` `CarControllerParams` | add `ANGLE_OVERRIDE_HARD = 1200`, `ANGLE_LEAD_BP = [3.1,8,10,11.75,17.5,26.9]`, `ANGLE_LEAD_V = 89.5/G = [0.0760,0.0611,0.1178,0.1598,0.0838,0.0409]` s (G = GB-P knots 1178/1465/760/560/1068/2188, i.e. the image's D/P ratio, κ 1.155); `HONDA_ACCORD_EPS_ANGLE_LOOP_FW` becomes the set {`…A16A`, `…A16B`} | — | no (constants) |
| `carcontroller.py` `_update_angle` | **O1**: on if \|tq\| > `ANGLE_OVERRIDE_HARD`, or \|tq\| > 600 for ≥ N consecutive frames; off ≤ 500; N = param (0 = V298) | `AccordAngleOverrideDebounce` 0 → 6 | **yes** once the param exists |
| same | **cap**: `dmax = min(jerk-limit, cap/100)` | `AccordAngleRateCap` 120 → 250 deg/s | yes |
| same | **clip**: `ANGLE_ERROR_MAX_V[:2] × s` (17, 15.5 → 35, 32) | `AccordAngleClipLowScale` 1.0 → 2.06 | yes |
| same | **lead**: after the limiter, before the clip, skipped while O1: `sp += g · interp(v, LEAD_BP, LEAD_V) · ω_f`; ω_f = LP30ms((sp_lim[n] − sp_lim[n−5]) / 0.05); history seeded to the measured angle on every latActive rising edge and every O1 release | `AccordAngleLeadGain` 0 → 0.5 | yes |
| `carstate.py` (Honda) | parse `STEER_MOTOR_TORQUE` 0x1AB on the pt bus **only when `EPS_ANGLE_LOOP_FW`**: T = (field & 0x1FF)·8·(−1 if field & 0x200); `ret.steeringTorqueEps = −T` (sign fixed by unit test on r79, see P4) | — | no |
| `selfdrive/ui/onroad/starpilot/torque_bar.py` `TorqueBar._update_state` | in angleState on the Accord angle FW: `bar = clip(steeringTorqueEps / 2461, ±1)` (full scale = the lane rail) | `AccordAngleBarFromEps` 0 → 1 | yes |

The drive-1 config is a Galaxy toggle-config delta (`toggle-config_V299_*.json`) plus its REVERT (all five params
back to the V298 defaults). The fork code itself is a one-time change; with the defaults it is byte-for-byte V298
behaviour (BELIEF until its unit test replays r79's carOutput to 0.000° with the defaults: prerequisite P3).

**The 0x1AB frame is valid (EVIDENCE, s6, segments 6 and 14 of r79):** 6000 frames at 50 Hz, Honda checksum valid on
**100 %** (3587 engaged), the 2-bit counter steps by 1 on **100 %**, CONFIG_VALID 1, OUTPUT_DISABLED 0. Adding it to the
CANParser cannot trip `canValid` on V298/V299 (BELIEF on parser timing: 50 Hz expected rate set in the message list).

**Wire instruments for the fork edits:** each fork term is on the log already: `carOutput.actuatorsOutput.steeringAngleDeg`
minus the limiter recompute of `carControl.actuators.steeringAngleDeg` = lead + O1 + clip exactly (the M2/M4 limiter
recompute reproduces V298 on 100 % of frames). A new `m4_common.limiter_reconstruct` mode with the V299 rules must
reproduce `co_ang` to ≤ 0.01° (FAIL F4 otherwise). The bar is `carState.steeringTorqueEps` (now non-zero).

### 2(a) ALTERNATIVE — firmware-owned friction/D fix

Same as (b) for FZ1, FZ2, V1, O1, cap, clip, bar. **No fork lead.** Instead, in the cave:

| term | where | listing (to be assembled by the two-pass linker; the G-table pointer `mov 0xC4CDA,r9` at `0xC4C1C` and every jr/bcond MUST be relinked — the V298 C3B-P splice bug) | bytes |
|---|---|---|---|
| washout D (D on abe − abe_lp) | after the op-skip guard (label CONT, `0xC4C18`) | `ld.w -0x6c44[gp],r8 ; mov r26,r13 ; shl 16,r13 ; ld.w -0x6cf8[gp],r9 ; addi 1,r9,r9 ; bv SEED ; mov r13,r9 ; sub r8,r9 ; sar 9,r9 ; add r9,r8 ; br ST ; SEED: mov r13,r8 ; ST: st.w r8,-0x6c44[gp] ; sar 16,r8 ; sub r8,r26` | ≈ 40 |
| friction comp, folded into D's operand (D = 6·op enters S with +, like P) | after `0xC4C58 sar 8,r16` (E′), before the camera gate (the camera path zeroes r26) | `mov r16,r9 ; movea 75,r0,r13 ; mul r13,r9,r0 ; sar 12,r9 ; movea 67,r0,r13 ; cmp r13,r9 ; cmovgt r13,r9,r9 ; subr r0,r13 ; cmp r13,r9 ; cmovlt r13,r9,r9 ; add r9,r26` | ≈ 30 |

Cave 260 → ≈ 330 B (free to `0xC4FF0`). **New RAM: one int32, gp-0x6c44 (0xFEDF13BC)** = the first word of V289's
censused 12-byte run (V289 flew with it, r62/r63).

```python
def v299a_op(abe, Ep, st):                         # r26 into OPH (0x29EE0); D = clamp((48*op)>>3, +-10240)
    seed = (st.sent6cf8 == 0x7FFFFFFF)             # Honda's first-tick sentinel (set by the 0x2A164 skip epilogue)
    x = abe << 16                                  # |abe| <= 13000 after the op-skip guard -> < 2^31
    lp = x if seed else st.lp + ((x - st.lp) >> 9) # EMA 2^-9 (tau 512 ms)
    st.lp = lp                                     # st.w -0x6c44[gp]
    op = abe - (lp >> 16)                          # washout
    pf = clamp((Ep * 75) >> 12, -67, 67)           # = Kf 28 / 6 in D's units; 6*67 = 402 S (~64 T)
    return op + pf
```

| (a) item | status |
|---|---|
| GATE 1 for gp-0x6c44 | **static only so far (EVIDENCE):** 0 gp-relative 4-byte accessors of gp-0x6c44…-0x6c39 in the V298 image (positive controls found gp-0x6abe 23, gp-0x6dd0 6, gp-0x6cf8 4). **Owed:** 6-byte forms, register-indirect census, Ghidra xrefs on the V298 program, boot value; V289's flight is on-car evidence on a different lineage only |
| init | seeded on the first tick after any skip (sentinel), so engage, request drop, bail and camera re-arm all start with D_washout = 0 (BELIEF until the H1 interpreter run) |
| instrument | the existing wire sees it: on r79's slews (\|rate\| > 30 deg/s) the plain-D replay scores R² 0.926 against the tap, the washout replay 0.419 (EVIDENCE, s2b) |
| GATE 2 | friction gain capped at **Kf 28** (+25 % small-signal P). Kf 42 gives 4 fails, 112 gives 53 (EVIDENCE, s5b) |

**Why (a) is not the primary (EVIDENCE, s4/s5b):** the friction comp the loop can afford (Kf ≤ 28) does nothing
measurable: stuck fraction 0.276 vs V298 0.294 at 3 m/s and 0.319 vs 0.316 at 12 m/s on the r79F member. The washout
costs turn-in overshoot (+5–6 % at 3 m/s vs +0.4 % for (b)) and release lurch (3.3–3.6° vs 2.4–2.6° at 5 m/s,
nominal). Every friction lever the firmware's feedback can hold is GATE-2-capped by the highway member
`b_q*J1.0+h10 @ 26.9 FB.83`.

---

## 3. GATE 2 and the time criteria (run; panel-2 common scorers; plant = the V294-identified family)

**GATE 2, R2 box** (PM ≥ 45 tier A / 30 tier B, GM↑ ≥ 6 dB, \|T\| 5–30 Hz ≤ +3 dB; 44 members × 12 speeds × 5 frame variants):

| loop | fails | worst PM − bar (binding point) | min GM↑ | max \|T\| 5–30 Hz |
|---|---|---|---|---|
| V298 (control; **= V299-b feedback, byte-identical**) | **0** | +8.5 (PM 38.5, `b_lo*ms_free+h10 @ 11.9 FA.83`, fc 0.80) | 13.8 dB | −0.2 dB |
| V299-a small-signal (Kp 112 + Kf 28, washout) | 0 | +0.4 (PM 30.4, `b_q*J1.0+h10 @ 26.9 FB.83`) | 13.0 dB | +0.2 dB |
| V299-a saturated (Kp 112, washout) | 0 | +9.5 | 14.4 dB | −0.9 dB |
| (a) at Kf 112 (rejected) | 218 | −21.0 (PM 9.0) | 2.9 dB | +4.3 dB |

The control reproduces SCORE-FREQ's C3B-P row exactly (PM 38.5 at the same point, GM 13.8, −0.2 dB): the pipeline
is the one that cleared V298 (EVIDENCE).

**Reference path, nominal member** (s5; T_ref = plan → wheel; outer = the fork path loop, τ_o 1 s, 60 ms):

| v m/s | PM / GM / Ms (all) | V298 bw Hz / lag@0.5 Hz | V299-b bw / lag@0.5 | \|T_ref\| peak V298 → b | T_ref @20 Hz | outer PMo / GMo V298 → b |
|---|---|---|---|---|---|---|
| 3.1 | 83.7 / 23.2 / 1.24 | 1.61 / 141 ms | 2.20 / 105 ms | 1.233 → 1.274 | 0.0038 = | 82.9/16.8 → 85.2/18.1 |
| 8 | 85.9 / 23.0 / 1.25 | 1.76 / 138 | 2.64 / 108 | 1.029 → 1.045 | 0.0048 = | 80.0/19.6 → 81.7/20.3 |
| 10 | 102.2 / 26.2 / 1.13 | 0.68 / 298 | 0.76 / 243 | 1.020 → 1.029 | 0.0024 = | 71.7/17.8 → 75.0/21.4 |
| 11.9 | 91.9 / 27.9 / 1.10 | 0.47 / 399 | 0.51 / 325 | 1.015 → 1.022 | 0.0018 = | 64.5/16.0 → 68.9/22.0 |
| 17 | 95.8 / 33.3 / 1.04 | 0.26 / 359 | 0.27 / 316 | 0.980 → 0.981 | 0.0026 = | 58.3/21.8 → 60.6/25.4 |
| 26.9 | 79.9 / 35.0 / 1.04 | 0.75 / 273 | 0.78 / 253 | 1.030 → 1.033 | 0.0050 = | 73.5/18.0 → 74.7/19.3 |

The lead adds ≤ 3.3 % reference peaking, no 20 Hz leakage (the boxcar nulls the model staircase), and outer margin.

**Time criteria, closed loop with the fork model** (s4/s4b; members nominal and r79F = nominal with route 79's
single-method Coulomb 156 T ≤ 5 m/s / 85 T above, BELIEF; the 20 Hz staircase and carState i−1 modelled):

| scenario (metric) | v | V298 nom / r79F | **V299-b** nom / r79F | V299-a nom / r79F |
|---|---|---|---|---|
| 90° turn-in, plan 300 deg/s (t90 s) | 3 | 0.90 / 0.95 | **0.54 / 0.57** | 0.51 / 0.53 |
| (overshoot) | 3 | +0.4 % / −1.0 % | **+0.4 % / −0.9 %** | +6.3 % / +5.0 % |
| (wheel peak deg/s; tap peak LSB) | 3 | 163, 127 / 158, 132 | **266, 179 / 257, 185** | 306, 206 / 300, 211 |
| 90° turn-in (t90; overshoot) | 5 | 1.02, −5 % / 1.13, −7 % | **0.59, −5 % / 0.65, −7 %** | 0.53, +1 % / 0.55, 0 % |
| 45° turn-in (t90; overshoot; tap pk) | 8 | 0.53, +5.9 %, 154 / 0.55, +5.4 %, 161 | **0.40, +7.2 %, 183 / 0.41, +6.3 %, 191** | 0.42, +9.5 %, 180 / 0.43, +8.8 %, 189 |
| drift 1.5 deg/s (stuck fraction) | 3 / 8 / 12 / 20 | .172 .057 .073 .043 / .294 .189 .316 .198 | .138 .051 .053 .034 / .266 .185 .299 .190 | .154 .044 .095 .032 / .276 .172 .319 .182 |
| light opposing hand 400/700/1000 gp 1 s, release (lurch deg; bar 8°) | 5 | 2.6 2.9 2.9 / 1.9 1.9 1.9 | **2.4 2.6 2.6 / 1.7 1.5 1.4** | 3.3 3.6 3.5 / 2.4 2.6 2.5 |
| same | 12 / 20 | ≤ 1.43 / ≤ 0.38 | ≤ 1.69 / ≤ 0.53 | ≤ 1.66 / ≤ 0.46 |
| hold + road noise 15 T (4–8 Hz T rms LSB; reversals/s) | 8 | 0.074; 10.3 / 0.051; 0 | 0.074; 9.2 / 0.042; 0 | 0.104; 9.1 / 0.039; 0 |
| ±1° 0.2 Hz (gain; lag ms) | 20 | 0.93; 466 / 0.91; 977 | **0.93; 428 / 0.91; 941** | 0.90; 411 / 0.87; 918 |
| 18–22 Hz lane T rms in the slew (LSB) | 3 | 0.031 | 0.065 | 0.090 |

One element at a time (s4b, 3 m/s, nominal): firmware freeze change alone = V298 (t90 0.896); fork changes alone =
the whole effect (t90 0.542). Lead 0 → 0.5: t90 0.573 → 0.542, 8 m/s 0.441 → 0.404 (overshoot +6.5 → +7.2 %). Lead 0.7
overshoots more (+9 % at 8 m/s), hence 0.5 (≤ the measured D fraction 0.55–0.88, so the lead never exceeds the D it
cancels). The rejected kick (below) is the only element that moved stick (3 m/s 0.138 → 0.073).

**Not run (declared):** the full panel-2 goal grid (r71b real paths, 22 scenarios × 4 members × 100 speeds) exceeds
the 30 s rule. The (b) feedback loop is byte-identical to the one that grid cleared (C3B-P), and the fork terms act on
the reference. The r71b-path tracking/dwell cells are therefore inherited, not re-run.

---

## 4. Route-79 counterfactuals (EVIDENCE: computed on r79's wire and fork logs; open-loop where stated)

| question | V298 | V299 rule | source |
|---|---|---|---|
| hands-off settled \|bar\| p99 / p99.9 / max by band (0–5, 5–8, 8–12.5, 12.5–22, > 22) | 897/1092/1205 · 683/1018/1196 · 580/962/1141 · 450/789/1212 · 402/897/1066 | 0 frames > 1229 | s1-A |
| freeze duty hands-off (all / hard frames) | 7.16 % / 26.2 % | **0 / 0** | s1-B |
| integration discarded hands-off (all / < 8 m/s), \|E·G\| weight | 17.8 % / 27.2 % | **0 / 0** | s1-B |
| freeze toggles per second (all / hard) | 4.63 / 9.98 | 0 / 0 | s1-B |
| threshold crossings per minute of hands-off turning (0–5 / 5–10) | 1108 (964 / 1216) | **0** | s1-B |
| intermediate rule "hard 900 only" | — | duty 0.19 %, crossings 93 /min | s1-B |
| O1 episodes / time / hand caught / twist fired / onset delay | 415 / 100.8 s / 70 / 345 / — | **88 / 86.6 s / 70 / 18 / +20 ms p50, +50 p90** | s1-C |
| O1 rule "steeringPressed only" | — | 116 epi, twist 0, hand onset +100 ms p90 | s1-C |
| cap-bound share of hard / hands-off hard frames (O1 off) | 21.8 % / 43.9 % | 18.8 % / 29.7 % (cap 250) | s1-D |
| clip-bound share hard / hands-off hard | 0.1 % / 0.1 % | 8.8 % / 12.4 % (clip V299) | s1-D |
| lane torque the V299 firmware rules would have commanded on the RECORDED wheel (peak / p99 hard) | replay 199 / 148 (meas. 183 / 135) | 245 / 192 | s2 R1 (open loop: errors V299 would close are still integrated, so an upper-bound-like number) |
| net lane drive along the motion in fast hands-off returns (p50 LSB, share driving) | +1 (0.50) | +38 (0.70) | s2 |
| proposed bar: \|corr\| with \|tap\| / pinned / P(≥ 0.9 \| tap < 25) | 0.135 / 59.7 % / 0.60 | **0.97 / 0 % / 0.000** (10–40 ms latency: 0.973–0.959) | s3 |
| a fork "breakaway kick" trigger rate (/min latActive: 0–5, 5–10, 10–20, > 20 m/s) | — | raw sign change > 0.5 deg/s: **202 / 260 / 183 / 135**; debounced 0.5 s / 0.3 s hold: 43 / 32 / 33 / 28 | s7 → **kick rejected** |

The open-loop replays (s2 R2/A1) with the faster fork setpoint saturate at the rail on the recorded wheel: the wheel
V298 produced cannot answer a faster setpoint. They are not used as predictions; the closed loop (§3) is.

---

## 5. Hazards and fail-safe paths

**State words.** (b) adds none in firmware. The fork state is: the lead's 5-frame history and 30 ms pole, and the O1
debounce counter. (a) adds gp-0x6c44.

| path | (b) | (a) |
|---|---|---|
| engage (latActive rising) | fork lead history seeded to the measured angle (ω_f = 0); O1 counter 0 | + washout seeded on the first tick after the skip epilogue (sentinel) |
| request drop / A2 / B2 | firmware unchanged: `jr 0x2A164` epilogue, I8 := 0, sentinel set, lane ramps out on dir-2 66 (0.5 s) | same; abe_lp reseeds on the next run |
| 0xE4 timeout sentinel (fork dead) | unchanged from V298: setpoint word 0x7FFF, lane drops; no fork term can act | same |
| rate invalid (\|abe\| > 13000) | unchanged op-skip `jr 0x2A164` | washout code sits after the guard, never sees an invalid abe |
| camera frame (arm ≠ 2) | unchanged: r16 = r26 = 0, I decays | the friction add sits before the gate, so the camera path still zeroes r26 |
| firm hand (> 1200 raw) | fork O1 the same frame (no debounce), setpoint = wheel + 0.06 ω; firmware hard freeze (1229); Honda fade ×0.30 at 2289 | same |
| light hand 600–1200 raw | firmware integrates against it ≤ 60 ms + 20 ms, then O1 (setpoint = wheel, E ≈ 0). Lurch ≤ 2.6° in sim (V298 2.9°) | lurch ≤ 3.6° |
| light hand < 600 raw | the lane holds its setpoint (design intent; A3 bounds the I) | same |
| O1 fails with a hand on (fork bug) | worst lane torque the hand meets at \|bar\| 2289 ≤ 8 m/s: K·clip·fade = **K·clip = 1803–2051 T × 0.30 ≈ 540–615 T** (V298: 876–994 T × 0.30 ≈ 263–298 T), plus the frozen I; the hand still wins (Honda base assist plus the bar) | same |
| plan glitch (step) | the setpoint slews ≤ 250 deg/s (≤ the jerk limit above ≈ 6 m/s); lead adds ≤ 0.5 τ × rate ≈ 5–20° before the clip; P bounded by the clip | no lead |

**Authority rises (state before the drive):** at ≤ 8 m/s, hands-off, P may reach 73–83 % of the lane rail (V298
36–40 %). The sim tap peak in a 90° turn rises 127–156 → 179–208 LSB (58–68 % of rail), and the wheel peak rate rises
136–164 → 257–276 deg/s. Above 10 m/s nothing changes but the lead (≤ 3 % reference peaking).

**Lag budget (end to end):**

| element | value | owner | V299 |
|---|---|---|---|
| fork pairing carOutput[i] ← carState[i−1] | 10 ms | fork | unchanged; the clip/O1 already use i−1 |
| sendcan → bus → EPS 0xE4 hold | ≤ 10 + 1–10 ms | fork/EPS | unchanged |
| EPS angle hold 100 Hz + two-sample sum | ≈ 5.5 + 5 ms | firmware | unchanged |
| output lag pole + transport | 31.5 + 2 ms | firmware | unchanged |
| firmware torque word vs 0x18F | leads by 10 ms | instrument only | replay at +10 ticks (C13) |
| model staircase | 20 Hz (79 % of travel in 2 frames) | planner | the lead's boxcar has a zero at 20 Hz (T_ref @20 Hz unchanged) |
| closed loop @0.5 Hz | 260–440 ms measured (C8) | both | −7 to −26 % (model) |
| planner anticipation | liveDelay 0.35 s (never estimated) | fork | **unchanged for drive 1.** After the lead the inner lag (model 105–325 ms) stays below 0.35 s, so the lead does not double-count with the planner (BELIEF); UseAutoSteerDelay stays on |

---

## 6. Pre-registered FAIL criteria for ONE short drive (any one ⇒ do not fly again; revert with the REVERT toggle config + V298 rwd)

| id | criterion (measured on the next route) | what it would mean |
|---|---|---|
| F1 | ring presence > 0.5 %, F7 > 0 /100 s, or a new 5–30 Hz line; or 18–22 Hz eng/dis > 2.5 or 13–17 Hz > 3.5 | the lead or the faster setpoint leaks into the loop |
| F2 | any hands-off turn-in at ≤ 8 m/s overshoots its plan by > 15 % of the turn or > 10° | authority without damping |
| F3 | the V299-rule replay's R² vs the tap < 0.85, or it does not beat the V298-rule replay on hands-off 300 < \|bar\| < 1229 frames | the build is not what we think (attribution) |
| F4 | `limiter_reconstruct` with the V299 rules reproduces `co_ang` on < 99 % of latActive frames, or any pressed episode (> 1200 raw) where the setpoint is not at the wheel within 2 frames | the fork does not do what the design says; the override path is suspect |
| F5 | stall-surge rate in 5–10 m/s turning > 55 /min (r79 63–66) | M1 was not the mechanism |
| F6 | hands-off \|err\| > 1° for > 1 s on a straight ≥ 8 m/s (M-N6 given a duration) | the lead hurts holds |
| F7 | bar \|corr\| with \|tap\| < 0.9, or the bar deflects against the lane's push on > 10 % of frames with \|tap\| > 50 LSB | note 3 not fixed |
| F8 | release lurch > 8° after a ≥ 1 s grab | the freeze removal is unsafe |
| F9 | the operator reports grinding, vibration, micro-ratcheting or ratcheting worse than V298 (his words) | primary symptom |

**The drive card** (controlled setting; ~15–30 s of symptomatic frames per item):
- Prerequisites: camera LKAS **off**. It was violated on r79 (3906 camera frames forwarded to bus 0).
- Apply the toggle config. Confirm carFw reads `A16B` and the bar moves with the wheel's push.
1. **Hands-off large turns ≤ 8 m/s** (parking lot or quiet junction, AOL on): let the system take 2–3 turns of ≥ 60° with the hands hovering. This is the item r79 never had (1.2 s of hands-off wind-up).
2. A firm grab and a turn by hand. Expect the immediate yield of V298.
3. A light 1 s hold off the line at ~5 m/s and at ~15 m/s, then release.
4. 60 s of highway lane centring hands-off (note 1, F6).
5. Glance at the bar in all of the above.

**The drive read's new checks:**
- The V299-vs-V298 rule replay (F3).
- The limiter recompute with V299 rules (F4).
- Per hands-off turn-in: t90, overshoot, wheel peak, tap peak (F2).
- Stall-surge rate per minute of turning, and the \|bar\| crossing census at 1229 (F5).
- Dwells/min in 4 bands.
- Bar \|corr\| and sign (F7).
- 0.5 Hz closed-loop lag by band.
- O1 episode census, split twist/hand.
- 18–22 and 13–17 Hz eng/dis (F1).
- C13's instrument repairs (dir-2 ramp, +10 ticks, R3* reversal clause) applied first.

**Sentences a null licenses:**
- F3 null (rule replays tie) ⇒ no frame landed in 300 < \|bar\| < 1229 hands-off. Repeat item 1.
- F5 null with F3 passing ⇒ the freeze was not the ratchet. M1 is falsified and the refute's ranking falls.

---

## 7. Declared misses

1. **The small-correction stick (note 4, mechanism 2) is not fixed.** Predicted dwells/min stay at 0.80–0.97 × r79.
   Two friction levers were tested and both rejected:
   - the firmware error-keyed friction comp is GATE-2-capped at Kf 28, where it is inert (s5b, s4);
   - the fork breakaway kick would fire 85–260 /min on r79's real plan, or 13–43 /min debounced. That makes it a
     setpoint dither, not a friction fix (s7). The sim never saw this; its plan was clean.
2. **Hand-steered manoeuvres will feel the same** (they yield by design). If the operator wants co-steer assist in AOL
   turns, that is a different, unproposed design.
3. **Goal criterion "hard-turn 1.6–3 Hz wheel rate ≤ V282" will likely fail harder.** r79 was already 8.48 vs 3.45–4.02.
   A faster setpoint and a wider reference bandwidth pass more of the plan's 1.6–3 Hz content. This conflicts with
   note 2, and the operator should rule.
4. The **highway** authority (clip 16–18 % of rail ≥ 11.75 m/s, VM jerk cap) is untouched and still untested (6 s of
   r79 data).
5. Time scoring is my reduced set (5 scenarios × 2 members), not the panel-2 full grid. The r79F friction member is
   single-method and too sticky at 12 m/s: ±1° never moves the wheel there, whereas r79 measured slope 0.64–0.82.
6. The lead's dose (0.5) is sized on the image's design D/P ratio and the measured D fraction. The measured D
   magnitude is itself unresolved (0.55–0.88 ×).

## 8. What I would graft from the other angles

- **A torque-domain friction channel**, the right home for friction: the fork owns the intent, the firmware owns the
  torque. The fork would send a 2-bit "breakaway assist" field in 0xE4 byte 2. The firmware would add ±L_f (not
  integrated) while the fork asserts it. It needs a census of the spare 0xE4 bits, a GATE 1 for the parse path, and a
  fork trigger that s7 shows must be far more selective than plan-slope sign. A friction/stick specialist angle should
  own it.
- A **stiffness** angle's re-fit of the GB table where the R2-box margin allows: +8.5° at the binding point, 13.8 dB.
  That is the only lever that moves the small-signal dead zone F_c/K without a relay.
- An **instrument** angle's repair of C13 before scoring this drive. My F3/F5 depend on the dir-2 ramp and the
  +10-tick timing.
- A **hand-detection** angle's reaction-compensated hand estimate, tq_hand = tq − (−0.69 α − 0.69 ω − 163 sgn ω): it
  could replace the 60 ms debounce if it ever reaches R² ≫ 0.31.

---

### Open questions for the orchestrator

- P1: the 0x1AB sign convention on the fork (bar = −T/2461) must be unit-tested on r79 (`co`/`cs` caches) before it
  ships. s3's sign check against err is inconclusive (0.61) because the I carries the hold torque.
- P2: (a)'s gp-0x6c44 GATE 1 census on the V298 program is owed (static 4-byte scan is clean).
- P3: the fork defaults must replay r79's `co_ang` to 0.000°.
- P4: does the operator want the "6×" in hand-steered turns (co-steer assist), or is hands-off strength the goal?
