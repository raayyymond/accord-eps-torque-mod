---
name: reference_accord_c63a0_cannot_reach_gp6b26_friction_lane
description: Closes the "does 0xC63A0 (Path-2 damper weight) reach the friction lane's hard-fault monitor" question -- gp-0x6b26 has exactly ONE writer image-wide (inside FUN_00036c12 itself, fed only by gp-0x6a5e/gp-0x6c2c), and both of those inputs' sole writers (FUN_00041464, FUN_00041eec) are structurally disjoint from 0xC63A0's reader (FUN_00038148) and its entire downstream chain. No firmware code path exists from 0xC63A0 to gp-0x6b26 or to FUN_00036d74's monitor. Also independently re-confirms FUN_00036d74 (friction hard-fault monitor), the 0xC407E clamp, the mode-26 ceiling record 0xD70A8, and Surface A (FUN_000347b8) by fresh Ghidra reads.
metadata:
  type: reference
---

2026-08-07, operator brief: verify/refute the friction-lane hard-fault mechanism (V74/V75 stoplight-launch
incidents) and specifically whether cal `0xC63A0` (raised 1024->2048 in V74/V75, the Path-2 damper weight
into `FUN_00038148`) can influence the friction lane `gp-0x6b26`/`FUN_00036d74`. Program: `code.bin`
(confirmed current via `list_open_programs`). Method: decompile-first, disasm to pin exact bytes, Python
raw LE byte scan (`analysis-2020accord/scan_gp_accesses.py`, self-check passed) as the required second
method for every writer/reader count.

## THE CLOSURE — 0xC63A0 cannot reach gp-0x6b26 by any code path [EVIDENCE, fresh this session]

1. **`gp-0x6b26` has exactly ONE writer, image-wide** — `0x36cf0: st.h r6,-0x6b26[gp]`, inside
   `FUN_00036c12`. Confirmed by 2 independent methods: `search_instructions(operand_pattern="6b26")` (7
   raw hits, 2 adjudicated false positives — `FUN_0006b162`'s `bge`/`ble` branch-target text collisions
   to `0x6b26c`/`0x6b266`, not real accesses) and a fresh Python LE byte scan (`scan_gp_accesses.py`,
   decoder self-check passed) — **5 real hits, byte-identical addresses, 1 STORE + 4 loads.** The store
   is unconditionally fed by the clamp result (`r6 = clamp(raw, -cal(0xC407E), +cal(0xC407E))`, disasm
   `0x36ccc-0x36ce2`) — confirms `|gp-0x6b26| <= cal(0xC407E)` on every write, no bypass path exists
   because there is only one writer.
2. **`FUN_00036c12`'s only two inputs are `gp-0x6a5e` (voted speed) and `gp-0x6c2c` (motor rate)**
   (disasm `0x36c1a`/`0x36c60`, matches prior memory). Fresh writer census of both, same method:
   - `gp-0x6c2c`: writers ONLY at `0x4184e`/`0x41ac2`, both inside **`FUN_00041464`** (0x41464-0x41b8d).
   - `gp-0x6a5e`: writer ONLY at `0x42342`, inside **`FUN_00041eec`** (0x41eec-0x42375).
3. **`0xC63A0` has exactly ONE access image-wide** — `0x381ac: ld.hu 0x73a0[tp],r9`, inside
   `FUN_00038148` (0x38148-0x382d6). Confirmed by fresh Python scan (tp-relative, base_reg=5): 1
   Format-VII hit, 0 extended-disp23 hits. `FUN_00038148` and its entire downstream chain
   (`gp-0x6b70` -> `FUN_00037fe6`[0x37fe6-0x38147] -> `gp-0x6ad6` -> `FUN_0003a382` -> `gp-0x6ad4` ->
   `FUN_0003aa2c` aggregator -> governor `FUN_0004503c` -> `gp-0x6b98`) occupies address ranges
   **completely disjoint from `FUN_00041464`/`FUN_00041eec`** — neither of `gp-0x6b26`'s two inputs is
   written anywhere in that downstream chain.

**⇒ There is no firmware (code-level) data-dependency path by which `0xC63A0` can change `gp-0x6b26`,
and therefore none by which it can trip `FUN_00036d74` (the friction-lane hard-fault monitor, DTC 0x1d) or
`FUN_00036c12`'s own one-cycle-lagged echo (DTC 0x1c).** Restoring `0xC63A0=2048` is safe with respect to
THIS specific fault mechanism, on evidence, not inference. The only theoretically possible connection is a
PHYSICAL/plant-mediated one (a larger Path-2 damper term changes the delivered torque -> changes how the
wheel/motor actually moves -> changes the resolver-derived `gp-0x4f50`/`gp-0x6c2c` reading) — structurally
identical to "every torque lever affects the plant, which the rate sensor then reads back" and not
evidence of a `0xC63A0`-specific risk to this lane. [BELIEF for magnitude/plausibility of that physical
loop; not code-quantified.]

## Independently re-confirmed this session, fresh Ghidra reads (not new, but re-derived not just cited)

- **`FUN_00036d74`** (`0x36d74-0x36dec`): reads `gp-0x6b26`, compares against `tp+0x5004`(`=0xC4004`,
  byte-read fresh: `00 00 00 3F` = float **0.5** exactly), symmetric, unconditional relay to
  `FUN_000462e6(0x39bc,...)` on any single-cycle violation — **no internal debounce**.
  `FUN_000462e6` fresh-decompiled: unconditionally calls `FUN_00016de6(0x1d,param_1,1,1)` regardless of
  its own first argument — confirms the "always DTC 0x1d" pattern already on record, from source this
  time, not inferred.
- **Caller gate, `FUN_0002214a` @ `0x2290a: jarl 0x00036d74,lp`**: fresh full disasm of the caller shows
  this call is gated by `cmp r0,r28 / be 0x2290e` where `r28 = uVar4 = (1<<gp-0x67fa) & 0x830` — **the
  IDENTICAL gate, same register, tested immediately before, that wraps `FUN_00036c12`'s own call
  (`0x228c4-0x228cc`)**. Not unconditional relative to the whole state space (requires `gp-0x67fa` in
  {4,5,11}) — but **unconditional relative to the producer**: there is no code path in which
  `FUN_00036c12` writes `gp-0x6b26` this cycle without `FUN_00036d74` checking it in the same cycle. This
  is the correct reading of "unconditional" for this monitor, refining the operator's framing.
- **`0xC407E`**: fresh byte read = `ff 01` = **511**. Fresh Python scan: exactly 3 reads
  (`0x36c34`/`0x36cd0`/`0x36cdc`), 0 writers, 0 extended-disp23 hits — matches prior census exactly.
- **Mode-26 ceiling record**: `0xC77A0 + 26*4 = 0xC7808` -> pointer `a8 70 0d 00` = **`0x000D70A8`** —
  exact match to the operator's stated address. Record bytes at `0xD70A8`:
  `02 00 2c 01 20 03 00 02 00 04 00 00` decodes to **count=2, X=[300,800], Y=[512,1024]** — exact match.
  `0xC6158` fallback (used when `gp-0x6ac2` unsigned >= 13000) fresh-read = `00 02` = **512**.
- **Surface A (`FUN_000347b8`, `0x347b8-0x348dc`)**: fresh disasm confirms double-precision compare vs
  13000.0, float-domain twin ceiling table at `0xC6550` (fresh byte read: count=2(u32), X=[300.0,800.0],
  Y=[0.5,1.0] — exact IEEE754 decode, matches prior memory), clamp re-derivation (`cmovne`+`negf.s`+
  `maxf.s`), and fault call `FUN_000462e6(0x417a, fVar5, clamp_result, ..., -5/1024)` using the SAME
  `0x3ba00000`/`0xbba00000` (=+-5/1024) epsilon constants as the EME bit32 family — confirms the ±5-count
  window byte-exact. `FUN_00034350`'s own one-cycle-lagged echo (fault `0x4179` -> `FUN_0004613e` ->
  unconditionally `FUN_00016de6(0x1c,...)`) also freshly confirmed present at `0x34358-0x3438a`.
- **`gp-0x6b94`/`gp-0x6bd0`/`gp-0x6b70`/`gp-0x6ad6`/`gp-0x6ad4` fresh writer/reader census** (Python scan):
  no fault-check consumer found on any of `gp-0x6b70`/`gp-0x6ad6`/`gp-0x6ad4` (pure forward-path, single
  reader each). `gp-0x6b94`'s only fault-adjacent readers are its OWN shadow-lockstep pair (with
  `gp-0x4ce0`, inside `FUN_0003aa2c`, fires on primary/shadow MISMATCH not magnitude) and
  `FUN_0004595a` (already established REFUTED as a V75 differentiator, per
  [[reference_accord_v75_step_size_hypothesis_refuted_and_fun347b8_precise_trigger]] — it explicitly
  tolerates output lagging target). **Monitor 1 (`FUN_00042af8`) and Monitor 2 (`FUN_00043e44`) confirmed,
  independently of the decompile-grep this session extends, to never appear in the writer/reader list of
  `gp-0x6bd0`, `gp-0x6b94`, `gp-0x6b70`, `gp-0x6ad6`, or `gp-0x6ad4`.**

## Minor correction found in passing (does not change any verdict)

`FUN_00034350`'s three writes to `gp-0x6bd0` — fresh disasm assigns roles slightly differently than
[[reference_accord_gp6bd0_damper_own_ceiling_consistency_monitor_fun347b8]]'s labels: `0x34730`=clamp to
**+ceiling**, `0x34744`=clamp to **-ceiling** (that memory says "unclamped pass-through" here),
`0x34752`=**raw/unclamped pass-through** (that memory says "clamp to -ceiling" here). All THREE branches
and the overall `clamp(product, -ceiling, +ceiling)` semantics are identical either way — only the
address-to-role mapping for two of the three writes was swapped in the prior note. Flagging, not fixing
that memory per convention (ask before editing another session's file).

## Related
[[reference_accord_friction_lane_direct_hard_fault_monitor_gp6b26_c4004]] — the base finding this
independently re-derives from source. [[reference_accord_friction_lane_c407e_census_and_mode26_record_identity]]
— the 0xC407E census this matches exactly. [[reference_accord_path2_is_a_real_closed_loop_via_gp6b98_and_0xc63a0_sizing]]
— establishes 0xC63A0's single-reader status and Path-2's structure, which this session's writer census of
`gp-0x6b26`'s own inputs shows is DISJOINT from the friction lane. [[reference_accord_gp6bd0_damper_own_ceiling_consistency_monitor_fun347b8]],
[[reference_accord_v75_step_size_hypothesis_refuted_and_fun347b8_precise_trigger]] — Surface A's mechanics,
re-confirmed fresh here. [[reference_accord_monitor1_monitor2_full_accumulator_mechanics_v75]] — source of
the Monitor 1/2 structure, cross-checked here by an independent method (raw byte scan vs decompile-grep).
