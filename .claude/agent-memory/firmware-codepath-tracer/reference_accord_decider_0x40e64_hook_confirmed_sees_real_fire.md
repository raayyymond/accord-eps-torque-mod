---
name: reference_accord_decider_0x40e64_hook_confirmed_sees_real_fire
description: Accord TVA-A160 FUN_00040d58 (engage-SM decider) full disassembly confirms the V31P-V2 telemetry hook at 0x40e64 DOES execute on the real ENGAGED-context (param=2) torque-MAX disengage fire (0x40dd6 bnc taken -> 0x40dfc mov 2,r12 -> 0x40dfe br 0x40e64 -> EXECUTES). REFUTES the hypothesis that the hook only sees benign r12==2 and never the real disengage. The only paths that bypass 0x40e64 are pure-PASS shortcuts that write the identical value (0) 0x40e64 would have written anyway -- no data is lost.
metadata:
  type: reference
---

# FUN_00040d58 full disasm -- does the real disengage reach 0x40e64? YES (2026-07-13, Ghidra code.bin)

Full `disassemble_function(0x40d58)` obtained this session (68 instructions, 0x40d58-0x40e6a). Confirms and
extends `reference_accord_decider_shared_epilogue_trampoline_anchors.md`'s byte-level audit with the missing
piece: an explicit trace of every EXIT path to determine which ones reach 0x40e64 and which bypass it.

## The mission-critical case: param=2 (ENGAGED), torque-MAX gate fires
```
00040dc6: ld.hu -0x6a62[gp],r14      ; r14 = voterMAX (gp-0x6a62)
00040dca: xori 0xffff,r14,r0        ; sentinel test
00040dce: be 0x00040dfc             ; sentinel fire -> shared target
00040dd0: ld.hu 0x7312[tp],r16      ; r16 = cal 0xC6312 = 320
00040dd4: cmp r16,r14               ; computes r14-r16 = voterMAX-320
00040dd6: bnc 0x00040dfc            ; NOT taken iff voterMAX<320; TAKEN (fire) iff voterMAX>=320  <-- THE GATE
...
00040dfc: mov 0x2,r12               ; r12 = 2 (torque disengage code)
00040dfe: br 0x00040e64             ; unconditional branch to the shared epilogue
...
00040e64: st.b r12,-0x35b6[gp]      ; <-- HOOK SITE. EXECUTES with r12=2 on this path.
00040e68: mov r12,r10
00040e6a: dispose 0x0,{lp},[lp]     ; the ONLY dispose/return in the whole function
```
When the real torque-MAX disengage fires in the ENGAGED context (the mission's primary concern), control flow
provably reaches 0x40e64 and executes the hooked store with r12=2. There is no alternate exit for this specific
condition.

## What DOES bypass 0x40e64 -- confirmed benign-only
Three shortcut paths write `gp-0x35b6` directly and jump to 0x40e68 without touching 0x40e64:
- `param=0` case (0x40d70: `st.b r0,-0x35b6[gp]` / `jr 0x40e68`) -- r6==0 is not among the 7 known real call
  contexts (params 1/2/3/4 only, per `reference_accord_engage_sm_caller_enumeration_v34`); likely dead/defensive.
- `param=1` (ENGAGING) full-pass (0x40dc0: `st.b r0,-0x35b6[gp]` / `br 0x40e68`) -- ALL 4 param-1 gates passed.
- `param=2` (ENGAGED) torque-MAX pass + angle-consensus OK (0x40dd8 stores 0, calls `FUN_000406ae`, and on
  nonzero return at 0x40de4 reloads `r12` from the just-written `gp-0x35b6` (=0) and jumps to 0x40e68).

**In every bypass case, the value being skipped past 0x40e64 is 0 (the default `mov 0x0,r12` set at function
entry, 0x40d60) -- the exact same value 0x40e64 would have stored had it executed.** These are compiler-level
redundant-store eliminations along the all-pass path, not evidence of the hook missing a real event.

## Verdict on the mission's Q3 hypothesis
**REFUTED, not confirmed.** "The hook at 0x40e64 only sees benign r12==2, never the real disengage" does not
hold -- disassembly proves the real ENGAGED-context torque-MAX fire (0x40dd6) reaches 0x40e64 with r12=2. The
reason ENGAGE_SM_CUT telemetry (V31P-V2 bit0) fired ~957x benignly and did not spike at the actual cut event is
therefore NOT a hook-placement bug. Two remaining explanations, neither closed this session: (a) cal 0xC6312=320
is a low threshold that fires constantly during any real steering input in V31P-V2 (which retains stock 320, no
V33 disable) -- so gate-A firing is background noise uncorrelated with the specific cut, or (b) a CAN-330 TX-rate
issue in how the OR-latch gets sampled/cleared (see [[reference_accord_can330_tx_rate_unresolved]]).

## Related
[[reference_accord_decider_shared_epilogue_trampoline_anchors]] -- the original byte-level anchor audit this
memory's full-function trace confirms and completes (that memory established the epilogue structure; this one
proves reachability from the real fire condition).
[[reference_accord_can330_tx_rate_unresolved]] -- the remaining open item for why the telemetry didn't discriminate.
