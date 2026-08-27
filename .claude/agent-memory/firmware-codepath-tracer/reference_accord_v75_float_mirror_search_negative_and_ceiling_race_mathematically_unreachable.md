---
name: reference_accord_v75_float_mirror_search_negative_and_ceiling_race_mathematically_unreachable
description: Exhaustive whole-ROM float32/float64 search finds NO float twin of FactorC/FactorE's own breakpoint/output values anywhere -- the only int/float lockstep on the damper signal is the already-documented gp-0x6bd0-vs-its-own-ceiling check (FUN_00034350/FUN_000347b8), and it is byte-confirmed untouched by V74 AND V75. A full firmware-exact grid replay then PROVES that check is mathematically unreachable by V75's edit in the creep/launch speed band (0-2240 raw = 0-35km/h): V75's raw damper product tops out at EXACTLY the ceiling's hard floor (512) with zero exceedance margin, and that floor is provably independent of the race variable gp-0x6ac2. Corrects/closes the open BELIEF in reference_accord_gp6bd0_damper_own_ceiling_consistency_monitor_fun347b8.md.
metadata:
  type: reference
---

2026-08-06, task: adjudicate the operator's H for the V75 stoplight-launch EPS-lamp/total-loss incident --
"V75 tripped an int/float lockstep because the damping cal was edited in int only, float twin left at
stock." Programs: `code.bin` (stock), byte-read directly against the two built plain images
`_v74_engagedcols_x0_12_addonly_plain_image.bin` and `_v75_CY0.566-EX1.200_magprobe_plain_image.bin`
(both confirmed on-disk, matching `docs/STATE.md`/`builds/v50_v79/build_v75_tva.py`'s own SHA). Method: decompile-first
(fresh `FUN_00034350`/`FUN_000347b8` decompiles), then an exhaustive Python byte-exact scan, then a
firmware-exact grid replay of `damper_authority()` using the REAL byte tables from all three images (not
hand-copied numbers).

## (1) Exhaustive float-mirror search -- NEGATIVE, two independent methods

**Method A** (naive, rounded-value sweep, all byte offsets, 7 scale factors): flooded with ~365k
near-zero-denormal false positives from including 0 as a target -- **method discarded, recorded as a
trap for the next session:** never include 0 in a float-target list for a whole-image byte sweep.

**Method B** (exact byte-pattern search): built the EXACT little-endian float32/float64 encoding of
every nonzero stock FactorC/FactorE/Friction/Ceiling value (`2240,3840,5120,8960,234,429,908,60,400,
2500,4000,140,539,927,300,800,512,1024,1280,5760,-9830,-5734,-1966`), at 7 scale factors each
(`x1,/1024,/64,/100,/256,/32,x2`), and searched the WHOLE 1MB stock image for byte-exact matches at
every offset (not just 4-aligned). **Positive control passed**: found the already-documented ceiling
mirror at `0xC6554/58/5C/60` (300.0/800.0/0.5/1.0), confirming the method works.

**Every other hit was adjudicated and excluded**, by reading its surrounding context (16-48 bytes) and
checking whether it forms a recognizable 2- or 4-point LERP table matching FactorC/E's actual shape:
- `0xC6040`=300.0: sits among `[1.0,10.0,200.0,10000,300.0,7.0,10.1,10.0,10.0,50,15.0,15.2]` -- an
  unrelated small-parameter table, no X1/Y0/Y1 pairing. Excluded.
- `0xC65BC`=800.0: sits among `[-1.0,-1.0,3,700.0,800.0,1100.0,0.0,1.5,2.0,7,0.0,9.0]` -- a DIFFERENT
  float table in the same `0xC6xxx` cal block (breakpoints 700/800/1100, not 300/800), unrelated to
  FactorC/E. Excluded.
- `0xC5064`/`0xF9C64`/`0xFA864`=2500.0 (triple, byte-identical, in the `tp+0x6000` "risky model-coeff"
  block): sits among `[4.0,25.0,38.0,20.0,2500.0,0.0414,2.0,40000.0,0.0457,4.0,...]` -- matches the
  already-known "6-LERP FOC Iq/Id gain-schedule cluster" (`reference_accord_fun757a2_iqid_gainschedule_
  bridge_resolved.md`), not a FactorE mirror. Excluded.
- `0xC5570`=512.0 (float64): unrelated neighboring floats (`10000.0,500.0,180.0,180.0,9.0,1.0`),
  same risky block. Excluded.
- `0xC661C`=400.0: **checked in full** -- turns out to be a REAL, legitimate float table at
  `0xC6610-0xC661C` = `X0=350.0 X1=410.0 Y0=5000.0 Y1=400.0`, matching `FUN_00045a20`'s own documented
  tolerance-band LERP (`X=[350,410] Y=[5000,400]`) -- coincidental reuse of the round number 400 by a
  COMPLETELY DIFFERENT subsystem (angle-tracking-error tolerance, not FactorE). Also confirms that
  memory's table values are stored as FLOAT32, not int as the shorthand there implied.

**Second-array check**: each of `FactorC`'s/`FactorE`'s/`Ceiling`'s mode-26 record pointers
(`0xD77D0`/`0xD780C`/`0xD70A8`) appears **exactly once** in the whole image (own pointer array only,
confirmed by `bytes.find` exhaustive search) -- no parallel/duplicate pointer array exists.

**⇒ CONCLUSION: no float mirror of FactorC's or FactorE's own data exists anywhere in the 1MB ROM.**
The ONLY float/int lockstep pair touching this signal chain at all is the CEILING mirror already on
record (`0xC6554` block vs `0xC77A0[mode]`) -- there is no second one to have "forgotten."

## (2) The one real lockstep pair -- byte-confirmed UNTOUCHED by both V74 and V75

Read directly from all three images (not from a build script's own assertion):
```
FactorC mode26  Y[0]: stock=0        v74=429      v75=566        <- THE EDIT
FactorE mode26  X[0]: stock=60       v74=12       v75=12
                X[1]: stock=400      v74=400      v75=200        <- THE EDIT
                Y:    stock=[0,140,539,927]  v74/v75=[0,539,539,927]
Ceiling mode26 (INT, @0xD70A8): stock=v74=v75= X=[300,800] Y=[512,1024]   <- BYTE-IDENTICAL, all 3
Float mirror (@0xC6550 block):  stock=v74=v75= byte-identical raw hex    <- BYTE-IDENTICAL, all 3
Friction mode26: stock=[-9830,-5734,-1966]  v74=v75=[-14745,-8601,-2949] (x1.5, V74's edit, unchanged by V75)
0xC407E: stock=511  v74=v75=850
```
**Neither side of the one real int/float lockstep pair (the ceiling) was touched by V74 or V75.** This
directly falsifies H's literal mechanism ("edited int, forgot the float twin") -- there was no edit to
either side of any actual lockstep pair. What V74/V75 edited (FactorC/E) has no float shadow at all, so
there is nothing for it to fall out of step WITH in that sense.

## (3) THE DECISIVE TEST -- full firmware-exact grid replay, real byte tables, both builds

Reimplemented `lerp_int`/`damper_authority`/`ceiling_floor` to mirror `FUN_00034350` EXACTLY (verified
against a fresh decompile: flat-clamp outside `[xs[0],xs[-1]]`, truncating C division inside), then swept
`speed in [0,14000] step 32/64`, `rate in [0,4500] step 20`, mode=26, on stock/v74/v75's real bytes:

```
                creep-band max product      exceeds ceiling      lowest speed where          speed=0,
                (speed 0-2240=0-35km/h,     floor (512) in       ANY rate first exceeds       rate=99
                 rate 0-4500)                creep band?          the floor (512)?           product
stock:  0    at (speed=?, rate=?)   -- always 0     False         speed=6240 (~97km/h)          0
v74:  388    at (speed=0, rate=4000)          False         speed=6240 (~97km/h)         50
v75:  512    at (speed=0, rate=4000)          False (== floor,   speed=6240 (~97km/h)        137
                                                exactly touches, never exceeds)
```
**V75's creep-band maximum lands EXACTLY on the ceiling's floor (512), by construction of the build's
own "safe max C_Y0=566" binary search, and never exceeds it.** This is not an empirical grid-sampling
observation -- it is provable exactly: in the creep band FactorC is CONSTANT (`=Y[0]=566`, flat below
`X[0]=2240`), and FactorE is monotone non-decreasing with a hard cap `Y[3]=927` for `rate>=4000` (also
unedited by either build) -- so the product's supremum over the WHOLE creep band is the single value
`(566*927)>>10 = 512` exactly, reached only at the corner `(speed<=2240, rate>=4000)`.

**The ceiling's own floor (512) is a HARD, `gp-0x6ac2`-independent minimum** -- confirmed by
`lerp_int`'s own semantics (flat-clamp to `ys[0]=512` below `X0=300`, and the out-of-range fallback
`tp+0x7158=0xC6158=512` is the SAME value) -- it can never read below 512 regardless of what
`gp-0x6ac2` (the ceiling's own race-condition index, sampled independently by `FUN_00034350` at T1 and
`FUN_000347b8` at T2, moments apart in the same 100Hz tick) does between the two samples.

**⇒ Since `gp-0x6bd0 <= 512 <= ceiling(T2)` ALWAYS holds in the creep band (for BOTH V74 and V75),
`FUN_000347b8`'s `|gp-0x6bd0/1024 - ceiling(T2)| > 5/1024` fault condition is mathematically UNREACHABLE
in the incident's own operating region (stoplight launch, mode 26, speed near 0), independent of
`gp-0x6ac2`'s dynamics.** V75's dose is exactly, deliberately AT the boundary that would matter -- but
"at the boundary with zero margin, never exceeding" is precisely the ONE condition under which this
specific check cannot fire, because the boundary IS the check's own unconditional floor.

Confirmed on a fresh fully re-decompiled `FUN_00034350` (`0x34350`) that the entry-time double-check
(`FUN_0004613e(0x4179)` -> DTC index 0x1c) is testing the SAME excess quantity `FUN_000347b8` computed
and stored (`gp-0x6bc4/6/8/a`) the PREVIOUS 100Hz tick -- i.e. 0x1c and 0x1d are two DTC-index labels
on ONE underlying comparison, not two independent checks; both share the same unreachability conclusion.

**Global note, not new to V74/V75**: the product DOES exceed the floor (821 vs 512, pre-existing in
STOCK too) at highway speed >=~97 km/h (`speed>=6240`, unchanged across stock/v74/v75 -- `C_Y1..Y3` and
`E` untouched by either build). That corner is real, pre-existing, and irrelevant to a stoplight-launch
incident.

## (4) The other lockstep families -- confirmed, via prior-session memory, NOT sensitive to gp-0x6bd0

Cross-checked against `reference-accord-fun43e44-no-assist-chain-float-twin.md` (fresh full-function
scan, this kit): **`FUN_00042af8`/`FUN_00043e44` (the "corridor/wall" Monitor 1/Monitor 2 family, same
DTC 0xF00049 / fault-index 0x1c-0x1d bucket) never read `gp-0x6b94`, `gp-0x6bd0`, or ANY individual
aggregator lane** -- they independently re-derive a completely different "corridor/boost WALL" quantity.
Monitor 2's own float accumulator (`FUN_00044666`) is additionally confirmed **permanently gated off**
(`0xC74A4=0xEA`, byte-verified, `reference-accord-consistency-monitor-hardshutdown.md`). Neither could be
sensitized by a FactorC/E edit even in principle.

Confirmed via `FUN_0006b9fa`/`FUN_0006ce7c` fresh decompile: the SIX shadow-lockstep pairs (aggregator
sum `gp-0x6b94`/`gp-0x4ce0`, governor output/sub-terms, post-governor comp) write BOTH cells with the
SAME instructions in the SAME cycle -- these are same-DOMAIN (int-vs-int) write-consistency checks
(the RAM-corruption/interrupt-race class), **not calibration-value-dependent**: a bigger `gp-0x6bd0`
does not change whether these two cells stay in sync, only a genuine corruption event would. Their
downstream consequence (`FUN_0006ce90`, a "channel 8" RTOS-style event dispatcher, `FUN_0006be18`'s
sole caller) was decompiled but not traced to a specific DTC this session -- flagged open, but
**not calibration-sensitive regardless of where it terminates.**

## (5) What remains OPEN -- the one avenue not closed

`FUN_00045a20` (undebounced, `gp-0x67fa` in {4,5,11}, fault index 0x1d via code `0x3a09`) checks
`comp = (gp-0x6acc - gp-0x6ace)/1024` against a bound derived from `gp-0x6ab4` (LERP of angle-tracking
error `gp-0x6a10`, table confirmed BYTE-IDENTICAL stock/v74/v75 at `0xC6610-0xC661C` = float
`X=[350,410] Y=[5000,400]`) and `gp-0x6abe` (column rate). Unlike the ceiling-race check, `gp-0x6acc`/
`gp-0x6ace` are POST-aggregator-sum quantities -- so V75's larger `gp-0x6bd0` contribution (up to 512 vs
V74's 388 at the same creep operating point, a real +124-count/32% increase in ONE of ~11 additive
terms) DOES change what flows into this check, unlike the ceiling-race mechanism. **The numeric link
from that +124-count delta to a `comp`-bound violation was not traced this session** (would need
`FUN_000456a4`'s full producer chain for `gp-0x6acc`/`gp-0x6ace` replayed the same way `damper_authority`
was here) -- this is the single most promising remaining thread, not the one this session closes.

## Verdict on H

**REFUTED for the specific mechanism as posed** ("int table edited, float twin left at stock, causing an
int/float divergence that grew with the driving input") -- there is no float twin of FactorC/FactorE's
data anywhere in the ROM, and the one real float/int lockstep on this exact signal (the ceiling check)
had NEITHER side touched by either build, and is additionally proven mathematically unreachable by
V75's edit in the incident's own (creep-speed) operating region, independent of the race-condition timing
that made the mechanism plausible in the first place.

**PLAUSIBLE remains open, but weakly**, for `FUN_00045a20` — a real, live, undebounced, single-cycle-
latching monitor — but per the reconciliation below, its own `comp` term has NO direct code dependency
on `gp-0x6bd0`; only an unquantified physically-mediated chain (damper output -> steering -> tracking
error) could connect it to V75's edit. This is the one thread neither session closed, but it is a much
narrower opening than "the most promising remaining candidate" — it requires a causal step outside the
firmware bytes (an actual perturbation-to-tracking-error transfer function) that no session has measured.

## Reconciliation with `reference_accord_v75_step_size_hypothesis_refuted_and_fun347b8_precise_trigger.md`
**Found mid-session, same day, independent approach — reconciled, not duplicated.** That session pinned
`FUN_000347b8`'s EXACT comparison via fresh disasm: `r26 = clamp(fVar5, -fVar6, +fVar6); fault if
|fVar5-r26| > 5/1024` — a ONE-SIDED clamp-shrink check, not the symmetric "mismatch" paraphrase this
memory inherited. Consequence: the fault needs `fVar5` (gp-0x6bd0/1024, T1's value) to sit ABOVE T2's
freshly-resampled bound — i.e. `gp-0x6bd0` pinned near a T1 ceiling >512, then the ceiling shrinking
by T2. That session found this needs `gp-0x6bd0 > ~517` at T1, computed it requires `gp-0x6ac0` (FactorE's
OWN index — note: NOT `gp-0x6ac2`, the ceiling's index; the two are correlated but distinct per
[[reference_accord_gp6ac2_is_backdrive_rate_not_gp6ac0_twin]]) near FactorE's `X3=4000` (849 deg/s), and
left the verdict as "2.57x beyond route-5d's measured max (330 deg/s) — not established as reachable,"
i.e. an open BELIEF that a sufficiently violent transient COULD still get there.

**This session's grid-sweep closes that specific opening**: FactorE's LERP is HARD-CAPPED at `Y[3]=927`
for ANY `rate>=4000` (`lerp_int`'s own semantics: `if x>=xs[-1]: return ys[-1]`, confirmed against a
fresh decompile) — there is no headroom past the X3 breakpoint. So the raw product's supremum over the
ENTIRE creep band, for a rate of literally ANY magnitude (4000, 8000, 20000 — the table cannot express
a difference), is `(566*927)>>10 = 512` EXACTLY. **`gp-0x6bd0 > ~517` is not merely "requires an extreme,
unmeasured rate" — it is unreachable by V75's mode-26 calibration at ANY rate, full stop**, because the
factor that would need to grow (FactorE) has nowhere left to grow. This sharpens that session's [BELIEF,
unresolved] open item 1 into a closed, provable NO for this specific mechanism — the "does a real launch
reach 849 deg/s" question becomes moot, since even an arbitrarily large rate cannot move `gp-0x6bd0` off
512 in this speed band.

Also folds in that session's `FUN_00045a20` finding, which revises this memory's own §5 "open avenue"
downward: `FUN_00045a20`'s `comp` term is computed from a SEPARATE LERP on `gp-0x6a10`/`gp-0x6ac0` and
**does not reference `gp-0x6bd0` anywhere in its own arithmetic** — only a long, physically-mediated
chain (damper output perturbs steering perturbs tracking error) could connect V75's edit to this monitor,
and that chain was NOT quantified by either session. This is a WEAKER remaining thread than this memory's
original §5 framing suggested — it is not a direct code dependency, only a hypothesized physical one.

## Related
[[reference_accord_gp6bd0_damper_own_ceiling_consistency_monitor_fun347b8]] -- this memory's BELIEF
section ("pinning is the precondition that exposes this monitor... driven by gp-0x6ac2 changing between
T1/T2") is the one this session's math closes: pinning happens, but at a value (512) that structurally
cannot be exceeded by ceiling(T2) regardless of gp-0x6ac2, in the creep band specifically.
[[reference_accord_hard_shutdown_full_map_v75_incident]] -- source of `FUN_00045a20`'s full disasm and
the six shadow-lockstep pairs, both re-verified/extended here.
[[reference-accord-fun43e44-no-assist-chain-float-twin]],
[[reference-accord-consistency-monitor-hardshutdown]] -- source of the Monitor 1/2 ruling-out.
[[reference_accord_v75_true_headroom_e_exhausted_c_max_566]] -- source of the C_Y0=566 "safe max" value
that this session shows is EXACTLY the boundary that makes the ceiling-race check unreachable (not a
coincidence noted before this session).
