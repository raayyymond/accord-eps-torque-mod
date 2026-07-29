---
name: reference_accord_gp6bbe_angle_rate_path_traced_net_damping
description: Full disassembly trace of gp-0x6bbe's ("boost") true dominant signal -- corrects the earlier same-session characterization ("torque EMA, same-signed reinforcing"). The core signal is an UNFILTERED angle-rate-error term (gp-0x6a56 minus a torque/state-modulated baseline), with the torque EMA entering only as a multiplicative AMPLITUDE scale, not an additive branch. Net effect is DAMPING (opposes angle rate), not reinforcement. Identifies 4 pure static-gain/clamp lever candidates inside the pre-existing DAMP_BLOCK (0xD2000-0xD2FFC) that do not overlap V44/V47's specific edits.
metadata:
  type: reference
---

# `gp-0x6bbe`'s true dominant signal: angle-rate error, not torque -- traced 2026-07-29/30 for team-lead's redirect after the angle-domain audit

Corrects [[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]] and
[[reference_accord_aggregator_domain_audit_no_angle_lane_found.md]]'s characterization of `gp-0x6bbe`
("boost", `FUN_00034a72`) as "torque EMA, same-signed reinforcing." A sister agent (ReturnToCenter) flagged
that the function's tail contains an FSM-result-minus-raw-`gp-0x6a56` term; this session re-traced the
WHOLE function via fresh disassembly (not decompile alone) to settle it with addresses.

## [VERIFIED, disasm] The torque EMA is a side-chain, not the core additive signal

`iVar29` (the EMA on raw `gp-0x4f60`, `0xC6372`=205, already documented) feeds a magnitude/LERP chain
(`DAT_ca4f4[mode]` + slew-blend `PTR_DAT_ca06c[mode]`=102/1024≈0.0996) producing a scalar
`blendedMagnitude` that **MULTIPLIES** the angle-rate-error term (see below) -- it does NOT reach
`gp-0x6bbe`'s final store as a separate additive branch. Checked the function's tail (`0x3507c-0x350c2`)
directly: it is a single clamp of ONE accumulated value, no second addend.

## [VERIFIED, disasm, addresses] The rate-error chain

```
0x34ab8  ld.h -0x6a56[gp],r13      raw angle rate, read #1
0x34aca  addi 0x2ee0,r13,r15       r15 = angle_rate+12000
0x34ada  addi -0x5dc1,r15,r0       vs 23999
0x34ae6  setfnc r24                r24 = 1 iff |angle_rate| < 12000 (VALIDITY GATE, symmetric-window idiom)
...[4-state machine gp-0x682e produces baseline "iVar13", gated on gp-0x67fe/gp-0x67f4/gp-0x6a5e sanity
   PLUS an override: bVar10 = ... && !(10000<gp-0x6a10) && !(20000<gp-0x6a02+10000), and a dwell counter
   gp-0x68c8 vs cal tp+0x74d1(=3760)*10]...
0x34e8a  cmp r0,r24; be 0x34e94    if angle rate OUT of range: r6 = iVar13 (baseline itself)
0x34e8e  ld.h -0x6a56[gp],r6       else: r6 = angle_rate_raw, read #2
0x34e96  sub r6,r28                rate_error = iVar13(baseline) - r6
0x34e98-0x34eaa                    rate_error_clamped = clamp(rate_error, +/-12000)
0x34f20-0x34f44                    term1 = (rate_error_clamped * K1[mode]) >> 7
                                   term2 = (term1 * speedLERP1(gp-0x6a5e)) >> 10
                                   term2_clamped = clamp(term2, +/- clampBound[mode])
0x34ffa-35010                     term3 = (term2_clamped * blendedMagnitude) >> 14
                                   iVar21_final = term3 * polarity(gp-0x6752, +1 boot-init, established)
0x35078-0x350c2                   gp-0x6bbe = clamp(iVar21_final, +/- speedLERP2(gp-0x6a62))
```
**No EMA/IIR anywhere on the raw angle-rate itself** -- only one subtraction and static clamps. Genuinely
unfiltered on the phase-carrying signal.

`gp-0x682e`'s override gate (`bVar10`) reads the SAME two variables flagged OPEN in
[[reference_accord_aggregator_domain_audit_no_angle_lane_found]]: `gp-0x6a02` (confirmed torque-domain,
`(gp-0x4f60*10)/gp-0x4ebc`, per `FUN_0003fc16`) and `gp-0x6a10` (still not fully domain-resolved) at a
10000-count threshold. This may be part of the team-lead's driver-torque-override answer -- not chased
further this session.

## [VERIFIED, byte reads] The two "speed LERPs" -- one gain, one flat no-op clamp

Mode index = 10 for this car (re-confirmed via the pointer-chase: `0xC9EC4`->`0xD27BC` match, same method
as [[reference_accord_gp6a5e_is_voted_vehicle_speed]]'s addendum).

**Table A -- `gp-0x6a5e` (avg voted speed), a REAL GAIN.** Pointer `0xCA17C`->`0xD2834`. Byte-read: count=6,
X=[0,640,2560,5120,7808,10240] counts = **[0,10,40,80,122,160] km/h**, Y=[541,639,653,551,439,439] (Q10).
Shape: 0.528@0km/h -> peak 0.638@40km/h -> 0.538@80km/h -> 0.429@122km/h+ (flat beyond). Multiplies
`term1` directly. Creep(1.8-10.8km/h): gain≈0.55-0.62. Road(50.4-75.6km/h): gain≈0.61-0.55. **Close to each
other in both regimes -- a broad hump peaking at 40km/h, NOT a strong monotonic speed-rise.**

**Table B -- `gp-0x6a62` (max-voted speed), NOT a gain -- the FINAL CLAMP CEILING.** Pointer
`0xC7998`->`0xD20C0`. Byte-read: count=5, X=[0,640,2560,5760,6400] counts = **[0,10,40,90,100] km/h**,
Y=[512,512,512,512,512] -- **FLAT**. Functionally a fixed +/-512 clamp on this car's calibration, dressed
as a table but speed-INDEPENDENT in practice.

Other tables read: `K1`(Q7 gain on rate_error) pointer `0xCA34C`->`0xD200C`=**43**; `clampBound`(mid-chain
ceiling) pointer `0xC7A80`->`0xD2000`=**666** -- a DIFFERENT cell from `FUN_00034350`(damping)'s already-
documented clamp at `0xD209C`/`0xD20A8`.

## [INFERRED, moderate-high confidence, NOT numerically simulated] Sign/phase -- NET DAMPING, not reinforcing

`rate_error = baseline - angle_rate_raw`. All downstream multipliers are non-negative by construction;
polarity(`gp-0x6752`)=+1 (no inversion). **If `baseline` is slow relative to 22Hz** (built from a
slew-blended torque-magnitude + a `gp-0x6a10`-indexed LERP + `sign(gp-0x6a02)`, none obviously fast
oscillators by construction) **then `rate_error ≈ -angle_rate_raw` at 22Hz, and `gp-0x6bbe ≈
-(gain)*angle_rate` -- NET DAMPING on angle rate, textbook viscous shape, NOT reinforcement.** This
REVERSES the sign character implied by the (now-superseded) torque-EMA framing. Not independently
time-domain-simulated this session (unlike `FUN_0003a382`'s prior full simulation) -- flagged as the next
step if GATE 2 needs certification.

## Candidate levers -- 4 pure static-gain/clamp options, checked against build lineage

All four sit INSIDE the already-edited `DAMP_BLOCK` (`0xD2000-0xD2FFC`, per `build_v47_tva.py:153`, shared
CRC at `0xD2FFC`, touched by both V44 and V47) -- but at byte addresses that do NOT overlap either build's
specific edits (`0xD27C6/DA` Factor-C Y0, `0xD2802/04/06`+`0xD2816/18/1A` Factor-E Y0-2, `0xD209C/A8` clamp
header -- checked by direct grep of `build_v44_tva.py`/`build_v47_tva.py`, not just "same 4KB region"):
- **`K1` @ `0xD200C` = 43** -- Q7 gain on rate_error, applied first. Blast radius: `search_instructions` on
  the pointer-array base `0xca324` (whole image) = **1 hit, this function only.** Cleanest single-point lever.
- **`clampBound` @ `0xD2000` = 666** -- mid-chain ceiling; first byte of the shared block, handle CRC with care.
- **speedLERP1 Y-values** @ `0xD2834+0xE..0x18` (541/639/653/551/439/439) -- lowering cuts the speed-gain shape.
- **speedLERP2 (flat clamp)** @ `0xD20C0+0xC..0x14` (5x 512) -- already-flat ceiling; uniform reduction has
  no speed-dependent side effect since the table has no shape to disturb.
None of the four appears in any `build_v*_tva.py`.

## Related
[[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]] -- the earlier (superseded on this point)
characterization of `gp-0x6bbe`'s frequency response, based on the torque-EMA framing this session corrects.
[[reference_accord_aggregator_domain_audit_no_angle_lane_found]] -- flagged `gp-0x6a10`/`gp-0x6a02` open;
this session closes `gp-0x6a02` (confirmed torque) and ties both into `gp-0x682e`'s override gate.
[[reference_accord_gp6a5e_is_voted_vehicle_speed]] -- source of the mode-index=10 pointer-chase method reused here.
