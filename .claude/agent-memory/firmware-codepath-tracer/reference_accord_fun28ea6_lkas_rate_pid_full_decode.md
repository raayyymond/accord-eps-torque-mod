---
name: reference_accord_fun28ea6_lkas_rate_pid_full_decode
description: Full decode of the control block at 0x29D6C-0x2A190 inside FUN_00028ea6 -- it is a PID on STEERING-RATE ERROR whose setpoint is the CAN-0xE4 LKAS torque command mapped through a variant table, and whose feedback is a first-order lag of gp-0x6a56 (column angular rate). Includes the CAN 0xE4 path end to end, the driver-torque override taper, the identity of gp-0x674e (static variant/table-set index) and gp-0x682f (|driver torque|>>5), and the fact that Ki (0xC63E6) is ZERO on stock AND V112 so the integrator is inert. Updated 2026-09-01 -- the driver override is TWO mechanisms (the Y taper AND a 0xC64B4-B7 debounce that writes gp-0x6807=4), all eight of whose cals are disarmed on a V112/V268 base; the 0xC6974 grab-rate taper is 4-knot FLAT and inert (correction to an earlier revision); and the 6-byte extended-displacement gp-relative encoding is decoded here.
metadata:
  type: reference
---

# FUN_00028ea6 0x29D6C-0x2A190 is a STEERING-RATE PID. Traced fresh 2026-08-31 (GhidraMCP, stock `code.bin`).

`gp=0xFEDF8000`, `tp=0xBF000`. All addresses below are instruction addresses I read this session.

## The error (0x29d78) [EVIDENCE -- disassemble_bytes dry_run + register liveness scan]

```
00029d6c mulh  r13,r16          ; r16 = sign * LERP_c9a88[variant](|torque request|)  = RATE SETPOINT
00029d72 st.h  r16,-0x6a32[gp]  ; setpoint published to gp-0x6a32
00029d76 shl   0x5,r16          ; x32
00029d78 sub   r26,r16          ; >>> THE ERROR = 32*setpoint - r26 <<<
```
`r26` is written ONLY at 0x28f7c/0x28f84/0x28fa4/0x28fae/0x28fb8/0x28fbc (the rate-lag block) and
0x290b6 (`mov 0,r26`, gate-fail path). Verified by scanning every `r26`-bearing line of the whole
function disassembly -- no write between 0x290b6 and 0x29d78. So **the subtrahend IS the clamped
output of the gp-0x3d30 first-order lag.**

* **Minuend = setpoint** = `sign(req) * LERP(PTR[0xC9A88 + 4*gp-0x674e])(|req|)`.
  Variant-0 table @0xE4000: X=[0,12,20,24,32,64,96,128,160,240] Y=[0,16,28,34,48,92,124,148,162,172].
* **Subtrahend = measured** = clamped lag of `gp-0x6a56` = **column angular rate**.

**Scaling proof that both operands are the same physical quantity:** the lag has DC gain
`b/(1024-a) = 1560/(1024-923) = 15.45`, and the output is `y_old + y_new ~= 30.9 x rate`, versus
`32 x setpoint` on the other side -- a 1.035 ratio. With the kit's settled `gp-0x6a56 ~= 8 counts per
column deg/s`, setpoint max 172 = **21.5 deg/s**, lag clamp 7680 = **31 deg/s**, deadband cal 4 (after
the `>>5`) = **0.5 deg/s**. Every constant lands on sane steering-rate numbers.

## The two accumulators are DIFFERENT (the brief that sent me here conflated them)

| state | cals | input | clamp |
|---|---|---|---|
| `gp-0x3d30` | `tp+0x73E8`=923 (a), `tp+0x73EA`=1560 (b), `>>10` | **`gp-0x6a56` = column angular rate** | output clamped +-`tp+0x72E6`=7680 |
| `gp-0x3d34` | `tp+0x73E2`=31 (a), `tp+0x73E4`=634 (b), `>>5` | **`gp-0x4f60` = driver/column torque** | its per-cycle DELTA clamped +-0x3200 (a literal, NOT 0x72E6); `>>6` -> `gp-0x6830` |

`gp-0x3d2c` is the cold-start flag: !=1 -> both states read as 0. Set to 1 on the pass path, 2 on fail.

## The PID (0x29d9c-0x2a190) [EVIDENCE]

* deadband on the I path only: `e_db = deadband(err>>5, +-tp+0x72E4=4)`
* **I**: `gp-0x6dd0 = clamp((gp-0x6dd0>>3) + (e_db * tp+0x73E6)>>3, +-(tp+0x71BA<<10>>3))<<3`
  🛑 **`tp+0x73E6` (`0xC63E6`) = 0 on stock AND on the V112 image.** The integrator gain is ZERO --
  the I path contributes nothing and `gp-0x6dd0` (BSS-zero) stays 0. Anyone treating this integrator
  as live is wrong on this calibration.
* **P**: `clamp((32*err * LERP_cb994[variant](|req|))>>8, +-tp+0x71BC=15360)`  (Kp 205..696)
* **D**: `clamp(((32*err - gp-0x6cf8) * LERP_cb7d4[variant](|req|))>>3, +-tp+0x71B6=10240)`;
  `gp-0x6cf8` is written with `32*err` at 0x2a18c -- so D is on the ERROR, not the setpoint.
* sum `= (I>>7) + P + D`, then x LERP_cbb54/cbc34 (index `gp-0x6830`) x LERP_cbae4/cbbc4
  (index `gp-0x682f`), each `>>8`, clamp +-`tp+0x71BE`=15360 -> `gp-0x6b2e`
* then a second lag (`tp+0x73EC`=992/`tp+0x73EE`=507, state `gp-0x3d3c`), a sign/hysteresis gate
  (`tp+0x74A3`, `tp+0x71B8`=102, `gp-0x6806`), then **x engagement ramp `gp-0x69b0` (Q15) >>15**
  -> `gp-0x6b30`
* finally `clamp((other_lane + gp-0x6b30) * gp-0x6752 * tp+0x746C(891) >> 15, +-tp+0x71B4)`
  -> `gp-0x6b38` -> `gp-0x6b3c`.  `0xC61B4` = **512 stock, 3072 in V112**.
  ⚠ the summand is NOT driver torque -- Ghidra's `iVar28` is reused; by 0x2a1fc it holds a
  `gp-0x6b2c`/`tp+0x773E`-`0x7744` lane value. I nearly reported that wrong.

## YES, the CAN steering command is an input -- full path [EVIDENCE]

CAN **0xE4** (Honda `STEERING_CONTROL`) -> mailbox -> RAM `0xFEDF6BD8`
-> `FUN_00021724` @0x21724 byte-swaps `gp-0x1428`/`gp-0x1427` (payload bytes 0-1, big-endian signed)
-> `FUN_00052676` (the 0xE4 RX handler) writes `gp-0x69ae = clamp(cmd * -4, +-0x4000)`
   (0x5268c/0x526f2/0x52726/0x527c6; sole writer; `0x7FFF` sentinel on timeout) and the frame's
   mode bits to `gp-0x6802/6803/6804/6805`
-> `FUN_00028ea6` @0x29032 clamps it to a **speed-scheduled envelope** LERP[0xCB844+4*variant]
   indexed by `gp-0x6a5e`
-> x driver-override taper x rate gain -> torque request -> clamp +-240 (`0xC64F0/F1`)
-> **LERP[0xC9A88+4*variant] maps it to the RATE SETPOINT.**

**Descriptor proof that FUN_00052676 owns 0xE4:** the CAN RX table record layout is
`[+0 idx][+4 mode][+8][+0xC][+0xE id][+0x10][+0x14 buffer][+0x18][+0x1C handler]`; the record at
0xBB624 has id `0x00E4`, buffer `0xFEDF6BD8`, handler `0x00052676`. Cross-checked against the
neighbouring record (buffer `0xFEDF6B98`, handler `0x52608`, which indeed reads `gp-0x1463`).

## gp-0x674e and gp-0x682f [EVIDENCE]

* **`gp-0x674e` = static VARIANT / TABLE-SET index.** Sole writer `FUN_00042692` @0x4272a:
  `gp-0x674e = byte at 0xCD012 + 0x24*hwid + 8`. That is the 36-byte-per-record part-number config
  table (16 records, ASCII "TVAA05360Y", "TVAA15360Y", "TVAC15360Y", ... then 0xFF filler); the field
  takes values {0,1,3,4,6,7,8,9}. It is NOT a runtime signal. `gp-0x674e<<2` indexes a bank of
  **28-entry** pointer arrays laid out contiguously at 0xCB7D4, 0xCB844, 0xCB8B4, 0xCB924, 0xCB994,
  0xCBA04, 0xCBA74, 0xCBAE4, 0xCBB54, 0xCBBC4, 0xCBC34 (stride 0x70 = 28 x 4).
* **`gp-0x682f` = `min(|gp-0x4f60| >> 5, 255)`** -- driver-torque magnitude index. Written only at
  0x29068 and 0x290b8 (both in FUN_00028ea6). `gp-0x682f > tp+0x74B8` **kills the LKAS torque
  request outright** (`0xC64B8` = 112 stock = |torque| 3584; **255 in V112**, i.e. that cutout is
  disabled there).
* Companion: `gp-0x6830 = |d/dt(lagged gp-0x4f60)| >> 6`, a driver "grab-rate" index; it indexes the
  LERP whose record starts at `tp+0x7974` (`0xC6974`).
  🛑 **CORRECTED 2026-09-01 (operator-confirmed from bytes):** that record is **4 knots, X=[4,6,8,10],
  Y=[255,255,255,255]** — raw `0xC6974` = `04000400060008000a00ff00ff00ff00ff00`. It is **FLAT and
  INERT**, on stock AND V268. An earlier revision of this note recorded it as 5 knots ending `Y=0`
  "zeroing authority above index 10" — that was WRONG. The code's hardcoded 4-knot offsets confirm 4:
  `movea 0x7974,tp,r9` @0x29c5a, `add 0xa,r9` @0x29c68 -> `&Y[0]`=`0xC697E`, and the clamp-high load
  `ld.hu 0x7984,tp` @0x29c86 -> `Y[3]`=`0xC6984`.

## The driver-override taper (why gp-0x4f60 is TORQUE, functionally)

At 0x29a8e-0x29a9e the code forks on `sign(clamped LKAS cmd)` vs `sign(gp-0x4f60)`; each fork picks a
pair of tables (further selected by `gp-0x6803 == 2`, a CAN-0xE4 mode bit):
`cba74[0]`/`cba04[0]` X=[70,72,78,80,254] Y=[254,234,12,0,0]; `cb924[0]`/`cb8b4[0]`
X=[32,42,80,112,255] Y=[255,255,255,0,0]. Authority collapses to zero as driver torque rises.
A driver-torque override axis, not a velocity axis. (The CAN399 `STEER_TORQUE_SENSOR` DBC bridge is
inherited kit evidence, not re-derived here -- see
[[reference_accord_gp4f60_identity_conflict_and_producer_traced]].)

## FUN_0002a93a is a DEAD twin of this block [EVIDENCE, positive-controlled]

`gp-0x6dd0` and `gp-0x6cf8` each have exactly 2 touches in `FUN_00028ea6` and 2 in `FUN_0002a93a`.
`get_function_callers(FUN_0002a93a)` = none; a raw Python `jarl` disp22 scan (opcode field 0x1E,
hw1 bits 6-10) over 0x13000-0x100000 found **0x22522 -> 0x28ea6** and **0x23276 -> 0x34350** (both
controls) and **zero** calls to 0x2a93a; `0x0002a93a` also never appears as a 32-bit LE word anywhere
in the image, so it is not in any dispatch table. Residual: a computed `jmp` could still reach it.
=> the PID state is owned solely by FUN_00028ea6.

## 🛑 THE DRIVER OVERRIDE IS **TWO** MECHANISMS, NOT ONE (traced 2026-09-01, GhidraMCP + raw LE Python)

`gp-0x682f` (= `min(|gp-0x4f60|>>5, 255)`, a **zero-extended byte, hard ceiling 255**) drives BOTH:

**(A) The multiplicative Y taper** — `0x29A8E-0x29CC2`, banks `0xCBA74`/`0xCB924` (signs agree) and
`0xCBA04`/`0xCB8B4` (signs oppose); within a pair, `gp-0x6803 == 2` picks the first
(`cmovne` @0x29B76 / @0x29C52). Y multiplies demand at `mulu` @0x29CB4 -> `mul r22` @0x29CBC ->
`sar 0x10`. ⚠ `andi 0xffff` @0x29CB8 means **Y must stay <= 257** or the product wraps.
Records are **4-knot and the code hardcodes it** (`add 0xa`, `+6`); it never reads the `s16` count.
Clamps to `Y[0]` below `X[0]` and `Y[3]` at/above `X[3]`; no OOB.

**(B) A debounce -> latch -> STEER_STATUS path** — counter `gp-0x6758`, latch `gp-0x6757`, writing
**`gp-0x6807 = 4`** (@0x2928E/0x292AE/0x2A470/0x2A490). Thresholds are byte cals compared unsigned
against the SAME `gp-0x682f`: **`0xC64B4`/`B5`/`B6`/`B7`**, in parallel with |torque-rate| vs
halfword cals **`0xC61C0`/`C2`/`C4`**. On STOCK it fires at index 54 = raw 1728 — *below* the taper's
own knees, so on a stock-cal base (B) is the binding override, not (A).

**All eight of those cals are DISARMED on a V112/V268 base** — `0xC64B4..B8` = **255** (stock
112/96/54/64/112) and `0xC61C0/C2/C4` = **0xFFFF** (stock 1600/896/1280). Every compare is an
unsigned `bh`/`bnh` against an operand that cannot exceed 255 (resp. 12800), so **both (B) and the
`0xC64B8` hard cutout are UNSATISFIABLE there** and the Y taper is the only surviving mechanism.

**Containment result (two methods, positive control passing):** ALL **20** writers of `gp-0x6807`
and ALL **24** writers of `gp-0x69b0` live in `FUN_00028ea6` + `FUN_0002a30e`. `gp-0x6807` has only
two readers outside them, `0x4E8EC` (`FUN_0004e82e`) and `0x55C96` (`FUN_00055c42`) — both CAN
frame builders, report-only. Non-torque routes to `gp-0x6807` do exist in the same SM
(`0x29130-0x291D8`): fault word `gp+0x6400` bit 4 -> 6; `gp-0x6758 >= 0xC64E0+0xC64E1` (50+50) -> 7
plus **DTC 0x49** via `jarl 0x16de6` @0x291CA; and a `setfc` flag -> 3.

**Tooling lesson from this trace — NEITHER tool was complete alone.** For `gp-0x4f60`: raw disp16
Python found 69 sites, Ghidra `search_instructions` found 73; Ghidra missed 3 (unanalysed/unbound
code) and Python missed **7 six-byte extended-displacement sites** (0x4C784, 0x59BFA, 0x59C02,
0x59C44, 0x59C4C, 0x5A0BC, 0x5A0C4). Union = 76. Same for `gp+0x6400`: Python missed the 6-byte
writer at `0x4A882`.
**The 6-byte gp-relative form, derived from that ground truth and positive-controlled 7/7:**
`hw1` bits0-4 = reg1 (gp=4), `hw1` bits11-15 = 0, `hw1` bits5-10 in {0x3C,0x3D};
`reg3` = `hw2>>11`; **`disp[6:0] = (hw2>>4)&0x7F`, `disp[22:7] = hw3`.**
Example `ld.h -0x4f60, gp, r6` = `84 07 07 32 61 ff`.

## 🛑 `gp+0x6400` IS NOT A FAULT WORD — it is the STATIC VARIANT-CODING word (traced 2026-09-01)

The `STEER_STATUS = 6` route at `0x29172` (`ld.w 0x6400,gp,r6` / `shr 0x4` / `bnc`) tests **BIT 3
(mask 0x8)**, not bit 4 — `shr` sets CY from the LAST bit shifted out, so `shr 0x4` yields bit 3.
Ghidra's decompiler of the twin in `FUN_0002a30e` says it outright:
`if ((*(uint *)(&DAT_00006400 + unaff_gp) & 8) != 0) { *(gp-0x6807) = 6; }`.

`gp+0x6400` (`0xFEDFE400`) has ~90 readers and exactly **3 writers**, all configuration-time:
`0x50ABE`/`0x50B52` in **`FUN_000508e8`** (the UDS variant-coding write service) and `0x4A882` in
`FUN_0004a798` (`st.w r10, 0x6400, gp`, the **6-byte extended form** — a disp16 scan misses it; it is
an NVM restore that also writes `gp+0x63F4` and `gp+0x6404`). `FUN_000508e8` derives the word bit by
bit from the per-part-number config record at **`0xCD01B`/`0xCD01C`** (0x24 stride, the same table at
`0xCD000` that yields `gp-0x674e`). Bit 3 is set when `(0xCD01B + 0x24*hwid) & 4 == 0`.

**Dumped all 16 records: bit 3 is SET only for record 0, the blank/uncoded `000005360Y`
(`CD01B = 0x80`). Every real TVA/TVC/TWA part number has `CD01B` = 0x35 or 0x75, both with bit 2 set,
so bit 3 is CLEAR.** => `STEER_STATUS = 6` fires only on an UNCODED ECU. It is a static per-variant
constant, not reachable by driving, torque, current or temperature.

## 🛑 DTC 0x23 (the current/thermal governor's) IS UNSATISFIABLE — cal `0xC71A4` = 41038

`FUN_00036828` tail, instruction level:
```
00036b1c shl   0x5, r8          ; governor output <<5
00036b22 zxh   r8               ; <<< CAPS r8 AT 65535, and it is a multiple of 32
00036bc6 mul   r8, r9, r0       ; r9 = r8 * (0 or 1)
00036bce sar   0x5, r9          ; => r9 <= 2047, ALWAYS
00036bd0 zxh   r9
00036bca ld.hu 0x71a4, tp, r7   ; r7 = 0xC71A4 = 41038 (V268 AND stock)
00036bd2 cmp   r7, r9
00036bd4 bc    0x36be4          ; unsigned r9 < r7 -> skip; DTC 0x23 needs r9 >= 41038
```
`2047 < 41038`, both operands unsigned (`ld.hu` + `bc`). **Structurally impossible, at any dose.** The
`zxh` at `0x36b22` caps the quantity BEFORE the shift, so no amount of added motor duty can reach it.
Neighbouring cals share the look of disabled sentinels: `0xC71A0`=41036, `0xC71A8`=41040,
`0xC71AC`=41042, `0xC71B0`=45116, against live-looking 14s at `0xC719A`/`0x719E`/`0x71A2`/`0x71AA`.

## `FUN_0002a30e` liveness is UNRESOLVED (do not call it live OR dead)

`0x2A30A` is `dispose ... lp` (FUN_00028ea6's return) and `0x2A30E` is a real `prepare
{r20,r22,r24,r26,r28,lp}` prologue taking 5 params — so it is a separate function, **not** a
branch-reached tail of `FUN_00028ea6` (an earlier note of mine implied otherwise).
A **positive-controlled** raw `jarl` disp22 scan finds **no caller**, and `0x0002a30e` appears nowhere
as a 32-bit LE word. **But that scan does not decode the 6-byte `jarl disp32` form**, and it takes
parameters, so "dead" is not safe to assert. It uses the SAME cals as the `FUN_00028ea6` copy, so the
override conclusions hold either way.
⚠ One thing that WOULD differ if it is live: its rate compare is `*(ushort *)(tp+0x71c0) < param_1`
with `param_1` a **uint** from the caller. In `FUN_00028ea6` the same operand is `r28`, clamped to
+-12800, so `0xFFFF <` is unsatisfiable; for `FUN_0002a30e` param_1 is unbounded until the caller is
identified.

**`jarl` disp22 decode, positive-controlled 3/3** (0x22522->0x28ea6, 0x23276->0x34350,
0x2291e->0x3aa2c): opcode field `(hw1>>6)&0x1F == 0x1E`;
**`disp = sign_extend22( ((hw1 & 0x3F) << 16) | hw2 )`**, target = addr + disp.

## Related
[[reference_accord_gp6abe_column_degps_scale_settled]] -- the 8 counts/deg-s scale for gp-0x6a56.
[[reference_accord_gp4f60_identity_conflict_and_producer_traced]] -- gp-0x4f60's producer + identity flag.
[[reference_accord_arb_input_cluster]] -- older inventory; its `gp-0x6a5e = fused driver torque` label
is superseded (voted vehicle speed; the 0xCB844 X breakpoints 3200..8320 divide by 64 into
50.0/53.3/56.7/60.0/74/88/102/116/130 km/h, and the 0x7D00 sentinel is 500 km/h).
