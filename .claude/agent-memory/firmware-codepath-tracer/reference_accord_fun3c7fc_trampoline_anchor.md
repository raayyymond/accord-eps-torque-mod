---
name: reference-accord-fun3c7fc-trampoline-anchor
description: Byte-exact disasm of FUN_0003c7fc (Accord TVA-A160 angle-deadband gate, cal 0xC6354=4825) with a single convergent bail-landing anchor at 0x3c93c (4-byte st.b, non-branch) recommended for a telemetry trampoline. Refines reference_accord_segmentD_fun3d04c_full_gate_map.md's flagged-but-not-byte-verified mention of this function.
metadata:
  type: reference
---

# FUN_0003c7fc — full byte-verified disasm + trampoline anchor (2020 Accord TVA-A160)

Session 2026-07-13, READ-ONLY audit via GhidraMCP (`program="master.bin"`, the stock `code.bin` image,
NOT the active `_uds_telem_plain_image.bin`). V850:LE:32, gp=0xFEDF8000, tp=0xBF000. Function bounds
`0x3c7fc`–`0x3c943` (dispose). No files/DB modified.

## Callers — exhaustive, confirmed via `search_instructions` (not `get_xrefs_to` per project convention)
Exactly 3 static call sites, ALL from `FUN_0003d04c` (the SEGMENT D deliver-commit function documented in
[[reference-accord-segmentD-fun3d04c-full-gate-map]]):
| call site | preceding cal loaded into gp-0x69ce | gp-0x6770 set to | param (r6) |
|---|---|---|---|
| 0x3d154 | tp+0x7354 = 0xC6354 = **4825** | 3 | `mov 0,r6` → **0** |
| 0x3d17a | tp+0x735c = 0xC735C = **7407** | 3 | `mov r26,r6` → whatever r26 held |
| 0x3d1a0 | tp+0x7354 = 0xC6354 = **4825** | 8 | `mov 0,r6` → **0** |
All 3 sites unconditionally clear `gp-0x6773`(-26483)=0 immediately after the call, regardless of
`FUN_0003c7fc`'s return value.

## `ref` characterization — for the documented (4,0) path, ref is a FIXED CAL CONSTANT, not a live filter
`FUN_0003c7fc(param_1)` opens with `jarl 0x0003c7ce,lp` (`0003c802`); result cached in callee-saved `r26`
for the rest of the function (hence `prepare {r26,r28,lp}`).
- `FUN_0003c7ce(param_1)`: `r28 = param_1; r28 = ((r28<<16)/cal(tp+0x7432=0xC7432=29746))<<9 /
  cal(tp+0x713a=0xC713A=28986); r28 += FUN_0003c6fc(param_1); result = r28 * sign_byte(gp-0x6752)`.
- `FUN_0003c6fc(param_1)`: a signed breakpoint-search + linear-interpolation LERP over a table at
  `tp+0x78b4..0x78d0`-ish (confirmed by disasm: cmp against `tp+0x78b6`/`0x78c2`/`0x78b8`, walk pointers,
  `(y1-y0)*(x-x0)/(x1-x0)+y0` interpolation idiom).
- **For the actual traced call (`FUN_0003d04c` case-4 body, `FUN_0003c7fc(0)`), param_1=0 zeroes the
  scaled term in `FUN_0003c7ce` entirely** (`(0<<16)/cal = 0`), so **`ref = r26 = sign_byte(gp-0x6752) *
  FUN_0003c6fc(0)`** — a LERP-table lookup AT INDEX 0, i.e. **a fixed per-boot calibration baseline**, NOT a
  dynamically filtered live angle. Same reduction applies to the third call site (also param=0). The
  second call site (param=r26, non-zero in general) DOES exercise the full scaled-reconstruction form.
  **Practical read: for the two param=0 call sites, "ref" is effectively a calibration constant — the
  deadband check reduces to `|gp-0x6CC4 − const| > 4825`, consistent with prior memory's simpler framing,
  now with the source of `ref` pinned exactly.**

## The compare pairs — BOTH arms fully decoded, byte-exact
Two structurally parallel `|delta|>4825` implementations exist, gated by `gp-0x6773`:

**Arm A (`gp-0x6773==1`, "committed" mode)** — delta = `r26(ref) - gp-0x6CC4(FULL 32-bit word)`:
```
0003c81c  ld.w   -0x6cc4[gp], r14        ; r14 = gp-0x6CC4 (word)
0003c820  ld.hu  0x7354[tp], r11         ; r11 = cal 0xC6354 = 4825 (d9 12 LE, confirmed live via read_memory)
0003c824  subr   r26, r14                ; r14 = r26 - r14 = ref - gp-0x6CC4   (delta)
0003c826  cmp    r14, r11                ; flags = r11 - r14 = 4825 - delta
0003c828  bge    0x0003c82e   [be 05]    ; TAKEN (delta<=4825) = continue/pass. NOT-TAKEN = fall to bail.
0003c82a  jr     0x0003c93a   [80 07 10 01], len 4   ; +Δ-EXCEEDED bail (pc-relative, 4 bytes, NOT anchor-eligible)
0003c82e  ld.hu  0x7354[tp], r8          ; reload cal 4825
0003c832  subr   r0, r8                  ; r8 = -4825
0003c834  cmp    r14, r8                 ; flags = r8 - r14 = -4825 - delta
0003c836  ble    0x0003c83c   [b7 05]    ; TAKEN (delta>=-4825) = continue/pass. NOT-TAKEN = fall to bail.
0003c838  jr     0x0003c93a   [80 07 02 01], len 4   ; -Δ-EXCEEDED bail (pc-relative, 4 bytes, NOT anchor-eligible)
```
**Gate FIRES (deadband exceeded) = NOT-TAKEN on either `bge`@0x3c828 or `ble`@0x3c836** → falls straight
into the immediately-following `jr 0x3c93a` (both are 4-byte unconditional jumps, PC-relative — excluded
as anchors per the mission's constraint, but they conveniently converge on the SAME target).

**Arm B (`gp-0x6773==0`, default/non-reset sub-branch)** — after a reset-check bypass (sentinel
`gp+0x6470==-0x8000`/`0x7fff` OR `gp-0x67FE==0` → skip straight to a re-init branch, NOT a deadband
compare), the actual gate at `0x3c8c6`:
```
0003c8c6  ld.w   -0x6cc4[gp], r6
0003c8ca  jarl   0x00049a5a, lp          ; r10 = ABS(gp-0x6CC4)  (generic ABS helper)
0003c8ce  ld.hu  -0x69ce[gp], r6         ; r6 = working-copy cal slot (=4825 or 7407 per caller, see table above)
0003c8d2  cmp    r10, r6                 ; flags = r6 - r10
0003c8d4  bc     0x0003c920   [e1 25]   ; TAKEN (unsigned r6<r10, i.e. |gp-0x6CC4| > working-cal) = MAGNITUDE bail
0003c8d6  ld.h   -0x6cc4[gp], r14        ; r14 = LOW 16 bits of gp-0x6CC4 (signed halfword this time)
0003c8da  ld.hu  0x7354[tp], r12         ; r12 = cal 0xC6354=4825 (hardcoded again, not the working slot)
0003c8de  subr   r26, r14                ; r14 = ref - low16(gp-0x6CC4)   (delta2)
0003c8e0  cmp    r14, r12                ; flags = 4825 - delta2
0003c8e2  blt    0x0003c920   [f6 1d]   ; TAKEN (4825-delta2 < 0, i.e. delta2>4825) = +Δ-EXCEEDED bail
0003c8e4  ld.hu  0x7354[tp], r11         ; reload cal 4825
0003c8e8  subr   r0, r11                 ; r11 = -4825
0003c8ea  cmp    r14, r11                ; flags = -4825 - delta2
0003c8ec  bgt    0x0003c920   [af 1d]   ; TAKEN (-4825-delta2 > 0, i.e. delta2 < -4825) = -Δ-EXCEEDED bail
```
`0x3c920` sets `r12=0` then falls into the shared tail `0x3c926: cmp 1,r12 / bne 0x3c93a` — since r12=0,
`bne` is always taken → lands at `0x3c93a` too. **So Arm B has THREE distinct fire conditions (magnitude
vs. working-cal, +Δ, −Δ), all routing to the SAME `0x3c93a` landing point as Arm A.**

## Confirmed: ONE convergent bail-landing point, reached ONLY on gate failure, never on success
Full-image + local-cluster check: **5 distinct fired-path entries** — `0x3c82a`(jr), `0x3c838`(jr),
`0x3c87c`(be, the unrelated `tp+0x74a7==0` feature-disable bail — cal read live = `01 01`, i.e. **stock=1,
this bail is dead in practice**), and the two Arm-B routes via `0x3c920`→`0x3c928`(bne) — **all converge at
`0x3c93a`**. The two SUCCESS paths (`0x3c874: br 0x3c940` and `0x3c938: br 0x3c940`) jump PAST `0x3c93a`
directly to `0x3c940`, **never touching the bail landing zone**. This is a clean, exhaustively-verified
single telemetry point for "this cycle's deadband/commit check failed," independent of which of the 3
callers/2 arms/3 fire-conditions triggered it.

## Fired-path → cut propagation
```
0003c93a  mov   0x4, r28        [04 e2], len 2      ; r28 = 4 (bail return code)
0003c93c  st.b  r0, -0x6770[gp] [44 07 90 98], len 4 ; gp-0x6770 ("mode" byte) := 0 — THE CUT.
                                                       ; overwrites whatever the caller had just set it to
                                                       ; (3 or 8, per the call-site table above)
0003c940  mov   r28, r10        [1c 50], len 2       ; r10 = 4 (return value)
0003c942  dispose 0x0,{r26,r28,lp},[lp]               ; pop r26/r28/lp from stack (prepare's saved copies),
                                                       ; return
```
Per [[reference-accord-segmentD-fun3d04c-full-gate-map]], `FUN_0003d04c`'s own return is whatever
`FUN_0003c7fc` returns for the case-4 path, and its own caller (`FUN_00041222`) discards that return value
— so the ONLY externally-visible effect of a fired gate is the **`gp-0x6770=0` write**, i.e. resetting the
"mode" byte the caller had just set to 3/8, downstream-interpreted (per that memory) as the deliver-commit
being blocked that cycle. No DTC/fault-report call exists anywhere in this bail path.

## RECOMMENDED TRAMPOLINE ANCHOR
**Address `0x3c93c`, single instruction `st.b r0, -0x6770[gp]`, bytes `44 07 90 98`, length 4 bytes.**
- **Not pc-relative** — gp-relative store, fully relocatable into a code cave and re-executable there
  unmodified (gp is a fixed global 0xFEDF8000, unaffected by cave location).
- **Not a branch/jarl/jr** — satisfies the mission's exclusion explicitly.
- **4-byte-aligned** (`0x3c93c mod 4 == 0`) and exactly 4 bytes — a perfect 1-for-1 slot for `jr <cave>`.
- **Reached on EVERY fired path, from every caller, both arms** (see convergence proof above) — one anchor
  covers all firings; two anchors are NOT needed.
- **Reached on ZERO success paths** — telemetry captured here is unambiguously "deadband/commit gate fired
  this cycle," not conflated with the pass case.

### Register / PSW notes for the stub
- Anchor reads: `r0` (hardwired 0, no real register dependency) and `gp`/`r4` (fixed 0xFEDF8000 — must be
  intact, but no stub would touch it). Writes memory only (gp-0x6770); **no GPR is written by this
  instruction**, so nothing to restore from the anchor's own effect besides re-doing the store itself.
- Following instruction (`0x3c940 mov r28,r10`) reads `r28` — set by the UNTOUCHED preceding `mov 0x4,r28`
  at `0x3c93a` (outside the patched 4 bytes) — so `r28` survives the patch automatically; the stub must not
  clobber `r28` (or must restore it) before falling through.
- `lp` is safe to clobber (a `jarl <cave>,lp` overwrite is fine) — the function's REAL return address was
  already pushed to the stack by `prepare {r26,r28,lp},0x0` at entry (`0x3c7fc`); `dispose` at `0x3c942`
  restores `r26/r28/lp` from that stack copy unconditionally, so the LIVE register content of `lp` (and
  `r26`) at the anchor point does not affect correctness.
- **PSW/condition flags: NOT consumed downstream.** V850 `mov`/`st.b`/`dispose` do not read or write PSW.
  The flags live entering `0x3c93a` are whatever the taken bail branch's last `cmp` produced; no instruction
  between the anchor and the function's `dispose`/return reads them. Save/restore of PSW in the stub is
  therefore defensive, not structurally required at this specific anchor — but harmless to keep (matches
  the general stub template already used for the `0x4141E` per-cycle hook in
  [[reference-accord-telemetry-ram-hook-a160]]).
- **No delay slots** — this is V850E2, not SH-2A; branches take effect immediately, no instruction-after-
  branch execution-before-effect trap applies here (flagging explicitly since the general project
  boilerplate is SH-2A-oriented).
- **CRC note:** `0x3c93c` is deep inside the `[0x13000, 0xC4FFC)` code CRC block (same block covering the
  `0xC4E00` cave used for the `0x4141E` hook per [[reference-accord-telemetry-ram-hook-a160]]) — any patch
  here requires the same CRC recompute as that hook.

## Open questions / not resolved this session
- `gp-0x6773`'s own writer(s) (the flag selecting Arm A vs B) were not searched this session — all 3 known
  call sites only ever CLEAR it to 0 post-call; something else must set it to 1 to select the "committed"
  arm. Not required for the anchor recommendation (anchor is arm-agnostic) but relevant to fully closing the
  gp-0x6cc4/mode state machine.
- `gp-0x67FE==0` bypass branch inside Arm B (`0x3c890-0x3c896`) reads the SAME status byte documented
  elsewhere ([[reference-accord-v34-state4-suppression-downstream]]) as a broadly-read (55 sites), writer-
  unresolved byte — consistent with, not newly resolved by, this session.
- The third call site's `r26` param (non-zero, feeds `FUN_0003c7ce`'s full scaled-reconstruction path) was
  not traced back to its own producer — would need one more hop up in `FUN_0003d04c` to characterize what
  the case-using-cal-7407 physically represents.

## Related
[[reference-accord-segmentD-fun3d04c-full-gate-map]] — where this function was first flagged (approximate
address ranges, not byte-exact); this memory supersedes that entry's FUN_0003c7fc section with byte-exact
addresses/lengths/bytes and the trampoline-specific analysis.
[[reference-accord-engage-sm-second-gate-gp6cc4]] [[reference-accord-gp6cc4-tracking-pipeline]] — the same
`gp-0x6CC4`/cal-`0xC6354` pairing gating the ENGAGE-SM decider `FUN_00040d58`, structurally independent of
this deliver-commit reuse.
[[reference-accord-telemetry-ram-hook-a160]] — the existing per-cycle hook design (`0x4141E`) and free-RAM/
cave-CRC conventions this anchor should reuse if built into a trampoline.
