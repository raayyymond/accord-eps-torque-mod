# HANDOFF 2026-09-01 — THE REFERENCE, SCALED 6x (V276)

**Artifact:** https://claude.ai/code/artifact/52f1483a-0720-49df-bc96-238537170973

## The headline

**LKAS commands a RATE, not a torque.** The assist map `0xC9A88` is that rate loop's REFERENCE and it
ceilings at ~23 deg/s. **Every build since V38 moved how hard the loop pushes; none ever moved what it
asks for.** That is the mechanism behind the operator's standing report that *"the angle rate doesn't
scale with the torque"* — more gain bought faster acceleration to the same ceiling, never a higher one.

`0xC9A88` and `0xC62E6` have **never been flown in any build** (verified: grep of every
`build_v*_tva.py` and the lever index).

## V276 — BUILT, NOT FLOWN

```
image f4ea35df1051db25736cd52710dfb8af194d4f74ecfd798d77ba026a7ff5e846
rwd   6c4542b0ff6edce1c2eda37befae6933497a2c672703547e8d1489472fa86f08
660/660 assertions · 457 changed bytes, 4 of them code · FUN_00028ea6 BYTE-IDENTICAL
```
| edit | cell | change |
|---|---|---|
| reference | `0xC9A88` ×28 records | every Y knot **exactly 6×**, Honda's shape preserved. 180 → 1080 |
| measurement | `0xC62E6` | 7680 → 46080. Honda's setpoint:feedback ratio **1.395 preserved exactly** |
| telemetry | `0x55DF2-3`, `0x55E10`, `0x55E0E` | CAN-427 → `gp-0x674e`; sar 3→0; clamp floor 0→1 |

**FROZEN AND ASSERTED:** Kp `0xCB994`, Kd `0xCB7D4`, gain `0xC6CD0`=5346, output clamp `0xC61B4`=3072,
P/sum/D/I clamps, all 112 override-taper records.

**Torque is NOT raised.** Peak 2441→2505 (+2.6 %). The frozen P clamp enforces the cap structurally:
`(15360 × 5346) >> 15 = 2505`, whatever the map does. Max LKAS torque stays **6× stock**.

## Three builds died to get here — all passed their own assertions

- **V273/V274** — froze torque CELLS believing that froze TORQUE. The map scales the ERROR feeding Kp,
  so P saturated over ~80 % of range. The defending assertion read two already-frozen cells: a tautology.
- **V275** — divided Kp/Kd by 6 to compensate. `E = 32*sp − fb`, and **fb is measured and does not
  scale**, so the compensation preserves the feedforward half and leaves the FEEDBACK half 6× weaker.
  At the point where V268 delivers 0 torque, V275 delivered 2034. The loop stops nulling.
- **The taper flatten**, carried in both, is **upstream** — it produces the demand index — and its
  companion cutoff `0xC64B8`=255 is unsatisfiable, so the taper reaching Y=0 is the ONLY live mechanism
  that zeroes the command. The operator's median override torque sits ONE COUNT below its first knot.

## Facts established this session

- ⭐ **ONE selector indexes ALL FIVE per-variant banks** — `gp-0x674e`, `ld.bu` at `0x29AA0`/`0x29B7C`/
  `0x29CC4`, `shl 0x2` at `0x29AAA`. `gp+0x63fd` never appears in `FUN_00028ea6`. So the CAN-427 tap
  settles map, Kp, Kd AND both taper banks at once.
- ⭐ **The record-numbering ambiguity is RESOLVED.** Table base is `0xCD000`, stride 0x24, string-first.
  Record 2 is named `TVAA1` **and** carries selector 1 → wire **5**. Record 11 = `TVCA4`, selector 7 →
  wire **35**. Name and index sit on the same row; there was never a 0-vs-1-based conflict.
- ⭐ **The ×8 counts-per-deg/s factor is now EVIDENCE.** `rate_c` on CAN tracks the steering-angle
  derivative at **slope 0.9725, corr 0.980, n = 28,940**. The packer emits `(-gp-0x6a56) >> 3`, so
  `gp-0x6a56` is 8 counts/deg/s.
- **D acts on Δ(FULL ERROR)**, not Δsetpoint — `0x29D76 shl 0x5` / `0x29D78 sub r26,r16`. With Kd=128
  it saturates at |Δsetpoint| > 20 counts, so **D probably already rails routinely on the car**.
- 🛑 **`0xC61B4` AND `0xC61BE` each have EIGHT tp-form readers in TWO output stages, not four**, each
  with one sign-extended read. The second stages (`0x2A910..`, `0x2B024..`) sit in code Ghidra never
  made a function — **invisible to every xref census**. Found by raw byte scan.
- **EME has no rate axis** — every term in the fault word at `FUN_00042af8` is a magnitude comparison
  or an int/float lockstep residual. `gp-0x4f64` is a dynamic MAGNITUDE limit (>= 0x2801 forces zero),
  not a rate limit. STATE.md's EME gate is discharged **on the rate question**.
- **`FUN_0002a93a` is DEAD** by three independent methods (controlled jarl/jr disp22 scan, 32-bit
  pointer-word scan, Ghidra xrefs) — so the map ×6 landing in it is harmless.
- ⚠ **Trap for future taps:** `0x55DF0` is `ld.h` (16-bit) reading a BYTE cell, so it silently ORs in
  `gp-0x674d`. All 16 records hold 0 there, so V276's tap is clean — but the next one may not be.

## The drive

Endpoint is **CAN 399 bytes 2–3 (`STEER_ANGLE_RATE`)**, already free at 100 Hz, ±12000 clamp — confirm
the new regime fits under it. The 427 tap answers the record question from any drive, parked included.
🛑 **The drive must ENTER the regime**: alternating gentle and hard corrections at 5–15 mph. Steady
cruising never approaches the old ceiling and would produce an uninterpretable null.

**RISK:** in fast-steering, high-command moments the lane will PULL where it used to RESIST. Above
demand index ~40 at standstill P sits at its clamp, so fine command resolution is lost there.
**Assess stationary or at low speed first.**

## Open

1. The 6-byte extended-displacement gp-relative form — every "zero readers" null this session is a
   disp16 null. Needs a decoder positive-controlled against a known extended-form site.
2. What writes `gp-0x4f64` (`0x7C2E2`/`0x7C3B4`/`0x7C47C`) — bounds magnitude, not rate.
3. The loop period. `FUN_0002214a` is TCB0 of a **six**-entry OSEK task array at `0xBB920`, stride 0x30,
   base pointer at `0xBB7EC`. No per-record period field. Needed to convert D's per-frame saturation
   threshold into a real steering rate.
4. Golden model **NOT updated** for the rate-loop findings — the 87-symbol / SHA256 contract needs a
   dedicated pass.
