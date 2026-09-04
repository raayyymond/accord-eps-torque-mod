---
name: reference_accord_gp4f62_dt_is_dma_sensor_tick_not_cpu_ms
description: "gp-0x4f62's producer FUN_0007e74a divides by a Delta-t measured in units of a rolling 2-bit counter (gp-0x4e9e[channel]) that mirrors a field decoded from a DMA-channel-1-received torque-sensor frame (0xFFFF7362/736A = SVD DTC1/DTS1) -- NOT a CPU-tick counter. gp-0x4e3d is a 2-value (0/1) redundant-channel A/B select flag, not a 4-phase software counter (corrects an open item in reference_accord_gp4f62_not_fixed_delay_and_h0_void_scope). Exact sensor-rate/CPU-rate ratio unresolved (DTRS1 trigger source + peripheral baud rate not in this kit's SVD). Also on the V283 image specifically: r24's whole Q-format chain (0x3ab90-0x3ac5f) is bit-for-bit the closed form's assumption (no bug), gp-0x671d census is unchanged (16 sites, same 2 writers), and gp-0x683c is confirmed to have ZERO accessors (0x3AA94 decompiles to gp-0x6806, the V104 repoint verified present by direct byte read on the real V283 file, not carried-forward belief)."
metadata:
  type: reference
---

# r24 derivative dt / Q-format / gain-arm trace, V283 image (2026-09-03, `r24trace` for `team-lead`)

Motivated by `V282-R24-TAP-READ-r36-r38-2026-09-03.md` §3.2: r24's measured wire magnitude is 0.30-0.52x
(best estimate 0.37-0.43x) of the closed form's prediction, and the leading hypothesis was a shorter
effective derivative `dt` (assumed 4.0 ms, needs ~1.6 ms to explain the gap while staying inside the
measured phase residual). Full trace, addresses and Python mirror: `docs/traces/TRACE-2026-09-03-r24-derivative-dt-and-gain-arm.md`.

## The mechanism [EVIDENCE, fresh disasm + decompile, V282 Ghidra vehicle cross-verified against the real V283 file's bytes]

`gp-0x4f62 = 2*(torque[n]-torque[n-D])/dt(raw)` (`FUN_0007e74a`, D=cal(0xC6C42)=4, byte-confirmed on
V283). `dt(raw)` accumulates into `gp-0x4e7e` from a per-call delta of a 2-bit rolling counter table
`gp-0x4e9e[channel]`, `channel = gp-0x4e3d` (confirmed 0/1 only, a redundant torque-sensor A/B select
flag written by `FUN_0007ff08`'s init/DTC state machine — NOT a 4-phase software counter as an earlier
memory left open; the mod-4 wrap in the delta arithmetic is because the COUNTER VALUES themselves cycle
0-3, not because the channel index does).

`gp-0x4e9e[channel]`'s WRITER (`FUN_000825f0`, invisible to a plain displacement-text scan — its write is
`movea -0x4e9e,gp,r9; ... st.b ...,[r9]`, the exact array-base blindspot
[[reference-accord-gate1-movea-gp-array-blindspot-and-scalar-bound]] already documents) sets
`table[channel] = (frame_status_byte & 3)`, where `frame_status_byte = gp-0x548 + channel*4` is decoded
once per 1kHz CPU tick by `FUN_0007007c` from a **DMA-received** staging buffer: the availability check is
`0x30 - DAT_ffff7362`, and `0xFFFF7362`/`0xFFFF736A` are the SVD's `DTC1`/`DTS1` (DMA Transfer Count /
Status registers, DMAC channel 1, base `0xFFFF7300`). **The rolling 2-bit field is part of the torque
sensor's own serial frame protocol, and it increments at the SENSOR's native message rate, not the CPU's
1kHz task rate.** `FUN_000825f0`'s sole caller `FUN_0007df80`'s sole caller `FUN_0006bb08` is the SAME
1kHz-task function that calls `FUN_0007f3f8` (`gp-0x4f62`'s gated producer call), per
[[reference_accord_gp4f62_torque_rate_producer_and_c6c42_window]].

**Implication**: if the sensor's message rate exceeds 1kHz (plausible — DMA receive into a ring buffer is
architecturally over-engineered for an exactly-1:1-with-CPU link), each CPU tick's rolling-counter delta
would typically exceed 1, inflating `dt(raw)`'s denominator relative to a naive "1 raw-count = 1 CPU-ms"
assumption — shrinking the computed rate for the same real Δtorque and real time span, in exactly the
direction and rough shape the wire's 2.5-2.7x gap needs. **The exact ratio is NOT resolved** — needs
either the DMA trigger-source config (`DTRS1`, `0xFFFF7340`, boot-init write not yet located; a naive
`0x7340` operand search collides with an unrelated `tp`-relative cal at `0xC6340`, excluded) or the
physical sensor's datasheet message rate, neither available from this kit's generic SVD.

## What this refutes / confirms, on the V283 image specifically

- **Q-format hypothesis REFUTED.** `0x3AB90-0x3AC5F` (r24 in `FUN_0003aa2c`) is bit-for-bit
  `scaled=(clamp(dtorque,±5120)*gain_q10)>>10` — single `mul`, single `sar 0xa`, no bug. `gp-0x4f62`'s own
  divide (`0x7E7D8-0x7E854`) is a raw integer `divq`, no Q-format shift at all.
- **Gain-arm hypothesis REFUTED as census.** `gp-0x671d`: 16 sites, same 2 writers (`FUN_0003bcb2` zeros
  it, `FUN_00041d56` — resolver/FOC domain — writes it), unchanged from stock/every prior build. Confirmed
  by two methods with adjudication: a raw Python byte scan over-counts to 26 (hw2 is shared between odd
  `-0x671d` and even `-0x671e`) but resolves to exactly Ghidra's 16 once the `ld.bu` parity bit (hw1 bit5)
  is applied. 5244 arm fires iff `gp-0x671d==0 && gp-0x6806!=0`.
- **`gp-0x683c` confirmed dead by DIRECT byte read of V283, not carried-forward belief**: `0x3AA94` =
  `84 7f fb 97` on the real V283 file, decompiles to `gp-0x6806` (STEER_CONTROL_ACTIVE) — the V104 repoint
  ([[reference_accord_r24_gate_repoint_reconciles_lever_b_dead_vs_v280_live]]) is present, unchanged.
  Zero readers/writers by two independent null-searches (Ghidra's 1 hit is a branch-target text
  collision, excluded; raw Python scan of the real file: 0 hits in 0x13000-0xFFFFC). Control: the same
  scan for gp-0x6806's pattern returns exactly 16 hits, so the null isn't a silent scan failure.

## Addendum 2026-09-03 (same session) — set-difference against a raw byte census, and the bounded DTRS1 attempt

**gp-0x4f62 has exactly ONE producer, one call site, program-wide** (`jarl ...,0x7e74a`: 1 hit, at
`0x7F9DA` inside `FUN_0007f3f8`). A raw byte census's `0x7F436`/`0x7F442` "second cluster" is a DIFFERENT
branch of the SAME function — a defensive reset (`if (gp-0x4f62==gp-0x4488) zero both`) after calling
`FUN_0007e8d8`, not a second differencer on a different task/clock. Two new genuine readers of gp-0x4f62
found: `0x2C4E8` (`FUN_0002c478`) and `0x3B6A8` (near `FUN_0003b66a`, the 8Hz bandpass boost modulator) —
neither changes the dt mechanism, both just consume the already-computed value.

**gp-0x683c re-confirmed dead by a SECOND independent byte-pattern census, individually adjudicated.** A
cluster of 14 raw hits at `0x52E54-0x53430` that looked like they might be the missed `ld.hu`/`ld.w`
`disp|1` encoding of `-0x683c` all decode, unambiguously, to `-0x683b` (an adjacent shadow-consistency
flag, unrelated cell) — same even/odd hw2-collision trap as `gp-0x671d`/`gp-0x671e`, one byte lower.
`gp-0x683c` itself: still zero real accessors.

**DTRS1 (DMA trigger-source select, `0xFFFF7340`) — one bounded attempt, per operator/team-lead's stop
conditions, NOT resolved.** Confirmed the image's addressing idiom for this SFR region (`movhi -0x1,r0,rX`
+ displacement off `rX`; `0x6C242`/`0x6C33C` clear a bit in `DTS1`, corroborating the DMA-channel-1
mechanism independently). Found a **generic table-driven bulk SFR initializer** (`FUN_0006cc34`-class, 12
bytes/descriptor, OR's a 16-bit peripheral offset with `0xFFFF0000`) that would make a DTRS1 write
**structurally invisible to any instruction-operand text search** — the value would be ROM data in a
table this session did not parse. Even a located entry would need this chip's DMA trigger-source
enumeration, not in this kit's SVD. **Stopped per agreement: mechanism established, multiplier not
determinable from this image.**

## Related
[[reference_accord_gp4f62_torque_rate_producer_and_c6c42_window]] — this session's mechanism supersedes
its "peaks at 125Hz, fixed 1kHz D=4" framing; that file's transfer-function math is still right in SHAPE
(sinc rolloff, 90°-lead) but its `dt` numeric anchor (4.0ms) is now flagged, not confirmed.
[[reference_accord_gp4f62_not_fixed_delay_and_h0_void_scope]] — this session directly resolves that
file's open item ("does gp-0x4e3d increment every tick or is it a phase table") — it's a 2-value channel
select, and the real "phase" mechanism lives one level deeper, in the DMA-fed counter table.
[[reference_accord_fun3aa2c_is_gp6b94_writer_and_r24arm_gate]] — the arm-gate condition this session
re-confirms unchanged.
[[reference-accord-gate1-movea-gp-array-blindspot-and-scalar-bound]] — the exact blind-spot class that
found `gp-0x4e9e`'s writer.
