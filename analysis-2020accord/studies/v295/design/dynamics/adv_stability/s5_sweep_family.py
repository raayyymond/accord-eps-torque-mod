# -*- coding: utf-8 -*-
"""s5_sweep_family.py -- adversary `stability`: attack surface (e) "does A1017 move the complaints in the claimed
direction across the WHOLE family, or only on the designer's 6 members?"  Uses the shared harness's closed-loop engine
(H.simulate, mode B, the real-fork port) -- spot-checked first: the V294 nominal `lp` tracking-gain row must reproduce
the harness report's 0.840 / 0.865 / 0.586 / 0.764 / 0.917 (V295-HARNESS.md section 6) before anything is read.

Members: every harness family member (identified + corners + light_b + stress) PLUS my own corners the designer did
not run: light_b with J x0.5 / x2.5, light_b with b x0.5, light_b with 6 ms delay, nominal with J 0.5 NOT refitted.
Candidate and V294 in the SAME batch, dists full and lp.  Output: s5_sweep_family.json / _out.txt.
"""
import json
import os
import sys
import time
from dataclasses import replace

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "design", "harness"))
import v295_harness as H  # noqa: E402


def members():
    fam = H.family()
    out = dict(fam)
    lb = fam["light_b"]
    out["lb_J0.5x"] = replace(lb, name="lb_J0.5x", J=lb.J * 0.5)
    out["lb_J2.5x"] = replace(lb, name="lb_J2.5x", J=lb.J * 2.5)
    out["lb_b0.5x"] = replace(lb, name="lb_b0.5x", b=lb.b * 0.5)
    out["lb_tau6"] = replace(lb, name="lb_tau6", tau_ms=6)
    nom = fam["nominal"]
    out["nom_J0.5nr"] = replace(nom, name="nom_J0.5nr", J=np.full(len(nom.J), 0.5))
    for k in out:
        if not hasattr(out[k], "kappa"):
            out[k].kappa = False
    out["nominal_kappa"].kappa = True
    return out


def main():
    t0 = time.time()
    base = H.Cells.v294()
    cand = base.replace(fb_a=1017, name="A1017")
    assert cand.problems() == [], cand.problems()
    fam = members()
    names = list(fam.keys())
    chunks = H.route_chunks()
    lines = []
    pr = lambda *a: (print(*a, flush=True), lines.append(" ".join(str(x) for x in a)))  # noqa: E731
    pr("s5 sweep: %d members %s, %d chunks" % (len(names), names, len(chunks)))
    res = {}
    KEYS = ("track_gain", "turn_hold", "straight_delivery", "i_share", "cmd_rms", "r_lo", "r_mid", "r_hi", "hard16", "J_err")
    for dist in ("lp", "full"):
        # batches of members to bound memory
        for g0 in range(0, len(names), 6):
            grp = names[g0:g0 + 6]
            mem = [fam[n] for n in grp]
            R = H.simulate([base, cand], mem, chunks, H.SimOpts(mode="B", dist=dist))
            nM, nK = len(mem), len(chunks)
            for ci, cname in enumerate(("V294", "A1017")):
                for mi, mn in enumerate(grp):
                    rows = [ci * nM * nK + mi * nK + k for k in range(nK)]
                    dm = H.drive_metrics(H.drive_series_sim(R, rows))
                    dm["limit_cycle"] = H.limit_cycle_peak(R, rows)
                    res[(dist, cname, mn)] = dm
            pr("  %s members %s done  %.0f s  (bails %d)" % (dist, grp, time.time() - t0, int(R["n_bail"].sum())))
    meas = H.drive_metrics(H.drive_series_measured(chunks))
    # ---- spot check: the V294 nominal lp tracking-gain row
    want = dict(zip([b[0] for b in H.BANDS], (0.840, 0.865, 0.586, 0.764, 0.917)))
    got = {b: res[("lp", "V294", "nominal")][b]["track_gain"] for b in want if b in res[("lp", "V294", "nominal")]}
    ok = all(abs(got[b] - want[b]) <= 0.002 for b in got)
    pr("SPOT CHECK harness retrodiction row (V294, nominal, lp, tracking gain): got %s want %s -> %s" % (
        {k: round(v, 3) for k, v in got.items()}, want, "PASS" if ok else "FAIL"))
    pr("measured (drive): " + "  ".join("%s tg %.3f th %.3f hard %.2f rmid %.2f" % (
        b, meas[b].get("track_gain", np.nan), meas[b].get("turn_hold", np.nan), meas[b].get("hard16", np.nan),
        meas[b].get("r_mid", np.nan)) for b in meas))
    # ---- ratio tables
    for dist in ("full", "lp"):
        pr("\n==== dist %s: A1017 / V294 (ratio) and difference for gains" % dist)
        pr("%-13s %-6s %8s %8s %8s %8s %8s %8s %8s %10s" % ("member", "band", "hard16", "r_mid", "r_lo", "r_hi", "J_err",
                                                           "dTG", "dTH", "LC dB V/A"))
        for mn in names:
            v = res[(dist, "V294", mn)]
            a = res[(dist, "A1017", mn)]
            for b in v:
                if b == "limit_cycle":
                    continue
                rat = lambda k: a[b][k] / v[b][k] if (k in a[b] and v[b].get(k) and np.isfinite(v[b][k]) and v[b][k] != 0) else np.nan  # noqa: E731
                d = lambda k: a[b][k] - v[b][k] if k in a[b] else np.nan  # noqa: E731
                pr("%-13s %-6s %8.3f %8.3f %8.3f %8.3f %8.3f %+8.4f %+8.4f %5.1f/%4.1f" % (
                    mn, b, rat("hard16"), rat("r_mid"), rat("r_lo"), rat("r_hi"), rat("J_err"), d("track_gain"),
                    d("turn_hold"), v["limit_cycle"]["dB"], a["limit_cycle"]["dB"]))
    json.dump(H.to_jsonable(dict(res=res, measured=meas, names=names)), open(os.path.join(HERE, "s5_sweep_family.json"), "w"))
    open(os.path.join(HERE, "s5_sweep_family_out.txt"), "w").write("\n".join(lines) + "\n")
    pr("total %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
