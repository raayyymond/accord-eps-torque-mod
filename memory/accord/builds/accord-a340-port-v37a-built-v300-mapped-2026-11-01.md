---
name: accord-a340-port-v37a-built-v300-mapped-2026-11-01
description: 2026-11-01 — the 39990-TVA-A340 EPS is a DIFFERENT COMPILE (no address carries over); V37A 2x ported and BUILT (REV 3, 0xC6508 kept stock because it is the driver-override cut on A340); V300 6x fully mapped but NOT built (cave re-assembly classifier-stopped 3x)
metadata:
  type: project
---
A340 stock bin sha 01a53539…; Ghidra `/A340_stock.bin`. Same bootloader/cipher/CRC layout as A160; code+cal re-laid from 0x14000.
Lane = FUN_00029230; Kp/Kd/Ki/map/fades are 36-record speed-scheduled RAM tables (FUN_0002a740); P = (E·Kp)>>3, Kp 8-bit; r6/r8 live
at the hook; 0xC6CD0 occupied (free run 0xC6D28..0xC6FEF, host 0xC6E88); 0xC6508 = DTC gate AND the hand-override demand cut.
V37A-A340 REV 3: image 8654c02f…, rwd cf9f4adf…, clamps 900 (= 2× stock peak 450), 36 map records → 374, 412 B, not flown.
V300-A340: Kp 7 / Ki 20 / G-table ÷2 / sar 7 CAM decay / A160 output-lag pair / link r7, freeze-out r13 — spec in
docs/specs/design/a340/PORT-SPEC-A340-2026-11-01.md. Page https://claude.ai/artifact/4xPMkqRT1czKaemNg55fJw.
**Why:** the operator added the A340 bin and asked for both mods with the same functionality and safety.
**How to apply:** never carry an A160 address to A340; edit all 36 records; re-express gains on the >>3/8-bit scale; keep 0xC6508 stock.
Related: [[accord-v37a-built-reference-map-2x-slope-no-cap-2026-10-17]], [[accord-v300-release-built-dom-release-fork-2026-10-15]].
