---
name: feedback-telemetry-must-reserve-a-did-not-fire-value
description: Any firmware telemetry encoding MUST reserve a wire value that a live probe can never emit, so "the cave did not fire" is distinguishable from a valid low reading. Caught in V54 by smoke-testing the decoder against a pre-V54 rlog.
metadata:
  type: feedback
---

**Rule: reserve a wire value that a working probe can never produce.** If the stock value of the carrier
bits is zero, a dead cave reads as zero — and zero usually decodes to a perfectly plausible measurement.

**Why:** caught while building V54 (2026-07-27). The first encoding was
`bucket = min(gp-0x6966 >> 7, 31)` into `0x14A` byte4 bits 7:3. Smoke-testing the decoder against the
**V53** rlog — a firmware with no probe in it at all — produced:

```
bucket 0, 5994 frames, 100.0%   "lane at FULL bound"
=> lane ran at FULL bound throughout: it CAN be the driver. V55 candidate = mute (Y->0).
```

A confident, actionable, completely fabricated answer, from a dead channel. That is exactly how a V55
gets built on a probe that never ran — and this kit had *already* eaten two silent telemetry nulls
(FOURFRAME, FOURFRAME2) whose failure mode was invisible.

**How to apply:** bias the encoding so the live range starts at 1. V54 ships
`wire = min((gp-0x6966 >> 7) + 1, 31)` — costs one instruction and one bucket at the top of the range,
and buys an unambiguous liveness flag. `rlog-tools/probe/decode_v54_authority.py` treats an all-zero drive as
**VOID** and exits non-zero rather than interpreting it.

Generalises beyond CAN: the same trap applies to any probe whose "no data" state is a legal-looking
value — spare-bit piggybacks, unused RAM cells, zero-initialised counters.

**Second rule from the same build:** prefer an encoder that changes only a *register field* of an
already-verified instruction over one that introduces a **new opcode value**. V54's +1 bias was first
written as `add imm5,r7` (Format II op `0x12`), a new opcode whose only evidence would have been the
post-build re-disassembly. It was replaced with `movea 0x1,r7,r7` — `movea imm16,reg1,reg2` computes
`reg2 = reg1 + imm16`, and using `reg1 = r7` instead of `r0` reuses an encoder already verified against a
real instance. Same precedent FOURFRAME used for bc-vs-bnc.

Related: [[reference-accord-piggyback-channel-audit-dbc-panda]],
[[reference-accord-v53-flashed-steer-to-zero-confirmed-telemetry-null]].
