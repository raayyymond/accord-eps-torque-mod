# V295 design, lens "dynamics": phase and lag of the command -> torque -> acceleration path

Subagent `dynamics`, 2026-09-30. **Design only.** Nothing was built, flashed or sent, and no CAN traffic was generated. The
fork, STATE, memory, lineage, the golden model and `../accord-firmwares` were not touched, and nothing was committed.
Every decision-bearing claim is marked **[E]** EVIDENCE (with its method) or **[B]** BELIEF. The operator scores symptoms;
everything here is a band, a transfer function or a simulation.

The FAIL criteria were written before any candidate number was computed: `CRITERIA-dynamics.md`.

---

## 0. Bottom line

**Recommendation for this lens: `A1017`.** It moves the fb-lag pole `0xC63E8` from 1011 to 1017 (s16 LE `F3 03` -> `F9 03`),
and **nothing else**:
- The trim operand's corner moves from 2.03 Hz to 1.09 Hz. `b` is held at 567, so the trim's high-frequency gain (8b/1024) is
  unchanged.
- It is cal-only, one byte plus the page CRC.
- The rail stays at +2461 / -2463 and the sub-rail slope at 0.6409 T/wire, both unchanged. The fork's plant gain is unchanged
  too.

What it does, in one line: it rotates the acceleration trim from "part inertia" to "pure damping" at 2 Hz, which moves the
trim's damping peak from 3.1 Hz down to 2.3 Hz, into the hard-turn jerk band. It adds **nothing** above 5 Hz.

| | V294 | A1017 | source |
|---|---|---|---|
| trim damping part at 2 / 2.5 / 3 / 5 Hz (T per deg/s) | 1.61 / 1.83 / 1.91 / 1.60 | **2.17 / 2.19 / 2.11** / 1.52 | [E] exact 1 kHz transfer, `d1`, `d6` |
| trim angle at 2 Hz (0 = pure damping) | +23 deg | **+6 deg** | [E] same |
| \|T/x\| at 9 / 13 / 20 / 25 Hz vs V294 | 1 | **1.01 / 1.01 / 1.00 / 1.00** | [E] same |
| \|P/x\| at 20 Hz (V282 ground at 44.90) | 2.079 | 2.080 | [E] harness M_HF |
| K_alpha (T per deg/s^2 below the pole) | 0.210 | **0.390** (x1.86) | [E] arithmetic, `d6` |
| delivered 9-30 Hz torque, recorded command, 5 plants incl. stress | 1 | **x0.98-1.03** | [E sim] `d2(b)`, `d5` |
| mode B r_mid (1-3 Hz wheel rate), 0-15 m/s, **every member, both disturbance models** | 1 | **x0.69-0.97** | [E sim] `d5` score, `d2` |
| mode B hard-turn 1.6-3 Hz, 5-10 / 15-22 m/s, dist full, 6 members | 1 | **x0.94-0.98 / x0.89-0.98** | [E sim] `d5` |
| tracking gain / turn-hold, every band | | **within +/-0.004 / +/-0.015** | [E sim] |
| light_b outer loop at 26.9 m/s: Ms / GM / PM | 3.07 / 1.69 / 31 deg | **2.44 / 1.85 / 49 deg** | [E model, B world] `d1` M3 |

**It reaches one of the three complaints, weakly: "jerky on hard turns at medium speed."**
- Its direction is favourable, or within +/-3 %, in every band from 0 to 22 m/s, on every plant member, under both
  disturbance models.
- The size is small:
  - identified world: x0.94-0.98 on the hard-turn band;
  - light-damping prior: x0.86-0.94.
- For comparison, V293 -> V294 moved the same band x0.77 / x0.93 (nominal) and x0.56 / x0.43 (light_b). [E sim]

**It cannot reach the other two complaints.** "Loose at low speed" and "loose / understeer at highway turns" do not move:
tracking gain changes by at most 0.004. No phase knob in this lens can move them, because they are DC gain and the fork's law,
not lag.

**On the operator's literal metric (0xE4 command vs wheel angular acceleration) it is slightly NEGATIVE at about 1 Hz.**
- The added low-frequency inertia means the wheel accelerates 2-13 % less per command at 1 Hz (identified world), and 8-24 %
  less on light_b, where it is damping a resonance.
- It is +/-6 % elsewhere.
- Seen as an acceleration servo, it raises K_alpha/J from 1.05 to 1.95, so alpha/alpha_ref goes from 0.51 to 0.66. But
  alpha_ref per count falls because the FF is untouched.

That trade is stated, not hidden. See section 8.

**The lens's other knobs, and why they are not the pick** (numbers in sections 4-6):
- **Output lag `0xC63EC/EE`: the runner-up, `L8` (992/507 -> 974/792, 5.05 -> 7.97 Hz).**
  - What it gains: the only firmware element of the round trip, cut from 31.5 to 19.9 ms. Outer-loop GM rises 3-17 % and Ms
    falls, on every member.
  - What it costs: delivered 9-30 Hz torque x1.38-1.56 on every member (the RISK band); the 30-120 Hz ripple x1.41 on the road
    and x1.57 at the slew-cap staircase; and
    on the identified plant under `lp` the 1.6-3 Hz motion rises x1.01-1.08.
  - Its ranking on the jerk band flips between plant worlds.
  - On the literal metric, below the wheel mode it moves the cmd -> alpha phase further from 0 deg (+4 to +7 deg at 2 Hz). It
    improves it only above about 6 Hz, where the drive cannot score it.
- **Kd as a command-rate feedforward: dominated by the output lag.** At equal low-frequency lead, `D256` has
  - a 100 Hz kick ripple x4.8 at the slew cap,
  - 23-120 Hz content x1.7-2.4,
  - a third cell (sum clamp 15240) needed to hold the rail, and
  - no schedule above idx 32.

  `D512` and `D945` fail F3: |T/x| is x3.45 and x6.1 at 30 Hz.
- **`L10` fails pre-registered F7:** lp nominal hard-turn at 22+ m/s x1.116. **`L12` / `L15`** fail F7, and x2.1-2.6 at 25 Hz
  is the RISK band.

**Ceiling (design rule 8).**
- Below the wheel mode, cmd -> alpha is set by the spring: 55-95 % of the command holds angle, and alpha leads the command by
  +40 to +86 deg at 1-3 Hz. No firmware phase knob moves that by more than about 10 deg.
- Friction sets the small-signal deficit, and no phase knob touches it.
- The trim's low-frequency authority is capped by the fb state's int32 headroom: K_alpha is at most about 0.42 T per deg/s^2 at
  margin 2 and at most about 0.85 at margin 1, at Kp 960. A1017 sits at 0.39.
- Beyond values: a speed schedule, a second operand, or an angle-hold term are all caves or fork work. None is available this
  session.

---

## 1. Pre-registered criteria and what fired (`CRITERIA-dynamics.md`)

| id | criterion | A1017 | L8 (runner-up) | others |
|---|---|---|---|---|
| F1 | rail <= 2461 on either sign; sub-rail within 0.5 % | PASS (+2461/-2463; 0.6409) | PASS (+2461/-2462; 0.6408) | all L/D/A pass |
| F2 | no `problems()`; int32 margin >= 2; b <= b_max | PASS (**2.17** at the \|x\|=12000 edge; 10.4 on the r71b replay) | PASS (4.06) | A1020 FAILS (1.24); A1018 would be 1.86 |
| F3 | \|T/x\| 9-30 Hz <= 3x V294; \|P/x\|(20) <= 6.24 | PASS (<= 1.01x) | PASS (<= 1.55x) | **D512 FAILS** (3.45x at 30 Hz), **D945 FAILS** (6.1x) |
| F4 | stress zeta >= 0.9x V294; all stable; inner GM >= 6 | PASS (zeta within -0.6 %; GM >= 14.9) | PASS (zeta +0 to +4 %; GM >= 13.5) | all pass |
| F5 | delivered 9-30 Hz <= 2x V294 (1.3-2x = RISK) | PASS (<= 1.03x) | **RISK** (1.38-1.56x) | L10 RISK (1.56-1.92x); L12 FAILS (2.1-2.2x at 17-30 Hz); D512 FAILS (2.3-3.0x) |
| F6 | outer GM no worse than -10 %; Ms no worse than +10 % | PASS (GM +0.3 to +19 %; Ms -0.2 to -20 %) | PASS (worst GM -1.4 %, mode13 at 17 m/s) | all pass |
| F7 | tracking / turn-hold drop <= 0.02; r_mid / hard-turn rise <= 10 % | PASS (worst +4.4 %: hard-turn lp light_b 22+) | PASS (worst x1.084: lp J_hi 22+, `d5`) | **L10 FAILS** (x1.116 lp nominal 22+); **L12 FAILS** (x1.137); L8+A1014 FAILS (x1.102) |
| F8 | synthetic 30 s flight separated >= 3 SE; real-tap null not != 0 beyond 3 SE | PASS (z median 13.5, 22/23 groups > 3; null pooled +0.011 +/- 0.006) | PASS pooled (z median 12.8; null pooled +0.031 +/- 0.047), but the per-group null is **inflated** (4/23 groups \|z\| > 3; section 7) | all L/D/A separable |

**Lens-level "NO CHANGE" test** (a / b / c, pre-registered):

| candidate | (a) phase >= 5 deg at 2 Hz | (b) light_b GM >= +5 % at 17-27 m/s | (c) favourable >= 3 % on both worlds under lp | result |
|---|---|---|---|---|
| **A1017** | fails (+1.0 to +4.4 deg) | **+12.4 % / +10.4 %** | **r_mid at 0-15 m/s: nominal x0.86-0.97, light_b x0.69-0.86** | **not "no change"** |
| L8 | the size passes (+5.5 to +7.0 deg), but the direction is **away** from 0 deg below the wheel mode, so it is adjudicated not favourable. The clause as written did not specify a direction; that is a defect in my pre-registration, and I am stating it | +14.5 % / +12.6 % | fails: nominal lp rises | passes on (b) only, a light_b-only (BELIEF-world) benefit |

---

## 2. Harness spot-check (`d0_spotcheck.py`, `d0_spotcheck_out.txt`)

- [E] **The lane equals the golden model** (`lkas_fb_lag` + `lkas_rate_pid_tick`, independent code) on 32,000 ticks: 0
  mismatches on T, E, P, D, S and y. Four cell sets were checked: V294; output lag 962/982; Kd 512 with D clamp 10240 and sum
  clamp 15240; and fb_a 1017.
- [E] **Retrodiction row reproduced:** V294, nominal, `lp`, mode B, tracking gain 0.840 / 0.865 / 0.586 / 0.764 / 0.917. This is
  identical to V295-HARNESS.md section 6.
- [E] **Anchors reproduced:** \|P/x\|(20 Hz) = 2.079; output-lag DC 507/512 = 0.990234; pole 5.053 Hz; K_alpha 0.2097.
- [E] **Results do not depend on the noise realisation.** The two independent batches, the `d2` sweep and the `d5` `score()`,
  use different x-noise draws because the batch sizes differ. They agree in the direction of every A1017 and L8 effect quoted
  here. The magnitudes agree within about +/-3 % on the lp hard-turn cells, and that spread is the sim's noise floor for those
  cells.

---

## 3. The output lag: what it is and what else it smooths

- **Arithmetic [E, decompile + listing + byte scan].**
  - `0x2A174 ld.hu 0x73ee,tp,r7` (b = 507) and `0x2A184 ld.h 0x73ec,tp,r7` (a = 992, signed).
  - Then `o' = (a*o >> 10) + (S*b >> 10)`, `y = (o + o') >> 5` (`0x2A180`/`0x2A194 mul`, `0x2A1A0`/`0x2A1A6 sar 0xa`,
    `0x2A1AC sar 5`). The state is gp-0x3d3c.
  - This is confirmed by the saved V294 decompile, lines 1217-1230, and by `disassemble_bytes dry_run` at 0x2A170-0x2A1B0.
- **Readers [E, two methods].** Each cell has one live reader and one reader in the uncalled twin island:
  0xC63EC at 0x2A184 and 0x2A8A2; 0xC63EE at 0x2A174 and 0x2A892.
  - Method 1: the raw LE scan `d4_reader_scan.py`, positive-controlled (0xC63E8 is found at 0x28F8A and 0xC63EA at 0x28F86).
  - Method 2: the census c2 (23/23 controls) and the builds' own `ISLAND_CONTROLS`.
  - One non-tp halfword match at 0x7FD5C decodes as an op-0x12 immediate on r1. It is not a load.
- **Lineage [E].** 992/507 on all 272 images (census c5). Every build script asserts it. It was **struck DO-NOT-FLASH on
  2026-09-06 (V287 day) for the V282 rate servo**:
  - at >= 10 Hz, GM fell to 0.99 / 0.86 / 0.72x and Honda's oscillation detector fired;
  - the record called it a waterbed, because that loop's sensitivity peak sat at about 26 Hz (BUILD-LINEAGE V287;
    ARC-GROUNDING-TORQUE-MODE-AND-ACCEL-TRACKING section 5).
  - That verdict is for a loop with \|P/x\|(20) = 44.9. V294's is 2.079. It does not transfer.
  - On V294 the inner GM stays >= 11.5 even at 15 Hz, and every stress mode gains damping. [E model]
- **What it smooths, besides the FF [E, `d2(c)`, `d5`]:**
  - (i) The **100 Hz command staircase**. The 30-120 Hz ripple at the 123/frame slew cap is 0.89 T rms on V294, 1.40 at L8 and
    1.72 at L10. The 5-30 Hz staircase content is x1.25-1.50 at L8.
  - (ii) The **trim's sensor noise** (x white 1.93 counts). It is 0.036 T rms on V294 and 0.039 at L8, quantised to 0 in every
    HF band up to L8.
  - (iii) The **D kicks**. There are none on V294 (Kd 0).
  - (iv) The **fb restart pulse after a bail**. At 300 deg/s its peak is 419 T on V294 and 482 at L8.
  - (v) The ramp-down path. The lag runs on both paths, so a faster pole releases faster after a skip. [B] harmless.
- **Its phase cost on V294 [E, `d1` M1].** The FF path 0xE4 -> T has an equivalent delay of 36.1 / 35.0 / 29.8 ms at
  1 / 2 / 5 Hz. The 100 Hz ZOH contributes 5 ms of that, and it is not firmware.

| output-lag pole | 1 Hz | 2 Hz | 5 Hz |
|---|---|---|---|
| V294 (5.05 Hz) | 36.1 ms | 35.0 ms | 29.8 ms |
| L7 | 27.6 ms | 27.2 ms | 24.8 ms |
| **L8** | **24.9 ms** | **24.6 ms** | **22.8 ms** |
| L10 | 21.0 ms | 20.8 ms | 19.8 ms |
| L12 | 18.3 ms | 18.2 ms | 17.6 ms |
| L15 | 15.6 ms | 15.6 ms | 15.3 ms |

---

## 4. Per-knob physics (linear, exact 1 kHz, the harness's own transfer functions; `d1_linear.py` -> `d1_linear_out.txt`)

**Families.**
- **L** (output lag): a = round(1024·e^(-2 pi f Ts)), b = floor(507/512·16·(1024-a)), so DC <= V294's.
- **D**: Kd flat on all 4 knots, D clamp 10240, sum clamp 15240 (holds the rail).
- **A**: fb_a with b held, or with K_alpha held.

### 4.1 cmd -> alpha, closed form (inner trim loop closed), nominal at 12 m/s

V294 reference:

| | 0.3 Hz | 0.5 Hz | 1 Hz | 2 Hz | 3 Hz | 5 Hz | 8 Hz |
|---|---|---|---|---|---|---|---|
| \|alpha/cmd\| | 0.075 | 0.164 | 0.365 | 0.644 | 0.859 | 1.154 | 1.25 |
| phase (+ = alpha leads) | +137 | +117 | +86 | +58 | +40 | +11 | -26 |

Candidates (ratio vs V294; phase change in deg):

| knob | ratio 1 / 2 / 5 / 8 Hz | dphase 1 / 2 / 5 / 8 Hz |
|---|---|---|
| L8 | 1.02 / 1.04 / 1.14 / 1.29 | +3.8 / +6.3 / +12.3 / +14.3 |
| L10 | 1.02 / 1.06 / 1.19 / 1.39 | +5.1 / +8.6 / +17.3 / +21.1 |
| D256 | 1.01 / 1.01 / 1.01 / 1.05 | +2.9 / +5.2 / +13.7 / +23.2 |
| **A1017** | **0.94 / 0.96 / 1.02 / 1.01** | **-1.1 / +2.4 / +1.2 / 0.0** |
| A1014 | 0.98 / 0.98 / 1.01 / 1.01 | -0.7 / +0.9 / +0.6 / 0.0 |

- On light_b (12 m/s) A1017 reads ratio 0.82 / 0.91 / 1.06 and dphase -8.3 / +9.7 / +0.8 deg.
- **Physics [E]:**
  - At 1-3 Hz the phase is POSITIVE (alpha leads) because of the spring. Any lag reduction moves it further from 0 deg.
  - Only above about 6 Hz, where the plant is inertia-dominated, does removing lag bring the phase toward 0 deg.
  - That region is where the metric agent found the drive incoherent (alpha_theta usable to 4.3 Hz only), and where the fork's
    P term dominates the command.

### 4.2 Trim opposing torque T/omega: angle and damping part

Values are the angle (0 = damping, +90 = inertia) and the damping part in T per deg/s:

| | 2 Hz | 3 Hz | 5 Hz | 13 Hz | 20 Hz | 25 Hz |
|---|---|---|---|---|---|---|
| V294 | +23 / 1.61 | +2 / 1.91 | -25 / 1.60 | -67 / 0.38 | -81 / 0.10 | -88 / 0.02 |
| L8 | +30 / 1.57 | +12 / 2.03 | -13 / 2.05 | -57 / 0.76 | -73 / 0.28 | -81 / 0.12 |
| L10 | +33 / 1.54 | +16 / 2.04 | -7 / 2.20 | -51 / 1.01 | -69 / 0.43 | -77 / 0.22 |
| D256 | +29 / 1.54 | +11 / 1.90 | -10 / 1.80 | -33 / 1.00 | -36 / 0.80 | -37 / 0.72 |
| **A1017** | **+6 / 2.17** | **-12 / 2.11** | -35 / 1.52 | -71 / 0.31 | -84 / 0.07 | -90 / 0.00 |
| A1014 | +15 / 1.89 | -5 / 2.03 | -30 / 1.57 | -69 / 0.35 | -82 / 0.09 | -89 / 0.01 |

- The L and D knobs move trim damping UP in frequency (to 4-5 Hz and above 13 Hz).
- The fb pole moves it DOWN, into the 1.6-3 Hz jerk band, and leaves 13-25 Hz unchanged. See `fig_d1_trim_bode.png`.
- At 25 Hz A1017's trim angle is -89.6 deg, so its damping part is about 0 there. It is still not anti-damping, and
  `mode20`/`mode20_lo` zeta is unchanged (section 4.4).

### 4.3 High-frequency controller gain \|T/x\|, ratio vs V294

| knob | 13 Hz | 20 Hz | 25 Hz | 30 Hz |
|---|---|---|---|---|
| L8 | 1.44 | 1.51 | 1.53 | 1.55 |
| L10 | 1.68 | 1.82 | 1.86 | 1.89 |
| L12 | 1.87 | 2.09 | 2.17 | 2.23 |
| L15 | 2.08 | 2.45 | 2.59 | 2.69 |
| D256 | 1.24 | 1.51 | 1.73 | 1.97 |
| D512 | 1.75 | 2.42 | 2.93 | **3.45** |
| D945 | 2.80 | 4.14 | 5.12 | **6.10** |
| A1017 | 1.01 | 1.00 | 1.00 | 1.00 |

- Absolute \|T/x\|(20 Hz): V294 0.082, L8 0.123, V282 1.761.
- **L8 is at 7 % of V282's value** [E].

### 4.4 Stress-mode damping and inner loop (`d1` M6/M8, `d5` M_LOOP)

- **A1017:** every stress zeta is within -0.6 % / +0.1 % of V294's. For example, `mode20` at 5 m/s is 0.0763 against 0.0764,
  and `mode20_lo` at 5 m/s is 0.1251 against 0.1258.
- **L8:** zeta rises by 0 to 4 %. `mode20` at 5 m/s goes 0.0764 -> 0.0777 and `mode20_lo` at 12 m/s 0.226 -> 0.237. The one
  exception is `mode13` at 25 m/s: 0.1464 -> 0.1460.
- **Inner GM minimum:** V294 16.3, A1017 14.9, L8 13.5, L10 12.6. Every member is stable with the delay x1.5.
- **Second method for A1017 on light_b [E, exact linear poles `closed_loop_modes`]:** the wheel mode goes from 0.74-1.23 Hz at
  zeta 0.45-0.47 to **0.58-0.90 Hz at zeta 0.51-0.62**. It is more damped, and it is lower because of the added inertia. The
  identified members have no oscillatory wheel mode, so they have nothing to move.

### 4.5 Fork outer loop, r1 linearised (`d1` M3; stress members read the wheel-side angle)

| plant, speed | V294 Ms / GM / PM | L8 | L10 | D256 | **A1017** |
|---|---|---|---|---|---|
| nominal, 8 m/s | 1.185 / 10.5 / 145 | Ms -1.3 %, GM +9.9 % | -1.8 %, +15 % | -1.4 %, +17 % | -2.5 %, +4.7 % |
| nominal, 26.9 m/s | 1.087 / 19.9 / 139 | -0.9 %, +4.3 % | -1.3 %, +7.0 % | -1.0 %, +22 % | -0.3 %, +1.2 % |
| light_b, 8 m/s | 1.737 / 4.05 / 53 | -3.3 %, +17 % | -4.5 %, +25 % | -3.1 %, +16 % | **-15.8 %, +17 %, PM +14** |
| light_b, 17 m/s | 2.000 / 2.63 / 50 | -4.7 %, +14.5 % | -6.5 %, +21 % | -4.9 %, +14.5 % | **-15.6 %, +12.4 %, PM +20** |
| light_b, 26.9 m/s | 3.066 / 1.69 / 31 | -10.9 %, +12.6 % | -14.6 %, +19 % | -11.6 %, +14 % | **-20.4 %, +10.4 %, PM +17.5** |
| mode13, 17 m/s | 1.063 / 22.4 / 111 | GM -1.4 % | -1.4 % | +13.6 % | +0.8 % |

- The fork's liveDelay (0.326 + 0.1 s) enters only the planner look-ahead, not the feedback. An EPS lag change of -11.6 ms
  (L8) is about 3 % of it. [B] No retune is needed, and liveDelay learns online.

---

## 5. Time domain on the shared harness (`d2_time.py` -> `d2_time_out.txt`; `d5_score.py` -> `d5_score_out.txt`)

**Mode B, candidate / V294 in the same batch** (`d5` `score()`, 6 members):

| | A1017 | L8 |
|---|---|---|
| r_mid, full, 0-22 m/s, all 6 members | x0.84-0.98 | x0.96-0.996 |
| r_mid, lp, 0-15 m/s | nominal x0.86-0.97; light_b x0.69-0.86 | nominal x1.00-1.02; light_b x0.97-0.99 |
| r_mid, lp, 22+ | x0.89-1.02 | x0.95-1.07 |
| hard-turn 1.6-3 Hz, full, 5-10 / 15-22 m/s | x0.94-0.98 / x0.89-0.98 | x0.97-0.99 / x0.95-0.996 |
| hard-turn, lp | x0.86-1.04 | identified members x1.01-1.08 (nominal x1.03-1.06); light_b x0.95-1.05 |
| tracking gain, turn-hold | within +/-0.004, +/-0.015 | within +/-0.0015, +/-0.006 |
| J_err (0.15-2.4 Hz) | x0.95-1.04 | x0.97-0.99 |
| 1-5 Hz line, lp | -4.7 -> -5.6 dB nominal; +0.7 -> -1.1 dB light_b | unchanged |

- [E sim] The `d2` batch (different noise draws) agrees in direction, cell for cell.
- **The lp rise of L8 on the identified plant is the forced path.** alpha/cmd is x1.04-1.07 at 2-3 Hz (section 4.1), so more of
  the fork's own 1.6-3 Hz command reaches the wheel.
- **A1017's lp fall is partly the reverse.** alpha/cmd is x0.94-0.96 at 1-2 Hz. **The sim cannot split commanded from
  uncommanded 1-3 Hz motion** [B]. Under `full`, which carries the road disturbance, A1017 still reads x0.92-0.98 on nominal, so
  part of it is disturbance rejection.

**Delivered HF torque, recorded command** (mode A, dist full). V294 absolute, nominal, T rms:

| band | 5-9 Hz | 9-13 Hz | 13-17 Hz | 17-23 Hz | 23-30 Hz | 30-120 Hz |
|---|---|---|---|---|---|---|
| V294 | 1.74 | 1.11 | 0.65 | 0.53 | 0.23 | 0.26 |

Ratio vs V294 (the same within +/-0.03 on light_b, mode13, mode20, mode20_lo, and again in mode B lp):

| candidate | 5-9 | 9-13 | 13-17 | 17-23 | 23-30 | 30-120 |
|---|---|---|---|---|---|---|
| **A1017** | 1.04 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| L8 | 1.20 | 1.39 | 1.47 | 1.52 | 1.53 | 1.41 |
| L10 | 1.27 | 1.56 | 1.73 | 1.83 | 1.86 | 1.70 |
| D256 | 1.02 | 1.13 | 1.28 | 1.48 | 1.74 | **2.35** |
| D512 | 1.13 | 1.44 | 1.84 | 2.35 | 2.96 | **4.29** |

**Margin argument for L8 against the no-grinding record** [E arithmetic, B physics]. It is required of any RISK-band candidate
by rule 3, and it is written here even though L8 is not the pick.
- L8 adds about 0.27 T rms at 17-23 Hz. On a rigid J 0.2 that is about 0.01 deg/s of wheel motion (0.032 deg/s for the total
  0.80 T rms).
  - That is 8x below the rate sensor's own noise (0.24 deg/s).
  - It is about 60x below V282's grinding ring (about 16 x-counts, 2 deg/s).
  - The added loop gain at 20 Hz is 7 % of V282's.
  - Every stress mode gains damping.
- **But V282's grind was a loop resonance, not forced content, and the torque-mode car has not been driven with x1.5 more
  9-30 Hz torque. "Probably below perception" is BELIEF.**

---

## 6. The D term: the command-rate feedforward, and whether the V288 record transfers

- **[E, census + `d1`] D is a phase lead on the whole error E**, the FF and the trim alike. On V294:
  - The command part is a one-tick-in-ten kick of Kd·Δsp/2 S.
  - Averaged through the output lag it is a lead zero with tau_D = 32·Kd·Ts/Kp = **3.33e-5·Kd s**.
  - **Kd ≈ 945 cancels the 31.5 ms output-lag pole exactly** (M1: tau_eq 5 ms = the ZOH alone).
  - The feedback half at Kd/8·Δr26 is the same zero on the trim, so it lifts \|T/x\| above 5 Hz by the same factor. That is why
    D512 and D945 fail F3.
- **Dominated by L.** At equal low-frequency lead, D256 against L7 gives:

| | D256 | L7 |
|---|---|---|
| cmd -> T at 1 / 2 Hz | +3.1 / +6.1 deg | +3.1 / +5.6 deg |
| 9-17 Hz ratio | x1.13-1.28 | x1.27-1.32 |
| 23-120 Hz ratio | **x1.74-2.35** (the 100 Hz kick train) | x1.27-1.35 |
| staircase ripple at 30-120 Hz | **4.23 T** | 1.23 T |
| rail | needs a third cell (sum clamp 15360 -> 15240); otherwise 2461 -> 2481 | unchanged |
| schedule | none above idx 32 | not applicable |

- **V288's excitation mechanism transfers only as forced response** [E arithmetic, B physics].
  - On V282 the kick was 32·Δsp·Kd/8 into a rate loop that de-damped the 20 Hz mode to zeta about 0.016-0.026. The slew cap
    carried about 54 % of the D binds.
  - On V294 the shl 2 makes the kick **8x smaller per Kd unit** (Kd 256 is 1/4 of V282's Kd 128 kick). The V294 loop leaves the
    20 Hz stress mode at its open-loop zeta: 0.076 against 0.076.
  - With 1/4 of the excitation into a resonator 3x better damped, the ring would be about 1/10 of V282's.
  - It is still extra 23-120 Hz content on a symptom the operator has called absent.
- **Instrument (rule 6).** Its command part is a deterministic function of Δcmd, so the exact-model regression attributes it:
  D256 synthetic z median 10.7, null pooled +0.039 +/- 0.051 (`d3`). "No separate wire instrument for D" is solvable for the
  command part. The feedback part is negligible and unobservable.
- **Verdict:** not recommended. It adds nothing that the output lag does not do more cleanly.

---

## 7. Attribution on the existing wire (design rule 6; `d3_attribution.py` -> `d3_attribution_out.txt`)

**Method [E].**
1. March V294 and the candidate byte-exact on r71b's own command and 1 kHz rate. Positive control: V294 equals plib's march
   bit for bit (0 mismatching ticks).
2. Build a synthetic tap: quant(T_cand) plus the **real** V294 tap residual (3.64 counts rms), with the same quantiser and the
   same timing.
3. Regress y = tap - quant(T_V294) on r = T_cand - T_V294 in 30 s groups of hands-off engaged frames.
4. SE by a 1 s block bootstrap.
5. **Null control: the real r71b tap.**

| candidate | footprint \|dT\| rms (p99) | synthetic beta median, z median (min), groups z>3 | real-tap null beta median, pooled +/- SE, groups \|z\|>3 |
|---|---|---|---|
| **A1017** | **9.9 (48)** | **1.014, 13.5 (2.5), 22/23** | **+0.028, +0.011 +/- 0.006, 1/23** |
| L8 | 3.1 (11) | 1.117, 12.8 (1.0), 21/23 | +0.148, +0.031 +/- 0.047, **4/23** |
| L10 | 4.3 (16) | 1.074, 15.4 (1.5), 22/23 | +0.102, +0.022 +/- 0.034, 6/23 |
| D256 | 2.5 (9) | 1.108, 10.7 (1.0), 22/23 | +0.125, +0.039 +/- 0.051, 5/23 |
| A1014 | 3.8 (19) | 1.050, 6.9 (2.3), 22/23 | +0.066, +0.026 +/- 0.014, 0/23 |

- **The L and D nulls are inflated** [E, B cause]. A lag change's footprint is about Δtau·dT/dt, and so is the tap's timing
  uncertainty (the plant study: +/-4 ms; about 2 ms of residual lag). The per-group SE is therefore optimistic for them.
  - The pooled read still separates cleanly: beta about 1.0 against about 0.03.
- A1017's footprint lives at 0.3-3 Hz, where timing does not matter, and its null is clean.
- **Second read, the FF-identity lag against the static surface** [E]: V294's real tap has a best lag of +18 ms (per-group median;
  IQR 10-20).
  - The L8 synthetic reads +10 ms (IQR 7-16) and L10 +8 ms.
  - This read is not specific: A1017 also moves it (+10 ms), because the trim's residual structure changes.

**A1017's pre-registered wire predictions** (the metric agent's trim-footprint regression; V294 measured with CI):

| band | V294 measured \|K\| [CI] | A1017 predicted \|K\| | predicted phase shift |
|---|---|---|---|
| 0.3-1 Hz | 0.193 [0.183, 0.202] | **0.33** | -12 deg |
| 1-3 Hz | 0.128 [0.124, 0.132] | **0.17** | -17 deg |
| 3-8 Hz | 0.060 | 0.064 | -10 deg |

- The ratios are EVIDENCE. The mapping onto that report's phase convention is BELIEF: the same handedness plus 180 deg, which
  gives +145 / +97 / +56 deg.

**The sentences a result licenses (written now, before any build):**

| result | what it licenses |
|---|---|
| **ATTRIBUTION** (exact-model regression, >= 30 s hands-off engaged): beta >= 0.5 (predicted 1.0 +/- 0.1) and \|K\|(0.3-1 Hz) >= 0.28 | **A1017 is on the car.** |
| beta <= 0.3 and \|K\| at V294's 0.19 | **The image on the car is not A1017. STOP.** Nothing else from the drive is licensed. |
| \|K\|(0.3-1 Hz) > 0.45 or a phase shift < -30 deg | the arithmetic is not what this report says. Stop and re-derive. |
| **NULL on the symptom:** the edit is live (above), and the operator reports hard turns at medium speed as jerky as V294 | Moving the trim's damping peak from 3.1 Hz down to 2.3 Hz is not the lever for that jerk. That move is +35 % damping at 2 Hz, which is still only about 1/5-1/8 of V282's rate-loop reaction in 1-3 Hz and the most this operand can give at int32 margin 2. **The jerk is not trim-damping-limited in 1.6-3 Hz at this size.** The next lever is the trim's magnitude (b, with its HF cost) or the fork's outer loop, **not a further pole move.** |
| **COST CHECK:** the operator reports the steering "slower", "heavier" or "lagging" in quick transitions | The added 1 Hz inertia is felt (alpha per command -2 to -13 % at 1 Hz). Revert to V294's 1011. |
| any NEW line in 5-30 Hz, or grinding / stutter | Not predicted: the lens adds nothing there. Treat it as an image or instrument fault and revert. |

**Band reads, secondary.** These are cross-drive, so they are not an endpoint under the one-short-drive doctrine. Hard-turn
1.6-3 Hz wheel-rate rms at matched speed x demand cells against r71b: predicted x0.89-0.98. 1-3 Hz wheel rate at 0-10 m/s
hands-off: x0.84-0.93. [B: the car is between the two worlds.]

---

## 8. Scoring against the operator's three complaints and the goal metric

| complaint / metric | A1017 | L8 | can this lens reach it? |
|---|---|---|---|
| **"Jerky on hard turns at medium speed"** (1.6-3 Hz, 5-15 m/s) | **favourable in both worlds:** full x0.94-0.98 (identified), x0.94 / x0.89 (light_b); lp x0.86-1.04. Small: about 1/4 of the V293 -> V294 step | identified world lp **x1.01-1.08 (worse)**; full and light_b x0.95-0.99. The ranking flips | **weakly, via the fb pole** [B for the car] |
| **"Loose on straights and turns at low speed"** (tracking 0.87 / straight delivery 58 %) | tracking +0.002 / -0.001; straight delivery +0.004 | -0.001 / -0.004 | **no.** DC gain, friction (Fc 76 T at 3 m/s) and the fork's law. The p-gain lens's territory |
| **"Loose / understeer at highway turns"** (turn-hold 0.67-0.69) | turn-hold +/-0.006 | +/-0.006 | **no.** The fork law on this plant; the V294 trim changes it by <= 0.004 (harness section 0.6) |
| **Goal: cmd vs alpha** (literal) | \|alpha/cmd\| x0.87-0.98 at 1 Hz identified (x0.76-0.92 light_b); phase within +/-2 deg identified; **slightly worse** at 1 Hz | +2-5 % at 1-3 Hz, +10-17 % at 5 Hz; phase +4 to +7 deg at 1-3 Hz (**away** from 0), toward 0 above 6 Hz | **no firmware phase knob improves it below the wheel mode**. See section 9 |
| Goal, seen as an acceleration servo (alpha vs alpha_ref) | K_alpha/J 1.05 -> 1.95; alpha/alpha_ref 0.51 -> 0.66 at < 1 Hz; disturbance-acceleration rejection x0.69 | unchanged at low frequency | yes, but alpha_ref per count is set by FF / K_alpha, and a matching FF raise is a static-gain edit (rule 4, not this lens) |

---

## 9. Physics ceiling (design rule 8)

1. **The spring.** On the identified family, 55-95 % of the command variance holds angle (metric agent). The literal
   cmd -> alpha phase is +86 to +150 deg below 1 Hz and +40 to +58 deg at 2-3 Hz.
   - Every phase knob in this lens moves it by at most about 10 deg below 3 Hz.
   - The output lag's -25 deg at 2 Hz currently **cancels** part of the spring's lead. Removing it makes the literal phase
     worse there. [E]
2. **Friction** sets the small-signal deficit: 0.37 against 0.89 deg/s^2 per count. That is an amplitude effect, and no
   phase knob touches it. [E metric; harness flatness: V294 and A1017 differ < 5 %]
3. **The output lag** is 31.5 ms of time constant, about half of the ~60 ms round trip. It is the only piece the firmware
   owns; the 20-22 ms pipeline, the 3 ms rate former and the fork's filters are out of reach.
   - The HF guard allows about 8 Hz (-11.6 ms) inside F5's RISK band.
   - Cancelling it fully (Kd 945, or lag_a -> 0 with b 16220) would take |T/x| at 20-30 Hz to x4-6 of V294's.
4. **The int32 cap on the trim's low-frequency authority** [E arithmetic]. |a*s| < 2^31 at the |x| = 12000 bail edge forces
   b/(1024-a) < 2^31/(12000·a). So K_alpha <= 0.85·(Kp/960) T per deg/s^2 at margin 1, and <= 0.42 at margin 2, whatever the
   pole.
   - A1017 at 0.39 is at that ceiling for margin 2.
   - Any b increase from another lens combined with A1017 must keep b <= about 616, because b_max(1017) = 1232 against 2301 at
     1011.
5. **What would be needed beyond values** (none available this session, and each is a cave or fork work):
   - a **speed schedule** of the pole or trim;
   - **two operands** (rate damping plus acceleration inertia with independent gains);
   - an **angle-hold term** (+k·θ, the fork FF's job);
   - **exogenous command content** to score the literal metric (fork side).

---

## 10. Risks (stated before any drive)

**A1017.**
- **(a) More low-frequency inertia.** K_alpha goes x1.86 (0.21 -> 0.39 T per deg/s^2). At about 1 Hz the wheel accelerates
  2-13 % less per command (identified) and up to 24 % less (light_b, near its wheel mode).
  - It could feel slower or heavier in quick transitions. [B]
  - The trim's rms on the r71b replay rises 18.7 -> 28.0 T (p99 95 -> 140, max 309 -> 429). The trim share of FF is still
    below about 12 % (V294: 1.6-8 % by band).
- **(b) int32.**
  - Worst case at the |x| = 12000 edge: margin 2.17 (V294 4.06).
  - On the real drive, a*s max is 2.07e8, margin 10.4 (V294 17.8).
  - fb clamp: max |r26| 790 of 1024, **0 binds** (V294 637). P binds fall 461 -> 345. S binds 0. [E replay `d5`]
- **(c) Restart pulse after a filter bail** (lane only, wheel held): 503 T peak at 300 deg/s, above 50 T for 433 ms (V294
  419 T / 252 ms). The pulse lasts longer because the state decays more slowly. There are no |x| bails on r71b (max 373 deg/s);
  the bar / polarity bails are not on the wire. [B: rare]
- **(d) Unchanged:**
  - the rail, sub-rail slope, trim cap (616 T = 25 %), zero-command torque, FF and HF;
  - soft-EME: the lane cannot reach 5120-5325 (rail 2461). Base assist under driver torque is not modelled. [B]
- **(e) Lineage** [E, lever index + BUILD-LINEAGE]:
  - 0xC63E8 was moved on the **rate-servo** operand by V289 (25 Hz, flown: ring moved to 16 Hz) and V291/V292 (9.94 Hz, V292
    flown: REVERT, 7 Hz re-armed). V293 restored it to stock 923.
  - **V294 moved it to 1011 on the difference operand and flew clean.** A1017 is V294's own direction, pushed further, inside
    V294's build-script ladder bounds a in [1000, 1018] (1-4 Hz).
  - V294's design ladder (light-damping world, K_alpha held) preferred the 1.4 Hz pole at low speed and 2.0 Hz at 26 m/s.
    A1017 does not hold K_alpha; it raises it.
- **(f) Overlap** with the trim-ratio lens: A1017 raises K_alpha through the pole instead of through b. That avoids b's x2 HF
  cost, but it shares b's low-frequency authority budget (see 9.4).

**L8, the runner-up.**
- Delivered 9-30 Hz x1.38-1.56; 30-120 Hz ripple x1.41 on the road and x1.57 at the staircase.
- A cell frozen on 272 images, with no on-car record; struck on V282 for a different loop.
- On the identified plant under `lp`, 1.6-3 Hz x1.01-1.08.
- Restart pulse x1.15.
- The attribution null is timing-confounded (read pooled, not per group).

---

## 11. Runner-ups, with numbers (all differences from V294, same harness)

| candidate | cells | what it buys | why not |
|---|---|---|---|
| **L8** | 0xC63EC 992 -> 974 (`CE 03`), 0xC63EE 507 -> 792 (`18 03`) | cmd -> T -11.6 ms; outer GM +3-17 % (light_b 26.9 m/s: GM 1.69 -> 1.90, Ms 3.07 -> 2.73); alpha/cmd at 5-8 Hz x1.14-1.29 | HF x1.38-1.56 (RISK); jerk-band ranking flips; the literal phase moves away from 0 below the mode |
| A1014 | 0xC63E8 1011 -> 1014 | half of A1017: r_mid lp nominal x0.95-0.97, light_b x0.85-0.93; int32 3.11; footprint \|K\|(0.3-1) 0.24 | a smaller readout, a smaller effect |
| L7 | 992 -> 980, 507 -> 697 | -8 ms; HF x1.27-1.37 | a smaller L8 |
| D256 | Kd 0 -> 256 flat (28 records), D clamp 0 -> 10240, sum clamp 15360 -> 15240 | lead similar to L7; outer GM +14-22 % | the kick ripple (30-120 Hz x2.35, staircase ripple x4.8); three cells; no schedule above idx 32 |
| L10 | 992 -> 962, 507 -> 982 | -15.6 ms; light_b 26.9 m/s GM +19 %, Ms -15 % | **fails F7** (x1.116); HF x1.56-1.92 |
| L8+A1014 | three cells | both effects | **fails F7** (x1.102); two edits to attribute |
| D512 / D945 / L12 / L15 / A1020 | | | fail F3 / F3 / F5+F7 / F5+F7 / F2 |
| A999 or A1017 with K_alpha held (b 1090 / 305) | | | these are b moves (trim-ratio lens). b 1090 doubles HF (x1.9); b 305 halves the trim |

---

## 12. Files (all in `analysis-2020accord/studies/v295/design/dynamics/`)

| file | contents |
|---|---|
| `CRITERIA-dynamics.md` | pre-registered FAIL criteria and the lens-level no-change sentence |
| `d0_spotcheck.py` / `_out.txt` | harness spot-check: the lane against the golden model on 4 sets; one retrodiction row; the anchors |
| `d1_linear.py` / `_out.txt` / `.json` | the linear study of 18 candidates: M1 cmd -> T, M2 alpha/cmd, M3 outer loop, M4 trim T/omega, M5 HF, M6 stress, M8 safety |
| `d2_time.py` / `_out.txt` (log `d2_log.txt`) / `.json` | mode B sweep (full and lp; nominal and light_b), delivered HF in modes A and B incl. stress members, staircase, sensor noise |
| `d3_attribution.py` / `_out.txt` / `.json` (log `d3_log.txt`) | the synthetic-flight attribution with the real-tap null; the FF-identity lag read. Cache in `_scratch/` |
| `d4_reader_scan.py` / `_out.txt` | raw LE reader scan of 0xC63E8/EA/EC/EE, 0xC61B6, 0xC61BE and the Kd/Kp banks, positive-controlled |
| `d5_score.py` / `_out.txt` / `d5_score_A1017.json` / `d5_score_L8.json` / `d5_replay_internals.json` | the shared harness's full `score()` for both finalists; the r71b replay internals (r26, clamps, int32 on the drive) |
| `d6_predict.py` / `_out.txt` / `.json` | trim-footprint predictions, physical constants |
| `fig_d1_trim_bode.png` | trim opposing torque and its damping part against f, V294 / A1017 / A1014 / L8 / L10 (the jerk band and the no-grinding band shaded) |
| `fig_d2_ff_delay.png` | the equivalent delay of 0xE4 -> T against f |

**Defects in my own work, reported rather than hidden.**
1. The first `d3` run found 0 windows: the |bar| < 400 mask breaks every 30 s contiguous run. The script now uses
   consecutive groups of 1500 hands-off tap frames, and the output file is from that version.
2. The pre-registered clause (a) did not specify a phase direction. It is adjudicated in section 1.
3. My F2 threshold (margin >= 2) is mine. The harness guard fails only at margin < 1.
