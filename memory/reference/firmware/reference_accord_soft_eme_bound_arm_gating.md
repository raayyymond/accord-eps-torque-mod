---
name: reference-accord-soft-eme-bound-arm-gating
description: "2026-06-03 (V30 FLASHED→drove well but residual soft EME on ONE hard SUSTAINED hands-off turn → V31 BUILT). Load-bearing model for WHEN each arm of the soft-EME integrator bound is live, established by walking FUN_00042af8 on STOCK code.bin myself. The integrator gp-0x3570 winds up on (command − bound); bound = the SAME 3-way max/min as the lockstep wall: r29(upper)=MAX(corridor, IIR gp-0x3574>>8, boost), r27(lower)=MIN(corridor, −IIR gp-0x3578>>8, −boost), built 0x43136–0x43156, assigned r29@0x4318a / r27@0x4316e, then the integrator update is 0x431c4–0x4327c. ★ EACH ARM IS CONDITIONALLY GATED: (1) CORRIDOR (dir1/dir2 cal 0xC674E/0xC675A = tp+0x7748/0x7754) is the DRIVER-OVERRIDE arm — zeroed at 0x43110–0x43134 when |gp-0x6bf0 driver-override/assist signal| ≤ cal 0xC6156(=9216) (i.e. hands-off / light driver input → BOTH arms 0; |val|>9216 → one-sided), AND additionally zeroed at 0x43114 (cmp r21,r13; bh) when authority r13≠0 (r21=cal 0xC641A=0). So the corridor is live only when the driver is actively fighting AND authority is ~0. (2) BOOST (cal 0xC6760 int / 0xC65B8 float, LERP over |angular rate gp-0x6ac2|, rate≈0→Y[0]=0) is ungated by driver/pos but passes a STATE MACHINE 0x42fb8–0x43016 (state byte gp-0x3562, counter gp-0x355c, ceiling cal 0xC64E3≈20, threshold cal 0xC641E=16384) that FORCES r23=0 (@0x42ffa state1→2, @0x43004 state2 while r13≠0) once authority has been >16384 for ~20 cycles, latched until authority returns to 0. (3) IIR (gp-0x3574 upper / gp-0x3578 lower) decays toward 0 (τ≈102ms, alpha cal 0xC6418=10) when its input (column velocity, see below) ≈0, e.g. a held wheel. ★ r13 = gp-0x6966 = AUTHORITY MAGNITUDE = (|integrator gp-0x3570 >>15| × cal 0xC61DA[=1092]) >> 10 (writer 0x432b0–0x432c8; loaded into r13 @0x42d86; same uVar34 that arms SM2 @0xC6422=16384). BOTH the corridor's 0x43114 gate AND the boost SM key off this authority. ★ ROOT CAUSE of V30's residual EME: on a hard SUSTAINED HANDS-OFF turn, at the initiation instant authority≈0 → corridor is OFF (driver-assist≈0, |gp-0x6bf0|≤9216), boost≈0 (wheel held → angular rate≈0), IIR decaying (column velocity≈0) → bound collapses below the 2× command (~1024) → integrator winds up → authority climbs → corridor AND boost BOTH latch off (both authority-gated) → bound=IIR alone → decays to 0 → SM2/SM3 cut. V30 widened the CORRIDOR (cal 0xC674E + float mirror), which is exactly the driver-override arm that is OFF in the hands-off regime → didn't help. This also RESOLVES the contested IIR input identity: IIR is small on a held turn ⇒ input is COLUMN VELOCITY, not the LKAS command. ★ WHY V31 (boost floor) WORKS: V31 floors the boost LERP Y to a flat 4096 (int 0xC6768/6A/6C, float 0xC65C4/C8/CC=4.0, matched ÷1024 — lockstep-safe, float twin includes boost). Boost is gated only by AUTHORITY, not by driver-assist/pos_err, so at the initiation instant (authority≈0) boost is ON and floored to 4096. Bound ≥ 4096 > worst-case command (governed_LKAS≤1024 + COMP≤2560 = 3584). So the integrator can't wind up; authority never climbs; the boost-zeroing SM never fires; corridor's authority-gate stays open. SELF-STABLE FIXPOINT (and attracting: a partial wind-up 0<authority≤16384 relaxes because boost stays floored to 4096 the whole way up to the latch point). The runaway/both-off state is UNREACHABLE from normal operation. The corridor (V30) couldn't do this because it's driver-assist-gated → vanishes at the hands-off instant the EME initiates; boost is authority-gated → present at that instant. Residual: 4096−3584=512 margin rests on COMP ceiling 2560 (cal 0xC67DC - ADDRESS CORRECTED 2026-08-06, 0xC67D8 is Y[0]=512) + governed clamp 1024 (cal 0xC61B4); COMP magnitude uncertain (right-size via gp-0x6ac0). tp=0xBF000, gp=0xFEDF8000. STOCK program = code.bin (/master.bin, 2113 fns) — NEVER _v27. See [[reference-accord-corridor-lockstep]], [[reference-accord-lerp-envelope-gating]], [[reference-accord-override-snap-state-machines]], [[reference-accord-lerp3-gp3574-chain]], [[project-accord-torque-mod-v0]]."
metadata:
  node_type: memory
  type: reference
---

# Accord soft-EME integrator bound — per-arm gating + why V31 (boost floor) holds where V30 (corridor) didn't

> 🛑 **CORRECTION BANNER 2026-08-06 — three fixes, all decision-bearing.**
>
> 1. **THE SOFT-EME / SM1-2-3 CUT CANNOT LATCH.** [EVIDENCE, fresh decompile] the authority-node
>    **recovery branch is a single fixed-step rise with NO bypass condition**, regardless of which SM
>    caused the cut. **It self-clears.** Any statement anywhere that this mechanism can produce a
>    *latched* loss of assist is wrong — a latch needs the DTC-eligibility chain
>    ([[reference-accord-monitor2-corridor-and-the-c64a4-trap]]), not these SMs.
> 2. **`gp-0x3570` is a PURE UNATTENUATED INTEGRATOR** — it adds the **entire** `(cmd − bound)` every
>    1 kHz cycle. It is **not** a 1/4-per-cycle tracker. ⇒ a sustained **100-count excess arms SM2 in
>    153 ms**, not seconds. Any dwell-time argument built on the tracker reading is void.
> 3. **BOOST-FLOOR MARGIN EROSION IS REFUTED AS THE V75 CAUSE** — margin **+215 clamp-sum / +481
>    realized**, and it **never crosses zero**. Combined with (1), this mechanism cannot produce V75's
>    signature at all.
>
> ⊕ And the mechanism is **measured near-inert on-car**: V54 read authority **≤ 119 across 5,989
> frames** against a **3,073** knee ([[reference-accord-v54-flashed-authority-is-zero-by-design]]).
> ⊕ Address fix: COMP ceiling **2560 is `0xC67DC`**, not `0xC67D8` (= Y[0] = 512) — see the Residual
> section below.

Established 2026-06-03 by walking `FUN_00042af8` on STOCK `code.bin` myself after V30 was **flashed,
drove well, but threw a residual soft EME on ONE hard sustained hands-off turn**. Bases `tp=0xBF000`,
`gp=0xFEDF8000`. Reconciles + extends [[reference-accord-lerp-envelope-gating]] (which already had the
corridor-gated-hands-off piece) and [[reference-accord-corridor-lockstep]] (the 3-way wall) into the full
gating model.

## The bound is a gated 3-way max/min [V]

The soft-EME integrator `gp-0x3570` winds up on `(command − bound)` (update block `0x431c4–0x4327c`;
SM2 arms when its magnitude ≥ `0xC6422`=16384, SM3 when it saturates at clamp `0xC61DC`=30720 → authority→0
→ instant cut, ~10 s ramp recovery). The bound is the **same 3-way structure as the lockstep wall**:

```
r29 (upper, @0x4318a) = MAX( corridor_r7,  IIR r11 = gp-0x3574>>8,  boost r23 )
r27 (lower, @0x4316e) = MIN( corridor_r12, -IIR r9 = gp-0x3578>>8, -boost )
   built across 0x43136–0x43156
```

**`command` = clamp(gp-0x6acc, ±0x2000)`, `gp-0x6acc = governed_LKAS(≤1024) + COMP(≤2560) ≤ 3584.**

## Each arm is conditionally gated — this is the whole story [V]

| arm | source | gated OFF when | so it's live when |
|---|---|---|---|
| **corridor** (dir1/dir2) | cal `0xC674E`/`0xC675A` (tp+0x7748/0x7754), LERP over column velocity | `\|gp-0x6bf0\| ≤ 9216` (cal `0xC6156`) **OR** authority `r13 ≠ 0` (`0x43110`/`0x43114`) | driver actively fighting (`\|gp-0x6bf0\|>9216`) **and** authority ≈ 0 |
| **boost** | cal `0xC6760` int / `0xC65B8` float, LERP over `\|angular rate gp-0x6ac2\|`; rate≈0→Y[0]=0 | latched 0 by SM (`gp-0x3562`, `0x42fb8–0x43016`) after authority `r13` > `0xC641E`(16384) for ~`0xC64E3`(20) cycles; stays off until authority=0 | authority ≤ 16384 (incl. all of low/idle) |
| **IIR** | `gp-0x3574`/`gp-0x3578`, IIR(α=`0xC6418`=10, τ≈102 ms) of a LERP over **column velocity** | never hard-gated, but DECAYS toward 0 when its input (column velocity) ≈ 0 (held wheel) | column moving |

`gp-0x6bf0` = the **driver-override / assist** signal (≈0 hands-off — per
[[reference-accord-lerp-envelope-gating]]; a 2026-06-03 writer-trace alternatively read it as
`angle_error×gain×polarity` — identity not fully reconciled, but ≈0 in the hands-off held-turn case either
way). **The corridor is a DRIVER-OVERRIDE arm**, not a baseline LKAS bound.

## r13 = AUTHORITY (both the corridor gate and the boost SM key off it) [V — walked the writer]

`r13` (used at the corridor gate `0x43112` and the boost SM `0x42fcc`/`0x43002`) is loaded `@0x42d86` from
`gp-0x6966`. Writer `0x432b0–0x432c8`: `gp-0x6966 = (|gp-0x3570>>15| × cal 0xC61DA[=1092]) >> 10` = the
**authority magnitude** = the same `uVar34` that arms SM2. So **both the corridor's authority-gate (`0x43114`,
`cmp r21,r13; bh`, `r21`=cal `0xC641A`=0 ⇒ zero corridor if authority≠0) and the boost-latch SM key off the
integrator's own wound-up state.** (Walked directly because the tracer was internally inconsistent here.)

## Root cause of V30's residual soft EME (hard sustained hands-off turn) [V/I]

At the **initiation instant** — wheel held, hands off, authority ≈ 0:
- corridor OFF (driver-assist ≈ 0, `|gp-0x6bf0| ≤ 9216`) — **V30's widened 4096 corridor is inactive here**;
- boost ≈ 0 (wheel not rotating → angular rate ≈ 0 → Y[0]);
- IIR decaying (column velocity ≈ 0).

→ bound collapses below the 2× command (~1024) → integrator winds up → authority climbs → corridor **and**
boost **both** latch off (both authority-gated) → bound = IIR alone → decays to 0 → SM2/SM3 cut. **V30 widened
the one arm (corridor) that is gated off in precisely the hands-off regime that failed.** (Stock 1× never
EMEs because cmd ≈512 fits under the residual; 2× ≈1024 exceeds it — the 2×-only signature.)

## Why V31 (matched flat boost floor 4096) holds — self-stable fixpoint [V/I]

Boost is gated **only by authority**, never by driver-assist/pos_err. So at the initiation instant
(authority ≈ 0) boost is ON and **floored to 4096** (V31: int `0xC6768/6A/6C`→4096, float
`0xC65C4/C8/CC`→4.0, matched ÷1024 — lockstep-clean, the float twin includes boost). Then bound ≥ 4096 >
command (≤3584) ⇒ integrator can't wind up ⇒ authority never climbs ⇒ the boost-zeroing SM never fires ⇒
corridor's authority-gate stays open. **Self-stable** (and attracting: any partial wind-up
`0<authority≤16384` relaxes, because boost stays floored at 4096 all the way up to the 16384 latch point, so
authority can never reach it). The runaway/both-off state is **unreachable from normal operation.**

The corridor (V30) couldn't do this — it's driver-assist-gated, so it vanishes at the hands-off instant the
EME initiates. **Boost is authority-gated, so it is present at that instant.** That is exactly why flooring
boost is the right lever and flooring the corridor wasn't.

**Residual:** the `4096 − 3584 = 512` margin rests on COMP ceiling 2560 (cal **`0xC67DC`**, ~~`0xC67D8`~~ —
**ADDRESS CORRECTED 2026-08-06**) + governed clamp 1024 (cal `0xC61B4`); COMP magnitude is uncertain
(V30 residual #1) — raise the floor or trace `gp-0x6ac0` to size exactly if a larger realized COMP is
suspected.

> ⚠ **CORRECTION 2026-08-06 — the VALUE was right, the ADDRESS was wrong.** The COMP ceiling **2560 is
> at `0xC67DC`, not `0xC67D8`**; **`0xC67D8` = 512**. The structure is a **3-point LERP**:
> **X** `0xC67D2` / `0xC67D4` / `0xC67D6` = **3200 / 3800 / 4150**, **Y** `0xC67D8` / `0xC67DA` /
> `0xC67DC` = **512 / 1024 / 2560**. This also settles the reconciliation failure recorded in the V54
> memory (*"`0xC67D8` reads 512"*) — it reads 512 because it is **Y[0]**, not the ceiling.
> Recompute `tp + disp` and count LERP points before quoting any Y cell
> ([[accord-lerp-tables-count-word-first]]).

## Build

V31 = `builds/v18_v49/build_v31_tva.py` = V30 (GAIN/clamps/ramp + corridor ×4 + float mirror + PN) **+ matched flat boost
floor 4096/4.0**. 49/49 CRC, ECU-decode==patched, 31-byte diff / 22 runs, **0 executable code edits**
(independent file-level byte-diff). Output `…/39990-TVA,A160-V31-LKAS-2x-corridor4x-boostfloor4096-…rwd` +
`../accord-firmware/analysis-2020accord/_v31_plain_image.bin`. **UNFLASHED** (iron rule). Handoff `docs/handoffs/2026-06/HANDOFF-2026-06-03-v31.md`.

## Related

[[reference-accord-corridor-lockstep]] (the 3-way wall + int↔float lockstep; float twin includes boost) ·
[[reference-accord-lerp-envelope-gating]] (the corridor=driver-override-gated piece, now extended) ·
[[reference-accord-override-snap-state-machines]] (SM2/SM3 arming off the integrator; r13=authority) ·
[[reference-accord-lerp3-gp3574-chain]] (IIR input = column velocity, resolved here) ·
[[project-accord-torque-mod-v0]] · [[feedback-operator-lived-experience-overrides-analyst-recs]] ·
[[feedback-rigorous-validation]]
