---
name: reference-accord-observer-gate-tautology-and-term-mismatch
description: CORRECTS the golden model — FUN_0003b8f6's |gp-0x6b98|<=0x2000 enable gate is TAUTOLOGICAL (producer clamps to exactly ±0x2000 four instructions before the store), so the observer never drops out; and its two subtraction operands do NOT share a term set, so the "two filters on one signal" leak is a DC gain that FALLS with frequency.
metadata:
  type: reference
---

Traced 2026-08-10 on stock `code.bin`, testing the "observer phase-mismatch leaks the EPS's own LKAS
command into the residual" hypothesis. Verdict: **hypothesis exonerated.** Reproducer:
`analysis-2020accord/observer_leak_model.py` (self-checking, asserts every cal against stock).

## 🛑 CORRECTION TO THE GOLDEN MODEL (line ~1269)

The model says of `FUN_0003b8f6`'s gate: *"🛑 A COMMAND-CONDITIONAL DISCONTINUITY: under strong command
Path 2 goes invalid."* **THAT IS FALSE.** [EVIDENCE]

Gate: `gp-0x6b98 + 0x2000U < 0x4001` ⇒ `∈ [−8192, +8192]`. Its producer, four instructions before the store:

```
0x43b0e  addi   -0x2000, r14, r0
0x43b12  movea   0x2000, r0, r21
0x43b16  bgt    0x00043b24
0x43b18  addi    0x2000, r14, r0
0x43b1c  movea  -0x2000, r0, r6
0x43b20  cmovle r6, r14, r21        ; r21 = clamp(r14, ±0x2000)
0x43b4e  mov    r21, r8
0x43b52  st.h   r8,  -0x6b98, gp    ; writer 1
0x43dfc  st.h   r21, -0x6b98, gp    ; writer 2
```

Bound == clamp, **inclusive at both rails** (8192+8192 = 16384 < 16385 = 0x4001). The gate is a defensive
sanity check on a value that cannot violate it. ⊕ Independently re-derived by agent ArcAudit.

🛑 **SCOPE CORRECTION 2026-08-10 (ArcAudit caught it, verified, accepted).** This entry first read
*"the observer never drops out"*, citing V87's `gp-0x6b70` non-zero 99.80%. **That citation is INVALID
and points the WRONG WAY.** `decompile_function 0x3bc20` (whole function):
```c
sVar2 = *(short *)(gp-0x6bfc);
if ((int)sVar2 + 20000U < 0x9c41) { uVar1 = 0x400; } else { uVar1 = 0xffff; sVar2 = 0x7fff; }
*(short *)(gp-0x6bfe) = sVar2;   *(undefined2 *)(gp-0x695c) = uVar1;
```
A gate failure writes `gp-0x6bfc` = 0x7FFF → `gp-0x6bfe` = 0x7FFF → `FUN_00038148` writes
**`gp-0x6b70` = 0x7FFF, NON-ZERO** ⇒ failures *raise* the non-zero count; 99.80% is consistent with an
arbitrarily high failure rate.
⇒ **What is EVIDENCE: the `|gp-0x6b98| ≤ 0x2000` leg cannot fail.** What is **BELIEF**: that the gate
rarely fails *overall* — the other three legs (`|gp-0x4f60| ≤ 25600` = the sensor's own window,
`|gp-0x6abc| ≤ 13000` vs a ±1,930 reachable envelope, `gp-0x6752` a static boot constant) are slack,
but that is an argument, not proof. **Do not cite this entry for "the observer never drops out".**

⊕ **FOUR EXACT, EQUIVALENT GATE DISCRIMINATORS** (because `gp-0x6bfc` is clamped to ±20000 on the
success path, `FUN_0003bc20` cannot fail on a success — `20000+20000 = 0x9C40 < 0x9C41`; and
`gp-0x6bfe`/`gp-0x6b70` are single-sourced 1W/1R, so nothing else can forge the sentinel):
```
gp-0x6c00 == 0xFFFF <=> gp-0x695c == 0xFFFF <=> |gp-0x6b70| >= 8193 <=> gp-0x6bf6 == 0x7FFF <=> gate failed
```
★ **`gp-0x6bf6` is the most information-dense cell in the function**: it is written on **BOTH** arms
(`clamp(2639 × model, ±20000)` on success, `0x7fff` on fail) ⇒ **never stale**, unlike
`gp-0x6ae0`/`gp-0x6ae2`. It gives **`|model|` DIRECTLY** and flags the gate in the same cell, 1W/0R.
With `gp-0x6ae2` it yields `ratio` exactly:
`ratio = (gp-0x6ae2/1024) / (|gp-0x6bf6|/2639) × (1024/K1)` — the separation that turns a friction-dose
*justification* into a *sizing*. Strictly better than a `gp-0x6ae0` rung (that is d/dt of the rate).
★ **`|gp-0x6b70| ≥ 8193` costs NO new cave bit** — V86/V86B/V87/V88 all already probe `gp-0x6b70` at
threshold 64, so it is a threshold change on an existing rung (ArcAudit). Exact because the success path
clamps to ±`0xC6200` = ±8192 *inside* the plausible branch while 0x7FFF is written outside it.
🛑 **NO gate flag catches `gp-0x6752 == 0`** — polarity zero **PASSES** the gate (`(0)+1 = 1 < 3`) and
emits a valid non-sentinel output while the command branch, FRICTION and INERTIA all collapse together.
⊕ **A gate failure HOLDS the previous `gp-0x6ae2` (~41 ct, non-zero) ⇒ it cannot CREATE a zero, only
prolong one** ⇒ observed zeros are fresh independent of gate duty; NON-zero readings stay conditional.
★ **`gp-0x695c` is a plain RAM status word (0x400 ok / 0xFFFF bad)** — if UDS-readable, the question
closes with **no build**. ★ `|gp-0x6b70| ≥ 8193` is exact because the success path clamps to
±`0xC6200` = ±8192 *inside* the branch while 0x7FFF is written outside it. ⚠ V86/V86B/V87 rungs sat at
**64**, so existing cave data cannot separate sentinel from signal.
⚠ Weak, do-not-promote: LeakDose's `gp-0x6b70` regressions on `log|rate|` (+0.947, +0.573, CIs excluding
0) would be diluted by a large sentinel-pinned population ⇒ loosely disfavours a high failure rate.

⊕ `gp-0x6bfa`'s source RESOLVED by agent TorquePath: the sum of **field D** of the 11-slot assist-channel
request struct (`FUN_00025c32` +8, clamp ±20000 = the model's OWN output clamp ⇒ observer units), summed
**ungated**, only destination the residual ⇒ a **declared-disturbance slot**. **LKAS passes ZERO**
(`0002b530 sst.h r0,0x8[ep]`) ⇒ a static-ish per-channel bias, nothing engagement-conditional. Closes
the last gap in the leak accounting **without changing its conclusion**.

📋 **TOOL RULE, reproduced jointly this session: NEITHER Ghidra NOR Python alone is complete on this
program.** Ghidra's `search_instructions` misses unanalysed regions (3 real `gp-0x4f60` hits at
`0x2d9a2`/`0x2dae6`/`0x4f996`, all "No function found"); a naive Python scan misses the 6-byte extended
form. **The UNION is required.** ⚠ And the 6-byte formula's `hw1`/`hw2` mean the **SECOND and THIRD**
halfwords: `disp = (sext16(hw2)<<7) | ((hw1>>4)&0x7F)`, `reg1 = hw0 & 0x1F`. Applying it to the first two
yields garbage and a false "unused" verdict.

⊕ **SAME IDIOM ONE HOP DOWN:** `FUN_00038148`'s sentinel is `|gp-0x6bfe| ≤ 20000` and `gp-0x6bfc` is
clamped to **exactly ±20000** in `FUN_0003b8f6`. Also tautological. **Honda pattern: sentinel bound ==
producer clamp.** Check the producer's clamp before believing any sentinel path in this chain is live.

`gp-0x6b98` writer census, **confirmed two ways** (Ghidra 45 / raw LE byte scan of BOTH encodings —
disp16 `hw2==0x9468`, extended `{8407|a407} 87?? 28ff` — 33+12 = **45, exact agreement**):
`0x43b52`, `0x43dfc` (normal path, clamped) · `0x6e104`, `0x6e1dc` (limp mode).

## The two operands do NOT share a term set

`FUN_00038148`'s six lanes: `6b4e · 6b4c · 6b26 · 6b46 · 6bd0 · 6bbe` (weights `0xC63A0..AA` all 1024).
`FUN_0003aa2c`'s lanes into `gp-0x6b94`: `6b62 · 6b4c · 6ade · **6ad4** · 6b26 · 6bbe · 6bd0 · 6b86 ·
r24 · r26 · FUN_00036682()`. Absent from B: `gp-0x6ad4` (the loop's OWN PID output), r24, r26, `6b62`,
`6ade`, `6b86`. Plus governor slew, comp-add and the Q15 shaper.

🛑 **CORRECTED 2026-08-10, same session — the LKAS OVERLAY *IS* CANCELLED.** My first pass listed the
post-aggregator add of `gp-0x6afe` as having "no counterpart in branch B". **WRONG**, and it was one of
two identities I had explicitly flagged as inherited-not-derived. Orchestrator-verified: `FUN_00026c80`
computes `sVar38 = clamp(Σ gp-0x62c8[i], ±0x2800)`, stores it to **`gp-0x6b4e`**, and tail-calls
`FUN_00042ac6(sVar38)` whose whole body is a store to `gp-0x6afe` @0x42ad6 (its 0x7FFF sentinel
unreachable because the caller already clamped) ⇒ **`gp-0x6afe` ≡ `gp-0x6b4e` bit for bit**, and
`gp-0x6b4e` is in branch B at unity weight (`0xC63A8` = 1024, 7 images). ⇒ **the overlay appears on BOTH
sides** and for *that* term the "two filters on one signal" framing is correct — leak `|H_A − H_B|` =
0.196 @7.79 Hz, 0.360 @21 Hz. The term-set mismatch stands for the OTHER lanes, but those are base-assist
terms present with LKAS off, so they cannot produce an engagement-conditional effect.
📋 **METHOD NOTE THAT PAID OFF: flagging an inherited identity as unverified is what let this be caught
instead of shipped.** Keep doing it.

⚠ **BUT the scaling IS matched** — resolving the golden model's "two conventions" warning: branch A does
`/1024` → EMA2 → **raw float** × `0xC6468`(2639); branch B does `w=1024` unity → `× 0xC6468 >> 10`.
**Both net ×2.5771.** The conventions each cancel their own branch's normalisation ⇒ Honda *did* intend a
cancellation. The term sets are what don't match.

⇒ **Leak = DC gain that FALLS with frequency** (0.90× at 7.79 Hz, 0.56× at 21 Hz of DC, at any realistic
overlap). A low-pass leak cannot preferentially excite 6–9 or 18–28 Hz.

## Filters, re-derived (validates the golden model's numbers)

`0xC40D4` IS applied twice (states `gp-0x3628`, `gp-0x3624`, coefficient re-read) ⇒ 2-pole α=573/4096.
`0xC63AC` single-pole α=102/1024, state `gp-0x374c`; the `*0x10`/`>>4` is IIR resolution, not gain.
Adding one tick of transport reproduces the model exactly: −36.05° @7.79 Hz, −82.84° @21.09 Hz.

`gp-0x6bfa` = saturating ±20000 view of 32-bit `gp-0x3d90` (`FUN_00026c80` @0x27396-0x273b8, shadow
`gp-0x4cfa`); 1 reader, 3 writers. **What `gp-0x3d90` integrates is UNRESOLVED.**

🛑 **Do not propose `0xC40D4` as a phase-match lever** — see [[reference-accord-fun36c12-negative-accel-feedback]]
and the lineage: **V86 flew 573→286 and returned a well-powered null** (`f(V86)/f(V85)` = 1.001
[0.976, 1.060], CI disjoint from the pre-registered [0.797, 0.875]).
