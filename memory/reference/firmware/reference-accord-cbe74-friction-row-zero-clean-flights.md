---
name: reference-accord-cbe74-friction-row-zero-clean-flights
description: "The 0xCBE74 x1.5 friction row has flown on a LIVE column (mode 24/26) exactly twice and both flights hard-faulted — zero clean flights. V73's clean flight wrote mode 10 (disengaged) only, so it tests nothing, and it also fails to exonerate 0xC407E = 850."
metadata:
  type: reference
---

**[EVIDENCE, 2026-08-10 — byte-verified by dereferencing `0xCBE74 + mode*4` on the images and reading the
Y array at `record + 8`. Not read from build scripts.]** Honda's Y row is `9ad99ae952f8`
(−9830, −5734, −1966); ×1.5 is `67c667de7bf4` (−14745, −8601, −2949).

## The flight record — the kit had this wrong in both directions

| build | ×1.5 on a **live** column (24/26)? | m24 manual | m26 engaged | `0xC407E` | on-car |
|---|---|---|---|---|---|
| stock / V70 / V71c / V72 | — | Honda | Honda | 511 | baseline |
| V73 | **NO** — mode 10 only, **DISENGAGED** | Honda | Honda | **850** | flew clean — **says nothing about this lever** |
| **V74** | **YES** (13 engaged modes) | Honda | **×1.5** | 850 | 🛑 **HARD FAULT, latched loss of assist** |
| **V75** | **YES** | Honda | **×1.5** | 850 | 🛑 **HARD FAULT, latched** |
| V76 flown = `_v76_v38base_relu_damper` | **NO** — reverted by the V38 rebase | Honda | Honda | 511 | flew route 65 clean |
| ⚠ V76 other = `_v76_gate_fb_arm5244_gateprobe` | **YES** | Honda | ×1.5 | 850 | never flew |
| V77 / V77B | **YES** | Honda | ×1.5 | 850 | **NEVER FLEW** |

⇒ **×1.5 on this car's live columns has flown exactly TWICE and BOTH hard-faulted. ZERO clean flights.**

## 🛑 The fault-attribution inversion

The standing record blames `0xC407E` = 850 (RULE 11's interlock mechanism, which is EVIDENCE and stands).
**But V73 carried 850 and flew clean** — and V73 is also the build whose friction edit was inert. The one
control that was supposed to separate the two cells separates neither. **V73→V74 is 64 differing runs
(13 friction sites + 51 others), so the friction row cannot be PINNED** — but the control meant to
exonerate it is what now implicates it.

⇒ 🛑 **STATUS: the row moves from EXONERATED to OPEN SUSPECT. No dose of it flies again until a probe
measures the lane.** The old status is superseded, not erased — see `docs/BUILD-LINEAGE.md` RULE 11.

## ⚠ RULE 10 refinement — the two faults are not in the same mode

[EVIDENCE for the bytes; BELIEF for what it implies about cause.]
- **V74 faulted in MANUAL** (LKAS disengaged, over a bump). Manual = **mode 24**, and m24's Y array is
  **byte-identical to Honda on V74** ⇒ the friction row **was not in force** in the mode that faulted.
- **V75 faulted ENGAGED** (operator: *"continuing like normal, with openpilot engaged"*) = **mode 26**,
  where V75 carried ×1.5 ⇒ **it WAS live for that one.**

⇒ **At flight level the association is 2-for-2; at MODE level it is 1-for-1.** Both belong in a flight
decision. Neither restores exoneration.

## ⚠ Two artefacts share the V76 build number

`_v76_v38base_relu_damper` (friction Honda, `0xC407E` 511 — **the flown one**) vs
`_v76_gate_fb_arm5244_gateprobe` (friction ×1.5, `0xC407E` 850 — never flew). They disagree on **both**
cells in RULE 11. 🛑 **The lineage row's BASE column is the discriminator. A GLOB IS NOT A CHECK** — any
ledger that resolves "V76" by wildcard silently answers the opposite question.

**How to apply:** before citing any friction-row result, dereference the pointer table and print the mode
number beside the address ([[reference-accord-an-address-is-not-a-mode]]), and resolve the build by its
exact artefact filename. See [[accord-friction-lane-ceiling-is-the-hard-fault]],
[[reference-accord-car-is-tvca4-mode-24-26]], [[feedback-rule7-mode-proof-or-a-bet]],
[[accord-check-build-lineage-before-proposing-lever]].
