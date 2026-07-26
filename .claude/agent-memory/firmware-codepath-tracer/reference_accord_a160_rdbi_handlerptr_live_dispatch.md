---
name: reference-accord-a160-rdbi-handlerptr-live-dispatch
description: "2026-07-10 Ghidra byte-verified (code.bin/master.bin AND the candidate _uds_telem_plain_image.bin, program accord2020_ghidra): CORRECTS reference_accord_a160_rdbi_dispatch_table_offbyone.md's claim that the per-DID 0xB77FC-table +0x10 'handler_ptr' field is dead data. It is NOT dead — it is the REAL per-DID payload-builder dispatch, called via a periodic state-machine (FUN_000209ea, serviced from w_steer_control_task), independent of the groupID/0xB7568 jump-table mechanism. This changes the correct patch design for DID 0x4801 telemetry from 'repoint a groupID jump-table slot' to 'patch the DID's own handler_ptr field directly' — and explains the previous build's actual bug (it patched DID 0x4800's handler_ptr, not 0x4801's)."
metadata:
  type: reference
---

# Accord A160 app-UDS RDBI: handler_ptr field IS live, called via FUN_000209ea (2026-07-10)

## Why this exists / what it corrects

`reference_accord_a160_rdbi_dispatch_table_offbyone.md` (same session-day, earlier) concluded the `+0x10`
"handler_ptr" field in the `0xB77FC` per-DID table is dead data — "exhaustive whole-program search_instructions
... returns zero hits" and `get_xrefs_to(0x4d5c2)` "returns zero references." That search missed
`FUN_000209ea` (0x209ea-0x20a9e). **This memory retracts the "dead field" conclusion.** The field is real,
read, and called on the live RDBI path — the earlier search's operand-pattern scope apparently didn't reach
this function despite it being in the same 0x20000-region address neighborhood.

## CONFIRMED: `FUN_000209ea` reads and CALLS the per-DID `handler_ptr` field

Full disasm 0x209ea-0x20a9e (program `code.bin`). Key sequence:
- Gate: only proceeds if `(*(byte*)(gp-0x1524)) & 7 == 1` (a "substate" byte) **AND** a "pending" bit
  (bit0 at absolute `0xFEDF6AAE` = `gp-0x1552`, tested via `tst1 0x0,0x6aae,r18` where `r18=0xFEDF0000`) is set.
- Reads cursor `gp-0x1553`, looks up `idx = *(byte*)(gp-0x1574 + cursor)` (the DID-index array pass-1
  populates — see the off-by-one memory), sets bit `cursor&7` in the call-bitmask `gp-0x1569` (this is a
  SEPARATE mechanism from what consumes that bitmask in `FUN_00020fc4` — see below), clears the pending bit.
- Computes `entry_ptr = 0xB77FC + idx*0x14` (true table base, confirmed again this session by direct read).
- Builds a LOCAL context struct at `gp-0x15f4` (fields at +0,+4,+8,+0xc,+0x10,... mirroring the exact struct
  `FUN_00021036` builds for its own `FUN_00020f0a` call): DID bytes echoed into the response buffer at
  `*(ctx+8)` (buffer write-cursor pointer), `*(u16*)(ctx+0xC) = 0` (length reset), buffer pointer advanced +2
  past the DID echo.
- `00020a8c: sld.w 0x10, ep, r28` — **reads `*(u32*)(entry_ptr + 0x10)` = handler_ptr, with `ep` = the TRUE
  entry pointer (verified: `ep` was set via `mov r6,ep` at 0x20a8a, and `r6` was saved from the SAME `ep` that
  computed session_mask at `entry_ptr+8` earlier in the function — traced register-by-register).**
- `00020a96/9c: mov 0x20a9e,lp; jmp r28` — **calls `handler_ptr(ctx = &(gp-0x15f4))`**, manual-lp indirect-call
  idiom (same pattern used elsewhere in this dispatcher).

Independently re-confirmed via `search_instructions(mnemonic=sld.w, operand_pattern="0x10, ep")`: the exact
instruction `00020a8c: sld.w 0x10, ep, r28` is in the result set (50-match, truncated) — the field IS read.

## CONFIRMED: this is THE live per-DID payload-builder ABI (ctx pointer, not the groupID scalar)

Compared two handler_ptr targets directly:
- **DID 0xF181's real handler `0x0004f6fa`** (idx26, groupID irrelevant): `mov r6,r26` (ctx ptr in r26),
  `st.h r14,0xc,r26` (`r14=0x10=16`, matches the DID's own declared_len from the table!), `jarl 0x211ba,lp`
  (same prep fn the cave uses), then `mov 0x13100,r6; mov 0xe,r7; jarl 0x2114e,lp` — loads a literal string
  pointer + length 14 and appends it via `FUN_0002114e`. **This is the app-id string builder** (matches the
  known-good `22 F1 81` response) — confirms `0xF181` builds its payload via ITS OWN handler_ptr, NOT via
  groupID slot0 (which is a 2-byte `jmp lp` no-op, see below) — closing the earlier open question of whether
  groupID-0 is a "generic reader." **It is not; it does nothing.**
- **The cave at `0xC4E00`** (re-read from the actual candidate build `_uds_telem_plain_image.bin`, since stock
  `code.bin` has this region blank/`0xFF` — cave code only exists in candidate images): `st.h r15,0xc,r6`
  (`r15=0xA=10`) — **writes directly to `r6+0xC`, i.e. treats r6 as the ctx POINTER on entry**, exactly the
  `FUN_000209ea`/`0x0004f6fa` ABI. Then `jarl 0x211ba,lp`; four `mov <addr>,r6; mov 0x2,r7; jarl 0x2114e,lp`
  blocks reading `gp-0x6a62`, `gp-0x6a5e`, `gp-0x4f68`, `gp-0x6cc4` (2 bytes each, computed as absolute
  `0xFEDF159E/0xFEDF15A2/0xFEDF3098/0xFEDF133C` = `gp-0x6a62/0x6a5e/0x4f68/0x6cc4` — arithmetic verified);
  `jarl 0x2073a,lp` (finalize). **72 bytes total (0xC4E00-0xC4E47), matches prior "72 bytes" claim.**

**Conclusion: the cave's ABI (ctx pointer in r6 on entry) matches the `handler_ptr` call site exactly, and
does NOT match the groupID/jump-table (`0xB7568`) call site**, which passes a masked SCALAR
(`andi 0xff,r6,r22` in `FUN_00020fc4`'s prologue) — repointing a groupID slot to the cave (the previously
proposed redesign options A/B) would call the cave with a garbage scalar "pointer," and `st.h r15,0xc,r6`
would write 2 bytes at whatever tiny absolute address that scalar represents — a real corruption risk, not
just "unreached."

## CONFIRMED (byte-read of the actual candidate build): the previous build's exact bug

Read `0xB77FC`+40 bytes from `_uds_telem_plain_image.bin` (the actual candidate output, not stock):
- **Entry0 (DID 0x4800, idx0)**: handler_ptr field (`0xB780C`) = `00 4e 0c 00` = **`0x000C4E00` — the cave
  address is patched HERE**, not on DID 0x4801. DID 0x4800's declared_len/gate/session/group fields all stock.
- **Entry1 (DID 0x4801, idx1)**: declared_len field (`0xB7812`) correctly edited `0x0038→0x000A` (this part of
  the original build WAS correct), but handler_ptr field (`0xB7820`) is **UNCHANGED stock `dc d8 04 00` =
  `0x0004D8DC`** — the cave was never wired to 0x4801 at all.

This is the SAME off-by-one root cause as the table-base bug already documented, now confirmed to have a
second consequence: it silently repointed DID **0x4800's** real handler (`FUN_0004D5C2`, the fault-flag
telemetry builder — confirmed live and unmolested in stock) to the cave instead. **If this candidate image
was ever flashed, DID 0x4800 reads would have returned the cave's 4-signal RAM read instead of DID 4800's
real fault-flag payload — a second, previously unflagged regression.** (Believed UNFLASHED per the operator's
build-state記録 — verify before assuming no real-car impact.)

## CONFIRMED: DID 0x4801's stock handler_ptr `0x0004D8DC` is not a no-op — explains the "always constant bytes" symptom

Disasm: `0004d8dc: mov 0x1,r15; st.w r15,-0xff4,gp; st.b r0,-0x33c4,gp; jr 0x0004d890` (tail call). `0x4d890`
takes ctx in r23 (`mov r6,r23`) and does a signed-16 read/shift/negate off `gp-0x4f60` before further
(unexamined) processing. **This retracts the earlier session's characterization of `0x0004D8DC`/`0x4d890` as
effectively inert** (that characterization was reached by assuming the groupID/slot4 path was the live one).
The true explanation for "bit-exact-identical response regardless of session/torque" is that DID 0x4801's
REAL stock handler (`0x0004D8DC`→`0x4d890`) runs and is gated by whatever state `gp-0x4f60`/the RoutineControl
flags are in during a plain diagnostic poll — not that no code runs at all. Not fully traced past `0x4d890`'s
first few instructions — lower priority now that the fix path (handler_ptr redesign) doesn't depend on it.

## CONFIRMED: full live call chain, SID 0x22 request → handler_ptr(ctx) invocation

`FUN_00021036` (SID 0x22/RDBI top handler, confirmed live: idx9 in service table `0xB7644`) →
`FUN_00020f0a` (pass-1 validate, called at `0x21092`) populates `gp-0x1574[0]=idx`, `gp-0x1554` (valid count).
On success (`gp-0x1567==0`), `FUN_00021036` @`0x2109e-0x210c4` UNCONDITIONALLY: sets `gp-0x1538=0`,
`gp-0x1536=1`, sets substate `gp-0x1524` low-3-bits to `1` (via `0x6adc`-absolute bit ops, `set1 bit0`,
`clr1 bit1`, `clr1 bit2`), and arms the SAME pending-bit `gp-0x1552` bit0 (`set1 0x0,0x6aae,r18`) that
`FUN_000209ea` gates on. Next tick of **`w_steer_control_task`** (the main periodic steering-control task,
confirmed via `get_xrefs_to`) → `FUN_00045d9e` → `FUN_00020c0a` → `FUN_00020bfc` → `FUN_00020aa2` →
`FUN_000209ea` fires, consumes cursor 0, calls `handler_ptr(ctx)`. Cursor `gp-0x1553` is written only by
`FUN_0001fe80` (a sibling per-tick worker, the ISO-TP frame-send/re-arm stage, itself gated on the same
substate==1) — no explicit reset-to-0 instruction was found in `FUN_00021036`; relies on BSS zero-init /
prior-cycle completion. Not fully proven but supported by the empirical "stable, repeatable response across
sessions" behavior already observed for the (buggy) candidate build.

## Corrected patch design (supersedes the groupID-jump-table redesign options in the off-by-one memory)

**Minimal correct patch — 3 fields, all in the TRUE `0xB77FC`-based table, entry1 = `0xB7810` (DID 0x4801,
idx1, stride 0x14):**
1. `0xB7812` (declared_len, u16 LE): `38 00` → `0A 00` (56→10 = 2 DID-echo + 4×u16 payload). Already correct
   in the existing candidate build — keep.
2. `0xB7820` (handler_ptr, u32 LE): `dc d8 04 00` → `00 4e 0c 00` (stock `0x0004D8DC` → cave `0x000C4E00`).
   **This is the fix the previous build missed.**
3. `0xB780C` (DID 0x4800's handler_ptr, u32 LE): must be **left at/restored to stock `c2 d5 04 00`
   (`0x0004D5C2`)** — the previous build incorrectly wrote the cave address here instead of at `0xB7820`.
   If building from the existing candidate image, this is a required REVERT, not a no-op.

No groupID field, no `0xB7568` jump-table edit, no NEW jump-table slot needed. The cave at `0xC4E00` (72
bytes, content re-verified this session from `_uds_telem_plain_image.bin`, byte-identical to the previous
session's description) requires NO changes — its ABI already matches the handler_ptr call site.

Links: [[reference-accord-a160-rdbi-dispatch-table-offbyone]] (superseded on the "handler_ptr is dead" point
only — the table-base/off-by-one finding in that memory remains correct and is the reason both bugs share a
root cause) · [[reference-accord-a160-app-uds-session-gate-and-egress]]
