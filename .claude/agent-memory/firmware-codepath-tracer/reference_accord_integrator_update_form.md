---
name: reference-accord-integrator-update-form
description: Exact pseudocode form of gp-0x3570 integrator update in FUN_00042af8; LAB_00043132 idle gating; V21 startup fault verdict — from Ghidra decompile 2026-05-31
metadata:
  type: reference
---

# gp-0x3570 integrator update form — Accord EPS s_motor_torque_rate_shaper

Verified from Ghidra decompile of FUN_00042af8 (54,953 chars, grep-extracted 2026-05-31). Bases tp=0xBF000, gp=0xFEDF8000.

## Exact integrator update pseudocode [V — Ghidra decompile grep]

```c
iVar22 = uVar25 * 0x8000;          // cmd << 15 (uVar25 = mode-gated LKAS command)
iVar45 = iVar27 * 0x8000;          // T1/T2 envelope << 15
iVar43 = *(int *)(gp - 0x3570);    // load old integrator state
iVar47 = iVar22 >> 2;              // cmd * 0x2000

// Branch 1 (normal, overflow-safe, cmd != envelope):
iVar45 = iVar43 + (iVar47 - (iVar45 >> 2)) * 4;
// = old_integ + (cmd - iVar27) * 0x8000

// Branch 2 (negative/T2 envelope case, using iVar38 = T2 LERP output):
iVar45 = iVar43 + (iVar47 - iVar23) * 4;
// = old_integ + (cmd - iVar38) * 0x8000

// LAB_00043266: iVar45 = 0  (fires when delta would take integ past zero in wrong direction)

// Clamp to ±cal[0x71dc] << 15:
uVar39 = *(ushort *)(tp + 0x71dc);   // 30720 stock = SM3 trip threshold
// ... saturating clamp ...
*(int *)(gp - 0x3570) = iVar43;      // store clamped integrator
uStack_f0 = iVar43 >> 0xf;           // uVar53 = integrator >> 15
uVar53 = uStack_f0;
if ((int)uStack_f0 < 0) uVar53 = -uStack_f0;  // uVar53 = |integ >> 15|
```

**Form: LITERAL `integ += (cmd - envelope) * 0x8000`**, NOT excess-over-bound.

At cmd=0: update delta = (0 - envelope)*0x8000. This is NEGATIVE (moves integrator toward negative clamp, not SM3 trip) if envelope > 0.

At cmd=0 AND envelope=0 (LAB_00043132 case = hands-off LKAS with |driver_assist|<9216): delta = 0. Integrator does not move.

## LAB_00043132 envelope gating [V]

`iVar27 = 0` fires when:
- `bVar1 || *(ushort*)(tp+0x741a) < uVar30`
- `tp+0x741a = 0xC741a = 0` → `0 < uVar30` is always true → gating happens when the T1/T2 LERP block reaches its zero-output condition (|driver_assist| < 9216 threshold).

At hands-off LKAS (gp-0x6bf0 ≈ 0), LAB_00043132 fires: `iVar43 = 0; iVar27 = 0`. BUT iVar43 is then OVERWRITTEN by `iVar43 = *(int*)(gp-0x3570)` — so only iVar27=0 (envelope=0) matters.

## V21 startup fault verdict [STRONG NO for cal-based envelope-double]

**Cal-based envelope-double on V18 (stock SM clamps 30720/16384) would NOT reproduce the V21 startup fault.**

Reason: at startup (cmd=0, driver_assist=0), the integrator update delta=0. SM3 integrator cannot wind. The startup fault is therefore NOT from SM3 integrator saturation.

**What V21 code patches did that a cal edit would not:**
- Patches 0x42DAE + 0x42DCA change gp-0x3574 stored scale from ×256 to ×512
- IIR converges to 2× target value; readback gp-0x3574>>8 = 2× envelope
- This REDUCES per-cycle wind-up (takes longer to trip SM3), opposite of causing a startup fault
- Neither r9 (0x42DAE, IIR target) nor r11 (0x42DCA, bypass store) feeds any variable except gp-0x3574

**True cause of V21 startup fault: [STRONG inference] ECU BOOT-ROM code-integrity check** (see 2026-05-31 session trace below; 2026-06-01 session exhaustively ruled out any SOFTWARE code-integrity check in the application layer — see [[accord-init-sm-fun220ba-fun1a104]]).

## 2026-05-31 — V21 idle fault trace, instruction-grounded [V]

`search_instructions "3574"` program-wide (185k instructions): gp-0x3574 accessed at EXACTLY TWO addresses — `0x42daa` (ld, shaper internal) and `0x42dcc` (st, shaper internal). **ZERO external readers outside FUN_00042af8.** Candidate 2 (external threshold compare) is ruled out.

### FUN_00043e44 architecture [V — decompile 2026-05-31]

FUN_00043e44 is a **multi-flag diagnostic observer**, NOT an envelope function. It maintains its own independent float IIR states `gp-0x3554` (upper) and `gp-0x3558` (lower), written ONLY inside FUN_00043e44 (search confirmed: 0x442e4 st + 0x442ee st; zero external readers/writers). These are completely separate from gp-0x3574.

**Float LERP1 at tp+0x75d4 (0xC65D4):** X=[0,9,10,200,210,220,230], Y=[2.0,2.0,0.5,0.5,0.5,0.5,0.5]. Same shape as integer LERP1 (Y ratio 4:1); breakpoints are 1/64-scaled version (9 = 576/64). Alpha shared from tp+0x7418=10.

**FUN_00043e44 outputs used by the shaper:**
- `gp-0x6dbc` (st at 0x44a22) = float governor-limited LKAS command → shaper 0x43b24 reads it, ×1024 → int, compares vs gp-0x6b98 (actual cmd) → **command-tracking monitor**
- `gp-0x6db0` (st at 0x449f4) = float lower envelope (from gp-0x3558 IIR) → shaper 0x43172 reads it, ×1024 → int, compares vs gp-0x6af6 (col correction) → **position-tracking monitor**
- `gp-0x6c84` (st at 0x449f0) = float col-velocity correction → shaper 0x43b64 reads it, ×32768 → int, fed into leaky-integrator gp-0x3564

**The leaky integrator at 0x43b64-0x43bf0 (gp-0x3564):** compares (float_col_velocity_correction × 32768) vs gp-0x3566 (previous-cycle uVar53/integrator magnitude). This is a **col-velocity correction vs integrator magnitude monitor**, NOT an int-vs-float envelope comparison. Its output gp-0x6908 has ZERO readers program-wide.

**The DTC 0x3f1b path:** FUN_000462e6 called from 0x44a42 when |fVar22|≥128. FUN_000462e6 → FUN_00016de6(0x1d) = CSIG broadcast only; no LKAS-enable variable written. FUN_00056518 = telemetry packer. Confirmed: 0x3f1b appears as a constant at ONLY ONE location (0x44a42); no gating code reads it.

**INT/FLOAT DIVERGENCE VERDICT [V]:** gp-0x3574 vs gp-0x3554/3558 are NEVER directly compared anywhere. The divergence from V21 (integer 2×, float 1×) is real but undetected by any LKAS gate. Int/float divergence is NOT the V21 idle fault mechanism.

**gp-0x3574 role:** Sets SM2/SM3 integrator UPPER BOUNDS only (sar8 at 0x43136 → r10=max(r23,r11) and r15 = lower bound). Does NOT control LKAS torque amplitude (that is tp+0x746c gain).

**V21 idle fault TRUE CAUSE [STRONG inference = code-integrity check]:**
- V21 patches code bytes at 0x42DAE (0xC8→0xC9) and 0x42DCA (0xC8→0xC9)
- Bootloader CRC at 0xC4FFC is recomputed and correct (build verified 49/49)
- If ECU performs a SECONDARY runtime code-section hash (different polynomial or range), it detects the patched bytes and inhibits LKAS at init
- All other paths (SM integrator, FUN_00043e44 flags, gp-0x3574 external reader) ruled out [V]
- Candidate 3 (warm-reset RAM) is irrelevant — gp-0x3574 doubling makes SM3 HARDER to trip, not easier

**RESOLUTION: Abandon V21 code-patch approach.** V19/V20 achieve equivalent SM-threshold rescaling via CAL bytes only (tp+0x71dc / tp+0x7422 in block #48), which are NOT checked by the code-section integrity checker. V20B (SM3=0xFFFF, SM2=3×) is the correct non-faulting approach.

## SM clamp values confirmed in V21 [V — read_memory 2026-05-31]

- 0xC6422 = `00 40` = 0x4000 = 16384 (SM2 arm) — STOCK, V21 unchanged
- 0xC61DC = `00 78` = 0x7800 = 30720 (SM3 trip + integrator clamp) — STOCK, V21 unchanged

## gp-0x6b08 = LKAS command storage [V — decompile]

`*(short*)(gp-0x6b08) = (short)uVar25` stores the mode-gated command before the integrator update. uVar25 = mode-gated gp-0x6acc (±0x2000/0x3000 cap per FUN_000074c4[tp+4]).

See also: [[reference-accord-override-snap-state-machines]], [[reference-accord-lerp3-gp3574-chain]]
