---
name: reference-accord-ecu-id-variant-table
description: "The per-part-number variant table @0xCD000 (16 rows x 0x24): 5-byte ASCII key at record +0x00 (NOT +0x22), selector columns at +0x12 (gp+0x63fd assist curve), +0x16/+0x17/+0x19 (gp-0x674c/f/d), +0x1A (gp-0x674e setpoint-limit mode). A160 = slot 2 'TVAA1'. The matching HW-ID at gp-0x6408..640C is NOT in code.bin -- it is UDS-written at manufacture, so slot identity can only be CLOSED by a live read"
metadata:
  node_type: memory
  type: reference
---

The static configuration table that selects every per-variant curve set on this ECU. Load-bearing because at least two separate subsystems (LKAS setpoint limit, base-assist boost curve) index tables through bytes fetched from it.

## Layout

Table origin `0xCD000` = `tp + 0xE000` (tp = `0xBF000`). **16 rows, stride `0x24` (36 bytes).**

Row layout (offsets within the record):

| offset | absolute (slot N) | feeds | meaning |
|---|---|---|---|
| `+0x00` | `0xCD000 + N*0x24` | — | **5-byte ASCII key** (matched against this ECU's HW-ID) |
| `+0x12` | `0xCD012 + N*0x24` | `gp+0x63fd` | base-assist boost-curve family index (0..33) |
| `+0x13/14/15` | | `gp+0x63fd` | 3 failover alternates, picked by `FUN_00042746`'s 2-bit state |
| `+0x16` | `0xCD016 + N*0x24` | `gp-0x674c` | (curve-set selector) |
| `+0x17` | | `gp-0x674f` | |
| `+0x19` | `0xCD019 + N*0x24` | `gp-0x674d` | |
| `+0x1A` | `0xCD01A + N*0x24` | `gp-0x674e` | LKAS **setpoint-limit** mode (indexes `0xCB844`) |

**The key is at record offset `+0x00`, not `+0x22`.** An early read of this session used `+0x22` and produced garbled labels (`..TVA`, `..TVC`). The data values were unaffected; only the labels were wrong. Verify with: slot 0 key = `"00000"`, slot 1 = `"TVAA0"`, slot 2 = `"TVAA1"`.

## The 16 slots

| slot | key | `+0x12` (assist) | `+0x1A` (setpoint mode) |
|---|---|---|---|
| 0 | `00000` (blank default) | 0 | 0 |
| 1 | `TVAA0` | 4 | 0 |
| **2** | **`TVAA1`** <- **our A160** | **10** | **1** |
| 3 | `TVAC1` | 10 | 1 |
| 4 | `TVAA2` | 4 | 0 |
| 5 | `TVAA4` | 4 | 0 |
| 6 | `TVAA6` | 10 | 1 |
| 7 | `TVAC4` | 10 | 1 |
| 8 | `TVAA7` | 12 | 3 |
| 9 | `TVCA0` | 16 | 4 |
| 10 | `TVCA3` | 22 | 6 |
| 11 | `TVCA4` | 24 | 7 |
| 12 | `TVCA6` | 22 | 6 |
| 13 | `TWAA0` | 28 | 8 |
| 14 | `TWAA1` | 28 | 8 |
| 15 | `TWAA2` | 30 | 9 |

`TVA*` = Accord family; `TVC*`/`TWA*` = other Honda chassis sharing this firmware image.

## The selector is a FETCHED BYTE, not the slot index

A common and consequential misreading. `FUN_00057f8e` returns the matched **slot** (0-15, or 0 on no match). That slot is then used as an index to *fetch* the selector:

```
0x4271a  jarl  0x57f8e, lp          ; r10 = slot index
0x4271e  mulhi 0x24, r10, r6        ; slot * 0x24
0x42722  add   tp, r6
0x42724  ld.bu 0xe01a, r6, r8       ; fetch the byte
0x4272a  st.b  r8, -0x674e, gp      ; THE WRITE
```

So `gp-0x674e` ranges over `{0,1,3,4,6,7,8,9}` (not 0-15), and `gp+0x63fd` over `{0,4,10,12,16,22,24,28,30}` (not 0-7). Patch-surface estimates that assume "selector == slot index" will be wrong — this produced a 144-halfword estimate for a 9-halfword edit.

## *** PROVENANCE CAVEAT: the HW-ID is not in ROM ***

`FUN_00057f8e` compares each key against **this ECU's own 5-byte HW-ID at `gp-0x6408..0x640C`**. That ID is **not baked into `code.bin`** — per [[reference-accord-tva-hw-id-provenance]] it is written at manufacture via a Honda-proprietary UDS service `0x84`.

Therefore **"our car is slot 2 / `TVAA1`" rests on the part number (39990-TVA-**A1**60) resembling the key string.** It is well-supported but not statically provable. The only way to CLOSE it is a live UDS read of `gp-0x6408..640C` from the car.

**Robustness if that assumption is wrong:** every real `TVAA*` slot (1-8) yields a setpoint-limit record that is byte-identical flat-15360, and an assist curve in the *falling* family. So both current conclusions survive a mis-ID among Accord keys. The one meaningful cliff is **slot 0** (blank/no-match), which selects the *rising* assist family — ~2.8x more assist at high column torque.

Related: [[reference-accord-setpoint-limit-15360-lerp]], [[reference-accord-assist-curve-family-sport-mode]], [[reference-accord-pointer-base-audit]]
