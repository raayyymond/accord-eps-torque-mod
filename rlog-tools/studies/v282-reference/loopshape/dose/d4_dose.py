# -*- coding: utf-8 -*-
"""D4 -- the DOSE sweep: what each reachable loop parameter does to the identified loop.

This is ALGEBRA ON AN IDENTIFIED TRANSFER, which is allowed: the plant P_la(jw) is measured from
each route's own logged input and output, and the controller is the fork's own arithmetic with one
constant changed.  It says what the LOOP does.  It does NOT say what the car will feel like -- the
shake constraint is measured separately in d5_shake.py from flown data.

Reported currency: |S| = |1/(1+L)| power-averaged in the study's own exposure bands.  |S| is the
factor by which the feedback multiplies a tracking error that the feedforward left behind:
|S| = 1 means the loop removes nothing.  The three bands carry 8.7 % / 26.9 % / 63.9 % of the
measured d(NRMSE^2) gap.
"""
import json
import numpy as np
import dlib as D
from d1_ident import k_tot

FMAX = 1.2          # the identification's honest upper edge (d2: coherence)
COH = 0.50


def load(tag="hi"):
    return json.load(open(D.OUT / f"d1_{tag}.json"))


def metrics(v, **kw):
    f = np.array(v["f"])
    P = np.array(v["P_re"]) + 1j * np.array(v["P_im"])
    valid = np.array(v["valid"]) & (D.smooth_c(np.array(v["coh_ry"])) > COH)
    K = k_tot(f, v["cfg"], v["v"], v["k_m"], **kw)
    return D.loop_metrics(f, K * P, valid, fmax=FMAX)


def target(res):
    """V282's own |S| -- the operator's stated definition of 'good'."""
    rows = [metrics(v) for k, v in res.items() if v["cfg"]["g"] == "V282"]
    rows = [r for r in rows if r]
    return {k: float(np.median([r[k] for r in rows])) for k in
            ("S0.15_0.3", "S0.3_0.6", "S0.6_1.2", "Ms")}


def sweep(res, key, label, values, routes=None, **fixed):
    routes = routes or [k for k, v in res.items() if v["cfg"]["g"] in ("T5", "T64", "T64B")]
    print(f"\n--- {label} ---")
    print(f"{'dose':>8s} " + " ".join(f"{x:>18s}" for x in
          ("|S| 0.15-0.30", "|S| 0.30-0.60", "|S| 0.60-1.20")) + f" {'Ms':>16s} {'PM@fc':>14s}")
    out = []
    for val in values:
        rows = []
        for rt in routes:
            kw = dict(fixed)
            kw[key] = val
            m = metrics(res[rt], **kw)
            if m:
                rows.append(m)
        if not rows:
            continue
        g = lambda k: (np.median([r[k] for r in rows]), np.min([r[k] for r in rows]),
                       np.max([r[k] for r in rows]))
        s1, s2, s3, ms = g("S0.15_0.3"), g("S0.3_0.6"), g("S0.6_1.2"), g("Ms")
        pms = [r["pm"] for r in rows if np.isfinite(r["pm"])]
        pm = np.median(pms) if pms else float("nan")
        print(f"{val:8.2f} " + " ".join(f"{a:6.3f} [{b:5.3f},{c:5.3f}]" for a, b, c in (s1, s2, s3))
              + f" {ms[0]:5.2f} [{ms[1]:4.2f},{ms[2]:4.2f}] {pm:8.1f} (n={len(pms)})")
        out.append(dict(dose=val, S1=s1[0], S2=s2[0], S3=s3[0], Ms=ms[0], pm=float(pm)))
    return out


def main():
    res = load("hi")
    tgt = target(res)
    print("TARGET -- V282's own median |S| at >=15 m/s (what 'good' measured like):")
    print(f"   |S| 0.15-0.30 Hz {tgt['S0.15_0.3']:.3f}   0.30-0.60 {tgt['S0.3_0.6']:.3f}"
          f"   0.60-1.20 {tgt['S0.6_1.2']:.3f}   Ms {tgt['Ms']:.2f}")
    print("\nFLOWN, per route (>=15 m/s, coherence-gated, <=1.2 Hz):")
    print(f"{'route':22s} {'grp':8s} {'kp/LAF':>7s} " + " ".join(f"{x:>9s}" for x in
          ("S.15-.3", "S.3-.6", "S.6-1.2", "Ms", "fc", "PM")))
    for rt, v in res.items():
        m = metrics(v)
        if not m:
            continue
        c = v["cfg"]
        print(f"{rt:22s} {c['g']:8s} {c['kp']/c['laf']:7.4f} "
              + " ".join(f"{m[k]:9.3f}" for k in ("S0.15_0.3", "S0.3_0.6", "S0.6_1.2", "Ms"))
              + f" {m['fc']:9.2f} {m['pm']:9.1f}")

    R = {}
    R["kp"] = sweep(res, "kp_mult", "SteerKP multiplier (rev 5 / rev 6.4 routes; flown kp = 1.0)",
                    [1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0])
    R["kp_norl"] = sweep(res, "kp_mult",
                         "SteerKP multiplier WITH THE RATE LOOP AND OBSERVER OFF (isolates SteerKP)",
                         [1.0, 1.5, 2.0, 3.0, 4.0, 6.0], rl_mult=0.0, dob_mult=0.0)
    R["ki"] = sweep(res, "ki_mult", "AccordTorqueKi multiplier (flown 0.30)",
                    [1.0, 2.0, 3.0, 5.0, 8.0])
    R["rl"] = sweep(res, "rl_mult", "AccordRateLoopGain multiplier (flown 0.001, toggle-capped ~1.5x)",
                    [0.0, 1.0, 1.5, 2.0, 3.0])
    R["dob"] = sweep(res, "dob_mult", "AccordDobHz multiplier (flown 0.6 Hz)",
                     [0.0, 0.5, 1.0, 1.5, 2.0, 3.0])
    # LAF is the OTHER way to raise kp/LAF: it scales P, I and the loop together (P_la = P_tq/LAF)
    print("\n--- SteerLatAccel (LAF): scales P_la = P_tq/LAF, so it moves P, I and the observer "
          "gain together, and it also rescales the feedforward torque ---")
    print(f"{'LAF':>8s} {'kp/LAF':>8s} " + " ".join(f"{x:>18s}" for x in
          ("|S| 0.15-0.30", "|S| 0.30-0.60", "|S| 0.60-1.20")) + f" {'Ms':>16s}")
    laf_rows = []
    for laf in (14.0, 12.0, 10.0, 8.0, 6.0, 4.0):
        rows = []
        for rt in [k for k, v in res.items() if v["cfg"]["g"] in ("T5", "T64", "T64B")]:
            v = res[rt]
            f = np.array(v["f"])
            P = (np.array(v["P_re"]) + 1j * np.array(v["P_im"])) * v["cfg"]["laf"] / laf
            valid = np.array(v["valid"]) & (D.smooth_c(np.array(v["coh_ry"])) > COH)
            cfg = dict(v["cfg"]); cfg["laf"] = laf
            K = k_tot(f, cfg, v["v"], v["k_m"])
            m = D.loop_metrics(f, K * P, valid, fmax=FMAX)
            if m:
                rows.append(m)
        g = lambda k: (np.median([r[k] for r in rows]), np.min([r[k] for r in rows]),
                       np.max([r[k] for r in rows]))
        s1, s2, s3, ms = g("S0.15_0.3"), g("S0.3_0.6"), g("S0.6_1.2"), g("Ms")
        print(f"{laf:8.1f} {1.0/laf:8.4f} "
              + " ".join(f"{a:6.3f} [{b:5.3f},{c:5.3f}]" for a, b, c in (s1, s2, s3))
              + f" {ms[0]:5.2f} [{ms[1]:4.2f},{ms[2]:4.2f}]")
        laf_rows.append(dict(laf=laf, S1=s1[0], S2=s2[0], S3=s3[0], Ms=ms[0]))
    R["laf"] = laf_rows
    R["target"] = tgt
    json.dump(R, open(D.OUT / "d4_sweep.json", "w"), indent=1)


if __name__ == "__main__":
    main()
