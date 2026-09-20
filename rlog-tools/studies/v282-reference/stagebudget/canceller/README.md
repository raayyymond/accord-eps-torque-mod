# Stream `canceller` — is the fork's delay canceller actually cancelling?

MEASUREMENT of a software stage from its own logged input and output on 15 cached routes, plus exact
discrete algebra of that stage. No simulator, no prediction of the car's response.

## Run order

| script | what it produces |
|---|---|
| `c1_delayparams.py` | `c1_delayparams.json` — each route's OWN initData: `SteerDelay`, `UseAutoSteerDelay`, `AdvancedLateralTune`, `AccordRefFilter`, `AccordJerkLpHz`, persisted `LiveDelay` |
| `c1b_livedelay.py` | `C1B-OUT.txt` — decodes the banked `LiveDelay` param and prints the in-route `lateralDelay` trace (median/p5/p95/number of changes) |
| `c2_stage.py` | `C2-OUT.txt`, `c2_stage.json` — **A.** frame-by-frame reconstruction of the logged setpoint (the validation gate) · **B.** realised \|H\|/phase of `u→setpoint`, `u→sp_pre` (canceller alone) and `raw→jerk` (F_j alone) vs the closed-form discrete algebra |
| `c2a_align.py`, `c2b_identity.py` | diagnostics that pinned `delay_frames` and the filter rc from the log alone; `c2b` is the exact-identity test that caught the wrong D |
| `c3_dquestion.py` | `C3-OUT.txt` — the fork's own `lagd.py` estimator re-implemented and re-run offline on every route (with a pass/fail positive control) |
| `c4_dose.py` | `C4-OUT.txt` — dose tables for `SteerDelay` and `HONDA_ACCORD_JERK_LP_HZ`, and a second estimate of the true model→achieved group delay from the band phase at ≥15 m/s |
| `c5_speedcheck.py` | `C5-OUT.txt` — the stage's transfer split by speed bin (it is speed-invariant to ±0.003) |

## The correction that everything else rests on

🛑 **D in the canceller is `liveDelay.lateralDelay + 0.1`, not `liveDelay.lateralDelay`.**
`controlsd.py`: `lat_delay = self.sm["liveDelay"].lateralDelay + get_control_lateral_smooth_seconds(...)`,
which for `brand == "honda"` returns `LAT_SMOOTH_SECONDS = 0.1` — verified at all 7 flown commits.
So V282 flew **D = 0.300 s** and rev 6.4 flew **D = 0.390–0.400 s**.

With the wrong D the reconstruction of the logged setpoint has a 25 % residual and the jerk filter appears
to have a 0.8 Hz corner. With the right D the residual is **0.03–0.12 %**, `delay_frames` lands exactly on
`int(D/0.01)`, and the filter rc lands exactly on `1/(2π·LP_FILTER_CUTOFF_HZ)` at zero frame shift.

## Method rules honoured

- Per-bin \|H\| = \|Pxy\|/Pxx averaged as MAGNITUDES weighted by input power; lag = −phase/(2πf) per bin, same weights.
- Predictions are the **discrete** transfer (`alpha = dt/(rc+dt)`), band-averaged with the *same* weights as the measurement.
- Windows never cross a clock gap, a disengagement or a `steeringPressed` frame; the first 2 s of every
  engaged run is dropped (the request buffer and both filters are priming).
- "Engaged" = laterally engaged (`controlsState...torqueState.active` AND `carControl.latActive`).
- Every route's configuration is read from its OWN initData × its own flown `GitCommit`, never from a label.
- The `lagd` replay carries a positive control (inject a known +0.10 / +0.20 s, recover +0.100 / +0.204).
- ⚠ The 1.20–2.40 Hz phase column wraps past −180° on the `AccordRefFilter 0.12` routes; read the
  canceller-only column there, and do not read a negative "lag" as a lead.
