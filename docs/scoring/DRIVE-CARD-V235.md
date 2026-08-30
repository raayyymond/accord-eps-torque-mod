# DRIVE CARD — V235

## 🚗 AT THE CAR

```
  FILE   39990-TVA,A160-V235-V234BASE-C63AE.BACK.TO.HONDA.1024-0x13000-0x100000.rwd
  rwd    sha256 a6a58fa9ce11a0fa...        image sha256 ad6d485eefb2f6bc...
  BEFORE anything: kill openpilot/pandad   ->  tmux kill-server
```

🛑 **The flash decision is yours. Name the file and the bus, and I will repeat both back before
anything happens.** Nothing is flashed without that.

**While driving — the whole job:** *does the car feel acceptable?* One episode is enough and **your
verdict is final.** If it feels wrong, **stop** — that is a complete result, and no measurement
overrides it.

**Stop and say so if:**
- the **ratchet or stutter is clearly worse** than your car
- a **new higher-pitched noise** appears — this is now measured as UNLIKELY, so if it happens it is important: say so
- anything faults, or the EPS lamp lights

**Fallbacks in order:** **V234** → **V233** → **V122** (your car).

---

## 🛑 V236 EXISTS NOW, AND IT IS THE FIRST BUILD AIMED AT BOTH SYMPTOMS

```
  V236   39990-TVA,A160-V236-V235BASE-ASSISTMAP.SLOPECAP.1536.RATCHET-0x13000-0x100000.rwd
         rwd 25646ed45da588e0...     image 509785673468a346...
       = V235 + ONE cell: 0xC6384  2048 -> 1536
```

I found a ratchet lever that was worked out, gated and built as **V168 last year — and never flown.**
Every build since reverted the cell, including all of mine. That is the same silent loss that put
Lever B 2.5× off its optimum.

The work behind it: the ratchet is **in torque, not wheel rate**; **engagement creates it** (19.9×
speed-matched, engaged 7/7 vs manual 0/7); **nothing in thirty builds has moved it** while the grind
fell steadily — so the two symptoms are different problems. The base power-assist map is the largest
torque-fed term, 5.8–7.8× the entire PID, and its slope cap holds the small-signal gain at exactly
2.000. Lowering it to 1.500 predicts **3.4× more damping**, and because the term is a real gain the
change is **monotone with no reversal at any value** — the property the notch work never had. It
**cannot touch LKAS**: the clamp feeding it is 0 on all 161 images, so the map sees only your torque
sensor.

⚠ **It does the thing you told me not to do, and here is the size of it — measured, not estimated.**
The cap binds only over the first 100 counts of driver torque, and across 13 routes and 878,000 engaged
samples that is **34.2 % of your engaged driving**:

```
  0-25   9.8 %  |  25-60  12.4 %  |  60-100  12.0 %   <- assist reduced here, 34.2 % total
  100-150 13.5 % |  150-250 21.4 %  |  250-450 11.5 %   <- untouched
```

Your median steering torque is 128–226 counts, so **normal cornering is above the capped region and
unaffected** — the cost falls on **near-centre, small-correction steering**, which is where added
effort is most noticeable. The absolute size is modest, since the cap already clips those segments'
raw slopes (6.16 / 5.26 / 3.05) down to 2.000 and V236 takes that to 1.500.

**It is your feel, not LKAS** — the map is fed by the torque sensor alone, proven by `0xC616C` = 0 on
all 161 images. The cap sets small-signal gain, so this is **25 % less
assist at small steering inputs — more effort.** Your standing instruction is *"Increasing mass and
friction should not be our primary approach to resolving the ratcheting… We want both."* This is the
only gated ratchet lever this kit has ever produced, and it costs exactly that. **It does not cost
angular velocity or acceleration** — no rate or authority cell moves — but it will feel heavier at
small inputs, and whether that trade is acceptable is yours to decide, not mine to bury.

**V235 remains the no-added-effort option.** V236 is V235 plus that one cell, so the pair also isolates
it exactly.

---

## What V235 is: your car, plus three things

**15 payload bytes.** Every other cell is byte-identical to what you drive today — verified by diffing
the built image against your car, not asserted.

```
  0xC60A8/AC/B0/B4   the notch, re-tuned to the net-damping optimum   12 B
  0xC40DC            alpha2  8 -> 22, which is Honda's own value       1 B
  0x55DF2            the biquad-state probe on CAN 427                 2 B   telemetry only
```

**1. The notch.** Your ECU has exactly one filter cell. Honda centres it at 55 Hz. Measuring that
filter's own lane on three flown routes showed it **damps below 15 Hz and pumps above 22 Hz**, with the
pumping power concentrated at 19–26 Hz — so a notch belongs there, and Honda's cuts that band only
1.51×. V235's geometry was chosen by optimising against that measurement:

```
  net damping vs your car    6-9      9-12    12-15    22-30    30-40   damping  pumping
  V235                     1.004x   1.000x   0.891x  -0.050x  -0.888x   0.965x  -0.469x
```

**It leaves the damping at your ratchet frequency intact and turns both pumping bands into damping.**

**2. `0xC40DC`.** 22 is Honda's shipped value; your car's 8 is the modified one. That cell feeds
`gp-0x6b26`, which the record calls *"a REAL 6–9 Hz DAMPER"*. Your 8 attenuates that damper to 0.782×
at 18.5 Hz — it removes damping. Restoring 22 gives it back.

**3. The probe.** No control effect. It puts the filter's internal state on CAN 427, which answers a
question 56 builds never asked.

---

## What the probe settles, whatever else happens

The filter's state boots to exactly `0.0f`. If its enable never fires on the car, that state stays zero
for the whole drive.

- **reads identically zero** → the filter never executes, and **the entire notch axis is dead** — which
  would explain 56 builds of nothing, and retire it for good
- **reads non-zero** → it runs, and how hard it works becomes measurable for the first time

---

## How well this generalises — cross-validated, and one route disagrees

The notch geometry was chosen by optimising against measurements from three flown routes. Holding each
one out in turn:

```
  trained without   picks geometry        held-out score vs Honda
  ra4               25.0 / 23.5 / 0.96    ra4:  +0.097  V235 better
  ra5               25.0 / 23.5 / 0.96    ra5:  +0.075  V235 better
  ra6               25.0 / 23.5 / 0.96    ra6:  -0.010  Honda better
```

**The filter itself is not fitted** — every fold picks the same geometry, so no single route is driving
the choice. One route, ra6, scored it below Honda — **and that turned out to be a fault in the test,
not in the build.** ra6 ran a different filter of its own whose notch erases the 22–26 Hz band, which
is exactly the band this design is about; it was being asked to judge an effect it cannot see.

**Re-derived on the one route that carries Honda's filter angles (ra4, 100 % of the band usable), the
optimum comes out as V235's geometry byte for byte, and beats Honda by 36 %.** V235 wins on two of
three routes by about ten times the margin it loses by on the third, so the average clearly favours it —
**but the advantage is not uniform, and three routes is too few to put an interval on it.**

That is a reason to drive it and watch, not a reason to skip it — and it is one more thing your verdict
settles that the data cannot.

---

## Confirmed on a second route, through a second signal

The filter's lane is only one of about six that sum together before reaching the motor. So the lane
pumping at 19–32 Hz was necessary but not sufficient — if the other lanes cancelled it at the sum,
notching it would buy nothing you could feel.

**r95 answers that.** It ran Honda's filter byte-for-byte and taps the *aggregator* rather than the
lane:

```
  band     the SUM (r95)      the LANE (ra4)
  6-9      -0.918  78% pwr    -0.879     <- damping dominates the ratchet band
  19-22    +0.609   coh 0.93  +0.625
  22-26    +0.791   coh 0.97  +0.826     <- where V235 cuts
  26-32    +0.964             +0.994

  sign agreement: 7 of 8 bands
```

**The sum pumps at 19–32 Hz with coherence up to 0.97** — the other lanes do not cancel it, so cutting
there reaches the motor. And 78 % of the sum's power sits at 6–9 Hz in strong damping, which V235
leaves at 1.004×.

---

## The cost — measured, and it is smaller than I thought

V235 raises 55 Hz by ~143× versus Honda's cut, and one filter cell cannot notch both 25 Hz and 55 Hz.
I flagged that as the build's one real cost. **It has now been measured, and it is negligible.**

The trick is that CAN's sampling folds 52–71 Hz down into 30–49 Hz, and two of the measured routes
differ in exactly the right way: **ra4 ran Honda's notch (55 Hz cut 121×), ra5 ran a 25 Hz notch that
passes 55 Hz** — same lane dose otherwise. If the lane carried real energy up there, ra5's folded band
would exceed ra4's.

```
  excess in the folded band, ra5 - ra4  =  -0.05 % of total power
```

**There is essentially no energy at 52–71 Hz in this lane**, so Honda's notch there is removing almost
nothing, and V235 gives back almost nothing.

⇒ **The 50–72 Hz noise the audio does show is not coming from the lane this build touches.** It comes
from somewhere else, and V235 will not make it louder. If you hear a new high-pitched noise anyway,
that is genuinely informative — it would mean the lane model is wrong somewhere.

*(Two routes, and the two folded sub-bands scatter in opposite directions; the total is what licenses
this, not either half alone.)*

---

## Against the three things you asked for

You asked for grinding, LKAS authority, and peak command oscillation. **V235 is aimed at two of them
and does nothing for the third.** Rather than leave that to be inferred:

**Grinding / ratcheting — addressed.** The notch cuts the band that both the lane and the aggregate
pump in, while leaving the damping at your ratchet frequency at 1.004×.

**LKAS authority — untouched, verified cell by cell.** All 15 command-path and authority cells read
identical to your car: the gain, both forward clamps, the gate byte, both ±8192 rails, Lever B, the
r26 arm, the input span, the lockout, the fault interlock, the rate limiter and the governor cal.
**Zero differ.** So this build will not change how much steering LKAS can ask for, in either direction.

And the obvious lever for authority is one you have already rejected: raising the gain does buy it
back, but **you flew 8× as V101 and reported grinding and vibration at all speeds**, then chose 6×
yourself. Authority has to come from somewhere other than the gain.

**Peak command oscillation — the premise did not survive testing, but V235 acts where the effect
actually is.** Both readings of it that this bus can observe were tested against controls and neither
held: the "command reverses after a peak" reading gives a correlation of +0.099 (p=0.188) with two of
five routes going the wrong way, and the "oscillates while the command is large" reading **reverses** —
roughness *falls* as the command grows. The roughness is a **small-command** phenomenon. A filter is
linear, so V235's notch works identically at every command size, including the small ones where the
roughness lives.

---

## What each outcome means

| you report | what it settles |
|---|---|
| **better** | the pumping at 19–26 Hz was the mechanism, and optimising against the lane measurement works — the method is validated, not just this build |
| **worse, new high noise** | the 55 Hz cut matters more than the pumping does; fall back and the notch stays at Honda's placement permanently |
| **worse, same character** | the notch is not where your symptom lives — and the probe tells us whether it even ran |
| **no change** | if the probe reads non-zero, the filter runs and does not matter ⇒ **the whole notch axis retires after 56 builds** |

**Every one of those is a result.** There is no outcome here that wastes the drive.

---

## The paired arms, if you want to isolate a cell

Each pair differs by **two bytes**, so driving both attributes the difference exactly:

| pair | isolates |
|---|---|
| V235 vs **V234** | `0xC63AE` (soft relay small-signal gain, 1024 vs 512) |
| V234 vs **V233** | Lever B (5244 vs 13107) |

You do not need these to drive V235. They exist so that if something changes, we can say *which cell
did it* rather than guessing.

---

## What is not in this build, and why

- **Lever B stays at 5244** — your value, and V88's. The record brackets it on both flanks: below it
  *"made it WORSE"*, above it was **the worst build ever recorded on all three symptoms**. Every build
  V221–V233 carried 13107; that was a mistake of mine and it is out.
- **`0xC63AE` stays at 1024** — Honda's and yours. The 512 that every build since V206 carried is
  **unpriced**, and the opposite direction is already NO-GO for a gain that *reverses* across your
  amplitude range.
- **No cave change.** The 164-byte cave is byte-identical, so this is not the bricking class.
