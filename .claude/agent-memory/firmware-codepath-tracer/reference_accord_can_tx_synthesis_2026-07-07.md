# Accord TVA-A160 CAN TX subsystem — 4-segment swarm SYNTHESIS (2026-07-07)

**Mission (handoff §5 NEXT STEP #1):** find a free TX mailbox / scheduler slot on the EPS **car-facing** CAN
channel to add a new ~100 Hz, no-mux telemetry frame (angle `gp-0x6cc4`, voter-MAX `gp-0x6a62`, voter-AVG
`gp-0x6a5e` + a status byte) that would confirm the gentle-EME trigger on the car.

**Method:** 4 parallel `firmware-codepath-tracer` radare2 agents, one per subsystem segment, all on STOCK
`../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin` (flat base 0). Tool discipline: radare2 5.5.0 with **`v850.gnu`**
(the default `v850` plugin mis-decodes V850E2 — re-verified this session: `0x410c0` default→bogus
`jarl 0x004c0188,r12`, `v850.gnu`→correct `ld.bu -26622[gp],r12; cmp 2,r12`). r2 `aa`/`axt` xrefs are
unreliable on this image (≈1 function recovered); segments used manual V850 JARL22 byte-scanners + raw-pointer
scans instead (script in scratchpad; method in the Segment B/D files).

Segment files (read for byte-level evidence):
- `reference_accord_can_tx_segmentA_channel_topology.md` — physical channel map
- `reference_accord_can_tx_segmentB_scheduler_descriptor_table.md` — the `0xBB544` scheduler (RX, not TX)
- `reference_accord_can_tx_segmentC_driver_hw_mailbox.md` — the real HW writer + logical table
- `reference_accord_can_tx_segmentD_known_frame_provenance.md` — known-ID → dispatch provenance

---

## The real outbound TX path (three-way convergent: B, C, D independently)

```
builder fns (399=FUN_00055c42, 0x660=FUN_000561b0, ...)
  → shared indirect-dispatch registry "Table B":
        fn-ptr array   0xB72AC   (4B stride)
        buffer-ptr     0xB7264 / 0xB721C (CAN-ID array) / 0xB71B8 (DLC)
        channel byte   0xB7208
  → FUN_0001d68e  (the HW mailbox writer — byte-scatter of 8 data bytes)
  → CAN peripheral message buffer at 0xFF481000 + idx*64   (FCN0, base+0x1000)
```

**Table B is exactly 17 entries, sentinel-terminated (`0x800007FF`), fully occupied — ZERO free logical
slots** (Segment C reconstruction, confirmed by Segment B which retracted an initial "free slots" misread):

| idx | CAN ID | DLC | role |
|---|---|---|---|
| 0–3 | 0x720–0x723 | 8 | TX (newly identified) |
| 4 | 0x660 | 8 | TX internal-only |
| 5 | 0x64D | 5 | TX internal-only |
| 6 | 0x32E | 4 | TX internal-only |
| 7 | 0x1AB (427) | 3 | **TX car-facing** |
| 8 | 0x19F | 6 | TX internal-only |
| 9 | 0x18F (399) | 7 | **TX car-facing** |
| 10 | 0x14A | 8 | **TX car-facing** |
| 11–16 | 0x75B/0x753/0x752/0x72B/0x6FF/0x6FB | — | RX-only (builder=NULL) |

## Corrections to the mission brief (each byte-verified, ≥2 independent agents)

1. **`FUN_00016de6` is NOT the HW mailbox writer** — it is a DTC/fault logger (Segments C + D, plus a prior
   independent trace `reference_accord_consistency_monitor_hardshutdown.md`). Real writer = `FUN_0001d68e`.
2. **`FUN_000541d8` is NOT the HW TX driver** — it is a pure-RAM software checksum/retry state machine over a
   44-byte-stride table at `gp-0x32CC` (Segment C).
3. **`FUN_000520d0` / table `0xBB544` is NOT a TX scheduler** — it is a periodic **RX-message-validity /
   dual-value lockstep-consistency** dispatcher (19 slots, all used): entry 7 = the CAN-0xE4 STEERING_CONTROL
   RX processor `FUN_00052676`; entries 0/16 = lockstep comparators via fault reporter `FUN_0006b9fa`
   (Segment B, corroborated by D + A who each traced the same chain).

## Physical channel topology (Segment A — authoritative, SVD-grounded)

- CMSIS-SVD for the exact chip (`UPD70F3508_V850E2Px4.svd`, product ID `0DB40h`) declares two CAN ("FCN")
  controllers: **FCN0 base `0xFF480000`**, **FCN1 base `0xFF4A0000`**, 64 message buffers each at
  `base+0x1000+n*0x40`. Confirmed from live code by the boot zero-fill loop `@0xcf6–0xd08`
  (`for(addr=0xFF480000; addr<0xFF4A2000; addr+=4) *addr=0`).
- **`0xFF489000` is FCN0's own `+0x9000` sub-block, NOT a second channel** — this corrects Segments B/C, which
  read `0xFF481000+0x8000` as "channel B." Per the SVD's addressBlock declarations `0x9000` belongs to FCN0.
- **Only FCN0 shows any software TX activity.** An exhaustive dual-idiom literal scan found ZERO references to
  `0xFF4Axxxx` (FCN1) anywhere in the 1 MB image except the single boot zero-loop bound.

## Channel-selector verdict (Segment D + A)

- The per-message channel byte at `0xB7208` reads **`0x06` for all 11 populated slots — car-facing and
  internal alike.** There is **no per-message field that splits car-facing from internal** in this dispatch
  path. `FUN_0001d68e` writes only FCN0 (`0xFF481000`) at all call sites.
- **Implication:** in the statically-traced firmware, car-facing and internal frames go out the **same
  physical controller (FCN0)**. The car-facing/internal split the comma observes is therefore NOT a firmware
  per-frame channel selector we can find — it is either external bus/gateway wiring, or FCN1 is driven through
  fully-runtime-parameterized addressing that static analysis cannot see (no evidence found for the latter).

---

## MISSION CONCLUSION

There is **no drop-in free TX slot** anywhere in the scheduling/dispatch layer. To add the telemetry frame the
build must **extend the three parallel Table-B arrays by one entry each** (CAN-ID `0xB721C`, DLC `0xB71B8`,
fn-ptr `0xB72AC`; plus the channel-byte `0xB7208` and buffer-ptr `0xB7264` arrays), repointing every xref to
those bases, with the new builder stub placed in the **code cave `0xC4E00–0xC4FEF`** (~528 B free, CRC block
auto-recomputed). This is a **code+data patch, not a data-only cal edit** — heavier than V31T, matching the
handoff's "FOUR_FRAME_TELEMETRY_PORTING_BUNDLE heavy path." HW mailbox headroom (~64/FCN0) is not the limiter.

A newly-added frame via that path lands on **FCN0 — the same physical wire as the known car-facing IDs
399/427/0x14A** — which is exactly what the telemetry frame needs. **Stated as a working hypothesis.**

## ONE verification to run before committing to a build (recommended by Segments A + D)

Trace a **known car-facing builder** (399 = `FUN_00055c42`, or 427/0x14A) forward through `FUN_0001d68e` to its
**final message-buffer store address**, and confirm it lands in the **FCN0 `0xFF481000+idx*64`** range — and,
if possible, adjudicate whether internal-only IDs route through a *different one of `FUN_0001d68e`'s 3 call
sites* than car-facing IDs. If a car-facing builder demonstrably writes FCN0, the "new frame → same wire as
399/427/0x14A" hypothesis is confirmed and the extension build can proceed against FCN0 with confidence.

## Status
Read-only / study only. Nothing flashed, no firmware/build changed. All work on branch
`claude/radare2-decompilation-tracers-dreujb`.
