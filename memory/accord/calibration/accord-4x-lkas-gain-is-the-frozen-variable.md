---
name: accord-4x-lkas-gain-is-the-frozen-variable
description: The 4x forward LKAS gain is exactly 4.000x on every build since V38 and migrated cells at V57 — invisible to every bisection — but it is structurally decoupled from the loop hosting the ~8 Hz mode.
metadata: 
  node_type: memory
  type: reference
  originSessionId: e91b71d0-25c8-4a14-9b74-24c186211918
  modified: 2026-08-09T07:33:35.453Z
---

**[EVIDENCE, direct LE reads of the plain images]**
```
build          0xC646C   0xC6CD0    forward LKAS gain
stock              891     blank    1.000x
V38/V42/V80       3564     blank    4.000x   <- 4x in the SHARED cell
V58 ... V86B       891      3564    4.000x   <- V57 decoupled it; magnitude NEVER changed
```
**Exactly 4.000× on every build in the modern lineage, without exception.**

🛑 **A variable with zero variance cannot appear in any dose–response, cross-build matrix or A/B — it is
invisible to every instrument this kit has built, by construction.** That is why ~48 builds of bisection
never touched it.

⚠ **Worse than a simple frozen cell: it MIGRATED at V57.** Anyone diffing images across the lineage sees
`0xC646C` go 3564 → 891 and reasonably concludes the gain was reverted. **It was not** — V57 decoupled the
forward reader onto `0xC6CD0` and carried the same 4.000× across. The one variable that never moved *looks
like* it moved.

🛑🛑 **BUT IT IS NOT THE AMPLIFIER, on two independent grounds:**

1. **Path 1 and Path 2 are STRUCTURALLY DECOUPLED [EVIDENCE, verified two ways].**
   `search_instructions(FUN_00028ea6, "6b98")` → **0 over 1,874 instructions**; a raw Python LE scan of the
   function extent for both the `disp16` and `disp|1` forms → **0 hits**; positive control finds **33
   image-wide**. The arbitration function hosting the 4× **never reads the delivered motor command.**
   Path 2's poles — its Q and its frequency — are set entirely by cals inside Path 2.
   ⇒ **The 4× scales EXCITATION into Path 2, not Path 2's loop gain.**
2. **The "4× created the symptoms" keystone is RETRACTED.** `archive/LEDGER-V38-TO-V84.md:192`'s **63.66×** is at
   **20–30 Hz**; the cell for the ratchet band reads **1.41×**, inside the [0.63, 1.50] null. The source
   handoff calls that table's numbers *"uninterpretable"* for a speed confound. The underlying routes
   (`b9`/`77`/`79`) are on **a different comma device** (`807a3c21c9f405e8`) and are **unrecoverable**.

⇒ 🛑 **NEVER RECOMMEND LOWERING THE LKAS GAIN.** Standing operator instruction, 2026-08-09:
*"that is the whole point of this work, to increase max LKAS capability (ideally linearly)."*
**And the evidence agrees with the instruction** — the 4× is not implicated.

★ **CONSEQUENCE: the authority trade curve is FLAT.** Raising authority does not move Path 2's Q. The
limit on going above 4× is **clamp headroom** — and the failure mode on saturation is **a jump to relay
behaviour (Q → ∞)**, per V80, not graceful degradation. 🛑 `gp-0x6bfc` (±20000) and `gp-0x6b70` (±8192)
have **never been measured against real driving**; sizing a rung on either is blind exactly the way V84's
`|r24| ≥ 1024` (input never exceeded 201) and V69's bit4 were blind.

See [[accord-ratchet-is-a-lightly-damped-resonance]].
