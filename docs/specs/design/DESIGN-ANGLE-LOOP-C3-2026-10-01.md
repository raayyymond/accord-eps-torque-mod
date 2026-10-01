# DESIGN C3 — angle-loop SYNTHESIS (2026-10-01): PRIMARY C3-P, FALLBACK C3-F

**Status: DESIGN ONLY.** Nothing was built, flashed or sent; the fork was not touched; no `.rwd` or image was written.
Ghidra was used read-only (`disassemble_bytes dry_run:true`, `run_script_inline` with `dry_run:true` = PseudoDisassembler,
`list_open_programs`) on stock `code.bin` and the open V294 program, which is code-identical to V295 except cal `0xC63EA`
and its CRC; nothing was saved. Python is the `bin_decompile` env. Every byte-level number was read from the V295 image
(sha `5c044d65…`) or executed by the panel-2 common scorer's own interpreter.

**Author:** the synthesis agent, a subagent of the orchestrator `main`.

**What C3 is.** The round-2 panel (five designers, 30 candidates, three judges, two common scorers) converged on one
graft and all three judges named it: **designer G's re-sized loop** (a fresh, guarded rate D at Kd 48, with G's speed
table re-fitted under the round-2 GATE-2 "R2 box") **carrying designer E2's integral policy** (ICL raised to 8192 plus
the angle-referenced I bound "A3"). The two halves are **byte-orthogonal** — G changed only table DATA over rev2-A's P2
code; E2's policy is a self-contained block ahead of that table — so the graft costs exactly E2-A3's cave. This page
**assembles** that graft, verifies it on BOTH common scorers run unchanged, and delivers it as **C3-P (PRIMARY)**, with a
pol-free held-D **C3-F (FALLBACK)** that the panel had scored only as a mirror (no hex) and that this page is the first to
assemble.

Every decision-bearing claim is marked **EVIDENCE** (method given) or **BELIEF**. Code is cited by address or grep string.

**Scripts** (all in `analysis-2020accord/studies/angle_loop/c3/`, run with `python <script>`; caches in
`_scratch/angle_loop/c3-synthesis/`, gitignored):

| script | what it does | output |
|---|---|---|
| `c3_common.py` | the ONE source of truth: the C3 implementations, their sources, the V295 anchors | — |
| `c3_build.py` | assembles every C3 cave from E2's assembler + G's table rows; CONTROL A (P2 reproduction) | `_scratch/.../c3_build_log.txt`, `c3_cave_<id>.hex` |
| `c3_bytes.py` | every in-place/cal byte applied in memory to V295, full diff, byte account, the delivered surface from the BUILT-in-memory image's own table | `_scratch/.../c3_bytes_out.txt` |
| `c3_score_time.py` | registers the C3 caves on **panel2/score_time.py (imported unchanged)**; `h1` (bytes vs the grid's own cave stage), `run` (the full 22-scenario grid, frame `vgr`), `report` | `c3_score_time_tables.md`, `_scratch/.../c3_time_summary.json` |
| `c3_score_freq.py` | registers the C3 specs on **panel2/score_freq.py (imported unchanged)** | `_scratch/.../freq/score_freq_tables.md` |

---

## 0. The answer in one page

### 0.1 The two implementations

| | **C3-P (PRIMARY)** | **C3-F (FALLBACK)** |
|---|---|---|
| D operand | **fresh** 1 kHz motor-rate `gp-0x6abe`, Honda-guarded (`op+13000 ≤ 26000`), Kd 48 | **held** 100 Hz motor-rate `gp-0x6a56` via the in-place E5 pair, Kd 24 |
| speed table G(v) | G-P48 (6 knots, fitted under the full strict R2 box) | G-F24 (6 knots, same discipline) |
| integral policy | ICL 8192 + the **angle-referenced I bound A3** (two slopes 26/102 T/deg + 1250 S, knee 12.5 m/s; low-speed cap 4096 S below 6 m/s) | the same A3 block |
| in-place set | E1 E2 B2 A2 E4 HOOK **OPH** V1 (rev2-A P2's) | E1 E2 B2 A2 E4 HOOK **E5a E5b** V1 (rev2-A F2's) |
| cave | `0xC4C00`, **222 B** (180 code + 42 table), sha `dd131c6985a1a59a` | `0xC4C00`, **204 B** (162 code + 42 table), sha `237306b2b342d1fc` |
| bytes written | **266** (in-place 20 + cal 24 + cave 222), **RAM 0** | **251** (in-place 23 + cal 24 + cave 204), **RAM 0** |
| GATE 2 (R2 box) | **0 fails** (= G-P48, EVIDENCE) | **0 fails** (= G-F24, EVIDENCE) |
| goal time criteria ≥ 8 m/s | **0 fails on all 4 members** (EVIDENCE, common time scorer) | **0 fails** (EVIDENCE) |
| the pol = −1 dependence | yes (fresh D; R1 INVERTED catches it drive 1) | **none** (held rate carries pol like θ) |
| 13 Hz anti-damping vs V295 | 0.79× (no worse than P2) | **1.9×** — the creep-grind band (declared M13, R4 watch) |

**Both pass every decidable goal time criterion in every band ≥ 8 m/s, on all four members, AND the R2-box GATE 2.** No
single designer candidate in the panel did both — the time winners (E2's) ran P2's refuted small-signal loop (690 R2-box
fails), the frequency winners (G's) kept ICL 4096 and failed F1. C3 is the composition the two scorers pointed to.

### 0.2 Headline numbers, from the common scorers run unchanged (EVIDENCE)

| metric | C3-P | C3-F | P2 (ref) | source |
|---|---|---|---|---|
| tracking on r71b's real angle paths, replay, 8–15 / 15–22 / >22 | **0.980 / 0.987 / 1.006** | 0.981 / 0.983 / 1.006 | 0.892 / 0.855 / 1.001 | `score_time`, frame vgr |
| turn-hold min ≥ 8 m/s (a ≤ 2.0 / a 2.5) | 0.98 / 0.98 | 0.98 / 0.98 | 0.73 / 0.69 | " |
| real-curve hold min | 0.98 | 0.96 | 0.76 | " |
| light / firm release lurch, b_lo×J_hi, max ≥ 8 m/s | **4.1 / 3.2°** | 4.0 / 3.1° | 10.9 / 7.9° | " |
| hard-turn 1.6–3 Hz wheel rate / command's own, max ≥ 8 | **1.07** | 0.99 | 1.53 | " |
| texture, T 5–30 Hz under road noise, max ≥ 8 (bar 2.0) | 0.77 | 0.73 | 0.71 | " |
| R2-box / strict GATE-2 fails | **0 / 0** | **0 / 0** | 690 / 824 | `score_freq` |
| M20 (× V295) | 0.96 | 0.82 | 0.68 | " |
| Re(T/ω) 5 / 13 / 20 Hz, ages 1–10 | −0.05 / −0.37 / −0.43 | −0.53 / **−0.91** / −0.80 | −0.57 / −0.37 / −0.34 | " |
| tier A / tier B min PM (full frame box) | 51.7° / 34.2° | 50.7° / 34.8° | 42.3° / 26.1° | " |

### 0.3 The rulings this synthesis makes (each an orchestrator-level choice, with its reason)

1. **PRIMARY table = G-P48 (GATE-2 clean), not G-P48d.** C3-Pd (the G-P48d table) passes the linear tracking metric
   (0.961 vs G-P48's declared 0.935 on `b_q×ms_free`) but carries **166 R2-box fails, all on `b_q×ms_free`** (PM 17.0°,
   a 1.28 Hz ring ζ 0.055) whose only stop band (R3\*) catches the ring **after** the car shows it. GATE 2 is this kit's
   safety gate (CLAUDE.md). The cost of choosing G-P48 is a declared tracking miss on a **two-stress-corner report
   member** (b/4 with J 1.66–2.08, "J unidentified above 10 m/s"), and on the **real r71b paths** G-P48 is only −0.004
   behind G-P48d at 15–22 m/s (0.987 vs 0.991, EVIDENCE `op_merge`). **Pay 0.004 of real-path tracking for 0 R2-box
   fails.** C3-Pd is fully specified in §9.1 as the one-ruling variant if the orchestrator rules `b_q×ms_free` credible.
2. **ICL 8192, not 12288.** 8192 holds every r71b-sized curve (turn-hold 0.98 at a 2.5; EVIDENCE) and is **below V295's
   own clamp 10240** (EVIDENCE: byte read — authority stays inside a stock limit). 12288 adds ≈ 660 T of I authority no
   measured curve needs. It is 0 bytes to add later (§9.2).
3. **A3 (the low-speed cap) is in the PRIMARY.** It makes the loop **release cleanly to the driver below 8 m/s** (release
   lurch back to P2's 10.6° on b_lo×J_hi, vs A2's 13.9°) — the "releases to the driver" hard constraint. Its price is that
   low-speed turn-**hold** returns to P2's 0.90–0.95 below 6 m/s (the goal gates hold only ≥ 8 m/s). **If the operator
   rules low-speed HOLD over the < 8 m/s release lurch, use C3-PA2** (A2, −18 B, §9.3): low-speed hold 0.998, < 8 m/s
   lurch 13.9°. This is the single most operator-dependent choice on the page; both are built and scored.
4. **F5 (the stock camera on a relay close): procedure, not the 6803 == 2 arm.** The `gp-0x6803 == 2` arm cuts engage
   droop a third but makes the lane push **×1.8–2.1 harder against a firm hand** (the `0xCBAE4` fade arm) and needs the
   fork to send a bit on every frame. The F5 route for C3 is **A2-skip on request 0 + the fork's B3 health gate +
   camera-LKAS-off by procedure (a FLIGHT PREREQUISITE)**. A firmware camera interlock (+20 B) is a separate safety
   follow-up (§7, H-cam).

---

## 1. PRIMARY C3-P — every byte

### 1.1 In-place code edits (each decoded by Ghidra dry-run this session; `c3_score_time.py`/`C3InPlace`)

Every V295 old byte was read from the open V294 program (code-identical) and asserted by `c3_bytes.py` before replacement.

| id | addr | V295 → C3 bytes | V295 → C3 instruction (Ghidra dry-run) | loop term |
|---|---|---|---|---|
| E1 | `0x28F4C` | `24 3f aa 95` → `24 3f 00 96` | `ld.h -0x6a56[gp],r7` → `ld.h -0x6a00[gp],r7` | x := θ (0.1° counts); the ±12000 bail now tests θ |
| E2 | `0x28FA4` | `89 d1` → `c9 d1` | `subr r9,r26` → `add r9,r26` | r26 = s_old + s_new = 8θ[n] + 8θ[n−1] |
| B2 | `0x29A50` | `e2 47 00 00` → `e0 df 34 43` | `setfe r8` → `cmovne r0,r27,r8` | r8 := (request == 1) ? bVar2 : 0 |
| A2 | `0x29A56` | `da 05` → `b2 05` | `bne 0x29A60` → `be 0x29A5C` | the PID runs iff ramp ≠ 0 ∧ r8 ≠ 0 |
| E4 | `0x29D6A` | `08 80 ed 80` → `24 87 52 96` | `mov r8,r16 ; mulh r13,r16` → `ld.h -0x69ae[gp],r16` | sp := gp-0x69ae (clamp(−4·raw)) |
| HOOK | `0x29D76` | `c2 82 ba 81` → `89 37 8a ae` | `shl 2,r16 ; sub r26,r16` → `jarl 0xC4C00,r6` | the hook (r6 = 0x29D7A on entry) |
| OPH | `0x29EE0` | `10 40 bb 41` → `1a 40 00 00` | `mov r16,r8 ; sub r27,r8` → `mov r26,r8 ; nop` | D = (Kd·op) >> 3, op = r26 (the cave's fresh operand); Kd from `zxh r7` @0x29EDE, unchanged |
| V1 | `0x1310D` | `30` → `41` | data: F181 `39990-TVA,A160` → `…,A16A` | the fork interlock string |

**EVIDENCE (Ghidra PseudoDisassembler, dry-run):** every new encoding decodes exactly as the "C3 instruction" column
states; the current V294 bytes at every site match the "V295" column. r26 is written by the cave (the D operand); r25 and
r14 are never written in the hook→0x2A1E6 range (rev2-A's §1.1 EVIDENCE, re-asserted). The hook `jarl` displacement is
`+0x9AE8A` and reproduces the flown V112 hook encoder.

### 1.2 The cave (`0xC4C00`, 222 B = 180 code + 42 table), decoded by Ghidra dry-run

Every instruction below is the Ghidra PseudoDisassembler reading of the assembled bytes at `0xC4C00` (dry-run,
`c3_score_time.py`/`C3Cave`). The table pointer (`mov 0xc4cb4,r9`) locates the 7-row table at `0xC4CB4`.

```
0xC4C00  c2 82          shl   0x2,r16            displaced 0x29D76: 4*sp
0xC4C02  ba 81          sub   r26,r16            displaced 0x29D78: E = 4*sp - r26 = 16*(theta_sp - theta)
0xC4C04  24 d7 42 95    ld.h  -0x6abe[gp],r26    op = fresh 1 kHz motor-rate EMA                        [D OPERAND]
0xC4C08  1a 46 c8 32    addi  0x32c8,r26,r8      op + 13000 (Honda's validity form, FUN_0003f776)
0xC4C0C  20 6e 90 65    movea 0x6590,r0,r13      26000
0xC4C10  ed 41          cmp   r13,r8
0xC4C12  e0 d7 36 d3    cmovh r0,r26,r26         (op+13000) > 26000 unsigned (incl. 0x7FFF): op := 0    [D GUARD]
0xC4C16  e4 47 a3 95    ld.hu -0x6a5e[gp],r8     v (64 counts per km/h)                                 [G(v)]
0xC4C1A  29 06 b4 4c 0c 00  mov 0xc4cb4,r9       -> table
0xC4C20  e9 6f 01 00    ld.hu 0x0[r9],r13        X0
0xC4C24  ed 41          cmp   r13,r8
0xC4C26  cb 05          bh    0xC4C2E            v > X0 (unsigned): walk
0xC4C28  e9 47 03 00    ld.hu 0x2[r9],r8         G = G0 (clamp low)
0xC4C2C  b5 15          br    0xC4C52            -> APPLY
0xC4C2E  e9 6f 07 00    ld.hu 0x6[r9],r13        X(i+1)
0xC4C32  ed 41          cmp   r13,r8
0xC4C34  c3 05          bnh   0xC4C3C            v <= X(i+1): segment i
0xC4C36  09 4e 06 00    addi  0x6,r9,r9          next row (the 0xFFFF row ends the walk)
0xC4C3A  a5 fd          br    0xC4C2E
0xC4C3C  e9 6f 01 00    ld.hu 0x0[r9],r13        X(i)
0xC4C40  ad 41          sub   r13,r8             dv = v - X(i)
0xC4C42  29 6f 04 00    ld.h  0x4[r9],r13        S(i), Q12 signed
0xC4C46  ed 47 20 02    mul   r13,r8,r0          dv*S(i)
0xC4C4A  ac 42          sar   0xc,r8             >> 12
0xC4C4C  e9 6f 03 00    ld.hu 0x2[r9],r13        G(i)
0xC4C50  cd 41          add   r13,r8             G = G(i) + ((v-X(i))*S(i) >> 12)
0xC4C52  e8 87 20 02    mul   r8,r16,r0          E*G                                                    [SPEED GAIN on P and I]
0xC4C56  a8 82          sar   0x8,r16            E' = (E*G) >> 8
0xC4C58  e4 47 99 b0    ld.hu -0x4f68[gp],r8     |driver torque|                                        [1 HARD FREEZE]
0xC4C5C  20 6e 00 02    movea 0x200,r0,r13       512
0xC4C60  ed 41          cmp   r13,r8
0xC4C62  db 25          bh    0xC4CAC            |tq| > 512 (unsigned): freeze
0xC4C64  24 4f 00 96    ld.h  -0x6a00[gp],r9     th                                     [3 ANGLE-REFERENCED BOUND]
0xC4C68  e0 49          cmp   r0,r9
0xC4C6A  ae 05          bge   0xC4C6E
0xC4C6C  80 49          subr  r0,r9              |th|
0xC4C6E  e4 47 a3 95    ld.hu -0x6a5e[gp],r8     v                                                      [two-level slope]
0xC4C72  20 6e 40 0b    movea 0x0b40,r0,r13      2880 (= 12.50 m/s)
0xC4C76  ed 41          cmp   r13,r8
0xC4C78  bb 05          bh    0xC4C7E            v > 12.5 m/s: high slope
0xC4C7A  c4 4a          shl   0x4,r9             |th| << 4  (~26 T/deg)
0xC4C7C  a5 05          br    0xC4C80
0xC4C7E  c6 4a          shl   0x6,r9             |th| << 6  (~102 T/deg)
0xC4C80  09 4e e2 04    addi  0x4e2,r9,r9        + B = 1250 S (~200 T): the bound
0xC4C84  20 6e 66 05    movea 0x0566,r0,r13      1382 (= 6.0 m/s)                                       [LOW-SPEED CAP]
0xC4C88  ed 41          cmp   r13,r8
0xC4C8A  eb 05          bh    0xC4C96            v > 6 m/s: no cap
0xC4C8C  20 6e 00 10    movea 0x1000,r0,r13      4096 S (= P2's own ICL, ~655 T)
0xC4C90  ed 49          cmp   r13,r9
0xC4C92  ed 4f 36 4b    cmovh r13,r9,r9          bound = min(bound, 4096)
0xC4C96  24 6f 31 92    ld.w  -0x6dd0[gp],r13    I8 = 8*I (Honda's I state, READ only)
0xC4C9A  aa 6a          sar   0xa,r13            I >> 7 = the I's share of S
0xC4C9C  e0 81          cmp   r0,r16
0xC4C9E  ae 05          bge   0xC4CA2
0xC4CA0  80 69          subr  r0,r13             t = sgn(E')*(I >> 7)
0xC4CA2  e9 69          cmp   r9,r13             t - bound
0xC4CA4  ce 05          bge   0xC4CAC            winding past the bound: freeze
0xC4CA6  ce 6e 00 80    andi  0x8000,r14,r13     r14 = the ramp (0x2A1E6 multiplier)                    [4 RAMP-IN]
0xC4CAA  ca 05          bne   0xC4CB2            ramp full: integrate
0xC4CAC  00 32          mov   0x0,r6             FRZ: e5 := 0 -> Honda's exc = 0 -> I unchanged
0xC4CAE  b6 07 d0 50    jr    0x29D7E            skip 0x29D7A mov r16,r6 / 0x29D7C sar 5,r6
0xC4CB2  66 00          jmp   [r6]               DONE: return to 0x29D7A
0xC4CB4  TBL  (7 rows, LE: X u16 = gp-0x6a5e counts (230.4 per m/s), G u16, S s16 Q12)
            ca 02 9a 04 11 04   X  714 ( 3.10 m/s)  G 1178  S  1041
            33 07 b9 05 cc e5   X 1843 ( 8.00 m/s)  G 1465  S -6868
            00 09 b4 02 68 f6   X 2304 (10.00 m/s)  G  692  S -2328
            93 0a cf 01 4e 07   X 2707 (11.75 m/s)  G  463  S  1870
            c0 0f 2c 04 46 08   X 4032 (17.50 m/s)  G 1068  S  2118
            36 18 8c 08 00 00   X 6198 (26.90 m/s)  G 2188  S     0
            ff ff 8c 08 00 00   sentinel row
```

**Whole cave hex (`c3_cave_C3-P.hex`, sha256 `dd131c6985a1a59a…`, 222 B):** written by `c3_build.py`; it is
byte-identical to E2's assembled A3 cave (`e2_cave_A3.hex`) with G-P48's six table rows substituted (EVIDENCE,
`c3_build.py` cross-check), and its code portion is byte-identical to E2-A2/A3's (which the panel's bytes-risk judge
hand-decoded at cave offset 0x64 and H1'd). The exits: `jr 0x29D7E` (the freeze return, past Honda's `sar 5`) and
`jmp [r6]` → `0x29D7A` (the normal return, where Honda does e5 = E' >> 5).

### 1.3 Calibration cells (24 changed bytes; `c3_bytes.py`, each old byte asserted against V295)

| cell | addr | V295 | **C3** | what it is |
|---|---|---|---|---|
| a | `0xC63E8` | 1011 | **0** | fb pole: the 2-tap FIR → a pure 2-sample sum |
| b | `0xC63EA` | 1050 | **8192** | fb gain: s_new = 8θ |
| C | `0xC62E6` | 1024 | **65535** | r26 clamp (θ ≤ 409.6°) |
| DB | `0xC62E4` | 4 | **0** | I deadband |
| Ki | `0xC63E6` | 0 | **56** | Ki_eff = 56·G/256; the PI corner at 0.62 Hz |
| ICL | `0xC61BA` | 10240 | **8192** | I >> 7 ≤ 8192 S (≈ 1313 T); **below V295's own 10240** |
| DCL | `0xC61B6` | 0 | **10240** | D clamp |
| Kp Y ×5 | `0xE5384` | 960 | **112** | Kp_base, flat (selector 7) |
| Kd Y ×4 | `0xE5126` | 0 | **48** | D = (48·op) >> 3 |

Everything else is V295's. **Only ICL differs from rev2-A P2's cal set** (4096 → 8192); the table rows and the Kd record
(34 → 48) are the G-P48 data.

### 1.4 The loop, integer-exact Python (each line is a byte or a cal above)

```python
def c3p_tick(st, theta, sp69ae, abe, v6a5e, tq4f68, ramp, req, bvar2):
    if not (ramp != 0 and req == 1 and bvar2):                 # A2 + B2 (0x29A48..0x29A64)
        st.I8 = 0; st.Eprev = 0x7FFFFFFF; return lag_gate(st, 0)
    s_new = (8192 * theta) >> 10                               # 0x28F8E.. a 0: 8 theta
    r26 = clamp(st.s_old + s_new, -65535, 65535); st.s_old = s_new   # E2 0x28FA4 add
    E = s32((sp69ae << 2) - r26)                               # cave 0xC4C00/02: 16(theta_sp - theta)
    op = abe if ((abe + 13000) & 0xFFFFFFFF) <= 26000 else 0   # cave 0xC4C04..12: Honda's validity form
    G = walk(TBL_C3P, v6a5e)                                   # cave 0xC4C16..50
    Ep = s32(E * G) >> 8                                       # cave 0xC4C52/56: the speed gain, on P and I
    # --- the integral policy (A3): hard freeze, then the angle-referenced bound, then ramp ---
    frozen = (tq4f68 > 512)                                    # 0xC4C58..62
    if not frozen:
        sh = 4 if (v6a5e <= 2880) else 6                       # 0xC4C6E..7E (two-level slope)
        bound = (abs(s16(theta)) << sh) + 1250                 # 0xC4C64..80
        if v6a5e <= 1382: bound = min(bound, 4096)             # 0xC4C84..92 (low-speed cap, A3 only)
        t = (st.I8 >> 10) if Ep >= 0 else -(st.I8 >> 10)       # 0xC4C96..A0 : sgn(E')*(I>>7)
        if t >= bound: frozen = True                           # 0xC4CA2..A4 : wind past the bound -> freeze
        elif (ramp & 0x8000) == 0: frozen = True               # 0xC4CA6..AA : ramp not full -> freeze
    e5 = 0 if frozen else (Ep >> 5)                            # FRZ: r6=0 -> 0x29D7E | else 0x29D7A/7C
    I = clamp((st.I8 >> 3) + ((e5 * 56) >> 3), -(8192<<7), 8192<<7)  # 0x29DA4..C2, ICL 8192
    P = clamp((Ep * 112) >> 8, -15360, 15360)                  # 0x29E34..5C
    D = clamp((48 * op) >> 3, -10240, 10240)                   # 0x29EDE zxh r7 ; OPH mov r26,r8 ; mul ; sar 3 ; DCL
    S = (I >> 7) + P + D ; st.I8 = I << 3                      # 0x29F18.. ; 0x2A190
    return lag_gate(st, fade_and_clamp(S))                     # fade (floor 0.297), SCL, output lag 992/507, x ramp, x pol x 5346 >> 15, OCL
```

**EVIDENCE:** this is `nl_sim.Lane` with CandLane's C3-P column switches (G-P48 rows, dop fresh, Kd 48, ICL 8192, ARB_A3);
`c3_score_time.py h1` executes the assembled cave bytes against exactly this arithmetic (the function the grid runs):
**0 / 6000 mismatches** (§3).

### 1.5 Overflow budget (EVIDENCE, `c3_bytes.py` applied to G-P48's table)

|E| ≤ 4·32767 + 65535 = 196 603; max G over 0–60 m/s 2188; |E·G| ≤ 4.30·10⁸ < 2³¹. |48·op| ≤ 48·13000 = 624 000 → >> 3
→ DCL 10240. No int32 wrap on the grid (EVIDENCE: `score_time` wraps = 0).

### 1.6 Integrity regions the edit dirties (the builder's H8; NOT done here)

Full diff over `[0x13000, 0x100000)` = **264 bytes** (2 of the 222 cave bytes equal 0xFF). **UNLISTED: none** (EVIDENCE,
`c3_bytes.py`). Three regions: the **main block** (trailer `0xC4FFC`; holds `0x13100`/V1, the code edits and the cave),
the **cal page** `0xC6000..0xC6FFC`, and the **record block** holding `0xE5000`. The builder recomputes each and must pass
`verify_bootloader_crc.py` on the built image.

---

## 2. FALLBACK C3-F — every byte (what differs from C3-P)

**In-place code: C3-P's set without OPH, plus C1's E5 pair (23 changed bytes).**

| id | addr | V295 → C3-F bytes | instruction (Ghidra dry-run) | loop term |
|---|---|---|---|---|
| E5a | `0x29EDE` | `c7 00` → `80 39` | `zxh r7` → `subr r0,r7` | −Kd |
| E5b | `0x29EE0` | `10 40 bb 41` → `24 47 aa 95` | `mov r16,r8 ; sub r27,r8` → `ld.h -0x6a56[gp],r8` | D = (−Kd·x_held) >> 3, x = 8 counts/deg/s |

**The cave** (`0xC4C00`, 204 B = 162 code + 42 table, sha `237306b2b342d1fc`), decoded by Ghidra dry-run
(`c3_score_time.py`/`C3CaveF`): it is C3-P's cave **with the fresh-D operand block removed** (the five lines
`ld.h -0x6abe … cmovh`). The D now comes from the in-place E5 pair, so **the cave never writes r26** — it passes through
for the held-D multiply at `0x29EE0`. The G(v) walk, the speed gain, and the **identical A3 policy block** follow:

```
0xC4C00  shl 0x2,r16 ; sub r26,r16          E = 16(theta_sp - theta)   [r26 untouched below]
0xC4C04  ld.hu -0x6a5e[gp],r8 ; mov 0xc4ca2,r9 ; <the G(v) walk>       table at 0xC4CA2
0xC4C40  mul r8,r16 ; sar 0x8,r16                                       E' = (E*G) >> 8
0xC4C46  ld.hu -0x4f68[gp],r8 ; movea 0x200 ; cmp ; bh 0xC4C9A          [1 HARD FREEZE |tq|>512]
0xC4C52  ld.h -0x6a00[gp],r9 ; … ; shl 0x4/0x6,r9 ; addi 0x4e2,r9,r9    [3 ARB, two-level slope + B]
0xC4C72  movea 0x566 ; … ; cmovh r13,r9,r9                              [LOW-SPEED CAP 4096 below 6 m/s]
0xC4C84  ld.w -0x6dd0[gp],r13 ; sar 0xa,r13 ; … ; cmp r9,r13 ; bge 0xC4C9A   [the bound test]
0xC4C94  andi 0x8000,r14,r13 ; bne 0xC4CA0                              [4 RAMP-IN]
0xC4C9A  mov 0x0,r6 ; jr 0x29D7E                                        FRZ
0xC4CA0  jmp [r6]                                                       DONE -> 0x29D7A
0xC4CA2  TBL (G-F24 rows: (714,1009,892) (1843,1255,-5882) (2304,593,-1789) (2707,417,1539)
              (4032,915,1953) (6198,1948,0) (65535,1948,0))
```

**Cals:** C3-P's, except **Kd Y ×4 = 24** (D = −24 S per deg/s on the held rate x = 8 counts/deg/s = 3.85 T per deg/s).
**Bytes:** 23 + 24 + 204 = **251 written** (249 differ; UNLISTED none). Same three integrity regions.

**Why C3-F is the fallback and not the primary:** it removes C3-P's two dependencies — the fresh-D sign rests on
`pol = gp-0x6752 = −1` (fresh D only), and the fresh operand cannot be told from the held one on the 50 Hz wire in one
drive (§6). Its cave code is C1 rev 2's class, the most-reviewed in the kit. **The price:** its 13 Hz anti-damping is
−0.91 ≈ **1.9× V295's −0.47** in the creep-grind band (declared M13, R4 watch 10–17 Hz), where C3-P is 0.79× (no worse
than P2). Under Priority 1 (the goal's "no new 5–30 Hz line") above Priority 2, the fresh D wins primary. This matches
rev2-A's P2-vs-F2 rule and all three round-2 judges.

---

## 3. H1 — the cave bytes execute as the loop the grid runs (EVIDENCE)

`c3_score_time.py h1` executes each cave's **assembled bytes** with the panel-2 common time scorer's own V850E2
interpreter (`nl_cave.Cpu` + `Cpu2`), against `CandLane.cave_stage` — the exact function the time grid runs — over 6000
edge-heavy cases each (the 0x7FFF sentinel, the validity edges ±13000/13001, |tq| at every threshold ±1, signed hand
words, ramp 0/partial/0x8000/0xFFFF, the table knots ±1, the 1382/2880 speed knees, a random register file; every
non-scratch register and every other RAM cell checked unchanged):

| candidate | cave B | mismatches |
|---|---|---|
| **C3-P** | 222 | **0 / 6000** |
| **C3-F** | 204 | **0 / 6000** |
| C3-PA2 | 204 | 0 / 6000 |
| C3-Pd | 222 | 0 / 6000 |
| C3-P44 | 222 | 0 / 6000 |
| controls P2 / E2-A3 / G-P48 / G-F24 | — | 0 / 6000 each |
| **negative control** (P2 rows in the lane, G-P48 rows in the bytes) | — | **1498 / 1500** |

The negative control fails, so the byte substitution is real. **This is the first assembled, interpreter-checked listing
for the held-D + A3 combination (C3-F)**, which the panel had only as a mirror (BELIEF). BELIEF until Ghidra decodes a
BUILT image (the builder's H5) — §1.1/§1.2/§2 already decode the bytes dry-run.

---

## 4. GATE 2 — magnitude AND phase, in every loop the signal is in (EVIDENCE, common frequency scorer)

`c3_score_freq.py` imports `panel2/score_freq.py` unchanged and registers the C3 specs. The integral policy acts only
through FREEZE states, which are the scorer's I-frozen ("PD") loop; the linear PID loop is the skeleton's. So **C3-P's
entire T0 row is identical to G-P48's and C3-F's to G-F24's** — EVIDENCE that the integral policy does not move GATE 2
(the scorer's own finding F1, reproduced for the grafts). The R2 box = the brief's credible set + `ms_free × {b_lo, b_q}`,
every member at hold ages 1–10 AND 11–20, the 0.25 m/s grid + knots, and the frame box (κ 0.83/1/1.155 under FA, 0.83/1.155
under FB).

| | **C3-P** | **C3-F** | P2 (ref) | V295 (ref) |
|---|---|---|---|---|
| R2-box fails | **0** | **0** | 690 | — |
| strict fails (aged single corners at 45°) | **0** | **0** | 824 | — |
| tier A min PM (full frame box) | 51.7° (J_hi+h10 κ0.83) | 50.7° | 42.3° | — |
| tier A aged (strict) | 47.1° | 46.9° | 37.7° | — |
| tier B min PM, excl. ms_free× | 34.2° (b_q×J1.0+h10 FB κ0.83, 26.9 m/s; ring 1.89 Hz ζ 0.18) | 34.8° | 26.1° | — |
| ms_free× b_lo / b_q | 35.4 / 36.6° | 35.8 / 36.9° | 13.3 / 8.2° | — |
| unstable gated points (exact ρ) | 0 (max ρ < 0.9939) | 0 (< 0.9943) | 0 | — |
| M20 (× V295) | 0.96 (ages 1–20) / 0.976 (21–30) | 0.82 | 0.68 | 1.00 |
| L20 (× V295, worst) | ≤ 0.97 | ≤ 0.83 | 0.68 | 1.00 |
| peak \|T\| 5–30 Hz, gated | ≤ −0.3 dB | ≤ −0.8 dB | — | — |

**Re(T/ω) 5–25 Hz, worst over 1–35 m/s, ages 1–10 (T counts per deg/s, > 0 damps)** (EVIDENCE, the scorer):

| Hz | 5 | 7 | 10 | 13 | 15 | 17 | 20 | 25 |
|---|---|---|---|---|---|---|---|---|
| V295 | +2.46 | +1.24 | +0.09 | −0.47 | −0.66 | −0.77 | −0.82 | −0.76 |
| **C3-P** (= G-P48) | **−0.05** | −0.16 | −0.30 | −0.37 | −0.40 | −0.42 | **−0.43** | −0.42 |
| P2 | −0.57 | −0.44 | −0.39 | −0.37 | −0.36 | −0.35 | −0.34 | −0.31 |
| **C3-F** (= G-F24) | −0.53 | −0.70 | −0.86 | **−0.91** | −0.90 | −0.87 | −0.80 | −0.65 |

- **C3-P:** the Kd 34 → 48 step **removes most of P2's 5–7 Hz anti-damping** (−0.57 → −0.05 at 5 Hz: the F7 / 7 Hz class,
  M14), and its 13 Hz (−0.37, 0.79× V295) and 20 Hz (−0.43, 0.52× V295) are **no worse than P2 and well under V295**.
- **C3-F:** the held D carries the hold's lag and anti-damps 13 Hz at −0.91 ≈ **1.9× V295** — the creep-grind band.
  Declared M13, watch 10–17 Hz (R4).

**GATE 1 (RAM):** 0 RAM words written. New reads: C3-P adds `gp-0x4f68` (|hand|), `gp-0x6a00` (the angle the P sees),
`gp-0x6dd0` (Honda's I state, read before Honda's own read at `0x29DA4` in the same tick), a second `gp-0x6a5e`, and the
fresh `gp-0x6abe` (whose sole writer `FUN_00041464` runs earlier in the same 1 kHz pass — rev2-A H-fresh, EVIDENCE). C3-F
adds the same minus `gp-0x6abe`. No new state word, so no engage/disengage init to trace beyond Honda's own I reset
(A2/B2 zero I8 and set the sentinel on every skip).

---

## 5. Time gates — the goal's own criteria, on the common time scorer run unchanged (EVIDENCE)

`c3_score_time.py run 13` ran all 22 scenarios × 4 members (nominal, bc, F_hi, b_lo×J_hi) × 94 speeds in frame `vgr`
(the firmware's correction table applied to every motor-frame signal), with P2 / E2-A3 / G-P48 / G-F24 as same-batch
**controls that reproduce SCORE-TIME's decision-bearing cells** (P2 0.892/0.856, G-P48 0.892/0.835, E2-A3 0.986/0.993,
P2 light lurch 10.9°, E2-A3 5.8° — all match the published panel-2 cells).

**Goal time criteria, fails per band ≥ 8 m/s (worst over the 4 members):**

| cand | 8–10 | 10–12.5 | 12.5–15 | 15–22 | >22 |
|---|---|---|---|---|---|
| **C3-P** | pass | pass | pass | pass | pass |
| **C3-F** | pass | pass | pass | pass | pass |
| P2 | TRK/LURCH | TRK/LURCH | TRK/HOLD/LURCH | TRK/HOLD/RHOLD | pass |
| G-P48 | TRK/LURCH | TRK/LURCH | TRK/HOLD | TRK/HOLD/RHOLD | pass |

**The decided criteria, C3-P / C3-F, worst over members and the band's speeds:**

| goal criterion | C3-P | C3-F | bar |
|---|---|---|---|
| tracking (replay) 8–15 / 15–22 / >22 | 0.980 / 0.987 / 1.006 | 0.981 / 0.983 / 1.006 | 0.95–1.05 |
| turn-hold a ≤ 2.0, min 8–22 | 0.98 | 0.98 | ≥ 0.90 |
| turn-hold a 2.5 (r71b's sustained max ≤ 18 m/s), min 8–22 | 0.98 | 0.98 | ≥ 0.90 |
| real-curve hold (r71b's own curves), min | 0.98 | 0.96 | ≥ 0.90 |
| release lurch, light / firm, b_lo×J_hi, max ≥ 8 | 4.1 / 3.2° | 4.0 / 3.1° | ≤ 8° (rev2-B) |
| hard-turn 1.6–3 Hz wheel rate / command's own, max ≥ 8 | 1.07 | 0.99 | ≤ V282 (decided on car) |
| texture T 5–30 Hz under road noise, max ≥ 8 | 0.77 | 0.73 | ≤ 2.0 counts |
| 510 ms timeout mid-motion excursion, max ≥ 8 | 2.41° | 2.53° | declared |
| int32 wraps / sentinel push / detector reversals | 0 / 0.002° / 0 | 0 / 0.002° / 0 | 0 / ≤ 0.1° / 0 |

The r71b replay is r71b's own `gp-0x4f60` torque word fed to the lane; every tracking/hold number is the worse of clean
and replayed. The hard-turn ratio of **1.07** is the lowest among the goal-passing designs (E2-A3 1.43, P2 1.53) — C3-P's
re-sized D pulls the 1.6–3 Hz amplification down, the M9 direction. **Dwell-then-jump** is counted, not failed (the goal's
bar is relative to V282, not simulable): see §6 M-C3-1.

---

## 6. Pre-declared misses (each quantified, with the stop band that covers its ring)

**Stop bands (rev2-A's, inherited unchanged):** **R3\*** — at any speed, a 0.5–5.5 Hz oscillation in 0x14A or the 0x18F
rate that grows, or ≥ 4 visible cycles above 2× the pre-event rms (ζ < 0.10) → REVERT. **R4** — a narrowband 5–30 Hz line
in the 0x18F rate or the torque bar absent on V282/V295 → REVERT. **R5** — ring > 0.5 %, F7 > 0. **R9** — the operator's
own words.

| # | criterion (goal) | band | predicted, C3-P (C3-F where it differs) | stop band / revert | basis |
|---|---|---|---|---|---|
| M-C3-1 | small corrections ≤ V282 (dwell-then-jump, in-phase gain) | 12.5–22 m/s | **The GATE-2-clean table's cost.** ±0.3° 0.2 Hz in-phase gain at 15–22 m/s **0.31** (P2 0.79; C3-Pd 0.78); dwell-then-jump events +1° at 15–22 **15** (P2 0); nominal small corrections stay P2-class only on C3-Pd. | rev2-A M2/M4 (operator's words; dwell rate vs r6c). **If the operator reports highway micro-ratcheting on small corrections, switch to C3-Pd (§9.1).** | EVIDENCE sim (`score_time`) |
| M-C3-2 | tracking in every band ≥ 8 | report member `b_q×ms_free`, 13.5–19 m/s | linear 0.935 (nominal 0.951); on the real r71b paths −0.004 vs C3-Pd at 15–22 (0.987 vs 0.991 replay) | on-car tracking < 0.95 in the 15–22 band = FAILED | EVIDENCE freq + sim |
| M-C3-3 | 20 Hz gain ≤ V295 | 13–25 Hz | M20 0.96× (C3-P) / 0.82× (C3-F); 20–25 Hz anti-damping 0.85–1.00× V295's worst case (C3-P). Frame-exact (controller-only); the car's 20 Hz response is BELIEF. | **R4** | EVIDENCE model |
| M-C3-4 | 5–7 Hz damping (no F7) | all | Re(T/ω) 5 Hz −0.05 (C3-P, the least on the panel) / −0.53 (C3-F) where V295 damps at +2.46 | **R4** (5–8 Hz line); F7 > 0 | EVIDENCE model |
| **M-C3-5 (C3-F only)** | no new 5–30 Hz line | ≥ 13 Hz | 13 / 15 Hz anti-damping **1.9× / 1.8× V295** (age 0) in the creep-grind band | **R4 with a 10–17 Hz watch** | EVIDENCE model (plant > 8 Hz is BELIEF) |
| M-C3-6 | the loop releases to the driver (lurch) | **< 8 m/s** (not a goal band) | C3-P (A3): 10.6° b_lo×J_hi (P2 10.5°). **C3-PA2 (A2): 13.9°** — the A2 regression the cap repairs | R9 ("a lurch on letting go"); release overshoot > P2's + 2° at < 8 m/s | EVIDENCE sim |
| M-C3-7 | low-speed turn-hold (not a goal band) | ≤ 6 m/s | C3-P (A3): P2's 0.90–0.95 at a 1.0–1.5 (the cap re-arms P2's ICL below 6 m/s). **C3-PA2 (A2): 0.998** | operator words ("looser at low speed") | EVIDENCE sim |
| M-C3-8 | low-speed stick-slip "gone" (the frontier) | 3–7 m/s | **unchanged** from every candidate: ±1° stuck 42–90 %, 90 % on F_hi. No integral policy touches it (the friction-against-P class). | operator words | EVIDENCE sim; every candidate in the record misses this |
| M-C3-9 | road load at θ ≈ 0 (crown/crosswind) | any | the bound caps I at ≈ 200 T + slope·\|θ\|; P carries the excess with a steady error = excess/Kp_eff. **Never seen on r71b** (E2 §2.3: every steady hold ≥ 43 T under the bound) | a steady hands-off error > 1° on a straight ≥ 12.5 m/s → REVERT | EVIDENCE r71b; BELIEF other roads |
| M-C3-10 | engage droop | ≤ 10 m/s | 6.0° b_lo×J_hi at 8 m/s (C3-F 6.6°); the fork's ramp-in sets it, no I policy moves it | — | EVIDENCE sim |
| M-C3-11 | highway hold creep (dwell-then-jump in holds) | 13–30 m/s | ≈ 0.24 per hold creeps on the nominal friction world; 0 on bc (friction ×2). The rev2-A M11 class, roughly doubled by the higher highway gain. | — (operator's words) | EVIDENCE sim |
| M-C3-12 | the fork stops sending | all | last θ_sp held 0.51 s → sentinel → A2 → ≈ 0.1 s decay; mid-motion wheel 2.4° at 8–12.5 m/s | — | EVIDENCE tracer + sim |
| inherited | F5 (stock camera), pol = −1 (C3-P), the FB frame, aged hold in the time domain | — | §7 / not simulable | procedure + fork B3 gate; R1 INVERTED drive 1 | — |

---

## 7. Hazards and fail-safe paths (item by item; "fails safe" = no torque path without a valid, current setpoint)

| # | path | C3 behaviour | fails safe? | E/B |
|---|---|---|---|---|
| H-sen | 0xE4 fault sentinel 0x7FFF (request 0xFF) | A2 skips the PID; sim push 0.002° every member | **yes** | EVIDENCE guard bytes + sim |
| H-tmo | the fork stops sending | last θ_sp held 510 ms → sentinel → A2 → ≈ 0.1 s decay; \|T\| < 50 by +0.25 s | **holds the last VALID command 0.51 s** (stock does the same); M-C3-12 | EVIDENCE tracer + sim |
| H-rate | motor rate invalid (`gp-0x6abe` = 0x7FFF) | the cave applies Honda's own `op+13000 ≤ 26000` test → op := 0 → D = 0 (C3-P); the held cell is 0 (C3-F) | **yes**, no new exposure | EVIDENCE: H1 incl. 0x7FFF / ±13000 / 13001 |
| H-fresh | is `gp-0x6abe` current at the lane? (C3-P) | its sole writer runs earlier in the same 1 kHz pass (0x930 ⊂ 0xD30) | **yes** | EVIDENCE rev2-A decompile |
| **H-pol** | the sign of C3-P's fresh D | the lane output and θ and x are all ×pol; **the fresh D is not pol-invariant.** On this car pol = `gp-0x6752` = −1, boot-static (V98, 17 983 frames). **C3-F is pol-invariant** (held x carries pol like θ). | **yes on this car**; on a pol = +1 car C3-P's D would ANTI-damp | EVIDENCE decompile + V98. **FLIGHT PREREQUISITE: this image must not go to another car** (safety rule 5). R1 INVERTED catches it drive 1. |
| H-start | engage / first tick | stateless cave; I = 0 after any skip; I frozen through ramp-in; the fork sends θ_meas at engage. Sim droop ≤ 6.0° (6.6° C3-F) | yes; droop is M-C3-10 | EVIDENCE sim |
| H-drop | request drop / main off | A2: ≈ 0.1 s output-lag release | yes | EVIDENCE sim |
| H-ovr | override / release (V283's class) | freeze above \|tq\| 512 + the **angle-referenced bound** (κ-independent) + ICL 8192 + fade + the fork's O1. Release overshoot ≤ 4.1° light / 3.2° firm ≥ 8 m/s (bounded) | bounded; M-C3-6 | EVIDENCE sim; the ARB reads no torque word, so κ does not enter (E2's point) |
| H-auth | authority | P rails at 26–105° of error by speed; ICL 8192 ≈ 1313 T, **below V295's own 10240**; the sum and output clamps are V295's (rail 2461) | bounded by the existing clamps | EVIDENCE arithmetic |
| **H-cam** | **the stock camera's 0xE4 on a relay close** (comma off, Honda LKAS on) | the firmware cannot tell the camera's torque value from an angle setpoint; a camera `raw` becomes θ_sp = −raw/10° and the lane steers there with full P authority (sim: a phantom 30° setpoint → wheel 20–32° in 0.5 s at 12.5–27 m/s) | **NO — not fail-safe in firmware.** | **FLIGHT PREREQUISITE: camera LKAS OFF.** Plus the fork's B3 health gate and the A2-skip on request 0. A firmware camera gate (gate on `gp-0x6803 == 2`, +20 B) is a separate safety follow-up; it costs ×1.8–2.1 hand authority and is NOT in C3. |
| H-fork-tq | a torque-mode fork on this image | it would send torques as angles | **yes, IF** V1 (`…A16A`) and the fork's angle-loop key both ship, and the revert `.rwd`s are re-headered | EVIDENCE fw string; the fork half is BELIEF |
| H-bad | corrupt 0xE4 frames | up to 49 bad frames decoded as valid before the fault | bounded by the fork's own counter | BELIEF (decompile) |

**Fork prerequisites (FLIGHT PREREQUISITE unless marked):**
- **camera LKAS off** (H-cam) — FLIGHT PREREQUISITE.
- **the fork sends an angle setpoint in the EPS's own 0.1°/count frame on 0xE4** (θ_sp = −raw/10°, request 1), with its
  **inactive output = θ_meas** and a per-frame Δmax, and **any fork angle integral at τ_o ≥ 1 s and none below 8 m/s**
  (rev2-A §3.5; τ_o < 1 s is caught by R3\*) — FLIGHT PREREQUISITE.
- **V1 `39990-TVA,A16A` in carFw + the fork's angle-loop interlock key** — FLIGHT PREREQUISITE (H-fork-tq).
- the revert `.rwd`s (V295 and V294) re-headered to list A16A — FLIGHT PREREQUISITE.
- **this image is car-specific (pol = −1)** — FLIGHT PREREQUISITE, C3-P only; C3-F removes it.

---

## 8. The instrument — what one short drive must show (no new telemetry bit)

The loop is identified **within an episode** from signals already on the wire: 0xE4 (θ_sp = −raw/10 and the request),
0x14A (θ at 100 Hz), 0x18F (rate, driver torque = raw × 1.024, STEER_STATUS), the CAN 427 tap (T = gp-0x6b38, 50 Hz,
polarity +sign(cmd)), and the F181 string in carFw. Decode with the patched cereal (the slot-137 collision); take routes
from the device's realdata. **Design for ≈ 15–30 s of engaged frames in each of three bands: one > 22 m/s, one at
10–12.5 m/s (the dip), one at 5–8 m/s**, plus **one deliberate light-hand episode** (rest a hand lightly ≈ 2–4° toward
straight for 3 s at 10–15 m/s, keep the 0x18F word under ≈ 500, then let go).

**Regression** (hands-off, |0x18F| < 500 wire, request 1, ≥ 1.2 s after engage):
`tap = c_P·(raw − 10θ) + c_I·Σ(raw − 10θ)·dt + c_D·ω_18F + c0`.

| verdict | condition |
|---|---|
| **LIVE: the image** | carFw EPS = `39990-TVA,A16A` |
| **LIVE: the angle loop** | c_meas / c_raw ∈ [−1.25, −0.80] (the P acts on 16(θ_sp − θ)) |
| **LIVE: the speed schedule** | c_P within ±30 % of the band prediction, **and the dip** c_P(10–12.5)/c_P(5–8) ∈ [0.25, 0.60], **and** c_P(>22)/c_P(5–8) ∈ [1.05, 1.8] |
| **LIVE: the PI corner** | c_I / c_P ∈ [2.7, 5.1] s⁻¹ (≈ 3.9) |
| **LIVE: the re-sized D** | c_D ∈ **[0.45, 0.70]** tap per deg/s of ω_18F for C3-P (predicted 0.57, flat in speed), [0.38, 0.58] for C3-F — **resolvable from P2's 0.40 (0.30–0.50) in one drive** (G's instrument). The coefficient on θ̇_sp ≈ 0 (D is not on E). |
| **LIVE: the angle-referenced bound** | in the 3 s light-hold episode, the I component (tap − c_P·e − c_D·ω, 1 Hz LP) **stays flat within ≈ 200 T** of its pre-hold value; a ramp toward the clamp means the bound is NOT live |
| **LIVE: the frame** (which D operand) | the D coefficient is constant on ω_18F across \|θ\| < 25° and \|θ\| > 85° for both; it cannot separate C3-P's fresh operand from C3-F's held one (a 5.5 ms lag behind the 5 Hz output lag) — that is proven **statically** (H5 decodes `mov r26,r8` vs `ld.h -0x6a56,r8`) |
| **LIVE: A2** | after every request drop, \|tap\| < 20 within 0.15 s |
| **INVERTED → abort (R1)** | c_meas/c_raw > 0, **or c_D aiding (same sign as ω)** — for C3-P the second is the pol check (H-pol) |
| **NOT LIVE: cave skipped** | c_P ≈ 0.14 in every band |
| **NOT LIVE: wrong image** | \|c_meas\| < 0.2·\|c_raw\| and the tap reproduces V295's raw-only surface |

**REVERT (any one; written before the build):** R1 INVERTED · R2 \|tap\| ≥ 300 hands-off for > 0.3 s · **R3\*** a 0.5–5.5 Hz
ring that grows or ≥ 4 cycles ζ < 0.10 · **R4** a 5–30 Hz line absent on V282/V295 (C3-F: watch 10–17 Hz) · R5 ring > 0.5 %
or F7 > 0 · R6 \|θ − θ_sp\| > 10° hands-off > 0.5 s at > 8 m/s · R7 tap still pushing toward 0° > 0.2 s after a request drop ·
R8 STEER_STATUS ≠ 0 or 0x14A b4 bits 0–2 ≠ 7 engaged · R9 the operator's words (grinding, ratcheting, a jerk, a lurch on
letting go, "looser at low speed", "heavier in my hands").

**The sentence a null drive licenses:** *"If the I component ramps during a light 3 s hold, the angle-referenced bound is
not live; if it is flat but the release still overshoots by more than the §5 value + 2°, the plant is outside the credible
set — revert either way. If c_D is 0.40 (not 0.45–0.70), the D was not re-sized — the build is P2, not C3."*

---

## 9. The variants (each built, H1-checked and scored; offered for a specific ruling)

### 9.1 C3-Pd — the b_q × ms_free ruling (table swap, same bytes, same code)

C3-P's cave and in-place set with **G-P48d's table** (cave `c3_cave_C3-Pd.hex`, 222 B, sha `3aa6d14fe580d6fd` — identical
to the bytes-risk judge's merged graft). **Frequency:** 166 R2-box fails, **all on `b_q×ms_free`** (PM 17.0°, ring 1.28 Hz
ζ 0.055), **declared and covered by R3\***. **Time:** keeps P2-class highway small corrections (±0.3° 0.2 Hz in-phase gain
at 15–22 = 0.78 vs C3-P's 0.31; dwell +1° at 15–22 = 0 vs 15), linear tracking 0.961 (passes). **Choose C3-Pd if the
orchestrator rules `b_q×ms_free` credible** (the synthesis leans C3-P: GATE 2 is the safety gate, and R3\* detects the ring
only after the car shows it). Both cost the same bytes.

### 9.2 ICL 12288 (0 bytes over C3-P, not for the first flight)

`c3_cave_C3-P.hex` with the ICL cal `0xC61BA` = 12288. +0.012 replay tracking at 8–15 m/s and the a 3.5 hold margin; no
lurch cost (the bound binds first). Worst-case I authority rises to ≈ 1970 T where the bound is defeated — above anything
r71b needs, and above V295's own 10240 clamp. **Not recommended first; 0 bytes to add later.**

### 9.3 C3-PA2 — the low-speed ruling (A2, −18 B)

C3-P's cave without the low-speed cap (`c3_cave_C3-PA2.hex`, 204 B). **≥ 8 m/s identical to C3-P** (every goal time
criterion passes). Below 8 m/s: low-speed turn-**hold** 0.998 (vs A3's 0.90–0.95), but the release lurch regresses to
13.9° on b_lo×J_hi (vs A3's 10.6°). **Choose C3-PA2 if the operator rules low-speed HOLD over the < 8 m/s release lurch.**

### 9.4 C3-P44 — more 20 Hz margin (table + Kd swap)

C3-P's code with **G-P44's table and Kd 44** (`c3_cave_C3-P44.hex`, 222 B). M20 0.88× V295 (a 10 % margin vs C3-P's 0.96),
0 R2-box fails; costs more highway dwell-then-jump and a lower in-phase gain. Choose only if the BELIEF-grade plant
response at 20 Hz outweighs small-correction precision.

---

## 10. What a FAIL looks like (written before any build; any one means **do not flash**)

| id | failure |
|---|---|
| H1 | the BUILT image's cave bytes, executed by the interpreter, differ from the lane's cave arithmetic on any of 60 000 inputs; or any register outside {r6, r8, r9, r13, r16, r26} (C3-P) / {r6, r8, r9, r13, r16} (C3-F) changes; or r25 or r14 is written; or any RAM is written |
| H2 | `score_freq` on the BUILT table/cals: any R2-box fail outside the declared set (C3-Pd only: `b_q×ms_free`), any unstable point, M20 or L20 > V295's in the same frame, any \|T\| 5–30 Hz > +3 dB |
| H3 | `score_time` on the BUILT table: any goal time criterion failing on any member ≥ 8 m/s; any int32 wrap; a sentinel push > 0.1° |
| H4 | GATE 1: the cave writes any RAM, or reads any RAM other than the listed gp cells |
| H5 | from the BUILT image in Ghidra: the hook ≠ `jarl 0xC4C00,r6`; the `jr` ≠ `0x29D7E`; `jmp [r6]` is not the normal exit; r26 read between `0x29D7A` and `0x29EE0` by anything but the new `mov r26,r8` (C3-P); r25/r14 written in the cave; the cave reachable from a skip path |
| H6 | with A2+B2 on the BUILT image: P computed on the 0x7FFF sentinel; B2's cmov ≠ r8 := (Z ? r27 : 0); `0x2913A` does not dominate `0x29A48` |
| H7 | the table lacks the 0xFFFF row, or the walk reads outside the table for any v in 0..65535 |
| H8 | any integrity region fails `verify_bootloader_crc.py` on the BUILT image (walk 49/49, full chain 50/50), including the block holding `0x13100` |
| H9 | F181 ≠ `39990-TVA,A16A`; the `.rwd` header does not list both A160 and A16A; the revert `.rwd`s are not re-headered |
| H10 (C3-P) | pol ≠ −1: the V98 record is contradicted, or the config parse gives +1 on this car |
| adversarial | the mandatory close-out adversarial pass (≥ 3 independent agents, disjoint surfaces, "do not flash" reachable) finds any decision-bearing defect |

**On the car: REVERT** on any of R1–R9 (§8). **FAILED its stated goal** if, on the car: a band ≥ 8 m/s with turn-hold
< 0.90 over ≥ 60 s; tracking outside 0.95–1.05 in any band ≥ 8 m/s; a new 5–30 Hz line; or dwell-then-jump above r6c in a
band other than the declared 3–7 m/s / 10–12.5 m/s / highway-hold misses.

---

## 11. How C3 differs from the recent arc (V38 → present)

C3 is **not a value inside V294/V295's cal space, not torque mode, not a rate loop with an unfiltered 20 Hz tail, not a
fork rewrite** — the four things the goal rules out. It is the **first angle loop**: the rate operand (V282…V295's loop
closed on a 100 Hz sample-and-hold of the motor-frame rate, re-attributed by the 2026-09-30 tracers) is replaced by a
1 kHz loop on the EPS's own steering angle `gp-0x6a00`, with a speed-scheduled P, a bounded I that the angle itself
bounds, and a guarded rate D for phase. The class differences from the record:

- **vs V294/V295 (acceleration trim, cal-only):** those were scored against a loop gain |L| ≤ 0.63 on their stated
  quantity and the operator ruled both FAILED their goal. C3 closes a loop (|L| ≫ 1 at DC via the integrator) on the
  quantity that removes the friction dead zone — steering angle — and is scored against the goal, not a cal value.
- **vs the cave-bricking class (V24, V27, V48B):** every one bricked. C3 is a **gated cave** — GATE 1 (0 RAM, all reads
  earlier-in-tick), GATE 2 (0 R2-box fails, magnitude and phase in every loop), a byte-exact mirror the H1 executes, the
  wire instrument on every term, an adversarial pass reachable — the discipline every post-V29 success shares.
- **vs V291/V292 (loop-opening above 10 Hz → 7 Hz re-armed) and V289 (20 Hz notch → 16 Hz pole):** C3 adds no lagged
  feedback and no notch; the one new dynamic element is the guarded rate D, whose 13 Hz (C3-P) is no worse than P2 and
  whose 5 Hz anti-damping is the least on the panel.
- **vs V283 (Ki on an operand holding the command → release lurch):** C3's Ki is on the angle error with the
  angle-referenced bound and the hard freeze — the release lurch is 4.1° (C3-P), the smallest of every F1-fixing design.

---

## 12. What this page did not do (so nobody reads it as done)

- **No image was built**, so nothing here is decoded from a BUILT image (H5); the cave listings/H1 are on the assembled
  bytes, and §1.1/§1.2/§2 decode those bytes dry-run. The in-place edits are rev2-A's records, re-asserted against V295.
- **The common scorers carry the credible set, hold ages and frames; the time scorer models every rate operand at κ 1 in
  its `unity` frame and the correction table in `vgr` (the primary).** κ (torque-word counts per T count) is unmeasured
  (BELIEF) — the angle-referenced bound is κ-independent by construction, which is why it is preferred.
- **Not decidable without V282:** dwell-then-jump ≤ V282 and hard-turn energy ≤ V282's (counts and ratios reported).
- **Low-speed stick-slip "gone" is met by no candidate** (M-C3-8) — the declared frontier.
- **F5 (the camera relay close) and pol ≠ −1 are not simulable** (§7).
- The mandatory **close-out adversarial pass on the BUILT image** (≥ 3 independent agents, "do not flash" reachable) and
  the **Artifact** (the signal-flow diagram with the LERPs, before/after) are the build-time steps, not done on this
  design page.
