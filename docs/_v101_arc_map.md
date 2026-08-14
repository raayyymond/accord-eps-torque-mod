# V101 ARC MAP — the whole record, vetted, so the flight score can land on a pre-cleared shortlist

**Written by the V101 landscape pass, 2026-08-13.** Read-only against the record except for this file.
`extract-r85` owns the route-`0x85` flight score; **nothing in this file reads an rlog.**

**Every byte figure below is read from the `_*_plain_image.bin` snapshots on disk**, never from a build
script. New reader this pass: `analysis-2020accord/ledger_v38_to_v100_bytes.py` — a one-build extension of
`ledger_v38_to_v99_bytes.py` (TARGET V100, PREV_ON_CAR V99, one row added to `BUILDS`). Reproduce:

```
ACCORD_FIRMWARE_ROOT=C:/Users/dudei/Desktop/Projects/accord-firmwares
python analysis-2020accord/ledger_v38_to_v100_bytes.py frozen      # §1
python analysis-2020accord/ledger_v38_to_v100_bytes.py delta       # §1c
python analysis-2020accord/ledger_v38_to_v100_bytes.py diff V99 V100
```
**90 build images load (V22..V100, V95 correctly excluded as a burned number).** Anchors pass on every
run: stock `0xC646C == 891`, `code.bin[0x454FE] == 0xBA`, every image `len == 0x100000`.
**`N == 90` means the cell has NEVER moved on any build.**

🛑 **STATUS:** V99 flew as route `0x82`. **V100 FLEW AS ROUTE `0x85` and is ON THE CAR.** V100 is a
**ZERO-CALIBRATION INSTRUMENT BUILD** — the control law he drove on `0x85` is **V99's**, bit for bit
(§1c). Identity: V100 = `0x14A` byte4 **b3 ≡ constant 1** + byte7[7:6] = 2; V99 = **b5** duty 1.000000 +
byte7[7:6] = 2. **b3 vs b5 separates them single-frame.**

## 🛑🛑 THE ROUTE-`0x85` RESULT — E1 READ **ZERO**. THE REFERENCE-CLAMP HYPOTHESIS IS DEAD.

[EVIDENCE, `extract-r85`, decode confirmed arithmetically by the orchestrator] Over **29,999 frames /
249.2 s engaged — ~4× the best engaged exposure ever recorded on this kit** — both PID saturation rungs
read **EXACTLY ZERO**: `b5` (`|gp-0x6ad6| ≥ 8192`) duty **0.000000 in every one of 8 wheel-rate bins**;
`b6` (`|gp-0x4f60 − gp-0x6ad6| ≥ 10240`) duty **0.000000**. Positive controls healthy — `b4`
(`sign(gp-0x6ad6)`) **0.6057** engaged, **the same cell as `b5`**, so the load is live and the rung could
see; `b7` 0.5222. Identity duty 1.000000, fault-free, 427 not saturating.

⇒ **The pre-registered ZERO sentence is licensed verbatim:** *"`gp-0x6ad6` never reached the PID's ±8192
clamp in any engaged frame. Path 2's marginal authority was NOT zeroed by this saturation,
`d(gp-0x6b94)/d(gp-0x6b70) = 0.2565` stands in the flown regime, and the `f′`-compression account
remains the only surviving explanation for V89 and V97. **THE REFERENCE-CLAMP HYPOTHESIS IS DEAD AND
MUST NOT BE RE-PROPOSED.**"*
⊕ The composite E2 sentence is also licensed: *"Neither saturation was active — Path-2's marginal
authority was never zeroed by clipping."* **That closes the whole saturation family**, not one clamp.
⊕ `gp-0x6b94` uses only **19 % of its range** (p50 102 ct, max 1,933 of ±10,240) ⇒ consistent with V65's
"the aggregator never rails". **The delivered path is linear end to end on this drive.**
⚠ A separate agent is proving the cave rungs could physically have fired — **strong, not yet final.**

🛑 **AND THE DRIVE IS NOT CREEP.** Engaged p50 **39.6 km/h**, p90 **99.6**, max **104.5**; **≥50 km/h for
88.4 s, ≥80 km/h for 45.5 s.** Wheel rate: micro (1–13 °/s) **102.7 s** · ratchet (13–50 °/s) **51.3 s**
· macro (>50 °/s) **14.8 s**. ⇒ **§5.2c is a mandatory read before any number in this file is quoted for
this drive — most of the arc's sizing is creep-only, and one kill re-opens.**

---

# §1 — THE CROSS-BUILD CELL MATRIX AT V100, READ FROM THE IMAGES

## §1a The frozen-count matrix — the cells that have MOVED, newest first

`moves` = how many times the cell changed value anywhere in the V22..V100 chain.

| addr | **N frozen** | since | moves | stock | **V100** | state | what it is |
|---|---|---|---|---|---|---|---|
| `0x55DF2` | **1** | V100 | 6 | 37864 | 37996 | NON-STOCK | CAN-427 packer SOURCE (V100 repointed `gp-0x6b70` → **`gp-0x6b94`**, the aggregator output). Telemetry only |
| `0xC40BC` | **2** | V99 | 3 | 600 | **300** | NON-STOCK | Coulomb relay knee. **CLOSED AT ANY DOSE by V99's E1** |
| `0xC63AC` | **2** | V99 | 2 | 102 | 102 | **STOCK** | Stage-1 IIR α on the ACTUAL arm. V97 moved it 102→150; **V99 reverted it to Honda's own value** |
| `0x55E10` | 5 | V96 | 4 | 0xA3 | 0xA6 | NON-STOCK | 427 packer shift (`sar 6`). Telemetry only |
| `0xD7A5C/5E/60` (m26 Y) | 5 | V96 | 7 | −9830/−5734/−1966 | **−14745/−8601/−2949** | NON-STOCK | `0xCBE74` friction/inertia LERP, **ENGAGED** column, ×1.5 |
| `0xD7A6C/6E/70` (m27 Y) | 5 | V96 | 7 | same | same ×1.5 | NON-STOCK | same dose, mode 27 |
| `0xD6A6C/6E/70` (m24 Y) | 5 | V96 | 2 | −9830/−5734/−1966 | **unchanged** | STOCK | the MANUAL column — deliberately left Honda |
| `0xC640A` / `0xC640C` | 5 | V96 | 2 | −8192 / −3277 | unchanged | STOCK | `FUN_00036c12` non-LERP fallbacks |
| `0xC40D2` | **11** | V89 | 1 | 102 | **204** | NON-STOCK | **K1**, modelled Coulomb friction (MODEL arm). V89's own lever, never touched since |
| `0x3AA96` + `0xC6446` | **12** | V88 | 9 | 0xC5 / 512 | **0xFB / 5244** | NON-STOCK | **LEVER B** — the r24 engaged arm + its gate. The kit's second measured fix |
| `0xC40D4` | 14 | V86b | 2 | 573 | 573 | STOCK | observer torque IIR. V86 moved it 573→286, **reverted by V87's rebase** |
| `0xC63A0` | 18 | V83a | 6 | 1024 | 1024 | STOCK | Path-2 lane weight w[0] (`gp-0x6bd0`, the damper lane) |
| `0xC6A72`/`74` | 18 | V83a | 10 | 3072 | 3072 | STOCK | `gain_A` rec0 |
| `0x2A1F0` + `0xC6CD0` | **19** | V81 | 5 | 29804 / −1 | **31952 / 3564** | NON-STOCK | **V57's private 4.000× forward LKAS gain** + its decouple displacement |
| `0xC62EA` | 19 | V81 | 5 | 320 | **0** | NON-STOCK | low-speed steer lockout — steer-to-zero |
| `0xC646C` | 19 | V81 | 7 | 891 | 891 | STOCK | the SHARED sensor scale V57 stopped abusing |
| `0x454FE` | **20** | V80 | **11** | 0xBA | **0xB5** | NON-STOCK | V42's macro-ratchet fix. **Eleven moves on one byte** |
| `0xC407E` | 22 | V78 | 4 | 511 | 511 | STOCK | **the hard-fault interlock clamp**, back at Honda's 511 |
| `0xC6444` | 30 | V72 | 4 | 512 | 512 | STOCK | r26 engaged arm |
| `0x3AB76` / `0x3AC20` | 32 | V71b | 6 | 0xAA | 0xAA | STOCK | **Lever A** (V62's `sar`) — off the car, deliberately |
| `0xC643E` / `0xC6440` | 39 | V65 | 4/2 | 1536 / 2048 | unchanged | STOCK | `gain_A` arm / third arm |
| `0x55C0E` | 51 | V53 | 8 | — | jarl→cave | NON-STOCK | the `0x14A` cave hook (100 Hz). Instrument infrastructure |
| `0xC644A` | 57 | V49p | 4 | 1024 | 1024 | STOCK | V43's dirty-derivative pole |
| `0xC6450` | 61 | V47 | 2 | 1024 | 1024 | STOCK | V46's lever |
| `0xC6206` / `0xC6208` | 62 / 67 | V46 / V41 | 4/2 | 512 / 205 | unchanged | STOCK | the speed-selector cals V40 **bricked** on |
| `0xC61B2`/`B4` · corridor walls · boost floors (14 cells) | **70** | V38 | 2–3 | various | **≈5× wider** | NON-STOCK | the V38 authority envelope every later build sits on |
| `0xE4194..0xE521C` (72 cells) | 70 | V38 | — | 15360 | **16384** | NON-STOCK | ARB setpoint limits, all selectors |
| `0xC64B8` | 71 | V37 | 1 | 0x70 | **0xFF** | NON-STOCK | DTC-0x49 fix (resolved on-car 2026-07-14) |
| `0xC61C0-C4`, `0xC64B4/B6` | 72 | V36 | 1 | Honda | **65535** | NON-STOCK | gentle-EME debounce, disabled |
| `0x13109` / `0x14120` | 90 | V22 | 1 | `-` | `,` | NON-STOCK | cosmetic part-number marker |
| `0xC64DE` | 90 | V22 | 1 | 25617 | 25627 | NON-STOCK | "legacy re-engage ramp", label disputed, **never once isolated in 90 builds** |

## §1b 🛑 THE FROZEN PERIMETER — 66 of 114 named cells sit at **N = 90: never moved on any build**

**This is the single most decision-relevant fact in the matrix.** The entire observer/PID *structure* has
been an untouched perimeter for the whole arc; every V85→V100 edit has been **inside** it, never **to** it.

| addr | N | stock = V100 | what it is |
|---|---|---|---|
| `0xC4080` | **90** | 0 | **K0 — the NEVER-RAISE pure-Coulomb relay hazard.** VIRGIN |
| `0xC40D0` / `0xC40D6` / `0xC40D8` | **90** | 408 / 246 / 3686 | the other three `FUN_0003b8f6` EMAs. VIRGIN, untraced as levers |
| `0xC6200` | **90** | 8192 | **the ±8192 clamp — FOUR roles, one of them the PID reference.** VIRGIN |
| `0xC63AE` | **90** | 1024 | Stage-2 input scale. VIRGIN, **NO-GO** |
| `0xC6468` | **90** | 2639 | model output gain — **SHARED, scales BOTH arms of the residual.** VIRGIN |
| `0xC646E` | **90** | 1428 | the INERTIA/damping gain. VIRGIN |
| `0xC63A2/A4/A6/A8/AA` | **90** | 1024 ×5 | Path-2 lane weights w[1..5]. VIRGIN |
| `0xC6AE6` / `0xC6B12` / `0xC6B26` | **90** | 2048 / 98 / 256 | **PID Kd / Ki / Kp.** VIRGIN — the PID gains have never been touched in 90 builds |
| `0xC616C` | **90** | **0** | term-0's driver-torque clamp. VIRGIN, **NEVER-RAISE** |
| `0xC61F6` | **90** | 3 | r24 lane deadband. VIRGIN — **and 0 of 65 images ever wrote it** |
| `0xC6194` | **90** | 3 | the REAL LKAS slew limiter — **DEAD** (`0xC4118` all-1) |
| `0xC61B8` / `0xC61DA` / `0xC61D6` | **90** | 102 / 1092 / 0 | pre-gain deadband · Q10 integrator scale · shaper slew step |
| `0xC520C` | **90** | 5 | governor rate ceiling (V40 bricked on a **neighbour**) |
| `0xC63F8` / `0xC63FC` | **90** | **33 / 328** | ⭐ **a 10× LEFT/RIGHT ramp-rate asymmetry, VIRGIN on all 90 images** |
| `0xE5284/E52FC/E5404/E547C` | **90** | 4 | the authority-collapse curve records |
| **FactorC m26 Y** | *(mode record)* | `[0, 234, 429, 908]` | **BYTE-STOCK on V100** ✔ verified this pass |
| **FactorE m26 X / Y** | *(mode record)* | `[60,400,2500,4000]` / `[0,140,539,927]` | **BYTE-STOCK on V100** ✔ verified this pass |

⊕ **Damper verification, run this pass directly against the images** (pointer arrays `FactorC 0xC9E9C`,
`FactorE 0xC9F84`, mode 26, `Y` at `base+2+2n`): FactorC/FactorE mode 26 are **byte-identical to STOCK on
V84, V85, V86, V87, V88, V89, V90, V92, V94, V96, V97, V98, V99 and V100.** The only exception in that
window is **V86b**, which lifted FactorC `Y[0]` 0→908 and nothing else. ⇒ **the base-assist damper has
been at Honda's own surface for 14 consecutive build images (V87→V100), V86b excluded.** [EVIDENCE]

## §1c V100's cumulative non-stock delta — 292 bytes, ZERO unattributed

`image sha256 c1d36b68390421bfce6c826799108839a8acb90decfb18c72a584189e54197db` (re-derived this pass).

| class | bytes | note |
|---|---|---|
| CAVE / telemetry | **132** | `0xC4B34-0xC4BB7`. **Changes no control signal** |
| CRC / packaging | 20 | 5 per-4KiB block checksums. A consequence, not a lever |
| **CONTROL-LAW** | **140 bytes, 114 named cells** | **bit-for-bit identical to V99's 140** — V100 moved **ZERO calibration bytes** |

**V99 → V100 = 128 bytes in 12 runs**: `0x55DF2` (1 B, 427 repoint) · `0xC4B36..0xC4BCD` (123 B, cave) ·
`0xC4FFC` (4 B, CRC). ⇒ **V100 is a ZERO-CALIBRATION INSTRUMENT BUILD. It is not a fix and must never be
recorded as one.** Whatever the operator felt on route `0x85`, the control law he drove is **V99's**.

## §1d Image-trust flags

- ⚠ **V70 was re-cut under the same build number**, so the second cut silently overwrote the first's plain
  image. The image on disk loads and diffs cleanly, but **do not cite a V70 hash as proof of anything.**
  Open defect: `memory/accord-recut-overwrites-the-previous-plain-image.md`. Fix recommended, not applied.
- ⚠ **Two artefacts share the V76 number** and disagree on both RULE-11 cells. **A glob is not a check** —
  the ledger pins `V76 = _v76_v38base_relu_damper_plain_image.bin` by name.
- ✅ No missing images in the V22..V100 chain; the `packaging_mask` audit returns the same 12
  "real edit, not packaging" bytes recorded before (`0x55C0F`, `0xC61C0..C5`, `0xC64B4..B8`).
- ✅ The previously-recorded "loader misses `_v67_plain_image.bin`" bug **did not reproduce** against the
  current file set.

---

# §2 — THE KILL LIST

**Vocabulary, and these are NOT synonyms** (`BUILD-LINEAGE.md:476`, `AUDIT-2026-08-12:24-35`):

| word | means | what it licenses |
|---|---|---|
| **FALSIFIED** | in force on a drive, pre-registered effect did not appear | retiring the hypothesis **against the symptom actually scored** |
| **INERT-BY-MODE** | never in force — wrong mode record / gate never armed / silently reverted | **nothing.** The lever is UNTESTED |
| **STRUCTURALLY-DEAD** | executed, and its output is arithmetically zero or negligible where the symptom lives | nothing about the hypothesis; the *cell* is dead |
| **UNINTERPRETABLE** | flew, lever LIVE, the **instrument** failed | **nothing — and it is a design failure on our side** |
| **WRONG-DIRECTION** | measured, and the sign says the other way | the lever is real; the push was backwards |
| **NEVER-TRIED** | no build ever wrote the cell | a *candidate*, not a re-run |

## §2a FALSIFIED — in force, and it did not fix its target (or moved it the wrong way)

| lever | what it is | flew as | on-car result | **status** |
|---|---|---|---|---|
| **`0xC40BC` 600→6000** | Coulomb relay knee, UP | **V85**, route `6e` | lever DELIVERED (relay saturation 39.5→11.1 %, engaged 7.21×) but engaged/manual 6–9 Hz went **2.89× → 6.58×**, band contrast **+0.682 [+0.213, +1.166]** ⇒ **raising it made the ratchet 2.3× WORSE** | **WRONG-DIRECTION** |
| **`0xC40BC` 600→300** | the same knee, DOWN, virgin range | **V99**, route `0x82` | 🛑 **E1 NULL — all four rate bins moved, all four DOWN** (lever 0.7335/0.8749; control 0.9374/0.9119); the pre-registered "all four ⇒ route artefact, not the lever" sentence fired verbatim. **Because the reachable friction set is bit-identical V98↔V99, this closes the cell AT ANY DOSE** | **FALSIFIED — cell closed at every dose** |
| **`0xC40D2` 102→204 (K1)** | modelled Coulomb friction, MODEL arm | **V89**, routes `75`/`76` | **0.947 [0.827, 0.979]**, inside a same-build placebo band [0.900, 1.111] = 0.92σ. Operator: *"fixed nothing."* The naive CI **excluded 1.00** — the placebo control earned its keep on first use | **FALSIFIED** — precise kill: aimed at a **live arm** (V98 `b6`=0.4235) but a **negligible sub-term** (`\|friction\| ≥ 0.0625` on 0.009 of the 1–13 °/s micro regime) |
| **`0xC40D4` 573→286** | observer torque IIR pole | **V86**, route `6f` | pre-registered [0.797, 0.875]; measured **1.001 [0.976, 1.060] — DISJOINT, well-powered** ⇒ 🛑 **the LINEAR-LOOP hypothesis is DEAD**; ~8 Hz is a resonance, Q 14–29 | **FALSIFIED** |
| **`0xC6444` 512→3072** | r26 engaged arm, UP | **V71c**, route `58` | grind #1 **223 vs 109 — HIGHER, P=0.0215**; grind #2 returned (7 bursts @44.31 Hz); ratchet **8,521 ct p-p = the corpus RECORD**. **The 6× r26 CUT is load-bearing in Lever B** | **FALSIFIED AND REVERSED** |
| **`0xCBE74` ×1.5 engaged** | friction/inertia LERP, m26/m27 | **V91/V92**, routes `78`/`79` | engaged ratio **0.99 [0.91, 1.26]** vs pre-registered 1.50 ⇒ read as a null — 🛑 **now known to be CLOSED-LOOP INVARIANCE (`y = K·α` is invariant to `K`), not an inert lever** | **UNINTERPRETABLE** (was mis-filed as falsified) |
| **`0xCBE74` ×0.25 engaged** | the same cells, DOWN | **V94**, route `7d` | ☠ **the only build the operator has ever aborted.** *"Vibrated the entire car."* Measured after: the delivered lane is **+137°/+139° vs wheel rate at 6–9 Hz ⇒ +518/+565 ct of POSITIVE `Re(Z)` — a real damper, and V94 removed 6/6ths of it** | **WRONG-DIRECTION, with a measured sign** |
| **damper dose `k`** | FactorC/FactorE | V74…**V80**/V83a | **V80 at k=4.16 = "worst grinding ever"** — 2.09× broadband HF lift + a 30 s 27.4 Hz limit cycle, **no fault** (a *stability* failure). Grind #1 **INERT across k = 0.58 → 4.16**; 6–9 Hz improves **only** at k=4.16, the same point that carries the penalty. **There is no free-benefit bracket** | **FALSIFIED as a dose; the SHAPE thread survives (§2f)** |
| `0xC644A` 1024→64 | dirty-derivative pole | V43 | null; the lane was later ELIMINATED by V56 | FALSIFIED |
| `0xC6450` 1024→32 | — | V46 | null. 🛑 **re-proposed as "new" by two agents in one session — the founding incident of `BUILD-LINEAGE.md`** | FALSIFIED |
| `0xD2006` 102→43 | — | V60 | *"It did not fix the vibration issue."* | FALSIFIED |
| 12 Hz EMA on 19 carriers | — | V52c | *"did not fix the vibration; clearly changed manual feel."* 🛑 no rlog exists | FALSIFIED |
| `0xC6AFC`/`0xC6AFE` → 0 | mute of `gp-0x6ad4` | V56, route `24` | null **and cost damping** — 🛑 **BAND-SCOPED: scored on 15–26 Hz, NEVER on 6–9 Hz**, and route `24` is not on disk. The elimination is carried as if general. **It is not** | FALSIFIED **at 15–26 Hz only** |

## §2b INERT-BY-MODE — the byte was on the car; the lever never acted

| lever | why | **status** |
|---|---|---|
| **V44 / V47 / V72's damper builds** | wrote modes **10/11**; the car is **TVCA4**, modes 24/25 manual, 26/27 engaged. V72's own probe: a rung that should have fired 100 % fired **0 of 87,940** | **INERT-BY-MODE** ⇒ *"damping is null"* on all three is UNINTERPRETABLE, not falsified |
| **V69 / V70's entire r24 dose ladder** | written to mode-10 `gain_B` ⇒ **byte-stock behaviour. THE LADDER NEVER EXISTED.** The recorded *"clean single-variable r24 series ×1→×2→×4"* was **three replications of ONE condition** | **INERT-BY-MODE** ⇒ r24's dose is **UNTESTED**, not near-inert |
| **V73's `0xCBE74` ×1.5** | mode 10 only — a **DISENGAGED** column | **INERT-BY-MODE.** Its clean flight says nothing, and the control meant to exonerate `0xC407E`=850 instead **implicates the friction row** |
| **V64** (`0xC6440`/`0xC643E`) | `0x14A` byte4 read a **constant `0x87` across all 14,980 frames** ⇒ `gp-0x6c2c` never crossed T=12800 | **INERT-BY-GATE** — a *solved* null (we know why) |
| **V67 / V68 (`gp-0x67df`)** | fired **0/186,321** (V67) and **0/53,991** (V68), straight through the 1468-ct 28 Hz burst. 🛑 **the cell has NEVER been non-zero on any build ⇒ NO POSITIVE CONTROL** | **INERT-BY-GATE, UNSOLVED** — a quiet car and a dead probe are indistinguishable |
| **`0x454FE`** (V42's macro-ratchet fix) | `gp-0x67fa`'s reachable set is effectively **{11} alone**: state 5 structurally dead, state 10 measured 0.0000 %, state 4 **0/123,277 while driving** | **MEASURED INERT.** Keep the byte (lost silently three times, costs nothing) but 🛑 **no build may be justified on it.** ⚠ This SUPERSEDES the note calling it *"a genuinely untested ratchet lever"* |

## §2c STRUCTURALLY-DEAD — it executed, and its output is zero or negligible where he lives

**These are the strongest kills in the record — structure, not nulls.**

| lever | why it cannot act |
|---|---|
| **base-assist damper on the STOCK surface** *(= what is on the car, §1b)* | `ch₀ = clamp((FactorC(speed) × FactorE(rate)) >> 10, ±ceiling)` — a **PRODUCT of two dead zones**: FactorC `Y[0]`=0 below **34.97 km/h**, FactorE `Y[0]`=0 below **12.7 °/s** ⇒ **exactly ZERO on 95.91 % of engaged frames, 100 % of the micro-ratcheting regime, 100 % of ratcheting at parking-lot speed** |
| **`0xC63A0` 1024→2048** | weights a product already zero at creep. Flew **FOUR times** (V72/V73/V76g/V81), measured inert ⊕ **V84's own revert of it was therefore also inert** |
| **FactorD** | FactorC multiplies in **FIRST** with `Y[0]`=0 below 34.97 km/h in all four of this car's modes. **Zero × anything = 0.** Three independent confirmations. 🛑 **This also REFUTES *"FactorD is the only frequency-selective lever"* — THIS FIRMWARE HAS NONE** |
| **`0xC6194`** (LKAS slew limiter) | REAL and calibrated — 3 ct/tick = 1.37 s full scale, *exactly the shape the operator described* — **but its input partition `0xC4118` is all-1 ⇒ 100 % of the request bypasses it.** 🛑 **Arming it goes the WRONG way.** ⚠ The record's stated reason *"output ×0"* is **WRONG** (that is `0xC6196`) — *a lever can be correctly filed DEAD for a reason that is itself false* |
| **`0xC6B12`** (PID Ki) | at 6–10 km/h the **P term alone** (16,000 at e=2000) exceeds the anti-windup bound (**7,264**) ⇒ the integrator is **pinned** |
| **`0xC616C` / term 0 (`gp-0x6b4a`)** | term 0's producer passes through `clamp(driver_torque, ±cal 0xC616C)` and **`0xC616C` = 0** on stock and every build ⇒ **both writer branches yield zero ⇒ TERM 0 IS IDENTICALLY ZERO** |
| **`gp-0x6b4e`** | provably ≡ 0 |
| **`0xC6B66`/`0xC6B80`** (13-pt LERP) | axis is **ABSOLUTE steering angle**, not a tracking error (the relation holds in MANUAL, where a tracking error is undefined); **88.6 % of engaged driving sits in its flat first segment** ⇒ a near-constant 0.878× broadband trim |
| **return-to-centre / detent** | `gp-0x6b62 ≠ 0` and the `gp-0x6bda` gate both **0.0000 over 75,227 engaged frames**, with an **855 s sustained (0,0) run**. Re-identified as a **RACK END-STOP CUSHION** (arms on `\|gp-0x6b98\| > 4096` **AND** motor rate `< 200` = a stall detector, **no angle term anywhere**). **~99.3 % dead in MANUAL too** ⇒ its absence cannot explain any engaged/manual difference |
| **`0xC520C`** (governor ceiling) | `gp-0x6ac0` = 4.7121 ct per °/s ⇒ first knot **222.8 °/s**; measured returns max 528 ct against a 1050 knot — **0.00 %** reach it |
| **`0xC63A4`** | its lane carries **~1.1 ct of a 342 ct signal** |
| **`0xC6372` / `0xC636E`** | a **DEAD BRANCH** — `tp+0x7498 = tp+0x7499 = 1`, byte-verified on stock and every build |
| **AUTH / `0xC67C8`** | β(log AUTH) = **−0.013 [−0.344, +0.319]** — CI **excludes** the predicted +1; and `gp-0x6b4c` is a **second LKAS route that never sees AUTH**. ⚠ the table header is `0xC67BE`; `0xC67C8` is its `Y[0]` |
| **`0xC64B8`** | at this car's mode **both arms deliver 0 everywhere the branch could fire**; stock and V37 are **bit-identical here — V37 removed nothing** |
| **`0xC6442` / `0xC61F6`** | 🛑 **written by 0 of 65 images.** The record's *"V39 \| FALSIFIED"* row is FALSE — V39's entire delta vs V38 is a 4-byte cave hook. `gp-0x671d` reads **0 / 402,424 frames** | **NEVER-TRIED, and mis-recorded as tested** |

## §2d UNINTERPRETABLE — flew, lever LIVE, the instrument failed. **Not falsified. Do not collapse these.**

⭐ **This is where the kit's recoverable value is hiding.**

| lever | why it could not be scored |
|---|---|
| 🛑🛑 **`0xC63AC` 102→150** — **V97, route `0x80`. DO NOT RE-DOSE. DO NOT FILE FALSIFIED.** | The lever is proven LIVE and **both of the operator's own hypotheses are REFUTED**: the address is excluded 3 ways (`0x38202` = `ld.hu 0x73ac[tp]`, census 1R/0W by **five** methods, Ghidra∖Python set-difference EMPTY), and the code is used (`FUN_00038148`'s sole caller guards it with a mask **byte-identical to the guard on the assist-channel mixer** ⇒ **a shut gate means NO POWER ASSIST AT ALL**; `sign(gp-0x374c)` toggled **181× in 109 s**). Three closing reasons, **none of them the lever**: (1) **NO INSTRUMENT** — V96's regressor was 34× over-range, `M ≡ 0` on 10,749/10,749; (2) **EXPOSURE** — 1 hands-off episode ≥2 s; (3) **THE OBSERVABLE** — 🛑 **DC gain is 1.000000 at any `A`: a POLE, not a GAIN ⇒ no amplitude statistic can see it, and none was pre-registered.** ⭐ V98's `b6`=0.4235 proves ACTUAL is a **load-bearing arm** ⇒ **the last structural excuse for its null is gone. It is the single clearest recoverable item in the kit — but ONLY WITH A PHASE OR GROUP-DELAY OBSERVABLE.** Re-dosing it blind is V97 again |
| **V96's S1/S2** (`f′`) | VOID by the same 34× over-range. Later closed *analytically*: the Stage-2 rescale is the IDENTITY, swing 1.000× |
| **V53's FOURFRAME2** | never transmitted — our own STRB/SSAM cave defect (STRB=0x80, SSAM=0). The predecessor FOURFRAME failed for a **different** reason (the CAN gateway is a **whitelist**: only `0x14A`/`0x18F`/`0x1AB` cross). **Two consecutive silent telemetry builds, two causes, the first masking the second** |
| **`0xC6446` as a *ratchet* lever** | the V88 handoff itself: *"the cross-build 6–9 Hz comparison inherits route 71's [0.18, 5.51] split-half null ⇒ it CANNOT RESOLVE a ratchet change under ~3–5×."* **"Unchanged" is not supported — "cannot resolve" is** |
| **`0xC4080` / `0xC63AE` / `0xC6200` / the PID gains** | **NEVER-TRIED** — see §3, each is prohibited or blocked, not untested-by-oversight |

## §2e The command-side levers — including the two that worked

| lever | what it is | result | status |
|---|---|---|---|
| ⭐ **Lever A** — `0x3AB76`/`0x3AC20` `sar 0xa→0x9` | a flat **2.000×** on **BOTH** rate lanes, at every speed and rate | **V62: 18–22 Hz 8× down at creep, 42× at 16–32 °/s.** Operator: ⭐ ***"Original grinding at 2–5 mph is gone!"*** — the kit's **first** measured fix | 🛑 **DO NOT RESTORE.** The `sar` is **UNGATED** ⇒ it reproduces V62/V65 in the **MANUAL** arm, and his V65 report on exactly that condition is *"makes the entire car vibrate, almost like I have a subwoofer… happens regardless of LKAS engagement."* ⚠ the int16-overflow leg of this argument is **WITHDRAWN**; the verdict stands on the manual-arm leg alone. **Off the car for 32 builds.** |
| ⭐ **Lever B** — `0x3AA96` `c5→fb` + `0xC6446` 512→5244 | switches r24's gate from a dead cell to `latActive`, and doubles the arm **while LKAS applies** | **V88, route `73`: 15–22 Hz delivered command 0.549 [0.407, 0.844]; 0.5–3 Hz authority 1.192 [0.780, 1.812] = NULL** (no authority cost). Operator: ⭐⭐ ***"grinding — fixed."*** ⊕ *"micro-ratcheting and ratcheting… the main remaining issues"* | **ON THE CAR, frozen 12 builds.** **UP is BLOCKED BY THE RAIL** — 2.0× (V88) = 1.50× hot-end margin, 2.5× = at the rail, **3.0× PINS = relay class**. **DOWN is DEMOTED** — the §5 argument for testing it down rested on rate-dependence, which the 235-block corpus **REFUTED** (`eng × log rate` band contrast **+0.022 [−0.070, +0.116]**) |
| `gain_A` rec0/rec1 LOWERED | — | Lever B's gate repoint makes `lp = latActive`, and the armed path at `0x3AB5E` **OVERWRITES `gain_A` with `[0xC6444]` = 512** ⇒ **V84 and V85 ALREADY deliver 512 engaged at every speed.** V84's own pre-registered experiment: **FAIL on V84, FAIL on V85** | **ENGAGED-INERT — already run, twice failed** |

★★ **Both measured fixes are rate-lane, MODE-PROOF, COMMAND-SIDE levers.
Every measured fix in this kit came from a mode-proof lever; every mode-indexed lever was inert.**

## §2f The one thread the damper partition leaves standing — and it is a SHAPE, not a dose

🛑 **A standing memory was REFUTED from the images and corrected in place** (V99 close-out). The claim
*"neither prior test ever had both dead zones open; FactorE `X[0]` is 60, not 12; 25 % authority at 10 °/s
is unreachable by moving X; it requires raising `Y[0]` off zero"* is **FALSE on all four counts.**

```
FactorE mode 26, read from every image
STOCK/V86b/V88..V100  X=[60, 400,2500,4000]  Y=[  0,140,539,927]   saturates 84.9 deg/s   <- ON THE CAR
V75                   X=[12, 200,2500,4000]  Y=[  0,539,539,927]   saturates 42.4 deg/s   FLOWN r5e
V76                   X=[ 0, 119,2500,4000]  Y=[  0,300,539,927]   saturates 25.3 deg/s   FLOWN r65
V79/V80               X=[ 0, 119,2500,4000]  Y=[  0,897,912,927]   saturates 25.3 deg/s   FLOWN r66
```
**NO flown build ever raised FactorE `Y[0]` off zero.** V80's relay came from a **STEEP RAMP SATURATING
AT 25.3 °/s**, not a step. ⇒ **the relay-ness is set by `X[1]`, not by `Y[0]`.**

| build | `X[1]` | saturates | relay index `N(50)/N(500)` | operator |
|---|---|---|---|---|
| **V75** | **200 ct** | **42.4 °/s** | **1.45** | ⭐ *"strongly attenuated the micro-ratcheting"* (then an unrelated `0xC407E`=850 fault) |
| V76 | 119 ct | 25.3 °/s | (k 1.39) | *"still grind #1 and micro-ratcheting at creep"* |
| **V80** | 119 ct | 25.3 °/s | **3.27** | ☠ *"worst grinding ever"* — **and 6–9 Hz 0.418 [0.33, 0.61], the only k-ladder point outside its null** |

🛑 **The non-monotonicity IS the finding: V76 delivered MORE damping below 3 °/s than V75 and he said
micro-ratcheting was still there; V75 delivered LESS at the bottom and he said it was strongly
attenuated.** The separator is **SHAPE** — V75 alone has a small rate deadband (`X[0]`=12 ct = 2.55 °/s)
followed by a **long linear ramp to 42 °/s**: the most viscous, least relay-like damper ever flown, and
the only one with a positive operator report on the target symptom. **[BELIEF, stated as a thread, not a
recommendation]** — two positives, two serious negatives (V80's grinding, V75's fault), **all four
confounded**, and going past 4 breakpoints is a **CODE edit to the always-on base-assist damper = the
V24/V27/V48B bricking class.**

---

# §3 — THE STANDING PROHIBITIONS, QUOTED VERBATIM WITH THEIR SOURCE

### `0xC4080` (K0) — **NEVER RAISE**
> *"`FRICTION += cal/1024 × ratio` with **no `|model|` factor** ⇒ a **latent PURE COULOMB RELAY**:
> amplitude-independent and unbounded in index"* — `BUILD-LINEAGE.md:496`
**VIRGIN on all 90 images** (this pass). It is one of three named *flatten-a-curve-into-a-relay* hazards.

### `0xC63AE` (Stage-2 input scale) — **never → 0, and NO-GO in either direction**
> *"the LERP index becomes ≡ 0 ⇒ output ≡ `±Y[0]`, a constant ⇒ **a pure relay at full authority**."*
> *"🛑🛑 `0xC63AE` IS NO-GO AS A V100 LEVER … RULE 7 **PASSES** here … **But the dose is a LEVEL shift,
> not an AC change**, and the **AC gain is NON-MONOTONE in scale and REVERSES SIGN across the operator's
> own amplitude distribution**: at scale 1536 the ratio is **0.773 at p10, 1.078 at p50, 1.277 at p90**.
> **1280 is arithmetically WORSE than stock.** A gain rising with amplitude is the hardening
> nonlinearity that sets up a limit cycle — **V80 class.**"* — `BUILD-LINEAGE.md:497`
🛑 **The NO-GO has TWO legs. V100's E3 endpoint tests only the FIRST (perceptual floor). Leg 2 — the
AC-gain sign reversal / hardening nonlinearity — is untouched by E3 and by any amplitude statistic.**
> *"A landmine catch: `docs/TRACE-2026-08-13-path2-authority.md` §6–7 was still actively recommending
> `0xC63AE` 1024→2048 as the LEAD V100 candidate when this was found… **Do not read that trace
> top-to-bottom and propose the cell — the corrections are in it, but read them.**"* — handoff §3

### `0xC6200` (the ±8192 clamp) — **never < `Y[0]`, and a BLOCKING FLAG on any edit**
> *"the clamp does the same thing from the other side."* — `BUILD-LINEAGE.md:498`
> *"**BLOCKING FLAG**: `0xC6200` must not be edited by any future build until `0x39ff6` is chased."*
> — handoff §4
> *"**Stop calling `0xC6200` 'gp-0x6b70's clamp' — it is FOUR distinct things**: the friction lane
> (6 sites), `gp-0x6b70`'s own output clamp (4), the Stage-2 LERP's `Y[9]` (1), and the PID reference
> clamp (3), plus `0x39ff6` unchased."* — `BUILD-LINEAGE.md:498`
> *"**GENERALISABLE LESSON** — every build script since V90 labelled this cell 'gp-0x6b70's clamp' (one
> of its four roles), and that mislabel is what kept the PID-reference role invisible for ten builds.
> A cal cell with multiple roles, labelled by only one, is a latent wrong answer."*
⊕ RULE 11's census on this cell is **now complete** (the three unknown readers are the PID clamp) —
except `0x39ff6`.

### `0xC616C` — **NEVER-RAISE**
> *"⚠ `0xC616C` is a standing **NEVER-RAISE** cell."* — `STATE.md:24`
It clamps the driver torque feeding term 0. **VIRGIN, N=90, value 0.**

### `0xC6CD0` (the 4× LKAS gain) — **never recommend lowering it**
> *"**MEASURED, multiple flights.** Never lower it — it is not the cause of any symptom, only the volume
> it's heard at."* — `_v100_arc_map.md` §2
> *"It scales **EXCITATION**, not loop gain. 🛑 **NEVER recommend lowering.**"* — `memory/MEMORY.md`
✅ **EXONERATED TWICE, 2026-08-13**: it does **not** reach term 0 (`FUN_0002b422` writes a literal zero
into field `+2` at `0x2b52a` while the 4× goes to field `+4`), and it is **not saturating** (its ceiling
went 512 → 2048, **exactly 4× with the gain**, and the next fixed clamp sits **5×** above). *"Extra
command buys no extra authority"* is **REFUTED.** Frozen 19 builds.

### `0xC40BC` — the standing "FREEZE at 6000" is **CONTRADICTED**
> *"🛑🛑 `STATE.md`'s standing 'FREEZE `0xC40BC` at 6000' is **CONTRADICTED** on the 6–9 Hz band… **The
> car is at 600 and that is the better value for ratcheting. Do not restore 6000.**"* — `STATE.md`
🛑 **And as of V99 the whole cell is closed at any dose. Do not propose it in either direction.**

### `0xC61F6` 3→0 (rate-lane deadband) — **DO NOT; it pushes the destabilising way**
> *"a deadband is the **DUAL of a relay**: `N(A) → 0` as `A → 0` is precisely what *prevents* harmonic
> balance from closing. **Deleting it ADDS small-signal gain.** ⚠ This **reverses** the E12 framing that
> opened it as a candidate."* — `BUILD-LINEAGE.md:486`

### `0xC61D6` (shaper slew step) — **ALREADY REJECTED, twice**
> *"an 11-round review labelled it 'highest-risk; last/never': it does **not** re-enable an anti-snap
> ramp, it **activates a dormant, uncalibrated speed × torque 2D map** onto the live command. ⇒ 🛑
> **There is NO usable cal-only rate-limiter lever on this path.** (This is the second time a subagent
> has re-proposed `0xC61D6`.)"* — `BUILD-LINEAGE.md:487`

### `0xC407E` — **DO-NOT-RAISE (RULE 11), and the most expensive lesson in the file**
> *"**A CLAMP MAY BE AN INTERLOCK. NEVER RAISE ONE WITHOUT FINDING ITS MONITOR.** … it cost two mid-drive
> total losses of power steering. Honda set that clamp to exactly ONE COUNT below the monitor's own trip
> threshold… **V73 raised `0xC407E` 511 → 850 and removed the interlock without knowing it was one.**
> V74 and V75 both hard-faulted with latched total loss of assist."* — `BUILD-LINEAGE.md:208-224`
⚠ Corollary: *"do not 'fix' this by raising `0xC4004` instead."* Currently **511 = stock, frozen 22 builds.**

### `0xC63A0` — **EXONERATED**, refuting the standing "do not double `0xC63A0`"
It weights `gp-0x6bd0`, **not** `gp-0x6b26` (that is `0xC63A6`). It flew at 2048 four times and measured
inert. The **fault** cell is `0xC407E`.

### `0xC618A` / `0xC627E` / `0xC63C0` (the relay-with-dwell in `FUN_00036388`) — **do not arm it**
> *"the snap flattens the one shaped curve in the lane into a constant — the FLATTEN-A-CURVE-INTO-A-RELAY
> class… and the lane is **dead engaged AND ~99.3 % dead in manual.**"* — `BUILD-LINEAGE.md:510-518`

### The authority-collapse curve (`0xE5284`/`E52FC`/`E5404`/`E547C`) — **safety is ASYMMETRIC**
> *"🛑 **NOT A 6–9 Hz LEVER — refuted five ways.** It targets the measured ~0.5–1 Hz SURGE, which **NO
> OPERATOR COMPLAINT IS ATTACHED TO.** 🛑🛑 **SAFETY IS ASYMMETRIC** — Honda collapses authority when the
> driver pushes hard; widening it makes the car **fight the driver harder and for longer.** Only a
> **MONOTONE-NON-INCREASING** reshape is defensible."* — `_v99_arc_map.md` D3.C1
⚠ He drives on its knee: curve `X[0]` = 2240 vs **measured median override torque 2235 — one count below.**

### 🛑 CODE CAVES ARE THE ONLY BRICKING CLASS
> *"**Three of this kit's code caves bricked the ECU: V24, V27, V48B.** Every success since V29 has been
> cal-only or a single in-place branch/displacement edit."* — `BUILD-LINEAGE.md:703-706`
Two mandatory gates for any cave, filter or dynamics change:
- **GATE 1 — RAM OWNERSHIP**, including writers and register-indirect access. *"static clearance is
  **not** sufficient — `gp-0x1500` passed both static methods and still failed on-car."*
- **GATE 2 — CLOSED-LOOP STABILITY**, **magnitude *and* phase**, in every loop the signal is in.
- **GATE 2 COROLLARY**: *"A flat `FactorC` sized so the supremum **equals** the ceiling clips 0.00 % and
  passes every no-clip guard, while delivering a constant 495 counts across a 34× rate range… **'does not
  clip' and 'is not a relay' are different statements, and only the first was ever checked.**"*
- **GATE 3 (probes)**: size a rung against **the LANE's own reachable output**, never a downstream or
  writer's clamp. V96 violated this and under-used its channel ~4× (34× over-range).
- **GATE 4 (probes)**: read the **GAIN IN FORCE / the selector**, not a lane output.
- ⚠ **`gp-0x6b94` ↔ `gp-0x4ce0` is a shadow-lockstep pair** (`FUN_00045a20` hard-shutdown monitor).
  **Reading is free; WRITING either half trips the monitor.** Binding on any future build that writes the
  aggregator output.

### RULES that gate a *proposal*, not just a build
- **RULE 3** — *"CONFIRMED does not mean STILL ON THE CAR."* Byte-check the current image first.
- **RULE 4** — *"attribute a lever to a build only from that build's own byte diff, never from prose.
  Two entries here were wrong, and both errors ran toward 'already tested.'"*
- **RULE 5** — *"a null is only a null if the lever was in force."*
- **RULE 6** — *"a lever is only in force if the car reads the TABLE you edited."*
- **RULE 7** — *"a lever is MODE-PROOF, or it is a bet."* This car is **TVCA4**, modes **24/25 manual,
  26/27 ENGAGED**. ⇒ **AND "FALSIFIED" MUST NAME THE SYMPTOM.**
- **RULE 8/8b** — evaluate a no-clip rule on the **observed envelope**, state which regimes it does NOT
  contain, and *"state the pass as a BOUND, never a proof."*
- **RULE 10** — *"'single-variable' is relative to the mode the car is actually in."*
- **RULE 11** — the interlock rule above. **RULE 12** — a table's shape is bounded by its **output clamp**,
  not its breakpoint count. **RULE 13** — trace a function's outputs **forward**; do not enumerate one
  cell's readers and stop.

---

# §4 — THE RETRACTIONS. Do not re-cite any of these.

| # | the retracted claim | what is true instead |
|---|---|---|
| 1 | *"Stock encodes an exact pole match and V97 broke it"* — the **0.111 / 0.136 / 0.151 "phantom"** | The cell identity is real and probably deliberate (`round(0.1·4096)=410`, Honda ships **408 = 4×102**) — **but it is a match between two STAGES, not the ARMS**, which do not share an input and are already **84° and 0.557-vs-0.906 apart at stock.** 🛑 **NEVER quote the phantom.** Survives: V97 moved the arms **further apart** (+7.82°, +5.4 %) |
| 2 | *"REQUEST is minor"* | `b5` tests REQUEST vs **ACTUAL**; the denominator is the **RESIDUAL** (`\|iVar6\|` p50 389 ct). This is the kit's own retracted "≤ 9 %" error, repeated. **REQUEST is the most important unmeasured term in the chain** |
| 3 | *"427 is broadband ⇒ no band-specific claim"* | An **artefact**: 427 is transmitted at 49.835 Hz and a ZOH images 5–15 Hz onto 35–45 Hz. With a valid **20–24 Hz** control, 6–9 Hz excess is **2.30× on 427 and 1.97× on column — they agree** |
| 4 | *"V86's `gp-0x67ab < 2` rung put the lever in force three ways"* | **The rung could NEVER have fired** — `< 2` is true of **both** states. The gate's openness is known **structurally** (`gp-0x67ab ≡ 0`, sticky-OR over roles {2,3,4}, `0xC4124` contains none of them, byte-identical across 65 images), **not** from V86 |
| 5 | **the "≤ 9 % share" bound** on Path 2 | 🛑 **INVALID — bounding one arm against the other's *admitted range* is invalid for a difference of correlated estimates.** The denominator is the **residual**, not the range. **Path-2's share is UNRESOLVED, not small** |
| 6 | **"+0.144, the rate axis is band-specific to the ratchet"** | **REFUTED by 2.4× the data**: `eng × log rate` band contrast **+0.022 [−0.070, +0.116]**. What grows with rate is the **EXCITATION**, present in every band. ⇒ **nothing argues for limiting the LKAS command's angle rate** |
| 7 | **the "2.09× → 21.17×" binned engaged/manual dose curve** | **Inflated by two confounds its own controls caught** (at 8–50 °/s the MANUAL arm carries ~9× the sustained column load; only 5 routes contribute, to *different* bins). 🛑 **Quote §1's model numbers (1.16× → 3.94×), never the 21×** |
| 8 | **"the 8.69 Hz line V56 introduced"** | It is **wheel order 1** — `0.489·v`. **No liveness conclusion may rest on it** |
| 9 | **"V84 fixed the highway ring"** | The operator, correcting the orchestrator twice: *"Not even sure what the ring is. We are working on grinding, vibrating, and ratcheting issues"*, then *"None of these have been fully fixed in V84."* A **band moving is not a symptom being fixed** |
| 10 | **"row says UNFLASHED after it flew"** | **SEVEN enumerated in the audit** (V83a, V84, nearly V85, V86, V86B, V89, V94/V96); V98's own heading records the **EIGHTH**; `BUILD-LINEAGE.md`'s V100 row states the kit has now shipped **TEN**. 🛑 The 7th **cost real work** — it sent the session's strongest analyst to close a verdict with *"fly V96, S2 answers it"* when V96 had already flown and its regressor was 34× over-range ⇒ **S1 and S2 are BOTH VOID** |
| 11 | *"the arms may be wildly unequal, so whichever you move the residual barely notices"* | **REFUTED by V98's comparator** — `b6` = 0.4235 ⇒ **MODEL ≈ ACTUAL.** V89 and V97 were both correctly *aimed*; their nulls are **DOSE or DIRECTION, not reach** |
| 12 | *"the engaged MODE RECORD read ≠ the record written" (V91/V92)* | **REFUTED in the same session it was written** — V73 probed the same index byte `gp+0x63fd` over 104,061 frames. ⚠ **The memory file's own `description:` frontmatter still asserts the refuted claim while its body refutes it, and `MEMORY.md`'s pointer repeats the stale version. A LIVE DEFECT IN THE RECALL LAYER** |
| 13 | *"gp-0x6b26 is apparent inertia, lowering is strictly safe"* (V93/V94's premise) | **BACKWARDS.** The delivered lane is **+137°/+139° vs wheel rate at 6–9 Hz ⇒ POSITIVE `Re(Z)` = a real damper.** ⊕ The desk figure *"+75°, 26 % dissipative, structurally cannot damp 6–9 Hz"* is also wrong and retired |
| 14 | *"neither prior test ever had both damper dead zones open"* + 3 companion claims | **FALSE on all four counts — FIVE builds had both open, THREE FLEW** (V75/V76/V80). See §2f |
| 15 | *"the plant model is structurally blind to rack position"* · the **1.67–1.82× desk steering ratio** | **REFUTED.** `FUN_0003b8f6` **does** read absolute steering angle (`0x3ba12`) and indexes a compensation table at `0xC6B64`. Measured over 47 routes / 427 min, four estimators: **16.9:1 near centre → 11.1:1 at lock**, swing 0–120° = **1.176 [1.147, 1.201]** vs the firmware's **1.206× ⇒ ADEQUATE.** ⭐ The rack is **SYMMETRIC** — an injected 2 % asymmetry **would** have been detected ⇒ a real ≥2 % asymmetry is **EXCLUDED** |
| 16 | *"the Stage-2 transfer cannot be read from the image"* · *"`f′` swings ≥10× and cannot be pinned statically"* | **FALSE — the rescale is the IDENTITY, swing 1.000×.** `gp-0x6982`/`gp-0x6984` have **ZERO writers image-wide** (four methods, with a working positive control) and both boot to 1024 |
| 17 | the **`R ≈ 387 ct` crossover framing** for φ · the anchor *"1.18, stable to 1.0 %"* | **STRUCK, not merely corrected.** Block-bootstrapped, the true rel s.e. on an absolute 6–9 Hz RMS is **24–29 %, not 3.7 %**; the two routes measured 231.2 / 225.1 — *"a coin flip, not a crossover."* The anchor is **`A = 1.13 ± 0.09`, a LOOSE cross-check**; rectification had inflated its apparent stability **~8×**. 🛑 **1.18 / "1.0 %" must not appear anywhere** |
| 18 | V98's *"0.4235 engaged vs 0.8041 manual"* headline | **Rate-confounded and overstated by ~22 %.** Matched on a 4\|rate\|×6 speed grid: **route 81 diff −0.2950 [−0.4099, −0.1727]**, route 82 **−0.3372 [−0.5354, −0.1895]**. The finding survives; **quote the matched figures** |
| 19 | V99's **E2** | **UNDERPOWERED — its null width (0.343) exceeds the entire 0.10 gap between the hypotheses it was built to separate. Its formal NULL is a power artefact. It is not evidence for anything** |
| 20 | *"~80 % of what you feel isn't gated on LKAS"* | **RETRACTED.** In his own regime (override vs manual-hands-on, grip matched both arms), 6–9 Hz **OVR/MAN-ON = 1.43…2.90×, 10 of 10 routes, 9 builds, median ~2.2×.** **An LKAS-gated lever is fully back on the table** |
| 21 | *"grind #2 is V62's `sar`"* | **REFUTED — V71C carries NEITHER `sar` byte and produced a spectrally identical 44.31 Hz event** (p99 1741.9 = 12.2× any non-bursting build). **Grind #2's origin is OPEN.** ⊕ The COROLLARY (*"check whether symptom X first appeared in the build that introduced the previous lever"*) is unaffected |
| 22 | Lever A's **int16-overflow-ceiling** leg | **WITHDRAWN** — `mul` writes a full 32-bit low word and `sar 0xa` operates on 32 bits, so `5120 × 5244 >> 9 = 52,440` fits. **Do not cite an r24 overflow ceiling.** The DO-NOT-RESTORE verdict stands on the manual-arm leg alone |
| 23 | *"a clean single-variable r24 series ⇒ r24 is near-inert"* | The ladder **never existed** (mode-10 `gain_B`). **r24's dose is UNTESTED, not near-inert** |
| 24 | *"task 5 = 100 Hz"* · *"the control task rate comes from OSTM0"* | Both retracted. **Task rate = 1000 Hz, EVIDENCE** (`0xC64DF`=100 measured on-car at 100.00 ms + the `0x830 ⊆ 0x930` lockstep). 🛑 **NOT from OSTM0**, which is 500 Hz because PCLK is 40 MHz — *"a recorded red herring an agent nearly shipped"* |
| 25 | the "**highway 40–49 Hz is wheel order 3**" veto | **RETIRED as an estimator tautology** — `order = f0·CIRC/v` returns ≈3.00 by arithmetic at band centre near 28 m/s; order 2's 1.995 has the same defect ⇒ *"one tautology counted twice"* |

⚠ **Two instrument facts that invalidate existing analyses, not retractions but the same weight:**
- **`carState.yawRate` is IDENTICALLY ZERO on this car** — 0 nonzero of 512,895 samples. Use
  `livePose.angularVelocityDevice.z` (**z-DOWN ⇒ negative on a LEFT turn**).
- **`vEgo` is INVALID as a speed reference for any rear-axle kinematic quantity at angle** — it runs
  **+7.9 %** fast at 250–400°, shaped like a flat plateau, and **produced a FALSE PASS of a positive
  control** before being caught. Use `(ws_rl + ws_rr)/2`.
- 🛑 **The `raw14` off-by-one is in EVERY cache** — pairing `t` with `raw14_b4` reads the cave byte ~10 ms
  early = **28° at 7.79 Hz.** Safe pairs: `(t, probe)` or `(raw14_t, raw14_b4)`.

---

# §5 — THE V101 SHORTLIST, AS A BRANCHING TREE ON THE FLIGHT RESULT

## §5.0 The three endpoints V100 pre-registered, and what each decides

| endpoint | measurand | pre-registered decision |
|---|---|---|
| **E1** | `d(b5)` = duty of `\|gp-0x6ad6\| ≥ cal(0xC6200)` = **the PID reference clamp**, engaged, **within-route absolute** | **HIGH (≥ 0.30)** ⇒ the whole V89→V100 arc's levers were discarded downstream by a saturation. **ZERO** ⇒ **"the reference-clamp hypothesis is DEAD and must not be re-proposed."** Resolvable window **[0.030, 0.970]**; needs **≥3 independent clamp EPISODES** to beat zero (rule of three on `n_eff`) |
| **E2** | **MARGINAL** `d(b6)` = duty of `\|gp-0x4f60 − gp-0x6ad6\| ≥ 10240` (RUNG D′, the error clamp) | `d(b5)=0.0000` **AND** `d(b6)=0.0000` with healthy controls ⇒ *"Neither saturation was active — Path-2's marginal authority was never zeroed by clipping."* **Closes the whole saturation family.** 🛑 **`d(b6)` UNCONDITIONED IS NOT THE ERROR CLAMP'S DUTY** — quote the 2×2 |
| **E3** | `Q = RMS₆₋₉(column torque, 0x18F) / RMS₆₋₉(SIGNED gp-0x6b94)`; `φ = 0.2565·A·Q`, `A = 1.13 ± 0.09` | `Q ≥ 1.39` ⇒ φ > 0.364 ⇒ delivered > 1.088 ⇒ **above the perceptual floor, the `0xC63AE` NO-GO's floor leg is overturned.** `Q ≤ 1.12` ⇒ the floor leg **stands**. **`\|Q − 1.254\| within ±11 % ⇒ INDETERMINATE, make NO verdict** |

🛑 **THREE CORRECTIONS TO THE BRIEF'S OWN FRAMING, each load-bearing:**
1. **Term 0 (`gp-0x6b4a`) is IDENTICALLY ZERO** and therefore **cannot be the source of any rail** — its
   producer passes through `clamp(driver_torque, ±cal 0xC616C)` and **`0xC616C` = 0** in stock and on every
   build. The handoff's *"term 0 rails the reference at 32 % of its own clamp"* (§4) was written **before**
   that finding and is superseded by `STATE.md`'s item 3. ⇒ **"the next lever must be `0xC6200` or term 0"
   collapses to "`0xC6200` or terms 1–6."** [EVIDENCE, `STATE.md:20-24`]
2. **`0xC6200` is under a BLOCKING FLAG until `0x39ff6` is chased**, and it is **four things at once** —
   editing it moves the friction lane, Path-2's output clamp, the Stage-2 LERP's `Y[9]` **and** the PID
   reference in one byte. **It is not a single-variable lever and must not be proposed as one.**
3. **`0xC63AE`'s NO-GO has two legs and E3 tests only one.** Overturning the perceptual-floor leg does
   **not** touch the AC-gain sign-reversal / hardening-nonlinearity leg (V80 class).

⇒ **Under E1 HIGH the honest next build is another INSTRUMENT, not a fix.** The terms that must supply
≥ 5,030 counts (61.4 %) of any rail are **terms 1–6, and none of them has ever been on the wire.** Naming
a lever before knowing which term rails the reference would be the V93/V94 mistake in a new place.

## §5.1 BRANCH A — **E1 HIGH — DEAD.** Recorded so the record shows it was considered.

`d(b5) = 0.000000` over 29,999 frames in all 8 rate bins, with `b6` also 0.000000 and the positive
control `b4` = 0.6057 **on the same cell as `b5`** ⇒ the load is live and the rung could see. **The
reference clamp never binds.** Everything this branch contained is therefore moot and **must not be
re-proposed**: **A1**, a comparator ranking terms 1–6 against `gp-0x6b70` (there is no rail to
attribute); **A2**, repointing the clamp's three reader sites (`0x3a7a2` family) off `0xC6200` onto a
virgin cal in the V57 `0x2A1F0`→`0xC6CD0` style (there is no hard zero to decouple); **A3**, raising
`0xC6200` (it moves four things at once and was blocked on `0x39ff6` anyway); **A4**, term 0 /
`0xC616C` (structurally dead + NEVER-RAISE); **A5**, "the upstream gains were discarded by a
saturation" (they were **delivered**, not discarded). ⇒ **`0.2565` stands unconditioned in the flown
regime**, and the saturation family is closed by the composite E2 sentence.
⚠ The one item worth carrying out of this branch: **RULE 11 on `gp-0x6ad6` — is there a monitor on that
cell? — is UNANSWERED in the record.** It binds anything that widens the reference (B1′ included).

## §5.2 BRANCH B — **E1 ZERO. ✅ THIS IS THE LIVE BRANCH** (`d(b5) = 0.000000`, `b4`/`b7` healthy)

**What it licenses, verbatim (pre-registered):** *"`gp-0x6ad6` never reached the PID's ±8192 clamp in any
engaged frame. Path 2's marginal authority was NOT zeroed by this saturation, `d(gp-0x6b94)/d(gp-0x6b70)
= 0.2565` stands in the flown regime, and the `f′`-compression account remains the only surviving
explanation for V89 and V97. **THE REFERENCE-CLAMP HYPOTHESIS IS DEAD AND MUST NOT BE RE-PROPOSED.**"*

**The surviving mechanism, stated exactly:** `f′`, the Stage-2 LERP's local slope, is a deterministic
function of `|iVar6|`, and the firmware **desensitises this lane 6.3× exactly when the driver pushes** —
which is how he provokes the symptom.

```
|iVar6| ct : 0-178  178-356  356-719  719-1200  1200-1800  1800-3000  3000-5000  5000-10681
f'         : 2.539   2.174    1.496    0.948      0.488      0.346      0.248       0.212
             ^ hands-OFF p50 188-337 ct                       ^ hands-ON p50 2,818-2,829 ct
             f' = 2.174                                        f' = 0.346
```
**V89 and V97 both argued their direction on hands-OFF data (the steep part) while the symptom lives on
the flat part.** Two independent masks agree to 2 %. [BELIEF — but it fits all the data and requires
nothing unmeasured.]

| # | candidate | new or re-run? | perceptual bracket | what the record says | verdict |
|---|---|---|---|---|---|
| **B1′** ⭐ | **Raise the Stage-2 LERP's interior Y-knots** so `f′` in his own regime rises toward the hands-off value | **GENUINELY NEW** — no build has ever written a Stage-2 knot | 🛑 **MY EARLIER SIZING IS RETRACTED — see §5.2c.** *"`Y[6]` 2546 → ~2887 gives `f′` 0.346 → 0.63 = 1.82×"* was computed on the **CREEP** knot set (0.0 / 6.6 km/h). `0xC669A`/`0xC66A8` **truncate the axis to 7,000 above 50 km/h**, and route `0x85` is 88.4 s ≥50 km/h. **The dose must be re-derived at the ≥50 km/h knot set.** The candidate stands; the number does not | 🛑 **BLOCKERS, all real:** (a) **the addresses are NOT pinned anywhere in the record** — the knots are quoted per-speed and per-mode, so this is a 2-D surface. **A tracer must pin them and classify RULE 7 first.** (b) **`Y[9]` of this LERP IS `0xC6200`** — do not touch the last knot. (c) **MODE-INDEXED = the kit's highest historical failure class.** (d) RULE 12 / GATE 2: a knot edit must not flatten a segment. (e) **RULE 11 unanswered — is there a monitor on `gp-0x6ad6`?** | ⏳ **STILL THE LEAD, BLOCKED PENDING A TRACER.** Do not propose it with unpinned addresses or a creep-derived dose |
| **B0** ⛔ | **The `gp-0x69aa` LERP on the PID reference** (`0xC6ABA..0xC6AC8` X / `0xC6ACA..0xC6AD8` Y, `mul`/`sar 0xa` at `0x38124`) — a scalar on the ENTIRE sum of terms into `gp-0x6ad6` | **NEVER-TRIED** — ✅ byte-verified by me across **all 91 images** (stock + 90 builds): header 8, Y `[1024]×8`, fallback `0xC6448` = 1024, **identical on every one** | **CANNOT BE PRICED** — `\|gp-0x6ad6\|`'s distribution has **never been measured** (V100 gave only its SIGN and one threshold at 8192) ⇒ sizing it is a **GATE-3 violation**, the V96 error in a new place | 🛑🛑 **KILLED ON THE AXIS IDENTITY. `gp-0x69aa` IS NOT VEHICLE SPEED** — it is a **Q15-normalised governor DERATE product, unity = `0x8000`**, MIN-only, seeded at unity, sole writer `0x45342` in `FUN_0004503c`. See §5.2b | ⛔ **NO-GO. Recoverable only as an instrument** |
| **B2** | **`0xC6468` (model output gain, 2639) UP** — scaling both arms scales `iVar6`, moving the operating point along the LERP | **GENUINELY NEW**, VIRGIN N=90 | 🛑 **FAILS THE BRACKET BY ARITHMETIC.** At x = 2829 ct: k=1 ⇒ `k·f′` = **0.346**; **k=2 ⇒ 5658 ct ⇒ f′ 0.212 ⇒ 0.423 = 1.22×** — well under the ~1.8× floor. k=0.5 ⇒ **0.71×** (wrong way). k≈4 lands on the 10681–14490 segment where `f′` = **1.036** ⇒ **4.14× = near-railing = relay class** | ⊕ Also: doubling both arms pushes them toward the **±20000 plausibility clamp** whose latch has **never fired** in 87,423 frames — a new failure mode for a 1.22× gain | ❌ **KILLED ON ARITHMETIC.** *(Recorded so it is not "discovered" as new next session.)* |
| **B3** | **`0xC63AC` BELOW 102** (lag instead of V97's lead), **with a phase/group-delay observable** | **"the same lever pushed the other way"** — a different claim from a new lever | unknown — **DC gain is 1.000000 at every value**, so **no amplitude statistic can ever see it** | ⭐ **It sits on a LOAD-BEARING arm** (V98's `b6` = 0.4235 removed the last structural excuse), and it *"has never once been scored."* 🛑 **But re-cutting it without a pre-registered phase or group-delay observable is V97 again**, and the record says so explicitly. **The instrument is the build, not the dose** | ⏳ **RECOVERABLE, INSTRUMENT-FIRST.** Never as a bare re-dose |
| **B4** | **`0xC63AE` 1024→2048** | NEVER-TRIED | **E3 decides the floor leg** (`Q ≥ 1.39` overturns it) | 🛑 **E3 CANNOT CLEAR LEG 2.** The AC gain **reverses sign across his own amplitude distribution** (0.773 p10 / 1.078 p50 / 1.277 p90) — a **hardening nonlinearity, V80 class** — and *"1280 is arithmetically WORSE than stock."* An amplitude endpoint is structurally incapable of testing that leg | ❌ **STAYS NO-GO even if E3 comes back high.** Report `Q` and its CI; make no verdict |
| **B5** | Anything on the **command side** (Lever A/B, `gain_A`, the rate lanes) | re-runs | — | Lever B **UP is rail-blocked**, **DOWN is demoted** (the rate-dependence that motivated it was refuted); Lever A is **DO-NOT-RESTORE** on the manual arm; `gain_A` lowered is **already run and twice failed** | ❌ **The command side is exhausted by the record** |
| **B6′** ⭐ | The **base-assist damper as a V75-shaped viscous ramp** (`X[1]`→200, long ramp to 42 °/s) | **"the same lever, a different SHAPE"** — the relay-ness is set by **`X[1]`, not `Y[0]`** (§2f) | V75 is the **only** flown damper with a positive operator report on micro-ratcheting | ⭐ **PROMOTED BY THE ROUTE-`0x85` OPERATING POINT (§5.2c): both of its dead zones are OPEN on this drive.** FactorC `X[0]` ≈ 35 km/h against **88.4 s ≥50 km/h**; FactorE `X[0]` ≈ 12.7 °/s against **51.3 s in 13–50 °/s + 14.8 s >50 °/s**. ✅ The surface is **byte-STOCK on V100 and on every build V87→V100** (verified this pass) ⇒ **single-variable is achievable.** ⚠ Two positives, two serious negatives, **all four confounded**. 🛑 **RULE 8b**: V75's fault was a **FAST TRANSIENT** and a clip rule is structurally blind to it | ⏳ **THE STRONGEST SURVIVING PLANT-SIDE THREAD, and the only candidate whose live-ness on THIS drive is established rather than assumed.** `0xC407E`=511 is what makes it re-testable at all |

## §5.2a 🛑 B1′ HARDENED — AND MY OWN SINGLE-KNOT PROPOSAL IS DEFECTIVE

**The check that mattered was the one I had not run: raising ONE interior Y knot changes the slope of
BOTH adjacent segments, in opposite directions.** Full `f′` tabulation across the entire X range
(mode 26, creep records; `f′` = `ΔY/ΔX` per segment):

```
seg   X range        STOCK f'   |  B1 AS I PROPOSED IT     |  B1' HARDENED
                                |  (Y[6] 2546 -> 2887)     |  (Y[6],Y[7],Y[8] += 341)
 0        0 -   178    2.5393   |   2.5393   1.000x        |   2.5393   1.000x
 1      178 -   356    2.1742   |   2.1742   1.000x        |   2.1742   1.000x   <- HANDS-OFF sits here
 2      356 -   719    1.4959   |   1.4959   1.000x        |   1.4959   1.000x
 3      719 -  1200    0.9480   |   0.9480   1.000x        |   0.9480   1.000x
 4     1200 -  1800    0.4883   |   0.4883   1.000x        |   0.4883   1.000x
 5     1800 -  3000    0.3458   |   0.6300   1.822x  <-TGT |   0.6300   1.822x   <- HANDS-ON sits here
 6     3000 -  5000    0.2485   |   0.0780   0.314x  <-!!! |   0.2485   1.000x
 7     5000 - 10681    0.2116   |   0.2116   1.000x        |   0.2116   1.000x
 8    10681 - 14490    1.0362   |   1.0362   1.000x        |   0.9467   0.914x   <- the only cost
```

🛑🛑 **THE SINGLE-KNOT EDIT I PROPOSED FLATTENS SEGMENT 6 BY 3.19× — 0.2485 → 0.0780 — producing a
2,000-count-wide near-dead segment immediately above the one it steepens.** The slope profile goes
`0.4883 → 0.6300 → 0.0780 → 0.2116`: a sharp local minimum, i.e. **a KINK, an amplitude-dependent gain
that rises then collapses 8× then rises again.**
⇒ **That is the SAME defect that makes `0xC63AE` NO-GO** (AC gain non-monotone in amplitude, reversing
across his own distribution). **My lead candidate, as first written, reproduces the failure mode I used
to kill someone else's. It is withdrawn in that form.** [EVIDENCE — arithmetic above, reproducible]
✅ Monotonicity is *not* the issue — Y stays increasing in both variants, and the tracer's finding that a
step is structurally impossible for a Y-knot edit is consistent with this. **Monotone-in-Y is not
monotone-in-SLOPE, and only the second one matters for a describing function.**

✅ **THE FIX IS A LEVEL SHIFT, NOT A SINGLE KNOT:** raise `Y[6]`, `Y[7]` **and** `Y[8]` by the same +341,
leaving `Y[9]` = 8192 pinned (**it IS `0xC6200` — it must not move**). Then:
- **segment 5 gets the full 1.822×** — the target, and the only segment that moves;
- **segments 6 and 7 are EXACTLY unchanged** (1.000×) — the kink is gone;
- **the entire cost lands in segment 8** at 0.914× (an 8.6 % flattening), **above |iVar6| = 10,681 — a
  region route 80 measured as beyond the reachable range at creep (max ~6,900)**;
- **hands-off cost is EXACTLY ZERO** — the hands-off operating point (|iVar6| p50 188–337 ct) sits in
  segment 1, which no variant touches. **The edit is surgical to the hands-on regime by construction.**

### 🛑🛑 BUT THE DOSE CANNOT BE SIZED FROM THIS DRIVE — and this is the session-killing error, caught
**Does the 2,829 ct hands-on median travel to route `0x85`? NO — and it cannot be rescued from data on
disk.** Three independent reasons:
1. **It is a route-81 CREEP figure.** `|iVar6|` is a residual of MODEL − ACTUAL; nothing licenses its
   median at 100 km/h equalling its median at 6 km/h.
2. **The knot set itself changes**: `0xC669A`/`0xC66A8` truncate the X axis to **7,000 above 50 km/h**,
   so the same `|iVar6|` maps to a *different* `f′` — the table above is the **creep** table.
3. 🛑 **`|iVar6|` IS NOT RECOVERABLE FROM ROUTE `0x85`.** The route-80 inversion worked because 427
   carried **`gp-0x6b70`**, which inverts through the LERP. **V100 repointed 427 to `gp-0x6b94`** ⇒
   neither `gp-0x6b70` nor `|iVar6|` is on the wire on this drive.
⇒ **B1′ is a blind dose at highway. It needs its own instrument pass first** (427 → `gp-0x6b70` at
mid-range/highway speeds), **or it is V97 again: a live lever aimed at an unmeasured operating point.**
⇒ **The dose stays RETRACTED.** The *form* (three-knot level shift) is settled and reusable; the
*magnitude* and *which of the 7 speed records to write* are not.
⚠ And note the tracer's report that the lever is **byte-identical ≥40 km/h** — if that holds, an edit to
the creep records is **inert on the 88.4 s of this drive above 50 km/h**, and the mid-range half of his
complaint needs the mid-range speed records dosed instead. **Those two facts have to be reconciled before
any cut.**

---

## §5.2b ⛔ THE `gp-0x69aa` LERP ON THE PID REFERENCE — VETTED AND KILLED, WITH THE REASON

The structure is real and correctly described (`TRACE-2026-08-13-v100-6ad6-and-ivar6.md:112-128`):
```
0x38124  mul r12,r10,r0    ; sum-of-terms × LERP(gp-0x69aa)
0x38128  sar 0xa,r10       ; >>10
         X 0xC6ABA..0xC6AC8 = [0, 6554, 13107, 19661, 22938, 26214, 29491, 32768]
         Y 0xC6ACA..0xC6AD8 = [1024]×8        ⇒ EXACT IDENTITY at stock, every knot
```
✅ **NEVER-TRIED confirmed independently** — byte-read across **all 91 images** (stock + 90 builds):
header 8, X and Y **identical on every one**, fallback `0xC6448` = 1024. Zero mentions in any build
script. `TRACE-2026-08-10-damping-axis-hunt.md:275` already recorded it: *"`0xC6ABA`/`0xC6ACA` mixer LERP
(flat) — **NO**, zero mentions, ever."*

🛑🛑 **BUT IT IS NOT A SPEED LERP, AND THE RECORD ALREADY CLOSED THIS — as a CORRECTION OF RECORD
against a prior brief that made the same assumption:**
> *"🛑 **The brief's identity for `gp-0x69aa` is wrong. It is not raw vehicle speed.** `read_memory
> 0xC6ABA,32` gives X = `[0, 6554, 13107, 19661, 22938, 26214, 29491, 32768]` = **0, 0.2, 0.4, 0.6, 0.7,
> 0.8, 0.9, 1.0 × 32768** — a **Q15-normalised 0…1 ratio**, gated `< 0x8001`. 32768 raw counts would be
> 512 km/h at 64 ct/km/h."* — `docs/TRACE-2026-08-10-damping-axis-hunt.md:257-260`

`gp-0x69aa` is a **Q15 MIN-only derate product, unity = `0x8000`, sole writer `0x45342`** in the G1
governor `FUN_0004503c` (`mulu` / `shr 0xf` / `st.h -0x69aa[gp]`, lead-decoded), meaning **"no derate
active"** — corroborated in three further places (`HANDOFF-2026-07-24-low-speed-steer-lockout.md:249-250`,
`memory/accord-low-speed-lockout-window-c62ea.md:38`, `memory/accord-fun45608-authority-slots-not-motoroff.md:45`).

**Four consequences, in order of severity:**
1. **The speed-shaping premise is gone.** It cannot be shaped by speed. The attraction of "the V69 shape
   done right" — dose at creep, exactly 1.000× at highway — **does not exist on this cell.**
2. 🛑 **Unity `0x8000` IS the top knot `X[7]`, and the derate is MIN-only seeded at unity ⇒ the index is
   PINNED AT THE TOP OF THE AXIS in normal driving.** So **`Y[0..6]` are INERT BY OPERATING POINT** and
   only `Y[7]` (`0xC6AD8`) and the `>0x8000` fallback `0xC6448` are live. **This is the FactorC/FactorD
   dead-zone class verbatim — and the axis misidentification is the same error that killed FactorD**
   (`gp-0x6a10` turned out to be absolute steering angle, not a tracking error).
3. ✅ **`gp-0x69aa == 0x8000` is CONFIRMED ON-CAR BY A WORKING POSITIVE CONTROL.** It is a **required
   conjunct of the same AND-chain** as the low-speed lockout, and **V53's `0xC62EA`→0 produced
   steer-to-zero on-car** ⇒ the chain passed ⇒ the conjunct held. [EVIDENCE at creep; **BELIEF at
   highway** — one rung `gp-0x69aa < 0x8000` settles it, and per R3 *a threshold on a
   STATIC/CONFIGURATION quantity is the safe class*.]
4. ⇒ **The candidate reduces to ONE FLAT SCALAR on the whole compensation bundle. Not a shaped lever.**

⚠ **Encoding hazard at the only live knot:** my byte read returns `X[7]` as **`0x8000` = −32768 SIGNED**,
which breaks monotonicity if the LERP reads X signed; and the record separately notes *"X[7] = 32768
exceeds the ±25600 validity ⇒ **top segment unreachable**"* (`TRACE-2026-08-10:140`). **The top of the
axis is degenerate in its own encoding, and the top of the axis is the only part that is live.**

### The four remaining questions, answered

**Does the gain-rescaling-invariance partition close it? — NO, and that is not how it dies.**
The partition eliminates downstream **absolute-count limits** as *causes*, because downstream stages
replay stock's exact count sequence under the rescaled PID. This LERP is a **linear gain**, not a count
limit, so the partition does not forbid it as a **lever**. What the partition *does* establish is that a
cell sitting at flat unity on all 91 images **cannot be the CAUSE of anything** — which was never the
claim. ⇒ **The partition kills it as a cause, not as a lever. The axis identity is what kills it.**

**New, or a re-run? — a RE-RUN of the V38–V52 authority/gain era in different clothing.** Once it
collapses to a flat scalar it is the same class as `0xC61B2`/`0xC61B4` (the arbitration/LKAS output
clamps, ×4 since V38) and `0xC646C`/`0xC6CD0`. Only its *position* is new — on the PID reference rather
than on the command. **Nothing has been stated that would make the result different this time.**

**Direction — the lever class argues against this cell's FORM, not for a direction on it.**
`b4` = **0.6057** ⇒ the reference is negative on **60.6 %** of engaged frames and positive on **39.4 %**.
A scalar amplifies **both signs**: it delivers "more of whatever the compensation bundle is already
doing, including on the 39 % of frames where it is doing the opposite." The record's conclusion —
*"THE LEVER CLASS IS MORE COLUMN FRICTION / DAMPING, NOT LESS COMMAND"* — calls for a **signed,
dissipative** term, not a **symmetric gain**.
⚠ **And one of that conclusion's two legs is now undermined by this very lineage:** the `0xC40BC`
"600 beats 6000 by 2.3×" line rests on a cell **V99 closed at any dose**, on a 3-route flag that
*"cannot be fully separated from V86's `0xC40D4`."* **The driver-grip leg (−0.655 vs a control's −0.266,
CIs disjoint) is independent and stands. The conclusion survives on one leg, not two.**

**GATE 2 — five recorded instances, and this is the real blocker.** On a mode with **ζ 0.017–0.036,
Q 14–29**, the loop's damping term dominates peak amplitude, and every recorded gain change on a term
carrying damping has gone the wrong way:

| build | the gain change | what it did |
|---|---|---|
| **V80** | damper `k` = 4.16 | 2.09× broadband HF lift **+ a sustained 27.4 Hz, Q ≈ 140 limit cycle no other build produces even once** |
| **V94** | removed 6/6ths of a real 6–9 Hz damper | ☠ **ABORTED.** Motor acceleration 3–7× up above 9 Hz; 18–31 Hz coherence the highest in the corpus |
| **V61** | rate lane | made it **worse**, and inverted the record: *"the rate lane is the mode's damper"* |
| **V71c** | `0xC6444` UP | ratchet at the **corpus record**, 8,521 ct p-p |
| **V83a** | — | the **worst build in the modern lineage** on both scored bands (grind #1 2.674×, micro-ratchet 1.526×) |

⇒ **A symmetric scalar on the whole compensation bundle moves damping AND stiffness together and cannot
be signed a priori. GATE 2 is not satisfiable by argument here** — which is exactly the position
`build_v80_tva.py` was in when it wrote *"V80 IS NOT CLEARED TO FLY"* and flew anyway.

### ⇒ RECOVERABLE ONLY AS AN INSTRUMENT — and it is a good one
**Repoint 427 to `gp-0x6ad6`** (measured `< 8192` on 100 % of 29,999 frames ⇒ the packer gives
`8192·5>>6 = 640` of 1023 ⇒ **no-clip by the lane's OWN clamp — GATE 3 satisfied, LSB 12.8 ct**) plus one
rung **`gp-0x69aa < 0x8000`**. That converts an unpriceable dose into a measured distribution for the
price of one displacement byte, and it is decidable from a single 15–30 s episode.

**The sentence a null will license:** *"427 carried `gp-0x6ad6` for a full symptomatic drive; its engaged
distribution is p50 X, p90 Y, max Z against the ±8192 clamp, and `gp-0x69aa` sat below unity on d % of
frames — so any future scalar on the PID reference can be sized against a measured lane instead of a
guess, and the derate-indexed LERP is [live / pinned]."*

---

## §5.2c — 🛑 THE OPERATING-POINT AUDIT: WHAT IS CREEP-ONLY, AND THE KILL IT RE-OPENS

Route `0x85` is **engaged p50 39.6 km/h, p90 99.6, max 104.5 — 88.4 s ≥50 km/h, 45.5 s ≥80 km/h.**
**Most of the arc's sizing was built at creep and does not describe this drive.**

| number | where it came from | travels to route `0x85`? |
|---|---|---|
| **The whole `f′`-compression table** (2.539 … 0.212) | mode-26 knots at **0.0 and 6.6 km/h** | 🛑 **NO.** `0xC669A`/`0xC66A8` truncate the Stage-2 X axis: X = `[0,640,1600,3200,5120,7680,12800]` ct = **[0,10,25,50,80,120,200] km/h**, Y = `[12000,10000,10000,7000,7000,7000,7000]` ⇒ **the axis caps at 7,000 above 50 km/h.** `STATE.md:371` already flags this |
| **My own B1 dose** (`Y[6]` 2546 → ~2887 for 1.82×) | derived from the creep knots above | 🛑 **RETRACTED FOR THIS DRIVE.** The candidate stands; **the number must be re-derived at the ≥50 km/h knot set** |
| **The hands-on / hands-off 6.3× `f′` compression** (\|iVar6\| p50 2,829 vs 188 ct) | route 81, creep | ⚠ **NO.** The **only surviving mechanism for V89 and V97 has been measured exclusively at creep** |
| **`\|iVar6\| ≤ ~6,900, p50 ~130`** | route 80, creep | ⚠ NO |
| **`0xC40BC`'s "93.1 % of hands-on frames above the 10.61 °/s knee"** | creep-dominated hands-on frames | ⚠ NO (moot — the cell is closed) |
| **The perceptual bracket** (0.55× felt / 1.09× not) | V88/V62 at creep; V85/V89 mixed | ⚠ mixed provenance — use it as a rough floor, not a precise boundary |

### 🛑🛑 THE KILL THAT RE-OPENS — the base-assist damper's death is a **CREEP** death

`ch₀ = clamp((FactorC(speed) × FactorE(rate)) >> 10, ±ceiling)`, and the two dead zones are
**FactorC `X[0]` = 2240 ct ≈ 35 km/h** and **FactorE `X[0]` = 60 ct ≈ 12.7 °/s.**

Route `0x85` exposure against those two thresholds:
```
speed:  >= 50 km/h  88.4 s   |  >= 80 km/h  45.5 s        <- FactorC's zone is OPEN
rate :  13-50 deg/s 51.3 s   |  > 50 deg/s  14.8 s        <- FactorE's zone is OPEN
        (micro 1-13 deg/s 102.7 s                          <- FactorE still shut here)
```
🛑🛑 **I OVERSTATED THIS IN MY FIRST TWO MESSAGES AND I AM CORRECTING IT HERE. "Both dead zones are
open ⇒ the damper is LIVE on route `0x85`" is TOO STRONG.** Computed from the **byte-stock V100 surface**
(`ch₀ = (FactorC(speed) × FactorE(rate)) >> 10`, mode 26, 64 ct/km/h, 4.7121 ct/(°/s)):

```
ch0, counts        |rate| ->    2     5    13    20    30    50   100   200 deg/s
   5 / 20 / 35 km/h          0.0   0.0   0.0   0.0   0.0   0.0   0.0   0.0     <- FactorC shut
  50 km/h  C=140.4           0.0   0.0   0.1   1.9   4.6   9.9  21.1  33.3
  60 km/h  C=234.0           0.0   0.0   0.1   3.2   7.7  16.5  35.1  55.5
  80 km/h  C=429.0           0.0   0.0   0.2   5.9  14.0  30.3  64.3 101.8
 100 km/h  C=588.7           0.0   0.0   0.3   8.1  19.3  41.6  88.3 139.7
 104.5 km/h C=624.6          0.0   0.0   0.3   8.6  20.4  44.1  93.6 148.3
                                   ^^^^^^^^^^ the MICRO bin (1-13 deg/s, 102.7 s, the LARGEST) is
                                              STILL EXACTLY ZERO AT EVERY SPEED
```
| operating point | `ch₀` | % of the 512 ceiling |
|---|---|---|
| **the MEDIAN engaged frame** (39.6 km/h × ~10 °/s) | **0.0 ct** | **0.00 %** |
| mid-range, brisk (60 × 30) | 7.7 ct | 1.50 % |
| highway, brisk (80 × 30) | 14.0 ct | 2.74 % |
| highway, macro (100 × 50) | 41.6 ct | 8.12 % |
| the extreme corner (104.5 × 100) | 93.6 ct | 18.29 % |

⇒ **THE PRECISE, DEFENSIBLE STATEMENT:** *the SPEED leg of the dead-zone kill IS opened by this drive
(FactorC is nonzero above 35 km/h, and 88.4 s sit there). **The RATE leg is NOT**: FactorE's `X[0]` =
12.7 °/s still zeroes the ENTIRE micro bin — 102.7 s, the largest — at every speed, including 104 km/h.
And where both zones are open the delivered dose is **1.5–8 % of ceiling**, reaching 18 % only at a
corner this drive barely visits.*
⇒ **The kill SURVIVES IN SUBSTANCE for the micro regime, which is the regime he names.** It is
**narrowed**, not overturned: *"zero on 100 % of the micro regime"* is still true on this drive; *"zero
on 95.91 % of engaged frames"* is a creep-route figure that does not transfer.
✅ What was live was **Honda's own surface** — FactorC/FactorE mode 26 are **byte-STOCK on V100 and on
every build V87→V100** (V86b excluded), verified this pass.
⇒ 🛑 **B6′ IS DEMOTED, NOT PROMOTED — on arithmetic, before his words are even considered.** My promotion
of it in §5.2 was based on "the zones are open" without pricing the surface. **Pricing it reverses the
call.** See §5.2d for the second, independent demotion.
🛑 V80's k-ladder falsification is untouched (grind #1 inert across k = 0.58 → 4.16; the only 6–9 Hz gain
sits at the same point that carries the HF penalty).

---

## §5.2d ⭐ THE OPERATOR'S NEW AXIS — `d(LKAS demand)/dt`, AND WHAT IT DOES TO THE SHORTLIST

> *"Slow parking lot creep **and mid-range**… I think it is **speed independent**, moreso has to do with
> **how harshly the LKAS demand is**. Let x := LKAS demand then the stuttering is worst when **dx/dt** is
> high."* — the operator, 2026-08-13

**Taken at face value, without fitting it to any candidate:**

**1. It DEMOTES B6′ a second time, independently of the arithmetic above.** `ch₀ = FactorC(SPEED) ×
FactorE(WHEEL RATE)` is gated on **the one axis he says is irrelevant** and on **a rate that is not the
rate he named**. And his account is of ONE phenomenon spanning creep *and* mid-range — a term that is
identically zero below 35 km/h **cannot address the creep half of it.** ⇒ **A speed-and-wheel-rate-gated
damper is structurally the wrong shape for this framing. B6′ does not survive it.**

**2. The corpus null does NOT cover him, and the record says why.** The 235-block result is
`eng × log |WHEEL rate|` band contrast **+0.022 [−0.070, +0.116]** — **wheel rate, a different quantity
from `d(LKAS demand)/dt`.** The retracted "+0.144" claim was also about wheel rate. **Nothing in the
corpus has ever regressed on a command derivative.** [EVIDENCE — the absence is real, I looked]

**3. ⭐⭐ THE ARC SUPPORTS HIS AXIS, AND THE SUPPORT IS THE STRONGEST EVIDENCE IN THE KIT.**

| result | what it says about a command-derivative axis |
|---|---|
| ⭐⭐ **V88** — the kit's second measured fix | **Lever B halved the DELIVERED COMMAND's 15–22 Hz content — 0.549 [0.407, 0.844] — with authority untouched (0.5–3 Hz 1.192 [0.780, 1.812] = NULL), and he called the grinding FIXED.** Halving high-frequency command content **is** attenuating `dx/dt`. **The kit's best result already acted on his axis** |
| ⭐ **V62** — the kit's first measured fix | `sar 0xa→0x9` on **both rate lanes** — a derivative-path gain. *"Original grinding at 2–5 mph is gone!"* |
| ⭐ **the ~28 Hz lane-change transient** | **DOSE-INDEPENDENT ⇒ "EXCITATION, not gain"**, and the excitation contrast is **ALC vs driver-commanded = 2.389 [1.453, 4.898]** — an automatic lane change **is** a high-`dx/dt` event. The closest relative in the record, and it points his way |
| ⚠ *"nothing argues for limiting the LKAS command's ANGLE RATE"* | **This was derived from the WHEEL-rate null and does not bind a command-derivative axis.** Its scope is narrower than its wording |

⇒ **BOTH of the kit's only two measured fixes are command-derivative-path levers.** That is a stronger
prior for his framing than anything the observer side has ever produced.

**4. 🛑🛑 AND IT PROMOTES A CELL THE RECORD FILED DEAD — `0xC6194`.**
> *"**REAL and calibrated** — 3 ct/tick = 1.37 s full scale, **exactly the shape the operator
> described** — but its input partition `0xC4118` is all-1, so **100 % of the request bypasses it.**"*

**`0xC6194` is a genuine slew limiter on the LKAS request — i.e. a literal `d(demand)/dt` limiter — and
it is dead only because of a partition byte.** If his axis holds, **this is the single most on-target
cell in the firmware**, and the kit has been walking past it because it was filed under a different
symptom framing.
🛑 **DO NOT PROPOSE IT YET — two things must be re-read first**, and I flag them rather than assume:
(a) the record's *"⚠ arming it goes the WRONG way"* — **the reason is not stated anywhere I could find,
and a lever can be correctly filed DEAD for a reason that is itself false** (this same cell already had
one wrong reason on file: *"output ×0"*, which is `0xC6196`); (b) `0xC4118`'s partition semantics and
whether arming it is cal-only or a code edit. **Both are tracer questions and neither is answered.**
⊕ Note the standing *"there is NO usable cal-only rate-limiter lever on this path"* is about **`0xC61D6`**
(a dormant 2-D map), **not** `0xC6194`. Do not let the two merge.

**5. What his axis does to the rest of the shortlist:** **B1′** and **B3** act on the observer residual,
which is fed by REQUEST (the LKAS aggregator output) — so they are **compatible** with his axis but do
not target it. **B0/B2/B4/B5** are unaffected (all already dead). ⇒ **If his axis holds, the ranking
becomes: `0xC6194`/`0xC4118` (pending the two re-reads) > B1′ > B3, and B6′ drops off.**
🛑 **SUPERSEDED IN PART by §5.2d-bis below — the corrected `dCMD/dt` result moves `0xC6194` DOWN, not up.**

### §5.2d-bis 🛑 THE `dCMD/dt` ANALYSIS WAS CORRECTED BY ITS OWN AUTHOR, AND IT CUTS BOTH WAYS
Control-band-free (the earlier "−0.018 null" was an artefact — the 20–24 Hz control sits **inside** V68's
18–28 Hz engaged-conditional band and over-subtracts), the partial is **positive in every band 2–44 Hz**,
floor ≈ **+0.09**, **6–9 Hz +0.124** against a **+0.224 peak at 2–5 Hz.**

✅ **CONFIRMS the "excitation, not gain" reading** — the same verdict the ~28 Hz lane-change transient
already carries.
🛑🛑 **BUT IT IS DOUBLE-EDGED, AND THE RECORD ALREADY NAMES THE TRAP:**
> *"**Spinning the wheel raises the WHOLE column spectrum**, so a rate slope alone can never separate
> firmware from driver. **Only the engaged-vs-manual INTERACTION does.**"*

**A broadband-positive partial peaking at 2–5 Hz is exactly that signature.** 6–9 Hz (+0.124) sits
**BELOW** the 2–5 Hz peak (+0.224) ⇒ **the band contrast against a low-frequency reference is NEGATIVE —
there is no resonance selectivity on this axis.** ⇒ *"Harder command ⇒ more of everything"* is a
**DRIVER/EXCITATION** statement, not evidence of a firmware gain to turn down.
⇒ 🛑 **THE MISSING CONTROL IS THE ENGAGED-vs-MANUAL INTERACTION ON `dCMD/dt`** — the same control that
rescued the 235-block corpus from the identical artefact. **Until it is run, a positive partial does not
license a command-path lever.**
⭐ **SYNTHESIS FOR V101: if the command's effect is EXCITATION, attenuating the command is not the lever —
the lever is the loop's RESPONSE to it.** That **undercuts the `0xC6194`/`0xC4118` line** (already a hard
NEVER-ARM on independent grounds) **and STRENGTHENS the PID gain family (§5.2g), which IS the response
controller.** [BELIEF — but it fits both the corrected partial and the ~28 Hz precedent.]

### §5.2d-ter ⭐⭐ UNDER-RATED — a ±102 DEADBAND **+ a SIGN-CONSISTENCY GATE WITH STATE** (`gp-0x6b30`) on the LIVE COMMAND PATH
Reported by a tracer, **virgin**, and 🛑 **its July elimination was ANALYTICAL, NOT A FLIGHT RESULT.**
The ±102 is almost certainly **`0xC61B8`**, which my §1b matrix independently carries at **N = 90, value
102, VIRGIN, "pre-gain deadband"**, and which `memory/reference-accord-pregain-deadband-c61b8.md` files
**ELIMINATED** on the reasoning *"polarity `gp-0x6752` cannot chatter."*

🛑 **Three reasons it deserves its own vet before V101 is ranked. I have NOT traced it and am not claiming
it — but on the arc it is the strongest structural match to his symptom yet named:**
1. ⭐ **It is not a plain deadband — the sign-consistency gate carries STATE.**
   🛑🛑 **CORRECTED BY THE TRACER, FROM THE CODE, 2026-08-13 — AND THE CORRECTION IS TO ME.** I called it
   a **HYSTERESIS** and argued *"a phase LAG that GROWS as amplitude FALLS."* **That is WRONG.** The block
   **never outputs a lagged input — it outputs the input, or EXACTLY ZERO, latched** ⇒ it is a
   **LATCHING KILLSWITCH, not backlash.** **The growing-lag describing function does NOT transfer and must
   not be quoted.** ✅ The instinct that it was not a plain deadband was right; **the name was wrong.**
   ⭐ **What the correct reading buys instead — and it generalises:** a latching **zero-output dropout** is
   the **same structural class as the `gp-0x6ad4` dropout relay `gate2-pid` has just found** on the
   aggregator (`0x3acbc`/`0x3acc4`). ⇒ **This firmware uses latching zero-output dropouts as a DESIGN
   IDIOM, in at least two places.** Consequences: **(a)** the *"flatten a curve into a relay"* hazard list
   should carry **dropouts** alongside clamps and steps; **(b)** 🛑 **GATE 3 sizing must check whether a
   lane has a DROPOUT, not only a clamp — a dropout is invisible to every no-clip rule the kit runs**,
   which is the V80 lesson (*"'does not clip' and 'is not a relay' are different statements"*) in a new
   form. **This is the durable finding from the whole hysteresis line, and it survives the candidate's
   death.**
2. ⭐ **Amplitude-dependent lag that worsens at small amplitude is the textbook generator of
   micro-ratcheting / stick-slip** — the symptom **nothing in 60 builds has moved** — and it sits on the
   **LIVE COMMAND PATH**, i.e. his own axis.
3. 🛑 **The elimination was analytical and never flown.** Named failure class: *"a lever can be correctly
   filed DEAD for a reason that is itself FALSE"* (`0xC6194`'s recorded reason was `0xC6196`'s), plus
   I1/I2/I3 — *"a verdict without a named symptom is not a verdict."* **The recorded reason addresses
   CHATTER; the mechanism now described is HYSTERESIS LAG. Different mechanism, so the elimination does
   not reach it.**

⚠ **What I am NOT saying: that it should be edited.** Removing a deadband pushes the destabilising way
(`0xC61F6` precedent), and removing a *hysteresis* is a **GATE-2 question with a sign nobody has.**
⇒ **Vet it the same four ways the speed LERP and the PID family were vetted, before it is ranked.**

---

## §5.2e ⭐⭐ THE V101 PAYLOAD SPEC — the instrument, designed first

🛑 **This is a SPEC, not a build. No build script, nothing cut.**

### The design decision that shapes everything: **HIS AXIS IS ALREADY FREE ON THE WIRE**
The standing rule is explicit: *"the operator reasons from steering angle, driver torque and LKAS
demand — **ALL ALREADY FREE ON THE WIRE.** Cave bits must **COMPLETE** that picture, not duplicate it."*
**`d(LKAS demand)/dt` is computable off-line from `0x0E4`**, which is in `sendcan` src1 and carries
usable bandwidth (V84 measured 25–30 Hz content at rms 45.8 ct on it).
⇒ 🛑 **DO NOT SPEND A CAVE BIT MEASURING `dCMD/dt`. It is free.** Spend the bits on **the internal
quantity that must be CONDITIONED on it** — the analyst then builds the conditional duty off-line at
zero build cost (D6.2 rows 4/5: *conditional duty — bit X given a bus quantity*).
⭐ **This converts the highest-value question in the build from an expensive in-ECU derivative — which
would need a new cave-owned RAM cell and therefore a NEW GATE-1 LIVENESS CLAIM on the only bricking
class in the kit — into a free off-line join.**

### The payload

| bit | measurand | form | τ class | est. B |
|---|---|---|---|---|
| **b7** | `gp-0x6ad6 < 0` | single-operand **SIGN** — mandatory partner for the 427 lane | 0.03–0.05 s | 10 |
| **b6** ⭐ | `\|gp-0x6bfa\| ≥ \|gp-0x374c>>4\|` — **REQUEST vs ACTUAL**, V98's `b5` rung **byte-identical** | **COMPARATOR** | — | 30 |
| **b5** ⭐⭐ | ~~`\|gp-0x6bfa\| ≥ \|gp-0x6bfe\|` REQUEST vs MODEL~~ → **SUPERSEDED by §5.2f: `gp-0x69a4 ≥ 868`, the LEVER-B PARITY RUNG** | threshold on a **DERIVED** boundary | — | 10 |
| **b4** | `gp-0x67ab == 1` | threshold on a **STATIC/CONFIGURATION** quantity ⇒ the **R3 SAFE** threshold class | near-constant | 10 |
| **b3** | **IDENTITY — unconditional constant 0** (V100 is constant **1**) | constant | — | 0 |
| byte7[7:6] | **2**, carried from V98/V99/V100 | constant block | — | 18 |
| — | merge/shl PASS1+PASS2 + RET | — | — | ~36 |
| | | | **TOTAL** | **≈114 B** (revised, §5.2f) |

**Budget: 114 B against V100's 132 B and V98's PROVEN 154 B, on a 1,212 B extent (11.1 %).** Fits with
margin. Store set stays `{gp-0x1514, gp-0x1511}`; registers `{r6, r7}` only.
⚠ **Buildability, per the standing note:** a comparator is two-operand and the flown caves use `r6`/`r7`
with single-operand rungs ⇒ **recompute the operand inside each rung (+~20 B, already in the 30 B
figures). Do NOT claim a third scratch register — that is a new liveness claim.**

### The 427 magnitude lane — `0x1AB` ← `gp-0x6ad6`
- **Edit 1:** `0x55DF2` `hw2` displacement → `-0x6ad6` = **`0x952A`**. ⚠ **This is a TWO-byte diff, not
  one** — V100's one-byte diff was a coincidence (`-0x6b70`=`0x9490` and `-0x6b94`=`0x946C` share the
  high byte `0x94`; `0x95` does not). **Do not carry over "the repoint is one byte."**
- **Edit 2 — REQUIRED, and it is a GATE-3 fix:** `0x55E10` `sar 6` (`0xA6`) → **`sar 7` (`0xA7`)**.
  Packer is `clamp(|X|·5 >> N, 0, 0x3FF)`. `gp-0x6ad6`'s **own writer clamp is ±25600**, so at `sar 6`
  the max code is `25600·5>>6 = 2000` — **it WOULD SATURATE, a GATE-3 violation.** At `sar 7`:
  `128000>>7 = 1000 ≤ 1023` ⇒ **no-clip by the lane's OWN clamp, exactly as V100 did for `gp-0x6b94`.**
  **LSB = 25.6 counts.** ⊕ The `0xA{N}` encoding is EVIDENCE from the lineage: stock `a3`=sar 3, V92
  `a4`, V94 `a1`, V96+ `a6`.
- 🛑 **Do not size on the measured `< 8192`.** That bound comes from `b5` being a threshold at exactly
  8192; it is a demonstrated envelope, not the structural one. RULE 8b: *state a pass as a BOUND, never
  a proof.* Choosing `sar 6` for the extra 2× resolution buys LSB 12.8 but reintroduces a **1023
  sentinel that is ambiguous against the plausibility-latch tell already in the record.** Take `sar 7`.
- **The sign bit is not optional.** The rectification price is **cell-specific** — 4.1–5.2× on
  `gp-0x6b70` but **1.11×** on `gp-0x6b94` — so it must be **derived for `gp-0x6ad6`, not imported.**
  The one datum we have: `b4` (its sign) duty **0.6057** ⇒ the lane is **not zero-mean**, it sits
  negative ~61 % of the time, which usually makes rectification *cheaper* than on a zero-mean lane.
  **But that is an inference. `b7` costs 10 B and removes the guess. Ship it.**

### 🛑 THE SENTENCE A NULL LICENSES — for every bit. *(If it were "we would not be able to tell", the bit would not be here.)*

- **b6 — the highest-value bit in the build.** *"The LKAS REQUEST arm remains the smallest of the three
  observer arms even on the frames of highest `d(LKAS demand)/dt`, so 'the stutter tracks command
  harshness' does NOT act by swelling the REQUEST arm of the disturbance observer — if his axis is
  right, the mechanism is downstream of the observer."* ⭐ **Positive control comes free from prior
  data: V98 measured this exact rung at 0.0000 over 6,591 engaged frames at CREEP. Route 81 IS the
  control; a non-zero duty at mid-range/highway is the finding.**
- **b5.** *"REQUEST is smaller than MODEL as well as ACTUAL on d % of frames; with b6 the three observer
  arms are fully RANKED per frame at mid-range and highway for the first time, and REQUEST is confirmed
  the minor arm outside creep."*
- **b4.** *"`gp-0x67ab` is never 1 across 249 s of engaged driving, so the terms-1–7 block is never
  dropped and the PID reference never vanishes — the `gp-0x67ab ≡ 0 STRUCTURALLY` claim is confirmed
  DYNAMICALLY and can stop being carried as a structural assumption."* A non-zero duty is a major
  finding: **term 0 is identically zero, so a dropped block means the reference vanishes entirely.**
- **b7.** *"`gp-0x6ad6` does not change sign in engaged driving, so the 427 lane is an unsigned level and
  no phase or coherence claim may be made from it."* (Expected FALSE — `b4` already measured 0.6057.)
- **427.** *"`gp-0x6ad6`'s engaged distribution is p50 X / p90 Y / max Z at 0.000 % saturation, so any
  future scalar or knot edit on the PID reference can be sized against a MEASURED lane instead of a
  guess."* **Failure sentence, pre-registered:** *"if 427 reads ≡ 0 or pins at 1023, the repoint or the
  shift is wrong and NO sizing claim may be made from this drive."*

### 🛑 IDENTITY — and it is the weakest part of this spec, stated plainly
**byte7[7:6] IS EXHAUSTED as an identity field**: V96/V97 burn {1,3}, V98/V99/V100 burn {2}, and 0 means
"≤ V91". ⇒ V101's identity must be **composite**: `byte7[7:6] = 2` (excludes ≤V91 structurally) **AND
`b3 ≡ 0`** (V100 is `b3 ≡ 1`) **AND `b5` non-constant** (V99 is `b5 ≡ 1`). That is single-frame
separable from V99 and V100 — **but it is a composite, not a single positive constant, and a composite
is what let V96 and V97 become inseparable.**
⇒ 🛑 **The ≥3-bit identity-field build (X2) is now OVERDUE.** The record already prescribes it *"as its
own build, never combined with a new measurement class — that is how V24/V27/V48B bricked ECUs."*
**Do not fold it into V101.**

### What the ANALYST does off-line — free, no bytes
1. Compute `dCMD/dt` from `0x0E4` and stratify **every** bit on it. 2. Report the **joint 2×2×2**
`(b6, b5, b4)` and the marginals — *the marginal is reportable at full n regardless of where any
conditional lands.* 3. Report `gp-0x6ad6`'s distribution from 427, signed via `b7`. 4. Use the
**within-drive LKAS-off arm** as the control. 🛑 **Report the marginal AND say which is which** — an
unconditioned duty is not the conditional a downstream claim needs.

### Drive protocol
**One drive, engaged, stop when the symptom is felt.** Because his axis is command-harshness, the drive
should include the conditions that produce high `d(LKAS demand)/dt` — **curves and lane changes at the
speeds where he feels it, creep AND mid-range** — plus the **mandatory within-drive LKAS-off arm**.
⚠ **Route 85's 249.2 s is not a new floor to design against.** One good drive is not a protocol; he
still stops when he feels the symptom, and **that remains correct behaviour, not a shortfall.**

---

## §5.2f ⭐⭐ HOW DID V88 DO IT? — the record HAS an answer, and it CONTRADICTS ITSELF on one number

### (1) What "the delivered command" actually was — `gp-0x6b98`, the LOOP'S OUTPUT
V87 repointed the cave source to **`gp-0x6b98`** and V88 carried it (`ARC-AUDIT-2026-08-10:139-140`).
`gp-0x6b98` is the **TOTAL MOTOR COMMAND at the end of the chain** —
`gp-0x6b94 → governor → gp-0x6ace → comp-add → gp-0x6acc → shaper → gp-0x6b08 → gp-0x6b98 → FOC` —
and the record states plainly that it is *"the TOTAL motor command, **base assist included**, and base
assist is a function of column torque."*
🛑 **So "V88 halved the delivered command" does NOT mean "V88 attenuated the LKAS demand."** It means
**the motor command's HF content halved.** ⇒ **There is NO undrawn coupling to find: the rate lanes sum
into the aggregator, which is upstream of `gp-0x6b98` by four hops. It is the same node, by
arithmetic.** The 0.5–3 Hz null (1.192 [0.780, 1.812]) is what says the *LKAS* command was untouched.

### (2) The mechanism IS in the record — and it is the naive intuition INVERTED
The V88 scoring agent predicted a RISE and was refuted, and wrote up why
(`memory/accord-v88-flew-grinding-fixed-command-intact.md`):
> *"I predicted 15–22 Hz would **RISE**, reasoning that r24 is a differentiator and Lever B doubles its
> gain. **Wrong: r24 is rate FEEDBACK inside the loop, and `gp-0x6b98` is the loop's OUTPUT, not its
> input. More derivative feedback = more damping = LESS HF motion everywhere inside the loop.**"*

Supporting evidence, independent of the prediction: V87's engaged spectrum **rises** with frequency
(29 / 29 / **52** ct rms) against a **flat manual arm (~9)** — *"the signature of an **under-damped
closed loop at stock derivative gain**, not of a feedforward differentiator."*
⇒ ✅ **The paradox in the brief dissolves: "a bigger gain on a differentiator should raise HF" is a
FEEDFORWARD intuition. r24 is FEEDBACK.**

### (3) 🛑🛑 BUT TWO [EVIDENCE]-TAGGED ACCOUNTS IN THE RECORD CONTRADICT EACH OTHER, AND NOBODY HAS RECONCILED THEM
`memory/accord-r24-r26-two-selectors-one-gate.md` establishes, from the disassembly, that **the single
gate byte `0x3AA96` does TWO things at once**:
```
r26 -> gain_A : 0x3AB5E takes 0xC6444 = 512   when lp != 0   (else gain_A's own LERP = 3072)  => r26 CUT 6.00x
r24 -> gain_B : 0x3AC08 takes 0xC6446 = 5244  when lp != 0                                     => r24 RAISED ~10.2x
NET vs stock  = (5244 + 512a) / (3072 + 3072a),   a = gp-0x69a4/1024
                a = 0     -> 1.707x        a = 0.848 -> 1.000x PARITY        a > 0.848 -> BELOW STOCK
```
- **Account A** (the V88 memory): *more derivative feedback ⇒ more damping ⇒ less HF.* **Requires the
  NET derivative gain to have gone UP.**
- **Account B** (the two-selectors memory): the same byte **cuts r26 6× while raising r24**, and the net
  is **BELOW stock whenever `a > 0.848`.**

⭐⭐ **THEY CANNOT BOTH BE RIGHT, AND THE WHOLE THING TURNS ON ONE NUMBER THAT HAS NEVER BEEN
MEASURED: `a = gp-0x69a4/1024`.**
- `a < 0.848` ⇒ net feedback rose (≤ 1.707×) ⇒ **Account A holds, V88 and V62 share ONE mechanism.**
- `a > 0.848` ⇒ net feedback FELL ⇒ **Account A is wrong**, and the kit's best result is unexplained.

### (4) Cross-check against V62 — and the record's own flagged open question
**V62** = `sar 0xa→0x9` on **BOTH** lanes = a flat **×2.000 on r24 AND r26**, ungated, every speed and
rate ⇒ **net derivative feedback unambiguously UP.** Account A predicts improvement. ✓ It improved.
**V88** = r24 up, r26 down ⇒ **net ambiguous, sign unknown.**
⇒ **V62 and V88 CAN share a mechanism — but ONLY if `a < 0.848` on the flown routes.**
🛑 And the record already carries the alternative, verbatim, as its **leading open question**:
> *"⚠⚠ **CARRY THIS UNEXPLAINED — do not smooth it.** r26 ×2 (V62/V65) **AND** r26 ÷6.00 (V67/V68)
> **BOTH HELPED, and ÷6 helped MORE** (168 vs 109 against stock's 879). A monotone 'more r26 damping is
> better' story and a monotone 'less is better' story are **both refuted by the same two rows.** The
> corpus cannot say why, and that is the leading open question."*
⊕ Consistent with the standing **"2× ≈ OPTIMUM, not a point on a ramp"** warning on V62: a lane feeding a
lightly-damped mode has a damping **optimum**, not a monotone gain effect. [BELIEF — and if the stock
value sits near a local *worst*, moving either way improves it, which would explain both rows with one
mechanism. **Untested: there is no phase measurement on these lanes anywhere in the record.**]

### (5) ⚠ ADVERSARIAL — the honest verdict
**V88's mechanism is PARTLY understood and CANNOT currently be re-aimed:**
- ✅ The **coupling** is understood and is plain arithmetic — the lanes sum into the measured node.
- ✅ A **mechanism** exists (derivative feedback ⇒ damping) and it inverts the naive intuition correctly.
- 🛑 The **SIGN OF THE NET DOSE IS UNKNOWN**, because `gp-0x69a4` has never been measured.
- 🛑 **UP is rail-blocked** (3.0× PINS = relay class), **DOWN is demoted**, and the record's own two rows
  say **both directions have helped before.**
⇒ **The kit's best result is NOT reproducible on demand, and V101 must not pretend otherwise.**
⭐ **But it is ONE RUNG AWAY from being reproducible on demand** — and that is the most actionable thing
in this file.
🛑 ⚠ **RECORD DEFECT, live:** `accord-r24-r26-two-selectors-one-gate.md`'s headline (*"there IS a clean
single-variable r24 series and it says r24 is NEAR-INERT"*) was **VOIDED by RULE 7** — that ladder was
mode-10 `gain_B` and **never existed**; the correct reading is *"r24's dose is UNTESTED."* **Its
STRUCTURAL findings (the shared gate, the net formula, gain_A byte-identical across 11 images, the
separate RAM) are byte facts and survive.** `memory/MEMORY.md`'s index line still repeats the voided
headline — **same defect shape as the `cbe74` frontmatter, and it needs the same fix.**

### ⇒ THE CONSEQUENCE FOR THE PAYLOAD: swap one bit
**`b5` becomes the Lever-B parity rung.** Dropping REQUEST-vs-MODEL (the third triangle edge, incremental
— V98 already ranked two of three) costs little; adding `a` **unblocks the only reproducible fix the kit
has.** A single-operand threshold is ~10 B against a comparator's 30 B, so the payload **shrinks to
≈114 B** — tighter than V100's 132 B.

| bit | measurand | form | est. B |
|---|---|---|---|
| **b7** | `gp-0x6ad6 < 0` | SIGN, mandatory partner for 427 | 10 |
| **b6** ⭐ | `\|gp-0x6bfa\| ≥ \|gp-0x374c>>4\|` — REQUEST vs ACTUAL, **V98's rung byte-identical** | COMPARATOR | 30 |
| **b5** ⭐⭐ | **`gp-0x69a4 ≥ 868`** — the **LEVER-B PARITY RUNG** (868 = 0.848 × 1024) | threshold on a **DERIVED boundary**, not a guessed one | 10 |
| **b4** | `gp-0x67ab == 1` | threshold, **R3 SAFE class** (static/config) | 10 |
| **b3** | IDENTITY, constant **0** (V100 is constant 1) | constant | 0 |
| byte7[7:6] | 2, carried | constant block | 18 |
| — | merge/shl + RET | — | ~36 |
| | | **TOTAL** | **≈114 B** |

**`b5`'s null sentence, pre-registered:** *"`a` sits below 0.848 on d % of engaged frames, so Lever B's
net rate-lane dose was **[above / below] stock parity** on the drive that produced the kit's only
reproducible fix — which **[confirms / refutes]** the derivative-feedback-damping account, and makes the
lane **[re-aimable in a known direction / still unexplained]**."*
🛑 **Both branches are decision-bearing, and neither is "we would not be able to tell."**

---

## §5.2g ⭐ THE PID GAIN FAMILY — VETTED. **SURVIVES, CONDITIONALLY**, with one crux to settle first

**Candidate:** `0xC6ADC` Kd / `0xC6B08` Ki / `0xC6B1C` Kp, all indexed on `gp-0x6ac0`; **VIRGIN 95/95**;
**RULE 7 passes** (direct `tp` displacement, not mode-indexed). ⊕ My §1b matrix independently flags this
exact family at **N = 90 — "the PID gains have never been touched in 90 builds"** — the two readings agree.

### (1) Does the invariance partition close it? — **NO.** Same reason as the speed LERP.
It bars *"no downstream **absolute-count limit** can behave differently than it did on stock."*
**A PID gain is a linear gain, not a count limit.** ⇒ **The partition kills the PID gains as a CAUSE**
(they are byte-stock, so they replay stock exactly — and V87's subtractive rebase confirms the symptoms
survive at near-stock) — **but it does not touch them as a LEVER.**
⭐ **And its own exception clause points AT this node:** *"The ONE downstream exception: torque ABOVE what
stock could ever produce. Stock's max LKAS lane was 417 counts. The band 418–1782 never existed before."*
The PID's reference carries a **4×-boosted** LKAS contribution ⇒ **the PID operates inside exactly the
"genuinely new territory" the partition carves out.**

### (2) New, or a re-run? — **GENUINELY NEW AS A CLASS. No build in 100 has edited a PID gain.**
Against the eras (V38–52 authority/filters/poles/caves · V53–61 telemetry+mutes · V62–73 rate lane ·
V74–83a damper · V84 revert · V85–100 observer): every one touched a **PARALLEL summand** — a lane into
the aggregator, a damper factor, an observer arm — or a filter. **A series controller gain is none of them.**
⚠ **The closest relative is real and worth naming: `0xC644A` IS the PID's own D-path IIR pole**, moved by
**V43** (1024→64) and **V49p**, now back at stock, frozen 57 builds. ⇒ **the D path's FILTER has been
touched twice; its GAIN never has.** A pole and a gain are different levers on the same term.

### (3) Has the arc implicated Kp / Ki / Kd / `0xC644A`?
| term | implicated? | detail |
|---|---|---|
| **Kp `0xC6B26`** | **NO — never, anywhere** | clean |
| **Kd `0xC6AE6`** | **NO by any build** — but a live contradiction sits in `memory/` | **`gate2-pid`'s to adjudicate, not mine** |
| **Ki `0xC6B12`** | 🛑 **YES — the audit's E5 kill** | *"at 6–10 km/h the **P term alone** (16,000 at e = 2000) already exceeds the anti-windup bound (**7,264**) ⇒ the integrator is **pinned**"* |
| **`0xC644A`** (D pole) | **YES, twice — and BOTH verdicts name the wrong symptom** | V43 flew NULL scored on the **21 Hz vibration**; the lane was later *"ELIMINATED by V56"* — scored on **15–26 Hz, never 6–9 Hz** |

🛑🛑 **I DO NOT FULLY ACCEPT THE Ki RECONCILIATION.** The tracer's finding is that `0xC6AF0`'s anti-windup
**SCHEDULE** collapses only above 3604 ct = 764.8 °/s, **6.8× above the measured range** ⇒ it never
collapses. **That is a DIFFERENT claim from E5.** E5 is a **magnitude** argument: the anti-windup
*bracket* is **7,264** and the P term alone reaches **16,000**, so the integrator is pinned.
⭐ **The tracer's result CONFIRMS the precondition E5 needs — that the bracket is live and sitting at its
flat first-segment value — rather than refuting it. Reading it as a refutation is a category error.**
⇒ **"The gain SCHEDULING is dead, not the gains" is ACCEPTED as a description of the TABLES. It is NOT
accepted as a refutation of E5.** ⇒ 🛑 **Ki stays STRUCTURALLY-DEAD pending a re-run of E5's own
arithmetic — a `gate2-pid` question, and the one place we must reconcile. Kp and Kd are unaffected.**
⊕ **`0xC644A` is RECOVERABLE, not spent:** *"a verdict without a named symptom is not a verdict."*
**Do not cite V43's null as covering the D path at 6–9 Hz — and do not call the cell untested either.**
It is the I1/I2/I3 class: a live lever retired for the wrong question.

### (4) Does the five-instance GATE-2 table argue against the PID gains? — **YES, MORE strongly, not less.**
**V80** (damper `k`), **V94** (damper removal), **V61** (rate lane), **V71c** (`0xC6444`), **V83a** are
**all PARALLEL-path gains.** None is a controller gain. ⇒ 🛑 **The table does NOT exonerate the PID — it
UNDER-REPRESENTS the risk.** A parallel summand changes one term's contribution; **a PID gain scales the
ENTIRE loop gain of the torque-tracking loop** — a strictly larger perturbation class, on a mode measured
at **Q 14–29, ζ 0.017–0.036**, where five smaller perturbations already went the wrong way.
⭐ **The fair counter, and it is real:** all five failed because **the SIGN was unknown** (V94's premise was
backwards, V61 inverted the record, V71c reversed). **Kd is the damping term by construction**, so the PID
may be the one family where GATE 2 is *answerable* rather than a guess. **That is exactly what `gate2-pid`
must return: a signed direction, per term, with phase.**
⚠ Scoping note for them: **V85 named the lever class "PHASE/LAG"; V86 falsified exactly ONE phase lever —
`0xC40D4`, an observer EMA, NOT a PID term.** One falsified phase lever in the observer does not falsify
the PID's own D path.

### 🛑🛑 (5) THE CRUX — the "flat first segment" rests on an INHERITED number, and the record holds THREE that disagree by 5.9×
The headline property (*"the operating point sits entirely inside the flat first segment ⇒ a clean scalar
with no slope discontinuity"*) rests on `gp-0x6ac0` **max ≈ 528 ct.** You flagged it as inherited from
**returns**. It is worse than that:

| figure | source | context |
|---|---|---|
| **528 ct** | the `0xC520C` analysis | **hands-off RETURNS only** |
| **329.8 ct** | `memory/accord-damper-is-mode-table-selected.md:54` | **highway peak** |
| **1,941 ct** | `BUILD-LINEAGE.md:378` — route `5d`, *"the axis that matters"*, 101,118 frames | parking-lot cranking, 412 °/s |

⊕ The axis is confirmed shared — *"All three lane gains are LERPs indexed on `gp-0x6ac0`"* — and the scale
is exact (`4.7121 = 2^18/(48×1159)`, instruction-level). The damper's own gate `gp-0x6ac0 < 0x32c9`
(**12,993**) shows the cell is *structurally* free to run far past 528.
🛑 **IF THE TRUE ENGAGED MAX IS ~1,941 ct, THE HEADLINE PROPERTY FAILS**: the P table's knots at **300 and
2000** are **both traversed**, Kp is **not** flat in the reachable range (256 → 225 across 300→2000 ct),
and **editing `Y[0]`+`Y[1]` together creates a slope discontinuity at the 2000 knot — the EXACT defect I
found in my own B1 single-knot proposal.** ⇒ **Same error class as B1's: an operating-point claim
inherited from the wrong regime.** I am **not** asserting the property is wrong — **it is not
established**, and it is cheap to settle: `gp-0x6ac0`'s engaged distribution on route `0x85`, or one rung.

### ⇒ VERDICT: **SURVIVES, CONDITIONALLY** — the first fix candidate in this file that is neither dose-blocked nor sign-blocked on structure
**Conditions, all cheap:** (a) **settle `gp-0x6ac0`'s ENGAGED reachable range** — 528 vs 1,941 decides
clean-scalar vs B1-class discontinuity; (b) **`gate2-pid` returns a signed direction per term**; (c)
**Ki EXCLUDED** pending E5 re-adjudication — **Kp and Kd only**; (d) `0xC644A` treated as
**recoverable-but-unscored**, not as tested.
⇒ **If (a) and (b) both come back clean, V101 can be a FIX WITH ITS INSTRUMENT** — a 4-byte cal edit plus
the ~114 B cave — **and my instrument-only recommendation is superseded.** If either fails, it stands.

---

## §5.2h ✅ MY SYNTHESIS WAS TOO STRONG — it kills `0xC6194` ONLY. The `0xC63EC` low-pass SURVIVES, and is STRENGTHENED.

**You are right and I am correcting it.** *"If the command's effect is excitation, attenuating the command
is not the lever"* conflated two different interventions:

| | `0xC6194` (killed) | `0xC63EC`/`0xC63EE` (survives) |
|---|---|---|
| type | **SLEW LIMITER — a hard nonlinearity** | **LINEAR one-pole IIR + 2-tap FIR** |
| selectivity | rate-limits the **whole** request — binds on large SLOW moves too | **band-selective**; moving `a`,`b` together **holds DC to 0.2 %** |
| authority | **deletes low-frequency authority** | **preserves it exactly** |
| independent blocker | 🛑 arming via `0xC4118` **silently deletes LKAS steering** | none |

⭐ **AND "EXCITATION, NOT GAIN" IS NOT NEUTRAL TOWARD THE LOW-PASS — IT ACTIVELY SUPPORTS IT.**
- If the symptom were a **limit cycle / self-excited oscillation**, reducing the input would **not** help —
  a limit cycle sustains itself regardless of drive. The lever would have to be loop gain or phase.
- If it is a **forced response at a lightly-damped resonance**, then `output(f₀) ≈ Q · input(f₀)`, so
  **reducing input at f₀ reduces output proportionally.** That is linearity, not a gain that isn't there.
- 🛑 **The record independently EXCLUDES the limit cycle**: *"limit cycle EXCLUDED"* (the Q 14–29
  ring-down memory), and V85's comb/PLV work put **<15 %** of the ~8 Hz content as relay-generated.
⇒ **"Excitation, not gain" is precisely the finding that makes a band-selective INPUT filter the right
class of lever.** My synthesis should have said *"a hard rate limit is not the lever"* — it does not
generalise to a linear band-selective filter, and I withdraw the broader form.

### ⚠ BUT I MUST CORRECT YOUR SUPPORTING ARGUMENT — **V88 IS NOT THE EXISTENCE PROOF**
> *"V88 is the existence proof: it worked by reducing high-frequency content of the delivered command,
> which is the same class of action one node over."*

🛑 **It is NOT one node over — it is the OTHER SIDE OF THE LOOP.** §5.2f established that V88's measured
cell `gp-0x6b98` is the loop's **OUTPUT**, and its HF content comes from the **rate lanes — torque-sensor
DERIVATIVE FEEDBACK** — which is why the scoring agent's own write-up says *"r24 is rate FEEDBACK inside
the loop… more derivative feedback = more damping."* `0xC63EC`/`0xC63EE` sits on the **LKAS command path**
(`FUN_00028ea6` = the arbitration, `gp-0x6806`'s producer) — the loop's **INPUT**.
⇒ **V88 reduced output HF by changing FEEDBACK; the low-pass would reduce input HF by filtering the
COMMAND. Different node, different mechanism. V88's precedent does NOT transfer, and the numerical
coincidence (0.564 vs 0.549) is NOT evidence of a shared mechanism.** Do not carry it as one.

### 🛑 THE REAL THREAT IS T5/SHARE, NOT THE SYNTHESIS — and it is unmeasured
The record's standing finding: **the LKAS lane is already a ~1–5 Hz low-pass**
(`reference-accord-lkas-lane-is-a-lowpass`), which V80's analysis used to argue *"a 27 Hz command
component cannot reach the motor that way."*
⇒ **There may be very little 6–9 Hz command content left to remove.** The decision-relevant number is not
*"does the filter attenuate 7.79 Hz"* (it does, 0.564) but ***"what fraction of the column's 6–9 Hz energy
is driven by the COMMAND's 6–9 Hz content?"*** **That is the T5 class that killed `0xC63A4` at 1.1 ct of
342, and it is UNMEASURED.**
⚠ **And the obvious off-line check is contaminated**: cmd→column coherence *"is NOT an attribution
instrument"* — 0.254 engaged vs **0.544 MANUAL**, where the LKAS command is identically absent ⇒ loop
feedthrough, not attribution. **The clean measurement is the ECU-INTERNAL command lane (`gp-0x6b4c`) on
427** — which is a one-displacement-byte repoint and would size the low-pass properly.

### ⇒ YOUR MISSING-CONTROL QUESTION, ANSWERED DIRECTLY
**The `dCMD/dt` engaged-vs-manual interaction control does NOT gate the low-pass.** The low-pass's case
rests on three legs, none of which is the partial: **(i)** the loop is a forced response at a
lightly-damped resonance — **EVIDENCE**; **(ii)** the command has material 6–9 Hz content reaching the
loop — **UNMEASURED, and this is its real blocker**; **(iii)** attenuating (ii) reduces the forced
response — **linearity**. ⇒ **It stands independently of the `dCMD/dt` result, but it stands on (ii),
which nobody has measured.** Size it before flying it.

---

## §5.2i ⛔ `0xC61B8` + THE `gp-0x6b30` HYSTERESIS — VETTED, AND IT DIES ON THE ENABLE'S POLARITY

**My own hysteresis argument was right about the MECHANISM and it does not matter, because the block runs
in the wrong arm.** I am killing my own candidate.

### 🛑🛑 THE ENABLE IS `gp-0x6806 == 0`, AND `gp-0x6806` IS **LKAS ENGAGEMENT**, NOT THE LOW-SPEED LOCKOUT
Three independent record entries, all pre-existing:
- **`gp-0x6806` = `STEER_CONTROL_ACTIVE`**, packer `shl 3` (`ARCHIVE-CLAUDE-MD:101`).
- **V67 measured `gp-0x6806` == `latActive` in 150,302 / 150,327 = 99.983 %**, all 25 disagreements
  single-frame edges (`BUILD-LINEAGE.md:1034`).
- **`FUN_00028ea6` — the very function containing this block — IS `gp-0x6806`'s PRODUCER**
  (`BUILD-LINEAGE.md:1014`, the arbitration set).

⇒ **`gp-0x6806 == 0` means LKAS IS NOT ACTIVE ⇒ THE DEADBAND AND THE HYSTERESIS RUN IN *MANUAL* ONLY.**
⊕ Internally consistent: **Lever B arms on `gp-0x6806 != 0` (ENGAGED); this block arms on `== 0`
(MANUAL). They are complementary halves of the same flag.**

### ⇒ THE KILL, and it is the cleanest in this file
**The symptom is engagement-REQUIRED**, measured with the grip confound removed, both arms hands-off,
pooled over four routes and four builds: **73/88 = 83.0 % engaged vs 0/118 = 0.0 % MANUAL, Fisher
p = 3.8×10⁻⁴¹ — zero hits in 118 manual windows / 302 s.** And the operator: *"literally every bad
symptom is LKAS engaged only."*
⇒ 🛑 **A TERM THAT ONLY RUNS IN MANUAL CANNOT PRODUCE A SYMPTOM THAT NEVER OCCURS IN MANUAL.**
**STATUS: STRUCTURALLY-DEAD for this symptom** — same class as the return-to-centre/detent kill
(*"~99.3 % dead in MANUAL too ⇒ its absence cannot explain any engaged-vs-manual difference"*).
**The hysteresis-vs-deadband describing-function argument stands as physics and is simply not reachable
here. Do not spend `gate2-pid` on it.**

### 🛑🛑 BUT THE CONTRADICTION IT EXPOSES IS FAR MORE IMPORTANT THAN THE CANDIDATE
The brief states `gp-0x6806` is *"the low-speed lockout, ~100 % ON below 3 mph, 8.9 % at 3–4 mph, **0 %
above 4 mph**."* **That cannot be reconciled with `gp-0x6806` == `latActive` over 150,327 frames** — route
`0x85` was **engaged with p50 39.6 km/h and 45.5 s above 80 km/h.** Only one can be right, and **each
branch has a large consequence:**
- **If `gp-0x6806` = latActive (the record, 3 sources, 150k frames):** the hysteresis is manual-only ⇒
  **dead, as above.**
- **If the tracer is right:** then **Lever B — gated on the same flag — has been INERT ABOVE 4 mph for 12
  builds, and V88's attribution collapses**, because route 73's win included **120 s engaged ≥50 km/h.**
⇒ 🛑🛑 **RESOLVING `gp-0x6806`'s IDENTITY IS NOW THE HIGHEST-PRIORITY TRACER QUESTION IN THE SESSION —
one branch invalidates the kit's best measured result.** It is also exactly the failure class I wrote up
this session: **verify the ENABLE from its producer, not from a label.**

### The other questions, answered
- **Partition:** does not close it (a deadband is a threshold, but the block is virgin and byte-stock, so
  it replays stock ⇒ **not a CAUSE**). ⭐ One sharp consequence *if* it sits upstream of the 4× gain:
  *"every stage upstream operates 4× closer to zero, so a fixed absolute threshold occupies 4× MORE of the
  working range"* ⇒ **we would have made the ±102 deadband effectively 4× wider.** Moot under the kill,
  **but this is the one case where the partition would ADD to a candidate rather than remove it — worth
  remembering for the next threshold found upstream of the gain.**
- **New or re-run:** **NEVER-TRIED** — `0xC61B8` and `0xC64A3` byte-stock on every image, all 22 script
  hits are guards. Genuinely new as a class (**no build has touched a stateful nonlinearity**).
- **Has the arc implicated it:** yes — filed **ELIMINATED** on *"polarity `gp-0x6752` cannot chatter."*
  My point stands that this addresses **CHATTER, not HYSTERESIS LAG** — *"a lever can be correctly filed
  DEAD for a reason that is itself false"* — **but the manual-arm finding supersedes the whole dispute.**
- **GATE-2 table:** all five instances are **engaged-path** gains ⇒ **does not reach it.** Moot.
- **Reading (c) — "`gp-0x6806` toggles on a cadence ⇒ a relaxation oscillator whose period IS the
  stutter": 🛑 REFUTED BY THE ARC.** V67's 150,327 frames show **25 disagreements, all single-frame
  edges.** A ~7.79 Hz relaxation oscillator would produce **~1,170 toggles in 150 s, not 25.**
- **`0xC62EA` = 0 since ~V35 — "did we create this exposure ourselves?"** ⭐ **The hypothesis is real but
  points the OTHER way.** `0xC62EA`→0 removed the ~5 km/h lockout, so the car stays **ENGAGED** to zero
  speed — *"creep sits in a regime stock Honda would have locked out"* (`STATE.md`). ⇒ we did not create
  hysteresis exposure (that is manual-side); **we created ENGAGED-AT-CREEP exposure — the exact regime in
  which he provokes the symptom.** 🛑 **That belongs in the record as a live self-inflicted-exposure
  hypothesis, and it is testable for free: `0xC62EA` is 320 on stock and 0 on every build since ~V35, so
  no build in the corpus can separate them — but a single drive with it restored to 320 would.**

---

## §5.2j ⭐⭐ THE FINAL V101 PAYLOAD — **THE 427 CONFLICT DISSOLVES.** Both candidates get what they need.

### The resolution: **only the SHARE needs a magnitude lane. The DROPOUT is a comparator.**
- **The dropout is a BINARY EVENT with a DERIVED BOUNDARY** — the aggregator drops `gp-0x6ad4` past
  **±10240**, an immediate in the instruction stream (`0x3acbc addi 0x2800 / 0x3acc4 cmovc`). ⇒ **its duty
  IS the answer, no scale assumption, exactly the `b5` model.** ⭐ **And a rung at `10240/k` reads the
  POST-EDIT dropout duty for a Kp dose `k` TODAY, before the edit exists:**
  `k = 1.25 → 8192 · k = 1.5 → 6826 · **k = 2.0 → 5120**`. **Rung at 5120 ⇒ the duty upper-bounds the
  dropout for ANY dose ≤ 2.0×, dose-agnostic across the whole plausible range.**
- **The SHARE cannot be a bit** — it is a ratio of band-limited RMS, which no single-frame rung computes.
  **It genuinely needs 427.** (V100's E3 has the same shape: the numerator was free on `0x18F`, only the
  internal denominator needed the lane.)
⇒ ⭐ **427 goes to `gp-0x6b4c`; the PID loses NOTHING.**

### ⭐ And the repoint is FREE — one byte, no packer change [verified this pass]
```
V100 today   -0x6b94 -> hw2 0x946C   hi 0x94
V101         -0x6b4c -> hw2 0x94B4   hi 0x94      => SAME HIGH BYTE => ONE-BYTE diff at 0x55DF2
GATE 3: gp-0x6b4c's OWN writer clamp is +-10240 -> (10240*5)>>6 = 800 of 1023  => NO-CLIP, LSB 12.8 ct
        => 0x55E10 STAYS at sar 6 (0xA6).  NO second edit.
```
⊕ **This is strictly cheaper than the `gp-0x6ad6` plan I specced earlier**, which needed a **two-byte**
repoint **and** a `sar 6 → sar 7` GATE-3 fix (its ±25600 clamp gives max code 2000 — it would saturate).
**What `gp-0x6ad6` loses:** B1′ stays unsizeable ⇒ **it waits for V102.** Acceptable — it is third-ranked
and separately blocked on a tracer.

### THE PAYLOAD — ≈98 B, the smallest since V96
| bit | measurand | form | est. B |
|---|---|---|---|
| **b7** | `gp-0x6b4c < 0` | **SIGN — mandatory partner for 427** | 10 |
| **b6** ⭐⭐ | **`\|gp-0x6ad4\| ≥ 5120`** — the **DROPOUT DOSE-SAFETY rung** (5120 = 10240/2, a **DERIVED** boundary) | threshold on a derived boundary | 14 |
| **b5** ⭐⭐ | **`gp-0x69a4 ≥ 868`** — the **LEVER-B PARITY rung** (868 = 0.848 × 1024, derived) | threshold on a derived boundary | 10 |
| **b4** | `gp-0x67ab == 1` | threshold, **R3 SAFE class** (static/config) | 10 |
| **b3** | **IDENTITY — unconditional constant 0** (V100 is constant **1**) | constant | 0 |
| byte7[7:6] | **2**, carried | constant block | 18 |
| — | merge/shl + RET | — | ~36 |
| **427** | **`gp-0x6b4c`**, signed via b7, `sar 6` unchanged | **magnitude lane** | 1 |
| | | **TOTAL** | **≈98 B** |

🛑 **Why I did NOT spend a bit on `gp-0x6806`**, despite it being the session's most consequential open
question: **it has ALREADY been measured dynamically — V67, 150,302/150,327 frames.** The dispute is an
**identification**, and a static read of the producer settles that; a fourth duty measurement does not
outrank 150k frames. **Spend the tracer, not the bit.**
⚠ **τ pricing, honestly:** b6/b5/b4 are all threshold-class (**measured τ 0.350–1.547 s** on route `0x85`,
worse than the pre-flight prior). At 249 s engaged, worst-case `n_eff ≈ 161` ⇒ **a zero reading bounds a
duty at < 1.9 % (rule of three), and a 0.20/0.80 call carries ≈ ±0.06.** Adequate for every question here.

### 🛑 THE SENTENCE A NULL LICENSES — every bit
- **b6 (the bit that unblocks the PID fix).** **Duty 0.0000** ⇒ *"The PID output never reaches half the
  aggregator's ±10240 dropout threshold across 249 s of engaged driving, so a Kp dose up to 2.0× cannot
  trigger the dropout relay — the newly-found V80-class hazard is priced OUT for that whole dose range."*
  **Duty > 0** ⇒ *"the dropout is live at d %, and a dose k raises it to today's duty at 10240/k — the
  hazard is real and the maximum safe dose is bounded by that curve."* **Both decision-bearing.**
- **b5.** *"Lever B's net rate-lane dose was [above/below] stock parity on the drive that produced the
  kit's only reproducible fix ⇒ the derivative-feedback account is [confirmed/refuted] and the lane is
  [re-aimable in a known direction / still unexplained]."*
- **b4.** *"`gp-0x67ab` is never 1 across 249 s ⇒ the terms-1–7 block is never dropped, and a structural
  assumption carried through the whole arc becomes a dynamic measurement."*
- **b7.** *"`gp-0x6b4c` does not change sign ⇒ 427 is an unsigned level and no phase or coherence claim may
  be made from it."* (Expected FALSE.)
- **427 — the SHARE endpoint, as a DIMENSIONLESS SAME-DRIVE RATIO** (E3's lesson: an absolute 6–9 Hz RMS
  carries 24–29 % rel s.e.; the ratio form 4.4–7.7 %):
  `S = RMS₆₋₉(gp-0x6b4c, signed) / RMS₆₋₉(column torque, 0x18F)`, both from the same route.
  **PRE-REGISTERED DECISION BOUNDARY** — delivered `= 1 − S·(1 − 0.564)`, **coherent addition, i.e. an
  UPPER bound on the benefit**:
  ```
  S = 1.00 -> 0.564   S = 0.90 -> 0.608   near the felt line (0.549)
  S = 0.75 -> 0.673   S = 0.50 -> 0.782   UNTESTED MIDDLE
  S = 0.25 -> 0.891   S = 0.10 -> 0.956   NOT-FELT band (0.947 / 1.088) => KILL
  ```
  ⇒ ***"S ≥ 0.9 ⇒ the low-pass can reach the felt line at its strongest setting. S ≤ 0.25 ⇒ it cannot
  reach the perceptual floor at ANY setting and the candidate is DEAD."*** 🛑 **And the record makes the
  kill branch the more likely one: the LKAS lane is already a ~1–5 Hz low-pass**, so the command may
  contribute little of the 6–9 Hz band. **This bit of arithmetic prices the candidate BEFORE the drive,
  which is the whole point.**
  **Failure sentence:** *"if 427 reads ≡ 0 or pins at 1023 the repoint is wrong and NO share claim may be
  made from this drive."*

### 🛑🛑 SHOULD V101 CARRY A CAL LEVER? — **NO, AND HERE IS THE POSITIVE REASON, NOT A FALLBACK**
✅ **My crux (a) came back CLEAN**: `gp-0x6ac0` crosses 300 ct (4.91 %) but **never reaches 2000 (0.00 %)**
⇒ **the PID edit creates NO discontinuity, and my three-figure flag is resolved** (330 = highway, 528 =
returns, **1,941 = MANUAL — none was the engaged point**). ⊕ And `Y[2]` must scale too, or the dose fades
2.000× → 1.324× at peak rate — **the same three-knot level-shift discipline as B1′.**

**But the decisive argument is structural, and it applies to BOTH candidates identically:**
> ⭐ **The measurement's entire job is to CHOOSE the dose. Pairing a dose with the measurement that would
> have set it spends the measurement AFTER the decision it exists to inform.**
- **PID:** b6 prices the dropout ⇒ *then* choose `k`. Flying a `k` now means choosing it blind to the very
  hazard `gate2-pid` just found.
- **Low-pass:** 427 measures `S` ⇒ *then* choose the corner. And **at 1000/380 the dose delivers 0.801×,
  which sits in the UNTESTED MIDDLE of the perceptual bracket — a coin-flip on feel.** Flying it now means
  committing to a corner before the number that sets the corner exists.
⇒ **V101 = INSTRUMENT-ONLY, and it is the considered answer: not "we are not ready", but "this build is
the last blocker on two fixes, and spending it as a fix destroys its own value."** **V102 can then be a
fix with its dose already sized and its hazard already priced** — which no build in this arc has ever
managed.
⚠ **The cost, stated plainly and it is his call:** **third consecutive zero-calibration build (V98, V100,
V101).** ⊕ **What is different this time, and it is worth telling him:** V98 and V100 measured to *explain*
a null; **V101 measures to SET A DOSE.** Both endpoints have pre-registered numeric boundaries that convert
directly into a V102 cal edit — **it is the first instrument in the arc whose output is a build.**

---

## §5.2k 🛑🛑 FINAL — BOTH FIXES DEAD, `b5` ANSWERED FROM THE IMAGES, AND **V101 DOES NOT JUSTIFY A DRIVE**

### The payload I specced in §5.2j is now mostly vacuous. Taking each bit in turn:
| bit | status after the new results |
|---|---|
| **427 ← `gp-0x6b4c`** | ⛔ **the SHARE endpoint is MOOT** — the low-pass is dead two independent ways ⇒ **the repoint has no pre-registered endpoint. DROP IT and save the byte.** A channel with no endpoint is the thing this kit's own design law forbids |
| **b6 `\|gp-0x6ad4\| ≥ 5120`** | ⛔ **VACUOUS — `AUTH ≤ 5120 < 10240` always ⇒ the dropout is structurally unreachable.** My rung tests something that **cannot happen**: the V69-`bit4` failure class verbatim (*"STRUCTURALLY VACUOUS — it could never have fired on any build, any drive"*). **Killed, mine, accepted** |
| **b5 `gp-0x69a4 ≥ 868`** | ⭐ **ANSWERED FROM THE IMAGES — see below. No bit required.** |
| **b4 `gp-0x67ab == 1`** | ⚠ a **confirmation** of a well-supported structural claim. Knowledge-bearing, **not drive-justifying on its own** |
| AUTH comparator | ⚠ resolves Kp/Ki/E5/pinning on one bit — **but `gate2-pid`'s own verdict is that even fully cleared, AUTH licenses only 1.13×, i.e. AT the not-felt boundary.** ⇒ **four questions whose answer cannot change a build decision** |

### ⭐⭐⭐ `b5` IS ANSWERED — AND IT RESOLVES THE V88 CONTRADICTION FROM THE IMAGES
**Read from the plain images this pass** (`0x3AA96` gate · `0xC6444` r26 arm · `0xC6446` r24 arm):
```
build              gate      0xC6444  0xC6446    net vs stock = (5244 + 512a)/(3072 + 3072a)
STOCK/V62/V65      0xC5 dead     512      512    gate dead => NEITHER arm executes
V67 / V68 / V88    0xFB ARMED    512     5244    1.707 at a=0  ->  0.937 at a=1
V71c               0xFB ARMED   3072     5244    1.707 at a=0  ->  1.354 at a=1
V100 (on the car)  0xFB ARMED    512     5244    same as V88
```
✅ **First: `0xC6444`'s FALSIFICATION STANDS. V71c had the gate ARMED (`0xFB`)**, so the *"`0xC6444` is
NULL BY CONSTRUCTION on gateless builds"* note **does not reach V71c.** I checked this expecting to
overturn the falsification and it held — **verified in the safe direction.**

🛑🛑 **AND THE DECISIVE INFERENCE — `a` IS MATERIALLY NON-ZERO, PROVED BY AN ON-CAR CONTRAST:**
**At `a = 0` V88 and V71c are ARITHMETICALLY IDENTICAL** (the `0xC6444` term enters only as `arm26 · a`;
same gate, same r24 arm). **They are NOT identical on-car** — V88 is the kit's best result (*"grinding
fixed"*) and **V71c is the worst build in the corpus for the ratchet** (grind #1 HIGHER P=0.0215, grind #2
returned, ratchet at the **corpus record** 8,521 ct p-p). ⇒ **`a` cannot be ≈ 0, and the r26 arm is
load-bearing.** [EVIDENCE — images + two on-car outcomes, no new drive]

⇒ **AND THAT REFUTES ACCOUNT A.** *"More derivative feedback ⇒ more damping ⇒ less HF"* predicts **V71c
(net 1.354 at a=1, the HIGHER dose) should have been BETTER. It was dramatically worse.**
🛑 **The V88 memory's stated mechanism is WRONG and needs correcting** — the coupling it describes is
right, the causal direction is not.

### 🛑 BUT THE FULL PICTURE IS AN **OPTIMUM**, NOT A DIRECTION — and that CLOSES the lane
Three on-car points, all with the rate lane in force:
| build | net rate-lane dose | on-car |
|---|---|---|
| **V61** — rate lane cut | **below** V88 | 🛑 *"made it WORSE, inverting the record: the rate lane is the mode's damper"* |
| **V67 / V68 / V88** | **0.937 at a=1** | ✅ **the two best results in the kit** |
| **V71c** — r26 arm restored | **1.354 at a=1** | 🛑 **worst in the corpus on all three symptoms** |
⇒ ⭐ **BOTH directions away from V88's setting are measured WORSE.** That is the standing
*"2× ≈ OPTIMUM, not a point on a ramp"* warning, now supported on **both flanks** rather than one.
⇒ 🛑🛑 **THE RATE LANE IS CLOSED AT ITS OPTIMUM, AND V88 IS SITTING ON IT.** Lever B **UP** is
rail-blocked *and* measured worse (V71c); Lever B **DOWN** is measured worse (V61). **There is no further
gain available on this lane, and knowing `a` would only tell us where on a curve whose peak we already
occupy.** ⇒ **b5's remaining value collapses with it.**

### ⇒ **HONEST ANSWER: V101 DOES NOT JUSTIFY A DRIVE.**
Every bit is now vacuous (b6), answered without a drive (b5), a bare confirmation (b4), or
non-decision-bearing (AUTH — best case 1.13×, below the felt line). The 427 endpoint is moot.
🛑 **A build that measures two dead levers is worse than no build**, and this one would measure three.
**Do not cut V101.**

### ⭐ WHAT THE SESSION ACTUALLY PRODUCED — and it is not nothing
1. **The V88 mechanism contradiction is RESOLVED from the images** — Account A refuted, `a` proved
   materially non-zero, `0xC6444`'s falsification verified in the safe direction.
2. **The rate lane is CLOSED at an optimum V88 already occupies** — with both flanks measured. That
   retires the kit's self-declared *"leading open question"* and removes Lever B from every future
   shortlist in both directions.
3. **Two fix candidates killed on measured grounds** (low-pass 39× below the not-felt line; Kp has no
   value that is both safe and felt).
4. **A firmware design idiom identified** — latching zero-output dropouts in at least two places ⇒
   **GATE 3 must check for a DROPOUT, not only a clamp** (§5.2i).
**None of that needed a drive, and all of it narrows the search.** That is the honest deliverable.

| # | item | why now |
|---|---|---|
| **X1** ✅ **ANSWERED — closed as NOT-MOTIVATED, not as INERT** | **Asked and answered: *"Never noticed a difference."*** ⇒ **LICENSED:** *a 10× ramp-rate asymmetry (`0xC63F8`=33 vs `0xC63FC`=328, VIRGIN on all 90 images) produces no left/right asymmetry the operator has ever noticed, against a rack **measured symmetric** (19 paired per-bin CIs all cover equality; an injected 2 % asymmetry WOULD have been detected). There is no operator-facing L/R asymmetry to explain, so **no lever is motivated by one.*** 🛑 **NOT LICENSED: "the cells are inert."** This is **weak negative evidence, not a measurement** — *an absence of a complaint is not a report of improvement*, he was not asked to look for it during a symptomatic episode, and a **ramp-RATE** asymmetry is a transient property that steady-state feel would not surface. **What would keep it open:** a measured L/R contrast in the 6–9 Hz band from the caches already on disk — free, no build. If nobody spends that, **close it NOT-MOTIVATED and do not re-raise it** | ✅ **CLOSED** |
| **X6** 🛑 | **OPEN RULE-11 ITEM, recorded so it is not lost: IS THERE A MONITOR ON `gp-0x6ad6`?** No monitor census exists for that cell anywhere in the record I read | **BLOCKING for anything that widens the PID reference** — B1′ included. RULE 11 cost this kit two mid-drive total losses of assist (`0xC407E`). *"Before raising any clamp, saturation or output limit, search for a monitor that tests the same cell."* Put to a tracer |
| **X2** | **The BUILD-IDENTITY FIELD build** — ≥3 bits with its own `0x18F` hook, **as its own build, never combined with a new measurement class** | Standing requirement since V97's identity could not be separated from V96 single-frame. byte7[7:6] gives only **one** clean generation and V96/V97 already burn {1,3} |
| **X3** | 🛑 **Fix the recall-layer defect** — `memory/accord-cbe74-dose-measured-inert-wrong-mode-record.md`'s **frontmatter asserts a claim its own body refutes**, and `MEMORY.md`'s pointer repeats the stale version. The filename encodes the retracted claim | It is the exact error class `feedback-search-the-kit-before-naming-a-cause` exists to prevent |
| **X4** | `BUILD-LINEAGE-PART1-LEVER-INDEX.md` **is ~19 builds behind** — a mandated by-address grep for `0xC63AC`, `0xC40BC`, `0xC40D2`, `0xC63A6` returns **nothing** from the index `CLAUDE.md` makes mandatory | A process gate that silently returns "no prior work" is worse than no gate |
| **X5** | The **golden-model GAP** — `eps_chain_control.py` does **not** model the PID's internals, so `0xC6200`'s reference clamp and the ±10240 error clamp are **absent from it** | If E1 comes back HIGH, the golden model is wrong about the whole chain's authority. Implementing it *"changes delivered numbers and must be its own verified pass with a re-derived contract"* (87 symbols / `740f4bcd…`) |

## §5.4 THE HARD CONSTRAINTS EVERY CANDIDATE ABOVE WAS SCORED AGAINST

- **ONE SHORT SYMPTOMATIC DRIVE.** ~15–30 s of engaged, symptomatic frames, one episode; plan for
  **15–65 s across 1–3 episodes at creep**, and **make the within-drive LKAS-off arm MANDATORY** (route
  81 proved it obtainable; V98's spec called it *"optional and free"* — it is neither).
- **UNBUILDABLE at this exposure, do not propose:** any cross-build band ratio · any episode bootstrap or
  split-half null · ring-down ζ/Q · any ≥50 km/h claim · any 26–31 Hz claim · any grind-#2 claim (166 s
  floor) · any dose ladder · any 5.12 s-window override statistic · **any E2-class partial-correlation
  endpoint (needs 25–58 min contiguous engaged; best-ever is 65.9 s = 16–50× short — STRUCK)**.
- **WHAT SURVIVES:** single-frame identity/liveness · **duty of a cave bit** · ⭐⭐ **comparator rank duty**
  · joint 2×2 contingency · conditional duty · the within-drive manual arm · onset windows at the
  `latActive` edge · within-build sign-crossing rate · ⭐ **the operator's own report**.
- **THE POWER GATE:** *"if any endpoint's sentence contains 'compared to V99', IT FAILS."*
- **Sign bits are cheap; threshold bits are not** — τ **0.029–0.052 s** for sign rungs vs **0.065–0.603 s**
  for threshold rungs = 2–20× stickier and that much less effective sample. Size the floor **per rung from
  its own measured τ.**
- **A magnitude channel shipped without its sign bit is not a smaller build, it is a wrong one** —
  measured price on this exact lane: 6–9 Hz RMS understated **4.9–5.5×**.
- **Any exposure calculation using `1/√(2n)` is optimistic by 6–8× on this car.** Block-bootstrap.
- **PERCEPTUAL BRACKET: ~0.55× (−45 %) IS felt (V88, V62); ~1.09× (+9 %) is NOT (V85, V89).**
  A lever below that floor is not worth a drive.

## §5.5 🛑 THE HONEST FRAME FOR WHATEVER LANDS

**Nothing in sixty builds has ever moved micro-ratcheting or ratcheting.** They are reported present, in
his words, on **V76, V81, V83a, V84, V85, V86B, V87, V88, V89, V90 and V97** — and the two builds that
moved them moved them the **WRONG WAY** (V83a's micro-ratchet band 1.526× [1.174, 2.019]; V94 aborted).

**Exactly TWO interventions have both a measured on-car change AND his own report of improvement:**
**V62** (Lever A, *"Original grinding at 2–5 mph is gone!"*) and **V88** (Lever B, *"grinding — fixed"*).
Both are **rate-lane, mode-proof, command-side**.

⇒ *"V97 felt like nothing"* is, statistically, **the modal outcome of this arc — not an anomaly.**
The question every instrument exists to answer is **which kind of nothing it is.**

🛑 **Score BANDS; let the OPERATOR score SYMPTOMS. Never call anything fixed that he has not called
fixed. An ABSENCE of complaint is not a report of improvement. "The ring", "grind #1/#2", "S1…S4" are
KIT JARGON for frequency bands — not symptoms he named.** His words are **grinding, vibrating,
micro-ratcheting ("stuttering" — his own parenthetical, not a fourth symptom), ratcheting, excess
friction.**
