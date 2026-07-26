---
name: reference-accord-post-governor-comp-add
description: FUN_000456a4 (renamed m_post_governor_torque_comp_add) = LKAS delivery chain node 3/4; NOT a passthrough hop — it ADDS a speed-LERP-scheduled correction term onto the governor output gp-0x6ace, writing gp-0x6acc (the shaper input). Closes the one unmapped node in the gp-0x6b94->gp-0x6ace->gp-0x6acc->gp-0x6b98 chain.
metadata:
  type: reference
---

# m_post_governor_torque_comp_add (FUN_000456a4) — Accord TVA-A160

Verified in the open Ghidra project (code.bin, V850:LE, image base 0) on 2026-05-26.
This node was previously listed in every chain memory ([[reference-accord-gp6b4c-lane-chain]],
[[reference-accord-governor-gp0x184-chain]]) only as a **passthrough hop** `gp-0x6ace -> gp-0x6acc`
with no description. It is NOT a passthrough — it is an additive correction stage.

## Position in the LKAS delivery chain

```
... -> m_motor_torque_governor (FUN_0004503c) -> gp-0x6ace
    -> m_post_governor_torque_comp_add (FUN_000456a4) -> gp-0x6acc
    -> s_motor_torque_rate_shaper (FUN_00042af8, ld.h -0x6acc @0x431c4) -> gp-0x6b98 -> FOC
```

## What it does (disasm-verified [V])

1. Standard scheduler/dwell prologue (gp-0x257c struct +0x14 counter, gp-16000 table, FUN_0001cba6).
2. Redundancy plausibility monitor `FUN_0004613e(0x3c35, gp-0x68f6, gp-0x68f8, gp-0x68f4, gp-0x68fa)`
   on the gp-0x68f4 var group (same idiom as FUN_0004503c's FUN_0004613e(0x3702,...)).
3. Computes an additive correction TERM (index uVar6 = `gp-0x6a10` = 0xFEDF15F0):
   - LERP1 over axis `tp+0x7834`(0xC6834) / values `tp+0x7838`(0xC6838), bounds tp+0x7832 / tp+0x7836.
   - **Term engages ONLY when `LERP1 < gp-0x6ac0`** (gp-0x6ac0 = the runtime motor-electrical-rate
     index — ⚠ NOT vehicle speed, corrected 2026-07-17 via 7-hop resolver trace; same var used as the
     rate axis in m_motor_torque_demand_aggregator).
   - `term = (gp-0x6ac0 - LERP1) * tp+0x7204(Q10) >> 10`, then **MIN-clamped** by a second LERP over
     axis `tp+0x77d4`(0xC67D4) / values `tp+0x77d8`(0xC67D8).
   - `sign(term)` is taken from the sign of `gp-0x6abe` (`if (gp-0x6abe > 0) term = -term`).
   - else (LERP1 >= gp-0x6ac0): `term = 0`.
   - term is mirrored to `gp-0x6ad0` (0xFEDF1530) — telemetry/diagnostic sink.
4. **`gp-0x6acc = gp-0x6ace + term`** (st.h @0x45932), lockstep shadow gp-0x4cc8 (mismatch -> FUN_0006b9fa).
   The magic-`0x49d6b173` / `tp+0x74ba == 0xE9` branch applies a `*tp+0x7134/1000 + base` cal
   unit-conversion (variant/debug gate; same shape as the governor's tp+0x74b9 branch).

## Key addresses

| Item | Addr | Note |
|---|---|---|
| gp-0x6ace read (governor output) | ~0x458bc | additive input |
| gp-0x6acc write (= gp-0x6ace + term) | 0x45932 | -> shaper input |
| index gp-0x6a10 | 0xFEDF15F0 | LERP index — ⚠ CORRECTED 2026-07-19, see below |
| threshold gp-0x6ac0 | 0xFEDF1540 | runtime motor-electrical-rate MAGNITUDE (gate + scale); ⚠ NOT road speed (corr. 2026-07-17); universally read `ld.hu` (23/23 sites) with a dedicated signed sign-companion gp-0x6abe from the same producer FUN_00041464 — [INFERRED] it's stored non-negative, not the raw signed rate |
| sign source gp-0x6abe | 0xFEDF1542 | term polarity; written only by FUN_00041464 (same producer as gp-0x6ac0), always read `ld.h` (signed) |
| term mirror gp-0x6ad0 | 0xFEDF1530 | telemetry sink — **CONFIRMED dead-end 2026-07-19**: exactly 1 instruction touches it in the whole image (the write at 0x458c4 itself), 0 other readers/writers anywhere |
| LERP1 full table | 0xC6832/34/36 (X=3800/4000/4150), 0xC6838/3A/3C (Y=5000/3037/1000) | tp+0x7830 base; 3-POINT table, falling curve — corrects the earlier 2-cell summary |
| LERP2 full table | 0xC67D2/D4/D6 (X=3200/3800/4150), 0xC67D8/DA/DC (Y=512/1024/2560) | tp+0x77d0 base; 3-point, rising curve |
| Q10 gain | 0xC6204 = 3072 | tp+0x7204; `term_raw = (RATE-LERP1)*3072>>10 = (RATE-LERP1)*3` exactly (clean integer factor) |

## Confidence

- **[V]** Additive structure (`gp-0x6acc = gp-0x6ace + term`), the LERP-difference term math, the
  `LERP1 < gp-0x6ac0` engagement gate, and the polarity from gp-0x6abe — all verified in disasm.
- **[INFERENCE]** Semantic role = a speed-scheduled steering-return / low-speed-assist compensation
  added late, before the shaper. Structure is consistent with it (speed-gated, tapering, sign from a
  direction/rate var, additive) but the label is NOT independently confirmed. Do not assert it as fact.
  ⚠ 2026-07-19 refinement: since INDEX (gp-0x6a10) turned out to be an engage-domain tracking-error
  magnitude, not a speed/rate signal (see [[reference-accord-fun456a4-gate-no-hysteresis-and-index-identity]]),
  a better working label is "motor-rate-vs-tracking-error corrective term" — still [INFERENCE], not confirmed.
- **See [[reference-accord-fun456a4-gate-no-hysteresis-and-index-identity]] for the 2026-07-19 deep dive**:
  full LERP table values, byte-exact gate instructions, confirmed NO hysteresis/debounce on the gate,
  confirmed gp-0x6a10's real producer chain (NOT a filtered copy of gp-0x6ac0), and exhaustive
  whole-image consumer counts (zero external consumers) for every candidate cal.

## Ghidra annotations applied (2026-05-26)

Renamed FUN_000456a4 -> `m_post_governor_torque_comp_add`; plate comment + EOL comment @0x45932.
Sibling chain renames same session: FUN_0003aa2c -> m_motor_torque_demand_aggregator,
FUN_0004503c -> m_motor_torque_governor, FUN_00042af8 -> s_motor_torque_rate_shaper.

## Related

- [[reference-accord-gp6b4c-lane-chain]] — the chain this node sits in
- [[reference-accord-governor-gp0x184-chain]] — upstream node 2 (the governor)
- [[reference-accord-shaper-fun42af8]] — downstream node 4 (the shaper)
- [[reference-accord-tva-downstream-chain]] — gp-0x6b98 -> motor output
