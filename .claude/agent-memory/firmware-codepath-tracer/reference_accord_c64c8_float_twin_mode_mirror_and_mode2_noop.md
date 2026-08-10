---
name: reference_accord_c64c8_float_twin_mode_mirror_and_mode2_noop
description: FUN_00043e44 (the shaper's float twin) independently re-reads the SAME 0xC64C8 mode byte and 0xC61D4 static cal as the shaper's own 0x431CC dispatch, and reproduces the identical 3-way branch and clamp bounds -- so a mode switch alone cannot desync the twin for this term. But mode 2's formula, with 0xC61D4=0 (stock), is a byte-exact no-op vs mode 0: the pre-clamp already bounds gp-0x6acc to +-8192, well inside mode 2's +-12288 post-clamp. Mode 2 offers NO filtering capability even nonzero -- 0xC61D4 is a flat scalar, not a table, so it can only ever be a static additive bias, never a low-pass. Closes thread C of the lever-hf HF-selectivity brief (2026-08-09).
metadata:
  type: reference
---

# `FUN_00043e44` mode-branch mirror + `0xC64C8` mode-2 no-op proof (2026-08-09, `lever-hf` session)

[EVIDENCE, fresh `decompile_function(0x43e44)`, code.bin stock] Dispatched to answer: does switching
`0xC64C8` (the aggregator mode selector read by the shaper at `0x431CC`, per
[[accord-aggregator-reaches-motor-via-gp6acc-bridge]]) desync `FUN_00043e44`'s float twin
([[reference_accord_shaper_float_twin_blocks_filter_insertion]])?

## The twin re-derives the shaper's own mode dispatch, byte-exact

`FUN_00043e44` reads `tp+0x74c8` (=`0xC64C8`, the SAME tp offset the shaper's `0x431CC` reads) and
`tp+0x71d4` (=`0xC61D4`, the SAME static cal the shaper's `0x431C8` reads):

```c
fVar12 = clamp_or_zero(gp-0x6acc / 1024, +-8.0)     // pre-computed unconditionally, matches the
                                                      // shaper's cmovc pre-clamp at 0x431D0-D8 exactly
mode = *(byte*)(tp+0x74c8)
if   mode == 1: target = cal(tp+0x71d4)/1024                    // matches shaper r15==1 exactly
elif mode == 2: target = cal(tp+0x71d4)/1024 + fVar12            // matches shaper r15==2 exactly
else:           target = fVar12                                  // matches shaper default exactly
target = clamp(target, -12.0, +12.0)   // = +-12288 raw, matches shaper's mode-2 +-0x3000 clamp exactly
```

This is a byte-exact structural mirror of the shaper's `0x431CC-0x43204` dispatch — same two tp-relative
cal reads, same three-way branch, same final clamp bound. **Switching `0xC64C8` alone cannot desync this
ONE term of the twin from the shaper** — both independently compute the identical formula from the
identical raw inputs (`gp-0x6acc`, `0xC61D4`).

## But mode 2 is a provable no-op today, and never a filter regardless of cal value

`0xC61D4` = 0, confirmed via `read_memory(0xC61D4)` this session (code.bin stock). With that:
```
mode 2: target = clamp(0 + clamp_or_zero(gp-0x6acc,+-8192), +-12288)
      = clamp_or_zero(gp-0x6acc, +-8192)                          [since +-8192 is already inside +-12288]
      = mode 0's output, exactly
```
**Mode 2 is byte-exact identical to mode 0 with the current cal.** Even with `0xC61D4` nonzero, mode 2's
formula is `static_scalar + gp-0x6acc, clamped` — a flat ADDITIVE DC BIAS, no history, no time constant.
`0xC61D4` is a single u16 cal (not a table), so mode 2 **structurally cannot become a low-pass or any
other frequency-selective element**, regardless of value.

⇒ **`accord-aggregator-reaches-motor-via-gp6acc-bridge`'s open item ("mode 2 blends... formula not fully
characterized") is now closed: it's an additive bias, not a filter.** Any hope of using `0xC64C8`=2 as a
cal-only insertion point for HF filtering is retracted — structurally impossible, not merely untested.

## Residual, not closed this session

`FUN_00043e44` is a much larger parallel plant-model re-derivation beyond this one term — it independently
predicts `gp-0x6b98` from ~10 other raw cells (`gp-0x6b94`, `gp-0x4f64` governor ceiling, `gp-0x6bf0`,
`gp-0x6b00`, `gp-0x6af6`, `gp-0x6b0a`, `gp-0x4f60`, `gp-0x6b4a`, `gp-0x6966`, `gp-0x6a28`, `gp-0x6752`
polarity), sums ~7 independent divergence flags (weights 1/2/4/8/16/32/64) into a bitfield, and escalates
via a 3-state debounce (~0.01s dwell, matches the "10ms" in
[[reference_accord_shaper_float_twin_blocks_filter_insertion]]) before `FUN_000462e6(0x3f1b,...)` →
DTC 0xF00049. None of those OTHER terms are mode-gated — a filter inserted anywhere else on the spine
still needs to keep ALL of them in tolerance, independent of `0xC64C8`. Not hand-traced to closed form
(V850 decompile variable-slot reuse made it slow) — flag as [BELIEF, structure sketched not fully
verified] if it becomes load-bearing.

## Related
[[reference_accord_shaper_float_twin_blocks_filter_insertion]] — the twin's overall blast radius and
phase budget this session's finding refines (the mode-2 sub-question specifically).
[[accord-aggregator-reaches-motor-via-gp6acc-bridge]] — repo memory whose open item this closes.
