---
name: reference_accord_0x29d72_is_the_feedback_operand_hook_flagsafe
description: 0x29D72 (st.h r16,-0x6a32,gp, bytes 64 87 ce 95) is THE feedback-operand hook in FUN_00028ea6 -- r26 holds the clamped fb sum there with zero intervening accesses back to 0x28FBE and forward to sub r26,r16 @0x29D78; it is byte-identical to stock in V289 (V288 rev 2's cave is NOT in the V289 base), has NO PSW/flag hazard (unlike the 0x2A1B0 post-lag site), r7 is dead scratch, r16/r10/r26/lp are live, and it is SKIPPED once the engagement ramp reaches 0 so cave state must be seeded on gp-0x6cf8 == 0x7FFFFFFF.
metadata:
  type: reference
---

# `0x29D72` is the feedback-operand hook, and it is flag-safe

2026-09-09, subagent `fbhook`, GhidraMCP `disassemble_bytes dry_run:true` on stock `code.bin` +
raw-Python byte reads of the V289 image. Full trace:
`docs/traces/TRACE-2026-09-09-v290-feedback-operand-hook.md`.

## The site

```
0x29D6E  ld.hu 0x72e4,tp,r10     ; cal(0xC62E4)=4  -- LIVE to 0x29D7E
0x29D72  st.h  r16,-0x6a32,gp    ; 4 B, bytes 64 87 ce 95   <-- THE HOOK
0x29D76  shl   0x5,r16
0x29D78  sub   r26,r16           ; E = 32*sp - r26
```

- **LIVE across it**: `r26` (the clamped feedback operand — the injection target), `r16` (`sp`; the cave
  must replicate the `st.h` **and** leave `r16` intact), `r10` (`cal 0xC62E4`), `lp` (`jr` only, never
  `jarl` — the `0x29A2C`–`0x2A29A` reuse window contains this site).
- **Dead scratch**: **`r7`** (neither source nor destination anywhere in `0x29D40`–`0x29DAE`), plus
  `r6`/`r8`/`r9`/`r13`.
- **NO flag hazard.** `ld.hu` @`0x29D6E` sets nothing; the next flag consumer (`ble` @`0x29D82`) is armed
  by `cmp r10,r6` @`0x29D7E`, i.e. after the return point. Contrast the post-lag site `0x2A1B0`, where
  `cmp 0x1,r16` @`0x2A1AE` is live into `bne` @`0x2A1B4` and the cave must re-issue it.
- `get_xrefs_to(0x29D72)` → **no references** (not a branch target; the 4-byte `jr` cannot be jumped into).
- `jr` encoding on this binary: `hw1 = 0x0780 | (disp>>16 & 0x3F)`, `hw2 = disp & 0xFFFF`, LE. For a cave
  at `0xC4C90`: `disp = 0x9AF1E` ⇒ bytes `89 07 1e af`.

## r26's lifetime — 18-hit whole-function census, reproduced

`r26` is callee-saved (`prepare`/`dispose`) and has **zero accesses between `0x28FBE` (clamp resolved)
and `0x29D78`** — the whole 3.5 KB span is a free injection window. It is REWRITTEN at `0x29F76`, i.e.
*after* the E-former, so a hook at/after `0x2A174` must NOT read `r26` for feedback
([[reference_accord_r26_feedback_hook_cleanest_at_v288_cave_entry]]).

## ⚠ What is STALE in the older record

`DESIGN-20HZ-DAMPING-LOOPSHAPE-2026-09-08.md` and the older memory say "chain from the fb-operand site
at `0xC4C00`". **That was V288 rev 2's cave, reached by a `jr` at `0x29D72`. V289 is V282-based and does
NOT carry it** — a full-file diff (185 bytes) shows `0xC4C00` in V289 is the *sum-notch* cave hooked from
`0x2A174`, and `0x29D72` is byte-identical to stock in V289, V282 and stock. A V290 feedback cave must
install its own `jr` at `0x29D72`.

## Disengage behaviour — the one real hazard

Three `jr`s at `0x29A5C`/`0x29A64` (→ `0x2A164`) and `0x29A70` (→ `0x2A0C6`) — the complete enumeration,
`get_xrefs_to` on both targets — skip everything from the setpoint through the PID, **including this
hook**. Honda's own fb EMA at `0x28F86` sits *below* the guard and keeps running every tick against live
manual steering, so a frozen cave resumes against a completely different `r26`. Seed on
`gp-0x6cf8 == 0x7FFFFFFF`; for a notch the DC-consistent seed is `x1=x2=y1=y2=r26`, not zero.
See [[accord-disengage-skips-the-pid-hook-and-gp-0x6cf8-is-hondas-first-tick-sentinel]].

## Alternative site

`0x28FBE`+`0x28FC0` (`mov r26,r16` + `sar 0x5,r16`, a 4-byte pair; `0x28FC0` has no xrefs) runs on EVERY
tick — no freeze, no seeding — but the `r16` it produces is the rectified copy that feeds the
per-variant walk at `0x28FC8+` and `gp-0x6a34` (`st.h` @`0x290CA`, the only writer image-wide), so a
filter there changes a second lane. Not recommended.
