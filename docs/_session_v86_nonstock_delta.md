# What is non-stock about the ECU — cumulative STOCK → V85 delta

**Read from the BUILT IMAGE, not from the build scripts.** Every number below was recovered by a raw
little-endian byte read of the image files; every table address was **dereferenced from its pointer
array inside the image**, never quoted from a script. Generated 2026-08-08 by the image-audit pass.

| | |
|---|---|
| STOCK baseline | `accord-firmwares/analysis-2020accord/stock_fw_dump/code.bin` · 1,048,576 B · sha256 `3f1d55a98aac6e73631d94d583065c57d83dd3a86df0e7d06e56a3feb58fd822` |
| **V85 candidate** | `_v85_FRICTION.C40BC.6000-PROBE.RATE.6ABC-FRIC.6AE2_plain_image.bin` · 1,048,576 B · sha256 **`cc9cdd662ab92049e266d3fef862763bee24dc21e8efa1fe8314ec983ed06e8f`** ✅ matches the recorded value |
| V85's base | the flown V84, sha256 `344f22f7303f6b5b006b13d329192ce098d118c9ce149834cb3cc05899dc637a` ✅ matches |
| V84 → V85 | **63 differing bytes**: 2 control (`0xC40BC`) + 57 inside the 64-byte cave span + 4 CRC |
| STOCK → V85 | **364 differing bytes in 87 runs, ZERO unattributed** |
| CRC | bootloader walk **49/49 PASS** · full linked chain **50/50 PASS** · **0 bytes** written into `[0xC5000,0xC5FFC)`, the block the bootloader skips |

🛑 The diff is restricted to **`[0x13000, 0x100000)`**. `build_*.full_image()` writes `0xFF` filler
below `0x13000` — confirmed all-`0xFF` in V85 — so a naive whole-file diff reports ~50,284 bogus bytes.

---

## 1. The one-paragraph answer

Of the 364 non-stock bytes, **121 cannot execute on this car**: they are Honda calibration records for
**other vehicle variants' mode slots**, left behind by V72–V75 and never reverted. This car is `TVCA4`,
which uses **modes 24 / 25 / 26 / 27**, and every one of those records is **byte-identical to Honda** in
all six factor families and all four `gain_B` arrays.

What actually reaches the steering is **15 calibration cells and 5 code edits**. Of those, **exactly one
is new in V85** (`0xC40BC`, 600 → 6000). Everything else has already been on the car.

```
364 bytes
├── 121  other cars' mode records .............. INERT, carried by accident (V72–V75 residue)
├──  52  CRC trailer words (13 blocks) ......... bookkeeping, chain verifies 50/50
├──  68  probe cave payload @0xC4B34 ........... telemetry only, no control path
├──  10  code edits (5 sites) .................. 2 cosmetic + 3 functional
└── 113  calibration cells (15 cells) .......... the actual non-stock steering behaviour
```

---

## 2. THE LIVE NON-STOCK SURFACE — every cell that can execute on this car

| addr | stock | V85 | what the variable physically is | what the change does to the car | introduced | status |
|---|---|---|---|---|---|---|
| `0x13109`, `0x14120` | `2d` (`-`) | `2c` (`,`) | ASCII version string, `39990-TVA-A160` → `39990-TVA,A160` | Nothing. **Cosmetic.** 🛑 Every modified build shares it, so an rlog **cannot** tell you which build is flashed | **V22** | inert |
| `0x2A1F0-1` | `6c 74` = disp `0x746C` | `d0 7c` = disp `0x7CD0` | The `tp`-relative displacement in the **forward** LKAS-gain load. `tp = 0xBF000` ⇒ `0x746C` → `0xC646C` (shared sensor scale, 6 readers/3 subsystems), `0x7CD0` → `0xC6CD0` (a private cell) | **Decouples the forward LKAS reader from the 4 feedback readers.** Alone it does nothing; it is the other half of `0xC6CD0` | **V57** | on-car (V57–V77, V81–V85) |
| `0xC6CD0` | `ff ff` (unused, 65535) | `ec 0d` = **3564** | The private forward-LKAS gain cell that `0x2A1F0` now points at | **4× LKAS authority** on the forward path only, with the feedback path left at Honda's 891. This is the "4× LKAS" the kit has been flying since V57 | **V57** | on-car; **frozen 46+ builds** |
| `0x3AA96` | `c5` | `fb` | One condition/branch byte gating the **r24 rate-lane engaged arm** | **Lever B**: repoints the r24 arm gate so `0xC6446` is actually reachable when LKAS is engaged | **V67** | on-car (V67, V68, V76, V84) |
| `0xC6446` | `00 02` = 512 | `7c 14` = **5244** | The r24 rate-lane **engaged arm** value | With `0x3AA96`, raises the engaged r24 rate-derivative arm ~10×. Kit's best measured grind-#1 result (0.40 [0.27, 0.58]) on V67/V68 — but V84 re-delivered it and the operator still reported grinding | **V67** | **on-car, measured** |
| `0xC6444` | 512 | **512** | The r26 engaged arm | **STOCK — deliberately left alone** as the S3 lever | — | stock |
| `0x454FE` | `ba` (`bne`) | `b5` (`br`) | The **state-4 governor substitution** branch | V42's macro-ratchet fix: forces the branch so the state-4 governor cannot forbid a command-magnitude increase | **V42** | ⚠ **on-car but MEASURED INERT** — `gp-0x67fa == 4` fires **0 / 123,277** driving frames, so the byte cannot execute on recent routes |
| `0x55C0E-11` | `24 36 e8 ea` | `86 ff 26 ef` | The CAN `0x330` TX build hook | Redirects 4 bytes of the `0x330` transmit path into the probe cave. **Telemetry only** | **V49P / V53** | inert (measurement) |
| `0xC4B34-77` | `FF` ×68 | 68-byte cave | The probe cave payload — V85's four `0x14A` byte-4 rungs on `gp-0x6abc` and `gp-0x6ae2` | Publishes 4 bits of internal state onto a spare CAN field. **No control path.** Re-cut every build | **V31P** (extent), payload per build | inert (measurement) |
| **`0xC40BC`** | `58 02` = **600** | `70 17` = **6000** | **The friction-ratio normaliser in `FUN_0003b8f6` (1 kHz).** 1 reader / 0 writers image-wide | **Turns a Coulomb RELAY into a viscous damper.** See §3 | **V85 — NEW** | 🛑 **NEVER FLOWN, UNVERIFIED** |
| `0xC61B2` | 512 | **2048** | Mixer-channel clamp (1 of 4) | ×4 headroom on 2 of the 4 mixer channels. The four now sum to 5120 (stock 2048) | V22 (→1024) → **V38** (→2048) | on-car |
| `0xC61B4` | 512 | **2048** | Mixer-channel clamp (2 of 4) | as above. ⚠ `0xC61AA`/`0xC61AC` are **untouched at 512** | V22 → **V38** | on-car |
| `0xC61C0` / `C2` / `C4` | 1600 / 896 / 1280 | `FFFF` ×3 | **Angle-rate** tiers of the `STEER_STATUS` debounce state machine `FUN_0002a30e` | Raised to unsigned max ⇒ **the angle-rate arm of the "no torque alert 2" debounce can never fire** | **V36** | on-car |
| `0xC64B4` / `B6` / `B7` / `B8` | 112 / 54 / 64 / 112 | `FF` ×4 | **Torque** tiers of the same debounce SM | Same, on the torque arm. Together with `0xC61C0-C4` this is **V37's gentle-EME fix** — the one confirmed cure in the kit's history | **V36** (3 of 4) → **V37** (4th) | ✅ **measured on-car — resolved gentle EME 2026-07-14** |
| `0xC64DE` | 17 | **27** | A byte cal read at 18 sites in the `0x29xxx`–`0x2Bxxx` arbitration / `STEER_STATUS` / ENABLE region | ⚠ **UNKNOWN.** The old builder label "EME ramp step" is **unsupported and was retracted**. It has ridden along on every flashed build since V22 | **V22** | carried; effect unknown |
| `0xC6598` `C659C` `C65AC` `C65B0` `C65C4` `C65C8` `C65CC` | f32 1.0, 1.0, −1.0, −1.0, 0.0, 1.5, 2.0 | f32 **5.0, 5.0, −5.0, −5.0, 5.0, 5.0, 5.0** | **FLOAT mirror** of the soft-EME corridor / boost walls | ×5 corridor and boost widening. Must move in lockstep with the int copy below — they are the `FUN_00043e44` DTC-`0xF00049` lockstep pair | V29 → V30 → **V38** | on-car |
| `0xC674E` `C6750` `C675A` `C675C` `C6768` `C676A` `C676C` | i16 1024, 1024, −1024, −1024, 0, 1536, 2048 | i16 **5120, 5120, −5120, −5120, 5120, 5120, 5120** | **INT** copy of the same walls (scale 1024 ct = 1.0) | as above. ✅ Mirror consistency verified: every int is exactly 1024× its float twin | V25 → V30 → **V38** | on-car |
| `0xC62EA` | `40 01` = 320 | `00 00` = **0** | The **low-speed steer lockout window**, ≈ 5 km/h | Window collapsed to zero ⇒ the lockout that sets `STEER_STATUS = 3` and kills `STEER_CONTROL_ACTIVE` + the authority ramp **never engages**. This is what lets LKAS work at creep | **V53** | on-car (V53–V77, V81–V85) |
| `0xE4194…0xE4245` `0xE5194…0xE521D` (8 records × 9 cells) | 15360 | **16384** | `arb_setpoint_limit` — the LKAS setpoint clamp, a **degenerate (flat) 9-point LERP** | **+6.7% top-end setpoint** at every tier. V38 patched all 8 selector-reachable records (`sel {0,1,3,4,6,7,8,9}`); records `sel {2,5,10,11}` are left at 15360 because the selector cannot reach them | **V38** | on-car |

### Anchor checks (the off-by-`0x1000` trap)
`tp = 0xBF000`. Every `tp`-relative address above was anchored against a value read from the image:
`tp+0x50BC = 0xC40BC` (600 ✓) · `tp+0x507E = 0xC407E` (511 ✓) · `tp+0x746C = 0xC646C` (891 ✓) ·
`tp+0x7CD0 = 0xC6CD0` (3564 ✓). 🛑 `tp+0x6000 = 0xC5000`, **not** `0xC6000`.

### What is STOCK and must be understood as stock
| addr | value | why it matters |
|---|---|---|
| **`0xC407E`** | **511** on stock **and** on V85 | ✅ **CONFIRMED.** Honda's own hard-fault interlock clamp, **one count under its own 512 trip**. V73 raised it to 850 and V74/V75 hard-faulted. It is **not in the diff at all** |
| `0xC63A0` | 1024 (stock = 1024) | Path-2 damper weight, Honda's. V72–V76 and V81 carried 2048; V83a/V84/V85 do not |
| `0xC6444` | 512 | r26 engaged arm, left stock on purpose |
| `0xC64C8` | 0 | aggregator mode = **pass-through** |
| `0xD2006` | 102 | blend cal, stock |
| `0xC64FA` | 5 | stock |
| `gain_A` `0xC6A68`/`0xC6A7C` | Y = [3072, 3072, 2434, 2048] / [3072, 3072, 2488, 1536] | **byte-stock** |

---

## 3. THE ONE NEW THING IN V85 — `0xC40BC`, 600 → 6000

### Where it sits

```
  gp-0x6b98  (DELIVERED motor command, hard-clamped to ±0x2000)
      │
      ├──────────────► model  = EMA2(gp-0x6b98·polarity/1024, α=573/4096)
      │                        + clamp(FIR(EMA2(gp-0x4f60/1024, α=3686/4096)·1159/32768), ±15)
      │                          · LERP(gp-0x6a10, X@0xC6B66 / Y@0xC6B80)/1024
      │
  gp-0x6abc  (motor RATE)
      │
      └──► iVar20 = polarity · gp-0x6abc · 12                      @0x3BAB0
                │
                └──► ratio = clamp(iVar20 / cal(0xC40BC), ±1.0)    @0x3BAB4   ◄── THE CELL
                                                                                  600 → 6000
                             │
      FRICTION = clamp(EMA(|model|·ratio·102/1024 + 0·ratio, α=408/4096), ±10)
      INERTIA  = clamp(EMA2(d/dt(iVar20)·0.5·17.453293, α=246/4096)·1428·2⁻²⁴, ±10)
                             │
      gp-0x6bfc = clamp(2639 · (model − FRICTION − INERTIA), ±20000)
                             │
      FUN_0003bc20 → gp-0x6bfe → FUN_00038148 → gp-0x6b70 → FUN_00037fe6 → gp-0x6ad6
        → PID FUN_0003a382 → gp-0x6ad4 → aggregator → gp-0x6b94 → gp-0x6acc bridge → MOTOR
```

Gate (else the function writes the `0x7FFF` INVALID sentinel and the whole lane drops out):
`|gp-0x6b98| ≤ 0x2000` **and** `|gp-0x4f60| ≤ 0x6400` **and** `|gp-0x6abc| ≤ 13000` **and**
`gp-0x6752 ∈ {−1, 0, 1}`. The caller's own state guard is `andi 0x830` @`0x221D6` ⇒ `FUN_0003b8f6`
runs only in states {4, 5, 11}.

### The arithmetic, mirrored exactly

```python
# FUN_0003b8f6 @0x3b8f6 -- task 1, 1 kHz. Constants read little-endian from the image.
CAL_C40BC = 600          # 0xC40BC : bytes 58 02  (V85: 70 17 -> 6000)
RATE_GATE = 13000        # the function's OWN enable bound on |gp-0x6abc|

def ratio(gp_6abc, polarity, cal):          # @0x3BAB0 .. @0x3BAB4
    iVar20 = polarity * gp_6abc * 12        # @0x3BAB0
    q = iVar20 // cal                       # @0x3BAB4  ld.hu 0x50BC[tp],r16  (encoding 0x50BD)
    return max(-1, min(1, q))               # clamp(±1)

# the saturation point, in counts of gp-0x6abc:
#   |gp-0x6abc| * 12 >= cal   <=>   |gp-0x6abc| >= cal // 12
#   cal = 600  ->  50 counts    against a gate of 13000  ->  pinned at ±1 over 99.62% of the range
#   cal = 6000 -> 500 counts    against a gate of 13000  ->  linear over 3.8% -> the shape Honda uses
```

### What that means for the car

| `0xC40BC` | saturates at | relay index `N(50)/N(500)` | comparable |
|---|---|---|---|
| **600** (stock, and **all 84 builds before V85**) | 50 ct ≈ 10.6 °/s | **7.87** | — |
| 3000 | 250 ct | 1.64 | ≈ V75's damper (1.45) |
| **6000** (**V85**) | 500 ct ≈ 106 °/s | **1.00** | Honda's own viscous shape |

Reference: Honda's viscous damper 1.00 · V75 1.45 · **V80's bang-bang damper 3.27 — the build that
produced the worst grinding in this car's history.** This term is **2.4× worse than V80's** as shipped.

✅ **`0xC40BC` is the ONLY cell in its lane that V85 moves** — verified from the image, every other
constant the arithmetic above depends on is byte-stock: `0xC40D0` = 408 (the lane's only pole, so **no
phase change**) · `0xC40D2` = 102 · `0xC4080` = 0 (so `FRICTION` is purely `|model|`-proportional) ·
`0xC40D4` = 573 · `0xC40D6` = 246 · `0xC40D8` = 3686 · `0xC613A` = 1159 · `0xC6468` = 2639 ·
`0xC646E` = 1428. `0xC646C` (the shared sensor scale) = **891, Honda's** · `0xC6AF0` (V56's mute
target) = **5, Honda's**.

Because `FRICTION` is proportional to `|model|`, and `model` is dominated by the **delivered motor
command**, this relay is **engagement-scaled with no engagement flag anywhere in it**.

🛑 **THE HONEST RISK.** This **removes dissipation**. The reduction is a flat **10×** at and below
50 counts ≈ **10.6 °/s — most ordinary steering** — tapering to 1.00× only above 500 counts (106 °/s).
The term is dissipative and V56's mute of this same lane's terminus is on record as having **cost
damping and feel**. The argument for doing it anyway is that a relay's harmonic injection is not clean
damping and its gain *rises* as amplitude falls — **that is an argument, not a measurement.** If the
6–9 Hz micro-ratchet gets worse, this is why, and **reverting is two bytes**.

---

## 4. THE 121 INERT BYTES — other cars' mode records

Every table address here was **dereferenced from its pointer array in the V85 image**. All ten pointer
arrays (`FactorB 0xC9CCC` · `FactorC 0xC9E9C` · `FactorD 0xC9DB4` · `FactorE 0xC9F84` ·
`Ceiling 0xC77A0` · `Friction 0xCBE74` · `gain_B 0xCBF5C / 0xCC044 / 0xCC12C / 0xCC214`) are
**byte-identical to stock**, so the dereference is Honda's own.

**This car = `TVCA4` = modes 24 (manual) / 25 / 26 (engaged) / 27.** Read out of V85:

| family | m24 | m26 | vs stock |
|---|---|---|---|
| FactorB | `0xD6760` Y=[1024,1024,1024,1024] | `0xD774C` Y=[1024,1024,1024,1024] | **STOCK** |
| FactorC | `0xD67E4` Y=[0, 234, 429, 908] | `0xD77D0` Y=[0, 234, 429, 908] | **STOCK** |
| FactorD | `0xD67A4` Y=[700, 1024, 1024, 1024] | `0xD778C` Y=[700, 1024, 1024, 1024] | **STOCK** |
| FactorE | `0xD6820` X=[60,400,2500,4000] Y=[0,140,539,927] | `0xD780C` same | **STOCK** |
| Friction | `0xD6A64` Y=[−9830, −5734, −1966] | `0xD7A54` same | **STOCK** |
| gain_B ×4 | `0xD6A9C` / `0xD6AD8` / `0xD6B14` / `0xD6B50` | `0xD7A88` / `0xD7AC4` / `0xD7B00` / `0xD7B3C` | **STOCK** |

The 121 non-stock bytes in `[0xCE000, 0xD9FFF]` all belong to modes
**0, 1, 2, 3, 4, 5, 10, 11, 12, 14, 15, 17, 23, 29, 32, 33** — every one a different vehicle variant's
record. Notable members:

- `0xD2A7E` and `0xD2ABA` = **`gain_B` mode-10** Y rows, both `[5244, 5244, 5244, 5244]` (stock
  `[3072, 3072, 2322, 1536]` / `[2561, 2561, 2247, 1947]`). Written by V72's "Lever A" and inherited
  ever since. **This is the byte proof that the r24 dose ladder never existed** — mode 10 is not this
  car's mode.
- The `FactorC m*/Y[0]` and `FactorE m*/X[0], X[1], Y[0], Y[1], Y[2]` edits across blocks
  `0xCE000`–`0xD9000` are the V72–V75 damper package, applied by mode index and left behind.

✅ **V84 genuinely deleted the engaged-only damper.** Block `0xD7000` — which holds *every* mode-24…27
record — **does not appear in the stock→V85 diff at all.**

---

## 5. FROZEN CELLS — what a V86 must preserve

`build_v85_tva.py` declares **10 `FROZEN_CELLS` + 2 `FROZEN_BYTES` = 12** items. All 12 verified from
the V85 image and confirmed byte-identical to V84:

| addr | required value | stock? | why |
|---|---|---|---|
| `0xD77DA` | **0** | = stock | FactorC mode-26 Y[0] → Honda. **The engaged-only damper, deleted at V84** |
| `0xD77EE` | **0** | = stock | FactorC mode-27 Y[0] → Honda (mode 27 is a *second* engaged column on `TVCA4`) |
| `0xD7822` | **60** | = stock | FactorE mode-27 X[0] → Honda |
| `0xD7824` | **400** | = stock | FactorE mode-27 X[1] → Honda |
| `0xD782C` | **140** | = stock | FactorE mode-27 Y[1] → Honda |
| `0xC6446` | **5244** | non-stock | Lever B's r24 engaged arm, the flown V67/V68 value |
| `0xC6444` | **512** | = stock | r26's engaged arm — stock deliberately, as the S3 lever |
| `0xC407E` | **511** | = stock | 🛑 **The DTC-`0x1d` interlock.** Honda's clamp, one count under its own 512 trip |
| `0xC6CD0` | **3564** | non-stock | V57's decoupled forward reader — the 4× LKAS setpoint |
| `0xC63A0` | **1024** | = stock | Path-2 damper weight, Honda's |
| `0x3AA96` | **`0xFB`** | non-stock | Lever B's gate repoint, the flown V67/V68 byte |
| `0x454FE` | **`0xB5`** | non-stock | V42's macro-ratchet fix (`br` not `bne`). **Lost 3× already; keep** |

⚠ **Bookkeeping discrepancy, flagged not fixed:** `docs/STATE.md` line 99 says "all **14** frozen cells
byte-identical to V84". The builder's list is **12**. No 14-item list exists in the kit; the "14" in
`BUILD-LINEAGE.md` line 524 refers to the *14 friction sites*, a different set. All 12 pass.

**Standing instruction: the damper cells stay FROZEN in every future build** (`0xD77DA`, `0xD77EE`,
`0xD7822`, `0xD7824`, `0xD782C`) — the V84 flight gave a four-point monotone dose–response tying the
damper to the 26–31 Hz band, and any regression toward V81's 25.1% burst duty is an abort signal.

---

## 6. CRC / integrity

Method: replay of the bootloader's `CheckProgrammingDependencies` walk (`FUN_0000b006`),
`analysis-2020accord/verify_bootloader_crc.py`. CRC primitive = HW DCRA @`0xFF836020` = Ethernet
CRC32 = `zlib.crc32`. Each block's stored trailer word sits at `block_start + block_len`.

| check | result |
|---|---|
| Bootloader walk (**with** the verified `0xC6000` bridge) | **49 blocks, 0 mismatches — PASS** |
| Full linked-list walk (**no** bridge, hygiene check) | **50 blocks, 0 mismatches — PASS** |
| `[0xC5000, 0xC5FFC)` — the block the bootloader **skips** | calc `0x09C1200B` = stored, and **byte-identical to stock**: **0 differing bytes written into it** |
| CRC trailer words that moved vs stock (13) | `0xC4FFC` `0xC6FFC` `0xCEFFC` `0xCFFFC` `0xD0FFC` `0xD2FFC` `0xD3FFC` `0xD4FFC` `0xD6FFC` `0xD8FFC` `0xD9FFC` `0xE4FFC` `0xE5FFC` |

The `0xC5000` result matters: V40 wrote motor-rate cap tables into that block and left its CRC stale,
and V40 faulted at ignition. V85 does not touch it at all.

---

## 7. Cross-build matrix — read from the IMAGES

Same cells, every build since V67. `0x454FE`/`0x3AA96` in hex; the rest decimal.

| cell | STOCK | V67 | V68 | V72 | V73 | V74 | V75 | V76 | V78 | V79 | V80 | V81 | V83a | V84 | **V85** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `0xC40BC` friction normaliser | 600 | 600 | 600 | 600 | 600 | 600 | 600 | 600 | 600 | 600 | 600 | 600 | 600 | 600 | **6000** |
| `0xC407E` fault interlock | 511 | 511 | 511 | 511 | **850** | **850** | **850** | **850** | 511 | 511 | 511 | 511 | 511 | 511 | **511** |
| `0xC63A0` Path-2 damper wt | 1024 | 1024 | 1024 | 2048 | 2048 | 2048 | 2048 | 2048 | 1024 | 1024 | 1024 | 2048 | 1024 | 1024 | **1024** |
| `0xC6446` r24 engaged arm | 512 | 5244 | 5244 | 512 | 512 | 512 | 512 | 5244 | 512 | 512 | 512 | 512 | 512 | 5244 | **5244** |
| `0xC6444` r26 engaged arm | 512 | 512 | 512 | 512 | 512 | 512 | 512 | 512 | 512 | 512 | 512 | 512 | 512 | 512 | **512** |
| `0xC6CD0` 4× LKAS fwd gain | 65535 | 3564 | 3564 | 3564 | 3564 | 3564 | 3564 | 3564 | 65535 | 65535 | 65535 | 3564 | 3564 | 3564 | **3564** |
| `0x2A1F0` fwd-reader disp | 29804 | 31952 | 31952 | 31952 | 31952 | 31952 | 31952 | 31952 | 29804 | 29804 | 29804 | 31952 | 31952 | 31952 | **31952** |
| `0x3AA96` Lever B gate | `C5` | `FB` | `FB` | `C5` | `C5` | `C5` | `C5` | `FB` | `C5` | `C5` | `C5` | `C5` | `C5` | `FB` | **`FB`** |
| `0x454FE` ratchet fix | `BA` | `BA` | `BA` | `B5` | `B5` | `B5` | `B5` | `B5` | `BA` | `BA` | `B5` | `B5` | `B5` | `B5` | **`B5`** |
| `0xC62EA` low-speed lockout | 320 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 320 | 320 | 320 | 0 | 0 | 0 | **0** |
| `0xC61B2` mixer clamp | 512 | 2048 | 2048 | 2048 | 2048 | 2048 | 2048 | 2048 | 2048 | 2048 | 2048 | 2048 | 2048 | 2048 | **2048** |
| `0xD77DA` FactorC m26 Y[0] | 0 | 0 | 0 | 0 | 0 | 429 | 566 | 429 | 566 | 566 | 566 | 566 | 566 | 0 | **0** |
| `0xD782C` FactorE m27 Y[1] | 140 | 140 | 140 | 140 | 140 | 539 | 539 | 539 | 140 | 140 | 140 | 539 | 539 | 140 | **140** |
| `0xD7A5C` Friction m26 Y[0] | −9830 | −9830 | −9830 | −9830 | −9830 | −14745 | −14745 | −14745 | −9830 | −9830 | −9830 | −9830 | −9830 | −9830 | **−9830** |

Reading the matrix:

1. **`0xC40BC` is virgin across every build ever made** and moves for the first time in V85. That is
   the entire novelty of this build.
2. **V78/V79/V80 sit on a V38 base** — that is why `0xC6CD0`, `0x2A1F0` and `0xC62EA` snap back to
   stock in those three columns. Those builds were flown **without** the 4× LKAS gain and **without**
   the low-speed lockout removal. V81 restored all three.
3. **`0x454FE` has been silently lost and restored repeatedly.** Traced byte-by-byte through the whole
   image chain: `STOCK BA → V42 B5 → V49P BA → V50 B5 → V50probe BA → V52 B5 → V53 BA → V71a B5 →
   (V76 v38-base) BA → V77 B5 → V78 BA → V80 B5`. Two long silent absences in the main lineage:
   **V53–V70 (18 builds)** and **V78–V79**. It is present now — and currently **measured inert**
   (`gp-0x67fa == 4` fires 0/123,277 driving frames), so its presence is insurance, not a live fix.
4. **`0xC6444` has been frozen at stock 512 for every build in this window.** It is the untried S3 lever.
5. **The damper row (`0xD77DA` / `0xD782C` / `0xD7A5C`) is back at Honda's values from V84 onward.**

### What class of build V85 is, against the arc since V38

| era | class of intervention |
|---|---|
| V38–V52 | authority, filters, poles, code caves |
| V53–V61 | telemetry probes and lane mutes |
| V62–V73 | the **rate lane** (r24 / r26) |
| V74–V83a | the **base-assist damper** (FactorC/FactorE surfaces) |
| V84 | damper **reverted to Honda**; Lever B re-delivered |
| **V85** | **the plant-model friction lane — a term that had never been touched by any build.** Not a gain, not a rate limit, not a filter, not a pole, not a damper surface. It changes the **shape of a nonlinearity** (relay → viscous) at a fixed operating point |

**This is genuinely new, not a re-run.** `0xC40BC` and the seven cals around it (`0xC40D0`, `0xC40D2`,
`0xC4080`, `0xC40D4`, `0xC40D6`, `0xC40D8`, `0xC646E`) are named in **zero** of the 84 build scripts —
the entire plant-model calibration block was virgin. The nearest prior art is **V56**, which *muted*
this lane's terminus (`0xC6AF0` → 0) rather than reshaping it, returned a NULL on 18–22 Hz, and cost
damping — which is exactly why V85's pre-registered expectation is that **S1 should not move.**

---

## 8. Evidence markers

**[EVIDENCE]** — every byte value, address, hash, CRC result, pointer dereference, mode-record identity,
the `0xC407E = 511` confirmation, the zero-unattributed diff, the frozen-cell verification, and the
cross-build matrix. All from raw little-endian byte reads of the images on disk, Python only.

**[EVIDENCE]** — the physical meaning of `0xC40BC`, `0xC6446`/`0x3AA96`, `0xC62EA`, `0xC6CD0`/`0x2A1F0`,
`0x454FE`, `0xC61C0-C4`/`0xC64B4-B8`, and the `0xE4000`/`0xE5000` setpoint records: each cited to a
kit document or memory whose own method is recorded there. The `0xE4000` selector set `{0,1,3,4,6,7,8,9}`
was **re-derived independently here from the image** and matches.

**[BELIEF]** — that V85's `0xC40BC` change will improve S2/S3/S4. It has never been on a car.

**UNKNOWN** — the physical meaning of `0xC64DE` (17 → 27). Its old "EME ramp step" label was retracted
as unsupported; its 18 read sites are all in the arbitration / `STEER_STATUS` / ENABLE region. It has
ridden along on every flashed build since V22 and has never been isolated.
