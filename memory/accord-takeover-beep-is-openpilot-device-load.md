# ⚠ The intermittent "take over" beep is openpilot DEVICE LOAD — not the EPS, not the car

Diagnosed 2026-07-29 from route `24`. The operator had been getting intermittent take-over prompts
across drives "even though nothing went wrong from my perspective". It is a **soft-disable that
self-recovers**, and the car is provably innocent.

## The event

```
426.410s  alertType='commIssue/softDisable'          "TAKE CONTROL IMMEDIATELY / Communication Issue Between Processes"
426.530s  alertType='selfdrivedLagging/softDisable'  "TAKE CONTROL IMMEDIATELY / System Lagging"
427.450s  underlying condition clears  (duration 1.040 s; banner lingers to ~428.5 s)
```

**Fired exactly once as a driver-visible banner in the whole 15:43 route.** It never escalated:
`selfdriveState.enabled/active` and `carControl.latActive` stayed true throughout (zero transitions
279 s → 588 s), so LKAS and ACC were never actually lost. That is precisely why it feels like a false
alarm — openpilot shouted and then caught itself.

## The car and the EPS are clean nulls at that moment

- CAN `0x18F` `STEER_STATUS` = **0 continuously from 193.1 s to 588.0 s** — the event sits deep inside
  one unbroken no-fault span. (The only ST=3 blips route-wide are at t=0.265 s / 943.668 s, ignition
  on/off — consistent with the V53 `0xC62EA`→0 cal, not a fault.)
- `controlsState.lateralControlState.torqueState.saturated` = **False in 94,241/94,241** samples
  route-wide ⇒ `steerSaturated` excluded outright.
- `pandaStates`: **3 health transitions in the entire route**, all bracketing ignition. `can0`/`can1`
  totalError / TxLost / RxLost / coreReset **flat zero all route**; zero delta inside [420,435] s on
  every counter; `spiErrorCount` grows uniformly ~0.39/s everywhere, not bursty.
- **Zero `steeringPressed` transitions** in [420,435] s ⇒ the "21 Hz chatter trips the pressed
  threshold" idea is excluded *for this event* by direct evidence.
- V56 probe field calm mid-band (7-8) throughout 425-433 s.

## Root cause: diffuse scheduling contention, no single culprit

- Inter-arrival gaps for `modelV2`, `cameraOdometry`, `livePose`, `liveCalibration`, `radarState`,
  `driverStateV2`, `controlsState` **all peak far from the event** (466/471/437/481/506 s).
  `controlsState`'s worst gap route-wide is 29.5 ms against a ~10 ms cadence.
- **Zero camera frameId skips** across all three cameras.
- `procLog` per-process CPU (⚠ `cpuUser`/`cpuSystem` are **cumulative seconds** — you must difference
  consecutive samples ÷ dt): biggest mover at the event is `starpilot.system` at **+5.3 pp**; `pandad`
  +0.2, `selfdrived` +0.3. No spike.
- The real condition is chronic: **5-6 of 8 cores near saturation continuously**, 70-79% average, on a
  StarPilot/sunnypilot fork carrying `starpilot.system`, `starpilot.starp`, `mapd` on top of the stock
  stack. `thermalStatus` never leaves green (~72 °C); device offline all route.

⇒ `selfdrived`'s own loop-freshness watchdog crossed threshold for ~1 s under standing load and
recovered. **The lever is process load, not code** — but see
[[feedback-no-openpilot-side-modifications]]; this is the operator's call.

## 🛑 Three rlog tooling traps this exposed

1. **`selfdriveState.alertSound` is unpopulated route-wide** — `none` in every frame including a
   full-size `userPrompt` "TAKE CONTROL IMMEDIATELY". **Absence of `alertSound` is NOT absence of a
   beep.** Anchor on `alertType` / `alertStatus` / `onroadEvents` instead.
2. **`onroadEvents` DOES exist** in this fork (top-level `Event.onroadEvents`, edge-triggered so it has a
   low message count and is easy to miss in a `which()` histogram). It carries `softDisable` /
   `immediateDisable` booleans — use those, not substring matching on names.
3. 🛑 **Anchor the route clock on the first `carState` of each segment**, never the first event of any
   type. Every segment file's first entry is a re-embedded bootstrap message carrying the **original
   boot timestamp** (bit-identical `5786544129145` across segs 0/6/7/8), which biases a naive clock
   **+1.34 s** late. Correct convention: `route_t = seg*60 + (mono − t0_carState_of_that_seg)/1e9`.
4. `0x33D` LKAS_HUD **byte 4 is counter+checksum**, cycling `0x00/0x1f/0x2e/0x3d` every 10 ms. Not a
   beep bit. Only bytes 0-3 carry HUD state.

## How to apply
- Do not spend firmware effort on this symptom; it is device-side and the CAN/EPS null is clean.
- One loose thread, not chased: per-core `iowait`/`softirq` from `ProcLog.CPUTimes`, which would separate
  CPU-bound contention from an I/O stall.
- Cross-drive recurrence is unquantified — this sweep covers one route (1 engaged occurrence in 15:43).
