# -*- coding: utf-8 -*-
"""studies/grind/grind1_census_v289_regimes.py -- second pass on the V289 census (team-lead, 2026-09-09): every table SPLIT BY
SPEED REGIME (< 8 / 8-18 / > 18 m/s), because both V289 bookmarks sit at 3-5 m/s and 70-140 deg of wheel angle while the
highway segments (r62 segs 9-12, ~25 m/s) are the yardstick regime; and b7 scored ENGAGED-ONLY with the 3 s after every
SCA fall excluded (the cave keeps running through Honda's disengage fade).

Reads the main run's stage cache (_scratch/grind1_census_v289_r62_r63_cache.pkl: window census R/pres, episodes, hot masks)
so the yardstick is the SAME detector, and re-loads the routes for the per-frame work.  Writes
_scratch/grind1_census_v289_regimes.txt.  Subagent `census62`.  Analysis only.
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

FS, FST = 100.0, 50.0
LO, HI, CAP = 18.0, 22.0, 122
ALL, V282_ROUTES, V288_TAG, V289_ROUTES, ARMS, GRP = M.ALL, M.V282_ROUTES, M.V288_TAG, M.V289_ROUTES, M.ARMS, M.GRP
ci, boot_stat = M.ci, M.boot_stat
REGIMES = (("< 8 m/s", 0.0, 8.0), ("8-18 m/s", 8.0, 18.0), ("> 18 m/s", 18.0, 99.0))
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def main():
    rng = np.random.default_rng(20260910)
    cells = {k: GI.read_cells(p) for k, p in CEN.IMG.items() if k in ("V282", "V288", "V289")}
    CACHED = pickle.load(open(M.CACHE_P, "rb"))
    R, pres, episodes = CACHED["R"], CACHED["pres"], CACHED["episodes"]
    G, B4 = {}, {}
    for tag in ALL:
        G[tag] = WIRE.load_route(tag, cells[CEN.CELL_OF[tag]])
        B4[tag] = M.load_b4(tag, G[tag])
        G[tag]["hot"] = CACHED["hot"][tag]
        G[tag]["marks"] = M.marks_of(tag)
        g = G[tag]
        # b7 scoring mask: engaged AND not within 3 s after any SCA falling edge
        sca = g["sca"] > 0.5
        fall = np.flatnonzero(np.diff(sca.astype(int)) == -1) + 1
        post = np.zeros(len(sca), bool)
        for i in fall:
            post[i:i + 300] = True
        g["b7mask"] = g["eng"] & ~post
        g["reg"] = np.digitize(g["vego"], [8.0, 18.0])          # 0/1/2
        print("loaded", tag, flush=True)
    R_reg = np.digitize(R["v"], [8.0, 18.0])
    for e in episodes:
        e["reg"] = int(np.digitize(e["v"], [8.0, 18.0]))

    pr("=" * 168)
    pr("V289 CENSUS, SECOND PASS -- EVERY TABLE BY SPEED REGIME (< 8 / 8-18 / > 18 m/s); b7 engaged-only minus 3 s after each SCA fall")
    pr("=" * 168)

    # ---------------------------------------------------------------- 1. exposure + presence by regime
    pr("\n1. EXPOSURE (engaged s) and PRESENCE (%% of 2 s windows present; amp p50/p90/max) by regime")
    pr("  %-9s | %-36s | %-36s | %-36s" % ("arm", *[r[0] + ": eng s | n win | pres % | amp" for r in REGIMES]))
    for name, tags in ARMS:
        parts = []
        for k, (lab, lo, hi) in enumerate(REGIMES):
            secs = sum(((G[t]["eng"]) & (G[t]["reg"] == k)).sum() / FS for t in tags)
            sel = np.isin(R["tag"], tags) & (R_reg == k)
            if sel.sum() >= 5:
                parts.append("%5.0f | %4d | %5.1f%% | %3.0f/%3.0f/%3.0f" % (secs, sel.sum(), 100 * pres[sel].mean(), *np.percentile(R["amp"][sel], (50, 90)), R["amp"][sel].max()))
            else:
                parts.append("%5.0f | %4d | (thin)" % (secs, sel.sum()))
        pr("  %-9s | %-36s | %-36s | %-36s" % (name, *parts))

    # ---------------------------------------------------------------- 2. episodes by regime
    pr("\n2. EPISODES by regime (regime = mean vEgo over the episode): n, rate per engaged hour of that regime [gamma-Poisson CI], class split, env peak p50/p90/max, dur p50/p90")
    pr("  %-9s %-9s %4s %7s %-20s | %-24s | %-16s | %-14s" % ("arm", "regime", "n", "eng s", "ep/h [CI]", "BURST/SUST/RIDE %", "env p50/p90/max", "dur p50/p90 s"))
    EPR = {}
    for name, tags in ARMS:
        for k, (lab, lo, hi) in enumerate(REGIMES):
            es = [e for e in episodes if e["tag"] in tags and e["reg"] == k]
            secs = sum(((G[t]["eng"]) & (G[t]["reg"] == k)).sum() / FS for t in tags)
            n = len(es)
            EPR[(name, k)] = (n, secs, es)
            if secs < 30:
                pr("  %-9s %-9s %4d %7.0f   (thin exposure)" % (name, lab, n, secs)); continue
            rate = 3600 * n / secs
            lo_ = 3600 * stats.chi2.ppf(0.025, 2 * n) / 2 / secs if n > 0 else 0.0
            hi_ = 3600 * stats.chi2.ppf(0.975, 2 * n + 2) / 2 / secs
            if n >= 3:
                cl = np.array([e["cls"] for e in es]); ev = np.array([e["env"] for e in es]); d = np.array([e["dur"] for e in es])
                pr("  %-9s %-9s %4d %7.0f %5.0f [%4.0f, %4.0f]     | %3.0f / %3.0f / %3.0f          | %4.0f/%4.0f/%4.0f   | %5.2f / %5.2f" % (
                    name, lab, n, secs, rate, lo_, hi_, *[100 * np.mean(cl == c) for c in ("BURST", "SUSTAINED", "RIDE-ALONG")],
                    *np.percentile(ev, (50, 90)), ev.max(), np.median(d), np.percentile(d, 90)))
            else:
                pr("  %-9s %-9s %4d %7.0f %5.0f [%4.0f, %4.0f]     | (n < 3)" % (name, lab, n, secs, rate, lo_, hi_))
    pr("\n  rate ratios by regime (V289 pool / reference, gamma-Poisson on the V289 count with the reference rate fixed):")
    for k, (lab, lo, hi) in enumerate(REGIMES):
        for ref in ("V282pool", "r39", V288_TAG):
            n, s, _ = EPR[("V289pool", k)]; nr, sr, _ = EPR[(ref, k)]
            if s < 30 or sr < 30 or nr == 0:
                continue
            rr = (n / s) / (nr / sr)
            lo_ = (stats.chi2.ppf(0.025, 2 * n) / 2 / s) / (nr / sr) if n > 0 else 0.0
            hi_ = (stats.chi2.ppf(0.975, 2 * n + 2) / 2 / s) / (nr / sr)
            pr("  %-9s V289pool / %-9s = %.2f [%.2f, %.2f]   (n %d in %.0f s vs %d in %.0f s)" % (lab, ref, rr, lo_, hi_, n, s, nr, sr))

    # ---------------------------------------------------------------- 3. decay slopes by regime (the prediction test)
    pr("\n3. PREDICTION TEST by regime: per-episode decay slope gd (/s), tau_dn, zeta_dn, frac gd <= -1/s, SUSTAINED share; bootstrap by episode")
    pr("  %-9s %-9s %4s | %-24s %-16s %-22s %8s %8s" % ("arm", "regime", "n", "gd p50 [CI]", "tau_dn ms", "zeta_dn p50 [CI]", "gd<=-1", "SUST %"))
    GDR = {}
    for name, tags in ARMS:
        for k, (lab, lo, hi) in enumerate(REGIMES):
            es = [e for e in episodes if e["tag"] in tags and e["reg"] == k and np.isfinite(e["gd"]) and np.isfinite(e["gu"])]
            if len(es) < 3:
                pr("  %-9s %-9s %4d   (thin)" % (name, lab, len(es))); continue
            gd = np.array([e["gd"] for e in es]); f0 = np.array([e["f0"] for e in es]); z = np.abs(gd) / (2 * np.pi * f0)
            cl = np.array([e["cls"] for e in es])
            GDR[(name, k)] = gd
            cgd = boot_stat(gd, np.median, rng, 2000); cz = boot_stat(z, np.median, rng, 2000)
            pr("  %-9s %-9s %4d | %6.2f [%6.2f,%6.2f]    %6.0f           %6.4f [%6.4f,%6.4f]  %8.2f %8.0f" % (
                name, lab, len(es), np.median(gd), *cgd, 1000 / max(-np.median(gd), 1e-9), np.median(z), *cz, np.mean(gd <= -1.0), 100 * np.mean(cl == "SUSTAINED")))
    pr("  decay-rate ratios |gd| V289 pool / reference by regime (prediction ~1.7):")
    for k, (lab, lo, hi) in enumerate(REGIMES):
        for ref in ("V282pool", "r39", V288_TAG):
            if ("V289pool", k) not in GDR or (ref, k) not in GDR:
                continue
            ga, gb = np.abs(GDR[("V289pool", k)]), np.abs(GDR[(ref, k)])
            bs = [np.median(ga[rng.integers(0, len(ga), len(ga))]) / max(np.median(gb[rng.integers(0, len(gb), len(gb))]), 1e-9) for _ in range(4000)]
            pr("  %-9s |gd| V289pool / %-9s = %.2f [%.2f, %.2f]   MW p(faster) = %.3g   n %d vs %d" % (
                lab, ref, np.median(ga) / np.median(gb), *ci(bs), stats.mannwhitneyu(ga, gb, alternative="greater").pvalue, len(ga), len(gb)))

    # ---------------------------------------------------------------- 4. rung bell by regime
    pr("\n4. RUNG BELL by regime (capped-frame onsets; pre = median env -0.5..0, post = max 0..0.5; post/pre [CI]; post-peak decay slope /s):")
    pr("  %-9s %-9s %5s | %8s %8s %8s %-16s | %-22s" % ("arm", "regime", "n ev", "pre", "post", "ratio", "95% CI", "post-peak decay [CI]"))
    for name, tags in ARMS:
        rows = {k: [] for k in range(3)}
        for tag in tags:
            g, e = G[tag], G[tag]["e4"]
            d = np.diff(e["grid"]); base = e["egrid"][1:] & e["egrid"][:-1]
            cap = base & (np.abs(d) >= CAP); n = len(cap)
            env = CEN.envelope(g["bar"], 20.0, FS)
            on = np.flatnonzero(cap[20:] & ~np.array([cap[i - 20:i].any() for i in range(20, n)])) + 20
            for i in on:
                j = int(np.searchsorted(g["t"], e["tgrid"][i + 1]))
                if j - 50 < 0 or j + 101 >= len(g["t"]) or not g["eng"][j - 50:j + 101].all():
                    continue
                kpk = j + int(np.argmax(env[j:j + 50])); seg = np.log(np.maximum(env[kpk:kpk + 50], 1e-9))
                rows[int(g["reg"][j])].append((np.median(env[j - 50:j]), env[j:j + 50].max(), stats.linregress(np.arange(len(seg)) / FS, seg).slope))
        for k, (lab, lo, hi) in enumerate(REGIMES):
            rr = np.array(rows[k])
            if len(rr) < 5:
                pr("  %-9s %-9s %5d   (thin)" % (name, lab, len(rr))); continue
            pre, post, ds = rr[:, 0], rr[:, 1], rr[:, 2]
            bs = [np.median(post[j]) / max(np.median(pre[j]), 1e-9) for j in (rng.integers(0, len(rr), len(rr)) for _ in range(2000))]
            pr("  %-9s %-9s %5d | %8.1f %8.1f %8.3f [%.3f, %.3f]   | %6.2f [%6.2f, %6.2f]" % (
                name, lab, len(rr), np.median(pre), np.median(post), np.median(post) / np.median(pre), *ci(bs), np.median(ds), *boot_stat(ds, np.median, rng, 2000)))

    # ---------------------------------------------------------------- 5. band powers by regime
    pr("\n5. BAND POWER by regime, engaged (bar raw^2 / wheel rate (deg/s)^2), 6-10 / 13-17 / 18-22 / 22-24 / 24-40 Hz, and the 18-22 line excess (dB) -- segment PSDs, Hann 512")
    bands = ((6, 10), (13, 17), (18, 22), (22, 24), (24, 40))
    pr("  %-9s %-9s %-5s %5s %6s | %s | %-10s | %-18s" % ("route", "regime", "sig", "n seg", "secs", " ".join("%10s" % ("%d-%d" % b) for b in bands), "18-22 exc", "13-17 / 22-24 max exc"))
    BPR = {}
    for tag in ALL:
        g = G[tag]
        for k, (lab, lo, hi) in enumerate(REGIMES):
            runs = C20.runs(g["eng"] & (g["reg"] == k), 512)
            for sig, arr in (("bar", g["bar"]), ("wire", g["wire"] / V.CPD)):
                f, P = C88.seg_psds([arr[a:b] for a, b in runs], FS, 512)
                if len(P) < 5:
                    pr("  %-9s %-9s %-5s %5d   (thin)" % (tag, lab, sig, len(P))); continue
                bp = [C88.bandpow(f, P, a_, b_).mean() for a_, b_ in bands]
                BPR[(tag, k, sig)] = bp
                ex = C88.excess_db(f, P.mean(0))
                mx = lambda a_, b_: ex[(f >= a_) & (f <= b_)].max()
                pr("  %-9s %-9s %-5s %5d %6.0f | %s | %+9.1f  | %+6.1f / %+6.1f" % (tag, lab, sig, len(P), sum(b - a for a, b in runs) / FS,
                                                                                 " ".join("%10.3g" % v for v in bp), mx(18, 22), mx(13, 17), mx(22, 24)))
    pr("  ratios V289 route / r39 and / r5e_v288 per regime (bar; wire):")
    for t in V289_ROUTES:
        for k, (lab, lo, hi) in enumerate(REGIMES):
            for ref in ("r39", V288_TAG):
                if all((x, k, "bar") in BPR for x in (t, ref)):
                    pr("  %-9s %-9s / %-9s bar %s | wire %s" % (t, lab, ref, " ".join("%6.2f" % (BPR[(t, k, "bar")][i] / BPR[(ref, k, "bar")][i]) for i in range(5)),
                                                             " ".join("%6.2f" % (BPR[(t, k, "wire")][i] / BPR[(ref, k, "wire")][i]) for i in range(5))))

    # ---------------------------------------------------------------- 6. b7 / b5 by regime, with the SCA-fall rule
    pr("\n6. 0x14A b7 = |S-y| >= |y| and b5 = sign(S-y), V289 routes, ENGAGED-ONLY MINUS 3 s AFTER EVERY SCA FALL; by regime, in episodes, at onsets; and b5-vs-rate coherence")
    pr("  %-9s %-9s %8s | %8s %8s %8s | %8s %8s | %8s %10s" % ("route", "regime", "frames", "b7 eng", "b7 epi", "b7 onset", "b5 eng", "b5 epi", "coh@20", "ph n/rate"))
    for tag in V289_ROUTES:
        g, b = G[tag], B4[tag]
        on = np.zeros(len(g["eng"]), bool)
        for e in episodes:
            if e["tag"] == tag:
                on[max(0, e["a"] - 25):e["a"] + 25] = True
        rate14 = np.interp(b["t"], g["t"], g["wire"]) / V.CPD
        have14 = np.interp(b["t"], g["t"], g["have18"].astype(float)) > 0.5
        nsig = 1.0 - 2.0 * b["bit5"]
        for k, lab in [(kk, r[0]) for kk, r in enumerate(REGIMES)] + [(None, "ALL")]:
            m = g["b7mask"] & ((g["reg"] == k) if k is not None else True)
            h = m & g["hot"]; o = m & on
            m14 = (np.interp(b["t"], g["t"], (m & g["hot"]).astype(float)) > 0.5) & have14
            runs = C20.runs(m14, 256)
            f, coh, ph, gain, n = WIRE.csd_pool([nsig[a_:b_] for a_, b_ in runs], [rate14[a_:b_] for a_, b_ in runs], FS, 256)
            pr("  %-9s %-9s %8d | %8.3f %8s %8s | %8.3f %8s | %8s %10s" % (
                tag, lab, m.sum(), g["bit7"][m].mean(), "%.3f" % g["bit7"][h].mean() if h.sum() else "-", "%.3f" % g["bit7"][o].mean() if o.sum() else "-",
                g["bit5"][m].mean(), "%.3f" % g["bit5"][h].mean() if h.sum() else "-",
                "%.2f" % WIRE.at(f, coh, 20.04) if n else "-", "%.1f" % WIRE.circ_at(f, ph, 20.04) if n else "-"))
    pr("  (prediction for b7: 0.10-0.11 engaged at 100 Hz instants, 0.12-0.37 in grinding windows.  coh/phase = episode frames of that regime.)")

    # ---------------------------------------------------------------- 7. the bookmark windows
    pr("\n7. THE BOOKMARK WINDOWS: -6..0 s before each bookmark (and 0..+3 s after), per second: v, |ang|, |bar|, idx, bar 18-22 env (raw), wheel-rate 18-22 env (deg/s), line f, b7, b5")
    for tag in (V288_TAG,) + V289_ROUTES:
        g = G[tag]
        env = CEN.envelope(g["bar"], 20.0, FS); envr = CEN.envelope(g["wire"], 20.0, FS) / V.CPD
        for mk in g["marks"]:
            pr("  %s bookmark %.1f s:" % (tag, mk))
            pr("    %6s %5s %5s %6s %5s %8s %8s %6s %5s %5s %4s" % ("t-mk", "v", "|ang|", "|bar|", "idx", "env bar", "env rate", "f Hz", "b7", "b5", "eng"))
            for dt in range(-6, 4):
                a = int(np.searchsorted(g["tr"], mk + dt)); b_ = min(len(g["tr"]), a + 100)
                if a >= len(g["tr"]) or b_ - a < 50:
                    continue
                f0, prom = CEN.line_of(g["bar"][a:b_], FS)
                pr("    %6d %5.1f %5.0f %6.0f %5.0f %8.0f %8.2f %6.1f %5.2f %5.2f %4.2f" % (
                    dt, g["vego"][a:b_].mean(), np.median(np.abs(g["ang"][a:b_])), np.median(np.abs(g["bar"][a:b_])), np.median(g["idx"][a:b_]),
                    env[a:b_].max(), envr[a:b_].max(), f0 if np.isfinite(f0) and prom >= 8 else np.nan, g["bit7"][a:b_].mean(), g["bit5"][a:b_].mean(), g["eng"][a:b_].mean()))

    with open(os.path.join(M.SCR, "grind1_census_v289_regimes.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote", os.path.join(M.SCR, "grind1_census_v289_regimes.txt"))


if __name__ == "__main__":
    main()
