---
name: reference_accord_r24_gate_repoint_reconciles_lever_b_dead_vs_v280_live
description: Reconciles the apparent contradiction between "Lever B (gp-0x683c) is unreachable, zero writers" and "V280's r24 engaged gain 0xC6446=5244 is live" -- both are correct. The 0x3AA96 gate byte is a pure hw2 displacement edit (0xC5->0xFB) that repoints the SAME ld.bu instruction at 0x3aa94 from reading gp-0x683c (dead, 0 writers, confirmed on stock AND V280) to reading gp-0x6806/STEER_CONTROL_ACTIVE (16 writers, confirmed identical set stock=V280). Nothing was armed -- the gate's SOURCE cell was swapped. Traces directly to reference_accord_gp683c_repoint_hypothesis_and_v850_bit5_encoding_rule.md's 2026-08-01 proposal, which named gp-0x6806 as exactly this repoint target.
metadata:
  type: reference
---

# r24 gate reconciliation — "Lever B unreachable" vs V280's live 0xC6446 — 2026-09-03, `fwloops20`, for `team-lead`

Team-lead's reconciliation request after I ranked r24 (10.24x engaged gain) as the #1 candidate for the
18-22Hz creep grind. Full method/numbers relayed to team-lead directly; this file records the durable
fact for future sessions.

## The resolution, one line
**"Lever B" (writing gp-0x683c to arm it) is and remains dead — nobody tried it on V104-V280.** Instead,
the single `ld.bu` instruction at `0x3aa94` that reads the gate flag was retargeted, at the raw
instruction-encoding level, to read a DIFFERENT, live cell (`gp-0x6806`) instead of the dead one. Two
different edits with the same practical effect (make the 0xC6446/0xC6444 arm reachable), only one of
which is what "Lever B" ever meant.

## Byte-level proof, this session, both `stock_fw_dump/code.bin` and the flown
`_v280_V280R2-V268BASE-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`

```
0x3aa94  stock: 84 7f c5 97   ld.bu -0x683c[gp],r15
0x3aa94  V280:  84 7f fb 97   ld.bu -0x6806[gp],r15
```
`hw1` (`84 7f`) unchanged — pure 1-byte `hw2` edit (`0xC5`→`0xFB`), no opcode/`hw1` change. Per the
existing V850 `ld.bu` displacement rule (`disp = (hw2&0xFFFE)|bit5(hw1)`, `hw1` bit5=0 on both images):
stock decodes `0x97C4|0`→`-0x683c`; V280 decodes `0x97FA|0`→`-0x6806`. This ONE flag (`lp`) gates BOTH
lanes: r26 at `0x3ab56-58` (falls through to cal `0xC6444`), r24 at `0x3ac04-06` (falls through to cal
`0xC6446`) — one edit arms both.

**Writer census, both images, this session:**
- `gp-0x683c` (`st.b`, canonical `hw2=0x97C4` exact): **0 hits, stock AND V280.** Still genuinely dead.
- `gp-0x6806` (`st.b`, canonical `hw2=0x97FA` exact): **16 hits, stock AND V280, identical address set.**
  Matches this kit's existing "16 writers/13 readers" figure for STEER_CONTROL_ACTIVE.
- Full `0x97C5`-pattern scan (catches the real read at `0x3aa94` plus 14 unrelated `-0x683b` decoy
  sites in `FUN_00052e32`/`FUN_00053216`): 15 hits stock, 14 hits V280 — the ONE site that dropped out
  is exactly `0x3AA96`; every decoy site is byte-identical between images. **This is a single, surgical,
  1-byte edit — nothing else in this instruction family moved.**

## Where this edit came from
[[reference_accord_gp683c_repoint_hypothesis_and_v850_bit5_encoding_rule]] (2026-08-01) proposed exactly
this: `gp-0x683c`'s zero-writer status confirmed 3 ways, the gate's priority order pinned
(`gp-0x671d` outranks it, tested first), and TWO live repoint candidates evaluated — `gp-0x6806`
("structure resolved, on-car chatter number already exists, semantic gap on settled-while-engaged") and
`gp-0x67fe` ("semantically cleaner, no chatter measurement yet"). `gp-0x6807` and `gp-0x67a4` were
evaluated and REJECTED on semantic grounds (multi-valued lockout state; saturation-dwell monitor,
respectively) — not by a re-derivation of the null, by content. V104's flown edit chose `gp-0x6806`.
`docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md`'s "Lever B RE-ARMED" label for this is IMPRECISE — recommend
rewording to "0x3AA96 gate repointed from dead gp-0x683c to live gp-0x6806 (STEER_CONTROL_ACTIVE)";
flagged to team-lead, not edited directly (memory-update convention).

## Open item this session did NOT close
Team-lead separately asked for r24's 20Hz small-signal gain in "aggregator counts per deg/s of WHEEL
rate", to compare against the LKAS lane's ~46-73 counts/deg/s DC. r24's native loop variable is
`gp-0x4f62`, a TORQUE-RATE (4-tap difference of `gp-0x4f60`, driver/column TORQUE — see
[[reference_accord_gp4f62_torque_rate_producer_and_c6c42_window]]), not a wheel-rate signal. Converting
requires a torsion-bar-stiffness/mechanical-impedance constant relating `gp-0x4f60` to column/wheel
angle — grepped this kit's record (torsion bar stiffness, `gp-0x4f60` absolute scale) and found nothing;
the golden model's own docstring (`eps_lkas_chain_model.py:173`) says outright "the CAN count scale is
not proven identical to gp-0x4f60's." **This constant is NOT on record anywhere in this kit as of this
session.** What IS certified: r24's gain per torque-rate-count at 20Hz = `(5244/1024) * 0.9894` (the
-0.092dB factor from the differencer) ≈ **5.067 aggregator-counts per torque-rate-count**, phase
**+75.6°** from the torque-rate input (14.4° lag from an ideal derivative). Concrete next step if this
conversion is needed: trace `FUN_0007f3f8` (`gp-0x4f60`'s Sensor-B fusion producer) back to its raw
ADC/CAN scale — not done this session.

## Related
[[reference_accord_gp683c_repoint_hypothesis_and_v850_bit5_encoding_rule]] · [[reference_accord_rate_lane_v62_to_v69_gain_arc]] ·
[[reference_accord_gp4f62_torque_rate_producer_and_c6c42_window]] · [[reference_accord_v280_engaged_gates_census_biquad_confirmed_live]]
