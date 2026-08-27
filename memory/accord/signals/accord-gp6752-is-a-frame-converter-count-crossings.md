---
name: accord-gp6752-is-a-frame-converter-count-crossings
description: "gp-0x6752 = -1 is NOT a stray negation - it is the DRIVER-FRAME to AGGREGATOR-FRAME converter, applied at exactly the 7 places a signal crosses between the two frames. Count FRAME CROSSINGS, never negations. This settles the K1 friction polarity: 0xC40D2 = 204 makes the wheel LIGHTER, so reverting it would make the wheel HEAVIER."
metadata:
  type: reference
---

# 🛑🛑★★★★★ `gp-0x6752` IS A FRAME CONVERTER — COUNT CROSSINGS, NOT NEGATIONS

2026-08-23. Found while auditing `accord-friction-polarity-more-friction-is-more-assist`, whose
sign chain omitted the multiply. **The memory's CONCLUSION survives; its CHAIN did not.** It was
**right for the wrong reason — two errors that cancelled** — which is worse than being wrong,
because the reasoning breaks the moment anyone reuses it.

## THE FINDING
`gp-0x6752` is applied at **exactly the 7 sites a signal crosses between the driver frame and the
aggregator/motor frame** — one factor each, no site applying it twice, no driver-frame-internal
computation applying it at all:
```
0x3B92E  FUN_0003b8f6  ld.b -0x6752 -> cVar5, used twice below
 (cVar5) FUN_0003b8f6  gp-0x6b98 (motor cmd) x cVar5 -> plant-model frame
0x3B91C  FUN_0003b8f6  ld.h -0x6abc; x cVar5 x 12 -> friction's velocity sign
0x381EE  FUN_00038148  the six aggregator lanes x POL before differencing vs MODEL
0x3668E  FUN_00036682  gp-0x4f60 x 0xC646C x POL -> aggregator lane gp-0x6b46
0x358C2  FUN_000352b4  assist-map magnitude x POL -> gp-0x6b82 -> gp-0x6b86
0x3AB78  FUN_0003aa2c  r24/r26 x POL -> aggregator addends
0x3A71A  FUN_0003a382  PID(driver-frame error) x POL -> gp-0x6ad4
```
⇒ It is a **hardware-orientation / assembly-handedness byte**, which is why it comes from a boot
config record rather than being a constant. **The golden model already NAMES it `assist_polarity`
— the kit had the right name and never joined it to the frame story.**
⚠ Scope: `gp-0x6752` has **55** `ld.b`/`st.b` sites program-wide; **7 on this path plus the
aggregator's other addends were audited.** The other ~48 (motor control, diagnostics, CAN) were not.

## ⭐ THE SELF-CHECKING ARGUMENT — use this instead of a parity count
```
u  = POL·K·(Ts - Tref)          [FUN_0003a382 @0x3A874]
Ts = P·u + Text                  [plant: the motor unwinds the torsion bar]
Ts = (L·Tref + Text)/(1+L),   L = -P·POL·K
```
**`L > 0` is forced PHYSICALLY:** at `L < 0` the loop *amplifies* `Text` by `1/(1+L) > 1` — an
anti-assist — and at `L < -1` it runs away. The car assists and does not run away. Therefore
`dTs/dTref = L/(1+L) > 0` ⇒ **`gp-0x6ad6` is a TARGET FELT EFFORT; lowering it lightens the wheel.**
⊕ **Cross-check:** this predicts `d(gp-0x6b94)/d(gp-0x6b70) > 0`, and the kit **MEASURED**
+0.2529 / +0.2565 / +0.2617 with a passing positive control. One extra or one missing negation
would have predicted negative.
⊕ **Second confirmation, no loop reasoning:** `gp-0x6ad4` has **exactly two touches program-wide** —
`0x3A8A0 st.h` (sole writer) and `0x3ACA8 ld.h` (sole reader) — so nothing can negate between them.

## THE CONSEQUENCE FOR `0xC40D2` (K1, on the car at 204 since V89; stock 102)
**Raising K1 makes the wheel LIGHTER.** It is **not** a source of the steady "excess friction"
complaint, and **reverting it would make the wheel HEAVIER — the wrong way.** It **cannot**
rate-limit a 6× LKAS command: LKAS enters via `gp-0x6b4c` directly into the aggregator; K1 only
moves the PID's *reference*. The chain's robustness comes from `d(gp-0x6b70)/d(res) = f' >= 0`
holding **everywhere**, so it never has to assume where the residual sits.
⚠ **The one honest route by which 204 could still feel bad:** Coulomb friction flips sign at every
reversal, so larger K1 = a larger **STEP at each reversal** — notchiness on turn-in, not steady
drag. Transient, unmeasured, and V89's own docstring pre-registered it. [BELIEF, structural]

## 🛑 TWO TRAPS THAT COST TIME HERE
1. **`0xC40D2` (K1, a `tp`-block scalar in the plant model, `FUN_0003b8f6`) is NOT the ×1.5 friction
   TABLE** (14 mode-record sites `0xCF6E0…0xD9A6C` behind `0xCBE74`, feeding the `gp-0x6b26` lane)
   that V73 introduced and V81 reverted. **Two different mechanisms sharing the word "friction."**
   V81's *"removes drag the operator is used to"* is about the TABLE and is **not** evidence about
   `0xC40D2`. Reconciling against it means reconciling against the wrong lane.
2. **`gp-0x4f62` is `d(gp-0x4f60)/dt`** (`FUN_0007e74a` @`0x7E860`, a ring-buffered N-sample finite
   difference), **not a second torque channel** — it is r24's input. The aggregator's `iVar21`
   *reads* as base assist and is not; the real base-assist map is `gp-0x6b86` (`FUN_000352b4`).

Related: [[accord-gp6752-is-negative-one]] · [[accord-friction-polarity-more-friction-is-more-assist]] ·
[[accord-steering-sign-convention-confirmed]] · [[accord-fprime-compression-explains-v89-and-v97]]
