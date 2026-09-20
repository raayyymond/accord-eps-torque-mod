# -*- coding: utf-8 -*-
"""d4 -- WHICH transfer is actually unidentified, and what would each injection point fix?

Before choosing an injection point I re-derive, on T64's own windows, the standard error of every
leg of L = P * C_fb, because the brief's premise ("above ~1.2 Hz the loop identification is not
trustworthy, coh(Z,e) 0.19-0.42") names only ONE of them.

  P    = S_ZM / S_ZU     variance set by coh(Z,U) and coh(Z,M)
  Cfb  = S_Z,UFB / S_Z,E variance set by coh(Z,E)   <-- the named casualty
  Ltot = -P * Ky         (f3's projected estimator)

and the SENSITIVITY reading:  T_ze = 1 - T_zm EXACTLY (algebra: S_ZE = S_ZZ - S_ZM), so a small
|T_ze| is NOT evidence of loop gain when a model-inverse feedforward is present -- it is (1 - P*C_ff)
over (1 + P*C_fb).  Printed with phase so the claim can be checked.

Then the two injection points are priced on the SAME target coherence:
  reference node  W_z :  Sww = rho * See / |T_ze|^2          (must beat the road-driven ERROR)
  command  node   W_u :  Sww = rho * Smm / |P|^2             (must beat the road-driven MEASUREMENT)
and each is converted to the four costs with the measured transfers.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
STUDY = HERE.parents[1]
F1 = STUDY / "shapedgain" / "frontier" / "out"
sys.path.insert(0, str(STUDY / "loopshape" / "loopshape"))
import lp_lib as LP  # noqa: E402

FS, NPS = 100.0, 1024
DF = FS / NPS
G = 256.0                        # verified numerically in d3


def xs(A, B):
    return np.mean(np.conj(A) * B, axis=0)


def coh(A, B):
    return np.abs(xs(A, B)) ** 2 / np.maximum(xs(A, A).real * xs(B, B).real, 1e-300)


def se_deg(g2, n, overlap=1.125):
    ne = n / overlap
    return np.degrees(np.sqrt(np.maximum(1 - g2, 0) / np.maximum(2 * ne * g2, 1e-12)))


def pool(fam, vlo=15.0):
    routes = [r for r, g in LP.GROUPS.items() if g == fam]
    cols, vm, sec = None, [], 0.0
    meta = json.load(open(F1 / "f1_meta.json"))
    for r in routes:
        p = F1 / f"f1_{r}.npz"
        if not p.exists():
            continue
        D = np.load(p)
        sel = D["vmed"] >= vlo
        if cols is None:
            cols = {k: [] for k in ("X", "Y", "Z", "M", "UFB", "UFF", "U", "SR")}
            f = D["f"]
        for k in cols:
            cols[k].append(D[k][sel])
        vm.append(D["vmed"][sel]); sec += meta[r]["sec"]
        del D
    return dict(f=f, sec=sec, vmed=np.concatenate(vm), **{k: np.concatenate(v) for k, v in cols.items()})


if __name__ == "__main__":
    W = pool("T64")
    f = W["f"]
    Z, M, U, UFB, Y, SR = W["Z"], W["M"], W["U"], W["UFB"], W["Y"], W["SR"]
    E = Z - M
    n = Z.shape[0]
    Szz, See, Smm, Suu = xs(Z, Z).real, xs(E, E).real, xs(M, M).real, xs(U, U).real
    Tzm = xs(Z, M) / Szz
    Tze = xs(Z, E) / Szz
    Tzu = xs(Z, U) / Szz
    Tzsr = np.abs(xs(Z, SR) / Szz)
    Tzy = np.abs(xs(Z, Y) / Szz)
    P = xs(Z, M) / xs(Z, U)
    Cfb = xs(Z, UFB) / xs(Z, E)
    g_zu, g_zm, g_ze, g_zb = coh(Z, U), coh(Z, M), coh(Z, E), coh(Z, UFB)

    print(f"T64, n = {n} windows, >=15 m/s.  Standard errors are Bendat-Piersol with n_eff = n/1.125.\n")
    print("WHICH LEG IS BROKEN")
    print(f"{'f Hz':>6s} | {'coh ZU':>6s} {'coh ZM':>6s} {'coh ZE':>6s} | "
          f"{'SE P deg':>8s} {'SE C deg':>8s} | {'|P|':>7s} {'argP':>6s} | "
          f"{'|Tzm|':>6s} {'argTzm':>7s} {'|Tze|':>6s} {'argTze':>7s} | {'|L|=PC':>7s} {'argL':>6s}")
    sel = np.where((f >= 0.29) & (f <= 2.45))[0]
    for i in sel:
        L = P[i] * Cfb[i]
        sp = max(se_deg(g_zu[i], n), se_deg(g_zm[i], n))
        print(f"{f[i]:6.3f} | {g_zu[i]:6.3f} {g_zm[i]:6.3f} {g_ze[i]:6.3f} | "
              f"{sp:8.1f} {se_deg(g_ze[i], n):8.1f} | {abs(P[i]):7.3f} {np.degrees(np.angle(P[i])):6.0f} | "
              f"{abs(Tzm[i]):6.3f} {np.degrees(np.angle(Tzm[i])):7.0f} {abs(Tze[i]):6.3f} "
              f"{np.degrees(np.angle(Tze[i])):7.0f} | {abs(L):7.3f} {np.degrees(np.angle(L)):6.0f}")

    # ---------------- price the two injection points at the same target
    print("\n\nINJECTION POINT, PRICED AT THE SAME TARGET COHERENCE 0.7 (rho = 7/3)")
    rho = 7.0 / 3.0
    KS = [7, 10, 13, 16, 19, 22]
    print(f"{'f Hz':>6s} | {'REFERENCE NODE (m/s^2 of setpoint)':^44s} | {'COMMAND NODE (unit torque)':^44s}")
    print(f"{'':6s} | {'A mm/s2':>8s} {'cmd':>8s} {'rate d/s':>9s} {'path':>8s} {'':6s} | "
          f"{'A':>9s} {'= mm/s2':>8s} {'rate d/s':>9s} {'path':>8s} {'':5s}")
    tot_r = np.zeros(4); tot_c = np.zeros(4)
    for k in KS:
        Az = np.sqrt(rho * See[k] / np.abs(Tze[k]) ** 2) / G
        Au = np.sqrt(rho * Smm[k] / np.abs(P[k]) ** 2) / G
        # a command probe of Au produces the same MEASUREMENT motion as a reference probe of Au*|P|/|Tzm|
        z_equiv = Au * abs(P[k]) / max(abs(Tzm[k]), 1e-9)
        print(f"{f[k]:6.3f} | {Az*1000:8.3f} {Az*abs(Tzu[k]):8.5f} {Az*Tzsr[k]:9.4f} {Az*Tzy[k]:8.4f} {'':6s} | "
              f"{Au:9.5f} {z_equiv*1000:8.3f} {z_equiv*Tzsr[k]:9.4f} {z_equiv*Tzy[k]:8.4f}")
        tot_r += [Az, Az * abs(Tzu[k]), Az * Tzsr[k], Az * Tzy[k]]
        tot_c += [Au, z_equiv * 1e-3, z_equiv * Tzsr[k], z_equiv * Tzy[k]]
    print(f"{'SUM':>6s} | {tot_r[0]*1000:8.3f} {tot_r[1]:8.5f} {tot_r[2]:9.4f} {tot_r[3]:8.4f} {'':6s} | "
          f"{tot_c[0]:9.5f} {tot_c[1]*1e6:8.3f} {tot_c[2]:9.4f} {tot_c[3]:8.4f}")

    np.savez(OUT / "d4.npz", f=f, P=P, Cfb=Cfb, Tzm=Tzm, Tze=Tze, Tzu=Tzu, Tzsr=Tzsr, Tzy=Tzy,
             See=See, Smm=Smm, Szz=Szz, Suu=Suu, g_zu=g_zu, g_zm=g_zm, g_ze=g_ze, n=n, sec=W["sec"])
    print("\nwrote out/d4.npz")
