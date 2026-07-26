---
name: accord-shaper-deadband-dropout
description: Verified mechanism that zeroes whole-power-steering transiently (no DTC) during hard override on sharp turn — Accord TVA-A160 s_motor_torque_rate_shaper deadband gate
metadata:
  type: reference
---

## The Dropout Mechanism (VERIFIED)

**Function:** `s_motor_torque_rate_shaper` (FUN_00042af8, 0x42af8)

Both base driver-assist (gp-0x6bf0) and LKAS (gp-0x6acc) converge inside this function into a single accumulator (gp-0x3570, int32). The final output gp-0x6b98 is the ONLY path to FOC — there is no separate base-assist path to the motor. Zeroing gp-0x6b98 kills both LKAS and base power steering.

### Demand accumulator (gp-0x3570)

- Integrates the delta between combined demand (`uVar25`) and its min/max limits each 1ms tick
- Clamped to +-(tp+0x71DC * 0x8000) = +-30720*32768 range
- `uStack_f0 = accumulator >> 15`; `uVar53 = |uStack_f0|`; max `uVar53` = 30720

### Deadband gate at `~0x43350` (VERIFIED bytes in decompile)

```c
uVar33 = uVar53 * *(u16*)(tp+0x71DA) >> 10;   // = uVar53 * 1092 / 1024
uVar34 = uVar33 & 0xffff;
if (uVar34 < *(u16*)(tp+0x7424)) {             // < 29491
    iVar45 = 0;                                  // HARD ZERO
} else {
    iVar45 = *(int*)(gp-0x356c);               // slew accumulator
    // ramp iVar45 toward sVar26 by step tp+0x71D6
}
```

**Threshold math:** fires when `uVar53 < 29491*1024/1092 = 27654`, i.e., when demand accumulator < **90%** of its maximum saturation value.

### Slew output (gp-0x356c) -> final demand

- With `cVar8 = tp+0x74C9 = 0`, final demand = `iVar45` (slew output, NOT raw demand)
- So when `iVar45 = 0` → `uVar34 = 0` → `gp-0x6b98 = 0` → motor command = 0
- `gp-0x356c` is overwritten with `iVar45` each cycle → when set to 0, stays 0 as long as deadband fires

### Slew step = 0 (tp+0x71D6 = 0x0000)

- No ramp movement: `iVar45 -= 0` or `iVar45 += 0`
- Once deadband sets iVar45=0, it STAYS zero until demand accumulator recovers above 90%
- Recovery time ≈ 27654/uVar25 ms (at combined demand 1000: ~27ms; at 500: ~55ms)

### Physical trigger for 2x-LKAS build

During a hard driver override opposing LKAS on a sharp turn:
1. LKAS pushing one way at 2x torque; driver pushing the other → net combined demand passes through zero
2. Demand accumulator drops below 90% threshold → deadband fires → iVar45=0
3. With step=0, slew stays at 0; accumulator takes tens-to-hundreds of ms to rebuild
4. During rebuild: gp-0x6b98 = 0 → **whole power steering (base + LKAS) is zero** → wheel goes heavy
5. No DTC because this is a computed state in the shaper, not a fault handler

The 2x gain makes the LKAS component larger, requiring a larger driver override, which makes the zero-crossing more abrupt and the accumulator drop faster.

## Calibration Values (VERIFIED at correct tp=0xBF000 base)

| Offset | Address | Value | Description |
|--------|---------|-------|-------------|
| tp+0x71D6 | 0xC61D6 | 0x0000 (bytes: 00 00) | Slew step (0 = disabled) |
| tp+0x71DA | 0xC61DA | 0x0444 = 1092 | Scale factor for uVar34 |
| tp+0x71DC | 0xC61DC | 0x7800 = 30720 | Accumulator clamp |
| tp+0x7422 | 0xC6422 | 0x4000 = 16384 | Lane-2 deadband threshold (50% of max) |
| tp+0x7424 | 0xC6424 | 0x7333 = 29491 | Main deadband threshold (90% of max) |
| tp+0x74C9 | 0xC64C9 | 0x00 | cVar8: 0 = use slew output; 1 = use raw demand |

## Editable Levers (ranked by safety)

### LEVER 1 — RECOMMENDED: tp+0x71D6 (slew step)
- **Address:** 0xC61D6
- **Current bytes:** `00 00` (u16 LE)
- **Proposed:** `0E 00` (14 decimal) — same as Civic's slew step
- **Effect:** slew output ramps at 14 units/ms after deadband trigger; dropout becomes a brief dip (recovery ~27-70ms at moderate demand) instead of a sustained zero
- **Safety:** preserves deadband entirely; only adds recovery rate. Does NOT remove fault detection.

### LEVER 2 — MORE AGGRESSIVE: tp+0x7424 (deadband threshold)
- **Address:** 0xC6424
- **Current bytes:** `33 73` (u16 LE = 29491 = 90% of max)
- **Proposed:** `00 40` (0x4000 = 16384 = 50% of max)
- **Effect:** deadband only fires when demand is truly weak (<50% of max accumulator); slew stays active during moderate-magnitude zero crossings
- **Safety tradeoff:** allows slew output when demand has some ambiguity near zero; monitor for creep at rest

### LEVER 3 — NOT RECOMMENDED: tp+0x74C9 (slew bypass)
- **Address:** 0xC64C9
- **Current:** `00` (use slew output)
- **Proposed:** `01` (bypass slew, use raw demand directly)
- **Risk:** completely removes rate-of-change protection on FOC current

## Disassembly-confirmed data flow: iVar45=0 → gp-0x6b98 (2026-05-27 addendum)

The decompiler reuses `iVar45` for two distinct physical values. The deadband path in assembly:

1. **0x434ee: `mov r0, r12`** — r12=0 (deadband zero; decompile "iVar45=0")
2. **0x43504: `st.w r12, -0x356c[gp]`** — slew state = 0 (persists; step=0 → stays 0)
3. **r8 ≈ 0** via `cmovp r0, r16, r8` at 0x434f6 (if demand component r27 > 0)
4. State machine at 0x43524–0x436d2 sees r8≈0, r11=gp-0x6b08 → triggers **gp-0x6960 = 0** (0x4362a: `st.h r0, -0x6960[gp]`) — the critical intermediary
5. gp-0x6960=0 → r6=0 (0x435b2/435f6/436b2: `ld.hu -0x6960[gp], r6`) → r26≈0 → LERP r28≈0 → r20≈0
6. r12 (REASSIGNED at 0x43af0 to feed-forward) + r20 ≈ 0 → governor clamp ≈ 0
7. r21 = clamp(≈0, ±0x2000) ≈ 0 → **0x43b52: `st.h r8, -0x6b98[gp]` and 0x43dfc: `st.h r21, -0x6b98[gp]`** → gp-0x6b98 = 0

The decompile-level `iVar45=0` correctly predicts gp-0x6b98→0, but the physical path goes through state machine intermediate **gp-0x6960** (not a direct register carry). The critical new variable: **gp-0x6960** (0xFEDF169F) = assist-level output; zeroed by state machine when demand crosses zero.

The `iVar45` in the decompile's ±0x2000 clamp region (decompile lines 1253-1255) maps to **r21**, which is a different register from the deadband r12. The decompiler variable reuse is confirmed — do not trust the decompile alone for this path; use disassembly.

## What the voter path does (NOT the primary dropout cause)

gp-0x67f5 (voter convergence) affects only the governor rate step:
- Converged: tp+0x7206 = 512 units/tick
- Non-converged: tp+0x7208 = 205 units/tick

This slows recovery rate but does NOT zero the output. Voter non-convergence causes sluggishness, not a hard cutout.

**Why:** linked to [[accord-slew-limiter]], [[accord-shaper-fun42af8]], [[accord-mixer-lkas-source-chain]]
