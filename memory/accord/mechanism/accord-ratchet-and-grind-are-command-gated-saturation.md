---
name: accord-ratchet-and-grind-are-command-gated-saturation
description: The 6-9 Hz ratchet and the 20-26 Hz grind are both SWITCHED ON by LKAS command magnitude (3.0x and 4.0x by 1k-2k counts, 52x and 11.8x by 3k+), band-specific with two control bands FALLING - and they switch on in the same regime where the 4x-to-6x gain step stops delivering torque. One saturating nonlinearity, two spectral signatures.
metadata:
  node_type: memory
  type: reference
---

# THE RATCHET AND THE GRIND ARE **COMMAND-GATED**, AND IT IS THE SAME REGIME WHERE THE GAIN DIES

★★★★★ **EVIDENCE**, 2026-08-27. Prompted by the operator's own phrasing — *"jerky motion under
large torque command, jerky steering wheel turning under LKAS instead of a smooth turn"* — which the
record had never used as a discriminator.

## 1. THE MEASUREMENT
14 routes (V90–V107, 4× and 6×), 2.56 s windows, **engaged AND hands-off** (D3: rolling-median
`|cs_tq|` over 0.5 s < 1200), **< 20 mph**. Statistic = band power in the steering **rate**,
**normalised by 1–3 Hz power in the same window** ⇒ a **SHAPE**, immune to how hard the manoeuvre was.

```
  |cmd|      n      3-5 ctl   6-9 RATCHET   10-13 ctl   14-18 ctl   20-26 grind
  <1k      878        0.362        0.657       0.543       1.037         2.285
  1k-2k     82        0.258        1.972       0.376       1.162         9.240
  2k-3k     45        0.226        3.074       0.377       1.153        12.991
  3k+       53        0.687       34.168       1.790      13.126        26.889

  FOLD-RISE vs the <1k baseline  -- THE CONTROL THAT MATTERS
  1k-2k             0.7x         3.0x        0.7x        1.1x          4.0x
  2k-3k             0.6x         4.7x        0.7x        1.1x          5.7x
  3k+               1.9x        52.0x        3.3x       12.7x         11.8x
```

## 2. ⭐ THE CONTROL PASSES, AND IT IS THE STRONG KIND
At **1k–3k command the ratchet band rises 3.0–4.7× while TWO control bands FALL** (3–5 Hz to 0.6–0.7×,
10–13 Hz to 0.7×) and a third is flat (14–18 Hz, 1.1×). **A confound — harder steering, sharper
corners, more road input — would lift every band together.** It does the opposite.
At **3k+** everything broadens, but 6–9 Hz rises **52×** against the next-largest band's 12.7×.
⇒ **The ratcheting is SWITCHED ON by command magnitude. It is not a constant background resonance
being passively excited.**

## 3. 🛑 AND THE GRIND RIDES THE SAME GATE
20–26 Hz rises **4.0× / 5.7× / 11.8×** on the same axis. ⇒ **ratchet and grind are two spectral
signatures of ONE command-gated nonlinearity**, not two independent defects. This is consistent with
[[accord-engagement-amplifies-6-9hz]] measuring the mechanism as a **command-proportional Coulomb
relay** — a relay is exactly what clipping under a large command produces, and stick-slip is exactly
what the operator means by *"jerky instead of smooth"*.

## 4. ⭐⭐ IT COINCIDES WITH WHERE THE GAIN STOPS DELIVERING
Same corpus, same hands-off mask: the **4× → 6× gain step delivers 1.03× [0.69, 1.50] below 15 mph at
`|cmd| ≥ 2048`, against 1.81× [1.28, 2.52] at 15–45 mph** (ideal 1.500); ratio-of-ratios
**0.557 [0.359, 0.909]**, P(low < high) = **0.992**. See
[[accord-gain-stops-delivering-at-low-speed-high-command]].
⇒ **The regime where extra gain buys no extra torque is the regime where the ratchet switches on.**
That is what a saturating element does: past the knee it stops passing gain AND starts generating
harmonics. **[BELIEF, strongly supported]** — one mechanism, both symptoms.

## 5. WHAT THIS CHANGES ABOUT THE RATCHET HUNT
The record's characterisation stands and is not contradicted: ~7.79 Hz, **Q 14–29**, ζ 0.017–0.036,
motor/rack-side, speed-invariant, in the bar and angle-rate but **not in openpilot's command**
([[accord-ratchet-is-a-lightly-damped-resonance]], [[accord-ratchet-characterised-on-route-4f]]).
**What is new is the GATE.** Sixty builds hunted a *linear* lever — a pole, a damper, a gain — for
what is now measured to be a **command-triggered nonlinearity**. ⇒ 🛑 **A linear lever cannot fix a
relay.** The target is the SATURATING ELEMENT: find what clips, and either raise its ceiling or
soften its corner.
⊕ This also explains the kit's oldest frustration — *"nothing has moved micro-ratcheting or
ratcheting in sixty builds"* — and why [[accord-ratchet-axis-is-wheel-rate]] found the amplitude
scaling with wheel rate: wheel rate and command magnitude are strongly correlated engaged.

## ⚠ LIMITS
- **n is small in the high-command cells** — 82 / 45 / 53 windows against 878 at baseline. The
  **1k–3k rows are the trustworthy ones** (controls falling, effect 3–4.7×); the 3k+ row is
  directionally consistent but thin and broadband.
- Command magnitude correlates with cornering. **The band-specificity at 1k–3k is what survives
  that**, because a cornering confound cannot make two bands fall while a third rises.
- Pooled across 4× and 6× builds. **Not** a per-gain result; do not read a dose from it.
- The saturating element is **NOT IDENTIFIED**. `0xC520C` is excluded (struck, rate-indexed, first
  knot 222.8 °/s) and the forward clamps `0xC61B2`/`B4` are excluded (they scale exactly with the
  gain: 512/2048/3072/4096 for 1×/4×/6×/8×). **Open.**

Related: [[accord-v80-damper-relay-and-grind1-inert]] · [[accord-the-8x-gain-is-the-carrier]] ·
[[accord-low-speed-rate-limit-is-openpilot-steer-max]]
