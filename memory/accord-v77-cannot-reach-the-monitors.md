---
name: accord-v77-cannot-reach-the-monitors
description: Two of three monitor surfaces are verified blind to 0xC63A0; the third (gp-0x6b98 vs its float envelope) is live ONLY IF an unresolved link holds — so V77's status is UNDETERMINED.
metadata:
  type: project
---

🛑🛑🛑 **V77's STATUS IS UNDETERMINED. It is NOT cleared to fly.** Two of three monitor trip surfaces
are **orchestrator-verified blind** to `0xC63A0`; a third is live **only if** a disputed link holds.

## Surfaces A and B — verified BLIND to `0xC63A0` [EVIDENCE, orchestrator-verified in Ghidra]

**The argument, in two verified steps:**

1. **The monitors read `gp-0x6bd0` DIRECTLY.** `FUN_000347b8` computes
   `fVar5 = (float)(int)*(short *)(gp - 0x6bd0) * 0.0009765625` — the damper cell itself, Q10 — tests
   the residual against the float constant `0x3ba00000` (= 5/1024), and reports via
   `FUN_000462e6(0x417a,…)` (fid 29). `FUN_00034350`'s own top-of-function check re-verifies the same
   invariant one cycle later off the Q10 int mirrors `gp-0x6bc4/6/8/a` → `FUN_0004613e(0x4179,…)`
   (fid 28).
2. **`0xC63A0` is strictly DOWNSTREAM of it.** In `FUN_00038148`, `gp-0x6bd0` appears **exactly once**,
   as one of six **read-only** summands, weighted by `*(ushort *)(tp + 0x73a0)` = `0xC63A0`, behind a
   **zeroing** gate `(*(short*)(gp-0x6bd0) + 0x800) < 0x1001` (|x| ≤ 2048). **The function's only store
   is `*(short *)(gp - 0x6b70) = iVar9`. There is NO write to `gp-0x6bd0` anywhere in it.**

⇒ **Reverting `0xC63A0` changes not one bit that either monitor sees.** Surface B
(`gp-0x6acc` vs `gp-0x6ace`) is a fully parallel pipeline — `FUN_000456a4`'s comp term is built only
from `gp-0x6a10`/`gp-0x6ac0`/`gp-0x6abe`, with **zero** references to `gp-0x6b98`/`gp-0x6bd0`/`gp-0x6b70`.

## 🛑 Surface C — the ORIGINAL Monitor 1/2 pair, and it flips the answer CONDITIONALLY

The pair `gp-0x3564` (Monitor 1) / `gp-0x3550` (Monitor 2) does **not** compare `gp-0x6bd0` at all.
It compares **`gp-0x6b98`, the merged command itself**, against a float envelope `gp-0x6dbc`/`fVar23`:
`fVar12 = −((float)*(short*)(gp-0x6b98) * 0.0009765625 − fVar23)`; outside ±5/1024 it sets flag **32.0**
(the "torque arm" weight) → `gp-0x3540`/`gp-0x3550` → `FUN_000462e6(0x3f1b,…)` → **fid 29**. The same
check recurs one cycle later in `FUN_00042af8` (`gp-0x3564`, +10/cycle, threshold 100) →
`FUN_0004613e` @`0x43D42` → **fid 28**. `fVar23` is built from `gp-0x4f64` + corridor tables
`tp+0x71d4`/`tp+0x71d8` with **no Path-2 references** ⇒ only the left side could move.

⇒ **IF `0xC63A0` reaches `gp-0x6b98`, V77 has a real mechanism and is NOT dead on arrival.**

🛑🛑 **THAT PREMISE IS DISPUTED AND UNRESOLVED — it is the whole flash decision.** It was justified by
*"Path 2 closes through `gp-0x6b98`"*, which is **the wrong direction**: `FUN_0003b8f6` **reads**
`gp-0x6b98` back **into** Path 2, making it an **input**, not an output. A second tracer decompiled
`FUN_00042af8` in full and reports `gp-0x6b94` (the aggregator's output) appears **nowhere** in its
1,424 lines — the governor's sum runs on `gp-0x6afe`/`gp-0x6b08`/`gp-0x4f64`, i.e.
`gp-0x6b98 = clamp(clamp(gate(gp-0x6afe) + uVar34))`.

⇒ **THE ONE QUESTION: what writes `gp-0x6afe`, and does it carry `gp-0x6ad4`/`gp-0x6b94` — anything
downstream of `0x381AC`?** Answer it before flashing V77.
⚠ Settle it by **reading the body and following the binding**, NOT by grepping the displacement
([[feedback-displacement-grep-misses-reused-ghidra-variable]]).
⚠ Also unknown even if the link holds: whether the ±5/1024 window is *normally* exceeded on stock, and
whether 2048→1024 is **enough** to pull the residual back inside it. That is a magnitude question ROM
alone cannot answer.

⇒ If V77 is flown while Surface C is dead, **that outcome carries NO information** — the lever never
touched the mechanism. See [[accord-both-faults-fired-at-max-angle-rate-slew]].

★ **BUT `0xC63A0` IS NOT INERT — it does move delivered torque.** A subagent claimed this session that
`gp-0x6ad6` is a gate input to `FUN_0003a382` and never a data input, therefore `0xC63A0` = "0.00 dB,
full stop". **That is FALSE and was caught by reading the decompile.** `gp-0x6ad6` appears **three**
times in `FUN_0003a382`: the entry gate, its sign bit, **and `uVar19 = (uint)*(short *)(gp - 0x6ad6)`
— a DATA read.** `uVar19` is clamped to ±(`tp+0x7200`) into `uVar24`; `iVar30 = gp-0x4f60 − uVar24`
forms the **error**, clamped to ±0x2800 as `iVar31`, driving three gain-scheduled lanes into
`gp-0x6ad4`:
- **P** `iVar14 = IIR((iVar31 × LERP_uVar20) >> 10 × 0x20, tp+0x7450)`, state `gp-0x367c`
- **I** `iVar18 = ((LERP_uVar16 × iVar31) >> 10) + gp-0x3688`, state `gp-0x3688`
- **D** `iVar29 = ((iVar31 − gp-0x3684) × LERP_uVar12) >> 10`, state `gp-0x3684`

⇒ **`FUN_0003a382` IS a gain-scheduled PID on the error between `gp-0x4f60` and `gp-0x6ad6`** — the
golden model's original wording was right. So `0xC63A0` **does** move the delivered command via Path 2.
🛑 **Keep the two questions separate:** "does `0xC63A0` move delivered torque?" (**yes**) is NOT the same
as "does it move what the monitors compare?" (**no** for Surfaces A/B; **undetermined** for Surface C,
which hinges on the `gp-0x6afe` link above). Conflating them is how V77 gets flown on a false premise.

⊕ The gate is real and worth keeping: when it fails (`|gp-0x6ad6|` or `|gp-0x4f60| > 25600`, or
`gp-0x2588`/`gp-0x2584` bit 27, or `gp-0x6ac0 ≥ 0x32c9`), `gp-0x6ad4 = 0` **unconditionally**. A
`gp-0x6ad6` rail-hit as a fault contributor is a live **[BELIEF]**, unsized.

⚠ **`0xC63A0`'s effect was always confounded with damper liveness.** V72/V73 carried 2048 without a
manual fault — but their damper was structurally **zero**, so `2 × 0 = 0` and the weight was inert.
V74/V75 are the only builds where it carried signal, and both faulted. **That history cannot separate
"the weight" from "the damper being live."**

⚠ Treat as **[BELIEF] pending verification** (reported by a tracer, not orchestrator-checked): that
`FUN_0003aa2c`'s output `gp-0x6b94` does **not** reach `gp-0x6b98` (`FUN_00042af8` allegedly never
references it, running instead on `gp-0x6afe`/`gp-0x6b08`/`gp-0x4f64`), and that the "B" input branch
`gp-0x4f60` in `FUN_0003b8f6` is dead code (`0xC4048`/`0xC404C`/`0xC4050` all zero).

Related: [[accord-v77-built-c63a0-revert]] · [[accord-path2-is-a-closed-firmware-loop-and-c63a0-weights-it]] ·
[[accord-v74-fault-damper-WAS-in-force-mode-lag]] · [[feedback-verify-the-crux-yourself-it-caught-four-errors]]
