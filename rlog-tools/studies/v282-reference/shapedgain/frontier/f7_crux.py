# -*- coding: utf-8 -*-
"""f7 -- the crux checks on the frontier, and the tiered answer.

1. PER-FREQUENCY picture of the headline configs: what the notch and the gain each do, where.
2. The frontier RE-RUN under three independent perturbations of the two modelled objects, to see
   whether the RANKING survives:  (a) V forced to 1.0 above 1 Hz, (b) the loop base taken as
   L_tot (the whole feedback path, which over-reads) instead of L_pid, (c) the metric's V282
   reference taken as my own 0.471 instead of the brief's 0.442.
3. TIERS.  A config is only defensible if its crossover stays inside the band where the logs can
   see phase.  Tier A: wc <= 0.50 Hz (coh(Z,U) >= 0.85 there, delay phase <= 12 deg).
   Tier B: wc up to 1.2 Hz -- reported, flagged, NOT defended.
4. The low-speed consequence of every headline config, since the metric only sees >= 15 m/s.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
sys.path.insert(0, str(HERE.parents[1] / "loopshape" / "loopshape"))
import lp_lib as LP                                        # noqa: E402
from f5_frontier import Engine, C_of, FLOWN                # noqa: E402

HEAD = [
    ("as flown           ", 1.0, 14.0, 0.0, 1.00),
    ("ARM-KP  SteerKP 2.0", 2.0, 14.0, 0.0, 1.00),
    ("SteerKP 3.0        ", 3.0, 14.0, 0.0, 1.00),
    ("KP3.0 + Q0.70      ", 3.0, 14.0, 0.0, 0.70),
    ("KP3.0 + Q0.50      ", 3.0, 14.0, 0.0, 0.50),
    ("KP3.0 + Q0.35      ", 3.0, 14.0, 0.0, 0.35),
    ("KP3.0 LAF10 Q0.50  ", 3.0, 10.0, 0.0, 0.50),
    ("KP3.0 LAF8  Q0.40  ", 3.0, 8.0, 0.0, 0.40),
    ("KP3.0 LAF8  Q0.30  ", 3.0, 8.0, 0.0, 0.30),
    ("KP3.0 LAF7  Q0.50 Ki2.5", 3.0, 7.0, 2.5, 0.50),
]


def run_with(eng, kp, laf, kih, q, Vmode="h1", Lbase="pid", ref=0.442):
    C1 = C_of(eng.f, eng.v, kp, laf, FLOWN["ki"], kih, q)
    K = C1 / eng.C0
    L0 = eng.L0 if Lbase == "pid" else eng.Ltot
    L1 = L0 * K
    rho = (1.0 + L0) / (1.0 + L1)
    Vv = eng.V.copy()
    if Vmode == "unit":
        Vv[:, eng.f > 1.0] = 1.0
    E1 = eng.E + Vv * eng.D * (rho - 1.0)
    U1 = eng.UFF + eng.UFB * K * rho
    m = float(np.sum(np.abs(E1[:, eng.b]) ** 2)) / eng.px
    return dict(metric=m, closure=(1.3512 - m) / (1.3512 - ref),
                shake_cmd=float(np.sqrt(np.sum(np.abs(U1[:, eng.shk]) ** 2) / eng.pu_shk)),
                shake_L=float(np.mean(np.abs(L1[:, eng.shj]))),
                L1=L1, K=K, rho=rho,
                bands=[float(np.sum(np.abs(E1[:, s]) ** 2)) / eng.px for s in eng.sb])


def margins(eng, L1):
    Lm = np.mean(L1, axis=0)
    sel = (eng.f >= 0.10) & (eng.f <= 3.5)
    ff, LL = eng.f[sel], Lm[sel]
    mag = np.abs(LL)
    ph = np.unwrap(np.angle(LL))
    wc = pm = np.nan
    x = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0]
    if len(x):
        k0 = x[0]
        w = np.log(mag[k0]) / (np.log(mag[k0]) - np.log(mag[k0 + 1]))
        wc = float(ff[k0] + w * (ff[k0 + 1] - ff[k0]))
        pm = float(180.0 + np.degrees(np.angle(np.exp(1j * np.interp(wc, ff, ph)))))
    Sm = np.abs(1.0 / (1.0 + np.mean(L1, axis=0)))
    ms = (eng.f >= 0.10) & (eng.f <= 2.5)
    return wc, pm, float(np.max(Sm[ms])), float(eng.f[ms][int(np.argmax(Sm[ms]))])


if __name__ == "__main__":
    eng = Engine()
    S = json.load(open(OUT / "f3_ident.json"))
    eng.Ltot = np.empty_like(eng.L0)
    for tag, lo, hi in (("15-22", 15.0, 22.0), ("22+", 22.0, 99.0)):
        D = S[f"T64|{tag}"]
        Lt = np.array(D["L_tot"][0]) + 1j * np.array(D["L_tot"][1])
        eng.Ltot[(eng.v >= lo) & (eng.v < hi)] = Lt

    print("1. PER-FREQUENCY.  |L| of the whole loop, window-averaged; 'K' = |C_new/C_old|.")
    fq = [0.20, 0.29, 0.39, 0.59, 0.78, 0.98, 1.46, 1.95, 2.54, 3.03]
    jj = [int(np.argmin(np.abs(eng.f - q))) for q in fq]
    print(f"{'config':24s} " + " ".join(f"{q:>6.2f}" for q in fq))
    for name, kp, laf, kih, q in HEAD:
        r = run_with(eng, kp, laf, kih, q)
        Lm = np.mean(np.abs(r["L1"]), axis=0)
        print(f"{name:24s} " + " ".join(f"{Lm[j]:6.3f}" for j in jj))
    print(f"{'  V282 reference |L|':24s} " + " ".join("     -" for _ in fq))
    Dv = S["V282|15+"]
    Lv = np.abs(np.array(Dv["L_pid"][0]) + 1j * np.array(Dv["L_pid"][1]))
    fv = np.array(Dv["f"])
    print(f"{'  (V282 measured)':24s} " + " ".join(f"{Lv[int(np.argmin(np.abs(fv-q)))]:6.3f}" for q in fq))
    print()
    print("   |C_new/C_old| -- where each config puts its gain")
    print(f"{'config':24s} " + " ".join(f"{q:>6.2f}" for q in fq))
    for name, kp, laf, kih, q in HEAD:
        r = run_with(eng, kp, laf, kih, q)
        Km = np.mean(np.abs(r["K"]), axis=0)
        print(f"{name:24s} " + " ".join(f"{Km[j]:6.2f}" for j in jj))
    print()
    print("2. HEADLINE TABLE with margins, bands and the low-speed consequence")
    print(f"{'config':24s} {'metric':>7s} {'clos%':>6s} {'shkCmd':>7s} {'shkL':>6s} {'Ms':>5s} "
          f"{'f_Ms':>5s} {'wc':>6s} {'PM':>4s} | bands .15-.3 .3-.6 .6-1.2 1.2-2.4 | P-gain x at 2/8/20 m/s")
    out = {}
    for name, kp, laf, kih, q in HEAD:
        r = run_with(eng, kp, laf, kih, q)
        wc, pm, ms, fms = margins(eng, r["L1"])
        lsr = [(kp + LP.low_speed_factor(vv)) / laf / ((1.0 + LP.low_speed_factor(vv)) / 14.0) for vv in (2.0, 8.0, 20.0)]
        print(f"{name:24s} {r['metric']:7.3f} {r['closure']*100:6.1f} {r['shake_cmd']:7.3f} {r['shake_L']:6.3f} "
              f"{ms:5.2f} {fms:5.2f} {wc:6.3f} {pm:4.0f} | " + " ".join(f"{b:6.3f}" for b in r["bands"])
              + " | " + " ".join(f"{x:5.2f}" for x in lsr))
        out[name.strip()] = dict(kp=kp, laf=laf, ki_hi=kih, q=q, metric=r["metric"], closure=r["closure"],
                                 shake_cmd=r["shake_cmd"], shake_L=r["shake_L"], Ms=ms, f_Ms=fms, wc=wc, pm=pm,
                                 bands=r["bands"], lowspeed_Pgain=lsr)
    print()
    print("3. ROBUSTNESS of the closure numbers to the two modelled objects")
    print(f"{'config':24s} {'base':>7s} {'V=1 >1Hz':>9s} {'L_tot base':>11s} {'ref 0.471':>10s}")
    for name, kp, laf, kih, q in HEAD:
        a = run_with(eng, kp, laf, kih, q)
        b = run_with(eng, kp, laf, kih, q, Vmode="unit")
        c = run_with(eng, kp, laf, kih, q, Lbase="tot")
        d = run_with(eng, kp, laf, kih, q, ref=0.471)
        print(f"{name:24s} {a['closure']*100:7.1f} {b['closure']*100:9.1f} {c['closure']*100:11.1f} {d['closure']*100:10.1f}")
    json.dump(out, open(OUT / "f7_head.json", "w"), indent=1)
