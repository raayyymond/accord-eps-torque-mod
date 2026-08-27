---
name: accord-lkas-authority-frozen-since-v38
description: "★★★★★ The V38 LKAS-authority package is BYTE-IDENTICAL on all 53 images V38→V84 — forward gain 3564 (4.27× stock delivered), setpoint 16384, clamps 2048. ~30 flights, zero variation. The excitation variable the operator's own premise names has never been an arm."
metadata:
  node_type: memory
  type: reference
---

Established 2026-08-09 by a byte read of every plain image V38 → V84, not from build scripts.
Reader: `analysis-2020accord/studies/ledger/ledger_v38_to_v84_bytes.py`; full ledger `docs/archive/LEDGER-V38-TO-V84.md`.

## What V38 was
**V37 + 102 bytes, 12 of them CRC. Cal-only, zero code edits.** [EVIDENCE — byte diff of the two images]
- `0xC646C` 1782 → **3564** (×2)
- `0xC61B2` / `0xC61B4` 1024 → **2048** (×2) — ⚠ these are the **arbitration / LKAS output clamps**, not
  a "pre-gain deadband arm" as several build scripts and `BUILD-LINEAGE.md` still label them
- corridor `0xC674E/50`, `0xC675A/5C` ±4096 → ±5120 and boost floor `0xC6768/6A/6C` 4096 → 5120, with
  their float mirrors ±4.0 → ±5.0 (×1.25 guard walls)
- setpoint limit, **8 of 12 records** 15360 → **16384** (×1.0667)

**Multiplier:** stock delivers `15360 × 891 / 32768` = **417.6**; V37 = 835.3 (2.00×);
**V38 = 1782.0 = 4.267× stock**, against a clamp knee at 4.904×. **V38 itself delivered ×2.133 and
100% of today's 4.00× gain / 4.27× delivered.**

## 🛑 The finding
> **Forward gain resolved through the reader's own displacement at `0x2A1F0` = 3564 on ALL 53 images
> V38…V84. Setpoint = 16384 on all 53. Clamps = 2048 on all 53. Corridor, boost floor and float mirrors
> byte-identical to V38 on all 53.**

**No build since V38 has ever flown — or even been built — with LKAS authority at or near stock.**
V57 added no authority; it only changed **which cell** supplies the forward gain
(`0xC646C` shared → `0xC6CD0` private; see [[reference-accord-c646c-shared-gain-not-lkas-only]]).

⇒ The kit has varied damping, filters, rate lanes and dampers for **46 build numbers and ~30 flights**
against a **frozen 4.27× excitation**, while its own standing counter-argument — *"self-interference is
amplitude-independent; 4× buys DUTY, not amplitude"* — was **purely analytical and never checked against
a flight.**

## Mechanics of the arm, if it is ever run
`0xC6CD0` is **safe to move alone on the V81/V83a/V84 lineage**: exactly **one reader** (`0x2A1EE`), zero
writers, no float mirror, structurally engaged-only. The operator has driven 891 / 1782 / 3564 with no
reported manual-feel difference. `0xC646C` is **NOT** safe (5 remaining readers, two scaling raw driver
torque on a path to the motor). ⚠ Do not port onto a V76/V78/V79/V80 base — those read `0xC646C`
directly.

🛑 **Lowering it collides head-on with the operator's standing constraint** (*"without limiting the max
steering angle rate under strong LKAS command"*) — peak torque from a rail-pinned command falls in exact
proportion. **Disqualified as a fix; admissible only as a one-flight diagnostic.**

## ⊕ Partially pre-answered on 2026-08-09, which lowers its information value
Command magnitude vs symptom, measured across V80/V81/V83a/V84:
- **Burst DUTY rises 5–45×** across the command range (V84 17–23 Hz: 0.012 → 0.541, a 45× rise).
- **In-burst AMPLITUDE rises ≤2.3× (median 1.29×)**, and the only Theil-Sen slope whose CI excludes zero
  (V84 6–9 Hz, 0.268) **fails its own split-half floor of 0.230**.
⇒ **The standing "command buys duty, not amplitude" rule SURVIVES this corpus** [EVIDENCE]. An authority
cut would therefore be expected to reduce **duty**, not amplitude — useful, but predictable.
⚠ Confound: high command co-occurs with low speed and curves.

## Other never-delivered levers found in the same ledger
- **`gain_B` ENGAGED columns** (`0xD7A88`/`0xD7A9C`, `0xD7AC4`/`0xD7AD8`, `0xD7B00`/`0xD7B14`,
  `0xD7B3C`/`0xD7B50`) — **never written in any array, any mode, on any of 54 images.** This is exactly
  what V69/V70 were designed to do; both wrote mode 10 on a modes-24/26 car and delivered nothing.
  Its **speed axis** gives natively what a flat arm cannot (boost at creep, ≈1× at highway), and
  m24/m25 stay Honda ⇒ engaged-only by construction.
- **`0x3AB76`/`0x3AC20` `sar`** reachable set `{AB=÷2, AA=1×, A9=2×, A8=4×, A7=8×}` — only `AA` and `A9`
  ever built; **above 2× is unexplored**.
- **FactorE `X[1]` widening beyond 400** — only ever narrowed; free under both clip rules.
- **`0xC6C42`** (the r24/r26 differentiator span, D=4) — named the PHASE lever in V62's handoff, never
  built. ⚠ But D cannot buy a corner in-band (roll-off 125 Hz at D=4, 71 Hz at D=7).

## 🛑 Record defects this ledger found
1. **V84 is recorded as "BUILT, VERIFIED, UNFLASHED"** in `STATE.md` and `BUILD-LINEAGE.md`. **It flew as
   route `6d`.** Identical to the defect V83a's handoff flagged one build earlier.
2. **V42 is on record as a single-lever ratchet test; its image shows SIX functional groups**, including
   zeroing all four `gain_A` records. Every V42-derived attribution inherits that confound. ⊕ And
   **`0x454FE` cannot execute** — `gp-0x67fa == 4` fires **0/123,277** driving frames (8/92,826, all in
   Park), on stock too ⇒ **ELIMINATED, not falsified.** Whatever fixed the ratchet on V42, it was not
   the byte the kit credited.
3. **`0xC644A` on V43 is 32, not 64** — wrong in `BUILD-LINEAGE.md`, the memory file and the handoff.
   64 is V49's value.
4. **`0xC61B8` = 102** (the real pre-gain deadband) was **never rescaled** while its clamp siblings went
   ×4 across 54 images.
5. The setpoint-limit table is quoted two incompatible ways (`0xE41BC` vs `0xE51A8`); it is **12 records
   of n=9 at stride 0x28** in two blocks, `0xE41BC` is a **Y row**, not a record base, and **4 of 12
   records were left stock by V38 and are still stock on V84**.
