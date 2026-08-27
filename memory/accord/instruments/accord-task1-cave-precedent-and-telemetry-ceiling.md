---
name: accord-task1-cave-precedent-and-telemetry-ceiling
description: "CORRECTS the kit's cave risk model: 0x3AC78 is a task-1 1kHz trampoline hook INSIDE the aggregator that FLEW CLEAN on V39, and V48B's own postmortem exonerates the clock rate. A task-1 trampoline is PROVEN; only a STATEFUL filter allocating NEW RAM into a live path is unprecedented. Also maps the permanent whitelisted-CAN telemetry ceiling at 15 bits total."
metadata:
  type: reference
---

# 🛑🛑★★★★★ THE CAVE RISK MODEL WAS WRONG — A TASK-1 TRAMPOLINE HAS ALREADY FLOWN

2026-08-22. Found by an independent Python census of **every** `build_v*_tva.py` for hook addresses.

## THE CORRECTION
The standing claim — *"every flown cave is a read-only tap at ONE site (`0x55C0E`, task 5, 100 Hz); a cave
in a hot 1 kHz function has ZERO precedent"* — **is wrong, and was retracted by its own author.**
**Only TWO hook addresses have ever been used kit-wide: `0x55C0E` and `0x3AC78`.**

**`0x3AC78` is inside `FUN_0003aa2c` — THE AGGREGATOR ITSELF — called from `FUN_0002214a` (task 1) at
mask `0xc30`, i.e. gapless 1 kHz on the road-reachable states {4, 11}.** V39 replaced
`ld.h -0x6bd0[gp],r9` with a `jr` to `0xC4B34`, ran a 44-byte cave that conditionally zeroed a live
aggregator register, and jumped back. **It was flashed and road-tested: zero faults, drove normally.**
(V39 falsified its own hypothesis, not the hook mechanism.) It allocated **no new persistent RAM**.
⊕ Independently corroborated: a second agent's own disassembly of that exact function reads
`0003ac78: ld.h -0x6bd0[gp],r9`, byte-for-byte, 32 bytes from an unrelated line it had traced.

## 🛑 AND V48B'S OWN POSTMORTEM EXONERATES THE CLOCK RATE
Quoted from it: *"Hook `0x7FEAC`… reached exactly once per call, no loop, no sub-rate divider… The biquad
is correctly clocked at fs = 1000 — this was a worry and it is clean."* V48B died of **two named,
avoidable defects**: (a) a **RAM collision** — its `x2` state cell `gp-0x14FA` aliased a live monitor byte
inside a register-indirect-dispatched I/O-mailbox array at `0xb7260`, invisible to static scans; and (b)
**closed-loop stability never checked** — it validated open-loop magnitude against the *wrong* loop (the
LKAS crossover, 1–5 Hz) while the signal lives in the **always-on base-assist loop, which has no LKAS gate
and no speed gate**, which is why it fired **parked, with no LKAS command, in full-authority oscillation**.

⇒ **CORRECTED STATEMENT: a task-1 trampoline is PROVEN (V39, plus 55 builds at `0x55C0E`). What has never
flown is a STATEFUL FILTER that allocates NEW persistent RAM and writes into a live signal path.**
Those are two different claims and the kit had collapsed them into one.

## GROUNDWORK COMPLETED 2026-08-22, reusable for any future 1 kHz cave
- **Hook `0x36cca`** (`FUN_00036c12`, post-scale/pre-clamp) cleared by a **real pcode liveness sweep**,
  cross-validated two ways: **live-out = {gp, tp, r6, r16}**; r7–r15, ep, lp all free scratch.
- **Hook `0x346a4`** (`FUN_00034350`, Honda's own damper, before its clamp+shadow-store): **9+ free scratch
  registers, only r8 live-in.**
- ⭐ **Hook UPSTREAM of Honda's own clamp and shadow-store, and filter the LOCAL REGISTER, never the shared
  RAM cell.** Then Honda's clamp bounds whatever the filter produces and the shadow pair still writes
  atomically ⇒ **RULE 11 and the lockstep cannot trip by construction.** `gp-0x6c2c` has **4 independent
  consumers** (including the oscillation detector `FUN_000428d4`), so editing the CELL blasts far wider
  than editing a local copy.
- **RAM census, 8 cells, 3 methods** — disp16 (with the **`st.w`/`ld.w` LSB-discriminator trap**: the
  displacement halfword's LSB selects .h vs .w, so a naive word scan returns false zero hits), the 6-byte
  extended form, and `movhi`+register-indirect. Every extra raw hit adjudicated to a false positive.
  Five donors (`gp-0x6d08/6d04/6d00/6de8/6de4`) confirmed **1 writer / 0 readers**.
- **Tick ordering confirmed**: `FUN_0003b66a` runs before `FUN_00036c12` in the same tick ⇒ a cave can
  reuse those cells as filter state with **no neutralisation edit**.
- 🛑 **Shadow-lockstep pairs are AT LEAST SIX, not five** — `gp-0x6b26`/`gp-0x4cd0` was missed by the
  scoped sweep. Treat any count as a **floor**. Reading a protected cell is free; writing one half is a
  hard fault.
- 🛑 **Static clearance is STILL not sufficient.** `gp-0x1500` passed both static methods and failed on-car
  (V50P) via a runtime-computed index into the mailbox array — a pattern **no byte scan can enumerate**.
  **A live probe is the final gate.**
- **No monitor polices task-1 execution TIME** (DTC 0x18 is boot-only, re-confirmed). The real constraint
  is the RTOS deadline, with **zero diagnostic visibility if violated**. A filter-sized cave is ~30–80
  cycles against ~80,000 per tick.

## ⊕ THE WHITELISTED-CAN TELEMETRY CEILING, FULLY MAPPED — permanent
**Only three IDs cross the gateway.** `0x14A` = **0** free bits (byte4[7:3] are V103's five rungs; byte4
[2:0] are **Honda's own** `gp-0x6799`/`0x679b`/`0x679a`; byte7 Honda + identity) · `0x18F` = **10** ·
`0x1AB` = **5** (found by decompiling `FUN_00021864` rather than inheriting "already spoken for").
**Fifteen bits, total, for ever.** A new CAN ID can never reach openpilot.
⭐ **`0x18F` hook `0x55D50` is byte-stock on every build ever made**, sits *after* all of Honda's writes
including byte5's `&0xf0` clear (so a cave can OR append-only with **zero edits to Honda's instructions**),
and the checksum runs last so spare bits are auto-covered. **1048 free cave bytes verified at `0xC4BD8`.**
⚠ Sampling: 100 Hz / 21.73 Hz = **4.60 samples/cycle**, a non-integer ratio, so the sampling phase rotates
and **duty bias is indistinguishable from zero even at 20 samples** — but variance on a 4-cycle fragment
is −40 %/+15 %. **Pool bursts; never score one fragment.**

Related: [[accord-v106-built-gp6b26-x3-mode-proof]] · [[accord-can-tx-gateway-whitelist-and-20-free-bits]] ·
[[accord-v850-scan-traps-formatv-and-storezero]] · [[accord-dtc-0x18-hard-eligible-cadence-watchdog]]
