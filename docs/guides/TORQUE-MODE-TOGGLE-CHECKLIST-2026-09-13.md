# EPS torque mode — the checklist for a V293 drive, and for reverting

**2026-09-13, third and final form.** The fork side is a **Galaxy toggle config**, nothing more:

| file (`analysis-2020accord/reference/`) | what it does |
|---|---|
| **`toggle-config_V293_torque_mode.json`** | the torque-mode tune: `AccordRatePlantFF` **0**, `SteerKP` **0.3**, `AccordTorqueKi` **0.15**, `SteerFriction` **0.00**, `SteerLatAccel` 6.0, plus five pins that are already your values (`ForceAutoTuneOff` 1, `ForceAutoTune` 0, `AdvancedLateralTune` 1, `KeepLearnedLatAccelOffset` 1, `AccordTurnFFTaper` 0) |
| **`toggle-config_V282_rate_servo_REVERT.json`** | the installed rate-servo tune, exactly as your 2026-09-10 backup and route 6f's `initData` carry it (`AccordRatePlantFF` 1, `SteerKP` 0.9, `AccordTorqueKi` 0.30, `SteerFriction` 0.01, `SteerLatAccel` 6.0) |
| `*.decoded.json` beside each | the same ten keys, readable |
| `tools/make_galaxy_toggle_config.py` | regenerates both; the codec is checked against your own 2026-09-10 backup before anything is written |

Both files are **deltas** on purpose: Galaxy's restore applies exactly the keys in the file and leaves every
other setting alone. Restoring your full 2026-09-10 backup instead would drag `SteerRatio` back to 16.33
and `LaneChangeSmoothing` to 6 (route 6f shows you have since moved them to 16.88 and 4).

**There is no fork code for this.** The preset param (`AccordEpsTorqueMode`) and the Testing Ground 9 slot
that each shipped earlier on 2026-09-13 were both rejected and the fork commit was force-removed; Dom
`4247cb09e` carries nothing torque-mode-specific, and `starpilotLateralState.epsTorqueMode` never
shipped. If a device still shows an "Accord: EPS Torque Mode" toggle or a Testing Ground slot 9, it is
running a stale fork build.

---

## 🛑 THE ONE RULE

> **The torque config may be live only while a TORQUE-MAP EPS image (V293 or later) is in the ECU.**
> Every step order below is just that rule applied to the two directions.

The two mismatches are **not symmetric**:

| state | what the fork does | consequence |
|---|---|---|
| torque config + **rate-servo** image (V282/V292, stock) | the plain lateral-accel feedforward, sized for a torque actuator, fed to a rate servo | 🛑 **OVER-DELIVERY.** Feedforward **×2.55** at 15 m/s / 0.9 m/s² — measured from the fork code, inside the record's 2.4–4.3× band. Nothing downstream catches it: `opendbc/safety/modes/honda.h` applies **no** magnitude, rate, driver-torque or RT-window limit to `0xE4`. |
| installed tune + **torque-map** image (V293) | the rate-plant feedforward, i.e. the inverse of a servo that is no longer there | 🛑 **Not simple sluggishness.** On a held curve V293 delivers ~½ the torque per command below demand index 116, so the feedforward starves and the integrator carries the shortfall; on turn-in V293 never backs off and the rate runs **×3.17** what the geometry asks at 5 m/s (×1.46 at 12.5, ×0.95 at 28.5 — B6's back-solve). Opposite-direction errors minutes apart. Recoverable, not safe. |

⇒ **Never create the first row, not even for the drive to the flashing spot.** The second row is the
*less bad* of the two — prefer it in every transition window, and do not linger in it.

---

## A. Going TO V293 (torque map)

**Order: FLASH FIRST, RESTORE THE CONFIG SECOND.**

1. **Kill openpilot** (`tmux kill-server` on the comma device) — mandatory before any flash.
2. **Flash V293** and verify the part number and the image hash. Name the `.rwd` file and the bus out loud
   before starting; do not flash from this card.
3. **Confirm the flash took** before the car moves again.
4. **Only now**, Galaxy → toggle backup → **Restore** → upload `toggle-config_V293_torque_mode.json`. Galaxy
   answers *"Restored 10 toggle settings."* — if it says any were skipped as incompatible, stop and read
   which.
5. **Restart openpilot** (reboot the device). `controlsd` reads the tune at start.
6. **Leave everything else exactly as it is.** `SteerRatio` stays 16.88 (the map's nominal, scale 1.0000);
   `AccordEpsGainScale`, `AccordEpsSpringScale` and `AccordFFRateGain` are inert with the rate-plant branch
   off; `AccordTurnFFTaper` is pinned off by the config.
7. Verify §C before driving.

## B. Reverting to V282/V292 (rate servo)

**Order: RESTORE THE REVERT CONFIG FIRST, FLASH SECOND.** The mirror image, for the same reason: the window
between the two steps must never be "torque config + rate servo".

1. Galaxy → toggle backup → **Restore** → `toggle-config_V282_rate_servo_REVERT.json`. Restart openpilot.
2. Confirm §C reads the installed tune (Kp 0.9, rate-plant FF on).
3. **Kill openpilot**, flash V282 (or V292), verify.

**If you are ever unsure which way round you are:** restore the REVERT config. The installed tune is safe
on a rate servo and merely under-driven on the torque map.

---

## C. Verifying the state — from the wire, no code flag

`python rlog-tools/studies/grind/v293_flight_read.py <route id>` prints all of these in its section 0.
Negative-controlled on the V292 route r6f, which reads the installed tune exactly.

| check | where | torque config reads | installed tune reads |
|---|---|---|---|
| the keys | `initData.params` (logged once, at process start) | `AccordRatePlantFF` `0`, `SteerKP` `0.3`, `AccordTorqueKi` `0.15`, `SteerFriction` `0.0` | `SteerKP` `0.9`, `SteerFriction` `0.01`, and the two `Accord*` keys **absent** — an `Accord*` key at its `params_keys.h` default is absent, so absence means the default (rate-plant FF **on**, Ki 0.30) |
| **Kp at 100 Hz** | `controlsState…torqueState`: median `p / error` over active frames | **0.300** | **0.9000** (r6f: 42 905 frames, IQR [0.9000, 0.9000], 100 % within 5 %) — the fork logs `pid_log.error = error_with_lsf` and calls `pid.update(pid_log.error, …)`, whose `p = k_p·error`, so the ratio IS the toggle. This one survives a mid-route toggle change; `initData` does not. |
| the branch | median `f / desiredLateralAccel` | **1.00** (friction 0 ⇒ f = D) | **~0.3** (r6c 0.32, r6d 0.24, r6e 0.40, r6f 0.29) |

🛑 **Safe Mode RESETS this config.** All ten of its keys are in `SAFE_MODE_MANAGED_KEYS`
(`starpilot/common/safe_mode.py`), so a Safe Mode trip puts `AccordRatePlantFF` back to 1 and the tune back
to its defaults — the installed-tune-on-V293 row above while V293 is in the ECU. It is a route **out** of
the torque config, never into it. After any trip, restore the config again before the next drive on V293.
[EVIDENCE: the key list, read 2026-09-13.]

---

## D. The first-drive tune — all four numbers are PROVISIONAL, and they are sliders

The config sets the four Galaxy sliders; after restoring it you can re-tune between drives from Galaxy
without touching the fork.

| slider | config value | note |
|---|---|---|
| `SteerLatAccel` | **6.0** | 🛑 **NOT an identification.** Today's rate-servo value, carried over so the first flight is not also a gain change. On a rate servo a constant command gives a constant wheel *rate*, so lat-accel-per-command rises without bound as frequency falls; on a torque actuator the DC gain is finite and should come out **lower**. Identify it from the first drive's rlog (§3.5 of `docs/research/FORK-LATERAL-DESIGN-FOR-TORQUE-MODE-AND-RATE-TARGET-2026-09-13.md`: instrumental variables against `modelV2.action.desiredCurvature·v²`, ≥400 hands-off laterally-engaged pairs per bucket in ≥4 buckets to 0.5, both signs — **not from `torqued`**, whose buckets do not fill on this car). |
| `SteerFriction` | **0.00** | 🛑 **ZERO, and that is a STABILITY choice, not a feel choice.** This fork feeds the friction compensator the **LSF-inflated** error (§F), so its gain is multiplied by `1 + lsf/Kp` — ×17.9 at 5 m/s with Kp 0.3. At friction 0.01 the outer loop's worst phase margin is **22.8°** (Ms 4.32); at 0.00 it is **42.2°** (Ms 2.06), gain margin to 30° at ×1.40. |
| `SteerKP` | **0.3** | a third of today's 0.9. 🛑 **Its safety depends on friction being 0.00, and the two cannot be separated.** With friction 0 the low-speed loop gain is monotone in Kp, so 0.3 is the safe side; with **any** friction > 0 the gain has an interior minimum near Kp ≈ 1.0 and **a LOWER Kp is WORSE**. ⇒ **friction 0 AND Kp ≤ 1.0, both, never one without the other.** |
| `AccordTorqueKi` | **0.15** | half the rate-servo value. A mis-sized LAF with a live integrator is the configuration that hides the error until it is a wallow. |

### 🛑 The tune rule

> **Never raise friction above 0 before the LAF is fitted. Never take Kp above 1.0. And the modelled margins
> assume the measured, speed-dependent lag (0.15 s at motorway, ~0.25 s at 3–8 m/s — see
> `rlog-tools/studies/grind/TAU-ACTUATOR-DELAY-2026-09-13.md`), not the `SteerDelay` toggle echoed back.**

- the proportional contribution is `Kp + lsf`, which **rises** with Kp;
- the friction contribution is `(friction / 0.30) · (1 + lsf/Kp)`, which **falls** with Kp;
- with friction live their sum has an interior minimum near **Kp 1.0** at 5 m/s, so cutting Kp to 0.3
  *raises* the low-speed loop gain — the opposite of the usual reflex;
- at friction **0.00** the second term is gone and a lower Kp is plainly safer again.

[EVIDENCE: the `1 + lsf/Kp` inflation and `lsf(5 m/s) = 5.0625` are re-derived from the fork's own
`LOW_SPEED_X`/`LOW_SPEED_Y`/`MIN_SPEED`; the phase margins are adversary B's sub-check B6.]

**Also still live, from the design grid** (`DESIGN-V293-TORQUE-MODE-2026-09-13.md` §5): LAF ≤ 2.0
together with Kp ≥ 0.6 at motorway speed is the one RISK region, the V276-shaped outer-loop signature. No
runtime guard exists. If the identification returns a LAF near 2, lower Kp first, then LAF.

**One consequence worth knowing before the drive.** With the config values the *net* command at 15 m/s /
0.9 m/s² comes out **0.929×** today's: the bigger feedforward (×2.55 with the tune held equal) is more than
paid for by Kp 0.9→0.3, Ki 0.30→0.15 and friction 0.01→0.00. The terms move differently with speed, error
and curvature, so **this near-cancellation is a coincidence at one operating point, not a safety margin.**

| configuration | p | i | f | torque |
|---|---|---|---|---|
| installed tune (rate-plant FF) | 1.1523 | 0.7287 | 0.3772 | −0.3763 |
| rate-plant FF off, tune held at today's | 1.1523 | 0.7340 | 0.9600 | −0.4744 |
| the torque config | 0.6123 | 0.5850 | 0.9000 | −0.3495 |

**And the steer-ratio level changes meaning.** Today `SteerRatio` pushes twice in the same direction (the
map feeds both the measurement and the rate-plant feedforward). With the branch off the second consumer is
gone, so the level's sensitivity roughly **halves**. Leave it at 16.88 through identification. [BELIEF,
from the structure.]

---

## E. What this does *not* do

- **It is not a grinding fix.** V288 rev 2 flew a reference-side setpoint pre-filter, the cave was live, the
  D-clamp bind duty fell ×0.03 as designed, and the grinding was **unchanged**. Nothing on the fork's
  reference side reaches the 20 Hz ring. What may remove it is the *firmware* side — a torque-map image
  opens the rate loop by construction, and with the loop open there is no 18–22 Hz object at all (35
  routes). That claim is about V293, not about this config. [BELIEF that V293 removes the symptom — it has
  never been driven.]
- 🛑 **It DOES change authority below full demand.** From adversary A, re-derived from the built image:

  | | V282 | **V293** |
  |---|---|---|
  | delivered peak, at rest | 2461 | **2461 — identical** |
  | demand needed to reach it | idx ~116 | **idx 239–240** |
  | torque per demand index below the rail, wheel **still** | 21.35 counts/idx | **10.34 counts/idx** |
  | delivered at idx 58, wheel **still** | 1236 | **598 (×0.48)** |

  The peak is identical and now needs twice the demand to reach. Against a *moving* wheel V282's servo backs
  off while V293 delivers the same torque whatever the wheel does, so "less authority" holds only in the
  stalled regime. openpilot's LAF identification absorbs the slope change — which is why **the first drive
  is an identification drive and the tune comes after it**. `STEER_MAX` stays 4096 and the ±3/frame rate
  limit is untouched.
- **It writes nothing the REVERT config does not undo.** Restore the REVERT file and the installed tune is
  back exactly.

---

## F. Standing fork fact — the friction compensator is fed the LSF-inflated error

**A property of the fork, not of torque mode, and live on V282 today.**

```python
ff += friction_scale * get_friction(error_with_lsf + JERK_GAIN * friction_jerk, ...)
#                                   ^^^^^^^^^^^^^^   upstream openpilot passes the raw `error`
error_with_lsf = error * (1 + low_speed_factor / max(current_kp, 1e-3))
```

so the compensator's small-signal slope in torque units is `(friction / threshold) · (1 + lsf/Kp)` instead
of `friction / threshold`. At 5 m/s the low-speed factor is **5.0625**:

| Kp | `1 + lsf/Kp` | slope at friction 0.01 |
|---|---|---|
| 0.3 | ×17.9 | 0.596 |
| 0.9 | ×6.6 | 0.221 |
| 1.0 | ×6.1 | 0.202 |

1. **A lower Kp makes the friction term worse.** This is why the config ships friction at 0.
2. **It is already acting on the car.** At today's `SteerKP` 0.9 and `SteerFriction` 0.01 the compensator's
   gain is ×6.6 what the raw error would give at 5 m/s. The config does not add to it.

The same two lines are why `torqueState.p / torqueState.error` reads the `SteerKP` toggle exactly (§C):
`pid_log.error` *is* `error_with_lsf`, and the PID's `p = k_p · error` on the same number.
