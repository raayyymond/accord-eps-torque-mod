# ARM-KP3 — corrected readout. This SUPERSEDES the G0–G7 block in `make_armkp3_config.py`.

**2026-09-20.** The config file itself is unchanged and correct (SteerKP 3.0, AccordErrorNotchQ 0.30,
AccordTorqueKi 0.60, everything else rev 6.4 as flown). What changed is **how it must be read**, and the
status of the statistic that was used to size and defend it.

---

## 🛑 THE VECTOR-MARGIN STATISTIC IS NOT VALIDATED — and it was used to withdraw ARM-KP2

The `VM = min|1+L|` anchors quoted throughout this study (r71 0.322/0.079, rev 6.4 0.686/0.505, …) **could not
be reproduced** by an independent re-derivation, and the underlying engine **fails the one labelled test
available**: it cannot retrodict route 71's limit cycle from route 71's own flown parameters.

Three independent failures:

1. **Algebra.** Only **0.29 %** of loop gain over 2–6 Hz separates r71's controller from r72's *in the engine's
   model*. It structurally cannot tell apart the route that limit-cycled from the route that flew clean.
2. **Ordering.** On a cross-table of every plant × every controller, r72 (flew clean) reads the *smallest*
   margin in two of three bins, and V282's controller — months of clean driving — reads **worst on every
   plant, including its own.** The sign of the r71-vs-r72 difference also flips between plants.
3. **False clear AND false alarm.** On r71's own plant the engine reads r71's controller at 0.893 (safe — it
   was not) and rev 6.4's at 1.042 (unsafe — it is flying now).

⇒ **Every Tier B number built on that axis (49 %, 69 %, 80 % closure) is unfounded — not imprecise, unfounded.**
The earlier `|L|`-in-the-shake-band axis was already falsified for the same reason (it ranked r72 above r71).

**Does this un-withdraw ARM-KP2?** No. Its withdrawal rests on the *mechanism* — a ×3 gain raise with a notch
that has recovered to |N| 0.686 by 4.2 Hz, hand-verified from the notch algebra — not on the VM numbers. But the
specific figures in that withdrawal note (0.254/0.049 vs r71's 0.322/0.079) should not be quoted again.

## ✅ WHAT DOES RETRODICT — and it is the fork's own model

Plant = `J·θ'' + b·θ' + k(v)·θ = torque` with `J = HONDA_ACCORD_EPS_INERTIA = 8e-5`, `b = 0.0006`,
`k(v) = HONDA_ACCORD_HOLD_K_V` — i.e. exactly the model behind `get_honda_accord_mode_hz`, which I verified in
source reads `sqrt(k(v)/J)/2π`. Gain and phase anchored on each route's measured complex plant at 0.20 Hz
(where coh(Z,M) = 0.95–0.96), delay bracketed at the measured 55–75 ms:

| route | \|L\| at the −180° crossing | crossing f | predicted | observed |
|---|---|---|---|---|
| **r71 as flown (SteerFriction relay ON)** | **1.29 / 1.43 / 1.54** | 2.63 / 2.53 / 2.45 Hz | **LIMIT CYCLE** | **2.34 Hz ✓** (5–12 %) |
| r71 with the relay omitted (the engine's model) | 0.81 / 0.89 / 0.96 | — | stable | **FALSE CLEAR** |
| r72 as flown (relay off) | 0.53 / 0.56 / 0.59 | — | stable | flew clean ✓ |

The separation is **controller-driven**: with the relay, r71's controller carries ×1.57–1.58 the loop gain of
r72's on all three plant anchors; with the engine's model it reads ×0.986–0.989, i.e. *safer*.

## 🛑 ARM-KP3 IS A MECHANISM CHECK, NOT A METRIC RESULT

**The goal metric cannot read back a 15.9 % improvement on one drive.** Bootstrap on the existing routes:
**17.6 % (block) / 32.2 % (10-window) of NULL draws already reach J ≤ 1.2064.** Do not score the drive on J,
and do not report a J improvement as evidence the config worked.

## READOUT — read these and only these

- **G0 PARAMS GATE, from the route's own `initData`.** `SteerKP` 3.0 · `AccordErrorNotchQ` 0.30 ·
  `AccordTorqueKi` 0.60. If `AccordErrorNotchQ` reads ABSENT, the device's params `.so` lacks the key and the
  **drive is VOID, not a null.**
- **G0b 🛑 THE SAFETY INTERLOCK — confirm `AccordFrictionHyst` is still 0.015.** Verified in source at
  `latcontrol_torque.py:675`: `friction_torque = 0.0 if friction_hyst > 0.0`. That guard is the only thing
  keeping the relay that broke r71 dead, and **this fork back-fills absent keys with stock values** — route 6d's
  `initData` shows a back-filled `SteerFriction` 0.2120. Check the field, do not assume it.
- **G1** `median(torqueState.p / torqueState.error)` = 3.000; `median(-(p+i+f)/output)` = 14.00.
- **G2** Notch depth on the wire: re-synthesise `error_with_lsf`, push through the notch at Q 0.30 and at Q 1.00;
  RMS residual vs logged `torqueState.error` ≤ 1e-3 against Q 0.30 and ≥ 0.05 against Q 1.00.

## ⭐ WHAT TO LISTEN FOR — a DIFFERENT frequency from the one you know

On the retrodicting model, ARM-KP3 moves the −180° crossing to **1.5–1.8 Hz** — set by the Q 0.30 notch's own
phase — **not** the 2.34 Hz of r71. Peak |L| goes 0.36–0.46 @ 1.07 Hz (as flown) to 0.47–0.67, a bounded ×1.46
step, Ms ~1.5–1.8. **Score 1.5–1.8 Hz behaviour specifically.** For contrast on the same model: SteerKP 8 gives
peak |L| 0.86–1.25, and SteerKP 16 reads |L| 1.00–1.44 at the crossing — **predicted unstable on one of two
anchors.** The engine's VM never saw any of that.

## REVERT = SteerKP 1.0, AccordErrorNotchQ 1.0, AccordTorqueKi 0.30
Any sustained line **1.5–6.0 Hz** (widened, and re-centred on the predicted crossing); any oscillation, buzz,
whine or hunting reported at speed; any new low-speed symptom below 8 m/s (step Q to 0.40 rather than abandoning).

## WHAT COMES NEXT, AND IT NEEDS NO DRIVE
Repair the controller model — add the `SteerFriction` relay as a describing-function gain and the
`AccordRateLoopGain` inner loop (live at 0.001, against the fork's own note that 0.0012 "would cross" at
3.5–4 Hz) — then **re-run the retrodiction gate, pre-registered:** the statistic must (a) rank r71's controller
riskiest on a plant *not* taken from r71's own log, and (b) separate r71 from r72 by more than its own bootstrap
CI. A relay-only version already passes (a) on 2 of 3 plants at ×1.57–1.58 separation.
**If the repaired statistic still fails, the sentence that licenses is: no statistic available to this kit orders
the flown anchors by controller, therefore the Tier B class is CLOSED at any dose until the instability
mechanism is modelled.** That null costs zero drives.

## THE PROBE IS NOT ADMISSIBLE, and the cheap drive alternative is dead too
- A probe confined to 0.68–1.60 Hz would have read r71 at **|1+L| = 1.92 — "ample margin" — the day before it
  limit-cycled.** The margin only collapses at the mode: 0.804 at 2.34 Hz, 0.419 at 2.54 Hz. Both proposed
  designs chose their band precisely *because* tones at 1.9–4.3 Hz cost ×1.47 in the shake band. **Safe where
  useless, useful where unsafe.**
- It also repairs the wrong leg: both designs buy a better *plant*, while the measured failure is in the
  *controller* model.
- And neither is an inert tap — both manufacture a signal onto the actuator path.
- **Enriching by reference power does NOT restore coherence at 2–3 Hz on this EPS** (measured: no systematic
  improvement, matched-n, top vs bottom third), though it works plainly on V282. The reference path has almost
  no authority there (|L| 0.04–0.16), so the deficit is not a sampling problem. This kills the *cheap* drive,
  not every drive.

---
**Incidental but worth knowing:** route 6d — one of the two routes that define the J = 1.3512 baseline — carried a
back-filled `SteerFriction` 0.2120 in its `initData`. It was inert (the `:675` guard, `AccordFrictionHyst` 0.015),
but it is a reminder to read the params rather than the labels.
