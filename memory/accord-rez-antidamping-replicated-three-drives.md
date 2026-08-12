---
name: accord-rez-antidamping-replicated-three-drives
description: "Re(Z) < 0 from 2 to ~24 Hz, sign-flipping to damped at ~26 Hz, now replicated on THREE independent drives of the same functional car — and it is STRONGEST in the micro-ratchet regime the operator says is unfixed."
metadata:
  type: reference
---

# ★★★★★ THE ANTI-DAMPING REPLICATES THREE TIMES — and it peaks in the operator's unfixed regime

Routes **77 (V90) / 78 (V91) / 79 (V92)**, 2026-08-11. All three are **calibration-identical** (see
`[[accord-cbe74-dose-measured-inert-wrong-mode-record]]`), so this is **one car measured three
times**, not a build contrast. Tool: `rlog-tools/v92_boost_lane_and_rez.py`.
Estimator is the FROZEN `decode_v90_probe._wins` / `_band_transfer`; both channels are fields of the
**same `0x18F` frame**, so staleness cancels exactly in `Z = S_Tw/S_ww`.

## THE REPLICATION [EVIDENCE] — `Re(Z)`, ct·s/rad, engaged + hands-off + moving

| band | r77 (221 win) | r78 (188 win) | r79 (219 win) | coh² range |
|---|---|---|---|---|
| 2–4 | −1269 | −1394 | −1159 | 0.20–0.23 |
| 6–9 | **−3375** | **−3176** | **−3073** | **0.71–0.77** |
| 9–12 | −4593 | −4130 | −4370 | 0.76–0.83 |
| 12–16 | −3858 | −4020 | −3880 | 0.60–0.66 |
| 18–22 | −653 | −625 | −689 | 0.44–0.75 |
| 22–26 | −268 | +0.2 | −11 | the **zero crossing** |
| 26–31 | **+233** | **+370** | **+671** | 0.48–0.83 |

Shuffled controls ≈ 0.000 everywhere. **6–9 Hz reproduces within ±5 % across three independent
drives.** The **sign flip at ~24–26 Hz is on all three** ⇒ *grind #2's band is not anti-damped at
all*, corroborating the dissociation in `STATE.md` §F from a second instrument.

## ★ THE NEW RESULT — it is STRONGEST in the MICRO regime

Windows classified by their **own median |wheel rate|** (the instantaneous mask yields **0**
scoreable windows — a census artefact, not a null; `rlog-tools/v92_micro_regime.py`), pooled over
all three routes:

| band | static <1 °/s (457 win) | **MICRO 1–13 °/s (167 win)** |
|---|---|---|
| 6–9 | −2847 (coh² 0.710) | **−3480 (coh² 0.804)** |
| 9–12 | −3771 | **−4890 (coh² 0.815)** |
| 18–22 | −641 | −657 (coh² **0.802**) |
| 22–26 | +7 (**not trusted**, coh² 0.047) | −245 (coh² 0.734) |

⇒ **The anti-damping is largest and most coherent in exactly the 1–13 °/s regime the operator
reports as still unfixed** ("micro-ratcheting / micro-stuttering… turning angle rate still limited").
🛑 **This is an alignment between instrument and symptom, NOT a demonstration of cause.**
🛑 Ratchet (13–50 °/s) and macro (>50 °/s) are **NOT SCOREABLE** — 4 and 0 windows. Sustained fast
steering does not survive the hands-off mask. **That is the binding census limit for the next drive.**

## WHAT IT STILL DOES NOT SETTLE

`STATE.md` §C's gating experiment — **is the 2–26 Hz anti-damping in the PLANT or the firmware
loop?** — remains **unrun**. The discriminator is the **manual hands-off coast**, and these two
routes contain **1.8 s (r78) and 0.0 s (r79)** of it. Still ~15–20 min of driving owed.
See `[[accord-ratchet-is-a-lightly-damped-resonance]]`, `[[accord-v90-flew-probe-only-control-condition]]`.
