---
name: reference_accord_gp6bd0_shadow_faultpath_0x4179_0x417a
description: FUN_00034350 (damper) and its companion FUN_000347b8 form an int/float shadow-consistency PAIR checking that gp-0x6bd0's stored (clamped) value equals an independently float-recomputed clamp(product, ±ceiling), tolerance ±5/1024 (~0.49% of Q10 full scale). On mismatch, FUN_000347b8 calls FUN_000462e6(0x417a,...) UNCONDITIONALLY (not gated by the 0xC74A4 disable byte that only gates a DIFFERENT caller, FUN_00044666/"Monitor 2") which reaches FUN_00016de6(0x1d,1,1) -- the SAME hard-shutdown latch chain documented in reference-accord-consistency-monitor-hardshutdown. FUN_00034350's OWN top-of-function check (ID 0x4179) re-verifies the SAME invariant one 100Hz cycle later via FUN_0004613e -> FUN_00016de6(0x1c,1,1). This is a genuine, previously undocumented hard-fault-capable monitor tied to gp-0x6bd0, though it checks numerical clamp-consistency, not a physical magnitude limit -- decompile-first-then-assembly, both functions.
metadata:
  type: reference
---

# gp-0x6bd0's int/float shadow-consistency monitor -- traced 2026-08-06, stock code.bin

Task: is there a monitor that can hard-fault on `gp-0x6bd0`? Investigated because
`FUN_00034350`'s own decompile shows a top-of-function call `FUN_0004613e(0x4179, &gp-0x6bc6, &gp-0x6bc8,
&gp-0x6bc4, &gp-0x6bca)` on a plausibility-style branch, gated on values that turn out to be written by a
SIBLING function, `FUN_000347b8` — traced both fully (decompile-first per standing rule, then disassembly
to pin the exact float comparison since the decompile carried Ghidra's own "Heritage AFTER dead removal"
warning).

## Call order and task rate [EVIDENCE, `FUN_00022ca0` decompile, this session]

`FUN_00022ca0` = **task 5, 100Hz** (per [[accord-dtc18-cadence-watchdog]]'s task table). Inside the
`uVar5 = gp-0x67fa-state-mask & 0x830` branch (states {4,5,11} — the "detector" mask per
[[accord-gp67fa-state-gate-on-assist-chain]]):
```c
FUN_00034350(0x11);   // the damper — computes and stores gp-0x6bd0/gp-0x4cf2
FUN_000347b8();       // IMMEDIATELY after, same cycle — the shadow check
FUN_00034a72(0x12);   // boost (gp-0x6bbe), sibling
FUN_00035154();
```
So `FUN_000347b8` reads the value `FUN_00034350` JUST wrote, same 100Hz tick — the tightest possible
coupling. **This whole pair runs ONLY when `gp-0x67fa` ∈ {4,5,11}** (unconditional on vehicle speed, so
reachable at standstill whenever that state applies).

## What `FUN_000347b8` actually does [EVIDENCE, `disassemble_function` 0x347b8]

Recomputes, in FLOAT, an independent clamp of the damper's own output against the SAME ceiling table
(`gp-0x6ac2`-indexed, same fallback cal `tp+0x7158` as the integer path's `FUN_00034350`), using a
**separate float-domain mirror of the ceiling LERP at `tp+0x7554` onward**:

```
fVar_actual  = (float)gp-0x6bd0 / 1024.0                       ; 0x347c4/0x347d0
fVar_ceiling = LERP(gp-0x6ac2, table@tp+0x7554) or cal(tp+0x7158) if gp-0x6ac2>=13000   ; 0x347fc-0x3487a
fVar_clamp   = clamp(fVar_actual, ±fVar_ceiling)                ; 0x3487a-0x34890 (float min/max)
diff         = fVar_actual - fVar_clamp                         ; 0x34890
if (diff > +0.0048828125 || diff < -0.0048828125):    // ±5/1024, exact float constants 0x3BA00000/0xBBA00000
    FUN_000462e6(0x417a, fVar_actual, fVar_clamp, gp-0x6ac2, 0xbba00000)   ; 0x348a4-0x348b0
// regardless of pass/fail, ALWAYS write the shadow-history cells (consumed by FUN_00034350 next cycle):
gp-0x6bc4 = 5                          ; fixed sentinel
gp-0x6bc8 = int(fVar_clamp * 1024)     ; the recomputed ceiling, Q10
gp-0x6bca = -5                         ; fixed sentinel
gp-0x6bc6 = int(fVar_actual * 1024)    ; echo of gp-0x6bd0, Q10
```
`FUN_000462e6(0x417a,...)` **unconditionally** calls `FUN_00016de6(0x1d, 0x417a, 1, 1)` — confirmed by
fresh decompile of `FUN_000462e6` this session. This is the SAME `param_3=1,param_4=1` "fault-latching
branch" documented in [[reference-accord-consistency-monitor-hardshutdown]] for DTC 0x1d. **Critically,
this call path does NOT go through `FUN_00044666`** (the accumulator function whose trip is gated OFF by
`0xC74A4=0xEA`, per that memory) — `FUN_000347b8` calls `FUN_000462e6` DIRECTLY, so **the `0xC74A4` gate
does not disarm this specific trip.**

## `FUN_00034350`'s own check, ID 0x4179 [EVIDENCE, re-reads the same 4 cells one cycle later]

At the top of `FUN_00034350` (before this cycle's product computation):
```
iVar8  = gp-0x6bc4              (=5, constant, written by FUN_000347b8 LAST cycle)
iVar18 = gp-0x6bc6 - gp-0x6bc8  (= actual_value_prev - ceiling_prev, both Q10 ints)
sVar12 = gp-0x6bca              (=-5, constant)
if (iVar18 outside [sVar12, iVar8] == outside [-5,+5]):
    FUN_0004613e(0x4179, &gp-0x6bc6, &gp-0x6bc8, &gp-0x6bc4, &gp-0x6bca)
```
`FUN_0004613e` [EVIDENCE, fresh decompile]: logs the 4 args to a diagnostic record (`gp-0x6920`/`6918`/
`691a`/`6916`/`691c`) then calls `FUN_00016de6(0x1c, param_1, 1, 1)` — **the SAME hard-fault-latching
branch, DTC 0x1c.** So this is a **one-cycle-delayed re-verification of the identical invariant**
`FUN_000347b8` already checked in float — both test "does the stored/clamped Q10 damper value equal
`clamp(product, ±ceiling)` within ±5 counts (~0.49% of full scale)."

## Escalation chain [inherited from [[reference-accord-consistency-monitor-hardshutdown]], not re-derived]
`FUN_00016de6(0x1c or 0x1d, code, 1, 1)` → `FUN_00016634`(DTC history) + `FUN_00016b66`(status) →
`FUN_0001611e` (hard-fault-eligible check) → `FUN_00018738` (trip counter) → when counter reaches
threshold: `gp-0x685c`=1 (DTC latch) + `FUN_00018bc0`(`gp-0x3ef8`=1) → `FUN_00019f7c` (per-cycle) →
`gp-0x67fa`=8 (shutdown state) → `FUN_0001a16a` → `FUN_00045608(3,0,0x8000,0x8000)` (motor off).

## Verdict — EVIDENCE vs BELIEF, precisely separated

**[EVIDENCE]** A genuine hard-fault-capable monitor exists, tied specifically to `gp-0x6bd0`'s own
clamp arithmetic, running every 100Hz cycle whenever `gp-0x67fa`∈{4,5,11}, unconditional on speed
(reachable at standstill), NOT disarmed by the `0xC74A4` byte, reaching the same latch/shutdown chain as
the already-documented Monitor 1/Monitor 2.

**[BELIEF, NOT provable from static tracing alone]** Whether V75's specific cal edit (raising FactorC's
low-speed `Y[0]` 429→566) actually TRIPS this monitor is unresolved. The check is a **numerical
int-vs-float rounding-consistency tolerance** (±5/1024) on the clamp implementation, not a physical
magnitude bound — the clamp `gp-0x6bd0 = clamp(product, ±ceiling)` is applied UNCONDITIONALLY in code
regardless of FactorC's cal value, so this invariant should hold BY CONSTRUCTION for any input value that
stays inside the ceiling's linear region (and V75's own C_Y0=566 was verified elsewhere,
[[reference_accord_v75_true_headroom_e_exhausted_c_max_566]], to never exceed the ceiling on the full
grid). The one way this monitor COULD trip from V75's edit is a boundary/rounding edge case (e.g. int LERP
vs float LERP disagreeing by >5 counts at a specific breakpoint) that happens to be newly reachable now
that the product is nonzero at low speed instead of trivially 0≡0 as on stock — **this requires either
simulating the exact int/float arithmetic at the fault's actual (speed, rate) operating point, or reading
the DTC log from the car (a UDS operation, out of scope for this analysis session), to confirm or refute.**

## Separately confirmed: the AGGREGATOR's own gp-0x6bd0 window is NOT a fault path
`FUN_0003aa2c` @0x3ac78-0x3ac8c: `|gp-0x6bd0+0x800|<0x1001` (±2048) is a **silent clamp-to-zero**
(`cmovc 0x0,r9,r12`), no fault call. Since FactorF's ceiling caps `gp-0x6bd0` at 512-1024 (mode-dependent),
well inside ±2048, this window is architecturally unreachable in practice and is not a candidate mechanism.

## Related
[[reference-accord-consistency-monitor-hardshutdown]] — the escalation chain this reuses without
re-deriving. [[reference_accord_gp6bd0_full_reader_enumeration_and_dual_path]] — full reader census this
was found alongside. [[reference_accord_v75_true_headroom_e_exhausted_c_max_566]] — the ceiling-headroom
math that makes the "numerical edge case" reading more plausible than a "magnitude exceeded" reading.
