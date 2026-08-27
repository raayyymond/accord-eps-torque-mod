# ★★★★ THERE ARE **TWO** DEAD ZONES — and together they are why creep has never had damping

**Byte-derived 2026-08-05 from the decompile of `FUN_00034350` plus record reads on
`stock_fw_dump/code.bin`.** The kit has recorded "base damping is exactly zero below 35 km/h" since V72.
That is only **half** the story, and the missing half is why every dose proposed so far was homeopathic.

## The arithmetic — [EVIDENCE, decompiled]

```python
# FUN_00034350, damper output -> gp-0x6bd0
# seed is structurally pinned at 1024 (11-channel MIN-reduce; 9 channels hardcoded 1024)
out = ((((seed * B) >> 10) * C >> 10) * D >> 10) * E >> 10   # seed = 1024
if gp_0x6abe > 0: out = -out                                  # SIGN comes from gp-0x6abe
# and the WHOLE product is 0 unless gp-0x6ac0 < 0x32C9
```
**FactorB (`0xC9CCC`) and FactorD (`0xC9DB4`) are flat 1024 on every mode** — verified, one distinct Y
row each. So in practice:

> **`|gp-0x6bd0| = (FactorC × FactorE) >> 10`**, then clamped by the ceiling LERP `0xC77A0[mode*4]`
> (X=[300,800], Y=[512,1024] on all modes ⇒ floor **512** at creep).

## The two dead zones — both `Y[0] = 0`, on **different axes**

| factor | array | axis | `X[0]` | meaning |
|---|---|---|---|---|
| **FactorC** | `0xC9E9C` | **vehicle speed** `gp-0x6a5e` | **2240** counts | **35.0 km/h** (64 counts/km/h) — modes 10–15/22–27 |
| **FactorE** | `0xC9F84` | **motor rate** `gp-0x6ac0` | **60** | the rate dead zone |

Both rows begin at **Y[0] = 0**, and a LERP clamps flat to `Y[0]` below `X[0]`. **Zero × anything = 0.**
⇒ **At creep the speed factor alone forces the damper to exactly zero**, and even with the speed gate
opened, the *rate* factor is still climbing out of its own dead zone at the symptom's small rates.

⚠ **The speed onset is MODE-DEPENDENT, not a flat 35 km/h:** `X[0]` = 1280 (20 km/h) on modes 0–3,
1920 (30 km/h) on modes 4/5, 2240 (35 km/h) on modes 10–15 and 22–27 (the live family — see
[[reference-accord-car-is-tvca4-mode-24-26]]).

## 🛑 Why this matters for sizing — the scaling lever is structurally vacuous

Because **stock `Y[0] = 0` on BOTH factors**, *scaling a record by any k does nothing at creep*
(`k × 0 = 0`). The only way to deliver anything is to **lift `Y[0]` off zero**, and `Y[0] := Y[1]` is
already the maximum monotone lift of `Y[0]` alone. Anything beyond that must raise `Y[1]` too.

## ★★★★ THE LEVER — open the RATE dead zone; no `FactorC` rung alone can reach

**`gp-0x6ac0` during bursts is measured at 99 counts [94, 113]** — deep inside FactorE's dead zone
(`X[0]` = 60), on the first rising segment. Priced at that operating point, against a requirement of
**~43 [30, 60]**:

| configuration | delivered dose |
|---|---|
| stock | **0** |
| `FactorC Y[0] := 429` (`Y[2]`) alone | 6 |
| `FactorC Y[0] := 908` (`Y[3]`) alone | 14 |
| **both dead zones opened (`X[0]` = 12)** | **~50** ✅ |

⇒ 🛑 **NO `FactorC` rung alone reaches the requirement.** The lever is
**`FactorC Y[0] := Y[2]` + `FactorE X[0]: 60 → 12` + `FactorE Y[1] := Y[2]`**, applied to the **13
engaged modes**.

### 🛑 `X[0]` IS **12**, NOT 6 — and the reasoning is the part that must survive

A bare "12" invites a future session to "optimise" it back down. Two reasons, both directional:

1. **A firmware review flagged `X0 < 30` combined with `Y1 > 300` as the zone it would not fly without
   telemetry.** `X[0] = 12` sits at the **top of its own recommended 6–12 band**, which **halves the
   "the ramp starts too close to zero" concern for a ~6% dose cost** (53 → ~50, still clearing ~43
   inside [30, 60]).
2. ⚠ **The rate conversion is rigid-body and biased LOW through a resonance.** The measurement is taken
   at the **column**; the damper indexes the **motor**; and 18–22 Hz is a **torsional** mode. If the
   motor end swings more — which is exactly what a motor-inertia mode means — **the true delivered dose
   is HIGHER than computed.** Erring low is the correct side of that error.

★ **Why it works, and why it is not V72's mistake at larger size:** it **opens the rate dead zone rather
than raising a gain**, so the damper becomes genuinely **rate-proportional inside the symptom's range**
instead of a constant. V72 flattened FactorE into a relay; this does the **opposite** — it moves the knee
down so the proportional segment covers where the car actually operates. Lowering `X[0]` and raising
`Y[1]` while holding `Y[0] = 0` keeps the row monotone and keeps zero damping at zero rate.

*(Superseded: an earlier "rung B = `FactorC Y[0] := 429` alone" recommendation, priced at an assumed
rate of 330. The measured rate is 99, and at 99 that rung delivers 6 — homeopathic.)*

⚠ **Raising `FactorC` costs NO rate-proportionality** — it is speed-indexed, so it is a flat in speed
only. **`FactorE`'s shape IS the rate-proportionality**: flattening it makes `|out|` constant while
`gp-0x6abe` flips the sign, i.e. a **bang-bang relay** in a lightly-damped loop. That is what V72 did to
mode 10's FactorE (`Y → [927,927,927,927]`) and it must not be repeated. **Steepening `Y[1]` while
holding `Y[0] = 0` is NOT the same thing** and is safe — it makes the band more proportional, not less.

✅ **Resolved:** the operating rate was measured (`gp-0x6ac0` = 99 [94, 113] in-burst) and the dead-zone
lever does dominate any Y raise — see the table above. **Always price a damper rung at the symptom's own
measured rate**, not at a nominal one; the two differ by 3× here and it inverted the recommendation.

⚠ And both lanes are gated: `FUN_00034350` **and** the friction lane `FUN_00036c12` sit behind the same
`andi 0x830` state mask ⇒ if the live state is outside {4,5,11}, neither delivers.

Related: [[accord-damper-is-mode-table-selected]], [[accord-task5-is-100hz-damper-cannot-damp-21hz]],
[[reference-accord-gp6a5e-is-speed-reclassifies-v44-v47]], [[feedback-rule7-mode-proof-or-a-bet]].
