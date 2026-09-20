# -*- coding: utf-8 -*-
"""d1 -- the PROBE BUDGET, read from the logs, on the metric's own window set.

Everything the excitation design needs is a per-BIN quantity on the SAME window set the goal metric
and the frontier identification already use (f1: laterally engaged, hands off, >=15 m/s, contiguous
runs >= 30 s, unsaturated, nperseg 1024 = 10.24 s, hop 512, Hann, detrended).

Per bin f, pooled over a family's windows:
    Szz   the planner's own shaped-setpoint power        -- what the probe must beat
    See   the loop's own raw-error power  (E = Z - M)
    g2    coh(Z, E)                                      -- the broken quantity
    |Tze| = |Szm.../| ... measured setpoint->error transfer   (= sqrt(g2 * See / Szz))
    |Tzu| measured setpoint->COMMAND transfer             -- the rail / shake consequence
    |Tzm| measured setpoint->MEASUREMENT transfer         -- what the wheel does
    |Tzy| measured setpoint->ACHIEVED LATERAL ACCEL       -- what the driver feels

SIZING IDENTITY (algebra, stated so it can be attacked):
  With a probe W added at the SAME NODE as Z (so it drives the loop through the identical transfer),
  and using W ALONE as the instrument,
        e = Tze*(Z + W) + e_road ,   S_ee(today) = |Tze|^2*Szz + S_road
        coh(W,e) = |Tze|^2*Sww / S_ee(today)          <-- the Z-driven part is NOISE to W
                 = g2_old * (Sww/Szz)                  <-- because |Tze|^2*Szz = g2_old*See
  => rho_W  = g2_old * r ,  r = Sww/Szz per bin ;  coh_new = rho/(1+rho).
  With the COMBINED instrument Z+W (i.e. the logged desiredLateralAccel unchanged),
        coh_comb = g2_old*(1+r) / (g2_old*(1+r) + 1 - g2_old).
  EVIDENCE: g2_old, Szz, See are measured here.  The identity itself is algebra on the definition of
  coherence; it assumes only that the probe enters at the same node (it does, by construction) and
  that the loop is linear over the probe's amplitude (the probe is sized far below any clamp).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
STUDY = HERE.parents[1]
F1 = STUDY / "shapedgain" / "frontier" / "out"
sys.path.insert(0, str(STUDY / "loopshape" / "loopshape"))
import lp_lib as LP  # noqa: E402

FAMROUTES = {}
for r, g in LP.GROUPS.items():
    FAMROUTES.setdefault(g, []).append(r)

NPS, FS = 1024, 100.0
DF = FS / NPS                      # 0.09766 Hz bin width
BAND = (0.6, 2.0)                  # the band the probe must make identifiable
METRIC_BAND = (0.15, 2.4)
SHAKE = (1.8, 3.5)


def xs(A, B):
    return np.mean(np.conj(A) * B, axis=0)


def pool(fam, vlo=15.0, vhi=99.0):
    cols, vm = None, []
    for r in FAMROUTES.get(fam, []):
        p = F1 / f"f1_{r}.npz"
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
        del D
    if cols is None:
        return None
    return dict(f=f, vmed=np.concatenate(vm), **{k: np.concatenate(v) for k, v in cols.items()})


def budget(W):
    Z, M, U, Y, SR = W["Z"], W["M"], W["U"], W["Y"], W["SR"]
    E = Z - M
    Szz, See, Suu, Smm = xs(Z, Z).real, xs(E, E).real, xs(U, U).real, xs(M, M).real
    Sze, Szu, Szm, Szy, Szsr = xs(Z, E), xs(Z, U), xs(Z, M), xs(Z, Y), xs(Z, SR)
    g2 = np.abs(Sze) ** 2 / np.maximum(Szz * See, 1e-300)
    return dict(n=Z.shape[0], f=W["f"], Szz=Szz, See=See, Suu=Suu, Smm=Smm, g2=g2,
                Tze=Sze / np.maximum(Szz, 1e-300), Tzu=Szu / np.maximum(Szz, 1e-300),
                Tzm=Szm / np.maximum(Szz, 1e-300), Tzy=Szy / np.maximum(Szz, 1e-300),
                Tzsr=Szsr / np.maximum(Szz, 1e-300),
                v=float(np.median(W["vmed"])))


if __name__ == "__main__":
    store = {}
    fams = ["T64", "T64B", "T5", "T4", "V282"]
    for fam in fams:
        W = pool(fam)
        if W is None:
            continue
        B = budget(W)
        store[fam] = {k: (v.tolist() if isinstance(v, np.ndarray) and np.isrealobj(v)
                          else ([list(map(float, np.real(v))), list(map(float, np.imag(v)))]
                                if isinstance(v, np.ndarray) else v))
                      for k, v in B.items()}
        del W
    json.dump(store, open(OUT / "d1_budget.json", "w"))

    f = np.array(store["T64"]["f"])
    sel = np.where((f >= 0.25) & (f <= 3.6))[0]
    print("PER-BIN BUDGET, pooled >=15 m/s, family T64 (rev 6.4 as flown -- the config the probe flies on)")
    print(f"n windows = {store['T64']['n']}, bin width {DF:.5f} Hz, window 10.24 s\n")
    hdr = f"{'f Hz':>6s} {'|Z|rms':>9s} {'|E|rms':>9s} {'coh(Z,E)':>9s} {'|Tze|':>7s} {'|Tzu|':>8s} {'|Tzm|':>7s} {'|Tzy|':>7s} {'|Tzsr|':>8s}"
    print(hdr)
    for i in sel:
        b = store["T64"]
        zz = np.sqrt(b["Szz"][i]); ee = np.sqrt(b["See"][i])
        tze = abs(complex(b["Tze"][0][i], b["Tze"][1][i]))
        tzu = abs(complex(b["Tzu"][0][i], b["Tzu"][1][i]))
        tzm = abs(complex(b["Tzm"][0][i], b["Tzm"][1][i]))
        tzy = abs(complex(b["Tzy"][0][i], b["Tzy"][1][i]))
        tsr = abs(complex(b["Tzsr"][0][i], b["Tzsr"][1][i]))
        print(f"{f[i]:6.3f} {zz:9.4g} {ee:9.4g} {b['g2'][i]:9.3f} {tze:7.3f} {tzu:8.4f} {tzm:7.3f} {tzy:7.3f} {tsr:8.3f}")

    print("\nFAMILY COMPARISON of coh(Z,E) and Szz in the probe band")
    qs = [0.39, 0.59, 0.78, 0.98, 1.17, 1.37, 1.56, 1.76, 1.95, 2.34]
    j = [int(np.argmin(np.abs(f - q))) for q in qs]
    print(f"{'fam':7s} {'n':>4s} " + " ".join(f"{f[i]:>7.2f}" for i in j))
    for fam in fams:
        if fam not in store:
            continue
        print(f"{fam:7s} {store[fam]['n']:4d} g2 " + " ".join(f"{store[fam]['g2'][i]:7.3f}" for i in j))
        print(f"{'':7s} {'':4s} Zr " + " ".join(f"{np.sqrt(store[fam]['Szz'][i]):7.4g}" for i in j))
    print("\nwrote out/d1_budget.json")
