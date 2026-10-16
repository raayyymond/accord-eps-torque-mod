# Drive reader: release-firmware notes (2026-10-15)

Analysis only. Nothing here sends CAN, flashes, or touches a fork file. No commits were made.

## Command for a release route

```
export ACCORD_FIRMWARE_ROOT=C:/Users/dudei/Desktop/Projects/accord-firmwares
python rlog-tools/studies/angle_loop/angle_loop_drive_read.py <dongle>_<counter>--<hash>
python rlog-tools/studies/angle_loop/high_angle_hunt.py <dongle>_<counter>--<hash> --plot <dir>
```

- Attribution comes from the EPS fwVersion. `39990-TVA,A16C` is V300, the release image. No flag is needed.
- `--no-tap` forces the same path on any route. `--synthetic-release` is the self-check (below).
- First read of a new route extracts it once (about 65 s for the wire cache, about 10 s for the fork cache). Later reads take 4 to 7 s.
- The fork cache needs the release commit's cereal schema. No real release route exists yet, so that step is untested. **BELIEF:** it works, because the extractor already handled route 79's schema, which also lacks the status field.

## What changed

| # | Change | Where |
|---|---|---|
| 1 | F1's step clause uses the rate cap the fork ran. Order: logged `AccordAngleMaxRate` / 100, else 1.2 deg/frame on A16A/A16B (the c6452361e default, since defaults are not written to initData), else the release `values.py` MAX_ANGLE_RATE (2.5), else 2.5 and the output says it is a default. The source is printed on the snap line, the DOSE line and the X3 row. This supersedes the 2026-10-02 literal-1.2 ruling, per the lead's instruction. | `drive_read_v299.py` `rate_cap`, `o1_snaps` |
| 1 | X3 prints the dose that flew, e.g. `cap-250 dose: rate cap 250 deg/s ... clip x1`. Status is `DOSE`. The verdict header reads `V299 cap-250 dose`. | `dose_of`, `verdict` |
| 2 | Rate-bound and clip-bound bits are derived offline when `accordAngleStatus` is absent. Constants are parsed from the fork source, not hard-coded: `MAX_ANGLE_RATE`, `ANGLE_ERROR_MAX_BP/V`, `STEER_STEP` from `honda/values.py`, `MAX_LATERAL_JERK` from `lateral.py`, gravity and `DT_CTRL` from `car/__init__.py`. The hard-coded error-clip table stays only as a fallback, and the output says when it is used. | `fork_constants`, `derive_status`, `derived_vs_logged` |
| 3 | Tap flag from fwVersion (`tap_state`). Every tap section prints `NOT AVAILABLE on release firmware (no tap)`: verdict, R1, R2, R7, replay, A2, friction, light holds, 6B rule identity, 6G cap read, 6H, 6I, F1 replay, F7, F7b, F8, F9. `strongturn` gets a NaN tap, so its ripple and level fields are NaN, not Honda's torque. A16C counts as angle mode for the canValid check. | `angle_loop_drive_read.py`, `drive_read_v299.py`, `high_angle_hunt.py`, `high_angle_probe.py` |
| 4 | Reaction-test hands-off label. A frame whose bar the wheel's own inertia explains is not a hand. The test is Pearson R2 of the bar against wheel angular acceleration, over a centred 1 s window, with R2 >= 0.5 and k > 0. Both labels are printed. F6b is still decided by the pre-registered `|bar| < 300` label. A new row, `F6b-R` (OBSERVATION), counts 1229 freeze onsets under the new label. | `reaction_label`, `handsoff_v3_alt`, `enrichment`, `verdict` |
| 5 | Selftest: A2 and A3 rewritten for the new cap rule. New controls R1 (tap flag), R2 (reaction test), R3 (derived bits), R4 (constants parsed from source). | `drive_read_v299.py --selftest` |

`drive_read_fastlane.py` and `drive_read_fastpresence.py` were reviewed. Neither reads the tap, so neither needed a change.

## Validation

**Derived status bits against the logged bits (EVIDENCE, `derived_vs_logged`, printed in section 6A):**

| route | rows | rate-bound agree | clip-bound agree |
|---|---|---|---|
| 9c | 87302 | 100.0000 % (751 vs 751) | 100.0000 % (447 vs 447) |
| 9d | 80983 | 99.9988 % (2935 logged, 2936 derived) | 100.0000 % (1799 vs 1799) |

- The only miss is row 41374 on 9d: one false positive.
- At that row the carOutput angle did not move. The step of 0.3545 deg, which equals the jerk limit, appears one row later, together with the logged bit.
- **EVIDENCE:** the fork consumed the carControl row before the one the usual alignment picks. It is a one-row message-order slip at a setpoint jump, not a model error.
- The alignment is the previous carControl row and the latest carState row at or before the carOutput row. The same-row alignment scores 99.4 to 99.6 %.
- Carparams steerRatio 16.33 reproduces the bits. 16.84 gives 99.97 % on 9d.
- Rate bound needs the jerk term, not just the cap. The cap alone would miss most rate-bound frames above about 6 m/s.

**Synthetic release check (9c, `--synthetic-release`):**

- It makes the tap garbage (integer torque-like noise, not zeros).
- It clears 0x14A byte-4 bits 3 to 7, rewrites fwVersion to A16C, and drops the status field.
- Runtime is 4.1 s with no stderr output.
- Tap sections print the NOT AVAILABLE line.
- These JSON sections are identical to the full run: exposure, r3, r4, r6, r8, census, goal, dj, dwells, refs.
- In the v299 block these are identical: o1, stutter, enrich, hard, refs, releases, turnins, vm, f10.
- `rp` differs only in 8 `strongturn` fields (ripple and level of the tap). Real values in the full run, NaN in the synthetic run. The F7 count, rate and presence are identical.
- The `snap` block differs only in its clip source: reconstructed instead of the status bit.
- The hunt also completes on the stripped route in 3 s, with the tap columns shown as `-`.
- `--no-tap` on 9d: completes in 4 s, 17 NOT AVAILABLE markers.

**Reaction test:**

- 9c, 704 to 707 s, the routes-review window. The episode is 100 % reaction frames, with median window R2 0.81. All 1.22 onsets per second fall in reaction frames. The probe gives R2 0.89, k 0.616 there.
- Unit control R2: a bar of 0.6 x acceleration is labelled on 100 % of frames and recovers k 0.60. Unrelated noise is labelled on 0 %.
- **BELIEF:** R2 alone cannot separate a hand that accelerates the wheel from a wheel accelerating by itself. That is why the label is an observation and F6b keeps the old one.

## Re-run on the three routes (cached, about 6 s each)

Everything not listed below is byte-identical to the pre-fix output. The RUNTIME, `wrote` and `V299 blocks` timing lines are excluded.

| route | verdict before | verdict after |
|---|---|---|
| 9c V299, cap 250 | FAIL: F1, F6 | FAIL: F6. F1 PASS: 239 false snaps gone, largest step 2.50 equals the cap |
| 9d V299, cap 250 | FAIL: F1 | no FAIL fired. F1 PASS: 115 false snaps gone. NOT TESTABLE: F4a, F4b, F4c, F10 |
| 79 V298, cap 120 | FAIL: F1, F6 | FAIL: F1, F6. Same cause as before (V298 rule wins, status absent, 448 snaps at the 1.2 cap) |

**Changed or removed lines, every one of them:**

- **All three routes**
  - The O1-LIKE SNAPS line: now the fork's cap and its source. On 9c, 9d and 79 the snap event lines under it also changed or were removed.
  - The F1 verdict row and its `bar:` text.
  - The X3 row: `N/A config A` became `DOSE ...`.
- **9c and 9d**
  - The verdict header: `config A` became `cap-250 dose`.
  - The F1 note line about snaps.
  - The stutter null-sentence line: `F1 FAIL` became `F1 PASS`.
- **79**
  - One timing-only change (rule-validation wall seconds).

**Added lines (9c 16, 9d 16, 79 14):**

- DOSE THAT FLEW.
- Limiter constants.
- DERIVED-STATUS CHECK (9c, 9d) or the FIELD ABSENT derived line (79).
- REACTION-TEST label line.
- F6b-R row, 3 lines.

**JSON:** only `v299.snap` and `v299.verdict` changed. New keys: `tap`, `meta.tap`, `v299.tap`, `v299.attrib.{rate_cap, rate_cap_src, release, derived_check or derived}`, `v299.snap.cap_src`, `v299.verdict.dose`, and the extra `onsets1229` keys.

**Reaction-test result on the routes:**

| route | hands-off onsets, `\|bar\| < 300` label | hands-off onsets, reaction label |
|---|---|---|
| 9c | 0 per min | 13.6 per min (n 8, all shorter than 0.1 s) |
| 9d | 0 per min | 0 per min (n 0) |
| 79 | 0 per min | 3.5 per min (n 8, all shorter than 0.1 s) |

On 9c, 5 onsets sit at |theta| >= 60 deg. The reaction label would not fire F6b's 20 per minute bar on any of the three.

## Limits, said plainly

- **Selftest time.** `drive_read_v299.py --selftest` takes 13.0 s for 32 controls. It was already above 10 s before this work. Run it only after editing the reader.
- **6A on release.** The V299-rule validation against the spec mirror still prints on a release route. It checks the image mirror only, not the car.
- **Hunt and probe.** `high_angle_hunt.py` and `high_angle_probe.py` mark tap columns NaN on a release route. `high_angle_chain.py` and `turn_lead_replay.py` were not touched, and neither reads the tap.
- **Rate-bound derivation.** It assumes the fork's vehicle model uses the carParams steerRatio, which 9c and 9d confirm to 99.9988 %. If the release fork changes the model, re-run the derivation check on a route that still logs the field.
- **Untested path.** The release path has been run only on stripped V299 routes. The first real A16C route is the real test.
