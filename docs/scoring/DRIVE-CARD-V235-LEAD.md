# DRIVE CARD — V235

## 🚗 DRIVE THIS ONE

```
  V235   39990-TVA,A160-V235-V234BASE-C63AE.BACK.TO.HONDA.1024-0x13000-0x100000.rwd
         rwd    sha256 8b418939011854b5...      image sha256 399424fd8b032669...
  BEFORE anything: kill openpilot/pandad   ->  tmux kill-server
```

🛑 **The flash decision is yours. Name the file and the bus, and I will repeat both back before
anything happens.** Nothing is flashed without that.

**While driving — the whole job:** *does the car feel acceptable?* One episode is enough and **your
verdict is final.** If it feels wrong, **stop.**

**Stop and say so if:** the ratchet or stutter is clearly worse · a new higher-pitched noise appears ·
the wheel feels heavier near centre · anything faults.

**Fallback:** **V122** (your car).

---

## 🛑 Why the lead moved back to V235

**I built V238 and V240 as ratchet levers. On the kit's own phase measurement, both make the ratchet
slightly worse.** Their `.rwd` files are renamed `RATCHET-COST-DO-NOT-FLASH-FIRST-…`.

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
