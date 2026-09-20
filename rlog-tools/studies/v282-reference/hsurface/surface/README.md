# The |H| surface: model-desired -> achieved lateral accel, over speed x frequency x demand amplitude

Stream `surface` of the V282-reference workflow. MEASUREMENT of a closed-loop transfer from a logged
input and a logged output on 16 cached routes. No simulator, no model prediction.

    X = model desired lateral accel   controlsState.desiredCurvature * vEgo^2      (the goal's reference)
    Y = achieved lateral accel        livePose.angularVelocityDevice.z * vEgo      (independent of EPS mode)
    Z = the controller's setpoint     controlsState...torqueState.desiredLateralAccel

## Run order

| script | what it produces |
|---|---|
| `params_all.py` | `params_all.json` -- each route's flown fork params from its OWN initData (attribution) |
| `inv.py` | `inv.json`, `INV-OUT.txt` -- engaged seconds per speed bin, run lengths, instrument checks, rail census |
| `extract.py` | `spec_{40.96,20.48,10.24,5.12}.npz` -- per-window complex spectra of X, Y, Z, U + metadata. Has a self-test that must recover a known gain 0.8 and lag 0.25 s and agree with `v282cmp.band_H` |
| `surface.py` | `surface.json`, `ranked.json`, `SURFACE-OUT.txt` -- the cell table, floors, CIs, the ranked miss |
| `summary.py` | `SUMMARY-OUT.txt` -- exposure-weighted per band / per speed / per amplitude, admissibility census |
| `extras.py` | `EXTRAS-OUT.txt` -- where the demand lives, the causality direction test, amplitude trends, the 1.2-4 Hz output-power ratios |
| `lagsplit.py` | `LAGSPLIT2-OUT.txt` -- the X->Z / Z->Y lag split, grouped by flown `AccordRefFilter` |
| `reffilter.py` | per-route setpoint lag vs each route's own `AccordRefFilter` (the 2*RC identification) |
| `verify_crux.py` | independent time-domain check of the headline cells (shares no code with `surface.py`) |

## Method rules honoured

- Per-bin |H| = |Pxy|/Pxx averaged as MAGNITUDES weighted by input power. Never a phasor average.
- The SAME window length and taper for both builds inside a cell; each band is measured at the window
  length that resolves it (0.06-0.15 Hz at 40.96 s ... 1.2-4 Hz at 5.12 s), with cross-scale checks.
- Windows never cross a clock gap, a disengagement or a `steeringPressed` frame, and must spend >=80%
  of their samples inside their own speed bin.
- Every cell carries a coherence value and its 95% null floor, a split-half |H| floor, a surrogate |H|
  (each window's input against a different window's output), and a route-cluster bootstrap CI.
- Amplitude strata use FIXED absolute cuts on p95 |model| so exposure fractions mean something.
- Cells that cannot be read are PRINTED with the reason and the exposure they carry, never dropped.
