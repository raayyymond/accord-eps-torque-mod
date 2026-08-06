---
name: reference_accord_7hz_divider_hunt_null
description: Exhaustive hunt for a ~7.8 Hz (period-128, 1000/128=7.8125 or 500/64=7.8125) firmware divider that could explain the 7.79 Hz micro-ratchet line -- NO divider found anywhere in the image, three independent lines of evidence, plus a Python second-method re-scan confirming search_instructions was not undercounting near the assist chain. Retire the divider hypothesis; the line is plant/mechanical.
metadata:
  type: reference
---

2026-08-05, team-lead mission: does a ~1000Hz/128 or 500Hz/64 firmware decimation counter explain the
7.79 Hz micro-ratchet ([[accord-ratchet-characterised-on-route-4f]], [[accord-two-ratchets-micro-is-the-779hz-line]])?
**[EVIDENCE] NO. Three independent closures, all clean.**

## (a) The confirmed RTOS scheduler is algebraically incapable of period 128
`FUN_00014be4`'s rate divider runs on `gp-0x4304`, wraps at **100** (`if (99<c) c=0`), groups
`/1,/2,/5,/10,/100`. Only **{1000,500,200,100,10} Hz** are reachable from the confirmed 1kHz base
(see [[reference_accord_rtos_task_table_and_rate_scheduler]],
[[reference_accord_task5_100hz_live_verified_full_producer_census]]). A mod-100 counter cannot produce
a period-125..129 group — this is a structural proof, not a search result.

## (b) No local per-function decimation counter exists anywhere near the assist chain
Whole-image `search_instructions` (mnemonic blank, catches all opcodes) for every immediate in
125..130 decimal (`0x7d,0x7e,0x7f,0x80,0x81,0x82`) plus `0x3f` (mod-64, for the OSTM0/64 candidate):
**183,429 instructions scanned, ~370 total hits image-wide, ZERO inside any of the 14 known
assist-chain functions** — `FUN_0002214a`(task1)/`FUN_00022ca0`(task5)/`FUN_00034350`+`FUN_00034a72`
(damping/boost)/`FUN_00041464`(common-mode rate)/`FUN_0003aa2c`(aggregator)/`FUN_0003a382`
(resonance/residual)/`FUN_00036388`+`FUN_000352b4`+`FUN_00036c12`(lanes A/B/C)/`FUN_00026c80`(mixer)/
`FUN_0003ad74`(gain-table rebuild)/`FUN_00028ea6`+`FUN_0002a93a`(arb). The only `sar 0x7`/`shr 0x7`
hits inside these functions are **Q7 fixed-point coefficient scaling** (e.g. the known alpha=37/128 EMA
in `FUN_00041464`), NOT counters — confirmed by a full fresh `disassemble_function(0x3a382)`
(0x3a382-0x3a8a7 in full): no `andi`/`cmp` against 127/128 anywhere in it.

**Python second-method (required, per skill, when a null is load-bearing):** raw LE byte scan of the
whole `code.bin` for the `andi 0x7f`/`0x3f` opcode-shaped byte pattern found **68 raw hits vs
`search_instructions`'s 12** — looked like the documented undercounting bug. Spot-checked the 2
candidates nearest assist-chain code (`0x2a88e`, `0x3a6d9` inside `FUN_0003a382`) with
`disassemble_bytes(dry_run=true)`: **both are mid-instruction byte coincidences** (the naive 4-byte
scan straddled real 2-byte `jmp lp`/`mov 0x1,r10` instructions) — not genuine `andi`. All ~25
candidates in the 0x14000-0x50000 app range checked against `get_function_by_address`; none land
inside an assist function. **Confirmed a genuine null, not a `search_instructions` blind spot** —
distinguishes this from the kit's prior cases (`gp-0x671a`, cal `0xC64FA`, the `0x2a904` cal-load
idiom) where the tool genuinely missed real hits.

## (c) OSTM0 (500Hz confirmed / 64 = 7.8125Hz exactly — numerically the CLEANEST candidate) is dead
Fresh `decompile_function(0x1492a)` (the EI trampoline): OSTM0's EIIC (0x2c0) is **not one of its 7
dispatched cases** (0x970,0x600,0x340,0x470,0x110,0x100,0xf0 are the only ones) — falls to the fault
handler `FUN_00014810`. `get_xrefs_to(0xFFFFC000)` (OSTM0CMP) returns only the 2 known boot-time
writes (`FUN_00014c5c`, `FUN_000003b4`); a 3rd hit in `FUN_00052676` decompiled clean and is a
**coincidental immediate match** (0xffffc000 used as a numeric LERP-domain constant passed to
`FUN_00049a90`, not an I/O dereference) — NOT an OSTM0 consumer, false positive of `get_xrefs_to`
matching a literal operand. `0xFFFFC004` (candidate OSTM0CNT) has **zero xrefs at all**. OSTM0 is
initialized at boot and never read again anywhere in the image — not a live periodic source for
anything, torque or otherwise. This corrects/extends [[reference-accord-ostm0-master-tick-rate-derivation]]
and [[accord-pclk-40mhz-and-ostm0-is-500hz]] — confirms "OSTM0 is not the control tick" AND additionally
shows it has no other live use either.

Also checked all 7 EI-trampoline-dispatched interrupts for anything else periodic near 7.8Hz:
`FUN_00061614` (0x970 TSG21I05, highest urgency) is a mod-8 PWM/ADC state-rotation dispatcher, calling
`FUN_0006c5ce` every invocation regardless of the mod-8 phase — unrelated to any /128 gating. TAUA1I1's
period (the DTC18 cadence watchdog, [[accord-dtc18-cadence-watchdog]]) is still `[OPEN]` but that
memory already shows it only sets/clears pass-fail bits, no torque-domain write — structurally
irrelevant even if its window turned out to be ~128ms.

## Elimination table for the boring candidates
- **CAN 100Hz alias/beat**: no integer beat lands on 7.79Hz; `100/13=7.69` sits in the measurement
  spread but needs a `/13` divisor no scheduler in this kit has, AND CAN TX is egress-only —
  structurally cannot write back into a torque command regardless of whether such a divisor existed.
- **Wheel order 1** (`0.489*v`): excluded per [[accord-ratchet-characterised-on-route-4f]] (speed-invariant).
- **Envelope of the ~20.9Hz grind, not a carrier of its own**: not resolved by firmware analysis alone,
  but weakly disfavoured — an envelope still needs SOME ~7.8Hz firmware multiply gating the carrier,
  and none exists anywhere in the image (same null as the divider hunt itself).

## Verdict
**Retire the "1000/128" and "500/64" divider hypotheses. No firmware structure at ~7.8Hz exists
anywhere in `code.bin`, by scheduler algebra + exhaustive immediate-value search + Python re-scan +
the OSTM0 dead-end.** The 7.79Hz line is very likely a genuine plant/mechanical mode, consistent with
[[accord-ratchet-characterised-on-route-4f]]'s "the loop closes inside the EPS + plant — openpilot is
NOT the oscillator" finding (the line is in the torsion bar and angle rate but not in openpilot's
command).

## Related
[[reference_accord_rtos_task_table_and_rate_scheduler]] — the scheduler this closes off as the divider source.
[[accord-pclk-40mhz-and-ostm0-is-500hz]] — OSTM0 rate; this memory adds "and has no live consumer either."
[[accord-0x930-masks-are-state-not-phase-settled]] — the earlier phase-counter red herring this hunt
deliberately did not repeat (confirmed state-mask, not a divisor, before starting).
[[accord-ratchet-characterised-on-route-4f]], [[accord-two-ratchets-micro-is-the-779hz-line]] — the
measured line this hunt was trying to explain.
