# ADV-B vs the BUILT V295 image: unit / scale chain and the instrument

Adversary B (subagent), 2026-09-30.
- Nothing was flashed. No CAN was sent. No fork file, STATE, CLAUDE.md, memory, lineage or golden-model file was edited. Nothing was committed.
- FAIL criteria were written before any V295 number was computed: `advB/CRITERIA-ADV-B.md`.
- Every script and output is in `advB/`.
- Claims are marked **[E]** EVIDENCE (with the method) or **[B]** BELIEF.

## 0. Verdict: **PASS_WITH_DEFECTS**. Nothing in my lane is DO_NOT_FLASH.

**The image.** I re-hashed it first: `5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed` (rwd `f42a06bd…eaae87`), and both match. The whole-file diff against V294 is exactly 6 bytes: 0xC63EA–EB `37 02 → 1a 04` and the trailer 0xC6FFC `0xF3441165 → 0x8D982BD9`. The trailer equals `zlib.crc32` of [0xC6000, 0xC6FFC). Every other PID-chain cell is byte-equal to V294, read LE from each file. [E, `b1_bytes.py`]

**The physical claims survive from the bytes, with one unit qualifier.** Every quantity below is per deg/s of **x/8**, the EPS's own rate scale (the 0x14A/0x18F field). It is **not** per deg/s of the steering wheel. On centre the wheel moves 1.16× more than x/8, so the per-steering-wheel numbers are 0.86× the quoted ones. [E, two methods]

**The pre-registered c1/c2 read works.** I re-implemented it on my own byte-exact lane, which reproduces the real r71b tap to 2.25 counts rms. That is the quantiser floor.
- **Pooled over the hands-off drive:** c2 reads 0.989 on V294's real tap and 1.837 on a synthetic V295 tap. An inverted operand reads −1.85.
- **15 s hands-off windows:**
  - null: 0/46 false "live";
  - V295: 1/46 miss (c2 = 1.450 exactly, in a straight-driving window);
  - inverted: 0 windows ≥ 0.

**Four things must change in the read protocol before the drive.** None touches the image.
1. Define "with wheel motion" as an excitation gate. With it, errors are 0 at every window length.
2. Make the analyst's march pass a sign-calibration control on r71b. A flipped x convention in a fresh march turns V294 into c2 −0.99, and the "c2 < 0 → REVERT" rule would fire on an analysis bug.
3. Add an explicit NO-CALL outcome.
4. Tell the operator that no secondary outcome can be decided from one drive.

## 1. FAIL criteria: what fired

| id | result |
|---|---|
| U0 image / cells | **PASS**. The hash matches; 6-byte diff; b = 1050 LE; all other chain cells equal V294's; code region identical (0 bytes) |
| U1 x scale | **PASS**. Bytes: the 0x14A field is gp-0x69ea>>3 and gp-0x69ea = −x. Wire: slope 7.993 counts per deg/s; the integer identity f14 = f18>>3 holds on 94 % of same-batch frames (the remainder is timing) |
| U2 κ | Values PASS: 1.16 on centre, 0.965 beyond 160°. **DEF** fires on the wording: the docstring says "steering-wheel INERTIA" and "each deg/s of wheel rate" with no κ |
| U3 r26 per deg/s² | **PASS**. 0.6462 (closed form = numeric march) |
| U4 T per wire / per op unit | **PASS**. 0.6396 (least squares, wire 0–3686) to 0.6411 (closed form) T per wire; ×4094 wire per unit = 2619–2625. The brief's 2605 is 0.5–0.8 % low: under the 1 % line, a note only |
| U5 K_α | **PASS**. 0.3884 T per deg/s² of x/8 (numeric 0.390) |
| U6 damping | **PASS**. V295/V294 = 1.8519 at every f. 3.37 in phase (3.45 magnitude) at 2.5 Hz, against "~3.4" |
| U7 20 Hz | **PASS**. \|P/x\| 3.850, V294 2.079, ratio 1.852 (< 3). V282 \|(P+D)/x\| 44.900 from its own image; V295 is −21.3 dB below it |
| I0 tap reproduction | **PASS**. 2.25 counts rms hands-off (FF-only 15.2; inverted 29.9) |
| I1 null | **PASS**. False-alarm rate 0 at 10/15/30 s. Median c2 0.98–0.99 |
| I2 positive (PA) | **PASS**. Miss rate 0–2.2 % at ≥ 10 s; median 1.81–1.84 |
| I3 misfire | **DEF**. Under the stress control PB2 (residual scaled with b), ungated 10 s windows miss 8.7 % (> 5 %). The rule's own ≥ 15 s: ≤ 4.5 %. The **post-hoc** excitation gate brings every family to 0 % |
| I4 alignment | **PASS**. −4 / 0 / +4 / +8 ms moves the medians ≤ 0.03 and flips ≤ 2.2 % of windows (PA, low-trim windows only) |
| I5 FF identity on V295 | **PASS** on the 0.90 line (V295 reads 0.965). Note: the identity is **blind to inversion** (inverted reads 0.974) |
| I6 sign leg | **PASS**. The inverted operand reads c2 −1.85 (V295) and −1.00 (V294); no ≥ 10 s window ≥ 0; none > 1.45 at any length |
| I7 secondary outcomes | **Fires against one proposed sentence, not against the build.** ADV-stability-robust-joint §8.2 proposed "an unchanged 0.5–1 Hz error means the waterbed shift did not reach the car"; that sentence is not licensed. The build docstring's sentences are licensed |
| I8 quantiser | **PASS**. The field is sign-magnitude `(T<0)<<9 \| (|T|>>3)`, clamped to [0, 0x3FF]; \|T\| ≤ 3072 gives a field ≤ 384 < 512, so no sign aliasing |

Declared post-hoc items:
- **(a)** My first stress control PB, `quant(quant(N4) + 1.852·(tap − quant(N4)))`, re-quantises a scaled quantised signal. Its truncation passes a ±8 step as ±8 rather than ±14.8, so it compresses small trims. Its 13–25 % miss rate is an artefact of my control. PB2 (one quantisation of `L5 + 1.852·(tap_mid − L4)`) is the honest stress, and both are tabled.
- **(b)** The excitation gate is my proposal, derived after seeing the ungated scatter.

## 2. The unit / scale chain, re-derived from the image

### 2.1 x = 8 counts per deg/s, and of *what*

- **Bytes [E]** (Ghidra decompile first, then the listing, on the V294 program; the V295 code region is byte-identical by Python diff):
  - `FUN_00055a98` @0x55B48 does `ld.h -0x69ea[gp]`, then `>>3`, then passes it to the 0x14A packer. A float plausibility check follows: x·0.125 against ±1500.0, i.e. |x| ≤ 12000.
  - `FUN_00040a50` @0x40C42 does `ld.h -0x6a56[gp]` (x); @0x40C4E `subr r0,r26`; @0x40C50 `st.h r26,-0x69ea[gp]`. So gp-0x69ea = −x.
  - The 0x14A field is therefore (−x)>>3. The docstring's "0x14A field is −x>>3 @0x55B48" is right, but it skips the negated copy; see D4.
  - The packers at 0x557D6 and 0x55C62 publish −x at full resolution (`ld.h -0x6a56` then `subr r0`).
- **DBC [E]**, fork `20d24ab79` opendbc: the Accord uses `honda_civic_hatchback_ex_2017_can_generated`.
  - 0x14A STEER_ANGLE_RATE is (−1) deg/s.
  - 0x18F STEER_ANGLE_RATE is (−0.1) deg/s. **That factor is wrong for this car:** the wire gives −0.125 (a 1.25× error). See D7.
- **Wire, r71b [E]** (`b2_wire_units.py`):
  - The raw 0x14A field equals the raw 0x18F field >> 3 on **0.940** of same-batch frame pairs (0.911 on moving frames). The negated pairing matches on 0.18, so both fields carry −x.
  - x_fw = −(0x18F raw) against carState.steeringRateDeg: slope **7.993** (offset −3.07, the ceil bias of −((−x)>>3)).
- **κ, the steering wheel against x/8 [E]**: d(0x14A angle)/dt over ∫x/8 on 0.5 s spans.

  | \|angle\| | κ |
  |---|---|
  | 0–5° | 1.167 |
  | 5–10° | 1.161 |
  | 10–20° | 1.162 |
  | 20–40° | 1.141 |
  | 40–80° | 1.054 |
  | 80–160° | 0.978 |
  | > 160° | 0.964 |
  | spectral, 0.5–3 Hz on centre | 1.156 |

  - The inherited 1.16 / 0.965 are reproduced.
  - Mechanism [B]: x is rack/motor-side motion behind a variable-ratio rack.

### 2.2 The chain from x to T at b = 1050 [E: closed form = my lane; my lane = golden model on 60,000 ticks per image, 0 mismatches]

| quantity | V294 | **V295** | formula / method |
|---|---|---|---|
| r26 per deg/s² of x/8 (below the pole) | 0.3489 | **0.6462** | 8·b·Ts/(1024−a); constant-α march agrees to 0.01 |
| T per r26 count | 0.6011 | 0.6011 | (960/256)(254/256)(2·507/(32·32))(5346/32768) |
| T per sp count | 2.404 | 2.404 | 15 · 0.1603 |
| T per wire count, sub-rail | 0.641 | 0.641 | closed 0.6411; LS over 0–3686 = 0.6396; V295 = V294 at every point |
| wire per openpilot torque unit | 4094 | 4094 | r71b regression of 0xE4 on carOutput torque |
| T per openpilot torque unit | 2619–2625 | 2619–2625 | not 2605 (D6) |
| rail | +2462 / −2462 | +2462 / −2462 | cold-boot settle; ±1 count against the brief's +2461/−2463 is the output-lag fixed-point interval |
| **K_α, T per deg/s² of x/8** | 0.2097 | **0.3884** | numeric 0.210 / 0.390 |
| K_α per steering-wheel deg/s², on centre (÷1.16) | 0.181 | **0.336** | [E] κ above |
| K_α per steering-wheel deg/s², beyond 160° | 0.218 | 0.404 | |

**T/ω against frequency** (ω = x/8 in deg/s; + means opposing; exact 1 kHz z-domain including the output lag; lock-in on my lane matches to 4 digits at 2.5 and 20 Hz):

| f (Hz) | V294 \|T/ω\| | V294 phase | V294 damping | **V295 \|T/ω\|** | **V295 damping** | V295 inertia (T/deg/s²) |
|---|---|---|---|---|---|---|
| 0.3 | 0.390 | +78° | 0.080 | 0.723 | 0.148 | 0.376 |
| 1 | 1.160 | +53° | 0.704 | 2.148 | 1.304 | 0.272 |
| 2 | 1.747 | +24° | 1.598 | 3.235 | **2.959** | 0.104 |
| 2.5 | 1.863 | +13° | 1.817 | 3.450 | **3.365** | 0.049 |
| 3 | 1.907 | +3° | 1.904 | 3.532 | **3.526** | 0.011 |
| 5 | 1.764 | −23° | 1.629 | 3.267 | 3.017 | −0.040 |
| 20 | 0.652 | −70° | 0.223 | 1.208 | 0.412 | −0.009 |

- The ratio is 1.8519 at every frequency.
- Per steering-wheel deg/s on centre at 2.5 Hz: 1.566 → **2.901**.
- The docstring's "~97 % in phase at the 2–3 Hz wheel mode" holds at 2.5 Hz (97.5 %). It is 91 % at 2 Hz and 99.8 % at 3 Hz.

**|P/x| at 20 Hz** (P counts per x count, each image's own cells):

| image | \|P/x\| | \|(P+D)/x\| |
|---|---|---|
| V282 (sum operand, shl 5, Kp 248, Kd 128) | 19.038 | **44.900** |
| V294 | 2.079 | 2.079 |
| V295 | **3.850** | 3.850 |

V295 is ×1.852 of V294 and −21.3 dB below V282.

**The C clamp at b 1050 [E].**
- r26 reaches C = 1024 at:
  - 1585 deg/s² below the pole;
  - 177 deg/s at 2 Hz;
  - 161 deg/s at 2.5 Hz;
  - 125 deg/s as the HF asymptote.
- The docstring's "~118 deg/s" is the b 1106 figure.
- On r71b's recorded motion V295 sits at C on **69 ticks (0.0068 %)**; V294 on 0.
- My first lock-in at x = 2000·sin (250 deg/s at 2.5 Hz) ran V295 into the clamp and read 0.33 against the linear 0.43. That is the clamp, not a defect, and the table uses x = 500.

**Physical anchor of the fault-path numbers [E, arithmetic].** The restart-pulse cap's "100 deg/s" is x/8. That is 116 deg/s of steering wheel on centre and 96.5 beyond 160°. The int32 margin and the restart cap depend only on counts (|x| ≤ 12000, a, b, C, Kp), so no scale factor moves them.

## 3. The instrument (`b4_marches.py`, `b5_instrument.py`, `b6_identity.py`, `b8_second_method.py`)

**Marches [E].** My own lane (`advb_lane.py`, written from my Ghidra decompile of FUN_00028ea6, cells from each image) runs at 1 kHz on r71b's raw CAN.
- **Inputs:**
  - the 0xE4 bus-129 wire, zero-order held;
  - the request bit;
  - x = −0x18F raw, linear-interpolated at t18 − δ;
  - bar = 0x18F torque × 1.024;
  - the ramp, +33 per tick.
- **Marches:**
  - N4: V294 with r26 forced to 0;
  - L4: V294 live;
  - L5: V295 live;
  - I5 / I4: operand inverted.
- **Checks:**
  - N5 (V295 FF-only) == N4 on all 1,020,412 ticks: b is not read at r26 = 0.
  - The tap is sampled at round((tap_t − δ − t0)/1 ms).

**I0: which march reproduces the real tap** (hands-off settled frames, rms counts):

| δ (ms) | x | live L4 | FF only | inverted |
|---|---|---|---|---|
| −8 | lin | 4.68 | 15.8 | 30.3 |
| −4 | lin | 3.63 | 15.5 | 30.1 |
| 0 | lin | 2.59 | 15.3 | 30.0 |
| **+4** | **lin** | **2.25** | 15.2 | 29.9 |
| +8 | lin | 2.90 | 15.2 | 29.9 |
| 0 | zoh | 2.86 | | |

- On |trim| ≥ 24 frames: live 5.2, FF-only 63.7, inverted 126.7.
- **The byte-derived loop sign is right**, and the residual is at the tap's quantisation floor.
- **The "−4/0 ms" question, answered [E].** The kit's dejittered tap times sit 4.42 ms (median) before the raw batch times. My best δ is +4 ms on raw times, which is the same instant. Nothing in the c2 read depends on it (§3.3).

### 3.1 Per-window c1/c2 (δ +4 ms, x lin; rule c2 > 1.45)

Series:
- NULL = the real r71b tap;
- PA = tap + quant(L5) − quant(L4);
- PB2 = quant(L5 + 1.852·(tap_mid − L4)), the stress in which the whole residual scales with b;
- INV5 = tap + quant(I5) − quant(L4).

| windows | n | NULL c2 median [p5, p95] | null false alarm | PA c2 | PA miss | PB2 miss | INV5 c2 | INV5 ≥ 0 |
|---|---|---|---|---|---|---|---|---|
| HO 5 s | 139 | 0.99 [0.77, 1.14] | 0.7 % | 1.79 [1.13, 1.89] | 10.8 % | 12.2 % | −1.81 | 0 |
| HO 10 s | 69 | 0.99 [0.85, 1.06] | 0 | 1.81 [1.55, 1.87] | 2.9 % | **8.7 %** | −1.82 | 0 |
| **HO 15 s** | 46 | 0.98 [0.87, 1.02] | **0** | 1.81 [1.64, 1.85] | **2.2 %** | 2.2 % | −1.83 | 0 |
| **HO 30 s** | 23 | 0.98 [0.89, 1.01] | **0** | 1.83 [1.73, 1.85] | **0** | 0 | −1.85 | 0 |
| ALL 15 s contiguous | 48 | 0.97 [0.85, 1.03] | 0 | 1.80 [1.63, 1.86] | 0 | 4.2 % | −1.83 | 0 |
| ALL 30 s contiguous | 22 | 0.97 [0.90, 1.00] | 0 | 1.82 [1.70, 1.85] | 0 | 4.5 % | −1.85 | 0 |
| **hard turn ±10 s, all engaged** | 12 | 0.98 [0.97, 1.01] | 0 | **1.83 [1.81, 1.86]** | 0 | 0 | −1.85 | 0 |
| **pooled hands-off 695 s** (10 s block bootstrap) | – | **0.989 [0.977, 0.999]** | – | **1.837 [1.829, 1.844]** | – | 1.840 [1.822, 1.857] | **−1.851** | – |

- **c1 reads 0.991** pooled on every series; 15 s windows 0.945–0.997.
- **INV4** (V294, operand inverted) reads −1.00.

### 3.2 Why the ungated misses happen, and the gate that removes them [E]

- **Where the misses are:** every PA miss and every low PB2 value sits in a window whose V294 trim regressor has rms < 4 counts, i.e. less than half a tap LSB of straight driving. There the truncating quantiser dominates. The 21 such 15 s windows read PA c2 1.45–1.86; the 25 others read 1.74–1.86.
- **The gate:** score a window only if rms(TRIM_V294) ≥ 4 counts.

| gated windows | qualify | NULL c2 range | PA min | PB2 min | errors |
|---|---|---|---|---|---|
| HO 5 s | 64/139 | [0.88, 1.06] | 1.61 | 1.61 | **0** |
| HO 10 s | 34/69 | | 1.72 | | **0** |
| HO 15 s | 25/46 | [0.94, 1.01] | 1.74 | 1.73 | **0** |
| HO 30 s | 15/23 | | | | **0** |
| ALL 15 s | 30/48 | | | | **0** |
| ALL 30 s | 15/22 | | | | **0** |
| ALL 15 s sliding | 177/285 | | | | **0** |

- Hard-turn windows always qualify.
- **Second method, model selection with no regression** (`b8`): which image's march reproduces the tap by rms?
  - Real tap: V294 2.25 against V295 12.97.
  - PA: V295 2.25 against V294 13.25.
  - Gated 15 s windows pick the right image 25/25 in every case.
  - **Ungated PB2 picks V295 only 32/46.** The rms method needs the gate even more than c2 does.

### 3.3 Alignment and reconstruction [E]

- Over δ ∈ {−4, 0, +4, +8} ms the median c2 moves ≤ 0.025 (null) and ≤ 0.024 (PA).
- The call flips on 0 % (null) and ≤ 2.2 % (PA, low-trim windows) of 15 s windows.
- Using x by zero-order hold instead of linear interpolation changes the pooled null c2 by 0.001.
- Quantised against continuous regressors: pooled null 0.995 against 0.989; PA 1.811 against 1.837.
- Adding a sign(FF) truncation term moves nothing material.

### 3.4 The FF identity on the synthetic V295 tap (I5) [E, the kit's `v293_flight_read.identity_block`, V293 cells, bar fade]

| tap | all engaged R² | resid | on frames with \|V294 trim\| < 8 counts |
|---|---|---|---|
| real (V294) | 0.9868 | 22.4 | 0.9974 |
| **V295 PA** | **0.9652** | 36.3 | **0.9966** |
| V295 PB2 | 0.9650 | 36.4 | 0.9960 |
| **V295 inverted** | **0.9736** | 33.0 | 0.9968 |
| V282 cells (negative control) | −0.79 to −1.12 | | |

- Keep the inherited line at **0.90** on all engaged frames: V295 is expected at 0.965.
- Tightening to 0.98 would misfire on the correct image.
- The b-independent form is **R² ≥ 0.99 on |TRIM_V294| < 8 frames**.
- **The identity cannot see an inverted operand** (0.974). The sign is c2's job alone.

### 3.5 The V294 attribution's E3 estimator does not discriminate V295 [E by linearity; B for the exact figure]

- E3 is linear in the trim gain. The attribution's own additive control ("the real tap plus a second synthetic trim") read +0.387.
- A V295 flight should therefore read about 0.21 × 1.852 ≈ 0.39.
- Its LIVE line (> +0.10) fires for V294 and V295 alike. If E3 is reused, the V295 discriminator is β > 0.30.

## 4. Secondary outcomes: what ONE drive can and cannot decide (`b7_secondary.py`)

r71b, hands-off engaged, 5 s blocks (hard-turn episodes for HARD16), 2000 draws.
- "vs r71b" = a pseudo-drive of exposure E against a pseudo-drive of the full route.
- "d-v-d" = two independent pseudo-drives.
- **A within-route bootstrap is a LOWER bound on real drive-to-drive scatter** [B: different roads, different fork state].

| outcome | r71b value | no-change 90 % at E | prediction (design / ADV, b 1106) | can one drive decide? |
|---|---|---|---|---|
| 1.6–3 Hz hard-turn wheel rate, 5–15 m/s | 13.6 deg/s over 29.8 s | 15 s ×0.76–1.29 (d-v-d 0.73–1.33); 30 s ×0.80–1.24 (0.81–1.25). One episode against another ×0.50–2.00 | down, ×0.68–0.93 (nominal ×0.83) | **No.** An unchanged band licenses nothing. Only a fall below ~×0.73 is outside even this lower-bound scatter [B] |
| 0.5–1 Hz lat-accel error, 0–10 m/s (plan − act) | 0.058 m/s² over 253 s | 60 s ×0.42–1.66; 120 s ×0.57–1.57; **300 s ×0.70–1.48** | UP ×1.04–1.40 | **No, even with 5 min.** An unchanged value does NOT mean "the waterbed shift missed the car" |
| same, des − act | 0.046 | 300 s ×0.72–1.39 | same | No |
| 1–3 Hz rate, 15–22 m/s | 3.1 deg/s | 120 s ×0.39–2.37 | down ×0.75–0.99 | No |
| tracking gain 5–10 / 15–22 m/s | 0.873 / 0.830 | 120 s ±0.06 | ±0.004 | No: uninformative about V295 |
| turn-hold by band | 0.46–0.96 | 120 s ±0.12–0.15 | −0.009..+0.014 | No |

## 5. Defects and notes (reports; I changed nothing)

- **D1 [DEF, U2: units].** The docstring §0/§0b ("8.00 counts per deg/s", "steering-wheel INERTIA", "each deg/s of wheel rate"), the brief and the page quote K_α and the damping per deg/s of **x/8**.
  - Per steering-wheel deg/s on centre the numbers are ÷1.16: K_α 0.336 (not 0.388) and damping 2.90 T per deg/s at 2.5 Hz (not 3.4).
  - Beyond 160° they are ×1.04.
  - The ×1.852 ratios are unaffected.
- **D2 [DEF, I3: the rule].** "c2 > 1.45 on ≥ 15 s of engaged frames with wheel motion" does not define *wheel motion*.
  - Ungated, a live V295 can read 1.45 in a straight-driving 15 s window, and the stress case misses 8.7 % at 10 s.
  - Define the gate as rms(TRIM_V294) ≥ 4 counts per window: 0 errors at 5, 10, 15 and 30 s.
  - Add NO CALL for a drive with no qualifying window.
- **D3 [DEF: sign-rule hazard on the analyst side].** "c2 < 0 → SIGN INVERTED; REVERT" fires identically if the flight-read agent's fresh march uses x = +0x18F raw, where the bytes say −raw.
  - OLS on a negated regressor gives −c2, so V294 would read −0.99 and V295 −1.84 [E by construction].
  - The protocol must require the analyst's code to reproduce r71b first: pooled c2 0.99 ± 0.03, rms 2.25 ± 0.5.
- **D4 [note: citation].** 0x55B48 is `ld.h -0x69ea[gp]`, not a read of x. The negation is at 0x40C4E (`subr r0,r26`), stored at 0x40C50. The claim is right; the citation skips a hop.
- **D5 [note].** The docstring's "~118 deg/s of 2 Hz-band rate" is the b 1106 figure.
  - At 1050 the numbers are 125 deg/s (HF asymptote), 161 at 2.5 Hz and 177 at 2 Hz.
  - The docstring also says normal driving does not reach it. On r71b's recorded motion V295's r26 hits C on 69 ticks (0.0068 %).
- **D6 [note, < 1 %].** T per openpilot torque unit is 2619–2625 (image × wire), not 2605. `artifact/page_data.py` uses 2605 in LIGHT_B while `plant/v294_plant.py` uses 2625.4.
- **D7 [note: tooling trap].** The Accord DBC's 0x18F STEER_ANGLE_RATE factor (−0.1) is wrong for this EPS; the wire gives −0.125. Decoding 0x18F through the DBC gives 10 counts per deg/s, and every per-deg/s number would be off by 25 %.
- **D8 [DEF against a proposal, not the build].** ADV-stability-robust-joint §8.2's proposed null sentence ("an unchanged 0.5–1 Hz error means the waterbed shift did not reach the car") is not licensed; see §4. Do not adopt it.
- **D9 [note].** The regressor must be **V294's** trim (b 567).
  - Regressing on V295's own trim moves the expected values to 1.00 (V295) and 0.54 (V294), which needs a 0.78 threshold.
  - The docstring says FF_V294 / TRIM_V294 explicitly. Keep it that way in the flight read.
- **D10 [note: the rail].** My cold-boot settle reads +2462/−2462 on both images, against the brief's +2461/−2463. The difference is 1 count from the output lag's fixed-point interval. It is identical between V294 and V295.

## 6. THE PRE-REGISTERED V295 WIRE READ: protocol for the flight-read agent

1. **Route.** Key it by the full `counter--hash`. The image is attributed only by steps 5–6. The label, the date and the fork state are not evidence.
2. **Decode** (bus 1 ECU frames, bus 129 for the 0xE4 echo):
   - `wire` = i16be(0xE4 bytes 0–1);
   - `req` = 0xE4 byte 2 bit 7;
   - `x` = −i16be(0x18F bytes 2–3), in counts, which is x itself;
   - `bar` = i16be(0x18F bytes 0–1) × 1.024;
   - `tap` = (−1 if fld ≥ 512 else +1)·(fld & 511)·8, where fld = ((0x1AB b0 & 3) << 8) | b1.
   - Do **not** use the DBC factor for 0x18F.
3. **Marches.**
   - **Cells:** V294 cells read LE from the **V294 image** `3143616d…`, with b = **567**.
   - **Time base:** 1 kHz grid from the first 0x18F frame. `wire` and `req` are zero-order held. `x` and `bar` are linearly interpolated at (0x18F time − 4 ms). The ramp climbs +33 per tick after the request rises.
   - **Lane:** `advb/advb_lane.py`, which is tick-equal to the golden model's `lkas_fb_lag` + `lkas_rate_pid_tick`.
   - **Series:** N4 has r26 forced to 0; L4 is live.
   - **Tap sampling:** T is sampled at tick round((tap_t − 4 ms − t0)/1 ms).
   - **Regressors:** FF = N4 and TRIM = L4 − N4 at those ticks.
4. **Mandatory calibration first** (it catches the D3 sign trap and any lane error). Run the identical code on r71b `…00000071--a7b8ba5d9d`. It must give:
   - pooled hands-off c2 in [0.96, 1.02];
   - c1 in [0.97, 1.01];
   - rms(tap − quant(L4)) ≤ 3.0.
   If it does not, **stop**: the analysis is wrong, not the car.
5. **Frames.**
   - Settled lateral engagement = 0xE4 req & 0x18F SCA held ≥ 2.0 s before and ≥ 0.3 s after the frame.
   - Hands-off = settled and not carState.steeringPressed, dilated by ±0.5 s.
6. **Primary read: pooled.** OLS `tap = c0 + c1·FF + c2·TRIM` over all hands-off frames, with a 95 % CI from a 10 s block bootstrap.
   - Expected: V295 c2 **1.84** (CI about ±0.01–0.02), c1 **0.99**. V294 would read c2 0.99.
   - Rules:
     - CI entirely > 1.45 → **b 1050 LIVE**;
     - CI entirely < 1.45 and > 0 → **NOT V295; stop**;
     - c2 < 0 (after step 4 passed) → **INVERTED; revert to V294's rwd `a2b418f0…`**;
     - CI straddling 1.45 → **NO CALL**.
7. **Per-window read** (for a short drive). Windows are 15 s of hands-off exposure, or ±10 s around each hard turn at 5–22 m/s using all engaged frames.
   - **Score a window only if rms(TRIM) ≥ 4 counts.**
   - Rule c2 > 1.45 → live.
   - Measured on r71b: 0 errors in 25 (15 s), 34 (10 s) and 64 (5 s) gated windows; hard-turn windows 12/12, V295 1.81–1.87 against null 0.97–1.02.
   - No qualifying window → **NO CALL** ("drive again with turns").
8. **c1** must lie within [0.94, 1.00] per 15 s window, or 0.99 ± 0.01 pooled: the FF did not move.
9. **Second method (agreement required).** The V295 march (b 1050, same code) must reproduce the tap better than the V294 march. Pooled rms: V295 about 2.3 against V294 about 13, on gated windows.
10. **FF identity** (inherited gate). R² ≥ 0.90 on all engaged frames (expect 0.965), or ≥ 0.99 on |TRIM| < 8 frames. **Do not tighten to 0.98.** It cannot detect inversion.
11. **Null sentences:**
    - *Live:* "b 1050 is on the car and delivers 1.85× V294's trim." Nothing about symptoms.
    - *Not V295:* "this drive did not run V295's trim; nothing about V295 is licensed."
    - *Hard-turn 1.6–3 Hz band unchanged:* licenses nothing. The one-drive no-change scatter is ×0.76–1.29 at 15 s and ×0.80–1.24 at 30 s, and it contains the prediction.
    - *Low-speed 0.5–1 Hz error unchanged, or up:* cannot confirm or refute the predicted ×1.04–1.40. Even 300 s of 0–10 m/s spans ×0.70–1.48.
    - *Tracking / turn-hold:* uninformative (±0.06–0.3 against predicted ±0.01). The loose complaints are untested by this build (c1 = 1).
    - **The operator's words ("grinding", "stutter", "jerky", "loose") are his to score. The instrument only says whether b is live.**
    - Revert signature (docstring): grinding or stutter, or a new 5–30 Hz line on the tap or 0x18F.

## 7. Files (`analysis-2020accord/studies/v295/adversarial/advB/`)

| file | what |
|---|---|
| `CRITERIA-ADV-B.md` | the FAIL criteria, written first |
| `advb_lib.py` | image load and hash, LE reads, raw V850 gp/tp scanner (controls 0x55B48, 0x28F86) |
| `_ghidra_v294_FUN_00028ea6.c` | my Ghidra decompile of the lane (V294 program; the V295 code is byte-identical) |
| `advb_lane.py` | my integer lane, cells from the images |
| `b1_bytes.py` / `_out.txt` | hash, full diff, CRC, cells V294→V295, x-chain scan |
| `b2_wire_units.py` / `_out.txt` | integer identity, slopes, κ, wire per torque unit, DBC factors |
| `b3_units.py` / `_out.txt` | golden cross-check, surface, K_α, T/ω table, lock-in, 20 Hz for V282/V294/V295 |
| `b4_marches.py` / `_out.txt` | the 1 kHz marches (δ −8…+8 ms, lin/zoh); npz in `_scratch/` (gitignored) |
| `b5_instrument.py` / `_out.txt` / `.json` | the c1/c2 read: windows, controls, gate, alignment, clamp |
| `b6_identity.py` / `_out.txt` | the FF identity on real, synthetic and inverted taps |
| `b7_secondary.py` / `_out.txt` / `.json` | secondary-outcome no-change scatter |
| `b8_second_method.py` / `_out.txt` | model-selection read |
