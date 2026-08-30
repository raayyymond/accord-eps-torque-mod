# SCORING — V217, PRE-REGISTERED

**Written before the drive. Every threshold below is fixed now.** If a number lands outside its
interval, that is reported as measured — the prediction is not re-fitted afterwards.

**Build:** `f89ea01f405d513985ce51c47f6796e1ea77f600fab3d9f7817cd79907a1967b`
**Card:** `docs/scoring/DRIVE-CARD-V217.md` · **Run:** `score_drive.py <tag> V217`

---

## 0. IDENTITY — did the build actually reach the car?

Nothing below is interpretable until these pass. A failure here is an *uninterpretable* drive, and it
is our defect, not a result.

| check | expected | if it fails |
|---|---|---|
| 427 probe reads `gp-0x6b4e` | non-degenerate, not stuck at 0 or rail | the probe edit did not take — re-verify the flashed image |
| `b5` non-degenerate | **not exactly 0.0 or 1.0** | degenerate ⇒ uninterpretable, **not a null** |
| per-episode grind peak | **NOT at 20.50 ± 1 Hz** | the notch is not in force — the biquad edit did not take |

✅ **The probe target is verified to HAVE LIVE FEEDS — checked, not assumed.**

🛑 **427 IS NOT COMPARABLE TO ANY EARLIER ROUTE.** The shelf reads `gp-0x6b4e` at `sar 5`; the car
(V122, route `r24`) reads **`gp-0x6abc` at `sar 3`** — a different variable at a 4× different LSB.
Nearly every build in the corpus moves this cell, so **no 427 percentile, clamp duty or threshold may
be pooled or compared across builds without decoding it first**: run
`analysis-2020accord/verify/can427_source_per_build.py`, which decodes source and shift straight from
each image. Ignoring this is what put a struck row in `STATE.md`'s 427 clamp table — see the
correction there dated 2026-08-29. Use 427 here as an **identity/liveness check only**. `gp-0x6b4e` is the mode-5 arm of the `0xC4124` router, summing value B from slots 2/4/5/9. Two of those are confirmed live computed signals, not constants:
  · **slot 2** → `gp-0x6b78`, the `FUN_00033d10` PI lane-2 output (written `0x33FFA`)
  · **slot 4** → `gp-0x6b68` (written `0x23ACC`), gated by `gp-0x6a64` vs `0xC50A6` and by `|gp-0x6b68| ≤ 10240`
  ⇒ a reading of exactly 0 would be a **result** (both feeds gated off), not a dead channel. Worth stating because the kit has three recorded uninterpretable nulls (V64, V68, V92) that were all probes on cells nothing drove.

The third is the strongest identity check available and it costs nothing: the notch attenuates
**335,719×** at 20.50 Hz. A peak surviving there is arithmetically impossible with the filter live.

```
   16.0 Hz  2.0x     19.5 Hz  10.4x     21.5 Hz  12.0x     25.0 Hz  3.4x
   18.0 Hz  3.8x     20.50 Hz  the null  23.0 Hz   5.4x
```

---

## 1. RATCHET — `0xC63AE` 1024 → 512

**Predicted `b5` = 0.168, CI-propagated interval [0.113, 0.255].**

Derived, not guessed: V217 carries the engaged inertia at **2.384×** the V105 reference (the damper
was restored to the flown car in V214–V217), and the measured on-car slope is **−0.0891 per doubling
[−0.1328, −0.0200]** from the V105→V106 single-cell pair.

> ⚠ **This differs from what earlier shelf builds would have predicted.** V209/V213 sat at dose
> 0.333 ⇒ b5 ≈ 0.42. V217 is a *higher* dose because the damper is back, so b5 should be **lower**.
> Registering it now so the change is not mistaken for an effect of the ratchet lever.

✅ **THE PREDICTION IS VALID — verified, not assumed.** The dose-response was measured on the **V105→V106** pair, so it only transfers if `b5` is still the same rung reading the same signal. The 164-byte cave is **byte-identical V105 → V217** (`sha256[:16] d3bb75d8fce08211`). Gate `[16]` now anchors the cave to **V105 specifically**, not merely across the shelf — the whole shelf could have shared a cave that differs from V105’s, and `b5` would have silently meant something else while every check still passed.

🛑 **THE LEVER’S STATED MECHANISM IS CONTRADICTED BY THE KIT’S OWN MEASUREMENTS.** The V210 builder justifies `0xC63AE` as *"high small-signal gain around a zero crossing is the shape that sustains a small-amplitude limit cycle"*. Against that:

```
  limit cycle          EXCLUDED   calibrated Welch ladder: car 20.9 vs pure tone 53.8
  classic stick-slip   KILLED     d log f / d log A = -0.034 (needs amplitude dependence)
  rate-limit           KILLED     would need -1.0
  backlash             KILLED     would need positive
  frequency tracks     LOAD       +0.467 Hz over a 17.8x torque range, NOT amplitude/command
```

⇒ The ratchet is a **lightly-damped mechanical resonance (Q 14–29, motor/rack side)** that *"engagement SUPPLIES … it does not amplify an existing tone"*. **The relay-sustains-a-limit-cycle story is wrong.**

🛑 **AND THERE IS ALREADY A MEASURED ON-CAR TEST OF THIS CURRENCY — IT CAME BACK NULL.** V104 raised the assist-lane gain ×1.85, and that biquad response **peaks at 7.94 Hz, dead centre of the ratchet band** (swept from the image this session; the close-out already carries `max|H|` 1.8501 as a documented GATE 2 exception, but nobody had noted WHERE the peak sits). It flew as route `a4`. The record: *"V104 flew and FAILED — fixed nothing … its dose provably arrived (1.824×, predicted 1.66–1.85) and it still produced no felt change."*

⇒ **An 85 % gain lift centred in the ratchet band produced no felt worsening.** That is a direct on-car test of whether 6–9 Hz loop gain drives the ratchet, and it says no — corroborating the mechanical-resonance finding independently.

⚠ **This LOWERS THE PRIOR on `0xC63AE`**, which trades in the same currency in the opposite direction. A ratchet null on V217 should therefore be read as **expected, not surprising**, and it should NOT be taken as evidence the dose failed to arrive — `b5` settles arrival separately.
⚠ Not strictly implied: V104’s lift was **band-limited** (a biquad peak) while `0xC63AE` is **broadband** (it scales a memoryless nonlinearity). The two are not the same experiment, which is why this lowers the prior rather than closing the lever.

✅ **The lever can still work — by a DIFFERENT mechanism.** `0xC63AE` scales the observer output that feeds the tracking reference and hence the command, so lowering it lowers the 6–9 Hz **excitation** of a resonance the firmware cannot damp. That is excitation reduction, not limit-cycle breaking.

⚠ **What this changes for scoring.** The describing-function amplitude dependence (0.47–0.79) was derived for the *limit-cycle* framing. Under excitation reduction the expected effect is closer to the **linear dose** (0.500× at rung 1). **Do not treat the describing-function numbers as the prediction**; they bound it, they do not set it. The b5 interval below is unaffected — it is measured from the inertia dose, not from this framing.

**What a null licenses:** b5 inside [0.113, 0.255] with the ratchet unchanged in feel ⇒ the dose
reached the car and was **insufficient**, not inert ⇒ fly **V218** (256). b5 *outside* the interval
⇒ report as measured; do not re-fit.

**What would falsify the lever entirely:** b5 degenerate, or the operator reports the ratchet
unchanged across **both** V217 and V218. At that point `0xC63AE` is spent and the ratchet has no
firmware lever left — every alternative is already closed on its own terms.

## 2. GRINDING — the 20.50 Hz notch

**Predicted: 95.3 % of median episode 15–25 Hz band energy removed** (energy-weighted over 125
corpus episodes). The centre is confirmed optimal by two independent objectives — median episode
peak, and energy-weighted removal — which agree on 20.50 to the quarter-Hz.

**Primary measure is the operator's own report.** The band is the instrument, not the score.

**What a null licenses:** peaks displaced off 20.50 (identity passes) *and* grinding still reported
⇒ the notch is in force and the residual is outside its skirt ⇒ fly **V220** (poles 13.50, residual
4.7 % → 2.8 %). It does **not** license re-centring: r1e-style low-centroid routes are the
documented p10 tail, and one biquad was never going to cover it.

## 3. AUTHORITY — `0xC6CD0` 6× → 8×

**Predicted +28.9 %** (authority ~ m^0.88, the record's own exponent).

🛑 **There is no clean on-wire authority metric in this kit.** The honest measure is the operator's
report of how the wheel responds to LKAS. Registering that now rather than inventing a proxy after
the fact.

**What a null licenses:** authority still short with grinding/ratchet acceptable ⇒ fly **V219**
(10×, +56.0 %). Authority fine but something is worse above 30 Hz ⇒ the gain step is the suspect.

## 4. DAMAGE BAND — 30–49 Hz

The notch gives nothing back above 29.5 Hz, so the 8× step raises loop gain there 1.65× vs the car.

```
   30-40 Hz / grind ratio   < ~2    nothing broke -- keep the gain step
                            > ~5    something broke -- fall back to V216
                            between UNRESOLVED, needs a matched V216/V217 pair
```

🛑 **This band cannot resolve the 1.65× effect** — the corpus IQR spans a factor of 2.0, which is
wider. It is a **large-excursion detector** only. Do not read a small move in either direction.

🛑 **AND IT IS NOT PURELY 30–49 Hz.** Caches run at fs = 101.01–101.26 Hz ⇒ Nyquist ~50.5 Hz, so
anything real in **52–71 Hz folds into this band** — a 71 Hz line lands on 30 Hz. The fold source sits
entirely above Nyquist and can be neither seen nor filtered out afterwards, and no channel escapes it.
Read every number here as *"30–49 Hz **or its 52–71 Hz alias**"*. Settling it needs a cave zero-crossing
counter (`docs/specs/design/PROBE-zero-crossing-rate-counter.md`), not more analysis.

---

## 5. IS IT COMMANDED, OR IS THE EPS GENERATING IT? — free, within-drive, no matched pair

Added 2026-08-29 from the r7d decomposition. Costs nothing — both channels are already cached — and it
**attributes any high-band line to a side of the CAN bus from a single engaged episode.**

On r7d the two spectra separate completely:

```
   cs_rate  (measured column rate)   30.1 Hz at 63x background, engaged; ABSENT manual
   probe    (the firmware's own byte) 30.1 Hz at 11x background, engaged
   sc_req   (the LKAS request)        3.0 / 5.0 / 7.0 / 9.0 Hz -- a clean roll-off, NO 30 Hz at all
```

⇒ the EPS was **generating** that line, not tracking it. Apply the same test to whatever V217 shows:

| `sc_req` at the line | reading |
|---|---|
| line **present** in `sc_req` | openpilot is commanding it — upstream of the firmware, and no cal lever on the shelf addresses it |
| line **absent** from `sc_req`, present in `cs_rate` | **generated inside the EPS loop** — a firmware lever can reach it |
| line absent from both | not a steering-loop phenomenon; check the IMU channels for a road or tyre order |

🛑 This attributes, it does not size. It says **which side** a line comes from, never how big the
effect is or whether a lever moved it.

---

## What is NOT being tested, and will not be claimed

- **The ~31 Hz line on route `r7d`** (the aborted V94 drive). Narrowed on 2026-08-29 but still not
  named: it is **in the loop and not commanded** (63× in `cs_rate`, 11× in `probe`, absent from
  `sc_req`), it is **not a harmonic** of the 7.8 Hz ratchet (the 2f rung sits *below* background), and
  it is **not the inertia mode moving** — refuted again under the saturating functional form that
  favours that mechanism most. What is left is a **broadband engaged loop-gain rise carried by one
  drive**, confounded with build order (dose vs build number r = +0.750) and **not separable from a
  52–71 Hz alias**. This drive cannot settle any of it.
  See `analysis-2020accord/studies/mixer/r7d_31hz_what_it_is_and_isnt.py`.
- **Whether the 8× gain costs anything at 30–40 Hz.** Needs a matched pair, not one drive.
- **Any interaction between the three levers.** They are separated by band and by the probe, not by
  the build. A build carrying all three cannot decompose them.
