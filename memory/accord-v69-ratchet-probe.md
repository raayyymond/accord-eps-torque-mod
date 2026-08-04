---
name: accord-v69-ratchet-probe
description: "V69's probe is re-aimed from the exhausted grind detector to three RATCHET candidates — the aggregator's own hard nonlinearities — because ~7.4 Hz is the only symptom a 100 Hz channel can resolve."
metadata: 
  node_type: memory
  type: project
  originSessionId: afe7e152-cb42-4ab4-922a-42b0e91a5421
  modified: 2026-08-04T04:35:31.656Z
---

★★★ **V69's `0x14A` byte4 probe reads RATCHET candidates, not the grinds.** Operator instruction,
2026-08-04. Decoder `rlog-tools/decode_v69_ratchet.py`, linked mechanically — the build **fails** if
its `CAVE_HEX` is not byte-for-byte the built cave.

**TWO REASONS, and the second is the stronger one.**
1. The grind detector is **exhausted**: `gp-0x67df` has **never been observed non-zero in this kit**
   (0/53,991 on V68, 0/186,321 on V67, straight through the captured 28 Hz burst). With no positive
   control that null cannot separate "no oscillation" from "detector disabled / input dead" —
   see [[accord-v68-detector-still-zero-no-positive-control]].
2. ★ **The ratchet is the one symptom this channel can RESOLVE.** At ~7.4–7.6 Hz a 100 Hz probe gets
   **~13.5 samples/cycle**, so each bit's *own time series* carries the line. At grind #1 (21 Hz) and
   grind #2 (43 Hz) it never could — every prior probe could only report duty.

**WHY THESE THREE CELLS.** The ratchet is **symmetric + amplitude-saturated** (skew −0.16…+0.06 vs a
−3.27 sawtooth calibration) ⇒ the describing-function signature of a **hard nonlinearity in the
loop**. V65 killed the obvious one — the aggregator SUM `gp-0x6b94` never rails (120,049 frames). ★
**What that null never covered is each lane's OWN nonlinearity upstream of the sum**: eight ZERO-type
range gates (out-of-window contributes **0, not clipped** — a crossing is a *step*) plus two
saturating lane clips. **None has ever been measured.**

| bit | cell | ≥ +4096 means | why it is a top candidate |
|---|---|---|---|
| 7 | — | liveness | field == 0 ⇒ VOID |
| **6** | `gp-0x6ada` | top half of its ±0x2000 **saturating clip** | **r24's lane output** — the damping lane the record points at *and* the lane V69 scales. **0 readers / 1 writer** ⇒ zero blast radius. Duty = **rail-proximity meter**, which prices V69's ×4 dose on-car. See [[accord-aggregator-lane-mirrors-6ada-6adc]] |
| **5** | `gp-0x6b62` | half its ±0x2000 **ZERO gate** | **the operator's own hypothesis, never probed in 69 builds.** Return-to-centre: `FUN_00036388`, a slow ±1/tick accumulator **with hysteresis** |
| **4** | `gp-0x6ad4` | 40% of its ±0x2800 **ZERO gate** | the **unfiltered** residual lane (`FUN_0003a382`, raw derivative on the torque sensor straight into the aggregator), gain LERP-indexed by `gp-0x671a` ⇒ **closes a loop from Honda's own detector back into assist**. Live hands-off, which the boost lane is not |
| 3 | — | **constant 0** | V69 build class. V68 emits bit3 = 1 in **100.000%** of 53,991 frames ⇒ V68 excluded absolutely |

**bit6 was freed from the LKAS gate** to buy the third rung: `gp-0x6806` ≡ `latActive` at 99.983%
(150,327 frames), `0x18F` b4 bit3 and `0xE4` byte2 bit7 at 99.94–100%, and V69 *reverts* the gate so
that cell steers nothing on this build — see [[accord-lateral-engagement-signals]].

**BUDGET IS THE DESIGN CONSTRAINT.** Proven cave 68 B; prologue 4 + epilogue 20 leaves **44 B**; a
signed-halfword rung is **14 B** (`ld.h` 4 + `sar 0xc` 2 + `cmp 0x1` 2 + `blt +6` 2 + `movea` 4).
3 × 14 = 42 ≤ 44; a fourth needs 56. **Three rungs is arithmetic, not preference.** Growing the cave
is the only bricking class (V24/V27/V48B).

🛑 **THREE RESIDUALS, ALL REAL.** **(1) ONE-SIDED** — positive side only; a null bounds only that
lane's POSITIVE excursions, never quote it as two-sided. **(2) NO POSITIVE CONTROL on bits 5/4** —
only bit6 is expected to fire on any drive; **if bit6 also reads 0.000%, check bit7 and the `.rwd`
name BEFORE interpreting bits 5/4** (the V64 lesson, [[feedback-probe-the-gate-not-just-the-output]]).
**(3) V69-vs-V66/V67 is NOT structural** — those also emit bit3 = 0 with bits 5:4 measured 0 over
186,321 frames, so `{0x87, 0xC7}` ⊂ V69's payload space.

⚠ **CONSIDERED AND NOT TAKEN** (do not re-propose): `gp-0x6bbe` boost (±0x800, narrowest live gate)
is **driver-torque indexed** and the ratchet is hands-off; `gp-0x6bd0` damping (±0x800) has f5 = 0 at
both operating points on a **static** claim — **first cut if a rung frees up**; `gp-0x6b4c` is
already on CAN `0xE4`; `gp-0x4f62` (r24's input) is rung 4 if the cave ever grows.

Part of [[accord-v69-built-speed-shaped-rate-lane]].
