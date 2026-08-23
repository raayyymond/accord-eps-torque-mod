---
name: accord-uniform-dose-axis-exhausted-schedule-is-the-lever
description: "gp-0x6b26's Y row is signed int16 and Y[0] stock is -9830, so the uniform dose ceiling is x3.3335 - V106 at x3.0 sits at 90% of the int16 floor. x4/x5/x6 are OVERFLOW, not merely risky. The remaining degree of freedom is the SPEED SCHEDULE: Y[2] (the >=90 km/h knot) has x5.56 of room and that is exactly where the residual line is. Also refutes the 9.98% clamp-duty figure by 10-16x."
metadata:
  type: reference
---

# 🛑🛑★★★★★ THE UNIFORM DOSE AXIS IS EXHAUSTED — THE SCHEDULE IS THE SECOND AXIS

2026-08-23. Verified byte-exact from the stock and V106 images by two independent parties.

## THE ARITHMETIC
`build_v*_tva.py` writes the triple with `struct.pack_into("<3h", ...)` — **SIGNED INT16**.
```
Y[0] stock = -9830   =>  k_max = 32768/9830  = 3.3335    V106 at x3.0 = 90.00 % of the floor
Y[1] stock = -5734   =>  k_max = 5.7147
Y[2] stock = -1966   =>  k_max = 16.6673     <- room to the floor from V106: x5.56
```
🛑 **×4 / ×5 / ×6 stock-relative are int16 OVERFLOW, not "risky".** `pack_into` raises, so the
builder catches it — **but flag it before someone "fixes" it with a cast and silently inverts the
damper's sign.**

## THE SPEED SCHEDULE IS THE REMAINING DEGREE OF FREEDOM
X = **(0, 1280, 5760) counts = (0, 20, 90) km/h** at **64 counts/km/h** (cross-confirmed against the
unrelated `0xC62EA` = 320 counts ≈ 5 km/h). Delivered after Honda's LERP:
```
                  5 mph    20 km/h   50 km/h   >=90 km/h
V106            -24546     -17202    -12358     -5898     <- 4.2x WEAKER at highway
RESHAPE B       -27282     -24000    -20572    -16000        2.71x at >=90
```
**Honda tapers the term away with speed — and >70 km/h is exactly where V106's residual line
survives.** A reshape holding Y[0] fixed leaves creep clamp duty and the relay index **unchanged by
construction**, because the ±511 clamp bounds the term identically at every speed: a reshape changes
*where* the term reaches its authority, never how much it can have. That is the opposite risk
profile from another dose step.

## 🛑 THE CLAMP IS NOT THE BINDING CONSTRAINT — AND 9.98 % IS REFUTED 10–16×
Model-free: V106 is exactly ×3.0 of stock at every knot, so scaling r77's **measured wire** by 3.0
needs no model at all. **<16 km/h duty ≥ 511 = 0.643 %; S1-like 1.00 %; r78 at matched dose
0.00000.** An independent reconstruction gave 0.185 %. **Three estimates span 0.00–1.00 %. The
pre-registered ~1 % was right; 9.98 % was wrong by 10–16×.** ⇒ **~50× more clamp headroom than
assumed. The binding constraint is int16, not the clamp.**

⊕ **ASSUMPTION-FREE RELAY TEST, needs no transfer function:** if `|gp-0x6b26|` were railing, `b5`
would collapse to `(|gp-0x6ae2| ≥ 511)` with no α dependence and the duty-vs-α curve would go flat.
V106's is still FALLING at its top α decile (slope −0.097/log unit). **Not saturating.**

## 🛑 HIGHWAY α IS ~1.5–1.9× CREEP, NOT SMALLER
Measured `|gp-0x6c2c|` p99, r77 undamped: <16 = **1183**, 40–70 = 1096, **70–90 = 1836**.
Corroborated on a6: V104 1.74×, V105 1.94×. **"Creep is the worst case" is FALSE** — the reshape's
added gain lands on a *larger* input at highway, which is why a flat schedule's ≥70 cell is the
worst in every duty table (**6.2 % at 70–90 = V80 relay territory**, against ≤1.05 % for the
conservative reshape). 🛑 `accord-v80-damper-relay-and-grind1-inert`: *"does not clip" and "is not a
relay" are different statements* — V80's damper lived at 97 % of ceiling.

## SIZE A RESHAPE CONSTANT-FREE
`|b26|_X(v) = |b26|_measured(v) · Y_X(v)/Y_route(v)` — **measured wire × a ratio of two flash
tables.** No `>>24`, no `0x111`, no reconstruction, no dependence on any disputed scale constant.
Evaluate on the **per-frame delivered coefficient after LERP**, never on a uniform stock-relative k:
a flat Y is ~15× stock at the 90 km/h knot but only ~7× at 50 km/h.

Related: [[accord-v106-extinguished-the-mode-at-low-speed]] · [[accord-v107-built-reshape-b-and-tap]] ·
[[accord-v80-damper-relay-and-grind1-inert]] · [[accord-gp6b26-is-inertia-not-damping]]
