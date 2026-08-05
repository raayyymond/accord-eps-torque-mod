---
name: reference_accord_task5_100hz_live_verified_full_producer_census
description: LIVE Ghidra get_function_callers verification (not memory-relay) of task rate for every one of FUN_0003aa2c's 11 aggregator-lane producers plus FUN_0003ad74 (r24/r26 gain-table rebuilder) — task 1 (FUN_0002214a)=1000Hz confirmed for 8 producers, task 5 (FUN_00022ca0)=100Hz confirmed for FUN_00034350/FUN_00034a72/FUN_0003ad74. 🛑🛑🛑🛑 2026-08-05 THIRD UPDATE (read this section first, supersedes all earlier phase claims in this file): `fs_eff=312.5Hz` for FUN_00041464 was ITSELF wrong -- the 0xD30 gate is a STATE-membership test (gp-0x67fa one-hot), not a 16-phase duty cycle, per this kit's own SETTLED memory I failed to check. Correct rate is the full 1000Hz task1 rate. FINAL corrected numbers: FactorC/E combined phase ~58deg(cos~0.52)@20.9Hz, ~22deg(cos~0.93)@7.79Hz -- REAL, moderate-to-strong damping at both, not near-zero.
metadata:
  type: reference
---

# Full live task-rate census of the aggregator lane producers — 2026-08-04, team-lead mission "where is fast-enough damping authority"

Method: **direct `get_function_callers` + `read_memory` + `decompile_function` calls this session**, not
a memory relay — the brief explicitly asked to verify the standing 100Hz claim, not repeat it.

## The scheduler mechanism, re-derived fresh and byte-confirmed [EVIDENCE]

TCB pointer table `read_memory(0xbb858,28)` = `[0xbb920,0xbb950,0xbb980,0xbb9b0,0xbb9e0,0xbba10,0xbba40]`
— matches [[reference_accord_rtos_task_table_and_rate_scheduler]] exactly, independently reproduced.

`read_memory(0xbb920,16)` entry-point field (+0x08, bytes 8-11 LE) = `4a 21 02 00` = **`0x0002214a`**
(task slot 0 = `FUN_0002214a`). `read_memory(0xbb9e0,16)` entry-point field = `a0 2c 02 00` =
**`0x00022ca0`** (task slot 4 = `FUN_00022ca0`). Both fresh byte reads this session.

`decompile_function(0x14be4)` (the mod-100 rate divider) fresh: `FUN_000861e0(0)` is called
**unconditionally** at the top of every scheduler tick (no `if` guard at all) — this is the direct
evidence that task-slot-0 is the base 1000 Hz rate, not merely "the fastest group." Further down,
`FUN_000861e0(4,10,uVar3/10)` fires only `if (uVar3 % 10 == 4)` — 1 tick in 10.

`decompile_function(0x837c0)` (syscall-8 handler) fresh: computes
`*(uint*)((param_1 & 0xff)*0x30 + TCB_base + 0x2c)` — `param_1` is used as a **direct 0-based TCB slot
index**, confirming the argument passed by `FUN_00014be4` (`0` or `4`) selects the task, not an opaque
rate-group id.

**Conclusion, EVIDENCE not belief: task slot 0 (`FUN_0002214a`) = 1000 Hz, every tick. Task slot 4
(`FUN_00022ca0`) = 100 Hz, 1-in-10 ticks.** This is exactly the standing claim in
[[reference_accord_task5_rate_resolved_and_feedforward_insertion_point]] — CONFIRMED by an independent
byte/decompile pass, not merely re-cited.

## Live `get_function_callers` results for every aggregator-lane producer, this session

| function | lane / role | caller | task | rate |
|---|---|---|---|---|
| `FUN_0003aa2c` | the aggregator itself | `FUN_0002214a` | 0 | **1000 Hz** |
| `FUN_00036388` | Lane A, return-centre, `gp-0x6b62` | `FUN_0002214a` | 0 | **1000 Hz** |
| `FUN_000352b4` | Lane B, magnitude/peak-hold, `gp-0x6b86` | `FUN_0002214a` | 0 | **1000 Hz** |
| `FUN_00036c12` | Lane C, friction, `gp-0x6b26` | `FUN_0002214a` | 0 | **1000 Hz** |
| `FUN_0003a382` | resonance P/I/D, `gp-0x6ad4` (muted V56) | `FUN_0002214a` | 0 | **1000 Hz** |
| `FUN_00026c80` | mixer, writes `gp-0x6b4c` (LKAS) | `FUN_0002214a` | 0 | **1000 Hz** |
| `FUN_00036682` | Lane D, filtered Sensor-B | `FUN_0003aa2c` (inline, itself 1kHz) | 0 | **1000 Hz** |
| `FUN_00041464` | common-mode rate bus producer, `gp-0x6abe`/`gp-0x6ac0`, AND the friction-lane's own input EMAs `gp-0x6c2c`/`gp-0x6c2e` | `FUN_0002214a` | 0 | called @1000Hz but **internally phase-gated 5/16 -> fs_eff=312.5Hz** |
| `FUN_00034350` | damping, FactorC/E, `gp-0x6bd0` | `FUN_00022ca0` | 4 | **100 Hz** |
| `FUN_00034a72` | boost, `gp-0x6bbe` | `FUN_00022ca0` | 4 | **100 Hz** |
| `FUN_0003ad74` | rebuilds r24's gain_B table AND r26's gain_A table (the RAM LERP surfaces both rate lanes read) | `FUN_00022ca0` | 4 | **100 Hz** — NEW, closes an open item |
| `FUN_00022ca0` (task 5 entry) | — | *(none found — expected: reached only via TCB indirection, never a static `jarl`)* | — | — |

r24/r26 themselves are computed **inline inside `FUN_0003aa2c`** (not a separate callee) on `dtorque =
clamp(gp-0x4f62, +/-0x1400)`, unfiltered — so they run at the aggregator's own 1000 Hz, even though the
**gain tables** they multiply against are only refreshed at 100 Hz by `FUN_0003ad74`. This means the r24/r26
VALUE is full-rate, but their gain surface can be up to ~10ms stale relative to vehicle speed — a minor
staleness, not a bandwidth cut, since dtorque itself is what carries the 21Hz content and it is sampled
every tick.

## What this resolves

1. Closes [[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]]'s "FUN_00022ca0's actual task
   rate — decisive for boost/damping's dB, unresolved this session (no static caller; get_function_callers
   returns null, consistent with an RTOS task-table entry)" — **now resolved: 100 Hz**, via the TCB-index
   route (`get_function_callers` on the TASK ENTRY POINT itself will always return null, since it's reached
   by indirection, not a `jarl` — the RIGHT question is what task entry point's CALLEES include the lane
   producer, which is what this session checked).
2. Closes [[reference_accord_rate_lane_v62_to_v69_gain_arc]] §7's "Sole caller `FUN_00022ca0` is an RTOS
   task ... rate UNRESOLVED" for `FUN_0003ad74` — **100 Hz**, same task as the damping/boost host.
3. Confirms (does not merely repeat) [[reference_accord_task5_rate_resolved_and_feedforward_insertion_point]]
   and [[reference_accord_factorc_e_damper_full_trace_r24r26_parallel]]'s task-rate re-verification, via a
   third independent method this session (TCB byte read + FUN_00014be4/FUN_000837c0 decompile, not just
   `get_function_callers` alone).

## 🛑🛑🛑🛑 THIRD correction (2026-08-05, 3rd follow-up): `fs_eff=312.5Hz` itself was WRONG — `FUN_00041464` runs at the FULL 1000Hz task1 rate, not 312.5Hz. ALL phase numbers below using 312.5Hz are superseded again.

Team-lead's independent trip-amplitude reconstruction (matching the golden model's own recorded figures
to within 1% at 5 frequencies when driven at 1000Hz, badly mismatched at 312.5Hz) prompted a re-check.
Fresh `disassemble_function(0x22190)` this session confirms the call-site gate I (and the source memory
I inherited from) both misread: `0002219e andi 0xc30,r25,r0` / `000221f8 andi 0xd30,r25,r23 / be [skip] /
jarl FUN_00041464`. **This gate is REAL** — I did not imagine it — but its correct interpretation, per
this kit's own SETTLED memory
[[reference_accord_0x930_masks_are_state_not_phase_settled]] (which I should have checked before
inheriting "5/16 phases -> 312.5Hz" from an older, pre-settlement memory), is a **ONE-HOT STATE-MEMBERSHIP
TEST on `gp-0x67fa`** (`r25 = 1<<(gp-0x67fa & 0xF)`, then `andi 0xD30,r25` tests "is the ECU currently in
state {4,5,8,10,11}"), **NOT a rotating 16-phase duty-cycle counter**. "There is no phase counter and no
phase rotation anywhere in the control tasks" (quoting that memory directly) — during any SUSTAINED
operating condition (state fixed at, e.g., 10, for the whole time LKAS is engaged and driving normally),
the gate is either continuously TRUE or continuously FALSE, never "5 out of every 16 ticks." **When
`gp-0x67fa` is in the mask (the normal running condition), `FUN_00041464` fires on EVERY task1 tick =
1000Hz, full stop.**

**Corrected numbers, same scripts, `fs_ema` changed from 312.5 to 1000.0**:
```
FactorC/E combined phase (damper_phase_FULL_corrected.py):
  20.9 Hz: lag ~57-62deg (avg ~58-59deg), cos ~0.47-0.54   -- REAL, moderate damping (not ~zero)
  7.79 Hz: lag ~22.2-22.4deg,             cos ~0.92-0.93   -- strong damping, close to naive estimate

Friction lane cascade + total phase (friction_lane_1khz_corrected.py):
  20.9 Hz: cascade +54.92deg -> total -128.8deg avg, cos=-0.627  -- still damping, weaker margin than before
  45.0 Hz: cascade +23.55deg -> total -164.6deg avg, cos=-0.964  -- still damping, STRONGER than before
  gain(45Hz)/gain(21Hz) = 0.1813/0.1171 = 1.548 -- matches team-lead's independently-measured 1.53x
  (1683/1104 from golden-model trip amplitudes) almost exactly -- good cross-validation that 1000Hz is right.
```
**Practical consequences**: (1) the base damper is a REAL, moderate contributor at 20.9Hz now (cos~0.5,
not ~0) -- reopens whether V72's null on grind #1 is a phase-margin story at all, versus a
magnitude/saturation story; team-lead flagged this as decision-bearing and it is. (2) the friction lane's
falsifiable prediction is UNCHANGED (still damps at both 20.9 and 45Hz, still safe from the V62/grind-#2
pathology) but the 20.9Hz margin is weaker (cos -0.63 not -0.99) and the 45Hz margin is stronger (cos
-0.96 not -0.67) than previously reported. (3) the friction-lane headroom/clamp-crossing estimate also
needs the corrected cascade gains -- see [[reference_accord_gp6b26_friction_lane_damping_candidate]] for
the redone numbers.

**Lesson, stated plainly**: I inherited `fs_eff=312.5Hz` from an OLDER agent-memory file
([[reference-accord-fun41464-sign-filter-phase-response]], 2026-07-21) without checking whether it had
since been superseded — it had, by
[[reference_accord_0x930_masks_are_state_not_phase_settled]] in this SAME memory directory, which I did
not search for before using the figure. Should have grepped for "0x930" / "phase" / "state" mask
interpretations before trusting an inherited rate constant, especially one flagged in my own MEMORY.md
index as "★★★★★ SETTLED 0x930/0xc30/0xd30=one-hot ECU-STATE masks... SETTLED."

## [SUPERSEDED by the above] RE-RETRACTION (2026-08-05, 2nd follow-up): the "undetermined, mean cos=0" relay-simulation claim below is ALSO WRONG — found and fixed a real bug in my own sim, credit to team-lead for the catch

Team-lead reproduced my relay simulation independently and got a completely different, physically sane
answer (cos≈0.79 at 20.9Hz matching the plain ZOH formula `cos(180*f/fs)`, tightly clustered across 97
swept scheduler offsets) and correctly diagnosed my "mean=0, stdev=0.707, min=-1, max=+1" result as **the
statistical fingerprint of `cos(Uniform(0,2*pi))`** — i.e. an estimator that resolved nothing, not a real
physical finding. **They were right. I found the bug.**

**The bug**: my phase0-sweep varied the OSCILLATOR's phase while holding the sampling grid fixed at
`t=0,dt,2dt,...`, then compared the relay's measured phase against a comparison target that I re-derived
per phase0 in a way that was NOT self-consistent with what the simulation was actually measuring — the
measured relay phase (correctly) tracked the shifted oscillator, but my "ideal" reference tracking of that
same shift had an inconsistency I did not fully diagnose line-by-line (traced to the interaction between
how `phase0` entered the sampled signal vs. how it entered my "ideal" comparison formula). **Rather than
chase the exact line further, I re-implemented from scratch using team-lead's exact, unambiguous
methodology** (`v(t)=cos(2*pi*f*t)` NEVER phase-shifted; only the TASK GRID's start offset varies; ideal
target is `-v(t)`, fixed at 180 deg since `v(t)` itself never moves) — this design has no room for the same
class of bug, and it reproduces team-lead's own number closely: `37.2-37.8 deg` (cos 0.79-0.80) at 20.9Hz,
`13.9-14.1 deg` (cos 0.97) at 7.793Hz, essentially independent of grid offset, matching the analytic ZOH
formula `180*f/fs` to within simulation noise. **Confirmed, this validates team-lead's methodology and
number for the PURE ZOH+relay building block.**

## 🛑🛑 But the real mechanism has ONE MORE stage team-lead's simplified test omitted — and restoring it changes the number materially

Team-lead's test samples raw velocity `v(t)` directly. **The real firmware does not** — both the sign flip
(`0x3469e`, reading `r11` loaded at `0x34604 ld.h -0x6abe[gp],r11`) and FactorE's gate (`0x345fa ld.hu
-0x6ac0[gp],r14`) read `gp-0x6abe`/`gp-0x6ac0`, which are the OUTPUT of `FUN_00041464`'s own EMA
(alpha=37/128, cal `0xC643C`=37, fs_eff=312.5Hz) — not raw motor rate. This EMA is a real, confirmed,
address-cited stage sitting between true velocity and the relay decision, structurally different from the
now-confirmed-inert torque-EMA (that one really was dead; this one is not — it is the ONLY signal both the
sign flip and FactorE read).

**Re-ran the same corrected (grid-offset, not oscillator-phase) methodology WITH the EMA stage restored**
(script: `scratchpad/damper_phase_FULL_corrected.py`), robustness-checked across many grid offsets and two
simulation durations (30s and 60s):
```
20.9 Hz:  lag = 88.2 - 90.0 deg,  cos = -0.0002 to +0.032   (essentially ZERO net damping authority,
                                                              hovering right AT the 90deg boundary)
7.793 Hz: lag = 38.9 - 39.0 deg,  cos = 0.777 - 0.778        (solid damping, weaker than the pure-ZOH-only
                                                              0.97 estimate, but clearly still damping)
```
**This is a THIRD, different, and now well-validated number** — not my first claim (81.8/119.4deg, wrong
path), not my second claim (undetermined/mean-zero, simulation bug), and not simply team-lead's pure-ZOH
number either (0.79/0.97, which omits a real stage of the actual mechanism). The extra ~11-12deg gap
between simple LTI addition (ema_phase 39.6deg + zoh_avg 37.6deg = 77.2deg) and the simulated 88-90deg
comes from a genuine nested-ZOH interaction (the EMA's own output is itself a step function updated only
every 3.2ms at 312.5Hz, and the relay is hypersensitive to exactly which step is visible at each 100Hz
sample) that a naive additive estimate does not capture — not re-derived in closed form, time-domain result
trusted over the naive addition here.

**The physical story this supports, precisely**: at 7.79Hz the term delivers real damping (cos=0.78) —
explains why V72's dose fixed the ratchet. At 20.9Hz the term sits almost exactly ON the 90deg boundary
(cos≈0.00-0.03) — **not reliably damping, not reliably anti-damping, just carrying essentially ZERO net
phase projection onto velocity** — which is arguably a CLEANER explanation for V72's exact on-car result
(grind #1 neither improved nor worsened) than either "weak but positive" or "crosses into anti-damping":
raising the dose of a term whose phase already sits at ~90deg does nothing, in either direction, regardless
of magnitude — matching precisely what was observed.

**Lesson for the record, since this is the second phase-simulation error in two rounds**: when building a
"sweep an offset/phase parameter and check consistency" test, the SAFEST design is team-lead's — hold the
reference signal fixed and only move the SAMPLING GRID, so the "ideal" comparison target never needs to be
independently re-derived per sweep step. My original design (shifting the oscillator and re-deriving the
ideal target for each shift) introduced a self-consistency bug I did not fully pin to one line before
abandoning that design in favor of the safer one. Do not reuse the abandoned design.

## [SUPERSEDED by the above, kept for the record] RETRACTION + major correction (2026-08-05 follow-up): the 81.8°/119.4° figure below is WRONG — the torque EMA it used is PROVABLY INERT, and the real mechanism is far stranger

Team-lead raised the "grind #1 vanishes above ~25mph, right at FactorC's 35km/h gate" coincidence and asked
for the phase re-derived from the actual code, not inherited. Fresh `decompile_function(0x34350)` +
`disassemble_function(0x34350)` (both full, this follow-up session) found:

**The `alpha=205/1024` EMA I originally cited (`y[n]=y[n-1]+((gp-0x4f60[n]*32-y[n-1])*205)>>10`, cal
`0xC636E`=205 byte-confirmed, RAM state `gp-0x6df8`) IS REAL** — pinned to `0x34392-0x343ba` exactly:
`0x34392 ld.h -0x4f60[gp],r15` / `0x34396 ld.w -0x6df8[gp],r28` / `0x3439a ld.hu 0x736e[tp],r16` /
`0x343a2-a6 shl 0x5,r10; sub r28,r10` / `0x343a8 mul r16,r10,r0` / `0x343b8 sar 0xa,r10` /
`0x343ba add r10,r28`. **But its ONLY consumer is FactorB's key `gp-0x6bcc`, and FactorB's LERP table
(`0xD2738`, mode10, fresh byte read this session: count=4, X=(205,1331,2355,3072), Y=(1024,1024,1024,1024))
is FLAT AT UNITY across its ENTIRE domain — and the "invalid/implausible" fallback path (`0x3446a`) is
ALSO literally `0x400`=1024.** So FactorB multiplies by exactly 1.0 no matter what the EMA (or the
plausibility gate) produces. **The EMA is live, runs every 100Hz tick, and is structurally provably inert
for `gp-0x6bd0`'s dynamics.** My original 44.2°(EMA)+37.6-75.2°(ZOH)=81.8°/119.4° figure used this dead
path — **RETRACTED**, replaced below.

## The REAL dynamic path: `sign(-gp-0x6abe)` + `FactorE(|gp-0x6ac0|)`, both from ONE upstream EMA

Confirmed via the same fresh disasm: FactorE's gate loads `gp-0x6ac0` at `0x345fa`; the sign flip at
`0x3469e cmp r0,r11 / 0x346a0 ble / 0x346a2 subr r0,r8` reuses `r11`, loaded ONCE at `0x34604 ld.h
-0x6abe[gp],r11` — same register, same 100Hz-tick instant, no extra staleness between the two. Both trace
to `FUN_00041464`'s single EMA state (`gp-0x359c`), alpha=37/128 (cal `0xC643C`=37, byte-confirmed this
session), fs_eff=312.5Hz (5/16 phase-gated, inherited from prior sessions, not re-derived this round).

**Naive LTI estimate** (treating the upstream EMA's -39.6° continuous-time phase as additive with the
100Hz sample-hold's avg 37.6°/worst 75.2°): **avg -77.2° / worst -114.8°**, cos 0.14-0.22 avg, crosses 90°
worst-case. This is INVALID as stated — see below.

**Rigorous time-domain simulation** (mirrors the exact integer recurrence at both stages, `sign()` treated
as the hard nonlinearity it actually is, Python in `scratchpad/damper_phase_sim.py` +
`damper_phase_robustness.py`): because `FUN_00034350` samples `gp-0x6abe` at a FIXED 100Hz grid that is
**not harmonically locked to either 20.9Hz or 7.793Hz**, the measured phase of the resulting sign-relay's
fundamental harmonic depends entirely on the (firmware-uncontrolled) relative timing offset between the
scheduler and the oscillation. Sweeping that offset over a full cycle: **cos(net lag) spans the ENTIRE
range [-1.0, +1.0], mean 0.000, stdev 0.707, at BOTH 20.9Hz and 7.793Hz identically** (min/max/mean
essentially the same at both frequencies — an initial hypothesis that the ZOH-fraction-of-period would
differentiate them was tested and REFUTED). **This means: the code does not fix any particular phase
relationship between this damper's sign decision and either oscillation — it is exactly as likely to be
damping as anti-damping at either frequency, for reasons NOT resolvable from static firmware analysis.**

**Open tension I am flagging, not resolving**: this finding is in tension with the kit's own explanation of
why V72's Lever B fixed the 7.79Hz ratchet (the "14-28° healthy margin" framing) — that number was computed
treating the term as smooth/LTI, which this session shows is not a valid model for the sign-relay stage.
Candidate resolutions, none confirmed: (a) a real self-sustained limit cycle is a CLOSED-LOOP phenomenon
that self-selects a consistent relative phase (not modelable as an open-loop swept parameter, which is what
this simulation did); (b) even a zero-mean-phase mechanism could still perturb loop gain/energy in a way
that breaks a MARGINAL limit cycle without being "damping" in the classical sense. **Needs an on-car
measurement of `gp-0x6bd0` vs actual angle/motor-rate phase during a real oscillation episode — not
resolvable from firmware bytes alone.**

## [SUPERSEDED, kept for the record] Consequence for the FactorC/E base-assist damper's phase at 20.9 Hz — now fully quantified

With task-5=100Hz nailed down as EVIDENCE (not assumption), `FUN_00034350`/`FUN_00034a72`'s own internal
pre-filter EMA (`y[n]=y[n-1]+((gp-0x4f60[n]*32-y[n-1])*alpha)>>10`, alpha=205/1024=0.2002, cals
`0xC636E`/`0xC6372`) has TWO stacked phase penalties at 20.9 Hz, both now computed by exact z-domain
integer-arithmetic-mirroring Python (`ema_gain_phase`, single real-pole EMA, cross-validated against the
kit's own recorded 21Hz/7.79Hz figures to <0.5deg):

```
internal EMA (alpha=205/1024, fs=100Hz, f=20.9Hz):  |H|=0.1804 (-14.9dB),  phase = 44.2 deg lag
output ZOH  (1kHz aggregator reads a 100Hz-updated gp-0x6bd0/gp-0x6bbe): avg 37.6 deg, worst 75.2 deg
------------------------------------------------------------------------------------------------
COMBINED:                                            avg 81.8 deg,  worst 119.4 deg
```
**The worst-case number (119.4 deg) crosses the 90 deg flip point** — `cos(119.4deg) = -0.49` — meaning in
the worst sampling-alignment case this term is not merely weak but **actively ANTI-DAMPING** at 21Hz. The
average case (81.8 deg, `cos=0.14`) is still 86% attenuated. Neither case is good; this is the strongest
concrete explanation on record for why V72's damper dose fixed the 7.79Hz ratchet (14.0/28.0deg penalty
there, `cos`=0.97/0.88) and did nothing for grind #1 (18-22Hz) — **the same firmware element, at the
frequency that matters, has essentially zero-to-negative phase margin.**

## Related
[[reference_accord_task5_rate_resolved_and_feedforward_insertion_point]] — prior session's first
resolution of task-5=100Hz, via a different method (TCB-index formula only), reused and independently
re-derived here.
[[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]] — source of the 11-lane structure and the
open item this session closes.
[[reference_accord_rate_lane_v62_to_v69_gain_arc]] — source of the FUN_0003ad74 open item this session
closes.
[[reference_accord_factorc_e_damper_full_trace_r24r26_parallel]] — the FactorC/E damper trace this session's
phase math extends to a hard 20.9Hz number.
