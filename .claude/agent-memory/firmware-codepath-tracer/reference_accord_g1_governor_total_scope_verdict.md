---
name: reference-accord-g1-governor-total-scope-verdict
description: G1 (m_motor_torque_governor, FUN_0004503c) clamps the TOTAL aggregated command (LKAS+boost+friction+damping), verified at instruction level; no bypass exists for base-assist lanes; the "energy budget" is structurally unreachable, not a real thermal integrator.
metadata:
  type: reference
---

# G1 governor scope verdict — Accord TVA-A160

Traced 2026-07-20/21 in response to a team-lead falsification test: does G1 limit the TOTAL motor
command (LKAS + all base-assist lanes) or only LKAS? A prior analysis had CLAIMED (by structural
inference, not verified) that G1 is thermal/mechanical protection. This session settled both questions
with instruction-level evidence.

## VERDICT 1: G1 clamps the TOTAL aggregated command — [VERIFIED at instruction level]

Disassembly of `m_motor_torque_governor` (`FUN_0004503c`) at the clamp call:
```
000453e0: ld.h -0x6b94[gp],r6      ; r6 = gp-0x6b94 (aggregator's FULL summed output)
000453f0: ld.hu -0x4f64[gp],r8     ; r8 = governor cap
000453f4: mul r26,r8,r0            ; r8 = r26(Q15 voting factor, <=0x8000) * governor
000453f8: sar 0xf,r8               ; bound = (governor*factor)>>15
000453fc: subr r0,r7               ; r7 = -bound  (r8 unchanged = +bound)
000453fe: jarl 0x00049a90,lp       ; r10 = clamp(r6=gp-0x6b94, r7=-bound, r8=+bound)
```
`r6` is loaded from `gp-0x6b94` at `0x453e0` and NOT overwritten before the `jarl` at `0x453fe` — the
clamp target is unambiguously `gp-0x6b94`, confirmed at the register level (not a decompiler mislabel).

## VERDICT 2: gp-0x6b94 IS the sum of LKAS + boost + friction + damping — [VERIFIED, full decompile]

`FUN_0003aa2c` (`m_motor_torque_demand_aggregator`), normal-mode (`gp-0x67ac` suppression gate not ==1)
sum feeding `gp-0x6b94`:
```c
iVar19 = gp-0x6ade(±0x400) + gp-0x6b4c[LKAS](±0x2800) + gp-0x6ad4[PATH-A](±0x2800)
       + gp-0x6b62(±0x2000) + gp-0x6b26[FRICTION](±0x400) + gp-0x6bbe[BOOST](±0x800)
       + gp-0x6bd0[DAMPING](±0x800) + gp-0x6b86[resonance lane](±0x3000)
       + iVar21 + iVar16 [r24/r26 Sensor-B rate lanes]
gp-0x6b94 = clamp(iVar19 + FUN_00036682(), -0x2800, +0x2800)   // ±10240
```
Boost, friction, and damping are direct addends in the SAME sum as LKAS. When `gp-0x67ac==1`
(suppression gate active, trigger condition still unresolved — see
[[reference-accord-gp67ac-aggregator-lane-suppression-gate]]), the base-assist lanes are zeroed
*at the aggregator*, but this is not a bypass of G1 — it just changes what's in the sum G1 still clamps.

## VERDICT 3: no bypass exists for boost/friction/damping around G1 — [VERIFIED, exhaustive]

`search_instructions` on operand text `6bbe`/`6b26`/`6bd0`/`6b86` (10/7/11/6 raw hits, each hand-adjudicated
against branch-target hex-collision false positives — e.g. `be 0x0006bbe2` is NOT a real `-0x6bbe`
reference). Every real consumer decompiled and read:

- **Boost** `gp-0x6bbe`: producer `FUN_00034a72`; readers `FUN_0001bf88`, `FUN_00035154`,
  `FUN_00038148`(PATH-A), `FUN_0003aa2c`.
- **Friction** `gp-0x6b26`: producer `FUN_00036c12`; readers `FUN_00036d74`, `FUN_00038148`(PATH-A),
  `FUN_0003aa2c`.
- **Damping** `gp-0x6bd0`: producer `FUN_00034350`; readers `FUN_0001bf88`, `FUN_000347b8`,
  `FUN_00038148`(PATH-A), `FUN_0003aa2c`.
- **Resonance** `gp-0x6b86`: producer `FUN_000352b4`; sole reader `FUN_0003aa2c`.

`FUN_00038148` (PATH-A) is not a bypass — per [[reference-accord-gp6b4c-lane-chain]] it feeds
`gp-0x6b70`→`FUN_00037fe6`→`gp-0x6ad6`→`FUN_0003a382`→`gp-0x6ad4`→back into `FUN_0003aa2c`. Reconverges.

`FUN_0001bf88`, `FUN_00035154`, `FUN_00036d74`, `FUN_000347b8` are all the SAME idiom: read one lane,
range-check it (`FUN_000462e6` DTC-fault call on violation), write ONLY to isolated diagnostic-mirror
sibling variables (`gp-0x6bb2..6bb8`, `gp-0x6b20..6b24`, `gp-0x6bc4..6bca`) or (for `0x1bf88`) pack into
a UDS RDBI telemetry buffer via `FUN_00059912`. None write to `gp-0x6b94`/`gp-0x6ace`/`gp-0x6acc`/
`gp-0x6b98` or any other motor-command variable — dead-end monitors, same shape as `FUN_00027b0a` on
`gp-0x6b4c`.

**Consequence: G1 cannot be bypassed by base-assist lanes. Every path to the motor funnels through
`gp-0x6b94` → G1.**

## VERDICT 4: the "energy budget" is NOT a real thermal integrator — structurally unreachable

Cross-links [[reference-accord-governor-energy-budget-and-step-selector]] (§2, prior session) — this
session independently re-read the 4 key cal values from raw memory (not trusted from old notes):
`0xC509E`=**5325**, `0xC5164`=**0**, `0xC5128`=**1024**(→64.0 gain), `0xC6202`=**4762** — all match the
prior record exactly. Also freshly re-derived from `FUN_0007b022` decompile (lines ~110-120, 548-598):
`fVar64 = cal(0xC509E)/1024 = 5.2002` is used as BOTH the charge/discharge threshold AND the MIN-ceiling
on the two motor-rate LERP tables that feed one of `gp-0x4f64`'s three MIN operands — same cal, dual role.

Two independent reasons it cannot behave as a thermal integrator:
1. Ceiling cal `0xC5164=0` collapses the hysteresis band — no multi-cycle wind-up, degenerates to a
   same-cycle comparator on `fVar53 (=gp-0x6ba4/1024, delivered-torque magnitude) > fVar64`.
2. Structurally unreachable regardless of #1: `gp-0x6ba4` is upper-bounded by G1's OWN output
   (≤ governor nominal ceiling 4762 in steady state), and 4762 < 5325 — the charge condition can never
   fire. Circular: the accumulator watches the very quantity G1 already caps below its own threshold.

**Verdict: per-cycle-comparator-shaped, not thermal-integrator-shaped, and cannot activate at any
calibrated command magnitude.** Whatever protective role G1 serves, it is NOT demonstrated to be I²t/
thermal — it is better described as a motor-rate-adaptive combined-command ceiling with a driver-torque-
gated slew rate (see [[reference-accord-governor-energy-budget-and-step-selector]] §4 for the STEP
selector) and the (already root-caused, V42-fixed) state-4 ratchet riding in the same function
(see [[reference-accord-state4-governor-ratchet]]).

## VERDICT 5: cap table is a MIN-ceiling, not a multiplicative scale; doesn't bind at small amplitude

The `bound = (gp-0x4f64 × Q15_factor) >> 15` then `clamp(gp-0x6b94, -bound, +bound)` structure (Verdict 1)
is a ceiling — it only reduces the command when `|gp-0x6b94| > bound`, never rescales values already
inside it. At a ~139-count amplitude (concrete case from
[[reference-accord-governor-energy-budget-and-step-selector]] §6), even the most-reduced adaptive floor
on record (512) is ~3.7x above it; the freshly-verified ceiling (5325) and nominal (4762) are 9-34x above
it. **Does not bind at small-amplitude command content under any reading of its adaptive range.**

⚠ **Open item**: attempted to independently re-derive the exact 5-point LERP table (X=[1050,1700,2500,
3700,4100], Y=[5325,3584,2406,1587,512], as previously reported) from raw bytes at `0xC6226`/`0xC620E`
and did NOT get a clean match on a first pass — could be wrong base address, an interleaved layout, or a
different table. Doesn't change the Verdict 5 conclusion (bounded above by two independently-verified
numbers either of which alone is decisive at 139 counts), but the exact breakpoints are UNVERIFIED by me
this session — needs one more focused pass if they matter for a future build decision.

## Stage enumeration, aggregator → motor (for unambiguous naming)

| Stage | Function | Bound | Role |
|---|---|---|---|
| Pre-agg lane gates | inside `FUN_0003aa2c` | per-lane zero-gate (±0x400 to ±0x3000) | zeros an out-of-range lane before summing |
| A — Aggregator ceiling | `FUN_0003aa2c` → `gp-0x6b94` | ±0x2800 (10240) | first combined-command clamp |
| **B — G1 governor** | `FUN_0004503c` → `gp-0x6ace` | ±(gp-0x4f64×Q15≤1.0), nominal ≤4762 | **the total-command clamp this file verifies**; also driver-torque-gated slew-STEP and the state-4 ratchet |
| C — Post-governor comp-add | `FUN_000456a4` → `gp-0x6acc` | small, LERP-scheduled, additive | NOT a limiter — re-adds a small correction on top of G1's output |
| D — Shaper | `FUN_00042af8` → `gp-0x6b98` | final ±0x2000 (8192) | delivered-torque write; includes a 2nd application of the same governor cal |
| E — Downstream FOC/mixer | `FUN_0003b8f6`,`FUN_00041464`,distribute_clamp,mixer | ±8192 guards / ±20000 FOC / ±10240 etc. | distributes delivered cmd into FOC targets; wide, rarely binds first |
| F — Hard-shutdown monitors | M1 `gp-0x3564`, M2 `gp-0x3550`, `FUN_0004595a` | fault thresholds, not shaping | kill the command on divergence, don't limit it |

G1 (Stage B, nominal 4762) is tighter than the aggregator ceiling (Stage A, 10240), so **G1 is the
operative total-command limiter** whenever the summed command would otherwise exceed ~4762.

## Related
[[reference-accord-governor-energy-budget-and-step-selector]] — energy-budget/STEP-selector deep dive this file's Verdict 4 cross-checks and extends
[[reference-accord-gp4f64-three-consumers]] — the three consumers of gp-0x4f64 (this file covers Consumer 1 in depth)
[[reference-accord-governor-gp0x184-chain]] — gp-0x4f64 producer chain (branch 0/1/2, the motor-rate LERP)
[[reference-accord-gp6b4c-lane-chain]] — PATH-A reconvergence detail
[[reference-accord-shaper-fun42af8]] — Stage D detail
[[reference-accord-tva-downstream-chain]] — Stage E detail
[[reference-accord-state4-governor-ratchet]] — the ratchet defect riding in the same function, V42-fixed
