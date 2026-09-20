# HANDOFF 2026-09-20 — the goal metric mapped, and the loop-gain class closed

**No firmware was built, cut or flashed. No CAN was sent. Nothing was flashed.** All work is fork-side
(analysis + two toggle configs + one unapplied patch) plus kit analysis. 13 commits, `e7dc28b` → `299467d`.

## The one-line state

**The operator's goal metric is now measured over its whole domain, and the fork-side class that could close it
is CLOSED after two pre-registered attempts.** The best defended configuration, **ARM-KP3, closes 15.9 %** of the
gap and **has never flown**. There is no licensed path to a larger number from logged drives alone.

## What the goal metric is, and where the car sits on it

`J` = total (achieved − model-desired lateral accel) power over 0.15–2.4 Hz ÷ in-band demand power, ONE
denominator across bands, ≥15 m/s, laterally-engaged hands-off runs ≥30 s. Reproduced to four figures by four
independent implementations.

| | J | vs V282 |
|---|---|---|
| V282 reference | **0.442** | 1.00× |
| rev 6.4 as flown | **1.3512** | 3.05× |
| ARM-KP3 (predicted, unflown) | 1.2064 | 2.73× |

**98 % of the gap is 0.15–0.60 Hz. There is NO gap above 0.60 Hz** (V282 0.269 vs torque 0.286).

## The five things that turned out to be true

1. **The gap is TIMING, not gain.** The gain term is 0–3 % of torque mode's own in-band error, and the gain
   *difference* vs V282 is zero or in torque mode's favour below 0.3 Hz. Torque mode arrives **+140 to +340 ms**
   late. ⇒ `|H|` is the wrong scalar; rank on in-band tracking error.
2. **The fork's loop never crosses unity** (|L| < 1 at every frequency 0.08–2.5 Hz). V282's crossed at
   0.26–0.37 Hz with 105–110° margin, **on its proportional term alone**.
3. **The shake is the PLANT, not the loop.** V282's EPS presented a rate servo — command→wheel-rate gain flat at
   61–102 deg/s per unit torque across 0.6–3.5 Hz. V293's rises with frequency to **×5.3–13** at 1.8–3.5 Hz.
   The outer loop never suppressed that mode on either build; the V282 **EPS** suppressed it internally at 1 kHz.
4. **The fork's feedback variable is the measured steering angle** through a static zero-lag map (R² 0.967–0.998,
   lag exactly 0 on 15/15 routes). **Vehicle dynamics are outside the loop**, so the wheel-angle-to-yaw deficit is
   an open-loop error no fork gain reaches.
5. **The 55–75 ms delay is NOT binding** at these crossovers (4–9° against 95–141° of margin). It is what stops
   the fork emulating the 1 kHz inner servo, not what limits the gain.

## Deliverables in the operator's hands

| file | state |
|---|---|
| `toggle-config_V293_r64_ARM-D_observer-off.json` | unflown, queued since before this session |
| `toggle-config_V293_r64_ARM-KP3_margin-safe.json` | **unflown — the recommendation** |
| `ARM-KP3_READOUT_CORRECTED.md` | supersedes the build script's G0–G7 |
| `starpilot_Dom_margin-safe-gain.patch` | **written, verified, NOT applied** — write access to the fork was denied and not worked around |
| `WITHDRAWN-DO-NOT-FLY_…ARM-RF…` · `…ARM-KP2…` · `SUPERSEDED_…ARM-KP…` | withdrawn, with reasons beside them |

**ARM-KP3** = `SteerKP` 3.0 + `AccordErrorNotchQ` 0.30 + `AccordTorqueKi` 0.60. Command shake **×0.964 — quieter
than as flown.** It is a **mechanism check scored on G0–G2, never on J** (17.6–32.2 % of NULL bootstrap draws
already reach J ≤ 1.2064). `SteerKP` 3.0 is the toggle **ceiling** (`KP 0.6 × MAX_MULT 5.0`).

## Levers closed, each on a measurement

`AccordFFRateGain` (ceiling 0.60 below 8 m/s; toggle clamped 1.5; 0.5 already rails) · hysteresis `(ceiling, band)`
(slope-bound) · symmetric static intercept (moves error between halves) · one-sided outward term (null control
void; ×1.16 into the shake band; `s_a` flat 1.000 from 4→400° so no taper) · `AccordRefFilter` (**RF = 0 already
flew on r70/r71**; whole range spans 7 % of the metric) · the delay canceller (within 8.5 ms of ideal, *faster*
than V282's) · `SteerDelay` (≤10 ms) · `HONDA_ACCORD_JERK_LP_HZ` (not toggle-reachable, 8.5 ms left) ·
**actuator saturation** (0.000 % railed above 8 m/s; V282 rails **13.8× more** below) · `SteerLatAccel` (no
low-speed taper) · `AccordTorqueKiHigh` (negative on the metric) · `AccordRateLoopGain` raises (**Gate 2 failure**).

## 🛑 THE CLOSURE — two pre-registered gates, both failed

Pre-registrations committed **before** each result: `PREREG_retrodiction_gate.md` (74a7e9d → failed 879448f) and
`PREREG_retrodiction_gate_2.md` (a8a3c56 → failed 299467d).

> **Two independent pre-registered attempts to build a controller-ordering safety statistic have failed. The
> Tier B class is CLOSED PERMANENTLY for this kit. No third repair may be proposed. Closure beyond ARM-KP3's
> measured 15.9 % requires either an instrument this kit does not have, or an EPS-side change that restores the
> inner rate servo — a firmware question, out of scope by the operator's own standing constraint.**

**Clause (b) was unsatisfiable from the moment the anchor set was fixed — a proof, not a sweep.** The three
V282old routes strictly Pareto-dominate positive r71 on *both* permitted terms at once: 3.3–6.2× on the linear
branch and 2.73× on the relay branch.

**The durable finding, worth more than the verdict: the relay is probably not the mechanism.** r71 flew
`SteerFriction` 0.011 and limit-cycled; three V282 routes flew 0.010–0.030, **equally live** under the per-commit
guard, and flew clean for months at **2.5–6.2× r71's linear loop gain**. From the wire, in the opposite direction:
the relay's chatter in the controller *output* is **1.7–1.8× larger on the CLEAN routes**.

## Errors of mine, corrected in the record

- **"The 0.020 intercept does not exist"** (05fe5ac) — **retracted at ac96fa2.** I subtracted a *linear* `k·|angle|`
  from a *saturating* map; the deficit is real, additive, +0.0231 at 0.6–2.5 deg.
- **"The friction-shaped quantity is the flat 0.033 half-width"** — retracted. F is 0.0030 at dwell start and
  0.0353 at breakaway; it is an upper bound, mostly overshoot plus detector lag.
- **"Regime B is 64 % of the gap"** — a per-band normalisation artefact. Under one denominator it is 98 % at
  0.15–0.60 Hz.
- **"The loop crosses unity at SteerKP 2.0"** — does not reproduce; first crossing is at ~2.7–3.0.
- **ARM-RF** — withdrawn; **ARM-KP2** — withdrawn on a safety finding (its margin argument was aimed at 2.34 Hz
  when the margin binds at 3.4–4.9 Hz).
- **Gate #2's own premise** — *"a jerk term is phase lead"* is **FALSE** of the term I named. `friction_jerk` is
  reference-side (`:254` planner, `:304` the controller's own past command), so `d(friction_jerk)/d(measurement) = 0`
  and it contributes nothing to L(s).
- **The `friction_hyst` guard is a PER-COMMIT fact** (first at `08a5a7064`), not per-route — which is how r73 flew
  a relay nobody intended. `lp_lib.py` had `notch=False` for r72/r73; both flew it at Q = 1.0. Fixed.

## How this session differs from the recent arc

V282→V293 were **firmware** iterations; rev 2→6.4 were **fork tuning** iterations sized by feel and single
statistics. This session did neither. It **built the operator's own metric as an instrument** (speed × frequency ×
demand amplitude, exposure-weighted, with coherence and split-half floors), then used it to retire eleven levers
and close a class. The novel move was **pre-registering falsification gates and honouring them when they failed** —
twice — including refusing the relabelling that would have passed gate #1.

## What the next session must NOT do

🛑 **"If we dropped the V282 routes it goes 3/3."** True, and exactly the relabelling the fixed anchor set forbids.
🛑 **No third repair of the ordering statistic.** Pre-registered and binding.
🛑 Do not re-propose any lever in the closed list without new on-car evidence.

## Forward questions (do NOT use them to reinterpret the gate)

- **r73's convention:** its largest oscillation by 10× is at **2.775 Hz with the driver touching the wheel**
  (`steeringPressed` 19–42 % of episodes); the 4–5 Hz chatter is the object only hands-off. Decidable from logs in
  hand, and it bears on which object the fork should be designed against.
- **Any future instrument must score FREQUENCY PLACEMENT, not amplitude** — clean r75 carries **5.5×** the
  oscillatory energy of positive r73.
- **Drive content:** the missing ingredient is **held-speed stretches**, not distance. Resolving 0.15 Hz needs
  ≥20.5 s of continuous laterally-engaged hands-off driving; almost no run stays inside a speed bin that long.
  Ask for ≥6 runs of ≥41 s held inside 8–12 m/s and ≥6 at 4–7 m/s on gentle continuous curvature.
- **0–8 m/s above p95 demand 0.3 m/s²** (14.4 % of engaged time) can never be scored — V282 has 0–2 windows there
  and is no longer flashed.
