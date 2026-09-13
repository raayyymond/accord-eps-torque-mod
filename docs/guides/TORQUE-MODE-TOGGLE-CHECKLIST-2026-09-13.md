# EPS torque mode — the toggle checklist for a V293 drive, and for reverting

**2026-09-13.** The fork switch is `AccordEpsTorqueMode` (Galaxy → *Custom Patches* → **"Accord: EPS
Torque Mode (V293+ firmware only)"**). It ships **OFF**. Fork: `raayyymond-StarPilot/StarPilot`,
branch `Dom`, **uncommitted**.

This card exists because the firmware and the fork have to agree, and until now that agreement was
four separate toggles the operator had to flip consistently. It is now one.

---

## 🛑 THE ONE RULE

> **`AccordEpsTorqueMode` may be ON only while a TORQUE-MAP EPS image (V293 or later) is in the ECU.**
> Every step order below is just that rule applied to the two directions.

The two mismatches are **not symmetric**, which is why the order matters:

| state | what the fork does | consequence |
|---|---|---|
| mode **ON** + **rate-servo** image (V282/V292, stock) | the plain lateral-accel feedforward, sized for a torque actuator, fed to a rate servo | 🛑 **OVER-DELIVERY.** Feedforward **×2.55** at 15 m/s / 0.9 m/s² — measured from the built fork code, inside the record's 2.4–4.3× band. Nothing downstream catches it: `opendbc/safety/modes/honda.h` applies **no** magnitude, rate, driver-torque or RT-window limit to `0xE4`. |
| mode **OFF** + **torque-map** image (V293) | the rate-plant feedforward, i.e. the inverse of a servo that is no longer there | 🛑 **FEEDFORWARD STARVATION, not simple sluggishness.** The feedforward is far too small and the integrator carries the shortfall — a high-gain integrator doing a feedforward's job. Worst at low speed. |

⇒ **Never create the first row, not even for the drive to the flashing spot.** The second row is the
*less bad* of the two, not a safe state — prefer it in every transition window, and do not linger in it.

**🛑 Correction, 2026-09-13, from adversary B's sub-check B6 — "OFF-on-V293" is worse than this card
first said.** It was written as "under-delivery, the car wanders and the driver takes over,
recoverable". That understates it. The rate-plant feedforward inverts a plant that is no longer
there, so the shortfall is not a uniform softening — it is **strongly speed-dependent and largest
exactly where the low-speed gains are biggest**, and whatever the feedforward fails to supply, the
integrator winds up to supply instead.

| quantity | 5 m/s | 12.5 m/s | 28.5 m/s | whose measurement |
|---|---|---|---|---|
| steering rate for the same `0xE4` command, rate-plant FF ON | **×3.17** | ×1.46 | ×0.95 | **B6.** Quoted as B6 stated it; I did **not** re-derive it and I have not reconciled its sign convention with the row below. [REPORTED, not verified by me] |
| feedforward magnitude, generic ÷ rate-plant, at 15 m/s and 0.9 m/s² | — | — | — | ×2.55 — **my own measurement from the built fork code.** Same direction (the rate-plant FF is the smaller one), different quantity; the two are **not** comparable term for term. [EVIDENCE] |

Both rows agree on the operational point, which is the part you need: **with the mode OFF on a
torque-map image the feedforward is much too small, most so at low speed, and the integrator
compensates.** [EVIDENCE for the direction; the per-speed factors are B6's.]

### ✅ The two rows RECONCILED — they are not in conflict, they describe different regimes

The apparent contradiction (*"too little torque"* vs *"×3.17 the steering rate"*) dissolves once you ask
**what the wheel is doing**, because that is exactly what V293 stops responding to:

| regime | what happens with the mode **OFF** on V293 | which row it is |
|---|---|---|
| **Steady curve — the wheel is loaded and barely moving (a "stalled" wheel)** | V293 delivers **×0.5 of V282 per unit command** below idx 116, so a feedforward sized for V282 **under-commands**. The shortfall does not vanish: **the integrator winds up and carries it.** | the ×2.55 / starvation row |
| **Turn-in — the wheel is moving** | V282's rate servo would **back off** as the wheel speeds up; **V293 never backs off.** The same command therefore produces **×3.17 the steering rate at 5 m/s** (×1.46 at 12.5 m/s, ×0.95 at 28.5 m/s). | the B6 row |

**Neither is a safe state, and they fail in opposite directions** — starved and integrator-driven when
held in a curve, over-rated on turn-in, at the same speed, minutes apart. That is worse than a single
consistent error, because the driver cannot form one expectation. **The invariant stands unchanged:
never run the mode OFF on a torque-map image for longer than a transition window, and never run it ON
on a rate-servo image at all.** [The ×0.5 slope is adversary A's, from the built image; the per-speed
rate factors are B6's back-solve and are REPORTED, not re-derived here.]

---

## A. Going TO V293 (torque map)

**Order: FLASH FIRST, TOGGLE SECOND.** If you toggle first you then have to drive somewhere with an
over-driven EPS.

1. **Kill openpilot** (`tmux kill-server` on the comma device) — mandatory before any flash.
2. **Flash V293** and verify the part number and the image hash. Name the `.rwd` file and the bus out
   loud before starting; do not flash from this card.
3. **Confirm the flash took** before the car moves again.
4. **Only now**, in Galaxy → *Custom Patches*:

   | toggle | set to | why |
   |---|---|---|
   | **`AccordEpsTorqueMode`** | **ON** | the whole switch. Bypasses the rate-plant feedforward and swaps in the torque-mode tune. |
   | `AccordCurvatureLead` | **OFF** | it is already inert in torque mode and OFF by default; set it explicitly so the rlog reads unambiguously. |
   | `ForceAutoTuneOff` | **1** (already) | keeps the custom lateral-accel and friction in the loop and stops `paramsd` learning over the vehicle model. |
   | `SteerRatio` | **16.88, unchanged** | the map level. 16.88 is `HONDA_ACCORD_STEER_RATIO_NOMINAL`, i.e. scale exactly 1.0000, which serves the 83-route measured curve unaltered. **Do not re-tune it on the first drive** — see §D. |

5. **Leave everything else exactly as it is.** In particular:
   - 🛑 **Do NOT set `AccordRatePlantFF` to False by hand.** That single flip on a rate-servo image is
     the over-delivery hazard above, and the new switch exists so you never have to touch it. Torque
     mode overrides it whatever it says.
   - `AccordTurnFFTaper`, `AccordEpsGainScale`, `AccordEpsSpringScale`, `AccordFFRateGain` are all
     held inert in torque mode. Leave them.
6. **Reboot / restart openpilot** so `controlsd` picks the params up, then verify §C before driving.

---

## B. Reverting to V282/V292 (rate servo)

**Order: TOGGLE FIRST, FLASH SECOND.** The mirror image, for the same reason: the window between the
two steps must never be "mode ON + rate servo".

1. **`AccordEpsTorqueMode` → OFF** in Galaxy. Nothing else needs changing; the rate-servo tune
   (`SteerLatAccel`, `SteerFriction`, `SteerKP`, `AccordTorqueKi`) is untouched by torque mode and
   comes straight back.
2. Restart openpilot and confirm §C reads **OFF**.
3. **Kill openpilot**, flash V282 (or V292), verify.
4. Nothing else to restore. Torque mode writes to no persistent state of its own.

**If you are ever unsure which way round you are:** turn the mode **OFF**. OFF is safe on both
firmwares — correct on the rate servo, under-driven on the torque map.

---

## C. Verifying the state, before you drive

| check | where | reads |
|---|---|---|
| the mode itself | `starpilotLateralState.epsTorqueMode` | `True` at 100 Hz, **engaged or not**. This is the primary check. |
| the mode, second source | `initData.params["AccordEpsTorqueMode"]` | `"1"`. Present only because ON is non-default — an Accord param at its default is **absent** from `initData.params`, which is why the cereal field above exists. |
| the branch actually taken | `torqueState.f` | under torque mode `f` = desired lateral accel + friction, and friction ships at 0, so at ~0.9 m/s² it reads **~0.90**. Under the rate-plant branch the same point reads **~0.38**. |

🛑 **If the toggle appears to do nothing, check that `params_pyx.so` was rebuilt.** The five new keys
live in `common/params_keys.h`, which is compiled. On an older `.so` `StarPilotVariables` silently
falls through to the key's default — which is **OFF**, so the failure is in the safe direction, but it
is silent. The same trap already applies to every other `Accord*` toggle.

**Safe Mode forces the torque mode OFF.** If Safe Mode trips with V293 in the ECU you land in the
feedforward-starved state, not the over-driven one. That is deliberate — but it is not a *safe*
state, only the less bad one, so treat a Safe Mode trip on V293 as a reason to stop, not to continue.

---

## D. The first-drive tune — all four numbers are PROVISIONAL

They live in **one place**, `selfdrive/controls/lib/latcontrol_vehicle_tunes.py`, in the
`HONDA_ACCORD_TORQUE_MODE_*` block, and are exposed as sliders under the mode switch.

| toggle | ships at | replaces | note |
|---|---|---|---|
| `AccordTorqueModeLatAccel` | **6.0** | `SteerLatAccel` | 🛑 **NOT an identification.** 6.0 is today's rate-servo value, carried over so the first flight is not also a gain change. On a rate servo a constant command gives a constant wheel *rate*, so lat-accel-per-command rises without bound as frequency falls; on a torque actuator the DC gain is finite and should come out **lower**. |
| `AccordTorqueModeFriction` | **0.00** | `SteerFriction` | 🛑 **ZERO, and that is a STABILITY choice, not a feel choice.** This fork feeds the friction compensator the **LSF-inflated** error (§F), so its gain is multiplied by `1 + lsf/Kp` — ×17.9 at 5 m/s with Kp 0.3. At friction 0.01 the outer loop's worst phase margin is **22.8°** (Ms 4.32, crossover 0.82 Hz); at 0.00 it is **42.2°** (Ms 2.06), with gain margin to 30° at ×1.40. Nineteen degrees of phase for a term that cannot be sized until the LAF is. |
| `AccordTorqueModeKp` | **0.3** | `SteerKP` | a third of today's 0.9. 🛑 **Its safety depends on the row above being 0.00, and the two clauses cannot be separated.** With **friction 0** the low-speed loop gain is **monotone in Kp**, so 0.3 is plainly the safe side. With **any friction > 0** the gain has an **interior minimum near Kp ≈ 1.0**, and **a LOWER Kp is WORSE** — 0.3 would then be the *dangerous* side, which is the opposite of the usual reflex. ⇒ **friction 0 AND Kp ≤ 1.0, both, never one without the other.** The *proportional* part alone is `(Kp + low-speed factor) / LAF`, whose margin scales as `1/LAF`, and LAF is expected to fall. See the rule below. |
| `AccordTorqueModeKi` | **0.15** | `AccordTorqueKi` | half the rate-servo value. A mis-sized LAF with a live integrator is the configuration that hides the error until it is a wallow. |

### 🛑 The slider rule

> **The outer loop's gain is minimised near `Kp ≈ 1.0` at low speed, because the fork's friction
> compensator sees the LSF-inflated error. Never raise friction above 0 before the LAF is fitted.
> Never take Kp above 1.0. And the modelled margins assume `τ = 0.20 s` — which is the operator's
> `SteerDelay` toggle echoed back, NOT an identification; the Honda port's own prior is 0.10 s. A `τ`
> measurement from an rlog is being run.**

Why it is counter-intuitive, in one line each:

- the proportional contribution is `Kp + lsf`, which **rises** with Kp;
- the friction contribution is `(friction / 0.30) · (1 + lsf/Kp)`, which **falls** with Kp;
- with friction live their sum has an interior minimum, at 5 m/s near **Kp 1.0** — so cutting Kp to
  0.3 *raises* the low-speed loop gain, which is the opposite of the usual reflex;
- at the shipped friction of **0.00** the second term is gone and the gain is monotone in Kp again,
  so a lower Kp is then plainly safer. **That is why the rule is "friction 0 **and** Kp ≤ 1.0", not
  one or the other.**

[EVIDENCE: the `1 + lsf/Kp` inflation, `lsf(5 m/s) = 5.0625`, the ×17.9 / ×6.6 factors and the
Kp ≈ 1.0 minimum are re-derived from the fork's own tables and asserted in
`selfdrive/controls/tests/test_accord_eps_torque_mode.py`. The phase margins and Ms figures are
adversary B's sub-check B6 and were **not** re-derived here.]

**Also still live, from the design grid** (`DESIGN-V293-TORQUE-MODE-2026-09-13.md` §5): LAF ≤ 2.0
together with Kp ≥ 0.6 at motorway speed is the one RISK region, the V276-shaped outer-loop signature.
No runtime guard exists — the sliders reach it. If the identification returns a LAF near 2, lower Kp
first, then LAF.

**Identify LAF from the first drive's rlog, not from `torqued`.** Its buckets do not fill on this car
and its estimate is a long-filter TLS through central buckets on a plant whose gain has just changed
discontinuously. The recipe — instrumental-variables fit against `modelV2.action.desiredCurvature·v²`,
≥400 hands-off laterally-engaged pairs per `|τ|` bucket in ≥4 buckets spanning 0.05→0.50 with ≥2 above
0.25 — is §3.5 of
`docs/research/FORK-LATERAL-DESIGN-FOR-TORQUE-MODE-AND-RATE-TARGET-2026-09-13.md`.

**One consequence worth knowing before the drive.** With the shipped defaults the *net* command at
15 m/s / 0.9 m/s² comes out **0.929×** today's, not larger: the bigger feedforward (×2.55 with the
tune held equal) is more than paid for by Kp 0.9→0.3, Ki 0.30→0.15 and friction 0.01→0.00. The
feedforward rise is still real, and the terms move differently with speed, error and curvature — so
**this near-cancellation is a coincidence at one operating point, not a safety margin.** Measured
from the built fork code:

| configuration | p | i | f | torque |
|---|---|---|---|---|
| mode OFF (today, rate-plant FF) | 1.1523 | 0.7287 | 0.3772 | −0.3763 |
| mode ON, tune held at today's | 1.1523 | 0.7340 | 0.9600 | −0.4744 |
| mode ON, shipped defaults | 0.6123 | 0.5850 | 0.9000 | −0.3495 |

**And the steer-ratio level changes meaning.** Today `SteerRatio` pushes twice in the same direction
(the map feeds both the measurement and the rate-plant feedforward). In torque mode the second
consumer is gone, so the level's sensitivity roughly **halves**. A level that felt right before will
feel different. Leave it at 16.88 through identification. [BELIEF, from the structure.]

---

## F. Standing fork fact — the friction compensator is fed the LSF-inflated error

**This is a property of the fork, not of torque mode, and it is live on V282 today.** Recording it
here because it inverts the usual intuition about Kp and because nothing else in the kit writes it
down.

`latcontrol_torque.py` calls

```python
ff += friction_scale * get_friction(error_with_lsf + JERK_GAIN * friction_jerk, ...)
#                                   ^^^^^^^^^^^^^^
```

where **upstream openpilot passes the raw `error`**. And

```python
error_with_lsf = error * (1 + low_speed_factor / max(current_kp, 1e-3))
```

so the friction compensator's small-signal slope, in torque units, is

```
(friction / friction_threshold) · (1 + lsf / Kp)          instead of   friction / friction_threshold
```

At 5 m/s the low-speed factor is **5.0625**, so the multiplier is:

| Kp | `1 + lsf/Kp` | slope at friction 0.01 |
|---|---|---|
| 0.3 | ×17.9 | 0.596 |
| 0.9 | ×6.6 | 0.221 |
| 1.0 | ×6.1 | 0.202 |

**Consequences, both of which matter:**

1. **A lower Kp makes the friction term worse.** This is why the torque-mode friction ships at 0.
2. **It is already acting on the car.** On V282 today, at `SteerKP` 0.9 and `SteerFriction` 0.01,
   the compensator's gain is **×6.6** what the raw error would give at 5 m/s. Nothing here changes
   that; torque mode simply does not add to it.

[EVIDENCE: the two source lines are quoted verbatim from the fork, and every factor above is
re-derived from `LOW_SPEED_X` / `LOW_SPEED_Y` / `MIN_SPEED` in `latcontrol_torque.py` and asserted
in `test_accord_eps_torque_mode.py`. Whether upstream openpilot's behaviour is the *correct* one is
not settled here — only that the two differ.]

---

## E. What this does *not* do

- **It is not a grinding fix.** V288 rev 2 flew a reference-side setpoint pre-filter, the cave was
  live, the D-clamp bind duty fell ×0.03 as designed, and the grinding was **unchanged** (19.99 vs
  19.93 Hz, KS p 0.18; 258 vs 239 episodes/h). Nothing on the fork's reference side reaches the 20 Hz
  ring. What may remove it is the *firmware* side — a torque-map image opens the rate loop by
  construction, and with the loop open there is no 18–22 Hz object at all (35 routes). That claim is
  about V293, not about this toggle. [EVIDENCE on V288's null and the 35-route measurement; BELIEF
  that V293 therefore removes the symptom — it has never been driven.]
- 🛑 **It DOES change authority below full demand — the old wording here was wrong and is retracted.**
  (It read *"it does not change authority; the EPS peak stays 2505 torque counts."* Both halves were
  wrong: 2505 is the **structural ceiling**, which neither build reaches, and the peak is not the whole
  story.) From adversary A, re-derived from the built image:

  | | V282 | **V293** |
  |---|---|---|
  | delivered peak, at rest | 2461 | **2461 — identical** |
  | demand needed to reach it | idx ~116 | **idx 239–240** |
  | torque per demand index below the rail, wheel **still** | 21.35 counts/idx | **10.34 counts/idx** |
  | delivered at idx 58, wheel **still** | 1236 | **598 (×0.48)** |

  **In one sentence: the peak is identical and now needs twice the demand to reach.** Below idx 116 the
  lane delivers **0.47–0.49 of V282's stalled-wheel torque**. ⚠ **That comparison is against a wheel
  that is NOT moving.** Against a *moving* wheel V282's servo backs off — it delivers less, and can go
  negative — while **V293 delivers the same torque whatever the wheel is doing.** So "less authority" is
  true only in the stalled regime, and the two builds meet or cross once the wheel moves.
  ⭐ **openpilot's LAF identification absorbs the slope change** — the actuator fraction goes from ~12 %
  to ~24 % — which is precisely why **the first drive is an identification drive and the tune comes
  after it**, not before. `STEER_MAX` stays 4096 and the ±3/frame rate limit is untouched.
- **It writes nothing persistent.** Turning it off restores the previous behaviour exactly.
