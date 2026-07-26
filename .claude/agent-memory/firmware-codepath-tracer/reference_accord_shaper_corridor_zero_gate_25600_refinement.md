---
name: reference-accord-shaper-corridor-zero-gate-25600-refinement
description: FUN_00042af8 soft-EME corridor arm's zero-out condition is a |gp-0x6bf0|>25600 implausibility test gated on gp-0x67fe state, not simply "off when |gp-0x6bf0|<=9216" — refines reference_accord_soft_eme_bound_arm_gating.md
metadata:
  type: reference
---

Session 2026-07-19/20, disasm via radare2 6.1.4 w64 (`asm.arch=v850` decodes this image correctly on
this build/version — no v850.gnu needed, checked against known-good disp16 sites). Stock `code.bin`,
`gp=0xFEDF8000`, `tp=0xBF000`. Dispatched as part of a driver-torque-gate sweep for `main`/team-lead.

## What's confirmed, byte-for-byte, that [[reference-accord-soft-eme-bound-arm-gating]] doesn't state

That memory says the corridor arm is "off when `|gp-0x6bf0| <= cal 0xC6156(=9216)`". Fresh disasm at
`0x43016-0x43048` shows the actual zero-out test is NOT that compare. It's:

```
0x43016  ld.bu -0x67fe[gp],r8            ; assist substate
0x4301a-0x43026  r6=(r8!=2), r15=(r8!=1) ; is substate in {1,2}?
0x43028  ld.hu 0x741a[tp],r21            ; cal 0xC641A (authority-gate operand, unrelated to this test)
0x4302c  be 0x43032 (if substate==2)
0x4302e  cmp r0,r15 ; 0x43030 bne 0x43046 (if NOT substate==1 either -> r1=1, force-zero)
0x43032  ld.h -0x6bf0[gp],r10            ; r10 = gp-0x6bf0 (driver-assist magnitude)
0x43036  ori 51201,r0,r16                ; r16 = 2*25600+1 -- classic |x|>K unsigned-compare idiom
0x4303a  addi 25600,r10,r7
0x4303e  cmp r16,r7 ; setf nc/nl,r1      ; r1 = 1 iff |gp-0x6bf0| > 25600
0x43046  mov 1,r1                        ; (fallthrough from the substate check failing)
0x43048  ld.hu 0x7156[tp],r2             ; cal 0xC6156=9216 consumed HERE, separately
...
0x4310c  cmp r0,r1 ; 0x43110 bne 0x43132 ; r1!=0 -> zero the corridor (r12=0, r7=0)
```

So: **corridor forced to 0 when `gp-0x67fe` (assist substate) is NOT in {1,2}, OR when
`|gp-0x6bf0| > 25600`.** Cal `0xC6156=9216` is NOT the zero/nonzero threshold — it's consumed
immediately after this gate resolves, as an X-axis breakpoint feeding the corridor's own
flat-extrapolated LERP (table base `tp+0x7748`, entries `0x774a/0x774c/0x774e/0x7750`; corridor
ceiling Y confirmed 5120 in V42 at `0xC674E/50` positive, `0xC675A/5C`=-5120).

25600 recurs elsewhere as a plausibility ceiling (`gp-0x4f60` Sensor-B column-torque hard bail is the
same ±25600 window per [[reference_accord_gp4f60_is_sensor_b_column_torque]]), so this reads as an
implausible-signal guard on `gp-0x6bf0`, not a hands-off/hands-on switch per se.

## What this does NOT overturn

The corridor's overall behavior — near-zero/floor for small driver-assist magnitude, ramping toward
the 5120 ceiling as `gp-0x6bf0` grows, and the separate authority-gate at `0x43112/0x43114`
(`cmp r21,r13; bh` — corridor forced 0 whenever authority `r13`(gp-0x6966) `!=0`, fully re-confirmed
byte-for-byte this session) — is UNCHANGED. This is a refinement of the exact zero-condition and the
role of cal 0xC6156, not a correction to the qualitative story in
[[reference-accord-soft-eme-bound-arm-gating]] or the V31 boost-floor root-cause chain.

## Open

Y[0] of the corridor LERP (the value at the low end of the X-table, i.e. what the corridor arm
actually equals for `gp-0x6bf0` in the roughly-9216-and-below range) is NOT dumped/confirmed this
session — the "near-zero for small driver torque" framing is an inference from the table's shape
(flat-extrapolated LERP with a 5120 ceiling), not a direct byte read of Y[0]. Next step: dump the
4-halfword X array at `0xC7748` and cross-reference against Y at `0xC674A/4C/4E/50` to pin this.

## Related

[[reference-accord-soft-eme-bound-arm-gating]] (the memory this refines) ·
[[reference-accord-corridor-lockstep]] · [[reference-accord-state4-governor-ratchet]]
