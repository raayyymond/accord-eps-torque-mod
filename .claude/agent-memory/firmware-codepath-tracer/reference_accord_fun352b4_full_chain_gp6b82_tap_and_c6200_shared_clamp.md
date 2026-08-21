---
name: reference_accord_fun352b4_full_chain_gp6b82_tap_and_c6200_shared_clamp
description: Full fresh-decompile confirmation of FUN_000352b4 (base-assist/friction map) and FUN_0003aa2c (the aggregator gp-0x6b86 feeds), for the self-interference-cancellation design task. New facts -- gp-0x6b82 is the biquad's own raw input tap (a discrete RAM cell); cal(0xC6200) is a SHARED clamp used in TWO places (Path-2 PID reference AND an inner +-8192 clamp on raw torque inside FUN_000352b4, tighter than the previously-cited +-0x6400 outer bound); the full FUN_0003aa2c aggregator lane/window map; and FUN_000352b4/FUN_0003aa2c/the gp-0x6b98 writer (FUN_00042af8) all share ONE caller (FUN_0002214a, 1kHz task) -- single-tick causality confirmed.
metadata:
  type: reference
---

Found 2026-08-20, `self-interference-cancellation` design task (subagent, reporting to orchestrator).
Program: stock `code.bin`. Two fresh `decompile_function` calls this session
(`FUN_000352b4` @`0x352b4`, `FUN_0003aa2c` @`0x3aa2c`), cross-checked with `search_instructions` and
`get_assembly_context`.

## FUN_000352b4 full chain [EVIDENCE, fresh decompile]

```
gp-0x4f60 (raw torque, Sensor B)
  -> clamp to +-cal(0xC6200)=+-8192              [INNER clamp -- see correction below]
  -> + gp-0x6b4a (>=0 today, cal 0xC616C=0)
  -> clamp +-0x6400=+-25600                       [OUTER clamp, hardcoded immediate, currently slack]
  -> abs, 10-point breakpoint search over gp-0x37fc[] -> LERP
  -> clamp <=0x2fff=12287, x sign(raw), x *(char*)(gp-0x6752)
  -> gp-0x6b7a (shadow gp-0x4cdc, exact-equality lockstep; mismatch -> FUN_0006b9fa)
  -> [2nd limit/interp stage vs an interpolated "friction hold" value]
  -> gp-0x6b82  <== THE BIQUAD'S OWN RAW INPUT TAP (iVar34, Q10 int, /1024 = biquad's float input)
  -> [Honda's biquad, gated cal(0xC649B)==1 && cal(0xC64FA)<=gp-0x671a -- see
     reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm.md]
  -> + gp-0x6b7e (parallel EMA/IIR term off the 32-bit accumulator gp-0x381c)
  -> clamp +-0x3000=+-12288
  -> EXTREME-TORQUE DROPOUT: if |gp-0x4f60| (re-read RAW) > 25600, FORCE gp-0x6b86/shadow TO EXACTLY 0
  -> gp-0x6b86 (shadow gp-0x4cde, exact-equality lockstep; mismatch -> FUN_0006b9fa)
```

**NEW: `gp-0x6b82` is a discrete, readable RAM cell holding the biquad's exact pre-filter input**
(`iVar34`, reused verbatim by the decompiler for both the store to `gp-0x6b82` and the later biquad-gate
math `(float)iVar34 * 0.0009765625`) -- useful as a probe/tap point for anyone instrumenting the biquad
without needing to re-derive its input from the earlier stages.

## 🛑 CORRECTION: cal(0xC6200) is used in TWO PLACES, not one

`build_v*` record and STATE.md's E1/E2 finding established `cal(0xC6200)=8192` as the Path-2 PID
reference clamp (`|gp-0x6ad6| >= cal 0xC6200`, inside `FUN_0003a382`), on the never-edit list because
*"it clamps term 3 and the threshold with the same cell."* **Fresh disassembly this session shows the
SAME cal cell (`tp+0x7200`) is ALSO read inside `FUN_000352b4`** at `0x354ce` (`ld.h 0x7200[tp],r14`),
as a **third, independent use**: an inner min/max clamp on the raw torque value (`gp-0x4f60`) BEFORE the
10-point breakpoint LERP, tighter than the `+-0x6400=+-25600` outer bound that a prior brief/summary had
cited as "the" clamp. Since `gp-0x6b4a` (the term added between the two clamps) is currently ≡0
(`0xC616C=0`), **the value feeding the breakpoint search is effectively bounded to +-8192 today, not
+-25600.** Do not cite "+-0x6400" as FUN_000352b4's effective input clamp without this caveat. Never-edit
status is reinforced, now for a third reason.

## FUN_0003aa2c aggregator -- full lane/window map [EVIDENCE, fresh decompile]

Confirms and completes the partial map on record (STATE.md's "REACHABILITY BUDGET" section covers a
*different* aggregator, the Path-2 PID feeding gp-0x6ad6 -- do not conflate). This is Path-1's
aggregator, feeding `gp-0x6b94`:

| summand | zero-reject window (not clamp -- past it, contributes exactly 0) |
|---|---|
| `gp-0x6b62` | +-8192 |
| `gp-0x6b4c` | +-10240 |
| `gp-0x6ade` | +-1024 |
| `gp-0x6ad4` (resonance) | +-10240 -- **this is the lane `0x3acc4`'s `cmovc 0x0,r6,r13` implements** |
| `gp-0x6b26` (friction-comp/inertia) | +-1024 |
| `gp-0x6bbe` (boost) | +-2048 |
| `gp-0x6bd0` (damping) | +-2048 |
| `gp-0x6b86` (FUN_000352b4's output) | **+-12288 -- the WIDEST window of all**, matches the ceiling FUN_000352b4 itself already clamps to, so this lane structurally never trips its own aggregator gate |
| + `FUN_00036682()` return | (final filtered Sensor-B, unconditional add) |

Sum -> **saturating** clamp +-10240 (NOT zero-reject, a genuinely different nonlinearity from the 8
per-lane gates) -> `gp-0x6b94` (shadow `gp-0x4ce0`, same exact-equality lockstep idiom, mismatch ->
`FUN_0006b9fa`). Readers of `gp-0x6b94`: `FUN_0004503c` (governor), `FUN_0004595a` (redundancy monitor),
`FUN_0007ff08` (boot interlock) -- confirms the pre-existing "three non-aggregator consumers" record
exactly, via `search_instructions` (8 total hits on operand `0x6b94`, `truncated:false`, sole writer
`FUN_0003aa2c` at 3 sites matching its 3-way clamp/mirror pattern).

## Task-rate / causality -- clean single-tick chain [EVIDENCE]

`get_function_callers` on `0x352b4`, `0x3aa2c`, AND `0x42af8` (the function writing `gp-0x6b98`, found
via `search_instructions` on operand `0x6b98`: 2 of >=3 writers at `0x43b52`/`0x43dfc`, 30+ readers,
`truncated:true` at the 40-match cap) **all return the SAME single caller, `FUN_0002214a`** -- the
confirmed 1kHz task. The entire path from raw-torque read through the friction map, the aggregator, and
the final motor-command write executes inside ONE call of ONE 1ms task. Given `FUN_0003aa2c` reads
`gp-0x6b86` (written by `FUN_000352b4`) and the shadow-lockstep idiom implies same-tick freshness,
`FUN_000352b4` must execute before `FUN_0003aa2c`, which must execute before `FUN_00042af8`, within
`FUN_0002214a`'s body. **[BELIEF: inferred from data-flow necessity + the lockstep pattern, NOT from a
direct decompile of `FUN_0002214a`'s call order -- that decompile was not run this session and would
close this to EVIDENCE.]**

**Practical consequence for anyone tapping `gp-0x6b98` from inside `FUN_000352b4`**: since
`FUN_00042af8` runs later in the same tick, a read of `gp-0x6b98` early in the tick (inside
`FUN_000352b4`) yields exactly LAST tick's value -- a clean, deterministic 1-tick (1.000ms) transport
delay, not a race. Phase cost at 7.79Hz: 2.80 deg. At 21-26Hz: 7.6-9.4 deg. Computed directly, not
estimated.

## Related
[[reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm]] -- the biquad this
chain feeds. [[reference_accord_biquad_is_a_notch_v103_armed_and_recentering_priced_short]] -- the notch
characterization and V103 arming. [[reference_v850_search_instructions_base_register_collision_trap]] --
a methodological trap hit while GATE-1-verifying `gp-0x3814`/`gp-0x3818` in the same session.
[[reference_accord_selfinterference_cancellation_design_and_notch_verdict]] -- the design this trace was
produced for, and its honest-comparison verdict against the notch.
