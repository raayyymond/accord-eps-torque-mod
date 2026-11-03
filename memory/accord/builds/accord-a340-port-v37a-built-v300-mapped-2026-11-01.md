---
name: accord-a340-port-v37a-built-v300-mapped-2026-11-01
description: 2026-11-01/02 — the 39990-TVA-A340 EPS is a DIFFERENT COMPILE (no address carries over); V37A 2x BUILT as V37A-A340 REV 4 (image 5b71a52d…) and V300 6x as V300-A340 REV 3 (image dc30a73b…), both carrying the DTC-0x49 COUNTER MASK as 4 code bytes (gate loads 0x2961C/0x2962E → 0xC6D28 = 0xFF) because 0xC6508 is ALSO the hand-override cut on A340 and must stay 112; DampAxis 13 B carried, alpha2 0xC40D4, cave link r7, Kp 7/Ki 20/G÷2
metadata:
  type: project
---
A340 stock bin sha 01a53539…; Ghidra `/A340_stock.bin`. Same bootloader/cipher/CRC layout as A160; code+cal re-laid from 0x14000.
Lane = FUN_00029230; Kp/Kd/Ki/map/fades are 36-record speed-scheduled RAM tables (FUN_0002a740); P = (E·Kp)>>3, Kp 8-bit; r6/r8 live
at the hook; 0xC6CD0 occupied (free run 0xC6D28..0xC6FEF, host 0xC6E88); 0xC6508 = DTC gate AND the hand-override demand cut.
V37A-A340 REV 4 (2026-11-02): image 5b71a52d…, rwd e7728d58…, clamps 900 (= 2× stock peak 450), 36 map records → 374, 416 B, not flown.
**DTC-0x49 MASK (2026-11-02, both builds):** V37's `gate := 0xFF` cannot be a cal edit on A340 (0xC6508 = the override cut). Instead the two
counter-gate LOADS 0x2961C/0x2962E get hw2 0x7509 → 0x7D29 (read 0xC6D28 = 0xFF, unreferenced); hand index gp-0x67f5 is u8 so counter B
gp-0x671e is 0 every tick; trip = (0xC6530+0xC6531)&0xFF = 100 → FUN_00016ed0(0x49) + STEER_STATUS 7 (gp-0x67cd), unreachable. Raising
0xC6530/31 only DELAYS (byte sum ≤ 254, counter free-runs above 50). The port's `tp_readers` over-counts byte cells by the odd parity
neighbour (use `byte_readers`). Handoff `docs/handoffs/2026-11/HANDOFF-2026-11-02-a340-dtc49-mask.md`.
V300-A340 REV 3 BUILT 2026-11-02 (image dc30a73b…, rwd 2819a6f2…, 842 B, rail 2472, DampAxis rows + alpha2 0xC40D4=14 carried, 0xC6508 stock, counter mask D6b): Kp 7 / Ki 20 / G-table ÷2 / sar 7 CAM decay / A160 output-lag pair / link r7, freeze-out r13 — spec in
docs/specs/design/a340/PORT-SPEC-A340-2026-11-01.md. Page https://claude.ai/artifact/4xPMkqRT1czKaemNg55fJw.
**Why:** the operator added the A340 bin and asked for both mods with the same functionality and safety.
**How to apply:** never carry an A160 address to A340; edit all 36 records; re-express gains on the >>3/8-bit scale; keep 0xC6508 stock and
carry the 0x2961C/0x2962E → 0xC6D28 mask in EVERY A340 build that carries the V36 debounce package (the mask is what keeps DTC 0x49 off).
Related: [[accord-v37a-built-reference-map-2x-slope-no-cap-2026-10-17]], [[accord-v300-release-built-dom-release-fork-2026-10-15]].
