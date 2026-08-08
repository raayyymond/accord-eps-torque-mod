---
name: accord-probe-underranges-to-one-bit-comparator
description: "The gp-0x6b98 firmware probe UNDER-ranges to a ~1-bit sign comparator (99.2% of engaged frames in two adjacent levels) — presence/frequency claims survive but every command-side AMPLITUDE claim is void, including '120.5 counts at 21 Hz' and the flat-H1 result that eliminated the 0xC646C reader set."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 596df10f-7827-4cf9-8d92-4190a417047f
  modified: 2026-07-29T06:45:31.632Z
---

`field = clamp((gp_0x6b98 >> 9) + 8, 1, 15)` — 4 bits of a signed 16-bit register, **1 LSB = 512 counts**.
We built it guarding against **railing** on a road drive. The opposite happened.

**Route `24`, engaged + hands-off, n = 69,607:** field **7 = 59.0%**, field **8 = 40.1%** ⇒ **99.2% in two
adjacent levels**, i.e. `gp-0x6b98` lives inside **±512** while one LSB *is* 512. Rail occupancy at
fields 1 and 15 is **0.10% / 0.00%**; **field 15 never occurs in 943 s**; `field == 0` in **0** samples.
⇒ **The probe is a ~1.5-bit channel: an amplitude comparator, but a usable SPECTRAL probe.**
⚠ *"10 distinct values, 100% interior, no rails"* is true of the whole drive but **false of the analysed
engaged subset** — 4 distinct values, 93.2% in fields 7-8. Always state the subset.

| claim | status |
|---|---|
| presence / frequency of a mode in the command | ✅ survives — a comparator preserves zero-crossing timing |
| transition rate (11.3/s route-wide; 23.9/s at creep vs V55's 21.9/s) | ✅ survives; the robust statistic to quote |
| "120.5 counts at 21 Hz" | ⚠ **KEEP, restate** — encoder gain 1.006, false-positive floor 10-18 counts ⇒ **7-12× above floor, a real detection.** But it is a **bin-RMS, not an amplitude** (÷0.5766 → ≈209 counts) |
| "38× over openpilot's budget" | 🛑 **UNRESOLVED: 38× or 66×** — depends on whether openpilot's "31.7 counts" was an amplitude or a bin-RMS. The record must say. Either way it runs *against* openpilot as source |
| "flat H1 0.192 → 0.216, coherence 0.93" | ⚠ **UNCONFIRMED, not refuted.** Quantisation **exonerated by construction** (a memoryless nonlinearity cannot flatten a pole; coherence bias is DOWNWARD ⇒ 0.93 is a lower bound). The problem is **dof**: at ±19.6% a 16.8 Hz pole (rel-sse 0.215) and flat (0.245) are indistinguishable, and the *rise* is not significant |
| the `0xC646C` reader-set elimination | 🛑 **STANDS — on its structural leg** (`0xC646C` has 0 matches across all 468 instructions of `FUN_0003a382`, a byte fact). The transfer argument is corroborating only. **No candidate returns to scope** |
| "9 independent segments, significance 0.312" | 🛑 **wrong — K=3, significance 0.776.** Route 1c engaged is 2 contiguous runs = 23.6 s. `band_power(hop=nfft//4)` is 75% overlap, overstating dof ~4× |

**Why:** the operator asked directly whether we were tracking that only a few bits of the value are
visible. We were not. The audit that followed did **not** overturn the conclusions — quantisation was
exonerated by construction, and the `0xC646C` elimination survives on its structural leg — but it did
force three real restatements (bin-RMS vs amplitude, K=3 not 9, flat-H1 unconfirmed) and caught a
sentinel-collision bug in the obvious re-encoding. ⚠ **Both over- and under-correction were live risks
here: the first pass of this memory wrongly declared the amplitude figure void and the elimination
provisional.** Check the arithmetic before demoting a result, not just before promoting one.

**How to apply:** re-scale to **`SHIFT = 7`, `OFFSET = 8`** (128 counts/level) — the only option whose
railing can be bounded from data. 🛑 **`SHIFT = 6` requires `OFFSET = 9`**: `(x>>6)+8 == 0` for
x ∈ [−512,−449], colliding with the `field == 0` liveness sentinel that already saved this kit once.
🛑 Also: a ~1.5-bit quantiser's **5th harmonic of the 20-25 Hz mode FOLDS into the few-Hz band** at
fs = 100 Hz (25-79 counts, +5-7 dB over floor); it moves **5× faster with speed** than the mode, which is
the test any new few-Hz claim from this probe must clear. Keep the 1..15 clamp and the reserved 0
([[feedback-telemetry-must-reserve-a-did-not-fire-value]]). Always state the observable window next to a
probe-derived number. The **full 16-bit** CAN `0x18F` torsion-bar figures are unaffected — keep
sensor-side and command-side numbers rigorously separate. 100 Hz still cannot separate 21 from 79 Hz.
See [[v56-flashed-mute-null-and-costs-damping]].
