---
name: reference_accord_friction_lane_direct_hard_fault_monitor_gp6b26_c4004
description: The mode-26 friction lane (gp-0x6b26, FUN_00036c12) has its own previously-undocumented, deterministic (no timing/race dependency) hard-fault monitor -- FUN_00036d74, |gp-0x6b26/1024| > cal(0xC4004)=0.5=512 raw counts -> DTC 0x1d, plus a one-cycle-lagged redundant echo inside FUN_00036c12 itself -> DTC 0x1c. V73 raised the lane's OWN outer clamp 0xC407E from 511 (1 count under this ceiling, evidently by design) to 850 (338 counts OVER it) -- mode-proof, so this affects manual driving too. V74/V75's mode-26 Y-table x1.5 edit then lowers the motor-rate magnitude needed to cross the now-exposed 512 ceiling from ~6258 to ~4180 raw gp-0x6c2c counts, WITHOUT ever engaging the 850 outer clamp. Numerically verified in Python.
metadata:
  type: reference
---

2026-08-07, dispatched by team-lead to trace the mode-26 friction lane as the surviving V74 delta candidate
after Surface A (gp-0x6bd0 ceiling-race) and Monitor 1/2 (never read gp-0x6bd0/gp-0x6b94/aggregator lanes)
were both exonerated. Program: stock `code.bin`, confirmed current. Method: decompile-first, then disasm
for exact addresses/constants; Python re-implementation of the integer chain to verify the numeric crossing.
`gp=0xFEDF8000`, `tp=0xBF000`.

## THE FINDING, stated first
**This lane has a DIRECT, deterministic, previously-undocumented hard-fault monitor on its own output —
not a race, not an aggregator-mediated path. V73's clamp raise (511->850, mode-proof) opened a 338-count
gap above that monitor's fixed 512-count ceiling that nothing else in the firmware re-validated. V74/V75's
mode-26 friction-table x1.5 edit then makes that gap reachable at an ordinary (not extreme) motor-rate
magnitude, WITHOUT the 850 clamp ever engaging.** [EVIDENCE throughout unless flagged BELIEF/OPEN]

## Producer, confirmed [EVIDENCE, fresh decompile+disasm FUN_00036c12 @0x36c12-0x36d70]
```
sVar7 = LERP(gp-0x6a5e; table @0xCBE74[mode], X=[0,1280,5760] Y=mode-specific)   ; Y_SPEED coefficient
        gated: gp-0x671a<0xff && gp-0x67f4==1 (voted-speed-valid), else fallback cal(tp+0x740a/0x740c)
gate(gp-0x6c2c) = gp-0x6c2c if |gp-0x6c2c+32000|<64001 (i.e. roughly |gp-0x6c2c|<32001) else 0   ; @0x36c22-0x36c2c
raw = (((gate(gp-0x6c2c) * sVar7) >> 6) * 0x111) >> 0x12                          ; 0x111=273, >>18
gp-0x6b26 = clamp(raw, -cal(tp+0x507e), +cal(tp+0x507e))      ; tp+0x507e = 0xBF000+0x507E = 0xC407E
            shadow-lockstep with gp-0x4cd0, FUN_0006b9fa on mismatch (same pattern as gp-0x6bd0)
```
**Index = `gp-0x6a5e` (VOTED VEHICLE SPEED, confirmed `0x36c60: ld.h -0x6a5e[gp],r10`), scale 64 ct/km/h**
(`1280/20=64`, `5760/90=64` — matches mode0's km/h-labeled reading from prior memory exactly after unit
conversion). **Multiplier = `gp-0x6c2c` (filtered MOTOR RATE — NOT torque, NOT bar torque)**, confirmed
`0x36c1a: ld.h -0x6c2c[gp],r9`. **`0xC407E` (=`tp+0x507e`) is read `ld.h` (signed) at 3 sites, ALL inside
this function — confirmed exclusive, matches prior memory's "3 readers, all in this function."**
**⇒ Corrects team-lead's framing: this is a RATE x SPEED viscous-damping lane, not a torque-domain lane.
Bar torque does not appear anywhere in this arithmetic.** (A large bar-torque event can still *physically*
co-occur with a large motor-rate response — see Verdict below — but there is no code dependency.)

Mode-26 table, byte-confirmed at `0xD7A54` (fresh `read_memory`, exact match to team-lead's own read):
`n=3, X=[0,1280,5760], Y_stock=[-9830,-5734,-1966]`. `0xC407E` fresh-read on stock `code.bin` = **511**
(bytes `ff 01`). Team-lead's independently-confirmed table across builds: V73 raises `0xC407E`->850
(Y-table untouched); V74/V75 keep 850 AND raise mode-26 `Y`->`[-14745,-8601,-2949]` (exactly x1.5 at every
point, confirmed by the Python check below).

## THE MONITOR — `FUN_00036d74`, same-cycle, deterministic [EVIDENCE, fresh decompile+disasm @0x36d74-0x36dec]
Caller: `FUN_0002214a` (1kHz), called **immediately after `FUN_00036c12`** in the SAME cycle (confirmed
sequence in `FUN_0002214a`'s own decompile: `...FUN_00036c12(0x1f); FUN_00036d74(); FUN_00036bec();...`,
under the `uVar4=uVar2&0x830` gate — same {4,5,11} state mask as the damper's monitor pair).
```
fVar3 = (float)gp-0x6b26 / 1024                          ; 0x36d78-0x36d88
cal   = *(float*)(tp+0x5004)                              ; 0x36d80/0x36d8c/0x36dbc, tp+0x5004=0xC4004
if (fVar3 > cal) || (fVar3 < -cal):                        ; 0x36d90-0x36daa
    FUN_000462e6(0x39bc, fVar3, 0, cal, -cal)               ; -> FUN_00016de6(0x1d,...) UNCONDITIONALLY
                                                             ;    (confirmed pattern: 0x462e6 always routes 0x1d, established 3x this session for 0x417a/0x3a09/now 0x39bc)
gp-0x6b24=-cal*1024 ; gp-0x6b1e=+cal*1024 ; gp-0x6b22=0 ; gp-0x6b20=fVar3*1024   ; unconditional, every cycle
```
**`cal(0xC4004)` fresh-read = bytes `00 00 00 3F` = float32 **0.5** exactly = 512/1024 in the Q10 domain.**
**This is a flat, symmetric, `gp-0x6ac2`-independent, timing-independent magnitude ceiling on `gp-0x6b26`
itself — 512 raw counts, always.** No race variable, no re-sampled comparator (unlike Surface A) — if
`|gp-0x6b26|` ever exceeds 512, this WILL fault, deterministically, every time.

**`FUN_00036c12`'s OWN top-of-function check** (`0x36d02-0x36d38`, fault code `0x3672 -> FUN_0004613e ->
FUN_00016de6(0x1c,...)` unconditionally) re-tests `(gp-0x6b20-gp-0x6b22)` against `[gp-0x6b24,gp-0x6b1e]` —
the SAME 512-count bound `FUN_00036d74` just wrote LAST cycle, re-read one tick later. **Exact same
"redundant one-cycle-lagged echo of the prior cycle's already-computed residual" pattern documented for
`gp-0x6bd0`'s `FUN_00034350`/`FUN_000347b8` pair** — not an independent second condition, a confirmatory
mirror. `cal(0xC4004)` is used EXCLUSIVELY by `FUN_00036d74` (confirmed: `search_instructions("5004")` —
the only genuine `tp+0x5004` hits are its 3 reads; all other matches are unrelated `gp-0x5004`/absolute-
address/branch-target text collisions, adjudicated by context).

## THE GAP, and why it is mode-proof [EVIDENCE]
`0xC407E` (the lane's outer clamp) is **not mode-indexed** — a single shared cal across every mode.
- **Stock/pre-V73: 511 = exactly 1 count under the monitor's 512 ceiling.** This is very unlikely to be
  coincidence — it reads as the original calibrator having deliberately set the clamp 1 count inside the
  independent check's bound, guaranteeing by construction that the clamp itself could never trip it.
- **V73 onward: 850 = 338 counts OVER the ceiling.** The clamp no longer protects against the monitor at
  all — any raw (pre-clamp) friction product landing in `[512,850)` passes through the clamp UNTOUCHED and
  trips `FUN_00036d74` on the very next 1kHz tick, or `[850,∞)` gets clamped down to 850, which is STILL
  over 512 and ALSO trips it.
- **Because `0xC407E` is shared across modes, this gap exists in mode 24 (manual) too**, using the
  UNEDITED stock Y-table there (per team-lead's own byte read: mode24 Y unchanged in V74/V75) — see the
  quantitative section below for what magnitude that requires.

## Quantitative crossing, verified in Python (`scratchpad` script, exact integer/float chain re-implemented)
At the fault's stated operating point (33.3 km/h -> `gp-0x6a5e`=2131 raw, scale 64ct/km/h):
```
Y_speed stock = -5018.2   Y_speed V74/75 = -7527.4   ratio = EXACTLY 1.500 (matches the table edit precisely)
coefficient (per raw gp-0x6c2c count) stock = -0.0817   V74/75 = -0.1225   ratio = 1.500

gp-0x6c2c needed for STOCK's lane to reach its OWN clamp (511):        ~6258
gp-0x6c2c needed for V74/75's lane to reach FRICTION_CEIL (512):       ~4180   <- LOWER, easier to reach
V74/75's raw_product at gp-0x6c2c=6258 (stock's OWN clamp-reaching rate): **-766.5**
   -- exceeds the 512 ceiling by 254 counts, and does NOT reach the 850 outer clamp (|-766.5|<850),
      so it passes through completely UNCLAMPED and trips FUN_00036d74 with no rail to catch it.
```
**⇒ V74/V75 do not need an exotic or extreme motor-rate event to cross this ceiling. Any `gp-0x6c2c`
magnitude that would ALREADY have made STOCK's friction lane reach its own natural clamp boundary — i.e.
any driving condition under which the pre-V74 lane was already near its ceiling — produces a value ~254
counts past the independent monitor's threshold under V74/V75's calibration, unclamped.**

## Latent V73-only risk, distinct from the main finding [BELIEF, flagged not conflated]
Because `0xC407E` is mode-proof and the monitor's 512 ceiling is fixed, **V73 ALONE (clamp raised, Y-table
still stock, in EITHER mode) already has a nonzero path to this same fault** — it would need
`gp-0x6c2c`~6258 (mode 26) or the mode-24 equivalent (Y-table stock in both, so the SAME ~6258 estimate
applies in manual too, since mode24's Y-table is confirmed byte-identical to mode26-stock at the same
X-breakpoints per team-lead's table). Whether real driving ever reaches `gp-0x6c2c`~6258 is unmeasured —
if it does not, V73 flying clean is fully explained (the clamp raise added dead headroom nobody used); if
it does occasionally, V73 carried unexploited risk that V74/V75 simply made much easier to reach (lowering
the required rate from ~6258 to ~4180, a 1.5x-easier threshold). **This means reverting V74/V75's Y-table
edit alone does not fully close this class of risk — `0xC407E`=850 by itself is 338 counts past a monitor
neither V73 nor any later build appears to have re-checked.**

## Answers to team-lead's specific questions
1. **Index**: `gp-0x6a5e`, voted vehicle speed, 64 ct/km/h, table @`0xCBE74[mode]`. Not torque.
2. **Sign**: comes from `gp-0x6c2c`'s own continuous (not stepped) value times an always-negative
   `Y_speed`, gated by a symmetric `±32000` plausibility window — no bare `sign()` operator, no
   hysteresis/deadband/filter ON the sign itself, but `gp-0x6c2c` is itself an `alpha=22/64=0.344`
   single-pole EMA (per [[reference-accord-four-unprobed-lanes-abcd-solved]]), so a direction reversal
   shows as a smooth (moderately fast) swing through zero, not an instantaneous 2x step. **The
   sign-reversal-doubles-the-step hypothesis is not needed** — a monotonic rise in `|gp-0x6c2c|` past
   ~4180 trips the monitor just as surely, with no reversal required.
3. **What `0xC407E` clamps, and does it still bind**: exclusively `gp-0x6b26`'s own raw product (3
   internal readers, confirmed). **At the stated operating point it does NOT still bind — the signal
   crosses `FRICTION_CEIL` (512) at `gp-0x6c2c`~4180, well before it would even reach the 850 clamp
   (~6258 needed under V74/75's own coefficient to reach 850). The clamp is irrelevant to this fault path
   — the independent monitor fires first.**
4. **Does it reach a monitor's compared quantity — decisive question, answered YES, directly**:
   `FUN_00036d74` (same-cycle) -> `0x39bc` -> DTC 0x1d, and `FUN_00036c12`'s own entry check -> `0x3672`
   -> DTC 0x1c, one cycle later, redundant echo. This is a DIRECT dedicated monitor on `gp-0x6b26` itself,
   not mediated through the aggregator/governor/shaper at all — structurally simpler and MORE dangerous
   than Surface A, because there is no re-sampled comparator to race against; it is a flat, deterministic
   magnitude test.
5. **`FUN_00038148`'s `±1024` gate** (the PATH-2-style aggregator route, weighted by `0xC63A6`): NOT
   re-checked numerically this session — moot for explaining the fault, since the DIRECT monitor above
   fires first, upstream of and independent from that path.

## Verdict
**[EVIDENCE]** The mode-26 friction lane is NOT exonerated — unlike Surface A and Monitor 1/2, it has its
own direct, deterministic, address-pinned hard-fault path that V73's clamp raise opened and V74/V75's
table edit makes reachable at an ordinary (non-extreme) motor-rate magnitude, with no race/timing
dependency to escape through. **[BELIEF, not confirmed against telemetry]** Whether `gp-0x6c2c` actually
reached ~4180 (V74/75) at either real fault moment is unmeasured — this is a real, quantified, reachable
mechanism, not a proof that it is THE cause, but it is the strongest candidate found this session by a
wide margin (deterministic vs. Surface A's mathematically-proven-unreachable clamp-race).

## Open items / what would settle it
1. **`gp-0x6c2c`'s physical scale (deg/s per raw count) is not derived** — needed to say whether ~4180
   (or ~6258 for the V73-only latent risk) is an ordinary or extreme motor-rate value. Next step: decompile
   `FUN_00041464`'s `gp-0x35a0`/`gp-0x6c2c` chain fully (the `α=22/64` EMA on `raw resolver rate gp-0x4f50
   <<5`, final `>>9` scale) and anchor `gp-0x4f50` against a known-scale sibling signal.
2. Telemetry of `gp-0x6c2c` (or a proxy) at the two actual fault moments would settle this directly —
   compare against the 4180 threshold.
3. Whether `gp-0x6c2c` (this lane's own filtered rate) correlates with the `|d(angle rate)/dt|` metric
   team-lead measured is a physical-plausibility argument, not a code dependency — not quantified.

## Table-only lever, two directions, pick deliberately
1. **Lower `0xC407E`** back toward `<=511` (or precisely restore the "1 count under 512" invariant) —
   fixes the SOURCE, mode-proof, restores the original margin, no monitor loosening. Preferred direction
   per this kit's convention (fix the source table, not the safety check).
2. **Raise `cal(0xC4004)`** to `>=` `0xC407E`'s new value — loosens the monitor itself; flagging per
   established convention this needs explicit operator judgment, since the design intent of a 512-count
   ceiling on this specific lane is not otherwise documented.
Either one closes the gap; (1) is far more surgical since it also closes the latent V73-only risk in
manual mode, while (2) would leave manual mode's exposure open unless it too is separately addressed.

## Related
[[reference-accord-four-unprobed-lanes-abcd-solved]] — original (mode0) reading of this lane, `gp-0x6c2c`'s
EMA chain, and the sign-convention open item this session's finding does not need to resolve (the monitor
fires on magnitude alone, sign-agnostic). [[reference_accord_ceiling_race_v74_manual_reconciliation_and_dtc_index_sharing]],
[[reference_accord_fun456a4_signed_term_and_fun45a20_mismatch_refuted]] — the two mechanisms exonerated
this session, whose elimination is what pointed at this lane. [[reference_accord_monitor1_monitor2_full_accumulator_mechanics_v75]] —
source of the "0x462e6 always routes 0x1d / 0x4613e always routes 0x1c" pattern, reused here for the third time.
