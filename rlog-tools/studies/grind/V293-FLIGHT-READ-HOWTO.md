# V293 FLIGHT READ — how to score the first drive

**One command.** Everything below is what it prints and what each line means.

```
python rlog-tools/studies/grind/v293_flight_read.py <route id>
```

`<route id>` is the full comma route (`75604b0a432fdc89_00000070--abc123…`), a bare route counter, or a
cache tag that already exists. If the route is not in the v280 cache yet the script **extracts it first**
— the decode is copied verbatim from `extract_v292_routes.py`, and it was checked against the record: on
`75604b0a432fdc89_0000006f--d876c761bc` it reproduced `r6f_v292.npz` and `r6f_v292_b4.npz`
**byte-identically, every array**. So a route this tool extracts is readable by every other census tool
with the same yardstick.

Other flags: `--build V282|V292|V293|V281r3` (which image's cells to score against — defaults to V293, or
to a known route's own build) · `--tag` (cache tag to write) · `--reextract` · `--no-positive` (skips the
positive control, saves a few seconds) · `--controls` (see the last section).

Runtime is dominated by one thing: the presence predicate runs the record's 4096-point prominence
spectrum per 2 s window, about **1 s per 10 s of engaged time**. A 10-minute drive scores in 2–3 minutes.
That call is deliberately not optimised — every published presence number in the corpus came out of it,
and a faster spectral floor would silently move the comparison.

---

## What the scorecard says, section by section

### 0. Exposure and the fork toggles — is the drive attributable at all?

**The switch is a Testing Ground, not a param.** On the device it is **Galaxy → Testing Ground → slot 9
"Accord EPS Torque Mode" → variant B** ("B - Torque mode (V293+ only)"; A is the installed rate-servo
tune). The selection lives in `/data/testing_grounds/slots.json`. `AccordEpsTorqueMode` and the
`AccordTorqueMode*` family **no longer exist** — `common/params_keys.h` carries a comment where the key
used to be. So that row on the scorecard is **informational only**: `absent` is expected and carries no
information, while a *value* would mean the device is running a pre-rework fork.

Three readings, of which **two are gates**:

| reading | source | role |
|---|---|---|
| `AccordEpsTorqueMode` | `initData.params` | **informational** — absent by design |
| `epsTorqueMode` duty | `starpilotLateralState`, 100 Hz | **GATE**: must read `1.000`. Measured `0.000` over 75 374 frames on r6f_v292, the pre-V293 control. |
| median `f / desiredLateralAccel` | `controlsState…torqueState` | **GATE**: `≥ 0.75`. The only one that reads the **control path** rather than a stored setting. |
| Testing Ground slot / variant | `customReserved9` | reported — must read slot `9` variant `B`, and the scorecard says whether it agrees with the duty gate |

🛑 **Two cereal schema collisions, and neither reading works without a patch.** The kit declares union
slot `@137` as `epsTelemetry :Custom.EpsTelemetry` and `@116` as `modelDataV2SP :Custom.ModelDataV2SP`.
The fork declares the *same two slots with the same two struct ids* as `starpilotLateralState
:Custom.StarPilotLateralState` (`0xc2243c65e0340384`) and `customReserved9 :Custom.CustomReserved9`
(`0xa1680744031fdb2d`). The field layouts share nothing — nine V31P-V2 gate flags against eight
floats/bools plus `epsTorqueMode @8`, and one enum against six Text/UInt64 fields carrying the Testing
Ground selection. This script builds a **patched copy** of the schema under `_scratch/cereal_fork/` and
loads it with `capnp.load()`; the kit's own schema is never modified. **Any other kit script that reads
`epsTelemetry` or `modelDataV2SP` from a 2026-09 rlog is reading garbage.**

The Testing Ground selection **is** on the wire: `the_galaxy` publishes `slotId`, `slotName`, `variant`,
`variantLabel`, `reason` and `wallTimeNanos` on a heartbeat and on every manual change. Decoded on
r6f_v292 it reads *slot 1 variant A, "ACC Bolt Long Tune / A - Installed tune"* over 51 frames — real
text, which is the proof the patched struct decodes rather than producing plausible noise. If the
selection changes mid-route the scorecard says so and lists every pair it saw.

The `f/D` ratio deserves its own note, because the obvious statistic does not work. Under torque mode
friction ships at 0, so `f = desiredLateralAccel` exactly and the ratio is `1.000`; the rate-plant branch
scales it down. Measured pooled medians on four routes that are **not** torque mode: r6c 0.32, r6d 0.24,
r6e 0.40, r6f 0.31, worst single `|D|` band 0.58. The gate at 0.75 sits about 1.3× above the worst
observation and 1.3× below the expected 1.000. **The whole-route regression slope of f on D is not usable
as a gate** — it reads 0.21–0.64 on those same four routes. The ratio is the statistic; the slope is
printed only as context.

If the toggle reads OFF with V293 in the ECU, the band scores below are **not a build contrast** and the
mismatch is the feedforward-starved *and* high-gain-feedback state, which is not merely sluggish
(`ADV-V293-D` §4.4).

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

It should fire the identity FAIL (R² −0.561), the toggle FAIL (`epsTorqueMode` duty 0.000), the branch
FAIL (median f/D 0.294), the ring FAIL (×1.25), and **five REVERT triggers** — F7 6.30, tap ripple/level
0.339, absolute ripple ×2.23, the 1–4 Hz outer loop at 5–10 m/s, and 13–17 Hz ×1.81. The Testing Ground
row reports slot 1 variant A, agreeing with the duty gate that this is not torque mode. If it returns
anything resembling a pass on that route, stop and fix the instrument before reading a real drive.

Everything the script writes lands under `rlog-tools/studies/grind/_scratch/`. It reads rlogs and images
only. It flashes nothing and sends nothing on any bus.
