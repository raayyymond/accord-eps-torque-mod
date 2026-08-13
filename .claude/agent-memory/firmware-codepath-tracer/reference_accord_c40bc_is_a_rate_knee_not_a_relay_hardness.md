---
name: reference_accord_c40bc_is_a_rate_knee_not_a_relay_hardness
description: 0xC40BC is the DIVISOR of a saturating ramp on MOTOR RATE (ramp = clamp(rate*12/norm, -1, +1)) and does NOT scale the friction output magnitude -- so V85's 600->6000 did not soften a relay, it moved the saturation KNEE from 10.6 deg/s (inside the micro regime) to 106 deg/s (far above it), removing modelled friction from the symptom band entirely; that dissolves the apparent conflict between the V85 flight and cancellation reasoning. Also: it cannot re-arm K0 (0xC4080=0, ramp*0=0), it has a HARD FLOOR of 1 (unsigned divisor, 0 gives NaN), and FUN_0003b8f6 has NO engagement gate.
metadata:
  type: reference
---

# `0xC40BC` is a RATE KNEE, not a relay hardness — 2026-08-13, `tracer-arms`

Dispatched to adjudicate a stated conflict between the V85 flight measurement and desk
cancellation-reasoning. **The conflict dissolves — it was a mis-framing, not a contradiction.**
Write-up: `docs/TRACE-2026-08-13-v99-arm-levers.md` §8.

## The arithmetic, assembly-exact [EVIDENCE — `get_assembly_context` @ `0x3bab4`]
```
0x3bab0  mul 0xc,r6,r0         ; x = polarity * gp-0x6abc * 12
0x3bab4  ld.hu 0x50bc[tp],r16  ; norm = 0xC40BC     (tp+0x50BC = 0xC40BC, NOT 0xC50BC)
0x3babc  cvtf.uws r16,r9       ; read UNSIGNED
0x3bad0  divf.s r14,r12,r14    ; ramp = x / norm    <-- REAL FP DIVISION (the two *0.5 cancel)
0x3bad8..0x3bae4              ; ramp = clamp(ramp, -1.0, +1.0)
0x3bb0a  mulf.s r9,r14,r7      ; ramp * K0/1024        K0 = 0xC4080 = 0
0x3bb0e  mulf.s r12,r9,r14     ; ramp * K1             K1 = 0xC40D2 = 204 (V89)
0x3bb16  maddf.s r12,r10,r7,r14; friction = ramp*K1/1024*|model| + ramp*K0/1024
```
**It normalises a saturating ramp on MOTOR RATE. It does NOT scale output magnitude** — the peak is
`K1·|model| + K0`, independent of `0xC40BC`. It sets **saturation duty and small-rate magnitude only.**

## 🛑 THE RESOLUTION — V85 moved the KNEE out of the symptom band
Knee = `norm/12` counts = `(norm/12)/4.7121` column °/s (`gp-0x6abc` = 4.7121 ct per °/s):

| `0xC40BC` | knee | vs micro regime 1–13 °/s | small-signal gain (∝1/norm) |
|---|---|---|---|
| 150 | 2.65 °/s | inside | 4.0× |
| **300** | **5.31 °/s** | **inside, mid-band** | **2.0×** |
| **600 (stock, on car)** | 10.61 °/s | inside, top edge | 1.0× |
| **6000 (V85, flew)** | **106.1 °/s** | **far above ⇒ regime purely VISCOUS** | 0.1× |

**V85 neither hardened nor softened a relay — it removed modelled friction from the symptom regime**
(10× less there, viscous instead of Coulomb). Per the kit's own observer logic — *under-modelled
friction is chased ⇒ stick-slip* — that predicts **worse**, and worse is what flew
(engaged/manual 6–9 Hz 2.89× → 6.58×, contrast +0.682 [+0.213, +1.166]).

⇒ **The flight and cancellation-reasoning are about DIFFERENT AXES** — knee position/magnitude vs
sharpness of the switch. **`0xC40BC` moves both at once and they are not separable with this cell.**
No measurement is overturned. ⭐ Generalisable lesson: before declaring a theory/flight conflict,
check whether the cell moves **two** physical axes that the two arguments treat separately.

## The other answers [all EVIDENCE]
- **Direction:** lowering ⇒ steeper ramp ⇒ MORE modelled friction ⇒ (polarity chain,
  [[accord-friction-polarity-more-assist]]) **LIGHTER wheel**.
- **K0 — the kill criterion is NOT met.** The ramp is the **shared** normaliser for both terms, but
  `K0 = 0` and `ramp × 0 = 0` for any ramp ⇒ **lowering cannot numerically re-arm K0.** It does reshape
  **K1's** term toward `sign(rate)·|model|·K1/1024`, but that stays **∝|model|** and **bounded by the
  ±10 clamp** — **not** K0's *pure, amplitude-independent, unbounded-index* hazard. A milder cousin.
- **HARD FLOOR ≥ 1.** Read **unsigned** (`cvtf.uws` `0x3babc`) and used as a **divisor**
  (`divf.s` `0x3bad0`) ⇒ **0 gives ±Inf/NaN** into `gp-0x6bfc`/`gp-0x6bfe` and thence into float
  comparisons in the ±20000 path. Usable range **300–600**.
- 🛑 **NO ENGAGEMENT GATE.** `FUN_0003b8f6`'s entry guard is `|gp-0x6b98| ≤ 8192` ∧ `|gp-0x4f60| ≤ 25600`
  ∧ `|gp-0x6abc| ≤ 13000` ∧ `polarity ∈ {−1,0,+1}` — **all plausibility/range guards.** It runs in
  MANUAL too. V65 ("vibrates regardless of LKAS engagement") is the precedent.
- **No `0xC40D4` coupling.** `0xC40D4` filters the command into `fVar18`; `0xC40BC` normalises the rate
  ramp. Different operands, meeting only at `maddf.s`. **Separable ⇒ the V86 confound does not weaken
  the direction argument.**

## ⊕ V89's null, re-read
At 1 °/s the stock ramp delivers only **9.4 %** of full friction (`4.7 ct × 12 / 600`). **V89 doubled a
term the ramp mostly switches OFF at creep** — which would explain a flat result, and argues `0xC40BC`
(which moves the ramp) is better-aimed than `0xC40D2` (which moves a magnitude the ramp suppresses).
⚠ Rests on `|fVar18|`, unmeasured.

## Related
[[reference_accord_c40d0_c63ac_exact_alpha_match_v97_broke_it]] — companion finding, same decompile.
[[accord-friction-polarity-more-assist]] — the polarity chain the direction answer uses.
