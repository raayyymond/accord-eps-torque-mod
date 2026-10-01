# REFUTE C3, round 1: the NONLINEAR lens (2026-10-01)

**Verdict: REFUTED. Do not flash C3-P or C3-F as designed.**

The nonlinear lens found two undeclared failures at speeds of 8 m/s and above. Both apply to the primary and to the
fallback, and they decide the verdict:

1. **The A3 integral bound limits the light-hand release lurch in one direction only** (HIGH; finding N1).
   - It works when the driver's hand holds the wheel *toward centre*. That is the only direction the common scorer
     tests.
   - It does not work when the hand holds the wheel *further from centre*: tightening a curve, or nudging the car on a
     straight. In that case the bound |θ|·slope + 1250 grows with the angle the hand creates, so the I winds up to
     the bound or to ICL 8192.
   - On release, the wheel swings past the setpoint toward centre by up to:
     - **15.9–23.7°** at 8–15 m/s, and 8.2–12.7° at 15–22 m/s, under the design's own stiff-hand convention;
     - **13.1–14.6°** at 8–12.5 m/s with a consistent sensor at κ_T = 2.0 T/word, a value the E2 design itself included
       in "every hand model";
     - **10.6°** at 12.75 m/s for a 5° straight-road nudge.
   - The design pre-registered an 8° bar and claims **4.1° light / 3.2° firm**, "bounded", with "κ does not enter" (H-ovr).
     Both claims are false in this direction, and the case is not declared.
   - It is not a C3-only problem: P2 shows the same class. Above 12.5 m/s, though, C3's ICL 8192 makes it worse than
     P2: 23.7° against 14.6° at 12.75 m/s.
2. **The G-P48 speed table drops below G = 512 between 11.4 and 12.2 m/s** (HIGH; finding N2). For C3-F the window is
   10.8–12.85 m/s.
   - Below 512, Honda's integer I quantum becomes one-sided: e5 = ((E·G)>>8)>>5 is **0 for a +0.1° error and −1 for a
     −0.1° error**.
   - Inside that window, small-signal in-phase tracking collapses:

     | correction | C3-P | P2 |
     |---|---|---|
     | ±0.3° at 0.1 Hz | 0.33 | 0.88 |
     | ±0.5° at 0.2 Hz | −0.17 | 0.51 |
     | ±1° at 0.3 Hz | −0.10 | 0.25 |

   - Dwell-then-jump events at ±1°, 0.3 Hz rise from 18 to 64.
   - The cause is proven both ways. Flooring C3-P's G at 512 restores most of the loss, and lowering P2's G to 463
     reproduces the collapse.
   - This is the round-2 finding F4 ("small-signal in-phase tracking collapses at the 10–12.5 m/s gain dip"). The brief
     required this round to resolve it. C3 does not declare it, and its table makes it worse. The round-2 refuter had
     recorded **"G ≥ 512, so the sar 5 I path still sees at least 1 per 0.1° at every speed"** as a property of P2.
     G-P48 breaks that property.

There are also three MEDIUM declaration and quantification gaps (N3–N5), two LOW–MEDIUM ones (N6–N7) and one LOW one
(N8). They are listed below.

**What passes this lens (EVIDENCE):**
- the goal's tracking metric on r71b's real paths with the run's **real speed trace**: C3-P 0.982 / 0.990 / 1.001;
- synthetic turn-hold, including at aged sensor holds;
- braking through the 12.5 and 6 m/s knees;
- S-bends and held-turn reversals, with no dwell-then-jump;
- no hunt at centre under road noise;
- 0 int32 wraps.

The 6.6–6.8° "max snap" in the design's own r71b table is a detector artefact, not a dwell-then-jump (see "Resolved").

**Lens.** Coulomb friction and stiction, the 0.1° quantisers, the integer lane, the cave's exact listed arithmetic,
fade, sign-hold, ramp-in, light and firm override in **both directions**, co-steer, release, and the 510 ms timeout.

**Members.** nominal, bc, F_hi, b_lo×J_hi.

**Speeds.** 3 and 5 m/s, then 8–30 m/s every 0.25 m/s, plus the knots 11.9 and 26.9. Speed-varying traces were also
run.

**Hold ages.** Native (ages 1–10) and +h10 (ages 11–20).

**Safety of this work.** Nothing was built, flashed or sent. Ghidra was used read-only (a dry-run PseudoDisassembler
script), and nothing was saved.

---

## 1. Independence and controls

| # | what | method | result |
|---|---|---|---|
| K1 | cal | My own little-endian read of the V295 image (sha `5c044d65…`), compared with `lane_mirror_v295.load_cal`. The V295 values of every cell C3 changes were compared with the design's §1.3. | **EVIDENCE, PASS**: PCL, SCL, OCL, oa, ob, gate, dz, fwd and fadeB are identical. ICL 10240, Ki 0, DCL 0, DB 4, a 1011, b 1050 and C 1024 match §1.3. |
| K2 | listed immediates in the bytes | Searched each cave hex for the listed encodings: `movea 0x200` / `0xb40` / `0x566` / `0x1000`, `addi 0x4e2`, `shl 4/6,r9`, `ld.h -0x6a00`, `ld.w -0x6dd0`, `sar 10`, `andi 0x8000,r14`, `ld.hu -0x4f68`. | **EVIDENCE, PASS**: 12/12 for C3-P, C3-F and E2-A3; 10/10 for C3-PA2, which has no cap. |
| K2b | the cave bytes decode as listed | **Ghidra PseudoDisassembler (dry-run `run_script_inline` on the V294 program)** over the code bytes of `c3_cave_C3-P.hex` (0xB4 bytes) and `c3_cave_C3-F.hex` (0xA2 bytes). | **EVIDENCE**: every instruction matches the design's §1.2 and §2 listings, including `cmovh r13,r9,r9` (the cap is a min), `cmp r9,r13 ; bge FRZ` (signed t ≥ bound), `jr 0x29d7e`, and `jmp [r6]`. |
| K3 | my lane against the common scorer's `CandLane` | `c3nl_sim.Lane` was written from `lane_mirror_v295` (Honda's side) and the design's listing (the cave), not from `CandLane`. 40 000 ticks × 5 columns (C3-P, C3-F, C3-PA2, P2, E2-A3) of random and edge inputs: the sentinel, ±13000/13001, \|tq\| at 511/512/513, ramp 0 / 0x7FFF / 0x8000, request 0 / 1 / 0xFF, the table knots, and the 1382/1383 and 2880/2881 knees. | **EVIDENCE, PASS: 0 mismatching ticks** (T, I8 and the output-lag state all compared). |
| K4 | my whole closed loop against the scorer's `run()` | My runner was given the scorer's own Scn objects for ov_lt511, th, s03_02, tmos, cs and eng, on C3-P and C3-F × nominal / b_lo×J_hi / F_hi × 8, 11.75, 17 and 26.9 m/s. | **EVIDENCE, PASS: bit-exact** (\|Δθ\| = 0, \|ΔT\| = 0 on all 18 batches). The design's numbers therefore reproduce in its own scenarios. **Every finding below comes from scenarios, directions, amplitudes, frequencies or speed traces the scorer does not run.** |

The plant parameters (the r71b family) come from `nl_sim.params`, used only as a parameter table. The Karnopp
integrator, the sensor and fork models, the speed-varying runner and every metric are my own code in
`refute_c3_nonlinear/`.

---

## 2. Findings

### N1 — HIGH (C3-P and C3-F): the light-hand release lurch is bounded in only one direction; the undeclared outward case breaks the 8° bar

**The claim being tested** (design §0.2, §5, §7 H-ovr, §11):
- "release lurch light / firm, b_lo×J_hi, max ≥ 8 m/s **4.1 / 3.2°**" against a pre-registered 8° bar;
- H-ovr: "the **angle-referenced bound (κ-independent)** … Release overshoot ≤ 4.1° light / 3.2° firm ≥ 8 m/s (bounded)
  … the ARB reads no torque word, so κ does not enter (E2's point)".

E2's rationale for A3 is: "A hand that holds the wheel away from the setpoint drops the bound to B, so the I stops at
the level the turn needed."

**What the common scorer runs.** In `score_time.scenario` (OVW), the light-hand scenarios drag the wheel from the held
turn Ah **to 0**, which is toward centre. Every lurch number in the design is that one direction.

**The mechanism** (cave `0xC4C64..0xC4CA4`; EVIDENCE: Ghidra dry-run decode, K3):
- The bound is `(|gp-0x6a00| << 4 or 6) + 1250`, and the I freezes only while `sgn(E')·(I>>7) ≥ bound`.
- If the hand holds the wheel **further from centre** than the setpoint, E' points back toward the setpoint. The I
  first unwinds through 0 and then winds the *other* way.
- From then on, t = |I|>>7 is compared with a bound computed from the *hand's* larger \|θ\|. The bound is large, so
  the I runs to `64·|θ| + 1250` above 12.5 m/s, or to ICL 8192 (about 1313 T).
- Nothing in A3 refers to θ_sp, so "the level the turn needed" is not what bounds it.

On release, that I and the spring both pull toward centre. Trace (`out/trace_outward.txt`, 12.75 m/s, b_lo×J_hi, wheel
held at 2×Ah for 3 s):
- C3-P: I = −8098 S, which is exactly the bound 64·107 + 1250. The wheel goes **+10.7° → −17.7°** with the setpoint at
  +5.8°.
- P2 (I clamped at −4096): the wheel goes +11.0° → −8.0°.

**Quantified on my loop** (`out/lens_report.md`, worst over the 4 members, native age). The convention is the design's
own: a stiff hand, Kh 2000, Bh 30, with a constant word below the 512 freeze.

| scenario (hold time) | 8–10 | 10–12.5 | 12.5–15 | 15–22 | ≥ 22 | P2, same scenario, worst ≥ 8 |
|---|---|---|---|---|---|---|
| out: wheel taken to 1.5×Ah, word 400/511 (1 s) | **15.9** | **11.8** | 4.9 | 3.2 | 1.9 | 16.1 |
| out: 1.5×Ah (3 s) | **15.9** | **14.4** | **12.6** | **8.2** | 4.0 | 18.1 |
| out: 2×Ah (1 s) | **20.0** | **17.0** | **10.2** | 6.5 | 3.8 | 18.9 |
| out: 2×Ah (3 s) | **20.0** | **17.0** | **23.7** | **12.7** | 4.7 | 18.9 (12.5–15: 14.6; 15–22: 9.3) |
| nudge on a straight, sp 0, to 5° (3 s) | 5.1 | 6.2 | **10.6** | 6.8 | 4.4 | 13.8 |
| nudge on a straight, to 2° (3 s) | 3.8 | 4.6 | 5.9 | 3.8 | 2.5 | 12.5 |
| **consistent sensor κ_T 2.0** (word = hand force / 2; freeze at 1024 T), out 1.5×Ah (3 s) | **13.1** | **14.4** | **12.6** | **8.2** | 4.0 | 17.9 |
| consistent κ_T 2.0, out 2×Ah (1 s) | **10.7** | **14.6** | **10.2** | 6.5 | 3.8 | 16.6 |
| consistent κ_T 2.0, nudge 5° (3 s) | 5.1 | 6.2 | **10.6** | 6.8 | 3.5 | 13.8 |
| consistent κ_T 0.6, out / nudge (every case) | ≤ 7.3 | ≤ 4.6 | ≤ 3.8 | ≤ 1.8 | ≤ 1.5 | ≤ 9.0 |
| torque-source hand +300 T, word 300 (outward / nudge) | ≤ 4.8 | ≤ 6.0 | ≤ 4.9 | ≤ 3.0 | ≤ 2.0 | ≤ 6.2 |

Every number is degrees of release lurch past the setpoint toward centre (past centre for the nudges). Bold marks a
value over the design's 8° bar.

**Like for like.** At 8 m/s on b_lo×J_hi:
- The scorer's own inward ov_lt511 holds the hand at **1346 T** and gives 4.09°. Its I is ARB-frozen at +2692 S
  (`out/scorer_ov_handforce.txt`).
- The outward 1.5×Ah 1 s case holds the hand at **1674 T**, about the same, and gives **15.9°**. Its I is wound to
  −5894 S.

The convention, the hand stiffness and the force level are the same. The only difference is the direction.

**Why this is a refutation and not a declared miss:**
- M-C3-6 declares lurch only below 8 m/s.
- §5 and H-ovr state 4.1° as the maximum at 8 m/s and above.
- No stop band or instrument covers the outward direction. The §8 light-hold episode is specified "toward straight"
  only. A driver who rests the hand the other way would see the I ramp even with the bound live, so the null sentence
  ("if the I component ramps … the bound is not live") is direction-dependent too.
- The round-2 open finding (F4: "light-hand release lurch on b_lo×J_hi exceeds the declared 8° bar") is claimed
  resolved. It is resolved only for the inward hand.

**EVIDENCE / BELIEF:**
- EVIDENCE: the bound arithmetic (Ghidra decode plus K3), the simulation, and the trace.
- BELIEF: how often drivers hold the wheel outward with a light grip; that is not measured.
- BELIEF: which hand model is physical. κ_T is unmeasured. E2 cites an r71b bar fit of 0.003–0.09 T per count
  (±100 %). At that κ, the 512 freeze binds by about 46–92 T of hand force, and the outward lurch would be small in
  **both** directions, with or without A3.
- The design's lurch claim, its 8° bar and its κ-independence argument are all made under the κ→∞ convention. Under
  that convention they fail for the outward hand. If κ is small, A3 is not what bounds the lurch in either direction.
  In neither case is the claim "A3 bounds the light-hand lurch κ-independently" true.

### N2 — HIGH (C3-P; worse in C3-F): G < 512 at the dip makes the I quantum one-sided, and small-signal tracking collapses (the round-2 F4 item, unresolved and worse)

**Arithmetic** (EVIDENCE: the listed path `0xC4C52 mul ; sar 8` → `0x29D7A mov r16,r6 ; 0x29D7C sar 5`, with
E = 16 per 0.1° count; `out/g512_attribution.txt`):

| G | e5 for error −2 / −1 / +1 / +2 counts |
|---|---|
| 463 (C3-P at 11.75 m/s) | −2 / −1 / **0** / 1 |
| 511 | −2 / −1 / **0** / 1 |
| 512 | −2 / −1 / 1 / 2 |
| 537 (P2's minimum) | −3 / −2 / 1 / 2 |

The G walk of the C3-P hex gives G < 512 for v words 2621–2814, which is **11.38–12.21 m/s**: G = 692 − (v − 2304)·2328/4096
on segment 2, and 463 + (v − 2707)·1870/4096 on segment 3. For C3-F (minimum G 417) the window is about 10.8–12.85 m/s.
P2's minimum is 537, so P2 never enters this regime. The round-2 refuter recorded that as a required property.

**The consequence** (`out/small_dip_detail.txt`; worst member; the in-phase wire gain is the scorer's regression of
0x14A on the received setpoint). The collapse sits inside the G < 512 window:

| speed (m/s) | 11.25 | **11.5** | **11.75** | **12.0** | 12.25 | P2 at 11.75 |
|---|---|---|---|---|---|---|
| ±0.3° 0.1 Hz, C3-P | 0.94 | **0.38** | **0.33** | **0.33** | 0.88 | 0.90 |
| ±0.5° 0.2 Hz, C3-P | 0.63 | **−0.01** | **−0.06** | **−0.17** | 0.45 | 0.51 |
| ±1° 0.3 Hz, C3-P | 0.23 | **0.04** | **−0.10** | **−0.04** | 0.10 | 0.25 |
| ±0.5° 0.2 Hz, C3-F | 0.03 | −0.08 | −0.30 | −0.27 | −0.16 | — |

Dwell-then-jump events, summed over members and speeds in the 10–12.5 band:

| correction | C3-P | P2 | C3-F |
|---|---|---|---|
| ±1° at 0.3 Hz | 64 | 18 | 90 |
| ±0.5° at 0.2 Hz | 164 | 175 | 186 |

The largest snaps are 1.11° (C3-P) and 1.17° (C3-F). In the scorer's own ±1° 0.2 Hz probe the in-phase gain is 0.69
for C3-P against 0.87 for P2 at 10–12.5 m/s.

**Attribution, both directions** (`c3nl_g512.py`; F_hi and bc; 11.0–12.5 m/s):
- C3-P with G floored at 512 recovers most of the loss: ±0.3° 0.1 Hz on bc 0.33–0.39 → 0.75–0.79; on F_hi 0.74 → 0.94;
  ±0.5° 0.2 Hz on bc −0.06 → 0.38.
- P2 with G lowered to 463 in the same window reproduces the collapse: ±0.3° 0.1 Hz on bc 0.90 → 0.35; ±0.5° 0.2 Hz on
  bc 0.62 → −0.03.

**Why this is a refutation:**
- The brief lists F4 ("small-signal in-phase tracking collapses with friction at the 10–12.5 m/s gain dip") as an open
  finding this round must resolve.
- §6 of C3 has no 10–12.5 m/s small-correction row. M-C3-1 is scoped to 12.5–22 m/s. §10 names "10–12.5 m/s" as a
  declared dwell-then-jump band only by inheritance from rev2-A's M2, which concerned hold slips, with no
  quantification and no stop band.
- C3 makes the collapse worse than P2, the design that F4 refuted. The cause is a specific integer artefact of the
  GATE-2-fitted table.

**Status.** EVIDENCE: arithmetic, simulation, and both controls. BELIEF: the size on the car (Fs and Fc at 11–12 m/s
are the r71b ident ×1/×2).

**What would clear it** (a report, not licence to act): keep G ≥ 512 everywhere, for example by raising the 2707 knot.
That is table data only, 0 code bytes, but it must be re-gated on GATE 2 because the dip was fitted to the R2 box.
Otherwise declare and quantify the collapse with a stop band.

### N3 — MEDIUM (both): dwell-then-jump in small corrections at 8–10 m/s and above 22 m/s is undeclared, yet §10 treats it as an on-car FAILED

The design's own grid (`c3_score_time_tables.md`, ±0.3° at 0.2 and 0.5 Hz) gives these event counts:

| band | C3-P | P2 | largest snap (C3-P) |
|---|---|---|---|
| 8–10 m/s | 300 | 294 | 0.63° |
| ±1°: 8–10 m/s | 26 | 31 | 1.60° |
| > 22 m/s | 33 | 6 | 0.46° |

The > 22 m/s rise is new with the G-P48 table (C3-Pd gives 2).

My probes add:
- ±0.3° at 0.1 Hz: 150 events at 8–10 m/s (P2 165);
- ±0.5° at 0.2 Hz: 64 events at 8–10 m/s (P2 70), largest snap 0.74°.

Where the design falls short:
- §6 M-C3-1 is scoped to 12.5–22 m/s and quantifies only 15–22 m/s ("15 events").
- §10 says the build FAILED if dwell-then-jump is "above r6c in a band other than the declared 3–7 / 10–12.5 / highway-hold
  misses". 8–10 m/s and > 22 m/s small corrections are therefore not declared, and no stop band covers them.
- This is the round-2 F2 item for the 8–10 m/s band. It is carried over unresolved; the size is P2-class, so it is not a
  regression.

Status: EVIDENCE (simulation, and the design's own table). BELIEF: comparison with V282, which cannot be simulated.

### N4 — MEDIUM: tracking on a 0.1 Hz S-bend falls below 0.95 on two GATED time members at 16–17.5 m/s

The scenario is `scurve_1.5`: sp = A·sin(2π·0.1·t), with A sized for a_lat 1.5 m/s² (L 2.83 m, SR 16), 25 s, slope from
5 s. Worst slope by implementation:

| implementation | bc | b_lo×J_hi | nominal |
|---|---|---|---|
| C3-P | **0.940** at 17.0 m/s | **0.941** | 0.954 |
| C3-F | **0.918** | 0.920 | 0.933 |
| E2-A3 (P2's table + A3) | 0.965 | — | — |
| P2 | 0.847 | — | — |

At a_lat 2.0, C3-P gives 0.948. C3-P stays below 0.95 from 16.0 to 17.5 m/s.

- The deficit is mostly linear: it barely changes with amplitude and tracks the damping member. It comes from G-P48's
  lower highway gain, the GATE-2 cost. The ARB freeze duty is 0.
- M-C3-2 declares a tracking miss only for the **report member b_q×ms_free** ("two stress corners"). Here the miss
  appears on **bc and b_lo×J_hi, which are gated time members**.
- r71b's real paths pass (with the real speed trace C3-P gives 0.990 at 15–22 m/s) because their spectrum differs. The
  15–22 m/s margin therefore depends on the road.
- The design's own on-car criterion (M-C3-2: "on-car tracking < 0.95 at 15–22 = FAILED") would catch it. This is a
  quantification gap in what M-C3-2 says it covers, not an uncovered hazard.

Status: EVIDENCE (simulation).

### N5 — MEDIUM: overshoot from integral windup on fast transients and reversals (undeclared)

- After raising ICL to 8192, a large transient error winds the I to the clamp, because the bound at large \|θ\| is
  above ICL. This is E2's M-b mechanism.
- **Held-turn reversal** (`rev_2`: +A to −A in 1.5 s at a_lat 2): C3-P overshoots by 14–20 % of A between 9.5 and 14 m/s
  (0.197·A = 6.3° at 12.75 m/s, nominal). P2 shows −0.06 to +0.05 and E2-A3 0.186. At a_lat 1.5 the overshoot is up to
  0.165·A.
- **On r71b's own path** (run #7, 19 m/s, t 32.2–33.8 s; trace in `c3nl_r71b.py`): C3-P's I reaches −8192 and the
  wheel overshoots the reference by about **3.5°** twice (−22.2° against −18.7°; −21.6° against −18.1°). P2 lags
  instead.
- The scorer's own step-and-hold table also shows C3-P overshoot of 20 % at 8–10 m/s and 16 % above 22 m/s. Neither
  appears in §5 or §6.
- None of this is one of the goal's criteria. Hard-turn 1.6–3 Hz energy is decided on the car, and the design's ratio is
  1.07. It is a quantification gap for the "jerk / lurch" class the operator reports in his own words (R9).

Status: EVIDENCE (simulation).

### N6 — LOW–MEDIUM: M-C3-9 (road load at θ ≈ 0) is unquantified, and its stop band omits 8–12.5 m/s, where the error is largest

The scenario is a steady external load at sp = 0 (`zero_wind_*`). C3-P's steady error is:

| load | 8–10 m/s | 10–12.5 | 12.5–15 | 15–22 | > 22 |
|---|---|---|---|---|---|
| 200 T | ≤ 0.25° | ≤ 0.25° | ≤ 0.25° | ≤ 0.25° | ≤ 0.25° |
| 300 T | 1.24° | 1.41° | 1.34° | 0.51° | 0.35° |
| 500 T | 3.54° | 3.94° | 3.61° | 1.35° | 1.05° |

P2 stays ≤ 0.23° throughout.

- The design's stop band is "steady hands-off error > 1° on a straight **≥ 12.5 m/s** → REVERT". The 8–12.5 m/s goal
  bands, where the 26 T/deg slope makes the error larger, are uncovered.
- "Never seen on r71b" is E2's evidence, which I did not re-derive.

Status: EVIDENCE (simulation). BELIEF: how large road loads at centre are on the operator's roads.

### N7 — LOW–MEDIUM: turn-hold sags while accelerating through a constant-radius curve (shared class, slightly worse)

The scenario is `accelA`: sp 9.73°, accelerating 5 → 20 m/s at 1.5 m/s². The worst 1 s hold ratio at 8 m/s and above,
around 13.25–14.75 m/s (where k(v) rises from 36 to 58 T/deg), is:

| implementation | worst 1 s hold |
|---|---|
| C3-P | **0.864** |
| C3-F | **0.848** |
| P2 / E2-A3 | 0.888 |

In `accelB` (3 → 15 m/s, sp 28.8°) C3-P reaches 0.895.

- The ARB freeze duty is 0. This is the PI's lag while the load ramps, deepened by G-P48's lower G at 13–15 m/s. It is
  not A3.
- It is transient (about 2 s) and does not trip the goal's on-car turn-hold definition (< 0.90 over ≥ 60 s). The
  operator may still feel it as "loose / runs wide when accelerating out of a curve".
- Braking through the knees is clean: decelA/B/C hold ≥ 0.97 at 8 m/s and above, with no dwell-then-jump.

Status: EVIDENCE (simulation).

### N8 — LOW: the declared lurch figures are native-age only

- At +h10 (ages 11–20), the scorer's own light-hand lurch is **4.89°** (C3-P) and 4.83° (C3-F) at 8–10 m/s, against
  4.1° declared. The firm-hand lurch is 3.84° against 3.2° declared.
- An inward **partial** drag to 0.5×Ah (3 s) gives **5.40°** at 12.75 m/s (C3-P). P2 gives 10.58°.
- All of these are under the 8° bar, but above the declared maxima.

Turn-hold, engage droop (6.2° at +h10) and co-steer droop (2.4°) are essentially unchanged by age
(`out/aged_report.md`).

---

## 3. Resolved, not findings

- **r71b "max snap" 6.6–6.8°** (the design's table, C3-P). It is the record detector misreading r71b run #7 at
  t ≈ 31.9 s (19 m/s). The reference itself moves −15.75° → −25.8° → −18.7° within 0.6 s. The wheel dwells for 0.2 s
  at a reversal and then *follows* the 10° excursion. The detector's 2×-reference-change test sees only the net −2.5°.
  P2 does not "jump" there because it lags the excursion; its own 11.7–13.1° artefact is at run #1, t 14.1 s.
  **EVIDENCE: per-event list in `out/r71b_report.md` and the time trace.**
- **Speed is not constant within an r71b run** (the scorer uses the median speed). Re-run with each run's own vEgo(t):
  C3-P tracking 0.982 / 0.990 / 1.001 clean and 0.980 / 0.987 / 1.001 replayed. The real-curve hold minimum is 0.969.
  **The design's F1 resolution holds** (`out/r71b_report.md`).
- **Turn-hold at a_lat 2.0 / 2.5** at +h10: minimum 0.981 at 8 m/s and above. Braking through the 12.5 and 6 m/s knees
  with the bound slope switching: hold ≥ 0.97, no lurch at the knee (error ≤ 3.9° while braking from 15 m/s at
  1.5 m/s² in a 28.8° curve; P2 ≤ 7.5°).

---

## 4. What passes this lens (EVIDENCE: simulation on my loop unless stated)

- K1–K4 controls: bit-exact against the common scorer; the Ghidra decode of both caves matches the listing.
- The r71b goal metric with real speed traces, clean and replayed: pass, as above.
- S-bends (a_lat 1.5 and 2) and held-turn reversals: 0 dwell-then-jump events at any speed of 8 m/s or more. For
  overshoot see N5; for slope see N4.
- At centre with 15 T rms road noise for 30 s: no hunt (no limit cycle, p2p ≤ 0.23°), no dwell-then-jump.
- Torque-source hands (outward or nudge, ≤ 300 T, word = force): lurch ≤ 6.0° (C3-P), P2-class.
- Consistent sensor κ_T 0.6: every outward and nudge case ≤ 7.3°.
- Inward light hand (the scorer's direction), all ages: ≤ 4.9°.
- 0 int32 wraps across the whole lens (about 200 batches).
- Not re-run beyond the K4 equivalence (the scorer's own cells, which my loop reproduces bit for bit): the 510 ms
  timeout, the sentinel, request drop, engage droop and co-steer droop. Aged values: timeout mid-motion ≤ 2.6°, engage
  ≤ 6.7°, co-steer ≤ 2.6°.

---

## 5. Not verified, and why

- **The κ that decides N1's physical size.** It is unmeasured on this car. N1 is stated under the design's own
  convention and at κ_T 0.6 and 2.0.
- **Dwell-then-jump against V282.** V282 cannot be simulated; event counts are reported instead.
- **F5 (camera relay close) and pol ≠ −1.** These are not part of this lens and cannot be simulated.
- **The fresh-versus-held D at the frame ratio 0.83 / 1.155.** My time loop uses the scorer's 'vgr' frame only, like
  the design's grid.
- **Members beyond the four time members.** J ≈ 1.0, b_q and ms_free were not run in the time domain, following the
  brief's time-gate list.
- **No built image exists.** Every byte claim here is about the hex files and the V295 image.

---

## 6. Files and reproduction (all run with `python`, the bin_decompile env, fixed seeds)

Scripts are in `analysis-2020accord/studies/angle_loop/refute_c3_nonlinear/`. Text outputs are in `out/`, which is
tracked. npz/json caches are in `_scratch/angle_loop/refute-c3-nonlinear/`, which is gitignored.

| script | what it does | output |
|---|---|---|
| `c3nl_sim.py` | my independent lane, plant, sensors, fork and speed-varying runner, plus metric helpers | — |
| `c3nl_control.py` | controls K1–K4 | `out/control_out.txt` |
| `c3nl_lens.py run 14` then `c3nl_report.py` | 50 scenarios × 4 members × 4 implementations × 94 speeds | `out/lens_report.md` |
| `c3nl_aged.py` | the scorer's own scenarios at native age and at +h10 | `out/aged_report.md` |
| `c3nl_r71b.py run 8` then `report` | r71b paths at median speed and at real speed, clean and replayed; dwell events listed | `out/r71b_report.md` |
| `c3nl_speed.py` | braking and accelerating through the knees in a constant-radius curve | `out/speed_report.md`, `out/trace_accel.txt` |
| `c3nl_g512.py` | the G < 512 attribution (both directions) | `out/g512_attribution.txt`, `out/small_dip_detail.txt` |
| (inline) | mechanism traces and the scorer's inward hand force | `out/trace_outward.txt`, `out/scorer_ov_handforce.txt` |

Nothing was flashed, sent or built. No design file, scorer, shared cache, image or fork file was modified.
