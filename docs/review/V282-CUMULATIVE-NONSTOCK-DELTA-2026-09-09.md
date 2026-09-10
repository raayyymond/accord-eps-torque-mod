# V282 — the cumulative non-stock delta, read from the images

**Why this file exists:** on 2026-09-09 the operator chose **"Neither — revert to V282 and stop here."**
V282 is therefore what goes on the car. This document enumerates **every cell on the V282 image that
differs from STOCK** — the cumulative delta, not one session's changes.

**Method [EVIDENCE].** Raw little-endian Python byte reads of two images; **no build script, and no
earlier delta document, was consulted for a single value.** Every number below is re-read.
Script: `analysis-2020accord/studies/closeout/v282_cumulative_delta_from_images.py`
→ `analysis-2020accord/_scratch/out/v282_cumulative_delta.json`.
No Ghidra database was opened; no mutating call was made.

| image | file | sha256 |
|---|---|---|
| **stock** (the true stock dump) | `$ACCORD_FIRMWARE_ROOT/analysis-2020accord/stock_fw_dump/code.bin` | `3f1d55a98aac6e73631d94d583065c57d83dd3a86df0e7d06e56a3feb58fd822` |
| **V282** (plain image) | `$ACCORD_FIRMWARE_ROOT/analysis-2020accord/_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin` | `0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe` |
| **V282 flashable** | `$ACCORD_FIRMWARE_ROOT/flashing-2020accord/rwd/39990-TVA,A160-V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP-0x13000-0x100000.rwd` | `618365154e3ffdbb073c00a60173508291f0a18340d6a4f7d39cdd4b2a5b7e22` |

**Exactly ONE V282 `.rwd` exists on disk** (verified by listing; the seven other filenames containing the
string "V282" are `V283…V289`, whose names carry `V282BASE`). ⚠ *Naming this file is not a flash
instruction — the flash is gated on the operator naming the file and the bus himself.*

**Diff extent `[0x13000, 0x100000)`: 1,984 differing bytes in 311 runs (gap ≤ 2 merge).**
Independently reproduced here; identical in count to `docs/specs/V282-NONSTOCK-DELTA-2026-09-04.md`
and to the copy inside `docs/review/V288-CUMULATIVE-NONSTOCK-DELTA-2026-09-07.md`.

---

## 0. ATTRIBUTION CENSUS — every differing byte is accounted for

Run by the script above as an assertion, not a claim: each of the 1,984 differing byte addresses is
mapped to exactly one named row, and the script **aborts if any byte is unattributed.** It does not.

| row | differing bytes | row | differing bytes |
|---|---|---|---|
| R1 version-string marker | 2 | R15 EME soft-limit quad | 4 |
| R2 forward-gain load repoint | 2 | R16 EME ramp triple | 3 |
| R3 biquad arm repoint (3 sites) | 4 | R17 EME float mirrors | 13 |
| R4 rate-lane gate byte | 1 | R18 Coulomb relay knee / K1 / α2 | 5 |
| R5 `gp-0x67fa` substitution byte | 1 | R19 STEER_STATUS debounce `0xC61C0..C4` | 6 |
| R6 `0x14A` cave hook | 4 | R20 STEER_STATUS debounce `0xC64B4/B6` | 4 |
| R7 `0x14A` telemetry cave body | 164 | R21 DTC-0x49 gate | 1 |
| R8 CAN-427 torque tap window | 31 | R22 square-wave hold count | 1 |
| R9 private forward LKAS gain | 2 | R23 rate-lane + boost bank flatten | 992 |
| R10 forward clamps `0xC61B2/B4` | 2 | R24/25/26 LERP data (map / Kp / ceiling) | 662 |
| R11 feedback saturation clamp | 1 | R28 page-CRC trailers | 74 |
| R12 r24 engaged rate-lane gain | 2 | | |
| R13 biquad enable cal | 1 | **TOTAL ATTRIBUTED** | **1,984** |
| R14 low-speed steer lockout | 2 | **ORPHANS** | **NONE** |

---

## 1. THE TABLE

`status` — **MEASURED** = scored on-car · **INERT/INSTRUMENT** = read-only or measured to do nothing ·
**CARRIED** = deliberate at its introducing build, not re-chosen since · **CARRIED BY REBASE** = riding a
base rather than a decision · **UNACCOUNTED** = no lineage entry states the intent · **BOOKKEEPING**.

| # | address(es) | stock | **V282** | what the variable physically is | what the change does to the car | introduced | status |
|---|---|---|---|---|---|---|---|
| 1 | `0x13109`, `0x14120` | `0x2D` (`-`) | `0x2C` (`,`) | the version-string byte a UDS version read reports | marks the ECU non-stock on a version query. No control effect | V22 | BOOKKEEPING |
| 2 | `0x2A1F0` | disp `0x746C` (`6c74`) | disp `0x7CD0` (`d07c`) | displacement of the forward-LKAS gain load | repoints the forward path off the **shared** sensor-scale cal `0xC646C` onto the **private** cell `0xC6CD0`, so the LKAS gain can move without touching anything else that reads `0xC646C` | V57; lost in the V38 rebase, restored V81 | CARRIED — structural; it is what makes row 9 reachable |
| 3 | `0x35A08`, `0x35A12`, `0x35A18` | `e798` · `ec` · `e9` | `fb97` · `e0` · `ea` | biquad ARM flag source (`gp-0x671a` → `gp-0x6806`) + the arm comparison + its branch condition | arms Honda's dormant **55 Hz notch, engaged-only**. The stock ≥5 condition was never observed true in 255 k engaged frames | V103 | MEASURED |
| 4 | `0x3AA96` | `0xC5` (197) | `0xFB` (251) | the r24/r26 rate-lane **gate byte**: `gp-0x683c` (a dead flag) → `gp-0x6806` (`STEER_CONTROL_ACTIVE`) | **makes Lever B live** — r24 runs the engaged gain of row 12 on the 4-tap derivative of bar torque whenever LKAS is engaged | V67; these bytes from V104 | MEASURED — operator on V88: *"the audible grinding is fixed"* |
| 5 | `0x454FE` | `0xBA` (186) | `0xB5` (181) | one substitution byte in the `gp-0x67fa` selector path (V42's ratchet-fix) | **nothing.** The reachable set of `gp-0x67fa` is `{11}` alone | V42; these bytes from V80 | **INERT — measured inert.** Ships on inertia |
| 6 | `0x55C0E` (4 B) | `2436e8ea` | `86ff26ef` = `jarl 0xC4B34,lp` | hook that calls the telemetry code cave from the 100 Hz CAN frame builder | diverts 4 bytes of the frame-build path into the cave and back | V31p; these bytes from V53 | CARRIED (instrument) |
| 7 | `0xC4B34`–`0xC4BD7` (164 B) | `0xFF` filler | cave code (`CAVE_V280`), first bytes `243726956032ae05` | five *abs-compare → bit → mask → OR → store* rungs writing an 8-byte buffer at `gp-0x1518`, published as **CAN `0x14A` @ 100 Hz** | **publishes bits only; writes no control cell.** Car behaviour unchanged by the cave itself | body from V31p; hash `d3bb75d8` frozen V105→V281r3 (177 images); **V282 is the first re-point in that span** — 4 displacement halfwords retargeting the b5/b6 comparator operands onto `gp-0x6ADA` (r24) / `gp-0x6B38` (delivered lane torque T) / `gp-0x6B94` | INERT by design (instrument) |
| 8 | `0x55DF2`–`0x55E11` (31 B, incl. `0x55E0F` sar → `0000`) | Honda packer | repointed | the CAN-**427** `MOTOR_TORQUE` source window and its packer shift | publishes the **delivered LKAS-lane torque** `gp-0x6b38` on 427 as `(sign(T)<<9) \| (\|T\|>>3)` | these bytes from V280 | INERT by design (instrument) |
| 9 | `0xC6CD0` | `0xFFFF` (blank; reads −1) | **5346** | the private forward LKAS gain, Q15 (`×5346>>15` = ×0.16315) — reachable only via row 2 | **the ×6 forward gain.** Single largest authority multiplier on the LKAS path (stock effective gain came from `0xC646C` = 891 → ×0.02719) | V57; **5346** chosen at V102 (the first *downward* step, 8× → 6×); unbroken since V260 | MEASURED — dose-response across V101 / V102 / V112 … |
| 10 | `0xC61B2`, `0xC61B4` | 512, 512 | **3072, 3072** | forward-path ± tracking clamps (pre- and post-gain) | track the ×6 gain exactly (`5346×512//891 = 3072`) so the clamp does not bind before the gain does | V102; unbroken since V260 | MEASURED |
| 11 | `0xC62E6` | 7680 | **46080** (reads −19456 as int16) | the LKAS PID **feedback saturation clamp**, stored ×256 | the PID sees ×6 more feedback before saturating; the 1.395 ceiling ratio is preserved structurally | V276 (15360); **46080** at V280 | MEASURED (V280 / V281 arc) |
| 12 | `0xC6446` | 512 | **5244** | the r24 **engaged** rate-lane gain arm — **Lever B**'s value | ×10 stock on the 4-tap bar-torque derivative when engaged. Pulls two symptoms **opposite** ways: it pumps the 7 Hz strong-turn ripple and supplies ~83 % of the 20 Hz grinding mode's damping | V67; 5244 is V88's bracketed optimum, unbroken since V247 | MEASURED — in both directions |
| 13 | `0xC649B` | 0 | 1 | biquad enable cal | with row 3, arms Honda's 55 Hz notch engaged-only. Alone it would be inert | V103; unbroken since V120 | MEASURED (with row 3) |
| 14 | `0xC62EA` | 320 (≈ 4.995 km/h) | **0** | the low-speed steer **lockout** threshold | disables the low-speed LKAS lockout — LKAS keeps authority at creep | V53; restored V81 | CARRIED — **confirmed on-car** (route `1a`: `STEER_STATUS = 0` on 5,995/5,995 frames; 226 frames with `STEER_CONTROL_ACTIVE = 1` below 5 km/h, no fault) |
| 15 | `0xC674E`, `0xC6750`, `0xC675A`, `0xC675C` | 1024, 1024, −1024, −1024 | **5120, 5120, −5120, −5120** | the EME (Excessive-Motor-Effort) soft-limit quad, int16 | the **×5 authority ladder** — raises the EME interlock ceiling so the ×6 gain path is not cut by the shaper. `0xC674E` must stay above the tracking clamp (3072) or the build aborts | V25 → V30 → **V38** | CARRIED — structural interlock, unbroken 247 builds |
| 16 | `0xC6768`, `0xC676A`, `0xC676C` | 0, 1536, 2048 | **5120, 5120, 5120** | the EME ramp triple (3 knots) | same interlock family as row 15 | V31 → V38 | CARRIED — structural, unbroken 247 builds |
| 17 | `0xC6598`, `0xC659C`, `0xC65AC`, `0xC65B0`, `0xC65C4`, `0xC65C8`, `0xC65CC` (f32) | 1.0, 1.0, −1.0, −1.0, 0.0, 1.5, 2.0 | **5.0, 5.0, −5.0, −5.0, 5.0, 5.0, 5.0** | **float mirrors** of rows 15–16 | the shaper compares int against float at ±5 LSB (`int == float×1024`). 🛑 **If the int and float quads disagree the lockstep monitor trips — never revert one alone** | V29 → V30 → V38; V178 tried reverting to Honda 1.0 and was marked `SUPERSEDED-DO-NOT-FLASH-AUTHORITY`; ±5.0 unbroken since V179 | CARRIED — structural, unbroken 106 builds |
| 18 | `0xC40BC`, `0xC40D2`, `0xC40DC` | 600, 102, 22 | 1800, 612, 14 | Coulomb-relay knee · relay gain K1 · α2 (2nd HF filter coefficient) | the relay saturates later; small-signal gain held at V112's value by the knee/K1 pair | V112 (knee/K1), V109 (α2) — on this branch **only because V255 rebased onto V112** | ⚠ **CARRIED BY REBASE** — `0xC40D2` is on record as **measured NULL** at both bands (V88 r73 vs V89 r75+r76). Nobody has re-chosen these three on their merits since the rebase |
| 19 | `0xC61C0`, `0xC61C2`, `0xC61C4` | 1600, 896, 1280 | `0xFFFF` ×3 | `STEER_STATUS` debounce state-machine cals | blanked to max | V36 | 🛑 **UNACCOUNTED** — 12 live readers, 0 writers, present in all 249 images since V36; **no build entry states the intent.** A tracer task is still owed before the next authority change |
| 20 | `0xC64B4`, `0xC64B6` | 24688, 16438 | `0xFFFF` ×2 | `STEER_STATUS` debounce SM cals | blanked to max — disables the gentle-EME debounce | V36 | CARRIED — V36 fixed gentle EME but unmasked DTC 0x49 (row 21) |
| 21 | `0xC64B8` | 112 | 255 | the DTC-0x49 fail-counter increment gate | V37's fix for the dash-light fault V36 unmasked. Also a live torque-arbitration branch (`0x29A78`): raising it makes the full-interpolation arb path apply for torque in (112, 255] | V37 | MEASURED — gentle EME resolved on-car, no dash-light / LKAS-drop regression; the arb side effect is operator-accepted |
| 22 | `0xC64DE` | 17 | 27 | hold count (half-period) of a **sign-flipping square wave** on `gp-0x6b2c`, 8 live read sites. ⚠ **Not** a "re-engage authority ramp" — that label was corrected 2026-08-27 | lengthens that square wave's period from 17 to 27 ticks | V18 | ⚠ CARRIED — road-validated *"drives well"* **under a label later found wrong**, and never re-examined under the correct one |
| 23 | `0xCE000`–`0xD9FFF` (992 B) — rate families at `0xCBF5C`/`0xCC044`/`0xCC12C`/`0xCC214`, boost at `0xCA4F4`/`0xCA23C` | Honda curves | rate-lane Y flattened to `Y[0]` (only ever raises Y); boost flattened to V59's index-weighted mean | the base-assist damper's rate and boost banks, **all mode slots** (34 rate + 68 boost records) | the parametric-pump test with no table-selection escape hatch | V268 | MEASURED — *"V268's damper flatten is inert below 85 deg/s"* |
| 24 | LERP records in `0xE4000`–`0xE8FFF`, pointer table `0xC9A88`, slot-7 record `0xE502C` | `X = 0,12,20,24,32,64,96,128,160,240`; `Y = 0,24,42,50,62,100,126,154,166,172` | **`Y = 0,52,86,103,138,275,413,550,688,1032`** (X unchanged) | the **assist map** — the LKAS rate-loop **reference** the whole loop tracks | a straight line to the ×6 top: `Y = round(6·Ytop·X/240)`, slope **4.30 at every knot** vs Honda's saturating curve. This is `MAP.LINEAR.TO6X` | V280 rev 2 | MEASURED (r35, V281 rev 3 drive) |
| 25 | pointer table `0xCB994`, slot-7 record `0xE5378` | `X = 0,68,112,136,208`; `Y = 248,512,645,696,696` | **`Y = 248,248,248,248,248`** (X unchanged) | the **Kp schedule** of the LKAS rate PID, indexed by demand | removes the rising Kp-vs-demand schedule — constant proportional gain. This is the `KP.FLAT.Y0` the build is named for | V281 rev 3 | MEASURED — the self-sustained 7 Hz cycle is gone (F7 0.0 / 100 s) |
| 26 | pointer table `0xCB844`, slot-7 record `0xE51A8` (+ 7 of the other 9 slots) | `Y = 15360` ×9 | **`Y = 16384` ×9** | the mode/gear **setpoint ceiling** limiting `gp-0x69ae` | +6.7 % on that ceiling | V38 | CARRIED — structural; recorded as *"an AUTHORITY raise, DO NOT revert"* |
| 27 | pointer table `0xCB7D4`, slot-7 record `0xE511C` | `X = 0,11,22,32`; `Y = 128,128,128,128` | **identical — `128,128,128,128`** | the **Kd schedule** of the LKAS rate PID | nothing — listed to close the question, not as a lever. **Kd has never been edited on a flown build.** V290 option S′ would have been the first | — | n/a (verified unchanged) |
| 28 | page-CRC trailers, offset `0xFFC` in each touched 4 KB page | per-page CRC | recomputed | 74 bytes across the diffed pages | recomputed by the builder for every page a lever touches; not itself a lever | every build | BOOKKEEPING |

**Also verified byte-identical to stock on V282** (they matter because later builds moved them, and a
reverting operator should know the revert restores them): `0xC61B6` D clamp 10240 · `0xC61BC` P clamp
15360 · `0xC61BE` PID sum clamp 15360 · `0xC63E6` Ki **0** · `0xC63E8/EA` feedback lag pole **923/1560**
(16.5 Hz — V289 moved this to 875/2301 = 25 Hz) · `0xC63EC/EE` output lag pole 992/507 (5.05 Hz) ·
`0xC646C` shared sensor scale 891 · fade tables `0xCBA04`/`0xCBA74` · override tapers
`0xCB8B4`/`0xCB924`. And the two code-cave hook sites later builds used are **stock filler on V282**:
`0x2A174` = `e53fef73` (V289's notch hook) and `0x29D72` = `6487ce95` (V288's), with `0xC4BDC` and
`0xC4C00` still `0xFF` filler.

---

## 2. THE DELIVERED SURFACE, read from the image

The forward LKAS path, in the arithmetic the bytes actually implement:

```
0xE4 command  →  override taper (live arm 255)  →  demand index idx   [1 LSB = 16.126 raw counts]
      →  assist map (row 24, LERP over X/Y)     →  rate setpoint
      →  E = 32·setpoint − feedback(two-sample sum, DC 30.89, lag pole 0xC63E8/EA)
      →  P = E·Kp>>8      [Kp = 248 flat, row 25]      D on the error [Kd = 128 flat, row 27]
      →  S = clamp(P + D, ±15360)                      [0xC61BE, stock]
      →  T = clamp(S × G >> 15, ±OUT)                  [G = row 9, OUT = row 10]
      →  5.05 Hz output lag  →  motor
```

| quantity | stock | **V282** | ratio |
|---|---|---|---|
| assist-map top (`X = 240`) | 172 | **1032** | ×6.00 |
| assist-map slope, every knot | 0.10 → 0.72 (saturating) | **4.30 flat** | — |
| Kp at demand index 208 | 696 | **248** | ×0.36 |
| forward gain `G` | 891 (`0xC646C`) → ×0.02719 | **5346** (`0xC6CD0`) → ×0.16315 | ×6.00 |
| forward output clamp `OUT` | 512 | **3072** | ×6.00 |
| **peak delivered forward torque** `clamp(15360·G>>15, OUT)` | **417 counts** (clamp does **not** bind) | **2505 counts** (clamp does **not** bind) | **×6.00** |

**The ×6 is real authority, not a clamp artefact — in neither image does the output clamp bind at the
sum clamp's ceiling.** [EVIDENCE: both products computed from the byte values above.]

---

## 3. WHAT THIS MEANS FOR THE OPERATOR, PLAINLY

Reverting V289 → V282 restores exactly three things and nothing else — the V289 delta is 185 bytes:

1. The **notch code cave is gone.** `0x2A174` returns to Honda's `ld.hu`, `0xC4C00`–`0xC4C8B` and
   `0xC4BDC`–`0xC4BF7` return to `0xFF` filler. The 20 Hz content the notch was removing from the loop
   output is back in it.
2. The **feedback lag pole returns to 16.5 Hz** (`0xC63E8/EA` 875/2301 → 923/1560). Loop phase at
   20 Hz loses the +11.5° V289 bought.
3. Telemetry bits **b5/b7 on CAN `0x14A` byte 4 revert to V282's meaning** (b5/b6 = the r24
   comparators). Any decoder pointed at V289's b5 = `sign(S − y)` / b7 = `|S − y| ≥ |y|` will read
   nonsense on V282 — **attribute the build from the tap, not from the label.**

Everything in the table above — the ×6 authority chain, Lever B, the linear map, the flat Kp, the EME
ladder, the two instruments — is **unchanged by the revert**. In symptom terms the operator is
choosing to take the **20 Hz grinding back** in exchange for losing the 15–17 Hz line V289 relocated
it to; nothing about steering authority changes in either direction.

**Three groups are still not clean deliberate choices** and are unchanged by this session:
row 19 (`0xC61C0/C2/C4`, no lineage entry at all despite 12 live readers across 249 images), row 18
(`0xC40BC/D2/DC`, riding the V255→V112 rebase, with `0xC40D2` on record as measured NULL), and row 22
(`0xC64DE`, road-validated under a label later shown wrong). Row 5 (`0x454FE`) is measured inert and
ships on inertia alone.

*Written at close-out, 2026-09-09, agent `closeout` for orchestrator `main`. Analysis only — nothing
was built, flashed, or sent on the wire.*
