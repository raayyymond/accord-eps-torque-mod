# STATE archive

A RECORD, NOT AN INSTRUCTION.

## ⛔ **THE AUTHORITY COLLAPSE CURVE ADMITS NO BENEFICIAL CHANGE WITHIN THE SAFETY RULE**
Open item closed by exhaustive test, not by argument.
```
   mode 7, ALL FOUR RECORDS VIRGIN on 90 images
     0xE547C / 0xE5404  primary  X = [70, 72, 78, 80]   Y = [254, 234, 12, 0]
     0xE52FC / 0xE5284  blend    X = [32, 42, 80, 112]  Y = [255, 255, 255, 0]
   authority 254 -> 0 across TEN byte-counts (raw torque 2240 -> 2560)
   🛑 measured MEDIAN OVERRIDE TORQUE = 2235 = byte 69 -- ONE COUNT below X[0] = 70
```
=> **the operator drives on the knee**, so a small road-load increase tips him over a cliff that
drops authority 254 -> 12 in eight byte-counts. That is the “authority disappears” mechanism.

### ⛔ EVERY RESHAPE THAT HELPS VIOLATES THE RULE
The rule is **MONOTONE-NON-INCREASING: never more authority than stock at any torque.** Tested:
```
   hold longer     X=[74,76,78,80]     VIOLATES (254 vs 234 at byte 72, and above stock to byte 79)
   gentler slope   X=[70,72,88,90]     VIOLATES (150.8 vs 12.0 at byte 78)
   raise mid Y     Y=[254,234,120,0]   VIOLATES (120.0 vs 12.0 at byte 78)
   collapse earlier X=[60,70,78,80]    LEGAL -- but gives LESS authority everywhere
```
✅ **[EVIDENCE] this is not an argument, it is an enumeration**: authority is a monotone-decreasing
function of torque, so *holding it up longer anywhere* IS *more than stock somewhere*. The two are the
same statement. **No legal change improves it.**

### ⚠ THE TRADE, STATED FOR THE OPERATOR — NOT DECIDED HERE
Honda collapses authority **because the driver is pushing**; the curve is a driver-in-control override.
Raising it means **the driver must push harder to take the wheel back.** That is a genuine safety
trade, and it is the operator's call, not the kit's. If he wants it, the minimal bounded form is
`X[0]/X[1]` **70,72 -> 72,74** (two byte-counts ≈ 64 torque counts of extra hold, nothing else moved),
which is the smallest change that moves the knee off his median override torque. **NOT BUILT.**

### ⛔ AND THE `0xC61BC` CAVE PROBE IS NOT WORTH IT RIGHT NOW
It is a **probe, not a fix** — diagnostic value only — and caves are this kit's **only bricking class**
(V24, V27, V48B all bricked the ECU). With the calibration search exhausted and V158 ready to fly,
spending a brick risk on a measurement before the cheap measurement (a drive) has been taken is the
wrong order. **Revisit only if the V158 drive is ambiguous AND the operator authorizes a cave.**

