# ADVERSARY "stability" vs the p-gain candidate R1.3_8_100: the dynamics attack

Subagent `adv-stability (p-gain)`, 2026-09-30. **Design review only.**
- Nothing was built, flashed or sent. No CAN traffic, no image, no `.rwd`.
- The fork was only read, through the harness's read-only extract. No STATE, memory, lineage, golden-model or CLAUDE.md edits. Nothing was committed.
- Every decision-bearing claim is marked **[E]** EVIDENCE (with its method) or **[B]** BELIEF.
- Symptoms are the operator's to score. Everything below is a transfer function, a band or a simulation.

**Pre-registered FAIL criteria:** `adv_stability/ADV-stability-p-gain-CRITERIA.md`, written at 11:15, before any computation (the first output file is stamped 11:19).

**Scripts and outputs:** `adv_stability/` (a1–a15 and the `adv_*` libraries).

**Independence**
- The lane, the linear loops (inner and outer), the plant integrator and the nonlinear simulator are my own code.
- The fork in the nonlinear runs is the harness's `ForkPort`. Its gate H3b proves it bit-identical to the real `LatControlTorque`.
- The harness `sweep_drive` was used only for the family-direction check (e), after a spot check:
  - harness Lane(candidate) equals my lane on 5,000/5,000 ticks;
  - the V294 lp nominal tracking-gain row reproduces 0.840/0.865/0.586/0.764/0.917 exactly.

**Candidate under attack:** the Kp bank 0xCB994 in all 28 records, X [0,8,54,100,208], Y [1248,1248,1104,960,960]; V294 everywhere else.

---

## 0. Verdict: SURVIVES_WITH_CHANGES

I could not make it fail on stability, and nothing here says "do not flash".

**The attempts that did not break it**
- **No instability anywhere.** No closed-loop pole goes unstable on any member, delay, J corner or stress topology where V294 is stable (394 inner cases, 344 record-anchored 20 Hz members) [E].
- **No limit cycle at the flown gains.** In my byte-exact nonlinear replay the candidate shows no limit cycle, including the record-calibrated worlds in which my simulator does reproduce route 71-old's limit cycle for V293 + fork rev 2 [E, model].
- **It never re-arms the cycle V294's trim suppressed.**
- **The nonlinear margin to a sustained cycle stays at or above ×1.75 of the flown fork gain.** V294's is ×2.0–3.0 [E, model].

**Pre-registered criteria that fired**

| criterion | pre-registered consequence | result |
|---|---|---|
| **A2** | REFUTED | Fired as written, marginally: tracked-pole ζ ×0.893 and ×0.900 against the 0.9 line, in 2 of 394 cases. Both are unidentified two-mass stress topologies at the 9 ms delay corner. My V282 linear lane would be unstable on both members, so the flown V282 record excludes them. On the 72 record-consistent stress cases the minimum ratio is 0.972 (§3). I adjudicate A2 as not decision-bearing, and say so openly: that is the one place my verdict departs from the letter of my own criteria. |
| **E1** | SURVIVES_WITH_CHANGES | Fired. The designer's "15–22 m/s hard-turn 1.6–3 Hz: no change" is not robust (§7). |

**A second defect, in the designer's goal-metric claim**
- The report says: "closed-form |α/cmd| ×1.10–1.16 at every frequency and on every member".
- That is a harness artefact. `alpha_per_cmd` feeds `ff_tf` at idx 60 with map′·Kp(60) and omits map·Kp′. The designer flagged this defect for M_DRIVE and M_LOOP but did not correct it for M_TRACK.
- With the true local slope [E, a13]:

  | idx | \|α/cmd\| cand / V294 |
  |---|---|
  | 4 | ×1.11–1.34 |
  | 30 | ×1.01–1.16 |
  | **60** | **×0.88–0.95** |
  | **90** | **×0.73–0.74** |

- So on hard turns the literal goal metric moves the **wrong way**.

---

## 1. Pre-registered criteria and what fired

| id | criterion (short) | result |
|---|---|---|
| R1 | Kp(idx) and T(idx) reproduce the designer's table | **PASS**. Kp 1248/1248/1217/1167/1117/1039/986/960 at idx 3…100; T 30→40 … 949→974. My listing-style LERP equals golden `lkas_rate_lerp` on 0/256 idx [E, a1] |
| R2 | \|P/x\| @20 Hz: V294 2.079, candidate 2.703, V282 44.90 (±1 %) | **PASS**: 2.079 / 2.703 / 44.900. My V282 lane includes Kd 128 and the sum operand [E, a1] |
| R3 | rail +2461/−2463, first reached at idx 239 | **PASS**, both builds [E, a1] |
| A1 | candidate unstable where V294 is stable | **not fired**: 0 of 394 [E, a2] |
| A2 | a tracked pole with ζ < 0.3 falls below 0.9× its V294 ζ | **FIRED as written** on 2 of 394 (0.893, 0.900). Adjudicated in §3 |
| A3 | Ms > 2, or Ms > 1.25× V294's | **not fired**. Worst candidate Ms 1.55 (nominal + T2 16 Hz stress, 9 ms delay) [E, a2] |
| B1 | on V282-anchored 20 Hz members, candidate ζ more than 0.005 below open, or more than 1.5× V294's shift | **not fired** in the pre-registered regime (ζ_open ≈ 0.05–0.08, n 71): shift −0.0030…+0.0035. My implementation widened the window to ζ_open ≥ 0.05; there the literal clause fires on 146 well-damped members (ζ_open 0.10–0.74). Reported, not decision-bearing (§4) |
| B2 | candidate's damping sign at 13–25 Hz differs from V294's and is anti-damping | **cannot fire**. The candidate's controller phase is identical to V294's at every delay; only the gain is ×1.30 [E] |
| C1 | identified member: candidate Ms > 1.6 or GM < 3 where V294 passes | **not fired**. `ms_free` at 12 m/s straights is 1.62 → 1.84, but V294 already exceeds 1.6 there (reported) |
| C2 | light_b: candidate GM < 1.5, or my Ms more than 15 % above the designer's | **not fired** at nominal assumptions (minimum 1.53; 22+ straight 1.57). It fires under sensitivity variants that also sink V294 (§5.4) |
| C3 | a describing-function or nonlinear limit cycle for the candidate but not for V294 | **not fired** (relay DF §5.5; nonlinear kicked-cycle test §5.6) |
| C4 | 0–5 m/s identified GM < 3 | **not fired** (≥ 7.19) |
| D1 | a new sustained line more than 6 dB above V294 in 0.5–8 Hz | **not fired** (304-lane nonlinear sim, §6) |
| D2 | P clamp binds more than 0.1 % hands-off | **not fired**. The P clamp is reachable only at idx ≥ 179, identical for both builds; 0 hands-off frames on the r71b march [E, a11] |
| D3 | a per-frame torque step more than 2× V294's at the slew cap | **not fired**: ×1.28 (109 against 85 T), and 84 against 84 T across the idx-100 kink [E, a11] |
| D4 | on-centre breakaways more than 3× V294 with a line | **not fired**: at most ×2, broadband (§6) |
| D5 | parametric Kp(idx(t)) pumping, a new line more than 3 dB | **not fired as a line**. The rise is broadband (§6) |
| E1 | a claimed direction reverses on some member, or 15–22 hard16 rises more than 10 % | **FIRED** (§7) |
| E2 | the central 22+ claim holds on nominal only | **not fired**. 22+ tracking +0.050…+0.060 on all 17 members, under lp and full [E, a9] |

---

## 2. Reproduction [E, a1, a9]

**Bytes**
- My writer of the candidate changes exactly **252 bytes** on the five pages 0xE4000–0xE8000.
- Its per-record blocks equal the designer's spec in 28 of 28 records.
- The V294 X knots differ by slot exactly as the designer reported.

**Lane and surfaces**
- My integer lane equals the golden model's `lkas_fb_lag` + `lkas_rate_pid_tick` on 20,000 random ticks each for V294, the candidate and V282: 0 mismatches.
- The static surfaces reproduce the designer's table to the count:
  - maximum increase +85 T at idx 51;
  - monotone;
  - rail at idx 239;
  - negative rail −2463.
- **The local slope is discontinuous at idx 100.** The exact per-idx surface increments are 6–9 T at idx 94–99 against V294's 9–12 T, then equal from idx 100. So the incremental FF gain jumps **0.67 → 1.00** at |0xE4| ≈ 1613.
  - The designer's minimum of "0.72" is the ±8-idx smoothed value.

**Outer-loop method check**
- My outer-loop linearisation equals the harness's `outer_frf` at small angle to within 1 % in Ms and 1.5 % in GM (nominal and light_b, 3–27 m/s).
- Under the designer's same-idx convention it reproduces their s12 rows to within 0.04:

  | light_b point | mine | designer |
  |---|---|---|
  | 22+ hold | 3.05/1.70 → 3.20/1.67 | 3.00/1.71 → 3.18/1.66 |
  | 22+ straight | 3.03/1.71 → 3.47/1.59 | 3.04/1.70 → 3.43/1.60 |

**Harness sweep, spot-checked and then used**
- It reproduces the designer's direction table: 22+ tracking +0.050…+0.060, 15–22 +0.049…+0.070, 10–15 +0.071…+0.102, 5–10 +0.024…+0.032.
- That covers all 17 members, including 11 the designer did not run.
- **Restart pulse:** 19/57/189/546 T at 10/30/100/300 deg/s, against the designer's 18/56/188/545. Above 50 T for 51 ms at 30 deg/s, against V294's 0 ms.

---

## 3. (a) The inner acceleration loop

**Method** [E, a2]
- An exact-ZOH (matrix-exponential) discretisation of the continuous plant plus the lane's own 1 kHz state equations.
- Deliberately not the harness's semi-implicit Euler.
- Two readouts:
  - discrete closed-loop eigenvalues, with every oscillatory pole tracked by continuation in Kp 960 → 1248 in 16-count steps;
  - Nyquist GM, PM and Ms.

**Cases (394)**
- the eight identified members plus light_b × five speeds;
- J ×0.5 and ×2.5 on nominal and light_b;
- light_b with b ×0.5, and with k ×0.35 (a soft spring at large angle);
- transport delay 0/4/6/9/12/18 ms, which is ×1.5–×3 of the 6 ms corner, on the rate former's 3 ms;
- two-mass stress modes (13, 16, 20 and 25 Hz; ζ 0.02–0.1; r2 0.2–0.5) in three topologies:
  - **T1**, the harness's: road on the motor, free hand-wheel;
  - **T2**: motor → compliance → rack carrying the road, sensor on the motor;
  - **T3**: the same with the sensor on the rack, non-collocated.

**Results**
- **Stability:** V294 and the candidate are stable in all 394 cases.
- **Ms:** at the family's own 2 ms delay, nominal 1.06 → 1.08 and light_b 1.12–1.14 → 1.15–1.17. That matches the designer's "Ms ≤ 1.17".
  - Worst over all delays and stress cases: 1.43 → 1.55.
- **GM** over the same 394 cases: V294 ≥ 4.09, candidate ≥ 3.14.
  - Harness convention at 2 ms: nominal 42 → 33.
- **Every pole V294 shifts, the candidate shifts by ×1.3** of V294's shift from the open plant (ratios 1.11–1.34). This is linearity: the candidate is V294's trim at ×1.30 gain with the same phase.
  - So "is any closed-loop pole less damped than on V294?" — **yes, every pole V294 already de-damps, by 1.3× V294's own shift.**
- **The two A2 hits:**

  | member | point | pole | ζ V294 → cand | ratio |
  |---|---|---|---|---|
  | nominal + T3 (13 Hz, ζ 0.1, r2 0.2) | 11.9 m/s, τ 9 | 5.8 Hz | 0.242 → 0.216 | 0.893 |
  | nominal + T2 (20 Hz, ζ 0.02, r2 0.5) | 26.9 m/s, τ 9 | 15.2 Hz | 0.128 → 0.115 | 0.900 |

  The worst lightly damped case (just above the line) is light_b + T2 20 Hz, ζ_open 0.050, τ 9: V294 0.0375, candidate 0.0338 (ratio 0.901).
- **Record-consistency filter** [E for the linear algebra; B for the filter's premise, a14]:
  - V282 flew for months with a ring at ζ ~0.016 and never diverged.
  - On 198 of 270 stress cases, including both A2 hits and the ζ 0.034 case, my V282 linear lane is **unstable** (ρ 1.02–1.03).
  - On the **72 record-consistent** cases:

    | measure | value |
    |---|---|
    | minimum tracked-pole ratio | 0.972 (0 below 0.9) |
    | poles with ζ < 0.06 | 6 |
    | their shift, candidate vs open | −0.0005 |
    | their shift, candidate vs V294 | −0.0001 |

  - ⚠ **Caveat [B]:** the filter uses V282's PID-only lane. V282's sibling r24 bar-derivative lane (arm 5244) is recorded as **damping at 20 Hz** (memory: "r24 pumps at 7 Hz and damps at 20 Hz") and is not in my model. So the filter may exclude some members that were in fact consistent. For that reason I report A2 as fired, not voided.
- **Harness-claim correction.** The designer's "stress-mode damping ≥ V294's at all nine points" holds only at the harness's default 2 ms delay. At 6–9 ms, T1 flips to anti-damping for both builds, the candidate by ×1.3: nominal + T1 20 Hz at τ 9 gives ζ 0.0740 open → 0.0716 V294 → 0.0708 candidate [E, a2].

---

## 4. (b) 20 Hz against the on-car record

**B3 — gain and phase** [E, a3]
- The lane's opposing torque per wheel rate is computed with the 3 ms former, the ZOH and the transport delay τ.
- 0° is pure damping; beyond −90° is anti-damping. The table shows the damping component in T per deg/s at 20 Hz:

  | τ | V282 | V294 | candidate | candidate / V282 |
  |---|---|---|---|---|
  | 0 ms | +2.58 | +0.063 | +0.082 | – (all damping) |
  | 2 ms | −0.92 | −0.100 | **−0.129** | 14 % |
  | 6 ms | −7.53 | −0.396 | **−0.514** | 6.8 % |
  | 9 ms | −11.34 | −0.557 | **−0.724** | 6.4 % |

  - At 13 Hz both V294 and the candidate damp for τ ≤ 2 ms.
  - At 25 Hz both anti-damp for τ ≥ 2 ms (V282 −3.28 at 2 ms).
  - The phase is identical for V294 and the candidate at every delay (−98.8° at 20 Hz, 2 ms). **The sign of the candidate's damping always equals V294's**; only the size is ×1.30.
- ⚠ **Correction to the designer.** "\|P/x\| 2.703 = a 16.6× margin to V282's flown grinding gain" is a magnitude ratio.
  - V282's phase at 20 Hz (−93.8° at 2 ms) is closer to pure spring than V294's (−98.8°).
  - So on the **anti-damping component** at the nominal 2 ms delay the margin is **~7×, not 16.6×**. It is 15× at 6–9 ms.
  - Not decision-bearing given the next point.
- **V282's loop alone makes a 14–22 Hz pole on the RIGID plant** [E, a3(1)]:
  - ζ 0.03–0.32 on nominal / b_lo;
  - unstable on J_lo and light_b at 6 ms.
  - The record's 20 Hz ring is reproducible as V282's own crossover resonance, with no plant mode at all.
  - The candidate's inner |L| at 20 Hz is ≈ 0.034 (0.84 T per deg/s against Jω ≈ 25). **A crossover resonance there is impossible for this candidate.**
- **Anchored stress members** [E for the model, a3(2)]
  - 18,000 (member × speed × topology × f2 × r2 × ζ2 × delay) combinations were screened.
  - **344** reproduce the record: V282 gives a 15–25 Hz pole at ζ 0.008–0.030 while the open plant's flexible mode has ζ ≥ 0.05.
  - On those members:
    - the candidate's ζ is ≥ 0.981 × V294's;
    - no member is unstable;
    - in the **record's own regime (ζ_open 0.05–0.08, n 71)** the candidate's shift from open is **−0.0030…+0.0035**, and candidate minus V294 is −0.0007…+0.0008. **B1 does not fire.**
  - The largest absolute shifts (−0.025) are on well-damped modes, ζ_open 0.31–0.36 → 0.31–0.34.

---

## 5. (c) The outer loop with the UNCHANGED fork law

### 5.1 My linearisation [E, adv_outer.py]

The fork's generic torque path, read from the extracted `latcontrol_torque.py`, `common/pid.py` and opendbc `get_friction`:

```
meas   = -cf(v)/sR(theta)*rad(theta)*v^2
e_lsf  = (sp - meas)*(1 + lsf(v)/kp)                   # lsf = (interp(v,[0,10,20,30],[12,10.5,8,5])/max(v,1))^2
u_la   = kp*e_lsf + i + ff + relay(e_lsf)              # i += ki*0.01*e_lsf ; relay slope 0.011*14/0.30 = 0.513
wire   = 4096*u_la/LAF                                 # 100 Hz ZOH, pipe 22 ms
T      = localslope(idx0) x out-lag + trim(Kp(idx0))   # u = -T(tau)
plant  : J th'' + b th' + k_loc th = u
```

- **One difference from the harness and designer: `k_loc = k·sech²(θ0/sat)`**, the tangent of the plant simulator's own spring `k·sat·tanh(θ/sat)` at the hold angle.
  - The harness's `outer_frf` and the designer's `pg_lib.outer_local` use the small-angle k at every operating point.
- **Operating points are matched on the same HOLD TORQUE.** The candidate therefore sits at its own lower idx: 38 → 32, 33 → 27, 75 → 68.

### 5.2 Anchors against the on-car record

**(A) Route 71-old limit-cycled** [memory `accord-v293-rev2-flew-route71…`]
- Configuration: V293 (same FF as V294, no trim) + fork rev 2 (Kp 0.85, relay live, Ki 0.30, LAF 14).
- Symptom: 2.34 Hz, ±6°, on every sustained curve above 20 m/s.
- My model at 21.8 m/s, 16–29°:

  | world | GM | at |
  |---|---|---|
  | **light_b** | **0.78–0.84** | 1.8–2.1 Hz (0.89–0.90 @2.44 Hz with the small-angle k) |
  | every identified member (nominal, b_lo, J_hi, J_hi2, ms_free) | 10–20 | – |

- ⇒ **The on-car record falsifies the identified family at sustained curves ≥ 20 m/s and supports light_b there** [E for the model; the record is EVIDENCE in memory].
- Independent support: light_b's static hold map predicts r71b's own sustained-curve holds [E, a4]:

  | speed | angle | predicted | V294 delivered |
  |---|---|---|---|
  | 26.9 m/s | 11.0° | 350 T | ~340 T (idx 33) |
  | 17 m/s | 18.4° | 395 T | ~390 T (idx 38) |

  The identified nominal needs about 1180 T at 17 m/s, 18.4°.

**(B) Route r71b (V294 + r1)** did not limit-cycle, and showed a rate-only 1.95 Hz, +10.3 dB line on hard curves above 15 m/s.
- light_b gives GM 2.42 / 2.14 / 1.60 and Ms 2.5–3.7 at 15–19 / 19–22 / 22+ m/s curves.
- Stable and lightly damped ✓.

**(C) r71b 22+ straights** (15 s only) [E, a6]
- Measured: a weak 2.3–2.7 Hz excess, +1.2 dB (angle), +1.9 (rate), +2.9 (command).
- A synthetic Ms ≈ 3 line added at 50–100 % of the rate's rms reads +4.4…+6.2 dB on the same detector.
- **[B]** The car at 22+ straights looks better damped than light_b's Ms 3.1 says; the exposure is too thin to reject it.

**Record-calibrated worlds** [E for the model, a7]
- Worlds: light_b with b ×β and J ×γ that satisfy (A) and (B): (β, γ) = (0.75, 0.5), (0.75, 0.75), (1, 0.5), (1, 0.75), (1, 1), (1.25, 1).
- Two of them also meet a soft (C) (V294 22+ straight Ms ≤ 2.5).

### 5.3 The candidate against V294 at the drive's operating points

**light_b, same hold torque, relay on, 22 ms** [E for the model, a5]

| op point (v, angle, idx V294 → cand) | V294 Ms / GM | cand Ms / GM |
|---|---|---|
| curve 15–19 (17, 18.4°, 38 → 32) | 2.48 / 2.42 | 2.52 / **2.45** |
| curve 19–22 (20.5, 9.8°, 38 → 32) | 2.49 / 2.14 | 2.50 / **2.16** |
| curve 22+ (26.9, 11°, 33 → 27) | 3.66 / 1.60 | 3.66 / **1.61** |
| straight 22+ (26.9, 0.6°, 5 → 4) | 3.08 / 1.69 | **3.57 / 1.57** |
| straight 15–22 | 2.00 / 2.63 | 2.18 / 2.44 |
| straight 10–15 | 1.72 / 3.45 | 1.85 / 3.21 |
| straight 0–5 (low-speed factor) | 1.86 / 4.49 | 2.05 / 4.21 |
| hard 5–10 (8, 76°, 75 → 68) | 2.53 / 3.11 | 2.29 / **3.77** |
| low-speed turn (3.1, 161°, 80 → 74) | 2.33 / 3.44 | 2.09 / **4.28** |

**Across all six calibrated worlds (72 comparisons)** [E, a7]
- Straights: GM ×0.91–0.97, Ms ×1.05–1.16. The minimum candidate GM is **1.55** at 22+ straights (V294 1.64).
- Highway holds (idx 18): GM ×0.95–0.98.
- Curves at speed: GM ×0.99–1.04.
- Hard 5–10 and low-speed turns: GM ×1.20–1.26.
- No world gives a candidate GM below 1.2.

**Identified members:** GM ×0.79–0.95 on straights and ≥ 1.0 in turns. Minimum candidate GM 4.16 (`ms_free`, 12 m/s straights, J 2.1 unidentified); nominal ≥ 8.9.

⚠ **Correction for both builds.** Using the tangent spring lowers the light_b curve margins below the small-angle numbers the designer quoted: 22+ curve Ms 3.66, not ~3.0. The candidate is **no worse than V294** on curves, because its trim rises ×1.16–1.2 while its local FF slope rises only ×1.02–1.13 there. On straights it is worse by ×0.91–0.95 in GM.

### 5.4 Sensitivity at the highway-straight point (light_b)

| variant | V294 GM | cand GM | designer's G5 floor, min(V294's, 1.5) |
|---|---|---|---|
| pipe 22 ms (nominal) | 1.69 | 1.57 | pass |
| **pipe 33 ms (×1.5)** | 1.42 | **1.30** | **FAIL** |
| pipe 44 ms | – | – | – |
| **κ 1.15** (the fork reads the wheel angle, the plant the rack) | 1.47 | **1.36** | **FAIL** |

- [E for the model]
- The measured pipe is 20 ms plus about 2 ms [E, harness H3a], so the ×1.5 variant is pessimistic.
- For light_b (fitted on the wheel angle) κ is probably already inside the fit [B].
- **Stated so the pre-registration is honest:** G5 passes only at the nominal delay and κ 1.0.

### 5.5 The friction relay as a describing function [E, a15]

- `get_friction` is `interp(e, [-0.30, 0.30], [-f·LAF, +f·LAF])`. That is a **saturation** of slope 0.513, whose DF runs from 0.513 down to 0.
- Sweeping N over [0, 0.513]: GM is monotone in N at every operating point and every member (light_b, nominal, b_lo). The minimum is always at N = 0.513, which is the linear "relay on" case.
- ⇒ **No relay-induced limit cycle** is possible for either build when the relay-on loop is stable. C3 does not fire on the relay.

### 5.6 A nonlinear gain margin with a working positive control [E for the model, a10, a12]

**Positive control, first attempt (a8 part 1, reported): FAILED**
- On light_b with its prior friction (Fc 31.5 / Fs 52.5 T), nothing limit-cycles from 5 T road noise, V293 + rev 2 included. The plant sticks.

**Positive control, second attempt (a10): works**
- Kick each lane (3 s of 2.3 Hz curvature modulation at ±40 %), then read 7–37 s after the kick.
- World: light_b dynamics with the identified friction ×2 (F_hi, ~12/16 T at 22 m/s).
- **V293 + rev 2 SUSTAINS** a 2.73 Hz, 9.7° p-p, command 451 p-p cycle at 21.8 m/s, 16° (β 0.75, γ 0.5). That is route 71-old's signature (2.34 Hz, ±6°, command ±300).
- It runs away at 26.9 m/s, 11° in two worlds.
- **V294 + r1, V294 + rev 2, candidate + r1 and candidate + rev 2 never sustain in any world or at any operating point.** Post-kick rms is ≤ 0.38 deg/s.
- A small residual 3.5 Hz, +5 dB, 0.1–0.2 deg/s shows on the candidate in two cases where V294 reads 0.00: stick-slip hunting at the higher gain.

**Nonlinear GM (a12)**
- Definition: the smallest multiplier g on SteerKP at which a kicked cycle sustains.

| op point | V294 g* | cand g* | ratio |
|---|---|---|---|
| straight 26.9 m/s | 2.0 / 3.0 / > 3 | same | **1.00** |
| curve 26.9 m/s 11° | 2.0 / 2.5 / 3.0 | 1.75 / 2.0 / 2.5 | **0.80–0.88** |
| 21.8 m/s 16° | 2.5 / 2.5 / 3.0 | 2.5 / 2.5 / 2.5 | 0.83–1.00 |
| 17 m/s 18.4° | 3.0 / 3.0 / > 3 | same | 1.00 |
| 12 m/s straight | > 3 | > 3 | – |

- The linear analysis said highway curves were neutral (×0.99–1.03). The large-amplitude test disagrees because the kicked cycle swings idx down into the ×1.2–1.3 region.
- **The candidate spends up to 20 % of the nonlinear margin on highway curves.** At the flown fork (g = 1) neither build cycles.
- The V294 trim is what bought that margin: g* < 1 → ≥ 2.0 against V293 + rev 2 in the same worlds.

---

## 6. (d) Nonlinear traps [E, a8, a11]

**Static checks and the r71b march** [a11]

| trap | result |
|---|---|
| P clamp (arithmetic, \|E\| ≤ 4·map + C) | reachable only at idx ≥ 179 for both builds. At idx ≤ 100 the worst case \|E\|·Kp>>8 with r26 at −C is 10,290 (idx 100; 5,655 at idx 8), below 15,360 |
| P clamp on r71b | hands-off 0 / 0 frames; all-engaged 114 / 114 frames (identical) |
| fb clamp C | never binds on r71b hands-off, either build |
| max \|T\| hands-off | 1319 / 1319 |
| per-frame static torque change at the 123-count slew cap | 85 → **109 T** (×1.28, at small idx); **84 → 84 T** across the kink |

**The idx-100 kink**
- The local slope jumps 0.67 → 1.0 [E, a1].
- Test: a command dithering ±12 % at 1 Hz across idx ~100 at 8 m/s.
- Result: 1.6–3 Hz wheel rate rises **×1.9–2.1** on nominal, F_hi and b_lo (0.8 → 1.7 deg/s, harmonics of the dither), while the 1 Hz fundamental falls (×0.88).
- In light_b-type worlds the same angle sits at idx ~70, so the kink is not crossed: ×1.06–1.32.
- On r71b, idx ≥ 100 is 2.5 % of 0–10 m/s hands-off frames (a4) [E].
- ⇒ The kink matters only on the hardest low-speed turns. Magnitude in the car's own terms [B]: +0.9 deg/s of 1.6–3 Hz on hard turns that measured 14.9 deg/s there.

**On-centre** (crown 15/60 T, planner wander, road noise; 8 worlds × 5 speeds; 80 s; my plant and the fork port) [a8]
- No limit cycle and no new line more than 6 dB (D1 not fired).
- **Broadband 1–3 Hz wheel rate rises:**

  | worlds | speeds | rise |
  |---|---|---|
  | identified | 12–27 m/s | ×1.25–1.45 |
  | light_b and the three calibrated worlds | 22–27 m/s | **×1.24–1.58** (light_b 22 m/s: 0.80 → 1.22 deg/s) |
  | all | 8 m/s | ×1.25–1.38 |

- 3–8 Hz: ×1.1–1.65.
- Stick-slip breakaways: ×1.5–2.1 at 22–27 m/s in light_b-type worlds, flat on the identified family.
- ⇒ The designer's disclosed "+9–30 % (lp)" straight-line cost is **understated in the record-consistent worlds (+30–60 %)**. The harness's own lp over 17 members gives ×1.05–1.38.

**13–17 Hz (the record's shoulder band)**, upper bound [B]
- If the whole engaged excess at hands-off 8–15 m/s (engaged ÷ disengaged 1.88, V294 0.383 deg/s = ×0.88 of r6c) is FF-driven and scales ×1.3 at small idx, the candidate reads **≤ ×1.07 of r6c**.
- That is under the kit's ×1.5 REVERT gate. It is a watch item on the existing scorer.

---

## 7. (e) Do the claims move in the claimed direction across the family?

**Harness `sweep_drive`** on 17 members: the designer's 6, plus J_lo, J_hi2, J_0.3, b_hi, F_lo, tau0, ms_free, nominal_kappa, and my three record-calibrated worlds. Both lp and full [E for the model, a9].

| claim | across 17 members | verdict |
|---|---|---|
| 22+ tracking up | +0.050…+0.060, lp and full, all members | **robust** |
| 22+ turn-hold up | +0.031…+0.076 | robust |
| 15–22 tracking / hold up | +0.049…+0.070 / +0.071…+0.124 | robust (15–22 is DIRECTIONAL in the harness) |
| 10–15 tracking up | +0.071…+0.102 | robust |
| 5–10 hard-turn 1.6–3 Hz down | ×0.80–0.91 (lp), ×0.94–0.97 (full) | **robust** |
| **15–22 hard-turn 1.6–3 Hz "no change"** | **lp: up on 13/17 (×1.04–1.14); above ×1.10 on 5** (J_0.3 1.13, F_hi 1.12, nominal_kappa 1.14, light_b 1.11, cw_b1_J.5 1.13). full: ×0.99–1.00 | **E1 FIRES: not robust** |
| 22+ hard-turn 1.6–3 Hz (not gated by the designer) | lp ×0.85–1.26 (nominal 1.22, cw_b.75 1.26) | a cost |
| 1–3 Hz wheel rate, straights and holds | lp ×1.05–1.38 at 0–5, 10–15, 15–22, 22+ | a cost (see §6) |
| J error (0.15–2.4 Hz) | ×0.82–0.96 at ≥ 10 m/s | robust improvement |
| 1–5 Hz limit-cycle peak | no rise above 3 dB; light_b and calibrated worlds improve 1–1.7 dB (lp) | robust |

**My own nonlinear ramps at 17 m/s, 22°** (1.5 s turn-in, 4 s hold, 1.5 s out; a8)
- Hard 1.6–3 Hz: **×1.14–1.24** in light_b and all three calibrated worlds; ×0.92–1.0 on the identified family.
- At 12 m/s (52°): ×0.98–1.14. At 8 m/s: ×0.88–1.13.
- ⇒ In every world consistent with route 71-old's record, the candidate **raises** loop-generated 1.6–3 Hz motion in 15–22 m/s hard turns by 7–24 %. That is the band of r71b's 1.95 Hz rate line and, arguably [B], the operator's "medium speed".
- The designer's "15–22 ×0.99 (full), ×0.99–1.12 (lp; worst light_b). No change, with a light_b tail" understates this. **The tail is the record-consistent world.**
- Magnitude caveat [B]: the harness grades plant-alone 1–8 Hz as NOT FIT, and under `full` the change is ×0.99–1.00.

**Goal metric (cmd → α)** [E, a13, my closed form with the true local slope, 8 members × 4 speeds × 0.5–5 Hz]

| idx | \|α/cmd\| cand / V294 | phase change |
|---|---|---|
| 4 | ×1.11–1.34 | ±6.5° |
| 30 | ×1.01–1.16 | – |
| 60 | ×0.88–0.95 | – |
| 90 | ×0.73–0.74 | – |

- The designer's "×1.10–1.16 at every frequency on every member" is the harness's `alpha_per_cmd` / `ff_tf` evaluated at idx 60 with map′·Kp(60): it omits map·Kp′.
- The small-amplitude flatness (0.35 → 0.50) and the mode-A literal R² come from the byte-exact simulation and are not affected by this.

---

## 8. Required changes (to the claims and to the drive's instruments; no byte change is required by this adversary)

1. **Correct the goal-metric claim (§7).** The closed-form |α/cmd| rises for small commands and **falls ×0.73–0.95 for idx 60–100 (hard turns)**. Quote the true-local-slope numbers; drop "×1.10–1.16 on every member".
2. **Restate the hard-turn prediction.**
   - 5–10 m/s: down, robust.
   - **15–22 m/s: up ×1.04–1.14 (lp, 13/17 members, every record-consistent world) and ×1.14–1.24 in nonlinear ramps. Flat under `full`.**
   - Add a **REVERT trigger on the 15–22 m/s matched hard-turn 1.6–3 Hz cell (bands §2.1b) at more than ×1.10 against r71b**, alongside the designer's 5–10 m/s trigger.
   - Pre-register that **S7/P4's rate line on hard curves above 15 m/s (r71b: 1.95 Hz, +10.3 dB) must not grow by more than 3 dB or move into 2.0–2.7 Hz**.
3. **Restate the straight-line cost.**
   - 1–3 Hz wheel rate on straights and holds: ×1.3–1.6 in record-consistent worlds, not +9–30 %.
   - Pre-register the on-wire read: hands-off straights 1–3 Hz rms by band against r71b (22+: 1.06 deg/s).
   - Pre-register that a rise above ×1.6 goes to the operator as the "nervous on highway straights" risk.
4. **Disclose that G5 fails under sensitivity:** pipe ×1.5, or κ 1.15, puts the light_b 22+ straight GM at 1.30–1.36, below V294's 1.42–1.47.
   - And that, with the tangent spring, the light_b curve margins are lower for **both** builds (22+ curve GM 1.60, Ms 3.66).
   - The candidate is not worse than V294 on curves.
5. **Record A2 as fired as written.** It is the linear ×1.3 of V294's own shift, on unidentified stress topologies at 9 ms, excluded by an approximate V282-record filter (§3). Correct "stress-mode damping ≥ V294's at all nine points" to "at 2 ms delay only".
6. **Record the idx-100 kink** (incremental FF gain 0.67 → 1.0) and its harmonic signature (×2 of 1.6–3 Hz under a command straddling idx 100). It is confined to about 2.5 % of low-speed frames.
7. **Correct "16.6× margin to V282's grinding gain"** to ~7× on the anti-damping component at 20 Hz for the nominal 2 ms delay (15× at 6–9 ms). It is not decision-bearing: the record-anchored shift is ≤ 0.003.

---

## 9. What I believe but could not show (BELIEF, stated so nobody relays it as fact)

- **Which world the car is in at speed.**
  - Route 71-old's cycle and r71b's hold torques favour light_b's statics and its lightly damped mode on sustained curves ≥ 20 m/s.
  - r71b's 22+ straights (15 s) look better damped than light_b.
  - The candidate's cost is on straights; its benefit or neutrality is on curves. A world where straights at speed are near-marginal is not excluded by 15 s of data.
- **The nonlinear GM and every simulated wheel-motion magnitude** depend on my friction and noise models. The positive control works only with the identified-×2 friction, not light_b's prior friction.
- **V282's r24 lane** is not modelled, so the record filter in §3 is approximate.
- **Nothing above ~8 Hz is identified.** Every 13–25 Hz statement rests on stress members, and on the one on-car anchor (V282's ring, V294's clean HF).

## 10. Files (all in `analysis-2020accord/studies/v295/design/p-gain/adv_stability/`)

**Criteria:** `ADV-stability-p-gain-CRITERIA.md`, pre-registered.

**Libraries**

| file | contents |
|---|---|
| `adv_lib.py` | decoder, candidate writer, listing LERP, integer lane, linear lane TFs |
| `adv_lin.py` | exact-ZOH closed loop and Nyquist; T1/T2/T3 two-mass |
| `adv_outer.py` | fork linearisation with the tangent spring |
| `adv_sim.py` | nonlinear simulator: my vectorised lane + Karnopp plant + `ForkPort` |

**Scripts** (each with an `*_out.txt`, and `*.json` where noted)

| script | covers |
|---|---|
| `a1_spotcheck` | R1–R3, lane vs golden |
| `a2_inner` | (a), 394 cases (json) |
| `a3_20hz` | (b) |
| `a4_oppoints` | the drive's op points |
| `a5_outer` | (c): method check, anchors, grid |
| `a6_straight_spectra` | anchor C |
| `a7_calibrated_world` | – |
| `a8_nlsim` | positive control part 1 (failed as run), 304-lane scenarios |
| `a9_family_directions` | harness sweep, 17 members |
| `a10_posctrl` | kicked positive control |
| `a11_traps` | – |
| `a12_nl_gm` | – |
| `a13_alpha_cmd` | – |
| `a14_record_filter` | – |
| `a15_relay_df` | – |

**Raw sim traces:** `adv_stability/_scratch/_scratch_*.npz` (moved there after the runs; a8 writes them beside itself), regenerable.
