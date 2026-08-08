# 🛑🛑 `0x18F`'s PAYLOAD IS ONE CAN FRAME (≈10 ms) STALE RELATIVE TO `0x14A`'s

**Measured 2026-08-07 on route 67 (V81), segment 8.** This is a **permanent instrument calibration**,
not a route-67 finding. It **corrects every `command → bar` phase this kit has ever computed**, in this
session and in every prior one, by ≈+10 ms — which at 27.5 Hz is **99°**, i.e. it can inturn a lead into a
lag and reverse a causal reading.

## The invariant that makes it measurable — [EVIDENCE]

The EPS transmits a steering **angle** and a steering **angle rate**, and the rate is the derivative of the
angle **computed inside the EPS at its ~1 kHz tick, before the 100 Hz CAN sampling that aliases
everything**. A derivative leads its integral by exactly **+90°**. So the *departure* from +90°, measured as
a function of frequency, is a direct readout of timebase error — and the units of that departure say what
kind of error it is:

- a departure constant in **milliseconds** ⇒ a pure **timebase offset**
- a departure constant in **degrees** ⇒ a **filter**

Two rate copies exist, and they ride **different messages**:

| copy | message | stored factor | rides with |
|---|---|---|---|
| `rate_c` | `0x14A` b2-3 | ×−1.0, **1 °/s LSB** | the ANGLE |
| `rate_f` | `0x18F` b2-3 | ×−0.1 as stored — **wrong, true is −0.125** | the **TORSION BAR** |

Lead-error expressed as time, 20–35 Hz, event window:

| f (Hz) | `rate_c` err | `rate_f` err |
|---|---|---|
| 19.92 | −2.63 ms | −14.95 ms |
| 23.83 | −2.28 ms | −11.96 ms |
| 27.34 | **−2.03 ms** | **−12.14 ms** |
| 30.08 | −2.47 ms | −12.42 ms |
| 35.16 | −1.85 ms | −6.95 ms |

Constant in **ms**, not degrees ⇒ pure offset. `rate_c` ≈ **−2.2 ms** (same message as the angle, so this
residual is EPS-internal). `rate_f` ≈ **−12.1 ms**. Difference **9.9 ms = one 100 Hz frame**.

## What to do about it

- **Add ≈+10 ms to any `0x18F` channel before comparing it with a `0x14A` channel.** The bar (`tq`) and
  `rate_f` both ride `0x18F`; the angle (`ang`), `rate_c` and the V75/V81 **probe byte** ride `0x14A`.
- The kit's caches (`extract_r67_v81.py`, and `extract66`'s schema **verbatim**, so *every* `_cache_*`)
  build one row per `0x14A` frame and carry the **most recent `0x18F`** forward. Recover each held value's
  own timestamp from `raw18_t` — `v81loop_lib.native_18f()` does this. The residual hold age after that is
  0.31 ms mean, negligible.
- ⚠ `rate_f`'s stored scale is **0.8× the truth**: `rate_f/rate_c = 0.7954 ± 0.006` below 2 Hz across five
  segments, raw-field ratio 7.99–8.03. Use `rate_fine_degs = rate_f * 1.25`.
- ⚠ `cs_tq` / `cs_rate` (openpilot's interpolated `carState` copies) are **unusable above ~10 Hz**:
  `corr(tq, cs_tq)` is 0.998 below 2 Hz but **0.60** broadband in the 27.5 Hz event. Use raw CAN.
- ⚠ **1.7% of CAN rows share a `logMonoTime`** (1372 of 78,760 on route 67; seg 3 has 604). `np.gradient`
  over `t` divides by zero there and NaNs the whole column, silently.

Method and code: `rlog-tools/v81loop_alias.py` (S0.6b), `rlog-tools/v81loop_lib.py::native_18f`.
Related: [[accord-alias-resolution-via-derivative-ratio]] uses the same invariant for aliasing,
[[accord-v81-carries-neither-grind1-fix]], [[feedback-v76-v80-tooling-traps]].
