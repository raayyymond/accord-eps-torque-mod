# SCORING 2026-08-10 — the V89 flight, routes `75` and `76`

**Verdict line:** V89 **flew** and its probe **fired**, but **H2 FAILED** — no resolvable
band-specific fall in the ratchet band — and the mechanism for the failure is visible in V89's own
probe: **the term K1 doubles is zero or negligible across the whole micro-ratcheting regime.**
H3 passed (nothing fell). The operator scored it *"fixed nothing, still only as good as V88"*, and
**every instrument here agrees with him.**

Data: `_cache_r75/` (16 segments) and `_cache_r76/` (13 segments), extracted by
`rlog-tools/extract_r75_r76.py`. Comparison arm: `_cache_r73/` (V88), which already existed and was
**not** re-extracted. Scripts: `analysis-2020accord/v89_e1_identity.py`, `v89_e2_h2h3.py`,
`v89_e3_contrast.py`, `v89_e4_inertia.py`, `v89_e5_t2contrast.py`, `v89_e6_bar_impedance.py`.
Logs and JSON alongside them in `_cache_r75/`.

---

## 0. Method provenance — the instrument was not reimplemented

`extract_r75_r76.py` adds rows to `decode_v84_probe_r6d.ROUTES` and calls that module's
`extract()` / `split()`, exactly as `extract_r6e.py` / `extract_r6f_r70.py` / `extract_r71.py` /
`extract_r73.py` do. Field names, ZOH/interp convention, IMU axis pick, sentinel definition and
`PASS_1D` are therefore bit-for-bit the ones every prior route was scored with. **Smoke test: it
reproduces route 73's published census exactly** — 61,161 frames / 613.4 s / 72.66 % engaged /
119.6 s ≥50 km/h. Scoring reuses `_grind2_lib.wrecs` (NFFT 256, hop 128, p99 analytic band
envelope, ~10.2 s `blk` units), `boot_cellwise` (cell-stratified log-ratios over
(eng, speed-bin, effort-bin, rate-bin) — speed- *and* rate-matching is inside the estimator),
`split_half_null`, `_r47_lib.augment`, and `compare_v75_v76_v80_grind.BANDS_EXT` (which is what
installs the 32–38 Hz negative control).

🛑 **The raw14 off-by-one was respected throughout.** Every cave read uses `(raw14_t, raw14_b4)`;
the families are never crossed.

---

## 1. Fault status — both routes clean [EVIDENCE]

| | r75 | r76 | r73 (V88) |
|---|---|---|---|
| frames / duration | 93,244 / 932.2 s | 75,911 / 760.8 s | 61,161 / 613.4 s |
| ENGAGED | 583.7 s = **9.73 min** (62.6 %) | 657.2 s = **10.95 min** (86.6 %) | 444.4 s (72.7 %) |
| `STEER_STATUS` | {0: 93,131, 3: 114} | {0: 75,898, 3: 12} | {0: 61,147, 3: 15} |
| DTC-active duty | 0.00000 | 0.00000 | 0.00000 |
| sentinels 0x14A / 0x18F | 0 / 0 | 0 / 0 | 0 / 0 |
| `OUTPUT_DISABLED` duty | 0.00112 | 0.00013 | 0.00023 |
| EPS entry in `onroadEvents` | none of 2,075 | none of 1,674 | none of 1,786 |

All 29 rlogs read to a clean end, 0 truncations.

### Exposure, engaged

```
                    0-5    5-20   20-50  50-80    80+   km/h
  r75              18.6    70.4   160.7  117.9  216.1   = 583.7 s
  r76               8.3    67.7   220.0  303.5   57.6   = 657.2 s
  r73 (V88)         6.9   148.1   169.8   39.4   80.2   = 444.4 s
```
**695 s engaged ≥50 km/h and 274 s ≥80 km/h**, against 119.6 / 80.2 on route 73.

**The operator's own regimes, engaged (|steering rate|):**

| regime | r75 | r76 | pooled | r73 |
|---|---|---|---|---|
| **micro-ratcheting 1–13 °/s** | 242.2 s | 226.4 s | **469 s** (782 s on the 0x14A grid) | 165.2 s |
| **ratcheting 13–50 °/s** | 54.6 s | 53.4 s | 108 s | 94.2 s |
| macro >50 °/s | 18.7 s | 31.1 s | 50 s | 63.0 s |

🛑 **Creep is thin.** 18.6 s + 8.3 s engaged below 5 km/h. Manual frames are 80 % / 50 % parked, so
raw engaged/manual ratios remain worthless, as on every prior route.

---

## 2. IDENTITY — **V89 FLEW. PASS.** [EVIDENCE]

🛑 **First, a correction to the pre-registration's own arithmetic.** "≈0.60 ⇒ V89 flew" was the
wrong bar, and `extract_r75_r76.identity_verdict`'s built-in rule (`≥0.90 ⇒ V88`) reports the wrong
answer for the same reason. **Agreement between two rare booleans is dominated by the both-false
cell.** Route 73's two duties were both 0.273 ⇒ chance 0.6028. Route 75's are 0.060 and 0.102 ⇒
**chance 0.8503**. A raw 0.9539 on route 75 sounds like V88 and is not.

`v89_e1_identity.py` runs four parameter-free statistics with route 73 as the measured control:

| | **r73 = V88 control** | r75 | r76 |
|---|---|---|---|
| **S1 duty match** b6 vs (wire≥160) | 0.27332 / 0.27325, **\|diff\| 0.00007** | 0.05965 / 0.10226, **\|diff\| 0.0426** | 0.09259 / 0.14701, **\|diff\| 0.0544** |
| S2 agreement / chance / **kappa** | 0.9654 / 0.6028 / **0.913** | 0.9539 / 0.8503 / **0.692** | 0.9415 / 0.7876 / **0.724** |
| **S3 b5 = (cave cell ≠ 0)** | **0.9980** | **0.4055** | **0.4918** |
| S4 best agreement over ALL T | 0.9655 **at T=164** (predicted 160) | 0.9794 at T=290 | 0.9592 at T=224 |

**S3 is dispositive.** V88's cave read `gp-0x6b98`, the motor command, which is essentially never
exactly zero: b5 = **0.9980 on route 73 and 0.9980 on route 71 (V87)**, and the 427 wire is
non-zero on 98.9–99.5 % of frames on all three routes. On r75/r76 the cave's cell is **zero 59 % /
51 % of the time.** No threshold change, no rung edit, no scaling can make a never-zero cell read
zero half the drive. **⇒ `0xC4B38` took; the cave is on `gp-0x6ae2`; V89 is on the car.**
S1 corroborates: a same-cell rung forces equal duties, and they are off by 1.7× / 1.6×.

⊕ The residual association (kappa 0.69 / 0.72) is **expected, not a failure**:
`gp-0x6ae2 = K1/1024 · |model| · sign(rate)`, and `|model|` is driven by the same applied torque the
motor command tracks. The question was never "is there any association" but "is it the identity
relation", and S1 / S3 / S4 all say no.

⚠ **What is NOT established:** that `0xC40D2` (K1 = 204) also took. It has no independent readout —
the cave probes the friction *term*, not the *constant*. Both edits are in one image and one CRC
block and the cave edit is proven, so a partial flash is not a live hypothesis; but as a claim
about K1 specifically this is **BELIEF**.

---

## 3. H1 — **THE PROBE FIRED. PASS**, with a finding attached [EVIDENCE]

Cave rung duties (safe pairing only):

| rung | r75 engaged | r76 engaged | r73 (V88) engaged |
|---|---|---|---|
| **b5 = friction ≠ 0** | **0.5361** | **0.4949** | 0.9978 |
| **b6 = \|friction·1024\| ≥ 64** | **0.0373** | **0.0694** | 0.2935 |
| b7 = friction < 0 | 0.2803 | 0.2570 | 0.5177 |
| b4 gate / b3 fingerprint | 1.0000 / 1.0000 | 1.0000 / 1.0000 | 1.0000 / 1.0000 |

Both load-bearing rungs are **strictly between 0 and 1**, engaged and manual, moving and
stationary. Neither dead nor railed ⇒ **the flight is interpretable for the lever.**

### 3b. ★★★★★ …and the probe immediately explains the null: **the term is RATE-GATED**

The pre-registration expected "non-zero on a large majority of engaged frames". It is non-zero on
**~50 %**, and the structure of the other half is the finding. Duty of b5 by covariate, engaged:

| \|steering rate\| | <1 °/s | 1–3 | 3–8 | 8–20 | 20–60 | >60 |
|---|---|---|---|---|---|---|
| **b5 (friction ≠ 0), r75** | **0.189** | 0.335 | 0.874 | 0.974 | 0.981 | 0.996 |
| **b5, r76** | **0.177** | 0.333 | 0.894 | 0.984 | 0.997 | 0.999 |

It is not a speed gate (duty is identical engaged-and-moving) and not a load gate. It is
**`sign(motor rate)`**: `friction = |model| · sign(polarity · gp-0x6abc) · K1/1024`, and
`gp-0x6abc` is the resolver/motor electrical rate. **`sign(0) = 0` ⇒ the modelled Coulomb friction
term is identically ZERO whenever the motor rate quantises to zero**, which is most of the time at
low wheel rate. That is textbook Coulomb friction and it is a fifth independent confirmation of the
term's identity — but it is also the thing that kills the dose.

**Pooled across r75 + r76, in the operator's own regimes:**

| regime | engaged seconds | friction ≠ 0 | **\|friction\| ≥ 0.0625** |
|---|---|---|---|
| <1 °/s | 297.4 s | 0.182 | **0.000** |
| **micro-ratcheting 1–13 °/s** | **782.0 s** | 0.542 | **0.009** |
| ratcheting 13–50 °/s | 111.5 s | 0.987 | 0.235 |
| macro >50 °/s | 50.0 s | 0.998 | 0.684 |

⇒ 🛑🛑 **[EVIDENCE] In the micro-ratcheting regime the doubled friction term exceeds 0.0625 on
0.9 % of frames and is exactly zero on 46 %.** Since `friction = 0.199·|model|` at K1 = 204,
`|friction| < 0.0625` bounds `|model| < 0.314` — against a model whose bar arm is clamped at 15 and
whose ±10.0 friction clamp binds at `|model| ≥ 50`. **The V89 dose changes the model output by
`0.0996·|model| < 0.031` there.** Whether that is negligible depends on a LERP that lives in RAM
(`gp-0x64b8` / `gp-0x641c`) and cannot be read from the image, so "negligible" is **BELIEF** — but
**"the lever barely acts in the regime the operator named" is EVIDENCE**, and it is the single most
useful thing this flight produced.

---

## 4. H2 — **THE LEVER: FAIL.** No resolvable band-specific fall [EVIDENCE]

### 4a. 🛑 The confound, stated before any number: routes 75/76 are a QUIETER drive

| arm | median \|0x0E4 request\| | sustained \|tq\| | median \|rate\| | `e_1-4` | median \|angle\| |
|---|---|---|---|---|---|
| V88/r73 | **841.5** | 201.9 | 7.52 °/s | 265.1 | 9.5° |
| V89/r75 | 239.4 | 114.5 | 2.56 °/s | 159.2 | 4.2° |
| V89/r76 | 211.8 | 123.1 | 1.68 °/s | 120.5 | 4.2° |

**Every excitation covariate is 2–4× lower on the V89 arm**, and the matching validity check fails:
`e_1-4` (driver input) V89 pooled / V88 = **0.803 [0.629, 1.058]**, r76 alone **0.716 [0.574,
0.983]**. Route 73 carried far more cornering; 75/76 are mostly straight highway. **A bare band
ratio below 1.00 is exactly what a quieter drive produces with no firmware effect at all.**

### 4b. The ratios, controls first

Split-half nulls (each arm's own noise floor, same estimator): `e_6-9` [0.45, 1.02] to [0.50, 0.89]
per arm; on the 6–9 minus 32–38 **contrast**, [0.69, 1.40] on all three arms.

| | `e_1-4` (validity) | **`e_6-9`** | `e_18-22` | `e_26-31` | **`e_32-38`** (neg. control) | `e_40-49` |
|---|---|---|---|---|---|---|
| r75 / r73 | 0.920 [0.72, 1.36] | **0.758 [0.45, 1.27]** | 1.007 | — | 1.138 [0.74, 1.52] | — |
| r76 / r73 | 0.716 [0.58, 0.98] | **0.697 [0.25, 1.23]** | 0.895 | — | 0.876 [0.34, 1.28] | — |
| **pooled / r73** | 0.803 [0.63, 1.06] | **0.655 [0.38, 1.06]** | 0.922 | 0.956 | 0.959 [0.60, 1.32] | 0.870 |

**Wheel-order veto** (orders 1–6, circumference swept 2.073–2.088 m, 0.8 Hz guard, per-window):
169/325 · 291/428 · 239/487 windows survive. Vetoed `e_6-9`:
r75 0.763 [0.56, 1.51] · r76 0.622 [0.32, 1.67] · **pooled 0.709 [0.41, 1.54]**.

**Band contrast (`e_6-9` log-ratio minus a control band's, paired on the same resampled episodes):**

| | vs `e_32-38` | vs `e_1-4` | vs `e_18-22` |
|---|---|---|---|
| pooled, raw | 0.683 [0.514, **1.000**] | 0.816 [0.498, 1.325] | 0.711 [0.529, 1.178] |
| **pooled, ORDER-VETOED** | **0.914 [0.608, 1.853]** | 0.856 [0.506, 1.531] | 0.698 [0.510, 1.203] |

### ⇒ VERDICT: **H2 FAILS its pre-registration.**
- `e_6-9` pooled is **0.655 [0.380, 1.059]** raw and **0.709 [0.405, 1.538]** order-vetoed — the CI
  **includes 1.00** in every cut, so the required "CI excluding 1.00" is not met.
- The point estimate is a ~30–35 % fall and every control band also falls (0.87–0.96), consistent
  with the quieter drive rather than with a lever.
- The **order-vetoed contrast against the negative control is 0.914 [0.608, 1.853]** — dead centre
  of the null. **The fall is not band-specific once the mandated veto is applied.**
- Both arms' own split-half nulls on the contrast are [0.69, 1.40]; the measured contrast sits
  inside them.

**The ratchet line itself is unchanged** (order-vetoed): f0 **8.23 [8.03, 8.40] Hz** on V88 vs
**8.22 [8.09, 8.35]** (r75) and **8.40 [8.03, 8.60]** (r76). Prominence 3.94 / 2.94 / 3.34.
By rate regime, micro 1–13 °/s: V89 pooled / V88 = **0.878 [0.601, 1.631]** — null. The 13–50 °/s
and >50 °/s regimes have **no cell with matched exposure on both arms** ⇒ NOT SCOREABLE.

---

## 5. H3 — **THE OPERATOR'S CONSTRAINT: PASS.** Nothing fell [EVIDENCE]

Channel: the 427 packer's `wire = clamp((|gp-0x6b98|·5)>>3, 0, 0x3FF)` at ~50 Hz — V87 edit #6,
unchanged on V88 and V89, and exactly the channel V88's own H1 0.5–3 Hz row used.
🛑 **V88's `b7` SIGN bit is not available on V89** (the cave was repointed), so this is the
rectified magnitude. Engaged, zero-railed windows only; cell-stratified on speed × effort × rate.

| band | r75 / r73 | r76 / r73 | **pooled / r73** |
|---|---|---|---|
| **0.5–3 Hz** | 0.923 [0.784, 1.191] | 0.902 [0.778, 1.188] | **0.883 [0.810, 1.129]** |
| 3–6 Hz | 0.951 | 0.810 | 0.883 [0.748, 1.077] |
| 6–9 Hz | 0.920 | 0.796 | 0.864 [0.705, 1.057] |
| 9–12 Hz | 0.883 | 0.801 | 0.899 [0.721, 1.112] |
| 15–22 Hz | 1.063 | 0.836 | 0.970 [0.717, 1.142] |

Split-half null on 0.5–3 Hz: V88 [0.52, 1.05], r75 [0.82, 1.00], r76 [0.88, 1.00].

⇒ **The 0.5–3 Hz CI includes 1.00 in every cut. No fall is established.** The verified sign chain
predicted a small RISE and none is visible either; the honest reading is **NULL**, and specifically
**there is no evidence of the sign-chain inversion the pre-registration flagged as "the headline"**.
⚠ Every band moves together by ~0.88, and the upstream request is a third of route 73's — this is
an operating-point difference, not a command-shaping change.

---

## 6. H4 — the operator's own score

> *"fixed nothing, still only as good as V88."*

**His report is the verdict and the instrument does not contradict it.** No band moved by more than
its own noise floor; the ratchet line is at the same frequency and the same prominence; the
micro-regime ratio is 0.878 [0.601, 1.631]. **Nothing here is called fixed, improved, or changed.**
The one thing the instrument adds is the *reason*: §3b shows the doubled term is ~zero exactly where
he feels the symptom.

---

## 7. The operator's new hypothesis — the column-inertia reaction

> *"a large LKAS motor torque, acting against the steering-wheel/column INERTIA, shows up on the
> column torque sensor as an apparent DRIVER torque in the OPPOSITE direction — so the assist law
> fights its own overlay."*

### 7a. 🛑 THE POLARITY WAS ANCHORED FIRST — every phase below depends on it

A 180° convention error turns an inertia into a spring. **Anchor:** in the MANUAL arm with the
driver working the wheel (window-median `|tq| > 1200` ct and >2 °/s rms), the driver does **positive
work**, so `phase(T_bar, ω)` must be ≈0°.

| | 0.3–1 Hz | 1–2 Hz | 2–4 Hz | coherence² @0.3–1 |
|---|---|---|---|---|
| r73 | **−12.3°** | −3.0° | −4.9° | 0.964 |
| r75 | **−6.3°** | −3.1° | +1.1° | 0.982 |
| r76 | **−13.4°** | +2.8° | −2.8° | 0.952 |

**≈0° at coherence 0.95–0.98 ⇒ positive `tq` is torque driving the wheel in the +angle direction.
No flip.** ⊕ Second check: `corr(d(ang)/dt, rate_f)` = **+0.84 / +0.66 / +0.67** ⇒ the 0x14A angle
and the 0x18F rate share a polarity, so `rate_f` may stand in for the angle channel. [EVIDENCE]

### 7b. THE SIGN IS POSITIVE, NOT ANTI-PHASE — the hypothesis as stated is REFUTED [EVIDENCE]

Command channel: **openpilot's own 0x0E4 request**, chosen deliberately. `STATE.md` §3 records that
`gp-0x6b98` is the TOTAL motor command including base assist, and base assist is a function of
column torque, so a naive cmd↔column coherence is loop feedthrough. **0x0E4 is computed from the
camera and the planned path, not from the column torque** ⇒ exogenous to the EPS loop.

**Two controls, both run first.** (A) The manual arm: |0x0E4| is **identically 0** while `latActive`
is false (non-zero on 0.0–0.1 % of manual frames) — the ideal placebo. (B) A 5 s circular time shift
inside each engagement run — identical spectra, destroyed timing.

`r(0x0E4, column torque)`, engaged, median with episode-block CI:

| band | r75 ENGAGED | r75 manual | r75 shifted | r76 ENGAGED | r73 ENGAGED |
|---|---|---|---|---|---|
| 0.2–3 Hz | **+0.793 [0.739, 0.833]** | +0.035 | −0.027 | **+0.677** | **+0.553** |
| 6–9 Hz | **+0.393 [0.333, 0.443]** | −0.007 | +0.018 | **+0.463** | **+0.317** |
| 9–12 Hz | +0.284 | −0.008 | +0.038 | +0.386 | +0.140 |

Engaged phase at 0.2–3 Hz: −11.2° / −16.9° / −3.7°; coherence² 0.75–0.82.

**And it is NOT the driver co-steering** — splitting on `steeringPressed`:

| band | r73 hands-OFF | r73 hands-ON | r75 hands-OFF | r75 hands-ON | r76 hands-OFF | r76 hands-ON |
|---|---|---|---|---|---|---|
| 0.2–3 Hz | **+0.791** | +0.088 | **+0.827** | +0.200 | **+0.731** | +0.051 |
| 6–9 Hz | **+0.456** | +0.095 | **+0.407** | +0.114 | **+0.518** | +0.003 |

The relation lives **entirely in the hands-off arm.** ⇒ the column torque sensor is carrying a large
command-driven component with the driver's hands nowhere near it — **which is the operator's
mechanism** — but it is **IN PHASE with the command, not opposite.**

⇒ ★★★★ **[EVIDENCE] The EPS reads its own overlay as an apparent driver torque in the SAME
direction as the overlay.** That is not self-cancellation; **it is POSITIVE FEEDBACK.** More motor
torque → more apparent driver torque in the same direction → base assist adds more torque in that
direction. The operator's instinct — *the firmware does not know its own overlay is on the sensor* —
is supported; **his sign is not, and the true sign is the worse one.**

### 7c. THE IMPEDANCE SHAPE REFUTES A DOMINANT INERTIAL REACTION [EVIDENCE]

`v89_e6_bar_impedance.py`. Channel: `rate_f` = STEER_ANGLE_RATE from **0x18F — the same CAN frame
as the torque**, 0.1 °/s per LSB, so there is no cross-message ZOH skew and α needs only one
(spectral) differentiation. This replaces `v89_e4`'s T3, which differentiated the 0.1°-quantised
`ang` twice and was quantisation-limited above 6 Hz.

```
   INERTIA          T = J·α        phase(T,ω) = +90°    |Z| RISES linearly with f
   DAMPER           T = C·ω        phase       =   0°   |Z| FLAT
   SPRING           T = K·θ        phase       = −90°   |Z| FALLS as 1/f
   NEGATIVE DAMPING T = −C·ω       phase       = 180°   (a self-exciting loop)
```

ENGAGED, HANDS-OFF (`|Z|` in ct·s/rad; "×floor" = band rms over the quantisation floor):

| band | r73 \|Z\| / phase / coh² | r75 \|Z\| / phase / coh² | r76 \|Z\| / phase / coh² | ×floor |
|---|---|---|---|---|
| 2–4 | 2837 / **−152.2°** / 0.51 | 3378 / **−168.1°** / 0.52 | 3168 / **−173.8°** / 0.49 | 32–45 |
| 4–6 | 3226 / −134.8° / 0.65 | 3492 / −156.6° / 0.57 | 3311 / −159.2° / 0.59 | 28–43 |
| **6–9** | **5915 / −129.3° / 0.83** | **4735 / −142.7° / 0.74** | **4362 / −138.6° / 0.80** | 36–50 |
| 9–12 | 6590 / −145.5° / 0.79 | 5513 / −147.8° / 0.78 | 5447 / −141.3° / 0.84 | 40–43 |
| 12–16 | 5121 / +178.1° / 0.75 | 5196 / −170.1° / 0.75 | 4871 / −175.4° / 0.58 | 33–59 |
| 16–22 | 1610 / +134.5° / 0.57 | 1758 / +139.2° / 0.44 | 1694 / +149.7° / 0.43 | 44–72 |
| 26–31 | 1140 / +14.8° / 0.66 | 965 / +9.9° / 0.63 | 944 / +3.1° / 0.47 | 44–79 |

1. **The inertia prediction is +90°. The measurement is −130° to −175° across 2–16 Hz** — about
   220° away, on three routes, two builds, with coherence 0.5–0.84 and 28–59× the quantisation
   floor. ⇒ **the column torque is NOT dominated by an inertial reaction anywhere in 2–16 Hz.**
2. `cos(phase) < 0` across 2–16 Hz ⇒ **the real part of the column's driving-point impedance is
   NEGATIVE — anti-damping — and it is largest in |Z| at 9–12 Hz, straddling the ratchet.** At
   6–9 Hz, `Re(Z) ≈ −0.7·|Z| ≈ −3300 ct·s/rad`. That is what "lightly-damped mode" looks like from
   the outside and it is consistent with the record's Q 14–29.
3. **The MAGNITUDE, however, is the right order for a column.** A pure inertia at 7.5 Hz with
   J = 0.04 kg·m² gives `|Z| = ωJ = 1.96 N·m·s/rad ≈ 2350 ct·s/rad` at the 1200 ct/N·m anchor.
   Observed at 6–9 Hz: 4362–5915 ct·s/rad = **1.9–2.5× the pure-inertia prediction.** So an inertial
   component of the size the operator's hypothesis needs is **not excluded — it is simply not the
   dominant term, and its phase is not what the data show.** *(The counts→N·m anchor is openpilot's
   Honda `STEER_THRESHOLD = 1200` counts for "the driver is holding the wheel" ≈ 1 N·m. **BELIEF,
   ±3×.** opendbc carries the signal as "tbd" with no scale.)*

🛑 **THE CONTROL THAT DOES NOT EXIST.** The same impedance MANUAL + hands-off + moving would
separate "the EPS loop is anti-damped" from "the column is anti-damped". It has **6 / 1 / 0
qualifying windows** on the three routes — nobody drives with no hands and no LKAS.
**⇒ UNINTERPRETABLE for that contrast on these logs.** It would need a deliberate hands-off coast.

### 7d. MAGNITUDE-PROPORTIONAL **or** ACCELERATION-PROPORTIONAL? — **BOTH, and both band-specific**

`v89_e5_t2contrast.py`, 1,229 engaged windows over all three routes. `log e_6-9` and the 32–38 Hz
control response regressed on `log rms|cmd|`, `log rms|dcmd/dt|`, `log rms|d²cmd/dt²|` jointly, with
route fixed effects + `log v` + `log |rate|`, block-bootstrapped, **both responses fitted on the
same resample** so the difference's CI is honest.

🛑 **Collinearity control, printed first:** corr(log mag, log d1) = **+0.708**, corr(log mag,
log d2) = **+0.420**, corr(log d1, log d2) = **+0.852**. Magnitude and acceleration are only 0.42
correlated ⇒ **the discriminator works.** `d1`'s negative joint coefficient is a collinearity
artefact against `d2` (0.85) and carries no interpretation.

| regressor | **6–9 Hz** | 32–38 Hz control | **DIFFERENCE** | excludes 0? |
|---|---|---|---|---|
| `log \|cmd\|` | +0.403 [+0.270, +0.534] | +0.104 [+0.002, +0.198] | **+0.298 [+0.162, +0.431]** | **YES** |
| `log \|dcmd/dt\|` | −0.635 [−1.087, −0.188] | −0.446 [−0.724, −0.189] | −0.189 [−0.675, +0.278] | no |
| `log \|d²cmd/dt²\|` | +1.403 [+1.019, +1.806] | +0.899 [+0.697, +1.141] | **+0.503 [+0.140, +0.875]** | **YES** |

⇒ 🛑 **The discriminator does NOT come out one-sided, and the brief's expected answer is only half
reproduced.**
- **The kit's prior corpus result survives**: the ratchet band's sensitivity to command MAGNITUDE is
  **4× the control band's and the difference excludes 0** — a load-proportional / stick-slip
  mechanism has a real, band-specific signature.
- **But so does acceleration.** `|d²cmd/dt²|` also has a band-specific excess (+0.503), and its
  point estimate is larger. Read alone it looks decisive (+1.403); **most of that is the common
  cause the kit already recorded** — the negative control loads at +0.899, i.e. HF-rich command
  content raises *every* column band.
- ⚠ The excess at 6–9 Hz over the control is what a **resonance** does to broadband excitation: a
  lightly-damped 7.8 Hz mode is preferentially fed by HF-rich content. So the `d²` excess is
  **consistent with excitation of a resonance and does not require an inertial reaction.**
  Combined with §7c's phase, the resonance reading is the better-supported one. **[BELIEF]**

---

## 8. What this flight can and cannot say

**Can (EVIDENCE):**
1. V89 is on the car; the cave reads `gp-0x6ae2`; both routes are fault-free with 20.68 min engaged.
2. The modelled Coulomb friction term is **rate-gated by `sign(motor rate)`** and is zero or below
   0.0625 on **99.1 %** of the micro-ratcheting regime.
3. No band-specific fall in 6–9 Hz survives the wheel-order veto and the negative control.
4. No fall in the 0.5–3 Hz delivered command ⇒ no sign-chain inversion signal.
5. Hands-off, the column torque carries a large, command-driven, **in-phase** component that both
   controls put at zero — the EPS's own overlay is read as co-directional apparent driver torque.
6. The column's driving-point impedance has a **negative real part across 2–16 Hz**; the inertia
   signature (+90°, |Z| ∝ f) is absent. The operator's mechanism, as stated in *sign* and in *shape*,
   is refuted; the *magnitude* is the right order and is not excluded as a minor term.

**Cannot:**
1. **Separate the V89 dose from the drive.** The arms differ 2–4× in every excitation covariate and
   `e_1-4` matching fails. A build comparison needs a route matched to route 73's manoeuvre mix, or
   a within-route A/B.
2. Score the 13–50 °/s and >50 °/s regimes at all — no matched cell exists on both arms.
3. Say whether the anti-damping is the EPS loop or the column: the manual hands-off moving control
   has ≤6 windows on all three routes.
4. Confirm that `0xC40D2` = 204 is live — no readout exists for the constant itself.

---

## 9. What the next build should take from this

Not a recommendation to flash anything — a statement of what the data now constrain.

- 🛑 **Do not re-dose K1.** §3b is an arithmetic argument, not a null: the term it scales is zero on
  46 % of the micro regime and under 0.0625 on 99.1 % of it, because Coulomb friction is
  `sign(motor rate)`-gated. Doubling it again doubles ~nothing where the symptom is.
- ⊕ **`0xC4080` (K0, the pure-Coulomb constant term) is the cell that is NOT rate-gated in the same
  way** — but it carries the recorded NEVER-RAISE relay hazard and is untouched. This flight does
  not change that; it only explains why K1 could not substitute for it.
- ★ **The best-supported mechanism now on the table is §7b's positive feedback**: the overlay
  appearing on the torque sensor in the same direction, at coherence 0.75–0.82 in 0.2–3 Hz and
  0.24–0.38 in 6–9 Hz, hands-off, with the manual and time-shift controls at zero — feeding a base
  assist law that is a function of that sensor. A lever that subtracts a *model of the EPS's own
  contribution* from the sensed torque before the assist law reads it is the class this points at.
  **That is a structural claim about where to look, not a proposal — it needs a Ghidra trace of what
  the assist law actually subtracts today.**
- 🛑 **Any future build comparison needs matched manoeuvres.** This flight's biggest loss was not
  exposure (20.68 min, the largest in the corpus) but *mix*: 695 s of engaged highway against route
  73's 120 s, and a third of the command amplitude. The 6–9 Hz claim would have been resolvable at
  route 73's excitation.

---
---

# ADDENDUM (same session) — the rung conflict settled, and H2 re-scored against a placebo floor

Requested by the orchestrator after the interim. Scripts: `analysis-2020accord/v89_e7_rung_and_zero.py`,
`v89_e8_placebo_and_dose.py`, `v89_e9_placebo_fix.py` → `_cache_r75/v89_e{7,8,9}_*.json`.

## A1. The rung assignment — **b5 = (x ≠ 0), b6 = (|x| ≥ 64)**, settled three ways

`ArcAudit` reported the probe "tests |gp-0x6ae2| ≥ 64, not literal zero". That is **V86's** rung map
applied to a **V86B-derived** cave. The kit's own build scripts carry the swap, with a comment:

```
build_v86_tva.py:406   BIT_SIGN, BIT_NONZERO, BIT_MAG, BIT_GATE, BIT_FINGERPRINT = 0x80, 0x40, 0x20, 0x10, 0x08
build_v86b_tva.py:219  BIT_SIGN, BIT_MAG, BIT_NONZERO = 0x80, 0x40, 0x20   # b6 = MAG, b5 = NONZERO -- SWAPPED vs V86
```
V87, V88 and V89 all import V86B's constants.

**M2, the cave bytes out of the shipped V89 image**
(`_v89_V88BASE-FRICTION.C40D2.204-CAVE.6AE2.SIGN.MAG64_plain_image.bin`):
```
0xC4B34 +00  00 3a 24 37 1e 95 60 32 a3 05 42 3a 60 32 ae 05
        +16  48 3a a6 32 41 32 61 32 a3 05 44 3a a4 37 55 98
        +32  62 32 a9 05 41 3a c4 3a 48 3a 84 37 ed ea c6 36
        +48  07 00 07 31 44 37 ec ea 24 36 e8 ea 7f 00
   +04..05 = 1e95  ->  ld displacement -27362 = gp-0x6AE2      OK
   +18     = a6    ->  `sar 0x6`, magnitude rung trips at ±64  OK
```
⊕ `0xC4B46` `a8`→`a6` **is** the magnitude rung by construction: a non-zero test is a bare `cmp 0`
and takes no shift, so a `sar` immediate can only belong to the ≥ T rung.

**M3, the raw alphabet — parameter-free.** `|x| ≥ 64` implies `x ≠ 0`, so the magnitude rung must
nest strictly inside the non-zero rung:

| route | alphabet | b6 set & b5 CLEAR | b5 set & b6 CLEAR |
|---|---|---|---|
| 73 (V88) | 0x1F:121 · 0x3F:24,540 · 0x7F:9,850 · 0xBF:19,766 · 0xFF:6,885 | **0** | 44,306 |
| 75 | 0x1F:55,433 · 0x3F:15,702 · 0x7F:2,511 · 0xBF:16,551 · 0xFF:3,048 | **0** | 32,253 |
| 76 | 0x1F:38,576 · 0x3F:15,297 · 0x7F:2,577 · 0xBF:15,027 · 0xFF:4,435 | **0** | 30,324 |

**Zero counter-examples in 230,319 frames ⇒ b6 ⊂ b5.** This is the same statistic that makes
`V86_ONLY = {0x48,0x58,0xC8,0xD8}` a build discriminator: those are exactly the bytes this test
forbids, and they occur 0 times.

## A2. `gp-0x6ae2` is EXACTLY ZERO on 46.4 % / 50.5 % of engaged frames, and the zeros are FRESH

| | r73 = V88 (cave on `gp-0x6b98`) | r75 | r76 |
|---|---|---|---|
| **exactly zero** | **0.0022** | **0.4639** | **0.5051** |
| non-zero but < 64 | 0.7043 | 0.4988 | 0.4254 |
| \|value\| ≥ 64 | 0.2935 | 0.0373 | 0.0694 |

⊕ Corroborates `ObserverMatch`'s ~41-count sizing independently: |value| ≥ 64 on only 3.7–6.9 %.

**FRESH, not a stale hold** — three consistency arguments and one logical one:
- **D1 run-length.** Zero runs: median 20/30 ms, p99 660/867 ms, **0.41 % / 0.64 % exceed 1 s** — the
  same dwell as the non-zero runs. It dithers; it does not freeze.
- **D2** `P(exactly zero)` vs `|rate_f|`, both routes independently:
  `<0.05 °/s 0.865/0.885 · 0.35–0.75 0.729/0.751 · 1.5–3 0.284/0.237 · 6–12 0.039/0.031 · >25 0.011/0.002`
  — **80× monotone, on a mechanical variable the observer's gate does not read.**
- **D3, logic.** A gate failure holds the *last successful* value, ~41 counts, i.e. **non-zero**.
  A stale hold can prolong a zero; it cannot generate one.
- 🛑 **What none of this does:** V89's cave has no `gp-0x6c00` rung and `gp-0x6ae0`/`gp-0x6ae2` are
  success-path-only, so nothing here observes the gate. A direct answer needs the rung.
- 🛑 **One structural question stays open:** the zero could be a three-valued `sign()` returning 0 at
  `gp-0x6abc == 0`, **or** `|model|` itself going to zero at low rate. Both fit these data. That is a
  Ghidra read of `FUN_0003b8f6`, not another drive, and it decides whether K1 is structurally absent
  at low rate or merely one small term among several.
- ⊕ The `gp-0x6752 == 0` third state would write a fresh zero **uncorrelated with wheel rate** — the
  opposite of D2 — so the data exclude it as the source even before the writer census.

## A3. H2 re-scored against a PLACEBO-PAIR NULL — **still FAIL, and now for a sharper reason**

`LeakDose`: block bootstraps understate cross-build uncertainty ~2.8× here (0.37 vs sd 1.03 over 213
constant-α pairs). Routes 75 and 76 are **two different drives on the same build**, so this flight
can build its own placebo.

⚠ **My first placebo was too tight and its own output said so.** Random segment partitions gave
sd(log) 0.164 — but the one genuine cross-drive same-build pair, whole r75 vs whole r76, landed at
**contrast 0.807 (log −0.214) = 1.3σ of that floor.** A random partition puts segments from both
drives in both arms and averages away the drive-level heterogeneity being estimated. Rebuilt from
**contiguous segment chunks that never straddle a route**: sd(log) 0.228 (2 chunks) / 0.164 (3) /
0.257 (4) — unstable at 4–8 chunks, so the honest calibrator is the real pair.

**Measured, all engaged: `e_6-9` 0.655 [0.360, 1.116], contrast 0.683 [0.523, 1.019] (log −0.381).**

| floor | sd(log) | σ | resolvable? |
|---|---|---|---|
| random segment partition (too tight) | 0.164 | 2.33 | yes |
| contiguous 3-chunk, same build | 0.164 | 2.33 | yes |
| contiguous 2-chunk, same build | 0.228 | 1.67 | marginal |
| **r75 vs r76 — the one real same-build pair** | **0.214** | **1.78** | **no** |
| **`LeakDose` corpus placebo, 213 pairs** | **1.025** | **0.37** | **no** |

**A same-build placebo pair already reproduces 56 % of the measured log-contrast.**

### ★ And the decisive cut: on the only INTRINSICALLY ORDER-CLEAN stratum, it is FLAT

`LeakDose` defect #2 — orders 1–6 never reach 32–38 Hz at parking speed while orders 3–4 hit 6–9 Hz
constantly, so band and control are screened asymmetrically. The fix these routes allow is exposure.
⚠ My first cut (v ≥ 18.8 m/s) was **not** clean and the veto said so (3/66, 3/175, **26/102**
flagged): with the 0.8 Hz guard and the 2.073–2.088 m sweep, order 1 must clear 9.8 Hz, and the
stratum must be defined by its **slowest** window. The correct cut is **v ≥ 22.2 m/s (80 km/h)**,
order 1 = 10.68 Hz, 1.68 Hz of margin — **checked: 0/59, 0/162, 0/43 windows vetoed.**

| | contrast | placebo floor | verdict |
|---|---|---|---|
| **v ≥ 22.2 m/s, no veto needed on EITHER band** | **0.947 [0.827, 0.979]** | [0.900, 1.111], sd 0.059 | **0.92σ — FLAT** |

🛑 **This is the placebo correction earning its keep**: the block-bootstrap CI [0.827, 0.979]
*excludes* 1.00, and the effect is nonetheless **inside its own same-build placebo band.** Quoting the
CI alone would have produced a false 5 % "fix".
⚠ Thin: 1 common cell, 8 vs 3 episodes (route 73 has only 9 blocks above 80 km/h).

⇒ **The all-engaged 0.683 is carried by the low-speed windows, which is exactly where the screening
is asymmetric. Where the asymmetry is structurally absent, V89 and V88 are indistinguishable.**

## A4. `LeakDose`'s magnitude-vs-rate regression — **THIRD INSTRUMENT, THIRD REPRODUCTION**

1,240 engaged windows across all three routes; command range p5–p95 = 97 → 3,407 ct (**35×**, far
wider than any prior route pair). Route fixed effects; block bootstrap.

| term | 6–9 Hz | 32–38 Hz control | **BAND CONTRAST** | excludes 0? |
|---|---|---|---|---|
| `log \|cmd\|` | +0.274 [+0.129, +0.415] | −0.071 [−0.173, +0.023] | **+0.345 [+0.209, +0.482]** | **YES** |
| `log \|rate\|` | +0.326 [+0.196, +0.467] | +0.258 [+0.178, +0.347] | +0.069 [−0.030, +0.165] | no |

With `log v` added: `log|cmd|` contrast **+0.219 [+0.088, +0.357]** still excludes 0; `log|rate|`
+0.040 [−0.061, +0.140] null; `log v` contrast **−0.361 [−0.454, −0.265]** (the ratchet band falls
with speed relative to the control — D5's decay, reproduced).

🛑 **CONTROL — block permutation** (regressors shuffled between ~10.2 s blocks, marginals and
within-block structure preserved, 600 draws):

| term | observed | permutation null | p |
|---|---|---|---|
| `log \|cmd\|` | **+0.345** | median +0.000, 95 % [−0.140, +0.142] | **< 0.002** |
| `log \|rate\|` | +0.069 | median +0.001, 95 % [−0.111, +0.113] | 0.205 |

⇒ ★★★★★ **[EVIDENCE] The ratchet band's excess sensitivity is to command MAGNITUDE, not to wheel
RATE — reproduced on a third instrument, on the widest command range in the corpus, and it survives
its own permutation control while the rate term does not.** Together with the 30-route corpus and
`LeakDose`'s two-route fit, **magnitude-not-rate is now about as established as anything in this kit,
and it is the constraint every remaining hypothesis has to satisfy.**

⚠ Restricted to the order-clean highway stratum alone (343 windows) the pattern **inverts**:
`log|cmd|` contrast +0.150 [−0.030, +0.320] (no longer excludes 0) and `log|rate|` +0.185 [+0.074,
+0.304] (does). That is either power or a real regime difference and **I am not reading it either
way** — it is recorded because it is the one cut that disagrees.

⊕ **Consistency with §7d:** the `|d²cmd/dt²|` band-specific excess (+0.503) and this `|cmd|` excess
(+0.345) are not in conflict. `|cmd|` survives permutation and reproduces on three instruments;
`|d²|` is what a lightly-damped 7.8 Hz mode does when fed HF-rich broadband content. **The
load-proportional term is the established one.**

## A5. H3, restated under the wider floor

The 0.5–3 Hz command ratio was **0.883 [0.810, 1.129]** pooled — a CI that already includes 1.00.
A wider cross-build floor can only widen it further, so **H3's PASS is unaffected and is if anything
strengthened**: there is no evidence of a fall in the delivered LKAS command, hence no sign-chain
inversion signal. Nothing in this addendum changes §5.

---
---

# ADDENDUM 2 — §7b SPLITS: self-interference survives at 0.2–3 Hz and is WITHDRAWN at 6–9 Hz

Requested by the orchestrator: separate **(a) self-interference** from **(b) the car is simply
turning**. Scripts: `analysis-2020accord/v89_f1_selfinterference.py`, `v89_f2_requests.py` →
`_cache_r75/v89_f1_selfinterference.{log,json}`, `v89_f2_requests.json`.

## B1. The discriminator — partial out what the car is actually doing

Per hands-off engaged window, `cmd` and `tq` are each residualised on **steering angle, wheel rate,
IMU lateral acceleration and yaw rate**, all band-passed, within the window, before correlating.

| band | | V88/r73 | V89/r75 | V89/r76 | 5 s-shifted control |
|---|---|---|---|---|---|
| **0.2–3 Hz** | raw | 0.753 | 0.829 | 0.730 | −0.03 … −0.07 |
| | **partial** | **0.593 [0.457, 0.707]** | **0.396 [0.345, 0.489]** | **0.400 [0.352, 0.450]** | **0.004 / −0.049 / −0.087** |
| 3–6 Hz | partial | −0.048 | −0.154 | −0.112 | ~0 |
| **6–9 Hz** | raw | 0.458 | 0.425 | 0.516 | −0.007 / +0.014 / −0.003 |
| | **partial** | **0.001 [−0.052, 0.053]** | **0.039 [−0.004, 0.081]** | **0.070 [0.026, 0.127]** | ~0 |
| 9–12 Hz | partial | −0.033 | −0.009 | 0.137 | ~0 |

⇒ **The 0.2–3 Hz relation SURVIVES partialling at +0.40 … +0.59 with both controls at 0.00.**
⇒ 🛑 **The 6–9 Hz relation COLLAPSES to zero.**

**Leakage excluded as the explanation for the 6–9 Hz raw value.** 0x0E4 band rms is 89–92 % of total
at 0.2–1 Hz but **6.3 / 7.8 / 10.0 % at 6–9 Hz** — small but real. Re-running with everything below
5 Hz **high-passed out first**: 6–9 Hz raw r 0.462 / 0.433 / 0.512 (unchanged) and partial 0.008 /
0.051 / 0.077 (still zero). **So the 6–9 Hz correlation is genuine command content, not leakage —
and it is entirely accounted for by the column's own motion.**

## B2. Straight vs cornering — **(b) is REFUTED for the 0.2–3 Hz component**

⚠ The first attempt stratified on raw `|imu_lat|`, which carries a mounting bias of +0.32…+0.53 m/s²
and gave a useless 1.5× spread. `cs_yaw` is **identically zero** in these caches. Redone on two
de-biased proxies: `|imu_lat − route median|` and the bicycle-model `a_lat = v²·|δ|·π/180/(SR·WB)`
(corr between them +0.297, so they are close to independent tests).

| stratum | 0.2–3 Hz **partial** | 6–9 Hz **partial** |
|---|---|---|
| IMU: straight (<p25) | **0.444 [0.380, 0.516]** | 0.051 [−0.012, 0.130] |
| IMU: cornering (>p75) | 0.375 [0.324, 0.436] | 0.085 [0.052, 0.144] |
| IMU: hard (>p90) | 0.325 [0.247, 0.406] | 0.120 [0.017, 0.180] |
| bicycle: straight (<p25) | **0.512 [0.443, 0.572]** | 0.030 [−0.036, 0.070] |
| bicycle: cornering (>p75) | 0.399 [0.345, 0.520] | 0.013 [−0.035, 0.076] |
| bicycle: hard (>p90) | 0.553 [0.398, 0.656] | 0.006 [−0.052, 0.139] |

**The 0.2–3 Hz partial is as large on the straight as in a corner — larger, on both proxies.**
(b) predicts it collapses when the tyres are not working. It does not. **[EVIDENCE]**
⚠ Scope: these are mostly straight highway drives — hands-off engaged |angle| median **4.1°**, p90
8.6°, bicycle `a_lat` p90 1.34 m/s². **The cornering arm is MILD cornering, not hard cornering.**

## B3. 🛑 What the 6–9 Hz collapse does and does not license

**It does NOT establish (b).** The orchestrator's own caveat is the binding one: self-interference is
partly **mediated by column motion** — the motor back-drives the rack, the column moves, the bar
twists — so partialling on angle and rate removes (a) as well as (b). **At 6–9 Hz the test is
uninformative between the two hypotheses.**

**What it does establish, and it is enough to change the headline:** at the ratchet frequency there
is **no command-locked bar torque beyond what the column's own kinematics already account for.**

⇒ **§7b is SPLIT:**
- ✅ **0.2–3 Hz — the self-interference reading STANDS.** The EPS's overlay appears on the torque
  sensor co-directionally, beyond anything the vehicle's motion explains, and it does not need the
  tyres. This is the LKAS command band.
- 🛑 **6–9 Hz — WITHDRAWN.** *"The EPS reads its own overlay as apparent driver torque at the ratchet
  frequency"* is **not supported**. Anything built on positive feedback **at 7.8 Hz** must not cite it.

⊕ **§7c is untouched and is now the stronger of the two.** The impedance result — phase(T_bar, ω)
−130° to −175° across 2–16 Hz, `Re(Z) < 0` — is a **torque-versus-velocity** relation, i.e. it lives
*inside* the kinematic channel that the partialling removes. Partialling cannot subtract it. **The
6–9 Hz mechanism these routes support is anti-damping in the column's own dynamics, not a
command-locked overlay.**

## B4. Firmware context (from `TorquePath`), which the document lacked

The LKAS command **is** a known input to the disturbance observer (`FUN_0003b8f6` reads
`gp-0x6b98`; `FUN_00038148` reconstructs it from six lanes including the overlay at unity weight) —
but **no base-assist producer reads any LKAS-descended cell.** So the loop §7b measures is:

```
LKAS cmd -> aggregator -> motor -> rack -> back-drives the pinion -> TORSION BAR TWISTS
   -> 3-coil sensor -> boost curve FUN_00034a72 -> gp-0x6bbe -> SAME aggregator   [CLOSED]
```

⇒ §9's recommendation — *subtract a model of the EPS's own contribution from the sensed torque
before the assist law reads it* — **is a real gap, not a restatement of what exists.** The observer
subtracts the overlay from the **residual**; nothing subtracts it from the **sensed torque feeding
boost**. Correcting the kit's standing feasibility note: the path exists and is closed.
⚠ Scope after B3: the case for intervening on it rests on the **0.2–3 Hz** measurement, not on 7.8 Hz.

## B5. Ring-down ζ vs command magnitude — **CANNOT BE RUN. Yield reported, then stopped.**

Per the standing instruction to report edge yield before fitting. `latActive` falling edges, screened
on ≥5 s engaged before / ≥5 s hands-off after / clean disengage (no brake, no grab):

| route | falling edges | pass | at v ≥ 18.8 m/s |
|---|---|---|---|
| 73 (V88) | 5 | **0** | 0 |
| 75 | 7 | **2** (t = 265.9 s, 278.0 s) | 0 |
| 76 | 3 | **0** | 0 |

**Both survivors are at v = 0.29 m/s — a car park, the worst case for the estimator** (wheel orders
4–7 sit inside 6–9 Hz there, and a non-decaying order biases ζ̂ by 3.5–5.7×). **Zero edges exist at
order-clean speed on any of the three routes.** Recorded power needs 10–28 edges for ±50 % on ζ, and
the ζ-versus-command-magnitude test needs that split across **two** command bins.
⇒ **The test is not supportable on this corpus. Not fitted.**
⊕ Every one of route 73's 5 edges has the brake active at the edge, which is why this screen returns
0 where the V88 session's looser screen returned 1–2. The per-edge table is in
`_cache_r75/v89_f2_requests.json` so a different screen can be applied without re-deriving it.

## B6. Instrument checks done for `LeakDose`, with one route-specific finding

- **Cache consistency:** whole-route rows == sum of segments exactly on all three (61,161 / 93,244 /
  75,911). Per-segment `(n−1)/span` is 99.98–100.04 Hz on r75; r73 and r76 each have one segment at
  97.1 / 97.2 Hz (dropouts inside the span). Nothing is mid-write.
- **The stagger claim reproduces**: `t == raw14_t[1:]` on all three.
- 🛑 **But it is NOT uniform across routes.** `median(raw18_t − raw14_t)` at equal index is
  **+0.000 ms on r73 and r75** and **+9.986 ms on r76**, and `sstat == raw18_st[:len(sstat)]` holds
  on r73/r75 but **fails on r76**. **Route 76's rows pair a 0x18F frame with a 0x14A frame one
  100 Hz period apart, where r73/r75 pair them at zero offset.** Any cross-message phase work on r76
  carries an extra 10 ms that r73 and r75 do not.
- **Consequence for this document, checked rather than assumed:** §7c / `v89_e6` uses `tq` and
  `rate_f`, **both decoded from the same 0x18F frame into the same row**, so their relative timing is
  exact and the impedance phase table is immune on all three routes. §7b / B1 pair `e4tq` (0x0E4,
  held) with `tq` (0x18F), so a one-frame skew applies: 10 ms attenuates a correlation by
  `cos(2πf·0.01)` = 0.998 at 1 Hz and 0.88 at 7.5 Hz. **The reported r values are slightly
  UNDER-stated, never inflated.**

---

## B5-CORRECTION (same session) — the edge count in B5 was **2; it is 0**

🛑 **My screen was incomplete and `LeakDose` caught it.** B5 tested `~cs_press` over the 5 s after
each falling edge — *the driver's hands off the rim* — but **never tested that `latActive` STAYED
FALSE.** A re-engagement inside the window re-excites the mode and voids the ring-down. Both of my
"passes" re-engage almost immediately:

| edge | manual duration after the edge | verdict |
|---|---|---|
| r75 t = 265.9 s | **4.6 s** (needs ≥5 s) | FAILS |
| r75 t = 278.0 s | **1.9 s** | FAILS |

**Corrected yield: 5 / 7 / 3 falling edges on routes 73 / 75 / 76, and ZERO usable on all three.**
Two independent implementations now agree to 0.1 s on every edge's pre- and post-durations.
⊕ `LeakDose` puts the corpus-wide poolable yield at **1 usable edge in 99**.
⇒ **B5's conclusion is unchanged and strengthened: the ζ-versus-command-magnitude test is not
supportable on this corpus, and it is not a fixable-by-more-driving problem.**

★ **The actionable pattern, which the corrected table makes clearer: 8 of the 10 edges on routes
75/76 end in BRAKING**, and the two longest engagements in the corpus (359.6 s before r75's
t = 756.7 s edge, 596.2 s before r76's t = 704.5 s) were lost **purely on disengage cause.** If a
ring-down protocol is ever driven deliberately, the instruction that matters most is
**cancel button · foot off the brake · hands off · hold 5 s either side.**
⊕ r76's t = 725.6 s edge additionally crosses a segment boundary.

---

## B6-CORRECTION — **the r76 "+9.986 ms stagger" is an INDEX artefact, not a timing skew**

🛑 **I reported this wrongly to two agents and it is now withdrawn.** B6 said route 76's rows pair a
0x18F frame with a 0x14A frame *"one 100 Hz period apart"*, implying a phase penalty on r76 that
r73/r75 do not carry. **There is no such penalty, on any of the three routes.**

**What the +9.986 ms actually was.** It is `median(raw18_t[i] − raw14_t[i])` at **equal index**, and
route 76 has **2 fewer 0x18F frames than 0x14A frames** (75,910 vs 75,912; r73 and r75 have exactly
equal counts). Equal-index differencing therefore compares different instants. It is bookkeeping,
not timing.

**The measurement that matters, and it is index-free.** `last18` is held-last, so the quantity is the
*age of the 0x18F payload carried by each row*:

| | 0x18F payload age (median / p10 / p90) | 0x14A payload age — CONTROL |
|---|---|---|
| r73 | **0.000 / 0.000 / 0.000 ms** | 0.000 ms |
| r75 | **0.000 / 0.000 / 0.000 ms** | 0.000 ms |
| r76 | **0.000 / 0.000 / 0.000 ms** | 0.000 ms |

Because **0x18F and 0x14A are logged at the SAME instant on 95.7 % / 95.6 % / 95.8 % of frames** —
they arrive in one CAN burst and share a `logMonoTime`. ⇒ **`tq` and `rate_f` are not one frame late
relative to the row grid on any route.** The `−8° at 3 Hz … −68° at 23 Hz` penalty attributed to this
pairing **does not exist in these caches.** (Max age is 10.4 / 10.7 / 55.0 ms at dropouts.)

⊕ **The first version of this measurement was wrong and its own control caught it.** Subtracting
`raw14_t[0]` re-zeroed an array that was already on `t`'s origin (`raw14_t[0] = −0.0105 s`, the frame
before the first row) and injected a spurious +9.1 ms — which the 0x14A control then reported as
+9.1 ms where it must be 0. **Run the control before the measurement.**

### The `sstat` index test is near-worthless and neither agent should cite it
`sstat` is the constant 0 on **99.977 % / 99.878 % / 99.984 %** of rows — 14 / 114 / 12 non-zero
samples. **Every index shift from −3 to +3 matches at ≥ 0.99994.** The test turns on a dozen samples.
⊕ And for the record it *is* repairable on r76 by a single shift — `sstat[1:] == raw18_st[:N−1]`
exactly, i.e. shift **−1**, where r73/r75 take shift 0. The two candidates that were tried (`[:N]`
and `[1:]`) are shifts 0 and +1; the answer is the other direction. **But given the 99.98 % constancy
this should not be leaned on either way** — the frame-count difference above is the real explanation
and the payload-age table is the real measurement.

### Net effect on this document
- **§7c / `v89_e6` (the impedance):** immunity argument **upgraded from structural to measured** —
  `tq` and `rate_f` share a frame *and* the row's timestamp. Phase table unaffected on all routes.
- **§7b / B1 (the correlations):** the only cross-message pairing is `e4tq` (0x0E4). Its measured hold
  age is **6.4 ms median, 7.5 ms p90** (against `sc_t`, the closest timestamp array the cache stores
  for that message), not the 10 ms I quoted. That attenuates a correlation by `cos(2πf·0.0064)` =
  **0.998 at 1 Hz and 0.95 at 7.5 Hz.** The direction of the caveat stands — **the reported r values
  are floors** — but the size was pessimistic by ~1.6×.

---

## B6-CORRECTION-2 — **the 10 ms skew IS real, on all three routes.** B6-CORRECTION over-corrected

🛑 **`LeakDose` is right and my previous correction is withdrawn in its conclusion.** The r76
`+9.986 ms` equal-index number *was* bookkeeping — that part of B6-CORRECTION stands. But
*"therefore there is no cross-message timing skew on any route"* **does not follow and is wrong.**

### The structural proof — decisive, and independent of any weak statistic
`decode_v84_probe_r6d.extract()` appends a ROW on a 0x14A frame, but only `if last18 is not None`.
If 0x18F were processed **before** the co-logged 0x14A, `last18` would already be set on the very
first 0x14A and rows would start at `raw14_t[0]`, giving `len(t) == len(raw14_t)`. Observed on all
three routes:

```
len(t) = len(raw14_t) - 1     and     t == raw14_t[1:]     and     raw18_t[0] == raw14_t[0] exactly
```
⇒ the first 0x14A found `last18` **empty** even though a 0x18F shares its instant
⇒ **0x14A is processed BEFORE the co-logged 0x18F**
⇒ **row `i` carries 0x18F frame `i`, whose time is `raw14_t[i]` = `t[i]` − one 100 Hz period.**

**The payload is ~10 ms older than its label, on every route.** `LeakDose`'s penalty — **−8° at 3 Hz
rising to −68° at 23 Hz** — stands.

### Why my "payload age = 0.000 ms" metric missed it
It measured the age of the **most recent** 0x18F frame at the row's timestamp. Because 0x18F and
0x14A are co-logged (95.7 %), the most recent frame at `raw14_t[i+1]` is frame `i+1`, age 0 — **but
the row stores frame `i`.** The metric assumed the row carries the newest frame, which is exactly the
question. Its 0x14A control could not catch it either: `probe` genuinely does come from the
co-timestamped frame.

### The empirical test agrees — `sca` (= `(0x18F byte4 >> 3) & 1`, stored via `last18`) vs `raw18_b4`
Mismatch rate on transition neighbourhoods only, where the shift is identifiable:

| route | −3 | −2 | −1 | 0 | +1 | +2 | best |
|---|---|---|---|---|---|---|---|
| r73 | .600 | .400 | .200 | **.000** | .200 | .400 | **0** |
| r75 | .600 | .400 | .200 | **.000** | .200 | .400 | **0** |
| r76 | .400 | .200 | **.000** | .200 | .400 | .400 | **−1** |

⚠ **Weak on its own** — 10 / 14 / 6 transitions, 50 / 70 / 30 neighbourhood samples. It is worth
quoting only because it agrees with the structural proof, which is not weak.
⊕ **r76's two bookkeeping differences cancel into the same physical result:** the −1 index shift and
the +9.986 ms equal-index offset (from its 2 missing 0x18F frames) combine to put the payload at
`t[i] − 10 ms`, identical to r73/r75.

### Net effect on this document — one statement moves, no result does
- **§7c / `v89_e6` (the impedance): UNAFFECTED, and both agents agree.** `tq` and `rate_f` come from
  the **same `last18` tuple**, i.e. the same 0x18F frame, so their *relative* timing is exact
  whatever the row label is. The phase table stands on all three routes.
- **§7b / B1 (the correlations):** the relevant quantity is the **relative** skew between `tq`
  (~10 ms old) and `e4tq` (~6.4 ms old against `sc_t`, a proxy) — roughly **3.6 ms**, not the 10 ms
  of the raw label offset and not the 6.4 ms I last quoted. **I am no longer quoting a single
  factor:** the relative skew is bounded by one period, so attenuation at 7.5 Hz lies in
  **0.88–1.00**. The robust statement is unchanged and is the only one that should be cited:
  **the reported r values are FLOORS.**
- **Band energies, duties, ratios, the identity result, H1/H2/H3:** insensitive to a uniform label
  offset. Unaffected.
- **The b5/b6 conditioning tables:** covariates are interpolated onto the raw14 timebase, so `rate_f`
  carries the 10 ms. Immaterial against broad bins spanning an 80× dynamic range.

### Method note
Two of my three instrument claims this round were wrong in opposite directions — first an origin bug
that the control caught, then a metric whose assumption *was* the hypothesis. **A control only tests
what it is pointed at.** The 0x14A control could not fail here no matter what, because `probe` is
co-timestamped by construction; a control that cannot fail is not a control.

---

## B6-FINAL — the skew is EXACTLY computable per row. **Do not exclude r76; do not use an index shift.**

The processing-order rule proved in B6-CORRECTION-2 makes the whole question exact, with no statistic
and no per-route constant. Row `i` is created by 0x14A frame `i+1` and carries the last 0x18F frame
processed **strictly before** it, so:

```python
last18_index = np.searchsorted(raw18_t, raw14_t[1:], side="left") - 1
payload_time = raw18_t[last18_index]          # the TRUE timestamp of tq / rate_f in each row
payload_age  = t - payload_time               # exact, per row, no fitting
```

### The result: the age is ~9.93 ms and FLAT on all three routes

| median payload age, by decile of the route (ms) | | |
|---|---|---|
| **r73** | 9.94 9.93 9.93 9.95 9.94 9.94 9.94 9.95 9.94 9.93 | flat |
| **r75** | 9.93 9.94 9.93 9.94 9.94 9.94 9.93 9.93 9.95 9.93 | flat |
| **r76** | 9.94 9.93 9.94 9.92 9.92 9.93 9.93 9.94 9.93 9.94 | flat |

| tail | r73 | r75 | **r76** |
|---|---|---|---|
| rows > 12 ms | 4.88 % | 4.64 % | **4.61 %** |
| rows > 15 ms | 2.30 % | 2.04 % | **1.99 %** |
| rows > 20 ms | 0.86 % | 0.68 % | **0.79 %** |

**r76 is indistinguishable from the other two — marginally the cleanest on two of three tails, and
its decile medians are as flat as theirs.** There is no route-wide drift on any route.

### 🛑 Why the index shift looked like drift, and why it is the wrong variable
The exact shift census `last18_index − row_index` is a **mixture on every route**:

```
r73:  0 x54,771 · -1 x6,367 · -2 x10 · -3 x6 · -4 x4 · -5 x1 · -6 x1 · -7 x1
r75:  0 x83,725 · -1 x9,517 · -2 x2
r76: -1 x68,178 · -2 x7,619 ·  0 x97 · -3 x10 · -4 x5 · -5 x2
```
**All three routes have non-constant index shifts.** A dropped 0x18F frame advances the index
relation without changing the physical fact that each row carries the *previous* co-logged 0x18F —
so the index shift is bookkeeping (for the third time this session) and the **age is the physics.**

⇒ **`LeakDose`'s "r76 accumulates drift, exclude it from cross-message work" is NOT supported.**
Their per-transition shifts (−1 … −4) are real *as index statistics*, and their `−4 at 760.7 s` is
the final transition at the very end of the route — but r73 has shifts out to −7 and the same tail
fractions. Excluding r76 would cost **10.95 min of engaged data, the highest engaged fraction in the
corpus (86.6 %)**, for a defect the other two routes have equally.
⇒ **And my own frame-count guard (`len(raw18_t) − len(raw14_t)`) is superseded, not just imprecise.**
`LeakDose` was right that it cannot predict the shift; the correct response is that **no shift
constant is needed at all.**

### The recommendation that replaces both of ours
**Use `payload_time` above as the time base for any 0x18F-derived channel** (`tq`, `rate_f`, `sca`,
`sstat`, `slow3`) instead of the row label `t`. It is exact, per-row, monotone non-decreasing on all
three routes (verified), needs no re-extraction, no per-route constant, and no exclusion. This is
`LeakDose`'s "resample from each channel's own timestamp array" advice made concrete.
⊕ Dropout regions (age > 20 ms) exist on all three routes at 0.7–0.9 % of rows and are visible in
`payload_age` directly, so they can be screened rather than assumed away.

### Net effect on this document: still none
`v89_e6` remains immune (`tq` and `rate_f` share the `last18` tuple). The §1 correlations carry the
relative skew already discussed, unchanged and route-independent. **No result moves, and r76 stays
in.**

---

## B6-FINAL-CORRECTION — it is a MIXTURE, and my `payload_time` fix is not "exact" either

`LeakDose` settled the mechanism at source, with the test neither of us ran: read the order inside
`evt.can` directly. **0x14A is processed first on 91.28 % of co-logged events** (r73 91.61 %, r75
90.52 %, r76 91.71 %; 51,691 events). The structural proof in B6-CORRECTION-2 is confirmed in
mechanism and conclusion — but it is a **mixture, not a pure delay**:

```
H(f) = 0.9128 · exp(-j·2πf·0.010) + 0.0872
```

Verified independently here; reproduces their numbers exactly:

| f (Hz) | \|H\| | phase | pure-delay phase | flat-10 ms over-correction |
|---|---|---|---|---|
| 3.00 | 0.9986 | −9.86° | −10.80° | **+0.94°** |
| **7.79** | **0.9906** | **−25.67°** | −28.04° | **+2.37°** |
| 12.00 | 0.9782 | −39.70° | −43.20° | +3.50° |
| 21.00 | 0.9383 | −70.44° | −75.60° | +5.16° |
| **23.00** | **0.9278** | **−77.45°** | −82.80° | **+5.35°** |

★ **The amplitude term is new — neither of us had it.** The jitter attenuates by 0.93–0.99 over
3–23 Hz on top of the phase shift.

### 🛑 And it exposes a flaw in B6-FINAL's own recommendation
My `payload_time` uses `searchsorted(..., side="left")`, which **excludes equal timestamps** and so
always picks the *previous* 0x18F. On the 8.72 % of events where 0x18F is processed first, the row
really carries the **co-logged** frame at age 0 — and **co-logged frames share a `logMonoTime`, so no
timestamp-based reconstruction can tell them apart.** If my formula resolved them, ~8.7 % of rows
would show age ≈ 0. Measured: **0.000 % on all three routes**, median 9.94 ms.

⇒ **My formula bakes in the majority case and REPRODUCES the mixture rather than removing it.
"Exact" was overstated and is withdrawn.** What it does do correctly is handle **dropouts and
non-uniform gaps**, which a flat constant does not.

### What each fix actually achieves — the honest ladder
| approach | phase | amplitude | dropouts | mixture |
|---|---|---|---|---|
| flat 10 ms | over-corrects +2.4° @7.79, +5.4° @23 | not addressed | no | no |
| `H(f)`⁻¹ | correct **on average** | corrects, but gains noise up 1.078× at 23 Hz | no | on average only |
| **`payload_time`** (B6-FINAL) | correct per row **for the 91.28 %** | not addressed | **yes, exactly** | **no — inherits it** |
| **re-extraction** | exact | exact | exact | **exact** |

⇒ **The only complete fix is re-extraction that records the 0x18F timestamp per row at extract time**,
where the within-event order is still visible. Everything available on the existing caches is an
approximation, and the residual is now quantified: ≤2.4° of phase and ≤1 % of amplitude at 7.79 Hz.

### Net effect on this document: still none, and for the same reason each time
`v89_e6` compares `tq` against `rate_f`, **both from the same `last18` tuple**. Whatever the mixture
does, it does identically to both, so the *relative* phase is exactly zero and the impedance table is
untouched. The §1 correlations carry a relative skew whose residual is now bounded rather than
guessed — **the reported r values remain floors, and the mixture's own 0.93–0.99 attenuation pushes
in the same direction.**
