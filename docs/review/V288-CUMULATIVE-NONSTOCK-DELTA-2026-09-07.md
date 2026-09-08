# V288 rev 2 — cumulative non-stock delta, read from the built image

**Date** 2026-09-07 · subagent for orchestrator `main` · **Method** raw Python little-endian byte diff,
`stock_fw_dump/code.bin` vs `_v282_..._plain_image.bin`, extent `[0x13000, 0x100000)`. **No Ghidra
database opened.** Independently reproduced: **1,984 bytes / 311 runs (gap≤2 merge)**, byte-identical
in count and value to the existing `docs/specs/V282-NONSTOCK-DELTA-2026-09-04.md` (578 runs at a
tighter merge threshold, same 1,984 bytes) — cross-checked cell-by-cell against that file and against
`docs/BUILD-LINEAGE.md` / `BUILD-LINEAGE-PART1-LEVER-INDEX.md`.

**V288 rev 2 = V282 + `{hook 0x29D72, cave exit 0xC4BD6, telemetry rung 0xC4BDC–0xC4BFD, filter cave
0xC4C00–0xC4C2F, CRC 0xC4FFC}` — no cal byte moves.** I was not given a V288 image, so rows 29–33 below
are **taken from the orchestrator's brief, not independently diffed** — flagged accordingly.

I could not obtain stock's sha256 in this session (no hash step in my script) — cite
`docs/specs/V282-NONSTOCK-DELTA-2026-09-04.md`'s header (`stock 3f1d55a98aac6e73…`,
`V282 0ea98d06b292ca1a…`) for the artifact hashes.

---

## The grouped delta (33 rows)

`status`: **MEASURED** = scored on-car · **INERT/UNVERIFIED** · **CARRIED** = deliberate at its
introducing build, not re-chosen since · **CARRIED BY REBASE** = riding a base rather than a decision ·
**UNACCOUNTED** = no lineage entry states the intent · **FROM BRIEF** = V288-specific, per main, not
independently diffed here.

| # | address(es) | stock | V282/current | what it physically is | what it does to the car | introduced | status |
|---|---|---|---|---|---|---|---|
| 1 | `0x13109`, `0x14120` | `2d` (`-`) | `2c` (`,`) | version-string byte the UDS read reports | marks the image non-stock on a version query; no control effect | V22 | BOOKKEEPING |
| 2 | `0x2A1F0` | disp `0x746C` | disp `0x7CD0` | displacement of the forward-LKAS gain load | repoints the forward path off the shared sensor-scale cal `0xC646C` onto the private `0xC6CD0`, so the LKAS gain can move independently | V57, lost in V38 rebase, restored V81 | CARRIED (structural — makes `0xC6CD0` reachable) |
| 3 | `0x35A08`,`0x35A12`,`0x35A18` | `e7 98`·`ec`·`e9` | `fb 97`·`e0`·`ea` | biquad ARM flag source (`gp-0x671a`→`gp-0x6806`) + arm comparison + branch condition | arms Honda's dormant 55 Hz notch **engaged-only**; the old ≥5 condition was never observed true in 255k engaged frames | V103 | MEASURED |
| 4 | `0x3AA96` | `c5` | `fb` | rate-lane (r24/r26) gate byte: `gp-0x683c` (dead) → `gp-0x6806` (`STEER_CONTROL_ACTIVE`) | **Lever B is live** — r24 runs the engaged gain `0xC6446` on the 4-tap derivative of bar torque when LKAS is engaged | V67, current bytes from V104 | MEASURED — operator on V88: "the audible grinding is fixed" |
| 5 | `0x454FE` | `ba` | `b5` | one substitution byte in the `gp-0x67fa` selector path | V42's ratchet-fix substitution | V42, current run from V80 | **INERT — measured inert** (reachable set of `gp-0x67fa` is `{11}` alone); shipping on inertia only |
| 6 | `0x55C0E` | 4 B stock frame-build code | `jarl 0xC4B34,lp` | hook that calls the code cave from the 100 Hz frame builder | diverts 4 bytes of the frame-build path into the cave and back | V31p, current bytes from V53 | CARRIED (instrument) |
| 7 | `0xC4B34`–`0xC4BD7` (164 B) | `0xFF` filler | cave code, `CAVE_V280` | 5 "abs-compare→bit→mask→OR→store" rungs writing an 8-byte buffer at `gp-0x1518`, published as CAN `0x14A` @100 Hz | **publishes bits only — writes no control cell.** Behaviour unchanged by the cave itself | body from V31p; sha `d3bb75d8` frozen V105→V281 rev3 (177 images); **V282 is the first re-point in that span** (4 displacement halfwords: bit-6 operand A `gp-0x6B94`→`gp-0x6ADA(r24)`, operand B `gp-0x4F64`→`gp-0x6B38(T)`; bit-5 operand A `gp-0x6AE2`→`gp-0x6ADA(r24)`, operand B `gp-0x6B26`→`gp-0x6B94`) | INERT by design |
| 8 | `0x55DF2`+`0x55E0F` (31 B) | Honda packer | repointed | CAN-427 `MOTOR_TORQUE` source window + its `sar` shift | publishes the delivered LKAS-lane torque `gp-0x6b38` on 427: `(sign(T)<<9)\|(\|T\|>>3)` | current bytes from V280 | INERT by design (instrument) |
| 9 | `0xC6CD0` | `0xFFFF` (blank) | **5346** | private forward LKAS gain (reachable only via row 2) | the **6× forward gain** — single largest authority multiplier on the LKAS path | V57; 5346 chosen V102 (first *downward* step, 8×→6×); unbroken from V260 | MEASURED (dose-response V101/V102/V112…) |
| 10 | `0xC61B2`, `0xC61B4` | 512, 512 | 3072, 3072 | forward-path ± tracking clamps | track the 6× gain exactly (`5346×512//891=3072`) so the clamp doesn't bind before the gain does | V102; unbroken from V260 | MEASURED |
| 11 | `0xC62E6` | 7680 | **46080** | LKAS PID feedback saturation clamp (stored ×256) | PID sees 6× more feedback before saturating; 1.395 ceiling ratio preserved structurally | V276 (15360); 46080 at V280 | MEASURED (V280/V281 arc) |
| 12 | `0xC6446` | 512 | **5244** | r24 engaged rate-lane gain arm (**Lever B**'s value) | ×10 stock on the bar-torque derivative when engaged. Pulls two symptoms opposite ways: pumps the 7 Hz strong-turn ripple, supplies ~83 % of the 20 Hz grind's damping | V67; 5244 is V88's bracketed optimum, unbroken from V247 | MEASURED (both directions) |
| 13 | `0xC649B` | 0 | 1 | biquad enable cal | with row 3, arms Honda's notch engaged-only — alone it would be inert | V103; unbroken from V120 | MEASURED (with the arm repoint) |
| 14 | `0xC62EA` | 320 | 0 | low-speed steer lockout threshold (4.995 km/h) | disables the low-speed LKAS lockout — LKAS keeps authority at creep | V53, restored V81 | CARRIED — CONFIRMED on-car (route `1a`: `STEER_STATUS=0` 5,995/5,995 frames, 226 frames `STEER_CONTROL_ACTIVE=1` below 5 km/h, no fault) |
| 15 | `0xC674E`,`0xC6750`,`0xC675A`,`0xC675C` | 1024,1024,−1024,−1024 | 5120,5120,−5120,−5120 | EME soft-limit quad (±A, ±B, int16) | the ×5 authority ladder — raises the Excessive-Motor-Effort interlock ceiling so the 6× gain path is not cut by the shaper. `0xC674E` must stay above the tracking clamp (3072) or the build aborts | V25→V30→**V38** | CARRIED — structural interlock, unbroken 247 builds |
| 16 | `0xC6768`,`0xC676A`,`0xC676C` | 0,1536,2048 | 5120,5120,5120 | EME ramp triple (3 knots) | same interlock family as row 15 | V31→V38 | CARRIED — structural, unbroken 247 builds |
| 17 | `0xC6598`,`0xC659C`,`0xC65AC`,`0xC65B0`,`0xC65C4`,`0xC65C8`,`0xC65CC` (float) | 1.0f,1.0f,−1.0f,−1.0f,0.0f,1.5f,2.0f | all **±5.0f** | float mirrors of rows 15–16 | shaper compares int vs float at ±5 LSB (`int == float×1024`); **if int/float quads disagree the lockstep monitor trips** — do not revert alone | V29→V30→V38; V178 tried reverting to Honda 1.0 and was marked SUPERSEDED-DO-NOT-FLASH-AUTHORITY; ±5.0 unbroken from V179 | CARRIED — structural, unbroken 106 builds |
| 18 | `0xC40BC`,`0xC40D2`,`0xC40DC` | 600, 102, 22 | 1800, 612, 14 | Coulomb-relay knee, relay gain K1, α2 (2nd HF filter coeff) | relay saturates later; small-signal gain held at V112's value by the knee/K1 pair | V112 (knee/K1), V109 (α2); on this branch **only because V255 rebased onto V112** | ⚠ **CARRIED BY REBASE** — `0xC40D2` measured NULL at both bands (V88 r73 vs V89 r75+r76); nobody has re-chosen these three on their own merits since the rebase |
| 19 | `0xC61C0`,`0xC61C2`,`0xC61C4` | 1600, 896, 1280 | `0xFFFF`×3 | `STEER_STATUS` debounce SM cals | blanked to max | V36 | 🛑 **UNACCOUNTED** — 12 live readers, 0 writers, present in all 249 images since V36; no build entry states the intent (grouped with row 20 in a summary that doesn't cover blanking 3 cells to max). Recommend a tracer task before the next authority change |
| 20 | `0xC64B4`,`0xC64B6` | 24688, 16438 | `0xFFFF`×2 | `STEER_STATUS` debounce SM cals | blanked to max — disables the gentle-EME debounce | V36 | CARRIED — V36 fixed gentle EME but unmasked DTC 0x49 (see row 21) |
| 21 | `0xC64B8` | 112 | 255 | DTC-0x49 fail-counter increment gate | V37's fix for the dash-light fault V36 unmasked; also a live torque-arbitration branch (`0x29a78`) — raising it makes the full-interpolation arb path apply for torque in (112,255] | V37 | MEASURED — gentle EME resolved on-car, no dash-light/LKAS-drop regression (operator-accepted side effect on the arb branch) |
| 22 | `0xC64DE` | 17 | 27 | hold count (half-period) of a sign-flipping square wave on `gp-0x6b2c` (**not** a "re-engage authority ramp" — 2026-08-27 correction), 8 live read sites | lengthens the square wave's period 17→27 ticks | V18 | ⚠ CARRIED, road-validated "drives well" **under a label later found wrong**; never re-examined under the correct label |
| 23 | `0xCE000`–`0xD9FFF` (992 B), families at `0xCBF5C`/`0xCC044`/`0xCC12C`/`0xCC214` (rate, ~484 B) + `0xCA4F4`/`0xCA23C` (boost, ~496 B) | Honda curves | rate-lane Y flattened to Y[0] (only ever raises Y); boost flattened per record to V59's index-weighted mean | the parametric-pump test with no table-selection escape hatch — every mode slot covered (34 rate slots + 68 boost records) | V268 | MEASURED — "V268's damper flatten is inert below 85 deg/s" |
| 24 | `0xE4000`–`0xE8105` (392 B), pointer table `0xC9A88` | saturating Honda curve, slot-7 top 172 | straight line to the ×6 top: `Y=round(6·Ytop·X/240)`, slot-7 top 172→1032, slope 4.30 at every knot | the LKAS rate-loop **reference** the whole loop tracks — linear, 6× steeper demand→rate map (`MAP.LINEAR.TO6X`) | V280 rev 2 | MEASURED (r35, V281 rev 3 drive) |
| 25 | `0xE4360`+ (198 B), pointer table `0xCB994` | slot-7 Y `[248,512,645,696,696]` (other slots rising 205/266/307-family) | flat at Y[0]: slot 7 `[248,248,248,248,248]` | removes the rising Kp-vs-index schedule — constant proportional gain in the rate PID; X axes untouched | V281 rev 3 (`KP.FLAT.Y0` — the mod this V282 build is named for) | MEASURED — the self-sustained 7 Hz cycle is gone (F7 0.0/100 s) |
| 26 | `0xE4194`,`0xE41BC`,… (72 B), pointer table `0xCB844` | 15360 flat, 8 records × 9 knots | 16384 flat | +6.7 % on the mode/gear setpoint ceiling limiting `gp-0x69ae` | V38 | CARRIED — structural, "an AUTHORITY raise, DO NOT revert" |
| 27 | Kd LERP records, `0xCB7D4`, 28×20 B | 128 flat | **128 — stock, unchanged** | not touched by V282 despite the brief's expectation of a Kd delta | — | n/a (listed to close the "Kd bank" question, not a lever) |
| 28 | page-CRC trailers, offset ≥`0xFFC` in each 4 KB page | per-page CRC | recomputed | 21 runs / 74 B total across the diffed pages | recomputed by the builder for every page a lever touches; not itself a lever | every build | BOOKKEEPING |
| 29 | `0x29D72` (hook) | — | new `jarl`-class hook | V288 rev 2's hook into the frame-build path, analogous in role to row 6's `0x55C0E` | routes into the new filter/telemetry cave | V288 rev 2 | **FROM BRIEF, not independently diffed** — no cal byte moves per main |
| 30 | `0xC4BD6` (cave exit) | — | new exit stub | terminates/returns from the extended `0xC4B34` cave body | closes the V288 rev 2 cave extension cleanly back to the hook site | V288 rev 2 | **FROM BRIEF** |
| 31 | `0xC4BDC`–`0xC4BFD` (telemetry rung) | — | new code | an added telemetry rung appended to the `CAVE_V280` body (row 7) | publishes additional bits/values, read-only by design per the kit's cave doctrine | V288 rev 2 | **FROM BRIEF** — verify GATE 1/2 and "publishes only" independently before flight per `CLAUDE.md`'s cave rule |
| 32 | `0xC4C00`–`0xC4C2F` (filter cave) | — | new code, 48 B | a filter computation added alongside the telemetry rung | feeds/derives a filtered quantity for the new telemetry; **confirm read-only vs any write to a live control cell** — not verifiable without the image | V288 rev 2 | **FROM BRIEF — unverified read/write status** |
| 33 | `0xC4FFC` (CRC) | see row 28 family | recomputed | page-CRC trailer for the `0xC4xxx` page, recomputed after rows 29–32 | bookkeeping only | V288 rev 2 | **FROM BRIEF**, BOOKKEEPING |

---

## Summary

Of the 1,984 non-stock bytes I independently diffed between stock and V282, **86 % are calibration
levers** (four table families — the V268 rate-lane/boost flatten, the V280 rev 2 assist-map
linearization, the V281 rev 3 Kp flatten, and the V38 setpoint-ceiling raise — plus 26 in-place cal
cells), **10 % is read-only telemetry instrumentation** (the `0xC4B34` cave, its `0x55C0E` hook, and
the `0x55DF2` 427 torque-tap window, none of which write a control cell), **3.7 % is CRC bookkeeping**,
and the remainder is a version-string marker and six small code-region repoints. Every calibration row
above is traceable to a specific introducing build in `docs/BUILD-LINEAGE.md` /
`BUILD-LINEAGE-PART1-LEVER-INDEX.md`, cross-checked against the existing
`docs/specs/V282-NONSTOCK-DELTA-2026-09-04.md`, and I found no run in my own diff that document does not
already explain.

Three groups are **not clean deliberate choices**: `0xC61C0/C2/C4` (row 19) has no lineage entry at all
despite 12 live readers across 249 images; `0xC40BC/D2/DC` (row 18) rides the V255→V112 rebase rather
than a decision made on this branch, and `0xC40D2` is on record as measured NULL; and `0xC64DE`
(row 22) was road-validated under a label later shown to be wrong and has never been re-assessed under
the correct one. `0x454FE` (row 5) is measured inert and ships on inertia alone. V288 rev 2's own
additions (rows 29–33) move **no calibration byte** — they are new code only, per the orchestrator's
brief — but I could not verify that from an image; rows 31–32 in particular should get an independent
read/write check against `0x14A` and any live control cell before flight, consistent with the kit's
GATE 1/GATE 2 cave rule.

No run in my diff went unattributed.
