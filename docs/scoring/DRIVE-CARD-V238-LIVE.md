# DRIVE CARD — V238

## 🚗 DRIVE THIS ONE

```
  V238   39990-TVA,A160-V238-V235BASE-ENGAGED.LAGPOLE.8.TIGHTEN-0x13000-0x100000.rwd
         rwd    sha256 e9faa7b461c6118b...      image sha256 34ceb5aefaa9bdd5...
  BEFORE anything: kill openpilot/pandad   ->  tmux kill-server
```

🛑 **The flash decision is yours. Name the file and the bus, and I will repeat both back before
anything happens.** Nothing is flashed without that.

**While driving — the whole job:** *does the car feel acceptable?* One episode is enough and **your
verdict is final.** If it feels wrong, **stop.**

**Stop and say so if:** the ratchet or stutter is clearly worse · the wheel feels heavier near centre
(V238 is built specifically *not* to do this) · steering feels soggy on a quick input · anything faults.

**Fallbacks:** **V235** → **V122** (your car).

---

## 🛑 Read this before you decide whether to drive at all

**I measured both levers in the lane this arc has been chasing, and both are tiny.** V236 and V239 are
**withdrawn** — their `.rwd` files are renamed `SUPERSEDED-DO-NOT-FLASH-…`.

```
  0xC6906  the lag pole    WHOLE range (k 20 -> 2)             3.8 %
  0xC6384  the slope cap   2048 -> 1536  (what V236/V239 did)  0.0 %   band ratio 1.0000
                           pushed to 256 (Honda ships 2048)    4.2 %
```

**`0xC6384` is inert because it is out of reach.** Lowering it moves only the **top X breakpoints** —
the `Y` values never change at all — and the lowest breakpoint that moves anywhere sits at **2844
torque counts**. Across 113,521 engaged frames on 25 routes, you are above that on **1.65%** of them.
The control: on a route whose torque never crosses 2844, the lane output is **bit-identical at every
dose down to 256**.

The cap's branch **never fires at any value Honda or this kit has shipped** — the map's natural maximum
slope is **0.350** against a cap sitting at **2.000**, 5.7× above anything the map reaches.

That also retires the number the record carried for this cell. *"Q ratio 14.29 → 4.26"* came from a loop
model that assumed the cap **scales the lane gain**. It doesn't — it relocates two breakpoints in a
region you barely visit.

**So V238 is what is left, and its ratchet content is honestly 2.7%.** That is not a fix. It is free,
it is real, and it rides along with the grinding work — but you should not expect it to solve the
ratchet, and I am not going to present it as though it might.

---

## What V238 changes, in full

**Against your car: 23 payload bytes.**

```
  0xC60A8/AC/B0/B4   the notch, re-aimed to the net-damping optimum      12 B   grinding
  0xC6906 Y[0..3]    the engaged lag pole, 20 -> 8                        8 B   ratchet, 2.7 %
  0xC40DC            alpha2 8 -> 22, which is Honda's own value           1 B   restores a damper
  0x55DF2            the biquad-state probe on CAN 427                    2 B   telemetry only
```

**Zero of 15 command-path and authority cells differ from your car.** This build cannot change how much
steering LKAS can ask for, in either direction.

---

## The honest case for driving it anyway

**The grinding work is the real content**, and it has a mechanism behind it that nothing before V229
had: Honda's biquad is a **55 Hz notch**, every build from V172 onward relocated it out of the band it
was cutting, and V235's geometry was chosen by net-damping optimisation and held up under
leave-one-route-out.

**And the probe settles the notch axis either way.** The filter's state boots to exactly `0.0f`:

- **reads identically zero** → it never executes, and the whole notch axis retires after 56 builds
- **reads non-zero** → it runs, and how hard it works becomes measurable for the first time

---

## Where the ratchet search stands

The loop census called this lane the **largest** torque-fed term — 5.8–7.8× the entire PID at 7.79 Hz.
Its two calibrations together yield **at most ~4%** across their entire ranges.

**Whatever sustains the ratchet is not reachable through this lane's cals.** That is a real result, and
it is the most useful thing this tick produced: it closes a lane the kit would otherwise have kept
grinding at, and it says the search has to move — to another lane, or to something that is not a
calibration at all.

**LKAS authority:** unchanged, and there is still no authority lever on this shelf. The only EPS-side
route is the gain, which you rejected on V101.
