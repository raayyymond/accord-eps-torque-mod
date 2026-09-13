# TRACE 2026-09-13 — what the LKAS rate PID tracks, byte-exact, and the four ways to change it

**Agent:** `looptrace` (firmware-codepath-tracer), subagent of `main`. **Study/analysis only** — nothing
built, nothing flashed, nothing sent on any bus, no build script edited, no commit.

**Tooling.** GhidraMCP only for disassembly/decompilation (`decompile_function` first, then
`disassemble_bytes dry_run:true` to pin bytes, plus `search_instructions` and `get_function_callers`).
Raw-Python little-endian byte scans in the `bin_decompile` env for every load-bearing count or null,
each positively controlled before its null was trusted. **No mutating Ghidra call was made; nothing was
saved to the shared project.**

**Program.** `code.bin` (stock dump), the **sole** open program, 2090 functions (post-`ghidrafill`),
confirmed via `list_open_programs`. **Constants:** `gp = 0xFEDF8000`, `tp = 0xBF000`.
**Anchor check performed before any tp arithmetic:** `ld.h 0x73e8,tp` at `0x28F8A` must read the
halfword at file offset `0xC63E8`; that halfword is `9b 03` = 923 on stock, the value the record ascribes
to the feedback pole `a`. `0xBF000 + 0x73E8 = 0xC63E8` ✔ — **no off-by-0x1000.**

**Images.** `_v292_…_plain_image.bin` sha256 `d1128232…`, `_v282_…` sha256 `0ea98d06…`,
`_v279_V279-V268BASE-PURE.FEEDFORWARD.FB0.KD0.LINEAR.TORQUE.TAP_plain_image.bin`, all under
`C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/`.

Every decision-bearing claim is marked **[E]** EVIDENCE (address + method) or **[B]** BELIEF.

---

## 0. HEADLINE — five results, in order of consequence to the session's decision

1. **[E] The structural change the session is considering has already been built once, as V279, and it
   was never flown.** `docs/BUILD-LINEAGE.md` §V279 — *"PURE FEEDFORWARD: the rate PID opened into a
   linear torque map (2026-09-02, NOT FLOWN — THE FLIGHT CANDIDATE)"*. Read from **its own image**:
   `0xC62E6 = 0`, Kd bank = 0, map Y = 2X, Kp = 256 flat. Its image and `.rwd` are on disk and are
   **not** marked DO-NOT-FLASH. §5.
2. **[E] The exact, cal-only, one-halfword mute is `0xC62E6 := 0`** — the feedback lag filter's own
   **output clamp**. Clamping to ±0 forces `r26 ≡ 0` on **every** path, for every state value, with no
   dependence on the pole, the boot value, or the `s = −1` absorbing state. I re-derived the clamp
   branch by hand for `C = 0` and all three arms return 0. This is the cell the V282/V292 build tag
   calls **`FEEDBACK46080`** (46080 today, 7680 stock). §4a.
3. **[E] Torque mode does not change the delivered steady-state surface at all.** With the wheel still,
   `fb = 0` already, so `T(idx)` is byte-for-byte what V282/V292 deliver today — 2462 counts at the
   rail, the P clamp binding from `idx ≈ 115`. **What changes is the response to wheel motion**, and it
   changes *upward*: today the loop backs the torque off as the wheel follows; in torque mode it does
   not. That is the authority claim **and** the risk, in one sentence. §4a.
4. **[E] The `0x2A0C6` route is NOT a reset — it is a second, feedback-only rate-damper MODE**, gated by
   `gp-0x680a == 1`, reading `|fb>>5|` through a LERP at `0xC6710–0xC6730` and delivering
   `−sign(fb)·LERP`. It **cannot run**: `gp-0x680a` has **zero writers image-wide by two independent
   methods** and its `.data` source byte at flash `0x868A6` is `00`. The record calls this "SKIP 3". §3.6.
5. **[E] On a V292 base, option (c)'s quantiser penalty is exactly zero.** V291's 1.07-count quantum,
   its dead zone and its −32-count DC bias are all properties of the two `sar 0xa` floors that V292's
   cave already removes. A 2 Hz pole on a **V282/V291** base would cost a 5.10-count quantum and a
   **−157.5-count** DC bias; on a **V292** base it costs neither. §4c.

---

## 1. THE FEEDBACK OPERAND — sensor to error, byte-exact

### 1.1 The chain, with the producer newly pinned

```
gp-0x6abe  raw sensor (signed halfword)
   |  FUN_0003f776  (body 0x3F776-0x3F883; sole caller FUN_00022ca0)
   |  x = pol * ((raw * 48 * [0xC613A]) >> 15), saturated to +-12000
   |  stored to gp-0x6a56  AND the lockstep mirror gp-0x4ca6
gp-0x6a56  the PID's rate operand, +-12000 saturated
   |  FUN_00028ea6 @ 0x28F4C   ld.h -0x6a56,gp,r7     <-- the ONLY read of this cell in the PID
   |  0x28F50-0x28F58  plausibility BAIL if |x| > 12000 (redundant; the producer already saturates)
   |  0x28F86-0x28FBE  the one-pole lag, two-sample sum, clamp +-[0xC62E6]
r26        the feedback operand
   |  0x29D78  sub r26,r16
E = 32*sp - fb
```

### 1.2 The producer, decompiled — **[E]**, `decompile_function(0x3f776)`

```c
iVar4 = (int)*(char *)(gp - 0x6752) *                       /* pol, the +-1 arm flag           */
        ((int)(*(short *)(gp - 0x6abe) * 0x30                /* raw * 48                        */
               * (uint)*(ushort *)(tp + 0x713a)) >> 0xf);    /* * [0xC613A], Q15                */
/* then: < -11999 -> -12000 ; < 12000 -> (short)iVar4 ; else 12000 */
*(short *)(gp - 0x6a56) = sVar3;   *(short *)(gp - 0x4ca6) = sVar3;   /* LOCKSTEP PAIR */
```

A separate arm above it zeroes **both** cells when the raw sensor fails plausibility — Ghidra renders
the test as `0x6590 < 0x1900 + [gp-0x6abe]`, the standard unsigned-window idiom for **`|raw| > 13000`**.
On disagreement between the pair it calls `FUN_0006b9fa(gp-0x4ca6)`.

| quantity | value | evidence |
|---|---|---|
| `[0xC613A]` (`tp+0x713a`) | **1159**, identical stock / V282 / V292 | Python LE read |
| raw → `x` scale | `48 × 1159 / 32768` = **1.697754** counts of `x` per raw count | the two constants above |
| `x` saturation | **±12000**, at the producer (`0x3F7B8 / 0x3F7D0 / 0x3F7E0`), plus a zero-write at `0x3F81E` | prior trace, re-confirmed |
| `x` scale, physical | **8 counts per deg/s** | *inherited*, see §7.1 — **[B]** this session |
| `x` sign | `pol = gp-0x6752`, a **±1** flag whose three writers are `0x490C0` (+1), `0x49838` (+1), `0x49844` (−1); it is never written 0 | prior trace |
| tick | **1 ms**, `Ts = 1e-3` | **[E]-by-consistency only**, §7.2 |

⇒ **±12000 counts = ±1500 deg/s.** The plausibility bound is ~27× the largest rate the car has ever been
measured at (42–56 deg/s peak on V278r3). It is a sensor-fault bound, not an operating limit.

### 1.3 The filter, and the clamp the build tag names

`disassemble_bytes(0x28F86, 56, dry_run:true)`, re-read this session; byte-identical stock / V282, and
on V292 the two `mul`/`sar` pairs execute inside the cave instead (§4 and the V292 design).

```
28F86  ld.hu 0x73ea,tp,r16      b = [0xC63EA]     UNSIGNED, cap 65535
28F8A  ld.h  0x73e8,tp,r9       a = [0xC63E8]     ** SIGNED **, cap 32767
28F8E  mul   r16,r7,r0          r7 = low32(x*b)            <-- V292 replaces this with jr 0xC4C00
28F92  mul   r26,r9,r0          r9 = low32(s*a)
28F96  ld.hu 0x72e6,tp,r13      C = [0xC62E6]
28F9A  sar   0xa,r7             step_b = floor(x*b / 1024)   SEPARATE floor
28F9C  ld.hu 0x72e6,tp,r14      C again
28FA0  sar   0xa,r9             step_a = floor(s*a / 1024)   SEPARATE floor
28FA2  add   r7,r9              s_new
28FA4  add   r9,r26             out = s_old + s_new          the TWO-SAMPLE SUM
28FA6  cmp   r13,r26
28FA8  st.w  r9,-0x3d30,gp      s := s_new   (32-bit state cell)
28FAC  ble   28FB2
28FAE  mov   r14,r26            out := +C
28FB0  br    28FBE
28FB2  subr  r0,r14
28FB4  cmp   r14,r26
28FB6  bge   28FBE
28FB8  ld.hu 0x72e6,tp,r26
28FBC  subr  r0,r26             out := -C
28FBE  mov   r26,r16            the clamped feedback
```

🛑 **`0xC62E6` IS the "FEEDBACK46080" of the V282/V292 build tag.** Python byte read: stock **7680**,
V282 **46080**, V292 **46080**. It binds on the **two-sample sum**, i.e. on the feedback operand itself,
**before** the error is formed. It is **not** a clamp on the rate sensor and not a clamp on the output.

**Reader census of `0xC62E6`, both methods:**

| image | accesses | where |
|---|---|---|
| stock / V282 / V279 | **3** | `0x28F96`, `0x28F9C`, `0x28FB8` — all inside the filter |
| **V292** | **5** | `0x28F96`, `0x28F9C` (now **orphaned**, the cave jumps over them), `0x28FB8`, plus the cave's own `0xC4C28`, `0xC4C2C` |

**[E]** — raw Python two-encoding scan over `[0x13000, 0x100000)`, **8/8 positive controls PASS**
(`ld.h -0x6a56` @`0x28F4C`, `ld.w -0x3d30` @`0x28F7C`, `st.w -0x3d30` @`0x28FA8`, `ld.bu -0x3d2c`
@`0x28F66` — an **odd** displacement, exercising the `ld.bu` bit-5 parity trap —, `ld.h 0x73e8,tp`
@`0x28F8A`, `ld.hu 0x73ea,tp` @`0x28F86`, the **6-byte** `gp-0x6752` @`0x48E56`, `st.h -0x6a34`
@`0x290CA`). The scanner sees 23,373–23,394 gp/tp accesses image-wide, so its zeros are verified zeros.

🛑 **A build script that asserts "exactly three readers of `0xC62E6`" will FAIL on a V292 base.** The
count is five, two of them dead.

### 1.4 The recurrence, and the V292 cave

```python
# stock / V282 / V291 :  0x28F86..0x28FA8
s_new = ((a*s) >> 10) + ((b*x) >> 10)      # TWO separate arithmetic floors, toward -inf
out   = s + s_new                          # 0x28FA4, the two-sample sum
s     = s_new                              # 0x28FA8  st.w, 32-bit
fb    = max(-C, min(C, out))               # 0x28FA6..0x28FBC,  C = [0xC62E6]

# V292 :  the SAME, with each floor's residue carried (cave 0xC4C00, hook 0x28F8E)
t_b = b*x + rem_b ; step_b = t_b >> 10 ; rem_b = t_b & 0x3FF     # rem_b = gp-0x6D74
t_a = a*s + rem_a ; step_a = t_a >> 10 ; rem_a = t_a & 0x3FF     # rem_a = gp-0x6D72
s_new = step_a + step_b ; out = s + s_new ; s = s_new ; fb = clamp(out, C)
```

`DC = 2b/(1024 − a)`. V282 `(923, 1560)` → **30.8911**. V292 `(962, 958)` → **30.9032** (+0.04 %).

⭐ **The number this DC gain actually sets, and why DC-holding matters:** at steady state the loop
settles where `E = 0`, i.e. `32·sp = DC·x`, i.e.

```
commanded wheel rate = 32·sp / (DC × 8 counts-per-deg/s) = 0.12943 deg/s per count of sp   (V292)
                                                          0.12951 deg/s per count of sp   (V282)
```

**[E]** for the arithmetic, **[B]** for the 8 counts/deg·s⁻¹ (§7.1). At the V282 map's ceiling
`sp = 1032` that is **133.6 deg/s**; at the measured p90 demand `idx = 58`, `sp = 249` → **32.2 deg/s**,
which is the record's own measured 42/56 deg/s band at higher demand. **A pole change that holds DC
leaves this reference scale untouched — that is the whole content of "DC-held".**

### 1.5 The V292 image, verified against its own design — **[E]**

Full-range Python diff, `[0x13000, 0x100000)` (never a whole-file diff — the `0xFF` filler trap):
**V292 differs from V282 in exactly 69 bytes, in 10 clusters**, and the 52-byte cave at `0xC4C00`
matches the design listing **byte for byte**:

| offset | V282 → V292 | meaning |
|---|---|---|
| `0x28F8E` | `f0 3f 20 02` → `89 07 72 bc` | the `mul` replaced by `jr 0xC4C00` |
| `0xC4BAA` | `81 c9` → `d1 c2` | the `0x14A` bit-3 rung repointed to `ld.w -0x3d30` (the fb state) |
| `0xC4C00–0xC4C33` | `FF`×52 → the cave | 15 instructions |
| `0xC4FFC`, `0xC6FFC` | — | the two block CRCs |
| `0xC63E8` | 923 → **962** · `0xC63EA` 1560 → **958** | the fb pole |
| `0xC6446` | 5244 → **4725** | the r24 engaged arm |

---

## 2. THE SETPOINT SIDE

### 2.1 The path

```
CAN 0x0E4 STEER_TORQUE (100 Hz)
   |  handler writes gp-0x69ae at 0x5268C / 0x526F2 / 0x52726 / 0x527C6   (4 writers)  [E]
gp-0x69ae = clamp(-4 * signed wire STEER_TORQUE, +-0x4000)                 [B] this session, §7.3
   |  0x29032  ld.h -0x69ae      <-- the COMMAND path
   |  0x29124  ld.h -0x69ae      <-- a GATE only  (|cmd| <= 0x4000 test)
   |  clamp to +-LERP_speed(0xCB844 -> rec 0xE51A8)        V282: 16384 flat (stock 15360)
   |  * (G_speed * activity & 0xFFFF)  >> 16     then  >> 6                   total >> 22
   |  clamp to +[0xC64F0] / -[0xC64F1]  =  +-240 ; then rectify, keep the sign
idx  (0..240)      published to gp-0x697a @0x29DDA, and its low byte to gp-0x674b (the 427 tap)
   |  assist map, pointer family 0xC9A88, selector 7 -> record 0xE502C
sp = sign(cmd) * LERP_map(idx)      published to gp-0x6a32 @0x29D72
   |  0x29D78  sub r26,r16
E = 32*sp - fb
```

**The demand index scale is 16.125736 wire 0x0E4 counts per idx LSB, EXACTLY** — inherited **[E]** from
`reference_accord_kp_kd_schedule_axis_is_the_demand_index`, not re-derived here.

⭐ **New this session, and it simplifies that formula: the "driver-activity" factor folded into `G` is
FLAT.** The LERP at `tp+0x7976..0x7984` = `0xC6976..0xC6984`, axis `gp-0x6830` = `|bar-derivative|>>6`,
has **Y = [255, 255, 255, 255] and Ymax = 255 on stock, V282 and V292** — a constant ×255. **[E]**,
Python byte read. So the recorded `idx = |clamp((G·cmd)>>22, ±240)|` is exact as written.

### 2.2 The assist map, selector 7 — read from the images **[E]**

X knots (identical on every build): `[0, 12, 20, 24, 32, 64, 96, 128, 160, 240]`

| build | Y knots | ceiling | shape |
|---|---|---|---|
| stock | `[0, 24, 42, 50, 62, 100, 126, 154, 166, 172]` | 172 | concave |
| **V279** | `[0, 24, 40, 48, 64, 128, 192, 256, 320, 480]` | 480 | **linear, Y = 2X** |
| **V282 / V292** | `[0, 52, 86, 103, 138, 275, 413, 550, 688, 1032]` | **1032** | **linear, Y/X = 4.30 at every knot** |

**V282's map is 6.00× stock at the ceiling and linear to within a count everywhere** — the
`MAP.LINEAR.TO6X` of the build tag, re-confirmed.

### 2.3 Command update rate vs loop tick

The 0x0E4 command is written at **100 Hz** by the CAN handler; the PID runs at **1 kHz**. **`sp` is
therefore a 10-tick staircase**, and every command change lands on exactly one tick in ten. This is
structural and unchanged by any option below. Its consequence for the D term is §3.4.

### 2.4 The override taper — four tables, and the always-on ×254/256

```
factor = ((A * B) & 0xFFFF) >> 8            A in {0xCBB54, 0xCBC34},  B in {0xCBAE4, 0xCBBC4}
S      = (factor * S) >> 8                  selected by bVar1
```

| table | record (sel 7) | axis | X | Y |
|---|---|---|---|---|
| A `0xCBB54` | `0xE55A4` | `\|bar-derivative\|` | `[0,3,6,8,10,20]` | `[255,255,255,255,255,205]` |
| B `0xCBC34` | `0xE56F4` | same | `[0,3,6,8,10,20]` | `[255,255,255,255,255,205]` — **identical to A** |
| C `0xCBAE4` | `0xE54FC` | speed `gp-0x6a5e` | `[24,45,64,80,96,112]` | `[255,205,164,125,90,51]` |
| D `0xCBBC4` | `0xE564C` | speed | `[16,26,38,48,64,96]` | `[255,243,218,179,77,77]` |

**[E]** all four read from the images; identical stock / V282 / V292. Two consequences:

* **A ≡ B**, so the `bVar1` choice only ever selects between the two **speed** tapers C and D.
* At rest the factor is `((255·255)&0xFFFF)>>8 = 254`, so **the taper costs ×254/256 = 0.9922 even with
  no driver torque and no speed** — it is never exactly unity. This is why the delivered rail is **2462**
  and not the 2481 the record quotes from the untapered arithmetic.
* Both speed tapers are **large** derations at their upper knots (C → 51/255 = 0.20, D → 77/255 = 0.30).
  Which one is live is **not settled here** — §7.4.

---

## 3. P, I, D AND THE DELIVERY

### 3.1 The exact integer mirror

Each line carries the instruction that executes it. Verified decompile-first
(`decompile_function(0x28ea6)`), then pinned in assembly at the four points that matter.

```python
# ---------------- FUN_00028ea6, the LKAS rate PID.  Ts = 1 ms.  V282/V292 cal values inline.
def clamp(v, c): return c if v > c else (-c if v < -c else v)

E  = 32*sp - fb                                  # 0x29D78  sub r26,r16     ** THE ERROR **

# ---- I : a DEADBAND on E>>5, then Ki, 32-bit accumulator stored x8 --------------------------
e5   = E >> 5
DB   = 4                                          # [0xC62E4]  0x29D6E/84/8C/96   (4 live readers)
exc  = e5-DB if e5 > DB else (e5+DB if e5 < -DB else 0)
Ki   = 0                                          # [0xC63E6]  0x29D9C           ** ZERO **
ICL  = (10240 << 10) >> 3                         # [0xC61BA] = 10240  ->  1,310,720
I    = clamp((I_state >> 3) + ((exc*Ki) >> 3), ICL)   # 0x29DA4 ld.w gp-0x6dd0
I_state = I << 3                                  # 0x2A190 st.w gp-0x6dd0   (the cell holds 8*I)

# ---- P -------------------------------------------------------------------------------------
Kp   = 248                                        # LERP(0xCB994 -> 0xE5378) on idx; FLAT on V282
P    = clamp((E*Kp) >> 8, 15360)                  # 0x29E36 mul, 0x29E3E sar 0x8, clamp [0xC61BC]

# ---- D : on the FULL error, with an E_prev plausibility window -----------------------------
Kd   = 128                                        # LERP(0xCB7D4 -> 0xE511C) on idx; FLAT
dE   = 0 if not (-768000 <= E_prev <= 768000) else E - E_prev    # 0x29E7E cmovnc
D    = clamp((dE*Kd) >> 3, 10240)                 # 0x29EE4 mul, 0x29EEC sar 0x3, clamp [0xC61B6]
E_prev = E                                        # 0x2A18C st.w gp-0x6cf8   (32-bit)

# ---- the sum ------------------------------------------------------------------------------
S    = (I >> 7) + P + D                           # 0x29F18 sar 0x7,r2 ; 0x29F1E add r9,r2 ; 0x29F24 add r8,r2
                                                  #   r2 = I   r9 = P   r8 = D      <-- see §6.1
S    = ((((tapA*tapB) & 0xFFFF) >> 8) * S) >> 8   # the override taper, 254/256 at rest
S    = clamp(S, 15360)                            # 0x2A13E..0x2A160, [0xC61BE]

# ---- the output lag :  a one-pole IIR with the >>5 the feedback filter does NOT have -------
la, lb = 992, 507                                 # [0xC63EC] @0x2A184 , [0xC63EE] @0x2A174
ln   = ((la*lag_state) >> 10) + ((S*lb) >> 10)
y    = (lag_state + ln) >> 5                      # DC = 2*507/((1024-992)*32) = 0.99023
lag_state = ln                                    # gp-0x3d3c

# ---- the engagement ramp and the delivery --------------------------------------------------
# gate, ARMED ONLY WHEN NOT ENGAGED:  [0xC64A3]==1 and gp-0x6806==0
#    if |y| <= [0xC61B8]=102  or  y*gp-0x6b30 <= 0 :  yr = 0
yr   = sxh((y * ramp) >> 15)                      # 0x2A1E6 mul r14,r9 ; 0x2A1EA sar 0xf ; ramp = gp-0x69b0, max 0x8000
addend = 0                                        # r11 = (short)[gp-0x6b2c], IDENTICALLY ZERO (inherited)
T    = clamp(((addend + yr) * pol * gain) >> 15, 3072)
#      0x2A1EE ld.h 0x746c,tp  (V282 repoints the displacement to 0x7CD0 = 0xC6CD0 = 5346)
#      0x2A1F2 ld.b -0x6752,gp ; 0x2A1F6 mulh ; 0x2A1FC add r9,r11 ; 0x2A1FE mul ; 0x2A202 sar 0xf
#      0x2A1F8 ld.hu 0x71b4,tp -> [0xC61B4] = 3072 on V282 (512 stock)
# 0x2A23C  st.h r1,-0x6b38,gp         T, the lane torque
```

### 3.2 The cal cells, read from the images, with their reader census

| addr | what | stock | V279 | V282 | V292 | live readers | dead-twin readers |
|---|---|---|---|---|---|---|---|
| `0xC62E4` | **I deadband on `E>>5`** | 4 | 4 | 4 | 4 | 4 (`0x29D6E/84/8C/96`) | 3 |
| `0xC63E6` | **Ki** | **0** | 0 | **0** | **0** | 1 (`0x29D9C`) | 1 |
| `0xC61BA` | I clamp (`<<10 >>3`) | 10240 | 10240 | 10240 | 10240 | — | — |
| `0xC61BC` | **P clamp** | 15360 | 15360 | 15360 | 15360 | 4 (`0x29E3A/44/4A/58`) | 3 |
| `0xC61B6` | **D clamp** | 10240 | 10240 | 10240 | 10240 | 4 (`0x29EE8/EF2/EF8/F02`) | 3 |
| `0xC61BE` | **sum clamp** | 15360 | 15360 | 15360 | 15360 | 4 (`0x2A13E/146/14C/156`) | 4 |
| `0xC63EC/EE` | output-lag poles | 992/507 | 992/507 | 992/507 | 992/507 | 1 each | 1 each |
| `0xC61B8` | out-lag gate threshold | 102 | 102 | 102 | 102 | — | — |
| `0xC64A3` | out-lag gate arm | 1 | 1 | 1 | 1 | — | — |
| `0xC61B4` | **output clamp** | 512 | **3072** | **3072** | **3072** | 4 (`0x2A1F8/20C/212/21C`) | 4 |
| `0xC6CD0` | **forward gain** (V57/V81 repoint) | 65535 | **5346** | **5346** | **5346** | 1 (`0x2A1EE`, via the V282 displacement) | — |
| `0xC646C` | the stock forward-gain cell | 891 | 891 | 891 | 891 | 5 live | 1 |

**[E]** — same controlled Python scan as §1.3. Every one of the six PID clamp/gain cals is **private to
this PID**: its only other readers are inside `FUN_0002a93a` / `FUN_0002a892` / `FUN_0002b35a`, the
**uncalled twin island** `0x2A30E–0x2B421` that `ghidrafill` proved has zero callers.

### 3.3 The schedules, read from the images **[E]**

| | X knots | stock Y | V279 Y | V282 / V292 Y |
|---|---|---|---|---|
| **Kp** `0xCB994`→`0xE5378` | `[0, 68, 112, 136, 208]` | `[248, 512, 645, 696, 696]` | `[256]×5` | **`[248]×5` — FLAT** |
| **Kd** `0xCB7D4`→`0xE511C` | `[0, 11, 22, 32]` | `[128, 128, 128, 128]` | **`[0]×4`** | `[128]×4` — **FLAT, and flat on stock too** |

Both axes are the **demand index**. Kd's last X knot is 32, so above `idx = 32` the walk returns the last
Y — **Kd is unschedulable above idx 32**, re-confirmed. With every Y equal to 128, **Kd = 128
unconditionally on stock, V282 and V292**.

### 3.4 ⭐ What the D term actually is today — measured on the exact integer mirror

Ki = 0 makes this a PD loop. The D term is `clamp((E[n]−E[n−1])·128 >> 3, ±10240)` on the **full**
error, so it carries **both** `32·Δsp` (the 100 Hz command staircase) and `−Δfb` (the rate derivative).
Driving the mirror with the measured 123-count/frame command slew cap and a 20.3 Hz ring of amplitude
`A` counts, 1800 scored ticks after warm-up:

| ring `A` (counts) | mean \|D\|, fb live | mean \|D\|, fb muted | ticks with D railed at ±10240 |
|---|---|---|---|
| 0 | 72.8 | 72.8 | 0.7 % |
| 4 | 143.9 | 72.8 | 0.7 % |
| 16 | 353.2 | 72.8 | 0.7 % |
| 64 | 1193.1 | 72.8 | 0.7 % |

With the command **held** (so only the ring drives `dE`):

| ring `A` | mean \|D\| | max \|D\| | railed |
|---|---|---|---|
| 4 | 71.6 | 128 | 0 |
| 16 | 282.3 | 480 | 0 |
| 64 | 1128.1 | 1792 | 0 |

**Two things fall out, both [E] from the mirror:**

1. **The command staircase already rails the D clamp on 0.7 % of ticks** — one tick in ten carries the
   whole 10 ms command step, and at the slew cap that step is `32·Δsp ≈ 1046`, giving
   `D = 1046·128>>3 = 16736`, clipped to 10240. **This is true today; it is not created by any option
   below.** It is a ±10240 impulse train at 100 Hz into a sum clamp of 15360 — **67 % of the sum
   ceiling, from a feedforward term.**
2. **The ring's contribution dominates the mean at realistic amplitudes** (280 of 353 at `A = 16`), so
   D is not "mostly feedforward" in the mean. Both terms are large; they differ in shape (impulse vs
   sinusoid) and in sign convention.

### 3.5 The delivery tail — where the lane torque goes

```
0x2A23C  st.h r1,-0x6b38,gp     T = clamp((y_ramped * pol * gain) >> 15, +-[0xC61B4])
0x2A2C2  cmove 0x0,r1,r16       gated copy
0x2A2EA  st.h r16,-0x6b3c,gp    the LIVE forward   (0x2B41C is the DEAD twin)
FUN_0002b422 @0x2b42e           clamp to +-[0xC61B2] (3072 on V282) -> ep request array
FUN_00025c32 / FUN_00026c80     -> 0x276F0  st.h -> gp-0x6b4c   (clamp +-0x2800)
FUN_0003aa2c @0x3aa3e           DIRECT summand, UNIT weight -> gp-0x6b94
  -> FUN_0004503c governor -> gp-0x6ace -> FUN_000456a4 -> gp-0x6acc
  -> FUN_00042af8 shaper  -> gp-0x6b08 -> gp-0x6b98   (the FOC motor command)
```

Inherited **[E]** from `TRACE-2026-09-13-lkas-lane-to-aggregator-and-ghidra-gap.md`; I re-ran the
`gp-0x6b4c` census and reproduce its 8 accesses on stock, 9 on V292 (the extra is the `0x14A` cave's
read at `0xC4B92`). `gp-0x6b38` gains two readers on V292: `0x55DF0` (the CAN-427 torque tap) and
`0xC4B40` (the `0x14A` cave). Both are telemetry.

### 3.6 🛑 `0x2A0C6` is a MODE, not a reset — and it is unreachable

The record calls `0x29A70 jr 0x2A0C6` "SKIP 3" and describes the target as a reset route. **It is a
second delivery lane.** `disassemble_bytes(0x2A0C6, 64, dry_run:true)`:

```
2A0C6  mov   0x0,r24
2A0C8  cmp   r0,r26                 sign of the feedback
2A0CA  ld.hu -0x6a34,gp,r8          |fb>>5|, published at 0x290CA
2A0CE  mov   0x1,r12
2A0D0  ld.hu 0x7712,tp,r9           X_min = [0xC6712] = 64
2A0D4  cmovlt -0x1,r12,r12          r12 = sign(fb)
2A0D8  movea 0x7710,tp,r7           the table base = 0xC6710
2A0EA  mov   0x7fffffff,r16         E_prev := the poison sentinel
2A0F4  ld.hu 0x7722,tp,r10          Y[0] = 608          (below-range)
...    LERP over X [65,67,73,80,88,96,104] -> Y [608,704,704,832,832,832,832,832]
       output = -sign(fb) * LERP(|fb>>5|)
```

That is a **pure viscous damper on the wheel rate, with no command term at all**. It bypasses P, I and D
entirely and joins the chain at the `0xC61BE` sum clamp.

**It cannot run. [E], three ways:**

| method | result |
|---|---|
| Ghidra `search_instructions(operand_pattern="-0x680a")` | **2 matches, both `ld.bu`** (`0x29A68` live, `0x2A96A` dead twin). Zero writers. |
| raw Python two-encoding scan, 8/8 controls PASS | **2 accesses, both `ld.bu`.** Zero writers, any encoding. |
| `.data` boot value | the boot copy loop `0x1476C–0x14794` walks flash `0x86260 → 0x8AB18` into RAM `0xFEDF11B0 →`. `gp-0x680a` = `0xFEDF17F6`, source flash `0x868A6` = **`00`**. |

⇒ `gp-0x680a ≡ 0` for the life of the ECU, so the `== 1` branch never executes and `gp-0x6a34`'s only
live consumer is dead in practice. **Residual [B]:** a register-indirect `st.b` through a pointer would
not appear in an operand scan. Combined with "boots to 0" and "two accesses image-wide, both loads",
I consider the claim strong but not airtight.

⭐ **The same boot-loop read closes an open item the V292 design and the fb-filter trace both left as
BELIEF:** `gp-0x3d30` (`0xFEDF42D0`, source flash `0x89380`) = `00 00 00 00` and `gp-0x3d2c`
(`0xFEDF42D4`, source `0x89384`) = `00`. **Both boot to zero, from the `.data` image, inside the copy
loop's range.** The sentinel therefore boots ≠ 1 and `s := 0` on the first tick. **[E], not [B].**
`gp-0x6D74/72/70` likewise read `00 00` at flash `0x8633C/3E/40`.

---

## 4. THE CANDIDATE STRUCTURAL CHANGES, SIZED FROM THE BYTES

### 4a. TORQUE MODE — `fb ≡ 0`, cal-only, exact

#### The cell, and why the clamp beats the input gain

Two cal routes exist. **The clamp is strictly better.**

| route | edit | exactness |
|---|---|---|
| **`0xC62E6 := 0`** (the output clamp) | 1 halfword | **EXACT on every path and for every state value** — I traced the clamp branch by hand for `C = 0`: `r26 > 0` → `mov r14,r26` = 0; `r26 < 0` → `ld.hu`+`subr` = −0 = 0; `r26 == 0` → unchanged = 0. It is read `ld.hu`, so 0 reads as 0 with no sign trap. |
| `0xC63EA := 0` (the input gain `b`) | 1 halfword | exact **only if `s` never reaches a negative absorbing state**. On stock/V282/V291 `floor(−a/1024) = −1` for every `a < 1024`, so `s = −1` is absorbing and `fb` would rest at **−2, forever**, not 0. On a **V292** base the cave removes that absorbing state and `b = 0` is exact — but it depends on the cave being present. |

⇒ **Use `0xC62E6 = 0`.** It is what V279 used. It is in the `0xC6000` CRC page (trailer `0xC6FFC`).

#### What the lane then computes

```python
E = 32*sp          # fb == 0 identically
I = 0              # Ki = 0, unchanged
P = clamp((32*sp*248) >> 8, 15360)
D = clamp((32*(sp[n]-sp[n-1])*128) >> 3, 10240)     # a PURE COMMAND DERIVATIVE
S = clamp((254*(P+D)) >> 8, 15360)
y = output-lag(S)                                    # unchanged, DC 0.99023, corner 5.05 Hz
T = clamp((y*ramp>>15 * pol * 5346) >> 15, 3072)
```

**Is a cal-only mute exact, or is a code edit needed? [E] — a code edit is NOT needed.** One halfword
plus the page CRC.

#### The delivered surface, from the built V282/V292 cells

| idx | sp | E = 32·sp | P | S | **T** |
|---|---|---|---|---|---|
| 1 | 4 | 128 | 124 | 123 | **19** |
| 3 | 13 | 416 | 403 | 399 | **64** |
| 5 | 21 | 672 | 651 | 645 | **104** |
| 10 | 43 | 1376 | 1333 | 1322 | **213** |
| 20 | 86 | 2752 | 2666 | 2645 | **427** |
| 32 | 138 | 4416 | 4278 | 4244 | **685** |
| 58 | 249 | 7968 | 7719 | 7658 | **1237** |
| 96 | 413 | 13216 | 12803 | 12702 | **2051** |
| **115** | 494 | 15808 | 15314 | 15194 | **2454** |
| 160 | 688 | 22016 | **15360** ← P clamp binds | 15240 | **2462** |
| 240 | 1032 | 33024 | **15360** | 15240 | **2462** |

🛑 **This is identical to what V282/V292 deliver TODAY with the wheel still**, because with the wheel
still `fb = 0` already. **Torque mode changes nothing about the steady-state surface and therefore
nothing about peak authority.** The **P clamp `0xC61BC` binds from `idx ≈ 115`**, which is why the rail
is 2462 and why the top half of the map is inert — a pre-existing fact, unchanged by any option here.

🛑 **What DOES change, and it is an authority INCREASE:** today, once the wheel starts following, `fb`
grows and `E` shrinks; the lane settles at `wheel rate = 0.1294·sp deg/s` and the torque backs off to
whatever holds that rate. With `fb ≡ 0` the error never shrinks, so **T stays at its full command value
for as long as the command is held, regardless of how fast the wheel is already moving.** The lane
becomes a torque source with **no rate limit of its own**. That is exactly what "openpilot expects a
torque" means — and it is the thing to state on the risk line before any drive.

#### The command-derivative kick — already present, and what to do about it

§3.4 shows the ±10240 D rail on 0.7 % of ticks is **today's behaviour**, driven by the command
staircase, not something the mute creates. What the mute removes is the ring-derivative part of D.
**If the session wants D gone as well, two routes:**

| route | cost | CRC page |
|---|---|---|
| **`0xC61B6 := 0`** (the D clamp) | 1 halfword, **same page as `0xC62E6`** | `0xC6FFC` only |
| Kd bank `0xCB7D4` → record `0xE511C`, four Y knots → 0 (V279's route) | 8 bytes across 28 records | adds the `0xE5000` page CRC |

⇒ **`0xC61B6 = 0` is strictly cheaper and is exactly equivalent** (the clamp arms are `if D > C: D = C`
/ `elif D < −C: D = −C`, and at `C = 0` all three arms yield 0 — the same hand-trace as the fb clamp).
**[E]** `0xC61B6` has 4 live readers, all in this D block, and 3 in the dead twin.

#### What downstream sees

| consumer | sees the mute? | evidence |
|---|---|---|
| the fb state `gp-0x3d30` | **keeps running normally** — the mute is at the clamp, downstream of the state. On V292 the `0x14A` **bit-3 rung still publishes `sign(s)`**, a **free positive control** that the filter is alive while the lane no longer responds to it. | 3 accesses on V292: `0x28F7C`, `0x28FA8`, `0xC4BA8` |
| `gp-0x6a34` = `\|fb>>5\|` | goes to 0 | its only live consumer is the `gp-0x680a == 1` damper mode, which **cannot run** (§3.6) |
| plausibility monitor `FUN_0004595a` | **no**, not in kind | it compares `\|gp-0x6b94\|` against `\|gp-0x6ace\|` (demand vs governor output) and their product's sign, and calls `FUN_000462e6` on a fault. Muting the LKAS feedback changes the *value* of `gp-0x6b94`, never the demand↔governor relation. `decompile_function(0x4595a)` |
| the `gp-0x6a56` / `gp-0x4ca6` lockstep pair | **no** — nothing here writes either cell | §1.2 |
| the `gp-0x671d` r24 first-strike latch | **no** — it arms on r24-lane magnitudes, a different lane | `reference_accord_gp671d_arm_inverts_r24_on_v280plus…` |
| governor `FUN_0004503c`, shaper `FUN_00042af8`, EME | `T` is still clamped to ±3072 by `0xC61B4` and the aggregator still clamps ±0x2800. **No range change.** | §3.5 |
| **[B] the one real interlock question** | **an EME-class monitor that integrates sustained motor effort.** In torque mode the lane can hold `T` at its command value indefinitely while the wheel moves, where today it decays. Peak is unchanged; **dwell at peak is not.** I did **not** locate or read such a monitor this session — §7.5 names the exact next step. |

### 4b. ACCELERATION TRACKING

#### Where the substitution goes, and what it costs

**The cheapest placement is inside V292's existing cave**, differencing the filter input:

```
0xC4C00  ld.hu -0x6d70,gp,r13    ; r13 = x_prev          NEW  (+4 B)
0xC4C04  st.h  r7,-0x6d70,gp     ; x_prev := x           NEW  (+4 B)
0xC4C08  sub   r13,r7            ; r7 = x - x_prev       NEW  (+2 B)
0xC4C0A  mul   r16,r7,r0         ; t_b = (dx)*b          <- the existing cave continues unchanged
...      (the rest of the 52-byte V292 cave, verbatim)
```

**+10 bytes, +3 instructions.** Register footprint is **unchanged**: `r13` is already in the cave's set
`{r7, r9, r13, r14}` and is reloaded two instructions later by the cave's own
`ld.hu -0x6d74,gp,r13`. **[E]** for the register set, from the V292 design's own liveness argument plus
its errata (r7/r9 are live-in and are consumed by the replicated `mul`s — which is still true here,
since `r7` is read before it is rewritten).

**RAM:** one more halfword, `gp-0x6D70` = `0xFEDF1290`. **[E] free and boots to zero:** zero accesses of
any kind on stock, V282, V292 or V279 in the controlled scan; `.data` source flash `0x86340` = `00 00`.
It sits inside the same certified-free 72-byte run as the V292 cave's own two cells.

**Flash:** `0xC4C34–0xC4FF0` is 956 bytes of `0xFF` above the cave — ample. **CRC:** `0xC4FFC` only.

#### Is there an existing cell that already forms a rate difference in this lane? **No. [E]**

* The **r24 lane** forms `(bar[n] − bar[n−4])>>1` from the **torsion-bar torque**, in `FUN_0003aa2c` —
  a different lane, a different signal, and it reaches the motor through the aggregator, not through
  this PID.
* The **sibling filter** `gp-0x3d34`, computed alongside the fb filter at `0x28F78`/`0x29080`, IS a
  difference — `iVar23 = (iVar31 − s2) >> 4` — but of the **torsion bar** `gp-0x4f60`, not the rate.
  Its output drives `gp-0x6830` (the override-taper axis) and `gp-0x682f`.
* Inside `FUN_00028ea6` there is **exactly one** read of `gp-0x6a56`, at `0x28F4C` — confirmed by both
  Ghidra and the raw scan against the 30-access image-wide census.

⇒ **Nothing already differences the rate in this lane. A cave is required.**

#### What the closed loop becomes, from the arithmetic only

Substituting `x → x[n] − x[n−1]` multiplies the **entire feedback branch** by `(1 − z⁻¹)`, whose
magnitude at 1 kHz is `2·sin(π f Ts)`:

| f | ×factor | dB |
|---|---|---|
| 1 Hz | 0.00628 | −44.0 |
| 2 Hz | 0.01257 | −38.0 |
| 5 Hz | 0.03141 | −30.1 |
| **7.3 Hz** | **0.04586** | **−26.8** |
| 10 Hz | 0.06282 | −24.0 |
| 16 Hz | 0.10049 | −20.0 |
| **20.3 Hz** | **0.12746** | **−17.9** |
| 30 Hz | 0.18822 | −14.5 |

Three statements follow, and no physics beyond them:

1. **At DC the feedback is exactly zero.** `Δx = 0` for a constant rate ⇒ `fb = 0` ⇒ `E = 32·sp`. **So
   acceleration tracking IS torque mode at steady state, plus a transient term.** Option (b) contains
   option (a); it is not an alternative to it.
2. **The return ratio is cut at every frequency below ~160 Hz**, and cut *more* at low frequency than
   at 20 Hz — 8.9 dB more at 7.3 Hz, 26 dB more at 1 Hz. It is a **high-pass on the feedback**, the
   opposite shape to option (c).
3. **The `P` term then produces a torque proportional to −(filtered angular acceleration)**, which
   enters the wheel's equation of motion with the same sign as an inertia term. Stating only what the
   arithmetic gives: it is **electronic inertia**, and inertia adds no damping — it lowers the natural
   frequency of whatever mode it acts on. **That is the direction V289's revert signature moved
   (20 Hz → 15–17 Hz, louder).** I flag this as the principal reason to be cautious about (b), and I
   have **not** modelled the closed loop.

#### Scale, width and overflow

To restore today's feedback magnitude at a chosen frequency, `b` must rise by `1/(2 sin(π f Ts))`:

| match at | `b_new` | `ld.hu` cap 65535 | worst-case `a·s` (sustained max slew of `x`) | margin vs 2³¹ |
|---|---|---|---|---|
| 7.3 Hz | **20888** | OK | 1.26e8 | **17.1×** |
| 10 Hz | 15250 | OK | — | — |
| 16 Hz | 9533 | OK | — | — |
| **20.3 Hz** | **7516** | OK | 4.51e7 | **47.6×** |
| (unchanged) | 958 | OK | 5.75e6 | 373× |

The worst case is computed correctly, not conservatively: `x` is saturated to ±12000, so a *sustained*
difference `δ` can only persist while `x` traverses its 24000-count range. The filter settles in
`1/(1−a/1024) = 62` ticks, so the largest `δ` that can build a steady state is `24000/62 = 387` counts,
giving `s = b·387/62`. **No overflow at any `b` in the table.** `[0xC63EA]` is read `ld.hu` so `b` may
go to 65535; `[0xC63E8]` is read **`ld.h`, signed**, so `a` must stay ≤ 32767 and, for stability, ≤ 1023.

**One transient to state:** after a filter bail the stored `x_prev` is stale, so the next tick's `Δx`
can be as large as 24000. With `b = 7516` that injects `s = 176,156` in one tick — `a·s = 1.69e8`,
margin 12.7×, and the output is clamped to ±46080 anyway. Bounded, but it is a one-tick spike worth a
line in any docstring.

### 4c. LOW-FREQUENCY-ONLY FEEDBACK — the same two cells, different integers

**Yes, it is exactly V291's cells** — `0xC63E8` (`a`, `ld.h` **signed**) and `0xC63EA` (`b`, `ld.hu`) —
with no code change. DC held at `2·1560/(1024−923) = 30.8911`:

| target | `a` | `b` | actual DC | err | actual `f_c` | quantum `1024/b` (counts) | dead zone (deg/s) | **DC bias (counts)** |
|---|---|---|---|---|---|---|---|---|
| 1 Hz | **1017** | **108** | 30.8571 | −0.11 % | 1.09 Hz | **9.481** | 1.185 | **−292.6** |
| 2 Hz | **1011** | **201** | 30.9231 | +0.10 % | 2.03 Hz | **5.095** | 0.637 | **−157.5** |
| 3 Hz | **1006** | **278** | 30.8889 | −0.01 % | 2.82 Hz | 3.683 | 0.460 | −113.8 |
| 5 Hz | **993** | **479** | 30.9032 | +0.04 % | 4.89 Hz | 2.138 | 0.267 | −66.1 |
| 8 Hz | 975 | 757 | 30.8980 | +0.02 % | 7.80 Hz | 1.353 | 0.169 | −41.8 |
| V291/V292 | 962 | 958 | 30.9032 | +0.04 % | 10.11 Hz | 1.052 | 0.132 | −32.5 |
| V282 | 923 | 1560 | 30.8911 | 0 | 16.53 Hz | 0.656 | 0.082 | −20.3 |

`quantum = 1024/b` raw counts · `dead zone = quantum / 8` deg/s · `DC bias = −0.5·1024/(1024−a) × 2
terms × 2 (the two-sample sum)`.

🛑 **The answer to "at 2 Hz it is worse — by how much":**

* **On a V282 or V291 base:** the quantum goes 1.052 → **5.095** counts (**×4.84**), the dead zone
  0.132 → **0.637** deg/s, and the DC bias −32.5 → **−157.5** counts. That last one is the one that
  matters: against `E = 32·sp − fb`, a −157-count bias in `fb` is **+157 counts of phantom error, i.e.
  nearly five whole setpoint counts of permanent false demand**. At `sp = 3` (E = 96 nominal) that is
  **+164 % of demand**. A 1 Hz pole costs **−292.6**.
* **On a V292 base: ALL THREE ARE EXACTLY ZERO.** The cave carries each `sar 0xa` residue, so
  `mean(step) = b·x/1024` exactly at every amplitude, the dead zone does not exist, and the quantisation
  error is a first difference of a bounded sequence with exactly zero DC. **[E]** — this is the V292
  design's own §1.3 telescoping identity, re-derived, and its §2(i) exhaustive check over
  `x = −1491…1491`.

⇒ **V292 is the base that makes option (c) cheap.** Every pole below ~10 Hz was previously priced
against a quantiser penalty that scales as `1/(1024−a)`; on V292 that price is gone and the only
remaining constraint is loop stability.

⚠ **Two things option (c) does NOT fix, and they should not be conflated with it:**
`0xC62E6`'s ±46080 clamp still binds on the output (`|x| ≥ C(1024−a)/(2b) = 1491` counts = 186 deg/s —
never reached in practice), and the **P clamp still binds from idx ≈ 115**.

### 4d. Summary of the four routes, by cost

| option | edit | bytes | CRC pages | new liveness claims | new RAM |
|---|---|---|---|---|---|
| **(a) torque mode** | `0xC62E6 := 0` (+ optionally `0xC61B6 := 0`) | **2 (or 4)** | `0xC6FFC` | **none** | none |
| **(b) acceleration** | (a)'s structure + 3 instructions inserted at the head of the V292 cave + `b` rescaled | **+10 in the cave, 2 for `b`** | `0xC4FFC` + `0xC6FFC` | **none beyond V292's own** | 1 halfword, `gp-0x6D70` |
| **(c) low-f feedback** | `0xC63E8`/`0xC63EA` | **4** | `0xC6FFC` | none | none |
| **(d) leave the loop** | no firmware change | 0 | — | — | — |

---

## 5. LINEAGE — has any flown build ever zeroed or scaled the LKAS rate feedback?

**[E]**, from `grep` over `analysis-2020accord/builds/**/build_v*_tva.py` and `docs/BUILD-LINEAGE.md`,
with every value re-read from the **images**, not from the scripts.

| build | what it did to the feedback | flown? | on-car result |
|---|---|---|---|
| stock → V274/V275/V276 | `0xC62E6` **7680 → 46080 (×6)** — *raised* the clamp so the loop could still measure a ×6 rate | V276 **yes** | rang at damping fraction 0.57 |
| V278 / V278r3 | `0xC62E6` 7680 → 15360 (×2), ratio 1.395 preserved | **yes** | 3.9 Hz gone; high-angle stutter = P desaturating |
| **V279** | **`0xC62E6` → 0. The feedback operand is forced to 0 every tick; `E = 32·sp`.** Plus Kd bank → 0, map Y = 2X (ceiling 480), Kp → 256 flat. | **NO — never flown** | none. Built, 710/710 assertions, independent rebuild reproduced, adversarial pass returned **no do-not-flash**. Image and `.rwd` on disk, **not** marked DO-NOT-FLASH. |
| V280 → V292 | `0xC62E6` restored to **46080** and held there on every build since | yes | — |
| V289 | `0xC63E8/EA` 923/1560 → **875/2301**, DC held, corner 16.5 → **25.0 Hz** | **yes** (r62/r63) | no fault; the 20 Hz mode was removed and a pre-existing 15–17 Hz pole took its margin |
| V291 | `0xC63E8/EA` → **962/958**, DC held, corner → **9.94 Hz** | **no** — superseded by V292 | — |
| V292 | same cells as V291, plus the residue-carrying cave | **on the car now** | operator: grinding still present, high-angle stutter **worse** |

**Answers to the brief's question, plainly:**

* **The fb clamp `0xC62E6` has been flown at 7680, 15360 and 46080 — a three-point ladder, all
  non-zero.** It has been built at **0** exactly once, as V279, and **that build has never been driven.**
* **The pole pair `0xC63E8/EA` has been flown at exactly two settings** — stock `(923,1560)` on every
  build up to V288, and V289's `(875,2301)`. V291's `(962,958)` reached the car only inside V292.
* **No flown build has ever zeroed the LKAS rate feedback.** There is no on-car evidence, in either
  direction, for what torque mode does to this car.

🛑 **Therefore, if the session goes to torque mode, it is re-running a lever that was designed,
adversarially reviewed and shelved — not a new one.** The honest framing for the operator is: *"V279 was
this, at a ×2.79 map; the proposal is V279's structure at V282's ×6 map, on a V292 base."* What is
genuinely different this time is (i) the map is ×6 rather than ×2.79, (ii) the base carries the V292
cave and its `0x14A` bit-3 liveness control, and (iii) the symptom being chased is grinding and the
high-angle stutter, where V279's stated target was the 3.9 Hz crossover and the bang-bang servo.

---

## 6. CORRECTIONS TO THE RECORD

| claim in the record | status | evidence |
|---|---|---|
| `0x29F18 sar 0x7,r2` is **P** = (Kp product) >> 7; `r9` is I (TRACE-2026-09-13-fb-lag-filter-bytes §4) | **WRONG — the registers are swapped.** `r2` is the **I accumulator**, shifted right 7; `r9` is **P**; `r8` is **D**. P is `(E·Kp) >> 8` clamped to `±[0xC61BC]`, formed at `0x29E36 mul` / `0x29E3E sar 0x8`. | `decompile_function(0x28ea6)`: `iVar16 = (iVar16 >> 7) + uVar13 + uVar33`, then `disassemble_bytes(0x29E2C)` showing `sar 0x8,r8` against the `0x71bc` clamp |
| `0x29A70 jr 0x2A0C6` is "SKIP 3", a reset route | **TOO WEAK.** It is a **second delivery mode** — a feedback-only viscous damper, `−sign(fb)·LERP(\|fb>>5\|)` over `0xC6710–0xC6730`. It is unreachable, which is why the mislabel has cost nothing so far. | `disassemble_bytes(0x2A0C6, 64)`; §3.6 |
| the cold-boot value of `gp-0x3d30` / `gp-0x3d2c` is **BELIEF** (fb-lag trace §5.4; V292 design §8.2) | **now EVIDENCE: both boot to 0.** The `.data` copy loop `0x1476C–0x14794` runs flash `[0x86260, 0x8AB18)` into RAM from `0xFEDF11B0`; `gp-0x3d30` ← flash `0x89380` = `00 00 00 00`, `gp-0x3d2c` ← `0x89384` = `00`. Control: `gp-0x6AB0` ← flash `0x86600` = `88 02 88 02`, the known non-zero cell. | `disassemble_bytes(0x14750, 80)` + Python |
| "`gp-0x69ae` has exactly 3 readers, **both GATES not summands**" | **imprecise.** It has 3 readers and 4 writers. `0x29124` is a gate (`\|cmd\| ≤ 0x4000`), but **`0x29032` is the command path** — it is clamped to the speed-scheduled LIM, scaled, shifted `>>22` and becomes the demand index that walks the assist map. "Not a summand" is true; "a gate" is not. | `decompile_function(0x28ea6)` lines feeding `uVar33`; controlled Python scan |
| the demand index formula omits the activity factor | the factor exists (`0xC6976..0xC6984`, axis `gp-0x6830`) but is **flat at 255** on stock, V282 and V292, so the recorded formula is exact. | Python byte read |
| the delivered rail is 2481 / 2505 | **2462 on the built cells.** The override taper is `((255·255)&0xFFFF)>>8 = 254`, so an always-on **×254/256** sits between the sum and the sum clamp. 2481 omits it. | the integer mirror, §4a |
| `search_instructions` on `-0x6a56` | returns **25**; the true count is **30** (extras at `0x14B1E`, `0x2D9BE`, `0x4F942`, `0x4F964`, `0x5150E`). The undercount trap, reconfirmed on a cell the record already documents as 30. | both methods, side by side |

---

## 7. WHAT I DID NOT VERIFY — and the exact next step for each

1. **The 8 counts per deg/s scale of `x`.** Every deg/s figure in this trace inherits it. It is
   consistent across three independent places in the record (the r24 trace's dead-zone column, the V292
   design's 1491 counts = 186.4 deg/s, and the rate-reference back-calculation), but I did **not**
   derive it from the sensor chain. **Next step:** decompile `FUN_00041464` (the four `st.h -0x6abe`
   writers at `0x41790/0x417A0/0x419F8/0x41A18`) and convert the raw sensor's own units, then multiply
   by the 1.697754 factor of §1.2.
2. **`Ts = 1 ms`.** EVIDENCE-by-consistency only (two label↔byte agreements: stock `a = 923` → 16.53 Hz
   matches the record's "16.5 Hz"; V289's `a = 875` → 25.03 Hz matches its own build tag `FBPOLE.25HZ`).
   **Not** a scheduler read. **Next step:** read the timer ISR period.
3. **`gp-0x69ae = clamp(−4·wire, ±0x4000)` and `1 LSB = 16.125736 wire counts`.** Inherited **[E]** from
   `reference_accord_0e4_handler_x4_verified_and_gp6803_is_set_me_x00`; I confirmed the four writers and
   the two readers but did not re-derive the arithmetic. **Next step:** `decompile_function(0x52600)`.
4. **Which speed taper is live, C (`0xCBAE4`) or D (`0xCBBC4`).** My reading of the selector says
   `bVar1 = true` → A×C, and `bVar1` is `(speed ≤ 32000)` gated by five plausibility cells and
   `gp-0x67f4 == 1`; the kit memory says the live fade is `0xCBBC4` = D, i.e. `bVar1` false. A ≡ B so
   only the C/D choice matters, and C and D differ materially (0.20 vs 0.30 at their top knots).
   **Next step:** `analyze_dataflow` on `bVar1`'s producer at `0x28F0x`, or read `gp-0x67f4`'s writers.
5. 🛑 **The EME / sustained-effort interlock for option (a).** This is the one open item that could
   return "do not flash". Torque mode does not raise peak torque, but it raises **dwell at peak**.
   **Next step:** census the readers of `gp-0x6b94`, `gp-0x6ace` and `gp-0x6acc` for any accumulator or
   timer, decompile the governor `FUN_0004503c` and `FUN_000456a4`, and check for an integrate-and-trip
   structure. My `FUN_0004595a` read shows an instantaneous comparator, not an integrator — but that is
   one monitor, not the census.
6. **Register-indirect writers.** All my "zero writers" results (`gp-0x680a`, `gp-0x6D70`) come from
   operand-text and raw-displacement scans, which cannot see a store through a pointer. The `.data` boot
   values corroborate but do not close it.
7. **Closed-loop stability of any option.** I priced none of them. Option (b) in particular inserts a
   differentiator into the feedback and I have stated only what the arithmetic gives; `gate73`, `Ms`,
   `pkR` and the plant family are untouched here.
8. **I did not re-derive the lane-to-aggregator path**; §3.5 is `ghidrafill`'s, spot-checked by
   reproducing its `gp-0x6b4c` census on three images.
