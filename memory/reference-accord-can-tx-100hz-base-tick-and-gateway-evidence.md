---
name: reference-accord-can-tx-100hz-base-tick-and-gateway-evidence
description: CORRECTION — the EPS CAN-TX base tick is 100 Hz, NOT 62.5 Hz (derived 3 ways from cadence x measured wire rate). Plus much stronger gateway-whitelist evidence: 8 of 11 broadcast slots are absent at the comma while identically configured, and FOURFRAME's 0x6A0-0x6A3 are absent as predicted. Read via pure Python table reads, no Ghidra.
metadata:
  type: reference
---

Measured from route 13 (`...00000013--f484e75b00`, FOURFRAME build) + a pure-Python read of the TX
dispatch tables in `_vfourframe_plain_image.bin`. **No disassembler needed** — routing `0xB7208`
(1 B/slot), ID `0xB721C` (4 B/slot, `ID = entry >> 18`), cadence `0xB7C9C` (1 B/slot), static-payload
`0xB7264`, callback `0xB72AC`; 18 slots.

**★ CORRECTION OF RECORD — BASE TICK IS 100 Hz, not 62.5 Hz.** Derived three independent ways from
`cadence x measured wire rate`, all agreeing:

| slot | mbx | ID | cadence | measured on wire | => base tick |
|---|---|---|---|---|---|
| 7 | 6 | 0x1AB (427) | 2 | 50 Hz | 100 Hz |
| 9 | 6 | 0x18F (399) | 1 | 100 Hz | 100 Hz |
| 10 | 6 | 0x14A (330) | 1 | 100 Hz | 100 Hz |

CAN 399's rate is independently confirmed at **exactly 100.000 Hz** by a logMonoTime linear fit
(period 10.0000 ms on all 4 segments). ⇒ `reference-accord-can-tx-architecture-new-id`'s "62.5 Hz base
tick" and its derived per-slot rates are **WRONG and struck**. Consequences: **FOURFRAME transmits at
100 Hz, not 62.5** (bus load ~43 kbps not 27); any packer-hooked telemetry samples at 100 Hz
(Nyquist 50 Hz — comfortably covers the 21 Hz resonance).

**★ GATEWAY WHITELIST — much stronger evidence than the original single-ID argument.** Route 13:
**1,111,018 CAN frames** parsed across buses 0/1/2/128/129/130/193; **zero** frames of `0x6A0-0x6A3`
(FOURFRAME) or `0x555` (VCANTX-TEST) anywhere. Bus 1 carries exactly 27 IDs.
Of the **11 broadcast slots (0-10), only 3 reach the comma** — `0x14A`, `0x18F`, `0x1AB`, precisely the
EPS IDs openpilot's Honda DBC knows. **Eight are absent**: `0x720`, `0x721`, `0x722`, `0x723`, `0x660`,
`0x64D`, `0x32E`, `0x19F`. And **slot 8 (`0x19F`) is configured IDENTICALLY to slot 9 (`0x18F`)** —
same mailbox 6, same cadence 1, both static-payload + callback — yet one is 100 Hz on the wire and the
other never appears. ⇒ per-ID whitelist downstream of the comma tap, confirmed on 8 controls rather
than 1. **FOURFRAME's silence at the comma is EXPECTED and says NOTHING about whether the cave fired.**

**⚠ THE PLANNED RED-PANDA CONFIRMATION MAY NOT WORK.** `docs/RED-PANDA-EPS-SETUP.md` has the red panda
connecting **through the comma Bosch harness** — the SAME tap as the comma's built-in panda. If that is
the only available tap, a red panda sees the same filtered set and cannot discriminate
"gateway dropped it" from "cave never fired". Confirm a tap upstream of the gateway exists BEFORE
wiring anything up. `tools/sniff_fourframe.py` (listen-only, transmits nothing, decodes all 16 signals
+ positive controls) is built and ready if such a tap is found.

**★ BETTER COMMA-VISIBLE TELEMETRY CHANNEL — free bytes in whitelisted frames.** Per-byte entropy over
all of route 13:
- **`0x18F` byte5 = CONSTANT ZERO in 100% of 22,409 frames** — a fully free byte at 100 Hz.
- **`0x14A` byte4 = CONSTANT 0x07 in 100% of 22,408 frames** — a fully free byte at 100 Hz.
- `0x14A` byte2 takes only 4 values {0x00,0x01,0xFE,0xFF}; `0x14A` byte7 / `0x18F` byte6 are the
  6-bit counter/checksum (the 2 spare bits V31P already used).
- **`0x1AB` is a poor carrier**: DLC is only **3**, byte0 ∈ {0x80,0x81}, and the s16 at bytes 0-1 is a
  live saturated signal (min -32768, max -32315, 100% nonzero) — not the "near-zero unused" frame the
  older note implied.

⇒ combining `0x18F` byte5 + `0x14A` byte4 carries a **full 16-bit signal at 100 Hz** on frames PROVEN
to cross the gateway, using the same spare-bit piggyback class that has flashed successfully four times
(V31P/V49P/V50P/V51P) — far lower risk than FOURFRAME's new-mailbox programming. **Verify both bytes are
constant on other routes before building on this.**

Also confirmed from the rlog fingerprint: `ecu=eps addr=0x18DA30F1 fw='39990-TVA,A160'` — the comma
proves a MODIFIED image is running, but **every build in this kit shares that string**, so the rlog
CANNOT identify which build is flashed. Bonus confirmations: `minSteerSpeed = 0.0`,
`steerAtStandstill = False` (openpilot is not the low-speed obstacle — see
[[accord-low-speed-lockout-window-c62ea]]).

Supersedes on the base tick + strengthens the gateway verdict of
[[reference-accord-can-tx-architecture-new-id]]. Related:
[[reference-accord-vibration-requires-lkas-engaged]].
