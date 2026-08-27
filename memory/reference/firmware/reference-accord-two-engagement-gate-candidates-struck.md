---
name: reference-accord-two-engagement-gate-candidates-struck
description: "STRUCK: FUN_0002a93a and 0xC6AF0/gp-0x6966, both engagement-gate candidates that looked live and are not. FUN_0002a93a is dead code (0 callers/xrefs, annotated dead since V37) -- a prior memory called it live on a mis-cited correction that was actually about a different function. 0xC6AF0's authority-clamp collapse is inert on every V31+ build because gp-0x6966 is pinned at 0 (V54's on-car probe) -- the LERP sits on its wide-open knot and the collapse never occurs. Both looked like exactly what a relay/switch-not-dose hypothesis needs; the record already held the answer in both cases."
metadata:
  type: reference
---

# Two engagement-gate candidates STRUCK — a structurally real mechanism can be inert, and the record already knew it

2026-08-12. Both surfaced while enumerating engagement-gated nonlinearities for the driver-override
ratchet hypothesis — both looked, structurally, like exactly the kind of relay a "switch, not a dose"
mechanism needs. Both are dead on this car's actual firmware/build lineage. Recording together because
they are one fact: **a plausible-looking candidate needs its own on-car/lineage check before it's ranked,
not after** — the same lesson `feedback-search-the-kit-before-naming-a-cause` and
`accord-check-build-lineage-before-proposing-lever` already carry, now with two fresh instances.

## 1. `FUN_0002a93a` is DEAD CODE — a mis-cited "live" claim

A prior session's memory described `FUN_0002a93a` as a binary all-or-nothing gate on the arb-curve
computation (`if (ramp==0 && no pending request) { whole computation zeroed }`) and called it "very much
live," citing a correction as support. **The citation was mis-attributed**: that correction is about a
*different function*, `FUN_00028ea6` (the real PATH-A arbitration) and its cal gain `0xC646C`, which had
been misread as −1/inert in an earlier session. It says nothing about `FUN_0002a93a` having a caller —
the inferential leap ("PATH-A's chain is live, therefore this function which allegedly feeds it must also
be live") was never independently checked.

**Fresh check**: `get_function_callers(0x2a93a)` and `get_xrefs_to(ram:2a93a)` on `code.bin` — **zero
callers, zero xrefs, both methods.** This matches `builds/v18_v49/build_v37_tva.py`/`builds/v18_v49/build_v38_tva.py`'s own
long-standing annotation, present since those builds: `"FUN_0002a93a (DEAD: 0 callers/xrefs/ptrs)"` — a
fact already on record in the build scripts and never cross-checked against the "live" claim before it
was written.

**Reusable lesson**: a "live, not inert" claim inherited from a *neighbouring* function's correction is
not evidence about the function in question. Check the citation's actual subject, not just its verdict.

## 2. `0xC6AF0` / the authority output-clamp collapse is INERT on everything this kit flies

`gp-0x6966` (AUTHORITY) drives a Q15 LERP at `0xC6AF0` (X=[0,3277,3604,19661,32768],
Y=[32768,32768,0,0,0]) that scales the PID's own output clamp in `FUN_0003a382`. Above authority 3604 the
clamp collapses to a zero-width window, discarding the full P+I+D response regardless of magnitude — read
as a genuine dead-zone/relay that could be muting the PID during sustained engaged holding.

**The seductive part, worth saying plainly**: this is cal-only, single-reader, never touched by any
build — exactly the shape of an ideal, low-risk lever, and the collapse mechanism it describes is exactly
what an engagement-correlated relay hypothesis wants. That is precisely why it will be re-proposed unless
this strike is on record.

**Refuted by [[v54-flashed-authority-measured]]**, from V54's own on-car probe (route `1b`, fault-free):
`gp-0x6966` (the soft-EME windup magnitude) is **identically 0 on every V31+ build** — V31's boost floor
makes the windup that would raise it unreachable. With authority pinned at 0 the LERP sits on its `X=0`
knot, where `Y=32768` — **the clamp is permanently wide open; the collapse this mechanism describes never
occurs on anything this kit has flown since V31.** Flattening `Y` to 32768 would change nothing — it is
already there. The PID is never muted through this path.

## The shared lesson

Both mechanisms are structurally real — the code does exactly what each description says. Both are inert
in practice because of a *value*, not a structural fact: one candidate's host function has no caller at
all; the other's gating variable is pinned by a completely different lever (V31's boost floor) flown
builds ago. **The record already held both answers before either candidate was proposed this session** —
grep the kit's own `memory/` and the build lineage for a candidate's cal/variable before ranking it, not
after.

Related: [[v54-flashed-authority-measured]] · [[accord-check-build-lineage-before-proposing-lever]] ·
[[feedback-search-the-kit-before-naming-a-cause]]
