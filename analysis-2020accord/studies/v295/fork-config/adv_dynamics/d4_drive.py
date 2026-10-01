# -*- coding: utf-8 -*-
"""d4_drive -- ADV-dynamics (c)(d): r71b replay, fork = the REAL LatControlTorque (harness real_fork mode), one batch
per config with an identical row layout and seed (paired sensor noise).  Configs V294+r1 / V295+r1 / V295+r2alt.
Metrics = the harness's drive_metrics (same code as the drive) + my straight-line / weave / hard-turn / oversteer reads."""
import os, sys, json, time
import numpy as np
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import d2_engine as E
import v295_harness as H
import fc_lib as FL

OUT = os.path.join(HERE, "out")
BANDS = tuple(H.BANDS) + (("8-22", 8.0, 22.0), ("17-27", 17.0, 27.0))
MEMBERS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["nominal", "b_lo", "F_hi", "J_hi", "light_b"]
DISTS = sys.argv[2].split(",") if len(sys.argv) > 2 else ["lp", "full"]
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 0
TAG = sys.argv[4] if len(sys.argv) > 4 else "main"


def run_config(cfg, members, dist, chunks, seed):
    cn, fn = E.CONFIGS[cfg]
    d = H.route()
    tg0 = d["toggles"]
    fam = H.family()
    B = len(members) * len(chunks)
    rows = [FL.Fork("x", ki_high=E.KIH[fn])] * B
    H.ForkPort = lambda B_, tg: FL.VecPort(B_, tg0, rows)  # noqa: E731   (a SHADOW only; the real code drives)
    d["toggles"] = dict(tg0, accord_torque_ki_high=E.KIH[fn])
    try:
        R = H.simulate([E.CELLS[cn]], [fam[m] for m in members], chunks,
                       H.SimOpts(mode="B", dist=dist, real_fork=True, null_shadow=True, seed=seed))
    finally:
        H.ForkPort = FL._OrigPort
        d["toggles"] = tg0
    return R


def extra(R, rows):
    """my reads: straight-line wheel-rate bands, weave, and oversteer at hard demand."""
    out = {}
    for nm, lo, hi in BANDS:
        acc = {k: [] for k in ("w", "s13", "s15", "big_pl", "big_ac", "c24")}
        for j in rows:
            n = R["lens"][j]
            v, r, pl, ac = R["v"][j, :n], R["rate18"][j, :n], R["la_plan"][j, :n], R["la_act"][j, :n]
            mk = (v >= lo) & (v < hi)
            cut = np.zeros(n, bool); cut[100:-100] = True
            st = mk & cut & (np.abs(pl) < 0.4)
            if st.sum() > 50:
                acc["w"].append(H._bp(r, 0.2, 1.5)[st]); acc["s13"].append(H._bp(r, 1.0, 3.0)[st])
                acc["s15"].append(H._bp(r, 1.0, 5.0)[st])
            cv = mk & cut & (np.abs(pl) >= 0.8)
            acc["c24"].append(H._bp(r, 2.0, 2.7)[cv])
            bg = mk & (np.abs(pl) >= 1.5)
            acc["big_pl"].append(pl[bg]); acc["big_ac"].append(ac[bg])
        res = {}
        for k in ("w", "s13", "s15", "c24"):
            a = np.concatenate(acc[k]) if acc[k] else np.zeros(0)
            res[k] = float(np.sqrt(np.mean(a ** 2))) if len(a) > 300 else float("nan")
        pl = np.concatenate(acc["big_pl"]) if acc["big_pl"] else np.zeros(0)
        ac = np.concatenate(acc["big_ac"]) if acc["big_ac"] else np.zeros(0)
        res["hold_big"] = float(np.median(ac / pl)) if len(pl) > 200 else float("nan")
        res["hold_big_p95"] = float(np.percentile(ac / pl, 95)) if len(pl) > 200 else float("nan")
        res["big_n"] = int(len(pl))
        out[nm] = res
    return out


def main():
    t0 = time.time()
    chunks = H.route_chunks()
    allres = {}
    for dist in DISTS:
        for cfg in ("V294+r1", "V295+r1", "V295+r2alt"):
            R = run_config(cfg, MEMBERS, dist, chunks, SEED)
            dev = float(np.max(R["port_vs_real_maxdev"]))
            for mi, m in enumerate(MEMBERS):
                rows = [mi * len(chunks) + k for k in range(len(chunks))]
                S = H.drive_series_sim(R, rows)
                dm = H.drive_metrics(S, band_list=BANDS)
                ex = extra(R, rows)
                for b in dm:
                    dm[b].update(ex.get(b, {}))
                lc = H.limit_cycle_peak(R, rows)
                div = bool(np.any(~np.isfinite(R["ang"][rows])) or np.nanmax(np.abs(R["ang"][rows])) > 720)
                allres["%s|%s|%s" % (dist, cfg, m)] = dict(bands=dm, lc=lc, diverged=div, n_bail=int(R["n_bail"][rows].sum()),
                                                          port_dev=dev)
            print("  %s %s done (%.0f s, port-vs-real max dev %.1e)" % (dist, cfg, time.time() - t0, dev), flush=True)
    json.dump(allres, open(os.path.join(OUT, "d4_drive_%s_seed%d.json" % (TAG, SEED)), "w"), indent=1)
    # ---------------- report
    L = []
    P = lambda s: (print(s), L.append(s))  # noqa: E731
    key = lambda dist, cfg, m: allres["%s|%s|%s" % (dist, cfg, m)]  # noqa: E731
    for dist in DISTS:
        P("\n==== dist %s (seed %d) ====" % (dist, SEED))
        for m in MEMBERS:
            P("-- %s" % m)
            P("   band   | trk V294r1 V295r1 r2alt  (d)    | hold V294r1 V295r1 r2alt (d)    | holdBig r1/r2alt | J V295r1->r2alt | "
              "hard16 V294r1 V295r1 r2alt (x vs V295r1, x vs V294r1) | s13 x | weave x | c24 x | i_share d")
            for nm, _, _ in BANDS:
                a, b, c = (key(dist, cfg, m)["bands"].get(nm) for cfg in ("V294+r1", "V295+r1", "V295+r2alt"))
                if a is None or b is None or c is None:
                    continue
                rt = lambda x, y: (x / y if (y and np.isfinite(y) and y > 0) else float("nan"))  # noqa: E731
                P("   %-6s | %.3f %.3f %.3f (%+.3f) | %.3f %.3f %.3f (%+.3f) | %.3f/%.3f | %.3f->%.3f x%.2f | %.3f %.3f %.3f (x%.2f, x%.2f) | x%.2f | x%.2f | x%.2f | %+.3f" % (
                    nm, a["track_gain"], b["track_gain"], c["track_gain"], c["track_gain"] - b["track_gain"],
                    a["turn_hold"], b["turn_hold"], c["turn_hold"], c["turn_hold"] - b["turn_hold"],
                    b["hold_big"], c["hold_big"], b["J_err"], c["J_err"], rt(c["J_err"], b["J_err"]),
                    a["hard16"], b["hard16"], c["hard16"], rt(c["hard16"], b["hard16"]), rt(c["hard16"], a["hard16"]),
                    rt(c["s13"], b["s13"]), rt(c["w"], b["w"]), rt(c["c24"], b["c24"]), c["i_share"] - b["i_share"]))
            for cfg in ("V294+r1", "V295+r1", "V295+r2alt"):
                lc = key(dist, cfg, m)["lc"]
                P("   limit-cycle line 1-5 Hz %-11s f %.2f Hz  %+.1f dB  rms %.3f deg/s   diverged %s  bails %d" % (
                    cfg, lc["f"], lc["dB"], lc["rms"], key(dist, cfg, m)["diverged"], key(dist, cfg, m)["n_bail"]))
    open(os.path.join(OUT, "d4_drive_%s_seed%d_out.txt" % (TAG, SEED)), "w").write("\n".join(L) + "\n")
    print("runtime %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
