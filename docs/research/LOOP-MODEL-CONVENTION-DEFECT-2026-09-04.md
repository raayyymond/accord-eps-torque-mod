# 🛑 DEFECT OF RECORD — the kit carries TWO loop models in OPPOSITE sign conventions, and they disagree at 7.3 Hz

**Subagent `znback`, 2026-09-04.** Filed as a standalone note at `team-lead`'s instruction because
this is a defect **in the record**, not in any one analysis, and it will mislead the next agent
exactly as it nearly misled this one. **Grep terms:** `convention defect` · `two loop models` ·
`sign convention` · `L/(1+L)` vs `L/(1-L)` · `closed-loop T(f) not computable` · `ring vs Nyquist`.

Reproduce with: `python analysis-2020accord/studies/pidframe/zn_fidelity.py` (SECTION 0).

---

## 1. THE TWO MODELS

| | **(a) NYQUIST / GAIN-MARGIN model** | **(b) MEASURED RING model** |
|---|---|---|
| where it lives | `ZN-ACCEL-FRAME-V285-ADDENDUM-2026-09-04.md` §A3; `studies/zn285/zn_ku_corrected.py` | `STUTTER-7HZ-V283-r36-r38-2026-09-03.md` §A13–A14; the `|L|` = 0.976 figure everywhere |
| convention | **NEGATIVE feedback.** Instability at `∠L = −180°`, closed loop `T = L/(1+L)` | **POSITIVE feedback around the ripple.** Sustained oscillation at `L = +1`, margin `\|1−L\| ≈ 1/Q`, `T = L/(1−L)` |
| what it contains | one smooth forward path: byte-exact `C` × output lag × feedback EMA × a plant modelled as **flat magnitude with a −3.75°/Hz phase slope** | a **two-arm sum**, `L_tot = Ls + Lr`, from measured ripple shares — a servo arm and the **r24 arm** |
| anchored on | the item-4 `\|L(20)\|` row and the measured plant phase at 10/22 Hz | a per-episode complex-ACF fit, 5 episodes, `Q = πf₀/α` |
| valid where | **20–32 Hz** — near its anchor, for gain-margin/Ku questions | **at `f₀ ≈ 7.3 Hz` only** — it is a single-frequency composition, not a curve |

## 2. THE DISAGREEMENT, AT 7.3 Hz

| | model (a) says | model (b) says |
|---|---|---|
| `\|L(7.3)\|` | **1.319** | **0.976** |
| `∠L(7.3)` | **−71.5°** | ≈ **0°** (a sustained ring must be near `+1`) |
| closed-loop peak | `\|1+L\| = 1.89` ⇒ `\|T\| = 0.70` — **NO PEAK AT ALL** | `\|1−L\| = 0.024` ⇒ `Q ≈ 42` — **a ~42× resonance** |

**They are not two views of one loop. They are two different loops.** Model (a) is a smooth delay
model fitted at 20 Hz: it contains **no plant resonance** and **no r24 lane whatsoever**. The 7.3 Hz
ring is measured to live in the r24 arm — `FUN_0003aa2c`, which references **neither** `0xE5378` (Kp)
**nor** `0xE511C` (Kd). Model (a)'s single forward path simply does not include the mechanism model
(b) is describing.

## 3. 🛑 THE CONSEQUENCE — a single closed-loop `|T(f)|` curve is NOT computable from what has been measured

Do not build one. Specifically, **these three quantities cannot be produced honestly today**:

1. **A full `|T(f)|` curve** — §2. Whichever model you pick is wrong about the other's band.
2. **`f_-3dB` (closed-loop bandwidth)** — needs the plant **MAGNITUDE** above ~5 Hz. The record
   measures the plant's **phase** (−28° @ 10 Hz, −73° @ 22 Hz) and its **DC gain** (from four
   sustained `(|T|, rate)` pairs), and **never its magnitude in between.** Any `f_-3dB` is an
   artefact of assuming flat.
3. **`max|T|` over 0–50 Hz** — the ~20 Hz creep line has **no measured `|L|` at all**:
   `CREEP-20HZ-LOOP-ID-2026-09-03.md` §0 item 7(a) shows `L_in(line) = −1 by construction` at a
   spectral line inside a closed loop, so any margin read there is a tautology. **Its peak height is
   unquantified in BOTH directions.**

## 4. WHAT YOU MAY DO

- **Gain-margin / Ku / blind-band questions (20–32 Hz):** use model (a). Report `GM` and `Ku`.
- **7.3 Hz ring questions:** use model (b), and **only as a RATIO between candidates.** `zn285` §5.3
  item 5 explicitly warns the absolute `Q ≈ 41` does not map to felt amplitude (the operator reports
  "a damped ring at ~40 %"). **Never convert `|L|` into a predicted amplitude.**
- **Never compose a number that crosses the two.** If a quantity needs both bands, it is not
  computable — say so.
- **When quoting `|L|`, always state which model and which frequency.** The value `0.976` has already
  been mis-attributed once in this record: it was written as a 20 Hz figure when it is a 7.3 Hz one,
  and that single mis-attribution produced the retracted `Ku ≈ 143–151`.

## 5. ⚠ A SECOND, RELATED READING TRAP IN `CREEP-20HZ-LOOP-ID` §1.4

The §1.4 table reports **`GM = none` in 8 of its 10 rows**, and only the two `bar-IV` rows give a
number (`1.75× @ 23.4 Hz`, `1.32× @ 22.4 Hz`). **That is not "8 estimators found no mode."**

- **The table scans 2–24 Hz only** (its own heading). The `cmd-IV` rows are still at −148…−164° at
  22 Hz with a **−6°/Hz** slope, so they cross −180° at **24.7–27.3 Hz — just outside the window.**
  For that family, `none` means **not scanned**, not absent.
- The `bar-IV` rows report a GM precisely because they carry the **most** phase lag (−8.5…−9°/Hz) and
  therefore cross **earliest**, at 22.6–23.8 Hz — inside the window.
- 🛑 **The `direct` family is the genuine dissenter:** its phase goes −145° → −144° from 20 to 22 Hz,
  i.e. **advancing, not lagging.** It shows no approach to −180° at all. One of three families does
  not support the crossing.
- **The whole table is labelled BELIEF by its own author** — "off-line `G` has coherence 0.3–0.6";
  only `|L(20)| ≈ 1` is EVIDENCE.

**Net:** the 27–32 Hz crossing's **existence** is supported by 2 of 3 estimator families, but the
**gain margin at it spans roughly `1.57×` to `4.11×`** across families (crude extrapolation of the
published rows to each family's own −180° point). `Ku = 227` is therefore the **conservative,
worst-family** choice — the right call for a safety bound, but it should be quoted as such and not as
a measurement. Anyone reading "Ku is MEASURED-grade" should read this section first.
