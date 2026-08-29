# STATE archive — superseded during the notch work

A RECORD, NOT AN INSTRUCTION.

## ✅✅ **`0xCC914` IS LIVE — IT IS A BREAKPOINT VECTOR, AND THE GOLDEN MODEL'S MAP WAS SHORT ONE ARRAY**

### ⛔ THE "DEAD TABLE" CLAIM IS FULLY RETRACTED
`0xCC914` is read at **`0x34936`**: `ld.w 0xd914[r16], r15` with **`r16 = tp + mode*4`** — the identical
idiom to `FUN_0003ad74`'s 4th gain_B array at `0x3ADC2` (`tp+0xD214`). Decoder validated against that
known-live cell before being trusted.
```
   disp23 = (sext(hw3) << 7) | ((hw2 >> 4) & 0x7F)          reg1 = hw1 & 0x1F
   0x3ADC2  90 07 49 79 a4 01  ->  0x01a4<<7 | 0x14 = 0xD214   base r16   (KNOWN LIVE, validates)
   0x34936                     ->                    0xD914   base r16   (0xCC914)
```
⭐ **WHY BOTH EARLIER SCANS MISSED IT — THE BASE REGISTER IS A *COMPUTED* REGISTER.** A `mov imm32`
literal scan misses it (the other five arrays ARE literals, this one is not) **and** a tp-relative scan
misses it (`reg1` is `r16`, not `tp`). This is the recorded *"operand-text search cannot see
register-indirect writes at all"* trap in a new form: **scanning by base-register identity is
structurally incomplete.** Three encoding traps have now bitten in one session — `hw2 = (disp|1)`,
`disp > 0x7FFF` cannot be disp16, and now a computed base register.

### ✅ WHAT IT ACTUALLY IS — THE SPEED BREAKPOINT VECTOR OF A SECOND BLENDED FAMILY
`FUN_000348e0` is structurally the SAME architecture as gain_B's blender:
```
   curves[1..5] = 0xC92F4[m], 0xC93DC[m], 0xC94C4[m], 0xC95AC[m], 0xC9694[m]      (10-knot each)
   bp           = 0xCC914[m]                    <- FIVE SPEED BREAKPOINTS, record+0..+8
   speed        = gp-0x6a5e (voted vehicle speed)
   i = walk(bp, speed);  frac = (speed - bp[i-1]) / (bp[i] - bp[i-1])
   gp-0x6394[j] = lerp(curves[i][j+1],   curves[i+1][j+1],   frac)      runtime X row
   gp-0x63a8[j] = lerp(curves[i][j+0xb], curves[i+1][j+0xb], frac)      runtime Y row
```
```
   0xCC914[24/26/27] -> 0xD6B7C / 0xD7B70 / 0xD7B7C
   bp = [0, 512, 2560, 5120, 8960] counts = [0, 8, 40, 80, 140] km/h   (identical on all three modes)
```
✅ record layout obeys the **knot-count header** invariant: `hdr@+0 = 10`, `X@+2..`, `Y@+0x16..`.

### ⚠ THE MODEL'S *"flat zero at creep"* IS ONLY TRUE AT A STANDSTILL
Curve 1 (0 km/h, `0xD74D0`) has **all-zero Y**, so across 0–8 km/h the whole term is scaled by
`frac = speed/512`:
```
   2 km/h -> 25.0 %      5 km/h -> 62.5 %      8 km/h -> 100 %      of curve 2
   mode 26 curve 2 (0xD7554)  X=[0,34,101,245,499,846,1888,2966,3656,4150]
                              Y=[0,677,1052,1391,1732,1911,2204,2321,2361,2355]
```
=> **a LINEAR RAMP through the entire creep band, not a dead zone.** The golden model has been
corrected in place (`eps_chain_lanes.py`), and its **VERIFICATION CONTRACT RE-RUN: 87 symbols,
stdout 2512 bytes, sha256 `740f4bcd…` EXACT.**
⚠ **[BELIEF, NOT A LEVER YET]** a steep near-centre slope (Y 0->677 over X 0->34) times a
speed-proportional creep ramp is *suggestive* for a creep-band feel symptom, but the axis is
`gp-0x6a10` ABSOLUTE steering angle, which the kit has already REFUTED as a frequency-selective
lever. **Not proposed as a build.** What would close it: identify the consumers of `gp-0x6394` /
`gp-0x63a8` and establish whether the term is inside the 6–9 Hz loop at all.

