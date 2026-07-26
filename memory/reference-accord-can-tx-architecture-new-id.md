---
name: reference-accord-can-tx-architecture-new-id
description: A160 EPS CAN-TX = single FCN0 controller, 18 slots via tables 0xB7208(route)/0xB721C(ID=entry>>18)/cadence 0xB7C9C; all broadcast IDs ride mailbox 6; FREE mailbox pool 7-32 (recommend 16); a new TX ID = a dedicated free mailbox + a small cave. Comma-visibility is a DOWNSTREAM GATEWAY per-ID whitelist, not a firmware/bus difference.
metadata:
  type: reference
---

Full A160 EPS CAN-TX architecture. Lead-verified items read directly from `_v38_plain_image.bin`; the rest
from firmware-codepath-tracer (detail of record: `.claude/agent-memory/firmware-codepath-tracer/reference_accord_can_tx_full_table_decode_and_new_id_recipe.md`).

**Controller:** single FCN0 @`0xFF480000` (only initialized; FCN1 @`0xFF4A0000` dead). Per-mailbox regs step
`0x40`, index n: `STRB` +0x1024 (bit7 SSOW = dir, 1=TX), `DTLGB` +0x1020 (DLC), `DAT0..7B` +0x1000,
`CTL` +0x9038 (arm/trigger), `MID0W` +0x11028 (ID<<18, IDE bit29). SVD: `svd_for_ghidra/UPD70F3508_V850E2Px4.svd`.

**Emitter:** `FUN_0001d82e(slot)` → `FUN_0001d68e(mailbox,slot)`. 18 logical slots (0-17); each slot's HW
mailbox comes from the routing table.

**Tables (18 slots — lead-verified reads):**
- routing `0xB7208` (1 B/slot): slots 0-10 → shared **mailbox 6** (round-robin); 11-16 → dedicated mailboxes
  5..0; slot 17 → mailbox 6 (dynamic-ID bypass, ID from RAM `gp-0x1700`).
- ID `0xB721C` (4 B/slot): **`ID = entry >> 18`** (verified: slot 9 = `0x18F`/399, packer `FUN_00055c42`;
  slot 10 = `0x14A`/330, packer `FUN_00055a98`). Slots 4-10 IDs = 660/64D/32E/1AB(427)/19F/18F(399)/14A(330).
- static-payload-ptr `0xB7264`, dynamic-callback-ptr `0xB72AC` (per slot).
- cadence `0xB7C9C` (1 B/slot, in 62.5 Hz base-tick units, verified): slots 0-3/8/9/10 = 1 (62.5 Hz),
  7(427) = 2 (31.25 Hz), 4(660) = 20, 5(64D) = 100, 6(32E) = 10.

**Scheduler:** `FUN_0002214a` (1 kHz) → /16 nibble counter `gp-0x3518` → 62.5 Hz base tick → per-slot cadence.

**★ GATEWAY VERDICT (lead-verified evidence).** The comma-VISIBLE (399/427/330) vs ABSENT (660/64D/32E/19F)
split is a **DOWNSTREAM GATEWAY per-ID whitelist, NOT a firmware/bus difference**: ALL broadcast IDs ride the
same mailbox 6 / FCN0 / wire, and the 4 "absent" IDs are ACTIVELY scheduled + fired — `0x19F` at 62.5 Hz, the
SAME rate/mailbox as the visible `0x18F`/399 — yet never reach the comma. ⇒ a new arbitrary ID on the normal
path is dropped at the comma's built-in panda exactly like `0x19F`; a new-ID frame is visible ONLY on a red
panda tapped directly on the EPS bus (upstream of the gateway), OR if the chosen ID happens to be one the
gateway already forwards. (Residual: the dynamic mailbox-6 arming is not 100% firmware-closed, but the
actively-fired-but-absent evidence is direct.) Extends [[reference_accord_can_single_fcn0_external_gateway]],
supersedes the hedged 2026-07-07 car-facing-vs-internal note, and resolves the old "CAN-330 TX rate
unresolved" (330 = slot 10, 62.5 Hz, reached via an indirect callback — why the old disp22 scan missed it).

**NEW-ID RECIPE (build-prep — re-verify the mailbox at build time before any flash).** Do NOT extend the
packed 18-slot tables (zero slack, huge blast radius). Instead claim a FREE FCN0 mailbox: the **7-32 band is
the free pool** (init `FUN_0001cf30` bare-izes 7-32 — STRB=0, no ID, never armed; the dispatch table only
references 0-6). **Recommended mailbox 16** (STRB `0xFF481424`, MID0W `0xFF491428`, CTL `0xFF489438`, DAT0B
`0xFF481400`); alts 10/24; avoid boundaries 7/32. Init once: STRB=0x80 (TX), DTLG=8, MID0W = id<<18. Per
cycle (small cave in the 1 kHz task): write 8 payload bytes to DAT0..7B, then strobe CTL `0x0100` then
`0x0200` (mirrors `FUN_0001d68e`'s trigger). Write your own packer.

**Deployment consequence for telemetry:** because a new ID won't cross the gateway to the comma's built-in
panda, a new-ID full-frame probe is a **red-panda-direct-capture** tool, NOT a comma-rlog tool. Comma-rlog
telemetry (V31P/V49P/V50P/V51P) still requires piggybacking a whitelisted ID (330) in its spare bits. Which
channel is worth building depends on how the operator logs. See [[operator-wants-live-general-capabilities]].

**★ MANDATORY TX-READINESS GATE — `gp-0x1712` bit0 (abs 0xFEDF68EE).** A real hardware-relevant TX-inhibit,
NOT bookkeeping: stock checks it at BOTH the enqueue (`FUN_0001d82e`, first gate) and the arm (`FUN_0001d68e`
@0x1d7da: `ld.bu -0x1712[gp],r12; shr 1; bnc skip-fire`). It is steady-1 in normal engine-on driving but drops
to 0 during (a) the mailbox-bank reconfig (`FUN_0001cf30` rewrites every mailbox's CTL/ID/mask incl. ~16) and
(b) a bus-off/comm-fault recovery — firing a mailbox while its registers are mid-rewrite is the race this
prevents. **Any standalone TX cave MUST gate its whole body on it:** `ld.bu -0x1712[gp],rX; shr 0x1,rX; bnc
<skip all mailbox writes>` (bit0=1 → fire, 0 → do nothing). Writers: set `FUN_0001e29e` (reconfig-done),
clear `FUN_0001e2be`/`FUN_0001d5a6` (fault-recovery/master-reset). (A coarser layer above it: `DAT_ff48024c`
bit4.)

**BUILD STATUS — `VCANTX-TEST-txgate` BUILT + lead-verified, UNFLASHED (the kit's FIRST active-CAN-TX cave).**
`build_vcantx_test_tva.py` = V38 + a cave at 0xC4B34 (hook 0x55C0E, the proven 330-packer site, 62.5 Hz) that
gates on `gp-0x1712` bit0, then programs FREE mailbox 16 (STRB=0x80/DTLG=8/MID0W=0x555<<18) and transmits a
fixed 8-byte magic (A5 5A ×4) via the CTL 0x100→0x200 strobe (byte-identical to `FUN_0001d68e`). Lead-verified
off the built image: gate reads the right byte (matches stock 0x1d7da), bnc lands on the restore, only mbx16
touched, 4×/hook/CRC intact. **RESIDUALS settled ONLY by a red-panda flash-test** (parked, red panda on the
EPS bus — a new ID won't reach the comma panda; watch for 0x555 @62.5 Hz AND any bus disruption): (1) how FCN0
handles a mailbox armed outside its `gp-0x1744` software bookkeeping (controller behavior, not disasm-closable);
(2) whether ID 0x555 collides with another ECU's frame. This is a mechanism test; swapping the fixed payload
for real cell telemetry is trivial once the mechanism + gateway-visibility are confirmed on-car.
