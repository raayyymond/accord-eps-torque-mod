---
name: accord-the-live-variant-selector-is-7-tvca4-measured-on-the-wire
description: THIS CAR'S VARIANT SELECTOR gp-0x674e IS 7 -- record 11, key TVCA4 -- MEASURED on the V276 drive (CAN 427 wire 35 = 7x5 on 46,576/46,576 frames, two independent decoders). NOT slot 1 / record 2 / TVAA1: that was a part-number ASSUMPTION in V38's docstring, never a measurement, and it was re-adopted by mistake on 2026-09-01. Slot 7 = assist-map ceiling 172 (same shape as slot 1), override taper shape A (the cliff), Kd 128. Every per-variant bank is indexed by this ONE byte.
metadata:
  type: reference
---

# THE LIVE VARIANT SELECTOR IS 7 (record 11, `TVCA4`) -- MEASURED, 2026-09-01 [EVIDENCE]

**On the wire.** V276's 427 tap sends `clamp(|gp-0x674e| * 5, 1, 1023)` (`mul 5` @`0x55E06`, `sar 0` @`0x55E10`,
floor `mov 1,r7` @`0x55E0E` -- all verified in the V276 image). Route `r2e`: **wire = 35 on 46,576 of 46,576
frames**, byte0 = 0x80. Two decoders that share no code (the kit's cache pipeline and a raw capnp read of the
`can` events) agree. 35 = 7 x 5 -> **`gp-0x674e` = 7**.

**In the table.** `0xCD000`, stride 0x24, 16 records searched by `FUN_00057f8e` (5-byte key at `gp+0x6408..0c`
vs record +0..+4, returns 0 on no match). Record 11 = `TVCA45360Y`, selector byte +0x1A = **7**.

**Three independent lines now agree:** V73's mode probe (manual mode 24 appears ONLY in row 11 --
[[reference-accord-car-is-tvca4-mode-24-26]], 2026-08-05); the V276 handoff's prediction ("selector 7 -> wire
35"); and the V276 wire itself.

## What slot 7 selects (all five banks are indexed by this ONE byte, `shl 0x2` @`0x29AAA`)
| bank | slot 7 |
|---|---|
| assist / rate-reference map `0xC9A88` -> `0xE502C` | ceiling 172 (stock), same shape as slots 1/3/6 |
| override taper `0xCBA04`/`0xCBA74` (mode==2) | shape A -- the CLIFF, X 70,72,78,80 / Y 254,234,12,0 |
| Kp `0xCB994` / Kd `0xCB7D4` | Kd = 128 |
| grab-rate gates `0xCBB54`/`0xCBC34` | flat 255 (inert) |

## Why this keeps getting lost -- and how not to lose it again
- `build_v38_tva.py` (2026-07-18) hard-codes `SETPOINT_LIVE_SELECTOR = 1` with the comment "A160 = variant slot 2
  (key 'TVAA1')". **That was an assumption from the part number.** It was falsified by V73 on 2026-08-05 and
  again by the wire on 2026-09-01, yet an agent reading V38's docstring re-derived "slot 1" as new on 2026-09-01
  and the orchestrator propagated it into a handoff and a memory before catching it.
- **Rule:** any claim about WHICH slot is live must cite a MEASUREMENT (the 427 wire or the V73 probe), never
  a part-number key. If a document says slot 1 / record 2 / `TVAA1`, it is wrong; correct it in place.
- **V278's tap carries the selector in bits 3:0 of CAN 427** -- every drive re-measures it for free. It must
  read 7. If it reads anything else, stop and re-derive before trusting any per-variant edit.

See also [[accord-variant-selector-max-is-nine]] (slots 10-27 are dead) and
[[accord-one-selector-indexes-all-five-banks]].
