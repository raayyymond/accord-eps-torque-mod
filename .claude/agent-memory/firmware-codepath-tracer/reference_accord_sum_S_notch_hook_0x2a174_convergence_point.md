---
name: reference_accord_sum_S_notch_hook_0x2a174_convergence_point
description: In FUN_00028ea6, the clamped P+I+D sum S (register r12) is produced by FOUR converging paths (three clip/in-range branches plus the 0x2A164 disengage fallthrough) that all meet at 0x2A174 (ld.hu 0x73ee,tp,r7), the first instruction of the output-lag filter -- NOT before it, since the three branch predecessors are 2-byte and separate. A same-length jr swap at 0x2A174 is the hook for a notch on S. r12=S confirmed on the engaged path, r12=0 confirmed exactly on the 0x2A164 disengage route (mov 0x0,r12 at 0x2A172, falls straight through). The 0x2A0C6 "gp-0x680a lane" route also reaches 0x2A174 via its own LERP feeding the SAME clamp entry at 0x2A138, but its S value there is NOT confirmed zero. Scratch r6/r7/r9/r13 confirmed dead across 0x2A174-0x2A1B0 (4 registers, matches a biquad's need); r16/r22/r24/r27/r29 are live (published at 0x2A188/18C/190/19C/1A2) and must not be touched.
metadata:
  type: reference
---

# The sum-`S` notch hook: `0x2A174` is the ONLY convergence point, all disengage routes reach it, 4 scratch regs confirmed free

2026-09-08, subagent `tracer`, stock `code.bin`, `disassemble_bytes dry_run:true` fresh this session
(`0x2A0A0`-`0x2A1B4`). Answers `loopshape`'s Q10-Q12 for a biquad notch cave on the clamped P+I+D sum
`S`, applied between the sum clamp (`0xC61BE`) and the output-lag filter.

## The hook site

```
0x2A146/0x2A15E/0x2A162  br 0x2A174     (three 2-byte branches, the clip-high/clip-low/in-range exits)
0x2A172                  mov 0x0,r12 ; falls through, no branch          (the 0x2A164 disengage route)
0x2A174  ld.hu 0x73ee,tp,r7   <<<<< THE ONLY TRUE CONVERGENCE POINT — HOOK HERE (4 bytes)
0x2A178  ld.w  -0x3d3c,gp,r9
0x2A17C  st.h  r12,-0x6b2e,gp   ; publishes S (== gp-0x6b2e telemetry cell)
0x2A180  mul   r7,r12,r0        ; S consumed, r12 becomes b*S (S dies here)
```

Three of the four predecessors are 2-byte `br`s at DIFFERENT addresses (too short for a 4-byte `jr`,
and not one common site); the fourth falls through with no branch at all. **`0x2A174` is therefore the
only address every path passes through** — same structural shape as `0x28FBE` for the feedback clamp
(see [[reference_accord_r26_feedback_hook_cleanest_at_v288_cave_entry]]). Hook: replace the 4-byte
`ld.hu 0x73ee,tp,r7` with a 4-byte `jr <cave>`; the cave's last act before `jr 0x2A178` must replicate
that load (`r7 := 507`).

## `r12` = `S`, confirmed on both engaged and one disengage route

Engaged: all three clip/in-range branches leave the clamped value in `r12`. Disengage (`0x2A164`, target
of `0x29A5C`/`0x29A64`): `0x2A172 mov 0x0,r12` falls straight through into `0x2A174` — **`S=0` exactly**,
no branch skips the hook.

## The THIRD route (`0x2A0C6`, "`gp-0x680a` lane") also reaches the hook — but its `S` value is unconfirmed

`0x2A0C6` zeroes the SAME five registers (`r24`/`r27`/`r29`/`r22`, sentinel `r16`) as `0x2A164`, but
instead of zeroing `r12` it runs its OWN LERP (reading `gp-0x6a34` — the SAME rectified-feedback cell
from [[reference_accord_gp6a34_publishes_rectified_fb_to_a_gated_lane]] — through a table at
`tp+0x7710`-`0x7730`) producing a value that feeds `0x2A138`, the SAME clamp entry the normal path uses.
**So this route reaches `0x2A174` too (no path bypasses the hook), but its `S` is NOT proven to be zero
or small** — that needs the `tp+0x7710`-`0x7730` LERP's knot values traced, not done this session.

## Scratch census — 4 free registers, matching a biquad's need

Checked every operand from `0x2A174` through `0x2A1B0` (the interleaved-store block): `r6`, `r7`, `r9`,
`r13` are never READ in that span (each is freshly overwritten later: `r7`/`r9` by the code that still
runs after the cave at `0x2A178`/`0x2A180`/`0x2A184`/`0x2A194`; `r6` next written `0x2A1BE`; `r13` next
written `0x2A1D4`). **All four are free scratch for the cave** — `r7` has one constraint: must hold
`507` as the cave's last act. **Must NOT touch**: `r16` (E / sentinel, stored `0x2A18C`→`gp-0x6cf8`),
`r22` (→`gp-0x6b34` @`0x2A1A2`), `r24` (→`gp-0x6dd0` @`0x2A190`), `r27` (→`gp-0x6b36` @`0x2A19C`), `r29`
(→`gp-0x6b32` @`0x2A188`) — all five are published shortly after `0x2A174` by code the cave does not
displace.

## Cycle budget and free flash

**[BELIEF, no V850E2 datasheet timing traced]** ~20-25 instructions (5 `mul` + ~10 `ld`/`st` + branches),
even at a pessimistic 4 cycles/instruction ≈ 100 cycles ≈ 2.5 µs at the confirmed `PCLK=40MHz` — **≈0.25%
of the 1 ms tick**, an order of magnitude of margin even under that pessimistic assumption. No slack
indicator exists to check this against (no TCB period field, no watchdog counter found, per the source
trace's TASK 3).

**[EVIDENCE, fresh byte read]** `0xC4C2C`-`0xC4C2F` = `b6 07 4a 51` (tail of V288's own cave, non-`0xFF`);
`0xC4C30` onward is `0xFF` immediately. `[0xC4C30,0xC4FFC)` = 972 bytes, only the known 12 non-`0xFF`
bytes at `0xC4FF0`-`FB` remain — **960 bytes free**, and V288's own `jr 0x29D76` return + the `0x14A`
rung are fully contained in `0xC4BD6`-`0xC4C2F`, not in the way.

Full trace: `docs/traces/TRACE-2026-09-08-rate-loop-lags-and-inloop-filter-hooks.md`, THIRD FINAL ADDENDUM.
