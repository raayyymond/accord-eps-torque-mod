# REFUTE C2 rev 2: the STABILITY lens (2026-10-01)

**Status: analysis only.** Nothing was built, flashed or sent. The fork was not touched. Ghidra was used read-only:
`decompile_function`, `get_xrefs_to`, `get_function_by_address` and `disassemble_bytes` with `dry_run: true`, on stock
`code.bin` and the V294 program. Nothing was saved.

**Author:** the C2-rev2 stability refuter, a subagent working for the orchestrator `main`.

**Python:** the `bin_decompile` environment.

**Scripts:** `analysis-2020accord/studies/angle_loop/refute_stability/c2r2/`. Outputs are in
`_scratch/angle_loop/refute-c2r2-stability/`.

---

## 0. Verdict: REFUTED. Do not flash any of the four implementations as written.

### 0.1 What was handed to this refuter

The "C2 rev 2" design payload is the judge's own stop notice. It says no design was picked, merged or re-scored, no design
document was written, and no files were produced. **There is no C2 rev 2 design to flash.** On that basis alone the
answer is refuted, exactly as in round 1.

So that the lens produces a usable result, I ran it in full on **all four implementations the two revisions put
forward**:

| implementation | source | D operand | Kd | G table |
|---|---|---|---|---|
| P2 | rev2-A primary | fresh gp-0x6abe | 34 | 6 knots |
| F2 | rev2-A fallback | held gp-0x6a56 | 20 | 6 knots |
| D2a | rev2-B primary; P1 in rev2-A | fresh gp-0x6abe | 34 | 7 knots |
| B0r | rev2-B fallback; F1 in rev2-A | held gp-0x6a56 | 20 | 7 knots |

The G(v) tables were parsed from the published cave hex. Each table address was read from the cave's own
`mov imm32, r9`.

### 0.2 The refutation

**F1 (HIGH, CONFIRMED, applies to all four).** The P/I operand and the D operand are in different angle frames, and no
design carries that difference.

- **The two frames.**
  - P and I act on gp-0x6a00. The identified plant's angle is in the same frame.
  - D acts on the motor-linear rate: x = gp-0x6a56, or gp-0x6abe.
  - gp-0x6a00 includes Honda's correction C(d). Its slope is **1.155 for |θ| < 27.7°**, 1.120 / 1.083 / 1.032 further
    out, and **0.962 beyond 81°**.
  - So near centre, the D term's gain per degree of the plant's angle is **×0.866** of what every design assumed. The
    designs assume x = 8 counts per deg/s everywhere.
- **Evidence, by two independent methods.**
  1. **The bytes.** I read the LERP knots `0xC6892` / `0xC68A2` LE from the V295 image and recomputed the slope. The
     formation of gp-0x6a00 is in `TRACE-2026-09-30-angle-signal-gp6a00` §2.1, and FUN_0003f776 (my decompile) shows x
     has no correction.
  2. **The wire, on r71b 0x14A.** I regressed d(θ_6a00)/dt (±50 ms centred difference) on x/8, by angle bin.

     | \|θ\| bin | d(θ)/dt per x/8 |
     |---|---|
     | 0–5° | 1.155 |
     | 5–10° | 1.162 |
     | 10–20° | 1.158 |
     | 20–30° | 1.154 |
     | 30–60° | 1.103 |
     | 60–90° | 1.016 |
     | 90–200° | 0.965 |
     | 200–600° | 0.964 |

     Over all angles together the slope is **1.0015**. That is the plant ident's "G2 PASS 1.0004" figure, and the
     aggregate hides the angle dependence.
- **Prior awareness.** The D-structure designer knew this frame difference and applied it to D1b only ("the VGR
  correction lives in gp-0x6a00, not in the accumulator"). It was not applied to the rate operand that every C2
  implementation uses.
- **Result.** With the near-centre ratio applied, under either reading of which frame the identified plant lives in, all
  four implementations fall below the brief's GATE-2 bars on gated members (§2 F1 table):
  - **tier A:** J_hi **43.2–44.1°** at 1–4 m/s, and ms_free **43.6–43.8°** at 8.5–11.9 m/s, against the 45° bar;
  - **tier B:** b_lo×J_hi+h10 **27.3–28.3°**, b_q×J1.0+h10 **27.5–29.7°**, and b_lo×J_hi×tau6 (+h10) **24.6–26.2°**,
    against the 30° bar.
  - Under the second reading, b_q×J1.0+h10 is below 30° over **15.25–35 m/s**, which is the highway.
- **Stability itself holds.** Every point stays stable: exact ρ ≤ 0.992, exact GM ≥ 8.8 dB. The rings are at 1.0–2.1 Hz
  with ζ 0.10–0.55.
- **Why it still refutes.**
  - The rings are inside the R3\* and R3 frequency bands, but these shortfalls are not declared.
  - With ζ ≥ 0.10 they are also above the "≥ 4 visible cycles (ζ < 0.10)" trigger of R3\* and R3, so neither stop
    would fire.
  - Under the brief, an undeclared PM below the bar on a credible member is a refutation.

### 0.3 What I corroborate

Under the designs' own plant and sensor model, I reproduce every published anchor (§1). On the brief's full gated set,
including the 0.05 m/s fine grid at 7–13.5 m/s, **I find 0 GATE-2 fails for all four.**

### 0.4 The other findings

None of these is refuting on its own:
- **F2 (MEDIUM).** P2's "13–25 Hz anti-damping ≤ 0.79× V295" is fragile with respect to the hold phase and the
  rate-former lag.
- **F3 (MEDIUM, rev2-B).** Re(T/ω) is under-quantified, and the 5–10 Hz anti-damping is neither reported nor declared.
- **F4 (MEDIUM).** Products of ms_free with the damping corners reach PM 13.5°.
- **F5–F9 (LOW / INFO).** Listed in §2.

---

## 1. Method and validation

### 1.1 The independent model (`c2r2_model.py`)

It imports **none** of the designers' loop code: ds_model, ds_lane, score_freq, c1_lib, stab_lin, harness_freq and r2a_*
are all unused.

**Inputs:**
- the **V295 image**, sha `5c044d65…`, asserted;
- cals read little-endian: OA 992, OB 507, fwd 5346, EMA 37/128 at `0xC643C`, 1159 at `0xC613A`, a/b 1011/1050, and the
  clamps;
- the **cave hex** of each implementation, for the table;
- the **r71b identification data**: `v295/plant/_scratch/p5c.json` and `p5b_ms.json`.

**Each member is rebuilt from the brief's definitions:**
- J refits;
- J1.0 interpolated between the 0.8 and 1.3 refits;
- b_lo per speed (and on the knots, as `b_lo_knot`; the two agree);
- b_q = max(0.25·b, 3.46) at ≥ 12.5 m/s;
- bc, linear part = b_lo;
- tau0 and tau6;
- mode13 and mode20 as collocated two-mass plants;
- ms_free.

**Sensor and lane facts, each confirmed in Ghidra this session:**
- FUN_00041464: gp-0x6abe = EMA(1024·gp-0x4f50) >> 10, α from `0xC643C`.
- FUN_0003f776: x = pol·((abe·48·1159) >> 15), clamped, and zeroed when invalid.
- FUN_00068fbe / FUN_00068f52: gp-0x4f50 is an IRQ-protected 1 kHz snapshot of an ISR 2-sample mean of the resolver delta.
- V294 `0x2A174..0x2A1FE`: the output lag, the ramp and fwd·pol.

**Two models:**
- **(A) Exact periodic.**
  - The lane tick by tick on the full state: ZOH plant, delay line, EMA, held θ and x refreshed at slot 4 after the lane,
    2-tap r26, I, output lag.
  - The 10-tick monodromy gives ρ and the least-damped pole.
  - Gain scaling gives the exact GM, up and down.
  - Fractional extra delay gives the exact delay margin.
  - Variants: ages 1–10 (nominal), 11–20 (+h10) and 0–9 (+h0).
- **(B) Averaged-hold LTI.** It gives PM over every |L| = 1 crossing, GM, |Tc|, |Tref|, Re(T/ω), M20 and L20.

### 1.2 Positive controls (`c2r2_validate.py` → `validate_out.txt`)

| anchor | published | mine |
|---|---|---|
| V294 / V295 Re(T/ω), 5–25 Hz, ages 0 and 10 (rev2-A §3.3, 24 numbers) | table | **max \|Δ\| 0.005** |
| P2 / F2 Re(T/ω), ages 0 and 10 (32 numbers) | table | **max \|Δ\| 0.005** |
| P2 nominal / J_hi / ms_free | 64.9 / 46.7 / 47.6 | 64.9 / 46.7 / 47.6 |
| P2 b_q×J1.0 / +h10 / b_lo×J_hi / J1.0 / J1.0+h10 / b_lo×J_hi×tau6+h10 | 37.4 / 34.0 / 37.4 / 39.0 / 35.5 / 30.5 | identical |
| F2 J_hi / b_q×J1.0 / b_q×J1.0+h10 | 47.0 / 39.0 / 33.4 | identical |
| D2a b_q×J1.0+h10 | 34.0 | 34.0 |
| B0r b_q×J1.0+h10 | 34.0 | **33.6 (at 15.5 m/s, not 26.9)**; see F5 |
| exact GM vs LTI GM (6 points) | — | agree to ≤ 0.1 dB |
| exact LPTV delay margin → equivalent PM (`c2r2_dm.py`, 11 points) | — | **equals the averaged-hold PM to 0.1°** |

The model is correct. Where it disagrees with the designs, the disagreement is about a **model fact** (F1) or about
**reporting** (F2–F5), not about arithmetic.

### 1.3 Coverage (`c2r2_sweep.py` → `sweep_<impl>.json`, `report_out.txt`)

**Grid:** 243 speeds. That is 1–35 m/s at 0.25 m/s, plus the plant knots 3.1 / 8.0 / 11.9 / 17.0 / 26.9, plus 0.05 m/s
steps over 7–13.5 m/s (the steep G segment).

**Members** (108, each at ages 1–10 and 11–20):

| tier | members |
|---|---|
| A (gated) | nominal, J_lo, J_hi, b_lo, b_hi, tau0, tau6, mode13, mode20, ms_free |
| B (gated) | b_lo×J_hi, b_lo×tau6, J1.0, b_q, b_q×J_hi, b_q×J1.0, b_q×tau6, b_lo×J_hi×tau6, b_lo_knot (±tau6) |
| report | the C1 rev 2 factorial remainder, J1.3 and its products, b_q0, bq10×J1.0 (±tau6), tau10, b_lo×J0.3, and the ms_free products |

**Computed at each point:**
- exact ρ;
- ρ at gain ×2 (the exact 6 dB check);
- ρ at the fade floor ×0.297;
- ρ with I frozen, at ×1 / ×0.297 / ×0.05 (the ramp-in and hands-on loops);
- the LTI metrics.

That is 104,976 points.

---

## 2. Findings

### F1: HIGH, CONFIRMED, refuting all four. The measured P:D frame ratio is not modelled

`c2r2_frame.py` → `frame_out.txt`, run on the brief's gated set with the 0.25 m/s grid plus the knots.

**The two readings of the frame:**
- **FA.** The identified plant is in the θ (gp-0x6a00) frame, so D ×1/1.155.
- **FB.** The plant is in the motor frame. Then P and I ×1.155 (G ×1.155), spring k ×1.155, and D ×1.

The identification fitted `J·ω̇ + b·ω + k·θ` with θ taken from 0x14A and ω = x/8 (`plib.py` docstring), so it is
effectively mixed-frame. The two readings bracket it (BELIEF on which one is closer).

**The minimum PM by implementation and reading.** Bars: tier A 45°, tier B 30°. The ring is the least-damped closed-loop
pole at the worst point.

| member | P2 FA | P2 FB | F2 FA | F2 FB | D2a FB | B0r FB | ring |
|---|---|---|---|---|---|---|---|
| J_hi (A) | **43.2** (1–4 m/s) | **44.0** | **43.4** | **44.1** | 44.0 | 44.1 | 1.0–1.2 Hz, ζ 0.51–0.55 |
| ms_free (A) | **43.8** (8.5–11.9 m/s) | **43.6** | **43.8** | **43.7** | 43.6 | 43.7 | 1.2–1.4 Hz, ζ 0.31–0.33 |
| b_lo×J_hi+h10 (B) | **28.3** (1–8 m/s) | **27.3** | **28.0** | **27.4** | 27.3 | 27.4 | 1.4–2.0 Hz, ζ 0.19–0.29 |
| b_q×J1.0+h10 (B) | **29.5** (15.5 m/s) | **28.5** (15.25–35 m/s) | **29.3** | **27.5** (15–35 m/s) | 28.2 | 27.5 | 1.6–1.9 Hz, ζ 0.10–0.15 |
| b_lo×J_hi×tau6+h10 (B) | **26.2** (1–8 m/s) | **24.6** | **26.0** | **24.8** | 24.6 | 24.8 | 1.45–2.06 Hz, ζ 0.17–0.27 |
| b_lo×J_hi×tau6 (B) | ≥ 30 | **29.8** (7.75–8 m/s) | ≥ 30 | ≥ 30 | 29.8 | ≥ 30 | 2.05 Hz, ζ 0.22 |

- **Outward.** At large angles (|θ| > 81°, ratio 0.964), all four pass. FA'/FB' give tier A ≥ 47.3° and tier B ≥ 31.2°.
- **The cross-check.** The exact LPTV delay margins agree. For example, P2 FB b_lo×J_hi×tau6+h10 at 8 m/s has DM 36.0 ms,
  equivalent to PM 24.6°. B0r FB b_q×J1.0+h10 at 17.5 m/s has DM 41.4 ms, equivalent to 27.5° (`dm_out.txt`).
- **EVIDENCE.**
  - The slope 1.155 is EVIDENCE from the bytes and the wire, two methods (§0).
  - The PM numbers are EVIDENCE from my model.
- **BELIEF.**
  - The frame the identified plant lives in. Both readings fail near centre.
  - That near-centre operation (|θ| < 28°) dominates engaged driving above 8 m/s. That holds at highway speed by
    geometry.
- **Not declared anywhere.**
  - Neither revision mentions the D-operand frame.
  - rev2-A's R3\* floors ("ζ ≥ 0.164 at ≤ 8.25 m/s") and rev2-B's misses do not cover these members.
  - Both stops trigger at ζ < 0.10 or on growth, so a ζ 0.10–0.29 ring at 1.4–2.1 Hz, PM 24.6–29.7°, would pass silently.
- **Feasibility probe (`c2r2_remedy.py`; NOT a design).**
  - Raising Kd by 1.155 (P2 34→39, F2 20→23) closes FA. P2 reaches tier A 46.6° and tier B 30.3°; F2 reaches tier B
    29.9°, still short.
  - It does **not** close FB: tier B stays at 28.9° / 28.5° on b_lo×J_hi×tau6+h10 at 8 m/s. FB also needs a G cut near
    8 m/s.
  - At large angles, Kd 39 acts like about 40.5. That is near rev2-A's P3 (Kd 41) envelope collapse, but large angles
    occur only at low speed, where the probe gives ≥ 51° / 36° at ≤ 10 m/s.
  - A re-fit is needed. It is not a byte patch.

### F2: MEDIUM (P2 / D2a; rev2-A's own H2 criterion and its P-over-F rationale). The 13–20 Hz "≤ V295" claim is phase-fragile

`c2r2_extra.py` E1 → `extra_E1E2E5.txt`. Re(T/ω) is the worst value over 1–35 m/s, in T counts per deg/s, where > 0
damps. All worst points are at 27 m/s unless stated.

| condition | P2 13 Hz | P2 20 Hz | V295 13 / 20 Hz | P2 / V295 |
|---|---|---|---|---|
| transport 2 ms, ages 1–10 (the design's case) | −0.37 | −0.34 | −0.47 / −0.82 | 0.79 / 0.41 |
| **ages 0–9** (slot 4 before the lane; rev2-A's H-slot4 lists this phase as possible) | −0.38 | −0.35 | −0.34 / −0.73 | **1.12** / 0.48 |
| transport 6 ms (tau6), ages 11–20 | −0.39 | −0.49 (at 11.75 m/s) | −1.66 / −0.50 | 0.23 / **0.98** |
| tau6, ages 11–20, plus a 0.5-tick rate-former lag | −0.43 | −0.52 | | 0.26 / **1.04** |
| tau6, ages 11–20, plus a 1-tick lag | −0.48 | −0.55 | | 0.29 / **1.10** |

- **The two facts behind this.**
  - The rate-former lag is real. gp-0x4f50 is an ISR 2-sample mean of the resolver delta, snapshotted at 1 kHz
    (EVIDENCE, my decompile).
  - Its size is not known. The ISR period is BELIEF; the record puts shaft ratio × ISR period at 0.0141 s.
- **Consequence for rev2-A.** Its do-not-flash rule **H2** includes "P2's worst-over-speed Re(T/ω) at 13–20 Hz above V295's
  at either hold age". It was evaluated only at 2 ms transport and ages 1–10 / 11–20. **It trips at ages 0–9, at 13 Hz,
  and in the tau6-aged corner with any rate-former lag of 0.3 ms or more.**
- **The ranking still holds.** P2 stays better than F2 everywhere: F2 is 1.78× at ages 1–10, 2.26× at ages 0–9, and up to
  4.67× at 7 Hz in the tau6-aged corner. The P-over-F ranking survives.
- **Declare it on the page.** The headline "≤ 0.79× V295" is not robust and should be stated as phase-dependent.
- **Not refuting.** The 20 Hz loop gain still holds: M20 0.68×, L20 ≤ 0.70×. R4 covers any new line.

### F3: MEDIUM (rev2-B only). Re(T/ω) is under-quantified and the 5–10 Hz part is not reported

**The 13 Hz figures.** rev2-B §4.1 / §5.1 quote ReTw13 = −0.11 (D2a) and −0.58 "×1.2 V295" (B0r). Those are read at a
**single speed** (nominal, 12.5 m/s), which is `score_freq.summarize` reading `rows[("nominal", 12.5)]`. The worst values
over speed are:

| | rev2-B quotes | worst over speed | × V295 |
|---|---|---|---|
| D2a, 13 Hz | −0.11 | **−0.37** | 0.79× |
| B0r, 13 Hz | −0.58 ("×1.2") | **−0.84** | **1.78×** |

**The 5–10 Hz band.** rev2-B never reports or declares it. All four implementations anti-damp at 5–10 Hz in the nominal
configuration, while V294 and V295 damp:

| | 5–10 Hz Re(T/ω) |
|---|---|
| D2a | −0.39 to −0.57 |
| B0r | −0.84 to −0.86 |
| V294 | +0.05 to +1.33 |
| V295 | +0.09 to +2.46 |
| aged tau6 corner | down to −1.97 (×4.7 V295 at 7 Hz) |

- **Why it matters.**
  - F7 = 0 is a goal criterion.
  - The 7 Hz cycle is a recorded failure class: V291/V292 re-armed it.
  - rev2-A declares this as M14, with R4 and F7 as the stop. rev2-B does not.
- **Not refuting.** No 5–10 Hz closed-loop pole or peak appears on any member (peaks ≤ −3.4 dB), and rev2-B's
  R-census / R5 (F7 > 0) would catch it in flight.
- **Still a defect.** The brief requires Re(T/ω) 5–25 Hz to be reported against V294/V295.

### F4: MEDIUM (all four). Products of ms_free with the damping corners

These products are not in the brief's enumerated set. They are the same class of product the C1 refutation used: two
corners, each of which is gated.

| member | PM | speed | ring | ζ |
|---|---|---|---|---|
| **b_q×ms_free+h10** | 13.5° (P2/D2a), 14.9° (F2/B0r) | 15.75 m/s | 1.26–1.28 Hz | **0.047** |
| b_q×ms_free | 17.3–19.5° | 12.5–22.5 m/s | — | 0.063 |
| b_lo×ms_free (±tau6, ±h10) | 18.5–22.8° | 8.5–13 m/s | 0.81–0.9 Hz | 0.07–0.09 |

- **Stability holds.** All are stable, with ρ ≤ 0.9965.
- **Stop-band coverage.** The rings are inside R3\* and R3. With ζ < 0.10, R3\* would fire.
- **Declarations exceeded.** rev2-A's declared highway floor (ζ ≥ 0.086, 1.44–1.46 Hz) is exceeded. rev2-B declares no
  report-member rings at all; its b_lo×J1.0, b_lo×J_hi2 and b_q×J1.3 rows at 23.6–30° are undeclared.
- **Credibility is BELIEF.**
  - ms_free's J is 2.08 at 11.9 m/s and 1.66 at 17 m/s, which is unidentified above 10 m/s.
  - b_q is the refuters' damping stress.
  - The orchestrator should rule whether ms_free products belong in the credible set. Note that ms_free itself is gated
    at tier A.

### F5: LOW (rev2-B). The binding member is misreported

rev2-B claims a tier-B minimum PM of 34.0° for both D2a and B0r (`b_q*J1.0+h10@26.9`). Independently:
- **D2a:** 32.6° (b_lo×J_hi+h10 at 1 m/s);
- **B0r:** 32.1° (b_lo×J_hi+h10 at 1 m/s), and b_q×J1.0+h10 is 33.6° at 15.5 m/s.

rev2-A reports the same 32.6° / 32.1° that I find. All of these are above 30°, so this is not decision-bearing.

### F6: LOW / ruling needed. The strict reading of "hold ages 1–20 on every member"

If single corners must clear 45° at ages 11–20 as well:

| member | PM | speed |
|---|---|---|
| J_hi+h10 | 42.2° (P2/D2a), 42.6° (F2/B0r) | 1 m/s |
| ms_free+h10 | 43.5–43.7° | 8.8–9 m/s |

Both designs tier the aged single corners at 30°, which treats aging as a stacked uncertainty. I read that as reasonable.
It is reported for a ruling.

### F7: INFO. light_b (the prior, report-only) is unstable on F2/B0r when aged

| implementation | case | PM | ρ | pole | ζ |
|---|---|---|---|---|---|
| F2 / B0r | 27 m/s, ages 11–20 | −4.4° | **1.0064** | 3.71 Hz | −0.027 |
| P2 / D2a | 27 m/s, ages 11–20 | 4.9° | — | 3.49 Hz | 0.028 |

- **On my integer lane** (frictionless plant), F2 grows into an **81° peak-to-peak limit cycle at 3.6 Hz**, and P2 settles
  into a 0.2° one (`intlane_out.txt`).
- **rev2-A's quantification** of light_b (ζ 0.075 / 0.060) is at ages 1–10 only.
- **Covered.** The ring is inside R3\*, and growth means REVERT.
- **Not credible.** The prior is contradicted by r71b (rate R² negative above 10 m/s) and is report-only in the brief.

### F8: INFO. The fresh-D sign depends on pol

**What I verified on the wire this session (EVIDENCE).** x and d(θ_6a00)/dt share a sign on r71b 0x14A: correlation 0.9955 on the raw
gradient, 0.9975 with ±50 ms smoothing (`frame_wire_out.txt`). So **F2/B0r's D damps whatever pol is**.

**What P2/D2a depend on.** Their D is (Kd/8)·gp-0x6abe, which has no pol factor. It damps only if **pol = −1**. If it did
not:
- the loop would be unstable at 1 m/s on nominal, b_lo, b_q and b_lo×J_hi;
- ρ would be 1.010–1.031, with a 2.0 Hz pole and ζ −0.08 to −0.23 (`polflip_out.txt`).

**What establishes pol = −1.** It is record EVIDENCE (`accord-gp6752-is-a-frame-converter-count-crossings`, the V98 b3
read). **It was not re-measured by me**, and it cannot be determined from 0x14A, because both θ and x carry pol.

**What covers it.** The first drive's R1 INVERTED check.

### F9: INFO. The fork outer loop

`c2r2_extra.py` E4, run on every gated member at every age:

| τ_o | worst PM | worst GM |
|---|---|---|
| 1 s | ≥ 64.5° | ≥ 8.3 dB |
| 0.5 s | 23.7° | **2.3 dB** |
| 0.3 s | **unstable** at 0.80 Hz | — |

The fork-spec rule (§5.6: no angle integral below 8 m/s, none faster than τ_o = 1 s) holds. rev2-B relies on that rule
without restating it. Its R3 lower edge, 0.8 Hz, only barely covers the 0.80 Hz outer-loop ring.

---

## 3. What survived the attack (under the designs' own model)

All four implementations, P2, F2, D2a and B0r, survived the following:

- **GATE 2, the brief's tiers: 0 fails** on the full gated set, at ages 1–10 and 11–20, including the 0.05 m/s fine grid.
  - Tier A minimum: 46.7° / 47.0° (J_hi, 1 m/s).
  - Tier B minimum: 30.5° / 30.1° (b_lo×J_hi×tau6+h10).
  - b_q×J_hi: ≥ 42.2°. b_q×tau6: ≥ 56.8°.
- **Exact stability.** Exact ρ < 1 at every one of the 104,976 points, report members included, light_b excepted (F7).
  The exact GM is ≥ 6 dB everywhere: ρ at ×2 is < 1.
- **The reduced-gain loops are stable everywhere.** The fade floor (×0.297) and the I-frozen P+D loop are stable at ×1,
  ×0.297 and ×0.05. This covers the hands-on freeze and the ramp-in.
- **No 5–30 Hz closed-loop peak above −3.4 dB**, on |Tc| or |Tref|.
- **L20 ≤ 0.70× V295 and M20 0.68–0.70× V295.**
- **The exact LPTV delay margin reproduces the averaged-hold PM to 0.1°.** The 100 Hz hold does not alias at the
  1–2 Hz crossovers.
- **The two-mass stress (E3) leaves 0 of 6,912 points unstable** per implementation. That stress is:
  - f₂ at 13 / 15 / 16.5 / 17 / 20 / 22 Hz;
  - ζ₂ at 0.02 / 0.05;
  - r₂ at 0.2 / 0.4;
  - both mode placements (free-free resonance at f₂, and the wheel-side anti-resonance at f₂);
  - on nominal, b_lo, b_q and J_hi;
  - at both ages.

  The loop raises modal ζ by ×1.2–1.6. The worst 5–30 Hz peak is −4.5 dB.
- **The integer lane matches the linear model** (`c2r2_intlane.py`, `c2r2_intlane_cmp.py`). It tracks the exact periodic
  model to **≤ 0.05° on a 2° step** at all nine binding points. There is no integer limit cycle (settled 0.5–30 Hz
  residue ≤ 0.0013°). The ring frequencies match the eigenvalues; for example, peak spacing 0.62 s against a 1.62 Hz
  pole.

---

## 4. Limits, and what I could not verify

- **Everything above about 8 Hz is model**, as the designs say. F1 sits at 1–2 Hz, inside the identified band.
- **Which frame the identified plant is in is BELIEF.** Both readings fail near centre, and both pass outward.
- **The rate-former lag size is BELIEF.** Its existence is EVIDENCE.
- **pol = −1 is record EVIDENCE that I did not re-measure.** P2/D2a's D sign depends on it (F8).
- **I did not re-score friction, the time-domain gates, or bytes and fail-safe.** Those are other lenses.
- **"Credible" for the ms_free products (F4) and the strict age tier (F6) are rulings** for the orchestrator.

## 5. What would turn this into a PASS (for the designers; not run here beyond the feasibility probe)

1. **Carry the measured frame ratio.** The D operand per degree of the plant's θ is 8/s(θ), with s = 1.155 / 1.120 /
   1.083 / 1.032 / 0.993 / 0.962 by angle band (the bytes).
   - Re-fit Kd and G(v), and gate both the near-centre end (s = 1.155) and the outward end (s = 0.962) at the speeds
     where each is credible.
   - Kd ×1.155 alone fixes FA but not FB, so a G trim near 8 m/s is needed too.
2. **Re-state the 13–20 Hz Re(T/ω) claim** at ages 0–9 and at tau6 with a rate-former lag bound. Either declare the
   ≥ 1.0× V295 cases under R4, or change H2.
3. **rev2-B:** report Re(T/ω) worst-over-speed for 5–25 Hz, and declare the 5–10 Hz anti-damping as rev2-A's M14 does.
   Correct the B0r 13 Hz figure (1.78×) and the tier-B binding member.
4. **Rulings:** whether ms_free × {b_lo, b_q} is credible, and whether single-corner +h10 is tier A or tier B.

## 6. Files

| script | output (`_scratch/angle_loop/refute-c2r2-stability/`) |
|---|---|
| `refute_stability/c2r2/c2r2_model.py` | the independent model |
| `c2r2_validate.py` | `validate_out.txt` |
| `c2r2_sweep.py` | `sweep_{P2,F2,D2a,B0r}.json`, `sweep.log` |
| `c2r2_report.py` | `report_out.txt` |
| `c2r2_extra.py` (E1–E5) | `extra_E1E2E5.txt`, `extra_E1.json`, `extra_E3E4.txt`, `extra_E3.json` |
| `c2r2_sens.py` | `sens_out.txt`, `sens.json` |
| `c2r2_frame.py` | `frame_out.txt`, `frame.json` |
| `c2r2_dm.py` | `dm_out.txt` |
| `c2r2_intlane.py`, `c2r2_intlane_cmp.py` | `intlane_out.txt`, `intlane_cmp_out.txt` |
| `c2r2_remedy.py` | `remedy_out.txt` |
| (inline) pol-flip consequence | `polflip_out.txt` |
| `c2r2_frame_wire.py` (bytes + 0x14A frame ratio) | `frame_wire_out.txt` (reads `_scratch/cache/75604b0a432fdc89_00000071--a7b8ba5d9d/can.npz`) |
