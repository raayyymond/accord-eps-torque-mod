---
name: reference-accord-notch-biquad-search-negative-result
description: Searched the full LKAS/base-assist torque command path (arb IIR, all 5 assist-shaping lanes, r24/r26, comp-add, boost, filtered-Sensor-B, return-centre, shaper, governor, the shared FUN_0004613e monitor) for a notch/band-stop/biquad (two delayed states, cross-multiplied coefficients) structure. Found none -- every filtering idiom in this path is single-pole EMA, a plain accumulator, or median/rank-select. Negative result, not exhaustive whole-image.
metadata:
  type: reference
---

Tasked by team-lead 2026-07-20/21: production EPS firmware normally band-limits the assist loop with a
notch/phase-lead compensator to suppress exactly the hands-off column resonance this kit is chasing
(V38's 21Hz hands-off-only vibration). Looked for biquad-shaped arithmetic — two persisted delay states
(x[n-1]/x[n-2] or y[n-1]/y[n-2]) combined via distinct cross-multiplied coefficients (b0,b1,b2,a1,a2 or
similar) — as opposed to the single-pole EMA idiom (`state += (target-state)*gain>>10`, ONE persisted
state) this kit has catalogued everywhere else.

## What was checked this session [VERIFIED per-function]

- **Arb IIR (`gp-0x3d3c`, pole 0.96875, [[reference-accord-lkas-lane-is-a-lowpass]])** — `search_instructions`
  on operand `-0x3d3c` across all 185,722 instructions: exactly 2 hits, both in `FUN_00028ea6` (one
  `ld.w` read, one `st.w` write). A single persisted 32-bit state with no paired second state anywhere
  near it. Cannot be part of a biquad by construction (a biquad needs >=2 states). Confirms genuinely
  single-pole, not a mislabeled biquad section.
- **`FUN_0004613e`** — the shared "monitor" call invoked at the top of nearly every lane function (boost,
  damping, friction, comp-add, governor, aggregator — all with a distinct magic ID like
  `0x3702`/`0x3638`/`0x4179`/`0x38b3`/`0x3c35`/`0x3c35`). Decompiled in full this session:
  ```c
  void FUN_0004613e(undefined2 param_1, undefined2 *param_2, *param_3, *param_4, *param_5) {
      gp-0x6920 = param_1; gp-0x6918=*param_2; gp-0x691a=*param_3; gp-0x6916=*param_4; gp-0x691c=*param_5;
      FUN_00016de6(0x1c, param_1, 1, 1);
      return;
  }
  ```
  Not a filter — a fault reporter. Copies its 4 pointer args into a fixed scratch struct and
  unconditionally calls the hard-shutdown-eligible DTC path `FUN_00016de6(0x1c,...)`. Each lane calls it
  only on its OWN pre-computed redundancy-mismatch condition (two IIR-tracked copies of a signal
  diverging beyond a threshold), never as part of normal signal processing. This rules out the single
  function common to almost every lane as a hidden filter.
- **`FUN_00036682`** (filtered Sensor-B term, most filter-shaped of the group): 3-tap median/rank-select
  (bounding a candidate between two neighbors) feeding a single-pole EMA on a 32-bit accumulator
  (`gp-0x37ac`, gain `tp+0x73d2`). No a1/a2 feedback coefficients, no y[n-2] term — median-select + lag,
  not a biquad.
- **`FUN_0003a382`** (resonance lane, [[reference-accord-fun3a382-resonance-lane-unfiltered-correction]]):
  3 stages, two are algebraically-identity "lags" (gain=1024=unity, confirmed by direct byte read) and
  one is a raw one-sample difference (derivative). None combine into a 2nd-order structure.
  `FUN_00034350` (damping), `FUN_00036c12` (friction), `FUN_00034a72` (boost rate limiter),
  `FUN_000456a4` (comp-add term) — all the same single-MAC `state += (target-state)*gain>>10` idiom, one
  persisted state each, byte-verified this session and in prior sessions.

## Verdict

**No biquad-shaped arithmetic (two delayed states, cross-multiplied coefficients) was found anywhere in
the traced torque command path** — arbitration, the 9-lane demand aggregator (boost/friction/damping/
resonance/magnitude/r24/r26/filtered/return-centre), governor, post-governor comp, or shaper. The
filtering vocabulary is uniformly single-pole EMA, plain accumulators, or median/rank-select.

**This is NOT an exhaustive whole-image search.** No blind byte/opcode-pattern sweep was run outside the
named functions and their immediate neighbors (185,693 instructions total in the image; this session's
coverage is maybe 2-3k instructions of hand-verified decompile, layered on prior sessions' coverage of
the same subsystem). Between this session and the accumulated prior tracing, essentially the entire
CAN-input-to-motor-output torque path has now been decompiled at least once — but two regions were
explicitly NOT checked and are the natural next place to look if this thread continues:
1. The CAN RX handler(s) that produce `gp-0x4f60`/`gp-0x4f62` in the first place (upstream of everything
   traced here) — a notch on the raw sensor signal before it ever reaches the command lanes would not
   show up in any of the functions above.
2. The FOC/motor-current-loop functions downstream of `gp-0x6b98` (delivered torque command) — a
   current-loop notch would live in current-control code, not the torque-command shaping path this
   session covered.

## Related
[[reference-accord-lkas-lane-is-a-lowpass]] — the arb IIR this session re-confirmed as single-state
[[reference-accord-gp67ac-aggregator-lane-suppression-gate]] — found in the same sweep
[[reference-accord-damping-friction-returncentre-torque-gates]] — found in the same sweep
