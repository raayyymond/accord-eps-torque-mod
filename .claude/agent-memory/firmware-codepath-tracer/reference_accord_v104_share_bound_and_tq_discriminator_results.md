---
name: reference_accord_v104_share_bound_and_tq_discriminator_results
description: V104 flew (built at c4 x1.85 on the FUN_000352b4 biquad, see reference_accord_fun352b4_clamp_address_map_and_biquad_output_target_resolved.md) and the operator felt NO change in steering feel, engaged or manual -- only the engaged half is informative, since c4 is provably inert while disarmed. Derives an upper bound on gp-0x6b86's share of delivered assist from that null (s<=10.6% under a no-rejection linear model; UNBOUNDED/inapplicable if compensator's rejection-loop hypothesis holds -- the two readings are NOT distinguishable from the perceptual null alone). Documents the pre-registered tq (driver-required-torque) discriminator built to distinguish the two readings using route ra4 (V104, first flight with gp-0x6b86 on CAN 427) vs r9e (V103): the MANDATORY split-half-null-first control revealed the design is underpowered (noise floor +-26.5% to +-59% against a pre-registered +-3% threshold) because only 6 (r9e) / 8 (ra4) episodes exist -- pooled result INCONCLUSIVE on both a median-torque and a crest-factor (impulsiveness) statistic; the >=80km/h stratum is UNTESTABLE (exactly 1 episode per route); the <16km/h stratum (the operator's own named symptom window) IS testable (every episode touches it) and is SUGGESTIVE (not established) in the Reading-A direction on both statistics. The concrete, durable finding: 6-8 episodes is not enough data for this question at any useful precision -- more engaged low-speed driving on both builds is the actual fix, not a cleverer statistic.
metadata:
  type: reference
---

# V104 flew, felt-null share bound, and the tq discriminator's power-limited verdict — 2026-08-22

`feel-impact` task (team-lead orchestrated), continuing the same-day `c4`/`gp-0x6b86` trace (see
[[reference_accord_fun352b4_clamp_address_map_and_biquad_output_target_resolved]] Round 3 and
[[reference_accord_dc_domain_aggregator_census_and_biquad_numerator_theorem]]). V104 (built, `0xC60B4`
`c4` 0.81731->1.51202, H(0) 1.000034->1.850063) was flashed and driven; docs recording it as
"built, not flashed" were stale — confirmed by the operator directly.

## The operator's report and the informative half [EVIDENCE, from FUN_000352b4's own arm-gate structure]

Verbatim: *"I did not feel any [change in] normal, manual, LKAS-disengaged OR LKAS-engaged steering
feel."* **Only the ENGAGED half is informative.** `c4` is read/multiplied at exactly one instruction
(`0x35a30`/`0x35a3c`), reached only through the ARMED branch (`0x35a28-80`); disarmed, the code takes
the literal unity-passthrough `0x35a86: mov r10,r6` and never touches `tp+0x70b4`. So "no change felt
manually" is a **provably expected null**, not evidence — conflating it with the engaged half overstates
the case. (Team-lead corrected their own framing to the operator on this point after this catch.)

## The share bound, both readings [arithmetic EVIDENCE; which reading is TRUE is unresolved BELIEF]

Let `s` = `gp-0x6b86`'s share of delivered assist. `c4` raises the LANE's own gain by a fixed
**+85.00%** (H(0) ratio, frequency- and speed-independent — this is a filter-topology fact, not
dependent on the assist map's own speed-scheduling). Using a relayed perceptual-calibration bracket
(~9% not felt / ~45% felt, NOT independently re-derived this session, provenance outside this task):

```
Reading A (no rejection, linear/additive combination downstream — supported this session by: V104's
  only edit is c4; r85/r95 real aggregate-sum telemetry shows 0.000000 clip duty in every regime even
  at 8x forward gain; V102/V103 biquad-term clip duty also 0.000000 at k=1.85):
    s <= 0.09 / 0.85 ≈ 0.1059  =>  UPPER BOUND s <= ~10.6% of delivered assist.
  (context point: s ≈ 0.45/0.85 ≈ 52.9% would plausibly have crossed into felt territory by the same calibration)

Reading B (compensator's rejection hypothesis — gp-0x6b86 is a disturbance at a junction whose
  reference is architecturally blind to it, physical feedback = gp-0x4f60 the torque sensor):
    the null places NO bound on s at all — arithmetic is INAPPLICABLE, not merely imprecise, since a
    loop's DC/low-frequency disturbance rejection can suppress the felt effect independent of magnitude.
```

**UPDATE, later same session (relayed from team-lead, not independently re-derived by me): a separate
spectral/dose analysis of route `a4` found the dose arrived at 1.824x (predicted 1.66-1.85) and 6-9Hz
moved 0.445 [0.24,0.66] — reported as "the lane was NOT rejected," which if correct favors Reading A as
the standing explanation.** I did not verify this dose/spectral result myself; flagging its
existence and that it bears directly on which reading applies.

**The bound does NOT mechanically change with speed** (the 85% is topology-fixed), but `s` ITSELF could
be speed-dependent since the assist map's near-origin slope is ~2x steeper at parking than at 50km/h
(relayed fact, not independently re-derived) — if other lanes don't scale the same way, the true
low-speed `s` could exceed the pooled 10.6% bound. **I could not produce a low-speed-specific revision
of the bound** — the arithmetic needs a low-speed-specific felt/not-felt calibration point that doesn't
exist; the operator's whole-drive "felt nothing" impression is not obviously a careful low-speed-specific
EFFORT read (as opposed to his GRINDING-noise attention, a different channel). Said so plainly rather
than fabricating a number.

## The `tq` discriminator — pre-registered BEFORE the outcome, then run [EVIDENCE throughout]

Goal: use route `ra4` (V104's first flight, `gp-0x6b86` on CAN 427 via `sar 4`, confirmed on-wire >800
wire-code — arithmetically impossible under V103's packer, an independent on-car confirmation V104 was
really flown) vs `r9e` (V103) to test whether driver-required torque (`tq`, standard CAN, present on
every route) differs at matched (speed, curvature) conditions — a test that needs no isolation of
`gp-0x6b86` itself.

**Design**: engaged-only (`e4req==1`); episodes = contiguous engaged runs, min 5s, broken on >0.5s time
gaps; speed = 5 quantile bins pooled across both routes; curvature (`cc_curv`) = 4 quantile bins within
each speed bin; statistic = sample-weighted mean of per-cell `(median9-medianA4)/((median9+medianA4)/2)`
(the SYMMETRIC percent-difference — a plain ratio `(A-B)/A` was tried first and found badly behaved,
producing an off-center, inflated null from small-denominator cells; the symmetric version is
well-centered and used as primary going forward). Episode bootstrap (not frame bootstrap), MANDATORY
split-half null on `r9e` alone run and read FIRST, with an explicit pre-registered commitment to revise
thresholds before reading the cross-build result if the null said the pre-registered ±3% was unusable.

**RESULT: the design is severely underpowered.** `r9e` has only 6 episodes, `ra4` only 8 (one `r9e`
episode is 10.7s). Split-half null on `r9e` alone: **90% CI ±26.5% (symmetric median-torque stat) to
±56-59% (crest-factor stat)** — an order of magnitude wider than the pre-registered ±3%. Revised
per-commitment before reading the cross-build number.

- **Pooled (20 cells, all speeds), median|tq|**: cross-build symmetric Δ = -7.05%, 90%CI [-36.4%,
  +34.8%] — **INCONCLUSIVE**, comfortably inside the null's own noise.
- **Pooled, crest factor (p95/median |tq|, the pre-declared impulsiveness secondary — the operator later
  clarified the symptom as "a ratchet ON TOP OF a higher-frequency vibration," making peakiness the more
  literal target than the median)**: cross-build Δ = +25.2%, 90%CI [-7.6%, +50.8%] — **INCONCLUSIVE**,
  point estimate in the WRONG direction (more peaky) but CI too wide to read either way.
- **>=80km/h stratum: UNTESTABLE.** At the episode level, `r9e` and `ra4` EACH have exactly 1 episode
  touching that speed — an episode bootstrap from a pool of 1 has no resampling variance; refused to run
  it rather than report a number with false precision.
- **<16km/h stratum (the operator's own named window, "low speed <10mph"): TESTABLE** — every episode on
  both routes touches this band at least briefly (6/6, 8/8), though unevenly. Used a coarser 4-cell
  (curvature-only) design given less data in one speed slice. Results: **median|tq| Δ=+49.1%, 90%CI
  [+21.9%, +69.3%]** (V104 needing LESS torque — Reading-A direction, CI mostly but not fully clear of
  the null's own ±36.8% reach); **crest factor Δ=-29.9%, 90%CI [-64.4%, +17.5%]** (V104 LESS peaky —
  also Reading-A direction, CI straddles zero). **Called SUGGESTIVE, not established**, on both — same
  sign as a real regime-specific effect would produce, plausibly larger here because of the assist map's
  steeper low-speed slope, but not cleanly separated from the (still-wide, if narrower) null.

**The durable, most-useful finding is the negative**: *"6-8 episodes is not enough data for the
precision this question needs — more engaged low-speed driving on both builds is what would close it,
not a cleverer statistic."* A drive-card requirement, not a statistics problem.

## Method notes worth reusing
- The `(A-B)/A` ratio statistic is unstable under small per-cell denominators; prefer `(A-B)/((A+B)/2)`
  (symmetric percent difference) for any future matched-cell comparison in this kit's telemetry work.
- Precomputing a `{episode: {cell: array}}` map once, then concatenating small arrays per bootstrap draw,
  is far faster than re-masking the full frame array on every draw (the naive version was too slow to
  finish a 2000-draw bootstrap over 20 cells in 3 minutes; the precomputed version runs in seconds).
- See [[reference_accord_cs_v_units_are_meters_per_second_not_kph]] — hit and corrected mid-task,
  directly relevant to any speed-thresholded cut in this analysis.

## Related
[[reference_accord_fun352b4_clamp_address_map_and_biquad_output_target_resolved]],
[[reference_accord_dc_domain_aggregator_census_and_biquad_numerator_theorem]],
[[reference_accord_frictionhold_table_ram_collision_concern_and_aggregate_clamp_telemetry]] — the three
prior files from this same session's `c4`/`gp-0x6b86` trace this one concludes.
