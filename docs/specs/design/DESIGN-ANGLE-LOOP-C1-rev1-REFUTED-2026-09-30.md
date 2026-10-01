> **ARCHIVED RECORD (2026-10-01).** This is C1 **rev 1** exactly as the round-2 refuters read it. It was REFUTED (stability lens: b_q x J_hi / b_q x J1.0 near-unstable to unstable at >= 12.5 m/s, `analysis-2020accord/studies/angle_loop/reports/REFUTE-C1-r1-stability-2026-09-30.md`). It is superseded by C1 rev 2 in `DESIGN-ANGLE-LOOP-C1-2026-09-30.md`. Its scripts reproduce with `C1_VARIANT=kd16` (c1_lib). A record, not an instruction.

# DESIGN C1 (2026-09-30): the angle loop, revised against the three refuters

**Status: DESIGN ONLY. SUPERSEDES C0** (`DESIGN-ANGLE-LOOP-C0-2026-09-30.md`). Nothing was built, flashed or sent.
The fork was not touched. Ghidra was used read-only (`disassemble_bytes` dry run) on the V294 program, which is
code-identical to V295 except cal `0xC63EA` and its CRC.

**Author:** subagent (Opus), for the orchestrator `main`. **Brief:** resolve every finding of the three refuters
(`analysis-2020accord/studies/angle_loop/reports/REFUTE-stability-2026-09-30.md`, `REFUTE-friction-…`,
`REFUTE-safety-…`), by a design change re-verified with both harnesses **and the refuters' own scripts**, or by a
quantified miss written on this page before any build.

**Base image:** V295 `_v295_V295-V294BASE-ACCELTRIM.B1050-…TORQUE.TAP_plain_image.bin`, sha256 `5c044d65…52ed`.
Every pre-edit byte quoted below was re-read from it in Python this session.

**Evidence produced here.** Every script is in `analysis-2020accord/studies/angle_loop/c1/`; caches in
`_scratch/angle_loop/c1/` (gitignored, regenerable). Text outputs sit next to the scripts.

| script | what it does | output |
|---|---|---|
| `c1_lib.py` | the C1 table, the cave's integer walk, and the C1 lane mirror for **both** time harnesses (`harness_time.run` and `refute_friction/fric_lib.run`) | — |
| `c1_selftest.py` | the mirror's controls (§1.6) | `selftest_out.txt` |
| `c1_assemble.py` | assembles the cave listing to bytes, executes **those bytes** in a minimal V850 interpreter, compares with the mirror | `c1_assemble_out.txt`, `c1_cave.bin.hex` |
| `c1_members.py` | the GATE-2 member set by tier (§2.2) | — |
| `c1_design_G.py`, `c1_explore_fI.py` | the G(v) envelope on a 0.25 m/s grid; the PI corner / Kd exploration | `design_G.txt`, `explore_fI.txt` (first sweep), `explore_fI_summary.txt` (every fI × Kd × knot-set run) |
| `c1_gate2.py` | GATE 2, sections A–E (§3) | `gate2_{A_Kd16_final,B,C,D,E}_Kd16.txt` |
| `c1_time.py` | the time harness (unmodified `run/metrics/per_speed_score`) on C1 and C0, nominal / robust / outer-loop suites | `time_{nominal,robust,pi}_score.txt` |
| `c1_robust_table.py` | compact per-member table | `robust_table.txt` |
| `c1_ipolicy.py` | the I-policy study, four scenarios, six policies in one batch | `ipolicy_all.txt` (and `_scratch/…/ipolicy.log`) |
| `c1_freeze_duty.py` | the cost of hands-off torque crossing the freeze threshold | `freeze_duty.txt` |
| `c1_handsoff_torque.py` | the engaged driver-torque distribution on route a6 (rlogs) | `handsoff_torque_a6.txt` |
| `c1_page_numbers.py` | Bode, tracking group delay, LIVE predictions, discriminator, hard-turn band | `page_numbers.txt` |
| `c1_rerun_refuters.py` | **runs the refuters' own scripts, unmodified, on C1** (the minimum patch that swaps the lane) | `refute_rerun/*.txt` |

Every decision-bearing claim is marked **EVIDENCE** (with method) or **BELIEF**. Code is cited by address or grep
string, never by line number.

---

## 0. The decision in one page

**C1 = C0's seven in-place edits, unchanged, plus ONE cave of 132 bytes (96 code + 36 table), plus calibration.**
Three things change from C0:

1. **The table is re-based** (G ×2, Kp_base 225, Ki_base 100). The integrator now sees a +1 LSB error at every
   speed (C0 was blind to it below ~11.5 m/s). Zero extra bytes. EVIDENCE §2.1.
2. **G(v) is re-sized** on a 0.25 m/s grid against an enlarged credible set that includes every combined member the
   stability refuter named (b_lo×J_hi, ×tau6, J ≈ 1, b at 0.25× of the fit at speed, hold aged to 20 ticks).
   Kp_eff is **570 at 8–12 m/s** (C0: 600–946) and **≤ 1971 at highway** (C0: 3000). Five knots, one fewer than C0.
   EVIDENCE §2.2, §3.
3. **The I policy is a FREEZE, not a bleed.** When |driver torque| > 512 or the ramp is below full, the cave returns
   two instructions late (to `0x29D7E` with r6 = 0), so Honda's own code integrates nothing. **The cave now writes no
   RAM at all.** It removes the 1–9° light-hand lurch above the threshold, the engage wind-up, the override-latch
   overshoot and the co-steer droop. EVIDENCE §2.3.

| question | answer | basis |
|---|---|---|
| Is GATE 2 met on the refuters' enlarged set? | **Yes, 0 fails on 3 640 points.** Tier A (single-factor family) PM ≥ 46.5°, tier B (every combined/stress member named) PM ≥ 32.0°, exact GM ≥ 7.8 dB, both linear methods agree to ≤ 0.99°. | EVIDENCE §3.1 |
| Does it survive the refuters' own scripts? | **Stability lens: yes** (`stab_scan`: no credible member < 45°, no combined member < 30°; the J_hi trough is 61°, not 40.7°; highway goes unstable only below b = 0.131× the fit, was 0.207×; `stab_nl`'s b = 5 highway limit cycle is gone). **Friction lens: partly** (light-hand lurch, engage wind-up, co-steer droop and the e5 defect fixed; stiction misses remain and are declared). | EVIDENCE §4 |
| What does the robustness cost? | **0.5 Hz tracking at 11.9–19 m/s: 0.886–0.915** (harness proxy, nominal; C0 0.93–1.04). 0.2 Hz tracking (0.98–1.03) and turn-hold (≥ 0.99) still pass in every band ≥ 8 m/s. 1–3 dwell-then-jump events per scenario set at 10–12.5 m/s where C0 had 0. | EVIDENCE §4.1; declared §8 |
| Is the 5–17 Hz anti-damping designed out? | **Bounded, not designed out.** C1's worst Re(T/ω) is 0.59–0.90× C0's over 5–25 Hz, **0.997× V295's at 20 Hz**, but 6.8× V295's at 13 Hz. 0/240 hands-off, 0/144 low-b and 0/288 hands-on two-mass stress rows unstable. Kd 16 meets Re(T/ω)₂₀ ≤ V295's at every speed; Kd 22 does not (1.25×). | EVIDENCE §2.4, §3.5 |
| Low speed (0–7 m/s)? | **Pre-declared MISS**, quantified §8: stick-slip 2–7 events per scenario set at 3–6 m/s, a constant-setpoint hunt of 0.11–0.42° p2p at 3–7 m/s. No friction term without an instrument; the first drive measures F_s(v), F_c(v) and the dead zone (§6.4). | EVIDENCE §4.3 |
| Fork prerequisites? | F4 (fwVersion + param), C3/C5, C8, Δmax(v), O1, τ_o ≥ 1 s with no integral below 8 m/s, a measured panda bound, plus two firmware traces (preemption, timeout) are **flight prerequisites**. F3 is not, if the operator keeps the camera's LKAS off; its firmware form is **one byte** at `0x2937C` but switches the engage state chain, untraced outside the lane (§2.6). | EVIDENCE/BELIEF §2.6, §9 |

**What C1 is predicted to do against the goal** (EVIDENCE: simulation, nominal plant; the strict and robust readings
are §4):

| goal criterion | C1 prediction | verdict on the page, before any build |
|---|---|---|
| dwell-then-jump ≤ V282 in every band; low-speed stick-slip gone | 3–6 m/s: 2–7 events per scenario set (C0: 2–7); 7–8 m/s: 0; **10–12.5 m/s: 1–3** (C0: 0); ≥ 15 m/s: 0. Hunt at a constant setpoint 3–7 m/s. | **PRE-DECLARED MISS at 0–7 m/s and 10–12.5 m/s.** V282 is not simulable, so "≤ V282" is decided on the car. |
| tracking 0.95–1.05 in every band ≥ 8 m/s | 0.2 Hz: 0.981–1.030. 0.5 Hz: 0.974 (8), 0.955 (10), **0.908 / 0.895 / 0.891 / 0.886 / 0.915** (11.9 / 12.5 / 15 / 17 / 19), 0.958 (22), 1.008–1.025 (26–30). | **PRE-DECLARED MISS of the 0.5 Hz proxy at 11.9–19 m/s.** The on-car read (a 0.5 Hz low-passed regression over ≥ 10 s runs) is dominated by lower frequencies, where C1 passes (BELIEF on that mapping). |
| turn-hold ≥ 0.90 in every band ≥ 8 m/s | 0.996–1.013 | predicted PASS |
| ring ≤ 0.5 %, F7 = 0, no new 5–30 Hz line | no line on any member (holds ≤ 0.8 T counts rms); 0/80 20 Hz stress rows unstable (V282: 28/80) | predicted PASS |
| 20 Hz loop gain ≤ V295 | M20 ≤ 2.28 (V295 3.58); L20 ≤ 0.636× V295's; Re(T/ω)₂₀ ≤ 0.997× V295's | predicted PASS |
| hard-turn 1.6–3 Hz energy ≤ V282 | below the reference's own at every speed (1.43/1.80 at 3 m/s … 0.13/0.19 at 30) | predicted PASS (harness control, not V282) |

---

## 1. The loop in integer form: every byte and every cal

### 1.1 In-place code edits: C0's seven, unchanged

Re-read from V295 this session (Python); decodes are Ghidra dry runs on the V294 program (C0 §1.1 and this session).

| id | address | V295 bytes → C1 bytes | V295 → C1 instruction | loop term |
|---|---|---|---|---|
| E1 | `0x28F4C` | `24 3f aa 95` → `24 3f 00 96` | `ld.h -0x6a56[gp],r7` → `ld.h -0x6a00[gp],r7` | operand x = θ (0.1° counts); the ±12000 bail now tests θ |
| E2 | `0x28FA4` | `89 d1` → `c9 d1` | `subr r9,r26` → `add r9,r26` | r26 = s_old + s_new |
| B2 | `0x29A50` | `e2 47 00 00` → `e0 df 34 43` | `setfe r8` → `cmovne r0,r27,r8` | r8 := (request == 1) ? bVar2 : 0 |
| A2 | `0x29A56` | `da 05` → `b2 05` | `bne 0x29A60` → `be 0x29A5C` | the PID runs iff ramp ≠ 0 ∧ r8 ≠ 0 |
| E4 | `0x29D6A` | `08 80 ed 80` → `24 87 52 96` | `mov r8,r16 ; mulh r13,r16` → `ld.h -0x69ae[gp],r16` | sp := gp-0x69ae |
| H | `0x29D76` | `c2 82 ba 81` → `89 37 8a ae` | `shl 2,r16 ; sub r26,r16` → `jarl 0xC4C00, r6` | the hook |
| E5 | `0x29EDE`, `0x29EE0` | `c7 00` → `80 39`; `10 40 bb 41` → `24 47 aa 95` | `zxh r7` → `subr r0,r7`; `mov r16,r8 ; sub r27,r8` → `ld.h -0x6a56[gp],r8` | D = clamp((−Kd·x_rate) >> 3, ±DCL) |

**Hook encoding.** EVIDENCE (`c1_assemble.py`): the same encoder reproduces the flown V112 hook `0x55C0E 86 ff 26 ef`
(`jarl 0xC4B34, lp`) byte for byte, and gives `89 37 8a ae` for `jarl 0xC4C00, r6` at `0x29D76`. BELIEF until
Ghidra decodes the built image (H5).

Not applied, as in C0: edit 6 (`0x29A5A`) and the cal `0xC63F6`.

### 1.2 The cave (`0xC4C00`, 132 bytes, inside the free span `0xC4BD8..0xC4FEF`)

EVIDENCE: `c1_assemble.py` (V295 bytes `0xC4BD8..0xC4FEF` all 0xFF; every encoding form controlled against an
instruction of the same form in V295, 14 controls, all OK — `c1_assemble_out.txt`). BELIEF until assembled into an
image and decoded by Ghidra.

```
;  entered by  jarl 0xC4C00, r6  from 0x29D76  (r6 = 0x29D7A).  Scratch r8 r9 r13; reads r14 (the ramp) and r26.
;  No ep, no lp, no stack, NO RAM WRITE.  Each line names the loop term it implements.
0xC4C00 C1:    c2 82              shl   2, r16              displaced 0x29D76: 4*sp
0xC4C02        ba 81              sub   r26, r16            displaced 0x29D78: E = 16*(theta_sp - theta)
0xC4C04        e4 47 a3 95        ld.hu -0x6a5e[gp], r8     v, 64 counts per km/h                    [G(v)]
0xC4C08        29 06 60 4c 0c 00  mov   0xC4C60, r9         table                                    [G(v)]
0xC4C0E        e9 6f 01 00        ld.hu 0[r9], r13          X0                                       [G(v)]
0xC4C12        ed 41              cmp   r13, r8                                                      [G(v)]
0xC4C14        cb 05              bh    L1                  v > X0 (unsigned): walk                  [G(v)]
0xC4C16        e9 47 03 00        ld.hu 2[r9], r8           G = G0 (clamp low)                       [G(v)]
0xC4C1A        b5 15              br    APPLY
0xC4C1C L1:    e9 6f 07 00        ld.hu 6[r9], r13          X(i+1)                                   [G(v)]
0xC4C20        ed 41              cmp   r13, r8
0xC4C22        c3 05              bnh   SEG                 v <= X(i+1): segment i                   [G(v)]
0xC4C24        09 4e 06 00        addi  6, r9, r9           next row; the 0xFFFF row ends the walk
0xC4C28        a5 fd              br    L1
0xC4C2A SEG:   e9 6f 01 00        ld.hu 0[r9], r13          X(i)
0xC4C2E        ad 41              sub   r13, r8             dv = v - X(i)
0xC4C30        29 6f 04 00        ld.h  4[r9], r13          S(i), Q12, signed
0xC4C34        ed 47 20 02        mul   r13, r8, r0         dv*S(i) (low word)
0xC4C38        ac 42              sar   12, r8
0xC4C3A        e9 6f 03 00        ld.hu 2[r9], r13          G(i)
0xC4C3E        cd 41              add   r13, r8             G = G(i) + ((v - X(i))*S(i) >> 12)
0xC4C40 APPLY: e8 87 20 02        mul   r8, r16, r0         E*G (low word)          <-- THE SPEED GAIN, on P and I
0xC4C44        a8 82              sar   8, r16              E' = (E*G) >> 8
0xC4C46        e4 47 99 b0        ld.hu -0x4f68[gp], r8     |driver torque|          <-- THE I FREEZE
0xC4C4A        20 6e 00 02        movea 512, r0, r13        THR
0xC4C4E        ed 41              cmp   r13, r8
0xC4C50        cb 05              bh    FRZ                 |tq| > 512 (unsigned): freeze
0xC4C52        ce 6e 00 80        andi  0x8000, r14, r13    r14 = the ramp (the 0x2A1E6 multiplier)
0xC4C56        ca 05              bne   DONE                ramp == 0x8000: integrate normally
0xC4C58 FRZ:   00 32              mov   0, r6               e5 := 0  ->  Honda's exc = 0, I unchanged
0xC4C5A        b6 07 24 51        jr    0x29D7E             skip 0x29D7A mov r16,r6 / 0x29D7C sar 5,r6
0xC4C5E DONE:  66 00              jmp   [r6]                return to 0x29D7A
0xC4C60 TBL:   (6-byte rows, LE: X u16, G u16, S s16)
               ca 02 2d 02 4e 01   X  714 ( 3.1 m/s)  G  557  S  334      Kp_eff  490
               33 07 89 02 00 00   X 1843 ( 8.0 m/s)  G  649  S    0      Kp_eff  570
               cd 0a 89 02 b9 11   X 2765 (12.0 m/s)  G  649  S 4537      Kp_eff  570
               4d 0f 85 07 3b 02   X 3917 (17.0 m/s)  G 1925  S  571      Kp_eff 1692
               36 18 c3 08 00 00   X 6198 (26.9 m/s)  G 2243  S    0      Kp_eff 1971
               ff ff c3 08 00 00   sentinel row
```

**Size and inventory.** 96 bytes of code (33 instructions) + 36 bytes of table = **132 bytes** (C0: ≈ 98 + 42 = 140).
Every instruction belongs to one of four terms: the two displaced instructions, the G(v) LERP, the speed gain, or the
I freeze. The freeze costs 26 bytes, the same as C0's bleed; it drops C0's `ld.w`/`st.w` of `gp-0x6dd0`.

**The freeze return path.** EVIDENCE: Ghidra dry-run decode of `0x29D66..0x29DC6` (this session):
```
29d7a mov r16,r6 ; 29d7c sar 0x5,r6          e5 = E'>>5                (SKIPPED on the freeze)
29d7e cmp r10,r6 ; 29d80 mov 0,r9 ; 29d82 ble 0x29d8c
29d84 ld.hu DB,r9 ; 29d88 subr r6,r9 ; 29d8a br 0x29d9c        exc = e5 - DB
29d8c ld.hu DB,r13 ; 29d90 subr r0,r13 ; 29d92 cmp r13,r6 ; 29d94 bge 0x29d9c   (exc = 0)
29d96 ld.hu DB,r9 ; 29d9a add r6,r9                              exc = e5 + DB
29d9c ld.hu Ki,r6 ; ... 29da4 ld.w -0x6dd0,gp,r10 ; 29da8 mul r6,r9,r0 ; ... I = clamp(I_old + (exc*Ki>>3))
```
With r6 = 0 on entry at `0x29D7E`, `cmp r10,r6` against DB ≥ 0 takes `ble`, and `0 >= -DB` takes `bge` with r9 = 0,
so exc = 0 and I = clamp(I_old). EVIDENCE: `c1_selftest.py` CHECK 3 emulates these instructions register by
register: exc = 0 for all 2 070 DB values tried, and the emulation equals the mirror's dead-zone formula on 20 000
random (e5, DB). The DB register r10 cannot be used to freeze, because the subtraction reloads DB from flash
(`0x29D84`, `0x29D8C`, `0x29D96`) — that was the first idea and the decode killed it.

**r14 is the ramp.** EVIDENCE: Ghidra decode `0x2A1E6 mul r14,r9,r0` (`ee 4f 20 02`) is the `y × ramp` multiply,
and the hook trace's first-use scan lists r14 live and unwritten from `0x29D78` to there. The SM writes it from
`gp-0x69b0` (`0x29396..0x293B0`: `ld.hu 0x73f8,tp,r14 ; add r12,r14 ; st.h r14,-0x69b0 ; zxh r14`). The ramp saturates
at exactly 0x8000 (decompile, state 3: `if (33 + ramp < 0x8000) … else ramp = 0x8000`), so bit 15 is set iff the
ramp is full. Re-prove on the built image (H5).

### 1.3 Calibration cells

| cell | stock | V295 | C0 | **C1** | what it is |
|---|---|---|---|---|---|
| a `0xC63E8` (s16) | 923 | 1011 | 0 | **0** | fb pole: 2-tap FIR |
| b `0xC63EA` | 1560 | 1050 | 8192 | **8192** | fb gain: s_new = 8θ |
| C `0xC62E6` | 7680 | 1024 | 65535 | **65535** | r26 clamp (θ ≤ 409.6°) |
| DB `0xC62E4` | 4 | 4 | 0 | **0** | I deadband (DB 1 evaluated, rejected §2.7) |
| Ki `0xC63E6` | 0 | 0 | 199 | **100** | re-based: fI = 7.8125·100/(2π·225) = 0.553 Hz |
| ICL `0xC61BA` | 10240 | 10240 | 4096 | **4096** | I>>7 ≤ 4096 S (≈ 660 T). The clamp acts on I, not through Ki, so the rebase leaves it unchanged. |
| DCL `0xC61B6` | 10240 | 0 | 10240 | **10240** | D clamp |
| Kp record Y `0xE5384` ×5 | 248/512/645/696/696 | 960 ×5 | 450 ×5 | **225 ×5** | re-based Kp_base (selector 7 → `0xE5378`) |
| Kd record Y `0xE5126` ×4 | 128 ×4 | 0 ×4 | 16 ×4 | **16 ×4** | D on −rate: 2.56 T per deg/s |
| everything else (PCL, SCL, OCL, sign-hold, output lag 992/507, `0xC63F4/F6/F8`) | — | V295 | unchanged | **unchanged** | — |

**CRC.** As C0: the code edits and the cave dirty trailer `0xC4FFC` only; the cals dirty `0xC6FFC`; the Kp/Kd records
sit in the `0xE5xxx` block V293–V295 already rewrote. The builder recomputes all three and runs
`verify_bootloader_crc.py`. (Not re-checked this session.)

### 1.4 The loop, integer-exact Python

```python
def c1_tick(st, theta, x_rate, sp69ae, v6a5e, tq4f68, ramp, req6805, bvar2):
    if not (ramp != 0 and req6805 == 1 and bvar2):               # guard with B2 + A2 (0x29A48..0x29A64)
        st.I8 = 0; st.Eprev = 0x7FFFFFFF; S = 0                   # 0x2A164 skip
        return lag_and_gate(st, S)
    s_new = (8192 * theta) >> 10                                  # 0x28F8E.. a = 0 -> 8*theta
    r26 = clamp(st.s_old + s_new, -65535, 65535); st.s_old = s_new  # 0x28FA4 add (E2)
    E = (sp69ae << 2) - r26                                       # cave: displaced shl 2 ; sub
    G = walk(TBL, v6a5e)                                          # cave: G(i) + (((v - X(i)) * S(i)) >> 12)
    E = s32(E * G) >> 8                                           # cave: mul ; sar 8
    frozen = tq4f68 > 512 or (ramp & 0x8000) == 0                 # cave: ld.hu ; movea ; cmp ; bh / andi ; bne
    e5 = 0 if frozen else E >> 5                                  # FRZ: r6 = 0, return to 0x29D7E | else 0x29D7C
    exc = e5 - DB if e5 > DB else (e5 + DB if e5 < -DB else 0)    # 0x29D7E..0x29D9A (DB = 0)
    I = clamp((st.I8 >> 3) + ((exc * 100) >> 3), -(4096 << 7), 4096 << 7)   # 0x29DA4..0x29DC2
    P = clamp((E * 225) >> 8, -15360, 15360)                      # 0x29E36 mul ; 0x29E3E sar 8 ; PCL
    D = clamp((-16 * x_rate) >> 3, -10240, 10240)                 # E5 ; DCL
    S = (I >> 7) + P + D ; st.I8 = I << 3                         # 0x29F18.. ; 0x2A190
    return lag_and_gate(st, fade_and_clamp(S))                    # 0x2A0B4.. fade, SCL ; output lag ; x ramp ; OCL
```

**Scale, hands off** (EVIDENCE: arithmetic, as C0 §1.4 with Kp_eff = 225·G/256):

| v (m/s) | ≤ 3.1 | 5 | 8–12 | 12.5 | 15 | 17 | 19 | 22 | 26 | ≥ 26.9 |
|---|---|---|---|---|---|---|---|---|---|---|
| G | 557 | 592 | 649 | 776 | 1414 | 1925 | 1989 | 2085 | 2213 | 2243 |
| Kp_eff | 490 | 520 | 570 | 682 | 1243 | 1692 | 1748 | 1833 | 1945 | 1971 |
| Ki_eff (= Kp_eff × 100/225) | 218 | 231 | 253 | 303 | 552 | 752 | 777 | 815 | 864 | 876 |
| T per degree of error (≈ Kp_eff/10) | 49 | 52 | 57 | 68 | 124 | 169 | 175 | 183 | 195 | 197 |
| P reaches the rail at \|e\| = 24 576 / Kp_eff | 50.2° | 47.3° | 43.1° | 36.0° | 19.8° | 14.5° | 14.1° | 13.4° | 12.6° | 12.5° |

### 1.5 Overflow budget (EVIDENCE: arithmetic over the operand bounds)

| quantity | worst case | limit |
|---|---|---|
| \|E\| | 4·32767 (sentinel) + 65535 = 196 603 | — |
| \|E·G\| | 196 603 × 2243 = 4.41·10⁸ | < 2³¹ |
| \|E'\|, \|E'·225\| | 1.72·10⁶, 3.88·10⁸ | < 2³¹ |
| \|e5·Ki\| | 53 800 × 100 = 5.4·10⁶ | — |
| \|dv·S\| in the walk | 1152 × 4537 = 5.2·10⁶ | — |

No int32 wrap in any C1 time-harness run (the harness's `s32g` counter, `wraps` column = 0 everywhere).

### 1.6 The mirror and its controls (EVIDENCE: `c1_selftest.py`, `c1_assemble.py`)

| check | result |
|---|---|
| CHECK 1: `LaneC1` with the cave off equals `harness_time`'s original `LaneVec` (A2 guard), tick for tick | **0 mismatches / 40 000** random ticks with skips and driver torque |
| CHECK 2: `LaneC1F` with C0's table and bleed equals the friction refuter's `fric_lib.LaneC0` (the C0 listing) | **0 / 40 000** |
| CHECK 3: Honda's exc code with r6 = 0 (the freeze) | exc = 0 for all DB; 0 / 20 000 vs the mirror |
| CHECK 5: the C1 walk vs the exact real LERP over gp-0x6a5e = 0..65535 | −1.02 … +0.06 counts; monotone; knots reproduced |
| **H1 at design time:** the assembled bytes, executed by a minimal V850 interpreter, vs the mirror's cave | **0 mismatches / 200 000** random (E, v, \|tq\|, ramp, register file), incl. the 0x7FFF sentinel and the table edges: r16 = E', exit address = the freeze decision, r6 = 0 on the freeze, every register other than r6/r8/r9/r13/r16 unchanged |

The interpreter decodes from the bytes by field extraction (byte-level build work, CLAUDE.md's allowed use) and its
branch and `jr` decodes reproduce the image's own controls (`0x29372 jr 0x29734`, `0x2A1E4 br`, `0x29384 bnh`).
**It is not Ghidra.** H5 (Ghidra decode of the built image) is still required.

---

## 2. What changed from C0, finding by finding

### 2.1 (a) The re-base: the +1 LSB blind spot is gone (friction refuter F2)

EVIDENCE (`c1_selftest.py` CHECK 4): e5 = E'>>5 for a ±1 angle-LSB error.

| v (m/s) | 0–10 | 11.5–12.5 | 15 | 19 | 26–30 |
|---|---|---|---|---|---|
| C0: G, e5 for +1 / −1 LSB | 256–442, **0** / −1 | 518–569, 1 / −2 | 896, 1 / −2 | 1421, 2 / −3 | 1707, 3 / −4 |
| C1: G, e5 for +1 / −1 LSB | 557–649, **1** / −2 | 649–776, 1 / −2 | 1414, 2 / −3 | 1989, 3 / −4 | 2213–2243, 4 / −5 |

- **No speed has e5 = 0 for +1 LSB** (C0: every speed below ~11.5 m/s).
- **Residual, declared:** the floor of `sar` is still asymmetric (+1 → 1, −1 → −2 at G 512–1024). The integrator
  equilibrates where mean E' ≈ +16 counts, i.e. **a +½-LSB (0.05°) offset at 3–12 m/s, ≤ 0.013° at highway**.
  Removing it costs 4 bytes (`addi 16,r16,r16` before the return) and adds a 2-T bias to P; not adopted.
- **Effect, small amplitude** (the friction refuter's own `expG_smallamp.py` re-run on C1): at 8–12.5 m/s, ±0.2–0.3°,
  0.2 Hz the gain is now 0.955–1.04 (C0: 0.66–0.94). EVIDENCE `refute_rerun/expG_smallamp_nominal.txt`. The 0.5 Hz
  small-amplitude shortfall remains (stiction, §2.5).

### 2.2 (b) G(v) re-sized against the enlarged credible set (stability refuter F1, F2, F3, F4, F7)

**The member set** (`c1_members.py`). Tier A keeps C0's bar; tier B adds every combination the stability refuter named.
The refuter's own `combo()` definitions are copied verbatim, so the members mean exactly what the refuter ran.

| tier | gate | members |
|---|---|---|
| A | PM ≥ 45°, exact GM ≥ 6 dB, stable, no 5–50 Hz pole ζ < 0.2, M20 ≤ 3.58, L20 ≤ V295's on the same member, \|T\|, \|T_ref\| ≤ +3 dB in 5–30 Hz | nominal, J_lo, J_hi, b_lo, b_hi, tau0, tau6 |
| B | PM ≥ 30°, stable, exact GM ≥ 6 dB | b_lo×J_hi, b_lo×J_hi×tau6, b_lo×tau6, J_hi×tau6, b/1.9×J_hi, b_lo×J0.3 (refuter F3); J_hi2 (= J 0.8 refit) and **J1.0** (the 0.8/1.3 refits interpolated, BELIEF on the interpolation) (F2); nominal/b_lo/J_hi with **slot 4 late by 10 ticks** (hold ages 11–20, F7); **b_q** = nominal with b × 0.25 at ≥ 12.5 m/s, floored at 3.46 (b_lo's identified low-speed value; BELIEF that the steering's own damping is not lumped vehicle dynamics) (F4 fix b); bc (linear part = b_lo) |
| report | not gated, tabulated | J1.3 refit, tau10, b_lo×tau10, ms_free (J 2.08), light_b (the prior), b/1.9, b_q0 (unfloored 0.25×) |

**Method.** The loop is linear in g = G/256: L = g·A(f) + B(f) (the refuter's `stab_lin.frf`, factored;
EVIDENCE: reproduces `stab_lin.margins` to 0.01° at six points incl. J_hi 11.9 m/s = 40.73° under C0). For each
(member, v) on the 0.25 m/s grid plus the plant knots 3.1/8.0/11.9/17.0/26.9, G_max is the largest G meeting the
tier gate scanning up from 128. The table is then fitted at ≥ 4.4 % below the envelope everywhere (the envelope is on an 8-count G grid)
(`c1_design_G.py` → `design_G.txt`).

**What binds** (EVIDENCE `design_G.txt`):

| speed | binding member | envelope Kp_eff | C1 Kp_eff |
|---|---|---|---|
| ≤ 3.1 m/s | J_hi (tier A) | 513 | 490 |
| 3.25–9.75 | b_lo×J_hi×tau6 (tier B) | 520–731 | 492–570 |
| 10–12.0 | b_lo×J_hi×tau6 and **J1.0** | 598–633 (trough at 11.9) | 570 |
| 12.25–13.0 | J1.0, b_lo×J_hi×tau6 | 703–900 | 625–794 |
| ≥ 13.25 | **b_q** (b at 0.25× of the fit) | 956 (13.25) → 2067 (≥ 26.9) | 852 → 1971 |

**The choice of Kd and fI** (EVIDENCE `explore_fI_summary.txt`, `gate2_B_Kd16.txt`, `gate2_B_Kd22.txt`, the provisional Kd 22 run in
`time_nominal_score_PROVISIONAL_kd16_vs_kd22.txt`):
- **Kd 16 kept.** Kd 22 raises the envelope (Kp_eff +10–30 %) and improves 0.5 Hz tracking at 10–12.5 m/s by
  0.04–0.06, but its 20 Hz anti-damping at highway is **1.3× V295's** (Re(T/ω)₂₀ −0.79 vs −0.63). With the highway gain
  set by b_q, raising Kd lifts both the D part and (through a higher envelope) the P part of the 20 Hz anti-damping: Kd 16 at Kp_eff 1971 sits at 0.997× V295's, Kd 22 at 1.25× (EVIDENCE for those two; BELIEF, by the arithmetic of §2.4, for the Kd values between). Kd(v) needs the 8-byte re-key (§2.7).
- **fI 0.553 Hz kept** (Ki_base 100). fI 0.62 buys +0.05 of 0.5 Hz tracking at 15–19 m/s but over-shoots 26–30 m/s
  to 1.05–1.06 (1.11 on b_hi) and lowers the low-speed envelope 12 %; fI 0.45–0.50 loses 0.5 Hz tracking everywhere.
- **Five knots** (3.1, 8, 12, 17, 26.9). A sixth knot at 13 m/s buys 2–4 % Kp at 12.5–15 m/s for 6 bytes; not adopted.

**GATE 2 result: 0 fails on 3 640 points** (§3.1).

**Tracking consequence.** The 0.5 Hz in-phase tracking (the harness's `track_gain` = |T|cos φ = Re T_ref — EVIDENCE:
the linear proxy reproduces C0's harness numbers to ±0.008 at 8/12.5/19/26/30 m/s) drops at 11.9–19 m/s:

| v (m/s), nominal | 8 | 10 | 11.9 | 12.5 | 15 | 17 | 19 | 22 | 26 | 30 |
|---|---|---|---|---|---|---|---|---|---|---|
| time harness tg0.2 | 1.006 | 1.017 | 1.030 | 1.018 | 0.991 | 0.981 | 0.986 | 1.007 | 1.020 | 1.021 |
| time harness tg0.5 | 0.974 | 0.955 | **0.908** | **0.895** | **0.891** | **0.886** | **0.915** | 0.958 | 1.008 | 1.025 |
| C0, same harness, tg0.5 | 0.979 | 1.017 | 1.040 | 1.004 | 0.946 | 0.927 | 0.977 | 1.018 | 1.040 | 1.050 |
| \|T_ref(0.5 Hz)\| (magnitude) | 1.040 | 1.066 | 1.083 | 1.047 | 0.987 | 0.968 | 0.994 | 1.032 | 1.082 | 1.093 |
| inner-loop group delay at 0.5 Hz | 113 ms | 142 | 171 | 162 | 136 | 128 | 125 | 120 | 113 | 112 |
| turn-hold ratio (harness) | 1.000 | 0.997 | 0.996 | 0.996 | 1.005 | 1.003 | 1.009 | 1.009 | 1.011 | 1.013 |

- The 0.5 Hz shortfall is **phase, not magnitude**: |T_ref| is 0.97–1.08.
- **C0 also missed 0.5 Hz at 15 and 17 m/s** (0.946, 0.927), speeds its own table did not score.
- A fork look-ahead (C10, `steerActuatorDelay`) converts phase into in-phase tracking, but **a single scalar cannot
  serve all speeds**: the best one (45 ms) gives 0.935–1.017 at 8–22 m/s and over-boosts 26–30 m/s to 1.057–1.069
  (`page_numbers.txt` §2). BELIEF on how the on-car regression weights this.

### 2.3 (c) The I policy, chosen with bytes in mind (friction refuter F1, F5; C0 §2.7's bleed)

**Options and their cost** (bytes beyond the shared `jmp [r6]`):

| policy | bytes | RAM | can an existing branch do it? |
|---|---|---|---|
| C0's bleed, 8I −= 8I>>6 above \|tq\| 1024 | 26 | RMW of gp-0x6dd0 | no |
| freeze above \|tq\| THR (r6 := 0, return to 0x29D7E) | 18 | **none** | the return-past trick reuses Honda's own I code; the DB register cannot (§1.2) |
| + freeze while ramp < 0x8000 | +6 (`andi` on r14, `bne`) | none | the guard only tests ramp ≠ 0; r14 already holds the ramp, so no load |
| + reset (st.w r0) above \|tq\| 2048 | +10 | a write | — |
| bleed scaled by (1−f) | ≥ 30 (re-derives the fade LERP or a gp-0x682f-indexed shift) | RMW | no |

**Results** (EVIDENCE: `c1_ipolicy.py`, one batch per scenario so every policy sees identical inputs; nominal plant;
fric_lib's plant and fork frame):

| scenario (the refuter's script it re-implements) | C1 (freeze 512 + ramp) | C0's bleed (1024) | no policy |
|---|---|---|---|
| E1 light-hand override, δ 0.5–2°, 3 s, release (`expC`) — \|tq\| 700–1000 | **−0.03 … 0.46°** | 1.9–8.7° | 1.9–8.7° |
| E1, \|tq\| ≥ 1100 | ≤ 0.32° | ≤ 0.55° | 2.2–8.5° |
| E1, \|tq\| 0–500 (below THR) | 1.9–8.7° (unchanged) | 1.9–8.7° | 1.9–8.7° |
| E2 engage under load, released at once (`expD`) — overshoot | **≤ 0.08°** | 0.15–2.33° | — |
| E2, droop (3–8 m/s / 12.5 / ≥ 19) | 6.5–6.9° / 2.4° / 0.5–1.1° | 6.0–6.1° / 2.2° / 0.5–1.0° | — |
| E2, released ≥ 1 s after engage | identical (3.2–3.4° at ≤ 8 m/s) | identical | — |
| E3 co-steer, a helping hand 2 s then release (`expF`) — droop | **≤ 0.98°** (\|tq\| 700 or 1500) | 0.13–4.1° (700), 0.24–3.5° (1500) | 0.07–4.4° |
| time harness `ov_latch` (override latch, ramp down and back) — overshoot | **≤ 0.08°** | 0.59–3.89° (C1 gains) | — |
| E4 **new**: a 3 s override that moves the wheel, fork O1, release — lurch | 0.13–3.55° (both directions) | 0 (straighten) / 0.40–5.36° (tighten) | 0.20–5.94° |

**Decision: freeze when \|gp-0x4f68\| > 512 or the ramp is below full. 26 bytes, no RAM.** Reasons:
1. It removes the light-hand lurch for every hand above 512 internal counts (≈ 524 wire), and the latch overshoot,
   which C0's bleed did not.
2. It keeps the curve-carrying I through co-steering, where the sign-blind bleed drained it (refuter F5).
3. **The ramp freeze earns its 6 bytes:** it removes a 1.6–2.3° engage overshoot and a 0.6–3.9° override-latch
   overshoot, at the cost of 0.3–0.8° more droop only when the driver lets go the instant the lane engages.

**Why 512.** It is the first knot of Honda's own fade-B LERP (key 16), and it sits at the hands-off engaged p99 at low
steering rate. EVIDENCE (`c1_handsoff_torque.py`, route a6, 10 segments, 41 031 engaged frames without
`steeringPressed`): |0x18F| p50 118, p95 375, p99 811 wire overall; **p99 548 at |rate| < 10 deg/s**; above 500 wire
in 1.3 % of frames at < 10 deg/s, 25 % at 10–30 deg/s, 48 % at 30–60 deg/s, 0.9 % at 20–40 m/s.

**What the freeze costs.** EVIDENCE (`c1_freeze_duty.py`, sim, torque word above THR a fraction of the time in 50–300 ms
bursts): at 3 % duty, tracking −0.00…−0.03; at 25 % duty, 0.5 Hz tracking −0.06…−0.14 at 8–19 m/s; turn-hold stays
0.99–1.01 at every duty. BELIEF: the rate-correlated torque on route a6 is the driver's hands resting on the wheel; a
truly hands-off wheel carries only its own inertia reaction, which is small.

**Residuals, declared (§8):**
- **A hand below 512 internal counts** that holds the wheel off the setpoint still winds the I: lurch 1.9–8.7°, as C0.
  Whether a hand resisting 240–950 T of lane torque reads below 512 on the sensor is **BELIEF**: the T-to-sensor
  scale is unknown. The first drive measures it (§6.4).
- **A long override that moves the wheel (with O1)** leaves the frozen I stale: lurch 2.0–3.6° at 5–8 m/s,
  0.8–1.3° at 12.5, ≤ 0.7° at ≥ 19 m/s. A reset at |tq| > 2048 (+10 bytes, a RAM write) zeroes it for "straighten"
  overrides but makes "tighten" overrides 2.1–5.4°. Not adopted: the freeze has the smaller worst case.
- **Engage droop** under a load the driver hands over: 6.5–6.9° at ≤ 8 m/s if he lets go at once (3.2–3.4° after 1 s).
  It is P-only pickup of k·θ0 through the ramp. The fix is a fork-side feed-forward or a faster ramp; neither is in C1.
- **Goal wording.** THE GOAL names "a bounded I that bleeds on driver torque". C1's I is bounded (ICL) and **frozen**,
  not bled, on driver torque. The goal's measured criteria are unaffected; the operator should know the mechanism
  changed and why (refuter F5: a sign-blind bleed drains the I that carries the curve).

### 2.4 (d) The 5–25 Hz damping: bounded, not designed out (stability refuter F5)

EVIDENCE (`c1_gate2.py` B, the refuter's `stab_hf.torque_per_rate`; hold included, d = 2). Re(T/ω) in T counts per deg/s,
worst over every speed 1–35 m/s at 0.25 m/s:

| | 5 Hz | 7 | 10 | 13 | 15 | 17 | 20 | 25 |
|---|---|---|---|---|---|---|---|---|
| V294 (flew, no grind) | +1.42 | +0.82 | +0.23 | −0.08 | −0.20 | −0.28 | −0.34 | −0.37 |
| V295 | +2.63 | +1.51 | +0.42 | −0.15 | −0.37 | −0.51 | −0.63 | −0.69 |
| V282 (ground at 20 Hz) | +19.8 | +12.6 | +5.05 | −0.05 | −2.52 | −4.42 | −6.39 | −7.93 |
| C0 worst (26–30 m/s) | −5.25 | −3.48 | −2.12 | −1.45 | −1.17 | −0.97 | −0.76 | −0.54 |
| **C1 worst (≥ 26.9 m/s)** | **−3.12** | **−2.14** | **−1.40** | **−1.02** | **−0.87** | **−0.76** | **−0.63** | **−0.48** |
| C1 / V295 | (V295 damps) | (V295 damps) | (V295 damps) | 6.8 | 2.3 | 1.5 | **0.997** | 0.70 |
| C1 / C0 | 0.59 | 0.61 | 0.66 | 0.71 | 0.74 | 0.78 | 0.83 | 0.90 |

**The bound, in plant terms** (EVIDENCE `gate2_C_Kd16.txt`, `gate2_D_Kd16.txt`):
- the refuter's 240 hands-off two-mass rows (fz 10–20 Hz, r2 0.1–0.5, ζ_w 0.01–0.05): **0 unstable**; C1's least-damped
  ζ is below V295's on 168/240 rows (C0: 171); ratio min **0.740**, median 0.975;
- the same rows with the motor-side b at the b_q value (the 3–5 Hz damping the identification did not see), 144 rows:
  **0 unstable**; ratio min 0.644, median 0.958;
- 288 hands-on rows (arms ×1–5 the wheel inertia): **0 unstable**; ratio min 0.488, median 0.982;
- the reconciler's 80 20 Hz stress rows on `harness_freq`'s exact lifted loop: **0 unstable** (V282: 28);
  ζ shift vs the open plant −0.012 … +0.038.

**Why not designed out.** The P term on an angle operand behind the 5.05 Hz output lag and the 100 Hz hold is −90° of
phase relative to a rate operand, so it anti-damps at 5–17 Hz at any useful gain; V295's acceleration operand is +90°.
D on the held rate also anti-damps above ~7 Hz (C1 at 3 m/s, mostly D: −0.42 at 13 Hz). Lowering Kd lowers the 13 Hz
term but removes the 2–5 Hz damping that carries tier A at 1–3 m/s (J_hi binds there at Kd 16). The fresh-operand
cave (C0 §3.5) buys phase but raises M20 7 % and adds a state word. **Design rule adopted: Re(T/ω)₂₀ ≤ V295's at every speed**, which Kd 16 meets at 0.997× (EVIDENCE) and Kd 22 does
not (1.25×, EVIDENCE).

### 2.5 (e) Low speed and friction: the pre-declared miss, and what the first drive measures

EVIDENCE: the friction refuter's own scripts re-run on C1 (`refute_rerun/`), the time harness, and the robust suite.

| symptom | where | predicted size (C1, nominal unless stated) | C0 |
|---|---|---|---|
| dwell-then-jump / hold slips per five-scenario set | 3 / 5 / 5.5 / 6 / 7 m/s | 6 / 7 / 4 / 2 / 0; snap ≤ 1.70° (`expA2`) | 7 / 6 / 4 / 2 / 0 |
| same | 10 / 11.9 / 12.5 m/s | **1 / 3 / 3** (F_hi: 4 / 4 / 4; bc: 4 / 2 / 0) | 0 / 0 / 0 |
| constant-setpoint hunt (`expB2`, last 20 s of 40) | 3 / 4 / 5 / 6 / 7 m/s | p2p 0.35–0.42 / 0.29–0.34 / 0.22–0.27 / 0.16–0.18 / 0.11–0.12°; 4–7 slips per 20 s; T p2p 188 / 160 / 129 / 99 / 68 | 0.23–0.39° at 3–5 m/s |
| slow ramps 0.25–0.5°/s (`expA_ramps`) | 3–7 / 8–12.5 / ≥ 19 m/s | 2–12 / 1–2 / 0 events per 16 s of ramp (two 8 s ramps); snaps 0.31–0.88° / 0.25–0.47° / — | 9–12 / 1 / 0 |
| small-amplitude 0.5 Hz tracking (`expG`) | 8–19 m/s, ±0.2–1° | 0.13–0.96 (stiction against 57–175 T/deg) | 0.14–0.93 |
| holds under road disturbance (`expB_holds`) | ≥ 8 m/s | no limit cycle; error p2p ≤ 0.17°, T 5–30 Hz ≤ 0.96 rms | same class |

**Why no friction term in C1.** The low-speed friction is the least identified part of the plant (Fs 95/65 T at
3/5 m/s, CI ±129). A compensation term sized from the wrong number would trade stick-slip for a limit cycle. **No term
without an instrument.**

**What the first drive measures to size it** (all on the wire, §6.4): the breakaway torque F_s(v) and the Coulomb
level F_c(v) per band from the tap and the angle; the dead-zone width at dwell ends; the hunt amplitude and period at a
constant setpoint at 3–7 m/s; and the dwell-then-jump rate per band against r6c.

### 2.6 (f) The safety defects: prerequisite or firmware form, each

EVIDENCE for the byte facts below (Python on V295, positive-controlled scans; Ghidra decode of `0x29360..0x293C0`).

| item (safety refuter) | flight prerequisite? | cheap firmware form? | in C1? |
|---|---|---|---|
| **F4** a distinct fwVersion + the fork param (torque fork on the angle image, F1) | **YES** | the version string at `0x13100` (and the `.rwd` header). The bootloader's and CRC's view of that string is **not traced** (spec §5.1 UNVERIFIED). | No — a build-step decision once the bootloader check is traced |
| **C3/C5/C4** measured angle while inactive; start from θ_meas | **YES** | — | fork |
| **C8** drop the request unless 0x14A b4 bits 0–2 = 7 | **YES** (fork, cheap) | a cave gate costs ≈ 10–12 bytes (`ld.bu -0x679c[gp]`, e.g. `84 57 65 98` into r10; `cmp 3`; branch to E' = 0 + freeze, or `jr 0x2A164`). **Mid-engagement mode-3 exits are already covered in firmware**: mode 3 leaves only to state 4 on `gp-0x67fe ≠ 2` (B2 skips that tick) or to state 1 on a `−0x8000` baseline (θ wraps to ~+32700, the ±12000 bail). C8 covers engaging without mode 3. EVIDENCE: angle trace §3.1 (all nine handlers decompiled) + B2. BELIEF: a baseline that turns 0x7FFF while mode stays 3 is not excluded by any gate, firmware or fork. | No |
| **F3** camera discrimination (`gp-0x6803 == 2`) | **NO, if** the operator keeps the stock camera LKAS off (procedure; the refuter's do-not-flash list does not include it) | **One byte**: `0x2937C fa 1d` (`bne 0x293BA`) → `f5 1d` (`br`). State 1 then never takes the `0x6803 == 0` arm (`0x29376 ld.bu -0x6803,r15 ; cmp r0,r15 ; bne`). It **switches the engage chain** to states 6/7/8: up-ramp `0xC63FC` = 328 (0.1 s) instead of `0xC63F8` = 33; down-ramp `0xC63FA` = 66; status `gp-0x679f` = 2/4/6 instead of 1/3/5 (16 writers, 0 direct readers found); `gp-0x679e` set (one outside reader, `0x2B35A`); fade-B arm `0xCBAE4[7]` → `0xE54FC` (X 24/45/64/80/96/112, Y 255/205/164/125/90/51) instead of `0xCBBC4[7]` → `0xE564C` (X 16/26/38/48/64/96, Y 255/243/218/179/77/77) — 12 halfwords to copy; fade-A identical; the taper cliff arms (inert under E4). **`gp-0x6803` has readers outside the lane** (`0x2A552…0x2A976`, `0x4E87E`) that are **not traced**. | **No** — a C2 candidate after the census |
| **Δmax(v)** (C6), F4 authority | **YES** | a clamp on E' in the cave (≈ 8 bytes); not designed | No |
| **τ_o ≥ 1 s**, no fork integral below 8 m/s | **YES** — GATE 2 E: τ_o 0.3 s → GM 1.5–2.0 dB on J_hi / b_lo×J_hi at 3 m/s (J1.0 unstable); τ_o 1 s → GM ≥ 11.9 dB on every credible member | — | fork |
| **O1** (override yields) | **YES**: without it the harness's `ov_fade` overshoot is 2.9–4.6° at ≤ 8 m/s on every I policy (P returns the error) | — | fork |
| **F7** the panda's 0xE4 bound under the angle build | **YES** — measure | — | — |
| **F2** RX-task preemption window; the timeout path to `gp-0x6805 = 0xFF` | **YES** — trace before flash (the window is one tick and int32-bounded: EVIDENCE refuter; its existence is BELIEF) | — | — |
| **F5** `0x2913A` dominates `0x29A48` (B2) | **YES** — re-prove on the built image (H6) | — | — |
| **C10** `steerActuatorDelay` | recommended `UseAutoSteerDelay` on drive 1 | — | fork |

### 2.7 Evaluated and not adopted (with the reason, so nobody re-proposes them blind)

| alternative | what it buys | why not |
|---|---|---|
| Kd 22 flat (+ its own table) | 0.5 Hz tracking +0.04–0.06 at 10–12.5 m/s; fewer events at 10–12.5 (0/1/1) | Re(T/ω)₂₀ at highway 1.3× V295's |
| Kd(v) via the in-place re-key (C0 §3.6: `0x29CFC`, `0x29D18`, 8 bytes; Kd 22 ≤ 12.5 m/s, 16 above) | the 10–12.5 m/s gain above | +3 in-place edits and a re-gated envelope; 15–19 m/s still misses (b_q binds there) |
| fI 0.62 | 0.5 Hz tracking at 15–19 m/s +0.05 (linear proxy) | 26–30 m/s 1.05–1.06 nominal, up to 1.11 on b_hi; low-speed envelope −12 % |
| DB 1 (with the re-base, 1 LSB at low speed, 0.15 LSB at highway) | 1–2 fewer events at 3–5 m/s (Kd 22 run) | ess up to 0.39°, 0.5 Hz tracking −0.02…−0.03 |
| a 6th knot at 13 m/s | Kp +2–4 % at 12.5–15 m/s | 6 bytes for ≤ 0.01 tracking |
| THR 1024 | fewer false freezes during hands-on turning | E1/E3 at \|tq\| 700–1000: lurch 2–8°, droop up to 4.1° |
| reset at \|tq\| > 2048 | 0 lurch after a straightening override | 2.1–5.4° after a tightening one; +10 bytes and a RAM write |
| friction compensation | the low-speed miss | no instrument yet (§2.5) |

---

## 3. GATE 2: magnitude and phase in every loop the signal is in

Two independent linear methods on every non-aged point: the stability refuter's `stab_lin` (LTI fundamental +
exact 10-tick periodic monodromy, exact GM by bisection, slot-4 delay chain for the aged hold) and the design's
`harness_freq` (LTI fundamental, M20, L20, |T|, |T_ref|). 100 Hz hold ages 1–10 (11–20 on the `+h10` members),
5.05 Hz output lag, 2 ms transport (0/6/10 ms members). r71b plant family. These are model numbers; the plant above
about 8 Hz is not identified.

### 3.1 The fine grid (EVIDENCE `gate2_A_Kd16_final.txt`; 140 speeds × 26 members = 3 640 points)

| member | tier | min PM (at m/s) | points below the tier bar | min exact GM (dB) | max M20 | max L20 / V295 |
|---|---|---|---|---|---|---|
| nominal | A | 62.3 (1.0) | 0 | 21.4 | 2.28 | 0.636 |
| J_lo | A | 66.3 (27) | 0 | 20.3 | 2.28 | 0.636 |
| J_hi | A | 46.5 (1.0) | 0 | 19.4 | 2.28 | 0.636 |
| b_lo | A | 53.5 (1.0) | 0 | 18.4 | 2.28 | 0.636 |
| b_hi | A | 61.1 (27) | 0 | 24.4 | 2.28 | 0.636 |
| tau0 / tau6 | A | 63.4 / 60.2 (1.0) | 0 | 23.8 / 18.0 | 2.28 | 0.636 |
| b_lo×J_hi | B | 35.2 (10.0) | 0 | 11.3 | | |
| b_lo×J_hi×tau6 | B | **32.7 (10.0)** | 0 | 9.3 | | |
| b_lo×tau6 / J_hi×tau6 | B | 50.7 / 44.8 (1.0) | 0 | 15.3 / 16.7 | | |
| b/1.9×J_hi / b_lo×J0.3 | B | 33.0 (10.0) / 42.1 (1.0) | 0 | 10.6 / 16.1 | | |
| J_hi2 (J 0.8 refit) | B | 39.8 (11.9) | 0 | 15.9 | | |
| **J1.0** | B | **32.0 (11.9)** | 0 | 14.4 | | |
| nominal / b_lo / J_hi, hold +10 ticks | B | 57.0 / 46.5 / 42.3 (1.0) | 0 | 14.7 / 12.0 / 14.0 | | |
| **b_q** | B | **32.8 (27)** | 0 | **7.8** | | |
| J1.3 refit | report | 22.7 (11.9) | 10 below 30° | 12.5 | | |
| ms_free (J 2.08 at 11.9) | report | 7.6 (11.9) | 28 below 30° | 10.7 | | |
| light_b (the prior) | report | **−24.3, unstable ≥ 14 m/s** | | | | |
| tau10, b_lo×tau10, b/1.9 | report | 58.0, 47.9, 53.5 | 0 | | | |

- **Tier A, all points:** no 5–50 Hz closed-loop pole with ζ < 0.2; max(|T_c|, |T_ref|) in 5–30 Hz ≤ −6.6 dB.
- **Method agreement:** |PM(stab_lin) − PM(harness_freq)| ≤ 0.99° on every non-aged point (gate: 1°).
- **What C0 had at the refuter's points** (refuter F1–F3 → C1): J_hi at 11.9 m/s 40.7° → **61.2°**; b_lo×J_hi at 11.5
  17.3° → **37.8°**; J 0.8 refit at 11.9 20.2° → **39.9°**; J 1.3 refit 6.9° → **22.7°** (report: J 1.3 is not
  excluded by the identification at 10–15 m/s, so this is a residual risk, §8).

**PM by member at the design speeds** (°; EVIDENCE same file):

| v | Kp_eff | nominal | J_hi | b_lo | b_lo×J_hi | ×tau6 | J1.0 | J_hi2 | b_q | nom+h10 | b_lo+h10 | J1.3 | ms_free | light_b |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 490 | 62.3 | 46.5 | 53.5 | 36.0 | 34.0 | 41.0 | 42.0 | 62.3 | 57.0 | 46.5 | 40.5 | 57.0 | 25.9 |
| 5 | 520 | 66.8 | 51.0 | 56.2 | 38.6 | 36.5 | 46.9 | 47.3 | 66.8 | 61.2 | 48.7 | 47.5 | 57.0 | 24.3 |
| 8 | 570 | 72.8 | 56.5 | 59.4 | 41.2 | 38.8 | 53.8 | 53.4 | 72.8 | 66.8 | 51.2 | 55.9 | 57.3 | 21.7 |
| 10 | 570 | 77.0 | 59.4 | 70.8 | 35.2 | 32.7 | 43.0 | 46.5 | 77.0 | 72.8 | 64.0 | 39.6 | 23.3 | 22.9 |
| 11.9 | 570 | 75.4 | 61.2 | 77.8 | 38.5 | 36.1 | 32.0 | 39.8 | 75.4 | 72.0 | 72.0 | 22.7 | 7.6 | 24.0 |
| 12.5 | 682 | 76.5 | 63.5 | 78.0 | 39.8 | 37.2 | 36.1 | 43.9 | 52.0 | 73.0 | 72.0 | 26.6 | 12.3 | 16.1 |
| 15 | 1243 | 77.2 | 66.5 | 74.8 | 41.5 | 38.3 | 45.0 | 52.4 | 34.0 | 73.0 | 67.7 | 35.5 | 25.1 | −8.1 |
| 19 | 1748 | 74.5 | 67.1 | 71.7 | 47.2 | 43.9 | 54.5 | 59.1 | 34.0 | 70.1 | 64.3 | 48.3 | 43.5 | −20.3 |
| 26 | 1945 | 66.5 | 62.0 | 64.3 | 51.1 | 48.3 | 56.5 | 58.3 | 33.0 | 62.2 | 57.1 | 54.2 | 60.6 | −23.8 |
| 30 | 1971 | 65.6 | 61.3 | 63.5 | 51.2 | 48.5 | 56.2 | 57.9 | 32.8 | 61.3 | 56.3 | 54.0 | 61.4 | −24.3 |

### 3.2 Bode, nominal (EVIDENCE `page_numbers.txt` §1)

| v | row | 0.1 | 0.3 | 0.5 | 1 | 1.6 | 2 | 3 | 5 | 7 | 10 | 13 | 17 | 20 | 25 | 30 Hz |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | \|L\| | 38.6 | 9.01 | 4.16 | 1.59 | 0.929 | 0.735 | 0.482 | 0.262 | 0.161 | 0.089 | 0.055 | 0.033 | 0.023 | 0.015 | 0.010 |
| | ∠L | −107 | −123 | −124 | −120 | −118 | −119 | −127 | −145 | −162 | 177 | 161 | 141 | 128 | 108 | 89 |
| | \|T_ref\| | 1.013 | 1.104 | 1.223 | 1.263 | 0.964 | 0.780 | 0.467 | 0.179 | 0.078 | 0.029 | 0.014 | 0.006 | 0.004 | 0.002 | 0.001 |
| 8 | \|L\| | 15.6 | 5.27 | 3.22 | 1.66 | 1.05 | 0.834 | 0.536 | 0.279 | 0.167 | 0.091 | 0.056 | 0.033 | 0.024 | 0.015 | 0.010 |
| | ∠L | −90 | −91 | −93 | −99 | −106 | −112 | −124 | −146 | −163 | 176 | 160 | 141 | 128 | 107 | 88 |
| | \|T_ref\| | 1.003 | 1.023 | 1.040 | 1.014 | 0.894 | 0.795 | 0.544 | 0.216 | 0.092 | 0.034 | 0.016 | 0.007 | 0.004 | 0.002 | 0.001 |
| 12.5 | \|L\| | 12.1 | 3.79 | 2.12 | 0.965 | 0.587 | 0.470 | 0.316 | 0.187 | 0.125 | 0.076 | 0.049 | 0.031 | 0.022 | 0.014 | 0.010 |
| | ∠L | −94 | −100 | −102 | −104 | −105 | −107 | −114 | −130 | −146 | −168 | 174 | 152 | 138 | 116 | 95 |
| | \|T_ref\| | 1.006 | 1.040 | 1.047 | 0.863 | 0.608 | 0.490 | 0.307 | 0.143 | 0.074 | 0.032 | 0.016 | 0.008 | 0.005 | 0.003 | 0.002 |
| 19 | \|L\| | 12.9 | 4.27 | 2.54 | 1.24 | 0.755 | 0.591 | 0.370 | 0.191 | 0.118 | 0.069 | 0.045 | 0.028 | 0.021 | 0.014 | 0.009 |
| | ∠L | −92 | −94 | −97 | −103 | −110 | −114 | −124 | −141 | −155 | −172 | 172 | 154 | 140 | 119 | 98 |
| | \|T_ref\| | 1.001 | 1.002 | 0.994 | 0.914 | 0.759 | 0.654 | 0.439 | 0.210 | 0.114 | 0.055 | 0.030 | 0.016 | 0.011 | 0.006 | 0.004 |
| 26 | \|L\| | 18.2 | 5.37 | 2.87 | 1.24 | 0.724 | 0.560 | 0.346 | 0.177 | 0.109 | 0.063 | 0.042 | 0.027 | 0.020 | 0.013 | 0.009 |
| | ∠L | −97 | −106 | −109 | −112 | −116 | −119 | −128 | −143 | −156 | −172 | 174 | 155 | 142 | 121 | 101 |
| | \|T_ref\| | 1.007 | 1.046 | 1.082 | 1.015 | 0.796 | 0.660 | 0.419 | 0.196 | 0.107 | 0.053 | 0.030 | 0.016 | 0.011 | 0.006 | 0.004 |

- Crossover is now ~1.0–1.3 Hz at 12.5–26 m/s (C0: 1.4–1.8 Hz). That is the price of the b_q and J1.0 members.
- The PI peaking is at 0.3–1 Hz (up to 1.26 at 3 m/s, 1.08 at 26 m/s), not in the 1.6–3 Hz hard-turn band.

### 3.3 The hard-turn band and the discriminator (EVIDENCE `page_numbers.txt` §4, §5)

**|T_ref| peak in 1.6–3 Hz:** nominal 0.58–0.96; b_lo 0.84–1.21; J_hi 0.85–1.06; **b_lo×J_hi 1.20–1.58,
b_lo×J_hi×tau6 1.28–1.68** (C0 on the refuter's combination: up to 3.44); J1.0 up to 1.40; b_q up to 1.37.

**Least-damped closed-loop pole, 0.3–8 Hz, by member** (stab_lin exact):

| v | nominal | b_lo | J_hi | b_q | J1.0 | b_lo×J_hi | light_b |
|---|---|---|---|---|---|---|---|
| 12.5 | 0.35 Hz ζ 0.89 | 2.38 / 0.74 | 1.39 / 0.65 | 3.20 / 0.36 | 1.36 / 0.26 | 1.96 / 0.28 | 3.21 / 0.11 |
| 15 | overdamped | 2.93 / 0.61 | 1.86 / 0.63 | 4.10 / 0.18 | 1.75 / 0.32 | 2.55 / 0.26 | 3.78 / **unstable** |
| 19 | overdamped | 2.99 / 0.60 | 1.75 / 0.71 | 4.45 / 0.18 | 1.81 / 0.45 | 2.79 / 0.30 | 4.18 / **unstable** |
| 26 | overdamped | 2.53 / 0.65 | overdamped | 4.24 / 0.21 | 0.95 / 0.81 | 2.48 / 0.43 | 4.36 / **unstable** |

### 3.4 20 Hz, both conventions

| convention | V295 | C1 | gate |
|---|---|---|---|
| M20 (100 Hz hold, 3 ms former) | 3.58 | ≤ 2.28 at every speed and member | ✓ |
| L20 on the same member | — | ≤ 0.636× V295's | ✓ |
| Re(T/ω) at 20 Hz | −0.633 | worst −0.631 (≥ 26.9 m/s) | ✓ (0.997×) |
| the 80 two-mass 13/16/20/24 Hz stress rows | 0 unstable | **0 unstable** (V282: 28) | ✓ |

### 3.5 5–25 Hz damping: §2.4. Two-mass stress: §2.4.

### 3.6 The fork outer loop (EVIDENCE `gate2_E_Kd16.txt`; stand-in L_o = T_ref·e^(−0.06 s)/(τ_o s))

| τ_o | worst GM on nominal / b_lo / J_hi / b_lo×J_hi / ×tau6, 3–26 m/s | J1.0 (not credible below 5 m/s) |
|---|---|---|
| 1.0 s | **≥ 11.9 dB** | 9.7 dB at 3 m/s |
| 0.5 s | 5.9 dB (b_lo×J_hi×tau6, 3 m/s) | 3.7 dB |
| 0.3 s | **1.5–2.0 dB** (J_hi, b_lo×J_hi, 3 m/s) | −0.7 dB (unstable) |

**In the time domain** the τ_o = 1 s integrating stand-in adds 1–4 stick events at 7–19 m/s and raises the step
overshoot to 16–33 % (EVIDENCE `time_pi_score.txt`), as C0 found. The rule stands: **no fork integral on angle error
below 8 m/s, none faster than τ_o = 1 s anywhere; the stock LatControlAngle path stays feed-forward.**

### 3.7 Hold age to 20 ticks (stability refuter F7)

Slot 4 late by 10 whole ticks costs 3.5–8.1° of PM (EVIDENCE `refute_rerun/stab_scan.txt` §4): nominal 57.1–73.2°,
b_lo 46.6–72.0°, J_hi 42.5–62.3° (C0 on b_lo at 26–30 m/s: 37.3–37.6°). The `+h10` members are gated in tier B (§3.1).

---

## 4. Time-domain results, and the refuters' own scripts on C1

### 4.1 Time harness, nominal (EVIDENCE `time_nominal_score.txt`; `harness_time.run` unmodified, C1 lane)

| m/s | Kp_eff | ess° | hold | tg0.2 | tg0.5 | ±1° fit | dj events | T_hf hold | T_hf sin | hunt p2p° | step ov % | hard16 / ref |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 490 | 0.08 | 1.002 | 1.066 | 1.180 | 1.37 | 6 | 0.5 | 2.1 | 2.73 | 10 | 1.43 / 1.80 |
| 5 | 520 | 0.05 | 0.999 | 1.048 | 1.088 | 1.24 | 7 | 0.5 | 1.3 | 1.53 | 14 | 1.31 / 1.69 |
| 5.5 | 529 | 0.05 | 0.999 | 1.041 | 1.067 | 1.21 | 4 | 0.5 | 1.0 | 1.22 | 12 | 1.20 / 1.52 |
| 6 | 537 | 0.03 | 0.999 | 1.035 | 1.046 | 1.18 | 2 | 0.5 | 1.1 | 1.26 | 11 | 1.55 / 1.91 |
| 7 | 554 | 0.03 | 1.000 | 1.021 | 1.008 | 1.12 | 0 | 0.6 | 1.0 | 1.08 | 8 | 2.06 / 2.49 |
| 8 | 570 | 0.03 | 1.000 | 1.006 | 0.974 | 1.05 | 0 | 0.6 | 0.9 | 0.64 | 6 | 1.79 / 2.26 |
| 10 | 570 | 0.05 | 0.997 | 1.017 | 0.955 | 1.08 | 1 | 0.5 | 0.7 | 0.74 | 7 | 1.00 / 1.51 |
| 11.9 | 570 | 0.05 | 0.996 | 1.030 | 0.908 | 1.11 | 3 | 0.5 | 0.7 | 0.66 | 8 | 0.53 / 0.98 |
| 12.5 | 682 | 0.05 | 0.996 | 1.018 | 0.895 | 1.08 | 3 | 0.6 | 0.8 | 0.40 | 6 | 0.50 / 0.91 |
| 15 | 1243 | 0.04 | 1.005 | 0.991 | 0.891 | 0.99 | 0 | 0.6 | 1.4 | 0.02 | 1 | 0.38 / 0.60 |
| 17 | 1692 | 0.05 | 1.003 | 0.981 | 0.886 | 0.96 | 0 | 0.5 | 2.0 | 0.00 | −1 | 0.31 / 0.45 |
| 19 | 1748 | 0.05 | 1.009 | 0.986 | 0.915 | 0.97 | 0 | 0.8 | 2.1 | 0.01 | 2 | 0.26 / 0.38 |
| 22 | 1833 | 0.04 | 1.009 | 1.007 | 0.958 | 1.01 | 0 | 0.6 | 2.7 | 0.02 | 4 | 0.21 / 0.30 |
| 26 | 1945 | 0.04 | 1.011 | 1.020 | 1.008 | 1.01 | 0 | 0.6 | 2.5 | 0.04 | 9 | 0.16 / 0.23 |
| 30 | 1971 | 0.03 | 1.013 | 1.021 | 1.025 | 1.02 | 0 | 0.6 | 2.9 | 0.03 | 13 | 0.13 / 0.19 |

**Safety scenarios** (same file): sentinel L16 peak T 79–280 for ≤ 0.05 s, **0.0° excursion** at every speed (A2);
override-latch overshoot ≤ 0.08° (C0: 0.55–4.23°); request-drop excursion identical for `meas` and `zero` (the
centring hazard stays closed); harness `ov_fade` (no O1) overshoot 0.27–4.64° — P returns the error, so **O1 is a
prerequisite** (§2.6).

**Line-only gate:** no line at any speed on any member (T_hf in the holds ≤ 0.8 counts rms). **Strict texture**
(T_hf in the sinusoids > 2.0 counts) at ≥ 17 m/s: 2.0–2.9 (C0: 2.3–5.4). The 2-count threshold has no N·m scale
(BELIEF, as C0).

### 4.2 Robust members (EVIDENCE `robust_table.txt`; cell = tg0.2/tg0.5, events, hold)

| member | events 3–7 m/s (C1 / C0) | 10–12.5 m/s events (C1 / C0) | tg0.5 at 11.9–19 m/s (C1) | worst hold ≥ 10 m/s |
|---|---|---|---|---|
| nominal | 19 / 19 | 7 / 0 | 0.886–0.915 | 0.996 |
| J_lo | 24 / 25 | 5 / 1 | 0.85–0.91 | 1.00 |
| J_hi | 6 / 7 | 1 / 3 | 0.90–0.98 | 1.00 |
| b_lo | 18 / 17 | 5 / 0 | 0.87–0.93 | 0.99 |
| b_hi | 21 / 20 | 3 / 1 | 0.81–0.91 | 0.99 |
| F_lo | 3 / 3 | 2 / 0 | 0.88–0.92 | 1.00 |
| F_hi | 28 / 25 | 12 / 5 | 0.88–0.92 | 1.00 |
| tau0 / tau6 | 16 / 20, 20 / 20 | 7 / 0, 6 / 0 | 0.88–0.92 | 1.00 |
| **bc** (bias-corrected) | 20 / 20 | 6 / 3 | 0.87–0.91 | 0.99 |
| J1.0 | 5 / 4 | 2 / 5 | 0.92–1.03 | 0.99 |
| J_hi2 | 5 / 5 | 2 / 7 | 0.91–1.02 | 1.00 |
| nominal + 13 Hz / + 20 Hz mode | 18 / 19, 18 / 19 | 7 / 0, 7 / 0 | 0.89–0.92 | 1.00 |

C1 trades C0's stick-free 10–12.5 m/s on the nominal-class members for robustness on the J-class members, which C0
failed (J_hi2 7 events, J1.0 5, J_hi 3 at 10–12.5 under C0). Turn-hold passes everywhere ≥ 10 m/s; 8 m/s holds 0.89
(J1.0) and 0.93 (J_hi2), as C0.

### 4.3 The refuters' own scripts, re-run on C1 (EVIDENCE `refute_rerun/*.txt`; `c1_rerun_refuters.py`)

| script | C0 (the refuter's report) | **C1** |
|---|---|---|
| `stab_scan.py` §1 credible members, 0.5 m/s grid | J_hi 40.7° at 11.9 m/s | **min 46.6° (J_hi, 1 m/s); no credible member < 45°** |
| `stab_scan.py` §2 combined corners | b_lo×J_hi 17.3°, ×tau6 14.4° | **35.3°, 32.8°; none < 30°; none unstable** |
| `stab_scan.py` §3 highway thresholds (26 m/s) | unstable < 0.207× b; PM 30 < 0.368× | **unstable < 0.131×; PM 30 < 0.237×** |
| `stab_scan.py` §4 delay margin / hold +10 | ≥ 46 ms; 37.3° on b_lo at 26–30 | ≥ 73 ticks; ≥ 42.5° |
| `stab_jrows.py` J refits at 11.9 m/s | J 0.8 20.2°, J 1.3 6.9° | **J 0.8 39.9°, J 1.3 22.9°** (report member, §8) |
| `stab_fix.py` J_hi PM-45 / b_lo×J_hi PM-30 limits at 10.5–12.5 | C0 Kp_eff 851–1000 exceeds both | C1 570–682 is under both (limits 809–1062 and 647–830) |
| `xcheck_hf.py` (harness_freq) on the trough | — | J_hi 58–64°; b_lo×J_hi 35–41°, ζ 0.25–0.36, \|T_ref\|₁.₆₋₃ 1.26–1.71 |
| `stab_nl.py` A: 2° step at 12 m/s (nonlinear, friction, quantised) | J_hi×b/1.8 overshoot 1.01° (50 %), 3 crossings | **0.41°, 1 crossing** |
| `stab_nl.py` B: highway with b = 5 | 30 m/s: a sustained 4–6 Hz limit cycle, 0.69° p2p | **none at 19/26/30 m/s** |
| `stab_nl2.py` road noise | 3–6 Hz wheel-rate rms 1.96–2.23 deg/s at b 5 | 0.43–0.45 deg/s at b 5 |
| `stab_hf.py` / `stab_more.py` | — | same conclusions as §2.4, §3.6 |
| `expC_lighthand.py` | lurch 1.0–8.9° at \|tq\| ≤ 1000 | **≤ 0.46° at \|tq\| ≥ 700**; unchanged at \|tq\| 0 (§2.3) |
| `expD_engage.py` | droop 5.9–6.3°, overshoot 1.5–2.3° | droop 6.5–6.9°, **overshoot ≤ 0.08°** |
| `expF_costeer.py` | droop 2.9–3.5° (bleed) | **0.01–0.96°** |
| `expG_smallamp.py` | 0.2 Hz 0.66–0.94 at ±0.2–0.3°, 8–10 m/s | 0.955–1.04; 0.5 Hz unchanged (stiction) |
| `expH_biascorrected.py` (bc) | fails stick at 8/12.5/19, track at 19 | stick 2 at 8, 0 at 12.5/19; tg0.5 0.894 at 12.5/19 (declared) |
| `expA2_harness_midspeeds.py` | 5.5/6 m/s: 4/2 events | 5.5/6 m/s: 4/2 events; 6.5–8: 0; 10: 1 |
| `expB2_hunt_map.py` | hunt 3–5 m/s, 0.23–0.39° | hunt 3–7 m/s, 0.11–0.42° (declared) |
| `expB_holds.py` | highway holds clean | highway holds clean (≤ 0.96 T rms 5–30 Hz) |

**Two run notes.** (1) `stab_nl.py` has no main guard and re-defines its integer constants when run as `__main__`, so
the runner substitutes exactly that one line (450/199 → 225/100). A first run without it doubled the gain and is
discarded. (2) The friction refuter's `selfcheck.py` tests the C0 lane against the C0 table by construction, so on C1
it reports mismatches by design; `c1_selftest.py` replaces it.

---

## 5. Hazards and mitigations (C1)

| hazard | C1 mitigation | residual | E/B |
|---|---|---|---|
| 0xE4 RX fault sentinel 0x7FFF | A2 (request 0xFF → skip) | the one-tick preemption window (task priority untraced), int32-bounded | EVIDENCE guard + sim; BELIEF on preemption |
| `gp-0x67fe ≠ 2` (θ forced to 0) | B2 | none found | EVIDENCE decompile |
| mode-3 exit mid-engagement | B2 (→ state 4) and the ±12000 bail (−0x8000 baseline) | a baseline turning 0x7FFF while mode stays 3 (no gate anywhere) | EVIDENCE angle trace §3.1; BELIEF on the 0x7FFF case |
| engaging without mode 3 | fork C8 | 10 ms + the fork round trip | BELIEF on the fork |
| speed-voter fault | B2 (bVar1 needs `gp-0x67f4 == 1`) | — | EVIDENCE |
| request drop / main-off / panda zero | A2 → ~0.1 s release | Honda's 2 s hand-back gone (operator-facing) | EVIDENCE sim |
| engage init | stateless cave; I = 0 after any skip; **I frozen through the ramp-in** | droop under a handed-over load (§2.3) | EVIDENCE sim |
| override / release lurch (V283's class) | **freeze above \|tq\| 512** + fade + ICL 4096 + fork O1 | a hand below 512; a stale I after a long override (§2.3, §8) | EVIDENCE sim; BELIEF on the sensor scale |
| position-servo authority | P rails at 50.2° (≤ 3 m/s) … 12.5° (≥ 26.9); the fork's Δmax(v) caps demanded P at 0.1·Kp_eff·Δmax: **780 T at 5 m/s (Δmax 15°), 456 T at 10 (8°), 710 T at 20 (4°), 591 T at 30 (3°)** before I | a fork bug = the rail (2461) | EVIDENCE arithmetic; Δmax values BELIEF |
| **low 3–5 Hz damping at speed** (the F4 class) | G(v) sized for PM ≥ 30° at b = 0.25× (floored); R3 a **stop** from the first highway minute | unstable only below 0.131× the fit (b ≈ 3.4 at 26 m/s); the prior light_b world is unstable ≥ 14 m/s | EVIDENCE model; BELIEF physics |
| 5–17 Hz anti-damping | bounded (§2.4) | 6.8× V295's at 13 Hz; no stress row unstable | EVIDENCE model; the plant above 8 Hz is not identified |
| camera 0xE4 on relay close | procedure: camera LKAS off | a comma crash with camera LKAS on | EVIDENCE census; F3 not in C1 |
| torque fork on the angle firmware | F4 (prerequisite) | none if F4 + param | EVIDENCE fw string |
| highway LSB limit cycle | Kp_eff ≤ 1971 (C0's cap was 3000) | sim: no line | EVIDENCE sim; BELIEF on the real quantiser |

---

## 6. The instrument: what proves C1 live in one short drive

C1 adds **no telemetry bit**. Every term is observable from signals already on the wire: 0xE4 sendcan (θ_sp = −raw/10,
request), 0x14A STEER_ANGLE (θ, 100 Hz) and b4, 0x18F rate and STEER_TORQUE_SENSOR (driver torque, wire = raw ×
1.024 → the freeze predicate is a wire predicate), the CAN 427 tap (T = `gp-0x6b38`, `sign(T)<<9 | |T|>>3`, 50 Hz,
wire polarity +sign(cmd)), 0x18F STEER_STATUS. Decode with the patched cereal (slot-137 collision). Take routes from
the device's realdata.

### 6.1 Pre-registered LIVE / NOT-LIVE / REVERT

**Window:** hands-off (|0x18F| < 500 wire), request 1, ≥ 1.2 s after the engage edge, |θ_sp − θ| below the P-rail angle
of the band (§1.4). **Regression** (0.3–3 Hz, θ resampled to the 50 Hz tap):
`tap = c_P·(raw − f14A) + c_I·Σ(raw − f14A)·dt + c_D·ω_18F + c0`.

| band | 0–5 | 5–10 | 10–15 | 15–22 | > 22 m/s |
|---|---|---|---|---|---|
| Kp_eff | 490–520 | 520–570 | 570–1243 | 1243–1833 | 1833–1971 |
| c_P (tap per raw count = Kp_eff/800) | 0.61–0.65 | 0.65–0.71 | 0.71–1.55 | 1.55–2.29 | 2.29–2.46 |
| c_I / c_P | 3.47 s⁻¹ (2π·0.553) | ← | ← | ← | ← |
| c_D (tap per deg/s, opposing) | ≈ 0.32 | ← | ← | ← | ← |

| verdict | condition |
|---|---|
| **LIVE: E-loop** | c_meas/c_raw ∈ [−1.25, −0.80] |
| **LIVE: speed schedule** | c_P within ±30 % of the band prediction in every band with ≥ 15 s of window, **and** c_P(> 22)/c_P(5–10) ∈ [2.5, 5.0] (predicted 3.2–3.8) |
| **LIVE: PI corner** | c_I/c_P ∈ [2.4, 4.5] s⁻¹ |
| **LIVE: the freeze** | in every hands-on episode with \|0x18F\| > 600 wire for ≥ 0.5 s and \|θ_sp − θ\| > 0.3°, the I component (tap − c_P·e − c_D·ω) changes by < 3 tap counts per 0.5 s, where an unfrozen I would ramp ≈ 0.03·G·e(counts) T/s (≈ 12 tap counts per 0.5 s at 1°, 8–12 m/s) |
| **LIVE: A2** | after every request drop, \|tap\| < 20 within 0.15 s |
| **NOT LIVE: wrong image / torque firmware** | \|c_meas\| < 0.2·\|c_raw\| and the tap reproduces V295's raw-only surface (R² ≥ 0.9) |
| **NOT LIVE: cave skipped** (in-place edits only) | c_P ≈ 0.28 in every band (Kp_base 225 without G) |
| **INVERTED** | c_meas/c_raw > 0 → abort |

**I reconstruction (BELIEF until validated on the drive).** `I_n = clamp(I_{n−1} + [not frozen_n]·((Ki_eff·(E_n>>5))>>3))`
at 1 kHz on 100 Hz-held inputs, with frozen_n = (|0x18F| > 524 wire) ∨ (ramp not full, from the request edge + 0.99 s).
Pass: the residual correlates with the reconstruction at r ≥ 0.8.

### 6.2 REVERT (any one; written before the build)

| id | signature |
|---|---|
| R1 | INVERTED |
| R2 | hands-off, request 1, \|tap\| ≥ 300 (the rail) for > 0.3 s |
| **R3 — STOP from the first highway minute** | a growing or sustained 3.5–5.5 Hz oscillation in 0x14A or the 0x18F rate at ≥ 12.5 m/s (the light_b world: unstable 3.8–4.4 Hz at ≥ 15 m/s) |
| R4 | a narrowband 5–30 Hz line in the 0x18F rate or the torque bar absent on V282/V295 |
| R5 | ring presence > 0.5 % or F7 > 0 per 100 s |
| R6 | \|θ − θ_sp\| > 10° hands-off for > 0.5 s at > 8 m/s |
| R7 | after a request drop, \|tap\| still pushing toward 0° for > 0.2 s |
| R8 | STEER_STATUS ≠ 0, or 0x14A b4 bits 0–2 ≠ 7, while engaged |
| R9 | the operator's own words: grinding, ratcheting, a jerk in hard turns |

### 6.3 What the drive identifies (pre-registered discriminator, §3.3)

| if the 0x14A angle at ≥ 12.5 m/s turn-ins shows | then the plant is | next step |
|---|---|---|
| no visible ring | nominal / J_hi class | the highway gain may be raised only after a 3–5 Hz identification |
| a 2.4–3.0 Hz decaying ring, ζ 0.6–0.7 | b_lo | keep |
| a 1.4–1.9 Hz ring, ζ 0.26–0.45 (2–3 visible cycles) | J ≈ 1 (J1.0) | the 10–16 m/s gain is right where it is |
| a 1.96–2.8 Hz ring, ζ 0.26–0.30 | b_lo×J_hi | keep; hard-turn energy is the risk |
| **a 3.2–4.5 Hz ring, ζ 0.18–0.36** | b at ~0.25× of the fit at 3–5 Hz (b_q) | keep; never raise the highway gain |
| a growing 3.8–4.4 Hz oscillation | light_b | **REVERT (R3)** |

### 6.4 What the first drive measures for C2 (friction compensation and the freeze threshold)

All from the wire; each is a within-episode read (one short drive suffices):
1. **Breakaway torque F_s(v)**: at every dwell end (0x18F rate from 0 to > 0.5°/s after ≥ 100 ms stuck, hands-off),
   lane torque (tap × 8) minus the spring estimate k̂(v)·θ (the r71b family's k).
2. **Coulomb F_c(v)**: in slow steady motion (|ω| 0.5–5°/s), lane torque − k̂θ − b̂ω.
3. **Dead-zone width**: |θ_sp − θ| at dwell ends, per band (P-only predicts F_s/(Kp_eff/10) degrees).
4. **Hunt**: in constant-θ_sp windows ≥ 10 s at 3–7 m/s, the θ p2p and period (predicted 0.11–0.42°, period
   7–11 s at 3–5 m/s).
5. **dwell-then-jump rate per band** against r6c (the goal's own metric).
6. **The sensor scale and the freeze duty**: in hands-on episodes, |0x18F| against the lane torque the hand resists
   (tap × 8 + k̂θ), which gives the T-to-sensor ratio; and the fraction of hands-off engaged frames with
   |0x18F| > 524 wire per band and per steering-rate bin.

A friction feed-forward for C2 (BELIEF: ≈ F_c·sign(θ̇_sp) in the cave, ~12 bytes) is sized from items 1–3; the
freeze threshold (a 2-byte immediate) from item 6.

---

## 7. What a FAIL of C1 looks like (written before any build)

### 7.1 In the harness and the adversarial pass: any one means **do not flash**

| id | failure |
|---|---|
| H1 | The interpreter (`c1_assemble.run_bytes`) executing **the built image's** cave bytes differs from `c1_lib`'s cave on any of 200 000 random inputs; or `LaneC1` differs from the original `LaneVec` with the cave off (CHECK 1). |
| H2 | `c1_gate2.py` A on the built image's table: any tier-A point with PM < 45°, exact GM < 6 dB, a 5–50 Hz pole ζ < 0.2, M20 > 3.58, L20 > V295's, or \|T\| or \|T_ref\| > +3 dB in 5–30 Hz; any tier-B point with PM < 30°, exact GM < 6 dB or instability; any method disagreement > 1°; Re(T/ω)₂₀ above V295's at any speed; any two-mass stress row unstable. |
| H3 | The time harness on the nominal plant with the built-image mirror: any line; hold < 0.90 or tg0.2 outside 0.95–1.05 at ≥ 8 m/s; any int32 wrap; the sentinel excursion ≠ 0.0°; the `ov_latch` overshoot > 0.2°. |
| H4 | GATE 1: the cave writes any RAM, or reads any RAM other than `gp-0x6a5e` and `gp-0x4f68`; any new reader or writer of `gp-0x6dd0`. |
| H5 | From the built image (Ghidra): r6, r8, r9 or r13 read before written on any path from `0x29D7A` or from `0x29D7E`; r14 written anywhere between `0x29D7A` and `0x2A1E6` on the PID path; any branch into `0x29D76..0x29D7D`; the cave reachable from a skip path; the hook not decoding as `jarl 0xC4C00, r6`; the `jr` not landing on `0x29D7E`. |
| H6 | With A2 + B2 in the built image: P computed on the 0x7FFF sentinel on any tick; the B2 `cmov` not r8 := (Z ? r27 : 0); `0x2913A` not dominating `0x29A48`. |
| H7 | The table lacks the 0xFFFF row, or the walk reads outside the table for any v in 0..65535. |
| H8 | Any CRC fails `verify_bootloader_crc.py`. |

### 7.2 On the car

| | condition |
|---|---|
| **REVERT** | any of R1–R9 |
| **FAILED its stated goal** | any band ≥ 8 m/s with on-car turn-hold < 0.90 over ≥ 60 s; a new 5–30 Hz line; on-car tracking outside 0.95–1.05 in a band **other than** the declared 11.9–19 m/s 0.5 Hz proxy miss (§8); dwell-then-jump above r6c in a band **other than** the declared 0–7 and 10–12.5 m/s |
| **The pre-declared misses** | §8. They are FAILs of those criteria, declared now; C2 is designed against them from the §6.4 measurements |
| **NOT INTERPRETABLE** | must not happen: LIVE needs ~15–30 s of hands-off frames in two speed bands; ask for one stretch > 22 m/s and one at 5–10 m/s |

---

## 8. The pre-declared misses (each with its band and predicted size)

| # | criterion | band | predicted (sim) | basis |
|---|---|---|---|---|
| M1 | low-speed stick-slip gone; dwell-then-jump ≤ V282 | **0–7 m/s** | 2–7 events per five-scenario set at 3–6 m/s, snaps ≤ 1.70°; slow ramps 2–12 events per 16 s of ramp; **constant-setpoint hunt 0.35–0.42° p2p (3 m/s), 0.29–0.34 (4), 0.22–0.27 (5), 0.16–0.18 (6), 0.11–0.12 (7), period 7–11 s** | EVIDENCE §2.5 |
| M2 | dwell-then-jump ≤ V282 | **10–12.5 m/s** | 1–3 events per scenario set (nominal), up to 4 (F_hi, bc); slow-ramp snaps 0.25–0.47° | EVIDENCE §4.1, §4.2 |
| M3 | tracking 0.95–1.05 (0.5 Hz in-phase proxy) | **11.9–19 m/s** | 0.886–0.915 nominal; 0.81–0.93 on b_hi / b_lo / bc; 0.2 Hz passes (0.98–1.03); \|T_ref(0.5)\| 0.97–1.08 | EVIDENCE §2.2 |
| M4 | tracking at lane-keeping amplitudes ≤ ±1° | 8–19 m/s | 0.5 Hz 0.13–0.96 (stiction) | EVIDENCE §2.5 |
| M5 | release after a ≥ 3 s override that moved the wheel (with O1) | all | 2.0–3.6° at 5–8 m/s, 0.8–1.3° at 12.5, ≤ 0.7° at ≥ 19 | EVIDENCE §2.3 |
| M6 | release after a light hand below the threshold | all | 1.9–8.7° (as C0) if the hand reads < 512 internal counts | EVIDENCE sim; BELIEF on how often |
| M7 | engage under a handed-over load | ≤ 8 m/s | 6.5–6.9° droop if released at once (3.2–3.4° after 1 s); 2.4° at 12.5; ≤ 1.1° at ≥ 19 | EVIDENCE §2.3 |
| M8 | texture (strict reading) | ≥ 17 m/s | 2.0–2.9 counts rms (2-count bar has no N·m scale) | EVIDENCE sim; BELIEF on feel |
| M9 | residual robustness | 10–16 m/s | the J 1.3 refit (not excluded by the identification) has PM 22.7° at 11.9 m/s; ms_free 7.6° | EVIDENCE model |
| M10 | hands-on turning | all | the freeze may be active 25–48 % of turning frames when hands rest on the wheel; 0.5 Hz tracking −0.06…−0.14 in that regime | EVIDENCE route a6 + sim; BELIEF on attribution |

---

## 9. Fork prerequisites (the spec's §5 and §8 carry the detail)

| prerequisite | why (C1 evidence) | status |
|---|---|---|
| F4 fwVersion marker + `AccordEpsAngleLoop` param | a torque fork on this image commands angles (safety F1) | **flight prerequisite**; the bootloader view of `0x13100` untraced |
| C3/C5/C4 | inactive = measured angle; engage from θ_meas | **flight prerequisite** |
| C8 (mode-3 bits) | engage-time gate | **flight prerequisite** |
| C6 Δmax(v) | caps demanded P (§5) | **flight prerequisite** |
| O1 | without it, ov_fade overshoot 2.9–4.6° at ≤ 8 m/s | **flight prerequisite** |
| no fork integral below 8 m/s; τ_o ≥ 1 s | GATE 2 E; time 'pi' suite | **flight prerequisite** |
| C10 `UseAutoSteerDelay` on drive 1 | inner group delay 84–171 ms, speed-dependent (§2.2) | recommended |
| camera LKAS off | F3 not in firmware | **operator procedure for drive 1** |
| panda 0xE4 bound measured; RX preemption + timeout traced; B2 dominance on the built image | safety refuter | **flight prerequisites** (traces, not fork code) |

---

## 10. Concerns and open items

1. **The robustness cost is real and declared.** C1 is slower than C0 at 10–19 m/s (crossover 1.0–1.3 Hz) because the
   refuters' combined members (J ≈ 1 at 10–16 m/s; b at 0.25× at speed) are now gated. If the first drive shows the
   nominal plant (no ring at 12.5–19 m/s turn-ins, §6.3), the next design may relax tier B — **only after** a 1–5 Hz
   FRF above 10 m/s, never on the absence of a complaint.
2. **The cave encodings are BELIEF until Ghidra decodes the built image** (H5), despite 14 encoding controls and the
   0/200 000 interpreter run.
3. **r14 = ramp at the hook** rests on the hook trace's liveness scan plus one Ghidra decode; re-prove on the image.
4. **The sensor scale** (T counts vs gp-0x4f68 counts) is unknown; the freeze threshold and M6 depend on it.
5. **F3's firmware form** is one byte but switches the engage chain; `gp-0x6803` readers at `0x2A552…0x2A976` and
   `0x4E87E`, and `gp-0x679e`'s reader at `0x2B35A`, are untraced.
6. **J 1.3 and ms_free at 10–14 m/s** remain below 30° (report members). The identification cannot exclude J 1.3 there.
7. **Everything above about 8 Hz is model, not measurement.**
8. **The goal names a bleed; C1 freezes.** The operator should rule on the wording.
