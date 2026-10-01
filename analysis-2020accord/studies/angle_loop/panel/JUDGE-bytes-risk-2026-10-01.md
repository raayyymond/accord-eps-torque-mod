# JUDGE: BYTES & RISK. Angle-loop design panel, 2026-10-01

**Status: ANALYSIS ONLY.** Nothing was built, flashed or sent, and the fork was not touched. Ghidra was read-only:
`decompile_function` on stock `code.bin`, and `disassemble_bytes dry_run:true` on the open V294 program, which is
code-identical to V295 except cal `0xC63EA` and its CRC. Nothing was saved. No scorer cache was rewritten. I did NOT
re-run `score_freq.py quick`, because it overwrites the shared `_scratch/angle_loop/panel/score_freq_*.json`.

**Author:** the bytes-risk judge, a subagent for the orchestrator `main`. **My lens is PRIORITY 2:** total bytes, cave
count and size, RAM words, new encodings that stay BELIEF until a built image is decoded, hook-site liveness, CRC blocks
dirtied, how byte-exactly a golden-model mirror can cover the edit, and fault paths that do not fail safe. The brief makes
Priority 1 (meeting the goal) senior to Priority 2, so a goal/gate component carries 20 % of each score. A small build
that fails the goal must not outrank a slightly larger one that meets it.

Every decision-bearing claim is marked **EVIDENCE** (with its method) or **BELIEF**. Code is cited by address or grep
string.

---

## 0. Verdict in one table

Scores are out of 100: Size 25, Verifiability 30, Liveness / fault-path risk 25, Gate / goal standing 20. The common
**freq** scorer's table outranks a designer's own page. **The common TIME scorer was halted and produced nothing**, so
I use time-domain numbers only where a designer reports a failure against its own interest.

| # | id | score | bytes (normalised) / caves / RAM | one-line reason |
|---|---|---|---|---|
| 1 | **D2a** | **82** | 206 / 1 × 162 / 0 | C1r2 skeleton plus a fresh-rate D that reuses **Honda's own validity form**. Cave assembled and interpreter-tested 0/60 000. 0 GATE-2 fails, turn-hold 1.00, goal metric 0.961, 13–20 Hz anti-damping well under V295's. |
| 2 | **B0r** | **81** | 191 / 1 × 144 / 0 | Same skeleton with the held-rate D: 15 B smaller and in the flown V295/C1 D class. 0 fails. Loses to D2a only on 13 Hz anti-damping (−0.58 vs V295 −0.47). |
| 3 | A1-zero-cave (**+B2 mandatory**) | 73 | 79 / 0 / 0 | Fewest bytes by 2.5×: no cave, all in-place, re-key liveness verified here. But it FAILS goal turn-hold (0.88 freq, 0.79 own time at 19 m/s), has no I-freeze, and as written it omits the B2 interlock. |
| 4 | B1-robust-gaincut | 72 | ≈185 / 1 × 138 / 0 | Verified C1r2 cave code. 13 ms_free fails (34.1°, undeclared, stable). Dominated by B0r: same structure, refit to the full set. |
| 5 | D1b | 72 | 204 / 1 × 160 / **1** | Best 5–25 Hz damping. Costs one RAM word, a D scale that is BELIEF across angle (×0.83–1.0), and a one-tick DCL glitch on any accumulator re-reference. |
| 6 | D2c | 69 | 242 / 1 × 198 / 1 | Feedback lead, no setpoint kick, +40 B over D2a for +11–20 % stiffness. |
| 7 | D2b | 68 | 246 / 1 × 202 / 1 | Best goal metric (0.967). Largest cave of the passing set; ×2 P kick on setpoint steps. |
| 8 | A2-ki-cave (**+B2 mandatory**) | 64 | ≈183 / 1 × ~100 / 0 | Smallest cave. It was **never assembled** (~100 B BELIEF), has no I-freeze, and 3 ms_free fails (38.3°). |
| 9 | D1a | 60 | 185 / 1 × 144 / 0 | Fewest in-place bytes (17). Fails its own texture bar, the goal metric (0.944), and release lurch (to 20.5°). |
| 10 | D3b | 60 | 200 / 1 × 166 / 0 | A fresh inner operand through the bail is fail-safe, but the goal metric is 0.894 (FAIL). |
| 11 | D3a | 57 | 199 / 1 × 166 / 0 | Thinnest GM (6.3 dB), goal metric 0.913 (FAIL). |
| 12 | D1c | 55 | 232 / 1 × 188 / 1 | Texture 5.4 counts (FAIL). Dominated by D1b. |
| 13 | B3-noI-forkDC | 51 | ≈159 / 1 × ~114 / 0 | Small, but the cave is unassembled. Turn-hold 0.46 (FAIL), −4.5° override-release overshoot, and the fork's integral becomes load-bearing for stability. |
| — | B2-freshD-lead | 51 | ≈183 / 1 × 138 / 0 | **DISQUALIFIED AS WRITTEN:** unguarded `gp-0x6abe` read, so a 0x7FFF sentinel rails D (§2.1). 18 ms_free fails. |
| — | CGF-1 | 47 | ≈189 / 1 × 144 / 0 | **DISQUALIFIED AS WRITTEN:** the same unguarded 0x7FFF path, plus 35 fails down to 17.8° on ms_free, undeclared and outside R3. |
| — | CGF-2 | 36 | ≈217 / 1 × ~172 / 0 | **DISQUALIFIED AS WRITTEN:** inherits CGF-1's defects; the FF block is unassembled. |
| — | CGF-1b | 18 | ≈241 / 1 × ~196 / 0 | **DISQUALIFIED:** breaches the 20 Hz ceiling at NOMINAL across the whole grid (4 760 fails). Its cave calls a function that clobbers live r10, r12, r14 and r16. |
| — | E-none-1, E-none-2 | 0 | — | **DISQUALIFIED:** no design was produced (designer halted). |

**On my lens alone (no goal component), A1+B2 ranks first:** 79 B, zero caves, every byte EVIDENCE-grade, and the mirror
is Honda's own LERP with a different key. It does **not** meet Priority 1: highway turn-hold fails, declared as its miss
M1. **D2a and B0r are statistically tied** (82 vs 81). D2a buys 13–20 Hz damping for 15 B. B0r keeps the D in the flown
held-rate class, whose liveness is the easier on-car read.

**No candidate is shown UNSTABLE by the common scorer.** Every low PM is a positive PM. The scorer's exact monodromy
spot-checks give ρ < 1, and CGF's own exact poles over its report tier (ms_free included) give 0 unstable. So no
disqualification above rests on stability. They rest on fault paths, hard-gate breaches at the nominal member, or the
absence of a design (§3).

---

## 1. What I verified myself this session (the crux of every decision-bearing finding)

| # | claim | method | result |
|---|---|---|---|
| V1 | `gp-0x6abe` is written **0x7FFF** whenever the motor rate `gp-0x4f50` is outside ±13000 (`(x + 13000) > 26000` unsigned). In the valid branch it is the EMA `>>10`, bounded by ±13000. | Ghidra `decompile_function FUN_00041464` (stock): the `bVar2` branch writes `*(gp-0x6abe) = 0x7fff` and `*(gp-0x4cc2) = 0x7fff` | **EVIDENCE** |
| V2 | The HELD cell `gp-0x6a56` is written **0** on the same condition, and is otherwise clamped to ±12000 | Ghidra `decompile_function FUN_0003f776` (stock) | **EVIDENCE** |
| V3 | B2/CGF's in-place E5′ (`0x29EE0 → 24 47 42 95 = ld.h -0x6abe[gp],r8`, Kd kept positive by stock `zxh r7`) has **no guard** between the load and the multiply. The D multiply runs at `0x29EE4 mul r7,r8,r0`, then `sar 3` and the DCL clamp at `0x29EE8..0x29F06`. On the sentinel, D = (48·32767)>>3 = 196 602 (CGF), or (41·32767)>>3 = 167 930 (B2), clamped to **+DCL = 10 240 S**, which is ≈ 1 670 T counts (×5346/32768), **≈ 68 % of the 2 461 rail**, in a fixed direction. The output lag reaches 63 % of that in ~32 ms. | V850 dry-run listing `0x29E40..0x29F80` (V294) plus arithmetic | **EVIDENCE** for the lane output. **BELIEF** for exposure: whether the motor is still driven while `gp-0x4f50` is invalid was not traced. |
| V4 | D2a's guard `addi 13000,r26,r8 ; movea 26000,r0,r13 ; cmp r13,r8 ; cmovh r0,r26,r26` (`1a 46 c8 32 / 20 6e 90 65 / ed 41 / e0 d7 36 d3`) is the same test FUN_0003f776 applies, so D = 0 exactly when the held cell would be 0 | Hand ISA decode: hw1 `0xd7e0` = reg2 r26, op 111111; hw2 `0xd336` = reg3 r26, sub-op 011001 (register form, reg1 = r0), cond 1011 = H | **EVIDENCE** (ISA). The form was also Ghidra-decoded in-image at `0x3539E` (D page). |
| V5 | **A1's re-key is live-safe.** On the new path `0x29CFC → 0x29D10 → 0x29D18 → 0x29D6A`: r6, r9, r10, r13 and ep are rewritten before any read; ep is rebuilt at `0x29DCC`; r2 is dead (both `cmovgt`/`cmovle` arms at `0x29DB8/0x29DC2` define it); r8's only old reader `0x29D6A mov r8,r16` is replaced by E4; r7 survives to `0x29DDA st.h r7,-0x697a` and the Kp LERP `0x29DE8 zxh r7`; r22 survives to the Kd LERP key `0x29E92 mov r22,r13`. | Ghidra dry-run listings `0x29CD4..0x29E40` and `0x29E40..0x29F80` (V294) | **EVIDENCE** |
| V6 | RK1 `a4 3f a3 95 85 0d` = `ld.bu -0x6a5d[gp],r7 ; br +0x10` (→ `0x29D10`). RK2 `95 2d` = `br +0x52` (→ `0x29D6A`). | Hand ISA decode: hw1 `0x3FA4` = reg2 r7, field 11110, b = 1, reg1 gp; hw2 `0x95A3` gives disp −0x6A5D. Br disp checked against the in-image `85 25` at `0x29E9E` (+0x40) and `95 0d` at `0x29CE4` (+0x12). | **EVIDENCE** |
| V7 | **r26 is dead from `0x29D7A` to its first write `0x29F76 mov r13,r26`.** This is the D-class operand handoff via `0x29EE0 mov r26,r8`. | Same two listings; every branch in the range stays inside it | **EVIDENCE** (confirms the D designer) |
| V8 | **r16 is not written between `0x29D7E` and `0x29E34 mov r16,r8`.** This is CGF-2's FF decouple premise. **r10 = DB is read at `0x29D7E cmp r10,r6`**, so any cave returning to `0x29D7E` must preserve r10. | Same listings | **EVIDENCE** |
| V9 | At A2's hook `0x29D9C`: r9 (the I excitation) is LIVE and read at `0x29DA8 mul r6,r9,r0`; r8 and r13 are dead (r13 written at `0x29DA0`); r7 must be preserved. A2's pseudo-listing touches only r6, r8 and r13, which is consistent. | Same listing | **EVIDENCE** for the registers. **BELIEF** for the cave bytes, which were never assembled. |
| V10 | **r12 is LIVE across the C1 hook:** it is read at `0x29DCC mov r12,ep`, `0x29DD2 mov r12,r9` and `0x29E6E mov r12,ep` as the selector base for the Kp/Kd records. r10 (DB) and r7 (Kp key) are live too. | Same listings | **EVIDENCE**. CGF-1b's `FUN_0003e600` call (clobbers r6–r16, ep) would corrupt all of these. |
| V11 | Scorer column check: D3a turn-hold **0.988**, D3b **0.970**. The 0.59 and 0.76 the scorer's prose calls "turn-hold" are the `Tr163` column. | `score_freq_summary.json` keys `turnhold` and `Tr163` | **EVIDENCE**. The scorer's table is right; its prose is wrong. |
| V12 | `gp-0x67fe ≠ 2` without B2: θ is forced to 0 while the PID keeps running through the 2.048 s fade with request still 1. P acts on E = 16·θ_sp, signed toward the setpoint ("held turn ⇒ pulled further in"). TRACE Verdict B2: **"NOT covered ⇒ gate needed"**. | `TRACE-2026-09-30-sentinel-downstream-and-angle-validity-gates.md` §4.2 (read) | **EVIDENCE** (tracer). The dominance of `0x2913A` over `0x29A48` is BELIEF there and EVIDENCE per the brief. |

---

## 2. The two fault paths that decide the bottom of the table

### 2.1 The unguarded fresh-rate read (B2, CGF-1, CGF-2, CGF-1b)

B2 and every CGF variant read `gp-0x6abe` **in place** at `0x29EE0`, and that load has no guard (V1, V3). CGF's hazard
table says "gp-0x6abe clamp ±13000 … D clamps at ~360 deg/s … none found". That is a misreading. ±13000 is the
**validity window**, and outside it the cell holds **0x7FFF**. B2's hazard list names the EMA corner and the sign, but
not the sentinel. The D designer saw the same 4-byte in-place form and **rejected it for exactly this reason** (D page
§3.1, "A pure in-place alternative … was rejected").

- **What it does:** for as long as the motor-rate fault lasts with the lane running, the lane delivers a fixed-direction
  term of up to ~1 670 T counts (68 % of the rail). That torque was not commanded by the driver-assist system.
  **EVIDENCE** for the lane arithmetic. **BELIEF** for exposure, because nobody has traced whether the FOC drive keeps
  delivering with `gp-0x4f50` invalid. Held-D (A1, A2, B1, B0r, B3) and D2a/D2b/D2c are safe by construction (V2, V4).
- **The fix costs 18 cave bytes and changes the structure:** load the operand in the cave, apply Honda's validity form,
  and hand it over in r26 (`0x29EE0 → 1a 40 00 00 = mov r26,r8 ; nop`). **That is D2a.** Re-admitting B2 or CGF-1 with
  the guard means D2a's cave with B2's or CGF's table. CGF's table then still fails ms_free (§3).

### 2.2 The omitted B2 interlock (A1, A2)

A's page lists `0x29A50 cmovne r0,r27,r8` (+4 B) as a "RECOMMENDED interlock add-on" and leaves it out of the 75-byte
A1. TRACE §4.2 says it is **needed** (V12). Without it, losing angle validity mid-engagement drives the wheel open-loop
toward θ_sp for up to 2 s. **I score A1 and A2 only as A1+B2 (79 B) and A2+B2.** Each is penalised on risk for omitting
B2 as written. Note the trade-off: adding B2 also adds the one less-certain byte every C1-class candidate already
carries (r27 dominance, r8 deadness; H6 on the built image).

---

## 3. Disqualifications, with cause

| id | cause | re-admissible? |
|---|---|---|
| **B2-freshD-lead** | §2.1: the unguarded 0x7FFF path delivers ≈ 68 % rail uncommanded torque on a motor-rate fault (EVIDENCE lane arithmetic, BELIEF exposure). Also 18 tier-A fails on ms_free (30.9°), undeclared but stable. | Yes, with D2a's guard. It then becomes a D2a-structure build with Kd_eff 24 and B2's table, which must be refit under ms_free. |
| **CGF-1** | §2.1, plus 35 GATE-2 fails, ms_free down to **17.8°/21.2°** at 9.25–13 m/s. These were undeclared, and the ring they would produce (fc ≈ 0.92 Hz at 11.9 m/s) lies **outside** CGF's only stop band R3 (≥ 12.5 m/s, 1.0–5.5 Hz). Stable per CGF's own exact poles, so this is not a stability DQ. | Yes, with the guard **and** a table refit under ms_free. That gives away the "+35–40 % highway gain" that is the design's whole point. |
| **CGF-2** | Everything in CGF-1, plus the ~28-B FF block is unassembled (BELIEF). It returns to `0x29D7E`, where r10 = DB must survive (V8), and nothing shows that it does. | Its FF idea is a graft (§5), not a candidate. |
| **CGF-1b** | Breaches the 20 Hz ceiling at the **nominal** member across the whole grid: M20 1.00×, L20 1.04× V295, 4 760/4 760 fails. Aged Re(T/ω)₂₀ is 1.03× V295. The designer claimed "M20 ≤ V295", which the scorer did not reproduce. The ~50-B cave is unassembled, and it calls `FUN_0003e600` (clobbers r6–r16, ep) while r7, r10, r12, r14 and r16 are live (V10). Its GATE-1 note proposes saving r25, which is not in that clobber set. Not time-simulated. | No, not as a contender: it needs its own table, assembly and a register-save proof. |
| **E-none-1, E-none-2** | No design (designer halted). | n/a |

**Not disqualified, flagged:** A1, A2, B1 and B2 fail the brief's literal ms_free single corner (PM ≥ 45°) without
declaring it. They are stable, and refitting the table to fix it changes zero bytes. B3, D1a, D1c, D3a and D3b fail goal
criteria their own designers **declared** (turn-hold, texture, goal metric). A pre-declared, quantified miss is
admissible under the brief, and each is scored down, not out.

---

## 4. The scoring, line by line

**Byte normalisation.** The designers count differently. CGF omits cal bytes (~24). B counts full instruction slots. D
counts bytes that actually change. I report CHANGED in-place code bytes + whole cave including its table + changed cal
bytes. Where a cave was never assembled, its size is the designer's estimate, marked ~.

| id | in-place | cave | cal | **total** | RAM | caves | CRC blocks | unassembled (BELIEF) bytes | mirror coverage |
|---|---|---|---|---|---|---|---|---|---|
| A1+B2 | 27 | 0 | ≤ 50 | **≈ 77–79** | 0 | 0 | 3 (main, cal 0xC6FFC, E5xxx), **no 0xC4FFC** | 0 | **best:** Honda's own LERP, different key |
| A2+B2 | 31 | ~100 | ≤ 50 | ≈ 181 | 0 | 1 | 4 | **~100** | new Q8 LERP, no byte-exact mirror yet |
| B1 | 23 | 138 | ~24 | ≈ 185 | 0 | 1 | 4 | 0 (C1r2 code, `c1_assemble`; D's H1 on the same code) | c1_lib.LaneC1F (byte-exact) |
| B2 | 21 | 138 | ~24 | ≈ 183 | 0 | 1 | 4 | 0 | harness ran B2 as a held-D proxy, so fresh D has no time mirror |
| B3 | 23 | ~114 | ~22 | ≈ 159 | 0 | 1 | 4 | **~72** (freeze removed) | LaneC1F with Ki = 0 |
| CGF-1 | 21 | 144 | ~24 | ≈ 189 | 0 | 1 | 4 | 0 | cgf_time lane |
| CGF-2 | 21 | ~172 | ~24 | ≈ 217 | 0 | 1 | 4 | **~28** | cgf_time |
| CGF-1b | 21 | ~196 | ~24 | ≈ 241 | 0 | 1 | 4 | **~50** + a call | freq only |
| B0r | 23 | 144 | 24 | **191** | 0 | 1 | 4 | 0 (ds_asm, H1 0/60 000, full diff "UNLISTED: none") | ds_lane == LaneC1F 0/40 000 |
| D1a | 17 | 144 | 24 | 185 | 0 | 1 | 4 | 0 | ds_lane |
| D1b | 20 | 160 | 24 | 204 | **1** | 1 | 4 | 0 | ds_lane + H1 |
| D1c | 20 | 188 | 24 | 232 | **1** | 1 | 4 | 0 | ds_lane + H1 |
| D2a | 20 | 162 | 24 | **206** | 0 | 1 | 4 | 0 | ds_lane + H1 |
| D2b | 20 | 202 | 24 | 246 | **1** | 1 | 4 | 0 | ds_lane + H1 |
| D2c | 20 | 198 | 24 | 242 | **1** | 1 | 4 | 0 | ds_lane + H1 |
| D3a | 15 | 166 | 18 | 199 | 0 | 1 | 4 | 0 | ds_lane + H1 |
| D3b | 16 | 166 | 18 | 200 | 0 | 1 | 4 | 0 | ds_lane + H1 |

"Unassembled 0" still means **BELIEF until Ghidra decodes the BUILT image (H5)** for every cave candidate. The D set is
far stronger than A2/B3/CGF on this axis. Its evidence is a two-pass assembler, 27 encoding-form controls against V295,
11 exact-byte Ghidra decodes of the same forms elsewhere in the image, an interpreter executing the assembled bytes
against the lane arithmetic (0/60 000 mismatches per cave, r25 unchanged), and a full diff with no unlisted byte.

**Subscores (Size / Verif / Risk / Gate = total):**

| id | S/25 | V/30 | R/25 | G/20 | **total** | the deciding lines |
|---|---|---|---|---|---|---|
| D2a | 16 | 25 | 22 | 19 | **82** | guard = Honda's form (V4); r26 handoff verified (V7); fresh-D liveness is not visible on the 50 Hz tap in one drive (D's own admission), so it rests on H5; pol = −1 baked in (record: constant over 17 983 frames) |
| B0r | 17 | 27 | 21 | 16 | **81** | flown held-D class; 0 fails; 13 Hz −0.58 vs V295 −0.47 (×1.2) is the 13–17 Hz-line risk; goal metric 0.958 thin |
| A1+B2 | 25 | 27 | 15 | 6 | **73** | 0 caves (V5, V6); no I-freeze (the V283 release-lurch class, bounded by ICL 4096 ≈ 660 T); B2 omitted as written; turn-hold 0.88 / 0.79 FAILS the goal (declared M1) |
| B1 | 17 | 25 | 21 | 9 | **72** | verified C1r2 code; 13 ms_free fails (34.1°, undeclared); goal 0.952 thin; dominated by B0r |
| D1b | 14 | 22 | 17 | 19 | **72** | 1 RAM (V289-flown word, static GATE 1); D frame BELIEF; no first-tick guard; `FUN_0003bcb2` re-reference has 7 callers |
| D2c | 10 | 22 | 19 | 18 | **69** | +36 B over D2a, 1 RAM; no kick |
| D2b | 10 | 22 | 17 | 19 | **68** | largest passing cave; ×2 P kick (step peak T 1 029 vs 787); 5–13 Hz ≈ B0r |
| A2+B2 | 20 | 17 | 15 | 12 | **64** | ~100 B never assembled; no freeze; B2 omitted; 3 ms_free fails |
| D1a | 18 | 26 | 11 | 5 | **60** | DCL saturates on the 0xE4 staircase; lurch 9.6–20.5°; 40–200 Hz content 35× B0r; goal metric 0.944 |
| D3b | 15 | 23 | 17 | 5 | **60** | E1′ exact bytes decoded at `0x5658C`; the sentinel latches STEER_STATUS 7 (fail-safe, but a nuisance until the key cycles); goal metric 0.894 |
| D3a | 15 | 22 | 15 | 5 | **57** | GM 6.3 dB; light_b ζ 0.005 (report); goal metric 0.913 |
| D1c | 11 | 21 | 15 | 8 | **55** | texture 5.4 counts (FAIL); D is garbage beyond 409.6° |
| B3 | 19 | 18 | 11 | 3 | **51** | ~72 B unassembled to save 24 B of code that is already inert at Ki = 0; fork τ_o < 1 s turns GATE 2 E unstable; −4.5° release overshoot; turn-hold 0.46 |
| B2 (DQ) | 17 | 22 | 4 | 8 | 51 | §2.1 |
| CGF-1 (DQ) | 17 | 23 | 3 | 4 | 47 | §2.1, §3 |
| CGF-2 (DQ) | 13 | 15 | 3 | 5 | 36 | §3 |
| CGF-1b (DQ) | 10 | 6 | 2 | 0 | 18 | §3 |

---

## 5. Grafts worth taking from the runners-up

1. **D2a's validity guard is MANDATORY on any read of `gp-0x6abe`** (18 cave bytes; V1–V4). It is the only thing that
   makes "fresh D" safe. Any future build that reads a fresh sensor cell must reuse the producer's own validity test.
2. **B2 (`0x29A50 e2 47 00 00 → e0 df 34 43`) is MANDATORY in A1/A2** (+4 B; V12).
3. **A1's speed re-key (RK1/RK2, 8 in-place bytes, liveness verified in V5/V6) as a zero-cave Kd(v) schedule on the
   winner.** D2a/B0r run a flat Kd. E4 already makes the map walk dead in every C1-class build, so RK1/RK2 apply
   unchanged. Re-key only the **Kd** record: the cave's G(v) already schedules P and I, and re-keying Kp too would
   double-schedule P. It needs its own GATE-2 run, and it repurposes the demand tap `gp-0x674b`, which then carries
   speed.
4. **CGF-2's P-only friction feed-forward**, as a separate later build. It is the only design on the panel that attacks
   "low-speed stick-slip gone", which every candidate otherwise declares as a miss. Its decouple premise is verified
   (V8). Size it from the inert 427-tap breakaway reads first, preserve r10, and assemble and interpreter-test it before
   any GATE.
5. **D's verification toolchain is the bar for whichever cave is cut:** two-pass `ds_asm`, the form controls, the H1
   interpreter (0/60 000), and `ds_bytes` full diff with "UNLISTED: none". A2, B3, CGF-2 and CGF-1b never reached it.
6. **Refit every A/B/CGF table under the ms_free-inclusive envelope.** It costs zero bytes. D's tables show the cost:
   about −23 % Kp_eff at 12 m/s.
7. **B3's own lesson, taken further:** if a no-I variant is ever wanted, ship the verified C1 cave with Ki cal = 0. Do
   not ship a modified, unassembled cave to save 24 B of code that Ki = 0 already makes inert.
8. A2's **jr-out / jr-back, no-RAM, no-link hook at the Ki load (`0x29D9C`)**. Use it if a speed-scheduled Ki is ever
   wanted without the G walk. Its registers are verified (V9).

---

## 6. Disagreements (scorer and designers), with cause

1. **Scorer prose vs scorer JSON (V11).** "D3a turn-hold 0.59 FAILS; D3b 0.76 short" reads the `Tr1.6-3` column. The
   actual turn-hold is 0.988/0.970. D3a/D3b still fail the goal **tracking** metric, by their own designer's numbers
   (0.913 and 0.894), so their rank does not change.
2. **CGF hazard table vs bytes:** "gp-0x6abe clamp ±13000 … none found" is wrong; the cell holds 0x7FFF when invalid (V1).
3. **B2 hazard list:** it omits the 0x7FFF path.
4. **A page vs TRACE §4.2:** B2 is called "optional"; the trace says "gate needed".
5. **CGF instrument vs D page:** CGF's "LIVE: fresh D … no 100 Hz staircase in the residual" cannot be read on a 50 Hz
   tap. The D designer says fresh vs held D "cannot be told apart in ONE drive on the 50 Hz tap". For every fresh-D
   candidate (D2a included), whether the edit is live is proven **statically** by the built-image decode (H5), not on
   the wire. Under the kit's "every build carries the instrument for its own edit", that is weaker than the held-D
   class, and D2a's verifiability is scored down for it.
6. **CGF-1b's GATE-1 note** (save r25) vs the stated clobber set: r25 is not clobbered. r7, r10, r12, r14 and r16 are
   live and would be (V10).
7. **Byte totals:** CGF's 169/197/221 omit cal bytes. B's 196/170 count unchanged instruction-slot bytes. Normalised
   figures are in §4.
8. **A1 "tier A min 58.5°" vs scorer 44.8° (ms_free).** The scorer wins; the member set explains the gap.

---

## 7. What this judgment cannot see, and what a FAIL would have looked like

- **No common time-domain scoring exists** (that scorer was halted). Stick-slip, release lurch, engage droop and texture
  are self-graded, under four different scenario definitions, and are not comparable across designers. Where my scores
  use time numbers, it is only a designer reporting its own failure.
- **Everything above ~8 Hz is model.** The 13–20 Hz advantages of D2a/D1b are EVIDENCE in the model and BELIEF on the
  plant.
- **Exposure for §2.1 is BELIEF.** If a trace shows the FOC drive stops delivering the moment `gp-0x4f50` goes invalid,
  B2/CGF-1's risk falls to a transient. The guard still costs only 18 B, so the conservative call stands.
- **Written before scoring, as a FAIL for this judge:** any candidate with an uncommanded-torque fault path, an
  unassembled cave presented as final, a live register clobbered at a hook, or a hard-gate breach at the nominal member
  → disqualify or rank last. Each of these fired at least once (§3).
- **Flight prerequisites, whichever candidate wins (not waived):**
  - H5: Ghidra decode of the BUILT image, including the D operand and its sign.
  - H6: B2 dominance / r8 deadness and r25/r14 liveness on the built image.
  - H8: every CRC recomputed (main, 0xC4FFC, 0xC6FFC, E5xxx).
  - V1: re-header the revert `.rwd` files (A16A).
  - The adversarial pass on the built image, with "do not flash" reachable.
