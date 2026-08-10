---
name: accord-engagement-amplifies-6-9hz-via-coulomb-relay
description: Engaging LKAS multiplies the 6-9 Hz column mode 2.8x band-specifically, NOT rate-dependently; de-relaying the command-proportional Coulomb friction (0xC40BC=6000) made it 2.3x WORSE.
metadata:
  type: reference
---

Measured on the **full corpus** — 30 routes / 284 min / **235 episode blocks**
(`v89_c1_full_corpus.py` → `v89_c2_powered_discriminator.py` → `v89_c3_friction_relay.py`).
Band contrast = 6–9 Hz minus a 32–38 Hz control on identical windows; episode-bootstrapped.

## The target [EVIDENCE]
| term | band contrast | verdict |
|---|---|---|
| **`eng`** | **+0.413 [+0.146, +0.667]** | engagement multiplies 6–9 Hz by **2.8×**, **1.5× more than the control band** |
| `eng × log rate` | **+0.022 [−0.070, +0.116]** | **NULL** |
| **`log hands`** | **−0.655** vs control **−0.266** | CIs disjoint ⇒ **column friction damps this mode** |

⇒ **The engagement effect is a CONSTANT, band-specific gain — it does NOT grow with wheel rate.**
The rate dependence the operator feels is in the **EXCITATION** (turning the wheel feeds every band),
not in a rate-dependent firmware term.
⇒ 🛑 **NOTHING here argues for limiting the LKAS command's angle rate.** The target is a gain.

## The mechanism, and the inversion [EVIDENCE for the association, BELIEF for the cell]
On V87/V88 **stock modes 24 ≡ 26 are byte-identical in all six factor families** ⇒ engaging changes
**no calibration**. A constant 2.8× must come from the command's ENTRY moving the loop through a
nonlinearity. The one on record is **`FUN_0003b8f6`, a Coulomb relay PROPORTIONAL TO THE COMMAND**,
`ratio` saturating against **`0xC40BC`** (pinned across 99.62 % of its range at stock = pure relay;
raising the gate widens the linear region and **de-relays** it).

```
0xC40BC =  600   stock, V87, V88   <- THE CAR RIGHT NOW
0xC40BC = 6000   V85, V86, V86B only (routes 6e, 6f, 70)
```
Identified **within-route** (flag constant per route ⇒ only the engaged-vs-manual gap carries it):

| `0xC40BC` | engaged/manual 6–9 Hz amplification |
|---|---|
| **600** | **2.89× [2.14, 3.92]** |
| **6000** | **6.58× [3.19, 13.14]** |

**`eng × FRIC6000` band contrast +0.682 [+0.213, +1.166] — EXCLUDES 0, POSITIVE.**

🛑🛑 **De-relaying the Coulomb friction made the ratchet band 2.3× WORSE.**
🛑🛑 **`STATE.md`'s standing "FREEZE `0xC40BC` at 6000" is CONTRADICTED on the 6–9 Hz band** (it was
set on relay-saturation duty and other bands). **The car is at 600, the better value. DO NOT restore
6000.**
★ **Two independent lines agree that COLUMN FRICTION DAMPS THIS MODE:** driver grip and the
firmware's own relay. **⇒ the lever class is "MORE column friction/damping", not "less command".**

⚠ 3 routes carry the flag, one era; **V86 also moved `0xC40D4`** and **V86B armed the damper** — both
carried as interactions and both inconclusive-to-null, but `0xC40BC` cannot be fully separated from
V86's `0xC40D4`.
⚠ The instrument measures **6–9 Hz band energy, not "feels smooth"** — more Coulomb friction can damp
the oscillation and make the wheel notchier. **The operator scores that, not the instrument.**

## 🛑 Two loader bugs that produced a wrong headline first
1. **`_cache_r*/r<NN>.npz` skips every PER-SEGMENT cache** (`r<NN>s<K>.npz`) — ~180 min of ~417 min.
   On 12 routes the `eng × log rate` contrast read **+0.144 [+0.038, +0.288]**; the full corpus
   **refutes it**. See [[accord-ratchet-scales-with-wheel-rate]], corrected in place.
2. **`_{tag}_*_plain_image.bin` misses the `_v67_plain_image.bin` form** — dropped 18 of 32 routes.

Supersedes the exposure claim in [[accord-leverb-rate-discriminator-underpowered]]: the corpus was
never the limit, and 2.4× more data did **not** sharpen the Lever-B answer (+0.075 [−0.099, +0.245]).
