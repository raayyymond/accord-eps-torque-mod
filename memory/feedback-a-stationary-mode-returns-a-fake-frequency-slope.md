---
name: feedback-a-stationary-mode-returns-a-fake-frequency-slope
description: "A STATIONARY injected mode returns -1.14 to +1.73 Hz per e-fold through an argmax pipeline when the amplitude axis is INDEPENDENT of the observed band power, and the sign tracks (band centre - mode frequency). Lineless low-amplitude windows scatter their argmax to the band centre. Against band RMS the artefact floor is ZERO. This puts the kit's -1.93 Hz/e-fold f0 law inside an artefact's range until the Re(Z) estimator gets the same control."
metadata:
  type: feedback
---

# 🛑🛑★★★★★ A STATIONARY MODE RETURNS A FAKE FREQUENCY-vs-AMPLITUDE SLOPE

2026-08-23, route `a6`. Found by running the control BEFORE the measurement — which is the only
reason a "pitch rises as amplitude falls" result did not enter the record.

## THE CALIBRATION
A **stationary** 22.0 / 20.0 / 26.0 Hz mode injected at a ladder of amplitudes into route a6's own
manual-driving noise, through the identical binning + argmax pipeline. True slope = 0 by
construction. Search band 18–30 Hz, so band centre = 24 Hz.
```
injected 22.0 Hz -> vs log(BAND RMS) -0.000 Hz/e-fold | vs log(TRUE amp) -1.138
injected 20.0 Hz -> vs log(BAND RMS) -0.000           | vs log(TRUE amp) -0.759
injected 26.0 Hz -> vs log(BAND RMS) +0.000           | vs log(TRUE amp) +1.731
recovered peak in EVERY amplitude sextile: 21.98 / 19.98 / 25.97 -- dead flat
```
🛑 **Against BAND RMS the artefact floor is essentially ZERO — that regression is trustworthy.
Against an INDEPENDENT amplitude axis it is ±1.7 Hz/e-fold, and THE SIGN TRACKS
(band centre − mode frequency).** Mechanism: lineless low-amplitude windows have no peak to lock
onto, so their argmax scatters toward the middle of the search band.

## WHY THIS MATTERS — it reaches a ★★★★★ memory
`accord-f0-crossover-is-the-endpoint` records **−1.93 Hz per e-fold of amplitude**, and it was
measured against **COMMAND amplitude — an axis independent of the observed band power.** That is
exactly the configuration that manufactures a slope. **The number sits inside the artefact's range.**
🛑 **NOT retracted here:** `f0` is a `Re(Z)` zero-crossing, not an argmax, and *that* estimator has
never been calibrated. But the same family has already produced **`q_of` = 79 on white noise** and
**BW 0.749 / Q 36.2 on white noise** (`feedback-run-the-control-before-the-measurement`).
⇒ **Push a stationary synthetic at an amplitude ladder through the actual `Re(Z)` f0 code before
−1.93 is used to size anything.** OPEN.

## WHAT THIS KILLED
The hypothesis that **attenuation and pitch-rise are the same knob** — i.e. that damping the mode
would raise its frequency for free via the amplitude law. Three builds, three best-powered cells,
all **excluding** −1.93: V106 ≥70 km/h (n = 405 windows) **+0.391 [−0.386, +0.607]** · V105 40–95
[−0.254, +1.000] · V104 ≥70 [−0.500, +0.305]. **A refutation at road speed, not an underpowered
null.** ⚠ At 16–40 km/h it is genuinely unresolved, and <16 km/h dropped out for want of windows.

⭐ **AND A BAND-PLACEMENT CONTROL THAT CAUGHT A FALSE POSITIVE.** V106's own 40–95 slope read
**+1.838** — but sweeping the search band gives +3.16 / +2.71 / +1.68 / **−1.22**: the sign flips.
V104 and V105 are stable to three decimals across the same sweep. **A slope that moves with the band
edges is the band edges, not the signal** — and it is diagnostic of *no dominant line present*,
which is independently what V106's spectrum shows.

## HOW TO APPLY IT
1. **Prefer band RMS as the amplitude axis.** It has a zero artefact floor here.
2. **If the axis must be independent (command, dose, speed), calibrate the pipeline on a stationary
   synthetic FIRST and report the floor with the result.**
3. **Always sweep the search band.** Stability across band edges is a free, powerful control;
   instability means the argmax has nothing to lock onto.
4. **Check the drive-level confound explicitly.** a6's command was 0.755 e-folds below a5's, so
   under −1.93 the peak should have read **+1.46 Hz HIGHER**; it measured LOWER in all three
   regimes. That mismatch is what proved the peak movement was NOT the command law operating on a
   drive-level difference.

Related: [[feedback-run-the-control-before-the-measurement]] · [[accord-f0-crossover-is-the-endpoint]] ·
[[feedback-design-the-statistic-inside-a-drive]] · [[accord-v106-extinguished-the-mode-at-low-speed]]
