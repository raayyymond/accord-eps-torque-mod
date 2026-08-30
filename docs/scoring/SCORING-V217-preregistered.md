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

✅ **The probe target is verified to HAVE LIVE FEEDS — checked, not assumed.** `gp-0x6b4e` is the mode-5 arm of the `0xC4124` router, summing value B from slots 2/4/5/9. Two of those are confirmed live computed signals, not constants:
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

---

## What is NOT being tested, and will not be claimed

- **The ~31 Hz line on route `r7d`** (the aborted V94 drive). Its mechanism is unexplained; the
  apparent-inertia hypothesis is refuted by its own arithmetic. This drive cannot settle it.
- **Whether the 8× gain costs anything at 30–40 Hz.** Needs a matched pair, not one drive.
- **Any interaction between the three levers.** They are separated by band and by the probe, not by
  the build. A build carrying all three cannot decompose them.
