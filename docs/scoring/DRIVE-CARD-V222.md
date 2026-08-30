# DRIVE CARD — V222 · **the new primary. V221 is the fallback.**

**Flash target:** `39990-TVA,A160-V222-V221BASE-FRICTION.LANE.SATURATION.TO.CAR-0x13000-0x100000.rwd`
**.rwd SHA256** `0766d45cbad4bde1d48a0f53d63a17f28c436aaed694ef87c4a941f732a46b17`
**image SHA256** `0e83c7074699d6ab3eee1c035974fa23b5b271c641662001b63fd89558512dae`

> 🛑 **Nothing here authorises a flash.** Name the file and the bus yourself and they will be read
> back to you first. Kill openpilot/pandad (`tmux kill-server`) before any flash operation.

---

## What is on it — **23** payload bytes from YOUR CAR (V122), down from V221's 27

```
  0xC60A8/AC/B0/B4   notch 20.50 Hz            GRINDING       (18-22 Hz)
  0xC63AE            1024 -> 512               RATCHET        (~7.8 Hz)
  0xC6CD0 + clamps   6x -> 8x                  LKAS AUTHORITY (+28.9 %)
  0xC6446            5244 -> 13107             LEVER B: less HF everywhere, no LF cost
  0x55DF2            427 probe -> gp-0x6b4e    the instrument
```

**V222 is V221 with four bytes REMOVED from the delta, not added.** Every deliberate lever above is
byte-for-byte identical to V221. What changed is that the friction lane now matches your car at
**every** steering rate instead of only below its knee.

---

## What V216 got half-right, and why it mattered

`FUN_0003b8f6` is the **plant-model observer**. Mirrored from the decompile, address by address:

```
  ratio     = clamp(polarity * gp-0x6abc * 12 / cal(0xC40BC), -1, +1)          0x3BAAE..0x3BAE4
  friction  = EMA(|model| * ratio * cal(0xC40D2)/1024 + ratio * cal(0xC4080)/1024)
  model_out = clamp((model - (friction + damping)) * cal(0xC6468), +-20000)    0x3BBBE..0x3BBE0
  residual  = model_out - (actual >> 4)   ->   gp-0x6b70 = sign(res) * LERP(|res|)
```

V216's job was restoring this lane to your car. It restored the **slope** and not the **saturation**,
and every check that looked at this lane looked at the slope:

```
  car   (V122)        gate 3000  k1 1020    unsaturated slope 0.003984
  shelf (V216..V221)  gate  600  k1  204    unsaturated slope 0.003984   <- identical
```

But what each *saturates at* is `k1/1024` of the whole model, and there they are 5× apart:

```
  |gp-0x6abc|     CAR model_out   SHELF model_out    shelf/car
           1           1881.0           1881.0          1.0x   <- the ratchet regime
          13           1791.0           1791.0          1.0x   <- IDENTICAL
          50           1512.0           1512.0          1.0x
         150            760.0           1512.0          2.0x
         250              7.0           1512.0        216.0x   <- your car saturates here
         800              7.0           1512.0        216.0x
```

Your car models friction at **99.6 %** of the whole model once saturated, so **its observer residual
is annihilated above 250 counts of rate** — that lane goes quiet on fast steering. The shelf leaves
**80.1 %** standing, so the lane stays fully live at every rate.

⇒ **V217–V221 carry an uncharacterised ~216× behavioural difference from your car on fast steering**,
in four bytes the V217 card described only as *"less friction ⇒ heavier at high steering rate"*.

🛑 **The ratchet regime is completely unaffected — 1.0× at every rate the ratchet occupies.** This
changes no ratchet expectation. It is a fast-steering claim only.

---

## Why restore rather than keep

Nothing in the record chose 204. V216's own docstring says it is restoring the lane to the car, and
the exact slope match shows that was the intent — the saturation was simply missed. Restoring both
cells makes the lane identical to what you already drive at every rate and removes the only
uncharacterised delta from the flight candidate.

⚠ **This is a de-risking build, not a new lever.** I do **not** claim the shelf's high-rate behaviour
is worse — it is *unmeasured* there, and 216× is too large to carry unexamined into a drive whose
purpose is something else. If a V221 drive reports nothing odd on quick inputs, V222 is unnecessary
and V221 stands.

---

## The drive — identical protocol to V221

```
python rlog-tools/score/score_drive.py <tag> V222
python rlog-tools/score/score_authority.py <tag> V222
python rlog-tools/probe/decode_v204_observer_lane.py <tag> --v209
```

Everything on the V221 card about Lever B, the authority readout, the micro-regime sizing and the
ratchet expectation applies here **verbatim** — those levers are byte-identical. Read
`DRIVE-CARD-V221.md` alongside this one; it is not repeated.

**One thing to notice that V221 would not have shown you:** on **quick steering inputs** — a brisk
lane change, a fast correction — V222 should feel like your car and V221 should not. If V221 felt odd
there and V222 does not, that 216× is why.

---

## A confound this turned up in the record

The kit's headline for `0xC40BC` — *"de-relaying the Coulomb friction made the ratchet band 2.3×
worse"*, from 600 vs 6000 across 30 routes — **is not identified.** Those builds held `k1` at 102
while the gate moved 10×, so the small-signal slope fell 10× at the same time:

```
  V84/V87/V88   gate  600  k1 102   slope 0.001992
  V85/V86/V86B  gate 6000  k1 102   slope 0.000199    <- 10x LESS slope, not just a wider ramp
```

*"De-relaying made it worse"* and *"10× less modelled friction made it worse"* fit that data equally
well, and they are **different levers**. The second is separable via `0xC40D2` alone — one reader
(`0x3BAFE`), zero writers — and has never been tested in isolation. It also has a **real** structural
boundary at `k1 = 1024`, where the modelled friction equals the whole model, the residual is
identically zero, and beyond which the sign inverts. Sizing that is separate work and is not in this
build.

---

## If grinding improves but is not gone — **V223** is rung 2, already built

`39990-TVA,A160-V223-V222BASE-LEVERB.13107.TO.26214.RUNG2-0x13000-0x100000.rwd`  
.rwd `38b0773b774dd4922edf599ae911fb5007fae7e3e5a2a988a9a2c26d7be6fb1d`  
image `a2f034df682cbd4a9ffe9f56787fd40d5465c4c36423362ce7dc03501fa81869`

One more doubling of Lever B, and the dose is **computed rather than guessed**. The lane is a plain saturation, so the describing function gives the effective damping the loop actually sees, and it has a hard asymptote at `4L/(pi*A)` that no gain can exceed:

```
   gain k    onset   p50 (27)  p90 (146)  p99 (610)  max (1669)
     5244     1600       5244       5244       5244        5191   <- YOUR CAR
    13107      640      13107      13107      13107        6239   <- V222
    26214      320      26214      26214      16669        6360   <- V223
    65535      128      65535      62194      17380        6393
 asymptote              395582      73156      17509        6399
```

Two things fall out. **At the amplitudes where the roughness actually lives, V222 is nowhere near the knee** — 13107 → 26214 buys a full **2×** more damping at both p50 and p90. **And at the largest excursion it buys almost nothing** (1.20× → 1.23× even at the cal maximum), so the rung is *selective for the small-signal regime by construction*.

⊕ **The saturation worry is not new.** The knee at the largest excursion is k = 5184 and **your car is already past it at 5244**. More than that: V88’s measured win — grinding fixed, command untouched — came from 512 → 5244, *the very step that carried the largest excursions across that knee*.

⚠ Cost: the onset falls 640 → 320 counts, so clip duty goes ~5.9 % → ~16 % of engaged frames — the large, fast inputs. The onset/p90 margin drops **4.38× → 2.19×**; the build asserts it stays above 2× and prints it, rather than inheriting rung 1’s threshold silently. **This is an open-loop calculation** — it says what the lane can deliver, not that delivering more improves the car.

🛑 **Fly V222 first.** If V222 reads *worse* on grinding than V217 would have, 5244 was already at the optimum and **both rungs are wrong**.

---

## The follow-up arms are now REBASED ONTO V222

🛑 **V218, V219 and V220 were cut off V217, so each of them LACKS Lever B at 13107 AND the friction-lane restoration.** Flying one of them after V222 would have **silently handed back two levers** — the exact failure shape that lost V42’s ratchet fix at a rebase and that hid the 6–9 Hz damper cut inside every notch build from V196 to V213.

Each arm has been rebuilt on V222’s base, carrying its own lever and nothing else:

```
  build  arm                what it changes vs V222     .rwd SHA256 (first 16)
  V223   Lever B rung 2     0xC6446 13107 -> 26214      38b0773b774dd492
  V224   ratchet rung 2     0xC63AE   512 -> 256        04ae388ad7257a83
  V225   authority rung 2   0xC6CD0  8x -> 10x + clamps d4d21c547a1ab9c6
  V226   grind rung 2       notch poles 15.50 -> 13.50  038837ca3372a896
```

All five builds now share **the same 23 payload bytes from your car**, differing only by the one lever each arm exists to test. **Use these, not V218/V219/V220** — those three remain on disk for the record but are superseded as follow-ups.

Mapping from the outcome table above: *grinding better but still there* → **V226** · *ratchet unchanged and you want the dose ladder closed* → **V224** · *levers landed but steering still short* → **V225** · *grinding improved but not gone* → **V223**.

---

## A free extra read on this drive — pre-registered

V222 sits at relay saturation onset **250** counts; the whole V196–V217 shelf sat at **50**. A three-point flown ladder (V111 onset 50 · V112 onset 150 · V122 onset 250, all with the same unsaturated slope) shows the **grinding band falling monotonically with onset** in two rate bins, with the extreme builds’ CIs disjoint in both.

🛑 **I am not claiming it**, and the reasons are written down: the largest bin sorts nothing, the ratchet band scrambles in the same bin where grinding sorts, the middle build is highest in the intermediate band, onset is confounded with build number, and the arithmetic predicts no effect at these rates at all. But **this drive reads it at zero extra cost**:

```
python rlog-tools/score/rate_matched_band_ratio.py
```

| grind 15–22 vs the control band | reading |
|---|---|
| clearly BELOW the V196–V217 shelf era | the knee trend was real, and V222 gained from it |
| indistinguishable | the trend was route difference, as the checks suggest |
| clearly ABOVE | something else moved; do not attribute it to the knee |

⚠ Nothing on this card depends on the answer. It is a spare observation on a drive being made anyway.

---

## Two limits on the numbers you will read back

1. **The 30–49 Hz damage band is not purely 30–49 Hz.** Caches run at fs ≈ 101 Hz, Nyquist ~50.5, so anything real in **52–71 Hz folds into it** — a 71 Hz line lands on 30. The fold source is above Nyquist: it can be neither seen nor filtered out. Read that band as *"30–49 Hz **or its alias**"*, never as 30–49 alone.
2. **Band power tracks steering RATE, hard.** Across 1,368 engaged windows the 30–35 Hz band moves **63×** with rate and barely at all with speed. So any comparison between drives must match on **rate**, not speed — or use a band-to-control **ratio**, which is rate-robust. `score_drive.py` reports ratios for this reason; `rlog-tools/score/rate_matched_band_ratio.py` does the rate-matched version if you want it.

⚠ Neither changes what to flash. They change how to read the output.

---

## If the ratchet is unchanged — **V227** is the one genuinely untried lane

`39990-TVA,A160-V227-V222BASE-RESPID.CEILING.X1.1280.TO.512-0x13000-0x100000.rwd`  
.rwd `a270b05e382712549cf00098e4a8510440db03b4a3c2a55eb1fead2c946b31da`  
image `28b5f4c979660451cda9c457312b824622488201d96ecf1dbf3be90dd8d67434`

Every other ratchet lever on the shelf has either flown or been closed by arithmetic. **This lane has not.** The golden model’s own lane census calls `gp-0x6ad4` *"the most reachable authority of any gated lane"* and says outright that **it has never been scored at 6–9 Hz** — V56 muted it and scored the mute at ~21 Hz, which does not transfer.

One halfword moves the **knee** of its ceiling ramp, not the ceiling height:

```
   speed     stock ceiling   V227 ceiling   ratio
    3 km/h          57            171        3.00x
    6 km/h         228            683        3.00x
   10 km/h         455           1024        2.25x
   20 km/h        1024           1024        1.00x   <- IDENTICAL from here up
```

🛑 **This is an OPEN lever, not a predicted fix — and there are THREE outcomes, not two.** The cell feeds the lane’s **output clamp** *and* the **anti-windup window on its integrator** (both confirmed in the disassembly). The clamp half is reassuring — a symmetric clamp is memoryless and odd, so it cannot invert a sign, only let more of an existing contribution through. The **anti-windup half is not**: an integrator with more headroom stops saturating and contributes its full phase, so this **can** change the lane’s dynamics.

| outcome | what it means |
|---|---|
| ratchet **better** | the lane was damping and was being clipped |
| **no change at all** | the bound never binds at creep — a real possibility, and nothing measures the PID sum, since `gp-0x6ad4` is not mirrored anywhere |
| ratchet **worse** | the lane was pumping, or the freed integrator changed its phase |

Cal-only, so reflashing V222 undoes it.

⚠ **Read it at CREEP.** Above 20 km/h it is byte-identical in effect to V222, so a highway stretch cannot distinguish them.

---

## Verification behind this build

- **72/72 build assertions**, CRC 50/50, `.rwd` decodes byte-identical to the built image.
- **835 close-out assertions**, **15/15** shelf builders reproduce bit-for-bit.
- The unsaturated slope is **asserted identical** before and after, so the build cannot have touched
  the ratchet regime.
- `0xC40BC` and `0xC40D2` each have **exactly one reader** and zero writers, confirmed by the kit's
  own false-positive-filtered census (`tp_cal_readers.py`) and by the decompile.
- 🛑 A close-out entry listing `0xC40D2 = 204` as *"the FLOWN car"* was **removed** — the car is 1020,
  and that mislabel is precisely why the gap survived every check.
