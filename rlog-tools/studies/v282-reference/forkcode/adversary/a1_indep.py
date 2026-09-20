# -*- coding: utf-8 -*-
"""a1 -- re-derive ARM-KP2's closure independently, then shake every nuisance choice it rests on.

POSITIVE CONTROLS printed first.  If they fail, nothing below counts.
  PC1  median(cs_p / cs_err) must equal the route's flown SteerKP (the analytic C's P leg).
  PC2  median(-(p+i+f)/out) must equal the flown SteerLatAccel (the /LAF leg).
  PC3  the metric at nperseg 1024 must land on the handed-down 1.3512 / 0.442.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adv_core as A  # noqa: E402

OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
FLOWN = dict(kp=1.0, laf=14.0, ki=0.30, q=1.0)
ARMKP2 = dict(kp=3.0, laf=14.0, ki=0.30, q=0.60)


def pc_route(route, kp_exp, laf_exp):
    S = A.V.load(route)
    D = np.load(A.V.CACHE / f"{route}.npz", allow_pickle=True)
    act = (D["cs_active"] > 0.5) & (D["lat_active"] > 0.5)
    e = D["cs_err"][act]
    p = D["cs_p"][act]
    ok = np.abs(e) > 1e-4
    kp_meas = float(np.median(p[ok] / e[ok]))
    o = D["cs_out"][act]
    ok2 = np.abs(o) > 5e-3
    laf_meas = float(np.median(-(D["cs_p"][act][ok2] + D["cs_i"][act][ok2] + D["cs_f"][act][ok2]) / o[ok2]))
    del S, D
    return kp_meas, laf_meas


def closure_of(W, kp, laf, ki, q, Pkey, Vkey, ident, ref, flown_J, Lscale=1.0):
    f, v = W["f"], W["v"]
    C0 = A.C_fb(f, v, FLOWN["kp"], FLOWN["laf"], FLOWN["ki"], FLOWN["q"])
    C1 = A.C_fb(f, v, kp, laf, ki, q)
    L0 = ident[Pkey][None, :] * C0 * Lscale
    K = C1 / C0
    L1 = L0 * K
    rho = (1.0 + L0) / (1.0 + L1)
    Vv = ident[Vkey][None, :] if Vkey != "unit" else np.ones_like(L0)
    E = W["X"] - W["Y"]
    D = W["Z"] - W["M"]
    E1 = E + Vv * D * (rho - 1.0)
    b = (f >= A.BAND[0]) & (f <= A.BAND[1])
    px = float(np.sum(np.abs(W["X"][:, b]) ** 2))
    m = float(np.sum(np.abs(E1[:, b]) ** 2)) / px
    U1 = W["UFF"] + W["UFB"] * K * rho
    shk = (f >= A.SHAKE[0]) & (f <= A.SHAKE[1])
    sc = float(np.sqrt(np.sum(np.abs(U1[:, shk]) ** 2) / np.sum(np.abs(W["U"][:, shk]) ** 2)))
    sj = [int(np.argmin(np.abs(f - x))) for x in A.SHAKE_PTS]
    return dict(J=m, closure=(flown_J - m) / (flown_J - ref), shake_cmd=sc,
                shake_L=float(np.mean(np.abs(L1[:, sj]))),
                L0_shake=float(np.mean(np.abs(L0[:, sj]))),
                bands=A.bands_of(W, E1))


def main():
    res = {}
    print("=" * 110)
    print("POSITIVE CONTROLS  (flown SteerKP 1.0, SteerLatAccel 14.0 on T64; 0.9 / 6.0 on V282)")
    for r, kp, laf in [(A.T64[0], 1.0, 14.0), (A.T64[1], 1.0, 14.0), (A.V282[0], 0.9, 6.0)]:
        km, lm = pc_route(r, kp, laf)
        print(f"  {r}  kp_measured {km:7.4f} (expect {kp})   LAF_measured {lm:7.4f} (expect {laf})")

    print()
    print("=" * 110)
    print("1. THE METRIC AND ARM-KP2's CLOSURE UNDER EVERY NUISANCE CHOICE THAT WAS NEVER WRITTEN DOWN")
    print("   'closure' = (J_flown - J_new)/(J_flown - J_V282) with BOTH ends recomputed at that setting.")
    print()
    hdr = (f"{'nps':>5s} {'sat':>5s} {'detr':>6s} {'Pest':>5s} {'Vest':>5s} {'nwinT':>5s} {'nwinV':>5s} "
           f"{'J_flown':>8s} {'J_V282':>7s} {'J_KP2':>7s} {'clos%':>7s} {'shkCmd':>7s} {'shkL':>6s}")
    print(hdr)
    rows = []
    for nps in (512, 1024, 2048):
        for satfilt, dtr in ((0.02, "linear"), (None, "linear"), (0.02, "constant")):
            if nps != 1024 and (satfilt is None or dtr == "constant"):
                continue
            Wt = A.cat([A.extract(r, nps=nps, satfilt=satfilt, detrend=dtr) for r in A.T64])
            Wv = A.cat([A.extract(r, nps=nps, satfilt=satfilt, detrend=dtr) for r in A.V282])
            Jf, Jv = A.metric(Wt), A.metric(Wv)
            ident = A.identify(Wt, inst="X")
            for Pk, Vk in (("P", "V_h1"), ("P", "V_iv"), ("P_h1", "V_h1"), ("P", "unit")):
                r = closure_of(Wt, ARMKP2["kp"], ARMKP2["laf"], ARMKP2["ki"], ARMKP2["q"],
                               Pk, Vk, ident, Jv, Jf)
                print(f"{nps:5d} {str(satfilt):>5s} {dtr:>6s} {Pk:>5s} {Vk:>5s} {len(Wt['v']):5d} {len(Wv['v']):5d} "
                      f"{Jf:8.4f} {Jv:7.4f} {r['J']:7.4f} {r['closure']*100:7.1f} {r['shake_cmd']:7.3f} {r['shake_L']:6.3f}")
                rows.append(dict(nps=nps, sat=str(satfilt), detrend=dtr, P=Pk, V=Vk,
                                 nwin_t=len(Wt["v"]), nwin_v=len(Wv["v"]),
                                 J_flown=Jf, J_v282=Jv, **{k: (v if not isinstance(v, list) else v)
                                                           for k, v in r.items()}))
            if nps == 1024 and satfilt == 0.02 and dtr == "linear":
                np.savez_compressed(OUT / "a1_W_T64_1024.npz", **{k: v for k, v in Wt.items() if k != "route"})
                np.savez_compressed(OUT / "a1_W_V282_1024.npz", **{k: v for k, v in Wv.items() if k != "route"})
            del Wt, Wv
    json.dump(rows, open(OUT / "a1_nuisance.json", "w"), indent=1)

    print()
    print("=" * 110)
    print("2. LEAVE-ONE-ROUTE-OUT on the reference denominator and on the target (nps 1024)")
    Wt_each = {r: A.extract(r, nps=1024) for r in A.T64}
    Wv_each = {r: A.extract(r, nps=1024) for r in A.V282}
    Wt = A.cat(list(Wt_each.values()))
    ident = A.identify(Wt, inst="X")
    Jv_all = A.metric(A.cat(list(Wv_each.values())))
    print(f"   V282 pooled J {Jv_all:.4f};  per route " +
          "  ".join(f"{r[:10]} {A.metric(w):.3f}" for r, w in Wv_each.items()))
    print(f"   T64  pooled J {A.metric(Wt):.4f};  per route " +
          "  ".join(f"{r[:10]} {A.metric(w):.3f}" for r, w in Wt_each.items()))
    print()
    print(f"{'drop':>12s} {'J_flown':>8s} {'J_V282':>8s} {'J_KP2':>8s} {'clos%':>7s}")
    for drop in [None] + A.V282:
        keep = [w for r, w in Wv_each.items() if r != drop]
        Jv = A.metric(A.cat(keep))
        r = closure_of(Wt, **ARMKP2, Pkey="P", Vkey="V_h1", ident=ident, ref=Jv, flown_J=A.metric(Wt))
        print(f"{(drop or 'none')[:12]:>12s} {A.metric(Wt):8.4f} {Jv:8.4f} {r['J']:8.4f} {r['closure']*100:7.1f}")
    for drop in A.T64:
        keep = [w for rr, w in Wt_each.items() if rr != drop]
        Wk = A.cat(keep)
        idk = A.identify(Wk, inst="X")
        r = closure_of(Wk, **ARMKP2, Pkey="P", Vkey="V_h1", ident=idk, ref=Jv_all, flown_J=A.metric(Wk))
        print(f"{('T:'+drop[:10]):>12s} {A.metric(Wk):8.4f} {Jv_all:8.4f} {r['J']:8.4f} {r['closure']*100:7.1f}")

    print()
    print("=" * 110)
    print("3. SPEED BIN (the metric pools 15-22 and 22+; the plant and lsf differ a lot between them)")
    for lo, hi in ((15.0, 22.0), (22.0, 99.0)):
        selT = (Wt["v"] >= lo) & (Wt["v"] < hi)
        Wts = {k: (v[selT] if isinstance(v, np.ndarray) and v.ndim and v.shape[0] == len(Wt["v"]) else v)
               for k, v in Wt.items()}
        Wts["f"] = Wt["f"]
        idb = A.identify(Wt, inst="X", vsel=selT)
        r = closure_of(Wts, **ARMKP2, Pkey="P", Vkey="V_h1", ident=idb, ref=Jv_all, flown_J=A.metric(Wts))
        print(f"   {lo:.0f}-{hi:.0f} m/s  n {int(selT.sum()):4d}  J_flown {A.metric(Wts):.4f}  "
              f"J_KP2 {r['J']:.4f}  closure {r['closure']*100:5.1f}%  shkCmd {r['shake_cmd']:.3f}  "
              f"|L|shake {r['shake_L']:.3f} (today {r['L0_shake']:.3f})")

    print()
    print("=" * 110)
    print("4. DOSE LADDER on MY numbers (LAF 14, Q as noted), and the kp/LAF each dose implies")
    print(f"{'config':26s} {'kp/LAF':>7s} {'J':>7s} {'clos%':>7s} {'shkCmd':>7s} {'|L|shk':>7s}")
    for lbl, kp, q in (("as flown  KP 1.0 Q1.0", 1.0, 1.0), ("KP 1.5 Q1.0", 1.5, 1.0),
                       ("ARM-KP    KP 2.0 Q1.0", 2.0, 1.0), ("KP 2.5 Q1.0", 2.5, 1.0),
                       ("KP 3.0 Q1.0 (ceiling)", 3.0, 1.0), ("ARM-KP2   KP 3.0 Q0.6", 3.0, 0.6),
                       ("KP 4.0 Q0.6 (code)", 4.0, 0.6), ("KP 5.0 Q0.6 (code)", 5.0, 0.6),
                       ("KP 6.0 Q0.6 (code)", 6.0, 0.6), ("KP 8.0 Q0.6 (code)", 8.0, 0.6),
                       ("KP 12.0 Q0.6 (code)", 12.0, 0.6)):
        r = closure_of(Wt, kp, 14.0, 0.30, q, "P", "V_h1", ident, Jv_all, A.metric(Wt))
        print(f"{lbl:26s} {kp/14.0:7.4f} {r['J']:7.4f} {r['closure']*100:7.1f} {r['shake_cmd']:7.3f} {r['shake_L']:7.3f}")


if __name__ == "__main__":
    main()
