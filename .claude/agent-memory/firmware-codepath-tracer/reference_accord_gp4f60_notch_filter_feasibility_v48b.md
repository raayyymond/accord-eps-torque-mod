---
name: reference-accord-gp4f60-notch-filter-feasibility-v48b
description: V48B feasibility study for a 21.4Hz notch on Sensor-B torque gp-0x4f60 -- gp-0x4f60 is a SHADOW-LOCKSTEP pair (shadow gp-0x4486, mismatch -> fault index 0x17, same severity class as the governor shadow), consumed by 2 no-debounce-adjacent hard-shutdown monitors, 2 CAN broadcasts, a fault-log builder, and diagnostic snapshot packers -- recommends a FILTERED COPY (new RAM cell) over source-filtering, with exact hook sites, cave, and RAM addresses.
metadata:
  type: reference
---

# V48B notch-filter feasibility (2026-07-21) -- injection point, cave, RAM, safety verdict

Dispatched as a standalone feasibility study (not a build) for inserting a 21.4Hz 2nd-order notch
(biquad, ~8dB, Q~5) on Sensor-B/TAS torque `gp-0x4f60` upstream of the 5+ carriers that each
independently read it. Full GhidraMCP trace on stock `code.bin`, all findings address/decompile-verified
this session (not carried from an older claim without re-check).

## Producer -- NOT a single write site, but a single logical unit

`gp-0x4f60` (abs `0xFEDF30A0`) producer = `FUN_0007f3f8` (+ helper `FUN_0007ec34`, called on the
fault/reset sub-path). 4 store sites inside `FUN_0007f3f8`: `0x7f934`(zero-fault), `0x7f9c8`(**real
value**, `st.h r26`), `0x7fce6`(learned-gain writeback, `st.h r8`), `0x7fd1a`(zero-fault). Plus one zero
store in `FUN_0007ec34`@`0x7f2ea`. Producer call chain: `FUN_0007f3f8` <- `FUN_0006bb08` <-
`FUN_0002214a` (the confirmed ~1kHz control task, see [[control-task-tick-confirmed-1khz]]).

`get_xrefs_to(0xFEDF30A0)` returns a **misleading "No references found"** (the documented gp-relative
xref-engine false-zero). Corroborated with `search_instructions(operand_pattern="4f60")`: **74 matches,
186069 instructions scanned, truncated:false** -- this is the authoritative reader/writer set.

## NEW FINDING: gp-0x4f60 is a shadow-lockstep pair

`FUN_0007f3f8` decompile shows every touch of `gp-0x4f60` bracketed by a consistency check against a
shadow cell `gp-0x4486` (abs `0xFEDF3B7A`): if the two already agree, both are overwritten with the same
new value; if they disagree, `FUN_0006b9ee(gp-0x4486)` fires. Freshly decompiled `FUN_0006b9ee`:
```c
void FUN_0006b9ee(undefined4 param_1) {
  *(undefined4*)(gp-0x4d6c) = param_1;
  FUN_0006ce7c(0x17);
}
```
Hard-codes fault index `0x17` -- the SAME index CLAUDE.md's "GOVERNOR BULLET CORRECTION" already
established as hard-fault-eligible (`record[+8]&0x41`, motor-off + power cycle) for the governor's own
shadow pair (`gp-0x4f64`/`gp-0x448a`). This is a generic shadow-corruption fault index shared across
multiple variables, not governor-specific -- `gp-0x4f60` is under the identical class of redundancy
monitoring. `FUN_0006ce7c(0x17)` itself only latches a pending-fault byte (`gp-0x444f`/`gp-0x4e53`); the
downstream escalation to `FUN_00016de6` was NOT re-traced this session (severity carried forward from the
governor precedent, flagged as inference not fresh re-derivation).

`gp-0x4f62` (the finite-difference feeding r24/r26, see [[reference-accord-r26-adaptive-lane-full-trace-and-sign]])
has the identical shadow pattern against `gp-0x4488` (abs `0xFEDF3B78`). Its producer `FUN_0007e74a` is
called from INSIDE `FUN_0007f3f8`, immediately after the `gp-0x4f60` stores settle each cycle.

## Reader classification (74 hits / 40 functions) -- key groups

- **2 hard-shutdown monitors, both read gp-0x4f60 directly, both called only by FUN_0002214a (same task
  as the producer):** `FUN_00042af8`@`0x42c20` (Monitor 1, int corridor calc: `gp-0x4f60` clamped
  +/-0x6400 [+gp-0x6b4a if gated by `tp+0x74cb`] -> `gp-0x6af8` "fight trigger" -> DTC 0x1c path) and
  `FUN_00043e44`@`0x43eda` (Monitor 2, the FLOAT re-derivation of the IDENTICAL corridor calc, gated by
  the SAME `tp+0x74cb` flag -> DTC 0x1d, **no debounce**, see [[reference-accord-damping-clamp-dtc1d-trap]]
  for the pattern). These are a genuine int/float lockstep pair on gp-0x4f60 itself, not just on a
  downstream torque command.
- **2 CAN broadcasts:** `FUN_00055c42`@`0x55c50` (CAN 399 `STEER_TORQUE_SENSOR=-(gp-0x4f60*125/128)`,
  see [[reference-accord-gp4f60-is-sensor-b-column-torque]]) and `FUN_00055616`@`0x55624` (a second,
  unidentified CAN signal `-(gp-0x4f60>>2)`).
- **Diagnostic/fault-log:** `FUN_00056518`@`0x5654a` (packs Monitor-2's own logged fault params +
  gp-0x4f60 + gp-0x6b98 -- a fault-snapshot builder) and `FUN_00059912`/`FUN_00059e7a` (generic
  switch-dispatched UDS/RAM-readout packer, case 9/10 include gp-0x4f60 raw).
- **Cross-channel decoder, same code family as the producer, role unresolved:** `FUN_0008159e`/caller
  `FUN_00080a54`@`~0x81578` -- same per-channel calibration-table style as `FUN_0007f3f8`
  (`gp-0x5060+iVar12` etc.), consumes gp-0x4f60 inside its OWN channel's math. Candidate for a Main/Sub
  torque-sensor correlation check (Honda DTC C1420 -- no `"C1420"` string exists in the image,
  `search_strings` 0 hits, consistent with DTC text not being stored on-ECU). **NOT cleared, flagged open.**
- **Named 21Hz carriers (5, confirmed):** `FUN_0003a382`(resonance)@`0x3a6ca,0x3a7ca`;
  `FUN_0002c478`("type-8")@`0x2c480` (fresh decompile confirms `(gp-0x4f60 * cal[tp+0x746c])>>15` --
  reuses the SAME `0xC646C` cell already flagged in [[reference-accord-fun3a382-resonance-lane-unfiltered-correction]]
  as V38's 4x LKAS gain, corroborating this is a real fast carrier); `FUN_00034a72`(boost)@`0x34ace`;
  `FUN_000352b4`(magnitude)@`0x354d2,0x35aa4`.
- **6th carrier NOT in the operator's original list:** `FUN_00034350` (the DampFactors damping function,
  V44/V47 lineage) reads gp-0x4f60 directly @`0x34392`, separate from its gp-0x6a5e/gp-0x6ac0 gain-schedule
  inputs.
- **Arbitration:** `FUN_00028ea6` (`m_steer_torque_arbitration`)@`0x28f26,0x29a90` reads raw torque
  directly (separate from its known low-pass IIR `gp-0x3d3c`) -- plausibly driver-override/engagement
  threshold logic, untouched by any prior build. Do not perturb without a dedicated trace.
- **~14 unclassified** (coarse region triage only): `FUN_0001bf88`,`FUN_0001c1ce`,
  `FUN_0002a93a`(**known DEAD**, 0 callers, per [[v36-debounce-sm-root-cause-and-build]]),`FUN_0002b62c`,
  `FUN_0002db94`,`FUN_00033d10`,`FUN_00036682`(**known**: "filtered Sensor-B term", tau~170 cycles,
  already well-filtered, NOT a fast carrier),`FUN_00036828`,`FUN_0003b49a`,`FUN_0003b66a`,`FUN_0003b8f6`,
  `FUN_0003f884`,`FUN_0003fc16`,`FUN_0004c780`,`FUN_0004d8f0`,`FUN_0004de0c`,`FUN_0004e378`,`FUN_0004e82e`,
  `FUN_0004fbde`,`FUN_00069b8e`(a cascaded torque/command threshold check near the FOC/resolver region --
  gates on gp-0x6b98, gp-0x6abc, gp-0x4f60 in sequence, not resolved).

## Recommendation: FILTERED COPY, not source-filter

Hook once, immediately after `FUN_0007f3f8`'s real-value store settles (after `0x7fce6`, before/around its
`FUN_0007e74a()` call) -- read gp-0x4f60, run the biquad, store to a NEW unshadowed RAM cell. This never
touches `gp-0x4f60`/`gp-0x4486`, so it has ZERO interaction with the shadow-lockstep mechanism and ZERO
effect on the 2 hard-shutdown monitors, the 2 CAN broadcasts, the fault-log builder, or the diagnostic
snapshot packers -- all of which structurally want the raw value. Cost: 7 read-site repoints across 5
functions (listed above with exact addresses); does NOT cover r24/r26 (they derive from gp-0x4f62, one
hop downstream via `FUN_0007e74a`, not from gp-0x4f60 directly) -- acceptable because r24 is already
V39-suppressed and r26 is V42-zeroed in the current build lineage, but this is a real scope gap, not
closed by this design, and should be stated to the operator explicitly.

Source-filtering (rewriting the producer's store) was evaluated and NOT recommended: mechanically doable
(write the same filtered value to both gp-0x4f60 and gp-0x4486 in lockstep) but it unconditionally injects
new filter dynamics into flight-critical fault logic (2 monitors, one with NO debounce) whose tolerance
budgets were never validated against a filtered input, plus changes what's broadcast on 2 CAN signals and
what diagnostics see -- for a marginal implementation-complexity saving over the filtered-copy design.

## Cave and RAM (freshly re-verified this session, not just cited)

- Cave: `0xC4B34`-`0xC4FEF`, 1212 bytes, `read_memory` confirms every byte `0xFF` this session. Inside the
  `[0x13000,0xC4FFC)` CRC block (any occupant needs that block's CRC refreshed). Not physically near the
  injection site (0x7f3f8) or the carriers (0x2c478-0x3a382); no closer cave was searched for.
- RAM: `gp-0x1500`(0xFEDF6B00, 16-bit) + `gp-0x14E0`(0xFEDF6B20, 32-bit) -- `search_instructions` for
  "1500"/"14e0" reproduced the prior session's zero-reference finding independently. `read_memory` at the
  absolute addresses fails ("Unable to read bytes") -- confirms genuine unbacked RAM, not flash data.
  Total = 3x16-bit words, EXACTLY enough for a DF-II biquad (2 states + 1 output), no slack for a wider
  accumulator or DF-I. A broader free-RAM sweep was not performed.

## Safety verdict: CONDITIONAL GO, filtered-copy scheme only

GO conditions: (a) hook strictly downstream of the producer's settled store, never touching
gp-0x4f60/gp-0x4486; (b) clamp the biquad's own output before storing (cheap insurance, e.g. match Monitor
2's own +/-25.0/+/-0x6400 range); (c) confirm with operator that r24/r26 staying unfiltered is acceptable;
(d) resolve FUN_0008159e/FUN_00080a54's role and the ~14 unclassified readers before final build sign-off.
NO-GO as stated for source-filtering at the producer.

## Related
[[reference-accord-gp4f60-is-sensor-b-column-torque]] -- signal identity, CAN399 packer evidence this
session's classification builds on.
[[reference-accord-fun3a382-resonance-lane-unfiltered-correction]] -- the 0xC646C gain-cell reuse this
session found ALSO in FUN_0002c478, corroborating both as genuine fast carriers.
[[reference-accord-damping-clamp-dtc1d-trap]] -- the no-debounce DTC-0x1d pattern this session found is
ALSO the escalation path for Monitor 2's gp-0x4f60-derived corridor check, not just the damping clamp.
[[reference_accord_free_ram_candidates_gp1500_gp14e0]], [[reference_accord_codecave_c4b34_c4fef_larger_than_documented]]
-- prior-session cave/RAM records this session independently re-verified.
