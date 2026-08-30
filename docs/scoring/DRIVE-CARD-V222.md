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

## Verification behind this build

- **72/72 build assertions**, CRC 50/50, `.rwd` decodes byte-identical to the built image.
- **835 close-out assertions**, **15/15** shelf builders reproduce bit-for-bit.
- The unsaturated slope is **asserted identical** before and after, so the build cannot have touched
  the ratchet regime.
- `0xC40BC` and `0xC40D2` each have **exactly one reader** and zero writers, confirmed by the kit's
  own false-positive-filtered census (`tp_cal_readers.py`) and by the decompile.
- 🛑 A close-out entry listing `0xC40D2 = 204` as *"the FLOWN car"* was **removed** — the car is 1020,
  and that mislabel is precisely why the gap survived every check.
