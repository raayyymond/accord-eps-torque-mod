---
name: accord-ratchet-is-engagement-required
description: "★★★★ 2026-08-04 [EVIDENCE]: with the grip confound removed, the ratchet is engagement-REQUIRED, not conditional — 73/88 = 83.0% engaged hands-off vs 0/118 = 0.0% manual hands-off across four routes/builds, p=3.8e-41. And the rate is BUILD-INDEPENDENT (80/81/79/94%) ⇒ no build in this kit has ever moved the ratchet."
metadata:
  type: reference
---

# ★★★★ THE RATCHET IS ENGAGEMENT-**REQUIRED** — AND NO BUILD HAS EVER MOVED IT

**[EVIDENCE]** Grip confound removed: **both arms hands-off** (`|lowpass(tq, 3 Hz)| ≤ 300`), **creep
< 4 m/s**, pooled over four routes and four builds.

| route | engaged hands-off | manual hands-off | Fisher p |
|---|---|---|---|
| V70 `r50` | 4/5 = **80%** | 0/35 = **0%** | 5.5e-05 |
| V69 `r4f` | 22/27 = **81%** | 0/20 = **0%** | 9.4e-09 |
| V62 `r37` | 31/39 = **79%** | 0/39 = **0%** | 2.3e-14 |
| V59 `r2c` | 16/17 = **94%** | 0/24 = **0%** | 1.7e-10 |
| **POOLED** | **73/88 = 83.0%** | **0/118 = 0.0%** | **3.8e-41** |

**ZERO hits in 118 manual hands-off creep windows / 302 s.**
⇒ 🛑🛑 **the rate is BUILD-INDEPENDENT (80 / 81 / 79 / 94%) — NO BUILD IN THIS KIT HAS EVER MOVED THE
RATCHET.**
⚠ **This SUPERSEDES the earlier "engagement-conditional, 44/46 windows"** statement
([[accord-ratchet-characterised-on-route-4f]]) — same phenomenon, far better-controlled data.
★ **Converse: a hand on the wheel SUPPRESSES it while engaged** — V59 94% → 14% (p = 3.5e-4),
V69 81% → 37% (p = 4.5e-3).

## ★★★★ The transition trace — second by second, at constant speed
**[EVIDENCE — 4th-order Butterworth 6–9 Hz, `sosfiltfilt`, 2.56 s windows, hop 64; mono = seg1 `t` +
100.6; orchestrator-verified from `_scratch/cache/r50/r50s1.npz`.]**

| seg1 `t` | mono | `lat` | effort | RAW p-p | **6–9 Hz p-p** |
|---|---|---|---|---|---|
| 27.5 | 128.1 | 0.00 | 2646 | **6502** | **190** |
| 33.3 | 133.9 | 0.00 | 942 | 3237 | 136 |
| **33.9** | **134.5** | **0.06** | **320** | 1423 | **134** |
| **34.6** | **135.2** | **0.31** | **441** | 3182 | **1179** |
| 36.5 | 137.1 | 1.00 | 998 | 5070 | **2452** |
| 46.1 | 146.7 | 1.00 | 1548 | 4204 | 910 |
| 46.7 | 147.3 | 1.00 | 2129 | 3019 | **273** |

★★ **The headline pair:** `t = 33.9` (`lat` 0.06, effort 320) → **134 counts** vs `t = 34.6` (`lat`
0.31, effort 441) → **1,179 counts** — **8.8× in 0.7 s**, with **speed FALLING (1.75 → 1.60 m/s)** and
effort roughly flat, so **speed moves the wrong way for any confound.** The death is as sharp: effort
**1,548 → 2,129** over 0.6 s collapses the band **910 → 273.**
⇒ **it comes on tracking `latActive` and goes off when the driver grips.**

## ✅ The 6,502-vs-591 instrument discrepancy is SETTLED
At mono 127.5–128.1 the car is at `lat = 0.00`, effort **2,550–2,646**, and the 6–9 Hz content is
**190 counts** ⇒ **6,502 is RAW BROADBAND — the operator cranking, not the ratchet.**
★ **The ratchet proper runs seg1 `t` ≈ 34.6 → 46.1 (mono 135.2 → 146.7), ~11.5 s** ⇒ 🛑 **burst #0's
ratchet onset is mono ≈ 135.2, NOT 123.69.** That is the clean-material window.
✅ **[[accord-ratchet-q-measured-40]] was measured on the right data** — the episode reconciles
(2 × 2,452 = 4,904 ≈ 4,894; speed span matches `t` ≈ 33–46, post-engagement, not the cranking).

## 🛑 A correction to the operator's framing — the causal order, not the facts
**His hard MANUAL provocation produced NO ratchet at all** (effort 2,500–2,900; 6–9 Hz p-p **422–797**,
prominence **1–6**). **The manoeuvres SET UP the condition** — creep, loaded wheel, LKAS about to take
over — **and the ratchet fires when LKAS ENGAGES AND HE LETS GO.**
★ **Both parts of his account are correct; the causal order is the other way round. His report is
corroborated, not contradicted** — he named the right segments before the data did. See
[[feedback_operator_lived_experience_overrides_analyst_recs]].

## ⇒ What the build-independence buys
★★ **`0x454FE` is a genuinely UNTESTED lever for the ratchet** — it has not been on the car during a
single one of the four measurements above (V59/V62/V69/V70 are all post-V53, all stock at `0x454FE`;
[[accord-both-confirmed-fixes-were-off-the-car]]). ⚠ **A reason to restore it; NOT evidence it will
work** — [[accord-state4-cadence-refuted-state-is-sticky]]'s symmetry tension still argues against the
mechanism.
★★ **And four facts fit one picture:** *engagement-required* + *hands-off-conditional* + *Q ≈ 40* +
*base-assist damping exactly ZERO below ~35 km/h* ⇒ **at creep, the driver's hand is the only damping
in the system.** That is what makes the deferred FactorC/FactorE lever materially more compelling —
still deferred, still its own single-variable drive.
