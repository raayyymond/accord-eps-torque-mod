---
name: reference_accord_fun28ea6_publishes_p_d_sum_output_orphan_safe
description: FUN_00028ea6 (the LKAS rate PID, V282/V283/V284/V285 image family) publishes its own S/P/D/output-adjacent internal terms to gp-0x6b2e/-0x6b32/-0x6b34/-0x6b36 every tick, each with exactly one live writer (itself) plus a second writer in the same proven-unreachable orphan block FUN_0002a93a that loopshape already GATE-1-cleared for the output-lag pole and Kd LERP. Safe to read; the raw dE, however, is register-only and never published anywhere.
metadata:
  type: reference
---

# `FUN_00028ea6` publishes internal PID terms to `gp-0x6b2e/32/34/36` — same orphan-safe pattern as the output-lag pole

2026-09-04, subagent `telem285`, independently re-verified from the V282 image after `build285`
first reported the finding (their memory citation for the origin of this claim,
`reference_accord_fun28ea6_publishes_its_pid_internals_to_gp_cells`, does **not exist** anywhere in
`memory/` as of this session — treat that specific filename as broken/stale, not as a source; this
memory supersedes it with a fresh, independently-verified census).

## What's confirmed [EVIDENCE, `search_instructions` + `disassemble_bytes dry_run:true`, this session]

`search_instructions` for `0x6b3` inside `FUN_00028ea6` and image-wide for each displacement
individually:

| cell | live writer (`FUN_00028ea6`) | second writer | verdict |
|---|---|---|---|
| `gp-0x6b2e` | `0x2A17C st.h r12,-0x6b2e,gp` | `0x2B064`, `FUN_0002a93a` | shared-in-code, private-in-effect |
| `gp-0x6b32` | `0x2A188 st.h r29,-0x6b32,gp` | `0x2B054`, `FUN_0002a93a` | same |
| `gp-0x6b34` | `0x2A1A2 st.h r22,-0x6b34,gp` | `0x2B068`, `FUN_0002a93a` | same |
| `gp-0x6b36` | `0x2A19C st.h r27,-0x6b36,gp` | `0x2B060`, `FUN_0002a93a` | same |
| `gp-0x6b30` | `0x2A1D4` (read), `0x2A206` (write) | not checked | 5th cell, not yet identified |

`FUN_0002a93a` (body `0x2A93A`-`0x2B06F`) sits inside `[0x2A30E, 0x2B421)`, the duplicate compiled
copy of `FUN_00028ea6`'s body that `loopshape` already proved unreachable by five independent
arguments (`docs/specs/design/LOOPSHAPE-LAGPOLE-KD-2026-09-04.md` §1.2c — no direct branch in, no
`mov imm32` builds the address, the dispatch heads are byte-identical modulo register field, etc.).
**Same mechanism, now shown to extend to these four cells too** — this is a general property of the
whole orphan block, not a one-off for the lag pole.

⚠ One `search_instructions` result for `gp-0x6b2e` needed adjudication: 3 extra `set1` hits in
`FUN_00055616` resolve to a DIFFERENT base register (`r18 = 0xFEDF0000` via `movhi -0x121,r0,r18`,
not `gp = 0xFEDF8000`) — see
[[reference_accord_operand_text_search_false_positive_wrong_base_register]] for the full worked
trap. Excluded; does not change the count above.

`gp-0x6b2e` = S, the clamped PID sum — confirmed by position: the store at `0x2A17C` sits
immediately after the `0xC61BE`=15360 sum-clamp sequence (`0x2A13A`-`0x2A172`). The identity of
`-0x6b32`/`-0x6b34`/`-0x6b36` as P/D/output (in some order) is `build285`'s attribution, **not**
independently re-derived register-by-register by me this session — treat that specific mapping as
BELIEF pending a dedicated register trace, though the mere fact of "four internal terms published,
each orphan-safe" is now EVIDENCE.

## The consequence for tapping D — and why it's still not the whole story

Reading any of these four cells from a CAN-packer cave is a plain single-operand `ld.h`, same form
every flown V282 rung already uses — cheap, GATE-1-clean by the pattern above.

🛑 **But `D = 16·dE` (or whichever cell holds D) only holds while D is inside its own `±10240` clamp
(`0xC61B6`)** — on a railed frame the SIGN survives, the MAGNITUDE doesn't, and V283 strong-turn
frames already show `|D|` 880-1552 (14-15% of the clamp) at Kd 128; that fraction only grows as Kd is
raised toward `Ku`. **The raw `dE` itself (register `r8`, `0x29EE2 sub r27,r8` inside
`FUN_00028ea6`, formed immediately before the `×Kd` multiply at `0x29EE4` and the clamp) is NEVER
stored anywhere** — reading it requires new code inside the PID's own body, not a cave read. See
[[reference_accord_fun28ea6_lp_reused_as_scratch_and_29ee4_insertion_site]] for the insertion-site
design (same-length `jr` swap at `0x29EE4`, dead register `r10` there).

⇒ **Cheap (read a published cell) and correct-for-a-Kd-sweep (tap raw `dE` pre-clamp) pull in
different directions here.** For an instrument whose whole purpose is surveying behaviour near `Ku`
— exactly the regime where the D clamp stops being rare — the pre-clamp `dE` tap is the right one
despite costing more to build.
