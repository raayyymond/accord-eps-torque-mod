---
name: accord-v81-built-v75-minus-fault-cells
description: "V81 built and UNFLASHED — the flown V75 with 0xC407E 850->511 and the friction table back to stock; 126 bytes, and restoring them reproduces V75 bit-for-bit."
metadata: 
  node_type: memory
  type: project
  originSessionId: a1847153-0209-46d3-8a3d-e363459b6352
  modified: 2026-08-07T19:42:11.500Z
---

**Built 2026-08-07. UNFLASHED. The flash decision is the operator's and the file and bus must be named
back before anything is sent.**

**V81 = the FLOWN V75, with the friction lane returned to Honda's configuration. CAL-ONLY, NO CAVE CHANGE.**

| | value |
|---|---|
| builder | `analysis-2020accord/builds/v80_v107/build_v81_tva.py` |
| base | `_v75_CY0.566-EX1.200_magprobe_plain_image.bin` `e16ba4093205772e3a1bfb48f8790ade5c12f0e042b6608e51a48faaf1edf61c` — **the cut that FLEW route `5e`** |
| image | `_v81_C407E.511-FRICTION.STOCK_plain_image.bin` **`4ddbd0e2fca5c37873f4c1b633e88a81d4d62a3b45743ce2c13e1c7403bfd65b`** |
| rwd | `39990-TVA,A160-V81-V75BASE-C407E.511-FRICTION.STOCK-magprobe-6bd0-thermo-6ac2-0x13000-0x100000.rwd` **`fc4d4f74956c76dbda340e17ecf4c3ecbe3f86bbc47418cbc3b3185c52aea109`** (986,042 B) |

**EDIT 1** `0xC407E` **850 → 511** (`5203` → `ff01`) — restores Honda's hard-fault interlock.
**EDIT 2** the ×1.5 friction table → **stock** at all 14 sites (`0xCF6E0 0xCF6F0 0xD0A5C 0xD2A4C 0xD2A5C
0xD3A5C 0xD3A6C 0xD4A5C 0xD6A5C 0xD7A5C 0xD7A6C 0xD8A5C 0xD9A5C 0xD9A6C`), `67c667de7bf4` → `9ad99ae952f8`.

## Verified from disk by the orchestrator — all pass
- **25 differing runs / 126 bytes** vs the flown V75: 15 functional (86 B) + 10 CRC words. **0 unexpected.**
- **Value-anchored**: restoring exactly those 126 bytes reproduces the flown V75 **bit-for-bit**
  (sha back to `e16ba409…`) over all `0x100000` — a total statement, not a span check.
- **Exactly 1 flashable V81 `.rwd` and 1 V81 plain image on disk.** All 34 friction records byte-stock.
  Mode 24 (manual) identical to V75 across all six record types, resolved through the pointer arrays.
- **Unchanged from V75**: FactorC `[566,234,429,908]`, FactorE X `[12,200,2500,4000]` Y `[0,539,539,927]`
  ⇒ **k = 1.5798 identical**; `0xC63A0`=2048; `0xC62EA`=0; `0x454FE`=`0xB5`; `0x2A1F0` disp `0x7CD0`;
  `0xC6CD0`=3564; `0xC646C`=891 stock; the 68-byte cave and hook byte-identical (so V81 spends **zero
  cave risk** — code caves are this kit's only bricking class).

## Gates
**GATE 1** vacuous by construction (cal-only, no new RAM/code/cave byte); measured anyway.
**GATE 2 PASS, empirically** — V81 changes **no loop**. `k` is a frequency-independent scalar on the whole
damper path ⇒ loop gain equals V75's at every frequency; no new filter/delay/state ⇒ **phase is literally
unchanged**. The only dynamic element touched is a **saturation bound, moved DOWN**. `|gp-0x6c2c|` to
reach the clamp at creep: stock 3189 · flown V75 3539 · **V81 3189** ⇒ V81 clamps ~10% *more* often than
V75, which is harmless because at 511 the clamp sits **below** the 512 trip.

⚠ **V81 removes drag the operator may be used to** — creep effort will differ from V75's. Intended (the
V75 handoff attributes the *creep heaviness* complaint to V73/V74's friction ×1.5 plus `0xC407E` 850, and
`0xC407E` is mode-proof so it raised the drag ceiling in **manual** too), but it is a **feel change as
well as a safety change** and the operator should be told.

**Variant B** (`ACCORD_V81_FRICTION=V75`, keep ×1.5) implemented but **NOT cut** — the probe could not
discriminate: ×1.5 pins at the 511 clamp when the stock-equivalent raw ≥ 340.7 and the rung sits at 448.
Rungs at 320/352/416 (V75's `shr 0x5` + `cmp imm5` idiom, ~30 B) would settle it.

Related: [[accord-c407e-is-the-fault-interlock-c63a0-exonerated]] · [[accord-v80-damper-relay-and-grind1-inert]]
