---
name: accord-knee-and-k1-decouple-lightness-from-relayness
description: The friction relay's small-signal GAIN (lightness) and its SATURATION RATE (relay-ness) are set by two different cals - gain = (K1/1024)(12/knee), saturation = knee/12 - so scaling knee and K1 TOGETHER holds the lightness exactly while pushing the relay corner out. MEASURED on route 21 (V111): the relay is SATURATED 74.4 percent of the time in the operator's own grind-#1 regime. The +-10.0 clamp objection is DEAD (103x headroom). Built as V112 at x3.
metadata:
  node_type: memory
  type: reference
---

# ⭐⭐ `0xC40BC` AND `0xC40D2` **DECOUPLE** LIGHTNESS FROM RELAY-NESS

★★★★ **EVIDENCE for the arithmetic (read off `FUN_0003b8f6`); BELIEF for the on-car consequence.**
2026-08-27, written to answer [[feedback-do-not-buy-ratchet-with-mass-and-friction]].

## THE STRUCTURE
```
fVar13   = clamp(POL * gp-0x6abc * 12 / cal(0xC40BC), -1, +1)
friction = EMA(|model| * cal(0xC40D2)/1024 * fVar13)          # cal(0xC4080) = 0, no floor
residual = model - friction - inertia                          # MORE friction => MORE assist
```
**Two independent properties of that one product:**
```
  small-signal GAIN  (sets the LIGHTNESS)   =  (K1/1024) * (12 / knee)
  SATURATION rate    (sets the RELAY-ness)  =  knee / 12   counts of |gp-0x6abc|
```
⭐ **The knee appears in BOTH; K1 appears in only ONE.** So K1 is exactly the free variable that
cancels the knee's gain effect and leaves its saturation effect standing.
```
  config                    small-sig gain   saturates above    vs V111
  V111  (K1 204, knee  600)      0.003984        10.6 deg/s      1.000x
  knee x2 ALONE (knee 1200)      0.001992        21.2 deg/s      0.500x   <- HEAVIER.  wrong.
  knee x2 + K1 x2 (408, 1200)    0.003984        21.2 deg/s      1.000x   <- SAME lightness
  knee x4 + K1 x4 (816, 2400)    0.003984        42.4 deg/s      1.000x
```

## WHY THIS IS THE RIGHT *SHAPE* FOR THE DIRECTIVE
The operator wants **low apparent mass/friction to LKAS AND no ratcheting**. This lever:
- **adds no impedance** — it changes a feed-forward friction *compensation*, not a damping term, so
  it cannot load the LKAS path the way `gp-0x6b26` or α2 do;
- **holds the small-signal gain exactly**, so the wheel feels the same at low rate;
- **pushes the Coulomb corner out**, so the term is viscous over a wider range and **relay-like over a
  narrower one** — and the relay character is what
  [[accord-engagement-amplifies-6-9hz]] measures as the engagement-specific 2.8× amplification.
⊕ Below the old corner the two configs are **bit-identical**; above it the new one keeps climbing:
```
   deg/s     V111 fVar13   new (gain-compensated)   ratio
    5.0        0.4712            0.4712             1.000
   10.6        0.9990            0.9990             1.000
   15.0        1.0000            1.4136             1.414
   21.2+       1.0000            2.0000             2.000
```
⇒ **more friction compensation at high steering rate = MORE assist exactly where max angular
velocity is wanted** ([[accord-friction-polarity-more-assist]]).

## ✅✅ RESOLVED 2026-08-27 — THE CLAMP OBJECTION IS DEAD, AND THE DUTY IS MEASURED
**The clamp cannot bind.** `iVar11 = cal(0xC7468)*fVar18` clamps at ±20000 and `cal(0xC7468)=41232`,
so **`|model| ≤ 20000/41232 = 0.4851`** — a hard bound the arithmetic gives for free. Hence
`friction_max = 0.4851 × K1/1024`:
```
   V111 (K1 204)  friction_max 0.0966   ->  103x headroom to the +-10.0 clamp
   K1 x3 (612)                 0.2900   ->   34x
   K1 x4 (816)                 0.3865   ->   26x
```
⇒ **the ±10.0 float clamp is ~100x above anything this term can physically produce.** The V107-style
railing risk was hypothetical and is now excluded on arithmetic.

## ⭐⭐ AND THE RELAY DUTY IS **MEASURED** — route 21 IS the V111 drive
Identified by physics, not assumption: the 427 tap's quantiles **numerically equal** the steering
rate from `ang` (p95 39.4 vs 40.4, p99 167.4 vs 171.8, **p99.9 313.4 vs 313.3 °/s**), which only holds
if the tap is `gp-0x6abc` at sar 3. That also **independently confirms the 4.7121 ct/(°/s) scale.**
```
  RELAY SATURATION DUTY, 5-10 mph engaged hands-off |cmd|>=2048, n=289 frames
     knee  600 (V111)  0.7439   block-bootstrap 95% CI [0.6691, 0.8146]   <- ON THE CAR
     knee 1200         0.4810      DF gain rise 1.99x
     knee 1800 (V112)  0.2353      DF gain rise 2.97x    <- BUILT
     knee 2400         0.0484      DF gain rise 3.93x
     knee 3600         0.0000      DF gain rise 5.75x
```
🛑 **THE RELAY IS IN HARD COULOMB MODE 74 % OF THE TIME IN EXACTLY THE REGIME THE OPERATOR NAMES**
(*"grind number one still occurs at low speeds between 5 and 10 mph, particularly under strong
openpilot commands"*). **First direct measurement of the mechanism the kit has called a
command-proportional Coulomb relay since V80.**
⊕ Unconditioned, the same regime is only 18.5 % saturated — **command drives the saturation 4×**,
which is the same command gate [[accord-ratchet-and-grind-are-command-gated-saturation]] measured
from a completely different instrument.

## ⭐ THE GATE-2 ARGUMENT THAT MAKES A BIG DOSE DEFENSIBLE
The DF magnitude rises up to ~3× **but can never exceed the small-signal gain `g`, which is UNCHANGED
and is exercised on every drive at low rate.** No new gain regime is created — the lane simply
behaves at high rate the way it already behaves at low rate. **Structural, not statistical.**
⚠ What it DOES cost: at saturating rates the residual falls from `0.80·|model|` to `0.40·|model|`
(x3), i.e. **a 2× reduction in the torque-tracking reference above 31.8 °/s** — more assist by the
verified polarity, but not a small edit. Below 10.6 °/s V112 is **bit-identical** to V111, and the
regime's p50 is 3.7 °/s.

## ⚠ THE ORIGINAL RISK NOTE, KEPT — NOW SUPERSEDED BY THE ARITHMETIC ABOVE
**Holding the small-signal gain while moving the corner NECESSARILY DOUBLES THE LARGE-SIGNAL
OUTPUT.** There is no way around it: a saturation that reaches the same slope but later must emit
more before it flattens.
```
  V111 ceiling :  friction_max = |model| * 204/1024 = |model| * 0.199
  proposed     :  friction_max = |model| * 408/1024 = |model| * 0.398    <- 2x
  and friction is CLAMPED at +-10.0 float  (gp-0x6ae2 = friction * 1024 => +-10240 counts)
```
⇒ **if `|model|` can reach ~50 the term rails the ±10 clamp — and a railed term is a NEW Coulomb
relay at a HIGHER rate.** That is precisely V107's failure mode
([[accord-gp6b26-is-a-61hz-bandpass-and-v107-railed-it]]) reproduced one lane over.
🛑 **DO NOT BUILD THIS DOSE UNTIL `|model|`'s ENGAGED DISTRIBUTION IS KNOWN.** The kit has never
measured it; `gp-0x6ae2` has only ever been read through V106's `b5` comparator rung
(duty 0.2533 pooled / 0.4019 engaged <16 km/h), which is a comparison, not a magnitude.

## WHAT DECIDES IT
1. **`|gp-0x6abc|`'s engaged distribution** — if the ratchet regime already sits **below** 10.6 °/s
   the term is *already* linear there and moving the corner buys nothing. **Route `21` measures this
   if it is the V111 drive** ([[accord-v111-flew-alpha2-is-the-only-delta]]).
2. **`|model|`'s engaged distribution** — decides the clamp risk. **Not measured; needs a probe.**
⇒ **This is a lever SHAPE, not yet a build.** Recorded so the shape is not re-derived, and so the
clamp risk is not discovered on the car.

Related: [[accord-the-coulomb-relay-is-located-c40bc-is-its-knee]] ·
[[accord-v89-built-plant-model-friction]] (V89 doubled K1 102→204 — the same axis, the other end)
