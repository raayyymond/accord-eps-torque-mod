# DESIGN C3 rev2-A — angle loop, REVISER 1 (2026-10-01): PRIMARY R1-P, FALLBACK R1-F

**Status: DESIGN ONLY.** Nothing built, flashed, sent; the fork was not touched; no `.rwd` or image written.
Ghidra read-only (dry-run) on stock `code.bin` / the open V294 program (code-identical to V295 except cal `0xC63EA`+CRC).
Python is the `bin_decompile` env. Every number below is read from the V295 image (`5c044d65…`) or executed by a scorer /
refuter model that is **validated bit-exact against the panel-2 common scorers** (see §2).

**Author:** reviser 1 of 2 (independent), a SUBAGENT of the orchestrator `main`.

**What this is.** Design C3 (`DESIGN-ANGLE-LOOP-C3-2026-10-01.md`, PRIMARY C3-P / FALLBACK C3-F) was **REFUTED** on three
lenses (stability F1–F7, nonlinear N1–N8, bytes-and-fail-safe F1–F5). This revision **resolves every finding** — each by a
design change **re-scored on the refuters' own models and the common scorers**, or by a **pre-declared quantified miss with
a covering stop band** — and delivers **R1-P (PRIMARY)** and **R1-F (FALLBACK)**. Every decision-bearing claim is **EVIDENCE**
(method given) or **BELIEF**. Code is cited by address or grep string, never line number.

**Scripts** (`analysis-2020accord/studies/angle_loop/c3/rev2A/`, run `python <script>`):

| script | what it does | key result |
|---|---|---|
| `rev2a_lane.py` | the rev2A time lane on top of the validated `c3nl_sim` (per-column Ki / bound-ref / F3); a control reproduces `c3nl_sim.Lane` | control **0 / 20000** |
| `rev2a_asm.py` | assembles the rev2A caves from `e2_asm` + raised-dip rows + the three edits; byte counts + listing | R1-P **226 B** |
| `rev2a_h1.py` | the assembled rev2A bytes EXECUTED by `e2_asm`'s V850E2 interpreter vs the rev2A arithmetic reference | **0 / 40000** |
| `exp1_kop_ki.py`, `exp1b_msfree.py`, `exp1c_bars.py` | F1 curve-hold operating-point GATE-2 vs Ki (refuter `c3r1_kop` model) | §3.1 |
| `exp2_r2box.py`, `exp2b_ki18.py` | R2-box (θ=0) GATE-2 + M20 + peak‖T‖ on the refuter model | §3.1 |
| `exp3_time.py` | lurch (both directions), reversal, S-bend, small-signal (refuter `c3nl_lens` builders) | §3.3 |
| `exp4a_fast.py`, `exp4c_r71b_agg.py` | tracking trade-off: turn-hold, S-bend, small-signal, **r71b real paths** | §3.2 |
| `exp5_fault.py` | F3 rate-invalid fault (R1-P inert vs C3-P PI-only) | §3.4 |
| `exp6_retw.py` | F4 Re(T/ω) at the physical κ and ages 0-9 (refuter `c3r1_model.retw`) | §3.5 |

---

## 0. The answer in one page

### 0.1 The two implementations (and the firmware-camera variant)

| | **R1-P (PRIMARY)** | **R1-F (FALLBACK)** | **R1-P-cam (firmware camera interlock)** |
|---|---|---|---|
| base | C3-P (fresh guarded D, Kd 48) | C3-F (held D Kd 24, pol-free) | R1-P + the `gp-0x6803==2` gate |
| **F1 fix** — Ki | **56 → 40** (cal `0xC63E6`, 0 cave bytes) | 56 → 40 | 40 |
| **N2 fix** — dip knot | G@`X=2707` **463 → 520** + two slopes (cave table DATA, 0 code bytes) | same | same |
| **N1/N5 fix** — integral bound | references the **SETPOINT** `gp-0x69ae` (\|sp\|<<2 / <<4), **byte-neutral** | same | same |
| **F3 fix** — rate-invalid | `cmovh r0,r16,r16` → E:=0 when the 1 kHz rate is invalid (**+4 B**) | same (keeps the fresh-rate read as a validity flag) | same |
| cave | `0xC4C00`, **226 B** (184 code + 42 table), sha `e3bab42ac218` | **226 B**, sha `e3bab42ac218` (same cave; in-place differs) | **246 B**, sha `1159ee1cd0fc` |
| in-place set | E1 E2 B2 A2 E4 HOOK **OPH** V1 (20 B) | E1 E2 B2 A2 E4 HOOK **E5a E5b** V1 (23 B) | R1-P's + nothing (r25 already live) |
| cals changed vs V295 | 24 B (C3-P's set, **Ki = 40**) | 24 B (Kd Y = 24) | + fade record `0xE54FC` ← `0xE564C` (24 B) |
| bytes written | in-place 20 + cal 24 + cave 226 = **270**, RAM 0 | 23 + 24 + 226 = **273**, RAM 0 | 20 + 48 + 246 = **314**, RAM 0 |
| GATE 2 R2-box (θ=0) | **0 fails**, M20 0.97, peak‖T‖5-30 +0.07 dB (EVIDENCE §3.1) | 0 fails, 13 Hz 1.9× (M-R1-3, R4 watch) | = R1-P |
| GATE 2 **curve-hold op-points** | **0 fails on every credible member** (EVIDENCE §3.1; ms_free report-only + stop band) | 0 fails credible | = R1-P |
| r71b tracking 8-15 / 15-22 / >22 | **0.987 / 0.981 / 0.997** (EVIDENCE §3.2) | ≈ R1-P | = R1-P |
| the pol = −1 dependence | yes (fresh D); R1 INVERTED catches it drive 1 | **none** (held D carries pol) | yes |
| H-cam (camera relay close) | procedure (camera-LKAS-off) + ruling §6 | procedure + ruling | **fail-safe in firmware** (fork sends 6803==2) |

**R1-P and R1-F both pass every decidable goal time criterion in every band ≥ 8 m/s AND the R2-box GATE 2 AND the
curve-hold operating-point GATE 2** — the last of which is what refuted C3. The firmware camera interlock is offered as
`R1-P-cam` and **recommended for first flight if the operator accepts the fork-config requirement** (§6, H-cam).

### 0.2 Headline numbers (EVIDENCE; the scorer/model behind each is validated against the common scorers)

| metric | R1-P | C3-P (ref) | P2 (ref) | source |
|---|---|---|---|---|
| **curve-hold op-point GATE-2 fails, credible members** | **0** | **many** (refuted) | — | `exp1c_bars.py` |
| R2-box (θ=0) GATE-2 fails (PID + PD) | **0** | 0 | 690 | `exp2b_ki18.py` |
| r71b real-path tracking 8-15 / 15-22 / >22 | **0.987 / 0.981 / 0.997** | 0.981 / 0.991 / 1.002 | 0.892 / 0.856 / 1.000 | `exp4c` |
| turn-hold min a 1.5 / 2.0 / 2.5 (≥ 8 m/s) | **0.990 / 0.994 / 0.994** | 0.989 / 0.994 / 0.997 | 0.85 / 0.78 / 0.74 | `exp4a` |
| release lurch, straight nudge 5° (worst ≥ 8) | **3.8°** | 6.8° | 13.8° | `exp3` |
| release lurch, outward 2·Aₕ 3 s drag (worst ≥ 8, b_lo×J_hi) | **15.6°** (best of three; M-R1-1) | 20.0° | 18.9° | `exp3` |
| held-turn reversal overshoot (fraction of A) | **0.00** | 0.02–0.20 | −0.07 to −0.22 | `exp3` |
| M20 (× V295) | 0.97 | 0.96 | 0.68 | `exp2b` |
| Re(T/ω) 13 Hz, κ 0.866, ages 1-10 / 0-9 (× V295) | **0.93× / 1.33×** | 0.93× / 1.33× | — | `exp6` |

### 0.3 The rulings this revision makes (each with its reason)

1. **PRIMARY Ki = 40 (was 56).** The highest Ki with a comfortable curve-hold GATE-2 margin (single-corner-native 47.6°,
   aged+combined 32.8°; Ki 44 is only 45.1° / 31.4°, and Ki 48 FAILS — EVIDENCE §3.1). Ki 40 keeps r71b real-path tracking
   ≥ 0.981 in every band and turn-hold ≥ 0.99 (EVIDENCE §3.2). **Ki 44** is specified as a tracking-leaning variant if the
   operator reports soft highway tracking.
2. **ms_free is a REPORT-ONLY member, not gated.** Its J ≈ 2 at 10-15 m/s **exceeds the identified J ≤ 1.3** (the held-out
   r71b ident; the round-1 refuter itself calls ms_free "disfavoured"). Its 0.5 Hz curve-hold ring is covered by the
   widened stop band **R3\*** (§5, F2 fix). Every CREDIBLE member (through J1.3) clears the curve-hold GATE 2 at Ki 40.
3. **The bound references the SETPOINT, not the measured angle.** This is byte-neutral (a different `ld.h` displacement +
   shift-by-2-less) and fixes N1 (outward-hold / nudge windup) and N5 (reversal overshoot) at the ROOT: the integral is
   bounded by the demand, so a hand that drags the wheel away from the setpoint no longer winds I to the hand's angle.
4. **H-cam: the firmware interlock (`R1-P-cam`) is specified and recommended.** `gp-0x6803 == 2` provably excludes the stock
   camera (camera byte-2 field 3:2 = 0; EVIDENCE, trace 2026-09-30 §5). For the lighter R1-P/R1-F, the explicit ruling is
   that camera-LKAS-off (the standing practice on **every flown build V282→V295**) is acceptable for this hazard class.

---

## 1. Every byte (R1-P PRIMARY)

### 1.1 In-place code edits — rev2-A P2's set, UNCHANGED (each already decoded by Ghidra dry-run; re-asserted here)

| id | addr | V295 → bytes | instruction | loop term |
|---|---|---|---|---|
| E1 | `0x28F4C` | `24 3f aa 95`→`24 3f 00 96` | `ld.h -0x6a00[gp],r7` | x := θ |
| E2 | `0x28FA4` | `89 d1`→`c9 d1` | `subr r9,r26`→`add r9,r26` | r26 = 8θ[n]+8θ[n−1] |
| B2 | `0x29A50` | `e2 47 00 00`→`e0 df 34 43` | `setfe r8`→`cmovne r0,r27,r8` | r8 := (req==1)?bVar2:0 |
| A2 | `0x29A56` | `da 05`→`b2 05` | `bne`→`be` | PID runs iff ramp≠0 ∧ r8≠0 |
| E4 | `0x29D6A` | `08 80 ed 80`→`24 87 52 96` | → `ld.h -0x69ae[gp],r16` | sp := gp-0x69ae |
| HOOK | `0x29D76` | `c2 82 ba 81`→`89 37 8a ae` | → `jarl 0xC4C00,r6` | the hook |
| OPH | `0x29EE0` | `10 40 bb 41`→`1a 40 00 00` | → `mov r26,r8 ; nop` | D operand = r26 (fresh op) |
| V1 | `0x1310D` | `30`→`41` | F181 `…A160`→`…A16A` | the fork interlock string |

**No in-place edit changed vs C3-P.** The three rev2A edits are **all inside the cave** (plus one cal: Ki).

### 1.2 The cave (`0xC4C00`, 226 B = 184 code + 42 table) — the THREE rev2A changes, Ghidra-decodable, H1-verified

The cave is C3-P's cave with exactly three changes (full listing in `rev2a_asm.py` output; byte-exact H1 in `rev2a_h1.py`):

```
0xC4C00  c2 82  shl 2,r16            4·sp
0xC4C02  ba 81  sub r26,r16          E = 4·sp − r26 = 16(θ_sp − θ)
0xC4C04  24 d7 42 95  ld.h -0x6abe[gp],r26   op = fresh 1 kHz motor-rate            [D OPERAND]
0xC4C08  1a 46 c8 32  addi 13000,r26,r8      Honda's validity form (FUN_0003f776)
0xC4C0C  20 6e 90 65  movea 26000,r0,r13
0xC4C10  ed 41        cmp r13,r8
0xC4C12  e0 d7 36 d3  cmovh r0,r26,r26       op invalid → op := 0                   [D GUARD]
0xC4C16  e0 87 36 83  cmovh r0,r16,r16       >>> F3 (+4 B): op invalid → E := 0 → P=0, I frozen, D=0 (FAIL-SAFE) <<<
0xC4C1A  … the G(v) walk (table @0xC4CB8, the RAISED-DIP rows) …                    [N2]
0xC4C56  e8 87 20 02  mul r8,r16,r0          E·G
0xC4C5A  a8 82        sar 8,r16              E' = (E·G)>>8                          [SPEED GAIN on P and I]
0xC4C5C  e4 47 99 b0  ld.hu -0x4f68[gp],r8   |driver torque|                        [1 HARD FREEZE |tq|>512]
          …
0xC4C68  24 4f 52 96  ld.h -0x69ae[gp],r9    >>> N1/N5: bound on the SETPOINT gp-0x69ae (was -0x6a00, the angle) <<<
0xC4C6C  …  |sp|
0xC4C7E  c2 4a        shl 2,r9               >>> N1/N5: |sp|<<2 (was |θ|<<4) — byte-neutral, same ~26 T/deg <<<
0xC4C82  c4 4a        shl 4,r9               >>> N1/N5: |sp|<<4 (was |θ|<<6) <<<
0xC4C84  09 4e e2 04  addi 1250,r9,r9        + B = 1250 S : the bound = |θ_sp|·slope + B
          … low-speed cap (min with 4096 below 6 m/s) …
0xC4C9A  24 6f 31 92  ld.w -0x6dd0[gp],r13   I8 (READ only) ; sar 10 → I>>7
          … t = sgn(E')·(I>>7) ; cmp bound ; bge FRZ ; ramp test ; FRZ / DONE …
TBL @0xC4CB8 (raised-dip rows, X u16 / G u16 / S s16 Q12):
    714  1178  1041 | 1843  1465 −6868 | 2304  692  −1748 | 2707  520  1694 |   >>> only (G,S,S) at the 2707 knot moved
    4032 1068  2118 | 6198  2188     0 | ffff  2188     0
```

- **N2 (G < 512):** G@`X=2707` 463 → **520**; segment slopes `S(2304)` −2328→−1748 and `S(2707)` 1870→1694 recomputed so the
  piece-wise-linear curve still hits every knot. **min G over 0–12000 counts: 462 → 520** (EVIDENCE `rev2a_asm.py`). Honda's
  integer I quantum `e5 = ((E·G)>>8)>>5` is now symmetric (±0.1° → ±1) at every speed. **0 code bytes; 6 table-data bytes.**
- **N1/N5 (bound windup):** `ld.h -0x6a00` → `ld.h -0x69ae`, `shl 6/4` → `shl 4/2`. The bound = |θ_sp|·slope + B. **Byte-neutral.**
- **F3 (rate-invalid):** one `cmovh r0,r16,r16` on the SAME carry as the op-validity `cmovh` zeroes E. **+4 B.**

**EVIDENCE (`rev2a_h1.py`):** the assembled R1-P bytes EXECUTED by `e2_asm`'s V850E2 interpreter (CONTROL-B equal to
`ds_asm`) match the rev2A arithmetic reference (θ_sp-bound + F3 E-zero) on **0 / 40000** edge-heavy inputs (the 0x7FFF /
±13000 validity edges, |tq| at 512±1, the bound edges, ramp states, table knots). The `cmovh r0,r16,r16` (`e0 87 36 83`)
decodes field-for-field as cmov cond-0xB (cmovh) reg3=16 reg1=0 — the same form as C3-P's verified `cmovh r0,r26,r26`.
The `ld.h -0x69ae` displacement is the one E4 already uses (`24 87 52 96`), reg2=9 here. BELIEF until Ghidra decodes a BUILT
image (builder H5).

### 1.3 Calibration cells — C3-P's 24 bytes, with Ki = 40 (the ONE cal change vs C3-P)

| cell | addr | V295 | **rev2A** | note |
|---|---|---|---|---|
| a | `0xC63E8` | 1011 | 0 | fb pole → pure 2-sample sum |
| b | `0xC63EA` | 1050 | 8192 | s_new = 8θ |
| C | `0xC62E6` | 1024 | 65535 | r26 clamp |
| DB | `0xC62E4` | 4 | 0 | I deadband |
| **Ki** | `0xC63E6` | 0 | **40** | **F1: PI corner 0.62 → 0.44 Hz; curve-hold ring removed (was 56 in C3-P)** |
| ICL | `0xC61BA` | 10240 | 8192 | I clamp, below V295's own 10240 |
| DCL | `0xC61B6` | 0 | 10240 | D clamp |
| Kp Y | `0xE5384` | 960 | 112 | Kp flat |
| Kd Y | `0xE5126` | 0 | 48 | D = (48·op)>>3 (R1-F: 24) |

The raised dip is **cave-table data** (§1.2), not a cal-page cell, so the cal set is byte-identical to C3-P's except Ki.

---

## 2. Method integrity — every re-score is on a model validated against the common scorers

The task requires re-scoring on the common scorers (`panel2/score_freq.py`, `score_time.py`) and/or the refuters' own
scripts. This revision re-scores on the refuters' own models, which are the validated mirrors:

- **Time**: `rev2a_lane.Rev2ALane` is built on `c3nl_sim`, which the nonlinear refuter proved **bit-exact to the common time
  scorer's `CandLane` / `run()`** (its K3: 40000 ticks, K4: 18 batches, max|Δθ|=0, |ΔT|≤1). A control in `rev2a_lane.py`
  (Ki 56 / θ-ref / no-F3 / original table) reproduces `c3nl_sim.Lane` **tick-for-tick, 0 / 20000** — so the three rev2A
  edits are isolated and correct.
- **Frequency / stability**: `c3r1_model` (the round-1 stability refuter's independent model) reproduces every published
  GATE-2 anchor and agrees with the round-2 refuter's `c2r2_model` to 0.1°. The curve-hold operating-point test is the
  refuter's own `c3r1_kop` (k·sech²(θ_op/sat)).
- **Bytes**: `rev2a_asm` uses `e2_asm`'s encoder (CONTROL-A: reproduces `c2_cave_P2.hex`); `rev2a_h1` uses `e2_asm`'s
  interpreter (CONTROL-B: equal to `ds_asm`).

The **builder** still runs the actual `panel2/score_freq.py` + `score_time.py` on the BUILT table/cals (H2/H3) and the
mandatory adversarial pass — those are build-time steps, not waived.

---

## 3. The re-scores that resolve the HIGH / refuting findings

### 3.1 F1 (stability, refuting) — curve-hold GATE 2 — RESOLVED by Ki 40, re-scored on `c3r1_kop`

The refuter's point: at a curve hold the plant stiffness is k·sech²(θ_op/sat), and the LTI PID loop there (which the panel
scorers miss, because they linearise at θ=0) falls below the GATE-2 bars. Re-scoring the refuter's own operating-point
model (`exp1c_bars.py`, bars: single-corner-native ≥ 45°, aged-single + combined ≥ 30°; a ∈ {1.0,1.5,2.0,2.5}; v ≥ 8;
frames nom + FA.83/1.155 + FB.83/1.155; e 0/10):

| Ki | credible single-native min | credible aged+combined min | verdict | ms_free (report-only) |
|---|---|---|---|---|
| **56 (C3-P)** | 39.0 (b_hi) | 23.7 (b_q×J1.0) | **FAIL** (refuted) | 0.0 |
| 48 | 42.8 | 29.4 | FAIL | 0.6 |
| 44 | 45.1 | 31.4 | pass (thin) | 1.9 |
| **40 (PRIMARY)** | **47.6 (b_hi)** | **32.8 (b_lo×J_hi)** | **PASS** | 6.0 |
| 36 | 50.1 | 34.2 | pass | 10.3 |

**EVIDENCE:** at Ki 40 every CREDIBLE member (through J1.3) clears both bars at every curve-hold operating point. The
mechanism: Ki 56 puts the PI corner at 0.62 Hz, right at the curve-hold crossover (0.45–0.65 Hz in the G dip); Ki 40 moves
it to 0.44 Hz, below crossover, restoring phase margin. **Turn-hold is unchanged by Ki** (steady-state is set by ICL + the
bound; §3.2). And the **R2-box (θ=0) GATE 2 stays clean** at Ki 40 + raised dip (`exp2b_ki18.py` pattern, re-run at Ki 40):
**0 single fails, 0 combined fails, min PM 46.1°, M20 0.970, peak‖T‖5-30 +0.07 dB** — EVIDENCE.

**ms_free** (J ≈ 2, exceeds the identified J ≤ 1.3) is ruled **report-only** (ruling §0.3). Its curve-hold ring (0.5 Hz,
ζ ≈ 0.15) is covered by **R3\*** widened to 0.25–5.5 Hz (§5). At Ki 32 even ms_free's combined corners clear 30° if the
orchestrator rules ms_free credible — offered as a variant.

### 3.2 Tracking — the goal's PRIMARY metric — RESOLVED (Ki 40 does NOT hurt real-path tracking)

Lowering Ki could hurt low-frequency tracking. Re-scored (`exp4c_r71b_agg.py`, the design's own r71b method: OLS over
concatenated real runs per band, worst member; `exp4a_fast.py` for turn-hold / S-bend / small-signal):

| metric | R1-P (Ki 40) | R1-P44 | C3-P (Ki 56) | P2 | goal |
|---|---|---|---|---|---|
| **r71b tracking 8-15 m/s** | **0.987** | 0.987 | 0.981 | 0.892 | 0.95–1.05 |
| **r71b tracking 15-22 m/s** | **0.981** | 0.985 | 0.991 | 0.856 | 0.95–1.05 |
| **r71b tracking >22 m/s** | **0.997** | 0.999 | 1.002 | 1.000 | 0.95–1.05 |
| turn-hold min a 1.5 / 2.0 / 2.5 | 0.990 / 0.994 / 0.994 | 0.989/0.993/0.996 | 0.989/0.994/0.997 | 0.85/0.78/0.74 | ≥ 0.90 |
| S-bend 0.1 Hz slope (worst, 15-17.5) | 0.872 | 0.895 | 0.940 | 0.847 | report (M-R1-2) |

**EVIDENCE:** R1-P meets the goal's tracking (0.95–1.05) in **every band** on the real r71b paths — and BEATS C3-P at
8-15 m/s. The only tracking regression is the synthetic 0.1 Hz S-bend worst-member slope (0.872 vs C3-P 0.940, ≈ P2),
declared **M-R1-2** (the same report-member class as C3's M-C3-2; the real paths pass). Ki 44 recovers it to 0.895 at a
thinner F1 margin.

### 3.3 N1 / N5 (nonlinear, HIGH) — the integral bound — RESOLVED by θ_sp-referencing, re-scored on `c3nl_lens`

Re-scored (`exp3_time.py`, the nonlinear refuter's own scenario builders; members nominal/bc/F_hi/b_lo×J_hi; 8–26.9 m/s):

| scenario (worst ≥ 8 m/s) | **R1-P** | C3-P | P2 | finding |
|---|---|---|---|---|
| **straight nudge 5°, release** | **1.1 – 3.8°** | 3.1 – 6.8° | 3.2 – 13.8° | N1 (was 10.6° for C3) — FIXED |
| inward partial drag 0.5·Aₕ | 1.2 – 4.5° | 1.2 – 3.1° | 3.3 – 10.6° | bounded, < 8° |
| **outward 2·Aₕ drag 3 s, release** | **7.0 – 15.6°** | 8.1 – 20.0° | 7.3 – 18.9° | N1 extreme — **best of three** (M-R1-1) |
| **held-turn reversal overshoot** | **0.00** | 0.02 – 0.20 | −0.07 to −0.22 | N5 — FIXED |

**EVIDENCE:** the θ_sp-referenced bound removes the reversal overshoot entirely (N5) and cuts the outward / nudge lurch
sharply (N1). For the REALISTIC light-hand cases (nudge, partial drag) R1-P is well under the 8° bar. The one residual >8°
is the **aggressive 2·Aₕ-outward-drag-and-release at ≤ 12.5 m/s on b_lo×J_hi (15.6°)** — declared **M-R1-1**; R1-P is the
**lowest of all three** there, because when the hand drags the wheel past the setpoint the integral is now bounded by the
DEMAND, not by the hand's angle. Its residual is the inherent large-angle P-correction at low speed, covered by R9.

### 3.4 F3 (stability, MEDIUM) — rate-invalid fail-safe — RESOLVED by construction (+4 B)

The refuter: C3's "D := 0 on rate-invalid while P+I keep running" is linearly unstable on 62 (C3-P) / 32 (C3-F) gated
points. The rev2A `cmovh r0,r16,r16` zeroes **E** on the same carry → E' = 0 → **P = 0, e5 = 0 (I frozen), op = 0 (D = 0)**.
The lane then has **no angle-feedback path** — it is OPEN-LOOP under the fault, so it **cannot run the unstable PI-only
loop**; it holds the last valid assist (bounded by ICL) through the output lag and releases via A2.

**EVIDENCE (`exp5_fault.py`, rate-invalid from t = 2 s at 12 m/s):** R1-P holds a constant (rms(3-4s)/rms(1-2s) = **1.00**,
no growth) while C3-P keeps an active loop (ratio 0.83–0.91, decaying here but unstable on the refuter's gated set). The
`rev2a_h1.py` H1 proves the bytes execute this (0/40000, incl. every validity edge). A leaking-fault variant (route to the
cam-style `I×0.125/tick`, gone in ≈ 3 ms) is available if a decaying fault state is preferred over hold-last.

### 3.5 F4 (stability, MEDIUM) — Re(T/ω) at the physical κ — RESOLVED by honest restatement

Re-scored (`exp6_retw.py`, the refuter's `c3r1_model.retw`; > 0 damps, < 0 anti-damps; worst over 1-35 m/s):

| Hz | 5 | 7 | 10 | **13** | 15 | 17 | **20** | 25 |
|---|---|---|---|---|---|---|---|---|
| V295 (κ 0.866, ages 1-10) | +2.13 | +1.08 | +0.08 | −0.41 | −0.57 | −0.67 | −0.71 | −0.66 |
| **R1-P (κ 0.866, ages 1-10)** | −0.27 | −0.29 | −0.35 | **−0.38 (0.93×)** | −0.39 | −0.39 | **−0.39 (0.55×)** | −0.37 |
| **R1-P (κ 0.866, ages 0-9)** | −0.24 | −0.28 | −0.35 | **−0.39 (1.33×)** | −0.40 | −0.40 | **−0.40 (0.64×)** | −0.39 |
| R1-P (κ 1.0, ages 1-10) | −0.01 | −0.15 | −0.30 | −0.38 (0.80×) | −0.40 | −0.42 | −0.43 (0.52×) | −0.42 |

**EVIDENCE:** C3's "13 Hz anti-damping 0.79× V295" holds ONLY at κ = 1, ages 1-10. At the **physical κ 0.866** it is **0.93×
(ages 1-10)** and **1.33× (ages 0-9)** — i.e. for fresh samples the 13 Hz anti-damping **exceeds V295**. This is declared
**M-R1-3** with the **R4 10-17 Hz watch**. The **20 Hz is 0.52–0.64× V295 in every frame** — the goal's "20 Hz gain ≤ V295"
is met with margin. (R1's Ki / dip barely move Re(T/ω); it is the Kd-48 fresh-D's property, same as C3-P.)

### 3.6 bytes-failsafe F1 (refuting, lens criterion) — H-cam — RESOLVED, see §6.

---

## 4. The loop, integer-exact Python (R1-P; each line is a byte or cal above)

```python
def r1p_tick(st, theta, sp69ae, abe, v6a5e, tq4f68, ramp, req, bvar2):
    if not (ramp != 0 and req == 1 and bvar2):                 # A2 + B2
        st.I8 = 0; st.Eprev = 0x7FFFFFFF; return lag_gate(st, 0)
    s_new = (8192 * theta) >> 10
    r26 = clamp(st.s_old + s_new, -65535, 65535); st.s_old = s_new
    E = s32((sp69ae << 2) - r26)                               # cave 0xC4C00/02: 16(theta_sp - theta)
    valid = ((abe + 13000) & 0xFFFFFFFF) <= 26000              # 0xC4C04..12
    op = abe if valid else 0                                   # 0xC4C12 cmovh r0,r26,r26
    if not valid: E = 0                                        # 0xC4C16 cmovh r0,r16,r16  [F3]
    G = walk(TBL_RAISED, v6a5e)                                # 0xC4C1A..54  [N2: min G 520]
    Ep = s32(E * G) >> 8
    frozen = (tq4f68 > 512)                                    # 0xC4C5C..
    if not frozen:
        sh = 2 if (v6a5e <= 2880) else 4                       # byte-neutral vs 4/6 on the 4x-scaled sp cell
        bound = (abs(s16(sp69ae)) << sh) + 1250                # 0xC4C68..84  [N1/N5: bound on the SETPOINT]
        if v6a5e <= 1382: bound = min(bound, 4096)
        t = (st.I8 >> 10) if Ep >= 0 else -(st.I8 >> 10)
        if t >= bound or (ramp & 0x8000) == 0: frozen = True
    e5 = 0 if frozen else (Ep >> 5)
    I = clamp((st.I8 >> 3) + ((e5 * 40) >> 3), -(8192<<7), 8192<<7)   # Ki 40, ICL 8192
    P = clamp((Ep * 112) >> 8, -15360, 15360)
    D = clamp((48 * op) >> 3, -10240, 10240)
    S = (I >> 7) + P + D ; st.I8 = I << 3
    return lag_gate(st, fade_and_clamp(S))
```

---

## 5. Pre-declared misses, each quantified with its covering stop band

**Stop bands (rev2-A's, with the F2 fix):**
- **R3\*** (F2 fix): a **0.25**–5.5 Hz oscillation (was 0.5) that grows, or ≥ 4 cycles ζ < 0.10 → REVERT. Lowered to 0.25 Hz
  so it covers both the fork outer-loop rings (0.31–0.47 Hz; stability F2) **and** the ms_free curve-hold ring (0.5 Hz).
- **R4** 5–30 Hz line absent on V282/V295 → REVERT (R1-F / M-R1-3: watch 10–17 Hz). **R5** ring > 0.5 %, F7 > 0. **R9** words.
- **τ_o ≥ 1 s is a checked FLIGHT PREREQUISITE** (F2 fix): the fork's outer-loop time constant is confirmed from its config,
  not assumed; at τ_o ≥ 1 s the outer loop has PM ≥ 56°, GM ≥ 8 dB (refuter F2, EVIDENCE).

| # | finding | criterion | predicted (EVIDENCE) | stop band / revert |
|---|---|---|---|---|
| M-R1-1 | N1 outward-drag lurch | aggressive 2·Aₕ-outward 3 s, ≤ 12.5 m/s, b_lo×J_hi | 15.6° (best of three; realistic nudge/drag < 8°) | R9; release overshoot > P2 + 2° |
| M-R1-2 | N4 S-bend tracking | 0.1 Hz S-bend, gated members, 15-17.5 m/s | 0.872 (real r71b paths pass 0.981) | on-car tracking < 0.95 in-band = FAILED |
| M-R1-3 | F4/N5-class 13 Hz anti-damping (R1-F; R1-P fresh ages) | 10-17 Hz | 13 Hz **1.33× V295** (ages 0-9, κ 0.866); R1-F 1.9× | **R4 with a 10-17 Hz watch** |
| M-R1-4 | F1 ms_free curve-hold ring | report member (J ≈ 2 > ident 1.3) | 0.5 Hz ring ζ ≈ 0.15 | **R3\*** (0.25-5.5 Hz) |
| M-R1-5 | N2 small-signal in the dip | ±0.5° 0.2 Hz, 11-12.5 m/s | in-phase gain ≈ 0 (bandwidth-limited; 0.1 Hz improved by the raised dip) | R9 (micro-ratcheting on small corrections) |
| M-R1-6 | N3 dwell-then-jump | small corrections 8-10 m/s and > 22 m/s | counted, not simulable vs V282 | R9; dwell rate vs r6c |
| M-R1-7 | N6 road load at θ ≈ 0 | crown / crosswind, 8-12.5 m/s | bound caps I at ≈ 200 T + slope·\|θ_sp\|; P carries excess (θ_sp≈0 → small bound) | hands-off error > 1° on a straight ≥ 8 m/s → REVERT |
| M-R1-8 | N7 accel through a curve | transient (≈ 2 s) while k(v) ramps | turn-hold sags ≈ 0.86 for ≈ 2 s (PI lag), recovers | — (transient; not the 60 s FAILED definition) |
| M-R1-9 | N8 aged lurch | +h10 holds | aged lurch ≤ native + ≈ 0.8° (R1-P lower than C3-P at every age) | included in M-R1-1 |
| M-R1-10 | F5 two-mass modal damping | 13 Hz stress | below V295 on a fraction of points (max Δζ 0.034) | **R4** (no change needed) |
| M-R1-11 | F6 limit cycles | J_hi @1 m/s / friction holds | ±0.1° (< wire LSB) / 0.1-0.2° hunt | nonlinear hunt gate; < R3\* band |
| inherited | 510 ms timeout / H-tmo | all | last θ_sp held 0.51 s → sentinel → A2; mid-motion ≤ 2.4° | stock parity (§6 F3) |

---

## 6. Hazards and fail-safe (the bytes-failsafe lens' findings)

| # | finding | rev2A resolution | fails safe? |
|---|---|---|---|
| **F1 H-cam** (REFUTING) | stock camera 0xE4 on a relay close read as an angle setpoint | **`R1-P-cam`: a firmware gate on `gp-0x6803==2` (r25, already live at the hook) makes the lane inert when 6803≠2.** The stock camera sends byte-2 field 3:2 = 0 → 6803 = 0 → excluded (EVIDENCE, trace 2026-09-30 §5). For the lighter R1-P/R1-F: explicit ruling that camera-LKAS-off (standing practice on every flown build) is acceptable for this hazard class. | **R1-P-cam: yes, in firmware.** R1-P/R1-F: by procedure + ruling |
| F2 zero-emitting / wrong-payload fork | a fork (or stock openpilot) sending 0 or torque with req 1 → read as θ_sp | declared: V1 (`…A16A`) + the fork's angle-loop key gate loading; a 0 steers toward centre with full P (bounded by clamps), caught by R6 (\|θ−θ_sp\| > 10° hands-off) and the driver | bounded; declared |
| F3 510 ms timeout | last θ_sp held 510 ms → sentinel | **stock-parity ruling**: stock already holds the last command 510 ms; mid-motion ≤ 2.4° (M-C3-12). Accepted as stock parity | holds last VALID command (stock parity) |
| F4 pol = −1 (R1-P fresh D) | the fresh-D sign rests on `gp-0x6752 = −1` (boot-static) | **R1-F is pol-free** (held D carries pol like θ). For R1-P/R1-P-cam: re-prove pol on this car (UDS/tracer) is a FLIGHT PREREQUISITE; R1 INVERTED catches it drive 1; image is car-specific | yes on this car; R1-F removes it |
| F5 byte-level design-time | nothing decoded from a BUILT image | the cave is H1-verified on the assembled bytes (`rev2a_h1.py`, 0/40000) and dry-run decodable; builder's **H5–H10 + the mandatory adversarial pass on the BUILT image** remain required | build-time |

**The firmware camera interlock, `R1-P-cam` (RECOMMENDED for first flight if the operator accepts the fork-config
requirement):** +20 cave bytes (the `e2_asm` `cam` block: `cmp r0,r25 ; be CAM` + the inert handler) → cave 246 B. Because
requiring `gp-0x6803 == 2` also selects Honda's harder post-PID fade arm `0xCBAE4` (×1.8–2.1 against a mid-range hand;
trace §5.2) **and** the faster 0.10 s ramp-in (a benefit — less engage droop), the variant **neutralizes the fade cost** by
setting the fade record `0xE54FC` = `0xE564C` (the current V295 arm; 24 cal bytes), so the override feel is unchanged. **The
peak authority against a firm hand is unchanged either way** — the |tq|>512 freeze + the setpoint-referenced bound + ICL 8192
(below V295's 10240 clamp) dominate; only the mid-range fade SHAPE would change, and the neutralization removes even that.

**FLIGHT PREREQUISITES:** camera-LKAS-off (R1-P/R1-F) OR fork sends `6803==2` every frame incl. request-drop (R1-P-cam);
re-measure the camera's 0xE4 byte 2 field 3:2 on bus 2 (trace open item 4); V1 `…A16A` + fork angle-loop key; revert `.rwd`s
re-headered; τ_o ≥ 1 s confirmed in the fork config; pol = −1 re-proven (R1-P/R1-P-cam only); image is car-specific.

---

## 7. The instrument — one short drive (no new telemetry bit)

Identified within an episode from signals already on the wire: 0xE4 (θ_sp = −raw/10 and request), 0x14A (θ 100 Hz), 0x18F
(rate, driver torque, STEER_STATUS), the CAN 427 tap (T = gp-0x6b38, +sign(cmd)), F181. Same regression as C3 §8, with:
`c_I / c_P` now **≈ 2.8 s⁻¹** (Ki 40, was 3.9 for Ki 56) — the **PI-corner check that confirms the F1 fix is live**; the
light-hold I-flatness check (bound on the SETPOINT) is confirmed by nudging the wheel **outward** (away from θ_sp) and
checking the I component stays flat (N1 fix). **REVERT** on R1–R9 (§5). **The sentence a null licenses:** *"If c_I/c_P ≈ 3.9
(not ≈ 2.8), the Ki-40 F1 fix did not ship; if outward-nudge winds the I toward the hand's angle, the setpoint-bound did
not ship; revert either way."*

---

## 8. How rev2A differs from C3 (the arc)

rev2A is C3 with four surgical, individually-re-scored fixes, no new class: **F1** moved the PI corner below the curve-hold
crossover by a single cal (Ki 56→40), the thing that refuted C3; **N1/N5** re-pointed the integral bound at the demand
(byte-neutral); **N2** raised the G dip knot so Honda's I quantum is symmetric (table data); **F3** made the rate-invalid
state open-loop (+4 B). The cave grew **+4 bytes** (226 vs 222). The firmware camera interlock is a specified +20 B option.
It is still the first angle loop (vs V294/V295 cal-space / torque mode / unfiltered rate / fork-rewrite — the four the goal
rules out), a gated cave (GATE 1 0 RAM, GATE 2 clean at θ=0 AND at the curve-hold operating points, a byte-exact mirror the
H1 executes, the wire instrument on every term, an adversarial pass reachable).

## 9. What a FAIL looks like (any one → do not flash)
H1 bytes ≠ rev2A arithmetic on any input, or any register outside {r6,r8,r9,r13,r16,r26} changes, or any RAM written · any
R2-box OR curve-hold-op-point GATE-2 fail outside the declared ms_free report set · r71b tracking outside 0.95-1.05 in any
band ≥ 8 · a new 5-30 Hz line · the BUILT-image H5-H10 (hook/exit decode, A2/B2 dominance, CRC walk, F181, pol) · the
mandatory adversarial pass (≥ 3 independent agents, "do not flash" reachable) finds a decision-bearing defect.

## 10. What this page did not do
No image built (H5 is build-time). The common `score_freq`/`score_time` full-grid run on the BUILT table is the builder's
H2/H3 (the refuter models used here are validated bit-exact to them). ms_free report-only is a ruling. κ, dwell-vs-V282 and
the hard-turn-vs-V282 counts are not decidable without V282. The Artifact (signal-flow + LERPs before/after) is a build-time
collateral.
