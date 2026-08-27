# TECHNICAL SAFETY REVIEW: Honda Civic C120 EPS Max Torque Mod

## Your task

You are reviewing a proposed EPS (Electric Power Steering) firmware modification for a 2021 Honda Civic Sedan. This is real hardware that controls steering on a real car. You must evaluate the specific technical claims, math, and safety implications below. Do NOT punt with "out of scope" — this review requires your direct critique of the firmware values, risk of bricking, and physical safety. If something looks wrong or risky, say so. If it looks sound, explain WHY it's sound.

---

## Background: What is being modified

Honda EPS firmware contains a **torque lookup table** (9 breakpoints x 7 rows). Each row corresponds to a different vehicle speed range. When openpilot (self-driving software) sends a steering torque command, the EPS maps it through this table to determine how much assist the electric motor provides.

The firmware also contains a **filter table** (same 9x7 structure) that controls the rate-of-change limiter — how quickly the EPS motor is allowed to ramp between torque levels.

Both tables are written into the firmware .rwd file and flashed to the EPS ECU via CAN bus using the UDS protocol.

**If the firmware is corrupted or contains invalid values, the EPS may:**
- Refuse to operate (fail-safe → manual steering only, much heavier but drivable)
- Produce grinding/vibration sounds (motor fighting itself)
- Overheat the motor under sustained high torque
- In worst case, damage the EPS motor or gearing

**Recovery**: A stock .rwd backup can be reflashed to restore original firmware. The flash tool (eps-update.py) uses UDS protocol which includes verification steps. A partially-written flash can be recovered by re-flashing.

---

## The specific proposed values

### Stock C120 torque table (what's currently in the firmware from the 2.5x flash):

```
Row 1: 0x0000, 0x0500, 0x0980, 0x0D80, 0x0FCD, 0x1180, 0x1200, 0x1F80, 0x2D00
Row 2: 0x0000, 0x034D, 0x07CD, 0x0C00, 0x0F00, 0x1080, 0x1200, 0x1F80, 0x2D00
Row 3: 0x0000, 0x034D, 0x07CD, 0x0C00, 0x0ECC, 0x1066, 0x1200, 0x1F80, 0x2D00
Row 4: 0x0000, 0x0400, 0x0680, 0x0980, 0x0CD5, 0x1000, 0x1200, 0x1F80, 0x2D00
Row 5: 0x0000, 0x039A, 0x0726, 0x0AEF, 0x0E9A, 0x10E6, 0x1200, 0x1F80, 0x2D00
Row 6: 0x0000, 0x0746, 0x0B04, 0x0CDF, 0x0E19, 0x1008, 0x1200, 0x1F80, 0x2D00
Row 7: 0x0000, 0x06B3, 0x0B1A, 0x0CCD, 0x0E9A, 0x104D, 0x19BE, 0x232F, 0x2CA1
```

### PROPOSED new torque table (what we want to flash):

```
Row 1: 0x0000, 0x0500, 0x0980, 0x0D80, 0x0FCD, 0x1180, 0x1200, 0x4800, 0x6200
Row 2: 0x0000, 0x034D, 0x07CD, 0x0C00, 0x0F00, 0x1080, 0x1200, 0x4800, 0x6200
Row 3: 0x0000, 0x034D, 0x07CD, 0x0C00, 0x0ECC, 0x1066, 0x1200, 0x4800, 0x6200
Row 4: 0x0000, 0x0400, 0x0680, 0x0980, 0x0CD5, 0x1000, 0x1200, 0x4800, 0x6200
Row 5: 0x0000, 0x039A, 0x0726, 0x0AEF, 0x0E9A, 0x10E6, 0x1200, 0x4800, 0x6200
Row 6: 0x0000, 0x0746, 0x0B04, 0x0CDF, 0x0E19, 0x1008, 0x1200, 0x4800, 0x6200
Row 7: 0x0000, 0x06B3, 0x0B1A, 0x0CCD, 0x0E9A, 0x104D, 0x2000, 0x4200, 0x5F00
```

### Filter table: UNCHANGED from stock C120 values

```
Rows 1-5: 0x00C0, 0x011A, 0x011A, 0x011A, 0x011A, 0x011A, 0x011A, 0x011A, 0x011A
Rows 6-7: 0x009F, 0x0108, 0x0108, 0x0108, 0x0108, 0x0108, 0x0108, 0x0108, 0x0108
```

### Speed clamp: 0x0001 (near 0 kph minimum steering speed)

---

## SPECIFIC QUESTIONS TO EVALUATE

### Question 1: Torque discontinuity — is the jump from pt7 to pt8 too steep?

For rows 1-6, the table goes:
- pt7: 0x1200 (4,608)
- pt8: 0x4800 (18,432)

That's a **4x jump** between adjacent breakpoints. The table is otherwise smooth/monotonic through pts 1-7.

For comparison, the tested-and-working TBA-A030 (2016-2018 Civic Sedan) max torque table does:
- pt7: 0x1680 (5,760)
- pt8: 0x74BF (29,887)

That's a **5.2x jump** between adjacent breakpoints, and it's reportedly working fine.

The TBA-C020 (2019 Civic Sport) uses a fully linear ramp with no discontinuity at all:
- pt7: 0x5577 (21,879)
- pt8: 0x7732 (30,514)

**Is our 4x jump safe? Is it smoother or more aggressive than the proven TBA-A030 approach? Could this discontinuity cause the EPS to behave unpredictably at the transition?**

### Question 2: Are the proposed values within safe bounds?

- Maximum value in our table: 0x6200 (25,088)
- 16-bit signed integer max: 0x7FFF (32,767)
- TBA-A030 proven max: 0x7FFF (32,767)
- TBA-C020 proven max: 0x7FFF (32,767)

Our peak is 76.6% of the absolute maximum, and well below values that are proven on similar Civic hardware. **Are there any mathematical overflow, signedness, or boundary concerns with 0x6200?**

### Question 3: Does leaving filter tables stock actually avoid the C120 problem?

**History**: The C120 was initially added to eps_tool.py with modified filter table values at positions 8-9 (bumped from stock 0x011A to 0x0400/0x0480). A subsequent commit specifically reverted this: "dont mod filters for C120". No explanation was given, but this implies someone experienced problems.

**Our approach**: We are raising the torque table dramatically (pt8 from 0x1F80 to 0x4800, pt9 from 0x2D00 to 0x6200) while keeping filter tables completely stock.

**The concern**: The filter table controls the slew rate — how fast the EPS transitions between torque levels. Stock filters were designed for stock torque deltas (the largest stock jump between adjacent points in rows 1-6 is about 0x0800 / 2,048). We're now asking the EPS to transition through a delta of 0x3600 (13,824) between pt7 and pt8 with stock filters.

**Is this safe? Will stock filters adequately smooth the 4x torque jump? Could stock filters actually be BETTER here because they'll slow down the transition, preventing the grinding that modified filters caused? Or could the mismatch between high torque and low filter values cause its own problems?**

### Question 4: Row 7 treatment — is the curve shape correct?

Row 7 has a different stock curve than rows 1-6. In stock firmware, row 7's values are lower and have a different shape (it doesn't plateau at 0x1200 like the others).

Our proposed row 7: `0x0000, 0x06B3, 0x0B1A, 0x0CCD, 0x0E9A, 0x104D, 0x2000, 0x4200, 0x5F00`

- pt7 goes from stock 0x119A to 0x2000 (1.8x increase)
- pt8 goes from stock 0x11DA to 0x4200 (3.6x increase)
- pt9 goes from stock 0x11DA to 0x5F00 (5.2x increase)

For comparison, the existing 2.5x mod's row 7: `...0x19BE, 0x232F, 0x2CA1`

**Is the row 7 scaling proportionally consistent with rows 1-6? Should row 7's peak match rows 1-6 (0x6200) or is it correct to cap it lower (0x5F00)? What is row 7's purpose — does it represent low-speed or high-speed conditions, and does that affect what values are safe?**

### Question 5: Bricking risk assessment

**Can these torque table values brick the EPS?** Specifically:
- Are there any values that would cause the EPS MCU to crash or enter an unrecoverable state?
- If the EPS motor receives a torque command it physically cannot deliver, does it fail gracefully or hard-fault?
- Is the checksum recalculation in eps_tool.py sufficient to prevent corruption?
- If the flash partially fails mid-write, can the EPS still be communicated with for a recovery flash?
- Has anyone reported bricking a Honda EPS with bad torque table values (as opposed to bad filter values)?

### Question 6: Physical motor/hardware safety

The Honda Civic EPS motor is a brushless DC motor with a worm gear reduction. At 5.4x stock torque:

- **Thermal risk**: Is sustained 5.4x torque (e.g., parking lot maneuvering at low speed) likely to overheat the motor? Honda's stock firmware limits torque for a reason.
- **Mechanical stress**: Does the worm gear or column mounting handle 5.4x the designed assist force?
- **Current draw**: Higher torque = higher motor current. Is there risk of blowing the EPS fuse or damaging the motor driver H-bridge?
- **Practical context**: In real driving, openpilot rarely sustains max torque — it's brief pulses during turns. Does this intermittent usage pattern make sustained thermal/mechanical concerns less relevant?

### Question 7: Openpilot controller interaction with non-linear table

The torque table has a large non-linearity at pt7→pt8 (4x jump). Openpilot's torque controller assumes a relatively predictable relationship between commanded torque and delivered torque. The README warns: "Most newer controllers (Torque Controller / NNLC) work best when your delivered torque is predictable and smooth."

**How will openpilot's PID/torque controller behave when it crosses the pt7→pt8 boundary?** Will it:
- Suddenly get 4x more torque than expected, causing overshoot?
- Oscillate as it tries to control torque in the non-linear region?
- Work fine because the TorqueBP/TorqueV tuning in interface.py compensates for the non-linearity?

---

## Reference data for comparison

### TBA-A030 max (proven working, 2016-2018 Civic Sedan):
```
Torque rows 1-6: 0x0000, 0x0917, 0x0DC5, 0x1017, 0x119F, 0x140B, 0x1680, 0x74BF, 0x7FFF
Torque row 7:    0x0000, 0x0917, 0x0DC5, 0x1017, 0x119F, 0x140B, 0x2CB7, 0x74BF, 0x7FFF
Filter row 1:    0x009F, 0x0108, 0x0108, 0x0108, 0x0108, 0x0108, 0x0108, 0x05DC, 0x05DC
```

### TBA-C020 max (proven working, 2019 Civic Sport — fully linear):
```
Torque all rows:  0x0000, 0x07DE, 0x1444, 0x2355, 0x32CC, 0x4266, 0x5577, 0x7732, 0x7FFF
Filter all rows:  0x009f, 0x0108, 0x0108, 0x0108, 0x0108, 0x0108, 0x0108, 0x0400, 0x0480
```

### TGG-A120 (proven working, Civic Hatch, 2.5x):
```
Torque rows 1-6: ..., 0x1200, 0x1F80, 0x2D00
Filter rows 1-7: ..., 0x0108, 0x0400, 0x0480
```

Note: ALL proven implementations above that go beyond 2.5x (A030, C020) also modify filter tables. The C120 is the ONLY firmware where filter modifications were explicitly reverted. Our proposal is the first to attempt >2.5x torque with stock C120 filters.
