# REFUTE C3 r1: the STABILITY lens (2026-10-01)

**Status: analysis only.** Nothing was built, flashed, sent on a bus or committed. The fork was not touched. Ghidra was
used read-only (`decompile_function` on stock `code.bin`: `FUN_00041464`, `FUN_0003f776`); nothing was saved. No shared
scorer, cache or design file was modified.

**Author:** the C3-r1 stability refuter, a subagent of the orchestrator `main`.

**Python:** the `bin_decompile` environment.

**Scripts:** `analysis-2020accord/studies/angle_loop/refute_stability/c3r1/`. **Outputs:**
`_scratch/angle_loop/refute-c3r1-stability/` (gitignored; every number below is in one of those files).

**Object under test:** `docs/specs/design/DESIGN-ANGLE-LOOP-C3-2026-10-01.md` and its scripts and cave hex in
`analysis-2020accord/studies/angle_loop/c3/`. PRIMARY **C3-P** (fresh guarded D, Kd 48, G-P48 table) and FALLBACK
**C3-F** (held D, Kd 24, G-F24 table). Both carry Kp 112, Ki 56, ICL 8192 and the A3 integral policy.

---

## 0. Verdict: REFUTED. Do not flash C3-P or C3-F as written.

### 0.1 The refuting finding (F1, HIGH, CONFIRMED by three methods)

**At the turn-hold operating points the design scores itself on, the loop falls far below the GATE-2 bars on gated
members of the credible set. On two gated tier-B members it is linearly UNSTABLE. None of this is declared.**

- **Where the gap is.** Every GATE-2 number on the page (and in the panel-2 frequency scorer it imports) linearises the
  plant at θ = 0, with the spring slope k.
  - The identified plant's spring is **k·sat(v)·tanh(θ/sat(v))**. That is the same `load_at` the design's own time
    scorer uses for its turn-hold scenario (`panel2/score_time.py`, `def load_at`). So in a steady curve the
    small-signal stiffness is **k·sech²(θ_op/sat)**.
  - At the design's own curve sizes (`tgt_alat`: θ_op = degrees(a·2.83·16/v²), a = 1.0–2.5 m/s²), that is
    **0.13–0.8 k** at 8–20 m/s.
  - The page claims turn-hold 0.98 at a 2.0 and a 2.5 over 8–22 m/s. That time evidence comes from **four members
    only**: `MEMBERS = ("nominal", "bc", "F_hi", "b_lo*J_hi")` in `panel2/score_time.py`. No high-inertia member was
    ever run through a curve.
- **What happens there.**
  - The crossover sits at 0.45–0.65 Hz in the G(v) dip (10–14 m/s), on or below the fixed PI corner (Ki/Kp gives
    0.62 Hz at every speed).
  - The softened spring removes the plant's own phase support.
  - The phase margin collapses on high-inertia members (ms_free, J ≈ 2 at 10–15 m/s).

**Table F1-a. C3-P, PID loop, worst phase margin at the curve operating point, v ≥ 8 m/s** (`kop_bymember.txt`).

In each cell, the first number is the **nominal frame at native hold ages**, the reading most lenient to the design. The
second, in brackets, is the worst over the gated frame box and hold ages 1–20. A cell that fails its bar is **bold**.
Bars: tier A 45° (native ages), tier B 30°.

| member (tier) | a 1.0 | a 1.5 | a 2.0 | a 2.5 |
|---|---|---|---|---|
| ms_free (A) | 49.1 (**42.7**) | **37.2** (**28.0**) | **23.1** (**15.2**) | **14.0** (**6.9**) |
| b_hi (A) | ≥ 45 | ≥ 45 | **43.8** (40.9) | **39.0** (36.2) |
| J_hi (A) | ≥ 45 | ≥ 45 | 48.9 (**43.0** native ages, FA.83, 8 m/s; 38.0 aged) | 46.7 (**40.9** native ages, FA.83; 35.9 aged) |
| J1.0, b_q×J1.0 (B) | 47.1 (38.5) | 40.1 (31.8) | 35.3 (**27.1**) | 32.4 (**24.4**) |
| b_lo×ms_free (B) | 34.4 (**22.8**) | **20.8** (**10.0**) | **9.0** (**0.5**) | **0.9** (**0.2**): **ρ > 1 in the box** (18 points; not in the nominal frame at native ages) |
| b_q×ms_free (B) | 38.5 (**27.2**) | **25.3** (**14.5**) | **13.3** (**3.7**) | **4.8** (**0.4**): **ρ > 1 in the box** (5 points, FA.83 / FB.83) |

- Points below the bars, v ≥ 8 m/s, out of 15,162 operating points per curve size (members × speeds × frames × ages):

  | | a 1.0 | a 1.5 | a 2.0 | a 2.5 |
  |---|---|---|---|---|
  | C3-P | 37 | 222 | 518 | 765 |
  | C3-F | 37 | 229 | 543 | 825 |
- Every other gated member passes, including the nominal member. Its own worst is 47.4° for C3-P at a 2.5 and 11.9 m/s.
  **C3-F's nominal member fails narrowly: 44.9° at a 2.5, FA.83, native ages.**
- **C3-F is within a few degrees of C3-P in every cell**, usually worse. For example, ms_free a 2.0 is 21.4 (14.7). See `kop_bymember.txt`.

**Three independent methods agree** (EVIDENCE):

1. **My own LTI loop** (`c3r1_model.py`, `c3r1_kop.py`). It uses exact fractional-delay sampled channels.
2. **The round-2 stability refuter's code** (`refute_stability/c2r2/c2r2_model.py`, a different code base). I ran its
   LTI and its periodic model with the C3 tables parsed from the C3 hex and k scaled the same way. It reproduces every
   number to 0.1°.
   - ms_free at 12 m/s, a 2.0: 24.4° in both codes.
   - b_lo×ms_free at 12 m/s, a 2.5, FA.83: signed PM −3.6°, exact ρ 1.0008, a 0.57 Hz pole with ζ −0.021.
3. **Exact periodic monodromy and my integer lane** with the real tanh spring (`c3r1_kop_exact.py`, `c3r1_hold_td.py`,
   `c3r1_hold_diag.py`).
   - **Exact:** 24 operating points are linearly unstable for C3-P and 41 for C3-F (ρ up to 1.0015 / 1.0018). They are
     b_lo×ms_free and b_q×ms_free at a 2.0–2.5 and 10.5–13.5 m/s.
   - **Integer lane, frictionless:** b_lo×ms_free at 12 m/s, a 2.5, FA.83 settles into a **sustained 0.57 Hz limit cycle
     of θ 32–57°** (±12°, 30 s run). Its I swings 4000–7500 S and its freeze duty is ≤ 5 %, so this is the PID state,
     not a clamp.
   - **Integer lane with the identified friction** (ms_free band, Fc ≈ 20 T): the same case rings at ±3–6° for about
     15 s (about 8 cycles) before it sticks.
   - The tier-A ms_free case at a 2.0 is friction-masked in the time domain: 0.1–0.3° residual. Its linear margin is
     the GATE-2 quantity, and it is 23°.

**Why this refutes under the brief.**
- It is an undeclared PM below 45° on tier-A singles (ms_free, b_hi, J_hi) and below 30° on tier-B gated members
  (J1.0, b_q×J1.0, ms_free × {b_lo, b_q}), including linear instability.
- The stop band does not cover it. R3\* fires only on growth or ζ < 0.10. The ms_free a 1.5–2.0 rings are 0.52–0.56 Hz
  with ζ 0.14–0.22, so they are not caught. They also sit at R3\*'s 0.5 Hz lower edge.
- No M-item on the page mentions curve holds on high-inertia members, or the operating-point stiffness at all.

**The same structure carries the defect in every variant** (EVIDENCE: same check). At ms_free, 12 m/s, a 2.0:

| variant | PM |
|---|---|
| C3-Pd | 22.9° |
| C3-P44 | 22.6° |
| C3-PA2 | equal to C3-P (the A2/A3 policy is not in the linear loop) |

### 0.2 The other findings (§2)

| # | severity | finding |
|---|---|---|
| F2 | **MEDIUM–HIGH (stop-band coverage)** | The page's claim *"τ_o < 1 s is caught by R3\*"* is false for the worst cases. With a fork angle integral at τ_o 0.5 s, the outer-loop ring is **0.31–0.40 Hz**. At τ_o 0.3 s it is **0.37–0.94 Hz**, with the near-unstable worst at **0.45–0.47 Hz**. Both lie below R3\*'s 0.5 Hz lower edge. The integer lane with a fork stand-in shows a 0.40 Hz ring: ζ ≈ 0.05 on nominal at 11.9 m/s, and an almost sustained 8° p-p on b_hi at 11 m/s, both at τ_o 0.3 s. At **τ_o ≥ 1 s the outer loop is fine** (PM ≥ 56°, GM ≥ 8 dB). |
| F3 | **MEDIUM** | The page's §7 H-rate *"fails safe: yes"* is not supported for stability. When the motor rate is invalid, D = 0 but the angle P+I keep running. That PI-only loop is **linearly unstable** on 62 of 2888 gated points for C3-P (b_lo×J_hi, b_lo×ms_free, b_q×ms_free) and 32 of 2888 for C3-F. It has ζ < 0.10 on 445 / 351 points. |
| F4 | MEDIUM (reporting; round-2 finding F3 not resolved) | The page's Re(T/ω) claims hold only at κ 1 and ages 1–10. At the **physical** κ 0.866: C3-P 13 Hz is 0.93× V295, not 0.79×, and 5 Hz is −0.31, not the declared −0.05. At ages 0–9: 13 Hz is 1.14× (κ 1) and 1.33× (κ 0.866). C3-F's 13 Hz is 2.0–2.6×, against the declared 1.9×. The panel's own T4b table shows this, but the page does not. R4 covers any resulting line. |
| F5 | LOW | Two-mass stress: 0 unstable and no 5–30 Hz peak above +3 dB. The closed-loop modal damping is **below V295's on the same plant** in 10 % (C3-P) and 43 % (C3-F) of 11,520 stress points, mostly at 13–17 Hz. The maximum deficit is Δζ 0.034 / 0.041. |
| F6 | INFO | Integer lane: a sub-count quantisation limit cycle (about 0.1°, 0.25 Hz) at 1 m/s on J_hi. With friction there is 0.1–0.2° p-p stick-slip hunting in every curve hold (nonlinear lens). |
| F7 | INFO | The page's §1.2 hex listing has typos: `cc e5` (the hex has `2c e5` = −6868) and `68 f6` (the hex has `e8 f6` = −2328). The decoded values in the listing are correct. |

### 0.3 What I corroborate (θ = 0 linearisation; §3)

C3-P and C3-F pass GATE 2 completely in my independent model **when linearised at θ = 0**. The check covered:
- the whole credible set plus 14 report products;
- **every hold offset e = −1…10** (ages 0–9 up to 11–20);
- the gated frame box plus the physical frame points;
- the 0.25 m/s grid plus the knots, with a 0.05 m/s fine grid at 7–13.5 and 15–16.5 m/s;
- five loop states.

The results:
- **0** tier-A or tier-B fails, **0** strict fails, **0** GM < 6 dB, **0** peaks above +3 dB, **0** L20 > V295.
- Exact periodic check: **0** unstable points and **0** exact-GM < 6 dB points over 27,740 gated points per loop.
- Every published anchor reproduces (§1).

---

## 1. Method and validation

### 1.1 The model (`c3r1_model.py`): independent of every designer and scorer

**Inputs.** It imports no designer or scorer code (no score_freq, ds_model, c1_lib, c3_\*, r2a_\* or c2r2_\*). It reads:
- the V295 image, sha `5c044d65…` asserted, for OA 992, OB 507, FWD 5346, α 37/128 (`0xC643C`), 1159, and the fade
  records;
- the **selector-7 Kp/Kd record addresses**. The pointer tables at `0xCB994`/`0xCB7D4` resolve to `0xE5378`/`0xE511C`,
  so C3's cal writes at `0xE5384`/`0xE5126` land in the live records (EVIDENCE);
- the **C3 cave hex**: the table is located through its own `mov imm32, r9`, and the immediates are decoded
  (26000/13000, 512, 2880, 1382, 4096, 1250, shl 4/6, sar 12/8/10);
- the r71b ident JSONs.

**Ghidra, this session.** `FUN_00041464`: `gp-0x6abe = (prev + ((4f50·1024 − prev)·u16[0xC643C]) >> 7) >> 10`. This
runs on the valid branch (`4f50 + 13000 ≤ 26000`, unsigned). `FUN_0003f776`:
`gp-0x6a56 = pol·((abe·48·u16[0xC613A]) >> 15)`, clamped to ±12000, and 0 when abe is invalid.

**Two formulations.**
1. **Averaged-hold LTI with exact sampled channels.**
   - Each plant channel is the modified-z FRF of the ZOH plant, with a fractional total delay per channel.
   - The rate former is a window mean (θ(t) − θ(t − w))/w, built from two exact θ channels.
   - Transport delay is 2 or 6 ms.
2. **Exact periodic model on a 0.25 ms sub-step grid.**
   - It has one plant, a sub-step input delay line, the 10-tick hold refreshed at slot 4 after the lane (any offset e),
     the 2-tap r26, the EMA, I, D and the output lag.
   - The 10-tick monodromy gives ρ and the closed-loop poles. Gain scaling gives the exact GM, and an extra delay gives
     the exact delay margin.

**The integer lane** (`c3r1_intlane.py`) is written from the cave listing, the in-place edits and the V295 lane bytes:
- E = (sp<<2) − r26;
- the guarded op;
- the G walk, then E·G >> 8;
- the A3 freeze, bound, cap and ramp;
- e5, the I with ICL 8192, P, D and DCL;
- the fade, SCL, the output lag, then ×(pol·5346) >> 15, then OCL.

Around it: Honda's integer EMA, the 0.1° quantiser, the exact 10-tick hold, 0.1 ms plant sub-steps, Karnopp friction,
and optionally the tanh spring, a road torque and a fork stand-in.

**Frames.** FA means the plant is as identified and the motor-frame operands (fresh or held D) carry κ. FB means J and b
are scaled by 1/1.155. Gated: κ 0.83/1/1.155 under FA and 0.83/1.155 under FB. Physical: κ = 1/1.155 and 1/0.962.

### 1.2 Positive controls (`validate_out.txt`)

| anchor | published | mine |
|---|---|---|
| Re(T/ω) 5–25 Hz, V294, V295 (ages 1–10 and 11–20), C3-P and C3-F (both ages): 56 numbers | page §4 and panel2 T4 | **max \|Δ\| 0.005** |
| C3-P PM: nominal / J_hi @1 FA.83 / J_hi+h10 / b_q×J1.0+h10 @26.9 FB.83 / b_lo×ms_free+h10 @9 / b_q×ms_free+h10 @15.75 | 69.2 / 51.7 / 47.1 / 34.2 / 35.4 / 36.6 | 69.2 / 51.7 / 47.1 / 34.2 / 35.3 / 36.6 |
| C3-F PM, same set | 68.6 / 50.7 / 34.8 / 35.8 / 36.9 | identical |
| exact ρ and ring at the same points | 0.9655 (0.82 Hz, ζ 0.564), 0.9780 (1.89, 0.184), 0.9817 (1.26, 0.227), 0.9916 (1.21, 0.110) | identical |
| exact delay margin → PM, b_q×J1.0+h10 | — | 54.5 ms = 34.2° (equals the LTI PM) |
| integer lane vs linear ring, 2° step, b_q×J1.0+h10 @26.9 FB.83 | 1.89 Hz, ζ 0.184 | 1.88 Hz, ζ 0.178 (`intlane_T1.txt`) |
| operating-point PM, my code vs the c2r2 code (`c3r1_extras.py` X1) | — | identical to 0.1° at 9 points per design; c2r2's signed PM gives −3.6° / −5.7° on the unstable points |

The model is right. F1 is a **missing operating point** in the scorers, not an arithmetic disagreement.

---

## 2. Findings

### F1: HIGH, CONFIRMED, refuting. GATE 2 collapses at the curve operating point (see §0.1)

**Sizing.** The scorers' own `tgt_alat` gives θ_op = SR·L·a/v² with SR 16 and L 2.83 m. The spring factor is
sech²(θ_op/sat(v)), with sat(v) = 19.3 + 546·e^(−v/3.01) (the prior, BELIEF, used unchanged by `v294_plant` and
`score_time.load_at`).

| v (m/s) | a 1.0 | a 1.5 | a 2.0 | a 2.5 |
|---|---|---|---|---|
| 8 | 41° ×0.63 | 61° ×0.39 | 81° ×0.21 | 101° ×0.11 |
| 10 | 26° ×0.66 | 39° ×0.42 | 52° ×0.24 | 65° ×0.13 |
| 12.5 | 17° ×0.72 | 25° ×0.49 | 33° ×0.31 | 42° ×0.18 |
| 15 | 12° ×0.79 | 17° ×0.60 | 23° ×0.42 | 29° ×0.28 |
| 20 | 6° ×0.90 | 10° ×0.80 | 13° ×0.67 | 16° ×0.55 |
| 26.9 | 4° ×0.97 | 5° ×0.93 | 7° ×0.87 | 9° ×0.81 |

(`kop_out.txt`)

**The integral is live in these holds** (EVIDENCE: the arithmetic, and the integer lane's freeze duty of 0.00):
- At 12 m/s and θ_op 36°, the A3 bound is 360·16 + 1250 = 7010 S. The spring load is about 5500 S on ms_free.
- At 45° the clamp is ICL 8192 S, and the I sits at 5948 S.

**Mechanism** (EVIDENCE, arithmetic from the cave): the PI corner is Ki/Kp = (56/32768)/(112/256) per tick, which is
0.62 Hz **at every speed**, because Ki and Kp both act on E′ = E·G/256. In the G dip at 10–14 m/s the crossover falls
to 0.45–0.65 Hz. A softened spring on a J ≈ 2 member leaves almost no plant phase there.

**Exact instability** (`kop_exact_out.txt`):

| | C3-P | C3-F |
|---|---|---|
| operating points (v ≥ 8) with LTI PM < 30° | 1316 | 1365 |
| of those, exact ρ ≥ 1 | 24 | 41 |

- **C3-P:** b_lo×ms_free a 2.5 at 11.0–12.5 m/s (worst ρ 1.0015, 0.56 Hz) and b_q×ms_free a 2.5 at 12.5–13.5 m/s
  (ρ 1.0008).
- **C3-F:** includes 2 unstable points in the nominal frame at native ages.

**Low-speed band** (v < 8; not a goal band, but GATE 2 is all speeds). J1.0 and b_q×J1.0 fall to 25–28° (FA.83, e10),
and J_hi to 36–40°, at 3–7.5 m/s. Some of those θ_op exceed steering lock (at 3 m/s, a ≥ 1.5); 7.5 m/s at a 2.5
(θ 115°) is physical.

**Time domain, integer lane** (`hold_td_fric0.txt`, `hold_td_fric1.txt`, `c3r1_hold_diag.py`; ramp in over 1.5 s,
then a 120 T 60 ms pulse at 7 s):

| case | frictionless | identified friction |
|---|---|---|
| C3-P b_lo×ms_free @12, a 2.5, FA.83 | **limit cycle θ 32–57°, 0.57 Hz, sustained 30 s** | ±3–6° ring for about 15 s (8 cycles), then sticks |
| C3-F, same | 26.8° p-p sustained | 12.9° p-p at 12–14 s |
| C3-P b_lo×ms_free @12, a 2.0 (nominal frame) | 1.5° p-p sustained | 0.22° |
| C3-P ms_free @12, a 2.5, FA.83 | 1.2° p-p, ζ ≈ 0.05 | 0.31° |
| C3-P b_q×ms_free @13.5, a 2.5, FA.83 | 5.1° p-p | 0.05–0.3° |
| nominal / J_hi / J1.0 / b_q×J1.0, every case | decays (ζ 0.2–0.4) | decays |

**EVIDENCE / BELIEF split.**
- **EVIDENCE:**
  - the arithmetic and the margins, from two codes plus the exact periodic model plus the integer lane;
  - that the scorers never linearise off θ = 0 (`panel2/score_freq.py` `member_plant` builds `DM.rigid(J, b, k)`);
  - that the time scorer runs only nominal / bc / F_hi / b_lo×J_hi;
  - that the operating points are the design's own (`score_time.tgt_alat` and `ALATS`).
- **BELIEF:**
  - the shape of sat(v), which is the prior and was not fitted on r71b;
  - the physical credibility of J ≈ 2 at 10–15 m/s. The J profile's held-out cost prefers J ≤ 0.5 there (ident §3.2).
    **But ms_free is a gated tier-A member in the brief and on the page**, and b_hi, J1.0 and b_q×J1.0 fail too.
  - that real friction masks the tier-A case. It does in my lane, but GATE 2 is a linear bar.

**Feasibility probe** (inline run on `c3r1_model.py`, all at native hold ages; **NOT a design**). Lowering Ki moves the PI corner below the curve
crossover:

| Ki | ms_free @12 a 2.0 | ms_free @12 a 2.5 | b_lo×ms_free @12 a 2.5 FA.83 | b_q×J1.0 @26.9 FA.83, ages 1–10 (θ = 0) |
|---|---|---|---|---|
| 56 (C3) | 24.4 | 15.1 | 3.6 | 40.6 |
| 28 | 56.7 | 46.5 | 25.3 | 50.7 |
| 20 | 66.3 | 57.3 | 34.7 | 53.1 |

Ki is a 0-byte cal. Every time gate (tracking, hold, lurch) would have to be re-scored, so this is not a fix, only the
direction one lies in. A Ki that is not multiplied by G in the dip, or a scheduled Ki, is the other route.

### F2: MEDIUM–HIGH. "τ_o < 1 s is caught by R3\*" is false; the outer-loop ring is below R3\*'s band

Sources: `outer_out.txt` and the integer lane with a fork stand-in (100 Hz integral, 60 ms round trip, on the
setpoint).

| τ_o | worst PM | worst GM | ring frequency at PM < 30° |
|---|---|---|---|
| **1.0 s** | 59.3° (C3-P) / 56.1° (C3-F) | **≥ 8.0 dB** | — (none below 45°) |
| 0.5 s | 14.4° (b_hi@11.9, κ 1.155, e10) | 2.0 dB | **0.31–0.40 Hz** |
| 0.3 s | about 0 (b_hi@11, e10; \|T\| peak 68) | about 0 | **0.37–0.94 Hz**; the nominal worst is **0.45–0.46 Hz** |

- **Integer lane at τ_o 0.3 s:**
  - nominal at 11.9 m/s rings at **0.40 Hz**, 4.2 → 2.1 → 0.8° p-p over 5 s windows (ζ ≈ 0.05);
  - b_hi at 11 m/s holds about 8° p-p at 0.4 Hz over 30 s.
  - The ζ values are estimates from 5 s window amplitudes (frictionless lane).
- **Where the claim fails.** R3\* is defined as 0.5–5.5 Hz (page §6), so it does not see these rings. The prerequisite
  itself (τ_o ≥ 1 s, none below 8 m/s) is sound. What fails is the backstop, and the page states the backstop as the
  mitigation.
- **Fix (not run):** widen R3\* down to 0.25 Hz, or make τ_o a checked fork-config value.

### F3: MEDIUM. The rate-invalid "fail-safe" leaves an undamped PI angle loop (`doff_out.txt`)

Honda's validity form (cave `0xC4C08..12`) zeroes op on C3-P. `FUN_0003f776` zeroes gp-0x6a56 on C3-F. **θ comes from
the motor-position path and stays valid**, so the lane keeps steering with P+I and no D.

| | C3-P | C3-F |
|---|---|---|
| gated points (1 m/s grid, e 0/10, jb 1/0.866), exact | 2888 | 2888 |
| ρ ≥ 1 | **62** | **32** |
| ζ < 0.10 | **445** | **351** |

- Worst points for C3-P:
  - b_lo×ms_free @10, e10, FB: ρ 1.0037 at 1.10 Hz;
  - b_lo×J_hi @8, e10, FB: ρ 1.0025 at 1.94 Hz.
- Nominal stays stable (worst ρ 0.980).
- How long the state can persist with the lane engaged (DTC / assist shutdown) is BELIEF, not traced.
- V295's rate loop loses only its feedback operand in the same fault, which bounds rather than de-damps.
- **Fix (not run):** gate the PID on op validity (skip the lane).

### F4: MEDIUM (reporting). The Re(T/ω) claims are frame- and phase-fragile, and round-2 F3 is still unresolved (`retw_out.txt`)

Re(T/ω) is the worst over 1–35 m/s, in T counts per deg/s; > 0 damps.

| | 5 Hz | 7 | 10 | 13 | 15 | 17 | 20 | 25 |
|---|---|---|---|---|---|---|---|---|
| V295, κ 1 (page) | +2.46 | +1.24 | +0.09 | −0.47 | −0.66 | −0.77 | −0.82 | −0.76 |
| V295, κ 0.866 (physical) | +2.13 | +1.08 | +0.08 | −0.41 | −0.57 | −0.67 | −0.71 | −0.66 |
| **C3-P, κ 0.866** | **−0.31** | −0.30 | −0.35 | **−0.38 (0.93×)** | −0.39 | −0.39 | −0.39 (0.55×) | −0.37 |
| **C3-F, κ 0.866** | −0.70 | −0.76 | −0.83 | **−0.83 (2.05×)** | −0.81 | −0.78 | −0.71 | −0.57 |

- At **ages 0–9**, C3-P 13 Hz is −0.38 against V295's −0.34 (**1.14×**), and −0.39 against −0.29 (**1.33×**) at
  κ 0.866. C3-F 13 Hz is **2.4–2.6×**.
- A rate-former window of 1.5 ms and a one-tick-late fresh read move these by ≤ 0.1. They move the crossover PM by
  ≤ 0.4° (`sens_out.txt`).
- **What the page says.** §0.2, §4 and M-C3-4 quote the κ 1, ages 1–10 numbers as the claims: "13 Hz 0.79×", and "5 Hz
  −0.05, the least on the panel". The panel's own T4b (3 of 16 conditions above 1× at 13 Hz) is not carried onto the
  page.
- **Not refuting.** R4 covers any resulting line, and F7 > 0 covers 5–8 Hz.

### F5: LOW. Two-mass stress (`twomass_out.txt`)

The stress set:
- f₂ 13 / 15 / 16.5 / 17 / 20 / 22 Hz, ζ₂ 0.02 / 0.05, r₂ 0.2 / 0.4;
- both placements: free-free resonance at f₂, and wheel-side ring at f₂;
- nominal / b_lo / b_q / J_hi, e 0 / 10, κ 0.83 / 1 / 1.155, 10 speeds;
- 11,520 points per design.

Results:
- **0 unstable.** Max ρ is 0.984 for C3-P and 0.986 for C3-F.
- **No 5–30 Hz peak above +3 dB.** The worst is −2.7 / −1.3 dB.
- The loop raises modal ζ to ×1.2–3.3 of ζ₂.
- **But it is below V295's modal ζ on the same plant** in 1134 (C3-P) and 5013 (C3-F) points:
  - at 13 Hz this happens in 21 % / 71 % of cases;
  - the worst Δζ is −0.034 / −0.041 (b_lo @17, 13 Hz, r₂ 0.4).
- This agrees with F4 and with C3-F's declared M-C3-5 (R4 watch 10–17 Hz).

### F6: INFO. Limit cycles (`lc_out.txt`, `hold_td_fric1.txt`)

- Frictionless, the integer lane settles to zero at every θ = 0 binding point.
- The one exception is J_hi at 1 m/s, FA.83, after a 0.3° step: a **±1-count (0.1°) cycle at 0.25 Hz** with T 2–4
  counts p-p, sub-wire and below R3\*.
- With friction, every curve hold shows 0.1–0.2° p-p hunting (stick-slip of the integral loop). That belongs to the
  nonlinear lens's hunt gate.

### F7: INFO. Listing typos

Page §1.2 shows table bytes `cc e5` and `68 f6`. The hex (`c3_cave_C3-P.hex`) has `2c e5` (−6868) and `e8 f6` (−2328).
The decoded values on the page are the hex's, and the G walk checks out against the knots.

---

## 3. What survived the attack (θ = 0, the scorers' own linearisation)

Sources: `report_base.txt`, `exact_out.txt`, `sens_out.txt`.

| check | C3-P | C3-F |
|---|---|---|
| tier A min PM, ages 1–10 / 0–9 | 51.7 / 52.1 (J_hi@1 FA.83) | 50.7 / 51.1 |
| aged singles, strict 45°, e 1–10 | 47.1 (J_hi+h10) | 46.9 |
| combined min, any e −1…10 | 34.2 (b_q×J1.0+h10 @27 FB.83) | 34.8 |
| ms_free × {b_lo, b_q} min | 35.3 | 35.7 |
| min PM per hold offset | monotone 37.7 (e0) → 34.2 (e10); e −1 is 38.0 | 39.2 → 34.8 |
| physical frame points min | 35.3 | 35.8 |
| GM↑ min (LTI / exact ×2) | 13.7 dB / 0 exact fails | 6.7 dB / 0 |
| exact ρ ≥ 1, gated (27,740 pts per loop) | 0 (max 0.9937) | 0 (max 0.9941) |
| least-damped R3\*-band pole | 1.21 Hz, ζ 0.110 | 1.20 Hz, ζ 0.108 |
| 5–30 Hz closed-loop peak | −0.15 dB | +1.96 dB |
| L20 / V295 max | 0.970 | 0.833 |
| I-frozen (PD) loop | min 50.1°, 0 below bars | min 44.0° (aged B), 0 below bars |
| fade 0.80 (grab rate, I live) / 0.297 (hands-on, I frozen) | 39.1° / 98.9° | 39.4° / 104.9° |
| gain ladder 0.05–2 at the binding points (exact) | stable everywhere | stable everywhere |
| rate-former 0–3 ms, abe 1 tick late | ≤ 0.4° change in PM | ≤ 0.3° |
| fork integral τ_o 1 s | PM ≥ 59.3°, GM ≥ 8.0 dB | PM ≥ 56.1°, GM ≥ 8.3 dB |

**Report members** (min PM, every e, gated frames):

| member | C3-P | C3-F | note |
|---|---|---|---|
| b_lo×ms_free×tau6 | 33.5 | 33.6 | |
| b_lo×J_hi2 | 32.1 | 32.6 | |
| b/1.9×J1.0 | 30.2 | 31.2 | |
| b_q×J1.3 | **29.0** | 30.2 | J 1.3 is the brief's "not excluded" ceiling at 10–16 m/s |
| light_b | 8.7 | about 0 | report-only prior, contradicted by r71b |

---

## 4. Limits, and what I could not verify

- Everything above about 8 Hz is model, as the page says. F1–F3 sit at 0.3–2 Hz, inside the identified band.
- **sat(v)** and the **credibility of ms_free's J ≈ 2** are BELIEF. They are the two rulings that decide how hard F1
  bites:
  - If ms_free is dropped at 10–15 m/s, F1 still stands on b_hi (A) and on J1.0 / b_q×J1.0 (B).
  - Those failures are milder: PM 36–44 and 24–28, with ζ 0.18–0.32.
- The fork's actual τ_o and outer-loop structure (F2) are not specified anywhere I could read. The stand-in is a pure
  integral.
- The persistence of the rate-invalid state with the lane engaged (F3) is untraced.
- pol = −1 is record EVIDENCE that I did not re-measure. It cannot be told from 0x14A (round-2 F8).
- I did not score friction, tracking or lurch beyond the curve-hold rings, bytes, or fail-safe beyond F3. Those are other
  lenses.

## 5. What would turn this into a PASS (for the designers; probes, not designs)

1. **Linearise GATE 2 at the operating points the goal scores.** That means k·sech²(θ_op/sat) for a 1.0–2.5 at
   v ≥ 8, on every gated member.
   - Then either re-size the integral, as the Ki probe in §2 F1 shows, or schedule Ki independently of G in the dip.
   - Or pre-declare the curve-hold rings with a stop band that covers 0.45–0.9 Hz at ζ < 0.25.
   - Run ms_free / J1.0 / b_hi through the time scorer's `th` scenario.
2. **R3\* lower edge → 0.25 Hz**, or a static check of the fork's τ_o (F2).
3. **Skip the PID when op is invalid**, or declare the PI-only fault state with its margins (F3).
4. **Restate the Re(T/ω) claims at the physical κ and at ages 0–9** (F4).

## 6. Files

| script (`refute_stability/c3r1/`) | output (`_scratch/angle_loop/refute-c3r1-stability/`) |
|---|---|
| `c3r1_model.py` (independent LTI + exact periodic) | — |
| `c3r1_validate.py` | `validate_out.txt` |
| `c3r1_sweep.py`, `c3r1_report.py` | `sweep_base.npz`, `report_base.txt` |
| `c3r1_exact.py` | `exact.json`, `exact_out.txt` |
| `c3r1_kop.py`, `c3r1_kop_exact.py` (F1) | `kop.json`, `kop_out.txt`, `kop_bymember.txt`, `kop_exact_out.txt` |
| `c3r1_intlane.py` (integer lane), `c3r1_intlane_run.py`, `c3r1_lc.py`, `c3r1_hold_td.py`, `c3r1_hold_diag.py` | `intlane_T1.txt`, `lc_out.txt`, `hold_td_fric0.txt`, `hold_td_fric1.txt` |
| `c3r1_outer.py` (F2) | `outer_out.txt` |
| `c3r1_doff.py` (F3), `c3r1_sens.py` | `doff_out.txt`, `sens_out.txt` |
| `c3r1_retw.py` (F4) | `retw_out.txt` |
| `c3r1_extras.py` (the c2r2 cross-code check, the variants, the Ki probe) | `extras_out.txt` |
| `c3r1_twomass.py` (F5) | `twomass.json`, `twomass_out.txt` |
