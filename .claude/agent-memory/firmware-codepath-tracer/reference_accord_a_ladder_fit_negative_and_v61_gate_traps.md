---
name: reference_accord_a_ladder_fit_negative_and_v61_gate_traps
description: Empirical fit of the 8-build grind-#1 ladder against r26's unmeasured weight `a` FAILS at every tested value (max tau=0.429, both sum and antagonistic-difference models) -- kills the scalar total-rate-lane-authority model. Plus two data-integrity traps that would have corrupted the fit silently -- V61's real edit is a register-field zero at 0x3AB6C/0x3AC16, NOT the gain surface (byte-identical to stock); V67/V68/V71C bypass the LERP records entirely when engaged (gate 0x3AA96=0xFB routes to the flat arm cal instead).
metadata:
  type: reference
---

# The `a`-ladder fit is a clean NEGATIVE, and two builds nearly broke it silently

Resolved 2026-08-05, same session as [[reference_accord_gain_a_index_and_leak_v73]]. Team-lead's
primary ask: does ANY value of `a` (gp-0x69a4/1024) make the 8-build grind-#1 ladder monotone in
`T(a) = gainB/2^sar24 (+/-) (a/1024)*gainA/2^sar26`, evaluated at rate=104 (grind-#1's p50 operating
point), 0/10km/h records? Reproduce with `a_ladder_fit.py` (orchestrator scratchpad, not yet promoted
into `analysis-2020accord/`).

## 1. THE NEGATIVE RESULT [EVIDENCE: exhaustive grid, a in [0, 32768] Q10, i.e. 0-32x]

**No `a`, in either a SUM model (`+`) or a DIFFERENCE/"antagonistic" model (`-`), at either speed
record, reaches full concordance (Kendall tau=1.0) with the measured ladder** (V67/V68=109 <
V62/V65=168 < V71C=223 < V71B=545 < V70=729 < V69=746 < stock=879 < V61=2501, median `e_18-22` engaged
creep). **Best achieved anywhere in the whole sweep: |tau|=0.429 (20/28 concordant pairs), at a=0** --
i.e. the r24-ONLY model (ignoring r26/`a` entirely) is already the corpus's best-fitting scalar
story, and adding any `a` in any direction never improves on it. Sum and difference models coincide
exactly at a=0 (correct sanity check -- the a-term vanishes in both).

**Diagnostic residual**: V67/V68 (best score, 109) is the build the scalar model handles worst. Its
r26 arm is cut to 512 (tiny), so raising `a` in the SUM model actively drags V67/V68's T DOWN
(every other build's r26 term outgrows its own), even though V67/V68 should sit at an extreme if
"more scalar T = better" held. This is the quantitative form of the S1-vs-S2 tension already on
record (r26 UP helped V62/V65; r26 DOWN helped V67/V68) -- **no scalar `a`, summed or subtracted,
reconciles it.** ⇒ Kills the total/differential rate-lane-authority-as-scalar model. The mechanism is
more likely amplitude-dependent (closed-loop describing-function) or shape-dependent (which record
segment/rate-range carries the dose) than magnitude-dependent per se.

⚠ Power caveat: 8 points = 28 pairs, several involving CI-wide arms (V70/V69/V71B) per
`docs/specs/design/V72-DESIGN.md` §2.1.4's own admission (V71C vs V70 P=0.35, vs V69 P=0.15). The SIGN/ordering
negative is solid; the exact 20/28 count should not be treated as 28 independently-powered tests.

## 2. TRAP 1 -- V61's edit is NOT in the gain surface [EVIDENCE: byte-read + build-script cross-check]

`_v61_plain_image.bin` reads **byte-identical to stock** at: gate byte `0x3AA96`, both sar bytes
(`0x3AB76`/`0x3AC20`), all six arm cals (`0xC6440/42/44/46/643E`), and all four gain_A/gain_B LERP
records at 0/10km/h. A naive fit that reads "V61's gain" from any of these sources would wrongly
equate V61 with stock.

**The real edit, confirmed present**: two REGISTER-FIELD zeros, no cave, no RAM, matching
`builds/v50_v79/build_v61_tva.py`'s own documentation exactly --
```
0x3AB6C  mul r1,r6,r0 -> mul r0,r6,r0   bytes e137 -> e037   (r26 tap: r6 = r6*0 = 0)
0x3AC16  mov r1,r8    -> mov r0,r8      bytes 0140 -> 0040   (r24 tap: r8 = 0)
```
r0 is hardwired zero on V850; these zero the SHARED dtorque tap `r1` **before either gain multiply**,
so r24=r26=0 delivered unconditionally, independent of gain_A/gain_B/`a` entirely. Confirmed these
two bytes are byte-stock in all other 7 ladder builds (V70/V69/V71B/V62/V65/V67/V68/V71C) -- the
correction is V61-specific. A fit MUST special-case `T(V61)=0` rather than compute it from gains.

## 3. TRAP 2 -- V67/V68/V71C bypass the LERP records entirely when engaged [EVIDENCE]

Both run with `0x3AA96` repointed to `0xFB`. At ENGAGED creep -- grind-#1's own measured condition --
the delivered gain is the flat ARM cal (`0xC6446`=5244 for both; `0xC6444`=512 for V67/V68, =3072 for
V71C), NOT the rate=104 LERP-record value (per [[reference_accord_r24_gainb_table_structure_and_priority_gate]]'s
priority chain). Since neither build touches the underlying records, reading them directly returns
byte-stock values (3072/3072) -- plausible-looking but wrong for 2 of 8 ladder points. A fit must read
the gate byte per build and switch source (LERP record if `0xC5`/dead, arm cal if `0xFB`/repointed
AND engaged) rather than assume one source for every build. Same class of error as the mode-indexing
trap already on record for `0xCC154`/`0xCC184`.

## Related
[[reference_accord_gain_a_index_and_leak_v73]] -- `a`'s index formula, the
FUN_00039702->FUN_000389ec->FUN_000352b4 chain, and (this session, new) `FUN_0003897a` identified as
a generic asymmetric slew-rate limiter -- confirms the chain settles toward a boost-curve target at
`tp+0x769a-0x76b4` / `tp+0x7b66-0x7b98` (0xC669A-0xC66B4 / 0xC6B66-0xC6B98), NOT yet dumped/parsed.
[[reference_accord_rate_lane_v62_to_v69_gain_arc]], [[reference_accord_r24_gainb_table_structure_and_priority_gate]]
-- gate/arm priority chain this session's Trap 2 depends on.
