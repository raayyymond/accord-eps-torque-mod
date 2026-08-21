# ANALYSIS 2026-08-20 — the torsion-bar mode, and `q` (the assist lane's weight)

**Route `0x9e`, V103 on the car.** 64,776 rows @ 101.15 Hz, engaged 406.4 s in 7 episodes.

⚠ Written by the ORCHESTRATOR from the analyst's report — the analyst's own `Write` was refused by the
harness. Numbers are the analyst's; the orchestrator did not re-derive them. Method notes kept where
they matter.

---

## 1. `q` — THE ASSIST LANE'S SHARE OF THE 6-9 Hz AGGREGATOR SUM

> 🛑 **`q ~ 1/9` (by lane COUNTING) IS WRONG. The measured answer is `q(gp-0x6b86) = 10.58 * a`,
> with `a = gp-0x69a4/1024` in (0, 2.000] ⇒ `q >~ 1` for any non-trivial `a`.**

`q(lane) = |lane|(6-9) / |gp-0x6b94|(6-9)` (band-RMS, engaged) — the causal sensitivity a build needs.

### The decisive measurement — a cross-build 427 repoint [EVIDENCE]

`gp-0x6b94` (the aggregator SUM) **has been on the wire**: route `0x85` (V100) repointed the 427 lane
to it. Routes `0x96`/`0x9e` point at `gp-0x6b4c` (ONE lane). Same packer, same `sar 6`, same
12.8 ct/LSB, same cave sign bit, same estimator / masks / NFFT.

| route / build | 427 source | \|u\|/\|T_s\| @6-9 Hz (episode bootstrap 95% CI) | coh2 | shape (6-9)/(15-22) |
|---|---|---|---|---|
| `0x85` V100 | **`gp-0x6b94` — THE SUM** | **0.0946 [0.0607, 0.1042]** | **0.279** | 0.239 [0.203, 0.254] |
| `0x96` V102 | `gp-0x6b4c` — one lane | 0.2117 [0.2099, 0.2324] | 0.802 | 0.476 [0.461, 0.496] |
| `0x9e` V103 | `gp-0x6b4c` — one lane | 0.2202 [0.2027, 0.2469] | 0.888 | 0.509 [0.473, 0.553] |

⇒ `q(gp-0x6b4c)` = **2.24 / 2.33** raw; **1.99 / 2.13** normalised within-route to each route's own
15-22 Hz band (controls exposure / speed / build). Both agree.

⇒ `q(gp-0x6b86)` = `a` * 282.2/26.7 = **10.58 * a** → 1.06 @a=0.1 · 6.8 @a=0.644 · 21.2 at the cap.

### 🛑 WHY `q > 1` IS NOT AN ERROR — THE AGGREGATOR IS A NEAR-CANCELLATION AT 6-9 Hz

`coh2(T_s, gp-0x6b94)` = **0.279** while `coh2(T_s, gp-0x6b4c)` = **0.80-0.89**.
**Torque-coherent lanes largely cancel; a small, mostly INCOHERENT residue survives.**

Band-specific: at 2.5-4.5 and 15-22 Hz sum and lane are comparable (0.354 vs 0.29-0.54; 0.396 vs
0.43-0.45) — the cancellation is a **6-9 Hz phenomenon**.

Mechanism **[BELIEF]**: `pol = gp-0x6752 = -1` multiplies the base-assist magnitude, `r24` and `r26` —
but **not** `gp-0x6b4c`.

⇒ 🛑 **CONSEQUENCE FOR ANY BUILD: a high-authority edit inside a near-cancelling sum can BREAK the
cancellation and INCREASE the residue.** This is the `0xC63AC` failure class in a new form. The gating
question is no longer *"is the lever big enough"* but **"does it have the right sign"**.

### Static reachable bound [EVIDENCE]

Producer ceilings — each lane's OWN writer clamp, not its admission window (the GATE-3 error):
`6b86` +/-12288 (`0x35a8c`-`0x35aa4`, byte-verified) · `6b4c` +/-10240 · `6b62` 5786 (0 measured
engaged) · `6ad4` 1024 · `6b26` 511 · `6bbe` 512 · `6bd0` <=512 · `6ade` 0 · r24/r26 +/-8192 each.

**Sum = 47,257 against a +/-10,240 output clamp ⇒ over-subscribed 4.6x** — an independent structural
hint that cancellation is normal. Base assist's share of that worst case = **0.26**, itself 2.3x > 1/9.

### Small-signal slope [EVIDENCE]

`gp-0x6b86`'s gain w.r.t. the torque sensor is the map's local slope `a`, **UNFILTERED at 6-9 Hz**: the
EMA at `gp-0x381c` acts **only on the supra-threshold excess** (`gp-0x6b84 -> gp-0x6b7e`); the main path
`gp-0x6b82` is unfiltered. *(The analyst first read the lane as low-passed and corrected it.)*
EMA corner 1.55 Hz at k=20, 3.19 Hz at k=41; k-schedule `0xC6906`-`0xC690C` is **flat [20,20,20,20]**,
alternate arm `0xC6382` = 41.

Two NEW static bounds on the long-standing `avg(gp-0x69a4)` open item:
- **`a` <= 2.000** — every segment slope capped at `cal(0xC6384)` = 2048 (Q10) at table build.
- **mean slope <= 0.644** — X ceiling `cal(0xC6200)` = 8192, Y ceiling `cal(0xC6178)` = 5274, table
  starts at (0,0).

Measured 6-9 Hz inputs, engaged: `|T_s|` = 396.4 ct · `|x6b4c|` = 87.3 · `|e4tq|` = 25.8 ·
`|rate_f|` = 0.0514 rad/s · `|ang|` = 0.089 deg.

---

## 2. THE TORSION-BAR MODE — CONFIRMED

| estimator | `f_n` | `Q` | `zeta` |
|---|---|---|---|
| pooled 2-pole fit, `T_s` auto-spectrum, NFFT 512 | **8.162 Hz** | **10.21** | **0.0490** |
| NFFT 1024 / 256 (window-cap invariance) | 8.215 / 8.165 | 10.30 / 8.52 | — |
| **episode bootstrap 95% CI** | **[8.015, 8.187]** | **[7.49, 13.61]** | **[0.0367, 0.0667]** |
| independent: exogenous-drive \|T_s/e4tq\|^2 | **8.123 Hz** | 7.54 | 0.0663 |
| 0-5 m/s bin (the grinding regime) | **7.95** | 11.96 | — |

Predicted band from `f = (1/2pi)*sqrt(k_tb/J_eq)` with k_tb 1.5-2.5 N.m/deg, J_wheel 0.03-0.06 kg.m^2:
**6.0-11.0 Hz.** Observed **8.16**. **Q is window-cap invariant** (8.5 / 10.2 / 10.3 at NFFT 256/512/1024).

- **~18x resonant amplification of an exogenous command**: `|T_s/e4tq|` = 0.3-1.0 @3-5 Hz ->
  **12.38 @7.90 Hz** (coh2 0.366) -> 2.97 @9.9 Hz. For a 2-pole, peak/DC = Q ⇒ **Q ~ 12-18**, an
  independent estimator. ⚠ `e4tq` is not perfectly exogenous (openpilot sees `steeringAngleDeg`) but
  its own 8.1 Hz prominence is 0.21 — negligible self-content.
- **IMU null, with a REAL control.** coh2 @6-9 Hz: true (`tq`,`x6b4c`) **0.8881**; **episode-swap
  surrogate 0.0026 [0.0001, 0.0082]**; white noise 0.0004; `imu_lat` **0.0026**, `imu_vert` **0.0001**,
  `lp_yaw` **0.0027**, `v_rear` **0.0021** — all at the surrogate floor.
  ⇒ **TYRE / ROAD / SUSPENSION / WHEEL-ORDER SOURCES EXCLUDED.**
  (Not a `|X*exp(i*phi)|^2` no-op shuffle — that bug was made earlier on this route and is retired.)
- **Speed invariance**: binned `f_n` = 7.95 / 8.20 / 8.10 / 8.89 / 8.32 Hz over 0-26 m/s; per-window
  peak slope **+0.0477 [-0.0031, +0.0657] Hz/(m/s)** vs **+0.489** for wheel order 1 ⇒ **excluded by
  ~13 sigma.**
- **Amplitude**: pooled `f_n` = 8.29 / 8.35 / 8.15 Hz across the top three amplitude quartiles (100x
  range) ⇒ amplitude scales, frequency does not. `corr(ln|T_s|env, ln|u|env)` = 0.969, log-log slope
  1.194. ⇒ **the kit's "the line moved with gain" belongs to the ~21-24 Hz mode, NOT this one.**
- **Controller side**: `u/T_s` = **0.2075 at +39.7 deg** @6-9 Hz, CI [0.192, 0.233] / [+35.3, +41.3],
  coh2 0.888. P+D fit (tau_d 0/5/10 ms): a0 = 0.304-0.338, a1 = 2.0-2.3 ms ⇒ **29-37% derivative at
  7.9 Hz** — a real positive-real lead, the ingredient `L(jw)` needs to cross +1 just above `w_n`.
- **Engaged/manual** 6-9 Hz PSD **69x** (7-9 Hz 119x), 2.5-4.5 Hz 0.73x, 31-35 Hz 1.46x — **but
  15-22 Hz also moves 67x** ⇒ band-**preferential** over 6-22 Hz, not exclusive. Speeds match
  (p50 13.7 vs 12.6 m/s).

**FALSIFIERS (pre-registered):** hands-on with no `f_n` shift and no Q drop · a build detuning base
assist that leaves `gp-0x6b94`(6-9) unchanged · measured `k_tb`/`J_wheel` outside 7-9 Hz · an 8.1 Hz
line in manual at matched speed **and** torque amplitude · coherent 8.1 Hz in the chassis IMU.

---

## 3. THE NOTCH'S COLLATERAL COST — MEASURED, AND IT PASSES

### 🛑 A CONFOUND THE KIT MUST RETIRE

**`steeringPressed` IS A THRESHOLD ON THE TORQUE SENSOR ITSELF**: `|cs_tq| > 1200` agrees with
`cs_press` on **98.97% of 64,776 frames** (best single threshold; openpilot Honda `STEER_THRESHOLD`).
**[EVIDENCE]** ⇒ **every hands-on / hands-off AMPLITUDE contrast measured on `tq` is CIRCULAR** — the
"hands-on" arm is by construction the high-|torque| arm. Detector-**rate** results may survive;
amplitude ones do not.

### The driver's own 6-9 Hz content [EVIDENCE]

Per-window band-RMS (NFFT 256, medians — robust to burst domination), episode bootstrap:

| arm | n win/ep | 0.5-3 | 3-5 | **6-9** | 15-22 | 31-35 |
|---|---|---|---|---|---|---|
| MANUAL moving (load p50 **949 ct** — he IS loading it) | 99 / 7 | **266.5** | 56.5 | **33.7 [20.1, 38.7]** | 18.8 | 9.9 |
| MANUAL p90 / max | | 638 | 149 | **64.1 [27.2, 82.3]** / 119.0 | 31.4 | 18.9 |
| ENGAGED (all) | 307 / 6 | 42.5 | 17.5 | **59.4**; p90 **771.7 [432, 897]**; p99 **1243.8** | 69.7 | 10.8 |

The driver's own roll-off: **6-9 Hz is 12.6% of his 0.5-3 Hz steering content and only 3.41x his own
31-35 Hz noise floor.** Against the engaged distribution his **p90 (64.1 ct)** is **8.31%** of the
engaged p90, **6.96%** of p95, **5.15%** of p99. Load-matched engaged/manual @6-9 Hz = **4.36x**
(150-400 ct load) and **4.12x** (>2000 ct), against 15-22 Hz controls of 7.10x / 3.04x and 31-35 Hz of
1.80x / 0.93x.

⇒ **[EVIDENCE] During a symptomatic engaged episode, <= 5-8% of the 6-9 Hz torque-sensor content is
plausibly voluntary driver input.** An UPPER bound: even the 33.7 ct manual figure includes structure
ringing in response to his input — which is what we WANT notched.

### What he loses

Applying the r = 0.990 / 7.79 Hz curve to his measured manual spectrum:
**275.3 -> 271.1 counts RMS over 0.5-35 Hz — 1.52% removed.** The 6-9 Hz loss is **27.5 counts** of
driver torque (54.9 ct of assist at the `a` = 2.0 cap) against a **10,240-count** aggregator rail and a
**12.8-count** telemetry LSB ⇒ **~0.3-0.5% of rail, ~2-4 LSB. Nothing detectable.**

### 🛑 THE FALSIFIER, RECORDED WHETHER OR NOT IT FIRED

> *"If the driver's own 6-9 Hz torque were a material share of the in-band signal — say >= 30% in
> ordinary driving — the notch would remove real assist in a band he actively uses, and the wheel would
> go heavy and notchy exactly when he moves quickly. Measured, it is <= 8% during a symptomatic episode
> and only 3.4x his own noise floor, so the cost is below anything he can feel. **IT DID NOT FIRE.**
> Residual risk: route `0x9e` holds only 141 s of manual driving and essentially no fast manual inputs
> (`|rate| > 13 deg/s` yields 3 windows). His in-band capability under an aggressive input is
> UNSAMPLED. **If any future drive shows manual 6-9 Hz content above ~150 counts at
> `|rate| > 50 deg/s`, revisit this."*

### 🛑 "THE MODE RINGS FROM MANUAL STEERING TOO" — NOT SUPPORTED ON THIS ROUTE

Manual moving: peak at **5.33 Hz**; prominence(7-9.2 vs 3-5) = **0.14** (vs 2.30 for 13-16 Hz); the
2-pole fit runs to the 11 Hz boundary with Q = 3.16. **There is NO 8.1 Hz mode in the manual arm — its
6-9 Hz content is a broadband floor (33.7 ct, 1.8x its own 15-22 level), not a resonance.**
**[EVIDENCE]** Corroborates the golden model's own recorded correction (*"his hard MANUAL provocation
produced NO ratchet at all"*) and **CONTRADICTS** *"the mode rings from manual steering too"* — that
argument must not be cited as support for anything.

⚠ **It does NOT settle LKAS-CREATED vs LKAS-EXCITED**: in the manual arm his hands are ON the wheel
throughout, and grip is the kit's documented suppressor of this mode. There is no
manual-hands-off-moving arm with any excitation anywhere in the corpus. **The two hypotheses remain
unseparated. [BELIEF]**

### V103's own filter was INERT in the ratchet band [EVIDENCE]

Honda's shipped section decoded from its four floats:
`H(z) = 0.81731 * (1 - 1.8808 z^-1 + z^-2) / (1 - 1.5372 z^-1 + 0.63462 z^-2)`
⇒ zeros on the unit circle at **55.23 Hz**, poles r = 0.79663 at 42.35 Hz, DC gain 1.000034.
**At 7.79 Hz it is -0.149 dB / -10.6 deg, essentially transparent.** `0xC649B` = 1 in the V103 image
with coefficients byte-identical to stock ⇒ **V103 armed a section that is inert where the ratchet
lives.** This is why the `f0` null was correctly predicted in advance, and why nothing the operator
felt changed.

---

## 4. OPEN — what could not be computed

1. **`a = gp-0x69a4/1024` itself.** The map is rebuilt each tick from RAM `gp-0x6444...0x641e`, whose
   **ROM cal base `0xC6564...0xC658B` is 40 bytes of exact zero** (byte-read), sourced from RAM
   `gp-0x6350...0x6340` (X) and `gp-0x630c...0x62fc` (Y) written by `FUN_000389ec` via temperature /
   voltage LERPs. **No static ROM copy exists.** Closing it needs a probe on `gp-0x69a4` or the boot
   `.data` initialiser, not located.
2. **The hands-on test is NOT COMPUTABLE on `0x9e`.** 45.1 s hands-on engaged but only **6 runs
   >= 1.27 s and 1 run >= 2.53 s**; NFFT 128 resolution (0.79 Hz) exceeds the mode's bandwidth
   (0.80 Hz). Plus the circularity above. **Needs >= 4-5 contiguous hands-on engaged runs of >= 5 s —
   no route in the kit has them.**
3. **`r24`/`r26` in-band magnitude** — needs `gp-0x4f62`'s units (assumed per-tick delta at 1 kHz) and
   the live LERP gain. **[BELIEF]**
4. **`gp-0x6b26` / `gp-0x6ad4` in-band content** — no magnitude channel has ever carried either.
5. **A same-drive sum-vs-lane comparison** — `gp-0x6b94` and `gp-0x6b4c` have never been on the wire
   together; the 15-22 Hz shape normalisation is the control and it agrees.
6. **CAN-counts <-> `gp-0x4f60`-counts scale** — kit convention 1:1, order-consistent, **not
   verified**. Scales `q(gp-0x6b86)` linearly. **[BELIEF]**
