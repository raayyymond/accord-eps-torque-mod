---
name: reference-accord-gp6d78-init-flag-writers
description: Complete inventory of all gp-0x6d78 writers and State=3 transition analysis for 2020 Accord EPS; confirms no shaper dependency for any critical init bit
metadata:
  type: reference
---

## gp-0x6d78 = 0xFEDF1288 — EPS Init Status Flag Register

**Verified via Ghidra decompile of `../accord-firmware/analysis-2020accord/_v22_plain_image.bin`, 2026-05-31.**

### Architecture

- **Single write function**: `FUN_000197b8` at `0x197b8`
- **Mechanism**: `gp-0x6d78 |= (1 << param_1)` — BIT-SET ONLY, never clears via this path
- **31 call sites across 21 caller functions** (full list in xref output)

Companion functions:
- `FUN_000197d0` (0x197d0): BIT-READ → `(gp-0x6d78 >> param_1) & 1`
- `FUN_000197e0` (0x197e0): BIT-CLEAR → `DAT_fedf1289 &= 0x7f` (clears bit 15 only)
- `FUN_000197ea` (0x197ea): clears bit 0 as side-effect: `DAT_fedf1288 &= 0xfe`

### State=3 Transition (in FUN_00019888 at 0x19888)

```c
if ((FUN_000197d0(0xf) == 0) &&
    ((gp-0x6d78 & 0x2A10) == 0x2A10) &&
    (FUN_000220ba() == 1)) {
    // transition gp-0x67fa = 4 (and activate assist)
}
```

Required bits: **4 (0x0010), 9 (0x0200), 11 (0x0800), 13 (0x2000)**
Blocker: bit 15 must be CLEAR.

### Critical Bit Setters (mask 0x2A10)

| Bit | Function | Condition | Domain |
|-----|----------|-----------|--------|
| 4 (0x0010) | `FUN_0006651e` (0x6651e) | `gp-0x4e65==3`, `gp-0x4e6b==1`, motor position count >= threshold | Motor calibration/position verification |
| 9 (0x0200) | `FUN_0006e6c8` (0x6e6c8) | `gp-0x4e49==4` AND (FUN_0005aa62==1 OR timer > 0x13) | Motor init state machine (separate from 0x4e65) |
| 11 (0x0800) | `FUN_0007df80` (0x7df80) | `FUN_0005b2be(0xd)==0` (DTC table gp-0x9c0+13*0xc==0) | DTC plausibility gate — DTC slot 13 must be clear |
| 13 (0x2000) | `FUN_00021d3a` (0x21d3a), `FUN_00042692` (0x42692) | Requires bits 0 AND 3 already set; bit 13 also set via FUN_00042692 when bit 3 set | Calibration sequence progression |

### All Confirmed Bit Assignments

| Bit | Setter Function(s) |
|-----|--------------------|
| 0 | FUN_000567c0, FUN_00021f6a |
| 3 | FUN_00018f4a |
| 4 | **FUN_0006651e** ← critical |
| 5 | FUN_00018f4a |
| 6 | FUN_00018f4a |
| 7 | FUN_000567c0 |
| 8 | FUN_00018b04, FUN_0004bc90, FUN_0004bd7e, FUN_0004be92, FUN_00057cac |
| 9 | **FUN_0006e6c8** ← critical |
| 11 | **FUN_0007df80** ← critical |
| 12 | FUN_0001c78e, FUN_0001c996 |
| 13 | **FUN_00021d3a, FUN_00042692** ← critical |
| 15 | FUN_00064fb4 |
| 16 | FUN_00057bf0 |
| 17 | FUN_00057bf0 |
| 18 | FUN_0006d1ec |
| 19 | FUN_00063208 |
| dynamic | FUN_0004a36c (bit = FUN_00049eb4 result) |

### V21 Doubled Envelope Impact

V21 modifies FUN_00042af8: LERP3 scale shl 0x8 → shl 0x9 (doubles gp-0x3574).

**VERDICT: gp-0x6d78 bits 4/9/11/13 have ZERO dependency on shaper outputs, gp-0x3574, gp-0x6b98, or any LERP3/shaper chain value.** All four critical bits are set during pre-assist motor calibration and DTC checks, which occur BEFORE the shaper ever runs. V21's doubled envelope CANNOT block the State=3 transition via gp-0x6d78 stall.

The V21 startup fault must be elsewhere — code integrity check is the leading candidate per [[reference_accord_integrator_update_form]].

### Initial State

gp-0x6d78 starts at 0x0 at power-on. All bits set actively by init sequence.
