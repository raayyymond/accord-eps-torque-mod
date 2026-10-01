# TRACE 2026-09-30 — the LKAS lane's setpoint path and operand hook, and the smallest angle-loop edit set

**Agent:** `tracer-hook` (firmware-codepath-tracer), subagent of `team-lead` / `main`. Study only: nothing built,
flashed or sent. GhidraMCP only for disassembly and decompilation; Python for bytes.

**Goal served:** THE GOAL (2026-09-30): a 1 kHz loop on steering angle `gp-0x6a00` inside `FUN_00028ea6`, fed
by an angle setpoint carried in the 0xE4 `STEER_TORQUE` field, built as the smallest verified edit.

**Image:** V295, `_v295_V295-V294BASE-ACCELTRIM.B1050-...TORQUE.TAP_plain_image.bin`,
sha256 `5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed`.
**Ghidra program used:** the open V294 import (`_v294_...`, sha256 `3143616d…`, analysed). A Python diff over
`[0x13000, 0x100000)` shows V294 and V295 differ only at `0xC63EA..EB` (b 567 → 1050) and the page CRC
`0xC6FFC..FFF`. `0x28EA6..0x2A30E` is byte-identical. Every byte quoted below was re-read from V295 in Python.

**Mirror:** `analysis-2020accord/studies/angle_loop/lane_mirror_v295.py` (run it; it prints every claim marked
MIRROR below, and cross-checks the golden model tick for tick).

Every claim is marked **EVIDENCE** (with method) or **BELIEF**.

---

## 0. Headline

1. **The map path cannot carry an angle.** The setpoint is an 8-bit index: 241 magnitudes over the wire range,
   16.1257 wire counts per step, plus a floor asymmetry of one step. At 0.1 deg per wire count that is a
   **1.61 deg setpoint step**. EVIDENCE (bytes 0x29CB4..0x29D6C; MIRROR counts 241 distinct values).
2. **Three in-place edits give the angle loop's P and setpoint with no cave.** All are same-length
   instruction replacements; none moves a byte after it. EVIDENCE (encodings checked against existing
   instructions in the same image; no branch lands mid-instruction).
   - `0x28F4C` hw2 `aa 95` → `00 96`: x := `gp-0x6a00`.
   - `0x28FA4` `89 d1` → `c9 d1`: `subr` → `add` (back to stock's two-sample sum).
   - `0x29D6A` `08 80 ed 80` → `24 87 52 96`: sp := `ld.h -0x69ae[gp]`, bypassing the index and the map.
   - Cals: `a` `0xC63E8` → 0, `b` `0xC63EA` → 8192, `C` `0xC62E6` → 65535.
   - Result, MIRROR-proven on 20 000 random pairs: `r26 = 16·θ`, `E = 16·(θ_sp − θ)`, `θ_sp = −raw`.
     One wire count is 0.1 deg in `gp-0x6a00`'s own unit, range ±409.6 deg.
3. **Rate damping needs two more in-place halfwords**, at `0x29EDE..0x29EE3`. They give `D = clamp((−Kd·x)>>3)`
   on the 1 kHz rate `gp-0x6a56`. The negation is required: `sign(dθ/dt) = sign(x)` (EVIDENCE, §3.4), so a D on
   `+x` would anti-damp.
4. **These cannot be done without a cave:**
   - a speed-scheduled Kp, because the Kp axis is the demand index;
   - an I that bleeds on driver torque;
   - angle-validity gating beyond the ±12000 gate;
   - a clamp on the 0x7FFF fault sentinel.
5. 🛑 **SAFETY FINDING, applies to V293–V295 on the car now.** On an 0xE4 RX fault, `gp-0x69ae = 0x7FFF`. The
   lane commands sp = +1032, the map maximum, and fades it over **2.048 s**. Honda's sign-hold gate lets it
   through only if the lane was already pushing that way. EVIDENCE for the lane arithmetic (decompile, bytes,
   MIRROR). The motor-level outcome downstream is NOT traced.

---

## 1. The setpoint chain, hop by hop (V295)

| # | address | instruction / operation | width, Q | clamp | value to the next hop |
|---|---|---|---|---|---|
| 1 | `FUN_00021724` | `(u8[gp-0x1428]<<8) \| u8[gp-0x1427]` | u16 BE wire bytes 0-1 | none | `raw` |
| 2 | `0x526CC` | `sxh r6` | s16 | none | `raw` signed |
| 3 | `0x526D2/D4` | `shl 0x2` ; `subr r0,r6` | s32 | none | `−4·raw` |
| 4 | `0x526DA` → `0x526F2` | `jarl FUN_00049a90(r6,−0x4000,0x4000)` ; `st.h r10,-0x69ae` | s16 | ±16384 | `gp-0x69ae` |
| 4f | `0x5268C/0x52726/0x527C6` | fault paths: `movea 0x7fff` then `st.h` (bytes `20 6e ff 7f` at 0x52688, `20 86 ff 7f` at 0x52722, `20 36 ff 7f` at 0x527BC); they also set `gp-0x6805`/`gp-0x6803` to `0xFF` | | | sentinel 32767 |
| 5 | `0x29032` | `ld.h -0x69ae[gp],r13` | s16 | | cmd |
| 6 | `0x28FC8..0x29036` | LIM = LERP(`0xCB844[7]` → `0xE51A8`, speed `gp-0x6a5e`) ; `andi 0xffff` | u16 | V295: flat 16384 | LIM |
| 7 | `0x2903A..0x29044` | `r22 = clamp(cmd, ±LIM)` | s32 | ±16384 | `r22` |
| 8 | `0x29A74..0x29CB2` | taper = LERP(same-sign `0xCB924` / opposite-sign `0xCB8B4`, key `gp-0x682f`). The cliff arms `0xCBA74`/`0xCBA04` are selected only if `gp-0x6803 == 2`; openpilot sends 0. spF = LERP(`0xC6974`, key `gp-0x6830`) is flat 255. | u16 | | taper ∈ [0,255] |
| 9 | `0x29CB4/B8` | `G = (spF·taper) & 0xFFFF` | u16 | | 65025 hands-off |
| 10 | `0x29CBC/C0` | `v = (G·r22) >> 16` (low word of `mul`) | s32 | | |
| 10b | `0x29A86/88` | if `gp-0x682f > [0xC64B8]` then `v = 0` (`jr 0x29CC4`). V295 cal = 255, so this is unsatisfiable. | | | |
| 11 | `0x29CD6` | `sar 0x6` | s32 | | `v` |
| 12 | `0x29CD4/D8` | `mov 1,r8` ; `cmovn −1,r8,r8`: sign = −1 iff v < 0 | | | `r8` |
| 13 | `0x29CDC..0x29CFA` | clamp `[−[0xC64F1], [0xC64F0]] = ±240` ; `idx = \|v\|` | u8 | 240 | `idx` |
| 14 | `0x29D10..0x29D14` | `zxb r22` ; `st.b -0x674b` (the tap's demand byte) | u8 | | |
| 15 | `0x29D18..0x29D68` | `Y = LERP(0xC9A88[7] → 0xE502C, idx)`. X = 0,12,20,24,32,64,96,128,160,240; V295 Y = 0,52,86,103,138,275,413,550,688,1032 | u16 | | `r13` |
| 16 | `0x29D6A/6C` | `mov r8,r16` ; `mulh r13,r16` (16×16 signed) | s32 | Y must stay ≤ 32767 | **sp** |
| 17 | `0x29D72` | `st.h r16,-0x6a32[gp]` (published sp, zero live readers; Python + Ghidra) | | | |
| 18 | `0x29D76` | `shl 0x2,r16` (V294/V295; stock `shl 0x5`) | s32 | | `4·sp` |
| 19 | `0x29D78` | `sub r26,r16` | s32 | | **E** |

**Exact composition (EVIDENCE, MIRROR `setpoint_chain`):**
`idx = |clamp(((G·clamp(clamp(−4·raw,±16384),±LIM)) >> 16) >> 6, ±240)|` and `sp = sign·Y(idx)`.
One idx step is 2²²/(4·65025) = **16.1257 wire counts**. Because of the floor in step 10:
- raw = +1 gives idx 1;
- raw = −1 gives idx 0.

This is a one-step asymmetry (MIRROR).

**If the fork sends an angle in 0.1 deg counts through the map path:**
- The resolution is 1.61 deg.
- The range is 240 idx = 3870 counts = 387 deg.
- To make `4·sp` match a feedback with DC gain `g` (`r26 = g·θ`), the map must satisfy `Y(idx) = g·16.1257·idx/4`:

| feedback form | DC gain g | required Y(240) | mulh limit |
|---|---|---|---|
| a = 0, b = 8192, sum | 16 | 15 481 | inside 32 767 |
| stock a = 923, b = 1560, sum | 30.89 | 29 887 | inside 32 767 |

**Why the map path is rejected.** With any Kp that makes a useful angle loop, each 1.61 deg step is a torque
step. At Kp = 1000 (100 T counts per deg, §3.3) one step is about 160 T counts, 6.5 % of the rail.
EVIDENCE for the arithmetic; the dose is BELIEF.

The live setpoint taper (`0xCB924`/`0xCB8B4`, slot 7) is flat to `|tq|>>5 = 80` (2560 raw) and reaches 0 at
112 (3584 raw). On the map path it shrinks an angle setpoint toward 0, which is the centre. On the angle loop
that is a centring command, not a release. EVIDENCE (records read from V295).

---

## 2. The operand formation, register level (V295, Ghidra listing of the V294 program, bytes re-read)

```
-- fb filter: runs EVERY tick, above the engagement guard ------------------------------------------------
28f4c  ld.h  -0x6a56[gp],r7      24 3f aa 95   x = rate (8 counts per deg/s). ★ THE DISPLACEMENT EDIT SITE
28f50  addi  0x2ee0,r7,r11                     gate: x + 12000
28f54  addi  -0x5dc1,r11,r0 ; 28f58 bnc ; 28f5a jr 0x290b0     |x| > 12000 -> BAIL (r26 = 0, gp-0x3d2c = 2)
28f66  ld.bu -0x3d2c[gp],r9 ; cmp 0x1 ; bne 0x28f82            first valid tick after a bail reads s as 0
28f7c  ld.w  -0x3d30[gp],r26                   s_old (32-bit)
28f86  ld.hu 0x73ea[tp],r16                    b  = 0xC63EA = 1050 (unsigned)
28f8a  ld.h  0x73e8[tp],r9                     a  = 0xC63E8 = 1011 (SIGNED)
28f8e  mul   r16,r7,r0                         r7 = b*x
28f92  mul   r26,r9,r0                         r9 = a*s_old
28f96  ld.hu 0x72e6[tp],r13                    C  = 0xC62E6 = 1024
28f9a  sar   0xa,r7 ; 28fa0 sar 0xa,r9         two SEPARATE floors
28fa2  add   r7,r9                             s_new
28fa4  subr  r9,r26             89 d1          r26 = s_new - s_old   ★ (stock: add r9,r26 = c9 d1, s_old + s_new)
28fa6  cmp   r13,r26
28fa8  st.w  r9,-0x3d30[gp]                    s := s_new
28fac..28fbc                                   r26 = clamp(r26, +-C)
28fbe..28fc6, 290c6, 290ca st.h -0x6a34        gp-0x6a34 = |r26 & ~31| >> 5 (readers: only unreachable code, sec 6)
-- the guard -----------------------------------------------------------------------------------------
29a48  cmp r0,r14 ; setfne r20                 r20 = (ramp gp-0x69b0 != 0)
29a4e  cmp 0x1,r8 ; setfe r8                   r8  = (gp-0x6805 == 1)  STEER_TORQUE_REQUEST
29a56  bne 0x29a60 (on r20)  ; 29a5a bne 0x29a60 (on r8)  ba 05 ; 29a5c jr 0x2a164   SKIP iff ramp==0 && !request
29a60  cmp r0,r25 ; bne ; 29a64 jr 0x2a164     SKIP iff inputs invalid
29a68  ld.bu -0x680a ; 29a70 jr 0x2a0c6        gp-0x680a == 1 lane (zero writers, unreachable; kit memory)
-- setpoint (section 1) ------------------------------------------------------------------------------
29d6a  mov r8,r16  ; 29d6c mulh r13,r16      08 80 ed 80   ★ SETPOINT EDIT SITE (0x29D6A is a branch target; 0x29D6C is not)
29d6e  ld.hu 0x72e4[tp],r10                    DB = 0xC62E4 = 4
29d72  st.h  r16,-0x6a32[gp]
29d76  shl   0x2,r16                c2 82      (stock c5 82)
29d78  sub   r26,r16                ba 81      E = (sp<<2) - r26
-- I --------------------------------------------------------------------------------------------------
29d7a  mov r16,r6 ; 29d7c sar 0x5,r6           e5 = E>>5
29d7e..29d9a                                   exc = e5-DB if e5>DB ; e5+DB if e5<-DB ; else 0
29d9c  ld.hu 0x73e6[tp],r6                     Ki = 0xC63E6 = 0
29da0  ld.hu 0x71ba[tp],r13 ; 29dac shl 0xa ; 29dae sar 0x3   ICL = 10240<<10>>3 = 1,310,720
29da4  ld.w  -0x6dd0[gp],r10 ; 29db0 sar 0x3   I_old (the cell holds 8*I)
29da8  mul r6,r9,r0 ; 29db2 sar 0x3 ; 29db4 add r9,r10
29db6..29dc2                                   r2 = I = clamp(I_old + (exc*Ki>>3), +-ICL)
29de0  mov r2,r24 ; 29de4 shl 0x3,r24          r24 = 8*I  -> st.w @0x2A190
-- P --------------------------------------------------------------------------------------------------
29dc6..29e32                                   Kp = LERP(0xCB994[7] -> 0xE5378, key idx zxh) = 960 flat
29e34  mov r16,r8 ; 29e36 mul r9,r8,r0 ; 29e3e sar 0x8,r8      E*Kp>>8
29e3a..29e5c                                   r9 = P = clamp(.., +-0xC61BC = 15360)
-- D --------------------------------------------------------------------------------------------------
29e5e  ld.w -0x6cf8[gp],r8 ; 29e62..29e7e      r27 = E_prev if -768000 <= E_prev <= 768000 else E   (cmovnc)
29e76..29edc                                   Kd = LERP(0xCB7D4[7] -> 0xE511C, key idx byte r22) = 0
29ede  zxh r7                       c7 00      ★ D EDIT SITE (branch target from 0x29E9E/0x29EB4)
29ee0  mov r16,r8 ; 29ee2 sub r27,r8   10 40 bb 41   dE = E - r27      ★
29ee4  mul r7,r8,r0 ; 29eec sar 0x3,r8 (a3 42)
29ee8..29f06                                   r8 = D = clamp(.., +-0xC61B6 = 0 on V295)
-- sum, fade, sum clamp -------------------------------------------------------------------------------
29f18  sar 0x7,r2 ; 29f1e add r9,r2 ; 29f24 add r8,r2           S = (I>>7) + P + D   (no clamp here)
29f2a  mov r2,r22 (-> gp-0x6b34) ; 29f2e mov r8,r27 (-> gp-0x6b36) ; r29 = P (-> gp-0x6b32)
29f08..29fe8   A = r25 ? LERP(0xCBB54) : LERP(0xCBC34), key gp-0x6830 (r21)    r25 = (gp-0x6803 == 2)
29fe2..2a0b0   B = r25 ? LERP(0xCBAE4) : LERP(0xCBBC4), key gp-0x682f (r1)
2a0b4  mulu r9,r23 ; 2a0b8 andi 0xffff ; 2a0bc sar 0x8 ; 2a0be mul r2,r12 ; 2a0c2 sar 0x8   S*f>>8
2a13e..2a162   clamp +-0xC61BE (15360); + rail via ld.h (signed: latent defect if > 32767) ; sxh
-- the shared epilogue -------------------------------------------------------------------------------
2a164  mov 0,r24 ; mov 0,r29 ; mov 0,r27 ; mov 0,r22 ; 2a16c mov 0x7fffffff,r16 ; 2a172 mov 0,r12   (SKIP routes only)
2a174  ld.hu 0x73ee[tp],r7 ; 2a178 ld.w -0x3d3c[gp],r9 ; 2a17c st.h r12,-0x6b2e
2a18c  st.w r16,-0x6cf8[gp]   E_prev (0x7FFFFFFF on skip)
2a190  st.w r24,-0x6dd0[gp]   8*I     (0 on skip)
2a180/2a194/2a1a0/2a1a6/2a1a8/2a1aa/2a1ac   output lag: s' = (992*s>>10)+(507*S>>10); y = (s+s')>>5; 5.05 Hz, DC 0.990
2a198..2a1e4   SIGN-HOLD GATE: if [0xC64A3]==1 && gp-0x6806==0: T := 0 if |y| <= [0xC61B8]=102 or y*gp-0x6b30 <= 0
2a1e6  mul r14,r9 ; sar 0xf ; sxh               y * ramp(gp-0x69b0, Q15) >> 15  -> gp-0x6b30
2a1ee  ld.h 0x7cd0[tp],r7 (5346) ; 2a1f2 ld.b -0x6752 (pol) ; 2a1f6 mulh ; 2a1fc add r9,r11 (addend gp-0x6b2c == 0) ; 2a1fe mul ; 2a202 sar 0xf
2a204..2a220   clamp +-0xC61B4 (3072) ; 2a23c st.h -> gp-0x6b38 (lane torque; rail 2461 at S=15360)
```

**Register liveness.**

- **At `0x28FA4` (subr).** Live: r9 (s_new), r26, r13/r14 (C), r10 (speed), r15 (driver torque), r6, r21, r28,
  r29, r1, r2, lp, r24. Dead: r7 after the add. EVIDENCE (listing scan).
- **At `0x29D78` (sub), after it executes.** EVIDENCE (Python first-use scan of the listing, every register to the
  function end).
  - Live: r16 (E), r10 (DB), r12 (sel·4), r7 (idx), r22 (idx byte, the Kd key), r21, r1, r25, r14 (ramp),
    r11 (addend), r15 (read at 0x2A228), r20 (read at 0x2A2A0), and **lp** (reused as scratch, live
    0x29A2C→0x2A29A).
  - Dead or free: r2, r6, r8, r9, r13, r17, r18, r19, r23, r24, r26, r27, r28, r29, ep.
  - r26 has no read after 0x29D78 on the PID path. Its next touch is the write at 0x29F76.
- **At `0x29D6C`.** r8 (sign) and r13 (Y) are dead after the `mulh`: r8 is next written at 0x29E0A/0x29E34 and
  r13 at 0x29D8C/0x29DA0. This is why the 4-byte `ld.h` can replace both instructions.

---

## 3. The minimal angle-loop edit set

### 3.1 (a) Displacement only: `0x28F4E` `aa 95` → `00 96`

- **On the V295 base (`subr`, a 1011, b 1050, C 1024):** this does NOT give an angle loop.
  - `r26 = s_n − s_{n−1}` with `s = LPF(θ)`, so `r26 = LPF_2Hz(Δθ) · b/(1024−a)`. That is a **low-passed wheel
    rate**: 0.8077 counts per deg/s. MIRROR: 8.079 at 10 deg/s and 40.39 at 50 deg/s.
  - Then `P = 15·sp − 3.75·r26`. That is a **DC rate damper of 0.49 T counts per deg/s** rolled off at 2 Hz, in
    place of V295's acceleration trim.
  - Note that this is the evening verdict's "DC rate term" class, from 2 bytes. It is a damping lever, not the
    angle loop.
  - **Overflow ceiling:** `a·s` overflows int32 if `b·θ_max/13` exceeds 2.12 M. That means b ≤ about 5500 at
    θ ≤ 5000 counts.
- **On the V282 / stock structure (`add`):**
  - `r26 = s_old + s_new ≈ (2b/(1024−a))·LPF_16.5Hz(θ)`. With stock a/b that is **30.89·θ**; MIRROR gives 3062 at
    θ = 100 (the −27 is the known floor bias).
  - The clamp is a u16 cal (`ld.hu`, compare signed). The stock value 7680 saturates at 24.9 deg. V295's 1024
    would saturate at 6.3 counts with V295's a/b, or at 3.3 deg with stock a/b. Cal-only can open it to 65535,
    which is θ ≤ 2121 counts (212 deg) at 30.89.
  - The 16.5 Hz pole is pure loop lag on an angle operand.

### 3.2 (b) The angle loop: two code halfwords plus cals, setpoint still on the map

| edit | bytes |
|---|---|
| `0x28F4E` hw2 | `aa 95` → `00 96` |
| `0x28FA4` | `89 d1` → `c9 d1` |
| `0xC63E8` a | `f3 03` (1011) → `00 00` |
| `0xC63EA` b | `1a 04` (1050) → `00 20` (8192) |
| `0xC62E6` C | `00 04` → `ff ff` |

- **Feedback:** with a = 0 the filter is a 2-tap FIR. `s_new = (8192·θ)>>10 = 8θ` exactly, so
  `r26 = 8θ[n−1] + 8θ[n]`. That is `16θ` with a half-sample (0.5 ms) average and no pole.
- **Range:** C = 65535 bounds |θ| at 4096 counts (409.6 deg).
- **Setpoint:** the map must be `Y = 64.5·X` (Y(240) = 15 481). That gives 1.61 deg steps, so this variant is
  **rejected** (§1).
- **a = −1024 is NOT safe.** It cancels the state into a pure gain, but it places a pole at z = −1. The state
  integrates a Nyquist-rate toggle of the angle LSB without bound. Use a ≥ 0.

### 3.3 (b′) Add the setpoint edit: `0x29D6A` `08 80 ed 80` → `24 87 52 96` (`ld.h -0x69ae[gp],r16`)

**Encoding check.**
- Format VII: hw1 = (16<<11) | (0x39<<5) | 4 = `0x8724`; hw2 = −0x69ae = `0x9652`, which is even, as `ld.h`
  requires.
- The same family already in this image: `0x29032` = `24 6f 52 96` (ld.h -0x69ae,r13).
- The x edit follows the same check: `0x28F4C` stays `24 3f`, with disp `0x9600` = −0x6a00.
- The existing `ld.h -0x6a00[gp],r14` at `0x40B04` reads `24 77 00 96`.

**The loop, in integer form.** Every line is MIRROR-proven where marked.

```
theta_sp = -raw                              (0.1 deg per wire count, = gp-0x6a00's unit; range +-4096)
r26 = 8*theta[n] + 8*theta[n-1]                                  (= 16*theta at rest; MIRROR)
E   = (gp-0x69ae << 2) - r26 = 16*(theta_sp - theta)             (MIRROR, 20 000 random pairs, exact)
I   = clamp(I + ((dz(E>>5, DB) * Ki) >> 3), +-([0xC61BA]<<7))    contributes I>>7 <= [0xC61BA]
P   = clamp((E*Kp) >> 8, +-[0xC61BC])  = clamp(e*Kp/16, +-15360) e = theta_sp - theta in counts
S   = clamp((((A*B)&0xFFFF)>>8) * ((I>>7) + P + D) >> 8, +-[0xC61BE])
T   = clamp(pol*5346*((lag(S)*ramp)>>15) >> 15, +-[0xC61B4])
```

**What the numbers mean.**
- At full ramp, hands off: **T ≈ Kp/100 T counts per 0.1 deg**. EVIDENCE, arithmetic: 0.1631 · 254/256 · 0.990
  · Kp/16. For example, Kp = 1000 gives 100 T counts per deg.
- P reaches its clamp at `e = 15360·16/Kp` (24.6 deg at Kp 1000).
- The rail stays 2461. **Authority stays inside the existing clamps.** EVIDENCE.

**Overflow budget.** EVIDENCE (operand bounds from the bytes).
- |sp| ≤ 16384, or 32767 for the sentinel.
- |E| ≤ 196 603.
- `E·Kp` stays below 2³¹ for **Kp ≤ 10 922**. The `mul` keeps only the low word.

**Removed by the setpoint edit:** LIM(speed), the setpoint taper, the 240 clamp, the floor asymmetry and the
`gp-0x682f > 0xC64B8` zeroing.

**Still computed but no longer used for sp:** idx is still formed from `r22`. It keys Kp and Kd, so Kp is
scheduled on |θ_sp|/1.61 deg, not on speed. It is also stored to `gp-0x674B` and `gp-0x697a` (telemetry).

**BELIEF, plant from the record.** k is 7–80 T counts per deg. A P-only angle loop therefore holds a turn with
a steady error of k/(Kp/10) of the angle, which is large at highway k. **The I is on the critical path, not
optional.** The angle setpoint replaces the torque feedforward the fork used to send.

### 3.4 (c) Rate damping without a cave: `0x29EDE` `c7 00` → `80 39`, `0x29EE0` `10 40 bb 41` → `24 47 aa 95`

**The edit.**
- `0x29EDE`: `zxh r7` → `subr r0,r7`, so r7 = −Kd. 0x29EDE is a branch target, which is fine; the new instruction
  starts there.
- `0x29EE0`: `mov r16,r8 ; sub r27,r8` → `ld.h -0x6a56[gp],r8`. This is a 4-byte for 4-byte swap; 0x29EE2 is not
  a branch target.

**The result.**
- `D = clamp((−Kd·x) >> 3, ±[0xC61B6])`. MIRROR: Kd 16 at x 80 gives −160.
- Damping is **0.16·Kd T counts per deg/s**. V295's 2.96 at 2 Hz corresponds to Kd ≈ 18.
- `0xC61B6` must be raised from 0, for example to the stock 10240.
- `E_prev`/`gp-0x6cf8` and `r27` become irrelevant to D. `gp-0x6cf8` is still written at 0x2A18C.

**Why the negation is required.** EVIDENCE, three links:
1. Mode-3 `STEER_ANGLE` wire = −`gp-0x6a00`. Bytes at 0x40B04/08/0E/18 are `ld.h -0x6a00,r14` ;
   `mov r0,r26` (00 d0) ; `sub r14,r26` (ae d1) ; `st.h r26,-0x69ec`.
2. The rate wire = (−x)>>3. Bytes at 0x40B48/4C/4E are `ld.h -0x6a56,r9` ; `subr r0,r9` (80 49) ;
   `st.h r9,-0x69ea`.
3. The DBC factors are −0.1 and −1 (the fork's `honda_civic_hatchback_ex_2017_can_generated.dbc` lines 521-522).
   The redo audit measured `d(steeringAngleDeg)/dt ÷ steeringRateDeg` = +1.002…1.007 on three routes.

Together these give **dθ/dt = +1.25·x counts/s**: the same sign as x. So `E = 4sp − r26` with `r26 = +16θ`
is negative feedback, as in the flown rate loop, and a D on +x would be positive rate feedback.

**BELIEF.** D on the raw 1 kHz rate, behind only the 5 Hz output lag, is V282's class of delayed rate feedback.
It must pass GATE 2 at 15–25 Hz before any dose.

**Why not the stock D on E.** On the angle error, D sees ±16 per 0.1 deg tick of θ. At 10 deg/s that is a
100 Hz impulse train of about 5 T counts after the output lag (arithmetic; BELIEF on audibility).

### 3.5 Optional: reset I whenever the ramp is 0, `0x29A5A` `ba 05` → `b0 05` (`bne` → `bv`)

**The edit.** After `cmp r0,r8` with r8 ∈ {0,1}, OV is never set, so `bv` is never taken. The skip then fires
iff `ramp == 0`, whatever the request bit.

**Why.** On the stock guard the PID keeps running, and I keeps integrating, whenever the request bit is 1 with
ramp 0. That is the override-latch state; see §4. EVIDENCE for the guard (listing 0x29A48..0x29A64).

**Effect on output.** At ramp 0 the lane torque is already 0 (`× ramp` at 0x2A1E6). The visible change is that
the published cells and `gp-0x674B` hold stale values instead of recomputed ones. BELIEF that nothing reads them
for control; `gp-0x6a32` has zero readers (EVIDENCE).

### 3.6 What CANNOT be done without a cave (EVIDENCE: these are the only inputs the bytes read)

| wanted | why not in place |
|---|---|
| **Speed-scheduled Kp** | The Kp key is idx (`0x29DE8 zxh r7`). The lane has no speed-indexed gain. The only speed-indexed cal is LIM (`0xCB844`), and it clamps the command, not a gain. The fork could pre-distort θ_sp, but only at 100 Hz and about 60 ms latency. |
| **I bleed on driver torque** | I's only input is E, its clamp is a scalar, and it resets only on skip. The fade multiplies the sum after `I>>7` and never touches the accumulator. |
| **Angle validity** | The only gate on x is ±12000 (±1200 deg). `gp-0x6a00` is forced to 0 outside `gp-0x67fe ∈ {1,2}` (kit memory, `FUN_0003e6d8`). The lane leaves engagement through `gp-0x67fe != 2` → STEER_STATUS 3 → a 2.048 s fade, during which θ may read 0 while P pushes toward θ_sp. Mode-3 calibration of the zero is tracer-angle's surface. |
| **Clamp the 0x7FFF sentinel** | `ld.h -0x69ae` loads it as 32767. The cal-only mitigation is `0xC63F6` 16 → 328, which shortens the fault fade to 0.1 s; it also shortens a normal disengage. |
| **Release fully to the driver with I on** | The cal can drop fade-B's floor (`0xE564C` Y[4..5] 77 → 0) for a full release above 2048 raw. The wound I then returns when the driver lets go. That needs the bleed. |

---

## 4. Override and engage paths (EVIDENCE: decompile lines and listing)

**Post-PID fade.**
- `f = ((A·B) & 0xFFFF) >> 8`, then `S' = (f·S) >> 8`, applied to the **whole sum** `(I>>7) + P + D`
  (0x2A0B4..0x2A0C2).
- Under openpilot (`gp-0x6803 = 0`):
  - A = LERP(`0xCBC34` → `0xE56F4`, key `gp-0x6830` grab rate). X 0,3,6,8,10,20; Y 255…255,205.
  - B = LERP(`0xCBBC4` → `0xE564C`, key **`gp-0x682f` = min(|`gp-0x4f60`|>>5, 255)**). X 16,26,38,48,64,96;
    Y 255,243,218,179,77,77.
- At rest f = 254. The floor is f = 76 (0.297); with A at its 205 knee it is 61 (0.238).
- **The I accumulator is not bled by it.** I winds behind the fade.
- ⚠ **Kit memory correction (report, not applied).** `reference_accord_lkas_pid_register_map_and_taper.md` §3
  says B's axis is speed `gp-0x6a5e`. **It is `gp-0x682f`.** The decompile reassigns `uVar20 = gp-0x682f` before
  the B walk, and the walk compares `r1` = `ld.bu -0x682f` (0x29A7C) at 0x2A002/0x2A062.

**Engage.**
- State 1 → 3 when `gp-0x6805 == 1 && gp-0x6803 == 0 && gp-0x6807 < 3`. On the same tick, ramp += `0xC63F8` (33)
  and `gp-0x6806` := 1.
- The ramp then climbs 33/tick to 0x8000, about **0.99 s**.
- First engaged tick:
  - sp is the current command (no prefilter on V295).
  - The fb state is current, because the filter runs on every valid tick.
  - **I = 0 and E_prev = 0x7FFFFFFF**, but only if the preceding ticks were skips.
  - The output-lag state has decayed (fed S = 0 on skips; it is NOT reset).
  - The first-tick D sees dE = 0 (cmovnc).

**Disengage, I reset pinned.**
- I := 0 and E_prev := 0x7FFFFFFF on every **skip** tick (0x2A164 → 0x2A190/0x2A18C).
- A skip happens iff `(ramp == 0 && gp-0x6805 != 1)` or the inputs are invalid.
- **Request bit drops (openpilot disengage):**
  - State 2 → 4, `gp-0x6806` := 0, ramp −16/tick (`0xC63F6`).
  - I reset comes **2.048 s** after the drop from full ramp (ramp/16 ms in general).
  - The PID keeps running in the meantime, and the sign-hold gate is armed.
- **Override latch / fault (`gp-0x6807` = 4 or 7):**
  - State 5, ramp −328/tick (`0xC63F4`, 0.1 s).
  - If the request bit stays 1, **I is never reset**. The PID runs at ramp 0 and integrates.
  - On re-engage the wound I is applied under the 0.99 s ramp.
  - The record's "0.1–2.05 s" therefore overstates the reset in the override case.
- **Fork-side consequence (BELIEF, interface spec).** openpilot sends `STEER_TORQUE = 0` when inactive. On the
  angle loop that is "steer to centre" for the whole 2.048 s ramp-down. The fork should send θ_sp = current θ,
  in the EPS frame (`raw = −10·steeringAngleDeg`, with no openpilot angle offset), whenever lateral is inactive.

---

## 5. 🛑 The 0xE4 fault sentinel on the car now (V293–V295)

**What happens, step by step.** EVIDENCE for each step from the decompile (`FUN_00052676`, `FUN_00028ea6`
lines 124-134/182/282/351-389/766) and the MIRROR:

1. `FUN_00052676(param != 0)`, an RX fault or timeout status (BELIEF on which statuses), writes
   `gp-0x69ae = 0x7FFF` and `gp-0x6805 = gp-0x6803 = 0xFF`.
2. The validity flag fails, so `gp-0x6807 = 3`. The SM goes 2 → 4 and the ramp falls 16/tick (2.048 s), while
   the PID keeps running.
3. `r22 = clamp(32767, ±16384) = 16384`. That gives idx 254 → 240, sp = **+1032**, and P = 15480 → 15360
   (the rail).
4. Honda's sign-hold gate passes it only if the lane's previous output had the same sign and |y| > 102.
   Otherwise T is 0 and stays 0.

**MIRROR result** (lane already pushing +, starting from rest): T = 38 / 2245 / 1860 / 1259 / 57 at
0 / 100 / 500 / 1000 / 2000 ms.

**Compared with stock.** Stock had the same path, but sp = 172 was the maximum RATE setpoint (about 21 deg/s),
not maximum torque.

**Not traced:** whether the delivery downstream of `gp-0x6b38` (aggregator, EME, `gp-0x67a4`) also cuts on the
same fault.

**What triggers it (BELIEF).** A comma or panda crash while engaged stops 0xE4. The camera's 0xE4 is blocked by
the panda, so a timeout follows.

---

## 6. Censuses (two methods each, set difference empty)

Methods: a Python LE scanner over `[0x13000, 0xC0000) ∪ [0xC4000, 0xC5000)`, covering:
- the 4-byte gp forms (op 0x38–0x3F, `ld.hu`/`ld.w` hw2|1, `ld.bu` odd/even);
- the **store-r0** forms;
- the **6-byte extended** form.

The 6-byte form was positive-controlled by finding all 7 known `-0x4f60` sites. The store-r0 form was controlled
by finding the 8 `st.b r0,-0x6806` sites. These were set against Ghidra `search_instructions`.

| cell | touches | verdict |
|---|---|---|
| `gp-0x3d30` fb state | 0x28F7C ld.w, 0x28FA8 st.w | PRIVATE (Ghidra 2 = Python 2) |
| `gp-0x6a34` | W 0x290CA; R 0x2A0CA (`gp-0x680a` lane, unreachable), 0x2AFAE (`FUN_0002a93a`, uncalled twin) | no live reader (Ghidra 3 = Python 3) |
| `gp-0x6a32` sp | W 0x29D72, 0x2AC68 (twin) | zero readers |
| `gp-0x6dd0` I, `gp-0x6cf8` E_prev | 0x29DA4/0x2A190, 0x29E5E/0x2A18C (+ twin 0x2AC96/0x2B05C/0x2AD4A/0x2B058) | private |
| `gp-0x6a00` | sole writer 0x3E758; about 25 readers | the edit only adds a reader |
| tp cals a/b/C/DB/Ki/ICL/PCL/DCL/SCL/`0xC63F4`/`0xC63F6` | readers only in `FUN_00028ea6` and the twin 0x2A30E..0x2B421 | private (4-byte tp form only here; the 6-byte tp form is covered by the 2026-09-23 redo audit for a/b/C) |

The cave at `0xC4B34` reads `gp-0x6ada`, `gp-0x6b38`, `gp-0x6b94`, `gp-0x6b4c` and `gp-0x3680`. **None of the
PID internals are on the wire.** θ is on 0x14A and θ_sp is in the fork, but **I (`gp-0x6dd0`) has no instrument**.
A Ki dose needs a probe first (CLAUDE.md rule 3).

---

## 7. Golden-model cross-check (`lkas_rate_pid_tick` + `lkas_fb_lag`, `eps_chain_control.py`)

**Agreement.** Tick-for-tick on fb, E, P, S and T over 20 000 engaged V295 ticks (MIRROR `_crosscheck_golden`).

**Disagreements** (reports, not fixed):
1. **`engaged=False` is not what the skip does.** On a skip tick the bytes feed **S = 0** into the output lag,
   **zero I**, set **E_prev = 0x7FFFFFFF**, and zero the published cells. The model only zeroes T and keeps
   integrating and lagging the computed S.
2. **The sign-hold gate is missing.** 0x2A198..0x2A1E4 (`0xC64A3` = 1, dead zone `0xC61B8` = 102, test against
   `gp-0x6b30`, armed when `gp-0x6806 == 0`) is not in the model. Every disengage and fault transient differs.
3. **The fade is a scalar input** (`taper`, default 254), not `((A(gp-0x6830)·B(gp-0x682f)) & 0xFFFF) >> 8`.
   The model cannot represent the driver-torque fade or its 0.297 floor. This is correct hands-off.

---

## 8. Open, and the exact next step

- **Validity of `gp-0x6a00` while engaged.** Includes the mode-3 zero and the forced 0 outside `gp-0x67fe ∈ {1,2}`.
  This is tracer-angle's surface, and it decides whether the in-place set needs a validity cave.
- **The downstream fate of the sentinel pulse.** Trace `gp-0x6b38` → 0x2A2EA forward → the aggregator, with the
  `gp-0x67a4` and EME gates, on an 0xE4 timeout.
- **GATE 2 for P on angle plus D on raw rate**, on the identified plant family, before any dose.
- **The physical lock angle versus the ±409.6 deg range.** C = 65535 and the handler's ±4096 counts are both set
  by it.
