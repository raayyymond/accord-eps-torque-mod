---
name: reference_accord_v86_prep_plantmodel_c64c8_boost_lerp2_closed
description: V86-prep session (2026-08-08/09, ghidra-factord) — full plant-model cal block inventory with stock values, 0xC64C8/0xC64C9 aggregator-mode-selector values, and the boost LERP2's mode-24/25/26/27 re-derivation (closing a long-open item, band0 flat zero on the live modes too).
metadata:
  type: reference
---

[Session note: GhidraMCP `decompile_function`/`disassemble_function`/`search_instructions`/`read_memory`
never registered as callable this session — only the static bridge tools did, despite `check_tools`
reporting them "callable" server-side. Everything below is either cited from a fresh 2026-08-08 decompile
recorded in the golden model/repo memory, re-verified here with Python LE byte reads of
`stock_fw_dump/code.bin`, `_v84_..._plain_image.bin`, `_v85_FRICTION.C40BC.6000-..._plain_image.bin`; or
new Python-only pointer-chase work, validated against a known-published baseline (mode 10) before being
trusted for the live modes. See [[feedback-ghidra-tool-registration-can-silently-fail]].]

## 1. The plant-model cal block (`FUN_0003b8f6`, 1 kHz), full inventory with STOCK values

All of these are read every cycle by the 1 kHz plant-model observer that V85 partially dosed
(`0xC40BC` 600→6000). Byte-identical STOCK=V84=V85 except `0xC40BC` itself. 0 writers, 0 monitor readers,
for every cell — confirmed by grep of all `build_v*_tva.py` (prior session) + this session's Python read.

| addr | physical meaning | stock (=V84) | V85 |
|---|---|---|---|
| `0xC40BC` | relay saturation threshold, `ratio=clamp(rate*12/cal,±1)` | 600 | **6000** |
| `0xC40D0` | FRICTION EMA alpha, /4096 | 408 | 408 |
| `0xC40D2` | FRICTION `\|model\|` coefficient, /1024 | 102 | 102 |
| `0xC4080` | FRICTION ratio-only additive term, /1024 | 0 | 0 |
| `0xC40D4` | command-branch EMA2 alpha (2-pole LPF), /4096 | 573 | 573 |
| `0xC40D6` | INERTIA EMA2 alpha, /4096 | 246 | 246 |
| `0xC40D8` | sensor-branch EMA2 alpha, /4096 | 3686 | 3686 |
| `0xC646E` | INERTIA scale numerator, ×2⁻²⁴ | 1428 | 1428 |
| `0xC613A` | sensor-branch FIR scalar, /32768 | 1159 | 1159 |
| `0xC6468` | final scale into `gp-0x6bfc` (float here; Q10 in `FUN_00038148` — dual-convention trap) | 2639 | 2639 |
| `0xC4048/4C/50` (f32) | command-branch FIR coeffs c1/c2/c0 | 1.0/0.0/0.0 | unchanged |
| `0xC6B66`/`0xC6B80` | gp-0x6a10 LERP, 13pt bare arrays, sensor-branch shaping | see FactorD memory | unchanged |

`0xC646E` (INERTIA's only gain knob) is flagged as the cleanest untouched lever in this block if V86 wants
more of it: per the golden model it's a genuine rate-proportional (not relay) term, "positive real part
7.79-28.5 Hz", running at only 1-6% of its own ±10 clamp — headroom without V80's relay-class risk.
NOT sized, NOT priced against GATE 2, just flagged as structurally clean. `0xC40D4`/`0xC40D8` are the two
poles setting how well the command-branch and sensor-branch models track for the Path-2 subtraction.

## 2. `0xC64C8`/`0xC64C9` aggregator mode selector, values confirmed

[EVIDENCE, Python this session, all three images] `0xC64C8`=0 (pass-through, live path), `0xC64C9`=0
(blend mux), `0xC61D4`=0 (the mode-1 static replacement — **currently 0**, so mode 1 today is equivalent
to hard-zeroing the entire aggregator contribution, not "replace with a tuned value"), `0xC61DA`=1092
(Q15 blend scale). All byte-identical STOCK/V84/V85. Zero hits as an edit target in any `build_v*_tva.py`
(grep-confirmed). Reader per the 2026-08-08 decompile: `FUN_00042af8` @`0x431CC`, single static site, 0
runtime writers. Mode 2 blends toward the static cal, clamp ±0x3000 — formula not fully characterized,
would need `disassemble_function(0x431CC)`.

## 3. Boost's `gp-0x6a10` LERP2 — the THIRD consumer, re-derived for modes 24/25/26/27 (closes an open item)

Prior open item (`reference_accord_near_centre_structure_hunt_angle_tracking_chain_found.md`,
`reference_accord_factord_six_family_map_and_1khz_lane_v84.md`): `FUN_00034a72` (boost, same 100 Hz task
as FactorD's evaluator) reads `gp-0x6a10` as an index into a SPEED-BLENDED RAM buffer (`gp-0x6394`-family),
built from 5 mode-indexed pointer-array families, traced ONLY for mode 10 (which this car doesn't use).

**Method**: pure Python pointer-chase, no Ghidra. Validated by reproducing mode 10's already-published
values EXACTLY before trusting the same method for modes 24-27 (mode-10 speed axis `0xD2B64`, band0
`0xD24A4`, band1 `0xD2528` all matched the prior session's decompile-sourced numbers byte-for-byte).

```
Speed axis pointer array:  0xCC914 + mode*4  ->  bare 5×i16 array (no count header), same for every mode:
                            X = [0, 512, 2560, 5120, 8960] counts = [0, 8, 40, 80, 140] km/h
Band pointer arrays (mode*4 indexed, [n=10][X×10][Y×10] records):
  band0 (0-8 km/h):  0xC92F4 + mode*4
  band1 (8-40 km/h): 0xC93DC + mode*4
  band2 (40-80 km/h): 0xC95AC + mode*4
  band3a (80-140, table A): 0xC94C4 + mode*4
  band3b (80-140, table B): 0xC9694 + mode*4
```

Results, modes 24/25/26/27 (record addresses shift per mode but X arrays are identical across all
modes/bands; verified byte-stock STOCK vs V85 for band0/band1):
```
band0 (0-8 km/h), ALL FOUR modes: Y = [0]*10           <-- FLAT ZERO, same as mode 10
band1 (8-40 km/h), modes 24≡26:   Y=[0,677,1052,1391,1732,1911,2204,2321,2361,2355]
band1, modes 25≡27:               identical to 24/26
band2 (40-80 km/h), 24≡26: Y=[0,376,760,968,1168,1272,1327,1370,1437,1455]; 25≡27: Y=[0,363,729,925,1118,1224,1275,1318,1377,1396]
band3a (80-140 A), 24≡26: Y=[0,434,824,1093,1289,1443,1583,1699,1760,1790]; 25≡27: Y=[0,412,780,1035,1225,1371,1504,1614,1672,1701]
band3b (80-140 B), all 4 modes: Y=[0,310,512,630,723,766,789,810,907,914]  (24/25/26/27 all identical here)
```
🛑 **New pairing pattern, not previously documented**: for the boost band tables specifically, modes pair
as (24,26) and (25,27) — NOT a simple "engaged vs manual" split matching FactorC/D's own 24≡26 flat
identity, but a genuine four-way structure where two DIFFERENT column-pairs each carry their own (but
mutually-identical-within-pair) shape. Consistent with, not contradicting, `accord-stock-mode24-equals-
mode26-damper-is-ours.md`'s "stock ships zero engaged/manual differentiation" finding — it just extends to
a second dimension (25/27) not previously characterized for this table.

**Verdict**: band0's flat zero across ALL FOUR live modes means this THIRD `gp-0x6a10` consumer is ALSO
structurally dead exactly at creep speed (grind #1 / the ratchet, ~5 mph ≈ 6.4-8 km/h, sits inside or at
the edge of band0's speed-blend window, `fraction = speed/512`). Three independent `gp-0x6a10` readers
(FactorD, this boost LERP2, and the 1 kHz table in `FUN_0003b8f6`) now all confirm zero/near-zero
contribution at the creep operating point — convergent, not a coincidence of one table.
⚠ The exact combination formula (`r28 = r28 * LERP2(...)` — multiplicative gain vs additive, any offset)
is only a ONE-LINE partial trace from the source session, explicitly not chased to completion. Do not size
a lever off it without a fresh decompile of `FUN_00034a72`'s consumption of the LERP2 output.

## Related
[[reference_accord_factord_six_family_map_and_1khz_lane_v84]] — the FactorD/1kHz-table map this session
re-verified against V85 specifically (byte-stock, unchanged).
[[reference_accord_near_centre_structure_hunt_angle_tracking_chain_found]] — source of the boost LERP2
mechanism and pointer-array addresses, mode-10-scoped; this file's §3 is the mode-24/25/26/27 closure.
