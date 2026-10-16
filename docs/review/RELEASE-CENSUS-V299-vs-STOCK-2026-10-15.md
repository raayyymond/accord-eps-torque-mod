# RELEASE CENSUS — every byte V299 differs from STOCK, classified for the release cleanup (2026-10-15)

> ## Corrections (2026-10-15, from the four adversarial lenses and the GATE 2 re-score — applied in place below)
> The release that was BUILT from this census is **V300 rev 2** (`analysis-2020accord/studies/release/BUILD-V300-REPORT.md`):
> **766 B vs stock in 8 CRC blocks** (main, 0xC6, 0xD7, 0xE4–0xE8), **2110 B vs V299** — not the "≈ 740 B / 5 pages" first
> estimated in §2 (the Kp/Kd records span five pages; rev 2 keeps 13 DampAxis bytes in page 0xD7).
> 1. **D9 premise wrong (two lenses, E):** `gp-0x682f` is the **driver bar torque** `min(|gp-0x4f60| >> 5, 255)`, not the map
>    output (`r15` is loaded from `gp-0x4f60` at `0x28F26` and never overwritten before the store at `0x29068`; the decompiler
>    re-used its `iVar28`). `gp-0x6830` is a lag of the same bar torque; `gp-0x6a34` is the filtered rate feedback. The map's
>    output is **dead end to end** in the angle images (E4 loads `gp-0x69ae` directly), so **the revert stands**, on firmer
>    ground: none of the 17 sites changes when the map returns to Honda's values. `LENS-SIDECHANNELS-D9-D6-D7.md`, `LENS-INTERLOCKS-V300.md`.
> 2. **D6 stock values mis-transcribed:** `0xC64B4..B7` stock = **112 / 96 / 54 / 64** (hex read as decimal gave 70/60/36/40).
>    Keeping the package leaves Honda's driver-torque-transient STEER_STATUS = 4 trip and the DTC 0x49 over-torque counter OFF,
>    as on every flown build since V37 — disclosed on the release page.
> 3. **D5 split (GATE 2 report §1, E):** `0xC40DC` is the **DampAxis producer's EMA α2** (`FUN_00041464`, a torque-path cell) —
>    **KEPT at 14** in the release; `0xC40BC` (relay knee) and `0xC40D2` (K1) are observer-side (`FUN_0003b8f6` → plausibility
>    latch, no command written) — reverted to stock.
> 4. **D8 split (GATE 2, FAIL on the full revert):** the DampAxis Y rows `0xD7A5C..61` and `0xD7A6C..71` (−29490, −17202, −16000 ×2)
>    are **KEPT at V299's values** — reverting them drops GM 20 → 5.2 dB and raises the 5–30 Hz closed-loop peak +5.4 dB at 3 m/s
>    on the light-inertia member. The rest of D8 (r24 rate-axis flatten, damper/boost families) and D3 (r24 gate + arm) revert
>    cleanly (ΔPM −0.7…+0.1°, GM ≥ 20 dB). `GATE2-RESCORE-STOCK-PLANT-TERMS.md`.
> 5. **C2 gap:** the telemetry cave also forced **0x14A byte 7 bits 6–7** to 11 (`0xC4BC0..0xC4BCE`); the release restores both
>    bytes to stock. The 7 freed byte-4 bits' boot value on a stock car is BELIEF (`LENS-TELEMETRY-REMOVAL.md`).
> 6. Interlocks-lens disclosures carried to the page: the A7 EME ladder (1024 → 5120) loosens Honda's excessive-motor-effort
>    protection ≈ 5× in ALL driving, not only engaged; with a stock camera the car is LKAS-inert + Honda base assist, not stock
>    Honda LKAS; the lane has no ramp-out on a request drop.

Study artifact; nothing built, flashed or sent. Agent `fw-census` (fork) for orchestrator `main`.
**E** = EVIDENCE (method given) · **B** = BELIEF. `gp = 0xFEDF8000`, `tp = 0xBF000`.

| image | sha256 (prefix) |
|---|---|
| stock `stock_fw_dump/code.bin` | `3f1d55a9…` |
| V299 `_v299_V299-ANGLELOOP.C3REV2P.CAM-…A16B_plain_image.bin` | `30ff05fa…` |

**Diff extent `[0x13000, 0x100000)`: 2,471 differing bytes in 432 runs** (E: raw Python byte compare,
`analysis-2020accord/studies/release/release_census_v299_vs_stock.py`, 0.2 s). **Every one of the 2,471 bytes
is attributed to exactly one row below; the script asserts zero orphans** (E). JSON: `analysis-2020accord/_scratch/out/release_census_v299.json`.
Values below were re-read from the two images (record tables walked from their pointer tables at `0xC9A88`
map / `0xCB994` Kp / `0xCB7D4` Kd / `0xCB844` LIM / `0xCBAE4` fadeB2), not from any build script.
Lineage attribution (the "introduced" column) is from `docs/review/V282-CUMULATIVE-NONSTOCK-DELTA-2026-09-09.md`
and the V293/V294/V295/V298/V299 build docstrings.

| class | bytes | rows |
|---|---|---|
| **A** angle-loop structure | 322 | A1–A7 |
| **B** angle-loop tuning | 393 | B1–B4, B3x, B4x |
| **C** telemetry | 199 | C1–C3 |
| **D** legacy | 1,484 | D1–D11 |
| **E** CRC trailers | 73 | E1 |

Ghidra: the single open program is the STOCK `code.bin` (`list_open_programs`); not switched. Decompiles of
`FUN_00028ea6` (the LKAS lane) and `FUN_0003aa2c` (the r24/aggregator stage) were read for the liveness verdicts.

---

## 1. The census

### A — ANGLE-LOOP STRUCTURE (keep; the loop does not exist without them)

| id | address | stock → V299 | what it is | introduced | note |
|---|---|---|---|---|---|
| A1 | `0x13109`, `0x1310D` | `-`,`0` → `,`,`B` | F181 string `39990-TVA,A16B` at `0x13100` — the fork's firmware interlock (`39990-TVA,A16`+letter) | `,` V22; letter V298/V299 | E: carFw read A16A on route 79. The release letter is the orchestrator's call (A16C?). |
| A2 | `0x28F4E` (2) `0x29A50` (4) `0x29A56` (1) `0x29D6A` (4) `0x29D76` (4) `0x29EE0` (4) | see V298 docstring §0 | E1 x := θ (gp-0x6a00) · B2/A2 PID-run guard (ramp≠0 ∧ request==1) · E4 sp := gp-0x69ae · HOOK `jarl 0xC4C00` · OPH D operand = fresh rate | V298 | `0x28FA4` is STOCK on V299 (V294's `subr` undone by V298) — not in the diff. |
| A3 | `0xC4C00..0xC4D03` (260 B, 258 differ: two bytes coincide with `0xFF`) | filler → cave | G(v) 6-knot table, E′=(E·G)>>8, Ki arithmetic, A3 θ-referenced integral bound (asymmetric, two-level cap), 1229 hand freeze, op-skip `jr 0x2A164`, camera gate on gp-0x6803 == 2 | V298, re-laid V299 | Tuning constants live INSIDE this cave (G rows, 1229, 4096/6144, 1250). |
| A4 | `0xC63E8` a, `0xC63EA` b, `0xC62E6` C, `0xC62E4` DB | 923/1560/7680/4 → 0/8192/65535/0 | Honda's fb-lag re-purposed: s = 8θ, r26 = 16θ, clamp open, I deadband 0 | V298 | E: V298 §0. |
| A5 | `0xE54FC` record (26 B: X[6] + Y[6] from +2) | dir-2 fadeB2 X/Y → copy of dir-0 fadeB `0xE564C` | the post-PID hand-fade arm the gp-0x6803 == 2 interlock selects, neutralised to the stock arm's feel | V298 | E: both records dumped; V299 record = (16,26,38,48,64,96 / 255,243,218,179,77,…). |
| A6 | `0x2A1F0` disp `0x746C→0x7CD0`; `0xC6CD0` `0xFFFF→5346`; `0xC61B2`,`0xC61B4` 512→3072 | — | the **authority chain**: forward LKAS gain repointed from the shared sensor scale `0xC646C` (891) to a private Q15 cell (×6.00), with the two forward clamps tracking it exactly (5346·512//891 = 3072) | V57/V102 | **LIVE-REQUIRED** (E): `0x2A1EE ld.h 0x7cd0,tp` is the lane's output gain (`T = clamp((y·G)>>15, ±0xC61B4)` → `gp-0x6b38`, decompile lines 1246–1265). Reverting G to 891 cuts the lane rail 2461 → ~417 counts (×1/6); the whole C3-rev2-P design (Kp 112, Ki 40, A3 bound in S units) was scored on this rail. |
| A7 | int16 `0xC674E/50/5A/5C` ±1024→±5120, `0xC6768/6A/6C` 0/1536/2048→5120; f32 `0xC6598/9C/AC/B0/C4/C8/CC` → ±5.0 | — | the EME (excessive-motor-effort) soft-limit quad + ramp and their float mirrors (lockstep monitor compares int vs float×1024) | V25→V38 | **LIVE-REQUIRED** (B, inherited from the record: the shaper would cut the ×6 lane; `0xC674E` must stay > 3072). 🛑 Never move int without float. |

### B — ANGLE-LOOP TUNING (keep; values are the orchestrator's/1b's to set)

| id | address | stock → V299 | note |
|---|---|---|---|
| B1 | `0xC63E6` Ki | 0 → 40 | the integral gain Honda ships at zero |
| B2 | `0xC61BA` ICL | 10240 → 8192 | I clamp (icl = (ICL<<10)>>3) |
| B3 | `0xE5378`+12 (slot-7 Kp Y×5) | 248,512,645,696,696 → 112 ×5 | Kp flat; index = demand index (|raw|/16.126) |
| B4 | `0xE511C`+10 (slot-7 Kd Y×4) | 128 ×4 → 48 ×4 | Kd on the fresh rate (OPH) |
| **B3x** | the OTHER 27 Kp records (270 B) | stock schedules 205…717 → **960 flat** | 🛑 **V294 torque-mode leftover** (V298 re-wrote slot 7 only). If the selector (measured 7, max 9) ever lands elsewhere the angle loop runs at Kp 960 = ×8.6. **Release: write 112 flat on all 28** (V293's own rule: every slot must land on the same surface). |
| **B4x** | the OTHER 27 Kd records (108 B) | 128/64 → **0** | V293 leftover. **Release: 48 on all 28** for the same reason. |

### C — TELEMETRY (remove all; the operator's instruction)

| id | address | stock → V299 | what it is | introduced |
|---|---|---|---|---|
| C1 | `0x55C0E` (4) | Honda frame-builder bytes → `jarl 0xC4B34` | hook from the 100 Hz CAN frame builder into the probe cave | V31p/V53 |
| C2 | `0xC4B34..0xC4BD7` (164 B) | `0xFF` → `CAVE_V280` | five compare→bit rungs writing two bytes of the 8-byte buffer at `gp-0x1518` (writes `gp-0x1514` and `gp-0x1511` only), published on CAN `0x14A` byte 4 bits 3–7 **and byte 7 bits 6–7 (forced 11 at `0xC4BC0..0xC4BCE`; lens correction 2026-10-15)** | V105 body, V282 operands |
| C3 | `0x55DF2..0x55E11` (31 B) | Honda's `MOTOR_TORQUE` packer → repointed | CAN-427 tap: `(sign(T)<<9) \| (\|T\|>>3)` of `gp-0x6b38` (the lane torque) | V280 |

E: the angle-loop cave has no reference to any of these (V298: 0 RAM, one hook at `0x29D76`); removing C restores
Honda's 0x14A byte 4 and 427 content. **Cost, stated:** the drive-read instrument (`angle_loop_drive_read.py`) loses
the lane tap and the 0x14A status bits — the release is observable only through 0x18F/0xE4/0x1AB. The operator
has accepted this ("including the torque output too").

### D — LEGACY, with the angle-path liveness verdict

| id | address | stock → V299 | what it is | introduced | **verdict** | basis |
|---|---|---|---|---|---|---|
| D1 | `0x454FE` | `0xBA→0xB5` | substitution byte in the `gp-0x67fa` selector path | V42/V80 | **INERT → revert** | E (record): reachable set of `gp-0x67fa` is {11}; measured inert. |
| D2 | `0x35A08/12/18` + `0xC649B` | arm flag source `gp-0x671a→gp-0x6806`, cmp/branch; cal 0→1 | arms Honda's dormant ~55 Hz biquad notch, engaged-only (base-assist sensor path) | V103 | **LIVE-UNNEEDED → revert** | B: it was a grinding lever (20 Hz era). The angle loop has ring 0 % / F7 0 without any claim on it; crossover 0.4–0.6 Hz, 100× below the notch. GATE 2 impact nil (phase at < 1 Hz unaffected). Flag: the V298/V299 flights had it ON. |
| D3 | `0x3AA96` `0xC5→0xFB` + `0xC6446` 512→2048 | r24 lane gate byte `gp-0x683c`(dead)→`gp-0x6806` (STEER_CONTROL_ACTIVE); engaged gain arm | V67/V104 + V293 | **LIVE-UNNEEDED → revert (both together)** | E (decompile `FUN_0003aa2c`): `gain = (gp-0x671d≠0) ? 0xC6442 : (gate≠0 ? 0xC6446 : (bVar1 ? LERP(gp-0x6e38 table) : 0xC6440))`. On V299 while engaged the r24 damping lane runs at a flat 2048; on stock it runs Honda's speed LERP from the row-D8 bank (the gate is dead in stock, so `0xC6446` is unreachable = "Lever B unreachable"). The angle design never used r24 (not in C3-rev2-P). Reverting restores Honda's engaged r24 = Honda's disengaged r24. **GATE 2 re-scored 2026-10-15: REVERT, clean — ΔPM −0.7…+0.1°, GM ≥ 20 dB, L20 ≤ 1.01× (r24 is a driver-torque-DERIVATIVE lane on the hands-off twist, not a wheel-rate damper)** (B before the re-score: effect small — r24 measured "pumps 7 Hz / damps 20 Hz" at 5244; at 2048-vs-LERP the difference is a fraction of that). |
| D4 | `0xC62EA` | 320 → 0 | low-speed LKAS lockout threshold (≈5 km/h) | V53/V81 | **LIVE — operator decision; recommend KEEP** | E (record): on-car, STEER_STATUS 0 at creep, no fault. The goal says "at every speed"; stock would drop the loop below 5 km/h (parking/creep). Not required by the loop's arithmetic; required by the goal. One halfword. |
| D5 | `0xC40BC` 600→1800, `0xC40D2` 102→612 — **and, split out 2026-10-15: `0xC40DC` 22→14** | relay knee / K1 = the base-assist Coulomb relay inside the plant-model OBSERVER (`FUN_0003b8f6`, writes no command); **`0xC40DC` = the DampAxis producer's EMA α2 (`FUN_00041464`), a TORQUE-PATH cell** | V112/V109, carried by the V255 rebase | **knee/K1: LIVE-UNNEEDED → reverted (release). α2 `0xC40DC`: KEPT at 14 (GATE 2, corrections 3–4)** | E (GATE 2 report §1): the knee/K1 feed only the observer → plausibility latch; stock K1 102 ran under the ×6 lane V38→V88 without a trip. α2 is part of the DampAxis lane whose revert fails GATE 2. The earlier text filed all three as base-assist friction cells (B); corrected. |
| D6 | `0xC61C0/C2/C4` 1600/896/1280→`0xFFFF`; `0xC64B4..B7` 112/96/54/64→`0xFF` (corrected 2026-10-15; the earlier 70/60/36/40 read hex as decimal); `0xC64B8` 112→255 | STEER_STATUS debounce SM cals (gentle-EME), DTC-0x49 fail-counter gate | V36/V37 | **LIVE-REQUIRED (as a package) — keep** | E (record, on-car): with ×6 lane authority the stock debounce trips the gentle-EME STEER_STATUS fault; V36 fixed it, unmasked DTC 0x49, V37 fixed that. ⚠ `0xC61C0..C4` has 12 live readers and NO lineage entry stating intent (still owed a trace). ⚠ `0xC64B8` has a second role: the arb branch at `0x29A78` compares it against `gp-0x682f` (the map-scaled demand byte, see D9) — if D9 reverts, that comparison runs on Honda's scale again. Hand to the interlock lens. **Lens result (E): 12 readers named (6 in the live arbitration function, 6 in the uncalled `FUN_0002a30e`); 0xFFFF switches off the bar-torque-derivative terms, and with `0xC64B4..B8` at 255 the STEER_STATUS = 4 driver-torque trip can never fire — a disabled protection, disclosed on the page.** |
| D7 | `0xC64DE` | 17 → 27 | hold count of a sign-flipping square wave on `gp-0x6b2c` (8 read sites); label "re-engage ramp" was wrong | V18 | **LIVE-UNNEEDED → revert** | B: chosen under a wrong label, never re-examined; the loop design does not reference it; stock is Honda's validated value. Unknown function → the SAFE direction is stock. Flag for the lens: name the 8 readers' function. |
| D8 | `0xCE000..0xD9FFF` (992 B: rate families `0xCBF5C/0xCC044/0xCC12C/0xCC214`, boost `0xCA4F4/0xCA23C`, friction-comp Y `0xD7A5C/6C`) | Honda curves → rate Y flattened up, boost flattened to a mean, friction Y ×2–3 | the **base-assist damper banks, all mode slots** — what the driver feels hands-on, and the r24 LERP source of D3 | V268 (V105 for `0xD7A5C`) | **SPLIT (GATE 2 re-score 2026-10-15): the DampAxis Y rows `0xD7A5C..61` / `0xD7A6C..71` (12 B) are KEPT at V299's values; everything else in the banks → reverted** | E: live in manual AND engaged (the aggregator sums these lanes in `FUN_0003aa2c`). Measured "inert below 85 deg/s" (V268) — the loop rides the fork's 120 deg/s cap, so part of the envelope is above that. **Re-scored (`GATE2-RESCORE-STOCK-PLANT-TERMS.md`; E for the arithmetic, B for the lane signs): the full revert FAILS (GM 20 → 5.2 dB, |T| +5.4 dB at 3 m/s, Ms 1.26 → 2.68 on J_lo) because the DampAxis lane is a lagged positive-inertia term the identified plant already contains; with its 13 bytes (12 here + `0xC40DC`) kept, the rest of D8 and D3 revert with GM ≥ 20 dB and ΔPM within ±0.7°.** |
| D9 | all 28 map records, Y[1..9] (392 B) | 24,42,50,62,100,126,154,166,172 → 52,86,103,138,275,413,550,688,1032 | the assist map — in stock the RATE setpoint; **bypassed for the error by E4** | V102 lineage | **INERT for the loop → revert** | E: `0x29D6A` now loads `gp-0x69ae` directly; the map LERP output (`iVar28`) no longer reaches E. **CORRECTED 2026-10-15 (two lenses, E): `gp-0x682f` = min(\|gp-0x4f60\|>>5, 255) is the DRIVER BAR TORQUE, `gp-0x6830` its lag, `gp-0x6a34` the filtered rate feedback — none is map-derived; the decompiler re-used `iVar28`. The map output is dead end to end in the angle images (read at two sites, one in the uncalled twin). The 17 sites are byte-identical to stock in V300 and change nothing when the map reverts. The only map-adjacent coupling, the idx bypass at `0x29A7C` vs `0xC64B8` = 255, cannot fire at either scale.** |
| D10 | LIM records Y (72 B; slots 0,1,3,4,6,7,8,9) | 15360 → 16384 | the setpoint-ceiling LERP applied at `0x2903A` to `r22 = clamp(cmd, ±LIM)` → feeds the map index only | V38 | **INERT for the loop → revert** | E: `gp-0x69ae` itself is written at `0x526F2` as `clamp(−4·raw, ±0x4000)` (hard-coded; trace 2026-09-30 §table rows 4–7) and E4 reads it directly, so LIM never touches the angle setpoint. (The ±16384 the angle loop sees = ±409.6° is the RX writer's constant, not this cal.) |
| D11 | `0x14120` | `-` → `,` | the second, dead copy of the id string (`0x14117`); no caller found for its copy routine | V22 | **bookkeeping → revert** | B (trace 2026-10-05: cosmetic). |

### E — CRC trailers (73 B at offset `0xFFC` of 19 touched pages: `0xC4`, `0xC6`, `0xCE`–`0xD9`, `0xE4`–`0xE8`) — recomputed by any builder.

---

## 2. The proposed RELEASE delta (vs STOCK)

**Build it FROM STOCK, not from V299 with reverts**, so the lineage reads "stock + the angle loop" and the
assertion set is small and non-vacuous. Then assert `release XOR V299 == exactly {C1,C2,C3,D1,D2,D3,D5,D7,D8,D9,D10,D11,B3x→112,B4x→48, trailers}`.

| keep | rows | bytes (≈) | why |
|---|---|---|---|
| structure | A1–A7 | 322 | the loop, its guards, the camera interlock, the fade neutralisation, the ×6 authority chain + EME ladder |
| tuning | B1, B2, B3+B3x (112 ×28), B4+B4x (48 ×28) | 14 + 280 + 112 | final values from task 1b; **all 28 records on the same surface** |
| legacy kept | D4 lockout 0, D6 debounce/DTC package | 13 | the goal (every speed) and the authority interlock |
| **removed** | C1–C3; D1, D2, D3, D5 (knee, K1), D7, D8 (minus the 12 DampAxis Y bytes), D9, D10, D11 | 199 + 1,460 | telemetry; inert/unneeded legacy; base assist back to Honda |
| **kept, rev 2** | D5 α2 `0xC40DC` = 14; D8 Y rows `0xD7A5C..61`, `0xD7A6C..71` | 13 | the DampAxis lane — GATE 2 fails without it (corrections 3–4) |

Expected release footprint (first estimate): ≈ 740 bytes in 5 CRC pages. **AS BUILT (V300 rev 2, E): 766 B vs stock in 8 CRC blocks** (main `[0x13000,0xC4FFC)`, `0xC6`, `0xD7`, `0xE4`–`0xE8`; the Kp/Kd records span five pages and the 13 kept DampAxis bytes keep page `0xD7`), **2110 B vs V299**; pages `0xCE`–`0xD9` are stock except those 12 bytes and the `0xD7` trailer.

**Behavioural consequences of the reverts, read for the operator**
1. **Hands-on feel (manual driving) returns to Honda's** — D8 damper banks, D5 Coulomb relay, D7, D2 notch. He has driven on D8 since V268 (≈ 2026-09-01) and on D5 since V112; expect a perceptible change in base-assist damping at wheel rates > 85 deg/s and small-signal friction feel. **B** for magnitude.
2. **Loop authority unchanged**: the rail stays 2461 (A6), the EME ladder stays (A7), Kp/Ki/Kd/G(v)/A3 untouched.
3. **r24 while engaged** goes from flat 2048 to Honda's speed LERP (D3) — **GATE 2 re-scored: clean** (ΔPM −0.7…+0.1°, GM ≥ 20 dB); the stutter readouts on the first release drive are the on-car check (predicted unchanged; watch F7).
4. ~~Map side channels return to Honda's scale~~ **Corrected: `gp-0x682f/0x6830/0x6a34` are bar-torque / rate-feedback cells, never map-scaled; the map revert changes nothing on the engage/arb path** (the `0xC64B8` = 255 compare at `0x29A7C` never fires at either scale — E).
5. **Nothing on the wire identifies the build any more** except F181 (and the cave's effect on 0x18F) — the release attribution rule is the firmware id, which the fork already enforces.

**Decision items for the orchestrator/operator:** D4 (keep the creep lockout off — recommended), D8 (revert now with a harness re-score vs ship as a second step), the release F181 letter, and whether B3x/B4x are written 112/48 (recommended) or stock.

## 3. What the adversarial lenses must adjudicate (pre-registered)
- D9 side channels: enumerate the 17 `gp-0x682f`/`gp-0x6830` accessor sites (list above) and state which thresholds they feed; confirm Honda's scale is fail-safe.
- D6: the 12 readers of `0xC61C0..C4` (owed since 2026-09-09) and `0xC64B8`'s second role under the stock map.
- D3+D8: GATE 2 with Honda's r24 LERP and banks (magnitude AND phase, 0.3–30 Hz), plus the stutter readouts' predicted direction.
- D7: name the function of the `gp-0x6b2c` square wave from its 8 readers before the revert is accepted (the safe direction is still stock).
- C: confirm the stock bytes restored at `0x55C0E`/`0x55DF2..0x55E11` equal the stock dump byte-for-byte and that `gp-0x1518` has no other writer the cave's absence exposes.
