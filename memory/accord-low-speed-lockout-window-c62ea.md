---
name: accord-low-speed-lockout-window-c62ea
description: "The A160 low-speed steer lockout is cal 0xC62EA=320 (~5 km/h), a two-sided speed window vs voted speed gp-0x6a5e; failing it writes STEER_STATUS=3 which blocks STEER_CONTROL_ACTIVE and the authority ramp. Cal-only fix, no float mirror."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 999fba26-ffc6-4a2f-9832-a51b221c590a
  modified: 2026-07-25T07:31:58.330Z
---

# The low-speed steer lockout — located, verified, and cal-only (2026-07-24/25)

**The lever:** `0xC62EA` (`tp+0x72EA`) = **320** ≈ **4.995 km/h (3.104 mph)**. Upper bound `0xC62E8`
(`tp+0x72E8`) = **12800** ≈ 199.8 km/h. **Each has exactly ONE reader image-wide** (`0x28EBC` / `0x28EB6`,
both `ld.hu` subop `0x3F`), both plain u16 with **no float mirror**, in the `0xC6000` CRC block every
cal-only build already touches. Speed unit ≈ **64.0625 counts/km/h** (`×41>>6` from a 0.01 km/h CAN raw).

**The chain (verified instruction-by-instruction):**
```
0x290C8 cmp r2(HI),r10 / 0x290D2 cmp r31(LO),r10   ; window vs voted speed gp-0x6a5e
0x290EA ld.bu gp-0x68b3                            ; bypass, set ONLY when speed==0 exactly
0x2918E cmp r0,r27 / bne                           ; bVar2 tested exactly once
0x29192 mov 3,r6 / 0x29194 st.b r6,-0x6807[gp]     ; STEER_STATUS = 3 = LOW_SPEED_LOCKOUT
...
0x2937E ld.bu gp-0x6807 / 0x29382 cmp 2,r6 / 0x29384 bnh -> 0x29392
   ST>=3 falls through to 0x2938E `jr 0x29734` -> disengage: gp-0x6806=0, ramp=0
   ST<=2 reaches 0x2939A mov 1,r6 / 0x293A6 st.b -> gp-0x6806 = STEER_CONTROL_ACTIVE = 1
                          0x293AC st.h -> gp-0x69b0 authority ramp += 33 (cal 0xC63F8)
```
`STEER_CONTROL_ACTIVE` = `gp-0x6806 & 1` (packer `FUN_00055c42`: `shl 3`; STEER_STATUS is `shl 4`).
**On-car:** 0% control-active below 2 mph while OP commands, 88% at 3-4 mph, ≥99% above 4 — and ZERO
frames ever have control-active together with status 3. Three independent decoders, ~305k frames.

**Standstill asymmetry proves it is deliberate:** `gp-0x68b3` (writer `0x4d148`) is set only when speed is
*exactly* 0, so 0 km/h bypasses the window but 1-319 counts cannot.

**⚠ The AND-chain has 5 conjuncts**, so ST=3 is not proof the window failed: also `gp-0x67fe==2`
(substate), `gp-0x69aa==0x8000` (governor Q15 derate, cal `tp+0x73f2`=32768), `gp-0x69ae` within ±0x4000,
and a 5-channel validity test. If a lowered `0xC62EA` doesn't work, `gp-0x69aa` is the next suspect.

**The second 320-count gate `0xC62EE` is NOT a lockout** — it is a permissive inside a **CAN-commanded**
assist-shutdown task, triggered by `gp-0x6877`/`gp-0x6879` which come from **CAN `0x17C` POWERTRAIN_DATA
byte 5 bits 7/5** (`0xFEDF6BED`, written in `FUN_000524bc` @`0x524E6`/`0x524EA`). Normally 0.
**Leave it stock — and never RAISE it**, or a commanded assist-kill could fire at higher road speed.

**openpilot is not the obstacle:** `CP.minSteerSpeed = 0.0` for HONDA_ACCORD (`CarSpecs` default; the
`min_steer_speed=3 mph` at `values.py:163` is `HondaCarDocs` website metadata). The only OP floor is the
hardcoded `0.3` m/s in `controlsd.py:178`, bypassable via `CP.steerAtStandstill` (Honda sets it nowhere).

Full write-up: `docs/HANDOFF-2026-07-24-low-speed-steer-lockout.md`. See
[[accord-v850-scan-traps-formatv-and-storezero]] and [[accord-fun45608-authority-slots-not-motoroff]].
