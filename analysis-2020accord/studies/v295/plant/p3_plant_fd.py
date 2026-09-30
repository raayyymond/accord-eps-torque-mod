# -*- coding: utf-8 -*-
"""p3_plant_fd.py -- TASK 1, frequency domain: the OPEN plant u -> om (and u -> th) per speed band, hands-off engaged.
python p3_plant_fd.py -> p3_plant_fd_out.txt, _scratch/p3_fd.npz

u  = -T_live (T counts, + = LEFT): the delivered torque INCLUDING the trim, so u -> om is the OPEN plant.
Estimators (pooled Welch, 2.56 s Hann windows, 50 % overlap, windows inside hands-off engaged stretches, each window
  assigned to a speed band by its MEAN speed (speed spread <= 4 m/s); also split by the window's om rms (friction check)):
  DIRECT  H = S_u,om / S_u,u                         biased by feedback (the trim and the fork's outer loop)
  IV-ff   H = S_z,om / S_z,u,  z = u_ff = -T_null    the command's feedforward torque (exogenous to the INNER loop,
                                                      NOT to the fork's outer loop, which closes on th with ~60 ms)
  IV-sp   H = S_z,om / S_z,u,  z = desiredLateralAccel (the planner setpoint; exogenous to both loops, low bandwidth)
Fit (coherence-weighted, bins with coh >= 0.3, 0.3-8 Hz):  om/u = s e^{-s tau} / (J s^2 + b s + k)
  -> J, b, k, tau, f_n = sqrt(k/J)/2pi, zeta = b / (2 sqrt(k J)).  Friction is NOT in this linear model: at small
  amplitude it appears as extra b (describing function 4F/(pi*|om|)), which is why the time-domain fit (p4) carries F.
CIs: 200-resample bootstrap over the WINDOWS (window-block bootstrap), refitting each time.
"""
import os
import sys

import numpy as np
from scipy import optimize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frf as FRF  # noqa: E402
import plib as P  # noqa: E402

OUT = []
HERE = os.path.dirname(os.path.abspath(__file__))
NPER = 256
FS = 100.0


def pr(s=""):
    print(s, flush=True)
    OUT.append(str(s))


def model(f, J, b, k, tau):
    s = 1j * 2 * np.pi * f
    return s * np.exp(-s * tau) / (J * s * s + b * s + k)


def fit(f, H, w, x0=(0.2, 3.0, 15.0, 0.005)):
    def r(p):
        J, b, k, tau = np.exp(p[0]), np.exp(p[1]), np.exp(p[2]), p[3]
        e = np.log(model(f, J, b, k, tau)) - np.log(H)            # complex log: magnitude (log) + phase
        e = np.r_[e.real, np.angle(np.exp(1j * e.imag))]
        return np.r_[np.sqrt(w), np.sqrt(w)] * e
    p0 = np.r_[np.log(x0[:3]), x0[3]]
    sol = optimize.least_squares(r, p0, bounds=([-8, -8, -4, -0.02], [3, 5, 7, 0.08]))
    J, b, k, tau = np.exp(sol.x[0]), np.exp(sol.x[1]), np.exp(sol.x[2]), sol.x[3]
    return J, b, k, tau


def spectra_by_window(series, runs):
    """per-window FFTs (to allow a window bootstrap)."""
    from scipy import signal
    w = signal.get_window("hann", NPER)
    U = np.sum(w ** 2) * FS
    Fw = []
    for s in FRF.windows(runs, NPER, NPER // 2):
        F = {k: np.fft.rfft(w * signal.detrend(np.asarray(v[s:s + NPER], float))) for k, v in series.items()}
        Fw.append(F)
    return np.fft.rfftfreq(NPER, 1 / FS), Fw, U


def pooled(Fw, sel, U):
    keys = list(Fw[0])
    S = {}
    for p in keys:
        for q in keys:
            S[(p, q)] = sum(np.conj(Fw[i][p]) * Fw[i][q] for i in sel) / len(sel) / U
    return S


def mode(J, b, k):
    return np.sqrt(k / J) / (2 * np.pi), b / (2 * np.sqrt(k * J))


def main():
    d = P.load()
    u, uff, om, th = d["u"], d["u_ff"], d["om"], d["th"]
    lad = d["ctl_la_des"]
    series = dict(u=u, uff=uff, om=om, th=th, lad=lad)
    res = {}
    rng = np.random.default_rng(7)
    # windows over ALL hands-off engaged stretches, each assigned to a band by its MEAN speed (v spread <= 4 m/s)
    runs_all = P.runs(d["ho"] & (d["v"] > 0.5), min_len=NPER)
    f, Fw, U = spectra_by_window(series, runs_all)
    starts = list(FRF.windows(runs_all, NPER, NPER // 2))
    vbar = np.array([np.mean(d["v"][s:s + NPER]) for s in starts])
    vspr = np.array([np.ptp(d["v"][s:s + NPER]) for s in starts])
    omrms = np.array([np.std(om[s:s + NPER]) for s in starts])
    pr("windows: %d of %.2f s over %d hands-off engaged stretches; v spread <= 4 m/s kept" % (len(starts), NPER / FS, len(runs_all)))
    for nm, lo, hi in P.BANDS:
        allw = [i for i in range(len(starts)) if lo <= vbar[i] < hi and vspr[i] <= 4.0]
        med = np.median(omrms[allw]) if allw else 0
        for sub, wsel in (("all", allw), ("hi-amp", [i for i in allw if omrms[i] >= med]),
                          ("lo-amp", [i for i in allw if omrms[i] < med])):
            if len(wsel) < 6:
                continue
            S = pooled(Fw, wsel, U)
            nw = len(wsel)
            key = nm if sub == "all" else nm + "/" + sub
            pr("")
            pr("=" * 118)
            pr("BAND %s m/s [%s]: %d windows of %.2f s; om rms median %.2f deg/s (window rms range %.2f..%.2f)" % (
                nm, sub, nw, NPER / FS, np.median(omrms[wsel]), np.min(omrms[wsel]), np.max(omrms[wsel])))
            Hd = FRF.H_dir(S, "u", "om")
            Hiv = FRF.H_iv(S, "uff", "u", "om")
            Hsp = FRF.H_iv(S, "lad", "u", "om")
            c_uom = FRF.coh(S, "u", "om")
            c_zom = FRF.coh(S, "uff", "om")
            c_zu = FRF.coh(S, "uff", "u")
            c_sp = FRF.coh(S, "lad", "om")
            if sub == "all":
                pr("  %6s | %8s %6s | %8s %6s | %8s %6s | %5s %5s %5s %5s | %7s" % ("f Hz", "|dir|", "ph", "|IVff|", "ph", "|IVsp|",
                                                                          "ph", "c_uom", "c_zom", "c_zu", "c_spom", "J_inert"))
                for ff in (0.4, 0.8, 1.2, 1.6, 2.0, 2.3, 2.7, 3.1, 3.5, 4.3, 5.1, 6.3, 7.8, 10.2, 12.5, 15.2, 17.6, 20.3, 25.0):
                    i = int(np.argmin(np.abs(f - ff)))
                    pr("  %6.2f | %8.4f %6.0f | %8.4f %6.0f | %8.4f %6.0f | %5.2f %5.2f %5.2f %5.2f | %7.3f" % (
                        f[i], abs(Hd[i]), np.degrees(np.angle(Hd[i])), abs(Hiv[i]), np.degrees(np.angle(Hiv[i])), abs(Hsp[i]),
                        np.degrees(np.angle(Hsp[i])), c_uom[i], c_zom[i], c_zu[i], c_sp[i], 1 / (abs(Hiv[i]) * 2 * np.pi * f[i])))
            out = {}
            for est, H, cz in (("DIRECT", Hd, c_uom), ("IV-ff", Hiv, c_zom)):
                sel = (f >= 0.3) & (f <= 8.0) & (cz >= 0.3)
                if sel.sum() < 5:
                    pr("  %s fit: too few coherent bins (%d)" % (est, sel.sum()))
                    continue
                w = cz[sel] / (1 - np.minimum(cz[sel], 0.95))
                J, b, k, tau = fit(f[sel], H[sel], w)
                fn, z = mode(J, b, k)
                bs = []
                for _ in range(200):
                    pick = rng.choice(wsel, len(wsel))
                    Sb = pooled(Fw, pick, U)
                    Hb = FRF.H_iv(Sb, "uff", "u", "om") if est == "IV-ff" else FRF.H_dir(Sb, "u", "om")
                    cb = FRF.coh(Sb, "uff", "om") if est == "IV-ff" else FRF.coh(Sb, "u", "om")
                    sb = (f >= 0.3) & (f <= 8.0) & (cb >= 0.3)
                    if sb.sum() < 5:
                        continue
                    wb = cb[sb] / (1 - np.minimum(cb[sb], 0.95))
                    try:
                        Jb, bb, kb, tb = fit(f[sb], Hb[sb], wb, x0=(J, b, k, tau))
                    except Exception:
                        continue
                    bs.append((Jb, bb, kb, tb) + mode(Jb, bb, kb))
                bs = np.array(bs)
                lo_, hi_ = np.percentile(bs, 2.5, axis=0), np.percentile(bs, 97.5, axis=0)
                pr("  %-6s fit, %d bins 0.3-8 Hz coh>=0.3: J %.3f [%.3f,%.3f]  b %.2f [%.2f,%.2f]  k %.2f [%.2f,%.2f]"
                   "  tau %.0f [%.0f,%.0f] ms  f_n %.2f [%.2f,%.2f] Hz  zeta %.3f [%.3f,%.3f]" % (
                       est, sel.sum(), J, lo_[0], hi_[0], b, lo_[1], hi_[1], k, lo_[2], hi_[2], 1e3 * tau, 1e3 * lo_[3],
                       1e3 * hi_[3], fn, lo_[4], hi_[4], z, lo_[5], hi_[5]))
                out[est] = dict(J=J, b=b, k=k, tau=tau, fn=fn, zeta=z, ci_lo=lo_, ci_hi=hi_, nbins=int(sel.sum()))
            Hth = FRF.H_iv(S, "uff", "u", "th")
            i1 = (f >= 0.3) & (f <= 0.6)
            pr("  u -> th (IV-ff) |H| 0.3-0.6 Hz: %s deg/T -> dynamic stiffness ~ %.1f T/deg" % (
                np.round(np.abs(Hth[i1]), 4), 1.0 / np.mean(np.abs(Hth[i1]))))
            res[key] = dict(f=f, Hd=Hd, Hiv=Hiv, Hsp=Hsp, c_uom=c_uom, c_zom=c_zom, c_zu=c_zu, fits=out, nw=nw)
    np.savez(os.path.join(HERE, "_scratch", "p3_fd.npz"),
             **{"%s_%s" % (b.replace("/", "_"), k): v for b, r in res.items() for k, v in r.items() if k != "fits"})
    import json
    json.dump({b: {e: {kk: (vv.tolist() if hasattr(vv, "tolist") else vv) for kk, vv in fe.items()}
                   for e, fe in r["fits"].items()} for b, r in res.items()},
              open(os.path.join(HERE, "_scratch", "p3_fd_fits.json"), "w"), indent=1)
    open(os.path.join(HERE, "p3_plant_fd_out.txt"), "w", encoding="utf-8").write(chr(10).join(OUT) + chr(10))


if __name__ == "__main__":
    main()
