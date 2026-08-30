# DRIVE CARD — V238, and the two builds behind it

## 🚗 DRIVE THIS ONE

```
  V238   39990-TVA,A160-V238-V235BASE-ENGAGED.LAGPOLE.8.TIGHTEN-0x13000-0x100000.rwd
         rwd    sha256 e9faa7b461c6118b...      image sha256 34ceb5aefaa9bdd5...
  BEFORE anything: kill openpilot/pandad   ->  tmux kill-server
```

🛑 **The flash decision is yours. Name the file and the bus, and I will repeat both back before
anything happens.** Nothing is flashed without that.

**While driving — the whole job:** *does the car feel acceptable?* One episode is enough and **your
verdict is final.** If it feels wrong, **stop** — that is a complete result, and no measurement
overrides it.

**Stop and say so if:**
- the **ratchet or stutter is clearly worse** than your car
- steering feels **soggy or hesitant** on a quick input — a brief delay before the assist catches up.
  This is V238's one predicted failure mode; if you feel it, the dose is too big and the next rung is
  smaller, not larger
- the wheel feels **heavier near centre** — V238 is built specifically *not* to do this, so if it
  happens the model is wrong somewhere and that is important
- anything faults, or the EPS lamp lights

**Fallbacks in order:** **V235** → **V122** (your car).

---

## ⚠ V237 has been withdrawn — it was pointing the wrong way

V237 moved this same cell **upward** on the reasoning that the lane was a direct path plus a parallel
lagged branch, so a faster pole would damp. Reading the tail of `FUN_000352b4` properly shows that is
not the structure. **V237's `.rwd` is renamed `SUPERSEDED-DO-NOT-FLASH-…` and must not be driven.**

The lane is a **blend of two versions of the same assist map**:

```
  table1 = the assist map, capped by 0xC6384                (V236's cell)
  table2 = the same map, ALSO slew-limited by gp-0x69a0     (V192's cell)

  output(f) = table2 + H_k(f) · (table1 − table2)
            = table1 at DC          (the slew limit is fully undone)
            = table2 at high freq   (the slew limit fully in force)
```

So `k` is not a branch gain. **It is the valve on how much of the slew limiter's tightening survives to
the output at a given frequency.** Raising it restores *more* of what the limiter cut at 7.79 Hz, which
*raises* the lane's gain there — more positive feedback, less damping. Backwards.

**Lowering it is Honda's own direction.** `FUN_00035b20` tightens `gp-0x69a0` when its hard-reversal
counter trips — tightening that limiter is Honda's built-in oscillation response, and V192 applied
Honda's own ratio to it once more. V238 opens the same mechanism further, through a different cell.

---

## Why V238 first

All three builds carry the same **re-aimed notch** (for the grinding) and the same **biquad-state
probe** (which answers whether that filter runs at all). They differ only in the **ratchet**:

| build | ratchet lever | what it costs you |
|---|---|---|
| **V238** | the assist-map lane's **lag pole**, 20 → 8 | **no static effort** — DC gain is exactly 1, so assist is unchanged at any steady input. The risk is a brief *delay*, not weight |
| **V236** | the same lane's **slope cap**, 2048 → 1536 | **real effort** — this one *is* a gain, so it reduces delivered assist wherever it binds |
| **V235** | none | nothing — the control both others sit on |

**V238 does everything V235 does, plus a ratchet attempt that costs no steady-state effort.**

---

## What V238 changes, in full

**Against your car: 23 payload bytes.** Everything else is byte-identical to what you drive today.

```
  0xC60A8/AC/B0/B4   the notch, re-aimed to the net-damping optimum      12 B   grinding
  0xC6906 Y[0..3]    the engaged lag pole, 20 -> 8                        8 B   ratchet
  0xC40DC            alpha2 8 -> 22, which is Honda's own value           1 B   restores a damper
  0x55DF2            the biquad-state probe on CAN 427                    2 B   telemetry only
```

**Zero of 15 command-path and authority cells differ from your car** — verified cell by cell. This
build cannot change how much steering LKAS can ask for, in either direction.

---

## The dose, and why not the floor

Honda's own reader clamps `k` to `[2, 204]`, so the range is bounded by their code, not my judgement.

```
  k     corner     |H| at 7.79 Hz    tau      how much of the limiter's cut is UNDONE at the ratchet
  20    1.554 Hz      0.1966       0.102 s    20 %   <- your car today
   8    0.622 Hz      0.0797       0.256 s     8 %   <- V238
   2    0.155 Hz      0.0200       1.024 s     2 %   <- the floor; the next rung if 8 does nothing
```

**8, not the floor.** At `k=2` the restore time constant is about a second — the assist the limiter cut
would take that long to come back, and V192's card already names the failure mode: *"watch for a brief
HESITATION replacing the ratchet ⇒ too tight."* V238 cuts the restore **2.5×** while keeping τ at a
quarter second.

⚠ **The direction is structural; the size is not.** How much this is worth depends on how hard the slew
limiter actually bites in normal driving — the clip duty — and that has **not been measured on a route.**
It could be a large effect or a small one. What is no longer in doubt is which way it points.

---

## What the probe settles, whatever else happens

The notch filter's internal state boots to exactly `0.0f`. If its enable never fires on the car, that
state stays zero for the whole drive.

- **reads identically zero** → the filter never executes, and **the whole notch axis retires** after
  56 builds of moving it around
- **reads non-zero** → it runs, and how hard it works becomes measurable for the first time

---

## Honest expectations

**Grinding:** the notch is now aimed by measurement rather than assumption — it cuts the band the lane
*and* the aggregate demonstrably pump in, while leaving the damping at your ratchet frequency intact.

**Ratchet:** thirty-plus builds never moved it, and the reason is now understood — it is
firmware-created, engaged-only, lives in **torque** rather than wheel rate, and the levers that reach it
sit in this one lane. V238 and V236 are the two ends of it: V238 changes *how much of Honda's own rate
limiting is expressed*, V236 changes *the map's slope itself*. V238 is the one that does not charge you
effort for it.

**LKAS authority:** **neither build changes it.** The only EPS-side route is the gain, and you already
rejected that on V101. There is no authority lever on this shelf, and saying otherwise would be
inventing one.
