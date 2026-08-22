---
name: reference_accord_leverb_v104_v105_deployment_status_and_open_diagnostics
description: Lever B (r24 gain arm 0xC6446 512->5244 + gate repoint 0x3AA96 -0x683c[gp]->-0x6806[gp], V67/V88's mechanism) is ALREADY DEPLOYED on V104 and V105 -- confirmed by fresh byte read across the whole V96-V105 ladder, and by V104's own build-script docstring ("V101/V102/V103 all lost this lever... V104 restored it"). V62's DIFFERENT r24/r26 edit (sar 0xa->0x9 doubling at 0x3AC20/0x3AB76) is NOT on the car -- byte-identical to stock on every build checked. This is the kit's only lane with 2 independent measured+felt wins (V62, V88), and it is already active while the operator still reports grinding/ratcheting on V105. BOTH of the "two undiagnosed reasons" below are now RESOLVED (2026-08-22, `leverb-gate` task) -- see the amendment at top.
metadata:
  type: reference
---

> 🛑🛑 **RESOLVED 2026-08-22, `leverb-gate` session — BOTH open items below are closed. READ THIS FIRST.**
> 1. **Gate reachability: LIVE at creep, not gated off.** `gp-0x6806`'s gate depends only on
>    CAN LKAS-request bits, and the ramp SM's own speed-window eligibility check
>    (`gp-0x6807<3`, via cal `0xC62EA`) has its low-speed half disabled since V53 (confirmed 0
>    on V104/V105 by direct byte read) — creep speed cannot fail it. Full trace:
>    [[reference_accord_gp6807_is_live_speed_gated_not_dead_can_status]].
> 2. **Frequency mismatch: the premise is false — there is no center to move.** r24's own stage
>    (what Lever B multiplies) is provably memoryless/flat (zero state cells, zero phase, flat
>    gain). The lane's only frequency shaping is inherited from its upstream input
>    (`gp-0x4f62`'s N=4 differentiator), which is near-flat (within 0.16dB) over 7.79-26.8Hz and
>    RISES monotonically with frequency — 24.9Hz carries 1.18× MORE gain than 21.0Hz, not less.
>    Lever B is not mistuned to the old mode frequency; if anything it is already slightly more
>    potent at the new one. Full trace + H(f) table:
>    [[reference_accord_r24_leverb_transfer_function_flat_no_recenter]].
> 3. **Bonus finding**: V62's sar-doubling confirmed absent on V104/V105 too (direct byte read,
>    not just inference) — AND r24/r26's current dose (the V67/V88 arm mechanism) already matches
>    the BEST recorded grind#1 median in the kit's whole dose table, better than V62/V65's uniform
>    doubling. Stacking more r24/r26 dosing has weak prior support for the CURRENT complaint — see
>    [[reference_accord_v62_sar_absent_v104_v105_and_r24r26_at_historical_dose_ceiling]].
> ⇒ **Net: this lane is not under-deployed, not gated off, and not mistunable. The missing piece
> for the operator's still-present grinding/ratcheting most likely lies OUTSIDE r24/r26 entirely.**

# Lever B (r24/r26) deployment history, resolved by fresh byte read — 2026-08-22

`dynamics-designer` task (V106 candidate D, "which lane, and is it already tried"). Grounds the
compensator/junction memory's "V62/V88 are the only 2 wins" claim
([[reference_accord_compensator_hypothesis_junction_confirmed_and_6to9hz_reframed]]) in a fresh
byte-level deployment census this session did not find already stated anywhere on disk.

## The two DIFFERENT r24/r26 edits, and which is actually on the car [EVIDENCE — fresh Python LE byte
read across stock, V96, V100-V105]

**V62's edit** (`sar 0xa,r8`→`sar 0x9,r8` @`0x3AC20` for r24, `sar 0xa,r6`→`sar 0x9,r6` @`0x3AB76` for
r26 — doubles the lane OUTPUT regardless of which gain arm is selected):
```
0x3AC20: aa42 (unedited "sar 0xa") on EVERY build checked, stock through V105.
0x3AB76: aa32 (unedited "sar 0xa") on EVERY build checked, stock through V105.
```
**NOT on the car.** V62's own specific mechanism has not persisted.

**V88's "Lever B"** (`0xC6446` r24 gain arm 512→5244 [10.24×] + `0x3AA96` gate byte `c5`→`fb`, repointing
the arm's gate from `gp-0x683c` to `gp-0x6806`, "arm while LKAS applies" per V104's own docstring):
```
0x3AA96 gate byte:  stock/V101/V102/V103 = c5 (Honda stock, LOST)   V96/V100/V104/V105 = fb (ARMED)
0xC6446 r24 arm:     stock/V101/V102/V103 = 512                      V104/V105 = 5244 (10.24x)
```
**IS on the car** — V104 and unflashed V105 both carry it. V104's build script (read directly, not
inherited) states explicitly: *"E2/E3 are Lever B, byte-for-byte V67's encoding as last flown on
V88... V101/V102/V103 all lost this lever... V104 [restores it]."*

## Why this matters for V106
V62 and V88 are the kit's **only two builds ever with both a measured change AND an operator report of
improvement**, and both are in this one lane (`FUN_00036682`, r24/r26). **The operator's V105 report
("grinding AND ratcheting both still present") is a report on a car that ALREADY carries V88's
mechanism, active at 10.24× stock gain on that arm.** This reframes the whole candidate-D question:
the highest-prior-probability lever in the kit is not a NEW proposal, it's a DIAGNOSTIC — is it
actually helping, and if not, why not.

## Two undiagnosed reasons, named but NOT traced this session [BELIEF/hypothesis]
1. **Gate reachability**: Lever B arms on `gp-0x6806`, documented elsewhere in this kit's memory
   (`*gp6806_gate_is_can_domain*` grep pattern in this file's own index) as a CAN-command-domain gate.
   Whether that condition is actually TRUE during the creep/low-speed conditions where grinding is
   reported was not traced this session.
2. **Frequency mismatch**: V104's own pre-registered endpoint for Lever B (in its build script) scores
   **21.0-22.5Hz band RMS** against a V103 reference distribution — but `f0` migrates with gain
   (21.90/23.61/24.90Hz at 1×/4×/6× per the record). At the current 6× car the mode sits nearer
   24.9Hz, outside Lever B's own scoring band. If the lane's mechanism is itself frequency-selective
   (plausible, it's a rate/derivative-type term), it may be tuned to where the mode WAS, not where it
   IS. Not checked this session whether Lever B's own pre-registered endpoint (PASS/FAIL vs V103, LR
   14.1:1, right there in `build_v104_tva.py`) was ever actually scored on route `a4`/`a5`.

## Recommendation
Before designing any new V106 lever: (a) confirm Lever B's gate is live in the operator's actual
driving regime, (b) re-run Lever B's own build-script-specified endpoint at the CURRENT mode frequency
on route `a4`/`a5`. If gated off or mistuned in frequency, widening the gate or re-centering the target
band reuses a twice-proven mechanism rather than betting on an untested one.

## Related
[[reference_accord_compensator_hypothesis_junction_confirmed_and_6to9hz_reframed]] (the junction
topology and cancellation-law finding this deployment census grounds).
