---
name: reference-accord-gp35b5-reader-found
description: CORRECTS reference_accord_v34_state4_suppression_downstream.md item 4 — gp-0x35B5 (the engage-SM decider's committed substate byte) is NOT write-only. Its sole accessor FUN_00040d02 has 4 real JARL callers at 0x513ac/0x513c2/0x514b2/0x514c8, confirmed by radare2's own disassembler (not just byte-pattern matching). The value flows directly into an output struct (sst.b/st.b through a pointer at [r22+8]), reached itself via an indirect/table call (single occurrence of address 0x512fc found as raw 4-byte data at 0xB7AB4, i.e. a function-pointer-table slot). This reopens the causal chain from FUN_00040d58's return code (0/2/4/5/6/7) through gp-0x35B5 to a plausible status/diagnostic-report structure.
metadata:
  type: reference
---

# gp-0x35B5 HAS a reader — correction to `reference_accord_v34_state4_suppression_downstream.md` item 4

Session 2026-07-03, same investigation (V34 patch verification: `0x40de2`/`0x40e12` NOPs). While
cross-checking that memory's claims before relying on them (per project convention: "trust but verify"
another agent's memory before acting on it), I re-ran an independent whole-image JARL-target scan for
callers of `FUN_00040d02` (0x40d02 — `ld.bu -13749[gp],r10 / jmp[lp]`, the sole documented reader of
gp-0x35B5) using a freshly-derived-and-validated JARL22 byte encoding (see
`reference_accord_engage_sm_caller_enumeration_v34.md` for the corrected formula). **Result: 4 hits, not
zero:**

| call site | context |
|---|---|
| 0x513ac | inside a struct-builder at 0x512fc–0x5142x |
| 0x513c2 | same builder, 2nd call |
| 0x514b2 | a near-identical sibling block ~0x100 bytes later |
| 0x514c8 | same sibling block, 2nd call |

**Verified NOT a false positive of my byte-scan formula** — confirmed via r2's own `v850.gnu` linear
disassembly at all 4 sites, e.g.:
```
0x513a6  36f70900   sst.b r14, 2[ep]
0x513ac  beff56f9   jarl 0x00040d02, lp      ; r10 = gp-0x35B5
0x513b0  e051       cmp r0, r10
0x513b2  e205       be 0x513be
0x513b4  36f70900   ld.w 8[r22], ep
0x513b8  20468000   movea 128, r0, r8
0x513bc  8043       sst.b r8, 0[ep]           ; if gp-0x35B5 != 0: struct[0] = 128 (overrides earlier value)
0x513be  36c70900   ld.w 8[r22], r24
0x513c2  beff40f9   jarl 0x00040d02, lp       ; r10 = gp-0x35B5 (re-read)
0x513c6  0132       mov 1, r6
0x513c8  58570100   st.b r10, 1[r24]           ; struct[1] = raw gp-0x35B5 value (0/2/4/5/6/7)
```
`r22` is the incoming param (`prepare {r22,r24,r26,lp},0 / mov r6,r22` at the enclosing function's prologue,
0x512fc), and `[r22+8]` is dereferenced (`ld.w 8[r22],ep`) as a pointer to the OUTPUT struct — this is a
classic "build a status/report record" pattern: struct[0] gets a code from {127,255,0,16,17,18,19,34,128}
depending on the outer engage-SM-state switch (checked against 1,3,5,6,8 — the SAME state values
`FUN_00040d38` commits) PLUS is overridden to 128 specifically when gp-0x35B5 != 0; struct[1] gets the raw
gp-0x35B5 byte; struct[2] gets a small tag (0/1/2/34 range).

**The enclosing function (prologue at 0x512fc) itself has ZERO JARL callers** (whole-image scan, confirmed) —
but its address `0x000512FC` appears as **raw 4-byte little-endian DATA at file offset `0xB7AB4`**, i.e. a
single function-pointer-table slot. This is consistent with an INDIRECT/table-dispatched handler (e.g. a
UDS DID-read callback, similar in shape to the diagnostic dispatch tables documented elsewhere in this
project's memory, e.g. `reference_accord_dtc_construction_mechanism.md`'s "Diagnostic dispatch table at
tp-0x3aa0"). **Not yet identified which DID/service this table slot corresponds to** — that's the concrete
next hop to pin whether this is a live-CAN-broadcast path (e.g. the actual STEER_STATUS signal openpilot
reads) or a diagnostic-tool-only report (only observable when a scan tool actively polls this DID/service) —
these have very different implications for whether gp-0x35B5 plausibly explains the "no_torque_alert_2"
gentle-EME symptom during normal driving.

## Why this matters
`reference_accord_v34_state4_suppression_downstream.md` (§4, "Bottom line" §4) concluded gp-0x35B5 "has no
confirmed static consumer... either it's a dead vestige, or read via an indirect mechanism outside a static
byte scan's reach" and used this to hedge the overall V34 safety verdict. **The indirect-mechanism branch of
that hedge is now confirmed true, not speculative** — there IS a real consumer, reached via exactly the kind
of indirect dispatch the memory flagged as a possible gap. This does not overturn the OTHER strong findings
in that memory (0x40e1a's exclusivity to the 2 NOP'd branches; FUN_000406ae's clean no-fault internals;
FUN_00040d38's untouched lockstep check) — those remain solid. It specifically **reopens** the question of
whether suppressing return-code-4 changes an OBSERVABLE signal (via this struct-write path), which is exactly
the effect V34 is meant to have. **Net effect: this correction makes V34's rationale MORE plausible (there is
now a concrete candidate mechanism connecting the decider's return value to an output signal), not less** —
but the specific struct/DID identity, and whether it's the live-driving STEER_STATUS channel vs a
diagnostic-only report, is unresolved and is the right next step.

## Suspected root cause of the sibling's false "zero callers" result
Not confirmed, but plausible: this session independently found and had to correct a JARL22 bit-encoding
error in an earlier pass's Method box (`hi6 = byte1 & 0x3F` was wrong; correct is `byte0 & 0x3F` — see
`reference_accord_engage_sm_caller_enumeration_v34.md`). A similar off-by-one-byte encoding slip in the prior
session's scanner would silently produce false negatives on some/all real call sites without erroring. Not
verified against their actual script (not available to this session), so this is a hypothesis, not a finding.

## Related
[[reference-accord-v34-state4-suppression-downstream]] — the memory this corrects (item 4 specifically).
[[reference-accord-engage-sm-caller-enumeration-v34]] — this session's corrected JARL formula + full
FUN_00040d58 caller/body re-verification.
