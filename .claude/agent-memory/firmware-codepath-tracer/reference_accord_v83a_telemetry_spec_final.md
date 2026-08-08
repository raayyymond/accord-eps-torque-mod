---
name: reference_accord_v83a_telemetry_spec_final
description: FINAL, accepted V83a telemetry spec (8 bits, spec-only, not built as of writing) -- one splice on the live 0x14A/gp-0x6bd0 magprobe cave (adds alive-counter + build-fingerprint to byte7) and one new hook on 0x18F (adds a 4-bit |gp-0x6b94| level + sign + mode bit, thresholds 256/1024/2560/5120). Zero touch to 0x1AB in V83a. V83b follow-on spec included: gp-0x6a10/gp-0x67fe/arm-gate/damper rungs, MOTOR_TORQUE closed (will not free up bits, team-lead's final call). One new RAM cell total in V83a (gp-0x1500).
metadata:
  type: reference
---

# V83a telemetry -- accepted spec (2026-08-07)

Full design history in [[reference_accord_can_tx_399_427_hook_sites_and_widened_telemetry_budget]] and
[[reference_accord_fun3aa2c_is_gp6b94_writer_and_r24arm_gate]]. This entry is the FINAL, team-lead-
accepted 8-bit allocation after 3 rounds of correction (peak-hold-doesn't-fix-aliasing, gp-0x67fa-is-not-
mode, gp-0x6bd0-ceiling-is-tighter-than-the-aggregator-clamp). Recorded for whoever builds it.

## Bit table (8 bits, both edits together)

| frame | bits | field |
|---|---|---|
| `0x18F` byte4[2:0]+byte6.bit6 | 4 | `\|gp-0x6b94\|` level, per-sample @ 100 Hz, thresholds 256/1024/2560/5120 (team-lead's final call, supersedes an earlier 128/448/1600/4096 draft) (cumulative weights 8/4/2/1) |
| `0x18F` byte5.bit7 | 1 | sign of `gp-0x6b94` at sample |
| `0x18F` byte5.bit6 | 1 | mode `(gp+0x63fd)&2` -- robust to the 8/10-vs-24/26 ambiguity |
| `0x14A` byte7.bit7 | 1 | cave-alive counter parity (positive control) |
| `0x14A` byte7.bit6 | 1 | build fingerprint = 1 (never written pre-V83a on ANY build) |

`0x1AB` untouched, byte-stock. `gp-0x6a10` (FactorD gate/level), `gp-0x67fe` precondition, the arm-gate
AND, and the damper-≥288 sticky flag are all deferred to V83b's `0x1AB` hook (`0x55EFA`) -- tight 3-bit
and expanded 13-bit (if `MOTOR_TORQUE` frees up) allocations for that build already scoped, not repeated
here.

## Edit 1 -- splice on the live `0x14A` cave (does not touch its existing body)

Live cave at `0xC4B34`-`0xC4B75` (68 B, V75's `gp-0x6bd0` magprobe, confirmed byte-identical on
`_v81_C407E.511-FRICTION.STOCK_plain_image.bin` this session) is unchanged. Only its final 2 bytes at
`0xC4B76` (stock `7f00` = `jmp[lp]`) become a 42-byte tail running into the confirmed-free space from
`0xC4B78` (1144 B free total). New tail reads/increments/persists a new 1-byte counter at `gp-0x1500`
(0 confirmed writers/readers program-wide, fresh scan this session -- the ONLY new RAM cell in the whole
V83a spec), extracts its parity into byte7 bit7, ORs in a hardcoded bit6=1, masks against byte7's stock
bits5:0 (counter/checksum, PROVEN mask `0x3f`), then restores `r6` to the buffer base
(`movea -0x1518,gp,r6`, byte-identical to the existing cave's own restore) and returns.

## Edit 2 -- new hook on `0x18F`

Hook `0x55D50` (stock `2436e0eb` = `movea -0x1420,gp,r6`) -> `jarl <cave>,lp`. Cave reads `gp-0x6b94`
fresh every call (NO accumulator, NO peak-hold -- an earlier revision of this design used a 4-sample
peak-hold, which was WRONG: decimated-sample max doesn't recover content between samples, it's still a
25 Hz channel one layer down. 100 Hz per-sample IS the fix, since the target -- a 27.75 Hz highway limit
cycle -- has Nyquist 50 Hz, comfortably inside 100 Hz), takes `\|gp-0x6b94\|`, quantizes into a 4-bit
cumulative-threshold level (same idiom as the live `gp-0x6bd0` magprobe cave, thresholds 128/448/1600/
4096 -- the first two reused directly from the census-backed `gp-0x6bd0` breakpoints since no independent
census exists for the aggregate), packs the level split across byte4[2:0]+byte6.bit6 (non-contiguous,
matching the actual free-bit layout), sign into byte5.bit7, and `(gp+0x63fd)&2` (the mode bit, corrected
from an earlier wrong `gp-0x67fa==26` design) into byte5.bit6. Restores `r6` to the buffer base and
returns. **No new RAM** -- every write lands in bytes the stock `0x18F` builder already owns at those
exact displacements (`-0x141c`/`-0x141b`/`-0x141a`, confirmed via this session's own fresh disasm of the
stock builder, matching [[reference_accord_can_tx_399_427_bitmap]]).

## Byte-encoding provenance (for the build step)
- PROVEN, exact hex reused verbatim: the 330 splice's tail from `build_v49p_tva.py`'s `pack_polarity`
  cave (`ld.bu -0x1511`, `andi 0x3f`, `or`, `st.b -0x1511`, `movea -0x1518`, `jmp[lp]`); the 399 restore
  `movea -0x1420,gp,r6` = `2436e0eb`, the exact stock hook bytes.
- Same displacement as a real, already-disassembled stock instruction (register field differs, which
  carries none of the ld.bu/st.b parity risk): 399's `-0x141c`/`-0x141b`/`-0x141a` (stock instructions at
  `0x55c72`/`0x55cae`/`0x55ce2`).
- Genuinely new, mandatory disp16 encoder pass + Ghidra re-disassemble before any cut: `ld.bu`/`st.b
  -0x1500`; `ld.h -0x6b94[gp]`; `ld.bu 0x63fd[gp]` (positive-displacement form -- same FAMILY as the
  confirmed-working `ld.bu 0x6409[gp],r28` at `0x55e5e` in the 427 builder, but this specific
  displacement value is unverified).

## Decoder-side V83a identity rule
`330.byte7.bit6 == 1` alone is sufficient proof of V83a+: structurally never written by any instruction
in `code.bin` or any `build_v*_tva.py` output through V81 (confirmed via full builder disasm + grep this
session) -- reads 0 on any pre-V83a build regardless of live vehicle state.

## What was corrected en route (don't repeat these mistakes)
1. `gp-0x67fa` is NOT the mode cell (only used via `&0xf` bitmask tests) -- use `gp+0x63fd`, and test
   `&2` not `==26` (robust to the 8/10-vs-24/26 truncation ambiguity in the record).
2. `gp-0x6bd0`'s ceiling is its OWN evaluator's mode-indexed table (`0xC77A0`/`0xC6158` fallback), NOT
   the aggregator's looser `±0x800` pass-through clamp -- a threshold sized against the aggregator reads
   zero by construction (same defect class as V69's bit4).
3. A peak-hold over decimated 100 Hz samples does not fix aliasing against faster content -- it's still
   a 25 Hz channel. Per-sample at 100 Hz is correct when the target's Nyquist (50 Hz for a 27.75 Hz mode)
   fits inside the hook's own rate; don't over-engineer an accumulator you don't need.
4. `0x1AB` is 50 Hz, Nyquist 25 Hz -- structurally cannot carry anything meant for 27.75 Hz spectral
   work. Only slow/state signals belong there.
5. `gp-0x67f4` is NOT an open gate -- it's the speed-voter's own validity flag (see
   [[reference_accord_gp67fa_vs_gp63fd_mode_domain_and_v75_cave_reverse_engineered]]), a fault condition
   not a normal mode. Don't spend a rung on it.
6. `MOTOR_TORQUE`/`gp-0x4f74` is NOT dead code -- it's the terminal output of a live, checksum-guarded,
   1 kHz torque/current model (see
   [[reference_accord_motor_torque_zero_investigation_two_hypotheses_refuted]]). **CLOSED, final: team-
   lead decided NOT to repurpose it (2026-08-07) and stopped the sibling agent chasing it further. `0x1AB`
   stays at its structural 3 clean spare bits (`byte0[6:5]`+`byte2.bit7`) for V83b -- do not revisit.**

## V83b -- the `0x1AB` follow-on spec (not yet built, not yet bit-fitted to a final budget)

Deferred from V83a. `0x1AB` hook `0x55EFA` (stock `243634ec` = `movea -0x13cc,gp,r6`). Mode bit now
lives on `0x18F` (see above), so it is NOT duplicated here. Full candidate list, in priority order (team-
lead's explicit ranking):

1. **`gp-0x6a10` level (FactorD's LERP index)** -- already a live, computed RAM cell (`ld.hu -0x6a10[gp],rX`,
   single read, no formula needed in the cave), unsigned, unclamped, scale **0.1 deg/count**. Thresholds
   **12/25/50/150 counts** (1.2/2.5/5/15 deg), cumulative weights 8/4/2/1, same idiom as the `0x18F`
   level -- satisfies both "bracket 50 and 150" (the taper zone start/end) and "two thresholds below
   5 deg" in one 4-bit field. HIGH PRIORITY -- gates whether the FactorD lever (a speed-of-tracking-error
   damping cut, untested, never written by any build) is even worth designing.
2. **`gp-0x67fe` in {1,2}** (1 bit) -- FactorD's OTHER gate, a hard precondition: if false in a frame,
   FactorD is dead in that frame regardless of the level above. Idiom: `(raw-1) <=_unsigned 1`, the same
   pattern already live in this firmware at `FUN_0004d0ac` for a different {1,2} test.
3. Arm-gate `gp-0x671d==0 && gp-0x6806!=0` (1 bit, built against the post-repoint `gp-0x6806`).
4. Damper `|gp-0x6bd0|>=288` (1 bit), sticky/OR-accumulated since the last 427 send, reset after --
   threshold from the live `0x14A` magprobe's own route-67 census (damper sat 128-447 counts).

**Current confirmed budget is 3 clean bits** (`byte0[6:5]`+`byte2.bit7`) -- `MOTOR_TORQUE` will NOT free
up more (closed, see above). Full candidate list above is 7 bits; it will not fit as-is. Recommended cut
if 3 bits is still the number at V83b time: **`gp-0x6a10` coarse (2 bits: thresholds 25/50/150,
satisfying "bracket 50 and 150" plus one point below 5 deg) + `gp-0x67fe` (1 bit)** -- drops arm-gate and
damper from that build. Team-lead endorsed `gp-0x67fe` over any competing 1-bit ask as the right call
given its precondition framing. Final bit-fitting deferred to whenever V83b is actually cut, in case
another spare-bit source turns up between now and then.

No new RAM for V83b either -- `gp-0x6a10` and `gp-0x67fe` both read instantaneously at 427's 50 Hz rate
(team-lead confirmed: "the simpler at-rate read, not a true accumulator... angle error is slow"). Do
**not** use `gp-0x14dc` -- unverified free-scan, explicitly rejected. `gp-0x14dd` remains available
(already-vetted free byte) only if the damper sticky-latch bit makes it into a future cut.

## Related
[[reference_accord_can_tx_399_427_hook_sites_and_widened_telemetry_budget]] -- the original hook-site
discovery and 20-bit budget survey this spec draws its bits from.
[[reference_accord_fun3aa2c_is_gp6b94_writer_and_r24arm_gate]] -- `gp-0x6b94`'s producer, clamp range,
and the r24-arm gate condition.
[[reference_accord_gp67fa_vs_gp63fd_mode_domain_and_v75_cave_reverse_engineered]] -- the mode-cell
correction and the live cave's full decode.
[[reference_accord_motor_torque_zero_investigation_two_hypotheses_refuted]] -- why `0x1AB` stays
untouched in V83a.
