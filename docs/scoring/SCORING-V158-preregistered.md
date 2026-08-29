# SCORING V158 — pre-registered BEFORE the drive, 2026-08-29

🛑 **Written and committed before any V158 flight exists.**

## 🛑 THE RECOMMENDATION CHANGED, AND A POWER CALCULATION IS WHY

V160 (V158 + Lever B `0xC6446` 5244 → 6553) was the lead build. **It is demoted to a follow-up.**

V88 measured Lever B single-variable across a **10.24×** step (512 → 5244). V160's increment is
**1.2496×**. Extrapolating log-linearly from V88's own measured band ratios:

| band | V88's 10.24× step | V160's 1.25× increment predicts |
|---|---|---|
| 6–9 Hz | 0.859 | **0.986** — 1.4 % further |
| 9–12 Hz | 0.604 | **0.953** — 4.7 % further |
| 15–22 Hz | 0.549 | **0.944** — 5.6 % further |

against this kit's own same-firmware detection floor:

| band | null CI | not resolvable under |
|---|---|---|
| 6–9 Hz | route-71 split-half [0.18, 5.51] | ~3–5× |
| 18–22 Hz | r22 vs r23 [0.59, 1.34] | ~40 % |
| 21–26 Hz | r22 vs r23 [0.80, 1.20] | ~20 % |

⇒ **the Lever B increment is 4–30× below the floor. It cannot be measured on one drive.** It adds an
untested dose (V62's lesson: *"2× ≈ the OPTIMUM, not a point on a ramp"* — 5244 may already be at or
past optimum) and destroys attribution if the drive comes back worse.

**Fly V158. It is single-variable vs V122, and its change is the only one large enough to resolve.**

## What V158 is

V122 + the golden model's own damper prescription, **6 halfword edits, 10 payload bytes**, 67/67
assertions, CRC 50/50.
image `42078806f55829039b0891b0f32c465b7caa26f8c5079cfe9c60ab2ea7b0ccaf`

```
0xD77DA / 0xD77EE   FactorC (L2 speed) Y[0]  0 -> 429 / 426   (each mode's own Y[2])
0xD780E / 0xD7822   FactorE (L4 rate)  X[0]  60 -> 12
0xD7818 / 0xD782C   FactorE (L4 rate)  Y[1]  140 -> 539       (its own Y[2])
```

**It is the first build in this kit's history to deliver ANY base-assist damping at creep.** Stock and
every prior build sit at exactly 0 there, because `FactorC Y[0] = 0` zeroes the five-factor product
below 35 km/h.

### The predicted effect, in physical units — stated in advance

| source | viscous damping at creep |
|---|---|
| stock / V122 | **0.000** ct/(deg/s) |
| `gp-0x6bbe` (measured on-car, independent) | 1.571 ct/(deg/s) |
| **V158's damper** (from its own bytes) | **2.733** ct/(deg/s) |
| **total (Path 1 nominal)** | **4.304 — ×2.74** |
| **total NET of Path 2** | **2.63–3.53 — ×1.67 to ×2.25** (stability-bounded; see STATE) |

⚠ **[BELIEF] what that buys in ζ.** *Only* if the firmware's viscous term dominates damping would ζ go
**0.017–0.036 → 0.047–0.099**. If mechanical damping dominates, less. The Path-1 nominal is the
increment, NOT a ζ prediction.** The **x1.7-x2.7 NET** figure above is the one to hold: x2.74 is the
Path-1 nominal, before Path 2's stability-bounded pumping copy is netted off. This is the single
largest uncertainty and the drive is what settles it.


---

## 🛑 WHAT THE DRIVE MUST CONTAIN — not optional

V158's edit is **architecturally inert above ~35 km/h** (that is where stock FactorC already leaves
the dead zone). A highway drive tests nothing.

1. **Engaged creep, 2–8 km/h, with real steering activity.** This is the entire target band. Without
   it there is no result at all.
2. **AUDIO.** Only 5 of ~230 routes have usable creep-engaged audio, and the bus instrument has
   already been shown not to track what the operator hears (the engaged-vs-manual contrast collapses
   to **~1.1×** under controls, yet V88 demonstrably changed the felt symptom).
3. **At least one slow hard turn, hands-off, engaged** — the peak-command oscillation.
4. **A matched MANUAL creep segment** — same speeds, LKAS off. Without it every ratio is uncontrolled,
   and this session watched three uncontrolled ratios collapse when controls were added
   (2.8→1.12, 1.29→0.911, 1.309→0.958).

## PRIMARY — the operator's report

Standing rule: **score bands, let the OPERATOR score symptoms.** Three questions, each vs **V122**:

1. **ratcheting / stuttering at creep** — better / same / worse, **and at what speed**;
2. **grinding** — better / same / worse, and at what speed;
3. **steering effort / apparent mass at creep.** ⚠ V158 ADDS damping, which is drag. The operator's
   standing constraint is *low apparent mass and friction to LKAS AND no ratcheting*. If the ratchet
   improves but the wheel feels heavier at parking speeds, **that is the trade to report**, and the
   answer is to lower the dose, not abandon the lever.

## SECONDARY — bands, episode-clustered and speed-matched

Use **`rlog-tools/score/score_v158_creep.py`**. 🛑 **NOT `score_v133_creep.py`** — audited 2026-08-29 and its `boot()` is a **WINDOW** bootstrap (`rng.choice(e[:, i], len(e))`), which this kit’s standing rule forbids; measured **2.6x too confident** on synthetic data. The corrected scorer resamples EPISODES. Requirements it already satisfies:

- **episode bootstrap, never window bootstrap** — window bootstraps manufacture significance;
- a **30–40 Hz negative control** — a ratio moving in both signal and control bands is a global
  change, not a damping result;
- a **per-window speed census** — a moving wheel order manufactures "only on route X" lines;
- **safe cache pairs only**: `(t, probe)` or `(raw14_t, raw14_b4)`. Pairing `t` with `raw14_b4` reads
  the cave byte ~10 ms early = **28° of phase error at 7.79 Hz**.

## What will NOT be claimed

- No spectrum from the 427 wire (`0x1AB` samples at **49.8 Hz** ⇒ Nyquist 24.9 Hz).
- No ζ estimate from a band ratio — ζ needs a **ring-down**, the only estimator that passed its control.
- No "damping restored" claim from a 6–9 Hz ratio inside [0.18, 5.51]. **"Cannot resolve" is the
  honest reading, not "unchanged."**
- No amplitude claim from the `gp-0x6b98` probe — it under-ranges to ~1.5 bits; it is a **spectral**
  instrument only.

## Decision tree — committed in advance

| V158 result vs V122 | next build | why |
|---|---|---|
| ratchet **better**, effort acceptable | **V160** | take the free Lever B increment; then consider a damper dose ladder |
| ratchet **better**, wheel too heavy | lower FactorC `Y[0]` 429 → 234 (its own `Y[1]`) | dose 50 → 27, monotone, halves the drag |
| ratchet **unchanged**, effort unchanged | **V165** — damper dose ladder | the x1.7-x2.7 net was too small ⇒ the firmware term does not dominate the plant damping; the model’s *"err low"* argument is then overturned BY DATA |
| ratchet **worse** | **V167** (`0xC63A0` 1024→512), NOT a bare revert | **NAMED MECHANISM**: gp-0x6bd0 feeds BOTH aggregators, and Path 2 (FUN_00038148 @0x38150) applies an EXTRA pol multiply, so at pol = -1 it arrives PUMPING-signed. 0xC63A0 is that term’s Path-2 weight ALONE, so halving it removes half the pumping while keeping Path 1’s damping — it DISCRIMINATES, where a revert to V122 discards both and tells you nothing. Revert to V122 only if V167 is also worse. |
| **no creep episodes in the drive** | re-drive | the edit is inert above 35 km/h; a null would be for the wrong reason |

## Confounds stated in advance

- V158 changes **FactorC and FactorE together**. They are not separable on one drive, and the model's
  own analysis says neither alone reaches the required dose — so this is deliberate, not sloppy.
- **The damper is a drag term.** Any ratchet improvement is expected to come *with* some added effort.
  Reporting both is what makes the next dose choice possible.
- Damping fades as rate → 12 counts (`dose ∝ rate − 12`), so the very deepest micro regime gets less
  than the table suggests. This is deliberate (the model argues `X[0] = 12`, not lower).

## 🛑 REVISION, 2026-08-29 — THE INSTRUMENTED PRIMARY IS 18-22 Hz, NOT 6-9 Hz

Measured across every cached route with a computable null: **18-22 Hz resolves 7/9, 6-9 Hz resolves
1/9.** The 18-22 Hz engaged/manual ratio is **>1 on all nine routes (3.88 to 742)** — a large,
replicated, engagement-caused phenomenon. 6-9 Hz scatters around 1 with no consistent direction.

⚠ **This corrects an error above.** 18-22 Hz was designated a *“built-in control that should not
move”*. It is not a control: V158's damper is `-sign(rate) * f(|rate|)`, a **broadband viscous** term
whose LERP is on rate MAGNITUDE not frequency, so it opposes motion at every frequency and should
reduce 18-22 Hz as well.

| role | band | expectation |
|---|---|---|
| PRIMARY overall | the operator's report | unchanged |
| PRIMARY instrumented | **18-22 Hz** null-gated | the only band that resolves |
| secondary | 6-9 Hz | **expect NOT RESOLVED** — that is the measured floor |
| control | 30-40 Hz | must stay flat |

⚠ Attribution of an 18-22 Hz move to the damper holds **only because Lever B is byte-identical
across V122/V158** — verified. A future build touching both makes this band unattributable.

### CORRECTION to the 18-22 Hz threshold, same day

The detection threshold quoted above was derived from ONE cross-route replicate. Nine within-drive
split-half replicates give **median 1.72x, p90 2.93x, max 3.60x**, and **r24 (the V122 reference) is
the worst at 3.60x**. Reproducibility is worst where the excess is smallest, and V122 is the smallest.

| to clear | V158 must read |
|---|---|
| 1.72x median floor | <= 2.26 |
| 2.93x p90 floor | <= 1.32 |
| 3.60x r24 own floor | <= 1.08 |

A ratio of 1.0 means engaged == manual. **So V158 is instrumentally detectable only if it very nearly
eliminates the engaged excess.** Anything between roughly 1.1 and 3.9 is NOT RESOLVED, and that is the
most likely outcome. **The operator report remains the primary endpoint.**

### The 18-22 Hz prediction is ONE-SIDED, and that is what makes the drive falsifiable

| V158 reads | means |
|---|---|
| **1.42 - 2.32** | consistent with the damping account, but **inside the noise floor** -- NOT RESOLVED |
| **~3.9** | no measurable effect; damping is a small share of the plant, or the band is not resonance-limited |
| **clearly > 3.88**, outside [1.60, 10.87] high or above 7.56 | **the damping account is FALSIFIED**, and it is evidence the **Path-2 pumping copy dominates** -> fly **V167** |

Nothing in V158 predicts an increase: FactorC lifted and FactorE's dead zone opened both add a term
that OPPOSES motion in Path 1. So a rise is the one outcome that carries unambiguous information, and
its follow-up build already exists.

## [WITHDRAWN 2026-08-29 -- see the section below] Q of the 15-25 Hz resonance

The 15-25 Hz peak is strongly resonance-limited on every route (prominence 32-610x above the
28-40 Hz floor), and **Q is a better endpoint than any band ratio**:

| endpoint | split-half reproducibility |
|---|---|
| **Q of the 15-25 Hz peak** | **median 1.20x, p90 1.50x** |
| 18-22 Hz engaged/manual ratio | median 1.72x, p90 2.93x |
| 6-9 Hz engaged/manual ratio | resolves 1 route in 9 |

| V158 reads | means |
|---|---|
| **Q 1.64 - 2.68** | the predicted damping increase, **RESOLVED** against the 1.20x floor |
| Q ~3.6 - 4.5 | marginal to no effect |
| **Q clearly ABOVE 4.50** | **damping account FALSIFIED** -> Path-2 pumping -> fly **V167** |

Reference: **V122 (r24) Q = 4.50**. Q has fallen 9.00 -> 4.50 across V102..V122, so the endpoint has
tracked the kit's own progress.

Caveat: the pooled Q is not the mean of its halves (r24 pools to 4.50 from halves 6.00/6.75), so
split-half may understate pooled uncertainty. Both sides use the same procedure, so the comparison
holds.

## 🛑 PRIMARY ENDPOINT CORRECTED: slope-corrected EXCESS, not Q

Every previous resonance endpoint here was confounded by the wheel-rate signal's spectral
TILT, which runs 1/f^0.80 to 1/f^2.37 across routes. Coloured noise with **no resonance at
all** reproduces what the old measures reported:

| control (NO resonance) | prominence | fitted Q | fit r2 |
|---|---|---|---|
| 1/f^1.5 | 27.4 | 1.00 | 0.585 |
| 1/f^2.0 | 64.9 | 1.00 | 0.710 |
| real routes | 12.2 - 173.3 | 1.0 - 17.6 | 0.28 - 0.87 |

So fixed-floor prominence, fitted Lorentzian Q and half-power Q are all **withdrawn**.

### What replaces them

Fit the route's own power law over 3-40 Hz using only bins **outside** the bands under
test, measure the peak's excess over that background, and null it at **that route's own
measured slope**:

| band | excess | slope-matched null p95 | verdict |
|---|---|---|---|
| **GRIND 15-25 Hz** | **9.9 - 421.9** | 2.6 - 4.1 | **REAL on 9/9 routes** |
| RATCHET 5-12 Hz | 2.0 - 8.9 | 2.7 - 4.1 | real on only **6/9** |

The grind is unambiguous; the ratchet is marginal **in this channel**. That is a
signal-strength fact, not a noise one, and it is why 6-9 Hz endpoints have always
underperformed here.

### 🛑 The old inference rule was WRONG and is retracted

The withdrawn section said *"Q RISING above 4.50 falsifies the damping account -> fly
V167"*. **Half-power Q is NON-MONOTONE**: its null sits **above** the data (real 13.7-34.7
vs null p95 58-78), because on a noisy median periodogram the half-power crossing lands on
an adjacent bin. Adding damping broadens the peak and lowers Q, but once the peak weakens
toward the floor **Q rises again toward the noise value**. So a rise cannot distinguish
"damping failed" from "damping worked" -- exactly the discrimination the drive needed.
**Excess is monotone in peak strength and does not have this defect.**

### Scoring V158

Reference: **V122 (r24) grind excess 23.2x**, slope 1/f^1.62, split-half 1.67x on 7 windows.

| V158 reads | means |
|---|---|
| **excess clearly below 23.2x**, beyond the drive's own split-half | the damping account holds |
| within the split-half floor | no readable effect |
| **excess clearly ABOVE 23.2x** | the damping account is falsified -> the Path-2 pumping branch -> **V167** |

The one-sided logic is unchanged and now rests on a monotone statistic: nothing in V158
predicts a stronger peak, so a rise is the outcome that carries unambiguous information.

Run it with `rlog-tools/score/score_band_excess.py <route-tag>`.
