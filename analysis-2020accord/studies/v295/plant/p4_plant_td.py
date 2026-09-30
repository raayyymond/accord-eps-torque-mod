# -*- coding: utf-8 -*-
"""p4_plant_td.py -- TASK 1, time domain: J, b, k, F per speed band by OLS and by instrumental variables.
python p4_plant_td.py -> p4_plant_td_out.txt, _scratch/p4_td.json

EQUATION (per band, hands-off laterally engaged, MOVING frames):
    u(t - tau) = J*al + b*om + k*th + F*tanh(om/0.5) + c_roll*roll + c_run      (T counts; th deg, om deg/s, al deg/s^2)
  u = -T_live, the delivered torque INCLUDING the trim (so this is the OPEN plant).  tau is scanned 0..20 ms using the
  1 kHz march (u built as 10-tick block means at 1 ms offsets).  c_run = one constant per contiguous hands-off stretch
  of the band (angle-sensor offset, crown) removed by within-run demeaning of every column (Frisch-Waugh), instruments
  included; roll = liveParameters.roll (bank).  [A first version used 5 s block constants: they ABSORBED the Coulomb
  term wherever the rate keeps one sign for a whole block (F came out negative) -- superseded.]
  Signals are zero-phase low-passed at 8 Hz (4th-order Butterworth, filtfilt over the WHOLE route) before use; al is the
  central difference of the filtered om.  The same filter on every column keeps the linear equation exact; sgn(om) is
  computed from the filtered om.  ALL hands-off frames are used (a first version kept only |om| > 2 deg/s and lost 90 %
  of the data at speed); during stick the Coulomb term is whatever balances, so the stick frames carry an error bounded
  by the static friction -- the output-error fit (p5) models stick-slip properly and is the estimate of record.
ESTIMATORS
  OLS    plain least squares (biased: om/th/al are driven by the road torque d that is in the equation error, and the
         trim feeds al back into u)
  IV-ff  2SLS; instruments = a bank of the FEEDFORWARD torque u_ff = -T_null (command-only) filtered and delayed:
         u_ff, LP 0.5/1.5/4 Hz, BP 1-3 Hz, first and second differences of LP4, each at delays 0/5/10 frames, plus
         sgn(om_hat) (om_hat = the first-stage projection of om).  Exogenous to the INNER loop; the fork's outer loop
         closes on th with ~60 ms, so a SLOW road disturbance still leaks in (G3a quantifies it by simulation).
  IV-sp  2SLS; instruments = the same bank built from the planner setpoint desiredLateralAccel (exogenous to both
         loops, but low bandwidth -- identifies k and b, J only weakly).
CIs: block bootstrap over the 5 s blocks, 300 resamples, the estimator re-run each time.
"""
import json
import os
import sys

import numpy as np
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plib as P  # noqa: E402

OUT = []
HERE = os.path.dirname(os.path.abspath(__file__))
FS = 100.0
OMIN = 0.5
BLOCK_S = 5.0
FLP = 15.0


def pr(s=""):
    print(s, flush=True)
    OUT.append(str(s))


def lpf(x, fc, order=4):
    sos = signal.butter(order, fc / (FS / 2), output="sos")
    return signal.sosfiltfilt(sos, np.nan_to_num(x))


def bpf(x, lo, hi):
    sos = signal.butter(2, [lo / (FS / 2), hi / (FS / 2)], "band", output="sos")
    return signal.sosfiltfilt(sos, np.nan_to_num(x))


def u_at_delay(d, tau_ms):
    """u(t - tau): 10-tick block means of -T1k_live centred tau ms EARLIER than each frame."""
    return -P.block_mean_1k(d["T1k_live"], len(d["t"]), d["dms"] - int(tau_ms))


def instr_bank(z):
    cols = []
    zl4 = lpf(z, 4.0)
    base = [z, lpf(z, 0.5), lpf(z, 1.5), zl4, bpf(z, 1.0, 3.0), np.gradient(zl4) * FS, np.gradient(np.gradient(zl4)) * FS * FS]
    for sh in (0, 5, 10):
        for c in base:
            cols.append(np.r_[np.full(sh, c[0]), c[:len(c) - sh]])
    return np.column_stack(cols)


def demean_blocks(A, blk):
    A = np.array(A, float, copy=True)
    if A.ndim == 1:
        A = A[:, None]
    u, inv = np.unique(blk, return_inverse=True)
    for j in range(A.shape[1]):
        s = np.bincount(inv, A[:, j]) / np.bincount(inv)
        A[:, j] -= s[inv]
    return A


def tsls(y, X, Z):
    """2SLS: beta = (X' Pz X)^-1 X' Pz y, all columns already demeaned."""
    Q, _ = np.linalg.qr(Z)
    Xh = Q @ (Q.T @ X)
    return np.linalg.lstsq(Xh, y, rcond=None)[0]


def estimate(y, X, Z, blk, est):
    if est == "OLS":
        return np.linalg.lstsq(X, y, rcond=None)[0]
    return tsls(y, X, Z)


def prep(d, mask, tau_ms, zsrc):
    om = lpf(d["om"], FLP)
    th = lpf(d["th"], FLP)
    al = np.gradient(om) * FS
    u = lpf(u_at_delay(d, tau_ms), FLP)
    sg = np.tanh(om / OMIN)
    roll = np.nan_to_num(d["lpar_roll"])
    idx = np.flatnonzero(mask)
    run_id = np.zeros(len(d["t"]), int)
    for r, (a, b) in enumerate(P.runs(mask)):
        run_id[a:b] = r
    blk = np.floor(d["tr"][idx] / BLOCK_S).astype(int)
    X = np.column_stack([al, om, th, sg, roll])[idx]
    y = u[idx]
    Z = {nm: np.column_stack([instr_bank(z), roll])[idx] for nm, z in zsrc.items()}
    return y, X, Z, blk, idx, run_id[idx]


def run_band(d, mask, tau_ms, zsrc, ests=("OLS", "IV-ff", "IV-sp"), nboot=300, seed=0):
    y, X, Z, blk, idx, rid = prep(d, mask, tau_ms, zsrc)
    if len(y) < 500:
        return None
    yd = demean_blocks(y, rid)[:, 0]
    Xd = demean_blocks(X, rid)
    Zd = {k: demean_blocks(v, rid) for k, v in Z.items()}
    out = {}
    ub = np.unique(blk)
    groups = [np.flatnonzero(blk == u) for u in ub]
    rng = np.random.default_rng(seed)
    for est in ests:
        if est == "OLS":
            Zu = None
        else:
            Zb = Zd["ff" if est == "IV-ff" else "sp"]
            # first stage for sgn(om): project om on the bank, use sgn(om_hat) as the friction instrument
            Q, _ = np.linalg.qr(Zb)
            omh = Q @ (Q.T @ Xd[:, 1])
            Zu = np.column_stack([Zb, np.sign(omh)])
        b0 = estimate(yd, Xd, Zu, blk, est)
        resid = yd - Xd @ b0
        bs = []
        for _ in range(nboot):
            pick = rng.integers(0, len(groups), len(groups))
            ii = np.concatenate([groups[p] for p in pick])
            try:
                bs.append(estimate(yd[ii], Xd[ii], None if Zu is None else Zu[ii], blk[ii], est))
            except Exception:
                pass
        bs = np.array(bs) if bs else np.array([b0])
        J, b, k, F = b0[:4]
        fn = np.sqrt(k / J) / (2 * np.pi) if (k > 0 and J > 0) else np.nan
        ze = b / (2 * np.sqrt(k * J)) if (k > 0 and J > 0) else np.nan
        mb = []
        for r in bs:
            if r[0] > 0 and r[2] > 0:
                mb.append((np.sqrt(r[2] / r[0]) / (2 * np.pi), r[1] / (2 * np.sqrt(r[2] * r[0]))))
        mb = np.array(mb) if mb else np.full((1, 2), np.nan)
        # first-stage strength: R2 of each regressor on the instruments (IV only)
        fs_r2 = None
        if Zu is not None:
            Q, _ = np.linalg.qr(Zu)
            fs_r2 = [float(1 - np.sum((Xd[:, j] - Q @ (Q.T @ Xd[:, j])) ** 2) / np.sum(Xd[:, j] ** 2)) for j in range(4)]
        out_roll = float(b0[4])
        out[est] = dict(J=J, b=b, k=k, F=F, c_roll=float(b0[4]), fn=fn, zeta=ze, lo=np.percentile(bs, 2.5, axis=0).tolist(),
                        hi=np.percentile(bs, 97.5, axis=0).tolist(), fn_ci=[float(np.nanpercentile(mb[:, 0], 2.5)),
                                                                         float(np.nanpercentile(mb[:, 0], 97.5))],
                        zeta_ci=[float(np.nanpercentile(mb[:, 1], 2.5)), float(np.nanpercentile(mb[:, 1], 97.5))],
                        r2=float(1 - np.sum(resid ** 2) / np.sum(yd ** 2)), resid_rms=float(np.sqrt(np.mean(resid ** 2))),
                        n=int(len(yd)), seconds=len(yd) / FS, fs_r2=fs_r2, nblocks=len(groups))
    return out


def main():
    d = P.load()
    zsrc = dict(ff=d["u_ff"], sp=d["ctl_la_des"])
    # 1. the delay scan on the pooled moving hands-off frames (OLS residual variance and IV-ff J)
    pr("TAU SCAN (all bands pooled, hands-off, v > 3 m/s): tau ms -> OLS R2, OLS J, IV-ff J")
    allm = d["ho"] & (d["v"] > 3.0)
    scan = []
    for tau in (0, 5, 10, 15, 20, 25, 30, 40, 50, 60):
        r = run_band(d, allm, tau, zsrc, ests=("OLS", "IV-ff"), nboot=0)
        scan.append((tau, r["OLS"]["r2"], r["OLS"]["J"], r["IV-ff"]["J"], r["IV-ff"]["r2"]))
        pr("  tau %2d ms: OLS R2 %.4f J %.4f | IV-ff J %.4f R2 %.4f" % scan[-1])
    tau_best = max(scan, key=lambda s: s[1])[0]
    pr("  -> tau used: %d ms (max OLS R2)" % tau_best)
    res = {}
    for nm, lo, hi in (("all>3", 3.0, 99.0),) + P.BANDS:
        mask = d["ho"] & P.band_mask(d, lo, hi)
        r = run_band(d, mask, tau_best, zsrc)
        if r is None:
            pr("band %s: too few moving frames" % nm)
            continue
        res[nm] = r
        pr("")
        pr("BAND %s m/s  (%.0f s hands-off engaged, %d bootstrap blocks of 5 s)" % (nm, r["OLS"]["seconds"], r["OLS"]["nblocks"]))
        pr("  %-6s %22s %20s %20s %20s | %6s %6s | %5s %5s | %s" % ("est", "J T/(deg/s2)", "b T/(deg/s)", "k T/deg",
                                                               "F T", "f_n", "zeta", "R2", "rms", "1st-stage R2 al/om/th/sgn"))
        for est, e in r.items():
            pr("  %-6s %7.4f [%6.4f,%6.4f] %6.2f [%5.2f,%5.2f] %6.2f [%5.2f,%5.2f] %6.1f [%5.1f,%5.1f] | %6.2f %6.3f | %5.3f %5.1f | %s" % (
                est, e["J"], e["lo"][0], e["hi"][0], e["b"], e["lo"][1], e["hi"][1], e["k"], e["lo"][2], e["hi"][2],
                e["F"], e["lo"][3], e["hi"][3], e["fn"], e["zeta"], e["r2"], e["resid_rms"],
                "" if e["fs_r2"] is None else " ".join("%.2f" % v for v in e["fs_r2"])))
            pr("  %-6s   f_n CI [%.2f, %.2f] Hz   zeta CI [%.3f, %.3f]" % ("", e["fn_ci"][0], e["fn_ci"][1], e["zeta_ci"][0],
                                                                        e["zeta_ci"][1]))
    json.dump(dict(tau_ms=tau_best, scan=scan, bands=res), open(os.path.join(HERE, "_scratch", "p4_td.json"), "w"), indent=1,
              default=float)
    open(os.path.join(HERE, "p4_plant_td_out.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
