# HANDOFF — 2026-07-13 — V31P: gentle-EME gate-firing telemetry piggybacked into CAN 330

**Platform:** 2020 Honda Accord, `39990-TVA-A160`, Renesas V850E2. **STOCK analysis program = `code.bin`**
(Ghidra program `master.bin`, flat base 0; gp=0xFEDF8000, tp=0xBF000). Openpilot = operator's **StarPilot**
fork on a **comma 4** at `../openpilots/raayyymond-StarPilot/StarPilot` (branch `Dom`).

**Builds on** `handoffs/2026-07/HANDOFF-2026-07-12-comma4-uds-live-telemetry-bus-analysis.md`. That session proved live UDS
polling during LKAS is impossible on the comma 4 (OBD mux and steering share the single FDCAN2/bus-1
peripheral; 399/427 vanish under mux — confirmed on-car this session via `tools/test_obd_mux_steering.py`).
This session **built V31P**: instead of UDS, the firmware piggybacks gentle-EME **gate-firing flags** into
genuinely-spare bits of a frame openpilot already logs. **BUILT + fully Ghidra-verified, UNFLASHED.**

---

## 0. One-line state

**V31P = V31 (unchanged cals) + gentle-EME gate-firing telemetry into CAN 330 (0x14A) spare bits.** Five
suspect gates are instrumented at their real firmware decision sites (4 code-cave trampolines); each latches
one bit into a scratch RAM flag byte; the 330 content builder packs the flags (+2 live state flags) into
330 byte4[7:3]/byte7[7:6] just before the checksum. openpilot logs 330 raw → the flags ride into the rlog
live during LKAS with **no CAN TX, no UDS, no OBD mux, no bus conflict**. The StarPilot fork's UDS poller is
reverted and replaced by a lightweight RX decoder. **RWD built, 49/49 CRC, every hand-encoded byte
re-disassembled in Ghidra and confirmed. UNFLASHED.**

---

## 1. The gate → flag → wire map

Flag byte (scratch RAM): **gp-0x1500 = 0xFEDF6B00**, u8, whole-image 0 references, boot-zeroed. Gate stubs
`set1` a bit; the pack hook read-then-clears it each 330 frame (inside the builder's di section), so each
frame's bits = "fired since the last frame (~10 ms)" — catches cuts shorter than the sample interval.

| flag byte bit | 330 wire | flag | firmware site (all byte-verified on master.bin) | cal |
|---|---|---|---|---|
| bit0 | byte4 bit3 | ENGAGE_SM_CUT | decider `FUN_00040d58` epilogue `0x40e64`, r12==2 (voterMax≥320 torque disengage) | `0xC6312`=320 |
| bit1 | byte4 bit4 | VOTER_AVG | deliver-commit `FUN_0003d04c` bail jr `0x3d0b4` (gp-0x6a5e≥320) | `0xC62FE`=320 |
| bit2 | byte4 bit5 | GATE5_TORQUE | deliver-commit bail jr `0x3d098` (\|gp-0x4f68\|≥4096) | `0xC61EA`=4096 |
| bit3 | byte4 bit6 | ANGLE_DB | angle-deadband `FUN_0003c7fc` cut `0x3c93c` (\|angle−ref\|>4825, #1 suspect) | `0xC6354`=4825 |
| bit4 | byte4 bit7 | RATE_GATE | decider `FUN_00040d58` epilogue `0x40e64`, r12==5 (gp-0x6a60≥1600) | `0xC6310`=1600 |
| — | byte7 bit6 | TRUMP | live read gp-0x67FE==2 (dispatcher trump) in pack hook | — |
| — | byte7 bit7 | DELIVER_CUT | live read gp-0x6809≠0 (deliver flag = LKAS zeroed) in pack hook | — |

The decider epilogue store `st.b r12,-0x35b6[gp]` (r12 = the decider's refusal code) is a **2-for-1** hook:
one trampoline captures both voterMax (r12==2) and rate (r12==5). ⚠ r12==2 is not param-context-exclusive
(can also fire during benign *engaging* preconditions) — resolve at analysis time by correlating against
DELIVER_CUT / `STEER_STATUS`.

## 2. The firmware edits (build: `analysis-2020accord/builds/v18_v49/build_v31p_tva.py`)

4 code-cave stubs + 1 pack helper at cave **0xC4B34** (1212 B of 0xFF, `[0xC4B34,0xC4FEF]`), reached by 5
equal-length (4-byte) in-place SITE swaps (all stock bytes asserted before patch):

| site | stock | → |
|---|---|---|
| `0x40e64` | `st.b r12,-0x35b6[gp]` | `jr decider_stub` (stub sets bit0/bit4 by r12, re-execs store, `jr 0x40e68`) |
| `0x3d098` | `jr 0x3d1ea` | `jr gate5_stub` (set bit2, `jr 0x3d1ea`) |
| `0x3d0b4` | `jr 0x3d1e6` | `jr voteravg_stub` (set bit1, `jr 0x3d1e6`) |
| `0x3c93c` | `st.b r0,-0x6770[gp]` | `jr angle_stub` (set bit3, re-exec store, `jr 0x3c940`) |
| `0x55c0e` | `movea -0x1518,gp,r6` | `jarl pack_telemetry,lp` (pack 330 bits, clear flag, re-exec movea, `jmp[lp]`) |

**Transparency (why control is unchanged):** each stub re-executes the displaced instruction (or jumps to the
original bail target); the only added effect is a flag `set1`. Stubs clobber only `r10` (proven dead at every
return: `0x3d1e6`/`0x3d1ea` `mov ..,r10`, `0x40e68`/`0x3c940` `mov ..,r10`); pack clobbers only `r6/r7/r8`
(reassigned by the 3 instructions after its return) and preserves `r10`. Pass-paths (gate NOT firing) never
reach these anchors. The 330 checksum (`FUN_00057b24 @0x55c18`) runs *after* the pack hook, so it covers the
telemetry bits and openpilot validates them normally.

**Validation done this session (my own Ghidra reads, not agent reports):** imported `../accord-firmware/analysis-2020accord/_v31p_plain_image.bin`
and re-disassembled — all 36 cave instructions decode exactly as designed (every `set1` bit/disp, both
re-executed stores, both `bne`/`be` skip their `set1`, all stub `jr`s land on correct targets); all 5 sites
decode as `jr`/`jarl` to the correct cave stub. 49/49 CRC OK, ECU round-trip `decode==patched`, byte-diff =
{5 sites + 122 B cave + V31 cals} only. Artifacts:
`../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V31P-gateflags-330piggyback-caveC4B34-0x13000-0x100000.rwd` +
`../accord-firmware/analysis-2020accord/_v31p_plain_image.bin`.

## 3. Why 330 / these bits are safe (steps 1c/1h)

3 subagent audits + my verification (2026-07-13): 330 byte4[7:3] (5 bits) and byte7[7:6] (2 bits) are the
**top tier** — *never written by any instruction in the whole image* AND *undefined in openpilot's DBC*
(`honda_bosch_radarless` STEERING_SENSORS: openpilot reads only STEER_ANGLE/STEER_ANGLE_RATE from 330;
byte4[7:3]/byte7[7:6] carry no signal). Deliberately avoided the "defined-but-openpilot-ignores" bits
(STEER_WHEEL_ANGLE, the sensor-status flags) which another ECU might read. 399 (6 bits) + 427 (3 bits) are
available headroom if a future build needs more.

## 4. Fork side (`raayyymond/StarPilot`, branch `Dom` — committed, NOT pushed at handoff time unless noted)

- **Revert** `a430d4a5`: dropped the DID 0x4801 UDS poller (`eps_telemetry.py`) + the `0x18DA30F1` TX
  whitelist in `honda.h`; reverted card.py/cereal to base `2a3d2744`. **V31P needs no CAN TX at all.**
- **Feature** `8e7cba61`: new `selfdrive/car/eps_telemetry.py` = `EpsTelemetryDecoder` (RX-only: scans the
  card CAN list for 0x14A on bus 1, decodes byte4[7:3]+byte7[7:6]); `card.py` constructs it (Honda only),
  decodes in `state_update`, publishes `epsTelemetry` in `state_publish`; `custom.capnp`
  `CustomReserved11 → EpsTelemetry` (same @id `0xc2243c65e0340384`, 7 flags + raw byte4/byte7);
  `log.capnp` `customReserved11 @137 → epsTelemetry`; `services.py` logs it at 50 Hz.
- Schema **validated** via the `rlog-tools/` mirror (pycapnp round-trip OK on Windows; the full StarPilot
  cereal still can't load under pycapnp on Windows — that's the known heavy-`$Cxx` issue, NOT a schema error;
  `scons` on the comma is the real compile check).

## 5. rlog analysis tooling (this repo, `rlog-tools/`)

- `rlog-tools/cereal/custom.capnp` mirror EpsTelemetry updated to the V31P flags (same @id ⇒ same wire).
- `rlog-tools/decode/extract_eps_telemetry.py` — `epsTelemetry` rows now emit `engage_sm_cut, voter_avg,
  gate5_torque, angle_db, rate_gate, trump, deliver_cut, byte4, byte7`, time-aligned with the `cs` rows
  (399/427/330 via carState). **Note (corrected this session):** `str_torque_eps` (`cs.steeringTorqueEps`)
  is **always 0** on Honda — openpilot never parses 427; see memory `honda-op-steeringtorqueeps-always-zero`.
  Use the internal DELIVER_CUT flag as the cut anchor, not steeringTorqueEps.

## 6. NEXT SESSION

1. **Flash V31P** (operator names file + bus; iron rule). File:
   `39990-TVA,A160-V31P-gateflags-330piggyback-caveC4B34-0x13000-0x100000.rwd`.
2. **Source-build the fork** on the comma (`Dom`): `UsePrebuilt=0`; `scons` (compiles cereal — this is the
   schema check); the epsTelemetry decode is source-only. Reboot. (No panda reflash needed — no honda.h/TX
   change this time.)
3. **Drive with LKAS**, provoke a gentle EME (a demanding curve + a bump, per the 07-12 diagnosis).
4. **Analyze:** `python rlog-tools/decode/extract_eps_telemetry.py <route>--*/rlog.zst -o eme.csv`. At each cut
   (`STEER_STATUS=NO_TORQUE_ALERT_2` on 399, or DELIVER_CUT rising), read which gate flag(s) were set →
   **the first-crossing gate is the real gentle-EME trigger.** Then design a targeted fix (raise/reshape only
   that gate) instead of the blunt V33/V35 threshold disables.

## 7. Iron rules (unchanged)

- **No CAN/UDS send or flash without the operator naming the exact payload/file + bus; repeat it back.** V31P
  transmits nothing new on the bus (330 is an existing frame; only spare bits change). The read-only on-car
  test this session was `tools/test_obd_mux_steering.py` (SILENT, `set_obd` relay config, auto-restores).
- Analyze STOCK `master.bin`/`code.bin` only — never `_v*_plain_image.bin` (except to *verify a build*, as
  done in §2). ⚠ r2 default `v850` plugin mis-decodes V850E2 — use `v850.gnu` or Ghidra.
- Before any on-car flash: openpilot/pandad killed (`tmux kill-server`).
