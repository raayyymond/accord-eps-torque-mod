# HANDOFF 2026-08-03 — V68 flew, and the lane-change symptom is at 28 Hz, not 40–49 Hz

**★★★★ THE RESULT: the operator's highway lane-change vibration was CAPTURED — a 2.5 s burst at
28.12/28.51 Hz, 1468 counts peak-to-peak on the torsion bar, during an openpilot ALC right lane
change at 26 m/s. It is NOT in grind #2's 40–49 Hz band (69 counts in the same window), it is NOT a
wheel order (2 = 24.93, 3 = 37.40 Hz) and it is NOT an engine order (1 = 26.10, 2 = 52.20 Hz).**

**★★★ AND THE ARM THE CORPUS NEVER HAD IS CLOSED.** Route `4c` supplies **234.8 s of disengaged
highway above 20 m/s** against the entire prior corpus's **0.0 s**. The operator's *"only when
LKAS is engaged"* is testable for the first time — and for **40–49 Hz it is REFUTED**.

**🛑 AND HONDA'S OWN 1 kHz DETECTOR STAYED AT ZERO** — bit5 (`gp-0x67df != 0`) fired **0 times in
53,991 frames**, including straight through the lane-change burst.

Read alongside `docs/STATE.md`, `docs/BUILD-LINEAGE.md` and the predecessor
`handoffs/2026-08/HANDOFF-2026-08-03-the-detector-was-always-there.md`.

---

## 1. THE TWO ROUTES, AND WHAT MAKES THEM DIFFERENT

| route | id | build | driving | operator |
|---|---|---|---|---|
| `4c` | `0000004c--d0ea3c14b4` segs 4–8 | V68 | **LKAS OFF**, manual highway | *"No grind vibration felt"* |
| `4e` | `0000004e--11f5b814b6` segs 31–34 | V68 | **LKAS ON**, highway | *"Definitely felt the grind #2-like vibration when changing lanes, otherwise this highway was relatively straight"* |

Highway exposure, in seconds, measured on the mean-rate lattice:

| cut | `4c` engaged | `4c` **disengaged** | `4e` engaged |
|---|---|---|---|
| v ≥ 20 m/s | 11.9 | **234.8** | 160.6 |
| v ≥ 25 m/s | 0.0 | **148.4** | 55.1 |
| v ≥ 28 m/s | 0.0 | **42.7** | 0.0 |

★ The prior corpus held **0.0 s disengaged at every cut from 12 to 28 m/s** across 6,034 s and
eleven routes, verified two ways. That is the gap route `4c` fills.

🛑🛑 **THE CONFOUND, STATED BEFORE ANY NUMBER — AND IT IS STRUCTURAL, NOT INCIDENTAL.** V68's
control path is byte-identical to V67's, and V67's rate-lane arm is CONDITIONAL on the firmware's
own LKAS gate `gp-0x6806`. So on these routes

    LKAS ON   ==  gate open   ==  Kd = 2.00x       (route 4e: gate 100.000% of frames)
    LKAS OFF  ==  gate closed ==  Kd = 1 (stock)   (route 4c: gate 0.0% on segs 5-7)

**Arm and dose are the same variable.** Every cross-arm number below is "engaged AND doubled"
versus "disengaged AND stock". This is stated at every table rather than buried.

---

## 2. ✅ BUILD CONFIRMED FROM THE PROBE, AND THE CAVE VERIFIED BY HAND

Per the V64 lesson — confirm the firmware from the log, never the filename.

**From the logs:** byte4 takes exactly two values, `{0x8F, 0xCF}`, both inside V68's eight legal
payloads. **bit3 (the build-class marker) = 1 in 53,991/53,991 frames = 100.000%.** V66/V67 emit
bit3 = 0, so the payload sets are disjoint and those builds are excluded absolutely. `VOID` = 0,
`illegal` = 0, ordering violations = 0. bit6 tracks `carControl.latActive` exactly.

**From the flown image** (`_v68_plain_image.bin`, raw little-endian byte read, decoded by hand —
the required second method whenever a reading is load-bearing):

| addr | bytes | decode | V67 carried |
|---|---|---|---|
| `0xC4B34` | `20 3e 88 00` | `movea 0x88,r0,r7` — bit7 liveness **+ bit3 class marker** | `0x80` |
| `0xC4B38` | `84 37 fb 97` | `ld.bu -0x6806[gp],r6` — the LKAS gate | same |
| `0xC4B3C` | `61 32 b6 05` | `cmp 0x1,r6` / `blt +6` → bit6 = `!= 0` | same |
| `0xC4B44` | `a4 37 21 98` | `ld.bu -0x67df[gp],r6` — **ODD disp `0x9821`, hw1 `a437`** ✅ | `-0x671d` |
| `0xC4B48` | `61 32 b6 05` | `cmp 0x1,r6` / `blt +6` → **`>= 1`** | `cmp 0x5,r6` |
| `0xC4B50` | `84 37 e7 98` | `ld.bu -0x671a[gp],r6` — even disp, `hw2 = disp\|1` ✅ | same |
| `0xC4B58` | `27 3e 10 00` | `movea 0x10,r7,r7` → bit4 | same |

Both displacement parities are exactly as the build script asserts, and `blt` against an imm5 of 1
on a **zero-extending** `ld.bu` is the same test as an unsigned one for a byte in `[0,255]`.

⚠ **A NAMING TRAP FOR THE NEXT READER:** `builds/v50_v79/build_v68_tva.py` still calls bit4's constant `BIT_RATE`
and defines `RATE_DISP = 0x6AC0` — leftovers from the **superseded** rate-axis probe, whose `.rwd`
is prefixed `SUPERSEDED-DO-NOT-FLASH`. The live `CELLS` list is
`{0x6806, 0x67DF, 0x671A}` and the flown bytes above agree. **Read `CELLS`, not the constant name.**

✅ **FLIGHT-CLEAN, two independent methods.** `ST == 4` = **0** and `ST == 3` = **0** on both routes,
gridded *and* on the raw un-gridded `0x18F` src-1 stream (53,991 frames). Watchlist
(`steerUnavailable` / `steerTempUnavailable` / `canError` / `controlsMismatch` /
`immediateDisable` / `steerSaturated`) **CLEAN on both routes**. The zero-EME streak extends.

---

## 3. 🛑 THE DETECTOR READ ZERO — AND THE HONEST WEIGHT OF THAT

`gp-0x6c2c` is a **band-pass peaking near 61 Hz** (>90% of its 21 Hz gain out to ~180 Hz), which is
why V68 spent two rungs on it: it is the kit's only instrument above the 50.00 Hz CAN Nyquist.

| rung | meaning | fired |
|---|---|---|
| **bit5** `gp-0x67df != 0` | the FSM LEFT NEUTRAL — `\|gp-0x6c2c\|` crossed ±12800. **No reversal required.** | **0 / 53,991** |
| **bit4** `gp-0x671a >= 1` | ...and then reversed at least once | **0 / 53,991** |

**Including every frame of the lane-change burst in §5.** V67 read the same detector at `>= 5` and
got 0.000% over 186,321 frames; V64 flew this exact `ld.bu -0x67df[gp],r6` word on route 35 and also
read zero. **The bottom rung of the ladder is now measured, and it is empty.**

🛑🛑 **THE LIMIT, AT FULL STRENGTH — AND IT IS THE V64 LESSON ONE LAYER DOWN.** This is a null on a
**cell that has never once been observed non-zero in this kit**. There is **no positive control**.
It therefore bounds oscillation amplitude *only if the detector is genuinely live*, and "the
detector is disabled / its input is dead / `FUN_000428d4` is not reached in this operating mode" is
**not excluded by this measurement**. What the null does establish, conditional on liveness: no
oscillation anywhere in ~1–200 Hz reached the trip amplitude (**1056 counts at 60 Hz, 1104 at 45,
1186 at 100, 1683 at 21.3** — all on `gp-0x4f50`, whose own clamp is ±13000).

⇒ **OPEN, and it is the single highest-value firmware question left:** trace `gp-0x67df`'s writer
and establish whether `FUN_000428d4`'s detector stage has an enable condition. Until then the
detector's null is *bounded evidence*, not proof of silence. ⚠ `gp-0x4f50`'s deg/s conversion
remains **[OPEN]** and must not be closed by borrowing `gp-0x6ac0`'s 4.7121 counts/deg-s.

---

## 4. ★★★ THE ORDER VETO, AND THE 40–49 Hz ARM TEST

**The veto ran first and 30–49.5 Hz is empty on BOTH arms.** Averaged periodogram per route ×
speed bin, prominence against its own local floor, criterion **> 4**:

| route / arm | 30–49.5 Hz prominence | 8–30 Hz positive control |
|---|---|---|
| `4c` disengaged, 3 speed bins | **1.89 – 2.45** | 3.62 / 4.90 / 10.22, order 1 recovered to 0.17 Hz |
| `4e` engaged, 3 speed bins | **1.81 – 2.02** | 15.10 / 52.69 / 40.60 |

⇒ **Sixth independent confirmation that there is no spectral line in grind #2's band at highway**,
and the first on a **disengaged** arm.

★★ **AND THE ARM TEST ITSELF.** Maneuver-vs-control computed **inside each arm against its own
split-half null**, so route, day, road and tyre all cancel. One absolute pair of cuts for both arms
(maneuver `|rate|pk >= 19.0 deg/s`, control `<= 11.0`):

| band | **ON (4e, engaged)** | **OFF (4c, manual)** | null |
|---|---|---|---|
| 1–4 (validity) | 1.182 [0.818, 1.506] | 1.592 [0.807, 1.823] | [0.78, 1.29] |
| **18–22** | **3.129 [2.408, 5.298]** | 1.780 [1.444, 1.927] | [0.66, 1.51] |
| **24–28** | **5.098 [2.798, 6.160]** | 2.056 [1.470, 2.812] | [0.79, 1.23] |
| 30–40 | 2.072 [1.550, 2.292] | 2.081 [1.667, 2.711] | [0.72, 1.42] |
| **40–49 (grind #2)** | **2.516 [1.561, 3.701]** | **2.558 [1.469, 3.747]** | [0.77, 1.31] |

⇒ 🛑 **"IT ONLY HAPPENS WITH LKAS ENGAGED" IS REFUTED FOR 40–49 Hz.** The maneuver rise in grind
#2's band is **the same number in both arms** (2.52 vs 2.56), and 30–40 Hz matches too (2.07 vs
2.08). Engagement does nothing there.
⇒ ★★ **THE ENGAGEMENT-CONDITIONAL PART IS AT 18–28 Hz** — 18–22 rises 1.8× more when engaged,
24–28 **2.5× more**. That is a different band from the one this kit has been hunting.

⚠ **The raw cross-arm level contrast is NOT interpretable and is reported only to be dismissed.**
The 1–4 Hz exposure check fails at **0.213** — the driver supplies the torque when LKAS is off
(sustained effort p50 **565** counts) and the motor supplies it when LKAS is on (p50 **96**). The
(speed, effort, |rate|) cell matcher found **zero** cells with ≥4 windows in both arms; **0.0%** of
manual windows fall below the engaged arm's p90 effort. The arms do not overlap in effort **at
all**, so only the within-arm contrast above carries weight.

---

## 5. ★★★★ THE EVENT ITSELF — route `4e`, segment 33, t = 51.3 s

openpilot fires `preLaneChangeRight` at **t = 51.34 s**, then `laneChange` from 51.85 s. Blinker on
51.5 → 55.5 s. Engaged throughout, `ST == 0`, probe `0xCF` every frame.

| quantity | value |
|---|---|
| speed / rpm | **25.93 m/s** (58 mph) / 1566 |
| steering angle swing | −4.8° → **−11.3°** → −2.7° |
| steering rate peak | **38 deg/s** |
| **torsion bar peak-to-peak** | **1468 counts** (−776 … +692) |
| **26–30 Hz envelope** | **614** — route median 31 ⇒ **20×** |
| spectral lines | 27.34 / 27.73 / **28.12** / **28.51** / 28.90 Hz |
| line prominence | **up to 107** |
| **40–49 Hz envelope, same window** | **69** |
| 18–22 / 24–28 / 30–40 envelope | 348 / 369 / 66 |
| detector bit5 / bit4 | **0 / 0** |

**IDENTITY — what it is not, with the arithmetic:**

| candidate | predicted at this operating point | measured |
|---|---|---|
| wheel order 2 | 24.93 Hz | **28.12–28.51** ✗ |
| wheel order 3 | 37.40 Hz | ✗ *(but see below)* |
| engine order 1 | 26.10 Hz | ✗ |
| engine order 2 | 52.20 Hz | ✗ |

✅ **The estimator's own positive control fires in the same window:** lines at **37.10 / 37.49 Hz**
(prominence 18–22) sit on **wheel order 3 = 37.40 Hz**. So this analysis *does* find orders when
they are there — and the 28 Hz cluster is not one.

⇒ **The felt lane-change vibration is a ~28 Hz transient, and grind #2's band is quiet during it.**
The operator's *"grind #2-like"* is a fair description of the sensation; it is not the same mode.

---

## 6. 🛑 THREE CORRECTIONS OF MY OWN, MADE THIS SESSION

**(a) "There is an engaged-only fixed 28 Hz line" — WITHDRAWN, and it was the 42 Hz trap again.**
The whole-route averaged spectrum gave `4e` a 28.13 Hz peak at prominence **18.81** and `4c` only
**3.33**, which reads as engaged-only. It survived the band-centre test (the peak did not move as
the search band swept 24–30 / 20–35 / 18–40 / 15–45 / 23–33 Hz), so I was ready to call it a mode.
**Per-window analysis killed it:** 26–30 Hz content appears in **133/177 = 75.1%** of manual windows
at median prominence **7.50**, versus **88/121 = 72.7%** at **6.27** engaged — *more* on the manual
route. The route average smeared `4c`'s line only because `4c` swept more speed **and its line is
wheel order 2**: Theil-Sen **+1.0352 [+1.0012, +1.0616] Hz per m/s** against order 2's **+0.9616**,
with per-bin agreement of 0.1–0.35 Hz (24.68/25.02, 26.68/26.82, 28.12/28.22).
🛑 **THE RULE THIS ADDS:** an averaged spectrum compares two routes only if their **speed
distributions match**. Otherwise a moving order smears in one and concentrates in the other, and
the difference is the exposure, not the car.

**(b) Command↔bar coherence was computed against the wrong field.** I used `e4req`, which is
`(d[2] >> 7) & 1` — the **engagement bit** — not `e4tq` = `i16be(d, 0)`, the command. That is why
every band read exactly `0.000`. Redone against `e4tq`: `4e` engaged reads **0.343** at 26.5–29.5 Hz
and **0.016** at 40–49, `r47` **0.269** / **0.002**, against grind #1's recorded **0.917**. ⚠ The
manual negative-control column is **degenerate (n = 1 usable window)** and must not be quoted.

**(c) The maneuver contrast was first run with per-arm decile cuts** (19.0 vs 18.0 deg/s) and **no
null**. Both fixed in §4. A ratio without a null is not a finding.

---

## 7. ⚠ THE RATE-LANE SUGGESTION — REAL SHAPE, INSUFFICIENT POWER

The 24–30 Hz band is where V62's own corner table recorded **2.66×** for its flat Kd ×2, and
V67/V68 apply that ×2 **only while engaged**. So the obvious hypothesis is that the lane-change
burst is the rate lane again, one band lower than grind #2. Pooling every highway window in the
corpus by **arm-resolved dose** (gated builds contribute engaged windows to Kd = 2 and manual
windows to Kd = 1):

**Within each dose, maneuver / control** — null [0.86, 1.15]:

| band | Kd = 1 (stock) | Kd = 2 |
|---|---|---|
| 18–22 | 8.583 [2.60, 18.74] | 6.450 [5.12, 7.50] |
| **24–28** | 6.694 [3.06, 11.83] | **12.874 [7.16, 22.18]** |
| **26–30** | 3.665 [2.51, 10.22] | **11.822 [6.61, 20.44]** |
| 30–40 | 3.018 [2.27, 3.96] | 2.994 [2.60, 3.92] |
| 40–49 | 3.304 [2.66, 4.75] | 3.903 [3.40, 4.72] |

**Direct dose ratio Kd = 2 / Kd = 1, maneuver windows only** (106 vs 39 windows, 41 vs 17 blocks):

| band | maneuver windows | split-half null | control windows |
|---|---|---|---|
| **26–30** | **3.334 [1.201, 6.492]** | **[0.33, 3.36]** | 1.034 [0.904, 1.290] |
| 24–28 | 1.797 [0.806, 5.382] | [0.30, 3.53] | 0.934 [0.822, 1.082] |
| 40–49 | 1.359 [0.929, 1.806] | [0.62, 1.60] | 1.151 [1.022, 1.308] |
| 30–40 | 1.101 [0.830, 1.676] | [0.61, 1.63] | 1.109 [0.996, 1.259] |

⇒ 🛑 **SUGGESTIVE, NOT ESTABLISHED — AND I AM NOT CALLING IT MORE THAN THAT.** The 26–30 Hz point
estimate is **3.334×** and its CI lower bound **1.201** sits *inside* a split-half null whose upper
bound is **3.36**. It does not clear its own floor. The null is that wide because the Kd = 1
maneuver arm holds only **39 windows in 17 blocks** — roughly **50 s of active highway
maneuvering**. The control-window column being flat (1.034) is consistent with a transient-only
effect, but consistency is not evidence.
⚠ **And the dose contrast is confounded with arm and route:** the Kd = 1 maneuver pool is dominated
by `4c` (manual, driver-steered) and `r2b`; the Kd = 2 pool by `r47`. Driver-initiated and
ALC-initiated maneuvers are not the same excitation.

---

## 8. ★★★ RECOMMENDED NEXT STEP — ONE DRIVE, NO BUILD

**Because V68 is LKAS-gated, the car already carries both doses.** The A/B that settles §7 needs no
new firmware:

> **One highway run on a single stretch, alternating LKAS ON / OFF roughly every 60 s, with
> DELIBERATE lane changes in BOTH arms.**

That makes dose, road, tyres, temperature and time all within-route — the identical design that
separated V66 from V67 on route 47 and closed the creep grind #2 arm on route `4a`. Power, computed
rather than asserted:

| Kd = 1 maneuver blocks | split-half null upper bound |
|---|---|
| 17 (today) | 3.65× |
| 34 (2×) | ~3.16× |
| **51 (3×)** | **~2.42×** |
| 68 (4×) | ~2.35× |
| **102 (6×)** | **~1.96×** |

The measured point is **3.334×**, so a null ceiling below ~2.2× makes it decisive ⇒ **~150–250 s
more of *active maneuvering* in the LKAS-OFF arm**, i.e. lane changes, not cruising. At ~8 s per
lane change that is **20–30 deliberate lane changes with LKAS off**, plus a matching set with it on.

🛑 **NO CONTROL-PATH CHANGE IS SUPPORTED YET, and the reason is not "we found nothing."** It is that
the one lever the data points at — the rate lane, at 24–30 Hz — has a **point estimate inside its
own null**, and the last four sessions record what happens when this kit builds on a statistic that
has not cleared its floor. **Keep V68 on the car.** It is flight-clean, it keeps grind #1 fixed and
creep grind #2 at zero bursts, and it is the only build that supplies both doses on one drive.

⚠ **If the drive confirms it,** the lever is the *same* `sar 0xa` → `sar 0x9` site in `FUN_0003aa2c`
that V62 doubled and V67 made conditional — i.e. **partially reverting the thing that fixed grind
#1**. That trade must be priced before it is built, not after. Grep `build_v*_tva.py` first.

---

## 9. OPEN RESIDUALS

- 🛑 **`gp-0x67df`'s writer and `FUN_000428d4`'s enable condition — UNRESOLVED, and now
  verdict-affecting.** The detector has never been observed non-zero across V64, V67 and V68. Until
  a writer trace or a liveness argument exists, §3's null is bounded evidence, not silence.
- **`gp-0x4f50`'s physical units — [OPEN]**, deliberately.
- **`gp-0x61a0`'s writer and `gp-0x61e8`'s identity** — unresolved, not verdict-affecting.
- ⚠ **`4c` and `4e` are different roads 14 h apart** (02:48 vs 17:15 local). Every cross-route
  number is caveated in place; the within-arm contrasts in §4 are the ones that carry weight.
- ⚠ **The 28 Hz burst is n = 1 well-characterised event** plus a broader 24–30 Hz maneuver
  amplification. One event is a capture, not a rate. §8's drive is what turns it into a population.

---

## 🛑 METHOD NOTES

1. **An averaged spectrum compares two routes only if their speed distributions match.** A moving
   wheel order concentrates in a narrow-speed route and smears in a wide-speed one, manufacturing an
   "only on route X" line. New rule, and it nearly cost this session a false mode.
2. **The band-centre test is necessary but NOT sufficient.** The 28 Hz line passed it and was still
   mostly wheel order 2. Follow it with a **per-window** prominence census — a route-wide line is
   carried by many windows, not by one loud episode.
3. **Check which field you correlated.** An exact `0.000` across every band is a wiring error, not a
   result.
4. **A gated build gives you both doses on one drive.** V67/V68's conditional arm was designed as a
   control-path feature; it is also the cheapest experimental design this kit has.
