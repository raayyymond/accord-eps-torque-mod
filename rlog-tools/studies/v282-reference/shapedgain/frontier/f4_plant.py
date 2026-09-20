# -*- coding: utf-8 -*-
"""f4 -- a plant P(f) good ACROSS the whole 0.1-3.5 Hz range, so the shake band can carry a loop number.

The instrument (the shaped setpoint Z) has no power above ~1 Hz, so the IV plant dies there.  But the
COMMAND does have power at 1.8-3.5 Hz (that is where the shake lives), and |L| there is ~0.1, so the
DIRECT estimator is near-unbiased -- which is exactly the argument loopshape/L5 used for its
command -> steering-rate gains.  So:

    P_iv(f) = S_ZM / S_ZU                                  (used where the instrument is alive)
    P_dir(f) = k_map * ( S_U,SR / S_UU ) / (j 2 pi f)       (used in the shake band)
      k_map = the measured deg -> lateral-accel map gain, fitted per window set by regressing the
              logged M on the logged SR integrated in frequency, over 0.2-1.0 Hz.  No model.

POSITIVE CONTROLS
  (a) k_map fit residual and its agreement with the vehicle-model value implied by |M|/|SA|.
  (b) P_dir vs P_iv in the OVERLAP 0.3-0.9 Hz -- they must agree in magnitude and phase.
  (c) shake-band |L| as flown must reproduce the flown anchors: T64 0.08-0.15, T3 (r72) ~0.19,
      T2 (r71) ~0.46.  If those three land, the shake axis is calibrated and candidates can be
      placed on it.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
sys.path.insert(0, str(HERE.parents[1] / "loopshape" / "loopshape"))
import lp_lib as LP  # noqa: E402

BINS = [("15-22", 15.0, 22.0), ("22+", 22.0, 99.0), ("15+", 15.0, 99.0)]
FAMROUTES = {}
for r, g in LP.GROUPS.items():
    FAMROUTES.setdefault(g, []).append(r)
SHAKE = (1.8, 3.5)
FIT = (0.2, 1.0)
SPLIT = 0.9          # Hz: IV below, direct above


def stack(routes, vlo, vhi):
    cols, vm, laf = None, [], None
    for r in routes:
        p = OUT / f"f1_{r}.npz"
        if not p.exists():
            continue
        D = np.load(p)
        sel = (D["vmed"] >= vlo) & (D["vmed"] < vhi)
        if not sel.any():
            continue
        if cols is None:
            cols = {k: [] for k in ("X", "Y", "Z", "M", "UFB", "UFF", "U", "SR")}
            f = D["f"]
        for k in cols:
            cols[k].append(D[k][sel])
        vm.append(D["vmed"][sel])
        laf = float(D["laf"])
    if cols is None:
        return None
    return dict(f=f, laf=laf, vmed=np.concatenate(vm), **{k: np.concatenate(v) for k, v in cols.items()})


def xs(A, B):
    return np.mean(np.conj(A) * B, axis=0)


def plant(W):
    f = W["f"]
    jw = 2j * np.pi * np.maximum(f, 1e-9)
    Z, M, U, SR = W["Z"], W["M"], W["U"], W["SR"]
    SRi = SR / jw[None, :]                       # SR integrated = the angle, up to the map gain
    fit = (f >= FIT[0]) & (f <= FIT[1])
    num = np.sum(np.conj(SRi[:, fit]) * M[:, fit])
    den = np.sum(np.abs(SRi[:, fit]) ** 2)
    k_map = num / den
    res = np.sum(np.abs(M[:, fit] - k_map * SRi[:, fit]) ** 2) / np.sum(np.abs(M[:, fit]) ** 2)
    P_iv = xs(Z, M) / xs(Z, U)
    P_dir = k_map * xs(U, SRi) / np.maximum(xs(U, U).real, 1e-300)
    P_dirM = xs(U, M) / np.maximum(xs(U, U).real, 1e-300)
    coh_usr = np.abs(xs(U, SRi)) ** 2 / np.maximum(xs(U, U).real * xs(SRi, SRi).real, 1e-300)
    P = np.where(f <= SPLIT, P_iv, P_dir)
    return dict(P=P, P_iv=P_iv, P_dir=P_dir, P_dirM=P_dirM, k_map=k_map, k_res=float(res.real),
                coh_usr=coh_usr, f=f)


def cfg_C(f, v, kp, laf, ki, ki_hi, q, notch=True):
    lsf = float(LP.low_speed_factor(v))
    kie = float(LP.ki_of(v, ki, ki_hi))
    f0 = float(LP.mode_hz(v)) if notch else None
    if q is not None and q <= 0:
        f0 = None
    return LP.c_fb_analytic(f, kp, kie, laf, lsf, f0, q if q else 1.0)


if __name__ == "__main__":
    store = {}
    print("k_map fit (M = k * SR/jw over 0.2-1.0 Hz) and the IV/direct overlap check")
    print(f"{'fam':8s} {'bin':6s} {'n':>4s} {'v':>5s} {'k_map':>18s} {'resid':>7s} "
          f"{'|Pdir/Piv| 0.3':>15s} {'0.6':>7s} {'0.9':>7s} {'dphase 0.6':>11s}")
    for fam, routes in FAMROUTES.items():
        for tag, vlo, vhi in BINS:
            W = stack(routes, vlo, vhi)
            if W is None or W["Z"].shape[0] < 6:
                continue
            R = plant(W)
            f = R["f"]
            jj = [int(np.argmin(np.abs(f - q))) for q in (0.3, 0.6, 0.9)]
            rat = np.abs(R["P_dir"]) / np.maximum(np.abs(R["P_iv"]), 1e-30)
            dph = np.degrees(np.angle(R["P_dir"] / R["P_iv"]))
            v = float(np.median(W["vmed"]))
            print(f"{fam:8s} {tag:6s} {W['Z'].shape[0]:4d} {v:5.1f} "
                  f"{R['k_map'].real:9.5f}{R['k_map'].imag:+9.5f}j {R['k_res']:7.3f} "
                  f"{rat[jj[0]]:15.2f} {rat[jj[1]]:7.2f} {rat[jj[2]]:7.2f} {dph[jj[1]]:11.0f}")
            store[f"{fam}|{tag}"] = dict(
                f=f.tolist(), n=int(W["Z"].shape[0]), v=v, laf=W["laf"], k_map=[float(R["k_map"].real), float(R["k_map"].imag)],
                k_res=R["k_res"],
                **{k: [list(map(float, np.real(R[k]))), list(map(float, np.imag(R[k])))]
                   for k in ("P", "P_iv", "P_dir", "P_dirM")},
                coh_usr=list(map(float, R["coh_usr"])))
    print()
    print("POSITIVE CONTROL (c): shake-band |L| AS FLOWN, from P_dir x the route's OWN analytic C")
    print("   anchors from the brief: T64 0.08-0.15, T3 (r72) ~0.19, T2 (r71) ~0.46")
    print(f"{'fam':8s} {'bin':6s} {'v':>5s} {'|L| 1.8-3.5':>12s} {'|L|@2.0':>8s} {'|L|@2.6':>8s} "
          f"{'|L|@0.2':>8s} {'|L|@0.39':>9s} {'cohUSR 2.6':>11s}")
    for key, S in store.items():
        fam, tag = key.split("|")
        if tag != "15+":
            continue
        route = FAMROUTES[fam][0]
        p = LP.FLOWN[route]
        f = np.array(S["f"])
        P = np.array(S["P"][0]) + 1j * np.array(S["P"][1])
        C = cfg_C(f, S["v"], p["kp"], S["laf"], p["ki"], p["ki_hi"], 1.0 if p["notch"] else None, p["notch"])
        L = P * C
        b = (f >= SHAKE[0]) & (f <= SHAKE[1])
        g = lambda q: abs(L[int(np.argmin(np.abs(f - q)))])
        print(f"{fam:8s} {tag:6s} {S['v']:5.1f} {float(np.mean(np.abs(L[b]))):12.3f} "
              f"{g(2.0):8.3f} {g(2.6):8.3f} {g(0.2):8.3f} {g(0.39):9.3f} "
              f"{S['coh_usr'][int(np.argmin(np.abs(f-2.6)))]:11.2f}")
    json.dump(store, open(OUT / "f4_plant.json", "w"))
    print("\nwrote f4_plant.json")
