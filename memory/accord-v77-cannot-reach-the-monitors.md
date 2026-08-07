---
name: accord-v77-cannot-reach-the-monitors
description: All three monitor trip surfaces are structurally blind to 0xC63A0, so V77 cannot prevent a Monitor-1/2 trip - flying it would yield no information.
metadata:
  type: project
---

🛑🛑🛑 **V77 (V74 + `0xC63A0` 2048->1024) IS A NULL EXPERIMENT FOR THE HARD-FAULT CLASS.
Do not fly it expecting a safety result.** **ALL THREE** monitor trip surfaces are structurally
blind to `0xC63A0`, established along three independent lines.

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

## Surface C — the ORIGINAL Monitor 1/2 pair. Briefly looked like it flipped the answer; it does not.

The pair `gp-0x3564` (Monitor 1) / `gp-0x3550` (Monitor 2) does **not** compare `gp-0x6bd0` at all.
It compares **`gp-0x6b98`, the merged command itself**, against a float envelope `gp-0x6dbc`/`fVar23`:
`fVar12 = −((float)*(short*)(gp-0x6b98) * 0.0009765625 − fVar23)`; outside ±5/1024 it sets flag **32.0**
(the "torque arm" weight) → `gp-0x3540`/`gp-0x3550` → `FUN_000462e6(0x3f1b,…)` → **fid 29**. The same
check recurs one cycle later in `FUN_00042af8` (`gp-0x3564`, +10/cycle, threshold 100) →
`FUN_0004613e` @`0x43D42` → **fid 28**. `fVar23` is built from `gp-0x4f64` + corridor tables
`tp+0x71d4`/`tp+0x71d8` with **no Path-2 references** ⇒ only the left side could move.

It would be a live lever **if** `0xC63A0` reached `gp-0x6b98`. **It does not.** RESOLVED:
- **`gp-0x6afe` has exactly ONE writer program-wide** - `FUN_00042ac6` @`0x42ad6`
  (`st.h r15,-0x6afe,gp`), six lines: `gp-0x6afe = (param_1 + 0x2800 > 0x5000) ? 0x7fff : param_1`
  [**orchestrator-verified by direct decompile**; it reads nothing else]. Sole caller `FUN_00026c80`
  @`0x277f6`, passing `sVar38 = clamp(iVar14, +/-0x2800)`, accumulated **entirely inside that
  function** from local stack buffers filled from mode-table constants.
- `search_instructions` scoped to `FUN_00026c80`: **989 instructions, ZERO hits** for `6ad4`, `6b94`,
  `6ad6`, `6b70`. Same scan over `FUN_00042af8` (1,769 instructions) for `uVar34`: **zero hits** -
  independently reproducing the second tracer's full decompile, which found `gp-0x6b94` absent from
  all 1,424 lines.

(+) **Real but non-decisive:** `sVar38` is *also* stored to **`gp-0x6b4e`**, one of `FUN_00038148`'s
six weighted inputs and a **sibling** of `gp-0x6bd0`. => they share a common ancestor but run in
**PARALLEL, not series** - `gp-0x6afe` bypasses `FUN_00038148` entirely, so `0xC63A0`'s multiply
(which scales only `gp-0x6bd0`'s contribution to `gp-0x6b70`) never reaches it.

=> `gp-0x6b98 = clamp(clamp(gate(gp-0x6afe) + uVar34))` - **neither term carries anything downstream
of `0x381AC`. ALL THREE SURFACES ARE BLIND; V77 is a null experiment for this fault class.**

WARNING **This answer took the tracer three attempts** (structural NO -> conditional YES -> final NO),
and the YES rested on an unverified directional premise: it cited *"Path 2 closes through
`gp-0x6b98`"*, but `FUN_0003b8f6` **reads** `gp-0x6b98` back **into** Path 2, making it an **input**,
not an output. Recorded because the *pattern* matters: **a subagent reversing its own earlier finding
reads as diligence and is easy to accept unchallenged.**

=> If V77 is flown, **the outcome carries NO information** about this fault class - the lever
never touched the mechanism. See [[accord-both-faults-fired-at-max-angle-rate-slew]].

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
🛑 **Keep the two questions separate:** *"does `0xC63A0` move delivered torque?"* (**yes**) is NOT the
same as *"does it move what the monitors compare?"* (**no — all three surfaces**). Conflating them is
exactly how V77 gets flown on a false premise.

⊕ The gate is real and worth keeping: when it fails (`|gp-0x6ad6|` or `|gp-0x4f60| > 25600`, or
`gp-0x2588`/`gp-0x2584` bit 27, or `gp-0x6ac0 ≥ 0x32c9`), `gp-0x6ad4 = 0` **unconditionally**. A
`gp-0x6ad6` rail-hit as a fault contributor is a live **[BELIEF]**, unsized.

⚠ **`0xC63A0`'s effect was always confounded with damper liveness.** V72/V73 carried 2048 without a
manual fault — but their damper was structurally **zero**, so `2 × 0 = 0` and the weight was inert.
V74/V75 are the only builds where it carried signal, and both faulted. **That history cannot separate
"the weight" from "the damper being live."**

★ **`FUN_0003aa2c`'s output `gp-0x6b94` does NOT reach `gp-0x6b98`** — upgraded to **[EVIDENCE]**: two
tracers reached it independently (a full 1,424-line decompile of `FUN_00042af8`, and a 1,769-instruction
scan of the same function), and the `gp-0x6afe` forward trace above is consistent with it. **This
contradicts the golden model's long-standing "aggregator → `gp-0x6b98`" chain, which has at least one
unresolved hop.** `gp-0x6b94`'s 4 unchecked readers: `FUN_00036bec`, `FUN_0004503c`, `FUN_0004595a`,
`FUN_0007ff08`. ⚠ Still **[BELIEF]**: that the "B" input branch `gp-0x4f60` in `FUN_0003b8f6` is dead
code (`0xC4048`/`0xC404C`/`0xC4050` all zero) — reported, not orchestrator-checked.
⚠ Not exhaustive: 8 further `FUN_0004613e`/`FUN_000462e6` callers (`FUN_00027b0a`, `FUN_00027802`,
`FUN_00036388`, `FUN_00036c12`, `FUN_00041464`, `FUN_000365d2`, `FUN_00036d74`, `FUN_00041b8e`)
untraced; none is in the Path-2 dataflow by name, but a fourth surface is not formally excluded.

Related: [[accord-v77-built-c63a0-revert]] · [[accord-path2-is-a-closed-firmware-loop-and-c63a0-weights-it]] ·
[[accord-v74-fault-damper-WAS-in-force-mode-lag]] · [[feedback-verify-the-crux-yourself-it-caught-four-errors]]
