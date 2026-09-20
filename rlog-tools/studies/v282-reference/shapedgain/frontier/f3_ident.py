# -*- coding: utf-8 -*-
"""f3 -- identify, on the METRIC's own window set (>=15 m/s, nps 1024), the three transfers the
frontier needs, plus the positive controls that say whether to believe them.

    P(f)      command U -> the controller's own measurement M      (IV, instrument Z)
    C_fb(f)   raw error (Z-M) -> U_FB                              (IV, instrument Z)  [check vs analytic]
    L_tot(f)  the WHOLE feedback loop, PID + 100 Hz rate loop + observer, by projecting Z out of
              U and M and regressing (lp_lib.total_loop's estimator, re-implemented here)
    V(f)      M -> Y, the wheel-angle -> achieved-yaw leg that sits OUTSIDE the loop

POSITIVE CONTROLS printed:
  1. C_fb_IV / C_fb_analytic on every family -- the analytic C is built from each family's OWN flown
     SteerKP / LAF / ki / notch, so a ratio far from 1 means the identification is not usable.
  2. On the V282 families the PID is the ONLY feedback path, so K_y must come back equal to -C_fb.
  3. coherence of the instrument with u, with M and with the error.
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


def stack(routes, vlo, vhi):
    cols, vm = None, []
    laf = None
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
    return dict(f=f, laf=laf, vmed=np.concatenate(vm),
                **{k: np.concatenate(v) for k, v in cols.items()})


def xs(A, B):
    return np.mean(np.conj(A) * B, axis=0)


def identify(W):
    Z, M, U, UFB, Y = W["Z"], W["M"], W["U"], W["UFB"], W["Y"]
    E = Z - M
    Szz = xs(Z, Z).real
    Szm, Szu, Szb, Sze, Szy = xs(Z, M), xs(Z, U), xs(Z, UFB), xs(Z, E), xs(Z, Y)
    Suu, Smm, See, Syy = xs(U, U).real, xs(M, M).real, xs(E, E).real, xs(Y, Y).real
    P = Szm / Szu
    Cfb = Szb / Sze
    Vleg = Szy / Szm                      # IV estimate of the OUT-OF-LOOP wheel -> yaw leg
    Vh1 = xs(M, Y) / np.maximum(Smm, 1e-300)
    # total loop: project the exogenous reference out of U and M, then regress U_perp on M_perp
    bu = xs(Z, U) / np.maximum(Szz, 1e-300)
    bm = xs(Z, M) / np.maximum(Szz, 1e-300)
    Up, Mp = U - bu[None, :] * Z, M - bm[None, :] * Z
    Smpmp, Supup = xs(Mp, Mp).real, xs(Up, Up).real
    Ky = xs(Mp, Up) / np.maximum(Smpmp, 1e-300)
    return dict(P=P, Cfb=Cfb, L_pid=P * Cfb, L_tot=-P * Ky, Ky=Ky, V=Vleg, V_h1=Vh1,
                coh_zu=np.abs(Szu) ** 2 / np.maximum(Szz * Suu, 1e-300),
                coh_zm=np.abs(Szm) ** 2 / np.maximum(Szz * Smm, 1e-300),
                coh_ze=np.abs(Sze) ** 2 / np.maximum(Szz * See, 1e-300),
                coh_mu=np.abs(xs(Mp, Up)) ** 2 / np.maximum(Smpmp * Supup, 1e-300),
                coh_my=np.abs(xs(M, Y)) ** 2 / np.maximum(Smm * Syy, 1e-300),
                Szz=Szz, n=Z.shape[0])


def analytic_C(f, route, vmed, laf):
    p = LP.FLOWN[route]
    v = float(np.median(vmed))
    lsf = float(LP.low_speed_factor(v))
    ki = float(LP.ki_of(v, p["ki"], p["ki_hi"]))
    f0 = float(LP.mode_hz(v)) if p["notch"] else None
    return LP.c_fb_analytic(f, p["kp"], ki, laf, lsf, f0, 1.0), dict(v=v, lsf=lsf, ki_eff=ki, f0=f0, **p)


if __name__ == "__main__":
    store = {}
    print("IDENTIFICATION on the metric's own windows. 'ratio C' = |C_IV| / |C_analytic| (positive control 1)")
    print(f"{'fam':8s} {'bin':6s} {'n':>4s} " + " ".join(f"{q:>7.2f}Hz" for q in (0.20, 0.29, 0.39, 0.59, 0.98, 1.95, 2.93)))
    for fam, routes in FAMROUTES.items():
        for tag, vlo, vhi in BINS:
            W = stack(routes, vlo, vhi)
            if W is None or W["Z"].shape[0] < 6:
                continue
            R = identify(W)
            f = W["f"]
            Cana, info = analytic_C(f, routes[0], W["vmed"], W["laf"])
            store[f"{fam}|{tag}"] = dict(
                f=f.tolist(), n=int(R["n"]), v=float(np.median(W["vmed"])), laf=W["laf"], info={k: (v if not isinstance(v, np.floating) else float(v)) for k, v in info.items()},
                **{k: [list(map(float, np.real(R[k]))), list(map(float, np.imag(R[k])))]
                   for k in ("P", "Cfb", "L_pid", "L_tot", "Ky", "V", "V_h1")},
                **{k: list(map(float, R[k])) for k in ("coh_zu", "coh_zm", "coh_ze", "coh_mu", "coh_my")})
            j = [int(np.argmin(np.abs(f - q))) for q in (0.20, 0.29, 0.39, 0.59, 0.98, 1.95, 2.93)]
            rat = np.abs(R["Cfb"]) / np.maximum(np.abs(Cana), 1e-30)
            print(f"{fam:8s} {tag:6s} {R['n']:4d} " + " ".join(f"{rat[k]:9.2f}" for k in j))
    print()
    print("POSITIVE CONTROL 2: K_y vs -C_fb (must be ~1 on V282 families, where the PID is the only path)")
    print(f"{'fam':8s} {'bin':6s} " + " ".join(f"{q:>7.2f}Hz" for q in (0.20, 0.29, 0.39, 0.59, 0.98, 1.95)))
    for k, S in store.items():
        f = np.array(S["f"])
        Ky = np.array(S["Ky"][0]) + 1j * np.array(S["Ky"][1])
        C = np.array(S["Cfb"][0]) + 1j * np.array(S["Cfb"][1])
        j = [int(np.argmin(np.abs(f - q))) for q in (0.20, 0.29, 0.39, 0.59, 0.98, 1.95)]
        r = np.abs(Ky) / np.maximum(np.abs(C), 1e-30)
        fam, tag = k.split("|")
        print(f"{fam:8s} {tag:6s} " + " ".join(f"{r[i]:9.2f}" for i in j))
    print()
    print("INSTRUMENT COHERENCE (Z vs U / Z vs M / Z vs E) and the out-of-loop leg M->Y")
    for k, S in store.items():
        if not k.endswith("|15+"):
            continue
        f = np.array(S["f"])
        j = [int(np.argmin(np.abs(f - q))) for q in (0.20, 0.39, 0.98, 1.95, 2.93)]
        Vv = np.array(S["V"][0]) + 1j * np.array(S["V"][1])
        print(f"  {k:14s} n{S['n']:4d}  " +
              " ".join(f"{f[i]:.2f}Hz zu{S['coh_zu'][i]:.2f} zm{S['coh_zm'][i]:.2f} ze{S['coh_ze'][i]:.2f}"
                       f" |V|{abs(Vv[i]):.2f} argV{np.degrees(np.angle(Vv[i])):+5.0f} cohMY{S['coh_my'][i]:.2f} |" for i in j))
    json.dump(store, open(OUT / "f3_ident.json", "w"))
    print("\nwrote f3_ident.json")
