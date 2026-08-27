---
name: reference-accord-task5-100hz-syscall8-rate-divider
description: "RETRACTED 2026-08-12: the 100Hz claim for task 5 (FUN_00022ca0, hosts gp-0x6bbe/gp-0x6bd0's producers) is CONTRADICTED by gp-0x6bbe's own flown data (route 79 frequency/step/phase measurements all point close to 1kHz, not 100Hz). The FUN_000837c0/syscall8 mechanism this was derived from does not reliably establish task dispatch -- FUN_00083854/FUN_00083918 turned out to be general kernel primitives, not confirmed task-wake functions. Task 1 = 1kHz (control-task-tick-confirmed-1khz) is UNAFFECTED. Task 5's true rate is UNRESOLVED."
metadata:
  type: reference
---

## 🛑🛑 RETRACTED 2026-08-12 — READ THIS FIRST

**The 100Hz claim below is CONTRADICTED by `gp-0x6bbe`'s own flown data (route 79) and should not be
used.** Three independent measurements converge on a rate much closer to 1kHz than 100Hz:
- **Frequency response**: measured ≈−1.2dB at 6-9Hz, against a predicted −6.6/−8.4/−9.5dB at 100Hz vs
  −0.2/−0.3/−0.3dB at 1kHz. Measured sits on the 1kHz prediction, ~7dB from the 100Hz one.
- **Step response**: median normalized profile at 20ms is **+114%** of final value. A first-order system
  with the 100Hz-implied τ=44.8ms can move at most 36% in one 20ms sample — measured is 3.8x over that
  physical cap. Resolves τ∈[0,20]ms, consistent with the 1kHz (τ≈5ms) case, not the 100Hz one.
- **Phase**: rises monotonically −77° to +43° across 0.3–20Hz; a 100Hz-rate pole would make phase *fall*,
  not rise, over this range.

**Where the derivation broke**: re-examining `FUN_00083854`/`FUN_00083918` (called "wake-related" below
without a full decompile) shows they are general kernel event/dispatch primitives — traversing a linked
structure keyed on a `char` match, touching what looks like character/exception handling
(`FUN_00014d5c`, `FUN_00057ede`) — **not confirmed RTOS task-wake functions**. My identification of
`FUN_000837c0` as "the task-scheduling eligibility check" was never independently verified beyond a
self-consistency coincidence with task 1's ALREADY-KNOWN 1kHz rate (established by two OTHER, unrelated
methods) — and a generic "index 0 fires every tick" pattern is not uniquely diagnostic of task dispatch;
it could show up in an unrelated subsystem this reasoning happened to land on.

**What survives**: task 1 = 1kHz, per [[control-task-tick-confirmed-1khz]]'s own two methods
(OSTM0CMP hardware-timer math, STEER_STATUS=4 dwell measurement) — neither depends on anything below and
both are untouched. **Confirmed clean**: `FUN_00034a72`'s sole caller is `FUN_00022ca0` (re-verified via
two methods, `get_function_callers` and `get_xrefs_to` on `0x22ca0` itself, zero other paths) — so the
fast dynamics are not explained by the code actually running through task 1's context; the code genuinely
only executes inside task 5. **What does NOT survive**: the 100Hz rate claim itself, and everything
downstream of it in the "Consequence" section below — the −5.8/−7.5/−8.6dB attenuation figures for
`gp-0x6bbe` at 6-9Hz. **Task 5's true dispatch rate is UNRESOLVED** — treat it as empirically close to
1kHz (or at least τ≤20ms) per the measurements above, not confirmed at any specific value. Closing this
properly needs identifying what `FUN_000837c0`/`FUN_00083854`/`FUN_00083918` actually govern, which may
not even be RTOS task scheduling — not completed.

---

# Task 5 (`FUN_00022ca0`, assist-shaping) = 100Hz [RETRACTED, see above — kept below for the record]

Extends [[control-task-tick-confirmed-1khz]], which pinned the control task (`FUN_0002214a`) at 1kHz but
left the assist-shaping task's rate as "NOT statically determinable... ~100Hz architecturally normal."
This session determined it structurally, not just architecturally.

## Method

`FUN_000837c0` (the syscall-8 eligibility handler, called from every RTOS wake checkpoint) computes
`*(uint*)(param_1*0x30 + *(int*)(tp-0x3814) + 0x2c)`. Reading `*(int*)(tp-0x3814)` directly (tp=0xBF000,
so `tp-0x3814=0xBB7EC`) gives **`0x000BB920`** — the address of TCB[0] itself. The "table" this indexes
IS the 7-entry TCB pointer array (0x30-byte stride: `0xbb920, 0xbb950, 0xbb980, 0xbb9b0, 0xbb9e0, 0xbba10,
0xbba40`).

`FUN_00014be4` (the RTOS's mod-100 tick counter) calls `syscall8(0/1/3/4/5)` at rates /1, /2, /5, /10, /100
respectively — those parameter values are exactly the TCB array indices 0, 1, 3, 4, 5 (skipping 2 and 6,
the 4-byte stub task and the no-period background task — both consistent with needing no periodic wake).
**Array index 0 = TCB `0xbb920` = task 1** (`FUN_0002214a`), independently confirmed 1kHz per
[[control-task-tick-confirmed-1khz]], and `syscall8(0)` is the UNCONDITIONAL every-tick call — self-
consistent with the known anchor.

Byte-read task 5's own TCB at `0xbb9e0` (array index 4): confirms `[prio=2][taskid=5]` at offset +0x04
and entry point `0x00022ca0` at +0x08 — genuinely task 5. `syscall8(4,...)` fires on `c%10==4`, the **/10**
group. **⇒ task 5 = 1000Hz / 10 = 100Hz.**

[Residual, minor]: the exact bit-AND eligibility semantics inside `FUN_000837c0` (what the CURRENT task's
own `+0x24` field physically represents) were not fully re-derived — this rests on the array-index↔param
correspondence plus the task-1 self-consistency check, not a full trace of the mask bits. Recommend a
second, independent confirmation via on-car cadence measurement before treating 100Hz as fully certified,
though confidence is high given the clean self-consistency.

## Consequence

`FUN_00034a72` (boost, `gp-0x6bbe`) and `FUN_00034350` (damping, `gp-0x6bd0`) — both hosted on task 5 —
run at 100Hz, not 1kHz. Their outer torque EMA (alpha=205/1024=0.2002) gives real, non-negligible
attenuation at 6-9Hz (-5.8 to -8.6dB), moderate rather than the near-total loss a naive reuse of a 21Hz
figure would suggest.

`FUN_000389ec` (also on task 5) populates the RAM-resident LERP table `FUN_00038148` reads in its Path-2
stage-2 (X-knots at `gp-0x64b8..`, Y-knots at `gp-0x641c..`, 9 points). It commits its live table once per
10 calls of `FUN_000389ec` — combined with task5=100Hz, **the table only refreshes at 10Hz**, a separate,
slower cadence than the 1kHz rate `FUN_00038148` itself samples it at.

## OPEN — the LERP's own Y-value formula and `X[0]`

`Y[0]=0` is independently confirmed (two sessions, byte-anchored). `X[0]` (the low-extrapolation
threshold, live cell `gp-0x64b8`) is **not** confirmed — it is populated at runtime from an unidentified
per-vehicle source array (`gp-0x6350`/`gp-0x630c` region) via a shared normalization subroutine
(`FUN_0003897a`), neither of which yielded to a single decompile pass (dense median-of-3/shadow-lockstep
boilerplate obscuring the real per-knot formula). If `X[0]>0`, there is a genuine flat-zero band near
small values of the LERP's index — relevant to any probe reading the LERP's output near a sign crossing.
**The V95 telemetry probe's magnitude buckets on `gp-0x6b70` are the intended diagnostic for this**: a
sign bit stuck at a fixed value while the magnitude bucket reads its lowest bin is the signature of this
flat-zero band rather than a genuine absence of crossings.

## Related
[[control-task-tick-confirmed-1khz]] — the control-task (task 1) anchor this result is derived from and extends.
[[accord-plant-model-residual-aggregator-chain]] — the Path-2 chain (`FUN_00038148`→`gp-0x6b70`) this table feeds.
