# -*- coding: utf-8 -*-
"""d5 -- INJECTION POINT, decided on the full requirement, not on one transfer.

Each injection point must identify a SET of transfers.  Price each one at the same target coherence
and take the MAX over the set -- that is the honest amplitude.

REFERENCE NODE  W_z added to `setpoint` (the Z node, where the logged desiredLateralAccel is read).
  It enters the loop exactly where Z does, so every f3 estimator keeps its form.
    T_ze = (1 - P*C_ff)/(1 + P*C_fb)   needs  Sww >= rho * See / |T_ze|^2
    C_fb = S_W,UFB / S_W,E             same requirement (E is the binding channel)
    P    = S_W,M / S_W,U               needs  Sww >= rho * max(Smm/|T_zm|^2, Suu/|T_zu|^2)

COMMAND NODE  W_u added to the torque that LEAVES the controller (the AccordDither node), so the
  plant input is u_ctl + W_u and the logged `out` is u_ctl alone.  W_u is known, so u_total is too.
    M      = P*S*(ff + W) + S*d        P*S measured as S_W,M / Sww
    u_ctl  = -C*M + ff                 so S_W,(U+W)/Sww = S = 1/(1+L)  EXACTLY, one division,
                                       no plant model, no controller model, no unit chain
    P      = S_W,M / S_W,(U+W)
  requirements:  S needs Sww >= rho * Suu / |S|^2 ;  P needs Sww >= rho * Smm / |P*S|^2
  (the naive S_W,M/S_W,U ratio is -1/C, NOT P -- W must be ADDED BACK to the logged command.)

Costs are converted to the SAME physical axes for both, using measured transfers, so they compare.
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

FS, NPS, G = 100.0, 1024, 256.0
DF = FS / NPS
RHO = 7.0 / 3.0                 # target coherence 0.7


def xs(A, B):
    return np.mean(np.conj(A) * B, axis=0)


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
    Szz, See, Smm, Suu = xs(Z, Z).real, xs(E, E).real, xs(M, M).real, xs(U, U).real
    Tzm, Tze, Tzu = xs(Z, M) / Szz, xs(Z, E) / Szz, xs(Z, U) / Szz
    Tzsr, Tzy = np.abs(xs(Z, SR) / Szz), np.abs(xs(Z, Y) / Szz)
    P = xs(Z, M) / xs(Z, U)
    Cfb = xs(Z, UFB) / xs(Z, E)
    L = P * Cfb
    S = 1.0 / (1.0 + L)

    KS = [7, 10, 13, 16, 19, 22]
    print("REQUIRED PROBE AMPLITUDE, per transfer, at target coherence 0.70.  Bold number = binding.\n")
    print(f"{'f Hz':>6s} | {'|L|':>5s} {'|S|':>5s} {'|P|':>5s} | "
          f"{'REFERENCE  A (mm/s^2)':^34s} | {'COMMAND  A (unit torque)':^26s}")
    print(f"{'':6s} | {'':5s} {'':5s} {'':5s} | {'via E':>9s} {'via M':>9s} {'via U':>9s} {'MAX':>9s} | "
          f"{'via S':>8s} {'via M':>8s} {'MAX':>8s}")
    rows = []
    for k in KS:
        az_e = np.sqrt(RHO * See[k]) / np.abs(Tze[k]) / G
        az_m = np.sqrt(RHO * Smm[k]) / np.abs(Tzm[k]) / G
        az_u = np.sqrt(RHO * Suu[k]) / np.abs(Tzu[k]) / G
        az = max(az_e, az_m, az_u)
        au_s = np.sqrt(RHO * Suu[k]) / np.abs(S[k]) / G
        au_m = np.sqrt(RHO * Smm[k]) / np.abs(P[k] * S[k]) / G
        au = max(au_s, au_m)
        rows.append((k, az, au))
        print(f"{f[k]:6.3f} | {abs(L[k]):5.3f} {abs(S[k]):5.3f} {abs(P[k]):5.2f} | "
              f"{az_e*1e3:9.2f} {az_m*1e3:9.2f} {az_u*1e3:9.2f} {az*1e3:9.2f} | "
              f"{au_s:8.5f} {au_m:8.5f} {au:8.5f}")

    print("\n\nCOST OF EACH, ON THE SAME PHYSICAL AXES")
    # a command probe W_u produces measurement P*S*W_u; the setpoint that produces the same is
    # W_u*|P*S|/|T_zm| ; wheel rate and path follow with the measured Z-referred transfers.
    hdr = f"{'f Hz':>6s} | {'REF: cmd':>9s} {'rate':>7s} {'path':>7s} {'ang':>7s} | {'CMD: cmd':>9s} {'rate':>7s} {'path':>7s} {'ang':>7s}"
    print(hdr)
    tr = np.zeros(4); tc = np.zeros(4); trms = np.zeros(4); crms = np.zeros(4)
    for k, az, au in rows:
        zeq = au * np.abs(P[k] * S[k]) / max(np.abs(Tzm[k]), 1e-9)
        r = np.array([az * np.abs(Tzu[k]), az * Tzsr[k], az * Tzy[k], az * Tzsr[k] / (2 * np.pi * f[k])])
        c = np.array([au, zeq * Tzsr[k], zeq * Tzy[k], zeq * Tzsr[k] / (2 * np.pi * f[k])])
        tr += r; tc += c; trms += r ** 2 / 2; crms += c ** 2 / 2
        print(f"{f[k]:6.3f} | {r[0]:9.5f} {r[1]:7.4f} {r[2]:7.4f} {r[3]:7.4f} | "
              f"{c[0]:9.5f} {c[1]:7.4f} {c[2]:7.4f} {c[3]:7.4f}")
    print(f"{'SUM':>6s} | {tr[0]:9.5f} {tr[1]:7.4f} {tr[2]:7.4f} {tr[3]:7.4f} | "
          f"{tc[0]:9.5f} {tc[1]:7.4f} {tc[2]:7.4f} {tc[3]:7.4f}")
    print(f"{'RMS':>6s} | {np.sqrt(trms[0]):9.5f} {np.sqrt(trms[1]):7.4f} {np.sqrt(trms[2]):7.4f} "
          f"{np.sqrt(trms[3]):7.4f} | {np.sqrt(crms[0]):9.5f} {np.sqrt(crms[1]):7.4f} "
          f"{np.sqrt(crms[2]):7.4f} {np.sqrt(crms[3]):7.4f}")
    print("\nunits: cmd = unit torque; rate = deg/s of steering rate; path = m/s^2 of achieved lateral")
    print("       accel; ang = deg of wheel angle.  Compare: AccordDither ships 0.008-0.012 with a")
    print("       0.02 ceiling; the Honda slew limiter is 0.03/frame; backlash 2F/k is 1.1-1.3 deg.")

    np.savez(OUT / "d5.npz", f=f, L=L, S=S, P=P, Szz=Szz, See=See, Smm=Smm, Suu=Suu,
             Tzm=Tzm, Tze=Tze, Tzu=Tzu, Tzsr=Tzsr, Tzy=Tzy,
             ks=np.array([r[0] for r in rows]), az=np.array([r[1] for r in rows]),
             au=np.array([r[2] for r in rows]))
    print("\nwrote out/d5.npz")
