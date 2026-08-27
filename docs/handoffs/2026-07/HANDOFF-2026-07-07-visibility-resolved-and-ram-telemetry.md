# HANDOFF — 2026-07-07 (v3) — CAN visibility RESOLVED + minimal-code RAM telemetry design

**Platform:** 2020 Honda Accord, `39990-TVA-A160`, Renesas uPD70F3508 / V850E2. **STOCK analysis program =
`code.bin`** (`../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin`, flat base 0 → file offset == address). Bases:
`gp(r4)=0xFEDF8000`, `tp(r5)=0xBF000`. **Branch:** `claude/radare2-decompilation-tracers-dreujb`. **Read-only
study; nothing flashed, no firmware/build changed.**

**Tooling breakthrough this session:** the stock `code.bin` is already imported into the local Ghidra project
`accord2020_ghidra` as program **`master.bin`** (byte-verified identical to disk: `0x410c0`=`ld.bu -0x67fe,gp,r12`
trump, `0x55c50`=399 torque packer). **Ghidra (`V850:LE:32:default`, flat base 0) decodes the gp-relative loads
that r2's `v850.gnu` mis-decodes** — this is what cracked both questions below. Use Ghidra via GhidraMCP for all
future V850E2 dataflow. Caveats: the DB does NOT know gp/tp (accesses show as `unaff_gp + off`; abs = 0xFEDF8000 +
off), the `ram` block at 0x02000000 is a placeholder (real RAM ≈ 0xFEDEC000–0xFEDFFFFF), and inline scripts are
disabled (`GHIDRA_MCP_ALLOW_SCRIPTS` unset) — work through the decompiler.

---

## TASK 1 — Why are 399/427/0x14A comma-visible but 0x660/0x19F/0x32E/0x64D not? **RESOLVED.**

**Answer: the split is NOT routing / second bus / mailbox / channel. It is a per-message ENABLE BIT.** A frame is
built, queued, and transmitted **iff its bit is set in the enable bitfield at `0xFEDF693C`.** The comma-visible
frames are enabled in normal driving; the "internal" frames are not — same controller, same mailbox, same physical
wire, just **not requested.**

Evidence (all Ghidra-decompiled, in `reference_accord_can_tx_enable_bitfield_discriminator.md`):
- **One controller (FCN0), one HW TX mailbox (6), one software pending queue (`gp-0x170c`, 1 bit/message).** The
  only HW loader `FUN_0001d68e` writes `FCN0M{6}` and is invoked only with mailbox=6; it looks up CAN-ID/DLC/
  builder-ptr by logical index from Table B and **calls the builder inline when the message is popped** (so a frame
  is even *built* only on demand). Table-B channel byte `0xB7208==6` for all entries corroborates single-mailbox.
- **Periodic scheduler `FUN_0001e8ba`** iterates 11 TX slots (descriptor `0xB7C6C`=identity[0..10]) and tests
  `enable[group(idx)] & mask(idx)` where `group=0xB71E0[idx]`, `mask=0xB71F4[idx]=1<<(idx&7)`,
  `enable=gp-0x16c4=0xFEDF693C`. Only if set does it arm the reload timer and request the send.
- **Enable lifecycle:** `FUN_0001d5a6` (CAN reset, from init `FUN_00057f22`) zeroes all 3 enable bytes → at boot
  nothing transmits. `FUN_0001d96e` (TX-complete) re-arms (`|=`) to sustain periodic TX. `FUN_0001e38e(idx)` =
  disable API. The two builders (399=`FUN_00055c42`, 0x660=`FUN_000561b0`) are structurally symmetric and neither
  self-registers → the discriminator is entirely in this enable/dispatch layer.
- Because there is **no in-code routing DOF** to divert a *requested* frame away from the comma, the prior swarm's
  "physical-layer / gateway / second transceiver" hypothesis is strongly disfavored (still formally unexcludable
  from `code.bin` alone).

**Open sub-point (honest):** I traced the *sustain* (`FUN_0001d96e |=`) and *disable* (`FUN_0001e38e`) paths, but
not the exact mode condition that first *seeds* an internal frame's bit. Leading hypothesis (unchanged, now with
the mechanism located): seeded only under a diagnostic/bench/special mode gated by `gp-0x1688` (`0xFEDF6978`,
tested `&3` in the scheduler). Also not fully resolved: whether HW mailboxes 0–5 are dedicated TX or RX/unused
(does not change the bottom line).

**Consequence — the old telemetry blocker dissolves.** 0x660 isn't inherently invisible; it's just disabled.
Setting an internal frame's enable bit should make the comma see it (cheap on-car confirmation of all of the above).

---

## TASK 2 — Best (most variables) yet minimal-code RAM telemetry for the gentle EME. **DESIGN COMPLETE.**

**Core realization:** every gentle-EME suspect is already a persistent gp-relative RAM global at a fixed address.
So a snapshot needs no register liveness — one hook can copy any subset by address. This **decouples "most
variables" (bounded only by a source-offset table + buffer size) from "minimal code" (one detour + a small copy
loop).** The number of signals captured costs table bytes, not code.

### ⚠ Readout: the stock diagnostic read is NOT comma-visible (K-line) — the comma path is CAN-exfil
The EPS speaks **Honda-proprietary KWP2000 on CAN `0x72A`** (RX mbox 0x23, slot-22 handler `FUN_0001FA92`, SID
dispatcher `FUN_000156FA`; NOT ISO-14229, NOT 0x7E0). **SID `0xF4` = ReadMemoryByAddress-equivalent** (→
`FUN_00014FA0`→`FUN_0001CA0A`, reads `0xFEDF____` internal RAM correctly, no SecurityAccess, no programming
session). **BUT the RESPONSE egresses on K-LINE (UART `UARTH1 @ 0xFFFFEB00`), NOT on FCN0 CAN — so the comma on
CAN bus-1 CANNOT see it.** Egress trace (byte-grounded): transport latch `gp-0x22B6`(`0xFEDF5D4A`) bits 4–6 in
`FUN_00014e9e @ 0x14E9E` (`andi 0x70` → `be` K-line branch → `jarl 0x1fafa` UART TX); the pending consumer
`FUN_00015f32 @ 0x15F32` (tail-jumped from the CAN RX handler) `andi 0x8F` clears bits 4–6 and re-enters
`FUN_00014e9e`, forcing the K-line path. `FUN_0001d68e`/FCN0 is never in the diag-response path; there is no
diagnostic-response CAN ID. **⇒ UDS/KWP RAM read is only usable with a K-line adapter on the OBD-II port (pin 7),
not from the comma.**
- (Still valid for a K-line adapter:) session open TX `0x72A` `[FF 00 00 00 00 00 00 00]`; read TX `0x72A`
  `[F4 <count> 00 00 <a3><a2><a1><a0>]` → **K-line** RX `[F4 <bytes>]`; `0xF5` continues from the auto-incremented
  pointer. Example (4B @ `0xFEDF6A62`): `[F4 04 00 00 FE DF 6A 62]`.

### ⇒ The comma-visible readout is CAN-exfil, unlocked by Task 1
Because SID `0xF4` answers on K-line, the **only comma-visible RAM-telemetry path is to put the values on FCN0
bus-1 as a CAN frame** — which Task 1 makes trivial: **enable a disabled internal frame** (set its bit in the
`0xFEDF693C` enable bitfield) and **pack the suspect RAM globals into its builder's buffer each cycle.** That frame
then transmits on FCN0/bus-1 at 100 Hz and the comma logs it. Two design tiers:

- **Tier 1 (simplest, real-time, bandwidth-limited): enable 1–2 internal frames, repoint their builders.** Each
  frame carries ~7 payload bytes @100 Hz (e.g. angle u32 + status, or voter-MAX/AVG/rate + state). Two frames
  (e.g. 0x660 + 0x64D) ≈ 14 bytes/cycle = ~7 signals streamed live across the 90 ms cut. No free RAM, no ring, no
  hook — just set enable bit(s) + edit builder(s). This is the least-code comma-visible option and captures the
  cut at full rate. There are up to 8 disabled internal frames to draw bandwidth from.
- **Tier 2 (most variables, post-hoc): ring buffer + stream-out over one enabled frame.** Keep the 1-instruction
  hook + ring below (captures ALL ~18–22 signals at native 100 Hz); after a trigger-latched capture, an enabled
  internal frame's builder streams the ring out sequentially (768 B / 7 B per 100 Hz frame ≈ 1.1 s to dump). Gets
  every variable AND comma-visibility, at the cost of non-real-time exfil.

**Bootstrap note (build detail):** to start a disabled frame transmitting, its enable bit must be seeded (the
completion re-arm `FUN_0001d96e |=` only *sustains*). Safest: set the bit each cycle from the same hook (belt-and-
suspenders) rather than relying on a one-time seed + the re-arm loop; confirm the per-slot active state on-car.

### The minimal code change: ONE instruction
**Hook site `0x4141E`** — the instruction `jarl 0x00040a50, lp` (bytes **`bf ff 32 f6`**), the unconditional
post-SM-update call inside the engage/disengage dispatcher `FUN_000413ae`. Cadence chain (each single-caller,
unconditional): 100 Hz timer ISR `w_steer_control_task`(`0x2214A`) → `FUN_00022ca0` → `FUN_000413ae(6)` → falls
through to `0x4141E`. **All suspects are written by the SM state handlers before this point → exactly-once-per-cycle
snapshot.** Retarget the 4-byte `jarl` to the cave stub (`disp22` from `0xC4E00` = `0x809E2`, in range). The
displaced instruction is plain PC-relative `jarl` — fully relocatable into the stub. **Footprint in the stock code
stream = 4 bytes.**

### The cave stub (`0xC4E00–0xC4FEF`, ~528 B of 0xFF, CRC auto-recomputed)
Trampoline: save scratch regs → `jarl 0x40a50, lp` (the relocated original call) → on return, run a copy loop over
a ROM `(gp-offset, size)` table appending one record to the ring at the RAM write-pointer → advance pointer
(mask-wrap) → restore → `jmp` back to `0x41422`. ~60–100 bytes. Optional trigger-latch (+~8 instr): stop advancing
K records after `deliver flag gp-0x6809` transitions 1→0 (the cut), so the buffer always frames the cut; set a
"captured" byte the operator reads first.

### Ring buffer in free RAM
**Candidate `0xFEDF7C00`–`0xFEDF7EFF` (768 B).** Boot bss-clear (`FUN_000146c0`) zeroes all RAM
`0xFEDEC000–0xFEDFFFFF`; `.data` ends `0xFEDF5C67`; stack starts `0xFEDF791C` growing *down* (away from the window);
highest global write below is `gp-0x1380=0xFEDF6C80`; no `st.*` in the scan targets the window. ⚠ **Residual
verification (do before committing):** targeted byte-pattern scan of gp-relative stores in the `-0x100..-0x800`
sub-range (the window is `gp-0x400..gp-0x101`, close to gp — prime real estate). If it's not provably clean, fall
back to the disabled internal frames' now-unused TX buffers (e.g. 0x660 buf `gp-0x1510`) or the `gp+` tail near
`0xFEDFFE24`. Layout e.g. 24 B/record × 32 = 320 ms of 100 Hz history.

### The capture list (CORRECTED addresses — spec had 3 errors)
| signal | gp off | abs | type | note |
|---|---|---|---|---|
| frame counter | `gp-0xF48` | 0xFEDF70B8 | 1–2 B | time alignment (already rolling) |
| **angle** | `gp-0x6cc4` | 0xFEDF133C | **u32 (4B)** | ⚠ 32-bit, not u16 — #1 suspect |
| voter-MAX | `gp-0x6a62` | 0xFEDF159E | u16 | |
| voter-AVG | `gp-0x6a5e` | 0xFEDF15A2 | u16 | |
| voter-rate | `gp-0x6a60` | 0xFEDF15A0 | u16 | #3 suspect |
| col-torque src | `gp-0x4f60` | 0xFEDF30A0 | s16 | 399 torque source |
| \|torque\| | `gp-0x4f68` | 0xFEDF3098 | u16 | Gate-5 |
| deliver flag | `gp-0x6809` | 0xFEDF17F7 | u8 | the cut edge / latch trigger |
| trump | `gp-0x67fe` | 0xFEDF1802 | u8 | #2 suspect |
| **engage state** | **`gp-0x679c`** | **0xFEDF1864** | u8 | ⚠ spec's `gp-0x67DC` DOES NOT EXIST |
| FOC mode | `gp-0x6772` | 0xFEDF188E | u8 | |
| **mode** | `gp-0x6770` | **0xFEDF1890** | u8 | ⚠ spec said 0xFEDF1690 |
| CAN-TX enable | abs | 0xFEDF693C | 3 B | Task-1 confirm: are internal frames enabled? |
| mode-gate | `gp-0x1688` | 0xFEDF6978 | u8 | diagnostic/mode indicator |
≈ 26 B/record. Adding a variable = +3 B of table, not code.

### Byte budget / risk
- Stock-code change: **4 bytes** (the one `jarl` retarget). New cave bytes: ~60–100. RAM: 768 B (stock RAM, no
  flash). Patch + cave inside CRC block `[0x13000,0xC4FFC)` → builder auto-recomputes (49/49, like V31/V31T).
- Reentrancy: advance the write-pointer last; optionally wrap in di/ei (`FUN_0001fa42`/`FUN_0001fa72`, known to
  clobber only r8/r12/r14). Timing: ~30 instr/cycle @100 Hz = negligible.

### (K-line adapter option) UDS-`0xF4` readout
If a K-line adapter is on the OBD-II port (not the comma), the Tier-2 ring can be bulk-read with `0xF4`/`0xF5`
directly — no CAN-exfil builder needed. For the **comma**, use the CAN-exfil tiers above.

---

## IRON RULES (unchanged)
- **No CAN/UDS send without the operator naming the exact payload + bus; repeat it back first.** The `0x72A`
  session-open, `0xF4` read, and any enable-bit write above are DOCUMENTED here as design — NOT sent this session.
- Analyze STOCK `code.bin` only. Any `.rwd` remains UNFLASHED study until the operator explicitly directs a flash.
- Before any on-car flash: openpilot/pandad killed (`tmux kill-server`). `comma4_can_inventory.py` /
  `comma4_panda_test.py` are read-only, safe.

## Artifacts this session
- `reference_accord_can_tx_enable_bitfield_discriminator.md` (Task 1 resolution)
- `reference_accord_telemetry_ram_hook_a160.md` (Task 2 RAM/hook/variable facts)
- `reference_accord_uds_read_surface_*.md` (Task 2 KWP `0xF4` read surface) — from the UDS tracer
- This handoff.

## NEXT STEPS
1. **Design pivot locked:** comma-visible readout = CAN-exfil via an enabled internal frame (Task 1). UDS-`0xF4`
   is K-line-only (byte-traced) → not for the comma. Prefer **Tier 1** (enable 1–2 internal frames + repoint
   builders) unless all ~20 signals are needed simultaneously (then Tier-2 ring).
2. *(Optional confirmation, predicts NO CAN response)* Live-sniff `0x72A [FF …]` + `[F4 04 00 00 FE DF 6A 62]` and
   watch the comma raw log — the static trace predicts the response appears on K-line only (nothing on bus-1). If a
   CAN response DOES appear, revisit the egress trace. **Operator-confirmed payloads only.**
3. Ring window (Tier-2 only): finish the exhaustive gp-store scan of `gp-0x101..gp-0x400` (ep-path already cleared:
   zero `0xfedf7a–7e` literals program-wide) — or use a provably-dead region (the disabled internal frames' now-
   unused TX buffers, per Task 1).
4. Confirm on-car the simplest thing that also closes Task 1: **enable one internal frame (set its `0xFEDF693C`
   bit) and watch the comma** — if it appears, both the visibility finding and the CAN-exfil readout are proven at
   once.
5. If proceeding to a build: Tier 1 = set enable bit(s) + edit builder(s); Tier 2 = 1-instruction hook + cave stub
   + ring + streaming builder. Same rigor as V31T (49/49 CRC, full byte-diff, Ghidra re-verify, UNFLASHED).
