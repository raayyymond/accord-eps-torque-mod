# Live CAN scans (comma 4, red-panda-visible buses)

Read-only CAN inventories captured on the operator's 2020 Accord with
`tools/comma4_can_inventory.py` (SILENT/listen-only — never transmits). Used to
decide where an EPS telemetry frame can actually be captured.

## 2026-07-08-comma4-TIER1-flashed-can-inventory-carrunning.txt  ← DECISIVE TEST
Car running (14.1 V, ignition on, harness status 2), 10 s, 47112 frames, buses 0/1/2.
**Captured AFTER flashing the TIER1 0x660-telemetry `.rwd`** (0x660 rearmed to 100 Hz, payload
= voter-MAX/AVG torque + |column torque|). This scan is the on-car visibility experiment the
07-08 handoff called for.

**Result: 0x660 is STILL ABSENT on every comma bus (0/1/2).** The flash produced **zero** new
comma-visible CAN traffic:
- Unique-ID counts are **identical** to the 07-07 scan: bus0=100, bus1=36, bus2=100. Same ID set
  on bus 1 (no 0x660, no new ID appeared, none dropped).
- `0x0660` ABSENT, `0x019F` ABSENT, `0x032E` ABSENT, `0x064D` ABSENT — unchanged from 07-07.
- The 3 known-visible EPS frames unchanged: `0x14A` 100 Hz, `0x18F`/399 100 Hz, `0x1AB`/427 50 Hz.
- (Radar bank 0x280–0x2FF on bus 0/2 ran at ~14.9 Hz here vs ~10 Hz on 07-07 — a radar-side state
  difference, non-EPS, not material to telemetry.)

**Conclusion — GATEWAY CONFIRMED, CAN new-ID path DEAD.** A 100 Hz FCN0 frame that the EPS software
demonstrably schedules + transmits (0x660, Ghidra-verified) never reaches the comma → the split is an
external gateway forwarding only a whitelist {399, 427, 0x14A}. Repurposing/adding **any** new EPS TX
ID is invisible to the comma. This empirically closes the "new CAN ID" telemetry avenue. The only CAN
avenue left is spare/repurposable bits inside the 3 whitelisted frames (risky — car consumes them);
the gateway-independent fallback is K-line KWP `0xF4` RAM read on OBD pin 7.

## 2026-07-07-comma4-live-can-inventory-carrunning.txt
Car running (14.2 V, ignition on, harness status 2), 10 s, 38409 frames, buses 0/1/2.

**Decision-relevant conclusions (live-confirmed):**
- **The EPS sits on bus 1.** Its only comma-visible TX frames are `0x14A` (100 Hz, DLC 8),
  `0x18F`/399 STEER_STATUS (100 Hz, DLC 7), `0x1AB`/427 MOTOR_TORQUE (50 Hz, DLC 3).
  All three are full-DLC → **no spare bytes to piggyback.**
- **`0x660`, `0x19F`, `0x32E`, `0x64D` are ABSENT on every comma bus** — confirmed EPS-internal-only.
  A `0x660` telemetry piggyback (the old V31T plan) would NOT be captured by the comma. Dead end.
- Buses 0 and 2 are the radar/camera side (mirror each other: the `0x280–0x2FF` radar bank, `0x240`s,
  etc.); the EPS is not there.
- Diagnostic-looking low-rate frames exist on bus 1 (`0x640`/`0x641`/`0x674` @10 Hz; `0x674` carries
  ASCII `0x41`='A' → a UDS/tester response). Too slow (10 Hz) for the ~90 ms gentle-EME cut regardless.

**Therefore:** a telemetry frame must be a **new EPS TX CAN ID on the bus-1 (car-facing) channel**,
transmitted ≥50 Hz (100 Hz ideal). Free ID space is available on bus 1 (pick an unused ID). The open
firmware question is whether the EPS CAN controller has a spare TX mailbox wired to the *car-facing*
channel (the same physical channel as 399/427), not the internal one — that is the next disasm step
for the telemetry build.

**Sampling budget:** the gentle-EME cut holds ~90 ms; at 100 Hz single-signal that is ~9 samples, so
do NOT mux the critical signals. Torque + rate already come free from 399 @100 Hz, so the new frame only
needs the internal signals (angle `gp-0x6cc4`, voter torque `gp-0x6a62`/`gp-0x6a5e`, state bytes).
