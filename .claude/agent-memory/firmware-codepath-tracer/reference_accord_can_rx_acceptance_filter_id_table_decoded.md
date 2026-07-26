---
name: reference_accord_can_rx_acceptance_filter_id_table_decoded
description: A160 CAN RX acceptance-filter ID table at 0xB733C decoded (ID = word>>18), self-calibrated on the known LKAS ID 0xE4; proves the EPS accepts WHEEL_SPEEDS 0x1D0 and ENGINE_DATA 0x158. Parallel dest-buffer table at 0xB739C; index-pairing NOT yet verified.
metadata:
  type: reference
---

# CAN RX acceptance-filter ID table — DECODED (2026-07-24)

Closes the "next step to actually close this" written in
[[reference_accord_can_1d0_wheelspeed_dtc_names_no_decoder]] — that memory asked for exactly this
calibration and it now succeeds.

## The encoding: `CAN_ID = word >> 18`

Table base `0xB733C` (= `tp-0x7cc4`), **24 u32 entries** spanning `0xB733C..0xB739B`.
[VERIFIED: raw Python byte read of `code.bin`; offset == address.]

**Self-calibration**: entry `[22]` = `0x03900000` → `>>18` = `0x0E4` = the known LKAS
`STEERING_CONTROL` ID. The full decoded set is in **strictly descending ID order** and is
recognizably a Honda RX list, which independently validates the shift.

| idx | ID | dest word @`0xB739C+4i` | Honda DBC |
|---|---|---|---|
| 0 | `0x2636`* | `0xFEDF6B88` | ANOMALOUS |
| 1-3 | `0x78E`,`0x75A`,`0x72A` | `0xFEDF6C10/6C18/6B98` | ? |
| 4 | `0x26FF`* | **`0xFEDF6B00` = `gp-0x1500`** | ANOMALOUS |
| 5-8 | `0x6FA`,`0x3A1`,`0x374`,`0x328` | `0xFEDF6BA0/6AF8/6BA8/6C00` | ? |
| 9 | `0x326` | `0xFEDF6BB0` | SCM_FEEDBACK |
| 10,11 | `0x324`,`0x305` | `0xFEDF6BB8/6BC0` | ? |
| 12 | `0x1EA` | `0xFEDF6BD0` | VSA/ADAS |
| 13 | `0x1DC` | `0xFEDF6BE8` | ? |
| **14** | **`0x1D0`** | **`0xFEDF6BF0`** | **WHEEL_SPEEDS (4×15b, 0.01 kph)** |
| 15,16 | `0x1B0`,`0x1A4` | `0xFEDF6B08/6B10` | VSA_STATUS (0x1A4) |
| 17 | `0x198` | `0xFEDF6BD8` | ? |
| 18 | `0x17C` | `0xFEDF6BF8` | POWERTRAIN_DATA |
| **19** | **`0x158`** | **`0xFEDF6B58`** | **ENGINE_DATA (XMISSION_SPEED)** |
| 20,21 | `0x13C`,`0x130` | `0xFEDF6B90/6B68` | ? |
| **22** | **`0x0E4`** | `0xFEDF6B80` | **STEERING_CONTROL — the calibration anchor** |
| 23 | `0x094` | `0xFEDF6B40` | ? |

\* `[0]`=`0x98DBEFF1` and `[4]`=`0x9BFC9202` have dirty low bits (all others are clean `ID<<18`)
and their `>>18` exceeds 11 bits, so they are **not** plain standard-ID entries — mask/config/
extended-ID, unresolved.

## ★ The EPS DOES receive vehicle speed on the bus

`0x1D0` (WHEEL_SPEEDS) **and** `0x158` (ENGINE_DATA/XMISSION_SPEED) are both in the accept list.
This does NOT contradict [[reference_accord_no_vehicle_speed_in_arbitration_steerstatus3]] /
[[reference_accord_no_speed_gain_in_baseassist_feedback_loop]] — those proved no speed reaches the
*command/base-assist path*. Ingestion and use are different claims. Whether either frame is decoded
into a scalar is still **OPEN**.

## ⚠ The index-pairing is NOT verified — and the record CONFLICTS

The ID table and the dest table are materialized by `mov imm32` in **two different functions**
(`0x1d258` for `0xB733C`, `0x1de22` for `0xB739C`), so nothing yet proves `IDtable[i]` pairs with
`desttable[i]`. Under index-parallelism ID `0xE4` → `0xFEDF6B80`, but
[[reference_accord_can_1d0_wheelspeed_dtc_names_no_decoder]] asserted "slot 17 = `0xFEDF6BD8` =
the known LKAS routing", which would instead make LKAS ID `0x198`. Both `0xFEDF6BD8` (TX descriptor
entry 7, `reference_accord_can_tx_segmentB_scheduler_descriptor_table`) and `0xFEDF6B80` are tied to
`0xE4` in different tables. **Do not build on either pairing until resolved.**
Next step: disassemble the loops at `0x1d258` and `0x1de22` and read off the index expression each
uses to walk its table.

## ★★ A REAL big-endian CAN signal-getter bank exists at `0x215xx-0x217xx`

The RX buffers ARE decoded — by a bank of tiny generated accessor functions, one per signal. Verified
example, `FUN_00021706` (body `0x21706-0x21723`) [VERIFIED: `disassemble_bytes dry_run` @`0x21700`]:

```
0x21706  prepare { r28,lp }, 0x0
0x2170a  jarl 0x0001fa42, lp
0x2170e  ld.bu -0x140c, gp, r14    ; 0xFEDF6BF4 = <buf>+4
0x21712  ld.bu -0x140b, gp, r28    ; 0xFEDF6BF5 = <buf>+5
0x21716  shl 0x8, r14
0x21718  or  r14, r28              ; (buf[4]<<8)|buf[5]  = BIG-ENDIAN 16-bit
0x2171a  jarl 0x0001fa72, lp
0x2171e  mov r28, r10              ; return value
0x21720  dispose 0x0, { r28,lp }, lp
```

Sole caller: **`FUN_000522fe` @`0x5233a`** [VERIFIED: `get_xrefs_to(0x21706)`].

**Bytes 4-5 big-endian is exactly the position of Honda `XMISSION_SPEED2` in `0x158` ENGINE_DATA
(0.01 km/h), confirmed live on the EPS bus at ~97 Hz by a panda capture.** Sibling getters use the
same shape on other buffers/offsets, e.g. `0x2172c`/`0x21730` → `0xFEDF6BD8`+0/+1 (bytes 0-1 BE).
Other getter sites: `0x215D0`, `0x216D2`, `0x2174A`.

⚠ **This makes the ID↔dest pairing question decision-critical, and hints the index-parallel reading
may be WRONG.** Under index-parallelism `0xFEDF6BF0` is `0x1D0`'s buffer, but `0x1D0` WHEEL_SPEEDS
has no signal at bytes 4-5 matching a single BE16, whereas `0x158` does. If `0xFEDF6BF0` actually
holds `0x158`, `FUN_00021706` **is** the vehicle-speed getter. Resolve the pairing first.

⚠ An earlier hypothesis of mine — that the `0x21xxx` cluster was a per-message presence/SNA check
(one byte per frame) — was **WRONG and is retracted**; the disassembly shows two-byte BE assembly
feeding a value-returning getter. Recorded because the byte-scan evidence (single `ld.bu` hits per
buffer) genuinely looked like a presence check until disassembled.

## Bonus: all dest buffers are slots of the `0xB7260` array

Every dest is `0xFEDF6AE0 + 8n` — i.e. a slot of the 40×8-byte I/O mailbox array of
[[reference-accord-b7260-io-mailbox-array]]. `0xFEDF6B00` = `gp-0x1500` = slot 4 **of this RX dest
table too**, a second independent corroboration of the V50 GATE-1 on-car failure (it is a CAN RX
destination, written register-indirect — exactly the blind spot static scans missed).
