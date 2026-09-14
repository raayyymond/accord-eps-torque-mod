# Design note — if an inner loop ever comes back, which quantity? (2026-09-13)

**Context.** V293 opened the EPS's LKAS rate loop (fb clamp `0xC62E6` = 0). Route 70 measured the plant
that is left: a **spring plus Coulomb friction**, `u = a(v)·θ + b·θ' + F·sign θ'` in openpilot torque units
(`V293-PLANT-IDENT-2026-09-13.md`), and the operator's primary new symptom is **ratchety snapping between
angles** — dwell-then-jump events 3–23× V282's at the same steering activity, while the 0xE4 command is
2.9× *smoother* than on V282. Snap size ≈ `2F/k(v)`: the friction band expressed in angle. V282 had two
friction linearisers, both removed on the same drive: the EPS's 1 kHz rate servo and the fork's dithering
`d(angle_des)/dt` feedforward term.

The operator asked (2026-09-13, verbatim): *"something we may need to look into in the future is
introducing just enough closed-loop LKAS inner loop control, issue is that it isn't controlling the right
quantity... or what if we made the E = setpoint − (derivative of filtered angular velocity or filtered
derivative angular velocity)?"*

## What each inner-loop error signal turns the plant into

With `J·α = T − c·ω − k(v)·θ − F·sign ω` (J not identifiable below 1.5 Hz; k soft below 8 m/s):

| inner error `E` | the P term adds… | effect on the friction band `2F/k` | what openpilot's outer loop then sees |
|---|---|---|---|
| `setpoint − dω/dt` (**angular acceleration**, the operator's proposal) | electronic **inertia** (`J + K_P`) | **none** — the wheel is slower to break away and slower to stop, the band is unchanged | command → angle becomes a **double integrator** — worse than V282's single integrator. The kit's `TRACE-2026-09-13-lkas-pid-tracked-quantity.md` §4 already scored this DOMINATED (it contains torque mode and adds inertia). The derivative of the 0.125 deg/s-quantised rate needs so much filtering that the loop has no authority at the dwell timescale (4–9 Hz) |
| `rate setpoint − ω` (**V282**) | electronic **damper / rate servo** | linearised it (drives against rate error every ms) | an **integrator** (command → rate), which is why the fork needed the rate-plant feedforward hack — "not the right quantity" |
| `angle setpoint − θ` (**electronic spring**) | stiffness `K_e` | **shrinks it to `2F/(k + K_e)`** and speeds the spring pole | still **command → angle**, exactly the plant the fork's spring feedforward (`get_honda_accord_rate_plant_ff`) models — V293 made stiffer. The right quantity |
| `T += F̂·sign ω` (**friction cancellation**) | nothing (a sign-following bias) | removes it directly if `F̂ ≈ F` | unchanged torque map. The most surgical and the riskiest: anti-damping if `F̂ > F`, chatter on a noisy 1 kHz sign |
| a **small fb clamp** ("half-open" V282) | V282's servo near centre, the torque map away from it | linearised only inside the clamp | a **hybrid** neither controller can model — do not |

## Order of rungs (the cheap ones first, each with its own instrument)

1. **Fork, toggles (this session):** `SteerFriction` at the measured `F` (the only term opposing Coulomb
   friction), the plant feedforward back on with the spring corrected (`AccordEpsSpringScale`) and its
   rate term restored (`AccordFFRateGain`, which also restores the command dither). Instrument: the
   rate-magnitude concentration and dwell-and-jump statistics (`v293_ident_h.py`) against the V282
   references — a pre-registered fall from 0.47 toward 0.33–0.35 at q75–90.
2. **Fork, code:** a 100 Hz rate-feedback term (`torque += K_v·(ω_des − ω)` from `carState.steeringRateDeg`),
   crossover a few Hz — no firmware. Only if rung 1 leaves the snap statistic where it is.
   **Sample-rate check (operator's question, 2026-09-13 night — measured on route 70's own CAN timestamps):** the steering feedback is **100 Hz**, not 50 — `0x14A` STEERING_SENSORS (angle) and `0x18F` STEER_STATUS (rate, 0.125 deg/s LSB) both arrive at 100.9 Hz median (p5–p95 9.1–11.3 ms), `0xE4` goes out at 100 Hz, and the samples are FRESH each frame (identical consecutive values only 5 % on the rate and 10 % on the angle while moving, equal on both frame parities — a 50 Hz-held value re-sent at 100 Hz would read ~100 % on one parity). Only the **427 torque tap (`0x1AB`) is 50 Hz** (49.7 Hz), and a fork rate loop would not use it. So a 100 Hz rate-feedback term in the fork has a 100 Hz measurement to close on; its delay budget is the openpilot round trip (~20–40 ms) plus the EPS torque-map response, not a sample-rate floor. [EVIDENCE — `r70_v293.npz` timestamps]
3. **Firmware:** an angle loop (electronic spring). A **cave** — the kit's only bricking class — with the
   two GATES of `BUILD-LINEAGE.md` Part 2. After rung 2, never before.
4. **Never:** an angular-acceleration loop; a half-open fb clamp.

Related: `docs/research/FORK-LATERAL-PATH-V293-2026-09-13.md` (what the fork computes today),
`rlog-tools/studies/grind/V293-PLANT-IDENT-2026-09-13.md` (the plant), `docs/STATE.md` (the decision).
