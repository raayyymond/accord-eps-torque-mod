# REFUTE V299 — stability / nonlinear (2026-10-02)

**Target:** `docs/specs/design/v299/DESIGN-V299-SYNTHESIS-2026-10-02.md` (V298 + 21 in-place cave bytes: hard freeze 512 → 1229,
opposing-hand clause removed, asymmetric A3 bound; fork G4 O1 gate, lead 0, 0.4 s takeover, configs A and B).
**Role:** REFUTER, stability and nonlinear behaviour. ANALYSIS ONLY: nothing was built, flashed or sent, and no fork, firmware,
golden-model, STATE, lineage or git file was touched. Python = `bin_decompile`. Ghidra was not needed, because the cave arithmetic
was taken from the synthesis' §1.2 listing and checked bit-for-bit against S2Lane (control C1). Classifier interruptions: 0.

## VERDICT: **FAIL — do not build as specified.**

The verdict rests on two pre-registered criteria that fired:

- **FC fired.** The design's own drive criterion F4 is "a hands-off turn-in at ≤ 10 m/s overshoots θsp by > 6°". My model predicts
  it fires on a 60° hands-off turn-in at 10 m/s. This holds in two independent engines and on both plant members, under configs A
  and B alike (S2 engine 4/4 columns, my engine 8/12; V298 0/4 and 1/12). The cause is integrator windup, which the freeze
  removal un-masks in the 6–12.5 m/s band. In that band A3 has no cap, and 16|θ|+B exceeds ICL at large angles. The synthesis
  scored turn-ins at 3 and 8 m/s only. The drive card's own Part A ("engaged turning at 3–10 m/s … one hands-off turn-in")
  exposes this point.
- **FD fired for config B, and B's own falsifier X3 fires in simulation.** At B's slew rates the twist re-arms an O1 relay through
  the **80-ms 600-raw debounce path, not through the hard path**: 3.1–3.9 O1 entries per turn, stall-surges ×3 and 5–10 Hz wheel
  rate ×3.4 versus config A. Hard-path O1 entries occur on 50–62 % of hands-off turn-ins at ≤ 8 m/s (S2 engine 16/32, mine 20/32;
  X3's bar is > 50 %). Both engines also find B no faster than A at 3–6.5 m/s. The synthesis' "next step" fix, a 2-frame
  hard-path debounce, removes **none** of it in my model.

**Path to PASS** (BELIEF; each item must be re-scored):

1. Extend the A3 cap through the 6–12.5 m/s band, for example imm16 `1382 → 2880` and cap `4096 → 6144` (4 bytes in place).
   In my engine this brings the 10 m/s overshoot from 7.5° to 2.9° worst, with hold error ≤ 0.8°.
2. Fly config A only and drop B.
3. Add a read for the ms_free curve-hold ring (D4 below).

Everything else I attacked held: GATE 2 linear (inherited), friction hunting, the light hand at every hold age, firm-hand
release, and the twist tail on route 79.

---

## 0. FAIL criteria — written BEFORE any script ran (`refute/PREREG-stability-nonlinear.txt`)

| id | criterion (abridged) | fired? |
|---|---|---|
| FA | a loop V299 operates in has PM < 30° / GM < 6 dB / ρ ≥ 1 where V298 was at the bar | **no.** Every sub-bar point is inherited; the inner bytes are identical (§3) |
| FB | sustained self-excited cycle (≥ 3 cycles, ≥ 0.5° or ≥ 5 deg/s rms 1–10 Hz) hands-off, absent in V298 | **no** (T3: 0/96 rows; T8: ≤ 2 tail cycles in both) |
| FC | my sim predicts the design's OWN F3/F4/F5/F6b/X3 firing in a plausible manoeuvre inside the r79 envelope | **YES.** F4 at 10 m/s (§1). X3 for config B (§2) |
| FD | relay (1229 freeze or fork O1) cycling ≥ 2/s for ≥ 1 s hands-off at nominal twist | **YES for config B** (§2). A is borderline: ≤ 3 entries per s, 1.2 per turn, V298 8.5 |
| FE | 13–17 / 18–22 Hz closed-loop gain > 1.10 × V298 | **no** for loop gain (identical bytes). The excitation is ×1.02–1.31 under B (§6) |
| FF | light-hand release lurch > V298's at matched hold age, or > 8° at ≥ 8 m/s, holds ≤ 10 s | **no.** V299 is bounded at 4–5.8° swing; V298 reaches 26–28° (§4) |

---

## Defect list (most severe first)

| # | what | sev | evidence class | fix |
|---|---|---|---|---|
| D1 | **F4 self-trip: hands-off turn-in overshoot 7.0–7.5° at 10 m/s / 60°** (both members, A and B; V298 0.8–6.0). At 11.75 m/s / 45–60° it is 7.5–10.8° (V298 3.2–9.6). The firmware freeze removal is the main term (fw-only 6.7° median); the fork's G4/lead-0 adds to it (fork-only 5.1°) | **HIGH** | model, 2 engines | A3 cap through v ≤ 2880 (12.5 m/s) at 6144 S → 1.6 [3.0]° at 10 m/s, 3.9 [7.6]° at 11.75 (BELIEF; needs GATE 2 PD/PID re-score and a C4 authority read). Or re-scope F4 and say so on the page. Conditional integration (freeze while \|E\| > 5–8°) is **rejected**: it strands the hold at 12–42° error |
| D2 | **Config B re-arms a twist relay through the 80-ms G4 debounce.** 3.1–3.9 O1 entries per 60/90° turn at 3–6.5 m/s (A 0.9), stall-surges 2.7–3.4 per turn (A 0.9), wheel 5–10 Hz rms 4.2–4.5 deg/s (A 1.2, ≈ V298). B_nohard and B_h2 do not fix it; cap-only and clip-only each stay clean. It is the **combination** | **HIGH** | model (mine; S2 agrees in direction: ss 2.0–2.5 vs 1.0–1.1, r4–8 5.1–5.9 vs 2.9–3.7) | drop config B from this drive; redesign the authority dose separately (cap OR clip, not both) |
| D3 | **X3 fires in simulation and B is not faster than A.** Hard-path O1 entries occur on 50 % (S2) / 62 % (mine) of ≤ 8 m/s hands-off turn-ins, and 58 % / 75 % at 3–6.5 m/s. t90 for B vs A, S2 engine: 1.07/1.20/0.94/0.86 s vs **0.99/1.04/0.96/0.96 s**. Mine: 1.26–1.38 vs 0.96–1.13 s. The synthesis' A estimate "≈ 1.2/1.4 s" was **never simulated** and is wrong by about 0.2–0.45 s | **MED-HIGH** | model, 2 engines | correct the A row; A alone carries the note-2 gain at 3–8 m/s |
| D4 | **V299 removes V298's incidental damping of the ms_free curve-hold mode** (PM 6.3° in my GATE 2; S1 6.1°). At 10–13 m/s the step ring is ×1.5–4 larger on the ms_free family (11.75 m/s b_lo×ms_free: 6.84/4.96/3.60° vs V298 1.67/0.92/0.40° with the twist residual on). Route 79's "no ring" was measured with a 5–12 % random PD duty that V299 sets to ≈ 0 | MED | model; the family itself is disputed | pre-register a 0.4–0.8 Hz curve-hold ring read at 10–13 m/s in the drive read (amplitude > 1° or > 2 half-cycles = revert) |
| D5 | **GATE 2 at route 79's D fraction (×0.55, P ×0.93) × curve hold 2.5 m/s² × age 10.** PID PM 1.6° (b_lo×ms_free, 11 m/s), and **24.5° on a non-ms_free member** (b_lo×J_hi, 8 m/s). Inherited from V298 (identical bytes), but V299 spends more time in PID (freeze duty 8–12 % → 0) | MED (inherited) | linear model (mine) | declare it on the page; it is the operator's ms_free ruling plus a D-shortfall item |
| D6 | The unwind claim "4.2° → 0.6°" holds on r79F only. On b_lo×J_hi the unwind past centre is V299-A median 3.9° (V298 1.3°), B max 6.5–7.1° | LOW-MED | model | report it per member |
| D7 | Config B raises 13–17 / 18–22 Hz lane-torque excitation in 3–8 m/s turn-ins to ×1.02–1.31 of V298 (×2.7–3 of A) | LOW | model (no 13–22 Hz plant mode in the family) | drop B (D2) |
| D8 | Light-hand outward release swing saturates at 5.0–5.8° at 8 m/s, at the edge of F3's 5° "straight" clause. It occurs on a curve, so F3 does not literally fire. It is age-independent because the asymmetric bound limits it | LOW | model | none; for information |
| D9 | My O1-loop GM at Trt 90 ms with lead 0 is **6.1 dB** (S1 8.3 dB). It passes, but at the bar | LOW | linear model | none |
| D10 | Process: my first `rsn_t8_msfree.py` ran 42 s, over the < 30 s rule. It was restructured to 19.1 s; every number reported is from the compliant run | — | — | — |

---

## Controls — the engine is the bytes (EVIDENCE)

| control | method | result |
|---|---|---|
| C1 lane = S2Lane = the in-place bytes | `rsn_control.py`: my `rsn_engine.Lane` (V298 / V299 rules, written from the synthesis §1.2 listing + Honda I/P/D/fade/olag/fwd, cal cells read from the V298 image, sha 177abf04 asserted) vs `s2_time.S2Lane` (V298 / D1c columns). 6000 ticks × 128 columns, random θ/sp/abe/word, ramp mix | **T and I mismatches 0**. S2Lane = D1Lane = the in-place bytes by the synthesis' H1 (0/5748) |
| C1 can fail | V299 rule on my lane vs S2's V298 column | 187,893 mismatches |
| C2 G walk | my walk vs `score_time.glut` on 0..12000 | 0 mismatches |
| C3 GATE 2 anchor | my injection model, nominal, straight, 3.1 m/s | PM 79.0° / GM 24.0 dB / fc 1.67 Hz (S1 anchor 83.7 / 23.2 / 1.81) |
| C4 GATE 2 anchor | worst ms_free curve hold | **6.3°** at b_lo×ms_free 11.75 m/s a 2.5 age 10 (S1: 6.1°, ρ 0.9985) |
| C5 second engine | F4 / X3 / A-vs-B re-run on S2's own `s2_time.run` (unchanged) | agrees in sign and size (§1, §2) |

The engine (`rsn_engine.py`) is mine: lane, 100 Hz fork (from `carcontroller._update_angle` and
`lateral.apply_steer_angle_limits_vm` at Dom `2712e1336`, plus the synthesis' F1–F5 diffs), twist word, runner and metrics. Shared
inputs are **data only**: the plant family table (`v294_plant.family`, r79F = nominal + route 79's Coulomb 156/85 T, Fs 1.25 Fc),
the angle-correction LERP for κ, route 79's CarParams (VM), and M3's twist fit (`d1_r79.json`).

---

## 1. D1 — the 10–11.75 m/s overshoot (F4)

Each turn-in is a linear ramp at the planner's rate (`plan_rate`, jerk 5 m/s³ via the VM, cap 320), followed by a 2.5 s hold and
an unwind. The overshoot is max(θ) − A during the hold. F4 = > 6° or > 15 % of the turn at ≤ 10 m/s.

**My engine** (`rsn_t1_turnin.py`, 2 members × 2 seeds per cell):

| v m/s | A° | V298 ovs med [max] | V299-A | V299-B | F4 columns V298 / A / B |
|---|---|---|---|---|---|
| 8 | 60 | 1.4 [2.6] | 4.3 [5.0] | 4.3 [5.9] | 0/4 · 0/4 · 0/4 |
| **10** | **60** | 2.8 [7.5] | **7.1 [7.5]** | **7.3 [7.5]** | 1/4 · **4/4 · 4/4** |
| 10 | 90 | 6.8 [7.5] | 7.8 [8.9] | 7.8 [8.9] | 3/4 · 4/4 · 4/4 |
| 11.75 | 60 | 6.3 [10.5] | 10.3 [10.8] | 10.5 [10.8] | (F4 is ≤ 10 m/s) |
| 11.75 | 67.9 | 7.7 [10.3] | 11.3 [12.0] | 10.7 [12.8] | — |

**S2's own engine** (`rsn_xcheck_s2.py`; V298, SYN-A = D1c fw + G4/lead 0/take 0.4 at cap 120 and clip ×1.0, SYN-250 = config B;
2 members × 2 seeds):

| v | V298 per column | SYN-A | SYN-250 | F4 columns |
|---|---|---|---|---|
| 8 | −4.8 / 1.8 / 3.2 / −0.5 | 3.7 / 3.7 / 5.0 / 5.0 | 3.7 / 3.7 / 4.3 / 5.8 | 0 · 0 · 0 |
| **10** | 6.0 / 3.5 / 3.1 / 0.8 | **7.5 / 7.5 / 6.7 / 6.9** | **7.5 / 7.5 / 7.0 / 7.1** | **0 · 4/4 · 4/4** |
| 11.75 | 10.9 / 8.5 / 10.8 / 5.7 | 10.7 / 10.8 / 9.7 / 9.7 | 10.8 / 10.8 / 10.2 / 10.2 | — |

**It is not an artefact of the ramp shape** (`rsn_t1c_smooth.py`: raised-cosine turn-ins of 1.0 / 1.5 / 2.5 s). At 10 m/s / 60° the
overshoot is V298 5.7/4.9/5.1, V299-A **7.5/7.5/5.1** and B 7.5/7.5/5.2, with F4 in 0/12 vs 6/12 vs 6/12 columns. At 11.75 m/s /
45° it is V298 3.2/5.1/5.4 vs V299 7.5/7.4/5.8–7.2.

**Mechanism (EVIDENCE: my trace `dbg1.py`, V299-B r79F 11.75 m/s 67.9°).** The wheel lags the setpoint by about 25° through the
slew. With no freeze, I runs at ≈ 18 S/tick and reaches **ICL 8192 S at t = 1.6 s**. The wheel then passes the setpoint to
**78.5° (+10.6°)**, and I unwinds at Ki over about 2 s. A3 never acts here: v-word 2707 ≤ 2880 gives shift 4 and **no cap**
(cap only ≤ 1382), and the bound 16·|θ|+1250 exceeds 8192 above 43°. V298 avoided most of this only because the reaction-twist
freeze (> 512, or > 300 opposing) toggled during the slew, which is the synthesis' own M4. The synthesis quantified M4 at
3 and 8 m/s only.

**Attribution and fixes** (`rsn_t1b_attrib.py`, 30/60/90° pooled, 2 members × 2 seeds):

| system | 6.5 m/s | 8 | **10** (F4 cols) | 11.75 | \|err\| at hold end, worst |
|---|---|---|---|---|---|
| V298 | −0.1 [3.8] | 0.0 [3.1] | 2.3 [6.8] (1/12) | 4.9 [8.9] | 7.3 |
| V299 fw + V298 fork | 2.1 [3.0] | 1.8 [3.3] | 6.7 [8.9] (**8/12**) | 10.0 [13.9] | 2.4 |
| V298 fw + fork A | 0.2 [1.9] | 0.3 [2.8] | 5.1 [6.7] (3/12) | 5.5 [11.1] | 7.7 |
| V299-A | 2.2 [5.3] | 1.9 [5.0] | 6.6 [8.9] (**8/12**) | 9.7 [11.9] | 2.4 |
| **A + A3 cap 6144 through 12.5 m/s** (hypothetical) | 1.1 [3.0] | 0.2 [2.5] | **1.6 [3.0] (0/12)** | 3.9 [7.6] | 3.9 (6.5 m/s), ≤ 1.2 above |
| A + freeze while \|E\| > 8° / 5° (hypothetical) | −12.2 | −13.0 | −26.9 | −41.4 | **12–42 (P alone cannot hold the curve)** — rejected |

---

## 2. D2 / D3 — config B's twist relay, X3, and A versus B

**My engine** (`rsn_t4_relay.py`, r79F, 60/90°, 4 seeds, twist α-scale ka 1.0 / 1.3; the fit is R² 0.31). All turns are pooled
over 3–8 m/s:

| system | ka | hard-path O1 per turn | O1 entries per turn | ≥ 2 O1 entries in a 1-s window | 1229-freeze episodes per turn | stall-surges per turn |
|---|---|---|---|---|---|---|
| V298 | 1.0 | (600-instant) | 8.5 | 81 % of turns (max 9/s) | 23.4 (512/300) | 5.1 |
| V299-A | 1.0 | 0 % | 1.2 | 47 % (max 3/s) | 0.0 | 1.2 |
| **V299-B** | 1.0 | **62 %** | 2.1 | 66 % (max 3/s) | 0.8 | 1.8 |
| V299-A | 1.3 | 6 % | 1.5 | 53 % | 0.1 | 1.4 |
| **V299-B** | 1.3 | **88 %** | **4.3** | **84 %** (max 4/s) | 1.9 | **3.4** |

**Splitting what in B causes it** (`rsn_t4b_bsplit.py`, V299 fw, 60/90°, 2 members × 3 seeds):

| fork | 3 m/s t90 / O1 / ss / w5–10 | 5 m/s | 6.5 m/s | 8 m/s |
|---|---|---|---|---|
| A | 0.99 / 0.9 / 0.9 / 1.16 | 1.13 / 0.9 / 0.9 / 1.24 | 0.96 / 0.9 / 0.9 / 1.26 | 1.19 / 1.2 / 1.2 / 1.52 |
| **B** | 1.26 / **3.1 / 2.7 / 4.24** | 1.38 / **3.2 / 2.8 / 4.43** | 1.36 / **3.8 / 3.2 / 4.40** | 1.18 / 1.9 / 1.9 / 2.52 |
| B, no hard path | 1.30 / 3.1 / 2.7 / 3.75 | 1.30 / 3.2 / 2.8 / 4.47 | 1.42 / 3.9 / 3.4 / 4.35 | 1.17 / 2.3 / 2.2 / 3.39 |
| B, hard path held 2 frames | 1.34 / 3.2 / 2.6 / 4.32 | 1.32 / 2.8 / 2.6 / 4.28 | 1.38 / 3.5 / 3.2 / 4.41 | 1.25 / 2.8 / 2.6 / 3.50 |
| B, cap only (clip ×1.0) | 1.14 / 1.0 / 0.8 / 1.88 | 1.17 / 0.9 / 0.9 / 1.87 | 1.08 / 1.0 / 1.0 / 2.02 | 1.13 / 1.3 / 1.3 / 2.22 |
| B, clip only (cap 120) | 1.12 / 1.1 / 1.1 / 1.67 | 1.31 / 1.0 / 1.0 / 1.53 | 1.07 / 1.2 / 1.2 / 1.78 | 1.06 / 1.3 / 1.4 / 1.92 |

**Reading (BELIEF on the twist model).** With cap 250 and clip ×1.6 together, the reaction twist stays above 600 raw for 8 frames
during the slew. G4 then latches O1, the setpoint snaps to the wheel, the torque collapses, and the twist falls below 500. Release
starts the 0.4 s takeover, the re-slew rebuilds the twist, and the cycle repeats. **This is note 4's mechanism re-armed one level
up, through the debounce, not through the hard path.** The synthesis' §6 null sentence names "a 2-frame hard-path debounce" as the
next step; per the table above that step would change nothing.

**S2's own engine** (`rsn_xcheck_s2_ti.py`, 60°, 2 members × seeds 0–3). Via-hard is re-derived from S2's recorded word at the
fork's i−2 sample:

| cand | v | t90 median [range] | ovs max | O1 entries per turn | turns with via-hard O1 | stall-surges | r4–8 |
|---|---|---|---|---|---|---|---|
| SYN-A | 3 / 5 / 6.5 / 8 | **0.99 / 1.04 / 0.96 / 0.96** | 2.9 / −1.4 / 5.3 / 5.0 | 1 / 1 / 1 / 1 | 0 / 0 / 1 / 1 of 8 | 1.1 / 1.1 / 1.0 / 1.0 | 3.4 / 3.7 / 2.9 / 3.3 |
| SYN-250 (B) | 3 / 5 / 6.5 / 8 | 1.07 / 1.20 / 0.94 / 0.86 | 3.7 / −0.2 / **6.8** / 5.9 | 2.5 / 2.5 / 2.0 / 1.0 | **4 / 6 / 4 / 2 of 8** (50 %) | 2.0 / 2.1 / 2.5 / 2.0 | 5.4 / 5.8 / 5.9 / 5.1 |
| V298 | 3 / 5 / 6.5 / 8 | 1.53 / 1.75 / 1.72 / 2.09 | 2.5 / −1.5 / 0.4 / 0.8 | 7.5 / 7.5 / 6.5 / 10.5 | (600-instant) | 1.5 / 3.5 / 5.1 / 5.8 | 6.0 / 7.8 / 9.2 / 11.0 |

The synthesis printed V299 t90 "0.78 / 0.85" against A "≈ 1.2 / 1.4". The first pair is the r79F-only median over seeds 1–3. The
second was **inferred, not simulated**. Over both members and four seeds, A is as fast as B at 3–6.5 m/s and B is faster only at
8 m/s, by 0.1 s.

**What route 79 itself shows (EVIDENCE, `rsn_r79_twist.py`).** Hands-off is defined as latActive with no steeringPressed within
±1 s, 8.4 min in total.

| band | hands-off min | \|raw\| p99 / p99.9 / max | > 1200 raw entries per min | > 600 held 8 frames, per min | > 1229 words (V299 freeze) per min | > 512 words (V298) per min |
|---|---|---|---|---|---|---|
| 0–5 m/s | 0.7 | 801 / 998 / 1177 | 0 | 1.39 | 0 | 138.5 |
| 5–8 | 0.6 | 658 / 973 / 1114 | 0 | 0 | 0 | 89.8 |
| 8–12.5 | 1.8 | 511 / 924 / 1114 | 0 | 0 | 0 | 63.1 |
| > 12.5 | 5.3 | 418 / 758 / 1184 | 0 | 0 | 0 | 25.8 |

At V298's slew rates the 1229 / 1200 thresholds clear the measured twist (EVIDENCE). P(> 600 raw) rises steeply with
|α|: 0.5 % below 100 deg/s², 15 % at 300–600, **26 % at 600–1000**. Only **7 hands-off frames below 8 m/s** have |α| > 1000. Config B
operates exactly where route 79 has no data, so the twist behaviour above 1000 deg/s² is an extrapolation of an R² 0.31 fit. The
drive card's X3 is the right falsifier, but two engines already predict that it fires.

---

## 3. GATE 2 — my own derivation (`rsn_t5_gate2.py`, 7.3 s)

**Method.** I built a float mirror of the lane's linear structure: the two-sample fb sum of the 100 Hz-held angle (age 0 / 10 ms),
G(v), Kp 112/256, Ki 40 per-tick with e5 = E′/32 (PID) or frozen (PD), Kd 48 on the 37/128 EMA of the motor-frame rate (κ at the
operating angle), fade 254/256, OB 507 / OA 992, fwd 5346, and 2 ms transport. It is closed around the linearised plant
(J, b, k·sech²) and measured by sinusoidal injection at the plant input (L = T/u, fundamental). The grid is 6 members × 11 speeds ×
{straight, curve hold 2.5 m/s²} × age {0, 10} × D {×1, ×0.55 with P ×0.93} × {PID, PD}, at 26 frequencies from 0.35 to 40 Hz.

| block | min PM (where) | PM < 30 points | note |
|---|---|---|---|
| PID, D ×1 | **6.3°** (b_lo×ms_free, 11.75 m/s, curve hold, age 10, fc 0.56 Hz) | 13 of 264, all ms_free curve hold at 10–13 m/s | matches S1's 6.1° (ρ 0.9985). Non-ms_free worst is 41.6° |
| PID, D ×0.55 (r79) | **1.6°** (b_lo×ms_free, 11 m/s, curve hold, age 10) | 26 of 264 | includes **b_lo×J_hi curve hold, age 10: 29.3 / 27.1 / 24.5° at 3.1 / 5 / 8 m/s** (non-ms_free) |
| PD, D ×1 / ×0.55 | 48.7° / 39.1° | 0 | the frozen state is always comfortable |
| O1 loop, lead 0 (V299), Trt 30 / 60 / 90 ms | GM 17.2 / 9.9 / **6.1 dB**, PM ≥ 55.8° | 0 | S1 gave 11.4 / 9.4 / 8.3 dB |
| O1 loop, lead 0.06 (V298) | GM 5.1 / 4.1 / **1.0 dB**, PM 23.8° at 90 ms | 129 with GM < 6 | lead 0 is a real gain (EVIDENCE that removing the lead adds margin) |

**Reading.**

- The inner linear loop is V298's by bytes (C1), so **FA does not fire**.
- Two inherited facts matter for V299 specifically. First, the low-PM ms_free curve-hold mode (D4). Second, V298 spent 5–12 % of
  settled hands-off time in PD by accident of the twist freeze, and V299 sets that to about 0 % (route-79 replay 11.4 → 0.4 %,
  synthesis §4; my sims 8–12 % → 0). **V299 therefore runs the sub-bar PID points the whole time V298 sometimes did not.**
- At the 5–30 Hz end the linear closed-loop gain is identical. See §6 for the excitation.

---

## 4. Light hands of increasing age, and firm-hand release (FF / F3 / F5)

**Light hand** (`rsn_t2_lighthand.py`). The hand is applied to a hold at the speed's turn angle (5 m/s 30°, 8 m/s 20°,
15 m/s 8°, 25 m/s 4°). Hand words are 400 and 550 (the band neither the 1229 freeze nor G4's 600-raw debounce covers) and 900
(the G4 band). Hold ages are 1/2/4/8 s; hand models are a stiff position hand and a constant force (0.29 T per word, BELIEF);
directions are toward centre and outward. The read is the swing past the plan in the 1.5 s after release.

| case | V298 swing by age 1/2/4/8 s | V299-A | V299-B |
|---|---|---|---|
| position hand, 5 m/s, 400 words, outward | 0.3 / **26.1 / 18.9 / 20.1** | 4.1 / 4.2 / 4.1 / 4.2 | 3.3 / 4.3 / 4.2 / 4.3 |
| position hand, 8 m/s, 400 words, outward | 0.5 / **18.8 / 25.6 / 27.9** | 5.6 / 5.6 / 5.8 / 5.6 | 2.6 / 5.2 / 5.2 / 5.2 |
| position hand, 8 m/s, 550 words, outward | 0.1 / 0.0 / 5.2 / 13.3 | 3.5 / 5.5 / 5.5 / 5.0 | 5.2 / 5.0 / 5.2 / 5.0 |
| position hand, 15 m/s, 400 words, outward | 0.4 / 1.4 / 2.1 / 4.2 | 1.1 / 3.0 / 4.8 / 4.8 | 0.4 / 3.0 / 4.8 / 4.8 |
| position hand, 15 m/s, 550 words, toward centre | −0.2 / −0.1 / 0.0 / 0.1 | 1.1 / 2.0 / 2.2 / 2.4 | 1.3 / 1.8 / 2.4 / 2.4 |
| force hand, any v / word / direction (worst) | ≤ 2.4 swing; lurch up to 19.9 (5 m/s, 900 words, outward) | ≤ 2.7 swing; lurch ≤ 9.8 | ≤ 3.7 swing |

V299's swing **saturates by about 4 s at 4–5.8°, independent of hold age**: the asymmetric bound caps the I at B ≈ 200 T toward
centre. V298's opposing-freeze relay, interrupted by twist dips below 300, lets I wind to the symmetric bound and produces
18–28° releases, which is the N1 class. **FF does not fire.** D8 records the 8 m/s swing, which sits at F3's 5° straight clause on a
curve. F5 (droop > 4° toward centre) does not fire either: the toward-centre position-hand swings are ≤ 2.4°.

**Firm-hand override** (`rsn_t7_override.py`). The hand drags the wheel to centre at 1500 or 2500 words, holds 1.5 s, and is
released suddenly or slowly (word and grip fall over 0.6 s through 1229 → 600 → 500 raw).

- The freeze lands at the word's ramp time: 13–20 ms at 5–8 m/s (the twist helps) and 100–186 ms at 15 m/s (V298: 7–33 ms).
- The lane tap under the hand is 6–13 % of rail, the same for all three systems.
- The release overshoot is V299 ≤ 4.7° vs V298 ≤ 4.2°, and release t90 is 0.27–0.71 s.

Nothing fires.

---

## 5. Friction limit cycles and holds (FB) — `rsn_t3_friction.py`, `rsn_t8_msfree.py`

**Holds and slow tracking.** Scenarios were holds at 0 / 2 / 6° after a 1° step, and a 1.33 deg/s drift. Speeds were 3–25 m/s.
Members were r79F, r79F_hiFs (Fs 1.6 Fc), ms_free_r79F and b_lo×J_hi, with the twist residual on. **No row has ≥ 3 sustained
cycles in either system (0 of 96).** Wheel-rate rms in 1–10 Hz is ≤ 1.34 deg/s and |e| p95 is ≤ 0.92° for V299 (V298 1.54°). With
Coulomb friction the system **sticks rather than hunts**, and the small-correction stick (M1) is unchanged. That is a known miss,
not a new one.

**ms_free curve hold** (age 10, 1° step, 26 s; columns are the first three half-peaks / tail cycles ≥ 0.25° / tail p-p):

| v | member | twist on? | V298 | V299-A |
|---|---|---|---|---|
| 11 | b_lo×ms_free (friction off) | yes | [0.47, 0.34, 0.06] / 0 / 0.23 | **[3.69, 2.28, 0.99]** / 0 / 0.27 |
| 11.75 | b_lo×ms_free (friction off) | yes | [1.67, 0.92, 0.40] / 0 / 0.23 | **[6.84, 4.96, 3.60]** / 0 / 0.41 |
| 11 | ms_free_r79F | yes | [0.24] / 0 / 0.68 | [1.44, 0.80, 0.43] / 2 / 1.00 |
| 11.75 | b_lo×ms_free_r79F | yes | [1.08, 0.66, 0.65] / 0 / 1.45 | [1.84, 1.10, 0.90] / 2 / 1.41 |
| 10–13 | r79F (nominal) | yes | ≤ 0.29 | ≤ 0.39 |

The ring is decaying, so FB does not fire. The amplitude, however, is ×1.5–4 V298's on the ms_free family once V298's random
5–12 % PD duty is removed, and that is D4. On the nominal member there is no difference.

---

## 6. 5–30 Hz — `rsn_t6_hf.py`

The linear closed-loop gain is **identical by bytes**: C1 gives identical outputs whenever no freeze differs, and the P/D/sum/olag
cells are unchanged. **FE does not fire.**

The lane-torque excitation in 13–17 / 18–22 Hz relative to V298 is:

- hands-off turn-ins at 3 / 5 / 8 m/s: **config A ×0.32–0.46**, **config B ×1.02–1.31**;
- 10–25 m/s turn-ins: ×0.16–0.65 for both configs;
- lane keeping: ×0.82–1.03.

The wheel-rate 5–10 Hz in turn-ins at 3–8 m/s is V298 4.7–6.6, A 1.5–1.6 and B 3.3–4.9 deg/s. Config B puts back most of the
ratchet-band content that A removes (D2, D7). The r71b family has no 13–22 Hz mode, so wheel content above 10 Hz cannot be judged
here.

---

## 7. Fork-side O1 lead and the I under O1 (arithmetic, BELIEF on Trt)

With lead 0 the O1 setpoint is the wheel Trt ago, so E = 16(θ(t−Trt) − θ). The never-frozen I (600–1229 words with O1 active)
integrates this into a position memory of the drag: about 1.1·k·Δ S per degree, with k = Trt in ticks. At Trt 25 ms that is
≈ 28 S ≈ 4.5 T per degree dragged, which is small and resists the driver. It is consistent with the synthesis' declared M5
(+17 % hand force). The firm-hand runs in §4 show no lurch from it.

---

## 8. What I ran (all < 30 s; outputs in `_scratch/v299_REFSN/`)

| script (`v299_design/refute/`) | does | wall |
|---|---|---|
| `rsn_engine.py` | my lane + fork + twist + runner (module) | — |
| `rsn_control.py` | C1/C2 controls vs S2Lane / glut, plus the negative control | 5.2–6.3 s |
| `rsn_t1_turnin.py` | T1 turn-in sweep (6 speeds × 3 A × 2 members × 2 seeds × 3 systems) | 8.7 s |
| `rsn_t1b_attrib.py` | D1 attribution + 2 hypothetical fixes | 4.4 s |
| `rsn_t1c_smooth.py` | D1 under raised-cosine plans | 4.5 s |
| `rsn_xcheck_s2.py` | D1 on S2's engine | 3.0 s |
| `rsn_t4_relay.py` | X3 / relay census, ka 1.0 / 1.3 | 6.7 s |
| `rsn_t4b_bsplit.py` | B split + debounce variants | 5.6 s |
| `rsn_xcheck_s2_ti.py` | A vs B + X3 on S2's engine | 4.4 s |
| `rsn_r79_twist.py` | route-79 twist tail (EVIDENCE) | 0.1 s |
| `rsn_t2_lighthand.py` | light hands × ages | 9.2 s |
| `rsn_t7_override.py` | firm hand + release | 4.8 s |
| `rsn_t3_friction.py` | hunting / holds | 17.6 s |
| `rsn_t8_msfree.py` | ms_free curve-hold ring (compliant version) | 19.1 s (first version 42 s, D10) |
| `rsn_t5_gate2.py` | GATE 2 by injection, plus the O1 loop | 7.3 s |
| `rsn_t6_hf.py` | 5–30 Hz excitation | 22.6 s |

**Not modelled (declared).**

- No 13–22 Hz plant mode exists in the family.
- The twist model is M3's fit (R² 0.31), extrapolated above |α| 1000 deg/s².
- The hand-word-to-plant-torque ratio (0.29 T per word) is BELIEF.
- The plant matches route 79 best at 10–13 m/s (synthesis M11). That is where D1 sits, which strengthens D1.
- My GATE 2 grid starts at 0.35 Hz: lower crossovers (nominal at 13–17.5 m/s) show as "none" and are excluded.
