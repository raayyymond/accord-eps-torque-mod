---
name: reference-accord-no-steering-angle-tx-eps-does-not-own-angle
description: "2026-07-23 CONFIRMED: this EPS ECU (39990-TVA-A160) transmits NO steering-wheel-angle CAN message (no 0x156/STEERING_SENSORS, no angle ID anywhere in its 17-slot TX/RX dispatch table); it does track an internal calibratable 'RACKPOS' quantity (DTC names only) but that is not CAN-broadcast. Answers: EPS does not own the reported dash/HDS steering-angle zero-point."
metadata:
  type: reference
---

# Accord TVA-A160 EPS does NOT transmit/own steering-wheel angle (2026-07-23)

Mission: does this EPS ECU own the reported steering ANGLE and its zero-point (operator's dash/HDS angle
reads ~4° off, wants to recalibrate)? Traced on stock `code.bin` (GhidraMCP only), gp=0xFEDF8000,
tp=0xBF000, program="code.bin" explicit on every call (multiple programs open in the shared project).

## BOTTOM LINE — HIGH CONFIDENCE: NO, this EPS does not own/report a steering-wheel-angle CAN signal.

## Evidence [V — byte-level, cross-corroborated 3 ways]

**1. Full 17-slot CAN TX/RX dispatch table ("Table B", base `0xB721C`) decoded exhaustively.**
Read raw via `read_memory` (0xB721C, 44 bytes = 11×4B MIDs first pass, then cross-checked against the
already-written `reference_accord_can_tx_synthesis_2026-07-07.md` which had the full 17). `CAN_ID = MID>>18`
decoded by hand for every entry:
| idx | CAN ID | role |
|---|---|---|
| 0-3 | 0x720-0x723 | TX, spare/inactive |
| 4 | 0x660 | TX, EPS-internal only (gateway-blocked) |
| 5 | 0x64D | TX, EPS-internal only |
| 6 | 0x32E | TX, EPS-internal only |
| 7 | 0x1AB (427) | TX, car-facing (motor-torque-ish) |
| 8 | 0x19F | TX, EPS-internal only |
| 9 | 0x18F (399) | TX, car-facing — STEER_TORQUE_SENSOR = -(gp-0x4f60×125/128), confirmed elsewhere |
| 10 | 0x14A (330) | TX, car-facing (LKAS-related, spare-bit telemetry piggyback target in this kit) |
| 11-16 | 0x75B/0x753/0x752/0x72B/0x6FF/0x6FB | RX-only (builder=NULL) |

**Zero occurrences of 0x156 (Honda STEERING_SENSORS/STEER_ANGLE, decimal 342) or any recognizable
angle-message ID, in TX or the RX-only slots.**

**2. Independent byte-pattern corroboration.** `search_byte_patterns` for the raw LE MID bytes that 0x156
would produce in this same encoding (`0x156<<18 = 0x05580000` → LE bytes `00 00 58 05`): **zero hits
anywhere in the 1MB image.** Confirms #1 isn't an artifact of Table-B specifically — no code anywhere sets
up a mailbox MID for that ID via this idiom.

**3. Independent string-table corroboration.** `search_strings` for `STEER_ANGLE|ANGLE_SENSOR|SAS`
(regex, whole image): **zero matches.** No DTC name, no debug string, nothing referencing an angle sensor
or SAS by name anywhere in the firmware.

## What this EPS DOES own (for contrast)
Torque (CAN 399, STEER_TORQUE_SENSOR), a motor/torque-adjacent frame (427/0x1AB), and LKAS-related
telemetry (330/0x14A) — all previously documented. No vehicle speed either (see
`reference_accord_no_vehicle_speed_in_arbitration_steerstatus3.md` / `reference_accord_no_speed_gain_in_baseassist_feedback_loop.md`).

## Secondary finding — an internal "RACKPOS" calibration concept exists, but is NOT broadcast [V structure, INFERRED link]
`search_strings` for `RACKPOS` found a coherent 5-entry family in the DTC-name string table (base
`0xBAEA0`, per `reference_accord_can_1d0_wheelspeed_dtc_names_no_decoder.md`):
`KFC_RACKPOS_PLAUSI` (0xBA15C), `KFC_RACKPOS_NOCALIB` (0xB9C48), `KFC_RACKPOS_NOINIT` (0xBA170),
`KFC_RACKPOS_PRECALIB` (0xBA184), `KFC_RACKPOS` (0xB9C5C) — pointers to these 5 strings sit
**consecutively** in the pointer array at `0xBAED8/DC/E0/E4/E8` (4-byte stride, `get_xrefs_to` on each
string address confirmed each has exactly one referrer, these 5 addresses). This is thematically and
positionally coherent (init/precalib/nocalib/plausi/base-name), strongly suggesting a real
calibration-aware internal state machine for a **rack position** quantity, distinct from CAN torque.

**Could NOT pin the exact trigger code / numeric fault index this session** (flagged as an OPEN item by
an earlier session too — `reference_accord_can_1d0_wheelspeed_dtc_names_no_decoder.md` explicitly notes
"this array's index is NOT proven equal to FUN_00016de6's fault-index argument"; re-confirmed here: a
`search_instructions` false-zero trap was hit and corrected — the tool requires operand text with a space
after the comma, e.g. `"0xe, r6"` not `"0xe,r6"` — but even after correcting the format, disambiguating
which numeric idx belongs to the RACKPOS DTC-name family vs. unrelated small-index calls (e.g.
`FUN_00018ce8(0xe)`/`FUN_00018ce8(0xd)`, a torque-sensor-channel-status check inside
`FUN_0003d4a2`, the STEER_STATUS/motor-off dispatcher) was not resolved in the time available).

**Plausible (NOT proven) physical identity:** `gp-0x6CC4` (0xFEDF133C), documented in
`reference_accord_gp6cc4_tracking_pipeline.md` as a 3-writer angle/position TRACKING ACCUMULATOR built
from mod-2048/4096 wrap-corrected deltas with a 4-channel consensus-gate and an early-bypass on
sentinel/uninitialized history (structurally similar in flavor to "NOINIT"/"PRECALIB" states) — sits in
the SAME FOC/PI-controller code cluster (`0x3b8f6-0x40e78`) as `FUN_0003d4a2`'s own `gp-0x6CC4`/`gp-0x4EC6`
reference at `0x3d58e`. This is an **inference from thematic/structural similarity, not a proven identity**.

**Even in the best case this identification is correct, it does not change the bottom line**: this
internal position/angle-tracking signal is a **derived quantity** (very plausibly reconstructed from the
motor resolver + turns-count on this dual-pinion architecture — see
`reference_accord_foc_inner_current_loop_architecture.md` for the resolver/FOC angle chain, which is
explicitly an INTERNAL motor angle, not the driver's wheel angle) and is **never transmitted on the CAN
bus** (confirmed exhaustively above) — so it cannot be what the operator/HDS observes as "steering angle."

## What was NOT resolved / would need more work
- Whether this EPS **receives** 0x156 (or any external angle signal) for internal cross-check — the RX
  acceptance-filter table (`FUN_0001cf30`, `tp-0x7cc4`/`0xB733C`) that would settle this was never decoded
  (same open item as the VSA-0x1D0 wheelspeed investigation). Table-B's RX-only slots (11-16) do NOT
  include 0x156, but Table-B is fundamentally the TX/scheduler-adjacent structure, not the CAN acceptance
  filter, so this is a plausibility argument, not a closed one.
- The exact RACKPOS DTC trigger site/condition (see above).
- Which module DOES own steering angle on this platform/model-year — out of scope (would require that
  module's own firmware; not inferable from this dump). Real-world Honda architecture of this era
  typically sources STEERING_SENSORS (0x156) from the VSA modulator or combination meter, not the EPS —
  consistent with, but not proven by, this firmware's silence on the topic.

## Related
[[reference_accord_can_tx_synthesis_2026-07-07]] — the full Table-B provenance this finding builds on.
[[reference_accord_can_1d0_wheelspeed_dtc_names_no_decoder]] — the DTC-name table method and the sibling
VSA-0x1D0 finding; same open item (index-numbering not proven) applies to RACKPOS.
[[reference_accord_gp6cc4_tracking_pipeline]] — the candidate internal angle/position accumulator.
[[reference_accord_no_vehicle_speed_in_arbitration_steerstatus3]] — the sibling "this EPS doesn't have X"
finding for vehicle speed; same investigative shape.

## ADDENDUM 2026-07-23 (same session) — UDS/routine-control enumeration + a real hardware Data-Flash region found

Follow-up mission: "trace the CAN angle TX packer back to source + any stored offset read at init." No
packer exists (above), so nothing to trace forward. For "stored offset read at init," two things found:

**1. There IS a genuine, separate hardware "Data Flash" region: `0x02000000-0x02008000` (32KB),
per `docs/FIRMWARE-DECOMPILE-GUIDE.md`'s own memory-map table, documented there as "calibration —
doubled-with-tag-word storage"** (a redundant/wear-leveled non-volatile scheme — this is the closest
analog to "EEPROM" on this MCU, distinct from the static `0xC5xxx/0xC6xxx` tp-relative CODE-FLASH cal
block that all V14-V50 builds have edited). **This region is NOT included in `code.bin`** (`list_segments`
confirms code.bin is one flat block `0x0-0xFFFFF`; `0x02000000` is a different physical address entirely)
— its live contents cannot be inspected from this file.

**2. code.bin DOES contain a self-programming driver for that region** — found by
`search_instructions(mnemonic="movhi", operand_pattern="0x200,")`, which returned exactly 4 hits, all at
`0x5112/0x520a/0x521c/0x53f0` (functions `FUN_000050f4`/`FUN_000051ec`/`FUN_000053de`). Decompiled: these
manipulate Renesas flash-macro hardware sequencer registers (`0xFF434xxx`/`0xFF436xxx`: erase-range regs,
status/FLMD-style polling) to erase/write pages in `0x02000000+` — i.e. this is generic
erase/write plumbing, not itself a specific calibration value.

**Traced outward (get_function_xrefs, 3 hops) and this entire cluster is SELF-CONTAINED inside the
`0x3000-0x5a00` address range** (all callers found: `FUN_00003054/0000340c/0000348c/00003e10/00004942/
000056c6`, all in the same low range = pre-`~0x14000` boot/init code). **No caller was found in the
"application" layer** (arbitration, torque/damping, engage-SM, DTC logger, CAN — everything traced
earlier this session and in prior sessions) that reaches this data-flash driver via this addressing idiom.
One apparent "high-level caller" (`FUN_00025c32`, a generic multi-channel sensor-validity-monitor
framework, address `0x25c32`) turned out to be a **decompiler-display false positive**: it uses the
numeric literal `0x50f4` as a lookup-table base displacement, and Ghidra rendered it as the function name
`FUN_000050f4` purely because that literal happens to equal a function's entry address elsewhere in the
image — verified NOT a real call (no CALL-type xref, only DATA-type, and the decompiled context is a
`ushort` table read, not a function pointer invocation). **Caution for future sessions**: this exact
"numeric literal misprinted as a function name" trap can waste real time; when a decompiled expression
contains a `FUN_XXXXXXXX` symbol used as an addend/pointer to a *table*, re-check whether it's a genuine
call before treating it as a cross-module link.

**Net conclusion**: a real non-volatile calibration store exists on this chip, but this session found no
evidence connecting it to a steering-angle or torque-neutral value specifically — the only code that
touches it is confined to boot-time flash-sequencer housekeeping. Whether the RACKPOS calibration flags
(NOCALIB/PRECALIB above) are backed by this data-flash region or are pure volatile RAM state that resets
every power-cycle was **not determined** — this is the single biggest remaining open question for a "does
X get stored across key-cycles" framing. Settling it would require either (a) locating the actual read-path
that populates RAM from `0x02000000+` at boot (not found this session — the 4 `movhi 0x200,` hits found
were all erase/write-side, no matching read-side hit was searched separately with a plain `ld`/`sld`
mnemonic filter, which is the concrete next step), or (b) a physical/separate dump of the data-flash sector
itself (outside this file, would need different tooling).

## ADDENDUM 2 2026-07-23 (same session) — RX side closed: 0x156 also NOT in the accepted-ID table

Bounded follow-up per operator/team-lead: decode the CAN RX acceptance table (previously flagged
unresolved in `reference_accord_can_1d0_wheelspeed_dtc_names_no_decoder.md`) and check whether this ECU
*receives* 0x156 for internal use, closing the RX half of the "EPS doesn't touch steering angle" claim.

**Table decoded: `0xB733C`, 24×4-byte MID entries, same encoding as TX Table-B** (`ID = MID>>18` for
standard 11-bit frames; extended 29-bit frames are `0x80000000 | ID`, derived from the known OBD-functional
entry `0x98DBEFF1 = 0x18DBEFF1 | ext-flag`). The table runs exactly `0xB733C-0xB739C` (24 entries) before
transitioning cleanly into the already-documented dest-buffer table at `0xB739C` — confirms 24 is the true
extent, not a read-window artifact. **`get_xrefs_to(0xB733C)` returns nothing** (the standard movhi/movea
blind spot) — decode trusted instead via **3 independent landmark IDs landing exactly right with zero
remainder**: `0x1CA80000→0x72A` (documented diagnostic RX mailbox), `0x07400000→0x1D0` (VSA wheel speed —
matches the `KFC_VSA_1D0` DTC-name finding above), `0x03900000→0xE4` (documented LKAS STEERING_CONTROL RX).

Full 24-entry accepted-RX-ID list (decimal=hex): `0x98DBEFF1`(OBD functional, ext), 1934=0x78E, 1882=0x75A,
**1834=0x72A**(diag), `0x1BFC9202`(ext, undecoded further), 1786=0x6FA, 929=0x3A1, 884=0x374, 808=0x328,
806=0x326, 804=0x324, 773=0x305, 490=0x1EA, 476=0x1DC, **464=0x1D0**(VSA wheel speed), 432=0x1B0, 420=0x1A4,
408=0x198, 380=0x17C, 344=0x158, 316=0x13C, 304=0x130, **228=0xE4**(LKAS), 148=0x94.

**0x156 (342) is absent.** Closest neighbor is 0x158 (344) — a genuinely distinct ID (every entry decoded
to an exact integer, no remainder, so this isn't a rounding artifact bumping into 0x156).

**VERDICT: this ECU neither transmits nor accepts a steering-angle CAN signal, both directions confirmed.**
Per explicit instruction this session did NOT chase the RACKPOS trigger further (internal-only, doesn't
bear on the operator's recalibration goal) — that remains exactly as open as documented above.

**3. UDS/diagnostic surface enumerated (via existing verified memory, not re-derived) — no Routine Control
or angle/SAS-named service found.** Two distinct diagnostic stacks exist on this ECU:
- Legacy KWP2000-over-CAN-0x72A/K-line stack (`reference_accord_uds_read_surface_a160.md`): full SID table
  0xC0-0xFF enumerated; explicitly **does not implement** standard SIDs 0x10/0x22/0x23/0x27/0x2C/0x34-0x37
  (so no SID 0x31 RoutineControl either — 0x31 was never in scope for that stack in the first place).
- App ISO-TP UDS stack (`reference_accord_a160_app_uds_session_gate_and_egress.md`,
  `reference_accord_a160_rdbi_handlerptr_live_dispatch.md`): documents SID 0x22 (RDBI) in detail; no
  mention of SID 0x31 having been found/traced in any prior session either.
Combined with this session's whole-image string search (zero hits on `SAS`/`STEER_ANGLE`/`ANGLE_SENSOR`),
there is **no positive evidence of a UDS-triggered angle or torque-neutral calibration/learn routine
anywhere in this firmware.** This is an enumeration returning empty, not a proof of absence (SID 0x31
specifically was not exhaustively byte-scanned for in this session), but combined with the CAN-TX and
string-table negatives it is a reasonably strong converging negative.
