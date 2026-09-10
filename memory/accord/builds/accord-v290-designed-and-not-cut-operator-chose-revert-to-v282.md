---
name: accord-v290-designed-and-not-cut-operator-chose-revert-to-v282
description: V290 was designed, fully specified and scored on 2026-09-09 and NO IMAGE WAS BUILT -- shown the candidate table the operator chose "Neither -- revert to V282 and stop here", taking the 20 Hz plant mode back rather than spend a drive on a x1.22 effect that cannot be read (S') or on a candidate whose worst-case transient authority is 0.928 against his own 0.95 floor (C). Also records the two class closures that came out of the round -- the Kp/Kd SCHEDULE class is capped at x2.1 ring improvement at INFINITE dose, and the knot-X lever is dominated everywhere by deepening Y.
metadata:
  type: project
---

# V290: designed, scored, NOT CUT — the operator chose to revert to V282 (2026-09-09)

## The decision, as his

**Operator, 2026-09-09, verbatim in substance: *"Neither — revert to V282 and stop here."*** He will flash
**V282** (`39990-TVA,A160-V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP-…rwd`,
sha256 `618365154e3ffdbb073c00a60173508291f0a18340d6a4f7d39cdd4b2a5b7e22`), **taking the 20 Hz plant mode
back**, rather than spend a drive on either survivor. **NO V290 image, rwd or build script exists.**

## The table he was shown

| option | 7 Hz gate ≤ 1.01 | pkR med / **worst** ≥ 0.95 | delivered ring | ζ_worst |
|---|---|---|---|---|
| **revert to V282** | 1.0028 | 1.000 / 1.000 | 545 ms | +0.0129 |
| **C** — V282 + notch 21.5 Hz Q1.5 on the **feedback operand** + fb pole 40 Hz | 1.0092 ✅ | 0.971 ✅ / **0.928 ❌** | 387 ms (×1.41) | **+0.0349 (×2.7)** |
| **S′** — V282 + Kd (112,112,112,128) + a readability cave | 1.0100 ✅ (at the limit) | 0.995 / 0.99 ✅ | 448 ms (×1.22) | +0.0178 |
| **D** = C + any schedule | 1.016–1.024 ❌ | 0.92 ❌ | — | — |
| **B/B′** — any schedule on the **V289** base | 1.012–1.020 | **0.806 ❌ at every Kd** | — | — |

**Both survivors failed a different one of his own constraints, and neither failure was hidden from him.**
S′ is legal but **unreadable from one drive** (its within-drive contrast is unbiased and **2.6× too
imprecise**, and the two operator-facing channels are confounded **in the flattering direction** — low-demand
rings are already 41 % quieter and half as long on the base builds). C buys ×2.7 damping but costs 0.928 of
worst-case capped-step peak rate.

## Two class closures from the round — do not re-propose these

| claim | status | method |
|---|---|---|
| **The Kp/Kd SCHEDULE class is capped at ×2.1 ring improvement at INFINITE dose** | EVIDENCE | delivered dose = grinding-episode-seconds-weighted mean over pooled r62+r63 (25.5 s, 2553 samples). `Y[0..2] = 0` — deleting D below the knot, an absurd build — reaches only 257 ms (×2.1) and blows the 7 Hz gate to 1.0604. Cause: **~half of grinding seconds sit above the knot (idx 32)**, where every Y-only record is byte-identical to base |
| **Moving the knot X is DOMINATED everywhere by deepening Y — the X lever is CLOSED** | EVIDENCE | S80 (313 ms at gate 1.0243) beats X64 (338 ms at 1.0255) on **both** axes, with 2 fewer bytes and in the safer byte class; the domination holds along the whole (effect, gate) frontier, because an X extension buys reach by spending exactly the full-lock protection it was chosen to preserve |
| **The V289 base is dead for any calibration edit** | EVIDENCE | pkR 0.799–0.807 at **every** Kd 64–128, because V289's notch sits in the reference transfer and no cal edit recovers it |
| **The added post-lag term class is closed on the surviving plant, either sign** | EVIDENCE | minus drives the 16.4 Hz pole to ζ −0.082; plus removes it but the crossover reappears at 26.9 Hz ζ +0.006 — (1−N)/8 bypasses the 5 Hz output lag and re-injects the 20 Hz content the notch removed |
| Option C is **implementable** | BELIEF (dynamics EVIDENCE; the hook is traced but the build was never attempted) | hook `0x28F4C` (`ld.h -0x6a56,gp,r7`, `24 3f aa 95` → `89 07 44 bd`), cave `0xC4C90` (868 B free, CRC `0xC4FFC`), notch Q14 `b0=b2=15680`, `b1=a1=−31074`, `a2=14976`, ±12000 clamp, fb pole `0xC63E8/EA` → 796/3522. ⭐ `0x28F4C` sits **below** the engagement guard, so the cave runs every tick and needs **no sentinel seeding** |

## Pre-registered revert signature for C, if it is ever cut

C **re-creates** the 16 Hz object — a pole at 16.5 Hz, ζ_med +0.057 in 100 % of surviving fits, better
damped than V289's but **inside the burst range the operator has already rejected**. Watch for a 15–18 Hz
line in trains, grinding lower-pitched than V282's, a new 10–14 Hz line (C's sensitivity there is ×2.0
V282's), audible HF hiss (rms |R| 30–500 Hz ×1.91). 🛑 **If C's 16.5 Hz pole is audible, the ENTIRE
loop-shaping class is closed — both placements, both bases, and the Kd schedule — and V291 must come from
outside it.**

**Why it matters:** three separate design rounds this session produced candidates, and the binding
constraint turned out to be the operator's authority floor and the readability law, not the physics.
See [[accord-filter-placement-decides-authority-not-the-filter]],
[[accord-kp-kd-schedule-x-axis-is-demand-index-16-125736-per-lsb]],
[[accord-clamped-loop-parametric-modulation-hazard-v290-kd-schedule-safe]],
[[accord-v289r1-flew-the-ring-moved-to-16hz-revert-signature]],
[[accord-20hz-line-is-plant-mode-clamp-explanation-falsified-two-line-census]].

**How to apply:** do not propose a Kp/Kd schedule edit for the grinding again without pricing it at the
**delivered** (episode-seconds-weighted) dose, not the nominal `Y[0]` — the nominal reading over-states the
effect ~5×. Do not propose an X-knot move at all. Do not build from
`docs/specs/design/DESIGN-V290-2026-09-09.md` (the first, refuted memo). If the operator later relaxes the
worst-case transient-authority floor, option C is ready to cut as specified above; sources
`docs/review/V290-BASE-DECISION-2026-09-09.md` (**read its ADDENDUM — it supersedes the body's ranking**),
`docs/review/V290-DECISION-TABLE-2026-09-09.md`, `docs/specs/design/DESIGN-V290B-2026-09-09.md`,
`DESIGN-V290-TELEMETRY-2026-09-09.md`,
`docs/traces/TRACE-2026-09-09-v290-feedback-operand-hook.md` (+ its ADDENDUM).
