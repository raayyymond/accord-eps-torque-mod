# -*- coding: utf-8 -*-
"""POSITIVE CONTROL for the feedforward reconstruction.

Rebuilds the WHOLE ff_torque the fork computed, at the gain each route actually flew, and compares
it to the LOGGED feedforward `pid_log.f / latAccelFactor`.  Also checks the instrument identity
    pid_log.output == -clip(p + i + f) / LAF
which pins latAccelFactor and full scale from the log itself rather than from a toggle.

Nothing in sweep.py is reported unless this passes.
ANALYSIS ONLY.  Run: python validate.py
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))           # v282cmp
import ffrecon as F                                  # noqa: E402
import v282cmp as C                                  # noqa: E402

CACHE = C.CACHE


def load(route):
    """Everything on the controlsState clock, plus the two fields v282cmp.load does not expose
    (liveParameters.stiffnessFactor, liveTorqueParameters.latAccelOffsetFiltered)."""
    D = np.load(CACHE / f"{route}.npz", allow_pickle=True)
    t = D["t_cs"]

    def I(tk, k, dflt=np.nan):
        if tk in D.files and k in D.files and len(D[tk]):
            return np.interp(t, D[tk], D[k])
        return np.full(len(t), dflt)

    v = I("t_cst", "vego")
    S = dict(route=route, t=t, v=v,
             active=(D["cs_active"] > 0.5) & (I("t_cc", "lat_active") > 0.5),
             pressed=I("t_cst", "spress") > 0.5,
             sa=I("t_cst", "sa_deg"), sr=I("t_cst", "sr_deg"), aoff=I("t_lp", "aoff", 0.0),
             setpoint=D["cs_la_des"], model=D["cs_des_curv"] * v * v,
             out=D["cs_out"], p=D["cs_p"], i=D["cs_i"], f=D["cs_f"], sat=D["cs_sat"] > 0.5,
             roll=I("t_lp", "roll", 0.0), stiff=I("t_lp", "stiff", 1.0),
             lao=I("t_lt", "lao_f", 0.0))
    return S


def instrument_check(S, laf):
    """pid_log.output must equal -clip(p+i+f, -LAF, +LAF)/LAF frame by frame."""
    m = S["active"]
    pre = (S["p"] + S["i"] + S["f"])[m]
    got = S["out"][m]
    pred = -np.clip(pre, -laf, laf) / laf
    err = np.abs(pred - got)
    # fit LAF from the unsaturated frames instead of trusting the toggle
    un = np.abs(pre) < 0.98 * laf
    lf = float(np.dot(pre[un], -got[un]) / max(np.dot(-got[un], -got[un]), 1e-30))
    return dict(n=int(m.sum()), max_err=float(err.max()), p99=float(np.percentile(err, 99)),
                frac_gt_1e3=float((err > 1e-3).mean()), laf_fit=lf,
                frac_at_fs=float((np.abs(got) >= 0.999).mean()))


def build_ff(S, cfg, use_offset):
    tab = F.TABLES[cfg["commit"]]
    ad, adr, d_ad, dt = F.build_demand(S, cfg, use_offset)
    hold = F.hold_term(ad, S["v"], cfg, tab)
    mv, raw, lim = F.move_term(adr, S["v"], cfg["gain"], tab)
    z, rl, dob = F.build_inner(S, cfg, tab, ad, adr, d_ad, dt)
    # latcontrol_torque.py:  ff_torque = -(hold+move) + -(z + rl) + -dob      (friction_torque = 0
    # whenever AccordFrictionHyst > 0; on r70/r71 the hysteresis term did not exist)
    ff = -(hold + mv) - (z + rl) - dob
    return dict(ad=ad, adr=adr, hold=hold, move=mv, raw=raw, lim=lim, z=z, rl=rl, dob=dob, ff=ff, dt=dt)


def score(ff_model, ff_log, m):
    a, b = ff_model[m], ff_log[m]
    r = float(np.corrcoef(a, b)[0, 1])
    sl = float(np.dot(a, b) / max(np.dot(a, a), 1e-30))
    res = float(np.std(b - a) / max(np.std(b), 1e-30))
    return r, sl, res


if __name__ == "__main__":
    print(F._self_test())
    print()
    print("=" * 112)
    print("INSTRUMENT CHECK:  pid_log.output == -clip(p+i+f, +/-LAF)/LAF   (full scale = 1.0 torque)")
    print("=" * 112)
    print(f"{'route':10s} {'rev':22s} {'n frames':>9s} {'max err':>9s} {'p99 err':>9s} "
          f"{'frac>1e-3':>10s} {'LAF fitted':>11s} {'LAF toggle':>11s} {'frac at FS':>11s}")
    for rk, cfg in F.ROUTECFG.items():
        if not (CACHE / f"{rk}.npz").exists():
            print(f"{cfg['tag']:10s} {cfg['rev']:22s}   NO CACHE")
            continue
        S = load(rk)
        r = instrument_check(S, cfg["laf"])
        print(f"{cfg['tag']:10s} {cfg['rev']:22s} {r['n']:9d} {r['max_err']:9.2e} {r['p99']:9.2e} "
              f"{r['frac_gt_1e3']:10.4f} {r['laf_fit']:11.4f} {cfg['laf']:11.2f} {r['frac_at_fs']:11.5f}")
        del S

    print()
    print("=" * 112)
    print("RECONSTRUCTION OF THE WHOLE ff_torque AT THE FLOWN GAIN vs LOGGED pid_log.f / LAF")
    print("=" * 112)
    print(f"{'route':10s} {'offset':7s} {'corr':>8s} {'slope':>8s} {'resid/sig':>10s} "
          f"{'rms err':>9s} {'|ff| p99':>9s}   speed band")
    for rk, cfg in F.ROUTECFG.items():
        if not cfg["ff_live"] or not (CACHE / f"{rk}.npz").exists():
            continue
        S = load(rk)
        for use_off in (False, True):
            c = build_ff(S, cfg, use_off)
            ff_log = S["f"] / cfg["laf"]
            for lo, hi, nm in ((0.0, 99.0, "all"), (2.0, 8.0, "2-8"), (8.0, 15.0, "8-15"), (15.0, 99.0, ">15")):
                m = S["active"] & ~S["pressed"] & (S["v"] >= lo) & (S["v"] < hi)
                if m.sum() < 500:
                    continue
                r, sl, res = score(c["ff"], ff_log, m)
                rms = float(np.sqrt(np.mean((ff_log[m] - c["ff"][m]) ** 2)))
                print(f"{cfg['tag']:10s} {'ON' if use_off else 'OFF':7s} {r:8.4f} {sl:8.3f} {res:10.3f} "
                      f"{rms:9.4f} {float(np.percentile(np.abs(ff_log[m]), 99)):9.3f}   {nm}")
            del c
        del S
        print()
