# -*- coding: utf-8 -*-
"""studies/grind/v283_grind_census.py -- the GRINDING read on r36/r37/r38 (V283 = V282 + Ki 50) against
r35 (V281 rev 3) and r34 (V280 rev 2).  Subagent grind283, 2026-09-03.  Analysis only.

Three questions, in the operator's terms:
  1. the 18-22 Hz creep line he calls grinding / micro-ratcheting: how OFTEN (episodes per 100 s of engaged
     hands-off creep) and how BIG (bar 18-22 raw), speed- and idx-matched against r35 and r34.
  2. is there a PRONOUNCED incident of the r35 23:48:21 kind (a ~1 s exponential burst of the 20 Hz mode
     at a loaded turn start)?  Every candidate is ranked and the top ones characterised.
  3. does Ki 50 touch the grind?  Pre-registered as ~0 at 20 Hz (PREREG-V283-READ.md statistic (f)).
     r35 vs r36/r37/r38 differ ONLY in Ki (0 -> 50) plus the read-only cave, so this is a clean contrast.

Census method is r35's, unchanged (grind_incident_r35.py section 3): 2 s windows, step 0.5 s, engaged
LATERAL, v < 6 m/s; "line present" = most prominent 15-26 Hz peak with prominence >= 8 AND bar 18-22 >= 40 raw.
Run: python v283_grind_census.py     (writes _scratch/v283_grind_census.txt beside it)
"""
import os
import sys

import numpy as np
from scipy import signal, stats

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402
import v280_map_profiles as V                 # noqa: E402
import _grind2_lib as G2                      # noqa: E402
from v282_r24_tap_read import read_cells, demand_live, IMG, BUILD, V283_ROUTES, line_of, band   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FST = 100.0, 50.0
CACHE = C20.CACHE
ALL = ("r36", "r37", "r38", "r35", "r34")
GRP = {"r36": "V283", "r37": "V283", "r38": "V283", "r35": "V281r3", "r34": "V280r2"}
W, STEP = 200, 50          # 2 s windows, 0.5 s step -- r35's census, unchanged
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def envelope(x, f0, fs, bw=2.0):
    y = C20.bandpass(x, max(f0 - bw, 1.0), f0 + bw, fs)
    return np.abs(signal.hilbert(y))


def growth_fit(t, env):
    """log-envelope slope on the rise (10 %->90 % of the peak) and on the decay."""
    if len(env) < 20 or not np.isfinite(env).all() or env.max() <= 0:
        return np.nan, np.nan
    k = int(np.argmax(env)); pk = env[k]
    up = np.flatnonzero((env[:k + 1] >= 0.10 * pk) & (env[:k + 1] <= 0.95 * pk))
    dn = k + np.flatnonzero(env[k:] >= 0.10 * pk)
    gu = np.polyfit(t[up], np.log(np.maximum(env[up], 1e-6)), 1)[0] if len(up) >= 8 else np.nan
    gd = np.polyfit(t[dn], np.log(np.maximum(env[dn], 1e-6)), 1)[0] if len(dn) >= 8 else np.nan
    return gu, gd


def main():
    cells = {k: read_cells(p) for k, p in IMG.items()}
    G = {}
    for tag in ALL:
        print("loading %s ..." % tag, flush=True)
        g = C20.load(tag)
        D = dict(np.load(os.path.join(CACHE, tag + ".npz")))
        g["tr"] = g["t"] - g["t"][0]
        c = cells["V283"] if tag in V283_ROUTES else (cells["V281r3"] if tag == "r35" else cells["V280r2"])
        g["idx"], _ = demand_live(np.round(g["cmd"]), g["bar"], c)
        B = np.load(os.path.join(CACHE, tag + "_b4.npz"))
        k14, P14, tn14, _ = C20.dejitter(B["t14b"], 0.01, 100)
        b4 = B["b4"].astype(int)
        for bit in (4, 5, 6, 7):
            g["bit%d" % bit] = np.round(np.interp(g["t"], tn14, ((b4 >> bit) & 1).astype(float)))
        G[tag] = g

    pr("=" * 150)
    pr("THE GRINDING READ ON r36/r37/r38 (V283 = V281r3 + inert r24 comparator tap + Ki 0->50) vs r35 (V281r3) and r34 (V280r2)")
    pr("=" * 150)
    pr("  Kp is FLAT 248 on r35 AND on r36/r37/r38; r34 carries the V280 LERP 248..696.  r35 -> V283 is a Ki-ONLY")
    pr("  calibration change (0xC63E6 0 -> 50) plus four read-only cave displacements, so r35 vs r36/37/38 isolates Ki.")

    # ---------------------------------------------------------------- windowed census
    rows = []
    for tag in ALL:
        g = G[tag]
        msk = g["eng"] & (g["vego"] < 6.0)
        for aa, bb in C20.runs(msk, W):
            for s in range(aa, bb - W + 1, STEP):
                e = s + W
                f0w, promw = line_of(g["bar"][s:e], FS)
                fq, pq = line_of(g["bar"][s:e], FS, 5, 12)
                rows.append(dict(
                    tag=tag, t=g["tr"][s], f0=f0w, prom=promw, f610=fq, p610=pq,
                    amp=band(g["bar"][s:e], 18, 22), amp610=band(g["bar"][s:e], 6, 10),
                    ramp=band(g["wire"][s:e], 18, 22) / V.CPD,
                    rate=float(np.mean(np.abs(g["wire"][s:e])) / V.CPD),
                    v=float(g["vego"][s:e].mean()), ang=float(np.median(np.abs(g["ang"][s:e]))),
                    T=float(np.median(np.abs(g["T100"][s:e]))), idx=float(np.median(g["idx"][s:e])),
                    tq=float(np.median(np.abs(g["bar"][s:e]))), b6=float(g["bit6"][s:e].mean()),
                    creep=bool(1.0 <= g["vego"][s:e].mean() < 3.0),
                    hoff=bool(np.median(np.abs(g["bar"][s:e])) < 400)))
    R = {k: np.array([r[k] for r in rows]) for k in rows[0]}
    pres = (R["prom"] >= 8) & (R["amp"] >= 40)
    pr("\n" + "=" * 150)
    pr("1. THE 18-22 Hz CREEP LINE -- census (2 s windows, step 0.5 s, engaged LATERAL, v < 6 m/s;")
    pr("   present = most prominent 15-26 Hz peak, prominence >= 8 AND bar 18-22 >= 40 raw).  r35's method, unchanged.")
    pr("=" * 150)
    pr("  %-5s %-8s %6s %6s %6s | %-22s | %-20s | %s" % (
        "route", "build", "n", "pres", "%", "f mean sd p10/p90", "amp p50/p90/max raw", "by idx bin: present % (amp p50)"))
    for tag in ALL:
        sel = R["tag"] == tag; ps = sel & pres
        if not sel.any():
            continue
        bins = []
        for lab, bs in (("0-20", R["idx"] <= 20), ("20-60", (R["idx"] > 20) & (R["idx"] <= 60)),
                        ("60-120", (R["idx"] > 60) & (R["idx"] <= 120)), (">120", R["idx"] > 120)):
            b = sel & bs
            bins.append("%s: %.0f%% (%.0f, n%d)" % (lab, 100 * pres[b].mean() if b.any() else np.nan,
                                                    np.median(R["amp"][b]) if b.any() else np.nan, b.sum()))
        pr("  %-5s %-8s %6d %6d %6.0f | %.2f %.2f %.2f/%.2f | %4.0f/%4.0f/%4.0f | %s" % (
            tag, GRP[tag], sel.sum(), ps.sum(), 100 * pres[sel].mean(),
            R["f0"][ps].mean(), R["f0"][ps].std(), *np.percentile(R["f0"][ps], (10, 90)),
            *np.percentile(R["amp"][sel], (50, 90)), R["amp"][sel].max(), " ; ".join(bins)))
    # grouped
    pr("")
    for grp in ("V283", "V281r3", "V280r2"):
        sel = np.isin(R["tag"], [t for t in ALL if GRP[t] == grp]); ps = sel & pres
        pr("  %-5s %-8s %6d %6d %6.0f | %.2f %.2f %.2f/%.2f | %4.0f/%4.0f/%4.0f | (pooled)" % (
            "POOL", grp, sel.sum(), ps.sum(), 100 * pres[sel].mean(), R["f0"][ps].mean(), R["f0"][ps].std(),
            *np.percentile(R["f0"][ps], (10, 90)), *np.percentile(R["amp"][sel], (50, 90)), R["amp"][sel].max()))

    pr("\n  THE OPERATOR'S OWN STRATUM -- engaged LATERAL, HANDS-OFF (|bar| < 400 raw), CREEP 1-3 m/s (3-7 mph):")
    pr("  %-5s %-8s %7s %7s %7s %9s %9s %9s %9s" % ("route", "build", "n win", "pres", "%", "amp p50", "amp p90", "amp max", "rate18-22"))
    for tag in ALL:
        sel = (R["tag"] == tag) & R["creep"] & R["hoff"]
        if sel.sum() < 5:
            pr("  %-5s %-8s %7d   (too thin)" % (tag, GRP[tag], sel.sum())); continue
        pr("  %-5s %-8s %7d %7d %7.0f %9.0f %9.0f %9.0f %9.2f" % (
            tag, GRP[tag], sel.sum(), (sel & pres).sum(), 100 * pres[sel].mean(),
            np.median(R["amp"][sel]), np.percentile(R["amp"][sel], 90), R["amp"][sel].max(), np.median(R["ramp"][sel])))
    for grp in ("V283", "V281r3", "V280r2"):
        sel = np.isin(R["tag"], [t for t in ALL if GRP[t] == grp]) & R["creep"] & R["hoff"]
        if sel.sum() < 5:
            continue
        pr("  %-5s %-8s %7d %7d %7.0f %9.0f %9.0f %9.0f %9.2f   (pooled)" % (
            "POOL", grp, sel.sum(), (sel & pres).sum(), 100 * pres[sel].mean(),
            np.median(R["amp"][sel]), np.percentile(R["amp"][sel], 90), R["amp"][sel].max(), np.median(R["ramp"][sel])))

    # ---------------------------------------------------------------- episodes per 100 s
    pr("\n" + "=" * 150)
    pr("2. RATE OF OCCURRENCE -- contiguous line-present EPISODES per 100 s of engaged hands-off creep")
    pr("   (an episode = >= 1.0 s of consecutive 0.1 s frames whose local 2 s window is line-present)")
    pr("=" * 150)
    pr("  %-5s %-8s %10s %10s %10s %10s %10s %10s" % (
        "route", "build", "creep s", "episodes", "per 100 s", "ep s p50", "ep amp p50", "ep amp max"))
    epi_all = {}
    for tag in ALL:
        g = G[tag]
        m = g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 3.0) & (np.abs(g["bar"]) < 400)
        secs = m.sum() / FS
        # frame-level "line present": nearest census window of the same route
        sel = np.flatnonzero(R["tag"] == tag)
        if len(sel) == 0 or secs < 5:
            pr("  %-5s %-8s %10.1f   (too thin)" % (tag, GRP[tag], secs)); continue
        wt, wp = R["t"][sel], pres[sel]
        j = np.clip(np.searchsorted(wt, g["tr"] - 1.0), 0, len(wt) - 1)
        near = np.abs(wt[j] + 1.0 - g["tr"]) < 1.5
        hot = m & near & wp[j]
        eps = C20.runs(hot, int(1.0 * FS))
        durs = np.array([(b - a) / FS for a, b in eps]) if eps else np.array([])
        amps = np.array([band(g["bar"][a:b], 18, 22) for a, b in eps]) if eps else np.array([])
        epi_all[tag] = (eps, durs, amps, secs)
        pr("  %-5s %-8s %10.1f %10d %10.2f %10.2f %10.0f %10.0f" % (
            tag, GRP[tag], secs, len(eps), 100 * len(eps) / max(secs, 1e-9),
            np.median(durs) if len(durs) else np.nan, np.median(amps) if len(amps) else np.nan,
            amps.max() if len(amps) else np.nan))
    for grp in ("V283", "V281r3", "V280r2"):
        ts = [t for t in ALL if GRP[t] == grp and t in epi_all]
        if not ts:
            continue
        ne = sum(len(epi_all[t][0]) for t in ts); ss = sum(epi_all[t][3] for t in ts)
        aa = np.concatenate([epi_all[t][2] for t in ts if len(epi_all[t][2])]) if any(len(epi_all[t][2]) for t in ts) else np.array([np.nan])
        pr("  %-5s %-8s %10.1f %10d %10.2f %10s %10.0f %10.0f   (pooled)" % (
            "POOL", grp, ss, ne, 100 * ne / max(ss, 1e-9), "", np.nanmedian(aa), np.nanmax(aa)))

    # ---------------------------------------------------------------- Ki test (f)
    pr("\n" + "=" * 150)
    pr("3. DOES Ki 50 TOUCH THE GRIND?  PREREG-V283-READ.md statistic (f): '18-22 Hz creep bar amplitude")
    pr("   (hands-off, 1-3 m/s) unchanged (Ki 1 % of D at 20 Hz)'.  r35 (Ki 0) vs r36/r37/r38 (Ki 50), Kp flat 248 both.")
    pr("=" * 150)
    a = R["amp"][np.isin(R["tag"], V283_ROUTES) & R["creep"] & R["hoff"]]
    b = R["amp"][(R["tag"] == "r35") & R["creep"] & R["hoff"]]
    c = R["amp"][(R["tag"] == "r34") & R["creep"] & R["hoff"]]
    if len(a) > 5 and len(b) > 5:
        u = stats.mannwhitneyu(a, b, alternative="two-sided")
        pr("  bar 18-22 amp, hands-off creep windows:  V283 n %d p50 %.0f (p90 %.0f)  vs  V281r3 n %d p50 %.0f (p90 %.0f)  vs  V280r2 n %d p50 %.0f" % (
            len(a), np.median(a), np.percentile(a, 90), len(b), np.median(b), np.percentile(b, 90), len(c), np.median(c) if len(c) else np.nan))
        pr("  V283 / V281r3 ratio of medians %.2f  ;  Mann-Whitney U p = %.3f  ->  %s" % (
            np.median(a) / max(np.median(b), 1e-9), u.pvalue,
            "NO detectable Ki effect at 20 Hz (prereg (f) HOLDS)" if u.pvalue > 0.05 else "a difference at p<0.05 -- see the idx-matched table below"))
    pr("\n  idx-matched (the only variable creep20 found the line tracks), hands-off creep windows, bar 18-22 p50:")
    pr("    %-14s %10s %10s %10s %10s" % ("idx bin", "V283", "V281r3", "V280r2", "V283/V281r3"))
    for lab, bs in (("0-5", R["idx"] <= 5), ("5-20", (R["idx"] > 5) & (R["idx"] <= 20)),
                    ("20-60", (R["idx"] > 20) & (R["idx"] <= 60)), (">60", R["idx"] > 60)):
        vals = []
        for grp in ("V283", "V281r3", "V280r2"):
            s = np.isin(R["tag"], [t for t in ALL if GRP[t] == grp]) & R["creep"] & R["hoff"] & bs
            vals.append(np.median(R["amp"][s]) if s.sum() >= 4 else np.nan)
        pr("    %-14s %10.0f %10.0f %10.0f %10.2f" % (lab, vals[0], vals[1], vals[2], vals[0] / vals[1] if vals[1] else np.nan))
    pr("\n  5-12 Hz line (the strong-turn stutter band), same windows:")
    pr("    %-8s %8s %8s %8s" % ("build", "pres %", "6-10 p50", "6-10 p90"))
    for grp in ("V283", "V281r3", "V280r2"):
        s = np.isin(R["tag"], [t for t in ALL if GRP[t] == grp]) & (R["v"] < 6)
        p6 = (R["p610"] >= 8) & (R["amp610"] >= 40)
        pr("    %-8s %8.0f %8.0f %8.0f" % (grp, 100 * p6[s].mean(), np.median(R["amp610"][s]), np.percentile(R["amp610"][s], 90)))

    # ---------------------------------------------------------------- incident hunt
    pr("\n" + "=" * 150)
    pr("4. PRONOUNCED-INCIDENT HUNT -- the r35 23:48:21 class (a ~1 s EXPONENTIAL burst of the 20 Hz mode at a")
    pr("   loaded turn start).  Every contiguous line-present stretch >= 1.5 s, ranked by peak bar 18-22 envelope.")
    pr("   r35's incident: envelope peak 500 raw, per-second 306, growth +1.42 /s, decay -3.9 /s, 7.5 Hz companion 596 raw.")
    pr("=" * 150)
    cands = []
    for tag in ALL:
        g = G[tag]
        sel = np.flatnonzero(R["tag"] == tag)
        wt, wp = R["t"][sel], pres[sel]
        j = np.clip(np.searchsorted(wt, g["tr"] - 1.0), 0, len(wt) - 1)
        hot = g["eng"] & (np.abs(wt[j] + 1.0 - g["tr"]) < 1.5) & wp[j]
        for a, b in C20.runs(hot, int(1.5 * FS)):
            f0, prom = line_of(g["bar"][a:b], FS)
            if not np.isfinite(f0):
                continue
            env = envelope(g["bar"][a:b], f0, FS)
            gu, gd = growth_fit(g["tr"][a:b], env)
            cands.append(dict(tag=tag, t0=g["tr"][a], t1=g["tr"][b - 1], dur=(b - a) / FS, f0=f0,
                              env=env.max(), amp=band(g["bar"][a:b], 18, 22), a610=band(g["bar"][a:b], 6, 10),
                              gu=gu, gd=gd, v=g["vego"][a:b].mean(), ang=np.median(np.abs(g["ang"][a:b])),
                              idx=np.median(g["idx"][a:b]), tq=np.median(np.abs(g["bar"][a:b])),
                              rate=np.mean(np.abs(g["wire"][a:b])) / V.CPD, T=np.median(np.abs(g["T100"][a:b])),
                              a=a, b=b))
    cands.sort(key=lambda r: -r["env"])
    pr("  %-5s %8s %6s %6s %8s %8s %8s %8s %8s %6s %6s %6s %7s %7s" % (
        "route", "t0 s", "dur", "f0", "env pk", "18-22", "6-10", "grow /s", "decay/s", "v", "|ang|", "idx", "|tq|", "|rate|"))
    for r in cands[:20]:
        pr("  %-5s %8.1f %6.1f %6.1f %8.0f %8.0f %8.0f %8.2f %8.2f %6.1f %6.0f %6.0f %7.0f %7.1f" % (
            r["tag"], r["t0"], r["dur"], r["f0"], r["env"], r["amp"], r["a610"], r["gu"], r["gd"],
            r["v"], r["ang"], r["idx"], r["tq"], r["rate"]))
    pr("")
    for grp in ("V283", "V281r3", "V280r2"):
        cs = [r for r in cands if GRP[r["tag"]] == grp]
        eng = sum(G[t]["eng"].sum() / FS for t in ALL if GRP[t] == grp)
        big = [r for r in cs if r["env"] >= 400]
        pr("  %-8s: %3d line-present stretches >= 1.5 s over %6.1f s engaged (%.2f per 100 s) ; env pk p50/p90/max %4.0f/%4.0f/%4.0f ; %d with env pk >= 400 raw (the r35-incident class)" % (
            grp, len(cs), eng, 100 * len(cs) / max(eng, 1e-9),
            np.median([r["env"] for r in cs]) if cs else np.nan,
            np.percentile([r["env"] for r in cs], 90) if cs else np.nan,
            max([r["env"] for r in cs]) if cs else np.nan, len(big)))

    # detail on the top V283 candidates
    pr("\n  DETAIL on the three loudest V283 stretches (the r35 incident's instrument set):")
    for r in [x for x in cands if GRP[x["tag"]] == "V283"][:3]:
        g = G[r["tag"]]; a, b = r["a"], r["b"]
        w = slice(max(0, a - 200), min(len(g["t"]), b + 200))
        pr("    %s t %.1f-%.1f s (%.1f s), f0 %.2f Hz : bar 18-22 %.0f raw (env pk %.0f), 6-10 %.0f, rate 18-22 %.2f deg/s, tap 18-22 %s" % (
            r["tag"], r["t0"], r["t1"], r["dur"], r["f0"], r["amp"], r["env"], r["a610"],
            band(g["wire"][a:b], 18, 22) / V.CPD,
            ("%.0f" % C20.bamp(g["T"][(g["T_t"] >= g["t"][a]) & (g["T_t"] < g["t"][b - 1])], 18, 22, FST))
            if ((g["T_t"] >= g["t"][a]) & (g["T_t"] < g["t"][b - 1])).sum() >= 32 else "n/a"))
        pr("        operating point: v %.1f m/s, |angle| p50 %.0f deg (%.0f..%.0f), idx p50/p90 %.0f/%.0f, |tq| p50/p90 %.0f/%.0f raw, |T| p50 %.0f, |rate| %.1f deg/s" % (
            r["v"], r["ang"], np.min(g["ang"][a:b]), np.max(g["ang"][a:b]), r["idx"], np.percentile(g["idx"][a:b], 90),
            r["tq"], np.percentile(np.abs(g["bar"][a:b]), 90), r["T"], r["rate"]))
        pr("        envelope growth %+.2f /s, decay %+.2f /s (r35's incident: +1.42 / -3.90) ; bit6 duty %.3f, bit4 duty %.3f in the stretch" % (
            r["gu"], r["gd"], g["bit6"][a:b].mean(), g["bit4"][a:b].mean()))
        pr("        20 s context: engaged %.2f, v %.1f..%.1f, |angle| %.0f..%.0f, idx max %.0f" % (
            g["eng"][w].mean(), g["vego"][w].min(), g["vego"][w].max(),
            np.min(np.abs(g["ang"][w])), np.max(np.abs(g["ang"][w])), g["idx"][w].max()))

    with open(os.path.join(SCR, "v283_grind_census.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote", os.path.join(SCR, "v283_grind_census.txt"))


if __name__ == "__main__":
    main()
