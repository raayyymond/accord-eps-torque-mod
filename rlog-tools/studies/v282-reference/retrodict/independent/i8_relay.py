# -*- coding: utf-8 -*-
"""i8 -- the SteerFriction relay's ACTUAL quasi-linear gain, reconstructed frame by frame from the log.

The fork's `get_friction` on this car is NOT a relay: with steeringAngleDeadzoneDeg = 0 (Honda never
sets it; opendbc's configure_torque_tune default is 0.0) apply_center_deadzone is a no-op and the
term is a SATURATING RAMP,

    fric_lataccel(e) = friction * LAF * clip(e / 0.30, -1, +1),      e = error_with_lsf + 0.22 * friction_jerk

so its slope in TORQUE per unit lateral-accel error is friction / 0.30 (the LAF cancels against
torque_from_lateral_accel), and it saturates at |e| > 0.30 m/s^2.  Against P, whose torque slope is
kp / LAF, the ratio is

    relay / P  =  friction * LAF / (0.30 * kp)                       [small signal]

Two measurements of the derating, both from the LOGGED error_with_lsf (pid_log.error):
  (a) EXACT expected derivative -- the fraction of frames with |e| < 0.30, which is E[f'(e)] / slope
      for the actual distribution, no Gaussian assumption;
  (b) band-limited regression -- rebuild the term on the logged trace, band-pass both to 1.5-3.5 Hz
      and regress, which is the describing function of the actual waveform in the band that matters.

ANALYSIS ONLY.  python i8_relay.py <route> [...]
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V  # noqa: E402

FS = 100.0
THR = 0.30
JERK_GAIN = 0.22
CC_SPEED_BP, CC_SPEED_V = [0.0, 5.0, 12.0, 25.0], [0.08, 0.12, 0.18, 0.18]
CC_LAT_BP, CC_LAT_V = None, None      # filled from the fork below


def fric_jerk_deadzone(v, setpoint, lat_bp, lat_v):
    sd = np.interp(np.maximum(v, 0.0), CC_SPEED_BP, CC_SPEED_V)
    cw = np.interp(np.abs(setpoint), lat_bp, lat_v)
    return sd * cw


def run(route, lat_bp, lat_v):
    D = np.load(V.CACHE / f"{route}.npz", allow_pickle=True)
    S = V.load(route)
    t = S["t"]
    err = np.interp(t, D["t_cs"], D["cs_err"])
    jerk = S["jerk_des"]
    m = S["active"] & ~S["pressed"] & ~S["sat"] & np.isfinite(err) & np.isfinite(jerk)
    out = {}
    for tag, lo, hi in (("15+", 15.0, 99.0), ("5-15", 5.0, 15.0), ("all", 0.0, 99.0)):
        mm = m & (S["v"] >= lo) & (S["v"] < hi)
        if mm.sum() < 3000:
            continue
        dz = fric_jerk_deadzone(S["v"][mm], S["setpoint"][mm], lat_bp, lat_v)
        fj = np.copysign(np.maximum(np.abs(jerk[mm]) - dz, 0.0), jerk[mm])
        x = err[mm] + JERK_GAIN * fj
        lin = float(np.mean(np.abs(x) < THR))
        # band-limited describing function on the longest contiguous engaged run in the bin
        runs = V.runs(mm, t, min_s=20.0)
        num = den = 0.0
        sos = signal.butter(4, [1.5, 3.5], btype="band", fs=FS, output="sos")
        for a, b in runs:
            dz2 = fric_jerk_deadzone(S["v"][a:b], S["setpoint"][a:b], lat_bp, lat_v)
            fj2 = np.copysign(np.maximum(np.abs(jerk[a:b]) - dz2, 0.0), jerk[a:b])
            e2 = err[a:b] + JERK_GAIN * fj2
            if not np.isfinite(e2).all():
                continue
            y2 = np.clip(e2 / THR, -1.0, 1.0)           # relay output / (friction*LAF)
            eb = signal.sosfiltfilt(sos, e2 - e2.mean())
            yb = signal.sosfiltfilt(sos, y2 - y2.mean())
            num += float(np.dot(eb, yb)); den += float(np.dot(eb, eb))
        df_band = (num / den) * THR if den > 0 else float("nan")   # relative to the 1/THR slope
        out[tag] = dict(n=int(mm.sum()), sec=float(mm.sum() / FS), v=float(np.median(S["v"][mm])),
                        err_rms=float(np.std(err[mm])), x_rms=float(np.std(x)),
                        frac_linear=lin, df_band=float(df_band),
                        err_p95=float(np.percentile(np.abs(err[mm]), 95)))
    del S, D
    return out


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    # CENTER_CHATTER_JERK_DEADZONE_LAT_ACCEL_* read straight out of the fork snapshot
    import re
    src = open(HERE / "forksnap" / "lt_84766cdc5.py", encoding="utf-8", errors="replace").read()
    lat_bp = eval(re.search(r"CENTER_CHATTER_JERK_DEADZONE_LAT_ACCEL_BP\s*=\s*(\[[^\]]*\])", src).group(1))
    lat_v = eval(re.search(r"CENTER_CHATTER_JERK_DEADZONE_LAT_ACCEL_V\s*=\s*(\[[^\]]*\])", src).group(1))
    print(f"CENTER_CHATTER_JERK_DEADZONE_LAT_ACCEL_BP {lat_bp}  V {lat_v}")
    res = {}
    for route in sys.argv[1:]:
        r = run(route, lat_bp, lat_v)
        res[route] = r
        print(f"\n=== {route} ===")
        print(f"   {'bin':6s} {'sec':>6s} {'v':>5s} {'rms(err)':>9s} {'rms(x)':>8s} {'p95|err|':>9s} "
              f"{'frac|x|<0.3':>12s} {'DF 1.5-3.5':>11s}")
        for tag, d in r.items():
            print(f"   {tag:6s} {d['sec']:6.0f} {d['v']:5.1f} {d['err_rms']:9.3f} {d['x_rms']:8.3f} "
                  f"{d['err_p95']:9.3f} {d['frac_linear']:12.3f} {d['df_band']:11.3f}")
    json.dump(res, open(HERE / "out_i8_relay.json", "w"), indent=1)
