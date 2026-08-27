---
name: accord-the-lowspeed-grind-is-an-83hz-harmonic-series
description: On V107 the operator's low-speed grinding has a measured, controlled spectral signature - an ~83.5 Hz HARMONIC SERIES five harmonics deep (82/172/254/328/414 Hz), engagement-gated, p=0.000 against a null that includes the grid search. Even AND odd harmonics present, so it is an asymmetric periodic process, not a symmetric relay. Gives V109 a pre-registered quantitative endpoint.
metadata:
  node_type: memory
  type: reference
---

# THE LOW-SPEED GRIND IS AN **~83.5 Hz HARMONIC SERIES** — MEASURED, CONTROLLED

★★★★★ **EVIDENCE**, 2026-08-27. Route `1e` = **V107**, the build immediately before V108/V109.
The operator on V108: *"low speed below ten miles an hour, grinding is still there… two modes.
One… maybe around a hundred hertz. And another… around a hundred or two hundred hertz."*

## THE INSTRUMENT — and it already existed, unrecognised
`analysis-2020accord/_scratch/cache/r1e/r1e_spec.npz`: **26,638 frames × 513 bins, 3.91 Hz
resolution, 0–2000 Hz, 1337.3 s, 100 % coverage.** Built by `rlog-tools/decode/extract_r1e_audio.py`
from `rawAudioData` (16 kHz PCM). ⚠ **It was named `_spec`, not `_audio`, and was overlooked** —
every earlier acoustic result in this session used the coarse 20-band third-octave caches instead,
which stop at V104. 🛑 **Route `1b` carries ZERO audio blocks; all V107 audio is `1e`-only.**

## THE RESULT
Engaged-minus-manual, **matched speed, below 10 mph, hands-off, WITHIN drive** (1868 engaged /
1026 manual frames). Absolute level never travels between drives — cabin gain differs 3–12× — so
every contrast here lives inside route `1e`.
```
  HARMONIC-COMB FIT   score = mean engaged excess over the first 6 harmonics of f0
  BEST f0 = 83.50 Hz     comb score +1.682 dB
     1x    83.5 Hz   +2.80 dB   (peak bin  82.0)
     2x   167.0      +1.37      (bin 171.9)
     3x   250.5      +1.53      (bin 253.9)
     4x   334.0      +1.48      (bin 328.1)
     5x   417.5      +1.23      (bin 414.1)
```
⭐ **THE CONTROL, and it is the strong kind.** An **engaged-vs-engaged random split** at the same
sample sizes, with **the same f0 grid search run inside the null** (so the search cannot inflate the
result): p50 **+0.304**, p95 **+0.506**, max **+0.589** over 200 draws.
⇒ **real +1.682 dB, p = 0.000** — 3.3× the p95 and above the null's maximum.
⊕ Per-bin version of the same control: null max|dB| p95 = **1.13 dB**; the real 82.0 Hz bin is
**+2.80 dB**, and five separate clusters clear the floor (78–90, 156–176, 254–262, 324–328,
441–445 Hz).

## \U0001f6d1 EVEN **AND** ODD HARMONICS ⇒ NOT A SYMMETRIC RELAY
2× and 4× are both present and both clear the null. A **sign function emits odd harmonics only**.
⇒ **the source is an ASYMMETRIC periodic process** — a one-sided impact, a ratchet-and-release, or a
rectified/offset nonlinearity. **Not the symmetric Coulomb relay of
[[accord-the-coulomb-relay-is-located-c40bc-is-its-knee]]**, at least not that term alone.

## WHAT ~83.5 Hz MIGHT BE — stated as arithmetic, not as a claim
`1000 Hz / 12 = 83.33 Hz`, and the control task is 1 kHz ([[control-task-tick-confirmed-1khz]]).
⚠ **The bin spacing is 3.91 Hz**, so the fit resolves f0 only to about **±2 Hz** — it cannot
distinguish 83.33 from anything in 81.5–85.5 Hz. **Do not treat the 1 kHz/12 coincidence as
identification.** ⊕ It is NOT an electrical order: the ~119 Hz third-octave centroid is fixed across
a 40× steering-rate span ([[accord-the-100hz-mode-is-ours-and-engagement-gated]]), which excludes
PMSM 6th/12th-order ripple for this family.

## ⭐⭐ IT GIVES V109 A PRE-REGISTERED, QUANTITATIVE ENDPOINT
V109 cuts `0xC40DC` (α2) so the `gp-0x6b26` lane loses **34 % at 100 Hz and 39 % at 200 Hz**
([[accord-c40dc-is-the-band-limit-lever]]). The comb score is the readout, and the sentence a null
licenses is writable in advance:
```
  comb score at f0 = 83.5 Hz, engaged-minus-manual, <10 mph, hands-off, within-drive
     V107 baseline          +1.682 dB   (p95 null +0.506)
     V109 drops toward null  => the gp-0x6b26 lane FEEDS this series; alpha2/knee is the lever
     V109 unchanged          => the lane does NOT feed it; look elsewhere, and alpha2 is dead here
```
🛑 **The V109 drive MUST capture audio.** `extract_r1e_audio.py` is route-parameterised by one
constant (`ROUTE`); the same cache must be built for the new route or the endpoint is unmeasurable.
⚠ **Audio caches currently stop at V104** for the third-octave family and exist **only for `1e`** in
the spectrogram family — V105, V106 and `1b` have none.

## ⚠ LIMITS
- **One route, one build.** No cross-build comparison is possible without more spectrograms, and
  absolute level never travels between drives (drive-card manoeuvre 0 still uncollected).
- Engaged and manual segments are matched on **speed only**.
- At **10–20 mph** the picture differs: the 83.5 Hz fundamental is absent from the surviving
  clusters and the excess concentrates at **238–285 and 301–348 Hz** (peaks +2.77 / +2.55 dB,
  null p95 0.85). **Whether that is the same series without its fundamental, or a different
  mechanism, is NOT established.**

Related: [[accord-the-100hz-mode-is-ours-and-engagement-gated]] ·
[[accord-ratchet-and-grind-are-command-gated-saturation]] · [[accord-c40dc-is-the-band-limit-lever]]
