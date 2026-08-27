# TRACE — V99 flight score, route `0x82`, 2026-08-13

**Build:** V99 = V98 base + `0xC40BC` 600→300, `0xC63AC` 150→102 (revert to Honda), `0xC4B52` 00→02
(the b5 identity immediate).
**Route:** `75604b0a432fdc89_00000082--e30d55731b--{0,1}--rlog.zst`, 2 segments, 121.7 s.

**Operator's report, verbatim, and it is the primary evidence:**
> *"I did end up driving V99. I think it helped with the audible aspect of the grinding, though I'm
> not sure."*

That is **weak positive and hedged.** Nothing below overwrites it, and nothing below is called
"fixed" — he has not called anything fixed.

## Artefacts produced

| file | what |
|---|---|
| `rlog-tools/decode/extract_r82.py` | route-82 cache; adds a `ROUTES` row and calls `extract_r7d.extract_route` — the instrument is NOT reimplemented |
| `rlog-tools/decode/extract_r82_audio.py` | ⭐ NEW — the 16 kHz cabin microphone, never used by this kit before |
| `rlog-tools/score/v99_r82_score.py` | E1 / E2 / E3 / POS-1..3 / R5b / audible bands / acoustic |
| `rlog-tools/score/v99_r82_matched.py` | 🛑 the RATE-MATCHED engaged/manual contrast, both routes, + the common-stratification E1 curve |
| `analysis-2020accord/_scratch/cache/r82/` | `r82.npz`, `r82s{0,1}.npz`, `r82_audio.npz`, identity/health/census JSON |
| `analysis-2020accord/sessions/v99/v99_r82_score.json` + `.log` | the full machine-readable readout |

Reproduce with:
```
cd rlog-tools
python decode/extract_r82.py            # cache + identity + health + census
python decode/extract_r82_audio.py 82 81
python score/v99_r82_score.py
python score/v99_r82_matched.py         # rate-matched arms + common-stratification E1
```

---

## 1. GATE 0 — FAULT-FREE. ✅ PASS  [EVIDENCE]

| check | value |
|---|---|
| 0x14A `0x7FFF` sentinels | **0** |
| 0x18F `0x7FFF` sentinels | **0** |
| CONFIG_VALID duty | **1.00000** |
| OUTPUT_DISABLED duty | **0.00000** |
| DTC bit2 duty | **0.00000**, 0 transitions |
| STEER_STATUS histogram | **{0: 12004}** — one state, no 3/4 excursions |
| 0x1AB COUNTER +1 | 99.95 % · CHECKSUM 16/16 distinct |

`onroadEvents` are all driver/device side (steerOverride 216, pedalPressed 169,
gasPressedOverride 110, wrongGear/reverseGear 20 each, commIssueAvgFreq 4, selfdrivedLagging 2 =
device load, not the EPS).

## 2. IDENTITY — the pre-registered rule. ✅ PASS  [EVIDENCE]

Pre-registered (`builds/v80_v107/build_v99_tva.py` ~line 159): *b5 duty ≥ 0.999 over the whole route AND
byte7[7:6] == 2.* **IF THE IDENTITY RULE FAILS, NOTHING IN THE READOUT MAY BE REPORTED.**

| | measured |
|---|---|
| **b5 duty** | **1.000000** — 0 of 12,005 frames with b5 == 0 (V98 measured **0.0022** on the byte-identical rung) |
| **byte7[7:6]** | histogram **{2: 12,005}**, duty **1.000000** |
| byte4[7:3] field | {6, 12, 14, 20, 28, 30} — **all EVEN** |

🛑 The all-even field is **expected**, not a fault: `b3` is a measurand and `b5` is now a constant 1,
so byte4[7:3] = V98's field + 4 on every frame. **A scorer applying the ~50-build "byte4[7:3] is
always ODD" convention would have pulled this build.**

⇒ **V99 IS ON THE CAR.** The readout is unlocked.

## 3. EXPOSURE

- 121.7 s, 12,004 rows @ 98.61 Hz. **ENGAGED 59.8 s (49.8 %)** · MANUAL 60.2 s.
- **4 engagement episodes**, longest 31.3 s, 3 ≥ 10 s.
- Engaged speed p50 **6.66 km/h** (p90 18.1, max 21.4). Zero engaged time ≥ 50 km/h — the
  parking-lot creep protocol the build asked for.
- Engaged rate regimes: micro (1–13 °/s) 17.8 s · ratchet (13–50) 26.6 s · macro (>50) 8.3 s.

⭐ **The mandatory within-drive LKAS-OFF arm is PRESENT, and in a better form than route 81's.**
Route 81 appended one 59.9 s manual demonstration at the tail. Route 82 **interleaves** them:

```
m0  0.00 – 19.45  MANUAL   19.5 s  v p50  3.77  |rate| p50 50.2
ep0 19.46 – 35.31 ENGAGED  15.9 s  v p50  5.13  |rate| p50 19.3
m1 35.32 – 50.39  MANUAL   15.1 s  v p50  3.49  |rate| p50 28.8   <- flanked by engagement
ep1 50.40 – 81.68 ENGAGED  31.3 s  v p50  6.94  |rate| p50 21.1
m2 81.69 –108.37  MANUAL   26.7 s  v p50 12.60  |rate| p50 63.9
ep2 108.38–110.92 ENGAGED   2.5 s  v p50 18.94  |rate| p50  3.8
ep3 111.66–121.73 ENGAGED  10.1 s  v p50 16.71  |rate| p50  3.1
```

⚠ **The arms are NOT matched in wheel rate.** Manual |rate| p50 is 28.8–63.9 °/s against engaged
19.3–21.1. Every cross-arm statistic below is standardised over (speed × |rate|) cells and drops
cells with no counterpart, but the matched-cell coverage is the binding limit on that comparison.

## 4. POSITIVE CONTROLS

| control | measured | verdict |
|---|---|---|
| **POS-1** identity | above | ✅ |
| **POS-2** 427 non-degenerate | **245 distinct codes** (≥20), **p99 232** (≥8), max 244, **0.000 % saturation**, 49.78 Hz, src=1 | ✅ (route 81: 251 codes) |
| **POS-3** b3 constant | duty **0.0000**, **0 transitions**, engaged and manual | ✅ `gp-0x6752` constant and NEGATIVE — reproduces V98 |
| b6 latch exclusion | 427 == 1023 on **0** frames ⇒ **0 of 12,004 rows excluded** | as on 7e/7f/80/81 |

### R5b — `arg(V) − arg(B′)` must be ±180°. ✅ REPRODUCES, fifth route.

**Sign convention, self-checked before any phase number: `angle(scipy.signal.csd(x,y)) =
arg(Y) − arg(X)`; positive ⇒ y LEADS x.** Self-check: y = x delayed 5 samples at 100 Hz gave
−140.22° against an expected −140.22°.

🛑 **A correction to my own first pass, and it mattered.** The V96/V97 routes (7e/7f/80) carry
`sign(gp-0x374c>>4)` on byte4 **b6 (0x40)**; V98/V99 moved it to **b4 (0x10)** because b6/b5 were
taken by the comparators. Using one mask for all routes read a constant bit on the V96 routes and
returned NaN phases. Fixed in `score/v99_r82_score.py:load()`.

```
route  build   arg(B')-arg(rate)   arg(V)-arg(rate)   arg(V)-arg(B')   coh
 82    V99         -89.51              +87.45            +175.92       0.537
 81    V98         -78.08             +101.17            +179.76       0.571
 80    V97         -93.20              +82.23            +170.64       0.754
 7e    V96         -95.94              +87.54            -179.54       0.201
 7f    V96         -95.39              +82.89            +179.03       0.118
```

🛑 **I did not use the point estimate to pass/fail this.** A ±180° test needs an error bar, and the
prior routes were quoted "within 1°" from single whole-engaged Welch estimates with **no error bar
at all** — so an invented tolerance would have decided the verdict on my arbitrary choice. My first
pass did exactly that (a ±2° threshold) and printed "READOUT VOID" off a 4° deviation. Replaced by
a **block-bootstrap CI over 5.12 s windows**:

```
r82 (V99) arg(V)-arg(B') = +179.05 deg [-179.77, +179.76]  18 windows / 18 blocks  -> CI COVERS +-180
r81 (V98) arg(V)-arg(B') = +179.66 deg [-179.88, +179.90]  21 windows / 21 blocks  -> CI COVERS +-180
```

⇒ **R5b reproduces on route 82. The readout is not void.** The whole-engaged +175.92° is the
low-coherence single-Welch estimate; the windowed circular mean is +179.05°.

---

## 5. E1 — PRIMARY. The lever's own null-by-construction control.

`0xC40BC` 600 → 300 differs by exactly **2.00×** below 25 ct (5.31 °/s motor-referred) and by
**1.000×** above 50 ct (10.61 °/s) — so the drive contains its own internal control band.

```
bin deg/s  role                            n   V98 n   V99 b6           95% CI   V98 b6    delta
0-5        LEVER (full 2.00x dose)      1563     894   0.3602 [0.2699, 0.4506]   0.4911  -0.1309  -> MOVED
5-25       LEVER (partial dose)         2523    2469   0.3111 [0.2870, 0.3352]   0.3556  -0.0445  -> MOVED
25-60      CONTROL (dose ratio 1.000)   1185    1781   0.3063 [0.2469, 0.3657]   0.3268  -0.0205     no move
60+        CONTROL (dose ratio 1.000)    708    1447   0.5621 [0.3775, 0.7468]   0.6164  -0.0543     no move
```

CIs use the b6 bit's **own measured correlation time** inside each stratum (global engaged
τ = 0.052 s), not a naive binomial — a binomial SE here would be ~5× too tight.

Taken at face value this is the pre-registered E1 signature: **lever bands moved, control bands did
not.**

### 🛑 But it does not survive its own offset check, and that is the honest headline.

**All four deltas are NEGATIVE** (−0.131, −0.045, −0.021, −0.054). A uniform sign across lever and
control bins is the signature of a **route-wide offset** — a different drive, a different operating
point — sitting underneath any lever effect. The two control bins simply have wider CIs (n = 1185
and 708 against 1563 and 2523), so they fail to clear significance rather than demonstrably not
moving.

The offset-immune statistic is the **LEVER duty / CONTROL duty ratio computed WITHIN each route**,
which cancels any route-wide multiplier exactly. Both arms bootstrapped over their own 5.12 s
engaged blocks (14 blocks each):

| statistic | V99 (r82) | V98 (r81) | verdict |
|---|---|---|---|
| b6(0–5) / b6(25–60) | **1.176** [0.763, 1.816] | **1.503** [1.128, 1.976] | CIs **OVERLAP** |
| b6(5–25) / b6(25–60) | **1.016** [0.717, 1.447] | **1.088** [0.815, 1.380] | CIs **OVERLAP** |
| lever pooled / control pooled | **0.773** [0.531, 1.221] | **0.898** [0.700, 1.174] | CIs **OVERLAP** |

### E1 on a COMMON stratification — the artefact criterion is MET, and the null is LICENSED

`score/v99_r82_matched.py` §D re-derives **both** routes from their own caches on **one** set of edges.
First, a prerequisite: **route 81's four bins reproduce EXACTLY** from its cache — n = 894 / 2469 /
1781 / 1447 and b6 = 0.4911 / 0.3556 / 0.3268 / 0.6164, all four to four decimals. The V98
reference is **measured, not merely quoted**, so the comparison is apples-to-apples.

```
bin      role       V99 n   V99 b6   V98 n   V98 b6    delta    ratio
0-5      LEVER       1563   0.3602     894   0.4911  -0.1308   0.7335
5-25     LEVER       2523   0.3111    2469   0.3556  -0.0445   0.8749
25-60    CONTROL     1185   0.3063    1781   0.3268  -0.0205   0.9374
60+      CONTROL      708   0.5621    1447   0.6164  -0.0543   0.9119

mean V99/V98 duty RATIO:  LEVER 0.8042   CONTROL 0.9247   |   all four deltas share a sign: TRUE
```

🛑 **ALL FOUR BINS MOVED, AND ALL FOUR MOVED DOWN.** `builds/v80_v107/build_v99_tva.py` is unambiguous about what
that means: *"A change in ALL FOUR bins is an operating-point / route artefact, NOT the lever, and
must be reported as such."*

⇒ **E1 READS NULL, and I license the pre-registered sentence VERBATIM:**

> *"Doubling the modelled-Coulomb small-signal gain in the 1-13 deg/s micro regime does not move the
> MODEL-vs-ACTUAL arm balance at any wheel rate, so the friction ramp's KNEE POSITION is not what
> sets that balance while he feels the symptom — and since the reachable friction set is unchanged,
> no larger dose of THIS cell can do it either. The next lever must be outside FUN_0003b8f6's
> friction path."*

**The one residual, stated rather than used to rescue the lever:** the 0–5 °/s ratio (0.7335) sits
apart from the other three (0.8749 / 0.9374 / 0.9119), and that is the predicted full-dose bin. The
lever bins fell 12 % more than the control bins in the ratio. But the offset-immune DiD CIs above
**overlap**, so that separation is not distinguishable from the offset at this exposure. The
pre-registration was written precisely to stop a lever being rescued from an all-bins-moved pattern,
and I am honouring it. **What would separate them is a second route on the same build** — not a
better statistic — and that is the one thing the exposure protocol does not supply.

## 6. E2 — the within-symptom slope. NULL by the pre-registered criterion, and UNDERPOWERED.

Partial Spearman( log(6–9 Hz column-torque band RMS), bit window duty | speed, |wheel rate|,
press ), 1.28 s windows, 5.12 s block-permutation null, 5,000 permutations. The `b6` rung is
byte-identical to the one that produced V98's result.

```
exposure: 86 windows, 12 blocks, 4 episodes   (route 81: 98 windows, 21 blocks)

LOW  6-9 Hz tercile n=29  band RMS  39.1  b6 0.3702  b4 0.4324  b7 0.6562  v 9.40  |rate| 30.9
MID  6-9 Hz tercile n=28  band RMS 292.9  b6 0.3859  b4 0.4314  b7 0.5619  v 8.01  |rate| 15.8
HIGH 6-9 Hz tercile n=29  band RMS 656.8  b6 0.3225  b4 0.4491  b7 0.5595  v 6.38  |rate| 22.9

b6: partial r -0.236   block-perm p 0.1968   null 95% |r| <= 0.343   NULL   [V98 r -0.321]
b4: partial r +0.081   block-perm p 0.6018   null 95% |r| <= 0.282   NULL   [V98 r +0.087]
b7: partial r -0.153   block-perm p 0.3810   null 95% |r| <= 0.323   NULL   [V98 r +0.037]
```

✅ **The two controls stayed NULL**, as required — `b4` reproduced to three decimals (+0.081 vs
+0.087).

🛑 **THE DECISIVE FACT ABOUT E2: route 82's own null width (0.343) is LARGER than the entire gap
between the two competing hypotheses.** "r reproduces −0.321" and "|r| shrank below 0.221" are
**0.10 apart**, and this route cannot resolve 0.34. So:

- By the pre-registered wording — *"a null on E2 — i.e. r reproduces −0.32 within its own null
  width"* — |−0.236 − (−0.321)| = 0.085 < 0.343, so **E2 formally reads NULL.**
- But r = −0.236 is also **not distinguishable from zero** (p = 0.197).
- **E2 therefore cannot discriminate between the two readings, and I am not quoting the licence
  sentence as though it had.**

The cause is exposure, not method: 12 blocks against route 81's 21, from a 121.7 s drive against
181.5 s, with engagement fragmented into 4 episodes of which two are under 11 s.

⊕ The hoped-for first — a within-symptom statistic replicated on a second build — **did not land**.
The sign and rough magnitude carried over (−0.24 vs −0.32), which is encouraging, but that is
BELIEF, not a replication.

## 7. E3 — overall engaged b6 duty

```
b6: tau 0.052 s  n_eff 1161  duty 0.3527  SE 0.0140  95% CI [0.3252, 0.3802]
b4: tau 0.310 s  n_eff  193  duty 0.4484  SE 0.0358  95% CI [0.3783, 0.5185]
b7: tau 0.029 s  n_eff 2060  duty 0.5794  SE 0.0109  95% CI [0.5580, 0.6007]
V98 route 81 reference: 0.4235 [0.363, 0.484]
```

⇒ **CIs OVERLAP, but only just** — in [0.363, 0.380]. Reported with its CI, never as a verdict on
its own, per the pre-registration.

Stratified (all engaged, latch exclusion applied):

```
ENGAGED       n=5979  b6 0.3527   MANUAL       n=6025  b6 0.7391
ENG+override  n=1303  b6 0.4129   MAN+handson  n=2965  b6 0.9852
ENG+handsoff  n=4676  b6 0.3360   MAN+handsoff n=3060  b6 0.5007
```

## 7b. 🛑 THE ENGAGED/MANUAL CONTRAST IS RATE-CONFOUNDED — ON BOTH ROUTES

Those raw engaged/manual numbers **must not be quoted as they stand**, and neither must V98's
headline 0.4235-vs-0.8041. `b6` is strongly rate-dependent, and the two arms are not rate-matched:

```
route 82 (V99)  ENGAGED  0-5:26.1%  5-25:42.2%  25-60:19.8%  60+:11.8%   micro 21.4s ratchet 24.4s macro  7.9s
                MANUAL   0-5:25.2%  5-25:11.5%  25-60:19.2%  60+:44.1%   micro  8.3s ratchet 13.0s macro 29.3s
                -> MANUAL is 3.72x more 60+ deg/s weighted than ENGAGED

route 81 (V98)  ENGAGED  0-5:13.6%  5-25:37.5%  25-60:27.0%  60+:22.0%   micro 14.3s ratchet 33.1s macro 15.8s
                MANUAL   0-5:31.7%  5-25:12.9%  25-60:15.0%  60+:40.4%   micro 18.6s ratchet 20.7s macro 51.2s
                -> MANUAL is 1.84x more 60+ deg/s weighted than ENGAGED
```

Since engaged b6 rises from ~0.31 at low rate to 0.56 at 60+, a macro-heavy manual arm **biases the
contrast in exactly the direction that manufactures it**. `score/v99_r82_matched.py` §C therefore matches
both arms on a **4 |rate| × 6 speed** cell grid, weight = min(n_eng, n_man), cells below 30 frames
in *either* arm dropped, CI by 5.12 s block bootstrap.

| route | raw diff | **matched diff** | 95 % CI | matched exposure surviving |
|---|---|---|---|---|
| **82 (V99)** | −0.3864 | **−0.3372** | [−0.5354, −0.1895] | 14 cells; 96.6 % of engaged, 62.7 % of manual |
| **81 (V98)** | −0.3806 | **−0.2950** | [−0.4099, −0.1727] | 15 cells; 96.0 % of engaged, 83.4 % of manual |

**⇒ THE CONTRAST SURVIVES MATCHING ON BOTH ROUTES.** [EVIDENCE]

- Matching moved route 82's contrast by 13 % and route 81's by **22 %** — so **V98's headline
  overstated the gap by about a fifth**, and the record should carry the matched figure
  (**engaged 0.4543 vs manual 0.7493, diff −0.2950 [−0.4099, −0.1727]**) rather than
  0.4235-vs-0.8041.
- **This is a correction to the MAGNITUDE, not to the finding.** Both CIs exclude zero by a wide
  margin, so *"engagement swells the ACTUAL arm relative to MODEL"* stands on both builds.
- Enough matched exposure survived that dropping the contrast was not necessary — worth saying,
  because the discipline requires dropping it if matching had emptied the cells.
- The two routes' matched CIs **overlap heavily** ⇒ **V99 did not change the engaged/manual gap.**

---

## 8. ⭐ THE OPERATOR'S OWN CLAIM — the audible aspect. NOT pre-registered.

### 8a. Cross-build band ratios, route 82 / route 81, engaged

🛑 `builds/v80_v107/build_v99_tva.py` lists cross-build band ratios as an **UNBUILDABLE ENDPOINT** at this exposure.
Computed because he asked. **Every ratio is printed beside the within-route split-half noise floor
of the same statistic**, per the V97 lesson (a 5.92× ratio against its own 6.98× floor).

```
tq_0x18F_column          r82/r81   block-boot CI    r82 floor p95  r81 floor p95  verdict
  0.5-3                    0.895   [0.38, 2.23]         3.19           4.22       inside noise
  6-9                      1.021   [0.65, 1.47]         4.61           3.07       inside noise
  12-16                    1.020   [0.78, 1.38]         1.52           1.61       inside noise
  15-22                    0.986   [0.55, 1.46]         2.26           1.90       inside noise
  18-22                    1.087   [0.55, 2.01]         2.34           2.27       inside noise
  20-24 (neg. control)     0.884   [0.72, 1.44]         2.69           3.08       inside noise
  26-31                    1.113   [0.84, 1.42]         1.54           1.24       inside noise
```

The same holds for steering angle, the angle-acceleration proxy and CAN 427: **every band, on
every signal, is inside its own within-route split-half noise floor.**

⇒ **"Cannot be distinguished from noise." No cross-build band ratio is headlined.**

🛑 Note on the ZOH: 427 is transmitted at 49.8 Hz, so a ZOH onto the 100 Hz grid images 5–15 Hz onto
35–45 Hz. **35–45 Hz is void as a control band on 427** and was not used; 20–24 Hz is the stated
negative control throughout.

### 8b. The within-drive LKAS-off arm — the preferred comparison

```
tq_0x18F_column       ENG/MAN   block-boot CI    split-half floor p50/p95   verdict
  0.5-3                 2.884   [ 0.52,  8.07]        1.58x / 3.19x        inside noise
  6-9                  10.801   [ 2.22, 45.18]        1.66x / 4.33x        EXCEEDS
  12-16                 3.522   [ 1.12,  8.49]        1.16x / 1.52x        EXCEEDS
  15-22                 4.494   [ 1.44, 13.05]        1.54x / 2.30x        EXCEEDS
  18-22                 5.903   [ 1.08, 17.48]        1.27x / 2.37x        EXCEEDS
  20-24 (neg. control)  6.078   [ 1.46, 15.27]        1.62x / 2.72x        EXCEEDS
  26-31                 3.095   [ 1.52,  5.68]        1.23x / 1.54x        EXCEEDS
```

🛑 **THE NEGATIVE CONTROL BAND MOVED TOO, AND BY AS MUCH AS THE SIGNAL BANDS.** The engaged/manual
excess is **BROADBAND**, not band-selective. That reproduces the standing "vibration requires LKAS
engaged" result and says nothing about V99 versus V98 — **it is a property of engagement, not of
this build.** Reported as such and not headlined as an audible-band finding.

### 8c. ⭐ THE ACOUSTIC CHANNEL — a genuinely new instrument

**The rlog carries a real microphone and this kit has never used it.**  [EVIDENCE — enumerated from
the rlog, not assumed]

```
rawAudioData   1,048-1,196 msgs/segment   16,000 Hz mono int16, 800 samples (50 ms) per message
soundPressure    564-602 msgs/segment     broadband + A-weighted dB
```

A cabin mic cannot hear 8 Hz. The audible signature of a mechanical ratchet is a **6–31 Hz amplitude
modulation of a broadband rasp**, so `decode/extract_r82_audio.py` computes the per-band **envelope** on
the same 100 Hz grid as the CAN rows, and every band statistic above applies to it unchanged.

🛑 **A TRAP THAT WOULD HAVE MANUFACTURED THE ANSWER, and it was caught.** `logMonoTime` is the
*publish* time and jitters ±10 ms about the true 50.01 ms cadence (measured dt p10 41.28 / p50 50.01
/ p90 60.97 ms; 800 samples @ 16 kHz **is** 50.00 ms). Placing each block at `round(t·SR)` punctures
the stream with a 1–4 bin hole every ~8 bins — **a periodic dropout at ~11 Hz, landing inside the
12–16 Hz modulation band under test.** Interpolating those holes would have injected the very line
being measured. Blocks are instead laid **end to end**, with a new run anchored only at a real
dropout (dt > 75 ms). Route 82 has 101 such runs; coverage rose 84.8 % → 89.5 % and the fake
periodicity is gone.

**Within-drive route 82, ENGAGED / LKAS-OFF, envelope modulation (fl = split-half floor p95):**

```
              6-9            12-16          18-22          20-24          26-31
a20_100     1.16 noise     0.51 EXCEEDS   1.08 noise     1.17 noise     0.45 EXCEEDS
a100_300    1.03 noise     0.69 noise     0.83 noise     0.79 noise     0.32 EXCEEDS
a300_800    0.93 noise     1.56 noise     1.75 EXCEEDS   1.99 EXCEEDS   1.78 EXCEEDS
a800_2k     6.02 EXCEEDS  10.14 EXCEEDS   4.83 EXCEEDS   4.67 EXCEEDS   3.59 EXCEEDS
a2k_4k      1.35 noise     1.46 EXCEEDS   1.79 EXCEEDS   2.10 EXCEEDS   1.73 EXCEEDS
a4k_7k      5.12 EXCEEDS   4.61 EXCEEDS   3.65 EXCEEDS   3.23 EXCEEDS   1.42 noise
```

**Cross-build r82 / r81, engaged — EVERY band on EVERY carrier is inside its own floor:**

```
a20_100    6-9 0.93(fl 1.45)  12-16 0.90(fl 1.56)  18-22 0.96(fl 1.43)  20-24 1.03  26-31 0.98
a100_300   6-9 1.34(fl 1.84)  12-16 1.30(fl 2.53)  18-22 1.35(fl 1.74)  20-24 1.18  26-31 1.84
a300_800   6-9 1.33(fl 2.36)  12-16 1.04(fl 1.69)  18-22 1.24(fl 1.67)  20-24 1.27  26-31 0.91
a800_2k    6-9 0.92(fl 1.91)  12-16 0.98(fl 1.81)  18-22 1.00(fl 1.64)  20-24 1.05  26-31 0.89
a2k_4k     6-9 1.86(fl 6.59)  12-16 1.91(fl 6.21)  18-22 2.09(fl 4.58)  20-24 1.60  26-31 1.62
a4k_7k     6-9 0.77(fl 2.87)  12-16 1.20(fl 2.21)  18-22 1.26(fl 2.30)  20-24 1.11  26-31 0.84
```

Raw levels (envelope median): engaged r82/r81 is 0.84–1.19 across all six carriers;
`soundPressureWeightedDb` p50 24.7 (r82) vs 24.2 (r81).

### 🛑 The instrument's own positive controls — and the second one FAILS

A cross-build null on a channel with no demonstrated positive control is uninterpretable (V64, V68,
V92). Two controls were run, both within route 82.

**(a) LIVENESS — does the envelope track vehicle speed? Road noise must.** ✅ PASSES.

```
a20_100 -0.091   a100_300 +0.546   a300_800 +0.395   a800_2k +0.459   a2k_4k +0.170   a4k_7k +0.063
```

**(b) COUPLING TO THE MECHANICAL SYMPTOM — does the audible modulation co-vary with the 6–9 Hz
column-torque band during engagement?** 🛑 **FAILS.** Partial Spearman | speed, |rate|, press;
5.12 s block-permutation null; 43 engaged windows with valid audio, 14 blocks.

```
            6-9              12-16            18-22
a20_100   r+0.006 p0.982   r-0.144 p0.565   r-0.132 p0.634
a100_300  r-0.074 p0.752   r-0.354 p0.142   r-0.203 p0.469
a300_800  r-0.360 p0.089   r-0.434 p0.031*  r-0.295 p0.218
a800_2k   r-0.236 p0.303   r-0.129 p0.610   r-0.166 p0.482
a2k_4k    r-0.031 p0.908   r+0.157 p0.505   r+0.100 p0.674
a4k_7k    r+0.075 p0.768   r-0.010 p0.969   r+0.119 p0.572
```

**One nominal hit in 18 tests at α = 0.05 is exactly chance (expected 0.9), and its sign is
NEGATIVE — more audible modulation when there is LESS 6–9 Hz column torque.**

⇒ **The microphone is LIVE but is NOT demonstrated to be coupled to the mechanical grinding.**
Therefore the cross-build acoustic null **cannot confirm or refute** the operator's audible claim,
and I am not using it to do either. The large engaged/LKAS-off acoustic contrast (a800_2k 12–16 Hz
= 10.14× against a 1.56× floor) is real and is the instrument's demonstrated dynamic range, but
attributing it to *the grinding* rather than to some other consequence of engagement is **BELIEF,
not EVIDENCE**, precisely because control (b) failed.

---

## 9. WHAT THIS LICENSES

**About the friction path (`FUN_0003b8f6`: K0 `0xC4080`, K1 `0xC40D2`, `0xC40BC`, `0xC40D0`):
E1 reads NULL on its own pre-registered artefact criterion, and the null sentence is LICENSED
VERBATIM** (§5, common stratification: all four bins moved, all four down). That closes the
friction ramp's **knee position** as a lever on the MODEL-vs-ACTUAL balance, and — because the
reachable set of the friction term is bit-identical between V98 and V99 — closes **any larger dose
of `0xC40BC`** with it. *The next lever must be outside `FUN_0003b8f6`'s friction path.*

Two limits on that closure, stated rather than buried. **(i)** The 0–5 °/s bin fell further than
the other three (ratio 0.7335 against 0.8749 / 0.9374 / 0.9119) and that is the predicted full-dose
bin; the offset-immune DiD CIs overlap, so it is not separable from the route offset here. The
closure rests on the pre-registered rule, not on a demonstration that the lever did nothing.
**(ii)** E2 could have arbitrated it and could not: its null width (0.343) exceeds the entire 0.10
gap between the hypotheses it was built to separate. The binding constraint on both is **59.8 s of
engaged exposure in 4 fragmented episodes**, giving 12–14 resampling blocks where V98 had 21.
**This is an EXPOSURE failure, not an analysis failure**, and it is the third build running (V89,
V97, V99) whose primary endpoint died to it.

**About `0xC63AC`'s revert:** no endpoint in this build was capable of scoring it, and none is
claimed. It was cut as base hygiene — a return to Honda's own 102, restoring the bit-identical
α = 0.099609375 match between the MODEL arm's `0xC40D2`-side EMA and the ACTUAL arm's accumulator
pole that V97 broke. **The only evidence bearing on it is negative and weak:** the drive was
fault-free, R5b reproduced, and none of the four control statistics (b4, b7, POS-3, the 20–24 Hz
band) shifted. That is consistent with "the revert introduced nothing", which is all a revert should
do. **No improvement is claimed for it, and none is measurable here.**

**About the operator's report — this is the primary evidence in the drive, and no pre-registered
endpoint covers it.** He said *"I think it helped with the audible aspect of the grinding, though
I'm not sure."* That is a hedge, not a cure.

🛑 **THE PLAIN ANSWER: WE WOULD NOT BE ABLE TO TELL.** At this exposure, on this drive, with these
instruments, there is no measurement that could have distinguished "the audible grinding got
quieter" from "nothing changed". Specifically:

- Every cross-build audible band ratio on column torque, steering angle, the angle-acceleration
  proxy and CAN 427 is **inside its own within-route split-half noise floor** (§8a).
- Every cross-build acoustic band ratio, on all six carriers, is likewise **inside its floor** (§8c).
- The one channel that *is* physically right for an audible claim — the microphone — is **live**
  (speed control passes, ρ up to +0.55) but **fails its coupling control** to the mechanical band
  (1 nominal hit in 18 tests = chance, and wrong-signed). Per the kit's own design law a null on a
  channel without a positive control is uninterpretable, so it cannot be used either way.
- The one large audible-band effect that *is* resolvable — engaged vs LKAS-off — is **broadband**,
  moving the 20–24 Hz negative control as much as the signal bands, so it measures **engagement**,
  not this build.

That is a legitimate answer and it is better than a number that would have to be walked back. It is
also an indictment of the instrument design, not of his report: **his claim was about the audible
aspect and nothing in the pre-registration was built to score it.** The microphone is now extracted
and cached for both routes, so the *next* build can pre-register an acoustic endpoint and a
coupling control for it.

**Nothing here is called fixed. He has not called anything fixed.**

## 10. METHOD NOTES AND CORRECTIONS MADE DURING THIS SCORE

1. **raw14 off-by-one** — the extractor's convention was verified from the cache before any
   statistic: `t == raw14_t[1:]`, `probe == raw14_b4[1:]`, and `probe == raw14_b4[row2raw14]` all
   hold. Every bit series is `raw14_b4[row2raw14]` with an assertion against `probe` at load. The
   unsafe pair `(t, raw14_b4)` — worth 28° at 7.79 Hz — is never formed.
2. **The V96/V97 bit-mask bug** (§4) — caught because three routes returned NaN phases.
3. **The invented R5b tolerance** (§4) — replaced with a bootstrap CI.
4. **The audio timestamp trap** (§8c) — would have manufactured an ~11 Hz line in the band under
   test.
5. **Resampling unit** — 5.12 s contiguous blocks, not windows. The kit's mandated episode
   bootstrap is impossible here (4 engaged episodes), and the block unit is weaker; it is labelled
   as such everywhere it is used, and the split-half null uses the same unit so floor and contrast
   are like-for-like.
6. **1.28 s windows, not 5.12 s** — the symptom regime is engaged + hands-on + override, and
   override runs are short (corpus median 0.02 s, p90 0.55 s).
7. **The `steeringPressed` mask points away from the symptom.** Of route 82's 86 engaged windows,
   only **4** survive as pure hands-on (`|STEER_TORQUE_SENSOR| > 1200` on every frame of the
   window) — the rest straddle the threshold, and those are exactly where the oscillation is. The
   unmasked arm is the one read; `press` is carried as a covariate in E2 instead.

---

# 11. ⭐ V100 PRE-FLIGHT POWER GATE — run BEFORE the cut

🛑 The standing gate in `CLAUDE.md`: *"Before cutting, write the sentence a null will license. If
the honest answer is 'we would not be able to tell,' the build is not ready — fix the instrument
first."* V97 flew uninterpretable because nobody ran that gate **quantitatively**. Run here against
**route-82-class exposure, assumed as the ceiling**: 59.79 s engaged, 5,979 frames, 4 fragmented
episodes, 12–14 blocks. Script: `rlog-tools/score/v100_power_gate.py`, readout
`analysis-2020accord/sessions/v99/v100_power_gate.json`.

## τ prior for a threshold rung — MEASURED, not guessed

A real threshold rung `|gp-0x6b70| >= thr` is **synthesised from CAN 427** on routes 80/81/82 and its
correlation time measured. It is the closest empirical analogue to RUNG A obtainable without flying
anything.

```
route   thr    duty   tau s   n_eff        route   thr    duty   tau s   n_eff
r82    1024  0.3250   0.302     198        r81    1024  0.4559   0.245     269
r82    2048  0.1442   0.341     175        r81    2048  0.2414   0.390     169
r82    2560  0.0632   0.579     103        r81    2560  0.1268   0.603     109
r80    1024  0.3281   0.105     164        r80    2560  0.0320   0.065     263
```

⇒ **τ = 0.065 – 0.603 s for a threshold rung**, against 0.029–0.052 s for the flown *sign* rungs.
**A threshold rung is 2–20× stickier than a sign rung and therefore costs that much effective
sample.** That is a general design fact worth carrying: sign bits are cheap, threshold bits are not.

## Q1 — CI half-width for a duty endpoint

`n_eff = T/tau`, half-width `= 1.96*sqrt(p(1-p)/n_eff)`, T = 59.79 s.

```
  tau s   n_eff    p=0.05   p=0.20   p=0.50   p=0.80   p=0.95
  0.029    2062    0.0094   0.0173   0.0216   0.0173   0.0094
  0.052    1150    0.0126   0.0231   0.0289   0.0231   0.0126
  0.100     598    0.0175   0.0321   0.0401   0.0321   0.0175
  0.200     299    0.0247   0.0453   0.0567   0.0453   0.0247
  0.310     193    0.0308   0.0565   0.0706   0.0565   0.0308
  0.500     120    0.0391   0.0717   0.0896   0.0717   0.0391
  1.000      60    0.0552   0.1014   0.1267   0.1014   0.0552
```

⭐ **EXPECTED CI ON `d_clamp`: half-width ±0.032 to ±0.098** at the worst case p = 0.50, over the
measured τ range; ±0.020 to ±0.059 out at p = 0.10 / 0.90.

## Q2 — the resolution floor

🛑 The normal approximation fails at the rails. Near zero the right tool is the **rule of three on
effective samples**: zero events in `n_eff` gives a 95 % upper bound of `3/n_eff`. A duty is
distinguishable from 0 only once it delivers **≥ 3 independent clamp episodes**.

```
  tau s   n_eff   min d vs 0   max d vs 1   = seconds clamped
  0.029    2062       0.0015       0.9985         0.09
  0.052    1150       0.0026       0.9974         0.16
  0.100     598       0.0050       0.9950         0.30
  0.310     193       0.0156       0.9844         0.93
  0.603      99       0.0303       0.9697         1.81
```

⭐ **CONSERVATIVE RESOLVABLE WINDOW: `d_clamp` in [0.030, 0.970].** Any duty between ~3 % and ~97 %
reads as different from **both** rails. Single-frame floor 1/5,979 = 0.000167. Empirical precedent
that a true zero is measurable: route 82's b3 duty **0.0000 with 0 transitions** over 12,004 frames,
and V98's b5 duty 0.0022.

## Q3 — does a duty endpoint survive? **YES, CONDITIONALLY — and the condition is the whole point**

🛑 **E1 WAS A DUTY ENDPOINT AND IT DIED.** "Duties are cheap" is not automatically true. What killed
E1 was not that it was a duty — it was that it was a **cross-build duty DIFFERENCE**, exposed to a
route-wide offset that moved all four bins together.

```
bin      delta      own half-width   |delta|/hw
0-5      -0.1308        +-0.0904        1.45
5-25     -0.0445        +-0.0241        1.85
25-60    -0.0205        +-0.0594        0.35   <- effect below its own error bar
60+      -0.0543        +-0.1847        0.29   <- effect below its own error bar
```

In **3 of 4 bins the cross-build effect was at or below its own half-width**. A cross-build duty
delta of ~0.05 is simply not resolvable at this exposure.

⭐ **RUNG A differs in KIND, not degree.** It asks a **within-route, absolute, structural** question
— *"is the PID reference pinned?"* — decided against a threshold far from the noise, with **no
reference to any previous build**. Its decision boundary is ~0.5 wide, not ~0.05:

- at τ = 0.065 s (half-width ±0.032): a 0.20 / 0.80 call carries **9.3 σ** of margin
- at τ = 0.603 s (half-width ±0.098): a 0.20 / 0.80 call carries **3.0 σ** of margin

🛑 **THE GATE FOR V100: if any endpoint's sentence contains "compared to V99", IT FAILS THIS POWER
GATE.** Write every endpoint as a single-drive absolute.

## Q4 — minimum contiguous exposure to resolve E2's 0.10 gap: **UNBUILDABLE**

Empirical block-permutation scaling `null95 = k/sqrt(n_blocks)` from the two measured points:
12 blocks → 0.343 (k = 1.188) · 21 blocks → 0.221 (k = 1.013). Separating r = −0.32 from −0.22 at
95 % confidence and 80 % power needs |gap| ≥ 2.8·SE ⇒ SE ≤ 0.0357 ⇒ null95 ≤ 0.0700.

```
conservative k=1.188 -> 288 blocks -> 1,475 s = 24.6 min contiguous engaged
optimistic   k=1.013 -> 209 blocks -> 1,072 s = 17.9 min contiguous engaged
textbook SE(r)=(1-r^2)/sqrt(n-1) -> 675 independent units -> 58 min
```

⭐ **ANSWER FOR THE DRIVE PROTOCOL: one continuous episode of 25–58 minutes.**

🛑 The operator stops within 15–30 s of feeling the symptom, and the **best engaged exposure ever
recorded is 65.9 s** (route 81). **That is 16–50× short.**

⇒ **THE E2 ENDPOINT CLASS — DISCRIMINATING TWO CORRELATION VALUES ~0.1 APART — IS UNBUILDABLE AT
THIS EXPOSURE AND MUST NOT BE PROPOSED AGAIN.** The conclusion is robust to the method: both the
empirical scaling and the textbook formula land one to two orders of magnitude beyond a symptomatic
drive.

⊕ What E2-class statistics **can** still do at 12 blocks: detect **|r| ≥ ~0.34 against zero**. Usable
for large effects only, never for discriminating two moderate ones.

## Q5 — can `d_clamp` be bounded from data we already have?

`gp-0x6ad6` has never been on the wire, but `gp-0x6b70` **is** — CAN 427 — and it is one of the terms
summed into it. Clamp threshold `0xC6200` = 8192.

```
route   n_eng     p50      p90      p99      MAX   MAX/8192   frac>=8192
r82      5979   537.6   2380.8   2956.8   3008.0     0.367      0.0000%
r81      6591   883.2   2611.2   2892.8   3161.6     0.386      0.0000%
r80      1719   601.6   2073.6   2624.0   2675.2     0.327      0.0000%
```

⭐ **[EVIDENCE] Over 14,289 engaged frames on three routes, `|gp-0x6b70|` never exceeds 3,162 counts
= 38.6 % of the clamp threshold**, and 427 saturation is 0.000 %, so that is a real distribution tail
and not a measurement ceiling.

**What this does NOT give:** `gp-0x6ad6` is a sum whose other terms (`gp-0x6b4a` ±25600, `gp-0x6b60`
±15360, five more at ±10240) have a combined bound of ~100,352 — **12× the threshold** — and they are
unobserved and may add or cancel. ⇒ 🛑 **NO NUMERICAL BOUND ON `d_clamp` IS DERIVABLE. `d_clamp` in
[0, 1] stands.**

⭐ **What it DOES give, and it changes the build's expected value:** `gp-0x6b70` can supply at most
38.6 % of the threshold, so it **cannot rail `gp-0x6ad6` on its own** — the other six terms must
supply at least **5,030 counts (61.4 %)** of any rail that occurs.

⇒ **If `d_clamp` comes back HIGH, the saturation is driven by terms the entire V89→V99 arc never
touched**, and "every lever was discarded by a saturation" gains a mechanism. **If it comes back LOW,
that hypothesis dies** and the levers were delivered, not discarded. **Either way RUNG A is
decisive** — which is exactly what a build should be.

⊕ **The positive control is pre-computable.** `|gp-0x6ad6| >= |gp-0x6b70|` has a *predicted* duty,
because `gp-0x6b70`'s distribution is measured above — so a wildly off value indicts the instrument
rather than the car. That is the property V96's over-ranged channel lacked, and it is a comparator,
which the kit's own design law notes is immune to under- and over-ranging by construction.

## Verdict on the proposed endpoints

| endpoint | power verdict |
|---|---|
| **RUNG A** `d_clamp` as a within-route absolute | ✅ **PASSES** — 3.0–9.3 σ on a 0.20/0.80 call; resolvable window [0.030, 0.970] |
| **RUNG A** as a cross-build delta vs V99 | 🛑 **FAILS** — inherits E1's exact failure mode |
| **Positive control** `abs(gp-0x6ad6) >= abs(gp-0x6b70)` | ✅ **PASSES** — same duty arithmetic, and its expected value is pre-computable from 427 |
| **Second rung** on the ±10240 error clamp at `0x3a7d0` | ✅ **PASSES** on the same arithmetic, provided it is also read as a single-drive absolute |
| **Any E2-class partial correlation** | 🛑 **FAILS** — needs 25–58 min contiguous; do not propose again |

---

# 12. THE 427 SIGN DEFECT — found by `tracer-c63ae`, fixed here

## The defect
`score/v99_r82_score.py` built its 427 signal **rectified**:
```python
d["mt427"] = d["mt_row"].astype(float) * (64.0 / 5.0)          # :672  -- WRONG
d81["mt427"] = d81["mt_row"].astype(float) * (64.0 / 5.0)      # :718  -- WRONG
```
427 carries only the **magnitude** of `gp-0x6b70`; the **sign is byte4 b7**, which this same file
computes at `:118` as `d["sign_6b70"]` and applies correctly everywhere else. Rectifying a signed
oscillation folds every negative half-cycle up — it doubles the apparent frequency and moves energy
from *f* to 2*f*. Inherited from `score/v98_r81_score.py:541`.

**Fixed** on both lines: `... * np.where(d["sign_6b70"], -1.0, 1.0)`.

⊕ **`decode/extract_r82.py` is CLEAN** — checked. It never builds a signed 427 series; it stores the raw
wire magnitude in the cache (correct, that is what the wire carries) and documents the sign bit's
location in its header. The defect was confined to the two consumer lines.

## Corrected numbers, and the effect is large
Within-route ENG / LKAS-OFF on the 427 row, standardised ratio:
```
band     rectified   ->   SIGNED
0.5-3      2.616          3.121
6-9       10.050         19.238     <- 1.91x
12-16     13.177         10.811
15-22      9.810          8.743
18-22      8.503          7.779
20-24      9.796          8.991
26-31      9.825          9.713
```
Band-RMS medians move in both directions, exactly as folding *f* → 2*f* predicts: engaged 12–16 Hz
falls 82.69 → 44.63 while 26–31 Hz rises 45.65 → 54.65.

## 🛑 DOES THE PUBLISHED AUDIBLE VERDICT CHANGE? **NO — and it is STRENGTHENED.**
The cross-build row that scores the operator's report:
```
mt427_gp6b70   (r82 win 86 / r81 win 98)
band     r82/r81   block-boot CI   r82 floor p95  r81 floor p95   verdict
0.5-3     0.835    [0.45, 1.52]        3.04           4.01        inside noise
6-9       0.987    [0.64, 1.45]        3.85           2.72        inside noise
12-16     0.914    [0.72, 1.30]        1.41           1.61        inside noise
15-22     1.018    [0.57, 1.43]        1.79           1.96        inside noise
18-22     1.143    [0.52, 1.84]        1.85           1.89        inside noise
20-24     1.211    [0.71, 1.61]        1.89           1.79        inside noise
26-31     0.942    [0.72, 1.34]        2.07           2.55        inside noise
```
The 6–9 Hz cross-build ratio goes **0.868 → 0.987**, i.e. from "13 % apparent improvement" to
essentially **1.000**. It was already inside its own floor (3.85 / 2.72) and it is now much further
inside. **Every band remains inside its floor. "Cannot be distinguished from noise" holds, and the
correction removes an artefact that pointed the wrong way.** [EVIDENCE]

⚠ The verdict was protected because every ratio was pre-screened against a within-route split-half
floor. That is the discipline earning its keep — but it is luck that the artefact was small relative
to a floor of 3.85×, not design. **A rectified channel could have produced a headline.**

## ⭐ THE PRICE TAG — and it makes V100's `b7` mandatory
Omitting the sign on this lane costs a **measured 1.9× on a 6–9 Hz standardised ratio**, and up to
**5.5×** on the raw within-route contrast. That is the kit's design law — *"every probe that DECIDED
something was a SIGN BIT PAIRED WITH A MAGNITUDE CHANNEL"* — with a number attached, replicated on
two routes and two builds. **V100's `b7` is not stylistic. A magnitude channel without its sign bit
is a broken instrument, and the breakage is invisible unless something is compared against a floor.**

⊕ **Scope is bounded and it is NOT the `raw14` class.** Six earlier scorers (`v87_probe_6b98`,
`decode_v90_probe`, `v92_boost_lane_and_rez`, `v95_lane_decomposition`, `v96_probe_vs_ratchet`,
`v97_r80_vs_v96`) handled the sign correctly — `v87` made rectification an explicit
*"RECTIFICATION TRANSPARENCY"* measurement. This is a regression introduced at V98 and inherited by
V99, with a clean before/after. ✅ `Re(Z)` is not exposed: it is built from `0x18F` bytes 0–1 and
2–3, never 427.

🛑 **A CORRECTION TO THE ANCHOR, caused by the same defect.** The free anchor
`RMS₆₋₉(gp-0x6b70) / RMS₆₋₉(column torque)` was quoted as **1.190 / 1.178, "1.0 % apart"** — but
those were computed on the **rectified** channel. Recomputed with the sign applied:

```
r82: 1.1725  95% CI [1.0709, 1.2709]   rel s.e. 4.37 %
r81: 1.0825  95% CI [0.9089, 1.2106]   rel s.e. 7.73 %
```
⇒ **1.173 vs 1.083 is 8 % apart, not 1 %.** The CIs still overlap and the anchor is still usable,
but **the rectification defect inflated its apparent stability by ~8×.** Use **1.13 ± 0.09**, not
1.18 ± 0.01.

---

# 13. V100 POWER GATE, PART 2 — the two endpoints §11 did not cover

§11 already answers items 1, 2, 3 and the "bound from existing data" question under the label
`d_clamp`; **`d(b5)` is the same quantity** (`|gp-0x6ad6| ≥ 8192`) and those answers carry over
unchanged. This section covers the two endpoints that are new in the V100 spec.

## Item 4 — `d(b6 | b5=0)` is a CONDITIONAL duty. **Quantified, and it has a hazard.**

`n_eff` for the conditional is `T·(1 − d(b5))/τ`. Half-widths at p = 0.5:

```
d(b5):            0.00    0.50    0.80    0.90    0.95    0.99
conditioning s:  59.79   29.90   11.96    5.98    2.99    0.60

tau=0.065  hw:   0.032   0.046   0.072   0.102   0.144   0.323
tau=0.300  hw:   0.069   0.098   0.155   0.219   0.310   0.693
tau=0.603  hw:   0.098   0.139   0.219   0.310   0.438   0.980
```

**Where it stops resolving.** For a 0.20 / 0.80 structural call (0.30 from the midpoint) at 2.8 σ
(95 % confidence, 80 % power) we need hw ≤ 0.107:

| τ | conditional dies above |
|---|---|
| 0.065 s (best measured) | **d(b5) > 0.909** |
| 0.300 s (central) | **d(b5) > 0.578** |
| 0.603 s (worst measured) | **d(b5) > 0.153** |

At a laxer 2 σ bar (hw ≤ 0.15): d(b5) > 0.953 / 0.784 / 0.566.

⭐ **THE HAZARD, AND IT IS STRUCTURAL: THE TWO ENDPOINTS ARE ANTI-CORRELATED IN POWER.** The
scenario that makes `d(b5)` most interesting — `b5` near 1, i.e. *"every lever since V89 was
discarded by a saturation"* — is **exactly** the scenario that empties `b6`'s conditioning set. If
`d(b5)` comes back at 0.9, the conditional has 5.98 s of conditioning exposure and a half-width of
±0.10 to ±0.31. **The build cannot confirm its own headline and characterise the error clamp on the
same drive.**

✅ **MITIGATION, and it costs nothing because `b6` is already a free-running rung.** Report the
**JOINT 2×2 (b6, b5) table**, exactly as V98 did for its own comparator pair. The **marginal**
`d(b6)` is then always available at the full n = 5,979 / `n_eff` = 99–920 regardless of `d(b5)`, and
the joint table exposes the dependence structure directly. **The conditioning must be a post-hoc
slice, never a hardware gate.** Pre-register the marginal as the reportable quantity and the
conditional as the bonus, not the other way round.

## Item 5 — φ's exposure requirement. **The stationary formula is wrong by 3–8×.**

`tracer-c63ae`'s figures (90 independent samples in a 3 Hz band from 15 s ⇒ 7.5 % rel s.e.; 30 s ⇒
5.3 %) are arithmetically right — `n = 2·B·T`, rel s.e. `= 1/√(2n)` — and at route-82 exposure that
formula predicts **3.7 %**. 🛑 **It assumes STATIONARITY over the whole engaged span, and route 82 is
not remotely stationary:** 4 fragmented episodes at 5.1 / 6.9 / 18.9 / 16.7 km/h and wheel rates
19–21 °/s. Measured directly, by block bootstrap over the same 5.12 s blocks used everywhere else:

```
                                   measured      block-boot 95% CI        rel s.e.
r82  RMS_6-9(gp-0x6b70)   signed    231.2 ct     [141.6, 359.0]            24.12 %
r81  RMS_6-9(gp-0x6b70)   signed    225.1 ct     [122.6, 375.6]            29.36 %
      window spread p90/p10:  r82 23.7x   r81 46.0x
```

⇒ **The real relative s.e. on an ABSOLUTE 6–9 Hz RMS at route-82-class exposure is 24–29 %, not
3.7 %.** Episode-to-episode variability dominates spectral-estimation variance by 6–8×. Any exposure
calculation for this car that uses `1/√(2n)` will be optimistic by that factor.

### Is the R = 387 ct boundary resolvable? **It depends entirely on whether φ is framed as a ratio.**

**If the decision is on an ABSOLUTE count (R vs 387 ct)** — rel s.e. 24–29 %. For the boundary to be
excluded at 2.8 σ we need `|R − 387| ≥ 2.8·0.24·R`, i.e.

> **resolvable only if R ≤ 231 ct or R ≥ 1,180 ct. Between those it decides nothing.**

The measured `RMS₆₋₉(gp-0x6b70)` is **231.2 ct (r82) and 225.1 ct (r81)** — sitting *exactly* on the
lower edge. At r82's s.e. it clears by 0.1 %; **at r81's s.e. (29.4 %) the threshold is 212 ct and
225.1 FAILS it by 6 %.** 🛑 **As an absolute-count endpoint, φ is a coin flip and does NOT pass its
power gate.**

**If the decision is on a RATIO** — and φ *is* a ratio, `0.2565·N/D` — most of the episode variance
**cancels**, because numerator and denominator scale together with episode intensity. Measured:

```
ratio RMS_6-9(gp-0x6b70) / RMS_6-9(column torque)
r82: 1.1725  [1.0709, 1.2709]   rel s.e. 4.37 %     <- 5.5x better than the absolute
r81: 1.0825  [0.9089, 1.2106]   rel s.e. 7.73 %     <- 3.8x better
```

⇒ **A ratio endpoint needs the true value to sit ≥ 2.8 × 7.7 % ≈ 22 % away from its boundary.**
That is a wide, comfortable gate for any boundary the value is not sitting on top of.

### ⭐ THE RECOMMENDATION, AND IT IS THE WHOLE POINT OF RUNNING THE GATE EARLY
**Define φ's endpoint as a RATIO against a dimensionless boundary — never as an absolute count
against 387 ct.** The ratio form is **3.8–5.5× more precise on identical data**, for free, because
episode intensity cancels. The absolute form throws that factor away and lands on a coin flip that
passes on one route's noise and fails on the other's.

## Endpoint verdicts, consolidated

| endpoint | verdict |
|---|---|
| **`d(b5)`** within-route absolute (§11 `d_clamp`) | ✅ **PASSES** — hw ±0.032…±0.098; 3.0–9.3 σ on a 0.20/0.80 call; resolvable window [0.030, 0.970] |
| **`d(b5)`** as a cross-build delta vs V99 | 🛑 **FAILS** — inherits E1's exact failure mode |
| **`d(b6)` marginal** | ✅ **PASSES** at full n, independent of `d(b5)` |
| **`d(b6 \| b5=0)` conditional** | ⚠ **CONDITIONAL PASS** — dies above `d(b5)` ≈ 0.58 (central τ), as early as 0.15 at worst-case τ. **Anti-correlated with the headline endpoint.** Pre-register the marginal + joint 2×2 instead. |
| **φ as a RATIO** | ✅ **PASSES** — rel s.e. 4.4–7.7 %, needs ~22 % separation from its boundary |
| **φ as an ABSOLUTE count vs R = 387 ct** | 🛑 **FAILS** — rel s.e. 24–29 %; resolvable only if R ≤ 231 or ≥ 1,180 ct, and the measured value sits exactly on the edge |
| **Any E2-class partial correlation** | 🛑 **FAILS** — needs 25–58 min contiguous engaged |
