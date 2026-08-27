---
name: reference_accord_v75_step_size_hypothesis_refuted_and_fun347b8_precise_trigger
description: Tests H ("V75's stoplight-launch fault is a per-cycle step-size/slew trip, not magnitude") against the governor slew-STEP and FUN_00045a20 -- both REFUTED with margin. Fresh disasm of FUN_000347b8 pins its EXACT trigger condition (a one-sided ceiling-shrink check, not a generic +-5ct mismatch), which requires gp-0x6ac0 near FactorE's X3=4000 (849 deg/s) -- 2.57x beyond route-5d's measured 330 deg/s max -- for V75's specific CY0/EX1 edit to matter. Closed-form correction: the "2.72x V75/V74" dose ratio is a LOCAL-SLOPE number valid only for deltaR<=200ct; in the saturated/plateau regime the ratio collapses to 566/429=1.32x.
metadata:
  type: reference
---

Built 2026-08-06, testing the V75 stoplight-launch incident's step-size hypothesis (H). Program:
`code.bin` (stock, confirmed via `list_open_programs` before starting). Method: decompile-first, then
disasm to pin exact conditions; every cal cross-checked with fresh `read_memory`; the Q10 damper chain
independently re-implemented in Python and validated against `builds/v50_v79/build_v75_tva.py`'s own asserted
`LIVE_EXPECT` constants (`dose_old=50, dose=137, dose_69hz=181` at `BURST_RATE=99/127`) -- exact match,
confirming the model.

## FUN_00045a20 -- fresh decompile, byte-confirmed constants [EVIDENCE]
Re-derives [[reference_accord_hard_shutdown_full_map_v75_incident]]'s account exactly; adds byte reads:
- `tp+0x7610/0x7614/0x7618/0x761c` = `0xC6610/14/18/1C`, fresh `read_memory`: floats `350.0, 410.0,
  5000.0, 400.0` -- confirms `X=[350,410] Y=[5000,400]` LERP on `fVar5=gp-0x6a10*0.1`.
- `tp+0x702c=0xC602C`, fresh `read_memory`: bytes `00 00 A0 40` = **5.0** (float). This is the WIDE
  tolerance; the function's TIGHT tolerance is a hardcoded literal `0.001` (≈1 raw count in the /1024
  domain). **Refined reading**: when `|gp-0x6abe| < fVar4` (the LERP'd reference, which is huge — 5000 —
  whenever tracking error is small, so this is the COMMON case), the bound on `comp=(gp-0x6acc-
  gp-0x6ace)/1024` is `±0.001` (≈±1 count) — comp must be near-exactly zero. Only when `|gp-0x6abe| >=
  fVar4` does the bound widen to `±(5.0+0.001)` (≈±5121 counts).
- **`comp` is `FUN_000456a4`'s post-governor compensation ADD term (`gp-0x6acc-gp-0x6ace`), computed from
  a SEPARATE LERP on `gp-0x6a10`/`gp-0x6ac0`. It does NOT reference `gp-0x6bd0` anywhere in its own
  arithmetic.** No direct code dependency exists between the damper (V75's lever) and this monitor.
  ⇒ **RULED OUT as a direct trigger for V75's specific edit** — only a long, physically-mediated chain
  (damper perturbs steering -> perturbs gp-0x6a10 -> shifts this monitor's own inputs) could connect them,
  not independently verified.

## Governor slew-STEP selector -- fresh disasm + byte reads, REFUTED as V75's differentiator [EVIDENCE]
Fresh `disassemble_function(0x4503c)` confirms [[reference-accord-governor-energy-budget-and-step-selector]]
exactly, byte-for-byte: `0x45410 ld.hu 0x7206,tp,r16` (STEP=cal `0xC6206`) / `0x45416 ld.hu 0x7208,tp,r16`
(STEP=cal `0xC6208`), selected by `gp-0x67f5==0`. Fresh `read_memory(0xC6206,4)` = bytes `00 02 CD 00` ->
**`0xC6206=512` (FAST), `0xC6208=205` (SLOW)** — exact match. `0xC531E` fresh-read = **1062** (bytes
`26 04`, u16 LE) — the driver-torque-voted threshold, matches memory.
`get_function_callers(0x4503c)` = `FUN_0002214a` only — **the governor runs at 1000 Hz** (task1), while
`gp-0x6bd0` (per `get_function_callers(0x34350)` in a prior session, triple-confirmed) updates once per
10 governor cycles (**100 Hz**, task5). So a `gp-0x6bd0` step appears to the governor as a single-1kHz-
cycle jump in its TARGET (`gp-0x6b94`, since the aggregator sums `gp-0x6bd0` with unity coefficient,
range-gated ±2048 inclusive, per [[reference_accord_v75_ceiling_c77a0_noclip_asymmetry_and_aggregator_inclusive_bound]]).

**The numbers** (Python mirror of `FUN_00034350`'s exact Q10 chain, B=D=1024 asserted flat on engaged
modes, validated against `builds/v50_v79/build_v75_tva.py`'s own `LIVE_EXPECT`):
```
mode 26, SPEED=0 (stoplight/creep -- FactorC is flat at Y[0] for ALL speed<2240ct=35km/h, so the WHOLE
launch sits on FactorC's floor value; speed contributes ZERO per-cycle variation during a launch):
  deltaR(ct)  V74   V75   ratio | note
       50      21    59  2.81x | both in linear ramp
      100      51   139  2.73x | both in linear ramp
      200     109   297  2.72x | both in linear ramp (V75's ramp ends exactly here, X1=200)
      353     198   297  1.50x | V75 SATURATED (flat 539 plateau), V74 still ramping (X1=400)
      400     225   297  1.32x | BOTH saturated
     1555     225   297  1.32x | BOTH saturated (route-5d's own measured max column rate, 330 deg/s)
     4000     388   512  1.32x | BOTH saturated at FactorE's OWN X3 -- V75 lands EXACTLY on the 512
                                 ceiling floor (566*927>>10=512.4->512, matches builds/v50_v79/build_v75_tva.py's own
                                 "touches the floor by construction" statement)
```
**Max single-100Hz-cycle `|Δgp-0x6bd0|` achievable by EITHER build, at ANY rate swing up to and including
route-5d's measured max (1555ct/330deg/s), is 225 (V74) / 297 (V75).** Both are comfortably under
STEP_FAST (512). Both exceed STEP_SLOW (205) — V74 by only 20 counts, V75 by 92 — **but per
[[reference-accord-governor-energy-budget-and-step-selector]]'s own §4b finding (FUN_0004595a, the only
monitor comparing `gp-0x6ace` OUTPUT against `gp-0x6b94` TARGET), OUTPUT LAGGING TARGET is explicitly
TOLERATED — the monitor only faults on OUTPUT EXCEEDING TARGET or opposite-sign. A bigger SLOW-mode lag is
a difference of DEGREE (V75 takes ~1-2 cycles longer to converge), not a threshold V75 uniquely crosses
into fault territory — V74 ALREADY produces a smaller instance of the identical, tolerated condition.**
**⇒ THE GOVERNOR SLEW-STEP BOUND IS REFUTED as V75's differentiating fault mechanism, with margin, even
under the maximally generous assumption that the full measured 330deg/s rate swing occurs within a single
100Hz tick.**

## Closed-form correction: the "2.72x" dose ratio is LOCAL-SLOPE ONLY, not a swing-independent constant
`FactorE` Y is IDENTICAL between V74 and V75 (`[0,539,539,927]`) — only the X breakpoint moved
(`X1: 400->200`). **In the saturated/plateau regime (rate>=400ct, i.e. >=84.9 deg/s — well within
route-5d's measured envelope), the ratio collapses to a closed form: `V75/V74 = C_Y0_V75/C_Y0_V74 =
566/429 = 1.319x`**, independent of rate, because both builds' `FactorE` output equals the SAME `539` (or
converges toward the SAME `927` at X3) and only the `FactorC[0]` multiplier differs. **The 2.72x figure is
real but applies ONLY to the local derivative / small-swing regime (`deltaR<=200ct ≈42.4 deg/s` in one
100Hz tick, i.e. angular acceleration <=4240 deg/s²)** — a regime that is real dynamically (governs how
FAST the two builds' damper output RISES) but does not describe the TOTAL achievable one-cycle jump, which
saturates well below 2.72x. This is a genuine, previously-unstated refinement of the task brief's own
"2.72x" framing — both are correct, for different quantities (local slope vs total swing).

## FUN_000347b8 -- fresh disasm, PRECISE trigger condition pinned (refines [[reference_accord_gp6bd0_damper_own_ceiling_consistency_monitor_fun347b8]])
Full disasm `0x347b8-0x348dc`. The comparison is **NOT** a symmetric "fVar5 vs fVar6 mismatch" as the
inherited paraphrase suggested — it is a genuine **CLAMP re-computation**:
```
r26 = clamp(fVar5, -fVar6, +fVar6)      ; fVar5=gp-0x6bd0/1024 (already stored); fVar6=T2-resampled ceiling
if |fVar5 - r26| > 5/1024: FAULT         ; (0x34882-0x3488c: cmovne + negf.s + maxf.s implement the clamp)
```
**Consequence, worked through explicitly**: if `fVar5` already sits inside `[-fVar6,+fVar6]` (T2's
resampled bound), `r26=fVar5` exactly, the difference is 0, and the check ALWAYS PASSES — **regardless of
what T1's ceiling was, and regardless of whether T2's ceiling GREW relative to T1's.** The check can only
fire when `fVar5` (the value already computed/clamped at T1) EXCEEDS T2's freshly-resampled bound — which
requires the ceiling to have SHRUNK between T1 and T2 while `gp-0x6bd0` was pinned near T1's LARGER value.
**⇒ Retracts my own initial "undershoot during a strengthening backdrive event" hypothesis — a GROWING
ceiling cannot trip this check (the newly-larger bound only makes the existing value MORE comfortably
in-range).**

Since the ceiling table's floor is 512 (the LERP clamps flat at `Y[0]=512` for `gp-0x6ac2<X[0]=300`,
fresh-confirmed: `0xC6158=512` fallback, matches `Y[0]`), the ceiling **cannot shrink below 512** — so for
a >5-count fault, `gp-0x6bd0` must have been sitting ABOVE ~517 at T1 (i.e. `gp-0x6ac2` was into its ramp,
ceiling>512, at T1), then the ceiling snapped back toward 512 by T2. **`gp-0x6bd0` reaching >517 in the
creep/low-speed regime (speed<35km/h, the WHOLE stoplight-launch window) requires `gp-0x6ac0` near
FactorE's own `X3=4000ct` (≈849 deg/s)** — per the table above, V75's plateau (297) and even V74's (225)
sit far below 517 everywhere up through route-5d's own measured max (1555ct/330deg/s); only the extreme
4000ct corner reaches it (V75=512 exactly there, V74=388, a genuine 124-count margin difference).
**⇒ This mechanism is real and DOES differentiate V74 from V75, but ONLY at a rate regime (≈849 deg/s)
2.57x beyond anything measured on route 5d — not established as reachable during an ordinary stoplight
launch.** [BELIEF for "ordinary launch reaches this," unresolved either way]

## Verdict on H
**H as literally stated (Δgp-0x6bd0 vs the governor STEP, or vs FUN_00045a20's bound) is REFUTED**, with
quantified margin, even under the most generous swing assumption (full 330 deg/s route-5d max reached in
one 100Hz cycle). **A refined sibling hypothesis H′ (FUN_000347b8's ceiling-shrink cross-check) remains
live and IS a genuine V74-vs-V75 differentiator, but its own precondition (`gp-0x6ac0`≈849 deg/s) is not
established as reachable in an ordinary launch** — it would require either an extreme, non-driver-typical
rate transient (a sudden LKAS correction independent of the driver's gentle input, or a static-friction
breakaway spike) at the exact moment of launch, which is plausible but NOT confirmed from firmware bytes
alone. See open items below.

## Open items / what would settle it
1. Whether `gp-0x6ac0`/`gp-0x6ac2` genuinely reach ≈4000ct (849 deg/s) during a real stoplight-launch
   breakaway transient — not measurable from firmware bytes; needs on-car telemetry of `gp-0x6ac0` (or a
   proxy) captured through an actual launch, ideally including the first ~200ms after the wheels start
   turning.
2. Whether `FUN_0002214a` (task1, 1kHz) can preempt `FUN_00022ca0` (task5, 100Hz) mid-execution between
   `FUN_00034350`'s and `FUN_000347b8`'s back-to-back calls — decisive for whether T1 and T2 can ever
   actually see different `gp-0x6ac2` values in practice. Inherited as OPEN from
   [[reference_accord_gp6bd0_damper_own_ceiling_consistency_monitor_fun347b8]], not resolved this session
   (would need RTOS scheduler/interrupt-priority decompile, not attempted).
3. `FUN_00045a20`'s indirect (physically-mediated) link to the damper via `gp-0x6a10` was named but not
   quantified — would need a closed-loop model of how much `gp-0x6bd0`'s change perturbs tracking error.

## Related
[[reference_accord_hard_shutdown_full_map_v75_incident]] — FUN_00045a20's original decompile (matches).
[[reference_accord_gp6bd0_damper_own_ceiling_consistency_monitor_fun347b8]] — FUN_000347b8's original
account, REFINED (not contradicted) by this session's fresh disasm of the exact clamp/compare logic.
[[reference-accord-governor-energy-budget-and-step-selector]] — STEP selector and FUN_0004595a's
lag-tolerant behavior, both re-confirmed fresh and applied quantitatively here.
[[reference_accord_v75_true_headroom_e_exhausted_c_max_566]], [[reference_accord_v75_ceiling_c77a0_noclip_asymmetry_and_aggregator_inclusive_bound]] — source tables (FactorC/E, ceiling) this session's Python
mirror reproduces exactly against `builds/v50_v79/build_v75_tva.py`'s own `LIVE_EXPECT` assertions.
[[reference_accord_gp6ac2_is_backdrive_rate_not_gp6ac0_twin]] — gp-0x6ac2's identity, used throughout.
