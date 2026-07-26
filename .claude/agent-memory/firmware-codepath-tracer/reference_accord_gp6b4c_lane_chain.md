---
name: reference-accord-gp6b4c-lane-chain
description: gp-0x6b4c (LKAS mixer output) reader map, forward chain to FOC via gp-0x6b94→gp-0x6ace→gp-0x6b98, clamp stack, and lane-family clarification for 39990-TVA-A160 (V850 code.bin)
metadata:
  type: reference
---

## gp-0x6b4c Lane Chain (TVA/Accord code.bin)

Absolute address: 0xFEDF14B4 (gp=0xFEDF8000, gp-0x6b4c).

### Readers (verified by Ghidra search_instructions)

| Address | Function | Role |
|---|---|---|
| 0x276e2/f0/708/716 | m_motor_cmd_mixer | Writer (mixer computes and stores here) |
| 0x285b4, 0x28b16, 0x28b38 | FUN_00027b0a | Sanity monitor / error reporter (FUN_0004613e code 0x3ce7), NOT motor driver |
| 0x3816c | FUN_00038148 | Motor-current demand mixer — weighted sum → gp-0x6b70 |
| 0x3aa3e | FUN_0003aa2c | Direct addend in multi-source torque aggregator → gp-0x6b94 |

### Forward chain to FOC (verified)

```
gp-0x6b4c (±0x2800 from mixer)
  ├─[direct] addend in FUN_0003aa2c (inline clamp ±0x2800)
  └─[PATH A] FUN_00038148 (gain tp+0x73aa, polarity gp-0x6752)
              → gp-0x6b70
              → FUN_00037fe6 (7-channel sum, speed-scaled gains tp+0x74ad–0x74b3)
              → gp-0x6ad6
              → FUN_0003a382 (PI loop, ref=(gp-0x4f60-gp-0x6ad6))
              → gp-0x6ad4
              → FUN_0003aa2c (addend)
  ──────────────────────────────────────────────
              → gp-0x6b94 (clamp ±0x2800)
              → FUN_0004503c: governor s_clamp(gp-0x6b94, ±(gp-0x4f64×speed>>15))
              → gp-0x6ace
              → FUN_00042af8: rate shaper (mode mix with tp+0x71d4, governor gp-0x4f64)
              → gp-0x6b98 (clamp ±0x2000 hard)
              → FOC (FUN_000370b6/0x3b8f6/0x56420/0x7c4f2) + CAN pack FUN_00059912
```

### Sibling lane family

- gp-0x6b4e (0xFEDF14B2): mixer-written; FUN_00038148 input (gain tp+0x73a8)
- gp-0x6b4c (0xFEDF14B4): this lane
- gp-0x6b4a (0xFEDF14B6): gate check in FUN_00042af8; monitor in FUN_00027b0a; also read by FUN_00043e44
- gp-0x6b3c (0xFEDF14C4): arb→telemetry only (m_steer_torque_limit_and_pack), NOT a motor lane
- gp-0x6b94 (0xFEDF146C): written by FUN_0003aa2c; the aggregated motor-torque demand; feeds FUN_0004503c (governor) and FUN_0004595a (cross-check)

### Binder stack (ordered, first applicable wins)

1. Mixer clamp ±0x2800 (m_motor_cmd_mixer 0x276f0) — gp-0x6b4c write ceiling
2. Inline clamp ±0x2800 in FUN_0003aa2c (0x3aa3e idiom `+0x2800U < 0x5001`)
3. gp-0x6b94 output clamp ±0x2800 (FUN_0003aa2c final)
4. FUN_0004503c governor: `s_clamp(gp-0x6b94, ±(gp-0x4f64×speed_scale>>15))` — adaptive/speed-scheduled, runtime-written by FUN_0007b022
5. FUN_00042af8 hard ceiling ±0x2000 on gp-0x6b98

### Key open questions

- tp+0x73aa (0xBF73AA): Q10 gain for gp-0x6b4c in FUN_00038148 — if 0, PATH A contribution is zero
- tp+0x74ab (0xBF74AB): mode byte in FUN_0003aa2c — if != 0 in mode-1, direct gp-0x6b4c addend (iVar20) is zeroed
- FUN_0007ff08 at 0x80820 reads gp-0x6b94 — decompile failed; likely telemetry, needs r2 disasm
- gp-0x4f64 runtime values (FUN_0007b022 writes at 0x7c2e2/0x7c3b4/0x7c47c) — governor curve characterization

### Lane architecture verdict

gp-0x6b4c and gp-0x6b98 are IN SERIES, not parallel. gp-0x6b4c is upstream demand; gp-0x6b98 is the downstream motor command. LKAS arb torque reaching gp-0x6b4c DOES reach the motor via gp-0x6b94 → gp-0x6ace → gp-0x6b98 → FOC. The gp-0x6b94 → gp-0x6ace path is the same path previously identified as the "primary" lane; gp-0x6b4c is a tributary feeding into it.

See also: [[reference-accord-shaper-fun42af8]], [[reference-accord-governor-gp0x184-chain]], [[reference-accord-lkas-path-wiring]]
