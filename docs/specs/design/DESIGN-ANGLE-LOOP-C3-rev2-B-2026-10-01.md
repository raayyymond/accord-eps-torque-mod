# DESIGN C3 rev2-B — angle-loop, every C3-r1 refutation resolved (2026-10-01): PRIMARY C3B-P, FALLBACK C3B-F

**Status: DESIGN ONLY.** Nothing built, flashed or sent; the fork was not touched; no `.rwd` or image was written.
Ghidra was used read-only (`disassemble_bytes dry_run:true`, `run_script_inline dry_run:true`, `list_open_programs`) on
stock `code.bin` and the open V294 program (code-identical to V295 except cal `0xC63EA` and its CRC); nothing was saved.
Python is the `bin_decompile` env. Every byte-level number is read from the V295 image (sha `5c044d65…`) or executed by
the panel-2 common scorers' own interpreters.

**Author:** REVISER 2 of 2 (independent), a subagent of the orchestrator `main`.

**What this page is.** Design C3 (`DESIGN-ANGLE-LOOP-C3-2026-10-01.md`) was REFUTED by three independent lenses. This page
takes C3's structure and applies the SMALLEST set of edits that resolves **every** finding — each either by a design
change **re-scored on the common scorers run unchanged** (`panel2/score_freq.py`, `panel2/score_time.py`) and the
refuters' own scripts, or by a **pre-declared, quantified miss with a covering stop band**. It delivers **C3B-P (PRIMARY)**
and **C3B-F (FALLBACK)**.

Every decision-bearing claim is marked **EVIDENCE** (method given) or **BELIEF**. Code is cited by address or grep string,
never line number.

**Scripts** (`analysis-2020accord/studies/angle_loop/c3/rev2B/`, run with `python <script>`; caches in
`_scratch/angle_loop/c3-rev2B/`):

| script | what it does | output |
|---|---|---|
| `rb_table.py` | builds the GB-P / GB-F tables (G ≥ 512 everywhere) and proves the one-sided-quantum property is gone (N2) | `rb_table_out.txt` |
| `rb_build.py` | assembles the C3B caves (A3 + opposing-freeze sgn300 + GB table; flight adds the op-skip) and H1-checks the fresh cave bytes against `e2_asm.cave_ref` | `c3b_cave_*.hex`, `rb_build_out.txt` |
| `rb_gate2.py` | θ=0 GATE 2, the **operating-point** GATE 2 (refuter F1), and the rate-invalid PI-only loop (refuter F3), on the C3-r1 stability refuter's INDEPENDENT model, at a chosen Ki | `gate2_ki<N>.txt` |
| `rb_opbreak.py` | per-member operating-point GATE 2 (which members fail, and whether ρ ≥ 1) | `opbreak_ki<N>.txt` |
| `rb_explore_ki.py` | the largest flat Ki that passes every gated operating point, per speed | `explore_ki_C3-P.txt` |
| `rb_n1.py` | the outward / inward light-hand release lurch, θ vs setpoint bound vs the opposing-hand freeze (N1); CONTROL bit-exact vs `c3nl_sim.Lane` | `n1_lurch.txt` |
| `rb_time.py` | the goal time grid at Ki 20…56 (the Ki vs real-curve-hold / tracking trade) on `panel2/score_time.py` | `rb_score_time_tables.md` |
| `rb_final.py` | the FINAL C3B-P / C3B-F on **both** common scorers run unchanged (h1, the goal time grid, GATE 2) | `rbf_score_time_tables.md`, freq tables |

---

## 0. The answer in one page

### 0.1 What C3B changes over C3 (the resolutions)

C3B keeps C3's class exactly — a 1 kHz firmware **angle** loop in `FUN_00028ea6`, Honda's rate sample as the D operand,
a speed-scheduled P, a bounded I, a guarded rate D for phase — and applies five edits, each tied to a refutation:

| # | edit | resolves | cost |
|---|---|---|---|
| R-Ki | **Ki 56 → 40** (cal `0xC63E6`) | **F1** (stability, refuting): the operating-point instability (ρ up to 1.0031) is removed — **0 exact ρ ≥ 1** anywhere; the residual PM shortfall is confined to the J≈2 ms_free family (declared). Still meets the goal's real-curve hold (0.94 / 0.92) and 15–22 tracking (0.98 / 0.98). | **0 code bytes** |
| R-G | **GB-P / GB-F tables** (6 knots, G ≥ 512 at every speed) | **N2** (nonlinear, refuting): Honda's I quantum `e5 = ((E·G)>>8)>>5` is one-sided when G < 512; GB keeps G ≥ 559 so e5 sees ≥ ±1 per 0.1° at every speed. Re-fitted under the full θ=0 R2 box (0 fails). | **0 code bytes** (table DATA) |
| R-S | **opposing-hand freeze, sgn 300** (E2-S block) | **N1** (nonlinear, refuting): the A3 bound limited the light-hand release lurch in ONE direction; an outward light hand wound the I and the release lurched 23.7°. The opposing-hand freeze stops the I unwinding when a > 300-count hand opposes the error → outward lurch 5.6° ≥ 12.5 m/s. | **+16 cave bytes** |
| R-skip | **op invalid → skip the lane** (`jr 0x2a164`, C3B-P only) | **F3** (stability): when the motor rate is invalid the D was 0 but the angle P+I kept running — an undamped, locally unstable PI loop. C3B-P skips the whole PID (the proven A2 epilogue) on an invalid rate → no torque path. Also closes bytes-lens **H-rate**. | **+2 cave bytes** |
| R-R3 | **R3\* widened to 0.25–5.5 Hz** (telemetry stop band) | **F2** (the outer-loop 0.31–0.47 Hz rings sat below R3\*'s old 0.5 Hz edge) and the declared curve-hold rings of F1 (0.45–0.9 Hz). | 0 bytes (telemetry) |

**Byte budget.** C3B-P flight cave **240 B** (C3-P 222 + 16 sgn + 2 op-skip); in-place 20 + cal 24 (Ki 56→40 is the only
cal that differs from C3-P). C3B-F flight cave **220 B** (C3-F 204 + 16 sgn; held D has no abe read, so no op-skip —
F3 declared). The +18 cave bytes buy the structural resolution of two **refuting** findings; the 0-byte alternative
(declare both) would ship a 23.7° outward lurch and a locally-unstable rate-invalid state, which is what got C3 refuted.

### 0.2 The two implementations

| | **C3B-P (PRIMARY)** | **C3B-F (FALLBACK)** |
|---|---|---|
| D operand | **fresh** 1 kHz motor-rate `gp-0x6abe`, Honda-guarded, Kd 48 | **held** 100 Hz motor-rate `gp-0x6a56` via E5, Kd 24 |
| speed table | GB-P (6 knots, G ≥ 559, fitted under the R2 box) | GB-F (6 knots, G ≥ 560) |
| integral | **Ki 40**, ICL 8192, A3 bound (θ-referenced, two slopes 26/102 T/deg + 1250 S, knee 12.5 m/s, low-speed cap 4096 S < 6 m/s) **+ opposing-hand freeze sgn 300** | the same |
| rate-invalid | **skip the lane** (`jr 0x2a164`) | D := 0 (Honda zeroes the held cell); PI-only ms_free-product ring **declared** |
| in-place set | E1 E2 B2 A2 E4 HOOK **OPH** V1 (= C3-P's) | E1 E2 B2 A2 E4 HOOK **E5a E5b** V1 (= C3-F's) |
| cave | `0xC4C00`, **240 B** (198 code + 42 table), sha `9a10cdc4ec75` | `0xC4C00`, **220 B** (178 + 42), sha `9de9365fa952` |
| pol = −1 dependence | yes (fresh D; R1 INVERTED catches it drive 1) | **none** (held rate carries pol like θ) |
| 13 Hz anti-damping vs V295 | 0.79× (≈ C3-P; Kd unchanged) | 1.9× — creep-grind band (declared M-C3B-13, R4 watch) |

### 0.3 Headline numbers, the common scorers run unchanged (EVIDENCE)

| metric | C3B-P | C3B-F | bar / ref | source |
|---|---|---|---|---|
| θ=0 GATE 2 (R2 box / strict) fails | **0 / 0** | **0 / 0** | 0 | `rb_final freq` (common scorer) |
| M20 ÷ V295 (κ1 / phys) · peak 5–30 Hz · GM↑ | 0.96/0.96 · −0.2 dB · 13.8 dB | 0.82/0.83 · +2.2 dB · 6.6 dB | ≤1 · ≤+3 · ≥6 | " |
| operating-point exact ρ ≥ 1 (F1) | **0** | **0** | 0 | `rb_gate2` (Ki 40) |
| real-curve hold min (r71b curves) | **0.94** | 0.92 | ≥ 0.90 | `rb_final time` (Ki 40) |
| tracking 8–15 / 15–22 / >22 (replay) | 0.979 / 0.964 / 0.989 | 0.981 / 0.957 / 0.987 | 0.95–1.05 | `rb_final time` |
| tracking 8–15 / 15–22 / >22 (clean) | 0.987 / 0.981 / 0.997 | 0.989 / 0.976 / 0.996 | 0.95–1.05 | " |
| turn-hold a ≤ 2.0 / a 2.5, min ≥ 8 | 0.98 / 0.98 | 0.98 / 0.98 | ≥ 0.90 | " |
| outward light-hand release lurch, max ≥ 12.5 | **5.6°** | ≈ 5.6° | ≤ 8° (C3: 23.7°) | `rb_n1` |
| inward light / firm lurch, b_lo×J_hi, max ≥ 8 | 3.9 / 2.9° | 3.9 / 2.9° | ≤ 8° | `rb_final time` |
| co-steer droop, max ≥ 8 (opposing freeze) | **0.9°** | 0.9° | (C3: 2.3°) | " |
| **every goal time criterion, fails ≥ 8 m/s** | **0** | **0** | 0 | " |
| G min over all speeds (N2) | **559** | 560 | ≥ 512 | `rb_table` |

**All non-ms_free credible members pass the operating-point GATE 2; the only shortfall is on the J≈2 ms_free family
(ms_free 21.2°, b_lo×ms_free 4.6°, b_q×ms_free 8.2°, all ρ < 1 — no divergence), which the held-out plant ident
disfavours (prefers J ≤ 0.5 at 10–15 m/s) and which friction masks in the time domain. It is DECLARED (M-C3B-F1) and
covered by R3\* 0.25–0.9 Hz.** (EVIDENCE: `rb_opbreak` Ki 40.)

### 0.4 Rulings this revision makes, and the ONE it escalates

1. **Ki 40, not lower and not 56.** A flat Ki cannot both pass the goal's real-curve hold (needs Ki ≳ 36) and clear the
   a2.0–2.5 operating-point margins on the J≈2 ms_free family (needs Ki ≲ 20). Ki 40 is the value that meets the goal
   with **zero operating-point instability** and the margin shortfall confined to the BELIEF-disfavoured ms_free family.
   A scheduled Ki (Ki ∝ G) would clear both but costs a second in-cave multiply and new liveness; it is a §9 follow-up,
   not spent here under *minimise*.
2. **The opposing-hand freeze (sgn 300) is in BOTH implementations** — it is the structural fix for the outward lurch
   (N1) and the common scorer already models it (`c2`). The A3 θ-bound is kept (the setpoint bound alone did **not** fix
   N1 and worsened the inward partial drag; EVIDENCE `rb_n1`).
3. **The op-skip is in the PRIMARY only.** The fresh cave already reads and guards `gp-0x6abe`, so the skip is +2 bytes.
   The held fallback has no abe read; adding one would cost ~14 bytes and partly undo its "no fresh read" character, so
   the fallback **declares** its rate-invalid PI-only ms_free-product ring (ρ 1.0017, a rare fault, covered by R3\*).
4. ⚠ **ESCALATED — bytes-lens F1 (the stock camera on a relay close) is NOT resolved in firmware by this revision and
   needs an orchestrator/operator ruling.** The F3 op-skip does not help it (the camera sends a VALID rate). Either the
   procedural mitigation (**camera LKAS OFF**, a flight prerequisite) is ruled acceptable for this hazard class, or a
   firmware interlock is built. §7 H-cam specifies the interlock option and its cost. **A reviser cannot make this
   ruling; it is the one finding this page leaves open.**

---

## 1. PRIMARY C3B-P — every byte

### 1.1 In-place code edits — IDENTICAL to C3-P (re-asserted against V295; Ghidra dry-run this session)

C3B-P's in-place set is byte-for-byte C3-P's: **E1** `0x28F4C` (`ld.h -0x6a56→-0x6a00`, x := θ), **E2** `0x28FA4`
(`subr→add`, r26 = s_old+s_new), **B2** `0x29A50` (`setfe r8 → cmovne r0,r27,r8`), **A2** `0x29A56` (`bne→be`, PID runs
iff ramp ≠ 0 ∧ r8 ≠ 0), **E4** `0x29D6A` (`mov/mulh → ld.h -0x69ae,r16`, sp := gp-0x69ae), **HOOK** `0x29D76`
(`shl 2/sub → jarl 0xC4C00,r6`), **OPH** `0x29EE0` (`mov r16,r8/sub → mov r26,r8 ; nop`, D operand = r26), **V1**
`0x1310D` (F181 `…A160 → …A16A`). The Ghidra dry-run at `0x29A48..0x29D7E` this session confirms the current V294 bytes
at every site match the "V295" column and that **r25 has a single writer** (`setfe r25` @`0x29A82`), so no edit disturbs
the dominance chain (EVIDENCE: `disassemble_bytes dry_run`, `run_script_inline` R25Scan).

### 1.2 The cave (`0xC4C00`, 240 B flight = 198 code + 42 table; 238 B score cave)

The cave is C3-P's **E2-A3 cave** (`shl 2 ; sub r26 ; fresh-op guard ; G walk ; E·G ; A3 policy ; FRZ/DONE`) with **three
additions**, each decoded by Ghidra dry-run (EVIDENCE) and executed by the common time scorer's own V850E2 interpreter
against `CandLane.cave_stage` (H1: **0 / 8000**, `rb_final h1`):

1. **the opposing-hand freeze** inserted in the policy block after the hard-freeze test (E2-S, `rb_build` POL_A3S `sgn=300`):
   ```
   movea 300,r0,r13 ; cmp r13,r8 ; bnh N2 ; ld.h -0x4f60[gp],r9 ; xor r16,r9 ; blt FRZ ; N2:
   ```
   r8 = |driver torque| (gp-0x4f68), r16 = E′, r9 = signed hand torque (gp-0x4f60). `xor r16,r9 < 0` ⇔ sign(hand) ≠
   sign(E′): a hand that pushes AWAY from the setpoint with |tq| > 300 freezes the I (so it cannot unwind into a lurch).
2. **the GB-P table** substituted for G-P48's rows (6 knots; §1.3).
3. **the op-skip** (flight cave only; Ghidra dry-run EVIDENCE, `rb_build`): the validity `cmovh r0,r26,r26` is replaced by
   ```
   0xC4C10  cmp   r13,r8
   0xC4C12  bnh   0xC4C18        ; op+13000 <= 26000 (rate valid): continue
   0xC4C14  jr    0x2A164        ; rate INVALID: skip the whole lane
   ```
   `0x2A164` is the SAME epilogue A2/B2 jump to (`jr 0x2a164` @`0x29A5C`/`0x29A64`): it writes `gp-0x6dd0 := 0`
   (Honda's I state), `gp-0x6cf8 := 0x7FFFFFFF` (the first-tick sentinel) and runs the output lag with S = 0, so the
   output decays and **no new torque path exists on an invalid rate** (EVIDENCE: `disassemble_bytes 0x2a164..0x2a1b0`).

The exits are C3-P's: `jr 0x29D7E` (freeze, past Honda's `sar 5`) and `jmp [r6]` → `0x29D7A` (normal, Honda's e5 = E′>>5).

### 1.3 Calibration cells — C3-P's, except Ki (and the table rows, which live in the cave)

| cell | addr | V295 | **C3B** | note |
|---|---|---|---|---|
| a | `0xC63E8` | 1011 | 0 | fb pole → pure 2-sample sum (= C3-P) |
| b | `0xC63EA` | 1050 | 8192 | s_new = 8θ (= C3-P) |
| C | `0xC62E6` | 1024 | 65535 | r26 clamp (= C3-P) |
| DB | `0xC62E4` | 4 | 0 | I deadband (= C3-P) |
| **Ki** | `0xC63E6` | 0 | **40** | **the one cal that differs from C3-P (was 56)**: PI corner 0.62 → 0.44 Hz |
| ICL | `0xC61BA` | 10240 | 8192 | I>>7 ≤ 8192 S (= C3-P; below V295's own 10240) |
| DCL | `0xC61B6` | 0 | 10240 | D clamp (= C3-P) |
| Kp Y ×5 | `0xE5384` | 960 | 112 | Kp flat (= C3-P) |
| Kd Y ×4 | `0xE5126` | 0 | 48 | D = (48·op)>>3 (= C3-P) |

**GB-P table** (in the cave at `0xC4CC4`, 7 rows LE `X u16 (230.4 cts/m/s), G u16, S s16 Q12`; EVIDENCE `rb_table`):
`(714, 1178, 1041) (1843, 1465, −6264) (2304, 760, −2033) (2707, 560, 1570) (4032, 1068, 2118) (6198, 2188, 0)
(0xFFFF, 2188, 0)`. Walk min **G = 559 @ 11.75 m/s** (G-P48 was 462). GB-F: `(714,1009,892) (1843,1255,−4753)
(2304,720,−1626) (2707,560,1097) (4032,915,1953) (6198,1948,0) (0xFFFF,1948,0)`, walk min **560**.

### 1.4 The loop, integer-exact Python (each line a byte or cal above; = the function the grid runs)

```python
def c3bp_tick(st, theta, sp69ae, abe, v6a5e, tq4f68, tq4f60, ramp, req, bvar2):
    if not (ramp != 0 and req == 1 and bvar2):                 # A2 + B2
        st.I8 = 0; st.Eprev = 0x7FFFFFFF; return lag_gate(st, 0)
    r26 = clamp(st.s_old + ((8192*theta)>>10), -65535, 65535); st.s_old = (8192*theta)>>10
    E  = s32((sp69ae << 2) - r26)                              # 16(theta_sp - theta)
    if ((abe + 13000) & 0xFFFFFFFF) > 26000:                   # cave 0xC4C10..14  [R-skip, F3]
        return skip_lane(st)                                   #   -> jr 0x2a164: I8=0, sentinel, output decays
    op = abe
    G  = walk(GB_P, v6a5e)                                     # [R-G, N2: G >= 559]
    Ep = s32(E * G) >> 8
    # --- integral policy: hard freeze, opposing-hand freeze, A3 bound, ramp ---
    frozen = (tq4f68 > 512)                                    # hard freeze
    if not frozen and tq4f68 > 300 and (s16(tq4f60) ^ Ep) < 0: # [R-S, N1] opposing-hand freeze
        frozen = True
    if not frozen:
        sh = 4 if (v6a5e <= 2880) else 6
        bound = (abs(s16(theta)) << sh) + 1250
        if v6a5e <= 1382: bound = min(bound, 4096)
        t = (st.I8 >> 10) if Ep >= 0 else -(st.I8 >> 10)
        if t >= bound or (ramp & 0x8000) == 0: frozen = True
    e5 = 0 if frozen else (Ep >> 5)
    I  = clamp((st.I8 >> 3) + ((e5 * 40) >> 3), -(8192<<7), 8192<<7)   # [R-Ki: Ki 40]
    P  = clamp((Ep * 112) >> 8, -15360, 15360)
    D  = clamp((48 * op) >> 3, -10240, 10240)
    S  = (I >> 7) + P + D ; st.I8 = I << 3
    return lag_gate(st, fade_and_clamp(S))
```

### 1.5 Overflow (EVIDENCE `rb_build` / `score_time` wraps = 0)

|E| ≤ 4·32767 + 65535; max GB G 2188; |E·G| < 2³¹; |48·op| ≤ 624 000 → DCL 10240; the opposing `xor r16,r9` and the
op-skip touch no new 32-bit product. No int32 wrap on the grid.

---

## 2. FALLBACK C3B-F — what differs from C3B-P

**In-place:** C3B-P's set without OPH, plus C1's E5 pair (`0x29EDE subr r0,r7 ; 0x29EE0 ld.h -0x6a56,r8` → held D).
**Cave (220 B):** C3B-P's **without the fresh-operand guard block and without the op-skip** (the held cave never reads
`gp-0x6abe`), carrying the GB-F table and the **same opposing-hand freeze sgn 300**. **Cals:** C3B-P's with **Kd 24**.
**Why fallback:** it removes the pol = −1 dependence (held rate carries pol like θ) and is C1's most-reviewed class, at
the cost of 1.9× V295's 13 Hz anti-damping (declared M-C3B-13). **F3 for the fallback is DECLARED**, not skipped: when
the rate is invalid, Honda zeroes the held cell so D = 0 while P+I run; the resulting PI-only loop is locally unstable
only on **b_lo×ms_free / b_q×ms_free** (19 of 2888 gated points, worst ρ 1.0017, the BELIEF-disfavoured J≈2 family),
a rare fault covered by R3\* (EVIDENCE `rb_gate2` doff, Ki 40).

---

## 3. H1 — the cave bytes execute as the loop the grid runs (EVIDENCE)

`rb_final h1` executes each **score** cave's assembled bytes with the common time scorer's own V850E2 interpreter
(`nl_cave.Cpu` + `Cpu2`) against `CandLane.cave_stage` — the exact function the time grid runs — over 8000 edge-heavy
cases (the 0x7FFF sentinel, validity edges ±13000/13001, |tq| at 300/512 ±1, signed hand words of both signs, the table
knots ±1, the 1382/2880 knees, a random register file; every non-scratch register and every other RAM cell checked
unchanged): **C3B-P 0 / 8000, C3B-F 0 / 8000**. The op-skip (flight cave) diverges from the score cave only on an
**invalid** rate; that path is decoded by Ghidra dry-run (§1.2) and its target `0x2A164` is disassembled, not simulated.
`rb_build` also runs e2_asm's H1 on the fresh score cave against `cave_ref` (the opposing-freeze + A3 reference):
**0 / 30000**.

---

## 4. GATE 2 — magnitude AND phase, in every loop (EVIDENCE)

### 4.1 θ = 0 (the brief's GATE 2), on the common frequency scorer and the independent refuter model

The integral policy (Ki, bound, opposing freeze) acts only through FREEZE states = the scorer's I-frozen ("PD") loop,
so C3B-P's linear PID row is GB-P's and C3B-F's is GB-F's. Over the R2 box (brief credible set + ms_free×{b_lo,b_q},
every member at hold ages 1–20, the 0.25 m/s grid + knots, the frame box κ 0.83/1/1.155 under FA, 0.83/1.155 under FB):

| | C3B-P | C3B-F | bar |
|---|---|---|---|
| **R2-box fails / R2-lit / strict / G-strict** | **0 / 0 / 0 / 0** | **0 / 0 / 0 / 1\*** | 0 |
| tier-A box / aged-strict min PM | 58.8° / 56.0° | 60.2° / 50.1° | 45° |
| tier-B box (excl. ms_free) min PM | 39.8° | 40.3° | 30° |
| ms_free×{b_lo, b_q} min PM (ring ζ) | 38.5° (ζ 0.148) / 40.8° (ζ 0.131) | 31.1° (ζ 0.123) / 36.8° (ζ 0.138) | 30° |
| min GM↑ / peak 5–30 Hz / max L20 ÷ V295 | 13.8 dB / −0.2 dB / 0.96 | 6.6 dB / +2.2 dB / 0.83 | ≥ 6 / ≤ +3 / ≤ 1 |
| M20 (κ 1 / physical κ 0.866) | 0.962 / 0.959 | 0.822 / 0.831 | ≤ 1.00 |

**EVIDENCE: `rb_final freq` (the common frequency scorer, imported unchanged; VALIDATE PASS, all 6 controls reproduce
the round-1 anchors exactly).** On this official pipeline C3B-P and C3B-F pass the brief's θ=0 GATE 2 with **0 R2-box and
0 strict fails** — and the ms_free products, which on P2 sit at 13.3° with ring ζ 0.03–0.05 (the creep-grind corner), are
lifted to 31–41° with ring ζ 0.12–0.15 (far better damped). The one `G-strict` = 1 on C3B-F is `b_lo×ms_free×tau6+h10`
= 29.9° (a designer-G *reported* ×tau6 product, not a brief-gated member). The refuter model reproduces these to
|ΔPM| 0.1° (`rb_gate2` Ki 40 §1).

### 4.2 The operating-point GATE 2 (refuter F1) — RESOLVED to a confined, declared miss

The refuter's F1 linearises the plant at the **curve operating point** `k·sech²(θ_op/sat(v))` (θ_op = SR·L·a/v²). At
C3's Ki 56 this was **linearly unstable** (ρ up to 1.0031) on several members. **At Ki 40 there is 0 exact ρ ≥ 1**, and
the PM shortfall is confined to the ms_free family (EVIDENCE `rb_opbreak` Ki 40; worst over a 1.0–2.5, frame, e, v ≥ 8):

| member (J) | C3B-P worst PM | C3B-F worst PM | ρ_max | fails? |
|---|---|---|---|---|
| nominal, J_lo, b_lo, tau0/6, mode13/20 (0.2) | 56.7–60.4° | 55.2–58.5° | 0 | **pass** |
| J_hi (0.5), b_hi (0.2) | 48.5–48.6° | 47.4–48.3° | 0 | **pass** |
| b_lo×J_hi, b_lo×tau6, J1.0, b_q, b_q×J_hi, b_q×J1.0, b_q×tau6 | 32.8–57.9° | 30.3–56.5° | 0 | **pass** (≥ 30) |
| **ms_free (≈2)** | **21.2°** | **17.8°** | 0.9959 | miss (bar 45) |
| **b_lo×ms_free (≈2)** | **4.6°** | **1.1°** | 0.9997 | miss (bar 30) |
| **b_q×ms_free (≈2)** | **8.2°** | **5.0°** | 0.9987 | miss (bar 30) |

**Declared M-C3B-F1:** the a2.0–2.5 curve-hold on the J≈2 ms_free family has PM 1–21° and rings at 0.45–0.9 Hz with
ζ 0.02–0.12, **but ρ < 1 (no divergence)**, the member is disfavoured by the held-out ident (prefers J ≤ 0.5 at
10–15 m/s), and the refuter's own integer lane with the identified friction shows these rings masked to ±0.1–0.6°.
**Covered by R3\* (0.25–0.9 Hz, ζ < 0.25).** Every J ≤ 1.0 member passes; this is a narrow BELIEF-grade worst case, not
the broad, instability-grade, UNdeclared shortfall that refuted C3.

### 4.3 GATE 1 (RAM) and the rate-invalid fail-safe (F3)

0 RAM words written (same as C3). New reads: `gp-0x4f60` (signed hand, for the opposing freeze — a read, in the same
tick Honda reads `gp-0x4f68`), plus C3-P's reads. The op-skip adds **no RAM write** — it routes to Honda's own skip
epilogue. **F3 (the rate-invalid PI-only loop)** is fully fail-safe on C3B-P (the lane skips) and declared on C3B-F.

### 4.4 Re(T/ω) at the PHYSICAL κ and ages 0–9 (refuter F4, resolved on the page)

The D operand (Kd 48 fresh / 24 held) is UNCHANGED from C3, so M20 and Re(T/ω) ≈ C3's. Per refuter F4 (`c3r1_retw.py`,
EVIDENCE), the page must state these at the **physical** κ 0.866 and at ages 0–9, not only κ 1 / ages 1–10:

| Hz | 5 | 13 | 20 |
|---|---|---|---|
| V295 (κ 0.866) | +2.13 | −0.41 | −0.71 |
| **C3B-P** (κ 0.866, ages 1–10) | −0.31 | −0.38 (**0.93×**, not 0.79×) | −0.39 (0.55×) |
| C3B-P (κ 0.866, ages 0–9) | — | −0.39 (**1.14–1.33×**) | — |
| **C3B-F** (κ 0.866) | −0.70 | −0.83 (**2.05×**, declared 1.9×) | −0.71 |

The 13 Hz anti-damping is thus **frame- and age-fragile**: ≈ V295 at the physical κ, slightly above it at ages 0–9.
Covered by R4 (any resulting 5–30 Hz line) and F7 (F7 > 0 covers 5–8 Hz). `rb_final freq` reports the common scorer's own
M20 / Re(T/ω) for the final tables.

---

## 5. Time gates — the goal's own criteria, on the common time scorer run unchanged (EVIDENCE)

`rb_time` (Ki 20…56) maps the trade; `rb_final time` (Ki 40) is the final run. P2 / E2-A3 reproduce the published
SCORE-TIME cells (controls). The goal's decided criteria at Ki 40, worst over members and band speeds:

| goal criterion | C3B-P | C3B-F | bar |
|---|---|---|---|
| tracking (replay) 8–15 / 15–22 / >22 | 0.979 / 0.964 / 0.989 | 0.981 / 0.957 / 0.987 | 0.95–1.05 |
| tracking (clean) 8–15 / 15–22 / >22 | 0.987 / 0.981 / 0.997 | 0.989 / 0.976 / 0.996 | 0.95–1.05 |
| turn-hold a ≤ 2.0, min 8–22 | 0.98 | 0.98 | ≥ 0.90 |
| turn-hold a 2.5, min 8–22 | 0.98 | 0.98 | ≥ 0.90 |
| real-curve hold (r71b), min | **0.94** | 0.92 | ≥ 0.90 |
| outward light-hand lurch, max ≥ 12.5 (N1) | **5.6°** | 5.6° | ≤ 8° |
| inward light / firm lurch, b_lo×J_hi, max ≥ 8 | 3.9 / 2.9° | 3.9 / 2.9° | ≤ 8° |
| co-steer droop, max ≥ 8 | 0.9° | 0.9° | (C3: 2.3°) |
| **goal time fails per band ≥ 8 m/s** | **0** | **0** | 0 |

**The Ki trade (EVIDENCE `rb_time`):** real-curve hold is 0.75 (Ki 20) → 0.86 (Ki 28) → 0.92 (Ki 36) → **0.94 (Ki 40)** →
0.98 (Ki 56); 15–22 tracking is 0.918 (Ki 20) → 0.953 (Ki 28) → **0.975 (Ki 40)**. The operating-point instability is
0 up to Ki ≈ 44 and appears (ρ > 1) only by Ki 56. Ki 40 is the value that clears the goal with 0 instability.

---

## 6. Pre-declared misses (each quantified, each with a covering stop band)

**Stop bands (rev2-A's, with R3\* widened):** **R3\*** — at any speed, a **0.25**–5.5 Hz oscillation in 0x14A or the 0x18F
rate that grows, or ≥ 4 cycles ζ < 0.25 → REVERT (the lower edge is dropped from 0.5 to 0.25 Hz to cover the outer-loop
and curve-hold rings, **F2** / F1). **R4** — a narrowband 5–30 Hz line absent on V282/V295 → REVERT. **R5** — ring > 0.5 %,
F7 > 0. **R9** — the operator's words.

| # | criterion | band | predicted | stop band | basis |
|---|---|---|---|---|---|
| M-C3B-F1 | GATE-2 margin at the curve operating point | ms_free family, a 2.0–2.5, 9.5–16.5 m/s | PM 1–21°, ring 0.45–0.9 Hz ζ 0.02–0.12, **ρ < 1**; J≈2 disfavoured by the held-out ident; friction-masked to ±0.1–0.6° | **R3\* 0.25–0.9 Hz** | EVIDENCE `rb_opbreak`, `rb_gate2` |
| M-C3B-F2 | outer-loop ring (a fork angle integral) | τ_o < 1 s | 0.31–0.47 Hz rings (refuter F2) | **R3\* ≥ 0.25 Hz**; **τ_o ≥ 1 s is a CHECKED fork-config prerequisite** | EVIDENCE refuter F2 |
| M-C3B-F3 (C3B-F only) | rate-invalid PI-only ring | all | ρ 1.0017 on b_lo×ms_free / b_q×ms_free (19/2888 pts), rare fault; C3B-P skips the lane | R3\* | EVIDENCE `rb_gate2` doff |
| M-C3B-13 (C3B-F) | no new 5–30 Hz line | ≥ 13 Hz | 13/15 Hz anti-damping 1.9–2.05× V295 (held D) | **R4, 10–17 Hz watch** | EVIDENCE model |
| M-C3B-F4 | Re(T/ω) at physical κ / ages 0–9 | 13 Hz | 0.93× (κ 0.866), 1.14–1.33× (ages 0–9) — not 0.79× | R4 | EVIDENCE refuter F4 |
| M-C3B-F5 | two-mass modal ζ vs V295 | 13–17 Hz | below V295 on 10 % (P) / 43 % (F) of stress points, max Δζ −0.034/−0.041; 0 unstable, no peak > +3 dB | R4 | EVIDENCE refuter F5 |
| M-C3B-N3 | dwell-then-jump small corrections | 8–10 m/s and > 22 m/s | 8–10: ≈ 300 events (P2-class); > 22: reduced vs C3 by G ≥ 512. Relative to V282 (not simulable) | R9; dwell rate vs r6c | EVIDENCE sim (goal's own grid) |
| M-C3B-N4 | tracking on gated time members | S-bend a1.5, bc / b_lo×J_hi, 16–17.5 m/s | the GB table's higher highway gain lifts C3's 0.940 toward 0.95; any residual on-car < 0.95 at 15–22 = FAILED | on-car tracking < 0.95 | EVIDENCE sim |
| M-C3B-N5 | windup overshoot on reversals | 9.5–14 m/s | the opposing-hand freeze + Ki 40 reduce C3's 14–20 % reversal overshoot; residual declared as a "jerk" class | R9 | EVIDENCE sim |
| M-C3B-N6 | road load at θ ≈ 0 (crown/crosswind) | 8–12.5 m/s | P carries the bound-capped excess with a steady error; the 300 T / 500 T cases give 1.2–3.9° at 8–15 m/s | **a steady hands-off error > 1° on a straight ≥ 8 m/s → REVERT** (extended from ≥ 12.5) | EVIDENCE sim |
| M-C3B-N7 | turn-hold while ACCELERATING out of a curve | 13–15 m/s | transient (~2 s) PI lag, min 1 s hold ≈ 0.86; does not trip the 60 s on-car definition | R9 ("runs wide accelerating out of a curve") | EVIDENCE sim |
| M-C3B-N8 | aged-sensor lurch | ≥ 8 m/s | aged (+h10) light / firm lurch ≈ 4.9 / 3.8°, under the 8° bar | — | EVIDENCE sim |
| M-C3B-6/7/8 | low-speed release / hold / stick-slip | < 8 m/s | inherited from C3 (A3 cap); low-speed stick-slip unchanged (the friction frontier, met by no candidate) | R9 | EVIDENCE sim |
| inherited | F5 camera, pol = −1 (C3B-P), the FB frame | — | §7 / §0.4 ruling | procedure + fork gate; R1 INVERTED drive 1 | — |

---

## 7. Hazards and fail-safe paths (the delta from C3)

| # | path | C3B behaviour | fails safe? |
|---|---|---|---|
| **H-rate** | motor rate invalid (`gp-0x6abe` = 0x7FFF or ±out of ±13000) | **C3B-P: the cave `jr 0x2a164` → the whole PID is skipped, output decays** (the A2 epilogue). C3B-F: D = 0 (held cell), PI-only, the ms_free-product ring declared (M-C3B-F3). | **C3B-P: fully (resolves refuter F3 + bytes H-rate).** C3B-F: declared |
| H-ovr | override / outward light hand (N1) | the hard freeze > 512, the **opposing-hand freeze > 300**, the A3 bound, ICL 8192, fade; outward release lurch ≤ 5.6° ≥ 12.5 m/s | bounded; M-N1 resolved |
| **H-cam** | **the stock camera's 0xE4 on a relay close** (comma off, Honda LKAS on) | the firmware cannot tell the camera's command from an angle setpoint; the F3 op-skip does NOT help (the camera sends a valid rate). | **NO — not fail-safe in firmware. ESCALATED (§0.4).** Mitigation today: **camera LKAS OFF (FLIGHT PREREQUISITE)** + the fork B3 gate + A2-skip on request 0. **Firmware interlock option:** gate the lane on `gp-0x6803 == 2` in the guard (+4–6 B, a new `ld.bu`); the camera sends field 0, so the lane would skip camera frames — **but `gp-0x6803 == 2` also arms the engage-SM direction-2 path (0.10 s ramp-in) and the `0xCBAE4` fade arm (×1.8–2.1 hand authority, friction-refuter item)**, so it is NOT free. A cleaner discriminator needs a byte-trace of the camera's own 0xE4 SET_ME field (TRACE open item #4). **Orchestrator/operator ruling required before flight.** |
| H-pol | the sign of C3B-P's fresh D | on this car pol = `gp-0x6752` = −1 (boot-static, V98). **C3B-F is pol-invariant.** | yes on this car; **FLIGHT PREREQUISITE: this image stays on this car**; re-prove pol; R1 INVERTED catches it drive 1 |
| H-tmo | the fork stops sending | last θ_sp held 510 ms → sentinel → A2 → ≈ 0.1 s decay; mid-motion wheel ≈ 2.4° | holds the last VALID command 0.51 s (= stock); declared M-C3B-12 |
| H-fork-tq | a torque-mode / zero-emitting fork on this image | reads torques (or 0) as angle setpoints; a 0 drives toward centre. | **bounded IFF** V1 `…A16A` + the fork's angle-loop key ship and the revert `.rwd`s are re-headered (bytes-F2). **Declare the zero-emitting sub-case.** |

**Flight prerequisites:** camera LKAS off (or the H-cam ruling) · the fork sends θ_sp on 0xE4 in the EPS 0.1°/count
frame, inactive output = θ_meas, **any fork angle integral at τ_o ≥ 1 s (CHECKED) and none below 8 m/s** · V1 `…A16A`
in carFw + the fork key · the revert `.rwd`s re-headered to list A16A · **this image is car-specific (pol = −1,
C3B-P only)**.

---

## 8. The instrument — one short drive (no new telemetry bit)

As C3 §8, with two additions that read the two new terms:
- **the opposing-hand freeze (N1):** in a deliberate **outward** 3 s light-hold (rest a hand ≈ 2–4° FURTHER into a curve,
  |0x18F| ≤ 500, then release), the I component (tap − c_P·e − c_D·ω, 1 Hz LP) **must stay flat within ≈ 200 T** and the
  release must NOT overshoot the setpoint toward centre by more than the §5 value + 2°. A ramp-then-lurch means the
  opposing freeze is not live. **The light-hold episode is now BIDIRECTIONAL** (one inward, one outward).
- **Ki (F1):** c_I / c_P ∈ [1.9, 3.6] s⁻¹ (≈ 2.8, down from C3's 3.9) — the lower PI corner is the F1 fix on the wire.

**REVERT:** R1 INVERTED · R2 |tap| ≥ 300 hands-off > 0.3 s · **R3\*** a **0.25**–5.5 Hz ring that grows or ≥ 4 cycles
ζ < 0.25 · R4 a 5–30 Hz line absent on V282/V295 (C3B-F: 10–17 Hz watch) · R5 ring > 0.5 % or F7 > 0 · R6 |θ − θ_sp| > 10°
hands-off > 0.5 s at > 8 m/s · R7 tap pushing toward 0° > 0.2 s after a request drop · R8 STEER_STATUS ≠ 0 or 0x14A b4
bits 0–2 ≠ 7 engaged · R9 the operator's words.

**The sentence a null licenses:** *"If c_I/c_P is 3.9 (not ≈ 2.8), Ki was not lowered — the build is C3, not C3B. If an
outward 3 s light hold still ramps the I or lurches on release, the opposing-hand freeze is not live. If a curve hold at
a2+ rings at 0.45–0.9 Hz, that is the declared ms_free margin (M-C3B-F1) — revert."*

---

## 9. Variants and the one follow-up (each a specific ruling)

- **C3B-P-sched (the scheduled-Ki follow-up).** Ki ∝ G (a second in-cave multiply at the I stage + saved G) would clear
  the ms_free operating-point margin AND the real-curve hold with no declared F1 miss. It costs ~+12 cave bytes and a new
  liveness claim at the I stage, so it is NOT spent here under *minimise*; it is the design to cut if the operator rules
  the ms_free-family curve-hold ring unacceptable. (BELIEF: it resolves F1 fully; not assembled.)
- **C3B-P-ICL12k** (0 bytes): ICL `0xC61BA` = 12288 for +0.012 replay tracking at 8–15 m/s; above anything r71b needs
  and above V295's 10240 clamp. Not for the first flight.
- **C3B-P-cam** (+4–6 B): the firmware `gp-0x6803 == 2` camera interlock (§7 H-cam), IF the orchestrator rules firmware
  over procedure — with its ×1.8–2.1 hand-authority cost to re-score on the friction harness.

---

## 10. What a FAIL looks like (any one = do not flash)

As C3 §10 (H1 byte-exact, H2 R2-box, H3 goal time gates, H4 GATE 1, H5 built-image Ghidra decode incl. the op-skip
`jr 0x2a164` and the opposing-freeze `xor`/`blt`, H6 A2/B2 dominance, H7 the table, H8 CRC, H9 F181, H10 pol), **plus**:
- **H-N1:** the BUILT image's outward 3 s light-hold release lurch > 8° at any speed ≥ 12.5 m/s.
- **H-F1:** any operating-point exact ρ ≥ 1 on ANY member (the declared miss is bounded margin, never divergence).
- **H-skip:** the cave's invalid-rate branch does not reach `0x2A164`, or reaches it with any RAM written in between.
- the mandatory **close-out adversarial pass** (≥ 3 independent agents, "do not flash" reachable) finds any
  decision-bearing defect.

---

## 11. How C3B differs from C3 and the recent arc

C3B is **C3's class** — the first firmware angle loop — with the three refutations closed by the smallest edits: a cal
(Ki), a table (GB), a known cave block (the opposing freeze), and a 2-byte branch (the op-skip). It is **not** a new
class. Against the arc: like every post-V29 success it is a GATED cave (GATE 1 0 RAM, GATE 2 magnitude+phase with the
operating-point linearisation the refuter added, a byte-exact mirror the H1 executes, the wire instrument on every term
including the two new ones, an adversarial pass reachable). The one item it leaves open — the stock-camera relay close —
is a HAZARD-CLASS ruling for the orchestrator, flagged here rather than papered over.

## 12. What this page did not do

- No image built → nothing decoded from a BUILT image (H5); the cave listings/H1 are on the assembled bytes, decoded
  dry-run.
- The **common frequency scorer run** (`rb_final freq`) confirms the θ=0 GATE 2 / M20 / Re(T/ω) on the common pipeline;
  its final table is written to `_scratch/angle_loop/c3-rev2B/freq/`.
- **bytes-lens F1 (camera) is ESCALATED, not resolved** — it needs the orchestrator/operator ruling of §0.4.
- κ is unmeasured (BELIEF); the A3 bound and the opposing freeze are κ-independent / sign-only by construction.
- Low-speed stick-slip "gone" is met by no candidate (the friction frontier).
- The mandatory close-out adversarial pass on the BUILT image and the Artifact (signal-flow + LERPs before/after) are
  build-time steps, not done on this design page.
