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
- a **new higher-pitched noise** appears — expected, see the cost below, but say so anyway
- anything faults, or the EPS lamp lights

**Fallbacks in order:** **V234** → **V233** → **V122** (your car).

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

## The cost, plainly

**55 Hz runs ~143× louder than Honda's cut.** One second-order section cannot notch both 25 Hz and
55 Hz — that is structural, not a tuning choice, and any geometry that cuts the pumping pays it. The
audio does show LKAS-caused excess at 50–72 Hz, so **if a new higher-pitched noise appears, that is
where it comes from.**

The counter-argument, which is why it is still worth driving: **Honda's 55 Hz cut is on your car today
and has not stopped the grinding**, while the band the lane demonstrably pumps into was left cut only
1.51×.

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
