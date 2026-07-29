# 🛑 The `gp-0x6b98` probe UNDER-ranges to a 1-bit comparator — amplitude claims from it are void

Measured 2026-07-29 on route `24` (V56, 16 segments, first road drive with the probe). The operator's
standing question — *"are we keeping track that we are only looking at a few bytes of the observed value,
not the entire thing?"* — turns out to be the load-bearing issue, and the answer is worse than expected,
in the **opposite** direction from the one we guarded against.

## The encoding

```python
field = clamp((gp_0x6b98 >> 9) + 8, 1, 15)   # 4 bits of a SIGNED 16-bit register
# 1 level = 512 counts.  Observable window ~ [-3584, +3584].  Outside that it rails.
# field == 0 is reserved for "the cave did not fire".  Sampled at 100 Hz -> 21 Hz and 79 Hz alias.
```

We built this expecting **railing** on a road drive, because commands would be large. The reverse happened.

## What the road drive actually shows

Engaged + hands-off, n = 69,607:

| field | `gp-0x6b98` range | share |
|---|---|---|
| 5 | −1536..−1025 | 0.1% |
| 6 | −1024..−513 | 0.3% |
| **7** | **−512..−1** | **59.0%** |
| **8** | **0..511** | **40.1%** |
| 9 | 512..1023 | 0.4% |
| 10 | 1024..1535 | 0.0% |

**99.2% of frames sit in two adjacent levels.** Rail occupancy at field 1 and field 15 is **0.0%** in
every engaged condition. `bit7 = 1` in 94,369/94,369; bits 2:0 constant `7`.

⇒ With one LSB = 512 counts and the signal living inside ±512, **the probe is behaving as a ~1-bit sign
comparator on the motor command**, not as a 4-bit measurement.

## What survives and what does not

**Survives — presence and frequency.** A comparator preserves zero-crossing timing, so "is there content
at f?" and "at what frequency?" remain answerable. Transition rate is the honest robust statistic:
11.3 changes/s route-wide engaged+hands-off, **23.9/s speed-matched to creep** (V55/route `1c` was
**21.9/s** — essentially the same).

🛑 **Does NOT survive — any amplitude.** The recorded **"120.5 counts at 21 Hz in `gp-0x6b98`"** and the
**"38× over openpilot's budget / 8.7× even unfiltered"** that rests on it are set by the **quantiser
step**, not by the signal. 120.5 counts is under a quarter of one LSB, recovered only through dither of
unknown magnitude. **Retract the number or attach an explicit interval — do not re-quote it bare.**

⚠ **Weakened — the "flat H1" result.** Recomputing H1(sensor→field), engaged + hands-off, NFFT=256:

| | 1.17 Hz | 3.12 | 5.08 | 7.81 | 21.09 Hz | windows |
|---|---|---|---|---|---|---|
| V55 / route 1c, vEgo≤1.98 | 0.058 | 0.480 | 0.335 | 0.389 | 0.132 | **3** |
| V56 / route 24, speed-matched | 0.540 | 1.153 | 1.020 | 0.463 | 0.584 | **5** |
| V56 / route 24, all speeds | 1.467 | 0.507 | 0.340 | 0.038 | 0.464 | 438 |

This does **not** reproduce the recorded *"flat 0.192 @1 Hz → 0.216 @21 Hz, coherence 0.93"*. The
windowing differs (contiguous engaged+hands-off runs required here), so it is **not a like-for-like
refutation** — but the figure is clearly **method-sensitive, computed on very few degrees of freedom,
through a 1-bit output**. 🛑 That matters because the flat-transfer claim is what the record used to
**eliminate the entire `0xC646C` reader set**. Treat that elimination as **provisional** until it is
re-established on a channel with real resolution.

## How to apply

- **Any future build carrying this probe must re-scale it.** With `gp-0x6b98` inside ±512, `SHIFT = 9` is
  ~6 bits too coarse. `SHIFT = 6` (64 counts/level, window ±448) puts the observed distribution across
  most of the 1..15 range; `SHIFT = 7` (128 counts/level, ±896) is the conservative choice if larger
  transients are expected. Keep the clamp to 1..15 and the reserved 0 —
  [[feedback-telemetry-must-reserve-a-did-not-fire-value]].
- **State the observable window next to every probe-derived number.** "P[15-26] = 182 in field units"
  is honest; "120.5 counts at 21 Hz" is not.
- The **full 16-bit** CAN `0x18F` torsion-bar signal is *not* subject to any of this. Keep sensor-side
  and command-side figures rigorously separate — the sensor-side 786×/877× engaged/disengaged ratios in
  [[reference-accord-v56-flashed-mute-is-null-and-costs-damping]] are unaffected.
- 100 Hz sampling still cannot separate 21 Hz from 79 Hz. Unchanged.
