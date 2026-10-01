# ADV "wiring + observability" on the V295 fork config (r2 = r1, and r2alt = r1 + AccordTorqueKiHigh 0.8)

Adversary subagent, 2026-09-30. **Analysis only**: nothing was sent, flashed, deployed or committed.
- The fork was read with `git show` / `git archive` at `Dom 20d24ab79` only. Its working tree was not touched.
- STATE, memory, BUILD-LINEAGE and the config files were not edited.
- The FAIL criteria were written before any computation: `ADV-wiring-r2-CRITERIA.md` (W1–W10).
- Scripts and outputs: `adv-wiring/aw1…aw6*.py` and `adv-wiring/out/`.

Marks: **[E]** EVIDENCE (method given), **[B]** BELIEF.

## Verdict: SURVIVES WITH CHANGES

**The files are what the report says they are, and the fork reads them the way the design assumes.**
- None of W1, W2, W3, W5 or W6 fired.
- The only config difference, AccordTorqueKiHigh 0.8, is live on the Accord path.
- On the logged 100 Hz data, the Ki(v) read separates it from r1 frame by frame.
- The firmware c1/c2 read does not move with the fork change.

**What fails is part of the pre-registered outcome sentences (W10), plus one caveat about initData (W8).**
- Some revert triggers fire by chance on one drive at roughly one in three to one in five.
- The "contradicts the model" sentence has no minimum exposure.
- The expected values and the scatter used to judge them come from two different metric implementations.

The file bytes themselves need no change.

| id | result | one line |
|---|---|---|
| W1 wiring | PASS | Every key is read on the Accord torque path under gates that r1's own values open |
| W2 KiHigh semantics | PASS | Ki = interp(v, [8, 18], [0.3, 0.8]), applied to the logged error. The design's port equals the real fork bit for bit with KiHigh 0.8 |
| W3 back-fill / persistence | PASS, with a hazard | No stock sync can overwrite these values. The hazard is a stale compiled params library, and the procedure already covers it |
| W4 range | PASS | Every value lies inside its clamp |
| W5 codec | PASS | Two decoders agree, the restore path was simulated, and 26/26 keys are allowed and coerce to the same value |
| W6 revert | PASS | r2, the r2 revert and the r2alt revert are all byte-identical to the flown r1. r2alt − r1 = {KiHigh 0 → 0.8} only |
| W7 Ki discriminator | PASS | 0.328 / 0.398 / 0.496 / 0.659 / 0.800 by bin, against r1's 0.3000 flat. About 10.6k usable frames per 120 s at 8–22 m/s |
| W8 other reads | PASS, with a caveat | Kp, LAF and the friction plateau read correctly. **initData is a snapshot taken at route start** |
| W9 firmware/fork separation | PASS | c1 0.991–0.992 and c2 1.840–1.841 on an r2alt-like command, including an open-loop stress |
| W10 one-drive claims | **FAIL, in part** | The oversteer turn-hold limit, the "darty" ×1.3 and the absolute 0.6° weave false-alarm often. The contradiction sentence needs an exposure floor. Metric mismatch |

---

## (a) Wiring: how the fork at 20d24ab79 reads each key [E: code read, `git show`, grep strings cited]

**Import path (Galaxy → params).** `the_galaxy.py` `restore_toggle_values` → `_restore_toggle_values` → `_coerce_toggle_restore_value` → `_params_raw.put`.
- **Wrapper checks:** `format` must be None or `"starpilot-toggle-backup"`, and `version` must be an int ≤ 1.
- **`settingsCount` is never read** by the restore.
- **Keys:** a key is written only if it is in `_get_toggle_backup_keys()`. That set is the **compiled** params library's keys that are PERSISTENT, not DONT_LOG, have a default and are not in EXCLUDED_KEYS. Any other key is **silently skipped** and counted in the message: "Skipped N incompatible or unavailable settings."
- **Delta semantics:** keys absent from the file are untouched.
- **No onroad lock for these keys.** Only the personality keys require the car to be parked. (The favourites path does block SteerKP / SteerFriction / SteerLatAccel onroad; the Galaxy restore does not.)

**Runtime (`starpilot_variables.update`, then the per-frame `LatControlTorque.update`).**

| key(s) | read where / gate | clamp | what it does at 100 Hz |
|---|---|---|---|
| SteerKP 0.9 | `get_value("SteerKP", condition=advanced_lateral_tuning and is_torque_car…)`; controlsd writes `LaC.pid._k_p` every frame | [0.05, 3.0] | Flat Kp on `error_with_lsf = error·(1 + lsf/Kp)` |
| AccordTorqueKi 0.3 / **AccordTorqueKiHigh 0.8** | `condition=is_honda_accord and known(...)`; `get_honda_accord_torque_ki(CS.vEgo, ki, ki_high)` | [0.05, 1.0] / [0, 6] | `pid._k_i` is replaced when the value changes. The increment is `i += Ki·0.01·error_with_lsf`, so the state does not step when Ki changes. ki_high ≤ 0 means flat |
| SteerLatAccel 14.0 | `condition=advanced_lateral_tuning`; `use_custom_latAccelFactor` is True (≠ stock 1.689, and ForceAutoTuneOff) | [0.845, 16.89] | output torque = (p+i+f)/14 |
| SteerFriction 0.011 | Same gate; `use_custom_friction` is True, since round(0.011, 2) = 0.01 ≠ 0.21. The stored value stays unrounded | [0, 1] | `get_friction(error_with_lsf + 0.22·fj, dz, 0.30, tp)`: a relay of ±F·LAF = ±0.154 m/s² over a 0.30 threshold (slope = +57 % of Kp) |
| ForceAutoTuneOff 1 / ForceAutoTune 0 / AdvancedLateralTune 1 | Gates for everything above. FATO also forces use_custom_steerRatio and locks paramsd's SR/stiffness | – | – |
| KeepLearnedLatAccelOffset 1 | `controlsd.get_torque_control_params`: the learned offset is used whenever `sm.all_checks(liveTorqueParameters)` and useParams hold. torqued sets useParams for Honda plus torque | – | `ff −= offset·fade` |
| AccordJerkLpHz 1.2 | `jerk_filter.update_alpha(1/(2π·1.2))` | [0.5, 8] | Identical to the generic 1.2 Hz filter |
| AccordRefFilter 0, AccordErrorNotchQ 0, AccordTurnFFTaper 0, AccordDither 0 | Identity paths | – | Inert |
| AccordRatePlantFF 0 → HoldMap, HoldLevel, FrictionHyst(Band), RateLoopGain, DobHz, FFRateGain, EpsGain/SpringScale, DitherGate | Read only inside the `accord_rate_plant_ff` branch | – | **Inert by mode** (carried belt-and-braces) |
| LaneCentering 1 | `toggle.lane_centering` → `LaneCenteringController` | – | Unchanged |

**Back-fill (the route-73 class) [E: the logic of `_sync_stock_param` re-evaluated in `aw1`].**
- Only SteerFriction, SteerKP and SteerLatAccel among the file's keys are synced.
- A value is back-filled only if it is unset, or equal to the recorded stock. The 2026-09-14 fix is present ("An explicit 0.0 is a user value").
- The file values 0.011 / 0.9 / 14.0 are not equal to the stocks 0.212 / 0.6 / 1.689. Every case was tested (steady, stock unknown, stock changed, other-platform stock), and none of them back-fills.
- AccordTorqueKi and AccordTorqueKiHigh are not synced at all.

**Persistence [E].**
- All 26 keys are `PERSISTENT` with no CLEAR_ON_* flag (`common/params_keys.h`), so they survive a boot.
- SafeMode would force all 26 (26/26 are SafeMode-managed) back to stock. r71b had SafeMode 0.

⚠ **Hazard: the committed params library is stale [E: byte search of `git show 20d24ab79:common/params_pyx.so` and `libcommon.a`].**
- Neither contains any `Accord*` key, `KeepLearnedLatAccelOffset` or `LaneChangeTurnGate`. The library was last committed 2026-09-11 ("Revert build").
- The device's own library does know all 26 keys. r71b's initData carries 26/26, and `Params::clearAll` deletes unknown-key files at every manager start (`manager.py: params.clear_all(...)`, `params.cc`).
- **If the device's library is ever reverted to the committed one, r2alt silently becomes r1:**
  - the restore skips KiHigh;
  - the next boot deletes it;
  - the runtime falls back to its default of 0.0.
- r1 is immune, because every r1 Accord value equals its code default.
- The pre-registered runtime-toggle read and the Ki(v) read catch this. So does the Galaxy message: it must say **"Restored 26 toggle settings."** with no "Skipped".

**Preconditions for the keys to matter at all.** These are device state, not in the file; all are verified on r71b initData [E]:
- `ForceTorqueController 1`, `LateralTune 1`;
- `NNFF 0` / `NNFFLite 0`. With NNFF on, controlsd swaps in `LatControlNNFF`, which has no Accord code, so every Accord key is dead;
- `SafeMode 0`, `AccordVariableSteerRatio 1`;
- `FLMTrialApplied False`. FLM changes the friction threshold.

## (b) Codec [E: `aw1_codec_wiring.py`, `out/aw1_codec_wiring_out.txt`]

Two decoders were used:
- **M1** is the fork's own `xor_encrypt_decrypt` / `decode_parameters` / `encode_parameters`, cut out of `git show 20d24ab79:starpilot/system/the_galaxy/utilities.py` (sha256 `5143618c…`).
- **M2** is written by hand: base64, then XOR with the key regex-read from the same file, then JSON.

| file | sha256 | M1 == M2 == .decoded (values and JSON types) | fork re-encode == data | restore sim |
|---|---|---|---|---|
| r2 | `38ba2950…` (= flown r1) | yes | yes | 26/26 allowed, 26/26 coerce unchanged |
| r2 REVERT | `38ba2950…` | yes | yes | same |
| **r2alt** | `c428be32…` (decoded `149a6473…`) | yes | yes | same; `AccordTorqueKiHigh` FLOAT ← JSON 0.8 → 0.8 |
| r2alt REVERT | `38ba2950…` | yes | yes | same |

- **The delta:** over the union of keys, r2alt − r1 = `{AccordTorqueKiHigh: (0.0, 0.8)}`, with the same key set.
- **The reverts** name every key r2alt sets, so the delta format cannot leave 0.8 behind.
- **No typo keys:** every key exists in `params_keys.h`.
- **Types match the importer.** BOOL keys get JSON bools; FLOAT keys get JSON floats and never bools. A bool on a FLOAT key would be rejected and silently skipped.

## (c) Observability

**The fork reads on r71b with the r2alt value substituted.** [E: `aw2_reads_replay.py`]
- **Method.** r71b's own inputs were replayed through the **real** `LatControlTorque` @20d24ab79, using the harness `h3` path with post-hoc alignment. It is open loop.
- **Control:** the r1 replay equals the logged torqueState (p 9.7e-7, i 2.4e-7, f 6.2e-5, output 4.4e-6, error 1.1e-6).
- The read arithmetic is the attribution script's own, on float32 fields.

| read | logged r71b | r1 replay | **r2alt replay** | second method |
|---|---|---|---|---|
| Kp = p/error | 0.90000 | 0.90000 | 0.90000 | – |
| LAF = (p+i+d+f)/−output | 14.0000 | 14.0000 | 14.0000 | – |
| friction plateau p95 | 0.157 m/s² = 0.0112 torque = 46 counts | same | same | – |
| Ki, 1–8 m/s | 0.3000 [IQR 0.3000–0.3000] | same | **0.3000** | fork closed form 0.3000 |
| Ki, 8–9 | 0.3000 | 0.3000 | **0.328** [0.315, 0.339] | closed form 0.328; OLS 0.327 |
| Ki, ~10 | 0.3000 | 0.3000 | **0.398** [0.387, 0.410] | 0.398; OLS 0.408 |
| Ki, ~12 | 0.3000 | 0.3000 | **0.496** [0.485, 0.508] | 0.496; OLS 0.496 |
| Ki, ~15 | 0.3000 | 0.3000 | **0.659** [0.646, 0.668] | 0.659; OLS 0.657 |
| Ki, ≥ 18 | 0.3000 [0.3000–0.3000] | 0.3000 | **0.8000** [0.8000–0.8000] | 0.800; OLS 0.804 |
| integrator share, ≥ 15 m/s (mean ratio) | 0.308 | 0.308 | 0.579 (open loop, an **upper bound**; design predicts +0.01…+0.05 closed loop) | – |

- **The per-frame read equals the fork's closed form** within p99 4e-4, on 99.9 % of frames within 0.005.
- **The read gives Ki, not Ki·(1+lsf/Kp),** because the logged error already carries the lsf factor.
- **Yield:** 44,527 usable frames in 505 s at 8–22 m/s, about 10,600 per 120 s. **A few seconds above 18 m/s decides it.** W7 PASS.

**The design simulated the fork that will run.** [E: `aw6_port_r2alt_gate.py`]
- The design's own `VecPort` with KiHigh 0.8 was run against the real fork with `accord_torque_ki_high 0.8`, frame by frame over the whole r71b replay (101,157 frames), with neither state ever re-synchronised.
- Max |d|: p 0, i 0, f 5.6e-17, torque 3.5e-18, for both r1 and r2alt.
- The f1 control proved this for r1 only. It now holds for r2alt too.

**initData is a route-start snapshot.** [E: `system/loggerd/logger.cc`]
- `LoggerState::LoggerState` builds `init_data` once per route, and `next()` rewrites the same bytes into every segment.
- A Galaxy restore done **while onroad** takes effect live (`update_starpilot_toggles` → background refresh) but is invisible to initData for that whole route.
- ⇒ **The runtime `starpilotPlan.starpilotToggles` (first + changes, timestamped) and the Ki(v) read are primary. initData confirms only a restore made before the route started.**

**Firmware c1/c2 is independent of the fork change.** [E: `aw3_c1c2_independence.py`, using ADV-B's byte-exact lane with cells from the V294/V295 images]
- **Method.** r71b's command was replaced by an r2alt-like command: wire − 4096·k·(torque_r2alt − torque_r1), taken from the open-loop real-fork replay.
- **Synthetic V295 tap:** r71b's real residual plus quant(L5′).
- **Scoring:** ADV-B's hands-off frames, pooled OLS with a 10 s block CI, gated 15 s windows, and model selection by rms.

| series | c1 | c2 | gated 15 s windows > 1.45 | rms V295 / V294 march |
|---|---|---|---|---|
| drive (1): V295 on r71b's command | 0.991 | 1.837 [1.829, 1.844] | 25/25 | 2.25 / 13.25 |
| calibration: the real r71b tap (V294) | 0.991 | 0.989 [0.980, 0.998] | 0/25 | 12.97 / 2.25 |
| drive (2): V295 on r2alt command, k 0.3 (rms 57 counts) | 0.991 | 1.840 [1.832, 1.846] | 25/25 | 2.25 / 13.17 |
| drive (2): k 1.0 stress (rms 190, max 734 counts) | 0.992 | 1.841 [1.833, 1.847] | 25/25 | 2.25 / 13.16 |
| control: V294 on r2alt command, k 1.0 | 0.992 | 0.993 | 0/25 | – |

- Max |L5′| was 1357 counts, against the 2461 rail, so the lane stays linear.
- ⚠ **Misuse trap:** scoring drive (2) with drive (1)'s regressors gives **c1 1.03–1.11** and c2 1.88–1.97. c1 must come from drive (2)'s own march of drive (2)'s own command.
- BELIEF: x is not perturbed here. The < 1 Hz integrator change moves little of the 1–3 Hz wheel acceleration that excites the trim.

**What one drive can and cannot decide.**
- Scatter sources: r71b pseudo-drive bootstraps in `aw4` and `aw5`, and ADV-B b7.
- A within-route bootstrap is a **lower bound** on real drive-to-drive scatter.

| sentence (design s7) | one drive? | basis |
|---|---|---|
| V295 live (c2 > 1.45) | **Yes**, on both drives, unaffected by the fork | [E] above; ADV-B's gated windows |
| r2alt landed (runtime 0.8 plus the Ki(v) schedule) | **Yes**, deterministic | [E] aw2 |
| Kp / LAF / friction unchanged | **Yes** | [E] aw2 |
| initData AccordTorqueKiHigh 0.8 | **Only if restored parked, before the route** | [E] logger.cc |
| **Null:** 8–22 m/s tracking within drive (1) ± 0.06 cannot distinguish | **Correct, and understated.** The pooled 8–22 band depends on speed mix (in the design's metric, 10–15 reads 0.58 and 15–22 reads 0.83). Its d-v-d 90 % is about ±0.2–0.35 in the design's own metric, so the power for +0.06 is 0.06–0.09 | [E] aw5 chunk bootstrap (coarse: 21 chunks) |
| 15–22 m/s tracking rise (+0.09…+0.10) | **Only with ≥ 120 s of engaged 15–22 m/s.** At 120 s: d-v-d [−0.03, +0.05], power 0.95. At 60 s: ±0.25, power 0.07 | [E] aw5 (coarse) |
| **Contradiction:** 15–22 tracking below drive (1) by > 0.06 | **Not decidable below about 120 s.** At 60 s, no-change scatter reaches −0.26 (design's metric) or −0.11 (b7's). A false "contradiction" is likely | [E] aw5, b7 |
| 22+ m/s changes (+0.03…+0.045) | No. b7 tracking ±0.08 at 60 s; r71b had 70 s at 22+ | [E] b7 |
| Integrator share +0.01…+0.05 | No. The direction is confirmed only open loop | [B] |
| **Revert: tracking > 1.05** | OK. P(fires) ≤ 0.04 if r2alt behaves as predicted | [B] normal approximation on b7 bands |
| **Revert: turn-hold > 1.10 in ANY band** | **False-alarms.** P per drive ≈ 0.19 (0–5 m/s, where r2alt = r1 by gain) and 0.14–0.20 (22+). About 38 % that a correctly behaving r2alt trips at least one band | [B] normal approximation on b7 |
| **Revert: "darty", straight 1–5 Hz rate > ×1.3 drive (1)** | **False-alarms as written.** No-change P(ratio > 1.3) is 0.13–0.37 at 0–15 m/s for 30–120 s, and 0.34–0.42 with no speed band. At ≥ 15 m/s and 120 s it is 0.09, but r71b had only 84 s straight at ≥ 15 | [E] aw4 bootstrap |
| **Revert: 0.2–1.5 Hz straight weave at ≥ 15 m/s, "about 0.6° p-p"** | **Not usable as an absolute.** r71b's background p-p in that band is already **0.50–0.60°** (median 0.54). A 0.6° hunt added on top roughly doubles it (×1.76–1.85), so a relative rule could see it. r71b had only **2** straight hands-off 10 s windows at ≥ 15 m/s | [E] aw4 |
| **Metric identity** | The expected values use `H.drive_metrics` (f13); the quoted ±0.06 / ±0.12–0.15 is b7's, a different implementation. At 10–15 m/s, r71b tracking reads **0.583** in one and **0.691** in the other | [E] f13 out vs b7 out |

**The carry-over.** "Below 8 m/s it is r1 exactly" is true of the **gain**, not of the **integrator state** carried in from above 8 m/s.
- Open-loop upper bound: |Δi| p95 1.9 m/s² (0.135 torque) in the first 10 s below 8 m/s after leaving ≥ 8.
- It is 0 in engagements that never exceed 8 m/s.
- In closed loop it is transient. The design's closed-loop drive sim puts 0–5 m/s tracking Δ ≤ 0.001 [E model].
- The G4 hunt test runs at constant speed, so it cannot see carry-over. This is a wording defect, not a wiring one.

## (d) What r1 carries that the designer might have changed or pinned (reported, not decided)

1. **The file is not a complete statement of the lateral state**, despite f9's docstring saying it is.
   - These inputs sit on the same controller path but are not in the file (values from r71b initData):
     - `SteerRatio 16.84`, the level of the variable-SR map via FATO;
     - `AccordVariableSteerRatio 1`, `ForceTorqueController 1`, `LateralTune 1`, `NNFF 0` / `NNFFLite 0`;
     - `UseAutoSteerDelay 1` / `SteerDelay 0.2`, `LatSmoothSeconds 0.1`, `SafeMode 0`;
     - `LaneCenteringE2EAuthority 0.2`, `LaneChangeTurnGate 1`, `LaneChangeSmoothing 4`.
   - An A/B across two drives should diff **all** lateral initData keys, not just the 26.
2. **KeepLearnedLatAccelOffset: true, kept.** The wire supports it: offset + integrator ≈ roll compensation. But:
   - the offset is a drifting covariate. Within r71b it moved −0.10 → −0.18 m/s², and each drive starts from the cached value;
   - torqued fits it with a slope that reads 5.2 raw (2.06–2.33 filtered and clipped), while the controller divides by LAF 14.
   - Log `ltp_off` at the start of each drive.
3. **UseAutoSteerDelay 1 is not pinned.** lat_delay = the learned liveDelay (0.326 s on r71b) + 0.1.
   - The design's stage 6 shows ±0.1 s trips G6/G8. A lagd change between the drives would confound the G6/G8-class reads.
   - Pinning it (UseAutoSteerDelay 0, SteerDelay 0.326) would remove the confound, but it changes r1. Record liveDelay on both drives.
4. **LaneChange\* keys are not pinned.** Lane changes put transients into the band metrics. Exclude `laneChange` windows from the band reads.
5. **The gated r2 (= r1) as drive (2)** would give the kit its first genuine drive-to-drive replicate. Every scatter used here is a within-route lower bound.

## Required changes (to the pre-registration and procedure; the files stand)

1. **Oversteer revert:**
   - use tracking gain > 1.05 per band;
   - if turn-hold > 1.10 is kept, require ≥ 120 s of exposure in that band and a CI clear of 1.10;
   - drop 0–8 m/s from r2alt's revert, since r2alt's gain equals r1's there.
2. **"Darty" ×1.3:**
   - restrict it to straight, hands-off frames at ≥ 15 m/s, with ≥ 120 s of exposure, as a ratio to drive (1);
   - otherwise call it NO CALL.
   - As written, the no-change false-alarm rate is 0.13–0.42.
3. **Weave:**
   - define it relative to drive (1): 0.2–1.5 Hz angle p-p ≥ 2× drive (1)'s median over straight hands-off 10 s windows at ≥ 15 m/s, or a sustained spectral line;
   - drop the absolute "0.6°", which equals r71b's own background;
   - make it NO CALL below about 5 qualifying windows.
4. **Contradiction sentence** (15–22 tracking < drive (1) − 0.06):
   - require ≥ 120 s of hands-off engaged 15–22 m/s exposure on both drives;
   - name the metric (`H.drive_metrics` tracking gain, the |plan| > 0.3 slope) and derive its scatter with the same code.
   - Treat 15–22 m/s, not the pooled 8–22, as r2alt's primary band.
5. **Attribution order:**
   - the runtime toggles (first + changes, with timestamps) and the Ki(v) read come first; initData counts only if the restore preceded the route;
   - restore while parked, before the drive, and confirm "Restored 26 toggle settings." with no "Skipped".
6. **Drive-to-drive covariates:**
   - diff the full lateral initData set: SteerRatio, AccordVariableSteerRatio, NNFF, NNFFLite, ForceTorqueController, LateralTune, UseAutoSteerDelay, SteerDelay, LatSmoothSeconds, SafeMode, LaneCentering\*, LaneChange\*;
   - log `ltp_off` and `liveDelay` at each drive's start.
7. **c1/c2 on drive (2)** must use drive (2)'s own march of its own command. Reusing drive (1)'s regressors biases c1 to 1.03–1.11.
8. **Reword** "below 8 m/s it is r1 exactly" to: "below 8 m/s Ki is r1's; the integrator state carried in from higher speed is not".

## Files

| file | what |
|---|---|
| `ADV-wiring-r2-CRITERIA.md` | W1–W10, written first |
| `adv-wiring/aw1_codec_wiring.py` → `out/aw1_codec_wiring_out.txt` | two decoders, the restore simulation, clamps, the back-fill cases, the compiled-library key search, SafeMode |
| `adv-wiring/aw2_reads_replay.py` → `out/aw2_reads_replay_out.{txt,json}` | real-fork replay of r1 / r2alt; Kp, Ki(v), LAF, friction, i-share; carry-over |
| `adv-wiring/aw3_c1c2_independence.py` → `out/aw3_c1c2_independence_out.txt` | the c1/c2 read on an r2alt-like command, stress and control |
| `adv-wiring/aw4_revert_scatter.py` → `out/aw4_revert_scatter_out.txt` | "darty" / weave no-change scatter; oversteer false-alarm odds |
| `adv-wiring/aw5_metric_scatter.py` → `out/aw5_metric_scatter_out.txt` | one-drive scatter of the design's own metric |
| `adv-wiring/aw6_port_r2alt_gate.py` → `out/aw6_port_r2alt_gate_out.txt` | design VecPort (KiHigh 0.8) against the real fork, bit for bit |
| `adv-wiring/_aw2_replay.npz` | replay torques (gitignored) |
