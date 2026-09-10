---
name: accord-h1-torque-table-resolution-is-false-map-scale-is-a-gain-effect
description: The operator's colleague's hypothesis H1 ("switching between two table points; scaling loses resolution") is FALSE, tested on bytes and wire 2026-09-09. The idx quantiser is before the assist map and map-independent (1 LSB = EXACTLY 16.125736 raw 0xE4 counts -- 2^22/65025/4 -- at the live taper arm, confirmed twice independently 2026-09-09); its whole residual through the loop is 2.3-2.5 output counts at 18-22 Hz, identical in grinding and quiet windows, vs 29-41 measured counts. openpilot's only command-indexed table is the identity. Kernel of truth: scaling the map raises loop gain per command count -- a GAIN effect, not resolution. H2 (4-frame staircase) re-falsified on the same routes.
metadata:
  type: reference
---

# H1 ("torque-table resolution") is FALSE; H2 ("4-frame staircase") re-falsified (2026-09-09)

| claim | status | method |
|---|---|---|
| the index quantiser (command → assist-map index) sits before the map and is map-independent | EVIDENCE | disassembly of `0x29CB0–0x29D7C`; cal `0xC64F0` = 240 identical on stock/V112/V282/V289 |
| 1 index LSB = EXACTLY 16.125736 raw 0xE4 counts (0.394 % of full scale), using the LIVE taper arm (255) | EVIDENCE | `2^22/(255·255·4) = 4,194,304/65,025/4`, confirmed by enumerating command 0…4096; corrects an earlier pass's 16.19 (used the superseded 254 cliff arm); independently re-confirmed twice 2026-09-09 (`docs/traces/TRACE-2026-09-09-kp-kd-schedule-axis.md`, agents `reqaxis` and `scalecheck`) — same Kp/Kd schedule axis, see [[accord-kp-kd-schedule-x-axis-is-demand-index-16-125736-per-lsb]] |
| the ×4 folded into the 0xE4→idx scale is built as `shl 0x2` + `subr r0` (`FUN_00052676`), NOT a `mul` — an operand-text search for `mul` on this cell returns a false zero | EVIDENCE, new 2026-09-09 | `decompile_function`/`disassemble_function 0x52676`, `TRACE-2026-09-09-kp-kd-schedule-axis.md` §V.1 |
| the map's quantisation residual, through the loop, is 2.3–2.5 output counts at 18–22 Hz and IDENTICAL in grinding and quiet windows | EVIDENCE | staircase-minus-continuous LERP residual on r39/r5e_v288, pushed through P and the gain |
| measured torque at 18–22 Hz in grinding is 29–41 counts (native 50 Hz clock) — 12–32× the residual | EVIDENCE | 427 tap, r39/r5e_v288, native-clock band integral vs the 100 Hz-interpolated figure (which understates it) |
| openpilot's only command-indexed table on the Accord path is `torqueBP/V = [0,4096]/[0,4096]`, the identity | EVIDENCE | `opendbc/car/honda/interface.py` + `carcontroller.py` on the operator's fork; every other `np.interp` in `latcontrol_torque.py` is indexed by speed or lat-accel |
| the command never dwells: 96–99 % of 100 Hz frames change; ±1-alternation and two-value 100 ms windows ≈ 0.000 in every stratum | EVIDENCE | re-confirms the 2026-09-07 wire study on r39/r5e_v288 AND on r62/r63 — H2 re-falsified |
| f0 of the grinding line is pinned 20.03–20.08 Hz across map scale (×2/×6), Kp (248–696), and idx bin-crossing rate; uncorrelated with the bin-crossing rate (ρ 0.00–0.18) | EVIDENCE | 9-route/5-build mode-nature census; wrong direction and wrong invariance for H1's mechanism |
| V288 made every setpoint step ~11× finer (a direct test of H1's mechanism) and the grinding did not move | EVIDENCE | `GRIND1-CENSUS-V288-R5E-2026-09-08.md`: 258 vs 239 ep/h, f 20.06 vs 20.03 |
| the quantiser is sign-asymmetric near centre (index 1 reached at command +1 one direction, −17 the other) | EVIDENCE, new finding | enumeration of command 0…4096 through the decode; too small and static to tone, not previously documented |

**Why it matters:** closes a plausible-sounding non-mechanism for the grinding, and sharpens the real lever (loop gain, not table resolution). See [[accord-v289r1-flew-the-ring-moved-to-16hz-revert-signature]] (same session, same routes).

**How to apply:** if H1 or a variant (table dithering, index resolution, LERP jitter) is proposed again, cite this falsification — the residual-vs-tap ratio (12–32×) and the V288 null (11× finer steps, no change) kill it fastest. The gain-effect kernel of truth (scaling the map raises loop gain per command count) is a real, separately tracked lever — do not conflate the two when explaining this to the operator.
