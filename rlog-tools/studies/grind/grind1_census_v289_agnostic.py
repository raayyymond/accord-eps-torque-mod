# -*- coding: utf-8 -*-
"""studies/grind/grind1_census_v289_agnostic.py -- FREQUENCY-AGNOSTIC grind census (team-lead, 2026-09-09, after `marks62` found the
V289 grinding line at 14.4-16.8 Hz): the V282 yardstick's 18-22 Hz gate is BLIND to a line that has moved to 16 Hz, so a
"presence fell" reading under that gate is the gate, not the car.

Same detector LOGIC and NORMALISATION as grind1_census_v282.py, with the frequency freed:
  window   2 s / 0.5 s step / lateral-engaged; the most prominent 12-25 Hz peak (GI.line_of, same prominence estimator);
  present  = prominence >= 8 AND bar band amplitude in [f0-2, f0+2] >= 40 raw   (the V282 rule used 15-26 Hz for the peak and
             the FIXED 18-22 Hz band for the amplitude; here the band FOLLOWS the peak);
  episode  = contiguous >= 0.5 s present run inside an engaged run; per episode: f0 (12-25 Hz), Hilbert envelope at f0 +- 2 Hz,
             GI.growth_fit rise/decay slopes -> tau_up / tau_dn / zeta, duration, class by the V282 rules (BURST / SUSTAINED /
             RIDE-ALONG with the 6-10 Hz companion), operating point; TRAINS = chains of episodes with < 5 s between them.
Routes r39 (V282), r3a/r3c (V282 pool), r5e_v288 (V288), r62_v289 / r63_v289 (V289) side by side, plus:
  3  13-17 vs 18-22 Hz band power per speed regime (< 8 / 8-18 / > 18 m/s), bar and wheel rate, same segment-PSD normalisation;
  4  was the 16 Hz line there BEFORE (weaker)?  14-17 Hz presence and band amplitude on r39 / r5e_v288 vs V289; PSD excess at
     14-17 on every route; per-route f0 distribution -- SHIFTED mode vs UNMASKED second mode.
Writes _scratch/grind1_census_v289_agnostic.txt.  Subagent `census62`.  Analysis only.
"""
import json
import os
import pickle
import sys

import numpy as np
from scipy import signal, stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import grind1_census_v289_r62_r63 as M        # noqa: E402  constants + registrations (main() not run)
import grind1_census_v288_r5e as C88          # noqa: E402
import grind1_census_v282 as CEN              # noqa: E402
import creep20_loop_id as C20                 # noqa: E402
import grind_incident_r35 as GI               # noqa: E402
import v280_map_profiles as V                 # noqa: E402
import wire_0xe4_20hz as WIRE                 # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
W, STEP = 200, 50
FLO, FHI = 12.0, 25.0
ALL, V282_ROUTES, V288_TAG, V289_ROUTES, ARMS, GRP = M.ALL, M.V282_ROUTES, M.V288_TAG, M.V289_ROUTES, M.ARMS, M.GRP
ci, boot_stat = M.ci, M.boot_stat
REGIMES = (("< 8 m/s", 0.0, 8.0), ("8-18 m/s", 8.0, 18.0), ("> 18 m/s", 18.0, 99.0))
FBINS = ((12, 14), (14, 17), (17, 18), (18, 19.5), (19.5, 20.5), (20.5, 22), (22, 25))
CACHE_P = os.path.join(M.SCR, "grind1_census_v289_agnostic_cache.pkl")
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def window_census(G, tags):
    rows = []
    for tag in tags:
        g = G[tag]
        for aa, bb in C20.runs(g["eng"], W):
            for s in range(aa, bb - W + 1, STEP):
                e = s + W
                x = g["bar"][s:e]
                f0w, promw = CEN.line_of(x, FS, FLO, FHI)
                amp = CEN.band(x, max(f0w - 2, 1.0), f0w + 2) if np.isfinite(f0w) else np.nan
                rows.append(dict(tag=tag, t=g["tr"][s], f0=f0w, prom=promw, amp=amp,
                                 amp1417=CEN.band(x, 14, 17), amp1822=CEN.band(x, 18, 22), amp610=CEN.band(x, 6, 10),
                                 v=float(g["vego"][s:e].mean()), ang=float(np.median(np.abs(g["ang"][s:e]))),
                                 tq=float(np.median(np.abs(g["bar"][s:e]))), rate=float(np.mean(g["rate"][s:e]))))
        print("  windows", tag, len(rows), flush=True)
    R = {k: np.array([r[k] for r in rows]) for k in rows[0]}
    pres = (R["prom"] >= 8) & (R["amp"] >= 40)
    return R, pres


def extract_episodes(G, R, pres, tags):
    episodes = []
    for tag in tags:
        g = G[tag]
        sel = np.flatnonzero(R["tag"] == tag)
        wt, wp = R["t"][sel], pres[sel]
        j = np.clip(np.searchsorted(wt, g["tr"] - 1.0), 0, len(wt) - 1)
        near = np.abs(wt[j] + 1.0 - g["tr"]) < 1.5
        hot = g["eng"] & near & wp[j]
        g["hot_ag"] = hot
        for a, b in C20.runs(hot, int(0.5 * FS)):
            f0, prom = CEN.line_of(g["bar"][a:b], FS, FLO, FHI)
            if not np.isfinite(f0):
                continue
            s0, s1 = max(0, a - 100), min(len(g["tr"]), b + 100)
            env = CEN.envelope(g["bar"][s0:s1], f0, FS)
            env7 = CEN.envelope(g["bar"][s0:s1], 7.5, FS, bw=2.5)
            gu, gd = CEN.growth_fit(g["tr"][s0:s1], env)
            amp = CEN.band(g["bar"][a:b], max(f0 - 2, 1.0), f0 + 2); amp6 = CEN.band(g["bar"][a:b], 6, 10)
            n25 = max(4, int(0.25 * FS)); off = a - s0
            e20 = env[off:off + (b - a)]; e7 = env7[off:off + (b - a)]
            m = min(len(e20), len(e7))
            e20b = e20[:m][:m - m % n25].reshape(-1, n25).mean(1) if m >= n25 else e20[:m]
            e7b = e7[:m][:m - m % n25].reshape(-1, n25).mean(1) if m >= n25 else e7[:m]
            corr7 = float(np.corrcoef(e20b, e7b)[0, 1]) if len(e20b) >= 4 and np.std(e20b) > 0 and np.std(e7b) > 0 else np.nan
            if np.isfinite(gu) and np.isfinite(gd) and gu >= 1.0 and gd <= -1.0 and (b - a) / FS <= 3.0:
                cls = "BURST"
            elif amp6 >= 1.2 * amp and np.isfinite(corr7) and corr7 >= 0.5:
                cls = "RIDE-ALONG"
            else:
                cls = "SUSTAINED"
            body = e20[:m]
            trend = stats.linregress(np.arange(len(body)) / FS, np.log(np.maximum(body, 1e-9))).slope if len(body) >= 20 else np.nan
            ff = WIRE.fine_line(g["bar"][a:b], FS, FLO, FHI)[0] if b - a >= 100 else np.nan
            episodes.append(dict(
                tag=tag, a=a, b=b, t0=g["tr"][a], t1=g["tr"][b - 1], dur=(b - a) / FS, f0=f0, ffine=ff, cls=cls,
                env=float(np.nanmax(env)), amp=amp, amp6=amp6, corr7=corr7, gu=gu, gd=gd, trend=trend,
                envr=float(np.nanmax(CEN.envelope(g["wire"][s0:s1], f0, FS))) / V.CPD,
                v=float(g["vego"][a:b].mean()), ang0=float(g["ang"][a]), angm=float(np.median(np.abs(g["ang"][a:b]))),
                rate0=float(g["rate"][a]), idx0=float(g["idx"][a]), hands=float(np.median(np.abs(g["bar"][a:b]))),
                reg=int(np.digitize(g["vego"][a:b].mean(), [8.0, 18.0]))))
    return episodes


def main():
    rng = np.random.default_rng(20260911)
    cells = {k: GI.read_cells(p) for k, p in CEN.IMG.items() if k in ("V282", "V288", "V289")}
    G = {}
    for tag in ALL:
        G[tag] = WIRE.load_route(tag, cells[CEN.CELL_OF[tag]])
        G[tag]["marks"] = M.marks_of(tag)
        G[tag]["reg"] = np.digitize(G[tag]["vego"], [8.0, 18.0])
        print("loaded", tag, flush=True)
    if os.path.exists(CACHE_P):
        CACHED = pickle.load(open(CACHE_P, "rb"))
        R, pres, episodes = CACHED["R"], CACHED["pres"], CACHED["episodes"]
        for tag in ALL:
            G[tag]["hot_ag"] = CACHED["hot"][tag]
    else:
        R, pres = window_census(G, ALL)
        episodes = extract_episodes(G, R, pres, ALL)
        pickle.dump(dict(R=R, pres=pres, episodes=episodes, hot={t: G[t]["hot_ag"] for t in ALL}), open(CACHE_P, "wb"))
    R_reg = np.digitize(R["v"], [8.0, 18.0])

    pr("=" * 168)
    pr("FREQUENCY-AGNOSTIC GRIND CENSUS, 12-25 Hz PEAK-TRACKED -- r39 (V282) / r5e_v288 (V288) / r62_v289 / r63_v289 (V289), same threshold logic and normalisation")
    pr("=" * 168)
    pr("present = most prominent 12-25 Hz peak has prominence >= 8 AND bar amplitude in [f0-2, f0+2] >= 40 raw; episode = >= 0.5 s contiguous present, engaged.")

    # ---------------------------------------------------------------- 1. presence + f0 distribution
    pr("\n1. PRESENCE (all engaged windows) and the f0 DISTRIBUTION of present windows -- shares in 12-14 / 14-17 / 17-18 / 18-19.5 / 19.5-20.5 / 20.5-22 / 22-25 Hz")
    pr("  %-9s %-13s %6s %6s %6s | %-48s | %-20s | %-18s" % ("arm", "label", "n win", "pres", "%", "f0 shares (%) " + " ".join("%5s" % ("%g-%g" % b) for b in FBINS), "f0 p10/p50/p90", "amp p50/p90/max"))
    for name, tags in ARMS:
        sel = np.isin(R["tag"], tags); ps = sel & pres
        f0 = R["f0"][ps]
        if ps.sum() < 5:
            pr("  %-9s %-13s %6d %6d  (thin)" % (name, GRP.get(name, ""), sel.sum(), ps.sum())); continue
        sh = " ".join("%5.0f" % (100 * np.mean((f0 >= a_) & (f0 < b_))) for a_, b_ in FBINS)
        pr("  %-9s %-13s %6d %6d %6.1f | %-48s | %5.2f/%5.2f/%5.2f    | %4.0f/%4.0f/%4.0f" % (
            name, GRP.get(name, ""), sel.sum(), ps.sum(), 100 * pres[sel].mean(), " " * 14 + sh, *np.percentile(f0, (10, 50, 90)),
            *np.percentile(R["amp"][ps], (50, 90)), R["amp"][ps].max()))
    pr("\n  1b. Presence and f0 by SPEED REGIME (window mean vEgo):")
    pr("  %-9s %-9s %6s %6s %6s | %-48s | %-20s" % ("arm", "regime", "n win", "pres", "%", "f0 shares (%)", "f0 p10/p50/p90"))
    for name, tags in ARMS:
        for k, (lab, lo, hi) in enumerate(REGIMES):
            sel = np.isin(R["tag"], tags) & (R_reg == k); ps = sel & pres
            f0 = R["f0"][ps]
            if sel.sum() < 5:
                pr("  %-9s %-9s %6d   (thin)" % (name, lab, sel.sum())); continue
            if ps.sum() < 3:
                pr("  %-9s %-9s %6d %6d %6.1f | (few present)" % (name, lab, sel.sum(), ps.sum(), 100 * pres[sel].mean())); continue
            sh = " ".join("%5.0f" % (100 * np.mean((f0 >= a_) & (f0 < b_))) for a_, b_ in FBINS)
            pr("  %-9s %-9s %6d %6d %6.1f | %-48s | %5.2f/%5.2f/%5.2f" % (name, lab, sel.sum(), ps.sum(), 100 * pres[sel].mean(), " " * 14 + sh, *np.percentile(f0, (10, 50, 90))))

    # ---------------------------------------------------------------- 2. episodes
    pr("\n" + "=" * 168)
    pr("2. EPISODES, peak-tracked -- per V289 episode, then per-arm summaries")
    pr("=" * 168)
    pr("  %-9s %-9s %6s %6s %6s %6s %8s %8s %6s %6s %6s %6s %6s %7s %7s %7s %7s" % (
        "route", "class", "t0 s", "dur", "f0", "ffine", "env bar", "env rate", "6-10", "v", "|ang|", "rate0", "idx0", "|tq|", "gu /s", "gd /s", "trend"))
    for e in [e for e in episodes if e["tag"] in V289_ROUTES]:
        pr("  %-9s %-9s %6.1f %6.2f %6.1f %6.2f %8.0f %8.2f %6.0f %6.1f %6.0f %6.1f %6.0f %7.0f %7.2f %7.2f %7.2f" % (
            e["tag"], e["cls"], e["t0"], e["dur"], e["f0"], e["ffine"], e["env"], e["envr"], e["amp6"], e["v"], e["angm"], e["rate0"], e["idx0"], e["hands"], e["gu"], e["gd"], e["trend"]))
    for tag in ALL:
        if G[tag]["marks"]:
            pr("  bookmarks %s: " % tag + " ; ".join("%.1f -> %s" % (mk, ", ".join("%.1f-%.1f %s f %.1f env %.0f" % (e["t0"], e["t1"], e["cls"], e["f0"], e["env"]) for e in episodes
                                                                     if e["tag"] == tag and e["t0"] - 5 <= mk <= e["t1"] + 5) or "no episode within 5 s") for mk in G[tag]["marks"]))

    def rate_blocks(tags, eps):
        cnt, exp_ = [], []
        for tag in tags:
            g = G[tag]
            eng_idx = np.flatnonzero(g["eng"])
            blk_of = np.full(len(g["eng"]), -1); blk_of[eng_idx] = np.arange(len(eng_idx)) // 3000
            nb = blk_of.max() + 1
            c = np.zeros(nb); x = np.bincount(blk_of[eng_idx], minlength=nb) / FS
            for e in eps:
                if e["tag"] == tag:
                    c[blk_of[e["a"]]] += 1
            cnt.append(c); exp_.append(x)
        return np.concatenate(cnt), np.concatenate(exp_)

    pr("\n  2a. Rate per engaged hour (30 s block bootstrap), class split, f0 of episodes, envelope and duration -- ALL episodes, then those with f0 < 18 Hz and f0 >= 18 Hz:")
    pr("  %-9s %-8s %4s %7s %-18s | %-16s | %-18s | %-16s | %-14s | %-14s" % ("arm", "f0 set", "n", "eng s", "ep/h [CI]", "BURST/SUST/RIDE %", "f0 p10/p50/p90", "env p50/p90/max", "dur p50/p90", "rate env p50/max"))
    RATE = {}
    for name, tags in ARMS:
        for fset, fn in (("all", lambda e: True), ("<18 Hz", lambda e: e["f0"] < 18), (">=18 Hz", lambda e: e["f0"] >= 18)):
            es = [e for e in episodes if e["tag"] in tags and fn(e)]
            c, x = rate_blocks(tags, es)
            r = 3600 * c.sum() / x.sum()
            bs = np.array([3600 * c[j].sum() / max(x[j].sum(), 1) for j in (rng.integers(0, len(c), len(c)) for _ in range(4000))])
            RATE[(name, fset)] = (r, bs)
            if len(es) < 3:
                pr("  %-9s %-8s %4d %7.0f %5.0f [%4.0f, %4.0f]  | (n < 3)" % (name, fset, len(es), x.sum(), r, *ci(bs))); continue
            cl = np.array([e["cls"] for e in es]); f0 = np.array([e["f0"] for e in es]); ev = np.array([e["env"] for e in es]); d = np.array([e["dur"] for e in es])
            evr = np.array([e["envr"] for e in es])
            pr("  %-9s %-8s %4d %7.0f %5.0f [%4.0f, %4.0f]  | %3.0f / %3.0f / %3.0f   | %5.2f/%5.2f/%5.2f | %4.0f/%4.0f/%4.0f   | %5.2f / %5.2f  | %5.2f / %5.2f" % (
                name, fset, len(es), x.sum(), r, *ci(bs), *[100 * np.mean(cl == c_) for c_ in ("BURST", "SUSTAINED", "RIDE-ALONG")],
                *np.percentile(f0, (10, 50, 90)), *np.percentile(ev, (50, 90)), ev.max(), np.median(d), np.percentile(d, 90), np.median(evr), evr.max()))
    for fset in ("all", "<18 Hz", ">=18 Hz"):
        for a_, b_ in (("V289pool", "V282pool"), ("V289pool", V288_TAG), ("V289pool", "r39")):
            ra, rb = RATE[(a_, fset)], RATE[(b_, fset)]
            pr("  rate ratio [%s] %s / %s = %.2f [%.2f, %.2f]" % (fset, a_, b_, ra[0] / max(rb[0], 1e-9), *ci(ra[1] / np.maximum(rb[1], 1e-9))))

    pr("\n  2b. DECAY / RISE of the peak-tracked rings: gu, gd (/s), tau_up / tau_dn (ms), zeta_dn = |gd|/(2 pi f0), frac gd <= -1/s, body-trend >= -0.5/s share (sustained-shaped):")
    pr("  %-9s %-8s %4s | %-22s %-22s | %8s %8s | %-22s | %7s %8s" % ("arm", "f0 set", "n", "gu p50 [CI]", "gd p50 [CI]", "tau_up", "tau_dn", "zeta_dn p50 [CI]", "gd<=-1", "trend>=-.5"))
    GD = {}
    for name, tags in ARMS:
        for fset, fn in (("all", lambda e: True), ("<18 Hz", lambda e: e["f0"] < 18), (">=18 Hz", lambda e: e["f0"] >= 18)):
            es = [e for e in episodes if e["tag"] in tags and fn(e) and np.isfinite(e["gu"]) and np.isfinite(e["gd"])]
            if len(es) < 3:
                pr("  %-9s %-8s %4d   (thin)" % (name, fset, len(es))); continue
            gu = np.array([e["gu"] for e in es]); gd = np.array([e["gd"] for e in es]); f0 = np.array([e["f0"] for e in es]); z = np.abs(gd) / (2 * np.pi * f0)
            tr = np.array([e["trend"] for e in es]); tr = tr[np.isfinite(tr)]
            GD[(name, fset)] = (gd, z)
            pr("  %-9s %-8s %4d | %6.2f [%6.2f,%6.2f]  %6.2f [%6.2f,%6.2f]  | %8.0f %8.0f | %6.4f [%6.4f,%6.4f] | %7.2f %8.2f" % (
                name, fset, len(es), np.median(gu), *boot_stat(gu, np.median, rng, 2000), np.median(gd), *boot_stat(gd, np.median, rng, 2000),
                1000 / max(np.median(gu), 1e-9), 1000 / max(-np.median(gd), 1e-9), np.median(z), *boot_stat(z, np.median, rng, 2000), np.mean(gd <= -1), np.mean(tr >= -0.5) if len(tr) else np.nan))
    for fset in ("all", "<18 Hz", ">=18 Hz"):
        for a_, b_ in (("V289pool", "V282pool"), ("V289pool", V288_TAG), ("V289pool", "r39"), ("r62_v289", "r39"), ("r63_v289", "r39")):
            if (a_, fset) in GD and (b_, fset) in GD:
                ga, gb = np.abs(GD[(a_, fset)][0]), np.abs(GD[(b_, fset)][0]); za, zb = GD[(a_, fset)][1], GD[(b_, fset)][1]
                bs = [np.median(ga[rng.integers(0, len(ga), len(ga))]) / max(np.median(gb[rng.integers(0, len(gb), len(gb))]), 1e-9) for _ in range(4000)]
                bz = [np.median(za[rng.integers(0, len(za), len(za))]) / max(np.median(zb[rng.integers(0, len(zb), len(zb))]), 1e-9) for _ in range(4000)]
                pr("  [%s] |gd| %s / %s = %.2f [%.2f, %.2f] ; zeta ratio %.2f [%.2f, %.2f] ; MW p(V289 faster) %.3g ; n %d vs %d" % (
                    fset, a_, b_, np.median(ga) / np.median(gb), *ci(bs), np.median(za) / np.median(zb), *ci(bz), stats.mannwhitneyu(ga, gb, alternative="greater").pvalue, len(ga), len(gb)))

    pr("\n  2c. TRAINS -- consecutive episodes on a route with < 5 s from one's end to the next's start: onset-to-onset repeat interval, train length, share of episodes in trains >= 3:")
    pr("  %-9s %4s | %6s %-26s | %-20s | %8s | %-22s" % ("arm", "n ep", "n trn", "repeat s p25/p50/p75 (n gaps)", "train len p50/max", ">=3 share", "f0 within trains sd (Hz)"))
    for name, tags in ARMS:
        gaps, lens, sds, ntr, in3 = [], [], [], 0, 0
        for tag in tags:
            es = sorted([e for e in episodes if e["tag"] == tag], key=lambda e: e["t0"])
            i = 0
            while i < len(es):
                j = i
                while j + 1 < len(es) and es[j + 1]["t0"] - es[j]["t1"] < 5.0:
                    j += 1
                if j > i:
                    ntr += 1; lens.append(j - i + 1)
                    gaps += [es[k + 1]["t0"] - es[k]["t0"] for k in range(i, j)]
                    sds.append(np.std([es[k]["f0"] for k in range(i, j + 1)]))
                    if j - i + 1 >= 3:
                        in3 += j - i + 1
                i = j + 1
        n = sum(1 for e in episodes if e["tag"] in tags)
        if gaps:
            pr("  %-9s %4d | %6d %5.1f/%5.1f/%5.1f (%3d)         | %5.1f / %3d          | %8.2f | %6.2f" % (
                name, n, ntr, *np.percentile(gaps, (25, 50, 75)), len(gaps), np.median(lens), max(lens), in3 / max(n, 1), np.median(sds)))
        else:
            pr("  %-9s %4d | %6d   (no trains)" % (name, n, ntr))

    pr("\n  2d. Where do the V289 episodes sit?  by f0 set x regime: n, ep/h of that regime's engaged time, |ang| median, hands-on share, env p50/max")
    pr("  %-9s %-8s %-9s %4s %7s %6s | %6s %6s %6s %8s" % ("arm", "f0 set", "regime", "n", "eng s", "ep/h", "|ang|", "hands", "idx", "env p50/max"))
    for name, tags in ARMS:
        for fset, fn in (("<18 Hz", lambda e: e["f0"] < 18), (">=18 Hz", lambda e: e["f0"] >= 18)):
            for k, (lab, lo, hi) in enumerate(REGIMES):
                es = [e for e in episodes if e["tag"] in tags and fn(e) and e["reg"] == k]
                secs = sum(((G[t]["eng"]) & (G[t]["reg"] == k)).sum() / FS for t in tags)
                if secs < 30:
                    continue
                if es:
                    pr("  %-9s %-8s %-9s %4d %7.0f %6.0f | %6.0f %6.2f %6.0f %4.0f/%4.0f" % (
                        name, fset, lab, len(es), secs, 3600 * len(es) / secs, np.median([e["angm"] for e in es]), np.mean([e["hands"] > 700 for e in es]),
                        np.median([e["idx0"] for e in es]), np.median([e["env"] for e in es]), max(e["env"] for e in es)))
                else:
                    pr("  %-9s %-8s %-9s %4d %7.0f %6.0f |" % (name, fset, lab, 0, secs, 0.0))

    # ---------------------------------------------------------------- 3. band power by regime
    pr("\n" + "=" * 168)
    pr("3. 13-17 vs 18-22 Hz BAND POWER per speed regime, engaged (bar raw^2 ; wheel rate (deg/s)^2), segment PSDs Hann 512 with segment-bootstrap CIs; and their ratio")
    pr("=" * 168)
    pr("  %-9s %-9s %-5s %5s %6s | %-26s %-26s %-26s | %8s" % ("route", "regime", "sig", "n seg", "secs", "13-17 [CI]", "18-22 [CI]", "22-24 [CI]", "13-17/18-22"))
    BP = {}
    for tag in ALL:
        g = G[tag]
        for k, (lab, lo, hi) in enumerate(REGIMES):
            runs = C20.runs(g["eng"] & (g["reg"] == k), 512)
            for sig, arr in (("bar", g["bar"]), ("wire", g["wire"] / V.CPD)):
                f, P = C88.seg_psds([arr[a:b] for a, b in runs], FS, 512)
                if len(P) < 5:
                    pr("  %-9s %-9s %-5s %5d   (thin)" % (tag, lab, sig, len(P))); continue
                b13 = C88.bandpow(f, P, 13, 17); b18 = C88.bandpow(f, P, 18, 22); b22 = C88.bandpow(f, P, 22, 24)
                BP[(tag, k, sig)] = (b13.mean(), b18.mean(), b22.mean())
                pr("  %-9s %-9s %-5s %5d %6.0f | %8.3g [%7.3g,%7.3g] %8.3g [%7.3g,%7.3g] %8.3g [%7.3g,%7.3g] | %8.2f" % (
                    tag, lab, sig, len(P), sum(b - a for a, b in runs) / FS, b13.mean(), *boot_stat(b13, np.mean, rng, 1000), b18.mean(), *boot_stat(b18, np.mean, rng, 1000),
                    b22.mean(), *boot_stat(b22, np.mean, rng, 1000), b13.mean() / b18.mean()))
    pr("  ratios, V289 route / reference, per regime: 13-17 | 18-22 | 22-24  (bar ; wire)")
    for t in V289_ROUTES:
        for k, (lab, lo, hi) in enumerate(REGIMES):
            for ref in ("r39", V288_TAG):
                if all((x, k, s) in BP for x in (t, ref) for s in ("bar", "wire")):
                    pr("  %-9s %-9s / %-9s  bar %6.2f | %6.2f | %6.2f    wire %6.2f | %6.2f | %6.2f" % (
                        t, lab, ref, *[BP[(t, k, "bar")][i] / BP[(ref, k, "bar")][i] for i in range(3)], *[BP[(t, k, "wire")][i] / BP[(ref, k, "wire")][i] for i in range(3)]))

    # ---------------------------------------------------------------- 4. was 16 Hz there before?
    pr("\n" + "=" * 168)
    pr("4. WAS THE 16 Hz LINE THERE BEFORE?  14-17 Hz presence (peak-tracked windows with f0 in 14-17), 14-17 Hz band amplitude distribution, PSD excess at 14-17 on every route")
    pr("=" * 168)
    pr("  %-9s %-13s %6s | %6s %6s | %6s %6s | %-18s %-18s | %-22s" % ("route", "label", "n win", "f0 14-17", "%", "f0 18-22", "%", "amp 14-17 p50/p90/max", "amp 18-22 p50/p90/max", "14-17 exc dB [CI] @ f"))
    for tag in ALL:
        g = G[tag]
        sel = R["tag"] == tag; ps = sel & pres
        n1417 = int((ps & (R["f0"] >= 14) & (R["f0"] < 17)).sum()); n1822 = int((ps & (R["f0"] >= 18) & (R["f0"] < 22)).sum())
        runs = C20.runs(g["eng"], 512)
        f, P = C88.seg_psds([g["bar"][a:b] for a, b in runs], FS, 512)
        ex = C88.excess_db(f, P.mean(0)); m = (f >= 14) & (f <= 17); i = np.flatnonzero(m)[np.argmax(ex[m])]
        bs = [C88.excess_db(f, P[rng.integers(0, len(P), len(P))].mean(0))[i] for _ in range(200)]
        pr("  %-9s %-13s %6d | %6d %6.2f | %6d %6.2f | %4.0f/%4.0f/%4.0f      %4.0f/%4.0f/%4.0f      | %+5.1f [%+.1f,%+.1f] @ %5.2f" % (
            tag, GRP[tag], sel.sum(), n1417, 100 * n1417 / sel.sum(), n1822, 100 * n1822 / sel.sum(),
            *np.percentile(R["amp1417"][sel], (50, 90)), R["amp1417"][sel].max(), *np.percentile(R["amp1822"][sel], (50, 90)), R["amp1822"][sel].max(), ex[i], *ci(bs), f[i]))
    pr("\n  4b. Same, engaged windows with hands-off |bar| < 400 and by regime -- 14-17 Hz present share and amp p90:")
    pr("  %-9s | %s" % ("route", " | ".join("%-26s" % (r[0] + ": n / 14-17 % / amp p90") for r in REGIMES)))
    for tag in ALL:
        parts = []
        for k, (lab, lo, hi) in enumerate(REGIMES):
            sel = (R["tag"] == tag) & (R_reg == k) & (R["tq"] < 400)
            if sel.sum() < 5:
                parts.append("%4d (thin)" % sel.sum()); continue
            n1417 = ((sel & pres) & (R["f0"] >= 14) & (R["f0"] < 17)).sum()
            parts.append("%4d / %5.2f / %5.0f" % (sel.sum(), 100 * n1417 / sel.sum(), np.percentile(R["amp1417"][sel], 90)))
        pr("  %-9s | %s" % (tag, " | ".join("%-26s" % p for p in parts)))
    pr("\n  4c. f0 of present windows vs |angle| and vs regime, per route (median f0 in |ang| bins 0-5 / 5-20 / 20-60 / > 60 deg): does the line's frequency follow the operating point?")
    pr("  %-9s | %-40s | %-40s" % ("route", "median f0 by |ang| bin (n)", "median f0 by regime (n)"))
    for tag in ALL:
        ps = (R["tag"] == tag) & pres
        pa = []
        for a_, b_ in ((0, 5), (5, 20), (20, 60), (60, 999)):
            s = ps & (R["ang"] >= a_) & (R["ang"] < b_)
            pa.append("%5.2f (%3d)" % (np.median(R["f0"][s]), s.sum()) if s.sum() >= 3 else "  -   (%3d)" % s.sum())
        pk = []
        for k in range(3):
            s = ps & (R_reg == k)
            pk.append("%5.2f (%3d)" % (np.median(R["f0"][s]), s.sum()) if s.sum() >= 3 else "  -   (%3d)" % s.sum())
        pr("  %-9s | %-40s | %-40s" % (tag, "  ".join(pa), "  ".join(pk)))
    pr("\n  4d. Two lines at once?  Among V289 present windows: share where BOTH a 14-17 Hz and an 18-22 Hz peak exceed prominence 8 (a second, weaker line beside the tracked one):")
    for tag in ALL:
        g = G[tag]; sel = np.flatnonzero((R["tag"] == tag) & pres)
        both = 0; only16 = 0; only20 = 0
        for i in sel:
            s = int(np.searchsorted(g["tr"], R["t"][i])); x = g["bar"][s:s + W]
            f16, p16 = CEN.line_of(x, FS, 14.0, 17.0); f20, p20 = CEN.line_of(x, FS, 18.0, 22.0)
            b16 = np.isfinite(p16) and p16 >= 8; b20 = np.isfinite(p20) and p20 >= 8
            both += b16 and b20; only16 += b16 and not b20; only20 += b20 and not b16
        n = max(len(sel), 1)
        pr("  %-9s present n %4d : both %5.1f %%  only 14-17 %5.1f %%  only 18-22 %5.1f %%  neither %5.1f %%" % (
            tag, len(sel), 100 * both / n, 100 * only16 / n, 100 * only20 / n, 100 * (len(sel) - both - only16 - only20) / n))

    with open(os.path.join(M.SCR, "grind1_census_v289_agnostic.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote", os.path.join(M.SCR, "grind1_census_v289_agnostic.txt"))


if __name__ == "__main__":
    main()
