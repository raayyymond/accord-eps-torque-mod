# DESIGN C2 rev 2, reviser A (2026-10-01): PRIMARY P2 (fresh-rate D, 6-knot G), FALLBACK F2 (held-rate D, 6-knot G)

**Status: DESIGN ONLY.** Nothing was built, flashed or sent, and the fork was not touched. No image or `.rwd` file was
written. The patched images in this study exist only in memory inside `r2a_bytes.py`. Ghidra was used read-only:
`decompile_function`, `get_xrefs_to`, `get_function_callers` and `disassemble_bytes` with `dry_run: true`. These ran on
stock `code.bin` and on the open V294 program, which is code-identical to V295 except cal `0xC63EA` and its CRC. Nothing
was saved.

**Author:** reviser A, a subagent (Opus) working for the orchestrator `main`. Reviser B works independently; I have not
seen its work.

**Brief:** C2 round 1 was refuted on all three lenses (stability, nonlinear, bytes-and-fail-safe) for one reason: **the C2
synthesis halted and no design existed.** This page resolves every finding of those three refutations. A finding is
resolved either by a design change, re-scored with the common scorers and the refuters' own scripts, or by a quantified
miss declared before any build, with a stop band that covers its ring. The page delivers a PRIMARY and a FALLBACK
implementation.

- **The user's instruction:** *"Make sure that multiple potential designs and implementations per design are evaluated
  as part of this workflow."* This page scores **three designs**:
  - **P**, fresh-rate D;
  - **F**, held-rate D;
  - **Z**, zero cave.
- Designs P and F carry **seven implementations** between them:
  - P1, P2, P3, P4, P5;
  - F1, F2.
- Every other expressible panel candidate also runs through the **common time scorer**:
  - A1+B2, A2+B2;
  - B1, B2+guard, B3;
  - CGF-1+guard;
  - D1a, D1b, D1c, D2b, D2c, D3a, D3b.

**Base image:** V295, `_v295_V295-V294BASE-ACCELTRIM.B1050-…TORQUE.TAP_plain_image.bin`, sha256 `5c044d65…52ed`. Every
script asserts it. Every pre-edit byte is asserted against it before it is replaced.

**Scripts** (all in `analysis-2020accord/studies/angle_loop/c2/rev2A/`, fixed seeds, run with `python <script>`; caches
go to `_scratch/angle_loop/c2rev2A/`, which is gitignored):

| script | what it does | output |
|---|---|---|
| `r2a_common.py` | the ONE source of truth: designs, implementations, structures, tables, the rejected variants | — |
| `r2a_env.py` | the speed-gain envelope for the Kd 41 / 48 structures + a reproducibility control on Kd 34 | `r2a_env_control.txt` |
| `r2a_fit.py` | the integer G(v) tables (5 / 6 / 7 knots), with a control that the 7-knot fit reproduces the panel tables | `r2a_fit_out.txt` |
| `r2a_freq.py` | GATE 2, sections A–F (detail in §3) | `r2a_freq_{A,B_all,C,D,E,F}.txt` |
| `r2a_refute_rerun.py` | **the stability refuter's own independent model and attack lists**, re-run on P1/P2/F1/F2 with its anchors reproduced first | `r2a_refute_rerun_out.txt` |
| `score_time.py` | **THE COMMON TIME SCORER** (detail in §4) | `score_time_selftest.txt`, `score_time_out.md` |
| `r2a_time_report.py` | the time tables and the pre-registered bars, generated from the caches | `score_time_out.md` |
| `r2a_bytes.py` | every byte: assemble, compare with the panel hex, branch fields from the bytes, register/memory census, H1 0/60 000, full diff, overflow budget, integrity regions named | `r2a_bytes_out.txt`, `c2_cave_<impl>.hex` |
| `r2a_listing.py` | the cave listing of every implementation | `c2_cave_<impl>.lst` |

`r2a_freq.py` sections:
- **A:** the common scorer on the brief's GATED set and on the report members.
- **B:** the exact periodic model on every member.
- **C:** Re(T/ω) 5–25 Hz at hold ages 0 and 10.
- **D:** the goal's own tracking metric, turn-hold and the hard-turn band.
- **E:** the fork outer loop at τ_o 0.3 / 0.5 / 1 s.
- **F:** two-mass stress at 13–20 Hz.

`score_time.py` scope:
- every panel column plus this reviser's implementations, in ONE batch per (scenario, speed, member);
- 5 members × 12 speeds × 18 scenarios;
- a dense pass at 3–30 m/s every 0.25 m/s.

Every decision-bearing claim is marked **EVIDENCE** (with the method) or **BELIEF**. Code is cited by address or grep
string.

---

## 0. The answer in one page

### 0.1 The C2 round-1 findings and how each is resolved

| refuter | finding (severity) | resolution | evidence |
|---|---|---|---|
| stability | C2 was never produced: no edits, cave, cals, GATE-2 scoring or declared misses (blocking) | **Design written.** PRIMARY P2 and FALLBACK F2: every byte (§1, §2), the cave hex with load address and hook displacement, cals, GATE 2 on the full set (§3), time domain (§4) | this page; `r2a_bytes_out.txt`; `c2_cave_P2.hex` / `c2_cave_F2.hex` |
| stability | no pre-registered stop band or declared miss (blocking) | **§6.** Every miss is quantified with its ring frequency. Stop band **R3\***: 0.5–5.5 Hz at every speed. It covers every sub-bar report-member ring (0.92–1.53 Hz and 3.72–3.81 Hz) and the τ_o < 1 s outer-loop ring. | `r2a_freq_B_all.txt`, `r2a_freq_E.txt` |
| stability | `panel/score_time.py` does not exist (major) | **Written and controlled:** `c2/rev2A/score_time.py`. It is in this reviser's folder because two revisers run in parallel; the orchestrator may promote it. CONTROL 1: == `ds_time.run` bit for bit. CONTROL 2: zero-cave columns == `harness_time.run`. CONTROL 3: P1 == D2a and F1 == B0r configs. | `score_time_selftest.txt` |
| stability | the panel's bytes-risk ranking was relayed, not verified (info) | **Re-scored, not relayed.** P1 (= D2a) and F1 (= B0r) were re-run on `score_freq` and reproduce the panel's numbers exactly: 64.9 / 46.7 / 32.6° and 64.8 / 47.0 / 32.1°, 0 fails. Both were then run through the exact periodic gate on every member and through the refuter's own model. | `r2a_freq_A.txt`, `r2a_freq_B_all.txt`, `r2a_refute_rerun_out.txt` |
| nonlinear | no C2 design (blocking) | as above | — |
| nonlinear | every nonlinear check unverifiable (blocking) | **Run on the exact integer lane** (see the note below this table) | `score_time_out.md` |
| nonlinear | no common time gate for D2a / B0r (high) | **Every expressible panel candidate is scored in the same batch** (16 columns + 2 zero-cave columns) | `score_time_out.md` |
| bytes | no artefact (blocking) | **§1.1–§1.6 and §5:** decode, displacements, liveness at `0x29D76`, GATE 1, int32, guards, timeout, fault, preemption, torque-mode fork, zero-emitting fork, stock camera | `r2a_bytes_out.txt`; my own Ghidra listing of `0x29D60..0x29F80` |
| bytes | "not scored" fields cannot excuse a shortfall (high) | **Every field scored.** Misses are declared in §6 before any build. | — |
| bytes | `score_time` missing (medium) | as above | — |
| bytes | panel candidates not refuted by this lens (info) | P2 has D2a's cave code byte for byte (only the table differs). F2 has **C1 rev 2's cave code** byte for byte (sha `a6f902d5`). Both are re-verified here on bytes. | `r2a_bytes_out.txt` |

**The nonlinear lens, as run** (`score_time.py`, on the exact integer lane):
- **Members:** nominal, bc, F_hi, b_lo×J_hi and nominal+h10 (hold ages 11–20).
- **Speeds:** 3.1, 5, 8, 10, 11.9, 12.5, 15, 17, 19, 22, 26.9 and 30 m/s (the plant knots are included).
- **Scenarios:** stick-slip, dwell-then-jump, dead band, tracking at 0.2 / 0.5 Hz, turn-hold, light-hand (400 / 1000) and
  firm-hand release, co-steer, engage under load, ramp-in, latch, the 0xE4 sentinel, **the 510 ms timeout hold**, request
  drop and the hard turn.
- **Dense pass:** nominal and bc at 3–30 m/s every 0.25 m/s.

### 0.2 The designs and implementations evaluated

Bytes are counted as **written** bytes: changed in-place code, plus the whole cave including its table, plus changed cal
bytes. Every candidate has **RAM 0** and **1 cave** at `0xC4C00`.

| design / impl | what it is | bytes | GATE 2 (brief's set) | goal metric ≥ 8 m/s | worst Re(T/ω) 13 Hz, age 0, × V295 | time bars | verdict |
|---|---|---|---|---|---|---|---|
| **P1** | D2a as the panel fitted it: fresh-rate D, Kd 34, 7 knots | 206 | 0 fails | 0.961 | 0.79 | PASS | dominated by P2 (−6 B, same loop) |
| **P2** | **P1 with the 15.5 m/s knot dropped** (it is collinear: G 1124 vs 1122) | **200** | **0 fails** (score_freq and exact) | **0.961** | **0.79** | **PASS** | **PRIMARY** |
| P5 | P1 with the 15.5 and 17.5 m/s knots dropped | 194 | 0 fails | **0.946 FAIL** (b_q, 17 m/s) | 0.79 | PASS | rejected: misses the goal metric |
| P3 | fresh-rate D Kd 41 (cal only) | — | the envelope collapses to 0 at 12.5–15.25 m/s | — | — | — | rejected (§9) |
| P4 | fresh-rate D Kd 48 (cal only) | — | the envelope collapses to 0 at 1–16.5 m/s | — | — | — | rejected (§9) |
| F1 | B0r as the panel fitted it: held-rate D (C1's E5), Kd 20, 7 knots | 191 | 0 fails | 0.958 | **1.78** | PASS | dominated by F2 |
| **F2** | **F1 with the 15.5 m/s knot dropped** | **185** | **0 fails** | **0.957** | **1.78** | **PASS** | **FALLBACK** |
| Z: A1+B2 | zero cave: Honda's Kp/Kd LERPs re-keyed to speed, flat Ki | 79 | 1 fail (ms_free 44.8°, panel scorer) | — | — | **FAIL**: turn-hold 0.766 | reference: the bytes floor fails the goal |

The rest of the panel, in the same time batch (§4):
- **FAIL the time bars:** B3 (turn-hold 0.44–0.46), D1a (5–30 Hz torque in holds up to 6.65 counts and 40–200 Hz 26.6),
  D1c (6.78) and D2c (2.54 > 2.0).
- **PASS the bars, with the costs recorded in §4:** B1, B2+guard, CGF-1+guard, D1b, D2b, D3a, D3b and A2+B2.
  - D3a/D3b miss the goal's tracking: wire gain at 0.2 Hz 0.60–0.97, at 0.5 Hz 0.10–0.79, which is the D designer's own
    goal-metric fail.
  - A2's Ki cave was never assembled.
  - B1, B2 and CGF-1 carry the frequency-domain fails listed in SCORE-FREQ.

### 0.3 Why P2 is primary and F2 the fallback (rule written before the final scoring)

**The rule.** Take the implementations that pass all of:
- 0 GATE-2 fails on the brief's set (common scorer AND exact periodic);
- 0 sub-bar points in the refuter's own model;
- the goal metric 0.95–1.05 and turn-hold ≥ 0.90 on every member ≥ 8 m/s;
- the time bars on all five members.

Among those, choose **the fewest bytes inside the design whose 5–30 Hz damping stays under V295's at both hold ages.** That
is the model proxy for the goal's *"no new 5–30 Hz line"*. The fallback is the fewest-bytes passing implementation of the
other design.

**P2 against the rule.** EVIDENCE: `r2a_freq_C.txt`, worst over 1–35 m/s.
- At hold age 0, P2's worst Re(T/ω) is **0.79× V295** at 13 Hz and **0.41×** at 20 Hz.
- At hold age 10 it is 0.10–0.22× V295 over 10–20 Hz, and 0.96× at 25 Hz.

**F2 against the rule.** **F2 exceeds V295's anti-damping in the band where the record has its 13–17 Hz line:**
- at hold age 0: **1.78× at 13 Hz, 1.21× at 15 Hz** (27 m/s);
- at hold age 10: **1.25× at 10 Hz**.

F2 is 15 bytes smaller, but it buys those bytes with a quantified risk to a goal criterion. Under Priority 1 above
Priority 2, P2 wins. This matches the panel judge's ranking (D2a 82, B0r 81).

**Why F2 is still the right fallback:**
- **It removes P2's two specific dependencies:**
  - the fresh-rate D sign rests on `pol = gp-0x6752 = −1` (EVIDENCE, §5 H-pol);
  - the fresh D's operand cannot be told apart on the 50 Hz wire in one drive (§7).
- **Its cave code is C1 rev 2's, byte for byte.** That is the most-reviewed cave code in this kit.

### 0.4 Predicted against the goal (nominal unless stated; model and simulation, not a drive)

| goal criterion | P2 | F2 | verdict before any build |
|---|---|---|---|
| dwell-then-jump ≤ V282; low-speed stick-slip gone | Dwell-then-jump events 3–5 per set at 3.1–5 m/s (nominal 4 / 3, bc 5 / 2) and 0 at ≥ 8 (bc: 1 at 11.9). Hold slips 3 per hold at 10–12.5 m/s (the ms_free dip). ±1° stick 42–63 % at 3–5 m/s. | same class (5 / 2 events, 42–63 %) | **PRE-DECLARED MISS (M1, M2)**. V282 cannot be simulated, so "≤ V282" is decided on the car. |
| tracking 0.95–1.05 in every band ≥ 8 m/s (the goal's own metric) | **0.961–1.011** on 12 members | 0.957–1.011 | **predicted PASS**. The margin, 0.011 at 17 m/s on b_q, is inside the metric's ±0.028 control (BELIEF on the r71b spectrum). |
| turn-hold ≥ 0.90 in every band ≥ 8 m/s | \|T_ref(0.02 Hz)\| ≥ 0.998; harness hold 0.990–1.02 | ≥ 0.998 / 0.987–1.02 | **predicted PASS** |
| ring ≤ 0.5 %, F7 = 0, no new 5–30 Hz line | T 5–30 Hz in holds ≤ 0.72 counts on every member. 0 detector reversals. 0 / 10 500 stress points unstable. 13–25 Hz anti-damping ≤ 0.79× V295. | ≤ 0.77 counts, 0 reversals, 0 unstable; **13–15 Hz anti-damping 1.21–1.78× V295** | P2: **predicted PASS**. F2: **declared risk (M13)**. |
| 20 Hz loop gain ≤ V295's | M20 0.67×, L20 ≤ 0.68×, Re(T/ω)₂₀ 0.41× / 0.22× | M20 0.66×, L20 ≤ 0.70×, Re₂₀ 0.84× / 0.58× | **predicted PASS** (both) |
| hard-turn 1.6–3 Hz energy ≤ V282's | The wheel's 1.6–3 Hz rate is 0.79–0.91× the command's own on nominal, ≤ 1.07× on bc, **up to 1.40× on b_lo×J_hi at 8 m/s**. \|T_ref\|₁.₆₋₃ ≤ 2.03 on b_q×J1.0+h10. | the same class (1.29× on b_lo×J_hi) | **PRE-DECLARED (M9)**. The harness compares against the command, not V282; decided on the car. |

---

## 1. PRIMARY P2: every byte

### 1.1 In-place code edits

Every old byte below is asserted against V295 by `r2a_bytes.py` before it is replaced.

| id | address | V295 → P2 bytes | V295 → P2 instruction | loop term | decode evidence |
|---|---|---|---|---|---|
| E1 | `0x28F4C` | `24 3f aa 95` → `24 3f 00 96` | `ld.h -0x6a56[gp],r7` → `ld.h -0x6a00[gp],r7` | x := θ (0.1° counts). The ±12000 bail now tests θ. | form control `0x40AEA 24 77 00 96` (D page) |
| E2 | `0x28FA4` | `89 d1` → `c9 d1` | `subr r9,r26` → `add r9,r26` | r26 = s_old + s_new = 8θ[n] + 8θ[n−1] | inherited (C1) |
| B2 | `0x29A50` | `e2 47 00 00` → `e0 df 34 43` | `setfe r8` → `cmovne r0,r27,r8` | r8 := (request == 1) ? bVar2 : 0 | inherited. r27 dominance is EVIDENCE (tracer flow graph); **re-prove on the built image (H6)** |
| A2 | `0x29A56` | `da 05` → `b2 05` | `bne 0x29A60` → `be 0x29A5C` | the PID runs iff ramp ≠ 0 ∧ r8 ≠ 0 | Ghidra on `b2 05` at `0x15456` (D page) |
| E4 | `0x29D6A` | `08 80 ed 80` → `24 87 52 96` | `mov r8,r16 ; mulh r13,r16` → `ld.h -0x69ae[gp],r16` | sp := gp-0x69ae | form `0x29032 24 6f 52 96` |
| H | `0x29D76` | `c2 82 ba 81` → `89 37 8a ae` | `shl 2,r16 ; sub r26,r16` → `jarl 0xC4C00, r6` | the hook, displacement **+0x9AE8A** | target re-extracted **from the bytes** (`r2a_bytes.py` [2]). The encoder reproduces the flown V112 hook `0x55C0E 86 ff 26 ef`. |
| OPH | `0x29EE0` | `10 40 bb 41` → `1a 40 00 00` | `mov r16,r8 ; sub r27,r8` → `mov r26,r8 ; nop` | D = (Kd·op) >> 3; Kd from `zxh r7` at `0x29EDE`, **unchanged** | Ghidra on `1a 40` at `0x211A2` = `mov r26, r8` (D page) |
| V1 | `0x1310D` | `30` → `41` | data | F181 `39990-TVA,A160` → `39990-TVA,A16A` (the fork interlock) | data (tracer §4) |

**EVIDENCE (my own Ghidra dry-run listing of V294 `0x29D60..0x29F80`, this session):**
- **r26 is not read between `0x29D7A` and its first write at `0x29F76 mov r13,r26`.** Its only appearance before that is
  the displaced `0x29D78 sub r26,r16`. Every branch in the range stays inside the range.
- **r14 and r25 are not written in that range either.**
- `0x29EDE zxh r7 ; 0x29EE0 mov r16,r8 ; sub r27,r8 ; 0x29EE4 mul r7,r8,r0 ; sar 3 ; DCL clamp tp+0x71b6 (= 0xC61B6)` is
  the D the OPH edit feeds.
- `0x29D7A mov r16,r6 ; sar 5,r6 ; 0x29D7E cmp r10,r6` is the e5 path the freeze return skips. r10 is DB, loaded at
  `0x29D6E ld.hu 0x72e4[tp]`; the cave does not touch r10.

### 1.2 The cave (`0xC4C00`, 156 bytes = 114 code + 42 table, in the free span `0xC4BD8..0xC4FEF`)

EVIDENCE (`r2a_bytes.py`):
- The code bytes are **identical to the panel's `ds_cave_D2a.hex` code**; only the table differs.
- Every branch target re-extracted from the bytes is OK.
- The cave writes registers {r6, r8, r9, r13, r16, r26} only. r25 and r14 are never written.
- **No memory is written.** It reads gp-0x6abe, gp-0x6a5e, gp-0x4f68 and its own table.
- **H1:** the assembled bytes, executed by `ds_asm.run_bytes` against the lane's cave arithmetic, give **0 mismatches in
  60 000 random inputs**. The inputs include the 0x7FFF sentinel, the validity edges ±13000 / 13001, the table knots ±1
  and a random register file. Every non-scratch register, r25 and r14 included, is checked unchanged.

The listing below is from the bytes (`c2_cave_P2.lst`). It is **BELIEF until Ghidra decodes the BUILT image (H5)**.
- The forms are controlled: Ghidra dry-runs this session decode the same encodings elsewhere in stock:
  - `0x3F77E 24 47 42 95` = `ld.h -0x6abe, gp, r8`;
  - `0x3539E ee 47 36 43` = `cmovh`;
  - `0x3AFFC e4 47 a3 95` = `ld.hu -0x6a5e, gp, r8`;
  - `0x2C508 e4 47 99 b0` = `ld.hu -0x4f68, gp, r8`;
  - `0x29372 80 07 c2 03` = `jr`.
- The register fields differ only by bitfield.

```
;  entered by  jarl 0xC4C00, r6  from 0x29D76 (r6 = 0x29D7A).  Scratch r6 r8 r9 r13 r16 r26; reads r14 (the ramp).
;  No RAM write, no ep/lp/stack, r25 untouched (live 0x29A82..0x2A0AC across the hook: tracer).
0xC4C00 C:     c2 82              shl   2, r16              displaced 0x29D76: 4*sp
0xC4C02        ba 81              sub   r26, r16            displaced 0x29D78: E = 16*(theta_sp - theta)
0xC4C04        24 d7 42 95        ld.h  -0x6abe[gp], r26    op = fresh 1 kHz motor-rate EMA (-4.712 counts per deg/s)  [D OPERAND]
0xC4C08        1a 46 c8 32        addi  13000, r26, r8      Honda's validity form (FUN_0003f776): op + 13000
0xC4C0C        20 6e 90 65        movea 26000, r0, r13
0xC4C10        ed 41              cmp   r13, r8
0xC4C12        e0 d7 36 d3        cmovh r0, r26, r26        (op + 13000) > 26000 unsigned, incl. 0x7FFF: op := 0     [D GUARD]
0xC4C16        e4 47 a3 95        ld.hu -0x6a5e[gp], r8     v, 64 counts per km/h                                     [G(v)]
0xC4C1A        29 06 72 4c 0c 00  mov   0xC4C72, r9         table
0xC4C20        e9 6f 01 00        ld.hu 0[r9], r13          X0
0xC4C24        ed 41              cmp   r13, r8
0xC4C26        cb 05              bh    L1                  v > X0 (unsigned): walk
0xC4C28        e9 47 03 00        ld.hu 2[r9], r8           G = G0 (clamp low)
0xC4C2C        b5 15              br    APPLY
0xC4C2E L1:    e9 6f 07 00        ld.hu 6[r9], r13          X(i+1)
0xC4C32        ed 41              cmp   r13, r8
0xC4C34        c3 05              bnh   SEG                 v <= X(i+1): segment i
0xC4C36        09 4e 06 00        addi  6, r9, r9           next row; the 0xFFFF row ends the walk
0xC4C3A        a5 fd              br    L1
0xC4C3C SEG:   e9 6f 01 00        ld.hu 0[r9], r13          X(i)
0xC4C40        ad 41              sub   r13, r8             dv = v - X(i)
0xC4C42        29 6f 04 00        ld.h  4[r9], r13          S(i), Q12 signed
0xC4C46        ed 47 20 02        mul   r13, r8, r0         dv*S(i)
0xC4C4A        ac 42              sar   12, r8
0xC4C4C        e9 6f 03 00        ld.hu 2[r9], r13          G(i)
0xC4C50        cd 41              add   r13, r8             G = G(i) + ((v - X(i))*S(i) >> 12)
0xC4C52 APPLY: e8 87 20 02        mul   r8, r16, r0         E*G                                                        [SPEED GAIN, on P and I]
0xC4C56        a8 82              sar   8, r16              E' = (E*G) >> 8
0xC4C58        e4 47 99 b0        ld.hu -0x4f68[gp], r8     |driver torque|                                            [I FREEZE]
0xC4C5C        20 6e 00 02        movea 512, r0, r13
0xC4C60        ed 41              cmp   r13, r8
0xC4C62        cb 05              bh    FRZ                 |tq| > 512 (unsigned): freeze
0xC4C64        ce 6e 00 80        andi  0x8000, r14, r13    r14 = the ramp (0x2A1E6 multiplier)
0xC4C68        ca 05              bne   DONE                ramp full: integrate
0xC4C6A FRZ:   00 32              mov   0, r6               e5 := 0 -> Honda's exc = 0 -> I unchanged
0xC4C6C        b6 07 12 51        jr    0x29D7E             displacement -0x9AEEE: skip 0x29D7A mov r16,r6 / 0x29D7C sar 5,r6
0xC4C70 DONE:  66 00              jmp   [r6]                return to 0x29D7A
0xC4C72 TBL:   (6-byte rows, LE: X u16 = gp-0x6a5e counts (230.4 per m/s), G u16, S s16 Q12)
               ca 02 ab 04 b4 04   X  714 ( 3.10 m/s)  G 1195  S  1204    Kp_eff 523   52 T/deg
               33 07 f7 05 cc e0   X 1843 ( 8.00 m/s)  G 1527  S -7988    Kp_eff 668   67 T/deg
               00 09 74 02 63 fc   X 2304 (10.00 m/s)  G  628  S  -925    Kp_eff 275   28 T/deg
               93 0a 19 02 e1 0a   X 2707 (11.75 m/s)  G  537  S  2785    Kp_eff 235   24 T/deg
               c0 0f 9e 05 1d 05   X 4032 (17.50 m/s)  G 1438  S  1309    Kp_eff 629   63 T/deg
               36 18 52 08 00 00   X 6198 (26.90 m/s)  G 2130  S     0    Kp_eff 932   93 T/deg
               ff ff 52 08 00 00   sentinel row
```

**Whole cave, hex (`c2_cave_P2.hex`, sha256 `75e8755743e14d93…`):**
`c2 82 ba 81 24 d7 42 95 1a 46 c8 32 20 6e 90 65 ed 41 e0 d7 36 d3 e4 47 a3 95 29 06 72 4c 0c 00 e9 6f 01 00 ed 41 cb 05
e9 47 03 00 b5 15 e9 6f 07 00 ed 41 c3 05 09 4e 06 00 a5 fd e9 6f 01 00 ad 41 29 6f 04 00 ed 47 20 02 ac 42 e9 6f 03 00
cd 41 e8 87 20 02 a8 82 e4 47 99 b0 20 6e 00 02 ed 41 cb 05 ce 6e 00 80 ca 05 00 32 b6 07 12 51 66 00 ca 02 ab 04 b4 04
33 07 f7 05 cc e0 00 09 74 02 63 fc 93 0a 19 02 e1 0a c0 0f 9e 05 1d 05 36 18 52 08 00 00 ff ff 52 08 00 00`

**Every instruction names its loop term:**
- the displaced pair: 2 instructions;
- the D operand and Honda's guard: 5;
- the G(v) LERP: 19;
- the speed gain: 2;
- the I freeze: 9.

**Nothing else.** The 15.5 m/s knot was removed because it is collinear: the 6-knot walk gives G 1124 at 15.5 m/s against
the 7-knot table's 1122. It costs nothing measurable: goal metric 0.961 → 0.961, and every GATE-2 number is unchanged to
0.1° (§3).

### 1.3 Calibration cells (24 changed bytes)

| cell | V295 | **P2** | what it is |
|---|---|---|---|
| a `0xC63E8` | 1011 | **0** | fb pole: the 2-tap FIR |
| b `0xC63EA` | 1050 | **8192** | fb gain: s_new = 8θ |
| C `0xC62E6` | 1024 | **65535** | r26 clamp (θ ≤ 409.6°) |
| DB `0xC62E4` | 4 | **0** | I deadband |
| Ki `0xC63E6` | 0 | **56** | Ki_eff = 56·G/256; the PI corner is at 0.622 Hz |
| ICL `0xC61BA` | 10240 | **4096** | I>>7 ≤ 4096 S, about 660 T |
| DCL `0xC61B6` | 0 | **10240** | D clamp |
| Kp record Y `0xE5384` ×5 | 960 ×5 | **112 ×5** | Kp_base, flat (selector 7) |
| Kd record Y `0xE5126` ×4 | 0 ×4 | **34 ×4** | D = (34·op)>>3 = **−20.0 S per deg/s = 3.21 T per deg/s** |

Everything else is V295's, unchanged: PCL, SCL, OCL, the sign-hold, the output lag 992/507, `0xC63F4/F6/F8` and the
timeout cals. The `0xC63F6` ramp cal stays 16.

### 1.4 The loop, integer-exact Python (each line is a byte or a cal above)

```python
def p2_tick(st, theta, sp69ae, abe, v6a5e, tq4f68, ramp, req6805, bvar2):
    if not (ramp != 0 and req6805 == 1 and bvar2):            # A2 + B2 guard (0x29A48..0x29A64)
        st.I8 = 0; st.Eprev = 0x7FFFFFFF; S = 0                # 0x2A164 skip path
        return lag_and_gate(st, S)
    s_new = (8192 * theta) >> 10                               # 0x28F8E..  a = 0: 8 theta
    r26 = clamp(st.s_old + s_new, -65535, 65535); st.s_old = s_new   # E2 0x28FA4 add
    E = (sp69ae << 2) - r26                                    # cave 0xC4C00/02 (displaced shl 2 ; sub)
    op = abe if ((abe + 13000) & 0xFFFFFFFF) <= 26000 else 0   # cave 0xC4C04..12: Honda's validity form
    G = walk(TBL_P2, v6a5e)                                    # cave 0xC4C16..50
    E = s32(E * G) >> 8                                        # cave 0xC4C52/56
    frozen = tq4f68 > 512 or (ramp & 0x8000) == 0              # cave 0xC4C58..68
    e5 = 0 if frozen else E >> 5                               # FRZ: r6 = 0 -> 0x29D7E | else 0x29D7A/7C
    exc = e5                                                   # DB = 0
    I = clamp((st.I8 >> 3) + ((exc * 56) >> 3), -(4096 << 7), 4096 << 7)   # 0x29DA4..0x29DC2
    P = clamp((E * 112) >> 8, -15360, 15360)                   # 0x29E34..0x29E5C (Kp record flat 112)
    D = clamp((34 * op) >> 3, -10240, 10240)                   # 0x29EDE zxh r7 ; OPH mov r26,r8 ; 0x29EE4 mul ; sar 3 ; DCL
    S = (I >> 7) + P + D ; st.I8 = I << 3                      # 0x29F18.. ; 0x2A190
    return lag_and_gate(st, fade_and_clamp(S))                 # fade, SCL, output lag 992/507, x ramp, x pol x 5346 >> 15, OCL
```

This is exactly `ds_lane.DSLane` with the D2a column configuration. **EVIDENCE:**
- `ds_selftest` CHECK 1: DSLane == `c1_lib.LaneC1F`, the C1 pages' byte-exact lane, 0 / 40 000.
- H1 on these bytes: 0 / 60 000.
- `score_time` CONTROL 3: P1's configuration == the panel's D2a.

**Scale, hands off.** EVIDENCE: arithmetic plus the integer walk (`r2a_fit_out.txt`, and the instrument table in §7).
- Kp_eff = 112·G/256. The torque is 0.1002·Kp_eff T per degree:
  - 52 T/deg at ≤ 3.1 m/s;
  - 67 at 8;
  - 28 at 10;
  - 24 at 11.75;
  - 46 at 15;
  - 60 at 17;
  - 78 at 22;
  - 93 at ≥ 26.9.
- P reaches the rail (PCL 15360) at |e| = 24576 / Kp_eff:
  - 42.6–47° at ≤ 5 m/s;
  - 87–105° at 10–12.5 m/s;
  - 26.4–31.8° at ≥ 22 m/s.

### 1.5 Overflow budget (EVIDENCE: `r2a_bytes.py` [6], on this table)

| quantity | worst case | limit |
|---|---|---|
| \|E\| | 4·32767 (sentinel; under A2 the PID does not run on it) + 65535 = 196 603 | — |
| \|E·G\| | 196 603 × 2135 (max over 0–60 m/s) = 4.20·10⁸ | < 2³¹ |
| \|dv·S\| in the walk | 6.5·10⁶ | < 2³¹ |
| \|E'·112\| | 1.84·10⁸ | < 2³¹ |
| \|34·op\| | 34 × 13000 = 442 000 → DCL | — |

### 1.6 Integrity regions the edit dirties (the builder's H8; NOT done here)

The full diff over `[0x13000, 0x100000)` against V295 is **198 bytes**. Two of the 200 written cave bytes equal 0xFF.
**UNLISTED: none.** The edits fall in three integrity regions:
- the main code block, whose trailer is at `0xC4FFC`; it holds `0x13100`, the code edits and the cave;
- the cal page `0xC6000..0xC6FFC`;
- the record block holding `0xE5000` (the Kp/Kd records that V293–V295 already rewrote).

The builder recomputes each of them and passes the kit's `verify_bootloader_crc.py` (walk 49/49, full chain 50/50) on the
built image. This design does not do that step.

---

## 2. FALLBACK F2: every byte (what differs from P2)

**In-place code edits: P2's set without OPH, plus C1's E5 pair. 23 changed bytes in all.** `r2a_bytes.py` [5] lists every
byte.

| id | address | V295 → F2 bytes | instruction | loop term |
|---|---|---|---|---|
| E5a | `0x29EDE` | `c7 00` → `80 39` | `zxh r7` → `subr r0,r7` | −Kd |
| E5b | `0x29EE0` | `10 40 bb 41` → `24 47 aa 95` | `mov r16,r8 ; sub r27,r8` → `ld.h -0x6a56[gp],r8` | D = (−20·x_held) >> 3 |

**The cave** (`0xC4C00`, 138 bytes = 96 code + 42 table):
- **The code is C1 rev 1 / rev 2's 96 bytes, byte for byte.** EVIDENCE: sha256 of the code `a6f902d5…` equals
  `c1/c1_cave_r2.bin.hex[:96]`.
- The table differs. The freeze `jr` displacement is **−0x9AEDC** (from `0xC4C5A`).
- H1: 0 / 60 000.
- It writes {r6, r8, r9, r13, r16} only. No RAM is written. It reads gp-0x6a5e, gp-0x4f68 and the table.

F2's table, LE rows:

| X | v (m/s) | G | S | Kp_eff | T/deg |
|---|---|---|---|---|---|
| 714 | 3.10 | 1187 | 896 | 519 | 52 |
| 1843 | 8.00 | 1434 | −6388 | 627 | 63 |
| 2304 | 10.00 | 715 | −1779 | 313 | 31 |
| 2707 | 11.75 | 540 | 2507 | 236 | 24 |
| 4032 | 17.50 | 1351 | 1348 | 591 | 59 |
| 6198 | 26.90 | 2064 | 0 | 903 | 90 |

The sentinel row is `0xFFFF`, G 2064.

Hex (`c2_cave_F2.hex`, sha256 `482de8587ce23cbc…`):
`c2 82 ba 81 e4 47 a3 95 29 06 60 4c 0c 00 e9 6f 01 00 ed 41 cb 05 e9 47 03 00 b5 15 e9 6f 07 00 ed 41 c3 05 09 4e 06 00
a5 fd e9 6f 01 00 ad 41 29 6f 04 00 ed 47 20 02 ac 42 e9 6f 03 00 cd 41 e8 87 20 02 a8 82 e4 47 99 b0 20 6e 00 02 ed 41
cb 05 ce 6e 00 80 ca 05 00 32 b6 07 24 51 66 00 ca 02 a3 04 80 03 33 07 9a 05 0c e7 00 09 cb 02 0d f9 93 0a 1c 02 cb 09
c0 0f 47 05 44 05 36 18 10 08 00 00 ff ff 10 08 00 00`

**Cals:** P2's, except **Kd record Y `0xE5126` ×4 = 20.** D = −20 S per deg/s on the held rate x = 8 counts per deg/s,
which is 3.21 T per deg/s: the same DC damping as P2.

**Bytes:** 23 + 24 + 138 = **185 written** (183 differ from V295; unlisted: none). The integrity regions are the same
three as P2.

---

## 3. GATE 2: magnitude and phase, in every loop the signal is in

**Conditions:**
- the r71b plant family with the brief's credible set: tier A at PM ≥ 45° and GM ≥ 6 dB, tier B at PM ≥ 30°;
- `ms_free` gated as a tier-A single corner, as the brief lists it;
- `mode13` / `mode20` collocated two-mass modes;
- **every gated member also gated aged** (`+h10`, hold ages 11–20);
- the 0.25 m/s grid over 1–35 m/s, including the plant knots 3.1 / 8.0 / 11.9 / 17.0 / 26.9 (140 speeds);
- the firmware EMA rate model;
- the 5.05 Hz output lag;
- 2 ms transport (0 / 6 ms on the tau members).

Everything above about 8 Hz is model, not identified plant (BELIEF on the plant).

### 3.1 Common scorer (`score_freq`, its own `validate()` = PASS) and exact periodic model

| | P2 | F2 | (P1 / F1, panel tables, re-scored) |
|---|---|---|---|
| GATE-2 fails, brief's set (common scorer; 34 members × 140 speeds) | **0** | **0** | 0 / 0 |
| GATE-2 fails, exact periodic model (ρ, exact GM, every gated member) | **0** | **0** | 0 / 0 |
| unstable points on ANY member, gated or report (exact ρ) | **0** | **0** | 0 / 0 |
| tier A min PM | 46.7° (J_hi, 1 m/s); nominal 64.9°; ms_free 47.6° (8.75 m/s) | 47.0° (J_hi, 1 m/s) | identical |
| tier B min PM | 32.6° (b_lo×J_hi+h10, 1 m/s, fc 1.38 Hz) | 32.1° (same, fc 1.44 Hz) | identical |
| min exact GM, gated | **15.1 dB** (b_q×J1.0+h10, 26.9 m/s) | 8.5 dB (b_lo×tau6+h10, 8 m/s) | identical |
| least-damped low pole, gated | 1.62 Hz ζ 0.129 (b_q×J1.0+h10, 15.75 m/s) | 1.65 Hz ζ 0.135 (same) | — |
| least-damped 5–50 Hz pole | 19.93 Hz ζ 0.073 (mode20: the plant's ζ 0.05 mode is DAMPED) | 19.82 Hz ζ 0.070 | — |
| max \|T_c\|, \|T_ref\| 5–30 Hz, gated | **−5.6 dB** | −3.7 dB | — |
| M20 (× V295 3.384) / L20 (× V295, worst) | 2.28 (0.67×) / 0.677× | 2.24 (0.66×) / 0.697× | — |
| Kp_eff range | 234–932 | 236–903 | — |

**The combined members the refuters named, read from the exact gate** (min PM at the binding speed):

| member | P2 | F2 |
|---|---|---|
| b_q×J_hi | 46.7° (1 m/s) | 47.0° (1 m/s) |
| b_q×J1.0 | 37.4° (15.5 m/s) | 39.0° (15.5 m/s) |
| b_q×tau6 | 62.7° | 62.5° |
| b_q×J1.0+h10 | 34.0° (26.9 m/s) | 33.4° (15.5 m/s) |
| b_lo×J_hi | 37.4° (1 m/s) | 37.3° (1 m/s) |
| b_lo×J_hi×tau6 (report) | 35.2° (8 m/s) | 35.2° (1 m/s) |
| b_lo×J_hi×tau6+h10 (report) | 30.5° (8 m/s) | 30.1° (1 m/s) |
| J1.0 | 39.0° (1 m/s) | 39.3° (1 m/s) |
| J1.0+h10 | 35.5° (1 m/s) | 36.1° (1 m/s) |

All of these are ≥ 30°.

### 3.2 The stability refuter's OWN model and attack lists (`r2a_refute_rerun_out.txt`)

**Positive control first.** The refuter's `anchor()` reproduces its published numbers in this process:
- C0 J_hi @ 11.9 m/s: PM 40.8°, against the published 40.7°;
- every C1 rev 1 anchor, Δ 0.0°.

**The patch, the minimum:**
- immediates 112 / 56 and each implementation's table;
- for P only, the D operand Comega = (34/8)·4.712·EMA(z) in place of Kd·hold.

**Result: 0 sub-bar points on every attack, for P1, P2, F1 and F2.** The attacks are:
- ATTACK 1, tier A plus F_hi / F_lo / ms_free;
- ATTACK 2, tier B;
- ATTACK 3, combined members with the 10-tick aged hold;
- ATTACK 4, b_q×J_hi, b_q×J1.0, b_q×tau6, J1.0×tau6 and b_q0×J_hi, at age 0 and aged.

P2's worst points:
- b_lo×J_hi×tau6+hA: 30.5° at 8 m/s, GM 21.3 dB, ring 1.98 Hz;
- b_q×J1.0 aged: 34.0° at 27 m/s.

### 3.3 Re(T/ω) 5–25 Hz, worst over 1–35 m/s, both hold ages (`r2a_freq_C.txt`; T counts per deg/s, > 0 damps)

| Hz | 5 | 7 | 10 | 13 | 15 | 17 | 20 | 25 |
|---|---|---|---|---|---|---|---|---|
| V294, age 0 | +1.33 | +0.67 | +0.05 | −0.25 | −0.36 | −0.42 | −0.44 | −0.41 |
| V295, age 0 | +2.46 | +1.24 | +0.09 | −0.47 | −0.66 | −0.77 | −0.82 | −0.76 |
| **P2**, age 0 | −0.57 | −0.44 | −0.39 | **−0.37 (0.79×)** | −0.36 (0.54×) | −0.35 (0.46×) | **−0.34 (0.41×)** | −0.31 (0.41×) |
| **F2**, age 0 | −0.84 | −0.84 | −0.86 | **−0.84 (1.78×)** | **−0.81 (1.21×)** | −0.77 (0.99×) | −0.69 (0.84×) | −0.55 (0.73×) |
| V295, age 10 | +1.69 | +0.08 | −1.17 | −1.50 | −1.44 | −1.26 | −0.89 | −0.25 |
| **P2**, age 10 | −0.74 | −0.42 | −0.23 (0.19×) | −0.15 (0.10×) | −0.14 | −0.15 | −0.20 (0.22×) | −0.24 (0.96×) |
| **F2**, age 10 | −1.68 | −1.62 | **−1.47 (1.25×)** | −1.20 (0.80×) | −1.00 | −0.80 | −0.52 (0.58×) | −0.10 |

- **5–7 Hz:** both designs are mildly anti-damping, where V294 and V295 damp. −0.44 to −0.84 T per deg/s at 5–7 Hz is
  1/6–1/50 of the plant's own identified damping b of 5–26 T per deg/s, so no identified mode is at risk. It is declared
  as M14 (§6) with stop band R4.
- **The 25 Hz age-10 point** is 0.96× V295 for P2: under V295, with no margin to spare. It is reported.

### 3.4 The goal's own tracking metric, turn-hold, hard-turn band (`r2a_freq_D.txt`)

Twelve members: nominal, b_lo, b_hi, J_hi, J1.0, b_q, b_q×J_hi, b_q×J1.0, b_lo×J_hi, ms_free, nominal+h10 and
b_q×J1.0+h10. Fourteen speeds from 8 to 30 m/s.

| | P2 | F2 | P5 (5 knots) |
|---|---|---|---|
| goal metric min..max | **0.961–1.011** (min: b_q, 17 m/s) | 0.957–1.011 | **0.946** (b_q, 17 m/s): FAIL |
| turn-hold \|T_ref(0.02 Hz)\| min | 0.998 | 0.998 | 0.998 |
| \|T_ref\| 1.6–3 Hz max (member) | 2.03 (b_q×J1.0+h10, 26–30 m/s); 1.64 (b_lo×J_hi, 8 m/s); nominal ≤ 0.99 | 1.92; 1.51 | 2.04 |

### 3.5 Fork outer-loop stand-in L_o = T_ref·e^(−0.06 s)/(τ_o s) (`r2a_freq_E.txt`; 13 members × 12 speeds)

| τ_o | P2 worst PM / GM | F2 worst PM / GM | reading |
|---|---|---|---|
| 1.0 s | **67.7° / 8.3 dB** (J1.0, 3.1 m/s) | 66.7° / 8.7 dB | passes |
| 0.5 s | 40.4° / **2.3 dB** | 40.5° / 2.6 dB | GM < 6 dB: **not allowed** |
| 0.3 s | **−47.5°** (ms_free, 11.9 m/s): unstable | −46.4° | **not allowed** |

**Fork prerequisite (unchanged from C1): any angle integral in the fork at τ_o ≥ 1 s, and none below 8 m/s.** Its
violation is caught by R3\* (§6).

### 3.6 Stress beyond the gate (`r2a_freq_F.txt`)

**Setup:** collocated two-mass modes at 13 / 15 / 16.5 / 17 / 20 Hz, ζ₂ 0.02 / 0.05, wheel share r₂ 0.2 / 0.4, on
nominal, b_lo and nominal+h10, at every 1 m/s from 1 to 35. That is 2 100 points per implementation.

| | P2 | F2 |
|---|---|---|
| unstable | **0 / 2 100** | **0 / 2 100** |
| min PM | 56.0° | 55.0° |
| max \|T\| 5–30 Hz | −6.1 dB | −5.0 dB |
| least-damped mode | 20.02 Hz ζ 0.036 (open ζ 0.02: the loop adds damping) | 19.99 Hz ζ 0.034 |

The 13–17 Hz stress modes are not the least damped for either design.

---

## 4. Time domain: the common scorer (`score_time.py`; `score_time_out.md`)

### 4.1 The scorer and its controls (EVIDENCE: `score_time_selftest.txt`)

- **Engine.**
  - The lane: `ds_lane.DSLane` for the cave columns, and the original `harness_time.LaneVec` for A1/A2.
  - The plant: `harness_time.PlantVec` (Karnopp stick, 10 kHz sub-steps).
  - The sensors (from `ds_time`):
    - gp-0x6a00 held at slot 4;
    - the integer EMA mirror of gp-0x6abe at 1 kHz;
    - gp-0x6a56 as the slot-4 hold of `FUN_0003f776`'s integer form;
    - Honda's oscillation-detector mirror.
  - `+h10` delivers the slot-4 values 10 ticks late (hold ages 11–20).
- **CONTROL 1:** this runner == `ds_time.run` bit for bit on 16 cave columns, in four scenarios (rh 8, ov_fade 3.1,
  sen_L16 19, s05 26.9): max |ΔT| = 0, max |Δθ| = 0.
- **CONTROL 2:** the zero-cave columns (Kd 0) == `harness_time.run` on the original LaneVec: max |ΔT| = 0.
- **CONTROL 3:** P1's lane configuration == the panel's D2a, and F1's == B0r.
- **Added scenarios (defined in the docstring):**
  - `tmo`: the fork stops sending and the setpoint is held 510 ms, then the 0x7FFF sentinel with request 0xFF;
  - `cs`: co-steer, a helping torque of 0.5× the spring load for 2 s with the torque word at 400, below the freeze;
  - `db`: a 0.2 deg/s creep to 2°;
  - `hard`: 0 → A in 0.3 s, 2 s hold, back in 0.3 s.

### 4.2 The pre-registered bars, every member and every speed

| column | turn-hold ≥ 0.90 at ≥ 8 m/s | line: T 5–30 Hz in holds ≤ 2.0 and 0 detector reversals | sentinel push ≤ 0.1° | tmo: \|T\| < 50 by sentinel + 0.25 s | int32 wraps | verdict |
|---|---|---|---|---|---|---|
| **P2** | 0.990 | 0.72 / 0 | 0.00° | 0 | 0 | **PASS** |
| **F2** | 0.987 | 0.77 / 0 | 0.00° | 0 | 0 | **PASS** |
| P1 / F1 / P5 | 0.990 / 0.987 / 0.990 | ≤ 0.79 / 0 | 0.00° | 0 | 0 | PASS |
| B1, B2+guard, CGF-1+guard, D1b, D2b | ≥ 0.988 | ≤ 1.08 / 0 | 0.00° | 0 | 0 | PASS |
| D3a / D3b / A2+B2 | 0.985 / 0.949 / 0.975 | ≤ 0.94 / 0 | ≤ 0.01° | 0 | 0 | PASS (they miss the goal's tracking elsewhere) |
| B3 | **0.442** | 1.32 / 0 | 0.00° | 0 | 0 | FAIL (no I: turn-hold) |
| D1a / D1c | 0.982 / 0.990 | **6.65 / 6.78** | 0.00° | 0 | 0 | FAIL (texture) |
| D2c | 0.965 | **2.54** / 0 | 0.00° | 0 | 0 | FAIL (texture) |
| A1+B2 | **0.766** | 0.79 / 0 | 0.01° | 0 | 0 | FAIL (turn-hold) |

### 4.3 P2 (and F2) per band: the numbers behind the declared misses

Nominal is shown first; bc and b_lo×J_hi follow where they differ. Every value is from `time_full.json`. F2 is within
±0.5° and ±1 event of P2 everywhere unless stated.

| quantity | 3.1–5 m/s | 8–12.5 m/s | 15–19 m/s | 22–30 m/s |
|---|---|---|---|---|
| dwell-then-jump events per set (s02+s05+ssm) | 4 / 3 (bc 5 / 2) | 0 (bc 1 at 11.9) | 0 | 0 |
| hold slips in rh, per scenario | 2 / 2 | **3 / 3 / 3 at 10 / 11.9 / 12.5** (the ms_free dip, 24–29 T/deg) | 1 at 15 | 1–2 at 22–26.9 |
| ±1° (ssm) stuck %, bc | 42–63 % | 19–57 % | 16–30 % | 5–12 % |
| tracking, wire regression gain, s02 (0.2 Hz) | 1.05–1.06 | 0.95–1.01 | **0.85–0.92** (bc 0.83–0.90) | 0.96–1.03 |
| tracking, s05 (0.5 Hz) | 1.13–1.18 | 0.22–1.03 | **0.35–0.46** | 0.57–0.74 |
| turn-hold (rh hold ratio) | 1.00 | 0.99–1.00 | 1.00–1.01 | 0.99–1.00 |
| step overshoot % | 9.7–16.2 (b_lo×J_hi 23–34) | 6.1–11.1 | −0.6 to 2.1 | 4.0–15.4 |
| release lurch, firm hand (tq 2400, I frozen) | 4.1–4.3° (bc 5.5–5.8, b_lo×J_hi 8.5–10.2) | 1.4–3.3° (b_lo×J_hi up to 7.2) | 0.5–0.8° | 0.3–0.4° |
| release lurch, **light hand 400** (below the freeze; I winds) | 4.2° (bc 6.8, b_lo×J_hi 10.6) | **4.6–7.1°** (bc 7.7, b_lo×J_hi 10.4) | 2.3–3.1° | 2.7–2.9° (b_lo×J_hi 3.5) |
| release lurch, light hand 1000 (frozen) | 4.1–4.2° | 1.3–3.5° | 0.45–0.73° | 0.24–0.36° |
| engage under load, droop | 4.6° (bc 5.1, b_lo×J_hi 6.9) | 1.1–4.5° | 1.3–2.1° | 0.45–1.4° |
| co-steer release droop | 0.6–1.9° | 1.2–1.7° | 0.5–0.9° | 0.2–0.4° |
| dead band (lag once creeping) | 0.25–0.40° | 0.11–0.14° (bc to 0.28) | 0.13–0.14° | 0.10° |
| hard turn: wheel 1.6–3 Hz rate rms / the command's own | 0.79–0.87 (bc 0.97–1.04, b_lo×J_hi 0.94–1.15) | 0.18–0.91 (b_lo×J_hi **1.40 at 8**) | 0.21–0.24 | 0.27–0.30 |
| timeout hold: \|θ − θ(stop)\| over the 510 ms hold | ≤ 0.09° (F_hi ≤ 1.02°) | ≤ 0.39° | ≤ 0.01° | 0.00° |
| sentinel push toward the sentinel | 0.00° | 0.00° | 0.00° | 0.00° |
| 5–30 Hz torque in holds / 40–200 Hz | ≤ 0.72 / 0.76 counts rms on every member | | | |
| oscillation detector | max 0.224 of threshold, 0 reversals | | | |

### 4.4 Dense pass (3–30 m/s every 0.25 m/s; nominal and bc)

**Scope:** 109 speeds × the s02, rh and ssm scenarios. Every column ran in one batch; the full table is in
`score_time_out.md` §Dense.

**Columns of the table below:**
- **turn-hold min ≥ 8:** the lowest rh hold ratio at ≥ 8 m/s, and the speed where it occurs.
- **s02 gain ≥ 8:** the wire regression gain at 0.2 Hz, min and max over ≥ 8 m/s, with the speed of each.
- **dwell-then-jump events:** summed over s02 + ssm on the grid, in three speed bands.
- **±1° stuck % max 3–7:** the highest share of time stuck on ±1° corrections at 3–7 m/s.
- **hold slips in rh, 13.25–30:** a slip is a ≥ 0.1° creep after ≥ 100 ms stuck.

| column | member | turn-hold min ≥ 8 | s02 gain ≥ 8 (min / max) | dwell-then-jump events 3–7 / 7.25–13 / 13.25–30 | ±1° stuck % max 3–7 | hold slips in rh, 13.25–30 |
|---|---|---|---|---|---|---|
| **P2** | nominal | **0.978** (28.75) | **0.852** (17) / 1.033 | 33 / **0** / **0** | 57.0 | 48 (≈ 0.24 per hold) |
| **P2** | bc | **0.981** (24.5) | 0.833 (17) / 1.011 | 35 / 5 / 0 | 62.8 | 0 |
| **F2** | nominal | 0.971 (28.75) | 0.835 (17) / 1.035 | 34 / 0 / 0 | 57.6 | 68 |
| **F2** | bc | 0.983 (22.25) | 0.814 (17) / 1.012 | 36 / 3 / 0 | 63.4 | 0 |
| P5 | nominal / bc | 0.978 / 0.982 | **0.777 / 0.762** (16.75) | 31 / 0 / 0 ; 35 / 5 / 0 | 56–63 | 47 / 0 |
| B1 / B2+guard / CGF-1+guard | nominal | 0.985 / 0.977 / 0.985 | 0.807 / 0.853 / 0.910 (17) | 43 / 32 / 30 at 3–7 | 66 / 59 / 55 | 77 / 60 / 75 |
| A1+B2 | nominal | **0.779** (17) | **0.406** (17) | 25 / 0 / 0 | 100 | 0 |

**What the dense pass adds to §4.3:**
- **Turn-hold ≥ 0.97 everywhere ≥ 8 m/s** on both members, for P2 and F2.
- **No dwell-then-jump event anywhere at 13.25–30 m/s**, and none at 7.25–13 on nominal. On bc there are 5 events at
  7.25–13 m/s, over 23 speeds × 2 scenarios.
- **The low-speed band (3–7 m/s) carries every event**: 33–36 over 17 speeds × 2 scenarios. That is M1.
- **The 0.2 Hz wire gain dips to 0.83–0.85 at about 17 m/s.** That is M3. The goal's own metric there is 0.961.
- **Highway holds on the nominal friction world creep in ≥ 0.1° steps** about 0.24 times per hold (M11). The bc world
  (friction ×2) sticks instead: 0 slips.
- **P2 is the best of the passing cave candidates on the highway-hold creep** (48 vs F2 68, B1 77, CGF-1 75).

**The same dense pass on the aged hold (nominal+h10, hold ages 11–20) and on F_hi (friction ×2)** (`time_dense2.json`):

| column | member | turn-hold min ≥ 8 | s02 gain ≥ 8 (min / max) | dwell-then-jump events 3–7 / 7.25–13 / 13.25–30 | ±1° stuck % max 3–7 | hold slips in rh, 13.25–30 |
|---|---|---|---|---|---|---|
| **P2** | nominal+h10 | **0.975** | 0.860 (17) / 1.039 | 37 / 0 / 0 | 56.4 | 72 |
| **P2** | F_hi | **0.976** | 0.856 (17) / 1.052 | 63 / 3 / 0 | **90.1** | 101 |
| **F2** | nominal+h10 | 0.967 | 0.843 (17) / 1.041 | 38 / 0 / 0 | 57.6 | 74 |
| **F2** | F_hi | 0.971 | 0.836 (17) / 1.054 | 64 / 1 / 0 | 90.7 | 98 |
| A1+B2 | F_hi | 0.776 | 0.376 / 0.845 | 8 / 26 / 0 | 100 | 0 |

**What the aged and high-friction passes show:**
- **The goal's turn-hold holds (≥ 0.97) on every member and every speed ≥ 8 m/s, with the hold aged to 20 ticks and with
  friction doubled.**
- **On F_hi, ±1° corrections at 3–7 m/s are stuck 90 % of the time.** This is the M1 class at its worst credible
  friction.
- **Highway-hold creep about doubles** on F_hi and on the aged hold: about 0.5 and 0.35 per hold (M11).
- **No candidate escapes M1 or M11.** A1 shows 0 creep only because it never closes the error (turn-hold 0.78).

---

## 5. Hazards and fail-safe paths (the bytes-and-fail-safe lens, item by item)

"Fails safe" here means: no torque path without a valid, current, driver-assist setpoint.

| # | path | P2 behaviour | F2 | fails safe? | E/B |
|---|---|---|---|---|---|
| H-sen | 0xE4 fault sentinel 0x7FFF (`gp-0x69ae`, request 0xFF) | A2 skips the PID on request ≠ 1; sim push 0.00° every member and speed | same | **yes** | EVIDENCE guard bytes and sim. The preemption window is 0 ticks (tracer: RX slot 3 prio 3, lane slot 0 prio 6). |
| H-tmo | the fork stops sending (crash, unplug) | The last θ_sp is held **510–514 ms** (the pending threshold `0xC626C` 500 ms + the 200 Hz phase), then the sentinel → A2 → output lag decay. Sim: \|T\| < 50 by +0.25 s; hold deviation ≤ 0.39° nominal, ≤ 1.0° F_hi. | same | **holds the last VALID command for 0.51 s** (stock does the same with the last rate demand); declared M12 | EVIDENCE tracer §3, sim |
| H-rate | motor rate invalid (`gp-0x4f50` outside ±13000 → `gp-0x6abe` = 0x7FFF) | The cave applies Honda's own test (`FUN_0003f776`: `0x6590 < x + 13000` → zero), so op := 0 and D = 0, exactly when the held cell would be 0 | the held cell is 0 (`FUN_0003f776`) | **yes**: no new exposure | EVIDENCE: my decompile of `FUN_0003f776` this session; H1 0/60 000 incl. ±13000 / 13001 / 0x7FFF |
| H-fresh | is gp-0x6abe current at the lane? | `FUN_00041464` (its sole writer) runs at `0x22200` when `(1<<mode) & 0xD30`; the lane runs at `0x22522` when `(1<<mode) & 0x930`, later in the same 1 kHz task `FUN_0002214a`. 0x930 ⊂ 0xD30, so **whenever the lane runs, the fresh rate was computed earlier in the same tick.** | n/a | **yes** | EVIDENCE: my decompile of `FUN_0002214a` and `get_xrefs_to` this session |
| **H-pol** | the sign of P2's fresh D | The lane output is multiplied by `pol = gp-0x6752` (`0x2a1fe`), and so are θ and x. P and the held D are pol-invariant; **the fresh D is not.** pol is boot-static, from config record 0x54 in the data-flash block (`FUN_00048a40`: byte `','` → +1, `0xFA` → −1). **On this car pol = −1, constant** (V98 b3 over 17 983 frames, verified three ways). | pol-invariant | **yes on this car**; on a pol = +1 car P2's D would ANTI-damp | EVIDENCE: decompile of `FUN_00048a40` / `FUN_0003f776` this session + the V98 record. Firmware is car-specific (safety rule 5). A pol-invariant variant (+8 B: `ld.b -0x6752[gp]` ; `mul`) was evaluated and not adopted (§9). |
| H-67fe | `gp-0x67fe ≠ 2` (θ forced to 0) | B2 makes the PID skip | same | yes | EVIDENCE tracer (r27 dominance); **H6 on the built image** |
| H-wrap | angle baseline wrap (−0x8000) | The ±12000 bail on θ → r26 = 0, and **STEER_STATUS 7 latches until key cycle** (LKAS off) | same | yes (a nuisance, not a hazard) | EVIDENCE angle trace |
| H-start | engage / first tick | stateless cave; I = 0 after any skip; I frozen through ramp-in; the fork sends θ_meas at engage (C5). Sim engage droop ≤ 4.6° nominal, 6.9° b_lo×J_hi | same | yes; the droop is declared M7 | EVIDENCE sim |
| H-drop | request drop / main off / panda zeros | A2: about 0.1 s output-lag release (Honda's 2 s hand-back is gone) | same | yes | EVIDENCE sim (dis_meas, dis_zero) |
| H-ovr | override / release (V283's class) | freeze above \|tq\| 512 + fade + ICL 4096 + the fork's O1. **A hand below 512 winds I: release overshoot up to 7.1° nominal, 10.6° b_lo×J_hi** (§4.3) | same (7.0° / 10.4°) | bounded (ICL 660 T); declared M6 | EVIDENCE sim; BELIEF on the torque-word scale |
| H-auth | authority | P rails at 26–105° of error by speed; ICL 660 T; the sum and output clamps are V295's (rail 2461). A fork bug equals the rail; the fork's Δmax(v) caps the demanded P | same | bounded by the existing clamps | EVIDENCE arithmetic |
| **H-cam** | **the stock camera's 0xE4 on a relay close** (comma off, Honda LKAS on) | **The firmware cannot tell the camera's torque value from an angle setpoint.** A camera command `raw` becomes θ_sp = −raw/10°, and the lane drives the wheel there with full P authority. Example: raw 100 gives 10° of steering-wheel angle; at 25 m/s that is about 0.6° of road wheel and about 2.4 m/s² of lateral acceleration. | same | **NO: not fail-safe in firmware. Mitigated only by procedure** (camera LKAS off, a flight prerequisite) | EVIDENCE: C1 rev 2 §2.10, the state-7 decompile. The arithmetic is EVIDENCE; the camera's raw range is BELIEF. |
| H-fork-tq | a torque-mode fork on this image | It would send torques as angles | same | **yes, if** V1 (`39990-TVA,A16A`) and the fork's `AccordEpsAngleLoop` key both ship, and the revert `.rwd`s are re-headered | EVIDENCE fw string and tracer §4; the fork half is BELIEF |
| H-fork-0 | an angle fork emitting raw 0 with request 1 | drives θ toward 0° with P authority (a valid-looking command) | same | **depends on the fork** (C3/C5: inactive = θ_meas; Δmax) | BELIEF on the fork |
| H-bad | corrupt 0xE4 frames | up to 49 bad-checksum / counter frames decoded as valid before the fault | same | bounded by the fork's own counter | BELIEF (decompile only; tracer) |
| H-slot4 | slot-4 phase | `FUN_00014be4` is called at three checkpoints in `FUN_0002214a`: two before the lane and one after | same | n/a: hold ages 0–9 instead of 1–10 would add margin; ages 1–20 are swept | EVIDENCE decompile; BELIEF on the realized phase |

**H-cam is the one fault path that does not fail safe, and it is shared by every angle-loop candidate in the record:**
C0, C1, the whole panel, P2 and F2. A firmware gate needs the fork to send `gp-0x6803 == 2` and a per-tick check in the
cave, at least +10 bytes. That switches the engage chain to states 6/7/8 (ramp-in 0.10 s) and the live post-PID fade to
`0xCBAE4`, which pushes **up to 2.1× harder against a 600–3240 raw hand.** It is a design of its own, with its own GATE 2
and time runs. It is **not in P2 or F2.** **The orchestrator should treat "camera LKAS off" as a hard flight
prerequisite and track the F3-class gate as the first safety follow-up.**

---

## 6. Pre-declared misses (each quantified, each with the stop band that catches its ring)

**Stop bands (written before any build):**
- **R3\*.** At **any speed**, an oscillation in **0.5–5.5 Hz** in 0x14A or the 0x18F rate that **grows**, or that shows **≥ 4
  visible cycles above twice the pre-event rms (ζ < 0.10)**, means **REVERT**. It covers:
  - every sub-30° report-member ring: 0.92–1.53 Hz at ≤ 8.25 m/s with ζ ≥ 0.164; 1.44–1.46 Hz at 14.5–35 m/s with
    ζ ≥ 0.086; light_b at 3.72 Hz with ζ 0.075 (F2: 3.81 Hz, ζ 0.060);
  - the τ_o < 1 s outer-loop instability at about 0.5–1 Hz;
  - anything outside the credible set.
- **R4.** A narrowband 5–30 Hz line in the 0x18F rate or the torque bar that is absent on V282/V295. For F2 the band to
  watch is **10–17 Hz**.

| # | criterion (goal) | band | predicted, P2 (F2 where it differs) | stop band / revert | basis |
|---|---|---|---|---|---|
| M1 | low-speed stick-slip gone; dwell-then-jump ≤ V282 | **3–7 m/s** | 3–5 dwell-then-jump events per scenario set; **±1° corrections stuck 42–63 %** of the time; dead band 0.25–0.40°; hold slips 2 per hold | operator words (R9); the per-band dwell rate vs r6c | EVIDENCE sim (§4.3); every panel candidate misses this (B1 66 %, A1 100 %, D3 80 %) |
| M2 | dwell-then-jump ≤ V282 | **10–12.5 m/s** (the ms_free dip, 23–29 T/deg) | 3 hold slips per hold, nominal; bc 2–3 | same | EVIDENCE sim |
| M3 | tracking faster than the goal's metric | **12.5–22 m/s** | wire gain at 0.2 Hz **0.85–0.92** (bc 0.83–0.90); in-phase at 0.5 Hz **0.35–0.57**. The goal's own metric passes (0.961–1.011). | not a revert. Lane changes and S-bends at highway speed will lag the plan. | EVIDENCE sim + freq |
| M4 | tracking at ±1° | 8–19 m/s | stuck 9–57 % (bc); fit gain 0.85–1.17 | — | EVIDENCE sim |
| M6 | release after a **light** hand (below the 512 freeze) | all; worst at 10–12.5 m/s | overshoot past θ_sp ≤ 4.6° (≤ 8 m/s), **4.6–7.1° (10–12.5 m/s)**, ≤ 3.1° (≥ 15); bc ≤ 7.7°; b_lo×J_hi ≤ 10.6°. At 11.9 m/s, 7° of wheel ≈ 0.4 m/s² lateral, transient. | R9 (operator's words); the regression's I-freeze check (§7) | EVIDENCE sim; BELIEF on the torque-word scale |
| M7 | engage under a handed-over load | ≤ 10 m/s | droop ≤ 4.6° (bc 5.1, b_lo×J_hi 6.9) | — | EVIDENCE sim |
| M9 | hard-turn 1.6–3 Hz ≤ V282 | 5–8 m/s on b_lo×J_hi; 15–30 m/s on b_q×J≥1 | wheel 1.6–3 Hz rate up to **1.40×** the command's own (b_lo×J_hi, 8 m/s; ring 1.86 Hz ζ 0.30); \|T_ref\|₁.₆₋₃ ≤ 2.03 on b_q×J1.0+h10 (ring 1.62 Hz ζ 0.13) | R3\* (0.5–5.5 Hz); its discriminator (§7.3) | EVIDENCE model + sim |
| M10 | the 0.2 Hz goal-metric margin | 15–19 m/s | metric 0.961 against the 0.95 bar; the ±0.028 control means it is **inside the metric's accuracy** | on-car tracking outside 0.95–1.05 in any band ≥ 8 m/s = FAILED its goal (§8.2) | EVIDENCE weights + BELIEF on r71b's spectrum |
| M11 | dwell-then-jump in highway holds | 13–30 m/s | ≥ 0.1° creeps after a ≥ 100 ms stick: about 0.24 per hold on the dense grid (nominal; F2 0.33), 0.35 (aged hold), 0.5 (F_hi), 0 on bc; no dwell-then-jump event in the sinusoids at ≥ 13.25 m/s on any member | — | EVIDENCE sim (§4.4) |
| M12 | the fork stops sending | all | the last θ_sp is held 0.51 s, then the sentinel → A2 → about 0.1 s decay | — | EVIDENCE tracer + sim |
| **M13 (F2 only)** | no new 5–30 Hz line | ≥ 20 m/s | 13 / 15 Hz anti-damping **1.78× / 1.21× V295** (age 0); 10 Hz **1.25×** (age 10) | **R4 with a 10–17 Hz watch** | EVIDENCE model (BELIEF plant > 8 Hz) |
| M14 | 5–7 Hz damping | all | Re(T/ω) −0.44 to −0.57 (P2), −0.84 (F2), where V294/V295 damp | R4 (a 5–8 Hz line); F7 > 0 | EVIDENCE model |
| M15 | the stock camera | — | not fail-safe in firmware (H-cam) | operator procedure | EVIDENCE decompile |

---

## 7. The instrument: what proves P2 (or F2) live in one short drive (no new telemetry bit)

**Signals on the wire:**
- 0xE4: θ_sp = −raw/10 and the request;
- 0x14A: θ at 100 Hz;
- 0x18F: rate, driver torque (wire = raw × 1.024) and STEER_STATUS;
- the CAN 427 tap: T = gp-0x6b38, 50 Hz, polarity +sign(cmd);
- **the F181 string** `39990-TVA,A16A` in carFw.

Decode with the patched cereal (the slot-137 collision), and take routes from the device's realdata.

### 7.1 LIVE / NOT LIVE / INVERTED (pre-registered)

**Window:** hands-off (|0x18F| < 500 wire), request 1, ≥ 1.2 s after the engage edge.

**Regression** (0.3–3 Hz): `tap = c_P·(raw − 10θ) + c_I·Σ(raw − 10θ)·dt + c_D·ω_18F + c0`.

| band (m/s) | 0–5 | 5–8 | 8–10 | 10–12.5 | 12.5–15 | 15–22 | 22–35 |
|---|---|---|---|---|---|---|---|
| P2 Kp_eff | 523–578 | 579–666 | 285–668 | **234–283** | 286–454 | 458–772 | 774–932 |
| P2 c_P = Kp_eff/800 | 0.65–0.72 | 0.72–0.83 | 0.36–0.84 | **0.29–0.35** | 0.36–0.57 | 0.57–0.97 | 0.97–1.17 |
| F2 c_P | 0.65–0.70 | 0.70–0.78 | 0.40–0.78 | 0.30–0.39 | 0.35–0.54 | 0.55–0.92 | 0.93–1.13 |

| verdict | condition |
|---|---|
| **LIVE: the image** | carFw EPS = `39990-TVA,A16A` |
| **LIVE: angle loop** | c_meas / c_raw ∈ [−1.25, −0.80] |
| **LIVE: the speed schedule** | c_P within ±30 % of the band prediction in every band with ≥ 15 s of window, **and the dip**: c_P(10–12.5) / c_P(5–8) ∈ [0.25, 0.60] (predicted 0.35–0.49), **and** c_P(> 22) / c_P(5–8) ∈ [1.05, 1.8] (predicted 1.16–1.61) |
| **LIVE: the PI corner** | c_I / c_P ∈ [2.7, 5.1] s⁻¹ (3.91) |
| **LIVE: the D** | c_D ∈ [0.30, 0.50] tap per deg/s, opposing ω (3.21 T per deg/s ÷ 8), flat in speed; the coefficient on θ̇_sp ≈ 0 (the D is not on E) |
| **LIVE: the freeze** | in hands-on episodes with \|0x18F\| > 600 wire for ≥ 0.5 s and \|θ_sp − θ\| > 0.3°, the I component changes by < 3 tap counts per 0.5 s |
| **LIVE: A2** | after every request drop, \|tap\| < 20 within 0.15 s |
| **INVERTED → abort (R1)** | c_meas / c_raw > 0, **or c_D aiding (same sign as ω)**. For P2 the second condition is the pol check (H-pol). |
| NOT LIVE: cave skipped | c_P ≈ 0.14 in every band |
| NOT LIVE: wrong image | \|c_meas\| < 0.2·\|c_raw\| and the tap reproduces V295's raw-only surface |

**What one drive cannot separate: P2's fresh D operand from F2's held one** (a 5.5 ms operand lag behind the 5 Hz output
lag). It is proven **statically**: H5 decodes `0x29EE0 mov r26,r8 ; nop` and the cave's `ld.h -0x6abe[gp],r26` in the built
image. This is declared, not hidden. The decision the drive must support, "the angle loop is live and its terms have the
designed size", is fully observable. The 13–17 Hz advantage of P2 is model-only, and the drive's evidence on it is the
absence of an R4 line.

### 7.2 REVERT (any one; written before the build)

| id | signature |
|---|---|
| R1 | INVERTED (above) |
| R2 | hands-off, request 1, \|tap\| ≥ 300 (the rail) for > 0.3 s |
| **R3\*** | **at any speed**, a 0.5–5.5 Hz oscillation in 0x14A or the 0x18F rate that grows, or ≥ 4 visible cycles above 2× the pre-event rms |
| R4 | a narrowband 5–30 Hz line in the 0x18F rate or the torque bar absent on V282/V295 (F2: watch 10–17 Hz) |
| R5 | ring presence > 0.5 %, or F7 > 0 per 100 s |
| R6 | \|θ − θ_sp\| > 10° hands-off for > 0.5 s at > 8 m/s |
| R7 | after a request drop, \|tap\| still pushing toward 0° for > 0.2 s |
| R8 | STEER_STATUS ≠ 0, or 0x14A b4 bits 0–2 ≠ 7, while engaged |
| R9 | the operator's own words: grinding, ratcheting, a jerk or a swerve in turns, a lurch on letting go |

### 7.3 Discriminator (decaying rings at turn-ins; the least-damped closed-loop poles from §3)

| 0x14A shows | the plant is | next |
|---|---|---|
| no visible ring | nominal / J_hi / b_lo class | a later build may raise the highway gain, only after the 1–5 Hz FRF |
| a 3.5–4 Hz ring with ζ about 0.5 (1–2 cycles) at ≥ 12.5 m/s | b_q, nominal J | keep |
| a 2.4–2.5 Hz ring with ζ about 0.26–0.29 | b_q×J_hi | keep |
| a 1.6–1.8 Hz ring with ζ 0.13–0.15 at 15–27 m/s | b_q×J ≈ 1 | keep; hard-turn amplification is expected (M9) |
| a 1.4–1.5 Hz ring with ζ 0.16–0.24 at ≤ 8 m/s | J ≥ 0.8 at low speed (outside the identified J ≤ 0.5) | keep; do not raise the low-speed gain |
| any 0.5–5.5 Hz ring with ζ < 0.10, or growing | outside the credible set (light_b class, or the fork's τ_o < 1 s) | **REVERT (R3\*)** |

---

## 8. What a FAIL looks like (written before any build)

### 8.1 In the harness and the adversarial pass: any one means **do not flash**

| id | failure |
|---|---|
| H1 | The interpreter (`ds_asm.run_bytes`), executing **the built image's** cave bytes, differs from the lane's cave arithmetic on any of 60 000 random inputs, OR any register other than the scratch set changes (**r25 and r14 included**). The scratch set is r6/r8/r9/r13/r16/r26 for P2 and r6/r8/r9/r13/r16 for F2. |
| H2 | `r2a_freq.py` A/B on the built image's table and cals: **any** gated point with PM < bar, exact GM < 6 dB, ρ ≥ 1, \|T\| or \|T_ref\| > +3 dB in 5–30 Hz, or M20/L20 > V295's. Also: any report-member point unstable; the refuter's model with any sub-bar point; P2's worst-over-speed Re(T/ω) at 13–20 Hz above V295's at either hold age; any stress point unstable. |
| H3 | `score_time.py` with the built table: any pre-registered bar failing on any member; any int32 wrap; a sentinel push > 0.1°. |
| H3b | the goal metric (`c1r2_trackmetric.slope`) < 0.95 for any member in any band ≥ 8 m/s |
| H4 | GATE 1: the cave writes any RAM, or reads any RAM other than gp-0x6a5e, gp-0x4f68 and (P2) gp-0x6abe |
| H5 | From the BUILT image, in Ghidra: the hook does not decode as `jarl 0xC4C00, r6`; the `jr` does not land on `0x29D7E`; `jmp [r6]` is not the normal exit; r26 is read between `0x29D7A` and `0x29EE0` by anything but the new `mov r26,r8` (P2); r14 is written between `0x29D7A` and `0x2A1E6`; r25 is written anywhere in the cave; any branch lands in `0x29D76..0x29D7D`; or the cave is reachable from a skip path. |
| H6 | With A2 + B2 in the built image: P computed on the 0x7FFF sentinel on any tick; the B2 `cmov` is not r8 := (Z ? r27 : 0); `0x2913A` does not dominate `0x29A48` (the tracer's flow-graph method, re-run on the built image) |
| H7 | The table lacks the 0xFFFF row, or the walk reads outside the table for any v in 0..65535 |
| H8 | Any integrity region fails the kit's `verify_bootloader_crc.py` on the built image (walk 49/49, full chain 50/50), **including the block holding `0x13100`** |
| H9 | The F181 bytes are not `39990-TVA,A16A`; the `.rwd` header does not list both A160 and A16A; or the V295/V294 revert `.rwd`s are not re-headered to list A16A |
| **H10 (P2)** | pol is not −1: the V98 b3 record is contradicted, or the config-record parse (`FUN_00048a40`) gives +1 on this car's data |

### 8.2 On the car

| | condition |
|---|---|
| **REVERT** | any of R1–R9 |
| **FAILED its stated goal** | Any one of: a band ≥ 8 m/s with on-car turn-hold < 0.90 over ≥ 60 s; **on-car tracking (the scorer's slope) outside 0.95–1.05 in any band ≥ 8 m/s**; a new 5–30 Hz line; dwell-then-jump above r6c in a band **other than** the declared 3–7 m/s, 10–12.5 m/s and highway-hold misses. |
| the pre-declared misses | §6. They are FAILs of those criteria, declared now. |
| NOT INTERPRETABLE | must not happen. LIVE needs about 15–30 s of hands-off frames in each of three bands: one stretch > 22 m/s, one at 10–12.5 m/s (the dip), and one at 5–8 m/s. |

---

## 9. Evaluated and not adopted (so nobody re-proposes them blind)

| alternative | result | why not |
|---|---|---|
| **P1**: D2a's 7-knot table | identical loop to P2, to 0.1° | +6 B for nothing |
| **P5**: 5 knots (no 15.5 / 17.5) | −12 B; 0 GATE-2 fails | **goal metric 0.946 at 17 m/s (b_q): FAILS the goal**. The size floor of this walk is 6 knots. |
| **P3 / P4**: fresh-rate Kd 41 / 48 (cal-only) | envelope = 0 at 12.5–15.25 m/s (Kd 41; b_q×J_hi, b_q×J1.0) and at 1–16.5 m/s (Kd 48; b_lo, b_q) | **The D term's own loop crosses unity against the lowest credible damping.** D_T = (Kd/8)·4.712·0.160 = 3.21 T per deg/s at Kd 34, 3.87 at 41 and 4.53 at 48, against b_lo below 10 m/s and the b_q floor, both 3.46. **Kd 34 is the largest D under that floor.** EVIDENCE (envelope, `r2a_fit_out.txt`); the mechanism is BELIEF (arithmetic). This also explains why B2 (Kd 41) and CGF-1 (Kd 48) were never fit to the brief's set. |
| pol-invariant fresh D (+8 B: `ld.b -0x6752[gp],r8 ; mul r8,r26,r0`) | removes H-pol | pol is EVIDENCE −1 and boot-static on this car; the image is car-specific. Priority 2. |
| D1b: fresh accumulator difference | best 5–25 Hz damping (panel) | +1 RAM word (gp-0x6c44), a stale-`d_prev` one-tick D, a D scale that is BELIEF across angle; time bars pass (§4) but it costs RAM over P2 |
| D2b / D2c: output-lag lead | +16–20 % stiffness | +40–46 B and a RAM word; D2c fails the texture bar (2.54); D2b is a 2× P kick on setpoint steps |
| A1+B2 (zero cave, 79 B) | the bytes floor | **turn-hold 0.766–0.781 at ≥ 8 m/s**: fails the goal |
| A2 (Ki cave) | turn-hold 0.976–0.983 | the cave was never assembled; tracking 0.67–1.01 / 0.15–0.92; tmo hold deviation up to 4.1° (F_hi) |
| CGF-1 (+ the mandatory guard) | highest highway gain | never fit to ms_free: 35 frequency-domain fails (SCORE-FREQ) |
| B3 (no firmware I) | | turn-hold 0.44–0.46 |
| a lower freeze threshold (256) to shrink M6 | 0 bytes | the record (route a6) reads > 500 wire on 25–48 % of HANDS-OFF turning frames; a lower threshold freezes I in normal turning. Not evaluated in sim, so not offered. |
| A1's speed re-key of the **Kd** record as a zero-cave Kd(v) (judge graft 3) | | not evaluated: RK1 re-keys r7 (the Kp key); the Kd key is r22 (`0x29E92 mov r22,r13`), so a Kd re-key is a different edit that needs its own liveness trace. Kd above 34 is capped by the P3/P4 finding anyway. |
| the F3-class camera gate (`gp-0x6803 == 2`) | closes H-cam | +10 B, switches the engage chain and the fade arm (×2.1 against a hand); its own design, GATE 2 and time runs; **the first safety follow-up** |

---

## 10. Concerns and open items

1. **H-cam is not fail-safe in firmware** (§5). The stock camera's LKAS on a relay close would be steered to as an angle.
   This is shared by every angle-loop design in the record. The mitigation is procedural only.
2. **P2's D sign rests on pol = −1** (EVIDENCE, boot-static). The image must never be flashed to another car (safety rule
   5). The first-drive INVERTED check covers it.
3. **The fresh-vs-held D operand is not wire-observable in one drive.** It is proven statically (H5).
4. **Everything above about 8 Hz is model.** P2's 13–25 Hz advantage over F2 (0.79× vs 1.78× V295 at 13 Hz) is EVIDENCE
   in the model and BELIEF on the plant.
5. **The goal-metric pass at 15–19 m/s has a 0.011 margin**, inside the metric's ±0.028 control (BELIEF on r71b's
   spectrum). The time-domain 0.2 Hz wire gain there is 0.85–0.92 (M3).
6. **Low-speed stick-slip is not fixed by any candidate** (M1). A friction feed-forward sized from the first drive's
   breakaway reads (C1 rev 2 §6.4) is the next design. CGF-2's FF is the panel's only attempt, and it is unassembled.
7. **The light-hand release lurch** (M6, up to 7.1° nominal, 10.6° b_lo×J_hi) is the V283 class, bounded by ICL. It
   depends on the unknown torque-word scale (BELIEF).
8. **The integrity trailers (H8) are the builder's step**, not done here.
9. **`score_time.py` lives in `c2/rev2A/`, not `panel/`.** That is deliberate, to avoid colliding with reviser B. Its
   three controls are in `score_time_selftest.txt`.
10. **The time-domain speed set is 12 speeds for the full scenario list, plus the dense 0.25 m/s pass** on s02 / rh / ssm
    for nominal, bc, nominal+h10 and F_hi (§4.4). The full scenario list was not run on the 0.25 m/s grid. The frequency
    domain is complete on that grid.
