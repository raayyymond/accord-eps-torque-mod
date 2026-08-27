---
name: reference_accord_gp4f62_not_fixed_delay_and_h0_void_scope
description: gp-0x4f62 is NOT a simple 2(x[n]-x[n-D])/D fixed-sample-delay derivative -- it's a time-normalized difference over an 8-slot ring buffer of gp-0x4f60, with a variable per-call elapsed-tick accumulator (table-looked-up, not constant), and the producer call itself is CONDITIONAL not unconditional every tick. D=cal(0xC6C42)=4 is byte-confirmed but a "peaks at 125Hz" claim does not follow from this structure without resolving the conditional gate and the tick-weight table -- open, not closed. Also: the D5 "H(0)=0 cannot bound sustained rate" proof survives narrowly (true steady state) but its use to argue the term is irrelevant to reduced achievable peak rate does NOT survive once railing (10-33pct measured engaged duty) is considered -- a railed term holds a constant 511ct/4762=10.7pct-of-authority drag through the whole acceleration transient, which never reaches the H(0)=0 steady state.
metadata:
  type: reference
---

# `gp-0x4f62` producer is NOT the assumed fixed-delay formula; and the H(0)=0 proof's precise surviving scope

2026-08-26, `hfmech` task, same session as the sibling band-limit memory. Team-lead assumed
`gp-0x4f62 = 2(x[n]-x[n-D])/D` at fixed 1kHz, D=cal(`0xC6C42`)=4, peaking at 125Hz. Checked fresh
rather than accepted, per the standing "verify from the image" instruction.

## The real structure [EVIDENCE, fresh decompile chain: `FUN_0007e74a` <- `FUN_0007f3f8` <- `FUN_0006bb08` <- `FUN_0002214a`]
`D=cal(0xC6C42)=4` byte-confirmed correct, stock=V107=4. But the actual computation
(`FUN_0007e74a`) is:
```
gp-0x4f62 = 2*(gp-0x4f60[n] - gp-0x4f60[n-D]) / (t[n]-t[n-D])
```
where `gp-0x4f60[n]` is stored into an **8-slot RING BUFFER** (`gp-0x2814`/`gp-0x2804` double-banked
for wraparound), and `t[n]` is a PARALLEL ring buffer of an accumulated "elapsed ticks" counter that
increments by a **variable, table-looked-up amount each call** (`cVar3-cVar9_prev`, indexed by a
rotating state byte `gp-0x4e3d`) — **not a fixed 1 tick per call.** And the call site itself
(`FUN_0007f3f8`, a ~250-line multi-mode DTC/fault state machine) invokes `FUN_0007e74a()`
**conditionally** (`if (cVar10=='\x01') FUN_0007e74a();`), not unconditionally every tick.
🛑 **`FUN_0007f3f8` runs on the confirmed 1kHz task-1 dispatch, SAME `0xd30` state mask as
`FUN_00041464`/`FUN_00036c12`** (traced via `FUN_0006bb08`<-`FUN_0002214a`) — so it IS on the same
clock as gp-0x6b26's cascade, that part of the framing is right. What's not confirmed is that
`gp-0x4f62` UPDATES every one of those ticks, or that its effective D corresponds to a fixed time span.

## Verdict — NOT CLOSED [explicit gap, not a guess]
**"Peaks at 125Hz" does not follow from this structure as read.** If `cVar10` gates true every tick for
the live/engaged case and the tick-weight table is uniform, team-lead's formula may still hold as an
approximation with the right effective D — but neither was confirmed this session. Next step: trace
`cVar10`'s write sites and the `gp-0x4e3d`/`gp-0x4e9e` lookup table to determine whether the engaged/
mode-24 update cadence reduces to something fixed. Not attempted further — flagged as a genuine open
item rather than guessed at. **Do not cite a peak frequency for gp-0x4f62 from this session.**

## The H(0)=0 proof — precise surviving scope [mixed EVIDENCE/BELIEF]
The literal claim ("a truly sustained constant rate produces zero acceleration in steady state, so
gp-0x6c2c settles to 0 regardless of K") is unaffected by railing and remains TRUE — a real steady
state never reaches the clamp because there's no acceleration content left to feed it.
**What does NOT survive**: using that proof to argue the term is irrelevant to a REDUCED ACHIEVED PEAK
RATE within a bounded real maneuver. A real maneuver has a transient (acceleration) phase before any
steady state; if `gp-0x6b26` rails during that phase it holds `sign(accel)×511` — a torque that does
NOT decay as the smoothly-scaling linear analysis assumed. `511/4762 = 10.7%` of governor authority
(cal-confirmed by `ratecap` this session), applied for as long as the transient stays railed — and
route 1e's measured rail duty (10-33% of ENGAGED time in the 10-40km/h bins) shows this is routine, not
an edge case. Cannot independently derive the measured 3.85× d(rate)/dt collapse (that needs closed-
loop dynamics or the on-car number, not open-loop arithmetic) — but the kit's own clamp-duty-vs-dose
numbers are ALREADY steeply super-linear (×1.5→0.10%, ×2.0→1.94%, ×3.0→9.98%, i.e. a 2× dose change
gave ~100× duty change), which is a structurally sound, code-grounded reason a modest linear dose
increase can produce a much-larger-than-linear rate-of-rate collapse once railing is in the loop.

## Related
[[reference_accord_gp6b26_alpha0_shared_alpha2_isolated_bandlimit_sweep]] (sibling finding, same
session), [[accord-gp6752-is-the-frame-converter-and-k1-makes-it-lighter]] (earlier, correct
identification of gp-0x4f62 as `d(gp-0x4f60)/dt`, not further specified there).
