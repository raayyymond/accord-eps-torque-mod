# BUILD LINEAGE — Part 6: the per-build entries from V293 onward

🛑 **This is a CONTINUATION of [`docs/BUILD-LINEAGE.md`](BUILD-LINEAGE.md), which is the ENTRY POINT.**
Split out at the 2026-09-13 close-out, when the entry file crossed **233 KB** against the 256 KB `Read`
cap (past it a file loads with its tail **silently truncated and no warning**). The RULES, the struck
levers, the ledger corrections, **Part 2 (code caves / GATE 1 / GATE 2)**, Part 3 and Part 4 all stay in
the entry file and are **not** repeated here.

⚠ **This file is `PART6`, not `PART5`.** `docs/BUILD-LINEAGE-PART5-V122-ONWARD-MEASURED.md` already
exists and is a different artifact — a generated V122 → V210 address index with no reasoning in it. The
two must never be confused.

**V291 and V292 keep their entries in the entry file** (V292's with its FLEW verdict). **V293 has a
one-line stub there so `grep V293` lands**, and its full entry is below. Every later build's entry goes
here.

🛑 **Same rule as everywhere else: grep by ADDRESS across BOTH files plus
[`BUILD-LINEAGE-PART1-LEVER-INDEX.md`](BUILD-LINEAGE-PART1-LEVER-INDEX.md) before proposing any
calibration edit, and state the cell's on-car result. FALSIFIED ≠ INERT-BY-MODE ≠ never-tried.**

---

### V293 — TORQUE MODE: the LKAS rate feedback clamped to zero, D killed twice over, the forward path re-levelled  (2026-09-13, **✈ FLEW 2026-09-13 on route `75604b0a432fdc89_00000070--717f5a7866` — see the FLIGHT paragraph right below this heading. Pre-flight status: CLEARED AS THE FLIGHT CANDIDATE OVER ONE DISSENT (B2 as written). A/C/D PASS; B1, B3, B4, B5, B7 PASS, B8 reported; B2 and B6 FAIL AS WRITTEN and both are adjudicated. V282 is the fallback; the fork preset is MANDATORY; the first drive is an IDENTIFICATION drive; the low-speed 1–4 Hz signature is the first revert trigger. The decision to fly is the operator's. Nothing is flashed.**)

> ✈ **FLEW 2026-09-13, route 70 (19 segments, 858 s laterally engaged, fork `Dom` `4247cb09e`, rev-1 toggle
> config confirmed in `initData` and by the 100 Hz Kp read 0.3000). THE OPERATOR'S SCORE, verbatim:** *"I did not
> experience any classic grinding or stuttering."* / *"steering felt ratchety, like the wheel did not move smoothly
> but only snapped between angles rather than smoothly moving between them"* / *"Sometimes steering felt loose and
> then sometimes there was oversteer and other times on hard transients, it would overshoot then correct slightly."*
> **Bands (the instrument, `V293-FLIGHT-READ-r70-2026-09-13.txt`):** the edit-live identity HOLDS (|427 tap| vs the
> image surface R² 0.986, resid 22 counts, sign(T) = +sign(cmd)) — the EPS rate loop is dead on the wire; 18–22 Hz
> ring present in **1.1 %** of windows (9.8–20.9 % on every reference), present-window amplitude ×0.43 of V282's
> (gate ≤ 0.40 — a marginal miss of its own clause, not a null: the terminal null sentence's antecedent "unchanged"
> is NOT met, so the in-loop class is NOT closed by this drive; the drive-controlled 18–22 Hz reads 1.88 = ×0.55 of
> r6c, and the excess moved DOWN to 9–17 Hz, unexplained); F7 strong-turn ripple **0.00**/100 s; 6–8.5 Hz tap ripple
> ×0.10; 5–9 Hz ×1.6–1.9 broadband (predicted); 13–17 Hz ×1.03; a 10.55 Hz +3.8 dB line not gated. **One REVERT
> trigger fired — the OUTER LOOP:** a genuine 1.2–1.8 Hz peak in command and angle (angle 3.55° at 0–5 m/s, 2.5×
> the worst reference; 6.5–11.8 dB prominence below 20 m/s where no reference has any), which the pre-registration
> assigns to the FORK TUNE, not the firmware. **The plant left behind is a SPRING + Coulomb friction, not a rate
> servo** (`V293-PLANT-IDENT-2026-09-13.md`): torque per degree 0.0079/0.0113/0.0154 u at 12.5/18.5/28.5 m/s, soft
> below 8; F 0.010–0.012 u; the fork's model was wrong twice (no friction, one LAF at all speeds — measured 3.2 → 6.4
> with speed, ×2.8 with amplitude); the ratchet is MEASURED (dwell-then-jump 6–39× V282 at th 0.25, the command 3×
> smoother); the low-speed loop had PM −11° from the hard-coded low-speed factor. **Authority vs stock, re-verified
> from the three images:** peak ×6.17 (2461 vs 399 lane counts), every authority cell exactly ×6.000, median ×4.35 —
> nothing changed. **Disposition: V293 STAYS IN THE CAR; the fix is the FORK — plant tables re-identified in code
> (Dom `66cf4454a`) + the rev-2 toggle config (`toggle-config_V293_torque_mode_r2.json`: plant FF on, friction 0.011,
> LAF 14, Kp 0.85, Ki 0.30, offset off).** Handoff `HANDOFF-2026-09-13-v293-flew-plant-is-a-spring.md`.

**Class — V279 rev 2's STRUCTURE (2026-09-02, built, never flown) REBASED ONTO V282: the LKAS lane stops
being a rate regulator and becomes a linear TORQUE MAP, `T = f(cmd)·taper`, with no rate feedback and no
derivative term.** It is **not a new lever** — V279 built the same three mechanisms on a V268 base. What
is new is **(i) the base** (V282's ×6 map, its clamps, its 0x14A cave and its `0x1AB` torque tap all come
along), **(ii) the r24 dose**, and **(iii) the StarPilot preset that flies it.** Against the recent arc:
V288 worked the **reference** side (setpoint pre-filter) and was null on the grinding; V289 put a **notch
on the loop output** and the ring relocated; V291/V292 **lowered the loop's feedback bandwidth** and the
ring did not fall while the 7 Hz mode came back. **V293 removes the loop instead of shaping it** — the
first build since V279 to change *what the loop is* rather than *how it is tuned*, and the first ever to
do so on a base the operator has driven and accepted.

**base** V282 (`_v282_…FEEDBACK46080.TORQUE.TAP_plain_image.bin`) · **CAL-ONLY, not one code byte** ·
**image** `f75e77cf0ba9d93b5302196877e59c6a41deae4983afc09ade99c5b766e1db17` · **rwd**
`ac4723865378ff376086174bbb82fcabf07c435fae5bf5706a6ef83caa6e71ba`
(`39990-TVA,A160-V293-V282BASE-TORQUEMODE.FB0-KD0.BANK.ALL+DCLAMP0-KP.FLAT.120.ALL-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP-0x13000-0x100000.rwd`,
**exactly one V293 rwd on disk**) · **242 assertions** (census **64 substantive / 172 vacuous / 6
tautological** post-`scriptfix`; 63/172/6 at write time, and adversary C found the substantive count
**overstated by 23**) · **16/16 mutations caught** (13/13 at write time) · **378 diff bytes over 6 CRC blocks, ZERO of them below `0xC0000`** — the cal-only claim is a
byte fact, not a docstring claim · script
`analysis-2020accord/builds/v108_plus/build_v293_tva.py` (agent `builder293`; presets + `--grid`, a
zero-edit control, `KP_SCOPE = all`), sha256 **`8ffb29a9…` at write time**; agent `scriptfix` then applied
adversary C's four hygiene fixes (the docstring's 87 % → 14.5 %, the Kd *"128 on 8 / 64 on 20"* line, the
D-clamp integer into the tag, a full-tuple assertion), so **the script hash moved and the IMAGE hash did
not — re-hashed at close-out: image still `f75e77cf…`, script now `27d6ff76…`.** 🛑 **Quote the script
hash with its moment; the artifact is the invariant** · the builder's dry run and adversary C's
**independent rebuild from the V282 image plus the pre-registration's edit list land on the SAME two
hashes** ·
**page** https://claude.ai/code/artifact/6751b3ba-2098-4c74-894b-b74741ff4565 (v2 — A/C/D1 verdicts, the
taper split, the authority callout) ·
design `docs/specs/design/DESIGN-V293-TORQUE-MODE-2026-09-13.md` · prereg
`docs/review/ADVERSARIAL-V293-PREREG-2026-09-13.md` (written before the image existed) · trace
`docs/traces/TRACE-2026-09-13-lkas-pid-tracked-quantity.md` · arc grounding
`docs/research/ARC-GROUNDING-TORQUE-MODE-AND-ACCEL-TRACKING-2026-09-13.md` · fork side
`docs/research/FORK-LATERAL-DESIGN-FOR-TORQUE-MODE-AND-RATE-TARGET-2026-09-13.md` and the operator's card
`docs/guides/TORQUE-MODE-TOGGLE-CHECKLIST-2026-09-13.md`.

#### The cells — base values read from the record, not from the build script

| cell | STOCK | V282 (the base) | **V293** | what it physically is |
|---|---|---|---|---|
| `0xC62E6` | 7680 (30×256) | **46080** | **0** | the LKAS rate-PID's **feedback saturation clamp**, applied to the two-sample sum `r26` at `0x28FA6–0x28FBE` before `sub r26,r16` at `0x29D78`. Zero forces the rate-feedback operand to **exactly 0 on all three branches** ⇒ `E = 32·setpoint` unconditionally. **The loop is open at every frequency.** Three accessors image-wide (`0x28F96`, `0x28F9C`, `0x28FB8`), all `ld.hu` (zero-extend, so a written 0 reads as 0 — no sign trap), **zero writers**. V279 rev 2 already flew this edit past five adversaries on a V268 base, and the whole span `0x28F7C–0x28FC8` plus `0x29D78` is **byte-identical between V268 and V282**, so that proof transfers |
| Kd bank `0xCB7D4` (all 28 records; live slot 7 = `0xE511C`, X 0/11/22/32, Y 128×4) | 128 | **128** | **0** | the rate PID's **derivative schedule**. With the feedback dead, `dE = 32·d(setpoint)` is a pure **setpoint kick**: one demand-index count near the top of the map is `dE = 32·344/80 = 137`, and at Kd 128 that is `D = (137·128)>>3 = 2192` counts — **87 % of the delivered peak from a single command step.** Zeroing makes `D = (dE·0)>>3 = 0` exactly, at every amplitude, with no clamp involved. **Never edited on any flown build** |
| `0xC61B6` | 10240 | **10240** | **0** | the **D clamp**, the same three-branch `cmp/ble/mov/subr/cmp/bge/ld.hu/subr` idiom as the fb clamp, so a zero bound forces `D` to exactly 0 on every branch. **7 readers** image-wide (4 live in the clamp block at `0x29EE8/EF2/EF8/F02`, 3 inside the dead twin island), **0 writers**. This makes D zero **twice over, by two independent cells** — which is what the pre-registration's A1 clause requires ("D ≢ 0 for any ΔE with EITHER cell alone" is a FAIL). **BYTE-STOCK from stock through V292** |
| Kp bank `0xCB994`, **all 28 records** | 248…717 rising | **flat per slot: 205 / 248 / 266 / 307** (V281 rev 3 flattened each record to its OWN Y[0]; the live slot 7 is **248**) | **120 flat, every record** | the **proportional schedule**. With `fb ≡ 0`, `P = (32·Y·Kp)>>8`; on V282's linear map `Y = 4.3·idx → 1032`, so Kp 120 gives `P = 15480` at idx 240, clipping to the **same 15360 P-rail V282 already has**, and linear below it. **Why 120 and not 248:** at fb = 0 V282's Kp 248 rails from **idx 116**, i.e. it would deliver PEAK TORQUE from 48 % of demand upward — a ×2.07 over-gain on the bottom half of the range. **Why all 28 records and not just slot 7:** the fb clamp is **ONE GLOBAL cell** while Kp is **per-slot**, so a selector that is ever not 7 must land on the same surface, not on zero feedback at a 205–307 Kp railing at 44–58 % of demand. (The selector was MEASURED **7** on the V276 wire and the record says it maxes at 9, so this is a **contingency, not a live defect** — it is bought for ~45 payload bytes.) 🛑 **Kp 119 was rejected by the prereg's own A2 clause**: it delivers 2504, one count below V282's rail, and A2 FAILs if the rail differs by one count or more. 119 stays on the builder's grid as the control showing the **clamp** pins the rail, not the arithmetic |
| `0xC6446` | 512 | **5244** (V84's Lever B) | **2048** | the **r24 ENGAGED rate-lane arm** — r24 is a lag-4 backward difference of torsion-bar torque, unit-weight sibling of the LKAS lane at `gp-0x6b94` ⇒ **1 : 1 at the motor**. On the wire it is a pure **PUMP at 3–7 Hz** (∠+170°) and a near-pure **DAMPER at 18–22 Hz** (∠+9…+15°, 73–86 % of the electronic 20 Hz damping). ⭐ **2048 is not an arbitrary rung: `0xC6440` = 2048 is the DISENGAGED arm, and it reads 2048 on EVERY image including STOCK** — so **V293 sets the engaged arm EQUAL to the disengaged one**, which is a far more interpretable statement than "a number between 512 and 5244". See the dose reasoning below |

#### The byte census, re-derived from the BUILT image by this writer, not taken from the builder's report

**378 differing bytes vs V282 in 183 runs, over 6 CRC blocks** — and it reconciles exactly:

| region | bytes | what |
|---|---|---|
| `0xC62E7` | 1 | the fb clamp's high byte (46080 → 0) |
| `0xC61B7` | 1 | the D clamp's high byte (10240 → 0) |
| `0xC6446–47` | 2 | the r24 arm (5244 → 2048) |
| `0xE4xxx`–`0xE8xxx` | **112** | the Kd bank — 28 records × 4 knots |
| `0xE4xxx`–`0xE8xxx` | **240** | the Kp bank — 28 records × knots, every one 120 |
| `0xC6FFC`, `0xE4FFC`, `0xE5FFC`, `0xE6FFC`, `0xE7FFC`, `0xE8FFC` | **22** | the six CRC trailers |

1 + 1 + 2 + 112 + 240 = **356 payload bytes**, + 22 trailer bytes = **378**. ⚠ **Two of the six trailers
differ in only 3 of their 4 bytes** (`0xE6FFC` `6fe05911` → `df1459ab`, `0xE7FFC` `af54b962` → `1fa0b9d8`),
which is why 6 blocks carry 22 and not 24 bytes — **a run-length scan that requires a full 4-byte trailer
run finds only FOUR blocks and undercounts.** Cells read back from the built image: `0xC62E6` = **0**,
`0xC61B6` = **0**, `0xC6446` = **2048**; Kd slot-7 record `0xE511C` Y = **0,0,0** (V282: 128,128,128);
Kp slot-7 record `0xE5378` Y = **120,120,120,120** (V282: 248,248,248,248), X knots unchanged.

Everything else **byte-identical to V282**: the ×6 map (slot 7 ceiling 1032), the P/sum clamps 15360, the
output clamps 3072, the forward gain 5346, `Ki = 0` (`0xC63E6`), the fb lag pole 923/1560 (its **state
keeps running** — only its clamped output is zero), the output lag 992/507, the override taper, the idx
clamps 240, the 0x14A cave and its rungs **b4–b7** (🛑 **b3 stays V282's ALIASED bit — it is NOT V292's
fb-state rung**), and the `0x1AB` tap of `gp-0x6b38` (= the delivered lane torque `T`). Only the CRC
trailers of the blocks owning the touched cells change.

#### The dose reasoning for `0xC6446` = 2048 — **the orchestrator's ruling, against the design agent's recommendation**

`DESIGN-V293-TORQUE-MODE` recommends **4451** (−15.1 %): with the servo gone the 7.3 Hz gate collapses to
`1.19·(arm/5244)` and 4451 restores it to exactly **1.010**, the criterion. **The orchestrator took 2048
instead, before any image existed**, on three grounds:

1. **A criterion-exact arm carries no margin against the operator's loudest symptom.** The same model
   under-predicted V292's measured 5–9 Hz cost **three-fold** (predicted ×1.03–1.10; the wire read
   ×2.9–4.3 route-normalised, ×1.6–2.2 raw), and that band is the one the operator has just called worse.
2. **2048 is the record's own priced lever** — *"7.3 Hz ring 0.98 → 0.48, no margin or authority cost"*
   (`GRINDING-DEEP-ANALYSIS-2026-09-03` §2–3). It is not a new number.
3. ⭐ **In torque mode the r24 cut is FREE at 20 Hz, and only here.** With the servo present, cutting r24
   costs 20 Hz damping (paired Δζ **−0.044 / −0.075 / −0.086** at κ 0.10 / 0.20 / 0.45 — the record's own
   finding, reproduced to four decimals). With the servo **gone**, removing r24 **RAISES** ζ (paired
   **+0.036 / +0.097 / +0.183**, on 96 / 96 / 100 % of plants). **r24's apparent 20 Hz damping was a
   partial cancellation of the servo's de-damping; delete the servo and it evaporates.** The broader
   (V282-pole-only) family's marginal 21–23 Hz pole at arm 5244 also clears below ~2622.

**BELIEF that 2048 is the better hedge** — the adversarial B surface is briefed to score 4451 and 2048
side by side, so the ruling is falsifiable rather than assumed. ⚠ The lever index's V69/V70 remark stands
and cuts the other way at the *other* end of the range: `0xC6446` = **512** (Honda stock) is **not** a
free improvement — `grind_loop_shape.py` §G's *"5244 → 512 improves both bands"* is **falsified on the
car**, because V70 at 512 put grind #1 back at creep. 2048 is between, and is the first time this cell has
been set there on any built image.

#### The delivered surface — the rail read from BOTH BUILT IMAGES

🛑 **THREE DIFFERENT NUMBERS HAVE BEEN CALLED "THE RAIL" IN THIS RECORD. THEY ARE NOT THE SAME QUANTITY,
AND ONLY ONE OF THEM IS DELIVERED.**

| number | what it actually is | use it for |
|---|---|---|
| **2461** | ⭐ **THE DELIVERED RAIL — the byte-exact steady state through the fade and the output lag, and it reads 2461 on the V293 image AND on the V282 image.** The residue is the output lag's integer fixed-point interval | **this is the one the car delivers** |
| 2462 | the **linear DC** of the same chain — what the output lag's DC gain gives before the integer fixed point settles | a linear cross-check only |
| 2505 | the **structural ceiling** — `min((15360·5346)>>15, 3072)`, the `T_ceil` convention the V279/V282/V292 docstrings print | 🛑 **NEVER quote it as delivered.** Neither build reaches it at fade 254 |

⇒ **Peak authority is ×1.000, not ×0.9992** — the ×0.9992 (2461 vs 2463) in
`DESIGN-V293-TORQUE-MODE-2026-09-13.md` §1.4 compared V293's byte-exact march against a V282 figure
computed a different way. **Both images rail at 2461** from a cold-start state of 0.

🛑 **2461 IS AN AT-REST NUMBER — condition every on-car rail read on SPEED.** ✅ **The SELECTOR question
is CLOSED** by a decompile of the built image: the taper is **ONE stage, not two** — `0x2A13x` carries
`factor = ((tapAB · tapCD) & 0xFFFF) >> 8; S = (factor·S) >> 8`, at-rest 254/256 only because **both halves
return 255 at rest** — and **`gp-0x6803` picks B × D (`0xCBBC4`)**. **The kit memory was right about D; the
tracer's C (`0xCBAE4`) reading was wrong.**

🛑 **BUT THE AXIS UNIT IS STILL OPEN, AND IT IS WORTH REAL TORQUE.** Adversary A read the C/D half's X axis
as speed and **assumed km/h — flagged as its own BELIEF** — which would derate the rail to **2151 at
10 m/s and 736 at ≥ 20 m/s.** The record's on-car tap numbers point the other way: V278 rev 3's
`T_meas/T_sim` is **0.42–0.51 at 3–9 m/s**, and the tap rails at 310 on faster routes. **Do not quote the
derated rails as established.** ⭐ **What is safe either way: the table is IDENTICAL on both builds, so the
V282 : V293 ratio holds at every speed and the trade below does not depend on resolving the axis.**
Because the output lag's floors give an **interval** of fixed points, *"the rail is identical to V282's"*
is scored on **matched trajectories** from a cold-start state of 0, not on a single number.

`T(idx)` in EPS torque counts at the CAN-427 tap, fade `m` = 254 (no driver torque). **The V293 row is the
byte-exact steady state `T_ss`; the V282 rows are the design's `T_ceil` convention** and so print 2505
where the delivered value is 2461:

| idx | 0 | 40 | 80 | 120 | 160 | 200 | 240 |
|---|---|---|---|---|---|---|---|
| **V293 `T_ss`** (Kp 120, fb ≡ 0) | 0 | 413 | 826 | 1237 | 1653 | 2067 | **2461** |
| V293 `T_ceil` (for comparison with the older docstrings) | 0 | 420 | 841 | 1260 | 1683 | 2104 | 2505 |
| V282 at fb = 0 (wheel still), `T_ceil` | 0 | 869 | 1739 | 2505 | 2505 | 2505 | 2505 |
| V282 at 10 deg/s of wheel rate, `T_ceil` | **−385** | 485 | 1355 | 2219 | 2505 | 2505 | 2505 |
| V282 at 20 deg/s of wheel rate, `T_ceil` | **−776** | 94 | 964 | 1828 | 2505 | 2505 | 2505 |

🛑 **"×1.00 of V282's authority" is true of the PEAK and of nothing else.** Three senses, and they
disagree: **peak torque ×1.000** (2461 delivered on both images) · **torque at a given command with the
wheel still ×0.48** below idx 115,
rising to ×1.00 at 240 · **torque delivered on the operator's own recorded episodes ×0.82 rms** on r39's
grinding windows and **×3.6** on loaded high-angle turns, because V282's servo has already nulled there
and V293 does not. **Sense 3 is the one he drives.** No single Kp makes all three ×1.00, because V282's
delivered torque is not a function of the command at all. The fade LERP (`0xCBBC4` slot 7) is the **only**
thing that backs a torque-mode lane off for a driver — there is no error term left to do it — and it is
the same LERP on both builds. At idx 48 V282 delivers 35 counts once the wheel reaches the asked rate and
0 at the null rate; V293 delivers ~492 counts **and keeps delivering them**, receding only as the driver's
own bar torque climbs the fade above |bar| ≈ 512. [EVIDENCE for the numbers; **BELIEF** that this feels
like V276's *"the only way to stop it is to hold the steering wheel very firmly"* — V276 also had a limit
cycle, which this does not.]

#### Predictions on record BEFORE the pass — so no adversary scores against a moving target

- **18–22 Hz wheel ring ×0.285** [0.27, 0.30] on r39's loudest windows, **×0.40** on r6c; the **on-car
  anchor** (engaged ÷ same-route disengaged on V282 routes, reciprocal) **×0.24–0.29**; ring-down
  169 → 43 ms; r6c's 12–17 Hz episodes ×0.80. ζ(20 Hz) 0.030 → **0.157–0.325** by κ.
  ✅ **RESOLVED by `advB3b`: the anchor is an ESTIMATE, not a lower bound.** The r24 lane is **SWITCHED**
  to `0xC6440` when disengaged, **not gated off** — the selector reads
  `g = 1024 if gp-0x671d else 0xC6446 if lateral else 0xC6440` (`0x3ABFE` / `0x3AC08` / `0x3AC12`) — so
  **on V293 the r24 lane is BIT-IDENTICAL engaged and disengaged.** ⚠ **Three residuals keep it an
  estimate rather than a measurement:** V293 still injects `f(cmd)` (the replay sizes the forced ring at
  **3.49** against V282's **10.30** counts); the disengaged reference is **mostly stationary**; and the
  **r26 base-assist arm `0xC6444` also moves with the `0x3AA96` gate** — unresolved.
  🛑 **The same predictor's V292 prediction (×0.535) FAILED on the wire (the loop's contribution went UP
  ×1.20–2.00). The failure is the METHOD's** — the design agent reproduced the published V292 number with
  its own implementation, so it is not a coding difference. **This is the largest single risk on the page.**
- **5–9 Hz wheel band on loaded high-angle windows ×2.10 (r39) / ×1.45 (r35)**, consistent with
  `|1 + L_V282(7.3 Hz)| = 2.04` — the servo's disturbance rejection removed. Stall-class P-rail duty
  0.66 → **0.00**; ripple/level 0.705 → 0.078 **but the denominator grows ×3.6**, so the ABSOLUTE
  6–8.5 Hz tap ripple must be scored too (×0.52 r39 / ×3.2 r35).
- **Outer loop is NOT the risk.** At the operator's live tune (LAF 6.0 / Kp 0.9 / Ki 0.30) V293's margins
  are indistinguishable from V282's: Ms 1.09–1.38 vs 1.04–1.35, PM 64° vs 66° at 28.5 m/s. **No cell in
  the 6 × 3 × 3 grid reproduces V276's 2–4 Hz signature that V282 does not also reproduce.** V276's shape
  returns not as a margin failure but as a **feedforward mis-scaling ×3.17 at 5 m/s** — hence the fork
  preset below.
- **Edit-live control:** regress `|427 tap|` on `f(cmd)·fade` — R² **−4.82 (V282) → +0.92 (V293)**,
  residual 349 → 47 counts; `0x14A` **b7 duty 0.996 → 0.808** is the mover, **b4 (sign r24)** the negative
  control; b6 is **not** pre-registered.
- ⭐ **The lever inside the lever, and the operator is entitled to it before he decides:** sweeping
  `0xC62E6` from 46080 to 0 with Kp 120 / Kd 0 held moves the wheel ring only **×0.299 → ×0.272** —
  **~90 % of the grinding benefit is Kd = 0 and the Kp re-level, not the clamp.** The clamp is what
  changes the delivered **quantity** (the session's other goal) and is nearly free on the ring.
- 🛑 **No intermediate dose exists.** `0xC62E6` is a **clamp, not a gain**: a small non-zero value is not
  "less feedback", it is a **Coulomb relay on sign(wheel rate)**. Swept byte-exact at 256/512/1024/2048/
  4096, every value is worse than zero on every column, and with the command frozen the relay **ADDS**
  18–22 Hz (×1.005–1.079) and 5–9 Hz (×1.02–1.10) motion. **The cell is effectively binary and 0 is the
  right end.**

#### READ IT BY — the first drive is an IDENTIFICATION drive, not a symptom drive

1. **Identification first** (fork memo §3.5): hands-off, laterally engaged, **≥ 400 frame pairs per |τ|
   bucket in ≥ 4 buckets to |τ| 0.5, both signs** — then fit LAF by instrumental variables against
   `modelV2.action.desiredCurvature·v²`. **Do not identify LAF from `torqued`**: its buckets do not fill on
   this car and its estimate is a long-filter TLS through central buckets on a plant whose gain has just
   changed discontinuously. Then the tune, then symptom scoring.
2. **The edit-live identity, on every engaged frame:** `T_tap = f(cmd)·taper`, with
   `sign(T) = −sign(cmd)` agreement ≈ 1.00 proving the feedback is dead. **T saturating below the map top
   means the map is not the live source.**
3. **The ring by the DRIVE-CONTROLLED measure the V292 flight read established** — engaged 18–22 Hz
   amplitude ÷ the **SAME route's lateral-disengaged** amplitude (V282 reads **3.4–3.9** on r6c/r39/r35;
   V292 read 4.1–6.8), plus present-window amplitude vs r6c (V282 ×1.0–1.05, V292 ×1.07–1.38) and the
   14–15 Hz line excess in dB. 🛑 **NOT the driven half-peak decay** — the V292 read showed it is confounded.
4. F7 and tap ripple/level at |angle| ≥ 30°; a 1–4 Hz line in command **and** angle; b4–b7 duties as the
   r24 control.

**THE SENTENCE A NULL LICENSES** (write it down before the drive, per the design law):
> *If the 18–22 Hz ring's amplitude and ring-down are unchanged with the LKAS loop open on every frame —
> the edit-live identity holding — then the 20 Hz object is not the LKAS loop's, and the whole in-loop
> class, V38 → V293, is closed.*

**REVERT IF:** grinding unchanged (**the operator's word, not a band**) · the 6–9 Hz ripple returns
(F7 ≥ 2/100 s **or** ripple/level ≥ 0.25) · **a 1–4 Hz oscillation of command and angle** — the V276
signature, i.e. the outer loop; the fix is the fork preset, not the firmware, **but the drive stops** · a
10–18 Hz line · a darty or loose feel · a one-sided pull at rest · any EME or DTC.
🛑 **It licenses no claim that the grinding or the stutter is fixed. The operator scores the symptom.**

#### The fork side — a TOGGLE CONFIG, no fork code, and the mismatch is not symmetric

**`analysis-2020accord/reference/toggle-config_V293_torque_mode.json`** — a Galaxy toggle backup (a DELTA of
10 keys) restored through Galaxy → toggle backup → Restore, then restart openpilot; the revert file
`toggle-config_V282_rate_servo_REVERT.json` sits beside it; both are written and round-trip checked by
`tools/make_galaxy_toggle_config.py`. The card is `docs/guides/TORQUE-MODE-TOGGLE-CHECKLIST-2026-09-13.md`.

🛑 **Three mechanisms in one day; this is the one the operator asked for.** It shipped first as a param
(`AccordEpsTorqueMode` plus four sliders), was reworked onto Testing Ground 9 the same afternoon, and the
operator rejected that too — *"way too complicated for what should just be a toggle config file"* — so fork
commit `3d1a3d0c7` was force-removed. **Dom `4247cb09e` carries nothing torque-mode-specific**;
`starpilotLateralState.epsTorqueMode @8` never shipped. The config: `AccordRatePlantFF` **0** (the switch),
`SteerKP` **0.3**, `AccordTorqueKi` **0.15**, `SteerFriction` **0.00**, `SteerLatAccel` 6.0, and pins
(`ForceAutoTuneOff` 1, `ForceAutoTune` 0, `AdvancedLateralTune` 1, `KeepLearnedLatAccelOffset` 1,
`AccordTurnFFTaper` 0) that were already his values. A delta because the restore applies only the keys
present and a full backup would drag `SteerRatio` back to 16.33 (route 6f: 16.88).

> **The one rule: the torque config may be live only while a torque-map EPS image (V293 or later) is in
> the ECU.** Going TO V293: **flash first, restore the config second, restart.** Reverting: **restore the
> REVERT config first, restart, flash second.**

| state | consequence |
|---|---|
| torque config + rate-servo image (V282/V292/stock) | 🛑 **OVER-DELIVERY** — feedforward **×2.55** at 15 m/s / 0.9 m/s², measured from the fork code, inside the record's ×2.4–4.3 band. **Nothing downstream catches it**: `opendbc/safety/modes/honda.h` applies no magnitude, rate, driver-torque or RT-window limit to `0xE4`. **Never create this row, not even for the drive to the flashing spot** |
| installed tune + torque-map image (V293) | **starvation on a held curve** (V293 delivers ~½ per command below idx 116 and the integrator carries the shortfall) and **×3.17 the turn-in rate at 5 m/s**. Recoverable, not safe. This is where a Safe Mode trip lands you with V293 in the ECU |

**Safe Mode DOES reset this config** — all ten keys are in `SAFE_MODE_MANAGED_KEYS` (`starpilot/common/safe_mode.py`), so a Safe Mode trip puts `AccordRatePlantFF` back to 1 and the tune back to its defaults. With V293 in the ECU that is the installed-tune-on-a-torque-map state (starved on a held curve, over-rated on turn-in; recoverable, not safe); on a rate-servo image it is the correct state. Either way it is a route OUT of the torque config, never into it.

⭐ **Attribution from the wire, no code flag** (`v293_flight_read.py` §0, negative-controlled on r6f):
`initData.params` key by key (an `Accord*` key at its default is ABSENT — `AccordRatePlantFF` absent means
ON); **`torqueState.p / torqueState.error` = `SteerKP` at 100 Hz, exactly** (the fork logs `error_with_lsf`
and feeds the same number to the PID; r6f reads 0.9000 over 42,905 frames, IQR [0.9000, 0.9000]); and the
median `f/D` ≥ 0.75 branch read. The `customReserved9` Testing Ground heartbeat is informational only.

🛑🛑 **A STANDING FORK DEFECT, FOUND BY B6 AND LIVE ON V282 TODAY — not a V293 problem.** StarPilot feeds
**`error_with_lsf`** (= `error·(1 + lsf/kp)`) into `get_friction`, where upstream openpilot feeds the
**raw** error. The friction compensator's gain is therefore **`(friction/0.30)·(1 + lsf/kp)`**:
**×17.9 at Kp 0.3 and 5 m/s** — and **×6.6 at the operator's LIVE Kp 0.9, on the car right now.**
⭐ **A lower Kp makes it WORSE, not safer** (the loop gain is minimised near Kp ≈ 1.0), which inverts the
preset's own rationale for Kp 0.3. **Repair: preset friction 0.01 → 0.00** ⇒ PM 22.8° → **42.2°**,
Ms 4.32 → **2.06**, gain margin **×1.40**.

Provisional first-drive tune — **the four Galaxy sliders, set by the config** and re-tunable between drives
(restore the config, then adjust): LAF **6.0** (🛑 carried over so the first flight is not also a gain change
— **not an identification**; on a torque actuator the DC gain is finite and should come out *lower*),
friction **0.00 (B6's repair, applied)**, Kp **0.3** (🛑 **its stated rationale is falsified by B6 — see
above**; the rule is friction 0 AND Kp ≤ 1.0, both), Ki **0.15**. **Net command at 15 m/s / 0.9 m/s² comes out
×0.929 of today's** at those values — the bigger feedforward is more than paid for by the Kp, Ki and friction
cuts, but that is **a coincidence at one operating point, not a safety margin.** `SteerRatio` stays **16.88**
through identification; with the rate-plant branch off its second consumer is gone so the level's
sensitivity roughly **halves** [BELIEF, from the structure].

#### 🛑 ADVERSARIAL PASS — COMPLETE. **CLEARED OVER ONE DISSENT.**

> **VERDICT: V293 is CLEARED as the flight candidate over ONE DISSENT (B2 as written), with V282 the
> fallback, the fork TOGGLE CONFIG (`toggle-config_V293_torque_mode.json`: rate-plant FF OFF /
> LAF 6.0 / friction 0.00 / Kp 0.3 / Ki 0.15 — existing sliders, no fork code) MANDATORY, the first drive an IDENTIFICATION drive, and the low-speed 1–4 Hz
> signature the first revert trigger. The decision to fly is the operator's. Nothing here licenses any
> claim that the grinding or the stutter is fixed — the operator scores the symptom; the pre-registered
> read and the terminal null sentence stand.**

**`advA3` PASS (A1–A4) · `advC3` PASS (C1–C5) · `advD3` PASS (D1–D5) · `advB3` / `advB3b`: B1, B3, B4, B5,
B7 PASS, B8 reported, 🛑 B2 and B6 FAIL AS WRITTEN — both adjudicated below.** Full table:
`docs/review/ADVERSARIAL-V293-PREREG-2026-09-13.md`.

- **A — ARITHMETIC: PASS on A1–A4.** The clamp block **simulated from its own decoded bytes over 4,023
  int32 states gives ZERO non-zero operands** — and the capable-null control is real: **V282 at 46080
  gives 4,012 on the same sweep.** `D ≡ 0` by **each cell alone**. The `0x2A0C6` damper mode is
  **unreachable by three methods**, including **zero LE32 hits of `0xFEDF17F6`** — which closes the
  tracer's residual on it. **Rail 2461 = 2461** on matched cold-start trajectories; **P first rails at
  idx 239**; linear fit **10.336·idx − 1.89** (max residual 2.19 counts, accounted for); worst product
  ×495 inside int32; the code region byte-identical; **b3 is V282's aliased `ld.w gp-0x3680`**; the tap
  (`gp-0x6b38`) under-reads by 0–7 counts.
- 🛑🛑 **A's CARRIED FINDING — NOT GATED, AND IT CHANGES HOW THIS BUILD MUST BE DESCRIBED.**
  **V293's sub-rail slope is 10.34 counts per demand index against V282's 21.35 at `fb = 0`.** Below
  idx 116 **V293 delivers 0.47–0.49 of V282's STALLED-WHEEL torque** (at idx 58: **598 vs 1236**), meeting
  it only at idx 239–240. In A's own words: **"the peak is identical and needs twice the demand to
  reach."** ⇒ 🛑 **DO NOT WRITE "AUTHORITY UNCHANGED" ANYWHERE ABOUT V293**, and **a page that shows only
  the rail is misleading** — the sub-rail surface is half of V282's against a wheel that is not moving,
  which is precisely the condition the driver feels at a stall.
- **C — BUILD AUDIT: PASS.** The **independent rebuild from the V282 image plus the pre-registration's
  edit list is byte-identical** and lands on both reported hashes. Non-blocking findings, each recorded
  because they are exactly the class this audit exists to catch: the **substantive assertion census (63)
  is overstated by 23**; **seven single-knot mutations are invisible to the assertions** (a knot could
  move and no assertion would fire); **the tag does not encode the D-clamp integer**, so two builds
  differing only in `0xC61B6` would carry the same tag; and two docstring errors. 🛑 **None of the four is
  in the artifact** — the image is what the pre-registration specifies.
- **D — INTERLOCKS: D1 PASS, and the number is what makes it one.** This was the clause most likely to
  return do-not-flash, because a torque-mode lane holds full commanded torque however fast the wheel
  already moves, so **dwell at the rail rises even though the peak does not.** The census found the
  mechanism and then bounded it: the **soft-EME integrator `gp-0x3570` in the shaper `FUN_00042af8`**
  arms **SM2 at `|I>>15| ≥ 15361`**, integrating the excess of `|cmd|` over
  `max(corridor, IIR, boost floor 5120)`. ⭐ **The LKAS lane's rail (≈ 2481 at the shaper's input) cannot
  reach the bound at all.** The only band V293 newly opens is **`5120 < |cmd| ≤ 5325`, and it needs
  75 ms of CONTINUOUS residency**; SM2/SM3 self-clear; the energy budget `FUN_0007b022` is unreachable;
  every interlock cal is byte-identical to V282. ⚠ **D5's wording is FALSE but INERT** — the dead twin
  island *does* read `0xC61B6`; it is uncalled, so nothing follows.
- 🛑🛑 **B6 — THE OUTER LOOP: INTERIM FAIL ON THE BUILD + PRESET PAIR AS SHIPPED. THE FIRMWARE IS NOT THE
  DEFECT; THE FORK IS.** At **5 m/s, κ 1.00, τ 0.20 s the outer loop's phase margin is 22.8°**
  (Ms 4.32, crossover 0.82 Hz). **Cause:** StarPilot feeds **`error_with_lsf`** (= `error·(1 + lsf/kp)`)
  into `get_friction`, where upstream openpilot feeds the **raw** error — so the friction compensator's
  gain is **`(friction/0.30)·(1 + lsf/kp)`**, i.e. **×17.9 at Kp 0.3 and 5 m/s.**
  ⭐ **AND A LOWER Kp IS WORSE, NOT SAFER** — the loop gain is minimised near **Kp ≈ 1.0**, so the
  preset's "Kp 0.3 is the conservative choice" reasoning is **backwards**. **The repair is on the fork
  side: preset friction 0.01 → 0.00** ⇒ PM **42.2°**, Ms **2.06**, gain margin **×1.40**.
  🛑 **RE-SCORED AT THE MEASURED τ AND AT THE REPAIRED PRESET: B6 STILL FAILS AS WRITTEN — AND IT IS A
  BROKEN CHECK THAT FIRES CLEANLY.** V293 at friction 0.00 breaks **3 of 10** controller-loop cells (worst
  **PM 33.2°**, k30 1.09, kU 1.80 at 5 m/s / τ 0.25) — and **V282, at the tune it is actually flown with,
  breaks 3 of 10 too** (worst **PM 35.6°**, k30 1.12, kU 1.74 at 28.5 m/s / τ 0.22). On the path-following
  channel **both** go unstable inside [0.5×, 2×] (kU 1.31 vs 1.27); the friction repair is worth **×1.58
  on k30.** ⇒ **Scored on its INTENT — V293's outer loop no worse than the build on the car — B6 PASSES.**
  ⚠ **Residual, named not closed: the creep margin at 5 m/s is only ~10–20 % of plant gain on BOTH builds,
  and the failure mode there is the V276 1–4 Hz signature — the FIRST THING TO WATCH, at low speed.**
  ⚠ **The verdict was conditional on τ ≥ 0.18 s, and τ = 0.20 s was the operator's `SteerDelay`
  toggle ECHOED BACK, not identified** (the Honda port's prior is **0.10 s**).
  ✅ **τ HAS SINCE BEEN MEASURED** (`rlog-tools/studies/grind/TAU-ACTUATOR-DELAY-2026-09-13.md`, six
  routes): **258 ms** [251, 264] at 3–8 m/s, 232 at 8–15, 211 at 15–25, **182** at 25+. **The condition
  τ ≥ 0.18 s holds at every speed band, and with margin (258 ms) at the 5 m/s point where the FAIL sits.**
  ⚠ **Not a clean substitution** — the same report finds the path is **not a pure delay** (three
  estimators differ by up to 100 ms; the fitted pole is **1.4–4.3 Hz, the torque controller's own
  bandwidth plus plant, NOT the EPS servo**) and says to use **`tau_eq(f)` at the crossover**, not a
  scalar. **B6's premise is satisfied on the best evidence available; the re-score settles the verdict.** ✅ **The 1–4 Hz V276 signature does NOT reproduce on frequency** — every predicted cycle sits at
  **1.21–1.25 Hz**. ⚠ **The clause's literal "[0.5×, 2×] true gain" wording is BROKEN** (V282 fails it at
  28.5 m/s, κ 2), **but the V293 FAIL does not rest on it**: it sits at **κ 1.00, where V282 reads 40.1°.**
- **B3 PASS** (delivered before `advB3` died): **rail ×1.000000 by three methods**, slope **0.641212
  counts per CAN count**, the P clamp binds at **idx 239**.
- **B1 PASS at r24 = 2048** — **0 unstable fits on every family and every κ**; **4451 has 5 unstable on
  the broad family at κ 0.45.** ⚠ The literal `ζ < 0.05` clause is **broken** — it condemns the FLOWN
  V282 on **250/250** and **12/12** — so it was scored as *"no unstable fit and no worse than V282."*
  ⚠ **The both-poles family at κ 1.45 is EMPTY (n = 0), hence unscoreable** — the κ dispute is not
  settled by this pass, it is sidestepped at one end.
- **B5 PASS at r24 = 2048** — the 5–9 Hz rise is **×1.50–1.59 vs V282** and **×1.05–1.13 vs STOCK**,
  **under both thresholds** (the clause needed ≥ ×1.6 **and** ≥ ×1.2 together); **4451 trips the first leg
  on r39.** ⭐ **The rise is BROADBAND and peakiness is UNCHANGED** — structurally different from the
  resonant 7 Hz re-arm V292 produced, which is the distinction the operator will actually feel.
- ⭐⭐ **B1 AND B5 TOGETHER VINDICATE THE 2048 RULING.** The dose was recorded above as **BELIEF** against
  the design's criterion-exact 4451, with B briefed to score both side by side. **It did, and 2048 wins on
  both clauses while 4451 fails each.** That BELIEF is now **EVIDENCE** on B1 and B5.
- **B4 PASS — the THINNEST margin in the pass.** Ripple/level on loaded turns **0.028 / 0.034 / 0.048**
  against the 0.25 gate (V282 0.019 / 0.013 / 0.099; **stock 0.044 / 0.033 / 0.087 — V293 sits BETWEEN
  the two**); predicted F7 **≈ 1.24 /100 s** against 2, **a margin of only ×1.6 through a nonlinear
  mapping.**
- **B7 PASS** — **0 of 250** plants with ζ < 0.10 in 10–18 Hz; 13–17 Hz **×1.058** max vs V282 against a
  ×1.5 gate. (V292's rejected number on the same band was ×1.9–2.1.)
- **B8 reported** — the command-driven 18–22 Hz torque is **×0.055–0.137 of V282's ring and has NO POLE:
  it cannot ring.** This is the residual the operator may still feel with the loop open, and it is small.
- 🛑 **B2 FAIL AS WRITTEN — ADJUDICATED PASS ON INTENT, AND THE DISSENT STANDS.** Uncalibrated ring
  **×0.285** (r39) / **×0.403** (r6c); the mandated V292 calibration (**×1.90–3.64**) ⇒ **×0.54–1.04 /
  ×0.77–1.47** against the ≤ ×0.50 gate; the open-loop calibration (×1.64) ⇒ 0.47 / 0.66; **the on-car
  anchor, no predictor, re-derived independently: ×0.237 / ×0.285 / ×0.265.**
  **Why it was adjudicated rather than settled by the broken-check rule:** B2 does **not** condemn a flown
  build, so that rule does not reach it. The calibration factor was measured on **V292, a build that did
  NOT open the loop** — the fit family's error there is in how a feedback pole reshapes the return ratio
  at 20 Hz, **an error with no channel when the operand is identically zero** (`|S| ≡ 1` is an identity the
  code region's bytes prove, not a fit). Transferred to the one fully-open-loop configuration the car has
  been measured in, **that calibration over-predicts the measured ring by ×1.3–2.0 — the calibrated
  predictor fails a measured case.** On the clause's intent (the ring at least halved) the direct on-car
  measurement reads ×0.24–0.29 and the command-driven residual ×0.06–0.14, **both EVIDENCE rather than
  model.** 🛑 **The V292 precedent is stated, not hidden: V292 was ALSO cleared over one dissent and then
  failed on the wire on clauses the model had passed — which is exactly why this candidate's ring claim
  rests on the car's own open-loop measurement and NOT on the replay.**
- 🛑 **Agent note: `advB3` DIED of an OUT-OF-MEMORY error mid-run**, after delivering B3 and the B6
  sub-check; **`advB3b` completed B1, B2, B4, B5, B7, B8 and the B6 re-score at the repaired preset.**
- 🛑🛑 **TWO RECORD DEFECTS `advB3` FOUND ON ITS WAY DOWN, both in machinery other results rest on.**
  **(a) The module-default `B(f)` fit is BAD** — at `nb = 1, nd = 4` it returns rms `ln|B|` **0.54**,
  phase error **38°** and **a spurious UNSTABLE 4.5 Hz root**; **use the design's `nb = 1, nd = 3`**, and
  re-check anything fitted with the module default. **(b) `r24_plant_refit.py` CANNOT REGENERATE
  `r24_plant_refit.json`** — its `fit_B(nb=4, nd=2)` now raises on the properness guard, so **the
  pre-registration's own named reference family for B1 is not reproducible from its own script** and the
  JSON on disk is an artifact with no working producer.
- **Golden model:** contract re-verified and **moved 90 → 94 symbols** this close-out, because the LKAS
  rate PID itself was finally added (`lkas_rate_pid_tick`, `lkas_rate_pid_surface`, `lkas_rate_lerp`,
  `lkas_output_lag`) — closing the gap that had left V288's and V289's mirrors with no caller. The
  `_self_check()`+`_demo()` hash is **unchanged**, and an independent march reproduces V293's surface.

_Four independent agents on disjoint surfaces (A arithmetic · B unit/scale + GATE 2 closed-loop · C build
audit · D interlocks/downstream), FAIL criteria fixed in `docs/review/ADVERSARIAL-V293-PREREG-2026-09-13.md`
**before the image existed**, with a FAIL on A, B(1–6) or D(1–4) defined as **DO NOT FLASH**. **Two clauses
did fail as written and neither was quietly dropped: B6 was voided by the kit's standing broken-check rule
because it condemns the FLOWN build by the same count, and B2 was adjudicated on its intent with the
dissent kept on the page.** The pass was structurally able to return "do not flash" and is on record as
having fired twice. **What it licenses is a candidate handed to the operator, not a recommendation to
fly — that decision is his.**_


---

### V294 — ACCELERATION TRIM on the V293 torque map: the tick difference of the lag-filtered wheel rate through the stock P gain, the feedforward byte-exact  (2026-09-20, **BUILT, NOT FLOWN. Adversarial pass A (arithmetic/sign/scale) and B (build audit/interlocks) both PASS with FAIL criteria fixed before they ran; six non-blocking defects, four fixed in the script. The decision to flash is the operator's. V293 stays on the car until then.**)

**Class — the first build to close a NEW loop variable in the EPS.** V282–V292 tuned or opened the EPS *rate* loop; V293 deleted it; the fork's rev 2–6.4 tried to replace it at 100 Hz through a ~60 ms round trip and could not damp the 1–2.7 Hz wheel mode. V294 puts a loop back at 1 kHz **on acceleration**, through the stock PID's own P gain, with V293's torque map untouched: `r26 = clamp(s_new − s_old, ±1024)`, `E = 4·sp − r26`, `P = (E·960)>>8 = 15·sp − 3.75·r26`. Not a re-run of any flashed lever: the operand (a tick difference of the lag state) has never existed on any image; no build has run Kp 960 or a 2 Hz fb pole. Nearest precedents: V289/V291 moved the same pole (25 / 9.94 Hz) with the SUM operand live — a different loop; V282's D term was an acceleration feedback on the ERROR (setpoint kick, 67 % clamp) at 48.7 P-counts per washout count vs this trim's 2.08 P-counts per x-count above 2 Hz (7 % of V282's rate loop; −26.7 dB at 20 Hz).

**base** V293 (`_v293_…TORQUEMODE.FB0…_plain_image.bin`, `f75e77cf…`) · **image** `3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85` · **rwd** `a2b418f061160f66ffaa8ac541a478d43771fcbd004a92dc3d7a071cfd9f706a` (`39990-TVA,A160-V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP-0x13000-0x100000.rwd`, **exactly one on disk**) · script `analysis-2020accord/builds/v108_plus/build_v294_tva.py` (159 assertions, self-census 66 substantive / 89 vacuous / 4 tautological — adversary B counts 41 substantive by entailment; zero-edit control reproduces V293 bit for bit; **20/20 mutations caught**, four of them added from adversary B's misses) · design `analysis-2020accord/studies/v294/v294_design.py`.

| where | V293 | V294 | what |
|---|---|---|---|
| `0x28FA4` **code** | `add r9,r26` c9d1 | `subr r9,r26` 89d1 | r26 := s_new − s_old (was s_old + s_new): the per-tick CHANGE of the lag-filtered wheel rate = acceleration through the lag pole, ×b/1024 |
| `0x29D76` **code** | `shl 0x5,r16` c582 | `shl 0x2,r16` c282 | E = 4·sp − r26 |
| `0xC62E6` fb clamp | 0 | 1024 | bounds the trim at (960·1024)>>8 = 3840 sum counts = 615 delivered = 25 % of the rail |
| `0xC63E8` fb-lag pole a | 923 (16.5 Hz) | 1011 (2.03 Hz) | the acceleration bandwidth |
| `0xC63EA` fb-lag gain b | 1560 | 567 | the trim gain (K_α/J = 1.0 at the BELIEF scale of 8 x-counts per deg/s) |
| `0xCB994` Kp bank ×28 | 120 flat | 960 flat | (sp<<2)·960 ≡ (sp<<5)·120 = 3840·sp for every 32-bit sp — **the feedforward is bit-identical** |

**314 diff bytes** = 2 code + 4 cal + 280 Kp + 28 CRC over 7 blocks; exactly two bytes below `0xC0000` differ in value. Kd 0 + D clamp 0 (no jerk term), Ki 0 (no rate term), r24 2048, map, 427 tap, 0x14A cave: byte-identical.

**Design (EVIDENCE for the algebra and the integer mirror; BELIEF for the plant J 8e-5 / k(v) / light b 0.0006):** with T = −K·H·α and H a LAG, J_eff = J + K·Re H and b_eff = b − K·ω·Im H, so every degree of loop lag turns the trim into damping; delayed RATE feedback anti-damps past 90° (V282's 20 Hz crossover resonance). Pole sweep at K_α/J = 1: ζ of the wheel mode ×0.81…1.28 (5…26 m/s) at the stock 16.5 Hz pole (inertia dominates below 5 Hz: WORSE at low speed), **×1.02 / 1.16 / 1.49 / 1.82 / 2.05 at 2.0 Hz**, ×1.13…1.93 at 1.4 Hz. Shipped 2.0 Hz. Rigid-body loop gain of the trim: max 1.7 at the 2.4 Hz resonance (that IS the damping), −180° crossings at 24–35 Hz with |L| 0.02–0.05 (from the plant's own s², not the trim). int32 margin at the ±12000 rate guard 4.06×. The difference operand settles to EXACTLY 0 at every steady rate (no floor bias, unlike the sum's 2434 at x = 80).

**Adversary A's two framing corrections, adopted:** (i) the 25 % cap binds only at ≥230 deg/s of wheel rate (measured peak 42–56; r71's limit cycle 88); through the whole chain the trim is **1.85 T counts per deg/s of 2 Hz-band rate** = 0.0007 torque/(deg/s), a damper comparable to the wheel's own (~18 counts at 10 deg/s, 163 at 88) — the right size for a ζ lever, and it makes the wire read a REGRESSION over the drive, not a per-frame read; (ii) at 2–3 Hz the trim is ~97 % damping / 26 % inertia; pure inertia only below ~1 Hz.

**Adversary B's census (positive-controlled, on the built image):** every changed cell private (3/1/1 accessors, zero writers, base and built accessor sets identical, all three cal cells in FLASH so no register-indirect write reaches them); the 0x14A cave reads the delivered torque and four non-PID cells, **not** the published P/I/D cells (zero readers image-wide; S read once in the orphan island); the fb state `gp-0x3d30` has one load and one store, both in the filter, and no reset block touches it; no governor/EME function reads any changed or rescaled cell; V293's D1 conclusion (lane cap 3072 cannot drive soft-EME wind-up) survives. **The one new behaviour:** up to 616 counts at ZERO command (V293: 0; V282 flew 2463) — so if the base assist were within 616 counts of the 5120 EME floor and the wheel ramped hard for 75 ms, V294 enters the 5120–5325 band V293 could not; bounded, 0.25× V282's flown exposure. After a filter BAIL the first tick's operand equals the fresh state (22–1023 counts, one tick, then the 5 Hz lag). **Defects (reports):** substantive count 41 by B's entailment census; `decode_one` mis-decodes the 6-byte `mov imm32` (neither V294 decode window contains one); the record's 30th `gp-0x6a56` access at `0x14B1E` is `jarl 0x5E0C8,lp` — the count is 29 (erratum added to the trace).

**The instrument (on the wire, untouched):** `residual = T_tap − FF_V293(idx)·taper` is the trim on every engaged ramped frame; regressed on −(0x18F rate through a 2 Hz low-pass, differenced): predicted slope 1.85 T counts per deg/s, FF identity R² ≥ 0.98 on low-acceleration frames = LIVE, RIGHT SIGN. Flat = not live (nothing else licensed). **Positive correlation = SIGN INVERTED: stop, revert to V293.** A new line anywhere in 5–30 Hz = the revert signature. Outcome: 1.6–3 Hz wheel-rate energy in hard turns vs r75/r76, predicted down — the operator scores the feel.

**Risk, plainly:** two code bytes change (in place, same length — V57/V104's class); the physical scale is BELIEF (K_α/J 0.5 / 1.0 / 2.0 at 4 / 8 / 16 counts per deg/s; the 25 % cap is scale-free); non-zero lane output at zero command while engaged (above); the first drive is on a REVERTED fork (two things change at once; the residual attributes the EPS edit regardless).

**Third adversary (2026-09-21, Opus with GhidraMCP reconnected; the operator clarified the subagent cap was on Fable only):** C1/C2/C4/C5 PASS from the real decompiler — both edits and their following instructions as claimed, all 1874 instruction boundaries of FUN_00028ea6 identical to V293 (two texts differ), the diagnostic packer at 0x4E82E is a pure record with no threshold, the cell census matches; one refinement: `0x2A0C8 cmp r0,r26` is a second in-function reader of the operand on the unreachable `gp-0x680a == 1` damper lane (zero writers, boots 0). **C3 was reported FAIL — "x = 1.0–1.7 counts per deg/s, the trim 5–8× weaker than designed" — and is WITHDRAWN on the wire.** Its chain identified the frame at gp-0x14ce as 0x14A; the record places the 0x14A buffer at gp-0x1518 (`FUN_00057b24(gp-0x1518, 8, 0x14a)`, TRACE-2026-08-13-v100-6ad6-and-ivar6). The direct measurement — three V292 routes (6d/6e/6f) where the rate loop was live and the lane delivers −4.80 T-counts per x-count — reads **x = 7.1–7.8 counts per deg/s at every rate bin from ±2 to ±12 deg/s** (`analysis-2020accord/studies/v294/x_scale_from_v292_wire.py`; median of 15 bins 7.5). **The design's 8 stands, upgraded from BELIEF to EVIDENCE; K_α/J = 1.0 at 8 is 0.9–1.0 at the measured value; no re-cut.** C's ISR reading (the rate former differences a 16384-count/rev position at ~3 ms → 1 count per deg/s of that shaft, ×1.6978 to x) is consistent with 8 if that shaft is geared ~4.71:1 to the steering wheel (the record's 4.7121 × 1.6978 = 8.00) — BELIEF, open.

**Fork side:** Dom `54ff1ea39` — every torque-mode term defaults to stock (off), `AccordRatePlantFF` off, new `AccordJerkLpHz` (1.2 default = generic; 4.0 = rev 6's value), nothing deleted; `toggle-config_V294_accel-trim_r1.json` (SteerKP 0.9, Ki 0.3, LAF 14, friction 0.011, every torque-mode term at stock) and `…_REVERT_to_V293_r64.json`. Golden model: `fb_op` / `e_shift` fields, `_self_check_v294()`, 94 symbols, hash unchanged. Handoff `HANDOFF-2026-09-20-v294-acceleration-trim-built-fork-reverted.md`.
