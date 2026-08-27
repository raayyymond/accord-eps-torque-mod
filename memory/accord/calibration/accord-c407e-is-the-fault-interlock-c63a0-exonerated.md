---
name: accord-c407e-is-the-fault-interlock-c63a0-exonerated
description: "The V74/V75 hard faults trace to cal 0xC407E raised 511->850, not to 0xC63A0 — refuting the standing \"do not double 0xC63A0\" directive."
metadata: 
  node_type: memory
  type: reference
  originSessionId: a1847153-0209-46d3-8a3d-e363459b6352
  modified: 2026-08-07T19:41:42.653Z
---

**Verified in Ghidra by the orchestrator, 2026-08-07 — not relayed.**

## THE MECHANISM [EVIDENCE]
- **Monitor `FUN_00036d74`**: `fVar3 = gp-0x6b26 * 0.0009765625`; if `|fVar3| > *(float*)(tp+0x5004)` →
  `FUN_000462e6(0x39bc,…)` → `FUN_00016de6(0x1d,…)` = **DTC 0x1d, latched TOTAL LOSS OF ASSIST**.
  `0xC4004` = f32 **0.5** ⇒ trip at **512 raw counts**. Symmetric, **no debounce**, single-frame.
- **`gp-0x6b26` has EXACTLY ONE WRITER image-wide** — `st.h r6,-0x6b26[gp]` @`0x36CF0` in `FUN_00036c12`
  — and it stores a value **already clamped to ±cal `0xC407E`** (clamp arms `0x36CCC`–`0x36CE2`).
  Confirmed by Ghidra + a raw Python LE scan covering disp16, the **6-byte disp23** form, LE32 address
  literals and movhi/movea pairs: 0 hits on every alternative encoding.
- **`0xC407E`** = `tp+0x507E` (anchor: `0xBF000+0x507E` = `0xC407E`; the off-by-0x1000 trap avoided):
  **0 writers, 3 readers, all `ld.h` SIGNED, all three inside `FUN_00036c12`.** Its entire blast radius
  is one lane's clamp magnitude.
- **Margins**: stock/V38/V76/V78/V79/V80 **511 → +1, UNTRIPPABLE** · **V73/V74/V75 850 → −338,
  TRIPPABLE** · V81 **511 → +1, UNTRIPPABLE**.
⇒ **Honda ships the clamp exactly one count under its own monitor's trip. It is an intentional
interlock.** V73 raised it to 850 without knowing that; V74 and V75 then hard-faulted.
🛑 It is a **bare `tp` scalar ⇒ mode-proof, live in MANUAL too** — which is why V74 faulted disengaged.

## 🛑 `0xC63A0` IS EXONERATED — a standing directive rests on a false premise
The operator directive on record — *"do not double `0xC63A0`, that is what was causing hard faults"* —
is **refuted**. `0xC63A0` (= `tp+0x73A0`) has **exactly one reader** (`ld.hu` @`0x381AC`), **0 writers**,
0 disp23 hits. Its only reader `FUN_00038148` writes exactly two cells — `gp-0x374c` (accumulator) and
`gp-0x6b70` (output) — and **never** `gp-0x6b26`, `gp-0x6c2c` or `gp-0x6a5e`. `gp-0x6c2c`'s two writers
are both inside `FUN_00041464`. **No firmware data path from `0xC63A0` to the faulting monitor.**
A *physical* path exists (aggregator → motor → plant → rate → `gp-0x6c2c`) and is **irrelevant**, because
the clamp acts before the store — so the monitor is safe for any `gp-0x6c2c` whatsoever.
⊕ `build_v80_tva.assert_c63a0_block` still asserts 1024 with the old rationale; **that comment is
known-wrong.**

## ★ V75's FAULT WAS NOT THE DAMPER [EVIDENCE]
In the last 5 s before the trip the damper was identically **ZERO for 4.98 s** and reached only level 2
(128–288) **19 ms** before it. Car stationary → launch; column rate reversed sign twice in 150 ms
(+55, +31, −38 °/s); **peak jerk 7,154 °/s² = 4.3× that route's own p99.9** and the route maximum.
Exactly what the `0xC407E` mechanism predicts.

⚠ [BELIEF, not EVIDENCE] "`0xC407E`=850 caused *both* faults" — **the DTC number was never confirmed
on-car.** What is EVIDENCE: the mechanism exists, is single-frame, is mode-proof, and the build history
lines up exactly.

## THE FRICTION LANE
The ×1.5 friction table was introduced by **V73, not V74** (stock/V70/V71c/V72 carry Honda's row).
With `0xC407E` = 511 the lane is safe whatever the table, because the clamp is the sole path to the cell.
On V76 (stock friction + clamp 511 = Honda's configuration) the probe `|gp-0x6b26| > 448` fired
**0 / 63,477 frames**, positive control 99.926% ⇒ the lane doesn't reach 448, let alone 511.

Related: [[accord-v80-damper-relay-and-grind1-inert]] · [[accord-v81-built-v75-minus-fault-cells]] ·
[[accord-check-build-lineage-before-proposing-lever]] · [[feedback-decompile-first-then-assembly]]
