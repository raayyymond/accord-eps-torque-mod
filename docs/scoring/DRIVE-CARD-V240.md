# DRIVE CARD — V240

## 🚗 DRIVE THIS ONE

```
  V240   39990-TVA,A160-V240-V238BASE-NORMAL.SLEW.HONDA0.600-0x13000-0x100000.rwd
         rwd    sha256 617f63f3cbd3de34...      image sha256 f2745df252e7ce7e...
  BEFORE anything: kill openpilot/pandad   ->  tmux kill-server
```

🛑 **The flash decision is yours. Name the file and the bus, and I will repeat both back before
anything happens.** Nothing is flashed without that.

**While driving — the whole job:** *does the car feel acceptable?* One episode is enough and **your
verdict is final.** If it feels wrong, **stop.**

**Stop and say so if:**
- the **ratchet or stutter is clearly worse**
- steering feels **hesitant** — a brief lag before assist catches up on a quick input. **This is V240's
  predicted failure mode.** If you feel it, the answer is a smaller dose, not a bigger one
- the wheel feels **heavier near centre** — measured *not* to happen, so it would matter
- anything faults, or the EPS lamp lights

**Fallbacks in order:** **V238** → **V235** → **V122** (your car).

---

## The lever, and why nobody found it before

`gp-0x69a0` rate-limits the assist-map walk. `FUN_00035b20` picks it from **two** curves depending on
whether the hard-reversal counter has tripped:

```
  NORMAL       0xC693E = [358, 358, 461, 512]   <- live in ordinary driving.  BYTE-STOCK on all 161 images
  OSCILLATING  0xC691A = [358, 307, 307, 307]   <- V192 tightened THIS one
```

**V192 moved the oscillating curve — and its own card says that curve "is read ONLY on the counter≥5
branch so it is provably inert in normal driving."** The curve that is *always* live has never been
touched by anyone.

V240 applies **Honda's own ratio** to it. Honda's oscillation response steps 512 → 307 = 0.5996:

```
  [358, 358, 461, 512]  ×0.600  ->  [215, 215, 277, 307]
```

**`Y[3]` lands on 307 — exactly Honda's own oscillating value.** V240 makes the normal curve as tight at
speed as Honda's own oscillation response already is. Like V192, this is **not a polarity gamble**.

---

## 🛑 What it actually is: a BROADBAND cut, not a targeted ratchet lever

I called this "the largest measured ratchet lever" last tick. Measuring it band by band, that
oversold it — and the correction matters, because it is **least** effective exactly where your
symptoms live:

```
  band              ratio     change     what lives here
  ratchet  6-9      0.9399     -6.0 %    the ratchet
  grind    9-15     0.8832    -11.7 %
  grind   15-22     0.9699     -3.0 %    V62's grinding band
  pump    22-40     0.8294    -17.1 %    (aliased from 52-71 Hz)
  ALL      1-50     0.8933    -10.7 %
```

**It is a rate limiter, so it cuts high frequency generally.** The lane loses 10.7% across the whole
band, and the ratchet gets 6.0% — *less* than average. The V62 grinding band gets 3.0%, less still.

Two things that stay true: **it never raises any band on any route** (max ratio is 1.000 everywhere),
and it is still the only cal in the path that does this without taking assist away. But it is a
broadband reduction in assist-lane high-frequency content, and the honest way to describe how that
might feel is **slightly duller, not obviously fixed**.

---

## What it measures

14 routes, the integer-exact firmware mirror driving real torque/speed/angle, Welch band power at 6–9 Hz:

```
  6-9 Hz band   0.9399   -6.0 %   range 0.813 .. 1.000
  assist p50    1.0000   +0.0 %   <- ordinary driving is UNAFFECTED
  assist p95    0.9469   -5.3 %   <- only the top of the assist demand pays
```

Against everything else measured this session:

| cell | what it is | measured at the ratchet |
|---|---|---|
| **`0xC693E`** | **the normal slew curve — V240** | **−6.0 %**, no median cost |
| `0xC6906` | the lag pole — V238 carries it | −3.8 % across its **whole** range |
| `0xC6384` | the slope cap — V236/V239 | **0.0 %**, withdrawn as inert |

**V240 is 1.6× the pole's entire reachable range, and it costs nothing at the median.**

**I tested the opposite direction too.** Removing the limiter entirely (gate duty → 0.00%) *raises*
band power by **2.8%** — the limiter is helping, and V240 makes it help more.

---

## V240 survives its own census

I then perturbed **every** cal the assist-map path reads, one at a time, and scored each on band power
*and* on delivered assist:

```
  cal                     scale   band 6-9  assist p50  assist p95
  gp-0x69a0 NORMAL         0.60     0.9126     1.0000     0.9469   <- V240
  CAL_7384  slope cap      0.60     0.9998     1.0000     1.0000
  CAL_7178 / 713C / 7200 / SPD_CAP_Y      1.0000 exactly, every dose
  CAL_7468                 1.40     0.3888     0.5192     0.6255
  BOOST_Y   angle boost    0.60     0.5698     0.6077     0.8092
  CAL_713A                 1.40     0.7185     0.7386     0.8742
```

**`gp-0x69a0` is the only one that reduces ratchet-band gain without taking assist away.** The other
three that move the band move assist with it — and worse than plain gain scaling would: band power goes
as gain², so `CAL_7468`'s 0.519 assist should give 0.269 band, and it gives 0.389. **They are the same
trade you rejected on V101, at a discount.**

Four cals are **completely inert** at ±40% — band ratio 1.0000 exactly. They are off every future list.

---

## What V240 changes, in full

**Against your car: 31 payload bytes.**

```
  0xC60A8/AC/B0/B4   the notch, re-aimed to the net-damping optimum      12 B   grinding
  0xC693E Y[0..3]    the NORMAL slew curve × Honda's 0.600                8 B   ratchet, -6.0 %
  0xC6906 Y[0..3]    the engaged lag pole, 20 -> 8                        8 B   ratchet, -2.7 %
  0xC40DC            alpha2 8 -> 22, which is Honda's own value           1 B   restores a damper
  0x55DF2            the biquad-state probe on CAN 427                    2 B   telemetry only
```

**Zero of 15 command-path and authority cells differ from your car.** V192's oscillating curve is left
byte-identical — V240 moves only the normal one.

---

## Honest limits

⚠ **A 6% lane-gain cut is not a promise of a 6% symptom cut.** What is measured is this lane's
contribution at the ratchet band. The step from there to *felt* ratcheting is the loop model, and that
model has been **wrong twice this session** — it oversold the slope cap as "3.4× more damped" when the
cell is inert, and it framed the lag pole as an additive branch when it is a blend. The direction here
rests on structure and on Honda's own behaviour, not on that model. The magnitude is a lane measurement.

⚠ **The hesitation risk is real and is the reason for the dose.** V192's card names it. V240 tightens
the always-live curve, so the warning applies with more force than it did to V192. **0.8× (`[286, 286,
369, 410]`) is the back-off rung** — but it measures only −0.5%, so it is a retreat, not a compromise.

**LKAS authority:** unchanged. There is still no authority lever on this shelf; the only EPS-side route
is the gain, which you rejected on V101.

**The probe still rides along:** the notch's state boots to `0.0f`, so if it reads identically zero the
filter never runs and the whole notch axis retires after 56 builds.
