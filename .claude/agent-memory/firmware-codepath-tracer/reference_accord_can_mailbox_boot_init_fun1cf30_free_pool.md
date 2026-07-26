---
name: reference_accord_can_mailbox_boot_init_fun1cf30_free_pool
description: Accord TVA-A160 FCN0 boot-time all-64-mailbox init routine FUN_0001cf30 fully mapped — identifies a genuine free/inert mailbox pool (7-31) and a near-empty TX-armed pool (mailboxes 57-63, ID=0x00000000 at boot) as candidate injection points for a new CAN TX ID, better than a placeholder-ID hunt.
metadata:
  type: reference
---

# FUN_0001cf30 — FCN0 boot mailbox init, full 0-63 map (2026-07-24)

Disassembly-verified on stock `code.bin`. `FUN_0001cf30(param_1)` (`0x1cf30`-`0x1d46b`) is the boot-time
config routine for ALL 64 FCN0 message buffers — separate from, and upstream of, the slot-based
round-robin/dedicated system in `reference_accord_can_tx_full_table_decode_and_new_id_recipe.md` (mailboxes
0-6, which this function ALSO touches as part of its sweep). Called with literal `param_1=0` by both its
direct callers (`FUN_0001d5a6`, `FUN_0001fb48`) — no other `param_1` value confirmed invoked this session
(didn't check for indirect/computed calls).

## Mailbox pool map

- **0-6**: the already-mapped round-robin/dedicated TX pool (399/427/330/660/19F/32E/64D + 11 more).
- **7-31 (25 mailboxes) — genuine free/inert pool.** `STRB` explicitly written `0`; **no ID or DLC written
  at all** — left at HW power-on-reset (`MID0W` SVD default `0x00000000`). No `0x07FF` placeholder pattern
  exists anywhere in this pass (a byte-scan for `FF 07` found only one nearby hit, `0xB7260`, which is an
  unrelated entry — slot 17's bypass row in the OTHER table system).
- **32-55ish**: already TX-armed (`STRB` bit7 set) with real, distinct, populated arbitration IDs from a
  table at `0xB733C` (24 entries, 4B each, same `ID=entry>>18` formula validated elsewhere). Decoded all 24:
  0x638(dirty low bits, not a clean entry), 1934, 1882, 1834, 0x9BFC9202(anomalous, see below), 1786, 929,
  884, 808, 806, 804, 773, 490, 476, 464, 432, 420, 408, 380, 344, 316, 304, 228, 148. None are placeholders
  — this pool is live and populated, not a safe edit target.
- **★ 56-63 (7 of 8 mailboxes) — best candidate found for a new TX ID.** Also TX-armed at boot (`STRB` bit7
  set, same pattern as 32-55) but ID-sourced from a `param_1`-indexed table pair: `0xB719C`(MID0H) /
  `0xB718C`(MID1H), index = `iVar10 + param_1*8` where `iVar10` cycles 0-3 per 4-mailbox group. Dumped both
  tables at `param_1=0`: **mailbox 56 (index0) has a real, non-zero ID (~0x94/148); mailboxes 57-63
  (indices 1-7) are literal `0x00000000`** in both halves — i.e. already configured as TX buffers with an
  unassigned/zero ID. Structurally this is a cleaner injection point than hunting a placeholder-ID sentinel:
  the direction/STRB config is already done, only the ID halfwords + a periodic data-write/trigger need
  adding (reuse `FUN_0001d68e`'s `CTL=0x0100` then `0x0200` trigger idiom).

## Open items
- Anomalous shared pattern: `0x9BFC9203` (main table slot 15, mailboxes-0-6 system) and `0x9BFC9202`
  (this table's index 4, ≈mailbox 36) differ by exactly 1 — possibly a shared sentinel/special record
  reused across both table systems. Not resolved; flagged before editing near either.
- `param_1` values other than 0 not ruled out (no indirect-call search done).
- Exact mailbox-to-table-index alignment for the 32-55 range has a possible off-by-one (an apparent
  duplicate-looking value between this table's last clean entry and the 56-63 table's first entry, both
  decoding to ~148) — not chased further, low stakes for the recommendation above.

## Related
[[reference_accord_can_tx_full_table_decode_and_new_id_recipe]] — the mailbox 0-6 round-robin/dedicated
system this builds on; same `ID=entry>>18` decode formula reused and reconfirmed here on an independent table.
