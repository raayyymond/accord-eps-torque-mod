# THE SHELF — what is built, what to flash, what it changes

**Updated 2026-08-29.** **⚠ FLY V217 FIRST.** 19 payload bytes from your car, every one a lever. Two rung-2 arms are ready behind it: **V218** (deeper ratchet dose) and **V219** (10× authority). Fly whichever the V217 drive points at.

🛑 **V207 was built and RETIRED without flying.** It asked whether the delivery chain zero-rejects
the merged command; the answer is provably no — the compensation is capped at 2560 by a 3-knot table,
the governor at 4762, and 7322 sits 870 counts under the ±8192 window. **A drive was saved by reading
a table.** Everything else from this arc is renamed
`SUPERSEDED-DO-NOT-FLASH-GATE2-…` and must not be sent.

🛑 **Nothing here has been flashed and no CAN or UDS message has been sent.** Flashing requires you to
name the file and the bus, and they will be read back to you first.

---

## 🛑 CORRECTION — I had the friction direction BACKWARDS

An earlier version of this file said the shelf’s low friction setting *“runs in the direction you have asked for”*. **That was wrong.** The polarity is verified nine links deep (`accord-friction-polarity-*`):

> **MORE modelled Coulomb friction ⇒ MORE assist ⇒ LIGHTER wheel. It does not fight LKAS.**

Friction is *subtracted from the plant model*, which lowers `gp-0x6ad6` — a torque-tracking **reference**, not a motor torque — so the loop holds your felt torque at a **lower** target. So the shelf’s 0.10× setting made the wheel ~10× **heavier** in that term and **removed** LKAS authority, fighting the 8× gain step in the same build.

---

## 📐 V219 — RUNG 2 of the AUTHORITY ladder (8× → 10×). Fly V217 first.

```
39990-TVA,A160-V219-V217BASE-GAIN10X-CLAMPS4608-AUTHORITY.RUNG2-0x13000-0x100000.rwd
  image 13c1d33b3ad9eff526283b7465e3b85b18084056479588ba2741537b25d10d33
```

🛑 **This corrects the record.** V211 says the EME wall *"structurally caps this lever below 10×"*. The two gates it actually asserts permit **10× with real margin**:

```
  mult  0xC6CD0  lane max  clamp window   V219 picks 4608
    8     7128     3341    [3342, 5119]   (V217 uses 4096)
   10     8910     4176    [4177, 5119]   432 above the lane, 512 below the wall
   12    10692     5011    [5012, 5119]   a 108-count squeeze -- NOT taken
```

**Priced on the record’s own exponents** (vibration ~ m^1.74, authority ~ m^0.88) against the notch’s measured 3.59× at 22–26 Hz, relative to your car at 6×:

```
    8x   authority +28.9 %   vibration 1.650x   NET 0.459x  quieter   V217
   10x   authority +56.0 %   vibration 2.432x   NET 0.677x  quieter   V219
```

⚠ I had been quoting authority as **linear** (+33 % at 8×). It is **m^0.88**, so 8× buys **+28.9 %**, not +33 %. Corrected here.

⚠ **Above 29.5 Hz the notch gives nothing back**, so 10× raises loop gain there **2.43× vs your car** against 8×’s 1.65× — a bigger *unopposed* raise. That is why rung 1 flies first, and why the 30–49 Hz band in `score_drive.py` matters on the V217 drive.

---

## 📐 V218 — RUNG 2 of the ratchet dose ladder. Fly V217 first.

```
39990-TVA,A160-V218-V217BASE-C63AE.512.TO.256-RATCHET.RUNG2-0x13000-0x100000.rwd
  image f73aee347d67c10e0a50431d01143407bdee180e792022e2002eb8451c10b691
```

V218 = V217 with `0xC63AE` **512 → 256**. Priced from the real curve (`assist_map_mirror`, input-scaled describing function — reproduces the recorded values):

```
  0xC63AE   small-amp loop gain   |gp-0x6b70| cost   small-signal gain
    1024          1.000x               1.000x          2.67 - 3.77x     Honda
     512          0.500x               0.500x          1.33 - 1.89x     V217, rung 1
     256          0.250x               0.250x          0.67 - 0.94x     V218, rung 2
```

**The trade is exactly 1:1 at small amplitude, with no knee** — halving the cal halves the ratchet loop gain and the assist term in lockstep. So **no dose is analytically preferred**; it is a pure preference, and the drive decides it.

⚠ **256 crosses a qualitative boundary:** small-signal gain falls **below unity** at every speed, so the observer lane *attenuates* near the origin instead of amplifying. 512 stays above unity. That is why rung 1 flies first.

**How to read the ladder:** V217 moves the ratchet but not enough → fly V218. V217 costs too much assist → the other direction (768) is the follow-up. Either way the two builds together are a **dose-response**, which is this kit’s strongest evidence form.

---

## ⭐ V217 — FLASH THIS ONE. The damper fix, complete end to end.

```
39990-TVA,A160-V217-V216BASE-INERTIA.LANE.WEIGHT.TO.FLOWN.V108-0x13000-0x100000.rwd
  image f89ea01f405d513985ce51c47f6796e1ea77f600fab3d9f7817cd79907a1967b
  .rwd  941d82bf2dc556551dc9615bdd01d5e5e2d4fca7d8064578b5afb4bc969dcd54
```

**What V216 still got wrong.** V214/V215 put the inertia *row* back to your car — but `0xC63A6` is that lane’s **weight** in the six-lane plant-model sum:

```
SUM = gp-0x6b4e*0xC63A8 + gp-0x6b4c*0xC63AA + gp-0x6b26*0xC63A6   <- w[3], INERTIA
    + gp-0x6b46*0xC63A4 + gp-0x6bd0*0xC63A0 + gp-0x6bbe*0xC63A2   (each >>10)
```

So the shelf restored the row and then fed it in at **half weight** — net inertia stayed at **0.5× your car**, undoing half the fix downstream and out of sight. All six weights are **1024 in stock AND on your car**; V216 was the only build halving one, it was **w[3]**, and no rationale for it appears anywhere in the lineage. V217 restores it.

**Complete delta vs YOUR CAR — 19 payload bytes, all levers:**

```
  0xC60A8/AC/B0/B4   notch 20.50 Hz          GRINDING
  0xC63AE            1024 -> 512             RATCHET / STUTTER
  0xC6CD0 + clamps   6x -> 8x                LKAS AUTHORITY
  0x55DF2            427 probe -> gp-0x6b4e  instrument
```

Inertia (row **and** weight, both modes) and friction now **match your car exactly**. Every other byte is one of the three levers or the probe. 59/59 builder assertions, CRC 50/50, readback byte-identical.


```
39990-TVA,A160-V216-V215BASE-FRICTION.LANE.TO.FLOWN.V108-0x13000-0x100000.rwd
  image 791e123fb4d8bd6ea0736c52546995bb15742444b5d5c23b6db128e8bd792a13
  .rwd  33b5a59c338b1702750565e36f3eca9f8e4a770c7e061ff1ece7db5313214ce1
```

V216 = V215 + the friction lane pinned to your car (`0xC40BC` 3000→600, `0xC40D2` 102→204). That is **0.200× → 2.000× Honda = 10× more assist = a lighter wheel**, and it saturates at 50 °/s (Honda’s own point) instead of 250. The ratchet regime (1–13 °/s) sits far below **both** saturation points, so the full 10× applies exactly where the symptom lives.

**Complete delta vs YOUR CAR — 20 payload bytes:**

```
  0xC60A8/AC/B0/B4   notch 20.50 Hz            <- grinding
  0xC63AE            1024 -> 512               <- ratchet/stutter
  0xC6CD0 + clamps   6x -> 8x                  <- LKAS authority
  0x55DF2 / 0x55E10  427 probe -> gp-0x6b4e    <- makes the drive readable
  0xC63A6            w[3] 1024 -> 512          <- carried from V181, still unpriced
```

Inertia (both modes) and friction now **match your car exactly**. 53/53 builder assertions, CRC 50/50, readback byte-identical.

⚠ **One cell still unpriced against the car:** `0xC63A6` (model lane `w[3]`) sits at 0.5× yours, carried from V181. Given the friction lesson — model-side weights move the tracking reference, not the motor — this deserves the same check. Next on the list.


```
39990-TVA,A160-V215-V214BASE-INERTIA.M26.AND.M27.TO.FLOWN.V108-0x13000-0x100000.rwd
  image afc1d88505d2c55d37d6379f4cab058b9d1926c334c13d4c92761d138c62fbff
```

V215 = V214 + **mode 27’s inertia row pinned too**. V214 restored only mode 26, resting on the memory that this car (TVCA4) uses modes 24/26. That memory is probably right — the V105→V106 on-car dose-response proves mode **26** is live — but there is **no equivalent evidence that 27 is dead**, and your car carries 27 high as well. RULE 7 says mode-proof or it is a bet, and this kit already lost a whole dose ladder to a mode assumption (V69/V70 wrote mode-10 `gain_B` and were byte-stock). **Six bytes removes the bet.** V214 is superseded.

**Full delta vs YOUR CAR — 23 payload bytes, every one named:**

```
  0xC60A8/AC/B0/B4   notch 20.50 Hz          <- grinding
  0xC63AE            1024 -> 512             <- ratchet/stutter
  0xC6CD0 + clamps   6x -> 8x                <- LKAS authority
  0x55DF2 / 0x55E10  427 probe -> gp-0x6b4e  <- makes the drive readable
  0xC63A6            w[3] 1024 -> 512        <- carried from V181
  0xC40BC / 0xC40D2  knee 600->3000, K1 204->102   <- carried; see note
  0xD7A5C / 0xD7A6C  inertia = YOUR CAR      <- restored, both modes
```

⚠ **One large carried delta remains, flagged not changed.** The friction lane sits at **0.10× your car’s** modelled friction (knee 5× higher, K1 halved back to Honda). That is a big reduction — but it is in the direction you have asked for (*“low apparent steering mass and friction to LKAS”*), so it is reported rather than reverted. Say the word and I will pin it too.


```
39990-TVA,A160-V214-V213BASE-INERTIA.RESTORED.TO.FLOWN.V108-0x13000-0x100000.rwd
  image 4be4d47c1f0ad0deacbac46bd020cf5e02f06896144455766be48e330dbcedb5
  .rwd  d6c2ed81f50bbcd0e23d94af672771d2ceca9c801725b29c286cc29a3a689e90
```

### 🛑 What this fixes, and why it matters more than the notch

`gp-0x6b26` (`0xD7A5C`, the engaged m26 row) is **a real 6–9 Hz damper** — measured after V94 flew it: **+137°/+139° vs wheel rate, |cos| 0.73 ⇒ +518/+565 counts of positive Re(Z)**. V94 cut it hard and **the drive was aborted**:

> *“Made the stuttering and grinding worse, by a lot. So much so that it vibrated the entire car, and I decided it was not safe to drive.”*

Route **`r7d` is that aborted drive**, and it carries the signature: a sustained, engagement-gated **~31 Hz line at 459× the creep-matched corpus median** (prominence 56×; survives 0.5 s edge-trimming; 56 % of 5–49 Hz power inside 30–35 Hz; speed-invariant across all three episodes; engaged/manual contrast 54×).

**The problem:** the car runs **V108 at 3.576× Honda**. The entire notch shelf runs **0.500×** — a **7.15× cut of that damper**, reached in two *never-flown* steps (V175 3.576→1.000, V196 1.000→0.500) and carried silently inside builds whose stated purpose is a grinding fix. **That is a bigger cut than the one you aborted on, in the same direction.**

Every earlier check compared this row to **Honda**, which made a 7.15× change *from your car* read as a tidy “half dose”. Close-out **[14]** now prices it against **both** references.

### What V214 is

V213 — notch 20.50 Hz + `0xC63AE` 512 + 8× gain + the `gp-0x6b4e` probe — with `0xD7A5C` pinned to **the value already on your car**. 14 payload bytes, cal-and-probe only, **no cave change**. 47/47 builder assertions, CRC 50/50, readback byte-identical.

**This is not “adding mass.”** It is declining to remove 86 % of a damper that is on the car today, inside an experiment about something else. Your standing instruction against fixing the ratchet by adding friction is respected: nothing here goes **above** what you already drive.

⚠ **V213 is the paired arm** — identical but with the damper cut. If V214 is good and V213 is worse, the damper cut is the culprit and this whole line of builds needs it reverted. That pair is now the cleanest single-variable test on the shelf.

```
python rlog-tools/score/score_drive.py <tag> V214   # start here -- NAME THE BUILD
```

---

## V213 — the paired arm: identical to V214 but with the 6–9 Hz damper CUT 7.15×.

```
39990-TVA,A160-V213-V208BASE-C63AE.512-GAIN8X-PROBE.GP6B4E-0x13000-0x100000.rwd
  image b1f998702adbbce9a52e7e430906f0cd77410625c29887e4d0a06e4cddb0e239
  .rwd  c43546ba8b59ec716c539d1457511524e591dc527810bdcd3c596339a6a3e3ca
```

Built 2026-08-29. **V212 + the authority lever.** 8 payload bytes, cal-and-probe only, **no cave change**. 42/42 builder assertions, CRC 50/50, `.rwd` readback byte-identical.

| lever | cell | targets |
|---|---|---|
| notch 20.50 Hz | `0xC60A8/AC/B0/B4` | **grinding**, 18–22 Hz |
| soft-relay dose | `0xC63AE` 1024→512 | **ratchet/stutter**, ~7.8 Hz |
| forward gain 6×→8× | `0xC6CD0` 5346→7128 + clamps `0xC61B2/B4` 3072→4096 | **LKAS authority** |
| 427 probe | `0x55DF2`, `0x55E10` | reads `gp-0x6b4e` so the drive is interpretable |

**The gain step is priced, not guessed.** It raises loop gain a flat 1.333× ⇒ vibration 1.650× (the kit’s m^1.74 amplitude law). The notch gives back 3.59× at 22–26 Hz ⇒ **net 0.459×: 2.18× quieter AND 1.33× more authority.**

**Both reasons this was previously staged are now resolved:**

1. The engagement-gated **42.19 Hz line is the rectifier image of the 21.09 Hz mode** — `gp-0x6ba6 = |gp-0x6b9a|` at `0x3b87a`, so 2f falls out arithmetically. It only indexes boost LERPs that are **flat at the operating point**, and that arc **already flew NULL** as V58/V59/V60. Not an independent mode.
2. **Grind #2** (40–49 Hz, +9.7 dB(A)) was **created by V62’s rate-lane ×2**, and this base is **byte-stock at `0x3AB76`/`0x3AC20`** — asserted in the builder. Prior work also found 40–49 Hz is **not engagement-conditional** and the 28 Hz transient is **dose-independent**.

✅ **The residual risk is now MEASURED on the drive itself.** `score_drive.py` gained a **30–49 Hz control band** on `cs_rate`, `imu_vert` and `imu_lat`, with a corpus baseline from 23 cached routes (30–40/grind median **0.0365**, IQR 0.0275–0.0561). On a clean notch drive the ratio should read **~0.54** — the notch removes 14.9× of the denominator, not because the upper band moved.

🛑 **But be clear what one drive settles.** The 1.65× gain effect is **smaller than the corpus IQR** (a factor of 2.0), so **one route cannot resolve whether the gain step costs anything at 30–40 Hz.** What it *can* catch is a grind-#2-scale event (11.71×): read the band as a **large-excursion detector** — under ~2 nothing broke, over ~5 fall back to V212, in between is unresolved and needs a matched V212 drive.

⚠ **Residual risk, stated plainly.** Break-even is 29.5 Hz; above it the notch gives nothing back, so this build **raises loop gain 1.65× across 30–49 Hz**. There is **no direct measurement of that band on this base** — the two arguments above are inference from prior builds, not a measurement of V213. **If you want the safer half, fly V212**, which is this build without the gain step.

⚠ **Three levers is a real confound.** The probe separates the ratchet lane from the grind band; it does **not** separate the gain step from either. V212, V210, V209 and V211 are all on the shelf to decompose an ambiguous result.

```
python rlog-tools/score/score_drive.py <tag> V213   # start here -- NAME THE BUILD
python rlog-tools/probe/decode_v204_observer_lane.py <tag> --v209
```

---

## V212 — THE CONSERVATIVE HALF. Same build without the gain step.

```
39990-TVA,A160-V212-V208BASE-C63AE.512-PROBE.GP6B4E-0x13000-0x100000.rwd
  image dcc1b921e85e56bce56b3c1e69c795194c141dd4486b4f4e8b3755a2a6c2b04a
  .rwd  1bd255313bee04338c23ac795453bc4eae344e1da102fd6cd77ec83c53055a22
```

Built 2026-08-29. **V208 base + `0xC63AE` 1024→512 + the V209 probe.** 4 payload bytes, cal-and-probe only, **no cave change** — not the bricking class. 36/36 builder assertions, CRC 50/50, `.rwd` readback byte-identical.

**Why this one and not V209 or V210.** The three symptoms had three separate builds, and only one of them could be read:

| build | notch (grinding) | `0xC63AE` (ratchet) | probe |
|---|---|---|---|
| V208 | yes | — | — |
| V209 | yes | — | yes |
| V210 | yes | yes | **no** |
| **V212** | **yes** | **yes** | **yes** |

V210 already carried both levers but **no instrument**, so a partial result would have been uninterpretable — the design failure the iteration doctrine explicitly forbids. V212 is that build with V209’s probe added.

**The two levers do not overlap in frequency**, measured from the built image:

```
            |H| at 7.8 Hz    |H| at 20.5 Hz
  stock        0.98290          0.87271
  V212         0.97953          0.00000
```

The notch is a null at the grind band and leaves the ratchet band essentially untouched (0.980 vs 0.983), so the `0xC63AE` dose owns 7.8 Hz on its own and the probe separates them. **GATE 2: max|H| = 1.0000 over 0–500 Hz, exactly stock’s bar** — the filter removes loop gain and adds none.

⚠ **Two levers in one build is a deliberate confound**, accepted because they act in different bands and the probe reads them apart. If the drive is ambiguous, V209 (notch only, instrumented) and V210 (notch + cal, blind) are both on the shelf to split it.

⚠ **The `0xC63AE` dose is not a flat 0.5×.** Its describing function ranges 0.47–0.79 over amplitude — see the V210 section below for the table. It lowers gain everywhere, which is the GATE 2 pass, but do not quote “half”.

**Probe decode** — 427 frame, source `gp-0x6b4e`, `sar 5`:
`x = (raw < 512 ? raw : raw - 1024) * 32`, rails at raw 320/704 (the ±10240 clamp in `FUN_00026c80`).
`gp-0x6b4e` is the **mode-5 arm of the `0xC4124` router** — value B from slots 2/4/5/9, slot 2 being the live PI lane-2 output — and `FUN_00038148` reads it at `0x3817C` as model lane w[4]. **Confirmed live 2026-08-29**, not a dead cell.

```
python rlog-tools/score/score_drive.py <tag> V212   # start here -- NAME THE BUILD
python rlog-tools/probe/decode_v204_observer_lane.py <tag> --v209
```

---

## V209 — the notch and probe WITHOUT the ratchet lever. The re-centred notch, plus the probe.

```
39990-TVA,A160-V209-V208BASE-PROBE-GP6B4E-0x13000-0x100000.rwd
  image 984dfe5590bb8bfedaedca1256008cdd81cf33837acaa54a909463768b47327c
```

Preflight 8/8, 40/40. V208 control cells byte-identical, +3 payload bytes putting `gp-0x6b4e` on CAN 427.

## V208 — the same fix without the instrument

```
39990-TVA,A160-V208-V202BASE-NOTCH.20.50.REFIT.ON.EPISODES-0x13000-0x100000.rwd
  image e27b4fcc2dafd872feb25e5625544dbe4f9067a742cec1670d8d3dde176b1f7a
```

🛑 **The notch was a hertz low.** It was fitted at 19.75 Hz from a per-route median of 20.12. Surveying
the cached corpus **per engaged episode** — 20 routes, 125 episodes — gives **median 20.70 Hz**
(p10 16.37, p90 23.05). Scoring the actual peaks through each candidate, under the same two gates:

| design | Δphase | median atten | p10 |
|---|---|---|---|
| V202 (19.75 / 15.25 / 0.9600) | −7.83° | 5.7× | 2.3× |
| **V208 (20.50 / 15.50 / 0.9575)** | −7.98° | **9.5×** | 2.0× |

✅ **Re-scored on the 18-route cluster** (the 2 outlier routes at ~15.7 Hz excluded, a 3.71 Hz gap separates them): **V208 gives median 10.4×, p10 3.4×.** The pooled p10 of 2.0× was those two routes, not a distribution tail. The best possible re-centre buys 1.11× — inside noise, so **V208 stands.**

**1.66× at the median for the same gate and budget** — and only −0.11° more lag at 3 Hz than V202, so
very nearly free. ⚠ 20 routes here vs 67 in the original fit, so the 0.58 Hz gap could be sampling;
what is not sample-dependent is that 19.75 sits below **both** medians.

## After the drive, one command

```
python rlog-tools/score/score_drive.py <route-tag>
```

Exposure and episode count first, then the free cave rungs (degenerate readings flagged as
**uninterpretable, not null**), the b3 validity gate, b6 against measured-dead, **b5 against its
pre-registered 0.31–0.49**, the 427 channel, and the grind peak **stratified by this drive’s own
episodes**. It refuses to apply the b5 prediction to a non-shelf route.

## V210 — the ratchet lever, on the current notch

```
39990-TVA,A160-V210-V208BASE-C63AE.1024.TO.512-0x13000-0x100000.rwd
  image ab49ca762b7017de436a7b80d15a7a72fda7e3f862f32c3a9106318018da814b
```

✅ **GATE 1 + GATE 2 PASS.** V208 plus **one calibration byte**: `0xC63AE` 1024 → 512. Preflight 8/8, 34/34 assertions, cave
byte-identical, the 427 probe untouched.

⭐ **What it actually does: it RAISES A CEILING.** `0xC63AE` scales the LERP’s input, so halving it **doubles the residual needed to clip — 14490 → 28980, at every speed.** The record’s own model of the ratchet is a *command-gated saturation*, with the instruction *“find what clips, and either raise its ceiling or soften its corner”*. This is the raise-its-ceiling branch, and unlike a gain argument it survives the ratchet being speed-invariant, because clip duty is about the ceiling, not loop gain.

`0xC63AE` also scales the curve behind `gp-0x6b70`, which computing from the image shows is a
**soft relay** — gain 2.67–3.77× near zero against 0.26–0.52× mid-range. Halving it halves that
small-signal gain (2.67→1.33, 3.77→1.89). It has **exactly one site image-wide and zero writers**,
and scales this stage only — the base assist map is untouched.

⚖ **The price.** The record's nine-link polarity trace covers this stage, with a measured
`d(gp-0x6b94)/d(gp-0x6b70)` of +0.25. Lowering the scale shrinks `gp-0x6b70` toward zero, and V87
measured it **negative 67 % of engaged time** — so the net is **predominantly less assist, a slightly
heavier wheel.** You have asked for low apparent friction *and* no ratcheting; this buys one with some
of the other, which is why it is **not** the recommended build. **Fly V205 first** — it measures the
range so this dose can be sized instead of guessed. A quarter dose is the follow-up.


### 🛑 PRE-REGISTERED, AND IT CHANGES HOW V206 MUST BE SCORED

If the ratchet is a limit cycle through this stage, it sits where `N(A)·|G|=1`, and the describing
function computed from the image **peaks at a specific amplitude**:

| speed | limit-cycle amplitude A* | N(A*) | predicted `|gp-0x6b70|` swing |
|---|---|---|---|
| 320 | 185 | 2.49× | 460 counts |
| 640 | 165 | 2.65× | 438 counts |
| 1280 | 150 | 3.02× | 453 counts |
| 2560 | 165 | 3.75× | 619 counts |
| 5120 | 310 | 3.95× | 1224 counts |

🛑 **SUPERSEDED ENDPOINT.** Two corrections: the limit-cycle FREQUENCY test is vacuous (a Q 14–29 resonance pins the −180° crossing within ±0.3 Hz of 7.79, so every hypothesis passes), and the amplitude table above is SPEED-INDEXED while the record calls the ratchet **speed-invariant** — so do not score on amplitude either.

⭐ **SCORE V205 ON CLIP DUTY AT ±8192.** `gp-0x6b70` saturates there and V205 reads it directly. High duty ⇒ the command-gated-saturation model is confirmed and V206 is aimed correctly. Low-but-nonzero ⇒ partial; a quarter dose quadruples the ceiling. **Identically zero ⇒ the element never clips and V206 comes off the shelf.** A duty needs no scale calibration and cannot be averaged away.


### ✅ A FREE ENDPOINT EVERY SHELF BUILD ALREADY CARRIES

The 164-byte cave at 0xC4B34 is **byte-identical from V105 through V202**, so V202/V205/V206 carry
V105’s exact rungs. Two of them report for free, with no extra bytes:

| rung | meaning | what to expect |
|---|---|---|
| **b5** | |modelled friction| ≥ |inertia| | **0.42, range 0.31–0.49.** V105 measured 0.2798 at 1.000× the inertia dose; V202 runs 0.333×. **b5 ≤ 0.28 means the halving is not reaching the car and the ratchet lever is inert** — the most useful null available |
| b6 | |gp-0x6b94| ≥ |gp-0x4f64| | 0.000000 — already measured dead on two routes; a non-zero reading would be new information |

The b5 prediction comes from a measured single-cell pair: V105→V106 doubled the inertia curve and b5
fell **−0.0891 [−0.1328, −0.0200]** on an episode bootstrap, with both sign rungs as null controls.
So this lever is known to reach the car with the right sign — what is unknown is whether the halving
does, and one drive of any shelf build answers it.

## 🛑 V211 — STAGED. Do NOT flash until the notch is confirmed on-car.

**Priced properly 2026-08-29 — the staging now rests on a measurement, not a procedure.**

The 6×→8× step (`0xC6CD0` 5346→7128) raises loop gain a flat **1.333×**, which by the kit's own empirical amplitude law (vibration ∝ gain^1.74) grows vibration **1.650× at every frequency*. The notch gives that back only inside its skirt:

```
   f (Hz)   notch atten   vs growth 1.65x   net
     23        4.48x            ->          0.37x  quieter
     28        1.89x            ->          0.87x  quieter
   --------- break-even at 29.5 Hz ---------
     30        1.59x            ->          1.04x  LOUDER
     35        1.13x            ->          1.47x  LOUDER
     40        0.80x            ->          2.07x  LOUDER
     49        0.30x            ->          5.53x  LOUDER
```

**Below 29.5 Hz it is a clear win** — 1.33× more authority *and* 2.18× quieter at 22–26 Hz. **Above it, the notch contributes nothing and the gain raise is unopposed.**

That band is not empty. **V59 measured an engagement-gated 42.19 Hz line** — prominence **11.10× engaged vs 0.00× disengaged**. Its proposed mechanism (2f parametric modulation of the PID lane gains) is **VOID**, re-verified 2026-08-29: `K_p`/`K_i`/`K_d` at `0xC6B1E`/`0xC6B0A`/`0xC6ADE` are **flat in segment 0** at the operating point `gp-0x6ac0` = 99, and the contrary reading used `0xC671E` — **off by 0x400**, landing on the square-wave injector block. So the *mechanism* is dead but **the line itself stands and is unexplained.**

⇒ Raising loop gain 1.65× exactly where the notch stops helping, in a band carrying an unexplained engagement-gated line, is not a blind change. **Fly V212 first.** If the notch is confirmed, this becomes reasonable and the natural follow-up is V212 + these cells.

⚠ **GATE 2 does not catch this** — it checks the biquad alone, but the loop gain is biquad × `0xC6CD0`. That gap is now closed by **close-out section [13]**, which prices any build raising `0xC6CD0` above the 5346 baseline and fails it unless explicitly staged.


```
39990-TVA,A160-V211-V208BASE-GAIN8X-CLAMPS4096-0x13000-0x100000.rwd
  image 70b205589b6f81a9f1e4f039daf8f744a66a1b9865ddbe133b499ef6ce35368e
```

**This is the LKAS authority build** — the first with a defensible case since V101. It raises
the forward gain 6× → 8× and the two clamps that must track it. 37/37, preflight 8/8.

| cell | V208 → V211 | why |
|---|---|---|
| `0xC6CD0` | 5346 → 7128 | the forward gain, 6× → 8× |
| `0xC61B2` | 3072 → 4096 | at 8× the lane max is 3341, which exceeds 3072 |
| `0xC61B4` | 3072 → 4096 | same — this is why V101 had to raise them too |

**Why it is worth re-opening.** The gain was abandoned three times because vibration grows as
`m^1.74` against authority’s `m^0.88`. **That trade is set by the baseline, and V208 moves it.**
Energy-weighted over the band the gain excites (22–26 Hz, 130 episodes):

| | |
|---|---|
| V208 attenuation there | **3.70×** (amplitude) |
| 6× → 8× vibration growth | 1.65× |
| **net vs the car today** | **0.45× — about 2.2× quieter** |
| authority gained | 1.29× |

V101 flew 8× at **1.65×** the then-current level and you reported grinding at all speeds. This
sits at **0.45×**.

🛑 **The staging is the safeguard, and it is not optional.** The case rests on a *belief*:
that the notch attenuates a **command-excited** line. The notch is on the base-assist path, not
the command path — but it sits inside the loop (motion → column torque → sensor → assist map
→ biquad → aggregator → motor → motion), so it lowers the loop gain that *sustains* the
resonance whatever excites it. **That is reasoning, not measurement.** If it is wrong, 8× lands
at 1.65× and you will hear it on the first engaged mile.

✅ The builder asserts the three gates that killed earlier gain builds: `0xC674E` = 5120 must
stay **above** the tracking clamp (the abort condition that caps this lever below 10×), lane max
3341 < 4096 so the clamps do not bind, and `0xC407E` stays at Honda’s 511 — V73
raised it and V74/V75 faulted.
## V199 — the low-phase fallback

```
39990-TVA,A160-V199-V196BASE-NOTCH.POLES.BELOW.ZEROS-0x13000-0x100000.rwd
  image c86646ab48c4a62546b4e7bafa59f8097d3bdd99ffdcd3aeabd9f93c7252dc10
  rwd   8df71f5db9f51e3cccf2d14c27aa580869434125112271115cfaddeddface708
```

A notch on the grind at **19.75 Hz**, plus the engaged inertia half-dose, built so the filter **cannot
add loop gain at any frequency**.

---

## 🛑 WHY V194 / V195 / V196 / V198 WERE PULLED

`BUILD-LINEAGE.md`, V105 section, says it outright:

> *"THE HIDDEN ONE: fixing DC with **poles at the notch angle** (the textbook narrow notch) forces
> `max|H|` to 1.098–1.608 … Fix: **Honda's own poles-BELOW-zeros layout**. **Check `max|H|` over
> 0–500 Hz against stock's 1.0000 before shipping any biquad edit.**"*

Every notch build from V188 on put the poles at the zeros. Measured from the built images:

| build | `max|H|` 0–500 Hz | zeros | poles | radius | verdict |
|---|---|---|---|---|---|
| V122 (Honda's layout) | 1.0000 | 55.23 | 42.35 | 0.7966 | PASS |
| V188 / V189 / V194 | 1.3533 | 19.40 | 19.40 | 0.9300 | **FAIL — adds 35 % loop gain** |
| V195 / V196 / V198 | 1.7177 | 19.75 | 19.75 | 0.9000 | **FAIL — adds 72 % loop gain** |
| **V199 / V200** | **1.000000** | 19.75 | **17.45** | 0.9675 | **PASS** |

V196 amplifies **1.88× Honda at 35 Hz, 4.57× at 45 Hz, 1.72× at Nyquist**. V103's own GATE 2 — the
argument that licensed arming this filter at all — was *"|H| ≤ 1.000032 everywhere 0.1–500 Hz ⇒ the
filter can only REMOVE loop gain, never add it."* A filter that **adds** gain in the loop whose
instability we are chasing is not a fix.

**It shipped because V195's own gate was written `check(mx <= 2.0, …)`.** The gate existed and the
number in it was wrong. V199's is `<= 1.0000001`, with a control assertion that the V196 base fails it.

---

## WHAT EVERY BUILD ON THIS SHELF CHANGES vs V122 — 11 cells, 30 payload bytes

| addr | V122 → V208/V209 | what it physically is | introduced |
|---|---|---|---|
| `0xC60A8` | −1.5372 → -1.905926 | biquad pole angle → **15.50 Hz** | V208 |
| `0xC60AC` | 0.63462 → 0.9168062 | biquad pole radius → **0.9575** | V208 |
| `0xC60B0` | −1.8808 → -1.983432 | **the notch centre, 55.23 → 20.50 Hz** | V208 |
| `0xC60B4` | 0.81731 → 0.6567325 | overall gain — forced by unity DC | V208 |
| `0xC40D2` | 1020 → **102** | K1, modelled Coulomb friction — Honda’s VALUE, but see below | V177 |
| `0xC40DC` | 8 → **22** | acceleration EMA alpha → **Honda** | V179 |
| `0xC63A6` | 1024 → **512** | w[3], the inertia term's weight, halved | V181 |
| `0xD7A5C` | (−29490,−17202,−16000) → **(−4915,−2867,−983)** | **engaged** inertia curve, **half Honda** | V196, kept |
| `0xD7A6C` | (−29490,−17202,−16000) → (−9830,−5734,−1966) | m27 inertia curve → **Honda** | V175 |
| `0x55DF2` | −27324 → −27328 | CAN 427 probe source → `gp-0x6ac0` | V183 |
| `0x55E10` | 12963 → 12964 | the probe's pack shift, `sar 4` | V183 |

**Measured on-car:** none of the four biquad cells — this filter geometry has never flown.
**Reverts to Honda:** `0xC40DC`, `0xD7A6C`.
🛑 **The friction lane is NOT Honda’s.** `0xC40D2` holds Honda’s K1, but the ramp knee `0xC40BC` was
never reverted (600 → 3000) and it multiplies the whole expression: `(600/3000)×(102/102)` = **0.200×**
Honda below saturation, with saturation moved from motor-rate 50 to 250. Above saturation it equals
Honda exactly. **Less friction means less ratchet and matches your low-friction directive, but the
verified polarity is more friction = more assist, so it is also an authority cut in that lane.**
**Unverified doses:** `0xC63A6`, `0xD7A5C` (the inertia sign has not been confirmed on-car).
**The cave is byte-identical** to V196 — no code-cave change, so this is not the bricking class.

🛑 **Manual driving is unaffected by the biquad either way.** The section is engagement-gated by V103's
three-site patch on `gp-0x6806`, so every notch cell is inert with LKAS off.

---

## BEFORE YOU FLASH

```
python flashing-2020accord/preflight.py "<the .rwd filename>"   # all five pass 8/8
tmux kill-server                                                # openpilot/pandad MUST be dead
```
Name the file and the bus out loud. They will be read back to you before anything is sent.

## THE DRIVE

Two passes are enough. The design law is that one short symptomatic drive must interpret the build.

1. **~15 s engaged creep, hands off** — the grind’s home ground.
2. **~15 s engaged, hands lightly on** — the corpus blind spot; `f'` compresses 6.3× when you push.

Then, in this order:

```
python rlog-tools/score/score_drive.py <tag> V209                     # start here -- NAME THE BUILD
python rlog-tools/probe/decode_v204_observer_lane.py <tag> --v209     # V209 only

The build argument is not optional: a route tag does not encode which firmware flew, and the ratchet
prediction is computed from the inertia dose read out of that build’s image. Without it the scorer
refuses to interpret b5 rather than guessing.
```

🛑 **The decoders were all broken until 2026-08-29** — they `chdir` to `rlog-tools/` and then looked
for a kit-root-relative cache path, so every one of them would have failed after a drive with
"no cache". Fixed in all five. If a decoder ever says "no cache" for a route you know exists,
that is the bug returning, not a missing capture.

## STOP CONDITIONS

| what you feel | what it means | what to do |
|---|---|---|
| ratcheting noticeably **worse** | the inertia sign is inverted | stop; reflash **V199** |
| wheel heavy or dead to fast inputs | the inertia half-dose is too much | stop; quarter it |
| a **new high note while engaged** | Honda’s 55 Hz null, which the notch gives up | stop — it can only appear with LKAS on, since the section is engagement-gated |
| grinding unchanged | **check the peak before concluding anything** — see below | do not assume the notch is wrong |

🛑 **"Grinding unchanged" is not by itself a null.** The notch is a **point fix**: V208 gives
~10× at 20–21.5 Hz but only ~2× at 16.5 Hz. Run the scorer first — it prints the drive’s own
**power-weighted** peak. A drive whose peak landed at 16 Hz never sampled the notch’s band, and
that is a statement about the drive, not about the fix.

## PRE-REGISTERED — write the sentence a null will license

| endpoint | prediction | what a null means |
|---|---|---|
| **15–25 Hz on `cs_rate`, at the drive’s own power-weighted peak** | peak ≈20.5 Hz → **the null** · 19.5 → 9.2× · 21.5 → 10.3× · 22.5 → 5.4× · 18.0 → 3.4× · 16.5 → 2.1× | if the peak sat in the notch’s band and nothing moved, the grind is not in the assist section’s path |
| corpus-wide band **energy** | V208 removes **14.9×** | a point fix cannot be judged on one episode |
| **`b5` (free — every shelf build carries it)** | **0.31–0.49**, against 0.2798 measured at 1.000× the inertia dose | **≤ 0.28 ⇒ the halved inertia is NOT reaching the car**, and the ratchet lever comes off the shelf. The most useful null available |
| `b6` (free) | 0.000000 | measured dead on two routes, 49k and 124k frames. Non-zero would be new information |
| `b3` (free) | must **vary** | a constant b3 is **run-invalidating**, not a finding |
| `gp-0x6b4e` saturation (V209) | unknown — this is why V209 is the one to fly | its producer is an uncapped 10-slot accumulator, so unlike every other clamp this bound is **not provable** and must be measured |
| 6–9 Hz on `cs_tq` | unchanged | the notch was never aimed there; that band is the ratchet |
| LKAS command 0.5–3 Hz | unchanged | the biquad is not in the command path, so movement here is something else |

## 🛑 WHAT THE NOTCH CAN AND CANNOT FIX — corrected 2026-08-29

Decompiling `FUN_000352b4` settled which signal this filter is actually on. The tp anchors check out
exactly (`tp+0x749b` = `0xC649B` the arm cell, `tp+0x70a8`–`0xb4` = the four coefficient cells), so this
is the filter we have been editing:

```
gp-0x4f60 (TORQUE SENSOR) -> clamp +-8192 -> 10-knot assist map -> gp-0x6b7a
  -> friction-hold limiter -> gp-0x6b82 -> BIQUAD -> clamp +-12.0 -> x1024
  -> + gp-0x6b7e  (UNFILTERED, added AFTER the filter)
  -> clamp +-0x3000 -> gp-0x6b86 -> aggregator
```

**`gp-0x6b86` is the base power-assist output, not the LKAS command.** An earlier note of mine called
it "the LKAS command" — that was wrong and is retracted. What follows:

| symptom | can this notch fix it? |
|---|---|
| **Grinding** | **Yes, and this is the right place.** motion → column torque → sensor → assist map → biquad → aggregator → motor → motion **is** the loop, and the notch cuts its gain at 19.75 Hz. |
| **LKAS authority** | **Not affected either way — and that is good news.** openpilot's command never passes through this filter, so **no notch dose can reduce how hard it steers.** The authority objection does not apply to this lever. |
| **Peak command oscillation** | **Not directly.** The command does not pass through the filter. It may still fall if it *tracks* the grind, which the record says it does — but that is an indirect claim, and this build is not evidence for it. |
| **Ratcheting** | Not by the notch. That is the inertia half-dose at `0xD7A5C`, carried on all three builds. |
