# ★★★★ ALIASING IS RESOLVABLE: `|Rate(f0)| / |Ang(f0)| = 2π·F_true` SURVIVES THE FOLD

**Established 2026-08-07 on route 67 (V81).** The kit has carried "a 21 Hz line is indistinguishable from
79 Hz aliased" through a dozen handoffs as an **unresolvable** ambiguity inherited by every analysis. It is
**not** unresolvable. There is a direct measurement, it costs nothing, and it **generalises to every
aliased line in the corpus**.

## The method — [EVIDENCE]

The EPS transmits both a steering **angle** and its **derivative**, and the derivative is taken **inside
the EPS at its ~1 kHz tick, BEFORE the 100 Hz CAN sampling**. Sampling then folds angle and rate
**identically**, so the *magnitude ratio* is untouched by the fold and still reports the **true**
frequency, not the observed bin:

```
|Rate(f0_observed)| / |Ang(f0_observed)|  =  2π · F_true
```

Read the ratio, divide by 2π, and compare against the candidate readings `f0`, `100−f0`, `100+f0`.

## The route-67 result

At the observed bin **27.34 Hz** (coherence 0.997 between the two channels):

| candidate | 2π·f (rad/s) |
|---|---|
| 27.34 Hz | **171.8** |
| 72.66 Hz | 456.5 |
| 127.34 Hz | 800.1 |

Measured ratio: **119.2 rad/s** (`rate_c`) and **115.4** (`rate_f`).

⇒ **72.66 Hz is off by 3.8× and is EXCLUDED.** The 27.5 Hz reading is the true one.

⚠ **Flagged residual, unexplained:** the measured ratio is still **31% under** the 27.34 Hz prediction
(119 vs 172). Angle quantisation (0.1° LSB) is far too small to account for it — the angle rms at the line
is ~60× the quantiser floor. So: **the alias twin is excluded [EVIDENCE]; the exact line frequency carries
a ~1.4× magnitude anomaly that is NOT understood.** Do not quietly drop this caveat when reusing the
method — a rate-channel low-pass would explain the magnitude but should also add phase lag, and the phase
says pure delay (see [[accord-0x18f-payload-one-frame-stale]]).

## Preconditions before trusting it

- Use a bin where **coherence between angle and rate is high** (0.997 here). At low coherence the ratio is
  contaminated by independent noise in both channels and wanders by 2× — the route-67 table shows implied
  `F_true` of 7.3–19.5 Hz at bins where coherence was 0.27–0.5, all meaningless.
- Use `rate_c` (`0x14A`, **same message as the angle**, so identical capture instant) in preference to
  `rate_f`; and correct `rate_f`'s 0.8× scale error if you use it.
- The test says nothing about *which* physical mode it is — only which frequency reading is real.

Method and code: `rlog-tools/v81loop_alias.py` (S0.6c).
Related: [[accord-0x18f-payload-one-frame-stale]] (same invariant, used for timebase),
[[accord-both-instruments-blind-above-50hz]], [[reference-accord-lkas-lane-is-a-lowpass]].
