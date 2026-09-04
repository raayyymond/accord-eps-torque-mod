# -*- coding: utf-8 -*-
"""straight_understeer_v282.py -- IS "UNDERSTEER ON STRAIGHT ROADS" AN OPENPILOT-SIDE PROBLEM?

The operator's V282 complaint list includes "understeer on straight roads (I think this should be a
StarPilot change)".  Straight-road behaviour is the small-command, near-centre regime, where THREE
different mechanisms all predict under-turn and the record has evidence for each:

  H1  openpilot ISN'T ASKING      -- net PID output ~0 in steady state (f cancelled by p and i)
  H2  the EPS ISN'T DELIVERING    -- the P-only droop / stall class (V281r3 settled at 0.62 of request)
  H3  openpilot IS asking and the EPS IS delivering, but openpilot's MEASUREMENT is inflated by
      SteerRatio 12.5 vs the truthful 16.1, so the loop settles 1 - 12.5/16.1 = 22.4 % SHORT of the
      true target and reports zero error while doing it.

H3 is decisive if true, because it is FREE to fix (a param) and it is invisible to every instrument
that closes on openpilot's own `error`.

Discriminators, all SR-FREE on at least one side:
  A  measurement bias      m/pose = controlsState.actualLateralAccel / (v*yaw_cal - g sin roll)
                           H3 predicts m/pose = 16.33/SR_param on each route.
  B  road-side tracking    lat_torqued vs desiredLateralAccel (BOTH SR-free) on straight frames,
                           delay-matched.  slope < 1 = real road-side under-turn.
  C  the ask               |0xE4 cmd|, demand index, and the f/p/i/d decomposition on straight frames.
                           H1 predicts |output| ~ 0 WITH a live error; H3 predicts error ~ 0.
  D  EPS delivery          measured column rate / the map's own reference at the straight-road demand
                           indices, plus the 427 torque tap.  H2 predicts << 1 here.
  E  persistent-error runs on straights: is openpilot's own error one-signed for seconds?

Arms:  r34 = V280 rev 2, SR 16.1, EPS Ki 0     (the SR control)
       r35 = V281 rev 3, SR 12.5, EPS Ki 0     (== V282 for this purpose: V282 adds only the INERT r24 tap cave)
       r36/r37/r38 = V283, SR 12.5, EPS Ki 50  (the integrator confounds the DC face -- reported separately)

Run: python rlog-tools/studies/osc-highangle/straight_understeer_v282.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oversteer_v283 as O  # noqa: E402

V, CO, B = O.V, O.CO, O.B
FS, CPD = O.FS, O.CPD
G = 9.81

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROUTES = ("r34", "r35", "r36", "r37", "r38")
ARMS = (("r34  V280r2 SR16.1 Ki0", ("r34",)),
        ("r35  V281r3 SR12.5 Ki0 (=V282)", ("r35",)),
        ("V283 SR12.5 Ki50", ("r36", "r37", "r38")))
SR_PARAM = {"r34": 16.1, "r35": 12.5, "r36": 12.5, "r37": 12.5, "r38": 12.5}

STRAIGHT = 0.0020      # |desiredCurvature| below this = "straight road" (radius > 500 m)
VMIN = 15.0            # m/s
LINES = []


def pr(s=""):
    print(s, flush=True)
    LINES.append(s)


def med(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else np.nan


def runs_of(mask, minlen):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= minlen]


def tls_slope(x, y):
    """total-least-squares slope through the origin (both axes noisy)."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if len(x) < 50:
        return np.nan, 0
    sxx, syy, sxy = float(x @ x), float(y @ y), float(x @ y)
    th = 0.5 * np.arctan2(2 * sxy, sxx - syy)
    return (float(np.tan(th)) if abs(np.cos(th)) > 1e-9 else np.nan), len(x)


def main():
    grids, routes, sims = {}, {}, {}
    for tag in ROUTES:
        grids[tag] = B.grid(B.load(tag))
        routes[tag] = V.Route(tag)
        sims[tag] = O.sim(routes[tag], kp=O.KP_OF[tag], ki=O.KI_OF[tag])

    def masks(tag):
        g = grids[tag]
        j = np.clip(np.searchsorted(g["lp_t"], g["t"]) - 1, 0, len(g["lp_t"]) - 1)
        base = (g["lat"] > 0.5) & (g["active"] > 0.5) & (g["pressed"] < 0.5) & (g["v"] > VMIN) & g["lp_calok"][j]
        st = base & (np.abs(g["descurv"]) < STRAIGHT)
        cv = base & (np.abs(g["descurv"]) >= 0.005)
        return base, st, cv

    # ------------------------------------------------------------------ A. measurement bias (SteerRatio)
    pr("=" * 160)
    pr("A -- MEASUREMENT BIAS: openpilot's actualLateralAccel vs the SR-FREE road value (v*yaw_cal - g sin roll)")
    pr("     H3 predicts m/pose = CP.steerRatio(16.33) / SR_param.")
    pr("     TLS slope through the origin on engaged frames with |pose| > 0.5 m/s2 (small-signal frames are all noise).")
    pr("=" * 160)
    for name, tags in ARMS:
        for tag in tags:
            g = grids[tag]
            base, st, cv = masks(tag)
            m = base & (np.abs(g["lat_torqued"]) > 0.5)
            s, n = tls_slope(g["lat_torqued"][m], g["lat_vm"][m])
            mm = base & (np.abs(g["lat_torqued"]) > 1.0)
            s2, n2 = tls_slope(g["lat_torqued"][mm], g["lat_vm"][mm])
            pr("  %-34s %s  m/pose %.3f (n=%d)   |pose|>1.0 %.3f (n=%d)   SRparam %.1f   predicted %.3f"
               % (name, tag, s, n, s2, n2, SR_PARAM[tag], 16.33 / SR_PARAM[tag]))

    # ------------------------------------------------------------------ B. road-side tracking on straights
    pr()
    pr("=" * 160)
    pr("B -- ROAD-SIDE TRACKING ON STRAIGHT ROADS: lat_torqued vs desiredLateralAccel, BOTH SR-free, delay-matched")
    pr("     frames: engaged, not pressed, v > %.0f m/s, |desiredCurvature| < %.4f /m (radius > %.0f m)" % (VMIN, STRAIGHT, 1 / STRAIGHT))
    pr("     slope 1.00 = the road gets exactly what openpilot asked for.  < 1 = UNDER-turn on straights.")
    pr("=" * 160)
    LAGS = np.arange(0.0, 1.25, 0.05)
    for name, tags in ARMS:
        for tag in tags:
            g = grids[tag]
            base, st, cv = masks(tag)
            t = g["t"]
            des = g["desiredLateralAccel"]
            road = g["lat_torqued"]
            best = (None, -9.0)
            for L in LAGS:
                d = np.interp(t - L, t, des)
                m = st & np.isfinite(d) & np.isfinite(road)
                if m.sum() < 200:
                    continue
                c = float(np.corrcoef(d[m], road[m])[0, 1])
                if c > best[1]:
                    best = (L, c)
            L = best[0] if best[0] is not None else 0.3
            d = np.interp(t - L, t, des)
            m = st & np.isfinite(d) & np.isfinite(road)
            s, n = tls_slope(d[m], road[m])
            mc = cv & np.isfinite(d) & np.isfinite(road)
            sc, nc = tls_slope(d[mc], road[mc])
            pr("  %-34s %s straight %.3f (r=%.2f lag %.2fs, %.0fs) | curve %.3f (%.0fs)"
               % (name, tag, s, best[1], L, n / FS, sc, nc / FS))

    # ------------------------------------------------------------------ C. the ask, on straights
    pr()
    pr("=" * 160)
    pr("C -- WHAT OPENPILOT ASKS FOR ON STRAIGHTS: the f/p/i/d decomposition, the CAN command, the demand index")
    pr("     H1 (isn't asking) predicts |output| ~ 0 WITH a live |error|.  H3 predicts |error| ~ 0.")
    pr("=" * 160)
    pr("  %-5s %8s %9s %8s %8s %8s %8s %8s %8s %8s %7s" %
       ("route", "|err|", "err(sgn)", "|f|", "|p|", "|i|", "|out|", "|cmd|", "idx p50", "idx p90", "sec"))
    for name, tags in ARMS:
        for tag in tags:
            g = grids[tag]
            base, st, cv = masks(tag)
            r = routes[tag]
            n = min(len(st), len(r.idx))
            stm = st[:n]
            idx = r.idx[:n]
            pr("  %-5s %8.3f %9.3f %8.3f %8.3f %8.3f %8.3f %8.1f %8.1f %8.1f %7.0f" % (
                tag, med(np.abs(g["error"][st])), med(g["error"][st]), med(np.abs(g["f"][st])), med(np.abs(g["p"][st])),
                med(np.abs(g["i"][st])), med(np.abs(g["output"][st])), med(np.abs(g["cmd"][st])),
                med(idx[stm]), float(np.nanpercentile(idx[stm], 90)) if stm.sum() > 10 else np.nan, st.sum() / FS))
    pr("  (error/f/p/i/out are m/s2 in the torque controller's lateral-accel frame; cmd = 0xE4 STEER_TORQUE counts)")

    # ------------------------------------------------------------------ D. EPS delivery at straight-road demand
    pr()
    pr("=" * 160)
    pr("D -- EPS DELIVERY AT THE STRAIGHT-ROAD DEMAND INDEX: measured column rate / the map's own reference")
    pr("     1.00 = the inner rate loop has no steady-state droop.  H2 predicts << 1 in the low-idx bins.")
    pr("     frames: engaged, hands light, command HELD >= 0.4 s, the map's reference > 1.0 deg/s")
    pr("=" * 160)
    IDXB = ((1, 6), (6, 12), (12, 20), (20, 40), (40, 68))
    for name, tags in ARMS:
        for tag in tags:
            r = routes[tag]
            ref = sims[tag]["ref_deg"][r.i100]
            k = 40
            pad = np.pad(r.idx, (k // 2, k - k // 2), mode="edge")
            win = np.lib.stride_tricks.sliding_window_view(pad, k)[: len(r.idx)]
            held = (win.max(1) - win.min(1)) <= np.maximum(0.25 * win.mean(1), 4.0)
            base = r.eng & (np.abs(r.tq_raw) < 400) & held & (ref > 1.0)
            cells = []
            for lo, hi in IDXB:
                m = base & (r.idx >= lo) & (r.idx < hi)
                cells.append("%3d-%3d %s(%5.1fs)" % (lo, hi, "%.2f " % med(np.abs(r.wire[m]) / CPD / ref[m]) if m.sum() > 100 else " --  ", m.sum() / FS))
            pr("  %-5s %s" % (tag, " | ".join(cells)))

    # ------------------------------------------------------------------ E. persistent-error runs on straights
    pr()
    pr("=" * 160)
    pr("E -- PERSISTENT ONE-SIGNED ERROR ON STRAIGHTS (openpilot's own error), and what it does about it")
    pr("     runs >= 1.0 s of |error| > 0.10 m/s2 with a constant sign, inside the straight mask")
    pr("=" * 160)
    for name, tags in ARMS:
        for tag in tags:
            g = grids[tag]
            base, st, cv = masks(tag)
            e = g["error"]
            out, dur, ii = [], [], []
            for sgn in (+1, -1):
                m = st & (sgn * e > 0.10)
                for a, b in runs_of(m, int(1.0 * FS)):
                    dur.append((b - a) / FS)
                    out.append(med(sgn * g["output"][a:b]))
                    ii.append(med(sgn * g["i"][a:b]))
            pr("  %-5s runs %3d  total %6.1fs (%4.1f %% of straight)  median dur %.2fs  median SIGNED output %+.3f  median SIGNED i %+.3f"
               % (tag, len(dur), float(np.sum(dur)) if dur else 0.0,
                  100.0 * (float(np.sum(dur)) if dur else 0.0) / max(st.sum() / FS, 1e-9), med(dur), med(out), med(ii)))

    out = os.path.join(HERE, "_scratch", "straight_understeer_v282.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
