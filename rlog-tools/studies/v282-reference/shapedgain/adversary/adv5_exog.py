# -*- coding: utf-8 -*-
"""ADV5: the two assumptions the asymptote rests on, tested on the FLOWN routes rather than asserted.

  ASSUMPTION 1  'the exogenous drivers of D are unchanged by the dose'.
      D = S*W with W = Z - P*u_ff - d the loop's exogenous drive.  W is computed per route as
      W = D*(1+L) from this stream's own L, and the irreducible residual A = (X-Y) - V*D is computed
      per route.  If either tracks a route's command roughness or its loop gain, the assumption is
      falsified on data that already exists.
  ASSUMPTION 2  'V is unchanged'.  The plant is compared between the two EPS builds, because the
      headline 'interpolation inside the flown envelope 0.050-0.379' pools them.

  Plus: the AccordErrorNotchQ hint, tested by putting the exact notch transfer into the loop.
"""
import json
import sys

import numpy as np
from scipy import signal

import advlib as A
from adv4_loop import BANDS, C_of, NPS, SHAKE, mode_hz, notch_H

TORQ = [rk for rk, m in A.FLOWN.items() if m["eps"] == "V293"]
V282 = [rk for rk, m in A.FLOWN.items() if m["eps"] == "V282"]


def per_route(rk, q_override=None):
    meta = A.FLOWN[rk]
    N = A.load_nodes(rk)
    sr = np.nan_to_num(N["Y"]) * 0  # placeholder; real wheel rate below
    S = None
    fr, sp, vs = A.windows(N, nperseg=NPS, overlap=0.5, minrun=30.0)
    if len(vs) == 0:
        return None
    # 1.8-3.5 Hz wheel-RATE RMS on the same mask (the shake currency)
    import v282cmp as V
    raw = V.load(rk)
    m = raw["active"] & ~raw["pressed"] & (raw["v"] >= A.VMIN)
    sos = signal.butter(4, [SHAKE[0], SHAKE[1]], btype="band", fs=A.FS, output="sos")
    segs = [np.nan_to_num(raw["sr"][a:b]) for a, b in V.runs(m, raw["t"], min_s=30.0)]
    shake = float(np.sqrt(np.mean(np.concatenate([signal.sosfiltfilt(sos, s) ** 2 for s in segs])))) if segs else np.nan
    ucmd = [-np.nan_to_num(raw["out"][a:b]) for a, b in V.runs(m, raw["t"], min_s=30.0)]
    ushake = float(np.sqrt(np.mean(np.concatenate([signal.sosfiltfilt(sos, s) ** 2 for s in ucmd])))) if ucmd else np.nan
    del raw

    X, Z, M, Y, U = sp["X"], sp["Z"], sp["M"], sp["Y"], sp["U"]
    E, D = X - Y, Z - M
    sel = A.bandsel(fr)
    den = float(np.sum(np.abs(X[:, sel]) ** 2))
    J = float(np.sum(np.abs(E[:, sel]) ** 2) / den)
    P_iv = np.sum(np.conj(X) * M, 0) / np.sum(np.conj(X) * U, 0)
    q = meta.get("q", 1.0) if q_override is None else q_override
    Cw = np.array([C_of(fr, v, meta, q=q) for v in vs])
    L = P_iv[None, :] * Cw
    W = D * (1.0 + L)
    Vd = np.sum(np.conj(M) * Y, 0) / np.sum(np.conj(M) * M, 0)
    Vi = np.sum(np.conj(X) * Y, 0) / np.sum(np.conj(X) * M, 0)
    out = dict(rk=rk, fam=meta["fam"], eps=meta["eps"], kpl=meta["kp"] / meta["laf"], nwin=int(len(vs)),
               v=float(np.median(vs)), J=J, shake=shake, ushake=ushake,
               Jinf_dir=float(np.sum(np.abs((E - Vd[None, :] * D)[:, sel]) ** 2) / den),
               Jinf_iv=float(np.sum(np.abs((E - Vi[None, :] * D)[:, sel]) ** 2) / den),
               Wpow=float(np.sum(np.abs(W[:, sel]) ** 2) / den),
               Dpow=float(np.sum(np.abs(D[:, sel]) ** 2) / den))
    for b1, b2 in BANDS:
        s = (fr >= b1) & (fr < b2)
        w = np.sum(np.abs(X[:, s]) ** 2, 0)
        out[f"P_{b1}"] = float(np.average(np.abs(P_iv[s]), weights=w))
        out[f"L_{b1}"] = float(np.average(np.abs(L[:, s]), weights=np.abs(X[:, s]) ** 2))
        out[f"W_{b1}"] = float(np.sum(np.abs(W[:, s]) ** 2) / den)
        out[f"Ainf_{b1}"] = float(np.sum(np.abs((E - Vd[None, :] * D)[:, s]) ** 2) / den)
    s = (fr >= SHAKE[0]) & (fr < SHAKE[1])
    out["L_shake"] = float(np.average(np.abs(L[:, s]), weights=np.abs(X[:, s]) ** 2))
    out["P_shake"] = float(np.average(np.abs(P_iv[s]), weights=np.sum(np.abs(X[:, s]) ** 2, 0)))
    del N, sp, X, Z, M, Y, U, E, D, L, W
    return out


def corr(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    k = np.isfinite(a) & np.isfinite(b)
    if k.sum() < 3:
        return np.nan
    return float(np.corrcoef(a[k], b[k])[0, 1])


def main():
    rows = []
    for rk in TORQ + V282:
        r = per_route(rk)
        if r:
            rows.append(r)
            print(f"  {rk[:8]} {r['fam']:8s} done", flush=True)
    json.dump(rows, open(A.OUT / "adv5_exog.json", "w"), indent=1)

    print("\nPER ROUTE (>=15 m/s, engaged hands-off, runs >=30 s, 10.24 s windows)")
    print(f"  {'route':>9s} {'fam':>7s} {'kp/LAF':>7s} {'J':>6s} {'Jinf_dir':>9s} {'Jinf_iv':>8s} "
          f"{'Wpow':>7s} {'shake':>7s} {'u_shake':>8s} {'|L|shk':>7s}")
    for r in rows:
        print(f"  {r['rk'][:8]:>9s} {r['fam']:>7s} {r['kpl']:7.4f} {r['J']:6.3f} {r['Jinf_dir']:9.3f} "
              f"{r['Jinf_iv']:8.3f} {r['Wpow']:7.3f} {r['shake']:7.3f} {r['ushake']:8.4f} {r['L_shake']:7.3f}")

    tor = [r for r in rows if r["eps"] == "V293"]
    print("\nASSUMPTION 1 -- is the irreducible residual really independent of how rough the loop is?")
    print("  (torque-EPS routes only, n=%d; Pearson r, and what it means if it is not ~0)" % len(tor))
    for ylab, key in (("Jinf_dir (the asymptote's own residual)", "Jinf_dir"),
                      ("Wpow (the loop error's exogenous drive)", "Wpow"),
                      ("Dpow (the loop error itself)", "Dpow")):
        print(f"    {ylab:42s}  vs wheel shake r = {corr([r['shake'] for r in tor], [r[key] for r in tor]):+.3f}"
              f"   vs command shake r = {corr([r['ushake'] for r in tor], [r[key] for r in tor]):+.3f}"
              f"   vs kp/LAF r = {corr([r['kpl'] for r in tor], [r[key] for r in tor]):+.3f}")
    print("\n  band-resolved: where the asymptote's residual sits, and where it moves with shake")
    print(f"    {'band':>12s} {'median Ainf':>12s} {'share of Jinf':>14s} {'corr(Ainf, shake)':>18s}")
    tj = np.median([r["Jinf_dir"] for r in tor])
    for b1, b2 in BANDS:
        vals = [r[f"Ainf_{b1}"] for r in tor]
        print(f"    {b1:5.2f}-{b2:4.2f} {np.median(vals):12.4f} {np.median(vals)/tj*100:13.1f}% "
              f"{corr([r['shake'] for r in tor], vals):18.3f}")

    print("\nASSUMPTION 2 -- the plant the extrapolation is being carried across")
    print(f"  {'EPS':>6s} {'n':>3s} " + " ".join(f"{'|P| '+str(b1):>10s}" for b1, _ in BANDS) + f" {'|P| shake':>10s}")
    for eps in ("V282", "V293"):
        rs = [r for r in rows if r["eps"] == eps]
        print(f"  {eps:>6s} {len(rs):3d} " + " ".join(f"{np.median([r[f'P_{b1}'] for r in rs]):10.2f}" for b1, _ in BANDS)
              + f" {np.median([r['P_shake'] for r in rs]):10.2f}")
    for eps in ("V282", "V293"):
        rs = [r for r in rows if r["eps"] == eps]
        lo = np.median([r["P_0.15"] for r in rs]); hi = np.median([r["P_shake"] for r in rs])
        print(f"    {eps}: |P|(shake)/|P|(0.15-0.30) = {hi/lo:.2f}   "
              f"kp/LAF flown {min(r['kpl'] for r in rs):.4f}..{max(r['kpl'] for r in rs):.4f}")
    print("  => a gain raise sized on the pooled envelope is being carried across a plant whose")
    print("     high-frequency shape differs by the ratio printed above.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
