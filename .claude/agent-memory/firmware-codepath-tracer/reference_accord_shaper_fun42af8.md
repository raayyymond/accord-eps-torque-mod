---
name: reference-accord-shaper-fun42af8
description: Verified production chain and clamp stack for FUN_00042af8 (Accord TVA-A160 V850 shaper) — how gp-0x6b98 (LKAS torque demand) is produced and every limit applied to it.
metadata:
  type: reference
---

# FUN_00042af8 — Accord TVA-A160 LKAS torque demand shaper
**Verified via Ghidra decompile, 2026-05-26. Program: code.bin, V850:LE:32, 39990-TVA-A160.**

## Key addresses
| Symbol | gp offset | Physical address | Role |
|--------|-----------|-----------------|------|
| gp-0x6acc | -0x6acc | 0xFEDF1534 | PRIMARY COMMAND INPUT to shaper — NOT gp-0x6b3c, NOT gp-0x69ae |
| gp-0x6b98 | -0x6b98 | 0xFEDF1468 | SHAPER OUTPUT (LKAS torque demand); written at decompile lines 1264 and 1403 |
| gp-0x6b3c | -0x6b3c | 0xFEDF14C4 | Arb output — NOT directly read by FUN_00042af8 |
| gp-0x69ae | -0x69ae | 0xFEDF1652 | LKAS setpoint — NOT directly read by FUN_00042af8 |
| gp-0x4f64 | -0x4f64 | 0xFEDF309C | Governor runtime value (written by FUN_0007b022 per MEMORY) |
| gp-0x6afe | -0x6afe | 0xFEDF1502 | Feed-forward / error correction addend |
| gp-0x6b04 | -0x6b04 | 0xFEDF14FC | Parallel internal demand path (dual-path lockstep mirror) |

## Input signal: gp-0x6acc
Written externally (likely by FUN_00028ea6 arb or a post-arb buffering step). Not written inside FUN_00042af8.

Mode-gated source selection (lines 633-645):
- mode==1 (cal): `uVar25 = tp+0x71d4` — a cal constant; returns 0xFFFF = -1 with absent cal partition
- mode==2 (offset): `uVar25 = clamp(tp+0x71d4 + gp-0x6acc, ±0x3000)` — cal absent means ±0x3000 clamp of (gp-0x6acc - 1)
- default (mode==0): `uVar25 = gp-0x6acc * (gp-0x6acc + 0x2000 < 0x4001)` — zero-gate for values > 0x2000

**⚠ CORRECTED 2026-07-19 — this is a ONE-SIDED zero-gate, NOT a symmetric ±8192 window.** An
earlier restatement of this finding (used as a golden-model input for a "sanitize-to-zero cliff"
investigation) mis-read it as a symmetric range gate ("out of ±8192 window → zero"). **That framing
was wrong.** Re-verified independently this session directly against `code.bin` disasm at the mode
selector's exact address (`0xC64C8` = tp+0x74c8 read `0x00` on this build → the mode==0 default path
below is confirmed LIVE, not hypothetical):

```
000431c4: 24 4f 34 95   ld.h -0x6acc,gp,r9        ; r9 = gp-0x6acc, SIGNED load
000431d0: 09 36 00 20   addi 0x2000,r9,r6          ; r6 = r9 + 8192
000431d4: 06 06 ff bf   addi -0x4001,r6,r0          ; flags = r6 - 16385 (discarded)
000431d8: e0 4f 02 5b   cmovc 0x0,r9,r11            ; r11 = CY ? 0 : r9
00043206: 64 5f f8 94   st.h r11,-0x6b08,gp        ; gp-0x6b08 = r11
```
The condition `gp-0x6acc + 8192 < 16385` reduces to a plain linear inequality `gp-0x6acc ≤ 8192` with
**no absolute value** — true for the entire negative range as well as 0..+8192, false only for
+8193..+32767. **gp-0x6acc is passed through unchanged for ANY negative value, no matter how large in
magnitude; only values above +8192 are zeroed.** Negative values always pass — that part of the
original note was right; "this is a ONE-SIDED zero-out, not a symmetric clamp" was already correctly
flagged in the original text below, but a downstream summary of this file dropped that qualifier and
treated it as symmetric. **If you are about to reason about a "cliff" or "chatter" risk on gp-0x6acc,
the risk is real only on the POSITIVE side of the command — a large negative excursion never hits
this gate.** See [[reference-accord-fun456a4-gate-no-hysteresis-and-index-identity]] for the
2026-07-19 addendum that used this corrected reading to show the cliff is not reachable at the
verified command maximum (7322 < 8192).

## Production formula for gp-0x6b98
At a high level (after tracing through the full function):

1. `uVar25` = gated gp-0x6acc (see mode selection above, default mode produces the gated value)
2. Multi-stage rate-shaping LERP on `uVar25` → `sStack_d6` (via rate-limited ramp with speed-dependent LERP ratio `uVar30` and velocity-gain `uVar33`)
3. `iVar45 = ((sStack_d6 * uVar30 / 32768) + (uVar25 * (1 - uVar30/32768))) * uVar33 / 32768` — Q15 LERP blending shaped demand with setpoint, scaled by speed-dependent gain
4. Feed-forward add: `iVar45 += gp-0x6afe * (gp-0x6afe within ±0x27FF)` — error correction term gated by its own range check
5. Governor stage: `iVar18 = gp-0x4f64 * (gp-0x4f64 < 0x2801)` — unsigned governor cap, zeroed if >= 0x2801; then symmetric ±governor clamp applied
6. Hard clamp ±0x2000: `iVar45 = clamp(iVar18, -0x2000, +0x2000)`
7. `uVar15 = (undefined2)iVar45` → written to gp-0x6b98 (and dual-path mirror gp-0x4ce2) with lockstep consistency check via FUN_0006b9fa

## Clamp stack (ordered, with editability tags)

| # | Clamp | Type | Value | Effect |
|---|-------|------|-------|--------|
| 1 | Input zero-gate | CODE IMMEDIATE | 0x2000 (gp-0x6acc+0x2000 < 0x4001) — lines 634-635 | Zeros the command if gp-0x6acc > 8192; NOT symmetric ±clamp |
| 2 | Mode-2 sum clamp | CODE IMMEDIATE | ±0x3000 — lines 639-642 | Only active in mode==2; cal absent means tp+0x71d4 = -1 |
| 3 | Rate-shape clamp via tp+0x71d4 | tp+ CAL | 0xFFFF = -1 signed | Cal absent → -1 as target: LERP LERP effectively passes gp-0x6acc; produces near-no-op for normal mode |
| 4 | Rate-shape inner via tp+0x71dc | tp+ CAL | 0xFFFF | Speed-gain numerator; all cal absent → 0xFFFF applied in Q15 multiplies |
| 5 | Feed-forward gate | CODE IMMEDIATE | ±0x27FF (gp-0x6afe+0x2800 < 0x5001) — lines 1241-1242 | Zeros gp-0x6afe if outside ±0x27FF |
| 6 | Governor clamp | gp- RUNTIME | ±gp-0x4f64 (max 0x2800 when gp-0x4f64 < 0x2801; else 0) — lines 1243-1251 | Written by FUN_0007b022; symmetric ±governor |
| 7 | **Final hard clamp** | **CODE IMMEDIATE** | **±0x2000 (8192) — lines 1253-1255** | **THE BINDING CEILING at full command. Instruction address: ~0x43B40-0x43B4E range within FUN_00042af8.** |

## What caps gp-0x6b98 at 8192?
**Clamp #7 — code immediate ±0x2000 at lines 1253-1255 of the decompile.** This is in CODE, editable in the firmware image. The assembly lies within the function body 0x42af8–0x43e43; the specific write to gp-0x6b98 was disassembly-confirmed at 0x43b52 and 0x43dfc.

The governor (gp-0x4f64) can only reduce the ceiling below 0x2000, never raise it above. The governor is itself capped at 0x2800 by its own code gate (gp-0x4f64 >= 0x2801 → governor = 0), but 0x2800 > 0x2000, so the governor is wider than the final clamp unless gp-0x4f64 < 0x2000.

**FUN_0007b022** manages gp-0x4f64 as a runtime governor. Its value is a gp- RUNTIME value (class C) — cannot be edited statically.

## tp+ reads in this function (all return 0xFFFF with absent cal)
- `tp+0x71d4` (mode-1 setpoint target) → 0xFFFF = -1 signed
- `tp+0x71dc` (rate-shape velocity gain numerator) → 0xFFFF
- `tp+0x741a` (LERP velocity threshold lo) → 0xFFFF
- `tp+0x741c` (LERP velocity threshold hi) → 0xFFFF
- `tp+0x741e`, `tp+0x74ca`, `tp+0x74cb`, `tp+0x74c4[+4]`, etc. — all 0xFFFF
- Practical effect: all tp+ cal reads are no-ops or extreme-value defaults. The function operates on its code-immediate constants and gp- runtime values exclusively.

## Related memories
[[reference-accord-lkas-window-ceiling]] — Era 11 context: arb output (gp-0x6b3c) is UPSTREAM of shaper; shaper input is gp-0x6acc (an intermediate buffer written by arb or post-arb stage).
[[project-accord-torque-mod-v0]] — current build state for Accord TVA.
