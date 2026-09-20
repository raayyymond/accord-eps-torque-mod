# -*- coding: utf-8 -*-
"""D5 -- the BINDING CONSTRAINT, measured: how 1.8-3.5 Hz steering-rate RMS scales with loop gain.

Pure measurement from flown data.  10 s blocks, laterally engaged, hands off the wheel, binned by
(speed x median |steering angle|) exactly as the study's own shake table, then:

  (i)  the WITHIN-EPS dose on the V282 firmware: six routes spanning kp/LAF 0.150 -> 0.379 (2.5x).
  (ii) the torque family, which spans kp/LAF 0.050 / 0.0607 / 0.0714 -- but every step of that is
       confounded with a rate-loop / observer / notch change, so it is reported and NOT regressed.
  (iii) a within-route control: does a route's own shake track its own instantaneous |P-term|?
        (the only dose that is free of route, road and fork confounds)

Also reports the command's own 1.8-3.5 Hz content, so a rise in wheel shake can be attributed to
the controller rather than to the road.
"""
import json
import numpy as np
from scipy import signal
import dlib as D

FS = 100.0
BLK = int(10 * FS)
VB = [(8, 15), (15, 22), (22, 99)]
AB = [(0, 5), (5, 15), (15, 90)]
SOS = signal.butter(4, [1.8, 3.5], btype="band", fs=FS, output="sos")


def blocks(S, want_press=False):
    m = S["active"] & (~S["pressed"] if not want_press else S["pressed"])
    out = []
    for a, b in D.V.runs(m, S["t"], min_s=10.0):
        for i in range(a, b - BLK + 1, BLK):
            sl = slice(i, i + BLK)
            v = float(np.median(S["v"][sl]))
            ang = float(np.median(np.abs(np.nan_to_num(S["sa"][sl]))))
            sr = np.nan_to_num(S["sr"][sl])
            out_ = np.nan_to_num(S["out"][sl])
            if not np.isfinite(v) or v < 8:
                continue
            out.append(dict(v=v, ang=ang,
                            shake=float(np.sqrt(np.mean(signal.sosfiltfilt(SOS, sr) ** 2))),
                            cmd_hf=float(np.sqrt(np.mean(signal.sosfiltfilt(SOS, out_) ** 2))),
                            p_rms=float(np.sqrt(np.mean(np.nan_to_num(S["p"][sl]) ** 2))),
                            sr_rms=float(np.sqrt(np.mean(sr ** 2)))))
    return out


def cell(b):
    for i, (lo, hi) in enumerate(VB):
        if lo <= b["v"] < hi:
            vi = i
            break
    else:
        return None
    for j, (lo, hi) in enumerate(AB):
        if lo <= b["ang"] < hi:
            return (vi, j)
    return None


def main():
    per = {}
    for rt, cfg in D.ROUTES.items():
        S = D.load(rt)
        bs = blocks(S)
        cells = {}
        for b in bs:
            c = cell(b)
            if c is None:
                continue
            cells.setdefault(c, []).append(b)
        per[rt] = {f"{c[0]}_{c[1]}": dict(n=len(v),
                                          shake=float(np.median([x["shake"] for x in v])),
                                          cmd=float(np.median([x["cmd_hf"] for x in v])))
                   for c, v in cells.items()}
        del S
    json.dump(per, open(D.OUT / "d5_shake.json", "w"), indent=1)

    names = [f"{VB[i][0]}-{VB[i][1]} m/s, {AB[j][0]}-{AB[j][1]} deg" for i in range(3) for j in range(3)]
    keys = [f"{i}_{j}" for i in range(3) for j in range(3)]
    print("1.8-3.5 Hz STEERING-RATE RMS (deg/s), median of 10 s blocks, hands off, engaged\n")
    print(f"{'route':22s} {'grp':8s} {'kp/LAF':>7s} " + " ".join(f"{k:>11s}" for k in keys))
    for rt, cfg in D.ROUTES.items():
        row = per[rt]
        print(f"{rt:22s} {cfg['g']:8s} {cfg['kp']/cfg['laf']:7.4f} "
              + " ".join((f"{row[k]['shake']:6.2f}({row[k]['n']:3d})" if k in row else f"{'-':>11s}")
                         for k in keys))
    print("\n  cells: " + " | ".join(f"{k}={n}" for k, n in zip(keys, names)))

    # ---- (i) the within-EPS dose on the V282 firmware ----------------------------------------
    print("\n(i) WITHIN-EPS DOSE, V282 firmware only: 6 routes, kp/LAF 0.150 -> 0.379 (2.5x)")
    ref = [r for r, c in D.ROUTES.items() if c["g"] == "V282"]
    dose = [r for r, c in D.ROUTES.items() if c["g"].startswith("V282")]
    base = {}
    for k in keys:
        vals = [per[r][k]["shake"] for r in ref if k in per[r]]
        if vals:
            base[k] = float(np.median(vals))
    print(f"    {'route':22s} {'kp/LAF':>7s} {'cells':>5s} {'ratio to V282 (geo mean)':>26s}  per-cell ratios")
    xs, ys = [], []
    for r in dose:
        rr = [per[r][k]["shake"] / base[k] for k in keys if k in per[r] and k in base
              and per[r][k]["n"] >= 3]
        if not rr:
            continue
        gm = float(np.exp(np.mean(np.log(rr))))
        kpl = D.ROUTES[r]["kp"] / D.ROUTES[r]["laf"]
        print(f"    {r:22s} {kpl:7.4f} {len(rr):5d} {gm:26.3f}  "
              + " ".join(f"{x:.2f}" for x in rr))
        for x in rr:
            xs.append(np.log(kpl)); ys.append(np.log(x))
    if len(xs) > 3:
        A = np.polyfit(xs, ys, 1)
        n = len(xs)
        yhat = np.polyval(A, xs)
        se = np.sqrt(np.sum((np.array(ys) - yhat) ** 2) / (n - 2) /
                     np.sum((np.array(xs) - np.mean(xs)) ** 2))
        print(f"\n    log-log slope d(log shake)/d(log kp/LAF) = {A[0]:+.3f} +/- {se:.3f}"
              f"  (n={n} cell-route pairs, NOT independent: 3 routes)")
        print(f"    => a 2x rise in kp/LAF multiplies the 1.8-3.5 Hz shake by "
              f"{2**A[0]:.2f} [{2**(A[0]-1.96*se):.2f}, {2**(A[0]+1.96*se):.2f}] on THIS EPS")

    # ---- (ii) the torque family --------------------------------------------------------------
    print("\n(ii) TORQUE family (every kp step is confounded with a rate-loop / observer change)")
    tref = [r for r, c in D.ROUTES.items() if c["g"] == "T64"]
    tb = {}
    for k in keys:
        vals = [per[r][k]["shake"] for r in tref if k in per[r]]
        if vals:
            tb[k] = float(np.median(vals))
    print(f"    {'route':22s} {'grp':8s} {'kp/LAF':>7s} {'rl':>7s} {'dob':>5s} {'ratio to T64':>13s}")
    for r, c in D.ROUTES.items():
        if not c["g"].startswith("T"):
            continue
        rr = [per[r][k]["shake"] / tb[k] for k in keys if k in per[r] and k in tb and per[r][k]["n"] >= 3]
        if not rr:
            continue
        print(f"    {r:22s} {c['g']:8s} {c['kp']/c['laf']:7.4f} {c['rl']:7.4f} {c['dob']:5.2f} "
              f"{float(np.exp(np.mean(np.log(rr)))):13.3f}")

    # ---- (iii) within-route control ----------------------------------------------------------
    print("\n(iii) WITHIN-ROUTE control: does a block's own shake track its own P-term RMS?")
    print("      (free of route / road / fork confounds; a positive slope means P feeds the band)")
    print(f"    {'route':22s} {'grp':8s} {'n':>4s} {'slope':>7s} {'r':>6s}   partial on speed+angle")
    for rt, cfg in D.ROUTES.items():
        S = D.load(rt)
        bs = [b for b in blocks(S) if b["p_rms"] > 1e-4 and b["shake"] > 1e-4]
        del S
        if len(bs) < 30:
            print(f"    {rt:22s} {cfg['g']:8s} {len(bs):4d}   (too few)")
            continue
        X = np.column_stack([np.log([b["p_rms"] for b in bs]),
                             np.log([b["v"] for b in bs]),
                             np.log([max(b["ang"], 0.05) for b in bs]),
                             np.ones(len(bs))])
        y = np.log([b["shake"] for b in bs])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        r = float(np.corrcoef(np.log([b["p_rms"] for b in bs]), y)[0, 1])
        print(f"    {rt:22s} {cfg['g']:8s} {len(bs):4d} {beta[0]:+7.3f} {r:+6.2f}")


if __name__ == "__main__":
    main()
