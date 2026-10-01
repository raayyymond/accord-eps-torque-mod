# -*- coding: utf-8 -*-
"""f2: the OUTER-LOOP linear screen (gates G1, G2, G3) over the fork-knob grid, on V295 cells, with V294+r1 and V295+r1
as references.  L_o(f) = K(f) * Cf(f) (H.outer_frf), and K(f) * LAF depends only on (cells, member, v) -- so K is computed
once per (member, v) with H.outer_frf itself and every candidate is exact algebra on it (checked against a direct
H.outer_frf call for 40 random candidates: second method).
G3 (describing function): the SteerFriction term is a saturation of slope F/0.30*(1+lsf/Kp) (torque per m/s^2) in
parallel with P+I; its DF N(A) lies in (0, slope], so a limit cycle needs the linear loop with the relay gain k to be
marginal for some k in (0, slope].  The gate sweeps k in [0, 2 x slope] (x2 amplitude margin) and requires stability
(GM > 1 and PM > 0 at every crossing) throughout."""
import sys, json, itertools, time
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/fork-config")
import numpy as np
import fc_lib as F
H = F.H

fam = H.family()
c294, c295 = H.Cells.v294(), F.cells_v295()
MEMBERS = list(F.ID_MEMBERS) + ["light_b"]
SPEEDS = F.SPEEDS
FG = F.FG
z100 = np.exp(2j * np.pi * FG * 0.01)
I_T = 0.01 / (1 - 1 / z100)


def K_table(cells):
    """K(f) * LAF for every (member, v), via H.outer_frf with a unit fork (Kp 1, Ki 0, LAF 1, friction 0): Cf = 1+lsf."""
    out = {}
    for m in MEMBERS:
        for v in SPEEDS:
            tg = {"steerKp": [[0], [1.0]], "accord_torque_ki": 0.0, "latAccelFactor": 1.0, "friction": 0.0}
            L = H.outer_frf(cells, fam[m].at(v), v, FG, relay=False, toggles=tg)
            out[(m, v)] = L / (1 + F.lsf_of(v))
    return out


def L_of(K1, fork, v, relay_mult=1.0):
    kp, ki = fork.kp, float(fork.ki_at(v))
    laf, fric = float(np.float32(fork.laf)), float(np.float32(fork.fric))
    Cf = (kp + ki * I_T + relay_mult * fric * laf / 0.30) * (1 + F.lsf_of(v) / kp)
    return K1 / laf * Cf


def mg(L):
    m = H.margins(FG, L)
    return m["Ms"], m["GM_min"], m["PM_min"], m["f_Ms"]


def screen(K, fork, ref_gm=None, ref_lb=None, dfs=(0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0)):
    """returns dict of per (member, v) margins and the gate verdicts."""
    res, fails = {}, []
    for (m, v), K1 in K.items():
        Ms, GM, PM, fMs = mg(L_of(K1, fork, v, 1.0))
        res[(m, v)] = (Ms, GM, PM, fMs)
        if m in F.ID_MEMBERS:
            if Ms > 1.6 or GM < 3.0 or PM < 35.0:
                fails.append("G1 %s %.1f Ms %.2f GM %.2f PM %.0f" % (m, v, Ms, GM, PM))
            if ref_gm is not None and GM < min(ref_gm[(m, v)], 1.5):
                fails.append("G1b %s %.1f GM %.2f < min(ref, 1.5)" % (m, v, GM))
        if m == "light_b" and v >= 17.0 and ref_lb is not None:
            rMs, rGM = ref_lb[v]
            if GM < 0.97 * rGM or Ms > 1.10 * rMs:
                fails.append("G2 light_b %.1f GM %.2f (ref %.2f) Ms %.2f (ref %.2f)" % (v, GM, rGM, Ms, rMs))
        # G3: the DF sweep (all members incl. light_b)
        for kk in dfs:
            Ms_, GM_, PM_, _ = mg(L_of(K1, fork, v, kk))
            if not (GM_ > 1.0 and PM_ > 0.0):
                fails.append("G3 %s %.1f relay x%.2f unstable (GM %.2f PM %.0f)" % (m, v, kk, GM_, PM_))
                break
    return res, fails


if __name__ == "__main__":
    t0 = time.time()
    K295, K294 = K_table(c295), K_table(c294)
    print("K tables %.1f s" % (time.time() - t0))
    # second method: algebra == a direct H.outer_frf call (40 random candidates)
    rng = np.random.default_rng(1)
    worst = 0.0
    for _ in range(40):
        fk = F.Fork("t", kp=float(rng.uniform(0.4, 1.4)), ki=float(rng.uniform(0.1, 1.0)), ki_high=0.0,
                    laf=float(rng.uniform(8, 16)), fric=float(rng.uniform(0, 0.03)))
        m = MEMBERS[rng.integers(len(MEMBERS))]
        v = SPEEDS[rng.integers(len(SPEEDS))]
        Ld = H.outer_frf(c295, fam[m].at(v), v, FG, relay=True, toggles=fk.toggles(v))
        La = L_of(K295[(m, v)], fk, v, 1.0)
        worst = max(worst, float(np.max(np.abs(Ld - La) / np.maximum(np.abs(Ld), 1e-12))))
    print("second method: algebraic L vs direct H.outer_frf, 40 random candidates: max rel diff %.2e" % worst)
    # 5e-8 = LAF float32 (the fork's capnp field, mirrored here) vs outer_frf's float64 LAF: immaterial
    assert worst < 1e-6

    # references
    r294, _ = screen(K294, F.R1)
    r295, f295 = screen(K295, F.R1)
    print("\nREFERENCE margins (Ms / GM / PM@deg / f_Ms) -- V294+r1 | V295+r1, relay slope included")
    for m in MEMBERS:
        print("  %-8s" % m + "  ".join("%4.1f:%4.2f/%5.1f/%3.0f|%4.2f/%5.1f/%3.0f" % (v, *r294[(m, v)][:3], *r295[(m, v)][:3])
                                       for v in SPEEDS))
    print("V295+r1 against its own G1/G3 gates:", f295 or "PASS")
    ref_gm = {k: min(r294[k][1], r295[k][1]) for k in r295}
    ref_lb = {v: (r294[("light_b", v)][0], r294[("light_b", v)][1]) for v in SPEEDS}
    # relay share of the small-signal loop gain
    print("\nr1: P torque gain vs relay torque gain per m/s^2 of error, by speed:")
    for v in SPEEDS:
        print("   v %4.1f  lsf %6.2f  P %.4f  relay %.4f  (relay/P %.2f)  Ki_eff %.3f" % (
            v, F.lsf_of(v), F.p_gain_torque(F.R1, v), F.relay_slope_torque(F.R1, v),
            F.relay_slope_torque(F.R1, v) / F.p_gain_torque(F.R1, v), 0.3 * (1 + F.lsf_of(v) / 0.9) / 14.0))

    # the grid
    LAFs = (14.0, 13.0, 12.0, 11.0, 10.0, 9.0)
    KPs = (0.6, 0.7, 0.8, 0.9, 1.0, 1.1)
    FRs = (0.0, 0.004, 0.008, 0.011, 0.015, 0.02)
    KIs = ((0.3, 0.0), (0.45, 0.0), (0.6, 0.0), (0.3, 0.6), (0.3, 1.0), (0.3, 1.5), (0.45, 1.5), (0.3, 2.5), (0.6, 2.5))
    rows = []
    t0 = time.time()
    for laf, kp, fr, (ki, kih) in itertools.product(LAFs, KPs, FRs, KIs):
        fk = F.Fork("g", kp=kp, ki=ki, ki_high=kih, laf=laf, fric=fr)
        res, fails = screen(K295, fk, ref_gm, ref_lb)
        idm = [res[(m, v)] for m in F.ID_MEMBERS for v in SPEEDS]
        lb = [res[("light_b", v)] for v in SPEEDS]
        rows.append(dict(laf=laf, kp=kp, fric=fr, ki=ki, ki_high=kih, n_fail=len(fails), fails=fails[:6],
                         id_Ms=max(x[0] for x in idm), id_GM=min(x[1] for x in idm), id_PM=min(x[2] for x in idm),
                         lb_Ms=max(x[0] for x in lb), lb_GM=min(x[1] for x in lb),
                         lb_GM_hi=min(res[("light_b", v)][1] for v in (22.0, 26.9)),
                         lb_Ms_hi=max(res[("light_b", v)][0] for v in (22.0, 26.9))))
    print("\ngrid %d candidates in %.1f s" % (len(rows), time.time() - t0))
    ok = [r for r in rows if r["n_fail"] == 0]
    print("PASS G1-G3: %d / %d" % (len(ok), len(rows)))
    for laf in LAFs:
        for (ki, kih) in KIs:
            sub = [r for r in ok if r["laf"] == laf and r["ki"] == ki and r["ki_high"] == kih]
            if not sub:
                continue
            kps = sorted(set(r["kp"] for r in sub))
            frs = sorted(set(r["fric"] for r in sub))
            print("  LAF %4.1f Ki %.2f/%.2f: pass Kp %s  F %s" % (laf, ki, kih, kps, frs))
    json.dump(dict(rows=rows, ref295={"|".join(map(str, k)): v for k, v in r295.items()},
                   ref294={"|".join(map(str, k)): v for k, v in r294.items()}),
              open("out/f2_outer.json", "w"), indent=1)
    # the binding constraints, for the LAF x Kp plane at F 0.011 / 0.0 and Ki 0.3 flat
    for fr in (0.011, 0.0):
        print("\nbinding gate by (LAF, Kp) at F %.3f, Ki 0.3 flat:" % fr)
        for laf in LAFs:
            s = []
            for kp in KPs:
                r = [x for x in rows if x["laf"] == laf and x["kp"] == kp and x["fric"] == fr and x["ki"] == 0.3 and x["ki_high"] == 0][0]
                s.append("Kp%.1f:%s" % (kp, "ok" if not r["n_fail"] else r["fails"][0].split()[0] + "(" + str(r["n_fail"]) + ")"))
            print("  LAF %4.1f  " % laf + "  ".join(s))
