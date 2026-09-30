# -*- coding: utf-8 -*-
"""s7_closedloop.py -- adversary `stability`, attack surfaces (c) time domain and (d): NONLINEAR closed-loop scenarios
with MY OWN integer lane (s0 MyLane == golden model), MY OWN plant integrator (0.2 ms sub-stepped Karnopp stick-slip,
saturating spring; not the harness's 1 ms semi-implicit Euler), MY OWN demand chain (census arithmetic), the Honda
limiter and the fork's r1 law via the harness ForkPort (bit-identical to the real LatControlTorque by gate H3b; my
retrodiction spot check in s5 passed through it).  V294 and A1017 rows see IDENTICAL inputs and noise.

Scenarios (30 s each, all in one batch):
  TURN v a   : desired lat accel ramps 0 -> a in 1 s at t = 3 s, holds to 12 s, ramps back in 1 s, 0 to 30 s.
               v in {8, 12, 16, 20} m/s, a in {1.5, 3.0} m/s^2  (hard turns at medium speed)
  CENTRE v   : desired 0 + a constant road torque 25 T + a 0.2-3 Hz road torque (10 T rms), v in {3.1, 8, 17, 27}
               (on-centre hunting / stick-slip)
  SLALOM v f : desired 1.5 sin(2 pi f t), v in {12, 20}, f in {0.3, 0.6, 1.0} Hz
Members: nominal, J_lo, J_hi2, b_lo, F_hi, light_b, light_b J x2.5, light_b b x0.5.
Runs: x-noise 0 (deterministic) and 1.93 counts (same draws for both lanes).
"""
import json
import os
import sys
import time
from dataclasses import replace

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "design", "harness"))
import v295_harness as H  # noqa: E402
from s0_lane_spotcheck import MyLane, lerp  # noqa: E402

MAP_X = [0, 12, 20, 24, 32, 64, 96, 128, 160, 240]
MAP_Y = [0, 52, 86, 103, 138, 275, 413, 550, 688, 1032]
MAPT = np.array([lerp(MAP_X, MAP_Y, i) for i in range(241)], np.int64)
SECS = 30.0


def demand(wire):
    """census section 2 at rest (bar 0: G = 255, taper 254): idx and the march-convention sp."""
    S = np.clip(-4 * np.asarray(wire, np.int64), -0x4000, 0x4000)
    prod = ((255 * 255) & 0xFFFF) * S >> 16
    v = np.clip(prod >> 6, -240, 240)
    idx = np.abs(v)
    sgn = np.where(v < 0, -1, 1)
    return -sgn * MAPT[idx]


def scenarios():
    t = np.arange(int(SECS * 100)) * 0.01
    out = []
    for v in (8.0, 12.0, 16.0, 20.0):
        for a in (1.5, 3.0):
            la = np.clip((t - 3.0) / 1.0, 0, 1) * a
            la = np.where(t > 12.0, np.clip(1 - (t - 12.0) / 1.0, 0, 1) * a, la)
            out.append(("TURN", v, a, la, 0.0, 0.0))
    for v in (3.1, 8.0, 17.0, 27.0):
        out.append(("CENTRE", v, 0.0, np.zeros_like(t), 25.0, 10.0))
    for v in (12.0, 20.0):
        for f in (0.3, 0.6, 1.0):
            out.append(("SLALOM", v, f, 1.5 * np.sin(2 * np.pi * f * t), 0.0, 0.0))
    return t, out


def members():
    fam = H.family()
    lb = fam["light_b"]
    M = {k: fam[k] for k in ("nominal", "J_lo", "J_hi2", "b_lo", "F_hi", "light_b")}
    M["lb_J2.5x"] = replace(lb, name="lb_J2.5x", J=lb.J * 2.5)
    M["lb_b0.5x"] = replace(lb, name="lb_b0.5x", b=lb.b * 0.5)
    return M


def run(x_noise, seed=5):
    t, sc = scenarios()
    M = members()
    rows = [(si, mn, ln) for si in range(len(sc)) for mn in M for ln in ("V294", "A1017")]
    B = len(rows)
    fa = np.array([1011 if r[2] == "V294" else 1017 for r in rows])
    lane = MyLane(B, fa, 567)
    v = np.array([sc[r[0]][1] for r in rows])
    ar = {k: np.zeros(B) for k in ("J", "b", "k", "Fc", "Fs", "sat")}
    for i, (si, mn, ln) in enumerate(rows):
        a = M[mn].arrays_at(np.array([v[i]]))
        for k in ar:
            ar[k][i] = a[k][0]
    J, bb, kk, Fc, Fs, sat = (ar[k] for k in ("J", "b", "k", "Fc", "Fs", "sat"))
    NF = len(t)
    des = np.array([sc[r[0]][3] for r in rows]) / np.maximum(v[:, None], 0.1) ** 2      # desired curvature
    # road torque: constant + 0.2-3 Hz band noise; the same draw for every row of a scenario (paired)
    rng = np.random.default_rng(seed)
    bsos = signal.butter(2, [0.2 / 500, 3.0 / 500], btype="band", output="sos")
    dscen = {}
    for si, s in enumerate(sc):
        if s[5] > 0:
            nz = signal.sosfilt(bsos, rng.normal(size=int(SECS * 1000)))
            dscen[si] = s[4] + s[5] * nz / nz.std()
        else:
            dscen[si] = np.full(int(SECS * 1000), s[4])
    D = np.array([dscen[r[0]] for r in rows])
    xn = np.random.default_rng(seed + 1).normal(0.0, 1.0, (len(sc), int(SECS * 1000)))
    XN = np.array([xn[r[0]] for r in rows]) * x_noise
    fork = H.ForkPort(B, H.route()["toggles"])
    th = np.zeros(B)
    om = np.zeros(B)
    hist = np.zeros((B, 3))
    hp = 0
    Tbuf = np.zeros((B, 3))
    tp = 0
    last_tq = np.zeros(B)
    steer_lim = np.zeros(B, bool)
    qcmd = np.zeros((B, NF + 4))
    sp = np.zeros(B, np.int64)
    rec = {k: np.zeros((B, NF)) for k in ("ang", "rate", "T", "la_act", "la_des", "cmd", "alpha", "slew")}
    om_prev = om.copy()
    nsub = 5
    h = 1e-3 / nsub
    t0 = time.time()
    for n in range(NF * 10):
        k = n // 10
        if n % 10 == 0:
            ang_q = np.round(th / 0.1) * 0.1
            r = fork.step(np.ones(B, bool), v, ang_q, np.zeros(B, bool), np.zeros(B), np.zeros(B), des[:, k],
                          np.full(B, 0.426), np.zeros(B), steer_lim)
            tq = r["torque"]
            lim, can = H.honda_limiter(tq, last_tq)
            rec["slew"][:, k] = np.abs(tq - lim) > 1e-9
            steer_lim = np.abs(tq - lim) > 1e-2
            last_tq = lim
            qcmd[:, k] = can
            rec["la_act"][:, k] = r["la_act"]
            rec["la_des"][:, k] = r["la_des"]
            rec["ang"][:, k] = ang_q
        if n >= 22 and (n - 22) % 10 == 0:
            sp = demand(qcmd[:, (n - 22) // 10])
        # sensor (rate former, 3 ms window) + lane
        xr = 8.0 * (th - hist[:, hp]) / 3e-3 + XN[:, n]
        x = np.clip(np.round(xr), -12000, 12000).astype(np.int64)
        T, _ = lane.tick(-x, sp)
        Tbuf[:, tp] = T
        tp = (tp + 1) % 3
        u = -Tbuf[:, tp] + D[:, n]
        hist[:, hp] = th
        hp = (hp + 1) % 3
        # plant: 5 sub-steps, Karnopp
        for _ in range(nsub):
            fnet = u - kk * sat * np.tanh(th / sat) - bb * om
            stuck = (om == 0.0) & (np.abs(fnet) <= Fs)
            fdir = np.where(om != 0.0, np.sign(om), np.sign(fnet))
            om_new = om + np.where(stuck, 0.0, (fnet - Fc * fdir) / J) * h
            om_new[stuck | ((om != 0.0) & (np.sign(om_new) != np.sign(om)))] = 0.0
            th = th + 0.5 * (om + om_new) * h
            om = om_new
        if n % 10 == 9:
            rec["rate"][:, k] = x / 8.0
            rec["T"][:, k] = T
            rec["cmd"][:, k] = qcmd[:, k]
            rec["alpha"][:, k] = (om - om_prev) / 0.01
            om_prev = om.copy()
    return t, sc, rows, rec, lane, time.time() - t0


def bp(x, lo, hi, fs=100.0):
    sos = signal.butter(2, [lo / (fs / 2), hi / (fs / 2)], btype="band", output="sos")
    return signal.sosfiltfilt(sos, x)


def jumps(rate, ang, fs=100.0, thr=0.25, min_dwell=0.2):
    """dwell-then-jump: dwells = runs of |rate| < thr of >= min_dwell s; jump = the angle change between consecutive dwells."""
    still = np.abs(rate) < thr
    runs = []
    i = 0
    n = len(rate)
    while i < n:
        if still[i]:
            j = i
            while j < n and still[j]:
                j += 1
            if (j - i) / fs >= min_dwell:
                runs.append((i, j))
            i = j
        else:
            i += 1
    amps = [abs(ang[runs[q + 1][0]] - ang[runs[q][1] - 1]) for q in range(len(runs) - 1)]
    return len(runs), (float(np.mean(amps)) if amps else 0.0), (float(np.max(amps)) if amps else 0.0)


def metrics(t, sc, rows, rec):
    out = {}
    for i, (si, mn, ln) in enumerate(rows):
        kind, v, par = sc[si][0], sc[si][1], sc[si][2]
        r, la, ld, al = rec["rate"][i], rec["la_act"][i], rec["la_des"][i], rec["alpha"][i]
        m = {}
        if kind == "TURN":
            hold = (t > 5.0) & (t < 12.0)
            ramp = ((t > 2.5) & (t < 5.0)) | ((t > 11.5) & (t < 14.5))
            b16 = bp(r, 1.6, 3.0)
            m["hard16_hold"] = float(np.sqrt(np.mean(b16[hold] ** 2)))
            m["hard16_ramps"] = float(np.sqrt(np.mean(b16[ramp] ** 2)))
            m["osc05_5_hold"] = float(np.sqrt(np.mean(bp(r, 0.5, 5.0)[hold] ** 2)))
            m["overshoot"] = float((np.max(np.abs(la[(t > 3) & (t < 12)])) - par) / par)
            m["hold_ratio"] = float(np.median(la[hold]) / par)
            m["peak_alpha"] = float(np.max(np.abs(al[(t > 2.5) & (t < 16)])))
            m["post_osc"] = float(np.sqrt(np.mean(bp(r, 0.5, 5.0)[(t > 15) & (t < 29)] ** 2)))
            m["jumps"] = jumps(r[(t > 3) & (t < 16)], rec["ang"][i][(t > 3) & (t < 16)])
        elif kind == "CENTRE":
            w = t > 5.0
            m["rate_0.3_5"] = float(np.sqrt(np.mean(bp(r, 0.3, 5.0)[w] ** 2)))
            m["rate_1.6_3"] = float(np.sqrt(np.mean(bp(r, 1.6, 3.0)[w] ** 2)))
            m["rate_3_8"] = float(np.sqrt(np.mean(bp(r, 3.0, 8.0)[w] ** 2)))
            f, P = signal.welch(r[w] - r[w].mean(), fs=100.0, nperseg=1024)
            mm = (f > 0.2) & (f < 8)
            m["f_peak"] = float(f[mm][np.argmax(P[mm])])
            m["jumps"] = jumps(r[w], rec["ang"][i][w])
            m["la_err_rms"] = float(np.sqrt(np.mean((la[w] - ld[w]) ** 2)))
            m["peak_alpha"] = float(np.max(np.abs(al[w])))
        else:
            w = t > 5.0
            f0 = par
            X = np.vstack([np.sin(2 * np.pi * f0 * t[w]), np.cos(2 * np.pi * f0 * t[w])]).T
            cd, *_ = np.linalg.lstsq(X, ld[w], rcond=None)
            ca, *_ = np.linalg.lstsq(X, la[w], rcond=None)
            G = complex(ca[0], ca[1]) / complex(cd[0], cd[1])
            m["gain"] = float(abs(G))
            m["phase"] = float(np.degrees(np.angle(G)))
            res = la[w] - X @ ca
            m["resid_1_5"] = float(np.sqrt(np.mean(bp(res, 1.0, 5.0) ** 2)))
            m["rate_1.6_3"] = float(np.sqrt(np.mean(bp(r, 1.6, 3.0)[w] ** 2)))
            m["peak_alpha"] = float(np.max(np.abs(al[w])))
        m["slew_share"] = float(np.mean(rec["slew"][i]))
        m["maxT"] = float(np.max(np.abs(rec["T"][i])))
        out[(si, mn, ln)] = m
    return out


def main():
    lines = []
    pr = lambda *a: (print(*a, flush=True), lines.append(" ".join(str(x) for x in a)))  # noqa: E731
    allres = {}
    for xn in (0.0, 1.93):
        t, sc, rows, rec, lane, rt = run(xn)
        res = metrics(t, sc, rows, rec)
        pr("\n######## x_noise %.2f  (%d rows, %.0f s)  max |r26| V294 %d A1017 %d ; fb-clamp binds V294 %d A1017 %d ; "
           "P binds V294 %d A1017 %d ; max|a*s| V294 %.3e A1017 %.3e" % (
               xn, len(rows), rt, lane.max_r26[0::2].max(), lane.max_r26[1::2].max(), lane.n_Cbind[0::2].sum(),
               lane.n_Cbind[1::2].sum(), lane.n_Pbind[0::2].sum(), lane.n_Pbind[1::2].sum(), lane.max_as[0::2].max(),
               lane.max_as[1::2].max()))
        Mn = sorted(set(r[1] for r in rows), key=lambda s: [r[1] for r in rows].index(s))
        for si, s in enumerate(sc):
            kind, v, par = s[0], s[1], s[2]
            pr("--- %s v %.1f %s" % (kind, v, ("a %.1f" % par) if kind == "TURN" else (("f %.1f Hz" % par) if kind == "SLALOM" else "d 25+10 T")))
            for mn in Mn:
                a, b = res[(si, mn, "V294")], res[(si, mn, "A1017")]
                keys = [k for k in a if k != "jumps"]
                txt = "  ".join("%s %s/%s" % (k, _f(a[k]), _f(b[k])) for k in keys)
                if "jumps" in a:
                    txt += "  jumps(n,mean,max) %s/%s" % (tuple(round(x, 2) for x in a["jumps"]), tuple(round(x, 2) for x in b["jumps"]))
                pr("   %-9s V294/A1017: %s" % (mn, txt))
        allres[xn] = {"|".join(str(x) for x in k): v for k, v in res.items()}
        # summary ratios
        for kind, keys in (("TURN", ("hard16_hold", "hard16_ramps", "osc05_5_hold", "post_osc", "peak_alpha")),
                           ("CENTRE", ("rate_0.3_5", "rate_1.6_3", "rate_3_8", "peak_alpha", "la_err_rms")),
                           ("SLALOM", ("gain", "resid_1_5", "rate_1.6_3", "peak_alpha"))):
            for kk in keys:
                rr = [res[(si, mn, "A1017")][kk] / res[(si, mn, "V294")][kk] for si, s in enumerate(sc) for mn in Mn
                      if s[0] == kind and res[(si, mn, "V294")][kk] > 1e-9]
                if rr:
                    pr("SUMMARY xn %.2f %-6s %-13s A/V ratio: min %.3f median %.3f max %.3f (n %d)" % (xn, kind, kk, min(rr), np.median(rr), max(rr), len(rr)))
            if kind != "SLALOM":
                ja = [(res[(si, mn, "V294")]["jumps"], res[(si, mn, "A1017")]["jumps"]) for si, s in enumerate(sc) for mn in Mn if s[0] == kind]
                pr("SUMMARY xn %.2f %-6s jumps: V294 n %d mean-amp %.3f deg | A1017 n %d mean-amp %.3f deg ; per-cell amp ratio max %.3f" % (
                    xn, kind, sum(x[0][0] for x in ja), np.mean([x[0][1] for x in ja]), sum(x[1][0] for x in ja),
                    np.mean([x[1][1] for x in ja]), max([x[1][1] / x[0][1] for x in ja if x[0][1] > 0.01], default=np.nan)))
    json.dump({str(k): v for k, v in allres.items()}, open(os.path.join(HERE, "s7_closedloop.json"), "w"))
    open(os.path.join(HERE, "s7_closedloop_out.txt"), "w").write("\n".join(lines) + "\n")


def _f(x):
    return ("%.3f" % x) if abs(x) < 100 else ("%.0f" % x)


if __name__ == "__main__":
    main()
