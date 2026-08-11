# SCORING 2026-08-11 — V90 flight (route `77`), and the cross-build K1 question

**Build on the car: V90**, flown as route `00000077--7411859c54`, 21 segments, 1245.3 s, fault-free.
**V90 is PROBE-ONLY — byte-identical to V89 in every calibration cell.** It adds four telemetry bits
on CAN `0x14A` byte 4 and repoints CAN `0x1AB` (427) `MOTOR_TORQUE` to `gp-0x6b26`.

**The operator's report on this drive, in his words:** *grind #1 still exists · micro-ratcheting still
exists · grind #2 can be felt on the highway-speed curves or lane changes · parking lot testing ·
highway and street level testing.*
🛑 **Nothing in this document is called fixed. No band result is presented as a symptom result.**

| artefact | path |
|---|---|
| extractor | `rlog-tools/extract_r77.py` → `analysis-2020accord/_cache_r77/` |
| scorer | `rlog-tools/decode_v90_probe.py` (`d1` `d3` `d4` `d5` `d6` `d6b`) |
| logs | `rlog-tools/{extract_r77,d1_v90,d3_v90,d4_v90,d5_v90,d6_v90,d6b_v90}.log` |
| JSON | `analysis-2020accord/_cache_r77/v90_d{1,3,4,5,6,6b}_*.json` |

---

## 0. HEADLINE

1. **IDENTITY PASS — V90 is on the car.** `b4 == 0` on 124,362/124,362 frames; impossible on
   V86B/V87/V88/V89. Parameter-free, single-frame.
2. **`gp-0x6b26` MEASURED FOR THE FIRST TIME ON ANY BUILD.** Engaged p50 5.5 / p99 114.3 / **max
   319.1** counts against the ±511 clamp. **Clamp duty EXACTLY ZERO in every stratum.** The lane is
   **not** a relay today. Clipping headroom: **1.60× never pins · 2.75× keeps pinning <0.1 % · 4.45× <1 %.**
🛑 **These are CLIPPING numbers, not a dose budget.** The binding constraint is an **int32 wraparound
upstream of the clamp at ≈1.6005×** (§10.2) — **2.75× would WRAP, not pin.**
3. **THE OBSERVER GATE NEVER FAILS** — `gp-0x6c00 < 0` on **0** of 124,362 frames, 20.49 minutes,
   engaged and manual, every wheel-rate bin.
4. **NO EVIDENCE THAT V89's K1 = 204 REGRESSED THE GRINDING.** `e_18-22` V89(+V90) ÷ V88, on three
   strata, all ≤ 1.03 and all **FLAT** against their own constant-build placebo bands.
5. **`Re(Z) < 0` ACROSS 2–16 Hz REPLICATED** on 221 windows / 884.5 s (V89 had 6). Re(Z) = **−3375
   ct·s/rad at 6–9 Hz** (V89: ≈ −3300). Inertia refuted again — phase −125° to −152°, never near +90°.
6. **The manual hands-off control STILL DOES NOT EXIST**: 2 qualifying windows on route 77. The
   deliberate hands-off coast remains the only new driving that would buy anything.
7. 🛑 **"THE FIRMWARE CANNOT SEE THE 6–9 Hz MODE" IS REFUTED** (§7). The motor rate tracks the column
   at 6–9 Hz exactly as well as at 2–4 Hz (`R = 1.016`), with the highest coherence of any low band
   (0.438 vs a shuffled 0.001). **The damping lane goes back in play for the ratchet** — it has 2.3×
   less authority per °/s there than at 15–22 Hz, not zero. What *is* attenuated toward the motor is
   the narrow 7.8 Hz **line**, not the band.
8. 🛑 **THE LOAD AXIS DOES NOT CARRY GRIND #2 — it carries it with the OPPOSITE SIGN** (§6c), and the
   ratchet and grind #2 dissociate on both load and speed. **No evidence that one lever touches both.**
9. 🛑 **`Re(Z)` EXTENDED TO 35 Hz (§4.1a): D DAMPS 16–35 Hz** ⇒ **the `Kd` cut is CLOSED** — it would
   buy +0.077 at the ratchet and pay −0.217 and −0.336 in the operator's own two grinding bands.
   ⊕ `Re(Z)` **flips sign at ~26 Hz**: anti-damped 2–26 Hz, **damped 26–35 Hz** ⇒ grind #2's band is
   not anti-damped at all, corroborating D6c's dissociation from a second, unrelated instrument.
10. 🛑🛑 **THE ANTI-DAMPING IS NOT THE PID (§4.1c).** At 6–9 Hz the PID's terms sum to a **net damper**
    (−0.121) while `Re(Z)` reads **−3375**. **The session's biggest open question, and every remaining
    firmware candidate has to answer it.**
11. 🛑 **A CHANNEL TRAP THAT INVERTS ANSWERS (§4.1b):** using the `0x14A` rate instead of the
    `0x18F` rate flips 26–31 Hz from **−0.336 DAMPING** to **+0.184 PUMPING** at identical coherence —
    the opposite build decision from the same data.

---

## 1. D2 — IDENTITY AND PROBE HEALTH

### 1.1 Identity — EVIDENCE, single-frame, parameter-free
`field = (byte4 >> 3) & 0x1F` histogram over 124,362 frames:

```
   1: 20,470    5: 23,291    9:    330   13: 15,098
  17: 25,990   21: 23,997   25:    365   29: 14,821
```
**All eight values are in the V90-ONLY set. Zero frames in the pre-V90 alphabet `{3,7,15,23,31}`.**
Map validator: every value ODD ⇒ `b3 ≡ 1` holds, **zero even values** ⇒ the field is being read at the
right bit offset and the cave ran on every frame.

### 1.2 Rung health
| rung | signal | all | engaged | manual | interpretable? |
|---|---|---|---|---|---|
| b7 `0x80` | `gp-0x6b26 < 0` | 0.5241 | 0.5220 | 0.5370 | ✔ (~0.50 by construction) |
| b6 `0x40` | `\|gp-0x6bf6\| ≥ 512` | 0.2462 | 0.2535 | 0.1998 | ✔ **the guessed threshold landed inside its predicted 0.10–0.50 — do NOT move `0xC4B4A`** |
| b5 `0x20` | `gp-0x6ae2 ≠ 0` | 0.6208 | 0.6752 | 0.2751 | ✔ |
| b4 `0x10` | `gp-0x6c00 < 0` | **0.0000** | 0.0000 | 0.0000 | railed — **and for a gate question 0.000 IS the answer** |
| b3 `0x08` | fingerprint | 1.0000 | — | — | by construction |

Rate dependence, engaged, by `|wheel rate|` (0–0.35 / 0.35–1 / 1–3 / 3–6 / 6–13 / 13–25 / 25–50 / 50+ °/s):
```
b6  0.057  0.231  0.154  0.140  0.314  0.466  0.543  0.851
b5  0.245  0.780  0.731  0.777  0.960  0.994  0.999  1.000
b7  0.557  0.457  0.523  0.519  0.503  0.494  0.488  0.483
b4  0.000  0.000  0.000  0.000  0.000  0.000  0.000  0.000
```

### 1.3 Exposure and health
- **Engaged 1074.6 s (17.91 min, 86.41 %)**; ≥50 km/h **316.4 s**; ≥80 km/h **42.0 s**; max 90.4 km/h.
- **Micro-ratcheting regime (1–13 °/s) 437.6 s · ratcheting (13–50 °/s) 196.0 s · macro (>50) 76.7 s.**
- 9 engagement episodes, all ≥ 10 s, longest 276.8 s. Manual 169.0 s, of which 67.7 % parked.
- `STEER_STATUS` {0: 124,358, 3: 3} — same shape as r73/r75/r76. **DTC-active duty 0.000000, 0
  transitions. 0 sentinels** on both `0x14A` and `0x18F`. `CONFIG_VALID` 1.0000, `OUTPUT_DISABLED`
  0.00002. **No EPS entry in 3,489 `onroadEvents`.**
- 427: 62,180 frames at 49.81 Hz, src 1, DLC 3, COUNTER +1 on 100.00 %, CHECKSUM 16/16 distinct.

---

## 2. D3 — THE `gp-0x6b26` DISTRIBUTION (the deliverable V90 was built for)

**Inverting the packer exactly.** `wire = clamp(|x|·5 >> 3, 0, 0x3FF)`, i.e. `wire = floor(|x|·5/8)`,
so `|x| ∈ [8w/5, (8w+7)/5]` — a 1.4-count bracket; the midpoint estimator `(8w+3.5)/5` errs ≤ 0.7 ct.
Observed wire range **[0, 199]**, **wire saturation 0.000000** ⇒ every sample is an honest measurement.
Sign from b7 at 100 Hz, paired **nearest 0x14A within 10 ms on 99.813 %** of 427 frames.

### 2.1 The distribution, counts

| stratum | n | p50 | p75 | p90 | p95 | p99 | p99.9 | max | clamp duty |
|---|---|---|---|---|---|---|---|---|---|
| **ENGAGED** | 53,630 | 5.5 | 16.7 | 39.1 | 58.3 | 114.3 | 184.7 | **319.1** | **0.000000** |
| MANUAL all | 8,434 | 2.3 | 7.1 | 13.5 | 19.9 | 41.8 | 81.1 | 104.7 | 0.000000 |
| MANUAL moving >0.5 m/s | 2,475 | 5.5 | 13.5 | 23.1 | 31.1 | 56.7 | 91.2 | 104.7 | 0.000000 |
| engaged, <1 °/s | 18,169 | 2.3 | 3.9 | 7.1 | 10.3 | 25.2 | 89.8 | 128.7 | 0.000000 |
| engaged, micro 1–13 °/s | 21,933 | 7.1 | 16.7 | 35.9 | 55.1 | 96.7 | 157.6 | 303.1 | 0.000000 |
| engaged, ratchet 13–50 °/s | 9,740 | 19.9 | 42.3 | 74.3 | 101.5 | 159.1 | 234.4 | **319.1** | 0.000000 |
| engaged, macro ≥50 °/s | 3,788 | 11.9 | 23.1 | 40.7 | 56.7 | 101.7 | 183.5 | 274.3 | 0.000000 |
| engaged, 5–20 km/h | 12,867 | 13.5 | 31.1 | 66.3 | 98.3 | 155.9 | 217.3 | 319.1 | 0.000000 |
| engaged, ≥80 km/h | 2,101 | 2.3 | 8.7 | 21.5 | 37.5 | 61.5 | 94.9 | 106.3 | 0.000000 |

### 2.2 🛑 Pinning duty vs gain multiplier — `P(|gp-0x6b26|·m ≥ 511)`

| stratum | m=1.0 | 1.25 | 1.5 | 2.0 | 2.5 | 3.0 | 4.0 |
|---|---|---|---|---|---|---|---|
| ENGAGED | 0 | 0 | 0 | 0.000131 | 0.000485 | 0.001529 | 0.007403 |
| micro 1–13 °/s | 0 | 0 | 0 | 0.000046 | 0.000046 | 0.000502 | 0.004195 |
| **ratchet 13–50 °/s** | 0 | 0 | 0 | 0.000513 | 0.002361 | **0.006674** | **0.028850** |
| **5–20 km/h** | 0 | 0 | 0 | 0.000233 | 0.001632 | 0.005363 | 0.026968 |
| 20–50 km/h | 0 | 0 | 0 | 0.000126 | 0.000168 | 0.000419 | 0.001466 |
| ≥80 km/h | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**largest m never pinning 1.60× · pinning <0.1 % up to 2.75× · pinning <1 % up to 4.45×.**

🛑 **DO NOT READ THIS AS A DOSE BUDGET — it is a CLIPPING ladder only.** A separate and tighter bound
governs the dose: `FUN_00036c12`'s `mul r13,r6,r0` (×0x111, high half discarded) is **unclamped and
UPSTREAM of `0xC407E`**, and int32 wraparound is structurally impossible only for a multiplier
**≤ 1.6005**. Above that the lane does not saturate gracefully — **it wraps, which is a full-scale
sign inversion delivered before the clamp meant to contain it.** See §10.2.

⚠ **OPEN-LOOP extrapolation, stated loudly.** It holds the observed distribution fixed under the dose.
In closed loop more damping *reduces* the motion driving `gp-0x6c2c`, so it over-states pinning and is
therefore **conservative** — but it is still an extrapolation. **The binding stratum is
ratchet 13–50 °/s / 5–20 km/h, not highway.**

⊕ **Lineage note with its scope stated:** `0xCBE74` ×1.5 pins **0.000000** of this drive ⇒ saturation
is not a candidate mechanism for the V74/V75 hard faults **on route 77's distribution**. Those builds
carried `0xC407E` = 850, not 511, so their clamp sat elsewhere, and route 77 is not their drive. This
**weakens** "the lane railed"; it does **not** clear the row.

### 2.3 Band content — controls first
Bands differ in width, so raw band rms is not comparable across them (white noise alone gives
rms ∝ √BW). Every row carries **density = rms/√BW** and a **within-run shuffle** as the null; the
shuffle comes out flat, which is what validates the normalisation.

**Signed reconstruction, 50 Hz (Nyquist 24.9 Hz), engaged, 303 windows:**
| band | rms (ct) | density | shuffled | meas/shuf |
|---|---|---|---|---|
| 2–4 Hz | 2.23 [1.87, 3.10] | 1.577 | 3.964 | 0.398 |
| 6–9 Hz | 2.74 [2.05, 3.69] | 1.580 | 4.019 | 0.393 |
| 9–12 Hz | 2.76 [2.32, 3.36] | 1.592 | 4.078 | 0.390 |
| **15–22 Hz** | **8.42 [6.26, 10.84]** | **3.184** | 4.035 | **0.789** |

⇒ **`gp-0x6b26` carries 2× the spectral density at 15–22 Hz that it carries at 2–4, 6–9 and 9–12 Hz,
and those three are indistinguishable from each other.** [EVIDENCE]

**b7 sign channel, 100 Hz — the only channel above 427's Nyquist. 1-bit ⇒ SPECTRAL only; amplitude
claims do not travel.** 403 windows:
| band | density | shuffled | meas/shuf |
|---|---|---|---|
| 6–9 Hz | 0.1029 | 0.1277 | **0.806** |
| 15–22 Hz | 0.1380 | 0.1296 | 1.065 |
| **26–31 Hz** | **0.1489** | 0.1270 | **1.173** |
| 32–38 Hz (control) | 0.1112 | 0.1264 | 0.880 |
| 40–49 Hz | 0.1083 | 0.1279 | 0.847 |

Ordering **26–31 > 15–22 > 32–38 ≈ 40–49 > 6–9**: the lane's sign-switching is enhanced in the two
bands the operator calls grinding and depressed in the micro-ratcheting band, against its own negative
control. [EVIDENCE for the ordering. **BELIEF** that this means the lane *drives* those bands — §4's
closed-loop caveat applies in full.]

---

## 3. D5 — THE (b6, b5) 2×2 AND THE OBSERVER GATE

### 3.1 🛑 The gate, measured for the first time: it never fails
**`gp-0x6c00 < 0` on 0 of 124,362 frames = 0.000000 %, over 20.49 minutes**, engaged and manual, in
every wheel-rate bin. The observer's success path ran on every frame of this drive.

### 3.2 The 2×2, ENGAGED, by wheel rate
| \|wheel rate\| | n | b6=0,b5=0 | b6=0,b5=1 | **b6=1,b5=0** | b6=1,b5=1 | **P(b5\|b6=1)** |
|---|---|---|---|---|---|---|
| ALL | 107,462 | 0.3185 | 0.4280 | **0.0063** | 0.2471 | 0.9751 |
| **<1 °/s** | 36,403 | 0.7327 | 0.2076 | **0.0152** | 0.0444 | **0.7447** |
| micro 1–13 | 43,898 | 0.1703 | 0.6277 | 0.0028 | 0.1992 | 0.9860 |
| ratchet 13–50 | 19,570 | 0.0040 | 0.4984 | 0.0001 | 0.4975 | 0.9999 |
| macro ≥50 | 7,591 | 0.0000 | 0.1489 | 0.0000 | 0.8511 | 1.0000 |

⇒ **The `|model|`-vs-relay confound is real but barely separable on this drive**: the discriminating
cell `(b6=1, b5=0)` is **0.63 %** of engaged frames. Above 1 °/s the relay is on essentially whenever
the model is large (P → 0.986 → 1.000): **friction and `|model|` are near-collinear in exactly the
regimes the operator names.** They decouple only **below 1 °/s, where 25.5 % of large-model frames
carry zero friction** — the Coulomb rate-gate showing up directly, a **sixth** independent
confirmation of the term's identity.

**Lever consequence:** above 1 °/s you cannot move the friction term independently of `|model|` on
this car. A K1 change in that regime is a change to a term that is a fixed function of the model —
a structural reason for V89's null, not merely an arithmetic one.

---

## 4. D4 — THE TRANSFER, AND THE CAVEAT THAT GOVERNS IT

> # 🛑 RULE FOR ALL PHASE AND IMPEDANCE WORK ON THIS CORPUS
> **Any phase or impedance estimate MUST use the `0x18F`-sourced rate (`rate_f`), and MUST state which
> rate it used.** `tq` and `rate_f` are both fields of the same held `0x18F` frame, so the skew cancels
> exactly; `rate_c` / `ang` / `wang` come from `0x14A` and carry ~9.15 ms of relative delay.
> **Using the wrong rate inverts the sign of the answer above ~16 Hz at identical coherence** — see
> §4.1b, where it flips 26–31 Hz from `−0.336 DAMPING` to `+0.184 PUMPING`.

### 4.1 `Re(Z)` — the driving-point impedance, REPLICATED with 37× V89's exposure
`Z(f) = S_Tω/S_ωω`, column torque (`0x18F`) against wheel angular velocity, engaged **hands-off**
(`steeringPressed` false) and moving, 5.06 s windows.

| band | Re(Z) ct·s/rad | \|Z\| | phase | coh² | coh² shuffled |
|---|---|---|---|---|---|
| 2–4 Hz | −1269 | 1438 | −152.0° | 0.261 | 0.001 |
| 4–6 Hz | −1419 | 1944 | −136.9° | 0.429 | 0.001 |
| **6–9 Hz** | **−3375** | 5841 | −125.3° | **0.769** | 0.004 |
| 9–12 Hz | −4593 | 5651 | −144.4° | 0.826 | 0.001 |
| 12–16 Hz | −3858 | 3864 | +176.8° | 0.628 | 0.001 |

**221 windows / 884.5 s.** `Re(Z) < 0` right across 2–16 Hz, and **−3375 at 6–9 Hz reproduces V89's
≈ −3300 on an independent drive**. Predicted phases: inertia +90°, damper 0°, spring −90°, negative
damping 180°. Measured −125° to −152°. **Inertia is refuted again.**

### 4.1a ★ EXTENDED TO 35 Hz, 2026-08-11 — `rlog-tools/v92_rez_extend.py`, log `v92_rez.log`
§4.1 stopped at 16 Hz only because those were the bands then in play. Both channels run at ~101 Hz, so
Nyquist is 50 Hz. Same estimator (the frozen `_wins`/`_band_transfer`), same 221 windows, same
shuffled control. **§4.1's own bands reproduce bit-for-bit**, which is the positive control.
**Pre-declared trust gate: coh² ≥ 0.10 AND ≥ 5× shuffled. All ten bands pass.**

| band | Re(Z) | \|Z\| | **phase** | coh² | shuf | vetoed n / phase / coh² |
|---|---|---|---|---|---|---|
| 16–18 | −1610.7 | 1941.7 | **+146.1°** | 0.550 | 0.003 | 89 / +136.0° / 0.538 |
| **18–22** | −652.5 | 1296.1 | **+120.2°** | **0.745** | 0.000 | 46 / **+113.5°** / **0.889** |
| 22–26 | −267.8 | 987.5 | **+105.7°** | 0.739 | 0.000 | 77 / +108.8° / 0.839 |
| **26–31** | **+232.9** | 667.1 | **+69.6°** | **0.834** | 0.002 | 85 / **+57.8°** / 0.627 |
| 31–35 | **+772.9** | 900.9 | **+30.9°** | 0.497 | 0.000 | 95 / +31.7° / 0.609 |

⊕ **`Re(Z)` flips sign between 22–26 and 26–31**: the column is **anti-damped 2–26 Hz and positively
damped 26–35 Hz.** The two decision bands carry the **highest coherence in the sweep.**

**D-term dissipative products** (`|H_D(f)| × (−sin φ)`; `|H_D|` is the D-sweep's quantity, not mine —
its 18–22 and 26–31 values are as given, the rest interpolated and flagged):
| band | \|H_D\| | −sin φ | **D product** | vetoed | vs the +0.076 pump at 6–9 |
|---|---|---|---|---|---|
| 6–9 | 0.094 | +0.816 | **+0.077 PUMP** | +0.073 | — |
| 16–18 | 0.213 *(interp)* | −0.558 | −0.119 DAMP | −0.148 | 1.6× |
| **18–22** | **0.251** | −0.864 | **−0.217 DAMP** | −0.230 | **2.9×** |
| 22–26 | 0.301 *(interp)* | −0.963 | −0.290 DAMP | −0.285 | 3.8× |
| **26–31** | **0.358** | −0.937 | **−0.336 DAMP** | −0.303 | **4.4×** |
| 31–35 | 0.415 *(interp)* | −0.514 | −0.213 DAMP | −0.218 | 2.8× |

⇒ **D pumps ONLY 2–12 Hz and DAMPS everything from 16 to 35 Hz.** Removing the +0.077 pump at the
ratchet costs **−0.217 at 18–22 (grind #1) and −0.336 at 26–31 (grind #2)**. **Cutting `Kd` is a
TRADE, and the cost is 3–4× the benefit, in the two bands the operator actually complains about.**

### 🛑🛑 4.1b THE CHANNEL CHOICE FLIPS THE ANSWER — and it is why §4.1 was trustworthy all along
The `0x18F`/`0x14A` skew does **not** limit these phases, because **`tq` and `rate_f` are BOTH fields
of the same held `0x18F` frame** (`last18[0]` and `last18[1]` in the extractor) ⇒ the staleness is
common to numerator and denominator and **cancels exactly** in `Z = S_Tω/S_ωω`.
**Proved, not asserted:** recomputing Z with `rate_c` (the `0x14A` rate) separates the phase by
exactly the 9.15 ms skew — −11.1° vs −9.9° predicted at 3 Hz, −100.1° vs −93.9° at 28.5 Hz, −116.6°
vs −108.7° at 33 Hz.

> **Had `rate_c` been used, 26–31 Hz would read −30.3° instead of +69.6°, giving `+0.184 PUMPING`
> instead of `−0.336 DAMPING` — the opposite build decision, from the same data, at the same
> coherence (0.827 vs 0.834). Same flip at 18–22 (+45.8° ⇒ +0.180 PUMPING).**

⇒ **Any phase work on this corpus must use the `0x18F`-sourced rate, and must state which rate it
used.**

### 🛑🛑 4.1c THE ANTI-DAMPING IS **NOT** COMING FROM THE PID — the session's biggest open question

🛑 **Two opposite sign conventions are in play and confusing them would invert this. Both are stated:**
- **Per-term dissipative products** (the D-sweep's convention): **negative = damping**, positive = pumping.
- **`Re(Z)`** (this document's convention): **positive = damping**, negative = anti-damping.
Predicted phases: inertia +90°, damper 0°, spring −90°, negative damping 180°.

At **6–9 Hz** the PID's own terms sum to:
```
   P  −0.145      I  −0.053      D  +0.077        =>   NET  −0.121   ==  DAMPING
```
**Yet the measured `Re(Z)` at 6–9 Hz is −3375 ct·s/rad ⇒ ANTI-DAMPING**, at coherence 0.769 against a
shuffled 0.001.

> ⇒ **The PID is a net DAMPER at the ratchet frequency, and the column is anti-damped anyway.
> The anti-damping is NOT coming from `FUN_0003a382`.** It is another aggregator lane, or the plant
> itself. **[EVIDENCE for both halves; BELIEF as to which alternative.]**

**Every remaining firmware candidate has to answer this**, and it reframes the search: a lever that
trims a PID term is trimming something that is already on the damping side of the ledger.

⊕ **And the sign flip corroborates D6c independently.** `Re(Z)` is **negative (anti-damped) 2–26 Hz**
and **positive (damped) 26–35 Hz** ⇒ **grind #2's band is not anti-damped at all**, so it is
mechanically a different phenomenon from the stuttering. **That is the same conclusion D6c reached from
the covariates** (opposite signs on both the load and the speed axes) — **two unrelated instruments,
same answer.**

---

⚠ **THE CONTROL STILL DOES NOT EXIST. `MANUAL hands-off moving` = 2 windows / 21.4 s** on route 77
(V89 had 6/1/0). ⇒ **these logs still cannot separate "the EPS loop is anti-damped" from "the column
is anti-damped."** The deliberate hands-off coast is still the only driving that would settle it.

⊕ **A hint, flagged as underpowered:** `ENGAGED hands-ON moving` (11 windows) reads Re(Z) **+441** at
2–4 Hz and **+1214** at 4–6 Hz, ≈ **+11** at 6–9 Hz, turning negative only at 9–16 Hz — i.e. the
driver's grip appears to restore positive damping. **coh² 0.023–0.228 against a shuffled 0.006–0.035,
so 6–9 Hz in particular is uninterpretable.** Consistent with the corpus's grip finding; not evidence
for it.

### 4.2 The `b26 → column` transfer — and the control that separates feedthrough from causation
🛑 **`gp-0x6b26` is derived from motor rate, which is caused by column motion. This is a closed loop;
a naive transfer is feedthrough.** Three controls: shuffled pairs, the manual arm, and the
**group-delay sign** — forward causation *requires* the response to lag the input, so a **negative
group delay is positive proof of feedthrough**.

**ENGAGED, 303 windows, 50 Hz grid:**
| band | \|tq/b26\| ct/ct | phase | coh² | coh² shuf | group delay | verdict |
|---|---|---|---|---|---|---|
| 2–4 | 2.54 | +161.9° | 0.031 | 0.001 | **−149.9 ms** | feedthrough |
| 4–6 | 2.90 | +148.5° | 0.068 | 0.000 | **−82.5 ms** | feedthrough |
| **6–9** | **17.76** | +131.8° | **0.289** | 0.000 | **−48.8 ms** | 🛑 **FEEDTHROUGH — disqualified for sizing** |
| 9–12 | 5.22 | +90.4° | 0.066 | 0.000 | −23.9 ms | feedthrough |
| 12–16 | 2.43 | +9.0° | 0.071 | 0.000 | −1.8 ms | ≈0, uninformative |
| **15–22** | **2.64** | −42.1° | **0.333** | 0.000 | **+6.3 ms** | **passes the one-sided screen** |

**MANUAL moving: 8 windows, coh² 0.020–0.188 against a shuffled 0.013–0.032 ⇒ no usable control arm.**

⇒ **The answer to "separate them or say you cannot" is: the group-delay control DID separate them,
band by band.** The large 6–9 Hz "gain" of 17.8 ct/ct is feedthrough — the column *leads* `gp-0x6b26`
by 48.8 ms — and must not be used to size a dose. **The only band that survives is 15–22 Hz:
`|column torque / gp-0x6b26| ≈ 2.64 ct/ct`, phase −42.1°, coh² 0.333 vs shuffled 0.000, group delay
+6.3 ms.** [EVIDENCE for the numbers. **BELIEF** that 2.64 is a plant gain — it is a closed-loop
correlation that merely failed to be disproved by a one-sided test.]

⊕ It is a coincidence worth noting, and only that: 15–22 Hz is also where D3 finds the lane's own
energy concentrated.

---

## 5. D1 — DID V89's K1 (`0xC40D2` 102 → 204) REGRESS THE GRINDING? **No evidence that it did.**

Estimator: the corpus's own — `_grind2_lib.wrecs` (NFFT 256 / hop 128, p99 analytic band envelope,
~10.2 s `blk` units) and `v89_e3_contrast.boot_contrast` (cell-stratified log-ratios over
(eng, SPEED bin, EFFORT bin, RATE bin) — **speed- and rate-matching is built into the estimator**).
Controls, run first: per-arm split-half nulls; the pre-declared 32–38 Hz negative control differenced
on the **same** resampled episodes; `e_10-16` as an extra no-hypothesis placebo band; and the
**placebo-pair null** (random disjoint SEGMENT partitions of a constant-build pool).

### 5.1 `e_18-22` (the operator's grinding band), V89 ÷ V88 and V89+V90 ÷ V88

| stratum | arm | windows | ep | cells | ratio | contrast | placebo band | verdict |
|---|---|---|---|---|---|---|---|---|
| all engaged | V89 | 915/325 | 32/13 | 9 | 0.922 [0.530, 1.380] | 0.961 | [0.799, 1.241] | **FLAT** 0.35σ |
| all engaged | **V89+V90** | **1707/325** | **61/13** | 13 | **0.972 [0.688, 1.343]** | 0.854 | [0.845, 1.221] | **FLAT** 1.75σ |
| symmetric order veto | V89 | 294/133 | 31/12 | 2 | 0.849 [0.441, 1.461] | 0.930 | [0.705, 1.463] | **FLAT** 0.38σ |
| symmetric order veto | **V89+V90** | 564/133 | 60/12 | 2 | **0.938 [0.639, 1.622]** | 0.913 | [0.729, 1.296] | **FLAT** 0.62σ |
| v ≥ 22.2 m/s | V89 | 205/59 | 8/3 | 1 | 0.941 [0.840, 1.088] | 0.986 | [0.835, 1.202] | **FLAT** 0.13σ |
| v ≥ 22.2 m/s | **V89+V90** | 237/59 | 10/3 | 1 | **1.028 [0.863, 1.379]** | 0.987 | [0.788, 1.309] | **FLAT** 0.11σ |
| v ≥ 20.46 m/s | V89 | 242/61 | 10/3 | 2 | 1.216 [0.962, 1.280] | 1.451 | [0.831, 1.191] | "resolvable" 3.83σ |

**The one stratum that reads a rise is an artefact and it can be shown to be one.** `v ≥ 20.46` and
`v ≥ 22.2` share 205 of 242 V89 windows and 59 of 61 V88 windows — **37 V89 and 2 V88 windows carry
the whole flip from 1.451 to 0.986.** Both thin strata run on **3 V88 episodes** and 1–2 cells, so
the matching is vacuous; and the no-hypothesis placebo band `e_10-16` also reads "resolvable"
(1.66σ) there, which is the signature of a stratum artefact rather than a band-specific effect.

⇒ **Reverting `0xC40D2` to 102 is NOT supported by the grinding measurement.** It is also not
contraindicated. **Power, stated honestly: this corpus cannot resolve an `e_18-22` change smaller
than ≈ ±20 % (all-engaged) to ±30 % (order-vetoed).**

### 5.2 `e_6-9`, reported separately and NOT as a fix
All-engaged contrast **0.717 [0.533, 1.008]**, 3.64σ outside its placebo band (V89+V90 arm); but under
the symmetric order veto **0.879, FLAT (0.76σ)** and at v ≥ 22.2 m/s **0.914, FLAT (0.76σ)**.
**The band measures lower on V89/V90 than on V88 on the unvetoed set and does not survive the veto.
The operator says micro-ratcheting still exists. A band moving is not a symptom being fixed.**

### 5.3 Absolute levels — for scale only
| arm | n | blk | `e_6-9` | `e_18-22` | `e_26-31` | `e_32-38` |
|---|---|---|---|---|---|---|
| V88/r73 | 325 | 45 | 332.2 [201.8, 575.5] | 128.4 [89.8, 176.4] | 81.3 [74.2, 97.6] | 44.3 [38.3, 49.7] |
| V89/r75 | 428 | 60 | 147.0 [104.7, 231.9] | 69.8 [49.5, 105.6] | 78.8 [65.2, 92.7] | 40.9 [34.2, 48.4] |
| V89/r76 | 487 | 68 | 134.8 [93.6, 201.6] | 55.0 [40.1, 81.1] | 48.5 [30.9, 69.9] | 31.2 [24.0, 42.8] |
| **V90/r77** | 792 | 113 | 248.3 [216.4, 320.1] | 106.7 [83.1, 139.9] | 76.4 [65.6, 88.6] | 48.5 [43.0, 54.5] |

🛑 **UNMATCHED.** `e_1-4` (driver input) V89 ÷ V88 = 0.80 [0.63, 1.06]: route 73 was driven far harder.
Route 77 is louder than r75/r76 **across every band including the control** — it was a harder drive
(rate median 4.2 °/s, p90 43.8, against r75's 2.6/18.4), consistent with the parking-lot + street +
highway protocol. **The raw medians are exposure, not firmware. The matched ratio is the number.**

---

## 6. D6 — THE THREE SYMPTOMS ON ROUTE 77, AND WHAT THE CORPUS CANNOT ANSWER

### 6.1 ★ Route 77 is a CONSTANT-BUILD PLACEBO by construction — and it is damning
V90 changes no calibration cell, so **r77 vs r75/r76 is the same firmware on different drives.**

| pair (SAME FIRMWARE) | `e_6-9` ratio | `e_18-22` ratio | `e_32-38` (control) |
|---|---|---|---|
| r77 ÷ r75 | **1.288 [1.017, 1.661]** — CI excludes 1 | 1.121 [0.870, 1.472] | 0.993 [0.807, 1.189] |
| r77 ÷ r76 | 1.340 [0.925, 2.259] | **1.333 [1.001, 2.307]** — CI excludes 1 | 1.379 [0.977, 2.164] |

**Two drives on identical firmware produce band ratios whose episode-block CIs exclude 1.00, and one
of them "excludes 1" on the band contrast as well.** This is a fresh, concrete instance of the
standing correction that block bootstraps understate cross-build uncertainty — and it is why every
number in §5 carries a placebo band.

### 6.2 🛑 The grind-#2 regime is essentially UNEXPOSED — census, not a number
The operator feels grind #2 **on highway-speed curves and lane changes**. That conjunction barely
exists in the corpus (cells are windows/blocks):

| cut | V88/r73 | V89/r75 | V89/r76 | V90/r77 |
|---|---|---|---|---|
| v≥22.2 m/s & rate≥5 °/s | 7/5 | 33/10 | **1/1** | **6/3** |
| v≥22.2 & rate≥2 | 32/9 | 77/22 | 9/5 | 26/7 |
| v≥13.9 & rate≥5 | 28/9 | 37/11 | 14/9 | 53/18 |
| v≥13.9 & rate≥10 | 10/4 | 16/7 | 2/2 | 27/8 |
| v≥13.9 & rate≥2 | 56/13 | 107/29 | 84/32 | 139/28 |

On the loosest populated cut (v≥13.9 & rate≥5) the **same-firmware** r77 ÷ r75 comparison returns
`e_18-22` **1.504 [1.184, 1.732]** and `e_6-9` **2.904 [0.862, 5.118]** — on identical firmware, with
**1 stratification cell**, i.e. no matching at all. **⇒ NO grind-#2 claim can be made on this corpus
in either direction.** What it would take: matched engaged exposure at **v ≥ 22.2 m/s with
|wheel rate| ≥ 5 °/s** — deliberate highway curves and lane changes, several minutes of them, on each
build being compared.

For scale only, on v≥13.9 & rate≥5: `e_26-31` V88/r73 198.7 [127.8, 373.4] · V89/r75 739.8
[326.1, 809.7] · V90/r77 404.4 [207.5, 685.7]. The spread across two same-firmware routes (739.8 vs
404.4) is larger than any cross-build difference here.

---

## 6c. D6c — GRIND #2 AGAINST THE **LOAD** COVARIATE: the load axis does NOT extend to grind #2

2,032 engaged windows, 286 blocks, all four routes. `|0x0E4|` p5 102 → p95 3,584 ct = **35.2× load
range**. Route fixed effects, block bootstrap over ~10.2 s units, every coefficient reported as a
**contrast against the 32–38 Hz negative control**.

**`log|cmd|` (the mesh-load proxy):**
| band | all engaged | highway v ≥ 13.9 m/s |
|---|---|---|
| **6–9 (ratchet)** | **+0.219 [+0.103, +0.338]** ✔ | +0.082 [−0.034, +0.200] n.s. |
| 18–22 (grinding) | **+0.213 [+0.088, +0.340]** ✔ | +0.018 [−0.109, +0.151] n.s. |
| **26–31 (grind #2)** | **−0.075 [−0.135, −0.012]** ✔ | **−0.163 [−0.258, −0.055]** ✔ |
| **40–49 (grind #2)** | **−0.066 [−0.110, −0.023]** ✔ | **−0.139 [−0.200, −0.072]** ✔ |

🛑 **Grind #2's bands get QUIETER with more command load, more so on the highway cut — the OPPOSITE
sign from the ratchet.** The hypothesised replication fails by reversing, not by going null.

**What does carry grind #2 (highway cut, contrasts vs 32–38):**
| axis | 6–9 | **26–31** | 40–49 |
|---|---|---|---|
| `log\|cmd\|` | +0.082 n.s. | **−0.163** ✔ | **−0.139** ✔ |
| `log\|rate\|` | +0.239 ✔ | **+0.553 [+0.442, +0.651]** ✔ | +0.131 ✔ |
| `log v` | **−1.162 [−1.497, −0.840]** ✔ | **+0.554 [+0.278, +0.825]** ✔ | −0.081 n.s. |
| `log\|lat accel\|` | +0.034 n.s. | −0.080 n.s. | **+0.177** ✔ |

### 🛑 THE DISSOCIATION — the real finding
**The ratchet and grind #2 carry OPPOSITE signs on BOTH the load axis and the speed axis**
(load, all-engaged: +0.219 vs −0.075; speed, highway: −1.162 vs +0.554; all four CIs exclude 0).
⇒ **No evidence that one lever could touch both symptoms.** Anything that reduces command load would,
on these coefficients, be expected to make 26–31 Hz *worse*. [EVIDENCE for the coefficients;
**BELIEF** for the mechanistic reading — a regression coefficient is not a lever response.]

⊕ **Lateral acceleration is not the "curve" covariate**: null at 26–31 Hz on the highway cut. The
operator's *"highway-speed curves and lane changes"* is captured by **wheel rate**, not sustained
lateral load — a constant-radius curve has low wheel rate, a lane change has high wheel rate.

⚠ **The ratchet's load coefficient replicates in DIRECTION but not MAGNITUDE** — +0.219 here against
the corpus's +0.950. This specification always carries `log v` as a competitor, pools four routes with
fixed effects, and includes route 77 (792 of 2,032 windows). **Sign and CI exclusion replicate; size
does not, and no claim is made that it does.**
⚠ The highway cut is **v ≥ 13.9 m/s**, not the v ≥ 22.2 m/s the operator names — that stricter cut has
6 windows on route 77 and cannot support a regression.

---

## 7. D7 — IS THE 6–9 Hz MODE VISIBLE IN THE MOTOR RATE? **The hypothesis is REFUTED.**

**Claim tested:** `gp-0x6b26`'s band shape is the lane's differentiator applied to a featureless
input ⇒ the motor rate has no 7.8 Hz peak ⇒ the mode lives beyond the torsion bar / worm mesh and no
motor-rate-derived term can damp it at any gain.

### 7.1 The lane, re-simulated and ASSERTED
Taps copied from `TRACE-2026-08-10-damping-axis-hunt.md` §1, **not re-derived** (`0xC643C`=37,
`0xC40DC`=22, `>>7`/`>>6`/`>>9`, true backward difference, ±0xFA0000 clamp), re-run at 1 kHz with
Python's arithmetic floor-shift (== V850 `sar`):
`|H(7.79)| = 3.0803` vs published 3.078 · `|H(21.09)| = 7.5465` vs 7.542 · `|H(28.10)| = 9.2676` vs
9.260. **Assertion passed.**

### 7.2 The band-shape argument is a TWO-BAND COINCIDENCE
Densities normalised to 15–22 Hz:
| band | (a) no-alias, flat input ∝\|H\| | (b) full-alias, flat input | **MEASURED** |
|---|---|---|---|
| 2–4 | 0.181 | 0.995 | **0.495** |
| 6–9 | 0.439 | 0.996 | **0.496** |
| 9–12 | 0.604 | 0.997 | **0.500** |
| 15–22 | 1.000 | 1.000 | **1.000** |

The 15–22/6–9 ratio matches (measured 2.015 vs 2.276 predicted) — **but a flat input through this
differentiator requires 2–4 Hz to sit at 0.412× the 6–9 Hz value, and it measures 0.998.**
⊕ The channel is **not alias-dominated**: full aliasing predicts flat 0.995 everywhere.

### 7.3 The quantisation floor kills 2–4 Hz, and only 2–4 Hz
Low-passed below 4 Hz, re-quantised through the exact packer law, measured what the quantiser alone
manufactures: **2–4 Hz 1.33× · 6–9 Hz 10.71× · 9–12 Hz 18.78× · 15–22 Hz 41.64×** above that floor.
⇒ 2–4 Hz *is* quantisation of a slow signal (which is why it broke the |H| shape); 6–9 Hz is not.
Set 2–4 aside and the three remaining bands follow the differentiator within ~17 %.

### 7.4 ★ THE CONTROL THAT DECIDES IT
`T(f) = B26(f)/W(f)` by cross-spectrum against the steering-wheel rate; `R(f) = |T|/|H| ∝ motor rate
/ wheel rate`, normalised at 2–4 Hz where column and motor are rigidly coupled (k and all scales
cancel). **A mode the motor cannot see must show a DIP.** 303 engaged windows:

| band | \|T\| ct/(°/s) | \|H\| | **R norm** | coh² | coh² shuffled |
|---|---|---|---|---|---|
| 2–4 | 0.845 | 1.230 | 1.000 | 0.271 | 0.005 |
| 4–6 | 1.469 | 2.012 | 1.063 | 0.210 | 0.003 |
| **6–9** | 2.086 | 2.989 | **1.016** | **0.438** | 0.001 |
| 9–12 | 2.061 | 4.108 | 0.730 | 0.206 | 0.000 |
| 12–16 | 3.390 | 5.349 | 0.923 | 0.365 | 0.000 |
| 15–22 | 4.652 | 6.802 | 0.996 | 0.765 | 0.000 |

**R is FLAT. No dip at 6–9 Hz — it reads 1.016 with the HIGHEST coherence of the low bands (0.438
against a shuffled 0.001).** 🛑 **"The firmware cannot SEE the 6–9 Hz mode" is REFUTED. The lane goes
back in play for the ratchet.** [EVIDENCE] Aliasing cannot rescue the hypothesis: shared alias energy
is broadband and would *decohere* the channels; 6–9 Hz is the most coherent low band on the route.

### 7.5 The real residual — the narrow LINE, not the band
Free-argmax over 4–15 Hz, same windows, same estimator, symmetric order veto on both.
**Chance for a flat spectrum is 3/11 = 0.273.**
| channel | median f0 | median prominence | fraction arg-maxing in 6–9 Hz |
|---|---|---|---|
| recovered motor rate | 9.53 Hz (vetoed 10.12) | **6.93** | **0.327** (≈ chance) |
| column torque | 8.56 Hz (vetoed 8.37) | **11.31** | **0.482** (vetoed 0.523) |

⇒ **Broadband 6–9 Hz column motion reaches the motor undiminished; the sharp resonance LINE is partly
on the far side of the compliance.** Neither "invisible" nor "fully visible".

### 7.6 Power — the channel had the range
At route 77's engaged median speed (9.30 m/s, k = 0.0815), a fully-transmitted 7.79 Hz column ring
would give, against a measured 6–9 Hz band rms of **2.74 counts**: 0.10° → 4.1 ct (1.5×) · 0.25° →
10.2 ct (3.7×) · 0.645° → 26.4 ct (9.6×) · 0.96° → 39.3 ct (14.4×).
⚠ 2.74 is the *median window*; 0.645–0.96° is the ring *when it fires* — a range check, not a matched
comparison.

### 7.7 What this changes for the build
`gp-0x6b26`'s output being 15–22 Hz-heavy is **the differentiator's own gain shape**, not a statement
about what the lane can perceive. The two facts are now separable:
- authority per unit of wheel rate: **2.99 at 6–9 Hz vs 6.80 at 15–22 Hz** ⇒ **2.3× less authority per
  °/s at the ratchet than at the grinding band — not zero.**
- a gain dose scales both ⇒ **a dose aimed at grinding will also act on the ratchet at ~44 % of the
  per-rate authority.** A side effect worth pricing in either direction, unavailable before this.

⚠ **Limitations:** both channels are sub-sampled without anti-alias filtering (b26 50 Hz, wheel rate
100 Hz), so shared alias energy is present in R even though it cannot explain the result; the
deconvolution divides by |H|, small below ~2 Hz, so nothing below 2 Hz is trustworthy; `rate_f`'s
~25 % scale error cancels in R but not in §7.6's absolute figures.

---

## 8. INSTRUMENT DEFECTS FOUND THIS SESSION

1. **🛑 `raw14` off-by-one — FIXED PROPERLY, and the obvious fix is WRONG.** `D.extract` appends to
   `raw14_*` on every 0x14A frame but appends a ROW only once `last18` is non-None, so the map is a
   **constant lead** (= 1 on r77). `extract_r77.py::_row2raw14` derives it and asserts it elementwise
   against both `raw14_t` and `raw14_b4`, storing `row2raw14` in the npz.
   **A `searchsorted` map on timestamps is WRONG**: `evt.can` can carry two 0x14A frames in one event,
   which share `logMonoTime` exactly (**3,018 duplicate raw14 timestamps on r77**), so searchsorted
   collapses onto the first of each tie and **mispairs 1,604 rows — while the TIMESTAMP check still
   passes.** Only the byte check catches it. Both are asserted.
2. **`_r31_common.runs_of` returns a GENERATOR.** The first consumer exhausts it and every later
   consumer silently sees **zero windows**. This produced an all-NaN shuffled control on the first D3
   pass — and a NaN control reads as "no control available", not as a bug. Materialise with `list()`.
   Worth auditing anywhere `runs_of` is passed to more than one estimator.
3. **`v88_d1_exposure.grid` interpolates `raw14_b4` with `np.interp`.** That column is a BITFIELD;
   interpolated values have meaningless bits. Any bit test reading `g["b4"]` is suspect. D3/D5 pair
   nearest-within-10 ms instead.
4. **🛑 STANDING-INSTRUCTION CORRECTION — the v ≥ 22.2 m/s stratum is NOT order-clean for these
   bands.** With circumference 2.073–2.088 m and guard 0.8 Hz, order *k* reaches a band over
   `v ∈ [(lo−0.8)·2.073/k, (hi+0.8)·2.088/k]`:
   - **6–9 Hz** clean above **20.46 m/s** — 18.8 m/s is *not* conservative enough;
   - **18–22 Hz** — order 2 covers **17.83–23.80 m/s**; clean only above 47.6 m/s (171 km/h);
   - **32–38 Hz** — order 3 covers **21.60–27.00 m/s**; clean only above 81 m/s.

   ⇒ **No speed stratum is clean for all three bands at once, and above ~21.6 m/s it is the 32–38 Hz
   NEGATIVE CONTROL that order 3 contaminates — the screening asymmetry INVERTS at highway.**
   Measured on the v ≥ 22.2 arm: 18/205 order hits on 18–22 Hz but **76/205 on the 32–38 control.**
   §5 therefore uses a **symmetric** veto (drop a window if any order 1–6 lands on ANY scored band's
   own measured line), so every band is screened by the identical rule on the identical window set.
   Per-band vetoes build different window sets per band and turn a contrast into a comparison of two
   different sets.

---

## 9. WHAT THIS FLIGHT DID AND DID NOT SETTLE

**Settled [EVIDENCE]:** V90 is on the car · the observer gate never fails · `gp-0x6b26`'s full
distribution and its zero clamp duty · the CLIPPING ladder (1.60× / 2.75× / 4.45× — **not** a dose
budget; the int32 wraparound at ≈1.6005× binds first, §10.2) · `Re(Z) < 0` across
2–16 Hz replicated at 37× the exposure · the 6–9 Hz `b26 → column` transfer is feedthrough · b6's
guessed threshold is well-placed · no measurable grinding regression from K1 = 204 · **the motor rate
DOES contain the 6–9 Hz band (R = 1.016, coh² 0.438 vs shuffled 0.001) — the "firmware is blind to the
ratchet" hypothesis is refuted** · **the load axis does NOT carry grind #2; it carries it with the
opposite sign, and the ratchet and grind #2 dissociate on both load and speed.**

Also settled: **D damps 16–35 Hz ⇒ the `Kd` cut is closed** (§4.1a) · **`Re(Z)` flips sign at ~26 Hz**,
so grind #2's band is not anti-damped · **the anti-damping is not the PID** (§4.1c) · **the `0x18F`
vs `0x14A` rate choice inverts the sign of any phase above ~16 Hz** (§4.1b).

**Not settled, and why:**
- 🛑🛑 **THE ONE THAT GATES EVERYTHING: is the EPS LOOP anti-damped, or the PLANT?** Manual hands-off
  moving = **2 windows / 21.4 s** in the whole corpus. **If it is the plant, no firmware lever can
  remove it — firmware could only add damping against it, and §10.-1 shows the available damping
  levers are spent.** Needs a deliberate hands-off coast: cancel button, foot off the brake, hands
  off, hold 5 s either side. **~15–20 minutes of driving. See §11.0.**
- **Where does the 2–26 Hz anti-damping come from, if not the PID?** Another aggregator lane, or the
  plant. Unanswered, and every remaining firmware candidate has to answer it.
- **Grind #2 at the speed the operator names.** v ≥ 22.2 m/s with |rate| ≥ 5 °/s is 6 windows on this
  route; §6c's regression is about 50 km/h+, not 80 km/h+. Needs deliberate exposure on every build
  being compared.
- **Is the friction lane separable from `|model|`?** Only below 1 °/s, where the discriminating cell
  is 0.63 % of engaged frames overall.
- **Is 2.64 ct/ct at 15–22 Hz a plant gain?** It survives a one-sided causality screen. That is not
  the same as being causal.
- **Why is the narrow 7.8 Hz LINE attenuated toward the motor while the 6–9 Hz BAND is not?** §7.5
  measures it; nothing here explains it.

**None of the operator's three symptoms is called fixed. He reports all three still present.**

---

# 10. 🛑 V91 PRE-REGISTRATION — written 2026-08-11, BEFORE the build is cut

**V91 as being cut, 2026-08-11:** `0xCBE74` **×1.5** on the ENGAGED record, `0xC407E` asserted at 511,
**cal-only, 12 bytes, cave and CAN 427 UNCHANGED from V90.**
**This section is written while the outcome cannot be seen. Nothing below may be revised after V91
flies except by adding a dated note saying what was changed and why.**
⚠ **Revision note, 2026-08-11:** this section was first drafted against a proposed ×2–2.5 dose and is
rewritten here for the **×1.5** dose actually being cut. Every number below is recomputed for ×1.5;
the ×2/×2.5 predictions are superseded and are **not** carried forward, so that no one can later pick
whichever bracket happens to fit.

## 🛑 10.-1 STATUS BLOCK — READ BEFORE USING THIS PRE-REGISTRATION

**This plan is live ONLY as a scoring recipe for V91 if V91 flies. Two levers a reader might reach for
from here are CLOSED, and they are closed on arithmetic rather than on a null.**

| lever | status | why |
|---|---|---|
| **`Kd` cut on `FUN_0003a382`'s D term** (the candidate "V92") | 🛑 **CLOSED — do not build** | §4.1a: **D pumps only 2–12 Hz and DAMPS 16–35 Hz.** Removing the **+0.077** pump at 6–9 Hz costs **−0.217 at 18–22** and **−0.336 at 26–31** — **2.9× and 4.4×** — and those are the operator's own two grinding bands. |
| **A larger `0xCBE74` dose than ×1.5** | 🛑 **CLOSED — there is no larger dose, ever** | The int32 wraparound bound is **≈1.6005×** (§10.2), so **×1.5 is at 94 % of the lever's ENTIRE range.** Not "untested at higher dose" — *unreachable*. |

⊕ **The orchestrator's wider position, recorded as reported and not as my measurement:** combined with
a Q-B-class sizing estimate of **5–69× below the resolvability floor** and `0xC63A6`'s kill on lane
magnitude (micro-regime p50 **7.1 ct** ⇒ 0.22 % of the residual clamp), **the whole `gp-0x6b26` lane is
considered spent — closed on arithmetic, not on a null.** ⚠ **The 5–69× figure and the `0xC63A6`
result are other agents' work, not mine**; I have not reproduced either and they are cited here so the
status is traceable, not so it is double-counted as my evidence.

⇒ **If V91 flies, score it with §10.1–10.6 exactly as written. Do not read §10 as licence to escalate
the dose, and do not read it as a live plan for the `Kd` lever.**

## 10.0 THE MODE MAP — resolved, and my own earlier flag was HALF WRONG

⚠ **Correction, 2026-08-11.** I originally wrote that *"27 appears in no byte-verified record I can
find"*. **That was wrong, and it is withdrawn.** It was true of the SPEC document, which names only 24
and 26, but not of the firmware: **mode 27's record exists and is byte-verified**, dereferenced
independently three times (orchestrator, `arc-sweep`, builder).

**The precise status, which is what should be carried forward:** *the record exists and is
byte-verified; the mode is never observed reached, so writing it is FREE INSURANCE, not a second
lever.* No result may be attributed to mode 27.

```
mode 24 MANUAL   ptr 0xCBED4 -> rec 0xD6A64   X@0xD6A66   Y@0xD6A6C
mode 25          ptr 0xCBED8 -> rec 0xD7A44   X@0xD7A46   Y@0xD7A4C
mode 26 ENGAGED  ptr 0xCBEDC -> rec 0xD7A54   X@0xD7A56   Y@0xD7A5C
mode 27          ptr 0xCBEE0 -> rec 0xD7A64   X@0xD7A66   Y@0xD7A6C
all four: n=3, X=[0, 1280, 5760], Y=[-9830, -5734, -1966], V90 byte-stock
```
⊕ **And modes 25/27 are barely reachable:** `gp-0x67e2` held at 1 for all **104,061** frames of V73
telemetry, so neither was entered once. **Dosing 27 is free insurance, not a second lever** — it
should not be described as one, and no result may be attributed to it.

**What survives from the original flag, and it is the part that matters:** the builder must still
**dereference `0xCBE74 + mode*4` and print the mode number beside every address touched.** That
discipline is what caught `0xD6A5C` being mode **23**, not 24, and what stops a Y row being written
into the X breakpoint array (compared UNSIGNED ⇒ a flat `Y[0]` at all speeds, a silent 5× at highway).

⊕ **§10.1's manual arm is the on-car version of the same check, and it costs nothing.** Mode 24 is
untouched, so **manual must read 1.00**. If mode 24 were edited by mistake, the manual arm scales and
says so on the first drive — no disassembly required.

## 10.1 ★ THE DOSE-IN-FORCE TEST — parameter-free, free, and it runs BEFORE any band scoring

427 carries `clamp(|gp-0x6b26|·5>>3, 0, 0x3FF)` and the dose multiplies `gp-0x6b26` **before** the
±511 clamp. So the dose is directly observable in the instrument already on the car.

**PREDICTION, stated now, for ×1.5.** The clamp binds only above an undosed **340.7** counts, and route
77's engaged **maximum over 53,630 frames is 319.1** ⇒ **at ×1.5 NOTHING clips — the whole distribution
scales linearly, end to end.**

| percentile | route 77 (measured) | **predicted ×1.5** | predicted wire |
|---|---|---|---|
| p50 | 5.5 | 8.25 | 5 |
| p75 | 16.7 | 25.05 | 15 |
| p90 | 39.1 | 58.65 | 36 |
| p95 | 58.3 | 87.45 | 54 |
| p99 | 114.3 | 171.45 | 107 |
| p99.9 | 184.7 | 277.05 | 173 |
| **max** | 319.1 | **478.65** (93.7 % of the 511 rail) | **299** |
| **clamp duty at ±511** | 0.000000 | **0.000000, in EVERY stratum** | — |

⚠ Quoted to 2 dp deliberately: every one of these lands on a **half-way** value (25.05, 58.65, 87.45,
171.45, 277.05), so a 1 dp rendering differs by 0.1 purely on rounding convention and **is not a
disagreement between two derivations.** ⊕ The source percentiles are themselves quantised at
1.6 ct/LSB, so **the third significant figure is not physically meaningful** — compare at 2 sf.

### Why ×1.5 and not more — three independent bounds, and one of them is not about clipping
1. **Clip envelope** — route 77 engaged max 319.1 against the ±511 rail ⇒ **≤ 1.6014**.
2. 🛑 **int32 wraparound in `FUN_00036c12`'s `mul r13,r6,r0`** (×0x111, high half discarded,
   **unclamped and UPSTREAM of `0xC407E`**) ⇒ structurally impossible only for **≤ 1.6005**, proven
   against `gp-0x6c2c`'s own hard ±32,000 producer clamp, **so it holds in transients route 77 never
   sampled.** This is the binding bound and it is *not* visible in any percentile table.
3. It is **the dose that flew on V74/V75**, so V91 changes exactly one thing against those builds.

⚠ The p50 sits at only ~3 wire LSB, so **p75/p90/p95 are the load-bearing statistics; p50 is
quantisation-coarse.**

### ⊕ THE CLIP CHECK — pre-stated, and it is a REVERT trigger
D3's pinning ladder puts the **largest never-pinning multiplier at 1.60×**, so **×1.5 sits only 6.3 %
under the rail** and the predicted maximum, **478.7**, is 93.7 % of it. That makes the clip check
sharp rather than academic:
- **Predicted: clamp duty exactly 0.000000, and `wire` never reaching 319** (the wire value of a
  railed lane).
- 🛑 **Any observed clamp duty above ~0 — equivalently, repeated `wire == 319` — means the lane is
  spending time at `sign(gp-0x6c2c) × 511`, i.e. it has become a COULOMB RELAY. That is the V80
  mechanism exactly, and V80 was "the worst grinding ever".** Treat it as a **revert trigger in its
  own right**, independent of any band result and independent of what the operator reports.
- Because the margin is 6.3 %, **a drive rougher than route 77 can cross it without the dose being
  wrong.** So report clamp duty **stratified by wheel rate and speed** — the binding strata are
  ratchet 13–50 °/s and 5–20 km/h — and read a small nonzero duty as *this drive exceeded route 77's
  worst sample*, not automatically as a build fault.

**THE TEST — three arms, all pre-declared:**
1. **ENGAGED, cell-stratified** (speed bin × wheel-rate bin, the same partition the band estimator
   uses): median `|gp-0x6b26|` ratio V91 ÷ route 77 must equal **1.50, tolerance ±15 % ⇒ [1.275,
   1.725]** (±10 % ⇒ [1.350, 1.650]), with a CI excluding 1.00. 🛑 A raw route-average percentile
   comparison is NOT acceptable — `|gp-0x6b26|` runs p50 2.3 at <1 °/s against 19.9 at 13–50 °/s, so
   an unmatched comparison confounds the dose with the drive.
2. **MANUAL — the built-in negative control. The ratio must be 1.00.** The dose is on the engaged
   record only. **If the manual arm also scales, the wrong record was edited** (mode 24 is MANUAL) and
   the build must be pulled regardless of what the bands say. Route 77 has 8,434 paired manual frames
   (2,475 moving), which is ample.
3. **PER SPEED BIN.** `0xCBE74` is a **speed-indexed LERP** (`gp-0x6a5e` = vehicle speed, settled). A
   whole-row ×N must give ×N **at every speed**. A ratio that varies with speed means only some
   breakpoints were edited — a free, decisive build-verification test that costs nothing.

**PRE-DECLARED READINGS, so a null cannot be misread (V64's null was on the GATE, not the hypothesis):**
- ratio ≈ 1.50 engaged, ≈ 1.00 manual, flat across speed ⇒ **DOSE IN FORCE.** Band results are
  interpretable.
- ratio CI **contains 1.00** ⇒ **DOSE NOT IN FORCE.** 🛑 **Every band result is then uninterpretable
  and must NOT be reported as a falsification of the damping hypothesis.** This is the single most
  important line in the section: V64's null was on the gate, and it was read as a result for weeks.
- ratio strictly between 1.00 and 1.50, or speed-dependent ⇒ **PARTIAL DOSE.** Report the effective
  multiplier per speed bin; do not average it away.
- ratio ≈ 1.50 in **both** arms ⇒ **WRONG RECORD.** Pull the build.

⊕ **The operator is a fourth dose-in-force instrument.** The trace doc predicts this dose adds
*"steering effort specifically during fast wheel-rate transients, largest at low speed."*
**A report of heavier steering is CONFIRMATION that the dose is live, not a failure** — and it should
be asked for explicitly rather than waited for.

## 10.2 PRIMARY ENDPOINT: `e_18-22` (the operator's grinding band)

**Direction predicted: DOWN.** Two independent instruments put this lane on the grinding band —
D3's band content (density 3.184 at 15–22 Hz vs 1.580 at 6–9) and D4's transfer, where 15–22 Hz is the
**only** band surviving the group-delay screen (2.64 ct/ct, +6.3 ms, coh² 0.333 vs shuffled 0.000).

**🛑 MINIMUM RESOLVABLE EFFECT, derived from this session's own placebo, not assumed:**
- on the **32–38-contrasted** statistic, the same-firmware placebo band is **[0.845, 1.221]**
  ⇒ **resolvable only if ≥ 15.5 % down or ≥ 22.1 % up.**
- on the **raw ratio**, the placebo band is **[0.820, 1.261]**, and whole-route same-firmware pairs ran
  as high as **1.333** (r77 ÷ r76) ⇒ **the honest raw-ratio floor is ≈ ±33 %.**

### 🛑 IS THE PREDICTED ×1.5 EFFECT ABOVE THAT FLOOR? **I cannot promise that it is, and I am saying so now.**
Bounding it honestly:
- **Upper bound.** A ×1.5 gain on **one** damping term cannot change a band energy by more than ×1.5
  (+50 %), and that ceiling is only reached if this lane alone set the 15–22 Hz column energy.
- **Lower bound.** Zero. The lane is one term among several entering the aggregator.
- **The measured transfer cannot narrow this.** D4's `|tq/b26| = 2.64 ct/ct` at 15–22 Hz is a
  **closed-loop** correlation that merely survived a one-sided screen. Using it to predict a dose
  response is exactly the inference D4 exists to forbid, and I will not do it.

⇒ **The plausible effect range STRADDLES the detection floor.** If V91's true effect on `e_18-22` is
below ~16 %, **this corpus returns a null that means nothing, and the operator's own report becomes the
primary endpoint.** Stated in advance so a null is not later read as "the lever does nothing".

### ⊕ AND THE MECHANISM PREDICTS A BIMODAL OUTCOME, WHICH CHANGES HOW A NULL READS
Under friction-induced vibration the response to added damping is **threshold-like, not proportional**
(Brockley & Ko; `HANDOFF-2026-08-10` §2a): below threshold nothing visible happens, above it the
vibration is quenched. ⇒ **The two most likely outcomes are "≈ nothing" and "a lot" — a clean ~18 %
is the LEAST likely of the three.** Pre-declared consequences:
- **A null at ×1.5 does NOT falsify the damping lever.** It says the dose was below threshold. 🛑 The
  kit's standing method reads small-dose nulls as falsification, and that inference is **invalid** for
  this mechanism.
- A large quench (≫ 50 % on the band, or the operator simply reporting the grinding gone) is a
  legitimate outcome of a ×1.5 dose and must not be dismissed as too large to be real.
- ⇒ **If ×1.5 nulls, the correct next step is a LARGER dose, not abandoning the lane.**

🛑🛑 **CORRECTION TO MY OWN EARLIER DRAFT OF THIS PARAGRAPH — it gave unsafe advice and I am
withdrawing it.** I wrote that D3's ladder leaves room to escalate to **2.75× (pinning < 0.1 %) or
4.45× (< 1 %)**. **That is wrong as a dose recommendation.** D3's ladder is a *clipping* argument
only, and clipping is not the binding constraint:

> **`FUN_00036c12`'s `mul r13,r6,r0` (×0x111, high half discarded) is UNCLAMPED and sits UPSTREAM of
> `0xC407E`. int32 wraparound is structurally impossible only for a multiplier ≤ 1.6005.**
> **A ×2.75 dose is past that bound. It would not "pin" — it would WRAP, and a wrapped product is a
> full-scale SIGN INVERSION on the damping lane, delivered before the clamp that is supposed to
> contain it.**

⇒ **The escalation ceiling is ≈1.60×, not 4.45×**, and ×1.5 is already at **94 % of it**. There is
**no meaningful headroom above ×1.5 on this cell.** If ×1.5 nulls, the next step is a **different
lever or a different injection point** — for example `0xC63A6`, which weights `gp-0x6b26` *after* the
clamp and therefore cannot pin and cannot wrap — **not a larger `0xCBE74`.**
⊕ Keep §10.1's clip check regardless: it is cheap, and it is the on-car witness for a bound that is
otherwise only a static argument.

⊕ **RECOMMENDATION THAT COSTS NOTHING AND BUYS THE MOST: fly V91 on the SAME ROUTE as 77.** Same
driver, same roads, adjacent in time — the best-matched cross-build pair this kit can construct, and
the only lever available for narrowing that ±20–33 % floor without new methodology.

## 10.3 PRE-DECLARED NEGATIVE CONTROLS
1. **32–38 Hz band**, differenced on the same resampled episodes (standard).
2. **A same-firmware placebo pair** — route 77 ÷ route 75. 🛑 **Mandatory.** Two drives on
   byte-identical firmware returned `e_6-9` **1.288 [1.017, 1.661]** with the band contrast also
   excluding 1.00. **The band contrast does not rescue a thin cut.** If V91 produces two routes, its
   own internal pair is the better placebo and should be used as well.
3. **The manual arm of §10.1** (must not scale).
4. **`e_1-4`** as the exposure/matching-validity check.
5. **The symmetric wheel-order veto** (drop a window if any order 1–6 lands on ANY scored band's own
   measured line) — per-band vetoes build different window sets per band. **No speed stratum is
   order-clean for 6–9, 18–22 and 32–38 at once; above 21.6 m/s it is the 32–38 CONTROL that order 3
   contaminates.**

## 10.4 `e_6-9` IS A **SECONDARY ENDPOINT** — and the band ratio is itself a test of the mechanism

D7 refuted "the firmware cannot see 6–9 Hz": the motor rate tracks the column there as well as at
2–4 Hz (R = 1.016, coh² 0.438 vs shuffled 0.001), and the lane's authority per °/s at 6–9 Hz is
**2.99 against 6.80 at 15–22 Hz — 44 %, not zero.** So a smaller effect is **predicted, not excluded**,
and 6–9 Hz is a **secondary endpoint** rather than a non-endpoint.

**PRE-REGISTERED PREDICTION, and it is the sharpest test in this section:**
```
   expected  log-effect(e_6-9) / log-effect(e_18-22)  =  |H(6-9)| / |H(15-22)|  =  2.989 / 6.802  =  0.44
```
This ratio is a **direct test of the mechanism**, because it is fixed by the lane's own transfer
function and is independent of the dose size, of the absolute effect, and of drive-to-drive
variability. Decision rules, fixed now:
- **ratio ≈ 0.44 (say 0.25–0.65), same direction** ⇒ **the mechanism is confirmed and the response is
  the lane's own gain shape.** This is the outcome that would make the lane a proven instrument.
- ratio ≈ 0 (6–9 flat while 18–22 moves) ⇒ consistent with D3's band content but **not** with D7's
  transfer measurement; report the tension rather than picking a side.
- **ratio > 1 (6–9 moves MORE than 18–22)** ⇒ 🛑 **a surprise contradicting D3, D4 and D7 at once. To be
  explained, never claimed as a win.**
- 🛑 The ratio is only computable if **both** effects clear the detection floor. If `e_18-22` is itself
  inside the placebo band, **the ratio is undefined and must not be quoted.**

🛑 **Whatever any of these numbers do, micro-ratcheting is fixed only if the operator says it is.**

## 10.5 🛑 26–31 Hz IS A **TWO-SIDED** ENDPOINT: a falsifiable QUENCH prediction *and* a harm trigger

**This band is where the two arguments collide, so both are pre-registered.**

**The lane's gain is LARGEST here** — `|H(28.10)| = 9.27` against 6.80 across 15–22 Hz and 2.99 across
6–9 Hz — **and GATE 2 says it is MOST dissipative here** (cos 0.68–0.76). Those two facts together make
a prediction, not just a worry:

> **PREDICTED: a ×1.5 dose should QUENCH the 26–31 Hz family, and by MORE than it quenches 18–22 Hz.**
> Expected log-effect ratio `e_26-31 / e_18-22 ≈ 9.27 / 6.80 ≈ 1.35`.
> ⚠ That uses the documented **point** value at 28.10 Hz against a band-rms at 15–22 Hz — a band
> integral over 26–31 was not computed (the D7 scripts are frozen), so treat 1.35 as ±0.1.

⚠ **A tension with §4.1a that a careful reader will spot, so it is stated rather than left to be
found.** §4.1a measures `Re(Z)` **positive (already damped) at 26–31 Hz**, whereas 2–26 Hz is
anti-damped. These are **not** in conflict — the quench prediction is about the **damping lane's own
gain** (`|H(28.10)| = 9.27`, its maximum), not about the PID's D term or about how much anti-damping
is there to remove. **But it does weaken the expected effect**: there is less negative damping to
cancel at 26–31 Hz than the 18–22 argument assumes, so **treat the 1.35× ratio as an upper bound on
the quench, not a point prediction.** The revert thresholds below are unaffected — they are one-sided.

**⊕ And D6c makes it stratum-specific, which is a sharper test than the route average.** Grind #2 rides
**wheel rate** (`rate^1.07` on the highway cut) and loads **negatively** (−0.163). The lane is
rate-derivative-driven, so its authority is greatest exactly where grind #2 is worst. ⇒
**PREDICTED: the 26–31 Hz quench is LARGEST in the high-rate / highway stratum (v ≥ 13.9 m/s,
|rate| ≥ 5 °/s), not in the route average.** Score that stratum explicitly.

🛑 **THE OTHER SIDE. V80 produced a sustained 27.4 Hz limit cycle in this exact band — ×92 over the
in-band median, Q ≈ 140, 30 s unbroken — and a loop-gain edit on the lane with the most gain at that
frequency is the move that produced it.** So an INCREASE here is a **double failure**: it harms the
car *and* it falsifies the dissipative-sign argument that GATE 2 rests on. Say both if it happens.

**REVERT V91 if ANY of the following holds:**
- **(a) BAND.** Engaged `e_26-31` ratio V91 ÷ route 77 **≥ 1.50** with its CI outside the same-firmware
  placebo band **[0.831, 1.200]**. (1.50 is **4.1σ** on the placebo sd(log) of 0.099, and sits above
  the largest same-firmware pair observed, 1.314.)
- **(b) LINE — the sharper detector, and the one that matches what V80 actually was.**
  🛑 **THRESHOLD FIXED 2026-08-11 from route 77 alone, before V91 existed.**
  `rlog-tools/v91_prereg_threshold.py`, read-only on the frozen `_cache_r77`.

  > **TRIP CONDITION: ≥3 consecutive `wrecs` windows with `p_26-31` > 37.12, on ENGAGED,
  > SYMMETRICALLY ORDER-VETOED windows.**
  > Geometry is the estimator's own: **2.56 s window, 1.28 s hop** (NFFT 256 / hop 128 at ~100 Hz) —
  > *not* the 5.12 s windows D3/D4 used on the 50 Hz grid. 3 consecutive ⇒ **≥5.12 s sustained.**
  > **Corroborating criterion in the other currency: ≥3 consecutive with `e_26-31` > 453.45.**

  **Route 77's own numbers, engaged + order-vetoed (477 windows, 105 blocks):**
  `p_26-31` p50 **5.66** · p90 13.43 · p95 18.92 · **p99 37.12** · max 1161.47 (205× the median).
  `e_26-31` p50 **77.85** · p95 298.46 · **p99 453.45** · max 717.02.

  **MEASURED FALSE-POSITIVE RATE ON THE REFERENCE BUILD: ZERO.** At the 37.12 threshold route 77 has
  5 windows above it, in **5 separate runs, longest run = 1 window** ⇒ **0 runs of ≥3**. Same on the
  envelope criterion (4 runs, longest 2, 0 runs of ≥3). **A detector with no measured false-positive
  rate on the reference build is not a detector**; this one has one, and it is zero.

  🛑 **TWO CORRECTIONS TO THE REQUESTED DESIGN, both from the calibration and both load-bearing:**
  1. **p99.9 is NOT usable and I did not use it.** On 477–792 windows, p99.9 is estimated from **a
     single sample** (1204.66 all-engaged / 658.84 vetoed). A threshold at 1/n resolution is noise.
     **p99 is used instead**, and it is reported with its run-length behaviour rather than asserted.
  2. **The detector MUST run on ORDER-VETOED windows, and this is measured, not precautionary.** On
     the **unvetoed** engaged set, route 77 contains a run of **7 consecutive windows (10.2 s)** above
     its own p99 — **the veto removes it entirely**, so it is a **tyre order, not a limit cycle**.
     ⇒ **An unvetoed detector produces a false positive on the reference build itself.** Orders 1–6
     reach 26–31 Hz at **13.1–16.6 m/s (k=4)** and **17.4–22.1 m/s (k=3)**, squarely in the driven
     range.

  ⊕ **Would it have caught V80?** V80's event was **×92 over the in-band median, sustained ~30 s**
  ≈ 23 consecutive windows, against a requirement of 3 at a threshold sitting **6.6× route 77's median
  prominence**. **[BELIEF, and the reason it is not EVIDENCE: V80's ×92 was an amplitude-over-median
  figure and this threshold is in prominence — two different currencies.** The margin is large enough
  that the conclusion is not in doubt, but the two numbers are not directly comparable and I will not
  present them as if they were.]
  ⊕ Route 77's own maximum is a **single 2.56 s window at 205× the median**. **The ≥3-consecutive
  requirement is exactly what separates that isolated transient from a limit cycle**, and it is why
  the criterion is a run length and not a peak.
- **(c) THE OPERATOR.** He reports new or worse vibration, buzzing, or noise. **This overrides (a) and
  (b) in both directions** — his report is primary, the bands are the instrument behind it.

- **(d) THE CLIP CHECK of §10.1** — clamp duty above ~0 at ±511, i.e. repeated `wire == 319`. A railed
  lane is `sign(gp-0x6c2c) × 511`, a Coulomb relay, and that is the V80 mechanism itself rather than
  one of its symptoms. **Revert trigger in its own right.**

⊕ Secondary safety readouts, not revert triggers on their own: `0xC407E` must read `ff01`; DTC-active
duty, sentinels and `STEER_STATUS` must stay at route 77's values (0.000000 / 0 / {0: 124,358, 3: 3}).

### The full pre-registered scorecard, so nothing is chosen after the fact
| # | endpoint | predicted | action |
|---|---|---|---|
| 0 | dose-in-force ratio, engaged | **1.50** [1.275, 1.725] | contains 1.00 ⇒ **everything below is uninterpretable** |
| 0b | dose-in-force ratio, manual | **1.00** | scales ⇒ wrong record, **pull** |
| 0c | clamp duty at ±511 | **0.000000** | > ~0 ⇒ relay, **revert** |
| 1 | `e_18-22` (primary) | **down**, size unknown and possibly below the floor | report vs the ±16–22 % floor |
| 2 | `e_6-9` (secondary) | down, **0.44 ×** the 18–22 effect | ratio > 1 ⇒ surprise, explain |
| 3 | `e_26-31` | **down, ≈1.35 × the 18–22 effect**, largest in the high-rate/highway stratum | ≥ **1.50 up** ⇒ **revert**; or **≥3 consecutive order-vetoed windows with `p_26-31` > 37.12** ⇒ **revert** |
| 4 | `e_32-38` | flat (negative control) | moves with everything ⇒ uniform drive change, not a lever |
| 5 | same-firmware placebo pair | ~1.00 | 🛑 mandatory; r77 ÷ r75 returned **1.288** on identical firmware |
| 6 | the operator | his words | **overrides every row above, in both directions** |

## 10.6 THE OPERATOR SCORES THE SYMPTOMS, IN HIS WORDS

Ask for, and report in, **his** vocabulary: **grinding · micro-ratcheting · ratcheting · stuttering ·
grind #2 on highway curves and lane changes · steering effort / excess friction.** Not band names.
🛑 **"The ring", "grind #1", "S1–S4" and every band label are KIT JARGON.**
🛑 **An absence of complaint is not a report of improvement.** *"I didn't notice anything odd"* is weak
negative evidence and is never a cure.
🛑 **A band moving is not a symptom being fixed.** Report "band X moved by Y" and, separately, what he
said.

---

# 11. THE DRIVING PROTOCOL — the two questions that now genuinely require new driving

## 🛑 11.0 THE HEADLINE: ONE EXPERIMENT NOW DETERMINES WHETHER **ANY** FIRMWARE LEVER CAN WORK

Three results this session converge on a single unanswered question, and it is no longer a refinement —
it is the gate on the entire remaining search:

1. **`Re(Z)` is negative across 2–26 Hz** — anti-damping, established on 221 windows / 884.5 s at
   coherence up to 0.83 against a shuffled 0.001 (§4.1, §4.1a).
2. **The PID is a net DAMPER at 6–9 Hz** (P −0.145, I −0.053, D +0.077 ⇒ −0.121) — **so the
   anti-damping is not coming from `FUN_0003a382`** (§4.1c).
3. **The damping levers that could push against it are spent** — `0xCBE74` is capped at ≈1.60× by an
   int32 wraparound and ×1.5 already sits at 94 % of that range (§10.-1).

> ### ⇒ **If the anti-damping at 2–26 Hz lives in the PLANT rather than in the firmware loop, NO
> firmware lever can remove it.** Firmware could then only *add damping against* it — and this session
> has shown the available damping levers are far too small to do that.
> ### **The measurement that separates those two cases is the MANUAL HANDS-OFF COAST, and the entire
> corpus contains 2 windows / 21.4 s of it.**

**That is the critical experiment.** §11.1 says exactly what it takes: **~6 runs of 30 s minimum
(≈40 windows), ~14 runs for a result comparable in precision to the engaged arm (≈100 windows)** —
about **15–20 minutes of driving**, and it also yields the ring-down edges for free (§11.2).

🛑 **Until that coast exists, "the EPS loop is anti-damped" and "the column is anti-damped" are
indistinguishable on this corpus, and every future firmware lever aimed at the stuttering is a bet on
the first one being true.** Nothing else in this protocol matters as much.

---

The kit's standing position has been that no new drive buys anything diagnostic. **D4 and D6b overturn
that for exactly two questions.** Everything below is sized from this session's own measured window
yields, not from guesses. **Total purposeful driving: ~35–45 minutes per build.**

🛑 **Safety is the operator's judgement, not mine.** Item (a) requires hands off the wheel on a moving
car; do it only on a straight, level, empty road with good surface and no crosswind, in short runs,
with hands within a few inches of the rim and ready to take over. **If a run cannot be done safely, it
should not be done — a missing control is a far better outcome than an incident, and this whole
session's method is built on refusing to manufacture controls.**

## 11.1 (a) THE HANDS-OFF COAST — the only way to separate "the loop is anti-damped" from "the column is"

**Why it matters:** `Re(Z) < 0` across 2–16 Hz is now established on 221 engaged windows (§4.1). But
`MANUAL hands-off moving` has **2 windows / 21.4 s** on route 77 and 6/1/0 on V89's routes. **Without
that arm, the negative damping cannot be attributed to the EPS loop rather than to the column itself —
and that attribution decides whether ANY firmware lever can ever touch the stuttering.**

**The manoeuvre, repeated:**
1. Get to the target speed on a straight, empty, level road.
2. **Disengage openpilot with the CANCEL BUTTON — not the brake, not by grabbing the wheel.**
3. **Hands off. Foot off the brake.** Hold steady throttle. Let the car track.
4. **Coast 25–30 s.** Re-take the wheel normally at the end.
5. Do **not** re-engage during the run.

**How many, and how long.** Measured yield: 221 windows from 884.5 s = **0.25 qualifying windows per
second** of continuous hands-off time.
| target | qualifying time | runs of 30 s | what it buys |
|---|---|---|---|
| **minimum useful** | **160 s** | **~6** | ~40 windows — a usable but wide estimate |
| **good** | **400 s** | **~14** | ~100 windows — comparable precision to the engaged arm |

**Split the runs across two speed bands so the arm can be compared with the engaged arm at matched
speed: half at 30–50 km/h, half at 60–80 km/h.**

🛑 **What makes a run INVALID** (all of these are screened out automatically, so a spoiled run costs
only time): any brake application · `steeringPressed` true (a hand on the rim registers) · re-engaging
openpilot · speed leaving the band · a gear change · coming to a stop · any steering input.

**Time cost: ~15–20 minutes including turnarounds.**

## 11.2 (c) RING-DOWN — free, because it rides on the same manoeuvre

The record says **1 usable edge in 99**, with **8 of 10 disengagements ending in braking**. That is a
protocol problem, not a data problem, and **§11.1's step 2 already fixes it**: a cancel-button
disengage with hands off and no braking, held 5 s either side, **is** a clean ring-down edge, and it
flows straight into the coast.

⇒ **One manoeuvre serves both.** Just hold ~5 s of steady engaged driving immediately **before**
pressing cancel, so the edge has a defined pre-state. **12–16 runs give 12–16 clean edges**, against
the 1 the entire corpus currently has. **Marginal time cost: zero.**

## 11.3 (b) HIGHWAY CURVES AND LANE CHANGES — to make grind #2 scoreable for the first time

**Why it matters:** the regime the operator names — **engaged, v ≥ 22.2 m/s (80 km/h), |wheel rate|
≥ 5 °/s** — has **7 / 33 / 1 / 6 windows** on routes 73 / 75 / 76 / 77. **No grind-#2 claim is
supportable in either direction**, and the D6c regression that does exist is about 50 km/h+, not
80 km/h+.

**Sizing, from this session's own yields.** Above 80 km/h engaged, route 77 returned 6 qualifying
windows from 42.0 s (**0.143 win/s**) and route 75 returned 33 from 216.1 s (**0.153 win/s**) — the two
roads yield almost identically, so the shortfall is **exposure, not road character**.

⇒ **100 qualifying windows needs ≈ 11 minutes of ENGAGED driving above 80 km/h.** Round up for
traffic: **~15 minutes above 80 km/h, engaged, per build.**

**How to spend those minutes — 🛑 and this CORRECTS what I wrote in the first draft of this section.**
My earlier advice was *"curves beat lane changes for yield — a 30 s curve held at ≥5 °/s gives ~10
windows."* **That is wrong, on two counts, and D6c is what shows it:**
1. **A constant-radius curve does not hold ≥5 °/s.** Once the curve is established the wheel is
   *stationary* at an offset — the wheel rate is near zero. Only the **entry and exit** qualify. A
   steady sweeper contributes almost nothing.
2. **D6c says grind #2 rides WHEEL RATE, not lateral acceleration** (`log|rate|` contrast **+0.553
   [+0.442, +0.651]** at 26–31 Hz on the highway cut; `log|lat accel|` **−0.080 [−0.241, +0.085]`, a
   null). A steady curve is exactly the manoeuvre that is high in lateral load and **low** in the
   covariate that actually carries the symptom.

⇒ **What is wanted is LANE-CHANGE-LIKE CONTENT at v ≥ 22.2 m/s — continuously CHANGING curvature, not
sustained curvature:**
- **Deliberate lane changes are the primary instrument**, not a supplement. Each contributes ~1–2
  qualifying windows and, because they are separated in time, each contributes its own block — which
  is what the bootstrap actually resamples. **Target ~60–80 lane changes** across the session,
  spread out rather than in bursts.
- **Winding highway, cloverleaf ramps and continuously tightening/opening bends** qualify for the same
  reason: their curvature is always changing, so the wheel is always moving.
- **Avoid banking the exposure on long steady sweepers** — they will inflate the ≥80 km/h seconds
  without producing qualifying windows, and the drive will look adequate while yielding nothing.
- **Blocks matter more than windows.** The bootstrap resamples ~10.2 s blocks nested in engagement
  runs; route 77 got **3 blocks** from its 6 windows. **Target ≥ 20 blocks**, i.e. manoeuvres spread
  across many distinct stretches.
- 🛑 **It must be repeated on EVERY build being compared.** A grind-#2 comparison against route 77's
  6 windows is not a comparison. If only one build gets this exposure, the result is a description of
  that build, not a contrast.

**Time cost: ~15–25 minutes of highway driving.**

## 11.4 WHAT THIS PROTOCOL WILL AND WILL NOT DELIVER

**Will:** a real manual hands-off arm for `Re(Z)` (the attribution that decides whether firmware can
touch the stuttering at all) · 12–16 clean ring-down edges against the corpus's 1 · the first
scoreable grind-#2 regime.
**Will not:** narrow the `e_18-22` resolution floor of ±20–33 % — that is set by drive-to-drive
variability, and the only lever on it is **flying V91 on the same route as 77** (§10.2).
**Will not:** settle anything about grind #2 unless the highway exposure is collected on **both** builds
being compared.

---

# 12. DOES AN ORDINARY RETURN-TO-CENTRE REACH THE `0xC520C` BREAKPOINTS? **NO.**

`rlog-tools/v93_return_to_centre.py` (new, read-only) · log `v93_rtc.log` · JSON
`_cache_r77/v93_return_to_centre.json`. Four routes: 77 (V90), 73 (V88), 75/76 (V89).

**The table** (Honda stock, byte-confirmed V37–V74, keyed on motor electrical rate `gp-0x6ac0`, and
**shared** by return-centre `gp-0x6b62` and LKAS's own in-aggregator term `gp-0x6b4c`):
`X = [1050, 1700, 2500, 3700, 4100]` counts → `Y = [5325, 3584, 2406, 1587, 512]` ceiling.

## 12.1 🛑 THE SCALE IS NOT UNKNOWN — the kit settled it on-car
`memory/reference-accord-rate-scale-4p7121-stands.md`: **`gp-0x6ac0` = |column °/s| × 4.7121**,
arbitrated through V74's bit7 (**4.7121 beat 10.0 in 8 of 9 episodes**, engaged agreement 84.74 % vs
82.07 %). A naive fit peaks near 5.8 [5.12, 8.27] but is **upper-biased**, because the estimator
substitutes column for motor rate. The sweep below therefore runs **4.7121 (settled) → 10.0
(disfavoured extreme)** and reports the scale at which the conclusion would flip.

Breakpoints in column °/s: **4.7121 → 222.8 / 360.8 / 530.5 / 785.2 / 870.1** · 10.0 → 105 / 170 /
250 / 370 / 410.

## 12.2 ⚠ RATE-CHANNEL CALIBRATION — and it CORRECTS how my own standing rule could be misapplied
Regressing each bus rate channel on the differentiated **angle** (0x14A, 0.1 °/count — a solid LSB
anchor), over four routes:

| channel | slope vs d(angle)/dt | r |
|---|---|---|
| **`rate_f` (0x18F)** | **0.756 · 0.767 · 0.743 · 0.763** | 0.96–0.98 |
| **`rate_c` (0x14A)** | **0.958 · 0.963 · 0.952 · 0.962** | 0.98–0.99 |

⇒ **`rate_f` reads ~24 % LOW** — the "~25 % low" note is confirmed and pinned to that channel
specifically. 🛑 **The §4 standing rule ("use the `0x18F` rate") is scoped to PHASE and IMPEDANCE work,
where the skew cancels because `tq` and `rate_f` share a frame. It does NOT apply to absolute
magnitude questions, where `rate_c` is the calibrated channel.** §12 uses `rate_c`.

## 12.3 THE MEASUREMENT
Return-to-centre = engaged, `|angle| > 5°`, rate signed **opposite** the angle, `|rate| > 1 °/s`,
sustained ≥ 0.30 s.

| arm | n | seconds | p50 | p75 | p90 | p99 | max |
|---|---|---|---|---|---|---|---|
| r77 engaged | 12,740 | 127.9 | **26.0** | 50.0 | 132.0 | 430.0 | 535.0 |
| r73 engaged | 7,801 | 78.3 | 30.0 | 102.0 | 257.0 | 448.0 | 542.0 |
| r75 engaged | 2,757 | 27.7 | 22.0 | 56.0 | 113.0 | 230.3 | 260.0 |
| r76 engaged | 4,616 | 46.3 | 30.0 | 64.0 | 124.0 | 274.3 | 455.0 |

**★ And the structure that decides it — route 77 engaged returns BY SPEED:**
| stratum | n | p50 | p90 | p99 | **max** |
|---|---|---|---|---|---|
| creep <10 km/h | 4,229 | 31.0 | 193.2 | 467.7 | 523.0 |
| 10–40 km/h | 7,937 | 25.0 | 120.0 | 350.0 | 535.0 |
| **40–80 km/h** | 574 | **11.0** | **22.0** | **28.0** | **35.0** |
| ≥80 km/h | 0 | — | — | — | — |

## 12.4 ⇒ DOES IT BIND? **NO — and by a wide margin.**
Pooled engaged returns (27,914 samples), at the settled scale:
- **median = 127.2 counts ⇒ ceiling 5325 = the FULL value, zero reduction.** The onset is **8.3×
  away**.
- duty above X0 **0.062** · above X1 0.024 · above X2 **0.00018** · above X3/X4 **0.000**.
- Even at the **disfavoured 10.0** scale the median is 270 counts ⇒ **still the full 5325 ceiling.**

**Critical scale — what would have to be true to flip it:** for the *median* return to reach X0 the
scale would have to be **38.89 ct/(°/s) = 8.25× the on-car-arbitrated 4.7121**, and **3.9× beyond the
disfavoured extreme.** The conclusion is not scale-sensitive in any plausible range.

## 12.5 ★ THE REAL BINDING TEST — a falling ceiling only BINDS once it drops BELOW the command
| command being capped | ceiling == command at | in °/s @4.7121 | hardest return seen (542 °/s) |
|---|---|---|---|
| LKAS alone at 4× (1782) | **3414.3 ct** | **724.6** | **NOT reached — 1.3× short** |
| LKAS + base assist aggregate (2229) | 2759.3 ct | 585.6 | **NOT reached — 1.1× short** |
| full governor flat ceiling (4762) | 1260.2 ct | 267.4 | reached |

⊕ **This decodes the prior claim's notation exactly.** `FEASIBILITY-8X-LKAS.md` Part 2 says *"V38
(LKAS alone 1782) binds from z~3414"* — my independent solve gives **3414.3 counts**, four significant
figures. So `z` is the **count**, not a command magnitude, and **their own number requires 724.6 °/s.**

## 12.6 THE PRIOR CLAIM, CHECKED NOT INHERITED — Part 1 CONFIRMED, Part 2 REFUTED
`FEASIBILITY-8X-LKAS.md` contains both of these:
- **Part 1:** *"measured on-car electrical rate at highway cruise (`gp-0x6ac0` peak 329.8, route 59)
  sits well below the adaptive rate-cap's 1050-count onset"* — **CONFIRMED.** My 40–80 km/h engaged
  returns max out at **35 °/s = 165 counts**, even further below.
- **Part 2:** *"even at TODAY's 4×, moderately fast steering already clips here"* — **REFUTED.** It
  requires **724.6 °/s**, which is **1.3× beyond the hardest correction in four routes** and **~28×
  the ordinary return.** Nothing in ~50 engaged minutes plus the manual segments reaches it.

## 12.7 VERDICT AND CAVEATS
> **NO. The `0xC520C` adaptive ceiling does not bind on ordinary return-to-centre.** The mechanism is
> real and correctly traced, but **inert in the operator's regime.** It takes a hard, fast correction
> — **top ~1 % of returns, essentially confined to creep and 10–40 km/h** — to reach even the first
> breakpoint, and **even then the ceiling stays above the command it would have to cut.**
> 🛑 **At 40–80 km/h it is definitively inert: max 35 °/s against a 222.8 °/s onset.**

**Two caveats, pulling in opposite directions, stated so the margin can be judged:**
- `gp-0x6ac0` is **rectified and EMA-filtered** from `gp-0x4f50`, so a filter attenuates transient
  peaks ⇒ my p99/max count estimates are **upper bounds** (this *strengthens* the null).
- The column→motor conversion is **biased low through a torsional mode**
  (`reference-accord-two-dead-zones-speed-and-rate`) ⇒ true motor rate may exceed column × 4.7121 in
  transients (this *weakens* the null at the tail).
⇒ **The median result (8.3× margin) is robust to both. The p99/max results are not, and no conclusion
here rests on them.**

⚠ **This says nothing about whether `0xC6CD0` should move** — that adjudication is the orchestrator's,
and a standing ★★★★★ memory freezes the 4× gain. §12 supplies only the number.
