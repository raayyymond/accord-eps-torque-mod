---
name: reference_accord_gp67fa_vs_gp63fd_mode_domain_and_v75_cave_reverse_engineered
description: Accord TVA-A160 -- CORRECTS a same-session error. gp-0x67fa is NOT the mode-24/26 selector; it is a small-int EPS state byte used only via `1<<(gp-0x67fa&0xf)` bitmask tests (0xC30, 0x820 confirmed) in FUN_0002214a (the 1kHz task). gp+0x63fd is the real mode-index cell, used as a table selector (not compared to a literal) in FUN_00034350 across 5+ mode-indexed pointer-table arrays; robust mode-bit test is `(gp+0x63fd)&2` (bit1 distinguishes engaged/manual under both the 8/10 and 24/26 readings). Also fully reverse-engineers the live V81/V75 cave at 0xC4B34: it is a peak-magnitude-level encoder for gp-0x6bd0 (the damper output) feeding CAN 0x14A byte4[7:3], using a 4-bit cumulative-threshold ("thermometer") quantization of |gp-0x6bd0|>>5. Also locates gp-0x6bd0's ceiling source (mode-indexed table at 0xC77A0, fallback tp+0x7158=0xC6158). CORRECTED: gp-0x67f4 is NOT a new/open gate -- it is the speed voter's own validity flag (per a sibling agent's FUN_00041eec trace), downgraded to low priority; 0x7d00 is the generic invalid-sensor sentinel, not a physical speed rail.
metadata:
  type: reference
---

# gp-0x67fa vs gp+0x63fd mode domain, and the V81 magprobe cave decoded (2026-08-07)

Found while correcting a V83 telemetry spec after team-lead flagged the error. gp=0xFEDF8000, tp=0xBF000.

## ERROR CORRECTED: gp-0x67fa is NOT the mode-24/26 cell

I had proposed streaming `gp-0x67fa == 26` as a "mode26" telemetry bit. **This is wrong.** Fresh
`disassemble_bytes(0x2214a, 120)` on `FUN_0002214a` (the confirmed 1kHz control task):
```
0002214e  ld.bu -0x67fa[gp],r13
00022172  andi  0xf,r13,r15        ; r15 = gp-0x67fa & 0xf  (LOW NIBBLE ONLY)
0002217c  shl   r15,r11,r25        ; r25 = 1 << r15   (r11=1)
0002219e  andi  0xc30,r25,r0       ; test against mask 0xC30 = bits{4,5,10,11}
000221b2  andi  0x820,r25,r0       ; test against mask 0x820 = bits{5,11}
```
`gp-0x67fa` is used ONLY via its low nibble against small bitmasks — consistent with 167 confirmed
program-wide read/write sites (`search_instructions operand_pattern="-0x67fa"`), essentially all plain
byte compares against small integers (0/4/5/8/10 elsewhere in this domain's prior record — hard-shutdown
sentinel ==8 confirmed directly in the 330 CAN builder this same session). No comparison to 26 (or 24)
found anywhere in the sites inspected. Team-lead's independent on-car evidence: V70's flown probe for
`gp-0x67fa==10` read 0.0000%, and the standing measurement is "state is a constant 5 while driving."

**The real mode-index cell is `gp+0x63fd`.** `search_instructions mnemonic=cmp operand_pattern="0x63fd"`
= 0 hits — it is never compared to a literal; it is used purely as a TABLE INDEX. Confirmed directly this
session in `FUN_00034350` (the damper evaluator): `(byte)(&DAT_000063fd)[gp]` selects rows in **5+
independent mode-indexed pointer-table arrays** — a ceiling table (`&PTR_DAT_000c77a0`, see below), and
at least 4 more LERP-table-pointer arrays (`&DAT_000c9ccc`, `&DAT_000c9e9c`, `&DAT_000c9db4`,
`&DAT_000c9f84`), each `*4` stride. This matches [[reference_accord_gp63fd_full_enumeration_writers_and_13_reader_arrays]]'s
"13 mode-indexed reader arrays" finding exactly — confirms gp+0x63fd's ROLE, though this session did not
independently re-derive that its literal values are specifically 24/26 (trusting the existing V73-probe
provenance for that specific claim, per team-lead).

## The V81/V75 live cave at 0xC4B34 fully decoded — it's a gp-0x6bd0 peak-level encoder

Imported `_v81_C407E.511-FRICTION.STOCK_plain_image.bin` fresh (`import_file`, `language=V850:LE:32:default`,
`auto_analyze=false` — non-mutating), then `disassemble_bytes(0xC4B34, 68, dry_run=true)` — clean 28-instruction
decode, matches the known tail byte-for-byte (`ld.bu -0x1514[gp],r6 / andi 0x7 / or / st.b / movea -0x1518,gp,r6 / jmp[lp]`,
already known to reuse V49P's byte4-write pattern). The BODY, not previously read, is:
```
mov 0x0,r7
ld.h -0x6bd0[gp],r6                ; r6 = damper output (signed)
cmp r0,r6 / be L1 / bge L2 / subr r0,r6   ; abs(r6)
L2: add 0x8,r7
L1: shr 0x5,r6                     ; r6 >>= 5  (divide by 32)
cmp 0x4,r6 / blt L3 / add 0x4,r7
L3: cmp 0x9,r6 / blt L4 / add 0x2,r7
L4: cmp 0xe,r6 / blt L5 / add 0x1,r7
L5: shl 0x4,r7                     ; position level into upper nibble
ld.hu -0x6ac2[gp],r6 / cmp r0,r6 / be L6 / add 0x8,r7   ; +8 if gp-0x6ac2 != 0
L6: [pack r7 into CAN 0x14A byte4[7:3], restore r6=buffer base, jmp[lp]]
```
This is a **4-bit cumulative-threshold ("thermometer") quantization of `|gp-0x6bd0|>>5`** (thresholds at
raw-shifted values 4/9/14, contributing weights 8/4/2/1 additively — NOT exclusive branches, so values
stack: 0/8/12/14 depending on magnitude bucket) OR'd with a `gp-0x6ac2 != 0` status bit, all packed into
the already-known 330 byte4[7:3] channel. This is almost certainly the source of the route-67 L0-L4
census team-lead quoted when correcting a telemetry-threshold proposal — the live cave already streams
exactly this signal. **This is now the kit's reference implementation for a peak/magnitude-level CAN
telemetry field** — reuse this exact idiom (rescaled) rather than a raw-value page/reconstruction scheme,
which aliases badly against any producer running faster than the 100Hz CAN hook (see below).

## gp-0x6bd0 ceiling mechanism (settles a threshold-sizing question)

Still in `FUN_00034350`: `gp-0x6bd0`'s clamp ceiling is `(&PTR_DAT_000c77a0)[gp+0x63fd]` — a
**mode-indexed array of ceiling-table pointers**, LERP'd on index `gp-0x6ac2`, with fallback
`*(u16*)(tp+0x7158)` (== **0xC6158** exactly, 0xBF000+0x7158). `|gp-0x6bd0|` can never exceed this
ceiling (typically several hundred to ~1024 per team-lead's independent census reading of the live V81
cave above) — a threshold sized against the AGGREGATOR's own looser ±0x800 pass-through clamp
(`FUN_0003aa2c`, see [[reference_accord_fun3aa2c_is_gp6b94_writer_and_r24arm_gate]]) is unreachable and
structurally vacuous, the same defect class as V69's bit4. Always size a threshold against the
PRODUCER's own clamp, not a downstream consumer's slack.

## gp-0x67f4 — CORRECTION: already solved by a sibling agent, downgrade to low priority

⚠ An earlier version of this entry called this "the first structural fact on record (previously never
probed)." **That framing is wrong and is corrected here** — a sibling agent (same session) fully
decompiled `FUN_00041eec` and established `gp-0x67f4` is the **vehicle-speed voter's own validity
flag**: set to 1 when ≥2 of 5 speed channels agree within 65 counts after debounce, written at `0x4218A`
(`st.b r12,-0x67f4,gp`) and `0x421A0` (`st.b r0,...`), by the SAME function that produces the voted
speed `gp-0x6a5e`. It has zero reference to engagement, `gp-0x6806`, `gp-0x69b0`, or `gp-0x67fa`.

This session's own observation in `FUN_00034350` is the CONSUMER side and is correct, but was
mis-framed as evidence of a new/open gate. Correct framing: **`FactorC`'s speed-shaping term is
DISABLED whenever the speed voter declares itself invalid** — `gp-0x67f4 != 1` is a FAULT condition
(the voter couldn't agree on a speed), not a normal operating mode:
```c
if ((gp-0x6a5e > 0x7d00) || (gp-0x67f4 != 1)) { uVar13 = 0x400; }   // unity gain, no scaling
else { uVar13 = <LERP lookup, mode-indexed via gp+0x63fd>; }
```
**This downgrades `gp-0x67f4` from "unprobed lever" to low priority — do not spend a telemetry rung on
it.** Also: `0x7d00` in this comparison is NOT a physical speed rail; it is the generic
invalid/saturated-sensor sentinel (`ASSIST_SENTINEL = 0x7d01`) reused verbatim across `gp-0x6a5e`,
`gp-0x6a62`, and `gp-0x6a64` throughout the image — the branch is really "voter invalid OR speed
sentinel-flagged," both fault paths, not a 320 km/h physical limit. FactorC's real speed axis is
**64.0625 counts/km/h** (`X=[2240,3840,5120,8960]` = 35/60/80/140 km/h).

## Aliasing lesson (general, not just for this signal)

`gp-0x6b94`'s writer `FUN_0003aa2c` has exactly one caller, `FUN_0002214a` — the confirmed 1kHz task
(`get_function_callers`). Any telemetry hooked into a 100Hz CAN builder samples such a value 10:1
undersampled. A raw periodic sample (or worse, a multi-frame paged reconstruction of one) aliases; a
**peak-hold accumulator** (running max across several hook calls, quantized+transmitted+reset) degrades
gracefully instead and is what the kit's own existing gp-0x6bd0 cave already does. Check a signal's
producer call-chain before designing ANY telemetry sampling scheme around it, not just its CAN hook rate.

## Related
[[reference_accord_fun3aa2c_is_gp6b94_writer_and_r24arm_gate]] — the aggregator this session also traced,
whose ±0x800 pass-through clamp is NOT the same as gp-0x6bd0's own tighter producer-side ceiling.
[[reference_accord_can_tx_399_427_hook_sites_and_widened_telemetry_budget]] — the telemetry design this
correction was made for.
[[reference_accord_gp63fd_full_enumeration_writers_and_13_reader_arrays]] — prior enumeration of gp+0x63fd
this session's finding corroborates.
