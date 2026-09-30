# V295 design, lens "robust-joint": a joint, worst-case search over every LKAS-PID cal knob

Subagent `robust-joint`, 2026-09-30. **Design only.** Nothing was built, flashed or sent; no CAN traffic; no firmware
artifact, fork, STATE, memory, lineage or golden-model file was touched; nothing committed. Scripts and outputs are
beside this file. Pre-registered criteria: `CRITERIA-robust-joint.md` (written before any candidate number).
Every decision-bearing claim is **[E]** EVIDENCE (method named) or **[B]** BELIEF. Bands are the kit's; symptoms are the
operator's to score — nothing here says any symptom is fixed.

---

## 0. Bottom line

**Recommendation — candidate A: ONE cal cell. `0xC63EA` (fb-lag gain b) 567 → 1106 (LE `37 02` → `52 04`), ×1.95.**
Every other byte of V294 unchanged: a 1011 (2.03 Hz pole), C 1024, Kp bank [960]×5 on all 28 records, map, output lag
992/507, `shl 2`, `subr`, Kd 0 / D clamp 0, Ki 0. Edit class cal-only (2 data bytes + the block CRC).

What it is physically [E, the harness's byte-exact lane + linear transfers]: the 1 kHz acceleration trim doubled.
- K_α 0.210 → 0.410 T per deg/s² below the 2.03 Hz pole (wheel J_eff 0.41 → 0.61 there, bare J 0.2 in the identified plant).
- Opposing torque per deg/s of wheel rate at 2 / 5 / 20 Hz: V294 1.75 @ +23° / 1.76 @ −25° / 0.65 @ −81°;
  A 3.41 / 3.44 / 1.26 at the same phases. It adds ~3.4 T/(deg/s) of damping at 2–5 Hz, against a plant damping of
  4.9 / 5.2 / 9.8 / 20.7 / 26.4 by speed band: +70 % at 0–10 m/s, +17 % at 15–22.
- **The feed-forward is bit-identical.** The static surface T(idx) equals V294's at every idx (golden-model march):
  rail +2461/−2463, sub-rail slope 0.6409 T per wire count, trim cap 616 T. The fork's outer-loop plant gain is
  therefore unchanged.

**Which complaints the lens reaches.** The sim ratios below are directions with the family envelope; they are not
on-car magnitude predictions. The 1–8 Hz wheel motion is NOT FIT from the plant alone (harness §0).

| complaint (his words) | band behind it | A vs V294, worst..best over 6–15 members, dists lp AND full | reached? |
|---|---|---|---|
| "Jerky on hard turns at medium speed" | 1.6–3 Hz wheel rate in hard turns, 1–3 Hz rate | hard turns 5–10 m/s ×0.93..×0.68, 15–22 m/s ×1.03..×0.67 (the ×1.03 is b_hi lp, inside the ±7 % floor); 1–3 Hz rate 15–22 ×0.99..×0.75 | **YES, direction DOWN on every member and both disturbance models** |
| "Loose on straights and turns at low speed" | tracking gain, straight delivery 0–10 m/s | tracking −0.001..+0.004; straight delivery ±0.01 | **NO** |
| "Loose/understeer at highway turns" | tracking gain, turn-hold 15–22 / 22+ | tracking ±0.000..+0.003; turn-hold −0.008..+0.013 | **NO** |
| goal: "comma LKAS command vs 2nd derivative of angle" | α/cmd flatness 1–8 Hz | actuator branch (closed form) R² 0.860 → 0.887 nominal at 12 m/s, 0.773 → 0.884 light_b; the literal on-road fit moves ±0.02 | modest; ceiling in §8 |

**Why the loose complaints are not in the pick.** The only cal knob that moves them is the static gain g: the Kp level
with b compensated, or the map. It is a transparent surrogate of the fork's LAF (g ≡ LAF 14/g on the FF, P and I; the
friction relay also scales ×g).
- In the nonlinear replay it buys tracking gain +0.022..+0.036 at g 1.1 and +0.041..+0.065 at g 1.2 (lp, every member,
  bands 0–5 / 5–10 / 15–22 / 22+) [E for the sim].
- On the identified plant it raises the loop's OWN 1–3 Hz wheel motion (dist lp): ×1.08–1.09 at 15–22 m/s at g 1.1, and
  ×1.13–1.22 at g 1.2 on every non-prior member. The same ratio is ×1.09 even with the planner's 1–3 Hz content low-passed
  out, so part of it is loop-generated. The harness's own noise floor for this ratio is ±2 % (§11.1).
- That is the pre-registered F3 flip, lp vs full, on the jerk proxy, and F2's "worse by more than half the margin"
  clause (> ×1.05). **Both fire, so the g-points are runner-ups C and D, not the pick.**

**Binding constraints on A** (all pre-registered, §1):
- **H-SAFE-3, the restart pulse** at 100 deg/s ≤ 2 × V294's 144 T: A reads 283. b = 1134 (×2.00) reads 290 and fails.
- **H-SAFE-2, the int32 margin** ≥ 2.0 at a·s: A reads 2.08.
- **Not binding:**
  - HF, where A is at ×1.95 of V294's 10–25 Hz gain against a cap of ×3;
  - the stress modes (ζ unchanged or up);
  - the inner loop (Ms ≤ 1.27 incl. delay ×1.5);
  - the outer loop, which gains margin. Light_b at 26.9 m/s goes from GM 1.67 / Ms 3.06 to 2.78 / 1.91.

**The one assumption that flips the choice (A → D, "trim ×1.95 + FF ×1.2"):** the plant world at medium-to-highway speed.
- **Identified overdamped family** (the drive's own identification): the extra FF gain adds loop-generated 1–3 Hz
  wheel motion at 15–22 m/s, so A is right.
- **Light_b world** (the prior: a lightly damped 1–2 Hz wheel mode the loop excites): D improves ALL THREE complaints.
  Hard turns go ×0.80/0.92 (lp) and ×0.76/0.74 (full); tracking +0.04..+0.07; outer GM at 26.9 m/s 2.3 vs V294 1.7.
  D would be the pick.
- r71b cannot decide between them in closed loop (harness §0.1/§0.7). A drive with exogenous excitation would.

**Wire read (§7).** One 30 s hands-off window separates A from V294 on the existing 427 tap, with no new instrument.
Regress the tap on V294's own byte-exact feedforward march and trim march:
- A reads c1 (FF) 0.99 and **c2 (trim) 1.92 [p5 1.83, p95 1.96]**;
- V294 reads c2 0.99 [0.93, 1.04], on the real r71b tap [E, a positive control through the real residual].

---

## 1. Pre-registration (`CRITERIA-robust-joint.md`) and what fired

| id | criterion | result |
|---|---|---|
| F1 | harness spot-check: lane == golden model; V294 nominal lp 5–10 tracking gain within 0.01 of 0.865 | **PASS** — 56,000 ticks on 7 cell sets inside this lens's space (b 1106..1700, a 1005/1015, C 2048, Kp schedule, lag 980/697, e_shift 1/0, Kd live) with 0 mismatches on T and S; retrodiction 0.865 by sweep_drive AND by simulate() with my own polyfit (0.865), measured 0.871 (`rj0_spotcheck_out.txt`) |
| H-SAFE-1 | rail ≤ V294's | A: +2461/−2463 [E, harness m_safe on the golden surface] |
| H-SAFE-2 | problems() empty; int32 margin ≥ 2.0 | A: none; 2.08 (a·s). **Binds**: b ≤ 1150 at a 1011; couples b to the pole (a 1015 → b ≤ 793) |
| H-SAFE-3 | trim cap ≤ 2 × 616; restart pulse @100 deg/s ≤ 2 × 144 | A: 616; 283. **Binds**: b 1120 → 286, b 1134 → 290 FAIL (`rj13_pick_linear_out.txt`) |
| H-HF-1 | max\|P/x\|, \|T/x\| over 10–25 Hz ≤ 3 × V294 | A: ×1.95 / ×1.95; \|P/x\| @20 Hz 4.06 (V294 2.08, V282 44.90) |
| H-HF-2 | stress ζ ≥ 0.8 × min(V294, open); mode13/20 ≥ 0.05 | A: every harness stress member ζ ≥ V294's (mode13 0.145→0.152, mode20 0.076→0.077, mode20_lo 0.226→0.238); extended 8–60 Hz scan worst ×0.895 (§5.3) |
| H-LOOP-1 | inner stable, Ms ≤ 1.5 incl. delay ×1.5 | A: all stable; Ms 1.252 (light_b 8 m/s), 1.266 at delay ×1.5; GM ≥ 8.3 |
| H-LOOP-2 | outer GM ≥ 0.95 × min(GM_V294, 2), Ms ≤ max(1.1 × Ms_V294, 1.5), every member × speed × relay | A: GM rel 1.67 (never below V294), Ms ratio 0.90; light_b 26.9 m/s GM 1.67 → 2.78 |
| F2 | ≥ one complaint proxy moved by the margin (hard-turn ≤ ×0.9, or tracking ≥ +0.03) on nominal AND light_b, lp AND full, no other proxy worse by > half | A: hard turns 5–10 m/s nominal ×0.83 / ×0.83, light_b ×0.68 / ×0.70 (lp/full); tracking ±0.003; 15–22 rate ≤ ×0.99 → **does NOT fire for A**. C/D: the jerk proxy at 15–22 lp ×1.08–1.22 > ×1.05 → **fires for C/D** |
| F3 | sign of the primary metric flips between members or dists → demote | A: no flip on 15 members × 2 dists. C/D: 15–22 m/s 1–3 Hz rate ×1.08–1.28 lp vs ×0.78–0.96 full → **flip → demoted** |
| F4 | pick violates any H-* in the finalist scoring | A: no (harness score(), §5) |
| F5 | a changed value unattributable in ~30 s | A: b reads as c2 in every 30 s window (§7) |
| F6 | quoting NOT-FIT magnitudes as predictions | observed: every 1–8 Hz number here is a same-batch RATIO / family envelope, labelled so |

**Process notes [E].**
- `rj2_probe_out.txt` printed J with a pre-fix weight set (2/2/2). The objective was corrected to the pre-registered
  1/1/1/1 before any grid ran (`rj3_grid.py` onward), and the probe was exploratory only.
- Stage 1 (`rj3_grid`) omitted the M_SAFE constraints. Stage 1b added them and they turned out to bind (§3).

---

## 2. The harness, spot-checked (the brief's "one tick, one retrodiction row")

- **Lane == golden model** (`lkas_fb_lag` + `lkas_rate_pid_tick`): 56,000 random ticks over 7 cell sets inside my
  search space, 0 mismatches on T and S [E].
- **Retrodiction row**: V294 nominal lp 5–10 m/s tracking gain 0.865. Two methods agree to the digit: sweep_drive, and
  simulate() with my own polyfit [E].
- **My fast linear scorer (`rj_lin.py`) == the harness's own functions** (lane_ctf, loop_frf, outer_frf, ff_tf) on V294
  and a candidate: worst relative deviation 8.7e-16 [E, `rj_lin.selftest`].
- **The harness Lane's V294 march == plib's T1k_live** on all 1,020,390 r71b ticks [E, `rj7`].

---

## 3. The search

Joint knob space, all relative to V294, every cell read from the V294 image by the harness:
- g: the FF (sub-rail) gain via the flat Kp, 960·g.
- t: the HF trim gain, Kp·b / (960·567), so b = 567·t/g.
- The fb pole f_fb, via a.
- The output lag corner, with the DC held ≤ V294's so the rail cannot rise.
- C.
- Kd with the D clamp. The sum clamp is cut 15360 → 15240 so the rail holds 2461.
- The Kp idx schedule: flat, lowboost (×s at idx ≤ 12 → 1 by idx 40), turnboost (×s at idx ≥ 56).
- kmap: Kp × k with the map Y / k. The FF is unchanged, b is divided by k, which relaxes the int32 bound cal-only.
- e_shift is derived: 2 unless b would exceed 0.95 · b_max, in which case the opcode is used.

**Ki is excluded.** The census finding stands [E, census §3(4), re-read]:
- The I term integrates E>>5 of E = 4·sp − r26. Σ r26 telescopes to the fb state, so I = an integrator of the COMMAND
  plus a lagged-rate term.
- It has no leak and no freeze on saturation, it winds up under driver torque, and it resets only at the ramp-end
  epilogue.
- No cal value makes it leak. The dead band and the I clamp only shape it:
  - a small I clamp turns it into a ± bias that follows the command sign, i.e. a hysteresis element (a limit-cycle
    source);
  - that element is the V283 class the operator rejected ("goes against what openpilot is modelling its output as, a torque").
- No wire instrument separates I.
- I could not defeat the finding, so Ki is not searched.

**Stage 1 — coarse linear grid** (`rj3_grid`, 15,552 candidates, 8 processes, 239 s, worst family member):
- g {0.9..1.4} × t {1..4} × f_fb {0.8..4 Hz} × lag {3.5..10 Hz} × Kd {0, 48} × 4 schedules;
- the H-HF/H-LOOP constraints only. Findings [E for the linear model]:
- the outer loop on light_b at highway (V294 GM 1.67) binds g. **The trim t raises it**, e.g. t 2 → 2.88, so g is only
  feasible jointly with t — the joint-search payoff;
- a faster output lag buys outer phase but costs the same HF_T budget the trim needs (lag 10 Hz = ×1.86 HF_T) → the lag stays;
- Kd 48 moves J by < 0.01 → dropped;
- a higher fb pole at equal HF gain loses low-frequency K_α and outer margin (fb 8 Hz: light_b GM 0.93) → the pole stays low.

**Stage 1b — M_SAFE included** (`rj4_grid2`, 9,408 candidates, 378 s). int32 margin ≥ 2 and restart ≤ 2× bind hard:
- t ≤ ~1.97 at a 1011;
- lower poles need b ≤ b_max/2 (kmap or the opcode to relax it; not worth it);
- C < 1024 buys restart-pulse margin, but C is **unreadable on the wire unless it binds** (≤ 0.01 % of engaged ticks at
  t 2), so it is held at 1024 (F5).

**Stage 1c — fine grid** (`rj5_fine`, 900, g 1.0..1.35 × t 1.5..2.05 × f_fb 1.7..2.4, C 1024, flat, lag held):
- the best fb pole at t ≈ 1.95 is 2.03–2.2 Hz (≤ 0.003 of J apart) → a stays 1011;
- the front runs along g up to 1.30, bound by the outer Ms of ms_free at 12 m/s and light_b at 3.1 m/s.

**Stage 2 — nonlinear byte-exact replay** (`rj6_sweep`; harness sweep_drive, mode B, the real-fork port, V294 in the
same batch; nominal / light_b / b_lo / F_hi / J_hi / tau6 × lp / full). Finalists:
- F1 = A (g 1.0, t 1.95);
- F2 = C (g 1.1);
- F3 = D (g 1.2);
- F4 (g 1.3);
- F5 (g 1.2, t 1.0, FF only);
- F6 = E (t 2.5, g 1.2).

The flip diagnostic (`rj9`) used a finer g at t 1.95 plus the planner-low-pass control. The noise-floor null (`rj17`)
used 3 byte-identical V294 copies.

**Stage 3 — the harness score()** on A and D (`rj10`, ~99 s each). Then sensitivity on 9 more members (`rj12`),
point B and the V282 HF anchor (`rj15`), the 8–60 Hz mode scan (`rj16`), and HF wheel motion (`rj20`).

---

## 4. The Pareto front (tracking vs HF exposure vs outer margin), 5 named points + the origin

`rj18_pareto_table_out.txt`. J is the pre-registered linear objective (lower = better; V294 = 0). HF = max |P/x|, |T/x|
over 10–25 Hz ÷ V294. oGMr = the worst over members of GM ÷ min(GM_V294, 2). lbGM27 = light_b outer GM at 26.9 m/s.
The last three columns are the NONLINEAR replay, V294 in the same batch, envelope over the 6 default members, lp AND full.

| point | cells (vs V294) | J | HF | oGMr | lbGM27 | restart @100 | int32 | Δ tracking (lp) | hard turn 5–10 | 1–3 Hz rate 15–22 |
|---|---|---|---|---|---|---|---|---|---|---|
| V294 | — | 0 | 1.00 | 1.00 | 1.67 | 144 | 4.06 | 0 | ×1 | ×1 |
| **B** trim ×1.5 | b 850 | −0.057 | 1.50 | 1.34 | 2.24 | 217 | 2.71 | ±0.001 | ×0.76..×0.94 | ×0.85..×1.00 |
| **A PICK** trim ×1.95 | **b 1106** | −0.107 | 1.95 | 1.67 | 2.78 | 283 | 2.08 | −0.001..+0.003 | **×0.68..×0.90** | **×0.75..×0.99** |
| **C** trim ×1.95 + FF ×1.1 | Kp 1056, b 1005 | −0.138 | 1.95 | 1.52 | 2.53 | 283 | 2.29 | +0.022..+0.036 | ×0.73..×1.00 | ×0.78..×1.09 |
| **D** trim ×1.95 + FF ×1.2 | Kp 1152, b 921 | −0.150 | 1.95 | 1.39 | 2.32 | 282 | 2.50 | +0.041..+0.065 | ×0.76..×1.10 | ×0.81..×1.22 |
| E trim ×2.5 + FF ×1.2 | Kp 1152, b 1181 | −0.209 | 2.50 | 1.76 | 2.93 | **362 ✗** | **1.95 ✗** | +0.041..+0.066 | ×0.64..×1.04 | ×0.71..×1.18 |
| X FF ×1.2 only (dominated) | Kp 1152, b 472 | +0.037 | 1.00 | 0.83 ✗ | 1.39 | 144 | 4.88 | +0.041..+0.065 | ×1.04..×1.25 | ×1.01..×1.24 |

Reading it:
- B → A → C → D is the feasible front. Moving down it trades outer margin and medium-speed loop-own motion for tracking,
  at constant HF.
- E is what the pre-registered safety caps cost. It is infeasible on H-SAFE-2 and H-SAFE-3.
- X shows an FF raise without the trim. It loses outer margin on light_b and raises jerk everywhere — never ship the FF
  raise alone.
- The pick is A: the robust point. No member and no disturbance model shows any complaint proxy worse, and it has the
  best outer margin on the front.

---

## 5. Candidate A in full

### 5.1 The cell and its record

| address | what | V294 | A | readers / record |
|---|---|---|---|---|
| `0xC63EA` (tp+0x73EA), u16 via `ld.hu` @0x28F86 | fb-lag gain b: the trim gain. K_α ∝ Kp·b/(1024−a) below the pole, damping ∝ Kp·b above it | 567 | **1106** | **one reader, no writer** [E: census c2 (Ghidra = Python) AND my own raw LE scan `rj19` with a control (a's `ld.h` @0x28F8A found); no LE32/absolute reference] |

**Lineage** (grep of `builds/**/build_v*_tva.py`: 21 scripts touch 0xC63EA; LEVER-INDEX row 33).
- **On the SUM (rate) operand**, b moved on V289 (2301 at a 875, 25 Hz). The ring moved to 16 Hz.
- On V291/V292 (958 at a 962, 9.94 Hz) it was a **REVERT**: the 7 Hz ripple re-armed.
- Stock through V288 and V293 used 1560 at a 923.
- **On the DIFF (acceleration) operand only V294's 567 has flown**, and it flew clean ("No grinding or stuttering!").
- A is the **same lever pushed further in the direction it already flew**, not a re-run and not a new lever:
  - the first flight's direction is supported by the bands (1.6–3 Hz hard-turn energy ×0.56–0.91 of r75/r76, confounded
    by the fork config) and by the harness counterfactual (V294 vs V293 ×0.77 / ×0.93);
  - the dose ×1.95 is untested, not falsified.
- The V289/V291/V292 results are a different loop (a rate servo, sum operand) and do not transfer.

### 5.2 M_SAFE [E, harness m_safe / restart_pulse / int32_margins on the byte-exact lane]
- Rail: +2461/−2463, unchanged.
- Sub-rail slope: 0.6409 T/wire, unchanged.
- Trim cap: 616 T (25 % of the rail), unchanged. C and Kp are unchanged, so the zero-command torque bound does not rise.
- The trim reaches that cap at about half V294's wheel motion: ~1500 deg/s² below the pole, or ~118 deg/s of 2 Hz-band
  rate above it (census: 2935 / 231 on V294, ÷1.95).
- On r71b the fb clamp would bind on ≤ 0.012 % of engaged ticks. That is V294's |r26| distribution × 2 [E, `rj1`]:
  p99.99 538 → 1049.
- int32 minimum margin 2.08 (a·s at the 12000 bail edge; V294 4.06); b / b_max 0.481.
- **Restart pulse after a filter bail** (fault path only: |x| > 12000, bar implausible, polarity):
  - peaks 28 / 84 / 283 / 561 T at 10 / 30 / 100 / 300 deg/s (V294 14 / 43 / 144 / 419);
  - duration above 50 T at 100 deg/s: 218 ms (V294 159);
  - this is the one safety quantity that doubles.
- Soft-EME: the lane's peak is unchanged, so nothing new is reachable [B for the governor path, inherited from ADV-V293-D1].

### 5.3 HF and "no grinding" — the margin argument the brief requires (rule 3)
- **Controller gain [E, linear, the harness M_HF].** |T/x| and |P/x| are ×1.95 of V294 at every frequency 5–30 Hz.
  |P/x| at 20 Hz is 4.06, against V294 2.08 (flew clean) and V282 44.90 (ground at 20 Hz). A is at 9 % of the flown
  grinder and inside the brief's ×3 threshold.
- **The inner loop has no crossover above 8 Hz** on any member.
  - Nominal |L| < 1 everywhere.
  - On light_b it crosses at 0.7–3.7 Hz with PM ≥ 103° [E, the harness M_LOOP].
  - Stress members: no crossing.
- **Stress modes [E for the model, B for the car].**
  - Every harness stress member's closed-loop ζ is equal to or above V294's, and above open:
    - mode13 0.152 / 0.180 / 0.147 against V294 0.145 / 0.171 / 0.146;
    - mode20 0.077 / 0.102 / 0.117 against 0.076 / 0.099 / 0.115;
    - mode20_lo 0.128 / 0.238 / 0.194 against 0.126 / 0.226 / 0.191.
  - An extended scan (`rj16`) put two-mass modes at 8–60 Hz, ζ 0.05/r2 0.2 and ζ 0.02/r2 0.5, at 5/12/25 m/s. The worst
    case is ζ_A / min(ζ_V294, ζ_open) = **0.895**: an 8 Hz, ζ 0.02, 50 %-wheel mode at 12 m/s.
  - The trim's opposing torque turns anti-damping only past ~28 Hz (phase −90°), where |T/ω| ≤ 0.9 T/(deg/s). At that
    frequency V282's same column reads ζ 0.014–0.022 (×0.2–0.3 of open).
- **Delivered torque content in the sim (mode B full / mode A).**
  - 5–9 / 9–13 / 13–17 / 17–23 / 23–30 Hz: ×1.49 / ×1.47 / ×1.62–1.67 / ×1.2 / ×1.3 of V294. In absolute terms that is
    2.6 / 1.5 / 1.0 / 0.65 / 0.30 T rms against V294's 1.7 / 1.0 / 0.6 / 0.53 / 0.23.
  - These are far below the tap's 8-count quantum.
  - On the identical recorded command, **V282's lane delivers 9.8 / 10.9 / 12.8 / 8.7 T rms** in the same bands
    (nominal; `rj15`). A is at 7–26 % of the flown grinder, band by band.
  - Under lp (the loop's own motion) A equals V294 to within ±5 % in every HF band on the stress members.
- **HF wheel motion [E for the sim, `rj20`].**
  - 3–5 Hz ×0.77–0.87 (damped) and 5–9 Hz ×0.96–1.00.
  - 9–45 Hz is ×0.98–1.03 on every member, except light_b 9–13 Hz (full) at ×1.07.
  - So the extra HF torque neither damps nor excites the HF wheel in the model.
- **Staircase** (the 100 Hz command steps): identical to V294's, because the FF is unchanged.
- **The honest limit [B].** Nothing above ~8 Hz is identified. The margin rests on the two on-car anchors
  (2.08 clean, 44.90 ground) and on stress members that are assumptions.

### 5.4 M_LOOP and the outer loop [E for the model]
- Inner: Ms ≤ 1.252 (1.266 at delay ×1.5), GM ≥ 8.3, all stable, on 12 members incl. tau9, J_hi2, kappa and the stress members.
- **Outer (the fork law linearised, relay on/off, every member × 6 speeds): GM never below V294's.**
  - light_b GM 4.5 / 4.4 / 4.0 / 3.4 / 2.6 / 1.7 → 7.8 / 7.5 / 6.8 / 5.8 / 4.4 / 2.8 at 3.1..26.9 m/s.
  - light_b Ms at 26.9 m/s: 3.06 → 1.91.
  - The trim's damping of light_b's 1–2 Hz mode is what the fork sees.

### 5.5 M_TRACK (the goal metric)
- **Closed form**, actuator branch α/cmd with the inner loop closed [E for the linear model, `rj11`]:
  - it flattens the 1.5–2.5 Hz hump;
  - light_b at 12 m/s, |α/cmd| at 1/2/3/5/8 Hz goes from 1.46 / 2.14 / 2.36 / 2.43 / 1.84 to 1.30 / 1.46 / 1.75 / 2.32 / 2.01;
  - the 1–8 Hz complex-gain R² goes 0.773 → 0.884; nominal 0.860 → 0.887.
- **Mode A literal fit** (the recorded command, dist full, per-chunk medians):
  - 1–3 Hz R² 0.324 vs 0.316 (nominal) and 0.329 vs 0.307 (light_b);
  - |G| 1.29 vs 1.44 deg/s² per count; phase unchanged within 3°;
  - the operator's literal on-road number will barely move, because the fork's P reaction dominates it (the metric report).
- **Probe transfer, 1–3 Hz, coherence 0.36–0.52:** G 0.54 vs 0.57 (nominal), phase +39° vs +37°.
- **Friction flatness** (|α/cmd| at 30 / 100 / 300 counts, nominal): 0.186 / 0.441 / 0.522 against 0.206 / 0.496 / 0.587.
  The shape is unchanged: small/large 0.36 vs 0.35. The level is ~10 % lower, because the trim adds inertia.
  **A does NOT relieve the small-signal friction deficit.**

### 5.6 M_DRIVE per complaint

Mode B, V294 in the same batch; ratio or difference; `rj8_sweep_read_out.txt`, `rj12_sens_out.txt`, `rj15_extra_out.txt`.

| member | dist | hard turn 5–10 | hard turn 15–22 | 1–3 Hz rate 5–10 / 10–15 / 15–22 | tracking 0–5 / 5–10 / 15–22 / 22+ | limit-cycle line (lp) |
|---|---|---|---|---|---|---|
| nominal | lp | ×0.83 | ×0.96 | ×0.87 / 0.94 / 0.98 | 0 / +0.001 / 0 / 0 | −5.4 dB vs −4.7 |
| nominal | full | ×0.83 | ×0.94 | ×0.85 / 0.90 / 0.95 | +0.003 / +0.002 / 0 / 0 | — |
| light_b | lp | ×0.68 | ×0.69 | ×0.77 / 0.81 / 0.80 | 0 / 0 / +0.001 / +0.003 | −0.9 dB vs +0.8 |
| light_b | full | ×0.70 | ×0.67 | ×0.67 / 0.77 / 0.75 | +0.004 / 0 / 0 / +0.001 | — |
| b_lo / F_hi / J_hi / tau6 | lp | ×0.75–0.90 | ×0.92–0.99 | ×0.84–0.88 / 0.92–0.95 / 0.98–0.99 | ±0.001 | — |
| same | full | ×0.78–0.86 | ×0.89–0.94 | ×0.79–0.86 / 0.86–0.91 / 0.91–0.95 | ≤ +0.004 | — |

**Measured on r71b** (the same code, hands-off chunks): hard turns 14.9 (5–10) / 7.6 (15–22) deg/s; tracking
0.873 / 0.871 / 0.583 / 0.830 / 0.924 by band.

---

## 6. Sensitivity of the pick to every plant uncertainty

Nonlinear replay, lp / full, V294 same batch (`rj12`, `rj6`, `rj15`).

| uncertainty | member | hard turn 5–10 (lp / full) | 1–3 Hz rate 15–22 (lp / full) | tracking | verdict |
|---|---|---|---|---|---|
| J ×0.5 | J_lo | ×0.80 / ×0.83 | ×0.99 / ×0.95 | ≤ +0.003 | holds |
| J ×2.5 | J_hi | ×0.90 / ×0.86 | ×0.98 / ×0.94 | ≤ +0.003 | holds (weakest J corner) |
| J ×4 | J_hi2 | ×0.93 / ×0.90 | ×0.98 / ×0.93 | ≤ +0.002 | holds, weakest overall: a heavier wheel makes the doubled trim relatively smaller |
| b ÷1.8 at speed | b_lo | ×0.75 / ×0.78 | ×0.98 / ×0.91 | ≤ +0.004 | holds |
| b ×1.5 | b_hi | ×0.88 / ×0.87 | ×0.99 / ×0.96 | ≤ +0.002 | holds (hard turn 15–22 lp ×1.03, inside the ±7 % floor) |
| Fc ×0.5 | F_lo | ×0.80 / ×0.82 | ×0.98 / ×0.94 | ≤ +0.003 | holds |
| Fc ×2 | F_hi | ×0.86 / ×0.83 | ×0.99 / ×0.95 | ≤ +0.004 | holds |
| delay 6 / 9 ms | tau6 / tau9 | ×0.82 / ×0.83 | ×0.98 / ×0.94 | ≤ +0.003 | holds |
| rack→wheel κ | nominal_kappa | ×0.82 / ×0.83 | ×0.98 / ×0.94 | ≤ +0.003 | holds |
| 13 Hz mode | mode13 | ×0.82 / ×0.83 | ×0.99 / ×0.95 | ≤ +0.003 | holds; ζ 0.145 → 0.152 |
| 20 Hz modes | mode20 / mode20_lo | ×0.82–0.83 / ×0.83 | ×0.98 / ×0.94–0.95 | ≤ +0.003 | holds; ζ up |
| prior world | light_b | ×0.68 / ×0.70 | ×0.80 / ×0.75 | ≤ +0.004 | holds, strongest |

**No member and no disturbance model flips the direction of A on any complaint proxy.** The spread is ×0.67..×0.99, and
it is widest where the plant's own damping is smallest.

---

## 7. How one short drive attributes the change on the EXISTING wire (rule 6)

**Instrument** [E, `rj7_wire_read`]: the 427 tap (the delivered lane torque gp-0x6b38), the 0x18F rate and the 0xE4 command.
- Per 30 s window of hands-off engaged tap frames, OLS: `T_tap = c0 + c1·FF_V294(cmd) + c2·TRIM_V294(cmd, x)`.
- FF_V294 and TRIM_V294 are the byte-exact V294 null and live-minus-null marches on the drive's OWN recorded 0xE4 and
  0x18F.
- The FF is linear in Kp at a fixed map, so c1 reads g. The trim at a fixed pole is linear in Kp·b, so c2 reads t.

| window reading | c1 (FF) median [p5, p95] | c2 (trim) median [p5, p95] | method |
|---|---|---|---|
| V294, the real r71b tap (23 windows) | 0.989 [0.965, 0.995] | 0.986 [0.934, 1.043] | real data |
| **A (b 1106)**, synthetic tap = its byte-exact march + r71b's REAL tap residual | 0.989 [0.965, 0.995] | **1.923 [1.828, 1.958]** | positive control |
| D (Kp 1152, b 921) | 1.190 [1.166, 1.195] | 1.927 [1.821, 1.974] | positive control |
| FF ×1.2 only | 1.189 | 0.983 | positive control |

Every one of the 23 windows separates A from V294. The byte-exact identity:
- the real r71b tap against the V294 march: 3.64 counts rms;
- a synthetic A tap against the V294 march: 14.5 counts rms, and against its own march 3.64.

**Reads, in order:**
1. c1 = 0.99 ± 0.03 confirms the FF is untouched. This is the check that no Kp or map bytes changed.
2. c2 ≈ 1.9 means the b cell is live.
3. The sign of c2: c2 < 0 is sign inversion. Stop and revert. It is structurally impossible for a b-only edit, but it
   is the positive check.
4. The band behind his first complaint: the 1.6–3 Hz wheel rate in hard turns at 5–15 m/s, and the 1–3 Hz rate at
   15–22. **Predicted DOWN.** Magnitude is not predicted (NOT FIT); the family envelope is ×0.67–0.93.

**The sentence a null licenses:**
> *"If c2 reads within [0.9, 1.1] on a 30 s hands-off window, b is not live — the drive is V294 and says nothing about
> V295. If c1 reads 0.97–1.00 and c2 1.8–2.0, the trim is live and doubled as designed; then an unchanged 'jerky on hard
> turns' — or unchanged 1.6–3 Hz hard-turn wheel-rate energy — means that EPS-side damping at 1–5 Hz does not limit that
> symptom, and no further trim inside the cal space will (the next lever is fork-side, or a new operand, i.e. a cave).
> The loose complaints are not tested by this build at all: c1 = 1.00 is the proof that the static gain did not move."*

---

## 8. Physics honesty: the ceiling on "α tracks cmd" (`rj11_ceiling_out.txt`, closed form, friction off)

- **Below ~1 Hz no value set can do it.** α/cmd has phase +87° to +165° at 0.5 Hz on every member: the command holds
  angle against the spring (k 6.5–80 T/deg).
  - Every candidate, including a ×32 V282-class gain, leaves |α/cmd| at 0.5 Hz within ±10 %.
  - Tracking α there needs +k·θ (hold torque from angle, positive feedback on angle). That is a CAVE, or the fork's
    FF-on-angle, and it is out of scope.
- **1–8 Hz: the trim flattens, the HF guard caps it.**

  | build | R² (1–8 Hz complex gain), nominal at 12 m/s | R², light_b at 12 m/s | \|P/x\| at 20 Hz |
  |---|---|---|---|
  | V293 (no trim) | 0.821 | 0.520 | — |
  | V294 | 0.860 | 0.773 | 2.08 |
  | A | 0.887 | 0.884 | 4.06 |
  | ×3 (the HF cap) | 0.907 | 0.936 | 6.1 |
  | ×8 at a 2 Hz pole | 0.954 | 0.971 | 16.6 |
  | ×32 at a 16 Hz pole | 0.945 | 0.964 | 54.5 |

  The ×32 row is **V282's grinding class**. Flat α/cmd is bought with exactly the HF gain the record says grinds.
- **Small signal:** friction makes |α/cmd| at 30 counts 0.36× that at 300. The trim cannot change that ratio: 0.351 → 0.356.
  - The lever for small-signal friction is a relay or friction compensation, the V293 r73 class (4 Hz chatter), or the fork.
- **The output lag (5.05 Hz)** puts −22° / −45° on the FF at 2 / 5 Hz. Moving it spends the same HF budget the trim
  needs, and the search dropped it.
- **Net:** the best safe values raise the actuator branch's 1–8 Hz flatness by ~+0.03 R² (identified) and ~+0.11
  (light_b). They leave ≤ 1 Hz and the small-signal deficit where they are.
- On the drive's literal metric, which the fork's P reaction dominates above 1 Hz, expect ±0.02.

---

## 9. Knobs excluded, and why (one line each)

- **Ki** (0xC63E6): see §3. It integrates the command with no leak or anti-windup; V283's rejected class; no instrument.
- **Kd / D clamp** (0xCB7D4 / 0xC61B6): < 0.01 of J.
  - It raises the rail to 2481 unless the sum clamp (frozen on 272/272 images) is also cut.
  - It is a one-tick-in-ten command kick.
  - Nothing on the wire separates D.
- **C** (0xC62E6): lowering it buys restart margin and a lower trim cap. But it binds on ≤ 0.01 % of ticks, so a short
  drive cannot see it (F5). It is held at 1024.
- **Output lag** (0xC63EC/EE, never moved on 272 images): it costs HF_T at the same rate the trim does, for less benefit.
  Lag 7 Hz fronts were dominated.
- **fb pole a** (0xC63E8): the optimum at t 1.95 is 2.03–2.2 Hz, within 0.003 of J of V294's own. Lower poles hit the
  int32 bound at 2× margin.
- **e_shift opcode** (0x29D76) / **kmap**: only needed for a lower pole or t > ~2. Neither pays under the caps.
- **Kp schedule** (lowboost / turnboost): its best J was below flat-g at every structure. A lowboost is a small-signal
  gain bump near the relay, i.e. limit-cycle risk.
- **FF gain g** (Kp level or map Y): runner-ups C/D, §10.

---

## 10. Runner-ups, with numbers

- **C — Kp 1056 flat ×28, b 1005** (FF ×1.1, trim ×1.95).
  - Tracking +0.022..+0.036 lp in every band and member. Predicted on-car (measured + Δ, BELIEF): 0.90 / 0.90 / 0.87 /
    0.96 by band.
  - Hard turn 5–10 ×0.73..×1.00; 1–3 Hz rate 15–22 ×1.08–1.09 lp on 5 of 6 members (×0.78–0.95 full).
  - Outer light_b GM 2.53 at 26.9 m/s; sub-rail 0.7049 T/wire; trim cap 678 T.
  - Wire read: c1 1.09, c2 1.92.
  - Demoted by F2/F3.
- **D — Kp 1152 flat ×28, b 921** (FF ×1.2, trim ×1.95).
  - Tracking +0.041..+0.065 (10–15 m/s: +0.083..+0.097); turn-hold 15–22 +0.064..+0.107.
  - Oversteer guard (measured + worst Δ): ≤ 0.977 tracking, ≤ 0.991 turn-hold at 22+ → no band exceeds 1.0.
  - Jerk proxy at 15–22 m/s lp on the 14 identified members: 1–3 Hz rate ×1.13–1.22, hard turn ×1.19–1.33 (1–3 Hz rate
    ×1.09 with the planner low-passed); full ×0.74–0.96.
  - Staircase HF ×1.2; trim cap 739 T (30 %); outer light_b GM 2.32.
  - **The pick if the car is the light_b world** (§0).
- **Record of the cell C and D add, `0xCB994`** (the Kp bank, 28 records; LEVER-INDEX row 38): 248-class on V282, 120 flat
  on V293, 960 flat on V294. On the diff operand only 960 has flown. 1056 and 1152 are untested. The FF raise they make is
  the same quantity as a lower fork LAF or a steeper map (the V293 ×6 map precedent).
- **B — b 850** (trim ×1.5): the conservative dose. HF ×1.5, restart 217, hard turn ×0.76..×0.94.
- **Not recommended — E (b 1181 with Kp 1152)**: breaks the pre-registered int32 (1.95) and restart (362) caps.
  - It is the only way to get D's tracking with more trim.
  - It is listed so the cost of those caps is visible (J −0.209 vs −0.150).
  - Relaxing H-SAFE-3 is defensible, because the restart pulse is fault-path only. But that is the orchestrator's call,
    not a post-hoc edit of mine.

---

## 11. Surprises, defects and reports (nothing outside this folder was edited)

1. **Harness defect (report, not fixed): the x-noise realisation is drawn per BATCH ROW**
   (`PlantBatch.rng.normal(0, x_noise, B)`), so a candidate and its "same-batch" V294 see different noise.
   - Null control: three byte-identical V294 copies in one batch (`rj17`).
   - Floor on "ratio vs V294": 1–3 Hz rate ±0.4–2 %, hard turn 15–22 / 22+ lp up to ±7 %, tracking ±0.001, full ±0.5 %.
   - The same candidate (A) read hard turn 15–22 lp ×0.96 / ×0.98 / ×1.00 in three different batches.
   - Effect: small lp ratios at 15–22 / 22+ m/s are noise-limited. None of this report's decisions rests on one; the g
     effect at 1.1–1.2 is 4–10× the floor.
2. **The FF-gain flip is partly planner-driven and partly loop-generated** [E, `rj9`]. With desiredCurvature
   low-passed at 0.8 Hz, D's lp 1–3 Hz rate at 15–22 falls from ×1.22 to ×1.09. It is not all "following the planner's
   1–3 Hz content better".
3. **Under dist full the g-effect is hidden by construction** [B]. The replayed residual carries V294's own
   planner-driven motion as a fixed torque, so the counterfactual cannot scale it. lp is the more trustworthy direction
   for a static-gain change.
4. **My stage 1 omitted M_SAFE**, and those constraints bind (§3). Fixed in stage 1b. **The first probe printed J with
   non-registered weights** (§1).
5. **The pick moves the restart pulse ×2** (fault path). It is the one safety quantity A changes materially.

---

## 12. Files (all in `analysis-2020accord/studies/v295/design/robust-joint/`)

| file | what |
|---|---|
| `CRITERIA-robust-joint.md` | pre-registered constraints, objective, FAIL sentences |
| `rj0_spotcheck.py` / `_out.txt` | harness spot-check (lane vs golden; retrodiction row, two methods) |
| `rj1_route_facts.py` / `_out.txt`, `rj1_cmd_psd.npz` | \|wire\|/idx distribution, command spectrum, V294 r26 distribution |
| `rj_lin.py` | fast linear scorer (self-test vs harness functions: 8.7e-16) |
| `rj_cands.py` | the joint knob generator, summary and pre-registered objective |
| `rj2_probe.py` / `_out.txt` | one-knob probes (exploratory; pre-fix weights) |
| `rj3_grid.py` / `_out.txt` (json in `_scratch/`, gitignored, 21 MB) | stage 1: 15,552 candidates |
| `rj4_grid2.py` / `_out.txt` (json in `_scratch/`, 14 MB) | stage 1b: 9,408 with M_SAFE |
| `rj5_fine.py` / `_out.txt` (json in `_scratch/`) | stage 1c: fine grid |
| `rj6_sweep.py` / `_out.txt` / `.json`, `rj8_sweep_read.py` / `_out.txt` | stage 2 nonlinear replay + per-complaint read |
| `rj7_wire_read.py` / `_out.txt` | the wire-attribution null + positive controls |
| `rj9_flip_diag.py` / `_out.txt` / `.json` | fine g, planner-low-pass control |
| `rj10_score.py`, `rj10_score_F1/F3.{json,txt}`, `rj14_score_read.py` / `_out.txt` | harness score() of A and D |
| `rj11_ceiling.py` / `_out.txt` | physics ceiling |
| `rj12_sens.py` / `_out.txt` / `.json` | sensitivity on 9 more members + stress HF |
| `rj13_pick_linear.py` / `_out.txt` | b scan against the caps; per-member linear tables of the named points |
| `rj15_extra.py` / `_out.txt` / `.json` | point B; V282 HF anchor |
| `rj16_hf_modes.py` / `_out.txt` | 8–60 Hz two-mass scan, trim damping sign |
| `rj17_noise_floor.py` / `_out.txt` / `.json` | the identical-cells noise-floor null |
| `rj18_pareto_table.py` / `_out.txt` / `.json` | the named Pareto table |
| `rj19_b_reader_scan.py` / `_out.txt` | raw LE reader scan of 0xC63EA with control |
| `rj20_hf_rate.py` / `_out.txt` / `.json` | HF wheel motion, V294 vs A |
| `rj21_curves.py` / `.json` | before/after curve data for the artifact (T/ω, \|P/x\|, surface, α/cmd, \|L\|) |
