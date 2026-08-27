---
name: reference-honda-eps-sa-secret-per-mcu-family
description: Honda assigns SecurityAccess key constants per MCU family (SH-2A vs V850), not per chassis; iHDS .rwd ! header is family marker not secret on V850
metadata:
  type: reference
source: collaborative
---

**Honda assigns SA-key constants per MCU family, not per chassis.** Cross-family pattern observed across 13 SH-2A and 52 V850 EPS .rwds:

| MCU family | Group label | Constants | Where it lives | Source |
|---|---|---|---|---|
| SH-2A (Civic TBA/TEG/TGN, Clarity TRW, CR-V TLA/TPA, Pilot TG7, Insight TXM) | Group B | `0x0111, 0x0112, 0x1120` | hardcoded in `rwd-xray/tools/eps_tool.py` | reverse-engineered |
| V850E2/Px4 (Accord TVA, others) | Group C | `0x0211, 0x0212, 0x1220` | firmware-embedded at `0x92C0..0x92C5` in code.bin | verified via datasheet decode |

The algorithm itself is identical: `key = ((seed + k0) & 0xFFFF) ^ ((seed * k1) % k2)`. Only the constants change.

**Group A confusion (V850 .rwd `!` header):** All 52 V850 .rwd files in iHDS carry the same `!` header value `001100121020` (Group A = `0x0011, 0x0012, 0x1020`). This is a **family-identifier marker**, NOT the SA secret on V850. The V850 firmware doesn't read the `!` header during SA validation — it uses its own firmware-embedded Group C constants. iHDS likely has a per-MCU-family lookup table that picks Group C for V850 regardless of what the .rwd `!` header says.

**Implication for cross-chassis SA-key prediction:** You **cannot** predict a sibling V850 chassis's SA secret from its `!` header value. To verify another V850 chassis (T2F, T3L, TV9, etc.), decode its code.bin and read the constants at the `0x92C0..0x92C5`-equivalent location.

**Why this pattern matters:** Honda's per-MCU-family secret structure is the right level of abstraction. Within a family, the secret is invariant across all chassis variants. Between families, the secret changes (almost certainly because each family's compiler toolchain has the secret baked in at build time). This is why finding the algorithm in one SH-2A car (`rwd-xray/tools/eps_tool.py`) enabled flashing all 13 SH-2A variants without per-chassis derivation. Same will be true for V850 once tooling adapts.

**How to apply:** When approaching a new Honda EPS chassis, first determine the MCU family (SH-2A or V850 — `code.bin` size is a fast heuristic: 384 KB = SH-2A, 1 MB = V850). Look up family secret from this table. If new family encountered, expect new secret group; treat as net-new RE task.

**Audit trail:** `analysis-2020accord/SA_KEY_HUNT_REPORT.md` (SH-2A family-invariance observation), `analysis-2020accord/RWDXRAY_IHDS_SAKEY_REPORT.md` (V850 19-chassis `!` header scan), `analysis-2020accord/V850_ALGORITHM_VERIFIED.md` (Group C firmware confirmation). See also [[reference-v850-sa-algorithm-tva]].
