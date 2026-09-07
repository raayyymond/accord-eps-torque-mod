# PRE-REGISTRATION — V287, the output-lag pole, read from ONE drive

Written **2026-09-06, BEFORE any build and BEFORE the drive.** Subagent `shape`.
Full derivation: `docs/research/GRIND1-LOOP-SHAPE-V287-2026-09-06.md`. Script: `grind1_loop_shape_v287.py`
(re-run it to reproduce every number below). **Do not move a threshold after the log lands.**

**Build.** **V287 = V282 + two calibration halfwords**, base V282 (on the car, confirmed on the wire):

| addr | tp offset | cell | now | becomes |
|---|---|---|---|---|
| `0xC63EC` | `tp+0x73ec` | LKAS rate-PID output-lag pole `a2` | 992 | **974** |
| `0xC63EE` | `tp+0x73ee` | LKAS rate-PID output-lag gain `b2` | 507 | **792** |

🛑 **PRE-FLASH GATE — DO NOT CUT THIS BUILD UNTIL IT IS CLOSED.** `0xC63EC` and `0xC63EE` each have a
**second reader** at `0x2A892` / `0x2A8A2`, inside the orphan Ghidra-undefined `0x2A400-0x2B600` region —
and that region is **not all dead** (`0x2B422` and `0x2B57A` are `jarl`ed from `0x22530` / `0x22572`).
Resolve those two readers first: `create_function` at `0x2A892` in a **scratch** import, never the shared
project, then decompile. If they are live, these cells are not private, the edit silently moves a second
lane, and the build is off (GATE 1 ownership failure).

✅ **GATE CLOSED, 2026-09-06** [EVIDENCE — `firmware-codepath-tracer`, memory `reference_accord_gate1_pole_cells_unreachable_dispose_is_a_return`]. The second readers at `0x2A892` / `0x2A8A2` are **UNREACHABLE**: `0x2A504`, the target of every `jr` from `FUN_0002a30e`, is a `dispose ..., lp` — a RETURN — so there is no fall-through into the duplicate block at `0x2A508`, zero branches enter it from outside (a 7-of-7-controlled scan, every raw hit adjudicated as a `prepare` prologue) and no immediate can construct its entry. **The lag poles pass GATE 1 and are private in effect.** Proved with dry-run disassembly and raw Python only; no Ghidra mutation and `save_program` not called.


Pole 5.05 → **7.97 Hz**, DC gain held at 0.990000 (−0.024 % vs 0.990234). **Cal-only, no code byte, no authority
change, no new probe.** Both cells are 992/507 in **all 285 images ever built** — never touched, not falsified.
Kp flat 248, Ki 0, Kd 128, `0xC6446` 5244, fb pole 923/1560, fb clamp 46080, output clamp ±3072, ×6 forward gain: all
unchanged. Build script must recompute the cal-page CRC and read both halfwords back from the built image.

## Why

The output-lag pole is the only never-touched cell in the LKAS rate PID whose sign is right for **both** symptoms: it
adds phase lead at 7 Hz (where the aggregator is a mild net pump, `Re` −0.23) and at 20 Hz (where the servo lane is
mostly quadrature). But it is a **waterbed** lever, not a damping lever: every dose cuts 18–22 Hz by growing 26–33 Hz,
and the sensitivity peak is **already at 26.3 Hz today**. The record's headline shape (932/1457, a 15 Hz pole) takes the
modelled gain margin from 1.77× to **0.72×** and is a **DO-NOT-FLASH**. 974/792 is the unique dose that is
simultaneously (i) small enough that its modelled margin, 1.19×, has a Kp-equivalent of 589 — inside the stock Kp LERP
top of 696 that every build before V281 rev 3 flew; (ii) large enough that one endpoint clears its route-to-route noise
floor; and (iii) large enough to **separate the two plant models** by 2.21× on a band whose spread is 1.25×.

**A SECOND, INDEPENDENT CEILING AGREES, AND IT IS NOT MONOTONE.** Honda's oscillation-reversal detector
(`FUN_000428d4`) counts alternate crossings of ±`cal(0xC620A)` = 12800 on `gp-0x6c2c` (a filtered motor
rotor-rate signal, on the MOTION side), resets if `cal(0xC64DD)` = 50 ticks pass between crossings, and
after 15 reversals applies a **live x0.600 cut to motor demand** through governor slot 2. Replaying the
19 measured creep and bookmark windows through each dose's sensitivity ratio and mirroring the counter:
**0 of 19 windows reach 15 reversals at any dose up to 8.0 Hz, and 8 of 19 FIRE at a 10 Hz pole.** So the
detector ceiling and the gain-margin ceiling agree, and 974/792 sits below both. (Its input filter
`0xC40DC` is already non-stock on V282 — 14 vs 22, corner 39.4 vs 67.1 Hz — but it is only 2.0 dB down at
30 Hz and does not protect against this lever's rise.)

**Treat it as a discriminator, not a cure.** Deciding the plant question settles the premise behind `Ku = 227`, behind
every high-frequency risk verdict in this kit, and behind the V255/V269 post-mortem.

## Stratum, identical for every statistic

Engaged **lateral** (`0xE4` STEER_REQUEST **and** `0x18F` STEER_CONTROL_ACTIVE), hands-off (`|bar| < 400` raw),
`vEgo` 1–3 m/s, contiguous runs ≥ 2 s, all streams de-jittered onto their nominal frame counters
(`creep20_loop_id.dejitter`). Comparators: **r39, r3a, r3c** (all V282) and r35 (V281 rev 3).

## Predictions

| # | statistic | today (r39 / r3a / r3c) | predicted on V287 |
|---|---|---|---|
| **P1** | 0x18F rate **18–22 / 26–33** band ratio | 2.766 / 1.388 / 3.983 | **× 0.335** |
| **P2 (GUARD, the decider)** | 0x18F rate **26–33 / 2–6** | 0.2596 / 0.3240 / 0.2814 | **× 2.58** (delay plant) **or × 1.03** (frozen plant) |
| **P3 (SHELF)** | 0x18F rate **33–49.9 / 2–6** | 0.2140 / 0.1962 / 0.2298 | × 1.47, must not exceed × 2.0 |
| **P4 (RING)** | 7.3 Hz episode `\|L_tot\|`, the n = 8 pool estimator | 0.980 [0.971–0.983] | **0.822** |
| P5 | 0x18F rate 18–22 Hz raw | 1.147 / 0.540 / 1.351 | × 0.76 — reported, **not decisive** (2.50× route spread) |
| P6 | ∠(T/rate) @ 20.31 Hz | −114.8° / −85.2° / −114.5° | +7.4° → −107.4 / −77.8 / −107.0 — **not decisive** (30° spread) |
| P7 | 0x14A byte 4 bit-6 duty | 0.0906 / 0.0345 / 0.0621 | **× 0.968** → 0.0877 / — / 0.0602 — **not decisive** |
| **P9 (DETECTOR)** | motion per unit torque: 0x18F rate 18–33 Hz over 427 T 18–33 Hz, in the 0.375–0.5 s after each grind onset | no x0.6 step in the record | **unchanged**; a x0.600 step means the reversal detector fired |
| P8 | 427 tap 18–22 Hz amplitude | 17.1 / 9.3 / 25.1 | rises ~× 1.15 — **the tap moves the WRONG WAY by design; do not score on it** |

P5–P8 are registered so they cannot be reached for after the fact. **They cannot resolve this dose and they license
nothing**, in either direction.

## Decision rule

- **P2 ≥ 2.0** ⇒ the **delay plant is confirmed** in the blind band for the first time. `Ku = 227` stands, no further
  pole raise is ever flyable, and the loop-shape axis for grind #1 is **CLOSED**.
- **P2 ≤ 1.3** ⇒ the **frozen plant** is right above 25 Hz. The blind band is not the hazard the record treats it as,
  and **932/1457 becomes a legitimate candidate** — cut it next with this same pre-registration.
- **1.3 < P2 < 2.0** ⇒ licenses nothing about the plant; gather creep exposure and re-read.
- **P1 ≤ 0.5 and P2 ≥ 2.0** ⇒ the waterbed is confirmed end to end: the edit moved the grind, it did not cure it.
- **P1 ≤ 0.5 and P2 ≤ 1.3** ⇒ the only genuinely favourable outcome. The pole is the lever and the dose can be raised.

## FAIL

**FAIL:** *over ≥ 20 s of engaged lateral hands-off creep, P3 exceeds × 2.0 of the V282 median, **or** P4 reaches 0.980
or above, **or** the 427 tap's saturation rate rises above 0.0 %, **or** any DTC appears that V282 did not produce, **or** P9 shows a x0.6 step in motion per unit torque that
V282 does not show.*
Any of those and the output-lag pole is not a safe axis at any dose — strike the shape family.

**COST FAIL, and it outranks every number here:** *the operator reports a new vibration, buzz or noise at a higher
pitch than today's grind, or any worsening of grinding, vibrating, micro-ratcheting, ratcheting or excess friction.*
Report symptoms in his words. An absence of a complaint is not a report of improvement.

## Risk, stated before the drive

Authority is unchanged (DC gain held to 0.024 %; no clamp, no gain, no Kp/Ki/Kd cell moves). **The risk is a new,
higher-pitched vibration.** The 26–33 Hz motion is predicted to rise **× 2.28** and the modelled sensitivity peak grows
from 2.38 at 26.3 Hz to **6.56 at 28.7 Hz**. Under the optimistic plant that rise is only × 1.03 and there is no new
peak — **the drive is what decides between those two**. The modelled gain margin falls 1.77× → 1.19×, a margin this car
flew for 280 builds at the top of the stock Kp LERP, but always-on rather than on high-demand-index frames only.
**If anything feels worse in any way, stop the drive.**

No overflow is possible: holding the DC gain holds the filter state magnitude, so int32 headroom is 9.1× (vs 8.9×
today) and the `sxh` at `0x0002A1EC` is bounded at `|v| ≤ 21389 < 32767` — the same bound as today, by construction.

## What refutes this pre-registration

P2 rising while P1 **also** rises (both bands up ⇒ the edit is a broadband gain change and the sensitivity framing is
wrong); or P4 rising rather than falling (the 7.3 Hz ring's servo arm does not scale with `H_lag`, which would
invalidate the two-arm composition the ring guard rests on).

## The cave bit: NOT spent, and why

The only in-place rung available is `bit = (abs(gp-0x6c2c) >= abs(gp-0x6c2e))`, and it costs **bit 5**
(the legacy bits 3 and 7 are single-operand sign rungs; converting one needs about +0x22 bytes, a length
change and a relocation — not the V282 class of edit). The exact edit, if it is ever wanted, is two
halfwords: **`0xC4B64-65` `26 95` -> `d4 93`** (hw2 `9526` -> `93D4`, gp-0x6ADA -> gp-0x6C2C) and
**`0xC4B70-71` `6c 94` -> `d2 93`** (hw2 `946C` -> `93D2`, gp-0x6B94 -> gp-0x6C2E); `hw1` stays `3724`,
both displacements even so both stay `ld.h`, plus the page CRC at `0xC4FFC`.

**Not spent at this dose**, because the rung's predicted duty moves only **x1.013** (0.5604 baseline)
against a **1.53x** baseline spread across the same 19 windows, while the 0x18F `26-33 / 2-6` guard
already on the wire moves **x2.58** against a **1.25x** spread; and because detector FIRING is directly
observable with no new instrument at all, as P9. Spending bit 5 would also turn a cal-only build into a
cal-plus-code-region build for no measurement gain. ⭐ **This flips at a 9 Hz pole or above**, where the
rung's prediction (x1.26) clears its spread and the 0x18F guard stops being reliable because the action
moves to about 30 Hz.

## The half-step, if the operator prefers the margin

`0xC63EC` = **979**, `0xC63EE` = **713** (pole 7.15 Hz). Modelled GM **1.30×**, which matches creep20's *measured*
1.32× at Kp 470 — the strongest empirical anchor available. But its plant separation is only 1.64× and P1 (× 0.484)
does not clear its 2.87× spread, so **that drive could falsify but never confirm.** Named here so the choice is
explicit rather than implicit.

## Amendments — adversaries A and D, 2026-09-06 (full derivation in the report, §B8)

1. **Q1 IS CONDITIONED.** With Ki 0 the sum is `P + D` and the sum clamp binds at `|P+D| ≥ 15481`, so on a
   tick where P is already railed at ±15360 **and** `sign(D) = sign(P)` the edit is bit-identical at the
   output. **Q1's binding-tick set is restricted to `(|P| < 15360) OR (sign(D) ≠ sign(P))`.** Measured
   surviving fraction of 2560-binding ticks: **75.5–100 %, median 97.3 %** — and **exactly 100 % in the
   creep stratum and in the r35 incident**, the windows Q2 and Q3 are scored on. Do **not** read a masked
   tick as a Q1 miss.
2. **BIT 6 IS SCORED DIFFERENTIALLY, ONSET MINUS STEADY, ON THE SAME DRIVE.** `bit 6 = (|r24| ≥ |T|)` and
   T's onset kick shrinks, so the onset duty rises mechanically — arithmetic about the comparator, not
   evidence about r24. 🛑 **V282's absolute 0.22 / 0.10 thresholds DO NOT TRANSFER to this build.**
   Predicted shift where bit 6 is even alive: **×0.98–1.11**. On the loaded onset ticks themselves bit 6
   is **identically 0.0000** (|T| ≥ 600 counts), so the effect is confined to low-|T| frames and is small.
3. **THE 102 DEADBAND IS GATED OFF ENGAGED.** `0xC61B8`'s rung at `0x2A1BC` runs only when
   `gp-0x6806 == 0`, and that cell is non-zero when engaged. B7.4's conclusion holds *a fortiori*. 🛑 The
   attribution of r39's stall runs to this rung is **STRUCK**, and the record's label *"the P-only
   deadband = `0xC61B8`"* is **WITHDRAWN pending re-derivation**. No statistic in this pre-registration
   depends on it.
4. **`0xC61B6` census:** 7 sites in 2 functions — 4 live in `FUN_00028ea6` plus 3 in the unreachable
   duplicate `FUN_0002a93a`. GATE 1 passes. ⚠ **D and the PID sum (`gp-0x6b36` / `gp-0x6b34`) are
   WRITE-ONLY and not on the wire**, so the clamp's binding is observable **only** through T via the
   mirror — which is Q1, and is why its conditioning matters.

---

## 🛑 SUPERSEDED 2026-09-06 by APPENDIX C — adversary B FAILED the 2560 dose

`docs/review/ADV-V287-B-UNITS-STRATA-2026-09-06.md` returned **FAIL** on F2 and F4, and I accept it.
In three ordinary strata this pre-registration never sampled — hands-on `|bar| > 700`, loaded
`|ang| > 60`, fast wheel `> 25 deg/s`, together 20–28 % of engaged time — 2560 is a **local Kd cut**,
not an excitation limiter (D_sp-dominance 33–38 %, p99`|D_fb|`/clamp 2.2–2.4), taking the effective Kd
in the loaded stratum to **95.4** and the 7.3 Hz ring to **`|L_tot|` = 1.038**. Three of its endpoint
thresholds were also inside their own spread.

**THE RE-SIZED SPECIFICATION IS IN APPENDIX C §C5 OF THE REPORT.** In short:

- **Dose 7680, not 2560.** It is the largest dose whose ring stays at or under the gate (`|L_tot|` =
  **0.983**, exactly at the CI upper bound) and the only one besides today's that is admissible in every
  stratum — borderline, at 79.7 % dominance in the SUBURBAN stratum where today's 10240 sits at 84.7 %.
- 🛑 **NO DOSE IS BOTH SAFE AND MEASURABLE ON ONE NORMAL ROUTE.** 7680's onset effect is ×0.947 (r39)
  / ×0.930 (r3c) against a 2-SE resolvability bar of ×0.914 / ×0.701. Every dose that clears the bar
  fails the ring gate. **The class is a PARTIAL MITIGANT.**
- ⭐ The onset endpoint is **route-wide and does not need the symptom to occur**, so its `n` grows with
  engaged time: 7680 becomes resolvable at **≈ 1,150 onset events ≈ 38 minutes of engaged driving**.
- Threshold fixes carried into §C5: **Q5 FAIL at > 0.983** (was 0.980, inside its own CI); **Q6 FAIL at
  > ×1.6 on ≥ 20 windows** (was ×1.3, inside the ×1.52 route spread); **Q2/Q3 defined on route-wide
  command-step onsets** so they exist on any drive; **Q10 added** on the loaded stratum's 6–9 Hz and
  18–22 Hz rate bands (FAIL above ×1.9 / ×2.3, clear of their ×1.44 / ×1.86 route spreads); **Q1 keeps
  the P-rail conditioning.**

---

## rev 2 — adversary B PASS WITH CONDITIONS, 2026-09-06.  Full text in the report §C5.

**Conditions before flashing, per adversary B: (1) the ring gate adjudicated via Q10 + the operator's
stutter report, not Q5; (2) Q2 scored PAIRED; (3) Q6 raised to ×1.9.**

1. ⭐ **Q2 IS PAIRED, WITHIN-DRIVE.** Per-event ratio of the **measured** 18–22 Hz onset envelope to the
   **10240-mirror** prediction on the **same drive and the same events**, in **1.0 s windows** (0.5 s is
   only 25 tap samples — too few for an 18–22 Hz estimate on a 50 Hz stream). Predicted **×0.957**.
   **PAIRED SE = 3.24 % (r39, n 435) / 4.99 % (r3c, n 229)**, measured as the spread of measured-tap ÷
   mirror on V282. ⇒ **needs n ≥ 651–811 onset events ≈ 22–27 minutes of engaged driving.** Better than
   the unpaired 38 min, but ≈ 1.5 normal routes rather than one — recorded as a difference from B's
   reading rather than smoothed over.
2. 🛑 **Q5 IS DOWNGRADED TO REPORTED.** The loaded 6–9 Hz multiplier that the `|L_tot| ≤ 0.983` gate
   rests on is measured as **0.941** (mine, pooled), **0.9895** (mine as read by `team-lead`) and
   **0.9756 / 0.9693 / 0.9832** (adversary B, per route) — a span **wider than the gate's whole margin**,
   and not stable even between my own poolings. **The ring FAIL criterion is now Q10 plus the operator's
   own stutter report (Q11).** ⚠ **OPEN RECONCILIATION:** those three measurements must be reconciled on
   one pooling before any future build leans on this gate. This also brings the prereg back in line with
   the standing rule that `|L_tot|` is licensed only as a ratio between candidates.
3. **Q6: threshold ×1.6 → ×1.9**, and the definition now reads **route-wide 2 s tiles, ≥ 20 required**
   (B's route-wide spread is ×1.83).
4. **Q10 is the ring gate**, FAIL above **×1.9 (6–9 Hz)** / **×2.3 (18–22 Hz)** at `|ang| > 60`; B
   recomputes the route spread at ×1.09 / ×1.30, so the margins are ×1.75 / ×1.78. **Q11 — the
   operator's own stutter report — outranks it.**
