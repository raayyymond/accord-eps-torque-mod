---
name: reference-accord-fun456a4-gate-no-hysteresis-and-index-identity
description: FUN_000456a4's zero-forcing gate is a bare unhysteretic compare (0->2560 in one cycle) and gp-0x6ad0 is a dead telemetry mirror -- true structural facts -- but gp-0x6a10 (its index) is angle/driver-torque-derived, NOT command-derived, so V38's 4x gain doesn't move its operating point: DEPRIORITIZED as a V38-vs-stock regression candidate as of 2026-07-19.
metadata:
  type: reference
---

# FUN_000456a4 chatter-source audit — Accord TVA-A160 (2026-07-19)

Requested by team-lead investigating the tens-of-Hz vibration felt at low speed under LKAS command
(post-V38 4x raise). See [[reference-accord-post-governor-comp-add]] for the node's position in the
chain (`gp-0x6ace -> FUN_000456a4 -> gp-0x6acc -> shaper`). This memory holds the byte-level detail.

## The gate — exact instructions [VERIFIED]

```
00045780: e4 37 41 95   ld.hu -0x6ac0[gp],r6      ; r6 = RATE = gp-0x6ac0 (fresh load, every call)
00045784: cf 00         zxh r15                     ; r15 = LERP1(INDEX) result
00045786: e6 79         cmp r6,r15                  ; flags = r15 - r6 (unsigned)
00045788: b1 05         bc 0x0004578e                ; CY=1 (LERP1<RATE) -> continue nonzero-term path
0004578a: 80 07 2c 01   jr 0x000458b6                ; else -> unconditional jump to term=0 (mov 0x0,r6)
```

**No hysteresis of any kind.** Both operands are recomputed from scratch every single call: `gp-0x6ac0`
is loaded live at 0x45780 (no filtered/averaged copy consumed anywhere in this function), and
LERP1(INDEX) is walked fresh starting at 0x45716. There is no second threshold on the release path
(same single compare governs both directions), no counter/dwell, no persisted latch bit. This is a
bare unhysteretic flip-flop by construction — same category of finding as the SM1/SM2 monitor
thresholds, except those at least have escalating counters; this one has none.

## Term math — exact [VERIFIED]

```
000457de: ld.hu 0x7204,tp,r15    ; r15 = cal 0xC6204 = 3072 (gain)
000457e2: sub r12,r6              ; r6 = RATE - LERP1(INDEX)
000457f2: mulu r15,r6,r0          ; r6 = (RATE-LERP1) * 3072
000457fc: shr 0xa,r6              ; r6 >>= 10   =>  term_raw = (RATE-LERP1) * 3   [exact integer factor]
...
00045850: cmp r6,r10               ; r10 = LERP2(INDEX)
00045852: bnc 0x000458a6           ; keep term_raw if <= LERP2(INDEX), else clamp down to LERP2(INDEX)
```

## Full LERP table contents [VERIFIED — read directly from code.bin]

**LERP1** (threshold vs RATE), base `tp+0x7830` = 0xC6830, raw bytes `03 00 D8 0E A0 0F 36 10 88 13 DD 0B E8 03 00 00`:

| cal addr | value | role |
|---|---|---|
| 0xC6832 | 3800 | X0 (LOW) |
| 0xC6834 | 4000 | X1 |
| 0xC6836 | 4150 | X2/HIGH |
| 0xC6838 | 5000 | Y0 |
| 0xC683A | 3037 | Y1 |
| 0xC683C | 1000 | Y2/ceiling |

FALLING curve: 5000 at INDEX≤3800 down to 1000 at INDEX≥4150. This is a 3-point table (the earlier
memory only listed the 0xC6834/0xC6838 pair — corrected here with the full 3 breakpoints).

**LERP2** (MIN-clamp on the term), base `tp+0x77d0` = 0xC67D0, raw bytes `03 00 80 0C D8 0E 36 10 00 02 00 04 00 0A 00 00`:

| cal addr | value | role |
|---|---|---|
| 0xC67D2 | 3200 | X0 (LOW) |
| 0xC67D4 | 3800 | X1 |
| 0xC67D6 | 4150 | X2/HIGH |
| 0xC67D8 | 512 | Y0/floor |
| 0xC67DA | 1024 | Y1 |
| 0xC67DC | 2560 | Y2/ceiling |

RISING curve: 512 at INDEX≤3200 up to 2560 at INDEX≥4150. Matches prior memory's floor(512)/ceiling(2560)
exactly, middle point (1024@3800) newly confirmed.

Gain `0xC6204` = 3072 (2 bytes `00 0C`), sole read at 0x457de.

## gp-0x6ad0 (term mirror) is a fully dead telemetry sink [VERIFIED]

Exhaustive text search across all 185,693 instructions in the image for any operand referencing
`6ad0` returns **exactly one match total**: the write itself at `0x458c4: st.h r6,-0x6ad0,gp`.
Zero other readers, zero other writers, anywhere. And the sum that matters doesn't even go through it:

```
000458bc: ld.h -0x6ace[gp],r12   ; governor output
000458c4: st.h r6,-0x6ad0,gp     ; mirror to dead telemetry sink
000458c8: add r6,r12             ; SAME r6, same cycle -> summed directly into governor output
```

The term can step from 0 to its full clamped magnitude in a single control cycle at the sum — nothing
filters, ramps, or delays it between computation and application.

## gp-0x6a10 (INDEX) is NOT a filtered copy of gp-0x6ac0 (motor rate) [VERIFIED, one hop short of full ID]

Sole non-zeroing producer: `FUN_0003fc16`. Structure:

```c
if (gp-0x67fe == 1 || gp-0x67fe == 2) {           // ENGAGED/HOLDING substate
    uVar7 = clamp(gp-0x69e0 + const, ±(tp+0x733a));
    sVar6 = gp-0x69ca - uVar7;
    gp-0x6a10 = min( abs(sVar6), <ceiling> );      // FUN_00049a5a=abs(), FUN_00049a78=min()
} else {
    gp-0x6a10 = 0;                                  // zeroed whenever not engaged/holding
}
```

`FUN_00049a5a` = generic `abs(int)` (24 callers image-wide: governor, angle-deadband FUN_0003c7fc,
decider FUN_00040d58, LKAS mixer functions, etc — a shared utility, not rate-specific).
`FUN_00049a78(a,b)` = generic `min(a,b)`.

`gp-0x69ca` is written across the engage-state-machine function cluster (FUN_0003bd7c, FUN_0003e462,
FUN_0003e6d8, FUN_0003e760, FUN_0003f884, FUN_0003fd9c — the same 0x3bxxx-0x3fxxx range already mapped
as the LKAS engage SM, see [[reference-accord-engage-sm-full-dispatcher-and-trump-exits]]).
`gp-0x69e0`'s sole writer is FUN_0003f884, same cluster.

`gp-0x6ac0` (RATE), by contrast, comes from `FUN_00041464` (the resolver/FOC electrical-rate chain,
[[reference-accord-c520c-cap-table-axis-provenance]]). **Different producer, different upstream
variables, no shared filter or call path.** The self-referential worry (index = lagged copy of the
gated signal) is refuted at the direct level.

**[OPEN]**: what `gp-0x69ca`/`gp-0x69e0` physically represent beyond "engage-SM domain, plausibly an
angle/torque setpoint tracking-error term" is not traced — would need one more hop into
`FUN_0003bd7c`/`FUN_0003f884`.

## ✅ RESOLVED 2026-07-19 — gp-0x69ca/gp-0x69e0 are angle+driver-torque derived, NOT command-derived

Full decompile of both producers (`FUN_0003bd7c` for `gp-0x69ca`, `FUN_0003f884` for `gp-0x69e0`),
requested by team-lead to test one specific question: **does the LKAS command move this gate's
operating point, in a way that would make V38's 4x gain + quartered-PID invariance argument not
apply?**

Both functions build their output from a **36000-scale steering angle/position accumulator cluster**
(`gp-0x69d0/d2/d4/de`, `gp-0x69c8`, `gp-0x6cc0`, `gp-0x6cdc`, `gp-0x35f4` — the literal `36000` scale
recurs, e.g. `iVar15 = sVar14 * 36000` in `FUN_0003f884`, consistent with a centidegree-style angle
representation), gated by the **FOC-mode/engage state machine** (`gp-0x6772`, `gp-0x67fe`, `gp-0x671d`),
and — in `FUN_0003f884` specifically — **driver hand torque** `gp-0x4f60` (already established
elsewhere in this kit as Sensor-B *driver column* torque, a sensor reading, not a command term).

I read every line of both decompiles for any reference to the LKAS command chain — `gp-0x69ae`
(setpoint), `gp-0x6b3c` (arb output), `gp-0x6b4c` (LKAS lane), `gp-0x6b94` (aggregator), `gp-0x6ace`
(governed demand), `gp-0x6b98` (final command). **None appear anywhere in either function.**

**Verdict: `gp-0x6a10` (hence `LERP1(gp-0x6a10)`, the gate threshold) sits entirely upstream of and
structurally independent from the LKAS gain `0xC646C`, the aggregator, the governor, and the shaper.**
Quartering the PID and 4x'ing the gain should not move this gate's operating point for the same
physical driving input — no firmware-level bypass of the invariance argument exists here. (One
honest caveat, not a loophole: `gp-0x69ca`/`gp-0x69e0` track physical steering *angle*, and angle is a
physical consequence of delivered torque a moment later — but that indirect physical feedback loop is
identical in kind to the "physical torque should match" premise the invariance argument already rests
on, not a firmware-level escape from it.)

## gp-0x67fe (engage/holding gate) toggle rate — settles once per drive, not a fast oscillator

Exhaustive search: `gp-0x67fe`'s only writers are 4 `st.b` sites, all inside `FUN_0003bd7c`
(`0x3bdb8`, `0x3be4e`, `0x3be5a`, `0x3be7a`). Decompiled the gating logic: it transitions to 1 or 2
only when the **FOC-mode byte** `gp-0x6772` reaches 4 or 5 AND a diagnostic check
(`FUN_00046ea6(8)==0`) AND a startup-dwell counter (`gp-0x671d < cal(tp+0x7500)`) all pass, behind a
**sticky latch** (`gp-0x6845`) that only clears when FOC-mode drops back below 4 (a full reset). This
is a motor-controller-readiness state machine that settles once at the start of a drive cycle
(calibration → running) and stays put. **[INFERRED, structural]** — not runtime-confirmed, but nothing
in the gating logic is keyed to a per-cycle signal; nobody has evidence of a fault-recovery loop that
would flip it at control-loop rate.

## ⚠ REGRESSION VERDICT — the reasoning pattern to keep, separate from the mechanics

**`FUN_000456a4`'s gate mechanics above are true and will be needed again: a real, unhysteretic,
0→2560-in-one-cycle mechanism with no dwell, no filter, no debounce.** That description does not
change. But **the regression argument built on top of it did not survive**, and the two must not be
conflated going forward:

> **A real, ugly, unhysteretic mechanism is not automatically the cause of a regression — it also has
> to have CHANGED.** `FUN_000456a4` is genuinely nasty. It is still not V38's bug, because nothing V38
> did (4x gain `0xC646C`, quartered openpilot PID) moves this gate's operating point — both of its
> inputs are angle/driver-torque/mode-state signals, structurally upstream of and independent from the
> command chain the gain sits in.

**Do not resurrect this candidate on the strength of the mechanics alone.** If it resurfaces, the
question to ask first is not "is this gate scary" (yes) but "did V38 change what feeds this gate"
(no, per this trace) — re-derive from `gp-0x69ca`/`gp-0x69e0`'s producers above rather than re-reading
the gate bytes, since the gate bytes were never in dispute.

**Deprioritized as a V38-vs-stock regression candidate as of 2026-07-19.**

## Side-finding: gp-0x6ac0 may be a stored magnitude, not the signed rate [INFERRED, not confirmed]

Every one of gp-0x6ac0's ~23 read sites image-wide uses `ld.hu` (unsigned), zero `ld.h` exceptions.
Its sign companion `gp-0x6abe` is written only by the same producer (FUN_00041464) and is always read
`ld.h` (signed) at all ~15 of its sites. Classic magnitude+sign producer pattern. If true, the existing
"gp-0x6ac0 clamped ±13000" note in the constellation describes the *signed physical quantity* upstream
of a magnitude-extraction step inside FUN_00041464, not literally what lands in gp-0x6ac0. Did **not**
decompile FUN_00041464's store logic to confirm this in this session — flagging for whoever next
touches that chain.

## Worked magnitude example [VERIFIED mechanics, INFERRED real-world applicability]

At INDEX=4000 (exact breakpoint): LERP1(4000)=3037, LERP2(4000) interpolates to 1024+(1536*200/350)=1901
(integer `divq` truncation).

- RATE steps 3030->3200 in one cycle (gate just opens): term_raw=(3200-3037)*3=489, under clamp -> **term jumps 0->489**.
- RATE steps 3030->4200 in one cycle: term_raw=(4200-3037)*3=3489, clamped to 1901 -> **term jumps 0->1901**
  (bigger than V38's ~1782-count primary LKAS lane on its own).
- Absolute ceiling (INDEX>=4150, RATE>>1000): **term can hit 2560** from a standing start of 0 in a
  single cycle — ~44% bigger than the 1782-count primary lane.

No live telemetry available to confirm RATE/INDEX actually cross this boundary noisily during the
reported low-speed vibration — this is the mechanism's *capability*, not a confirmed trigger.

## Mitigation candidates — all exclusive to this one function [VERIFIED, exhaustive]

Whole-image literal-operand search (185,693 instructions) found **zero consumers outside
FUN_000456a4** for every LERP1/LERP2 boundary cal and the gain: 0xC6830/32/36/38/3C (LERP1),
0xC67D0/D2/D6/D8/DC (LERP2), 0xC6204 (gain). Each has exactly one literal reference in the whole
firmware — the instruction inside this function. This is about as clean a blast radius as this kit
ever gets for a cal edit.

Ranked recommendation:
1. Lower 0xC67DC (LERP2 ceiling, 2560) and/or 0xC67DA/0xC67D8 — caps worst-case single-cycle injection
   directly without touching when the gate fires.
2. Raise 0xC6832/34/36 (LERP1 X) and/or 0xC6838/3A/3C (LERP1 Y) — requires a bigger RATE margin before
   the gate opens, reduces false-trigger likelihood on rate noise; doesn't address the gate's lack of
   dwell itself.
3. Lowering 0xC6204 (gain) scales term_raw down uniformly but doesn't cap the LERP2-clamped worst case
   once RATE-LERP1 is large — weaker lever than (1).

Do not recommend disabling the gate outright: its structure (opens more easily as tracking-error INDEX
rises, i.e. more permissive when the motor is off-target) reads like an overspeed/back-EMF-style
corrective term, not a cosmetic return-to-center aid — plausibly safety-adjacent.

## Float-monitor polarity check (2026-07-19, low-priority follow-up) — CONFIRMED mismatch, but not the lockstep-fault class

Team-lead asked whether `FUN_00043e44`'s float sanitize of `gp-0x6acc` at `0x44696` matches the
shaper's (`FUN_00042af8`) one-sided int gate found above, given int/float asymmetries have hard-faulted
this ECU before (V24-V27). Disassembled `0x4467a-0x446b8`:

```
0004467a: ld.h -0x6acc,gp,r16          ; r16 = gp-0x6acc, SIGNED
0004467e: cvtf.ws r16,r13               ; float(r16)
00044682: cvtf.sd r13,r10r11            ; -> double
00044686: movhi 0x3f50,r0,r13           ; double const = 2^-10 = 1/1024
0004468c: mulf.d r12r13,r10r11,r12r13   ; scaled = gp-0x6acc / 1024
00044692: movhi 0x4020,r0,r11           ; double const = 8.0
00044696: cmpf.d lt,r10r11,r12r13,0x1   ; is 8.0 < scaled?
0004469e: be 0x000446b8                 ; TRUE -> mov r0,r16  (ZERO — matches int side's positive check)
000446a0: movhi -0x3fe0,r0,r11          ; double const = -8.0 (0xc0200000_00000000)
000446a4: cmpf.d lt,r12r13,r10r11,0x2   ; is scaled < -8.0?
000446ac: be 0x000446b8                 ; TRUE -> ALSO zero    (NO int-side equivalent!)
```

**The float side is genuinely SYMMETRIC (±8.0, i.e. ±8192): it zeroes on EITHER `gp-0x6acc > 8192` OR
`gp-0x6acc < -8192`. The int side (this file + [[reference-accord-shaper-fun42af8]]) is confirmed
ONE-SIDED: it only zeroes `gp-0x6acc > 8192`, and passes an arbitrarily negative value through
unmodified.** This is a real, verified polarity mismatch between the two functions' treatment of
"implausible gp-0x6acc." **[VERIFIED]**, both sides read at instruction level this session.

**What this is NOT, based on what I traced:** this is not confirmed to be the same class of risk as
the V24-V27 corridor/boost lockstep brick mechanism. That mechanism is an explicit same-cycle
int-vs-float REDUNDANCY CHECK with a fault path on divergence (`reference/firmware/reference_accord_watchdog_fault_sm_fun43e44.md`
in the project-level `memory/` dir documents this precisely for the `±5/1024` wall compare at
`0x4463a`, which is a genuine matched pair with a debounced fault trip). **The ±8192/±8.0 sanitize
pair traced here is structurally different**: the int side's zero-gate result (`gp-0x6b08`) is a LOCAL
working variable consumed only within `FUN_00042af8`'s own rate-shaping math; the float side's result
(`r16`) is a LOCAL working variable consumed only within `FUN_00043e44`'s own downstream mode-dispatch
computation (continuing toward one of the 7 weighted plausibility flags documented in the project-level
memory above — I did not trace which specific flag). **I found no direct compare-and-fault between
these two specific zero-gated values** — they are two independent "sanitize gp-0x6acc before I use it"
idioms on the same upstream variable, not a matched redundancy pair with its own fault trip.

**Practical implication, stated carefully:** if `gp-0x6acc` sustains below -8192, the shaper's internal
rate-shaping math (via `gp-0x6b08`) would use that raw negative value un-sanitized, while the float
monitor would independently treat it as implausible (zeroed) for whatever flag its `r16` result feeds.
Whether that divergence in TREATMENT (not a direct value compare) could indirectly perturb one of the
monitor's 7 weighted flags in a way that trips the debounced hard-shutdown is **[OPEN]** — would need
tracing `r16`'s downstream use past `0x446b8` into the flag computation to settle. Given `gp-0x6acc`'s
verified maximum magnitude is 7322 (Q7 finding below) and the shaper's SEPARATE late-stage clamp
(`reference-accord-shaper-fun42af8`'s Clamp #7, ±0x2000 saturating) bounds the delivered command
regardless, this is a lower-priority thread than the reachability question it doesn't affect — but it
is a real, previously-undocumented structural asymmetry between two functions that a future session
should not assume are mirror-matched just because their nominal magnitude (8192/1024=8.0) coincides.

## Downstream cliff check (Q7 addendum, 2026-07-19) — not reachable at the verified maximum

The compensation term's output `gp-0x6ad0` sums into `gp-0x6acc` (`= gp-0x6ace + gp-0x6ad0`), which
feeds a **one-sided** zero-gate in the shaper — see the 2026-07-19 correction in
[[reference-accord-shaper-fun42af8]] (NOT a symmetric ±8192 window as an earlier restatement had it).
Worked the full margin this session: `max|gp-0x6ace| = 4762` (now VERIFIED, see
[[reference-accord-gp4f64-three-consumers]]) `+ max|gp-0x6ad0| = 2560` (this file's own LERP2 ceiling,
hard-clamped, no extrapolation) `= 7322 < 8192`. **The 870-count margin holds** — this specific
zero-cliff is not reachable via the additive chain even at both terms' independently-verified maxima.

## Related
- [[reference-accord-post-governor-comp-add]] — this node's position in the LKAS delivery chain
- [[reference-accord-c520c-cap-table-axis-provenance]] — gp-0x6ac0's producer chain (FUN_00041464)
- [[reference-accord-engage-sm-full-dispatcher-and-trump-exits]] — the 0x3bxxx-0x3fxxx cluster that
  produces gp-0x69ca/gp-0x69e0 (INDEX's real upstream)
- [[reference-accord-lkas-only-rate-limiter-c6194]] — prior finding that there's no live LKAS-specific
  slew limit; this term is likewise unfiltered on its own output
- [[reference-accord-generic-math-helpers-49a5a-49a78-49a90]] — abs()/min()/clamp() helper identities
  used throughout this trace and the governor's Q15-bound chain
