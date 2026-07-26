---
name: reference-accord-generic-math-helpers-49a5a-49a78-49a90
description: Three tiny generic math helpers (abs, min, clamp/median-of-3) at FUN_00049a5a/FUN_00049a78/FUN_00049a90 that recur constantly across the Accord TVA-A160 firmware — recognize them by shape/address instead of re-decompiling every call site.
metadata:
  type: reference
---

# Generic math helpers — Accord TVA-A160

These three adjacent small functions are called dozens of times across the codebase (arb, governor,
shaper, engage-SM, compensation terms). Recognizing them by address saves re-decompiling the same
2-5 line function every time it shows up in a new trace.

## FUN_00049a5a(int x) = abs(x)

```c
int FUN_00049a5a(int param_1) {
  bool bVar1 = -1 < param_1;
  int iVar2 = param_1 * bVar1 + in_r10 * !bVar1;   // decompiler artifact, effectively param_1 when >=0
  if (!bVar1 && (iVar2 = -0x80000000, param_1 != -0x80000000)) iVar2 = -param_1;
  return iVar2;
}
```
Standard `abs(int)` with the INT_MIN edge case handled. **24 callers image-wide** (governor
`FUN_0004503c`, angle-deadband `FUN_0003c7fc`, decider `FUN_00040d58`, LKAS mixer functions,
`FUN_0003fc16`, `FUN_0003bd7c`, etc.) — a shared utility, never rate/torque-specific by itself.

## FUN_00049a78(a, b) = min(a, b)

```c
undefined2 FUN_00049a78(uint param_1, uint param_2) {
  return param_2 * (param_2 <= param_1) + param_1 * (param_2 > param_1);
}
```
Plain `min(a,b)`. Frequently chained (`x = FUN_00049a78(x, sample)`) inside redundant-channel voting
loops to fold a running minimum across several samples — see the governor's Q15-bound chain below.
⚠ Ghidra's decompiler sometimes drops the second argument from the caller-side pseudocode (calling
convention / register-liveness artifact) — the raw disasm always shows both args in play; don't
conclude a caller is "1-argument" from decompile output alone.

## FUN_00049a90(value, lo, hi) = clamp(value, lo, hi) — a median-of-3

```c
int FUN_00049a90(int param_1, int param_2, int param_3) {
  // sign-magnitude-safe overflow arithmetic; net effect: returns the MEDIAN of the three inputs.
  // When param_2 <= param_3 (the overwhelmingly common calling pattern: param_2=-bound, param_3=+bound),
  // this degenerates to the textbook clamp(param_1, -bound, +bound).
}
```
Same family as `FUN_00049a5a`/`FUN_00049a78`, called via `jarl` immediately after computing a
`±bound` pair. Confirmed call site: `m_motor_torque_governor` (`FUN_0004503c`) at `0x453fe`:
`FUN_00049a90(gp-0x6b94, -bound, +bound)` where `bound = (governor × Q15-factor) >> 15` — see
[[reference-accord-gp4f64-three-consumers]] for the full chain this feeds.

## Why this matters

These three showing up together (`abs` → `min` → `clamp`) is the recurring idiom for "compute a
magnitude, fold it into a running bound via redundant-channel voting, then clamp a value to that
bound." Recognizing the shape short-circuits re-deriving it from scratch — as happened when tracing
the Q7 addendum's Q15 multiplicand question (2026-07-19): the governor's bound-setting chain turned
out to be a literal `0x8000` (unity Q15) seed combined ONLY via `FUN_00049a78`/`FUN_00049a90` calls
across a 3-channel redundant-sensor loop, never amplified — see [[reference-accord-gp4f64-three-consumers]].

## Related
- [[reference-accord-gp4f64-three-consumers]] — governor Q15-bound chain built from these helpers
- [[reference-accord-fun456a4-gate-no-hysteresis-and-index-identity]] — uses abs()+min() for gp-0x6a10
