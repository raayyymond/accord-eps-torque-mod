---
name: reference_accord_c63ac_is_the_pure_lead_pole_lever
description: 0xC63AC (Path-2 accumulator IIR, stock 102, VIRGIN on all 89 images) is the kit's only identified PURE LEAD / LAG-REMOVAL lever -- DC gain is exactly 1.000000 at every value, so it is a pole not a gain, and it escapes the closed-loop sign problem that disqualifies the six FUN_00038148 lane weights. 102->205 recovers +12.6 deg phase margin at 7.79 Hz AND returns 2.13x faster. Costs 1.38x transmission at 21 Hz, which collides with V62's measured 18-22 Hz fix. Also: 0xC644A is already at its maximum (stock 1024 = pass-through, zero lag) so there is no raise available.
metadata:
  type: reference
---

# `0xC63AC` — the only PURE-LEAD lever found — 2026-08-12, `fw-levers`

Context: the operator's crux has **two clauses that pull opposite ways** — the engaged return must be
(1) as SMOOTH as manual (more damping helps) *and* (2) FASTER than manual (more damping hurts). A **pure
dissipation** lever buys 1 and costs 2. Only a **pure lag-removal** lever buys both. This is the ranking
axis to use on this crux; damping-only levers are likely to fail on the operator's own scale even when
the 6–9 Hz instrument improves.

## The arithmetic (EVIDENCE — `FUN_00038148`, `_v97/ledger_v97_poles.py`)

```
gp-0x374c += ((target - gp-0x374c) * A) >> 10        # A = 0xC63AC = 102 stock
```

🛑 **DC gain = `a/(1-(1-a))` = 1.000000 for ANY `a`** — verified numerically at A = 102/205/410.
**It is a POLE, not a GAIN.** It cannot change how hard the car pulls, only *when*. **This is why it
escapes the sign problem**: the six lane weights change the *magnitude* of a contribution whose sign
through the loop depends on the unmeasured `L` and `f'`; a pole move at fixed DC gain removes lag
monotonically regardless of loop-gain sign.

| A | α | −3 dB corner | phase @6/7.79/9 Hz | phase @0.5/1/2 Hz | step→90 % |
|---|---|---|---|---|---|
| **102 (stock, VIRGIN)** | 0.0996 | 16.71 Hz | **−18.7/−23.6/−26.7°** | −1.6/−3.3/−6.5° | 21.9 ms |
| 154 | 0.1504 | 26.00 Hz | −12.0/−15.4/−17.6° | −1.0/−2.0/−4.1° | 14.1 ms |
| **205** | 0.2002 | 35.70 Hz | **−8.5/−11.0/−12.6°** | −0.7/−1.4/−2.9° | **10.3 ms (2.13×)** |
| 256 | 0.2500 | 46.11 Hz | −6.4/−8.3/−9.6° | −0.5/−1.1/−2.2° | 8.0 ms |

**102 → 205 recovers +12.6° phase margin at 7.79 Hz AND returns 2.13× faster — both clauses.**

## ⊕ Asymmetric integer dead zone — a nonlinearity linear analysis misses

`>>` on V850 is an **arithmetic** shift (floors toward −∞). So a **positive** error below
`ceil(1024/A)` floors to **0 and the accumulator STALLS**, while a **negative** error of the same size
still creeps at −1. The filter is **asymmetric at small error — a rectifying stiction.** Stock stalls up
to **11 counts**; A=205 → 5; A=410 → 3. Plausibly relevant to a micro-regime ratchet, and raising A
shrinks it. Worth checking whenever an `x += (err * K) >> N` accumulator appears anywhere in this image.

## Blast radius — the smallest of any candidate. 1 reader, 0 writers, TWO methods.

`search_instructions(operand="73ac", program="code.bin")` → **exactly one** real hit:
`0x00038202  ld.hu 0x73ac, tp, r13` in `FUN_00038148`. Other five hits excluded as `bne`/`jr`
branch-target coincidences. Whole-image raw LE scan (both parities) → 5 hits: that reader; two inside a
**stride-4 data table** at `0xBD682`/`0xBE9C2` (`40 3f d6 9e | 40 3f ac 73 | 40 3f 64 48`, `3f40` a
constant field); two mid-instruction byte coincidences at `0x64642`/`0x6E73E` in functions Ghidra HAS
analysed and where the operand search returns nothing. Touches Path 2's accumulator only — not Path 1,
not the PID, not the aggregator.

## 🛑 THE COST — not a free lever, and it collides with a MEASURED win

Raising α widens the passband, so Path 2 transmits more HF. A=205 vs stock:
**1.08× @7.79 Hz · 1.38× @21 Hz · 1.53× @28 Hz · 1.75× @42 Hz.**
⚠ **V62 fixed the grinding by taking 18–22 Hz down 8–42× — the kit's first measured fix.** A=205 puts
1.38× back at 21 Hz. **Raising `0xC63AC` may partially undo V62.** Price this before flying.

## "Must-not-move list" is weaker than it sounds
`build_v83a_tva.py:159` freezes `0xC63AC`, but the bound it protects is V83a's ≤1.32× max-effect estimate
for a **different cell (`0xC63A0`)**. It is an **analysis-comparability** freeze, **not a stability
veto**. Do not read it as a safety finding.

## Sibling poles, priced the same way
- **`0xC644A` — NON-CANDIDATE, no headroom.** Stock **1024 = α=1.000 = a pass-through**, pole at z=0,
  **zero lag; already at maximum.** Lineage from images: **V43 → 32**, V44 revert, **V49 → 64**, V49p
  revert (2 of 89). ⚠ Corrects the common "V43 was 1024→64" — that was V49. Both *lowered* it, adding
  **55.6°** and **35.8°** of lag at 7.79 Hz — the wrong way. V43's null therefore says something about
  the D-path's **authority**, not only its band.
- **`0xC6AE6` (Kd) — VIRGIN, conflicted, and NOT a scalar**: `build_v43_tva.py:240` documents it as a
  4-entry Y row `(2048,2048,2048,2048)` — flat, so it acts scalar, but a change is four cells. D pumps at
  7.79 Hz yet damps 16–35 Hz ⇒ the same trade as `0xC63AC` in the opposite direction. Price both against
  ONE shared phase budget.

## Related
[[reference_accord_fun38148_lane_weight_map_and_c63a0_reconciliation]] — the six GAIN-class weights this
pole lever is the alternative to; all disqualified on unknown sign.
[[accord-v62-fixed-the-grinding]] — the measured 18–22 Hz win this lever's HF cost collides with.
