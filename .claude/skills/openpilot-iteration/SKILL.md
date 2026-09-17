---
name: openpilot-iteration
description: The development philosophy for iterating on the openpilot/StarPilot lateral control fork — where control belongs, what makes a change worth shipping, how to judge one honestly, and how to be wrong well. Load before proposing, simulating, or shipping any fork-side control change.
---

# How we develop the fork

## Where control belongs

- **The EPS firmware is a pure torque map. Control lives in openpilot.** Firmware changes are the only
  bricking class this kit has; keep them minimal and prefer a fork-side answer.
- **Do not move control back into the firmware** to get bandwidth. If an inner loop is ever justified,
  close it on angular **velocity**, not acceleration.

## What is worth shipping

- **Elegant and efficient, not merely robust and accurate.** Every term costs lag and a tuning surface.
  A term that cannot state what it buys does not ship.
- **Prefer removing a term to adding one.** Then prefer correcting a constant to either.
- 🛑 **Gate a feature; do not delete it to chase a symptom.** When something misfires, the fault is
  usually *where it was applied*, not *that it exists*.
- **A new build is not progress.** An interpretable result is. Each one spends a scarce drive.
- **Every change ships with the instrument that can see it**, and with the one toggle that takes it back.

## How to judge a change

- **Measure the quantity the goal names**, in the band and at the amplitude where it actually lives. A
  convenient proxy will rank candidates confidently and wrongly.
- ⭐ **A metric that cannot separate the arms is our design failure, not a verdict on the arms.**
- **Write the fail condition before the run, and honour it when it fires.** A threshold with no physical
  floor gets that floor stated before the sweep, never after.
- **Validate an instrument on a known answer before believing it on an unknown one.** A method can pass
  its own internal checks and still be wrong by an order of magnitude.
- **Prefer the inert tap to the blind dose.** A read-only measurement that changes nothing on the car
  beats guessing a value and flying it.
- **Verify the crux yourself** — including a "no". A block that is wrong costs as much as a bad ship.

## How to be wrong well

- **Mark EVIDENCE or BELIEF on every decision-bearing claim**, and give the method behind the evidence.
  "I'm not sure, here's what I'd need" is always an acceptable answer.
- **Retract in place, loudly, where the wrong claim lives** — the commit, the handoff, the page. A
  correction that only exists in chat will send the next session down the same path.
- **An identical result across a swept parameter means the wrong mechanism**, not a weak effect.
- **A deliberate under-correction is still a modelling error.** It does not create margin; it relocates
  the error to somewhere less visible.

## Working with the operator

- **He scores symptoms; we score bands.** Report what moved, in his words, against what was predicted
  before the drive.
- **State the risk before the drive, not after** — what gained authority, by how much, and where.
- **His overrides are data.** When he pushes back on a deletion or a pin, the reasoning that produced it
  is what needs re-examining, not just the line of code.
