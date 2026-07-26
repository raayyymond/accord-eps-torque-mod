---
name: reference-accord-damping-clamp-dtc1d-trap
description: The damping output clamp bound (int table 0xD209C/0xD20A8) has a FLOAT MIRROR at 0xC6554/58/5C/60 checked every cycle by FUN_000347b8; a mismatch >5/1024 calls FUN_00016de6(0x1d) -- a NO-DEBOUNCE hard shutdown. Never edit the int clamp without a bit-exact matching float edit.
metadata:
  type: reference
---

# Damping clamp bound = a live DTC-0x1d int/float lockstep trap (DampFactors, 2026-07-21)

Safety reference for anyone editing the base-assist damping clamp. This is the real, confirmed version
of the V27 int/float divergence failure class, in this specific spot.

- `gp-0x6bd0`'s output clamp bound is a 2-point LERP on `gp-0x6ac2`: int table **`0xD209C`(m10)/`0xD20A8`(m11)**,
  X=[300,800], Y=[512,1024], fallback cal `0xC6158`=512.
- **`FUN_000347b8` (runs every cycle) re-derives that same bound INDEPENDENTLY IN FLOAT** from a
  byte-exact mirror at **`0xC6554`=300.0 / `0xC6558`=800.0 / `0xC655C`=0.5 / `0xC6560`=1.0** (in the
  `0xC6000` CAL block — a DIFFERENT CRC block from the int table). It clamps `gp-0x6bd0/1024` against the
  float bound, diffs against the actual int value, and if the difference exceeds **`5/1024`** calls
  `FUN_000462e6(0x417a,…)` → **`FUN_00016de6(0x1d, …, 1, 1)`** — a hard-shutdown DTC with **NO gate and
  NO debounce** (one true cycle = motor off).
- **RULE:** never edit the int clamp bound (`0xD209C`/`0xD20A8`) without a **bit-exact matching** edit to
  the float mirror (`0xC6554/58/5C/60`), or it trips on the next cycle. Both live in different CRC
  blocks, so both blocks' CRCs must also be refreshed.
- V47 deliberately does NOT touch the clamp bound: even aggressive Factor E damping (~213 counts) stays
  under the 512 floor, so the clamp never binds and the watchdog's float re-derivation reproduces the
  int value exactly (zero diff by construction). See [[reference-accord-damper-two-deadzones-factorC-factorE]]
  and [[project_v46_falsified_v47_dampers_only]]. `build_v47_tva.py` asserts these cells stay byte-stock.
