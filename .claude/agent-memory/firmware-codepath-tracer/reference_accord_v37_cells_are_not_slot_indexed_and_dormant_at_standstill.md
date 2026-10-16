---
name: reference-accord-v37-cells-not-slot-indexed
description: V37 vs stock is 42 bytes; every non-CRC cell is a direct tp load, and slot 2 vs slot 11 records read by their consumers are identical; no static path to a latched loss of assist at power-on (2026-10-05 trace)
metadata:
  type: reference
---

V37 = V31 cells + V36 debounce cells + 0xC64B8. 0xC6CD0 is NOT in the V37 diff. Full table and reader census in docs/traces/TRACE-2026-10-05-v37-slot-dependence.md.

- No V37 cell is pointer/selector indexed (raw LE scan, controls passed). `gp-0x674c` bank (FUN_0002b62c chain): sel 2 and sel 4 identical in all tables. `gp-0x674e` arb records at 0x29A78 identical for every selector, so `0xC64B8`=0xFF delivers 0 on any slot.
- Debounce SM runs only when gp-0x69aa == 0x8000 (LKAS authority full) and gp-0x67fe == 2. FUN_00036828 (DTC 0x23) dormant below 30 km/h and its 0xC602C threshold is 0. FUN_0002c478 output is identically 0 (limit table 0xC69CA..D0 all zero). FUN_0002b62c term max 139 stock / 279 V37 vs 512 clamp.
- gp-0x3514 (DTC applicability) is an operating-mode mask, not HW-ID derived. Per-DTC inhibit bitmap gp-0x1be0 setters (0x47588/0x475AC) have no callers found: open.
- Trap re-hit: ld.bu parity (opcode 0x3D = odd disp) conflated 0xC64B8 with 0xC64B9 (readers 0x4549E/0x4556E are 0xC64B9).

**How to apply:** do not re-propose "V37 is slot-dependent" without a reader that indexes a table where the two slots differ. Next discriminating step is a control image (stock + version string + valid CRCs only) or LX telemetry.
