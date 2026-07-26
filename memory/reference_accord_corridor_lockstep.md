---
name: reference-accord-corridor-lockstep
description: "2026-06-03 (V27 FLASHED→faulted → V28 ANALYSIS-FALSIFIED → ★V29 BUILT, cal-only, 49/49 CRC, byte-verified 0 code edits, UNFLASHED) load-bearing model for the 2020 Accord (39990-TVA-A160, V850E2). ★★★ CORRECTED AGAIN by reading shaper FUN_00042af8 DECOMPILE + watchdog FUN_00043e44 DISASM myself: the int wall gp-0x6af6 is a THREE-WAY MAX, not max(torque,corridor): gp-0x6af6 = max(dir_corridor[cal 0x774e, velocity-indexed flat ±1024], velocity/cmd-envelope IIR[gp-0x3574 sar-8, NOT driver torque; input vel-vs-cmd contested], boost[cal 0x7760 = X700/800/1100 Y0/1536/2048]) × polarity(gp-0x6752). BOTH monitors compare the FLOAT twins gp-0x6db0(dir1)/gp-0x6db8(dir2) ×1024 vs the INT walls gp-0x6af6/gp-0x6b00, window ±5 LSB (Monitor1 shaper @~0x43190 line642 |float×1024−int|; Monitor2 watchdog @0x4463a |twin−wall/1024|≤5/1024) → ≥128.0 → FUN_000462e6(0x3f1b) hard shutdown DTC 0xF00049. The float twin = (max-chain magnitude) × float(polarity); its CORRIDOR arm is the flat ±1.0 LERP tables I traced feeding ONLY the twin: dir1 table @0xC658C (Y@0xC6598/0xC659C=+1.0, X@0xC6590/94=−8/−1), dir2 table @0xC65A0 (Y@0xC65AC/0xC65B0=−1.0, X@0xC65A4/A8=+1/8) — r11=LERP(0xC6590)→r9→lp, r7=LERP(0xC65A4)→r2→lp/r20, NOT reused as a sign, NOT stored elsewhere. ⚠ TWO PRIOR ADDRESS ERRORS FIXED: (a) the float corridor mirror Y is 0xC6598/0xC659C/0xC65AC/0xC65B0, NOT 0xC6590/0xC65A4 (those are the X velocity/torque BREAKPOINTS — the V28-handoff's V29 proposal named them by mistake; doubling them scales the index axis, a V26-class wrong-table brick); (b) 0xC6664 is the ENVELOPE LERP_B (feeds early lp→gp-0x6da8 + the SEPARATE envelope monitor gp-0x6c84, nonzero at rest) — that is V26's rest-fault, NOT the corridor. V29 = build_v29_tva.py = V18 GAIN/clamps/ramp (the real 2×, GAIN 0xC646C monitor-INDEPENDENT, flashed+road-validated) + INT corridor ×2 (0xC674E/0xC6750 +1024→+2048, 0xC675A/0xC675C −1024→−2048) + FLOAT corridor mirror ×2 (0xC6598/0xC659C +1.0→+2.0, 0xC65AC/0xC65B0 −1.0→−2.0) + PN. NO trampoline, NO tolerance widen, 0xC6664/boost/speed LEFT STOCK & guarded. WHY V29 HOLDS where V25/26/27 faulted: it doubles ONLY the matched corridor arm on BOTH int+float sides → the IIR & boost arms AND the stock ±5/1024 float-vs-int residual are UNTOUCHED (V27's fatal flaw was doubling the WHOLE twin → 2× residual; V25 doubled int corridor only → desync; V26 doubled the envelope → rest offset). Monitors stay live (wrong corridor ~1024 LSB still caught). 49/49 CRC, ECU-decode==patched, 27B/16 runs, 0 executable code edits (byte-diffed vs stock + re-decoded .rwd from scratch), UNFLASHED. Output ../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V29-LKAS-2x-corridor2x-floatmirror-PNfix-…rwd + _v29_plain_image.bin. Handoff docs/HANDOFF-2026-06-03-v29.md. Confidence ~85%; residual (road-test arbiter): if the felt soft EME is the driver-override torque-sensor PLAUSIBILITY dropout (2026-05-26 model) not corridor overflow, the corridor widen won't fix it (but V29 still delivers safe 2× & must not hard-fault). ⚠ analyze STOCK code.bin (the /master.bin program, 2113 fns) ONLY — NEVER _v2x images. tp=0xBF000, gp=0xFEDF8000. --- (V28, ANALYSIS-FALSIFIED, prior) the V28 model said gp-0x6af6=max(driver-torque,corridor) and proposed doubling float 0xC6590/0xC65A4 — BOTH wrong per the 3-way-max retrace above. V28 (trampoline doubling whole twin + tolerance widen) DO NOT FLASH: V27/V28's trampoline doubles the WHOLE float twin = 2×max(torque,corridor) but the cal doubled only the corridor arm on the int side; when turning (hand torque → demand-dominated) twin=2×torque vs wall=torque → divergence ≈ FULL torque, not a 5/1024 residual → ±10/1024 tolerance can't cover → faults like V27. The 'divergence=2×residual' premise was a mis-ID of the max's secondary arm (the large driver-torque demand, not a small fixed table). Model now explains ALL: V25 faults full-lock (corridor-dom), V26 at rest (0xC6664 envelope offset), V27 turning (demand-dom). V29 (proposed, NOT built): DROP trampoline+tolerance widen; keep V18 GAIN (2×, in BOTH lockstep paths); widen corridor FLOOR by doubling BOTH int cal 0xC674E AND float corridor mirror 0xC6590/0xC65A4 (matched, cal-only, monitor intact) = 'V26 done right' (right table = corridor mirror, not LERP_B 0xC6664). Confidence ~90%; verify r11=gp-0x3574 load + the float secondary arm + the 0xC6590 match before building. ⚠ analyze STOCK code.bin only. --- (V28, ANALYSIS-FALSIFIED) doubling BOTH the float twin (trampoline) AND the int wall (cal) reaches exactly 2× and the PRIMARY corridor tables match — but the watchdog twin is polarity×max(corridor, SECONDARY tables 0xC65B8 Y→2.0); the secondary term's stock RESIDUAL ≤5/1024 DOUBLES under the 2× (divergence_V27 = 2×stock ≤ 10/1024) → busts the ±5/1024 monitor window the instant polarity≠0 → 0x3f1b hard shutdown when turning (NOT rest). No symmetric doubling avoids it; the residual itself doubles. V28 = V27 + PROPORTIONAL 2× widen of BOTH corridor monitors (Monitor2 watchdog movhi r7/r14/r16 5/1024→10/1024 @0x44640/0x44648/0x4466C; Monitor1 shaper addi 0x5→0xf + cmp 0xb→0x1e @0x43190/96 + 0x431B4/B6 = ±5→±15 LSB) — provably sufficient (stock≤5/1024 ⇒ V27≤10/1024 ⇒ 10/1024 window passes; real faults ~1024 LSB still caught). Only dir1/dir2 corridor checks widened; integrator(wt4)/torque(wt32) track. ⚠ negatives are SEPARATE movhi per check (byte-scan, NOT search_instructions which missed 0xbba0@0x44646); non-corridor negatives 0x4478C/0x448E6 LEFT STOCK. 49/49 CRC, UNFLASHED. --- (V27 prior) The DIRECTION CORRIDOR IS LOCKSTEP-MONITORED — widening the integer corridor (cal 0xC674E/0xC675A ±1024→±2048) faults DTC 0xF00049 unless the FLOAT corridor twins are matched. ⚠ THE FLOAT TWIN IS **NOT** cal 0xC6664. 0xC6664 is LERP_B, a velocity ENVELOPE multiplier; the float envelope = base/1024 + lerp_b·lerp_a and at rest lerp_a=2.0, so doubling 0xC6664 (V26) ADDED a constant +2.0 envelope offset at rest → V26 FLASHED → immediate hard fault, wheel un-turnable. The REAL float corridor twins are RAM lp (dir1, →gp-0x6db0) and r20 (dir2, →gp-0x6db8), computed in FUN_00043e44 as corridor_mag × float(polarity gp-0x6752): lp=r2×r13 @0x4461e/0x44624, r20=r13×r9 @0x4462e. BOTH monitors compare twin vs wall/1024: Monitor1 FUN_00042af8 @0x43172 trunc(twin×1024)≈int_wall(gp-0x6af6/gp-0x6b00); Monitor2 FUN_00043e44 @0x4463a/0x44662 |twin−wall/1024|≤5/1024. V25 widened int only→fault at lock; V24 doubled float twins only (cave)→fault; V27 = BOTH (int corridor ×2 + double lp/r20 via a code trampoline at the free 0xC4E00 cave). Wall+twin are command/angle LERPs (~0 at center) → faults at full lock not rest. ⚠ ANALYZE STOCK code.bin (the /master.bin program) — NEVER _v22/_v23/_v24 (experimental code edits). tp=0xBF000, gp=0xFEDF8000."
metadata:
  node_type: memory
  type: reference
---

# Accord corridor lockstep — the CORRECTED model + V29 (cal-only matched corridor, BUILT)

## ★★★★ 2026-06-03 (LATEST) — V30 FLASHED→drove well, residual soft EME on hard sustained HANDS-OFF turn → V31 (boost floor)

V30 flashed and drives well (no hard EME, most soft EMEs gone) **except one hard SUSTAINED hands-off turn**.
Root cause (walked `FUN_00042af8` myself): the soft-EME integrator bound is the SAME gated 3-way max/min as
this wall, and **each arm is conditionally gated**. The **corridor is the DRIVER-OVERRIDE arm** — zeroed when
`|gp-0x6bf0 driver-assist| ≤ 9216` (cal `0xC6156`, hands-off) AND when authority `r13 ≠ 0` (`0x43114`,
`r13 = gp-0x6966 = (|gp-0x3570>>15|×1092)>>10` = authority; `r21`=cal `0xC641A`=0). On a hands-off held turn
the corridor is OFF (V30's 4096 inactive), boost ≈ 0 (no angular rate), IIR decaying → bound collapses → 2×
command winds up → SM2/SM3. **The boost arm is also force-zeroable** by an SM (`gp-0x3562`, `0x42fb8–0x43016`)
that latches it 0 once authority > `0xC641E`(16384) for ~`0xC64E3`(20) cyc — but only at HIGH authority. **V31
= `build_v31_tva.py`** = V30 + a matched FLAT BOOST FLOOR (int `0xC6768/6A/6C`→4096, float `0xC65C4/C8/CC`→4.0,
÷1024 — the float twin's 3-way max INCLUDES boost, so lockstep stays at delta 0 incl. at rest). Boost is gated
only by authority, so at the initiation instant (authority≈0) it's ON and floors the bound to 4096 > command
3584 → no wind-up → authority never climbs → boost never latches off → SELF-STABLE FIXPOINT. The corridor
(V30) couldn't do this (driver-assist-gated → gone hands-off); boost is authority-gated → present. 49/49 CRC,
0 code edits, UNFLASHED. Full gating model: [[reference-accord-soft-eme-bound-arm-gating]]; handoff
`docs/HANDOFF-2026-06-03-v31.md`.

## ★★★ 2026-06-03 — THE WALL IS A 3-WAY MAX; V29 (corridor ×2) + V30 (corridor ×4) BUILT, UNFLASHED

> **V30 = `build_v30_tva.py`** = V29 with the corridor at **×4 (4096 / float 4.0)** instead of ×2, to ALSO
> contain the post-governor COMP_TORQUE: the shaper compares `gp-0x6acc = governed_LKAS(≤1024) + COMP(ceiling
> 2560, driver-override comp from `FUN_000456a4`)`, worst-case 3584 < 4096. **⚠ Trade:** 4096 ≥ 3584 ⇒ the
> integrator `gp-0x3570` never winds up ⇒ the corridor/SM soft-EME cutback is functionally inert (holds 2×
> under override). Hard-EME lockstep intact (corridor matched int↔float). Comp magnitude uncertain (right-size
> via `gp-0x6ac0` trace). 49/49 CRC, 0 code edits, UNFLASHED. Handoff `docs/HANDOFF-2026-06-03-v30.md`.
> The V29 (×2) detail below is the same lockstep at a smaller corridor.

Re-traced both monitor functions on STOCK `code.bin` directly (shaper `FUN_00042af8` decompile +
watchdog `FUN_00043e44` disasm). This overturned BOTH the V27 "pure corridor twin" model AND the V28
"`max(driver-torque, corridor)`" correction. The true int wall:

```
gp-0x6af6 = max( dir_corridor[cal 0x774e],  velocity/cmd-envelope IIR[gp-0x3574 >>8],  boost[cal 0x7760 = ANGULAR-RATE] ) × polarity(gp-0x6752)
```

- **dir_corridor** = LERP over s16 table `@0xC6748` (N=2, X=velocity[-8192,-1024], Y=+1024 flat); dir2 `@0xC6754`
  (Y=-1024). THE soft-EME corridor. Shaper decomp lines ~582–604 select it into `iVar27`/`iVar43`.
- **velocity/cmd-envelope IIR** = `gp-0x3574` (>>8 to natural; range [−12288,+12288], hard-cap 0x3000, typical
  ~512–2048). ⚠ NOT driver torque (that's `gp-0x69ca`). Input = LERP3 over `gp-0x4f60`, identity CONTESTED:
  column/motor angular velocity (2 memories, [STRONG]) vs rate-limited LKAS command (2 tracers, via the
  unwalked `gp-0x6b50`) — UNRESOLVED. Full chain + ranges: [[reference-accord-lerp3-gp3574-chain]].
  ⚠⚠ **RESOLVED 2026-07-18 — NEITHER candidate was right. `gp-0x4f60` = SENSOR-B (TAS) DRIVER COLUMN
  TORQUE**, proven by the CAN-399 packer `FUN_00055c42` (`STEER_TORQUE_SENSOR = -(gp-0x4f60 × 125/128)`).
  So this IIR arm is driven by *driver hand torque* — which also means the "⚠ NOT driver torque" caveat
  above is misleading: `gp-0x69ca` is not the only driver-torque signal in play, it is just a different
  one (sensor A vs sensor B; the two are independent sensors with no static scale bridge, see
  [[reference-accord-dual-torque-sensor-architecture]]). This materially changes the physical reading of
  the soft-EME bound's IIR arm — "decays when the column is held" should be re-derived on the torque
  interpretation. See [[reference-accord-gp4f60-is-sensor-b-column-torque]].
- **boost** = LERP over s16 `@0xC6760` (X[700,800,1100] Y[0,1536,2048], out [0,2048]) — Tracer B's "r23", a
  SEPARATE arm, NOT the corridor. Input `gp-0x6ac2` = `|steering ANGULAR RATE|` ∈[0,13000] (encoder→`gp-0x4f50`);
  boost saturates at 2048 for rate>1100. [EVIDENCE]
- Shaper decomp lines ~618–626 do `iVar45 = max(corridor, max(IIR,boost))` then ×polarity → `gp-0x6af6`/`gp-0x6b00`.
- ⚠ Arm-magnitude consequence: the IIR arm reaches **12288** ≫ corridor (2048), so it dominates the wall when
  active; the corridor only sets the FLOOR in the quiet regime (IIR + boost small). Boost ceiling (2048) = V29 corridor.

**Both monitors compare the FLOAT twins vs the INT walls** (±5 LSB):
- Monitor 1 (shaper, decomp line 642 / `~0x43190`): `|float(gp-0x6db0)*1024 − int(gp-0x6af6)|` in a ±5 window (weight 1; dir2 = `gp-0x6db8`/`gp-0x6b00`, weight 2).
- Monitor 2 (watchdog `FUN_00043e44` `@0x4463a`): `|gp-0x6db0 − gp-0x6af6/1024| ≤ 5/1024`. Accumulator ≥128.0 → `FUN_000462e6(0x3f1b)` hard shutdown (DTC `0xF00049`).

  > **REFINED 2026-07-18** — the "≥128.0" is more specific than it looks, and it matters. The 128.0 compare (`movhi 0x4300` @`0x44a26`) is against a **weighted sum of 7 flags** (weights 1,2,4,8,16,32,64; this Monitor-2 dir1/dir2 pair are weights **1** and **2**) whose **maximum is 127** — so no single-cycle flag combination can trip it. The trip is forced by a **debounce SM** on `gp-0x3540`/`gp-0x3550`: any flag set integrates `0.001`/cycle until `0.01` (**≈10 cycles ≈ 0.1 s @100 Hz**, decay `0.0005`), which advances to state 3 and adds **1024.0** → 1151 > 128. So a *momentary* lockstep divergence is tolerated; a **sustained** one for ~0.1 s trips.
  >
  > `FUN_000462e6` calls **`FUN_00016de6(0x1D, 0x3f1b, 1, 1)`** — the DTC setter. ⚠ [[reference-accord-override-snap-state-machines]] calls this same monitor **"REPORT-ONLY — does NOT gate torque"**, contradicting "hard shutdown" here. The DTC setter is definitely invoked; whether torque is gated is **UNVERIFIED**, as is the `0x1D`/`0xF00049` mapping. See [[reference-accord-watchdog-fault-sm-fun43e44]].

**The float twin** (computed in `FUN_00043e44`) = `(max-chain magnitude) × float(polarity gp-0x6752)`. I traced
its corridor arm: `r11 = LERP(0xC6590)` (dir1) and `r7 = LERP(0xC65A4)` (dir2) feed **only** the max chain
that becomes `lp`/`r20` (r11→r9→lp@0x44624/r20@0x4462e; r7→r2→lp@0x4461e), are sign/plausibility-gated off at
rest, and are NOT reused as a sign nor stored elsewhere. LERP Y-bases from disasm: dir1 `movea 0x7598,tp,r12`
(=`0xC6598`), dir2 `movea 0x75ac,tp,r14` (=`0xC65AC`).

### ⚠ Two prior ADDRESS errors, both fixed in V29

- **The float corridor-mirror Y is `0xC6598`/`0xC659C` (dir1, +1.0) and `0xC65AC`/`0xC65B0` (dir2, −1.0)** —
  the exact 1/1024 float mirror of the int corridor (both FLAT, so the velocity-vs-torque index axis is moot).
  **NOT `0xC6590`/`0xC65A4`** — those are the X breakpoints (−8.0/+1.0). The V28 handoff's V29 proposal named
  the X breakpoints; doubling them would scale the index axis (a V26-class wrong-table brick).
- **`0xC6664` is the ENVELOPE (LERP_B)** — it feeds the early envelope `lp → gp-0x6da8` and the SEPARATE
  envelope monitor `gp-0x6c84` (decomp line ~1287), nonzero at rest. That is V26's rest-fault. **LEFT STOCK.**

### V29 = `build_v29_tva.py` (BUILT, cal-only, UNFLASHED)

V18 GAIN/clamps/ramp (the real 2×; GAIN `0xC646C` is monitor-INDEPENDENT — absent from the wall computation
0x43040–0x43172 — and is flashed+road-validated) **+ INT corridor ×2** (`0xC674E`/`0xC6750` +1024→+2048,
`0xC675A`/`0xC675C` −1024→−2048) **+ FLOAT corridor mirror ×2** (`0xC6598`/`0xC659C` +1.0→+2.0,
`0xC65AC`/`0xC65B0` −1.0→−2.0) + PN. **No trampoline, no tolerance widen**; `0xC6664`/boost/speed left STOCK
& guarded; **0 executable code edits** (byte-diffed vs stock + re-decoded `.rwd`). 49/49 CRC, 27B/16 runs.

**Why V29 holds (the key):** it doubles ONLY the matched corridor arm on BOTH sides, so the IIR & boost arms
AND the stock ±5/1024 float-vs-int residual are UNTOUCHED. V27's fatal flaw was doubling the *whole* float
twin → the residual itself doubled → fault when demand-dominated. V29 leaves every non-corridor arm exactly
stock. Monitors stay fully live (a genuinely-wrong corridor ~1024 LSB still diverges far outside ±5).

**Confidence ~85%.** Residual (road test = arbiter, `feedback_operator_lived_experience`): if the felt soft
EME is the driver-override torque-sensor PLAUSIBILITY dropout ([[reference-accord-driver-override-plausibility-eme]])
rather than corridor overflow, the corridor widen won't fix THAT — but V29 still delivers safe 2× and must
not hard-fault. Output `…/39990-TVA,A160-V29-LKAS-2x-corridor2x-floatmirror-PNfix-…rwd` + `_v29_plain_image.bin`;
handoff `docs/HANDOFF-2026-06-03-v29.md`.

---

# Accord corridor lockstep — the V28 model (FALSIFIED-by-analysis, kept for the trail)

## ★★ 2026-06-03 (later) — THE WALL IS `max(driver-torque, corridor)`; V28 IS LIKELY BROKEN

> ⚠ This V28 "correction" was ITSELF overturned by the 3-way-max retrace above. The wall is
> `max(corridor, IIR, boost)` (three arms), and V28's proposed float address `0xC6590`/`0xC65A4` are the X
> breakpoints, not the Y magnitude. Read the V29 section above; this is kept only for the trail.

Operator asked "is the command compared to the envelope, or the corridor?" Settling it (reading shaper
disasm `0x43040–0x43172` directly) **overturned the V28 model.** `gp-0x6af6` is **NOT a pure corridor wall**:

```
0x43136 sar 0x8,r11         ; r11 = ×256-scaled value → natural (the driver-torque IIR gp-0x3574)
0x43138 cmp r23,r11
0x4313c cmovgt r11,r23,r10   ; r10 = max(r11=torque, r23=corridor LERP from cal 0x774e)
0x43170 mov r10,r15          ; (symmetric: r9 sar-8 vs -r23 → negative wall)
        → r29 → st.h r29,-0x6af6[gp]
```

**`gp-0x6af6 = max(driver-column-torque IIR, corridor floor)`.** The `sar 0x8` (÷256) marks `r11` as a
×256-stored quantity — and the only ×256 values here are the column-torque IIR accumulators
(`gp-0x3574`/`gp-0x3578`). The corridor (`r23`, natural-scale s16 cal `0x774e`) is only the **floor** of the max.
So the two monitors (`FUN_00043e44` Monitor 2 + shaper `FUN_00042af8` Monitor 1) are an **INT-vs-FLOAT
LOCKSTEP on `max(driver-torque, corridor)`** — the V13A dual-path lockstep, corridor as floor — NOT a
corridor twin. (To the operator's Q: the command isn't *clamped* by an envelope; `gp-0x6b98` is clamped only
by the governor `gp-0x4f64` + ±0x2000. But the driver-torque demand IS int-vs-float cross-checked here.)

**⇒ V28 IS LIKELY BROKEN — DO NOT FLASH.** V27/V28's trampoline doubles the WHOLE float twin =
`2 × max(torque_float, corridor_float)`; the cal doubled only the corridor arm on the int side
(`gp-0x6af6 = max(torque_int, 2×corridor_int)`). **Turning the wheel applies hand torque → demand-dominated**
→ twin = `2×torque`, wall = `torque` → divergence ≈ the **full torque magnitude**, not a 5/1024 residual.
The earlier "divergence = 2×residual ≤ 10/1024" was a **mis-ID of the max's secondary arm** (read as a small
fixed table `0xC65B8`; it is actually the large driver-torque demand). The ±10/1024 / ±15-LSB tolerance widen
**cannot cover a demand-scale divergence** → V28 hard-faults the instant the wheel turns, same class as V27.

**This model explains ALL three flashes (the old ones never fully did):**
- **V25** (int corridor ×2 only) → full lock = corridor-dominated there → int `2×corridor` vs float `corridor`.
- **V26** (`0xC6664` LERP_B) → +2.0 envelope offset → faults at rest.
- **V27** (trampoline doubles the whole float twin) → turning = demand-dominated → float `2×torque` vs int `torque`.

**Corrected fix — V29 (proposed, NOT built; simpler):** DROP the trampoline AND the tolerance widen. The 2×
torque already comes from V18's GAIN (`0xC646C`, flashed/works) — it works because the gain sits inside BOTH
lockstep paths (int + float demand both scale → monitor stays matched). To widen the corridor *floor* for the
soft EME without breaking the lockstep, double **both** corridor tables in lockstep: int cal `0xC674E` **and
the float corridor mirror `0xC6590`/`0xC65A4`** (exact float mirrors of the int corridor). Cal-only, no code
patch, monitor fully intact. "V26 done right" — the right float table is the corridor mirror, NOT LERP_B
`0xC6664`. (Note V25 widened int-only → faulted; V29 widens BOTH the matched int+float corridor tables.)

**Confidence ~90%.** Before any V29 build, verify: (1) walk `r11`'s load back to confirm it's the `gp-0x3574`
driver-torque IIR (the one inferred-not-walked link — but the V28-unsafe conclusion is robust to it, since
`r11` is clearly a demand-like ×256 quantity that dominates the max when steering); (2) the watchdog's float
"secondary" arm = the float recomputation of that same torque; (3) `0xC6590`/`0xC65A4` is the exact matched
float table to double alongside `0xC674E`. Method note: this came from reading the disasm MYSELF after two
tracers (Tracer 3 "corridor-only" vs Tracer 5 "max(IIR,corridor)") conflicted — when tracers conflict on a
load-bearing register chain, walk it directly.

Everything below (the V28 "monitor-tolerance 2×" section) is the as-analyzed V28 record + its now-falsified
rationale, kept for the trail.

---

## ★ 2026-06-03 — V27 FLASHED → HARD-FAULTED when turning → V28 BUILT (monitor-tolerance 2×) [FALSIFIED-BY-ANALYSIS, see above]

**V27 was flashed and hard-faulted the instant the wheel was turned** (wheel un-turnable). Same *class*
as V26 (a near-t=0 divergence), different quantity. Root cause (decomp `FUN_00043e44` +
`FUN_00042af8` + 4 tracers + algebra + the real stock table bytes):

- V27 doubles the float **twin** (`gp-0x6db0/db8`, trampoline) AND the int **wall** (`gp-0x6af6/b00`,
  cal `0xC674E`). Both reach **exactly 2×**, and the primary float corridor tables (`0xC6590`/`0xC65A4`)
  are exact mirrors of the int corridor → residual 0 there. So by steady-state math V27 should pass.
- BUT the watchdog twin is `polarity × max(corridor_mirror, SECONDARY tables)`. Secondary table
  `0xC65B8` = X[700,800,1100] Y[0, 1.5, **2.0**] — not a corridor. In stock the `max()` lets the twin
  exceed the corridor by a small **residual R ≤ 5/1024** (inside the monitor window). The divergence
  collapses to `R = polarity × max(0, secondary − corridor)`.
- **The 2× doubles R:** `divergence_V27 = 2·twin − 2·wall/1024 = 2·R`. Since stock `R ≤ 5/1024`
  (the car works stock), `2R ≤ 10/1024` — **over the ±5/1024 window** the moment `polarity ≠ 0`
  (any steering). Fault SM → `FUN_000462e6(0x3f1b)` hard shutdown in ~10 cycles. **No symmetric
  doubling escapes it — the residual itself doubles** (V27's trampoline, V24's cave, the operator's
  "double the int too" all give `2R`).

**V28 = `build_v28_tva.py` = V27 + a PROPORTIONAL 2× widen of BOTH corridor monitors** so `2R` fits:
- **Monitor 2 (watchdog):** `±5/1024 → ±10/1024`. Three `movhi` immediates: `r7` `0x3ba0→0x3c20`
  (+10/1024, @`0x44640`, **shared** positive), `r14` `0xbba0→0xbc20` (−10/1024, @`0x44648`, dir1 neg),
  `r16` `0xbba0→0xbc20` (−10/1024, @`0x4466C`, dir2 neg).
- **Monitor 1 (shaper):** `±5 → ~±15` LSB. Per direction: `addi 0x5→0xf` + `cmp 0xb→0x1e`
  (dir1 @`0x43190`/`0x43196`, dir2 @`0x431B4`/`0x431B6`). `±15` (not `±10`) gives margin for the `±1`
  `trunc()` rounding in `trunc(twin×1024) − wall`.
- **Provably sufficient for the corridor checks:** stock `R ≤ 5/1024` everywhere ⇒ V27 `2R ≤ 10/1024`
  everywhere ⇒ a 10/1024 window always passes; a genuinely-wrong corridor (~1.0 = 1024 LSB) is still
  caught → **recalibration, not blinding**. Only dir1/dir2 (the doubled corridor checks) are widened;
  the integrator (weight 4) and delivered-torque (weight 32) checks **track** (their twins are NOT
  doubled by the trampoline; both sides see the same widened wall) → left at stock tolerance.
- ⚠ **The negatives are SEPARATE `movhi` constants per check.** `search_instructions` MISSED the
  `movhi 0xbba0` @`0x44646` (Ghidra hadn't parsed it); a raw **byte scan** of `code.bin` found all 5
  (`0x4463E` +5/1024 shared; `0x44646`/`0x4466A`/`0x4478C`/`0x448E6` −5/1024). The two non-corridor
  negatives (`0x4478C`, `0x448E6`) are **LEFT STOCK** (their weights track); the build asserts they
  stay `0xbba0`. A positive-only widen would have bricked asymmetrically.
- **Build:** cipher round-trips, **49/49 CRC PASS**, all readbacks pass (widened constants decode
  correctly; non-corridor negatives stock; `0xC6664` stock; cave tail `0xFF`), 46-byte diff / 22 runs.
  Output `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V28-LKAS-2x-corridor2x-twindbl-MONtol2x-PNfix-…rwd`
  + `../accord-firmware/analysis-2020accord/_v28_plain_image.bin`. **UNFLASHED.** Residual [I-low]: only corridor checks widened (others
  reasoned to track, not emulated). Pre-flash: import `../accord-firmware/analysis-2020accord/_v28_plain_image.bin` + disassemble the 10
  tolerance sites; road test is the arbiter. Full handoff: `docs/HANDOFF-2026-06-03-v28.md`.

---

# Accord corridor lockstep — the V27 model (superseded by V28 above; V26 failure recorded)

Established across 2026-06-02. **V26 was flashed and HARD-FAULTED immediately on startup — the wheel
could not be turned at all** (worse than V25, which drove ~5–10 ft and faulted only at full lock).
This **falsified** the V26 premise that doubling cal `0xC6664` restores corridor lockstep. The corrected
model below is instruction-verified on the **STOCK** image `code.bin` (the `/master.bin` program in the
Ghidra project, 2113 functions). Bases `tp=0xBF000`, `gp=0xFEDF8000`.

## ⚠ The `0xC6664` mistake (what V26 got wrong, and why it faulted AT REST)

`0xC6664` is **LERP_B** — a velocity-indexed *envelope* multiplier, **not** a corridor twin
([[reference-c6664-lerp-b-envelope]], instruction-verified twice). In `FUN_00043e44` the float
watchdog envelope is built as:

```
envelope_Y = (u16 base gp-0x6444)/1024  +  lerp_b · lerp_a
```

where `lerp_a` = LERP over cal `0xC65D4`/`0xC65F0`. **At rest `lerp_a = 2.0`** (LERP_A Y[0]=2.0, read
from the bytes). So doubling `lerp_b` (`0xC6664` 1.0→2.0) does **not** scale the twin — it ADDS a
constant `lerp_a` = **+2.0** to the float envelope at *every* operating point including parked/centered.
The integer side didn't move → the watchdog diverged from t=0 → DTC `0xF00049` + latched motor-off
within ~10 cycles (~50–100 ms). That is the "immediate, wheel un-turnable" V26 fault.

## The corridor IS lockstep-monitored [V] — but via the float TWINS lp/r20, not 0xC6664

The corridor is computed in both domains and cross-checked by **two** monitors:

| | INTEGER side (cal `0xC674E`/`0xC675A` → LERP) | FLOAT twin (computed in `FUN_00043e44`) |
|---|---|---|
| dir1 (UPPER) | wall `gp-0x6af6` (0xFEDF150A) | `lp` → stored `gp-0x6db0` (0xFEDF1250) @0x449f4 |
| dir2 (LOWER) | wall `gp-0x6b00` (0xFEDF1500) | `r20` → stored `gp-0x6db8` (0xFEDF1248) @0x44a30 |

**Float twin computation in `FUN_00043e44` (stock code.bin) [V]:** `r13 = float(polarity gp-0x6752)`
(±1, or 0 if out of range); `lp = r2_corridor × r13` (@0x4461e dir1) or `r9_corridor × r13` (@0x44624);
`r20 = r13 × r9_corridor` (@0x4462e). The corridor magnitudes `r2/r9` come from the float corridor LERP
path (independent of the integer corridor cal). gp-0x6dc0 (integrator twin) is a SEPARATE quantity
(stored @0x44a2a from r10) — **not** affected by lp/r20.

**The two monitor checks [V]:**
1. **Monitor 1** = `FUN_00042af8` inline check @`0x43172`: `r8=gp-0x6db0`; `mulf.s 1024.0,r8`;
   `trncf.sw`; `ld.h -0x6af6[gp]`; `sub` → `trunc(twin × 1024) − int_wall`, tolerance ~±15. r17(1024.0
   @0x43176) is SHARED with dir2 (@0x43192) and the integrator check (@0x4328c).
2. **Monitor 2** = `FUN_00043e44` inline @`0x4463a`/`0x44662`: dir1 `r10 = lp − float(gp-0x6af6)/1024`
   then `|r10| > 5/1024 (0x3ba00000)` → weight 1.0 (r23); dir2 `r12 = r20 − float(gp-0x6b00)/1024`
   → weight 2.0 (r25). Weights sum into the fault_word (@0x44926+), trip at ≥128.0 (@0x44a2e) →
   `FUN_000462e6(0x3f1b)` → hard shutdown. (The float watchdog's fault-SM enable gate is `0xC64A4`=0
   = ENABLED; verified directly. NOTE: a tracer once misread this as `0xC74A4`=0xEA via an
   off-by-`0x1000` tp+disp slip — `tp+0x74A4 = 0xC64A4`.)

**Why faults appear at FULL LOCK, not at rest [V/I]:** the int wall and the float corridor magnitude
are both command/angle-dependent LERPs — ≈0 near center, maxing at full lock. So at rest twin≈0 and
wall≈0 (divergence ≈0, harmless); at full lock the widened wall/1024=±2.0 while the stock twin=±1.0 →
divergence ±1.0 ≫ 5/1024 → fault. This is exactly V25's "drove a few feet, faulted at full lock."

## The V24/V25/V26/V27 ladder (each had only part of the fix)

| Build | int corridor `0xC674E` | float twin (lp/r20) | result |
|---|---|---|---|
| **V24** | ±1024 (stock) | **doubled** (cave trampoline) | float 2.0 vs int 1.0 → fault (float-only) |
| **V25** | **±2048** | stock 1.0 | int 2.0 vs float 1.0 → fault at full lock (int-only) |
| **V26** | ±2048 | stock — but **`0xC6664` doubled** (wrong table) | envelope +2.0 offset → fault AT REST |
| **V27** | **±2048** | **doubled** (cave trampoline) | both 2.0 → match → no fault ✓ |

V27 is the first build with **both halves**. (V24 already proved the twin-doubling trampoline mechanism
works — Ghidra decoded its `addf.s lp,lp,lp` cave cleanly — it just lacked the integer widen. See the
sibling envelope-cave precedent [[reference-accord-v22-float-monitor-2x-cave]].)

## V27 build (current, UNFLASHED) — `build_v27_tva.py`

V18 base (GAIN `0xC646C` 891→1782, clamps `0xC61B4`/`0xC61B2` 512→1024, ramp `0xC64DE` 0x11→0x1B)
**+ INT corridor ×2** (`0xC674E`/`0xC6750` +1024→+2048, `0xC675A`/`0xC675C` −1024→−2048)
**+ a code trampoline that doubles the float twins** (`0xC6664` LEFT STOCK — V26's mistake reverted):

- `0x4463A` `subf.s r2,lp,r10` (e2ff6254) → `jr 0xC4E00` (8807c607)
- cave `0xC4E00` (stock all-`0xFF`, verified): `addf.s lp,lp,lp` (ffff60fc) ; `addf.s r20,r20,r20`
  (f4a760a4) ; `subf.s r2,lp,r10` (e2ff6254, displaced) ; `jr 0x4463e` (b70732f8)

Doubling lp/r20 reaches the dir1 divergence (in the cave), the dir2 divergence (@0x44662, sees the
already-doubled r20), and the two twin stores (gp-0x6db0/gp-0x6db8 → Monitor 1). At full lock twin
1.0→2.0 matches wall/1024=2.0 → Monitor 1 `trunc(2.0×1024)=2048=wall`, Monitor 2 `|2.0−2.0|=0`.
**Monitors stay fully live** (a genuinely wrong corridor LERP still diverges from the doubled-expected
value — recalibration to the 2× design point, not a disable; matches the operator's directive).

**Collateral-verified [V] on stock code.bin:** after 0x4463a, `lp` (r31) is used ONLY by the dir1
divergence + its store @0x449f4; `r20` ONLY by the dir2 divergence @0x44662 + its store @0x44a30; NO
`jarl` between 0x4463a and the stores (lp not clobbered). The LERP/threshold uses of lp/r20 the agent
flagged (@0x4448a.., @0x44586) are at LOWER addresses, i.e. BEFORE the twin assignments
(0x4461e/0x4462e) — they run on earlier register values, unaffected.

**Build integrity:** cipher round-trips, 49/49 bootloader CRC PASS, all readback asserts pass, 36-byte
diff / 15 runs, `0xC6664` confirmed still stock, cave tail still `0xFF`. The built `_v27_plain_image.bin`
was imported into Ghidra and the trampoline + all 4 cave instructions disassemble exactly as designed
(incl. the new `jr 0x4463e`). Output
`../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V27-LKAS-2x-corridor2x-twindbl-codetrampoline-PNfix-0x13000-0x100000.rwd`.
**STUDY ARTIFACT — no flash until the operator names file + bus.**

## Residual / arbiter

The trampoline doubles the float twin EXACTLY (×2) and the cal doubles the wall EXACTLY (×2), so the
small stock float-vs-int **residual `R = (twin − wall/1024)` also doubles** (→ `2R`). Monitor tolerances
are ±5/1024 (Monitor 2) / ±15 LSB (Monitor 1). If `R` were already near half-tolerance at some steering
angle, `2R` could trip. Typically `R` ≪ tolerance (both compute the same corridor), but it is NOT
measured across all angles. Close it before flash with an emulation sweep of `(twin − wall/1024)` on the
built image, or a cautious first drive. The road test is the true arbiter
([[feedback-operator-lived-experience-overrides-analyst-recs]]).

## ⚠ .bin discipline (this session's hard lesson)

Analyze stock firmware ONLY on `code.bin` (project path `/master.bin` = `../accord-firmware/analysis-2020accord/ghidra_project/code.bin`,
SHA-matched to `../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin`, 2113 functions). The open `_v22`/`_v23`/`_v24` plain images
carry V21–V24 **experimental code edits** — including a real trampoline at `0xC4E00` and `shl` edits —
and analyzing `_v24` produced a wrong "cave divergence (2·r20 − wall)" model + a confidently-wrong
NO-GO. Always `switch_program("code.bin")` and sanity-check `0xC4E00 == 0xFF` before trusting stock
analysis; pin every subagent to it explicitly.

## Related

[[reference-c6664-lerp-b-envelope]] (0xC6664 = LERP_B, NOT the twin) ·
[[reference-accord-corridor-vs-envelope]] (the corridor-vs-watchdog framing; its "double 0xC6664"
addendum is the V26 mistake — superseded here) · [[reference-accord-v22-float-monitor-2x-cave]] (the
prior cave-trampoline precedent + V850 encodings) · [[reference-accord-consistency-monitor-hardshutdown]]
(the DTC 0xF00049 latch chain) · [[reference-accord-lerp3-gp3574-chain]] ·
[[project-accord-torque-mod-v0]] · [[feedback-operator-lived-experience-overrides-analyst-recs]] ·
[[feedback-rigorous-validation]] · [[feedback-tight-agent-briefs]]
</content>
