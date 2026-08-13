# SCORING 2026-08-12 — V97 on route 80 (parking-lot creep, operator aborted)

**Data:** `75604b0a432fdc89_00000080--6c8b103892--{0,1}--rlog.zst` → `analysis-2020accord/_cache_r80/`
**Extractor:** `rlog-tools/extract_r80.py` (imports `extract_r7d` → `decode_v84_probe_r6d`; the
instrument is NOT reimplemented — same code that wrote every cache since `_cache_r6d/`).
**Scorers:** `rlog-tools/v97_r80_census.py`, `v97_r80_vs_v96.py`, `v97_r80_phase.py`,
`v97_r80_matched.py`. Machine-readable: `_cache_r80/r80_census.json`, `r80_vs_v96.json`,
`r80_phase.json`, `r80_matched.json`, `r80_decoded.npz`, `r80_1ab.json`, `r80_segments.json`.

**Operator's own report: ZERO difference from V96, drive stopped.** Nothing below contradicts that,
and nothing below should be read as a symptom score. The operator scores symptoms.

---

## 1. IDENTITY

### 1.1 What is proven — EVIDENCE
| leg | reading | rules out |
|---|---|---|
| `0x14A` byte7[7:6] ≠ 0 | **10,750 / 10,750 frames = 100.0000 %** | V94 and every build ≤ V91 (their code masks bits 7:6 off at `0x55BFC` / `0x55C24`). Structural, single-frame, no free parameter. |
| byte7 b6 duty | **1.0000** on 10,750 frames | V92. `STATE.md` §A6 has already discharged this from BELIEF to **EVIDENCE** on the 7e/7f flights (V92's b6 measured 0.0000 over 87,317 frames; V96's is a hard-wired constant 1 with a 164,096-frame unbroken rail). Route 80 **extends that rail by 10,750 frames**; it does not re-open the question. |
| 427 packer residue mod 5 | {0:1563, 1:1498, 2:767, 3:826, 4:629} → **55.90 % illegal-for-`sar 1`** over 5,283 nonzero frames | V94's `sar 1` packer, arithmetically. Consistent with V96/V97's `sar 6`. |
| byte4 field `(b4>>3)&0x1F` | **{1, 9, 17, 25}**, 100 % ODD, 0 even | MAP VALIDATOR 1 + 2 **PASS**: b3 (`gp-0x674e < 28`) constant == 1 all drive; byte-4 alignment confirmed. Pre-V90 alphabet {3,7,15,23,31}: **0 frames**. |

### 1.2 🛑 V97 CANNOT BE SEPARATED FROM V96 BY ANY SINGLE FRAME — and that is structural
Byte-diff of the two plain images (read from the images, not the build scripts):

```
_v96_V92BASE-REVERT.CBE74-PROBE.6B70.374C.674E-427.6B70.SAR6_plain_image.bin
      sha256 876cf2be5800f0f8e315f8b1d63dd103ec11ee7293577808ecff5f19a849cda3
_v97_V96BASE-C63AC.102to150_plain_image.bin
      sha256 7ac009044b46eeb2fd38d9ab6c7cb634e1be6ca44eb6f5083b9897c33829c2b3   (= handoff)

ndiff = 5 bytes
  0xC63AC  0x66 -> 0x96     102 -> 150, the loop-pole coefficient A
  0xC6FFC..0xC6FFF          CRC trailer
```

The cave, the 427 repoint (`0x55DF2`), the packer scale (`0x55E10`) and every CAN bit map are
**identical**. ⇒ **Route 80 is V96-or-V97, provably not V94/V92/≤V91.** Separating V96 from V97
requires measuring the pole, which is §4.

---

## 2. REGIME CENSUS — and it is a corner V96 never visited engaged

10,749 rows · 109.2 s · 2 segments · zero `0x7FFF` sentinels on `0x14A` and `0x18F`.
`latActive` 16.0 % = **17.2 s engaged**, in **ONE contiguous episode**. 90.3 s manual.

| | n | speed km/h p05/p50/p95/max | \|rate\| °/s p50/p95/max | angle range |
|---|---|---|---|---|
| ALL | 10,749 | −0.00 / 1.73 / 6.07 / **6.60** | 4.24 / 220.7 / 476.9 | −254.0 … +389.4° |
| ENGAGED | 1,719 | 2.44 / 5.13 / 6.34 / **6.40** | 16.16 / 141.0 / 186.3 | −55.1 … +41.1° |
| MANUAL | 9,030 | −0.00 / 0.00 / 6.02 / 6.60 | 1.00 / 244.1 / 476.9 | −254.0 … +389.4° |

**Dead zones** — engaged frames:
- **35.19 % sit below 5 km/h**, i.e. inside the `0xC62EA` low-speed steer-lockout window
  (320 counts ≈ 5 km/h). But `0x18F` STEER_STATUS is **0 on all 1,719 engaged frames**; status 3
  appears on only 9 frames of the whole drive — the same 9–11 frames routes 7e/7f show. **The
  lockout was not entered.**
- **base-assist damper FactorC (≥ 35 km/h): open on 0.00 % of ALL frames.** FactorE (≥ 12.7 °/s):
  55.79 % engaged. **BOTH open: 0.00 %.** ⇒ the damper product `ch0` is **identically zero for the
  entire drive**, engaged and manual. Consistent with the standing memory; re-confirmed here.
- `steeringPressed` duty engaged **0.1966** on route 80 vs **0.0638 / 0.0568** on 7e / 7f — the
  operator had hands on the wheel ~3× as much. A regime difference, not a build difference.

---

## 3. LIVE TELEMETRY — one channel excellent, one channel DEAD

### 3.1 ✅ The 427 lane (`gp-0x6b70`, the PID reference) is ALIVE and correctly scaled
5,375 frames @ 49.83 Hz, DLC 3, src 1. COUNTER +1 on 99.96 %, CHECKSUM 16/16 distinct,
CONFIG_VALID duty 1.0000, OUTPUT_DISABLED duty 0.0009.

| | value |
|---|---|
| nonzero | **98.29 %** |
| distinct wire codes | 250 of 1024 |
| wire range | [0, 249] — **saturation 0.000 %** |
| \|gp-0x6b70\| counts (wire × 12.8) | p50 **320** · p95 **2,778** · p99 **3,059** · max **3,187** |
| against the `0xC6200` clamp ±8192 | p99 = **37.3 %** of clamp |
| LSB | 12.8 counts = 0.156 % of range |

Engaged: \|b70\| p50 602, p95 2,483, sign-negative duty 0.5988. Manual: p50 166, p95 2,816,
neg duty 0.6707. **No under-range, no clip, no rail.** This is *not* a V64/V68-class null.

### 3.2 🛑 The REGRESSOR channel (`gp-0x374c>>4`) reads ZERO MAGNITUDE — a THIRD-ROUTE REPLICATION, not a new finding

⚠ **The record already knows this.** `STATE.md` §A5 states *"V96's INSTRUMENT FAILED AND MUST BE
RE-SIZED BEFORE ANY RE-FLY … a 34× over-range … next regressor LSB should be 128–256, not 2048"*,
established on routes 7e/7f. What route 80 adds is a **third independent route, in a completely
different regime (creep instead of highway), reaching the same reading — 100 % pinned, not
99.9 %.** That closes the last escape hatch, which was that the over-range might be regime-specific.
`M = 2·Mhi + Mlo = |gp-0x374c>>4| >> 11`, LSB 2048 counts, saturating code 3.

| route | build | frames | M histogram | engaged-only |
|---|---|---|---|---|
| **80** | V97 | 10,749 | **{0: 10,749}** | {0: 1,719} |
| 7e | V96 | 80,462 | {0: 80,385, **1: 77**} | {0: 61,429, 1: 77} |
| 7f | V96 | 83,632 | {0: 83,603, **1: 29**} | {0: 68,925, 1: 29} |

⇒ `|gp-0x374c>>4| < 2048` on **100 % of route 80** and on **99.90 % / 99.97 %** of V96's own two
flights. `Mhi` is **0 everywhere on all three routes**; the saturation duty that
`build_v96_tva.py` made "a first-class reported output" is **0.0000**.

**This is the GATE, not the hypothesis, and it is the instrument's own sizing.** The cell is not
dead: `sign(gp-0x374c) < 0` has duty **0.3672** (route 80) / 0.4445 (7e) / 0.4129 (7f), so the
signal is nonzero and changes sign constantly. What failed is the **magnitude quantiser**: sized
off a structural upper bound of ~68,600 counts, it put its first LSB at 2,048, and the real signal
lives entirely inside that first LSB. **V96's `f′` slope measurement — the entire stated purpose of
the V96 build — has no magnitude leverage on any route flown.** Same failure class as the
`gp-0x6b98` "1.5-bit comparator", in the opposite direction.

⊕ This does not retract the handoff's `f′` conclusion, which was closed **structurally in Ghidra**
(`f′ ≥ 0` enforced at three ungated sites), not from this probe.

---

## 4. THE DECISIVE MEASUREMENT — the pole's phase

### 4.1 Sign convention, stated and self-checked
`angle(scipy.signal.csd(x, y)) = arg(Y) − arg(X)`; **positive ⇒ y LEADS x**. Self-check: y = x
delayed 5 samples at 100 Hz ⇒ measured **−140.22°**, expected **−140.22°** — asserted in code, the
run dies if it fails.

### 4.2 What the pole predicts (integer recursion mirrored)
`gp-0x374c += ((target − gp-0x374c) × A) >> 10` at 1 kHz ⇒ `H(z) = a/(1 − (1−a)z⁻¹)`, `a = A/1024`.

| f | arg H, A=102 | arg H, A=150 | V97 − V96 |
|---|---|---|---|
| 6.00 Hz | −18.70° | −12.34° | **+6.37°** |
| **7.79 Hz** | **−23.63°** | **−15.81°** | **+7.82°** |
| 9.00 Hz | −26.73° | −18.07° | +8.66° |
| 21.00 Hz | −47.79° | −36.12° | +11.68° |

Reproduces the handoff's +7.82°. 🛑 `gp-0x374c` enters `gp-0x6b70` only through the
`−(gp-0x374c>>4)` term of `iVar6`, so **+7.82° is an UPPER BOUND** on what can appear on the 427
lane; the observable is diluted by that term's share.

### 4.3 Measured — 0x18F torque → 427 lane, 6–9 Hz, matched cells
2.56 s windows, Welch nperseg 32 (50 Hz), control = phase against the **time-reversed** torque
trace (destroys causality, preserves the spectrum).

| cell (speed × \|rate\|) | route | win / eps | phase | window-boot CI | coh | CONTROL phase / coh |
|---|---|---|---|---|---|---|
| 0–7 km/h × 5–20 °/s | **r80 (V97)** | 7 / **1** | **+38.64°** | [+35.44, +41.59] | 0.960 | +8.73° / 0.433 |
| | r7f (V96) | 2 / 2 | +35.37° | [+23.13, +47.62] | 0.974 | +4.16° / 0.049 |
| 0–7 km/h × 20–60 °/s | **r80 (V97)** | 4 / **1** | **+38.51°** | [+34.93, +42.08] | 0.971 | −154.12° / 0.395 |
| | r7e (V96) | 2 / 1 | +42.59° | [+41.04, +44.14] | 0.939 | +6.89° / 0.513 |

**Contrast V97 − V96: +3.27° in one cell, −4.08° in the other — OPPOSITE SIGNS, both smaller than
the +7.82° upper-bound prediction.**

🛑 **These CIs are WINDOW bootstraps and are therefore not admissible as evidence** — every arm has
1–2 episodes, so the between-episode variance is unestimable. Quoted only to show scale. Taking
them at face value gives CI fold-widths of **3.9×** and **1.3×** against the prediction.

⚠ A first pass (`v97_r80_phase.py`) reported coherence 1.000 across the board — an artefact of
`nperseg == len(window)`, i.e. a single Welch segment. Fixed in `v97_r80_matched.py`; the numbers
above carry ≥ 6 averages and a control that separates (control coherence 0.05–0.51 vs 0.94–0.97).

⚠ CAN-join bias: the 427 magnitude is 50 Hz, its sign bit is on `0x14A` at 100 Hz. De-rectifying
carries up to 10 ms of alignment error = **28° at 7.79 Hz**, 3.6× the effect. It is a route-level
constant only if the CAN cadence phase is stable, in which case it cancels in a build-to-build
difference — **not assumed**.

**VERDICT on §4: the predicted +7.82° lead is NOT RESOLVED by route 80. Not refuted — unmeasurable
with this exposure.**

---

## 5. BANDS — and the control kills the comparison

### 5.1 There is barely a matched regime at all
Engaged exposure, seconds, in the joint (speed × wheel-rate) grid — **r80 / r7e / r7f**:

| speed | 0–5 °/s | 5–20 °/s | 20–60 °/s | 60+ °/s |
|---|---|---|---|---|
| **0–7 km/h** | 4.4 / 12.9 / 6.9 | **5.6 / 4.4 / 2.1** | **5.4 / 2.0 / 0.4** | 1.8 / 3.1 / 2.6 |
| 7–15 | 0.0 / 20.9 / 25.0 | 0.0 / 23.4 / 13.8 | 0.0 / 20.9 / 10.0 | 0.0 / 11.7 / 6.2 |
| 15–30 | 0.0 / 23.9 / 66.1 | 0.0 / 17.6 / 19.9 | 0.0 / 18.8 / 11.3 | 0.0 / 9.7 / 9.0 |
| 30–60 | 0.0 / 158.7 / 258.6 | 0.0 / 25.2 / 39.2 | 0.0 / 5.9 / 9.7 | 0.0 / 0.2 / 0.9 |
| 60–200 | 0.0 / 236.5 / 194.4 | 0.0 / 18.2 / 12.8 | 0.0 / 1.2 / 0.6 | 0.0 / 0.0 / 0.0 |

Route 80 has **zero engaged exposure above 7 km/h**. The matched cells carry **~5 s per arm.**

🛑 **A methodological correction inside this session:** at 5.12 s windows this analysis reported
**zero matched cells**, and that would have been reported as "no comparison is possible". A
frame-level second method showed ~5 s of matched exposure on both sides — **the window length, not
the data, produced the null.** Recorded because it is exactly the kit's own failure mode.

### 5.2 🛑 SPLIT-HALF NULL — run BEFORE the ratio, and it destroys it
Cell: engaged, speed < 7 km/h, median |rate| ≥ 5 °/s, 2.56 s windows. Each arm split
first-half / second-half — the same statistic with the **build held fixed**.

| arm | 6–9 Hz | 15–22 Hz | 18–28 Hz | n win |
|---|---|---|---|---|
| r80 (V97) | **1.07×** | 0.95× | 0.96× | 11 |
| r7e (V96) | **6.98×** | 1.45× | 1.26× | 3 |
| r7f (V96) | **1.74×** | 1.39× | 1.76× | 4 |

**Cross-build ratio in the same cell** (r80 / V96 pooled): 6–9 Hz **5.92×** · 15–22 Hz **2.26×** ·
18–28 Hz **2.30×**, on 11 vs 7 windows and **1 vs 2 thirty-second episode blocks**.

⇒ **The 6–9 Hz cross-build ratio (5.92×) is SMALLER than r7e's own split-half noise ratio
(6.98×).** The comparison carries no information. Same conclusion at 15–22 and 18–28 Hz, where the
cross-build 2.26×/2.30× sits alongside within-arm noise of 1.26–1.76×.

### 5.3 Raw per-cell medians, for the record only
| cell | route | 6–9 | 15–22 | 18–28 | 26–31 |
|---|---|---|---|---|---|
| 0–7 km/h × 5–20 °/s | r80 (V97) | 368.22 | 76.12 | 83.59 | 14.72 |
| | r7f (V96) | 99.88 | 47.96 | 41.95 | 6.83 |
| 0–7 km/h × 20–60 °/s | r80 (V97) | 381.71 | 149.43 | 143.70 | 18.06 |
| | r7e (V96) | 341.71 | 105.18 | 90.00 | 10.87 |

In the better-matched (20–60 °/s) cell the 6–9 Hz ratio is **1.12×**. In the 5–20 °/s cell it is
**3.69×**. Two cells, a 3.3× disagreement, on ~5 s per arm. **Excitation, not build.**

---

## 5b. THE `427 == 1023` FLAG — measured, and it is a clean zero on all three routes

Scorer: `rlog-tools/v97_r80_override_and_1023.py` → `_cache_r80/r80_override_and_1023.json`.

The claim (TelemetryDesign's decompile, carried as their EVIDENCE — I did **not** re-verify the
`bnc` at `0x38234` in Ghidra): when `|gp-0x6bfe| > 20000` the observer's plausibility check fails,
`gp-0x6b70` is forced to **32767** and the ±8192 clamp is bypassed ⇒ wire `32767·5>>6 = 2559` →
clamped to **1023**.

⊕ **I verified the ceiling independently**, from `build_v96_tva.py:128`'s own no-clip proof: the
plausible branch's maximum wire is `8192·5>>6 = 640`. So the flag is **stronger than "== 1023":
any wire > 640 is arithmetically unreachable through the plausible branch.** Both are scored.

| route | build | 427 frames | wire max | top-5 codes | `== 1023` | `> 640` |
|---|---|---|---|---|---|---|
| **80** | V97 | 5,375 | **249** | 245–249 | **0 (duty 0.000000)** | **0** |
| 7e | V96 | 40,233 | 275 | 266–275 | **0** | **0** |
| 7f | V96 | 41,815 | 266 | 262–266 | **0** | **0** |

**Zero on 87,423 frames across three routes** — engaged and manual, hands-on and hands-off.
**The observer's plausibility branch never fired**, including throughout the operator's deliberate
elicitation. That is a genuine measurement, not an absence of data: the branch is on the wire, it
is single-frame detectable, and it read false every frame.

⇒ **My §3.1 "0.000 % saturation" reading is CONFIRMED and now correctly interpreted.** It is not
merely "no clipping" — it is "`gp-0x6b70` never left the plausible branch". The highest wire seen,
249, is **38.9 % of the plausible ceiling 640** and corresponds to \|gp-0x6b70\| = 3,187 counts.

---

## 5c. THE REGIME SPLIT — route 80 is NOT override-dominated

Mask: `STATE.md` §A2's own — hands-on ≡ `|0x18F STEER_TORQUE_SENSOR| > 1200`, and
**engaged + hands-on ≡ OVERRIDE by definition**.

| route | build | engaged | **OVERRIDE (hands-ON)** | hands-OFF | hands-off eps ≥1 s | longest |
|---|---|---|---|---|---|---|
| **80** | V97 | 17.2 s | **3.4 s (19.5 %)** | 13.8 s | 4 | **2.42 s** |
| 7e | V96 | 615.1 s | 39.2 s (6.4 %) | 575.8 s | 33 | 196.28 s |
| 7f | V96 | 689.5 s | 39.2 s (5.7 %) | 650.3 s | 37 | 126.36 s |

Cross-checked against openpilot's own `carState.steeringPressed`: engaged duty 0.1966 / 0.0638 /
0.0568, agreeing with the `|tq| > 1200` mask on **93.1 % / 99.5 % / 99.6 %** of engaged frames.

🛑 **This partly corrects the premise it was asked against.** Route 80 is **~3× enriched in
override** relative to V96's routes (19.5 % vs 6.4/5.7 %) — the operator's elicitation strategy is
visible in the data — but it is **not ~100 % hands-on**. Four fifths of its engaged time is
hands-off. The problem is not that route 80 is in the wrong regime for the `Q` estimator; it is
that **route 80 has almost no exposure in EITHER regime**: 3.4 s of override and 13.8 s of
hands-off, the latter in fragments whose longest is 2.42 s.

**Can the `Q` / return estimator run on route 80? No.**

| route | engaged + hands-off episodes ≥ 2 s | of which decaying-angle RETURNS |
|---|---|---|
| **80** | **1** | **1** |
| 7e | 24 | 14 |
| 7f | 27 | 11 |

**One return.** The `|Q| = 1.233` result that set V97's direction rests on 25 returns across 7e/7f.
⇒ **Not testable on route 80** — the honest output, rather than a low-confidence number.

---

## 5d. THE LAST CHANNEL WITH LEVERAGE — `sign(gp-0x374c)` — TESTED, AND IT FAILS ITS CONTROL

`Mhi`/`Mlo` are pinned (§3.2), so the only telemetered cell whose *dynamics* the pole touches is
the **1-bit sign of the LPF output** at 100 Hz. A faster pole (A = 150) passes more HF, so its
zero-crossing rate should rise. Matched cell as §5.2; statistic = sign transitions per second.

| arm | n win | median /s | IQR | **split-half** |
|---|---|---|---|---|
| r80 (V97) | 11 | 9.80 | [8.04, 10.39] | 0.94× |
| r7e (V96) | 3 | 8.24 | [4.31, 10.00] | **25.50×** |
| r7f (V96) | 4 | 0.59 | [0.39, 1.37] | 0.20× |

Cross-build r80 / V96 pooled = **12.50×** — but:
- **r7e's own split-half noise is 25.50×**, twice the cross-build effect;
- **the two V96 routes disagree with EACH OTHER by 14×** (8.24 vs 0.59) on the same build;
- and the **control bit** `sign(gp-0x6b70)` — whose bandwidth the pole does not set — moves
  **2.06×** cross-build, with r7e vs r7f disagreeing 3.8× (12.55 vs 3.33).

⇒ **The statistic is dominated by regime, not by build. Null.** This is the fourth control in this
scoring to kill the measurement it was run against.

---

## 6. WHAT THIS ROUTE CAN AND CANNOT SUPPORT

**CAN (EVIDENCE):**
1. Route 80 runs the V96-family instrument; V94/V92/≤V91 are excluded.
2. No faults: STEER_STATUS never left 0 except 9 frames (same as 7e/7f); OUTPUT_DISABLED duty
   0.0009; 0 sentinels.
3. The 427 lane carrying `gp-0x6b70` is a good instrument — 98.29 % nonzero, 0 % saturated,
   p99 at 37 % of clamp.
4. The V96/V97 regressor probe's magnitude channel is **structurally under-ranged on every route
   ever flown with it**, including V96's own two.
5. The base-assist damper product was zero on 100 % of the drive.

### 6.0 🛑 THE NET QUESTION — *"is there any measurement on route 80 that can distinguish 'the pole moved and the car did not care' from 'the pole did not move'?"*

# NO.

Four independent channels, each closed by a different mechanism:

| channel | why it cannot answer | grade |
|---|---|---|
| **Any static / single-frame test** | V96 and V97 differ in **5 bytes: one cal byte + CRC**. The cave, the 427 repoint, the packer and every CAN map are identical. No frame can carry the difference. | EVIDENCE (image byte-diff) |
| **The cave's regressor** — the cell the pole directly filters | `M` pinned at 0 on **100 %** of route 80, and `Mlo` duty **exactly 0.0000** (vs 77 / 29 firings on 7e / 7f). Zero residual leverage — the one bit that occasionally fired on V96's routes never fired here. **Known void before the drive:** `build_v97_tva.py:99-100` concedes it in the build script itself. | EVIDENCE |
| **The 427 lane's phase** — the diluted downstream observable | Prediction +7.82° (an upper bound). Measured contrast **+3.27° and −4.08° in two cells, opposite signs**, on 1–2 episodes per arm; ±28° CAN-join on top. The `Q` estimator that set the direction needs hands-off returns: route 80 has **1**, against 25 on 7e/7f. | EVIDENCE |
| **`sign(gp-0x374c)` zero-crossing rate** — the last dynamic channel | Cross-build 12.50× sits **inside** r7e's own 25.50× split-half noise; the two V96 routes disagree with each other by 14×; the control bit moves 2.06×. | EVIDENCE (§5d) |

**Therefore V97 is UNSCORED, not falsified.** The operator's *"zero difference from V96"* is a real
and important report about how the car feels — but route 80 contains **no instrument capable of
telling him whether the byte he flashed did anything at all.** That is a statement about the
instrument and the exposure, not about the lever.

**CANNOT:**
1. Separate V97 from V96 — not single-frame (structurally impossible), and not by phase either
   (§4.3: opposite signs across two cells, ~5 s per arm).
2. Score any symptom band. The split-half control exceeds the cross-build effect (§5.2).
3. Say anything about highway or 15–60 km/h behaviour: **zero engaged exposure above 7 km/h.**

**WHAT THE NEXT DRIVE NEEDS, if V96-vs-V97 is to be settled:** matched **engaged** exposure at the
*same* speed and wheel rate on both builds, many episodes each — the binding constraint is
**episode count**, not window count. For the pole specifically, ~7.8° at 6–9 Hz against a per-window
phase scatter of ±10–15° needs on the order of 50+ independent episodes per arm, or a probe that
does not go through the ±28° CAN join.

**AND, independently of any drive: `0xC63AC`'s effect is invisible to the instrument that is
supposed to see it.** The regressor channel needs re-sizing — **already the record's own standing
recommendation** (`STATE.md` §A5: LSB 2048 → 128–256). Route 80 removes the "it might be
regime-specific" caveat: |gp-0x374c>>4| < 2048 now holds on **three routes across highway and
creep**, 100 % pinned on the creep route.
