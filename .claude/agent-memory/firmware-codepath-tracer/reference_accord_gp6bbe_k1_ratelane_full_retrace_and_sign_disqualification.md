---
name: reference_accord_gp6bbe_k1_ratelane_full_retrace_and_sign_disqualification
description: SUPERSEDES OWN EARLIER VERSION SAME DAY. gp-0x6bbe's real formula is pol*K1*(baseline-raw angle-rate gp-0x6a56)*scale, K1@0xD200C=43 (Q7). CORRECTED: K1 is sld.h SIGNED (not unsigned as first reported), and gp-0x6a56's OWN producer (FUN_0003f776) carries a SECOND independent pol multiply that cancels the first -- net result: gp-0x6bbe is CURRENTLY a genuine -K*(column rate) damping term, not pumping. Bandwidth confirmed 0.989@-7.0deg at 8Hz (one EMA, established figure). Byte-stock confirmed directly from the V103 plain image (not a build script).
metadata:
  type: reference
---

# gp-0x6bbe full re-trace — TWO ROUNDS, 2026-08-21 (damping-injection-census, then priority-redirect C1-C5)

🛑🛑 **THIS FILE WAS WRONG EARLIER THE SAME DAY AND IS NOW CORRECTED. If you have this file cached from
before ~C1-C5 was answered, discard that version.** Round 1 (below, kept for the record of HOW the error
happened) concluded "K1 is unsigned, cannot carry independent sign, gp-0x6bbe currently pumps." Round 2
(full-function `disassemble_function`, not spot `disassemble_bytes` windows) found a SECOND `pol` load
inside `gp-0x6a56`'s own producer that Round 1 never looked for, and found K1's actual fetch instruction
is `sld.h` (signed), not the `ld.hu` pattern I'd inferred from neighboring reads. **Both errors were
caused by the same thing: judging an instruction's signedness/role from NEARBY code instead of isolating
the EXACT opcode and tracing EVERY `pol` reference by name, not by "I already found the one I expected."**
Lesson for next time: when a sign question is load-bearing, get the WHOLE function via
`disassemble_function` in one call and grep it yourself for every `ld.b -0x6752` / `sld.h` occurrence —
don't trust a spot-check window to be complete.

## ROUND 2 — the corrected, current understanding (EVIDENCE unless marked BELIEF)

**Two independent `pol` (`gp-0x6752`) loads feed `gp-0x6bbe`, and with `pol=-1` they CANCEL:**
1. `0x34ae2: ld.b -0x6752[gp],r8` inside `FUN_00034a72` itself (`gp-0x6bbe`'s producer) — propagates
   r8→r20 via the `(pol+1U<3)` validity idiom (`0x34af4-0x34b02`), used at `0x35010: mulh r20,r11`.
2. **NEW, missed on the first pass**: `0x3f77e: ld.b -0x6752[gp]` inside `FUN_0003f776`, the producer of
   `gp-0x6a56` (the raw angle-rate signal `gp-0x6bbe` reads). `FUN_0003f776` (fresh decompile) is PURE
   scale+clamp, no filter state:
   ```
   gp-0x6a56 = clamp( pol * ((gp-0x6abe * 0x30 * cal(0xC613A)) >> 0xf), ±12000 )
   ```
   `gp-0x6abe` = raw steering-COLUMN rate (established scale 4.7121 ct/(deg/s)). `cal(0xC613A)=1159`,
   confirmed the SAME address/value used by the boost-index chain (`gp-0x6ba6`'s producer,
   `FUN_0003b66a`) — a shared scale constant, cross-referenced two ways.

**Sign chain, holding baseline≈0 (see below):**
```
gp-0x6a56  = pol * S1 * gp-0x6abe                 S1 = 48*1159/32768 ≈ +1.698
rate_error = baseline - gp-0x6a56 ≈ -pol*S1*gp-0x6abe          [0x34e96: sub r6,r28]
gp-0x6bbe  = pol * K1 * rate_error * (positive scale factors)
           = pol * K1 * (-pol*S1*gp-0x6abe) * (+)
           = -pol^2 * K1 * S1 * (+) * gp-0x6abe = -K1 * S1 * (+) * gp-0x6abe      [pol^2=+1]
```
**With K1=+43 (current): `gp-0x6bbe ∝ -43*gp-0x6abe`. NEGATIVE coefficient on raw column rate —
a genuine -K*v damping term, structurally, in the shipped stock/V103 configuration, right now.**
This REVERSES my own Round-1 conclusion ("currently pumping").

**K1 IS signed** — `0x34b16: sld.h 0x0[ep],r29` (`ep` = dereferenced mode-record pointer inside table
`0xCA324`, confirmed the sole image-wide access to that table via `search_instructions`, and confirmed
zero hits for a hardcoded `0xD200C` reference anywhere else in the image — K1 is reachable ONLY through
this one path). Traced the signed `mul`/`sar` (arithmetic, sign-preserving) chain from K1's load all the
way to the `gp-0x6bbe` write — one potentially-alarming stretch (`0x34ffa mulu` / `0x34ffe shr`, both
UNSIGNED) turned out to operate on a DIFFERENT, reassigned register (`r24` reused for the always-≥0
"blendedMagnitude" after its earlier role as a validity flag was done) — the K1×rate_error value sits
untouched in `r13` throughout and re-enters via a SIGNED `mul` at `0x35000`. Full instruction-by-instruction
audit in the session's SendMessage log (2026-08-21, priority-redirect C1-C5). **A negative K1 would
correctly flip the whole term's sign — K1 is a genuine one-byte, image-wide-unique two-way sign lever.**

**"Baseline" (r28) — zeroed on 3 of 4ish FSM exit paths, indeterminate on the rest.** Full-function
disassembly shows `r28` explicitly `mov 0x0,r28` on state-2, state-3, and state-1-with-`bVar10`-false
exits; NOT written on state-0's exits or state-1-with-`bVar10`-true (`bVar10 = gp-0x67fe∈{1,2}`) — a
direct `jr`/`jr` bypass skips every zeroing site. Ghidra's own decompile shows the same gap (`iVar13`
unassigned on those paths) — not a disassembly artifact. **BELIEF, ~80% confidence: baseline≈0 in the
common/engaged operating case.** What would close it: identify what `gp-0x67fe∈{1,2}` means and whether
it's typically true or false while actively engaged/steering.

**Bandwidth — now a hard, cross-validated number, not just "unfiltered" by structural inference.**
`gp-0x6a56`'s producer has zero filter state (confirmed, pure scale+clamp). Its input `gp-0x6abe` is
written by `FUN_00041464`, established [[reference_accord_loop_lag_map_v104_and_fun41464_1khz_correction]]
to run at a CONFIRMED 1 kHz (corrected from a stale 312.5Hz belief) through ONE EMA
(`cal 0xC643C=37/128`), response **`0.989∠-7.0°` at 8 Hz** — essentially unfiltered. **Total filtering on
`gp-0x6bbe`'s entire rate path: one first-order EMA, -7° at 8 Hz. Nothing else touches it.** Best
bandwidth of any candidate found in the whole damping-injection census.

**Reconciling "phase~0° vs driver torque, REFUTES same-signed-as-torque⇒reinforcing"**: does NOT
contradict the -K*rate finding. That empirical result ruled out "gp-0x6bbe mirrors TORQUE's sign" — it
never characterized the RATE relationship. `gp-0x6bbe ∝ -rate` and "does not simply mirror torque's sign"
are both true at once, since rate and torque are not always same-signed in real driving data.

**GATE 1/byte-stock — re-verified with the V103 plain image directly (not a build script) this session**:
`_v103_V102BASE-BIQUAD.ENGAGED-CAVE.CMP.6ADA.6ADC.6AE2.6B26-SIGN.3680.6B4C.6ADA-ID.B3VARIES_plain_image.bin`
diffed byte-for-byte against stock: `FUN_00034a72` full body (1762B), `DAMP_BLOCK 0xD2000-0xD2020`
(K1+clampBound), the `FUN_00035154` monitor's independent envelope table `0xD2018` (44B), `FUN_00035154`
itself, `FUN_0003f776` (`gp-0x6a56` producer) — **all 0 diffs.** `0xC613A` (shared scale) identical both
images. Swept the wider cal neighborhood `0xC6130-0xC6500` (976B): 17 diffs found, **all already-
documented unrelated cells** (`0xC62EA` low-speed lockout, `0xC64B8`, `0xC64DE`, V103's own cave bytes) —
none touch this chain. `0xD200C`/`0xD2000` sit outside the established `[0xC5000,0xC5FFC)` CRC-skip gap;
BELIEF (not walked this session) that they're covered by the normal CRC linked list like everything else
in the `0xD` data range.

**Dose**: at the established 90 ct/(rad/s) empirical slope, 13-50°/s (0.23-0.87 rad/s) → 20-79 counts,
against the binding ±512 internal clamp (speedLERP2, confirmed unchanged) = 6.5×-26× headroom. Since the
relationship is linear in K1 and the CURRENT K1=43 already produces 20-79 counts (same order as an
8-20-count target dose), no large magnitude change is implied — `K1` in the 20s would roughly halve the
current (already damping-signed) contribution into the target range. Not a build recommendation, just the
arithmetic — gated on the baseline≈0 open item above and on whether -7°@8Hz survives as damping once the
REST of the loop's own transport delay (not measured for this specific path) is added.

## ROUND 1 (SUPERSEDED — kept only so the error is visible, do not cite as current)
K1 was believed unsigned (`ld.hu` pattern inferred from ~15 neighboring LERP reads in the same function,
without isolating K1's own fetch instruction). `gp-0x6a56`'s own producer's `pol` multiply was not found
(only checked `FUN_00034a72`'s own single `pol` load). Conclusion was "sign not independently settable,
currently pumping under the baseline≈0 simplification" — **both halves wrong**, corrected in Round 2 above.

See [[reference_accord_damping_injection_census_gp6ade_dead_and_gp6ad0_comp_add]] for the census this was
part of, [[reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal]] for the polarity fact
both rounds depend on, and [[reference_accord_loop_lag_map_v104_and_fun41464_1khz_correction]] for the
`FUN_00041464` bandwidth figure relayed above.
