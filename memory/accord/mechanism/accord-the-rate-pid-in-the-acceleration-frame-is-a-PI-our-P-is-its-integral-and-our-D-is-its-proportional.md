---
name: accord-the-rate-pid-in-the-acceleration-frame-is-a-PI-our-P-is-its-integral-and-our-D-is-its-proportional
description: 2026-09-04 (docs/research/PID-FRAME-SIZING-KP-KD-2026-09-04.md, analysis-2020accord/studies/pidframe/pid_frame_sizing.py). openpilot models its output as a TORQUE, i.e. an angular ACCELERATION. Re-expressed in that frame the EPS LKAS rate PID (FUN_00028ea6) is a PI with NO derivative term - our D term is its PROPORTIONAL gain (0.016 s) and our P term is its INTEGRAL gain (0.969), corner 9.64 Hz, |D|/|P| = 33.03*sin(pi*f*T). Relative to ANGLE: our I -> proportional, our P -> derivative, our D -> 2nd derivative. Kd=128 is therefore a LEAD COMPENSATOR whose zero (9.64 Hz) cancels the 5.05 Hz output-lag pole, holding the forward path flat 5-40 Hz; the phase margin is spent by the FEEDBACK EMA (0xC63E8/EA = 923/1560, exact pole 16.527 Hz, -50.5 deg at 20 Hz), and NO derivative filter exists anywhere in the loop. Consequence: the 7.3 Hz ring is integral-dominated and the 20 Hz grind proportional-dominated, which is why no single gain has ever moved both. Kp -> 0 costs ~90 % of loop gain at 1 Hz but only ~10 % at 20 Hz.
metadata:
  type: reference
---

# The rate PID, re-expressed in the ANGULAR-ACCELERATION frame, is a PI — our P is its INTEGRAL and our D is its PROPORTIONAL — 2026-09-04

Study: `docs/research/PID-FRAME-SIZING-KP-KD-2026-09-04.md` · code: `analysis-2020accord/studies/pidframe/pid_frame_sizing.py`

## The loop as written in the firmware

`FUN_00028ea6`, 1 kHz tick, sole caller `jarl 0x00028ea6,lp @0x22522` inside `FUN_0002214a`:

```
E = 32*sp - fb                        # sp = LKAS rate setpoint; fb = measured rate (TWO-SAMPLE SUM, DC gain 30.89)
P = clamp(E*Kp >> 8,   +/-15360)      # Kp from the LERP record, live slot 7 @ 0xE5378
D = clamp(dE*128 >> 3, +/-10240)      # Kd = 128, record 0xE511C
I = accumulator, gain cell 0xC63E6    # 0 on every build except V283 (=50)
S = clamp(254*(P+D+I) >> 8, +/-15360)
    output lag 992/507 -> *5346>>15 -> clamp +/-3072
```

## The frame change — why it matters

The operator's framing (2026-09-04): *"Kp is effectively Kd for our torque. An integrator on steering
angle rate is just steering angle, which would NOT be used in a PID loop on angular acceleration
(proportional to torque)."* He is right, and the arithmetic agrees.

The firmware's error `E` is a **RATE** error. openpilot's output is modelled as a **TORQUE**, which is
proportional to angular **ACCELERATION**. Each differentiation shifts every term up one order:

| firmware term | acts on | relative to ANGLE | relative to ACCELERATION |
|---|---|---|---|
| `I` (0xC63E6) | ∫E | proportional | double integral |
| `P` (Kp) | E | **derivative** | **INTEGRAL** |
| `D` (Kd) | dE | 2nd derivative | **PROPORTIONAL** |

⇒ **In the frame openpilot actually commands, this loop is a PI controller with no derivative term at
all.** Accel-frame proportional = our D, time constant 0.016 s. Accel-frame integral = our P, 0.969.
Corner where they cross: **9.64 Hz**, from `|D|/|P| = 33.03·sin(πfT)` at Kp = 248, Kd = 128, T = 1 ms.

## Two structural consequences

**1. Kd = 128 is a lead compensator, not a damper.** Its zero at 9.64 Hz cancels the output-lag pole at
5.05 Hz, holding the forward path flat from ~5 to ~40 Hz. What actually spends the phase margin is the
**feedback EMA** — `0xC63E8`/`0xC63EA` = 923/1560, exact pole **16.527 Hz**, contributing **−50.5° at
20 Hz**. **There is no derivative filter anywhere in this loop.** See
[[accord-the-creep-grind-is-the-lkas-rate-loop-crossover-resonance-d-dominated]].

**2. The two symptoms live on opposite sides of the 9.64 Hz corner.** The 7.3 Hz strong-turn ring is
**integral-dominated** (P term); the 20.3 Hz grind is **proportional-dominated** (D term). That is the
structural reason no single gain has ever moved both, across the whole post-V38 arc —
[[accord-r24-pumps-at-7hz-and-damps-at-20hz-the-same-cell-pulls-the-two-symptoms-opposite-ways]] is the
same shape of fact one lane further out.

## What Kp → 0 costs (EVIDENCE for the ratio, BELIEF for the closed-loop consequence)

Treating P and D as 90° apart, removing P scales the forward path by `|D| / |P+D|`:

| f | `|D|/|P|` | loop gain lost by Kp → 0 |
|---|---|---|
| 1 Hz | 0.104 | **−89.7 %** |
| 9.64 Hz | 1.000 | −29.3 % |
| 20 Hz | 2.074 | **−9.9 %** |

⇒ **Kp = 0 is very nearly a pure authority cut at lane-keeping frequencies and barely touches the
grind.** It is the correct Ziegler–Nichols P-only condition in the acceleration frame, but a quiet
20 Hz line on such a build is **not** a grind result — the loop simply got weak.

## The ZN programme this licenses 🛑 RESOLVED 2026-09-04 — READ THIS, NOT THE PARAGRAPH BELOW

**`Ku ≈ 227` [217–270], `Tu ≈ 36 ms`**, and the binding instability is **NOT** either symptom band — it is a Nyquist **−180° crossing at 27–32 Hz**. Anchored on a **MEASURED gain margin**: `CREEP-20HZ-LOOP-ID-2026-09-03.md`'s estimator table, **bar-IV** rows, `1.75× @ 23.4 Hz` (Kp 295) and `1.32× @ 22.4 Hz` (Kp 470); `Ku = Kd × GM`. ⚠ Only the bar-IV family finds a crossing at all — every other estimator row reads “none”.

⭐⭐ **Kd IS BRACKETED FROM BOTH SIDES: `Kd ∈ [118, 227]` at Kp 248.** The 7.3 Hz ring gets BETTER with more Kd (lower root **118** — a cut re-arms the cycle); the 27–32 Hz Nyquist gets WORSE (Ku **227**). **Today's Kd 128 sits near the FLOOR**, 1.08× above the root and 1.77× below Ku.

⭐ **Two independent methods converge on Kd ≈ 160**: ZN-PID of this frame gives **Kd 162 / Kp 329**; the loop-shape study's candidate **F** gives **Kd 160**. Within 1 %. F is the best-centred point (1.36× / 1.42×) and spends **16 %** of the blind-band margin (GM 1.77× → 1.48×).

🛑 **Td has no realisable home** — the firmware has exactly **three addends and ONE difference operator** (`0x29EE2 sub r27,r8`, single history cell `gp-0x6cf8`). The reachable form is ZN-**PI**.

🛑 **Kp = 0 delivers ZERO steady-state authority.** The plant is **type 0 in rate**, so with Kp = 0 AND Ki = 0, `L(0) = 0` exactly (steady state ⇒ `dE = 0` ⇒ `D = 0` ⇒ `S = 0`). Every stability metric improves; the car cannot hold a lane.

🛑 **Biggest open hole:** the answer bifurcates on plant phase above 25 Hz — delay model → Ku 227, frozen phase → Ku 865, a **3.8× spread** — and 27–32 Hz is **above the 427 tap's 25 Hz Nyquist**. A one-drive Ku estimate on the flying channels is INFEASIBLE for the binding mode.

### Superseded first-pass reasoning, kept for the record


Kp = 0 removes accel-frame integral action; raising Kd then finds **Ku**. Because D is already 2.07× P
at 20 Hz, the marginal mode is already Kd-dominated, so Ku is close: extrapolating the measured ring
loop gain of 0.976 ([[accord-the-ring-loop-gain-is-0976-gain-is-spent-as-a-lever]]) gives **Ku ≈ 143–151,
Tu ≈ 49 ms** — BELIEF, because removing P also removes ~90° of lag and moves the −180° crossover up in
frequency. That correction was still open when this note was written. It also **disputes the loop-shape
study's candidate F (Kd → 160)**, which would then sit above Ku.

🛑 `0xE511C` (the Kd record) is **not virgin** — V279/V279 rev 1 set it to 0, confounded and unflown.
**Kd has been 128 on every FLOWN build in the arc.**
