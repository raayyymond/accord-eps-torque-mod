---
name: reference_accord_can_1d0_wheelspeed_dtc_names_no_decoder
description: DTC-name table proves the EPS ingests a VSA wheel-speed CAN message (likely 0x1D0) for a plausibility monitor, but the live decoder/RAM variable/scaling was not located.
metadata:
  type: reference
---

**Evidence**: the DTC name string table (flat `char*[]` array, base `0xBAEA0`, index0 = "KFC_RSRADIUS",
confirmed by walking pointer arithmetic and cross-checking index73 -> "KFC_OUTPUT_STAGE_PHASE_..." as a
sanity check — NOTE: this array's index is NOT proven equal to `FUN_00016de6`'s fault-index argument;
treat the two numbering schemes as unconfirmed-identical) contains, among 127 entries:
`KFC_WHEEL_SPEED` (`0xB9BA4`), `KFC_WHEELSPD_PLAUSI` (`0xB9C68`), `KFC_VSA_1D0` (`0xB9D18`),
`KFC_VSA_1D0_SNA` (`0xB9B74`), `KFC_RACKPOS` (`0xB9C5C`), `KFC_RACKPOS_NOCALIB` (`0xB9C48`).
[VERIFIED: `search_strings`.]

**Inference**: "VSA_1D0" names a CAN-ID-keyed "signal not available" fault for message `0x1D0` from the
VSA (stability control) module — Honda's well-known `WHEEL_SPEEDS` message ID in other Accord-platform
DBCs. Adjacent to `KFC_RACKPOS`/`KFC_RACKPOS_NOCALIB`, this reads as a **wheel-speed vs. rack-position
plausibility cross-check**, structurally separate from the LKAS torque command chain (consistent with
[[reference_accord_no_vehicle_speed_in_arbitration_steerstatus3]] finding zero speed reads in
arbitration). [INFERENCE — the name table entries were not traced to a specific numeric fault index or
consumer function this session.]

**What was checked and did NOT resolve it**: `search_instructions` for literal `0x1d0` (8 hits,
all stack/gp-displacement noise, none a CAN-ID setup). The CAN mailbox dispatch infrastructure was
partially mapped: mailbox->dest-buffer table at `0xB739C` (32 x 4-byte entries, dest = literal RAM
address not gp-relative) — **slot 17 = `0xFEDF6BD8`, re-confirming the known LKAS routing** (index0
sanity-checked: `0xFEDF6B88`). The parallel ID/mask acceptance-filter table (`FUN_0001cf30`, written via
`tp-0x7cc4`/literal `0xB733C`, MMIO targets at peripheral offsets `+0x8028`/`+0x8030`) was read raw but
its per-mailbox CAN-ID encoding was not decoded/calibrated (did not find a clean `0xE4` needle to
establish the encoding, unlike the destination-buffer table which self-validated via the known LKAS
slot). **This is the same dead end the standing CLAUDE.md open item already describes** ("the string
trail dead-ends at a DTC-name table") — this session mapped one layer further (the dest-buffer table,
`0xB739C`) but did not close it.

**Next step to actually close this**: decode the `FUN_0001cf30` acceptance-filter table encoding by
calibrating against the KNOWN LKAS mailbox (slot 17, CAN ID `0xE4`) — find slot 17's entry in the ID
table (parallel structure to the `0xB739C` dest table, likely also 32 entries) and read off its 32-bit
encoding to establish the ID<->register-field mapping, then apply that mapping to find whichever slot
holds `0x1D0`. That slot's dest buffer (from `0xB739C`) gives the RAM address holding raw wheel-speed
counts; a follow-up xref sweep on that address would find the scaling/consumer.
