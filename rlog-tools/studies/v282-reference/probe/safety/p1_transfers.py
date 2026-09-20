# -*- coding: utf-8 -*-
"""p1 -- PRICE THE PROBE.  What does 1 m/s^2 of reference-path injection buy, in the quantities the
driver actually perceives, and what is already there that he has NOT complained about?

Everything here is read off the f1 window spectra (shapedgain/frontier/out/f1_*.npz), which are
FFTs of LOGGED signals on the goal metric's own window set (>=15 m/s, laterally engaged, hands off,
runs >= 30 s, unsaturated).  Nothing is modelled and no simulator is used.

TRANSFERS (identified, instrument = the shaped setpoint Z, which is exogenous to road disturbance,
so H1 = S_ZG / S_ZZ is UNBIASED for the closed loop Z->G at every frequency; low coherence raises its
VARIANCE, it does not bias it.  n windows is printed with every number):

    T_ZM   Z -> M      the controller's own measurement (static angle map, m/s^2)
    T_ZA   Z -> angle  = T_ZM / k_map                   (deg)                  <-- WHEEL ANGLE
    T_ZSR  Z -> SR     steering rate                    (deg/s)                <-- WHEEL MOTION
    T_ZY   Z -> Y      livePose yaw * v                 (m/s^2)                <-- LATERAL ACCEL
    T_ZW   Z -> yaw    = T_ZY / v                       (rad/s, deg/s)         <-- YAW RATE
    T_ZU   Z -> U      the command out in [-1,1]                               <-- RAIL / SLEW

AMBIENT (no transfer needed, pure measurement): the band-RMS that ALREADY exists in each of those
signals in 0.6-2.0 Hz, per speed bin, per route family.  That is the "has not complained about" ruler.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
F1 = STUDY / "shapedgain" / "frontier" / "out"
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(STUDY / "loopshape" / "loopshape"))
import lp_lib as LP  # noqa: E402

FS = 100.0
NPS = 1024
# speed bins centred on the three the brief asks for
BINS = [("15", 13.0, 18.0), ("22", 18.0, 25.0), ("28", 25.0, 99.0), ("15+", 15.0, 99.0)]
PROBE_BAND = (0.6, 2.0)
KMAP_FIT = (0.2, 1.0)
W = np.hanning(NPS + 1)[:NPS]          # scipy get_window('hann', N) is the periodic form
S2 = np.sum(W ** 2)                     # for PSD scaling
PSD_SCALE = 2.0 / (FS * S2)             # one-sided PSD from |rfft(x*w)|^2


def xs(A, B):
    return np.mean(np.conj(A) * B, axis=0)


def band_rms(P, f, lo, hi):
    """RMS of a signal inside [lo,hi] from its one-sided PSD."""
    s = (f >= lo) & (f < hi)
    df = f[1] - f[0]
    return float(np.sqrt(np.sum(P[s]) * df))


def do_bin(routes, vlo, vhi):
    cols, vm = None, []
    for r in routes:
        p = F1 / f"f1_{r}.npz"
        if not p.exists():
            continue
        D = np.load(p)
        sel = (D["vmed"] >= vlo) & (D["vmed"] < vhi)
        if not sel.any():
            D.close()
            continue
        if cols is None:
            cols = {k: [] for k in ("Z", "M", "Y", "U", "SR", "X")}
            f = D["f"]
        for k in cols:
            cols[k].append(D[k][sel])
        vm.append(D["vmed"][sel])
        D.close()
    if cols is None:
        return None
    C = {k: np.concatenate(v) for k, v in cols.items()}
    vmed = np.concatenate(vm)
    n = len(vmed)
    if n < 4:
        return None
    jw = 2j * np.pi * np.maximum(f, 1e-9)
    Z, M, Y, U, SR = C["Z"], C["M"], C["Y"], C["U"], C["SR"]
    SRi = SR / jw[None, :]                       # integrated rate == wheel angle (deg), up to DC

    # ---- k_map : (m/s^2) per deg, measured, from the logged pair (M, integrated SR) ----
    fit = (f >= KMAP_FIT[0]) & (f <= KMAP_FIT[1])
    k_map = np.sum(np.conj(SRi[:, fit]) * M[:, fit]) / np.sum(np.abs(SRi[:, fit]) ** 2)
    k_res = float((np.sum(np.abs(M[:, fit] - k_map * SRi[:, fit]) ** 2)
                   / np.sum(np.abs(M[:, fit]) ** 2)).real)

    Szz = xs(Z, Z).real
    out = dict(n=n, v_med=float(np.median(vmed)), v_lo=vlo, v_hi=vhi, f=f,
               k_map=complex(k_map), k_map_abs=float(abs(k_map)), k_map_res=k_res)
    for name, G in (("M", M), ("Y", Y), ("U", U), ("SR", SR), ("A", SRi)):
        Szg = xs(Z, G)
        Sgg = xs(G, G).real
        out[f"T_Z{name}"] = Szg / np.maximum(Szz, 1e-300)
        out[f"coh_Z{name}"] = np.abs(Szg) ** 2 / np.maximum(Szz * Sgg, 1e-300)
        out[f"psd_{name}"] = Sgg * PSD_SCALE          # ambient one-sided PSD, units^2/Hz
    out["psd_Z"] = Szz * PSD_SCALE
    out["psd_X"] = xs(C["X"], C["X"]).real * PSD_SCALE
    return out


def main():
    fams = {}
    for r, g in LP.GROUPS.items():
        fams.setdefault(g, []).append(r)
    fams["ALL_T64"] = fams["T64"] + fams["T64B"]
    res = {}
    for fam, routes in fams.items():
        for bn, lo, hi in BINS:
            R = do_bin(routes, lo, hi)
            if R is None:
                continue
            res[f"{fam}|{bn}"] = R
    np.savez_compressed(HERE / "p1_out.npz",
                        **{f"{k}::{kk}": v for k, R in res.items() for kk, v in R.items()
                           if isinstance(v, (np.ndarray,))},
                        **{f"{k}::__scalars": json.dumps({kk: (float(v) if not isinstance(v, complex)
                                                              else [v.real, v.imag])
                                                          for kk, v in R.items()
                                                          if not isinstance(v, np.ndarray)})
                           for k, R in res.items()})

    # ---------------- report ----------------
    f = res[[k for k in res if k.startswith("V282|")][0]]["f"]
    pb = (f >= PROBE_BAND[0]) & (f < PROBE_BAND[1])
    print("=" * 108)
    print("A. MEASURED MAP GAIN k_map  (m/s^2 of controller-measurement per DEG of wheel angle), 0.2-1.0 Hz fit")
    print(f"{'family|bin':18s} {'n':>4s} {'v_med':>6s} {'|k_map|':>9s} {'resid':>7s}   1 deg -> m/s^2 ; 1 m/s^2 -> deg")
    for k, R in sorted(res.items()):
        if not k.split("|")[1] in ("15", "22", "28"):
            continue
        print(f"{k:18s} {R['n']:4d} {R['v_med']:6.1f} {R['k_map_abs']:9.4f} {R['k_map_res']:7.3f}"
              f"   {R['k_map_abs']:.4f} ; {1/R['k_map_abs']:8.2f}")

    print()
    print("=" * 108)
    print(f"B. AMBIENT band-RMS already present in {PROBE_BAND[0]}-{PROBE_BAND[1]} Hz (measured, no transfer)")
    print(f"{'family|bin':18s} {'n':>4s} {'v':>5s} {'angle deg':>10s} {'rate d/s':>9s} {'latacc':>8s}"
          f" {'yaw d/s':>8s} {'cmd u':>8s} {'setpt Z':>8s} {'model X':>8s}")
    for k, R in sorted(res.items()):
        bn = k.split("|")[1]
        if bn not in ("15", "22", "28"):
            continue
        v = R["v_med"]
        a = band_rms(R["psd_A"], f, *PROBE_BAND)
        sr = band_rms(R["psd_SR"], f, *PROBE_BAND)
        y = band_rms(R["psd_Y"], f, *PROBE_BAND)
        u = band_rms(R["psd_U"], f, *PROBE_BAND)
        z = band_rms(R["psd_Z"], f, *PROBE_BAND)
        x = band_rms(R["psd_X"], f, *PROBE_BAND)
        print(f"{k:18s} {R['n']:4d} {v:5.1f} {a:10.4f} {sr:9.4f} {y:8.4f}"
              f" {np.degrees(y/v):8.4f} {u:8.5f} {z:8.4f} {x:8.4f}")

    print()
    print("=" * 108)
    print("C. THE PRICE OF INJECTION: |T_Z->G| per 1.0 m/s^2 of setpoint injection, and its coherence")
    for k in sorted(res):
        bn = k.split("|")[1]
        if bn not in ("15", "22", "28"):
            continue
        if not k.startswith(("V282|", "ALL_T64|", "T3|")):
            continue
        R = res[k]
        print(f"\n  --- {k}   n={R['n']}  v={R['v_med']:.1f} m/s   |k_map|={R['k_map_abs']:.4f} ---")
        print(f"  {'f Hz':>6s} {'|T_ZM|':>7s} {'|T_ZA| deg':>10s} {'|T_ZSR|':>8s} {'|T_ZY|':>7s}"
              f" {'yawdeg/s':>9s} {'|T_ZU|':>8s} {'coh_ZM':>7s} {'coh_ZY':>7s} {'ph_ZM':>7s}")
        for i in np.where(pb)[0]:
            v = R["v_med"]
            tzm = abs(R["T_ZM"][i]); tza = tzm / R["k_map_abs"]
            print(f"  {f[i]:6.2f} {tzm:7.3f} {tza:10.3f} {abs(R['T_ZSR'][i]):8.3f}"
                  f" {abs(R['T_ZY'][i]):7.3f} {np.degrees(abs(R['T_ZY'][i])/v):9.3f}"
                  f" {abs(R['T_ZU'][i]):8.4f} {R['coh_ZM'][i]:7.3f} {R['coh_ZY'][i]:7.3f}"
                  f" {np.degrees(np.angle(R['T_ZM'][i])):7.1f}")
    return res


if __name__ == "__main__":
    main()
