---
name: reference_accord_factord_six_family_map_and_1khz_lane_v84
description: Full six-factor damper map (A seed/B/C/D/E/ceiling) with mode 24/25/26/27 stock vs V84 byte census, multiplication order/clamps, proof FactorD is unreachable below 35 km/h, and discovery of a SEPARATE live 1 kHz gp-0x6a10-indexed table outside the damper.
metadata:
  type: reference
---

[EVIDENCE unless marked otherwise, fresh `decompile_function` this session (2026-08-08, fw-factord),
cross-checked with Python LE byte reads of `stock_fw_dump/code.bin` and
`_v84_LEVERB.ARM5244-DAMPER.HONDA.M26.M27-PROBE.R24.6ADA-FD.67FE.6A10_plain_image.bin`
(sha256 `344f22f7...c637a`, verified).]

## The six factor families, `FUN_00034350` (damper evaluator, sole caller `FUN_00022ca0` = task idx4 =
## 100 Hz per [[reference_accord_task5_100hz_live_verified_full_producer_census]])

| letter | name | ptr array / cell | n | index | gate (else → unity 1024, EXCEPT E) |
|---|---|---|---|---|---|
| A | seed | `gp-0x698a` (no per-mode array; produced elsewhere, believed pinned ~1024) | — | — | clamped ≤1024 inline |
| B | FactorB | `0xC9CCC` | 4 | complex filtered/limited torque-like term | several overflow-rail checks + `gp-0x6752+1<3` |
| C | FactorC | `0xC9E9C` | 4 | `gp-0x6a5e` (voted speed, 64 ct/km/h) | `gp-0x6a5e>32000 \|\| gp-0x67f4!=1` |
| D | FactorD | `0xC9DB4` | 5 | `gp-0x6a10` | `gp-0x67fe∉{1,2} \|\| gp-0x6a10>=10001` |
| E | FactorE | `0xC9F84` | 4 | `gp-0x6ac0` (motor rate) | **zeroes the WHOLE PRODUCT**, not just E, if `gp-0x6ac0>=13001 \|\| gp-0x6abe>13000` (🛑 corrected from an earlier 12999/25936 arithmetic slip: `0x32C9=13001` decimal, `0x6590=26000`) |
| F | ceiling | `0xC77A0` (array of per-mode POINTERS, `(&PTR_DAT_000c77a0)[mode]`) | 2 | `gp-0x6ac2` | if `>=12999` uses scalar `tp+0x7158` instead of the table |

**Multiplication order, byte-exact from the fresh decompile (`0x344xx-0x346xx`):**
```c
seed = clamp(gp-0x698a, 0, 1024);                 // A
product = ((((seed*B)>>10) * C)>>10) * D)>>10) * E)>>10;   // pure multiply, zero add/or
if (gp-0x6ac0>=13001 || gp-0x6abe>13000) product = 0;  // E's gate kills the WHOLE product
if (gp-0x6abe > 0) product = -product;            // sign from rate, not the index
ceiling = LERP_or_scalar(gp-0x6ac2, table F);
gp-0x6bd0 = clamp(product, -ceiling, +ceiling);   // symmetric, lockstep-shadowed at gp-0x4cf2
```
**C is applied BEFORE D in the chain** ⇒ if C=0 at the operating point, D's value is irrelevant — the
zero propagates through the remaining `>>10` stages regardless of what D or E compute.

## Byte census, modes 24/25/26/27, STOCK vs V84 — IDENTICAL for all six families

Ran a Python script dereferencing each pointer array at `arr+mode*4`, record layout `[u16 n][n·i16 X]
[n·i16 Y][u16 term]`, X at base+2, Y at base+2+2n (+0x0C for FactorD's n=5, matching
[[reference_accord_factord_domain_resolved_angle_error_magnitude]]'s layout rule).

```
FactorB  X=[205,1331,2355,3072]  Y=[1024]*4        -- all 4 modes, STOCK==V84
FactorC  m24/26 X=[2240,3840,5120,8960] Y=[0,234,429,908]   -- STOCK==V84 (Y[0]=0 in BOTH modes)
         m25/27 same X, Y=[0,233,426,875]                   -- STOCK==V84
FactorD  X=[0,50,100,150,700] Y=[1024]*5           -- all 4 modes, STOCK==V84 (flat unity)
FactorE  X=[60,400,2500,4000] Y=[0,140,539,927]    -- all 4 modes, STOCK==V84 (no m26/m27 plateau)
ceiling  X=[300,800] Y=[512,1024]                  -- all 4 modes, STOCK==V84
```
**V84's build-script cal edits (`0xD77DA`/`0xD77EE` FactorC m26/m27 Y[0]→0, `0xD7822/24/2C` FactorE m27→
Honda) are CONFIRMED to have fully reverted the V74-V81 engaged-only Coulomb-relay damper.** V84's damper
chain has **zero mode-24-vs-26 asymmetry anywhere** — it is Honda's stock viscous surface, byte-for-byte,
in every one of the six families. The `N(50)/N(500)`=0.00× stabilising describing function from
[[accord-stock-mode24-equals-mode26-damper-is-ours]] (repo memory) applies unchanged to V84.

## 🛑🛑 FactorD is structurally UNREACHABLE below 35 km/h — on STOCK and on V84, in EVERY mode

FactorC's axis is voted speed at 64 ct/km/h; `X[0]=2240=35 km/h`; below that the LERP clamps (strict
compare) to `Y[0]`. **`Y[0]=0` in FactorC for modes 24, 25, 26 AND 27, on both stock and V84** (byte
census above). Since C is multiplied in BEFORE D in the chain and the chain is pure multiply with zero
additive rescue path, **C=0 forces the entire product to 0 regardless of D's value.**

Grind #1 (4-5 mph ≈ 6.4-8 km/h) and grind #2 ("creep cornering") both sit inside `[0, 35 km/h)`. ⇒
**A FactorD edit is a structural no-op for both of the brief's target symptoms, as currently wired.**
Raising FactorD's Y-values cannot matter until FactorC's `Y[0]` is also lifted off 0 — which reopens the
exact V80-class "does the surface stay viscous or become a relay" question this kit already paid for
once. **This is the deliverable for that part of the brief, not a caveat on it.**

## 🛑🛑 NEW FINDING: a SECOND, physically separate, LIVE `gp-0x6a10`-indexed table exists, in a 1 kHz lane

`FUN_0003b8f6` — **sole caller `FUN_0002214a`**, the confirmed 1000 Hz control task (task idx 0, per
[[control-task-tick-confirmed-1khz]] / [[accord-task5-is-100hz-damper-cannot-damp-21hz]] repo memories;
NOT the 100 Hz `FUN_00022ca0` task FactorD's own table lives in) — reads `gp-0x6a10` directly (raw cell,
not FactorD's pointer array) and LERPs it against a table at:
```
X: tp+0x7b66 .. tp+0x7b7e  (0xC6B66 .. 0xC6B7E, step 2, NO count header, 13 points, bare array)
Y: tp+0x7b80 .. tp+0x7b98  (0xC6B80 .. 0xC6B98)
gate: gp-0x6a10 < 10001, else unity 1024 (same overflow rail as FactorD's own gate)
```
**Byte-read, stock == V84, never touched by any build:**
```
X = [0,340,640,850,1000,1200,1400,1576,1736,1916,2084,2280,4776]   (0.1deg/ct -> 0-228 deg, X[12]=477.6deg overflow rail)
Y = [899,908,981,1060,1083,1084,1084,1084,1084,1084,1084,1084,1084]   (Q10; 0.878 -> 1.059, plateaus by X=120deg)
```
**This is a real, LIVE, non-flat shaping curve — the opposite of FactorD.** It scales a clamped
(±15, floating point) correction term inside `FUN_0003b8f6`, which is itself a heavy float-IIR chain
blending `gp-0x6b98` (the final FOC motor command, per repo memory) and `gp-0x4f60` (torque sensor) —
structurally resembling a plant-model / motor-command-vs-torque-sensor correction, i.e. adjacent to the
operator's own "self-interference cancellation" hypothesis
([[docs/research/FEASIBILITY-SELF-INTERFERENCE-CANCELLATION.md]] repo doc, not re-read in full this session).
Its outer gate has **NO speed term** (`gp-0x6b98` range check, `gp-0x4f60` range check, `gp-0x6abc` rate
check, a 2-channel index check) ⇒ **unlike FactorD, this lane is NOT zeroed at creep speed.**

**Output trace — 🛑 CORRECTED, a sibling session (`fw-plantmodel`, same V85 orchestration, memory
[[reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps]]) fully decoded this function
byte-by-byte and supersedes my own partial read.** Their reconciliation of the SAME table this file
found (identical X/Y byte-read, independently reproduced):
- **`gp-0x6a10`'s LERP output scales `fVar13` (their "sens branch" term, into `fVar18`), and `fVar18` is
  the base of BOTH `gp-0x6bf6` (an early snapshot) AND — after `fVar18 − (FRICTION+INERTIA)` — of
  `gp-0x6bfc`, this function's MAIN, LIVE output.**
- `gp-0x6bfc` → `FUN_0003bc20` → `gp-0x6bfe` → `FUN_00038148` stage 2 → `gp-0x6b70` →
  `FUN_00037fe6` → `gp-0x6ad6` → PID `FUN_0003a382` → aggregator → governor → **`gp-0x6b98`, closing the
  loop** ("Path 2", per [[reference_accord_path2_is_a_real_closed_loop_via_gp6b98_and_0xc63a0_sizing]]).
  ⇒ **the `gp-0x6a10`-indexed table's contribution DOES reach the motor command through a real, live,
  1 kHz closed loop — it is NOT a dead/isolated lane.**
- `gp-0x6bf6`, `gp-0x6ae0` (INERTIA×1024), `gp-0x6ae2` (FRICTION×1024), `gp-0x6c00`, and `gp-0x695c`
  (bonus find) are **CONFIRMED FREE TAPS — 0 readers each**, by the sibling's validated
  disp16+ext23 scanner AND an independent LE32-literal pointer-table check (two methods, not just
  `search_instructions`). These are diagnostic/intermediate snapshots, distinct from the live path above.
- **Their own open item #2 asked whether this table is FactorD.** Answer, from this file: **NO.**
  FactorD = `0xC9DB4`, mode-selected (34-entry pointer array), n=5, breakpoints in RAW COUNTS
  `[0,50,100,150,700]`, flat `Y=1024×5` on both stock and V84. This table = `0xC6B66`/`0xC6B80`, a single
  FIXED (non-mode-indexed) 13-point array, breakpoints `[0,340,...,2280,4776]` counts, **live shaping**
  `Y=[899...1084]`. They share only the index variable `gp-0x6a10` and the same `0x2711` overflow gate
  literal — physically and functionally separate cal objects, on separate tasks (100 Hz vs 1 kHz).

**Why this matters:** it is angle-scheduled (same `gp-0x6a10` axis, itself ≈|raw column angle| under
ordinary hands-on driving per [[reference_accord_factord_domain_resolved_angle_error_magnitude]]), it is
LIVE (not flat), it runs at 1 kHz (no 100 Hz ZOH anti-damping ceiling above 25 Hz), it is NOT gated off
at creep speed, AND (per the sibling trace above) **it demonstrably reaches the motor command through
Path 2's live closed loop.** **This is a structurally more promising angle-scheduled candidate than
FactorD for grind #1/#2** — FactorD is proven dead below 35 km/h (this file, above); this table is not
speed-gated at all. 🛑 But per the sibling's §10, any edit to this loop is a **LOOP-GAIN edit, not an
isolated feedforward tweak** — GATE 2 (magnitude AND phase across the whole Path-2 loop) applies, and
their §6 transfer-function work (INERTIA corner ≈9.9 Hz, real part vs rate positive across 7.79-28.5 Hz)
should be read in full before anyone prices an edit to `0xC6B66`/`0xC6B80`, `0xC646E`, `0xC4080`, or
`0xC40D6`. Not priced this session — a genuine next-session candidate, not a proposal.

## Reader/writer census of `gp-0x6a10` — matches V84's own build-script figure exactly (3 writers / 14 readers)

`search_instructions operand_pattern="6a10"` returned 18 raw hits, 183,641 instructions scanned,
`truncated:false`. One is a false positive (`br 0x00066a10` in `FUN_000669d6` — a branch target that
numerically matches, not a gp-relative access). Adjudicated 17 real hits = **3 writers + 14 readers**,
independently reproducing `builds/v80_v107/build_v84_tva.py`'s own recorded census (`0xC9DB4`/`gp-0x6a10` "3 writers /
14 readers, every reader `ld.hu`").

**Writers (3), all lockstep-shadow-paired with `gp-0x4c90` per [[accord-lockstep-shadows-67fe-4c3a-and-6a10-4c90]]:**
- `0x3FCA4` `FUN_0003fc16` — the real `abs(angle−ref)` write (FactorD's producer).
- `0x3FD3E` `FUN_0003fc16` — the gate-off branch, zero write.
- `0x3E852` `FUN_0003e760` — a whole-state-block RESET routine (also zeros `gp-0x69ca`, `gp-0x69d4`,
  `gp-0x69de`, `gp-0x6bf0`, `gp-0x6bf4`, `gp-0x6a02`, `gp-0x67fe`, etc.) — decompiled fresh, confirmed
  the shadow write IS present (paired correctly), so this is NOT a lockstep-desync risk, just a
  disengage/reinit hook. Not yet determined what triggers this routine.

**Readers (14), by function — most NOT decompiled this session, named for blast-radius completeness:**
`FUN_0002c478`(0x2C4D8) · `FUN_00034350`(0x34582, FactorD table — traced) ·
`FUN_00034a72`(0x34C20, **boost** — NEW finding, boost is angle-scheduled too, not traced further this
session but corroborates [[reference_accord_near_centre_structure_hunt_angle_tracking_chain_found]]'s
`gp-0x6394`-family LERP2 boost path, which was scoped to the WRONG mode 10 pre-TVCA4-correction — a
mode-24/26 re-derivation of that RAM-table chain is an open item) · `FUN_00036828`(0x3687E) ·
`FUN_000371e0`(0x371E8) · `FUN_000389ec`(0x38A70 and 0x394DA, two sites) ·
`FUN_0003b8f6`(0x3BA12, the 1kHz table — traced) · `FUN_0003e760`(0x3E846, internal to the reset routine)
· `FUN_0003fc16`(0x3FC98, 0x3FD32, internal shadow-check reads) ·
`FUN_00041eec`(0x41FFE, **the `gp-0x67f4` 5-channel speed-voter producer** — gp-0x6a10 is ALSO one of the
voter's plausibility inputs, previously undocumented) ·
`FUN_000456a4`(0x45716, the common-mode rate/comp-add function, `gp-0x6abe`/`gp-0x6ac0`) ·
`FUN_00045a20`(0x45A24, **the hard-shutdown MONITOR** — gp-0x6a10 feeds a safety monitor; not yet
determined how — GATE 1/2 relevant if `gp-0x6a10`'s PRODUCER (not just FactorD's table) is ever edited).

**Blast-radius rule, confirmed:** editing FactorD's TABLE (`0xC9DB4` Y-values only) is fault-isolated to
`FUN_00034350` — none of the other 13 readers dereference that pointer array, they all read the raw
`gp-0x6a10` cell directly. Editing the PRODUCER (`FUN_0003fc16`, e.g. `tp+0x733a`'s 13° clamp or the
gate logic) would ripple into all 14, including the hard-shutdown monitor and the speed voter — a much
larger GATE 1/2 surface, not evaluated this session.

## Lineage — confirmed genuinely untested, not falsified

`grep` of all `build_v*_tva.py`: `0xC9DB4`/`FACTOR_D_PTRS` appears only in `rec_any()` read calls (used to
LOG the current D-value) and `for ptrs,name in (...)` assert-untouched print loops. **Never a write
target.** `0xC6B66`/`0xC6B80` (the 1 kHz table) appears in **zero** build scripts — completely unexamined
territory before this session.

## Related
[[reference_accord_factord_domain_resolved_angle_error_magnitude]] — the corrected identity of `gp-0x6a10`
itself (amended same session).
[[reference_accord_near_centre_structure_hunt_angle_tracking_chain_found]] — prior boost/`gp-0x6394`
creep-band trace, scoped to mode 10 (now known wrong per RULE 7); the `FUN_00034a72` connection this
file re-finds independently is the same one, needs a mode-24/26 re-derivation.
[[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]] — prior full disasm of the
same function, consistent with this session's fresh decompile.

## Open items / next verification
1. ~~Trace FUN_0003b8f6's outputs~~ — **DONE by the sibling `fw-plantmodel` session**, see the
   reconciliation above. Remaining: price an actual FactorD-alternative edit against Path 2's loop gain
   (their §10) — genuinely not attempted by either session yet.
2. Decompile `FUN_00034a72`'s use of `gp-0x6a10` (boost) against the CORRECT mode 24/25/26/27 pointer
   arrays — the existing near-centre-hunt memory did this for mode 10, which this car does not use.
3. Decompile `FUN_00041eec`'s use of `gp-0x6a10` as a speed-voter input — semantics unknown.
4. Decompile `FUN_00045a20`'s use of `gp-0x6a10` in the hard-shutdown monitor — safety-relevant if any
   producer-side edit is ever considered.
5. `gp-0x4e5f`, the hands-off dwell counter, and `gp-0x6a60` inside `FUN_0003f884` were read but not
   independently confirmed against other memory — the "collapses to |angle| under hands-on driving"
   explanation is [BELIEF, mechanistically supported by the reset-path structure], not a live measurement
   of those specific cells during route 6d.
