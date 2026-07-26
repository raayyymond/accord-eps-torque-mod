---
name: reference-accord-gp6cc4-tracking-pipeline
description: Accord TVA-A160 gp-0x6CC4 is a 3-writer angle/position TRACKING ACCUMULATOR (not a single-instant difference), built from mod-2048/4096 wrap-corrected deltas + a 4-channel consensus mechanism sharing the SAME history arrays as FUN_000406ae. Corrects and supersedes prior single-writer characterization in reference_accord_engage_sm_second_gate_gp6cc4.md. Cal 0xC6354 has 14 readers across 5 structural roles, NOT the narrow 2-3-reader lever 0xC6312 was.
metadata:
  type: reference
---

# gp-0x6CC4 tracking pipeline + cal 0xC6354 full enumeration (2020 Accord TVA-A160)

Byte-level walk via radare2 `v850.gnu`, `code.bin`, gp=0xFEDF8000, tp=0xBF000. 2026-07-03. This
CORRECTS two claims in `reference_accord_engage_sm_second_gate_gp6cc4.md` (written by a sibling agent
earlier the same session) and materially expands the picture. Method note: r2's linear `pd` desyncs in
parts of this function cluster (V850E2 decode gaps per project doc); all disp/opcode claims below were
cross-checked with a **from-scratch derived byte-level encoder** (see Method box) that is immune to
linear-desync, not just r2's sequential disassembly.

## Method — brute-force encoding derivation [V]
Derived empirically from >10 known-good r2-decoded instructions each:
- **JARL disp22,reg2** (4 bytes): `disp = ((byte1 & 0x3F) << 16) | (byte2 | byte3<<8)`, sign-extend bit21.
  Validated on 3 independent (src,target,bytes) triples, exact match.
- **LD.W/ST.W [gp]** (4 bytes): byte0=0x24(load)/0x64(store) with reg1=gp folded in low 5 bits (0x04);
  byte1 = `(reg2<<3)|7`; bytes[2:4] LE = `(disp+1) & 0xFFFF` (a consistent +1 encoding offset found
  empirically across 6 examples — not yet root-caused but 100% consistent, treated as a fixed field
  formula). Validated on 6 independent examples.
- **LD.HU [tp=r5]** (4 bytes): byte0=0xE5 (opcode-top 0b111, reg1=r5=5); byte1=`(reg2<<3)|7`; same
  disp+1 encoding. Validated on 7 examples. **LD.HU [gp=r4]** would be byte0=0xE4 (checked, 0 hits for
  the offsets tested — no half-word reads of gp-0x6CC4 exist).
This lets full-image reader/writer/caller enumeration be done as an O(n) byte scan, independent of r2's
sequential-decode desync in this function cluster — used to re-verify and EXCEED the prior single-r2-pass
enumeration.

## CORRECTION 1: gp-0x6CC4 has THREE writers, not one [V — full-image scan]
Full-image scan for `st.w rX, -27844[gp]` (disp=-0x6CC4): **3 hits**, not 1:
| addr | reg2 | shadow write (same site) |
|---|---|---|
| 0x3bcee | r7 | 0x3bcf2 → gp-0x4D0C |
| 0x3bf46 | r28 | 0x3bf4a → gp-0x4D0C |
| 0x3d24a | r14 | 0x3d24e → gp-0x4D0C |

All three are lockstep-shadowed to **gp-0x4D0C** (disp -19724), each with a `cmp`-then-`bne`→
`movea gp-0x4D0C,r6; jarl FUN_0006b9fa` fault path on mismatch of the PRE-update shadow vs main value
(pattern identical at all 3 sites). `ld.w[gp]` reads of gp-0x6CC4: **41 sites** (0x3bce4–0x40e00, matches
FUN_000406ae's decider-adjacent reads at 0x406d0/0x40708/0x40740/0x40778/0x40804/0x4086a/0x40e00). Total
41+3 = **44**, matching the sibling's aggregate "44 total references" figure — but the sibling's
attribution ("sole writer... with lockstep shadow gp-0x4cf4") was wrong on both counts: 3 writers not 1,
and the shadow is **gp-0x4D0C** (disp -19724 = -0x4D0C), not gp-0x4CF4 (a likely hex transcription slip,
off by 0x18). All 3 writer sites' shadow target = -19724 exactly, re-verified numerically.

## CORRECTION 2: the mod-2048/4096 wrap idiom feeds a DIFFERENT variable, not gp-0x6CC4 directly [V]
At writer #1 (0x3bcb2–0x3cf6, call it `FUN_0003bcb2`): the `sar 11/shl 11/sub` mod-2048 correction
(0x3bcc6–0x3bcce) operates on `gp[-0x4EC6] + param1(r6) − param2(r7)` and stores the WRAPPED result to
**gp+0x6468** (disp +25704, a POSITIVE gp-relative offset — a different physical location entirely, since
gp is a mid-point pivot and +25704/-27844 are ~53KB apart). The quotient (revolution/sector count) feeds
`FUN_0003bc48` (a quadrant/sector classifier, thresholds −512/−1024/−1536 on `gp[-0x4EC6]`). **gp-0x6CC4
itself = `param2(r26) − param1(r24)`** — the RAW, UNWRAPPED difference of FUN_0003bcb2's two call-args —
computed AFTER the FUN_0003bc48 side-call returns, at 0x3ce2–0x3cee. So: gp-0x6CC4 is not itself the
wrapped delta; the wrap-idiom is a sibling computation in the same function feeding a separate location.

## gp-0x6CC4 IS an INTEGRATING ACCUMULATOR, not a single-instant difference [V — 7 call sites decoded]
`FUN_0003bcb2` has exactly **7 callers** (0x3c666, 0x3c8b2, 0x3ca14, 0x3ce3a, 0x3cf0e, 0x3d404, 0x3dfbc —
found via the JARL brute-force encoder, cross-checked with r2 disasm at each site, all confirmed
`jarl 0x0003bcb2, lp`). At **5 of 7** sites, param2(r7) = **the CURRENT/OLD value of gp-0x6CC4 itself**
(freshly `ld.w -27844[gp]` right before the call), and param1(r6) = **gp-0x35FC** (disp -13820) in 4 of
those. So the dominant update is:
```
gp-0x6CC4_new = gp-0x6CC4_old − gp-0x35FC
```
i.e. gp-0x6CC4 is a running accumulator DECREMENTED each update by a term gp-0x35FC. One site (0x3cf0e)
is an explicit **RESET to 0** (`mov 0,r6; mov 0,r7` then call) — gated by a status compare
(`ld.hu -26884[gp]` vs threshold, plus a service call `FUN_00018ce8(13)` result check), i.e. event/state-
transition-driven, NOT a per-cycle reset — consistent with reset happening at mode-change/re-init rather
than continuously during steady driving (inference, not proven with a live trace).
Writers #2 (0x3bf46, `gp-0x6CC4_new = old + wrapped_delta(mod 4096, ±2048)`) and #3 (0x3d24a, combines a
quantized lookup-table bucket value (via the SAME FUN_0003bc48-style −512/−1024/−1536 classifier reading
`gp-0x4E84`/`gp-0x4E82` lookup halfwords) with the wrapped delta stored to gp+0x6468 by writer #1) are
further accumulation/refinement stages of the SAME state. **Net characterization: gp-0x6CC4 is the output
of a multi-stage angle/position TRACKING FILTER, built from mod-2048/4096 wrap-corrected deltas and
consensus-gated increments — structurally an angle-domain observer state, not a torque value and not a
single instantaneous difference.**

## gp-0x35FC (the dominant decrement term) = a 4-way consensus average [V]
Exactly **1 writer**, `0x3f574` (`st.w r14, -13820[gp]`), found via exhaustive `st.w[gp]`-disp scan (100%
scan, no other hits). Its value r14 is computed (multiple branch paths converging at 0x3f574) from a
**4-channel consensus/average routine at ~0x3f34e–0x3f410** that reads the SAME 4 history arrays
documented for FUN_000406ae — `gp-0x635C` (-25436), `gp-0x6374` (-25460), `gp-0x6368` (-25448), `gp-0x6380`
(-25472) — with the SAME per-channel counter bytes (`gp-0x671D`/`-0x671F`/`-0x671E`/`-0x6718`, i.e.
-26405/-26407/-26406/-26408), the SAME ABS-diff-vs-cal-0xC6354 gate via `FUN_00049a5a`, and the SAME
bitmask accumulation (8/4/2/1 into r26) — structurally IDENTICAL to FUN_000406ae's internals. **This ties
the two independently-documented "4-way consensus" mechanisms together: they consume the same 4 arrays.**
This directly answers mission item 2's temporal-vs-spatial question in favor of **spatial-history-buffer
of a raw sample stream, scanned i=0..count-1** — but does NOT itself prove the 4 arrays hold "past
gp-0x6CC4 samples"; it's equally consistent with 4 independent redundant channel histories (torque-sensor-
style coil tracks) that FEED the observer. Not resolved further this session — see Open Questions.

## FUN_000406ae return semantics — RE-VERIFIED, confirms (not corrects) sibling's memory [V]
Full tail at 0x407c0–0x40880 hand-decoded. Early-bypass at 0x4080e (`cmp r0,r12; bne→0x4087e`) skips
straight to `mov r21,r10; dispose` when: any of the 4 channels' most-recent-agreeing slot still holds
sentinel 0x7FFFFFFF, OR a counter byte ==0xFF, OR gp-0x6CC4 itself reads the sentinel — in this bypass,
**r21 stays at its init value 0** (never touched) → **return 0**. Non-bypass path: if mask r26==15 (all 4
agree) computes a fresh 4-way average into `gp-0x35AC` (disp -13740, confirmed = 0x35AC exactly, matching
sibling's claim); else reuses the stale gp-0x35AC. Final check (0x4086a–0x4087a):
`r10=ABS(gp-0x6CC4 − gp-0x35AC)` via FUN_00049a5a; `cmp r10,r8(cal 0xC6354)` — **V850 cmp(A,B) computes
B−A**, so `cmov h,1,r21,r21` sets r21=1 when `cal − r10 > 0` i.e. **deviation < cal (4825) → r21=1**
(CONFIRMS sibling's polarity: return 1 = "confirmed consistent", return 0 = "not confirmed", either from
insufficient history OR deviation ≥4825). Decider: `cmp r0,r10; be→r12=4(leave)`. **So YES: gp-0x6CC4
deviating from the 4-way reference average by ≥4825 forces the ENGAGED-state leave, exactly as hypothesized
— re-derived independently and confirmed, sign-check included (I initially mis-derived the cmp polarity on
first pass and self-corrected against the known-good 0xC6312 gate as a calibration reference).**

## CORRECTION 3 (major): cal 0xC6354 is NOT a narrow 2-3-reader lever — 14 readers, 5 structural roles [V]
Full-image `ld.hu[tp+0x7354]` scan: **14 readers**, zero `st.h`/writer hits, zero absolute
(movhi/movea) pointer builds found, **zero float twin** (searched IEEE754 single AND double for 4825.0,
0 hits anywhere in the 1MB image). So it is not literally *lockstep-monitored* (no fault-check comparing
it to a redundant copy) and remains cal-only (only calibration bytes would change). **But it is reused in
at least 5 structurally distinct roles**, not just the 2 previously documented:
1. Decider HOLDING-state direct gate `|gp-0x6CC4| > 4825` — 0x40e0c (previously known).
2. FUN_000406ae per-channel scan threshold + final reference-deviation check — 0x406ba, 0x40874
   (previously known, 0x40874 newly pinned as the SAME function's tail, not a separate function).
3. **NEW: a ±window/range gate on `(some_target − gp-0x6CC4)` or on `gp-0x35FC` itself**, gating entry
   into further LERP/scale computation, at 0x3c820/0x3c82e, 0x3c8da/0x3c8e4, 0x3d3a0 — these sit
   immediately upstream of / adjacent to several of FUN_0003bcb2's 7 call sites, i.e. **this cal also
   gates the very update pipeline that WRITES gp-0x6CC4**, not just downstream disengage checks.
4. **NEW: a raw numeric SCALE FACTOR** inside a gain/index formula
   (`sar3;mul;sar8;mulu;addi 8192;shr14`, combined with 2 other cals 28986=tp+0x713A and
   29746=tp+0x7432) at 0x3e07a, 0x3d3a8-ish, 0x3d6f0 — three separate sites. This is a pure numeric role,
   not a comparison at all; raising 0xC6354 would rescale whatever index/gain this formula produces.
5. **NEW: a state-variable COPY/SELECTOR** — cal 0xC6354 (and neighbor cal 0xC735C=tp+0x735C) get copied
   into a working slot `gp-0x69CE` (disp -27086) based on a dispatch-mode switch, at 0x3d0f2/0x3d122/
   0x3d138.
**Verdict (revises the mission's framing): raising 0xC6354 is cal-only in the narrow "only calibration
bytes change, no lockstep fault-monitor" sense — but it is NOT a clean, single-purpose lever like 0xC6312
was. It simultaneously relaxes the intended disengage gates (roles 1,2) AND changes the internal
window-gating of the gp-0x6CC4/gp-0x35FC update pipeline itself (role 3) AND rescales an unrelated
gain/index formula (role 4) AND changes a mode-selected working threshold used elsewhere (role 5). The
full downstream effect of roles 3-5 was NOT traced this session — treat as a materially higher-risk edit
than 0xC6312 pending that follow-up.**

## Dispatcher-state correction [V]
The mission text speculated the dispatcher state lives at `gp-0x679c`. Traced one hop from the decider's
ENGAGED-param caller (0x410a0–0x410d6, inside the region bracketing `FUN_00041222`): on decider return
r10≠0 (state 2 or 4, both non-stay), the caller calls `FUN_00040e74` (commits substate byte gp-0x35B5)
then falls to a shared tail that conditionally calls **`FUN_00040d38(3)`** — confirmed body:
`FUN_00040d38` writes its param to **`gp-0x67DC`** (disp -26524) with lockstep shadow **`gp-0x4CCB`**
(disp -19509), fault-checked via FUN_0006b9fa on mismatch — same pattern class as gp-0x6CC4/gp-0x4D0C.
**gp-0x67DC, not gp-0x679c, is the byte-verified dispatcher-state slot.** One further hop: when a status
byte `gp-0x67FE` (disp -26622) == 2, the caller also invokes `FUN_00040d38(3)` and clears substate flag
gp-0x35B5 via `FUN_00040e6e`. A stay-branch (r10==0) instead calls `FUN_000405fe` (a read-and-clear
accessor stub reading `gp-0x35B2`, disp -13746) and conditionally calls `FUN_0003d04c(r6=4,r7=0)` when
that flag ==1. **FUN_0003d04c was not decompiled this session — it is the most promising next hop toward
STEER_STATUS/deliver-flag (gp-0x6809 etc.), which the sibling's memory already flagged as unresolved via
185k-instruction search (no direct gp-relative store found — likely a pointer/struct write).**

## Bottom line for the bump-sensitivity question
**Belief, well-evidenced but not conclusively proven:** gp-0x6CC4 is an angle/position-domain TRACKING
ACCUMULATOR (mod-2048/4096 wrap idioms across all 3 writers are the standard signature of angle math, not
torque math), continuously updated by consensus-gated deltas from the same redundant-channel history
arrays used elsewhere in the coil-track sensor architecture. A structure like this is BY DESIGN sensitive
to a genuine abrupt physical event: a real mechanical jolt would show up as a large one-cycle delta at the
writer sites (writer #1's raw diff, writer #2's wrapped increment) and would very plausibly push the
ABS-deviation-from-4-way-average past the 4825 threshold for one or more cycles — exactly the bump-EME
symptom. **Not yet proven: the physical/raw sensor origin of `gp[-0x4EC6]` and the 4 history-array
sources** — that would require tracing the ARRAY WRITERS (not found this session; the 0x3f34e routine
only READS them) and `gp[-0x4EC6]`'s own producer. A live-RAM capture of gp-0x6CC4 (0xFEDF133C) during a
bump event remains the strongest direct confirmation, as sibling's memory already proposed.

## Related
[[reference-accord-engage-sm-second-gate-gp6cc4]] — sibling's original finding; CORRECTED here on writer
count (3 not 1), shadow address (gp-0x4D0C not gp-0x4CF4), and the 0xC6354 reader count/roles (14/5 not
"3 readers, no other uses").
[[reference-accord-lkas-engage-sm-disengage-trigger]] — the FIRST gate (gp-0x6a62/0xC6312), V33's target,
confirmed narrow/clean by contrast with 0xC6354's much broader reuse found here.
[[reference-accord-lkas-path-wiring]] — FOC PI controller region (FUN_0003b8f6) immediately upstream of
this whole cluster (0x3b8f6–0x40e78).

## Open questions / next verification
1. Who writes the 4 history arrays (gp-0x635C/-0x6374/-0x6368/-0x6380)? Not found this session — the
   0x3f34e routine and FUN_000406ae only READ them. Need a `st.w[ep]` scan with computed base
   gp-25436/-25460/-25448/-25472 (indexed writes, same `mov rN,ep;shl2,ep;add gp,ep` idiom as the readers)
   to find the producer(s) — would settle "4 redundant channels vs ring-buffer of gp-0x6CC4 history."
2. What does `gp[-0x4EC6]` (writer #1's raw input) physically represent? Trace its own writer(s).
3. `FUN_0003d04c(4,0)` — the most promising next hop toward the LKAS deliver-flag / STEER_STATUS byte
   closing the loop to the "no_torque_alert_2" symptom. Not decompiled this session.
4. Live-RAM read of gp-0x6CC4 (0xFEDF133C) during an actual hard-turn+bump event remains the strongest
   direct confirmation of bump-sensitivity, per sibling's original proposal.
