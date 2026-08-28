---
name: accord-the-oscillation-is-not-command-driven
description: "Only 6.9 percent of total rate power above 5 Hz is coherent with the LKAS command, and 20-30 Hz alone carries 36.0 percent of ALL rate power at coherence 0.100. That kills the entire command-side filter class (independently confirming the already-struck 0xC63EC/EE) and says the oscillation is a CLOSED-LOOP instability. It also contradicts the premise behind the operator's no-mass-no-friction directive: doubling the viscous term costs 1.4 percent of command authority at openpilot's own p90 demand."
metadata:
  node_type: memory
  type: reference
---

# 🛑🛑★★★★★ THE OSCILLATION IS **NOT COMMAND-DRIVEN** — SO NO COMMAND-SIDE FILTER CAN FIX IT

2026-08-27, 15 routes pooled, engaged & hands-off (D3) & moving, Welch 1024-pt @100 Hz.

## THE MEASUREMENT [EVIDENCE]
```
  band          % cmd power   % rate power   coh2    coherent rate power (of ALL rate power)
   0.1- 1.0 Hz    58.0971       27.9021      0.649        18.4569 %
   1.0- 2.0 Hz     4.6516        3.8229      0.448         1.8488 %
   2.0- 5.0 Hz     2.3508        3.2236      0.309         0.9923 %
   5.0- 8.0 Hz     0.5996        3.8160      0.237         0.8771 %
   8.0-12.0 Hz     0.3418        3.3190      0.153         0.5281 %
  12.0-20.0 Hz     0.3442        6.3918      0.078         0.4334 %
  20.0-30.0 Hz     0.1912       36.0137      0.100         5.0124 %   <- the dominant band
  30.0-50.0 Hz     0.1699        1.4076      0.037         0.0499 %
```
🛑 **RATE energy above 5 Hz = 50.95 % of all rate power. The part of it COHERENT with the LKAS
command = 6.90 %.** ⇒ **~86 % of the high-frequency motion is not linearly explained by the command.**
⊕ **Command energy above 5 Hz is only 1.65 % of the command's own total** (above 10 Hz: 0.83 %).

## 🛑 CONSEQUENCE 1 — THE WHOLE COMMAND-SIDE FILTER CLASS IS DEAD
A command-side low-pass can remove **at most the coherent part**, i.e. ≤ 6.9 % of total rate power,
and realistically far less. This **independently reproduces** the already-struck verdict on the
arbitration IIR `0xC63EC`/`0xC63EE` (`BUILD-LINEAGE.md:438`, *"DEAD ON ARITHMETIC … 91.1 % of bar
6–9 Hz power is INCOHERENT with the command"*) from a different instrument and a wider corpus.
🛑 **Do not propose lowering the arbitration corner, and do not propose any other command-side
filter.** ⊕ `Kd` (`0xC6AE6`) is separately **closed**: it is one knot of a **flat** four-knot LERP, so
a one-knot edit converts a constant into a rate-dependent nonlinearity — **worse than inert**
([[accord-kd-is-one-knot-of-a-flat-lerp]], which killed V110).

## ⭐⭐ CONSEQUENCE 2 — IT IS A CLOSED-LOOP INSTABILITY, SO THE LEVER IS LOOP DAMPING
**20–30 Hz carries 36.0 % of all rate power at coherence 0.100 with the command.** A band that
dominates the energy while being nearly uncorrelated with the forward input is the signature of a
**self-sustained loop oscillation**, not a driven response. That is consistent with
[[accord-vibration-requires-lkas-engaged]] (**9,200× less power with LKAS off**): engaging closes a
loop whose gain is too high — it does not inject the tone.
⇒ **The fix must raise loop damping or cut loop gain in 20–30 Hz. Filtering the input cannot work.**
⊕ And the only lever that has ever *measurably* worked is exactly that: **V106's ×3.0 on the
`gp-0x6b26` row extinguished the 21–27 Hz mode at low speed** — the first band-power result in the
kit to clear its own split-half null. (Uniform axis then declared exhausted; V107's reshape railed.)

## 🛑🛑 CONSEQUENCE 3 — THE DIRECTIVE'S PREMISE IS CONTRADICTED BY MEASUREMENT
[[feedback-do-not-buy-ratchet-with-mass-and-friction]] rests on the operator's causal belief that
added mass/friction **costs him max steering angular velocity**. Three measurements say otherwise:
1. **The firmware already OVER-delivers** vs the command it receives (`CMD→rate` **+1.2 dB** at
   1–2 Hz, coherence 0.51).
2. **The deficit is upstream, in openpilot** (`demandRate→CMD` **−16.0 dB**, attenuated *more* than
   the motion) — [[accord-the-rate-deficit-is-upstream-of-the-firmware]].
3. **Damping is cheap in authority terms.** `gp-0x6bbe` is ~90 ct/(rad/s) against a 2505-count
   full-command arb output:
```
   demanded rate     viscous term     cost of DOUBLING it, as % of full command
       5 deg/s          7.9 ct                0.63 %
      11 deg/s (p90)   17.3 ct                1.38 %
      40 deg/s (p99)   62.8 ct                5.01 %
```
⇒ **At openpilot's own p90 demand of ~11 °/s, doubling the viscous term costs 1.4 % of authority.**
🛑 **This RE-OPENS the damping class** — the only class with a measured success. It does **not**
overrule the operator; it reports that the reason he ruled it out does not survive measurement.
**Put it to him rather than acting on it unilaterally.**

## ⚠ WHAT IS NOT ESTABLISHED
- **Which** loop. The 20–30 Hz mode's phase and gain around the loop are not identified; an on-car
  gain-step system ID at 18–31 Hz remains the open item.
- Coherence at 12–30 Hz is **0.078–0.100**, so the *coherent* fraction is well estimated but the
  incoherent remainder's origin (plant, road, or a loop the command does not see) is **unresolved**.
