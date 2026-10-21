# DRIVE READ — accord-PTM routes ad…b4 (2026-10-18…20): the low-speed hands-on grinding, and what bounds the max angle

Study artifact; nothing built, flashed or sent. Subagent of orchestrator `main`.
**E** = EVIDENCE (method given) · **B** = BELIEF.
Scripts: `rlog-tools/studies/angle_loop/release_ad_b4/` — `read_ad_b4.py` (per route, 1.4–4.5 s cached), `report_ad_b4.py` (pooling, < 2 s).
Outputs: `out/read_ad_b4.json`, `out/report_ad_b4.txt` (every table below), `out/dr_*.txt|json` (the kit's `angle_loop_drive_read.py` on each route and on 9c/9d), `out/hunt.txt|json` (`high_angle_hunt.py`).
Compact caches: `analysis-2020accord/_scratch/cache/release_ad_b4/`.
Candidate mechanisms and gates are the ones named in `docs/review/LAT-RECORD-V298-TO-V300-AND-MAX-ANGLE-2026-10-20.md`.

## 0. The first fact

**All eight routes ran V300** (`39990-TVA,A16C`), so the V300 candidate set (V1, V2, V3 ranked above C1–C3) applies. These are the **first V300 flights in the record.** (E: `carParams.carFw` in each route's fork cache and in the extras pass.)

## 1. Attribution (E: carFw, initData GitCommit, carParams, the wire's 0xE4 request × 0x18F STEER_CONTROL_ACTIVE)

| route | EPS fw | fork commit | steerControlType | CP.maxLatAccel | route min | lateral engaged min | engaged min 0-3 / 3-6 / 6-10 / 10-15 / 15-22 / >22 m/s | hands-on (> 600 wire) engaged min < 6 / < 10 m/s |
|---|---|---|---|---|---|---|---|---|
| ad | A16C | 83fa2e68c8 | angle | 0.325 | 13.0 | 10.4 | 0.3 / 0.4 / 1.0 / 1.2 / 0.9 / 6.7 | 0.24 / 0.41 |
| ae | A16C | 83fa2e68c8 | angle | 0.325 | 15.0 | 10.0 | 0.2 / 0.8 / 1.6 / 0.7 / 0.4 / 6.5 | 0.39 / 0.63 |
| af | A16C | 311c4cc0b7 | angle | 3.589 | 19.0 | 11.1 | 1.7 / 1.3 / 1.6 / 1.4 / 1.4 / 3.6 | 0.36 / 0.42 |
| b0 | A16C | 311c4cc0b7 | angle | 3.589 | 26.4 | 17.3 | 1.2 / 2.6 / 3.4 / 4.5 / 3.9 / 1.7 | 0.74 / 1.20 |
| b1 | A16C | 311c4cc0b7 | angle | 3.589 | 13.1 | 5.5 | 0.2 / 0.2 / 0.2 / 3.4 / 1.5 / 0.0 | 0.09 / 0.11 |
| b2 | A16C | 311c4cc0b7 | angle | 3.589 | 9.1 | 5.7 | 0.4 / 0.7 / 1.6 / 1.1 / 0.6 / 1.1 | 0.48 / 1.08 |
| b3 | A16C | 311c4cc0b7 | angle | 3.589 | 14.9 | 9.9 | 0.5 / 0.9 / 1.3 / 2.0 / 1.3 / 3.8 | 0.19 / 0.28 |
| b4 | A16C | 311c4cc0b7 | angle | 3.589 | 13.8 | 9.6 | 0.2 / 0.4 / 1.1 / 2.5 / 4.2 / 1.3 | 0.14 / 0.33 |
| *9c (ref)* | A16B | Dom c6452361e4 | angle | 0.325 | 14.7 | 9.0 | 0.5 / 0.4 / 0.8 / 1.1 / 2.1 / 4.0 | 0.20 / 0.32 |
| *9d (ref)* | A16B | Dom c6452361e4 | angle | 0.325 | 13.6 | 9.4 | 0.9 / 0.7 / 0.7 / 2.9 / 2.2 / 2.1 | 0.16 / 0.31 |
| *79 (ref)* | A16A | Dom 2712e13369 | angle | 0.325 | 20.4 | 11.2 | 1.0 / 1.4 / 1.9 / 1.9 / 3.4 / 1.5 | 1.01 / 1.33 |

- `311c4cc0b7` is on af…b4: **the two local fork commits did fly**, so the 2026-10-18 note's "device runs 83fa2e68c8" is out of date from route af onward (E: initData GitCommit; CP.maxLateralAccel 3.589 confirms `311c4cc0b7` loaded).
- CP.steerRatio is **16.33** on every route; the `SteerRatio` param reads 16.84 (E). The carcontroller's VehicleModel uses CP, so the fork's limiter ran 16.33 (E: my limiter replay at 16.33 reproduces carOutput on 99.8–100 % of latActive rows, §4).
- Pooled V300 exposure below 6 m/s, hands-on and engaged: **2.6 min** (V299 refs 0.36 min, V298 1.0 min). Every low-speed hands-on comparison below rests on ~160 s of V300 data and only 22 s of V299 data. Treat the V299 rows as small-sample.
- The camera's bus-2 0xE4 requests on 7 of 8 routes, as on 9c/9d (E: drive reader). This is not new.

## 2. Grinding hunt

**Gate (lat-record §2.3):** lateral engaged (0xE4 STEER_REQUEST and 0x18F SCA, ≥ 95 % of a 1-s window), \|driver torque\| p50 > 600 wire, \|wheel rate\| p50 > 30 deg/s, speed < 6 and < 10 m/s. **Control:** the same gate disengaged (< 5 % engaged). Band rms is taken on the 4 Hz high-passed 0x18F torque sensor (bar, wire units) and on the 0x18F wheel rate (deg/s). The engaged/disengaged ratio of medians is computed per speed × rate bin (0-3 / 3-6 / 6-10 m/s × 30-60 / 60-120 / > 120 deg/s) and pooled as the engaged-count-weighted geometric mean. **Bar sign (E):** disengaged hands-on turning has bar·rate < 0 on 77–92 % of frames on every route, so the driver's push direction is −sign(bar).

### 2a. Band energy, engaged ÷ disengaged, hands-on, v < 6 m/s (v < 10 in brackets)

| band | V300 (n 92 / 346) | V299 9c+9d (n 13 / 99, matched 8 / 31) | V298 79 (n 45 / 64) | reading |
|---|---|---|---|---|
| bar 5–9 Hz (V2) | **1.36** (1.30) | 1.57 (1.79) | 1.72 (1.72) | V300 lowest of the three |
| rate 5–9 Hz (V2) | **1.08** (1.02) | 1.41 (1.48) | 1.54 (1.54) | V300 lowest |
| bar 15–25 Hz (C3) | **1.27** (1.25) | 1.64 (1.82) | 1.33 (1.33) | V300 ≈ V298, below V299 |
| rate 15–25 Hz (C3) | 0.91 (0.89) | 1.11 (1.08) | 1.17 (1.17) | no engaged excess |
| bar 35–50 Hz (V1) | **0.90** (0.88) | 0.91 (1.02) | 0.76 (0.76) | engaged ≤ disengaged on every build |
| rate 35–50 Hz (V1) | 0.76 (0.80) | 0.49 (0.47) | 0.73 (0.73) | engaged below disengaged |
| rate 8–25 Hz (C2) | **1.15** (1.05) | 1.69 (1.54) | 1.35 (1.35) | V300 lowest |

**At the record's grind #2 condition** (hands-on, < 10 m/s, \|angle\| > 150°), bar 35–50 Hz p50 reads engaged 8.8 vs disengaged 9.4 on V300 (n 62 / 217). V299 reads 8.8 vs 11.4 and V298 8.8 vs 7.9, at matched hand torque (\|bar\| p50 2644 vs 2613 on V300).

- **V1 (55 Hz notch disarmed) — NOT SUPPORTED on the 100 Hz grid** (E: the prediction was V300 engaged ≈ disengaged and above V299-engaged; V300-engaged equals V299-engaged at 8.8 and sits below its own control). **B caveat:** 44.6/55.4 Hz alias into 35–50 Hz only as folded energy, so a narrow line could hide under broadband hand noise. The comma microphone is the validated grind #2 instrument and was not read.
- **V2 (r24 ×1.5 at creep) — NOT SUPPORTED** (E: V300's 5–9 Hz engaged excess is the smallest of the three builds, on both the torque sensor and the wheel rate).
- **V3 (damper banks above 85 deg/s) — NOT SUPPORTED** (E: in the > 120 deg/s rate bin at 0–3 m/s, V300 bar 15–25 Hz reads 0.75 and bar 35–50 Hz 0.70 engaged/disengaged; 3–6 m/s reads 1.00 / 0.77).
- **C3 (D on the fresh motor rate) — present, not new** (E: the bar 15–25 Hz engaged excess is 1.27 on V300 against 1.33 on V298 and 1.64 on V299). It is concentrated at 3–6 m/s and below 120 deg/s, where V300 reads 1.73–1.85.

### 2b. Stutter readouts (the kit's own instruments, reused unchanged)

| route | 18–22 Hz ring presence | F7 /100 s | 18–22 Hz eng/dis | 13–17 Hz eng/dis | new 5–30 Hz line | dwells/min 0–5 m/s @0.25 (@0.50) | 1.6–3 Hz hard-turn rate rms 3–8 / 8–12 m/s |
|---|---|---|---|---|---|---|---|
| ad | 0.00 % | 0 | 0.77 | 1.37 | none | 0.0 (12.2), 29 s | 8.5 / 3.9 |
| ae | 0.00 % | 0 | 1.12 | 2.06 | none (bar 14.8 Hz +6.2 dB, not a new-line verdict) | 0.0 (3.5), 34 s | 6.5 / 4.6 |
| af | 0.00 % | 0 | 1.51 | 2.07 | none | 9.1 (29.2), 158 s | 9.1 / 6.1 |
| b0 | 0.07 % | 0 | 1.01 | 1.26 | none | 5.5 (21.7), 186 s | 12.8 / 4.7 |
| b1 | 0.00 % | 0 | 0.77 | 0.97 | none | 7.0 (24.5), 17 s | 7.1 / 3.6 |
| b2 | 0.00 % | 0 | 1.24 | 2.01 | none | 4.2 (10.6), 57 s | 9.6 / 2.7 |
| b3 | 0.00 % | 0 | 0.95 | 1.22 | none | 9.0 (27.8), 67 s | 5.6 / 2.9 |
| b4 | 0.38 % | 0 | 0.94 | 1.27 | none | 6.4 (14.9), 28 s | 7.9 / 3.1 |
| *9c V299* | 0.12 % | 0 | 0.99 | 1.64 | none | 15.0 (27.4), 44 s | 23.3 / 8.7 |
| *9d V299* | 0.13 % | 0 | 0.72 | 1.13 | none | 6.8 (28.8), 79 s | 11.2 / 9.0 |
| *79 V298* | — | — | — | — | — | 4.7 (12.3), 102 s | — |
| *V282 refs r6c / r39* | 2.63 / 1.65 % | 1.03 / 0 | 3.40 / 3.92 | — | — | 0.58 / 0.38 | 4.3–4.6 / 1.5–2.3 |

**Pooled dwells, 0–5 m/s, @0.25 deg/s (E, `v293_symptom_instruments.dwells` on every route):** V300 **6.2 /min** (576 s), V299 9.8 (123 s), V298 4.7 (102 s), V282 0.4–0.6. Every angle-loop build ratchets 10–20× V282 at creep. V300 sits between V298 and V299.

The grind-free status holds on V300 (E: ring presence ≤ 0.38 %, F7 0 on all eight routes, no new 5–30 Hz line, 18–22 Hz engaged/disengaged 0.77–1.51 against V282's 3.4–3.9).

### 2c. C1 — the hand fight (frames: engaged, \|bar\| > 600)

Opposing means the setpoint error θ_sp − θ points against the hand. At-clip means \|θ_sp − θ\| ≥ ANGLE_ERROR_MAX(v) − 0.15°. The P-only lane torque is the V300 integer P chain (`ceiling.py`'s mirror, constants read LE from the V300 image), **with no I and no hand fade, so it is an UPPER bound (B)**.

| v < 6 m/s | hands-on s | opposing | opposing AND at the clip | P-only torque when opposing, p50 (rail %) |
|---|---|---|---|---|
| V300 pooled | 158 | **78.8 %** | **33.6 %** (per route 12.5–48.1 %) | 422–929 T per route; 870–930 T (35–38 %) on 7 of 8 routes |
| V299 pooled | 22 | 75.8 % | 19.1 % (9c 3.8 %, 9d 38.0 %) | 155 / 888 T |
| V298 (O1 override) | 60 | 21.0 % | **0.0 %** | 182 T (7 %) |

At v < 10 m/s: V300 opposing 80.7 %, at the clip **28.2 %**; V299 81.1 % / 16.1 %; V298 27.9 % / 0.0 %.

**At matched hand torque the fight carries more torque-sensor HF** (E, V300 windows with \|bar\| p50 > 2000; at-clip n 30 vs not n 36):

| | at clip | not at clip |
|---|---|---|
| bar 15–25 Hz | 20.0 | 13.1 |
| bar 35–50 Hz | 12.9 | 7.9 |
| bar 5–9 Hz | 24.1 | 25.7 |
| wheel rate 8–25 Hz | 1.5 | 1.4 |

The extra energy is in the **torsion bar between the hand and the motor**, not in the wheel's motion.

### 2d. C2 — does the sent setpoint ride the wheel one round trip late?

The method is the cross-spectrum of θ_sp and θ over 0.5–5 Hz, in hands-on engaged runs below 10 m/s.

- **E:** the sent setpoint follows the wheel at **gain 0.76–1.08 and a delay of −4 to +11 ms** on V300 routes (coherence 0.18–0.67). That is at most about one 100 Hz frame, not the 40–60 ms the mechanism assumed.
- **E:** the planner's own desired angle (carControl, before the limiter and the clip) follows the wheel only weakly (coherence 0.01–0.15). The riding comes from the clip.
- **E with B reasoning:** with τ ≤ 12 ms the anti-damping band ωτ ∈ (π, 2π) sits at 42–83 Hz. That is above the 100 Hz command's useful band. The measured wheel-rate 8–25 Hz engaged excess on V300 (1.05–1.15) is the smallest of the three builds.
- **C2 as a resonant mechanism is NOT SUPPORTED.** As a static effect it is real: the clip cancels P's stiffness under a hand, which is half of C1.

### 2e. Ranking (what the wire supports)

1. **C1, the hand fight — SUPPORTED.**
   - E: a third of V300 hands-on creep time sits at the clip against the hand. The P demand there is ~35 % of rail (upper bound).
   - E: V298, with its O1 override, never sat there.
   - E: those windows carry 1.5–1.6× the 15–50 Hz torque-sensor content at equal hand torque. The top episode below is a textbook instance.
   - B: that this is what the operator calls "grinding".
2. **C3, D on the motor rate — present on every build since V298, not changed by V300.** It is concentrated at 3–6 m/s.
3. **C2 — static half of C1 only; the delayed-feedback version is refuted** (τ ≈ 1 frame).
4. **V1, V2, V3 — not supported on the 100 Hz grid** (E). V1 stays open for the microphone (B).

### 2f. Top 10 candidate grind episodes (V300; for the operator to match to what he felt)

Score is the window's band rms divided by the pooled V300 disengaged hands-on median in its speed × rate bin, maximised over bands. Across all 119 V300 engaged hands-on windows the score is p50 2.0 and p90 4.8. The disengaged control windows score p50 1.6 and p90 3.1. **t = seconds from route start, segment = t // 60.**

| # | route | t s (segment +s) | v m/s | angle ° | \|bar\| p50 | \|rate\| p50 °/s | top band (× control) | bar 5-9 / 15-25 / 35-50 | rate 5-9 / 15-25 / 35-50 | opposing at clip | peak bar / rate Hz |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | b0 | 690 (11 +30) | 6.3 | −12 | 2665 | 68 | rate 15–25 ×11.7 | 33 / 159 / 71 | 2.1 / **8.9** / 1.9 | 33 % | 29 / 24 |
| 2 | ae | 745 (12 +25) | 3.5 | −284 | 2125 | 41 | bar 5–9 ×8.9 | 216 / 11 / 7 | 4.0 / 0.6 / 0.3 | 0 % | 5 / 5 |
| 3 | b3 | 141 (2 +21) | 5.3 | +117 | 823 | 45 | bar 15–25 ×8.2 | 108 / 97 / 27 | 3.1 / 1.7 / 0.6 | 0 % | 9 / 6 |
| 4 | b2 | 375 (6 +15) | 6.2 | +77 | 1472 | 48 | bar 15–25 ×6.7 | 36 / 179 / 18 | 4.9 / 3.0 / 0.9 | 0 % | 15 / 5 |
| 5 | b2 | 381 (6 +21) | 2.3 | −60 | 638 | 73 | bar 5–9 ×6.5 | 132 / 25 / 7 | 4.1 / 0.8 / 0.2 | 0 % | 10 / 6 |
| 6 | b2 | 376 (6 +16) | 3.3 | +112 | 1849 | 32 | bar 15–25 ×6.1 | 16 / 72 / 12 | 0.7 / 1.7 / 0.3 | 57 % | 15 / 15 |
| 7 | b0 | 692 (11 +32) | 7.2 | +40 | 2232 | 82 | rate 8–25 ×5.5 | 56 / 98 / 17 | 4.9 / 4.1 / 1.4 | 0 % | 13 / 5 |
| 8 | b3 | 737 (12 +17) | 6.4 | −39 | 1124 | 66 | bar 5–9 ×5.3 | 159 / 38 / 11 | 4.2 / 0.8 / 0.4 | 8 % | 9 / 5 |
| 9 | b0 | 361 (6 +1) | 4.3 | −23 | 2371 | 58 | bar 15–25 ×5.1 | 25 / 60 / 28 | 2.1 / 3.0 / 1.5 | 72 % | 17 / 6 |
| 10 | b4 | 791 (13 +11) | 2.2 | −359 | 921 | 122 | bar 15–25 ×5.0 | 87 / 96 / 21 | 4.3 / 1.3 / 0.6 | 17 % | 12 / 7 |

**Episode 1, read frame by frame (E):** the driver yanks the wheel from −52° to +73° in about 2 s at 6.3 m/s with \|bar\| 2000–2900. The setpoint sits **−17° behind at the clip** for the whole swing (690.4–691.4 s). The wheel then reverses at −217 deg/s (692.4 s) against a +2690 bar. This is C1 in its plainest form.

Episodes 1, 7 and 9 are b0 around seg 6 and seg 11. Episodes 4–6 are one b2 manoeuvre at 375–381 s (seg 6).

## 3. Max angle

### 3a. Peaks per route (E: wire 0xE4 / 0x14A; fork carControl / carOutput)

| route | engaged setpoint peak ° | engaged wheel peak ° | wheel peak, any ° | planner desired peak ° | HANDS-OFF engaged wheel peak ° | \|θ\| > 150° engaged frames: clip / VM / rate-bound |
|---|---|---|---|---|---|---|
| ad | 270 | 275 | 392 | 270 | 64 | 26 % / 0 % / 16 % |
| ae | 317 | 305 | 389 | **388** | 304 | 48 % / 0 % / 28 % |
| af | 245 | 229 | 396 | 278 | 222 | 28 % / 0 % / 18 % |
| b0 | 373 | 390 | 393 | 332 | 188 | 82 % / 0 % / 42 % |
| b1 | 132 | 126 | 393 | 132 | 30 | — |
| b2 | 330 | 346 | 394 | 301 | 113 | 49 % / 0 % / 23 % |
| b3 | 186 | 176 | 394 | 203 | 170 | 48 % / 0 % / 12 % |
| b4 | 368 | 386 | 395 | 270 | 133 | 72 % / 0 % / 36 % |

- **The engaged high-angle turns on these routes were driven with hands on** (E: `high_angle_hunt.py` puts 0–28 % of each \|θ\| ≥ 60° engaged episode hands-off. Hands-off engaged time at \|θ\| > 150° is 0.0–1.5 s per route).
- The 386–390° engaged peaks on b0/b4 are hand-assisted: the wheel led the planner's desired (332 / 270°).
- The **400° cap never bound** (E: sent peak 373°).
- The **VM lateral-accel limit never bound at \|θ\| > 150°** on any route (E: limiter replay, §4).

### 3b. Which bound holds the wheel short of the planner, by speed band

The set is frames where the planner's \|desired\| > 30° and desired − wheel > 2° outward. Bounds come from the limiter replay. "None" means the setpoint went out at the desired value and the wheel still lagged, which is the firmware loop plus the hand. Pooled V300:

| band | short s | VM limit | error clip | rate cap | none (firmware / plant / hand) | shortfall p50, route medians ° |
|---|---|---|---|---|---|---|
| 0–3 m/s | 20.0 | 0 % | 47 % | 6 % | 47 % | 5–52 |
| 3–6 m/s | 56.5 | **0 %** | **60 %** | 4 % | 36 % | 11–36 |
| 6–10 m/s | 83.1 | **0 %** | 44 % | 4 % | 53 % | 8–21 |
| 10–15 m/s | 52.7 | 21 % | 15 % | 6 % | 58 % | 4–10 |
| 15–22 m/s | 2.4 | 25 % | 35 % | 9 % | 31 % | 9 |

Clip duty on all latActive frames at \|θ\| > 150° is 55 % (0–3 m/s), 50 % (3–6) and 43 % (6–10). Over all angles it is 12.8 / 16.8 / 6.6 / 1.1 / 0.3 / 0.2 %. VM duty is 0.0 % below 10 m/s and 1.6 % at 10–15.

**The lat-record's claim "clip-bound below 6 m/s, VM-limit above":**
- **CONFIRMED below 6 m/s** (clip 47–60 % of short frames, VM 0 %).
- **REFUTED for 6–10 m/s** (VM 0 %; the clip 44 % and the loop/hand 53 % hold it).
- **Only partly true above 10 m/s** (VM 21–25 %, with the loop's own lag the largest share).
- **B:** the planner rarely asks for more than the VM limit because its own ISO 3.0 m/s² clamp sits below the fork's 3.589.
- **Caveat (E):** almost all of these frames are hands-on. The hands-off, quasi-static subset (\|d desired/dt\| < 10 °/s for 0.5 s) totals **1.2 s** on V300. So the hands-off ceiling is **NOT TESTABLE on these routes**, and the lat-record's ceiling table (212–238° moving outward at 3–5 m/s) stays BELIEF.
- **The firmware integral cap is not observable** on release firmware (no tap). The "none" class (36–53 % below 10 m/s) is where the cap and P would act (B, per the lat-record arithmetic).
- **New (E):** at \|θ\| > 150° the **250 deg/s rate cap binds 12–42 %** of engaged frames. That is a third limiter at high angle, not in the lat-record's list.

### 3c. "Turn Exceeds Steering Limit" duty, old rule vs the 311c4cc0b7 rule

Method: a replay of `LatControl._check_saturation` (v > 5 m/s, not pressed, steerLimitTimer 0.8 s) on the controlsState rows.

| route (fork) | logged | OLD rule replay (agreement with logged) | NEW rule `9b7ef55826` replay (agreement) |
|---|---|---|---|
| ad (83fa2e68c8) | 1.0 %, 13 eps | 1.0 %, 13 eps (100 %) | 0.1 %, 1 ep |
| ae (83fa2e68c8) | 1.1 %, 18 eps | 1.1 %, 18 eps (100 %) | 0.0 %, 1 ep |
| af (311c4cc0b7) | 0.0 %, 0 eps | 1.3 %, 17 eps | 0.0 %, 0 eps (100 %) |
| b0 | 0.2 %, 2 eps | 1.7 %, 37 eps | 0.2 %, 4 eps (99.6 %) |
| b1 | 0.0 % | 0.9 %, 10 eps | 0.0 % (100 %) |
| b2 | 0.0 % | 2.6 %, 24 eps | 0.2 %, 6 eps (99.8 %) |
| b3 | 0.2 %, 1 ep | 2.5 %, 34 eps | 0.0 %, 2 eps (99.8 %) |
| b4 | 0.6 %, 3 eps | 2.8 %, 39 eps | 0.0 %, 0 eps (99.4 %) |

- **The new rule cut the alert ~10× on the routes it flew** (E: 0.9–2.8 % → 0.0–0.6 %).
- The alert text "take control | turn exceeds limit" still fired on b0 and b4 (E: selfdriveState alerts).
- The residual logged episodes my replay does not reproduce are BELIEF: `curvature_limited` (planner clamp), which is not logged here.

## 4. Other findings vs 9c/9d

- **The limiter replay is exact enough to trust (E).** It reproduces carOutput on **99.8–100 %** of latActive rows on ad…b4 and 9c/9d. On 79 it reaches only 79 %, because V298's fork had O1 and re-seeding. V298's bound split is therefore not reliable.
- **Hunting at high angle is lower than V299 (E, drive reader's 1.6–3 Hz hard-turn rate rms).**
  - 3–8 m/s: 5.6–12.8 deg/s on V300 vs 11.2–23.3 on 9c/9d.
  - 8–12 m/s: 2.7–6.1 vs 8.7–9.0.
  - Still 1.2–3× V282's 4.3–4.6 / 1.5–2.3.
  - Below 3 m/s V300 reads 14–18 deg/s on ae/b2/b4; 9c/9d have no exposure there.
  - BELIEF: the drop is the turn-initiation lead gated off (`45a1a529c2`). Episodes are mostly hands-on, so the hunt's fork/firmware decision is rarely reached.
- **Tracking, scored bands only (≥ 60 s):**
  - b0 8–15 m/s 1.04 (pass); b3 8–15 1.00 (pass), 15–22 0.85 (FAIL); b1 8–15 **0.63 (FAIL, 133 s)**.
  - \>22 m/s 0.97–1.00 everywhere.
  - b1's 8–15 m/s run is near-straight (no turn-holds), so its slope is on a small signal (B).
  - 9d 8–15 read 0.57 the same way.
- **No new 5–30 Hz line** on any route (E). ae shows a 14.8 Hz bar line at +6.2 dB that fails the new-line test. V292 showed a 14.8 Hz line too.
- The 13–17 Hz engaged/disengaged ratio reads 2.0–2.1 on ae/af/b2 vs 1.1–1.6 on 9c/9d (E). That is under the drive card's 3.5 bar.

## 5. What this means for the operator's two asks

- **Grinding (Q1).** The wire supports C1. Since V299 the fork no longer yields to a hand (O1 deleted), so a hand turning the wheel at creep meets the setpoint parked at the error clip on the other side for about a third of the time. That costs up to ~35 % of rail of P (upper bound), plus a winding I below 1229 counts. The torsion bar carries 1.5× the 15–50 Hz content there. V300's firmware reverts (notch, r24, dampers) show no hands-on HF increase on the 100 Hz grid. **B:** the fix is fork-side, a hand-yield below 1229 counts, rather than firmware.
- **Max angle (Q2).** Below 6 m/s the error clip holds the wheel short in 60 % of short frames; at 6–10 m/s it is the clip or the loop; VM binds only above 10 m/s; the 250 deg/s rate cap also binds at high angle. **The lat-record's warning stands (E now):** a symmetric clip raise also raises the C1 fight, which this read ranks first for the grinding. An outward-only, low-speed, high-angle clip gate is the form consistent with both findings (B).

## 6. Limits

- All V300 low-speed comparisons rest on 2.6 min of hands-on engaged creep (n 92 one-second windows below 6 m/s); V299's on 22 s.
- The 100 Hz grid folds 44.6/55 Hz; V1 needs the microphone.
- The P-only opposing torque ignores the hand fade (fadeA2/fadeB2) and the I, so it is an upper bound on P alone.
- Hands-off high-angle exposure on these routes is ≈ 0, so the hands-off angle ceiling is untested.
- Episode times are seconds from the first 0x18F frame of the route; the segment index is t // 60.
