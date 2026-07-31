---
name: reference-accord-gp6ac2-ceiling-only-and-no-motor-command-feedforward
description: gp-0x6ac2 (sign-mismatch resolver-rate/command detector) is a ceiling-only signal in all 4 real consumers; exhaustive read of the boost shaper/damper/aggregator found zero motor-command (gp-0x6b98) feedforward anywhere in the torque-to-assist chain
metadata:
  type: reference
---

**2026-07-30, "motor-reaction compensation" trace requested by team-lead (positive-feedback-through-torque-sensor
hypothesis for the ~21 Hz grinding).** Full findings sent via SendMessage; durable facts below. Program: stock
`code.bin` only (no experimental image was open this session).

## gp-0x6ac2 fully resolved

**Producer** `FUN_00041464` (0x41464): reads `gp-0x6b98` (delivered motor command) at `0x41672`
(`ld.h -0x6b98,gp,r16`), compares its sign against filtered resolver-rate, and on mismatch sets
r29 = `|filtered_rate|>>10` (`0x41682-0x41686`) else r29=0 (`0x41688`). Real store `0x418e0`
(`st.h r29,-0x6ac2,gp`), symmetric copy `0x41b30`/`0x41b44` for the parallel branch — both gated by a
`0x49D6B173`+tp+0x50eb/0x50ee CRC "manufacturing config" selector shared with the 3 sibling cells
(gp-0x6abc/6abe/6ac0), almost certainly inert on stock (not independently re-verified this session).
Also gated: forced to sentinel 0xFFFF if `|gp-0x6b98| > ~8192`. Confirms and pins addresses for
[[reference_accord_boost_index_input_is_resolver_rate_not_torque]]'s prior characterization.

**Every consumer — cross-checked two ways** (Ghidra `search_instructions`, 12 hits `truncated:false`;
independent full-image Python byte scan, both disp16 encodings, byte-by-byte unaligned) — **agree
exactly, 12/12, zero elsewhere in the 1,048,576-byte image.** 4 are the producer's own re-reads +
`FUN_00041b8e` (established float-lockstep shadow twin). The 4 real external readers:

1. `FUN_00034350` (0x346a4, the velocity-proportional damper) — gp-0x6ac2 plausibility-gated
   (`<0x32c9=12999`, else fallback cal **0xC6158 = 512**), indexes mode-array LERP **`0xC77A0[mode]`**
   (12 pointers, byte-read: 0xC0E068…0xD209C), clamps the raw damping product to ±ceiling at
   `0x34720-0x34762`, writing `gp-0x6bd0`. **gp-0x6ac2 never appears in the raw-damping product** —
   pure ceiling.
2. `FUN_000347b8` (0x347c0) — the FLOAT-domain lockstep twin of #1 (recomputes same ceiling via a
   float table at tp+0x7554/0x7558, populates `gp-0x6bc4/6bc6/6bc8/6bca` shadow cells FUN_00034350
   reads at entry). Same ceiling role, ASIL redundant-computation pattern, not a second mechanism.
3. `FUN_00042af8` (0x42f42) — inside the already-mapped corridor/Monitor-1 region
   ([[reference_accord_v48b_monitor1_dtc1c_notch_safety_closed]]). Plausibility-gated identically,
   indexes a second small LERP at cal **0xC6762-0xC676C** (raw bytes:
   `bc0220034c0400000006000800000700`, breakpoint/value split not decoded), producing a ceiling that
   symmetrically clamps a quantity at `0x43136-0x43170` feeding directly into the Monitor-1 int/float
   shadow-lockstep check at `0x43172-0x43186` — the exact site already proven a safe redundant-
   computation DTC gate. Again a ceiling, not a subtraction.
4. `FUN_00043e44` (0x4434e, report-only, [[reference_accord_fun43e44_report_only_and_gp6acc_slew_limiter]])
   — sole output `gp-0x6906` independently confirmed **1 total image-wide access** (the write itself,
   `0x449fa`), zero readers. Contains a literal `-(gp-0x6b98/1024 - x)` subtraction as one diagnostic
   bit-flag input, but feeds nothing live.

**Verdict: gp-0x6ac2 is a ceiling-only signal in all 4 real consumers, unanimously. Despite the evocative
"counter-torque detector" framing, it never scales, gates-open, or subtracts a compensation term
anywhere.**

## No motor-command/current feedforward found in the torque-to-assist chain

Full-decompile read (not skimmed) of the three functions that process torque into assist:
- `FUN_00034a72` (0x34a72, the boost/assist-amplitude shaper = golden model's `base_driver_assist_lane`,
  = the V59/V60 "parametric pump" function) — **zero references to gp-0x6b98 anywhere in its body.**
- `FUN_00034350` (the damper, above) — zero references to gp-0x6b98.
- `FUN_0003aa2c` (the aggregator, sums both at gp-0x6b94) — flat 9-term additive sum (iVar9 + iVar19 +
  gp-0x6ad4 + gp-0x6b26 + **gp-0x6bbe**(boost) + **gp-0x6bd0**(damper) + gp-0x6b86 + iVar21 + iVar16 +
  `FUN_00036682()`), clamp ±10240 → gp-0x6b94. Each term individually plausibility-windowed, not scaled.
  **Zero references to gp-0x6b98.** gp-0x6b94 confirmed (9 hits) to feed `FUN_0004503c` (the state-4
  governor), continuing into the segment-E corridor/authority chain toward gp-0x6b98.

**The only two places gp-0x6b98 appears anywhere in this region are (i) the gp-0x6ac2 sign-detector
(a ceiling input, not a correction) and (ii) the report-only FUN_00043e44 (zero live readers). Clean,
fully-verified negative: no motor-torque/current feedforward compensation exists anywhere upstream of
the boost curve in stock code.bin.**

One relevant positive: the damper (gp-0x6bd0) IS genuine velocity-proportional damping keyed on motor
resolver rate (gp-0x6abe/gp-0x6ac0), sign forced to -sign(rate) — the closest thing to "motor-reaction
awareness" in this firmware. But per [[accord-gp6a5e-producer-chain-and-creep-zero-damping]], FactorC's
Y[0]=0 in all 34 mode tables below 35 km/h, so this term is arithmetically zero at creep speed — the
exact regime where the grinding is worst.

## Loop map (for the positive-feedback-through-torque-sensor hypothesis)

Firmware gains in the loop: 0xCA4F4[mode]/0xCA154[mode](speed)/0xCA23C[mode]/0xC7970[mode](ceiling)/
0xCA06C[mode]→0xD2006=102(slew, V60's lever)/0xCA324[mode]/0xCA40C[mode] in the boost shaper;
0xC9CCC[mode]/0xC9E9C[mode](speed)/0xC9DB4[mode]/0xC9F84[mode](rate)/0xC77A0[mode](ceiling) in the
damper. No LKAS-exclusive decoupling point found in this chain (every lever is shared with base assist,
consistent with V60's GATE-2 note in STATE.md). Physical legs (motor→column twist→torsion bar→sensor
readback; motor→resolver→rate feedback) are NOT firmware and were not further characterized this
session.

## Open items
- gp-0x4f60's own ADC/CAN producer chain not re-audited this session for a hidden correction step.
- `FUN_00036682()` (one of the aggregator's 9 terms) not traced.
- Second gp-0x6ac2 LERP (0xC6762-0xC676C) breakpoint/value layout not decoded, bytes only.
- Q4 (observer/plant-inverse) is a strong-but-not-exhaustive negative — did not search every gp-0x4f60
  reader program-wide.
