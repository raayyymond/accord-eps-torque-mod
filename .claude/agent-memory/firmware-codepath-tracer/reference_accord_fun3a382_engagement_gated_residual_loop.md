---
name: reference-accord-fun3a382-engagement-gated-residual-loop
description: "★★★★★ FUN_0003a382/gp-0x6ad4 (the 'resonance'/residual lane, already known UNFILTERED at stock cal) is a genuine feedback loop whose REFERENCE MODEL and OUTPUT BOUND both change with engagement-linked state — gp-0x67ab gates whether the model (gp-0x6ad6) includes the LKAS-derived term gp-0x6b70; gp-0x67fe (assist substate 0/1/2) directly switches the loop's output bound between a fixed cal and a dynamic, AUTHORITY(gp-0x6966)-scaled bound. Also resolves gp-0x69aa's identity (governor low-speed-gated Q15 voting product) and closes the FUN_00034350 damper's engagement-gating question (NEGATIVE — no engagement-linked damping reduction found)."
metadata:
  type: reference
---

# FUN_0003a382 engagement-gated residual/observer-error loop — traced 2026-07-26

Tasked by team-lead to find engagement-gated elements sitting in a FEEDBACK path (as opposed to a pure
feedforward setpoint), motivated by on-car evidence
([[reference-accord-vibration-requires-lkas-engaged]]) that the 21Hz vibration exists only while
openpilot commands LKAS (9200x less 21Hz power disengaged), which falsified every prior
"always-on base-assist limit cycle" hypothesis. Full fresh decompile of `FUN_0003a382`,
`FUN_00037fe6`, `FUN_0004503c`, and `FUN_00034350` on `_vfourframe_plain_image.bin` (V38 cal + passive
telemetry cave, gp=0xFEDF8000, tp=0xBF000). Builds directly on
[[reference-accord-fun3a382-resonance-lane-unfiltered-correction]] and
[[reference-accord-fun352b4-peakhold-correction-and-fun3a382-stageA-pole]] (both already established
Stage A/B/C ≈ unity gain / effectively unfiltered at stock cal `0xC6450=0xC644A=1024`) — this session
adds the ENGAGEMENT-COUPLING half of the picture those files didn't investigate.

## [VERIFIED] The model term gp-0x6ad6 is gated `gp-0x67ab`, and includes the LKAS lane when live

`FUN_00037fe6` (writes `gp-0x6ad6`, decompiled in full):
```c
iVar4 = 0;
if (in-range(gp-0x6b4a)) iVar4 = -gp-0x6b4a;              // ALWAYS included, negated
if (reduce(gp-0x67ab) != 1) {                              // gate: v*(v<2)==1, i.e. v==1 exactly EXCLUDES
    iVar4 += gp-0x6bc2*w(tp+74ae) + gp-0x6b60*w(tp+74b2) + gp-0x6b2a*w(tp+74b3)
           + gp-0x6bce*w(tp+74ad) + gp-0x6b6e*w(tp+74b1) + gp-0x6bbc*w(tp+74af)
           + gp-0x6b70*w(tp+74b0);   // <- gp-0x6b70 = FUN_00038148(gp-0x6b4c[LKAS], gp-0x6b4e), per
}                                     //    [[reference-accord-gp6b4c-lane-chain]]
uVar3 = gp-0x69aa<0x8001 ? LERP(flat-extrap table @tp+0x7aba..0x7ad8, gp-0x69aa) : cal(tp+0x7448);
gp-0x6ad6 = clamp(iVar4*uVar3>>10, ±0x6400);
```
So the "idealized command model" that `FUN_0003a382` subtracts from the real sensor is, when
`gp-0x67ab != 1`, a 7-lane weighted sum that DIRECTLY includes the LKAS-mixer-derived `gp-0x6b70` term.
When `gp-0x67ab == 1`, the model collapses to just `-gp-0x6b4a`.

`gp-0x67ab` and its near-twin `gp-0x67ac` (the already-known wholesale aggregator-lane-suppression gate,
[[reference-accord-gp67ac-aggregator-lane-suppression-gate]]) are BOTH written in `FUN_00026c80`
(the mixer), at adjacent code (`0x2772a/0x2773a` for `67ac`, `0x2774c/0x2775c` for `67ab`), both sourced
from the SAME 11-channel classification loop (`0x271de-0x27304`) over channel array `tp+0x5124` —
specifically **the LAST-processed channel's (index 10) "mode class" test**. Byte-read `tp+0x5118`
(companion 11-byte table, one per channel): `01 01 01 01 01 01 01 01 01 01 01` — every channel's class
byte is `1`, never in `{2,3,4}`, so the test ALWAYS falls through to a **RUNTIME RAM flag array**
`gp-0x617c[channel]` (feeds `r22`→`gp-0x3d98`→`gp-0x67ac`) / a closely-related computation feeding `r11`
→`gp-0x3d94`→`gp-0x67ab`. **The producer of `gp-0x617c`/`gp-0x6170` was NOT traced this session — the
semantic trigger for these two gates remains OPEN**, same as the pre-existing memory's conclusion, but
now narrowed to a specific RAM address instead of "unresolved in the mixer's dense dispatch logic."

## [VERIFIED] The loop's own output bound is switched on `gp-0x67fe` (assist substate 0/1/2)

Inside `FUN_0003a382` itself (decompiled in full, address-anchored):
```c
if (reduce(gp-0x67fe)==0) {                 // v*(v<3)==0, true for v==0 (or v>=3, unreachable per producer)
    iVar9 = cal(tp+0x71fc);                 // FIXED bound
} else {                                    // gp-0x67fe in {1,2}
    bVar1 = (iVar9_prev_select + 0x3200) < 0x6401;   // range check
    iVar9 = bVar1 ? sVar14 : uVar16;         // sVar14 = 3-way select over gp-0x6bda vs 3 cal constants
                                              // uVar16 = CAN/consistency-validity-derived fallback
}
...
uVar21 = gp-0x6966;                          // = AUTHORITY, read directly at 0x3a632 (ld.hu -0x6966,gp,r11)
uVar12 = uVar21<0x8001 ? LERP(table tp+0x7af2..0x7b04, uVar21) : 0x8000;
iVar20 = ((iVar9_or_select * gp-0x3678_persisted)>>15) * uVar12/0x8000;   // AUTHORITY-scaled term
...
uVar22 = clamp(gp-0x6ad6, ±cal(tp+0x7200)=8192);       // the already-known clamp
errorterm = clamp(gp-0x4f60 - uVar22, ±0x2800);
[Stage A/B/C, unity-gain per prior memory] -> iVar28
gp-0x6ad4 = clamp(iVar28, ±iVar9)   // iVar9 = the gp-0x67fe-switched bound from above
```
`gp-0x67fe` is confirmed the FOC-mode-derived assist substate (producer `FUN_0003bd7c`, per
CLAUDE.md/`v31p-gateflags` record) — **60 raw hits image-wide** (search_instructions), read by nearly
every base-assist lane producer: `FUN_00034350`(damping), `FUN_00034a72`(boost), `FUN_0003a382`(this
lane), `FUN_00042af8`(shaper), `FUN_00043e44`(monitor M2), `FUN_00041eec`(torque fuser),
`FUN_0003d4a2`(hardware phase-disable dispatcher), and ~40 more functions not individually decompiled
this session. It is the single most pervasively-read engagement-substate discriminator in the base-assist
chain, by hit count.

## Net structural picture — a genuine engagement-coupled feedback loop

`gp-0x4f60` (torsion-bar sensor) → compared against `gp-0x6ad6` (model, LKAS-composed when `gp-0x67ab
!=1`) → UNFILTERED Stage A/B/C (unity gain at stock cal, established prior session) → bounded by `iVar9`
(FIXED when `gp-0x67fe==0`, else DYNAMIC + AUTHORITY-scaled) → `gp-0x6ad4` → summed into the SAME
aggregator (`FUN_0003aa2c`) that produces the delivered motor command `gp-0x6b98` (via governor + shaper)
→ physical motor/rack → torsion bar → closes back to `gp-0x4f60`. **Both halves of this loop — the
reference it compares against, and the ceiling on what it's allowed to feed back — are gated by
engagement-linked state (`gp-0x67ab`, `gp-0x67fe`, `gp-0x6966`=authority), while the loop's own gain
stages are the known-unfiltered ones.** This is the strongest candidate found this session for "a loop
that only closes (or whose gain/reference materially changes) when LKAS is engaged," consistent with the
9200x on-car engagement-dependence result.

## [VERIFIED] gp-0x69aa's identity resolved — closes an OPEN item in the prior fun3a382 memory

The prior memory flagged `gp-0x69aa` ("the flat-extrapolated LERP axis in FUN_00037fe6") as "role not
identified." **Resolved this session**: `FUN_0004503c` (the governor, `m_motor_torque_governor`) writes
`gp-0x69aa = (uVar17 * uVar6) >> 15` — the product of two Q15 redundant-sensor-voted factors computed via
the same `FUN_00049a90`/`FUN_00049a78` MIN/clamp chain documented in
[[reference-accord-gp4f64-three-consumers]]. **Both factors are computed through a LOW-SPEED-GATED
smoothing step**: `if (cal(tp+0x7316=0xC6316=640) <= gp-0x6a64) { apply a symmetric slew/bound adjustment
using cal tp+0x7492 } ` — i.e. the smoothing is only APPLIED when voted vehicle speed
(`gp-0x6a64`, confirmed VOTED SPEED not torque per
[[reference-accord-gp6a5e-is-voted-vehicle-speed]]) is **≥ 640 counts = 10 km/h**. Below 10 km/h (the
exact parking-lot regime the vibration was recorded in, route 13, 0-2.7 m/s) this smoothing is skipped
and the raw MIN/clamp output passes straight through into `gp-0x69aa`, which then directly SCALES
`FUN_00037fe6`'s model output `gp-0x6ad6` (see above). **This links the governor's already-documented
low-speed slew bypass to the residual-loop's reference gain — both change character in the same
sub-10km/h band, independently of the engagement question but compounding with it on the tested route.**

## [NEGATIVE RESULT] FUN_00034350 (damping producer) — no engagement-linked damping reduction found

Full decompile matches [[reference-accord-damper-two-deadzones-factorC-factorE]]'s 5-factor structure
exactly (Factor A seed clamp≤1024, B=driver-torque flat-unity/dead per prior finding, C=`gp-0x6a5e`
deadzone — **voted SPEED not torque**, per [[reference-accord-gp6a5e-is-voted-vehicle-speed]], treat that
memory as settled/adopted — D=`gp-0x6a10` angle-deviation, E=`gp-0x6ac0` motor-rate magnitude deadzone).
**NEW this session**: Factor D's LERP is only EVALUATED when `gp-0x67fe==1 or ==2`; otherwise it's forced
to flat unity (`0x400`=1024). This is the only engagement-substate-linked branch found in this function —
but it is numerically a NO-OP today because Factor D's own table (`0xC9DB4`) is flat 1024 at every
breakpoint regardless (already established). **No factor's deadzone is keyed on an engagement flag
directly** — C is speed-gated, E is motor-rate-magnitude-gated. Verdict: engagement does not reduce
damping through this producer; not a supporting mechanism for "vibration only when engaged."

## Ranked cal-only test proposal (unchanged target, new justification)

`0xC6450` (tp+0x7450, Stage A's pole in `FUN_0003a382`) `1024 → 32`. Single reader (`0x3a7f0`), no
lockstep/shadow pair, no float mirror (re-confirmed [[reference-accord-fun352b4-peakhold-correction-and-fun3a382-stageA-pole]]).
Converts Stage A from an exact-identity passthrough to a ~4.8Hz first-order low-pass (~12-13dB cut at
21Hz) WITHOUT touching the engagement-gated model (`gp-0x6ad6`/`gp-0x67ab`) or bound (`iVar9`/`gp-0x67fe`)
structure documented above — keeps the experiment attributable to filtering the loop's gain, not to
disabling its engagement-coupling. Not built or flashed this session.

## [CORRECTION 2026-07-26, later same day] Team-lead found the sharper lever inside this same lane — authority, not the Stage-A pole

**The `0xC6450` cal-only test proposed above is ALREADY FLASHED AND FALSIFIED — it is `builds/v18_v49/build_v46_tva.py`
verbatim** (`STAGEA_ADDR=0xC6450`, `1024→32`, same predicted effect, `_v46_plain_image.bin` confirms
`0xC6450=32`). CLAUDE.md already recorded this once ("V46 FLASHED... LEVER A FALSIFIED") and this is the
**second time** an agent re-proposed it — see [[feedback-check-build-scripts-before-proposing-cal-edit]].
**Lesson: grep `analysis-2020accord/build_v*_tva.py` for any candidate address BEFORE proposing it.**
`0xC644A` is likewise already-flashed (V43, also null) — same trap.

Team-lead's own corrected byte scan (mine undercounted — hit the `hw2=disp|1` trap for `ld.hu`/`ld.w`)
found the REAL lever: **`gp-0x6966` (AUTHORITY) has exactly 6 access sites in the whole image — 1 store
(`0x432c8`, inside `FUN_00042af8`, AUTHORITY's producer), 4 monitor reads, and EXACTLY ONE command-path
read: `0x3a632`, inside `FUN_0003a382`** (the same lane documented above). The LERP table it indexes,
`tp+0x7af0 = 0xC6AF0` (X `0xC6AF2..0xC6AFA`, Y `0xC6AFC..0xC6B04`):
```
X (authority):     0    3277    3604   19661   32768
Y (Q15 gain)  : 32768   32768       0       0       0
```
**Mechanism refinement (I had this wrong in the paragraphs above — authority does NOT gate the errorterm
computation, it gates the lane's OUTPUT BOUND):** `gp-0x6ad4 = clamp((StageA+StageB+StageC combine), ±
iVar9)`, where `iVar9`'s magnitude is multiplied by this authority-gated Q15 factor. Below authority 3277
the clamp is wide open; above 3604 it collapses to a zero-width window and the lane's full P+I+D response
is discarded regardless of magnitude — a saturating output clip, not a linear input gain. errorterm itself
(`gp-0x4f60 − clamp(gp-0x6ad6,±8192)`) is authority-independent.

**Phase, computed exactly at fs=1000Hz (confirmed sole caller), 21Hz:** Stage A (proportional, gain
∝ L1∈[153,256] via 0xC6B20, motor-rate-indexed) = 0° phase; Stage B (integrator, L2=98/1024 flat,
0xC6B0C) = |H|=0.726, **−86.2°**; Stage C (derivative, L3=2.0 flat, 0xC6AE0, own smoothing also unity in
this build) = |H|=0.264, **+86.2°**. Vector sum is **proportional-dominated (8–10:1 over I+D combined)**
with only **−3.3° to −5.4° net phase lag** across L1's full range — the I and D terms nearly
phase-cancel each other rather than adding a large net shift. This is a firmware-side fact I stand behind.
**What I could NOT determine**: whether this constitutes net damping or anti-damping AT THE PLANT'S
resonance requires the mechanical phase relationship between commanded torque and resulting torsion-bar
torque at 21Hz (the plant transfer function) — not obtainable from firmware. A force near-in-phase with
sensor DISPLACEMENT (not velocity) is classically a stiffness term, not a damping term, in a simple 2nd-
order picture; whether the small computed lag rotates enough into a velocity-like component to matter,
and its sign, is genuinely open. Flagged to team-lead as moderate-high confidence the lane MATTERS, low
confidence on its SIGN — closing that needs either FOURFRAME telemetry on `gp-0x6ad4` directly or an
on-car system-ID measurement.

**Authority's runtime range** — resolved via `builds/v18_v49/build_v19_tva.py`/`builds/v18_v49/build_v31_tva.py` (the ORIGINAL soft-EME
docs, not re-derived from scratch): `gp-0x3570` (the integrator AUTHORITY is computed from,
`gp-0x6966=(|gp-0x3570>>15|×1092)>>10`) has exactly 3 accesses, ALL inside `FUN_00042af8` (`0x43214`,
`0x4327c`, `0x432de`) — entirely self-contained in the shaper/M1 function alongside AUTHORITY's own
producer at `0x432c8`. **V19's build script documents SM2's arming threshold as `0xC6422=16384`,
condition `|integrated cmd|×1092/1024 > 16384`** — the SAME `×1092>>10` scaling as `gp-0x6966`, i.e. SM2
arms when authority (or its immediate pre-shift precursor) crosses 16384, **4.5× above the 3604 mute
knee**. V31's docs further establish this integrator winds up specifically on SUSTAINED/HELD LKAS
commands (corridor gate opens off during a driver-override-free hold → boundary collapses toward
boost/IIR floor → command exceeds it → integrator winds up) — authority is BY DESIGN expected to climb
into the high-thousands/16384+ range during ordinary sustained engagement. **Inference: this lane is
very plausibly MUTED for a large fraction of any drive where LKAS is holding a steady command**, and only
live during ramp-up, low-authority, or (plausibly, NOT traced this session) low-speed-lockout conditions
where `gp-0x6806`/`gp-0x69b0` are killed — that specific causal link (`gp-0x69b0`, which lives entirely
in the engage-SM `FUN_00028ea6`, to `gp-0x3570`/`gp-0x6966`, which live entirely in `FUN_00042af8`) is
NOT traced/confirmed, flagged OPEN.

**Safety review of "flatten 0xC6AF0's Y to 32768"**: table is inside the standard `[0xC6000,0xC6FFC)`
main cal block (safe location); single reader confirmed (`search_instructions` on `7af0`, one real hit,
three branch-target-text false positives excluded); `gp-0x6966` IS one of M2's (`FUN_00043e44`, fully
decompiled this session) 7 weighted fault-score flags — checked for self-consistency against a
`gp-0x6b0a`-derived, `tp+0x71da`-scaled expected value at the SAME instruction (`0x44230`) that
`builds/v18_v49/build_v22_tva.py` previously hijacked as a code-cave insertion point (V22's flash status not found in
CLAUDE.md/docs — flagging as prior art, not a resolved precedent) — but this check is independent of
`FUN_0003a382` and unaffected by the proposed edit. `gp-0x6ad4`/`gp-0x6ad6` do NOT appear anywhere in
M2's decompiled body — no independent float model of this lane exists in the monitor. **NOT fully
closed**: `gp-0x6acc` (downstream aggregate, numerically includes this lane's contribution) IS read by
M2 for other flags; whether keeping the lane live longer could push those flags toward tripping was not
resolved (would need the same depth of pass on M1/`FUN_00042af8`, not done this session). One clean
positive: the edit touches nothing in `gp-0x3570`/AUTHORITY's producer/SM1-3, so it **cannot change when
a soft-EME cut fires** — the only open question is the `gp-0x6acc`-vs-M2 interaction.

## [★★★★★ 2026-07-26, THIRD pass] CONFIRMED — the reference model gp-0x6ad6 carries the V38 4× LKAS gain

Team-lead's hypothesis, verified end to end: **the 4×-scaled LKAS command is present in the reference
model this loop regulates against, at full (unity) weight, undiminished relative to the other 6 summed
lanes.** Full chain, byte-verified on `_vfourframe_plain_image.bin`:

1. `0xC646C` (the LKAS arb gain) reads **3564 = 4×891** in this image. The multiply happens at `0x2a1ee`,
   inside `FUN_00028ea6` (arbitration, `0x28ea6-0x2a30d`), **before** the `gp-0x6b3c` write at `0x2a2ea` in
   the same function — strictly upstream of `gp-0x6b3c → limit_and_pack clamp → mixer → gp-0x6b4c`.
2. `limit_and_pack`'s clamp (`tp+0x71b2/0x71b4 = 0xC61B2/0xC61B4`) reads **2048, 2048** in this image —
   **4× the documented stock 512** — i.e. proportionally raised to match the gain, NOT clipping the signal
   back to stock scale. So `gp-0x6b4c` genuinely carries 4×-scaled magnitude.
3. **`FUN_00038148` (PATH-A) sums gp-0x6b4c[LKAS] with FIVE siblings** (`gp-0x6b4e, gp-0x6b26[friction],
   gp-0x6b46, gp-0x6bd0[damping], gp-0x6bbe[boost]`) — corrects the kit's prior "gain tp+0x73aa" shorthand,
   which undersold this function; it is a 6-lane mixer, not an LKAS-only transform. **All six lane weights
   (`tp+0x73a0..0x73aa`) byte-read = exactly 1024 (Q10 unity)** — no special up/down-weighting of LKAS.
   Overall gain `tp+0x7468=0xC6468=2639`(≈2.58) and EMA lag `tp+0x73ac=0xC63AC=102`(α≈0.0996, **a REAL
   first-order low-pass, ~16Hz corner at 1kHz** — unlike `FUN_0003a382`'s own near-unity Stage A/B/C poles)
   apply to the whole 6-lane sum, not LKAS-specifically. A second stage (unidentified `gp-0x6bfa`/
   `gp-0x6bfe` + a **runtime RAM-resident LERP table** at `gp-0x64b8..gp-0x641c`, unusual — most tables in
   this codebase are static cal) produces the final `gp-0x6b70`, clamped ±cal(0x7200)=8192. OPEN:
   `gp-0x6bfa`/`gp-0x6bfe` identity — doesn't change the weight/sign answer, downstream of where LKAS is
   already summed in.
4. `gp-0x6b70` enters `FUN_00037fe6`'s 7-lane sum (→`gp-0x6ad6`) with weight `tp+0x74b0=0xC64B0=1` (byte) —
   again unity, identical to its 6 siblings (`74ad/ae/af/b1/b2/b3`, all `=1`). **Sign**: no inversion beyond
   the single shared `polarity(gp-0x6752)` multiply inside `FUN_00038148` — added, not subtracted.
5. None of `0xC63A0-0xC63AC`, `0xC6468`, or `gp-0x6b70`/`FUN_00038148` appear in any `build_v*_tva.py` —
   confirmed genuinely untested territory before reporting this.

**Nuance for causal interpretation**: PATH-A's ~16Hz EMA attenuates 21Hz AC content in the LKAS command
(~−3 to −6dB, 50°+ lag) before it reaches the reference, but passes DC/slow-varying magnitude through at
unity (EMA property). **⇒ the likely mechanism is the 4× gain shifting the reference model's steady
operating point / which LERP breakpoints & clamp regions the downstream (near-unfiltered)
`FUN_0003a382` machinery sits in — NOT a directly-injected 21Hz ripple.** This is a materially different,
more defensible story than "4x gain = bigger 21Hz signal in the loop," and is consistent with why V43/
V46/V52C (all signal-domain filters) were null: if the effect is a gain-scheduling/operating-point shift,
none of those builds would have touched it.

## [★★★★★ 2026-07-26, FOURTH pass] gp-0x3570's windup driver traced — reads gp-0x6acc, NOT gp-0x6806; found a second, upstream gate on gp-0x6b3c

Team-lead's decisive question: does `gp-0x3570`'s (the soft-EME integrator, produces AUTHORITY
`gp-0x6966`) update read `gp-0x6806`/`STEER_CONTROL_ACTIVE` or the delivered command directly? Traced
`FUN_00042af8`'s windup rule in full (had to extract a window — the whole function is too large to
decompile in one call, ~54K chars):
```
uVar25 = cal(tp+0x71d4)                                       ; default
uVar39 = clamp_zero_type(gp-0x6acc, ±0x2000)                   ; zero-gate: in-range else 0
mode = *(tp+0x74c8)
if (mode != 1) uVar25 = uVar39                                 ; mode 0/2+: gated gp-0x6acc
if (mode == 2) uVar25 = clamp(cal(0x71d4) + uVar39, ±0x3000)   ; mode 2: fixed offset added
[mode 1: uVar25 stays the FIXED cal — gp-0x6acc ignored]
gp-0x6b08 = uVar25                                             ; = "command" for the windup
...
(upper_bound, lower_bound) = polarity-adjusted corridor/IIR/boost 3-way MAX/MIN (matches
  builds/v18_v49/build_v31_tva.py's documented structure exactly)
gp-0x3570 += (command − bound), clamped ±cal(0x71dc)=SM3 trip  [classic anti-windup integrator]
gp-0x6966 = |gp-0x3570>>15| × cal(0x71da)=1092 >>10            [shadow-protected write]
```
**`gp-0x6806` does not appear anywhere in `FUN_00042af8`** (grepped the full decompile). **The integrator
winds on the POST-GOVERNOR aggregate command `gp-0x6acc`, compared against the corridor/IIR/boost bound
— NOT on the engagement flag.** This is now a certain, verified fact, not an inference.

**NEW, UNPLANNED FINDING while tracing backward**: `gp-0x6b3c` (arb's raw output, upstream of everything
in the `gp-0x6ad6` chain documented above) has its OWN separate gate, discovered by disassembling around
its write site `0x2a2ea` in `FUN_00028ea6` (arb): `gp-0x6b3c = (r13==0) ? 0 : r1`, where `r1` is the
**4x-gained, clamped arb curve value** — traced the exact gain application: `0x2a1ee ld.h 0x746c,tp,r7`
[cal=3564 on-car] `→ 0x2a1f6 mulh r7,r13` [×polarity] `→ 0x2a1fe mul r13,r11,r0 → 0x2a202 sar 0xf,r11`
[Q15 shift] `→` clamp `±cal(0x71b4)=2048` `→ mov r11,r1`. **`r13` (the zero-selector) is set by a branch
testing `gp-0x67a4 ∈ {2,3}`** — `gp-0x67a4` is written by exactly ONE place, `FUN_0002b422`
(`m_steer_torque_limit_and_pack`, the pipeline stage immediately after arb) at `0x2b51e`, output of a
small persisted state machine (`gp-0x3d28`, states 0-7ish) gated on `gp-0x67a1`/`gp-0x67a2`/`gp-0x67a3`/
`gp-0x67a7` — none traced to a producer yet. Shape (0→1→3→6→4…, calls `distribute_clamp` each cycle)
reads like a cross-cycle pipeline health/readiness handshake between arb and limit_and_pack. **⇒
`gp-0x6b3c` (hence `gp-0x6b4c`, hence the LKAS content in `gp-0x6ad6`, see the THIRD-pass section above)
is ZEROED unless this separate state machine sits in state 2 or 3.**

**Net honest status on "does low-speed lockout drive authority down":** NOT closed. Two gaps remain: (1)
whether `gp-0x67a1/67a2/67a3/67a7` correlate with `STEER_STATUS`/engagement — untraced; (2) even if the
LKAS component of `gp-0x6acc` zeroes, `gp-0x6acc` also sums friction/boost/damping (driver-torque-keyed,
NOT LKAS-gated per [[reference_accord_g1_governor_total_scope_verdict]]) — so `gp-0x6acc` reaching zero
during ST=3 is not guaranteed even with the LKAS term gone; depends on real driver hands-on torque during
those frames, an empirical (rlog) question, not a pure static one.

## [🛑 2026-07-26, FIFTH pass — NEGATIVE RESULT] gp-0x67a4's 4 gating flags traced — NOT an engagement switch

Traced `gp-0x67a1`/`gp-0x67a2`/`gp-0x67a3`/`gp-0x67a7` (the inputs to `FUN_0002b422`'s state machine
`gp-0x3d28`→`gp-0x67a4` that gates `gp-0x6b3c`, see the FOURTH-pass section above) to their producers.

- **`gp-0x67a2` and `gp-0x67a3` are hardcoded literal `1`, unconditionally, every cycle.** Disasm
  `0x2a2e4-0x2a2f4`: `mov 0x1,r11 → st.b r11,-0x67a2,gp → [gp-0x6b3c write] → [gp-0x67a7 write] →
  st.b r11,-0x67a3,gp` (same register, unmodified in between). No branch skips these stores. Every
  state-machine test against these two (`==1`/`!=1`) always resolves the same way — dead conditions.
- **`gp-0x67a1` is the actual driver** — sole write (`0x2b560`) is the **return value of
  `FUN_00025c32` (`m_motor_cmd_distribute_clamp`)**, called with a small fixed local struct. Tested
  against literals 0/3/5 across the state machine. NOT purely one-way/boot-latching: state 2 resets to
  state 1 (killing `gp-0x67a4`) if `gp-0x67a1==0`, state 7 unconditionally resets to state 1 too — can
  re-trip during normal running. `FUN_00025c32` itself NOT traced this session — what its return code
  represents (success/fail? saturation flag?) is open.
- **`gp-0x67a7` looks like a Q10 ramp/blend fraction**, not a flag: `r14 = 1024 − ((1024 −
  cal(tp+0x73de-or-0x73e0)) × r14_prior) >> 15` on the main path (selecting between what look like
  up/down ramp-rate cals), truncated to a byte before the state machine compares it to literal `1`. Reads
  as a "has the ramp settled" check, not an engagement read.

**Verdict: `gp-0x67a4` is very likely NOT a clean LKAS-engagement switch.** None of its 4 inputs read
`STEER_STATUS`, `gp-0x6806`, or any other established engagement signal — the two live ones look like
internal health/settling checks for the distribute-clamp handoff. Plausible reading: this gate trips once
near a startup/re-init transient and stays open the rest of the drive, meaning `gp-0x6b3c` likely carries
the real 4×-gained value continuously rather than toggling with LKAS on/off. **This downgrades the
THIRD-pass finding's practical relevance for explaining the 9200x/14750x on-car engagement split** — the
4x-gain-in-the-reference-model structural fact still stands, but this particular candidate switch for WHY
it would only matter while engaged does not hold up. Team-lead's authority (`gp-0x6966`) telemetry
addition remains the best open path to closing the engagement-dependence question empirically.

## Open items
- Semantic trigger for `gp-0x67ac`/`gp-0x67ab` (producer of `gp-0x617c`/`gp-0x6170` RAM flags, not traced).
- Whether `gp-0x67ac` and `gp-0x67ab` are numerically identical every cycle (structurally near-duplicate,
  not proven equal).
- Whether `gp-0x6ad4` actually carries dominant 21Hz energy — mechanism verified, frequency content is not
  (needs FOURFRAME telemetry on this signal, or the cal-only test above, on-car).
- `gp-0x6806`/`gp-0x69b0`/`gp-0x6966`/`gp-0x67fa` reader enumeration this session used `search_instructions`
  only (fast first pass) — NOT cross-checked against the 6-byte V850E2 extended-displacement encoding or a
  raw Python byte scan. Treat as "at least this many," per this kit's own recorded undercounting history
  ([[accord-gp4f60-two-encodings-enumeration-trap]]).

## Related
[[reference-accord-fun3a382-resonance-lane-unfiltered-correction]] — Stage A/B/C unity-gain finding this builds on
[[reference-accord-fun352b4-peakhold-correction-and-fun3a382-stageA-pole]] — the cal-only test this file confirms is still clean
[[reference-accord-gp67ac-aggregator-lane-suppression-gate]] — the wholesale-suppression gate, now with the mixer-loop mechanics behind it
[[reference-accord-gp6b4c-lane-chain]] — gp-0x6b70's LKAS provenance
[[reference-accord-gp4f64-three-consumers]] — the governor's MIN/clamp Q15 chain reused for gp-0x69aa
[[reference-accord-gp6a5e-is-voted-vehicle-speed]] — settles Factor C's axis identity
[[reference-accord-vibration-requires-lkas-engaged]] — the on-car finding this whole trace was dispatched to explain
