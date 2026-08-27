---
name: reference_accord_gp6807_gates_gp69b0_engagement_ramp
description: STEER_STATUS (gp-0x6807) is not purely a CAN/UDS report — a state dispatcher tail-appended to FUN_0002a30e (Ghidra mis-bounds it) gates whether gp-0x69b0 (the engagement ramp) can advance; also a concrete reproduction of the search_instructions function-unbound-code blind spot
metadata:
  type: reference
---

**Task**: `blanked` subagent, 2026-08-27. Corrects/extends the 2026-07-14 record
(`docs/handoffs/2026-07/HANDOFF-2026-07-14-v36-debounce-sm-root-cause.md` §2c-2): "`STEER_STATUS=4` is a
lagging REPORT; the actual motor-zeroing instruction is STILL UNLOCATED." That record checked only the two
known FSM functions' own writes and two CAN/UDS packers. There is a third, real consumer it missed.

**EVIDENCE.** `search_instructions` on operand `"6807"` returns 32 matches, all attributed to
`FUN_00028ea6`, `FUN_0002a30e`, `FUN_0004e82e` (a UDS-style diagnostic snapshot packer — decompiled,
confirmed pure report: `*(buf+9) = gp-0x6807` alongside setpoint/torque/angle-rate fields, size-0x38
zero-padded buffer, classic RDBI-response shape) and `FUN_00055c42` (the CAN-399 packer, also pure report,
matches the kit's existing `399 STEER_STATUS=(d4>>4)&0xF` decode). A raw Python LE scan for the gp-relative
encoding of `-0x6807` (hw2 = `f9 97`) finds **40** hits, not 32 — **8 extra, all real**, at
`0x2a55c/0x2a598/0x2a602/0x2a688/0x2a6de/0x2a770/0x2a7ce/0x2a7fc` (these are hw2 offsets; instruction starts
2 bytes earlier).

**Why `search_instructions` missed them — a concrete, reproduced instance of the "silently undercounts"
trap, different flavor than the usual unanalyzed-region case**: `FUN_0002a30e`'s Ghidra-declared body is
`[0x2a30e, 0x2a507)` — it ends right after a `dispose 0x0,{r20,r22,r24,r26,r28,lp},lp` epilogue at `0x2a504`.
But that `dispose` is only ONE exit path; code continues immediately at `0x2a508` with a **state-machine
dispatcher** keyed on `gp-0x3d38` (`ld.bu -0x3d38,gp,r6` then a `cmp`/`bnc`/`be` chain into ~9 case bodies),
reached by direct fall-through/branch from the preceding code, fully disassemblable
(`disassemble_bytes dry_run` decodes it cleanly as ordinary V850 with no anomalies), but
**`get_function_by_address` returns "No function found" for the whole region through at least `0x2a8a6`.**
Ghidra's auto-boundary detector treated the mid-function `dispose` as the function end. `search_instructions`
evidently iterates function-bound instructions, so this whole tail — live, reachable, real code — is
invisible to it. `get_xrefs_to` on `0x2a55c`/`0x2a598` individually also returns "No references found" (true
in the narrow sense — they're fall-through targets, not branch/call targets — but not evidence of
dead code; the dispatcher entry `0x2a518 be 0x2a546` IS a real intra-region branch that reaches this code).

**What the dispatcher does with `gp-0x6807` — traced byte-exact for one state/case pair:**
```
; state gp-0x3d38==1, sub-case gp-0x6803==0 (gated behind gp-0x6805==1 upstream, at 0x2a546/0x2a552)
0x2a55a  ld.bu -0x6807,gp,r14      ; r14 = STEER_STATUS
0x2a55e  cmp r0,r14  ; be 0x2a56e  ; ==0 -> proceed
0x2a562  cmp 0x1,r14 ; be 0x2a56e  ; ==1 -> proceed
0x2a566  cmp 0x2,r14 ; be 0x2a56e  ; ==2 -> proceed
0x2a56a  jr 0x2a890                ; else (3,4,5,6,7 -- INCLUDES the debounce SM's "4") -> plain return, SKIP
0x2a56e  ld.hu -0x69b0,gp,r11      ; r11 = gp-0x69b0
0x2a572  ld.hu 0x73f8,tp,r14       ; r14 = cal 0xC63F8 = 33 (byte-confirmed, stock)
0x2a578  st.b  0x1,-0x679f,gp
0x2a57e  st.b  0x3,-0x3d38,gp      ; state -> 3 (self-transitioning FSM)
0x2a582  st.b  0x1,-0x6806,gp      ; sibling status byte, one below STEER_STATUS
0x2a586  add   r14,r11
0x2a588  st.h  r11,-0x69b0,gp      ; gp-0x69b0 += cal[0xC63F8]  <- THE GATED EFFECT
```
A second sub-case (`gp-0x6803==2`, at `0x2a598`-`0x2a5ac`) is structurally identical, step cal `0xC63FC`=328
(byte-confirmed) instead of `0xC63F8`. **STEER_STATUS outside {0,1,2} blocks a `gp-0x69b0` increment and a
state advance — a real gating effect on a signal, not a report.** Six more sibling sites at the dispatcher's
other states (`0x2a602/0x2a688/0x2a6de/0x2a770/0x2a7ce/0x2a7fc`) were pattern-matched (same `a4 77`/`f9 97`
byte signature at regular spacing) but **not individually re-disassembled** this session — treat as
pattern-confirmed, not exhaustively verified. A ninth case (state 9, `0x2a87a`→`0x2a882`) unconditionally
**zeroes** `gp-0x69b0` and resets state to 1 — a distinct abort path, not reached via the STEER_STATUS gate.

**BELIEF, not re-verified this session** — inherited from the kit's own 2026-08-26/27 memory
(`accord-mode-column-ramp-gp69b0-disengage-delay` / the `ratchet`-task 08-27 correction referenced in the
shared `memory/MEMORY.md` index): `gp-0x69b0` elsewhere is characterized as a 1kHz engagement ramp acting as
**a Q15 multiplier gating the whole LKAS block**. If correct, this partially closes the 2026-07-14 kit's
open question ("actual motor-zeroing instruction still unlocated") — not a hard zero, but **a stalled ramp**,
a better mechanistic fit for a "gentle" (not hard) EME, consistent with V37 (blanks the STEER_STATUS=4
trigger specifically) fixing it on-car. I have NOT personally traced `gp-0x69b0` forward to motor/PWM this
session.

**Also confirmed this session, byte-stock through V110**: `0xC61BE` (LKAS request clip, unrelated cell,
[[reference_accord_v36_gentle_eme_debounce_full_mechanism]]) = 15360 in stock + V107/V108/V109/V110.

**Open, ranked:**
1. `param_1`'s producer (the debounce SM's rate signal) — 0 static callers into `FUN_0002a30e`, likely a
   computed/indirect call off `w_steer_control_task`/`0x2214a`. Needs a `movhi`/`movea`-pair hunt (Ghidra
   won't xref those) near probable call sites.
2. The 6 unverified dispatcher-state siblings — low priority, pattern strongly suggests they're identical.
3. `gp-0x69b0` → actual assist/motor scaling, end to end — currently BELIEF via cross-reference to other
   memory, not a fresh trace.
4. `gp-0x6805`/`gp-0x6803`/`gp-0x3d38`/`gp-0x679f`/`gp-0x6806` identities — read as raw bytes this session,
   not independently named. `gp-0x3d38` is suspiciously close to the gating-map's `gp-0x3D28` ("ENABLE
   producer FSM 8-state handshake") — could be a sibling field of the same handshake struct or unrelated;
   NOT confirmed either way.
