---
name: reference-accord-gp-base-fedf8000
description: "2020 Accord TVA (V850) global-pointer gp = 0xFEDF8000 — master key converting every gp-relative control var to absolute RAM (abs = 0xFEDF8000 - offset). Cross-checked twice; STILL CORRECT. ⚠ tp CORRECTED 2026-05-26: application tp(r5) = 0xBF000 (NOT 0xF8000 — that's only the bootloader value); tp+offset cal lives at 0xBF000+off (PROGRAMMED), no absent partition. Unlocks: status/mode bitfield 0xFEDF1288, mode var 0xFEDF56E0, LKAS staging 0xFEDF68CC."
metadata:
  node_type: memory
  type: reference
---

On the 2020 Accord EPS firmware (`39990-TVA-A160`, Renesas V850E2, LE, code.bin in Ghidra port 8193), the V850 global pointer **gp (r4) = `0xFEDF8000`**. Ghidra never established gp from the raw bin, so the decompiler emits every small-data access as `*(...)(unaff_gp + -offset)`. Add `0xFEDF8000` to convert to the absolute RAM address: `abs = 0xFEDF8000 - offset`.

**Derivation + cross-checks (both independent, both exact):**
1. `FUN_0001ce68` (generic CAN mailbox-RX) stages the first data byte to `gp-0x1734` and the next byte to absolute `DAT_fedf68cd` (`0xFEDF68CD`). Consecutive ⇒ `gp-0x1734 = 0xFEDF68CC` ⇒ gp = `0xFEDF8000`. And `0xFEDF68CC` is the known LKAS `STEER_TORQUE` staging slot (int16 BE bytes[0:1]) per [[reference-accord-lkas-torque-path]]. ✓
2. `FUN_00065afe` toggles absolute `DAT_fedf55d8`; that equals `gp-0x2A28` = `0xFEDF8000-0x2A28` = `0xFEDF55D8`. ✓

**Resolved control variables (gp-offset → absolute):**
- `gp-0x6d78` = `0xFEDF1288` — **master 32-bit status/mode bitfield.** `FUN_000197d0(n)` returns bit n; `FUN_000197ea` is a state-transition handler that clears bit 0. Bit 9 gates the resolver-correction branch in `FUN_00065afe`.
- `gp-0x2920` = `0xFEDF56E0` — mode variable returned by `FUN_0006d116()` (checked `== 2`).
- `gp-0x1734` = `0xFEDF68CC` — LKAS STEER_TORQUE staging (CAN 0xE4).
- `gp-0x1718`/`-0x171c` = `0xFEDF68E8`/`0xFEDF68E4` — dispatcher route index / src ptr (`FUN_0001ddd0`).

**CAVEAT — gp does not make gp-relative vars xref-able.** Ghidra leaves gp-relative accesses as register-relative, so `xrefs_list` on the absolute address only catches the *absolute-mode* accessors (e.g. `0xFEDF1288` shows just `FUN_000197ea`). The same RAM var is read both ways in different functions. To enumerate ALL writers of a gp var you must set gp register-context in Ghidra (not exposed via GhydraMCP) or read candidate functions directly. Note on `tp`-relative cal: **the application `tp(r5) = 0xBF000`, not `0xF8000`** (corrected 2026-05-26 — `0xF8000` is only the bootloader tp; `FUN_00014084` @`0x140ce` re-sets `tp=0xBF000`; `gp=0xFEDF8000` is derived in the same routine and unchanged). So `tp+0x74xx` state bytes are at **`0xC64xx`** (programmed, readable), NOT `0xFF4xx` (erased). There is **no absent `0xF8000+` partition** — arbitration conditions CAN be evaluated from code.bin. See [[reference-accord-databin-tp-base]] (corrected) and [[reference-accord-lkas-window-ceiling]].
