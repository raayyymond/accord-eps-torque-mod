---
name: project-v54-authority-probe-built
description: V54 BUILT 2026-07-27, UNFLASHED — V38 + 0xC62EA 320→0 + a 44-byte read-only cave that packs a 5-bit gp-0x6966 authority bucket into CAN 330 (0x14A) byte4 bits 7:3. It is the instrument that unblocks the 0xC6AF0 edit direction.
metadata:
  type: project
---

```
_v54_plain_image.bin  SHA 233188ffa21d8ae685685a48410e0c15b49ffca8af2fa8d3684f987cf1a4710b
V54 .rwd              SHA 97ea51d2fa6b21d4584247be5571c34a5d3d15df742c2033324aae456c1c7517
```

**58 bytes off V38** in 5 runs: 44-byte cave @`0xC4B34`, 4-byte hook @`0x55C0E`, `0xC62EA` 320→0, two CRC
trailers. Builder `analysis-2020accord/builds/v50_v79/build_v54_tva.py` **imports** its encoders + CRC gates from
`builds/telemetry/build_vfourframe_tva.py` and its lockout constants + safety scans from `builds/v50_v79/build_v53_tva.py`, so the only
thing typed fresh is the cave.

## Why it exists
`0xC6AF0`'s edit direction has been blocked on one runtime number, `gp-0x6966`, since 2026-07-27. Two
attempts to measure it over a **new CAN mailbox** produced silence, and the second is uninterpretable —
see [[reference-accord-v53-flashed-steer-to-zero-confirmed-telemetry-null]]. V54 abandons that channel for
the proven piggyback ([[reference-accord-piggyback-channel-audit-dbc-panda]]).

## The encoding
`wire = min((gp-0x6966 >> 7) + 1, 31)` → `0x14A` byte4 bits 7:3. Bits 2:0 preserved via `andi 0x7`.

| wire | authority | meaning | V55 candidate |
|---|---|---|---|
| **0** | — | 🛑 **cave did not fire; drive is VOID** | rebuild |
| 1-25 | ≤ 3199 | lane at FULL bound — it *can* be the driver | mute (Y→0) |
| 26 | 3200-3327 | straddles the 3277 knee | — |
| 27-28 | 3328-3583 | inside the ramp | — |
| 29 | 3584-3711 | straddles the 3604 knee | — |
| 30-31 | ≥ 3712 | lane already clamped to 0 — cannot be injecting | keep-live (Y→32768) |
| mixed | — | the knee crossing IS the trigger | flatten the ramp |

The +1 bias is the liveness guarantee — see [[feedback-telemetry-must-reserve-a-did-not-fire-value]].

## Gates passed
50/50 CRC blocks, both bootloader walks, RWD decode-back with every gate re-run on the readback, and the
cave + hook **re-disassembled from the written image via GhidraMCP** (fresh import under a distinct
filename, SHA-checked before import, to defeat the stale-import trap). `bnh` resolves to `0xc4b4a`, the
`shl`. **GATE 1**: writes one RAM byte (`gp-0x1514`, read-modify-write), allocates *no* scratch RAM —
so the `gp-0x1500` failure class does not arise; clobbers only r6/r7, a subset of V31P's proven-dead set.
**GATE 2**: vacuous — report-only, into a TX payload byte no control path reads.

`0xC6AF0` asserted stock. `0xC646C` = 3564. `0x454FE` stock `0x65BA` (no V42 ratchet fix, matching V53).

Decode with `rlog-tools/probe/decode_v54_authority.py`. ⚠ Cannot settle 21.09 vs 78.91 Hz — `0x14A` is 100 Hz.

🛑 UNFLASHED. Flash only on explicit operator instruction naming the file and the bus.
