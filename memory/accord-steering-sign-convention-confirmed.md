---
name: accord-steering-sign-convention-confirmed
description: "OPERATOR-CONFIRMED, 2026-08-13 — negative driver torque and negative steering angle = a RIGHT turn, and the LKAS command's sign convention is OPPOSITE to driver torque's. Never confirmed before this date."
metadata: 
  node_type: memory
  type: reference
  originSessionId: fa9eb530-c732-4c40-8991-98e824e54a49
  modified: 2026-08-13T06:23:28.618Z
---

🛑🛑 **OPERATOR-CONFIRMED SIGN CONVENTION, 2026-08-13. He said: *"This has never been confirmed
until now. Make sure to remember this finding."*** Verbatim, so nothing is lost in paraphrase:

> *"FACT: negative driver torque and steering angle correspond to a right turn. Also, LKAS command
> demands torque in an opposite direction to driver torque. That is + LKAS demands negative steering
> angle. + driver torque demands positive steering angle."*

## The convention, stated as a table

| quantity | POSITIVE means | NEGATIVE means |
|---|---|---|
| **steering angle** | LEFT | **RIGHT** |
| **driver torque** (`STEER_TORQUE_SENSOR`) | driver pushing toward **LEFT** (+angle) | driver pushing toward **RIGHT** |
| **LKAS command** | demands **NEGATIVE** angle ⇒ **RIGHT** | demands **positive** angle ⇒ **LEFT** |

⇒ 🛑 **A POSITIVE LKAS COMMAND AND A POSITIVE DRIVER TORQUE PUSH THE WHEEL IN OPPOSITE PHYSICAL
DIRECTIONS.** The two signals do **not** share a frame. Any analysis that correlates, differences,
compares or co-plots LKAS command against driver torque **without a sign flip on one of them is
measuring the negative of what it thinks it is measuring.**

## Why this matters enough to be a memory

This kit has been inverted before, twice, decision-bearingly:
- `scipy.signal.csd(x,y)` returns `arg(Y)−arg(X)`; an agent labelled every cross-spectrum backwards
  and recommended **lowering** `0xC63AC` when the correct move was raising it. Caught only because an
  independent `Q` measurement disagreed by a replicated ~90°.
- V94 reached the car on a lever whose sign was unresolved, and **regressed the car so badly the
  operator aborted the drive.**

A frame mismatch between the command and the driver-torque channels is the same class of error, and it
sits underneath **every** engaged-vs-manual contrast the kit has ever computed. **Re-read any result
that mixes the two channels against this table before trusting it.**

## ⭐ LIVE CONNECTION — this may be the firmware cell we just measured [BELIEF, strong]

V98's `b3` rung measured **`sign(gp-0x6752) = −1`, CONSTANT NEGATIVE over all 17,983 frames** of route
`0x81` (duty 0.0000, see [[accord-v98-comparator-ranked-the-observer-arms]]). `gp-0x6752` is the
polarity factor the six lanes are multiplied by on their way to `gp-0x374c`:

```
six lanes -> x sign(gp-0x6752) -> x2639 (0xC6468) -> <<4 -> IIR pole 0xC63AC -> gp-0x374c
```

**A hard −1 sitting on the LKAS lane sum is exactly what a LKAS-frame → driver-torque-frame conversion
would look like.** If that is what it is, the firmware's own −1 and the operator's "opposite direction"
are the same fact seen from two ends. **NOT yet proven** — the alternative is that the −1 is an
unrelated internal convention and the frame flip happens elsewhere. **Worth closing; it is cheap.**

## ⚠ THE CONFOUND HE VOLUNTEERED — do not analyse left/right without it

> *"There is a left/right difference, but this might also be related to the fact that I think my
> steering angle sensor is calibrated wrong. So when the angle reads 0 degrees, the steering wheel is
> actually pointed slightly to the left."*

⇒ **Zero on the angle channel is NOT physical centre; it is offset slightly LEFT.** Consequences:

1. **A measured left/right asymmetry in the symptom is confounded with a sensor zero offset.** Do not
   attribute one to the other without an independent centre estimate (e.g. straight-line cruise mean
   angle, or the wheel-speed-difference zero crossing).
2. 🛑 **Every ABSOLUTE-steering-angle table in the firmware is being indexed off a shifted zero.** That
   includes the `0xC6B66`/`0xC6B80` 13-point LERP, whose axis is absolute angle and where **88.6 % of
   engaged driving sits in the flat first segment** — a zero offset moves the operating point on it.
   It also bears on FactorD, whose axis is absolute angle (see
   [[accord-factord-is-the-angle-error-lever]], where FactorD was REFUTED as a frequency-selective
   lever precisely because its axis is absolute angle).
3. `0xC63F8` = 33 vs `0xC63FC` = 328 is a **10× LEFT/RIGHT ramp-rate asymmetry, VIRGIN across all 89
   build images.** The operator reports a felt left/right difference. **That is now a live pairing —
   but it is NOT evidence until the sensor-zero confound is separated**, because a zero offset alone
   would make the two directions feel different with a perfectly symmetric firmware.

## How to apply

- **Before any analysis mixing LKAS command and driver torque, flip one.** State which, in the code.
- **Before any left/right claim, estimate the true centre** independently of the angle sensor's zero.
- **When reporting to the operator, say LEFT/RIGHT, not +/−.** He reasons in physical directions;
  the kit's sign conventions are where its worst errors have lived.

Related: [[accord-v98-comparator-ranked-the-observer-arms]] ·
[[accord-friction-polarity-more-assist]] · [[accord-lateral-engagement-signals]] ·
[[feedback-run-the-control-before-the-measurement]] · [[accord-factord-is-the-angle-error-lever]]
