---
name: accord-six-levers-closed-on-arithmetic
description: "Six candidate levers closed in the 2026-08-11 V90 session — 0xCBE74 (no larger dose exists: int32 wraparound at 1.6005x, and x1.5 is already 5-69x below the resolvability floor), 0xC63A6 (inert in regime on a PRE-REGISTERED threshold), the Kd cut (D damps 16-35 Hz, cost 3-4x the benefit), K1 (collinear with |model| above 1 deg/s), term 0 / mixer lane 2 (severed by 0xC616C = 0), and the 0xC520C governor as the return explanation (misses by 8.3x). Five of the six die on ARITHMETIC, not on a null."
metadata:
  type: reference
---

# Six levers closed, 2026-08-11 (the V90 flight session)

🛑 **A lever killed by ARITHMETIC cannot be re-opened by more exposure or a bigger dose.** Five of these
six are in that class. Grep this file before proposing any of them again.

| lever | why it is closed |
|---|---|
| **`0xCBE74`** friction-comp gain | **No larger dose exists, ever.** `FUN_00036c12`'s `mul r13,r6,r0` (×0x111, high half discarded) is **unclamped and UPSTREAM of `0xC407E`**; int32 wraparound is structurally impossible only for **≤ 1.6005×** ⇒ **×1.5 is 94 % of the lever's ENTIRE range.** Above that it does not pin — **it WRAPS, a full-scale sign inversion on the damping lane delivered before the clamp meant to contain it.** And at ×1.5 the delivered damping is **5–69× below the 11 % resolvability floor** in every band (6–9 Hz 0.16 % of the 208 ct engaged median · 18–22 Hz 1.20 % · 26–31 Hz 2.15 %). ⚠ Flown anyway as **V91**, by the operator's explicit decision with that verdict in front of him |
| **`0xC63A6`** friction-lane Path-2 weight | **Inert in the regime, on a PRE-REGISTERED threshold.** Micro-regime `\|gp-0x6b26\|` **p50 = 7.1 counts = 0.22 %** of the ±8192 residual clamp, against a stated **≲32 ct do-not-fly** line. It failed a bar written before the number existed |
| **the `Kd` cut** (`0xC6AE6/E8/EA/EC`, all 2048) | **A TRADE whose cost is 3–4× its benefit.** `Re(Z)` extended to 35 Hz: **D pumps ONLY 2–12 Hz and DAMPS 16–35 Hz.** Removing the **+0.077** pump at 6–9 Hz costs **−0.217 at 18–22 (2.9×)** and **−0.336 at 26–31 (4.4×)** — the operator's own two grinding bands |
| **K1 / friction** (`0xC40D2`) | **STRUCTURAL, not a power problem.** Above 1 °/s friction and `\|model\|` are near-collinear: `P(b5\|b6=1)` = 0.986 → 1.000, discriminating cell `(b6=1, b5=0)` = **0.63 %** of engaged frames. The term cannot be moved independently of the model in the regime the operator names |
| **term 0 / mixer lane 2** into `gp-0x6ad6` | **Severed by one zero constant** — `0xC616C` = 0 ⇒ `gp-0x6b76` is 0 or a `0x7fff` sentinel on every path. See [[accord-c616c-never-raise-driver-torque-relay]] |
| **`0xC520C`** governor ceiling as the return-complaint explanation | **Misses by 8.3×.** Pooled engaged returns median **127.2 counts** against a first breakpoint at **1050**; at 40–80 km/h max **35 counts (7.4 °/s)** against a **222.8 °/s** onset. Refutes `FEASIBILITY-8X-LKAS.md` Part 2 (which needs **724.6 °/s**); confirms its Part 1 |

⊕ **What survives on `0xCBE74` and is worth keeping**: its GATE-2 position is the best of any dynamics
lever in the kit — describing-function gain **exactly 1.000 through ×4**, the ±1024 zero-reject **can
never fire** (`0xC407E` clamps to ±511 first), the dissipative sign is closed **structurally**, and
**`H(0) = 0` EXACTLY** (proven three ways, including in the fixed-point integer arithmetic) ⇒ **it
contributes nothing at any sustained steering rate, at any multiplier — the operator's "do not limit
max LKAS steering angle rate" constraint is satisfied STRUCTURALLY.**
⚠ **But at 7.79 Hz the term is 97.2 % REACTIVE** (added apparent inertia, which lowers both `ω0` and
`ζ`) ⇒ **better supported for grind #1/#2 than for the ratchet**: matching grind #1's dissipative
delivery needs ~6.1× more gain, grind #2 ~9.2×, and there is no headroom.

Full narrative: `docs/HANDOFF-2026-08-11-v90-flew-and-the-lever-search-closed.md` §2.
Related: [[accord-anti-damping-is-not-the-pid]] · [[accord-c616c-never-raise-driver-torque-relay]] ·
[[reference-accord-cbe74-friction-row-zero-clean-flights]] ·
[[accord-c407e-is-the-fault-interlock-c63a0-exonerated]] · [[accord-check-build-lineage-before-proposing-lever]]
