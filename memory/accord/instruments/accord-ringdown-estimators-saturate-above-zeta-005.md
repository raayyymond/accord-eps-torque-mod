---
name: accord-ringdown-estimators-saturate-above-zeta-005
description: "BOTH kit ring-down estimators saturate at zeta~0.05 and REVERSE above it - demod reads a zeta=0.20 mode as 0.0084, 24x too lightly damped - and their answer moves 3.5-6.3x with the fit-window length alone. _scratch/out/_stock_r97_ringdown.json is UNQUOTABLE and the recorded zeta 0.017-0.036 is an upper bound on Q, not a measurement. Matrix pencil (E3) is the replacement."
metadata:
  type: reference
---

# 🛑🛑★★★★★ THE KIT'S RING-DOWN ESTIMATORS CANNOT MEASURE THE MODE WE CARE ABOUT

2026-08-21. **The control was run BEFORE the measurement and it changed the picture.**
`rlog-tools/studies/damping-q/ringdown_validate.py`. Four estimators, identical synthetic inputs, f_n = 8.16 Hz,
40 reps/cell, SNR 20 dB, truth zeta 0.005 → 0.200 (a 40× span).

| estimator | source | Spearman rho | dynamic range | verdict |
|---|---|---|---|---|
| E1 `hilbert_env` | `studies/stock-baseline/stock_r97_ringdown.py` — *"the only estimator that passed"* | +0.829 | **7.6×** | 🛑 does not order |
| E2 `demod` | `studies/damping-q/r67_ringdown_q2.py` | **+0.371** | **1.7×** | 🛑 does not order |
| **E3 matrix pencil** | NEW, no filter at all | **+1.000** | **41.3×** | ✅ unbiased |
| E4 `twopole_psd` | the 2026-08-20 `8.162 Hz / Q 10.21` fit | +1.000 | see below | ✅ in its own config |

Recovered vs truth, E1/E2: `0.005 → 0.0047/0.0050` · `0.020 → 0.0197/0.0198` ·
`0.049 → 0.0467/0.0388` · `0.100 → 0.0497/0.0246` · **`0.200 → 0.0359/0.0084`.**
**Both SATURATE at zeta approx 0.05 and then REVERSE. E2 reads a zeta=0.20 mode as 0.0084 — 24× too
lightly damped.** Fine below zeta ~0.02, worthless above it — and the mode of interest sits on the boundary.

## 🛑 THE SHARPER DEFECT — the fit-window length IS the answer
Truth zeta = 0.049 fixed, only the post-edge fit length varied:
`E1: 0.0446 (0.5 s) · 0.0508 (1.0) · 0.0465 (1.5) · 0.0365 (2.0) · 0.0235 (3.0) · 0.0147 (4.0)` —
**3.5× swing from an analyst's free choice.** E2 is worse (6.3×).
`E3 pencil: 0.0460 / 0.0482 / 0.0485 / 0.0486 / 0.0484 / 0.0483` — **flat.**

## RECORD DEFECTS THIS PRODUCES
1. 🛑 **`rlog-tools/_scratch/out/_stock_r97_ringdown.json` IS UNQUOTABLE.** It runs `fit_s = 2.0` over 3–4 s
   post-windows, squarely in the biased zone. Route 0x97 has **exactly ONE qualifying edge** at that
   script's own criteria; **E3 refuses it while E1 at `fit_s = 2.0` returns zeta = 0.0030, i.e. Q = 167.**
   That single pair of numbers is the whole case against the file.
2. 🛑 **The recorded `zeta 0.017-0.036 / Q 14-29` is an E1 number** ⇒ an **UPPER BOUND on Q, not a
   measurement.** At those values E1 is only ~1.3× biased, so the zeta survives *qualitatively* — but
   `[[accord-ratchet-is-a-lightly-damped-resonance]]`'s Q must be read as a ceiling.

## ✅ THE 2026-08-20 `Q = 10.21` IS VINDICATED — and the bracket now CLOSES
The transient nulls are the wrong control for a steady-state PSD fit. Run the right one (white-noise-
driven 2-pole of known zeta, 400 s at 100 Hz, Welch NFFT 512 — the exact 2026-08-20 configuration):
`0.049 → 0.0525 (1.07×)` · `0.100 → 0.0997` · `0.200 → 0.2018`. **Essentially unbiased at zeta ~0.05.**
Its one real vulnerability is broadband contamination, which biases zeta **HIGH**, i.e. makes Q look
**smaller**. Measured floor/peak = **0.033** (median; route spread 0.009–0.186) ⇒ bias 1.14× ⇒
**recovered zeta 0.0490 ⇒ true zeta approx 0.0412 ⇒ true Q approx 12.1, range 10.7–13.3.**
**Q is UNDERSTATED, not overstated.**

## E3 IS THE REPLACEMENT — and it refuses every null
Hua-Sarkar matrix pencil on **RAW** post-edge samples — no band-pass, no envelope, so the filter
step-response artefact cannot arise by construction. Two defects found and fixed during validation:
pole selection must be by **residue** (min-zeta lets a noise pole win, AUC 0.798), plus a
**variance-explained gate** (mode alone must explain >= 35 %).
**0/40 on white noise · 0/40 on a perfect step · 0/40 on a phase-randomised real-data surrogate ·
0/200 on the step in the separation test — while returning zeta 0.0490 [0.0445, 0.0530] on 200/200
true zeta = 0.049 decays.** E1/E2 return a *finite* zeta on 40–55 % of pure-noise draws — the
`q_of = 79.00` failure mode, still live in the kit's current code.
**Sensitivity sweep passes:** recovery identical to 4 dp across {residue, min-zeta} × gate
{0.15…0.65}; nulls 0/40 at all 10 settings. Only gate 0.65 breaks it, by rejecting real zeta = 0.20.

## 🛑 E3'S OWN DEFECT, self-reported
**The ANALYSIS WINDOW LENGTH moves it** — same defect class E1/E2 died for. The variance gate is a
ratio over the window, and a zeta = 0.05 ring at 8 Hz is gone in ~0.4 s, so a longer window dilutes the
mode's share: injected-ring detections at A=4 go **3/7 (0.75 s) → 2/7 (1.0) → 1/7 (1.5, 2.0) → 0/7 (3.0)**.
**Any future use must state the window.**

## 🛑 AND THE REAL-DATA NULL LICENSES NOTHING
E3 refuses all 7 clean `latActive` falling edges across 6 routes (E1/E2 return numbers on 6 of the same
7, spanning zeta 0.0002–0.0998 — a **500× spread**). **But the positive control was run first:**
injecting a known ring at A × the pre-edge 6–9 Hz band RMS gives **0/7 at A=1 across all 50
combinations of the three free choices**; best case anywhere is 3/7, only at A=4 with the shortest
window. ⇒ **the disengage-edge instrument has essentially ZERO power at realistic amplitudes.**
Both the kit's recorded number and this 0/7 are honest nulls; **neither is evidence.**

Related: [[feedback-run-the-control-before-the-measurement]] ·
[[accord-ratchet-is-a-lightly-damped-resonance]] · [[accord-column-cannot-host-q10-at-8hz]]
