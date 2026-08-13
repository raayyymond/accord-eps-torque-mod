---
name: reference-accord-fun38148-task-gate-and-c63ac-pole
description: FUN_00038148 (Stage-1 accumulator gp-0x374c + residual->gp-0x6b70) shares its guard byte-for-byte with the assist mixer FUN_00026c80, so "no assist" is the only way it is dead; 0xC63AC census and the residual-LERP origin, both re-derived 2026-08-12.
metadata:
  type: reference
---

Traced 2026-08-12 to test whether V97 (`0xC63AC` 102→150) was inert. Verdict: **LIVE.**

## The scheduling gate — the reusable fact

`FUN_00038148` has **exactly one caller**: `FUN_0002214a` @`0x22676`. `FUN_0002214a` is an **RTOS task
entry**, not a called function — its address appears once as a literal at `0xBB928` in a 7-record task
table (`0x2214A`, `0x22A88`, `0x22B20`, `0x22B24`, `0x22CA0`, `0x2351E`, `0x14C5C`; fields =
TCB ptr, `(id<<16)|(prio<<8)|7`, entry, stack top, size). `get_function_callers` returns **nothing** for
any of them — that is correct, not a tool zero.

```
0002214e ld.bu -0x67fa[gp],r13 ; 22172 andi 0xf,r13,r15 ; 2217c shl r15,r11,r25
000221d6 andi 0x830,r25,r28     ; r28 != 0  <=>  gp-0x67fa in {4,5,11}
000221ca andi 0xd38,r25,r27  ·  000221f8 andi 0xd30,r25,r23  ·  0002269a andi 0xc30,r25,r22
```

🛑 **`r28` (`0x830`) guards BOTH `FUN_00026c80` (the assist-channel mixer, @`0x225F6`) and
`FUN_00038148` (@`0x22676`), plus `FUN_0003b8f6`, `FUN_0002caa2`, `FUN_00027b0a`, `FUN_0002EDA8`.**
⇒ **If any of these is dead, the car has no power assist at all.** Use this as the liveness argument
for the whole observer/mixer group — it beats a speed/mode argument, and `gp-0x67fa` is the **EPS's own
state, independent of LKAS engagement**, so the group is live in manual driving too.

⚠ The **task rate is still NOT pinned.** The task table has **no period field**; activation is by
event/ISR. `gp-0x6d28` is incremented once per invocation at `0x22162` — the cheapest instrument.
Every phase figure in the V97 rationale scales with it (fs 500/1000/2000 → lead +11.3/+7.82/+4.34° at
7.79 Hz). See [[reference-accord-observer-filter-mismatch-leaks-the-command]].

## The lane, mirrored

```
sum6   = SUM_i (lane_i * inrange(lane_i, LIM_i) * cal_i) >> 10
         gp-0x6b4e/0xC63A8/±0x2800 · gp-0x6b4c/0xC63AA/±0x2800 · gp-0x6b26/0xC63A6/±0x400
         gp-0x6b46/0xC63A4/±0x400  · gp-0x6bd0/0xC63A0/±0x800  · gp-0x6bbe/0xC63A2/±0x800
         ALL SIX cals = 1024 (unity) in stock.  in-range FAIL ZEROES the lane (not a clamp).
target = ((sum6 * polarity(gp-0x6752) * cal(0xC6468=2639, ×2.577)) >> 10) * 16
gp-0x374c += ((target - gp-0x374c) * cal(0xC63AC)) >> 10     # 0x381FE ld.w / 0x38202 ld.hu / 0x38230 st.w
model  = gp-0x374c >> 4                                       # 0x38236 sar 0x4,r6
resid  = gp-0x6bfe + gated(gp-0x6bfa,±20000) - model           # 0x38218 ld.h -0x6bfe[gp]
gp-0x6b70 = clamp(sign(resid) * LERP(|resid| * 0xC63AE>>10), ±0xC6200=8192)
```
🛑 **The accumulator update is UNCONDITIONAL — it precedes the `gp-0x6bfe ∈ ±20000` gate** whose
failure writes the `0x7FFF` sentinel. `gp-0x6bfe` has 1 writer (`FUN_0003bc20` @`0x3BC3E`, same task,
same `r28`, earlier at `0x22416`) and 1 reader.

## `0xC63AC` census — 1 reader / 0 writers, two tools, EMPTY set difference

Ghidra `search_instructions(operand="0x73ac")` → **1** hit. Python raw scan (ops `0x38`–`0x3F`, both
parities, **any** base reg) → 5 raw, **1 tp-based**; excluded: `0x6E73E` base **r4=gp** ⇒ `0xFEDFF3AC`
(RAM, not a cal — the classic gp/tp confusion), `0xBD682`/`0xBE9C2` above `0xBB000` (data),
`0x64642` mid-instruction misalignment. 6-byte extended form 0; `movea`/`movhi` imm `0x63AC` 0;
`ep`-aliasing: 98 `movea imm,tp,ep` sites, **0** in `sld` reach. Reproduces
[[reference-accord-v850-6byte-disp-decoder-corrected]]'s "run both, set-difference" rule.

## The residual LERP builder — `FUN_000389ec`

Runs in a **different, slower task** (`FUN_00022ca0`). Stores `*(gp-0x373c)=0`, `*(gp-0x3714)=0`,
build loop starts at index 1, then `X[0]←gp-0x373c` / `Y[0]←gp-0x3714` ⇒ **`X[0]=Y[0]=0`, the curve
passes through the ORIGIN, there is NO low-signal deadband.** Independently reproduces
[[reference-accord-residual-lerp-gp3714-runtime-adaptive]].
- `X[k>0]` are **divided** by a runtime factor, `Y[k>0]` **multiplied** by another — both
  `FUN_0003897a` rate-limited, bounded `[204,2048]` (`0xC639A/9C` lo, `0xC6390/92` hi, slew
  `0xC6394=1331`/`0xC639E=717`), inputs `gp-0x6982` and `gp-0x6984`. ⇒ **origin slope `f'` swings ≥10×
  and CANNOT be pinned statically.** `gp-0x6982`/`gp-0x6984` are the cells to trace next.
- ⚠ The builder's 60 km/h schedule (`cal 0xC62D8 = 3840`, `/64` km/h) gates only a **Y-floor whose
  cals `0xC617A`/`0xC617C` are BOTH ZERO in stock** ⇒ **inert**, not a creep dead zone. Do not read it
  as one.

## 🛑 The residual is a DIFFERENCE OF TWO ESTIMATES OF THE SAME QUANTITY

```
resid = (+1)*gp-0x6bfe + (+1)*gated(gp-0x6bfa) - (+1)*(gp-0x374c>>4)     # 0x38238 subr / 0x3823a add
```
Coefficient on the Path-2 term is **EXACTLY −1**, and `0xC63AE`=1024 so the LERP index is **exactly
`|resid|`** ⇒ `gp-0x6b70 = ±LERP(|resid|)`, no intervening scale.

`gp-0x6bfe` ← `gp-0x6bfc` ← **1 writer**, the last instruction of `FUN_0003b8f6` (`0x3BC1A`):
```
gp-0x6bfc = clamp( cal(0xC6468)=2639 * (MODEL_A - friction - inertia), ±20000 )
  MODEL_A = LPF2(gp-0x6b98 * polarity / 1024) + angle-scheduled-gain * clamp15(column terms)
```
🛑 **Branch A (`gp-0x6bfe`, from the FINAL MOTOR COMMAND, float, 2-stage IIR) and Branch B
(`gp-0x374c>>4`, from the SIX ASSIST LANES, integer, through the `0xC63AC` pole) are TWO ESTIMATES OF
THE SAME QUANTITY — same units, SAME cal `0xC6468`=2639.** The recorded "two filters on one signal"
structure, see [[reference-accord-observer-filter-mismatch-leaks-the-command]].
⇒ **NEVER estimate Path-2's share by comparing its measured ceiling against Branch A's ADMITTED RANGE
(±20000).** A difference of two *correlated* estimates is smaller than either, so the denominator is
the residual, not the range. That comparison produced a bogus "≤9 % ⇒ failure class E" verdict in the
2026-08-12 session and I rejected it. This is **not** the `0xC63A4` shape (that lane was summed
*alongside* others; this one enters a **difference** at coefficient −1, zero dilution).

**What the share actually depends on:** `|resid| p50 = gp-0x6b70 p50 / f'`. With route-0x80's
`gp-0x6b70` p50 ≈ 320 ct and `f' ∈ [0.1, 10]`, `|resid| p50 ∈ [32, 3200]` ct against a Path-2 term
admitted to 2048 ct ⇒ **capable of dominating. UNRESOLVED, not small.**
⊕ **The settling measurement:** re-scale the V96 cave regressor rung (34× over-range, LSB 2048 → ~128)
so V96's own **S1** (slope of `gp-0x6b70` on `gp-0x374c>>4`) becomes measurable. **S1 ≡ `f'`.**

## Both in-function gates are TAUTOLOGICAL
- **`gp-0x6bfa` ±20000 gate is DEAD.** Sole writer `FUN_00026c80` clamps on all three arms
  (`0x273AC` +20000, `0x273C4` −20000, `0x273D6` pass-through) ⇒ `gated(D) ≡ D`.
- **`0x38234 bnc → movea 0x7fff` is a RELAY.** `FUN_0003bc20` is a plausibility latch that already
  writes `gp-0x6bfe = 0x7FFF` + `gp-0x695c = 0xFFFF` on failure, so the branch fires *iff*
  `gp-0x6bfe == 0x7FFF`. Independently re-derives
  [[reference-accord-observer-gate-tautology-and-term-mismatch]].

## `gp-0x374c` magnitude — under the flown probe's floor

V96/V97 cave `Mhi`/`Mlo` (LSB 2048): `|gp-0x374c>>4| < 2048` on **10,749/10,749** route-0x80 frames,
and `M==1` on only 77/80,462 (7e) and 29/83,632 (7f). ⇒ the term's magnitude is **unresolved**, so any
dose computed through it is unsized until the rung is re-scaled (~×16 finer).
