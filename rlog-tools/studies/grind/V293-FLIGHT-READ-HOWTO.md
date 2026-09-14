# V293 FLIGHT READ — how to score a drive

**One command.** Everything below is what it prints and what each line means.

**v2, 2026-09-13.** Three things changed, each because v1 would have given a wrong answer on the next
drive:

1. **The expected fork config is read from a file** (`--config`), not hard-coded, so a revised toggle
   config is scored against itself. Everything downstream that depends on a config value — the expected
   `SteerKP`, the expected `SteerLatAccel`, which feedforward arm should be live — now reads from that
   file too. §0.
2. **The `branch` gate was replaced.** v1's `median f/desiredLateralAccel ≥ 0.75` was broken as written
   and **failed a correctly-attributed drive**; the replacement reads `torqueState.f` against
   `starpilotLateralState.feedforward` and re-derives the fork's own f-formula on the wire. §0.
3. **Section 7 is new** — the operator's four symptoms as pre-registered instruments, with every
   reference column re-derived at run time and its own positive control. §7.
4. **Two more attribution gates**: `latAccelFactor` (an exact 100 Hz read of the authority scalar that
   works in **both** feedforward arms) and `fork commit` (rev 2's scales are 1.0 only because the plant
   tables moved into fork code). §0.

```
python rlog-tools/studies/grind/v293_flight_read.py <route id>
```

`<route id>` is the full comma route (`75604b0a432fdc89_00000070--abc123…`), a bare route counter, or a
cache tag that already exists. If the route is not in the v280 cache yet the script **extracts it first**
— the decode is copied verbatim from `extract_v292_routes.py`, and it was checked against the record: on
`75604b0a432fdc89_0000006f--d876c761bc` it reproduced `r6f_v292.npz` and `r6f_v292_b4.npz`
**byte-identically, every array**. So a route this tool extracts is readable by every other census tool
with the same yardstick.

Other flags: `--config` (the expected fork toggle config — see §0) · `--build V282|V292|V293|V281r3`
(which image's cells to score against — defaults to V293, or to a known route's own build) · `--tag`
(cache tag to write) · `--reextract` · `--no-positive` (skips the positive control, saves a few seconds) ·
`--no-symptoms` (skips section 7) · `--refresh-symptom-refs` (recompute section 7's reference routes) ·
`--controls` (see the last section).

Runtime is dominated by one thing: the presence predicate runs the record's 4096-point prominence
spectrum per 2 s window, about **1 s per 10 s of engaged time**. A 10-minute drive scores in 2–3 minutes.
That call is deliberately not optimised — every published presence number in the corpus came out of it,
and a faster spectral floor would silently move the comparison.

The first run also builds two caches that later runs reuse: a **control-path cache** per route
(`_scratch/cs_<tag>.npz`, one rlog pass) and the **section 7 reference table**
(`_scratch/v293_symptom_refs.json`). Budget a few extra minutes once; after that they are free.

---

## What the scorecard says, section by section

### 0. Exposure and the fork toggles — is the drive attributable at all?

**The fork side is a toggle config, not code** (2026-09-13, the operator's call — the preset param and the
Testing Ground 9 slot that preceded it were both undone; Dom `4247cb09e` carries nothing torque-mode-specific).

🛑 **The expected config is READ FROM A FILE, not baked into the script** (v2, 2026-09-13).

```
--config analysis-2020accord/reference/<name>.decoded.json
```

Default: `toggle-config_V293_torque_mode_r2.decoded.json` if it exists, else the rev-1
`toggle-config_V293_torque_mode.decoded.json`. **v1 hard-coded the rev-1 torque-mode values**, so the very
next drive — a revised config on the same firmware — would have been scored against the wrong expectation
and reported a bogus `toggle` FAIL. The file the scorer reads is the same artefact the operator restores
through Galaxy, so the two cannot drift.

**Rev 2, the current default** — 15 keys, on fork commit **9622aee9f**:

| | | | |
|---|---|---|---|
| `AccordRatePlantFF` **true** | `AccordEpsSpringScale` 1.0 | `AccordEpsGainScale` 1.0 | `AccordFFRateGain` 0.5 |
| `SteerFriction` 0.011 | `SteerLatAccel` 14.0 | `SteerKP` 0.85 | `AccordTorqueKi` 0.3 |
| `KeepLearnedLatAccelOffset` **false** | `SteerDelay` 0.2 | `UseAutoSteerDelay` false | `AccordTurnFFTaper` false |
| `ForceAutoTuneOff` true | `ForceAutoTune` false | `AdvancedLateralTune` true | |

Three of those change what other gates expect, and all three now read from the file: the **branch** gate
flips to expecting the plant-FF arm, the **kp** gate expects 0.85, and the **latAccelFactor** gate expects
14.0. The spring and gain scales are 1.0 because the correction moved into fork code — see the `fork
commit` gate below.

Two rules the gate applies to `initData.params`:

- an `Accord*` key **absent** from the store reads as its **`params_keys.h` declared default** (a params
  rebuild drops default-valued keys — measured on r6f). The defaults table is transcribed from
  `docs/research/FORK-LATERAL-PATH-V293-2026-09-13.md` §5. `SteerKP`, `SteerFriction`, `SteerLatAccel`,
  `SteerDelay` and `SteerRatio` are deliberately **not** in it: their declared defaults are
  platform-derived, so absence is genuinely ambiguous and must read as a MISMATCH rather than resolve to
  a guess.
- a key this cache **never captured** reads as `NOT CAPTURED`, which is a different thing from absent and
  is also a FAIL. The params dump records the key list it was written with, and the `fork_toggles` cache
  filename carries a hash of that list, so adding a key forces a re-read instead of silently serving a
  dump that never held it.

| reading | source | role |
|---|---|---|
| the config, key by key | `initData.params` (logged once, at process start) | **GATE `toggle`**: every key in the config file must match. |
| `Kp` at 100 Hz | `controlsState…torqueState`: median `p / error` | **GATE `kp`**: the fork logs `pid_log.error = error_with_lsf` and calls `pid.update(pid_log.error, …)`, whose `p = k_p · error`, so the ratio IS the `SteerKP` toggle on every active frame. The expected value comes **from the config file** (0.3 for rev 1, 0.85 for rev 2), never a constant. Measured on r6f_v292: **0.9000 over 42 905 frames, IQR [0.9000, 0.9000], 100 % within 5 %** — the installed tune, read exactly. This survives a mid-route toggle change; `initData` does not. |
| `latAccelFactor` at 100 Hz | `controlsState…torqueState`: median `−(p + i + f) / output` | **GATE `latAccelFactor`** — see below. Works in **both** feedforward arms. |
| the feedforward **branch** | `torqueState.f` vs `starpilotLateralState.feedforward`, plus the f-formula | **GATE `branch`** — see below. Replaces v1's broken `f/D` ratio. |
| the fork **commit** | `initData.gitCommit` | **GATE `fork commit`** — see below. The rev-2 config's scales only mean what they say on the code that carries the replaced plant tables. |
| Testing Ground slot / variant | `customReserved9` | **informational** — no slot is the torque mode; shown for the record (r6f: slot 1 / A, "ACC Bolt Long Tune"). |

#### The `latAccelFactor` identity — the one attribution read that works in both arms

```
output_torque      = output_lataccel / latAccelFactor
output_lataccel    = f + p + i + d          d is structurally 0 on this car
torqueState.output = −output_torque
⇒  −(p + i + f) / output  ==  SteerLatAccel   on every active frame, exactly
```

It holds whichever feedforward arm ran, because `pid_log.f = pid.f` in each. That makes it a wire read
of the **authority scalar** — the number that divides P, I *and* the feedforward together — which no
other gate covers. **Verified on r70_v293: median 6.0000, IQR [6.0000, 6.0000], 99.2 % of active frames
within 1 %.** The expected value is the config file's `SteerLatAccel` (6.0 for rev 1, **14.0** for
rev 2). PASS needs the median within **2 %** and **≥ 95 %** of active frames within 5 %; the median,
IQR and both fractions are printed. Frames where `|output| < 1e-3` are dropped — the ratio is 0/0
there — and the guard is on the denominator only, so it cannot bias the estimate.

#### The `fork commit` gate — why rev 2's scales are 1.0

🛑 **The rev-2 config sets `AccordEpsSpringScale` 1.0 and `AccordEpsGainScale` 1.0 not because no
correction is wanted, but because the correction moved into fork code.**
`HONDA_ACCORD_EPS_G_V` → `[550, 271, 246, 167]` and `_K_V` → `[0.93, 1.64, 2.15, 2.77, 3.15]` were
replaced on Dom at **9622aee9f**. Fly the rev-2 config on **4247cb09e** and those scales multiply the
*old* tables — the plant feedforward the identification measured as 1.4–2.6× too small — and **every
other gate would pass a silently wrong drive**.

The rlog cannot read the tables, only the commit, so this is a **commit check** and says so on the
page: `GitCommit` must be 9622aee9f and must not be 4247cb09e. A third commit reads REPORT, not PASS —
the tables cannot be verified from the log and the fork tree has to be checked by hand.

**What is deliberately NOT scored, and why.** A row regressing `f / SteerLatAccel` on
`angle_des · (k/G)(v)` would confirm `AccordEpsSpringScale` on the wire under the plant-FF arm. It is not
implemented, because `angle_des` is not logged: recovering it from `desiredLateralAccel` needs the fork's
vehicle model inverted, and two pieces of that are not pinned here — the understeer constant `chi` in
`curvature_factor = (1−chi)/(1−sf·u²)/l`, and the fact that the Accord steer-ratio map is **angle-indexed**,
so the inversion is a fixed point rather than a division. Building that chain on assumptions would produce
a number that looks like evidence and is not. The `branch` gate already establishes that the plant arm ran,
the `latAccelFactor` gate establishes the authority scalar, and the `toggle` gate reads the scale itself
out of `initData` — so the missing row is confirmatory, not load-bearing. If it is ever wanted, the honest
route is to invert the angle→lat-accel map **empirically** from each route's own logged
(`carState.steeringAngleDeg`, `torqueState.actualLateralAccel`) pairs, binned by speed *and* angle so the
steer-ratio nonlinearity is carried rather than assumed.

#### 🛑 Why the old `f / desiredLateralAccel ≥ 0.75` gate was wrong

It is worth stating in full, because it **failed a correctly-attributed drive**. The gate asserted
"friction 0 ⇒ `f` = `desiredLateralAccel` exactly". The fork does not compute those two from each other:

```
pid_log.desiredLateralAccel = setpoint  = expected_lateral_accel + jerk · lat_delay
pid_log.f                   = ff        = D_future − roll·9.81·fade − latAccelOffset·fade
D_future                                = desiredCurvature · vEgo²
```

One is the **0.30 s delayed reference plus a jerk lead**; the other is the **current command minus a
constant**. So

```
f / D  =  1 − c/|D|      by construction
```

and the whole 0.56 → 0.87 ramp across `|D|` bins that v1 reported is that one additive constant `c`. A
ratio that **rises with magnitude** is the signature of an **additive** term; a branch change is
**multiplicative** and would show a **flat** ratio. v1 was gating on a stale learned offset and calling it
a mis-attribution. `f` never sees `setpoint`.

#### What replaced it — two independent reads, neither touching the delayed setpoint

**(a) `torqueState.f` against `starpilotLateralState.feedforward`.** Both are published in the same
`Controls.publish` call, so they align index-for-index. The statistic is `median |f − feedforward|`
normalised by `median |f|`, so it does not depend on how hard the drive was steering.

- **EVIDENCE**: they are the *same number* in the else arm and differ by ~3.3× relative under the
  plant-FF arm. That is the whole of what the gate needs, and it is measured on five routes.
- **BELIEF**: *which* field holds which quantity under the plant-FF arm. The sizes are consistent with
  `feedforward` carrying the generic lat-accel term (|·| 0.372 on r6f, against 0.366 on r70 where the two
  agree) and `f` carrying the live branch's output (|·| 0.113, the size the fork's own hold-torque table
  predicts) — but that mapping was **not** read out of the fork source and nothing in the gate depends on
  it.

**Measured calibration, 2026-09-13, this estimator on five cached routes:**

| arm | routes | `median |f − feedforward| / median |f|` |
|---|---|---|
| **else** (`AccordRatePlantFF` = 0) | r70_v293 · r39 · r35 | **0.0000 · 0.0000 · 0.0000** |
| **plant FF** (`AccordRatePlantFF` = 1) | r6f_v292 · r6c | **3.3246 · 3.3706** |

The statistic is **bimodal with nothing in between**. The gate sits at **0.10 relative** (absolute guard
0.02 m/s²) — thirty times above the else side and thirty times below the plant side. The *failing* route
is r6f_v292 and the *passing* route is r70_v293, so the threshold is bracketed on both sides by real data.

🛑 **The gate's polarity follows the config.** Rev 1 asked for the else arm; the rev-2 config asks for the
plant-FF arm. A gate hard-wired to "the else arm must be live" would fail the next drive for doing exactly
what it was told. The scorer reads `AccordRatePlantFF` from the config file and expects the matching arm.

**(b) The f-slope.** Regress `f` on `D_future`, and — when `liveParameters.roll` is available — on the
roll term too:

```
f  ~  1.000 · D_future  −  9.81 · roll·fade  −  latAccelOffset · fade
```

In the else arm those three coefficients are exact. **Measured on r70_v293: 0.99992 / −9.8091 / −0.06865
at R² 0.999979, residual rms 0.0024 m/s².** The fork's own formula, confirmed on the wire to machine
precision. On r6f_v292 (plant arm) the same fit reads 0.5337 / −0.803 / +0.0196 at R² 0.192 — it does not
close, which is the point. The two-term version (no roll) reads slope **0.866** on r70 and is printed
beside it as context only.

#### 🛑 A correction to the record: the ~0.30 m/s² subtraction is mostly ROLL, not the learned offset

`V293-PLANT-IDENT-2026-09-13.md` §G1 read the median `D_future − f` of **+0.343 m/s²** as a stale learned
`latAccelOffset` inherited from the V282 tune, and recommended clearing it. The three-term fit **separates
the two terms**, and on r70 they split:

| term | median contribution to `D_future − f` |
|---|---|
| `9.81 · roll · fade` | **+0.408 m/s²** (`liveParameters.roll` median **+0.0423 rad = +2.42°**) |
| `latAccelOffset · fade` | **−0.069 m/s²** |

The fitted offset (−0.06865) matches the **published** `liveTorqueParameters.latAccelOffsetFiltered`
median (−0.06863) **to four decimals**, which is what makes the decomposition evidence rather than a fit.
So **clearing the learned offset removes about a fifth of that subtraction, not all of it.** A persistent
multi-degree roll estimate is a device-levelling or camber question and `KeepLearnedLatAccelOffset` does
not touch it. *(EVIDENCE for the split; BELIEF as to which of levelling or camber it is — this drive
cannot separate them.)*

The scorer therefore prints **two different offsets** and says which one acts:

- **published** — `liveTorqueParameters.latAccelOffsetFiltered` at 4 Hz. `torqued` publishes this whatever
  the toggle says.
- **effective** — the `fade` coefficient of the three-term fit. `KeepLearnedLatAccelOffset` decides whether
  controlsd *takes* the published value, so the effective one is the gate.

Both terms are also printed as their own **REPORT rows** in the verdict block — `roll term` carries the
median of `roll·g·fade` plus `liveParameters.roll` in radians and degrees, and `learned offset` carries the
median of `latAccelOffset·fade` beside the published `latAccelOffsetFiltered` and its `liveValid` duty — so
the next drive carries the split forward rather than re-deriving it. On r70 `liveValid` was true on
**0.00** of frames, i.e. the published offset is a restored cached value that was never re-validated on
that drive.

When the config asks for `KeepLearnedLatAccelOffset` = 0, the effective offset must read **|·| ≤ 0.02 m/s²**.
Calibration: r70_v293 reads −0.0687 with the toggle at 1 and would **fail**; r35 published exactly 0.00000
and its fitted value (+0.0127, inside its own 0.038 residual) would **pass**. The gate is only applied when
the else-arm identity closes (R² ≥ 0.95); under the plant-FF arm the effective offset is not identifiable
from the log and the row is REPORT.

🛑 **Two cereal schema collisions, and the informational row needs a patch.** The kit declares union slot
`@137` as `epsTelemetry :Custom.EpsTelemetry` and `@116` as `modelDataV2SP :Custom.ModelDataV2SP`. The
fork declares the *same two slots with the same two struct ids* as `starpilotLateralState
:Custom.StarPilotLateralState` (`0xc2243c65e0340384`, eight floats/bools) and `customReserved9
:Custom.CustomReserved9` (`0xa1680744031fdb2d`, six Text/UInt64 fields carrying the Testing Ground
selection). This script builds a **patched copy** of the schema under `_scratch/cereal_fork/` (rebuilt
automatically when the patched structs change) and loads it with `capnp.load()`; the kit's own schema is
never modified. **Any other kit script that reads `epsTelemetry` or `modelDataV2SP` from a 2026-09 rlog is
reading garbage.** The three gates do not need the patch — `initData` and `torqueState` are stock schema.

The `f/D` ratio deserves its own note, because the obvious statistic does not work. Under the torque config
friction is 0, so `f = desiredLateralAccel` exactly and the ratio is `1.000`; the rate-plant branch
scales it down. Measured pooled medians on four routes that are **not** torque mode: r6c 0.32, r6d 0.24,
r6e 0.40, r6f 0.31, worst single `|D|` band 0.58. The gate at 0.75 sits about 1.3× above the worst
observation and 1.3× below the expected 1.000. **The whole-route regression slope of f on D is not usable
as a gate** — it reads 0.21–0.64 on those same four routes. The ratio is the statistic; the slope is
printed only as context.

If the config reads as the installed tune with V293 in the ECU, the band scores below are **not a build
contrast** and the mismatch is the feedforward-starved *and* high-gain-feedback state, which is not merely
sluggish (`ADV-V293-D` §4.4). Restore `toggle-config_V293_torque_mode.json` and restart openpilot before
reading anything else.

### 1. The edit-live identity — the control that decides attribution

`|427 tap|` regressed on `f(cmd)·fade`, on every laterally engaged frame, with cells read little-endian
from the **built image**. With `0xC62E6 = 0` the delivered torque is an exact function of the demand index
and the fade and carries **no wheel-rate term** — so this regression is the on-wire test of whether the
loop is actually open.

**The estimator has zero free parameters.** No fitted scale, no offset. R² → 1 therefore means *the bytes
predict the wire*, not merely that the two correlate. Pearson r is printed beside it to separate a scale
error (high r, failing R²) from a structural one (low r). The tap is read at its **native 50 Hz** and the
predictor is ZOH-sampled onto it; the transport lag is scanned −40…+120 ms and the best row reported.

Three fade readings are scored because **the axis unit of `0xCBBC4` is open** (`ADV-V293-A` erratum): the
record indexes it by `|bar| >> 5`, adversary A read it as km/h. With the loop open the tap *is* the
surface, so **whichever reading wins on R² is evidence for which axis is right** — the drive can settle
the question the adversarial pass left open.

**⚠ Polarity.** Measured on the wire, `sign(T) = +sign(cmd)`. The pre-registration's phrase
*"sign(T) = −sign(cmd)"* is the opposite convention and that column reads ~0.15 on V282, not ~1.00. The
column that must approach 1.00 is `sgn=sgn(pred)`. Both are printed so the reading cannot be taken the
wrong way round.

**The gate and the yardstick behind it:**

| | value |
|---|---|
| pass gate | R² ≥ 0.50 and residual ≤ 2.5× this route's own positive control |
| estimator ceiling, real data | +0.964 |
| estimator floor, six non-V293 routes | −0.011 |

The residual gate is relative on purpose: it self-calibrates for the route's exposure, its demand-index
range and the tap's 8-count quantiser. The absolute 150-count fallback applies only when the positive
control is skipped.

**Positive control**, printed inline: a V293 tap synthesised from *this* route's own recorded command by
the byte-exact 1 kHz march (`Elec` with the feedback clamped to ±0), decimated to 50 Hz and quantised,
then regressed by the same estimator. It reads R² ≈ 0.92–0.96. **Not a tautology** — the predictor is the
steady-state surface and the synthetic tap is dynamic. If it comes back below 0.8 the estimator is
impaired on that route and the identity row must be read with that in mind.

### 2. The 18–22 Hz ring — the drive-controlled measure

Two numbers, both against `r6c` (the nearest-in-time V282 reference), with `r39` printed beside it.

- **engaged ÷ the same route's lateral-disengaged amplitude.** With `STEER_REQUEST` = 0 the rate loop is
  open, so this is how much the engaged loop adds over that route's own input. The disengaged reference is
  mostly **stationary** on every route, so it is like-for-like between builds but is not a road
  normalisation.
- **present-window ring amplitude** — the record's own predicate, unchanged: 2 s windows on a 0.5 s grid,
  present = 18–22 Hz prominence ≥ 8 **on the driver-torque bar** and bar amplitude ≥ 40. The predicate
  reads the bar, not the EPS torque, so the torque-map edit cannot move it directly.

**This second number carries the clause: ≤ 0.40× of V282's.** Below 10 present windows the ratio is
reported but not treated as decisive — that is an exposure limit, not a build result.

### 3. The 6–9 Hz strong-turn ripple — the operator's "stutter" channel

Three gates, all on the record's own thresholds and detectors:

| gate | threshold | source |
|---|---|---|
| F7 per 100 s of engaged high-angle time | ≥ 2 → REVERT | fixed 103-wire detector, `|angle| ≥ 30` and fdom ≥ 6 |
| tap ripple ÷ level, loaded turns | ≥ 0.25 → REVERT | `stutter_v283` §C |
| **absolute** 6–8.5 Hz tap ripple ÷ V282's | ≥ 1.5 → REVERT | DESIGN §6.3's symmetric sentence |

The absolute ripple is scored separately because torque mode grows the **denominator** ×1.2–3.6, so a
falling ratio can hide a rising ripple.

The 5–9 Hz wheel band is reported, not gated: a **broadband** ×1.5 rise is predicted (the servo's
disturbance rejection is what V293 removes), a **resonant line** is not. Read the band amplitude against
the line table in section 5 to tell them apart. ⚠ The `|angle| ≥ 30` hands-light stratum that B5 names
literally is **empty on all six reference routes** — under 3 s of runs ≥ 1 s. The populated column is the
6–8.5 Hz wheel rate on the same loaded-turn windows as the ripple.

### 4. The outer loop — the V276 1–4 Hz signature

🛑 **Coherence is not the discriminator.** It reads 0.88–1.00 at 1–4 Hz on every route in the corpus,
V282 and V292 alike, because openpilot commands there and the car follows. What separates a limit cycle
from ordinary tracking is the **angle amplitude** at 1–4 Hz against the V282/V281r3 references in the same
speed band. Coherence is kept as a guard: a rise with low coherence is road input, not the loop.

Speed bands are printed low first. The orchestrator's adjudication of clause B6 named the ~5 m/s creep
margin as the thinnest on **both** builds, and the failure mode there is exactly this signature. It is the
first revert trigger, and the fix if it fires is the fork preset, not the firmware — but the drive stops.

### 5. The other bands

13–17 Hz carries the prereg's B7 gate at ×1.5 of V282's, scored on **hands-off 8–15 m/s** — the stratum
the record headlined V292's rejected ×1.81–1.85 on. Hands-off all speeds is printed beside it because the
8–15 band can be thin on a short drive. 22–30 Hz is reported, not gated. The line table gives the peak of
the excess-dB spectrum in four search bands, so a narrow line can be told from a broadband rise.

### 6. The 0x14A cave duties

`b4` = sign(r24) is the **negative control** — it cannot depend on the delivered torque, so a large move
means something other than the intended cal changed. `b7` = sign of the LKAS summand is the pre-registered
mover. `b5`/`b6` are not pre-registered. `b0`–`b2` are stock Honda and read 1.000 on every build.

🛑 **Do not compare the pre-registered 0.996 → 0.808 with these rows.** Those were computed on r39's ten
loudest one-direction turn windows, where the summand's sign is pinned by the turn. Whole-route, V282
measures b7 0.507–0.548 and b4 0.394–0.404. The scorecard prints those measured rows and the b4 clause
uses them.

### 7. The operator's four symptoms

New in v2. The operator's verbatim score of the rev-1 flight was:

> "I did not experience any classic grinding or stuttering."
> "steering felt **ratchety**, like the wheel did not move smoothly but only **snapped between angles**
> rather than smoothly moving between them"
> "Sometimes steering felt **loose** and then sometimes there was **oversteer** and other times on hard
> transients, it would **overshoot then correct** slightly"

Section 7 turns each of those four words into a pre-registered instrument. The definitions live in
`rlog-tools/studies/grind/v293_symptom_instruments.py` — pure functions, no I/O — ported from the
identification subagent's own scripts so the numbers are the ones already in the record.

🛑 **Every reference column is re-derived by that code at run time** on the cached routes
(`r70_v293`, `r6c`, `r39`, `r35`), never copied from `V293-PLANT-IDENT-2026-09-13.md`. The reference
cache under `_scratch/v293_symptom_refs.json` is keyed by a **hash of the instrument source**, so
changing any definition invalidates every reference instead of comparing a new estimator against old
numbers. `r70_v293` is a reference column in its own right: every future drive is read against the
rev-1 flight the operator actually scored.

The control-path instruments need `controlsState`, `starpilotLateralState`, `liveTorqueParameters` and
`liveParameters`, none of which are in the v280 cache. The scorer builds a **second, separate cache** per
route (`_scratch/cs_<tag>.npz`, one rlog pass, never touching the v280 one). A route with no rlogs on
disk gets the CAN-only instruments and says so. The route counter was reset on this dongle, so two routes
can share a counter (`r35` and `r6f` both do); the prefix is disambiguated against the v280 cache's own
duration rather than guessed.

**Two hands-off masks, and they are not interchangeable.** The ratchet statistics use engaged-and-not-
pressed with a **±0.5 s buffer** (`v293_ident_k.py`); every control-path instrument uses engaged-and-not-
pressed with **no buffer** (`v293_ident_i.py` / `_c.py`). Swapping them moves the step-event count 29 → 23
and the 8–15 m/s tracking gain 0.884 → 0.808. Both sides reproduce their source exactly, which is why the
split is kept rather than reconciled.

#### 7.1 Ratchet — "snapped between angles"

Two instruments.

**Dwells per minute.** A dwell is the **0.10 s moving mean** of `|0x18F rate|` below a threshold for
≥ 0.20 s, inside a stratum run of at least 2 s. 🛑 A hard threshold on the raw 100 Hz field is a
**documented artefact**: it finds 13 dwells on r70 and **zero** on r6c. The smoothed detector is applied
identically to every route. All-engaged on every route — the driver-torque bar cannot stand in for
`steeringPressed` on this car (at `|bar| < 800` it catches 98.2 % of hands-off frames and 0.1 % of
hands-on ones), so r70's hands-off stratum is printed beside the all-engaged one rather than instead of
it. Dwell duration p90 and snap p90 at the 0.5 deg/s threshold come with it: the median snap is the same
on both builds, what differs is **how long the wheel sits still first**.

| dwells/min, th 0.25 | 0–5 | 5–10 | 10–20 | >20 |
|---|---|---|---|---|
| r70_v293 (all engaged) | **15.23** | **7.66** | **4.56** | **1.24** |
| r70_v293 (hands-off) | 20.97 | 8.08 | 5.26 | 1.27 |
| r6c (V282) | 0.39 | 0.64 | 0.44 | 0.20 |
| r39 (V282) | 0.38 | 0.00 | 0.84 | 0.00 |
| r35 (V281r3) | 0.51 | 0.00 | 0.88 | 0.51 |

**Pre-registered: PASS if ≤ 3× r6c's in every band with ≥ 60 s of exposure.** Calibration: r70_v293
**fails in all four bands**; r39 and r35 **pass**. Bracketed on both sides.

**Rate-magnitude concentration.** "Of all the wheel travel in a 4 s window, what share is delivered in the
fastest 10 % of its frames?" Windows are binned by their **own** rms wheel rate, because r70's rms rate is
2–3× the references' in the same speed band (roundabouts) and a raw comparison would not be like-for-like.
Read on the **rate** field, not the angle, which the 0.1 deg quantiser cannot resolve below ~10 deg/s.
The bin edges are **frozen** at the pooled four-route percentiles (1.358 / 2.195 / 3.965 / 10.099 deg/s) so
the instrument is per-route and cacheable; `v293_ident_h2.py` recomputed them from whatever routes were in
the run. Calibration is **recomputed on synthetic signals every run** and printed: a pure sine **0.157**,
0–2 Hz band-limited noise **0.278**, a 10-step staircase **1.000**.

| q75–90 bin | r70_v293 | r6c | r39 | r35 |
|---|---|---|---|---|
| rate | **0.468** | 0.345 | 0.325 | 0.351 |
| 0xE4 command | 0.440 | 0.391 | 0.393 | 0.392 |

**Pre-registered: PASS if ≤ 0.40.** r70 fails, all three references pass. The command row is the control
that matters: on r70 the command got *smoother* (its per-frame step is 2.9× smaller than V282's) while the
wheel got snappier, which is what makes the car the culprit rather than openpilot.

#### 7.2 Loose — stiffness, not wander

⚠ **"Loose" is not excess wander.** r70's 0.1–1 Hz angle wander on straights was *lower* than V282's
(0.137 / 0.141 / 0.229 deg against r6c's 0.207 / 0.207 / 0.209). That is a measured **null** and is
REPORT-only.

What is low is the **outer loop's stiffness** — the command it puts up per degree of angle error on
straights, in openpilot torque units — beside the **plant's own return spring** from the identification's
joint fit:

| band | r70 loop stiffness | plant spring | ratio |
|---|---|---|---|
| 0–5 | 0.00319 | 0.00228 | 1.40 |
| 5–10 | 0.00654 | 0.00600 | 1.09 |
| 10–20 | 0.01283 | 0.01149 | 1.12 |
| >20 | 0.02269 | 0.01539 | 1.47 |

The loop is barely stiffer than the car's own return spring below 20 m/s, so a disturbance moves the
wheel about as far as the loop then pulls it back — and on a straight the feedforward is nearly zero, so
almost nothing else is holding it. REPORT, no numeric pre-registration.

#### 7.3 Oversteer

**Turn-hold windows ≥ 1.5 s**, `|D| > 0.5` with `|dD/dt| < 0.3`: mean|actual| ÷ mean|desired| lateral
accel, per speed band and per `|D|` bin. r70 read **0.937** at 10–20 and **1.093** at >20; r6c read 1.004
and 0.995. **Pre-registered: the >20 m/s ratio ≤ 1.04.** r70 fails, r6c passes — bracketed.

**Tracking gain** — slope of actual on desired lateral accel, both low-passed at 0.5 Hz, over engaged runs
≥ 10 s. 🛑 **On the identification's band grid** (<8 / 8–15 / 15–22 / >22 m/s), because that is where the
reference lives; every other table in section 7 is on 0–5 / 5–10 / 10–20 / >20.

| tracking gain | <8 | 8–15 | 15–22 | >22 |
|---|---|---|---|---|
| r70_v293 | – | **0.884** | **1.020** | **1.123** |
| r6c | 0.966 | 0.968 | 0.996 | 0.989 |

r70 rises monotonically with speed: **under-turning below 15 m/s, over-turning above 22** — the
feedforward's missing speed law, seen directly in the closed loop, and the cleanest single number a
feedforward fix has to flatten. **Pre-registered: within 0.95–1.05 in every band with ≥ 60 s.** r70 fails
(>22 reads 1.123), r6c passes all four — bracketed.

#### 7.4 Overshoot-then-correct

A step is `|Δ desiredLateralAccel| ≥ 0.30 m/s²` over 0.5 s on a hands-off frame, ≥ 2.5 s from the last, with
`|dD/dt| ≤ 1.2` over the next 1.2 s and the stratum held for 2.0 s. Overshoot is
`(peak|actual| − |final desired|) / |final desired|` over the following 2 s.

| relative overshoot | 5–10 | 10–20 | >20 |
|---|---|---|---|
| r70_v293 (29 events) | 0.166 | **0.437** | **0.341** |
| r6c (102 events) | 0.095 | 0.226 | 0.183 |

**Pre-registered: ≤ 0.20 at 10–20 and >20.** r70 fails both. 🛑 **No route in the corpus passes this at
10–20 m/s** (r6c's 0.226 is the closest), so it is a **target**, not a bracketed threshold — a FAIL means
"not yet at the target", not "worse than V282". The census in §7.7 says so explicitly.

**The discriminator travels with it.** Absolute overshoot regressed on step size: a linear under-damped
loop gives a positive slope and ~0 intercept; a stiction release or a fixed feedforward offset gives slope
~0 and a positive intercept. On r70 that reads **slope −0.456, intercept +0.571, R² 0.027**, with the
correlation to the integrator at the peak only **+0.172**. A roughly fixed ~0.4–0.5 m/s² excursion that
does not scale — which **rules out an under-damped linear loop** and rules out wind-up.

#### 7.5 Report rows

- **1–4 Hz prominence**, the peak above a straight line fitted **in log-log to the 0.6–0.9 and 4–7 Hz
  shoulders**. 🛑 A flat baseline over 0.5–8 Hz scores the steering spectrum's own 1/f slope as a peak and
  returns 16–21 dB on *every* route; that estimator is wrong and is not used. r70 reads
  **6.51 / 11.78 / 7.65 / 3.08 dB** against r6c −2.32…+2.19, r39 −0.27…+2.21, r35 +0.61…+1.91.
- **1–4 Hz content on the rate field**, which the angle quantiser cannot reach: r70
  **59.1 / 23.0 / 8.2 / 2.3 deg/s** against r6c 5.1 / 4.8 / 1.1 / 0.49.
  **Pre-registered: prominence < 3 dB everywhere and rate content ≤ 2× r6c's.** The prominence clause is
  bracketed (all three references pass); the rate clause is measured against r6c itself, so only r6c
  passes it trivially.
- **Integrator share** of `|f|+|p|+|i|`, on the identification's band grid. r70 0.350 / 0.348 / 0.382 /
  0.384. **Pre-registered < 0.20** — a **target**: r6c reads 0.30–0.40 and no route passes. It is the
  number a correct feedforward should move furthest, which is why it is scored.
- **Delivery by regime.** r70: straight **80.0 %**, entry 95.7, hold 107.4, exit 113.2. **Pre-registered
  90–110 % on straights** — also a **target**: r6c under-delivers at 86 % and r39/r35 over-deliver at
  111/117 %. What it measures cleanly is the *direction and size* of the straight-line error, which is the
  friction term's own signature.

#### 7.6 Positive control

The same code must reproduce `V293-PLANT-IDENT-2026-09-13.md` on `r70_v293`, within **2 % relative or
0.003 absolute**, whichever is larger. Eleven instruments are checked and all eleven reproduce — dwells at
both strata, concentration, stiffness, turn-hold, tracking gain, overshoot, prominence, rate content,
integrator share and straight delivery. A FAIL here means an instrument moved, and **every number in
section 7 must be re-read before it is trusted**. The one number that is *not* matched is the step-event
total: the report's "38 step events found" is its pre-filter candidate count, and the post-filter total is
29, which is exactly the sum of its own per-band counts (3 + 18 + 8).

#### 7.7 Threshold calibration census

🛑 **A gate nothing fails is theatre. A gate nothing passes is a target, not a calibration.** §7.7 runs
each gate's own predicate on each cached route and prints the pass/fail matrix, so the reader can see
which gates are bracketed by real data and which are aspirational. A gate stated **as a ratio to r6c**
makes r6c's own PASS tautological (1 ≤ 2), so that column is marked `*` and excluded from the bracketing
judgement.

| gate | threshold | r70 | r6c | r39 | r35 | verdict |
|---|---|---|---|---|---|---|
| ratchet dwells th 0.25 * | ≤ 3× r6c | FAIL | PASS | PASS | PASS | bracketed |
| concentration q75–90 | ≤ 0.40 | FAIL | PASS | PASS | PASS | bracketed |
| tracking gain | 0.95–1.05 | FAIL | PASS | FAIL | FAIL | bracketed |
| turn hold >20 m/s | ≤ 1.04 | FAIL | PASS | FAIL | n/a | bracketed |
| step overshoot | ≤ 0.20 | FAIL | FAIL | FAIL | FAIL | 🛑 **target only** |
| 1–4 Hz prominence | < 3 dB | FAIL | PASS | PASS | PASS | bracketed |
| 1–4 Hz rate content * | ≤ 2× r6c | FAIL | PASS | FAIL | FAIL | 🛑 **target only** — only r6c passes, by construction |
| integrator share | < 0.20 | FAIL | FAIL | FAIL | FAIL | 🛑 **target only** |
| straight delivery | 90–110 % | FAIL | FAIL | FAIL | FAIL | 🛑 **target only** |

That distinction is computed at run time, not asserted here. **Five gates are bracketed by real data;
four are targets.** A FAIL on a target-only gate means "not yet at the target", not "worse than V282".

#### What a section 7 PASS licenses

"The statistic the operator's words pointed at has moved." Nothing more. **A statistic moving is not the
same as the car feeling right**, and the operator still scores the symptoms.

---

## The verdict block

Every clause prints as `PASS`, `FAIL`, `REVERT` or `REPORT`, each with its number and its threshold.
**Every gate is calibrated by V292 — the build the operator drove and rejected on 2026-09-13:**

| gate | V292 read | gate |
|---|---|---|
| present-window ring ÷ r6c | ×1.38 / ×1.07 / ×1.25 | ≤ 0.40 |
| F7 per 100 s | 3.99 / 2.22 / 6.30 | < 2 |
| tap ripple ÷ level | 0.214 / 0.327 / 0.339 | < 0.25 |
| absolute 6–8.5 Hz tap ripple ÷ r6c | ×2.23 / ×2.02 / ×2.23 | < 1.5 |

A gate a rejected build passes is theatre. None of these does.

**Two classes of revert trigger, and they point at different things** (new in v2):

- the **band** triggers — outer loop, F7, rip/L, absolute ripple, 13–17 Hz — say **stop the drive and go
  back to V282**. The firmware is the suspect.
- the **ratchet** trigger — §7.1 dwells/min at th 0.25 **above `r70_v293`'s** in **two or more** exposed
  bands — says go back to the **previous toggle config**. The fork tune is the suspect, the firmware is
  not, and `r70_v293` was a driveable, scored baseline. Two bands, not one, so a single thin band cannot
  fire it. It never fires when scoring `r70_v293` itself.

Then two standing reminders the block prints every time. **The operator scores the symptoms** — nothing
the tool prints licenses the word "fixed" for grinding, vibrating, micro-ratcheting, ratcheting or excess
friction; these are bands. And the operator-only revert triggers are not scoreable here: grinding
unchanged, a darty or loose feel, a one-sided pull at rest, any EME warning or DTC.

**If the identity holds and the ring does not fall**, the block prints the **terminal null sentence
verbatim**, in both the forms the record carries it: the pre-registration's "What PASS licenses" bullet
and DESIGN §6.3. That is the one outcome of this drive that closes a whole class, so it is quoted rather
than paraphrased.

---

## The controls — run once, before the drive

```
python rlog-tools/studies/grind/v293_flight_read.py --controls
```

This does two jobs. It runs the **same identity estimator** on six routes that are not V293 and confirms
it fails on all of them — an instrument that passes everywhere measures nothing. And it **recomputes every
band reference** the drive-day read cites, writing them to `_scratch/v293_flight_refs.json`, so those
numbers are re-derived from the caches rather than copied out of prose. Takes about 25 minutes; the
drive-day run then reads the JSON. Without it the script falls back to literals transcribed from
`V292-FLIGHT-READ-2026-09-13.md` and says so.

**Negative control, measured 2026-09-13.** Every row must fail the R² ≥ 0.50 gate:

| route | build | R² with V293 cells | resid | R² with own cells | resid |
|---|---|---|---|---|---|
| r6c | V282 | −0.011 | 173 | −1.217 | 256 |
| r39 | V282 | −0.840 | 320 | −2.882 | 465 |
| r35 | V281r3 | −0.069 | 236 | −1.529 | 363 |
| r6d_v292 | V292 | −0.135 | 270 | −1.781 | 423 |
| r6e_v292 | V292 | −1.225 | 317 | −4.601 | 502 |
| r6f_v292 | V292 | −0.561 | 255 | −2.954 | 406 |

On the const-fade reading r6c's own-cells row is R² −5.18 / residual 586, against the pre-registration's
−4.81 / 349 measured on r39's ten loudest windows — same sign, same order of magnitude, which is what a
whole-route number should give.

**The recomputed references reproduce the record exactly**, which is the check that the tool is reading
the corpus the same way the corpus was written:

| measure | recomputed | record |
|---|---|---|
| engaged÷disengaged 18–22 Hz, r6c / r39 / r35 | 3.399 / 3.920 / 3.618 | identical, §4 |
| same, r6d / r6e / r6f | 5.484 / 6.795 / 4.086 | identical, §4 |
| present-window amp p50, r6c / r39 / r35 | 2.630 / 2.766 / 3.487 | identical, §3.1 |
| presence %, all six routes | 9.8 / 20.9 / 16.2 / 18.1 / 18.7 / 20.5 | identical, §3.1 |
| F7 per 100 s, r6c / V292 ×3 | 1.03 / 3.99 / 2.22 / 6.30 | identical, DESIGN §6.2 |
| tap ripple ÷ level, r6c / r39 / V292 ×3 | 0.104 / 0.166 / 0.214 / 0.327 / 0.339 | identical, DESIGN §6.2 |

One number is **new** — the absolute 6–8.5 Hz tap ripple, which DESIGN §6.3's symmetric revert sentence
needs and never sized: r6c 73.1, r39 107.5, r35 119.2 counts; V292 163.0 / 147.4 / 162.8.

---

## Sanity check before you trust a run

Score a V292 route as if it were V293 and confirm the tool says so:

```
python rlog-tools/studies/grind/v293_flight_read.py r6f_v292 --build V293
```

Against the **rev-1** config it should fire the identity FAIL (R² −0.561), the toggle FAIL (`initData`:
`AccordRatePlantFF` absent = 1, `SteerKP` 0.9, `AccordTorqueKi` absent = 0.30, `SteerFriction` 0.01), the
kp FAIL (Kp 0.900 at 100 Hz over 42 905 frames — the installed tune), the **branch FAIL** (the plant-FF arm
executed, `|f − feedforward|/|f|` = 3.32, where the rev-1 config asks for the else arm), the ring FAIL
(×1.25), and **five REVERT triggers** — F7 6.30, tap ripple/level 0.339, absolute ripple ×2.23, the 1–4 Hz
outer loop at 5–10 m/s, and 13–17 Hz ×1.81. The Testing Ground row reports slot 1 variant A, informational.
If it returns anything resembling a pass on that route, stop and fix the instrument before reading a real
drive.

Note the branch row is the one that **inverts** when you point `--config` at the rev-2 file, which asks for
the plant-FF arm: on r6f the branch then reads PASS, because the gate tests *which arm ran against what the
config asked for*, not *which build is in the ECU*. That is the intended behaviour, and it is why the
branch gate alone never attributes a drive — the `identity`, `toggle` and `kp` gates do that.

Everything the script writes lands under `rlog-tools/studies/grind/_scratch/`. It reads rlogs and images
only. It flashes nothing and sends nothing on any bus.
