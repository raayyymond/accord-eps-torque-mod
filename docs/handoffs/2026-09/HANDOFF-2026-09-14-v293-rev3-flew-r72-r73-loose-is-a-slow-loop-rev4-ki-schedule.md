# HANDOFF 2026-09-14 (evening) — V293 rev 3 FLEW (routes 72 + 73): "loose" is a slow loop under a route-dependent feedforward; route 73 secretly ran a 0.212 friction relay; rev 4 = speed-scheduled Ki + relay gate + stock-sync fix + one hold-map knot (fork code + toggle config)

> **Status.** V293 is on the car, unchanged — nothing built, flashed or sent (the operator: *"I do not expect this to be a
> firmware iteration session"*). The operator drove the **rev-3** fork package (`Dom` `e8e62f0e1` +
> `toggle-config_V293_torque_mode_r3.json`) on **two routes**, `75604b0a432fdc89_00000072--8001fc3048` (16 segments, 627 s
> laterally engaged) and `75604b0a432fdc89_00000073--79fd149dd8` (11 segments, 599 s), and scored them together: *"better
> than rev 2; still feels a little loose; still jerky on hard turns; still doesn't feel as good as the 1 kHz inner loop did —
> not as smooth, 'confident', and well-controlled."* He also said he had **turned live delay learning on** himself.
> **Delivered: fork commits `f4e314da6` (rev 4) + `08a5a7064` (its test fix) on `Dom`, `toggle-config_V293_torque_mode_r4.json`
> (+ `_REVERT_to_r3`), the device pulled / params rebuilt / 21 keys written / rebooted, and the page
> https://claude.ai/artifact/MS72a2oMecgGmj4x2yqsGg (signal flow with the edits, every LERP before/after, the simulated
> consequence, the risk).** Previous narrative: `HANDOFF-2026-09-14-v293-rev2-flew-2hz-limit-cycle-rev3-hold-map-rate-loop.md`.

---

## 1. Attribution — the two routes were NOT the same drive [EVIDENCE]

Both: `GitCommit e8e62f0e1`, the five rev-3 keys present (`AccordHoldMap 1`, `AccordFrictionHyst 0.015`, `AccordRateLoopGain
0.0006`, `AccordErrorNotchQ 1.0`, `AccordRefFilter 0.12`), `SteerKP 0.85`, `SteerLatAccel 14`, `AccordTorqueKi 0.6`; wire reads
`p/error` **0.8500** and `−(p+i+f)/output` **14.0000** (IQR = median on both). Both: `UseAutoSteerDelay = 1` (the config wanted 0;
the operator's own choice) → `liveDelay.lateralDelay` **0.274 s** estimated, used by the controller.

🛑 **Route 73 ran `SteerFriction = 0.2120497077703476` — the STOCK Accord friction (`torque_data/params.toml`).** Route 72 ran
0.0. Mechanism, read from the fork source: `StarPilotVariables._sync_stock_param("SteerFriction", "SteerFrictionStock", friction)`
runs at start-up; when the recorded stock baseline differs from the live stock value, it back-fills the live key if the live
value is "tracking stock" **or is 0.0** — an explicit 0.0 counted as *unset*. The rev-3 config sets 0.0 on purpose. With
`ForceAutoTuneOff 1`, `use_custom_friction` is True and the toggle value feeds `torque_params.friction` → `get_friction` →
`friction_torque` inside the Accord plant-FF branch. The device still carried `SteerFriction 0.212 / SteerFrictionStock 0.212`
when this session began (read from `/data/params/d`). Reconstructed on the wire: relay rms **0.095 torque**, |relay| ≥ 0.1 for
21.7 % of engaged frames, **239 sign flips/min**; small-signal gain 0.212/0.30 × 14 = **9.9** in `SteerKP`'s units (Kp 0.85).
My S6 replay of the feedforward from the wire reproduces route 72's `f` with R² 1.000 in every band and route 73's with
R² 0.30–0.67 — the residual IS the relay.

## 2. What the wire said [EVIDENCE — `rlog-tools/studies/grind/v293r3_read.py`, report `V293-REV3-READ-r72-r73-2026-09-14.txt`; scorer v2 `V293-FLIGHT-READ-r72/r73-2026-09-14.txt`]

**2a. Route 72 (rev 3 as written): "loose" = a slow loop under a wrong feedforward.** Against the PLANNER's desired lateral
acceleration (desiredCurvature·v², the goal metric — the shaped setpoint hides the reference filter's lag):

| band | rms planner error | gain planner→actual | lag | \|H\|(0.2 Hz) / coh | error share <0.3 Hz | f share of torque (<0.3 Hz) |
|---|---|---|---|---|---|---|
| 1–8 | 0.143 | 0.96 | 0.00 | 0.97 / 0.97 | 18 % | 92 % |
| 8–15 | 0.116 | 0.98 | 0.11 | 0.88 / 0.93 | 56 % | 76 % |
| 15–22 | 0.107 | **0.80** | **0.46** | **0.66** / 0.80 | 79 % | 68 % |
| >22 | 0.138 | **0.74** | **0.52** | **0.76** / 0.93 | 83 % | 73 % |

Route 71 (rev 2) for contrast: gain 0.91 / 1.02 / 1.12, lag 0.00, f/u at >22 = 1.23 (the linear tables OVER-delivered and the
loop subtracted). Route 72's P+I supplied +24…+32 % of the low-frequency torque in the FF's own direction — the rev-3 map
UNDER-delivers at 8–30 m/s and the loop (Kp 0.85, Ki 0.6 through LAF 14: I time constant ≈ 1.4 s) is too slow to make it up.
A static plant model reproduces it: with the FF at fraction φ of the need, |T(0.2 Hz)| ≈ φ + (1−φ)·0.55 → 0.77 at φ = 0.5.

**2b. The hold map's error is ROUTE-DEPENDENT, so it is the integrator's job.** Per-stretch regression of the total torque
(0.5 Hz LPF) on the map at the MEASURED angle, hands-off (`v293r3_holdlevel.py`): routes 70/71 (the fitting routes)
**×1.10–1.25** at 8–30 m/s; route 72 **×1.57–1.71** at 15–30; route 73 ×1.29–2.07, with **left 3.01 vs right 0.90** at 15–22.
Still-wheel cells at 4–8°, >22 m/s: r70 1.22, r71 0.83, r72 1.67 — a ×2 spread between yesterday's two routes in the same
cell. Crown, wind and the speed law (route 72's >22 band median 25.7 m/s vs the fit's 22.8; the map is flat above 23 m/s
while the aligning torque rises with speed for a given angle) move the small-angle hold by ±30–70 % from road to road.
**No static map can be right to better than that; the loop must absorb it, and rev 3's loop could not.** The dynamic free
fits (a, b, J, F) on r72/r73 are closed-loop-biased by the stronger rev-3 controller and are NOT plant numbers.

**2c. Route 73 = the accidental high-gain experiment.** Tracking gain 0.98 / 0.98 / 0.97, rms planner error **0.047 / 0.043 /
0.054** (2.5× better than r72), |H|(0.2) 0.92–0.98 — and a **3.8–4.7 Hz rate line at +5.6…+9.6 dB on straights**, **66 rate
reversals/min** and **21 % of frames at the Honda 0xE4 rate cap** in low-speed hard turns (r72: 12/min, 0.3 %), cmd step
p99 246 counts (r72: 68). That is *"jerky on hard turns"* — the relay's describing-function limit cycle, not rev 3's design.
Route 73 also carried most of the session's hard turns (31 s of |plan| > 1.5 vs 14 s on r72).

**2d. What rev 3 fixed, as bands (the operator scores the symptoms).** No 2.34 Hz limit cycle on either route; no distinct 2 Hz
line on straights (the 1.66 Hz "peaks" in S3 are the band edge, not a line); low-speed hard-turn 0.5–5 Hz rate rms **47 deg/s**
on r72 vs 60 (rev 2) / 86 (rev 1); the route-71 stall→ramp→snap signature 0/min on both. Unchanged: |rate| > 80 deg/s bursts
in low-speed hard turns 81/min (rev 2: 83) — stiction + the delayed P, not addressed by rev 3 or rev 4. Scorer v2 fired its
ratchet REVERT on both routes (dwells/min at th 0.25 above r70's); as pre-warned in the rev-3 handoff §7 it counts loop
zero-crossings as dwells and on r73 it is counting the relay. The scorer's "identity" row read R² 0.976 on r72 (FAIL at its
0.98-class bar) and 0.942 PASS on r73 with an impaired positive control (0.63): the tap identity is noisier on today's more
dynamic driving; nothing was flashed, the ECU is V293.

## 3. The diagnosis in the operator's three sentences

| his words | what the wire says | cause |
|---|---|---|
| "still a little loose" | r72 gain 0.74–0.80, lag 0.5 s, 79–83 % of the error below 0.3 Hz at 15–30 m/s | the hold FF is 20–70 % wrong from road to road and Ki 0.6 / LAF 14 takes ~1.4 s to make it up |
| "still jerky on hard turns" | r73: 4–4.7 Hz chatter, 66 reversals/min, 21 % rate-capped; r72: bursts 81/min unchanged | r73 = the back-filled 0.212 relay (a fork bug); r72 = stiction + delayed P at low speed (open) |
| "not as good as the 1 kHz inner loop" | the first ~0.5 s after any disturbance is plant + 60 ms round trip; a 100 Hz loop cannot shorten it | the EPS rate loop had that bandwidth with no delay; the fork cannot replace it — see §6 |

## 4. Rev 4 — what shipped (fork `f4e314da6` + `08a5a7064` on `Dom`; config `toggle-config_V293_torque_mode_r4.json`)

**Fork code (all Accord-gated, defaults = the rev-4 flight values, Safe Mode = off):**

| change | what | why |
|---|---|---|
| `AccordTorqueKiHigh` (new key, default 2.5, stock 0 = flat) + `get_honda_accord_torque_ki(v, ki_low, ki_high)` | Ki = `AccordTorqueKi` below 8 m/s, `AccordTorqueKiHigh` from 18 m/s, linear between; applied per frame (PIDController scales the increment, so no integrator step) | §2a/2b. Simulated (`v293r4_design.py`): 2 s residual of a 0.03-torque bias at 19–26 m/s **0.11–0.12 → 0.005–0.013 m/s²**, Ms 1.75 unchanged, PM >100°; at 5 m/s Ki 2.5 rings a curve-hold kick to 16–36° pk-pk (the lsf already ×7 there) → the schedule |
| `_sync_stock_param`: an explicit 0.0 is a user value | back-fill only an UNSET key or one still tracking the recorded stock baseline; a user value with no baseline is never touched | §1 — route 73 |
| Accord branch: `friction_torque = 0` while `AccordFrictionHyst > 0` | the generic relay would double-count the friction the hysteresis FF supplies, and it is what ran away | §1/§2c, defence in depth |
| `HONDA_ACCORD_HOLD_K_V[28 m/s]` 0.0134 → **0.0160** (×1.20) | a v^1.0 rise 23→28 instead of flat; deliberately short of v² (×1.48) | §2b [BELIEF for the size] |

**Rejected, with numbers:** Kp 1.1 (+6 % on the 4 s rms, PM 103° → 62° at 26 m/s); Kp 1.6 (Ms 4.0); Ki 2.5 flat (low-speed
ring); ref filter 0.08 (step overshoot +64 % → +88 % for 0.06 s of rise); whole-map ×1.3 (overshoots where the map is right);
AccordFrictionHyst 0.020 (the kinetic F measured 0.004–0.009; a static-size preload can start the wheel and then overshoot).

**Config (delta, 21 keys):** rev 3 + `AccordTorqueKiHigh 2.5`, `UseAutoSteerDelay true` (the operator's choice, 0.274 s on the
wire), `SteerFriction 0.0` (now safe). Revert: `toggle-config_V293_torque_mode_r4_REVERT_to_r3.json` (`AccordTorqueKiHigh 0`).
Generator `tools/make_galaxy_toggle_config.py` (REV 4 block). Scorer `v293_flight_read.py` knows the key and the commit gate
(`want` 08a5a7064 or f4e314da6, `forbid` e8e62f0e1) — run on r72 against the r4 config it correctly FAILs the commit gate.

**Device (comma@10.0.0.168):** pulled `08a5a7064`; `rebuild_params()` ran (221 s, `missing_before: [AccordTorqueKiHigh]`,
`missing: []`); the 21 keys written with the typed setters and read back from `/data/params/d`; rebooted; after 5 min of
manager uptime `SteerFriction` still reads **0.0** with `SteerFrictionStock 0.212` — the sync fix holds. **Tests RUN ON THE
DEVICE:** `test_starpilot_variables.py` + `test_device_settings_layout.py` + `test_safe_mode.py` **72 passed**;
`test_latcontrol.py` **193/195** (the two Bolt/Palisade failures pre-exist on e8e62f0e1). Rev-3 baseline check on the device:
the two variables tests that failed on my first cut pass at e8e62f0e1 and pass after the fix (a mock-Params `len()` issue).

## 5. Pre-registered read of the next drive (rev 4 vs route 72)

Attribution first: `GitCommit` 08a5a7064 (or f4e314da6), `p/error` 0.85, `−(p+i+f)/output` 14, **`SteerFriction 0.0` in
`initData`** — if it reads 0.212 the sync fix failed; stop and report. Success: planner tracking gain 0.95–1.05 and |H|(0.2 Hz)
≥ 0.9 at 15–22 and >22 (r72 0.80/0.74, 0.66/0.76); rms planner error ≤ 0.08 m/s² there (0.107/0.138); lag ≤ 0.3 s (0.46/0.52).
Integrator share ≥ 0.25 is now BY DESIGN and not a fail. **Revert triggers:** a coherent 0.3–0.8 Hz line in command AND angle
on highway curves (the slow hunt) → `AccordTorqueKiHigh 1.5`; anything worse than r72 → the REVERT file. Read with
`v293_flight_read.py <route> --config …_r4.decoded.json` then `v293r3_read.py <tag> r72_v293r3 r71_v293r2`.

## 6. What rev 4 does NOT do — and the standing question for the firmware

The first ~0.5 s after a disturbance (T1 |e| at 0.5 s: 0.14–0.24 m/s² at 19–26 m/s, identical for every fork gain) is the
plant's own response through a 60 ms round trip; only P and the rate loop act there and both are delay-limited (Kp 1.6 → Ms 4;
Kv 0.0012 → 3.5–4 Hz crossing). **That half-second is what the 1 kHz EPS rate loop covered on V282**, and it is the residual
the operator calls "confident". If rev 4 tracks (gain ~1, lag ≤ 0.3 s) and still feels less controlled than V282, the next
lever is a firmware damper / inner loop with V293's map as its feedforward — the class the rev-3 handoff §7 named. Not this
session; the operator's call.

Low-speed hard-turn bursts (81/min on r72, unchanged from rev 2) are stiction + the lsf-driven P; rev 4 leaves low speed
untouched by design.

## 7. Files

**Fork (`raayyymond-StarPilot/StarPilot` @ `Dom`)**: `f4e314da6` — `common/params_keys.h`, `selfdrive/controls/lib/latcontrol_torque.py`,
`latcontrol_vehicle_tunes.py`, `selfdrive/controls/tests/test_latcontrol.py`, `starpilot/common/starpilot_variables.py`,
`starpilot/common/safe_mode.py`, `starpilot/common/assets/device_settings_layout.json`, `starpilot/common/tests/test_starpilot_variables.py`,
`starpilot/system/the_galaxy/tests/test_device_settings_layout.py`; `08a5a7064` — the isinstance guard + test fixes.
**Kit (tracked):** `rlog-tools/studies/grind/v293r3_read.py` (S0–S9, multi-route comparison), `v293r3_ffneed.py`,
`v293r3_holdlevel.py`, `v293r4_design.py`; reports `V293-REV3-READ-r72-r73-2026-09-14.txt`, `V293-FLIGHT-READ-r72-2026-09-14.txt`,
`V293-FLIGHT-READ-r73-2026-09-14.txt`, `V293-REV4-DESIGN-SWEEP-2026-09-14.txt`, `V293-REV4-FF-NEED-AND-HOLD-LEVEL-2026-09-14.txt`;
`v293_flight_read.py` (rev-4 key + commit gate); `tools/make_galaxy_toggle_config.py`; the r4 + revert config pairs in
`analysis-2020accord/reference/`; the ident caches `r72_v293r3` / `r73_v293r3` (`_scratch`, regenerable with
`v293r2_extract.py r72_v293r3=75604b0a432fdc89_00000072--8001fc3048 …`); this handoff; `docs/STATE.md`; memory. No firmware
artifact → nothing for `accord-firmwares`. No subagents were spawned this session (the operator asked for the comprehension
and design to be done directly; the turnkey tools did the data gathering).
