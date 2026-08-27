---
name: reference-accord-arb-bvar1-full-enumeration
description: Full byte-level enumeration of every LKAS-integrator-zeroing gate inside m_steer_torque_arbitration (FUN_00028ea6), Accord TVA-A160 -- bVar1 health computation plus three additional hard-BAIL range checks (gp-0x4f60, gp-0x6752 polarity, gp-0x6a56), and where gp-0x6809 (deliver flag) and bVar1 get consumed. All thresholds are far above real driving magnitudes -- LOW bump-sensitivity verdict.
metadata:
  type: reference
---

# `FUN_00028ea6` (`m_steer_torque_arbitration`) — full bVar1/bail gate enumeration

Verified 2026-07-03 via radare2 `v850.gnu` linear disasm (`code.bin`, gp=0xFEDF8000, tp=0xBF000). r2's `af`
auto-boundary badly truncates this function (reports size=316 due to internal `jr` jump-table-style tail
calls) — use `pd <N> @ addr` linear disasm, not `pdf`, for this function.

## bVar1 (r29) computation — 0x28eae–0x28f22 [V]

`bVar1 = (gp-0x67f4==1) AND (ch1..ch5 all < 32001) AND (gp-0x6a5e < 32001)`, else 0. All 6 sub-checks funnel
into a shared fail target `0x28f1c` (`mov 0,r29`):

| Signal | gp offset | addr checked | ceiling |
|---|---|---|---|
| plausibility flag | gp-0x67f4 | 0x28eae (loaded), 0x28f0a (tested) | ==1 required |
| ch1 | gp-0x6a44 | 0x28eb2/0x28ec4 | ≥32001 fails |
| ch2 | gp-0x6a40 | 0x28ed4/0x28ed8 | ≥32001 fails |
| ch3 | gp-0x6a3c | 0x28ee2/0x28ee6 | ≥32001 fails |
| ch4 | gp-0x6a38 | 0x28eee/0x28ef6 | ≥32001 fails |
| ch5 | gp-0x6a46 | 0x28efe/0x28f02 | ≥32001 fails |
| gp-0x6a5e (voted avg torque) | gp-0x6a5e | 0x28f0e/0x28f12 | ≥32001 fails |

All 6 idioms use `val + 6400` compared unsigned against `38401` (= 32001+6400+1... exactly `0x9601`), i.e.
the effective test is `val ∈ [-6400, 32000]`, ceiling = 32000 (0x7D00). **These are railed-sensor FAULT
levels, not normal-driving levels** — memory `reference_accord_lkas_column_torque_cut_trigger.md` already
flagged real column torque as topping out ~3400.

## Three additional hard BAIL checks — 0x28f22–0x28f66 [V, run AFTER bVar1 is computed, independent of it]

Each, on failure, does `jr 0x000290b0` — a DIRECT jump that zeroes `r9,r22,r26,r28,r12,r25` and `gp-0x682f`
regardless of bVar1's value:

| Signal | gp offset | addr | condition to BAIL |
|---|---|---|---|
| gp-0x4f60 (CAN torque sensor B / column velocity) | gp-0x4f60 | 0x28f26–0x28f3c | `\|gp-0x4f60\| ≥ 25601` (idiom: `+25600` vs `51201`) |
| gp-0x6752 (assist polarity) | gp-0x6752 | 0x28f22–0x28f48 | byte not in `{-1,0,1}` (`(polarity+1) ≥ 3` unsigned) — NOT "polarity==0" |
| gp-0x6a56 (angle-rate-derived) | gp-0x6a56 | 0x28f4c–0x28f5a | `\|gp-0x6a56\| ≥ 12001` (idiom: `+12000` vs `24001`) |

Per `docs/handoffs/2026-06/HANDOFF-2026-06-29-gentle-eme-v32.md` §5, the CAN-packer formula makes `gp-0x4f60` ≈ the reported
`STEER_TORQUE_SENSOR` (×1.024) — real EME-event peaks were 1239–3475, far under 25601. `gp-0x6a56` maps
1:1 to `STEER_ANGLE_RATE` at CAN scale ×(-0.1) deg/s [inferred from the packer formula in the v32 handoff,
NOT independently re-derived this session] — a threshold of 12000 raw units would require ~1200 deg/s,
implausible even for a hard bump. **Verdict: LOW bump-sensitivity for all 3 gates** (same conclusion the
prior session reached for bVar1's ceiling checks).

## 0x290b0 (the shared BAIL target) [V]
```
mov 2,r1 / mov 0,r9 / mov 0,r22 / mov 0,r26 / st.b r0,-26671[gp](gp-0x682f=0) / mov 0,r28 / mov r0,r12 / mov 0,r25
```
`r1` (2 on bail, 1 if all gates passed — set at 0x28f74) is stored to `gp-0x3d2c` (`-15660[gp]`, 0x290d4).
`gp-0x3d2c` is read on ENTRY next cycle (0x28f66) to decide whether to carry forward the accumulator pair
`gp-0x3d34`/`gp-0x3d30` (prev state==1) or reset it to 0 (prev state==2). **This is PER-FRAME, with one
extra cycle of accumulator-reset penalty** — not a multi-cycle latch.

## Where bVar1 (r29) actually gets consumed [V]
1. `0x29118`: `cmp r0,r29 / be 0x29138` — inside a compound OR-gate (also includes a `gp-0x69aa`
   ceiling/floor test, `gp-0x67be==2` requirement, and a compound mode flag) feeding
   `FUN_00046ea6(9, r27)` at `0x2913e` — a fault-report/latch call, matches
   `reference_accord_arb_input_cluster.md`'s note that `FUN_00046ea6(9)==1` zeroes `gp-0x6758` via
   `FUN_0002a30e` (re-engage ramp manager) — i.e. bVar1==0 here affects the RE-ENGAGE RAMP, not the
   in-frame LKAS output directly.
2. `0x2976a` and `0x29810`: both combined with `gp-0x6809` (deliver flag, `ld.bu -26633[gp]`, confirmed
   read at these two sites — the CAN-signature-adjacent flag prior memory said had "no gp-relative store"
   IS read here) via `cmp r0,r29 / be`/`bne` — gates a ramp/integrator write to `gp-0x6b2c` (`-27436[gp]`,
   adjacent to the documented dead-sink family `gp-0x6b2e/32/34/36`). **Confirms**: `(gp-0x6809 != 1) OR
   (bVar1==0)` zeroes this intermediate, consistent with prior memory's "arb reads gp-0x6809, zeroes
   iVar28 when !=1" claim, but that memory's addresses were vague — this pins the exact 2 read sites.

## Verdict for the gentle-EME investigation
None of the 6 bVar1 ceiling checks nor the 3 hard-bail range checks look bump-triggerable — all thresholds
sit 7–10x above real driving/CAN magnitudes. This function is UNLIKELY to be the gentle-EME root cause.
The stronger candidate found this session is the `FUN_00040d58` second gate —
[[reference-accord-engage-sm-second-gate-gp6cc4]].

## Related
[[reference-accord-arb-input-cluster]] — prior full-inventory scan, less granular on this function
[[reference-accord-lkas-column-torque-cut-trigger]] — prior ruling-out of the 32000 ceiling as a lever
