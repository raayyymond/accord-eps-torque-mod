---
name: reference-accord-v34-state4-suppression-downstream
description: Full downstream trace of V34 (NOP 0x40de2/0x40e12, suppressing FUN_00040d58 return-4). Caller FUN_00041222/FUN_00041304 treat return 2 and 4 IDENTICALLY (binary r10==0 test, not value-specific). The actual ENGAGED/HOLDING-exit transition (FUN_00040d38(8)/(3)) is gated by an INDEPENDENT signal (gp-0x67FE==2 + gp-0x138D/E or gp-0x1390, driven by FUN_000405fe), not by the decider's return code -- so V34 does not disable that exit path, only the angle-consensus TRIGGER for it. gp-0x35B5 (the byte that would distinguish 2 vs 4) is WRITE-ONLY: its sole reader FUN_00040d02 has zero callers anywhere in the 1MB image.
metadata:
  type: reference
---

# V34 (state-4 suppression) downstream trace -- 2020 Accord TVA-A160

Byte-level walk, radare2 `v850.gnu`, stock `code.bin`, gp=0xFEDF8000, tp=0xBF000. Session 2026-07-03,
verifying `build_v34_tva.py`'s patch (`0x40DE2 be->nop`, `0x40E12 bh->nop`, both targeting `0x40e1a: mov 4,r12`).
Builds on [[reference-accord-engage-sm-second-gate-gp6cc4]] and [[reference-accord-gp6cc4-tracking-pipeline]].

## 1. FUN_00040d58 full return-value map [V]
Linear `pd` of 0x40d58-0x40e78 (complete, clean decode, no undecoded opcodes):
```
param 0/default: r12=0 (stay)
param 1 (ENGAGING): r12 = 0 (engage success) | 2 (gp-0x6a62>=cal, torque refuse) | 5/6/7 (gate refuse, shared tail with param 4)
param 2 (ENGAGED):  r12 = 0 (stay) | 2 (gp-0x6a62 sentinel/threshold) | 4 (FUN_000406ae()==0, V34 target)
param 3 (HOLDING):  r12 = 0 (stay) | 2 (gp-0x6a62 sentinel/threshold) | 4 (|gp-0x6CC4|>cal 0xC6354, V34 target)
param 4 (RE-ARM):   r12 = 0 (?) | 5 | 6 | 7
```
The commit: `0x40e64 st.b r12,-13750[gp]` (gp-0x35B6) runs for EVERY non-zero-shortcut return (2/4/5/6/7); the
r12==0 stay path skips it (redundant, already 0) via a direct `br 0x40e68`. `0x40e68: mov r12,r10; dispose
0,{lp},lp` -- **the dispose's third operand IS the return jump (jmp[lp]); FUN_00040d58 truly ends at 0x40e6a.**
Code at 0x40e6e+ is TWO SEPARATE tiny functions, not a fallthrough tail:
- `FUN_00040e6e` (0x40e6e-0x40e72): `st.b r0,-13749[gp]; jmp[lp]` -- clears gp-0x35B5 to 0.
- `FUN_00040e74` (0x40e74-0x40e7c): `ld.bu -13750[gp],r14; st.b r14,-13749[gp]; jmp[lp]` -- commits gp-0x35B5 = gp-0x35B6.

## 2. Caller does NOT distinguish return 2 vs 4 -- byte-verified [V]
`FUN_00041222` (ENGAGED, dispatcher state 7) at `0x41280: jarl 0x40d58,lp` (param 2), then:
```
0x41284  cmp r0,r10
0x41286  be 0x4128e          ; r10==0 -> STAY handling
0x41288  jarl 0x40e74,lp     ; r10!=0 (2 OR 4, no further distinction) -> commit gp-0x35B5=gp-0x35B6
0x4128c  br 0x412b2          ; -> shared tail (SAME tail the STAY branch also falls into)
```
`FUN_00041304` (HOLDING, dispatcher state 8) has the **structurally identical** pattern at
`0x41364: jarl 0x40d58,lp` (param 3) / `0x41368-0x41372`. **Confirmed: the caller's only branch on the
decider's return is a binary `r10==0` test. Return codes 2 and 4 are indistinguishable to the caller** --
this corrects any assumption that state 4 routes to a materially different consequence than state 2.

## 3. The REAL exit-from-ENGAGED trigger is INDEPENDENT of the decider's return value [V — major finding]
Full decode of the shared tail `0x412b2-0x41300` (ENGAGED) and `0x41386-0x413aa` (HOLDING):
```
0x412b2  ld.bu -26622[gp],r15   ; gp-0x67FE (status/mode byte)
0x412b6  cmp 2,r15 / bh 0x41300 ; r15>2 -> no transition, dispose
0x412ba  cmp 2,r15 / bne 0x41300 ; r15!=2 -> no transition, dispose  (net: ONLY r15==2 continues)
0x412be  ld.bu -5006[gp],r8     ; gp-0x138E
0x412c2  cmp 1,r8 / bne 0x412de
0x412c6..0x412d8  FUN_00040d38(8) -> dispatcher state = 8 (HOLDING), clear gp-0x138E, FUN_00040d2c(1)
0x412dc  br 0x412fc
0x412de  ld.bu -5005[gp],r6     ; gp-0x138D
0x412e2  cmp 1,r6 / bne 0x41300
0x412e6..0x412f8  FUN_00040d38(3) -> dispatcher state = 3, clear gp-0x138D, FUN_00040d2c(0)/FUN_00040d14(0)
0x412fc  jarl 0x40e6e,lp        ; clear gp-0x35B5 (ALWAYS, both transition arms)
0x41300  dispose ...
```
**This tail runs on EVERY cycle regardless of r10** (both the r10==0 STAY branch at 0x4128e-0x412ae and the
r10!=0 branch at 0x4128c fall into it). `gp-0x138D`/`gp-0x138E` are precomputed ONLY inside the r10==0 (STAY)
branch, via `FUN_000405fe()` (an external accessor -- return value compared against a cached "last request"
byte `gp-0x138F`), latched sticky until consumed. **The state-7-exit transition (`FUN_00040d38(8)` or `(3)`)
is gated on `gp-0x67FE==2` + these latched request flags -- NOT on whether the decider returned 0, 2, or 4.**
HOLDING's tail (`0x41386-0x413aa`) is the same pattern with a single flag (`gp-0x1390`, disp -5008, the SAME
"current external request" cache byte ENGAGED also writes) instead of the 2-flag pair.

**Consequence for V34:** disabling decider-return-4 (and, via V33, return-2) does **NOT** disable the
ENGAGED/HOLDING exit mechanism itself -- that mechanism is driven by `gp-0x67FE`/`FUN_000405fe`, presumed to
be an independent request source (driver cancel, ACC handoff, etc., NOT traced to its own producer this
session). It only removes the angle-consensus (and torque-magnitude) signal as a way to REQUEST that exit.
Under V34, since r10 is now always 0, `FUN_000405fe`'s precompute runs on literally every cycle (previously
it could be skipped on a leave-cycle) -- if anything this makes the independent-request exit path MORE
consistently serviced, not less.

## 4. gp-0x35B5 is WRITE-ONLY -- no static reader found anywhere in the 1MB image [V — exhaustive byte scan]
Full-image byte-pattern scan (not just the local cluster) for `ld.bu -13749[gp]` (byte0=0xa4, disp bytes
`4b ca`, byte1 = valid `(reg<<3)|7`): **exactly 1 hit, `0x40d02`** -- a tiny one-instruction accessor
(`ld.bu -13749[gp],r10; jmp[lp]`), i.e. `FUN_00040d02`. A whole-image JARL-target scan (validated against 4
known-good call sites first) for callers of `0x40d02` found **zero hits**. Cross-checked: the SAME scan
methodology correctly found all known callers of neighboring functions (`FUN_00040d14`: 9, `FUN_00040d2c`: 5,
`FUN_00040d38`: 17, `FUN_00040d58`: 7, `FUN_0003d04c`: 14), so the null result for `0x40d02` is not a
methodology gap for nearby, structurally similar targets. **gp-0x35B5's only 2 writers are `FUN_00040e6e`
(clear to 0) and `FUN_00040e74` (commit from gp-0x35B6) -- both already covered above.**
**Practical implication:** the byte that WOULD distinguish "torque disengage"(2) from "angle-consensus
leave"(4) from "stay"(0) has no confirmed static consumer in this firmware image. Whatever produces the
operator-reported "no_torque_alert_2" STEER_STATUS distinction, it is **not** sourced from gp-0x35B5 via any
statically-reachable path found this session -- either it's a dead vestige, or it's read via an indirect
mechanism (function-pointer table, DMA'd struct) outside a static JARL/byte scan's reach. **Open, not
resolved.**

## 5. FUN_00040d38 (dispatcher-state setter) -- byte-verified, corrects prior memory's shadow address [V]
```
0x40d38  ld.bu -26524[gp],r13   ; gp-0x67DC (current dispatcher state)
0x40d3c  ld.bu -19509[gp],r15   ; shadow -- disp -19509 = -0x4C35 (gp-0x4C35), NOT gp-0x4CCB as
                                  ; reference_accord_gp6cc4_tracking_pipeline.md states (0x4CCB=19659 decimal,
                                  ; a transcription slip -- 19509 decimal = 0x4C35 exactly). CORRECTION FLAGGED,
                                  ; not yet applied to that file per the "ask before updating" rule.
0x40d40  cmp r15,r13 / bne 0x40d4e  ; mismatch -> fault
0x40d44  st.b r6,-26524[gp]     ; commit new state
0x40d48  st.b r6,-19509[gp]     ; commit shadow
0x40d4c  br 0x40d56 / jmp[lp]
0x40d4e  movea -19509,gp,r6 / jr 0x0006b9fa   ; LOCKSTEP FAULT on shadow mismatch
```
V34 does not touch FUN_00040d38, its shadow, or the lockstep check at all -- no new desync risk introduced.

## 6. FUN_000406ae fully re-disassembled (0x406ae-0x40880) -- confirms NO fault/DTC side effect [V]
Complete linear decode. The ONLY external calls inside are 5x `jarl 0x00049a5a` (the pure `ABS()` helper,
no memory writes, no calls -- `cmp r0,r6/cmov ge.../bge.../subr r0,r10/jmp[lp]`). The ONLY memory write is
the conditional `st.w r12,-13740[gp]` (gp-0x35AC) at 0x40862, gated by the 4-way agreement mask (`cmp
15,r26; be 0x4081c` skip). **No `jarl FUN_0006b9fa`, no `jarl FUN_00046ea6` (diagnostic logger), no DTC path
anywhere in this function.** Since V34 retains the `jarl FUN_000406ae` call unmodified (only nops the
caller's REACTION to its return value), this function's internals and its one side effect run byte-identically
to stock every cycle -- **the NOP cannot newly trigger a fault via this function; direct evidence, not
inference.**

## 7. gp-0x35AC (FUN_000406ae's confirmed-average) -- no external consumer found in cluster [V, cluster-scoped]
Textual scan of the 0x3c000-0x469dc cluster (40KB, covers the whole engage-SM/tracking-pipeline region):
exactly 2 refs to `-13740[gp]`, both inside FUN_000406ae itself (`0x40816` read, `0x40862` write). No reader
outside FUN_000406ae found in this cluster. **Correction to the mission's own guess:** gp-0x35ac =
`0xFEDF8000 - 0x35AC = 0xFEDF4A54`, not `0xFEDF3654` as the mission text speculated.
**Not a full 1MB scan** (unlike item 4's gp-0x35B5 check) -- flagged as cluster-scoped, lower rigor than item 4.

## 8. gp-0x67FE (the exit-transition gate byte) -- widely read, writer NOT found this session [OPEN]
Full-image `ld.bu -26622[gp]` byte-pattern scan: **55 static reader sites**, spanning `0x0290f8` to
`0x05577a` -- this is a broadly-consulted status/mode byte used far outside the engage-SM cluster. The
mirror `st.b -26622[gp]` byte-pattern scan (same signature class, byte0=0x44): **zero hits**. Either it's
written via a different instruction form (st.h, EP-relative/indexed store, bulk struct write) not covered by
this specific byte-pattern scan, or via an ISR/DMA path. **Not resolved this session** -- would need a
broader instruction-form sweep or Ghidra decompilation of one of the 55 read sites' enclosing function to
find the producer via data-flow rather than raw pattern matching.

## 9. 0x40e1a unreachability after the NOP patch [V for local cluster; reasoned for the rest of the image]
Full-image JARL-target scan (same validated methodology as item 4) found no JARL targeting 0x40e1a (expected
-- JARL targets are function entries; 0x40e1a is mid-function, immediately preceded by an unconditional `br
0x40e68` at 0x40e18, so it is neither a legal call target nor a fallthrough target). Textual scan of the full
0x3c000-0x469dc cluster's linear disasm found exactly 2 branches targeting `0x00040e1a`: `0x40de2` and
`0x40e12` -- the two V34 patches. V850 conditional short-branches are inherently local-range (empirically
observed deltas up to ~688 bytes within this function, nowhere near enough to reach 0x40e1a from outside the
~1KB engage-SM/tracking cluster). **Verdict: after the patch, `0x40e1a: mov 4,r12` is dead code -- reachable
by neither branch (both nop'd) nor fall-through (blocked by the preceding unconditional `br 0x40e68`).**
Residual, not exhaustively ruled out: an exotic 4-byte extended-branch form or a computed/indirect jump
(jump table) targeting this exact mid-function offset from far outside the cluster -- assessed as very low
probability (0x40e1a has no properties of a jump-table case target: it's not aligned to a case-table pattern,
and no jump-table structure was observed anywhere in this function or its callers) but not disasm-proven absent.

## Bottom line for the V34 fix
1. Suppressing state-4 is a clean, single-purpose removal: FUN_000406ae's internals/side-effects are
   unaffected (item 6), no other side action (counter reset, history-array reseed, re-arm ramp) was found
   tied specifically to the r12=4 arm inside FUN_00040d58 itself (item 1) -- the ONLY thing the nop changes is
   which value gets committed to the (apparently unread) gp-0x35B5 byte and whether the STAY-side
   `FUN_000405fe`/`FUN_0003d04c(4,0)` precompute runs that one cycle (item 3).
2. The dispatcher's actual mechanism for leaving ENGAGED/HOLDING (`FUN_00040d38(8)`/`(3)`) is NOT disabled by
   V34 -- it is gated by an independent signal (`gp-0x67FE`+ request-latch flags) whose producer was not
   traced this session (item 8). LKAS is not permanently unexitable under V34.
3. No hard-EME/DTC risk found: the only lockstep-fault path in this immediate cluster is FUN_00040d38's own
   shadow check (untouched by V34) and FUN_0006b9fa (never called from the code V34 touches or from
   FUN_000406ae).
4. Genuinely open: gp-0x35B5's real consumer (if any -- item 4) and gp-0x67FE's writer (item 8). Neither
   gap threatens the "is V34 clean" verdict, but both are loose ends in the broader STEER_STATUS/mode-SM
   picture worth closing with Ghidra decompilation if the operator wants full closure.

## Related
[[reference-accord-engage-sm-second-gate-gp6cc4]] [[reference-accord-gp6cc4-tracking-pipeline]]
[[reference-accord-lkas-engage-sm-disengage-trigger]] [[reference-accord-voter-0xffff-sentinel]]

## Correction flagged (not applied — ask operator first)
`reference_accord_gp6cc4_tracking_pipeline.md` states FUN_00040d38's shadow is "`gp-0x4CCB` (disp -19509)".
-19509 decimal = -0x4C35, not -0x4CCB (0x4CCB = 19659 decimal). This session's own disasm of FUN_00040d38
independently confirms disp -19509 at the shadow read/write/fault sites. Recommend correcting the label in
that file to `gp-0x4C35`.
