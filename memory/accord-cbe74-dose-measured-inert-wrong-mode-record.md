---
name: accord-cbe74-dose-measured-inert-wrong-mode-record
description: "V91+V92 flew the 0xCBE74 x1.5 dose and it is MEASURED INERT at its own single output gp-0x6b26 — two builds, two independent instruments, a working negative control. Leading explanation: the ENGAGED mode record is not 26/27."
metadata:
  type: project
---

# ★★★★★ THE `0xCBE74` ×1.5 DOSE IS INERT — measured, not inferred

**Routes 78 (V91) and 79 (V92), 2026-08-11.** Both fault-free. **The lever did nothing to the cell
it is documented to scale.**

## THE MEASUREMENT [EVIDENCE]

`0xCBE74`'s LERP has exactly **one** documented output (`build_v91_tva.py` §"THE LANE"):
`gp-0x4f50 → FUN_00041464 → gp-0x6c2c → FUN_00036c12 [the 0xCBE74 LERP] → gp-0x6b26 (±511)`
→ Path 1 aggregator (unweighted `add`) + Path 2 observer (`0xC63A6`). **There is no second
consumer**, so a null at `gp-0x6b26` is a null on the lever, full stop.

| arm | statistic | result | pre-registered expectation |
|---|---|---|---|
| **r78 ENGAGED**, cell-stratified (speed×rate) | p50 / p75 / p90 / mean | **0.988 / 1.230 / 0.941 / 0.964**, every CI containing 1.00 | **1.50**, window [1.275, 1.725] |
| **r78 MANUAL** (negative control) | p50 | **1.009 [0.982, 1.047]** | 1.00 ✅ **the control HOLDS** |
| **three-way duty** `P(\|gp-0x6b26\| ≥ 15)` | r77 / r78 / r79 | **0.167 / 0.161 / 0.165** | needed **0.204** (×1.22 lift) |

Two **independent instruments** agree: 427 continuous (`\|b26\|×5>>3`, r77/r78) and V92's **byte7 b7**
rung (`\|b26\| ≥ 15`, r79). Tools: `rlog-tools/v91_v92_dose_in_force.py`, `v91_v92_dose_threeway.py`.

## 🛑 WHY THIS IS A NULL ON THE **LEVER**, NOT ON THE FLASH

**V92's identity is proven single-frame and parameter-free**: `0x14A byte7[7:6] ≠ 0` on 16,236 of
87,317 frames — **impossible on every build V53–V91** (`gp-0x1511`'s only two writers mask bits 7:6
off), and confirmed by r78 reading **0.0000 %** on that same bit as a positive control. And the V92
image on disk (`c8e89fe35ebc445e…`) was **re-read this session** and carries
`0xD7A5C`/`0xD7A6C` = `(-14745, -8601, -2949)`. ⇒ **the dose was on the car and did nothing.**

## THE LEADING EXPLANATION — the engaged mode record is not 26/27 [BELIEF]

**The Y row is nonzero at all three knots**, so there is **no speed at which ×1.5 is a no-op**
⇒ an inert result means **the record being read is not the record we wrote.** [EVIDENCE for the
inference; BELIEF for which record it is.]

🛑 **And this was never testable against stock**: `[[accord-stock-mode24-equals-mode26-damper-is-ours]]`
records that stock ships **mode 24 ≡ mode 26 byte-identical**, so no stock observation can
distinguish "engaged reads 26" from "engaged reads 24". **V91/V92 are the first on-car test of the
kit's mode-26 assumption, and it FAILED.** Both arms reading 1.00 is exactly what "the car reads
mode 24 in both states" predicts. This is `BUILD-LINEAGE` **RULE 7** (*mode-proof or it is a bet*)
collecting its debt. See `[[reference-accord-car-is-tvca4-mode-24-26]]`.

## CONSEQUENCES

- 🛑 **Every band result on routes 78/79 is uninterpretable as a test of the damping hypothesis** —
  the §10.1 pre-registration says so in terms. Do not report the null as a falsification.
- ⇒ **routes 77, 78, 79 are three drives on the SAME FUNCTIONAL CAR** — the kit's largest
  same-firmware placebo set. See `[[accord-three-route-placebo-floor]]`.
- ⚠ **The V74/V75 fault question is NOT answered.** Both flights were fault-free, but with the dose
  not reaching the lane, a fault-free result is unsurprising and does **not** clear the dose.
- **Next step**: prove the mode index in Ghidra *before* re-dosing. Writing mode 24 would also dose
  MANUAL — which destroys the negative control and changes manual feel. State that cost up front.
