# HANDOFF — 2026-07-08 — Tier-1 0x660 telemetry build + CAN-TX visibility CORRECTION

**Platform:** 2020 Honda Accord, `39990-TVA-A160`, Renesas uPD70F3508 / V850E2. **STOCK analysis program =
`code.bin`** (`../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin`, flat base 0 → file offset == address). Bases:
`gp(r4)=0xFEDF8000`, `tp(r5)=0xBF000`. **Branch:** `claude/radare2-decompilation-tracers-dreujb` (merged to
`main` this session). **Nothing flashed. One `.rwd` BUILT (UNFLASHED study artifact).**

**Supersedes** the same-lineage `docs/handoffs/2026-07/HANDOFF-2026-07-07-visibility-resolved-and-ram-telemetry.md` — that doc's
Task-1 "RESOLVED: enable bitfield `0xFEDF693C`" claim is **RETRACTED** (see §2). Read this one as the current state.
Read alongside the corrected memory `reference_accord_can_tx_enable_bitfield_discriminator.md` (has the retraction),
`reference_accord_telemetry_ram_hook_a160.md`, `reference_accord_uds_read_surface_a160.md`.

---

## 0. One-line state

Mapped the entire EPS CAN-TX subsystem in **Ghidra** and answered the two session tasks. **Task-1 net: there is NO
EPS-software discriminator for comma visibility** — 0x660 is ROM-armed and transmitted on FCN0 at 5 Hz exactly
like 399, yet absent from the raw comma scan, so the split is almost certainly an **external gateway** (outside
`code.bin`, unverifiable from it). **Task-2 net: the stock RAM-read (KWP SID `0xF4`) answers on K-line, not
comma-CAN**, so comma telemetry must be CAN-exfil — and a Tier-1 0x660 telemetry `.rwd` was BUILT whose flash
**doubles as the definitive on-car visibility test.**

---

## 1. Tooling breakthrough (use this every future session)

The stock `code.bin` is already imported into the local Ghidra project `accord2020_ghidra` as program
**`master.bin`** — byte-verified identical to disk (`0x410c0`=`ld.bu -0x67fe,gp,r12`, `0x55c50`=399 torque
packer). **`V850:LE:32:default`, flat base 0.** **Ghidra decodes the gp-relative loads r2's `v850.gnu`
mis-decodes** — this is what cracked questions four prior r2 passes could not. Access via GhidraMCP.
- Caveats: the DB does NOT know gp/tp (accesses render as `unaff_gp+off`; abs = 0xFEDF8000+off), the `ram` block
  at 0x02000000 is a placeholder (real RAM ≈ 0xFEDEC000–0xFEDFFFFF), inline scripts are disabled
  (`GHIDRA_MCP_ALLOW_SCRIPTS` unset). r2/rizin is NOT installed this session.
- **Git note (Windows):** a prior clone left the git **index wiped** (0 files vs 5648 in HEAD) → every file looked
  "untracked" and `git checkout` refused. Fix = non-destructive `git reset` (rebuilds index from HEAD). Two files
  under `docs/session-2026-06-06-vle-stub-horde/build/qa/` have ~200-char paths that exceed Windows MAX_PATH — they
  live in history but can't be written to disk here; never stage their "deletion."

---

## 2. TASK 1 — why are 399/427/0x14A comma-visible but 0x660/0x19F/0x32E/0x64D not?

**Answer: no EPS-software mechanism discriminates. The split is almost certainly an EXTERNAL GATEWAY, not in
`code.bin`, and is empirically untested.**

Full FCN0 TX map (Ghidra-confirmed): one enabled controller **FCN0**, one HW TX **mailbox 6**, one software
pending queue **`gp-0x170c`**. Per-message arming is the timer path: active flag **`gp-0x16a0[slot]&1`** (ROM seed
`0xB7D00`: slots0-3=0, **slots4-10=1**) + inter-TX interval **`tp-0x7364`=`0xB7C9C`** (byte-read
`[1,1,1,1,20,100,10,2,1,1,1]`; the visible frames' intervals match their real rates — 399/idx9=1→100 Hz,
427/idx7=2→50 Hz, 0x14A/idx10=1→100 Hz, so the table + tick are validated). Suppression mask **`0xB71CC`** is a
uniform `0xC1` for all 11 slots; `gp-0x1713`=0 in normal driving → gate open for all. Buffer-ptr table `0xB7264`
byte-verified (idx4/0x660=`0xFEDF6AF0`=gp-0x1510; idx9/399=`0xFEDF6BE0`=gp-0x1420). **Every software gate treats
0x660 identically to 399.** 0x660 (idx4) is active-from-ROM and never cleared; the software schedules + transmits
it on FCN0 at 5 Hz.

Yet **0x660 — and 0x19F, which the same table clocks at 100 Hz — are ABSENT from a raw comma scan** (38409
frames/10 s, car running, `comma4_can_inventory.py` records every (bus,addr) with NO DBC filter). A 100 Hz FCN0
frame that never reaches the comma cannot be explained by any in-software gate → the discriminator is external
(gateway ECU forwarding only {399,427,0x14A}, or harness topology). This matches the original swarm's
"physical-layer config outside `code.bin`" hypothesis, which was right to leave open.

**⚠ RETRACTION:** a mid-session finding claimed the enable bitfield `0xFEDF693C` (gp-0x16c4) was THE discriminator.
It is **wrong** — that bitfield gates a fn-ptr call whose table (`0xB7C40`) is all-zeros (dead path). Retracted in
`reference_accord_can_tx_enable_bitfield_discriminator.md`.

**Consequence:** repurposing 0x660 (or adding any new EPS TX ID) is **more-likely-than-not INVISIBLE** to the
comma. Only 399/427/0x14A are known-visible. This is decidable only on the car.

---

## 3. TASK 2 — best minimal-code RAM telemetry for the gentle EME

**Every gentle-EME suspect is already a persistent gp-relative RAM global**, so telemetry is about *exfil*, not
capture. Two exfil channels were evaluated:

### 3a. Stock RAM read exists but is K-line, NOT comma-visible
The EPS speaks Honda **KWP2000 on CAN `0x72A`** (dispatcher `FUN_000156FA`, slot-22 handler `FUN_0001FA92`).
**SID `0xF4` = ReadMemoryByAddress-equivalent** (→`FUN_00014FA0`→`FUN_0001CA0A`) reads `0xFEDF____` RAM correctly,
**no SecurityAccess, no programming session**. **BUT the response egresses K-LINE (UART `UARTH1 @ 0xFFFFEB00`)**,
not FCN0 CAN (transport latch `gp-0x22B6` bits4-6 in `FUN_00014e9e`; consumer `FUN_00015f32` forces the K-line
branch; `FUN_0001d68e`/FCN0 never in the diag-response path). ⇒ **UDS RAM read needs a K-line adapter on OBD pin 7,
not the comma.** (Framing for a K-line adapter: session `0x72A [FF 00…]`, read `0x72A [F4 <cnt> 00 00 <a3><a2><a1>
<a0>]`, `0xF5` continues; example read 4B @0xFEDF6A62 = `[F4 04 00 00 FE DF 6A 62]`.)

### 3b. Comma path = CAN-exfil (the TIER1 build)
Because 0xF4 is K-line, comma telemetry must ride a CAN frame. Built **TIER1** (below). Per Task-1 it may be
gateway-blocked — so the flash is also the visibility experiment.

---

## 4. THE TIER1 BUILD (built + verified this session; UNFLASHED)

`../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-TIER1-telem-0x660-MAX-AVG-Gate5-100Hz-0x13000-0x100000.rwd`
Builder: `analysis-2020accord/builds/telemetry/build_tier1_telem_tva.py` (plain image `../accord-firmware/analysis-2020accord/_tier1_plain_image.bin`).

**= V31 base** (gain2x/clamps/ramp + corridor×4 + boost-floor 4096 + float mirror + PN — drives byte-identical to
the studied V31; the gentle-EME torque gates are ARMED at stock 320, so a capture can catch them firing)
**+ 6 in-place equal-length swaps in the 0x660 builder `FUN_000561b0`** (repack payload; encodings image-verified,
r15 survives the di/ei wrappers)
**+ 1 data byte** `0xB7CA0` `20→1` (0x660 TX interval 5 Hz → 100 Hz).

**0x660 payload (DLC 8, little-endian):**
| bytes | signal | gentle-EME gate |
|---|---|---|
| 0:1 | `gp-0x6a62` (0xFEDF159E) voter-MAX torque | crosses **320** → `0xC6312` (V33 decider) |
| 2:3 | `gp-0x6a5e` (0xFEDF15A2) voter-AVG torque | crosses **320** → `0xC62FE` (V35 deliver-commit) |
| 4:5 | `gp-0x4f68` (0xFEDF3098) \|column torque\| | crosses **4096** → Gate-5 (`0xC61EA`) |
| 6 | 0 (unchanged) | — |
| 7 | rolling counter (hi nibble) + Honda 4-bit checksum (lo) | — |

(Dropped V31T's `gp-0x4f60` — it's recoverable from the comma-visible 399 STEER_TORQUE.) Decode with
`analysis-2020accord/studies/telemetry/analyze_telem_0x660.py` (byte positions identical to V31T; rename the middle/third fields).

**Verification:** build self-check 49/49 CRC PASS, ECU-decode==patched image, all readback asserts pass; byte-diff
vs stock clean; **delta vs the proven V31T = exactly 9 bytes** (2 changed telemetry loads @0x561DC/DD + 0x561F4/F5,
the rate byte @0xB7CA0, the recomputed 0x13000-block CRC); the **emitted (encrypted→decoded) image disassembles in
Ghidra** to the intended instructions and the rate table reads `…,1(idx4),100,10,2,1,1,1` with visible-frame
neighbours untouched. Safe: telemetry lives only in the 0x660 content builder — no command/torque/motor/soft-EME/
engage-SM/fault code is touched.

---

## 5. NEXT STEPS

1. **Flash TIER1 → run `comma4_can_inventory.py` (the decisive visibility test).** `tmux kill-server` first; look
   for ID **0x660 at ~100 Hz on bus 1**. *Appears* → not gateway-filtered, you have working telemetry (decode
   §4); *absent* (expected likely, since 0x19F@100 Hz is also invisible) → gateway-confirmed, 0x660 path is dead.
   **Operator names file + bus before any flash (iron rule).**
2. **If invisible — pivot to a whitelisted frame or K-line.** (a) Analyse whether 427 (STEER_MOTOR_TORQUE, DLC3) or
   spare bits of 399/0x14A can carry the signals; (b) K-line adapter on OBD pin 7 + KWP `0xF4` RAM reads (works
   regardless of the gateway). Determine the visible frames' byte usage before committing.
3. **Confirm the gateway externally** (optional): scope the EPS CAN pins, or check the car's gateway/harness, to
   settle whether 0x660 is on the EPS-side bus but not forwarded. Not resolvable from `code.bin`.
4. **Gentle-EME diagnosis (the actual goal):** once a telemetry channel works, capture the ~90 ms cut and identify
   which gate's signal crosses first (voter-MAX 320 / voter-AVG 320 / Gate-5 4096 / or the still-open angle #1
   suspect `FUN_0003c7fc` gp-0x6cc4 / trump gp-0x67FE). Then design the real fix targeting the confirmed gate.

---

## 6. IRON RULES (unchanged)
- **No CAN/UDS send or flash without the operator naming the exact payload/file + bus; repeat it back first.** The
  `0x72A`/`0xF4` frames and the TIER1 `.rwd` above are documented as design/study — NOT sent/flashed this session.
- Analyze STOCK `code.bin` only — never `_v*_plain_image.bin` (those are build outputs).
- Before any on-car flash: openpilot/pandad killed (`tmux kill-server`). `comma4_can_inventory.py` /
  `comma4_panda_test.py` are read-only (SILENT), safe any time after openpilot is killed.

---

## 7. Artifacts & commit
Commit `512a11a` on `main` (fast-forwarded from `5358444`): `builds/telemetry/build_tier1_telem_tva.py`, `_tier1_plain_image.bin`,
the TIER1 `.rwd`, the 07-07 handoff, and 3 reference memories (CAN-TX map + retraction, telemetry RAM/hook facts,
UDS `0xF4` K-line surface). This handoff is a follow-up commit.
