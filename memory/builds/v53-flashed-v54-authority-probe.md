---
name: v53-flashed-v54-authority-probe
description: "V53 flashed 2026-07-27 — steer-to-zero confirmed on-car, four-frame telemetry still silent and the null is uninterpretable; V54 built to measure gp-0x6966 over the proven 0x14A piggyback instead."
metadata: 
  node_type: memory
  type: project
  originSessionId: e4a81c94-76cc-41f8-8718-4f38150aabbe
  modified: 2026-07-28T04:29:51.520Z
---

**V53 is on the car** (V38 cal + FOURFRAME2 cave + `0xC62EA` 320→0), flashed 2026-07-27.

✅ **Steer-to-zero works**, measured from raw CAN 399 not from report: `STEER_STATUS=0` in 5,995/5,995
frames (ST=3 never fires) and **226 frames of `STEER_CONTROL_ACTIVE=1` below 5 km/h** — a cell that is
identically empty on V38.

🛑 **The four-frame telemetry (`0x6A0`-`0x6A3`) was absent again** — 0 frames of 301,824. The null is
**uninterpretable**, not negative: six IDs the stock firmware genuinely broadcasts are equally absent at
the comma tap, while non-DBC IDs *are* logged. **A new-mailbox CAN channel cannot deliver a measurement
on this car — do not build a third one.**

**V54 (built, unflashed) is the replacement instrument**: a 44-byte read-only cave packing
`wire = min((gp-0x6966>>7)+1, 31)` into `0x14A` byte4 bits 7:3 at 100 Hz — the piggyback channel with
four successful flashes behind it. It unblocks the `0xC6AF0` edit direction, which is the last thing
standing between the kit and a directed vibration fix.

Two durable lessons from the build, both in the kit's `memory/`:
- reserve a wire value a live probe can never emit, so "did not fire" ≠ a plausible low reading;
- prefer changing a register field of a verified instruction over introducing a new opcode value.

See the kit repo: `docs/STATE.md`, `docs/BUILD-LINEAGE.md`,
`docs/handoffs/2026-07/HANDOFF-2026-07-27-v53-drive-result-and-v54-authority-probe.md`.
