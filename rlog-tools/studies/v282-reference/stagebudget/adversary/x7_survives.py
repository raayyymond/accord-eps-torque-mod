# -*- coding: utf-8 -*-
"""WHAT SURVIVES?  Every cell of the ranking re-tested with the ROUTE as the unit of inference and an
exact permutation test over the 3 + 9 route labels.  A cell is only reportable if both builds have at
least 3 routes with >= 3 windows in it.  Reported on NRMSE (the goal's own metric) and on |H|.
"""
import itertools
import numpy as np
import adv_lib as L

CHI = {c: i for i, c in enumerate(["X", "Y", "Z", "W", "A", "C", "K"])}
BANDS = [(0.15, 0.30, 2048), (0.30, 0.60, 1024), (0.60, 1.20, 1024), (1.20, 2.40, 512)]
MINW = 3
MINR = 3


def nrm(F, fr, f1, f2):
    b = (fr >= f1) & (fr < f2)
    X = F[:, CHI["X"]][:, :, b]
    Y = F[:, CHI["Y"]][:, :, b]
    Sxx = (np.abs(X) ** 2).sum((0, 1))
    Syy = (np.abs(Y) ** 2).sum((0, 1))
    Sxy = (np.conj(X) * Y).sum((0, 1))
    tot = float((Syy - 2 * np.real(Sxy) + Sxx).sum() / max(Sxx.sum(), 1e-300))
    Hb = Sxy / np.maximum(Sxx, 1e-300)
    coh = float((np.abs(Hb - 1) ** 2 * Sxx).sum() / max(Sxx.sum(), 1e-300))
    H = float(np.average(np.abs(Hb), weights=Sxx))
    return np.sqrt(max(tot, 0)), np.sqrt(max(coh, 0)), H


def perm_p(vals, istorq):
    vals = np.asarray(vals, float)
    n, k = len(vals), int((~istorq).sum())
    obs = vals[istorq].mean() - vals[~istorq].mean()
    cnt = tot = 0
    for c in itertools.combinations(range(n), k):
        m = np.zeros(n, bool); m[list(c)] = True
        tot += 1
        if abs(vals[~m].mean() - vals[m].mean()) >= abs(obs) - 1e-12:
            cnt += 1
    return obs, cnt / tot


def main():
    Rn = {n: {r: np.load(L.OUT / f"spec_{r}_n{n}.npz") for r in L.ROUTES} for n in (512, 1024, 2048)}
    rts = list(L.V282) + list(L.TORQ)
    print("=" * 150)
    print("Every cell, route as the unit.  'rV/rT' = routes contributing >=3 windows.  p = exact")
    print("permutation over the route labels.  MINIMUM ATTAINABLE p with 3 vs 9 routes is 2/220 = 0.009;")
    print("with 2 vs 9 it is 2/55 = 0.036; with 1 vs k it is 1/(k+1).")
    print("=" * 150)
    print(f"  {'band':11s} {'speed':6s} {'amp':3s} {'rV':>3s} {'rT':>3s} {'secV':>6s} {'secT':>6s} "
          f"{'M V282':>7s} {'M TORQ':>7s} {'dM':>7s} {'p(M)':>7s} | {'H V':>6s} {'H T':>6s} {'p(H)':>7s}")
    out = []
    for f1, f2, n in BANDS:
        R = Rn[n]
        fr = R[rts[0]]["m_fr"]
        for sb in range(4):
            lo, hi = L.SPD[sb]
            for ab in range(3):
                a0, a1 = L.ACUT[ab]
                M, H, ist, sec = [], [], [], []
                for r in rts:
                    d = R[r]
                    m = (d["m_v"] >= lo) & (d["m_v"] < hi) & (d["m_ap95"] >= a0) & (d["m_ap95"] < a1)
                    if m.sum() < MINW:
                        continue
                    t, c, h = nrm(d["F_lin_hann"][m], fr, f1, f2)
                    M.append(t); H.append(h); sec.append(m.sum() * n / 100.0)
                    ist.append(L.ROUTES[r]["eps"] == "V293")
                ist = np.array(ist, bool); M = np.array(M); H = np.array(H); sec = np.array(sec)
                if len(ist) == 0:
                    continue
                if (~ist).sum() < MINR or ist.sum() < MINR:
                    if len(ist) and (~ist).sum() >= 1 and ist.sum() >= 1:
                        print(f"  {f1:.2f}-{f2:.2f}   {L.SPDN[sb]:6s} {L.ACUTN[ab]:3s} "
                              f"{int((~ist).sum()):3d} {int(ist.sum()):3d} {sec[~ist].sum():6.0f} "
                              f"{sec[ist].sum():6.0f}   NOT TESTABLE at the route level")
                    continue
                dM, pM = perm_p(M, ist)
                dH, pH = perm_p(H, ist)
                star = "  <<<" if pM <= 0.05 else ("   <" if pM <= 0.10 else "")
                print(f"  {f1:.2f}-{f2:.2f}   {L.SPDN[sb]:6s} {L.ACUTN[ab]:3s} {int((~ist).sum()):3d} "
                      f"{int(ist.sum()):3d} {sec[~ist].sum():6.0f} {sec[ist].sum():6.0f} "
                      f"{M[~ist].mean():7.3f} {M[ist].mean():7.3f} {dM:+7.3f} {pM:7.4f} | "
                      f"{H[~ist].mean():6.3f} {H[ist].mean():6.3f} {pH:7.4f}{star}")
                out.append((f"{f1:.2f}-{f2:.2f}", L.SPDN[sb], L.ACUTN[ab], dM, pM,
                            float(sec[ist].sum())))
    print("\n  CELLS THAT SURVIVE route-level clustering at p <= 0.05, ranked by torque exposure seconds:")
    surv = sorted([o for o in out if o[4] <= 0.05], key=lambda o: -o[5])
    for o in surv:
        print(f"    {o[0]:11s} {o[1]:6s} {o[2]:3s}  dM {o[3]:+.3f}  p {o[4]:.4f}  torque sec {o[5]:.0f}")
    if not surv:
        print("    NONE")


if __name__ == "__main__":
    main()
