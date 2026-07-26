---
name: reference-accord-v40-governor-slew-step-65535-no-overflow
description: V40's governor slew-step cals (0xC6206/0xC6208) raised to 65535 do NOT overflow the 16-bit accumulator in FUN_0004503c — they defeat the rate limiter (instant jump-to-target) instead, verified by simulation with correct V850 CMP polarity.
metadata:
  type: reference
---

Audited whether V40's `0xC6206`/`0xC6208` (governor slew step, 512/205 → 65535) could cause a
16-bit sign-wraparound in the governed-torque accumulator `gp-0x6ace` in
`FUN_0004503c` (`m_motor_torque_governor`), code `0x4543a-0x45466`.

**Mechanism (instruction-verified, code.bin/stock — V40 changes cal values only, code
byte-identical):**
- `0x45410`/`0x45416`: `ld.hu 0x7206[tp],r16` / `ld.hu 0x7208[tp],r16` — unsigned STEP load
  (fast/slow selected by `gp-0x67f5`).
- `0x4541a`/`0x4541e`: `mul r23,r16,r0; sar 0xf,r16` — `r16 = (STEP * r23) >> 15` (arithmetic
  shift, product kept in 32-bit reg, high word discarded via `r0`).
- `r23` traces to a chain of two `FUN_00049a78` calls (`param_2<=param_1 ? param_2 : param_1`,
  i.e. plain `MIN`), the first seeded with a literal `0x8000` (`0x45380: ori 0x8000,r0,r6`) —
  a Q15 "1.0" ceiling. Because `MIN` can only shrink, **r23 is provably ≤ 32768 at every
  step of the chain**, confirming a prior note ("uVar15 bounded to [0,32768]") — and this bound
  lives in the SAME function, not a different one as that note worried.
- Consequence: `STEP(≤65535) * r23(≤32768) ≤ 65535*32768 = 2^31-2^15`, always < 2^31 — the
  32-bit signed multiply/shift **never overflows for any STEP value**, by construction (the
  shift-by-15 and the 2^15 ceiling are exactly matched).
- The STEP-scaled increment (`r16`/`iVar20`) is then combined with `HELD` (`gp-0x138a`,
  signed 16-bit) and `TARGET` (`r10`) via the branch chain at `0x4543a-0x45458`. Re-derived
  the V850 `cmp op1,op2` convention as `flags = op2-op1` (matches `mov`/`add`/`sub` operand
  order) and confirmed by simulation (`/tmp/sim3.py`, both `python /tmp/sim2.py` — WRONG
  first attempt — and the corrected `/tmp/sim3.py` — right one — are worth re-running if this
  function is revisited): with STEP=65535, `STEP` so vastly exceeds any realistic
  `HELD`/`TARGET` gap (low thousands, per the adaptive cap and `0xC6202`=4762 nominal) that the
  "haven't reached/overshot target yet" guards (`0x45448 ble`, `0x45456 blt`) are ALWAYS false —
  the code ALWAYS takes the "clamp directly to TARGET" branch (`0x45458: mov r10,r8`), even
  from extreme/unrealistic starting `HELD` values (tested ±40000). The final `sxh r10` at
  `0x45466` therefore only ever sign-extends a value that was already `TARGET` (already
  in-range), never a raw unclamped `HELD±STEP` arithmetic result.

**Verdict:** STEP=65535 makes the governor slew **instantaneous** (defeats the rate limiter
every cycle) rather than causing any wraparound/overflow. This is a real behavioral change
(no slew limiting at all) but not a computational-fault mechanism. See
[[reference-accord-v40-adaptive-cap-flatten-shadow-and-limp-path]] for the paired Part-B
finding on the same V40 diff. Relevant to `docs/HANDOFF-2026-07-19-v40-governor-slew-and-rate-cap.md`
and the V42-audit request.

**Caveat:** I did not verify with a cycle-accurate emulator — this is disassembly-plus-manual-
simulation. If V42 development wants higher confidence, `mcp__ghidra__emulate_function` against
`0x4503c` with synthetic register state would be the next step.

**UPDATE 2026-07-19 (re-audit for team-lead's Q1-Q4, [VERIFIED] via direct control-flow trace,
no simulation script this time):**
- Both cal loads are `ld.hu` (unsigned halfword, zero-extend) — bytes `e5870772` @`0x45410`
  (cal `0xC6206`) and `e5870972` @`0x45416` (cal `0xC6208`). **NOT signed** — `0xFFFF` loads as
  65535, never as -1. This refutes any "negative step" hypothesis outright.
- **Q15 scale confirmed exact:** `0x4541a mul r23,r16,r0` / `0x4541e sar 0xf,r16` →
  `STEP_scaled = (STEP * r23) >> 15`. `r23` is bounded to `[0,32768]` by construction — traced
  to its literal seed `0x45380: ori 0x8000,r0,r6` feeding `FUN_00049a78` (decompiled this
  session: `return param2<=param1 ? param2 : param1` — literal unsigned `MIN`), through two
  chained `MIN` calls each masked `andi 0xffff,r10,r23`. Product ceiling
  `65535 * 32768 = 0x7FFF8000 < 0x80000000` — **provably never overflows signed 32-bit for ANY
  STEP 0-65535**, confirmed by exact arithmetic, not simulation.
- **Slew guard structure re-derived directly from the branch graph** (`0x4543a-0x45458`, V850
  `cmp op1,op2` = `flags=op2-op1`, confirmed against known operand order): the "haven't
  reached/overshot" guards (`0x45448 ble`, `0x45456 blt`) gate whether the RAW `HELD±STEP`
  candidate is used unclamped, vs `0x45458 mov r10,r8` (clamp straight to TARGET). Because that
  guard is only satisfiable when the raw candidate is still strictly inside the `[HELD,TARGET]`
  interval, the raw candidate is **self-bounded to TARGET's own small range whenever it's used**
  — TARGET itself comes from a Q15-scaled **symmetric clamp** of the aggregator command to
  `±((gp-0x4f64 * r26)>>15)` (traced `0x453f0-0x453fe`, call `FUN_00049a90` with args
  `(aggregator, -bound, +bound)` — literal 3-arg clamp). Net effect: **no 16-bit
  truncation/wraparound is possible at ANY step value in [0,65535]** — for large STEP (incl.
  0xFFFF) the guard is simply never satisfied and the code snaps directly to TARGET every cycle
  (instantaneous slew, confirming the original verdict, now via exact branch-condition proof not
  a `/tmp/sim3.py` re-run).
- **NEW — Q4, image-wide reader search (`search_instructions`, 185,693 instrs scanned):**
  `tp+0x7206`/cal `0xC6206` and `tp+0x7208`/cal `0xC6208` are each read in **exactly ONE**
  instruction in the entire 1 MB image — `0x45410` and `0x45416`, both inside
  `FUN_0004503c` and nowhere else. (The raw substring `7208` also matches 4 unrelated branch
  targets and one unrelated absolute pointer literal `0xb7208[ep]` in two other functions —
  none are `tp`-relative cal reads.) **Zero blast-radius risk from a second consumer.**
- **Practical ceiling is behavioral, not computational.** The full unsigned range `0-65535` is
  arithmetically safe (no sign flip, no multiply overflow, no 16-bit wraparound anywhere in the
  chain). The only effect of raising `0xC6206`/`0xC6208` is how close the per-cycle step gets to
  "instant snap to target" — TARGET's own magnitude is governor-bounded to roughly the low
  thousands (`0xC6202`=4762 nominal), so a STEP chosen well below that (e.g. low hundreds to
  ~1-2k) still slews gradually over multiple cycles, while STEP approaching/exceeding that range
  collapses to one-cycle snapping. **A moderate raise (e.g. 512/205 → 1500-2500ish) is safe from
  this mechanism**; there is no cal value in range that can crash or invert this function.
- Confirms V40's ignition-fault root cause is NOT this governor slew mechanism, consistent with
  the existing STILL-UNRESOLVED status in `docs/HANDOFF-2026-07-20-v41-ratecap-flat.md` /
  CLAUDE.md (limp-path cap-flatten remains the leading suspect).
