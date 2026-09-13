---
name: accord-fb-pole-down-class-does-everything-but-fails-the-7hz-gate-r24-arm-is-the-blocker
description: "🛑🛑⭐⭐⭐⭐⭐ DESIGN 2026-09-13: lowering the LKAS feedback lag pole 0xC63E8/EA (16.5 Hz → 2–12 Hz, DC held) collapses Ms over 12–26 Hz 19.4 → 1.4–5.1, raises PM/GM, RAISES transient authority (pkR 1.02–1.09), 0/121 unstable, no new lightly damped pole — and FAILS the 7.3 Hz gate at every dose because 94 % of the gate damage is PHASE LAG priced against the FIXED r24 pump arm LR73 = 1.19∠−27°. A 6–18 % cut of 0xC6446 re-opens the class. fb×Kd is dominated; the P-path-only split passes the five gates but hollows out 3–4 Hz (|T(3.9)| ×2.4, parked); the gate set now carries G6–G8."
metadata:
  node_type: memory
  type: project
---

Subagent `fbdown`, 2026-09-13, `docs/specs/design/DESIGN-V291-FBLP-2026-09-13.md` (+ Addenda A–D). All
scoring on the record's own V290B machinery (304-fit family, gate73, pkR, steady state), controls
reproduced to the printed digit (V282, option C, V289, fb 25 Hz).

**What the class buys [EVIDENCE, byte-exact z-domain]:** first-order pole a/b re-solved for DC 30.891 —
12 Hz (950/1143) … 2 Hz (1011/201): max |1/(1+L)| over 12–26 Hz **19.4 → 5.1 (12 Hz) → 3.4 (8 Hz) → 1.4
(2 Hz)**; sensitivity at 20.3 Hz ×0.43 … ×0.17; crossover 15.6 → 3.9 Hz, PM +39° → +81°, GM 1.15 → 5.75;
**pkR 1.000 → 1.36 median / 1.09 worst** (the fb pole is not in the forward path, so removing inner damping
shows up as more overshoot, not less peak); steady state ×1.000; 0/121 unstable; HF motor noise ×0.74 → ×0.13;
no new pole below ζ +0.36.

**Why it fails [EVIDENCE]:** gate73 = |LS73·R73 + LR73| with LS73 = 0.55∠96°, LR73 = 1.19∠−27°; today
1.0028 — the servo's +j component cancels the r24 pump's. Any roll-off is lag at 7.3 Hz: 12 Hz reads 1.075
(magnitude-only 1.007, phase-only 1.076 — **94 % phase**). Kp-calibrated: 1.075 sits between Kp 300 (V280r2,
ripple present) and 330. The largest legal pole move is a = 925 (16.18 Hz, ×1.08 ring) — below the ×1.22 the
kit already ruled unreadable. **Never scored below 16.5 Hz before** (the 2026-09-03 rows carried DC 46, ×1.49).

**The escape:** extending the gate to |LS73·R73 + k·LR73| (k = 0xC6446/5244 — BELIEF that LR73 scales
linearly; the lane IS linear in the gain below its clamps), k = 0.939 buys 12 Hz, 0.901 buys 10 Hz, 0.861
buys 8 Hz. 5244 is V84's Lever B (stock 512): a cut is a partial revert of a non-stock edit.

**Closed axes:** fb × Kd (Kd raises 7.3 Hz phase but re-injects the 12–26 Hz gain one-for-one; Kd ≥ 160 on
V282's pole destabilises 77–112/121); 2nd-order fb LP at 6–12 Hz (fails G3/G4, up to 70/121 unstable);
output-lag pairing (93–109/121 unstable); **P-path-only split** (LP on the P operand, D on raw fb) passes the
five gates — gate 0.978, ring ×1.98, pkR_w 1.007 — but is a lead compensator built by subtraction: |R| at
3.9 Hz 0.21, |T(3.9)| ×2.37, |ΔL|<5 Hz 82–93 %, step overshoot 90–126 % — it buys 20 Hz with the 3–4 Hz band
the lane-change ring lives in. **Parked; the gate set was extended** (G6 |T(3.9)| ≤ 1.15, G7 |ΔL|<5 ≤ 30 %,
G8 overshoot ≤ 1.6× V282) and those cap the fb dose at ~8 Hz.

**Readability floor:** the record's within-drive CI ×0.34–2.01 ⇒ half-width ×2.43; C12 (12 Hz, ×2.17 SUB)
has a 2-SE interval containing 1 — **a build that cannot observe its own edit**; C10 (×2.98) and C8 (×3.81)
can. The ζ anchors in DESIGN-V290B §A.2 were CONFIRMATION, not fitting targets (the family used
windows 0.012–0.045 / −0.06–0.12); the ordering is stable across four tightened sub-families.

Related: [[accord-v291-c10-built-fb-pole-10hz-plus-r24-cut-loop-opening-class]] ·
[[accord-r24-lane-is-a-lag4-bar-difference-unit-weight-sibling-of-the-lkas-lane-damps-20hz-pumps-7hz]] ·
[[accord-filter-placement-decides-authority-not-the-filter]]
