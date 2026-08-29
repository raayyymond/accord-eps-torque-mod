# STATE archive

A RECORD, NOT AN INSTRUCTION.

## ⛔⛔ **PEAK COMMAND OSCILLATION HAS NO REMAINING FIRMWARE LEVER — THE LIMIT IS ALREADY OPEN**
V166 was designed, written, and **killed by its own base assertion before emitting an image.**

### THE CASCADE, AND WHY IT LOOKED LIKE A LEVER
```
   setpoint = STEER_TORQUE x -4      => openpilot's +-4096 rail is setpoint +-16384
   setpoint = clamp(setpoint, +-arb_setpoint_limit)      <-- the binding limit
   lkas_max = min((setpoint x gain) >> 15, forward_clamp 0xC61B2/B4 = 3072)
```
The golden model's `Calibration` default reads **15360**, and the model notes *"openpilot's
torqueBP*4=16384 clips the top 6.25 % at 15360; raising is safe."* At 6x gain
`(15360 x 5346)>>15 = 2505 < 3072`, so the clamp does NOT bind and the setpoint limit is the sole
binding limit. That looked like the one untouched lever for the third complaint.

### ⛔ IT IS ALREADY DONE ON THE FLYING BUILD
```
   record     stock    V122/V158/V160
   0xE4180    15360 -> 16384
   0xE41A8    15360 -> 16384    <-- THE A160 RECORD (gp-0x674e selector 1) -- OUR CAR
   0xE41F8 / 0xE4220 / 0xE5180 / 0xE51A8 / 0xE51D0 / 0xE51F8   also raised
   => exactly 8 of the 28 records, matching the model's "V38 patches all 8 reachable records"
   (16384 x 5346) >> 15 = 2673, still < 3072  =>  protocol reach 4096/4096, NOTHING is clipped
```
✅ **[EVIDENCE] the full +-4096 command range is already delivered.** The edit I designed is a
**no-op on this car.**

### ⭐ THE MISTAKE, AND THE RULE IT BREAKS
I read the **model's default Calibration field (15360 = STOCK)** and scanned the **stock image**,
then reasoned about the flying build. CLAUDE.md already carries the rule verbatim: *"Check build
lineage before proposing a cal lever — grep build_v*_tva.py + BUILD-LINEAGE.md before naming any
address; state its on-car result."*
⊕ **The build harness caught it**: the base assertion found **20** flat-15360 records where the stock
scan found 28, and refused to build. **That is the assertion doing exactly its job** — a base-value
check is not bureaucracy, it is the thing that stops a no-op reaching the car.
⭐ **A model's `Calibration` DEFAULTS ARE STOCK VALUES, NOT THE FLYING BUILD'S.** Read the image.

### ✅ SO THE THIRD COMPLAINT IS CLOSED, AND HERE IS WHY
Peak command oscillation is **sustained one-sided saturation at the 13-bit +-4096 rail** (6.4 % of
frames at 2–8 km/h, episodes to 4 s). With the setpoint limit already at openpilot's own rail:
- the firmware **delivers the entire command range**; there is nothing left to un-clip;
- openpilot rails because it wants **more than 4096**, and 4096 is the **CAN signal's 13-bit maximum**
  — a **protocol** limit, not a firmware one;
- the only firmware quantity that could deliver more torque per protocol count is the **GAIN**, and
  8x was measured **worse** (6x = 1.13 dB vs 8x = 2.24 dB acoustic excess) and rejected by the
  operator's own conditional instruction.
=> **the symptom is bounded by (protocol range x gain), the protocol is fixed, and the gain is frozen
by a measured result.** No firmware lever remains. Closing it needs either an openpilot-side change
(**barred by standing instruction**) or accepting the trade the 8x test already priced.

