# HANDOFF — 2026-07-07 — Full CAN→motor gating map, corrected suspect ranking, and the telemetry plan

**Platform:** 2020 Honda Accord, `39990-TVA-A160`, Renesas V850E2. **Currently flashed: V35** (gentle EME still
occurs). **STOCK analysis program = `code.bin`** (`../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin`, flat base 0 →
file offset == address). **Bases:** `gp (r4) = 0xFEDF8000`, `tp (r5) = 0xBF000`. ⚠ Tool: radare2's DEFAULT
`v850` plugin mis-decodes V850E2 — use **`v850.gnu`** (`r2 -a v850.gnu`); `af`/`pdf` mis-size functions —
hand-walk with linear `pd`.

**Branch:** `claude/eme-firmware-path-analysis-lv1xy9` (all work this session pushed there). **Nothing flashed;
no firmware/build changed this session** — this was analysis + a read-only tool + captures.

Read alongside the primary deliverable `docs/guides/GENTLE-EME-CAN-TO-MOTOR-GATING-MAP-2026-07-06.md` and the prior
lineage handoffs `-v35.md` / `-v34.md` / `-2026-06-29-gentle-eme-v32.md` / `-2026-06-30-v31t-telemetry.md`.

---

## 0. One-line state

The gentle EME survives V33+V34+V35, so the trigger is a gate **none of those builds touched.** A 6-agent
decompiling swarm mapped the ENTIRE LKAS-torque gating path CAN→motor; a follow-up hand-verification **corrected
Gate 5's identity** (it is |column torque|, not angular velocity) and re-ranked the suspects toward the **angle**
mechanisms. To discriminate the true trigger on the car we need live internal signals — but the planned `0x660`
telemetry frame is **not visible to the comma** (live-confirmed), so the capture path is a **new EPS TX CAN ID on
the bus-1 car-facing channel, ~100 Hz, no mux.** Next step is a read-only disasm pass to find a free TX
mailbox/scheduler slot on that channel.

---

## 1. The full gating map (primary deliverable)

`docs/guides/GENTLE-EME-CAN-TO-MOTOR-GATING-MAP-2026-07-06.md` — exhaustive enumeration of every point LKAS torque can be
gated CAN→motor, produced by 6 `firmware-codepath-tracer` subagents (one per pipeline segment), each flagged
**live-after-V35** and **bump-trippable**. Per-segment disasm detail is in
`.claude/agent-memory/firmware-codepath-tracer/reference_accord_segment{A..F}_*` and
`reference_accord_engage_sm_full_dispatcher_and_trump_exits.md`.

Pipeline: CAN 0xE4 STEERING_CONTROL → cmd `gp-0x69ae` → voter (`gp-0x6a62` MAX / `gp-0x6a5e` AVG torque,
`gp-0x6a60` rate) → engage/disengage SM (dispatcher `FUN_000413ae` state `gp-0x67DC`, decider `FUN_00040d58`) →
per-cycle deliver-commit `FUN_0003d04c` → arbitration `FUN_00028ea6` (deliver flag `gp-0x6809` → zero LKAS) →
ENABLE FSM `gp-0x67a4∈{2,3}` → LKAS out `gp-0x6b3c` → motor. **Intake (Segment A) and the motor-side tail
clamps (Segment F) are ruled out** — comms-validity checks and magnitude truncations, not sensor-conditional.

---

## 2. ⚠ CORRECTION this session — Gate 5 is TORQUE, not velocity (re-ranks the suspects)

Segment D had labeled deliver-commit **Gate 5** (`gp-0x4f68 ≥ cal 0xC61EA = 4096`) as column *angular velocity*.
**Hand-verification overturned this:** the CAN-399 packer `FUN_00055c42 @0x55c50` sends
`STEER_TORQUE_SENSOR = -(gp-0x4f60 × 125/128)`, and `gp-0x4f68 = clamp(|gp-0x4f60|, 0, 65535)` — so **Gate 5 is
`|column torque| ≥ 4096`.** Consequence: the logged EME torque peaked ~2340 (grab ~3560), **both under 4096**, so
Gate 5 did NOT fire on the five logged events. **Gate 5 is demoted.** (Correction committed into §"CORRECTION" of
the map doc + the D5 table row.)

**Corrected live-suspect ranking (after V33+V34+V35):**
1. **`FUN_0003c7fc` angle deadband** — `|gp-0x6cc4 − ref| > cal 0xC6354 (4825)` inside the deliver-commit chain.
   The SAME angle signal+threshold V34 NOP'd in the *decider*, surviving in a *second* function V34 never touched.
   Best structural fit for "V34 reduced but didn't eliminate." **#1.**
2. **`gp-0x67FE == 2` dispatcher trump** (`FUN_00041054 @0x410c0`) — unconditional, no debounce, forces state→3.
   Producer of `gp-0x67FE` unknown (0 store-sites found); may be a normal mode indicator → polarity needs care.
3. **`gp-0x6a60 ≥ 1600` re-arm RATE gate** (decider params 1/4) — `gp-0x6a60 = |clamp(gp-0x6a56 angle-rate,
   ±12000)|` (verified). Gates re-arming, not the initial cut → explains the "re-arms a beat later" half.
4. **Gate 5 `|torque| ≥ 4096`** — demoted; only fires on a >4096 spike the logged CAN (peak ~2340) didn't show.
5. **`gp-0x6772 != 5` FOC-mode** + **`FUN_00046ea6(13)` fault bit** — live, unresolved identities.
6. **Voter `0xFFFF` sentinel** — needs a genuine coil/DMA quorum glitch, not just a bump.

Per-suspect faithful Python pseudocode (byte-verified branches) is in the chat record of 2026-07-07; fold into a
`reference_` memory if a build proceeds.

---

## 3. Telemetry investigation — how to CONFIRM the trigger on the car

Three prior builds were confidently wrong; static analysis alone won't settle #1 vs #2 vs #3. We need live internal
signals at the cut instant. This session scoped exactly how.

### 3a. Rate + capture reality (measured from `analysis-2020accord/rlogs/` + a live scan)
- The gentle-EME **cut holds ~90 ms (~9 frames @100 Hz)**; torque transient rises over ~150 ms.
- **Comma-visible EPS TX frames (bus 1):** `0x14A` 100 Hz DLC8, `399`/`0x18F` STEER_STATUS 100 Hz DLC7,
  `427`/`0x1AB` MOTOR_TORQUE 50 Hz DLC3. All full-DLC → **no spare bytes to piggyback.**
- **`0x660`, `0x19F`, `0x32E`, `0x64D` are ABSENT on every comma bus** (rlogs + live scan with car running,
  38409 frames/10 s) → **EPS-internal-only.** The old V31T `0x660` piggyback would transmit where the comma
  can't see it. **Dead end for comma capture.**
- **399 already carries torque (`gp-0x4f60`) + rate (≈`gp-0x6a56`) at 100 Hz for free.**

### 3b. Design decision (locked)
- **Do NOT mux.** At 100 Hz single-signal you get ~9 samples across the 90 ms cut; a 4-page mux → ~2 (too few to
  see a threshold crossing). Muxing was only forced by trying to cram in signals 399 already gives free.
- **Telemetry = a NEW EPS TX CAN ID on the bus-1 car-facing channel, ~100 Hz, no mux.** Payload: 3 × u16 internal
  signals we can't otherwise see — **angle `gp-0x6cc4`**, **voter-MAX `gp-0x6a62`**, **voter-AVG `gp-0x6a5e`** —
  plus a **1-byte status field every frame** (deliver `gp-0x6809`==1, trump `gp-0x67FE`==2, FOC `gp-0x6772`==5,
  mode `gp-0x6770`). Torque/rate come from 399. This resolves the ~90 ms cut with no undersampling.

### 3c. Read tooling
- `tools/comma4_can_inventory.py` (NEW this session) — read-only (SILENT/listen-only, cannot TX) live CAN
  inventory: every ID per bus with measured Hz + DLC + sample, plus an EPS-frame-visibility report. Run on the
  car (`tmux kill-server; sleep 2; python3 /data/comma4_can_inventory.py [sec]`).
- Live output archived: `analysis-2020accord/reference/can-scans/2026-07-07-comma4-live-can-inventory-carrunning.txt`
  (+ `README.md` with conclusions).
- Once a telemetry frame is flashed, decode via cabana (`--dbc`, live `--zmq <ip>` or a route), plotjuggler, or a
  Python rlog decoder (extend `analysis-2020accord/studies/telemetry/analyze_telem_0x660.py`). openpilot logs all bus-1 IDs, so a
  new ID is captured automatically.

---

## 4. Firmware homework already done (partially transferable)

Deep disasm of the `0x660` builder was completed BEFORE the rate check killed the `0x660` plan. It does not apply
to `0x660` anymore, but the **techniques transfer** to the new-ID build:
- **`FUN_000561b0`** (0x660 builder) fully mapped: prologue saves lp/r6/r7/r8; buffer `gp-0x1510..gp-0x1509`;
  builds byte7 counter+checksum; calls `FUN_00057b24` (Honda 4-bit counter/checksum) + the TX driver later.
- **`FUN_0001fa42`/`FUN_0001fa72` = di/ei wrappers** (confirmed `di`@0x1fa54, `ei`@0x1fa8c), clobber only
  r8/r12/r14 — never r15.
- **Rolling per-frame counter** at word `gp-0xF48` (`0xFEDF70B8`), bits [17:15] increment each frame — a free,
  already-rotating page selector (was going to drive the mux; now moot).
- **Code cave**: `0xC4E00–0xC4FEF` is a ~528-byte `0xFF` run inside CRC block `[0x13000,0xC4FFC)` (CRC @0xC4FFC,
  auto-recomputed by the builder). Guarded 0xFF in `builds/v18_v49/build_v31t_tva.py` (`CAVE_GUARD`). Unreferenced.
- **JARL disp22 encoding derived** (verified against stock jarls): `word0 = 0xF800|0x780|((disp>>16)&0x3F)`,
  `word1 = disp&0xFFFF`, `disp = (target−pc)&0x3FFFFF`.
- Build infra: `builds/v18_v49/build_v31t_tva.py` is the clean base (V31 cals + CRC bookkeeping + guards + readback asserts).
  The muxed V31T2 artifacts (RWD/DBC/decoder) were **NOT built** — superseded by the capture-visibility finding.

---

## 5. NEXT STEPS

1. **Find a free TX mailbox on the EPS car-facing CAN channel** (read-only disasm). The EPS has ≥2 physical CAN
   channels — car-facing (399/427/0x14A) and internal (0x660/etc.). The new telemetry ID must be configured for
   the car-facing channel. Map the CAN-controller init + mailbox/descriptor tables (scheduler `FUN_000520d0`,
   descriptor table `~0xBB544`, TX driver `FUN_000541d8`, HW mailbox `FUN_00016de6`) to find a spare TX mailbox +
   scheduler slot on that channel, and how the channel is selected. This determines feasibility/cost of the new-ID
   build. Prior art: `FOUR_FRAME_TELEMETRY_PORTING_BUNDLE/` (the "heavy" new-frame path V31T avoided).
2. **Build the new-ID telemetry .rwd** (V31 base + new bus-1 frame, 3 u16 + status byte, ~100 Hz, no mux) with the
   same rigor as V31T (49/49 CRC, byte-diff, r2 re-verify, UNFLASHED). Use the cave `0xC4E00` for the builder if a
   code stub is needed; derive encodings + verify by disassembling the emitted image with `v850.gnu`.
3. **Capture drive → decode → identify the first-mover** at the cut instant among angle/voter-torque/state, then
   design the real fix (V36) targeting the confirmed gate with a clean-lever check.
4. Optionally record two `reference_` memories: (a) the corrected Gate-5 identity + suspect ranking, (b) the
   EPS bus-visibility map (only 0x14A/399/427 comma-visible; 0x660/0x19F/0x32E/0x64D internal-only).

---

## 6. IRON RULES (unchanged)
- **No flash without the operator naming file + bus; repeat it back first.** Everything this session is study/analysis.
- Analyze STOCK `code.bin` only — never `_v*_plain_image.bin`.
- Before any flash on a comma device, openpilot/pandad must be killed (`tmux kill-server`).
- `tools/comma4_can_inventory.py` and `tools/comma4_panda_test.py` are read-only (SILENT mode) — safe any time
  after openpilot is killed.

---

## 7. KEY ADDRESSES / SIGNALS
| thing | address |
|---|---|
| #1 suspect — deliver-commit angle deadband | `FUN_0003c7fc`; `gp-0x6cc4`(`0xFEDF133C`) vs cal `0xC6354`(4825) |
| #2 suspect — dispatcher trump | `gp-0x67FE`(`0xFEDF1802`)==2 @`0x410c0` (state-2 handler `FUN_00041054`) |
| #3 suspect — re-arm rate gate | `gp-0x6a60`(`0xFEDF15A0`) ≥ cal `0xC6310`(1600); producer `FUN_0003f776` |
| Gate 5 (demoted) — \|torque\| | `gp-0x4f68`(`0xFEDF3098`)=\|`gp-0x4f60`\| ≥ cal `0xC61EA`(4096) @`0x3d08c` |
| deliver flag (the cut) | `gp-0x6809`(`0xFEDF17F7`); FOC mode `gp-0x6772`(`0xFEDF188E`); mode `gp-0x6770`(`0xFEDF1690`) |
| voter torque | MAX `gp-0x6a62`(`0xFEDF159E`), AVG `gp-0x6a5e`(`0xFEDF15A2`) |
| CAN torque/rate (free on 399) | `gp-0x4f60`(`0xFEDF30A0`)=STEER_TORQUE_SENSOR src; rate `gp-0x6a56`(`0xFEDF15AA`) |
| 0x660 builder (internal-only) | `FUN_000561b0`; buffer `gp-0x1510`(`0xFEDF6AF0`); counter word `gp-0xF48`(`0xFEDF70B8`) |
| code cave | `0xC4E00–0xC4FEF` (~528B 0xFF, CRC block `[0x13000,0xC4FFC)`) |
| comma-visible EPS TX | bus1: `0x14A`@100Hz, `399`@100Hz, `427`@50Hz |
| tools | `tools/comma4_can_inventory.py` (read-only inventory), `analysis-2020accord/studies/telemetry/analyze_telem_0x660.py` (decoder base) |
