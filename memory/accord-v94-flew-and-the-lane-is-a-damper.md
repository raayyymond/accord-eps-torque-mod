---
name: accord-v94-flew-and-the-lane-is-a-damper
description: "V94 cut gp-0x6b26 6x against V92 on an 'it is inertia, lowering is strictly safe' premise. On-car the operator stopped driving it. The lane is a REAL 6-9 Hz damper (+137 deg vs wheel rate) — the first measured dose-response sign this lever has ever had, and it says UP, not DOWN."
metadata:
  type: project
---

# 🛑🛑★★★★★ V94 FLEW, AND IT ANSWERED THE QUESTION IT WAS BUILT TO ASK — WITH THE OPPOSITE SIGN

Flown 2026-08-12, route `7d`. **The firmware is still on the car.** The operator reported grinding and
stuttering bad enough to **shake the whole car**, judged it not safe to drive, and stopped at walking
pace. **No fault of any kind was set.**

## WHAT V94 DID [EVIDENCE — byte-diffed from the image]

Two changes on a V90 base:
1. **`0xCBE74` cut** — mode 24 ×0.50, modes 26/27 ×0.25, fallback ×0.75. Against V92's ×1.5 that is a
   **6× cut** on the engaged columns. This is the `gp-0x6b26` gain.
2. **427 telemetry packer `sar 3` → `sar 1`** — instrumentation only, rescaled so V93's lever became
   observable. **Exonerated as a cause** by an instruction-level walk plus the fact that openpilot's
   `steeringTorqueEps` dead-ends in `carstate.py`. It changes what we *see*, not what the car *does*.

## WHAT THE CAR DID [EVIDENCE]

- Motor acceleration **3–7× up above 9 Hz** vs the corpus.
- Column-torque ↔ wheel-rate coherence at **18–31 Hz the highest of any drive in the corpus**.
- Operator's own words: grinding, stuttering, whole-car vibration, unsafe.

## WHY — THE LANE IS A DAMPER, AND THE BUILD REMOVED IT

`gp-0x6b26` was believed to be an **inertia** term (`−K·α`, "nothing is dissipated"), so reducing it
was reasoned to be "strictly safe on both binding bounds." **Measured afterwards, on two independent
drives, ω-partialled against a shuffled control: the delivered lane sits at `+137°/+139°` versus
WHEEL rate at 6–9 Hz ⇒ |cos| = 0.73, contributing `+518/+565` counts of POSITIVE `Re(Z)`.** It is a
real 6–9 Hz damper. ⇒ [[accord-gp6b26-is-a-real-6to9hz-damper]]

**Removing 6/6ths of a damper made the thing the damper was damping much worse. That is exactly the
predicted behaviour of a damping term, and it is the first time this lever's `d(symptom)/dK` has ever
been observed.** Thirteen builds moved it UP; V93/V94 were the only ones that moved it DOWN.

## 🛑 THE CONSEQUENCE FOR FUTURE BUILDS

- **The direction is now MEASURED, and it is UP.** Do not propose lowering `0xCBE74` again. The
  "inertia ⇒ lower it" story is dead: [[accord-gp6b26-is-inertia-not-damping]] is **superseded** and
  `analysis-2020accord/build_v93_tva.py` / `build_v94_tva.py` encode the refuted premise.
- **But UP has already been tried thirteen times without fixing anything**, and V91/V92's ×1.5
  measured **0.99** — because `gp-0x6b26 = K·α` and α is what K damps, so in a stable closed loop the
  **product is invariant to K**. ⇒ the lever is real but the *instrument* pointed at it is blind.
  Measure the **input** (`gp-0x6c2c`) or a symptom, never the product.
- **Revert candidate on the shelf:** V92,
  `39990-TVA,A160-V92-V90BASE-CBE74.M26.M27.X1.5-CAVE.6BBE.6B62.6BDA.6A82-427.6BBE.SAR4-0x13000-0x100000.rwd`,
  SHA256 `388a1974d5702e17…`. Built, **not flashed** — awaiting the operator naming the file and bus.

## THE PROCESS FAILURE IS FILED SEPARATELY

Five compounding failures, and a 133/133-green assertion suite that encoded the wrong premise as a
PASS condition. ⇒ [[feedback-reducing-a-gain-is-not-a-safety-class]]

Links: [[accord-gp6b26-is-a-real-6to9hz-damper]] · [[feedback-reducing-a-gain-is-not-a-safety-class]] ·
[[accord-cbe74-dose-measured-inert-wrong-mode-record]] · [[accord-gp6c2c-is-motor-rate-derivative]] ·
[[accord-v80-damper-relay-and-grind1-inert]] ·
[[reference-accord-steeringpressed-mask-excludes-the-symptom-regime]]
