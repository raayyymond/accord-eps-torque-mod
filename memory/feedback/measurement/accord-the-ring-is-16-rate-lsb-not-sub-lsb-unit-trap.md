---
name: accord-the-ring-is-16-rate-lsb-not-sub-lsb-unit-trap
description: "🛑⭐⭐⭐⭐ UNIT TRAP 2026-09-13: the record's '0.17–0.28 LSB' ring amplitude is in units of the 0x14A ANGLE channel's 0.1° LSB (what openpilot reads); on the 0x18F RATE channel — the operand the EPS feeds back — the 18–22 Hz ring is 15.8 raw counts = 1.98 deg/s = ~16 LSB. Any argument that the EPS feedback cannot 'see' the ring, or that quantiser toggles drive it, is void; the feedback leg is LINEAR (0.879 of the T ring; one LSB of dither 0.003)."
metadata:
  node_type: memory
  type: feedback
---

**Why:** the orchestrator briefed two agents with "the ring is 0.17–0.28 LSB of 0.125 deg/s" and one design
addendum built a dead-zone/dither argument on it; `openloop` caught it against the source
(`OPENPILOT-EXCITATION-SOURCES-2026-09-10.md` §A1 is headed "the ANGLE ring") and measured r39: 0x18F rate
15.82 raw = 1.977 deg/s; 0x14A angle 0.0259° = 0.26 angle-LSB; rate → implied angle at 19.92 Hz = 0.158
angle-LSB (matches). A quantiser only makes toggles below one step — available to openpilot's angle path,
not to the EPS rate path.

**How to apply:** always name the CHANNEL and its LSB with any amplitude; when a lever's small-signal
behaviour depends on amplitude (any `>>k` integer filter, any deadband), convert the symptom into that
lever's own operand units first (the standing rule from the V288 lesson). Convert with 8 raw counts per
deg/s on the internal rate x = gp-0x6a56 and 0.125 deg/s per 0x18F LSB.

Related: [[accord-with-the-loop-open-there-is-no-18-22hz-object-zeta-open-ge-0-05]] ·
[[feedback-convert-the-symptom-into-the-levers-own-units-before-reading-a-null]]
