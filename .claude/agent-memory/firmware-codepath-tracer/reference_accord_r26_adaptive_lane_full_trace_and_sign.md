---
name: reference-accord-r26-adaptive-lane-full-trace-and-sign
description: "FUN_0003aa2c r26 adaptive torque-rate lane fully disassembled: gp-0x69a4 is an unsigned magnitude (producer+consumer both ld.hu), r26 and r24 share identical dtorque + identical single polarity load so they are NEVER opposite-signed, r26 has a hard zero-force gate and 2-sample average state that r24 lacks, and r26's default-path gain table is 4 fixed records at 0xC6A68/7C/90/A4 (Y-values at +0xA/C/E/0x10 each) with zero other xrefs image-wide -- an r26-exclusive, r24-untouched cal-only neutralization target."
metadata:
  type: reference
---

Traced 2026-07-19 on stock `code.bin` (Ghidra, gp=0xFEDF8000, tp=0xBF000), tasked by team-lead to settle
whether V39's r24-only suppression left r26 as an unexamined, possibly-opposite-signed lane. Builds on
[[reference-accord-demand-aggregator-pipeline]] and the `eps_lkas_chain_model.py` Section 6B/FUN_0003aa2c
documentation (which already had the arithmetic skeleton "VERIFIED 2026-07-19" but left gp-0x69a4's sign
and the r24-vs-r26 polarity relationship explicitly OPEN).

**Q1/Q2 -- gp-0x69a4 is an UNSIGNED MAGNITUDE, never a signed rate.** Byte-confirmed at BOTH ends:
- Consumer `FUN_0003aa2c`: `0003ab3a ld.hu -0x69a4,gp,r6` (e4375d96) reads current; `0003ab4a ld.hu -0x3672,gp,r10`
  (e4578fc9) reads the persisted previous sample; `shr 0x1,r6` (unsigned shift, not `sar`) averages them.
- Producer `FUN_000352b4` (the same function that also writes sibling lane gp-0x6b86): the store at
  `000355c6 st.h r10,-0x69a4[gp]` is fed exclusively by `cmovnc r0,r8,r10` where r8 traces back only to
  `ld.hu`/`sld.hu` table loads (0x35554, 0x35568) or 0 (out-of-plausibility-window case, gated on
  `gp-0x4f60` inside +/-25600 via the `addi 0x6400,r16 ; cmp 0xc801,r16` idiom @0x355b0-b8) -- no signed
  subtraction ever reaches the stored value. So gp-0x69a4 in [0,65535], always >=0, by construction.

**Consequence for the "opposite polarity" hypothesis: FALSIFIED at the instruction level.**
r26 = `clamp(polarity * [(dtorque * avg(gp-0x69a4))>>10 * gain_A]>>10, +/-0x2000)`
r24 = `clamp(polarity * shaped(dtorque*gain_B>>10, deadzone=cal 0xC61F6), +/-0x2000)`
Both consume the IDENTICAL clamped `dtorque` register (r1, set once @0x3aaac-c0 from gp-0x4f62, clamp
+/-5120) and the IDENTICAL single polarity load `0003ab78 ld.b -0x6752,gp,r14` (0477ae98) -- there is only
ONE load of gp-0x6752 in the whole function, reused unmodified by both the r26 clip (@0x3ab7e `mul
r6,r15,r0`) and the r24 clip (@0x3ac3e `mul r14,r6,r0`). avg(gp-0x69a4) and gain_A/gain_B are both
non-negative by construction (LERP tables, all positive Y in ASSIST_RATE_A/B_RECORDS). Therefore
**sign(r26) == sign(r24) == sign(dtorque)*sign(polarity) ALWAYS** -- there is no cancellation to lose and
no hidden inversion. V39 zeroing r24 alone removed roughly half of a same-signed pair, not a canceling
term; that r26 remaining live is consistent with, not contrary to, V39's null result.

Producer sign check (gp-0x4f62 itself): `FUN_0007e74a` @0x7e832 `sub r15,r8` computes CURRENT minus
DELAYED (not delayed-minus-current), then `shl 0x1,r10 ; divq r12,r10` = 2*(current-delayed)/dt. No sign
flip. gp-0x4f62>0 <=> gp-0x4f60 (raw Sensor-B torque, CAN-negated by the 399 packer) is increasing.

gp-0x6752 (assist_polarity) itself is written only in 3 places (`FUN_00048a40`@0x48e68/88,
`FUN_000490ac`@0x490c0, `FUN_000497e6`@0x49838/44), all inside calibration/config-record parsing that
selects `1` vs `0xff` off a comma(0x2c)-vs-(-6/0xfa) discriminator byte in a parsed record -- a static,
per-part-number config value, not a live per-cycle sign. [OPEN: which branch A160's own config record
resolves to -- not traced this session; doesn't affect the r24-vs-r26 relative-sign finding above, which
holds regardless of gp-0x6752's actual value since both lanes read the same byte once per cycle.]

**Q4 -- r26 has state/gating r24 lacks.** (a) 2-sample rolling average with persisted "previous" halfword
at gp-0x3672 and a valid-flag byte at gp-0x3670 (first-cycle seeds previous=current). (b) A hard
zero-force gate absent from r24: `if (gp-0x6b5e != 0) AND (assist_state_671a < cal 0xC64FA): pre_polarity
= 0` (branch @0x3ab2e-34, skips straight to the polarity multiply with r6 forced 0) -- a genuine
discontinuity source when gp-0x6b5e or the state crosses that boundary, structurally distinct from r24's
gain-only 3-way cal switch (671d/683c/state>=5 select among cal 0xC6442/0xC6446/0xC6440, but r24 never
force-zeros). (c) r26 has NO deadzone stage -- r24 subtracts/adds cal 0xC61F6 (+/-3 in this image) before
the polarity multiply; r26 goes straight from the double-shift product to the polarity multiply. So near
dtorque~0, r24 is suppressed by its deadzone but r26 is not.

**Q5 -- r26-exclusive cal-only neutralization, address-verified, zero other xrefs image-wide.**
`FUN_0003ad74` (sole caller `FUN_00022ca0` @0x2323a, a SEPARATE RTOS task from the one that runs
`FUN_0003aa2c`) builds r26's default-path gain table from 4 FIXED (non-mode-indexed) records at
tp-relative 0x7a68/7a7c/7a90/7aa4 = absolute **0xC6A68 / 0xC6A7C / 0xC6A90 / 0xC6AA4**, stride 0x14 (20B):
u16 count(=4) @+0, s16 X[4] @+2/4/6/8, s16 Y[4] @+0xA/C/E/0x10, u16 pad @+0x12. Byte-read and confirmed
EXACT against `ASSIST_RATE_A_RECORDS` in `eps_lkas_chain_model.py`:
```
0xC6A68: X=(0,400,1600,3000)  Y=(3072,3072,2434,2048)   Y0@C6A72 Y1@C6A74 Y2@C6A76 Y3@C6A78
0xC6A7C: X=(0,250,1200,3000)  Y=(3072,3072,2488,1536)   Y0@C6A86 Y1@C6A88 Y2@C6A8A Y3@C6A8C
0xC6A90: X=(0,400,1250,3000)  Y=(2664,2664,2243,1436)   Y0@C6A9A Y1@C6A9C Y2@C6A9E Y3@C6AA0
0xC6AA4: X=(0,400,1250,3000)  Y=(2560,2560,2145,1331)   Y0@C6AAE Y1@C6AB0 Y2@C6AB2 Y3@C6AB4
```
`search_instructions` scanned all 185,693 instructions image-wide for each of the 4 record base operands
(0x7a68/0x7aa4 spot-checked directly, 0x7a7c/0x7a90 by structural adjacency -- 4 `movea`s in the same
14-instruction block) and found exactly ONE hit each, `FUN_0003ad74` itself -- **no other function reads
this table.** r24's analogous gain source (`FUN_0003ad74`'s FIRST half, gp-0x6e40/38 B-bank) draws from a
completely different, mode-INDEXED pointer-array region (0xcbf5c/0xcc044/0xcc12c + tp+0xd214=0xCC214),
confirming the two banks never overlap.
Two override cals complete the picture, each ALSO with exactly one image-wide reference (confirmed by
`search_instructions`), both inside `FUN_0003aa2c`'s r26 body only: **0xC6444** (tp+0x7444, read @0x3ab5e
when gp-0x683c!=0) and **0xC643E** (tp+0x743e, read @0x3ab68 when NOT state<cal-0xC64FA). r24 uses its own
separate override set (0xC6442/0xC6446/0xC6440) -- disjoint addresses, confirmed by direct read of the
disassembly, not assumed.
**Zeroing the 16 Y halfwords (0xC6A72/74/76/78/86/88/8A/8C/9A/9C/9E/A0/AE/B0/B2/B4) + the 2 override cals
(0xC6444, 0xC643E) makes gain_A == 0 in every reachable state, forcing r26 == 0 unconditionally for any
dtorque or avg(gp-0x69a4) -- 18 halfwords (36 bytes), entirely inside the established 0xC6000-0xC7000 cal
block this kit has safely patched since V29, no code cave, no float-mirror lockstep risk (the whole r26
computation is pure fixed-point -- zero `mulf.s`/`cvtf` instructions anywhere in FUN_0003aa2c), and
provably r24-exclusive by the single-hit xref scan above.** This is the cleanest available lever if the
operator wants to null r26 the way V39 nulled r24, without touching gp-0x69a4's producer (which is shared
with the still-untouched gp-0x6b86 sibling lane) or any code path.

Q3 (magnitude) is bounded but not pinned: analytically, r26 reaches its full +/-0x2000 clip only if
avg(gp-0x69a4) exceeds ~546 in the Q10-shifted sense (8192 = 5120*avg*3072/2^20 => avg~=546); gp-0x69a4's
own realistic runtime range was not established this session (FUN_000352b4's LERP source tables for r8
were read structurally but their absolute cal addresses were not resolved) -- so whether r26 is a trim
term or capable of matching r24's full-scale contribution is [OPEN], not [INFERRED] as a "probably small"
guess would imply.

[VERIFIED]: gp-0x69a4 unsigned at both ends; r24/r26 share dtorque + single polarity load, hence same
sign always; the 4-record A-bank addresses + byte contents; the zero-other-xrefs blast-radius scan for
all 3 candidate cal targets; gp-0x4f62 producer sign (current-minus-delayed, no flip).
[INFERRED]: the physical meaning of "reinforcing vs opposing" in a mechanical feedback sense (requires
the column/motor coupling sign, outside firmware) -- NOT resolved this session, flagged OPEN to team-lead.
[OPEN]: gp-0x6752's actual runtime value for A160; gp-0x69a4's realistic magnitude range; whether the
forward chain gp-0x6b94->governor->shaper->gp-0x6b98 preserves sign with no flip (relied on prior-session
model verification, not re-derived this pass).
