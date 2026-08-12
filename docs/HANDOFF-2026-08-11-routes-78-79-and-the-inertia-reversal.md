# HANDOFF — 2026-08-11 · routes 78/79 scored, the dose did nothing, and the lever is the wrong physics

**Session shape:** pull two flights → score them → explain a null → find the null's premise was wrong →
reverse the direction of 13 builds → build twice, because the first build could not see its own edit.

**Read `docs/STATE.md` §A1–A5 first.** This is the narrative behind it.

---

## 1. What was pulled

`ssh comma` → routes **78** (16 seg, 927 s, driven 02:18) and **79** (15 seg, 875 s, driven 17:36),
405 MB, into `analysis-2020accord/rlogs/`. Extracted with `rlog-tools/extract_r78_r79.py`, which adds
rows to `decode_v84_probe_r6d.ROUTES` and calls **that module's** `extract()`/`split()` — the same
instrument that wrote every cache since `_cache_r6d/`. **CAN `0x14A` byte 7 is new** (V92 is the first
build ever to write it) and was added by a **pass-through tap**, not by editing the shared extractor;
the tap's byte-4 column is asserted elementwise against the extractor's, so a filter drift kills the
run rather than silently mispairing. `0x14A` DLC is **8** on every frame, so byte 7 physically exists.

Both flights **fault-free**. Route 78 carries **160 s engaged ≥ 80 km/h — the kit's best highway
exposure ever**, 3.8× route 77.

---

## 2. Identity

- **Route 79 = V92, PROVEN single-frame and parameter-free**: `0x14A` byte7[7:6] ≠ 0 on **16,236**
  frames. Impossible on every build V53–V91 (`gp-0x1511`'s only two writers mask bits 7:6 off).
- **Route 78 reads 0.0000 % on that same bit** — a clean positive control for the V92 test.
- 🛑 **Route 78 CANNOT be attributed to V91.** V91 is telemetry-identical to V90; no cave bit
  separates them. **Asked directly, the operator could not confirm the flash.** This matters — see §4.

---

## 3. What the drives measured

**The dose is not in force.** Engaged, cell-stratified by speed × wheel rate, episode-bootstrapped:
p50/p75/p90/mean = **0.988 / 1.230 / 0.941 / 0.964**, every CI containing 1.00, against a
pre-registered **1.50**. The **manual negative control holds at 1.009 [0.982, 1.047]** — a ±5 % CI,
which is what makes the engaged null trustworthy rather than a broken measurement. Three-way duty
`P(|gp-0x6b26| ≥ 15)` = **0.167 / 0.161 / 0.165** on r77/r78/r79 against a needed **0.204**.

**`Re(Z) < 0` replicated on three drives** — 6–9 Hz **−3375 / −3176 / −3073**, coh² 0.71–0.77 against
shuffled ≈ 0.000, with the sign flip to *damped* at ~24–26 Hz on all three. Classified by
window-median |wheel rate|, it is **strongest in the MICRO 1–13 °/s regime: −3480 at 6–9 Hz
(coh² 0.804), −4890 at 9–12** — the regime the operator says is unfixed. **An instrument agreeing
with a symptom, not a demonstration of cause.**
⚠ The ratchet regime (13–50 °/s) yielded **4** scoreable windows and macro **0**: sustained fast
steering does not survive the hands-off mask. That is the binding census limit on the next drive.

**`gp-0x6bbe` identified** — first measurement in the kit's history. It is the **base-assist output**
(assist map × polarity, speed-clamped by `PTR_DAT_000c7970[mode]`): flat gain ≈ 90 ct/(rad/s), phase
through zero at 5–6 Hz ⇒ **viscous**, on a **~74 ct DC pedestal** flat across 0–6 °/s, with
`P(<0)` = **0.887 engaged vs 0.499 manual**. 🛑 This **refutes** the structural flag that justified
the bit ("same-signed as the raw torque sensor ⇒ REINFORCING"): the measured phase against column
torque is **+140°…+164°**, and that is **fully predicted by `boost ∝ rate` alone**.

**The detent lane is dead.** `gp-0x6b62 ≠ 0` and the `gp-0x6bda` outer gate both read **0.0000 over
75,227 engaged frames**, and `b4 ≡ b5` on all 87,317 frames. 🛑 `byte7 b6` (dwell snap) is a **DEAD
rung** with a **855 s sustained (0,0) run** — exactly the pre-registered indictment condition. Read as
a null on the gate, V64 class. **Do not propose a detent/dwell lever.**

**A placebo floor.** Because the dose did nothing, r77/r78/r79 are three drives of the **same
functional car** — micro-regime column-torque spread 6–9 Hz **1.37×**, 18–22 **1.31×**,
**26–31 Hz 1.99×**, 32–38 control **1.54×**.

---

## 4. The null, and two corrections to how it was reported

The first write-up said *"two independent instruments agree"* and named
*"the car reads mode 24 in both states"* as the leading cause. **Both statements were wrong.**

**Correction 1 — the mode hypothesis is refuted.** `reference-accord-car-is-tvca4-mode-24-26` records
that **V73 probed `gp+0x63fd` — the same byte `FUN_00036c12` indexes (`0x36C4A ld.bu 0x63fd[gp],r15`)
— over 104,061 frames** and watched it change **8 manual → 10 engaged**, 18 transitions, all on
engagement edges, **99.09 % lag-matched**. The index tracks engagement. The hypothesis was dead before
it was written, and **one grep would have found it**. It reached a memory, `BUILD-LINEAGE`, a
published artifact and a whole build proposal first. Recorded as
`feedback-search-the-kit-before-naming-a-cause`.

**Correction 2 — one leg, not two.** Route 78 cannot prove V91 was flashed, so the conclusion rests on
**route 79's `byte7 b7` duty test alone** — a 1-bit test, lower-powered than the continuous one.

**And neither bypass branch explains it either.** `FUN_00036c12` has three gain sources:
```
gp-0x671a >= 0xFF  or  gp-0x67f4 != 1   ->  flat cal(0xC640C) = -3277   [FALLBACK-1]
gp-0x671a >= cal(0xC64FD) = 5           ->  flat cal(0xC640A) = -8192   [FALLBACK-2]
else                                    ->  LERP(0xCBE74[mode]) over gp-0x6a5e
```
`gp-0x67f4` was traced to `FUN_00041eec` and is the **vehicle-speed VALID/SETTLED flag** — set once
any wheel source is valid and the vote settles (Δ < 0x41 ≈ 1 km/h), cleared only when **all** sources
go invalid ⇒ **1 in normal driving**. `gp-0x671a` (oscillation detector) was measured **never
non-zero** on V64/V68. **All three gates pass. The null is UNEXPLAINED.**

---

## 5. The physics correction — and why it reverses the direction

`FUN_00041464`, **pinned in assembly because the decompile cannot settle it**:
```
415e8: add  r28, r24     ; r24 = NEW filtered EPS-motor rate
415fc: ble  0x41600      ; the NORMAL path SKIPS the next instruction
415fe: mov  r24, r7      ; RESET path ONLY (invalid state / first tick) => difference forced to 0
41602: sub  r7, r9       ; 🛑 r9 = NEW - OLD  ==  THE FIRST DIFFERENCE
41612: shl  0x5, r9      ; x32, clamped ±0xfa0000 -> r22   (Ghidra's `iVar14`)
4162e: mov  r22, r26     ; the EMA input IS that clamped difference
```
Ghidra renders the reset path as `uVar8 = uVar16; uVar16 = uVar8;`, which makes the difference look
**identically zero**, and it prints the EMA input as a bare `iVar14` whose assignment is easy to omit
when quoting. **The operator caught exactly that gap.** Both are variable reuse across paths.

⇒ `gp-0x6c2c` is **angular ACCELERATION**, so `gp-0x6b26 = −K·α`, and Path 1's unweighted `add` gives
`(J + K)·α = T_driver`: **apparent inertia rises by K, and the term dissipates nothing.**
`build_v91_tva.py`'s *"genuinely DISSIPATIVE, it opposes motor rate"* is **wrong**.

**13 builds have touched this LERP family — V73–V77, V81, V83a, V84, V86, V90–V92 — and every one
raised it or restored stock. Lowering it has never been tried.**

⊕ A Python mirror of the decompiled arithmetic (`analysis-2020accord/v93_mirror_and_curves.py`) puts
the stock lane's saturation knee at **1.60×** the largest acceleration route 77 produced;
`build_v91_tva.py` derived **1.6014** from measured percentiles by a completely different route.
**Two independent derivations to the same number** — that is what makes the mirror usable.
⊕ It also showed the **stock** lane becomes a Coulomb relay past its knee, worst at parking speed
(3,500 vs 16,000 at 90 km/h). ⚠ Measured clamp duty is **0.000000 in every stratum**, so the relay was
never entered; the margin, stated in the clamped variable, is **1.60× → ~6.4×** under V94.

---

## 6. What was built

| | V93 | V94 — **prefer this** |
|---|---|---|
| image | `779180f8aaf88f29…` | `cd971c05d483fe9c…` |
| rwd | `9c93dca63e9e404e…` | `3feccc09d8cbdd05…` |
| assertions | 126/126 | **133/133** |
| edits | 22 cal bytes | 22 cal bytes **identical** + 1 code byte |

**V94 exists because V93 cannot see its own edit.** 427 packs `wire = (|gp-0x6b26| × 5) >> 3` and V93
divides the cell by 4, so on route 78's measured distribution **87.5 % of engaged frames would land on
wire ≤ 1**. `sar 3 → sar 1` is exactly ×4 and cancels the ×0.25: V94's wire distribution reproduces
route 78's as-flown one (p75/p90/p95/p99/max **5/10/17/37/137** vs **5/10/17/38/138**), making the
ratio test **quantisation-identical**. ⊕ And since `gp-0x6b26 = −K·gp-0x6c2c` with **K known**, full
resolution makes the **EPS-motor acceleration recoverable** — the lever's input, never telemetered on
any build — **with no cave change**.

🛑 **V93 is NOT superseded and its hashes are NOT dead.** It is a valid, verified artefact that simply
measures itself poorly. V94 took a **new build number** precisely so V93's published hashes stay
meaningful — `feedback-name-superseded-hashes-dead-not-merely-omitted`.

---

## 7. What the next session must not repeat

1. **The hands-off coast is still owed** and it gates the entire remaining search. Routes 78/79 held
   **1.8 s and 0.0 s**. If the 2–26 Hz anti-damping lives in the **plant**, no firmware lever can
   remove it. ~15–20 min, no firmware needed.
2. **Ask whether V91 was actually flashed** before treating route 78 as a V91 measurement.
3. **Grep the kit before naming a cause for a null.**
4. **Do not propose a detent/dwell lever**, and do not re-fly `byte7 b6` without resolving its map.
5. **Do not re-raise `0xCBE74`** — it is an inertia term and cannot damp.
