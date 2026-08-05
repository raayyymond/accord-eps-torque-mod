---
name: reference_accord_gp6b26_friction_lane_damping_candidate
description: gp-0x6b26 (FUN_00036c12, "friction comp") is a 1kHz, velocity(motor-rate)-proportional, sign-clean aggregator lane not yet touched by any build script (RULE-4 byte-diff confirmed virgin across all 67 built images) -- the kit's top candidate for adding 21Hz damping. FINAL SIZED LEVER (2026-08-05): 0xD2A44 Y-values x1.5-2.0 paired with 0xC407E 511->850-1024; GATE 2 clean at every tested rung (45Hz suppressed 1.5-2.9x harder than 20.9Hz, no sign flips); manual-feel cost is a transient quick-input catch concentrated at parking speed, not steady heaviness. Phase (fs=1000Hz, corrected from an earlier 312.5Hz error): cos=-0.63@20.9Hz, cos=-0.96@45Hz.
metadata:
  type: reference
---

# Ranking the aggregator lanes for 21Hz damping authority — 2026-08-04, team-lead task-rate/damping-authority mission

## 🛑 CORRECTION (same session): the friction lane's phase is much better than first computed

My first pass below used [[reference-accord-four-unprobed-lanes-abcd-solved]]'s claim that `gp-0x6c2c`
is fed directly by "raw resolver rate `gp-0x4f50<<5`" through a single EMA (alpha=22/64) — i.e. TWO
PARALLEL EMAs, no derivative stage. **Fresh `decompile_function(0x41464)` this session (full read, not a
summary) shows that claim is wrong.** The real data flow is:
```
uVar16 = EMA(gp-0x4f50 * 1024, alpha=cal(tp+0x743c)=37/128, >>7)   # this IS the gp-0x6abe/6ac0 stage-1 state
iVar14 = clamp((uVar16[n] - uVar16[n-1]) * 32, +/-0xfa0000)        # discrete derivative of the EMA'd rate
gp-0x6c2c = EMA(iVar14, alpha=cal(tp+0x50dc)=22/64, >>6) >> 9      # 2nd EMA, on the DERIVATIVE not the raw rate
gp-0x6c2e = EMA(iVar14, alpha=cal(tp+0x50da)=3/128,  >>7) >> 9     # sibling, weaker pole
```
This is exactly the **cascade** structure the *original* (2026-07-29) lane-table memory described (EMA ->
derivative -> EMA) — my Python reproduction of that memory's own recorded per-stage numbers at 21Hz/312.5Hz
matches to 3 decimals (stage1 0.633/-39.65deg, derivative-shape 0.419/+77.9deg, stage2 0.712/-33.85deg,
combined 0.189/+4.4deg — all reproduced exactly). **The "four-unprobed-lanes" session's "correction" to a
parallel-EMA model was itself the error**, most likely a misread of `iVar14` as the raw input. Flagging
that file for review rather than silently editing it.

**At 20.9Hz** (this session's own target frequency, not 21.0): stage1 -39.6deg, derivative shape +78.0deg,
stage2(22/64) combined -> **|H|=0.189 (-14.5dB), phase = +4.6deg** vs raw `gp-0x4f50` — i.e. **almost NO
net phase distortion**, because the derivative's lead very nearly cancels the two EMAs' lag at this
specific frequency. Since the lane's own static gain (`sVar7`, the `0xD2A44` LERP) is confirmed **always
negative** (per [[reference_accord_friction_lane_fun36c12_smooth_no_stickslip]], a concurrent session's
fresh disasm of the SAME function this session also touches), the lane's total phase vs raw motor rate is
`4.6 + 180 = 184.6deg` (equivalently -175.4deg) — **`cos(184.6deg) = -0.997`, essentially a textbook -180deg
viscous damper with almost no added lag.** Adding the (unaffected-by-this-correction) 1kHz-task-samples-a-
312.5Hz-signal ZOH (avg 12.0deg / worst 24.1deg, computed earlier in this file) gives a total range of
**-151deg to -199deg** vs raw motor rate — `cos` ranges **-0.875 to -0.946** — i.e. still close to ideal
damping phase across the whole ZOH uncertainty band. **This lane's phase margin is the strongest of any
candidate examined this session, materially better than my original -45.7deg estimate.** The magnitude
(-14.5dB) and untested-lineage status below are unaffected by this correction.

## Why `gp-0x6b26` (Lane C, `FUN_00036c12`, "friction comp") ranks #1

Confirmed this session (`get_function_callers`): sole caller `FUN_0002214a` = **1000 Hz**, live-verified,
not relayed. Per [[reference-accord-four-unprobed-lanes-abcd-solved]] (prior session, re-used and
cross-checked here): `gp-0x6b26 = clamp(((gate(gp-0x6c2c) * Y_speed) >> 6) * 273 >> 18, +/-511)`.
`gp-0x6c2c` is a filtered **MOTOR RATE** (not torque) — a parallel EMA (alpha=22/64=0.34375, cal
`0xC40DC`=22) off the same raw resolver-rate input `gp-0x4f50` that feeds the common-mode bus, computed
inside `FUN_00041464` at the same phase-gated 5/16 schedule (fs_eff=312.5Hz). `Y_speed` is a 3-point LERP
`0xCBE74`->index10->`0x0D2A44`, X=[0,20,90]km/h, **Y=[-9830,-5734,-1966] — ALL NEGATIVE** -> the term is
`-K(speed) x motor_rate`, a genuine **viscous damper**, sign OPPOSING (net-damping verdict from the prior
session, sign convention inferred from the all-negative table + no separate sign flip, not independently
re-derived this session).

**Phase at 20.9Hz, recomputed this session with exact z-domain single-pole EMA + ZOH formulas** (mirrors
the decompiled integer recurrence, cross-validated against the prior session's hand/sim figures at 21Hz to
within 0.2deg):
```
EMA (alpha=22/64, fs_eff=312.5Hz, f=20.9Hz):        |H|=0.7131 (-2.94dB), phase=33.7 deg lag
ZOH (1kHz task reads a 312.5Hz-updated gp-0x6c2c):   avg 12.0 deg, worst 24.1 deg
------------------------------------------------------------------------------------
COMBINED:                                            avg 45.7 deg, worst 57.8 deg lag
```
`cos(45.7deg)=0.70`, `cos(57.8deg)=0.53` — **69-70% (avg) of ideal damping authority retained, nowhere
near the 90deg flip point.** This is a materially healthier phase margin than the FactorC/E base damper's
81.8/119.4deg at the same frequency (see [[reference_accord_task5_100hz_live_verified_full_producer_census]]),
because this lane runs at the full 1kHz rate, not 100Hz.

## Lineage check — GENUINELY UNTESTED [EVIDENCE, mandatory before naming any lever]

`grep -l "D2A44\|CBE74\|C407E" analysis-2020accord/build_v*_tva.py` = **0 hits across all 71 build
scripts.** `grep -l "C618A\|C627E"` (the return-centre lane's cals, see below) = **0 hits** too. Neither
lane's calibration cells have ever been named by any build script in this kit's history — confirmed by
direct grep this session, not inferred.

## Open items before this can be a build proposal

1. **Headroom NOT computed.** `gp-0x6c2c`'s exact scale relative to `gp-0x6ac0` (the kit's standard
   4.7121 counts/deg-s motor-rate reference) was not resolved this session — needed to compute what
   fraction of the +/-511 output clamp is used at grind #1's characterized operating point (`gp-0x6ac0`
   rateKey ~603 counts, per [[accord-v69-flew-dose-response-non-monotone]]) before raising the LERP
   magnitude, and how much headroom exists before clipping.
2. **Monitor/lockstep exposure of `0xD2A44`/`0xCBE74`/`0xC407E` NOT checked this session.** GATE-1 requires
   this before any build — unlike `gp-0x6bd0`'s ceiling (float twin `0xC6554`, known), this lane's exposure
   is simply unswept, not confirmed clear.
3. **Sign convention is INFERRED, not independently re-derived this session** — inherited from the prior
   session's read of the all-negative LERP table with no additional sign flip found in the combine. Worth
   one more disassembly pass on the final `add`/`sub` at the aggregator combine site before building.
4. Raising the LERP is a **cal-only Y-table edit** (no new instructions added to the 1kHz task body), so
   DTC-0x18's per-task overrun watchdog is not a structural concern the way it would be for a code cave.

## Correction/flag: `gp-0x6b62` (return-centre) ceiling claim needs re-verification

[[reference-accord-four-unprobed-lanes-abcd-solved]] and
[[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]] both state `gp-0x6b62`'s "state gp-0x6a82
moves by exactly +/-1/cycle" implies a **hard slew ceiling of ~7.6 counts at 21Hz** on the lane's OUTPUT.
Fresh `decompile_function(0x36388)` this session shows `gp-0x6a82` is a **debounce/hysteresis STATE
SELECTOR** (`uVar9 = uVar9+1` / `uVar9 = uVar9-1`, gating which of several assignment branches fires,
inside comparisons like `1 < DAT_00006440[gp]`), not obviously the thing that directly bounds the OUTPUT
`gp-0x6b62`'s per-tick step size. The actual output write is `*(short*)(gp-0x6b62) = sVar8 + sVar13` (a
fresh S+T-derived value, ramp-weighted by a SEPARATE variable `gp-0x6990`, clamped [0,32768] with its own
+/-33/tick step per the prior session) each 1kHz tick — behind a shadow-lockstep check against `gp-0x4cda`
(matches the kit's other shadow-lockstep pairs; a mismatch calls a repair handler `FUN_0006b9fa` instead of
updating). **Flagging, not overturning**: the net-damping-by-construction verdict (S/T share sign) still
looks right from this fresh pass, but the specific "<=7.6 counts reachable at 21Hz" amplitude-ceiling
number is NOT re-derived and should not be treated as load-bearing for a build decision without a full
re-trace of the `sVar8+sVar13`/`iVar6`-ramp-weight combine. `gp-0x6b62` is ALSO genuinely 1kHz
(`get_function_callers` confirmed live this session) and its S-term IS a real `-2.5 x filtered-motor-rate`
viscous damper if the amplitude ceiling turns out not to bind as tightly as recorded — worth a follow-up
session's full re-trace before ruling it out as a #2 candidate.

## Ranking for "add 21Hz damping authority," 1kHz-only, r24/r26 excluded per standing constraint

1. **`gp-0x6b26` (friction, `FUN_00036c12`)** — 1kHz, genuinely velocity(motor-rate)-proportional, clean
   opposing sign, phase margin **-151 to -199deg vs motor rate (cos -0.875 to -0.946, near-ideal -180deg
   damper)** per the correction above (supersedes this file's own first-pass 45.7-57.8deg estimate), UNTESTED
   by any build. Top candidate, pending the 3 open items below.
2. **`gp-0x6b62` (return-centre, `FUN_00036388`)** — 1kHz, right sign/shape (S-term `-2.5 x rate`), but the
   amplitude-ceiling claim that downgraded it is UNVERIFIED this session (see correction above) — worth
   re-investigating before ruling out, not before recommending.
3. NOT candidates: `gp-0x6bd0`/`gp-0x6bbe` (100Hz, phase margin thin-to-crossed, boost is reinforcing not
   opposing anyway), `gp-0x6b86` (peak-hold destroys phase), `FUN_00036682`/Lane D (ruled out by magnitude,
   -46 to -58dB), `gp-0x6ad4`/resonance (currently muted; its D-term is structurally the same "unfiltered
   lead, same-signed" shape the operator's r24/r26 constraint is protecting against), `gp-0x6b4c`/LKAS (not
   a controller term, it's the externally-commanded demand itself).

## 🛑★★★★★★ 2026-08-05 follow-up: damps at BOTH 20.9Hz AND 45Hz (team-lead's gain-tilt objection ANSWERED); likely ALREADY CLIPS at grind #1's stock amplitude

Team-lead raised the gain-tilt hazard (this lane's producer `FUN_00041464` is a band-pass peaking near
61Hz, so raising it feeds 40-49Hz ~1.5x harder than 18-22Hz — the exact V62/r24/r26 pathology). Settled by
computing the lane's OWN phase vs raw motor rate directly at both bands (valid because `gp-0x6c2c` is
natively motor-rate-domain, unlike r24/r26's torque-domain `dtorque` — this lane needs NO plant-phase
inference, unlike r24/r26):
```
20.9Hz: cascade +4.65deg -> +180(sign, Y_speed always neg) -> total avg +172.6deg, cos=-0.992 (damping)
45.0Hz: cascade -21.79deg -> +180 -> total avg +132.3deg, cos=-0.673 (still damping)
        worst-case ZOH range at 45Hz: [+106.4,-150.0]deg -- BOTH endpoints stay >90deg (never regenerative)
```
**Falsifiable prediction: raising gp-0x6b26 damps 40-49Hz too (more weakly, cos -0.67 vs -0.99), does NOT
reproduce V62's grind-#2 regression.** Mechanistic reason it differs from r24/r26: r24/r26 sense TORQUE
(upstream of the plant) so inherit the plant's frequency-dependent torque->velocity phase; this lane senses
VELOCITY directly (downstream of the plant) so the plant's phase never enters its own dissipation judgment.

**🛑 NEW HAZARD, [BELIEF/estimate not certified]: the lane likely ALREADY SATURATES its own ±511 clamp
(`0xC407E`) at grind #1's STOCK amplitude, before any lever is applied.** Using the characterized operating
point (`gp-0x6ac0` rateKey ~603 counts @ 20.9Hz, per [[accord-ratchet-characterised-on-route-4f]]-adjacent
memory) and the exact cascade gains: `gp-0x6c2c` amplitude estimate ~11,480 counts -> pre-clamp `gp-0x6b26`
estimate ~1,597 counts, **~3.1x past the ±511 clamp**. Rests on treating 603 as a clean sinusoidal peak —
not independently re-verified this session, flagged not certified. **Consequence: raising the LERP alone
buys little — must be PAIRED with raising `0xC407E` toward the aggregator's own `±0x400`=1024 gate** (which
has real headroom, currently only ~50% used by this lane).

**Monitor exposure INDEPENDENTLY CONFIRMED** (fresh `decompile_function(0x36c12)`, not relayed from F6):
write site is `if (gp-0x6b26==gp-0x4cd0) {gp-0x6b26=iVar5; gp-0x4cd0=iVar5;} else FUN_0006b9fa(...)` — a
**same-domain dual-store RAM-corruption check** (both plain `short`, written the identical NEW value
together, compared against each other's OLD value) — the same shadow-lockstep pattern as `gp-0x6bd0`/
`gp-0x4cf2` and `gp-0x6b62`/`gp-0x4cda` elsewhere in this kit. **NOT** a cross-domain float-recompute check
like `gp-0x6bd0`'s `0xC6554`/DTC-0x1d pair — raising the LERP Y-values does not trip it. Also confirmed the
clamp source in the same decompile: `tp+0x507c+2 = tp+0x507e = 0xC407E`, matching the byte-read 511 exactly.

**Plant-phase side exercise** (not load-bearing for this lane's verdict, done because team-lead asked for a
cross-check method): solving `cos(phase_diff(f) - phase_plant(f))` sign vs V62's r24/r26 dose-response
(`dtorque`'s exact D=4-sample differencer phase, Fs=1000Hz: 74.95deg@20.9Hz, 57.60deg@45Hz) gives two
180-deg-wide plant-phase bands (the honest limit of one sign-constraint per frequency): DAMPING-consistent
`(164.95,344.95)deg` @20.9Hz, REGENERATIVE-consistent `(-32.4,147.6)deg` @45Hz. A crossover-anchored point
estimate (assumes one smooth monotonic pass through the 22-24Hz crossover) gives `plant_phase(23Hz)≈-16.6deg`
— sits at the edge of both bands, consistent with a plant phase roughly FLAT near -15 to -20deg across
21-45Hz, with r24/r26's OWN differencer phase (which genuinely drifts 75deg->58deg) doing most of the work
of flipping the sign. [BELIEF, one extra smoothness assumption, not the only story consistent with the data.]

## 🛑★★★★★★ 2026-08-05, 3rd follow-up: saturation is a CANDIDATE ROOT CAUSE (team-lead's reframing), tightened with the clamp-crossing amplitude

The earlier headroom estimate used `gp-0x6ac0`=603, later flagged by team-lead as a "per-window WORST
INSTANT" statistic already once retracted in this kit for that substitution (see
[[feedback-episodes-not-windows]]). Redid it against the corpus's actual in-burst distribution (p50=104,
p90=254, p99=505) and, more usefully, **solved directly for the clamp-crossing amplitude** — the property
of the LANE itself, independent of any corpus statistic, and directly checkable against telemetry:

```
CLAMP-CROSSING gp-0x6ac0 amplitude: ~180-212 counts (~38-45 deg/s peak motor rate),
                                     STABLE across the whole creep speed band (3-10 km/h)
p50=104  -> 54% of clamp  (linear regime, below crossing)
p90=254  -> 132% of clamp (CLIPS)
p99=505  -> 262% of clamp (deep clip)
V72 measured=614 -> 318% of clamp (deep clip)
```
**The crossing sits between p50 and p90** — the typical/small part of a grind-#1 burst gets real,
proportional damping from this lane; only the upper part of the amplitude distribution saturates it. This
is exactly the amplitude range a describing-function-driven limit cycle would be expected to settle in
(the amplitude where effective damping starts falling off is generally close to where the cycle stabilizes,
not far below it) — **team-lead's reframing: this is a candidate ROOT CAUSE for grind #1's persistence
across ten builds of scalar-gain tuning, not merely a caveat on this lane as a lever.**

**If `0xC407E` raised 511->1024** (matching the aggregator's own `+/-0x400` ceiling, NO LERP gain change):
new crossing amplitude ~387 counts (~82 deg/s) — p50 AND p90 both move into the linear region, only p99
still clips. This reframes `0xC407E` from "a pairing for a gain raise" to potentially **the primary lever**:
surgical, no effect below the (now-higher) clamp, full effect above it, no small-signal gain change at all.

**Caveat carried forward**: p50/p90/p99 are percentiles of a population of instantaneous rate samples
across bursts, not necessarily each burst's own peak — treating each as a representative peak amplitude is
the best available proxy without raw waveform access. The CROSSING AMPLITUDE itself (180-212 counts) does
NOT depend on this caveat — it's a property of the lane's gain chain and clamp alone, solid regardless.

Also: new corpus context from team-lead — grind #1's dose ladder **saturates at ~2.2x excess-over-floor and
never reaches 1.0x** on any build tested, and **V72 measured 614 (squarely stock-band) despite delivering
V67/V68's bit-identical creep gain** — two independent legs now argue grind #1 is NOT a pure scalar-gain
phenomenon, consistent with a saturating element setting an amplitude-independent floor.

## 🛑🛑🛑 2026-08-05, 4th follow-up: `fs_eff=312.5Hz` WRONG -> corrected to 1000Hz, phase and headroom numbers both change

See [[reference_accord_task5_100hz_live_verified_full_producer_census]]'s 3rd-follow-up section for the
full mechanistic finding: the `0xD30` gate on `FUN_00041464`'s call site is a STATE-membership test on
`gp-0x67fa` (per this kit's own [[reference_accord_0x930_masks_are_state_not_phase_settled]]), not a
16-phase duty cycle -- the function runs at the FULL 1000Hz task1 rate whenever the ECU is in a normal
running state. Redid this lane's numbers with `fs_ema=1000` (was 312.5):

```
Cascade (gp-0x6c2c vs raw motor rate), fs=1000Hz:
  20.9Hz: |H|=0.1171 (-18.6dB), phase=+54.92deg   [was +4.65deg @312.5Hz]
  45.0Hz: |H|=0.1813 (-14.8dB), phase=+23.55deg   [was -21.79deg @312.5Hz]
  gain(45)/gain(21) = 1.548 -- MATCHES team-lead's independent trip-amplitude ratio (1.53x) closely,
  cross-validating fs=1000Hz.

TOTAL phase vs raw motor rate (+sign flip, +1kHz-task ZOH -- now nearly negligible since gp-0x6c2c
updates at the SAME 1kHz rate the task reads it):
  20.9Hz: avg -128.8deg, cos=-0.627   [was cos=-0.992 -- STILL damping, but weaker margin]
  45.0Hz: avg -164.6deg, cos=-0.964   [was cos=-0.673 -- STILL damping, STRONGER margin]
```
**Falsifiable prediction UNCHANGED**: raising gp-0x6b26 still damps at both bands, still safe from the
V62/grind-#2 pathology -- the SIGN never flips at either frequency even worst-case ZOH. The MAGNITUDE of
the 20.9Hz margin is weaker than first reported (cos 0.63 not 0.99); 45Hz is stronger (cos 0.96 not 0.67).

**Headroom/clamp-crossing, also corrected -- MATERIALLY LESS SATURATED than first reported**:
```
CLAMP-CROSSING gp-0x6ac0 amplitude: ~425-503 counts (~90-107 deg/s), stable across creep speeds
  [was ~180-212 counts @312.5Hz -- roughly 2.4x higher now]
p50=104 -> 22.7% of clamp (well below)
p90=254 -> 55.5% of clamp (well below -- previously reported as CLIPPING, that was wrong)
p99=505 -> 110.3% of clamp (barely clips)
V72 measured=614 -> 134.1% of clamp (modest clip, was 318% -- far less dramatic)
```
**This substantially softens the "saturation is the root cause" reading**: p50 AND p90 both have real
headroom now; only the extreme tail (p99+) clips, and only modestly. The lane is not "already pinned at
the resonance" the way the 312.5Hz-based estimate suggested -- raising the LERP gain should deliver real
additional authority across most of the grind-#1 amplitude distribution before any clamp is relevant.
`0xC407E`->1024 still helps (pushes crossing to ~917 counts, clearing p99 too) but is no longer the
load-bearing "must-pair" item the earlier estimate implied -- a gain raise alone now has real headroom.

## 🛑★★★★★★ 2026-08-05, 5th follow-up: LEVER SIZED — 1.5-2.0x + 0xC407E->850-1024, GATE 2 clean, feel cost characterized

Team-lead asked for the paired gain+clamp lever sized, GATE 2 stated as an explicit prediction, the
manual-feel cost named in advance, and RULE 4 lineage confirmed by byte diff (not source grep). All done
this session; scripts `scratchpad/rule4_bytediff.py`, `scratchpad/lever_sizing.py`.

**RULE 4 byte diff [EVIDENCE]**: read stock + diffed against ALL 67 built `_*_plain_image.bin` snapshots
for `0xD2A44` (18B full record), `0xCBE74` (44B, covers the mode-10 pointer slot), `0xC407E` (2B),
`0xC407C` (2B). **Zero differences, all 67 images, all 4 regions** — genuinely virgin, confirmed by the
byte-diff method RULE 4 requires, not just F6's grep.

**Lever ladder at 20.9Hz** (multiplier on `0xD2A44`'s Y-values, delivered = min(pre-clamp,511)):
```
        p50(A0=104)   p90(A0=254)          p99(A0=505)          0xC407E needed for p99 clear
1.0x    116 clear      284 clear            564->CLIPS@511       564  (<1024 OK)
1.5x    174 clear      425 clear            846->CLIPS@511       846  (<1024 OK)
2.0x    232 clear      567->CLIPS@511(111%) 1127->CLIPS@511      1128 (EXCEEDS aggregator's 1024 ceiling)
3.0x    348 clear      851->CLIPS@511(167%) 1691->CLIPS@511      1692 (EXCEEDS 1024)
```
**1.5x is clean** (whole p50-p99 range clear with `0xC407E`~846). **2.0x is the edge** (p90 starts
clipping even before `0xC407E`; clearing p99 needs 1128, past the aggregator's own `±0x400` ceiling which
binds first). **Recommend 1.5-2.0x paired with `0xC407E`~850-1024.**

**GATE 2, explicit falsifiable prediction [EVIDENCE, computed at every rung]**: delivered-damping-torque
ratio (45Hz/20.9Hz, `min(pre-clamp,511)*|cos(phase)|`) at 1.0x/1.5x/2.0x × p50/p90/p99 = **1.54x to 2.88x,
every cell >=1.0, no sign flips found anywhere tested.** Raising this lane suppresses 40-49Hz 1.5-2.9x
harder than 18-22Hz, monotonically, across the whole ladder — the opposite of the r24/r26/V62 pathology.
Scope limit: uses grind-#1's own amplitude percentiles as a proxy at 45Hz too (no grind-#2-specific
amplitude data available) — isolates the LANE's magnitude+phase behavior, not a claim about real 40-49Hz
on-car amplitudes.

**Manual-feel cost, characterized not just flagged**: at actual driver hand-steering rates (0.3-5Hz, NOT
the 21/45Hz grind bands), the cascade is deeply attenuated (-30 to -54dB vs its 21Hz gain) and sits near
90deg phase (quadrature, not the damping-aligned ~180deg it has at 21/45Hz) — DC gain -> 0 exactly (the
derivative stage kills a truly steady turn rate). **A smooth, deliberate low-speed maneuver should feel
close to unchanged even at 2x.** The real cost is a **brief transient "catch" at the onset of a FAST,
jerky steering input** (its higher-frequency content reaches nearer where this lane's gain rises),
concentrated at parking speed since `Y_speed` peaks at 0km/h and falls ~5x by 90km/h — should be
essentially gone by highway speed. Different character from V72's friction/breakaway offset (a roughly
constant, rate-independent DC effect) — name it to the operator as "momentary extra resistance on quick
low-speed steering inputs," not a general steering-weight change.

## Related
[[reference_accord_task5_100hz_live_verified_full_producer_census]] — the live task-rate verification this
ranking depends on.
[[reference-accord-four-unprobed-lanes-abcd-solved]] — source of the friction-lane and return-centre
structural characterization this file extends/partially corrects.
[[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]] — the 11-lane table this ranking covers.
