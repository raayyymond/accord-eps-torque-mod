---
name: accord-acoustic-cache-two-silent-zeros
description: "🛑🛑★★★★★ TWO SILENT ZEROS in the acoustic tooling, both found independently by two agents. (1) `wide[:,0]` (5–15 Hz) and `wide[:,2]` (21–28 Hz) of EVERY `*_audio.npz` are IDENTICALLY ZERO — a 1024-pt FFT at 16 kHz has 15.625 Hz bins and neither band contains one. (2) `extract_audio.py`'s `segments()` stops at the first absent index, so route `85` (the 4× rung, segments 15,16,18,19,20) was SILENTLY SKIPPED. Both produce confident wrong answers, not errors."
metadata:
  node_type: memory
  type: reference
---

# Two silent zeros in the acoustic tooling

**EVIDENCE**, verified by direct byte/array reads on 2026-08-21, and — the strongest part — **found
independently by two different agents in the same session.** Two agents converging on the same two
defects from different estimators is better evidence than either finding alone.

## 1. THE ALL-ZERO BAND COLUMNS
`rlog-tools/extract_audio.py` builds third-octave and "wide" band powers with **NFFT 1024 at 16 kHz**
⇒ **15.625 Hz bin spacing**:
```
bin centres: 0.000  15.625  31.250  46.875  62.500  78.125  93.750  109.375 ...
   5-15 Hz  -> 0 bins   COLUMN IS IDENTICALLY ZERO   (mean = 0.0 on every route, checked)
  21-28 Hz  -> 0 bins   COLUMN IS IDENTICALLY ZERO
  15-21 / 28-40 / 40-60 Hz -> ONE bin each: single-bin leakage, NOT a band power
```
🛑 **21–28 Hz is precisely the band the wheel-rate work separates stock from 6× on**, so the column
that looked like the acoustic cross-check of the kit's central result was **a zero**. Anything
computed from `wide[:,0]` or `wide[:,2]` — including any "sub-100 Hz cross-check" — is **void in
both directions**.

## 2. THE SILENTLY-SKIPPED ROUTE
`segments()` walks `--0--`, `--1--`, … and **stops at the first absent index**. Route `85` on disk is
segments **15, 16, 18, 19, 20** — index 0 is absent ⇒ the scan returns **zero segments** and the
route is skipped with no error. **`r85` is the 4× rung**, i.e. the middle of the gain ladder.
⚠ A silently-empty arm is how this kit has previously manufactured *"only on route X"* findings.

## 3. THE FIXES, BOTH IN THE TREE
- `rlog-tools/extract_audio_ladder.py` — replaces **only** the segment discovery with a glob;
  feature extraction byte-identical. ⚠ `r85`'s cache is a **5-of-21-segment SUBSET**; never quote its
  absolute level as a whole-route figure.
- `rlog-tools/extract_audio_env.py` — band-passes the **raw PCM** (4th-order zero-phase Butterworth)
  and takes the **true analytic (Hilbert) envelope**. No FFT bins ⇒ the bin trap cannot apply.
- `rlog-tools/extract_audio_grind.py` — **NFFT 16384 ⇒ 0.9766 Hz bins** for direct sub-100 Hz work,
  and caches the **whole 0–100 Hz spectrum** rather than pre-selected bands.

🛑 **THE GENERAL LESSON, and it is the reusable one: a band request that contains no FFT bin returns
0.0, not an error.** Before trusting any narrow band, assert `n_bins >= 1` and print it.
See [[accord-v850-scan-traps-formatv-and-storezero]] for the same failure class in byte scans, and
[[feedback-run-the-control-before-the-measurement]].
