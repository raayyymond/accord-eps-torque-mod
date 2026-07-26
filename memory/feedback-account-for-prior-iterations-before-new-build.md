---
name: feedback-account-for-prior-iterations-before-new-build
description: Standing operator instruction (2026-07-22) — before starting ANY new RWD version to address the current symptom, first take into account EVERY previous iteration (what was tried, flashed, and falsified). Do not re-propose a lever that a prior build already falsified on-car. The operator does not want to repeat this each session.
metadata:
  type: feedback
---

# Account for all prior iterations before proposing the next build

**Standing operator instruction (2026-07-22, recorded so it need not be repeated every session):**
Before starting work on a new `.rwd` version to fix the current issue, **first internalize the entire
prior build history for that symptom** — every lever tried, flashed, and its on-car result — and design
the next build so it does NOT repeat a falsified approach.

**How to apply, every session:**
- Read the current-state block in CLAUDE.md, the relevant `docs/HANDOFF-*.md`, the golden model, and the
  symptom's master dossier (for the vibration: `docs/VIBRATION-DOSSIER.md` + the theory ledger of what was
  falsified) BEFORE proposing V(N+1).
- For the vibration specifically, the falsified-lever ledger is long (V39 r24, V42 r26, V43 StageC pole,
  V44 Factor C, V45 slew, V46 StageA pole, V47 both damper deadzones, V48A a382 uVar27 ×0.25 + type-8
  mute — ALL null on-car; V48B notch cave → catastrophic RAM-collision brick). A new build that re-tries a
  single outer-assist-lane magnitude cut is a repeat of a known null — don't.
- Genuinely-new mechanisms (e.g. the FOC current-loop hypothesis, plant/tire compliance) are the point of
  a new version; incremental re-tries of exhausted levers are not.

**Why:** the operator has been burned by ~10 on-car nulls and a near-catastrophic brick. Each new build
costs a real flash + drive. Repeating a falsified lever wastes that. This pairs with
[[feedback-default-maximal-thoroughness]] (do all the analysis) and
[[feedback-cave-two-gates-ram-ownership-and-closed-loop]] (gate any dynamics change).
