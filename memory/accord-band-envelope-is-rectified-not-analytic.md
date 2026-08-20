---
name: accord-band-envelope-is-rectified-not-analytic
description: band_envelope in _r31_common.py and _r2b_common.py returns a RECTIFIED signal not an analytic envelope - every envelope-SHAPE result across ~20 callers is wrong
metadata:
  type: reference
---

🛑🛑 **`band_envelope` IS BROKEN IN TWO SHARED HELPERS** — `analysis-2020accord/_r31_common.py` and
`rlog-tools/_r2b_common.py`. **REPORTED 2026-08-20, NOT FIXED.**

**The bug:** both build `H[band] = 2 * X[band]` on a **one-sided** spectrum and then call
`np.fft.irfft`, which **forces a REAL output**. `abs()` of that is the **rectified band-passed signal
×2**, i.e. `2A·|cos ωt|` — it oscillates at 2ω. It is not an analytic envelope.

**Consequences:**
- `max()` accidentally equals the correct peak-to-peak `2A` — but is **2× the amplitude `A`** that
  `_r31_common`'s own docstring claims (*"this is the AMPLITUDE A, so peak-to-peak is 2*A"* — **wrong**).
- **Every percentile below the max is a rectification artefact**: median = `1.414A`, RMS = `1.414A`.
- `2 * band_envelope(...)` used as peak-to-peak at
  `analyze_bus_amplitude_vs_detector_T.py:282` is **2× too large**.
- Measured on route `0x95`: `env_RMS / signal_RMS` came out **exactly 2.000**, median 494 against an
  RMS of 1520.

**What survives and what does not:**
- ✅ **RATIOS between conditions are unaffected** — the ×2 cancels.
- 🛑 **Every envelope-SHAPE result is WRONG**: growth rate σ, decay τ, ring-down ζ/Q, and any
  p50 "amplitude". **This reaches back into historical Q and ζ figures in this kit.**

**~20 callers**: `analyze_r31_*`, `analyze_r35_v64_arms.py`, `analyze_r37_*`,
`decode_v59_boostindex.py`, `compare_v75_v76_v80_grind.py`, `selfint_transfer.py`,
`analyze_bus_amplitude_vs_detector_T.py`.

✅ **`rlog-tools/r95_lib.py::band_envelope` uses a full complex `ifft` and is CORRECT. Use it.**
Every number in the 2026-08-20 session was computed with either `r95_lib` or a Parseval-normalised
Hann-window band-RMS with no envelope at all.

Related: [[accord-the-8x-gain-is-the-carrier]], [[feedback-run-the-control-before-the-measurement]],
[[accord-raw14-offbyone-in-every-cache]].
