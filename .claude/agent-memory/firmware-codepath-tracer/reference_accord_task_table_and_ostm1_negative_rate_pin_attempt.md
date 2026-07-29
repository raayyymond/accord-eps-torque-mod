---
name: reference_accord_task_table_and_ostm1_negative_rate_pin_attempt
description: Attempt to pin FUN_00022ca0's (assist-shaping task) scheduling rate, needed to resolve the boost lane (gp-0x6bbe) dB ambiguity between -1.3dB(1kHz) and -14.9dB(100Hz). Found the real 7-entry RTOS task-control-block table (FUN_0002214a=entry1, FUN_00022ca0=entry5) but could NOT locate its dispatcher or any period/divisor field. Confirmed OSTM1 (the chip's second hardware OS-timer) is never configured anywhere -- rules out "a second timer paces the slow task" cleanly. Net: rate still NOT pinned, bounds 100-1000Hz unchanged, but two candidate mechanisms (in-task divider, second HW timer) are now ruled out, shifting weight of evidence toward 1kHz.
metadata:
  type: reference
---

**Context**: `gp-0x6bbe` (boost) and `gp-0x6bd0` (damping), two of the 11 `gp-0x6b98` aggregator summands
(`reference_accord_gp6b98_aggregator_definitive_lane_table_v57.md`), both run the same alpha=205/1024
single-subtraction EMA on the raw torque sensor, and boost is SAME-SIGNED (reinforcing, not opposing) per
that same memory. Their host task `FUN_00022ca0`'s rate decides whether `|H(21Hz)|` is -1.3dB (1kHz, a
proportional near-unity positive-feedback path -- the strongest surviving 21Hz suspect after V56 eliminated
`gp-0x6ad4`) or -14.9dB (100Hz, meaningfully filtered). `get_function_callers(FUN_00022ca0)` returns null.

## Found: the real RTOS task-control-block table -- 7 entries, both target functions present

LE32 literal scan for `0x0002214A` and `0x00022CA0` (the two task entry points) each found exactly ONE
hit in the whole image: `0xBB928` and `0xBB9E8`. Backed out to an index array at `0xBB858` (7 pointers:
`0xBB920/950/980/9B0/9E0/A10/A40`), each pointing 4 bytes before a 48-byte (`0x30`-stride) record:

| slot | fn ptr | note |
|---|---|---|
| 1 | `FUN_0002214a` | confirmed ~1kHz control task |
| 2 | `FUN_00022A88` | unidentified, immediately adjacent in memory to `FUN_0002214a`'s body end (`0x22a87`) |
| 3 | `FUN_00022B20` | unidentified; this entry's `+0x24` handler ptr differs from all others (`0xBB8EC`->`0xBBC3C` vs the shared `0xBB8B8`->`0xBBC40`) |
| 4 | `FUN_00022B24` | unidentified |
| 5 | `FUN_00022CA0` | **the assist-shaping task, target of this investigation** |
| 6 | `FUN_0002351E` | unidentified |
| 7 | `FUN_00014C5C` | the boot-init + outer state-poll dispatch loop (see below) -- priority/index field = 0, i.e. lowest |

Record layout (48 bytes, verified by diffing slot1 vs slot5 byte-for-byte): `+0x00` = `07 <priority?> <1-based index> 00`; `+0x04` = function pointer; `+0x08` = per-task RAM workspace base (sequential allocation, e.g. `0xFEDEC000` for slot1, `0xFEDEC7B0` for slot5); `+0x0C` = `low16(workspace size?) | high16=0x0100(const)` -- **slot1 and slot5 share the identical value `0x7A4`=1956 here**, the only other shared pair being slot2/slot4 (`0x6DC`=1756); `+0x10` = 0-based ordinal (redundant with `+0x00` byte2); `+0x14..0x23` = reserved/zero; `+0x24` = shared handler pointer (`0xBB8B8`->`0xBBC40` for 6 of 7 slots, slot3 alone uses `0xBB8EC`->`0xBBC3C`); `+0x28` = constant `1`; `+0x2C` = another per-task gp-relative pointer, sequentially allocated.

**No field in either record encodes a period, divisor, or tick count in any unit identifiable from the
data alone.** The `+0x00` byte1 sequence across all 7 slots in address order is `6,4,5,3,2,1,0` -- looks
like a priority level (task7/the idle loop = 0, lowest), not a rate.

## Could NOT find the table's dispatcher -- flagged, not guessed

The table base `0xBB858` is unreachable via gp-relative (offset from `gp`=0xFEDF8000 is ~19.7M, past the
23-bit extended-displacement range), tp-relative (exhaustive `search_instructions(mnemonic=movea,
operand=", tp,")` scan, ~200 hits, none at disp `-0x37A8` = `0xBB858-0xBF000`), or a raw 32-bit immediate
load (LE32 literal scan for `0xBB858` itself: zero hits, whole image). Whatever walks this table uses a
base register or indirection not found this session. **Next step, if resumed: full disassembly (not just
decompile) of `FUN_00014c5c`'s five housekeeping callees (`FUN_000197d0`, `FUN_000195da`, `FUN_0001cad2`,
`FUN_0001561c`, `FUN_0001600a`), or the interrupt vector table directly.**

## `FUN_00014c5c` decompiled in full -- confirmed NOT the caller of either target, and NOT a periodic wait loop

One-time init: `OSTM0CTL=1`, `OSTM0CMP=0x1387F`(79487) -- matches the already-recorded reload value
exactly (cross-validated fresh). Main body: `do { switch(gp-0x67fa) { call one of 3 functions } ;
[4 more housekeeping calls, always] } while(true)` -- **no wait/semaphore/interrupt-mask primitive
anywhere in the loop.** It is an unthrottled busy-poll, and none of its calls are `FUN_0002214a` or
`FUN_00022ca0`. This is task-table slot 7 (priority 0) -- confirms the real dispatcher for slots 1-6 is
a DIFFERENT mechanism than this loop.

## `gp-0x67fa` reconfirmed as a state machine (not a phase/round-robin counter) -- corroborates prior record

Byte scan found ~32 distinct `st.b -0x67fa[gp]` writer sites clustered in `0x19816-0x1A0BA`, each using a
different source register (the signature of an explicit state-transition switch, not an increment).
Fresh disassembly of `FUN_00022ca0`'s entry (`0x22ca4: ld.bu -0x67fa[gp],r9`) confirms it reads the SAME
variable, gated identically to the already-documented `FUN_00034350` `{4,5,11}`-state gate
(`reference-accord-sign-source-rate-not-divided.md`) -- reproduced fresh at `0x22db2: andi 0x830,r25,r28`.
**No `FUN_00014be4`-mediated divider found between the gate and `FUN_0002b62c`/`FUN_00034350`/
`FUN_00034a72`** -- re-derives, does not newly discover, that memory's conclusion.

## NEW NEGATIVE: OSTM1 (second hardware OS-timer) is never configured

Per the SVD: `OSTM1` base `0xFF801020`, `OSTM1CMP` at `0xFFFFC100`. Checked both the r0-relative disp16
store encoding that configured `OSTM0CMP` (`st.w r1,-0x4000,r0`) and a `movhi`+`movea` absolute-address
construction for `OSTM1CTL` -- **zero real hits** (the only `movhi -0x80,r0,rX` matches target unrelated
`0xFF80xxxx` peripherals, confirmed by reading the following instruction: e.g. `0x5C7CA` builds
`0xFF802010`, a different device entirely). **This rules out "a second hardware timer paces a slower task
class" as cleanly as a byte-scan can rule out anything.**

## Net verdict

Bounds unchanged: **100Hz-1000Hz, still not pinned.** But two of the four candidate mechanisms
team-lead named (in-task divider, second HW timer) are now ruled out, and the found task-table + shared
state-gate architecture is at least suggestive (not proof) of `FUN_00022ca0` running on the same OSTM0-
driven cadence as `FUN_0002214a`, with the table's priority field affecting preemption order rather than
period -- the ordinary RTOS case. Weight of evidence shifted toward 1kHz this session; the clean
architectural counter-argument for ~100Hz (slower human-bandwidth comfort task, per
`reference-accord-sign-source-rate-not-divided.md`'s corner-frequency argument) still stands unrefuted.

Recomputed `|H(21Hz)|` with the single-subtraction form `H(z)=a/(1-(1-a)z⁻¹)`, alpha=205/1024=0.2002,
independently reproduces team-lead's pre-stated figures exactly: fs=1000Hz -> pole=0.7998,
|H|=0.8618 -> **-1.29dB**; fs=100Hz -> |H|=0.1796 -> **-14.91dB**.

`0xC6372`/`0xC636E` reconfirmed never edited in any `build_v*_tva.py` through `build_v57_tva.py`
(STOCK_CALS lists only) -- matches record, no lever proposed here.

## Related
[[reference-accord-sign-source-rate-not-divided]] -- the prior session's coefficient-plausibility work and
the "no in-task divider" finding this session reproduces independently.
[[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]] -- source of the boost/damping dB figures
this rate question decides between.
[[reference_accord_ostm0_master_tick_rate_derivation]] -- the OSTM0 reload-value derivation this session
cross-validated fresh inside `FUN_00014c5c`'s decompile.
