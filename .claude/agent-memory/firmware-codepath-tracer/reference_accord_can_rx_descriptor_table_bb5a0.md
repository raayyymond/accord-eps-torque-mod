---
name: accord-can-rx-descriptor-table-bb5a0
description: "★★★★★ The CAN RX descriptor table @0xBB5A0 (stride 0x20) fully decoded — 19 IDs with handler ptr + RX buffer ptr. Locates the previously-unlocated wheel-speed decoder (0x1D0 -> FUN_00052E32, buf 0xFEDF6C20) AND independently explains V50's GATE-1 failure: gp-0x1500 = 0xFEDF6B00 = the CAN 0x326 RX buffer."
metadata:
  type: reference
---

**Found by scanning the image for clusters of known CAN IDs as halfwords, then decoding the stride.**
Closes the kit's standing open item "**wheel-speed decoder unlocated**" and "firmware
LOW_SPEED_LOCKOUT producer is not located".

## Record layout — base `0xBB5A0`, stride `0x20`
| off | meaning |
|---|---|
| `+0x00` | **handler function pointer** |
| `+0x04` | sequential index |
| `+0x08` | bus / channel group |
| `+0x0C` | flag |
| `+0x12` | **CAN ID** (halfword; `+0x10` is a flag halfword) |
| `+0x14` | enable |
| `+0x18` | **destination RX buffer pointer** (`0xFEDF6Axx..0xFEDF6Cxx`) |
| `+0x1C` | DLC/mask (`0xF` or `8`) |

## Decoded records
| rec | ID | handler | RX buffer |
|---|---|---|---|
| -2 | `0x13C` | `0x522FE` | `0xFEDF6B08` |
| -1 | `0x130` | `0x52452` | `0xFEDF6B10` |
| 0 | `0x17C` | `0x52414` | `0xFEDF6BE8` |
| 1 | `0x1DC` | `0x524BC` | `0xFEDF6C00` |
| 2 | `0x324` | `0x527DA` | `0xFEDF6BA0` |
| 3 | `0x328` | `0x525B8` | `0xFEDF6B98` |
| 4 | `0x0E4` | `0x52608` | `0xFEDF6BD8` |
| 5 | **`0x326`** | `0x52676` | **`0xFEDF6B00`** |
| 6 | `0x374` | `0x52832` | `0xFEDF6C18` |
| 7 | `0x3A1` | `0x528B8` | `0xFEDF6C10` |
| 8 | `0x198` | `0x52960` | `0xFEDF6BD0` |
| 9 | `0x094` | `0x52A14` | `0xFEDF6BF8` |
| 10 | `0x305` | `0x52ADE` | `0xFEDF6AF8` |
| 11 | `0x1A4` | `0x52C28` | `0xFEDF6BC0` |
| 12 | `0x1B0` | `0x52C78` | `0xFEDF6C28` |
| 13 | **`0x1D0` WHEEL_SPEEDS** | **`0x52E32`** | **`0xFEDF6C20`** (= `gp-0x13e0`) |
| 14 | `0x1EA` | `0x534DA` | `0xFEDF6BA8` |
| 15 | `0x78E` | `0x53CCC` | `0xFEDF6B88` |

## ⚠ Two traps this table resolves

**1. `gp-0x1500` is NOT free RAM — it is the CAN `0x326` RX buffer.**
`gp-0x1500 = 0xFEDF6B00` = record 5's `+0x18`. This is an **independent, static confirmation** of the
V50 GATE-1 on-car failure (probe saw it non-zero for 99.47% of the drive). The kit had attributed it to
"slot 5 of the 40-slot array listed at `0xb7260`, written via a table-dispatched pointer" — this table
names the actual owner. **Any future cave RAM candidate must be checked against `+0x18` of every record
here.** `gp-0x14E0 = 0xFEDF6B20` and `gp-0x13d8 = 0xFEDF6C28` (rec 12) are likewise inside the region.
See [[reference_accord_free_ram_candidates_gp1500_gp14e0]] (now known-bad) and
[[reference-accord-b7260-io-mailbox-array]].

**2. The `0x1D0` handler does NOT decode speed values — only validity.**
`FUN_00052E32` stores 48 globals, all SNA/validity flags + shadow twins (`gp-0x683b` aggregate,
`gp-0x6832/33/34/35` per wheel, `gp-0x6e0d..0x6e14`, twins `gp-0x4c3e..0x4c44`, `gp-0x4d3d..0x4d44`),
sourced from **CAN SNA bits** via `FUN_00052cce`/`FUN_00052d5e` bit extractors — *not* from any locally
computed range test. **Zero of those 48 are read anywhere in the assist path `[0x28000,0x46000)`**
(verified zero: the same method finds 8 real links for the `0x1EA` handler as a positive control).

The **values** flow separately and register-indirect: `FUN_00021646/21622/21672/2169E(gp-0x13e0)`
extract four 15-bit fields → `FUN_00053216` → the voter → vehicle speed. See
[[accord-gp6a5e-is-voted-vehicle-speed]]. **A gp-relative load/store scan of `0xFEDF6C20` returns 0 and
is still consistent with the data flowing** — the buffer address is passed as an argument, so the
dereference is register-indirect. This is the same class of blind spot as
[[accord-gp4f60-two-encodings-enumeration-trap]].
