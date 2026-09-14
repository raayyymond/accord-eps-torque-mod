# ADVERSARIAL PASS — the rev-2 fork package for the next V293 drive

Adversary subagent, 2026-09-13. **Analysis only**: nothing built, flashed, sent on any bus, or committed;
no file outside this one was written. Every number is re-derived from the SOURCES — the fork at
`raayyymond-StarPilot/StarPilot` @ `Dom`, the identified plant, and route 70's own rlog cache — never from
the orchestrator's brief. Scripts: `C:\Users\dudei\.claude\jobs\ad52c287\tmp\adv\{adv_lib,a1_ff_surface,
a2b_margins,a3_r70_replay,a4_sim,a5_transients,a6_bounds,a7_lowspeed}.py`.

> **DISPOSITION (orchestrator, 2026-09-13 night) — applied before the package was offered:** finding 1 → the on-disk config is the
> intended one (LAF 14 / Kp 0.85 / Ki 0.30 / friction 0.011; every document, the scorer and the page now agree; `UseAutoSteerDelay` 0
> kept). Finding 2 → `AccordFFRateGain` 1.0 → **0.5** (config regenerated). Finding 3 → fork commit `8c4051ce6` lowers the low-speed
> knots: `HONDA_ACCORD_EPS_K_V` [0.93, 1.64, …] → **[0.30, 1.00, 2.15, 2.77, 3.15]** (hold 0.00055 / 0.00086 / 0.0023 / 0.0041 per deg at
> ≤4 / 5 / 8 / 10 m/s — 25 % over the route-70 bound at 5, 25 % under the v² extrapolation at 8–10). Finding 4 recorded as the
> expected low-speed 'loose' cost. Finding 14 → the `−(p+i+f)/output = SteerLatAccel` identity added to the scorer's attribution
> block; the f/D gate was already retired by scorer v2. Findings 11/13 → checklist (device fork ≥ `8c4051ce6`; a stale params module
> shows up as absent keys in `initData`). Verdict carried: **FLY-WITH-CHANGE, changes applied.**


## VERDICT: **FLY-WITH-CHANGE**

Three changes, none of them expensive:

1. **Resolve which config is the package** — the brief and the file on disk are different tunes.
2. **`AccordFFRateGain` 1.0 → 0.5 (or 0.40)** — at 1.0 the feedforward alone passes full-scale torque in
   the low-speed band on route 70's own demand, and roughly doubles the low-speed entry overshoot.
3. **Carry the low-speed over-command into the checklist as the named revert trigger**, and add the two
   exact 100 Hz attribution reads below.

Nothing I found reaches DO-NOT-FLY. Both candidate configs are a stability *improvement* on the flown
one at every speed and under every plant model I could build, and both cut the flown build's torque-rail
duty below 8 m/s by about 6×.

---

## What a DO-NOT-FLY would have looked like (pre-registered, before any analysis)

Written to `.../tmp/adv/PREREG-DO-NOT-FLY.md` before the first script ran:

| id | criterion | result |
|---|---|---|
| D1 | low-speed over-command not recoverable (>30 deg past command, or the wheel pinned) | **partially met** — recoverable, but the transient doubles: see §3 |
| D2 | limit cycle >2 deg or in 1–10 / 15–25 Hz at the chosen SteerFriction | **not met** — clean null, §6 |
| D3 | wind-up lurch > 0.1 torque | **not met** — worst step 0.005, §7 |
| D4 | a param clamped, unknown, or read once so the restore does not take | **not met**, §9–§11 |
| D5 | a package number not re-derivable from the source | **met on the CONFIG**, §1 |
| D6 | re-engagement / lane-change divergence | **not met**, §8 |
| D7 | the drive cannot be attributed on the wire | **not met** — two exact gates exist, §14 |

---

# FINDINGS, ranked by severity

## 1. 🛑 The brief and the file on disk are DIFFERENT CONFIGS [EVIDENCE]

`analysis-2020accord/reference/toggle-config_V293_torque_mode_r2.decoded.json` and its generator
`tools/make_galaxy_toggle_config.py:117-134` (`TORQUE_MODE_R2`) carry:

| key | brief (b) | file on disk | ident's own pick |
|---|---|---|---|
| `SteerLatAccel` | 12.0 | **14.0** | 12.0 (J3 "C10") / 14.0 (K3 "R2′") |
| `SteerKP` | 0.70 | **0.85** | 0.70 (C10) / 0.92 (R2′) |
| `AccordTorqueKi` | 0.20 | **0.30** | 0.20 (C10) / 0.35 (R2′) |
| `SteerFriction` | 0.012 | **0.011** | 0.011–0.012 |
| `UseAutoSteerDelay` | not listed | **false** | required for `SteerDelay` to be read at all |

The file is a hybrid: C10's **code tables** (`AccordEpsSpringScale` 1.0) with R2′'s **loop gains**, and
R2′ was scored on the OLD tables with spring scale 2.15. **Neither J1 nor K1 scored the combination that
would actually be restored to the car.** Method: read both files and the generator; the encoded `.json`
round-trips to the `.decoded.json` through the generator's own codec.

Both behave near-identically in everything I measured below (I carried them side by side throughout), so
this is a bookkeeping defect, not a safety one — but it is precisely the
"attribute the build from the tap, not the label" failure this kit has already paid for. **Pick one, and
make the brief, the toggle file, the checklist, the scorer's expected-params table and the artifact agree.**

`UseAutoSteerDelay` false is load-bearing and must stay in whichever wins:
`lagd.py:236` serves `SteerDelay` only when `use_custom_steerActuatorDelay` is true.

## 2. 🛑 `AccordFFRateGain` 1.0 puts the feedforward over the rail at low speed [EVIDENCE]

Replay of the rev-2 feedforward branch on **route 70's own recorded demand** (`cs_la_des`, `vego`,
`sa_deg` from the ident cache, 856 s laterally engaged). No plant model is needed: `angle_des` and its
filtered rate are reconstructable frame by frame.

| rate_gain | max &#124;ff&#124; below 8 m/s | P(&#124;ff&#124; > 0.95) | P(&#124;ff&#124; > 1.0) | roundabout cell P(>0.95) |
|---|---|---|---|---|
| **1.0 (package)** | **1.133** | 0.28 % | **0.22 % (0.34 s)** | **1.08 %** |
| 0.5 (fork default) | 0.807 | 0.00 % | 0.00 % | 0.00 % |
| 0.40 (ident §F3/§K) | 0.742 | 0.00 % | 0.00 % | 0.00 % |

Roundabout cell = laterally engaged, v < 10 m/s, &#124;angle&#124; > 40 deg: 39.7 s, angle p50 142 deg, max 393 deg.

The hold term has **no clamp at all** (only the move term is clipped, at 1.0–1.4). Hold alone reaches
1.0 at 126 deg at 12.5 m/s, 89 deg at 18.5, 78 deg at 22.8 — above the planner's own lat-accel ceiling at
those speeds, so it does not bind there; below 8 m/s it does, because the planner allows 400 deg.

The package's rationale — *"with the V293 tables 1/G IS the measured viscous term, so 1.0 is the
model-consistent value"* — is true for the plant's **steady** viscous term, but the move term is fed the
filtered derivative of a **planner-limited reference**, not the wheel's actual rate. At 3 m/s the
planner's ISO jerk limit permits 1098 deg/s of reference rate, worth 2.0 torque units through G = 550.
**Recommendation: 0.5.** It keeps most of the command dither the ident wanted from the rate term and
removes every rail event in the replay.

## 3. 🛑 The low-speed hold over-commands by ~2.4×, and route 70 bounds it TIGHTER than the ident CI does [EVIDENCE]

The ident's `a` at 1–8 m/s is unidentified (`b`'s interval crosses zero) and the tables were built on the
conservative 0.00168 at the 4 m/s knot. **Route 70 itself bounds it much lower.** Hands-off (pressed
False, ±0.5 s buffer), 0–5 m/s, 67.0 s:

```
top 0.2 % of angles:  |angle| 241.9 .. 251.0 deg      |u| p50 0.145  p95 0.160  max 0.163
implied bound          a <= (max|u| + F) / min|angle| = (0.163 + 0.012) / 251.0 = 0.00070 torque/deg
OLS |u| on |angle|     slope 0.00076, intercept 0.0478
```

against the fork table's **0.00169 / deg at 3 m/s** — an over-command of **×2.4**, and below the ident
CI's own low end (0.00089). At 5–8 m/s the same test gives 0.00241 against the table's 0.00201–0.00374,
i.e. the tables are right there. The physical story is the obvious one: at walking pace there is almost
no self-aligning moment.

**What that does, simulated** (fork chain transcribed line for line, plant = spring + viscous + Coulomb
0.012 + dead time, Honda ±0.03/frame limiter, PID anti-windup, 100 Hz). Planner-rate-limited entry:

| v | target | plant a | C0 flown peak | brief peak | file-r2 peak | rail (rev 2) |
|---|---|---|---|---|---|---|
| 4.5 | 100 deg | 0.00070 | 168 deg (+68 %) | **211 deg (+111 %)** | **208 deg (+108 %)** | 0.10–0.12 s |
| 4.5 | 100 deg | 0.00228 | 139 (+39 %) | 169 (+69 %) | 166 (+66 %) | 0.11–0.13 s |
| 3.0 | 100 deg | 0.00070 | 166 (+66 %) | 200 (+100 %) | 194 (+94 %) | 0.05–0.07 s |
| 6.0 | 200 deg | 0.00070 | 275 (+37 %) | 307 (+53 %) | 309 (+55 %) | 0 |

**Steady state is correct in every case** (settled angle / commanded angle = 1.000–1.003) — this is a
1–2 s transient over-steer, not a divergence, and it does not depend on which end of the CI is right.
On a gentler 2 s hand-shaped roundabout entry the gap shrinks to +6 % (266 deg against C0's 252 deg at a
220 deg target), so reality sits between the two. Cutting `AccordFFRateGain` to 0.40 takes the 4.5 m/s /
200 deg case from +53 % to +38 % and the rail from 0.34 s to 0.19 s.

**[BELIEF]** The right structural fix is a clamp on the HOLD term, or a lower 4 m/s `K_V` knot (0.93 →
~0.40 would match the 0.00070 bound). Neither is worth a code change before this drive; `AccordFFRateGain`
0.5 plus a named revert trigger covers it.

## 4. ⚠ Both configs roughly HALVE the controller's hold stiffness below 8 m/s [EVIDENCE]

`Kp_eff · A(v) / SteerLatAccel`, torque per degree of angle error:

| v | C0 flown | brief | file-r2 |
|---|---|---|---|
| 4.5 | 0.00803 | 0.00431 (−46 %) | 0.00378 (−53 %) |
| 11.96 | 0.00792 | 0.00554 (−30 %) | 0.00526 (−34 %) |
| 18.94 | 0.00856 | 0.00777 (−9 %) | 0.00779 (−9 %) |
| 22.80 | 0.00925 | 0.00927 (+0 %) | 0.00944 (+2 %) |

The design tables report this only at 18.9 / 22.8, where it is held. **If "loose" comes back, it will come
back below 8 m/s**, where it is halved. Put it in the checklist next to the roundabout item.

---

# ATTACKS THAT RETURNED CLEAN — stated, so the pass is not theatre

## 5. Loop margins: both configs beat the flown one under every plant model [EVIDENCE]

I built three plant models because the ident's own numbers disagree:

* **M_A** — `LAF_rep` flat gain + the M1 lag + dead time (what the design's `L(s)` used).
* **M_B** — DC gain `A/a` from the same joint fit the tables come from, pole `a/b`, residual dead time.
* **M_C** — M_B's DC gain and pole **plus the full measured dead time** (the pessimistic corner).

🛑 **The ident's `LAF_true` and its own spring `a` are inconsistent by 1.4–1.7× at speed.** One unit of
torque holds `1/a` degrees, and the controller's own angle→lat-accel conversion turns that into
`A/a` = 9.12 m/s² at 15–22 m/s, against the report's measured LAF of 5.39. The reconciliation is the plant
pole at `a/b` = 2.81 rad/s (0.45 Hz), which the 0.25–1.5 Hz IV fit absorbed into a lower flat gain (B2's
M1 collapsed to `T = 0`). **Anyone reusing 5.39 as a DC gain is understating the loop gain by 1.7×.**
`L(s)` was recomputed under all three; a correct encirclement test replaced the previous pass's
"PM 88 deg" artefact, which was the grid edge being reported as a crossover.

| band | model | C0 flown | brief | file-r2 |
|---|---|---|---|---|
| >22 | M_A | PM 112.3 / Ms 1.73 | PM 113.5 / Ms 1.74 | PM 113.6 / **Ms 1.76** |
| >22 | M_C | PM 115.6 / Ms 1.27 | PM 120.5 / Ms 1.26 | PM 119.6 / Ms 1.27 |
| 15–22 | M_A | PM 112.8 / Ms 1.79 | PM 111.9 / Ms 1.67 | PM 111.5 / Ms 1.67 |
| 3.0 m/s | M_A | **UNSTABLE** (PM −108.8) | PM 0.0, Ms 6590 | PM 16.5, Ms 8.26 |
| 4.5 m/s | M_A | PM 17.1 / Ms 7.90 | PM 78.6 / Ms 1.93 | PM 89.6 / **Ms 1.74** |

M_A reproduces the design's own Ms at >22 to within 0.08, so it is the same model. **The design's
`Ms ≤ 2 ⇒ SteerKP ≤ 0.92 at LAF 14` bound checks out**: I get Ms 1.76 at 0.85/LAF 14 and 2.01 at
0.85/LAF 12. Nothing here fails, and 3 m/s is the only cell any config struggles in — the flown one worst.

## 6. Friction relay: no limit cycle at any value from 0.0 to 0.012 [EVIDENCE]

Time-domain, 60–90 s, constant demand and disturbance-excited, at 3 / 4.5 / 8 / 12 / 18.9 / 22.8 m/s, with
the plant's own Coulomb at the CI HIGH end (0.0170) so the controller's relay fights a bigger real one.
Tail peak-to-peak **0.03–0.18 deg** in every cell, no 1–4 Hz content (rms 0.0005 deg, flat across the
whole friction sweep), dominant "frequency" = the analysis-window fundamental, i.e. drift, not a cycle.
The relay's linear half-width in raw error is `0.30/(1 + lsf/SteerKP)` = 0.030 m/s² at 4.5 m/s for
`SteerKP` 0.70 (0.035 for 0.85) against the flown 0.014 — **raising SteerKP widens the relay, which is the
right direction.** Agrees with the ident's describing function. **0.011 and 0.012 are both safe; I have no
evidence to prefer 0.008 or 0.005, and lowering it gives up the term that opposes the ratchet.**

## 7. No wind-up lurch [EVIDENCE]

Full-scale 0.25 Hz square-wave demand for 20 s (the worst the planner could ask), 3 / 5 / 10 m/s:

| | max &#124;i&#124;/LAF | largest unwind step | max &#124;Δu&#124;/frame |
|---|---|---|---|
| C0 flown | 0.136–0.167 | 0.0058 | 0.0300 |
| brief | 0.056–0.062 | 0.0037 | 0.0300 |
| file-r2 | 0.066–0.074 | 0.0046 | 0.0300 |

`freeze_integrator` fires on `steer_limited_by_safety` (the ±0.03/frame limiter clipping by >0.01),
`steeringPressed`, `v < 0.3` and `unwind_detected`, and the PID's own anti-windup clamps `i` whenever
`p + i + d + f` is outside `±LAF`. The feedforward enters through `f`, so the clamp sees it. Nothing
charges against a saturated feedforward. **Rev 2 is strictly better than the flown build here.**

## 8. Re-engagement is limiter-bound, not config-bound [EVIDENCE]

Inactive 3 s at 60 deg, then engage: first-frame `|u|` = **0.030 for every config** — the Honda
`STEER_DELTA_UP/DOWN = 3` at `DT_CTRL` caps the very first command, so 0.33 s to full scale whatever the
feedforward asks. The inactive branch primes `accord_prev_angle_des` with the same offset-corrected
curvature the active branch targets (`latcontrol_torque.py:257-263`), and with the offset now 0 the two
expressions are identical, so there is no `angle_des` step and no rate-term spike. Lane changes are a
non-issue at speed: the planner's jerk limit caps the reference rate at 31 deg/s at 20 m/s, worth 0.131
torque through G = 240.

## 9. Every parameter is inside its clamp [EVIDENCE]

`SteerLatAccel`'s ceiling is `CP.lateralTuning.torque.latAccelFactor × LAT_ACCEL_FACTOR_MAX_MULT`
= 1.68933 × 10 = **16.893**, so 14.0 passes at 83 % of it and 12.0 at 71 %. `SteerKP`'s is
`KP × STEER_KP_MAX_MULT` = 0.6 × 5 = 3.0. `AccordFFRateGain` ≤ 1.5, `AccordTorqueKi` ∈ [0.05, 1.0],
`AccordEpsGainScale` ∈ [0.5, 2.0], `AccordEpsSpringScale` ∈ [0.0, 2.0], `SteerFriction` ∈ [0, 1],
`SteerDelay` ∈ [0.01, 1.0]. All 15 keys exist in `common/params_keys.h`.

## 10. `KeepLearnedLatAccelOffset` 0 really does zero the offset, and will not cause a pull [EVIDENCE]

`controlsd.py:366-373`: with `use_custom_latAccelFactor` true (14 ≠ 1.69) and `keep_learned_offset` false,
the `lat_accel_offset = torque_params.latAccelOffsetFiltered` branch is skipped, so the offset stays at
the static `CP.lateralTuning.torque.latAccelOffset`, which `interfaces.py:389` sets to **0.0**.
`update_live_torque_params` is still called every frame because `use_custom_torque_params` is true.

**[EVIDENCE that it does something]**: route 70 measured `f = 0.866·D − 0.300`, which requires a live
learner offset, so `use_live_params` was true and the toggle will change the value.
**[EVIDENCE that it is not a pull]**: the offset shifts only the feedforward — the error is
`setpoint − measurement` and never sees it — so the closed-loop steady state is unchanged. It changes
which term carries the bias, moving ~0.30 m/s² of it off the integrator. If anything the engagement
transient gets smaller. ⚠ `torqued` keeps learning and `latAccelOffsetFiltered` keeps drifting with
nothing consuming it, so flipping the toggle back later would apply whatever it has accumulated at once.

## 11. No read-once parameter — but the compiled params library is a real hazard [EVIDENCE]

Galaxy's `_restore_toggle_values` ends with `update_starpilot_toggles()`, which sets
`StarPilotTogglesUpdated` in params_memory; `starpilot_process.py:420-434` picks that up and reloads the
toggles in a background thread while onroad (immediately while offroad) and re-broadcasts them on
`starpilotPlan`. `controlsd` and `lagd` both read the broadcast. **None of the 15 keys is consumed at
CarParams construction time** (`ForceTorqueController` is, but it is unchanged at 1).

🛑 **The real hazard is a stale `common/params_pyx.so`.** `known()` = `self.default_values.__contains__`;
if the compiled library does not know a key, `get_value` silently returns the DEFAULT. That would revert
**`AccordFFRateGain` → 0.5, `AccordTorqueKi` → 0.30, `KeepLearnedLatAccelOffset` → True,
`AccordEpsSpringScale`/`AccordEpsGainScale` → 1.0** with no error anywhere. Route 70 proves the `.so`
knows `AccordRatePlantFF` (the else-branch ran) and `AccordTorqueKi` (Ki_eff 3.317 = 0.15 × 22.1 at
1–8 m/s); it **cannot** prove it knows the other four, because all four were at their defaults.
The fork's own `docs/how-to/rebuild-params-on-device.md` has the check.

## 12. `AccordTurnFFTaper` is inert under the plant-FF branch [EVIDENCE]

`latcontrol_torque.py:493-494` scales `ff` before the friction is added at :553, and the plant branch
keeps only `ff − ff_before_friction`. The taper cancels. Pinning it to 0 is harmless bookkeeping, not a
control change.

## 13. The stale-fork failure mode, quantified [EVIDENCE]

Rev-2 config on a pre-`9622aee9f` image gets **both** terms wrong, in opposite directions:

| v | hold new | hold old | ratio | move/dps new | move/dps old | ratio |
|---|---|---|---|---|---|---|
| 5.0 | 0.00201 | 0.00165 | 0.82 | 0.00182 | 0.00833 | **4.58** |
| 12.5 | 0.00793 | 0.00368 | **0.46** | 0.00369 | 0.01053 | **2.85** |
| 22.8 | 0.01284 | 0.00600 | **0.47** | 0.00438 | 0.01273 | **2.91** |

Under-hold ×0.46–0.82 **and** an over-driven move term ×2.9–4.6 (old `G` = 120 against new 550 at 5 m/s),
which at `AccordFFRateGain` 1.0 would sit on the move clip constantly at low speed. That combination was
never scored by anyone. `9622aee9f` is now HEAD of `Dom` and the working tree is clean, so the exposure is
a device that has not pulled. **Gate it on the wire, not on trust.**

## 14. Two EXACT 100 Hz attribution gates, verified on route 70 [EVIDENCE]

| gate | expression | route 70 read | expected |
|---|---|---|---|
| `SteerLatAccel` | `-(p + i + f) / output` | median **6.0000**, IQR [6.0000, 6.0000], 99.2 % within 1 % | 14.0 (or 12.0) |
| `SteerKP` | `p / error` | median **0.3000**, 100 % within 1 % | 0.85 (or 0.70) |

(`pid_log.error` is already the lsf-inflated error, so the ratio is exactly `SteerKP`; `pid_log.output` is
`-output_torque` and `output_torque = (p+i+d+f)/LAF` with `d = 0`.)

🛑 **The old branch gate must be retired.** Under the plant-FF branch `f` is
`(plant_ff + friction)·LAF` and no longer tracks the demand at all, so `f/desiredLateralAccel` is
meaningless — it was already broken for a different reason (ident §A2). **New branch gate:** rebuild
`angle_des` from `desiredLateralAccel`, `vEgo` and the SR map, and regress `f/LAF` on it; the slope must
be the speed-dependent hold term (0.0079 at 12.5 m/s, 0.0114 at 18.9), and the intercept the friction.

---

## 15. The worst case this drive could produce, and how to see it in 30 s

**An over-steered entry into a roundabout, a slip road or a tight junction at 3–6 m/s**: the wheel goes to
roughly **twice** the angle the plan wanted, the torque rails for 0.1–0.3 s, and it comes back over
1–2 s. Reads as *"it dives into the corner and then catches itself"* — the operator's **darty** trigger.
Route 70 carries 39.7 s of exactly that cell, so the first roundabout will exercise it.

Second, weaker: **loose at low speed**, because the controller's hold stiffness there is halved (§4). Not
on a straight — straight-line and motorway behaviour should be unremarkable, and steady-state tracking is
correct at every speed in the simulation. **A darty straight would be a different fault, not this one.**

**Checklist items this pass produces**
1. Decide brief-vs-file; regenerate the toggle config; make every document agree (§1).
2. `AccordFFRateGain` 1.0 → **0.5** (§2).
3. Before the drive: confirm the device is on `Dom` ≥ `9622aee9f` **and** that the compiled params
   library knows `AccordFFRateGain`, `AccordEpsSpringScale`, `AccordEpsGainScale`,
   `KeepLearnedLatAccelOffset` (§11, §13).
4. First 60 s of engaged driving: read `-(p+i+f)/output` and `p/error` and check both against the config
   before scoring anything else (§14).
5. Revert triggers, in the operator's words: **over-steer into a low-speed turn** (§3, §15), and
   **loose below 8 m/s** (§4). Not "loose at speed" — that is held or slightly improved.
