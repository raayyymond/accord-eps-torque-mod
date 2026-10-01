# DESIGN C0 (2026-09-30): the angle loop, reconciled into one candidate

**Status: DESIGN ONLY.** Nothing was built, flashed or sent. The fork was not touched. Ghidra was used read-only
(`disassemble_bytes` with `dry_run`, `get_xrefs_to`) on the V294 program, which is code-identical to V295 except cal
`0xC63EA` and its CRC.

**Author:** subagent `reconcile` (Opus), for the orchestrator `main`. This design reconciles the five reports of
2026-09-30:

| short name | report |
|---|---|
| time | `analysis-2020accord/studies/angle_loop/reports/HARNESS-TIME-2026-09-30.md` |
| freq | `…/reports/HARNESS-FREQ-2026-09-30.md` |
| spec | `docs/specs/design/SPEC-angle-setpoint-interface-2026-09-30.md` |
| sentinel | `docs/traces/TRACE-2026-09-30-sentinel-downstream-and-angle-validity-gates.md` |
| hold | `…/reports/HOLD-RECORD-CHECK-2026-09-30.md` |

The hook, angle and speed traces of the same day are cited as "hook trace", "angle trace" and "speed trace".

**Base image:** V295 `_v295_V295-V294BASE-ACCELTRIM.B1050-…TORQUE.TAP_plain_image.bin`, sha256 `5c044d65…52ed`.
Every pre-edit byte quoted below was re-read from it in Python this session.

**New evidence produced here.** The reconcile scripts and their text outputs are copied to
`analysis-2020accord/studies/angle_loop/reconcile_c0/`. The JSON caches are in `_scratch/angle_loop/reconcile/`
(gitignored, regenerable). The scripts are:

| script | what it does |
|---|---|
| `rec_time.py` | the time harness's own byte-exact `LaneVec`, with one insertion that emulates the cave. EVIDENCE that it equals `LaneVec` when G = 256: 0 mismatches in 20 000 random ticks. |
| `rec_time6.py` | the final C0 batch, run through the time harness's own `run()`, `metrics()` and `per_speed_score()`. |
| `rec_freq.py`, `rec_freq_rekey.py`, `rec_freq_edges.py`, `rec_gate2_c0.py`, `rec_mode20.py` | `harness_freq`'s own `metrics`, `gates` and `full`. |
| `rec_joint.py` | the per-speed intersection of the two harnesses. |

Every decision-bearing claim is marked **EVIDENCE** (with the method) or **BELIEF**. Code is cited by address or
grep string, never by line number.

---

## 0. The decision in one page

**C0 =** six in-place code edits (24 bytes), **plus ONE cave of about 140 bytes**, plus calibration.

- The cave multiplies the loop error by a speed gain G(v), so P and I scale together. It also bleeds the
  integrator while the driver is torquing.
- The cave holds **no new RAM state**.

| question | answer | basis |
|---|---|---|
| Is the goal met with zero caves (flat or angle-indexed Kp + bounded I)? | **No.** Both harnesses agree, now on the same candidates. | EVIDENCE §2.1 |
| Can the in-place "re-key" (Kp and Kd LERPs keyed on speed, 8 bytes, the time harness's lead) replace the cave? | **No.** The bytes look sound (§3.6), but a flat Ki cannot serve both ends. At Ki ≤ 300 highway tracking is 0.80–0.93; at Ki ≥ 400 the J_hi member's PM drops below 45° at 3–5 m/s. | EVIDENCE §2.4 |
| What is the minimum cave? | **A gain on E**, `E' = (E·G(v)) >> 8` at `0x29D76`. G is a 6-knot LERP over `gp-0x6a5e`. Optional in the same cave: an I bleed on driver torque, 26 bytes. | EVIDENCE §2, §3 |
| Fresh/fine-angle cave? | **Not in C0.** It does not buy robustness (time §7.1). It removes broadband texture only when combined with three other changes. | EVIDENCE time §10 |
| Edit 5 (D on −rate)? | **YES**, Kd 16 flat. It carries the low-speed phase. | EVIDENCE §2, §4 |
| Edit 6 (I reset at ramp 0)? | **NO.** Superseded by A2. Applying both kills the lane. | EVIDENCE §3.3 |
| Fade cal `0xC63F6` 16 → 328? | **NO.** A2 removes the sentinel pulse outright. 328 still delivers about 1 100 T for 0.1 s. | EVIDENCE time §6.1, sentinel §3.3 |
| A2, `0x29A56` `da 05` → `b2 05`? | **YES.** It closes the 0xE4 sentinel, the disengage-to-centre hazard and the latch wind-up. | EVIDENCE §3.3 |
| B2, `0x29A50` → `cmovne`? | **YES.** It closes the `gp-0x67fe ≠ 2` hole and the speed-fault gain hazard. r8 is dead on the skip path. | EVIDENCE §3.3 (re-verified here) |

**What C0 is predicted to do against the goal.** EVIDENCE (simulation) unless marked. Line-only reading; the strict
texture reading is §2.5.

| speed band | in both harnesses on the nominal plant | across the credible family |
|---|---|---|
| **≥ 8 m/s** | Every goal criterion except one:<br>• tracking 0.995–1.02 at 0.2 Hz;<br>• 0.98–1.05 at 0.5 Hz;<br>• turn-hold 1.00–1.02;<br>• 0 stick-slip events;<br>• no 5–30 Hz line;<br>• M20 1.93–2.67 vs V295's 3.58. | GATE 2 holds on **every** credible member: PM ≥ 47.5°, GM ≥ 12.6 dB. The plant family moves performance to the edge of the windows: 0.5 Hz gain up to 1.10 on `b_hi`, and 1–3 isolated stick events at 8–12.5 m/s on four members. |
| **3–5 m/s** | **Not met.** The ±1° straight-road correction stick-slips: 4 events, 2.1° snaps, stuck 50–75 % of the time. The stiction is Fs 95/65 T counts at 3/5 m/s. | No gain safe on the credible family beats that. **On the half-friction member `F_lo` it is met at 5 m/s.** |

- The low-speed friction CI is ±129 counts, so the drive decides (BELIEF).
- This is the one goal criterion C0 is **predicted to miss**, and the page says so before any build.

**Where the 30 m/s 0.5 Hz gain sits:** 1.050, exactly at the window edge, with ±0.002 batch noise. The cal-only
alternative Ki 188 (fI 0.52) moves it to 1.042, at the cost of one extra 12.5 m/s event. EVIDENCE `rec6_score_nominal.txt`.

---

## 1. The loop in integer form: every byte and every cal

### 1.1 In-place code edits

Ghidra dry-run decode on the V294 program, bytes re-read from V295 in Python.

| id | address | V295 bytes → C0 bytes | V295 instruction → C0 instruction | loop term | basis |
|---|---|---|---|---|---|
| E1 | `0x28F4C` | `24 3f aa 95` → `24 3f 00 96` | `ld.h -0x6a56[gp],r7` → `ld.h -0x6a00[gp],r7` | operand x = θ (0.1° counts). The ±12000 bail at `0x28F50..5A` now applies to θ, which catches the +32700 wrap. | EVIDENCE: Ghidra decode; hw2 `0x9600` = −0x6a00, even = `ld.h`; the same family at `0x40B04` |
| E2 | `0x28FA4` | `89 d1` → `c9 d1` | `subr r9,r26` → `add r9,r26` | r26 = s_old + s_new (the stock sum) | EVIDENCE: decode; stock carries `c9 d1` here |
| B2 | `0x29A50` | `e2 47 00 00` → `e0 df 34 43` | `setfe r8` → `cmovne r0,r27,r8` | r8 := (request == 1) ? bVar2 : 0 | EVIDENCE: form controlled by `0x23954 e0 37 34 33`; field decode: reg2 = r27, reg1 = r0, reg3 = r8, cond 0xA (sentinel trace §4.2). r8 dead on the skip path: §3.3. |
| A2 | `0x29A56` | `da 05` → `b2 05` | `bne 0x29A60` → `be 0x29A5C` | the PID runs **iff ramp ≠ 0 ∧ r8 ≠ 0** | EVIDENCE: Ghidra decode of `0x29A48..0x29A64` (below); Format III with disp 6, cond 2 matches `b2 05` at `0x290E4` |
| E4 | `0x29D6A` | `08 80 ed 80` → `24 87 52 96` | `mov r8,r16 ; mulh r13,r16` → `ld.h -0x69ae[gp],r16` | sp := `gp-0x69ae` = clamp(−4·raw, ±16384), bypassing the 8-bit map index | EVIDENCE: hook trace §3.3; branch targets into `0x29D6A` are `0x29D2A` and `0x29D40` only (Ghidra xrefs plus a raw Python branch scan) |
| H | `0x29D76` | `c2 82 ba 81` → `89 37 8a ae` | `shl 2,r16 ; sub r26,r16` → `jarl 0xC4C00, r6` | the hook into the cave, which re-executes both displaced instructions | encoding **BELIEF until assembled**, by construction against the flown V112 hook `0x55C0E 86 ff 26 ef` = `jarl 0xC4B34, lp` (§3.4). No branch targets `0x29D76` or `0x29D78` (EVIDENCE: Ghidra xrefs empty; raw scan of every Format III/V branch is empty). |
| E5 | `0x29EDE` | `c7 00` → `80 39` | `zxh r7` → `subr r0,r7` | r7 = −Kd | EVIDENCE: decode of `0x29ED8..0x29EEE` |
| E5 | `0x29EE0` | `10 40 bb 41` → `24 47 aa 95` | `mov r16,r8 ; sub r27,r8` → `ld.h -0x6a56[gp],r8` | D = clamp((−Kd·x_rate) >> 3, ±DCL) | EVIDENCE: hook trace §3.4; negation required because sign(dθ/dt) = sign(x) |

**The guard as decoded.** Ghidra dry-run on the V294 program, `0x29A48..0x29A64`:

```
cmp r0,r14 ; setfne r20 ; cmp 0x1,r8 ; setfe r8 (e2470000)
cmp r0,r20 ; bne 0x29a60 (da05)
cmp r0,r8  ; bne 0x29a60 (ba05)
jr 0x2a164
```

**Not applied.** Edit 6 (`0x29A5A` `ba 05` → `b0 05`) and the cal `0xC63F6` stay at their V295 values.

### 1.2 The cave (`0xC4C00`, in the free span `0xC4BD8..0xC4FEF`)

The encodings below follow from the V850E2 formats. Each one is controlled against an instruction of the same form
already present in V295; the control is named in the right column. **BELIEF until assembled and decoded by
Ghidra from the built image.**

```
;  entered by  jarl 0xC4C00, r6  from 0x29D76  (r6 = 0x29D7A, the return)
;  scratch r8 r9 r13, all dead at 0x29D76..0x29D7A (§3.4).  No ep, no lp, no stack, no new RAM.
C0:   shl   2, r16               c2 82        displaced 0x29D76
      sub   r26, r16             ba 81        displaced 0x29D78        r16 = E = 16*(theta_sp - theta)
      ld.hu -0x6a5e[gp], r8      e4 47 a3 95  v, 64 counts per km/h    (form: 0x28F0E e4 57 a3 95)
      mov   TBL, r9              29 06 <TBL>  table pointer            (form: 0x29CFC 30 06 ..)
      ld.hu 0[r9], r13           e9 6f 01 00  X0                       (form: 0x29D26 e6 6f 01 00)
      cmp   r13, r8              ed 41        v - X0                   (form: 0x29E50 ed 41)
      bh    L1                                v > X0 -> walk
      ld.hu 2[r9], r8            e9 47 03 00  G = G0 (clamp low)
      br    APPLY
L1:   ld.hu 6[r9], r13           e9 6f 07 00  X(i+1)
      cmp   r13, r8              ed 41
      bnh   SEG                               v <= X(i+1): segment i (unsigned)
      addi  6, r9, r9            09 4e 06 00
      br    L1                                the sentinel row X = 0xFFFF ends the walk
SEG:  ld.hu 0[r9], r13           e9 6f 01 00  X(i)
      sub   r13, r8              ad 41        dv = v - X(i)
      ld.h  4[r9], r13           29 6f 04 00  S(i), Q12 slope (signed)
      mul   r13, r8, r0          ed 47 20 02  dv*S                      (form: 0x29ED2 ed 3f 20 02)
      sar   12, r8               ac 42                                  (form: 0x29E3E a8 42 = sar 8)
      ld.hu 2[r9], r13           e9 6f 03 00  G(i)
      add   r13, r8              cd 41        G = G(i) + ((v - X(i))*S(i) >> 12)
APPLY:mul   r8, r16, r0          e8 87 20 02  E*G
      sar   8, r16               a8 82        E' = (E*G) >> 8           <-- THE SPEED SCHEDULE (P and I)
      ld.hu -0x4f68[gp], r8      e4 47 99 b0  |driver torque|           (form: 0x35CF8 e4 37 99 b0)
      movea 1024, r0, r13        20 6e 00 04                            (form: 0x52688 20 6e ff 7f)
      cmp   r13, r8              ed 41
      bnh   DONE                              |tq| <= 1024: no bleed
      ld.w  -0x6dd0[gp], r8      24 47 31 92  8*I                       (form: 0x29DA4 24 57 31 92)
      mov   r8, r13              08 68
      sar   6, r13               a6 6a
      sub   r13, r8              ad 41        8I -= 8I >> 6   (tau = 64 ms at 1 kHz)  <-- THE I BLEED
      st.w  r8, -0x6dd0[gp]      64 47 31 92                            (form: 0x2A190 64 c7 31 92)
DONE: jmp   [r6]                 66 00                                  (form: V112 cave 7f 00 = jmp [lp])
TBL:  (6-byte rows, LE: X u16, G u16, S s16)   -- halfword aligned
      b3 02 00 01 f9 00   X  691 (3.0 m/s)  G 256 (1.000)  S  249
      80 04 1c 01 52 01   X 1152 (5.0 m/s)  G 284 (1.111)  S  338
      33 07 55 01 85 03   X 1843 (8.0 m/s)  G 341 (1.333)  S  901
      40 0b 39 02 1c 09   X 2880 (12.5 m/s) G 569 (2.222)  S 2332
      1a 11 8e 05 d4 02   X 4378 (19 m/s)   G 1422 (5.556) S  724
      66 17 ab 06 00 00   X 5990 (26 m/s)   G 1707 (6.667) S    0
      ff ff ab 06 00 00   sentinel: X 0xFFFF, G 1707, S 0
```

**Size and inventory.**
- About 98 bytes of code (30 instructions) plus a 42-byte table.
- The branch displacements are filled at assembly.
- Every instruction maps to one of three loop terms: the displaced E, the G(v) LERP, or the bleed.

**Integer error of the table against the simulated LERP (EVIDENCE: Python, every v in 0..32000).**
- G differs from Honda's `divq` LERP, as simulated, by at most **1 count in 256** (0.4 %).
- The segment ends reproduce the knots to within 1.

### 1.3 Calibration cells

The table lists V295 values and C0 values, read LE from the V295 image. Kp and Kd use the records at live selector 7.
EVIDENCE: pointer reads `0xCB994[7]` = `0xE5378` and `0xCB7D4[7]` = `0xE511C`.

| cell | stock | V295 | **C0** | what it is |
|---|---|---|---|---|
| a `0xC63E8` (s16) | 923 | 1011 | **0** | fb filter pole. 0 makes it a 2-tap FIR. |
| b `0xC63EA` | 1560 | 1050 | **8192** | fb gain. s_new = 8θ exactly. |
| C `0xC62E6` | 7680 | 1024 | **65535** | r26 clamp. Bounds θ at 409.6° (hook trace §3.2). |
| DB `0xC62E4` | 4 | 4 | **0** | I deadband. §2.3 shows why 4 fails. |
| Ki `0xC63E6` | 0 | 0 | **199** | I gain on the base. fI = 7.8125·199/(2π·450) = 0.55 Hz, constant across speed under the E-gain. |
| ICL `0xC61BA` | 10240 | 10240 | **4096** | I clamp. I>>7 ≤ 4096 S, about 660 T, 27 % of the rail. |
| DCL `0xC61B6` | 10240 | 0 | **10240** | D clamp. Back to the stock value. |
| Kp record Y `0xE5384` ×5 | 248/512/645/696/696 | 960 ×5 | **450 ×5** | Kp base. idx no longer matters: the record is flat. |
| Kd record Y `0xE5126` ×4 | 128 ×4 | 0 ×4 | **16 ×4** | D gain on −rate. 0.160·16 = 2.56 T per deg/s. |
| PCL `0xC61BC`, SCL `0xC61BE`, OCL `0xC61B4`, sign-hold `0xC64A3`/`0xC61B8`, output lag `0xC63EC`/`0xC63EE` (992/507), `0xC63F4`/`0xC63F6`/`0xC63F8` | — | V295 | **unchanged** | — |

**CRC.** Assumed from the speed trace's CRC map; not re-checked this session.
- The code edits and the cave dirty trailer `0xC4FFC` only.
- The cals dirty `0xC6FFC`.
- The Kp/Kd records sit in the `0xE5xxx` block, the same block V293–V295 already rewrote.
- The builder must recompute all three and re-run `verify_bootloader_crc.py`.

### 1.4 The loop, integer-exact Python

The fb filter, error and lane epilogue are `lane_mirror_v295.lane_tick` with `x_src='angle'`, `fb_op='sum'`,
`sp_src='69ae'`, `d_src='rate'`. The cave stage is the only new arithmetic. Each line is annotated with its address.

```python
def c0_tick(st, theta, x_rate, sp69ae, v6a5e, tq4f68, ramp, req6805, bvar2):
    # guard 0x29A48..0x29A64 with B2 + A2: run iff ramp != 0 and req == 1 and bVar2 (and inputs valid)
    if not (ramp != 0 and req6805 == 1 and bvar2):
        st.I8 = 0; st.Eprev = 0x7FFFFFFF; S = 0          # 0x2A164 skip: I := 0, S = 0 into the output lag
        return lag_and_gate(st, S)
    s_new = (8192 * theta) >> 10                         # 0x28F8E..0x28FA2, a = 0  -> 8*theta
    r26 = clamp(st.s_old + s_new, -65535, 65535)         # 0x28FA4 add (E2), C = 65535
    st.s_old = s_new
    E = (sp69ae << 2) - r26                              # cave: displaced 0x29D76 shl 2 ; 0x29D78 sub
    G = lerp_q12(TBL, v6a5e)                             # cave: G(i) + (((v - X(i)) * S(i)) >> 12)
    E = s32(E * G) >> 8                                  # cave: mul ; sar 8    (E' = E * G/256)
    if tq4f68 > 1024:                                    # cave: ld.hu -0x4f68 ; cmp ; bnh
        st.I8 -= st.I8 >> 6                              # cave: 8I -= 8I >> 6  (st.w -0x6dd0)
    e5 = E >> 5                                          # 0x29D7C ; DB = 0 -> exc = e5 (0 only at e5 == 0)
    I = clamp((st.I8 >> 3) + ((e5 * 199) >> 3), -(4096 << 10 >> 3), 4096 << 10 >> 3)   # 0x29DA4..0x29DC2
    P = clamp((E * 450) >> 8, -15360, 15360)             # 0x29E36 mul ; 0x29E3E sar 8 ; PCL
    D = clamp((-16 * x_rate) >> 3, -10240, 10240)        # E5: 0x29EDE subr ; 0x29EE0 ld.h -0x6a56 ; DCL
    S = (I >> 7) + P + D                                 # 0x29F18..0x29F24
    st.I8 = I << 3                                       # 0x2A190
    return lag_and_gate(st, fade_and_clamp(S))           # 0x2A0B4.. fade, SCL ; 0x2A174.. 5.05 Hz lag, sign-hold,
                                                         # x ramp, x 5346/32768 (pol), OCL 3072 -> gp-0x6b38
```

**Scale, hands off.** EVIDENCE: arithmetic, time selftest 2.
- E = 16·(θ_sp − θ) in 0.1° counts.
- T ≈ **Kp_eff · 0.01002 T counts per 0.1°**, with Kp_eff = 450·G/256.
- The 427 tap reads T/8, i.e. **Kp_eff/800 tap counts per raw count**.

| v (m/s) | 3 | 5 | 8 | 12.5 | 19 | ≥ 26 |
|---|---|---|---|---|---|---|
| Kp_eff | 450 | 500 | 600 | 1000 | 2500 | 3000 |
| Ki_eff | 199 | 221 | 265 | 442 | 1106 | 1327 |
| T per degree of error (T counts) | 45 | 50 | 60 | 100 | 250 | 300 |
| P reaches the rail at \|e\| = | 54.6° | 49° | 41° | 24.6° | 9.8° | 8.2° |

### 1.5 Overflow budget (EVIDENCE: arithmetic over the operand bounds)

| quantity | worst case | limit |
|---|---|---|
| \|E\| | 16·(4096 + 12000) = 257 536 | — |
| \|E·G\| | 257 536 × 1707 = 4.40·10⁸ | < 2³¹ |
| \|E'\| | 1.72·10⁶ | — |
| \|E'·Kp_base\| | 7.7·10⁸ | < 2³¹ |
| (E'>>5)·Ki | 1.07·10⁷ | — |

- The 0x7FFF sentinel never reaches E (A2 + B2, §3.3).
- No int32 wrap occurred in any C0 time-harness run (the harness's `s32g` counter).

---

## 2. Adjudication: where the harnesses disagreed, the cause, and the C0 values

Both harnesses were re-run on **each other's** candidates and on a shared candidate set. Nothing was averaged.

### 2.1 Low-speed gain and "is the zero-cave set enough" (EVIDENCE: `rec_freq.py`, `rec_joint.py`)

| | time said | freq said | cause, found by re-running | adjudication |
|---|---|---|---|---|
| best Kp at 3–8 m/s | 1200–1500 with Kd 24–28 and Ki 1024 (SPEED-1, FLAT-L) | 637–730 (Kd 16), or about 1100 (Kd 24) | **Different objectives.** Time gates stick-slip at zero events and never gates PM. Freq gates PM ≥ 45 on the family and cannot see friction. | **Neither alone.** In freq, SPEED-1 at 3–8 m/s has PM 28–33° on nominal and **15° on J_hi/b_lo**, with \|T_ref\| 1.8–1.9 in the 1.6–3 Hz hard-turn band (4.1 on J_hi). In time, freq's ROBUST at 3 m/s leaves the ±1° correction **unexecuted** (fit 0.00, wheel 100 % stuck). |
| FLAT-T "3.9 Hz limit cycle" | an amplitude-limited 3.9 Hz oscillation | not tested at Kp 2500 | Freq on FLAT-T at 3–8 m/s: PM −1…+3°, closed-loop pole 4.3 Hz at ζ ≈ 0, GM 0.1–0.9 dB | **Agreement.** The time harness's limit cycle is the linear instability. |
| per-speed intersection | — | — | `rec_joint.py` takes every time line-only pass in the 615-config sweep and checks it on all 7 credible members | **Empty at 3 m/s** (6 time passes, worst PM 9–15°). **Empty at 12.5 m/s** on the time grid (J_hi binds). Non-empty at 5, 8, 19, 26 and 30. |

### 2.2 Crossover and the highway Kp (EVIDENCE: `rec_score_nominal.txt`, `rec6_score_nominal.txt`)

**Freq's designs aimed at fc 2.5–3 Hz**, which needs Kp 4600–5700 at 19–30 m/s. Fc ≥ 2.5 Hz is the freq harness's
own performance criterion, not a goal criterion.

**Re-run in time, the angle LSB sets the highway ceiling:**

| Kp_eff at 26–30 m/s | T counts rms 5–30 Hz in the holds | line? (threshold 2.0) |
|---|---|---|
| 2500–3000 | 0.3–1.4 | no |
| 3520, freq's ROBUST | 5.2–7.3 | **yes** |
| 4628, freq's design | 3.2–6.5 | **yes** |

- This is the 0.1° quantiser relay. Freq predicted it by describing function (BELIEF there); it is now EVIDENCE in sim.
- **Adjudication:** cap Kp_eff at 3000. The crossover at highway is then **1.75–1.78 Hz** (nominal) and 2.85–2.89 Hz
  (b_lo), not 3 Hz.
- The goal's tracking criterion lives below 0.5 Hz, so the PI corner, not the crossover, decides it.

### 2.3 The dead-zone residual (EVIDENCE: `rec_score_nominal.txt`, same gains, DB varied)

**Freq** ran DB = 0 in its linear model. It predicted 0.93–0.99 tracking for its ROBUST schedule and noted that DB 4
becomes 0.85/g° under an E-gain.

**Time**, running the same gains with **DB 4**, measured 0.2 Hz tracking:

| DB | 0.2 Hz tracking at 19–30 m/s |
|---|---|
| 4 | **0.85–0.86** |
| 1 | 0.93–0.95 |
| 0 (C0) | 0.98–1.02 |

- **Cause:** at highway the error during lane-keeping is 1–2 angle LSB. Even 0.15° of deadband idles the I, so the
  loop runs P-only, and P-only DC is Kp′/(Kp′ + k) = 0.86.
- **Adjudication:** DB `0xC62E4` = 0.
- The low-speed anti-hunting argument for DB > 0 did not survive the time harness. DB 1 at 3 m/s gave 7 stick events
  and 1.6° of hunting, against 0 events but a wheel that never moves at DB 4.

### 2.4 Re-key (zero cave) versus the E-gain cave (EVIDENCE: `rec_freq_rekey.txt`; time REKEY-300 rows)

**The re-key is plausible in the bytes (§3.6).** It gives Kp(v) and Kd(v) exactly. **Ki stays one scalar.**

**Freq search** (Kp(v) = the robust edge, Kd(v) searched, Ki flat 0…849):

| flat Ki | speeds passing safety + performance | why the others fail |
|---|---|---|
| 300 (best) | 4/7 | 19–30 m/s tracking 0.85–0.95 |
| ≥ 400 | — | the J_hi member's PM < 45° at 3–5 m/s |

**Time, REKEY-300 DB1:** 1/7 on nominal. 19–30 m/s tracking is 0.79–0.85 and hold 0.88–0.93.

**Adjudication:** the integrator must scale with the speed gain (constant PI corner). Only a cave does that.

### 2.5 The strict texture reading (EVIDENCE: `rec6_score_nominal.txt`, time §10)

| speed | C0 broadband T rms 5–30 Hz during the lane-keeping sinusoids | against the 2.0-count reading |
|---|---|---|
| 3–12.5 m/s | 0.9–2.1 counts | passes |
| 19–30 m/s | 3.1–5.4 counts | **fails** |

- This is setpoint plus feedback quantisation (0.1° each), not a resonance.
- The freq |S| strict reading **passes** on the nominal: max |S| in 5–30 Hz is +1.6…+2.2 dB.
- The 2-count threshold has no N·m scale (BELIEF, time §0.5).
- Removing the texture needs four changes together: a finer setpoint, 1 kHz interpolation, a finer angle and a fresh
  operand. That is a C1 question that the drive must first show is felt.

### 2.6 Other cross-checks

| item | resolution |
|---|---|
| **Sentinel sp** | The brief's 16384 is wrong. With E4 the 0x7FFF store is loaded raw as **32767** (EVIDENCE: the hook trace's fault-path stores at `0x5268C/0x52726/0x527C6` bypass the clamp; time mirror). Moot under A2. |
| **The 100 Hz hold** | Both harnesses already model ages 1–10, the hold report's convention. The freq exact periodic loop equals its LTI fundamental to 0.2 % (freq §2.4). Nothing is double-counted: both use the r71b plant, not the record's tap plant (hold report rec. 3). |
| **"No candidate is robust" (time) vs "ROBUST passes every gate" (freq)** | The two statements were about different candidates and different gates. On the **same** candidate (C0): GATE 2 holds on every credible member (§4.1). The time performance gates hold fully on 4 of 12 members and sit at the window edges on the rest (§4.4). Both statements are now one table. |

### 2.7 Why C0's values (EVIDENCE: rounds 2–4, `rec2…rec6`, all in `_scratch/angle_loop/reconcile/`)

**Kd 16 flat.** Kd 24 adds about 15° of PM at 3 m/s but costs 20 Hz gain at highway.

| Kd | highway M20 | V295's M20 |
|---|---|---|
| 16 | 2.67 (Kp 3000) | 3.58 |
| 24 | 3.28 (Kp 2500, C-A) | 3.58 |

C-A (Kd 24) did no better at low speed: 7 stick events at 3 m/s.

**fI 0.55 Hz** is the one PI corner that serves both ends:

| fI | 19 m/s, 0.5 Hz gain | 26–30 m/s, 0.5 Hz gain | 3 m/s credible edge |
|---|---|---|---|
| 0.45 | 0.93 (fails) | — | — |
| 0.55 | 0.977 | 1.045 / 1.050 | — |
| 0.60 | — | 1.05–1.06 (fails) | Kp 400 |

**Kp_eff 450/500/600/1000/2500/3000:**
- At 3–12.5 m/s Kp_eff is the credible-family safe edge for (Kd 16, fI 0.55), from `rec_freq_edges.py`.
- 19 m/s needs ≥ 2500 for tracking.
- 26–30 m/s sits at the LSB cap.

**ICL 4096.** At 3–8 m/s, ICL 2048 leaves a hold error of 2.8–4.9° and a hold ratio of 0.91–0.95.

| ICL | release overshoot at 3–5 m/s (no bleed) |
|---|---|
| 4096 | 4.7° |
| 10240 | 14–15° |

**The I bleed** (|tq| > 1024, τ 64 ms) changes no tracking or hold number at any speed.

| speed | release overshoot after a 1 s override, without bleed | with bleed |
|---|---|---|
| ≥ 12.5 m/s | 1.5–3.3° | 0.27–0.84° |
| 8 m/s | 4.8° | 2.2° |

---

## 3. Decisions on each edit, with reasons

### 3.1 The cave: REQUIRED, and its minimum content

**Required by the goal's criteria.**
- Tracking at ≥ 8 m/s needs Ki scaled with Kp (§2.4).
- Margin at 3–12.5 m/s needs low gain, while highway tracking needs about 5× more (§2.1, §2.2).
- No in-place edit can do both (EVIDENCE §2.4).

**Minimum content: one multiply of E by a speed LERP.**
- Six knots. Fewer cannot hold the 12.5 m/s J_hi bound: a straight 8→19 m/s line puts Kp 1690 at 12.5 m/s against a
  credible edge of 1000–1200.
- Plus the 26-byte bleed, which the goal names ("a bounded I that bleeds on driver torque").
- **No speed-validity code in the cave.** B2 already skips the PID whenever `gp-0x67f4 ≠ 1`. EVIDENCE: decompile of
  `FUN_00028ea6` in `_scratch/angle_loop/sentinel_gates/dec_28ea6_v294.c`: bVar1 needs all speed channels in range,
  `gp-0x67f4 == 1` and speed < 0x7D01, and the final bVar2 needs bVar1.
- During a voter fault, gp-0x6a5e slews toward 80 km/h. With B2 the PID is skipped, so the freq harness's speed-fault
  instability (Kp 3520–4628 at 3–8 m/s: 4.9–5.4 Hz, ρ > 1) cannot occur.
- **If B2 is dropped, the cave must gain an explicit `gp-0x67f4` gate** (about +10 bytes).

### 3.2 Edit 5 (D on −rate): YES, Kd 16

- **Low speed.** P-only PM at 3–8 m/s is 15–23° (freq §6). With Kd 16 and the C0 gains it is 64.6–70.3° nominal and
  48.7–54.0° worst credible (J_hi).
- **Highway.** D costs M20: 1.93–2.67 total, all below V295's 3.58.
- **20 Hz.** D on the held rate damps only 77 % at 20 Hz (hold report). The 20 Hz stress run (`rec_mode20.py`)
  reports, per plant row:

| | rows | unstable | ζ shift vs the open plant |
|---|---|---|---|
| C0 | 80 | 0 | −0.013…+0.033 |
| V295 | 80 | 0 | — |
| V282 (positive control) | 80 | **28** | — |

### 3.3 Guard edits A2 + B2: YES; edit 6 and `0xC63F6`: NO

**A2: the PID runs iff ramp ≠ 0 ∧ request == 1.** EVIDENCE for the semantics: guard decode §1.1. Simulation (time
§6.1 and C0 runs):

| scenario | without A2 (`0xC63F6` = 16) | with A2 |
|---|---|---|
| sentinel peak T | 2 100–2 290 T for 2.01 s | 76–277 T, decay only, ≤ 0.05 s above 50 |
| sentinel wheel excursion | 30–180° | 0.0° |
| request drop, fork sends 0 vs the measured angle | the two differ | identical; the centring hazard disappears |

**B2** adds bVar2 to the run condition: `gp-0x67fe == 2`, the speed validity, the `gp-0x69aa` range and the
sentinel range.

**r8 liveness on the skip path.** This was the sentinel trace's open item; it is closed here. EVIDENCE: Ghidra dry-run
of `0x2A164..0x2A23C`.
- On every path from `0x2A164`, r8's first touch is a **write**: `0x2A1C2 mov r9,r8` or `0x2A236 setfe r8`.
- No read precedes either.
- r8 ∈ {0,1} on that path in stock as well (the `0x29A64` invalid-input skip).

r27 = bVar2 at `0x29A50` is EVIDENCE within Ghidra's analysed body. That `0x2913A` dominates `0x29A48` is BELIEF,
from the decompile's linear structure (sentinel trace §4.2).

**Edit 6 is superseded.** With A2, ramp == 0 already skips. Applying both makes `bv` never taken, so every tick skips
(spec F1).

**`0xC63F6` stays 16.** Under A2 it only paces the ramp multiplier on an output that is already decaying.

**Cost, operator-facing.** Every disengage becomes a ~100 ms output-lag decay instead of Honda's 2 s PID-held fade.
That is openpilot's normal angle-car behaviour. The operator should know before the drive.

### 3.4 Hook site and register use (EVIDENCE: Ghidra dry-run decodes `0x29D66..0x29D7C`, `0x29D7A..0x29D9C`, `0x29D9C..0x29EDE`)

- **r6.** Written at `0x29D7A` (`mov r16,r6`) and not read between `0x29D76` and there, so it can be the link.
- **r8.** First touch after `0x29D7A` is a write (`0x29E0A`/`0x29E1C`/`0x29E34`).
- **r9.** Written at `0x29D80` (`mov 0,r9`) before any read.
- **r13.** Written at `0x29D8C` or `0x29DA0` before any read.
- **r10 is live** (DB, loaded at `0x29D6E`, read at `0x29D7E`). The cave does not touch it.
- **lp is live** (hook trace §2). The hook uses r6, not lp.
- **ep:** the cave does not use it.

**jarl encoding.** disp = 0xC4C00 − 0x29D76 = 0x9AE8A (even, within ±2 MB).
- hw1 = (6<<11)|(0x1E<<6)|0x09 = 0x3789.
- hw2 = 0xAE8A.
- So the bytes are `89 37 8a ae`.
- Control: the flown V112 hook `0x55C0E 86 ff 26 ef` decodes by the same formula to `jarl 0xC4B34, lp` (Python).
- BELIEF until decoded from the built image.

### 3.5 Fresh / fine angle cave: NOT in C0

- Fresh operands buy +5.9° of PM but raise M20 by 7 % (freq §11).
- They do not restore robustness (time §7.1: 2–4/7 on the off-nominal members).
- They remove texture only when combined with a finer setpoint, interpolation and a finer angle (time §10).
- **Re-open only if** the operator reports highway vibration and the drive shows 5–30 Hz broadband on the 0x18F rate
  above V295's.

### 3.6 The in-place re-key: viable bytes, rejected loop

The time harness's lead is to make `0x29CFC` `ld.bu -0x6a5d[gp],r7` + `br 0x29D10`, and `0x29D18` `br 0x29D6A`.

**EVIDENCE from Ghidra decodes `0x29CB4..0x29EDE`:**
- ep, r6 and r10 are rebuilt before use: ep at `0x29DCC`/`0x29E6E`, r6 at `0x29D7A`, r10 at `0x29D6E`.
- r12 (variant·4) is untouched.
- `gp-0x674B` and `gp-0x697A` have 2 writers each (the live lane and the dead twin) and **0 direct readers**
  (Python dual-form scan, control `gp-0x682f` = 12 ✓).
- Encodings, by arithmetic and controlled: `ld.bu -0x6a5d[gp],r7` = `a4 3f a3 95`; `br +0x10` = `85 0d`;
  `br +0x52` = `95 2d`.

**Rejected on the loop, not on the bytes (§2.4).** It stays the cheapest route to **Kd(v)**, if a later design needs
Kd 24–28 at low speed and Kd ≤ 16 at highway.

---

## 4. GATE 2: magnitude and phase in every loop the signal is in

Method: `harness_freq` exact lifted loop for stability and GM; LTI fundamental for PM, |S| and |T_ref|.
- 100 Hz hold, ages 1–10.
- 5.05 Hz output lag.
- 2 ms transport (0 and 6 ms in `tau0`/`tau6`).
- r71b plant family.
- EVIDENCE: `rec_gate2_c0.txt`. These are model numbers, and the plant above about 8 Hz is not identified.

### 4.1 The EPS angle loop, per speed and plant member

C0 gains: Kd 16, fI 0.55 Hz. Columns: fc (Hz), PM (°), exact GM (dB), phase crossover f180 (Hz), M20 (V295 = 3.58),
L20 (V295 on the same member), max |S| in 5–30 Hz (dB), max |T_ref| in 1.6–3 Hz, least-damped wheel mode (Hz / ζ).

| v | member | fc | PM | GM | f180 | M20 | L20 (V295) | \|S\| 5–30 | \|T_ref\| 1.6–3 | wheel |
|---|---|---|---|---|---|---|---|---|---|---|
| 3 | nominal | 1.39 | 64.6 | 20.7 | 9.73 | 1.90 | 0.0234 (0.0439) | +1.8 | 0.88 | 0.60 / 0.76 |
| 3 | b_lo | 1.86 | 56.9 | 18.6 | 8.71 | 1.90 | 0.0236 (0.0444) | +2.4 | 1.12 | 2.19 / 0.73 |
| 3 | J_hi | 1.08 | 48.7 | 24.9 | 7.87 | 1.90 | 0.0095 (0.0178) | +1.0 | 0.83 | 0.83 / 0.61 |
| 3 | tau6 | 1.39 | 62.6 | 17.9 | 8.02 | 1.90 | 0.0234 (0.0439) | +2.1 | 0.91 | 0.60 / 0.76 |
| 5 | nominal | 1.52 | 68.2 | 20.4 | 9.60 | 1.91 | 0.0235 (0.0440) | +2.0 | 0.90 | 2.49 / 0.79 |
| 5 | b_lo | 2.05 | 57.7 | 18.1 | 8.51 | 1.91 | 0.0237 (0.0444) | +2.6 | 1.09 | 2.36 / 0.63 |
| 5 | J_hi | 1.20 | 52.5 | 24.1 | 7.55 | 1.91 | 0.0095 (0.0178) | +1.1 | 0.95 | 1.13 / 0.60 |
| 8 | nominal | 1.75 | 70.3 | 19.5 | 9.21 | 1.93 | 0.0237 (0.0440) | +2.2 | 0.93 | 2.38 / 0.74 |
| 8 | b_lo | 2.35 | 55.8 | 17.0 | 8.05 | 1.93 | 0.0239 (0.0445) | +2.9 | 1.04 | 2.81 / 0.48 |
| 8 | J_hi | 1.42 | 54.0 | 22.4 | 6.92 | 1.93 | 0.0096 (0.0178) | +1.2 | 1.13 | 1.60 / 0.47 |
| 12.5 | nominal | 1.40 | 69.7 | 22.4 | 10.52 | 2.00 | 0.0231 (0.0413) | +1.6 | 0.86 | overdamped |
| 12.5 | b_lo | 2.37 | 57.6 | 16.3 | 7.91 | 2.00 | 0.0245 (0.0438) | +3.1 | 1.05 | 3.04 / 0.49 |
| 12.5 | J_hi | 1.67 | 47.7 | 17.8 | 5.65 | 2.00 | 0.0099 (0.0178) | +1.5 | 1.30 | 1.95 / 0.43 |
| 19 | nominal | 1.73 | 66.4 | 20.8 | 9.64 | 2.47 | 0.0236 (0.0342) | +2.1 | 0.96 | 1.96 / 0.76 |
| 19 | b_lo | 2.87 | 53.8 | 12.9 | 7.48 | 2.47 | 0.0283 (0.0410) | +4.3 | 1.13 | 3.77 / 0.42 |
| 19 | J_hi | 1.89 | 54.7 | 14.6 | 5.76 | 2.47 | 0.0119 (0.0172) | +2.4 | 1.12 | 2.47 / 0.50 |
| 26 | nominal | 1.78 | 59.7 | 20.5 | 9.38 | 2.67 | 0.0234 (0.0314) | +2.1 | 1.06 | 1.82 / 0.76 |
| 26 | b_lo | 2.89 | 47.5 | 12.6 | 7.38 | 2.67 | 0.0294 (0.0393) | +4.5 | 1.27 | 3.60 / 0.42 |
| 26 | J_hi | 1.73 | 53.2 | 16.1 | 6.17 | 2.67 | 0.0123 (0.0165) | +2.2 | 1.16 | 2.05 / 0.62 |
| 30 | nominal | 1.75 | 59.4 | 20.7 | 9.46 | 2.67 | 0.0232 (0.0311) | +2.1 | 1.06 | 1.74 / 0.78 |
| 30 | b_lo | 2.85 | 47.7 | 12.8 | 7.41 | 2.67 | 0.0292 (0.0391) | +4.4 | 1.26 | 3.54 / 0.43 |
| 30 | J_hi | 1.69 | 53.5 | 16.5 | 6.25 | 2.67 | 0.0123 (0.0165) | +2.1 | 1.15 | 1.95 / 0.65 |

- **Credible family** (nominal, J_lo, J_hi, b_lo, b_hi, tau0, tau6) at all 7 speeds:
  - worst PM 47.5° (b_lo, 26 m/s);
  - worst exact GM 12.6 dB;
  - M20 ≤ 2.67 and L20 below V295's on every member;
  - no 5–50 Hz closed-loop pole with ζ < 0.2.

  **Every freq safety gate passes.** EVIDENCE (`rec_freq_r3.json` / `rec_gate2_c0.json`; J_lo, b_hi and tau0 rows are
  in the txt).
- **Stress members:**

| member | where | result |
|---|---|---|
| J_hi2 | 12.5 m/s | PM 27.6° |
| ms_free (J = 2.03, BELIEF unphysical) | 12.5 m/s | PM 1.6°, ζ 0.01 |
| ms_free | 19 m/s | PM 27.9° |
| light_b (the prior world) | ≥ 12.5 m/s | **UNSTABLE**, 3.6–4.9 Hz, as for every design with a highway gain (freq §10) |

### 4.2 Bode, nominal member

Each speed has three rows: |L|, ∠L (°), |T_ref|.

| v | row | 0.1 | 0.3 | 0.5 | 1 | 1.6 | 2 | 3 | 5 | 7 | 10 | 13 | 17 | 20 | 25 | 30 Hz |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | \|L\| | 35.3 | 8.22 | 3.78 | 1.456 | 0.862 | 0.690 | 0.463 | 0.257 | 0.159 | 0.088 | 0.055 | 0.032 | 0.023 | 0.015 | 0.010 |
| | ∠L | −107 | −123 | −124 | −118 | −115 | −116 | −124 | −143 | −161 | 179 | 162 | 142 | 129 | 109 | 89 |
| | \|T_ref\| | 1.014 | 1.113 | 1.240 | 1.226 | 0.880 | 0.699 | 0.416 | 0.162 | 0.071 | 0.027 | 0.012 | 0.006 | 0.003 | 0.002 | 0.001 |
| 8 | \|L\| | 16.4 | 5.54 | 3.39 | 1.748 | 1.098 | 0.871 | 0.553 | 0.284 | 0.169 | 0.091 | 0.056 | 0.033 | 0.024 | 0.015 | 0.010 |
| | ∠L | −90 | −91 | −93 | −99 | −108 | −113 | −126 | −147 | −165 | 175 | 159 | 140 | 127 | 107 | 88 |
| | \|T_ref\| | 1.003 | 1.023 | 1.041 | 1.027 | 0.928 | 0.837 | 0.583 | 0.229 | 0.097 | 0.036 | 0.017 | 0.008 | 0.005 | 0.002 | 0.001 |
| 12.5 | \|L\| | 17.7 | 5.60 | 3.16 | 1.447 | 0.863 | 0.676 | 0.428 | 0.228 | 0.143 | 0.082 | 0.052 | 0.032 | 0.023 | 0.015 | 0.010 |
| | ∠L | −94 | −100 | −103 | −107 | −112 | −115 | −124 | −142 | −157 | −177 | 166 | 146 | 133 | 112 | 92 |
| | \|T_ref\| | 1.005 | 1.035 | 1.063 | 1.028 | 0.865 | 0.745 | 0.495 | 0.224 | 0.112 | 0.048 | 0.024 | 0.012 | 0.007 | 0.004 | 0.002 |
| 19 | \|L\| | 18.4 | 6.11 | 3.65 | 1.793 | 1.089 | 0.850 | 0.526 | 0.263 | 0.157 | 0.086 | 0.054 | 0.032 | 0.024 | 0.015 | 0.010 |
| | ∠L | −91 | −94 | −97 | −104 | −112 | −117 | −129 | −148 | −164 | 178 | 163 | 144 | 132 | 111 | 92 |
| | \|T_ref\| | 1.001 | 1.007 | 1.013 | 1.006 | 0.956 | 0.894 | 0.679 | 0.327 | 0.172 | 0.080 | 0.044 | 0.023 | 0.015 | 0.008 | 0.005 |
| 26 | \|L\| | 27.9 | 8.28 | 4.45 | 1.937 | 1.127 | 0.870 | 0.531 | 0.264 | 0.156 | 0.085 | 0.053 | 0.032 | 0.023 | 0.015 | 0.010 |
| | ∠L | −97 | −106 | −110 | −114 | −119 | −123 | −133 | −151 | −165 | 177 | 162 | 144 | 132 | 112 | 92 |
| | \|T_ref\| | 1.005 | 1.034 | 1.069 | 1.106 | 1.058 | 0.982 | 0.719 | 0.334 | 0.175 | 0.083 | 0.047 | 0.025 | 0.017 | 0.009 | 0.006 |

**Reading.**
- The PI peaking sits at 0.3–1 Hz: up to 1.24 at 3 m/s and 1.11 at 26 m/s. It is not in the hard-turn 1.6–3 Hz band.
- The tracking criterion is scored only at ≥ 8 m/s, where the peak is ≤ 1.11.
- **BELIEF:** the 3–5 m/s peaking (1.14–1.24 at 0.5 Hz) is the price of an I strong enough to break stiction there.
  It may read as "overshoot-then-correct" at parking speed.
- **Inner-loop equivalent delay at 0.2–0.5 Hz:** 50–110 ms (nominal) and 48–93 ms (b_lo). This replaces torque mode's
  0.15–0.25 s in the fork's `steerActuatorDelay` (spec C10). EVIDENCE: phase of T_ref.

### 4.3 The 20 Hz comparison to V295 (both conventions)

| convention | V295 | C0 (3 / 8 / 12.5 / 19 / 26–30 m/s) | gate |
|---|---|---|---|
| M20 with the 100 Hz hold and 3 ms former (freq) | 3.58 | 1.90 / 1.93 / 2.00 / 2.47 / 2.67 | ≤ V295 at every speed and member ✓ |
| record \|(P+D)/x\|, no hold (time `hf20`) | 3.85 | 2.02 / 2.03 / 2.09 / 2.53 / 2.73 | ✓ |
| \|L(20 Hz)\| on the same member | V295 0.031–0.044 nominal | 0.023–0.024 nominal; 0.029 b_lo | ✓ on all 10 members |
| 13/16/20/24 Hz two-mass stress rows (r2 0.2/0.5, ζ2 0.02/0.05) at 3/8/12.5/19/26 m/s | 0/80 unstable | **0/80 unstable**, ζ shift −0.013…+0.033 | V282: 28/80 unstable (positive control) |

### 4.4 Time-domain gates across the family

C0 with the bleed, line-only reading. EVIDENCE: `rec6_score_robust.txt`. Each cell is `tg0.2/tg0.5 · stick events`;
the line column is the max T rms 5–30 Hz in the holds.

| member | 8 | 12.5 | 19 | 26 | 30 m/s | line (holds) |
|---|---|---|---|---|---|---|
| nominal | 1.00/0.98 · 0 | 1.02/1.00 · 0 | 1.00/0.98 · 0 | 1.01/1.05 · 0 | 1.02/1.05 · 0 | ≤ 1.3 |
| F_lo | ✓ | ✓ | ✓ | ✓ | ✓ (also passes 5 m/s) | ≤ 1.4 |
| tau0 / tau6 / +13 Hz / +20 Hz | ✓ | ✓ | ✓ | ✓ | 1.05 edge | ≤ 1.3 |
| b_lo | ✓ | ✓ | 0.98/0.94 | ✓ | ✓ | ≤ 1.5 |
| J_hi | ✓ | 1 event | ✓ | 1.02/1.05 | 1.02/1.06 | ≤ 0.7 |
| J_lo | 1 event | 1 event | ✓ | ✓ | 1.02/1.06 | ≤ 1.2 |
| b_hi | ✓ | 1 event | ✓ | 1.03/1.09 | 1.03/1.10 | ≤ 1.3 |
| F_hi (2× friction) | 1 event | 3 events | ✓ | 1.02/1.05 | 1.02/1.06 | ≤ 0.9 |
| J_hi2, ms_free (stress) | J_hi2: 0.99/0.94, hold 0.93; ms_free ✓ | ms_free: stable gate fails (freq ζ 0.01) | ✓ | 1.05–1.06 | 1.06–1.07 | ≤ 1.3 |
| light_b (prior) | 9 events | 18 events | **unstable** | **unstable** | **unstable** | 290 |

**Reading.**
- No credible member grows a line.
- Every credible-member miss is either:
  - a 0.5 Hz gain up to 1.10 at 26–30 m/s (PI peaking; tg0.2 stays 1.02–1.03); or
  - 1–3 isolated stick events at 12.5 m/s.
- Both are knife-edge window misses, not instabilities.
- 3–5 m/s stick-slips on every member except F_lo at 5 m/s.

### 4.5 The fork's outer loop

**Stock `LatControlAngle` is a feedforward of the planner's angle.** It closes no loop on the measured angle
(EVIDENCE: spec §0 item 5; time §1). The real outer loop is the path-level loop through the planner. It is not
modelled (BELIEF).

The stand-in is an integrating correction on the ~60 ms-old 0x14A angle (time `outer='pi'`), modelled as
L_o = T_ref·e^(−0.06s)/(τ_o·s).

| τ_o | fc | PM | GM | basis |
|---|---|---|---|---|
| 1.0 s | 0.155–0.165 Hz | 81–84° | 15.7–22.1 dB (nominal and b_lo, all speeds) | EVIDENCE `rec_gate2_c0.txt` |
| 0.3 s | 0.51–0.69 Hz | 42–69° | **5.2 dB at 3 m/s** | same |

**In the time domain** the τ_o = 1 s stand-in adds 1–6 stick events at every speed. The cause is two integrators
against stiction and a quantised, stale angle (EVIDENCE: `rec6_pi.json`; time §8 found the same on every candidate).

**Design rule for the fork (BELIEF on the stand-in, EVIDENCE on the direction):**
- no integral on angle error below 8 m/s;
- none faster than τ_o = 1 s anywhere;
- the operator's StarPilot angle path should stay feedforward.

---

## 5. Hazards and mitigations

| hazard | C0 mitigation | residual | E/B |
|---|---|---|---|
| **0xE4 RX fault sentinel 0x7FFF** (on the car today: 2 s of rail-level push when the lane was already pushing that way) | **A2.** The request is 0xFF, so the PID skips. I := 0, and the output lag decays the pre-fault torque in ~0.05 s. | A one-tick preemption window between the SM's `gp-0x6805` read and the PID, if the RX task can preempt the lane (sentinel trace §6.5; task priority not traced). At most a 1 ms impulse into the 5 Hz lag. | EVIDENCE for the guard and the sim; BELIEF on preemption |
| **`gp-0x67fe ≠ 2`**: θ forced to 0 while the wheel is turned | **B2.** bVar2 is false, so the PID skips on the first tick. | none found | EVIDENCE: decompile (bVar2 requires `gp-0x67fe == 2`) |
| **Mode-3 loss** (`gp-0x679c ≠ 3`) with an in-range wrong angle | Fork contract **C8**: drop the request unless 0x14A b4 bits 0–2 = 7. A2 then skips at once. | 10 ms + the fork round trip. Mode 3 held in 2.3 M healthy frames over 91 routes. | EVIDENCE: angle trace §0.4; BELIEF on the fork |
| **Angle wrap** (+32700 on the −0x8000 baseline) | The ±12000 bail → ST 7, **sticky until key cycle** | LKAS lost for the drive | EVIDENCE: sentinel trace §4.1 |
| **Speed-voter fault** (gp-0x6a5e slews to 80 km/h; a highway gain at low speed would be unstable) | **B2.** bVar1 needs `gp-0x67f4 == 1`, so the PID skips while the voter is faulted. | the voter recovers only within 0x40 of the true vote | EVIDENCE: decompile + speed trace §1.3 |
| **Request drop / main-off / panda forcing raw = 0** ("steer to centre" for 2 s) | **A2.** Skip and a ~100 ms release. Time sim: sending 0 or the measured angle gives an identical excursion. | Honda's 2 s hand-back is gone (operator-facing) | EVIDENCE sim |
| **Engage init** | The cave is stateless. I = 0 and E_prev reset on every prior skip (A2). The output lag has decayed. The 0.99 s ramp-in multiplies the output. | The fork must start θ_sp at the measured angle (C3/C5), or E steps at engage. | EVIDENCE: lane bytes; BELIEF on the fork |
| **Override / release lurch** (V283's known failure class) | The fade (floor 0.297) + **I bleed** (τ 64 ms above \|tq\| 1024) + ICL 4096 + fork O1 (θ_sp follows θ_meas) | Sim **without O1**, release overshoot after a 1 s, 1.5–45° override: 0.27–0.84° at ≥ 12.5 m/s, 2.2° at 8, 4.6–4.8° at 3–5 m/s (P returns the full error, not the I). With O1 it is BELIEF-smaller. | EVIDENCE sim; BELIEF on O1 |
| **Position-servo authority** (the panda bounds nothing on 0xE4) | P saturates at the rail at \|e\| = 54.6/49/41/24.6/9.8/8.2° (3/5/8/12.5/19/≥26 m/s). Hands-off torque per degree is 45–300 T. The fork's Δmax(v) (spec C6: 15/8/4/3° at 5/10/20/30 m/s) caps the demanded P at about 640–1 040 T (26–42 % of the rail) before I. | A fork bug = the full rail (2461) | EVIDENCE: arithmetic; the Δmax values are BELIEF |
| **100 Hz hold of θ and the rate** | Modelled explicitly, ages 1–10, in both harnesses: 5.9° at 3 Hz, 39.6° at 20 Hz. D on the held rate is used only for 2–7 Hz damping (share ≥ 0.97). | D anti-damps above 45.5 Hz (hold report). No identified plant content there. | EVIDENCE: hold report; BELIEF on > 8 Hz |
| **Camera 0xE4 accepted if the relay closes** (up to ±70° as angles) | **Not in C0.** Procedural: the operator keeps the stock camera LKAS off. Follow-up: spec F3 (`gp-0x6803 == 2` interlock). | a comma crash with camera LKAS on | EVIDENCE: spec census; BELIEF on re-engage |
| **Torque fork on the angle firmware** | **Not in C0.** Spec F4: a distinct fwVersion plus the fork param. | Today nothing distinguishes the images. The angle build must not ship to the car without F4 or an operator procedure. | EVIDENCE: spec §0.4 |
| **The highway LSB limit cycle** (freq DF) | Kp_eff capped at 3000 | Sim: no line (≤ 1.4 counts). The real staircase can add (time caveat). | EVIDENCE sim; BELIEF on the real quantiser |

---

## 6. The instrument: what proves C0 live in one short drive

Every signal below is already on the wire. **C0 adds no telemetry bit**, and none is needed:
- the cave's input (speed) and output gain are observable through the 427-tap regression slope by speed band;
- the I state is reconstructible from on-wire signals (BELIEF, method below).

Signals: 0xE4 sendcan (θ_sp = −raw/10), 0x14A STEER_ANGLE (θ), 0x18F rate and driver torque, CAN 427 tap
(T = `gp-0x6b38`, `sign(T)<<9 | |T|>>3`, 50 Hz, wire polarity +sign(cmd)), 0x18F STEER_STATUS, 0x14A b4.
**Decode with the patched cereal** (slot-137 collision memory). Take routes from the device's realdata.

### 6.1 Pre-registered LIVE / NOT-LIVE / REVERT

**Window** (spec §6.1):
- hands-off: |0x18F torque| < 500 wire, request 1;
- ≥ 1.2 s after the engage edge;
- |θ_sp − θ| below the P-rail angle of the band (§1.4).

**Regression:** 0.3–3 Hz band, θ resampled to the 50 Hz tap,
`tap = c_P·(raw − f14A) + c_I·Σ(raw − f14A)·dt + c_D·ω_18F + c0`.

**Prediction per speed band** (EVIDENCE: arithmetic §1.4; tap = Kp_eff/800 per raw count):

| band | 0–5 | 5–10 | 10–15 | 15–22 | > 22 m/s |
|---|---|---|---|---|---|
| Kp_eff (LERP) | 450–500 | 500–780 | 780–1575 | 1575–2715 | 2715–3000 |
| c_P, tap per raw count | 0.56–0.63 | 0.63–0.97 | 0.97–1.97 | 1.97–3.39 | 3.39–3.75 |
| c_I/c_P (s⁻¹) | 3.46 | 3.46 | 3.46 | 3.46 | 3.46 |
| c_D, tap per deg/s, negative | ≈ 0.32 | ≈ 0.32 | ≈ 0.32 | ≈ 0.32 | ≈ 0.32 |

c_I/c_P = 2π·0.55.

| verdict | condition (all must hold for LIVE) |
|---|---|
| **LIVE: E-loop** | c_meas/c_raw ∈ [−1.25, −0.80] in a raw/f14A split regression (spec §6.1) |
| **LIVE: the cave's speed schedule** | c_P within ±30 % of the band prediction in every band with ≥ 15 s of window, **and** c_P(> 22 m/s)/c_P(5–10 m/s) ∈ [3.5, 7] |
| **LIVE: the PI corner** | c_I/c_P ∈ [2.4, 4.5] s⁻¹ |
| **LIVE: A2** | after every request drop, \|tap\| < 20 within 0.15 s (stock fade: about 2 s) |
| **NOT LIVE: wrong image / torque firmware** | \|c_meas\| < 0.2·\|c_raw\| and the tap reproduces V295's raw-only surface (R² ≥ 0.9) |
| **NOT LIVE: cave** (in-place edits live, G stuck or skipped) | c_P(> 22)/c_P(5–10) ∈ [0.7, 1.4], with c_P ≈ 0.56–0.63 everywhere |
| **INVERTED** | c_meas/c_raw > 0. **Abort.** |

**I reconstruction (BELIEF, to be validated on the drive).**
- Within the window, `I_n = clamp(I_{n−1} + Ki_eff·(E_n >> 5) >> 3)`, at 1 kHz on 100 Hz-held inputs.
- Both inputs are on the wire: θ_sp from sendcan, θ from 0x14A.
- The unknowns are the RX phase (0–10 ms) and the reset ticks, which are visible as request/ramp edges.
- Pass: the residual tap − (c_P·e + c_D·ω) correlates with the reconstructed I>>7·0.163/8 at r ≥ 0.8.

### 6.2 REVERT (any one, written before the build)

| id | signature |
|---|---|
| R1 | INVERTED (above) |
| R2 | hands-off, request 1, \|tap\| ≥ 300 (rail) for > 0.3 s |
| R3 | **a growing 3.5–5.5 Hz oscillation** in 0x14A or 0x18F rate at ≥ 12.5 m/s: the light_b world, predicted unstable at 3.6–4.9 Hz |
| R4 | a narrowband 5–30 Hz line in the 0x18F rate or the torque bar that is absent on V282/V295 (how-to §5). Above all 7–10 Hz at ≥ 19 m/s, the LSB relay signature. |
| R5 | ring presence > 0.5 % or F7 > 0 per 100 s |
| R6 | \|θ − θ_sp\| > 10° hands-off for > 0.5 s at > 8 m/s |
| R7 | after a request drop, \|tap\| still pushing toward 0° for > 0.2 s (A2 missing) |
| R8 | STEER_STATUS ≠ 0, or 0x14A b4 bits 0–2 ≠ 7, while engaged |
| R9 | the operator's own words: grinding, ratcheting, or a jerk in hard turns |

### 6.3 What the drive also identifies (pre-registered discriminator)

The closed-loop wheel mode at ≥ 19 m/s turn-ins (EVIDENCE: model, §4.1):

| if the 0x14A angle shows | then the plant is | and the next design step is |
|---|---|---|
| no visible ring; mode 1.7–2.0 Hz, ζ ≥ 0.72 | nominal | C0 holds; highway Kp_eff may not rise (LSB cap) |
| a 3.5–3.8 Hz ring, ζ ≈ 0.42–0.43 (one visible overshoot cycle) | b_lo | keep C0; no gain increase |
| 2.0–2.5 Hz, ζ 0.5–0.65 | J_hi | 12.5 m/s is the binding band |
| a growing 4.6–4.9 Hz oscillation | light_b | **REVERT** |

**Low speed.** Count dwell-then-jump in the 0–5 m/s band against r6c (V282).
- If it is above V282's, the next lever is **friction compensation in the same cave**, sized from the measured
  dead zone.
- More low-speed P/I gain is not the lever (§2.1).

### 6.4 The goal's criteria, as C0 predicts them on the wire

**This table is a prediction.** The operator scores symptoms. "Fixed" is his word, not this page's.

| criterion | C0 prediction (sim, nominal) | on-car read (spec §6.2) |
|---|---|---|
| dwell-then-jump ≤ V282 in every band; low-speed stick-slip gone | **0–5 m/s: predicted MISS** (4 events per ±1° correction, 2.1° snaps; F_lo passes at 5). 8–30 m/s: 0 events. | how-to §7.1 vs r6c |
| tracking 0.95–1.05, ≥ 8 m/s | 0.2 Hz: 0.995–1.021. 0.5 Hz: 0.977–1.050 (30 m/s at the edge). | how-to §7.3 |
| turn-hold ≥ 0.90, ≥ 8 m/s | 0.998–1.016 | how-to §7.3 |
| ring ≤ 0.5 %, F7 = 0, no new 5–30 Hz line | no line in sim (holds ≤ 1.4 counts); 0/80 20 Hz stress rows unstable | how-to §2, §3, §5 |
| 20 Hz loop gain ≤ V295 | M20 1.90–2.67 vs 3.58; record convention 2.02–2.73 vs 3.85 | design-side |
| hard-turn 1.6–3 Hz energy ≤ V282 | hard16 below the reference's own at every speed (1.25/1.80 at 3 m/s … 0.19/0.19 at 30) | rev64-goal band energy vs r6c |

---

## 7. What a FAIL of C0 looks like (written before any build)

### 7.1 In the harness and the adversarial pass: any one means **do not flash**

| id | failure |
|---|---|
| H1 | A byte-exact mirror built **from the built image's cave bytes** differs from `rec_time.LaneCave` on any tick of a 144 000-tick randomised self-test (time selftest 1, extended to G and the bleed). |
| H2 | Any credible member at any of 3/5/8/12.5/19/26/30 m/s, **or at the knot midpoints**, shows any of: PM < 45°; exact GM < 6 dB; M20 > 3.58; L20 > V295's; \|T\| or \|T_ref\| > +3 dB in 5–30 Hz; a 5–50 Hz pole with ζ < 0.2; instability. |
| H3 | The time harness on the nominal plant, using the built-image mirror, loses any of: no line at any speed; tracking/hold/stick passes at 8, 12.5, 19 and 26 m/s; or any int32 wrap. |
| H4 | GATE 1: the cave touches any RAM other than reads of `gp-0x6a5e` and `gp-0x4f68` and the read-modify-write of `gp-0x6dd0`; or a new reader/writer of `gp-0x6dd0` appears outside `FUN_00028ea6` and the cave. |
| H5 | Hook liveness re-derived from the built image fails: r6, r8, r9 or r13 read before written on any path from `0x29D7A`; any branch into `0x29D76..0x29D79`; or the cave reachable from a skip path. |
| H6 | With A2 + B2 in the built image, the mirror computes P on the 0x7FFF sentinel on any tick, or the B2 `cmov` decodes to anything other than r8 := (Z ? r27 : 0). |
| H7 | The table lacks the 0xFFFF sentinel row, or the walk reads outside the table for any v in 0..65535. |
| H8 | Any CRC (`0xC4FFC`, `0xC6FFC`, the `0xE5xxx` block) fails `verify_bootloader_crc.py`. |

### 7.2 On the car

| | condition |
|---|---|
| **REVERT** | any of R1–R9 (§6.2). |
| **FAILED its stated goal** (the build is scored against the goal it was designed for) | Any band ≥ 8 m/s with on-car tracking outside 0.95–1.05 or turn-hold < 0.90 over ≥ 60 s of band data. Or dwell-then-jump above r6c in any band ≥ 5 m/s. Or a new 5–30 Hz line. |
| **The pre-declared miss** | Low speed (0–5 m/s) above r6c. It is a FAIL of that criterion, and C1 (friction compensation) is designed against it. It is not a surprise. |
| **NOT INTERPRETABLE = a design failure on our side** | Must not happen. LIVE/NOT-LIVE above needs only ~15–30 s of hands-off engaged frames spread over two speed bands. Ask the operator for at least one stretch at > 22 m/s and one at 5–10 m/s. |

---

## 8. Concerns and open items

1. **Low-speed friction is the least identified part of the plant.** Fs 95/65 at 3/5 m/s, CI ±129. The 0–5 m/s
   verdict could flip either way: it passes on F_lo. **The drive measures it.**
2. **The cave encodings are BELIEF until assembled.** The branch displacements are not yet computed. The hook bytes
   are by construction. Ghidra must decode the built image, and H1–H8 must run.
3. **B2's r27 = bVar2 at `0x29A50`** is EVIDENCE within Ghidra's analysed body. Dominance is BELIEF. The build's
   adversary must re-prove it on the built image.
4. **The 30 m/s 0.5 Hz tracking is at the window edge** (1.050) on the nominal, and 1.06–1.10 on J_hi/J_lo/b_hi.
   Ki 188 (fI 0.52) is the cal-only fallback.
5. **Texture at 19–30 m/s** is 3.1–5.4 counts rms broadband (strict reading). There is no N·m scale; the operator
   decides whether it is felt.
6. **The fork side is BELIEF:** O1 on override, the measured angle while inactive, the slew from the measured angle at
   engage, Δmax(v), no fast angle integral (§4.5), `steerActuatorDelay` 0.05–0.11 s. **F3 (camera interlock) and
   F4 (fwVersion marker) are prerequisites** for a safe flight and are not in C0.
7. **Everything above about 8 Hz is model, not identified.** The 20 Hz object is bracketed only by the record's
   stress plants.
8. **The I reconstruction instrument (§6.1)** depends on the 0xE4 RX phase, which is not traced. If it fails, I is
   inferred only through c_I.
