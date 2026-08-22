---
name: reference_accord_frictionhold_table_ram_collision_concern_and_aggregate_clamp_telemetry
description: Round 2 of the V104 steering-feel-impact task (2026-08-22). Chasing the "friction-hold" breakpoint table's (gp-0x644x-0x647x, read inside FUN_000352b4) flash source instead found that at least 2 of its constituent RAM cells have ACTIVE WRITERS unrelated to any torque calibration -- gp-0x6480 from an angle/hysteresis counter pair (FUN_000371e0, whose own call path looks DEAD -- 0 callers, 2 methods) and gp-0x6468 from a modulo-2048-wrap + min/max-tracker-reset function (FUN_0003bcb2, clearly LIVE -- 7 call sites converging on FUN_0003d04c, itself with 10 more callers spanning a wide address range). NOT resolved either way -- open RAM-collision concern, same class as the gp-0x1500 family. Also: peak|H| at V104's c4=1.51202 is 1.850059 (not 1.0), confirming the "biquad cannot amplify" argument was valid ONLY at stock c4 and does not transfer to V104 (stale, not structural). Also: real telemetry from the only two unaliased-aggregator-sum routes (r85=V100, r95=V101, biquad NOT armed on either) shows |gp-0x6b94| duty>=10240 is 0.000000 in every regime slice checked (pooled/low-speed/high-torque/their intersection), max observed only 18.9%/30.7% of the ±10240 rail -- informative context but NOT a direct answer for V104's armed+boosted configuration. Sample-composition check on r9e/r96/r97 shows low-speed(<15kph) is 61-65% of samples (NOT thin), partially answering a regime-coverage worry. gp-0x6b86/gp-0x6b82/gp-0x6b7e have NEVER been captured on any flown route -- a genuine data gap requiring either V104's own flight or a full numeric replay-simulation.
metadata:
  type: reference
---

# Friction-hold table RAM-collision concern + aggregate-clamp telemetry — 2026-08-22

`feel-impact` task round 2 (team-lead follow-up), chasing whether the friction-hold table
`FUN_000352b4` builds (`local_44[]`/`local_58[]`/`auStack_64[]`, sourced from a wide `gp-0x645c`
to `gp-0x6480` RAM range) is a static ROM-copied calibration curve, per team-lead's request to find
its flash source and mode-proof it.

## 1. gp-0x6480 and gp-0x6468 have LIVE, torque-unrelated writers [EVIDENCE, fresh decompile + xrefs]

`search_instructions("6480")` / `search_instructions("6468")` (both `truncated:false`) found, besides
`FUN_000352b4`'s own reads:

- **`FUN_000371e0`** (`0x371e0`) writes `gp-0x6480`/`gp-0x6484` as a PAIR of 32-bit increment-or-
  reset-to−1 counters, gated on `gp-0x6a02`, `gp-0x6a10` (established elsewhere as ABSOLUTE STEERING
  ANGLE), and `gp-0x67fe=='\x02'` — an angle/hysteresis debounce, nothing torque-scale. Its sole caller
  `FUN_0002351e` has **ZERO callers**, confirmed 2 independent ways: `get_function_callers` returns
  none, AND a raw `search_instructions(mnemonic="jarl", operand_pattern="2351e")` returns 0 of 183,569
  scanned instructions. **This path looks DEAD** — if genuinely unreachable, `gp-0x6480` behaves as a
  static boot value in practice (its actual boot value not yet found).
- **`FUN_0003bcb2`** (`0x3bcb2`) writes `gp-0x6468` as `iVar3 - (iVar2<<0xb)` where `iVar3=(gp-0x4ec6+
  param_1)-param_2, iVar2=iVar3>>0xb` — a **modulo-2048 remainder** of some accumulated quantity, then
  calls `FUN_0003bc48` with the quotient. Same function also RESETS a shadow pair
  (`gp-0x6cc4`/`gp-0x4d0c`) and writes INT_MIN/INT_MAX sentinels (`0x80000000`/`0x7fffffff`) to
  `gp-0x6cd0`/`gp-0x4d18`/`gp-0x4d14`/`gp-0x6ccc` — a classic min/max-tracker RESET pattern. **Clearly
  LIVE**: 7 call sites (`0x3c5ea`,`0x3c7fc`,`0x3c946`,`0x3ca2a`,`0x3ce48`,`0x3d274`,`0x3debc`)
  converging on `FUN_0003d04c`, which itself has **10 more callers spanning `0x3d4a2` to `0x568d0`** —
  a genuinely active, well-connected module, structurally unrelated to anything torque/friction.

⇒ **The "friction-hold table" may not be a coherent static calibration table at all.** At least one
constituent cell (`gp-0x6468`) may be shared with, or entirely belong to, an unrelated live subsystem —
the same RAM-collision pattern already on record for the `gp-0x1500` family
(`reference-accord-b7260-io-mailbox-array.md`). **NOT resolved either way this session** — could be a
genuine collision, a deliberate multi-tick reuse, or a mis-attribution of exactly which bytes the
decompiler's `local_58`/`auStack_64` locals map to (Ghidra variable-name reuse is a known trap in this
kit). Needs `FUN_0003d04c`'s cluster traced (what subsystem is it — likely a gear/mode/diagnostic state
machine given the 0x3c5ea-0x3debc address density) before trusting any "flash source" or "physical axis"
claim about this table. **Consequence: `bVar3`'s duty (whether the friction-hold clamp is biting) cannot
be characterized as a simple torque-threshold comparison until this is resolved** — it may be gated by
whatever this partly-live block is actually doing.

## 2. peak|H| at V104's c4 is 1.850059, not 1.0000 — the "cannot amplify" argument does not transfer

Fresh sweep, 200,000 points over 0.01-500 Hz, exact recursion (`a1,a2,b1` = stock, unchanged by `c4`):
```
stock/V103  c4=0.81731   peak|H| = 1.000034  at DC
V104        c4=1.51202   peak|H| = 1.850059  at DC
```
**The "biquad cannot amplify (zeros on unit circle, peak|H|=1.0000)" clip-safety argument is TRUE ONLY
at stock c4 and is trivially FALSE at V104's c4** — the filter is now, by design, capable of amplifying
its own input by up to 1.85x. The remaining valid warrant for "no clip at k=1.85" is **purely the
separate empirical/exact-model bound** (handoff §4.3: "0.000000 duty over 1704s... clean to k≤3.40,
first clip at k=10.76"), not a structural proof — meaning its validity is bounded by the REGIMES that
1704s of flight actually visited, not universal. This is the correct frame for any future regime-
coverage concern about that figure.

## 3. Real aggregate-clamp (gp-0x6b94, ±10240) telemetry — the only 2 routes where it's unaliased

Per `check_427_alias.py::SUM_ROUTES = {"r85","r95"}` (V100/V101 — pre-V103, biquad NOT armed on
either, no `c4` contribution at all). Wire decode found in `rlog-tools/extract_r85.py`:
`427 = clamp(|gp-0x6b94|*5>>6, 0, 0x3FF)`, inverse `gp-0x6b94 = sign*mag*12.8`; the packer's own
comment gives the STRUCTURAL saturation point as wire-code 800 (`=10240*5>>6` exactly) — the decode is
directly comparable to the ±10240 clamp, not an approximation.

```
route  config                          |x6b94| max   p99      duty(|x6b94|>=10240), every regime slice checked
r85    V100, 4x fwd gain, biquad OFF    1932.8 (18.9% of rail) 1420.8   0.000000 (pooled/low-speed<15kph/high-tq>p90/intersection)
r95    V101, 8x fwd gain, biquad OFF    3148.8 (30.7% of rail) 2406.4   0.000000 (same, all slices)
```
Real, regime-resolved, genuinely zero — but on configurations with NO biquad/c4 contribution, so this
is context, not a direct k=1.85 answer. Even at 8x forward LKAS gain the total never exceeded ~31% of
the rail in any regime, including low-speed+high-torque corners (thousands of samples each) — a
reasonable but non-rigorous argument that this firmware's lanes don't typically pile up near their
individual ceilings simultaneously, even under a large excitation.

**Worst-case corner bound (the one number I CAN certify without telemetry)**: `gp-0x6b86`'s own
flown-max at k=1.85 is 6799 (handoff §4.3) = **66.4% of the 10240 aggregate ceiling**, leaving 33.6%
(3441 counts) of headroom for every other lane combined at that instant — genuinely unknown whether
that's threatened in practice.

## 4. Sample-composition check — the pooled 1704s dataset is NOT low-speed-thin

```
route  n         low-speed(<15kph) frac   low-speed & high-torque(>p90) frac
r9e    64,776    65.06%                   9.09% (n=5,885)
r96    87,614    63.90%                   8.39% (n=7,352)
r97    107,472   61.39%                   9.60% (n=10,319)
```
Low-speed is the MAJORITY of these captures on every route, with thousands of samples in the
low-speed+high-torque corner. Does not prove the clip-duty claim holds there (still can't see
`gp-0x6b86` on these routes), but refutes the specific worry that the pooled figure was drawn from an
overwhelmingly-highway dataset that never visited the symptom regime.

## 5. The real data gap — nothing captures gp-0x6b86/gp-0x6b82/gp-0x6b7e on ANY route

Checked every cache's key list (`r85`,`r95`,`r96`,`r97`,`r9e`): 427 has only ever carried `gp-0x6b4c`
or `gp-0x6b94` (aliased per build). None of the friction-hold-adjacent cells have ever been on the wire.
A true regime-resolved answer needs either V104's own flight (its 427 redesign already targets
`gp-0x6b86` + the `|gp-0x6b86|>=|gp-0x6b82|` comparator) or a full numeric replay of the ROM assist-map
pipeline (`gp-0x37fc[]`/`gp-0x37e8[]`, see
`reference_accord_assist_map_rom_source_found_and_shares_stage2_fork.md`) against the real captured
`tq`/`cs_v` timeseries. That replay does NOT need the friction-hold table resolved first — `gp-0x6b82
<= |gp-0x6b7a|` is already proven (memory: `reference_accord_fun352b4_clamp_address_map_and_biquad_output_target_resolved.md`),
so using `gp-0x6b7a` directly gives a conservative (over-estimating) proxy for `gp-0x6b86` that
sidesteps the friction-hold uncertainty. Not attempted this session — scoped as a substantial task.

## Related
[[reference_accord_fun352b4_clamp_address_map_and_biquad_output_target_resolved]] — the `gp-0x6b7a<=
gp-0x6b82` bound this file's replay-sim shortcut depends on, and the Round-3 c4/gp-0x6b7e independence
finding from earlier the same day. [[reference_accord_dc_domain_aggregator_census_and_biquad_numerator_theorem]]
— the DC-domain lane census and coefficient-sweep theorem from the same task, same day.
