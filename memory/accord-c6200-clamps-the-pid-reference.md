---
name: accord-c6200-clamps-the-pid-reference
description: 0xC6200 (=8192) is read at 0x3a7a2 INSIDE FUN_0003a382 and hard-clamps gp-0x6ad6 (the PID reference) before the error subtraction, so whenever |gp-0x6ad6| >= 8192 the PID's sensitivity to gp-0x6b70 — and to EVERY Path-2 gain above it — is EXACTLY ZERO through P, I and D at once. Conditions the 0.2565 authority figure. The cell has FOUR known roles plus one unchased reader; both clamp duties are UNMEASURED and are V100's content.
metadata:
  type: reference
---

# 🛑🛑 `0xC6200` CLAMPS THE PID'S REFERENCE — the saturation that can zero every Path-2 gain

Traced 2026-08-13 (`tracer-6ad6`), program `code.bin`. **Crux independently re-verified by the
orchestrator** — `read_memory(0xC6200)` = `00 20` LE = **8192**, and an independent
`disassemble_bytes(0x3a790..0x3a7f0, dry_run)` reproduced the listing **instruction-for-instruction**.
Byte-identical to stock on the **V98 image (ON THE CAR)** and V99: `code[0x3A798:0x3A7F0]`,
`code[0x37FE6:0x38146]`, `code[0x38148:0x382D8]` all match the stock dump.
Full trace: `docs/TRACE-2026-08-13-v100-6ad6-and-ivar6.md`.

## THE HEADLINE [EVIDENCE]

> **`|gp-0x6ad6| ≥ 8192` ⇒ `∂(gp-0x6ad4)/∂(gp-0x6b70)` = 0 — through P, I AND D SIMULTANEOUSLY.**

`gp-0x6b70` (all of Path 2) enters `gp-0x6ad6` at **unit weight** (`0xC64B0` = 1) through a **speed
LERP that is the IDENTITY** (Y `0xC6ACA..0xC6AD8` all 1024, out-of-range fallback `0xC6448` = 1024)
⇒ `(iVar4 × 1024) >> 10 == iVar4`. **There is no dilution anywhere for the clamp to hide behind.**

## THE STRUCTURE, address by address [EVIDENCE — `disassemble_bytes` dry_run + `decompile_function(0x3a382)`]

```
0003a798: ld.h  -0x6ad6[gp],r7     ; the REFERENCE, written by FUN_00037fe6 with a ±25600 clamp
0003a7a2: ld.h  0x7200[tp],r6     ; cal 0xC6200 = 8192          <-- THE CLAMP CONSTANT
0003a7b8:   mov r11,r7            ;   r7 = +8192                 <-- HIGH RAIL
0003a7c8:   subr r0,r7            ;   r7 = −8192                 <-- LOW RAIL
0003a7ca: ld.h  -0x4f60[gp],r8    ; the MEASURED DRIVER TORQUE
0003a7ce: sub   r7,r8             ; err = torque − clamp(ref, ±8192)     <-- THE PID ERROR
0003a7d0..0x3a7e2:                ; err = clamp(err, ±10240)   <-- SECOND saturation (0x2800, an IMMEDIATE)
0003a7e8: mul   lp,r8,r0          ; × Kp  — and I and D derive from the SAME `err`, nothing else
```
🛑 **P, I and D all come off that one clamped difference.** There is no second entry point for
`gp-0x6ad6` anywhere in the PID, so the clamp zeroes all three at once — not one term of three.

## 🛑🛑 THE CONDITION ON `0.2565` — THE PART MOST LIKELY TO BE LOST

> **`d(gp-0x6b94)/d(gp-0x6b70) = 0.2529 / 0.2565 / 0.2617` at 6 / 7.79 / 9 Hz is the UNSATURATED
> small-signal derivative, valid ONLY while `|gp-0x6ad6| < 8192`. On any frame where EITHER clamp is
> active the true derivative is EXACTLY ZERO, not 0.2565.**

The `path2-authority` result was reported as *"no dilution anywhere, every link unity."* Every link
**is** unity — and a hard clamp is not a link. ⇒ **A future session that reads `0.2565` without this
condition will aim a gain lever into a box that may already be full.** That is precisely the failure
this memory exists to prevent.

## `gp-0x6ad6` — census and production [EVIDENCE, five methods, Ghidra ∖ Python EMPTY]

**1 writer** `0x38142` (`FUN_00037fe6`, no lockstep shadow) · **2 readers**: `0x3a6ba` is a
**plausibility gate only** (`|gp-0x6ad6| ≤ 25600` ∧ `|gp-0x4f60| ≤ 25600` → the PID enable), `0x3a798`
is **the control path**. disp23 **0** · 32-bit literal `0xFEDF152A` **0 image-wide** · `ep`-alias
**0 of 1,295 candidate bases in reach**. ⚠ A raw scan offers two extra hits at `0xBCC52`/`0xBDF92`:
they are `st.b -0x6ad5[gp]` (**bit 0 is NOT a size selector for `st.b`** — my own alias rule
over-matched) inside a monotone data table with no function. **Excluded.**

```python
# FUN_00037fe6 @0x37fe6, once per 1 kHz pass from FUN_0002214a @0x22696
iVar4 = -s16(gp_0x6b4a)  if -25600 <= gp_0x6b4a <= 25600 else 0     # 0x37fea..0x38002  TERM 0
if u8(gp_0x67ab) != 1:                                              # gp-0x67ab ≡ 0 ⇒ ALWAYS taken
    iVar4 += zero_reject(gp_0x6bc2,10240) + zero_reject(gp_0x6b60,15360) \
           + zero_reject(gp_0x6b2a,10240) + zero_reject(gp_0x6bce,10240) \
           + s16(zero_reject(gp_0x6b6e,10240) + zero_reject(gp_0x6bbc,10240)) \
           + zero_reject(gp_0x6b70,10240)          # <-- ALL OF PATH 2, weight 1
gp_0x6ad6 = clamp((iVar4 * 1024) >> 10, ±25600)                     # 0x38124..0x38142
```
All seven weights `0xC64AD..0xC64B3` byte-read **= 1** on stock, V98 and V99.

## ⭐ TERM 0 RAILS IT AT **32 %** OF ITS OWN CLAMP — not 100 % [EVIDENCE]

`gp-0x6b4a ∈ ±25600` (writer clamp `0x27772..0x277aa`; 🛑 it also has a **shadow-lockstep twin at
`gp-0x4cd2`**, same class as `gp-0x6bfa`/`gp-0x4cfa` — write-side only, **reading is free**).
Term 0 does **not** need to rail `gp-0x6ad6` at ±25600; it needs only `|gp-0x6b4a| > 8192`.

| term | cell | window / clamp | ratio to the ±8192 PID clamp |
|---|---|---|---|
| **0** | `gp-0x6b4a` | **±25600** | **3.125×** |
| 1 | `gp-0x6bc2` | ±10240 | 1.25× |
| 2 | `gp-0x6b60` | **±15360** | 1.875× |
| 3 | `gp-0x6b2a` | ±10240 | 1.25× |
| 4 | `gp-0x6bce` | ±10240 | 1.25× |
| 5 | `gp-0x6b6e` + `gp-0x6bbc` | ±10240 each, pair `sxh`'d | 1.25× each |
| **7** | **`gp-0x6b70` — ALL OF PATH 2** | gate ±10240, but the cell is clamped **±8192 by the SAME cal** | **1.000×** |

⭐ **`0xC6200` bounds Path-2's entire output AND the entire reference with the same number** ⇒
**Path 2's full scale is exactly the width of the window it must fit inside**, and every
co-contribution from the other seven terms eats that headroom one-for-one.

## `0xC6200` IS **FOUR** THINGS — and the blocking flag [EVIDENCE: raw tp-disp16 scan, 15 hits]

The count matches `BUILD-LINEAGE.md:490`'s *"15 readers, 3 still unidentified"* exactly, and the
three were this clamp.

| sites | function | role |
|---|---|---|
| 6, `0x353de..0x354f0` | `FUN_000352b4` | friction-magnitude lane (`gp-0x6b86`) |
| 4, `0x382ac..0x382c6` | `FUN_00038148` | clamps **`gp-0x6b70`** — Path 2's output |
| 1, `0x38a94` | `FUN_000389ec` | Stage-2 LERP `Y[9]` |
| **3, `0x3a7a2`/`0x3a7b2`/`0x3a7c4`** | **`FUN_0003a382`** | **clamps `gp-0x6ad6`** — NEW 2026-08-13 |
| 1, `0x39ff6` | `FUN_00039702` | 🛑 **UNCHASED** |

> 🛑 **BLOCKING FLAG — `0xC6200` MUST NOT BE EDITED BY ANY FUTURE BUILD UNTIL `0x39ff6` IS CHASED.**
> V100 is unaffected: it **READS** `0xC6200` and changes **zero calibration bytes**, so an unchased
> reader cannot affect that build's correctness. The flag binds only a build that proposes *moving*
> the cell — **and moving it is a live temptation precisely because the cell now has FOUR known roles
> in the same loop, so an edit intended for one hits all four plus the unknown fifth.**
> To clear it: `decompile_function(0x39702)`.

🛑 **Stop calling `0xC6200` "gp-0x6b70's clamp."** Every build script since V90 labels it that way
(`build_v96_tva.py:701`, `v97:164`, `v98:677`, `v99:438`), and that label is what kept the PID role
invisible for ten builds.

## 🛑 V65's "THE AGGREGATOR NEVER RAILS" DOES **NOT** BOUND THIS CLAMP — do not make that inference

[[accord-aggregator-never-rails-loop-is-linear]] measured `gp-0x6b94` never reaching ±8192 in
**120,049 frames**, NEUTRAL 99.89–99.98 %. **Different cell, different point in the chain:**
`gp-0x6b94` is the aggregator output **downstream** of the PID; `gp-0x6ad6` is the reference
**upstream** of it. And the arithmetic says the two nulls are compatible, not redundant — a fully
railed reference contributes only `8192 × 0.2565 ≈ **2,101** counts` at `gp-0x6b94`, **comfortably
inside V65's NEUTRAL band (|·| < 4096)**. ⇒ **V65's null is silent about `d_clamp`.**
[BELIEF — the step uses `0.2565`, which is itself the unsaturated derivative, so this is a
linearisation; the conclusion is stated only in the safe direction: V65 does *not* bound the duty.]

## 🛑 BOTH DUTIES ARE **UNMEASURED** — this is OPEN, not answered

`gp-0x6ad6` **has never been on the wire.** (`grep -l 6ad6 build_v*_tva.py` → v43/46/52/52c/53/96/
vfourframe — **all prose and cal tables, zero probes.**) V100 measures both:
`b5 = |gp-0x6ad6| ≥ cal(0xC6200)` and `b6 = |gp-0x4f60 − gp-0x6ad6| ≥ 10240`.

⭐ **The second rung needs no clamp arithmetic in the cave** [EVIDENCE, exhaustively verified over the
full reachable `(REF, T)` grid, 0 mismatches]: when `C1 = 0` then `clamp(REF,±8192) ≡ REF`, so the
cheap unclamped predicate `C2'` **is identical** to the true one; when `C1 = 1` authority is already
zero. ⇒ **`authority is exactly zero ⟺ C1 ∨ C2'`, no approximation**, and the two bits ship
separately so the 2×2 joint is observable.
🛑 **`d(C2')` UNCONDITIONED IS NOT THE ERROR CLAMP'S DUTY** — on `C1 = 1` frames `C2'` is
uninterpreted. **The error clamp's true duty is `d(C2' | C1 = 0)`. Never quote the unconditioned one.**

**If the duty comes back HIGH:** V89's flat dose-response and V97's felt-null are explained by **one
mechanism requiring nothing unmeasured** — both levers were live, correctly aimed and correctly
signed, and their output was thrown away by a saturation. **If it comes back ZERO** (with the sign
positive-control healthy): the saturation hypothesis is **dead**, and the `f′`-compression account is
the only survivor. Either way it is decisive — which is why it is V100's content.
⚠ **Conditional on exposure:** the endpoint is a **duty**, and a short drive kills both rungs
equally. There is no cheaper fallback hiding inside the design.

Related: [[accord-friction-polarity-more-assist]] (the reference is a torque-tracking REFERENCE, not a
motor torque; `error = driver torque − reference`) · [[accord-aggregator-never-rails-loop-is-linear]]
(reconciled above) · [[accord-gp6b4a-direct-lkas-term]] · [[accord-stage2-lerp-rescale-is-identity]] ·
[[accord-anti-damping-is-not-the-pid]] · [[accord-0x18f-payload-one-frame-stale]] (why identity stays
on `0x14A`) · [[accord-v98-comparator-ranked-the-observer-arms]] · [[accord-probe-underranges-to-one-bit-comparator]].
