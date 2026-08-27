---
name: reference-accord-state4-ratchet-and-gp67fa-state-graph
description: Full gp-0x67fa top-level state machine graph (writers, dispatch map) + byte-verified governor magnitude-ratchet substitution in FUN_0004503c that only fires in state 4 — state 4 IS reachable mid-drive (5->4, 10->4), not boot-only.
metadata:
  type: reference
---

# Accord 39990-TVA-A160 — gp-0x67fa top-level SM + state-4 governor ratchet (session 2026-07-19/20)

Stock `code.bin`. gp=0xFEDF8000, tp=0xBF000. GhidraMCP (`search_instructions`, `decompile_function`,
`disassemble_function`). All addresses/bytes below instruction-verified this session unless marked [I].

## Background this corrects/extends

A prior session's "16-phase duty cycle" reading of `gp-0x67fa` was already retracted before this session
(it's a top-level init/operating/fault SM byte, lockstep-shadowed at `gp-0x4c39` via the standard
`if(cur==shadow){write both}else{FUN_0006b9fa(shadow)}` pattern seen everywhere else in this codebase).
This memory answers the follow-up: **can the SM return to state 4 after normal running, and does that
matter for torque delivery?** Answer: **yes to both.**

## Complete writer inventory (image-wide, `st.b -0x67fa[gp]` search, 33 sites)

ALL writers are inside 10 dispatch handler functions clustered in `0x197ea-0x1a0c0`, plus ONE outlier:
`FUN_00057e5e`@`0x57e94` — unconditionally forces state=1, part of a hardware-init/reset routine
(`DAT_ff83a000=0x80`, various `FUN_000194xx/0005acxx/0001b16c/000178c6` inits) — this is the power-on
reset entry, not a mid-drive path.

## Dispatch map (from `FUN_00019f7c`, the top-level dispatcher, byte-verified)

1→`FUN_000197ea`, 2→(no handler), 3→`FUN_00019888`, 4→`FUN_00019970`, 5→`FUN_00019b10`,
6→`FUN_00019bd0`, 7→`FUN_00019cd4`, 8→`FUN_00019cfa`, 9→`FUN_00019f00`, 10→`FUN_00019d90`,
11→`FUN_00019e7c`.

Dispatcher's OWN top-of-function block (before dispatch) does the hard-fault entry into state 8:
gated by `gp-0x3ee8==0` (fires once per power cycle only — matches existing M1 hard-shutdown notes),
condition includes `gp-0x685c!=0` as one OR'd term (ties to the existing corridor-lockstep/M1 chain).

## Full state graph (all 10 handlers decompiled)

`1→3` (self-test-gated) ; `3→{4 or 6}` ; `4→{11, 10, 6, or 5(if gp-0x68ad==1)}` ;
`5→{11(status bit16 ready), or 4(if gp-0x68ad==0)}` ; `10→{6, or 4}` ; `11→6` (fault only) ;
`6→{7,9}` ; `9→7` ; `7→` **no write at all**, dead-end sink (`FUN_00060c9a(1)` only).

`{6,7,9}` is a one-way degraded/fault branch — no traced path back into `{4,5,10,11}` in normal mode.
`{4,5,10,11}` is the live cluster (matches the existing `0xd30` torque-task mask). **11 is the best
candidate for "settled/steady" state** (only member of the cluster with no handler path back to 4) but
this is [I] — not directly observed, since 5→4 and 10→4 exist and are gated on cheap-to-flip runtime
flags, so oscillation within the cluster instead of parking at 11 cannot be ruled out from statics alone.

## Every literal-4 writer (5 sites total)

| addr | function | mode | condition |
|---|---|---|---|
| `0x198d8` | `FUN_00019888` (3→4) | diag only | `tp+0x74d0==4 && tp+0x74f9==0xAA` |
| `0x19952` | `FUN_00019888` (3→4) | **normal** | `FUN_000197d0(0xf)==0 && (gp-0x6d78&0x2a10)==0x2a10 && FUN_000220ba()==1` |
| `0x19bb0` | `FUN_00019b10` (**5→4**) | diag OR **normal** | diag: `tp+0x74d0==4`; normal: `gp-0x68ad==0` |
| `0x19de0` | `FUN_00019d90` (10→4) | diag only | `tp+0x74d0==4` |
| `0x19e54` | `FUN_00019d90` (**10→4**) | **normal** | NOT(`gp-0x4378==1 && gp-0x3eec!=0`) AND NOT(`gp-0x6d78&0x5080`) AND `FUN_000197d0(0xf)==0` |

**5→4 and 10→4 are both reachable in normal (non-diagnostic) operation, no power cycle required.**

Bonus independent corroboration that state 10 is a live torque-relevant excursion, not theoretical:
`FUN_0003d04c` (deliver-commit pre-gate, see [[reference_accord_segmentD_fun3d04c_full_gate_map]])
REJECTS the LKAS commit outright (`return 6`) whenever `gp-0x67fa==0xA`:
```
0003d074: ld.bu -0x67fa[gp],r15 ; cmp 0xa,r15 ; bne 0x3d080 ; jr 0x3d1ee  (-> reject)
```

## gp-0x68ad ("engage-ready" flag gating 4→5 and the 5→4 fallback) — torque-sensor-linked

Sole updater `FUN_0001a104`, called every cycle at the top of both state-4 and state-5 handlers.
Byte-verified disasm shows **no branch preserves gp-0x68ad==1 across cycles unchanged** — it is either:
- SET (from 0, when `gp-0x437c==1 && gp-0x6a98!=0`), or
- unconditionally CLEARED (from 1, when `gp-0x4378==1 && gp-0x6a98!=0`), or
- passed through `FUN_00022016`, which only PRESERVES it when `gp-0x679d==1` OR
  (`gp-0x6a5e!=0 AND gp-0x67f4==1`).

`gp-0x6a5e` and `gp-0x67f4` are the SAME torque-voter outputs documented in
[[reference-accord-voter-ratelimit-and-vote-logic]] / [[reference-accord-voter-0xffff-sentinel]]:
`gp-0x6a5e` = fused/averaged column-torque magnitude (`FUN_00041eec`), `gp-0x67f4` = the voter's
plausibility-converged latch (clears on total sensor loss, re-sets only when `|new-old|<65`, hysteretic).

**Practical read: staying past state 4/5 requires nonzero fused column torque AND a converged
plausibility latch (or the separate `gp-0x679d` flag).** A torque zero-crossing or a momentary
plausibility-latch drop — both plausible during a hard, large-angle turn near sensor saturation —
can flip `gp-0x68ad` to 0 and trip `5→4` on the very next dispatch cycle.

**[RESOLVED 2026-07-20]**: `gp-0x437c`/`gp-0x4378` (`_DAT_fedf3c84`/`_DAT_fedf3c88`) found via
absolute-address/immediate-materialization search (`mov 0xfedf3c80,rX` 32-bit immediate loads, NOT
gp-relative — confirms the "different base register" hypothesis). **Both are UDS/diagnostic-request
artifacts, NOT sticky ignition/run flags, and NOT the same signal as each other.** Sole writers:
`FUN_0001a4cc`/`FUN_0001a4f2`/`FUN_0001a516`, called only from `FUN_0001a24e` — a service-ID dispatch
table walker (`cVar2=*(char*)(param_1+2)`, linear-scanned against `(id_byte,fn_ptr)` pairs from
`0x8ac1c`). `FUN_0001a24e` is called from exactly one site, the `uVar5==0x41` arm of `FUN_0001b47a`'s
large UDS-service-ID switch (`0x22`/`0x34`/`0x35`/`0x37`-shaped arms visible = ReadDataByIdentifier/
RequestDownload/RequestUpload/TransferExit-style; sibling cluster `FUN_0001a33e` implements a textbook
SecurityAccess seed/key algorithm: `seed^0x395a`, `key²+0x9176`, 4-stage session counter
`_DAT_fedf3c90`). `FUN_0001b47a` itself is gated at the top by `gp-0x3ed8` ("request pending") and
`FUN_0001b212()==1` (parses/validates an inbound request frame) — the SID switch only runs on a
validated diagnostic request. **[VERIFIED down through FUN_0001b47a's own gating; FUN_0001b47a's own
caller has zero static xrefs — presumably a periodic diagnostic-RX task/function-pointer table, not
resolved. High confidence given the unambiguous SecurityAccess content, but flagging that one hop as
[INFERRED] not fully closed.]**

**Consequence — revises the ratchet-frequency picture favorably**: with no diagnostic tool attached,
both cells read their power-on default (0, no static initializer, no other writer). So in
`FUN_0001a104`: the "not engaged" SET runs through `FUN_00022034()`'s conditional OR-chain (not a
direct set), and — critically — the "already engaged" branch's **unconditional clear at `0x1a142`
essentially never fires in the field** (it requires `gp-0x4378==1`). Instead, every cycle runs through
`FUN_00022016()`'s conditional clear: `gp-0x679d!=1 && (gp-0x6a5e==0 || gp-0x67f4!=1)`.
**`gp-0x68ad` is genuinely HELD/latched across cycles once engaged — NOT a 1-cycle pulse that resets
every cycle.** It clears specifically on genuine torque-sensor transients (fused torque `gp-0x6a5e`
reading exactly 0, or plausibility latch `gp-0x67f4` not converged), not as permanent chatter. This
rules out the worst-case "bounces every cycle" reading while keeping the mechanism itself — and its
tight fit to the operator's hard-turn/high-column-torque symptom — intact.

## Q3 — calibration-only defeat: clean structural negative (checked 2026-07-20)

**Entry conditions (5→4, 10→4)**: walked the full reachability chain — `FUN_0001a104`, `FUN_00022016`,
`FUN_00022034` (5→4), `FUN_00019d90`'s normal-mode legs (10→4), and `FUN_00019888`→`FUN_000220ba`→
`FUN_00022078` (3→4 normal entry, for context). **Zero `tp+`-relative cal reads in any of these six
functions** — pure runtime-flag/state/counter logic throughout. No cal lever exists on the entry side.

**The substitution itself**: `tp+0x7134`(cal `0xC6134`, `ld.hu` unsigned, current=1000/`0x03E8`) and
`tp+0x748e`(cal `0xC648E`, `ld.h` **signed**, current=0) are read via IDENTICAL tp-displacement in BOTH
the primary/normal block (`0x454a8-0x454d8`) and the substitution block (`0x45578-0x455aa`) of
`FUN_0004503c` — same cells, not mirrors — AND in two unrelated functions (`FUN_00041464`, 16 reads of
`0x7134` alone — a high-traffic rate/velocity computation; `FUN_000456a4`, a mask-dispatched sibling of
the governor). Editing either cal changes ≥3 functions. More fundamentally: **the branch decision
itself (`0x454fc cmp 0x4,r12` and `0x45526 cmp r10,r24;bnh`) has zero cal dependency** — trigger is
purely `state==4 AND |fresh|>|held|`; these two cals only affect what gets substituted, not whether.
**No calibration edit, of any value, can defeat this mechanism** — a fix requires a code edit (e.g. the
2-byte conditional branches at `0x454fe`/`0x45528`, self-contained and narrowly scoped, unlike the
V24/V27 cave failures — a data point, not a recommendation).

## The governor magnitude ratchet — FUN_0004503c @ 0x454f8-0x45526, fully byte-verified

```
000454f8: ld.bu -0x67fa[gp],r12 ; cmp 0x4,r12 ; bne 0x455c4     ; only when state==4
00045500-0004550a: r24 = clamp(ABS(fresh gp-0x6ace))             ; FUN_00049a5a=ABS, FUN_00049a78=clamp(x,0,0xFFFF)
0004550e-00045524: r10 = clamp(ABS(gp-0x138a, the OLD persisted value))
00045526: cmp r10,r24 ; bnh 0x455c4        ; skip substitution when |fresh|<=|old| (unsigned)
                                             ; falls through (SUBSTITUTES) only when |fresh| > |old|
0004552e-000455aa: (on substitution) recomputes a rate-shaped value SEEDED FROM gp-0x138a (old value,
                    NOT a literal freeze) via the same tp+0x7134/tp+0x748e interpolation block used for
                    the normal (state!=4) path, and OVERWRITES gp-0x6ace/gp-0x4cca with it.
000455c4 (common landing, both paths) ... 000455cc: st.h r6,-0x138a[gp]   ; UNCONDITIONAL writeback
```

Confirms all 4 sub-questions: (a) compares against literal 4 — VERIFIED. (b) substituted value is a
rate-shaped recomputation seeded from the OLD value, not a literal freeze-copy — VERIFIED, more precise
than "previous value substituted". (c) comparison is unsigned ABS-clamped MAGNITUDE, not signed —
VERIFIED. (d) **writes back to gp-0x138a unconditionally — VERIFIED, making the ratchet SELF-SUSTAINING/
CUMULATIVE across consecutive state-4 cycles**, not a one-shot clamp: each state-4 cycle where
`|new|>|held|`, output is pulled toward the held value, and that suppressed output becomes next cycle's
comparison baseline.

## Other command-path functions that treat state 4 specially (beyond mask gates + governor)

- `FUN_0002cc2a`@`0x2ccb0`/`0x2d144` — LKAS-availability/dwell manager; branches explicitly on
  `state==8`/`state==5`/`state==4` inside its own counter SM (not just range-checked).
- `FUN_0002e734`@`0x2e8a6` and `FUN_00041304`@`0x4130c` — both trigger `FUN_0005db02(bVar|8)` (a
  status-bit broadcast, CAN/dash-adjacent) specifically when `state==4`.
- `FUN_00044cf0`@`0x44cfe` — **`state==4` SUPPRESSES a torque-cap/LERP-table branch**
  (`bVar1 = (mode==2) && (state!=4)`), a SECOND independent mechanism (beyond the governor
  substitution) by which state 4 changes torque shaping.
- `FUN_0002a30e`@`0x2a32c` reads `state==8` too but this function is DEAD CODE (0 callers per
  [[reference-accord-lkas-column-torque-cut-trigger]] / segmentE memory) — not load-bearing.

## Open items (next verification steps, in priority order)

1. `gp-0x437c` vs `gp-0x4378` writer identity (see above) — decides ratchet frequency.
2. `gp-0x679d` writer `FUN_000567c0` traces to `FUN_0005d9c2()` bit 3 + unpacked dwell-counter logic.
3. `FUN_000197d0(0xf)`/`(0x10)` (status word `gp-0x6d78` bits 15/16) producers not traced — only the
   generic OR-only "set bit" writer `FUN_000197b8` was found; whether these are one-way latches or can
   clear is unconfirmed.
4. `FUN_000220ba`/`FUN_00022078` (gates normal-mode 3→4) not decompiled past one level.

## Safety check on defeating the substitution (2026-07-20) — a real monitor exists, structural case it's not tripped

Before any code edit to skip the `0x454fe`/`0x45528` substitution branch, checked whether any monitor
independently re-models the state-4 hold (the exact failure class that bricked V24-V27: int-vs-float
lockstep divergence from an edit on only one side).

**`FUN_00043e44` (the established float watchdog) reads NEITHER `gp-0x67fa` NOR `gp-0x6ace`/`gp-0x138a`/
`gp-0x4cca` anywhere in its body (`0x43e44-0x44a8b`)** — confirmed by exhaustive image-wide operand
search for all four, zero hits in range. It cannot be modeling the state-4 hold; it never reads the
inputs that would let it.

**`gp-0x6ace`'s shadow `gp-0x4cca` is real but purely internal to `FUN_0004503c`** — every write site for
either cell is inside that one function, and both members of the pair are always written together (same
instruction pair, both the primary path and the substitution path). Skipping the substitution can't
create an internal shadow mismatch. **`gp-0x138a` has no shadow and no external reader at all** (6 total
accesses, all inside `FUN_0004503c`).

**Two OTHER functions do independently consume `gp-0x6ace`: `FUN_0004595a` and `FUN_00045a20`**
(dispatch order confirmed: `FUN_0004503c → FUN_0004595a → FUN_000456a4 → FUN_00045a20`, all under the
same `0xd30` state-gate as the governor).
- `FUN_00045a20` compares `gp-0x6ace` against `gp-0x6acc` — SAFE by construction, because `gp-0x6acc` is
  recomputed FRESH every cycle by `FUN_000456a4` (`0xFEDF1534`, sole writers `0x45932`/`0x45942`) as
  `bias + (gp-0x6ace_THIS_CYCLE + LERP_offset) × cal_0xC6134/1000` — mechanically downstream of whatever
  `gp-0x6ace` currently holds, substituted or not. Cannot diverge from the state-4 edit.
- **`FUN_0004595a` is the real one.** Compares `gp-0x6ace` against `gp-0x6b94` (sole writer `FUN_0003aa2c`,
  the aggregator — matches `reference/firmware/reference_accord_lkas_delivery_and_governor.md` exactly). Decoded the
  float-bitpattern trick (`(uint)x < 0xbc23d70b`, `0xbc23d70b`≈`-0.01`): net effect is **fault if
  `|gp-0x6ace|` exceeds `|gp-0x6b94|` by >~0.01, OR if the two have opposite sign** — an overshoot +
  polarity check on the governor, NOT an equality check. **No visible debounce** (unlike `FUN_00043e44`'s
  documented ~10-cycle SM) — a single bad cycle would trip it. Feeds `FUN_000462e6` → **unconditionally**
  calls `FUN_00016de6(0x1d, param_1, 1, 1)` — `0x1d` is the SAME hard-fault-eligible DTC index as the
  established M2 float watchdog.

**Structural (not measured) case that the edit doesn't trip it**: `gp-0x6b94` is read at `0x453e0`,
literally the first thing `FUN_0004503c` does, and the "fresh candidate" is built as
`s_clamp_i32(gp-0x6b94, ±governor bound)` then slew-limited against `gp-0x138a` — **the exact same
primary computation every state OTHER than 4 uses unmodified**, running unincident across every build
back to stock. The state-4 substitution only ever makes `gp-0x6ace` SMALLER (undershoot direction,
the safe side of this monitor). Removing it returns state 4 to the same already-proven path used
everywhere else. **This is a structural argument from confirmed code paths, not a live measurement or
numeric worst-case proof — flagged explicitly as [INFERRED, reasoned] not [VERIFIED] for the "won't
trip" conclusion specifically** (everything about the monitor's existence/mechanics/DTC-index IS
[VERIFIED]).

**Ordering confirmed** (was hypothesis, now disasm-checked): slew limiter at `0x4543a-0x45458` (MIN/MAX
clamp of raw candidate into `[gp-0x138a - step, gp-0x138a + step]`, step from cal `0xC6206`=512/
`0xC6208`=205) runs BEFORE the primary write (`0x4546a-0x454e4`) which runs BEFORE the state-4
substitution check (`0x454f8`+). Skipping the substitution leaves both the slew limit and the
`gp-0x6b94`-relative governor clamp fully intact — matches `reference_accord_fun43e44_report_only_and_gp6acc_slew_limiter.md`'s independently-documented slew-limiter mechanics exactly.

**`gp-0x679d` producer chain (`FUN_000567c0`, `FUN_0005d9c2`) is cal-free** — zero `tp+` reads in either.
`gp-0x67ba` (the other input) has no `gp`-relative writer anywhere in the image — same signature as the
UDS-artifact discovery above; NOT chased down with the absolute-address technique this session.

**⚠ `FUN_00016de6` (the generic DTC dispatcher `FUN_0004595a` feeds via `FUN_000462e6`) has NO visible
occurrence-counter debounce either** — checked one level deeper than the `FUN_0004595a`-has-no-debounce
finding above. With `param_3=1, param_4=1` (the call shape used here), it walks straight to
`FUN_0001611e()` (the established hard-fault-eligibility check, `record[+8]&0x41`, already nonzero for
index `0x1d`) and, if nonzero, calls `FUN_00018738` directly — the documented motor-off chain entry
point. The 4-condition gate ahead of that reads as static eligibility/session-state bitmap tests, not
an accumulating counter. **Net: if `FUN_0004595a`'s divergence condition is ever true even once, there
appears to be NO grace period before the motor-off chain starts.** This does not change the structural
"won't trip" argument above, but it means that argument is carrying full weight with zero margin for
error if it's wrong — raises the bar for what counts as "verified enough to flash" on this specific edit.

[[reference-accord-voter-ratelimit-and-vote-logic]] [[reference-accord-voter-0xffff-sentinel]]
[[reference_accord_segmentD_fun3d04c_full_gate_map]] [[reference_accord_segmentE_arbitration_shaper_dtc_gate_table]]
[[reference_accord_fun43e44_report_only_and_gp6acc_slew_limiter]] [[reference_accord_lkas_delivery_and_governor]]
