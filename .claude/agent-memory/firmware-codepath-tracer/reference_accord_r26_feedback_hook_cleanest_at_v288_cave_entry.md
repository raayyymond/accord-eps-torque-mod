---
name: reference_accord_r26_feedback_hook_cleanest_at_v288_cave_entry
description: r26 (the clamped feedback-EMA sum, fb) is a CALLEE-SAVED register in FUN_00028ea6 (prepare/dispose list) -- it is written once per tick (the clamp resolution near 0x28FAE/0x28FBC, or zeroed at 0x290B6 on the input-guard bail) and not touched again until the E-former at 0x29D78 (sub r26,r16). Zero intermediate readers/writers of r26 exist in that whole span, confirmed by a whole-function register census (18 total r26 hits). The V288 setpoint-filter cave's own entry (0xC4C00, reached via the jr at 0x29D72) already has r26 live with nothing downstream reading the unfiltered value before 0x29D78 -- the cleanest available hook for a feedback-side filter, cheaper than finding a new same-length swap site inside the function body.
metadata:
  type: reference
---

# `r26` (feedback sum) hook: cleanest site is the EXISTING V288 cave entry, not a new swap in the function body

2026-09-08, subagent `tracer`, stock `code.bin`, `search_instructions function:FUN_00028ea6
operand_pattern:"r26"` (18 hits total for the whole function). Answers `loopshape`'s Q8.

## `r26` is callee-saved, not scratch

`prepare {...,r26,...}` at the function's entry `0x28EA6`; `dispose ...,{...,r26,...},lp` at `0x2A30A`.
This is why it survives untouched for ~3580 bytes without being spilled/reused: the compiler deliberately
kept it live across that span.

## The full lifetime, from an 18-hit whole-function census

Written: `0x28F7C` (state load, then overwritten through the filter/clamp), final clamp resolution at
one of `0x28FAE`/`0x28FB8`-`0x28FBC` (three converging branches), or zeroed at `0x290B6` on the
input-guard-failure bail path (`|x|>12000` etc.). **Read exactly once after that**, at `0x29D78 sub
r26,r16` (the E-former, `E = 32·sp − fb`). No other access exists in the whole function.

## Candidate hook sites

1. **Inside the function body**: the three clamp branches converge at `0x28FBE mov r26,r16` (2B) +
   `0x28FC0 sar 0x5,r16` (2B) — a swappable 4-byte pair, but NOT a clean single-purpose slot: those two
   instructions start the Q7 rectification sequence (feeds `gp-0x6a34`, see
   [[reference_accord_gp6a34_publishes_rectified_fb_to_a_gated_lane]]), so a cave there must replicate
   `r16 := r26 (raw or filtered) ; r16 >>= 5` before resuming at `0x28FC2`. `lp` is live there too (an
   earlier reuse instance, `0x28EBC`-`0x290D2`, distinct from the documented `0x29A2C`-`0x2A29A` window)
   — **irrelevant for a `jr`-only hook**, since `jr` never writes `lp` (only `jarl` does); the
   established "same-length swap, `jr` not `jarl`" discipline is safe here regardless.
2. **Chaining from the V288 setpoint-filter cave (`0xC4C00`), reached via the `jr` at `0x29D72`** — per
   `SPEC-V288-SETPOINT-FILTER-CAVE-2026-09-07.md`'s own liveness table, `r26` (fb) is LIVE at this entry
   and explicitly listed as "must survive." **Confirmed this session: nothing reads or writes `r26`
   between `0x29D72` and `0x29D78` in the current code** (the 18-hit census above has no hit in that
   range besides the final consumer). **`r26` is therefore writable at the V288 cave's entry with zero
   risk of an intermediate consumer seeing a stale/partially-filtered value** — a strictly cleaner site
   than (1), since one existing hook could filter both `sp` (as V288 already does) and `fb` (a new
   addition) in the same subroutine before resuming at `0x29D76`, with no new insertion point needed.

Full trace: `docs/traces/TRACE-2026-09-08-rate-loop-lags-and-inloop-filter-hooks.md`, ADDENDUM Q8.
