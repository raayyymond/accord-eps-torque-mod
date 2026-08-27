---
name: reference_accord_v103_byte4_free_bits_and_clip_flag_cave_design
description: "\U0001f6d1\U0001f6d1 RETRACTED 2026-08-21 IN ITS CENTRAL CLAIM -- bits {2,1,0} are NOT free, they are HONDA'S (gp-0x6799/gp-0x679b/gp-0x679a, written in FUN_00055a98 BEFORE the cave hook). This file caused a real V104 defect: a comparator built on bit 0 clobbered a live bus bit. The older accord-can-tx-100hz-base-tick-and-gateway (free channel = bits 7:3) was RIGHT; V103 has simply SPENT all five. There is NO free bit left in 0x14A. Original (now-wrong) claim was that bits 7/6/5/4/3 are claimed by V103's PASS1-3 (LKAS sign, r24-lane sign, D_state sign, r24-vs-r26 comparator, friction-vs-inertia comparator) and byte7 has zero free bits (Honda's 5:0 + V103's own identity marker at 7:6). Records the FINALIZED V104 3-bit design (clamp-1-fired at 0x35a80, clamp-2-fired at 0x35aa4, both ~30B register-liveness-spot-checked sticky-OR taps, plus a zero-hot-path-edit comparator |gp-0x6b7e|>=|gp-0x6b82| computed entirely in the existing 100Hz cave), the 1kHz-vs-100Hz sticky-OR+clear-on-read latch design, an unresolved "does reads-only forbid code-byte edits to FUN_000352b4" fork, and the GATE-1 statement for gp-0x6b82/gp-0x6b7e (no lockstep pair, confirmed) and gp-0x3814/gp-0x3818 (the one pair in the function without the shadow idiom, confirmed).
metadata:
  type: reference
---

Found 2026-08-21, `safety-gates` audit follow-up (round 3), pricing a clip-detect cave rung for the
biquad-boost candidate. Program: stock `code.bin`, fresh read of `analysis-2020accord/builds/v80_v107/build_v103_tva.py`
(the actual as-flown build script, authoritative for what's on the car), cross-checked against the
flashed `_v103_V102BASE-BIQUAD.ENGAGED-CAVE...plain_image.bin` via direct Python byte reads (not Ghidra).

## 🛑🛑🛑 RETRACTION, 2026-08-21 — THE "{2,1,0} ARE FREE" CLAIM BELOW IS **WRONG**, AND IT CAUSED A DEFECT

**Read this before anything else in this file.**

**What is wrong:** the table below marks byte4 bits **2, 1 and 0** as *free*. **They are HONDA'S.**
`FUN_00055a98` writes all three **before** the cave hook at `0x55C0E` (decompiled from the built image
by `builder-v104`):
```c
*(gp-0x1514) = *(gp-0x1514) & 0xfb | (*(gp-0x6799) & 1) << 2;   // bit 2, UNCONDITIONAL
if (gp-0x67fa == 8) { ... } else {
  *(gp-0x1514) = *(gp-0x1514) & 0xfd | (*(gp-0x679b) & 1) << 1; // bit 1
  *(gp-0x1514) = *(gp-0x1514) & 0xfe |  *(gp-0x679a) & 1;       // bit 0
}
```
**V103's own cave masks — `0xbf` / `0xdf` / `0x67` — every one of them preserves bits 2:0.** Honda's
three bits were deliberately protected on the flown build. That is corroborating evidence this file
should have weighed and did not.

**The method error, stated plainly so it is not repeated:** this file derived "free" from *which bits
V103's cave claims*, and inferred the remainder were unclaimed. **It never checked whether Honda writes
them.** It DID perform exactly that check for `byte7` — correctly finding bits 5:0 are Honda's — and
simply did not do it for `byte4`. **Enumerating our own writers is not the same as enumerating all
writers.**

**What was right all along:** `memory/accord/signals/accord-can-tx-100hz-base-tick-and-gateway.md` — *"usable free
channel is `0x14A` byte4 bits 7:3"*. That figure is **not stale**. V103 has **spent all five**, which is
a different statement from "the others became free."
⇒ **CORRECT BUDGET: `0x14A` has ZERO free bits.** byte4 7:3 = V103's five passes; byte4 2:0 = Honda;
byte7 5:0 = Honda, 7:6 = V103's identity marker. A wider channel needs either displacing one of V103's
five, or a new hook into `0x18F` / `0x1AB`.

**The harm, recorded:** the V104 design in this file was built on bit 0. Its `andi 0xfe` would have
overwritten `gp-0x679a` on a frame that goes out on the vehicle bus, with blast radius undeterminable
from this firmware alone. It was cut, caught in verification, and **reverted** — the flown V104
(`b556a0b1…`) contains no cave change at all and is byte-identical to V103 in the cave extent.
🛑 **The rung was also REDUNDANT**: V104's 427 repoint carries `|gp-0x6b86|` at full 10-bit resolution,
and the manual-arm control supplies the in-force witness at zero bit cost. **Do not re-propose it.**

⭐ **The one part of the design work below that is worth keeping** is the dead-code trap found while
placing it: the cave's `RET` is its **only** exit, so any appended pass must be **spliced before it** —
appending after leaves the code unreachable and the rung silently reads a permanent 0, which would
report "arm didn't take" on a perfectly good build. `builds/v80_v107/build_v104_tva.py` now asserts this.

**Everything below this line is the ORIGINAL text, retained as a record. Its bit-budget table is WRONG.**

---

## 🛑🛑 CAN `0x14A` byte4 free-bit budget CORRECTED — only 3 bits, not 5  ⚠ **[RETRACTED — SEE ABOVE]**

A standing figure repeated to me this task ("usable free bits are `0x14A` byte4 bits 7:3") is **stale
post-V103**. Read `builds/v80_v107/build_v103_tva.py`'s cave section directly:

| bit | claimed by | what it carries |
|---|---|---|
| 7 | PASS3 | LKAS command (`gp-0x6b4c`) sign |
| 6 | PASS1 | `\|gp-0x6ada\|>=\|gp-0x6adc\|` (r24-vs-r26 lane comparator) |
| 5 | PASS2 | `\|gp-0x6ae2\|>=\|gp-0x6b26\|` (modelled-friction-vs-inertia comparator) |
| 4 | PASS3 | `gp-0x6ada` (r24 lane mirror) sign |
| 3 | PASS3 | `gp-0x3680` (PID D-term accumulator, `D_state`) sign |
| **2,1,0** | **free** | — |

`byte7` has **zero** free bits: bits 5:0 are Honda's own data (preserved via an `andi 0x3f` mask),
bits 7:6 are V103's own build-identity marker (`mov 0x3,r7; shl 0x6,r7`). **Total free budget for new
telemetry on the currently-flashed build is 3 bits, not 5.** A wider channel needs either giving up one
of V103's existing 5 bits, or a NEW hook into whatever assembles CAN `0x18F` or `0x1AB` (both confirmed
gateway-whitelisted per `accord/signals/accord-can-tx-gateway-whitelist-and-20-free-bits.md`, on record but NOT
re-located or vetted by me this session — that file lives in the shared `memory/` tree, not found in my
own agent-memory search this session, so its exact free-bit map for those two frames is unconfirmed
by me).

## Clip-detect cave design, priced [design, register-liveness spot-checked not exhaustively swept]

Detects "the biquad output clamp saturated" cheaply by testing the ALREADY-COMPUTED post-clamp integer
`iVar34` for exact equality to `+-0x3000` (12288), rather than re-deriving the raw pre-clamp float — since
`fVar22` (the clamped float) can only be exactly `+12.0`, exactly `-12.0`, or something strictly between,
`iVar34==+-0x3000` is an exact proxy for "the clamp fired" (negligible false-positive rate from the
in-band case coincidentally landing on the boundary).

**Tap point**: `0x35a88` (`add r15,r6` — where the armed and disarmed paths converge, `r6` holds
`iVar34` BEFORE the `gp-0x6b7e` pedestal is added). Overwrite the 4 bytes at `0x35a88-8a`
(`add r15,r6`(2B `cf31`) + `sxh r6`(2B `e600`), confirmed via `disassemble_bytes`) with a 4B `jarl` to a
cave stub:
```
add r15,r6 / sxh r6                          ; replicate the 2 overwritten instructions
mov r6,r14                                    ; r14: CONFIRMED dead here (last write 0x35a7c, consumed
                                               ;   0x35a80, not refreshed until 0x35aa4)
cmp r0,r14 / bge +2 / subr r0,r14             ; r14 = |r6|
addi -0x3000,r14,r9                           ; r9: CONFIRMED dead here (last write 0x35a5c, consumed
                                               ;   0x35a60, not refreshed until 0x35aac)
bne +8
ld.b FLAGCELL[gp],r9 / ori 0x01,r9,r9 / st.b r9,FLAGCELL[gp]   ; STICKY OR, never overwrite
jmp [lp]                                      ; jarl auto-set lp=0x35a8c, no bookkeeping needed
```
~30B new cave code, 0 net bytes at the hook site. **Sampling-mismatch fix** (filter=1kHz, CAN
assembler hook=100Hz, confirmed decimated 10x): the stub already ORs (sticky, satisfies the latch
requirement); the 100Hz hook (`0x55C0E`/`0xC4B34`) needs one more `st.b r0,FLAGCELL[gp]` (4B) AFTER
packing the bit, to clear for the next window. **With BOTH halves present (OR at 1kHz + clear-after-read
at 100Hz), duty is reported correctly at 100Hz resolution — neither over- nor under-reported.** The
under-report risk the orchestrator flagged applies to a NAIVE non-sticky design (just reading the
instantaneous 1kHz-updated bit at the 100Hz tick, which misses any clip event already overwritten by a
later non-clipping tick within the same 10-tick window) — that failure mode is exactly why the sticky-OR
half of this design exists, and the clear-after-read half is what stops it degenerating into a permanent
latch that would read "1" forever after the first clip (over-reporting). Both halves are required.

**Register-liveness method**: read forward from the tap point in the existing disassembly to the next
write of each candidate scratch register, confirmed no intervening read — NOT a full dataflow sweep
(`analyze_dataflow`/pcode was not used this pass, per-instruction manual trace only). Treat as a strong
spot-check, not exhaustive GATE-1 clearance to the standard the kit applies to persistent state cells.

## Round 4 — finalized V104 3-bit allocation, GATE-1 statement, and an unresolved design fork

`safety-gates` task, V104 spec (Lever B restore + telemetry). With only 3 free bits (above), the
requested (clamp-1-fired, clamp-2-fired, magnitude-on-`gp-0x6b82`, magnitude-on-`gp-0x6b7e`) — 4 signals
— cannot all fit. **Recommended allocation**: bit2=clamp-1-fired (tap `0x35a80`, ~30B, see stub above,
UPDATED tap point — this round moved the clamp-1 tap from `0x35a88`(post-pedestal, round 3's design) to
`0x35a80`(pre-pedestal, the ARMED-only int-conversion) specifically so it measures ONLY the biquad's own
±12.0 clamp, not the combined value; the round-3 stub design is retained below unchanged for the SECOND
clamp instead); bit1=clamp-2-fired (tap `0x35aa4`, `ld.h -0x4f60,gp,r14`, replicated + `r15`(the resolved
2nd-clamp value)-abs-compare, ~30B); bit0=comparator `|gp-0x6b7e|>=|gp-0x6b82|` (needs ZERO edits inside
`FUN_000352b4` — both cells are already-stored RAM with no other reader, so this is computed entirely
inside the ALREADY-hooked 100Hz cave at `0x55C0E`/`0xC4B34`, ~20-24B appended there). No dedicated
magnitude channel survives the 3-bit budget — the comparator substitutes for "how do the two relate"
per the kit's own scale-free-comparator design law.

**`0x35a80` tap detail** (clamp-1, ARMED-only): overwrites `trncf.sw r14,r6`(4B) with a `jarl`; stub
replicates it, uses `r14`(confirmed dead: written `0x35a7c`, consumed by the trncf itself, not refreshed
until `0x35aa4`) and `r9`(confirmed dead: written `0x35a5c`, consumed `0x35a60`, not refreshed until
`0x35aac`) as scratch, sticky-ORs a flag byte, returns via `jmp [lp]` to `0x35a84` — **deliberately leaves
`0x35a84`(`br 0x35a88`)/`0x35a86`(`mov r10,r6`, the disarmed path's ENTRY POINT, reached via `be 0x35a86`
from earlier in the function) completely untouched**, avoiding any risk to the disarmed path's landing.

**`0x35aa4` tap detail** (clamp-2): overwrites `ld.h -0x4f60,gp,r14`(4B, the dropout-check's own first
instruction) with a `jarl`; stub uses `r15`(the resolved 2nd-clamp candidate) and `r9`(dead, same window)
for abs+compare+sticky-OR, replicates the overwritten load, returns via `jmp [lp]`. Measures "did the
COMBINED (`k*y[n]+gp-0x6b7e`) value hit its own `+-0x3000` ceiling", independent of the separate,
rarer extreme-torque dropout that can zero the FINAL `gp-0x6b86` afterward — not conflated.

**Total new footprint ~100B of the confirmed 1048B free** — comfortable margin.

## 🛑 Unresolved design fork, flagged not decided: does "reads only" forbid CODE-byte edits to `FUN_000352b4`?

Both tap stubs above write ONLY to two new cells (never any existing torque-path value — every
overwritten instruction is replicated exactly first, so computed VALUES stay bit-identical to stock) but
DO replace 8 bytes total of `FUN_000352b4`'s own CODE (two 4B `jarl`s). This is a genuinely different risk
class from the proven `0x55C0E` hook (6+ flown builds, Honda's own `di`/`ei` critical section, one single
already-vetted point) — these would be two NEW insertion points inside a live 1kHz control-path function,
register-liveness cleared only by manual spot-check (not an exhaustive pcode sweep — same standard as the
round-3 design, not the higher bar this kit applies to persistent state cells). **If "reads only" is meant
literally (zero code-byte changes to the torque-computing function), only the comparator bit (bit0) is
buildable with the tools/values available today** — no known RAM cell reveals clamp-fired state passively
without either a 1kHz tap (this design) or accepting a ~10x duty undercount from 100Hz-only sampling of
`gp-0x6b86`. Not resolved as of this write — orchestrator to decide.

## GATE-1 statement (finalized) [EVIDENCE, adjudicated `search_instructions`]

`gp-0x6b82`: 1 real access image-wide (`0x358dc`, the write — single `st.h`, no accompanying shadow
store). `gp-0x6b7e`: 1 real access image-wide (`0x35a1e`, same pattern). **Neither is in a lockstep
pair** — a pair would show a second `st.h` to a `gp-0x4cXX`-family cell in the SAME instruction sequence
immediately followed by a compare-and-`FUN_0006b9fa`-on-mismatch pattern; neither cell has that.
**Independently confirms a `biquad-structure` finding**: `gp-0x3814`/`gp-0x3818`'s stores (`0x35a64`,
`0x35a6a`) are PLAIN `st.w`, unlike every OTHER persistent write in this function (`gp-0x6b7a`,
`gp-0x6b86`, the `gp-0x37e8`-family, etc., all shadow-wrapped) — **these are the one pair in
`FUN_000352b4` genuinely without the shadow idiom**, consistent with them being Honda's dormant, never-
shipped filter state. **Residual, stated plainly**: all of the above is disp16/extended-disp scanning +
manual disassembly reading — blind to a hypothetical register-indirect/computed-pointer dereference of
these same physical addresses from elsewhere in the image. No tool available this session rules that
out; this is the same ceiling every prior static GATE-1 pass in this kit has had, and precisely the
`gp-0x1500` failure class.

## 🛑 FINAL DECISION (round 5) — hot-path taps REJECTED, only the zero-edit comparator ships

Orchestrator ruled: **no `jarl` insertions inside `FUN_000352b4`** (code caves are this kit's only
bricking class; the round-4 taps were novel, unflown insertion points cleared only by manual spot-check).
Also: `clip-duty`'s offline reconstruction found engaged clip duty at k=1.85 is **0.000000** (0/1,704s,
200/200 bootstrap-clean to k<=3.40, 200/200-validated against V72's flown `gp-0x69a4` probe) — the
quantity the round-4 flags would have measured is confirmed zero, so instrumenting it further was a bad
trade regardless of GATE-1. **`427` telemetry is repointed to `gp-0x6b86` instead** (a 2-byte displacement
edit at an already-vetted site, full 16-bit resolution — NOT designed by me, `boost-pricing`'s call) for
magnitude; the ONE surviving cave bit is a comparator, **`|gp-0x6b86| >= |gp-0x6b82|`** (NOT
`|gp-0x6b7e|>=|gp-0x6b82|` as round 4 proposed — orchestrator's synthesis swapped in the FINAL clamped
output for the pedestal, since it doubles as an "in-force witness": duty ~0.5 at stock (sign-set by the
pedestal), ~1.0 engaged at k>=1.25, manual frames hold stock duty as a free control).

**Finalized implementation** — appended to the EXISTING already-flown `0x55C0E`/`0xC4B34` 100Hz cave as
one more self-contained pass (same reload-mask-OR-store idiom as `PASS1`/`PASS2`, reuses ONLY `r6`/`r7`,
no new liveness claim, **zero edits inside `FUN_000352b4`**):
```
ld.h -0x6b86[gp],r6 / abs -> r7 / ld.h -0x6b82[gp],r6 / abs -> r6 / cmp r6,r7 / mov 0x1-or-0x0,r7
  (bit0, unshifted) / reload byte4 / andi 0xfe (clear bit0 only) / or r7 / store
```
**44 bytes**, cave usage `164+44=208B` of `1212B` (`1004B` still free). `ld.h -0x6b86[gp],r6`=`24377a94`
is DERIVED (not directly disassembler-observed at this register) by two independent cross-checks from
already-confirmed encodings (swapping the register-field byte on the confirmed `-0x6b86,r14` read at
`0x3ac7c`, and swapping the displacement bytes on the confirmed `-0x6b82,r6` read) — both agree exactly,
flagged as derived-not-observed regardless.

**Deliberately NOT sticky/latched** — cannot be, without a 1kHz tap, which is exactly what was just
rejected. This is a plain 100Hz instantaneous sample of a continuously-defined relationship (not a rare
threshold-crossing pulse the way the round-4 clamp flags were), so expected to track duty reasonably; a
belief-not-measured residual is flagged for potential aliasing if either cell carries content near/above
the 50Hz Nyquist of 100Hz sampling (the biquad's own pole sits at 42Hz).

## Round 6 — `ld.h -0x6b86[gp],r6`=`24377a94` INDEPENDENTLY CONFIRMED (matches this file's own derivation);
## liveness closed by PRECEDENT, not a fresh claim

Orchestrator supplied `ld.h -0x6b86[gp],r6`=`24 37 7A 94` — **exact match to this file's own two-method
cross-derivation above.** Two independent routes (mine, derived; another agent's, however they got it)
agreeing on the same 4 bytes is strong corroboration; still flagging that I have not seen it directly at
a `,r6` destination in the existing disassembly (only the `,r14` read in `FUN_0003aa2c` is disassembler-
observed).

**Liveness for the two-operand `r6`/`r7` rung is not a new claim at all** — checked byte-for-byte against
`PASS1` (already flown on V102 AND V103): `PASS1` is `ld.h[A]->r6, abs, mov r6->r7, ld.h[B]->r6, abs,
cmp r6,r7, mov-assume-set, bge, mov-clear, shl(pre-position), reload byte4, andi(mask), or, store` = 46B.
This design is the IDENTICAL shape minus the `shl` (bit0 needs no pre-shift) = 44B. **Not "V96's
single-operand style" at all — it's `PASS1`'s two-operand style, which is the more recent, more relevant,
already-on-the-car precedent.** No operand needed recomputing in-cave to avoid a fresh liveness claim.

**Final 44B sequence** (bit0, `andi 0xfe` mask): `ld.h -0x6b86[gp],r6`(4B `24377a94`) / abs->r7(6B) /
`ld.h -0x6b82[gp],r6`(4B `24377e94`) / abs(6B) / `cmp r6,r7`(2B) / `mov 0x1,r7`(2B `013a`, pattern-matched
against `PASS1`'s `043a`/`PASS2`'s `023a`) / `bge+4`(2B) / `mov 0x0,r7`(2B) / reload+mask+or+store(14B).
Cave total `164+44=208B` of `1212B`, **1004B free.**

**Checksum-last coverage**: relayed from standing kit record (CLAUDE.md / prior briefs), NOT independently
re-traced by me this task — flag before relying on it if it becomes load-bearing.

## Related
[[reference_accord_fun352b4_clamp_address_map_and_biquad_output_target_resolved]] — the clamp this rung
measures, including the triple-confirmed (decompile + manual trace + `disassemble_bytes`) symmetric-clamp
verdict and the `gp-0x6b7e` pedestal finding this rung's tap point sits just before.
