---
name: reference_accord_factorc_e_damper_full_trace_r24r26_parallel
description: FUN_00034350 (gp-0x6bd0 base-assist damper) fully traced with instruction addresses; FactorC axis is VOTED VEHICLE SPEED not driver torque (corrects a 2026-07-21 memory); r24/r26 rate lanes are DIFFERENT additive terms in FUN_0003aa2c, not the same quantity as FactorC/E, confirmed from FUN_0003aa2c's decompile
metadata:
  type: reference
---

**2026-08-04, team-lead mission "map full base-assist damping surface + relate to r24/r26."** Program:
stock `code.bin` only (verified via `list_open_programs` before starting — no experimental image was
open). Full findings sent via SendMessage; durable facts below. Extends
[[reference_accord_factorc_lockstep_gate_clear_ceiling_only]] and
[[reference_accord_gp6ac2_ceiling_only_and_no_motor_command_feedforward]].

## Axis correction: FactorC's key is VOTED VEHICLE SPEED, not "voted driver torque"

`memory/reference-accord-damper-two-deadzones-factorC-factorE.md` (2026-07-21, top-level kit memory)
labels FactorC's key `gp-0x6a5e` as "voted driver torque." **That is superseded/wrong — it is voted
vehicle speed**, per the kit's own later ★★★★★★-settled finding (gp-0x6a5e = 64 cts/km/h) and
re-confirmed this session three ways: (1) same plausibility gate `gp-0x67f4==1` and bound `<=0x7d00`
used by `FUN_0003ad74`'s r24/r26 speed cross-axis; (2) FactorC's breakpoints (2240/3840/5120/8960)
divide EXACTLY by 64 into 35/60/80/140 km/h — round numbers, not the 64.0625/"9.99 km/h" approximation
the old memory used; (3) onset is **exactly 35 km/h**. Flag this axis label wherever it recurs.

## FUN_00034350 fully mapped with instruction addresses (stock, mode 10 = our PN)

```
gp-0x6bd0 = clamp( sign(-gp-0x6abe) * (seed*FactorB*FactorC*FactorD*FactorE, Q10 chained) , -ceiling, +ceiling)
```
- seed = MIN(gp-0x698a, 1024): compare `0x344e4`/flag `0x344e8`, applied `0x3461c`/`0x34620`. [OPEN]
  gp-0x698a's own producer/units not traced.
- FactorB: key gp-0x6bcc (MAX-selected driver-torque magnitude, stored `0x34438`), ptr array
  `0xC9CCC[mode*4]` → mode10 **0xD2738**, byte-read X=(205,1331,2355,3072) Y=(1024,1024,1024,1024) —
  flat/inert, confirmed live.
- FactorC: key gp-0x6a5e (speed), gate `gp-0x67f4==1` && `<=0x7d00` (else UNITY 1024, fails OPEN) at
  `0x344dc-0x344fa`, ptr array `0xC9E9C[mode*4]` resolved `0x34506`/`0x3450e` → mode10 **0xD27BC**,
  byte-read X=(2240,3840,5120,8960) Y=(0,235,430,877) — exact match to prior record, now byte-confirmed
  live. LERP body `0x34502-0x34566`.
- FactorD: key gp-0x6a10 (angle-deviation), gate `gp-0x67fe∈{1,2}` && `<9999` at `0x3456a-0x3458a`
  (else unity), ptr array `0xC9DB4[mode*4]` → mode10 **0xD2774**, byte-read count=5,
  Y=(1024,1024,1024,1024,...) — flat/inert. LERP body `0x34592-0x345f6`.
- FactorE: key gp-0x6ac0 (|motor rate|, 4.7121 cts/deg-s), gate `<0x32c9` AND a second gp-0x6abe bound
  at `0x345fe-0x34610` — **fails CLOSED (whole product → 0 at `0x34612`), unlike FactorC's fail-open.**
  Ptr array `0xC9F84[mode*4]` → mode10 **0xD27F8**, byte-read X=(60,400,2500,4000)
  Y=(0,140,539,927) — exact match, byte-confirmed live. LERP body `0x34624-0x34682`.
- Multiply chain `0x34684-0x3469c`: 4× (`mulu`+`shr 0xa`), seed*B first, then *C, *D, *E.
- Sign flip `0x3469e-0x346a2`: `if (gp-0x6abe>0) negate` — velocity-opposing, unconditional.
- Ceiling: key gp-0x6ac2 (a DIFFERENT signal — sign-mismatch/plausibility detector, see
  [[reference_accord_gp6ac2_ceiling_only_and_no_motor_command_feedforward]]), gate `<0x32c9` else
  fallback `tp+0x7158`=**0xC6158=512** (byte-confirmed), ptr array `0xC77A0[mode*4]` → mode10
  **0xD209C**, byte-read X=(300,800) Y=(512,1024) — exact match, byte-confirmed live. LERP+clamp+store
  `0x346a4-0x3475c`.
- Entry consistency check `0x34358-0x3438a` watches gp-0x6bc4/6bc6/6bc8/6bca (upstream torque-EMA
  state, NOT the FactorC/E tables) → `FUN_0004613e(0x4179,...)` → DTC 0x1c on mismatch. A FactorC/E
  Y-value edit does not touch anything this check reads.

## Numeric surface (seed=1024 max-authority assumption) — creep is HARD ZERO

Confirmed EXACTLY ZERO at every rate, 0-35 km/h inclusive (creep 4.9-8.0 km/h included), because
`lerp_flat` returns Y[0]=0 flat below X[0]=2240 regardless of FactorE — FactorC's gate alone is
sufficient, FactorE never needs to bind. At 60 km/h / 400 deg/s: 96 counts. At 100 km/h / 530 deg/s:
304 counts. Full grid in the SendMessage report to team-lead, 2026-08-04.

## r24/r26 are NOT the same term as FactorC/E — decompiled proof from FUN_0003aa2c

`FUN_0003aa2c` (the aggregator itself) computes r24 and r26 INLINE (not in a separate function) and
then sums them by plain addition alongside `gp-0x6bd0` and 8 other independently range-gated terms:
```
sum = gp-0x6ade + gp-0x6b4c + gp-0x6ad4(resonance) + gp-0x6b62(return-centre) + gp-0x6b26(friction)
    + gp-0x6bbe(boost) + gp-0x6bd0(FactorC/E damping) + gp-0x6b86(magnitude) + r26 + r24 + FUN_00036682()
```
11 additive terms total, each independently gated (contributes 0 outside its own window), NO
multiplication between lanes. r26's store is `st.h r21,-0x6adc,gp`, r24's is `st.h r16,-0x6ada,gp`,
both immediately before this sum line. **They meet by simple addition, nowhere else.** This retires any
framing where a rate-lane build (V61/V62/V67-V70) could have been dosing the same quantity as a
FactorC/E lever — confirms [[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]]'s 11-lane
count and settles the open question in the golden model's `assist_shaping_lanes` docstring.

Shared risk: both the 11-term sum AND a 2-term restricted sum (only return-centre + gp-0x6ade) are
gated by `gp-0x67ac` — if it reads 1, NEITHER FactorC/E NOR r24/r26 contribute anything. Trigger
condition still unresolved [MEMORY, pre-existing open item — "gp-0x67ac lane-suppression gate"].

## New minor path found: gp-0x6bd0 → FUN_00038148 → gp-0x6b70 → FUN_00037fe6 → gp-0x6ad6

`FUN_00038148` (decompiled) computes a SECOND, smaller weighted composite of 6 terms (gp-0x6b4e,
gp-0x6b4c, gp-0x6b26, gp-0x6b46, gp-0x6bd0 [weight tp+0x73a0], gp-0x6bbe), EMA-filtered, → gp-0x6b70.
`search_instructions` for "6b70" returns 21 hits but 19 are FALSE POSITIVES (`jarl 0x0006b700` —
absolute call-target digit collision, the documented substring-collision trap); the two real hits are
the writer (`0x382d2`, in FUN_00038148 itself) and the ONE real reader (`0x38006`, in FUN_00037fe6).
`FUN_00037fe6` (decompiled) multiplies this composite by a speed/rate LERP and clamps ±25600 →
gp-0x6ad6, which is ALREADY known closed to `FUN_0003a382`'s resonance lane
([[reference_accord_fun3a382_engagement_gated_residual_loop]], "gp-0x6ad6 CLOSED"). So FactorC/E also
very slightly raises the resonance lane's own input through an already-mapped tributary — small (own
weight cal, own EMA, gated by gp-0x67ab), not a new external system. Closes the "FUN_00038148/gp-0x6b70
downstream role uncharacterized" open item from
[[reference_accord_factorc_lockstep_gate_clear_ceiling_only]].

## GATE 2 phase, quantified AT THE RATCHET (7.79 Hz), not just 21 Hz

The kit's ZOH-lag argument that retired V44/V47 (100 Hz task-5 sample rate, "37.6°avg/75.2°worst at
20.9 Hz") is frequency-specific. Same formula (`phase=360*f*delay`, delay=T/2 avg or T worst, T=0.01s)
reproduces the recorded 21 Hz numbers exactly (cross-check), and at the ratchet's f0=7.79 Hz gives
**14.0° avg / 28.0° worst** — about 1/3 of the 21 Hz penalty, `cos(14°)=0.97`/`cos(28°)=0.88` fraction
of ideal damping authority surviving. **The phase argument that sank V44/V47 for the 21 Hz vibration
does not transfer cleanly to the ratchet.** Firmware ZOH only; plant/motor-side phase not modeled
[OPEN].

## V47's exact byte diff (from build_v47_tva.py, confirmed still the current CRC block layout via
build_v71b_tva.py:488 which still asserts 0xD2FFC as a trailer)

0xD27C6:0→235, 0xD27DA:0→234 (FactorC m10/m11 Y0), 0xD2802/04/06:0,140,539→700,750,800 and
0xD2816/18/1A: same for m11 (FactorE Y0/Y1/Y2). 23 bytes total vs V38, 2 CRC blocks (MAIN 0xC4FFC,
DAMP 0xD2FFC). **V47 WAS flashed and driven** — "marginally quieter at 5 mph, no effect in motion,"
filed against the 21 Hz vibration target, **never evaluated against the ratchet** (uncharacterized
until 2026-08-04). Delivers ≈160-184 counts hands-off authority at creep (min/max rate).

## Follow-up round (same session): seed traced, GATE-2 phase closed further, neighbor records named

**Seed (`gp-0x698a`) producer found**: sole writer `FUN_00026c80` (0x26c80, `search_instructions` 1 hit,
`st.h r16,-0x698a,gp`), decompiled in full. It is an 11-tap rolling-history MAX-reducer over a
mode-selected composite (per-sample state byte `tp+0x5124`, states 0-7 blend different raw driver-side
signals from a `gp-0x62e0[]`-relative array — base signal not further chased). **Same function ALSO
produces `gp-0x6b4c`** (a DIFFERENT additive lane in `FUN_0003aa2c`'s 11-term sum) **and the
`gp-0x67ac`/`gp-0x67ab` gate flags** (the lane-suppression gate that zeroes FactorC/E, r24, AND r26
together). **Seed is NOT a velocity/speed signal** — structurally distinct producer/RAM cluster from
both FactorC's axis (gp-0x6a5e) and FactorE's axis (gp-0x6ac0). ⇒ the damper is
`seed(urgency-like,NOT velocity) * FactorB(inert) * FactorC(speed) * FactorD(inert) * FactorE(|rate|) *
-sign(rate)` — quasi-velocity-proportional via FactorE's rising shape, gated by speed, modulated by a
third non-velocity factor, sign strictly velocity-opposing. Not a clean `b*v` damper; state it precisely.

**Task rate re-verified first-hand** (not from memory): `get_function_callers(0x34350)` → sole caller
**`FUN_00022ca0`** = the kit's established task-5/100Hz entry point [MEMORY] — independent confirmation.

**GATE-2 phase budget at 7.79 Hz, two sources stacked**: (1) 100Hz ZOH on `FUN_00034350` itself =
**14.0° avg/28.0° worst** (formula reproduces the kit's recorded 21Hz figures — 37.62°/75.24° — exactly,
cross-check); (2) the `gp-0x6abe`/`gp-0x6ac0` sensor-conditioning chain's OWN phase
[[reference_accord_common_mode_rate_signal_6abe_6ac0_full_chain]] — its own table gives **-19.9° at
7.4 Hz** (vs -39.3° at 21Hz), close enough to 7.79Hz to use directly. **Combined ≈ -34° to -48°** —
well under the 90° flip point, `cos`=0.67-0.83 of ideal damping authority retained. Motor/rack mechanical
plant phase beyond the sensor chain remains [OPEN] — not derivable from firmware bytes alone.

**±0x800 aggregator gate on gp-0x6bd0 confirmed structurally unreachable** by any FactorC/E deadzone
edit: the damper's OWN output clamp (ceiling table `0xD209C`, max Y=1024, untouched by a deadzone edit)
bounds `|gp-0x6bd0| <= 1024`, exactly half the ±2048 gate window — can only be defeated by ALSO editing
the ceiling table, which no proposal does.

**Neighbor records in the 0xD27BC-0xD2840 block, byte-read (132B, one call), 20-byte stride
(18B record + 2B pad)**: 0xD27BC=FactorC mode10 (Y=0,235,430,877) · 0xD27D0=FactorC mode11
(Y=0,234,431,877) · 0xD27E4=FactorC mode12 (Y=0,234,429,908) · 0xD27F8=FactorE mode10
(Y=0,140,539,927) · 0xD280C=FactorE mode11 (byte-identical to m10) · 0xD2820=FactorE mode12
(byte-identical to m10) · 0xD2834=a DIFFERENT table (count 6, non-flat hump Y=541-653-439,
X=0-640-2560-5120-7808-10240) — **NOT FactorC/E, pointer array/reader not identified this session.**

## Open items
- gp-0x62e0[] (seed's ultimate raw signal) and the 7 mode states in FUN_00026c80 — not chased further.
- 0xD2834's owning pointer array/reader — unidentified.
- Whether the ratchet's own motor-rate amplitude clears FactorE's 12.7 deg/s deadzone — undetermined;
  argues for opening BOTH factors together (as V47 already did) rather than FactorC alone.
- gp-0x67ac's trigger condition [pre-existing open item, still open].
- Motor/rack mechanical plant phase beyond the sensor-conditioning chain — GATE-2 residual, not
  resolvable from firmware bytes.
