---
name: reference_accord_fun38148_six_weight_v95_candidate_census
description: Full Q1-Q5 census of FUN_00038148's six Path-2 lane weights (0xC63A0..0xC63AA) for V95 candidate selection against the 6-9Hz micro-ratchet target -- all six frozen at stock 1024 through V94, only 0xC63A0 has any (confounded, never-isolated) on-car history, no int32 overflow risk on any of them, and the SIGN of raising any Path-2 weight is UNRESOLVED (RAM-resident LERP table never reverse-engineered) -- this is the blocking gap before sizing any build.
metadata:
  type: reference
---

# FUN_00038148 six-weight census for V95 (6-9Hz micro-ratchet target) -- 2026-08-11, `lane-weights-6bf`

Dispatched to enumerate and classify the six Path-2 lane weights `0xC63A0..0xC63AA` after V94's
`0xCBE74` cut (an ACCELERATION-domain lever, per [[reference_accord_v92_final_allocation_gp6abc_gp6bf0_adjudication]]
and `memory/accord-gp6b26-is-inertia-not-damping.md`) made the car shake and was judged unsafe. Full
fresh decompile of `FUN_00038148` (0x38148), `FUN_0003aa2c` (0x3aa2c, Path 1), `FUN_00034350` (0x34350,
damper), `FUN_00034a72` (0x34a72, boost), plus raw disasm of `FUN_00026c80` (0x26c80, mixer). All on
`code.bin` stock (confirmed identical to the current build's frozen values, see below).

## Stage-1/Stage-2 arithmetic, exact [EVIDENCE, fresh decompile]
```c
sum6 = Σ (x_lane * gate_lane(x_lane) * W_lane) >> 10     // 6 lanes, plain ADD, gate is hard ZEROING not clamp
target = ((sum6 * polarity(gp-0x6752) * 2639) >> 10) * 16 // 2639 = tp+0x7468 = 0xC6468, shared model gain
gp-0x374c += ((target - gp-0x374c) * 102) >> 10           // 102 = 0xC63AC, IIR alpha, fc~16.7Hz@1kHz
// Stage 2 (closes a prior OPEN item):
iVar6 = gp-0x6bfe + gated(gp-0x6bfa,±20000) - (gp-0x374c >> 4)
gp-0x6b70 = sign(iVar6) * RAM_LERP(|iVar6| * 0xC63AE >> 10), clamped ±0xC6200(=8192)
```
`gp-0x6bfe`←`FUN_0003bc20`←`gp-0x6bfc`←`FUN_0003b8f6`, whose first input is `gp-0x6b98*polarity` (the
DELIVERED motor command, one 1kHz tick earlier) — **Path 2 is a real closed firmware feedback loop
through `gp-0x6b98`**, confirmed structure per [[reference_accord_path2_is_a_real_closed_loop_via_gp6b98_and_0xc63a0_sizing]].

## The six weights
| gp var | weight (tp/abs) | stock | gate ± | producer | physical ID |
|---|---|---|---|---|---|
| gp-0x6b4e | 0x73a8/**0xC63A8** | 1024 | 10240 | FUN_00026c80 mixer | LKAS-command domain |
| gp-0x6b4c | 0x73aa/**0xC63AA** | 1024 | 10240 | FUN_00026c80 mixer | LKAS-command domain |
| gp-0x6b26 | 0x73a6/**0xC63A6** | 1024 | 1024 | FUN_00036c12 | ACCELERATION (`=-K·gp-0x6c2c`, re-ID'd 2026-08-11) — SAME signal V90-94's `0xCBE74` already tested |
| gp-0x6b46 | 0x73a4/**0xC63A4** | 1024 | 1024 | FUN_00036682 | torque-domain, own output <1Hz EMA — RULED OUT, can't carry 6-9Hz |
| gp-0x6bd0 | 0x73a0/**0xC63A0** | 1024 | 2048 | FUN_00034350 | DAMPER, 5-factor product — dead below 12.7°/s wheel rate / 35km/h (own memory: 95.91% of engaged frames zero, 100% of micro regime) |
| gp-0x6bbe | 0x73a2/**0xC63A2** | 1024 | 2048 | FUN_00034a72 | BOOST — the ONE lane independently confirmed on-car viscous/rate-derived, ~90ct/(rad/s), phase~0 @5-6Hz |

## Q3 lineage [EVIDENCE, grep + `build_v92_tva.py` FROZEN dict lines 506-514]
**All six are at stock 1024 right now** (re-asserted every build V90→V94). `0xC63A2/A4/A6/A8/AA` are
**completely virgin** — never appear in any build script except as a stock-value verification entry.
`0xC63A0` is the one exception: V72 doubled it 1024→2048 (1 reader `0x381AC`, 0 writers); flew on V74/V75
CONFOUNDED with the friction ×1.5 table and `0xC407E` 511→850 — the hard faults were `0xC407E`'s, NOT
`0xC63A0`'s (`memory/accord-c407e-is-the-fault-interlock-c63a0-exonerated.md`, orchestrator-verified
2026-08-07). V81 (V75-base, flew route 5e clean) kept it at 2048. V83a reverted it to 1024 for a
**loop-gain reason, not a safety one**. Stayed 1024 V84→V94. **⇒ no weight has EVER been isolated /
single-variable on-car tested** — `0xC63A0`'s only flight was always confounded with other edits.

## Q4 overflow [EVIDENCE, Python int32 mirror]
Worst case (all 6 lanes at gate ceiling, unity weight): sum6≈26,624 → ×2639≈70.3M, ~30x under int32's
2.1B even before the shrinking `>>10`/IIR stages. **No int32 overflow risk on any of the six weights at
any plausible multiplier** — structurally different from `0xCBE74`'s narrow `*0x111>>0x12` intermediate
that overflowed above ×1.5. Real ceilings are graceful, not cliffs: (1) each lane's own ±gate tests the
RAW lane value, unaffected by its weight; (2) `gp-0x6b70`'s own ±8192 clamp (`0xC6200`, shared with
`FUN_0003a382`'s bias clamp) is the practical ceiling, exact binding multiplier not computed (needs
`gp-0x6bfe`'s runtime magnitude, a telemetry question).

## 🛑🛑 Q5 sign — UNRESOLVED, the blocking gate before any V95 build on these weights
Stage 2's LERP table (`gp-0x64b6..`/`gp-0x641c..`, RAM-resident, populated at runtime by `FUN_000389ec`)
has **never been reverse-engineered in this kit's history** — flagged OPEN since 2026-08-06, still open.
Without its shape the sign of "raise a Path-2 weight ⇒ net damping direction at the motor" cannot be
derived from statics alone. **Precedent that this matters**: the kit's own prior closed-loop sweep on the
sibling weight `0xC63A0` found (BELIEF/estimate level) that W=1024→2048 crosses an INVERSION boundary —
combined stage1+PID magnitude 0.59/0.56 (damping) at W=1024 vs 1.18/1.12 (**damper INVERTED**) at W=2048,
at both 7.79Hz and 21Hz (`reference_accord_path2_is_a_real_closed_loop_via_gp6b98_and_0xc63a0_sizing.md`).
No reason to assume `0xC63A2` is immune — it sits in the identical Path-2 loop. **Next step to close
this**: fresh decompile of `FUN_000389ec` (task 5/100Hz) to derive the LERP table's construction rule
analytically, OR a live telemetry dump of the table's runtime X/Y contents.

## Verdict for V95 candidate selection
`0xC63A4` RULE OUT (structurally <1Hz). `0xC63A0` RULE OUT for the micro-regime target (own dead zone
excludes it) and carries the one documented inversion-risk precedent. `0xC63A6` flagged likely to share
`0xCBE74`'s phase problem (same underlying accel signal) — BELIEF, not computed. `0xC63A8`/`0xC63AA` are
command-tracking, not a natural damping lever. **`0xC63A2` (boost) is structurally the best candidate** —
the one on-car-confirmed rate-derived/viscous lane, virgin, single-reader, no overflow risk — **but
inherits Q5's unresolved sign gap exactly as much as `0xC63A0` did.** Do not size a build on it without
closing Q5 first (GATE 2).

## Related
[[reference_accord_gp67ac_resolved_zero_and_path1_always_live]] — companion finding this session, confirms Path 1's direct (unweighted) sum of gp-0x6bd0/gp-0x6bbe/gp-0x6b26 is also always live.
[[reference_accord_path2_is_a_real_closed_loop_via_gp6b98_and_0xc63a0_sizing]] — the closed-loop structure and 0xC63A0 inversion-risk precedent this file leans on.
[[reference_accord_fun38148_six_lane_identity_and_gp6a10_producer]] / [[reference_accord_fun38148_fun37fe6_channel_census_and_dead_lanes]] — prior sessions' partial census this extends to a full Q1-Q5 with fresh addresses.
