# PRE-REGISTRATION — the retrodiction gate for the repaired controller model

**Written and committed 2026-09-20, BEFORE the repaired statistic was computed.** The point of committing this
first is that the gate cannot be moved after the result is seen. Commit hash of this file is the proof.

## Background, in one paragraph

The frontier engine that produced this study's closure ladder (Tier A 16–33 %, Tier B 49–80 %) **failed its only
labelled test**: it cannot retrodict route 71's limit cycle from route 71's own flown parameters. Only 0.29 % of
loop gain over 2–6 Hz separates r71's controller from r72's in its model; on a plant × controller cross-table it
ranks r72 (flew clean) riskiest in two of three bins and V282's controller worst on every plant; and on r71's own
plant it reads r71 safe (0.893) and rev 6.4 — flying now — unsafe (1.042). Consequently **every Tier B number is
unfounded**, and ARM-KP3 is demoted to a mechanism check.

A **physical** model does retrodict, and it is the fork's own: `J·θ'' + b·θ' + k(v)·θ = torque` with
`J = HONDA_ACCORD_EPS_INERTIA = 8e-5`, `k(v) = HONDA_ACCORD_HOLD_K_V` — the model behind
`get_honda_accord_mode_hz` (`sqrt(k/J)/2π`, verified in source at the flown commit). With r71's `SteerFriction`
relay included it predicts |L| 1.29–1.54 at a −180° crossing at 2.45–2.63 Hz (observed 2.34 Hz, 5–12 % error);
with the relay omitted — which is what the engine does — it predicts stable. **The missing term is in the
CONTROLLER model, not the plant.**

## The repair to be made

1. **The `SteerFriction` relay as a describing-function gain**, added to `kp` on `error_with_lsf`. Note the guard:
   `latcontrol_torque.py:675` sets `friction_torque = 0.0 if friction_hyst > 0.0`, so the relay is live only when
   `AccordFrictionHyst == 0`. Per-route `SteerFriction` and `AccordFrictionHyst` must be read from each route's
   **own `initData`** — this fork back-fills absent keys with stock values (route 6d carries a back-filled 0.2120).
2. **The `AccordRateLoopGain` inner loop** on measured `steeringRateDeg`, live at 0.001 on rev 6.4, against the
   fork's own note (`latcontrol_vehicle_tunes.py:281-286`) that 0.0012 "would cross" −180° at 3.5–4 Hz.

## 🛑 THE GATE — both clauses must pass, judged on these exact terms

**(a) RANK.** The repaired statistic must rank **r71's controller riskiest** on a plant **NOT taken from r71's own
log** — i.e. on r72's, r73's, T64's or V282's identified plant. Rationale: r71's plant estimate is contaminated by
the very instability being retrodicted, so a statistic that only works on r71's own plant has proved nothing.
*Minimum:* riskiest on **≥ 2 of the 3** non-r71 plants with enough data.

**(b) SEPARATION.** The statistic must separate r71's controller from r72's by **more than its own route-cluster
bootstrap CI** — the two CIs must not overlap. Rationale: the failed engine's separation was 0.29 %, i.e. noise.

**(c) NO FALSE ALARM (added because the failed engine produced one).** It must **not** rank rev 6.4's flown
controller — which has driven without a limit cycle — as riskier than r71's on any plant.

## What each outcome licenses — written now, binding either way

**IF THE GATE PASSES:** re-derive the closure ladder on the repaired statistic. Tier B may be restored, revised
down, or killed; whatever it says is what the operator is told. A restored Tier B still needs its own margin
numbers quoted against the retrodicting model, never against the failed VM.

**IF THE GATE FAILS:** this sentence is licensed and is to be reported as the result, not as a setback —
> *No statistic available to this kit orders the flown anchors by controller. The Tier B class is therefore
> CLOSED at any dose until the instability mechanism itself is modelled — not until a better estimator is found.*

That null costs **zero drives** and it is class-closing. It does not affect ARM-KP3, which is defended on the
retrodicting physical model (bounded ×1.46 step, crossing moved to 1.5–1.8 Hz) and on hand-verified notch algebra,
not on the failed statistic.

**IN EITHER CASE**, the repaired statistic replaces `VM = min|1+L|` as this study's safety currency, and the
falsified axes — VM and shake-band `|L|` — are struck. Both failed the same way: they do not order their own
anchors.

## Guards against the ways this could be fudged

- The gate is judged on the **flown anchors only** (r71 limit-cycled; r72, r73, T64, V282 flew clean). No new
  labels may be invented.
- The describing-function gain must be derived from the fork's own arithmetic, not fitted to make r71 fail.
- A statistic that passes only by using r71's own plant fails clause (a) by construction.
- If the repair requires more than the two terms above to pass, that is a **fail** — it means the model is being
  tuned to the answer.
