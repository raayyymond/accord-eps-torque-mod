# -*- coding: utf-8 -*-
r"""turn_lead_replay.py -- does the fork's TURN-INITIATION LEAD (controlsd.py at Dom c6452361, "Turn-initiation lead
(see TURN_LEAD_*)") explain the logged desired curvature in the high-angle back-and-forth episodes?

    python rlog-tools/studies/angle_loop/turn_lead_replay.py <route> t0:t1 [...]      (t from the first wire frame)

ANALYSIS ONLY (2026-10-15).  Reads the fork-side cache only.  At every controlsState frame it replays, from LOGGED
inputs, the c6452361 code path between the model action and controlsState.desiredCurvature:
  new = modelV2.action.desiredCurvature (latest message)
  TURN LEAD (blinker on, laneChangeState off, 3 <= vEgo < 7, new*dir > -0.003):
      d_near = clip(1.3 v, 4, 14); lead = 0.85 * _plan_dual_probe(plan, d_near, d_near + 3) (0 if stopping short);
      lead = clip(lead, +-0.12); if lead*dir > 0:  lead *= speed_w * engage_w,
      engage_w = clip((1 - |kappa_meas| / |lead|) / (1 - 0.5), 0, 1)        <-- MEASURED curvature (the wheel)
      if lead*dir > max(new*dir, 0): new = lead
  (curvature hold: zero above 10 mph = 4.47 m/s -- frames below are flagged and excluded from the fit;
   lane centering: |correction| <= 0.004 * 0.30 = 0.0012 1/m, ignored)
  desired = clip_curvature(v, desired_prev(LOGGED), new, roll): jerk 5 m/s^3 / v^2 per s, |a_lat| <= 3 (+ roll g)
One-step replay: desired_prev is the LOGGED previous value, so a match cannot come from drift.
Prints R2 of replay vs logged (with and without the lead), the share of frames the lead binds, the share in the
engage_w linear zone (0 < w < 1: the setpoint is a FUNCTION OF THE WHEEL there, d new / d kappa_meas = -2 speed_w),
and the 1-5 Hz band rms of each.
"""
from __future__ import annotations

import contextlib
import io
import math
import sys
from pathlib import Path

import numpy as np
from scipy import signal

_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()] + [Path(__file__).resolve().parent]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import angle_loop_drive_read as D  # noqa: E402
import drive_read_v299 as V  # noqa: E402

DT = 0.01
MAX_JERK, MAX_ACC, MAX_CURV, G = 5.0, 3.0, 0.2, 9.81


def circle(xs, ys, look):
    px = py = 0.0
    for x, y in zip(xs, ys):
        px, py = x, y
        if math.hypot(x, y) >= look:
            break
    d2 = px * px + py * py
    return 0.0 if d2 < 1.0 else 2.0 * py / d2


def dual(xs, ys, dn, df):
    n, f = circle(xs, ys, dn), circle(xs, ys, df)
    if n * f <= 0.0:
        return 0.0
    return n if abs(n) < abs(f) else f


def main():
    route = sys.argv[1]
    with contextlib.redirect_stdout(io.StringIO()):
        W = D.load_route(route)
    FK, _, _ = V.fork_cache(W, D._fr())
    t0 = W["t"][0]
    tc = FK["t_ctl"]
    dlog = FK["ctl_dcurv"].astype(float)
    meas = FK["ctl_curv"].astype(float)
    imd = np.clip(np.searchsorted(FK["t_md"], tc, side="right") - 1, 0, len(FK["t_md"]) - 1)
    mact = FK["md_act_curv"][imd].astype(float)
    px, py = FK["md_px"][imd], FK["md_py"][imd]
    lcs = FK["md_lcstate"][imd]
    ics = np.clip(np.searchsorted(FK["t_cs"], tc, side="right") - 1, 0, len(FK["t_cs"]) - 1)
    v = FK["cs_vego"][ics].astype(float)
    bdir = (FK["cs_rblink"][ics].astype(float) - FK["cs_lblink"][ics].astype(float))
    vs = signal.sosfiltfilt(signal.butter(2, 2.0, fs=100.0, output="sos"), FK["cs_vego"].astype(float))
    aego = np.gradient(vs, FK["t_cs"])[ics]
    icc = np.clip(np.searchsorted(FK["t_cc"], tc, side="right") - 1, 0, len(FK["t_cc"]) - 1)
    lat = FK["cc_latActive"][icc].astype(bool)
    roll = np.interp(tc, FK["t_lp"], FK["lp_roll"].astype(float))
    bp = signal.butter(2, [1.0, 5.0], btype="band", fs=100.0, output="sos")
    for w in sys.argv[2:]:
        a, b = (float(x) for x in w.split(":"))
        S = np.flatnonzero((tc - t0 >= a) & (tc - t0 < b))
        rep, rep0, lb, lin = [], [], [], []
        for i in S:
            new = mact[i]
            vv = v[i]
            dr = bdir[i]
            bind = False
            wlin = False
            if lat[i] and dr != 0.0 and lcs[i] == 0 and 3.0 <= vv < 7.0 and new * dr > -0.003:
                dn = max(min(1.3 * vv, 14.0), 4.0)
                stop = aego[i] < -0.5 and vv ** 2 / (2.0 * -aego[i]) < 1.5 * dn
                lead = 0.0 if stop else dual(px[i], py[i], dn, dn + 3.0) * 0.85
                lead = max(min(lead, 0.12), -0.12)
                if lead * dr > 0.0:
                    sw = min(max((vv - 3.0) / 1.0, 0.0), 1.0)
                    ew = min(max((1.0 - abs(meas[i]) / abs(lead)) / 0.5, 0.0), 1.0)
                    wlin = 0.0 < ew < 1.0
                    lead *= sw * ew
                    if lead * dr > max(new * dr, 0.0):
                        new, bind = lead, True
            out = []
            for nn in (new, mact[i]):
                vv2 = max(vv, 1.0)
                prev = dlog[i - 1]
                r = (MAX_JERK / vv2 ** 2) * DT
                x = min(max(nn, prev - r), prev + r)
                lo, hi = (-MAX_ACC + roll[i] * G) / vv2 ** 2, (MAX_ACC + roll[i] * G) / vv2 ** 2
                x = min(max(x, lo), hi)
                out.append(min(max(x, -MAX_CURV), MAX_CURV))
            rep.append(out[0]); rep0.append(out[1]); lb.append(bind); lin.append(wlin)
        rep, rep0, lb, lin = map(np.asarray, (rep, rep0, lb, lin))
        y = dlog[S]
        r2 = lambda p: 1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2)
        ok = v[S] >= 4.6
        st = np.diff(dlog[np.r_[S[0] - 1, S]])
        rr = (MAX_JERK / np.maximum(v[S], 1.0) ** 2) * DT
        rl = np.abs(st) >= 0.8 * rr
        agree = lambda p: float(np.mean(np.sign(p - dlog[S - 1])[rl] == np.sign(st)[rl])) if rl.sum() else np.nan
        print("   rate-limited logged steps %d (%.0f %% of frames): step-sign agreement WITH lead %.3f, model only %.3f" % (
            rl.sum(), 100 * rl.mean(), agree(rep), agree(rep0)))
        pad = slice(max(S[0] - 300, 0), S[-1] + 300)
        off = S[0] - pad.start
        band = lambda x: np.std(signal.sosfiltfilt(bp, x[pad])[off:off + len(S)])
        print("%s %6.1f-%6.1f v %.1f (>= 4.6 m/s on %.0f %%): R2 replay WITH lead %.3f, model only %.3f "
              "(v >= 4.6: %.3f / %.3f); max |err| with lead %.2f, model only %.2f /km; lead binds %.0f %%, "
              "engage_w linear zone %.0f %% | 1-5 Hz rms /km: logged %.2f model %.2f meas %.2f" % (
                  route.split("_")[1][:12], a, b, np.median(v[S]), 100 * ok.mean(), r2(rep), r2(rep0),
                  (1 - np.sum((y[ok] - rep[ok]) ** 2) / np.sum((y[ok] - y[ok].mean()) ** 2)) if ok.sum() > 10 else np.nan,
                  (1 - np.sum((y[ok] - rep0[ok]) ** 2) / np.sum((y[ok] - y[ok].mean()) ** 2)) if ok.sum() > 10 else np.nan,
                  1e3 * np.max(np.abs(y - rep)), 1e3 * np.max(np.abs(y - rep0)), 100 * lb.mean(), 100 * lin.mean(),
                  1e3 * np.std(signal.sosfiltfilt(bp, dlog[pad])[off:off + len(S)]),
                  1e3 * band(mact), 1e3 * band(meas)))


if __name__ == "__main__":
    main()
