---
name: accord-the-lowspeed-grind-is-an-83hz-harmonic-series
description: A harmonic comb IS detectable above its own null on V107 (f0 ~83.5 Hz, five harmonics, p=0.000) - but the SAME test run across the gain ladder finds a significant comb on STOCK too, the scores do not order by gain, and the f0 estimate suffers a SUB-HARMONIC AMBIGUITY (40-50 vs 83-85 Hz families). So the comb is real but NOT ours and NOT shown to be the grinding. The V109 endpoint survives only as a within-build before/after.
metadata:
  node_type: memory
  type: reference
---

# ⚠ QUALIFIED — A COMB IS REAL, **STOCK HAS ONE TOO** (at a different `f0`), AND `f0` IS AMBIGUOUS

★★★★★ **EVIDENCE**, 2026-08-27. Route `1e` = **V107**, the build immediately before V108/V109.
The operator on V108: *"low speed below ten miles an hour, grinding is still there… two modes.
One… maybe around a hundred hertz. And another… around a hundred or two hundred hertz."*

## 🛑🛑 THE LADDER RESULT — RUN THE SAME TEST ON STOCK AND IT FIRES TOO
Recorded within the hour of the original claim, 2026-08-27. The spectrogram extractor was
generalised (`rlog-tools/decode/extract_route_audio.py`) and spectrograms built for the whole
available ladder. Scored identically by `rlog-tools/score/comb_score.py`:
```
  route  build        gain    f0 Hz   score dB   null p95      p
  97     V9b-STOCK      1x    49.50     +1.457      0.665  0.000   <- STOCK FIRES
  85     V100           4x    43.50     +2.494      0.821  0.000
  95     V101           8x    40.25     +3.513      0.729  0.000
  a6     V106           6x    85.00     +2.675      0.520  0.000
  1e     V107           6x    83.50     +1.682      0.486  0.000
```
🛑 **STOCK carries a significant comb.** ⇒ **"an engaged harmonic comb" is NOT by itself ours.**
⚠⚠ **BUT "the series is NOT ours" OVERSTATES IT — corrected in the same pass, before publishing.**
Stock's fitted comb is at **49.50 Hz and its 2× harmonic is NULL**:
```
  r97 STOCK  f0 49.50:  1x 49.5 +5.62 dB | 2x 99.0 -0.14 dB | 3x 148.5 +1.88 | 4x 198.0 -0.06
  r1e V107   f0 83.50:  1x 83.5 +2.80    | 2x 167  +1.37    | 3x 250.5 +1.53 | 4x 334  +1.48
  ra6 V106   f0 85.00:  1x 85   +4.18    | 2x 170  +2.05    | 3x 255   +1.35 | 4x 340  +4.06
```
⭐ **Stock has essentially NOTHING at ~99 Hz (-0.14 dB), which agrees exactly with the third-octave
result** ([[accord-the-100hz-mode-is-ours-and-engagement-gated]]: stock **-0.03 dB** at the 100 Hz
third-octave). **The two findings are CONSISTENT, not contradictory** — they are different statistics
and both say stock is quiet at 100 Hz.
⇒ **The honest statement: a significant comb exists on stock too, but at a DIFFERENT fitted `f0`
and with a NULL where the modified builds carry energy.** Whether stock's ~50 Hz comb and the
builds' ~85 Hz comb are the same object read two ways (see the sub-harmonic ambiguity below) or two
different lines **is NOT resolved.**
🛑 **And the scores do not order by gain**: 1× **1.457** < 6× **1.682** < 4× **2.494** <
6× **2.675** < 8× **3.513**. Stock is lowest, but V107 — the build the operator complained about — is
**second lowest**, and the two 6× builds straddle the 4×. **No dose-response.**

## 🛑 A SUB-HARMONIC AMBIGUITY IN THE ESTIMATOR — `f0` IS NOT RELIABLE
The fits split into two families, **40–50 Hz** (stock, V100, V101) and **83–85 Hz** (V106, V107),
and `83.5 ≈ 2 × 41.75`. **That is not two mechanisms — it is one estimator failing.** A comb at `f0`
ALWAYS also scores at `f0/2`, because every harmonic of `f0` is an even harmonic of `f0/2`; which of
the two the grid picks depends on whether the intervening odd multiples of `f0/2` happen to be
elevated by noise. ⇒ **the reported `f0` may be the true fundamental or any integer sub-multiple of
it, and the two "families" above are probably the same comb read two ways.**
⇒ 🛑 **Do not quote `f0 = 83.5 Hz` as a frequency identification**, and the earlier remark that
`1000/12 = 83.33` is now doubly worthless — it was already inside the ±2 Hz bin resolution, and the
fundamental itself is not identified.

## ✅ WHAT SURVIVES
1. **A harmonic comb exists and clears its own null on every route tested**, p = 0.000, with the
   grid search inside the null. **That much is solid.**
2. ⚠ **"An engaged comb" is not by itself ours** (stock fires), it is **not established as the
   grinding** (no operator-symptom correlation was ever computed), and it is **not dose-ordered**.
   ⊕ **But stock is quiet at ~100 Hz on BOTH statistics**, so the narrower claim — *the ~100 Hz
   content specifically is ours* — **still stands.** It is the "83.5 Hz comb is ours" framing that
   does not.
3. **The V109 endpoint survives, but only in its within-build form**: V109 vs V108 on the SAME
   route pair, same road, same driver. A cross-build ladder comparison is not supported by this
   statistic, because stock already scores as high as V107.
⊕ The instrument itself is sound and is the kit's only view above 50 Hz. **Keep building
spectrograms; the fault was the interpretation, not the extractor.**

## ⭐ THE PROCESS FAILURE, RECORDED
The original claim was published **one tick before** the ladder was run, on a single route, with no
stock arm — and the very first thing the ladder did was contradict it. **The stock comparison was
available the whole time** (r97's rlogs have been on disk all along) and cost one background job.
🛑 **RULE: when a result's whole force is "this is OURS", build the STOCK arm BEFORE publishing,
not after.** The kit already had this rule for band-power work
([[feedback-run-the-control-before-the-measurement]]); it was not applied here.
⊕ A second, narrower bug was caught in the same pass: the null originally required
`len(engaged) >= 2 x len(manual)` and **silently produced ZERO draws on four of the five routes**,
reporting `nan`. A grid-searched score with no null is guaranteed positive. Fixed to use disjoint
halves capped at `len(manual)`, which makes the null noisier than the real comparison and therefore
errs conservative; and the scorer now **refuses to report a score when it cannot build a null.**

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
