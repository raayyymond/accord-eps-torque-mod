---
name: reference_accord_gp6b70_probe_spec_path_separation_and_gate1
description: Probe spec for closing Q5 (sign of raising 0xC63A2/gp-0x6bbe's Path-2 weight) empirically -- gp-0x6b70 is exclusively a Path-2 product (GATE-1 closed, 1 writer/1 reader, no Path-1 role), so pairing it with the already-flowing gp-0x6bbe telemetry isolates the weight's marginal effect from Path-1's independent contribution. Proposes time-sharing the existing 427/0x1AB field rather than opening a new hook or touching 0x14A's saturated bits.
metadata:
  type: reference
---

# `gp-0x6b70` probe spec — isolates `0xC63A2`'s marginal effect from Path 1 (2026-08-11, `lane-weights-6bf`)

Team-lead's ask: design (not build) a probe to close Q5 (sign of raising `0xC63A2`, the boost lane's Path-2
weight) empirically, after 3 static-analysis sessions failed to close it via decompilation. Builds on
[[reference_accord_fun38148_six_weight_v95_candidate_census]] and
[[reference_accord_task5_rate_resolved_100hz_and_fun389ec_structure]].

## [EVIDENCE, fresh `search_instructions`] `gp-0x6b70` is EXCLUSIVELY a Path-2 signal — GATE-1 clean

`search_instructions(operand_pattern="6b70")`: 21 raw hits, **19 are `jarl 0x0006b700,lp`** (calls to an
unrelated function at absolute address `0x6b700` — a text-collision false positive, same class documented
elsewhere in this kit). **The 2 real hits**: sole write `st.h r11,-0x6b70,gp` @`0x382d2` in `FUN_00038148`
(Path 2's own output store), sole read `ld.h -0x6b70,gp,r13` @`0x38006` in `FUN_00037fe6` (Path 2's term
into `gp-0x6ad6`). **`FUN_0003aa2c` (Path 1, the direct aggregator) never references `gp-0x6b70` anywhere**
— confirmed via this session's own fresh decompile of `FUN_0003aa2c` (see
[[reference_accord_gp67ac_resolved_zero_and_path1_always_live]]).

⇒ **Any `gp-0x6bbe→gp-0x6b70` transfer measured on-car is, by construction, the Path-2-only segment** —
exactly and only the part `0xC63A2` controls. This is what separates the "gp-0x6bbe is dual-path"
complication team-lead flagged: Path 1's contribution to the wheel is entirely independent of `0xC63A2`,
so the pairing isolates the weight's marginal effect without needing a differential build.

**GATE-1**: 1 writer / 1 reader, zero blast radius, same class as every prior rung in this cave lineage.
Materially safer than `gp-0x1500`'s GATE-1 failure — that was a NEW RAM claim; `gp-0x6b70` is an existing,
already-populated Honda cell, read-only for telemetry purposes. **Not independently re-verified**: a raw
absolute-address scan for a `movea 0xFEDF1490,...`-style register-indirect write bypassing the `gp,rN`
operand text (the standing tool-policy concern) — flagged as the one remaining rigor item before a builder
cuts bytes, not done this session (function is small/self-contained and was decompiled in full, so risk
rated low, not zero).

## Since `0xC63A2` = 1024 (stock, frozen since V84), the CURRENT operating-point transfer is measurable NOW

No differential build needed to learn the LOCAL sign of raising the weight — the pairing on ANY flight
(including data already flying) gives the exact `d(gp-0x6b70)/d(gp-0x6bbe)` transfer at the current
operating point. Caveat: this bounds confidence to a MODEST nudge off 1024, not a large jump — `0xC63A0`'s
own precedent (inversion boundary between 1024 and 2048, per
[[reference_accord_path2_is_a_real_closed_loop_via_gp6b98_and_0xc63a0_sizing]]) is exactly the failure mode
a large jump risks. Since `0xC63A2` is fully virgin (unlike `0xC63A0`), this argues for sizing any V95 edit
conservatively, not for distrusting the probe.

## What the pairing does NOT need to also measure — the downstream chain is already structurally known

`gp-0x6b70→gp-0x6ad6`: unity weight (`0xC64B0=1`, established). PID (`gp-0x6ad6→gp-0x6ad4`): Stage A/B/C
already traced, proportional-dominated 8-10:1, small net phase lag — **but that figure was computed at
21Hz in the source memory, needs re-running at 6-9Hz before trusting it for this question** (cheap
arithmetic on an already-known transfer shape, not a new trace). Aggregator (`gp-0x6ad4→gp-0x6b98`): plain
ADD, unity, established. The plant (`gp-0x6b98`→wheel) is firmware-unknowable but doesn't need a new
telemetry node — the kit's existing Re(Z) methodology already closes this via `0x18F`'s real rate field,
which needs zero new bits (raw-decodable from any rlog per the standing scoring rule).

## Probe placement — proposed: time-share the existing 427/`0x1AB` field, not a new hook

`0x14A`'s 7 bits are fully saturated by V92's return-centre/dwell-relay payload (see
[[reference_accord_v92_final_allocation_gp6abc_gp6bf0_adjudication]]) — no free capacity there without a
cross-investigation trade. `0x1AB`/427 currently carries only `\|gp-0x6bbe\|` at 50Hz but has **3 already-
free bits** (`byte0[6:5]`+`byte2[7]`, per `docs/SPEC-2026-08-11-telemetry-budget.md` T1 census).
**Recommended**: alternate 427's payload between `gp-0x6bbe` and `gp-0x6b70` on alternating frames (parity
bit from one of the 3 free `0x1AB` bits) — full analogue resolution for BOTH signals at 25Hz each (still
>2.7x the 6-9Hz Nyquist margin), zero new hook, zero touch to `0x14A`. Fallback if judged too much packer
complexity: spend the 3 free `0x1AB` bits directly on `gp-0x6b70` as 1 sign + 2-bit **log**-magnitude
bucket (not linear — explicit avoidance of the `gp-0x6b98` probe's under-ranging mistake, since `gp-0x6b70`
has never been telemetered and no real percentiles exist to size a linear scale against).

## Free corroboration for task5=100Hz, rides on existing `gp-0x6bbe` telemetry

Outer torque EMA alpha=205/1024=0.2002 (established) gives τ≈5ms @1kHz vs τ≈50ms @100Hz — an order of
magnitude apart, resolvable from a driver torque step/impulse in any drive using `gp-0x6bbe`'s ALREADY-
FLOWING 427/`b7` telemetry. No new bits needed; a second independent route on the 100Hz finding, matching
task 1's existing two-route confidence.

## Related
[[reference_accord_fun38148_six_weight_v95_candidate_census]] · [[reference_accord_task5_rate_resolved_100hz_and_fun389ec_structure]] · [[reference_accord_gp67ac_resolved_zero_and_path1_always_live]] — the three prior files this session's probe spec builds on.
