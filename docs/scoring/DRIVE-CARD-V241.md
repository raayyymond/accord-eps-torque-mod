# DRIVE CARD — V241

## 🚗 DRIVE THIS ONE

```
  V241   39990-TVA,A160-V241-V235BASE-NOTCH.IMU.29.75-22.50-0.940-0x13000-0x100000.rwd
         rwd    sha256 57d240d77f568aac...      image sha256 2ef7eb8eb2417905...
  BEFORE anything: kill openpilot/pandad   ->  tmux kill-server
```

🛑 **The flash decision is yours. Name the file and the bus, and I will repeat both back before
anything happens.** Nothing is flashed without that.

**While driving — the whole job:** *does the car feel acceptable?* One episode is enough and **your
verdict is final.** If it feels wrong, **stop.**

**Stop and say so if:** the ratchet or stutter is clearly worse · a new higher-pitched noise appears ·
the wheel feels heavier near centre · anything faults.

**Fallbacks:** **V235** (V241 minus 12 bytes) → **V122** (your car).

---

## What changed, and why it is worth a drive

**V241 is V235 with the notch re-aimed — twelve bytes, nothing else.** The reason is that V235's
geometry was fitted to a **CAN objective**: the EPS's own channels, the same subsystem the build
modifies. The comma's IMU is physically separate and had no part in choosing it.

Asked the open question — *at which frequencies does engagement raise chassis motion above what the
road explains?* — the IMU names **22–30 Hz** as the largest engagement-created band in the whole
3–45 Hz range, peaking at **25–26 Hz**. **V235's band is right.** Its shape is not:

```
  V235   zero 25.00 Hz  pole 23.50 Hz  r 0.960   cost 0.43254   min|H| 6-15 = 0.9108
  stock  zero 55.23 Hz  pole 42.35 Hz  r 0.797   cost 0.57508   min|H| 6-15 = 0.9344
  V241   zero 29.75 Hz  pole 22.50 Hz  r 0.940   cost 0.31079   min|H| 6-15 = 0.9374
```

**V241 removes 28 % more of the measured engagement excess than V235 — and cuts *less* of the band
that damps.** V235 sat at 0.9108 there, slightly **below Honda's own floor**; V241 is back above it.

**It survives leave-one-route-out on all ten routes** — 29.75 / 22.50 / 0.940 wins every fold, one
distinct winner in ten. It is not fitted to any single route.

Both gates are recomputed from the written bytes, and both are the record's own bars, not mine:
**max|H| = 1.0000** (the lineage bar — V194–V198 were pulled for 1.35–1.72) and **min|H| over 6–15 Hz
= 0.9374 ≥ stock's 0.9344**, because the lane is measured *damping* there.

**And it is not fitted to the median car.** Re-searched under five other ways of combining the routes
— mean, geometric mean, worst-route, p75 — the winner is the same geometry every time. The only
weighting that prefers V235's 25 Hz is a **flat** one, i.e. the objective that ignores the measurement
and just aims at the middle of the band. That is precisely the difference between the two builds.

## 🛑 The honest ceiling on this build

The notch is optimised against **chassis motion**, but it filters a **torque lane**. Running the same
measurement on the torque channel shows the two domains do not agree at all:

```
  band            TORQUE     IMU
  ratchet 6-10     2.849   1.516    <- torque peaks here
  mid    10-15     0.946   1.547
  grind  15-22     1.245   1.621
  V241   22-30     1.337   2.481    <- motion peaks here
  upper  30-45     1.052   1.575

  agreement across 3-45 Hz:  spearman rho = +0.040, p = 0.61  -- none
```

**In torque, engagement's biggest effect is the ratchet band, and V241's band is nearly the weakest.**
So both V241 and V235 are aimed by a spectrum that is not the lane's own. V241 is still the better of
the two -- it beats V235 on the motion objective and respects Honda's damping floor, which V235 did
not -- but **expect less from either than the previous two cards implied.**

The bind is now explicit: in the domain the notch can reach, the band worth filtering is **6-10 Hz**,
and that is exactly the band the record forbids touching because the lane damps there. That is not a
gap in the analysis; it is the shape of the problem.

---

⚠ **What is NOT claimed:** that 28 % of modelled cost is 28 % less grinding. The weight is chassis
**motion**; the notch filters a **torque** lane. This is a better-founded aim than the one V235 had, not
a promise.

---

## Why the grinding side is the one worth attacking

### The ratchet, and why it is not the target

**V238 and V240 were built as ratchet levers. On the kit's own phase measurement, both make the
ratchet slightly worse.** Their `.rwd` files are renamed `RATCHET-COST-DO-NOT-FLASH-FIRST-…`.

The kit measured `gp-0x6b86` — the lane both builds cut — against wheel rate on three routes:

```
  band     median cos   verdict    routes
  6-9        -0.918     DAMPING    all 3 agree
  9-12       -0.989     DAMPING    all 3 agree     <- near-perfect damping
  12-15      -0.629     DAMPING    all 3 agree
  15-22      +0.551     pumping    routes DISAGREE
  22-30      +0.936     PUMPING    all 3 agree
```

That record's own instruction is explicit: **"place a notch only where the lane PUMPS. Never notch
6–15 Hz on this lane."**

And that is what V238 and V240 do — not with a notch, but with a rate limiter:

```
  V240's cut, band by band:   6-9  -6.0 %      9-15  -11.7 %      15-22  -3.0 %
```

**They remove the most damping exactly where the lane damps hardest.** Separately, the aggregate `Re(Z)`
at 6–9 Hz is measured anti-damping on stock at every speed — so this lane is one of the things
*offsetting* Honda's anti-damping, and cutting it makes the net worse.

I presented V240 as "the largest measured ratchet lever" two ticks ago. It is the largest measured
**broadband** lever, and at the ratchet it points the wrong way.

---

## What V235 is

**Against your car: 15 payload bytes — the smallest build in this arc.**

```
  0xC60A8/AC/B0/B4   the notch, re-aimed to 25.0 / 23.5 / 0.96              12 B   grinding
  0xC40DC            alpha2 8 -> 22, which is Honda's own value              1 B   restores a damper
  0x55DF2            the biquad-state probe on CAN 427                       2 B   telemetry only
```

**Its notch sits at 25.0 Hz — inside the band where all three routes agree the lane PUMPS (cos +0.936).
That is exactly where the rule says a notch belongs**, and its gain at the ratchet is 0.9879, so it
barely touches the damping bands at all.

**Zero of 15 command-path and authority cells differ from your car.**

---

## Its notch band is verified real, not an alias

The evidence placing this notch at 25 Hz came from CAN at ~101 Hz, where **22-30 Hz could have been
folded from 71-79 Hz** - the notch aimed at a ghost. The 16 kHz audio spectra settle it, on the same
three routes the placement was measured on:

```
  route      P(20-32)     P(69-81)    ratio
  ra4       3.582e+05    1.443e+05     2.48
  ra5       3.345e+05    1.152e+05     2.90
  ra6       3.839e+05    2.166e+05     1.77
  median over 13 routes                2.34   (all > 1)
```

**Real energy in the band beats its alias source ~2.3x on every route.** The notch is aimed at something
that is actually there.

⚠ At that ratio the fold still supplies about **30%** of the CAN band power - so the *direction* is
sound and any *magnitude* from that band carries a 30% contamination.

---

## Its notch band is the largest engagement effect on the car

The alias check said the band is real. A second, independent instrument now says it is also the
**biggest** thing engagement does. The comma's IMU is physically separate from the EPS and had no part
in choosing this notch:

```
  band          Hz     median   p25..p75   routes>1
  ratchet     6-10      1.496   0.96..2.12    45 %
  mid        10-15      1.696   1.05..3.59    47 %
  grind      15-22      1.621   1.14..2.18    64 %
  V235 notch 22-30      2.481   2.16..5.01    67 %   <-- largest
  upper      30-45      1.575   1.34..2.04    63 %
```

Per-bin, the peak is at **25-26 Hz** — where the notch sits — and it is about **1.7x the ratchet
band**, which is the weakest of the five.

The same instrument also ranked **V88**, the kit's one measured grinding fix, **near-best for grinding
and near-worst for ratchet** — a prediction written down before the answer was read. So the grinding
metric this build was tuned against measures something real.

⚠ The IMU measures motion; the notch filters a torque lane. This makes the placement well-founded, not
proven.

---

## What the probe settles either way

The notch filter's internal state boots to exactly `0.0f`. If its enable never fires on the car, that
state stays zero for the whole drive.

- **reads identically zero** → the filter never executes, and the whole notch axis retires after 56
  builds of moving it around
- **reads non-zero** → it runs, and how hard it works becomes measurable for the first time

---

## Where the ratchet search actually stands

This tick closed the last open avenue, and the result is a negative worth stating plainly:

- **Every cal in the assist-map path is measured.** Only `gp-0x69a0` moves the band without taking
  assist away — and it is broadband, so it cuts damping and pumping alike.
- **The biquad is the only frequency-selective device in the chain.** It *can* put a true null at
  7.79 Hz — but aiming it there would null a lane the kit measured as damping, which its own record
  forbids in as many words.
- **So there is no ratchet-selective lever available in calibration.** Every remaining cal lever is
  broadband gain reduction, which is the trade you rejected on V101, arriving through different cells.

**The ratchet is not reachable by calibration.** That is the honest state after this arc, and it means
the next real step is not another cal build — it is finding what *creates* the anti-damping, which the
stock baseline says is Honda's and present at every speed before we touch anything.

**LKAS authority:** unchanged, and there is still no authority lever on this shelf.
