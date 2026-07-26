---
name: reference_accord_fun3d04c_case4_and_arb_gp6809_forwarding
description: Full decompile of FUN_0003d04c's param_1==4 (ENGAGED deliver-commit) body for Accord TVA-A160, an extra undocumented gate in FUN_00041222 before that call fires, and confirmation that the arb's gp-0x6809-gated term (iVar28) DOES reach the real arb output gp-0x6b3c (not a dead sink) -- but gp-0x6809 itself has zero writers anywhere in the image.
metadata:
  type: reference
---

# FUN_0003d04c case-4 body + FUN_00041222's hidden second gate + arb gp-0x6809 forwarding (2026-07-13)

Verified via full `decompile_function` (program="code.bin", gp=0xFEDF8000, tp=0xBF000) of `FUN_0003d04c`,
`FUN_00041222`, and line-by-line trace of `m_steer_torque_arbitration`'s decompile (dumped to a scratch
file and sliced, since the full function is 55K+ chars and exceeds tool output limits).

## FUN_0003d04c(4,0) — the ENGAGED per-cycle deliver-commit, full body [V]
```c
undefined4 FUN_0003d04c(byte param_1, short param_2)
{
  if (FUN_00018ce8(0xd)==2 || FUN_00018ce8(0xe)==2) return 5;
  if (gp-0x67fa == '\n') return 6;
  if (gp-0x4e5f != 1 || cal(tp+0x71ea)/*0xC61EA=4096*/ <= gp-0x4f68) return 3;   // Gate 5
  if (gp-0x67f4 != 1 || cal(tp+0x72fe)/*0xC62FE=320*/ <= gp-0x6a5e) return 2;    // Gate 7
  // ... param_1 < 4 handled earlier (cases 0/1/2/3, not the ENGAGED path) ...
  // param_1 == 4 (the ONLY case reached by FUN_00041222's FUN_0003d04c(4,0) call):
  gp-0x6770 = 3;
  gp-0x6858 = 0;
  gp-0x69ce = cal(tp+0x7354);      // = 0xC6354 = 4825, the SAME cal as the angle-deadband gate
  FUN_0003c4e2();
  FUN_0003c6a4();
  uVar3 = FUN_0003c7fc(0);          // angle-deadband gate; param=0 -> ref is a fixed LERP-table(0) constant
  gp-0x6773 = 0;
  return uVar3;                     // discarded by the caller regardless
}
```
Gate 5 (gp-0x4f68>=4096) and Gate 7 (gp-0x6a5e>=320) bail BEFORE reaching this block, i.e. before ANY of
gp-0x6770/gp-0x6858/gp-0x69ce get refreshed and before FUN_0003c4e2/c6a4/c7fc(0) are even called. This
confirms and pins exactly what `reference_accord_deliver_commit_gate5_gate7_trampoline_anchors` inferred
structurally.

## FUN_00041222 (ENGAGED handler) — an UNDOCUMENTED second precondition before the commit [V]
```c
void FUN_00041222(void)
{
  FUN_000406ae();
  iVar2 = FUN_00040678();
  if (iVar2==0 && gp-0x6770==0) { ... fast-path bypass check on gp-0x6772==5 ... }
  else {
LAB_00041256:
    if (gp-0x138f != 2 && FUN_00046ea6(0xd)==0) {
      iVar2 = FUN_00040d58(2);           // the decider
      if (iVar2 == 0) {                  // decider says "stay"
        iVar2 = FUN_000405fe();          // edge-triggered flag accessor (reads/clears gp-0x35B2 per
                                          // reference_accord_gp6cc4_tracking_pipeline)
        gp-0x1390 = iVar2;
        if (gp-0x138f==1 || iVar2==1) {  // <-- EXTRA GATE, not in the mission brief
          gp-0x138d = iVar2;
          gp-0x138e = gp-0x138f;
          FUN_0003d04c(4,0);             // ONLY reached if this second condition also holds
        }
      } else {
        FUN_00040e74();                 // decider fired: gp-0x35b5 = gp-0x35b6 (substate commit only)
      }
      ... gp-0x67fe trump-exit handling (separate mechanism, not detailed here) ...
    }
  }
}
```
So the deliver-commit fires only when: decider says stay (`FUN_00040d58(2)==0`) AND
`(gp-0x138f==1 || FUN_000405fe()==1)`. This second condition was not in the mission brief's framing
("If the engage-SM decider returns nonzero, that commit is SKIPPED" — true but incomplete: it can ALSO be
skipped even when the decider says stay, if this flag pair doesn't hold). Not further characterized this
session (what gp-0x138f/FUN_000405fe's gp-0x35B2 flag represent semantically) — flagged for follow-up.

## Arb gp-0x6809 gate: confirmed to reach the real output, NOT a dead sink — but see caveat
Prior memory (`reference_accord_arb_bvar1_full_enumeration`) established gp-0x6809 gates a write to
gp-0x6b2c inside `m_steer_torque_arbitration`'s state==1 re-engage-ramp sub-branch, and flagged gp-0x6b2c
as "adjacent to the documented dead-sink family gp-0x6b2e/32/34/36" (which per
`reference_accord_mixer_lkas_source_chain` genuinely have zero readers anywhere). This session traced the
LOCAL variable (not just the memory write) forward within the same function and found:
```c
// state==1 sub-branch (steady state, ramp counter already saturated):
if (gp-0x6809==1 && bVar1) { iVar28 = <LERP table value>; gp-0x6b2c = iVar28; }
else                       { iVar28 = 0; gp-0x6b2c = 0; }   // <-- fires whenever gp-0x6809 != 1
// ... much later in the SAME function ...
iVar28 = (iVar28 + iVar23) * (short)gp-0x6752/*polarity*/ * (short)cal(tp+0x746c)/*891*/;
uVar13 = iVar28 >> 0xf;
... clamps against tp+0x71b4 ...
gp-0x6b3c = (short)uVar13 * (ushort)bVar6;   // FINAL ARB OUTPUT
```
`iVar28` (zeroed by the gp-0x6809 gate) is ADDED to `iVar23` (a separate arb-curve term) before the final
gain/clamp stage that produces `gp-0x6b3c`. So the gp-0x6809 gate's zeroing effect DOES reach the real
delivered-torque chain — it is NOT inert — but it is an ADDITIVE term reduction (removes the re-engage-ramp
contribution only), not a multiplicative full-zero of the arb output; `iVar23` still contributes.

**Caveat, unresolved:** exhaustive program-wide scan (`search_instructions`, mnemonic="", "set1", "clr1",
operand containing "6809" — 185116 instructions scanned each) finds ZERO writes to gp-0x6809 anywhere in
the image; only 4 reads, all inside `m_steer_torque_arbitration` itself (0x2975a/0x29808/0x29964/0x29a2c).
Either gp-0x6809 is a permanently-dead/boot-zero byte (making `gp-0x6809==1` never true, so this term is
ALWAYS zero in every cycle, not correlated with any specific event), or it's written through a mechanism no
operand-substring search can find (e.g. a computed/indexed store with no literal "6809" in the encoding).
**Recommendation: treat this gate as LOW PRIORITY for gentle-EME telemetry purposes** until/unless a writer
is found — an always-zero term can't discriminate a specific cut event.

## Related
[[reference_accord_deliver_commit_gate5_gate7_trampoline_anchors]] — original Gate5/Gate7 byte-level find,
now embedded in full function context above.
[[reference_accord_arb_bvar1_full_enumeration]] — original gp-0x6809 gate location; this memory extends it
with the forward data-flow proof (reaches gp-0x6b3c) and the caveat about zero writers found.
[[reference_accord_fun3d4a2_hardware_phase_disable_dispatcher]] — the actual hardware physical-cut site,
recommended over any of the above as the ground-truth telemetry anchor.
[[reference_accord_gp6cc4_tracking_pipeline]] — background on gp-0x35B2/FUN_000405fe possibly related to
the newly-found second gate in FUN_00041222 (not confirmed this session).
