# -*- coding: utf-8 -*-
"""Build my own per-window complex spectra, one route at a time (RAM).  Two extra channels the other
streams do not carry:
    C = desired CURVATURE (1/m)       and   K = achieved curvature = wz / v
which remove the v^2 / v asymmetry between X = curv*v^2 and Y = wz*v.  If a window's speed varies, that
asymmetry alone puts a spurious gain into |H|, and 8-15 m/s corner entries are exactly where speed varies.
"""
import sys
import numpy as np
import adv_lib as L

NS = [512, 1024, 2048]


def main():
    L.OUT.mkdir(parents=True, exist_ok=True)
    for r in L.ROUTES:
        S = L.load(r)
        v = np.maximum(S["v"], 1.0)
        S["C"] = S["X"] / (v * v)          # desired curvature
        S["K"] = S["Y"] / (v * v)          # achieved curvature  (Y = wz*v  =>  Y/v^2 = wz/v)
        L.CH[:] = ["X", "Y", "Z", "W", "A", "C", "K"]
        for n in NS:
            sp = L.spec_route(S, n, detrends=("lin", "mean"), tapers=("hann", "bh", "mt3"))
            if sp is None:
                print(f"  {r} n{n}: no windows")
                continue
            z = {f"F_{d}_{t}": sp["F"][(d, t)] for d in ("lin", "mean") for t in ("hann", "bh", "mt3")}
            mm = sp["meta"]
            for k in ("v", "ap95", "sa50", "sa95", "xrms", "yrms", "i0", "fr"):
                z["m_" + k] = mm[k]
            # extra per-window meta my attacks need
            i0 = mm["i0"].astype(int)
            vsd, kur, xin = [], [], []
            for k in i0:
                sl = slice(k, k + n)
                vsd.append(float(np.std(S["v"][sl])))
                kur.append(float(np.median(np.abs(S["C"][sl]))))
                xin.append(float(np.percentile(np.abs(S["X"][sl]), 50)))
            z["m_vsd"] = np.asarray(vsd)
            z["m_curv50"] = np.asarray(kur)
            z["m_ax50"] = np.asarray(xin)
            np.savez_compressed(L.OUT / f"spec_{r}_n{n}.npz", **z)
            print(f"  {r} n{n}: {len(i0):4d} windows  {len(i0)*n/100.0:7.1f} s")
        del S
    print("done")


if __name__ == "__main__":
    main()
