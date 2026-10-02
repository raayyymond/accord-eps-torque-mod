# REFUTE (inference): the route-79 synthesis's top mechanisms and its R1 / D-sign ruling

**Target:** `docs/scoring/DRIVE-READ-V298-r79-2026-10-02.md` (the synthesis). **Role:** refuter of the inference, not the data.
I attacked each top-ranked mechanism with the confound that fits the same data, then ran one discriminating analysis
the reports did not run. Where I was unsure I defaulted to "refuted".

**Script:** `analysis-2020accord/studies/angle_loop/v298_flight/refute_inference.py`. It reads the cache only and is vectorised.
- Wall time: **2.6 s** for the whole process (1.1 s inside the script).
- Output: `_scratch/out/r79/refute/refute_inference.{txt,json}`.
- It reuses M4's own grids and stall-surge detector (`m4_common.build_grid`, `m4_episodes.stall_surge`, `m4_episodes.freeze_states`), unmodified.
- Nothing was sent, flashed or edited outside `v298_flight/` and `_scratch/`.

**Labels:** EVIDENCE = measured on the wire or the fork logs, or read from source. BELIEF = modelled or inherited.
The operator scores the symptoms; I score bands. Throughout, "hard" uses the judge's definition: latActive and (|θ| > 30° or |rate| > 60 deg/s).

---

## 0. Verdicts at a glance

| # | synthesis claim (its rank) | my verdict | the deciding number |
|---|---|---|---|
| V1 | D **opposes** motion, so the R1 "INVERTED" band is withdrawn | **SURVIVES** | Adding a setpoint-rate regressor gives c_D,true **+0.20 to +0.50 in 20 of 20 cells**. A sign flip would need the tap to *lead* by 40 ms or more (R² 0.53 against the 0.89 peak), or the wire angle to lag the firmware's angle by 32–115 ms. |
| V2 | Note 2 #1 (strong): the fork's **120 deg/s cap** is the top binder in hard manoeuvres | **REFUTED as ranked** | The cap binds on **17.4 % of all hard time**, not 50 %. 64 % of the cap frames are **unwinds** (return to centre). Hands-off turn-in under the cap totals **≈ 5.4 s of 116.5 s (4.6 %)**. |
| V3 | C5: O1 trips on the **hands-off reaction twist** (345 of 415 episodes never pressed) | **REFUTED by time** | **86.9 s of the 100.8 s of O1 (86 %)** lies in the 70 episodes where steeringPressed was set. The 345 short twist episodes total **12.3 s**. |
| V4 | Note 2: the hard manoeuvres were hands-off servo tasks | **REFUTED** | Of 116.5 s of hard frames: steeringPressed **53 %**, hand-like O1 **58 %**, sd_enabled **0.0 %** (all always-on-lateral), blinker on **57 %**. |
| V5 | Note 4 #1 (strong): the **O1 relay** is the ratchet | **REFUTED as causal** | Stall-surge rate is **66.4 /min** with no O1 within ±0.5 s against **63.2 /min** with O1 near (5–10 m/s). M4's own pooled numbers are 40.98 vs 41.82, and no report cited them. |
| V6 | Note 4 #3 (weak): freeze chatter is "not enriched" | **REFUTED: it is the enriched one** | Near a crossing of \|bar\| 300 or 512: **80.7 vs 30.3 /min** (5–10 m/s) and **47.4 vs 8.4** (0–5). The same split on V282 and V294, which have no freeze, shows **no** enrichment. |
| V7 | "The firmware follows what it receives" (reach 0.998, rate 0.98) | **REFUTED inside cap runs** | In the 11 cap runs ≥ 0.3 s: wheel rate **0.90 × 120 deg/s**, error grows **+9.9 deg/s**, median error **7.7°**, tap p50 **14–97 LSB** (5–32 % of the rail). |
| V8 | Note 3 #1 (strong): the bar is a lateral-acceleration **request** / 0.3247 | **SURVIVES, sharpened** | In `TorqueBar._update_state` the actual lateral acceleration **cancels algebraically**: bar = (a_des − roll·g·k(v)) / 0.3247. It carries no measurement of the wheel at all. |
| V9 | The firmware rail is not the binder | **SURVIVES** | Tap max 183 LSB; 0 frames ≥ 300 (judge = M2; not re-attacked). |

---

## 1. The R1 / D-sign ruling (V1): attacked on identifiability, and it SURVIVES

**The attack.**
- In a band-pass regression tap ~ c_P·ew + c_I·∫ew + c_D·ω, a timing error δ on the P term leaks into the ω coefficient as 10·c_P·δ·(ω − θ̇sp).
- With c_P ≈ 0.6–0.9 tap per wire count, that leak is about 6–9 tap per deg/s per second of δ.
- A 50 ms mismatch is therefore about ±0.3–0.45, the same size as the claimed c_D.
- The judge's lag scan covered only L ≥ 0 and had no θ̇sp regressor. Its "positive at every lag 0–80 ms" therefore does not separate D from timing.

**The discriminating analysis.**
- I added θ̇sp (from the 0xE4 field) as a fourth regressor. A shared timing artefact then lands with equal and opposite signs on ω and θ̇sp, so **c_D,true = b_ω + c_sp**.
- I scanned L from −40 to +80 ms.
- I printed the angle-only timing offset that would flip the sign, d_flip = −c_D,true / (10·c_P).

| band | 2–5 Hz, ω = carState rate: b_ω / c_sp → **c_D,true** | 2–5 Hz, ω = d(ang)/dt | 0.3–3 Hz, ω = carState rate | 0.3–3 Hz, d(ang)/dt | d_flip (ms, needed) |
|---|---|---|---|---|---|
| 5–8 | +0.477 / −0.025 → **+0.452** | +0.377 | +0.342 | +0.260 | −45 to −89 |
| 8–12.5 | +0.413 / +0.043 → **+0.455** | +0.380 | +0.228 | +0.203 | −52 to −104 |
| 12.5–22 | +0.438 / +0.059 → **+0.498** | +0.384 | +0.447 | +0.365 | −77 to −115 |
| > 22 | +0.364 / +0.107 → **+0.471** | +0.310 | +0.487 | +0.396 | **−32** to −50 |
| pooled > 5 | **+0.463** | +0.379 | +0.254 | +0.195 | −41 to −92 |

**Lag scan** (pooled, 2–5 Hz, as R² / c_D,true):

| L | −60 ms | −40 ms | 0 ms | +30 ms | +40 ms | +80 ms |
|---|---|---|---|---|---|---|
| R² | 0.53 | 0.53 | 0.76 | **0.89** | 0.88 | 0.63 |
| c_D,true | −0.18 | −0.01 | +0.34 | **+0.46** | +0.46 | +0.29 |

**Independent timing anchors:**
- Sign-aware cross-correlation puts the tap **50 ms behind** ew at 0.3–3 Hz.
- The 0x18F rate is at lag 0 against d(0x14A angle)/dt, with the opposite sign (the expected wire sign).
- The carState rate is at lag 0.

**Verdict.**
- **D opposes in every cell** (EVIDENCE, two ω sources, two bands, with the setpoint term).
- A flip needs a physically backwards timing: the tap leading by ≥ 40 ms, or 0x14A lagging the firmware's angle by ≥ 32 ms.
  - Firmware P uses the two-sample sum 8θ[n] + 8θ[n−1] of a 100 Hz hold, so its angle is *older*, not newer (`docs/traces/TRACE-2026-10-02-fresh-rate-D-sign-and-pol.md` §2).
  - That makes the flip direction implausible (BELIEF on the packer age).
- The trace's byte reading (pol = −1, D enters with + and is multiplied by pol at the output) agrees.
- **Caveat the synthesis under-states:** the *magnitude* sits **below the LIVE band floor of 0.45 in 14 of 20 cells** (0.20–0.50 against the design's 0.566).
  - "D at design strength" is **not** established.
  - That matters for §3 (H), where D is the term braking the wheel.

---

## 2. Note 2: "high-angle / high-jerk / high-authority / high-torque manoeuvres seemed lacking"

### 2a. The denominator (V2, V3, V4): what the hard manoeuvres were

The synthesis's headline "the cap binds on 50–52 % of **hands-off** hard frames" is real. But hands-off is only a third of hard time.

| band | hard s | O1 % | O1 inside a pressed episode % | steeringPressed % | hands-off % | **cap, of ALL hard %** | cap, of hands-off hard % |
|---|---|---|---|---|---|---|---|
| < 5 | 55.1 | 69.9 | 65.4 | 62.1 | 29.0 | **17.7** | 61.1 |
| 5–8 | 40.5 | 64.3 | 57.3 | 53.2 | 33.6 | **22.3** | 66.5 |
| 8–12.5 | 17.8 | 49.1 | 42.7 | 31.1 | 49.1 | **8.0** | 16.3 |
| > 12.5 | 3.0 | 34.0 | 21.5 | 20.5 | 61.7 | **0.0** | 0.0 |
| all | **116.5** | **63.8** | **58.0** | **53.2** | **34.6** | **17.4** | 50.3 |

**O1 by time, not by count (EVIDENCE):**
- 415 episodes, 100.75 s in all.
- The 70 episodes in which |steeringTorque| exceeded 1200 are exactly the 70 in which steeringPressed was set. They carry **86.9 s**.
- The 345 never-pressed episodes carry **12.3 s** (≤ 50 ms each).
- In hard frames, O1 time is 74.4 s, of which **67.6 s is hand-like**.

**Context (EVIDENCE):**
- **sd_enabled = 0.0 % of hard frames.** Every hard manoeuvre was always-on-lateral, against 11 % sd_enabled over all latActive time.
- The **blinker was on in 57 %** of hard frames, and in 73 % of the pressed ones.

**The alternative that fits the same data:** the large-angle manoeuvres were **intersection or street turns the operator steered by hand** with AOL active. In that state the system yields by design:
- the O1 setpoint is the wheel;
- the firmware fade is ×0.30 at the |bar| p50 of 2289 (fadeB at |bar|/32 = 71 → 77/255; M2 cell read);
- the I is frozen (|bar| > 512).

The 6× lane is then mostly out of the loop, and the driver feels roughly stock assist plus 30 % of a lane whose error is about zero. *That is the 6× not being felt.*
- That the operator felt this is BELIEF.
- That it is what the system did is EVIDENCE.

**Was the grab a reaction to a lagging setpoint?** Mostly not. Window: 0.5 s before each of the 48 hand-like O1 episodes that touched a hard manoeuvre, against random hard non-O1 frames.

| | before the hand episodes | base |
|---|---|---|
| desired − applied, p50 | 16.2° | 12.9° |
| share with a > 10° gap | 65 % | 55 % |
| cap active in the window | 81 % | 82 % |

There is little enrichment, so the cap-to-grab chain is not supported. It is not excluded on n = 48.

### 2b. What the cap frames are (V2)

| set | s | wind-up (turn-in) | unwind (return) | hold |
|---|---|---|---|---|
| hard | 116.5 | 0.40 | 0.40 | 0.20 |
| hard & hands-off | 40.3 | 0.23 | **0.50** | 0.28 |
| hard & hands-off & **cap** | 20.3 | 0.27 | **0.64** | 0.09 |
| hard & hands-off & cap & v < 8 | 18.8 | 0.25 | **0.66** | 0.09 |
| hard & hand-like O1 | 67.6 | **0.49** | 0.34 | 0.17 |

**The cap mostly binds while the wheel returns to centre after the operator lets go.** Turn-ins happen with the hand on.
- Hands-off turn-in under the cap is about 5.4 s, 4.6 % of hard time.
- 79 % of cap frames fall within 0.5 s of an O1 release, against a 68 % base. That is mild enrichment: on release the limiter restarts from θ (`_update_angle`), so part of the cap time is the **re-slew after the hand lets go**.

### 2c. The firmware does not follow even the capped setpoint (V7, and a mechanism the synthesis did not rank)

**Cap runs ≥ 0.3 s (n = 11):**
- wheel rate along the setpoint p50 **0.90 × 120 deg/s** (p10 0.86);
- error grows at a median **+9.9 deg/s**; median error in the run **7.7°**;
- tap p50 per run 9–97 LSB, max 128 (≤ 42 % of the rail).

**Fast hands-off slews (|ω| > 60 deg/s, |θ| > 5°, no O1, not pressed), split by direction:**

| v band | direction | s | \|ω\| p50 | **net lane drive along the motion, p50 (LSB)** | share driving | error along the motion p50 | D at c_D 0.45 / 0.566 |
|---|---|---|---|---|---|---|---|
| < 5 | unwind | 6.8 | 110 | **−26** | 0.23 | +4.3° | 50 / 62 |
| 5–10 | unwind | 4.4 | 96 | **−37** | 0.19 | +4.9° | 43 / 54 |
| 5–10 | wind-up | 1.2 | 74 | +78 | 1.00 | +6.0° | 33 / 42 |

In hands-off returns the setpoint is **4–6° ahead of the wheel**, yet the lane's net torque **opposes the motion on 66–81 % of frames**.
- The arithmetic: D on the *measured* rate (Kd 48, about 0.45–0.57 tap/(deg/s) measured) contributes 43–62 LSB of braking at 100–120 deg/s.
- P at 4–6° gives about 30–45 LSB.
- So D outweighs P, and the wheel settles about 5–8° behind a 120 deg/s setpoint.

The status is mixed:
- EVIDENCE: the sign and the size of the net drive.
- BELIEF: the split into P and D, which uses the measured c_D and the design slope.

The self-aligning torque drives these returns, so the braking is not unsafe. But it is a **rate ceiling set by the firmware's D-on-measurement**, sitting under the fork's cap. Lifting the cap alone would not buy the 2× rate the cap suggests.

### 2d. Note 2 re-ranked

See `mechanisms` in the return value. In short:
1. **Hand-on override by design** (O1 + fade ×0.30 + I freeze), during AOL intersection turns. **Strong** that it acts on 58 % of hard time; that the operator felt it is BELIEF.
2. **The firmware's slew follow-up** (D on the measured rate plus a low-speed P slope of about 7 LSB/deg). **Moderate**: the wheel runs at 0.90 × the cap with a growing error and the tap far below the rail.
3. **The fork's 120 deg/s cap.** **Moderate, not strong**: 17 % of hard time, two thirds of it in returns to centre, and partly the re-slew after O1 release.
4. Highway authority (error clip 16–18 % of the rail, VM jerk cap). **Untested**: 3 s of hard frames above 12.5 m/s.

Ruled out: the rail (agrees with the synthesis).

---

## 3. Note 4: "stuttery / ratchety at times"

**The attack on #1 (O1 relay).** O1 sits on 75 % of low-speed turning frames, so the event-locked order cannot carry causation. M4 says so itself, and M4's own unpublished-in-synthesis line is decisive: stall-surge **40.98 /min with no O1 within 0.5 s, against 41.82 with O1 near** (`_scratch/out/r79/m4/m4_episodes.txt`).

**My discriminating analysis.** The same M4 detector, split by masks that are applied identically to r79 and to the references. The references are the control, because they have neither O1 nor the V298 integrator freeze.

Format: turning seconds, n, per minute.

| route, band | free of \|bar\| > 614 (O1 level) ±0.5 s | near | **free of a \|bar\| 300 / 512 crossing ±0.25 s** | **near** |
|---|---|---|---|---|
| **r79 V298 0–5** | 5.8 s, 1 | 52.0 s, 26, 30.0 | 28.6 s, 4, **8.4** | 29.1 s, 23, **47.4** |
| **r79 V298 5–10** | 8.1 s, 9, 66.5 | 56.0 s, 59, 63.2 | 21.8 s, 11, **30.3** | 42.4 s, 57, **80.7** |
| r6c V282 0–5 / 5–10 | — | 33.6 / 23.2 | 27.2 / 23.1 | 30.0 / **21.8** |
| r39 V282 0–5 / 5–10 | — | 21.8 / 18.4 | 12.8 / 35.9 | 22.7 / **14.0** |
| r71b V294 0–5 / 5–10 | — / 20.1 | 31.0 / 38.0 | 20.1 / 37.9 | 30.8 / **28.0** |

r79 split by the **reconstructed O1** (±0.5 s), 5–10 m/s: free **66.4**, near **63.2**. At 0–5 it is 9.7 (n = 1, 6 s) against 30.2.

r79 split by an **integrator-freeze toggle** (the `m4_episodes.freeze_states` predicates), 5–10 m/s:

| subset | stall-surges /min (n) |
|---|---|
| near a toggle | **80.1** |
| free of toggles | 32.4 |
| near a toggle, with O1 absent within ±0.5 s | **86.3** (n 9) |
| near an opposing-only freeze (300 < \|bar\| ≤ 512) | 83.3 |
| free of opposing-only freezes | 28.6 |

**Reading:**
- (EVIDENCE) Away from a |bar| 300/512 crossing, r79's stall-surge rate (8.4 / 30.3) is at or below the references (12.8–27.2 / 23.1–37.9).
- (EVIDENCE) **The whole r79 excess sits within ±0.25 s of a |bar| crossing of 300 or 512.** These are exactly the V298 cave's opposing-freeze and hard-freeze thresholds (design §1.4). The references show **no** enrichment near the same crossings (0.4–1.1×), so "surges make bar spikes" (reverse causality) does not reproduce where the freeze is absent.
- The excess survives with O1 absent (86 /min, n 9). O1 does not enrich the rate.

**Mechanism (BELIEF):**
- When the wheel decelerates into a stall, its reaction twist crosses 300 opposing E′ and freezes the I exactly when the I should build to break friction.
- The stall then lasts until P alone breaks away, the surge twists the bar past 512, and the cycle repeats.
- The fade cannot be this relay: fadeB is flat (255) up to |bar| 512 and only reaches 218/255 at 1216 (M2 cell read).
- The freeze alters the I *rate*, not the I *level*. A freeze cannot by itself collapse torque; it can only lengthen the stall.

**Caveats:** n is 57 near-crossing events at 5–10 m/s and 9 O1-free ones. r79's own deeper surges could raise its crossing rate. The reference control bounds that, but cannot exclude it.

**Rate cap split (r79 only):** 70.5 near vs 47.3 /min free at 5–10, and 44.9 vs 7.0 at 0–5. This is confounded with fast turning. The setpoint-rate split goes the *other* way at 5–10 (87.3 slow against 44.2 fast). Weak.

**Note 4 re-ranked:**

| rank | mechanism | strength |
|---|---|---|
| 1 | The bar-threshold-keyed integrator freeze (300 opposing / 512 hard) acting on stick-slip | moderate |
| 2 | Small-correction stick-slip across the P dead zone (synthesis #2; not attacked) | moderate |
| 3 | The fork's O1 relay | weak (acts, but does not enrich) |
| 4 | Limiter re-slew | weak |
| ✗ | A ring | ruled out (agree) |

---

## 4. Note 3 (V8): survives

`selfdrive/ui/onroad/starpilot/torque_bar.py` `TorqueBar._update_state` (fork Dom 2712e1336, read):
- In angle mode the bar is clip((a_act − roll·g·interp(v, [5, 15], [0, 1])) + (a_des − a_act), ±1) / CP.maxLateralAccel.
- **a_act cancels**, which leaves (a_des − roll term) / 0.32467.
- It is drawn whenever latActive, AOL included.
- Its first-order filter is 0.1 s.

**What else could the "torque/demand indicator" be?** The developer sidebar's "TORQUE %" reads `carControl.actuators.torque`. That is **0 on 100 % of latActive frames** in angle mode (cache `cc_tq`). But `developer_sidebar` = False in the drive's toggles, so it was not on screen (EVIDENCE: `sp_toggles_json`).

The bar is what the operator saw. The synthesis's #1 and #2 stand. **Strong.**

---

## 5. What I did not attack, and the exposure that would decide what is still open

**Not attacked:**
- the camera forwarding;
- Ki = 2.8 /s;
- the > 22 m/s tracking fragility;
- the R3\* reading;
- the small-correction stick (note 4 #2);
- note 1.

**Open:**
1. **Hand vs twist inside the 70 pressed O1 episodes is settled (hand, > 1200 counts, debounced).** The open question is whether the operator would have let go if the turn-in were stronger. That needs a *hands-off* large turn-in at ≤ 8 m/s, which never happened on r79: hands-off fast wind-up was **1.2 s** in total.
2. The freeze-as-stall-lengthener needs a replay counterfactual. Run M3's no-opposing-freeze replay variant on the near-crossing stall windows and ask whether the I would have broken the stall earlier.
3. D magnitude below the LIVE floor in 14 of 20 cells: is this regression attenuation, or real?

---

## 6. Out of scope, noticed

- `_scratch/out/r79/refute/` already held `refute_synth_data.*` and `err.txt` from another agent. I did not touch them.
- The judge's G section used the unfiltered bar. The 0.1 s UI filter cannot change a 59.7 % pinned share materially (BELIEF).
- In hands-off unwinds, the lane braking against a setpoint that is ahead of the wheel (§2c) is the same D-on-measurement property that would act as a velocity-error source in *any* hands-off turn-in. Its size there is unmeasured (1.2 s of exposure).
