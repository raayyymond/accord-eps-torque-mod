---
name: reference-accord-gp3574-v21-startup-trace
description: Full downstream trace of gp-0x3574 after sar 0x8 at 0x43136 in V21; confirms no lockstep or plausibility fault on first call; all lockstep checks are consistency checks not range checks
metadata:
  type: reference
---

# gp-0x3574 downstream consumption trace: V21 first-call analysis

Program: `../accord-firmware/analysis-2020accord/_v22_plain_image.bin` (V22 binary used as base for V21 comparison).
Function: `FUN_00042af8` (s_motor_torque_rate_shaper, entry 0x42af8).

## Binary search confirms: ONLY 2 accesses to gp-0x3574 in entire firmware

- `0x42DAA`: `ld.w -0x3574, gp, r11` — read (IIR path only, skipped when bypass fires)
- `0x42DCC`: `st.w r11, -0x3574, gp` — write (both IIR and bypass converge here)

No other function in the firmware reads or range-checks gp-0x3574. Confirmed via byte search for pattern `8D CA` (displacement bytes) across the entire 1MB binary.

## V21 shl 0x9 mechanics (disasm-verified)

Two distinct `shl` instructions were changed:

| Address | V22 stock | V21 | Role |
|---------|-----------|-----|------|
| `0x42DAE` | `shl 0x8, r9` | `shl 0x9, r9` | IIR target scale: r9 = LERP3_output * 512 |
| `0x42DCA` | `shl 0x8, r11` | `shl 0x9, r11` | Bypass/snap: r11 = LERP3_output * 512 |

Both paths converge at `0x42DCC: st.w r11, -0x3574, gp`.

The IIR is **internally consistent**: target at ×512, state at ×512 (from prior bypass).
IIR formula: `state += (LERP3*512 - state) * alpha >> 10`, both sides at same scale.

## Startup scenario (first call, LKAS not engaged)

At startup:
- `cVar4` = 0 (LKAS not engaged, `tp+0x74ca` byte = 0)
- Bypass fires at `0x42DA0: be 0x42DC8`
- `r9` = LERP3 output (column velocity lookup, Y-table at gp-0x6444+y_shift)
- `local_d4[0]` = `gp-0x6444[0]` = 0 (RAM zero-initialized)
- `y_shift` = LERP1_output = 2048 (from `tp+0x7770` at speed=0)
- Effective LERP3 Y[i] = 0 + 2048 = 2048 everywhere at startup
- LERP3 output = 2048 (interpolated or flat)

**V21 bypass path:**
```
r11 = 2048 << 9 = 1,048,576
gp-0x3574 = 1,048,576
sar 0x8 at 0x43136: r11 = 4,096
```

**V22 stock (hypothetical for comparison):**
```
r11 = 2048 << 8 = 524,288
gp-0x3574 = 524,288
sar 0x8 at 0x43136: r11 = 2,048
```

## Downstream trace from 0x43136

```
0x43136: sar 0x8, r11         -> r11 = 4096 (V21) or 2048 (stock)
0x43138: cmp r23, r11         -> compare slew_rate bound vs envelope
0x4313c: cmovgt r11, r23, r10 -> r10 = max(r11, r23) = upper envelope floor
0x43140: subr r0, r15         -> r15 = -r23 (negate slew rate)
0x43142: sar 0x8, r9          -> r9 = gp-0x3578 >> 8 = lower envelope (same scale)
0x43144: cmp r15, r9          -> 
0x4314a: cmovlt r9, r15, r15  -> r15 = min(r9, -r23) = lower envelope ceiling
0x4314e: cmp r10, r7; cmovgt  -> r10 = max(r10, T1/T2 LERP) = final upper clamp
0x43154: cmp r15, r12; cmovlt -> r15 = min(r15, T2) = final lower clamp

... ramp-up state machine (gp-0x6752 = 0 at startup) ...
... multiply torque cmd by ramp_factor = 0 at startup -> cmd_scaled = 0 ...

0x43206: st.h r11, -0x6b08, gp  -> gp-0x6b08 = LKAS mode cmd (after clamp chain)
0x43214: ld.w -0x3570, gp, r10  -> load integrator
... integrator update with cmd_scaled=0 -> integrator stays 0 ...
0x4327c: st.w r10, -0x3570, gp  -> gp-0x3570 = 0

0x432B4: ld.hu -0x4c5a, gp, r14 -> load shadow (= 0 at startup)
0x432C0: cmp r14, r13            -> r13=uVar30=gp-0x6966 read at fn start = 0
0x432C4: bne 0x432D2             -> 0 == 0 -> MATCH -> no fault
0x432C8: st.h r13, -0x6966, gp  -> gp-0x6966 = 0
0x432CC: st.h r9, -0x4c5a, gp   -> gp-0x4c5a = 0
```

## All lockstep pairs in FUN_00042af8

| Pair | Main | Shadow | Check style | Fault if... |
|------|------|--------|-------------|-------------|
| 1 | `gp-0x6966` | `gp-0x4c5a` | uVar30 (read at fn start) vs shadow (read at check) | shadow != value read at fn start |
| 2 | `gp-0x6b04` | `gp-0x4cce` | main (read just before) vs shadow | main != shadow |
| 3 | `gp-0x6b98` | `gp-0x4ce2` | main (read just before) vs shadow | main != shadow |

All three are **consistency checks (main==shadow)**, NOT range checks. They detect if one half of a redundant pair was written without the other. At startup all pairs are (0,0) — all match.

## Verdict: No fault from gp-0x3574 on first call

The V21 wider envelope (4096 vs 2048) does NOT cause any lockstep or plausibility fault on the very first call because:

1. Lockstep checks are consistency checks, not range/magnitude checks
2. At startup, ramp_factor=0 means torque output=0 regardless of envelope width
3. All integrators and shadow values start at zero and stay zero on first call
4. gp-0x3574 has zero external readers — no other function can range-check it

## What V21's shl 0x9 DOES change

Starting from the FIRST LKAS-engaged cycle (cVar4=1), the envelope is 2x wider:
- Upper bound = 4096 (V21) vs 2048 (stock)
- Lower bound = -4096 (V21) vs -2048 (stock)

This is the INTENDED wider rate-shaper window. The IIR state is already pre-set to the correct scale (1,048,576) from the bypass-path startup, so there is no transient on engagement.

## Open question: actual V21 startup fault cause

The V21 startup fault (from `reference_accord_integrator_update_form` memory) states
"true startup fault cause is [OPEN] — code-integrity check most likely."

The gp-0x3574 path analysis rules out this path as the fault source.
Most likely candidates in priority order:
1. CRC/code-integrity check on modified function bytes (shl 0x8 -> shl 0x9 changes byte at 0x42DAE and 0x42DCA)
2. A separate watchdog that checks LERP table consistency for gp-0x6444 at init
3. An issue in a DIFFERENT function path not yet traced

See also: [[reference-accord-lerp3-gp3574-chain]], [[reference-accord-integrator-update-form]]
