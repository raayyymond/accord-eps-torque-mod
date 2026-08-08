---
name: v31p-gateflags-330-piggyback-built
description: "V31P (and its successor V31P-V2) piggyback gentle-EME gate-firing telemetry into CAN 330 (0x14A) spare bits: 5 gate flags in byte4[7:3] + 2 flags in byte7[7:6]. V31P was FLASHED + driven (route 77/79 rlogs). Its byte7 bits were BROKEN — trump stuck at 1 ([[eps-gp67fe-trump-engaged-holding-substate]]), deliverCut stuck at 0 ([[eps-deliver-cut-gp6809-broken]]). V31P-V2 (BUILT + Ghidra-verified, UNFLASHED) keeps the 5 gates and replaces byte7 with angleConsensus (decider r12==4) + hardCut (gp-0x676e==4 all-phase disable). Cave 0xC4B34."
metadata: 
  node_type: memory
  type: project
  originSessionId: 4d2f7a6e-8b14-4fdc-9573-d7f3f505f709
---

**V31P** (2020 Accord `39990-TVA-A160`, V850E2) — the reusable live gentle-EME telemetry the operator
wanted, after live UDS-during-LKAS was proven impossible on the comma 4 ([[comma4-eps-uds-poll-comma-vs-redpanda]]).
Instead of UDS, the firmware piggybacks **gate-firing flags** into a frame openpilot already logs.

> **UPDATE 2026-07-13 — V31P was FLASHED + driven; two byte7 bits were broken → V31P-V2.**
> On route 77/79 rlogs the 5 gate flags (byte4[7:3]) work, but the 2 byte7 state bits do not:
> `TRUMP` (gp-0x67FE==2) read 1 in 100% of frames — it's the ENGAGED/HOLDING substate
> ([[eps-gp67fe-trump-engaged-holding-substate]]); `DELIVER_CUT` (gp-0x6809!=0) read 0 in 100% of
> frames — wrong condition (firmware cut is `!=1`), live-read in the wrong phase, and gp-0x6809 has
> no writer ([[eps-deliver-cut-gp6809-broken]]). Also learned: raw CAN 427 MOTOR_TORQUE is ~0 and
> not a cut anchor ([[honda-op-steeringtorqueeps-always-zero]]); the V32–V35 lineage (disabling
> voterMax/angle-consensus/voterAvg gates) never fixed the gentle EME; a subagent trace found the
> real all-motor-disable is `gp-0x676e==4` in `FUN_0003d4a2` (`0x3de6c`) but that's the HARD cut,
> which CAN 427 `OUTPUT_DISABLED` confirms does NOT fire at the gentle cuts.
> **V31P-V2** (`analysis-2020accord/build_v31p_v2_tva.py`, RWD
> `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V31P-V2-gateflags-v2-angleconsensus-hardcut-caveC4B34-0x13000-0x100000.rwd`,
> 49/49 CRC, cave re-disassembled in `../accord-firmware/analysis-2020accord/_v31p_v2_plain_image.bin`, UNFLASHED) keeps the 5 gates and
> replaces byte7: **bit6 = angleConsensus** (decider `FUN_00040d58` r12==4, the V34 gate, added to
> the existing decider stub) and **bit7 = hardCut** (gp-0x676e==4, latched at cave via a 6th site
> swap `0x3de6c`). Pack hook rewritten all-latched (no live-reads). Fork/rlog-tools renamed
> trump→angleConsensus, deliverCut→hardCut (same capnp @5/@6 = wire-compatible). Detail:
> `docs/HANDOFF-2026-07-13-v31p-v2-*.md`.

> **OUTCOME 2026-07-14 — V31P-V2 was FLASHED + driven (route 7f); the 5 gate flags are NON-DISCRIMINATING.**
> Decoded from raw CAN 330 bus 1 (StarPilot not updated): all flags fire on a steady ~10 Hz benign cadence;
> pre-cut firing rate ≈ whole-drive baseline; **nothing rises at either `STEER_STATUS=4` edge**, and the cuts
> don't land on the drive's CAN torque/rate peaks. The gate-telemetry approach watched the wrong sites: the
> gentle EME is the debounce SM `FUN_0002a30e`, and `STEER_STATUS=4` is a lagging report (`gp-0x6809` = dead
> code). A future discriminating build should log the VALUES of `gp-0x682f`, `param_1`, `gp-0x6757`, not these
> threshold bits. See [[v36-debounce-sm-root-cause-and-build]].

**Build:** `analysis-2020accord/build_v31p_tva.py` → `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V31P-gateflags-330piggyback-caveC4B34-0x13000-0x100000.rwd`. **BUILT, 49/49 CRC, every hand-encoded byte re-disassembled in Ghidra (`../accord-firmware/analysis-2020accord/_v31p_plain_image.bin`) and confirmed. UNFLASHED.** Base = V31 (all cals retained, drives identically).

**Mechanism (Decision B — instrument the real decision sites, not just thresholds):**
- Flag byte = scratch RAM **gp-0x1500 (0xFEDF6B00)** (whole-image 0 refs, boot-zeroed). 5 gate stubs `set1` a bit; pack hook read-then-clears each 330 frame (inside builder di) → bits = "fired since last frame".
- 4 code-cave trampolines at **0xC4B34** + 5 equal-length site swaps (all re-execute the displaced instr / jump to the original bail target, so control is unchanged — only a flag set is added; stubs clobber only dead r10):
  - `0x40e64` decider `FUN_00040d58` epilogue (r12==2 → bit0 ENGAGE_SM_CUT / voterMax≥320 0xC6312; r12==5 → bit4 RATE_GATE / rate≥1600 0xC6310) — one hook, 2 gates.
  - `0x3d098` deliver-commit Gate-5 bail jr → bit2 GATE5_TORQUE (|colTorque|≥4096 0xC61EA).
  - `0x3d0b4` deliver-commit voterAvg bail jr → bit1 VOTER_AVG (≥320 0xC62FE).
  - `0x3c93c` angle-deadband `FUN_0003c7fc` cut → bit3 ANGLE_DB (|angle−ref|>4825 0xC6354, #1 suspect).
  - `0x55c0e` 330 builder `FUN_00055a98` (`movea`→`jarl pack_telemetry`): packs flags into 330 byte4[7:3], reads gp-0x67FE==2→byte7 bit6 TRUMP and gp-0x6809≠0→byte7 bit7 DELIVER_CUT, clears flag byte, before the checksum @0x55c18.
- **330 wire:** byte4 bit3=ENGAGE_SM_CUT bit4=VOTER_AVG bit5=GATE5_TORQUE bit6=ANGLE_DB bit7=RATE_GATE; byte7 bit6=TRUMP bit7=DELIVER_CUT. These bits are firmware-never-written AND DBC-undefined (top-tier spare, 3-audit + own-Ghidra verified). Honda checksum covers them; openpilot validates normally.

**Fork (`raayyymond/StarPilot` branch `Dom`, committed locally):** revert `a430d4a5` drops the UDS poller + honda.h TX whitelist (V31P has NO CAN TX); feature `8e7cba61` adds `EpsTelemetryDecoder` (RX-only, scans CAN 0x14A bus 1), card.py hooks, and `custom.capnp CustomReserved11→EpsTelemetry` (same @id, 7 flag bools + raw byte4/byte7), `log.capnp epsTelemetry @137`, services.py @50 Hz. Schema pycapnp round-trip OK via `rlog-tools/` mirror. `rlog-tools/extract_eps_telemetry.py` updated to the flag columns.

**Next:** operator flashes V31P (names file+bus) + source-builds the fork (`UsePrebuilt=0; scons` = the real capnp compile check; no panda reflash needed) + drives → at each cut correlate which gate flag fired first → the true trigger → targeted fix. Full detail: `docs/HANDOFF-2026-07-13-v31p-gateflags-330-piggyback.md`. Related: [[gentle-eme-fires-on-saturated-lkas-command]], [[honda-op-steeringtorqueeps-always-zero]], [[operator-wants-live-general-capabilities]].
