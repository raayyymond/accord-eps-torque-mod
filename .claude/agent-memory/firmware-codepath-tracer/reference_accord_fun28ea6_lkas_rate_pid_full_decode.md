---
name: reference_accord_fun28ea6_lkas_rate_pid_full_decode
description: Full decode of the control block at 0x29D6C-0x2A190 inside FUN_00028ea6 -- it is a PID on STEERING-RATE ERROR whose setpoint is the CAN-0xE4 LKAS torque command mapped through a variant table, and whose feedback is a first-order lag of gp-0x6a56 (column angular rate). Includes the CAN 0xE4 path end to end, the driver-torque override taper, the identity of gp-0x674e (static variant/table-set index) and gp-0x682f (|driver torque|>>5), and the fact that Ki (0xC63E6) is ZERO on stock AND V112 so the integrator is inert.
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
* Companion: `gp-0x6830 = |d/dt(lagged gp-0x4f60)| >> 6`, a driver "grab-rate" index; the LERP at
  `tp+0x7976` (`0xC6976`) X=[4,6,8,10,255] Y=[255,255,255,255,0] zeroes authority above index 10.

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

## Related
[[reference_accord_gp6abe_column_degps_scale_settled]] -- the 8 counts/deg-s scale for gp-0x6a56.
[[reference_accord_gp4f60_identity_conflict_and_producer_traced]] -- gp-0x4f60's producer + identity flag.
[[reference_accord_arb_input_cluster]] -- older inventory; its `gp-0x6a5e = fused driver torque` label
is superseded (voted vehicle speed; the 0xCB844 X breakpoints 3200..8320 divide by 64 into
50.0/53.3/56.7/60.0/74/88/102/116/130 km/h, and the 0x7D00 sentinel is 500 km/h).
