# ARC GROUNDING — what the V38 → V292 record already says about TORQUE MODE, ACCELERATION TRACKING and a STARPILOT RATE TARGET

**Agent `arc`, 2026-09-13, for orchestrator `main`. Analysis only — nothing built, flashed, or sent on any
bus. No subagents spawned.**

**Why this file exists.** The session goal is a new firmware (plus StarPilot changes if needed) that keeps
**V282's authority (×6 torque, ×6 rate setpoint, no EME faults)**, has **no grinding**, has **no
stutter/oscillation**, and **changes the tracked quantity** — either the LKAS PID tracks angular
acceleration (≈ torque, what openpilot expects) or StarPilot models the rate servo and outputs a target
angular velocity. The kit's standing rule (`firmware-iteration` skill, *"Ground the session in the WHOLE
chain and the WHOLE recent record"*) is that no lever is proposed before it is grounded in the whole
post-V38 arc. **This is that grounding. It is not a design and it recommends no build.**

**Method.** Everything below was read at source this session: `docs/STATE.md`; `docs/BUILD-LINEAGE.md`
(entries V276 → V292, RULES, the closed-lever tables); `docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md` (by
address); every `docs/handoffs/2026-09/` file; `docs/review/V282-CUMULATIVE-NONSTOCK-DELTA-2026-09-09.md`;
`docs/research/{GRINDING,7HZ-STRONG-TURN}-DEEP-ANALYSIS-2026-09-03.md`;
`docs/specs/design/DESIGN-V291-FBLP-2026-09-13.md` + Addenda A–D; `rlog-tools/studies/grind/` and
`rlog-tools/studies/osc-highangle/` study docs; the repo and harness memory stores. **EVIDENCE** = read
from a named document or computed from image-derived constants stated here; **BELIEF** = inference.
Citations are by **file + heading or grep string**, never by line number.

---

## 🔗 RECONCILIATION — read this with `FORK-LATERAL-DESIGN-FOR-TORQUE-MODE-AND-RATE-TARGET-2026-09-13.md`

**Added at the 2026-09-13 close-out. Neither document's body was edited; this note records where the two
agents landed differently and how the session resolved it.**

This file and `docs/research/FORK-LATERAL-DESIGN-FOR-TORQUE-MODE-AND-RATE-TARGET-2026-09-13.md` (agent
`fork`) were written independently, on the firmware side and the openpilot side of the same goal. **They
do not contradict each other on any fact. They differ on which of the operator's two readings to build
first.**

| | position |
|---|---|
| **The fork memo** | **Design B first** — have StarPilot output a **rate target**. Its case: `AccordRatePlantFF` is **already a measured inverse of the LKAS assist map** (the map's open-loop scale is 141.4 deg/s per unit torque; the fork's identified `G(v)` is 0.85× that at 5 m/s and 0.49× at 28.5 m/s, exactly what a closed rate servo with finite loop gain should give). ⇒ **Design B is not a new idea in this fork; it is the completion of one that is already ~80 % built**, and it costs no firmware risk |
| **This file / the session** | **Torque mode first.** Two reasons, neither of which disputes the memo's case. **(1) Design B cannot remove the grinding** — V288 rev 2 flew exactly that class (a reference-side setpoint pre-filter): the cave was live, the D-bind duty fell ×0.03 as designed, **and the grinding was unchanged** (19.99 vs 19.93 Hz, KS p 0.18). Nothing on the fork's reference side reaches the 20 Hz ring. **(2) The operator's goal names torque** as what openpilot expects, and torque mode is the **model-independent test** of the in-loop class that V292's flight left open |

**Where the session's dispositions are recorded, and they are not re-litigable afterwards:**
`docs/review/ADVERSARIAL-V293-PREREG-2026-09-13.md` §*"Dispositions decided before the pass"* — in
particular that *"×6 rate setpoint"* has no meaning under torque mode (this file's §7.3 reaches the same
conclusion independently), that the 5–9 Hz rise is **gated** rather than merely reported, and that the
**outer loop is gated (B6)** because V276 is the nearest flown relative.

**The third reading, acceleration tracking, is DOMINATED and was recorded rather than built:** it
**contains** torque mode and adds electronic inertia on top, and the inertia term **needs a code cave** —
this kit's only bricking class. Reasoning: `docs/traces/TRACE-2026-09-13-lkas-pid-tracked-quantity.md` §4.

**What the fork side is:** a Galaxy **toggle config**, `analysis-2020accord/reference/toggle-config_V293_torque_mode.json`
(rate-plant FF off, Kp 0.3, Ki 0.15, friction 0.00, LAF 6.0) — and **no fork code**. It shipped first as a
param (`AccordEpsTorqueMode`), then as Testing Ground 9, and the operator rejected both the same day
(*"way too complicated for what should just be a toggle config file"*), so the fork commit was undone.
Card: `docs/guides/TORQUE-MODE-TOGGLE-CHECKLIST-2026-09-13.md`.

---

# 0. THE FOUR THINGS TO READ FIRST, IF NOTHING ELSE

1. 🛑 **TORQUE MODE HAS BEEN BUILT EXACTLY ONCE AND WAS NEVER FLOWN.** V279 rev 2 set the feedback
   saturation clamp `0xC62E6` to **0**, which forces the rate PID's feedback operand to zero on every
   path so `E = 32·setpoint`, with `Kd = 0` and a linear map. That IS "LKAS lane fb ≡ 0, T = f(cmd)".
   It passed five independent attackers and was never flashed. **The class is NEVER-TRIED, not
   falsified.** [EVIDENCE — `BUILD-LINEAGE.md` §*"V279 — PURE FEEDFORWARD"*, header reads
   *"2026-09-02, NOT FLOWN"*; `HANDOFF-2026-09-02-v279-pure-feedforward.md`]
2. 🛑 **THE NEAREST FLOWN PRECEDENT IS V276, AND IT DROVE BADLY.** V276 did not zero the feedback; it
   raised the feedback clamp ×6 so the error could **never change sign**, which made the P/D controller a
   `sign(error)` relay. On-car: *"a large, slower (2–4 Hz) oscillation when LKAS engaged … at all tested
   speeds … excites itself … Only way to stop it is to hold the steering wheel very firmly."*
   [EVIDENCE — `HANDOFF-2026-09-01-the-loop-that-stopped-damping.md`, operator verbatim]
3. 🛑 **"×6 rate setpoint" AND "TORQUE MODE" ARE NOT SIMULTANEOUSLY SATISFIABLE AS WRITTEN.** The ×6 rate
   setpoint is the assist map's ×6 top, and a *setpoint* only means something because a loop tracks it.
   With the feedback at zero the map stops being a reference and becomes a torque map. §7.3 states what
   survives and what does not.
4. 🛑 **V56's "lane mute" IS NOT EVIDENCE ABOUT THE LKAS FEEDBACK.** It muted `gp-0x6ad4`, which the
   2026-09-13 instruction-level trace established is a **driver-torque tracking PID**, not the LKAS
   output (`gp-0x6b4c` carries LKAS). It was also band-scoped, scored 15–26 Hz only.
   [EVIDENCE — `memory/accord/firmware/accord-gp6b4c-carries-the-lkas-lane-gp6ad4-is-a-driver-torque-pid-and-0x2a30e-0x2b421-is-a-dead-twin-island.md`;
   `docs/review/AUDIT-2026-08-12-dead-levers-and-liveness.md` row **I3**]

---

# 1. THE V282 RECIPE, CELL BY CELL, WITH ITS ON-CAR RESULT

Source of record: **`docs/review/V282-CUMULATIVE-NONSTOCK-DELTA-2026-09-09.md`** — every value there was
re-read by raw little-endian Python from the stock dump and the V282 plain image, with no build script
consulted, and an attribution census that aborts on any unattributed byte (1,984 differing bytes in 311
runs, **zero orphans**). Reproduced here with the on-car result and introducing build for each cell.

## 1.1 The authority chain (the "×6" the operator's requirement names)

| cell | stock | **V282** | what it physically is | on-car result | introduced |
|---|---|---|---|---|---|
| `0x2A1F0` (disp) | `0x746C` | `0x7CD0` | repoints the forward LKAS gain load off the **shared** cal `0xC646C` onto the **private** `0xC6CD0` | structural — it is what makes the gain cell reachable at all | V57; lost in the V38 rebase, restored V81 |
| `0xC6CD0` | `0xFFFF` (blank) | **5346** | private forward LKAS gain, Q15 (`×5346>>15` = ×0.16315) vs stock's `0xC646C` = 891 → ×0.02719 | **MEASURED**, dose-response across V101 (8×) / V102 (6×) / V112; 5346 unbroken since V260 | V57 cell, **5346 chosen at V102** — the first *downward* step |
| `0xC61B2`, `0xC61B4` | 512, 512 | **3072, 3072** | forward-path ± tracking clamps, pre- and post-gain | MEASURED; track the gain exactly (`5346×512//891 = 3072`) so the clamp never binds before the gain does | V102, unbroken since V260 |
| `0xC674E/50/5A/5C` | 1024,1024,−1024,−1024 | **±5120** | the **EME soft-limit quad** (direction corridor), int16 | CARRIED, structural, unbroken 247 builds. `0xC674E` must stay **above** the tracking clamp 3072 or the build aborts | V25 → V30 → V38 |
| `0xC6768/6A/6C` | 0, 1536, 2048 | **5120 ×3** | the EME **boost** ramp triple | CARRIED, structural. V31's boost floor is what stopped the hands-off soft EME | V31 → V38 |
| `0xC6598…0xC65CC` (f32) | 1.0/1.0/−1.0/−1.0/0/1.5/2.0 | **±5.0** | **float mirrors** of the two rows above | CARRIED. 🛑 **int and float must move together or the lockstep monitor trips.** V178 reverted one and is `SUPERSEDED-DO-NOT-FLASH-AUTHORITY` | V29 → V30 → V38 |
| `0xCB844` → `0xE51A8` | Y = 15360 ×9 | **16384 ×9** | mode/gear setpoint ceiling on `gp-0x69ae` | CARRIED — recorded as *"an AUTHORITY raise, DO NOT revert"* | V38 |

**The delivered surface, computed from these bytes** [EVIDENCE, the delta doc §2, arithmetic reproduced
here]:

```
peak forward torque = clamp( 15360 · 5346 >> 15 , ±3072 )  =  2505 counts     (stock: 15360·891>>15 = 417)
                      ^^^^^ the sum clamp 0xC61BE, STOCK on V282
```
⭐ **The ×6 is real authority, not a clamp artefact** — in neither image does the output clamp bind at the
sum clamp's ceiling.

## 1.2 The reference (the "×6 rate setpoint")

| cell | stock | **V282** | what it is | on-car | introduced |
|---|---|---|---|---|---|
| map records `0xC9A88` → slot 7 `0xE502C` | X = 0,12,20,24,32,64,96,128,160,240; Y = 0,24,42,50,62,100,126,154,166,**172** | Y = 0,52,86,103,138,275,413,550,688,**1032** | the **assist map** — the rate loop's REFERENCE, a LERP on the demand index | **MEASURED** (r35 / V281 rev 3). `Y = round(6·Ytop·X/240)`, slope **4.30 flat** vs Honda's saturating curve. Reference ceiling **44.5 → 133.6 deg/s** | V280 rev 2 |
| `0xC62E6` | 7680 | **46080** | the LKAS PID's **feedback saturation clamp**, stored ×256 | MEASURED across the V276 → V280 → V281 arc; preserves Honda's 1.395 setpoint:feedback ratio at the ceiling | V276 (15360) → **46080 at V280** |

🛑 **Read the map for what it is.** `memory/…/accord-lkas-commands-rate-not-torque.md`:
*"LKAS DOES NOT COMMAND TORQUE. IT COMMANDS A STEERING RATE… The map's ceiling is the REFERENCE of a
closed rate loop… the loop pushes until the wheel reaches that rate, then the error crosses zero and it
pushes BACK."* The same note separates the two axes explicitly: **RATE capability** = map ceiling +
`0xC62E6`; **TORQUE capability** = P/sum clamps + gain + output clamp. **They are independent cells and
the operator's requirement names both.**

## 1.3 The controller

| cell | stock | **V282** | what it is | on-car | introduced |
|---|---|---|---|---|---|
| Kp records `0xCB994` → `0xE5378` | X = 0,68,112,136,208; **Y = 248,512,645,696,696** | **Y = 248 ×5** (X untouched) | the rate PID's proportional schedule vs demand index | **MEASURED** — the self-sustained 7 Hz cycle GONE (F7 **0.0 / 100 s** on r35); cost: seven 1–3 s stalled runs at idx 54–79 (the P-only deadband) | **V281 rev 3** (`KP.FLAT.Y0`) |
| Kd record `0xCB7D4` → `0xE511C` | X = 0,11,22,32; Y = **128 ×4** | **identical** | the rate PID's derivative schedule | 🛑 **NEVER EDITED ON ANY FLOWN BUILD.** Listed in the delta doc to close the question | — |
| `0xC63E6` | **0** | **0** | **Ki**, the integral gain | Honda shipped the whole integrator — reset path, anti-windup `0xC61BA` = 10240, deadband `0xC62E4` = 4 — and disabled it with this one cell | — |
| `0xC63E8` / `0xC63EA` | 923 / 1560 | **923 / 1560** (stock) | the **feedback lag pole**, 16.53 Hz, DC 30.891 | never moved in 285 images before V289 | — |
| `0xC63EC` / `0xC63EE` | 992 / 507 | **992 / 507** (stock) | the **output lag pole**, 5.05 Hz, INSIDE the loop | never moved on any flown build | — |
| `0xC61BC` / `0xC61BE` / `0xC61B6` / `0xC61BA` | 15360 / 15360 / 10240 / 10240 | **all stock** | P clamp / sum clamp / **D clamp** / I anti-windup | V287 moved `0xC61B6` to 7680 and it was rejected | — |

**The forward path, in the arithmetic the bytes implement** [EVIDENCE, delta doc §2]:

```
0xE4 cmd → override taper (live arm 255) → demand index idx        [1 LSB = 16.125736 raw counts]
         → assist map (LERP)              → rate setpoint sp
         → E = 32·sp − feedback            (feedback = two-sample sum, DC 30.89, through 0xC63E8/EA)
         → P = E·Kp >> 8   [Kp 248 flat]   D = Kd·ΔE >> 3 on the ERROR  [Kd 128 flat, clamp 0xC61B6]
         → S = clamp(P + D, ±15360)        [0xC61BE, stock]
         → T = clamp(S × 5346 >> 15, ±3072)
         → 5.05 Hz output lag → aggregator (unit weight, via gp-0x6b4c) → governor → motor
```

## 1.4 The two sensor lanes and the rest of the delta

| cell | stock | **V282** | what it is | on-car | introduced |
|---|---|---|---|---|---|
| `0x3AA96` | `0xC5` | `0xFB` | the r24/r26 **rate-lane gate byte**: a dead flag → `gp-0x6806` (`STEER_CONTROL_ACTIVE`) | **MEASURED** — makes Lever B live. Operator on V88: *"the audible grinding is fixed"* | V67; these bytes from V104 |
| `0xC6446` | 512 | **5244** | **Lever B** — the r24 **engaged** rate-lane gain arm | **MEASURED IN BOTH DIRECTIONS.** It **pumps the 7 Hz strong-turn ripple** and supplies **73–86 % of the 20 Hz grinding mode's damping** | V67 gate; **5244 is V88's bracketed optimum**, unbroken since V247 |
| `0x35A08/12/18` + `0xC649B` | stock | arm repoint + enable 1 | arms Honda's dormant **55 Hz notch, engaged-only** | MEASURED (the stock ≥ 5 arm condition was never observed true in 255 k engaged frames) | V103 |
| `0xC62EA` | 320 (≈ 5 km/h) | **0** | the low-speed steer **lockout** | CONFIRMED on-car (route `1a`: 226 frames of `STEER_CONTROL_ACTIVE = 1` below 5 km/h, no fault) | V53; restored V81 |
| `0x55C0E` + `0xC4B34`–`0xC4BD7` | stock / `0xFF` | hook + **164 B cave** | the `0x14A` telemetry cave, 100 Hz, 5 comparator/sign rungs | **INERT BY DESIGN** — publishes bits, writes no control cell | body V31p; cave hash `d3bb75d8` frozen V105 → V281r3 (**177 images**); V282 is the first re-point in that span |
| `0x55DF2`–`0x55E11` | Honda packer | repointed | CAN-**427** publishes delivered LKAS torque `gp-0x6b38` as `(sign(T)<<9) \| (\|T\|>>3)` | INERT BY DESIGN (instrument) | V280 |
| `0xCE000`–`0xD9FFF` (992 B) | Honda curves | rate lanes flattened to `Y[0]`, boost to V59's mean | the base-assist damper's rate + boost banks, all 34+68 records | MEASURED — *"V268's damper flatten is inert below 85 deg/s"* | V268 |
| `0xC40BC/D2/DC` | 600 / 102 / 22 | 1800 / 612 / 14 | Coulomb-relay knee · K1 · α2 | ⚠ **CARRIED BY REBASE** — `0xC40D2` is on record as **measured NULL** at both bands | V112/V109, riding the V255→V112 rebase |
| `0xC61C0/C2/C4` | 1600/896/1280 | `0xFFFF` ×3 | `STEER_STATUS` debounce cals | 🛑 **UNACCOUNTED** — 12 live readers, 0 writers, 249 images, **no lineage entry** | V36 |
| `0xC64B4/B6`, `0xC64B8`, `0xC64DE`, `0x454FE`, version byte, CRCs | — | — | debounce SM · DTC-0x49 gate · square-wave hold · an inert substitution byte · bookkeeping | mixed; `0x454FE` is **measured inert** and ships on inertia | V36/V37/V18/V42 |

**The V282 cave's bit map on CAN `0x14A` byte 4** [EVIDENCE — `BUILD-LINEAGE.md` §*"V282 — V281 rev 3 +
the r24 COMPARATOR TAP"*]: **b7** = `sign(gp-0x6b4c)` (the LKAS summand) · **b6** = `|r24| ≥ |T|` ·
**b5** = `|r24| ≥ |aggregator sum|` · **b4** = `sign(r24)` · **b3** = `sign(gp-0x3680)` ·
**b0–b2 = stock Honda** (`0x14A` has zero free bits outside b3–b7).

---

# 2. EVERY BUILD OR LEVER THAT TOUCHED THE LKAS RATE LOOP'S FEEDBACK

## 2.1 The feedback path, as it exists

```
0x18F wheel rate  →  x = −rate (±12000 saturated by its producer @0x3F7A0, with a lockstep mirror at gp-0x4ca6)
   →  first-order lag: s_new = (a·s >> 10) + (b·x >> 10)        a = 0xC63E8 = 923, b = 0xC63EA = 1560
   →  feedback operand r26 = s + s_new     (the "TWO-SAMPLE SUM", DC = 2b/(1024−a) = 30.891)
   →  saturate to ±0xC62E6                 (V282: 46080)
   →  E = 32·sp − r26
```
State is 32-bit at `gp-0x3d30`; **runs every tick, engaged or not**; `0xC63E8` and `0xC63EA` each have
**exactly one reader image-wide** (`0x28F8A` / `0x28F86`). [EVIDENCE —
`docs/traces/TRACE-2026-09-13-fb-lag-filter-bytes.md`; `ADV-V292-D-INTERLOCKS-2026-09-13.md`]

## 2.2 The ledger

| build | what it did to the feedback | flown? | result |
|---|---|---|---|
| **V275** | scaled the map ×6 and divided Kp by 6 | **withdrawn, never flown** | 🛑 The compensation cancels only the **feedforward** half. `P = 32·sp·Kp − fb·Kp/6`. At the point where V268 delivers **0** torque V275 delivered **2034**; torque varied only 2441→2034 across the whole feedback range vs 2441→0 for V268. **The loop stops nulling.** [`memory/…/accord-scaling-a-setpoint-does-not-scale-its-feedback.md`] |
| **V276** | `0xC62E6` 7680 → **46080**; map ×6 | ✅ **FLOWN** | 🛑 **The only flown build in which the rate loop effectively stopped providing negative feedback.** `E < 0` needs `feedback > 32·sp_ceiling` = **33,024** raw against a median achieved rate of ~6,668. **V276 never crosses at all.** P reached its clamp in **all 28 slots** at full demand (V268: 97.4 %). Operator: a self-exciting **2–4 Hz** oscillation at all speeds, killed only by gripping the wheel. |
| **V278 rev 3** | `0xC62E6` 15360 (K = 2) — the crossover brought back inside the driving range | ✅ **FLOWN** | The 2–4 Hz mode **GONE** (band excess 0.76 vs V276's 4.58, corpus p50 0.82). *"Amazing authority … no more constant oscillations like in V276."* |
| **V279 rev 2** | 🛑 `0xC62E6` → **0**: the feedback operand is clamped to ±0 on all three branches, so `E = 32·sp` exactly. Kd → 0. Kp flat 256. Map Y = 2X. | 🛑 **BUILT, NOT FLOWN** | **This is torque mode.** `ff279` proved the zero-clamp kills all three branches from the bytes; `0xC62E6` has exactly 3 readers image-wide. Five attackers, no do-not-flash. Never flashed: the operator, after the V278r3 drive, *"has given me confidence we do not need to pursue a V279 methodology which requires massive StarPilot side changes."* |
| **V280 rev 2** | `0xC62E6` 15360 → **46080** (V276's value) with the **linear** map | ✅ **FLOWN** | Best authority to date; the stalled/P-desaturating stutter class **gone**; a residual 6.5–7.4 Hz strong-turn ripple **at** the reference. This is V282's value. |
| **V289 rev 1** | fb pole `0xC63E8/EA` 923/1560 → **875/2301** (16.5 → **25 Hz**, DC held) + a notch on the loop **output** | ✅ **FLOWN** (r62/r63) | First move of the fb pole in 285 images. The notch **removed the 20 Hz mode outright** (18–22 Hz band EMPTY, 0 of 1414 present windows) and a **different pre-existing 15–17 Hz pole took its margin**. Operator: *"Grinding is still an issue."* **Measured ζ 0.029 on both builds: the frequency moved, the damping did not.** |
| **V290 option C** | notch on the **feedback operand** (hook `0x28F4C`) + fb pole → **40 Hz** | **designed, NOT CUT** | pkR worst **0.928** against the operator's 0.95 floor. Operator: *"Neither — revert to V282 and stop here."* |
| **V291 (C10)** | fb pole → **962/958** (**9.94 Hz**, DC 30.903 held) + r24 arm 5244 → 4725 + b3 = sign(fb state) | **BUILT, NOT CLEARED, SUPERSEDED-DO-NOT-FLASH** | The first build ever to **lower** the servo's feedback bandwidth. Adversary B: byte-exact steady state ×1.34–1.80 at sp = 3 counts, and a 9–18 Hz sensitivity shoulder worse than V282 on **121/121** fits, peak ×1.99 at 12.85 Hz. |
| **V292** | V291's dose + a 52-byte **error-feedback cave** so the integer filter's mean equals the linear filter's at every amplitude | **BUILT, CLEARED, NOT FLOWN** | The flight candidate. sp = 3 reads ×1.0000 against byte-exact V282. Replay on the operator's own recorded episodes: ring **×0.55**, ring-down **×0.29–0.36**, 6–9 Hz ripple ×1.03/×0.94, torque ×1.00, 9–18 Hz shoulder ×1.1–1.2. |

## 2.3 🛑 HAS THE FEEDBACK EVER BEEN MUTED OR ZEROED ON A FLOWN BUILD?

**No.** [EVIDENCE, by exhaustion of the ledger above and a grep of `0xC62E6` across `BUILD-LINEAGE*.md`
and `analysis-2020accord/builds/`]

- The **only** build that zeroed it is **V279 rev 2, which was never flashed.**
- The closest a flown build has come is **V276**, which did not zero the feedback but pushed its crossover
  out of physical reach. **That is the strongest single piece of on-car evidence about what an open LKAS
  lane feels like, and it is bad:** a `sign(error)` relay driving an underdamped plant, which is the
  textbook self-sustaining limit cycle, and the operator's report matches that mechanism exactly (a firm
  grip stops it; letting go restarts it).
- **V56's mute is a different lane.** It zeroed `0xC6AFC`/`0xC6AFE`, the output bound of `gp-0x6ad4` —
  **a driver-torque tracking PID**, not the LKAS output. It was also scored on **15–26 Hz only** and never
  on 6–9 Hz, and `docs/review/AUDIT-2026-08-12-dead-levers-and-liveness.md` row **I3** flags it as
  *"band-scoped, carried as general."* **Do not cite it as evidence about the rate loop's feedback.**
- **V53–V61 "lane mutes"** in the arc summary refer to that same family of base-assist / driver-torque
  lanes, not to the LKAS rate loop. The rate loop's own feedback was not touched until **V276** moved its
  clamp and **V289** moved its pole.

## 2.4 What the record says the feedback *is* doing

- **It is this lane's damping.** *"rate feedback IS this lane's damping"*
  [`accord-scaling-a-setpoint-does-not-scale-its-feedback`].
- **At 7.3 Hz it is cancelling the r24 pump.** `gate73 = |LS73·R73 + LR73|`, with the servo arm
  `LS73 = 0.55∠+96°` and the r24 pump arm `LR73 = 1.19∠−27°`. The two vectors are nearly orthogonal and
  **partially cancel** — sum magnitude **1.0028**. *"The EPS's own 7.3 Hz rate feedback is currently
  cancelling most of the r24 pump's imaginary part."* [EVIDENCE — `DESIGN-V291-FBLP` §4]
  🛑 **This is the single most load-bearing fact for any build that removes the feedback.**
- **At 20 Hz it contributes only 17 % of the aggregator's damping** (Re +0.68 of magnitude 1.90, i.e.
  36 % efficient as a damper); r24 supplies the other 83 %. [EVIDENCE —
  `GRINDING-DEEP-ANALYSIS-2026-09-03.md` §2]
- **With the loop open there is no 18–22 Hz object at all.** 35 routes, 4,759 s lateral-disengaged: no
  resonance in 16–26 Hz; a synthetic ζ ≤ 0.03 mode at the same energy **would** have been found ⇒
  **ζ_open ≥ 0.05 or non-modal**. Engaged, V282 alone reads ζ **0.0164 [0.0126, 0.0222]** at 20.01 Hz.
  🛑 **Stated limit, from the same document:** opening the loop also removes the LKAS excitation, so
  "no object" has two readings. [EVIDENCE — `rlog-tools/studies/grind/OPENLOOP-RING-DAMPING-2026-09-13.md`]

---

# 3. THE Kd AXIS, THE Kp/Kd SCHEDULE, AND Ki = 0 — WHAT IS CLOSED AND WHAT IS OPEN

## 3.1 Was Kd = 0 ever flown? **No.**

**Kd has been 128 on every FLOWN build in the arc.** The record `0xE511C` is **not virgin** — V279 and
V279 rev 1 set it to 0 — but both are **confounded and unflown**, so it carries no on-car evidence.
[EVIDENCE — `BUILD-LINEAGE.md` §V284, *"Kd record note, for the ZN work that follows"*]

## 3.2 What D contributes at 20 Hz

D is on the **full error**, not on the setpoint: `0x29D76 shl 0x5` then `0x29D78 sub r26,r16`, and
`0x2A18C` stores **E**, not sp. `D = (ΔE·128) >> 3 = 16·ΔE`, clamped ±10240.
[EVIDENCE — `memory/…/accord-d-term-is-on-the-error-and-already-saturates.md`]

At 20 Hz, `|ΔE| = 2·sin(π·20/1000)·|E| = 0.1256·|E|`, so
**`|D|/|P| = 2.07 at Kp 248`**, 1.75 at Kp 295, 1.09 at Kp 470. **D leads P by 90° − 3.6°.** The rate PID
is a PD loop whose **D dominates at the line**. In the open-loop mirror on r34's creep windows, D carries
**67 T-counts against P's 53** — the "D ~55 %" figure in the handoffs.
[EVIDENCE — `rlog-tools/studies/grind/CREEP-20HZ-LOOP-ID-2026-09-03.md` §0 item 1 and §1.2]

**And D is what puts the crossover at 20 Hz.** With the same plant:

| Kd | `\|L(20)\|` | crossover | PM | Ms |
|---|---|---|---|---|
| **128 (flown)** | ≈ 1 | 17–21 Hz | 35–60° | 2–3 at 19–23 Hz |
| 64 | 0.51 | — | — | **3.8 at 8.6 Hz** |
| **0** | **0.37** | **7 Hz** | **22°** | **4.0 at 8.7 Hz** |

🛑 **"Less D" trades the 20 Hz creep line for a WORSE 8 Hz loop** — and 8 Hz is the band the high-angle
stutter lives in. [EVIDENCE — `CREEP-20HZ-LOOP-ID` §0 item 4; BELIEF for the absolute margins, whose
off-line plant estimate has coherence 0.3–0.6]

## 3.3 The Kd axis closes — the numbers

`Kd ∈ [118, 227]` at Kp 248, bracketed from **both** sides: the 7.3 Hz ring improves with more Kd (lower
root 118, so **a Kd CUT re-arms it and stays DO-NOT-FLASH**), the 27–32 Hz mode worsens (Ku ≈ 227
[217–270], Tu ≈ 36 ms). Today's 128 sits **near the floor**. [EVIDENCE —
`docs/research/PID-FRAME-SIZING-KP-KD-2026-09-04.md`; `ZN-ACCEL-FRAME-V285-2026-09-04.md`]

Then the axis closed from the other end: `zn39`'s forced-geometry test shows **the Kd axis flips sign as
the r24 arm shrinks**, and `grind39` measured that arm at **0.41–0.52** of the modelled magnitude.
⭐ **At the measured arm, the best Kd anywhere is worth 1–2 % on the ring** (against 26 % under the
modelled arm). **"Kd is not a weak lever — it is not a lever."**
[EVIDENCE — `HANDOFF-2026-09-04-R39-THE-KD-AXIS-CLOSES-AND-THE-SR-MAP-LANDS.md` §4]

**Also closed on the Kd axis:** `fb × Kd` is **dominated** — Kd raises 7.3 Hz phase but re-injects the
12–26 Hz gain one-for-one, and **Kd ≥ 160 on V282's pole destabilises 77–112 of 121 fits.**
[EVIDENCE — `DESIGN-V291-FBLP` Addendum A]

## 3.4 The Kp/Kd SCHEDULE class

- Both schedules are indexed by the **demand index at exactly 16.125736 wire counts per LSB.**
- **91 % of engaged time (100 % of cruise) sits in Kp's first segment**, so a Y-only Kp edit is nearly
  inert there; **Kd's knots (X = 0/11/22/32) straddle the busy zone instead.**
- 🛑 **The schedule class is CAPPED at ×2.1 ring improvement at INFINITE dose**, because roughly half of
  grinding seconds sit **above** the knot (idx 32) where every Y-only edit is byte-identical to base.
- **Moving the knot X is DOMINATED everywhere** by deepening Y. **The X lever is closed.**
- `Y[0..2] = 0` (deleting D below the knot) reaches only 257 ms and blows `gate73` to **1.0604**.
- The only legal survivor, **S′** (Y = 112,112,112,128), delivers **×1.22** — the ratio the kit has
  already ruled **unreadable from one drive** (within-drive CI ×0.34–2.01 ⇒ half-width ×2.43).
- The **V289 base is dead for any schedule**: pkR 0.799–0.807 at every Kd.
- The parametric-modulation hazard for a scheduled gain is **measured SAFE** (15–50× too slow, 50–500×
  too shallow; the measured `Kd(t)` through the byte-exact clamped mirror never pumped, 9 of 9).
  🛑 **But a Floquet analysis of the UNCLAMPED electronics is not a sufficient parametric-safety argument
  for this loop** — linear reads ~2 % where the clamped mirror reads 0.42×.

[EVIDENCE — `BUILD-LINEAGE.md` §V290 *"LEVERS CLOSED BY THIS DESIGN ROUND"*;
`docs/traces/TRACE-2026-09-09-kp-kd-schedule-axis.md`; `docs/review/V290-ROWS-READABILITY-2026-09-09.md`;
`V290-PARAMETRIC-HAZARD-2026-09-09.md`]

## 3.5 Ki = 0 — tried once, flown once, rejected on principle

**V283 = V282 + `0xC63E6` 0 → 50.** Flown on three routes, Ki fitted 51.9/52.0/52.1 against a 1.2–1.9
control floor. **The prereg PASS sentence FIRED: stalls 7 → 1 pooled — Ki 50 cured the P-only deadband.**
The cost is a DC face: tight-curve achieved÷asked 0.996 → **1.278**; inner DC gain 0.36 → 0.76. A new
residual was found and confirmed: **the integrator does not clear at disengage** (139–383 counts still
delivered 0.5–1.0 s after `STEER_REQUEST` drops).

🛑 **The operator rejected it on principle, not only on the drive:** *"This firmware consistently
oversteers. I don't like the idea of the integrator anyways, it goes against what openpilot is modelling
its output as, a torque."* And later: *"an integrator on steering angle rate is just steering angle,
which would NOT be used in a PID loop on angular acceleration."*
[EVIDENCE — `BUILD-LINEAGE.md` §V283; `HANDOFF-2026-09-04-ZN-ACCEL-FRAME-AND-THE-STARPILOT-RACK-MAP.md` §1]

**Ki does not touch the 20 Hz line** (1.10, p = 0.38).

## 3.6 ⭐ THE FRAME MAPPING — the single most relevant prior fact for "track acceleration"

`docs/research/PID-FRAME-SIZING-KP-KD-2026-09-04.md`, and it is the kit's own answer to the operator's
own question:

> **In the acceleration frame openpilot actually commands, our D is the PROPORTIONAL gain and our P is
> the INTEGRAL gain; our I is a double integral.** Corner 9.64 Hz, `|D|/|P| = 64·(Kd/Kp)·sin(πfT)`,
> `Ti = Kd/(31.25·Kp)`. 🛑 **The raw cell values are not comparable** — `Kd_cell = Kp′·8000`,
> `Kp_cell = (Kp′/Ti)·256`.

⇒ **The existing V282 controller, read in the acceleration frame, is ALREADY a PI controller on angular
acceleration.** "Making the PID track angular acceleration" is therefore **not** a new control law; it is
a re-labelling plus whatever is done to the **error signal**. §7 treats that distinction as the pivot of
the whole verdict.

**And every low-overshoot ZN variant is structurally unreachable**: ZN-no-overshoot (Kd 54),
ZN-some-overshoot (Kd 89) and Tyreus–Luyben (Kd 84) all land **below the floor**, where the 7.3 Hz ring
re-arms. **This loop has a *minimum* gain, which textbook recipes do not anticipate.** Turning the
controller down **withdraws the cancellation** that keeps the two-arm sum sub-unity — *"this loop has no
'quiet it down' regime."* [EVIDENCE — `ZN-BACKWARDS-NO-OVERSHOOT-2026-09-04.md`; handoff 09-04 §4]

---

# 4. THE 7 Hz HIGH-ANGLE STUTTER — the symptom the operator reports WORSE on V292's predecessor base

## 4.1 What it is

A **7.0–7.6 Hz** line present in the wheel rate **and** in the delivered torque T at coherence 1.00, at
`|angle| ≥ 30°`, 3–9 m/s, command railed or near-railed. Driver torque in the episodes is a **7 Hz RING**
(1470–1960 raw amplitude, near-zero mean — column twist), **not a hand**.
[EVIDENCE — `rlog-tools/studies/osc-highangle/HIGHANGLE-V278R3-2026-09-02.md`]

## 4.2 Build-by-build presence — the record's own table

| build | route | high-angle engaged | F7 episodes | F7 per 100 s | mechanism as read at the time |
|---|---|---|---|---|---|
| **stock** (`V9b-STOCK`) | r97 | 86 s | 2 (2.3–2.7 Hz, cliff) | — | **F7 absent**; only the F2 sway family |
| **V112** | r22 | 33 s | 1 (1.9 Hz, cliff) | — | **F7 absent** |
| **V278 rev 3** | r31 | 102 s | 13 (10 at 7 Hz) | **9.8** | 🛑 **P desaturating on a STALLED wheel.** 7 of 10: wheel stalled at 10–20 deg/s against a 36–45 deg/s reference; `E = +7k…+9k`; **P railed ~50 % of ticks**; a ±25 deg/s (±6000 in E) ripple crosses P's 5650 linear window every cycle ⇒ T 100 % modulated |
| **V280 rev 2** | r32 | 37 s | 3 | 8.1 | **stalled class GONE (0 of 7)**; every episode is now **AT the reference**, P linear 62–79 %, no clamp — an inner-loop crossover limit cycle |
| **V280 rev 2** | r33 | — | 4 | 4.3 | same |
| **V280 rev 2** (new tune) | r34 | — | 10 | 6.8 | 10 AT REF + 1 STALL; pooled 18 episodes, idx median 109 |
| **V281 rev 3** (Kp flat 248) | r35 | — | **0** | **0.0** | ⭐ **THE SELF-SUSTAINED 7 Hz CYCLE IS GONE.** 6–8.5 Hz rate ×0.19, tap ×0.14, ripple/level **0.18**, driver ring −41 %. **A damped ring at ~40 % remains**, f0 7.3 unchanged. **COST: seven 1–3 s stalled runs at idx 54–79 delivering 0.62 of V280's torque — the P-only deadband** |
| **V283** (Ki 50) | r36/r37/r38 | — | — | **F7 0.00 unchanged** | Ki cured the deadband (stalls 7 → 1) at the price of a DC face; rejected |
| **V282** (= V281r3 + tap) | r39, r3a, r3c, r6c | — | — | — | the current base; the 6–9 Hz ripple is the **revert signature**, not a live complaint |

## 4.3 What makes it worse, and what makes it better

**WORSE:**
- **More Kp.** `gate73` calibrated against the only 7 Hz lever with an on-car record:
  Kp 248 → **1.0028** (cycle measured GONE); Kp 300 ≈ V280 rev 2's creep Kp → **1.0526** (ripple
  PRESENT, 18 episodes); Kp 512 → 1.3024. [EVIDENCE — `DESIGN-V291-FBLP` §4.2]
- **More r24.** Net aggregator damping at 7 Hz in the loaded stratum is **Re −2.09** (net PUMPING):
  the servo lane contributes +1.17, r24 at 5244 contributes **−3.26**. The zero crossing is at
  `0xC6446` ≈ **1880**; Honda's own arms are 2048 and a 2150–3072 LERP. **V282 flies 5244, i.e. 2.8×
  past neutral.** [EVIDENCE — `GRINDING-DEEP-ANALYSIS-2026-09-03.md` §2]
- **Phase lag anywhere near 7.3 Hz.** Because the servo's `+j` component is what cancels the pump's,
  **94 % of `gate73` damage from a feedback roll-off is PHASE, not magnitude** — the magnitude-only
  column still passes at a 12 Hz pole (1.0071) while the full gate reads 1.0750.
- **A shaped Kp raise across the stall band** (V284): +13 % of loop gain at idx 68 and +31 % at its
  peak, driving the measured ring from 0.976 to **1.106 / 1.277**. **SHELVED.**

**BETTER:**
- **Kp flat 248** — the measured cure for the self-sustained cycle (F7 9.8 → 0.0).
- **Cutting r24.** `gate73` improves **monotonically** with any r24 cut. V291/V292's 5244 → 4725
  (−9.9 %) is what buys the gate back at a 9.94 Hz feedback pole (1.1163 → **1.0099**).
- **Ki**, for the *deadband* that Kp-flat created (stalls 7 → 1) — but at a DC cost the operator rejected.
- **A linear map** (V280): it removed the **stalled** sub-class outright by keeping P desaturated.

## 4.4 🛑 There is no sweet spot on r24, and a high-pass on it is dead

*"gate73 improves monotonically with any r24 cut and the 20 Hz damping falls monotonically — **no sweet
spot**, and a high-pass on r24 is **DEAD*** (it adds lead where r24 already sits at +171°; HP at 5/8 Hz
**re-arms the 7 Hz cycle**). [EVIDENCE — `docs/STATE.md` §*"The r24 lane, traced and measured"*;
`docs/traces/TRACE-2026-09-13-r24-lane-transfer.md`]

⚠ **κ, the effective r24 arm, is DISPUTED and open:** effective ≈ **0.45×** (b6 inversion, V281r3's
cycle-gone), **0.10–0.20** (the V289 bound), **1.45** (the record's pooled split). The wire reads
`GAIN_EFFECTIVE = 2353` against `GAIN_FLOWN = 5244`, i.e. 0.43–0.52 of the closed form. **Two independent
wire measurements of the same arm differ ×1.6 and nobody has reconciled them.**

## 4.5 What V292's dose was predicted to do to the 7 Hz stutter

| quantity | prediction | source |
|---|---|---|
| `gate73` | 1.0028 → **1.0099** (inside the ≤ 1.01 allowance, by 0.0001) | `DESIGN-V291-FBLP` Addendum C |
| 6–9 Hz strong-turn ripple, replayed on the operator's own recorded loaded turns | **×1.03** pooled on r39, **×0.94** on r35; 3 of 15 fits above ×1.05, **worst ×1.10** (the high-authority tail) | `rlog-tools/studies/grind/V292-REPLAY-PREDICTION-2026-09-13.md` |
| 5–9 Hz sensitivity bump | **0.91 at 9 Hz** (C8's crosses at 1.18) | Addendum C |
| capped-step overshoot | 39 % → **49 %** median (×1.21) | `DESIGN-V291-FBLP` §6.4 |
| ⚠ B5 fragility | V292's 5–9 Hz worst reaches 1.0 at only **−5.9°** of loop-phase error, vs V282's −31.6° | `ADV-V292-B-LOOP-2026-09-13.md`, recorded on the STATE page |

⇒ **The design pays the 7.3 Hz gate with a −9.9 % r24 cut and lands 1 part in 10,000 inside the
allowance, with a phase-margin-on-the-gate of ~6°.** That is the thinnest margin in the build.

## 4.6 🛑 WHAT THE RECORD PREDICTS FOR A LANE WITH NO RATE FEEDBACK AT ALL

This is the question the session actually needs answered, so it gets its own treatment. Two effects run
in **opposite directions** and the record sizes both.

**(a) The P-desaturation mechanism disappears — genuinely.**
The V278r3 stutter was `E` swinging across P's linear window because `E = 32·sp − fb` and `fb` carried a
±6000 rate ripple. With `fb ≡ 0`, `E = 32·sp` and the only ripple in `E` is whatever openpilot puts in the
command. The record already computed the counterfactual for the *adjacent* fix (a ×6 top, which pins P at
its rail): **T ripple/level 0.45 → 0.18 open-loop**, and a uniform ×6 gives 0.11.
[EVIDENCE — `rlog-tools/studies/osc-highangle/SERVO-AT-REFERENCE-2026-09-02.md`]
**With fb ≡ 0 the mechanism is not merely reduced, it is removed: there is no feedback ripple to
desaturate on.** [BELIEF, but it follows directly from the arithmetic]

**(b) The r24 pump loses its canceller — and this is the larger, measured term.**
`gate73` with the servo arm removed entirely is `|LR73|` alone = **1.19**. Against an allowance of 1.01
and a calibration where **1.0526 is the configuration whose ripple the operator felt**, that is
**≈ ×2.3 the whole allowance and ~2.5× past the Kp-300 reference point.** The sum today (1.0028) exists
*because* the two arms partially cancel: `0.55∠+96° = (−0.058, +0.547)` plus `1.19∠−27° = (+1.060,
−0.540)` = `(1.003, +0.007)`. **Delete the first vector and nothing cancels the pump's −0.540.**
[EVIDENCE for the arms and the arithmetic — `DESIGN-V291-FBLP` §4. BELIEF that the gate maps
monotonically to felt ripple — but it is the record's own gate, calibrated at two points the operator
has driven.]

**(c) Therefore the record's prediction for a no-feedback lane is: the STALL-class stutter goes, and the
r24-pumped strong-turn ripple gets WORSE unless r24 is cut at the same time.** The kit has a measured
neutral point for exactly this: **`0xC6446` ≈ 1880 takes the 7 Hz net damping to zero**, and
`0xC6446` → 2048 was independently priced as *"the largest free lever found for the 7.3 Hz ring (0.98 →
0.48, no margin or authority cost)"* — **at the price of half the 20 Hz damping**, which in a
no-feedback lane is a price you may already be paying.
[EVIDENCE — `GRINDING-DEEP-ANALYSIS-2026-09-03.md` §2–3; `HANDOFF-2026-09-06` §5.3]

**(d) One more term the record names and nobody has scored for this case:** a no-feedback lane also
removes the loop's own contribution to the **20 Hz** damping (17 % of the aggregator's). §5.4 treats that.

---

# 5. THE GRINDING — what the record says would REMOVE it, and every closed axis

## 5.1 What the object is, in the record's own words

- **It is the LKAS rate loop's 18–22 Hz crossover resonance, D-dominated**, engaged-only, hands-off,
  presence following `Kp(idx)` (13/42/83 % at idx 0 / 1–20 / 20–60), frequency pinned at 20.3–21.0 Hz
  across an 18× range of wheel rate. [`CREEP-20HZ-LOOP-ID-2026-09-03.md`]
- **Refined 2026-09-09: it is a PLANT MODE the loop DE-DAMPS** — the frequency is pinned across
  Kp 248–696 and rises **+0.4 Hz** with gain while damping **falls**; a crossover would move **down**
  2–4 Hz with −26° of controller phase. The Kp-pinning is confirmed **model-free at matched load**, and
  the clamp explanation for it is **FALSIFIED**. [`MODE-NATURE-V289-RECENSUS-2026-09-09.md`]
- **The 12–26 Hz band holds TWO lines, split by DEMAND, not speed**: a low-demand road/plant line at
  12.4–13.8 Hz identical on every build, and the high-demand grinding mode. A pooled median that ignores
  the demand gate drags to a spurious ~14.8 Hz.
- **It is an EXCITED RESONANCE, rung by ordinary broadband noise, with no identifiable source to remove.**
  The decisive measurement: the line's **phase coherence time equals its ring-down time** (6.5–17.4
  cycles) ⇒ *no persistent phase, therefore no persistent source.* Rice K = 0.00, no preferred amplitude,
  no plateau, no hysteresis, no harmonics. [`FORCED-VS-LIMIT-CYCLE-2026-09-10.md`]
- **It is engagement-gated**: ×33–72 rarer with lateral disengaged at matched or higher load across 17
  routes including stock (that is a *presence rate*; the **amplitude** ratio is **×4.5**).
- **Unit trap, corrected 2026-09-13:** the ring is **~16 LSB on the 0x18F RATE channel** (1.98 deg/s).
  The "0.17–0.28 LSB" figure was the ANGLE channel, and it propagated into two design briefs.

## 5.2 🛑 WHAT WOULD REMOVE IT RATHER THAN HALVE IT

The record gives exactly one answer, and it is stated as the kit's current design law:

> **The grinding object is a creature of the closed engaged loop. The lever is to make the LKAS rate loop
> stop acting in 12–26 Hz while keeping its action below ~8 Hz — and the price of that, in this loop, is
> paid at three places: the 7.3 Hz gate (the r24 pump arm), the 9–18 Hz sensitivity waterbed, and the
> feedback quantum at tiny rates. Score every candidate on ALL THREE, pointwise over 3–30 Hz, r24-folded,
> byte-exact — not on a band maximum.** [`docs/STATE.md` §*"THE DESIGN LAW, AS OF 2026-09-13"*]

The two independent facts behind it:
1. **With the loop OPEN there is no 18–22 Hz object** (ζ_open ≥ 0.05 or non-modal, 35 routes).
2. **V289's notch — an in-situ loop-opening at 20 Hz — removed the 20 Hz mode outright** (18–22 Hz band
   EMPTY, 0 of 1414 present windows). **What it did not do is quieten the car**, because a *different,
   pre-existing* 15–17 Hz pole took the margin the notch skirt (−41.6°) and the new fb pole (+11.5°)
   spent. **Measured ζ 0.029 on both builds.**

⇒ 🛑 **CLASS LESSON, recorded verbatim in the lineage:** *"a notch on this loop removes its target band
and hands dominance to the next crossing — a loop-shaping build must price the pole it CREATES, not only
the one it kills."*

⇒ **"Remove the grinding" therefore means: remove the loop's action across the WHOLE 12–26 Hz band at
once, and verify that the pole it creates is not inside 15–17 Hz.** A narrowband intervention has already
been flown and produced a relocated, louder, train-like ring the operator rejected.

## 5.3 EVERY CLOSED AXIS, WITH THE NUMBER THAT CLOSED IT

| axis | status | the number |
|---|---|---|
| **Notch at the mode (loop output)** | 🛑 **FLOWN AND REJECTED** (V289) | Removed 20 Hz completely (0/1414 windows) but the 15–17 Hz line stands ×9.6–23.2 above the floor, loudest episodes **725–826 raw** vs every V288/V282 bookmark. Operator: *"Grinding is still an issue."* |
| **Notch on the feedback operand** (V290-C) | **designed, NOT CUT** | pkR worst **0.928** vs the 0.95 floor; and it **re-creates** a 16.5 Hz pole at ζ +0.057 in 100 % of surviving fits |
| **Filter PLACEMENT** (forward vs feedback) | ⭐ **SETTLED, and it is not a damping lever** | Forward and feedback placement of the same filter are **algebraically identical** in poles, ζ, Ms, PM, GM and `gate73` **to machine precision**; they differ **only** in transient authority (pkR 0.78 → 0.98). V289's ×0.91 authority price was a price for the **topology**, not the damping |
| **Kp/Kd schedule** | 🛑 **CLOSED** | capped at **×2.1 at infinite dose**; only legal survivor delivers **×1.22**, below the **×2.43** readability floor; knot-X lever **dominated everywhere** |
| **fb × Kd** | **CLOSED** | dominated; **Kd ≥ 160 destabilises 77–112 of 121 fits** |
| **2nd-order feedback low-pass** (6–12 Hz) | **CLOSED** | all 16 rows fail `gate73` and stability; **up to 70/121 unstable**; two poles on the 8–15 Hz crossover spend up to 180° at once |
| **Output-lag pole UP** | 🛑 **DO-NOT-FLASH** | a **waterbed** — the sensitivity peak already sits at ~26 Hz; 15 Hz (932/1457) takes **GM to 0.72×** and fires Honda's oscillation detector. Re-confirmed independently: **93–109 of 121 fits unstable** |
| **Output-lag pairing with the fb pole** | **CLOSED** | 25 combinations, **no feasible cell**; best paired row still fails at 1.0288 |
| **P-path-only split** | **PARKED** | passes all five gates (gate 0.978, ring ×1.98, pkR_w 1.007) but is a lead compensator built by subtraction: **`\|T(3.9)\| ×2.37`**, `\|ΔL\|` below 5 Hz **82–93 %**, step overshoot 90–126 %. It buys 20 Hz with the 3–4 Hz band the lane-change ring lives in |
| **The added post-lag term** | **CLOSED, either sign** | minus drives the 16.4 Hz pole to **ζ −0.082**; plus removes it but the crossover reappears at 26.9 Hz **ζ +0.006** |
| **D-term clamp `0xC61B6`** | **REJECTED BY THE OPERATOR** | 2560 FAILED adversary B (effective Kd 95 in the loaded stratum, ring `\|L_tot\|` **1.038**); 7680 is a **~5 %** mitigant needing ~1,150 onsets ≈ **38 min** engaged. Operator on V287: *"still felt the grinding"*, and then rejected the whole class |
| **Reference-side / setpoint pre-filter** | ⚠ **FLOWN INERT, then the null was VOIDED, then re-closed** | V288 rev 2's cave was **live** (D-bind ×0.03) and grinding was **unchanged** — same 20.0–20.4 Hz line, same rate, amplitude, trigger class. 🛑 The 2026-09-10 session found the cave was **amplitude-dependent, not LTI, and transparent at the ring's amplitude**, so the null never tested the class. The class is **reopened in principle**; any retry needs a **fractional accumulator**, not a `>>k` integer IIR |
| **The excitation** | 🛑 **NOTHING TO REMOVE** | 514 burst onsets on 5 routes: no triggering event class; slew cap binds ≤ 8.2 %, best of any class ≤ 13.3 %, Δ² spikes 0 % [0, 2.0]; road/IMU **null** in 30 tests |
| **The 20 Hz camera comb** | **REAL, BOUNDED, NOT THE GRINDING** | modeld's 19.99974 Hz staircase, never smoothed because `clip_curvature` **never binds** (0.000). **Lock fraction ≈ 0.50** (corrected from 3.5–14.5 %); **perfect deletion buys ≈ 29 % amplitude (~3 dB)**. ⚠ V289 already flew the un-forced case and it got **worse** (confounded) |
| **The outer loop as the carrier** | **BOUNDED** | `\|L\| = 0.026–0.165`, bound **≤ 0.189** |
| **Cal-only levers on the V282 base, as a class** | 🛑 **EXHAUSTED** | `memory/…/accord-grind1-cal-only-levers-on-v282-are-exhausted-…` — every one priced on one model anchored to the measured loop; **none removes it without a trade** |

## 5.4 What V292 is predicted to deliver, and why it is a halving and not a removal

| quantity | V292 vs V282 | source |
|---|---|---|
| 18–22 Hz ring amplitude | **×0.55** [0.54, 0.57]; **×0.71** on the freshest route r6c | replay on the operator's own 10 loudest recorded grinding windows × 23 plant fits |
| mode ring-down time | **×0.29–0.36** (free half-life 108–197 → 39–71 ms; ζ 0.02–0.04 → 0.07–0.14) | same |
| max `\|1/(1+L)\|` over 12–26 Hz | 19.4 → **3.6 unfolded**, ×3.7–5.2 folded | byte-exact z-domain, 121-fit family |
| sensitivity at 20.3 Hz | **×0.34** | same |
| **9–18 Hz shoulder** | ⚠ **×1.09–1.11 (r39), ×1.17 (r6c), worst fit ×1.36** in replay; **×1.33–1.70 byte-exact at 12.85 Hz** | the pre-registered REVERT SIGNATURE |
| delivered torque outside the ring bands | ×0.999–1.000 | replay |

🛑 **It is a halving because the loop is opened above ~10 Hz, not removed from the band.** The record's
own null sentence for the build says so: *"decay not below 1.23× V282's while the phase HAS moved ⇒ the
object's damping is not set by the rate loop's return ratio ⇒ the whole in-loop class is closed."*

---

# 6. THE OPENPILOT SIDE

## 6.1 What the controller actually is

- **The car runs `LatControlTorque`** on 60/60 logged routes — the **TORQUE** controller. The operator's
  toggle `ForceTorqueController` is ON. `HondaLateralPidKpScale/KiScale = 0.33` is read by exactly one
  file, `latcontrol_pid.py`, and is **INERT** on the torque path. [EVIDENCE — `HANDOFF-2026-09-02-v279`;
  `memory/…/accord-starpilot-torque-controller-the-033-multiplier-was-inert.md`]
- **`kp` = 0.600 on ALL 60 routes** — the Honda Kp/Ki scale never acted. Later per-route values
  0.8 / 0.9 were measured; the note needs that amendment.
- **The law:** `T = [kp·e′ + I + FF]/LAF + friction·sat((e′ + 0.22·j_f)/0.30)`, kp = `SteerKP`,
  ki = 0.15, **kd = 0**, `FRICTION_THRESHOLD` 0.30 m/s². **Friction is LAF-independent and is 60–80 % of
  the small-signal gain.**
- 🛑 **`torqued` CANNOT VALIDATE ON THE MODDED EPS**: engaged `|torque|` p90 is 0.06–0.12 against buckets
  needing `|x|` up to 0.5; `totalBucketPoints` frozen at 6653. **`liveValid` was 0 on every tick** of
  r31/r32/r33, so the controller ran the **defaults 1.689 / 0.212** on every modded route. The earlier
  "raw LAF 4.5–5.2 clipped to 2.196" reading is **corrected: nothing was applied.**
- **Back-calculated from the car:** the car needs **friction ≈ 0.025** (the measured deadband; the
  asserted 0.08 was 3–4× the car) and **true LAF 5–10** (later refined to **≈ 3.3** by an
  invariance check across three assumed values spanning 1.9×, agreeing to 5 %; and to **12–15** on the
  2026-09-04 FF-balance reading). 🛑 **The two estimates disagree ×4 and the disagreement is open.**

## 6.2 🛑 "LKAS commands a RATE, and openpilot thinks it is commanding a TORQUE"

This is the structural mismatch behind the whole session goal, and the record states both halves:

- **Firmware side:** *"LKAS DOES NOT COMMAND TORQUE. IT COMMANDS A STEERING RATE… every build since V38
  moved how hard the loop PUSHES; none ever moved what it ASKS FOR."*
- **openpilot side:** the operator, 2026-09-04: *"an integrator on steering angle rate is just steering
  angle, which would NOT be used in a PID loop on angular acceleration"* and *"openpilot is modelling its
  output as a torque."*
- **The plant openpilot sees, measured:** *"stock's P term rails at `|E|` = 440 operand counts — ±1.8
  deg/s of rate error. With the wheel still, stock delivers its full 417 at a command of ~113 counts
  (< 3 % of scale)… To openpilot's angle PID the plant has looked like an INTEGRATOR (cmd → rate →
  angle)."* ⚠ The *"bang-bang servo, P rails at |E| = 440"* memory is marked **RETRACTED** for a second
  ×32 the bytes do not have (`P = E·Kp>>8`); **the qualitative point — that the plant reads as an
  integrator to openpilot — survives in the V279 handoff and in the measured `|P|` 11 / 5 / 2.5 at
  0.1 / 0.3 / 1 Hz.**
- **V279's own framing of the consequence:** *"V279 gives it torque into a spring-inertia column — a
  different loop SHAPE, so 'stock gain ÷ V279 gain' has no finite value and the multipliers could not be
  scaled; they had to be derived from the cmd→angle loop."* 🛑 **A torque-mode firmware changes the
  plant openpilot is tuned against, and the record says the retune cannot be derived by scaling.**

## 6.3 The steer-ratio map, and why it is not a tuning knob

**The rack is variable-ratio, measured** on the operator's own artifact (427 min / 47 routes, four
independent estimators): flat **≈16:1 to 48°**, quickening to **≈11.1:1** at lock.
⭐ `14.0/16.33 = 0.857` is **exactly** the old constant, i.e. StarPilot shipped *the rack at ~95° applied
at every angle*; `SteerRatio 12.5` is *the rack near LOCK applied at every angle*.

🛑 **THE SR MAP IS AN UNCONDITIONAL KEEP** (operator, 2026-09-04: *"SR is a definite keep for sure"*), and
the handoff records that the orchestrator framed it wrongly at first: **it is not a tuning change to be
validated on a drive — it is a correction to a measurement that was wrong.** *"Do not score the map.
Score what REMAINS once the measurement is honest."*

**And as of 2026-09-10 the deployed map is TOO FLAT** [EVIDENCE, SR-free instrument, r62/r63]:

| `\|wheel angle\|` | sR_true measured | map serves | road / asked |
|---|---|---|---|
| 2–6° | 16.9–18.0 | 16.33 | 0.95 |
| 12–60° | 15.9–16.5 | 16.33 | 1.01 |
| **60–400°** | **14.6–15.8** | 15.2–16.3 | **1.04–1.13** |

**ANGLE-driven, not a speed artefact** (rows move, columns do not). ⚠ n is thin above 45° (8–24 s).
The fork's own docstring derives **neutral level = 16.00 / 1.116 = 14.3**; the toggle sits at **16.33**.
**The lever is built and unused.**

## 6.4 The fork's state, and the rate-plant feedforward

Device build `0f98d8c75`, branch `Dom`, measured 2026-09-10: `AccordRatePlantFF` **True**,
`AccordFFRateGain` 0.5, `AccordTorqueKi` 0.30, `AccordVariableSteerRatio` True, `AccordTurnFFTaper`
**False (a dead toggle under the plant FF)**, `ForceAutoTune` **False**, `SteerRatio` **16.33**,
`SteerLatAccel` **6.0**, `SteerFriction` **0.01**, `SteerKP` **0.9**.

🛑 **`SteerLatAccel` 6.0 divides every P and I term, so feedback authority in torque fell ×2.5**
(0.8/2.11 = 0.379 → 0.9/6.0 = 0.150) while the **open-loop rate-plant FF took over the load.** Verified on
the wire: `pid_log.output / pid_log.f` = −0.137…−0.171 ≈ −1/6.
**The rate-plant FF is bandwidth-blind to a 10 Hz inner loop (~2 % perturbation);
`AccordTorqueKi` 0.30 → 0.15 is the conservative knob; `AccordRatePlantFF = False` is NOT conservative
(×2.4–4.3 steady FF).**

**`ModelCurvatureLead` / toggle `AccordCurvatureLead`** (uncommitted, default **OFF**, gain 0.75): a
slope-continuous extrapolation of the 20 Hz modelV2 staircase. Removes **63–66 %** of the camera-locked
leg but cuts the `0xE4` 18–22 Hz band only **−2.4 dB (r39) / −4.2 dB (r63)**, adds **+0.9–2.5 dB at
5–18 Hz**, `|H| ≥ 1` everywhere (no authority loss), a **lead below ~3.5 Hz and a LAG above it**.
~−18 % ring: **unreadable from one drive.** 🛑 **It must stay OFF for a V292 drive — with it ON, B5
fails.** Design B (trajectory-shaped, "lag-negative") is **FALSIFIED** — orientationRate is a different
head and a worse predictor.

## 6.5 🛑 THE OPERATOR'S STANDING FORK RULES — quoted

**2026-09-10, verbatim** (`memory/feedback/builds/feedback-no-openpilot-side-modifications.md`, AMENDED;
also `HANDOFF-2026-09-10-THE-EXCITATION-CENSUS.md` §5):

> *"I am fine with openpilot-side changes. That memory was only relevant to that specific section. But in
> general, I think the EPS should act faithfully on the openpilot commands. Only for the grinding issue,
> it's been so pervasive and after so much hard work on the EPS-side we still can't seem to get rid of it.
> So I'm willing to accept openpilot changes if the model's connection / steering authority is not limited
> (like by a LPF for example)."*

**What the memory records as the binding reading:**
- **Allowed, for the GRINDING issue only:** anything that removes 12–26 Hz content **without costing
  command authority or lag** — slope-continuous reconstruction of `desiredCurvature`, measurement-side
  filtering/notching, quantiser dither / error-feedback noise shaping, fixing an aliasing fold.
- 🛑 **Still forbidden:** anything that **limits the model's connection or steering authority**. Named
  explicitly by the operator: **a low-pass filter on the command.** By extension: added command lag,
  clipped output slew, reduced `STEER_MAX`, a lowered `STEER_DELTA_UP`. *"A colleague's fork fixes a
  different symptom this way (τ 0.10–0.28 s, costing 100–280 ms of group delay and −32° to −59° at 1 Hz);
  the operator has rejected that class by name."*
- **Scope is the grinding issue.** Outside it the default stands: **the EPS should act faithfully on
  openpilot's commands.**
- **How to apply:** *"state each one's added lag in ms and authority cost explicitly — those are the gates
  he will judge it on."*

**Two earlier operator rulings that are specifications, not preferences:**
> *"Oversteer is probably outerloop responsibility."*
> *"Innerloop is merely responsible for accelerating the steering angle as demanded by outerloop."*
> — 2026-09-04. The handoff records: *"That second sentence is a SPECIFICATION. It makes the EPS rate PID
> an **actuator judged on fidelity**, not a regulator judged on disturbance rejection."*

⭐ **That specification is the strongest textual support in the whole record for the torque-mode /
acceleration-tracking direction, and it predates this session.**

---

# 7. THE VERDICT TABLE — three classes

## 7.1 What "authority" means, quoted, and whether a torque-mode lane can have a "rate setpoint"

**The requirement, verbatim in substance** (`HANDOFF-2026-09-13-V291-LOOP-OPENING-BUILT-NOT-CLEARED.md`
§0): *"a new EPS firmware, with StarPilot changes if necessary, that keeps V282's authority (**×6 torque,
×6 rate setpoint, no EME faults**) and has no grinding."*

**The record's operational definitions:**

| phrase | the cells | the number, read from the image |
|---|---|---|
| **×6 torque** | `0xC6CD0` = 5346 (via the `0x2A1F0` repoint) + `0xC61B2/B4` = 3072 + the stock sum clamp `0xC61BE` = 15360 | **peak delivered forward torque 2505 counts** vs stock **417**, and *"in neither image does the output clamp bind at the sum clamp's ceiling"* |
| **×6 rate setpoint** | the assist map slot 7 top **1032** (stock 172) + `0xC62E6` = 46080 | **reference ceiling 133.6 deg/s** (V278 rev 3's ×2 map gave 44.5) |
| **no EME faults** | `0xC674E/50/5A/5C` = ±5120, `0xC6768/6A/6C` = 5120, the seven f32 mirrors = ±5.0 | the ×5 ladder; `0xC674E` **must stay above** the tracking clamp 3072 or the build aborts; int and float must move together or the lockstep monitor trips |

🛑 **CAN A TORQUE-MODE LANE BE SAID TO HAVE A "RATE SETPOINT"? No — and this is not a quibble.**
With `fb ≡ 0` the quantity the map produces is never compared to anything measured. `E = 32·sp`, so the
map becomes a **command-to-torque gain schedule**, and the only meaning left in "133.6 deg/s" is
whatever rate the plant happens to reach at the torque that schedule delivers. **The ×6 torque survives
literally; the ×6 rate setpoint survives only as a name.** What *can* be preserved is **the delivered
torque-vs-command surface**, which is what the operator has actually been driving and scoring.

⚠ **And there is a concrete arithmetic consequence nobody has written down.** [EVIDENCE — computed here
from the image constants in §1.3, using the record's own `P = (32·sp·Kp)>>8`, validated against V279's
published identity `P = 64·idx` at Kp 256 / `sp = 2·idx`]

```
V282 cells, feedback forced to zero:
  P = (32 · sp · 248) >> 8 = 31.0 · sp
  P clamp 15360  =>  sp_rail = 495.5 counts
  linear map slope 4.30/idx  =>  idx_rail = 115.2
  idx LSB 16.125736 wire counts  =>  0xE4 command ~1858 of 4096  (~45 % of scale)
```
⇒ **A torque-mode build that keeps V282's map AND V282's Kp 248 delivers a ramp to full torque at ~45 %
of command and is FLAT above it.** To keep the delivered surface **linear to full command** with
`fb ≡ 0`, Kp must come down to **119** (`(32·1032·119)>>8 = 15351`, just under the 15360 clamp; 120 gives
15480 and clips). **That is a derived design constant, not a recommendation** — it is here so the next
design does not rediscover the clipping the hard way, the way V273/V274 did.

**Verification of this block, run this session** (integer Python, V850 semantics, constants as tabulated
in §1). The same script reproduces four numbers the record publishes independently, which is what makes
the two new ones trustworthy:

| check | this session | the record's published value |
|---|---|---|
| `min((15360·5346)>>15, 3072)` | **2505** | 2505 (delta doc §2) |
| `min((15360·891)>>15, 512)` | **417** | 417 (delta doc §2) |
| `P = (32·2·idx·256)>>8 == 64·idx` for all idx 0…240 | **True**, P(240) = **15360** | V279's published identity, *"P = 32·2idx·256>>8 = 64·idx exactly"* |
| fb lag `DC = 2b/(1024−a)`, `f = (1000/2π)·ln(1024/a)` | V282 **30.8911 / 16.53 Hz** · V289 **30.8859 / 25.03 Hz** · V291-2 **30.9032 / 9.94 Hz** | 30.891/16.53, 30.886/25.03, 30.903/9.94 |
| V276's sign-crossing threshold `32·(6·172)` | **33,024** | 33,024 (`HANDOFF-2026-09-01-the-loop-that-stopped-damping.md`) |
| ⭐ **new:** `sp_rail` at Kp 248 with `fb ≡ 0` | **495.5** counts → idx **115.2** → **1,858** of 4,096 wire counts (**45.4 %**) | — |
| ⭐ **new:** Kp for an exact full-command fit | **119.07** ⇒ cell **119** | — |

## 7.2 The three classes

### CLASS A — **TORQUE MODE** (LKAS lane feedback ≡ 0, `T = f(cmd)`)

| | |
|---|---|
| **What the record ALREADY says (EVIDENCE)** | • **Built once as V279 rev 2 and never flown.** Cal-only + one packer window; `FUN_00028ea6` byte-identical; **outside the bricking class**. `0xC62E6` = 0 kills the feedback operand on **all three branches**; it has exactly 3 readers image-wide. • **Peak torque is structurally preserved** at 2505 by the P clamp regardless of the map. • **The operator's own 2026-09-04 specification** — *"Innerloop is merely responsible for accelerating the steering angle as demanded by outerloop"* — is this class. • **The P-desaturation mechanism behind the 7 Hz high-angle stutter cannot exist** without feedback ripple in `E`. • **The 20 Hz grinding object does not exist with the loop open** (ζ_open ≥ 0.05, 35 routes). |
| **What is UNTESTED** | • **Everything on-car.** No flown build has ever had `fb = 0`. • Whether the 20 Hz mode survives with the LKAS lane's 17 % of the aggregator's damping removed **and r24 still at 5244**. • Whether the soft-EME integrator winds up: it integrates `(cmd − bound)` **unattenuated at 1 kHz**, and a sustained 100-count excess arms SM2 in **153 ms**. A no-feedback lane holds a **steady** command where V282's nulls — **the duty at which the command sits high is what changes, not the peak.** • openpilot's outer-loop margin against a torque plant — *"never measured"*, and the record says the retune **cannot be derived by scaling.** |
| **What is FALSIFIED** | • **V275's version of it** — scaling the reference and dividing Kp — is falsified and the reason is general: it half-cancels and leaves a torque pedestal that can never null. • **A partially-open loop is falsified on-car: V276.** `E` that can never change sign ⇒ `sign(error)` relay ⇒ a self-exciting 2–4 Hz limit cycle at all speeds. |
| **Levers that LOOK like it but are NOT** | • 🛑 **V56's lane mute** — a different lane (`gp-0x6ad4`, driver-torque PID), band-scoped 15–26 Hz. **FALSIFIED-for-a-different-thing, not evidence here.** • 🛑 **V276** — INERT-BY-MODE, not zeroed: the feedback was still computed and still subtracted, just never able to dominate. • 🛑 **V289/V291/V292** — these *open the loop above a corner*. They are the same direction at a smaller dose, not the same experiment. • **V285 (Kp = 0)** — a bench config, **DO NOT FLY**, zero steady-state lane keeping. |
| **RISK — bricking** | ⭐ **LOWEST OF THE THREE. No cave is required.** `0xC62E6` → 0 is one halfword; `Kd` → 0 is a LERP bank. V279 rev 2 was cal-only plus one in-place packer window — the class every success since V29 belongs to. |
| **RISK — authority** | Peak torque **unchanged** (structural). **But the delivered surface changes shape** (§7.1): a ramp-and-clip at ~45 % command unless Kp comes down to ~119. And the *rate* the car reaches is no longer regulated — it is whatever the plant does under a fixed torque, which is exactly what varies with road load, speed and tyre. |
| **RISK — EME** | The ladder cells are untouched, so the ceiling is unchanged. ⚠ **But the soft EME is an unattenuated integrator on `(cmd − bound)`**, and the corridor arm is **OFF hands-off** (zeroed when `\|gp-0x6bf0\| ≤ 9216`). V31's boost floor is what holds today. **A sustained rather than nulling command is a new duty cycle for that integrator and it has never been driven.** [BELIEF — the mechanism is EVIDENCE; its behaviour under a torque-mode lane is untested] |
| **RISK — the 7 Hz pump** | 🛑 **THE LARGEST SCORED RISK.** `gate73` with the servo arm deleted is `\|LR73\|` = **1.19** against an allowance of 1.01 and a felt-ripple reference of 1.0526. **The r24 pump loses its canceller.** Mitigation exists and is measured: `0xC6446` ≈ **1880** is the 7 Hz neutral point, 2048 was priced at ring 0.98 → 0.48 with **no margin or authority cost** — at the price of **half the 20 Hz damping**. |
| **RISK — driver-torque interplay** | The override taper's **live arm is 255** and openpilot sends the arm field as **0**, so the 2240-cliff arm is never selected; the live post-PID fade is `0xCBBC4`. **Driver torque still enters through the taper and through r24**, and r24's 7 Hz pump is driven by the **torsion bar**, which is exactly what a driver's hands load. **A no-feedback lane cannot back off for a driver** — V276's *"only way to stop it is to hold the wheel very firmly"* is the shape of that failure. |

### CLASS B — **ACCELERATION TRACKING** (`fb = Δrate`)

| | |
|---|---|
| **What the record ALREADY says (EVIDENCE)** | • ⭐ **In the acceleration frame openpilot commands, D is ALREADY the proportional gain and P is ALREADY the integral gain.** Corner 9.64 Hz. **The controller is already a PI on acceleration; what would change is the ERROR.** • The raw cells are not comparable across frames: `Kd_cell = Kp′·8000`, `Kp_cell = (Kp′/Ti)·256`. • **D is already on the full error** and `E_prev` is already stored (`gp-0x6cf8`, `st.w` @`0x2A18C`) — the differencer exists. |
| **What is UNTESTED** | • **Everything.** No build has ever differentiated the feedback. • The instrument: **the 0x18F rate channel is NOT band-limited** (PSD rises monotonically to Nyquist, 1.8–4.8× on all five routes; no anti-alias filter anywhere). Differentiating it amplifies exactly the folded content the record says is unbounded. 🛑 *"A FREQUENCY endpoint is UNSOUND"* and the folded fraction is **currently unbounded** (`task5rate` withdrew its own ≤ 22–33 % bound). |
| **What is FALSIFIED** | • **The 1 kHz `dE` cave is PERMANENTLY RETIRED** — not because it was wrong but because the endpoint it served was unsound. • **Every low-overshoot ZN variant** on this loop (Kd 54 / 84 / 89) lands **below the ring floor** and re-arms the 7.3 Hz cycle. **This loop has a minimum gain.** • **Kd as a lever is closed** at the measured r24 arm (1–2 %). |
| **Levers that LOOK like it but are NOT** | • **V283's Ki** is the opposite move (one more integration, not one fewer). • **The D term** is a derivative of the *error*, not a change of the tracked quantity. **Raising Kd is INERT-BY-MODE for this question.** • **V285 (Kp = 0)** is the ZN P-only condition *in the acceleration frame*, i.e. the nearest structural cousin — and it is a **bench config with zero steady-state lane keeping**, `dE = 0 ⇒ D = 0 ⇒ S = 0 ⇒ L(0) = 0` exactly, verified three ways. |
| **RISK — bricking** | 🛑 **HIGHEST. This class REQUIRES A CAVE.** Differentiating the feedback needs a new RAM state cell and a hook, and **code caves are this kit's only bricking class** (V24, V27, V48B all bricked the ECU). GATE 1 (RAM ownership, including register-indirect writers) and GATE 2 (closed-loop stability, magnitude **and** phase) both apply. ⚠ And a cave that filters `x` **must do it in-register after the `ld.h` at `0x28F4C` and must never write `gp-0x6a56` back**, or it desyncs the `gp-0x4ca6` lockstep mirror. |
| **RISK — authority** | A pure derivative feedback has **zero DC gain**, so steady-state lane keeping comes entirely from the feedforward — i.e. it degenerates toward Class A at DC, with Class A's surface problem plus a cave. |
| **RISK — EME** | Same as Class A at DC (a non-nulling lane), plus whatever the cave's own execution time costs. V289's cave was 53 instructions and flew; V292's adds 10 per 1 ms tick. |
| **RISK — the 7 Hz pump** | A derivative **adds lead**, which is the right sign at 7.3 Hz — **but the record has already killed the nearest instance of that idea**: a high-pass on r24 is **DEAD** because it adds lead where r24 already sits at +171°, and HP at 5/8 Hz **re-arms the 7 Hz cycle.** Whether the same argument transfers to the servo arm is **open and would have to be scored on `gate73` directly.** |
| **RISK — driver-torque interplay** | Unchanged in kind from today; the derivative would make the lane **more** sensitive to the bar's 7.8–8.6 Hz torsional mode, which is the mode the whole 7 Hz story runs through. |

### CLASS C — **STARPILOT RATE TARGET** (firmware stays a rate servo; openpilot models it and outputs a target angular velocity)

| | |
|---|---|
| **What the record ALREADY says (EVIDENCE)** | • **The firmware is already a rate servo and the map is already its reference** — this class asks openpilot to speak the firmware's own language instead of changing the firmware. • ⭐ **NO FLASH, therefore NO BRICKING EXPOSURE** — the memory records this as a real advantage worth stating. • The operator has **already amended the fork rules to allow fork-side fixes for grinding**, gated on **authority and lag, not location**. • The command path is fully characterised: 100 Hz, changes on **92 %** of frames, **slew-capped at 123 raw/frame by openpilot's own limit** (0.03 × 4096 = 122.88), and `clip_curvature` **never binds**. • The demand index axis is known exactly: **16.125736 wire counts per LSB**, and the map is a LERP the fork could invert. |
| **What is UNTESTED** | • Whether openpilot can produce a stable outer loop against a rate reference — **the outer-loop phase margin of the torque controller on this car has NEVER been measured.** • Whether a rate target is even expressible: `LatControlTorque` outputs a torque and the Accord's `0xE4` field is a **command index**, not a rate. **A rate target would have to be mapped through the assist map's inverse in the fork.** • Whether the 20 Hz mode responds at all: **it is engagement-gated and loop-borne**, and this class does not change the loop. |
| **What is FALSIFIED** | 🛑 **THE MOST IMPORTANT ENTRY IN THIS TABLE FOR CLASS C: the grinding is not reachable from the command side.** • The excitation census found **no triggering event class** (514 onsets, 5 routes; cap binds ≤ 8.2 %, best of any class ≤ 13.3 %). • The line's **coherence time equals its ring-down time** ⇒ no persistent source. • Perfect deletion of the 20 Hz camera comb is worth **≈ 29 % amplitude (~3 dB)**, and **V289 already flew the un-forced case and the symptom got WORSE** (confounded). • `ModelCurvatureLead` measures **−2.4 / −4.2 dB** on the band, **~−18 % ring: unreadable from one drive.** • **A command LPF is forbidden by name.** |
| **Levers that LOOK like it but are NOT** | • **The SR map** is a **measurement correction**, not a tuning change and not a rate target. *"Do not score the map."* • **`SteerLatAccel`** scales the whole controller output; it is a **loop-gain** knob, not a change of tracked quantity — and going straight to the measured truth would be a 6× loop-gain cut in one step. • **The rate-plant FF already in the fork** is an open-loop feedforward, **bandwidth-blind to a 10 Hz inner loop (~2 %)** — it is not a rate servo model in the sense this class means. |
| **RISK — bricking** | **NONE.** No flash. |
| **RISK — authority** | The binding constraint is the operator's own: **no LPF, no added lag, no authority cut.** An inverse-map rate target is a **static** nonlinearity, so it adds no lag by construction — that is the one structural point in its favour. ⚠ But inverting a saturating map **amplifies command noise wherever the map is flat**, and V282's map is linear, so this is benign on V282 and would not be on stock's concave shape. |
| **RISK — EME** | Unchanged; the firmware is untouched. |
| **RISK — the 7 Hz pump** | Unchanged by construction — **which is also the problem.** The 7 Hz ripple is an **EPS-internal** two-arm phenomenon (`gate73`), measured EPS-internal on r34 (*"strong-turn ripple unchanged … wheel at reference, P linear → EPS-internal"*). **Class C cannot touch it.** |
| **RISK — driver-torque interplay** | Unchanged. |

## 7.3 The three requirements, scored against the three classes

| requirement | A — torque mode | B — accel tracking | C — StarPilot rate target |
|---|---|---|---|
| **×6 torque (peak 2505)** | ✅ structural, unchanged | ✅ structural, unchanged | ✅ unchanged |
| **×6 rate setpoint (133.6 deg/s reference)** | 🛑 **the cell survives, the meaning does not** — and the delivered surface clips at ~45 % command unless Kp → ~119 | ⚠ survives at AC, vanishes at DC | ✅ unchanged |
| **no EME faults** | ⚠ ceiling unchanged, **duty untested** | ⚠ same, plus cave execution | ✅ unchanged |
| **no grinding** | ⭐ the only class the openloop measurement says removes the object outright — **at the cost of removing the loop entirely** | ⚠ unscored; the derivative's phase at 20 Hz is the whole question | 🛑 **falsified as a grinding lever** — worth ~3 dB at best |
| **no stutter/oscillation** | ⚠ **splits**: the stall class goes, the r24 pump gets worse (gate 1.0028 → 1.19) unless r24 is cut | ⚠ unscored | 🛑 cannot reach it (EPS-internal) |
| **bricking class** | ⭐ cal-only | 🛑 cave | ⭐ none |

---

# 8. WHERE F7 AND "TAP RIPPLE/LEVEL" ARE DEFINED

Both are named in V291's and V292's **REVERT IF** clause (*"the 6–9 Hz strong-turn ripple returns
(F7 ≥ 2/100 s or tap ripple/level ≥ 0.25 in loaded turns)"*). Their definitions are **not** in that
clause; they are inherited from V281's pre-registration.

## 8.1 **F7** — the 7 Hz strong-turn episode family

**First defined in** `rlog-tools/studies/osc-highangle/HIGHANGLE-V278R3-2026-09-02.md`, section
**"Two families, then:"**:

> *"**F7 — the 7.0–7.6 Hz stutter (10 of 13 episodes, 22 s).** Command railed or near-railed (idx
> 112–238), driver torque 1170–1370 raw = WELL BELOW the cliff (taper 254, full authority), T rides at
> `|T| ≈ 700–1300` with a ±400–500 ripple at the same 7 Hz, coherence with rate 1.00, T leads rate by
> ~80°, angle swing 0.8–2.1°."*

Its **sibling** in the same section is **F2**, a 2.3–2.9 Hz sway on the override cliff, present on stock —
**F2 is not new to rev 3 and is not the stutter.**

**The detector**, from the same document's section *"Episodes, r31"* and from the pre-registration:
- **2–8 Hz rate envelope > 103 wire** (= 2.5 × the engaged low-angle p95), **duration ≥ 1 s**;
- gated to **`|angle| ≥ 30°`**, lateral engaged;
- classified F7 when **`f_dom ≥ 6 Hz`**.

**The threshold** is set in `rlog-tools/studies/osc-highangle/PREREG-V281-READ.md`, prediction row **(a)**:

> *"(a) F7 episodes per 100 s of high-angle engaged time (fdom ≥ 6 Hz, |angle| ≥ 30°, fixed threshold
> 103) … V280 measured 8.1 / 4.3 / 6.8 (pooled 6.3) → **V281 predicted ≤ 2**."*

**Scripts:** `rlog-tools/studies/osc-highangle/strongturn_r34.py`, `strongturn_r32_r33.py` (*"fixed
detector threshold 103 wire; same edges"*), `highangle_stutter.py`, `strongturn_r35.py`.
🛑 The prereg's own rule: **"Do not move a threshold after the log lands."**

**Measured values:** r31 9.8 · r32 8.1 · r33 4.3 · r34 6.8 · **r35 (V281 rev 3) 0.0** per 100 s.

## 8.2 **"tap ripple/level"** — the 6–8.5 Hz torque ripple, normalised

**Defined in** `PREREG-V281-READ.md`, prediction row **(b)**:

> *"(b) tap T 6–8.5 Hz ripple ÷ level, in-episode / in idx ≥ 68 frames with the wheel moving … V280
> measured 0.42–0.99 (median 0.55) → V281 predicted **≤ 0.25 median**."*

"Tap" is the **CAN-427 delivered-torque tap** introduced at V279/V280: field `((b0&3)<<8)|b1`,
`T = ±(field & 0x1FF) << 3`, i.e. `(sign(T)<<9) | (|T|>>3)` with **8 counts per LSB** and **bit 9 the
sign** — the LKAS lane's own output `gp-0x6b38`, at 50 Hz.
[EVIDENCE — `PREREG-V281-READ.md` header; `BUILD-LINEAGE.md` §V279 and §V280; the decoder correction in
`HANDOFF-2026-09-02-v278r3-flew-and-v280.md` §*"Two instrument corrections"*]

**The same statistic appears one build earlier** in `PREREG-V280-READ.md` as
*"T 6–8.5 Hz ripple ÷ level in high-angle turns ≤ 0.25 (rev 3 0.55–0.70)"* — **so 0.25 is V280's
threshold, carried forward unchanged into V281, V291 and V292.**

**Measured values:** V278 rev 3 in-episode 0.55–0.70 · V280 rev 2 median 0.55 (0.42–0.99) ·
**V281 rev 3 / r35: 0.21 median, p90 0.42** — *"prereg (b) ≤ 0.25 **PASS at the edge**."*
[`rlog-tools/studies/osc-highangle/HIGHANGLE-r35-V281R3-2026-09-03.md`]

⚠ **Note for anyone scoring a V292 drive:** the ≤ 0.25 threshold was **passed at the edge** on the base
build (0.21 against 0.25). It is a **tight** revert criterion, and the V292 replay predicts the ripple at
**×1.03 pooled with a ×1.10 worst fit** — i.e. a predicted 0.22 against a 0.25 trip. **The criterion and
the prediction are ~13 % apart.**

---

# 9. OPEN ITEMS THIS GROUNDING SURFACED (reports, not recommendations)

1. **κ, the effective r24 arm, is disputed three ways** (0.45 / 0.10–0.20 / 1.45; wire 2353 vs cal 5244)
   and every 7 Hz and 20 Hz number scales with it. **Two independent wire measurements of the same arm
   differ ×1.6 and are unreconciled** (`DESIGN-V291-FBLP` Addendum D2.3).
2. **10–14 Hz is unidentified in every stratum** (coherence 0.28–0.50). Any candidate whose corner lands
   there — C10 at 9.94 Hz and C12 at 11.94 Hz both do — **is being scored on a fit, not a measurement.**
3. **`gp-0x6806`'s state while engaged** is a live premise behind the sp = 3 clause (a ±102 deadband on
   `y` would zero sp = 3 on every build). The record's V103/V104 evidence says it is 1 while engaged;
   it is marked **BELIEF**.
4. **The outer loop's phase margin against this EPS has never been measured**, in any mode. Every Class A
   and Class C argument about the outer loop is therefore modelled.
5. **The true LAF estimates disagree ×4** (≈3.3 by invariance vs 12–15 by FF balance). A torque-mode
   firmware makes that number load-bearing, because the feedforward becomes the whole controller at DC.
6. **`0xC61C0/C2/C4` still has no lineage entry** despite 12 live readers across 249 images — owed before
   the next authority change.
7. **The IMU is still the top missing instrument** (road vs rack vs motor).

---

*Written by agent `arc` for orchestrator `main`, 2026-09-13. Study/analysis only. No image, `.rwd` or
build script was created; nothing was flashed; no CAN or UDS message was sent.*
