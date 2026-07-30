---
name: reference_accord_rate_limiter_enumeration_gp6bb2_cluster_and_angle_rate_producer
description: Full enumeration of rate/slew limiters on the boost-lane + angle-rate path for team-lead's ratchet-vs-grinding investigation. FUN_0004613e/13880 is NOT a rate limiter (it's a diagnostic-tag param to a fault logger) -- corrects the operator's framing. FUN_0003f776 is the SOLE producer of gp-0x6a56 (angle rate), deriving it ENTIRELY from gp-0x6abe (motor/resolver rate) via a fixed scale, not an independent sensor. The one REAL rate limiter on the assist path is FUN_00042af8's shaper slew (tp+0x71d6=0xC61D6=0, disabled in stock) -- already proposed in an OLD, pre-current-lineage build (old_tools/build_v16_tva.py) whose on-car result is NOT in current BUILD-LINEAGE.md.
metadata:
  type: reference
---

# Rate-limiter enumeration for the ratchet (7.4Hz) vs grinding (20-25Hz) investigation (2026-07-30)

Traced for team-lead's priority-1 rescope: operator's lived-experience call is that the ~7.4Hz ratchet
and 20-25Hz grinding are SEPARATE symptoms, ratchet correlating with command-rail duty (8.42x power
ratio rail-high/rail-low, partial r=+0.810) — the classic rate-limiter-induced-limit-cycle signature.

## (a) FUN_0004613e / "step 13880" — CORRECTS the operator's framing: this is NOT a rate limiter

[MEASURED] Call site `0x34a94-34aac` inside `FUN_00034a72`:
```c
delta = gp-0x6bb4 - gp-0x6bb6              // 0x34a86
if (gp-0x6bb2 > delta || gp-0x6bb8 < delta)  // 0x34a8a,90-92 -- i.e. |gp-0x6bb4-gp-0x6bb6| NOT within
                                              // [gp-0x6bb8, gp-0x6bb2] tolerance window
    FUN_0004613e(13880/*0x3638, a TAG*/, &gp-0x6bb4, &gp-0x6bb6, &gp-0x6bb2, &gp-0x6bb8)
gp-0x6bb2 = gp-0x6bb8   // "corrected" -- restore from the shadow/tolerance-lo constant
```
[MEASURED] Decompiled `FUN_0004613e` in full: it ONLY snapshots its 5 params into fixed log cells
(`gp-0x6920/18/1a/16/1c`) then calls `FUN_00016de6(0x1c, param_1, 1, 1)`. **No arithmetic, no clamping,
no write to any control-path signal.** 13880 is a DIAGNOSTIC TAG passed straight through to the fault
logger, not a step/rate constant — confirmed by `old_tools/build_v13_tva.py`'s own comment referencing
the SAME function with a DIFFERENT tag (`FUN_0004613e(0x38c7,..)`), i.e. this function is a
general-purpose "log+fault" callee, tag varies per call site.

[MEASURED] `gp-0x6bb4`/`gp-0x6bb6`/`gp-0x6bb8` are written EXCLUSIVELY by `FUN_00035154` (a sibling
function on the SAME task, `FUN_00022ca0`, called at `0x232fe` — `FUN_00034a72` itself is called at
`0x232c0`, i.e. `FUN_00034a72` runs first each tick, `FUN_00035154` runs second, so `FUN_00034a72`'s
check-at-top reads LAST TICK's `FUN_00035154` output). Decompiled+disassembled `FUN_00035154` in full:
it re-derives `gp-0x6bbe`'s (boost output) ceiling via an INDEPENDENT FLOAT computation against a
SEPARATE per-mode table (`0xc7888->0xc78b0(mode10)->0xD2018`), dumped this session: count=5,
X=[0,10,40,~90,~?] km/h (floats), **Y=[0.5,0.5,0.5,0.5,0.5] — flat, exactly matching the ALREADY-BYTE-
CONFIRMED integer Y5/speedLERP2 ceiling (0xD20C0, flat 512, 512/1024=0.5)**. It clamps
`boost_float=gp-0x6bbe/1024` to this SAME ±0.5 bound, and checks `|boost_float - clamped| <=
0.0048828125` (exactly 5/1024 counts). **This is a REDUNDANT re-verification of the SAME ±512 ceiling
`FUN_00034a72` already enforces via Y5 — not a second/different limiter.** If the two disagree by >5
counts, `FUN_00035154` ALSO independently calls `FUN_000462e6(0x39e9, ...)` (its own direct fault path,
separate from the `gp-0x6bb2` cross-tick check). `gp-0x6bb2=5`/`gp-0x6bb8=-5` (constants, stored every
tick) are literally this ±5-count tolerance re-expressed for the NEXT tick's cross-check in
`FUN_00034a72`.

**Verdict: neither the `gp-0x6bb2` cluster nor `FUN_0004613e` can bind, limit, or shape the control
signal — it is a pure computation-integrity WATCHDOG on the pre-existing ±512 ceiling, feeding (if
tripped) a diagnostic log only. It CANNOT be the source of a rate-limiting-induced limit cycle**, since
it has no forward path back into `gp-0x6bbe` or any other live signal (it only OVERWRITES its own
private cross-tick tolerance-check state).

**⚠ Safety flag (new, not previously documented):** `FUN_000462e6` is the SAME function documented in
[[reference-accord-consistency-monitor-hardshutdown]] as "Monitor 2 float watchdog," which dispatches via
`FUN_00016de6(0x1d, tag, 1, 1)` into the hard-fault-eligible latch chain (→ `FUN_00018738` →
`gp-0x685c` DTC latch → `FUN_00019f7c` → motor-off). That memory found Monitor 2's OWN accumulator
gated permanently off (`tp+0x74a4=0xEA`) — **but `FUN_00035154`'s call to `FUN_000462e6` is a
SEPARATE, DIRECT call site, NOT gated by `tp+0x74a4`** (verified: no gate check between the tolerance
compare at `0x3525e-62` and the call at `0x35270`). **Any build edit that changes `gp-0x6bbe`'s ceiling
math in `FUN_00034a72` without correspondingly updating `FUN_00035154`/table `0xD2018` risks tripping
this hard-shutdown-eligible path** (assuming fault index 0x1d's hard-fault-eligible bits, already
established for Monitor 2's use of the same index, apply here too — not independently re-verified this
session for THIS specific tag).

## (b) Angle-rate tributary (gp-0x6a56) — NO rate/slew limiter; MAJOR finding on its identity

[MEASURED] `search_instructions` for ALL writers of `gp-0x6a56` image-wide (mnemonic=st.h, pattern=6a56):
**exactly 4 hits, ALL inside `FUN_0003f776`** (`0x3f7b8`,`0x3f7d0`,`0x3f7e0`,`0x3f81e`), confirmed
`truncated:false`. `FUN_0003f776` is the SOLE producer of `gp-0x6a56` — called from `FUN_00022ca0` at
`0x22de2` (same task, runs BEFORE `FUN_00034a72`/`FUN_00035154` each tick).

```c
// 0x3f77e-0x3f7ea, NORMAL path (gp-0x6abe <= 12936, the common case):
iVar4 = polarity(gp-0x6752) * ((gp-0x6abe * 48 * cal(tp+0x713a)) >> 15)     // Q15 scale of MOTOR RATE
gp-0x6a56 = clamp(iVar4, -12000, +12000)          // fresh MAGNITUDE clamp every tick, NOT a delta/rate limit
// RARE path (gp-0x6abe > 12936, edge case near that channel's own ceiling): gp-0x6a56 forced to 0
```
**`gp-0x6a56` ("steering angle rate" in all prior memory) is NOT an independently-sensed quantity — it
is ENTIRELY SYNTHESIZED from `gp-0x6abe` (motor/resolver electrical rate, itself an EMA of raw
`gp-0x4f50` per [[reference_accord_fun41464_sign_filter_phase_response]]), via a FIXED scale factor
(`48 * cal(tp+0x713a)`, Q15).** This is a genuinely new correction to the whole angle-rate-tributary
investigation: `gp-0x6a56` and `gp-0x6ba6`/`gp-0x6b9a`'s "Branch A" (also `gp-0x6abe`-derived, per
[[reference_accord_gp6bbe_baseline_fsm_and_lerp_struct_solved]]) trace to the SAME ROOT SOURCE. This
means `baseline`'s slow branch and `angle_rate_raw` in `rate_error = baseline - angle_rate_raw` are NOT
independent — they are correlated copies of the same underlying motor-rate signal through different
scale/filter pipelines, which would produce SUBSTANTIAL PARTIAL CANCELLATION at the frequencies where
both pipelines still agree in phase. Flagging as a MAJOR follow-up item, not fully chased this session
(needs the two pipelines' relative gain/phase compared directly).

**No rate/slew limiter exists here** — the ±12000 bound is a magnitude clamp recomputed fresh from
`gp-0x6abe` every tick, with no reference to `gp-0x6a56`'s own prior value in the clamp math (only the
`sVar1==sVar2` shadow-consistency check references history, and that's redundancy verification, not
rate limiting).

## (c) gp-0x6a60 — NOT its own clamp/rate-limiter; mirrors gp-0x6a56's magnitude only

[MEASURED] Full disasm `0x3f7f6-3f800`: `gp-0x6a60 = min(abs(iVar4_clamped), 0xffff)`. Since
`iVar4_clamped` is already bounded to ±12000 (from (b)), `min(abs(x),65535)` NEVER binds — it is a
dead safety-net. **`gp-0x6a60` = `abs(gp-0x6a56)`, full stop; the "±12000 clamp" belongs entirely to
`gp-0x6a56`.** Not a rate limiter under any reading. `gp-0x6a60` is a genuine, LIVE consumer signal
though — used by the decider (`FUN_00040d58`) as `RATE_GATE` bit4 at threshold `0xC6310=1600` (per
`build_v31p_tva.py`/`build_v31p_v2_tva.py`, existing V31P telemetry read, NOT a proposed lever). 1600
is only 13.3% of the 12000 clamp ceiling — supports that `gp-0x6a56`/`gp-0x6a60` rarely approach
saturation in ordinary driving; whether they approach it during the team-lead's specific rail/ratchet
event is unmeasured.

## (d) No other delta-based limiter found in FUN_00034a72

Full re-scan of the already-traced function: the only "delta" arithmetic is (a)'s cross-tick tolerance
check (a monitor, not a limiter) and the `rate_error = clamp(baseline - angle_rate_raw, ±12000)` term
(a magnitude clamp on a computed instantaneous difference, not a cross-tick rate limit). No other
candidate found.

## The ONE real, LIVE rate limiter found on the assist path: FUN_00042af8 shaper slew, DISABLED in stock

Pre-existing memory [[reference-accord-slew-limiter]]/[[reference-accord-shaper-fun42af8]] (not
rediscovered, cited): `FUN_00042af8` (`gp-0x6b98` LKAS-demand shaper) has a genuine incremental-ramp
slew limiter, `prev += clamp(target-prev, ±step)`, `step = cal tp+0x71d6 = 0xC61D6`. **[MEASURED, fresh
byte-read this session] `0xC61D6 = 0x0000 = 0` on current stock `code.bin`** — step is ZERO, so the
limiter does not ramp; per that memory it "hard-zeroes and holds" (the documented "EME amplifier"
shape: hard cut + hold + jump-back on recovery) — structurally the textbook rate-limiter-induced
limit-cycle shape the team-lead's measurement points at.

**🛑 Already proposed once, status UNCLEAR — do not treat as untested.** `analysis-2020accord/
old_tools/build_v16_tva.py` (an OLD, pre-current-numbering build script, NOT in the current
`build_v9..v57` lineage) sets `0xC61D6: 0 -> 14` bundled into a multi-fix tag ("LKAS-2x-EMEfix-slew-
deadband-ramp-PNfix"). **This address does not appear anywhere in current `docs/BUILD-LINEAGE.md`** —
I cannot find an on-car verdict for this specific lever in the current lineage record. This needs the
operator to clarify whether V16 (old numbering) was ever actually flashed/tested and what happened,
before it's treated as a fresh, unflashed candidate.

## Related
[[reference_accord_gp6bbe_baseline_fsm_and_lerp_struct_solved]] — established gp-0x6abe as Branch A's
input to baseline; this session ties the SAME gp-0x6abe to gp-0x6a56's entire identity.
[[reference_accord_fun41464_sign_filter_phase_response]] — gp-0x6abe/gp-0x6ac0's own producer and phase-
gating (5/16 ticks), upstream of both baseline's Branch A and gp-0x6a56.
[[reference-accord-consistency-monitor-hardshutdown]] — FUN_000462e6/FUN_00016de6's hard-shutdown latch
chain, reused here to flag FUN_00035154's direct (ungated) call into the same path.
[[reference-accord-slew-limiter]] / [[reference-accord-shaper-fun42af8]] — the real shaper slew limiter,
cited not rederived.
