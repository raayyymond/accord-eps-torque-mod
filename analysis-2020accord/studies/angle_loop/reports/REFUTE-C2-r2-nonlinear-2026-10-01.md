# REFUTE C2 rev 2 — NONLINEAR lens (2026-10-01)

**Verdict: REFUTED. Do not flash any of P2, F2, D2a or B0r.** There are two independent reasons.

1. **No C2 rev 2 design exists to clear.** The synthesis judge stopped before choosing a design. Its primary and its
   fallback are both `"none"`, and `DESIGN-ANGLE-LOOP-C2-rev2-2026-10-01.md` was never written. A refuter cannot clear
   an empty object.
2. **The lens was run on all four candidate implementations anyway** (rev2-A's P2 and F2, rev2-B's D2a and B0r). It
   finds failures that neither revision declared, in all four implementations. The failures that decide the verdict:
   - **Turn-hold at 15–19 m/s fails the goal's 0.90 bar.** The hold ratio is 0.80–0.87 in curves at 1.5 m/s² and
     0.72–0.84 at 2.0 m/s². This happens on every member, including nominal and the friction-free control.
   - **The cause is the integrator clamp.** ICL 4096 caps the I at about 657 T. The identified spring load at those
     curves is 850–1170 T.
   - **The goal's own tracking metric, rerun in the time domain on the operator's own route, misses its bar.** Using
     route r71b's steering-angle paths, the slope is 0.85–0.86 at 15–22 m/s and 0.89–0.92 at 8–15 m/s.
   - **Small corrections at 8–15 m/s show dwell-then-jump.** Both revisions say there is none at those speeds.

Lens: NONLINEAR. It covers Coulomb friction and stiction, the 0.1° quantisers, the integer lane (sar 5, the e5 floor),
the cave's exact arithmetic, the fade, the sign-hold gate, ramp-in, light-hand and firm-hand override, co-steer,
release, and the 510 ms timeout hold. Members: nominal, bc, F_hi and b_lo×J_hi. Hold ages: native (1–10 ticks) and
+h10 (11–20 ticks). Speeds: every 0.25 m/s from 8 to 30 m/s, plus the knots 11.9 and 26.9, plus 3.1 and 5 m/s for
context. Nothing was built, flashed or sent. Ghidra was used read-only (decompile and dry-run disassembly), and nothing
was saved.

---

## 0. The object handed to this refuter

The C2 rev 2 synthesis payload says *"I stopped before finishing, so there is no judgement"*. `primary.id` and
`fallback.id` are both `"none"`, `design_doc` is `"not written"`, and `files` is `[]`. **EVIDENCE**, by `ls`:
`docs/specs/design/` holds `…C2-rev2-A-…` and `…C2-rev2-B-…` but no `…C2-rev2-2026-10-01.md`.

That alone returns `refuted = true`. The brief says *"If you cannot verify a decision-bearing claim yourself, say which
and return refuted = true"*, and no claim of a chosen design exists. Two revisions do exist on disk, though, and each
has a primary and a fallback. Leaving them unexamined would hand the orchestrator nothing usable. The user's
instruction is that multiple designs and implementations be evaluated. So the whole lens was run on all four:

| revision | role | implementation | D operand | table | cave hex (on disk) |
|---|---|---|---|---|---|
| rev2-A | primary | **P2** | fresh 1 kHz EMA gp-0x6abe, Kd 34, cave guard | 6 knots | `c2/rev2A/c2_cave_P2.hex` |
| rev2-A | fallback | **F2** | 100 Hz-held gp-0x6a56, Kd 20 | 6 knots | `c2/rev2A/c2_cave_F2.hex` |
| rev2-B | primary | **D2a** | as P2 | 7 knots | `panel/D-structure/ds_cave_D2a.hex` |
| rev2-B | fallback | **B0r** | as F2 | 7 knots | `panel/D-structure/ds_cave_B0r.hex` |

Shared by all four: Kp 112 flat, Ki 56, ICL 4096, DCL 10240, DB 0, cals a 0 / b 8192 / C 65535, the A2 and B2 guards,
and the I freeze on |tq| > 512 or ramp not full.

---

## 1. Independence and controls (how the numbers below can be trusted)

| # | what | method | result |
|---|---|---|---|
| C1 | the cave arithmetic | I wrote a **V850E2 mini-interpreter** from the ISA formats (`nl_cave.py`) that executes the four caves' bytes. It is compared with my own scalar mirror of the listed arithmetic. Inputs: random registers and RAM, the 0x7FFF sentinel, the ±13000/13001 validity edges, the table knots ±1, \|tq\| 511/512/513, and ramp 0/0x7FFF/0x8000/0xFFFF. Every register outside the scratch set is checked unchanged. | **EVIDENCE: 0 mismatches** in 21 155 (P2, F2) and 21 320 (D2a, B0r) cases. G(v) also matches for every v from 0 to 9000 plus 500 random values above. Minimum G is 536 for P2/D2a and 539 for F2/B0r, both above 512, so the sar 5 I path still sees at least 1 per 0.1° at every speed. |
| C2 | the downstream lane | My own dry-run disassembly of `0x29D60..0x29F80` on the V294 program (209 instructions), read after the decompile of `FUN_00028ea6`. | **EVIDENCE.** r26 is not read between `0x29D7A` and its write at `0x29F76`, except by the P2/D2a `mov r26,r8`. r8, r9 and r13 are written before they are read. r10 (DB) is loaded at `0x29D6E` before the hook. The freeze return at `0x29D7E` with r6 = 0 gives exc = 0 when DB = 0. The I clamp is `0x29DA0 ld.hu ICL; shl 10; sar 3` plus `cmovgt`/`cmovle`. The cave's scratch set is therefore dead after it returns. |
| C3 | the V295 cal | Read LE from the V295 image (sha `5c044d65…52ed`) by my own code, then compared with `lane_mirror_v295.load_cal`. | **EVIDENCE: identical**: PCL 15360, SCL 15360, OCL 3072, output lag 992/507, gate 1 / dz 102, fwd 5346, fadeA, fadeB. fadeB is 255 for \|tq\|>>5 ≤ 16. The fade and the I freeze therefore both begin at \|tq\| = 512. |
| C4 | my whole closed loop | My lane (`nl_sim.py`, written from C1–C3) and my own Karnopp plant, compared with the designers' engine (rev2-A `score_time.run`, which uses ds_time / DSLane / PlantVec). Same deterministic inputs, sensor noise set to 0 in both. | **EVIDENCE:** bit-exact (\|Δθ\| = 0, \|ΔT\| = 0) on rh at 11.9 m/s nominal, s02 at 17 m/s b_lo×J_hi, and tmo at 26.9 m/s F_hi. Within 0.015° and 4 T counts on ov_light400 at 10 m/s bc. **The designers' numbers in their own scenarios reproduce. Every refutation below comes from scenarios, amplitudes or speeds their suites did not run.** |

A second confirmation: the native-age values reproduce rev2-A's own declared numbers. Light-hand lurch is 7.11° on
nominal, 7.70° on bc and 10.40° on b_lo×J_hi, against rev2-A's 7.1 / 7.7 / 10.4. Firm-hand lurch on b_lo×J_hi at
8 m/s is 7.24°, against rev2-A's 7.2.

---

## 2. Findings

### F1: BLOCKING (all four implementations, both revisions). Turn-hold and goal tracking fail at 15–22 m/s; the integrator clamp sets the ceiling

**What happens.**
- The I is clamped at ICL 4096 S. Through the fade (254/256), the output lag (DC 0.990) and the forward gain
  (5346/32768), that is **about 657 T** (arithmetic, **EVIDENCE**).
- The identified spring at 17 m/s is k = 79.7 T/deg with sat(17) = 21.2°. So the I alone can hold only about 8.7° of
  wheel. At L 2.83 m and SR 16 that is about 1 m/s².
- Beyond that angle, P must carry the rest. P is 60 T/deg at 17 m/s (Kp_eff 595), so the residual error grows quickly.

**Hand check at 17 m/s and 2.0 m/s²** (target 17.95°). Solving `657 + 59.6·(17.95 − θ) = 1691·tanh(θ/21.22)` gives
θ ≈ 13.25°, a hold ratio of **0.738**. The simulation gives **0.73–0.74**.

**Turn-hold** (`nl_turnhold.py`). Ramp 1.5 s, hold 8 s, ratio taken over the last 2 s. The goal's bar is ≥ 0.90.

| a_lat | 13 m/s | 15 | 16 | 17 | 18 | 19 | 20 | 22 |
|---|---|---|---|---|---|---|---|---|
| 1.0 m/s² (nominal, P2) | 1.00 | 0.99 | 0.99 | 0.98 | 1.00 | 1.00 | 1.01 | 1.01 |
| **1.5 m/s²** (nominal, P2) | 0.97 | **0.86** | **0.83** | **0.81** | **0.87** | 0.93 | 0.99 | 0.99 |
| **2.0 m/s²** (nominal, P2) | **0.89** | **0.78** | **0.75** | **0.73** | **0.79** | **0.84** | **0.89** | 0.99 |
| 2.0 m/s², b_lo×J_hi (P2) | 0.91 | 0.80 | 0.77 | 0.75 | 0.80 | 0.85 | 0.90 | 0.99 |

- F2, D2a and B0r agree with P2 to within 0.01–0.02 on every cell, and so do bc, F_hi and the aged hold.
- **The friction-free nominal twin gives the same numbers** (0.73–0.74 at 17 m/s, 2.0 m/s²). This is the clamp, not
  friction.
- 1.5–2.0 m/s² at 15–19 m/s (54–68 km/h) is an ordinary ramp or arterial curve.

**The goal's own tracking metric, in the time domain, on the operator's own paths** (`nl_realref.py`).
- Method: route r71b's engaged, hands-not-pressed steering-angle paths are the reference. There are 6 runs (147 s) at
  8–15 m/s, 6 runs (154 s) at 15–22 m/s and 2 runs (58 s) above 22 m/s. Each run is simulated at its median speed.
  The score is the OLS slope of the 0.5 Hz-low-passed angle on the reference, which is the metric's definition in
  angle space.
- 8–15 m/s: **0.89–0.92**.
- 15–22 m/s: **0.85–0.86**.
- Above 22 m/s: 1.00.
- These values hold for all four implementations and all four members, and for the friction-free twins.
- **Attribution** (`nl_realref_diag.py`):

| band | slope at scale 1.0 | at 0.3× / 0.1× | ICL lifted to 16383 (diagnostic only) |
|---|---|---|---|
| 8–15 | 0.900–0.904 | 0.99–1.00 | 0.997–0.998 |
| 15–22 | 0.851–0.856 | 0.99–1.00 | 0.997–0.998 |

  A linear loop would not depend on scale; this one does, and lifting the clamp removes the deficit.
- On r71b, **11 % of engaged 15–22 m/s frames** and 4.9 % of engaged 8–15 m/s frames sit beyond the angle at which the
  clamp binds. The clamp angle is about 9.8° at 15–22 m/s and about 38° at 8–15 m/s.

**Why the revisions missed it.**
- rev2-A's turn-hold is \|T_ref(0.02 Hz)\| ≥ 0.998, which is linear and cannot see a clamp.
- Both time suites used harness_time's A_TURN: 5° at 19 m/s and 3° at 26 m/s, about 0.6 m/s². At those angles the
  spring load (≤ 390 T) never reaches the 657 T ceiling.
- rev2-A predicts turn-hold ≥ 0.97 and a goal metric of 0.961–1.011. rev2-B predicts turn-hold 0.99 and a goal metric
  of 0.958–0.961.
- **Neither revision declares a turn-hold or tracking miss above 15 m/s**, and neither has a stop band for it.
  rev2-A's own §8.2 defines *"a band ≥ 8 m/s with on-car turn-hold < 0.90 over ≥ 60 s"* as FAILED.

**EVIDENCE / BELIEF.**
- EVIDENCE: the clamp arithmetic (my disassembly), the 657 T ceiling (arithmetic), the simulation, and the hand
  solution.
- BELIEF: the spring's shape at large angles. k(v) is the r71b ident. The tanh saturation sat(v) = 19.3 + 546·e^(−v/3.01)
  is the prior hold map. With a linear spring the load would be larger and the shortfall worse; with an earlier
  saturation it would be smaller.
- BELIEF: SR 16 and no understeer in the a_lat-to-angle conversion. The r71b-path test needs no SR assumption.

### F2: HIGH (all four; for rev2-B the whole band is undeclared, for rev2-A the 8–10 and 12.5–15 m/s parts are). Dwell-then-jump in small corrections at 8–15 m/s

The record detector (`nl_sim.dwell_jump`) was run on sinusoid references the revisions never used: ±0.3° at 0.1 Hz,
±0.5° at 0.2 Hz, and ±1° at 0.3 Hz. These are lane-keeping-sized corrections (`nl_small.py`, per-speed detail in
`small.txt`). **The friction-free twin gives 0 events everywhere.**

| reference | member | 8–10 m/s | 10–12.5 m/s | 12.75–15 m/s | ≥ 15.25 m/s |
|---|---|---|---|---|---|
| ±0.3° 0.1 Hz | nominal | 3–5 events per 30 s at 9–10 m/s, jumps 0.22–0.32° | 3–5, ≤ 0.32° | 2 at 13 m/s (0.21°) | 0 |
| ±0.3° 0.1 Hz | bc / F_hi / b_lo×J_hi | 2–11, ≤ 0.43° | 6, ≤ 0.43° | 1–6, ≤ 0.34° | 2–3 at 15.25 m/s (≤ 0.21°); 0 from 15.5 m/s |
| ±0.5° 0.2 Hz | bc / F_hi | 2–6, **0.65–0.75°** | 6, ≤ 0.73° | 1–4, ≤ 0.61° | 0 |
| ±1° 0.3 Hz | bc / F_hi | 0 | 1–5 at 11–11.75 m/s, **jumps 1.09–1.26°** | 0 | 0 |

Band totals over the 0.25 m/s grid are in `lens_report.txt`. For example, mic03 bc gives 39–44 events at 8–10 m/s and
48–50 at 12.75–15 m/s per implementation.

The revisions' claims:
- rev2-A: *"no dwell-then-jump event in the sinusoids at ≥ 13.25 m/s on any member"*. Its declared dwell-then-jump
  bands are 3–7 m/s, 10–12.5 m/s (M2, hold slips) and highway holds (M11).
- rev2-B: *"no dwell-then-jump above 5 m/s"* and *"dj 8–12.5 = 0"*. **Its time scorer's speed set is
  {3, 5, 8, 10, 12.5, 15, 19, 26, 30}, which skips 10.25–12.25 m/s**, exactly where G bottoms out (536 at 11.75 m/s,
  Kp_eff 234, 23.5 T/deg). This is EVIDENCE from the `SCORE-TIME-c2rev2B.txt` header.

Mechanism: at the 10–12.5 m/s gain dip, P needs 0.8° (nominal) to 1.6° (F_hi) of error to break the static friction.
The I (PI corner 0.62 Hz) has to wind first, so the wheel dwells and then jumps. **EVIDENCE**: simulation plus the
friction-free control. **BELIEF**: whether this exceeds V282 on the car. V282 cannot be simulated, which is why both
revisions handle the low-speed band as a declared miss. Here the claim being refuted is "none".

Hold slips (rh, 6 s holds) begin at 9.5 m/s on nominal and at 8.5 m/s on F_hi (1–5 per speed). That is just below
rev2-A's declared 10–12.5 m/s M2 band: LOW, a band-edge gap.

### F3: HIGH for rev2-B, LOW for rev2-A. Override release lurch on b_lo×J_hi

| member / age | light hand (word 400 or 511, I winds to ICL), worst ≥ 8 m/s | firm hand (word 2400, I frozen), worst ≥ 8 m/s |
|---|---|---|
| nominal, native | 7.11° (11.75 m/s) | ~4° |
| b_lo×J_hi, native | **10.40° (11.75 m/s); 8.96–9.16° at 8–10; 7.7° at 12.75** | **7.0–7.25° (8 m/s)** |
| b_lo×J_hi, +h10 | **10.78° (P2, D2a) / 10.60° (F2, B0r)** | **8.30° (P2, D2a) / 8.00–8.03° (F2, B0r)** |

- **rev2-B** pre-registered *"lurch light ≤ 8°, lurch firm ≤ 8°"* and reports PASS at 6.3–6.8° and 4.1–5.7°. It never
  ran b_lo×J_hi in the time domain, on the stated premise that *"the LINEAR combined corners (b_lo×J_hi, …) carry no
  distinct nonlinear time signature"*. **That premise is false.** b_lo×J_hi has the largest lurch of any member, and it
  breaks rev2-B's own light-hand bar by 2.3–2.8°.
- **rev2-A** declares M6 as ≤ 10.6° on b_lo×J_hi at native age. The aged value is 10.78°, 0.18° over: a quantification
  gap, not a new class. Its firm-hand b_lo×J_hi figure of 7.2° reproduces at native age. Aged, it is 8.3°.
- A torque-source light hand (300 T, word 500) gives ≤ 6.3°, so the stiff-hand form above is the worst case.

### F4: MEDIUM (all four). Small-signal in-phase tracking collapses at the gain dip

Measured at 11.75 m/s (wire regression gain; friction-free in brackets):

| reference | F_hi | bc | friction-free |
|---|---|---|---|
| ±1° at 0.3 Hz | **0.23–0.24** | 0.42 | (0.87) |
| ±0.5° at 0.2 Hz | **0.49–0.53** | — | (1.01) |
| 0.3·A at 0.5 Hz | **0.10–0.11** | — | (0.32) |

The fit gain (amplitude) stays at 0.79–1.36, so this is phase lag: the wheel stick-slips behind the reference.

- rev2-A declares M4 using the amplitude fit gain (0.85–1.17) and the stuck %, which hides the in-phase collapse. Its
  §4.3 does list s05 at 0.22 on nominal.
- rev2-B reports neither.
- Above 0.2 Hz the goal metric's weight is only 2–4 %, so this is the "loose" feel more than the slope. It is a
  quantification gap, not a gate breach.

### F5: LOW. The timeout hold mid-motion is under-quantified

If the fork stops mid-sinusoid (`tmos`), the wheel moves **up to 2.35°** (F_hi, 10.25 m/s) onto the last held setpoint
during the 510 ms. rev2-A declares only the held-turn deviation (≤ 0.39° nominal, ≤ 1.0° F_hi). The behaviour itself
("hold the last valid command") is declared as M12. rev2-B does not run the timeout at all.

### What PASSES this lens (EVIDENCE: simulation, every column, both ages, at ≥ 8 m/s)

- **Fail-safe paths hold.**
  - 0xE4 sentinel: \|T\| ≤ 68 counts 50 ms after the fault, decaying.
  - Timeout: T = 0 from the sentinel + 0.25 s, on every column, in both the held-turn and the mid-motion scenario.
  - Request drop: T = 0 by 150 ms.
- 0 int32 wraps.
- No hunting limit cycle: at most 2 ω-reversals in the last 1.5 s of any hold.
- 5–30 Hz torque in holds ≤ 0.60 counts (bar 2.0).
- Engage-under-load droop ≤ 6.3° (6.5° aged) on b_lo×J_hi at 8 m/s, consistent with rev2-A's M7 (≤ 6.9°).
- Co-steer release droop ≤ 2.6°.
- The dead-band creep lag at ≥ 8 m/s is ≤ 0.32°.
- **The hands-off torque-word freeze** (route a6 duty by \|ω\|, BELIEF on transfer) moves the 8–15 m/s r71b-path slope
  by less than 0.01. It is not a material effect next to F1.

---

## 3. Why this is a refutation and not a declared miss

The brief: *"A pre-declared, quantified miss whose stop band covers it is NOT a refutation; an undeclared one is."*

- **F1** is not declared anywhere in either revision. Both predict PASS for turn-hold and for the goal metric at every
  speed of 8 m/s and above.
- **F2** contradicts the explicit "none" claims: rev2-B above 5 m/s, and rev2-A at 13.25 m/s and above. It also falls
  outside rev2-A's declared bands (8–10 m/s and 12.5–15 m/s).
- **F3** breaks rev2-B's own pre-registered 8° bar.

None of these has a stop band: rev2-A's R3\* covers 0.5–5.5 Hz rings, not a steady hold error or a stick-slip snap.

**The pass must be able to say "do not flash", and here it does.**

What a revision would need to clear this lens (a report, not licence to act):
1. Re-gate turn-hold at curve sizes set by lateral acceleration (≥ 2 m/s² at 13–22 m/s) with the integrator clamp
   modelled. Then either size ICL to the identified spring load or declare the miss with its band. Lifting ICL changes
   the light-hand lurch (F3), so the two must be re-scored together.
2. Run dwell-then-jump on ±0.3–1° corrections over the full 0.25 m/s grid, including 10.25–12.25 m/s.
3. Run b_lo×J_hi and the aged hold through the override scenarios.

---

## 4. Files and reproduction (all `python`, the bin_decompile env, fixed seeds)

Scripts are in `analysis-2020accord/studies/angle_loop/refute_c2r2_nonlinear/`. The text outputs quoted on this page
are copied to `refute_c2r2_nonlinear/out/`, which is tracked. The npz caches stay in
`_scratch/angle_loop/refute-c2r2-nonlinear/` (gitignored, regenerable).

| script | what it does | output |
|---|---|---|
| `nl_cave.py` | V850 interpreter vs mirror, four caves; exit 0 = all pass | stdout |
| `nl_sim.py` | the independent lane, plant, sensors and fork; metric helpers | — |
| `ctl_vs_designers.py` | control C4: my simulation vs rev2-A's engine | stdout |
| `nl_lens.py run 8` | the full lens: 19 scenarios × 4 members × 4 implementations × 2 ages × 93 speeds | `lens_*.npz` |
| `nl_report.py` | per-band tables | `lens_report.txt` |
| `nl_summary.py` | worst-case summary | `summary.txt` |
| `nl_small.py` | small-correction per-speed detail with friction-free twins | `small.txt` |
| `nl_turnhold.py` | turn-hold by lateral acceleration | `turnhold.txt` |
| `nl_realref.py [frz]` | the goal metric on r71b's paths | `realref.txt`, `realref_frz.txt` |
| `nl_realref_diag.py` | scale and ICL attribution | `realref_diag.txt` |

Nothing was flashed, sent or built, and no design file, image or fork file was modified.
