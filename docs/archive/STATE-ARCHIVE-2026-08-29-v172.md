# STATE archive — superseded when V172 was cut

A RECORD, NOT AN INSTRUCTION.

## ✅✅✅ **V162 / V163 BUILT — THE RESONANCE PID GETS ITS AUTHORITY BACK AT CREEP**
`0xC67C4` **1280 -> 512**, ONE HALFWORD, a **VIRGIN CELL**. 55/55 assertions each, CRC 50/50.
```
   V162  base V122  SINGLE VARIABLE   image 423711bf0f10b21f7ddce3e21d35cf390d93054c25ebed1075eb0572cb02d299
   V163  base V160  STACKED best-shot image 9487dc15f68a3a876ec70509d01167c9db9c8e328e9c003fa85dff94388ce0d6
```
### ⭐ THE GOLDEN MODEL NAMED THIS LEVER, AND IT IS AIMED AT THE RATCHET SPECIFICALLY
The model's elimination is explicit — *"for 52–70 % of the return the LKAS lane is a DC CONSTANT, yet
the 6–9 Hz |tq| envelope is unchanged … A constant cannot carry 7.8 Hz => **THE RINGING ENTERS THROUGH
A SENSOR-FED LANE, NOT THE COMMAND LANE.** Excludes every command-side lever and leaves {r24/r26,
gp-0x6ad4, gp-0x6b26, gp-0x6bbe, the V89 plant-model path}."* — and of those survivors it singles out:
> *"LIVE `gp-0x6ad4` resonance PID — **the most reachable authority of any gated lane HERE** … 🛑 V56's
> mute of this lane was scored at ~21 Hz — **the lane has NEVER been scored at 6–9 Hz, so it is OPEN,
> not eliminated.**"*
⚠ **THIS OVERTURNS A MEMORY.** `accord-v56-flashed-mute-null-and-costs-damping` records
`gp-0x6ad4`/`FUN_0003a382` as **eliminated**. An elimination scored at **21 Hz does not eliminate a
6–9 Hz role**, and the ratchet is 6–9 Hz. The model is the authoritative reference and it addresses
this directly. **Treat the memory's "eliminated" as scoped to ~21 Hz.**

### ✅ THE ARITHMETIC, READ FROM THE BYTES
`0xC67BE` = `(0, 3)` knot-count header; X@`0xC67C2`, Y@`0xC67C8`; axis = voted speed `gp-0x6a5e` @64 ct/km/h.
```
   stock  X = [128, 1280, 3200] = [2, 20, 50] km/h     Y = [0, 1024, 1024]

     speed     stock -> new     ratio     note
      2 km/h       0 ->    0    --        parking protection INTACT (X[0] untouched)
      3 km/h      56 ->  170    x3.00
      5 km/h     170 ->  512    x3.00     <- the ratchet's own band
      8 km/h     341 -> 1024    x3.00
     12 km/h     568 -> 1024    x1.80
     20 km/h    1024 -> 1024    --        UNCHANGED; edit confined to the creep band
```
=> **the lane whose job is to damp resonance is throttled to ~1/6 of its authority exactly where the
ratchet lives.** ✅ The model's own quoted 164–341 for the 4.9–8.0 km/h ratchet episodes **reproduces
from these bytes exactly** (170 at 5 km/h, 341 at 8 km/h) — two independent derivations agreeing.

### ✅ WHY THIS DIRECTION IS THE SAFE ONE
**[EVIDENCE]** It **RELEASES** authority and never removes any — the ceiling is ≥ stock at every speed.
**[EVIDENCE]** `X[0]=128` UNTOUCHED ⇒ at/below 2 km/h the ceiling stays **exactly 0**; Honda's
standstill/parking protection is byte-for-byte intact. **[EVIDENCE]** ≥20 km/h **nothing changes**.
**[EVIDENCE]** **Y is UNTOUCHED** — the ceiling's VALUE stays Honda's own 1024; only the SPEED at which
it is reached moves. **Honda already runs this lane at FULL authority above 20 km/h and the car does
not ratchet there**, so this moves creep TOWARD a known-good configuration rather than into new
territory. **[EVIDENCE]** the axis is **VEHICLE SPEED** — seconds-scale ⇒ **cannot modulate at 6–9 Hz**,
so the parametric-pump failure mode governing every rate-axis edit does not apply.
**[EVIDENCE]** `0xC67C4` is **VIRGIN**: `(128, 1280, 0)` on **all 161 build images** ⇒ no interaction
with any historical edit. **[EVIDENCE]** X stays strictly ascending, no collapsed knot (a zero-width
LERP segment divides by zero — asserted).

### ⚠ THE ONE REAL RISK
**[BELIEF]** that `gp-0x6ad4`'s **PHASE** is favourable at 6–9 Hz. It is a resonance controller, but its
design target may be the ~21 Hz mode, and **a controller phased for 21 Hz can have the wrong phase at
7.8 Hz — in which case MORE authority makes the ratchet WORSE.** This cannot be settled statically;
the lane has never been scored at 6–9 Hz, which is exactly why the model calls it OPEN.
⊕ **Mitigation**: the change is confined to 2–20 km/h and reverts to stock above, so any adverse effect
is **bounded to the creep band** and is felt immediately at low speed, not discovered at highway speed.
⊕ If worse, the diagnosis is unambiguous and the revert is one halfword; `X[1] = 768` (12 km/h) gives a
**2x** rather than 3x release.

