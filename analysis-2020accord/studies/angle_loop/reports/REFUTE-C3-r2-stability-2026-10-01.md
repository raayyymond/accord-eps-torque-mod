# REFUTE C3 rev 2: the STABILITY lens (2026-10-01)

**Status: analysis only.** Nothing was built, flashed, sent on a bus or committed. The fork was not touched. No shared
scorer, cache, design file or cave hex was modified. Ghidra was not needed for this lens: every number here is a loop
computation on bytes and cals read from the V295 image, and on the G(v) tables parsed from the published cave hex.

**Author:** the C3-rev2 stability refuter, a subagent of the orchestrator `main`.

**Python:** the `bin_decompile` environment.

**Scripts:** `analysis-2020accord/studies/angle_loop/refute_stability/c3r2/`. **Outputs:**
`_scratch/angle_loop/refute-c3r2-stability/` (gitignored). Every number below is in one of those output files.

**Object under test:** `docs/specs/design/DESIGN-ANGLE-LOOP-C3-rev2-2026-10-01.md`, with:
- **PRIMARY C3-rev2-P** (= rev2-B C3B-P): fresh guarded D, Kd 48, GB-P table, Ki 40;
- **FALLBACK C3-rev2-F** (= C3B-F): held D, Kd 24, GB-F table, Ki 40, in both its default and hardened forms.

---

## 0. Verdict: REFUTED, narrowly, by the configuration the design itself names as a flight prerequisite

**Where the design holds.** It survives every test it ran itself, and every test I added, as long as no fork angle
integral is present (§3). Specifically:
- θ = 0 GATE 2;
- the curve operating points on a ≤ 0.25 m/s grid, with fine steps of a;
- every hold offset;
- the frame box;
- the PD and hands-on loops;
- Re(T/ω) and L20;
- the two-mass stress.

**The headline.** The design lists *"any fork angle integral at τ_o ≥ 1 s (CHECKED)"* as a **FLIGHT PREREQUISITE**. Its
§0.2 F2 row backs this with *"refuter F2 shows τ_o ≥ 1 s has PM ≥ 56°, GM ≥ 8 dB"*. That number comes from round 1 and
was computed **at θ = 0 only**.

At the **curve operating points**, a fork integral anywhere in the permitted range τ_o 1 to about 4–6 s does the
following:
- it pushes the declared M-F1 ms_free family **over ρ = 1**;
- it takes a tier-A single and two combined members **below the GATE-2 bars**.

None of this is declared. Three independent methods agree: my LTI loop, my exact periodic model, and the integer lane.
The decisive outer-loop numbers also reproduce on the round-1 refuter's code, which is the code rev2-B used for its own
GATE-2 claims.

### 0.1 The refuting finding (R1, HIGH)

**R1. The τ_o ≥ 1 s fork-integral prerequisite is only cleared at θ = 0. At the curve operating points it is not
safe.**

*(a) The declared ms_free family diverges, and friction does not mask it.*
- M-F1 is quantified on the page as *"PM 1–21°, 0.45–0.9 Hz ζ 0.02–0.12, **ρ < 1**, friction-masked ±0.1–0.6°"*.
- The page's own FAIL line, H-F1 in rev2-B §10, reads: *"any operating-point exact ρ ≥ 1 on ANY member (the declared
  miss is bounded margin, never divergence)"*.

With the fork integral closed around the loop:

| exact ρ, worst over v / a / frames / e | τ_o 1.0 | 1.5 | 2.0 | 3.0 | 4.0 | 6.0 | none |
|---|---|---|---|---|---|---|---|
| C3-rev2-P b_lo×ms_free | **1.00364** | **1.00206** | **1.00125** | **1.00045** | **1.00005** | 0.99966 | 0.99890 |
| C3-rev2-P b_q×ms_free | **1.00267** | **1.00106** | **1.00024** | 0.99944 | 0.99905 | 0.99866 | 0.99791 |
| C3-rev2-P ms_free (tier-A single) | **1.00099** | 0.99918 | 0.99824 | 0.99729 | 0.99746 | 0.99831 | 0.99544 |
| C3-rev2-F b_lo×ms_free | **1.00432** | **1.00279** | **1.00201** | **1.00123** | **1.00085** | **1.00047** | 0.99973 |

(`tauscan_out.txt`; the full-grid sweep is `outer_P.npz` and `outdetail_P.txt`. At τ_o 1 s there are 166 ρ ≥ 1 points
for the primary and 255 for the fallback. All of them are on the ms_free family, at v 10–14.75 m/s and a 1.5–2.5.)

**Integer lane** (`intlane_outer_out.txt`): the design's own integer arithmetic, a 100 Hz fork integral with a 60 ms
round trip, and the identified Karnopp friction. At 11.9 m/s, a 2.5, FA.83, e10:

| case | frictionless | with the identified friction | no fork (control) |
|---|---|---|---|
| P b_lo×ms_free, τ_o 1 s | 66.5° p-p, 0.55 Hz, sustained 10–45 s | **61.9° p-p**, sustained | 1.1° p-p decaying / 0.26° (`intlane_out.txt`) |
| P ms_free (tier A), τ_o 1 s | 36.2° p-p sustained | **34.0° p-p** sustained | — |
| P b_lo×ms_free, τ_o 2 s | 35.0° p-p sustained | **31.6° p-p** sustained | — |

So the declared ±0.1–0.6° friction masking holds **only without the fork integral**. With the integral the permitted
fork configuration produces a 0.5 Hz steering oscillation of ±15–33°.
- **Inside R3\*'s band?** The ring is at 0.50–0.55 Hz, so it is inside R3\*'s frequency band.
- **Is the miss quantified?** No. Both "ρ < 1" and the amplitude are falsified by about two orders of magnitude.
- **Does the design's own fail line fire?** Yes, H-F1 fires.
- **Is this a "pre-declared, quantified miss whose stop band covers it"?** No.

*(b) Gated non-ms_free members fall below the bars (no ρ ≥ 1).* The data below is for τ_o 1.0 s, a 2.5, at 11–12.5 m/s
(the GB-P dip, G 559 at 11.75 m/s). Sources: `outdetail_P.txt`, `bhi_outer_out.txt`, `xcheck_out.txt`.

| member (tier) | outer-break GM / PM | actuator-break PM | least-damped ring |
|---|---|---|---|
| **b_hi (A, bars 45° / 6 dB)** | **4.8 dB / 37.6°** (e0, FA1.155), **4.5 dB / 35.8°** (e10) | 16.8° / 15.6° | **0.33 Hz, ζ 0.098** |
| J1.0, b_q×J1.0 (B, bar 6 dB) | **5.7 dB** (e10, FA.83) | 21.0–24.7° | 0.44–0.45 Hz, ζ 0.15 |
| nominal (A) | 7.8 dB / 60.4° (passes) | **31.6°** (< 45) | 0.37 Hz, ζ 0.17 |
| C3-rev2-F b_hi (A) | **5.1–5.3 dB / 41.4–43.0°** | 16.8–17.6° | 0.33 Hz, ζ 0.105 |

- **Extent.** The b_hi outer-break GM is below 6 dB for τ_o 1.0 to about 1.2 s, a ≳ 2.1, 11–13.5 m/s, at κ 1.155. At
  τ_o 1.5 s it recovers to 8.3 dB.
- **Integer lane.**
  - b_hi with τ_o 1: frictionless it decays at ζ ≈ 0.087, which matches the exact ζ 0.092. With the identified friction it
    **settles into a sustained 1.6–2.1° p-p hunt at 0.29 Hz**.
  - Nominal and J1.0 with τ_o 1: sustained **0.9–1.1° p-p at 0.25–0.30 Hz** with friction.
  - Without the fork, every one of these goes quiet.

These rings are inside R3\*'s band and would trip it, but nothing on the page predicts them.

**Cross-code check (EVIDENCE, `c3r2_xcheck_c3r1code.py`).** I built C3B-P/F on the round-1 refuter's `c3r1_model`
exactly as `rb_gate2.py` builds them. I closed the outer loop the way `c3r1_outer.py` does, and it gives:

| point | round-1 code | mine |
|---|---|---|
| b_hi | 4.7 dB / 37.1° | 4.8 dB / 37.6° |
| J1.0 | 5.6 dB | 5.7 dB |
| nominal | 7.6 dB | 7.8 dB |
| C3-rev2-F b_hi | 5.1 dB | 5.3 dB |

The same code, run at θ = 0 with the round-1 C3 (Ki 56), reproduces the published *"τ_o 1.0: PM 59.3°, GM ≥ 8 dB"*.
Mine gives 59.6° and 8.7 dB. So the published F2 number is right, but only at θ = 0.

⚠ **Method note.** For the ms_free points, the unsigned outer-break PM reads about 35–64° in both codes, even though the
loop is unstable. The encirclement happens where |L_o| > 1, across the sharp inner curve-hold resonance. Only the exact ρ
and the time domain can see it, and both do.

**Why this refutes under the brief.**
- It is an undeclared GM < 6 dB and PM < 45° on a tier-A single (b_hi), and GM < 6 dB on combined members (J1.0,
  b_q×J1.0).
- It falsifies the quantification of a declared miss: M-F1's "ρ < 1, friction-masked" becomes a 34–62° p-p limit cycle.
- Both happen in the fork configuration the design certifies as its flight prerequisite.

**What it does NOT say.**
- **It is not a fault of the cave bytes.** With no fork integral, or with τ_o ≳ 6 s, the primary passes every check in §3.
- **The cheapest remedies are a ruling and a re-declaration, at 0 bytes (BELIEF on adequacy; not re-scored here):**
  - either **no fork angle integral at all**, or **τ_o ≥ 6 s** for the primary;
  - or, if the J≈2 ms_free family is ruled out, **τ_o ≥ 1.5 s**, which clears b_hi, J1.0 and b_q×J1.0 to GM ≥ 8 dB;
  - then re-declare M-F1 and M-F2 with the operating-point numbers above.
- The fallback needs τ_o > 10 s, or none (§0.2 R3).
- A scheduled Ki (rev2-B §9 *C3B-P-sched*) is the structural fix if a fork integral is wanted.

### 0.2 Other findings

| # | severity | finding |
|---|---|---|
| R2 | **MEDIUM (fallback only)** | **C3-rev2-F's "ρ < 1" for the ms_free family has no margin.** Its worst point (b_lo×ms_free, 11.9 m/s, a 2.5, FA.83, e10) is ρ 0.99973 (ζ 0.007). It goes **ρ ≥ 1** under any of: the BELIEF sat(v) prior × 0.9 (1.00024); a 2.75 (1.00020); a 3.0 (1.00057). In the **integer lane, frictionless, it is already a sustained 10° p-p 0.59 Hz limit cycle at a 2.5**, where the linear ρ is 0.9997, because the integer floors tip it over. With friction it is 0.30° p-p late, 1.65° early (`sens_out.txt`, `intlane_out.txt`). The primary does not share this: it stays ρ ≤ 0.99978 under every variation tested, a ≤ 3.0 included. |
| R3 | **MEDIUM (default fallback C3B-F only)** | **The declared rate-invalid PI-only fault is quantified at θ = 0 only.** The page says "ρ 1.0017 on 19/2888 ms_free-product points". At the curve operating points the PI-only loop diverges on the **gated combined member b_q×J1.0** (ρ up to 1.0023). It also diverges on the ms_free family (up to 1.0065, 2062 points). It fails the R2 bars on every gated member, nominal included (17,077 points) (`loopsreport_F.txt`). The recommended hardened fallback (op-skip) removes this. The default's declaration is incomplete. |
| R4 | LOW | **The τ_o < 1 s declaration (M-F2) is θ = 0-only too.** At the operating points, τ_o 0.3 / 0.5 s make gated members linearly unstable (ρ up to 1.0061 / 1.0007). The unstable rings are at 0.37–1.15 Hz, and every ζ < 0.10 ring below 5 Hz is at 0.35–1.32 Hz, all inside R3\*. This is a quantification gap, not a coverage gap: the stop band covers it (`outreport_P.txt`). |
| R5 | LOW / INFO | **The fork integral plus Coulomb friction hunts on a straight**, below R3\*'s band. Integer lane, θ = 0, τ_o 1 s, identified friction: a **sustained 0.18–0.21 Hz cycle of 0.1–0.5° p-p** on nominal, b_hi and J1.0 at 8–20 m/s. It is 0.00° without the fork (`intlane_straight_out.txt`). It sits below R3\*'s 0.25 Hz edge and under M-N6's 1° revert, so no stop band covers it. This mainly belongs to the nonlinear lens (hunt gate). |
| R6 | LOW (interpretation) | **The strict reading of "hold ages 1–20 on every member"** (aged singles held to 45°): J_hi+h10 at the operating point is **43.9°** (8 m/s, a 2.5, FB.83; below 45 from hold offset e = 8 onward). It is 44.0° at 7.95 m/s. For C3-rev2-F, J_hi is 43.6° and b_lo 44.4°. The page's "aged-strict 56.0°" is θ = 0 only. These pass under the R2 convention, which the common scorer uses by default (aged = tier B, 30°). At this point the integer lane's I sits at the ICL clamp (8192 S), so the live loop is the PD loop, which clears 44°+ anyway (`escan_out.txt`, `intlane_out.txt`). |
| R7 | INFO | **"Every credible member through J1.3 passes"** holds for J1.3 itself: 36.7° within 10–16 m/s. It does not hold for the report product **b_q×J1.3**, which is **24.9°** (12.5 m/s, a 2.5, ring 0.69 Hz, ζ 0.19, inside R3\*). That product is not on the brief's gated list. |
| R8 | INFO | **The fade-0.80 transient** (grab rate, I live): b_hi is 44.3° at the operating point. C3-rev2-F's b_q×J1.0 is 29.9°. Both are transient states. |
| R9 | INFO | **Re(T/ω) against V294** (reported, not gated). At κ 0.866, the primary's 13 Hz anti-damping is **1.72×** V294 (ages 1–10) and **2.46×** (ages 0–9), and 20 Hz is 1.01–1.18×. The fallback is 3.8× / 4.8× at 13 Hz. Against V295, which is the goal's comparator, the page's numbers are right (`retw_out.txt`). |

---

## 1. Method and validation

### 1.1 The model (`c3r2_model.py`): mine, written from the bytes

**What it shares with the designers and scorers.** It imports no designer, scorer or earlier-refuter **loop** code. It
imports `c1r2_members` only for the member **parameters**, which are the brief's credible-set definitions.

**What it reads directly.**
- The V295 image (sha `5c044d65…` asserted), LE: OA 992, OB 507, FWD 5346, EMA α 37/128 (`0xC643C`), and 1159
  (`0xC613A`), so ABE_PER = 4.712.
- The GB-P / GB-F / G-P48 / G-F24 tables, parsed from the cave hex through the cave's own `mov imm32, r9`. GB-P and GB-F
  come from the **score** caves.
- An assertion that the GB-P and GB-F tables are **identical to the rows printed in the design's section "1.3
  Calibration cells"** (walk min G 559 / 560 reproduced).

**The lane, per the design's section "1.4 The loop, integer-exact Python" and `lane_mirror_v295.py`:**
- r26 = 8θ_h[n] + 8θ_h[n−1];
- E = 16 θ_sp − r26;
- E′ = E·G/256;
- I += E′·Ki/32768;
- P = E′·112/256;
- D = (Kd/8)·abe (fresh EMA) for P, or −(Kd/8)·x_h (held 6a56) for F;
- then the fade, the output lag, FWD, and the transport delay.

**Two formulations.**
- **LTI.** The 100 Hz hold enters as its fundamental. The plant is ZOH-discretised at 1 kHz with exact sampled θ and ω
  channels. It gives PM, GM up/down, the 5–30 Hz peak, Re(T/ω) and L20.
- **EXACT periodic.** An explicit state vector, built tick by tick. It includes:
  - the real 10-tick hold register, refreshed at the end of slot 0, at any age offset e = −1…10;
  - the 2-tap r26, the EMA, I, the output lag and the delay line;
  - optionally the fork integral as states (100 Hz, a 60 ms line).

  The 10-tick monodromy gives ρ and the closed-loop poles.

**The integer lane** (`c3r2_intlane.py`) is every floor and clamp of section 1.4 (G walk, Ep, the opposing-hand freeze, the
A3 bound and cap, the I quantum, ICL / PCL / DCL / SCL, the output lag, OCL). It runs around a 0.1 ms-sub-stepped plant
with the tanh spring, optional Karnopp friction (Fc and Fs from `v294_plant`), and an optional fork integral.

**Frames.**
- FA is the plant as identified, with the motor-frame operand carrying κ.
- FB scales J and b by 1/1.155.
- Gated: κ 0.83 / 1 / 1.155 under FA, and 0.83 / 1.155 under FB.
- Physical points: κ = 1/1.155 and 1/0.962.

### 1.2 Positive controls (`validate_out.txt`, `retw_out.txt`)

| anchor | published | mine |
|---|---|---|
| round-1 C3-P (Ki 56, G-P48), operating point | ms_free @12 a2.0: 24.4; a2.5: 15.1; b_lo×ms_free @12 a2.5 FA.83: 3.6, ρ 1.0008, 0.57 Hz, ζ −0.021 | 24.4 / 15.1 / 3.6, **ρ 1.0008, 0.57 Hz, ζ −0.021** |
| round-1 C3-P, θ = 0 | J_hi @1 FA.83: 51.7; J_hi+h10 min: 47.1; b_q×J1.0+h10 @26.9 FB.83: 34.2; b_q×J1.0 @26.9 FA.83: 40.6 | 51.7 / 47.1 / 34.2 / 40.6 |
| rev2-B `opbreak_ki40` (C3B-P) | b_lo×J_hi 32.8; J1.0 34.7; b_lo×ms_free 4.6; b_q×ms_free 8.2; ρ 0.9989 / 0.9979 | 32.8 / 34.7 / 4.6 / 8.2; ρ 0.9989 / 0.9979 |
| rev2-B (C3B-F) | b_lo×ms_free 1.1, ρ 0.9997; b_q×J1.0 30.3 | 1.1, ρ 0.99973; 30.3 |
| V295 / V294 Re(T/ω), κ 1 and 0.866 (16 numbers) | round-1 F4 table | **identical** to 0.01 |
| round-1 outer loop (θ = 0, Ki 56), outer break | τ_o 1.0: min PM 59.3, GM ≥ 8.0; τ_o 0.5 b_hi@11.9: 14.4 | 59.6 / 8.7 dB; 15.1 |

The rev2-B Ki-40 numbers that look different (J_hi 48.6 vs my 43.9; ms_free 21.2 vs 18.9) are **not** disagreements.
`rb_opbreak.py` reports the worst relative to the bar, and for aged singles that bar is 30°. The non-aged values match.

---

## 2. Findings in detail

### R1 (see §0.1): the fork integral at the curve operating points

**Why θ = 0 hides it.**
- At θ = 0 the inner loop's slow pole sits well clear of the fork integral's crossover, which is about 0.16 Hz at
  τ_o 1 s.
- At the curve operating point the spring softens to k·sech²(θ_op/sat), which is 0.18–0.31·k at 11–12.5 m/s, a 2.5.
- The inner loop's curve-hold mode then drops to 0.33–0.6 Hz with ζ 0.03–0.14 (ms_free family) or 0.30 Hz with ζ 0.37
  (b_hi).
- The fork integral's phase lag and its 60 ms round trip land on that mode.
- For the ms_free family, the inner T_ref has a resonant peak of about 1/(2ζ) ≈ 4–16. A τ_o = 1 s integral (|K_o| ≈ 0.3
  at 0.55 Hz) carries |L_o| well above 1 through the resonance's phase swing.

**The design's grid could not see it.**
- `rb_gate2.py` and `rb_opbreak.py` evaluate the operating points without the fork.
- `c3r1_outer.py` (round-1 F2) evaluates the fork only at θ = 0.
- No script on the record closes both at once.
- The binding speed, 11.75 m/s (the GB-P knot X3 = 2707, G 559), is not on `rb_opbreak.py`'s 0.5 m/s grid. It is on the
  brief's 0.25 m/s grid.

**Sweep coverage** (`c3r2_outer.py`):
- every gated member plus the ms_free products;
- v 1–35 m/s at 0.5, with 0.25 between 8 and 16, plus the knots;
- a 0, 1.0, 1.5, 2.0, 2.5;
- the five gated frames, e 0 and 10;
- τ_o 0.3 / 0.5 / 1.0 / 2.0;
- 334,400 points per design.

Exact ρ was computed wherever LTI PM < 35, GM < 6, or outer PM < 45. The τ scan (`c3r2_tauscan.py`) adds τ_o 1.5–10 and
none at the ms_free binding points.

**EVIDENCE / BELIEF.**
- **EVIDENCE:**
  - the arithmetic (two codes agree to ≤ 0.5° and 0.2 dB on the non-resonant points);
  - exact ρ;
  - the integer lane;
  - that the design's prerequisite text permits τ_o = 1 s (§6 FLIGHT PREREQUISITES, *"any fork angle integral at
    τ_o ≥ 1 s (CHECKED)"*).
- **BELIEF:**
  - the fork stand-in's form: a pure integral on the setpoint, 100 Hz, 60 ms round trip. That is the brief's
    description, and the round-1 stand-in.
  - whether the operator's fork will run an angle integral at all;
  - sat(v), the prior;
  - J ≈ 2 for ms_free at 10–15 m/s. The ident disfavours it, but the brief gates ms_free.

**What is still EVIDENCE if J ≈ 2 is ruled out.** b_hi (tier A), J1.0 and b_q×J1.0 still fall below the GM bar at
τ_o 1 s. None of those has J above 1.0.

### R2: the fallback's ρ < 1 has no margin

- **Primary, by contrast.** Its worst ρ moves only between 0.99834 and 0.99978 under every variation tested: the rate
  sample as a 1-tick difference, +1 ms transport, sat × 0.9 / × 1.1, and a 2.75 / 3.0 (`sens_out.txt`).
- **The fallback** crosses 1.0 under sat × 0.9 or a ≥ 2.75.
- **Integer lane, fallback, at its nominal binding point** (a 2.5, linear ρ 0.99973): a sustained 10.2° p-p cycle at
  0.59 Hz, frictionless. It is 31.9° p-p at a 2.75.
- **With friction:** 0.30–0.32° p-p late, after 1.6–3.8° half-cycles early.

R3\* covers the frequency. The page's "ρ < 1, no divergence" for C3-rev2-F is a linear-model statement with no margin.

### R3: the default fallback's PI-only fault at the operating points

- The design's own F3 table counts θ = 0 only, on a 1 m/s grid.
- At the operating points, the gated combined member b_q×J1.0 goes linearly unstable (ρ up to 1.0023; one example is
  PM 0.0 / ζ ≈ 0 at 15.5 m/s, a 2.0, FB.83, e10, a 1.26 Hz ring). The ms_free family reaches ρ 1.0065.
- The merged page already **recommends** the op-skip hardening for the fallback, which removes the PI-only state.
- What matters is that the **default** 220 B C3B-F is offered as acceptable *"if the orchestrator accepts the declared
  rare fault"*. The fault as declared is smaller than the fault as computed.

### R4: the τ_o < 1 s operating points

- At τ_o 0.3 / 0.5 s, gated members go unstable at the operating points: 4082 / 97 points, max ρ 1.0061 / 1.0007,
  rings 0.37–0.95 Hz.
- M-F2 quotes "0.31–0.47 Hz rings" from the θ = 0 analysis.
- Every unstable ring is still ≥ 0.35 Hz, so R3\* (0.25–5.5 Hz) covers it. This is a quantification gap, not a coverage
  gap.

### R5: straight-line hunt with the fork integral

- **Set-up:** integer lane, θ = 0, identified friction, τ_o 1 s, a 120 T × 60 ms pulse at 7 s, observed over 40 s.
- **Result:** a sustained 0.18–0.21 Hz cycle on nominal, b_hi and J1.0:

  | case | p-p |
  |---|---|
  | nominal @ 11.75 m/s | 0.35° |
  | b_hi @ 11.75 m/s | 0.52° |
  | J1.0 @ 11.75 m/s | 0.34° |
  | nominal @ 20 m/s | 0.11° |
  | nominal @ 8 m/s | 0.15° |

- **Without the fork:** 0.00–0.02°.
- **Coverage:** it is below R3\*'s 0.25 Hz edge, and too small for M-N6 (1°).
- **Severity:** sub-degree, so felt-or-not is R9's call. It is reported because no stop band covers it.

### R6 – R9: see §0.2.

---

## 3. What survived the attack

**θ = 0 GATE 2** (`opreport_P.txt`, `opreport_F.txt`; `c3r2_opsweep.py`).

The grid: v 1–35 m/s at 0.25, plus the knots, plus 0.05 between 7 and 13.5 (243 speeds); the gated members plus the
ms_free products; 9 frames; e −1 / 0 / 10. The e scan (`escan_out.txt`) is monotone, with the worst at e = 10, so
{−1, 0, 10} brackets every hold offset.

| | C3-rev2-P | C3-rev2-F | page |
|---|---|---|---|
| fails, R2 and strict | **0 / 0** | **0 / 0** | 0 / 0 |
| exact ρ ≥ 1 | 0 | 0 | 0 |
| tier-A min (strict, aged) | 56.4 (J_hi @1 FA.83 e10) | 56.4 | 56.0 |
| tier-B min excl. ms_free | 39.8 (b_q×J1.0 @27 FB.83 e10) | 40.3 | 39.8 / 40.3 |
| ms_free × {b_lo, b_q} | 38.5 / 40.8 | 31.1 / 36.8 | 38.5 / 40.8, 31.1 / 36.8 |
| min GM↑ / max 5–30 Hz peak | 13.7 dB / −0.1 dB | 6.6 dB / +2.1 dB | 13.8 / −0.2; 6.6 / +2.2 |

**Operating points without the fork** (1,364,688 points per design; a 1.0–2.5 in 0.25 steps; θ_op ≤ 450°).
- **C3-rev2-P:** 0 exact ρ ≥ 1, max **0.99890**. The fine 0.05 m/s scan agrees, and so does every modelling variation in
  `sens_out.txt`.
- **Gated non-ms_free members pass the R2 bars at v ≥ 8 and v < 8:**
  - worst b_lo×J_hi 32.8;
  - J1.0 and b_q×J1.0 34.7;
  - J_hi 43.9 (aged; see R6);
  - b_hi 46.8.
- **Below 8 m/s,** which the design never ran, nothing fails under R2.
- **The ms_free family** is as declared: PM 4.6–30, rings 0.48–1.41 Hz, ζ ≥ 0.030, ρ < 1.
- **C3-rev2-F:** max ρ 0.99973 (see R2).

**PD (I frozen), the hands-on fade floor 76/256, and the fade-0.80 PID** (`loopsreport_*.txt`).
- PD and PD297: 0 fails, 0 ρ ≥ 1, at θ = 0 and at the operating points, for both designs.
- PID80: see R8.

**Primary rate-invalid.** The op-skip routes to 0x2A164, so no loop exists. I take this as the judge's Ghidra-verified
claim; I did not re-verify it (bytes lens).

**Re(T/ω) against V295** (`retw_out.txt`). The page's restated numbers reproduce:
- C3-rev2-P 13 Hz: 0.80× (κ 1), **0.93×** (κ 0.866, ages 1–10), **1.33×** (ages 0–9).
- 20 Hz: 0.50–0.64× in every frame and age condition.
- 5 Hz: −0.27 against V295's +2.13. That is anti-damping, carried on rev2-B's §4.4 table, and F7 covers it.
- C3-rev2-F 13 Hz: 2.05× / 2.60×.
- At ages 11–20, 25 Hz is 1.39× V295 for the primary, where V295's own 25 Hz is small.

**L20.** Max |L(20)| / |L_V295(20)| is **0.968** for the primary (page 0.96) and **0.834** for the fallback (page 0.83),
over every gated member, speed, frame and e.

**Two-mass stress** (`tmreport_*.txt`). The set: f₂ 13–22 Hz, ζ₂ 0.02 / 0.05, r₂ 0.2 / 0.4, both placements, four
members, e 0 / 10, three κ, ten speeds; 11,520 points each. Exact results:

| | unstable | 5–30 Hz peak > +3 dB | worst peak | modal ζ below V295's | max Δζ |
|---|---|---|---|---|---|
| C3-rev2-P | 0 | 0 | −2.65 dB | 8 % | −0.031 |
| C3-rev2-F | 0 | 0 | −1.14 dB | 39 % | −0.044 |

This matches the declared M-F5 (10 % / 43 %, Δζ 0.034 / 0.041).

**The outer loop at θ = 0, τ_o ≥ 1 s.** No ρ ≥ 1 and no ζ < 0.10. Outer-break min PM is 55.2° and GM 11.1 dB for the
primary. The θ = 0 part of the design's prerequisite claim is right.

---

## 4. Limits and what I could not verify

- **The fork stand-in is the brief's description** (a pure angle integral on the setpoint, 100 Hz, 60 ms round trip) and
  the round-1 stand-in. The real StarPilot outer structure was not read; the fork repo is read-only and out of lens.
  Whether the fork will run an angle integral at all is a configuration ruling.
- **Everything above about 8 Hz is model.** R1 to R5 sit at 0.18–1.4 Hz, inside the identified band.
- **sat(v) is a prior (BELIEF)**, and **J ≈ 2 for ms_free is ident-disfavoured (BELIEF)**. R1(b) does not depend on
  either: b_hi, J1.0 and b_q×J1.0 are J ≤ 1.0.
- **Not re-verified here (other lenses):**
  - the op-skip target and epilogue;
  - the cave bytes;
  - the camera hazard;
  - the pol = −1 premise;
  - tracking, lurch and turn-hold time metrics.
- **The integer-lane friction is Karnopp with the family's Fc / Fs.** Real friction is rate- and temperature-dependent.
  The large ms_free limit cycles under the fork (34–62° p-p) are far above any friction effect, so this does not change
  R1(a).

## 5. What would turn this into a PASS

1. **Rule the fork-integral prerequisite again** at the curve operating points, and re-declare M-F1 and M-F2 with the
   numbers in §0.1. Options:
   - **none**, or τ_o ≥ 6 s for the primary; the fallback needs none or τ_o > 10 s;
   - or, if ms_free is ruled out, τ_o ≥ 1.5 s, which clears b_hi, J1.0 and b_q×J1.0 to outer GM ≥ 8.3 dB.

   Either way, add an R3\*-style watch for the 0.25–0.6 Hz curve-hold band.
2. Alternatively, a scheduled Ki (C3B-P-sched), re-run through this same outer-loop sweep (`c3r2_outer.py`) before
   anything is cut.
3. For the fallback: adopt the recommended op-skip hardening (R3), and either state R2's zero margin as a declared
   divergence (R3\*-covered) or lower its Ki.
4. Every outer-loop number on the page should come from a sweep that closes the fork AND linearises at the operating
   point. That means `c3r2_outer.py` or an equivalent, with exact ρ, not only the unsigned outer-break PM.

## 6. Files

| script (`refute_stability/c3r2/`) | output (`_scratch/angle_loop/refute-c3r2-stability/`) |
|---|---|
| `c3r2_model.py` (my LTI + exact periodic, V295/V294 included) | — |
| `c3r2_validate.py` | `validate_out.txt` |
| `c3r2_opsweep.py`, `c3r2_opreport.py` | `opsweep_P.npz`, `opsweep_F.npz`, `opreport_P.txt`, `opreport_F.txt` |
| `c3r2_outer.py`, `c3r2_outreport.py`, `c3r2_outdetail.py` (R1, R4) | `outer_P.npz`, `outer_F.npz`, `outreport_P.txt`, `outdetail_P.txt`, `outdetail_F.txt` |
| `c3r2_tauscan.py`, `c3r2_bhi_outer.py` (R1) | `tauscan_out.txt`, `bhi_outer_out.txt` |
| `c3r2_xcheck_c3r1code.py` (the cross-code check) | `xcheck_out.txt` |
| `c3r2_intlane.py`, `c3r2_intlane_outer.py`, `c3r2_intlane_straight.py` (the integer lane) | `intlane_out.txt`, `intlane_outer_out.txt`, `intlane_straight_out.txt` |
| `c3r2_sens.py`, `c3r2_escan.py` (R2, R6) | `sens_out.txt`, `escan_out.txt` |
| `c3r2_loops.py`, `c3r2_loopsreport.py` (R3, R8) | `loops_P.npz`, `loops_F.npz`, `loopsreport_F.txt` (and `_P`) |
| `c3r2_retw.py` (R9, L20) | `retw_out.txt` |
| `c3r2_twomass.py`, `c3r2_tmreport.py` | `twomass_P.npz`, `twomass_F.npz`, `tmreport_P.txt`, `tmreport_F.txt` |

**Withheld.** One of my responses this session was stopped by the automated safety classifier. At the time I was
reading the published score-cave and flight-cave hex files to locate the G(v) table. Per the task's process note I did
not reproduce or continue that inspection, and I took the table from the score caves instead. Those tables are asserted
equal to the rows printed on the design page. The flight cave's bytes were not decoded by this lens. The builder's H5
(Ghidra on the BUILT image) and the bytes lens remain the checks for them.
