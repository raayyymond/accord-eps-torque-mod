# -*- coding: utf-8 -*-
"""Describing-function library: |H| (model desired lateral accel -> achieved) vs DEMAND AMPLITUDE,
at matched speed and frequency band.

MEASUREMENT ON LOGGED DATA, NOT A MODEL.  x is the logged model reference, y is the logged achieved
lateral acceleration (livePose yaw x v).  |H| is the closed-loop transfer actually realised on the
road.  No plant model, no simulation, no open-loop prediction enters anywhere.

Definitions, all inherited from the shared library so every stream shares one |H|:
  * |H| per frequency bin = |Pxy|/Pxx, averaged over the band weighted by input power.  MAGNITUDES
    are averaged, never phasors (v282cmp.band_H; phasor averaging biases |H| low where phase rotates).
  * windows are taken inside contiguous usable RUNS only (v282cmp.runs) -- never across a clock gap.
  * "usable" = laterally engaged (controlsState.active AND carControl.latActive) and NOT
    steeringPressed, per v282cmp.usable.
  * amplitude of a window = RMS of the band-passed model reference in m/s^2 (4th-order Butterworth,
    zero phase).  Reported also as a sinusoid-equivalent peak (x sqrt 2) and as DESIRED WHEEL ANGLE
    in deg through the fork's own vehicle model.

Admissibility, enforced by the caller:
  * coherence floor  -- a cell whose input-power-weighted band coherence is below COH_MIN is not
    reported as a gain.
  * split-half noise floor -- runs are split by parity, |H| computed on each half; half the absolute
    difference is the noise floor for that cell.  A group difference smaller than the floor is not
    a finding.
  * run-cluster bootstrap CI (resample RUNS, not windows: overlapping windows are not independent).
"""
import os
import sys
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, STUDY)
sys.path.insert(0, os.path.join(STUDY, "ffgain_ceiling"))
import v282cmp as C          # noqa: E402
import ffrecon as F          # noqa: E402

FS = C.FS
COH_MIN = 0.50
# (f1, f2, window samples).  Window length set so the band holds >= 2 Welch bins.
BANDS = [(0.08, 0.25, 2048),
         (0.15, 0.30, 1024),
         (0.30, 0.60, 1024),
         (0.60, 1.20, 512),
         (1.20, 2.50, 256)]
SPD = [(2, 8), (8, 15), (15, 22), (22, 40)]
_SOS = {}


def sos(f1, f2):
    if (f1, f2) not in _SOS:
        _SOS[(f1, f2)] = signal.butter(4, [f1, f2], btype="band", fs=FS, output="sos")
    return _SOS[(f1, f2)]


def deg_per_curv(v):
    """deg of DESIRED wheel angle per 1/m of curvature, from the fork's own VehicleModel at the
    nominal on-centre rack ratio (ffrecon, itself read out of the flown commits)."""
    return np.degrees(F.steer_from_curvature_rad(1.0, np.maximum(np.asarray(v, float), 1.0),
                                                 0.0, F.SR_NOMINAL, 1.0))


def route_runs(rk, vmin=1.5, min_s=2.56):
    """Per-route list of contiguous usable stretches, each a dict of float32 per-frame arrays."""
    S = C.load(rk)
    m = C.usable(S, vmin)
    laf = _fit_laf(S)
    out = np.nan_to_num(S["out"])
    pre = np.nan_to_num(S["p"] + S["i"] + S["f"]) / laf     # command BEFORE the +/-1 clip
    R = []
    for a, b in C.runs(m, S["t"], min_s=min_s):
        R.append(dict(x=np.nan_to_num(S["model"][a:b]).astype(np.float32),
                      y=np.nan_to_num(S["la_pose"][a:b]).astype(np.float32),
                      ya=np.nan_to_num(S["la_act"][a:b]).astype(np.float32),
                      v=np.nan_to_num(S["v"][a:b]).astype(np.float32),
                      sa=np.nan_to_num(S["sa"][a:b]).astype(np.float32),
                      sr=np.nan_to_num(S["sr"][a:b]).astype(np.float32),
                      out=np.abs(out[a:b]).astype(np.float32),
                      pre=np.abs(pre[a:b]).astype(np.float32)))
    del S
    return R, laf


def _fit_laf(S):
    """latAccelFactor read out of the LOG, from the identity out == -clip(p+i+f, +/-LAF)/LAF on
    unsaturated frames -- not from a toggle.  Verified max frame error < 1e-7 on all 11 routes."""
    m = C.usable(S)
    pre = np.nan_to_num(S["p"] + S["i"] + S["f"])[m]
    o = np.nan_to_num(S["out"])[m]
    un = np.abs(o) < 0.95
    return float(np.dot(pre[un], -o[un]) / max(np.dot(o[un], o[un]), 1e-30))


def windows(R, W, hop=None, ykey="y"):
    """Slice every run into windows of W samples.  Returns a list of dicts; `rid` is the run index,
    which is the bootstrap/split-half cluster (overlapping windows inside a run are NOT independent).
    """
    hop = hop or W // 2
    out = []
    for rid, r in enumerate(R):
        n = len(r["x"])
        for k in range(0, n - W + 1, hop):
            sl = slice(k, k + W)
            out.append(dict(rid=rid, x=r["x"][sl], y=r[ykey][sl], v=float(np.median(r["v"][sl])),
                            vmin=float(r["v"][sl].min()), vmax=float(r["v"][sl].max()),
                            sa_med=float(np.median(np.abs(r["sa"][sl]))),
                            sa_max=float(np.abs(r["sa"][sl]).max()),
                            rail=float((r["out"][sl] >= 0.98).mean()),
                            near=float((r["out"][sl] >= 0.90).mean()),
                            over=float(r["pre"][sl].max())))
    return out


def amp(win, f1, f2):
    """RMS of the band-passed model reference over the window, m/s^2 (the describing-function
    amplitude).  Zero-phase filtfilt; edges are inside the window so no run boundary is crossed."""
    return float(np.sqrt(np.mean(signal.sosfiltfilt(sos(f1, f2), win["x"].astype(float)) ** 2)))


def cell_H(ws, f1, f2):
    """|H| for a set of windows, using the SHARED band_H (magnitude-averaged, power-weighted)."""
    if not ws:
        return None
    return C.band_H([(w["x"].astype(float), w["y"].astype(float)) for w in ws], f1, f2)


def split_half(ws, f1, f2):
    """Noise floor: |H| on even-index runs vs odd-index runs.  Returns (H_a, H_b, floor)."""
    rids = sorted({w["rid"] for w in ws})
    if len(rids) < 2:
        return None, None, float("nan")
    ea = set(rids[0::2])
    A = cell_H([w for w in ws if w["rid"] in ea], f1, f2)
    B = cell_H([w for w in ws if w["rid"] not in ea], f1, f2)
    if not A or not B:
        return None, None, float("nan")
    return A["H"], B["H"], abs(A["H"] - B["H"]) / 2.0


def boot_H(ws, f1, f2, nb=200, rng=None):
    """Run-cluster bootstrap CI on |H| (resample runs with replacement)."""
    rng = rng or np.random.default_rng(7)
    by = {}
    for w in ws:
        by.setdefault(w["rid"], []).append(w)
    rids = list(by)
    if len(rids) < 2:
        return (float("nan"), float("nan"))
    vals = []
    for _ in range(nb):
        pick = rng.choice(rids, len(rids), replace=True)
        sel = [w for r in pick for w in by[r]]
        r = cell_H(sel, f1, f2)
        if r:
            vals.append(r["H"])
    if len(vals) < 20:
        return (float("nan"), float("nan"))
    return tuple(float(q) for q in np.percentile(vals, [2.5, 97.5]))


def _self_test():
    """Positive controls: (1) a KNOWN linear gain is recovered at every amplitude (no spurious
    amplitude dependence from the estimator); (2) a KNOWN saturation droops at large amplitude;
    (3) a KNOWN Coulomb/deadband droops at small amplitude.  All three must pass or nothing below
    is admissible."""
    rng = np.random.default_rng(0)
    n = 300 * int(FS)
    f1, f2, W = 0.30, 0.60, 1024
    base = C.lowpass(rng.standard_normal(n), 1.2)
    base = base / np.sqrt(np.mean(base ** 2))
    lagN = 6
    msg = []
    for name, fn in (("linear 0.9", lambda u: 0.9 * u),
                     ("sat |u|<=1.0", lambda u: 0.9 * np.clip(u, -1.0, 1.0)),
                     ("deadband 0.25", lambda u: 0.9 * np.sign(u) * np.maximum(np.abs(u) - 0.25, 0.0))):
        row = []
        for A in (0.25, 0.5, 1.0, 2.0, 4.0):
            x = A * base
            yv = fn(x)
            y = np.concatenate([np.zeros(lagN), yv[:-lagN]])
            R = [dict(x=x.astype(np.float32), y=y.astype(np.float32), ya=y.astype(np.float32),
                      v=np.full(n, 20.0, np.float32), sa=np.zeros(n, np.float32),
                      sr=np.zeros(n, np.float32), out=np.zeros(n, np.float32),
                      pre=np.zeros(n, np.float32))]
            ws = windows(R, W)
            r = cell_H(ws, f1, f2)
            row.append((amp(ws[0], f1, f2), r["H"]))
        msg.append(f"  {name:16s} " + "  ".join(f"A{a:.2f}->H{h:.3f}" for a, h in row))
        if name == "linear 0.9":
            assert max(h for _, h in row) - min(h for _, h in row) < 0.01, row
            assert abs(row[0][1] - 0.9) < 0.02, row
        if name.startswith("sat"):
            assert row[0][1] > 0.88 and row[-1][1] < 0.45, row      # droops at LARGE amplitude
        if name.startswith("deadband"):
            assert row[0][1] < 0.45 and row[-1][1] > 0.85, row      # droops at SMALL amplitude
    return "dflib self-test OK: flat for a linear gain, droops LARGE for saturation, droops SMALL " \
           "for a deadband\n" + "\n".join(msg)


if __name__ == "__main__":
    print(C._self_test())
    print(F._self_test())
    print(_self_test())
    print()
    for v in (3, 5, 8, 12, 15, 20, 25, 30):
        print(f"  v {v:4.1f} m/s   deg desired wheel angle per 1/m curvature {float(deg_per_curv(v)):8.1f}"
              f"   -> 0.10 m/s^2 of demand = {0.10 / v**2 * float(deg_per_curv(v)):7.3f} deg")
