# SCORING — 2026-08-20 — **V103, ROUTE `0x9e`** (`75604b0a432fdc89/0000009e--54bb0788af`, 11 segments)

**Status: SCORED.** Identity confirmed, fault census clean, the pre-registered endpoint computed with
its mandatory command covariate, both operator symptoms localised in time and frequency.

> **Operator's own report on this drive (verbatim, and it outranks every number below):**
> *Grind #1 (low speed, audible grinding) **present**. High steer angle rate **ratcheting present**.
> "Seems like 6x torque available." "Provided very diverse scenarios: high-speed, low-speed, hard
> turns, LKAS engaged, LKAS dis-engaged."*
>
> 🛑 **Both symptoms he named FAILED. That is the headline. Nothing measured below changes it.**

---

## 0. WHAT THIS ROUTE IS — the largest and most diverse capture in the kit

| | route `0x9e` (V103) | previous best |
|---|---|---|
| raw duration | **647.8 s (10.80 min)**, 64,776 frames @ 101.15 Hz | — |
| **engaged** | **406.4 s** (62.74 %) | stock `0x97` ~576 s total, V102 `0x96` 566 s |
| **engaged, hands-off, 29–86 km/h** (the `f0` window) | **227.9 s** | stock 268 s · V102 152 s |
| hands-on while engaged | **11.23 %** (45.6 s) | V102 5.4 % · stock 14.4 % · V101 39.9 % |
| engagement episodes | **7** (6 ≥ 5 s, 5 ≥ 15 s, longest **173.3 s**) | — |
| speed span engaged | p10 8.5 · p50 42.1 · p90 89.4 · **max 91.6 km/h** | — |
| wheel rate engaged | p10 0.10 · p50 2.20 · p90 28.6 · **max 301.5 °/s** | — |
| engaged at rate ≥ 13 °/s | **97.0 s** (≥25: 51.1 s · ≥50: 12.6 s · ≥100: 5.7 s) | — |

**This is the first route that satisfies the `f0` drive card's item ① with 2.8× the required
exposure, AND carries ~100 s of the high-steer-rate driving the ratchet needs.** It is also the
first route with a real motorway leg (53.7 s above 85 km/h) *and* a real low-speed leg (105.9 s
engaged below 30 km/h) in the same capture.

### Per-segment breakdown
`f0-s` = engaged, hands-off, 29–86 km/h seconds. `v` = `v_rear = (ws_rl+ws_rr)/2`, **km/h**.

| seg | t range (s) | frames | eng s | hands % | **f0 s** | v p50 | v p90 | rate p50 | rate ≥13 s | grip s |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0.0–62.6 | 6,263 | 0.0 | — | 0.0 | 0.0 | 1.0 | — | 0.0 | 0.0 |
| 1 | 62.6–122.6 | 6,002 | 50.6 | 32.5 | 6.8 | 13.3 | 35.6 | 12.40 | 24.8 | 0.1 |
| 2 | 122.7–182.7 | 6,002 | 24.1 | 15.7 | 11.0 | 28.1 | 49.3 | 4.90 | 7.9 | 0.0 |
| 3 | 182.7–242.7 | 6,001 | 0.5 | 0.0 | 0.5 | 74.5 | 87.1 | 2.40 | 0.0 | 0.0 |
| 4 | 242.7–302.7 | 6,002 | 60.0 | 1.7 | 11.5 | 90.0 | 91.3 | 0.40 | 3.8 | 0.1 |
| 5 | 302.7–362.7 | 5,997 | 54.5 | 0.9 | **43.5** | 53.1 | 65.6 | 0.70 | 5.2 | 0.0 |
| 6 | 362.7–422.7 | 6,001 | 60.0 | 2.1 | **50.9** | 66.3 | 69.7 | 1.60 | 12.5 | 0.1 |
| 7 | 422.7–482.7 | 5,999 | 60.0 | 1.8 | **52.3** | 71.6 | 74.0 | 1.10 | 8.5 | 0.0 |
| 8 | 482.7–542.7 | 6,001 | 55.5 | 22.8 | 34.2 | 36.7 | 41.4 | 6.00 | **18.0** | 0.6 |
| 9 | 542.7–602.7 | 5,999 | 30.4 | 27.4 | 17.1 | 35.6 | 40.5 | 4.80 | 9.1 | 1.0 |
| 10 | 602.7–647.8 | 4,509 | 10.7 | 4.4 | 0.0 | 3.6 | 8.2 | 19.10 | 7.1 | 0.0 |

**Segments 5–7 carry the endpoint** (146.7 s of the 227.9 s `f0` window).
**Segments 1, 8, 9 and 10 carry the symptoms.**

⚠ **Drive-card item ③ (straight-line gripping) is again a NULL: 1.8 s in 141 runs, longest 0.1 s,
zero runs ≥ 5 s.** V102 had 0 s, stock 24 s. `corr(pressed, |wheel rate|)` engaged = **+0.494**
(record: +0.59 … +0.78). **The operator's own claim — "applying torque kills the buzz" — remains
UNTESTABLE from ordinary driving, on a fourth consecutive route.** It needs the deliberate test.

---

## 1. FAULT CENSUS — **CLEAN**

| check | value | verdict |
|---|---|---|
| `0x7FFF` sentinel, `0x14A` | **0** | pass |
| `0x7FFF` sentinel, `0x18F` | **0** | pass |
| `CONFIG_VALID` duty (`0x1AB` b0 bit7) | **1.000000** (0 zero frames of 32,388) | pass |
| `OUTPUT_DISABLED` duty (`0x1AB` b2 bit6) | 0.001359 — **44 frames, all at t = −0.0…0.9 s** | boot transient |
| `DTC` bit2 (`0x1AB` b0 bit2) | **0.000000**, 0 transitions | pass |
| `0x1AB` COUNTER +1 | 100.00 % | pass |
| `0x1AB` CHECKSUM distinct | 16/16 | pass |
| `STEER_STATUS` (`0x18F` b4 7:4) | **0: 64,668 (99.833 %) · 3: 108 (0.167 %)** | pass |
| `STEER_STATUS = 3` location | t = 0.3–1.4 s, seg 0, **parked** | the low-speed lockout (`0xC62EA`), expected |
| `STEER_STATUS = 4` (state-4 governor) | **never** | pass — V42's fix is holding |
| steering `onroadEvents` | `steerOverride` ×1339 only (driver override, normal) | pass |

**No fault. No DTC. No output disable in motion. No state-4 governor.**

---

## 2. IDENTITY — **PASS, THIS IS V103** [EVIDENCE]

V103 is the first build since V85 with **no single-frame identity witness** — `byte7[7:6]` has all
four codes allocated and `b3`'s two constant values are already claimed. `build_v103_tva.py`'s own
rule is therefore categorical, not statistical:

> **`b3` MUST VARY.** V101 pins it constant 1; V102 pins it constant 0. A `b3` that takes **both**
> values within a drive is structurally impossible on any predecessor.

| statistic | measured | required |
|---|---|---|
| `byte7[7:6]` histogram | **`{3: 64,777}`** — single code, duty **1.000000** | == 3 (as V101/V102) |
| **`b3` duty** | **0.459901** — **34,986 zeros and 29,791 ones** | must be strictly between 0 and 1 |
| `b3` transitions | 32,494 over 647.8 s | > 0 |
| non-constant of b6/b5/b4 | 3 of 3 | ≥ 1 |

**VERDICT: PASS.** Written to `analysis-2020accord/_cache_r9e/r9e_identity.json`.

⚠ **One stale negative-control string in `extract_r7d.health()`** prints
*"0x14A byte7[7:6] != 0 on 100.0000 % — MUST be 0.0000 % (V94 does not write byte 7)"*. That
assertion is **hard-coded for route `7d`/V94** and does not apply to any byte7-writing build. It is a
cosmetic defect in the shared health printer, not a failure. **Reported, not fixed.**

---

## 3. ⭐ THE PRE-REGISTERED ENDPOINT — `f0`, the `Re(Z)` zero crossing

### 3.0 Estimator validation, run FIRST
`rlog-tools/rez_control.py` pins the frozen `decode_v90_probe` estimator to **0.00 % on all ten
bands** against `v92_rez.log`'s published route-77 table (221/221 windows). **Passed before scoring.**

And the whole chain reproduces the published arms to four decimal places, which validates the new
route-`9e` extractor end to end:

| arm | published `f0` | this run | delta |
|---|---|---|---|
| STOCK 1× | 21.90 | 21.90 | **+0.001 Hz** |
| V100 4× | 23.61 | 23.61 | **−0.004 Hz** |
| V102 6× | 24.90 | 24.90 | **+0.004 Hz** |

### 3.1 THE RESULT

Conditioning: engaged · **hands-off** · moving · 29–86 km/h · 5.12 s Hann windows · 50 % hop.
**Bootstrap unit = ENGAGEMENT EPISODE** (primary). The window bootstrap is quoted only for
comparability with the published table, which used it and therefore understates its CIs.

| build | gain | ×stock | n win / ep | eff. s | **`f0`** | 95 % CI (**episode**) | 95 % CI (window) | **median \|0x0E4\|** |
|---|---|---|---|---|---|---|---|---|
| STOCK 1× | 891 | 1.0 | 102 / 14 | 258 | **21.90** | [21.46, 22.63] | [20.92, 23.05] | **465** |
| V100 4× | 3564 | 4.0 | 22 / 11 | 56 | **23.61** | [23.21, 24.01] | [23.23, 23.96] | 253 |
| V102 6× | 5346 | 6.0 | 51 / 14 | 129 | **24.90** | [24.27, 25.37] | [24.61, 25.29] | 98 |
| **V103 6×** | **5346** | **6.0** | **40 / 11** | **101** | **25.23** | **[24.88, 25.91]** | [24.91, 25.69] | **96** |

- **V103 − V102 = +0.33 Hz, episode CIs OVERLAP.**
- **V103 − STOCK = +3.33 Hz, episode CIs DISJOINT.**
- The law `f0 ≈ 21.3 + 0.60 × (gain multiple)` predicts **24.9 Hz** at 6×. **Observed 25.23 Hz.**

### 3.2 🛑 THE MANDATORY COMMAND COVARIATE

The command is **essentially identical between V102 and V103** — in-band median `|0x0E4|` 98 vs 96 —
so the covariate barely moves anything. **That is the good case: the comparison is clean.**

| build | med \|0x0E4\| | `f0` obs | `f0` adj (−1.93 Hz/e-fold, x-build law) | `f0` adj (−1.28, within-V102 law) |
|---|---|---|---|---|
| STOCK 1× | 465 | 21.90 | 24.90 | 23.89 |
| V100 4× | 253 | 23.61 | 25.42 | 24.81 |
| V102 6× | 98 | 24.90 | 24.90 | 24.90 |
| **V103 6×** | **96** | **25.23** | **25.17** | **25.19** |

- **V103 − V102 after adjustment: +0.27 Hz (x-build law) / +0.29 Hz (within law).**
  The command difference alone predicts only +0.04…+0.06 Hz.
- 🛑 **And the adjusted column reproduces §3.6 of the handoff exactly**: STOCK's adjusted `f0`
  (24.90) lands **on top of V102's** (24.90). **Adjusted for command, the entire stock→V102 march
  disappears.** [EVIDENCE, and it strengthens the existing BELIEF that most of the `f0` march is
  command amplitude, not the gain cell.]

### 3.3 THE NOISE FLOOR — computed BEFORE any ratio was quoted

**Split-half over episodes, 200 draws: |Δ`f0`| p50 = 0.61 Hz, p90 = 0.93 Hz, 95 % interval
[−1.04, +1.05] Hz.**

⇒ **The endpoint's irreducible noise floor on this route is ±1.05 Hz. The observed +0.33 Hz shift is
a THIRD of it and is NOT resolvable.**

### 3.4 SPEED-MATCHED, because V103's windows sat 1.1 m/s faster than V102's

`f0` moves +0.157 Hz/(m/s), so a 1.1 m/s difference is worth ~0.17 Hz — half the observed delta.

| speed window | STOCK | V102 | **V103** | V103 − V102 |
|---|---|---|---|---|
| 29–86 km/h | 21.90 [21.44, 22.57] | 24.90 [24.30, 25.39] | **25.23 [24.87, 25.97]** | +0.33 |
| 29–50 km/h | 22.67 [21.75, 23.39] | 24.94 [24.54, 25.95] | **25.14 [23.97, 25.98]** | +0.20 |
| 50–68 km/h | 22.85 [21.97, 23.77] | 24.90 [22.57, 25.63] | **25.20 [24.79, 25.91]** | +0.30 |
| 60–85 km/h | 21.30 [20.84, 22.64] | 25.54 [23.89, 26.16] | **25.83 [25.65, 26.86]** | +0.29 |

**V103 sits 0.20–0.33 Hz above V102 in every speed window — a consistent DIRECTION, in the WRONG
direction (higher = worse), but every CI overlaps and every delta is well inside the ±1.05 Hz floor.**

### 3.5 ⇒ THE ENDPOINT VERDICT

> **`f0` = 25.23 Hz [24.88, 25.91], n = 40 windows in 11 episodes, 101 s effective, median
> `|0x0E4|` = 96, command-adjusted 25.17 Hz.**
>
> **V103 did NOT move `f0`.** The +0.33 Hz shift is inside the split-half noise floor (±1.05 Hz), its
> CI overlaps V102's, it survives the command adjustment at +0.27 Hz, and it is in the wrong
> direction. **This is exactly what `docs/DRIVE-CARD-V103.md` wrote down before the drive:**
> *"We predict V103 moves the crossing by 0.06–0.3 Hz. We can only detect about 1 Hz. ⇒ We are
> predicting, in advance, that we will NOT be able to see it."*
>
> **The pre-registration held. The result is a correctly-anticipated null, not a failure — and it is
> also not evidence the biquad did nothing.** Nothing in this drive can distinguish "the filter moved
> `f0` by 0.06–0.3 Hz" from "the filter did nothing", and the drive card said so in advance.

### 3.6 `Re(Z)` IN FIXED BANDS — all four arms, one estimator, episode-bootstrapped

Validity gates (handoff §3.4): real coh² at 22–26 ≥ 0.10 · shuffled-pair coh² < 0.02 · ratio ≥ 5.
**V103: coh² 0.847, shuffled 0.0002, ratio 4,021. ALL PASS.**

| band | STOCK 1× | V100 4× | V102 6× | **V103 6×** |
|---|---|---|---|---|
| **6–9** (ratchet, sign-stable control) | **−1509** [−1786, −1234] | −3372 [−4251, −2571] | −3953 [−4289, −3232] | **−3639** [−4324, −3114] |
| 15–22 | −1131 [−1320, −844] | −1005 | −1179 | **−1135** [−1629, −904] |
| 18–22 | −476 [−574, −320] | −619 | −707 | **−751** [−1102, −591] |
| **20–28** (spec primary, band-RMS) | **+338** [+143, +523] | −35 ( . ) | −100 ( . ) | **−50** [−117, +47] ( . ) |
| 21.5–25.5 (legacy) | +300 [+144, +468] | −41 ( . ) | **−147** [−207, −37] | **−115** [−220, −71] |
| **22–26** (`Re(Z)` primary) | **+398** [+203, +604] | +65 ( . ) | **−128** [−181, −21] | **−81** [−153, −42] |
| 26–31 (⚠ tracks the dose) | +1061 | +790 | +376 | **+284** |
| **31–35** (negative control) | +1167 [+879, +1441] | +1159 | +908 | **+895** [+665, +1107] |

- **The negative control is stable across all four arms (1167 / 1159 / 908 / 895)** — the conditioning
  is doing its job.
- **V103 remains ANTI-DAMPED at 22–26 Hz (−81, CI excludes 0), exactly like V102 (−128), against
  stock's +398.** The sign the whole programme is chasing has **not** flipped back.
- **6–9 Hz — the ratchet band — is −3639 on V103 vs stock's −1509: 2.4× stock's anti-damping.**
  V102 was −3953 (2.6×). **No change.**

### 3.7 THE SLIDING SIGN MAP — V103 is superimposable on V102

```
Hz          16  17  18  19  20  21  22  23  24  25  26  27  28  29  30  31  32  33  34
STOCK 1x     N   N   N   N   N   .   P   P   P   P   P   P   P   P   P   P   P   P   P
V100  4x     N   N   N   N   N   N   .   .   P   P   P   P   P   P   P   P   P   P   P
V102  6x     N   N   N   N   N   N   N   N   .   P   P   P   P   P   P   P   P   P   P
V103  6x     N   N   N   N   N   N   N   N   .   P   P   P   P   P   P   P   P   P   P
```
*(N = 95 % CI entirely below zero = ANTI-DAMPED · P = entirely above = DAMPED · . = straddles)*

**V103's row is bit-identical to V102's. Whatever Honda's biquad did, it did not move the crossing.**

### 3.8 WITHIN-ROUTE COMMAND STRATIFICATION — drive-card item ②, and it REPLICATES

| arm | n | med \|0x0E4\| | v p50 | `f0` | 95 % CI |
|---|---|---|---|---|---|
| LOW cmd | 20 | 66 | 18.86 m/s | 26.36 | [25.75, 27.72] |
| HIGH cmd | 20 | 166 | 14.87 m/s | 25.07 | [24.61, 25.46] |

**HIGH − LOW = −1.29 Hz over a 2.49× command range = −1.41 Hz per e-fold, CIs DISJOINT.**
V102's own within-route value was −0.99 Hz over 2.16× = −1.28 Hz/e-fold. **Replicated on a second
build.** ⚠ **The speed ratio is 0.79×, NOT matched** — so this is partly a speed contrast and the
−1.41 is an upper bound on the pure amplitude slope. Reported with that caveat, as `route-stock` did.

---

## 4. THE SYMPTOMS — located in time and in frequency

**Instrument: driver-side torque `tq` (`0x18F` bytes 0:2 × −1), 2.53 s Hann windows, 50 % hop,
median over windows** (the spec's pre-registered summary statistic). Window length stated per spec §5.

### 4.1 THE TWO SYMPTOMS SEPARATE CLEANLY — different speed, same engagement

Top-decile census over all 505 windows of the route:

| band | top-decile engaged | hands-on | **v p50** | **rate p50** | (whole route: eng 0.63 · v 38 · rate 1.4) |
|---|---|---|---|---|---|
| **6–9 Hz** (ratchet) | **1.00** | 0.33 | **36 km/h** | **13.2 °/s** | |
| **15–22 Hz** (grind) | 0.97 | 0.21 | **11 km/h** | 16.1 °/s | |
| **20–28 Hz** (vibration) | 0.97 | 0.10 | **13 km/h** | 14.8 °/s | |

> **[EVIDENCE] The 6–9 Hz ratchet band peaks at ~36 km/h with the hands ON. The 15–28 Hz grind bands
> peak at 11–13 km/h with the hands mostly OFF. Both are ~100 % ENGAGED against a route baseline of
> 63 %.** That is a two-symptom split that matches the operator's two reports exactly: grinding at
> low speed, ratcheting at high steer-angle rate.

### 4.2 THE RATCHET SCALES WITH WHEEL RATE — and ONLY when engaged

`tq` band-RMS, median over 2.53 s windows, classified by each window's own median `|wheel rate|`:

**ENGAGED (304 windows)**
| rate bin °/s | n | v p50 | hands | 2.5–4.5 | **6–9** | 15–22 | 20–28 |
|---|---|---|---|---|---|---|---|
| still <1 | 116 | 69 | 0.00 | 11.2 | **16.3** | 27.7 | 17.0 |
| micro-lo 1–6 | 81 | 43 | 0.05 | 17.0 | **60.3** | 73.1 | 107.6 |
| micro-hi 6–13 | 50 | 40 | 0.22 | 34.6 | **369.1** | 156.8 | 287.4 |
| **ratchet 13–25** | 43 | 21 | 0.22 | 34.2 | **489.9** | **390.4** | **390.2** |
| ratchet-hi 25–50 | 9 | 11 | 0.66 | 111.4 | 459.8 | 216.7 | 126.2 |
| macro >50 | 5 | 13 | 0.78 | 129.5 | 155.8 | 101.6 | 57.8 |

**MANUAL (101 windows)** — 6–9 Hz is **flat at 23.8 → 42.8** across *every* rate bin.

> **[EVIDENCE] Engaged, the 6–9 Hz ratchet band rises 30× from 16.3 (still) to 489.9 (13–25 °/s).
> Manual, over the same rate range, it does not move at all (33 → 29). The rate dependence is
> ENGAGEMENT-SPECIFIC, not a property of turning the wheel.**

### 4.3 ENGAGED / MANUAL, MATCHED ON SPEED **AND** RATE

Ratio of median 2.53 s 6–9 Hz band-RMS. > 1 means engagement amplifies. CI = window bootstrap
within the cell.

| v km/h | rate °/s | n_E | n_M | **`tq` 6–9 E/M [95 % CI]** | rate_c | angle | **IMU lat** |
|---|---|---|---|---|---|---|---|
| 0–30 | 1–6 | 19 | 7 | 1.90 [0.80, 3.64] | 0.80 | 0.95 | 0.75 |
| **0–30** | **13–50** | 35 | 11 | **24.29 [10.77, 48.37]** | 8.93 | 5.22 | **0.70** |
| 0–30 | >50 | 5 | 11 | 6.54 [0.99, 19.00] | 1.67 | 1.55 | 2.98 |
| 30–60 | 1–6 | 36 | 11 | 1.03 [0.72, 1.87] | 0.82 | 0.87 | 0.93 |
| **30–60** | **6–13** | 30 | 7 | **10.65 [6.80, 21.30]** | 3.65 | 3.22 | **0.77** |
| **30–60** | **13–50** | 11 | 7 | **21.64 [13.31, 33.49]** | 3.10 | 2.75 | **1.25** |
| 60–95 | 1–6 | 26 | 17 | 2.16 [1.11, 3.98] | 1.22 | 1.22 | 0.67 |

> **[EVIDENCE] Matched on BOTH axes, engagement multiplies the 6–9 Hz driver-torque band by
> 10.7×–24.3× whenever the wheel is moving faster than ~6 °/s, and by 1.0×–2.2× (mostly n.s.) when it
> is not.** The prior record figure was a pooled **2.8×** (`accord-engagement-amplifies-6-9hz`);
> **this route, with 97 s at rate ≥ 13 °/s, shows the 2.8× was an average over a strongly
> rate-conditional effect.**
>
> 🛑 **And the IMU lateral ratio stays at 0.70–1.25 in every cell. The chassis does not see it. The
> ratchet lives in the column/rack, not in the car's body motion.**

### 4.4 WHICH CHANNEL CARRIES THE RATCHET — coherence against driver torque at 6–9 Hz

147 engaged windows of 5.06 s, shuffled-pair control:

| x → `tq` | coh² 6–9 | shuffled | phase ° | gain |
|---|---|---|---|---|
| **EPS 427 lane (signed `gp-0x6b4c`)** | **0.892** | 0.0066 | −39.7 | 4.295 |
| filtered rate `0x18F` | 0.792 | 0.0000 | −122.1 | 119.3 |
| steer rate `0x14A` | 0.777 | 0.0102 | −150.4 | 94.6 |
| steering angle | 0.725 | 0.0019 | −61.3 | 3870 |
| **LKAS command `0x0E4`** | **0.237** | 0.0006 | +20.7 | 7.5 |
| IMU lateral | **0.002** | 0.0016 | +136.8 | — |
| IMU vertical | **0.000** | 0.0010 | −162.3 | — |

> **[EVIDENCE, and it replicates `accord-ratchet-characterised-on-route-4f`] The ratchet is in the
> column and in the EPS's own assist-sum lane (coh² 0.89), NOT in openpilot's command (0.24) and NOT
> in the chassis (0.00).** The command is a *weak* participant, not the driver.

### 4.5 ENVELOPE — `scipy.signal.hilbert`, **not** the kit's rectified `band_envelope`

| channel | arm | p50 | p90 | p99 | burstiness p90/p50 |
|---|---|---|---|---|---|
| `tq` | **engaged** | 53.7 | **926.2** | 1957.8 | **17.25** |
| `tq` | manual | 38.3 | 96.5 | 186.8 | 2.52 |
| `rate_c` | engaged | 0.70 | 8.94 | 19.23 | 12.74 |
| `rate_c` | manual | 0.82 | 2.54 | 6.88 | 3.09 |

`corr(log envelope, log |wheel rate|)` engaged: **`tq` +0.615 · `rate_c` +0.664 · `e4tq` +0.353.**

> **[EVIDENCE] The ratchet's axis is WHEEL RATE, replicated.** And engagement changes it from a
> mildly-bursty background (p90/p50 = 2.5) to a violently bursty one (17.3).

### 4.6 THE EPISODES, BY TIMESTAMP

`env` = Hilbert envelope of band-passed `tq`, threshold = the route's own 99th percentile.

**6–9 Hz (RATCHETING) — threshold 1,850 ct, engaged median 54 ct**

| t0 | t1 | seg | dur | env max | v km/h | rate p50 | rate p90 | eng | hands |
|---|---|---|---|---|---|---|---|---|---|
| **486.9** | **491.2** | **8** | **3.09 s** | **2,314** | 34.5 | 13.0 | 40.9 | 1.00 | 0.52 |
| 536.0 | 536.6 | 8 | 0.61 s | 2,198 | 41.8 | 12.2 | 34.9 | 1.00 | 0.52 |

**20–28 Hz (VIBRATION/GRIND) — threshold 817 ct**

| t0 | t1 | seg | dur | env max | v km/h | rate p50 | rate p90 | eng | hands |
|---|---|---|---|---|---|---|---|---|---|
| 272.5 | 273.3 | 4 | 0.50 s | 1,160 | **91.0** | 30.0 | 42.6 | 1.00 | 0.22 |
| 287.3 | 288.5 | 4 | 0.57 s | 1,043 | **90.2** | 26.2 | 42.5 | 1.00 | 0.19 |

Secondary 15–22 / 20–28 Hz clusters (top-14 lists) sit at **seg 10 t ≈ 609–618 s @ 7–8 km/h**,
**seg 5 t ≈ 322–331 s @ 3.6–4.0 km/h**, **seg 6 t ≈ 417–419 s @ 5.3–5.8 km/h**,
**seg 2 t ≈ 142–160 s @ 3.7–7.6 km/h** — i.e. the **low-speed grinding** the operator reported.

### 4.7 ⭐⭐ THE COMMAND RAILS *INSIDE* THE STRONGEST RATCHET EPISODE

19 rail excursions (`|0x0E4| ≥ 4096`) while engaged, 14.6 s total. The two longest:

| t0 | dur | seg | env 6–9 during | engaged median env | v km/h | rate p50 |
|---|---|---|---|---|---|---|
| **487.0** | **3.96 s** | 8 | **1,979** | 54 | 34.7 | 13.1 |
| **492.2** | **1.81 s** | 8 | **1,602** | 54 | 34.4 | 18.6 |
| 123.0 | 2.48 s | 2 | 276 | 54 | 27.6 | 28.6 |
| 78.7 | 1.60 s | 1 | 136 | 54 | 13.0 | 91.3 |

**The route's longest command saturation sits exactly on its strongest ratchet episode**
(env 1,979 vs a median of 54 — **37×**). But rows 3–4 are the CONTROL: railing at t = 123.0 s and
78.7 s produced env = 276 and 136. **Railing alone does not produce the ratchet.**

**Zoom, 0.25 s bins, t = 485.75 → 487.00 s:**

| t | env 6–9 | \|0x0E4\| | rail % | angle ° | rate °/s |
|---|---|---|---|---|---|
| 485.75 | 171 | 612 | 0 | −14.3 | 13.4 |
| 486.00 | **805** | 1300 | 0 | −16.9 | 25.8 |
| 486.25 | **1691** | 2526 | 0 | −21.4 | 14.2 |
| 486.50 | **1694** | 3228 | 0 | −26.0 | 12.7 |
| 486.75 | 1883 | 3872 | 20 | −31.3 | 13.4 |
| 487.00 | 2091 | **4096** | **100** | −35.5 | 12.9 |

> **[EVIDENCE, single episode] The ratchet envelope rises 11× (171 → 1883) BEFORE the command
> reaches the rail.** The whole event is a hard **right** turn (negative angle, per the
> operator-confirmed convention) at 34 km/h sweeping −11° → −78° with the hands on, then unwinding
> to +39° by t = 495.5 s.
>
> **[BELIEF] The ratchet LEADS the rail.** Across the whole engaged record, `corr(rail(t),
> env69(t+lag))` peaks at **lag = −1.48 s, r = +0.338** — i.e. the envelope leads. But the
> correlation is broad and shallow (+0.23…+0.34 across ±3 s), so the lead is not sharply resolved.

### 4.8 IS THERE A ~23 Hz LINE ON THIS ROUTE?

**The operator did NOT report vibration on this drive.** Asked of the data anyway, with a proper
null (chi²₂ surrogates of the median-smoothed pooled PSD, averaged over the same n windows) and a
split-half frequency-stability check:

| arm | n win | v p50 | peak | prominence | null p95 | split-half | verdict |
|---|---|---|---|---|---|---|---|
| ENG hands-off 29–86 km/h | 99 | 63 | 24.50 Hz | 1.29 | 1.41 | 27.26 / 25.29 | **no line** |
| ENG hands-off 60–85 km/h | 48 | 69 | 25.29 Hz | 2.13 | 1.61 | 27.26 / 25.29 | line, but **UNSTABLE** |
| ENG hands-off 29–50 km/h | 24 | 39 | 22.13 Hz | 1.61 | 2.00 | 30.42 / 25.68 | **no line** |
| **ENG low speed <30 km/h** | **66** | **13** | **21.73 Hz** | **3.05** | **1.65** | **21.73 / 21.73** | ⭐ **LINE PRESENT, STABLE** |
| MANUAL moving 29–86 km/h | 51 | 50 | 28.45 Hz | 1.25 | 1.58 | 15.80 / 21.73 | **no line** |

> **[EVIDENCE] There IS one line on this route, and it is NOT at highway speed: 21.73 Hz, engaged,
> below 30 km/h, prominence 3.05× local median against a null p95 of 1.65, and the split-half puts it
> in the SAME bin twice.** It is absent manually and absent above 30 km/h.
>
> ⚠ 🛑 **This is a genuine methodological correction to the first pass of this scoring.** The
> original phase-shuffle control was a **no-op** — it randomised the phase of `X` and then took
> `|X e^{iφ}|² = |X|²`, returning the real spectrum bit-for-bit (4.42 vs 4.42). Under a real null,
> the highway "line" evaporates and only the low-speed one survives. **Do not cite the first pass.**
>
> **The 21.73 Hz low-speed line co-locates exactly with the operator's grinding #1.** [EVIDENCE for
> the co-location; **BELIEF** that it is the grinding's mechanism.]

---

## 5. THE V103 CAVE — what each rung measured, and what it licenses

Bit map read from `analysis-2020accord/build_v103_tva.py`, not from memory.

### 5.1 DUTIES vs THE BUILD'S OWN PREDICTION

| bit | measurand | all | **engaged** | manual | eng&mov | predicted (from V102's flight) |
|---|---|---|---|---|---|---|
| b7 `0x80` | `gp-0x6b4c < 0` — assist-sum sign | 0.2390 | **0.3808** | 0.0002 | 0.3804 | ~0.27 |
| b6 `0x40` | `|r24| ≥ |r26|` — rate-lane comparator | 0.9288 | **0.9179** | 0.9472 | 0.9174 | 0.8991 |
| b5 `0x20` | `|friction| ≥ |inertia|` | 0.3294 | **0.2384** | 0.4826 | 0.2391 | 0.2481 |
| b4 `0x10` | `sign(r24) < 0` | 0.3934 | **0.4409** | 0.3136 | 0.4415 | 0.4091 |
| **b3 `0x08`** | **`sign(D_state) < 0`** — `gp-0x3680`, NEW | 0.4599 | **0.4675** | 0.4472 | 0.4676 | n/a |

**b6, b5 and b4 land within 0.02–0.03 of their predictions; b7 runs 0.11 high (0.38 vs 0.27).**
The cave is doing what V102's did. `b7 = 0.0002` in manual is the expected structural zero (the
assist sum is not driven when LKAS is off).

**By wheel rate, engaged — both predicted monotone trends REPLICATE:**

| rate °/s | n | b7 | b6 | b5 | b4 | b3 |
|---|---|---|---|---|---|---|
| 0–0.35 | 9,214 | 0.2774 | 0.8487 | 0.1843 | 0.3858 | 0.4569 |
| 1–3 | 6,291 | 0.3772 | 0.9167 | 0.3163 | 0.4389 | 0.4597 |
| 6–13 | 4,813 | 0.4648 | 0.9697 | 0.2109 | 0.4897 | 0.4856 |
| 13–25 | 4,586 | 0.4453 | **0.9823** | 0.1751 | 0.4773 | 0.4745 |
| 25–50 | 3,853 | 0.4506 | **0.9875** | 0.1612 | 0.4975 | 0.4752 |
| >50 | 1,257 | 0.4940 | 0.9379 | **0.7399** | 0.4399 | 0.4638 |

**b6 rises 0.849 → 0.988 with wheel rate** (predicted 0.836 → 0.992). **`r24` — the direct-derivative
lane — dominates `r26` on 98.8 % of frames in the ratchet regime.** [EVIDENCE, comparator, immune
to sizing.]
**b5 collapses from 0.32 to 0.16 across the mid-rate range then jumps to 0.74 above 50 °/s** — the
inertia term wins in the ratchet regime and the friction term wins again in a fast slew.

### 5.2 b7 + 427 = a fully signed `gp-0x6b4c` — **but the channel is UNDER-RANGED**

| | V102 (route 96) | **V103 (route 9e)** |
|---|---|---|
| frames | 43,809 | 32,388 |
| nonzero | 60.49 % | 57.95 % |
| distinct | 127 | 115 |
| p50 / p90 / p99 | 3 / 24 / 73 | 2 / 29 / 63 |
| **max** | 130 | **117** |
| **field used** | **12.7 %** | **11.4 %** |
| sat @1023 / @800 | 0.0000 % | **0.0000 %** |

> 🛑 **GATE-3 VIOLATION, CARRIED FROM V102 (not new to V103): the 10-bit `0x1AB` field is under-used
> by ~8.7×.** The `sar 6` packer would need `|gp-0x6b4c| ≥ 13,094` counts to fill it; the lane
> reaches 1,498. **A `sar 3` packer (V90/V91's) would have filled the field and bought 3 bits of
> amplitude resolution for free.** Signs and zero crossings are exact regardless.

### 5.3 ⭐ b3 — the NEW rung, `sign(D_state)` — **HONESTLY, IT IS NEARLY A COIN FLIP**

`gp-0x3680` is the PID's own D-term accumulator (`FUN_0003a382`), 32-bit, two gp-relative accesses
in the whole image, both inside that function.

**Raw structure:** duty 0.4675 engaged, **32,494 sign changes in 647.8 s = 50.16/s**, run lengths
p50 = **2 frames**, p90 = 4, max = 30.

**Is it more than a coin flip per frame?** Run-length distribution vs the geometric null implied by
its own `P(stay)`:

| run length k | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| **ENGAGED observed** | **0.451** | **0.309** | 0.141 | 0.049 | 0.025 | 0.012 |
| geometric null | 0.503 | 0.250 | 0.124 | 0.062 | 0.031 | 0.015 |
| MANUAL observed | 0.539 | 0.220 | 0.116 | 0.056 | 0.031 | 0.015 |

**Engaged: a deficit of 1-frame runs and an excess of 2-frame runs — a mild preference for a
period-2 (≈25 Hz) alternation. Scaled χ² = 544 engaged vs 106 manual, a ~5× stronger departure.**

**Band share of `b3`'s own sign power (1–45 Hz), episode-bootstrapped:**

| arm | n win / ep | **20–28 Hz share** | 95 % CI |
|---|---|---|---|
| **ENG all moving** | 147 / 6 | **0.2898** | [0.2395, 0.3202] |
| **ENG hands-off 29–86 km/h** | 36 / 10 | **0.2460** | [0.2156, 0.2774] |
| MANUAL moving | 46 / 5 | **0.1676** | [0.1614, 0.1717] |
| STANDSTILL | 27 / 6 | 0.1780 | [0.1691, 0.2005] |
| *white-noise baseline (bandwidth alone)* | — | *0.182* | — |

> **[EVIDENCE] Engaged/manual share ratio = 1.729, episode-bootstrap CIs DISJOINT. Manual (0.168)
> and standstill (0.178) both sit ON the white-noise baseline of 0.182; engaged sits 35–59 % ABOVE
> it.** ⇒ **When LKAS engages, the PID's D-term acquires an excess of 20–28 Hz sign content that is
> not there in manual driving.** This is the first direct look inside the loop at the band where
> `f0` lives, and it says the D-term is *participating*.

🛑 **THREE HARD LIMITS ON THAT CLAIM, stated up front:**
1. **NO SPECTRAL LINE SURVIVES A PROPER NULL.** Under chi²₂ surrogates the peak is not significant
   on any arm and the **split-half is UNSTABLE everywhere** (e.g. 3.75/23.31 Hz). ⚠ **The first pass
   of this analysis reported "b3 peaks at 24.30 Hz ×2.86 engaged". THAT IS WITHDRAWN** — it used a
   band-median denominator with no null behind it. The *share* survives; the *line* does not.
2. **NO MAGNITUDE PARTNER.** b3 is a bare sign bit. It cannot say how big `D` is — only how often it
   changes sign and what that sign agrees with. Per the design law this is the weaker half of a rung.
3. **UNDER-SAMPLED.** 48.3 % of runs are ONE frame at 101.15 Hz. A p50 run of 2 frames *is* the
   25.3 Hz Nyquist-adjacent bin. **[BELIEF, stated as a limit] the ~25 Hz reading is a LOWER BOUND;
   any true content above 50.6 Hz folds into this band and is indistinguishable here.**

**What `sign(D_state)` agrees with (engaged & moving, 0.5 = chance):**

| hypothesis | agreement |
|---|---|
| **`−d/dt(wheel rate)`, i.e. −angular acceleration** | **0.6223** |
| `sign(gp-0x6b4c)` (the assist sum) | 0.5838 |
| `+wheel rate` | 0.5733 |
| `−d/dt(driver torque)` | 0.5453 |
| `sign(r24)` (b4) | 0.5146 |
| LKAS command `0x0E4` | 0.5066 |
| driver torque | 0.4975 (**chance**) |

> **[BELIEF] `D_state` behaves like −(angular acceleration)** — its strongest single agreement, at
> 62.2 %. That is what a D-term on a *rate* error looks like when the dominant content is the wheel's
> own acceleration. **It is NOT the driver-torque derivative (0.545) and NOT the command (0.507).**

### 5.4 b7's sign-vs-command agreement — a **METHOD** discrepancy, not a firmware change

| route | build | `|0x0E4| > 0` | `> 100` | `> 400` | `> 1600` |
|---|---|---|---|---|---|
| `0x96` | V102 | **0.7616** | 0.7809 | 0.6795 | 0.6104 |
| `0x9e` | **V103** | **0.7615** | 0.7709 | 0.6894 | 0.6620 |

`memory/accord-gp6b4c-is-an-11-slot-assist-sum.md` records V98 (route `0x81`) measuring this at
**52.80 % ≈ chance**. **V102 and V103 agree to four decimals here (0.7616 vs 0.7615)**, so the
difference from V98 is a **conditioning/method difference or a build difference at V98, not something
V103 changed.** ⚠ **Reported as an open discrepancy. The memory is NOT retracted.** Closing it needs
V98's exact conditioning re-run on route `0x81`.

---

## 6. THE LKAS COMMAND `0x0E4` — and the "widen the range?" decision

### 6.1 DISTRIBUTION, ENGAGED (n = 40,638 frames = 406.4 s)

median **188** · p75 467 · p90 **1,609** · p99 **4,096** · max **4,096** · mean 554.8 · exactly zero 0.36 %

**Occupancy in 256-wide bins: 59.58 % of engaged frames sit below 256 counts (6.25 % of the rail);
76.60 % below 512; 88.28 % below 1,024.**

### 6.2 RAIL DUTY — **the rail is only reached in the two symptomatic regimes**

| regime | sec | p50 | p90 | p99 | **@ rail %** | ≥90 % | ≥50 % |
|---|---|---|---|---|---|---|---|
| ENGAGED all | 406.4 | 188 | 1,609 | 4,096 | **3.605** | 4.309 | 8.084 |
| **ENG < 30 km/h (grind #1)** | 105.9 | 470 | 3,848 | 4,096 | **8.550** | 10.855 | 20.132 |
| ENG 30–60 km/h | 135.7 | 274 | 1,787 | 4,096 | 4.126 | 4.435 | 8.502 |
| **ENG 60–85 km/h** | 108.8 | 106 | 310 | 566 | **0.000** | 0.000 | 0.000 |
| **ENG > 85 km/h** | 53.7 | 70 | 190 | 420 | **0.000** | 0.000 | 0.000 |
| **ENG rate ≥ 13 °/s (ratchet)** | 97.0 | 665 | 4,096 | 4,096 | **10.324** | 12.180 | 22.741 |
| ENG rate < 1 °/s (straight) | 158.0 | 94 | 295 | 1,493 | 0.222 | 0.316 | 0.709 |
| ENG hands-off 29–86 km/h | 227.9 | 152 | 566 | 4,096 | 1.238 | 1.365 | 2.361 |
| **ENG hands-ON** | 45.6 | 1,592 | 4,096 | 4,096 | **18.471** | 20.706 | 38.716 |

**Rail excursions: 19 runs, 14.6 s total, p50 0.31 s, p90 1.97 s, max 4.01 s.**

### 6.3 QUANTISATION — **the command is NOT quantisation-limited**

- **4,562 distinct codes** used engaged, spanning the full [−4096, +4096].
- **Smallest gap between adjacent observed codes = 1 LSB. Median gap = 1 LSB.**
- Frame-to-frame |Δ| (nonzero): min 1 · **p50 28** · p90 123 · max 1,424.
- 1 LSB of `0x0E4` = `4 × gain / 32768` = `4 × 5346 / 32768` = **0.6526 counts of assist** at 6×.
- Sanity: `corr(sendcan 0x0E4, bus 0x0E4)` engaged = **0.9982**.

### 6.4 ⇒ THE DECISION

> **[EVIDENCE] A WIDER accepted command range would NOT buy finer control.** The command already
> resolves to 1 LSB, uses 4,562 distinct codes, and **59.6 % of engaged frames sit below 6.25 % of
> the rail**. There is no quantisation floor to relieve.
>
> **What a wider range WOULD buy is HEADROOM — and only where the car is already symptomatic.** The
> rail is touched **0.000 %** of the time above 60 km/h and **0.22 %** of the time going straight,
> but **8.6 %** below 30 km/h, **10.3 %** at ratchet-rate, and **18.5 %** with hands on.
>
> 🛑 **The converse is the interesting move, and it is the one that answers "command more finely":
> a NARROWER rail with a compensating firmware gain increase.** The command lives in the bottom
> 6 % of its range; halving the rail would double the effective resolution *where the command
> actually is* at zero cost in reachable authority for 96 % of frames — but it requires raising
> `0xC6CD0` to compensate, and **`0xC6CD0` is the measured carrier of the ~23 Hz vibration**
> (`memory/accord-the-8x-gain-is-the-carrier.md`). **That trade must not be made without re-scoring
> `f0`.**
>
> ⚠ **And note what railing is and is not.** `±4096` is *openpilot's* rail on the demand, upstream of
> the ECU. Clipping there saturates the DEMAND, not the delivered torque, and §4.7 shows the ratchet
> rises 11× *before* the rail is reached. **Widening the rail is unlikely to fix the ratchet and may
> feed it.**

---

## 7. WHAT COULD **NOT** BE COMPUTED, AND WHY

1. **Whether Honda's biquad (Part A) did anything at all.** `f0` moved +0.33 Hz against a ±1.05 Hz
   noise floor. **The drive card predicted 0.06–0.3 Hz and predicted in advance that it would be
   invisible. It was.** Nothing in this route distinguishes "small real effect" from "zero effect".
   **Closing it needs a dose ladder (a second arm at a different filter setting), not more driving.**
2. **The grip test (drive-card item ③).** 1.8 s of straight-line gripping in 141 fragments, longest
   0.1 s. **A fourth consecutive route with effectively zero.** The operator's single most specific
   mechanical claim remains untested. **Only the deliberate 20–30 s test closes it.**
3. **`b3`'s magnitude.** A bare sign bit. `D_state`'s size is unknown, so no dose or gain statement
   about the D-term is possible.
4. **Whether `b3`'s dither is really ~25 Hz.** 48 % of its runs are one frame at 101 Hz — it is at
   the sampling limit. **Any true content above 50.6 Hz aliases into this band.** Excluding that
   needs a faster tap or a counter rung, not more analysis.
5. **Causal direction on rail-vs-ratchet.** The lead is +1.48 s at r = +0.338, but the correlation is
   flat across ±3 s. **[BELIEF only.]** A within-episode onset-alignment test on many episodes would
   close it; this route has 2 clean ones.
6. **Whether the 21.73 Hz low-speed line IS the grinding.** Co-location is EVIDENCE; mechanism is
   BELIEF. There is no audio channel in this capture.
7. **The V98 52.80 % vs 76 % b7 discrepancy.** Not resolvable without re-running V98's exact
   conditioning on route `0x81`.

---

## 8. ARTEFACTS

**Cache — `analysis-2020accord/_cache_r9e/` (20 MB, 107 fields, 64,776 rows @ 101.15 Hz)**

`r9e.npz` (pooled) + `r9es0..10.npz` (per segment, `t` reset to 0) + `r9e_identity.json`,
`r9e_lane427.json`, `r9e_1ab.json`, `r9e_census.json`, `r9e_census_seg.json`, `r9e_health.json`,
`r9e_events.json`, `r9e_segments.json`, `r9e_lp.npz`.

Schema is **verbatim** the `extract_r7d` / `_cache_r6d`-onward schema, plus:

| new / route-specific field | meaning |
|---|---|
| `v103_b7 · v103_b6 · v103_b5 · v103_b4 · v103_b3` | the five cave rungs, decoded from `probe` (SAFE pairing with `t`) |
| `v102_b7 … v102_b3` | aliases of the above (b7/b6/b5/b4 are byte-identical to V102's rungs) |
| `mag427 · sgn427 · x6b4c` | `0x1AB` magnitude, b7-derived sign, and the signed lane in counts (`wire × 12.8`) |
| `x6b94` | **alias of `x6b4c`** so `v102_xb_lib.CH` finds a lane — ⚠ it is a DIFFERENT CELL on this route |
| `v_rear` | `(ws_rl + ws_rr)/2` — 🛑 **in m/s**, not km/h (`KMH = 1/3.6` in the extractor; the extractor's own print label is WRONG) |
| `lp_yaw` | `livePose.angularVelocityDevice.z`, interpolated onto `t` (**`carState.yawRate` is identically zero on this car**) |
| `ab_*` | the full `0x1AB` tap: `t1ab, b0, b1, b2, src, dlc, mt, config_valid, dtc_bit2, checksum, counter, output_disabled` |
| `raw14_b7` | the `0x14A` byte-7 tap (identity code in bits 7:6) |
| `row2raw14` | the asserted index map fixing the `raw14` off-by-one |

🛑 **`raw14` off-by-one holds here as everywhere: `t == raw14_t[1:]` and `probe == raw14_b4[1:]`.
Safe pairs are `(t, probe)` or `(raw14_t, raw14_b4)`. Never mix.**

**Code — all in `rlog-tools/`**

| file | what it does |
|---|---|
| `extract_r9e.py` | route registration + extraction + derive + identity + `lane427` (modelled verbatim on `extract_r96_r97.py`) |
| `v103_r9e_lib.py` | shared loader, masks, **episode-block bootstrap**, `f0_of`, band-RMS |
| `v103_r9e_census.py` | fault / identity / exposure / command census → `_v103_r9e_census.json` |
| `v103_r9e_f0.py` | the endpoint, all four arms, covariate, split-half, bands, sign map → `_v103_r9e_f0.json` |
| `v103_r9e_symptom.py` | regime band-RMS, top-window localisation, coherence, envelopes → `_v103_r9e_symptom.json` |
| `v103_r9e_symptom2.py` | ⚠ **supersedes** parts A/C/D2 of the above (two fixed defects) + speed-matched `f0` |
| `v103_r9e_cave.py` | rung duties, `b7`+427 signed lane, `b3` first pass → `_v103_r9e_cave.json` |
| `v103_r9e_b3.py` | `b3` with a proper null, aliasing audit, 427 under-range → `_v103_r9e_b3.json` |
| `v103_r9e_final.py` | run-length null, band-share CI, cross-route `b7`, rail duty by regime → `_v103_r9e_final.json` |

⚠ **Two defects found and fixed mid-analysis. Anyone reusing this code must know both:**
1. **Masking on an instantaneous quantity (wheel rate) and then demanding a contiguous window
   returns ZERO windows.** Window over the *engagement run*, then classify each window by its own
   median. `v103_r9e_symptom.py` parts A(rate)/D/D2 hit this and returned empty tables.
2. **A "phase-shuffled" spectral control that randomises `∠X` and then takes `|X e^{iφ}|²` is a
   NO-OP** — it returns the real spectrum bit-for-bit. Use chi²₂ surrogates of the smoothed PSD.
   The first pass reported a highway "line" that does not survive a real null.
