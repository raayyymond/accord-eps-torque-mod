---
name: reference-accord-a160-rdbi-dispatch-table-offbyone
description: "2026-07-10 Ghidra byte-verified (code.bin/master.bin, program 'code.bin' in accord2020_ghidra): the RDBI (SID 0x22) per-DID dispatch table used by the app-UDS stack is NOT handler-pointer-indexed at +0x0C as docs/guides/SPEC-uds-can-ram-telemetry-a160.md and builds/telemetry/build_uds_telem_tva.py assumed. True table base is 4 bytes earlier (0xB77FC, not 0xB7800), the 'handler pointer' field is dead/unread data program-wide, and the real dispatch is a DID-index -> 1-byte groupID -> 7-slot function-pointer jump table (0xB7568). This explains the empirical 'DID 0x4801 telemetry always returns constant bytes' result: the built cave handler at 0xC4E00 is never invoked."
metadata:
  type: reference
---

# Accord A160 app-UDS RDBI dispatch: table-base off-by-one + dead handler-ptr field (2026-07-10)

> **PARTIAL CORRECTION (same day, later session):** the "handler_ptr field is dead data — never read
> anywhere" conclusion below is RETRACTED. `FUN_000209ea` reads and calls it on the live path — see
> [[reference-accord-a160-rdbi-handlerptr-live-dispatch]] for the full correction, byte evidence, and the
> revised (correct) patch design. The table-base/off-by-one finding itself (0xB77FC true base) remains
> correct and is unaffected.

## Why this exists

Investigated an empirical result: the `39990-TVA,A160-UDStelem-DID4801-RAMread-...rwd` build (repurposing DID
`0x4801` to read `gp-0x6a62/gp-0x6a5e/gp-0x4f68/gp-0x6cc4` via a cave handler at `0xC4E00`, per
`docs/guides/SPEC-uds-can-ram-telemetry-a160.md` and `analysis-2020accord/builds/telemetry/build_uds_telem_tva.py`) returns
**bit-exact-identical bytes on every request**, across sessions, even under full-range steering-torque input.
Traced the REAL dispatch path in Ghidra (`code.bin`, gp=0xFEDF8000, tp=0xBF000) to find out why.

## CONFIRMED: the true per-DID table base is `0xB77FC`, not `0xB7800`

Three independent call sites all key off `tp - 0x7804 = 0xB77FC` (tp=0xBF000), stride `0x14` (20 bytes):

1. **DID→index binary search**, `FUN_00020d3a` (0x20d3a-0x20d75): `ep = tp + idx*0x14; ld.hu -0x7804[ep]` —
   compares the DID key against `*(u16*)(0xB77FC + idx*0x14)`. Binary search over `idx` range `[0,0x1b]`
   (28 entries), requires the table to be **DID-sorted** — confirmed by direct byte read (see table below).
2. **Length precheck**, `FUN_00020cd4` (0x20cd4-0x20ce0): `ep = (tp-0x7804) + idx*0x14; sld.hu 0x2[ep]` —
   reads `*(u16*)(0xB77FC + idx*0x14 + 2)`.
3. **Group-ID dispatch**, inside `FUN_00020fc4` (0x20fc4-0x21033), disasm-confirmed:
   `ep = (tp-0x7804) + idx*0x14; ep = *(byte*)(ep+0xC)` — reads a **1-byte group ID** at
   `0xB77FC + idx*0x14 + 0xC`.

Meanwhile `FUN_00020ce2` (the session/SA gate-check, called from `FUN_00020f0a`'s validate loop) uses base
`tp - 0x7800 = 0xB7800` (4 bytes LATER) for its own field reads (`param_1+4` = session mask). This is the
base the earlier SPEC session anchored on, because raw sequential reads starting at `0xB7800` happen to
produce plausible-looking `gate/session/flags/handler-ptr/DID/len` fields — **but the DID and declared-len
fields read that way are shifted one whole entry (0x14 bytes) relative to the entry that owns the
gate/session/handler-ptr fields you're reading them alongside.**

## CONFIRMED: full byte-verified table read, `0xB77FC`-based, resolves the true struct

Read 560 bytes (28 entries × 20B) from `0xB77FC`. True struct layout (20 bytes):
`u16 did; u16 declared_len; u32 gate_flags; u32 session_mask; u32 group_flags(low byte=dispatch groupID); u32 handler_ptr;`

| idx | DID | declared_len | groupID | handler_ptr (dead, see below) |
|---|---|---|---|---|
| 0 | `0x4800` | 0x38 | 0x00 | `0x0004D5C2` |
| **1** | **`0x4801`** | **0x38** | **0x04** | **`0x0004D8DC`** |
| 2 | `0x480A` | 0x38 | 0x00 | `0x0004DDFC` |
| 3 | `0x480B` | 0x38 | 0x00 | `0x0004E368` |
| ... | ... | ... | ... | ... |
| 25 | `0xF180` | 0x10 | 0x00 | `0x0004F6D6` |
| 26 | `0xF181` | 0x10 | 0x00 | `0x0004F6FA` |
| 27 | `0xF186` | 0x02 | 0x00 | `0x0004F72C` |

**This retracts/corrects `docs/guides/SPEC-uds-can-ram-telemetry-a160.md`'s table (which listed `0:0x4801/4D5C2`,
`25:0xF181/4F6D6`) and the prior memory `reference_accord_a160_app_uds_session_gate_and_egress.md` §2's
claim that `FUN_0004D5C2` is "DID 0x4801 handler" — `FUN_0004D5C2` is DID `0x4800`'s handler-ptr-field value;
DID `0x4801`'s true index is 1, not 0.** (Both docs' off-by-one has the SAME root cause: reading the raw
ROM window starting at `0xB7800` instead of the true base `0xB77FC`.)

## CONFIRMED: the `handler_ptr` field (SPEC's "+0x0C", true "+0x10") is DEAD DATA — never read anywhere

Exhaustive whole-program `search_instructions` for every addressing idiom that could load a 4-byte pointer
at displacement 0xC or 0x10 from any base (`ld.w`/`sld.w`, bracket `0xc[`/`0x10[` EP-relative form AND comma
`0xc,`/`0x10,` general-register form) returns **zero hits** in the RDBI code region. Independently,
`get_xrefs_to(0x4d5c2)` (the function the build/SPEC believed was DID 0x4801's handler) returns **zero
references**. This field is either vestigial (leftover from an earlier dispatch design) or reserved/unused
— **patching it (as the build does at `0xB780C`) has no runtime effect regardless of which DID's entry you
think you're targeting**, because no code path ever reads it.

## CONFIRMED: the REAL dispatch is DID-index → 1-byte groupID → 7-slot function-pointer table `0xB7568`

`FUN_00020fc4` (raw disasm, 0x20fc4-0x21033) is the actual per-DID invocation loop (pass 2, after
`FUN_00020f0a`'s validate/pass-1 populates a DID-index array at `gp-0x1574` and a per-DID call-bitmask at
`gp-0x1569`). For each validated DID: `groupID = *(byte*)(0xB77FC + idx*0x14 + 0xC)`, then
`handler = *(u32*)(0xB7568 + groupID*4)`, called as `handler(ctx)` via the V850 manual-lp
`mov <retaddr>,lp; jmp [handler_reg]` indirect-call idiom (raw disasm-confirmed at `0x21004-0x2100e`).

Byte-read jump table `0xB7568` (7 slots, 0-6):
`0:0x00020CC4  1:0x0004D388  2:0x000201D0  3:0x00020FC4(self)  4:0x0004D8EA  5:0x00020EDA  6:0x00050DB2`

**DID `0x4801`'s groupID = `0x04`** (byte-verified twice, at `0xB781C`) → dispatch target = **`0x0004D8EA`**
(word4 of the jump table, byte-verified twice from independent reads).

## CONFIRMED: `0x0004D8EA` — the function that ACTUALLY runs for every DID-0x4801 request — is a 2-instruction no-op stub

```
0004d8ea: st.w r0, -0xff4, gp     ; *(u32*)(gp-0xFF4) = 0   (clears one global flag)
0004d8ee: jmp lp                   ; return
```
It does **not** call `FUN_000211ba` (response-SM prepare), does **not** call `FUN_0002114e` (append), does
**not** call `FUN_0002073a` (finalize), and does **not** touch any of `gp-0x6a62/gp-0x6a5e/gp-0x4f68/gp-0x6cc4`
(the 4 gentle-EME telemetry signals) or any other RAM read. **No response payload is built by the real,
executed DID-0x4801 dispatch step, at all.**

For context: the SIBLING function `0x0004D8DC` (14 bytes earlier — sets the SAME `gp-0xFF4` flag to 1 instead
of 0, then tail-jumps into `0x0004D890`, a RoutineControl-status-style function gated on
`gp-0x105c==1 && gp-0x1060==2` that, only if that gate passes, appends a fixed 2 zero-bytes and finalizes)
is DID `0x4801`'s dead `handler_ptr` field value — i.e. it LOOKS like a real, plausible response builder, but
per the confirmed dispatch mechanism above, it is never reached from the DID-0x4801 request path either.

## BOTTOM LINE

**The build's premise was wrong at the table-indexing level, independent of any encoding/CRC correctness in
the build itself (which was internally self-consistent and byte-verified against its OWN — incorrect —
assumptions).** The cave handler at `0xC4E00` (72 bytes, reads the 4 gentle-EME RAM globals, byte-verified
correct AS WRITTEN) is **never invoked** by any live request, because:
1. The patched field (`0xB780C`, "handler_ptr") is dead data on this firmware — nothing reads it, for any DID.
2. Even under the correct table-base (`0xB77FC`), DID `0x4801`'s real dispatch (groupID 4 → `0x0004D8EA`)
   is a stock no-op stub that builds no response data.

The declared-length edit at `0xB7812` DOES land on DID 0x4801's own true `+0x02` field (56→10) — a real edit,
but with no reachable payload-building code to make it matter for THIS DID.

**Given no code path builds fresh response data for a DID-0x4801 request, whatever 8-10 bytes come back over
CAN on a live read must be either (a) stale content already sitting in the shared response buffer from a
prior transaction/boot state, or (b) all-zero/echo bytes from the framework's own generic handling — NOT a
live RAM read of anything, torque-related or otherwise. This is the most likely explanation for
"bit-exact-identical response regardless of session or torque input," though the exact buffer-lifecycle
mechanism that produces those specific observed bytes was not further traced (see Open Questions).**

## What this means for a working telemetry channel

The `0xB77FC`-based, groupID-mediated dispatch means **any patch to this table must target the TRUE-index
struct** (did@+0x00, declared_len@+0x02, gate@+0x04, session@+0x08, groupID-byte@+0x0C, dead-ptr@+0x10), and
critically must **change the groupID byte to select (or add) a jump-table slot whose target actually calls
`FUN_000211ba`/`FUN_0002114e`/`FUN_0002073a`** — patching the dead `handler_ptr` field alone will never work,
regardless of which DID or index is chosen. Two viable redesigns:
- **(a) Repoint an EXISTING groupID slot** in `0xB7568` (7 slots, 4 bytes each) to the `0xC4E00` cave, for a
  groupID that's either unused by any OTHER live DID, or shared only with DIDs safe to also redirect.
- **(b) Give DID 0x4801 a NEW groupID** (edit the byte at `0xB77FC + 1*0x14 + 0xC = 0xB780C`... **NOTE**: this
  is numerically the SAME address the original build already patches for a different reason — confirm no
  collision — for consistency, use the TRUE-scheme address `entry1_base(0xB7810) + 0xC = 0xB781C`) that maps
  through a new/appended `0xB7568` slot to the cave — requires extending the 7-slot table (check for free
  space after `0xB7584`, which is even more dead-table-adjacent territory not yet mapped).

Either redesign needs the SAME re-verification discipline as before (byte-diff, Ghidra disassemble the
emitted image, confirm the NEW groupID's jump-table slot resolves to the cave) — but this time verified
against the `0xB77FC`-true table, not the `0xB7800`-shifted one.

## Open questions / verification needed

1. **What actually calls `FUN_00020fc4` (pass 2) for a real request?** `get_xrefs_to(0x20fc4)` shows only a
   DATA ref from `0xB7574` (i.e. it's ITSELF group-3's jump-table target — self-referential/recursive-looking
   dispatch design). Checked `FUN_0002067c` (state=1 handler in the `FUN_0002073a` state-dispatch) — it does
   NOT call `FUN_00020fc4` directly; it calls `FUN_00020658` (unexamined) twice. The exact trigger chain from
   "RDBI request validated" to "pass-2 DID loop actually runs" was not fully closed. Next step: disassemble
   `FUN_00020658` and, if needed, trace `FUN_0002075c` (SID top dispatcher) post-`FUN_00021036`-call for a
   direct/indirect call to `FUN_00020fc4`.
2. **What are the exact stale/leftover bytes the operator's DID-0x4801 read returns?** Not traced — would
   need either a live RAM capture of the response-buffer region (`*(gp-0x1530)` deref `+0x18`) immediately
   before/after a request, or continued static trace of buffer initialization/clearing across the request
   lifecycle. Flagged as INFERRED explanation, not proven byte-for-byte.
3. **Groups 1,2,5,6 of the `0xB7568` jump table** (`0x0004D388`, `0x000201D0`, `0x00020EDA`, `0x00050DB2`)
   were not disassembled — one of these might be the "real" generic multi-byte RAM-read handler class used
   by OTHER working DIDs, useful as a template for redesign option (a)/(b) above.

Links: [[reference-accord-a160-app-uds-session-gate-and-egress]] (§2's `FUN_0004D5C2` DID attribution is
superseded by this doc — flagged for operator-approved correction, not silently edited) ·
[[reference-accord-telemetry-ram-hook-a160]]
