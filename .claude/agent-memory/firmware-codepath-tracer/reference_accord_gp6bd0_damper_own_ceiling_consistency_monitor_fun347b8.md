---
name: reference_accord_gp6bd0_damper_own_ceiling_consistency_monitor_fun347b8
description: FULL reader/writer census for gp-0x6bd0 (8 accesses, triple-confirmed) plus a NEW, previously-undocumented monitor -- FUN_000347b8 -- which independently re-derives the damper's ceiling in FLOAT (from a fixed, non-mode-indexed twin table at tp+0x7554=0xC6554, byte-identical to mode26's INTEGER ceiling 0xC77A0, X=[300,800] Y=[512,1024]) and hard-faults (DTC 0xF00049, fault index 0x1d) if gp-0x6bd0 disagrees with that independently-resampled ceiling by more than +-5 raw counts. The generic per-DTC debounce layer (FUN_00018738) has THRESHOLD=1 for fault indices 0x1c/0x1d -- a SINGLE bad 100Hz sample latches the hard shutdown, not a multi-cycle accumulator. V75's own build script confirms its dose is calibrated to touch this exact 512 ceiling floor by construction.
metadata:
  type: reference
---

> ## ⚠⚠ CORRECTED SAME SESSION, IMMEDIATELY AFTER FIRST WRITE — §4's sizing was WRONG, and it inverts
> the original verdict. Coordinator rebuilt mode-26's actual arrays from raw bytes (independently
> re-confirmed here via the pointer tables `0xC9E9C[26]=0xD77D0` and `0xC9F84[26]=0xD780C`, then the
> table contents themselves, on BOTH `code.bin` and `_v75_c566_ex1200_magprobe_plain_image.bin` — exact
> match to the coordinator's numbers, byte for byte):
> ```
> FactorC m26: X=[2240,3840,5120,8960]  Y: stock=[0,234,429,908]  V75=[566,234,429,908]
> FactorE m26: X: stock=[60,400,2500,4000]  V75=[12,200,2500,4000]   Y: stock=[0,140,539,927]  V75=[0,539,539,927]
> ```
> Recomputing `dose=(FactorC×FactorE)>>10` at creep (speed<2240) from these exact bytes: **V75 tops out
> at 297 counts for EVERY rate from 200 to at least 1555 (route 5d's observed max, 330°/s)** — FactorE
> plateaus at `Y1=Y2=539` across that whole span, so raising `C_Y0` alone (429→566, V74→V75) is what
> drives the visible 2.74x at low rate, but it does NOT push the creep-band peak anywhere near the
> 512-count ceiling FLOOR. **512 is reached ONLY at rate=4000 (849°/s) — `(566*927)>>10=512` EXACTLY,
> by construction (`build_v75_tva.py`'s own binary search: "the largest C_Y0 for which that corner
> lands at or below 512") — a rate never observed on this car.**
>
> **Two follow-up checks, both against the original §4 hypothesis:**
> 1. **Clamp vs extrapolate, pinned by fresh disasm of BOTH implementations** — `FUN_000347b8`
>    (`0x34818 bne`/fallthrough `0x3481a`, and `0x3482c be`/`0x3483e`) and `FUN_00034350`'s own integer
>    LERP (`if(X[0]<v){...}else{Y[0]}`, `if(v<X[1]){interp}else{Y[1]}`) **BOTH flat-clamp below X[0] and
>    above X[last]** — no extrapolation exists anywhere, on either side, in either domain. The
>    coordinator's hypothesized "extrapolates to 0.2/205-count effective ceiling" is **refuted**: the
>    below-X0 (`gp-0x6ac2≈0`, the overwhelming majority of driving) case reads flat `Y0=0.5=512/1024` on
>    both int and float sides, identically.
> 2. **`FUN_00034350`'s OWN entry re-check, re-derived from FRESH DISASSEMBLY (not the decompile's
>    verbose overflow-safe boolean form, which this session's first pass mis-parsed)**: `0x34358-0x3438a`
>    is two plain `cmp`+branch pairs testing `-5 <= (gp-0x6bc6 − gp-0x6bc8) <= 5`. Critically,
>    `gp-0x6bc8` does **NOT** store the ceiling (`fVar6`) — it stores `r26 = max(fVar5,-fVar6)`, which
>    **equals `fVar5` (=gp-0x6bd0/1024) itself** whenever in-bounds. So this residual is the EXACT SAME
>    `r16` `FUN_000347b8` already tested, re-read from RAM a cycle later — a genuine redundant check, not
>    a broader/different condition (an earlier decompile-based read of this in the same session wrongly
>    suggested it might fire every cycle; the raw asm resolves that cleanly).
>
> **Combined verdict: given the corrected dose table, `gp-0x6bd0`'s actual (unclamped) creep-band value
> never comes within 215 counts of the ceiling's absolute floor (512) at any rate this car has been
> measured at. The ±5-count window is never threatened — margin is 43x the tolerance, and no possible
> movement of `gp-0x6ac2` between the T1/T2 samples can close a 215-count gap it structurally cannot
> create (ceiling only ever rises from its own floor of 512, never falls below it).** The
> "pinned-at-ceiling + gp-0x6ac2 timing-skew" mechanism below is a real, correctly-characterized
> mechanism in the ABSTRACT (the monitor genuinely has zero debounce and a real dual-sample-time gap),
> but it is **NOT reachable by V75's actual creep-band dose** — this file's original §4 sizing error
> (extrapolating the 2.74x ratio uniformly to V74's 354-count PEAK-envelope figure, rather than reading
> the real per-rate table where FactorE saturates) inverted the verdict. **Whether `FUN_000347b8` is
> still relevant to the actual on-car fault is now OPEN again** — it would need either a rate spike this
> table doesn't cover (never observed, speculative) or a completely different mechanism. The census in
> §1, the forward chain in §2, and the monitor's MECHANICS in §3 (debounce, fault routing, DTC) all still
> stand as verified; only the SIZING conclusion in §4/§5 is retracted.

2026-08-06, task: trace `gp-0x6bd0` (base-assist damper output) forward to the motor and find any
monitor a LARGER damper term (V75, 2.74x V74's dose) could trip, in the context of an on-car report:
EPS lamp + LKAS fault + total power-steering loss immediately after a stoplight-to-launch transition
with LKAS engaged. Program: `code.bin` (stock) — explicitly confirmed via `list_open_programs` before
starting (session also had `_v74_engagedcols_x12_plain_image.bin` / `_v75_*_magprobe_plain_image.bin`
open; all analysis below is against STOCK unless noted).

## (1) gp-0x6bd0 reader/writer census — TRIPLE-CONFIRMED, exactly 8 accesses (3 writers, 5 readers)

Address `gp-0x6bd0` = `0xFEDF1430`. **`get_xrefs_to(0xFEDF1430)` on `code.bin` returns "No references
found"** — the documented misleading-zero trap (Ghidra does not resolve gp-relative displacements).
Two independent corroborating methods agree exactly:
- **Python raw LE byte scan** (`analysis-2020accord/scan_gp_accesses.py`, both the 4-byte Format-VII
  disp16 encoding AND a 48-bit extended-disp23 brute force): 8 Format-VII hits, 0 *genuine* disp23 hits
  (the scanner's 3 "extended" candidates at `0x34730`/`0x34744`/`0x3047bc` are byte-overlap artifacts of
  the SAME already-counted 4-byte instructions, confirmed by identical addresses and a nonsensical
  `disp=-0x1b6bd0`).
- **`search_instructions(operand_pattern="6bd0")`**: 11 raw hits; 3 are the known false-positive class
  (branch-target absolute-address text collisions: `be 0x0006bd04`, `bgt 0x00076bd0`, `bnh 0x00076bd0`
  — none are real `gp-0x6bd0` accesses). The remaining 8 are IDENTICAL, address-for-address, to the
  Python scan.

| addr | op | function | role |
|---|---|---|---|
| `0x034730` | `st.h r6,-0x6bd0,gp` | `FUN_00034350` | writer — clamp to +ceiling |
| `0x034744` | `st.h r6,-0x6bd0,gp` | `FUN_00034350` | writer — unclamped pass-through (raw product) |
| `0x034752` | `st.h r8,-0x6bd0,gp` | `FUN_00034350` | writer — clamp to −ceiling |
| `0x034726` | `ld.h -0x6bd0,gp,r7` | `FUN_00034350` | reader — self, shadow-lockstep check `sVar2==sVar12` (vs `gp-0x4cf2`) gating which of the 3 writes above fires this cycle |
| `0x0001c114` | `ld.h -0x6bd0,gp,r8` | `FUN_0001bf88` | reader — UDS RDBI telemetry pack only (case `bVar2==0xb`); packs raw bytes into a diagnostic response buffer via `FUN_00059912`, **no fault/DTC call anywhere in this function** — corrects a prior memory's blanket "range-checks + faults" description of this function, which does not hold for this specific case |
| `0x0347bc` | `ld.h -0x6bd0,gp,r7` | `FUN_000347b8` | reader — **THE NEW MONITOR, see §3** |
| `0x038150` | `ld.h -0x6bd0,gp,r10` | `FUN_00038148` | reader — PATH-A composite (weighted sum → `gp-0x6b70`, per [[reference_accord_factorc_e_damper_full_trace_r24r26_parallel]]) |
| `0x03ac78` | `ld.h -0x6bd0,gp,r9` | `FUN_0003aa2c` | reader — the aggregator, see §2 |

The 3-writer shape is the standard shadow-lockstep clamp idiom, confirmed fresh by full decompile of
`FUN_00034350`: `sVar2=gp-0x6bd0` and `sVar12=gp-0x4cf2` (the shadow) are compared; only if they still
match from last cycle does ONE of the three branches (clamp-high / raw / clamp-low) write BOTH
`gp-0x6bd0` and `gp-0x4cf2` together; on mismatch, `FUN_0006b9fa` (a generic lockstep-fault relay →
`FUN_0006ce7c(4)`) is called INSTEAD and neither is updated this cycle (stale-hold).

## (2) Forward chain, byte-confirmed join at the aggregator

`FUN_0003aa2c` (aggregator), fresh disasm `0x3ac78-0x3acce`:
```
0x3ac78  ld.h  -0x6bd0,gp,r9        ; r9 = gp-0x6bd0
0x3ac84  addi  0x800,r9,r15         ; r15 = r9 + 2048
0x3ac88  addi  -0x1001,r15,r0       ; flags = r15 - 4097
0x3ac8c  cmovc 0x0,r9,r12           ; r12 = (r9+2048 < 4097, i.e. |r9|<=2048) ? r9 : 0   -- ZERO-GATE not clamp
...
0x3acce  add   r8,r12               ; running_total += r12   -- plain unscaled ADD
```
Confirms prior memory byte-exact: `gp-0x6bd0` is accepted whole (not rescaled) into the SAME running
sum as LKAS (`gp-0x6b4c`), boost (`gp-0x6bbe`), friction (`gp-0x6b26`), resonance (`gp-0x6ad4`), r24/r26,
etc. — 11 additive terms total. Gate is `|gp-0x6bd0| <= 2048` (inclusive) — structurally unreachable
since the damper's OWN ceiling caps it at 1024 max (Q10 unity), well inside this gate.

Downstream (established in prior sessions, re-cited not re-derived this session):
`gp-0x6b94` (aggregator output, clamp ±0x2800=10240) → **G1 governor** `FUN_0004503c` (clamp
±(gp-0x4f64×Q15≤1.0), nominal ceiling 4762, cal `0xC6202`) → `gp-0x6ace` → post-governor comp-add
`FUN_000456a4` → `gp-0x6acc` → shaper `FUN_00042af8` (several stages, **final hard clamp ±0x2000=8192**
at `0x43B52`/`0x43DFC`) → `gp-0x6b98` (delivered torque) → gates (does not feed) the FOC current loop
via `FUN_00041464`'s ±0x2000 validity window at `0x41846-0x4185E`.

**Key structural fact for sizing: none of these downstream clamps can ever be the trigger.** The
damper's maximum possible contribution (1024 counts, or even a hypothetical unclamped product) is
tiny relative to G1's 4762 nominal ceiling and the shaper's 8192 rail — matches
[[reference-accord-g1-governor-total-scope-verdict]] Verdict 5 ("does not bind at small-amplitude
command content"). **The vulnerability found this session is NOT in the delivery/saturation path at
all — it is a LOCAL plausibility check on gp-0x6bd0's own value, upstream of all of this.**

## (3) THE NEW MONITOR — `FUN_000347b8`, gp-0x6bd0's own float-domain ceiling re-check

**Caller**: `FUN_00022ca0` (task-5, 100 Hz, confirmed via `get_function_callers`) — and critically,
**fresh decompile of `FUN_00022ca0` shows the exact call sequence**:
```c
FUN_00034350(0x11);   // computes/clamps gp-0x6bd0 against the ceiling, sampling gp-0x6ac2 at T1
FUN_000347b8();        // independently RE-validates gp-0x6bd0, sampling gp-0x6ac2 AGAIN at T2
FUN_00034a72(0x12);    // boost
FUN_00035154();
```
Both calls sit under the SAME `if (uVar5 != 0)` gate, `uVar5 = (1<<gp-0x67fa) & 0x830` — live whenever
`gp-0x67fa` ∈ {4,5,11}, which per `docs/STATE.md` includes the CONSTANT state 5 measured in 101,117 of
101,118 frames on V74's flight — **this whole mechanism runs on every ordinary engaged/manual 100 Hz
tick**, not a rare mode.

**Full disasm, `FUN_000347b8` (0x347b8-0x348dc)** [EVIDENCE, `disassemble_function`]:
```
fVar5 = float(gp-0x6bd0) / 1024                                   ; the damper's own value, normalized
dVar4 = (double) gp-0x6ac2  (unsigned)                             ; the ceiling's OWN index (back-drive rate)
if (dVar4 <= 13000.0):
    fVar6 = LERP(gp-0x6ac2, table@tp+0x7554)                       ; independently recomputed CEILING (float)
else:
    fVar6 = float(cal tp+0x7158 = 0xC6158 = 512) / 1024 = 0.5      ; same fallback FUN_00034350 itself uses
r16 = signed_excess(fVar5, fVar6)          ; 0 if |fVar5|<=fVar6 in-bounds; else the (negative) overshoot
if r16 > +5/1024 OR r16 < -5/1024:
    FUN_000462e6(0x417a, fVar5, fVar6, ..., -5/1024)               ; FAULT
gp-0x6bc4=5 ; gp-0x6bc8=round(fVar6*1024) ; gp-0x6bca=-5 ; gp-0x6bc6=round(fVar5*1024)   ; unconditional, every cycle
```
The ±5/1024 (≈±5 raw-count) window test uses the SAME idiom (same two constants `0x3ba00000`/
`0xbba00000`) as the already-documented "Monitor 2" bit32 check in
[[reference-accord-eme-bit32-float-monitor]] — confirms this is the firmware's standard epsilon for
int/float consistency checks generally, not something specific to this site.

**The float table is a FIXED (non-mode-indexed) twin of the integer ceiling** [EVIDENCE, raw
`read_memory` at `0xC6550`]:
```
0xC6550: count=2
0xC6554 (tp+0x7554): X0 = 300.0     0xC6558 (tp+0x7558): X1 = 800.0
0xC655C (tp+0x755c): Y0 = 0.5 (=512/1024)   0xC6560 (tp+0x7560): Y1 = 1.0 (=1024/1024)
```
**Byte-for-byte identical breakpoints to the integer ceiling `0xC77A0[mode26]` = `X=[300,800]
Y=[512,1024]`** (per [[reference_accord_v75_ceiling_c77a0_noclip_asymmetry_and_aggregator_inclusive_bound]]),
but this cell is read via a PLAIN `tp+0x7554` displacement — **NOT mode-indexed** (no
`(byte)(gp+0x63fd)*4` multiply anywhere in `FUN_000347b8`), unlike `FUN_00034350`'s own ceiling lookup.
`build_v74_tva.py`/`build_v75_tva.py`: **zero matches for `6554`/`C655`/`c655`** — this table has never
been examined or touched by any build in this kit.

**Fault routing, traced to the DTC**: `FUN_000462e6` ALWAYS calls `FUN_00016de6(0x1d, param_1, 1, 1)`
(hardcoded fault index 0x1d, regardless of its own first argument — confirmed by fresh decompile).
`FUN_00034350`'s OWN entry (`0x34358-0x3438a`) separately re-validates the SAME 4 cells
(`gp-0x6bc4/6bc6/6bc8/6bca`, written unconditionally by `FUN_000347b8` every cycle) and, on mismatch,
calls `FUN_0004613e(0x4179,...)` which ALWAYS calls `FUN_00016de6(0x1c, ...)` — **both 0x1c and 0x1d
map to DTC `0xF00049`** per [[reference-accord-consistency-monitor-hardshutdown]]'s established table.
This is a genuine "shadow written on a different path than the primary" pattern: `FUN_00034350`
(int-domain producer) and `FUN_000347b8` (float-domain independent re-check, called separately) trade
state through `gp-0x6bc4..0x6bca`, and a divergence trips a HARD DTC.

## THE DEBOUNCE — [EVIDENCE, fresh raw byte read] N=1, not N=10

`FUN_00018738`'s generic per-fault-index debounce record lives at `tp-0x72a8 + idx*0x1c` (28-byte
stride). Read directly for idx=0x1c and idx=0x1d:
```
idx 0x1c (iVar6=0xB8068): threshold u16 @0xB804E = 1   increment u16 @0xB805A = 0   bitmask u32 @0xB8054 = 0x3D01
idx 0x1d (iVar6=0xB8084): threshold u16 @0xB806A = 1   increment u16 @0xB8076 = 0   bitmask u32 @0xB8070 = 0x3D01
```
Trip arithmetic: `uVar4 = increment(0) + prior_count + 1`; trips (`bVar1=true`) when `uVar4 >= threshold`.
With `threshold=1`, the FIRST occurrence (`prior_count=0` → `uVar4=1`) ALREADY satisfies `1 >= 1` →
**trips on the very first bad 100 Hz sample.** Bit 0 of the bitmask (0x3D01, bit0 set) is tested via
`FUN_00046ea6(tp-0x58c0=0)` — a global per-bit inhibit-flag check (`gp-0x18d0|gp-0x18d4`, bit 0); if
clear (not inhibited — confirmed live in the historical V26 on-car fault via this SAME generic chain,
per [[reference-accord-consistency-monitor-hardshutdown]]), `gp-0x685c=1` (DTC latch) fires
IMMEDIATELY, `FUN_00018bc0()` sets `gp-0x3ef8=1`, and `FUN_00019f7c` (polled every base-loop cycle)
sees `gp-0x685c!=0` and drives `gp-0x67fa=8` → `FUN_0001a16a` → `FUN_00045608(3,0,0x8000,0x8000)`
(motor-off) within one further tick, latched via `gp-0x3ee8=1` until power-cycle.

**This revises the "10 fault cycles" figure in [[reference-accord-consistency-monitor-hardshutdown]]/
[[reference-accord-eme-bit32-float-monitor]] for THIS path specifically** — that 10-cycle number
belongs to Monitor 1's OWN internal weight-sum accumulator (`sVar24`/`gp-0x3564`, function-local to
`FUN_00042af8`, +=10/cycle to a 100 threshold, BEFORE it even calls into this generic layer). Neither
`FUN_00034350`'s entry check nor `FUN_000347b8` has any such internal pre-accumulator — they call
`FUN_0004613e`/`FUN_000462e6` directly on the FIRST detected mismatch, and this generic layer's own
threshold for idx 0x1c/0x1d is 1. **N=1 sample, 100 Hz, ≈10 ms from bad sample to DTC latch.**

## (4) Sizing — the mechanism, and why it is exposure not magnitude

The check is NOT "is |gp-0x6bd0| too large" in absolute terms — it is "does gp-0x6bd0 match an
INDEPENDENTLY-RESAMPLED recomputation of its own ceiling, within ±5 counts." This is harmless whenever
gp-0x6bd0 sits comfortably BELOW the ceiling (any transient shift in the ceiling's own value, driven by
`gp-0x6ac2` changing between `FUN_00034350`'s sample (T1) and `FUN_000347b8`'s sample (T2), is masked
by the large margin). **It is exposed specifically when gp-0x6bd0 is PINNED AT the ceiling** — because
then a ceiling recomputed at a slightly different instant (T2 vs T1) can disagree with the value that
was actually written (computed against T1's ceiling) by more than 5 counts, if `gp-0x6ac2` crossed
enough of the `[300,800]` ramp (slope 512/500=1.024 counts per unit) in between — e.g. crossing the
`X0=300` breakpoint from the flat-512 floor into the ramp shifts the ceiling by >5 counts for a ~5-unit
move in `gp-0x6ac2`.

**V74 vs V75, using each build's OWN stated numbers** (`build_v75_tva.py` header, not re-derived):
- V74 delivered dose at the measured in-burst rate (99 counts): **50 counts** — 9.8% of the 512 floor.
  V74's separately-measured on-car PEAK envelope (given in task context): **354 counts** — 69% of 512,
  still a wide margin.
- V75 delivered dose at the same rate: **137 counts** (2.74×); at the 6-9 Hz arm's rate (127): **181
  counts**. **`build_v75_tva.py` states explicitly, as a designed structural fact**: "ALL ELEVEN modes
  written to 566 TOUCH the floor — exactly 512, at the grid corner (speed 0, rate 4000)... 566 is the
  LARGEST `C_Y0` for which that corner lands at or below 512" — **V75's calibration is binary-searched
  to reach the 512 ceiling floor EXACTLY at some (speed,rate) cells, by construction.**

**⇒ V74's dose (peak 354, always ≥158 counts of margin below the 512 floor) structurally could not
expose this check. V75's dose is explicitly engineered to touch 512 (zero margin) at some cells on the
grid, and — extrapolating the 2.74× ratio to V74's own measured 354-count peak (≈970 counts, an
estimate, not independently re-measured this session) — would be CLAMPED/PINNED at the ceiling across a
much wider span of the (speed,rate) grid than V74 ever reached.** Pinning at the ceiling is the
precondition for this monitor's ±5-count window to matter at all.

## (5) Standstill specificity

- `FUN_000347b8` itself carries **no explicit vehicle-speed gate** — it runs unconditionally every 100
  Hz tick whenever `gp-0x67fa` ∈ {4,5,11} (ordinary engaged/manual driving, confirmed constant-5 on
  V74's own flight).
- The EXPOSURE mechanism is not a firmware ARM condition but a **design coincidence**: V74/V75's
  entire purpose is to open FactorC's dead zone AT CREEP (`build_v75_tva.py`: "raises the CREEP end of
  the speed axis") — i.e., these builds specifically activate the damper in the exact low-speed regime
  a stoplight launch sits in. Combined with `gp-0x6ac2` (the ceiling's OWN index) being a back-drive /
  torque-vs-rate SIGN-DISAGREEMENT detector — [BELIEF, not independently measured this session, but
  structurally plausible] most active exactly when a driver's initial input and the motor's just-started
  rotation can briefly disagree in sign (static-friction breakaway at launch) — **the fault's timing
  (immediately after a stop, pulling away) is consistent with both halves of the mechanism converging
  at once: the damper newly active at creep, AND its own ceiling index most volatile at launch.**
- `FUN_00069b8e` (mask 0x830, 1 kHz, freshly decompiled this session) IS a genuine standstill/idle-state
  gate (checks `|gp-0x6b98|`, `|gp-0x6abc|`, `|gp-0x4f60|` all under cals `tp+0x590a/0x5912/0x590e`, plus
  a timer vs `tp+0x592a`) but **does NOT reference `gp-0x6bd0` at all, and its only fault-relay call
  (`FUN_0006b9ee`) sits on a flag-disagreement/RAM-corruption path, not a torque-magnitude path** — RULED
  OUT as a candidate for this scenario, closing a previously-open item from
  [[reference_accord_gp6bd0_seed_ruled_out_and_engagement_gates_found]]'s neighborhood.

## Verdict

**[EVIDENCE]** A real, previously-undocumented, zero-debounce (N=1 sample, 100 Hz) hard-shutdown
monitor exists directly on `gp-0x6bd0`'s own value (`FUN_000347b8`, fault index 0x1d → DTC 0xF00049),
completely independent of and upstream of every downstream saturation/rate/energy-budget clamp (all of
which are ruled out by margin — the damper's contribution is tiny relative to G1's 4762 and the
shaper's 8192). **[BELIEF, mechanistically well-supported but not confirmed against actual fault-event
telemetry]** V75's dose is large enough to pin `gp-0x6bd0` at its own ceiling (512, by the build
script's own admission) across a much wider operating range than V74 ever reached, and pinning at the
ceiling is the precondition that exposes this monitor's ±5-count cross-check to transient disagreement
driven by `gp-0x6ac2` (the ceiling's own index) changing between the two independent sample times inside
the same 100 Hz tick.

## Open items / what would settle it
1. **Direct confirmation**: pull DTC history off the car after the fault — is the logged code
   `0xF00049` / internal fault index `0x1d` (or `0x1c`)? This would be decisive and is the single best
   next step.
2. `gp-0x6ac2`'s actual statistical behavior during a real standstill→launch transition was NOT measured
   this session (no telemetry pulled) — V75's OWN probe already added `bit3 = (gp-0x6ac2 != 0)`
   ("never measured in this kit" per `build_v75_tva.py`) — flying that probe (on a build that does NOT
   also carry the fault risk, e.g. a rung with `LEVERS={"CY0":False,"EX1":False}` or similar) would give
   the missing piece.
3. Whether `FUN_00046ea6(0)`'s underlying inhibit flags (`gp-0x18d0`/`gp-0x18d4` bit 0) are ever SET
   under ordinary driving (which would gate this whole path closed) was not traced to its own writers
   this session — inherited as "open" from the historical V26 case, where it was empirically NOT
   inhibiting.
4. The exact number of 1 kHz-task opportunities that can land between `FUN_00034350`'s and
   `FUN_000347b8`'s back-to-back calls (they are adjacent `jarl`s in `FUN_00022ca0`'s source with no
   explicit `__disable_irq` bracket around the pair) was not measured — the race window is narrow per
   100 Hz tick but recurs every tick during the whole launch.

## Related
[[reference_accord_factorc_e_damper_full_trace_r24r26_parallel]],
[[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]] — the producer this
extends. [[reference_accord_v75_ceiling_c77a0_noclip_asymmetry_and_aggregator_inclusive_bound]],
[[reference_accord_v75_true_headroom_e_exhausted_c_max_566]],
[[reference_accord_gp6ac2_is_backdrive_rate_not_gp6ac0_twin]] — the ceiling table and its index, whose
consequences for THIS monitor are new this session. [[reference-accord-consistency-monitor-hardshutdown]],
[[reference-accord-eme-bit32-float-monitor]] — the generic DTC/debounce infrastructure and the sibling
int/float check this session's ±5-count idiom matches exactly.
[[reference-accord-g1-governor-total-scope-verdict]] — source of the "downstream clamps can't be the
trigger" ruling.
