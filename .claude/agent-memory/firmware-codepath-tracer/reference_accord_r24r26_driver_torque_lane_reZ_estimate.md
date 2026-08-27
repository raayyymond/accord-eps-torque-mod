---
name: reference_accord_r24r26_driver_torque_lane_reZ_estimate
description: The genuinely DRIVER-SIDE (torque-sensor-derived, not motor-rate-derived) candidate for the operator's inertia-feedback hypothesis. r24/r26 (FUN_0003aa2c, feeding gp-0x6b94 directly, cals byte-identical stock/V101/V102, gate provably DEAD on all three -- confirmed 0x3AA96=0xC5 byte-read) = a 4-tap driver-torque difference (gp-0x4f62) x a rate-scheduled gain, clamped +-0x2000 EACH (8x gp-0x6b26's +-0x400 window at the same summing node). First Re(Z)-at-6-9Hz ESTIMATE for this lane (piggybacking the measured whole-car Z as the driver-torque/wheel-rate transfer, since r24/r26's input IS that same torque signal): comes out POSITIVE/dissipative (+431 to +1294 ct depending on gain), i.e. SAME sign class as gp-0x6b26, NOT the pump -- but this is BELIEF-tier and hinges entirely on one unresolved sign bit, gp-0x6752 (polarity), assumed +1. If gp-0x6752 is actually -1 on this car, r24/r26 flips to the kit's best pump candidate found so far.
metadata:
  type: reference
---

# r24/r26 -- the actual driver-side candidate, and its Re(Z) estimate [2026-08-20, `ratchet-inertia` cont'd]

Orchestrator correction accepted: `gp-0x6b26`'s input (`gp-0x6c2c`) is MOTOR/resolver rate, not driver
torque -- refuting it does not test the operator's literal "steering wheel" hypothesis. This file covers
the genuinely torque-sensor-derived candidate the record already names but had not phase-checked:
`r24`/`r26` (`gp-0x6ada`/`gp-0x6adc`), traced in `FUN_0003aa2c`.

## What it is, reconciled from 4 existing memories + one fresh byte-read this session

Shared input: `gp-0x4f62` = 0.5*(T[n]-T[n-N]), N=cal(0xC6C42)=4, a 4-sample backward difference of the
**raw torque sensor** `gp-0x4f60` (producer `FUN_0007e74a`) -- clamped once to +-5120 into `r1`
(`0x3aa9c-0x3aac0`). **This IS a genuine driver-side signal**, unlike `gp-0x6c2c`.
```
r24 = clamp( ((r1 * gain_cal) >> 10) * polarity(gp-0x6752), +-0x2000 )   # ONE >>10, FUN_0003aa2c 0x3ac16-58
r26 = clamp( ((r1 * a_smoothed) >> 10) * gain_cal2 >> 10, +-0x2000 )     # TWO >>10, 0x3ab6c-76
      a_smoothed = 2-tap boxcar of gp-0x69a4 ("a"), |H|>0.9997 at 7.79Hz -- functionally irrelevant
```
`gain_cal`/`gain_cal2` selected by a 4-way mux: `gp-0x671d!=0 -> 0xC6442` | `[gate]!=0 -> 0xC6446(r24)/
0xC6444(r26)` | `r2==0 -> 0xC6440(r24)/0xC643E(r26)` | else -> mode-indexed "curve-A" LERP (peaks
**3.000x at creep**, per `[[reference_accord_micro_regime_has_no_scheduled_dissipation]]`'s census).
Both feed `FUN_0003aa2c`'s sum -> `gp-0x6b94` **directly, at +-0x2000 (8192) EACH** -- 8x `gp-0x6b26`'s
+-0x400 window at the SAME summing node (`[[reference_accord_fun3aa2c_is_gp6b94_writer_and_r24arm_gate]]`).

**Fresh byte-read this session, stock vs `_v101_..._plain_image.bin` vs `_v102_..._plain_image.bin`**:
`0xC6440`=2048, `0xC6442`=1024, `0xC6446`=512, `0xC643E`=1536, `0xC6444`=512, `0xC61F6`=3, `0xC6C42`=4 --
**byte-identical on all three.** `bytes@0x3AA94..99` = `84 7f c5 97 e2 57` on all three -- the gate
byte at `0x3AA96` reads **`c5` = DEAD** (matches stock/V62/V65 per `docs/STATE.md`'s rate-lane table;
NOT the `0xFB` armed state V67/68/71c/V100 carried). **"Lever B stays removed" means the gate is dead,
not that r24/r26 are zero** -- they are structurally UNGATEABLE-TO-ZERO (the mux always resolves to
SOME positive cal), only the *which cal* question is affected by the gate.

⚠ Deadband `D=cal(0xC61F6)=3` confirmed negligible (0.4-2.4% of typical |dtorque| excursion per
`[[reference_accord_fun3aa2c_r24_r26_pole_census_no_filter_exists]]`) -- small-signal-linear assumption
OK for this nonlinearity specifically.

## Re(Z) estimate at 6-9Hz [BELIEF -- new methodology this session, not an on-car measurement]

Because r24/r26's input **is** the same physical torque signal `T_driver` that the whole-car
`Z_measured(f) = S_Tw/S_ww` already characterizes (`rlog-tools/_scratch/logs/v92_rez.log`, route 77), a linear filter
of that SAME signal has a computable cross-spectral relationship to wheel rate `w` without needing to
re-derive the plant: `Z_r24(f) = G * H_diff(f) * Z_measured(f)`, where `H_diff` is the 4-tap
differencer's own transfer function and `G` is the real, positive small-signal gain (`gain_cal/1024`,
sourced from the census's "3.000x at creep" ceiling, ranged 1-3 to also cover the flat fallback cals).
**This does NOT hold for a term (like `gp-0x6b26` or the whole of `gp-0x6b94`) whose input is NOT
`T_driver` itself** -- flagged explicitly so this method is not mis-applied elsewhere.

```
f=7.79Hz (6-9Hz band): |H_diff|=0.0977 @ +84.39 deg (verified: phase=90-180*N*f/fs, N=4)
Z_measured(6-9Hz) = 5840.8 @ -125.3 deg  (_scratch/logs/v92_rez.log, route 77, coh2=0.769, TRUST=YES)
total phase = 84.39 + (-125.3) = -40.9 deg  =>  cos = +0.756  =>  POSITIVE (damped, kit-standard convention)
Re(Z_r24) at G=1/2/3: +431 / +863 / +1294 ct
```
Repeated across all 8 measured bands (2-4 through 26-31Hz): **POSITIVE at 2-4/4-6/6-9/9-12Hz, flips
NEGATIVE at 12-16Hz onward** (the differencer's own phase keeps climbing toward the full +90 deg lead,
eventually overshooting `Z_measured`'s own phase enough to cross into the anti-damped quadrant at higher
frequency) -- i.e. **this estimate predicts r24 is dissipative exactly where `Z_measured` is worst
(9-12Hz) and BECOMES anti-damping in a band (12-31Hz) that is comparatively less of the operator's
complaint.** Structurally the OPPOSITE of what would be needed to explain the 6-9Hz pump.

## 🛑 The one assumption that decides everything: `gp-0x6752`

`r24`'s own polarity multiply (`0x3ac3e mul r14,r6,r0`) uses `gp-0x6752`, a **+-1 selector** set at boot
from a config-record byte (`0x2C -> +1`, `0xFA/other -> -1`), per
`[[reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps]]` §3/correction. **Whether
this car's config record selects +1 or -1 was flagged OPEN there and is STILL OPEN** -- it is boot-time
RAM state, not a flash cal cell, so it cannot be read from `_v101_..._plain_image.bin`/`_v102_...bin`
the way every other number in this file was. **If it is -1, every sign above flips**: r24 becomes
strongly ANTI-damping at 6-9Hz (-431 to -1294 ct) and 9-12Hz, and DAMPING at 12-31Hz -- i.e. it would
become the single best pump candidate this whole investigation has found, AND it would retrodict the
measured 12-16Hz-to-26-31Hz sign structure moving toward damped, which the data shows.
🛑 **This is the highest-leverage single fact anyone could resolve next** -- either read it live off a
running ECU (a UDS/telemetry read of RAM address matching `gp-0x6752`'s runtime location), or find and
decode the static config-record table in flash that the three producer functions
(`FUN_000490ac`/`FUN_00048a40`/`FUN_000497e6`) consume, and read this car's own variant byte.
`gp-0x6752` also gates `FUN_0003b8f6`'s model/inertia/friction polarity (Path 2) -- so this single bit
has a WIDER blast radius than just r24.

⚠ `r26` was NOT run through this same estimate this session (its own polarity handling was not visible
in the disassembly excerpt already on record; time-boxed out). Whatever `r24`'s true sign is, `r26`
shares its input and very plausibly its sign -- would ADD to whichever direction `r24` resolves to,
not cancel it, unless its own polarity handling differs (unconfirmed).

## Verdict, honestly staged
**STRUCTURAL MATCH**: far better than `gp-0x6b26` for "driver-side" -- genuinely torque-derived, live
unconditionally (mux never zeroes it), maximal at creep (matches the operator's regime), 8x the
aggregator headroom of `gp-0x6b26` at the same summing node, and independent of `0xC6CD0` (consistent
with the "6x != 4x on ratchet" dissociation).
**SIGN**: UNRESOLVED, not refuted, not confirmed -- my best-effort closed-form estimate (assuming
`gp-0x6752`=+1, the field's more commonly-assumed value per prior sessions) says dissipative/damping at
6-9Hz, same conclusion class as `gp-0x6b26`. **But this rests on one unverified boot-time RAM bit that
would reverse the entire conclusion if wrong.** Do not treat either sign as settled.

## Related
[[reference_accord_driver_side_inertia_hypothesis_refuted_synthesis]] -- the `gp-0x6b26` (motor-side)
half of this investigation, which this file extends to the driver-side candidate.
[[reference_accord_fun3aa2c_is_gp6b94_writer_and_r24arm_gate]] -- the aggregator/gate-condition source.
[[reference_accord_fun3aa2c_r24_r26_pole_census_no_filter_exists]] -- the pole/phase/deadband source.
[[accord-rate-lane-builds-were-never-single-variable]] (memory/, kebab-case) -- r24 vs r26 gain-selector
disassembly this file's `G` range is anchored to.
[[reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps]] -- source of the `gp-0x6752`
open question and its Path-2 blast radius.
`rlog-tools/_scratch/logs/v92_rez.log` -- the measured `Z` this file's estimate is built on.

---

# 🛑🛑 UPDATE 2026-08-20 (same day) — gp-0x6752 RESOLVED = -1. Sign FLIPS. r24/r26 is now the kit's best pump candidate.

**Independently re-verified myself, not just relayed from `pump-hunt`** — fresh `decompile_function(0x48a40)`
+ a raw Python hex dump of `stock_fw_dump/code.bin` at `0x1000-0x1600` this session, before reading
`pump-hunt`'s claim in detail. Found, myself: type-0x54 record (checksum/len=0x10/type=0x54) at **0x1180**,
selector byte (offset+4) = **0x2C** (→+1); a SECOND type-0x54 record at **0x14C0**, selector = **0xFA**
(→-1, confirmed in the decompile: `*(undefined1*)(gp-0x6752)=0xFF` on the `-6`==`(char)0xFA` branch).
Flash goes to `0xFF`-erased immediately after the 0x14C0 record (checked through 0x1600) — **no third
type-0x54 record exists**, and the parser walks the table strictly sequentially (`next = current +
length_byte`), so **0x14C0 (selector 0xFA, writes -1) is the LAST write and it is what sticks.**
This matches `pump-hunt`'s claim exactly, via an independent method (I did not read their memory file
before doing this trace). **Second, independent line of evidence**: `cave-engineer` relayed that V98's
on-car comparator `b3 = (gp-0x6752 ≥ 0)` measured **duty 0.0000 across 5 routes** (`docs/STATE.md`'s
V99 flight-score section, text I had already read and quoted myself earlier this session) — i.e.
gp-0x6752 reads negative on the real, running ECU too. **Two independent methods (static config-table
trace, on-car runtime measurement) agree: gp-0x6752 = -1.**

**Parity, also independently confirmed this session** (fresh full `decompile_function(0x3aa2c)`):
**BOTH r24 and r26 multiply by `gp-0x6752` EXACTLY ONCE** (`iVar17 = iVar17 * *(char*)(gp-0x6752)` for
r24's `gp-0x6ada` store; the analogous single multiply for r26's `gp-0x6adc` store, confirmed in the
same decompile) — ODD parity for both, so (per team-lead's own parity framing) the sign is load-bearing
for both lanes, not something that cancels.

## Corrected estimate
Every number in this file's Re(Z) table above FLIPS SIGN. At 6-9Hz: **r24 = -431 to -1294 ct (PUMPING)**
at G=1-3, same direction as the measured -3073..-4890 pump — the opposite of my original (wrong-polarity)
conclusion. **Retrodiction bonus**: the corrected model now predicts PUMP at 6-9Hz AND 9-12Hz (matching
the measured two worst bands) and DAMP at 12-31Hz (matching the measured high-band recovery), a
materially better shape-match than the +1 case had.

`gp-0x6b26` (`FUN_00036c12`) is CONFIRMED UNAFFECTED — `search_instructions operand_pattern="-0x6752"`
(55 hits, full program) contains no hit inside `0x36c12`'s body; its producer never reads `gp-0x6752`.
Its own on-car-measured +518/+565ct dissipative finding stands unchanged.

`FUN_0003a382` (the PID) is ALSO affected — confirmed in my own fresh decompile: the ENTIRE `P+I+D`
combine is multiplied by `(char)gp-0x6752` ONCE, immediately before the final clamp into `gp-0x6ad4`
(`iVar30 = (...) * (int)*(char*)(gp-0x6752) * (validity gate)`), not per-term. See
`[[reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal]]` (pump-hunt's file) and
`[[reference_accord_dterm_grindband_unresolved_and_pid_net_damping]]` (corrected in place) for the P/I/D
consequence — net P+I+D now reads +0.122 PUMPING (normalized GATE2 units, real-ct conversion still
unresolved) at 6-9Hz, same direction as r24/r26.

## Remaining open items, stated plainly
1. **r26's exact magnitude, still not computed** — it shares r24's now-resolved sign (same single
   `gp-0x6752` multiply, same input `r1`), so it ADDS to the pump rather than opposing it, but its own
   gain includes an extra `>>10` and the `gp-0x69a4`("a")-dependent boxcar-averaged term whose typical
   value is not established — could be smaller OR larger than r24's contribution depending on "a"'s scale.
2. **G (the r24 gain, 1-3x range) is not pinned to a single value** — still needs the exact `curve-A`
   LERP value at the operating point, not just its "3.000x ceiling" from the census.
3. **The PID's real-ct magnitude is unconverted** — GATE2's numbers are internally-comparable but not
   tied to an established ct scale.
4. Even summing r24's high end (-1294) + a plausible r26 addition + some PID contribution, this does
   NOT obviously reach the full -3073..-4890 without further work — **it is now a REAL, correctly-signed,
   material FRACTION of the pump, not the whole confirmed budget.** Do not overclaim closure.

⇒ **This changes the lever ranking materially.** `r24`/`r26` is no longer excludable by sign — it is now
the single best-evidenced additive-term candidate for (part of) the 6-9Hz pump found in this entire
investigation. A compensator here is a legitimate target for the operator's authorized large-cave build,
subject to GATE 2 (full loop, not isolated-stage) and GATE 1 (RAM ownership) — neither done yet.
