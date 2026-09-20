# -*- coding: utf-8 -*-
"""D6 -- the feedback transfer K(jw) AT THE SHAKE FREQUENCY, measured, and split by term.

The model reference carries no power at 1.8-3.5 Hz (d2: coherence 0.1-0.35 there), so in that band
the command is almost entirely a response to the measured wheel:

      U(jw) ~= -K(jw) * M(jw)     =>     K = -S_UM / S_MM     (H1, M as input)

That is a MEASUREMENT of the total feedback transfer where the operator's binding constraint lives,
and it needs no plant model at all.  Because p, i and f are logged separately it also splits:

      K_P = -S_Mp / S_MM      the SteerKP path (the dose's own lever)
      K_F = -S_Mf / S_MM      everything the fork puts in the feedforward slot: the rate loop,
                              the observer, the hysteresis, and the plant FF's response to r

Positive controls: (1) K_P must reproduce SteerKP * |notch| to within the r-driven bias, which is
independently known; (2) the coherence U<-M is reported so the reader can see how much of U is not
explained by M.  A bias from the r-driven part of U can only make |K| read HIGH.

Then: the measured |K| at 2.5 Hz is a real flown DOSE (the nine torque routes span rate loop
0 / 0.0006 / 0.001 and observer off / 0.6 Hz), so shake is regressed on it.
"""
import json
import numpy as np
from scipy import signal
import dlib as D
from d1_ident import k_tot, mode_hz

FS = 100.0
NPS = 512          # 5.12 s blocks: plenty of resolution at 1.8-3.5 Hz, many averages
SHK = (1.8, 3.5)


def xfer(S, mask, num_key, min_s=20.0):
    acc_mm = acc_mx = None
    fr = None
    acc_xx = None
    sec = 0.0
    for a, b in D.V.runs(mask, S["t"], min_s=min_s):
        if b - a < NPS:
            continue
        M = np.nan_to_num(S["la_act"][a:b])
        if num_key == "U":
            X = (np.nan_to_num(S["p"][a:b]) + np.nan_to_num(S["i"][a:b])
                 + np.nan_to_num(S["f"][a:b]))
        else:
            X = np.nan_to_num(S[num_key][a:b])
        M, X = M - M.mean(), X - X.mean()
        kw = dict(fs=FS, nperseg=NPS, noverlap=NPS // 2)
        f, mm = signal.welch(M, **kw)
        _, mx = signal.csd(M, X, **kw)
        _, xx = signal.welch(X, **kw)
        w = b - a
        acc_mm = mm * w if acc_mm is None else acc_mm + mm * w
        acc_mx = mx * w if acc_mx is None else acc_mx + mx * w
        acc_xx = xx * w if acc_xx is None else acc_xx + xx * w
        fr = f
        sec += w / FS
    if fr is None:
        return None
    K = -acc_mx / np.maximum(acc_mm, 1e-30)
    coh = np.abs(acc_mx) ** 2 / np.maximum(acc_mm * acc_xx, 1e-30)
    return fr, K, coh, sec


def band(f, X, f1, f2, power_w=None):
    m = (f >= f1) & (f < f2)
    w = power_w[m] if power_w is not None else np.ones(m.sum())
    return (float(np.average(np.abs(X[m]), weights=w)),
            float(np.degrees(np.angle(np.sum(X[m] * w)))))


def main():
    shake = json.load(open(D.OUT / "d5_shake.json"))
    keys = [f"{i}_{j}" for i in range(3) for j in range(3)]
    print("MEASURED feedback transfer K = -S_UM/S_MM in the shake band, >=15 m/s, hands off\n")
    print(f"{'route':22s} {'grp':8s} {'rl':>7s} {'dob':>4s} {'sec':>5s} | "
          f"{'|K|1.8-3.5':>10s} {'ph':>6s} {'coh':>5s} | {'|K_P|':>6s} {'ph':>6s} | "
          f"{'|K_F|':>6s} {'ph':>6s} | {'|K|model':>9s} {'ph':>6s} | {'P/K':>5s}")
    rows = []
    for rt, cfg in D.ROUTES.items():
        S = D.load(rt)
        m = D.V.usable(S, 15.0)
        rU = xfer(S, m, "U")
        rP = xfer(S, m, "p")
        rF = xfer(S, m, "f")
        v = float(np.median(S["v"][m])) if m.sum() else float("nan")
        km = D.k_m_measured(S, m)
        del S
        if rU is None:
            print(f"{rt:22s} {cfg['g']:8s}  (no runs)")
            continue
        f, K, coh, sec = rU
        _, KP, _, _ = rP
        _, KF, _, _ = rF
        w = None
        aK, pK = band(f, K, *SHK)
        aP, pP = band(f, KP, *SHK)
        aF, pF = band(f, KF, *SHK)
        ck = float(np.mean(coh[(f >= SHK[0]) & (f < SHK[1])]))
        fm = np.linspace(*SHK, 40)
        Km = k_tot(fm, cfg, v, km)
        am, pm = float(np.mean(np.abs(Km))), float(np.degrees(np.angle(np.sum(Km))))
        print(f"{rt:22s} {cfg['g']:8s} {cfg['rl']:7.4f} {cfg['dob']:4.1f} {sec:5.0f} | "
              f"{aK:10.3f} {pK:6.1f} {ck:5.2f} | {aP:6.3f} {pP:6.1f} | {aF:6.3f} {pF:6.1f} | "
              f"{am:9.3f} {pm:6.1f} | {aP/max(aK,1e-9):5.2f}")
        sh = [shake[rt][k]["shake"] for k in keys if k in shake[rt] and shake[rt][k]["n"] >= 3]
        rows.append(dict(rt=rt, g=cfg["g"], K=aK, phK=pK, KP=aP, KF=aF, Kmod=am, phmod=pm,
                         rl=cfg["rl"], dob=cfg["dob"], kpl=cfg["kp"] / cfg["laf"],
                         shake=float(np.exp(np.mean(np.log(sh)))) if sh else float("nan"),
                         ncell=len(sh)))

    print("\nMEASURED vs MODELLED |K| in the shake band (the model's rate-loop + observer terms "
          "are the part that was BELIEF):")
    tq = [r for r in rows if r["g"].startswith("T")]
    vz = [r for r in rows if r["g"].startswith("V282")]
    for lab, rr in (("V282 EPS", vz), ("torque EPS", tq)):
        if not rr:
            continue
        rat = [r["K"] / max(r["Kmod"], 1e-9) for r in rr]
        print(f"   {lab:11s} n={len(rr)}  measured/modelled  median {np.median(rat):.2f}"
              f"  range {min(rat):.2f}-{max(rat):.2f}")

    print("\nFLOWN DOSE in shake-band loop gain: shake vs the MEASURED |K| (cell-matched geo mean)")
    print(f"{'route':22s} {'grp':8s} {'rl':>7s} {'dob':>4s} {'|K|shk':>7s} {'shake':>7s} {'cells':>5s}")
    for r in sorted(rows, key=lambda x: x["K"]):
        print(f"{r['rt']:22s} {r['g']:8s} {r['rl']:7.4f} {r['dob']:4.1f} {r['K']:7.3f} "
              f"{r['shake']:7.3f} {r['ncell']:5d}")
    for lab, rr in (("torque EPS only", tq), ("V282 EPS only", vz)):
        rr = [r for r in rr if np.isfinite(r["shake"]) and r["ncell"] >= 3]
        if len(rr) < 4:
            print(f"   {lab}: n={len(rr)}, too few to regress")
            continue
        x = np.log([r["K"] for r in rr]); y = np.log([r["shake"] for r in rr])
        A = np.polyfit(x, y, 1)
        n = len(x)
        se = np.sqrt(np.sum((y - np.polyval(A, x)) ** 2) / (n - 2) / np.sum((x - x.mean()) ** 2))
        print(f"   {lab}: d(log shake)/d(log |K|_1.8-3.5Hz) = {A[0]:+.2f} +/- {se:.2f}  (n={n} routes,"
              f" r={np.corrcoef(x,y)[0,1]:+.2f})")
    json.dump(rows, open(D.OUT / "d6_shakeloop.json", "w"), indent=1)


if __name__ == "__main__":
    main()
