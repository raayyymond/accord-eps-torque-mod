# HANDOFF — 2026-06-30 — V31T passive telemetry (live gp-0x6a62 read) BUILT, UNFLASHED

**Platform:** 2020 Honda Accord, `39990-TVA-A160`, Renesas V850E2. **Currently flashed: V31.**
**STOCK Ghidra program = `code.bin` (`/master.bin`, 2113 fns). ⚠ NEVER analyze `../accord-firmware/analysis-2020accord/_v*_plain_image.bin` for stock claims.**
**Bases:** `gp = 0xFEDF8000`, `tp = 0xBF000`. Builds on `docs/handoffs/2026-06/HANDOFF-2026-06-30-sensorA-identity-gate-scale.md`
(the gate identity) and the `FOUR_FRAME_TELEMETRY_PORTING_BUNDLE/` (Clarity reference method).

---

## 0. One-line state

To CONFIRM the gentle EME fires on `gp-0x6a62 ≥ 320` and to SIZE a new `0xC6312`, we need a live read of
`gp-0x6a62` (it is a *different sensor* than the CAN torque, so its scale is unknowable on paper). **V31T =
V31 + a passive telemetry piggyback on CAN `0x660`** is BUILT, Ghidra-verified, 49/49 CRC, **UNFLASHED study
artifact.** Next: operator flashes (naming file+bus), captures a drive incl. the hard sustained turn, runs
`studies/telemetry/analyze_telem_0x660.py` → pick `0xC6312` → build V32.

---

## 1. CAN-TX architecture (mapped this session — corrects the prior "FUN_00057b24 = TX helper" claim)

`FUN_00057b24` is **NOT** a TX helper — it is the **Honda 4-bit CAN counter/checksum** (`0x10 − sum & 0xf`,
seeded with the CAN ID), OR'd into each frame's last nibble. The real path:

- **Content builders** (7 packers, each fills a RAM buffer + counter, then calls the checksum):
  `0x14A`(FUN_00055a98, DLC8), `0x18F`/399(FUN_00055c42, 7), `0x19F`(FUN_00055f2e, 6), `0x1AB`/427
  (FUN_00055d80, 3), `0x32E`(FUN_000562b8, 4), `0x64D`(FUN_0005605c, 5), `0x660`/1632(FUN_000561b0, 8).
  These (+ `0x728`/CCP) are the EPS's used TX-ID space — all off-limits for a *new* telemetry ID.
- **Transmit driver** `FUN_000541d8(slot, buf)`: re-computes checksum, compares to stored counter, commits
  mailbox via `FUN_00016de6`. Uses a 44-byte descriptor table at `gp-0x32cc` (RAM).
- **Mailbox HW write** `FUN_00016de6`: pokes V850E2 CAN controller mailbox regs (TX request/abort).
- **Scheduler** `FUN_000520d0(slot)`: ~19 slots; each a 32-byte ROM record at `~0xBB544` with period(+0xe),
  buffer ptr(+0x14), content-builder callback(+0x1c).

**`0x660` (FUN_000561b0) is a near-empty heartbeat**: it explicitly zeroes payload bytes 0..6 (`st.b r0,
-0x1510..-0x150a[gp]`, buffer `gp-0x1510`=`0xFEDF6AF0`) and uses only byte 7 for counter+checksum → ideal
piggyback target (6 free bytes). This is why the *new-frame* four-frame port (free slots in both tables +
HW mailbox + new builder) was unnecessary.

---

## 2. V31T = `builds/v18_v49/build_v31t_tva.py` — the edit

V31 **unchanged** (GAIN 1782, clamps 1024, ramp 0x1B, corridor ×4 int+float, boost floor 4096 int+float,
PN) **+ a 6-instruction, equal-length, in-place code edit** in `FUN_000561b0` (the 0x660 builder). Each
`st.b r0,disp[gp]` byte-zero (4 bytes) is swapped for a 4-byte `ld.hu`/`st.h` (Format VII, same length →
zero added bytes, zero NOP pad, zero jarl re-encode):

| file off | stock | → | telemetry |
|---|---|---|---|
| 0x561C2 | st.b r0,-0x1510 | | `ld.hu -0x6a62[gp],r15` (gate `gp-0x6a62`=`0xFEDF159E`) |
| 0x561CE | st.b r0,-0x150f | | `st.h r15,-0x1510[gp]` → wire **bytes 0:1 = gp-0x6a62** (u16) |
| 0x561DA | st.b r0,-0x150e | | `ld.hu -0x4f60[gp],r15` (sensor B `gp-0x4f60`=`0xFEDF30A0`) |
| 0x561E6 | st.b r0,-0x150d | | `st.h r15,-0x150e[gp]` → wire **bytes 2:3 = gp-0x4f60** (s16, scale bridge) |
| 0x561F2 | st.b r0,-0x150c | | `ld.hu -0x6a5e[gp],r15` (sensor A avg `gp-0x6a5e`=`0xFEDF15A2`) |
| 0x561FE | st.b r0,-0x150b | | `st.h r15,-0x150c[gp]` → wire **bytes 4:5 = gp-0x6a5e** (s16) |
| 0x5620A | st.b r0,-0x150a | | *unchanged* → byte 6 = 0 ; byte 7 = counter+checksum |

**Why `r15` is safe across the di/ei brackets:** each value is loaded in one critical-section slot and
stored in the next. `FUN_0001fa42` writes only r8/r14 (its nested `FUN_0001f98e` is empty), `FUN_0001fa72`
writes only r12/r14 — **neither touches r15**. r15 is also dead before its first stock use at `0x56232`, so
no live value is clobbered. **Wire endianness is LITTLE-endian** (V850 `st.h`), so byte0=LSB.

**Why it's transmit-consistent:** the checksum (`FUN_00057b24`) is computed *after* these stores over the
buffer, and `FUN_000541d8`'s re-verify reads the same buffer → counter/checksum stay valid; frame transmits
exactly as today. The edit touches the CAN-TX content builder ONLY — not command math, torque tables,
current control, the soft-EME walls (`FUN_00042af8`/`FUN_00043e44`), the engage SM, or any fault gate. The
int/float consistency monitors do not read this packer. Edit lies in main CRC block `[0x13000,0xC4FFC)`
(CRC @`0xC4FFC`), recomputed by the builder.

### Verification done this session
- Build self-check: **49/49 CRC PASS**, ECU-decode==patched, all readback asserts pass.
- byte-diff vs stock: **52 bytes / 28 runs** (V31 cals + 24 telemetry code bytes + 2 block CRCs).
- **Ghidra-verified**: imported `../accord-firmware/analysis-2020accord/_v31t_plain_image.bin`, disassembled `0x561be–0x56212` → all 6 instructions
  decode exactly as intended, brackets intact, no misalignment.

Outputs: `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V31T-telem-0x660-piggyback-sensorA-gate-0x13000-0x100000.rwd`
+ `../accord-firmware/analysis-2020accord/_v31t_plain_image.bin`.

---

## 3. Decoder — `studies/telemetry/analyze_telem_0x660.py`

`python studies/telemetry/analyze_telem_0x660.py <route>--rlog.zst [--src N] [--id 0x660]`. Decodes 0x660 (LE words) +
correlates with 399 `STEER_STATUS`. Prints: (Goal 1) `gp-0x6a62` vs 320 around each `STEER_STATUS→4`;
(Goal 2) gate median/p90/p95/p99/max over normal driving + the `gate : |CAN tbar|` scale to map road-data
CAN peaks into gate units. Auto-reports which `src` 0x660 lands on if not src 1.

---

## 4. NEXT STEPS

1. **Pre-flash bus check** (read-only): with V31 still flashed, `tools/comma4_panda_test.py` to confirm
   0x660 transmits and on which bus/src, and that nothing consumes 0x660 bytes 0..6 (stock = all zero).
2. **Flash V31T** — operator names file + bus, repeat back; kill openpilot/pandad first (`tmux kill-server`).
   It's the currently-flashed V31 behavior + telemetry, so the EME still occurs (that's the point).
3. **Capture** a drive including the hard sustained hands-off turn that EME'd on V30/V31.
4. **Decode** → confirm the 320 crossing (Goal 1); read legit-turn / grab peaks + scale (Goal 2).
5. **Build V32** = V31 + raise cal `0xC6312` (320 → chosen value, 2-byte LE), per the sensorA-identity
   handoff §5. (Optionally revert the 0x660 telemetry, or keep it.) Same rigor; UNFLASHED until named.

## 5. IRON RULES
- No flash without operator naming file + bus; repeat back first. V31T is a STUDY ARTIFACT.
- Analyze STOCK `code.bin` only — never `_v*_plain_image.bin`.
- Before any flash on a comma device, openpilot/pandad must be killed.
