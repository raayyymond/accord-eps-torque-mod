---
name: accord-cbe74-dose-measured-inert-wrong-mode-record
description: "V91+V92 flew the x1.5 dose and it measured INERT at its own single output gp-0x6b26 — ONE identity-proven leg (V92/route 79), not two. 🛑 The 'wrong ENGAGED mode record' explanation is REFUTED (V73 probed the same index byte over 104,061 frames). 🛑 The null is UNEXPLAINED — and 2026-08-12 it is also a CANDIDATE T10 (instrument invariant to the lever): V94 cut the same cell 6x and the operator ABORTED, which proves the cell reaches the car. 🛑 ADDRESS CORRECTION: the dosed bytes are 0xD7A5C/0xD7A6C; 0xCBE74 is a POINTER PAIR, byte-identical stock through V97."
metadata:
  type: project
---

# ★★★★★ THE ×1.5 DOSE IS INERT — measured, not inferred

> 🛑 **ADDRESS CORRECTION, 2026-08-12 (orchestrator-verified from the images).** This lever is named
> `0xCBE74` throughout the kit. **That address is a POINTER PAIR and is byte-identical in every image
> from stock through V97** (`d8e60c00e8e60c00` in stock/V90/V91/V92/V93/V94/V96/V97). The **dosed
> bytes are `0xD7A5C` / `0xD7A6C`** (+ trailer `0xD7FFC`):
> `stock 9ad9… → V91/V92 67c6… (×1.5) → V93/V94 66f6… (the cut) → V96/V97 67c6…`
> ⇒ **V96's "REVERT.CBE74" reverted to V91/V92's ×1.5 DOSE, not to stock — and V97 carries it.**
> No conclusion below changes: the analyses keyed off the right *bytes* (see the V92 identity
> paragraph, which already cites `0xD7A5C`/`0xD7A6C`), only the *label* was wrong.

> 🛑 **CLASS UPDATE, 2026-08-12.** This null is now a **candidate T10 — "the instrument is invariant
> to the lever"** (`[[accord-dead-lever-taxonomy-and-liveness-checklist]]`). `y = K·α` where α is
> what K damps ⇒ in a stable closed loop the product is invariant to K. **V94 cut the same cell 6×
> and the operator ABORTED the drive — which PROVES the cell reaches the car.** ⇒ this was never a
> dead lever; it was an unmeasurable one. Do not file it FALSIFIED.

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

## 🛑🛑 THE "WRONG MODE RECORD" EXPLANATION IS **REFUTED**. Retracted 2026-08-11, same session.

An earlier version of this memory (and a V93 proposal built on it) named *"the car reads mode 24 in
both states"* as the leading explanation. **That is refuted by evidence the kit already had, which
was not checked before proposing it.**

`[[reference-accord-car-is-tvca4-mode-24-26]]`: **V73 probed `gp+0x63fd` — the SAME byte
`FUN_00036c12` uses as its index** (`0x36C4A ld.bu 0x63fd[gp],r15`) — over **104,061 frames**. It
read **8 manual / 10 engaged, 18 transitions, all on engagement edges, 99.09 % lag-matched.**
The mode index **demonstrably changes with engagement**; it does not sit at 24.

**The Y row is nonzero at all three knots**, so there is no speed at which ×1.5 is a no-op. That
inference still stands — *something* bypassed the edit — but the mode is no longer the candidate.

## 🛑 AND NEITHER BYPASS BRANCH EXPLAINS IT EITHER — so the null is UNEXPLAINED

`FUN_00036c12` has exactly three gain sources. Both non-LERP branches were traced this session and
**both should pass in normal driving**:
- **`gp-0x67f4 != 1`** → flat `cal(0xC640C)`. Traced to `FUN_00041eec`: it is the **vehicle-speed
  VALID/SETTLED flag** — set to 1 once any wheel-speed source is valid and the voted speed settles
  (Δ < 0x41 ≈ 1 km/h), cleared **only** when *all* sources go invalid. **In normal driving it is 1.**
- **`gp-0x671a >= cal(0xC64FD) = 5`** → flat `cal(0xC640A)`. `gp-0x671a` is the oscillation
  detector's output, **measured never non-zero** on V64/V68 (inherited, not re-measured here).

⇒ all three gates pass, the LERP branch should be taken, mode 26 should be live, **and the ×1.5
should have appeared.** It did not. **The null has no surviving mechanism.**

## 🛑 THE EVIDENCE IS ALSO WEAKER THAN FIRST REPORTED — one leg, not two

The first write-up claimed *"two independent instruments agree."* **It does not follow.**
**V91 is telemetry-identical to V90** — no cave bit separates them — so **route 78 cannot prove V91
was ever on the car.** Asked directly, the operator could not confirm the flash. ⇒ route 78
corroborates only *if* V91 was flashed, and the conclusion rests on **V92's `byte7 b7` duty test
alone** (route 79, identity-proven single-frame): **0.1646 observed vs 0.1671 undosed against a
needed 0.2036** — a 1-bit test, lower-powered than the continuous one.

**Carry this as: the dose probably did not land, on ONE identity-proven leg, with no mechanism to
explain why.** Not as a settled fact.
⊕ **V94 fixes both halves**: a ×0.25 engaged dose is a **4× change** in `|gp-0x6b26|`, which is
unmissable *and* doubles as the identity signature V91 lacked.

## CONSEQUENCES

- 🛑 **Every band result on routes 78/79 is uninterpretable as a test of the damping hypothesis** —
  the §10.1 pre-registration says so in terms. Do not report the null as a falsification.
- ⇒ **routes 77, 78, 79 are three drives on the SAME FUNCTIONAL CAR** — the kit's largest
  same-firmware placebo set. See `[[accord-three-route-placebo-floor]]`.
- ⚠ **The V74/V75 fault question is NOT answered.** Both flights were fault-free, but with the dose
  not reaching the lane, a fault-free result is unsurprising and does **not** clear the dose.
- **Next step**: prove the mode index in Ghidra *before* re-dosing. Writing mode 24 would also dose
  MANUAL — which destroys the negative control and changes manual feel. State that cost up front.
