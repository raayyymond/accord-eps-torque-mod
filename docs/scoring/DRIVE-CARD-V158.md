# DRIVE CARD — V158

**Flash:** `39990-TVA,A160-V158-V122BASE-DAMPER.GOLDENMODEL.SHAPE-0x13000-0x100000.rwd`
in `../accord-firmwares/flashing-2020accord/rwd/`.
**Before flashing:** kill openpilot — `tmux kill-server` on the comma device.

**What changed vs V122:** the base-assist damper now delivers at creep. Stock and every previous
build deliver **exactly zero** damping below ~35 km/h. Nothing else moved.

---

## The one thing that matters

🛑 **THE MANUAL CREEP PASSES ARE WHAT HAVE ALWAYS BEEN MISSING.** Measured across all 23 cached
routes: engaged creep episodes run 9–22 and are never the limit; **manual creep episodes run 3–7 and
are the limit on every single scoreable route**, and 13 of 23 routes have no matched creep arms at
all. Only **one route in 23** ever resolved the 6–9 Hz band — and it is the one with the most manual
episodes. **8+ separate manual creep passes will do more for this drive than any amount of extra
engaged driving.**

⚠ **Expect the band scorer to say NOT RESOLVED.** That is the measured noise floor, not a failure.
**Your report is the primary endpoint and on most drives it is the only one.**


🛑 **V158 is architecturally inert above ~35 km/h.** A highway drive tests **nothing**.
The whole result lives in **engaged creep, 2–8 km/h, with the wheel actually moving.**

🛑 **RECORD AUDIO.** Only 5 of ~230 routes have usable creep-engaged audio, and the bus instrument
has been shown not to track what you hear.

---

## Drive order

🛑 **ALTERNATE, DO NOT DO ONE LONG BLOCK OF EACH.** Validated on r24: a drive with 10 engaged and
5 manual *stretches* **could not resolve the 6-9 Hz band at all** — and 6-9 Hz is exactly what V158
targets. The statistic resamples **episodes**, so **8+ separate engaged passes and 8+ separate manual
passes** are needed. More minutes in one block does **not** help; more separate passes does.

**1. Engaged creep — the main event. 5+ minutes, in SEVERAL separate passes.**
2–8 km/h, LKAS engaged, hands off, with real steering activity — a car park, a slow residential
loop, anything that makes the wheel work at walking pace. This is the only segment that can produce
a result.

**2. The same creep, LKAS OFF. 2+ minutes, in SEVERAL separate passes.**
🛑 **SAME STRETCH, SAME SPEED.** Not “some creep engaged and some creep manual” — tested on r24, which has creep audio in BOTH arms and the acoustic contrast was **still refused** because the arms sat **2.43 km/h** apart. Drive the identical loop at the identical pace, engaged, then manual, and alternate.
Same speeds, same surface, hands off where safe. Without this every ratio is uncontrolled — three
uncontrolled ratios collapsed under controls this session (2.8→1.12, 1.29→0.911, 1.309→0.958).

**3. One slow hard turn, hands off, engaged.**
The peak-command-oscillation case. Roughly 40–45 km/h through a tight turn.

**4. A few minutes of 15–40 km/h engaged.**
The band you have previously reported grinding in.

---

## What to tell me afterwards — this is the PRIMARY result

The standing rule is *score bands, let the operator score symptoms*. Three questions, each **vs V122**:

**1. Ratcheting / stuttering at creep** — better, same, or worse? **At what speed?**

**2. Grinding** — better, same, or worse? **At what speed?**

**3. Steering effort at parking speeds** — heavier, same, or lighter?
⚠ **This one is not optional.** The damper *is* drag. If the ratchet improves but the wheel feels
heavier when parking, that is the expected trade and I need to hear it — the answer is a lower dose
(V164 is already built), **not** abandoning the lever.

Rough is fine. "Better but noticeably heavier below 5 km/h" is a complete answer.

---

## What happens next, decided in advance

| what you report | next build | already built? |
|---|---|---|
| ratchet better, effort fine | **V160** — adds the r24 increment | ✅ |
| ratchet better, wheel too heavy | **V164** — dose 50 → 27, halves the drag | ✅ |
| ratchet unchanged, effort unchanged | **V165** — dose 50 → 65 | ✅ |
| ratchet worse | **V167** — `0xC63A0` 1024→512, NOT a bare revert | ✅ |
| no real creep in the drive | re-drive — the edit is inert above 35 km/h | — |

---

## Predicted effect, committed before the drive

Creep viscous damping goes from **0.000** to somewhere in **1.05-1.96 ct/(deg/s)**, on top of a
measured 1.571 already present -- a total of **2.63-3.53**, i.e. **x1.7 to x2.7**, and the first
non-zero damping this car has ever had at creep.

⚠ **Why a range, not x2.74.** The nominal Path-1 figure is 2.733 (x2.74), but the same cell also
enters a second aggregator with an inverted sign. A stability argument bounds that pumping copy to at
most 0.61x the damping, so the net is 39-100 % of nominal. **It does NOT cancel the damping.**

⚠ **What that buys is still uncertain.** This is the *firmware-side* increment. If the firmware's
viscous term dominates the plant's damping, ζ would rise roughly in proportion. If mechanical damping
dominates, less. **The drive is what settles it** -- that is the whole point.


Full pre-registration: `docs/scoring/SCORING-V158-preregistered.md`.

---

## After the drive — the three commands

```
python rlog-tools/decode/extract_route.py --route <N> --prefix <rlog prefix> \
       --segments <n> --build V158
python rlog-tools/score/score_v158_creep.py r<N>
python rlog-tools/decode/audio_creep_v158.py r<N>
```

Step 1 tells you immediately whether the drive is scoreable at all — whether both arms have enough
creep windows, and enough separate episodes. If it says NOT SCOREABLE, the answer is another drive
with more alternation, not more analysis.

Step 2 prints a **split-half null** beside every band. A band is only reported RESOLVED if the effect
lies outside that null. **"NOT RESOLVED" means cannot resolve — it does NOT mean unchanged.**

Step 3 is the channel that has historically tracked your report when the bus did not.
