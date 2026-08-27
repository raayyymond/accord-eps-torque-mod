# 🛑🛑 AN ENVELOPE RINGDOWN THROUGH A BANDPASS IS MEANINGLESS WITHOUT A STEP CONTROL

**Established 2026-08-07 on route 67 (V81), seg 8, the latActive falling edge at t = 52.193 s.**
**Two agents, independently, on the same edge, fitted a bandpass filter's own step response and read
it as plant damping.** One reported Q ≈ 7 with a monotone amplitude dependence; the other reported
Q ≈ 10.4–10.8 at **R² 0.987 over a 19.5× decay**. Both were artifacts. A filter's step response *is*
a clean exponential, so a high R² is not evidence of anything.

## The control — run it before quoting any ringdown [EVIDENCE]

Bandpass a **perfect step**: a synthetic oscillation that stops dead at t₀ with **zero** plant decay.
Any apparent decay is pure filter.

| band half-width | ~transient 1/(2H) | apparent tau | **apparent Q** |
|---|---|---|---|
| 1.5 Hz | 0.333 s | 0.104 s | **9.0** |
| 3.0 Hz | 0.167 s | 0.104 s | **9.0** |
| 5.0 Hz | 0.100 s | 0.135 s | **11.6** |

Both reported values sat inside that band.

**Second check — widen the band.** As the transient shrinks, a *real* decay separates from the
control; an artifact does not:

| half-width | DATA tau | STEP tau | ratio |
|---|---|---|---|
| 1.5 | 0.087 | 0.067 | 1.30 |
| 3.0 | 0.120 | 0.082 | 1.46 |
| 5.0 | 0.059 | 0.096 | 0.62 |
| 8.0 | 0.067 | 0.100 | **0.68** |
| 12.0 | 0.071 | 0.093 | **0.77** |

No systematic growth. At the best-resolved widths the data decays *faster* than the control.
⚠ Also: the Q family spans **9.7 → 1143** across fit start/end choices. Quoting one favourable point
as robust is the failure mode here; vary the fit window and report the spread.

## The physical result that replaced the number

**Q ≲ 6 (upper bound only). tau ≲ 0.067 s ≈ 1.8 cycles at 27.5 Hz. The ring does not ring down — it
STOPS.** Three consequences:

1. **The 27.5 Hz line is not a forced resonance driven by anything.** A Q ≲ 6 plant cannot amplify a
   small drive into a 500+ count bar oscillation. Any "drive × Q" bound built on this resonance is
   void — see [[accord-v81-highway-27hz-line]] if written.
2. It is an **actively sustained limit cycle whose energy source is engaged-only**, removed within
   ~2 cycles of the disengage edge.
3. **Exactly two things switch at that edge:** openpilot's command and the engaged-only damper
   (mode 26 → 24). openpilot's share is bounded at ≲ 3–5% ⇒ **the damper is the prime suspect**,
   reached independently of the harmonic argument.

🛑 **A cross-build ringdown Q ladder is not obtainable from these logs** — there is no decay to
measure. An attempt returned Q = 1028 (tau 11.8 s) on V80 seg13, which is a fitter with no
goodness-of-fit gate fitting noise. Gates if ever retried: R² ≥ 0.97, decay ≥ 10×, no re-engagement
in the window, fit start ≥ 0.2 s after the edge — **and the step control above.**

⚠ Every disengage-edge measurement is of the **DISENGAGED** plant: the engaged-only damper switches
off at that instant, and mode 24 is byte-stock on V76/V80/V81. It cannot test an engaged-damper dose.

## Two related traps from the same session

- **Full-event linewidth is NOT damping.** A Q of 103 measured from the line's width is phase
  diffusion of a self-sustained oscillator. f₀ wanders **0.576 Hz** across the event (2.5 s
  sub-windows: 27.37–27.95 Hz), which alone gives a linewidth-equivalent Q of ~48.
- **That drift also breaks harmonic fold arithmetic for N ≥ 5** — at 7f it is a ±4 Hz smear, so there
  is no stable fold location to test. Use a phase-lock test instead: complex demodulation tracks
  instantaneous phase and is inherently drift-tolerant, which is why the 3rd-harmonic result survived
  where the arithmetic did not. See [[accord-alias-resolution-via-derivative-ratio]].

Code: `rlog-tools/studies/loop-causality/v81loop_x10_cubic_and_q.py` (the control), `studies/loop-causality/v81loop_x8_harmonic.py` (phase-lock).
Related: [[accord-0x18f-payload-one-frame-stale]], [[accord-stock-mode24-equals-mode26-damper-is-ours]].
