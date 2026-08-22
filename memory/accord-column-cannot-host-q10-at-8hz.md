---
name: accord-column-cannot-host-q10-at-8hz
description: "The upper steering column measured engaged+hands-off is a J*s+b element with a 4.6 Hz corner, and its 8 Hz phase of arg Z = 117-150 deg admits Q <= 2.8 at 8.16 Hz where Q=10 would require 95.7 deg. Scale-free, band-free, model-free, single-bin. STRONG CONSTRAINT with ONE named untested assumption - the passive-arm falsifier is UNTESTABLE on this corpus."
metadata:
  type: reference
---

# ★★★★★ THE PASSIVE COLUMN CANNOT HOST A Q≈10 RESONANCE AT 8.16 Hz

2026-08-21. `rlog-tools/plant_phase_corner.py`, `plant_Jb_absolute.py`, `plant_falsifiers.py`.
**Orchestrator re-ran all three and checked the arithmetic independently.**

## ⭐ THE SINGLE-BIN FORM — the version no band-consistency objection can touch
Hands off, the upper column obeys `J_w*theta'' + b_w*theta' = -T_bar`, so
`Z = T_bar/Omega_w = -(b_w + j*w*J_w)` and `tan(180deg - |arg Z|) = w*J_w/b_w`.
Since `Q = w_n*J_w/b_w`, **at `w = w_n` these collapse:**

> **`Q(at the mode) = tan(180deg - |arg Z|)`, evaluated in that ONE bin.**
> No band. No `k`. No counts scale. No deg/s scale. No cross-frequency model.

Engaged hands-off, 7.5–8.5 Hz bin:

| route | eps | coh^2 | \|arg Z\| | Q = tan(180−a) | Q [95 % CI] |
|---|---|---|---|---|---|
| **V9b STOCK** | **13** | 0.742 | **117.4 deg** | **1.93** | [1.51, **2.77**] |
| V103 | 6 | 0.842 | 132.2 | 1.10 | [0.30, 1.33] |
| V102 | 8 | 0.759 | 150.2 | 0.57 | [0.41, 0.64] |
| V88 | 4 | 0.711 | 131.4 | 1.13 | [0.96, 1.27] |
| V100 4x | 3 | 0.888 | 117.2 | 1.94 | [0.85, 2.08] |

**For Q = 10 the 8 Hz bin would have to read `|arg Z| = 95.71 deg`** — `Z` within 5.7 deg of pure
inertia. **Measured: 117–150 deg.** Every bin is coh^2 0.71–0.89. **Largest upper CI anywhere: 2.77.**
Check it in one line: `tan(180-117.4) = 1.93`; `180 - atan(10) = 95.71`.

## THE ABSOLUTE FIT, and the physical check it could have failed
4–12 Hz, episode bootstrap 3000, engaged hands-off. Scale from [[accord-rate-f-is-0p7996-of-true-degs]]:

| route | eps | J_w (ct*s^2/deg) | b_w (ct*s/deg) | b/J rad/s |
|---|---|---|---|---|
| V9b STOCK | 13 | **1.248** [1.110, 1.358] | 35.8 [19.9, 42.5] | **28.7** |
| V100 4x | 3 | 1.202 [0.814, 1.449] | 35.0 [14.4, 45.9] | 29.1 |

**STOCK and V100 agree to 4 % on J_w and 2 % on b_w on independent drives.**
⭐ **J_w = 0.87–1.25 ct*s^2/deg => 0.033–0.078 kg*m^2, against the handbook steering-wheel + upper-column
figure of 0.03–0.06 — the very range `ANALYSIS-2026-08-20` §2 itself assumed. It lands on it.**

🛑 **`J_w*s^2` IS NOT DOMINANT AT 6–9 Hz — it is merely the LARGER term.** The column's own corner is
**4.6 Hz**, just below the band, and `|J_w*w|/b_w` = 1.32 / 1.64 / 1.97 at 6 / 7.5 / 9 Hz ⇒ **the
damper still contributes 45–60 % of `|Z|` across the band.** Any argument treating `H(s)` as
inertia-dominated at 6–9 Hz is wrong by ~2× in magnitude and ~55 deg in phase.
⚠ **`b_w` is a RANGE, not a value** — across six fit bands `J_w` moves 1.25× but `b_w` moves **3.1×**,
driven by the band's lower edge. `J_w` is the solid number.

## 🛑🛑 THE ONE UNTESTED ASSUMPTION — state it every time this is cited
Falsifier F1 was a **manual (LKAS-off) + hands-off** arm. The data **exists** — 98 windows, 502 s
corpus-wide — it was simply not run at first. Run: **coherence at 4–10 Hz is 0.005–0.016, 20–60× BELOW
the falsifier's own 0.30 gate.**
⇒ **F1 IS UNTESTABLE ON THIS CORPUS, for a PHYSICAL reason, not a missing-data one.** With LKAS off
*and* hands off there is essentially no 4–14 Hz excitation of the column, so the cross-spectrum
measures noise. This is [[accord-vibration-requires-lkas-engaged]] (9,200× less power LKAS-off) seen
from the other side: **the excitation the estimator needs only exists when engaged.**

⇒ The conclusion rests on **engaged arms plus the anti-damping direction argument**: loop anti-damping
at 6–9 Hz reduces apparent `b_w`, so engaged `J/b` **overstates** passive `J/b`, so the measured Q is
an **upper bound**. Directionally sound, but **load-bearing and untested — the weakest link.**
A scripted maneuver drive cannot close it either (`lateralManeuverPlan` requires `latActive`). Closing
it needs a bench measurement of the column.

## Falsifier F2 and the arm spread
- **F2** (CV of the per-bin ratio > ~0.5 on bins with coh >= 0.50): **4 of 5 routes survive**
  (STOCK 0.146, V103 0.454, V88 0.181, V100 0.376); **V102 genuinely TRIPS at 0.721.** Not explained
  away. Post-hoc: no route shows a *localised* 8 Hz excursion (7.5–9 Hz residual −0.85..+0.83 sd,
  V102 least of all at +0.07); V102's failure is a steep *smooth* slope. ⚠ **The log-log slope is
  negative on EVERY route (−0.51 to −4.32) where a pure `J*s+b` demands zero ⇒ the 2-parameter model
  carries a systematic smooth error everywhere.** The single-bin form above is immune to all of this.
- **Arm spread:** hands-on is a different mechanical system (the identity assumes zero driver torque),
  so arms *must* differ — that is control C4 passing. **Hard bound over EVERY arm, admissible or not:
  the most permissive upper 95 % CI anywhere is Q = 5.24–7.34. No arm reaches Q = 10.**

## HOW TO STATE IT
> *"The passive upper column, as measured engaged and hands-off, cannot support a Q≈10 resonance at
> 8.16 Hz; the passive-arm cross-check that would rule out a loop artefact in that measurement is not
> available on this corpus."*

🛑 **A STRONG CONSTRAINT WITH ONE NAMED UNTESTED ASSUMPTION — NOT a retraction of
[[accord-ratchet-is-a-lightly-damped-resonance]].** It corroborates
[[accord-the-8hz-mode-is-the-loop-not-the-plant]] from an independent instrument.

⚠ **OPEN DEFECT:** `|Z|` rolls off un-modelled above ~13 Hz (STOCK `|Z|/w`: 1.54, 1.50, 1.41, 1.39,
1.33 flat 6→12 Hz, then 1.15 @14, 0.45 @16). Not rate-channel noise, not torque noise. **If `tq` is
internally low-passed near there, every kit `|Z|` above ~10 Hz inherits it — including the 21–24 Hz
work.** NOT CHASED.
⚠ Under an explicit hands-off mask the 2-pole fit lands at **10.5 Hz, not 8.162** (zeta 0.072–0.184).
Mask difference vs §2 unresolved. Either way the spectral peak is 4–8× more resonant than the passive
column can be, which is the point.
⚠ C2 Coulomb test **UNDERPOWERED**: `d log b_w / d log V = −0.11 [−1.12, +0.72]` spans both −1
(Coulomb) and 0 (viscous). Needs a wider rate range than hands-off windows provide.
