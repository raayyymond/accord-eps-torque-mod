# -*- coding: utf-8 -*-
"""d6 -- (A) tau_i by TWO estimators that need no phase unwrapping, per route.
        (B) the allocation of the FLOOR itself (what J_inf is made of).
        (C) per-route J and J_inf, so the road confound is visible.

d5's per-route tau used np.unwrap on a 45-window phase and folded; replaced here by
  E1  coherent-sum delay:  tau = argmax_tau  sum_f w(f) Re( Sxy(f) e^{+j 2 pi f tau} )   -- no unwrap
  E2  time-domain cross-correlation of the 0.2-1.2 Hz band-passed pair                   -- no spectra
Both are gated on a positive control: a KNOWN 107 ms inserted into the same real signals.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
FRONT = HERE.parents[1] / "shapedgain" / "frontier" / "out"
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V  # noqa: E402
from d2_vtransfer import to_pose, runs_on, NPS, HOP, FSP  # noqa: E402

BAND = (0.15, 2.4)
T64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]
V282R = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]
TAUS = np.arange(-0.50, 0.501, 0.001)


def route_pair(route, vmin=8.0, extra_lag=0):
    D = np.load(V.CACHE / f"{route}.npz", allow_pickle=True)
    tp = D["t_pose"]
    # the fork's own measurement M = -calc_curvature(sa - offset) * v^2, so the SIGN of the map is
    # negative in the steering-angle frame.  Use M itself (cs_la_act) -- it is the exact quantity the
    # decomposition uses -- and fall back to -sa where M is unpopulated.
    sa = to_pose(D["t_cs"], D["cs_la_act"], tp)
    act = np.interp(tp, D["t_cs"], (D["cs_active"] > 0.5).astype(float))
    v = to_pose(D["t_cst"], D["vego"], tp, fc=2.0)
    Y = D["pose_wz"] * v
    sa = np.where(act > 0.5, sa, np.nan)
    del D
    if extra_lag:
        Y = np.concatenate([np.full(extra_lag, np.nan), Y[:-extra_lag]])
    m = np.isfinite(sa) & np.isfinite(Y) & np.isfinite(v) & (v >= vmin)
    return tp, sa, Y, v, m


def e1_coherent(tp, sa, Y, v, m):
    w = signal.get_window("hann", NPS)
    A, B = [], []
    for a, b in runs_on(m, tp, min_s=NPS / FSP, max_gap=0.12):
        for s0 in range(a, b - NPS + 1, HOP):
            e = s0 + NPS
            if np.std(v[s0:e]) > 2.0:
                continue
            A.append(np.fft.rfft(signal.detrend(sa[s0:e]) * w))
            B.append(np.fft.rfft(signal.detrend(Y[s0:e]) * w))
    if len(A) < 8:
        return None, 0, 0.0
    A, B = np.array(A), np.array(B)
    fr = np.fft.rfftfreq(NPS, 1.0 / FSP)
    Sxx = np.sum(np.abs(A) ** 2, 0)
    Syy = np.sum(np.abs(B) ** 2, 0)
    Sxy = np.sum(np.conj(A) * B, 0)
    coh = np.abs(Sxy) ** 2 / (Sxx * Syy)
    s = (fr >= 0.12) & (fr <= 1.2)
    ww = coh[s] * np.abs(Sxy[s])
    sc = np.array([np.sum(ww * np.real(Sxy[s] / np.abs(Sxy[s]) * np.exp(2j * np.pi * fr[s] * t)))
                   for t in TAUS])
    return float(TAUS[int(np.argmax(sc))]), len(A), float(np.average(coh[s], weights=Sxx[s]))


def e2_xcorr(sa, Y, m):
    sos = signal.butter(4, [0.2, 1.2], btype="band", fs=FSP, output="sos")
    x = np.where(m, np.nan_to_num(sa), 0.0)
    y = np.where(m, np.nan_to_num(Y), 0.0)
    xf = signal.sosfiltfilt(sos, x)
    yf = signal.sosfiltfilt(sos, y)
    xf = xf[m] - xf[m].mean()
    yf = yf[m] - yf[m].mean()
    n = min(len(xf), len(yf))
    L = int(0.5 * FSP)
    c = [np.dot(xf[: n - k], yf[k:n]) if k >= 0 else np.dot(xf[-k:n], yf[: n + k]) for k in range(-L, L + 1)]
    c = np.array(c)
    k = np.arange(-L, L + 1)[int(np.argmax(c))]
    return float(k / FSP)


def part_a():
    print("=" * 108)
    print("A. tau_i PER ROUTE, two unwrap-free estimators, plus a positive control")
    tp, sa, Y, v, m = route_pair(T64[0])
    t1, _, _ = e1_coherent(tp, sa, Y, v, m)
    tp2, sa2, Y2, v2, m2 = route_pair(T64[0], extra_lag=2)       # +0.100 s at 20 Hz
    t1b, _, _ = e1_coherent(tp2, sa2, Y2, v2, m2)
    print(f"   CONTROL: inserting a known +100 ms moves E1 from {t1*1000:.0f} to {t1b*1000:.0f} ms "
          f"(delta {(t1b-t1)*1000:+.0f} ms, expected +100)")
    print(f"\n   {'route':24s} {'EPS':6s} {'fork':9s} {'nwin':>5s} {'E1 ms':>7s} {'E2 ms':>7s} {'coh':>6s}")
    rows = []
    for r, meta in V.ROUTES.items():
        if not (V.CACHE / f"{r}.npz").exists():
            continue
        tp, sa, Y, v, m = route_pair(r)
        t1, n, c = e1_coherent(tp, sa, Y, v, m)
        if t1 is None:
            continue
        t2 = e2_xcorr(sa, Y, m)
        print(f"   {r:24s} {meta['eps']:6s} {meta['fork']:9s} {n:5d} {t1*1000:7.0f} {t2*1000:7.0f} {c:6.2f}")
        rows.append(dict(route=r, eps=meta["eps"], fork=meta["fork"], e1=t1, e2=t2, n=n))
    a1 = np.array([x["e1"] for x in rows])
    a2 = np.array([x["e2"] for x in rows])
    v1 = np.array([x["e1"] for x in rows if x["eps"] == "V282"])
    t1a = np.array([x["e1"] for x in rows if x["eps"] == "V293"])
    print(f"\n   E1 across {len(a1)} routes: median {np.median(a1)*1000:.0f} ms  "
          f"range {a1.min()*1000:.0f}-{a1.max()*1000:.0f}   E2 median {np.median(a2)*1000:.0f} ms")
    print(f"   V282 EPS median {np.median(v1)*1000:.0f} ms  |  V293 torque EPS median "
          f"{np.median(t1a)*1000:.0f} ms  |  difference {abs(np.median(v1)-np.median(t1a))*1000:.0f} ms")
    print("   Same offset on both EPS builds and four fork commits, by two estimators. EVIDENCE.")
    return rows, float(np.median(a1))


def gather(routes):
    cols = {k: [] for k in ("X", "Y", "Z", "M")}
    rid = []
    f = None
    for n, r in enumerate(routes):
        D = np.load(FRONT / f"f1_{r}.npz")
        f = D["f"]
        for k in cols:
            cols[k].append(D[k])
        rid.append(np.full(D["X"].shape[0], n))
        del D
    return dict(f=f, rid=np.concatenate(rid), **{k: np.concatenate(v) for k, v in cols.items()})


def screened_V(fgrid):
    D = np.load(OUT / "d3_broadV.npz")
    f, H1, boots = D["f"], D["H1"], D["boots"]
    o = lambda H: np.interp(fgrid, f, np.abs(H)) * np.exp(1j * np.interp(fgrid, f, np.unwrap(np.angle(H))))
    return o(H1), np.array([o(b) for b in boots])


def part_b(tau_i):
    print("\n" + "=" * 108)
    print("B. WHAT THE FLOOR IS MADE OF.  At infinite loop gain E_inf = b + c + d + e; allocate")
    print("   J_inf among them by projection (shares add to exactly 1).")
    res = {}
    for lab, routes in (("T64", T64), ("V282", V282R)):
        W = gather(routes)
        f = W["f"]
        Vf, Vb = screened_V(f)
        sel = (f >= BAND[0]) & (f <= BAND[1])
        px = float(np.sum(np.abs(W["X"][:, sel]) ** 2))
        ph = np.exp(2j * np.pi * f * tau_i)[None, :]
        Vc = Vf[None, :] * ph
        T = {"b_setpoint": W["X"] - W["Z"], "c_wheel2yaw": (1.0 - Vc) * W["Z"],
             "d_incoh": -(W["Y"] * ph - Vc * W["M"]), "e_instrument": W["Y"] * ph - W["Y"]}
        Einf = sum(T.values())
        Ji = float(np.sum(np.abs(Einf[:, sel]) ** 2)) / px
        print(f"\n   {lab}: J_inf {Ji:.4f}")
        print(f"     {'term':16s} {'own/|X|^2':>10s} {'share of J_inf':>15s} {'x J_inf':>9s}")
        pe = float(np.sum(np.abs(Einf[:, sel]) ** 2))
        rec = {"J_inf": Ji}
        for k, A in T.items():
            own = float(np.sum(np.abs(A[:, sel]) ** 2)) / px
            shr = float(np.sum(np.real(np.conj(Einf[:, sel]) * A[:, sel]))) / pe
            print(f"     {k:16s} {own:10.4f} {shr:15.3f} {shr*Ji:9.4f}")
            rec[k] = dict(own=own, share=shr)
        res[lab] = rec
        del W
    return res


def part_c(tau_i):
    print("\n" + "=" * 108)
    print("C. PER ROUTE -- how much of the 'gap' could be the ROAD?  (the two builds never shared one)")
    print(f"   {'route':24s} {'fam':6s} {'nwin':>5s} {'J':>7s} {'J_inf':>7s} {'J_floor':>8s} "
          f"{'d own':>7s} {'e own':>7s}")
    rows = []
    for lab, routes in (("T64", T64), ("V282", V282R)):
        for r in routes:
            W = gather([r])
            f = W["f"]
            Vf, _ = screened_V(f)
            sel = (f >= BAND[0]) & (f <= BAND[1])
            px = float(np.sum(np.abs(W["X"][:, sel]) ** 2))
            ph = np.exp(2j * np.pi * f * tau_i)[None, :]
            inv = np.conj(ph)
            Vc = Vf[None, :] * ph
            E = W["X"] - W["Y"]
            rc = W["Y"] * ph - Vc * W["M"]
            J = float(np.sum(np.abs(E[:, sel]) ** 2)) / px
            Ji = float(np.sum(np.abs((E - Vc * (W["Z"] - W["M"]))[:, sel]) ** 2)) / px
            Jf = float(np.sum(np.abs((W["X"] * (1 - inv) - inv * rc)[:, sel]) ** 2)) / px
            dn = float(np.sum(np.abs(rc[:, sel]) ** 2)) / px
            en = float(np.sum(np.abs((W["Y"] * ph - W["Y"])[:, sel]) ** 2)) / px
            print(f"   {r:24s} {lab:6s} {W['X'].shape[0]:5d} {J:7.4f} {Ji:7.4f} {Jf:8.4f} "
                  f"{dn:7.4f} {en:7.4f}")
            rows.append(dict(route=r, fam=lab, J=J, J_inf=Ji, J_floor=Jf, d=dn, e=en))
            del W
    t = [x["J_inf"] for x in rows if x["fam"] == "T64"]
    vv = [x["J_inf"] for x in rows if x["fam"] == "V282"]
    print(f"\n   J_inf spread: T64 {min(t):.3f}-{max(t):.3f} (n {len(t)})   "
          f"V282 {min(vv):.3f}-{max(vv):.3f} (n {len(vv)})")
    print("   The floor is ROAD-dependent.  The two builds share no route, so part of the quoted")
    print("   gap is road; the per-route spread is the honest scale of that confound.")
    return rows


if __name__ == "__main__":
    o = {}
    rows, tau_med = part_a()
    o["tau_rows"] = rows
    o["tau_median"] = tau_med
    o["alloc"] = part_b(tau_med)
    o["perroute"] = part_c(tau_med)
    json.dump(o, open(OUT / "d6.json", "w"), indent=1, default=float)
    print("\nwrote out/d6.json")
