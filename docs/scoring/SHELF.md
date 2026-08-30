# THE SHELF — what is built, what to flash, what it changes

**Updated 2026-08-29.** Five flashable builds: **V209 (fly this)** · V208 (the fix) · V210 (ratchet lever, priced) · **V211 (authority — STAGED, see below)** · V199 (fallback). All five reproduce bit-for-bit from their builders.

🛑 **V207 was built and RETIRED without flying.** It asked whether the delivery chain zero-rejects
the merged command; the answer is provably no — the compensation is capped at 2560 by a 3-knot table,
the governor at 4762, and 7322 sits 870 counts under the ±8192 window. **A drive was saved by reading
a table.** Everything else from this arc is renamed
`SUPERSEDED-DO-NOT-FLASH-GATE2-…` and must not be sent.

🛑 **Nothing here has been flashed and no CAN or UDS message has been sent.** Flashing requires you to
name the file and the bus, and they will be read back to you first.

---

## ⭐ V209 — FLASH THIS ONE. The re-centred notch, plus the probe.

```
39990-TVA,A160-V209-V208BASE-PROBE-GP6B4E-0x13000-0x100000.rwd
  image 984dfe5590bb8bfedaedca1256008cdd81cf33837acaa54a909463768b47327c
```

Preflight 8/8, 40/40. V208 control cells byte-identical, +3 payload bytes putting `gp-0x6b4e` on CAN 427.

## V208 — the same fix without the instrument

```
39990-TVA,A160-V208-V202BASE-NOTCH.20.50.REFIT.ON.EPISODES-0x13000-0x100000.rwd
  image e27b4fcc2dafd872feb25e5625544dbe4f9067a742cec1670d8d3dde176b1f7a
```

🛑 **The notch was a hertz low.** It was fitted at 19.75 Hz from a per-route median of 20.12. Surveying
the cached corpus **per engaged episode** — 20 routes, 125 episodes — gives **median 20.70 Hz**
(p10 16.37, p90 23.05). Scoring the actual peaks through each candidate, under the same two gates:

| design | Δphase | median atten | p10 |
|---|---|---|---|
| V202 (19.75 / 15.25 / 0.9600) | −7.83° | 5.7× | 2.3× |
| **V208 (20.50 / 15.50 / 0.9575)** | −7.98° | **9.5×** | 2.0× |

✅ **Re-scored on the 18-route cluster** (the 2 outlier routes at ~15.7 Hz excluded, a 3.71 Hz gap separates them): **V208 gives median 10.4×, p10 3.4×.** The pooled p10 of 2.0× was those two routes, not a distribution tail. The best possible re-centre buys 1.11× — inside noise, so **V208 stands.**

**1.66× at the median for the same gate and budget** — and only −0.11° more lag at 3 Hz than V202, so
very nearly free. ⚠ 20 routes here vs 67 in the original fit, so the 0.58 Hz gap could be sampling;
what is not sample-dependent is that 19.75 sits below **both** medians.

## After the drive, one command

```
python rlog-tools/score/score_drive.py <route-tag>
```

Exposure and episode count first, then the free cave rungs (degenerate readings flagged as
**uninterpretable, not null**), the b3 validity gate, b6 against measured-dead, **b5 against its
pre-registered 0.31–0.49**, the 427 channel, and the grind peak **stratified by this drive’s own
episodes**. It refuses to apply the b5 prediction to a non-shelf route.

## V210 — the ratchet lever, on the current notch

```
39990-TVA,A160-V210-V208BASE-C63AE.1024.TO.512-0x13000-0x100000.rwd
  image ab49ca762b7017de436a7b80d15a7a72fda7e3f862f32c3a9106318018da814b
```

✅ **GATE 1 + GATE 2 PASS.** V208 plus **one calibration byte**: `0xC63AE` 1024 → 512. Preflight 8/8, 34/34 assertions, cave
byte-identical, the 427 probe untouched.

⭐ **What it actually does: it RAISES A CEILING.** `0xC63AE` scales the LERP’s input, so halving it **doubles the residual needed to clip — 14490 → 28980, at every speed.** The record’s own model of the ratchet is a *command-gated saturation*, with the instruction *“find what clips, and either raise its ceiling or soften its corner”*. This is the raise-its-ceiling branch, and unlike a gain argument it survives the ratchet being speed-invariant, because clip duty is about the ceiling, not loop gain.

`0xC63AE` also scales the curve behind `gp-0x6b70`, which computing from the image shows is a
**soft relay** — gain 2.67–3.77× near zero against 0.26–0.52× mid-range. Halving it halves that
small-signal gain (2.67→1.33, 3.77→1.89). It has **exactly one site image-wide and zero writers**,
and scales this stage only — the base assist map is untouched.

⚖ **The price.** The record's nine-link polarity trace covers this stage, with a measured
`d(gp-0x6b94)/d(gp-0x6b70)` of +0.25. Lowering the scale shrinks `gp-0x6b70` toward zero, and V87
measured it **negative 67 % of engaged time** — so the net is **predominantly less assist, a slightly
heavier wheel.** You have asked for low apparent friction *and* no ratcheting; this buys one with some
of the other, which is why it is **not** the recommended build. **Fly V205 first** — it measures the
range so this dose can be sized instead of guessed. A quarter dose is the follow-up.


### 🛑 PRE-REGISTERED, AND IT CHANGES HOW V206 MUST BE SCORED

If the ratchet is a limit cycle through this stage, it sits where `N(A)·|G|=1`, and the describing
function computed from the image **peaks at a specific amplitude**:

| speed | limit-cycle amplitude A* | N(A*) | predicted `|gp-0x6b70|` swing |
|---|---|---|---|
| 320 | 185 | 2.49× | 460 counts |
| 640 | 165 | 2.65× | 438 counts |
| 1280 | 150 | 3.02× | 453 counts |
| 2560 | 165 | 3.75× | 619 counts |
| 5120 | 310 | 3.95× | 1224 counts |

🛑 **SUPERSEDED ENDPOINT.** Two corrections: the limit-cycle FREQUENCY test is vacuous (a Q 14–29 resonance pins the −180° crossing within ±0.3 Hz of 7.79, so every hypothesis passes), and the amplitude table above is SPEED-INDEXED while the record calls the ratchet **speed-invariant** — so do not score on amplitude either.

⭐ **SCORE V205 ON CLIP DUTY AT ±8192.** `gp-0x6b70` saturates there and V205 reads it directly. High duty ⇒ the command-gated-saturation model is confirmed and V206 is aimed correctly. Low-but-nonzero ⇒ partial; a quarter dose quadruples the ceiling. **Identically zero ⇒ the element never clips and V206 comes off the shelf.** A duty needs no scale calibration and cannot be averaged away.


### ✅ A FREE ENDPOINT EVERY SHELF BUILD ALREADY CARRIES

The 164-byte cave at 0xC4B34 is **byte-identical from V105 through V202**, so V202/V205/V206 carry
V105’s exact rungs. Two of them report for free, with no extra bytes:

| rung | meaning | what to expect |
|---|---|---|
| **b5** | |modelled friction| ≥ |inertia| | **0.42, range 0.31–0.49.** V105 measured 0.2798 at 1.000× the inertia dose; V202 runs 0.333×. **b5 ≤ 0.28 means the halving is not reaching the car and the ratchet lever is inert** — the most useful null available |
| b6 | |gp-0x6b94| ≥ |gp-0x4f64| | 0.000000 — already measured dead on two routes; a non-zero reading would be new information |

The b5 prediction comes from a measured single-cell pair: V105→V106 doubled the inertia curve and b5
fell **−0.0891 [−0.1328, −0.0200]** on an episode bootstrap, with both sign rungs as null controls.
So this lever is known to reach the car with the right sign — what is unknown is whether the halving
does, and one drive of any shelf build answers it.

## 🛑 V211 — STAGED. Do NOT flash this until V209 has confirmed the grind fix.

```
39990-TVA,A160-V211-V208BASE-GAIN8X-CLAMPS4096-0x13000-0x100000.rwd
  image 70b205589b6f81a9f1e4f039daf8f744a66a1b9865ddbe133b499ef6ce35368e
```

**This is the LKAS authority build** — the first with a defensible case since V101. It raises
the forward gain 6× → 8× and the two clamps that must track it. 37/37, preflight 8/8.

| cell | V208 → V211 | why |
|---|---|---|
| `0xC6CD0` | 5346 → 7128 | the forward gain, 6× → 8× |
| `0xC61B2` | 3072 → 4096 | at 8× the lane max is 3341, which exceeds 3072 |
| `0xC61B4` | 3072 → 4096 | same — this is why V101 had to raise them too |

**Why it is worth re-opening.** The gain was abandoned three times because vibration grows as
`m^1.74` against authority’s `m^0.88`. **That trade is set by the baseline, and V208 moves it.**
Energy-weighted over the band the gain excites (22–26 Hz, 130 episodes):

| | |
|---|---|
| V208 attenuation there | **3.70×** (amplitude) |
| 6× → 8× vibration growth | 1.65× |
| **net vs the car today** | **0.45× — about 2.2× quieter** |
| authority gained | 1.29× |

V101 flew 8× at **1.65×** the then-current level and you reported grinding at all speeds. This
sits at **0.45×**.

🛑 **The staging is the safeguard, and it is not optional.** The case rests on a *belief*:
that the notch attenuates a **command-excited** line. The notch is on the base-assist path, not
the command path — but it sits inside the loop (motion → column torque → sensor → assist map
→ biquad → aggregator → motor → motion), so it lowers the loop gain that *sustains* the
resonance whatever excites it. **That is reasoning, not measurement.** If it is wrong, 8× lands
at 1.65× and you will hear it on the first engaged mile.

✅ The builder asserts the three gates that killed earlier gain builds: `0xC674E` = 5120 must
stay **above** the tracking clamp (the abort condition that caps this lever below 10×), lane max
3341 < 4096 so the clamps do not bind, and `0xC407E` stays at Honda’s 511 — V73
raised it and V74/V75 faulted.
## V199 — the low-phase fallback

```
39990-TVA,A160-V199-V196BASE-NOTCH.POLES.BELOW.ZEROS-0x13000-0x100000.rwd
  image c86646ab48c4a62546b4e7bafa59f8097d3bdd99ffdcd3aeabd9f93c7252dc10
  rwd   8df71f5db9f51e3cccf2d14c27aa580869434125112271115cfaddeddface708
```

A notch on the grind at **19.75 Hz**, plus the engaged inertia half-dose, built so the filter **cannot
add loop gain at any frequency**.

---

## 🛑 WHY V194 / V195 / V196 / V198 WERE PULLED

`BUILD-LINEAGE.md`, V105 section, says it outright:

> *"THE HIDDEN ONE: fixing DC with **poles at the notch angle** (the textbook narrow notch) forces
> `max|H|` to 1.098–1.608 … Fix: **Honda's own poles-BELOW-zeros layout**. **Check `max|H|` over
> 0–500 Hz against stock's 1.0000 before shipping any biquad edit.**"*

Every notch build from V188 on put the poles at the zeros. Measured from the built images:

| build | `max|H|` 0–500 Hz | zeros | poles | radius | verdict |
|---|---|---|---|---|---|
| V122 (Honda's layout) | 1.0000 | 55.23 | 42.35 | 0.7966 | PASS |
| V188 / V189 / V194 | 1.3533 | 19.40 | 19.40 | 0.9300 | **FAIL — adds 35 % loop gain** |
| V195 / V196 / V198 | 1.7177 | 19.75 | 19.75 | 0.9000 | **FAIL — adds 72 % loop gain** |
| **V199 / V200** | **1.000000** | 19.75 | **17.45** | 0.9675 | **PASS** |

V196 amplifies **1.88× Honda at 35 Hz, 4.57× at 45 Hz, 1.72× at Nyquist**. V103's own GATE 2 — the
argument that licensed arming this filter at all — was *"|H| ≤ 1.000032 everywhere 0.1–500 Hz ⇒ the
filter can only REMOVE loop gain, never add it."* A filter that **adds** gain in the loop whose
instability we are chasing is not a fix.

**It shipped because V195's own gate was written `check(mx <= 2.0, …)`.** The gate existed and the
number in it was wrong. V199's is `<= 1.0000001`, with a control assertion that the V196 base fails it.

---

## WHAT EVERY BUILD ON THIS SHELF CHANGES vs V122 — 11 cells, 30 payload bytes

| addr | V122 → V208/V209 | what it physically is | introduced |
|---|---|---|---|
| `0xC60A8` | −1.5372 → -1.905926 | biquad pole angle → **15.50 Hz** | V208 |
| `0xC60AC` | 0.63462 → 0.9168062 | biquad pole radius → **0.9575** | V208 |
| `0xC60B0` | −1.8808 → -1.983432 | **the notch centre, 55.23 → 20.50 Hz** | V208 |
| `0xC60B4` | 0.81731 → 0.6567325 | overall gain — forced by unity DC | V208 |
| `0xC40D2` | 1020 → **102** | K1, modelled Coulomb friction — Honda’s VALUE, but see below | V177 |
| `0xC40DC` | 8 → **22** | acceleration EMA alpha → **Honda** | V179 |
| `0xC63A6` | 1024 → **512** | w[3], the inertia term's weight, halved | V181 |
| `0xD7A5C` | (−29490,−17202,−16000) → **(−4915,−2867,−983)** | **engaged** inertia curve, **half Honda** | V196, kept |
| `0xD7A6C` | (−29490,−17202,−16000) → (−9830,−5734,−1966) | m27 inertia curve → **Honda** | V175 |
| `0x55DF2` | −27324 → −27328 | CAN 427 probe source → `gp-0x6ac0` | V183 |
| `0x55E10` | 12963 → 12964 | the probe's pack shift, `sar 4` | V183 |

**Measured on-car:** none of the four biquad cells — this filter geometry has never flown.
**Reverts to Honda:** `0xC40DC`, `0xD7A6C`.
🛑 **The friction lane is NOT Honda’s.** `0xC40D2` holds Honda’s K1, but the ramp knee `0xC40BC` was
never reverted (600 → 3000) and it multiplies the whole expression: `(600/3000)×(102/102)` = **0.200×**
Honda below saturation, with saturation moved from motor-rate 50 to 250. Above saturation it equals
Honda exactly. **Less friction means less ratchet and matches your low-friction directive, but the
verified polarity is more friction = more assist, so it is also an authority cut in that lane.**
**Unverified doses:** `0xC63A6`, `0xD7A5C` (the inertia sign has not been confirmed on-car).
**The cave is byte-identical** to V196 — no code-cave change, so this is not the bricking class.

🛑 **Manual driving is unaffected by the biquad either way.** The section is engagement-gated by V103's
three-site patch on `gp-0x6806`, so every notch cell is inert with LKAS off.

---

## BEFORE YOU FLASH

```
python flashing-2020accord/preflight.py "<the .rwd filename>"     # V199/V200/V201 all pass 8/8
tmux kill-server                                                  # openpilot/pandad MUST be dead
```
Name the file and the bus out loud. They will be read back to you before anything is sent.

## THE DRIVE

Two passes are enough. The design law is that one short symptomatic drive must interpret the build.

1. **~15 s engaged creep, hands off** — the grind's home ground.
2. **~15 s engaged, hands lightly on** — the corpus blind spot; `f'` compresses 6.3× when you push.

Then:
```
python rlog-tools/score/score_drive.py <tag>       # start here — one command
python rlog-tools/score/cross_channel_band_excess.py <tag>
python rlog-tools/probe/decode_v205_observer_output.py <tag> --v205  # V205 only
python rlog-tools/probe/decode_v204_observer_lane.py <tag> --v204    # V204 only
```

## STOP CONDITIONS

| what you feel | what it means | what to do |
|---|---|---|
| ratcheting noticeably **worse** | the inertia sign is inverted | stop; reflash the prior build |
| wheel heavy or dead to fast inputs | the half-dose is too much | stop; quarter it |
| a **new high note while engaged** | Honda's 55 Hz null, which the notch gives up | stop; it can only appear with LKAS on |
| grinding unchanged | the notch is aimed at the wrong frequency | stop — no point continuing |

## PRE-REGISTERED — write the sentence a null will license

| endpoint | prediction | what a null means |
|---|---|---|
| **15–25 Hz excess on `cs_rate`, STRATIFIED BY THE DRIVE’S OWN PEAK** | peak near 20 Hz → **24.7×**; peak near 18 Hz → 4.6×; peak near 16.3 Hz → **2.3×** | pooling these hides the result — a low-peak drive can look like a null when the filter did exactly what it was designed to |
| 6–9 Hz excess on `cs_tq` | unchanged | the notch was never aimed there; that band is the ratchet |
| LKAS command 0.5–3 Hz | unchanged | the biquad is not in the command path at all, so any movement here is something else |
| `gp-0x6b7e` content at the drive’s peak (V203) | small vs the notch output | if it dominates, the pedestal is the bypass and the lever is `0xC6906–090C` (K = 20 at all four knots) |
| `gp-0x6b7e` duty | if identically zero, the friction-hold limiter never cuts engaged | the whole parallel path leaves the model |

## 🛑 WHAT THE NOTCH CAN AND CANNOT FIX — corrected 2026-08-29

Decompiling `FUN_000352b4` settled which signal this filter is actually on. The tp anchors check out
exactly (`tp+0x749b` = `0xC649B` the arm cell, `tp+0x70a8`–`0xb4` = the four coefficient cells), so this
is the filter we have been editing:

```
gp-0x4f60 (TORQUE SENSOR) -> clamp +-8192 -> 10-knot assist map -> gp-0x6b7a
  -> friction-hold limiter -> gp-0x6b82 -> BIQUAD -> clamp +-12.0 -> x1024
  -> + gp-0x6b7e  (UNFILTERED, added AFTER the filter)
  -> clamp +-0x3000 -> gp-0x6b86 -> aggregator
```

**`gp-0x6b86` is the base power-assist output, not the LKAS command.** An earlier note of mine called
it "the LKAS command" — that was wrong and is retracted. What follows:

| symptom | can this notch fix it? |
|---|---|
| **Grinding** | **Yes, and this is the right place.** motion → column torque → sensor → assist map → biquad → aggregator → motor → motion **is** the loop, and the notch cuts its gain at 19.75 Hz. |
| **LKAS authority** | **Not affected either way — and that is good news.** openpilot's command never passes through this filter, so **no notch dose can reduce how hard it steers.** The authority objection does not apply to this lever. |
| **Peak command oscillation** | **Not directly.** The command does not pass through the filter. It may still fall if it *tracks* the grind, which the record says it does — but that is an indirect claim, and this build is not evidence for it. |
| **Ratcheting** | Not by the notch. That is the inertia half-dose at `0xD7A5C`, carried on all three builds. |
