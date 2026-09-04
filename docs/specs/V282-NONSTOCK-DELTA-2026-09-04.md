# V282 — CUMULATIVE NON-STOCK DELTA, READ FROM THE BUILT IMAGE

**Date** 2026-09-04 · **Author** subagent `delta282` for orchestrator `main`
**Method** raw Python little-endian byte diff + a 280-image cross-build ledger. **No Ghidra database was
mutated.** Every number below is read from an image file, never from a build script constant.

| | |
|---|---|
| stock | `stock_fw_dump/code.bin`, sha256 `3f1d55a98aac6e73…` |
| V282 | `_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`, sha256 `0ea98d06b292ca1a…` |
| extent | `[0x13000, 0x100000)` |
| delta | **578 runs / 1,984 bytes / 68 regions** |

Scripts (analysis only, in `_scratch/out/`, regenerable): `delta282.py` (run/category split),
`ledger282.py` (cross-build cell ledger over all 280 numbered `*_plain_image.bin`), `hist282.py`
(per-cell change-point history), `reg2.py`/`reg3.py`/`reg4.py`/`ptr.py` (region and pointer-family
decomposition).

---

## 0. Two label corrections to the brief (EVIDENCE)

**(a) The ASSIST MAP is NOT `0xCE000`–`0xD9FFF`. It is the 28-record family behind pointer table
`0xC9A88`, records at `0xE4000`–`0xE8105`, stride `0x2C`.**
Method: `0xC9A88` is a clean 28-entry dword pointer table whose targets are `0xE4000, 0xE402C,
0xE4058, …` (stride 44). The V282 Y-array of record 0 (`0xE4018`) reads
`[52, 86, 103, 138, 275, 413, 550, 688, 1032]` against X `[12, 20, 24, 32, 64, 96, 128, 160, 240]` —
**Y/X = 4.30 at every knot, i.e. exactly straight** — and `1032 = 6 × 172`, where 172 is the stock top.
Stock is a saturating curve (Y/X falls 1.33 → 0.72). `build_v280_tva.py` independently names
`MAP_PTR, MAP_N, N_SLOTS = 0xC9A88, 10, 28` and `[A] ASSIST MAP -- 28 records via 0xC9A88`.

**(b) `0xCE000`–`0xD9FFF` (992 B) is V268's pair of flattens, not the assist map, and it entered at
V268 — not at V280 rev 2.** The 992 bytes are **byte-identical in V268, V273, V280 rev 2, V281 rev 3
and V282** (payload sha256[:8] `8287b9ec` in all five; V267 = `bbe887fb`). Its records resolve to the
mode-indexed rate-lane pointer arrays `0xCBF5C / 0xCC044 / 0xCC12C / 0xCC214` (≈484 B) and the
AMP1/AMP4 boost tables `0xCA4F4 / 0xCA23C` (≈496 B); ~12 B sit on a record boundary my ownership
heuristic cannot split (BELIEF on the 484/496 split; EVIDENCE that the whole 992 B is V268's and has
not moved since).

---

## 1. THE DELTA TABLE

`status` key: **MEASURED** = a drive scored it · **INERT/UNVERIFIED** · **CARRIED** = present and
deliberate at its introducing build, but not re-chosen on this branch · **BOOKKEEPING**.
`frozen N` = number of consecutive numbered build images (≤ V282, build-number order) carrying V282's
value, counting back from V282.

### 1a. Code-region in-place edits (8 bytes)

| address | stock | V282 | what it physically is | what it does to the car | introduced | status | frozen N |
|---|---|---|---|---|---|---|---|
| `0x2A1F0` | disp `0x746C` | disp **`0x7CD0`** | displacement of the forward-LKAS-path gain load | repoints the forward path off the **shared** sensor-scale cal `0xC646C` onto the **private** cell `0xC6CD0`, so the LKAS gain can move without moving the 4× sensor scale | **V57**, lost in the V38 rebase, restored **V81** | CARRIED (structural — it is what makes `0xC6CD0` reachable) | 197 |
| `0x35A08` | `e798` | **`fb97`** | `ld.bu` source of the biquad ARM flag: `gp-0x671a` → **`gp-0x6806`** (LKAS lateral-engaged) | arms Honda's dormant notch **engaged-only** | **V103** | MEASURED (V103/V104 arc) | 176 |
| `0x35A12` | `ec` (`cmp r12,r9`) | **`e0`** (`cmp r0,r9`) | the arm comparison | arm test becomes `flag != 0` instead of `flag ≥ 5` — the ≥5 condition was **never observed true** across 255,292 engaged frames | **V103** | MEASURED | 176 |
| `0x35A18` | `e9` | **`ea`** | branch condition of the arm rung | completes the engaged-only arm | **V103** | MEASURED | 176 |
| `0x3AA96` | `c5` | **`fb`** | the rate-lane (r24/r26) gate byte: `gp-0x683c` (dead) → **`gp-0x6806`** (`STEER_CONTROL_ACTIVE`) | makes **Lever B live** — r24 runs the engaged gain `0xC6446` on the 4-tap derivative of bar torque when LKAS is engaged. This byte is why the r24 lane is reachable at all | **V67**, current run from **V104** | MEASURED — operator on V88: *"the audible grinding is fixed"* | 175 |
| `0x454FE` | `ba` | **`b5`** | one substitution byte in the `gp-0x67fa` selector path | V42's ratchet-fix substitution | **V42**, current run from **V80** | **INERT — measured inert** (the `gp-0x67fa` reachable set is `{11}` alone) | 198 |

### 1b. The telemetry cave (168 bytes) — read-only, no actuation

| address | stock | V282 | what it physically is | what it does to the car | introduced | status |
|---|---|---|---|---|---|---|
| `0x55C0E` | 4 B | `jarl 0xC4B34,lp` | the hook that calls the cave from the 100 Hz frame builder | diverts 4 bytes of the frame-build path into the cave and back | **V31p**, current bytes from **V53** | CARRIED (instrument) |
| `0xC4B34` | 164 B `0xFF` filler | 164 B cave code | `CAVE_V280` — five "abs-compare → bit → mask → OR → store" rungs writing an 8-byte buffer at `gp-0x1518`, published as **CAN `0x14A`, 100 Hz** | **publishes bits only; it writes no control cell.** The car's behaviour is unchanged by it | body from **V31p**; sha `d3bb75d8` ran **V105 → V281 rev 3 unchanged (177 images)**; **V282 is the first change in 177 builds** | INERT by design |
| `0x55DF2` + `0x55E0F` | 31 B | repointed | the CAN-427 `MOTOR_TORQUE` source window + its `sar` shift | publishes the **delivered LKAS-lane torque `gp-0x6b38`** on 427 | current bytes from **V280** | INERT by design (instrument) |

**V282's own edit — the only thing separating V282 from V281 rev 3.** Full-image diff V281 rev 3 →
V282 is **five runs: four displacement halfwords inside the cave, plus one page-CRC trailer.** I
re-derived all four from the images (hw1 identical at every site; all new displacements even, so the
loads are still `ld.h` and were not silently widened to `ld.w`):

| site | hw1 (before → after) | disp before | disp after | rung |
|---|---|---|---|---|
| `0xC4B36` | `24 37` → `24 37` | `gp-0x6B94` (aggregator) | **`gp-0x6ADA`** (r24) | bit 6 operand A |
| `0xC4B42` | `24 37` → `24 37` | `gp-0x4F64` (unrelated cal) | **`gp-0x6B38`** (T, delivered torque) | bit 6 operand B |
| `0xC4B64` | `24 37` → `24 37` | `gp-0x6AE2` (unrelated) | **`gp-0x6ADA`** (r24) | bit 5 operand A |
| `0xC4B70` | `24 37` → `24 37` | `gp-0x6B26` (inertia) | **`gp-0x6B94`** (aggregator) | bit 5 operand B |

⇒ `0x14A` byte 4 **bit 6 = (|r24| ≥ |T|)** and **bit 5 = (|r24| ≥ |aggregator|)**. Bits 7 / 4 / 3
untouched. **Nothing the car actuates on moved.**

### 1c. In-place calibration cells (47 bytes)

| address | stock | V282 | what it physically is | what it does to the car | introduced | status | frozen N |
|---|---|---|---|---|---|---|---|
| `0xC6CD0` | `0xFFFF` (blank) | **5346** | the **private** forward LKAS gain (reachable only because of `0x2A1F0`) | **the 6× forward gain** — the single largest authority multiplier on the LKAS path | **V57**; 5346 chosen at **V102** (the first *downward* gain step, 8× → 6×); unbroken from **V260** | MEASURED (dose-response across V101/V102/V112…) | 25 |
| `0xC61B2` | 512 | **3072** | forward-path positive tracking clamp | tracks the 6× gain exactly (`5346 × 512 // 891 = 3072`) so the clamp does not bind before the gain does | **V102**; unbroken from **V260** | MEASURED | 25 |
| `0xC61B4` | 512 | **3072** | forward-path negative tracking clamp | as above, other sign | **V102**; unbroken from **V260** | MEASURED | 25 |
| `0xC62E6` | 7680 | **46080** | LKAS PID **feedback saturation clamp** (stored ×256) | lets the PID see 6× more feedback before saturating; the 1.395 ceiling ratio is preserved structurally | **V276** (15360); **46080 at V280** | MEASURED (V280/V281 arc) | 5 |
| `0xC6446` | 512 | **5244** | the **r24 engaged rate-lane gain arm** (Lever B) | ×10 stock on the bar-torque derivative when engaged. **Pulls two symptoms opposite ways**: it pumps the 7 Hz strong-turn ripple and supplies ~83 % of the 20 Hz grind's damping | **V67**; 5244 is V88's bracketed optimum, unbroken from **V247** | MEASURED (in both directions) | 38 |
| `0xC649B` | 0 | **1** | biquad enable cal | with `0x35A08/12/18`, arms Honda's notch engaged-only. **Alone it would be inert** | **V103**; unbroken from **V120** | MEASURED (with the arm repoint) | 159 |
| `0xC62EA` | 320 | **0** | low-speed steer lockout threshold | disables the low-speed LKAS lockout — LKAS keeps authority at creep | **V53**, restored **V81** | CARRIED | 197 |
| `0xC674E` | 1024 | **5120** | EME soft-limit quad, +A (int16) | **the ×5 authority ladder.** Raises the Excessive-Motor-Effort interlock ceiling so the 6× gain path is not cut by the shaper. `0xC674E` must stay **above** the tracking clamp (3072) or a build aborts | V25 → V30 → **V38 (5120)** | CARRIED — structural interlock | 247 |
| `0xC6750` | 1024 | **5120** | same quad, +B | as above | **V38** | CARRIED | 247 |
| `0xC675A` | −1024 | **−5120** | same quad, −A | as above | **V38** | CARRIED | 247 |
| `0xC675C` | −1024 | **−5120** | same quad, −B | as above | **V38** | CARRIED | 247 |
| `0xC6768` | 0 | **5120** | EME ramp triple, knot 0 | as above | V31 → **V38** | CARRIED | 247 |
| `0xC676A` | 1536 | **5120** | EME ramp triple, knot 1 | as above | V31 → **V38** | CARRIED | 247 |
| `0xC676C` | 2048 | **5120** | EME ramp triple, knot 2 | as above | V31 → **V38** | CARRIED | 247 |
| `0xC6598` | 1.0f | **5.0f** | **float mirror** of `0xC674E` | the shaper compares int against float at ±5 LSB (`int == float × 1024`; `0x4317A mulf.s`, r17 = 1024.0f). **If the float and int quads disagree, the lockstep monitor trips** | V29 → V30 → **V38**; V178 tried reverting to Honda 1.0 and was marked SUPERSEDED-DO-NOT-FLASH-AUTHORITY; **5.0 unbroken from V179** | CARRIED — structural; do **not** revert alone | 106 |
| `0xC659C` | 1.0f | **5.0f** | float mirror of `0xC6750` | as above | **V38 / V179** | CARRIED | 106 |
| `0xC65AC` | −1.0f | **−5.0f** | float mirror of `0xC675A` | as above | **V38 / V179** | CARRIED | 106 |
| `0xC65B0` | −1.0f | **−5.0f** | float mirror of `0xC675C` | as above | **V38 / V179** | CARRIED | 106 |
| `0xC65C4` | 0.0f | **5.0f** | float mirror of `0xC6768` | as above | V31 → **V38 / V179** | CARRIED | 106 |
| `0xC65C8` | 1.5f | **5.0f** | float mirror of `0xC676A` | as above | V31 → **V38 / V179** | CARRIED | 106 |
| `0xC65CC` | 2.0f | **5.0f** | float mirror of `0xC676C` | as above | V31 → **V38 / V179** | CARRIED | 106 |
| `0xC40BC` | 600 | **1800** | Coulomb-relay **knee** | the relay saturates later; small-signal gain is held at V112's `0.0039844` by the paired `0xC40D2` | **V112**; on this branch only because **V255 rebased onto V112** (V254 carried 3000) | ⚠ CARRIED BY REBASE | 30 |
| `0xC40D2` | 102 | **612** | relay gain K1 | pairs with the knee to hold small-signal gain | **V112**; via the V255 rebase (V254 carried 1020) | ⚠ CARRIED BY REBASE — **measured NULL at both bands** (V88 r73 vs V89 r75+r76) | 30 |
| `0xC40DC` | 22 | **14** | α2, the second HF filter coefficient | V109's HF lever | **V109**; via the V255 rebase (V254 carried 22 = stock) | ⚠ CARRIED BY REBASE | 30 |
| `0xC61C0` | 1600 | **`0xFFFF`** | `STEER_STATUS` debounce SM cal | blanked to max | **V36** | 🛑 **UNEXPLAINED — see §3** | 249 |
| `0xC61C2` | 896 | **`0xFFFF`** | `STEER_STATUS` debounce SM cal | blanked to max | **V36** | 🛑 **UNEXPLAINED — see §3** | 249 |
| `0xC61C4` | 1280 | **`0xFFFF`** | `STEER_STATUS` debounce SM cal | blanked to max | **V36** | 🛑 **UNEXPLAINED — see §3** | 249 |
| `0xC64B4` | 24688 | **`0xFFFF`** | `STEER_STATUS` debounce SM cal | blanked to max — disables the gentle-EME debounce | **V36** | CARRIED — V36 fixed gentle EME but unmasked DTC 0x49 | 249 |
| `0xC64B6` | 16438 | **`0xFFFF`** | `STEER_STATUS` debounce SM cal | as above | **V36** | CARRIED | 249 |
| `0xC64B8` | 112 | **255** | DTC-0x49 fail-counter gate | **V37's fix** for the dash light V36 unmasked | **V37** | MEASURED — gentle EME resolved, no dash-light regression | 248 |
| `0xC64DE` | 17 | **27** | 🛑 **NOT** a "re-engage authority ramp" — it is the **hold count (half-period) of a sign-flipping square wave**: `if c < cal: c++ else { c = 1 + (cal >> 1); gp-0x6b2c = −gp-0x6b2c }`, with 8 live read sites | lengthens that square wave's period, 17 → 27 ticks | **V18** | CARRIED — road-validated *"drives well"*, but validated **under a label that was wrong**; never re-examined since the 2026-08-27 correction | 266 |

### 1d. Table families (1,654 bytes)

| family | pointer table | records | stock | V282 | what it does | introduced | status | frozen N |
|---|---|---|---|---|---|---|---|---|
| **Rate-lane gain surface + AMP1/AMP4 boost**, `0xCE000`–`0xD9FFF`, 992 B | `0xCBF5C`, `0xCC044`, `0xCC12C`, `0xCC214` (rate, ≈484 B) · `0xCA4F4`, `0xCA23C` (boost, ≈496 B) | all 34 mode slots / 136 + 68 distinct records | Honda curves | rate-lane Y flattened to Y[0] (**only ever raises** Y); boost flattened per record to V59's index-weighted mean (**mean boost preserved, modulation removed**) | the parametric-pump test with **no table-selection escape hatch** — every mode covered | **V268** | MEASURED — *"V268's damper flatten is inert below 85 deg/s"* | 14 |
| **Assist map / LKAS rate-loop REFERENCE**, `0xE4000`–`0xE8105`, 392 B | **`0xC9A88`** | 28 records, stride `0x2C`, 10 knots | saturating Honda curve, slot-7 top 172 | **straight line to the ×6 top**: Y = round(6 × Ytop × X / 240); slot-7 top **172 → 1032**, slope exactly 4.30 at every knot | the reference the rate loop tracks — a linear, 6× steeper demand→rate map | **V280 rev 2** | MEASURED (r35, V281 rev 3 drive) | 3 |
| **Kp LERP records**, `0xE4360`+, 198 B | **`0xCB994`** | 28 records, 24 B, n = 5 | slot 7 Y `[248, 512, 645, 696, 696]` | **flat at Y[0]**: slot 7 `[248, 248, 248, 248, 248]` (other families 205 / 266 / 307) | removes the rising Kp-vs-index schedule — constant proportional gain in the rate PID. X axes untouched | **V281 rev 3** | MEASURED — r35: the self-sustained 7 Hz cycle is **gone** (F7 0.0 / 100 s) | 1 |
| **Setpoint-ceiling curves**, `0xE4194`, `0xE41BC`, …, 72 B | `0xCB844` | 8 records × 9 knots, all flat | **15360** | **16384** | +6.7 % on the mode/gear setpoint ceiling limiting `gp-0x69ae`. Memory record: *"an AUTHORITY raise, DO NOT revert"* | **V38** | CARRIED — structural | 247 |
| Kd LERP records `0xE4108`+ (`0xCB7D4`) | — | 28 records, 20 B, n = 4 | 128 flat | **128 — STOCK** | *not changed*; listed because the brief expected a Kd delta | — | — | — |

### 1e. Bookkeeping (76 bytes)

| what | bytes | note |
|---|---|---|
| page-CRC trailers (offset ≥ `0xFFC` in each 4 KB page) | **74** | 21 runs; recomputed by the builder, not a lever |
| version-string bytes `0x13109`, `0x14120` (`-` → `,`) | **2** | marks the image non-stock in the UDS version read; **V22**, in every build since (266 images) |

---

## 2. Q1 — the byte split

| category | bytes | % |
|---|---:|---:|
| **Calibration levers (tables + in-place cells)** | **1,709** | **86.2 %** |
| ├ V268 rate-lane + boost flatten (`0xCE000`–`0xD9FFF`) | 992 | 50.0 % |
| ├ V280 rev 2 assist-map linearization (`0xC9A88`) | 392 | 19.8 % |
| ├ V281 rev 3 Kp flatten (`0xCB994`) | 198 | 10.0 % |
| ├ V38 setpoint-ceiling raise (`0xCB844`) | 72 | 3.6 % |
| └ in-place cal cells (26 cells) | 47 | 2.4 % |
| **Cave's own code + hook** | **168** | 8.5 % |
| **CRC bookkeeping** | **74** | 3.7 % |
| **427 telemetry source window** | **31** | 1.6 % |
| **Code-region in-place edits** (6 sites) | **8** | 0.4 % |
| **Version string** | **2** | 0.1 % |
| **TOTAL** | **1,984** | 100 % |

**Read another way:** of 1,984 bytes, **199 (10.0 %) are instrumentation that cannot change the car**
(cave 164 + hook 4 + 427 window 31), **74 (3.7 %) are CRC**, **2 are a version string**, and
**1,709 (86.2 %) are calibration or control levers.** Of those levers, **92 % of the bytes are four
table edits**, not scalar cells.

---

## 3. Q2 — is anything present that nobody deliberately chose?

All 68 regions were cross-checked against the lineage. **One region is genuinely unaccounted for;
three more ride on a rebase rather than on a decision.**

### 🛑 UNACCOUNTED — `0xC61C0` / `0xC61C2` / `0xC61C4` (6 bytes)
`1600 / 896 / 1280` → **`0xFFFF / 0xFFFF / 0xFFFF`**, a deliberate 6-byte run that appears in the
**V35 → V36** diff and is present in **every one of the 249 images since**. The lineage says so in its
own words: *"Related and **not covered anywhere in this file**… **12 readers between them, 0 writers**…
**Unrecorded and unexplained.**"* No build entry states the intent. They are grouped with the
`STEER_STATUS` debounce cals in a single summary row, but that row does not explain blanking three
cells to `0xFFFF`. **12 readers, 0 writers — this is a live cal set, not dead space.**
⇒ **Recommend a tracer task on the 12 readers before the next authority change.** (EVIDENCE for the
byte values and the 249-image persistence; EVIDENCE for "unrecorded" = the lineage's own text.)

### ⚠ CARRIED BY REBASE, never re-chosen — `0xC40BC` 1800 · `0xC40D2` 612 · `0xC40DC` 14 (5 bytes)
These are **V112's** relay knee/K1 and **V109's** α2. V254 carried `3000 / 1020 / 22`; **V255 rebased
onto V112**, and every build V255 → V282 has carried the V112 values unchanged. The rebase itself was
deliberate (the filename says `V255-V112BASE-…`), but **no build since has chosen these three values
on their merits**, and `0xC40D2` is on record as **measured NULL at both bands**. Their change-point
history is a 20-step sawtooth (600 → 6000 → 600 → 300 → 600 → 1800 → … → 3000 → 1800), which is the
signature of values that ride bases rather than being reasoned about.

### ⚠ VALIDATED UNDER A WRONG LABEL — `0xC64DE` 17 → 27 (1 byte)
Present in **all 266 numbered images**; road-validated at V18 as a *"re-engage authority ramp"*. The
2026-08-27 correction established it is **the hold count of a sign-flipping square wave** on
`gp-0x6b2c`, with 8 live read sites. Nobody has re-assessed the +59 % period change under the correct
label. Not an accident — but the *reason* it is there no longer exists.

### ⚠ MEASURED INERT but still shipping — `0x454FE` `ba` → `b5` (1 byte)
198 images. The lineage records it as **measured inert** (the `gp-0x67fa` reachable set is `{11}`
alone), with the note *"Keep the byte — it has been silently…"*. Harmless, but it is one byte of code
edit whose only justification is inertia.

### Everything else is accounted for
`0x13109` / `0x14120` (V22) · `0x2A1F0` + `0xC62EA` (V53/V57, restored V81) · `0x35A08/12/18` +
`0xC649B` (V103) · `0x3AA96` + `0xC6446` (V67/V104/V247) · `0x55C0E` / `0xC4B34` / `0x55DF2` (the
instrument) · `0xC61B2/B4` + `0xC6CD0` (V102) · `0xC62E6` (V280) · `0xC64B4/B6` (V36) · `0xC64B8`
(V37) · `0xC6598…CC` + `0xC674E…6C` + the `0xCB844` ceiling family (the V38 authority ladder) ·
`0xCE000`–`0xD9FFF` (V268) · `0xC9A88` map (V280 rev 2) · `0xCB994` Kp (V281 rev 3) · CRC trailers.

**No orphan region survived the cross-check other than `0xC61C0/C2/C4`.**

---

## 4. Q3 — what has been FROZEN, and for how many builds

Statistic: N = consecutive numbered build images (≤ V282, in build-number order; 280 images on disk)
whose value equals V282's, counting back from V282. Produced by `_scratch/out/ledger282.py`.

| cell / family | value | frozen N | last build that differed |
|---|---|---:|---|
| `0xC64DE` square-wave hold count | 27 | **266** | never (V22 is the oldest image) |
| version-string bytes | `,` | **266** | never |
| `0xC674E` / `0xC6750` / `0xC675A` / `0xC675C` EME quad | ±5120 | **247** | V37 = ±4096 |
| `0xC6768` / `0xC676A` / `0xC676C` EME ramp | 5120 | **247** | V37 = 4096 |
| `0xCB844` setpoint-ceiling curves | 16384 | **247** | V37 = 15360 |
| `0xC64B8` DTC-0x49 gate | 255 | **248** | V36 = 112 |
| `0xC61C0/C2/C4`, `0xC64B4/B6` | `0xFFFF` | **249** | V35 = Honda values |
| `0x55C0E` hook | V53 bytes | **228** | V52c = stock |
| `0x454FE` | `b5` | **198** | V79 = `ba` |
| `0x2A1F0` disp · `0xC62EA` | `0x7CD0` · 0 | **197** | V80 = stock |
| `0x35A08/12/18` biquad arm | V103 bytes | **176** | V102 = stock |
| `0x3AA96` rate-lane gate | `fb` | **175** | V103 = `c5` |
| `0xC649B` biquad enable | 1 | **159** | V119 = 0 |
| `0xC6598…0xC65CC` float quad | ±5.0f | **106** | V178 = Honda ±1.0f |
| `0xC6446` Lever B | 5244 | **38** | V246 = 7866 |
| `0xC40BC` / `0xC40D2` / `0xC40DC` | 1800 / 612 / 14 | **30** | V254 = 3000 / 1020 / 22 |
| `0xC61B2` / `0xC61B4` / `0xC6CD0` | 3072 / 3072 / 5346 | **25** | V259 = 4096 / 4096 / 3564 |
| `0xCE000`–`0xD9FFF` V268 flattens | — | **14** | V272 (toggled V268 ↔ stock through V273) |
| `0x55DF2` 427 tap · `0xC62E6` clamp | V280 bytes · 46080 | **5** | V279 rev 1 |
| `0xC9A88` assist map | linear ×6 | **3** | V280 rev 1 |
| `0xCB994` Kp records | flat Y[0] | **1** | V281 rev 2 |
| **`0xC4B34` cave body** | V282 rungs | **1** | **V281 rev 3 — the cave sha `d3bb75d8` had been unchanged for 177 consecutive images, V105 → V281 rev 3** |

**The headline freeze:** *the instrument itself was the most frozen thing in the kit.* The cave that
every build's telemetry comes from **did not change for 177 builds** (V105 → V281 rev 3). V282 is the
first build in that span to re-point it — which is the "every build must carry the instrument for its
own edit" rule finally being applied to the instrument.

**The V38 authority ladder is the second freeze:** seven int cells, seven float mirrors and eight
ceiling curves — **~150 bytes untouched for 247 builds**, every one of them *structural*: the EME
interlock, the lockstep int/float mirror, the setpoint ceiling. Nothing in the post-V38 arc has moved
them (V178 tried; it was marked DO-NOT-FLASH-AUTHORITY).

### Ledger tooling
`analysis-2020accord/studies/ledger/ledger_v38_to_v84_bytes.py` **still runs** after the 2026-08-26
reorg (its anchors pass: `stock 0xC646C=891, 0x454FE=0xBA, len=0x100000`), but it covers only V38→V84
and hard-codes that image set. I did **not** modify it. The extension to V282 is a separate,
analysis-only reader at `_scratch/out/ledger282.py`, which walks **all 280 numbered
`*_plain_image.bin`** files and emits per-cell change-point histories (`hist282.py`).

---

## 5. Method notes and limits

- **EVIDENCE** — every stock/V282 value, every run boundary, every frozen-N count, the four cave
  displacements (hw1 and parity re-derived from the image bytes), the assist-map linearity check, and
  the region↔pointer-family mapping. All from raw Python little-endian reads on the image files.
- **BELIEF** — (i) the ≈484 / ≈496 split of V268's 992 bytes between the rate-lane and boost families
  (12 bytes sit on a record boundary the nearest-record heuristic cannot assign); (ii) physical
  identities quoted from the lineage and golden model that I did not re-derive from the decompile
  (`0xC61C0/C2/C4` as `STEER_STATUS` debounce cals, `0xC64DE`'s square wave, `0xC40BC/D2` as relay
  knee / K1).
- **Frozen N is a filename-ordered statistic, not an ancestry walk.** Builds rebase (V255 → V112 base;
  V280 rev 2 → V268 base), so a cell can show a broken run because a side branch differed, not because
  the mainline changed. Where that matters, both the introducing build and the unbroken run are given.
- No Ghidra program was opened or saved. No build script, image or `.rwd` was modified.
