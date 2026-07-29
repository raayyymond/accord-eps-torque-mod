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

⚠ **KEEP but RESTATE — "120.5 counts at 21 Hz" is a REAL detection.** ⚠ *An earlier pass of this memory
called it void on the grounds that it is under ¼ of one LSB. **That reasoning was wrong and is
withdrawn**: averaging K segments over 512 bins recovers far below the step size when dither is present —
the detection floor is set by the noise, not the LSB.*

- **Encoder gain = 1.006, i.e. unbiased.** (The stable 0.58 recovered/true ratio is the Hanning single-bin
  capture factor C = 0.5766, not encoder bias.)
- **Quantisation false-positive floor**, simulated with *zero* true 21 Hz content at route 1c's actual
  dither (224-336 counts rms, read off sd(field)): **10-18 counts**; worst of 200 trials at K=1 was 41.
  ⇒ **120 counts is 7-12× above floor. Real detection.** Independent reproduction gives 92.9-98.2.
- 🛑 **Two restatements are mandatory.** (a) **120.5 is a bin-RMS, not an amplitude** — ÷0.5766 gives
  ≈**209 counts** amplitude. (b) **If openpilot's "31.7 counts" was an amplitude and 120.5 a bin-RMS, the
  true ratio is 66×, not 38×.** If both used the same estimator, 38× stands. **The record must state which
  — this is unresolved.** Either way the correction runs *against* openpilot as the source.
- Precondition: with **zero** dither the probe returns exactly 0.000 for a 100-count input. The estimate
  holds only because route 1c carried 224-336 counts of motion.
- ⚠ The **railed-subset** figure (105.8 counts) is 33.7% of 23.6 s = **7.9 s non-contiguous** ⇒ ≤1
  non-overlapping segment, and its coherence 0.66 is at/below its own threshold. **Do not lean on it.**

⚠ **UNCONFIRMED, not refuted — the "flat H1" result.** 🛑 **Quantisation is EXONERATED by construction:**
ground-truth lanes pushed through the exact encoder (Monte Carlo, K=30 × 60 trials) reproduce H1's
**shape** to a few percent — a true 0.93 Hz pole gives true ratio @21/@1 = 0.069 and measures
0.071 ± 0.022. A memoryless nonlinearity applies one describing-function gain at every frequency; **it
cannot flatten a pole.** H1 bias is −6%/−8% and shape-preserving; **coherence bias is DOWNWARD**
(0.963-0.976 for a true 1.000), so the recorded **0.93 is a lower bound and conservative**.

The real problem is **degrees of freedom.** Recomputing H1(sensor→field), engaged + hands-off, NFFT=256:

| | 1.17 Hz | 3.12 | 5.08 | 7.81 | 21.09 Hz | windows |
|---|---|---|---|---|---|---|
| V55 / route 1c, vEgo≤1.98 | 0.058 | 0.480 | 0.335 | 0.389 | 0.132 | **3** |
| V56 / route 24, speed-matched | 0.540 | 1.153 | 1.020 | 0.463 | 0.584 | **5** |
| V56 / route 24, all speeds | 1.467 | 0.507 | 0.340 | 0.038 | 0.464 | 438 |

Error bars, `sd(H1)/H1 = sqrt((1−g²)/(2Kg²))`: V55/1c @21.09 Hz **±19.6%** (g²=0.813, K=3); V56 matched
**±20.2%**; V56 all-speeds @7.81 Hz **±61.6%**. A scale-free 5-point fit gives **best single pole
fc = 16.8 Hz (rel-sse 0.215) vs flat (0.245)** — **statistically indistinguishable. The data does not
constrain the shape at all.** At ±20% the 0.192 → 0.216 *rise* is also **not significant**; "flat" is
defensible as description, "rising" is not.

⚠ The 438-window row has coherences 0.003-0.293. At g² = 0.003, H1 is a ratio of two noise estimates —
**no transfer-function content.** Read that row instead as *"route-wide there is no coherent sensor→command
relationship"*, which is a separate and interesting fact.

🛑 **The `0xC646C` elimination STANDS — but rest it on the other leg.** ⚠ *An earlier pass downgraded it to
"not yet tested". Withdrawn.* The record has **two independent reasons**, and the structural one is a
**byte fact untouched by any of this: `0xC646C` has 0 matches across all 468 instructions of
`FUN_0003a382`**, so the carrier cannot read it. Rest the elimination there; the transfer argument is
**corroborating only. No candidate cause returns to scope.**

⚠ **Also correct of record:** the *"9 independent segments, coherence significance 0.312"* figure is
**wrong**. Route 1c engaged is **2 contiguous runs** (998 + 1359 = 2,357 samples = **23.6 s**) ⇒ **K = 3**
non-overlapping 512-pt segments, **significance 0.776** (K=6 at 50% overlap → 0.451). Nine independent
segments would need 46 s. **The quoted coherences (0.672, 0.687) sit near or below their own threshold.**
Root cause: `band_power(nfft=256, hop=64)` is 75% overlap, so the printed `K` overstates dof ~4×.

## How to apply

- **Any future build carrying this probe must re-scale it — and mind the sentinel trap.**
  🛑 **`SHIFT = 6` with `OFFSET = 8` COLLIDES WITH THE `field == 0` SENTINEL:** `(x>>6)+8 == 0` for
  x ∈ [−512,−449]. That would silently destroy the liveness guard that already saved this kit once (a V54
  image decoding as a plausible V55 reading). **Offset must go to 9 whenever shift goes to 6.**
  **Recommended: `SHIFT = 7`, `OFFSET = 8`** — 128 counts/level, 4× finer, and the only option whose
  railing can be **bounded from data** (must-rail 0.13%, may-rail ≤0.83% on route 24 engaged+hands-off;
  0.00%/5.70% on route 1c). It also preserves enough range to *measure* the tails, so `SHIFT = 6 /
  OFFSET = 9` (64 counts/level, 15 levels used, rails estimated 15-20% but **model-based, not measured**)
  can be chosen on data next time. Clamping cost is benign to ~40% rails (recovery 0.56 vs 0.58 at 10%).
  Keep the clamp to 1..15 and the reserved 0 — [[feedback-telemetry-must-reserve-a-did-not-fire-value]].
- 🛑 **A ~1.5-bit quantiser generates harmonics, and at fs = 100 Hz the 5th harmonic of the 20-25 Hz mode
  FOLDS INTO THE FEW-Hz BAND** — measured 25-79 counts, +5.1 to +7.1 dB above the local floor. Decisive
  test: it moves **5× faster with speed** than the mode does (0.60 Hz at a 20.12 Hz mode → 4.50 @20.90 →
  5.45 @21.09 → 8.40 @21.68). In route 1c the 5.47 Hz bin carries only 3.07 counts (field/sensor ratio
  0.059, the lowest in the band) ⇒ **no evidence of the artifact in existing data** — but **any new few-Hz
  claim drawn from the probe must clear this test first.**
- **`rlog-tools/decode_v55_motorcmd.py` had the guard inverted** — it warned only above 50% rails and
  prescribed `CMD_SHIFT=10`, the wrong direction. **Fixed 2026-07-29**: it now flags >80% occupancy in ≤2
  adjacent levels and prescribes `CMD_SHIFT=7`, including the offset-9 warning.
- **State the observable window next to every probe-derived number.** "P[15-26] = 182 in field units"
  is honest; "120.5 counts at 21 Hz" is not.
- The **full 16-bit** CAN `0x18F` torsion-bar signal is *not* subject to any of this. Keep sensor-side
  and command-side figures rigorously separate — the sensor-side 786×/877× engaged/disengaged ratios in
  [[reference-accord-v56-flashed-mute-is-null-and-costs-damping]] are unaffected.
- 100 Hz sampling still cannot separate 21 Hz from 79 Hz. Unchanged.
