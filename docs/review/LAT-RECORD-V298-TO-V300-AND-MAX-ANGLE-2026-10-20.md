# LAT RECORD — what changed V298 → V299 → V300 rev 2 (firmware + fork), the low-speed hands-on grinding, and what bounds the max steering angle (2026-10-20)

Study artifact; nothing built, flashed or sent. Subagent of orchestrator `main`.
**E** = EVIDENCE (method given) · **B** = BELIEF. Scripts (each < 1 s): `analysis-2020accord/studies/release/lat_record_2026_10_20/`
(`diff3.py` image diff, `ceiling.py` integer ceiling mirror, `holdload.py` measured hold load, `hfhands.py` hands-on band energy; `*.out.txt` = their output).

Operator's questions:
- **Q1** "what changed since V298? I think there are some rare instances of grinding at low speed, while manually turning the wheel while LKAS is engaged."
- **Q2** "Kp, Ki, Kd or max integral … goal: increase the max turning angle WITHOUT affecting LKAS performance and the current lack of grinding."

## 0. First fact for the route analyst

**No V300 (`39990-TVA,A16C`) route exists in the record** (E: grep of `docs/` for a V300 flight; STATE and the 2026-10-15 handoff say BUILT NOT FLOWN; the 2026-10-18 notes measured V299 routes 9c/9d).
The 2026-10-18 device read found the V300 rwd staged in `/data/eps-flash/` and CarParams empty.
**So the grinding was felt either on V299 (A16B, routes 9c/9d or later) or on a V300 drive the kit has not seen.** The candidate set differs completely between the two (§2). Read `carFw` on the grinding route first.

## 1. The cumulative delta, read from the images

Images: V298 `177abf04…`, V299 `30ff05fa…`, V300 rev 2 `7d58c823…` (sha256 re-hashed this pass). Diff over `[0x13000, 0x100000)`:

| step | bytes | runs |
|---|---|---|
| V298 → V299 | 67 | 4 |
| V299 → V300 | 2110 | 322 |
| V298 → V300 | 2172 | 324 |

E: `diff3.py`, raw LE byte compare. Every run below matches the build docstrings (`build_v299_tva.py`, `build_v300_tva.py`) and the release census.

### Table 1 — every change, firmware and fork, with its relevance to Q1

| # | step | where | change (read from bytes / code) | what it physically does | Q1 relevance (hands-on, engaged, low speed) |
|---|---|---|---|---|---|
| F1 | V298→V299 | cave `0xC4C64` | hard-freeze imm16 512 → **1229** (`00 02`→`cd 04`) | the integrator stops updating only above Honda's hands-on level (1200 on the wire) | **raises the fight**: a 550–1229-count hand no longer freezes I (E bytes; size from the V299 design §3.5, B) |
| F2 | V298→V299 | cave `0xC4C6A–0xC4CAB` (60 B) | the "opposing > 300" freeze clause removed | an opposing light hand no longer freezes I | same direction as F1 (E bytes) |
| F3 | V298→V299 | same span | A3 bound made asymmetric: toward centre = 1250 S flat | under an outward hand the I unwinds to −1250 S → the outward release lurch | release swing, not a tone (E bytes; B size) |
| F4 | V298→V299 | same span | two-level cap: **4096 S ≤ 6 m/s (= V298)**, 6144 S at 6–12.5 m/s (was ICL 8192), uncapped `shl 6` above | caps the steady integral at 26.7 % / 40 % of the rail | **≤ 6 m/s byte-identical to V298's rule** (E: cave decode, `v ≤ 1382` path) → cannot explain a low-speed change |
| F5 | V298→V299 | `0x1310D`, `0xC4FFC` | F181 A16A→A16B, CRC | id only | none |
| — | all three | `0xE54FC` fadeB2, `0xE55A4` fadeA2, Kp/Kd slot 7, Ki/a/b, ICL, gain 5346, clamps 3072, DCL 10240, lockout 0, DampAxis rows + α2 | **byte-identical V298 = V299 = V300** | the hand fade, the PID gains, the authority chain | **not a change since V298** (E: `diff3.py` cell check) |
| R1 | V299→V300 | `0xC649B` + `0x35A08/12/18` | **biquad arm** 1 → 0, arm source back to Honda's | disarms Honda's **55.23 Hz notch** (|H| < 1 on 36.8–82.2 Hz) on the base-assist **torque-sensor** lane, which V103→V299 ran **engaged-only** | **acts only engaged + hands-on** — see §2.2 |
| R2 | V299→V300 | `0x3AA96` `fb`→`c5`, `0xC6446` 2048 → 512 | **r24 gate/arm** back to Honda | the driver-torque-DERIVATIVE lane (`0.5·(T[n]−T[n−4])`) runs Honda's speed LERP engaged: gain **2.00 → 3.00 at creep** (2.50 at 10 km/h) | **acts only while the driver changes torque** — see §2.2 |
| R3 | V299→V300 | pages `0xCE000–0xD9FFF` (979 B) | damper banks (rate/boost/friction families) back to Honda's, DampAxis 13 B kept | less base-assist damping above ~85 deg/s wheel rate | manual turning at creep exceeds 85 deg/s; B, low |
| R4 | V299→V300 | `0xC40BC`, `0xC40D2` | Coulomb relay knee/K1 → stock | observer-side only, writes no command | none (E, GATE 2 re-score §1) |
| R5 | V299→V300 | `0xC64DE` 27 → 17 | square-wave hold count on `gp-0x6b2c` | lens: inert on the lane (addend 0) | none (E per the side-channel lens) |
| R6 | V299→V300 | 27 Kp / 27 Kd records (`0xE4–0xE8` pages) | 960 → 112, 0 → 48 | slots the selector never indexes (measured 7, max 9) | none (E: selector measured on the wire) |
| R7 | V299→V300 | ×6 map (28 records), LIM 16384 → 15360 | rate-setpoint map + ceiling | bypassed by E4 in the angle images | none (E: two lenses) |
| R8 | V299→V300 | `0x55C0E`, `0xC4B34` cave, `0x55DF2–0x55E11`, `0x454FE`, `0x14120` | all telemetry, an inert selector byte, the dead id copy | no physical effect | none; **cost: release routes have no lane tap** |
| R9 | V299→V300 | `0x1310D` + 8 CRC trailers | F181 A16C | id only | none |
| K1 | fork: V298 `2712e1336` → Dom `c6452361` (V299 flights) | `carcontroller.py` | **fork override O1 (600) deleted** (ruling 2026-10-02); limiter seeds from the wheel on the first frame; the clip re-seeds the limiter; 0x1AB bar; MaxRate flown **250** (V298 flew 120) | a hand below 1229 is no longer yielded to by the fork: the setpoint stays up to the clip away, opposite the hand | **the largest hands-on change since V298** (E code, handoff §4) |
| K2 | fork: Dom → `accord-PTM` `45a1a529c2`/`83fa2e68c8` (pushed) | `opendbc/car/honda/{values,carcontroller}.py`, `controlsd` | fw-id detection; `apply_steer_angle_limits_vm` on its own output, then the clip as a **pure bound** `clip(apply, θ_meas ± ANGLE_ERROR_MAX(v))`; 250 deg/s fixed; SR 16.84 + variable-ratio map; **turn-initiation lead OFF** under angle control; no AccordAngle* params; bar = lat-accel / `CP.maxLateralAccel` 0.3247 | under a hand the SENT setpoint = measured wheel ± clip every frame | the clip-ridden setpoint feeds the wheel back through the round trip (§2.1 C3) |
| K3 | fork: local `9b7ef55826` + `311c4cc0b7` (**NOT pushed**) | `latcontrol_angle.py`, `honda/interface.py` | saturation flag from the carcontroller limiter; `maxLateralAccel = 3.589` for the bar | the "Turn Exceeds Steering Limit" alert and the bar only | none on torque |

## 2. Q1 — candidate mechanisms, ranked

### 2.1 If the grinding route is V299 (A16B)

| rank | mechanism | changed since V298? | E/B |
|---|---|---|---|
| C1 | **The no-override hand fight (K1 + F1/F2).** With O1 gone and I integrating up to 1229 counts, a driver turning the wheel with LKAS engaged meets P at the clip plus a winding I. The V299 design sized it: **66–82 % of the rail opposing a 550–1150-count drag at 5–8 m/s, hand force ×2–3.6 V298's, F7b runs 0.55–1.56 s.** A loaded column with Coulomb friction 73–156 T then stick-slips; 9c/9d already measured dwells 6.8–15 /min at 0–5 m/s vs V282 0.4–0.6. | yes | E for the bytes, the code and the dwell counts; **B** that this is what the operator calls grinding |
| C2 | **The clip-ridden setpoint (K1/K2).** Under a hand the sent setpoint is `θ_meas(t−τ) ± clip`, so E′ ∝ `±clip + θ(t−τ) − θ(t)`. That cancels P's static stiffness and adds a delayed-position term that is damping at low frequency but **anti-damping for ωτ ∈ (π, 2π)** — 8–25 Hz for a τ of 40–60 ms, largest at low speed where G(v) is ×4.6. V298's O1 also rode the wheel, but with zero offset and only above 600 counts. | partly | E for the code path (`carcontroller._update_angle`); **B** for τ and the band |
| C3 | **D on the fresh motor rate (OPH, since V298).** The term most active while the driver turns the wheel: `D = 6·op`, ≈ 5 T per deg/s before the fade (B on the op scale), never scored hands-on. On r79 (V298) engaged hands-on 15–25 Hz torque-sensor energy was already **1.2–2.6×** disengaged hands-on below 6 m/s. | **no** | E weak (`hfhands.py`, n = 12/41 windows); V299 windows too few (n = 2–10) to compare |
| — | F3/F4 (asymmetric bound, caps) | yes | act only through I (Ki ≈ 2.8 /s); FRZ only stops I updating, it never steps torque — **cannot make a tone** (E, cave decode §2.2 of the codepath doc) |

### 2.2 If the grinding route is V300 (A16C) — add these, ranked above C1–C3

| rank | mechanism | E/B |
|---|---|---|
| V1 | **The 55.23 Hz notch disarmed (R1).** The record's **grind #2** is "a ~44.6 Hz mode (Q ≈ 37) under heavy DRIVER steering load at creep, \|angle\| 150–265°, also at 10–20 mph on semi-hard turns". On the 100 Hz grid 44.6 Hz is indistinguishable from **55.4 Hz**, and the notch's stop band (36.8–82.2 Hz) covers both. Every build V103→V299 ran it **engaged-only**, and V108 kept the arm on purpose ("unarmed is a BYPASS"). The census reverted it on BELIEF, judged against the angle loop's 0.4–0.6 Hz crossover, which says nothing about a base-assist-lane mode. **Exactly the reported condition: engaged, hands-on, low speed.** | E for the bytes, the band and the history (BUILD-LINEAGE V103/V104/V108, RULE 9, `accord-grind2-is-a-45hz-mode-under-driver-load`); **B** for causation (grind #2's origin is OPEN in the record) |
| V2 | **r24 back to Honda's LERP while engaged (R2).** Its input is the driver-torque derivative, so it acts only while the driver changes torque. V300 raises its creep gain ×1.5 (2.0 → 3.0). The record: r24 **pumps at 7 Hz**, and the higher creep r24 cost ~3× at 6–9 Hz (Lever B's removal win was at creep). The GATE 2 re-score that cleared the revert used a **hands-off** torsion-bar transfer only. | E for bytes and the lane equation; **B** for the symptom |
| V3 | Damper banks (R3): less base-assist damping above 85 deg/s. | B, low |
| — | R4–R9 | inert (E, lenses + selector measurement) |

### 2.3 What to read on the wire (release routes have NO tap)

- **Attribution:** `carFw` EPS = `39990-TVA,A16B` vs `A16C`; 0xE4 byte 2 bits 3:2 = 2.
- **Episode gate:** 0xE4 `STEER_REQUEST` = 1 and 0x18F `STEER_CONTROL_ACTIVE`; `vEgo` < 6 m/s; \|0x18F `STEER_TORQUE_SENSOR`\| > 600 wire (raw = wire / 1.024; 1200 wire = the 1229 freeze = `steeringPressed`); \|0x14A wheel rate\| > 30 deg/s. Control set: the same gate with LKAS disengaged.
- **C1 (fight):** sign of the driver torque vs sign of (0xE4 setpoint − 0x14A angle), where setpoint = −raw/10. The fight is on when they are opposite and \|setpoint − angle\| equals `ANGLE_ERROR_MAX(v)` within 0.1° (clip-bound). Then compare dwell/catch-up counts and 15–25 Hz torque-sensor energy, clip-bound vs not.
- **C2 (clip-ridden):** inside clip-bound frames, 8–25 Hz energy of the 0x14A rate and of the setpoint increments. The setpoint should carry the wheel's motion one round trip late.
- **V1 (notch):** 35–50 Hz energy of the 0x18F torque sensor (the alias band of grind #2) **engaged vs disengaged, hands-on, same speed and angle bins**. Prediction if V1 is the cause: on V299 engaged ≤ disengaged (the notch was on), on V300 engaged ≈ disengaged and above V299-engaged. The 100 Hz grid cannot tell 44.6 from 55.4 Hz; the comma **microphone** is the validated instrument for grind #2 (4.14× positive control).
- **V2 (r24):** 5–9 Hz energy of the 0x14A rate and the torque sensor in the same gate, V300 vs V299.

## 3. Q2 — what bounds the angle under LKAS

### 3.1 The arithmetic (integer, from the V300 image, mirroring the cave and Honda's PID)

Constants read LE from the V300 image (`ceiling.py`): Kp 112 ×5 · Ki 40 · ICL 8192 · PCL/SCL 15360 · gain 5346 · clamp 3072 · freeze 1229 · v-gates 1382/2880 · caps 4096/6144 · B 1250 · G(v) table at `0xC4CDA`.

```python
E   = 16 * err_tenths                          # 0xC4C00/02: 4·sp − 16θ, 160 per degree
Ep  = (E * G(v)) >> 8                          # 0xC4C54/58
P   = clamp((Ep * 112) >> 8, ±15360)           # 0x29E34–0x29E5C: 0.2734·G S per degree (322 S/deg at G 1178)
b   = min((θ_tenths << 4) + 1250, 4096 if v ≤ 1382 else 6144)   # 0xC4C86–0xC4CA0 (v ≤ 2880); (θ<<6)+1250 above
I   = min(b, 8192)                             # I>>7 ≤ ICL; the cap binds above |θ| = 17.8° (≤ 6 m/s) / 30.6°
S   = clamp(((I + P) * 254) >> 8, ±15360)      # hands-off fade 254/256
T   = min(3072, 5346 * 0.990 * S / 32768)      # lag DC 0.990; rail 2461 T at S = 15360
```

**Anchor (E):** with the measured standing error, the mirror reproduces the measured hold. At 4.5 m/s, 135°, error 8.7° it gives 1136 T against r9d's p50 1144 T. At error 6.6° it gives 1020 T against r9c's 976 T (`holdload.py`, quasi-static engaged holds, 3–6 m/s, 90–180°). **At 3–6 m/s the I sits at its 4096 cap and P carries the rest.**

**Load (B for the shape):** the V293 hold-map shape `k(v)·sat·tanh(θ/sat)`, scaled to that measured 1144 T, plus Coulomb friction 156 T at 0–5 m/s and 85 T above (r79 measured 156 / 73–94) for a wheel moving outward.

| v m/s | G | clip ° | P at clip (S) | I cap (S) | T max (T, % rail) | load at 270 / 430° (T, no friction) | **max angle, static / moving out** | fork VM limit ° (B) |
|---|---|---|---|---|---|---|---|---|
| 3 | 1178 | 17.0 | 5475 | 4096 | 1534 (62 %) | 1548 / 1768 | **264 / 212** | 400 |
| 4 | 1230 | 16.7 | 5616 | 4096 | 1556 (63 %) | 1450 / 1546 | lock / **238** | 400 |
| 5 | 1289 | 16.4 | 5780 | 4096 | 1583 (64 %) | 1471 / 1505 | lock / **220** | 372 |
| 6 | 1347 | 16.1 | 5929 | 4096 | 1606 (65 %) | 1395 / 1403 | lock / lock | 265 |
| 8 | 1464 | 15.5 | 6204 | 6144 | 1979 (80 %) | 1019 / 1019 | lock / lock | 152 |
| 10 | 761 | 19.5 | 4057 | 6144 | 1635 (66 %) | 982 / 982 | lock / lock | 98 |
| 12 | 581 | 16.6 | 2636 | 6144 | 1407 (57 %) | 886 / 886 | lock / lock | 68 |

**Readings:**
- **At 3–5 m/s the wheel moving outward stalls at 212–238°** with the error at the clip (E arithmetic, B load shape). This matches the 2026-10-18 note: the clip bound 25 % of frames above 250° on 9d, and only the hand-driven wheel reached 388–394° (E, route caches).
- **The 400° fork cap and the firmware ±409.6° clamp never bind** (E, 2026-10-18 measurement).
- **ICL 8192 does nothing at ≤ 12.5 m/s**: the caps 4096/6144 sit below it (E, cave decode). It binds only above 12.5 m/s at \|θ\| ≥ 10.8°.
- **Above ~6 m/s the firmware has 40–100 % headroom over the load.** There the angle ceiling is the fork's lateral-accel limiter `get_max_angle_vm` at `MAX_LATERAL_ACCEL` 3.589 m/s²: roughly 265° at 6 m/s, 150° at 8, 100° at 10, 70° at 12. These are kinematic numbers (SR 16.84, wheelbase 2.83 m, no understeer term), B ±30 %. The planner's own ISO 3.0 m/s² clamp bound only 2.6 % of frames on 9d (E).
- **The 1229 freeze and the A3 θ-referenced bound** never limit a hands-off hold: the bound exceeds the cap above 17.8° (E).

### 3.2 Table 2 — the levers

Columns (i)–(iv) as briefed. "Max angle" is the moving-outward column from `ceiling.py` at 3 / 4 / 5 m/s; lock ≈ 438° in the scan.

| lever | (i) max angle, 3/4/5 m/s (V300: 212/238/220) | (ii) risk to grind-free (18–22 Hz, 7 Hz) | (iii) release lurch / A3 | (iv) class | what the record already says |
|---|---|---|---|---|---|
| **ICL** 8192 → 10240 | **no change** at ≤ 12.5 m/s | none | none | cal | panel 2 raised 4096 → 8192 for the 15–22 m/s spring (850–1170 T); the caps re-bound it below 12.5 m/s |
| **Ki** | **no change** (time to reach the cap only) | phase at the PI corner | faster wind = more stored I | cal | refuter F1 cut Ki 56 → 40 for op-point instability (curve-hold ρ ≥ 1) |
| **Kd** | **no change** (static) | **highest**: direct HF damping on the fresh rate | — | cal (28 records) | D sized 0.55–0.88× design on r79; DCL history |
| **cap hi** 6144 → 7168 | **no change** ≤ 6 m/s; fixes 3–7° curve-hold shortfall at 8–10 m/s | low | **7168 trips F4 at 10 m/s** (5.6–6.6°) | cave immediate (2 B) | V299 §6.2: licensed for re-scoring only if drive data shows the I parked at 6144 with > 3° error |
| **cap lo** 4096 → 5120 | 266 / lock / lock | low (I is sub-Hz) | **≥ 5120 trips F4 at 3–4 m/s** (7.6° at 45°, 5.6° at 60°, sim); outward swing ∝ (I + 1250) | cave immediate `0xC4C96` (2 B + CRC) | V299 §1.2: "no single value satisfies both bands" |
| **cap lo** → 6144 | 360 / lock / lock | low | worse than 5120 (alt4 8.3° at 3 m/s) | cave immediate | rejected in V299 §1.2 |
| **Kp** 112 → 140 (all 28) | 290 / lock / lock | **moderate–high**: loop gain at every frequency | P returns the full error on release | cal | V299 panel: **Kp ×1.5 / ×2 rejected, PM −10° / −20°** |
| **G(v)** ×1.25 | = Kp row | same, but can be confined to ≤ 6 m/s | same | cave table immediates | the 11.75 m/s dip is "margin-limited on the identified plant" |
| **fork clip** ×1.15 | 254 / 388 / lock | none small-signal (the clip does not bind at small error) | release-instant gap ∝ clip (15.5–16.5° now) | fork constant | "cap 250 + clip ×1.6 together" rejected for re-arming the twist relay through the **old fork's O1 debounce**, which no longer exists (B that the reason lapsed) |
| **fork clip** ×1.3 | 314 / lock / lock | none small-signal; **raises the C1 hand fight ×1.3** | same, ×1.3 | fork constant | as above |
| fork MAX_LATERAL_ACCEL | none at ≤ 5 m/s; the ceiling at 6–12 m/s | none | none | fork constant | shared 3.589 m/s² with upstream; above the planner's ISO 3.0 |

### 3.3 Recommendation

- **Firmware: leave it untouched.** ICL, Ki, Kd and cap-hi do not move the low-speed angle at all (E). Cap-lo, Kp and G(v) do, but each carries a cost the record already measured: F4 overshoot at 3–4 m/s, or PM −10°. The release has no lane tap, so a firmware dose would also fly without the instrument for its own edit; only the achieved angle and the clip-bound error are visible. If a firmware lever is wanted anyway, the targeted one is **cap-lo 4096 → 5120** (2 bytes at `0xC4C96` + the main CRC, ≤ 6 m/s only), accepting the sim's 7.6° F4 overshoot at 45°/3 m/s.
- **Fork: raise the error clip at low speed and large angle only.** The form to design (B, needs the S2/RSN re-score): `ANGLE_ERROR_MAX ×1.3` below ~6 m/s when \|θ_sp\| > ~150° and the error points outward. At 3 m/s that reaches 314° moving outward, between cap-lo 5120 (266°) and 6144 (360°), with no flash, is reversible by a fork revert, and leaves small-angle tracking unchanged. The plain `×1.15` one-line edit of `ANGLE_ERROR_MAX_V` is the cheap version (4 m/s: 238 → 388°).
- **⚠ Q1 interplay.** If the grinding is C1 (the hand fight), any symmetric clip raise makes it worse. Decide Q1 from the wire first, then size the clip with the outward-only gate.

## 4. Open items and caveats

- The load shape beyond the measured 90–180° holds is the V293 hold map (B); quasi-static hands-off high-angle holds are rare in the caches (≤ 80 frames per bin).
- The VM angle limits above use a kinematic model; the real VehicleModel adds the understeer factor (B, +0–30 % at 12 m/s).
- The C2 delay band depends on the real round trip (fork frame 10 ms + CAN + the 100 Hz angle hold); the record has ~60 ms (B).
- D's scale (`op` counts per deg/s) is B (GATE 2 re-score caveat 2).
- `9b7ef55826` and `311c4cc0b7` are on local `accord-PTM` only; the device runs `83fa2e68c8` per the 2026-10-18 read.
