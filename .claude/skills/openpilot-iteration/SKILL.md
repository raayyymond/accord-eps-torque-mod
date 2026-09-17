---
name: openpilot-iteration
description: The development philosophy for iterating on the openpilot/StarPilot lateral control fork — where control belongs, what makes a change worth shipping, how to judge one honestly, and how to be wrong well. Load before proposing, simulating, or shipping any fork-side control change.
---

# How we develop the fork

## Where control belongs

- **The EPS firmware is a pure torque map; control lives in openpilot.** Firmware changes are the only
  bricking class this kit has — keep them minimal and prefer a fork-side answer.
- **Do not move control back into the firmware** to buy bandwidth. If an inner loop is ever justified,
  close it on angular **velocity**, not acceleration.

## What is worth shipping

- **Elegant and efficient, not merely robust and accurate.** Every term costs lag and a tuning surface;
  one that cannot say what it buys does not ship.
- **Prefer removing a term to adding one, and correcting a constant to either.**
- 🛑 **Gate a feature; do not delete it to chase a symptom.** The fault is usually *where it was
  applied*, not *that it exists*.
- **A new build is not progress — an interpretable result is.** Each one spends a scarce drive.
- **Ship with the instrument that can see the change, and the one toggle that takes it back.**

## How to judge a change

- **Measure the quantity the goal names**, in the band and at the amplitude where it lives — a proxy
  will rank candidates confidently and wrongly.
- ⭐ **A metric that cannot separate the arms is our design failure, not a verdict on the arms.**
- **Write the fail condition before the run and honour it when it fires.** A threshold with no physical
  floor gets that floor stated before the sweep, never after.
- **Validate an instrument on a known answer first** — a method can pass its own checks and still be
  wrong by an order of magnitude.
- **Prefer the inert tap to the blind dose**, and **verify the crux yourself, including a "no"**.

## How to be wrong well

- **Mark EVIDENCE or BELIEF on every decision-bearing claim.** "I'm not sure, here's what I'd need" is
  always acceptable.
- **Retract in place and loudly** — commit, handoff, page. A correction living only in chat sends the
  next session down the same path.
- **An identical result across a swept parameter means the wrong mechanism**, not a weak effect.
- **A deliberate under-correction is still a modelling error** — it relocates the error somewhere less
  visible rather than creating margin.

## Working with the operator

- **He scores symptoms; we score bands.** Report what moved, in his words, against the pre-registered read.
- **State the risk before the drive** — what gained authority, by how much, and where.
- **His overrides are data.** Re-examine the reasoning that produced the change, not just the line.
