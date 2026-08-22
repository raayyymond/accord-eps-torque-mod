---
name: accord-v104-flew-and-failed-verify-from-telemetry
description: "🛑★★★★★ V104 FLEW as route `a4` while STATE.md AND BUILD-LINEAGE.md:26 both said 'BUILT, NOT FLASHED' — the SECOND consecutive build with a stale on-car record. Settled from the WIRE: 57 frames with CAN-427 code > 800 (max 850) are arithmetically impossible on V103, whose packer ceilings at 800. Its dose provably arrived (1.824×) and it fixed NOTHING. ⇒ verify the flown build from telemetry, never from a doc."
metadata:
  node_type: memory
  type: reference
---

# V104 flew, failed, and both documents were wrong about it

## 1. 🛑 THE RECORD WAS WRONG — TWICE IN A ROW
`docs/STATE.md` and `docs/BUILD-LINEAGE.md:26` **both** said *"V104 — BUILT, NOT FLASHED. V103 IS ON THE
CAR."* **V104 was flashed and driven as route `a4` (938.1 s, 670.4 s engaged, fault-free).** The same
error had occurred one build earlier: V103's own block said *"built, not flashed, decision deferred"*
while it was being driven as route `0x9e`.

## 2. ⭐ HOW IT WAS SETTLED — FROM THE WIRE, NOT FROM A DOCUMENT
Route `a4` carries **57 frames with a CAN-427 wire code > 800, max 850.**
V103/V102's packer is `|gp-0x6b4c| · 5 >> 6` against a **±10240** writer clamp ⇒ **structural ceiling
`(10240·5)>>6` = 800**; observed max on `0x9e` was **117**. **A code of 850 is arithmetically impossible
on V103.** ⇒ **the build on the car during `a4` is V104, proven independently of any report or record.**

🛑 **STANDING RULE: VERIFY THE FLOWN BUILD FROM THE TELEMETRY, NEVER FROM THE RECORD.** Design each build
so it carries a **single-frame categorical witness** — a value structurally impossible on its predecessor.

## 3. THE DOSE ARRIVED AND THE LEVER IS DEAD
Within-drive `|gp-0x6b86|` engaged vs manual, binned by `|tq|` **AND speed** (5–20 km/h overlap):
**pooled median ratio 1.824×** against a predicted **1.66–1.85**. ✅ **The `c4` ×1.85 dose reached the
car.** **Operator verdict: both symptoms unchanged, no steering-feel change.** ⇒ **`c4` as a flat-gain
lever is CLOSED.**

🛑 **A TRAP IN OUR OWN PRE-REGISTRATION THAT WOULD HAVE INVERTED THE VERDICT.** The literal `|tq|`-only
binning returns **0.600 / 0.760 / 1.000 / 1.000 / 1.429** ⇒ *"≈1.00, the edit is not in force"* —
because **`a4`'s manual arm is 74 % PARKED** and the assist map is **speed-scheduled (~2× steeper at
parking)**. **Anyone running it as written would have reported an ARM FAILURE on a perfectly delivered
dose.** ⚠ **Binning on `|tq|` does not remove a speed schedule. Bin on BOTH.**

## 4. 🛑 THE 6–9 Hz RESULT DOES NOT SURVIVE THE OPERATOR'S OWN WINDOW — a withdrawal
He supplied the correction himself: *"I hope you are measuring in the right windows (low speed < 10 mph)."*
| V104/V103 at 6–9 Hz | raw [CI] | placebo-corrected |
|---|---|---|
| 0–40 km/h (as first reported) | 0.445 [0.24, 0.66] | 0.63 |
| < 16 km/h (**his window**) | 0.69 [0.30, 0.96] | 0.86 |
| < 10 km/h | **1.07 [0.30, 1.64]** | **1.29 — WORSE, CI spans 1** |

⭐ **And the tighter window is the BETTER-CONTROLLED one** — `a4`'s own split-half at 6–9 Hz is **2.14 at
0–40 but 0.71 at <16.** **The window originally reported was the one whose internal control was worst.**
⇒ **"the band responded, therefore the lane was not rejected" is WITHDRAWN.** The rejection question
(candidate c) is **OPEN**.

## 5. THE DRIVE-LEVEL OFFSET IS REAL — placebo correction is mandatory
The 32–45 Hz placebo (V104/V103) is **0.83 / 0.80 / 0.68 / 0.71** at <10 / <16 / <20 / 0–40 — it
**persists at every window**, so `a4` is genuinely a quieter drive than `r9e` across 6–45 Hz.
🛑 **Every V104-vs-V103 number must be placebo-corrected.**

## 6. WHAT SURVIVED AND WHAT DID NOT
**SURVIVES:** the dose measurement (1.824×, a within-drive lane quantity with no speed window) · **no
clipping** (max `|gp-0x6b86|` **2720** vs the ±12288 clamp, **4.5× clear**, duty 0.000000) ⇒ the
clamp/relay candidate is **DEAD** · the identity/telemetry confirmation · the harmonic refutation.
**DOES NOT SURVIVE:** the 6–9 Hz contrast · the refutation of candidate (c) that rested on it ·
**the 2.03× stock→6× reference at 6–9 Hz** (at <10 km/h the same statistic is 3.97× / 5.28×) · and the
framing *"the ratchet is only a 2× problem"* — **an artifact of the 0–40 km/h window in BOTH directions:
23× at highway, 4–5× at low speed. The ratchet band is gain-carried everywhere.**

## Related
[[accord-26hz-mode-is-a-steering-rate-phenomenon]] · [[accord-notch-is-the-only-shape-that-survives-gate2]] ·
[[accord-recut-overwrites-the-previous-plain-image]] · [[feedback-episodes-not-windows]] ·
[[accord-check-build-lineage-before-proposing-lever]]
