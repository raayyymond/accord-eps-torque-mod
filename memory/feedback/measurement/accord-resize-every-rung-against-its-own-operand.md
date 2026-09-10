---
name: accord-resize-every-rung-against-its-own-operand
description: A probe bit's FORM (sign, magnitude-vs-threshold, ratio) does not transfer between operands even when the form is proven elsewhere. V289's magnitude rung "|n| >= |y|" (its own b7) is INVERTED when reused unchanged on V290's rate-operand notch -- symptomatic duty reads LOWER than quiet on every route, which would ship a bit that falls when the grinding rises. Two other candidate rungs for the same operand were also measured and killed. 2026-09-09.
metadata:
  type: feedback
---

# Re-size every probe rung against its own operand's measured distribution, even when the form is proven

**What happened.** Designing V290's telemetry (a notch on the LKAS rate operand `x = gp-0x6a56`, a
different signal from V289's notch on the clamped PID-sum output `S`), the obvious move was to reuse
V289's own magnitude rung `b7 = |n| ≥ |y|` (which worked well on `S`) unchanged. Measured on the new
operand it is **INVERTED**: symptomatic-frame duty is *lower* than quiet-frame duty on every route and
both upsampling models (r39 0.061 symptomatic vs 0.189 quiet; r62 0.169 vs 0.263; r63 0.166 vs 0.283).
**Reusing V289's bit unchanged on this operand would have shipped an instrument that falls when the
grinding rises** — the opposite of what a magnitude channel is for.

**Two other rung forms proposed for the same operand were also measured and killed before shipping:**
- `|n| ≥ |x|>>S` ("is the operand's content in the notch band?") — **negative separation** between
  symptomatic and quiet frames on all 3 routes × both models (−0.006…−0.238). It reads the operand's raw
  low-frequency magnitude, not band content: engaged p50 |x| is 4–8 raw counts while p99 is 1257–1883, so
  quiet frames sit at the comparator's LSB-floor coin-flip and loaded turns are dominated by wheel slew.
- `|n| ≥ |d|<<k` (LF killed by a first difference first) — its **synthetic** calibration IS band-selective
  (k=3 peaks at duty 0.50 at 20 Hz), but **on the car it is flat** (r39 symptom 0.438 vs quiet 0.460) —
  both numerator and denominator sit at the LSB floor on quiet frames, so a form that calibrates cleanly
  on a synthetic sine can still be dead on the actual wire distribution.

**The rung that survived** (`b7 = |n| ≥ 16`, a plain threshold, not a ratio) was sized from the
operand's own measured 3-route distribution — not assumed, not carried over — using the fact that `n` is
band-limited by construction (the notch's `|1−H| ≥ 0.5` only over 12.44–37.13 Hz, →0 at DC and Nyquist),
so nothing above 50 Hz can inflate it and the 100 Hz wire predicts its magnitude honestly.

**Why this generalizes:** a rung's *form* (sign vs magnitude, threshold vs ratio) can be validated in the
abstract (synthetic sine sweeps, unit tests) while its *calibration* — where symptomatic and quiet
populations actually separate — is entirely a property of the specific operand's measured amplitude
distribution on THIS car. A proven form on one signal is not evidence it separates on a different signal,
even a related one in the same loop.

Source: `docs/specs/design/DESIGN-V290-TELEMETRY-2026-09-09.md` §0 (agent `instr290`), backed by
`v290_telemetry_sizing.py`/`sizing2.py`/`sizing3.py`.

**How to apply:** before shipping any probe bit that reuses a form validated on a different operand or a
different build, re-measure its symptomatic-vs-quiet separation on the ACTUAL operand it will read, on
real routes — never assume the form transfers just because it worked elsewhere or calibrates cleanly on a
synthetic signal. See [[accord-probe-underranges-to-one-bit-comparator]] and
[[feedback-size-probe-rungs-against-lane-reachable-output]] for related probe-sizing discipline.
