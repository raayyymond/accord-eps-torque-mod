# ANALYSIS — the V86 observer-leak retrodiction: NULL, and the design could never have resolved it

**2026-08-10 · agent `LeakDose` · persisted by the orchestrator (the harness blocked the subagent's
own file write; content is the agent's, verbatim in substance).**
**Study/analysis only. Nothing was built, flashed, or sent on CAN.**

Scripts and caches ARE on disk:
`analysis-2020accord/studies/sessions/v89/v89_e1_leak_retrodiction.py`, `studies/sessions/v89/v89_e2_leak_robustness.py`,
`studies/sessions/v89/v89_e3_leak_profile.py`, `studies/sessions/v89/v89_e4_leak_placebo.py` → `_scratch/cache/r73/v89_e{1,2,3,4}_*.json`

---

## HEADLINE

1. **The retrodiction is a NULL.** Against the whole α = 573 corpus, route `6f`'s 6–9 Hz band contrast
   sits at the **median** of a 213-pair placebo null (+0.066 vs a placebo median of −0.001).
2. **A wrong-direction "hit" appeared and died to its own control.** A 2-route comparison gave
   6–9 minus 32–38 = **−0.678 [−1.031, −0.287]**, jackknife-stable, against a prediction of **+0.654**.
   The placebo control shows the cross-build floor has **sd 1.03**, so −0.6 is the **22nd percentile of
   noise**. 🛑 **Do not cite the wrong-direction result.**
3. **The design is underpowered by 3.07×.** 21.6 % of placebo pairs at *constant* α reach the
   predicted +0.654 by chance alone.
4. **It had already been scored, and was already null.** `_scratch/cache/r6f/score_v86_bands.json`
   (2026-08-09) carries `creep_ratio["6-9"]["V86/r6f|V85/r6e"]` = **0.818 [0.517, 1.355], verdict
   NULL**, with a within-route null of [0.227, 4.399]. **It was never promoted into
   `BUILD-LINEAGE.md`**, which records only the frequency result.

**⇒ The leak lever has NO retrodictive support, and none is obtainable from flown data.
It is UNTESTED, not refuted.**

---

## 1. Single-variable check — EVIDENCE, full byte diff from the images

| pair | bytes | control cells | rest |
|---|---|---|---|
| V85 → **V86** | 68 | **`0xC40D4` `3d02` → `1e01` (573 → 286), 2 B — nothing else** | 62 B cave `0xC4B38`–`0xC4B77`, 4 B CRC |
| V85 → **V86B** | 74 | `0xD77DA` → `8c03`, `0xD77EE` → `6b03` (FactorC m26/m27 `Y[0]`); **`0xC40D4` stays 573** | cave + 2 CRC blocks |

**V86-vs-V85 IS single-variable on `0xC40D4`.** `0xC40BC` = 6000 on all three routes ⇒ the friction
gate cannot confound. Cell audit across V85 / V86 / V86B / V87 / V88 / V89:
573 / **286** / 573 / 573 / 573 / 573 ⇒ **n = 1 dose point in 30 routes.**

## 2. 🛑 A confound the brief did not carry: route `6e` is NOT parking-lot

| route | build | α | frames | engaged | v_max | eng < 5.2 m/s | eng ≥ 5.2 |
|---|---|---|---|---|---|---|---|
| `6e` | V85 | 573 | 43,641 | 35,794 | **28.25 m/s** | 2.7 min | **3.2 min** |
| `6f` | V86 | **286** | 23,058 | 14,161 | 5.38 | 2.3 min | 0.0 |
| `70` | V86B | 573 | 21,428 | 9,208 | 5.97 | 1.5 min | 0.0 |

`6f` and `70` are parking-lot; **`6e` reaches 101.7 km/h** and has more engaged time above 5.2 m/s than
below. Everything must be capped at v < 5.2 for common support, costing **54 % of `6e`'s engaged
exposure**.
**Loader check:** whole-route npz == sum of segments exactly (43,641 / 23,058 / 21,428). The `v89_c1`
glob bug does **not** bite here.

## 3. Controls — run first, as required

- **C1, within-route split-half null** (6–9 minus 32–38 contrast): `6e` half-width 0.270 ·
  **`6f` 1.147** · **`70` 1.196**. Raw 6–9 split-half ratios: `6f` [0.17, 5.27], `70` [0.19, 5.53].
  Independently corroborated by the 2026-08-09 cache ([0.385, 2.543] / [0.399, 2.492]).
  ⇒ **A 3.2× effect is already at `6f`'s own within-route floor.**
- **C2, a real pair at constant α (`6e` vs `70`):** contrast −0.074 [−0.612, +0.488]. But 18–22 Hz
  alone moves **−0.900 [−1.459, −0.350] at constant α** ⇒ **18–22 Hz is not a trustworthy cross-build
  band.**
- **C3:** the 32–38 Hz control is **NOT clean** — the model predicts +0.225 there, which biases the
  contrast downward (i.e. conservative for the hypothesis).
- **C4, the manual arm:** α is not engagement-gated, so the effect must appear there too. All null;
  6–9 contrast −0.023 [−0.671, +0.566].

## 4. Model reproduction

Reproduced at fs = 1000 Hz with a 1-tick delay; `0xC63AC` = 102 byte-verified on all six images.
Log-ratios 286-vs-573: **6–9 +0.879 · 18–22 +0.508 · 26–31 +0.329 · 32–38 +0.225**; contrasts vs
32–38: **+0.654 / +0.283 / +0.104**.

⚠ Absolutes differ from the orchestrator's table (0.190 vs 0.637 at 7.79 Hz) — the two are
differently normalised — but the **ratios and the monotone-decreasing shape reproduce.**

🛑 **Every prediction is an UPPER BOUND** (observed = leak-fraction × prediction) ⇒ **no amplitude null
can refute this hypothesis. Only the *shape* is scale-free.**

## 5. What collapsed

**2-route fit** (102 windows / 19 blocks): 6–9 contrast −0.678 [−1.031, −0.287]; 18–22 −1.774;
26–31 +0.100 [−0.148, +0.443] (matches the predicted +0.104 but cannot resolve it). Jackknife over
19 blocks [−0.792, −0.582], **zero sign flips**. `6f` vs `70` alone −0.577 [−1.044, −0.021];
`6f` vs `6e` alone −0.622 [−0.992, −0.232].

**14-slice profile** (per-band veto): −0.39 / −0.34\* / −0.45\* / −0.47\* / −0.93\* across 6–21 Hz,
then **positive** +0.54 / +0.08 / +0.22 / +0.18 at 24–36 Hz.
**corr(observed, model) = −0.640, Spearman −0.643** — the observed profile **rises** with frequency
where the model **falls**.

**🛑 PLACEBO CONTROL — 213 pairs, every constant-α route pair, v < 5.2 engaged:**

| statistic | placebo null | `6f` v `6e` | `6f` v `70` | `6f` v all 23 |
|---|---|---|---|---|
| S1: 6–9 minus 33–36 | median −0.001, **95 % [−2.171, +1.849]** | −0.522 (**22nd pct**) | −0.452 (26th pct) | **+0.066** |
| S2: corr(profile, model) | median 0.000, 95 % [−0.811, +0.789] | −0.613 (6.5 pct) | −0.693 (4.3 pct) | −0.237 (p = 0.283) |

**Placebo sd 1.025 against the block-bootstrap half-width of 0.37 that made §5 look significant —
a factor of 2.8.**

## 6. Power

sd 1.025 · detectable effect, one route vs one route, **±2.010** · prediction **+0.654**
⇒ **underpowered 3.07×** · the prediction is **0.90 σ** of a single-route offset · **21.6 %** of
placebo pairs reach +0.654 by chance. **The limit is structural: α = 286 exists on exactly one route.**

---

## 7. 🛑 DEFECTS FOUND — reported, not fixed

1. **Episode block bootstraps understate cross-build uncertainty by ~2.8× here** (0.37 vs 1.03).
   ⇒ **Any cross-build ratio in this kit quoted with a block-bootstrap CI and no placebo-pair null is
   over-confident.** This plausibly affects earlier cross-build claims and **is worth a dedicated
   audit.**
2. **The kit's orders-1–6 wheel-order veto never fires on 32–38 Hz at parking-lot speed** (the
   fundamental is < 2.51 Hz, so order 13+ would be needed), while orders 3–4 hit 6–9 Hz constantly
   ⇒ **asymmetric screening between the band and its own control.**
3. `v89_e2`'s R2/R5 were degenerate (a union veto over 14 slices left 11 of ~300 windows). Superseded
   by `v89_e3`. **Do not quote R2/R5 from `v89_e2_robust.json`.**

## 8. What would actually test it

**Not another parking-lot route.** The prediction is frequency-*shaped*, so the discriminating
measurement is **within-route, within-drive**: two α values alternating under matched exposure (or a
switchable α), scored on the **shape** statistic S2 rather than on any single band.

Absent that, an α lever is a **bet**, and this retrodiction **cannot be cited as support in either
direction**.

---

# ADDENDUM — the `gp-0x6b70` residual probe (agent `LeakDose`, final)

Scripts: `analysis-2020accord/studies/sessions/v89/v89_f1_residual_probe.py`, `studies/sessions/v89/v89_f2_residual_pooled.py`
→ `_scratch/cache/r73/v89_f1_residual.json`, `_scratch/cache/r73/v89_f2_pooled.json`.

## ★ HEADLINE — the residual and the symptom have SWAPPED signatures, CIs disjoint on BOTH axes
Same **175 engaged windows / 8 episode blocks**, same model, three responses. **[EVIDENCE]**

| response | log \|cmd\| rms | log \|rate\| |
|---|---|---|
| **logit b5 — the RESIDUAL `gp-0x6b70`** | **−0.012 [−0.659, +0.472] NULL** | **+0.774 [+0.515, +1.178] ✔** |
| **log `e_6-9` — the SYMPTOM (column)** | **+1.074 [+0.812, +1.445] ✔** | **+0.100 [+0.021, +0.220]** |
| log `e_32-38` — negative control | +0.124 [−0.110, +0.431] NULL | +0.369 [+0.186, +0.510] |

⇒ **The observer residual and the 6–9 Hz symptom do not share a driver.** The symptom is
**command-magnitude driven and band-specific** (contrast +0.950 vs the control band ⇒ not merely
"more motion"); the residual is **wheel-rate driven and command-independent**.
⊕ The symptom's magnitude-yes/rate-no signature **independently reproduces the 30-route corpus
result on two different routes with a different instrument.**

## Item 1 — engagement effect on the residual: NULL
🛑 The raw +16.3 pp on `6f` (ENG 0.9452 vs MAN 0.7818) is an **exposure artefact** — manual frames
spent parked. Under the standard motion screens the manual arm reads 0.9422; gap **+0.6 pp**.

| | windows / blocks | adjusted eng log-odds | verdict |
|---|---|---|---|
| `6f` (α=286) | 153 / 6 | −0.221 [−0.477, +1.908] | NULL (underpowered) |
| `70` (α=573) | 138 / 10 | +0.099 [−0.520, +0.584] | NULL |
| **pooled + route dummy** | **291 / 16** | **−0.083 [−0.507, +0.513]** | **NULL, well-centred** |

## Item 1b — sign coupling: NULL, through three controls
`f1`'s segment-permutation null had only 4 exchangeable units ⇒ **discard it**. A circular-shift
surrogate then made lag-0 on `6f` look significant — **it dies on the extended lag sweep: agreement
peaks at +100 frames = +1.00 s** on both routes (0.657 / 0.631). A control-loop coupling peaks
within tens of ms; a 1-second peak is **manoeuvre-scale co-drift**.
⊕ **Positive control:** `b7` agrees with `sign(driver torque)` at **0.879 / 0.886** versus
0.581 / 0.559 with the command ⇒ **the probe works and the observer is behaving sanely.**

## Rung controls — half the V86 cave carries nothing
`b6` railed ≥ **0.9955** in both arms on both routes ⇒ carries nothing. `b4` railed at exactly
**1.0000** ⇒ engagement cannot act through the aggregator gate. `b5` *is* live (window duty p5→p95
spans 4.7 log-odds despite 19–22 % of windows at duty 1.000).

## Identity — verified, not assumed
Probe alphabet **{31, 95, 127, 223, 255}** on `6f`, **{31, 63, 127, 191, 255}** on `70` ⇒ the b5/b6
weight swap is **directly visible in the raw alphabets**, and the magnitude rung nests exactly inside
the non-zero rung, fixing the weights parameter-free.

## P4 — does the residual co-move with the symptom? NULL
Partial corr (removing `e_32-38`, log v, log rate, route) = **−0.144**, block-permutation null 95 %
[−0.148, +0.120], p = 0.043. **At the edge of its own null, tiny, and negative.** Not reported as a
finding.

## Item 3 — V86/V85 6–9 Hz amplitude, bounded side result
Engaged, speed-matched, episode-bootstrapped: raw **0.68×** (log −0.390 [−0.895, +0.169]); prior
on-disk cache gives 0.818 [0.517, 1.355] NULL. Floors: `6f` within-route split-half **[0.17, 5.27]**;
cross-build placebo **±2.0 log units**. ⇒ **Uninterpretable.**

## 🛑 EXPOSURE CAVEAT ON ALL OF THE ABOVE
Two parking-lot routes, v_max 5.38 / 5.97 m/s, **0.0 s engaged ≥50 km/h**, 4 engaged episodes each,
8–16 blocks pooled. Item 1 pooled and item 2 are adequately powered (CIs tight and disjoint);
`6f`'s standalone item 1 is not.

## Defects (reported, not fixed)
1. `v89_f1`'s shuffled-pairs sign null is built from 4 segments and is uselessly wide — **do not
   quote `v89_f1_residual.json["sign"]`**; use `v89_f2_pooled.json["sign"]` with the lag-sweep caveat.
2. Carried: **episode block bootstraps understate cross-build uncertainty ~2.8×**; the orders-1–6
   veto never fires on 32–38 Hz at parking-lot speed while orders 3–4 hit 6–9 Hz constantly;
   `v89_e2`'s R2/R5 are degenerate.
