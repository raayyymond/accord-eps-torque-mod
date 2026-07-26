---
name: reference-accord-mixer-lkas-source-chain
description: Full verified chain from variant-mode through mixer to delivered LKAS cmd; gp-0x6b2e/32/34/36 are dead sinks; tp+0x71b2=512 is the binding clamp; max gp-0x3d8c=2048
metadata:
  type: reference
---

## Accord TVA-A160 Mixer LKAS Source Chain (verified 2026-05-26)

> **✅ EMPIRICALLY CONFIRMED 2026-05-26 — V14 FLASHED + ROAD-TESTED, WORKS.** The "REQUEST-LIMITED by the tp+0x71b2/b4 clamp" verdict below is the correct model: raising the arb gain (tp+0x746c 891→1782) and those clamps (512→1024) doubled the delivered LKAS torque at the wheel. The 4762 governor and the ±0x2800/±0x2000 downstream clamps did NOT bind (all far above the request-limited LKAS magnitude ~418 stock / ~835 V14). NOTE on slot index: the authoritative [[reference-accord-lkas-delivery-and-governor]] resolved the LKAS source to distribute **idx 1 / mode-0** (gp-0x62b0→gp-0x3d88→gp-0x6b4c direct addend), correcting the "slot 0 / mode-5 / 4×512=2048" reading here — but the magnitude verdict (request-limited below the governor) holds either way, and V14 confirms it.

### gp-0x6b2e / gp-0x6b32 / gp-0x6b34 / gp-0x6b36 — DEAD SINKS
- Written by FUN_0002a93a (at 0x2b064, 0x2b054, 0x2b060, 0x2b068) and by m_steer_torque_arbitration (at 0x2a17c, 0x2a188, 0x2a19c, 0x2a1a2).
- **No reader anywhere in the binary** — exhaustive `ld.h` / `sld.h` / `ld.hu` / `ld.w` search across all 185116 instructions returned zero hits for these four offsets.
- These are telemetry/diagnostic sinks. They do NOT feed the delivery path.

### Variant-mode gp-0x674e -> Delivery Path (YES, verified)
- gp-0x674e is read directly inside `m_steer_torque_arbitration` to index LERP curve pointer arrays (decompile lines 127, 826, 832, 882: `*(gp-0x674e) * 4` as pointer index).
- The LERP curves (e.g. `g_pArbSetpointLimitCurves`) set the setpoint magnitude limit (15360 for mode 1 / A160 image).
- Influence propagates: gp-0x674e -> arb LERP limit -> gp-0x6b3c -> gp-0x62f8[0] -> gp-0x62c8[ch] -> gp-0x3d8c -> gp-0x6afe -> gp-0x6b98.

### Mixer LKAS Source Scaling (m_motor_cmd_mixer, 0x26c80)
- Source table: `gp-0x62c8` (absolute 0xFEDF1D38), base pointer loaded at 0x26cc8.
- Channel mode array: `tp+0x5124` (absolute 0xC4124), content [0,0,5,0,5,5,0,0,0,5,0].
- **Switch case 0**: `st.h r0,0x0[r28]` -> gp-0x62c8[ch] = 0 (all mode-0 channels, ch 0,1,3,6,7,8,10).
- **Switch case 5**: `st.h r10,0x0[r28]` where r10 = `ld.h @(gp-0x62f8[0])` (NOT channel-indexed; always reads slot 0) -> gp-0x62c8[ch] = gp-0x62f8[0] for ch 2,4,5,9.
- Cases 4,6,7 are dormant in this image (case 4 gain at tp+0x746a is dead; cases 6,7 write zero).
- Inner loop (0x271de-0x27304) accumulates: `r6 += gp-0x62c8[ch]` for each of 11 channels. r6 only.

### gp-0x62f8[0] Source Chain
- `m_steer_torque_limit_and_pack` (0x2b422) reads `gp-0x6b3c` (arb final cmd, absolute 0xFEDF14C4).
- Clamps it: `r12 = clamp(gp-0x6b3c, ±tp+0x71b2)`. **tp+0x71b2 = 512** (bytes [0x00,0x02] at 0x000C61B2).
- Packs r12 into struct[+4] at 0x2b52c, then calls `m_motor_cmd_distribute_clamp` at 0x2b53e.
- Distribute_clamp (0x25c32) prologue: `r14 = clamp(input[+4], ±0x2800)`; writes `gp-0x62f8[ch] = r14`.
- Net: `gp-0x62f8[0] = clamp(clamp(arb_out, ±512), ±0x2800) = clamp(arb_out, ±512)`.

### Cal constants (tp-relative, absolute addresses)
| Symbol | tp offset | Absolute | Value | Role |
|--------|-----------|----------|-------|------|
| tp+0x71b2 | 0x71b2 | 0x000C61B2 | **512 (0x0200)** | limit_and_pack clamp — binding limit on arb->mixer path |
| tp+0x71bc | 0x71bc | 0x000C61BC | 15360 (0x3C00) | arb internal clamp (±15360 on uVar13) |
| tp+0x71be | 0x71be | 0x000C61BE | 15360 (0x3C00) | arb secondary clamp |
| tp+0x73cc | 0x73cc | 0x000C63CC | 0 | arb LERP rate gain (Q10); = 0 means rate contribution is zero |
| tp+0x746c | 0x746c | 0x000C646C | 891 (0x037B) | arb final multiplier (Q15 shift >>0xf) |

### Max-Request Arithmetic (Task 3)
- Max arb output (gp-0x6b3c): up to ±15360 (before limit_and_pack).
- After limit_and_pack clamp: ±512.
- gp-0x62f8[0] = ±512.
- Mixer case-5 channels (4 channels: ch 2,4,5,9) each contribute ±512 to r6.
- **Max gp-0x3d8c = 4 × 512 = 2048**.
- Gate clamp ±0x2800 (10240): 2048 << 10240 — clamp NEVER bites.
- Shaper governor ±0x2000 (8192): input to shaper is already clamped at ±0x2800; 2048 << 8192 — never bites.
- **VERDICT: REQUEST-LIMITED** at 2048 by the tp+0x71b2=512 cal constant in limit_and_pack.
- To raise delivered torque, raise tp+0x71b2 (currently 512). The arb itself allows up to 15360.

### Execution order (call chain to delivered cmd)
```
s_lkas_process_steer_cmd  -> gp-0x69ae (LKAS setpoint, clamped ±0x4000)
m_steer_torque_arbitration [reads gp-0x69ae, gp-0x674e] -> gp-0x6b3c (arb final, ±15360)
m_steer_torque_limit_and_pack [reads gp-0x6b3c] -> clamp to ±512 -> distribute_clamp input
m_motor_cmd_distribute_clamp -> gp-0x62f8[0]=±512, gp-0x62e0[0]=±512
m_motor_cmd_mixer [case 5 channels] -> gp-0x62c8[2,4,5,9]=gp-0x62f8[0]; inner loop r6 += each
  -> gp-0x3d8c = 4×512 = 2048 max
  -> clamp ±0x2800 (no-op at 2048)
  -> gate FUN_00042ac6 -> gp-0x6afe
  -> rate shaper FUN_00042af8 -> gp-0x6b98 (delivered)
```

[[reference-accord-lkas-path-wiring]]
[[reference-accord-shaper-fun42af8]]
[[reference-accord-tva-downstream-chain]]
