# DESIGN — V293: TORQUE MODE (the LKAS rate feedback forced to zero)

**Agent `tmdesign`, subagent of `main`, 2026-09-13. DESIGN STUDY ONLY — nothing was built, flashed, or
sent on any bus; no build script was edited; no image was written; nothing was committed or pushed.**

Base: **V282**, image `_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`.
Every cell below was read **little-endian from that image** (and from the V292 and V279 rev 2 images for
comparison), never from a build script's constants or docstring.

Every decision-bearing claim is marked **EVIDENCE** (with its method) or **BELIEF**. Citations are by
file + heading or grep string, never by line number.

**Scripts** (all under `rlog-tools/studies/grind/`, all analysis-only):
`v293_lib.py` · `v293_s1_surface.py` · `v293_s2_replay.py` · `v293_s3_gate7.py` · `v293_s4_highangle.py` ·
`v293_s5_ringdown.py` · `v293_s6_outer.py` · `v293_s7_anchor.py` · `v293_s8_r24_bothpoles.py` ·
`v293_s9_prereg.py` · `v293_s10_clamp.py`. Outputs in `rlog-tools/studies/grind/_scratch/v293_*.txt`.

---

# 0. THE ANSWER, IN ONE PAGE

**Torque mode is the strongest-supported candidate this kit has produced for the grinding, and the
support is not a model — it is the operator's own wire.** But the candidate as briefed has one real
defect, one open risk that no analysis here can close, and one lever inside it that turns out to carry
almost the whole grinding benefit.

| | |
|---|---|
| ⭐ **The ring** | On the record's own best-constrained plant family (reproduces BOTH the measured V282 pole and the measured V289 pole), removing the LKAS feedback takes the 20 Hz mode from **ζ 0.030 → 0.300** (κ 0.20) / **0.031 → 0.325** (κ 0.10) / **0.037 → 0.157** (κ 0.45). The byte-exact replay on the operator's own 10 loudest recorded episodes reads **wheel-rate ring ×0.28** [0.27, 0.30]. **And the car has already measured it**: the engaged ÷ disengaged 18–22 Hz ratio on V282's own routes is **3.48–4.20**, whose reciprocal — **×0.24 to ×0.29** — is what an open lane does, measured, not modelled. Three independent methods, one of them on-car. |
| 🛑 **The price, and it is on the operator's own complaint** | The **5–9 Hz wheel motion rises ×1.74–1.85** across the r24 arms (**×1.82** [1.80, 1.84] at the recommended arm; ×1.78 on r6c) on the same episodes, because V282's loop is a **disturbance-rejecting servo below ~13 Hz** and opening it removes that rejection. `gate73` with the servo arm deleted is **1.19 vs an allowance of 1.01** and vs **1.0526**, the configuration whose strong-turn ripple the operator *felt*. The r24 cut that buys the gate back is **0xC6446 = 4451, −15.1 %** — and it buys back **almost none of the ×1.8**. |
| ⭐ **And in torque mode that r24 cut is FREE** | With the servo present, cutting r24 costs 20 Hz damping (paired Δζ **−0.044 / −0.075 / −0.086** at κ 0.10 / 0.20 / 0.45 — the record's own finding, reproduced here **to four decimals**). With the servo **gone**, removing r24 **RAISES** ζ (paired **+0.036 / +0.097 / +0.183**, on 96 / 96 / 100 % of plants). **r24's apparent 20 Hz damping was a partial cancellation of the servo's de-damping; delete the servo and it evaporates.** That is new, and it is what makes the 7.3 Hz gate affordable here and nowhere else. |
| 🛑 **The candidate's defect** | **Kp 119 is the right number for the wrong reason.** It is not "authority-neutral": on the recorded episodes V293's delivered-torque rms is **×0.82** of V282's, and on loaded high-angle turns it is **×3.6** (1575 vs 436 counts, because V282's servo has already nulled). Kp 119's real justification is that it makes V293's cmd→torque slope **0.6356 counts/count**, which is **V279 rev 2's own surface** (0.645) — the configuration that already passed five adversaries. Say that, not "peak-neutral". |
| 🛑 **The risk nothing here can close** | **The one out-of-sample test of this predictor FAILED.** The same replay machinery predicted V292's ring at ×0.55; the wire read the route-normalised loop contribution **UP ×1.20–2.00**. I reproduced the published V292 prediction with my own implementation (×0.535), so the failure is the **method's**, not a coding difference. §2.4. |
| ⭐ **The lever inside the lever** | Sweeping `0xC62E6` from 46080 to 0 with Kp 119 / Kd 0 held moves the wheel ring only **×0.299 → ×0.272**. **~90 % of the grinding benefit is Kd = 0 and Kp 119, not the clamp.** The clamp is what changes the *delivered quantity* — the session's other goal — and it is nearly free on the ring. That decomposition should be in the operator's hands before he decides. |
| 🛑 **No intermediate dose exists** | `0xC62E6` is a **clamp, not a gain**. A small non-zero value is not "less feedback": it is a **Coulomb relay** on the sign of the wheel rate. Swept byte-exact at 256/512/1024/2048/4096, every value is **worse than zero on every column**, and with the command frozen the relay **ADDS** 18–22 Hz (×1.005–1.079) and 5–9 Hz (×1.02–1.10) motion rather than damping it. **The cell is effectively binary and 0 is the right end.** §7.2. |
| ✅ **openpilot's outer loop is NOT the risk** | At the operator's live tune (LAF 6.0, Kp 0.9, Ki 0.30) V293's outer margins are indistinguishable from V282's: Ms 1.09–1.38 vs 1.04–1.35, phase margin 64° vs 66° at 28.5 m/s. **No cell in the 6 × 3 × 3 grid reproduces V276's 2–4 Hz signature that V282 does not also reproduce.** The V276 shape comes back not as a margin failure but as a **feedforward mis-scaling of ×3.2 at 5 m/s**. §5. |
| ✅ **The stall class is removed, arithmetically** | On r31's own recorded stall window the P-rail duty goes **0.66 → 0.000** and the 6–8.5 Hz torque ripple **638.7 → 131.1** (×0.21). There is no feedback ripple in `E` to desaturate on. §4. |

**Recommendation, and it is a recommendation about what to put in front of the operator, not a
clearance:** the class is worth flying, at **`0xC62E6` = 0 · Kd bank = 0 · Kp flat 119 · `0xC6446` = 4451**,
**with the fork's `AccordRatePlantFF` OFF and `SteerKP` at 0.3** — and with §7's decomposition shown to
him first, because the honest reading is that he is being asked to accept a measured ×1.75 rise in the
5–9 Hz band (the stutter band he has just called worse) in exchange for a modelled-and-measured ×0.25
fall in the 18–22 Hz band. §7.4 states what I would do instead.

---

# 1. THE DELIVERED SURFACE, BYTE-EXACT (`v293_s1_surface.py`)

## 1.1 The cells, read from the images

| cell | V282 | V292 | V279 rev 2 | **V293** | what it is |
|---|---|---|---|---|---|
| `0xC62E6` | 46080 | 46080 | **0** | **0** | LKAS PID feedback saturation clamp, ×256 |
| Kd bank (`0xCB7D4`→slot 7) | 128×4 | 128×4 | **0×4** | **0×4** | the rate PID's derivative schedule |
| Kp bank (`0xCB994`→slot 7) | 248×5 | 248×5 | 256×5 | **119×5** | the proportional schedule |
| `0xC6446` | 5244 | 4725 | — | **4451** | the r24 engaged rate-lane arm |
| `0xC63E8`/`EA` | 923/1560 | 962/958 | 923/1560 | **923/1560** (stock) | the feedback lag pole, 16.53 Hz |
| `0xC63EC`/`EE` | 992/507 | 992/507 | 992/507 | **992/507** (stock) | the output lag pole, 5.05 Hz, in-loop |
| gain (`0xC6CD0` via `0x2A1F0`) | 5346 | 5346 | 5346 | **5346** | forward LKAS gain, Q15 |
| `0xC61BC`/`BE`/`B6`/`B4`/`B2` | 15360/15360/10240/3072/3072 | same | same | **same** | P / sum / D / output / pre-gain clamps |
| map (`0xC9A88`→slot 7) | 0…**1032** | 0…1032 | 0…**480** | **0…1032** (V282's) | the assist map |
| `0xC63E6` (Ki) | 0 | 0 | 0 | **0** | the integral gain |

**Everything else is V282, byte for byte. No code byte moves; this is the cal-only class every success
since V29 belongs to.** [EVIDENCE — cells read by `v293_lib.read_cells` from each image.]

## 1.2 Five positive controls, run before any V293 number

| check | this session | the record's published value |
|---|---|---|
| `min((15360·5346)>>15, 3072)` | **2505** | 2505 (`V282-CUMULATIVE-NONSTOCK-DELTA` §2) |
| `min((15360·891)>>15, 512)` | **417** | 417 (same) |
| `P = (32·2·idx·256)>>8 == 64·idx` ∀ idx 0…240, P(240) | **True, 15360** | V279's published identity |
| output-lag DC = `2·507/((1024−992)·32)` | **0.990234375** | `design290b.dc_held_lag` |
| closed-form surface vs a byte-exact tick march to steady state | **max \|diff\| = 1 count** | — |

**All five pass.** [EVIDENCE — `_scratch/v293_s1_surface.txt`.]

## 1.3 Why Kp 119 — and the better reason than the brief's

With `fb ≡ 0`, `P = (32·sp·Kp)>>8` and the P clamp is 15360:

| Kp | P at idx 240 | clips? | `sp_rail` | `idx_rail` | 0xE4 rail |
|---|---|---|---|---|---|
| **119** | 15351 | **no** | 1032.6 | **240** | **3870 (94.5 %)** |
| 120 | 15480 | yes | 1024.0 | 238 | 3840 |
| 160 | 20640 | yes | 768.0 | 179 | 2880 (70 %) |
| 248 | 31992 | yes | 495.5 | 115 | 1859 (**45.4 %**) |

So Kp 119 is the largest integer that keeps the surface linear to full command. **But its real
justification is different and stronger: it reproduces V279 rev 2's delivered surface.**

```
V293 : T(idx 240) = 2461 counts at 3870 CAN counts  =>  slope 0.6360 EPS counts per CAN count
V279 : the lineage's own published slope                            0.645
```
⭐ **V293 at Kp 119 on V282's ×6 map is the SAME TORQUE ACTUATOR as V279 rev 2, reached by a different
pair of cells.** V279 rev 2 passed five independent attackers with that surface. **That is the argument
for Kp 119, and it is not the one the brief gives.** [EVIDENCE — surface computed from the V293 cells;
V279's slope from `BUILD-LINEAGE.md` §*"V279 — PURE FEEDFORWARD"*.]

## 1.4 The surface, and what "authority" means in each of three senses

`T(idx)` in EPS torque counts at the CAN-427 tap, fade `m` = 254 (no driver torque):

| idx | 0 | 12 | 24 | 48 | 96 | 115 | 160 | 240 |
|---|---|---|---|---|---|---|---|---|
| reference rate deg/s | 0 | 6.5 | 12.9 | 25.8 | 51.6 | 61.8 | 86.0 | **129.0** |
| 0xE4 of 4096 | 0 | 194 | 387 | 774 | 1548 | 1854 | 2580 | 3870 |
| **V293 (Kp 119, fb 0)** | 0 | **124** | **246** | **493** | **985** | 1179 | 1641 | **2461** |
| V282 at fb = 0 (wheel still) | 0 | 259 | 512 | 1026 | 2052 | 2457 | 2463 | 2463 |
| V282, wheel 10 deg/s | 384 | 254 | 125 | 643 | 1669 | 2073 | 2463 | 2463 |
| V282, wheel 15 deg/s | 575 | 446 | 317 | 451 | 1477 | 1881 | 2463 | 2463 |
| V282, wheel 20 deg/s | 767 | 638 | 509 | 259 | 1285 | 1689 | 2463 | 2463 |
| V282, wheel 45 deg/s | 1727 | 1598 | 1468 | 700 | 326 | 730 | 1692 | 2463 |

**Peak: V293 2461 vs V282 2463 at the same idx — ×0.9992. The structural ceiling 2505 is unchanged and
neither build reaches it at fade 254.** [EVIDENCE — closed form; the byte-exact tick march reads 2461
and 2462, i.e. the two methods agree to ONE COUNT, and the march is the authority.]

⚠ **A defect of mine, found and fixed during this write-up rather than after it.** My first closed form
computed `floor(y·gain/32768)` and negated, where the ECU's `sar 0xf` after `mul` is an ARITHMETIC shift
and therefore `floor(−y·gain/32768)`. `floor(−x) ≠ −floor(x)`, so the table above shifted by 1 count when
it was corrected. No conclusion in this document depends on it, and the byte-exact march — which was
always right — is what every §2/§4 number was computed from.

🛑 **"×1.00 of V282's authority" is true of the PEAK and of nothing else.** Three different senses:

1. **Peak torque** — ×0.9992. Preserved.
2. **Torque at a given command with the wheel still** — ×0.48 below idx 115, rising to ×1.00 at 240.
3. **Torque delivered on the operator's actual episodes** — **×0.82** rms on r39's grinding windows, and
   **×3.6** on loaded high-angle turns (§4), because V282's servo nulls there and V293 does not.

**Sense 3 is the one the operator drives.** No single Kp makes all three ×1.00, because V282's delivered
torque is not a function of the command at all. [EVIDENCE — `v293_s1_surface.py`, `v293_s2_replay.py`.]

## 1.5 The fade, read from the image, and what the driver feels instead of a servo

`0xCBBC4` slot 7: X (`|bar|>>5`) = 16, 26, 38, 48, 64, 96 · Y = 255, 243, 218, 179, 77, 77.

| \|bar\| raw | m = (255·B)>>8 | V293 peak T | V282 peak T |
|---|---|---|---|
| 0–400 | 254 | 2460 | 2462 |
| 800 | 243 | 2353 | 2355 |
| 1200 | 219 | 2121 | 2122 |
| 1600 | 165 | 1598 | 1599 |
| 2000 | 89 | 861 | 862 |
| ≥ 2400 | 76 | 736 | 736 |

**The fade is the same LERP on both builds and multiplies both surfaces identically.** It is the ONLY
thing that backs a torque-mode lane off for a driver — there is no error term left to do it.

**What the driver feels**: at idx 48 the reference asks 25.8 deg/s. V282 delivers **35** counts once the
wheel is at that rate and **0** at the null rate of 26.7 deg/s. V293 delivers **492** counts and keeps
delivering them. Against the driver that is a steady **492-count push** that only recedes as his own bar
torque climbs the fade above `|bar|` ≈ 512. **V276's "the only way to stop it is to hold the steering
wheel very firmly" is the shape of that, and it is structural here, not incidental.** [EVIDENCE for the
numbers; BELIEF that it feels like V276 — V276 also had a limit cycle, which this does not.]

---

# 2. THE 20 Hz OBJECT UNDER TORQUE MODE

## 2.1 The identity that makes this prediction different from V292's

With `0xC62E6` = 0 the feedback operand is clamped to ±0 on all three branches, so **`L_servo(f) ≡ 0` at
every frequency** and the closed-loop sensitivity is **exactly 1**. Verified directly:
`|R_servo(7.3)|` = 3.1662 on V282 and **0.000e+00** on V293. [EVIDENCE — `v293_s3_gate7.py` CONTROL 0;
`|R_servo(7.3)| = 3.17` also reproduces `TRACE-2026-09-13-r24-lane-transfer` §3.1's published 3.17.]

⇒ the predicted wheel-rate band ratio for a disturbance-driven band is **`|1 + L_V282(f)|`**, a ratio
with no plant inversion and no time-domain march in it. Median over 23 fits, p10–p90 in brackets:

| f (Hz) | 3.0 | 5.0 | 6.0 | **7.3** | 9.0 | 12.0 | 14.0 | 16.0 | 18.0 | **20.3** | 22.0 | 26.0 | 30.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **×(open/closed)** | 3.06 | 2.56 | 2.32 | **2.04** | 1.68 | 1.15 | 0.86 | 0.64 | 0.38 | **0.16** | 0.53 | 0.81 | 0.83 |
| p10 | 2.63 | 2.25 | 2.06 | 1.84 | 1.53 | 0.95 | 0.64 | 0.43 | 0.27 | 0.12 | 0.32 | 0.68 | 0.73 |
| p90 | 5.61 | 3.83 | 3.13 | 2.40 | 1.81 | 1.30 | 1.03 | 0.79 | 0.50 | 0.28 | 0.74 | 0.96 | 0.98 |

🛑 **THE WHOLE TRADE IS THIS ROW.** V282's LKAS rate loop is a **disturbance-rejecting servo below
~13 Hz** and a **disturbance-amplifying de-damper above ~14 Hz**. Torque mode deletes both. The crossing
is at **13.0 Hz** on the median fit.

## 2.2 The byte-exact replay on the operator's own recorded episodes

Same machinery as `V292-REPLAY-PREDICTION-2026-09-13`: r39's 10 loudest 3 s engaged windows (f0
19.922 Hz), 23 plant fits, the same causal marching disturbance inversion, the same r24 arm-delta fold.
**The V282 arm reproduces every recorded window with `max|ΔT| = 0`, asserted on every window and every
fit.** Every column is a V293/V282 ratio on the same window, same 0xE4 command, same disturbance.

| 0xC6446 | gate73 | T 18–22 | **W 18–22** | W 9–18 | T 9–18 | T 5–9 | **W 5–9** | auth oob | auth LF | auth \|T\| |
|---|---|---|---|---|---|---|---|---|---|---|
| 5244 | 1.190 | 0.066 | **0.285** | 0.868 | 0.179 | 0.165 | **1.849** | 0.826 | 1.774 | 0.816 |
| **4451** | **1.010** | 0.066 | **0.285** | 0.888 | 0.179 | 0.165 | **1.822** | 0.826 | 1.774 | 0.816 |
| 2048 | 0.465 | 0.066 | **0.284** | 0.961 | 0.179 | 0.165 | **1.741** | 0.826 | 1.774 | 0.816 |
| 95 % CI (4451) | | [0.06,0.07] | **[0.27,0.30]** | [0.88,0.91] | [0.16,0.19] | [0.15,0.18] | **[1.80,1.84]** | [0.79,0.86] | [1.23,2.32] | [0.77,0.86] |

**r6c (the freshest V282 route, 3701 s, mostly motorway), 5 loudest ring windows:** W 18–22 **×0.403**
[0.37, 0.42], W 9–18 ×0.879, W 5–9 **×1.775**, auth |T| ×0.924.

⭐ **And on r6c's own loudest 12–17 Hz episodes — the band that fired V292's revert signature — V293
reads ×0.800** [0.73, 0.84] on that band, W 18–22 ×0.362, W 9–18 ×0.916, W 5–9 ×1.759.
**V292 made that band worse (predicted ×1.165, measured on the wire 13–17 Hz ×1.31–2.42 with a 14.84 Hz
line at +6.3 dB). V293 is predicted to make it BETTER.** The mechanism is different in kind: V292 moved
a pole and handed the margin to the next crossing; V293 removes the return ratio at every frequency, so
there is no next crossing to hand it to. [EVIDENCE for the replay numbers; the V292 wire numbers from
`V292-FLIGHT-READ` §4.]

🛑 **`T 18–22 = 0.066` IS VACUOUS AND MUST NOT BE QUOTED.** With the loop open the delivered torque
contains no feedback at all, so its ring content collapses by construction. **The wheel-rate column is
the load-bearing one** and it was pre-registered as such (`v293_s2_replay.py` docstring, F2, written
before the first run).

**Kp is a pure output scale with the loop open** — only authority moves:

| Kp | W 18–22 | W 9–18 | W 5–9 | auth oob | auth \|T\| |
|---|---|---|---|---|---|
| **119** | 0.272 | 0.848 | 1.696 | 0.826 | **0.816** |
| 160 | 0.273 | 0.851 | 1.727 | 1.086 | 1.096 |
| 200 | 0.280 | 0.863 | 1.758 | 1.358 | 1.370 |
| 248 | 0.283 | 0.895 | 1.795 | 1.683 | 1.697 |

**The rms-neutral Kp is ≈ 145.** Kp 119 is peak-neutral and rms-light by 18 %.

## 2.3 🛑 THE MEASUREMENT ON THE OPERATOR'S OWN CAR (`v293_s7_anchor.py`)

**With `STEER_REQUEST` = 0 the LKAS lane's output is gated to zero — which is, for the 18–22 Hz
question, exactly what `0xC62E6` = 0 does.** So the engaged ÷ disengaged band ratio on a V282 route is a
**direct measurement** of how much of the ring is the loop's own regeneration, and its reciprocal is the
measured prediction for torque mode. Wheel-rate channel, band rms over contiguous runs ≥ 2.56 s, pooled
by run length — **re-derived here, not relayed**:

| route | build | 5–9 | 9–13 | 13–17 | **18–22** | 22–30 | **⇒ torque mode at 18–22** | replay predicted |
|---|---|---|---|---|---|---|---|---|
| r39 | V282 | 1.770 | 1.204 | 1.903 | **4.200** | 2.467 | **0.238** | 0.284 |
| r6c | V282 | 0.897 | 1.086 | 1.857 | **3.479** | 2.059 | **0.287** | 0.403 |
| r35 | V281 rev 3 | 1.291 | 0.961 | 1.632 | **3.747** | 1.910 | **0.267** | — |

**Cross-check against `V292-FLIGHT-READ-2026-09-13` §4, which computed the same quantity by a different
estimator: r6c 3.399 (mine 3.479), r39 3.920 (mine 4.200), r35 3.618 (mine 3.747) — agreement to 5–7 %.**
[EVIDENCE — independent re-derivation.]

Speed-matched control (the flight read's own caveat is that the disengaged reference is mostly at rest):

| route | 18–22 at 0–3 m/s | at 3–8 m/s |
|---|---|---|
| r39 | 3.943 | — |
| r6c | **4.979** | **3.935** |
| r35 | 2.888 | 3.042 |

**The conclusion survives speed matching and gets slightly stronger on r6c.**

🛑 **Three declared differences, so the anchor is not over-read.** (1) Disengaged also drops the r24 arm
to Honda's 2048 — torque mode need not. (2) Disengaged carries no LKAS excitation; torque mode still
drives `f(cmd)` into the plant (§2.5 sizes that at 3.49 of 63.27 counts). (3) The disengaged reference is
mostly stationary. **And one the anchor cannot fix: at 5–9 Hz the engaged ÷ disengaged ratio is
confounded by the command, which is the dominant 5–9 Hz driver when engaged. The 5–9 Hz prediction of
×1.75 therefore rests on `|1 + L|` and the replay, NOT on this anchor.** [BELIEF, stated as such.]

## 2.4 🛑 THE PREDICTOR'S ONE OUT-OF-SAMPLE TEST FAILED

The same machinery predicted V292's ring at ×0.55 (published) — **I reproduce it at ×0.535 with my own
implementation**, so the following is a failure of the METHOD, not of the code:

| | predicted | measured on the wire |
|---|---|---|
| 18–22 Hz ring, V292 vs V282 | **×0.55** (T) / ×0.63 (W) | raw **×1.06–1.55** vs r6c; **route-normalised ×1.20–2.00** |
| ⇒ route-normalised loop contribution | 3.40 → ≈ **2.1** | **4.09 / 6.80 / 4.09** |

**The predictor was wrong by ×1.9–3.2 and in the wrong direction.** [EVIDENCE — `V292-FLIGHT-READ` §4;
my own reproduction of the V292 prediction.]

**Why V293's prediction is nonetheless better founded than V292's, and where it is not:**

- ⭐ **V292 was a pole MOVE — a shaping whose benefit depends on the fitted plant's phase.** V293 is the
  deletion of the return ratio; `|S| ≡ 1` is an **identity**, not a fit. The only modelled quantity left
  is the split between loop-regenerated and disturbance-driven ring, and **§2.3 measures that split
  directly on the car**, which V292 never had.
- 🛑 **But the flight read names two confounds that would also hit a V293 drive** — the driving model
  changed (`tsfdo` → `gyhu3`) and **every `Accord*` param key was wiped**, so the fork ran code defaults.
  **A V293 drive must re-check `initData.params` before any band is scored.** That is in the
  pre-registration (§6).
- 🛑 **And the honest residual: if the V292 prediction failed because the plant family is wrong in a way
  the disturbance inversion absorbs, that same error is in V293's replay.** §2.3's on-car anchor is the
  hedge, and it is why it leads.

## 2.5 The forced response — what the command alone still drives at 18–22 Hz

| quantity, r39's 10 loudest windows, median | counts |
|---|---|
| V282 total delivered-torque 18–22 Hz amplitude | 63.27 |
| V282 CMD leg alone (wire frozen) | 10.99 |
| **V293 delivered torque 18–22 Hz (= its CMD leg by construction)** | **3.49** (×0.055 of V282's total) |
| recorded wheel-rate ring | 34.32 raw counts (4.29 deg/s) |
| V293 replayed wheel-rate ring | 10.02 (×0.292) |
| residual disturbance `d`'s own 18–22 Hz content | 10.30 (×0.300) |

⇒ **the disturbance floor is the floor the open lane reaches, and the camera comb's own forcing through
a torque-mode lane is 3.49 counts against a 34-count ring — 10 %.** The `COMB-VS-ECHO` lock fraction of
0.50 does not rescue the comb as a mechanism here. [EVIDENCE.]

## 2.6 The matched free ring-down — and a metric of mine that FAILED

🛑 **`v292_replay_lib.kick_response` injects the kick into the wire disturbance, which in a CLOSED loop
reaches the electronics through the feedback. In torque mode the feedback is zero, so the kick never
reaches the torque and the incremental wire response is literally the impulse: no ring, r² = 0.02, and a
"half-life" pinned at the fitting window (205 ms on every fit). The `v293_s2_replay` TASK 2B table is
VOID.** It is recorded rather than quietly swapped. The corrected measurement (`v293_s5_ringdown.py`)
injects at the **plant input**, where a road or driver impulse acts:

| fit | LINEAR pole V282 | LINEAR pole V293 | V282 t½ | V292 t½ | **V293 t½** | 93/82 | r² |
|---|---|---|---|---|---|---|---|
| 225 | 19.95 / ζ 0.0248 | 21.38 / ζ **0.0989** | 195 ms | 74 ms | **50 ms** | 0.254 | 0.85 |
| 215 | 19.81 / 0.0209 | 20.71 / **0.1597** | 213 | 77 | **36** | 0.167 | 0.86 |
| 38 | 19.77 / 0.0353 | 21.45 / **0.0700** | 167 | 30 | **62** | 0.372 | 0.68 |
| 117 | 20.19 / 0.0412 | 22.95 / **0.3500** | 89 | 35 | **12** | 0.136 | 0.87 |

**CONTROL: V282 pools to 169 ms against the published 108–197 ms band, and V292 to 53 ms against the
published 39–71 ms.** Both reproduce ⇒ the corrected injection is the right one.
**V293 pools to 43 ms, ×0.252 of V282 — shorter than V292's.** And the mode's frequency moves **UP**
(19.8–20.2 → 20.7–23.0 Hz), which is the **opposite** of V289's revert signature (down into 15–17 Hz).
[EVIDENCE.]

---

# 3. THE 7.3 Hz QUESTION WITH THE SERVO ARM GONE (`v293_s3_gate7.py`, `v293_s8_r24_bothpoles.py`)

## 3.1 The magnitude gate, and it collapses to one line

`gate73 = |Ls·Rs + Lr·Rr|`, `Ls = 0.55∠+96°`, `Lr = 1.19∠−27°`, each arm's **new/today ratio at 7.3 Hz**.
Torque mode has **`Rs = 0` exactly** (not small — the operand is identically zero), so the two vectors
no longer partially cancel and

> **gate73 = 1.19 · k, k = `0xC6446`/5244, monotonic in k.**

| `0xC6446` | k | **gate73 (torque mode)** | gate73 (V282, servo present) | cut |
|---|---|---|---|---|
| 5244 | 1.0000 | **1.1900** | 1.0028 | 0 % |
| 4725 (V292's) | 0.9010 | 1.0722 | 0.8999 | −9.9 % |
| **4451** | 0.8488 | **1.0100** | 0.8471 | **−15.1 %** |
| 3933 | 0.7500 | 0.8925 | 0.7512 | −25.0 % |
| 2048 (Honda) | 0.3905 | 0.4647 | 0.4900 | −60.9 % |

`gate73 = 1.010` at k = 0.8487 ⇒ **`0xC6446` = 4451**. Hand-checked: `1.19·k = 1.010 ⇒ k = 0.848739,
arm = 4450.8`. [EVIDENCE — closed form, two methods.]

🛑 **4451 IS NOT THE RECORD'S ~1880.** 1880 is where `Re(aggregator)` at 7 Hz crosses zero in the loaded
stratum **with the servo present** (`GRINDING-DEEP-ANALYSIS` §2). 4451 is where the **total 7.3 Hz
return-ratio magnitude** returns to the record's own allowance **without** the servo. Different criteria.
The gate is the one calibrated at two configurations the operator has actually driven (Kp 248 → 1.0028,
cycle measured GONE; Kp 300 → 1.0526, ripple PRESENT).

## 3.2 🛑 Kd = 0 IS THE GATE-BREAKER, NOT THE CLAMP — and V293 is the cheapest of its family

| variant | \|Rs\| | ∠Rs | gate73 at k = 1 | r24 arm for gate ≤ 1.010 | cut |
|---|---|---|---|---|---|
| **V282** Kp 248 Kd 128 clamp 46080 | 1.0000 | −0.0° | **1.0028** | 5280 | — |
| Kp 248 **Kd 0** clamp 46080 | 0.7885 | −36.7° | **1.2923** | 3899 | −25.6 % |
| Kp 119 Kd 128 clamp 46080 | 0.7143 | **+20.1°** | **0.9073** | 5711 | none needed |
| Kp 119 **Kd 0** clamp 46080 | 0.3783 | −36.7° | **1.2211** | 4297 | −18.1 % |
| **V293** Kp 119 Kd 0 clamp 0 | **0.0000** | — | **1.1900** | **4451** | **−15.1 %** |

Two things fall out and neither was in the brief:

1. ⭐ **The record's own warning — "a Kd CUT re-arms the 7.3 Hz cycle and stays DO-NOT-FLASH"
   (`PID-FRAME-SIZING-KP-KD`, `HANDOFF-2026-09-04`) — is REPRODUCED quantitatively here: Kd 0 alone
   reads 1.2923.** Because a derivative is the servo's only lead term, deleting it rotates the servo arm
   from ∠0° to **∠−36.7°**, straight into the pump's quadrant.
2. ⭐ **V293's full deletion (1.1900) is BETTER on the gate than Kd = 0 with the feedback kept (1.2211–
   1.2923).** Deleting the arm entirely is cheaper than leaving a small mis-phased one. **V293 is the
   gate-cheapest member of the Kd-0 family**, and that is an argument for the full lever over the partial.

⚠ And one road not taken: **Kp 119 with Kd 128 kept and the clamp kept reads gate73 = 0.9073 — better
than V282, free, no r24 cut.** It is not torque mode and it does not change the delivered quantity; it is
noted because it is the only configuration in the table that improves the 7 Hz gate at zero cost.

## 3.3 The poles, not the magnitude — the r24-only loop (the brief's actual question)

Family: reproduces the **measured V282 pole** (19.7–20.4 Hz, ζ 0.012–0.045) **AND the measured V289 pole**
(15.6–17.3 Hz, ζ −0.06…0.12), and is closed-loop stable 2–60 Hz with both arms — the record's own
subfamily, re-run here.

**POSITIVE CONTROL: n = 269 / 256 / 12 at κ = 0.10 / 0.20 / 0.45, matching
`TRACE-2026-09-13-r24-lane-transfer` §6.1 EXACTLY, and every published row reproduces to four decimals**
— κ 0.10: 5244/20.04/+0.0312, 3933/19.79/+0.0217, 2622/19.57/+0.0101, 2045/19.47/+0.0066 ·
κ 0.20: 5244/20.02/+0.0297, 3933/19.52/+0.0130, 2622/18.98/−0.0031, 2045/18.76/−0.0110 ·
κ 0.45: 5244/20.09/+0.0370, 3933/19.41/+0.0290, 2622/18.60/+0.0146, 2045/18.18/+0.0054. **Twelve of
twelve.** [EVIDENCE — `_scratch/v293_s8_r24_bothpoles.txt`.]

| κ | `0xC6446` | **servo present** f / ζ | **servo GONE (V293)** f / ζ | worst pole 3–30 Hz, TM | unstable |
|---|---|---|---|---|---|
| **0.10** | 5244 | 20.04 / **0.0312** | 20.66 / **0.3250** | 22.42 / +0.0609 | **0 / 269** |
| | 4451 | 19.88 / 0.0249 | 20.61 / **0.3291** | 22.42 / +0.0623 | 0 |
| | 2048 | 19.47 / 0.0066 | 20.41 / 0.3417 | 22.43 / +0.0665 | 0 |
| | 0 | 19.13 / **−0.0133** | 20.35 / 0.3500 | 22.44 / +0.0700 | 0 |
| **0.20** | 5244 | 20.02 / **0.0297** | 20.53 / **0.3000** | 19.70 / +0.0949 | **0 / 256** |
| | 4451 | 19.71 / 0.0202 | 20.37 / **0.3143** | 19.64 / +0.0973 | 0 |
| | 2048 | 18.76 / **−0.0110** | 19.84 / 0.3455 | 19.47 / +0.1075 | 0 |
| **0.45** | 5244 | 20.09 / **0.0370** | 20.49 / **0.1570** | 5.53 / +0.1307 | **0 / 12** |
| | 4451 | 19.69 / 0.0320 | 20.13 / **0.1678** | 19.32 / +0.1388 | 0 |
| | 2048 | 18.18 / 0.0054 | 18.80 / 0.2232 | 18.76 / +0.1607 | 0 |
| | 0 | 16.83 / **−0.0485** | 17.56 / 0.3500 | 20.09 / +0.2000 | 0 |

**Paired Δζ from REMOVING r24 entirely:**

| κ | servo present (p10 / p50 / p90) | frac > 0 | **servo GONE** (p10 / p50 / p90) | frac > 0 |
|---|---|---|---|---|
| 0.10 | −0.0736 / **−0.0439** / −0.0149 | 0.01 | +0.0111 / **+0.0362** / +0.1206 | **0.97** |
| 0.20 | −0.1211 / **−0.0748** / −0.0333 | 0.00 | +0.0320 / **+0.0974** / +0.2306 | **0.96** |
| 0.45 | −0.1038 / **−0.0855** / −0.0584 | 0.08 | +0.0643 / **+0.1827** / +0.1982 | **1.00** |

## 3.4 What that means, in three sentences

1. ⭐ **Torque mode raises the 20 Hz mode's damping by ×4.2 (κ 0.45) to ×10.4 (κ 0.10), on the family
   that fits both measured poles.** [EVIDENCE — a modelled counterfactual on a measurement-constrained
   family, not a measurement.]
2. ⭐ **r24's 20 Hz damping is worth NOTHING once the loop no longer de-damps — it becomes a mild
   DE-damper (paired +0.036 to +0.097, 96–97 % of plants).** The record's "r24 supplies 73–86 % of the
   20 Hz damping" is a statement about a loop that is being de-damped by the servo; it does not survive
   deleting the servo. **This is what makes the −15.1 % r24 cut affordable in torque mode and expensive
   everywhere else.**
3. ✅ **The r24-only loop has NO unstable or marginal pole anywhere in 3–30 Hz, at any arm, at any κ, on
   any plant of the family — 0 of 269 / 256 / 12.** The worst pole is +0.061 to +0.131. **A magnitude
   gate of 1.19 does not correspond to a pole near the unit circle here.**

⚠ **THE DISAGREEMENT I MUST DECLARE.** A **broader** family — "fits the V282 pole and is stable", without
the V289 constraint — gives a much weaker answer: ζ 0.036 (torque mode) against 0.028 (V282), i.e. ×1.3
rather than ×10, and at κ ≥ 0.45 its **worst** plant carries a 21–23 Hz pole at ζ −0.008 to −0.034 with
r24 at 5244, clearing by arm ≈ 2622–3072. **The two families disagree because the V289 constraint pins
the plant's own `zp` near 0.35.** The both-poles family is better constrained and reproduces the record;
the broader one is the conservative reading. **Both are in `_scratch/v293_s3_gate7.txt` and
`_scratch/v293_s8_r24_bothpoles.txt`; I have not adjudicated them and I do not think I can from here.**

## 3.5 The deadband, since the brief names it

`0xC61F6` = 3, applied to `s` **after** the arm. Describing function `N(A) = (2/π)[π/2 − asin r − r√(1−r²)]`,
`r = 3/A`:

| band | bar amp | \|d\| | s at 5244 | N(5244) | N(2048) |
|---|---|---|---|---|---|
| 7.3 Hz loaded | 1500 | 137.4 | 703.7 | 0.9946 | 0.9861 |
| 7.3 Hz creep | 400 | 36.6 | 187.6 | 0.9796 | 0.9479 |
| **20.3 Hz ring** | 44 | 11.1 | 56.9 | **0.9329** | **0.8285** |

**Inert at 7 Hz; removes 7 % of the lane at the ring, and more as the arm is cut.** Since §3.4 says
cutting r24 is free-to-beneficial at 20 Hz in torque mode, the deadband pushes the same way.

---

# 4. THE HIGH-ANGLE STALL (`v293_s4_highangle.py`)

## 4.1 The stall class, on r31's own recorded stall window

r31 is V278 rev 3 — the only route on which the STALL class was measured (7 of 10 F7 episodes). The A
arm is **V278 rev 3's own cells**, so the disturbance inversion reproduces the recording exactly; the B
arms swap the electronics. One window survives the gate (rate 10–20 deg/s, ref 30–50 deg/s,
`|angle| ≥ 30°`, engaged): **t = 218.4 s, rate p50 12.5 deg/s, ref p50 43.0 deg/s, idx 240, |bar| 1270,
v 6.4 m/s.**

| arm | 6–8.5 Hz ripple | level | **rip/level** | **P-rail duty** | T 2–8 Hz | \|T\| mean |
|---|---|---|---|---|---|---|
| **V278 rev 3 (the recording)** | 638.7 | 906 | **0.705** | **0.660** | 495.8 | 881 |
| V282 | 223.3 | 1335 | 0.167 | 0.600 | 175.8 | 1357 |
| V292 | 228.8 | 1342 | 0.171 | 0.612 | 179.2 | 1375 |
| **V293 Kp 119** | **131.1** | 1687 | **0.078** | **0.000** | 141.0 | 1689 |
| V293 Kp 160 | 131.2 | 1689 | 0.078 | 1.000 | 140.8 | 1690 |

⭐ **POSITIVE CONTROL: V278 rev 3's replayed rip/level is 0.705, inside the record's own published
in-episode 0.55–0.70** (`HIGHANGLE-V278R3-2026-09-02`). The mirror reproduces the number the class was
named from. [EVIDENCE.]

⭐ **The V278 rev 3 mechanism is removed, and it is arithmetic, not a fit.** The P-rail duty goes
**0.660 → 0.000**: with `E = 32·sp` there is no feedback ripple to cross P's linear window. The absolute
6–8.5 Hz torque ripple falls **×0.21**.

⚠ **DECLARED EXTRAPOLATION:** r31's openpilot was commanding against the ×2 map, so replaying the same
recorded 0xE4 through V282's ×6 map asks for ~3× the reference. **The mechanism transfers; the absolute
torque level on the B arms does not.**

⚠ **Kp 160 rails P on 100 % of ticks at this window.** Kp 119 is the only value in the table that keeps
the surface out of the clamp at railed command.

## 4.2 Loaded high-angle windows on V282's and V281 rev 3's own routes — same cells both sides

r39, 4 windows, idx p50 240, rate p50 22–136 deg/s, v 1.7–3.5 m/s:

| arm | 6–8.5 ripple | level | rip/level | P-rail | **W 6–9** | T 18–22 | \|T\| mean |
|---|---|---|---|---|---|---|---|
| V282 (the recording) | 30.2 | 468 | 0.158 | 0.405 | **13.4** | 12.2 | **436** |
| V292 | 31.4 | 461 | 0.159 | 0.405 | 15.2 | 7.5 | 436 |
| **V293 Kp 119** | **15.7** | 1580 | **0.015** | 0.000 | **28.1** | 3.0 | **1575** |

r35 (V281 rev 3, LKAS cells byte-identical to V282's), 3 windows:

| arm | 6–8.5 ripple | level | rip/level | P-rail | **W 6–9** | \|T\| mean |
|---|---|---|---|---|---|---|
| V282 (the recording) | 8.2 | 592 | 0.014 | 0.446 | **10.5** | 528 |
| V292 | 7.3 | 601 | 0.012 | 0.444 | 12.4 | 528 |
| **V293 Kp 119** | **26.0** | 715 | 0.020 | 0.000 | **15.2** | 688 |

🛑 **THREE THINGS THE OPERATOR HAS TO BE TOLD, and two of them are bad.**

1. 🛑 **`rip/level` improves partly because the DENOMINATOR grows.** On r39 it goes 0.158 → 0.015 while
   the level goes 468 → 1575. **Do not quote `rip/level` alone for this build.** The absolute ripple is
   the honest number, and it splits: ×0.52 on r39, **×3.2 on r35**.
2. 🛑 **The wheel's 6–9 Hz motion roughly DOUBLES** — ×2.10 on r39, ×1.45 on r35 — consistent with §2.1's
   `|1 + L(7.3)| = 2.04`. **This is the stutter band the operator has just called worse on V292.**
3. 🛑 **At a railed command on a loaded turn V293 delivers ×3.6 the torque** (1575 vs 436) **into a wheel
   already moving at the commanded rate** (130 deg/s against a 129 deg/s reference). The lane will keep
   pushing; only openpilot's outer loop or the driver's own bar torque through the fade can stop it.

## 4.3 The V292 flight routes carry the stall class

| route | route s | engaged s | loaded-high-angle frames | stall-class frames |
|---|---|---|---|---|
| r6d_v292 | 1060 | 644 | 3513 | **384** |
| r6e_v292 | 1338 | 507 | 4725 | **388** |
| r6f_v292 | 759 | 572 | 2789 | **402** |

The stall-class frames are present but scattered (≈ 4 s each, no contiguous 1.5 s window survives the
density gate), so no window-based contrast could be run on them here. **They are the right population
for whoever scores a V293 drive.** [EVIDENCE for the counts; the frame gate is the record's own.]

---

# 5. openpilot's OUTER LOOP UNDER TORQUE MODE (`v293_s6_outer.py`)

## 5.1 The model, and the calibration that makes it trustworthy

`LatControlTorque` closes on the **steering angle off CAN** (`OUTER-LOOP-ID-2026-09-10` finding 1 — not
yaw, not the camera, no `livePose`):

```
L_outer(s) = [kp·(1 + lsf/kp) + ki/s]/LAF  ·  k_meas · Rate(s)/(j2πf) · e^{−j2πf·τ}
k_meas = v²/(SR·L_wb)·π/180        SR 16.88 (live), L_wb 2.83 m
```

**The FEEDFORWARD IS OPEN LOOP and does not enter the return ratio.** `AccordRatePlantFF`'s effect is a
**mis-scaling**, not a stability term — §5.3 sizes it.

The plant's own DC gain is **back-solved from the fork's own measured `HONDA_ACCORD_EPS_G_V`**, not taken
from the fits (which span ×400): `G_v282(v) = 141.4·L_dc/(1+L_dc)` with `L_dc = R_servo(0)·CPD·g0` and
`R_servo(0) = 4.7968` read from the V282 image cells.

| v (m/s) | G_v282 (deg/s/unit) | L_dc | g0 | **V293 rate per unit** | **ratio** |
|---|---|---|---|---|---|
| 5.0 | 120.0 | 5.607 | 0.14612 | **380.6** | **×3.17** |
| 8.0 | 110.0 | 3.503 | 0.09129 | 237.8 | ×2.16 |
| 12.5 | 95.0 | 2.047 | 0.05335 | 139.0 | ×1.46 |
| 18.5 | 85.0 | 1.507 | 0.03927 | 102.3 | ×1.20 |
| 28.5 | 70.0 | 0.980 | 0.02555 | 66.5 | **×0.95** |

(`k_map_unit` = 2605 EPS torque counts per unit command, read from the built V293 surface.)

🛑 **V282's rate-per-unit is set by the MAP and held within ×1.71 across the speed range by the servo.
V293's is set by the PLANT and swings ×5.72. The servo was regulating out exactly that variation.**

🛑 **A control of mine that FAILED first, and the failure was mine.** I first compared the model's
`|L|` at 1 Hz against the record's 0.026–0.165 and it failed at ×3. **The record's 0.026–0.165 is `|L|`
AT THE RING (18–22 Hz), not at 1 Hz.** Re-run at 20 Hz with the plant's real dynamics, the model spans
**0.0109–0.3811** over four named fits × three speeds — it overlaps the measured interval and exceeds
its 0.189 bound by ×2 on one fit, inside the family's own spread. **CONTROL PASSES.**

## 5.2 The grid — LAF (2, 4, 6, 8, 10, 12) × Kp (0.3, 0.6, 0.9) × Ki (0, 0.15, 0.30)

Median fit 225, τ = 0.10 s. `Ms = max|1/(1+L)|` over 0.2–12 Hz; `fc` = crossover; `PM` = phase margin.
**SAFE = `Ms` < 2.0 and (no crossover in band, or PM > 35°).** A cell "reproduces V276" if `|L| ≥ 1`
anywhere in 2–4 Hz.

| speed | V276 signature in ANY cell? | RISK cells (V293) | the same cells on V282 |
|---|---|---|---|
| **5.0 m/s** | **none, any cell** | **none** | none |
| **12.5 m/s** | **none** | **none** | none |
| **28.5 m/s** | **none** | LAF 2.0 × Kp 0.9 (all Ki); LAF 2.0 × Kp 0.6 × Ki 0.30 | **the same four cells are RISK on V282 too** |

At the operator's live cell **LAF 6.0, Kp 0.9, Ki 0.30**:

| fit | v | V282 \|L\|@1Hz / Ms / fc / PM | V293 \|L\|@1Hz / Ms / fc / PM |
|---|---|---|---|
| 225 | 5.0 | 0.0263 / 1.04 / — / — | 0.0829 / 1.09 / — / — |
| 225 | 12.5 | 0.1301 / 1.09 / — / — | 0.1891 / 1.14 / — / — |
| 225 | 28.5 | 0.4983 / 1.35 / 0.50 / **66°** | 0.4707 / 1.38 / 0.47 / **64°** |
| 38 (hi-auth) | 28.5 | 0.4995 / 1.33 / 0.50 / 66° | 0.4478 / **1.51** / 0.47 / **58°** |

Delay sensitivity (τ is the single BELIEF in the plant model): over τ = 0.02 / 0.10 / 0.20 s the V293
phase margin at 28.5 m/s moves 68° / 64° / 57°, tracking V282's 70° / 66° / 59°. **The delay does not
separate the two builds.**

✅ **VERDICT: openpilot's outer loop is not where torque mode fails.** The reason is arithmetic:
`k_meas ∝ v²`, so the outer loop's gain is dominated by high speed, and that is exactly where V293's
rate-per-unit ratio is ×0.95. The ×3.17 sits at 5 m/s where `k_meas` is 32× smaller.

**Safe cells: everything except LAF 2.0 with Kp ≥ 0.6 at motorway speed. Cells that reproduce V276:
none.** [EVIDENCE for the arithmetic; **BELIEF** for the absolute margins, whose plant lag τ is assumed
and whose `G(v)` table is the fork's identification on a DIFFERENT firmware.]

## 5.3 🛑 WHERE V276 COMES BACK — the feedforward, not the margin

`get_honda_accord_rate_plant_ff` computes `hold = k(v)·angle/G(v)` and `move = rate_gain·d(angle_des)/dt / G(v)`.
**Both divide by `G(v)`, the CLOSED-LOOP rate-servo gain.** In torque mode the true gain is
`k_map_unit·g0(v)`:

| v (m/s) | G_v282 | G_torque-mode | **FF error** | what the car does |
|---|---|---|---|---|
| 5.0 | 120.0 | 380.6 | **×3.17** | **OVERSHOOTS ×3.2** |
| 8.0 | 110.0 | 237.8 | ×2.16 | OVERSHOOTS ×2.2 |
| 12.5 | 95.0 | 139.0 | ×1.46 | OVERSHOOTS ×1.5 |
| 18.5 | 85.0 | 102.3 | ×1.20 | OVERSHOOTS ×1.2 |
| 28.5 | 70.0 | 66.5 | ×0.95 | about right |

🛑 **That is the V276 FAILURE SHAPE without any instability: an open-loop push 3× what the geometry needs
at low speed, with a feedback term divided by LAF 6.0 that is too weak to pull it back.** V276's operator
report — a self-exciting oscillation at all speeds, stoppable only by gripping the wheel — was a relay
limit cycle; this would be a steady over-push. **Different mechanism, similar complaint.**

**Three fork changes, with their costs stated the way the operator judges them
(`feedback-no-openpilot-side-modifications`, AMENDED):**

| change | added lag | authority cost | why |
|---|---|---|---|
| **`AccordRatePlantFF` → False** | **0 ms** | **none** (it raises FF, ×2.4–4.3 at today's LAF) | the plant-inverse FF is wrong for a torque plant; the generic `setpoint/LAF` becomes the correct one. The fork's own "3–10× too much torque" comment was about the RATE plant and does not apply. |
| **`SteerKP` 0.9 → 0.3** | **0 ms** | a **×3 cut in proportional feedback** | the fork memo's own §3.6 gating rule: the gain margin scales as 1/LAF and LAF is about to be re-identified. ⚠ This IS an authority cut and must be declared as one. |
| **`AccordTorqueKi` 0.30 → 0.15** | 0 ms | halves the integral | a mis-sized LAF with a live integrator hides the error until it is a wallow |

🛑 **`ModelCurvatureLead` must stay OFF** (it is absent from `initData.params` on every recent route, so
it defaults off — the requirement is already met, but check it).
🛑 **A command low-pass remains forbidden by name** and nothing here proposes one.

---

# 6. PRE-REGISTRATION FOR A TORQUE-MODE DRIVE

**Written before any image exists.** Thresholds are the record's own and are NOT to be moved after the
log lands (`PREREG-V281-READ` rule).

## 6.1 What would make V293 DO-NOT-FLASH, before any drive

| # | condition | status now |
|---|---|---|
| **B1** | an adversarial pass finds any code byte changed, or any cell outside the six named in §1.1 | not yet run — **required before a flash** |
| **B2** | the built image's delivered surface, read from the IMAGE, does not reproduce §1.4's table to ±2 counts | not yet run |
| **B3** | `0xC674E` (EME soft-limit) ≤ the tracking clamp 3072, or int and float EME mirrors disagree | unchanged by this build; must be re-asserted from the image |
| **B4** | any plant in the both-poles family carries a closed-loop pole with ζ ≤ 0 in 3–30 Hz with the servo gone | **PASSES: 0 of 269 / 256 / 12 at every arm, every κ** |
| **B5** | `gate73` > 1.01 at the chosen `0xC6446` | **PASSES at 4451 (1.0100), by 1 part in 10 000** — the same knife-edge V292 sat on |
| **B6** | the fork is flown with `AccordRatePlantFF` True | **must be turned OFF — this is a flight prerequisite, not a recommendation** |

## 6.2 The read from ONE short symptomatic episode

**The edit-live control, and it is within-frame** (`v293_s9_prereg.py`): with `fb ≡ 0` the CAN-427 torque
tap is an **exact function of the demand index and the driver's bar torque**, with **no dependence on the
wheel rate**. Regressing `|tap|` on `f(cmd)·fade` within the same frames:

| | V282 (the recording) | **V293 predicted** |
|---|---|---|
| R² | **−4.81** (median over 10 windows) | **+0.92** |
| residual rms | 348.8 counts | **47.4** (×7.4 smaller) |

🛑 **This is a positive-control-bearing check, not a tautology: the V282 residual IS the feedback leg, and
it must vanish.** The V293 residual is not zero because the tap quantises to 8 counts and the fade LERP
runs on the 100 Hz bar while the PID runs at 1 kHz.

**The 0x14A cave bits** (carried byte-identical — no code byte moves, so every bit stays live):

| bit | what it is | V282 duty | **V293 predicted** | role |
|---|---|---|---|---|
| **b7** | `sign(gp-0x6b4c)`, the LKAS summand | 0.996 | **0.808** | ⭐ **the second edit-live readout** |
| b6 | `\|r24\| ≥ \|T\|` | 0.126 | 0.155 | **do NOT pre-register** — +0.03 is inside one episode's duty noise |
| b5 | `\|r24\| ≥ \|aggregator sum\|` | — | — | not modelled |
| **b4** | `sign(r24)` | 0.808 | **0.808** | ⭐ **the NEGATIVE CONTROL** — identical by construction; if it moves, something other than the intended cal changed |
| b3 | `sign(gp-0x3680)` | — | — | unchanged |

🛑 **I expected b6 to be the mover and it is not — b7 is.** Recorded that way because it was the opposite
of my prior.

**The bands, on ONE symptomatic episode:**

| readout | channel | V282 baseline | **V293 predicted** | resolution |
|---|---|---|---|---|
| **18–22 Hz ring amplitude, hands-off creep** | 0x18F rate | r39 16.4, r6c 11.5 raw counts | **×0.24–0.29** ⇒ 3–5 counts | quantiser 1 count ⇒ 4× margin |
| **ring-down half-life** | 0x18F rate | 108–197 ms | **≈ 43 ms (×0.25)** | the record's own metric |
| **F7 per 100 s high-angle engaged** | 0x18F rate, 2–8 Hz envelope > 103 wire, ≥ 1 s, \|angle\| ≥ 30° | V282 1.03, V281r3 0.00, **V292 3.99 / 2.22 / 6.30** | ⚠ **unpredicted — the model says the band grows ×1.7–1.8** | fixed threshold 103, do not move |
| **tap ripple/level, loaded turns** | CAN 427 | V282 0.104–0.166, V281r3 0.21, V292 0.214–0.339 | 0.015–0.078 **but the level grows ×1.2–3.6** — report the ABSOLUTE ripple too | 8 counts/LSB at 50 Hz |
| **a 2–4 Hz outer-loop line** (the V276 signature) | 0x18F rate + 0xE4 | absent | **predicted absent** (§5.2, no cell) | — |
| **a 10–18 Hz line** | 0x18F rate | V292 fired this: 13–17 Hz ×1.31–2.42, a **14.84 Hz line at +6.3 dB** | **×0.85–0.96 predicted** (the band falls, it does not rise) | — |

**Every signal is confirmed on the wire in a V282-based build:** 0x14A byte 4 bits 3–7 (the V282 cave,
100 Hz, unchanged) · CAN 427 = 0x1AB delivered torque `(sign(T)<<9)|(|T|>>3)`, 8 counts/LSB at 50 Hz ·
0x18F STEER_ANGLE_RATE at 100 Hz, 8 counts per deg/s · 0xE4 STEER_TORQUE + STEER_REQUEST at 100 Hz ·
driver torque (wire = raw × 1.024). **No new cave bit is needed and none is proposed.**

🛑 **AND ONE THING TO CHECK BEFORE SCORING ANY BAND:** `initData.params` on the drive route.
`V292-FLIGHT-READ` §0 found every `Accord*` key ABSENT and the driving model changed between r6c and the
V292 routes. **If the params are wiped again the drive is confounded and the band scores are not a build
contrast.**

## 6.3 🛑 THE SENTENCE A NULL LICENSES

> **"If the 18–22 Hz ring amplitude on hands-off creep does not fall to at most 0.4× of V282's — an
> effect three times the ×1.22 the kit has ruled unreadable, and one the car's own engaged÷disengaged
> ratio of 3.5–4.2 says must be there — with the LKAS rate loop FULLY OPEN (`|R_servo|` = 0 at every
> frequency, verified on the wire by the within-frame identity in §6.2), then the 18–22 Hz object is NOT
> the LKAS rate loop's, the engaged÷disengaged ratio measures something other than the loop, and every
> in-loop class — shaping, notching, pole-moving and opening — is CLOSED."**

That is a genuinely terminal sentence, and it is the first one in this arc that is. **V292's own null
sentence was weaker** because V292 only opened the loop above a corner.

**The symmetric sentence, which must be written too:**

> **"If the 6–9 Hz strong-turn ripple rises as predicted (F7 ≥ 2 per 100 s, or the ABSOLUTE 6–8.5 Hz tap
> ripple ≥ 1.5× V282's on loaded turns), REVERT. The ×1.7–1.8 rise in the 5–9 Hz band is not a risk the
> build takes — it is a prediction the build makes, and it is on the symptom the operator has just
> called worse."**

---

# 7. WHERE THE CANDIDATE IS WRONG, AND WHAT I WOULD DO INSTEAD

## 7.1 The three corrections to the brief's framing

1. **"Kp flat = 119 so that P rails exactly at the map top"** — arithmetically right, but the reason to
   choose it is that it reproduces **V279 rev 2's delivered surface** (slope 0.6356 vs 0.645), the
   configuration that already passed five adversaries. It is **not** authority-neutral: rms ×0.82 on the
   grinding episodes, ×3.6 on loaded turns. §1.3–1.4.
2. **"r24 arm undecided: 5244 / 4725 / ~2048 / stock"** — the gate settles it at **4451**, and §3.4 shows
   the cut is **free at 20 Hz in torque mode**, which is not true of any other build in this arc. 2048 is
   over-cutting: it buys gate 0.465 that nothing needs and reverts a cell with a flown on-car record
   (V70: grinding back at the stock level — **with the servo present**).
3. **"the LKAS lane delivering what openpilot expects — TORQUE"** — delivered, but note that
   §1.4's third sense of authority means **openpilot's own feedforward becomes wrong by ×3.2 at 5 m/s**.
   The firmware change alone does not deliver the goal; it needs `AccordRatePlantFF` OFF in the same
   change. §5.3.

## 7.2 🛑 THERE IS NO INTERMEDIATE DOSE — I looked (`v293_s10_clamp.py`)

`0xC62E6` is a **clamp**, so a small non-zero value is a **Coulomb relay** on the sign of the wheel rate,
of magnitude `dT = (C·Kp>>8)·gain>>15`:

| `0xC62E6` | binds above | Coulomb dT (Kp 119) | as a fraction of peak |
|---|---|---|---|
| 256 | 1.04 deg/s | 19 | 0.008 |
| 512 | 2.07 | 38 | 0.015 |
| 2048 | 8.29 | 155 | 0.063 |
| 4096 | 16.57 | 310 | 0.126 |
| 46080 | 186.46 | — | linear everywhere the car drives |

Swept byte-exact on r39's 10 loudest windows × 4 fits, Kp 119 / Kd 0 / r24 5244:

| `0xC62E6` | W 18–22 | W 9–18 | W 5–9 | auth oob | auth \|T\| |
|---|---|---|---|---|---|
| **0** | **0.272** | **0.848** | **1.696** | 0.826 | 0.816 |
| 512 | 0.273 | 0.880 | 1.712 | 0.799 | 0.803 |
| 2048 | 0.274 | 0.982 | 1.770 | 0.789 | 0.782 |
| 4096 | 0.285 | 1.083 | 1.780 | 0.771 | 0.764 |
| 46080 | 0.299 | 1.150 | 1.788 | 0.761 | 0.752 |

**Every non-zero value is worse than zero on every column.** And with the command frozen — no external
excitation in those bands beyond the residual disturbance — the relay **ADDS** motion:

| `0xC62E6` | W 18–22 vs clamp 0 | W 5–9 vs clamp 0 |
|---|---|---|
| 512 | ×1.007 | ×1.047 |
| 2048 | ×1.041 | ×1.098 |
| 4096 | ×1.079 | ×1.090 |

**A relay closed around a lightly damped mode is the textbook limit-cycle generator, and this one
self-excites at both bands.** The cell is effectively binary; **0 is the right end**.

## 7.3 ⭐ THE LEVER INSIDE THE LEVER — and the operator should see this before he chooses

Read the last table's first and last rows side by side:

| | W 18–22 | W 5–9 | auth \|T\| | delivered quantity | gate73 | r24 cut needed |
|---|---|---|---|---|---|---|
| **V293** (clamp 0, Kd 0, Kp 119) | **0.272** | 1.696 | 0.816 | **torque** | 1.190 | −15.1 % |
| **"V293-lite"** (clamp 46080 **kept**, Kd 0, Kp 119) | **0.299** | 1.788 | 0.752 | **rate, still nulling** | 1.221 | −18.1 % |

🛑 **~90 % of the grinding benefit is Kd = 0 and Kp 119; the clamp contributes ×0.299 → ×0.272.** The
clamp is what changes the **delivered quantity** — the session's *other* goal — and on the ring it is
nearly free. **Three consequences:**

1. **The two goals are separable** and the operator can be told the price of each.
2. **"V293-lite" is NOT the safer choice.** It keeps the lane nulling (so no ×3.6 over-push on loaded
   turns, no FF mis-scaling, no outer-loop change at all) **but it is WORSE on the 7 Hz gate**
   (1.2211 vs 1.1900) and needs a **bigger** r24 cut, **which with a servo still in the loop is the
   expensive direction** — §3.3's servo-present column shows ζ(20 Hz) falling 0.030 → 0.020 (κ 0.20) /
   0.031 → 0.025 (κ 0.10) between arm 5244 and 4451, and V293-lite needs 4297. ⚠ That column is computed
   for V282's own Kp 248 / Kd 128 servo, not for V293-lite's Kp 119 / Kd 0 one, so the magnitude is
   indicative and the **sign** is the claim. **Torque mode is the variant in which the r24 cut is
   affordable, because there deleting r24 RAISES ζ (§3.4).**
3. ⚠ **And the third row nobody asked for: Kp 119 with Kd 128 KEPT and the clamp kept reads
   `gate73` = 0.9073 — better than V282, free, no r24 cut.** It is not torque mode and I have not scored
   its ring. **It is the only configuration in §3.2's table that improves the 7 Hz gate at zero cost, and
   it is worth one afternoon of someone's time before a flash.**

## 7.4 What I would do instead, and why

**I would fly torque mode, at `0xC62E6` = 0 · Kd = 0 · Kp 119 · `0xC6446` = 4451, with the fork changes
in §5.3 — and I would not call it a grinding fix.**

The reasoning, stated so the operator can disagree with it:

- ⭐ **The ring evidence is the best this arc has produced, and one leg of it is on-car** (§2.3). Nothing
  else in the record has an engaged÷disengaged measurement standing behind it.
- ⭐ **The null sentence is terminal** (§6.3). Whatever the drive says, the in-loop class closes or the
  grinding is solved. **No other candidate on the table can say that**, and the record's own design law
  ("remove the loop's action across the WHOLE 12–26 Hz band at once") names this build.
- 🛑 **But the predicted 5–9 Hz rise of ×1.7–1.8 is on the symptom the operator called WORSE today**, and
  it is not a risk — it is a prediction. The r24 cut to 4451 buys the magnitude gate back to 1.010 and
  **does not buy back the ×1.7** (the replay moves it only 1.849 → 1.822). **He is being asked to trade
  the band he is currently unhappy about for the band he has been unhappy about longer.** That has to be
  said in those words.
- 🛑 **And the honest structural objection: with `fb ≡ 0` the lane cannot back off for the driver.** Only
  the fade can, and the fade needs `|bar|` ≈ 1600 before it removes a third of the push. §1.5.

**If the operator will not accept the 5–9 Hz prediction, the class is not ready and the next move is not
a build — it is to find out whether the 5–9 Hz rise is real**, which the V292 flight data can answer
directly: V292 already opened the loop above ~10 Hz and its measured 5–9 Hz route-normalised ratio rose
**×2.92–4.25** against r6c's, against a model that predicted ×1.03–1.10. **That is the same sign and
three times the size**, and it is the strongest reason in this document to believe the 5–9 Hz prediction
and to distrust the ring prediction. [EVIDENCE — `V292-FLIGHT-READ` §4; the model prediction from
`V292-REPLAY-PREDICTION` §5.]

---

# 8. WHAT I DID NOT VERIFY

- **No image exists.** Nothing was built. §6.1's B1/B2/B3 are un-run and are flash prerequisites.
- **The plant families are inherited.** I re-ran the record's own grids and reproduced its published
  counts and rows exactly, but I did not re-fit `B(f)`, did not re-derive the two measured pole anchors,
  and did not adjudicate the both-poles vs V282-only disagreement in §3.4.
- **κ is still disputed three ways** (0.10–0.20 / 0.45 / 1.45). Every 7 Hz and 20 Hz number is reported
  at each; the ×10 ring-damping claim falls to ×4.2 at κ 0.45 and the κ 0.45 family has only 12 plants.
- **The outer-loop margins are modelled.** τ is assumed (sensitivity given); `G(v)` is the fork's
  identification **on a different firmware**; `low_speed_factor` is set to 0 throughout.
- **openpilot's outer loop is frozen in every replay.** The recorded 0xE4 is replayed unchanged in both
  arms, so no outer-loop reaction to a changed wheel rate is captured. In torque mode that omission is
  **larger** than it was for V292, because the command's leg of the delivered torque is now 100 % of it.
- **I did not model the EME soft integrator's duty.** A non-nulling lane holds a **steady** command where
  V282's nulls; the record flags that the soft EME integrates `(cmd − bound)` unattenuated at 1 kHz and
  arms SM2 in 153 ms on a sustained 100-count excess. **That is an open risk this document does not
  close, and it belongs in an adversarial pass.**
- **I did not re-derive V279 rev 2's cells from its image** beyond the map and Kp/Kd banks; the slope
  comparison in §1.3 uses the lineage's published 0.645.
- **No Ghidra.** This round read the images with Python only; every address is the record's.
- **On-car: nothing.** Nothing was flashed and nothing was sent on any bus.

---

*Written by agent `tmdesign` for orchestrator `main`, 2026-09-13. Design study only. No image, `.rwd`
or build script was created or edited; nothing was flashed; no CAN or UDS message was sent; nothing was
committed or pushed.*
