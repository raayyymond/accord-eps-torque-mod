---
name: reference-accord-deadband-signgate-eliminated-on-car
description: "gp-0x6806 IS TRANSMITTED as STEER_CONTROL_ACTIVE (CAN 0x18F byte4 bit3). Measured: 2 transitions in 180 s, ==1 in 96.26% of frames. The 0xC61B8 deadband + sign relay is bypassed during steady engaged driving and cannot be a 20-25 Hz mechanism."
metadata:
  node_type: memory
  type: reference
---

**Settled 2026-07-29 BY MEASUREMENT, after four independent static traces disagreed with each other.
The lesson is the finding: static reachability told us the gate CAN activate; the bus told us how often
it DOES.**

## The block (verified against current bytes, `FUN_00028ea6` `0x2a1ae`-`0x2a206`)

```python
# 0x2a1ae cmp 0x1,r16 / 0x2a1b4 bne 0x2a1e6   -> cal 0xC64A3 != 1 : SKIP, iVar34 passes UNMODIFIED
# 0x2a1b6 ld.bu -0x6806 / 0x2a1bc bne 0x2a1e6 -> gp-0x6806 != 0  : SKIP, iVar34 passes UNMODIFIED
if cal_0xC64A3 == 1 and gp_0x6806 == 0:
    L = 102                                    # cal 0xC61B8, ld.h SIGNED @0x2a1be, ld.hu UNSIGNED @0x2a1ca
    if -L <= iVar34 <= L:      iVar34 = 0       # flat deadband
    elif iVar34 * gp_6b30_prev <= 0: iVar34 = 0 # sign guard (integer product; signs differ OR either == 0)
iVar34 = (iVar34 * gp_0x69b0) >> 15             # ramp gain -- ALWAYS applied
gp_6b30 = iVar34                                # 0x2a206 -- ALWAYS stored, gated or not
```

⚠ **It IS on the forward path to the motor** — a subagent traced `st.h r1,-0x6b38 @0x2a23c` and concluded
"diagnostic side-channel only". That is a FALSE NEGATIVE: `r1` is ALSO consumed downstream.
```
0x2a1fc add   r9,r11          <- the gated iVar34 enters r11
0x2a1fe mul   r13,r11,r0      <- x POLARITY x GAIN(0xC646C)
0x2a202 sar   0xf,r11
0x2a226 mov   r11,r1
0x2a23c st.h  r1,-0x6b38,gp   <- a DIAGNOSTIC COPY (UDS record builder FUN_0004e82e)
0x2a2c2 cmove 0x0,r1,r16      <- ...and r1 ALSO goes to r16
0x2a2ea st.h  r16,-0x6b3c,gp  <- the arbitration OUTPUT -> gp-0x6b4c -> aggregator -> gp-0x6b98 -> motor
```
Both stores happen. Never conclude "diagnostic" from the first store you meet.

## ★★ `gp-0x6806` IS OBSERVABLE ON THE BUS — use this, don't infer it

The CAN 0x18F packer `FUN_00055c42` writes `gp-0x6806` to **byte4 bit3** and `gp-0x6807` (STEER_STATUS)
to **byte4 bits 7:4**. That matches opendbc `BO_ 399` exactly
(`STEER_CONTROL_ACTIVE : 35|1@0+`, `STEER_STATUS : 39|4@0+`).

**⇒ `STEER_CONTROL_ACTIVE` in any rlog IS `gp-0x6806`.**

Measured, route 24 (V56, road), segments 9-11:
```
18,000 frames, 180.0 s @ 100 Hz
gp-0x6806 == 1 : 17,326  (96.26%)   -> deadband/relay BYPASSED
gp-0x6806 == 0 :    674  ( 3.74%)   -> deadband/relay ACTIVE
transitions    : 2 in 180 s  =  0.011 /s
shortest run   : 6,740 ms   ->  max possible toggle frequency 0.1 Hz
```

⇒ **Two transitions in three minutes, against a mode at 20-25 Hz.** The gate is inert through steady
engaged driving and cannot chop. The "relay limit cycle" hypothesis — which fit the entire symptom
profile (hands-off, engagement-dependent, killed by directional torque, killed by saturation, frequency
drifting with speed) — is **DEAD**. It explained too much for something never measured.

## What remains TRUE and still worth fixing someday

`0xC61B8` = 102 in stock, V38, V55 and V56 — **never rescaled**, while its siblings `0xC61B2`/`0xC61B4`
went 512 → 2048 (x4) in lockstep with the gain. With openpilot's PID quartered, the pre-gain signal is 4x
smaller against an unchanged threshold, so the dead zone covers ~4x more of the LKAS working range than
the factory validated. **That is a real defect — but it lives on the ENGAGE RAMP, not in steady state**,
so it is not a vibration lever. `0xC61B8 -> 26` (102 x 891/3564 = 25.5) would finish the lockstep scaling.
**Not shipped in V57**; needs its own justification.

## Corrections of record generated here

- 🛑 A 2026-07-20 note claimed the zero-writers require `STEER_STATUS ∈ {3,4,7}`. **Two of them have paths
  that never test STEER_STATUS**: `0x29696` via `(r8==0 AND gp-0x6803==2)`, `0x2970e` via
  `(r8==0 AND gp-0x679e==0)`. The conclusion survived; the reasoning did not.
- 🛑 "`gp-0x6b30` has exactly 2 references image-wide" is right about LIVE refs but a raw byte scan finds
  **4** — `0x2A1D4`/`0x2A206` (live, in `FUN_00028ea6`, which ends at `0x2a30d`) plus `0x2A8DE`/`0x2A900`
  **above** that, inside the known-dead `FUN_0002a30e`/`FUN_0002a93a` copies. Same trap applies to
  `gp-0x6806`: 16 raw writers, **8 live + 8 dead-echo**. Always split at `0x2a30d`.
- The state machine: state var `gp-0x3d38` (9 states, dispatch table `0x29322`-`0x29356`), phase byte
  `gp-0x679f`, score/ramp `gp-0x69b0`. Cold boot dispatches state 0 → reset handler → `gp-0x6806 = 0` on
  the first cycle regardless of RAM contents, which moots the .bss question.

**How to apply:** before building against ANY internal flag, check whether it is already on the bus.
`gp-0x6806` cost four subagent traces and one wrong conclusion; the rlog answered it in one query.
See [[reference-accord-driver-override-curve-kills-lkas-authority]] and [[v57-decouple-built]].
