---
name: reference_accord_v103_probe_bitmap_final_and_identity_exhaustion
description: "🛑 SUPERSEDES an earlier same-day version of this file (b5=D's sign) -- team-lead reversed once more after cave-engineer's insight. TRUE FINAL, per team-lead msg 984096da: b3 -> sign(gp-0x3680) (D_state's delivered sign), b5 UNCHANGED (stays the friction-vs-inertia comparator). Exactly ONE bit changes from V102's map (b7/b6/b4/b5 all unchanged). Identity solved BETTER than the b5 version: b3 now TOGGLES where every predecessor pinned it constant (V101=1, V102=0) -- a categorical, fast-to-establish signature, not a duty-comparison. Records the ld.w -0x3680,gp,r6 = 24 37 81 c9 encoding (cave-engineer-derived, Ghidra-verified) since no ld.w-to-r6 example existed anywhere in the image to copy."
metadata:
  type: reference
---

# V103 probe: TRUE final bit map (b3, not b5, carries D), identity via toggle, gp-0x3680's cave-ready encoding

🛑 **This file was edited once already today to reflect a b5-carries-D map that was itself superseded
minutes later.** The map below (b3 carries D, b5 unchanged) is team-lead's final ruling, message
`984096da` to `cave-engineer`. If any other document/message states b5=D's sign, it is stale.

Designed 2026-08-20, task `damphunt round 3` continuation, in response to team-lead's V103 build request
(the operator chose the comparator probe over a bigger gain swing for V104's benefit). Builder:
`cave-engineer`. Base: V102's existing 154B cave at `0xC4B34`, hook `0x55c0e` inside `FUN_00055a98`
(the CAN `0x14A` / STEER_ANGLE_RATE 100Hz TX packer — see
[[reference_accord_probe_cave_c4b34_trampoline_and_jarl_encoding]] for the trampoline mechanics).

## The TRUE final map [EVIDENCE — cleared by team-lead, msg `984096da`]

| bit | boolean | cell(s) | role | expected value (proves wiring, or IS the measurand) |
|---|---|---|---|---|
| b7 | `gp-0x6b4c < 0` | `gp-0x6b4c` | UNCHANGED — wiring control | duty ≈0.27, rising 0.148→0.417 with wheel rate (V102's own measured pattern) |
| b6 | `\|gp-0x6ada\| ≥ \|gp-0x6adc\|` | `gp-0x6ada`,`gp-0x6adc` | UNCHANGED — wiring control | engaged duty 0.8991, rising 0.836(<1°/s)→0.981(13-25°/s)→0.992(25-50°/s) (V102, from `route-v102`) |
| b5 | `\|gp-0x6ae2\| ≥ \|gp-0x6b26\|` | `gp-0x6ae2`,`gp-0x6b26` | **UNCHANGED** — kept, not sacrificed | friction-vs-inertia comparator, preserved |
| b4 | `gp-0x6ada < 0` | `gp-0x6ada` | UNCHANGED — the r24/r26 measurand | r24's delivered Re(Z) sign, via offline CSD against bus `rate_f` |
| **b3** | **`sign(gp-0x3680) < 0`** | **`gp-0x3680` (D_state)** | **NEW — the measurand AND the identity signal** | D's delivered Re(Z) sign at 6-9Hz (and, free, 18-22/26-31Hz — same continuous 100Hz stream) via offline CSD against bus `rate_f`; ALSO doubles as identity (see below) |

**Exactly one bit changes from V102's map.** `b7`, `b6`, `b5`, `b4` are all byte-identical in logic to
V102; only `b3` moves from "forced constant 0" to "computed sign of `gp-0x3680`." Register discipline
unchanged: r6/r7 only, recompute inside each pass. `PASS1`'s mask (`0xB7`, owning bits 6 and 3) is
unaffected structurally — it now needs an extra compute-and-OR for bit 3 (read `gp-0x3680`, compare,
branch, shift into bit 3) instead of just clearing it, but pass OWNERSHIP and the mask partition are
identical; `PASS3` (`b7`,`b4`, unchanged, runs last) still proves `PASS1`/`PASS2` executed regardless of
what `PASS1` computes for bit 3.

## 🛑🛑 The 0x14A byte4/byte7 single-frame identity scheme is EXHAUSTED — but `b3` toggling is a BETTER fix than duty-comparison

Both identity axes independently ran out at V102:
- `byte7[7:6]` (2 bits, 4 codes): **all 4 allocated** — 0=≤V91, 1=V96/97, 2=V98-V100, 3=V101/V102.
- `b3` (1 bit, 2 static values): **both allocated as CONSTANTS** — V101 forces it `1` (unconditional
  `add 0x8,r7`), V102 forces it `0` (via the `PASS1` mask). A 1-bit field forced to EITHER constant value
  reproduces an existing build's signature, not a new one.

**Resolution, team-lead-final, better than this file's own earlier version**: `b3` is no longer a
constant on V103 — it's a LIVE bit, tracking `gp-0x3680`'s sign, which changes at ~7-9Hz easily. **A bit
that VARIES where every predecessor PINNED it constant is a categorical identity signature** — you only
need to observe ONE 0 and ONE 1 on the same channel to know it's not V101 (always 1) or V102 (always 0),
which is faster and simpler to establish than comparing full duty statistics (this file's own earlier,
now-superseded version proposed watching `b5`'s duty differ from V102's — team-lead's later map is
strictly better: it keeps `b5` unchanged AND gets a faster identity check, at the cost of exactly the
same one bit either way). **V103 is the first build since V85 without a single-frame identity witness.**

🛑 **Scorer instruction, exact wording from team-lead, must travel with the decoder**: *"`b3` MUST VARY.
A constant `b3` means either the build is not V103 or the D rung is dead — and that is the
run-invalidating check, not a finding."* The ~50-build "byte4 is always odd" convention died at V98; the
byte7-plus-b3-constant convention dies here too — **either old rule will misroute or reject V103's
telemetry.**

⚠ **Open question for a future session**: is `byte7[7:6]=0` or `=1` genuinely reusable (Honda's own
reset value there, or an even-earlier pre-V91 build's claim)? Not re-litigated this session — team-lead's
framing that all 4 codes are spent was taken as settled, matching their own build-lineage table.

## `gp-0x3680` (D_state) — cave-ready facts

**32-bit** (`ld.w`/`st.w`), unlike every other cell this cave touches (`gp-0x6ada`/`gp-0x6adc`/`gp-0x6ae2`/
`gp-0x6b26`/`gp-0x6b4c` are all 16-bit, `ld.h`/`st.h`). GATE-1: 1R/1W, both inside `FUN_0003a382`
(`0x3a85c` read, `0x3a87a` write), zero other consumers image-wide (183,569-instruction whole-image
scan) — re-confirmed this session, matches [[reference_accord_pump_hunt_comparator_probe_candidates]].

**`ld.w -0x3680[gp],r6` = `24 37 81 c9`** [EVIDENCE, `cave-engineer`-derived, Ghidra SLEIGH-verified via a
scratch program + `disassemble_bytes(dry_run=true)`, not hand-decoded]. No `ld.w ...,gp,r6` example
existed anywhere in the 183,569-instruction image to copy byte-for-byte (only `ld.w ...,gp,r9`
@`0x3a85c`=`24 4f 81 c9` and `...,gp,r15`@`0x3a832`=`24 7f 7d c9` existed as real anchors) — the
register field (`byte1 = 0x37` for r6, confirmed against dozens of existing `ld.h ...,gp,r6` instructions
since `ld.h`/`ld.w` share `hw1`'s encoding) had to be derived rather than copied. **Correctly declined to
hand-derive this myself and handed it to the builder instead** — matches this kit's own most-repeated
failure-mode warning (hand-decoded V850 opcodes).

## The b7/b6 "wiring control" vs a phase-domain "method control" — a real distinction, recorded for reuse

`b7`/`b6` unchanged (reproducing V102's own measured marginal duty) proves the **bit map is wired
correctly** — same source cell, same offset, same mask. It does NOT independently re-validate that the
**offline cross-spectral method** (comparator bit → CAN → Welch/CSD against bus rate → Re(Z) sign)
correctly recovers a KNOWN phase relationship — that would need a control whose EXPECTED
CROSS-SPECTRAL PHASE (not just marginal duty) is already independently measured, e.g. `gp-0x6b26`'s
own +518/+565ct/+137°/+139° finding (V96, on-car). **This build ships without a phase-domain control**
(team-lead's call, on the reasoning that the CSD method itself is the same code already validated by
the `gp-0x6b26`/whole-car measurements on prior builds, so it doesn't need re-proving per-build) —
recorded so a future session doesn't assume `b7`/`b6` cover this and skip designing one when it's
actually needed.

## Related
[[reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal]] — why D's sign needed
resolving in the first place. [[reference_accord_pump_hunt_comparator_probe_candidates]] — the earlier
candidate-cell census this map was built from. [[reference_accord_probe_cave_c4b34_trampoline_and_jarl_encoding]]
— the hook mechanics this build reuses unchanged.
