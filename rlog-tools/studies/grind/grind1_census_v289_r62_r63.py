# -*- coding: utf-8 -*-
"""studies/grind/grind1_census_v289_r62_r63.py -- the V282 GRIND #1 census (grind1_census_v282.py), UNCHANGED in
every threshold, run on the first two V289 rev 1 routes

    r62_v289 = 75604b0a432fdc89_00000062--1c7daa54e8   (17 segs, 2026-09-09, one bookmark)
    r63_v289 = 75604b0a432fdc89_00000063--1d4b188022   (12 segs, 2026-09-09, one bookmark)

side by side with the two yardsticks r39 (V282) and r5e_v288 (V288 rev 2), plus r3a/r3c for the V282 pool,
and the endpoints pre-registered for V289 (docs/STATE.md "RISK BEFORE THE DRIVE", 2026-09-09):

  1  the exact V282 census columns: presence, episode rate /engaged h, envelope p50/p90/max, line frequency,
     D-clamp bind duty (1 kHz mirror; V289 cells = V282 + the fb pole 875/2301, the notch is DOWNSTREAM of the
     D term so the bind predicate is unchanged in form), the capped-frame rung bell, presence duty per stratum;
  2  THE V289 PREDICTION TEST: decay / rise time constants of the 18-22 Hz rings (GI.growth_fit's log-envelope
     slopes, the same numbers wire_0xe4_burst_damping.py reports as tau_up / tau_dn), the free-decay damping
     ratio on command-quiet stretches, fraction of episodes decaying vs sustained, duration distribution.
     PREDICTION (STATE, adversary B): rings decay ~1.7x faster (zeta 0.019 -> 0.024 on the census fit, 0.016 ->
     0.038 byte-exact step ring) and stop being sustained;
  3  REVERT SIGNATURES: a new line at 13-17 or 22-24 Hz, a sustained ~16 Hz line, new straight-road
     (|angle| < 5 deg, engaged) vibration in 15-40 Hz -- same segment-PSD normalisation as the V288 census;
  4  H2 re-test on these routes: 0xE4 change cadence, gap histogram, slew-cap hits, the 20 Hz line's share in the
     command vs in the 0x18F wheel rate (the echo test) -- one table;
  5  what else is on the wire in a grinding window: driver torque, vEgo, angle, and the b4.5 = sign(S - y) vs
     0x18F wheel-rate cross-spectrum at the line (the loop's phase at 20 Hz, measured for the first time), with
     the 0x14A-vs-0x18F arrival offset stated.

METHOD FIDELITY.  Every census function is IMPORTED from grind1_census_v288_r5e.py (which copied them verbatim
from grind1_census_v282.main()); the V282 reproduction assertion is re-run here before any V289 table prints.
Loader: wire_0xe4_20hz.load_route.  Cells: V289 image (asserted = V282 in every cell EXCEPT fb_a/fb_b = 875/2301).
Caches: analysis-2020accord/_scratch/cache/v280/{r62_v289,r63_v289}{,_b4}.npz + _marks.json, written by
extract_r62_r63_v280cache.py (verbatim copy of the r5e builder).  Subagent `census62`, 2026-09-09.
Analysis only: builds nothing, sends nothing.

Run: python grind1_census_v289_r62_r63.py     (writes _scratch/grind1_census_v289_r62_r63.txt beside it)
"""
import hashlib
import json
import os
import pickle
import re
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
import grind_incident_r35 as GI               # noqa: E402
import grind1_census_v282 as CEN              # noqa: E402  helpers + dicts; main() not run
import grind1_census_v288_r5e as C88          # noqa: E402  the copied pipeline (functions only; main() not run)
import wire_0xe4_20hz as WIRE                 # noqa: E402  load_route, fine_line, welch_pool, bandamp, csd_pool

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FS1K, FST = 100.0, 1000.0, 50.0
LO, HI = 18.0, 22.0
CAP = 122
V282_ROUTES = ("r39", "r3a", "r3c")
V288_TAG = "r5e_v288"
V289_ROUTES = ("r62_v289", "r63_v289")
ALL = V282_ROUTES + (V288_TAG,) + V289_ROUTES
ARMS = [("r39", ("r39",)), (V288_TAG, (V288_TAG,)), ("r62_v289", ("r62_v289",)), ("r63_v289", ("r63_v289",)),
        ("V289pool", V289_ROUTES), ("V282pool", V282_ROUTES)]
V289_IMG = (LG.FW + "_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-"
            "NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
V289_SHA = "f0c10c29752d2b9bc4ec510800cd4de58166ebbb87f05613b5ee8e7af339a3ed"
CEN.IMG["V289"] = V289_IMG
for _t in V289_ROUTES:
    CEN.CELL_OF[_t] = "V289"
    CEN.GRP[_t] = "V289r1"
GRP = CEN.GRP
NB = C88.NB
ci, boot_stat = C88.ci, C88.boot_stat
STRATA_ORDER = C88.STRATA_ORDER
CACHE_P = os.path.join(SCR, "grind1_census_v289_r62_r63_cache.pkl")
CACHE_288 = os.path.join(SCR, "grind1_census_v288_r5e_cache.pkl")
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def marks_of(tag):
    p = os.path.join(C20.CACHE, tag + "_marks.json")
    if not os.path.exists(p):
        return []
    return [m["t_route"] for m in json.load(open(p))["marks"]]


def load_b4(tag, g):
    """0x14A byte 4 on its own dejittered 100 Hz clock + the same bits on the 0x18F frame axis (nearest)."""
    B = dict(np.load(os.path.join(C20.CACHE, tag + "_b4.npz")))
    k14, P14, tn14, res14 = C20.dejitter(B["t14b"].astype(float), 0.01, 100)
    b4 = B["b4"].astype(int)
    out = dict(t=tn14, P=P14, b4=b4, traw=B["t14b"].astype(float))
    for n in range(8):
        out["bit%d" % n] = (b4 >> n) & 1
        g["bit%d" % n] = np.round(np.interp(g["t"], tn14, out["bit%d" % n].astype(float))).astype(int)
    out["eng"] = np.interp(tn14, g["t"], g["eng"].astype(float)) > 0.5
    return out


def main():
    rng = np.random.default_rng(20260909)
    # ------------------------------------------------------------------ image + cells
    sha = hashlib.sha256(open(V289_IMG, "rb").read()).hexdigest()
    assert sha == V289_SHA, "V289 image hash mismatch: %s" % sha
    cells = {k: GI.read_cells(p) for k, p in CEN.IMG.items() if k in ("V282", "V288", "V289")}
    c282, c289 = cells["V282"], cells["V289"]
    diffs = []
    for k in c282:
        a_, b_ = c282[k], c289[k]
        same = (np.array_equal(np.asarray(a_[0]), np.asarray(b_[0])) and np.array_equal(np.asarray(a_[1]), np.asarray(b_[1]))) \
            if isinstance(a_, tuple) else np.array_equal(np.asarray(a_), np.asarray(b_))
        if not same:
            diffs.append(k)
    pr("=" * 168)
    pr("GRIND #1 (18-22 Hz) EPISODE CENSUS -- V289 rev 1 first two routes r62_v289 / r63_v289 vs r39 (V282) and r5e_v288 (V288), SAME YARDSTICK")
    pr("=" * 168)
    pr("V289 image sha256 %s (verified)" % sha)
    pr("cells read from the V289 image vs the V282 image (GI.read_cells, %d keys): differ in %s ; fb pole V282 %d/%d -> V289 %d/%d" % (
        len(c282), diffs, c282["fb_a"], c282["fb_b"], c289["fb_a"], c289["fb_b"]))
    assert sorted(diffs) == ["fb_a", "fb_b"] and (c289["fb_a"], c289["fb_b"]) == (875, 2301), "V289 cal delta is not exactly the fb pole"

    G, B4 = {}, {}
    for tag in ALL:
        G[tag] = WIRE.load_route(tag, cells[CEN.CELL_OF[tag]])
        g = G[tag]
        B4[tag] = load_b4(tag, g)
        g["marks"] = marks_of(tag)
        print("loaded %s: %.1f s, %.1f s engaged, %d bookmarks" % (tag, g["tr"][-1], g["eng"].sum() / FS, len(g["marks"])), flush=True)

    # ------------------------------------------------------------------ 0a. build attribution from the tap (byte-4 semantics)
    pr("\n0a. BUILD ATTRIBUTION FROM THE TAP (0x14A byte 4; V289: b7 = |S-y| >= |y| reads 1 while DISENGAGED, b5 = sign(S-y) duty ~0.5 engaged)")
    pr("  %-9s %-14s %8s | %s | %s" % ("route", "label", "eng s", "engaged duties b7 b6 b5 b4 b3", "DISENGAGED duties b7 b6 b5 b4 b3"))
    for tag in ALL:
        b = B4[tag]; e = b["eng"]
        pr("  %-9s %-14s %8.0f | %s | %s" % (tag, GRP[tag], e.sum() / FS,
                                             "  ".join("%.3f" % b["bit%d" % n][e].mean() for n in (7, 6, 5, 4, 3)),
                                             "  ".join("%.3f" % b["bit%d" % n][~e].mean() for n in (7, 6, 5, 4, 3))))
    for tag in V289_ROUTES:
        b = B4[tag]
        assert b["bit7"][~b["eng"]].mean() > 0.90 and 0.40 < b["bit5"][b["eng"]].mean() < 0.60, "%s does not carry the V289 tap signature" % tag
    pr("  => r62/r63 carry the V289 signature (b7 > 0.95 disengaged -- not 1.000: the notch state decays for ~50 ms after each disengage and the lateral-engaged")
    pr("     mask is interpolated; b5 = 0.500 engaged).  r5e_v288 / r39 read b7 = 0.00 disengaged.  [EVIDENCE: wire]")

    # ------------------------------------------------------------------ 0b. reproduction of the V282 census
    pr("\n0b. REPRODUCTION of grind1_census_v282.py on r39/r3a/r3c with the imported pipeline, vs the stored output")
    ref_txt = open(os.path.join(SCR, "grind1_census_v282.txt"), encoding="utf-8").read()
    CACHED = pickle.load(open(CACHE_P, "rb")) if os.path.exists(CACHE_P) else {}
    if "R" in CACHED and set(CACHED["hot"]) == set(ALL):
        R, pres, episodes = CACHED["R"], CACHED["pres"], CACHED["episodes"]
        for tag in ALL:
            G[tag]["hot"] = CACHED["hot"][tag]
        pr("  (window census + episodes loaded from %s)" % os.path.basename(CACHE_P))
    else:
        R, pres = C88.window_census(G, ALL)
        episodes = C88.extract_episodes(G, R, pres, ALL)
        CACHED.update(R=R, pres=pres, episodes=episodes, hot={tag: G[tag]["hot"] for tag in ALL})
        pickle.dump(CACHED, open(CACHE_P, "wb"))
    ok = True
    for tag in V282_ROUTES:
        m = re.search(r"^\s+%s\s+V282 LAF[\d.]+\s+(\d+)\s+(\d+)\s+" % tag, ref_txt, re.M)
        n_ref, p_ref = int(m.group(1)), int(m.group(2))
        sel = R["tag"] == tag
        n_new, p_new = int(sel.sum()), int((sel & pres).sum())
        e_ref = int(re.search(r"total episodes: \d+\s+\(.*?%s=(\d+)" % tag, ref_txt).group(1))
        e_new = sum(1 for e in episodes if e["tag"] == tag)
        m2 = re.search(r"^\s+%s\s+V282 LAF[\d.]+\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$" % tag, ref_txt, re.M)
        split_ref = tuple(int(m2.group(i)) for i in (2, 3, 4))
        es = [e for e in episodes if e["tag"] == tag]
        split_new = (sum(1 for e in es if e["cls"] == "BURST"), sum(1 for e in es if e["cls"] == "SUSTAINED"),
                     sum(1 for e in es if e["cls"] == "RIDE-ALONG"))
        good = (n_ref, p_ref, e_ref, split_ref) == (n_new, p_new, e_new, split_new)
        ok &= good
        pr("  %-4s windows n %d/%d present %d/%d | episodes %d/%d | BURST/SUST/RIDE %s/%s  -> %s" % (
            tag, n_new, n_ref, p_new, p_ref, e_new, e_ref, split_new, split_ref, "MATCH" if good else "MISMATCH"))
    tr282 = C88.transient_enrichment(G, episodes, V282_ROUTES)
    thr_cmd, thr_idx = C88.tick_thresholds(G, V282_ROUTES)
    tk282 = C88.tick_enrichment(G, episodes, V282_ROUTES, thr_cmd, thr_idx)
    ref_tr = re.search(r"ENRICHMENT RATIO ([\d.]+)x\n.*?CI \[([\d.]+), ([\d.]+)\]x", ref_txt).groups()
    ref_tk = re.findall(r"ENRICHMENT RATIO ([\d.]+)x\n.*?CI \[([\d.]+), ([\d.]+)\]x", ref_txt)[-1]
    ref_thr = re.search(r"threshold = (\d+) raw/frame .*? threshold = ([\d.]+)/frame", ref_txt).groups()
    s_tr = ("%.2f" % tr282["enrich"], "%.2f" % tr282["ci"][0], "%.2f" % tr282["ci"][1])
    s_tk = ("%.2f" % tk282["enrich"], "%.2f" % tk282["ci"][0], "%.2f" % tk282["ci"][1])
    s_thr = ("%.0f" % thr_cmd, "%.1f" % thr_idx)
    pr("  transient enrichment %s vs stored %s ; top-1%% tick enrichment %s vs stored %s ; thresholds %s vs stored %s" % (
        s_tr, ref_tr, s_tk, ref_tk, s_thr, ref_thr))
    ok &= (s_tr == ref_tr) and (s_tk == ref_tk) and (s_thr == ref_thr)
    # and the V288 route against ITS stored census (n windows / present / episodes / split)
    ref288 = open(os.path.join(SCR, "grind1_census_v288_r5e.txt"), encoding="utf-8").read()
    m = re.search(r"^\s+r5e_v288\s+V288r2 \(r5e\)\s+(\d+)\s+(\d+)\s+", ref288, re.M)
    sel = R["tag"] == V288_TAG
    es = [e for e in episodes if e["tag"] == V288_TAG]
    m3 = re.search(r"total: .*?r5e_v288=(\d+)", ref288)
    good288 = (int(m.group(1)), int(m.group(2)), int(m3.group(1))) == (int(sel.sum()), int((sel & pres).sum()), len(es))
    pr("  r5e_v288 vs its stored census: windows %d/%s present %d/%s episodes %d/%s -> %s" % (
        sel.sum(), m.group(1), (sel & pres).sum(), m.group(2), len(es), m3.group(1), "MATCH" if good288 else "MISMATCH"))
    ok &= good288
    pr("  => REPRODUCTION %s" % ("EXACT" if ok else "FAILED -- stop"))
    assert ok, "the imported pipeline does not reproduce the stored censuses"

    # strata
    SM, expo = {}, {st: {} for st in STRATA_ORDER}
    for tag in ALL:
        g = G[tag]
        SM[tag] = {st: (mk & g["eng"]) for st, mk in C88.strata_masks(g).items()}
        for st in STRATA_ORDER:
            expo[st][tag] = SM[tag][st].sum() / FS

    # ------------------------------------------------------------------ 1. exposure
    pr("\n" + "=" * 168)
    pr("1. EXPOSURE per stratum (engaged s) -- r39, V282 pool, r5e_v288, r62, r63, V289 pool")
    pr("=" * 168)
    pr("  %-28s %8s %8s %8s %8s %8s %8s   %s" % ("stratum", "r39", "V282pool", "r5e_v288", "r62", "r63", "V289pool", "flag (<30 s on a V289 route)"))
    for st in ("ALL engaged",) + STRATA_ORDER:
        if st == "ALL engaged":
            val = {t: G[t]["eng"].sum() / FS for t in ALL}
        else:
            val = {t: expo[st][t] for t in ALL}
        v282 = sum(val[t] for t in V282_ROUTES); v289 = sum(val[t] for t in V289_ROUTES)
        flag = " ".join(t for t in V289_ROUTES if val[t] < 30)
        pr("  %-28s %8.0f %8.0f %8.0f %8.0f %8.0f %8.0f   %s" % (st, val["r39"], v282, val[V288_TAG], val["r62_v289"], val["r63_v289"], v289, ("THIN: " + flag) if flag else ""))
    pr("\n  drive character (engaged frames): speed p10/p50/p90 m/s ; hands-on |bar|>700 share ; median idx ; slew-capped share ; |ang| p50/p90")
    for tag in ALL:
        g = G[tag]; e = g["e4"]; m = g["eng"]
        d = np.diff(e["grid"]); base = e["egrid"][1:] & e["egrid"][:-1]
        pr("  %-9s %-14s v %4.1f/%4.1f/%4.1f  hands-on %.3f  idx p50 %3.0f  capped %.3f  |ang| %4.0f/%4.0f  n eng %6d" % (
            tag, GRP[tag], *np.percentile(g["vego"][m], (10, 50, 90)), np.mean(np.abs(g["bar"][m]) > 700), np.median(g["idx"][m]),
            np.mean(np.abs(d[base]) >= CAP), *np.percentile(np.abs(g["ang"][m]), (50, 90)), m.sum()))

    # ------------------------------------------------------------------ 2. presence census
    pr("\n" + "=" * 168)
    pr("2. PRESENCE CENSUS (2 s windows, 0.5 s step, engaged; present = 15-26 Hz prominence >= 8 AND bar 18-22 >= 40 raw)")
    pr("=" * 168)
    pr("  %-9s %-14s %6s %6s %6s %-16s %-28s %-20s" % ("route", "label", "n win", "pres", "%", "95% CI (windows)", "f mean +- sd (p10/p90)", "amp p50/p90/max raw"))
    for name, tags in [(t, (t,)) for t in ALL] + [("V282pool", V282_ROUTES), ("V289pool", V289_ROUTES)]:
        sel = np.isin(R["tag"], tags)
        p = pres[sel].astype(float)
        cc = boot_stat(p, np.mean, rng, 2000)
        f0 = R["f0"][sel & pres]
        pr("  %-9s %-14s %6d %6d %6.1f [%5.1f, %5.1f]    %5.2f +- %4.2f (%5.2f/%5.2f)   %4.0f/%4.0f/%4.0f" % (
            name, GRP.get(name, ""), sel.sum(), (sel & pres).sum(), 100 * p.mean(), 100 * cc[0], 100 * cc[1],
            f0.mean(), f0.std(), *np.percentile(f0, (10, 90)), *np.percentile(R["amp"][sel], (50, 90)), R["amp"][sel].max()))
    pr("  (window CI = bootstrap over windows; windows overlap 4x, so these CIs are optimistic by ~2x)")
    pr("\n  2b. Operator's stratum -- engaged, hands-off (|bar| < 400), creep 1-3 m/s:")
    pr("  %-9s %7s %7s %7s %9s %9s %9s" % ("route", "n win", "pres", "%", "amp p50", "amp p90", "amp max"))
    for tag in ALL:
        sel = (R["tag"] == tag) & R["creep"] & R["hoff"]
        if sel.sum() < 5:
            pr("  %-9s %7d   (too thin)" % (tag, sel.sum())); continue
        pr("  %-9s %7d %7d %7.0f %9.0f %9.0f %9.0f" % (tag, sel.sum(), (sel & pres).sum(), 100 * pres[sel].mean(),
                                                     np.median(R["amp"][sel]), np.percentile(R["amp"][sel], 90), R["amp"][sel].max()))
    pr("\n  2c. Presence %% and bar 18-22 amp p50/p90 PER STRATUM (window assigned by its median |bar| / |ang| / mean rate):")
    wfb = {"FB: hands-on |bar|>700": R["tq"] > 700, "FB: |ang|>60 deg": R["ang"] > 60, "FB: wheel>25 deg/s": R["rate"] > 25}
    wfb["FB-dominated (any)"] = wfb["FB: hands-on |bar|>700"] | wfb["FB: |ang|>60 deg"] | wfb["FB: wheel>25 deg/s"]
    wfb["REF-dominated (none)"] = ~wfb["FB-dominated (any)"]
    wfb["REF & creep 1-3 m/s"] = wfb["REF-dominated (none)"] & (R["v"] >= 1) & (R["v"] < 3)
    wfb["REF & 3-8 m/s"] = wfb["REF-dominated (none)"] & (R["v"] >= 3) & (R["v"] < 8)
    wfb["REF & 8-15 m/s"] = wfb["REF-dominated (none)"] & (R["v"] >= 8) & (R["v"] < 15)
    wfb["REF & >=15 m/s"] = wfb["REF-dominated (none)"] & (R["v"] >= 15)
    wfb["REF & hands-off |bar|<400"] = wfb["REF-dominated (none)"] & (R["tq"] < 400)
    cols = [("r39", ("r39",)), ("V282pool", V282_ROUTES), ("r5e_v288", (V288_TAG,)), ("r62", ("r62_v289",)), ("r63", ("r63_v289",)), ("V289pool", V289_ROUTES)]
    pr("  %-28s | %s" % ("stratum", " | ".join("%-22s" % c[0] for c in cols)))
    f = lambda s: ("%4d %5.1f%% %4.0f/%4.0f" % (s.sum(), 100 * pres[s].mean(), np.median(R["amp"][s]), np.percentile(R["amp"][s], 90))) if s.sum() >= 5 else ("%4d (thin)" % s.sum())
    for st in STRATA_ORDER:
        pr("  %-28s | %s" % (st, " | ".join("%-22s" % f(np.isin(R["tag"], tags) & wfb[st]) for _, tags in cols)))

    # ------------------------------------------------------------------ 3. episodes
    pr("\n" + "=" * 168)
    pr("3. EPISODES (contiguous >= 0.5 s line-present, engaged) -- rate, class split, duration, amplitude, frequency")
    pr("=" * 168)
    pr("  total: %s" % ", ".join("%s=%d" % (t, sum(1 for e in episodes if e["tag"] == t)) for t in ALL))
    pr("\n  %-9s %-9s %6s %6s %6s %10s %8s %8s %8s %6s %6s %6s %6s %7s %6s %6s %8s %8s" % (
        "route", "class", "t0 s", "dur", "f0", "env pk", "18-22", "6-10", "corr7", "v", "|ang|", "rate", "idx", "|tq|", "trans", "creep", "gu /s", "gd /s"))
    for e in [e for e in episodes if e["tag"] in V289_ROUTES]:
        pr("  %-9s %-9s %6.1f %6.2f %6.1f %10.0f %8.0f %8.0f %8.2f %6.1f %6.0f %6.1f %6.0f %7.0f %6s %6s %8.2f %8.2f" % (
            e["tag"], e["cls"], e["t0"], e["dur"], e["f0"], e["env"], e["amp"], e["amp6"],
            e["corr7"] if np.isfinite(e["corr7"]) else -9, e["v"], abs(e["ang0"]), e["rate0"], e["idx0"], e["hands"],
            "Y" if e["trans"] else "n", "Y" if e["creep_onset"] else "n", e["gu"], e["gd"]))
    for tag in ALL:
        if G[tag]["marks"]:
            pr("  operator bookmarks %s (route-relative s) vs episodes: " % tag + " ; ".join(
                "%.1f -> %s" % (mk, ", ".join("%.1f-%.1f %s env %.0f f %.1f" % (e["t0"], e["t1"], e["cls"], e["env"], e["f0"]) for e in episodes
                                               if e["tag"] == tag and e["t0"] - 5 <= mk <= e["t1"] + 5) or "no episode within 5 s") for mk in G[tag]["marks"]))

    def rate_blocks(tags):
        cnt, exp_ = [], []
        for tag in tags:
            g = G[tag]
            eng_idx = np.flatnonzero(g["eng"])
            blk_of = np.full(len(g["eng"]), -1); blk_of[eng_idx] = np.arange(len(eng_idx)) // 3000
            nb = blk_of.max() + 1
            c = np.zeros(nb); x = np.bincount(blk_of[eng_idx], minlength=nb) / FS
            for e in episodes:
                if e["tag"] == tag:
                    c[blk_of[e["a"]]] += 1
            cnt.append(c); exp_.append(x)
        return np.concatenate(cnt), np.concatenate(exp_)

    pr("\n  3a. Episode rate per engaged HOUR (block bootstrap over 30 s engaged blocks, n=%d) and class split (bootstrap over episodes):" % NB)
    pr("  %-9s %6s %8s %10s %-18s | %-22s %-22s %-22s" % ("arm", "n ep", "eng s", "ep/h", "95% CI", "BURST % [CI]", "SUSTAINED % [CI]", "RIDE-ALONG % [CI]"))
    RATE = {}
    for name, tags in [(t, (t,)) for t in ALL] + [("V282pool", V282_ROUTES), ("V289pool", V289_ROUTES)]:
        c, x = rate_blocks(tags)
        r = 3600 * c.sum() / x.sum()
        bs = []
        for _ in range(NB):
            j = rng.integers(0, len(c), len(c)); bs.append(3600 * c[j].sum() / max(x[j].sum(), 1))
        RATE[name] = (r, ci(bs), np.array(bs))
        es = [e for e in episodes if e["tag"] in tags]
        cl = np.array([e["cls"] for e in es])
        parts = []
        for k in ("BURST", "SUSTAINED", "RIDE-ALONG"):
            fr = (cl == k).astype(float)
            cc = boot_stat(fr, np.mean, rng) if len(fr) >= 3 else (np.nan, np.nan)
            parts.append("%4.0f%% [%3.0f,%3.0f]" % (100 * fr.mean() if len(fr) else np.nan, 100 * cc[0], 100 * cc[1]))
        pr("  %-9s %6d %8.0f %10.0f [%5.0f, %5.0f]     | %-22s %-22s %-22s" % (name, len(es), x.sum(), r, *ci(bs), *parts))
    for a_, b_ in (("V289pool", "V282pool"), ("V289pool", V288_TAG), ("V289pool", "r39"), ("r62_v289", "r39"), ("r63_v289", "r39")):
        rr = RATE[a_][2] / np.maximum(RATE[b_][2], 1e-9)
        pr("  rate ratio %s / %s = %.2f [%.2f, %.2f]" % (a_, b_, RATE[a_][0] / RATE[b_][0], *ci(rr)))

    pr("\n  3b. Duration and amplitude distributions (bootstrap CI on the median, resample episodes):")
    pr("  %-9s %6s | %-28s | %-28s | %-28s | %8s" % ("arm", "n", "dur s p50 [CI] / p90 / max", "env peak raw p50 [CI] / p90 / max",
                                                     "bar 18-22 raw p50 [CI] / p90 / max", "mean env"))
    for name, tags in ARMS:
        es = [e for e in episodes if e["tag"] in tags]
        if not es:
            pr("  %-9s %6d   (none)" % (name, 0)); continue
        d = np.array([e["dur"] for e in es]); ev = np.array([e["env"] for e in es]); am = np.array([e["amp"] for e in es])
        fmt = lambda x: "%5.2f [%5.2f,%5.2f] %6.2f %6.2f" % (np.median(x), *boot_stat(x, np.median, rng, 2000), np.percentile(x, 90), x.max())
        pr("  %-9s %6d | %-28s | %-28s | %-28s | %8.0f" % (name, len(es), fmt(d), fmt(ev), fmt(am), ev.mean()))
    e282 = [e for e in episodes if e["tag"] in V282_ROUTES]; e288 = [e for e in episodes if e["tag"] == V288_TAG]; e289 = [e for e in episodes if e["tag"] in V289_ROUTES]
    if len(e289) >= 3:
        for lab, ref in (("V282 pooled", e282), ("r5e_v288", e288)):
            pr("  Mann-Whitney V289 pooled vs %s: env peak p = %.3g ; duration p = %.3g" % (
                lab, stats.mannwhitneyu([e["env"] for e in e289], [e["env"] for e in ref]).pvalue,
                stats.mannwhitneyu([e["dur"] for e in e289], [e["dur"] for e in ref]).pvalue))

    pr("\n  3c. LINE FREQUENCY -- census f0 of present windows (the yardstick), and a fine (zero-padded, parabolic) line per episode >= 1 s:")
    pr("  %-9s %6s %7s %7s %7s %7s | %-40s | %-30s" % ("arm", "n win", "mean", "sd", "p10", "p90", "share 15-18/18-19.5/19.5-20.5/20.5-22/22-26", "fine f0 per episode p25/p50/p75 (n)"))
    for name, tags in ARMS:
        ps = np.isin(R["tag"], tags) & pres
        f0 = R["f0"][ps]
        if len(f0) < 5:
            pr("  %-9s %6d   (thin)" % (name, len(f0))); continue
        sh = [np.mean((f0 >= a_) & (f0 < b_)) for a_, b_ in ((15, 18), (18, 19.5), (19.5, 20.5), (20.5, 22), (22, 26))]
        ff = []
        for e in episodes:
            if e["tag"] in tags and e["dur"] >= 1.0:
                g = G[e["tag"]]
                ff.append(WIRE.fine_line(g["bar"][e["a"]:e["b"]], FS, 15.0, 26.0)[0])
        ff = np.array(ff)
        pr("  %-9s %6d %7.2f %7.2f %7.2f %7.2f | %-40s | %5.2f/%5.2f/%5.2f (%d)" % (
            name, len(f0), f0.mean(), f0.std(), *np.percentile(f0, (10, 90)),
            "/".join("%.0f%%" % (100 * s) for s in sh), *(np.percentile(ff, (25, 50, 75)) if len(ff) else (np.nan,) * 3), len(ff)))
    f289 = R["f0"][np.isin(R["tag"], V289_ROUTES) & pres]; f282 = R["f0"][np.isin(R["tag"], V282_ROUTES) & pres]
    if len(f289) >= 5:
        pr("  KS test, present-window f0, V289 vs V282 pooled: D = %.3f, p = %.3g ; median %.2f vs %.2f Hz" % (
            *stats.ks_2samp(f289, f282)[:2], np.median(f289), np.median(f282)))

    # ------------------------------------------------------------------ 4. onset predicates
    pr("\n" + "=" * 168)
    pr("4. ONSET PREDICATES -- the V282 census's two enrichment tests, thresholds FROZEN at the pooled-V282 values")
    pr("=" * 168)
    pr("  top-1%% thresholds (pooled V282, frozen): |dcmd| >= %.0f raw/frame, didx >= %.1f/frame." % (thr_cmd, thr_idx))
    pr("  %-9s %5s | %-44s | %-44s | %s" % ("arm", "n ep", "loose transient: P(base) P(onset) enrich [CI]", "top-1% tick: P(base) P(onset) enrich [CI]", "steady-creep onsets"))
    TK = {}
    for name, tags in (("V282pool", V282_ROUTES), (V288_TAG, (V288_TAG,)), ("r62_v289", ("r62_v289",)), ("r63_v289", ("r63_v289",)), ("V289pool", V289_ROUTES)):
        tr = C88.transient_enrichment(G, episodes, tags, seed=0); tk = C88.tick_enrichment(G, episodes, tags, thr_cmd, thr_idx, seed=1)
        TK[name] = tk
        if tr["n"] < 3:
            pr("  %-9s %5d   (thin)" % (name, tr["n"])); continue
        pr("  %-9s %5d | %.3f  %.3f  %.2fx [%.2f, %.2f]                | %.3f  %.3f  %.2fx [%.2f, %.2f]                | %d (%.0f%%)" % (
            name, tr["n"], tr["p_base"], tr["p_ep"], tr["enrich"], *tr["ci"], tk["p_base"], tk["p_ep"], tk["enrich"], *tk["ci"],
            tr["n_creep"], 100 * tr["n_creep"] / max(tr["n"], 1)))
    pr("  per-class top-1%% tick enrichment: " + " | ".join(
        "%s: %s" % (name, ", ".join("%s n=%d %.2fx [%.2f,%.2f]" % (k, v[0], v[2], *v[3]) for k, v in TK[name]["cls"].items())) for name in ("V282pool", "V289pool")))
    pr("\n  Operating point at onset (medians) vs all engaged frames:")
    pr("  %-26s %8s %8s %8s %8s %8s" % ("stratum", "n", "v p50", "|ang|p50", "rate p50", "idx p50"))
    for name, tags in (("V282pool", V282_ROUTES), (V288_TAG, (V288_TAG,)), ("V289pool", V289_ROUTES)):
        allv = np.concatenate([G[t]["vego"][G[t]["eng"]] for t in tags]); alla = np.concatenate([np.abs(G[t]["ang"][G[t]["eng"]]) for t in tags])
        allr = np.concatenate([G[t]["rate"][G[t]["eng"]] for t in tags]); alli = np.concatenate([G[t]["idx"][G[t]["eng"]] for t in tags])
        pr("  %-26s %8d %8.1f %8.0f %8.1f %8.0f" % (name + " engaged frames", len(allv), np.median(allv), np.median(alla), np.median(allr), np.median(alli)))
        es = [e for e in episodes if e["tag"] in tags]
        if es:
            pr("  %-26s %8d %8.1f %8.0f %8.1f %8.0f" % (name + " onsets", len(es), np.median([e["v"] for e in es]), np.median([abs(e["ang0"]) for e in es]),
                                                     np.median([e["rate0"] for e in es]), np.median([e["idx0"] for e in es])))
    pr("\n  4b. Episode ONSETS per engaged hour, by the onset frame's stratum (exposure = engaged s in that stratum); ratio = V289 pool / V282 pool [gamma-Poisson CI]:")
    pr("  %-28s | %-30s | %-30s | %-30s | %s" % ("stratum", "V282 pool: n / s / ep per h", "r5e_v288: n / s / ep per h", "V289 pool: n / s / ep per h", "ratio V289/V282 [CI]   ratio V289/V288"))
    for st in STRATA_ORDER:
        row = []
        for tags in (V282_ROUTES, (V288_TAG,), V289_ROUTES):
            n = sum(1 for e in episodes if e["tag"] in tags and SM[e["tag"]][st][e["a"]])
            x = sum(expo[st][t] for t in tags)
            row.append((n, x, 3600 * n / x if x > 0 else np.nan))
        r282, r288, r289 = row
        if r282[2] and r282[2] > 0 and np.isfinite(r289[2]) and r289[1] >= 30:
            lo_ = (stats.chi2.ppf(0.025, 2 * r289[0]) / 2 / r289[1]) / (r282[0] / r282[1]) if r289[0] > 0 else 0.0
            hi_ = (stats.chi2.ppf(0.975, 2 * r289[0] + 2) / 2 / r289[1]) / (r282[0] / r282[1])
            rr = "%.2f [%.2f, %.2f]" % (r289[2] / r282[2], lo_, hi_)
        else:
            rr = "(thin)"
        r88 = "%.2f" % (r289[2] / r288[2]) if r288[2] and r288[2] > 0 and np.isfinite(r289[2]) else "-"
        pr("  %-28s | %4d / %6.0f / %6.0f             | %4d / %6.0f / %6.0f             | %4d / %6.0f / %6.0f             | %s   %s" % (st, *r282, *r288, *r289, rr, r88))

    # ------------------------------------------------------------------ 5. capped frames, D-bind, rung bell
    pr("\n" + "=" * 168)
    pr("5. THE 122.88 SLEW CAP -- capped-frame enrichment, D-clamp bind duty, 18-22 Hz envelope at capped onsets (the V282/V288 endpoints)")
    pr("=" * 168)
    for tag in ALL:
        g, e = G[tag], G[tag]["e4"]
        d = np.diff(e["grid"]); base = e["egrid"][1:] & e["egrid"][:-1]
        e["d"], e["base"], e["cap"] = d, base, base & (np.abs(d) >= CAP)
        e["hot"] = np.interp(e["tgrid"], g["t"], g["hot"].astype(float))[1:] > 0.5
        e["onsets"] = np.array([int(np.searchsorted(e["tgrid"], g["t"][ep["a"]])) for ep in episodes if ep["tag"] == tag], int)
    pr("\n  5a. capped-frame fraction: baseline / in episodes / pre-onset 0.5 s / onset +-0.5 s ; and P(cap within +-0.5 s of onset) vs 1 Hz baseline:")
    pr("  %-9s %9s %9s %9s %9s | %7s %14s %14s %11s %-22s" % ("route", "baseline", "episode", "pre-onset", "onset", "n eps", "P(cap +-0.5s)", "baseline P", "enrich", "95 % CI"))
    for tag in ALL:
        e = G[tag]["e4"]; n = len(e["d"])
        w = np.zeros(n, bool); wp = np.zeros(n, bool)
        for i0 in e["onsets"]:
            w[max(0, i0 - 50):min(n, i0 + 51)] = True; wp[max(0, i0 - 50):min(n, i0)] = True
        fr = lambda s: np.mean(np.abs(e["d"])[s] >= CAP) if s.sum() else np.nan
        vals = (fr(e["base"] & ~e["hot"]), fr(e["base"] & e["hot"]), fr(e["base"] & wp), fr(e["base"] & w))
        hit = np.array([bool((e["base"][max(0, i0 - 50):min(n, i0 + 51)] & (np.abs(e["d"])[max(0, i0 - 50):min(n, i0 + 51)] >= CAP)).any()) for i0 in e["onsets"]], bool)
        idx = np.flatnonzero(e["base"])[::100]
        bh = np.array([bool((e["base"][max(0, i - 50):min(n, i + 51)] & (np.abs(e["d"])[max(0, i - 50):min(n, i + 51)] >= CAP)).any()) for i in idx])
        pb = bh.mean()
        if len(hit) >= 3 and pb > 0:
            bs = [hit[rng.integers(0, len(hit), len(hit))].mean() / pb for _ in range(NB)]
            tail = "%7d %14.3f %14.3f %11.2fx [%.2f, %.2f]x" % (len(hit), hit.mean(), pb, hit.mean() / pb, *ci(bs))
        else:
            tail = "%7d %14s %14.3f" % (len(hit), "(thin)", pb)
        pr("  %-9s %9.4f %9.4f %9.4f %9.4f | %s" % (tag, *vals, tail))

    pr("\n  5b. D-CLAMP BIND DUTY, 1 kHz mirror over EVERY engaged run >= 1 s (|dE*128/8| > 10240); E = 32*sp - fb, fb through the build's OWN pole:")
    pr("      V282 routes: V282 cells.  r5e_v288: the cave setpoint filter (as flown).  V289 routes: V289 cells (fb pole 875/2301, as flown) AND the same")
    pr("      route with V282's pole 923/1560 (counterfactual).  The notch is downstream of P+D and does not enter the bind predicate.  CI = 10 s tick blocks.")
    g0 = G["r39"]; a0, b0 = [(e["a"], e["b"]) for e in episodes if e["tag"] == "r39"][0]
    o1 = GI.simulate(g0, a0, b0, c282); o2 = C88.simulate_sp(g0, a0, b0, c282)
    assert np.array_equal(o1["T"], o2["T"]) and o1["drail"] == o2["drail"], "simulate_sp diverges from GI.simulate"
    pr("      self-check: simulate_sp(no filter) reproduces GI.simulate bit-for-bit on r39 t %.1f -- OK" % g0["tr"][a0])
    DUTY = CACHED.get("DUTY", {})
    if os.path.exists(CACHE_288):
        old = pickle.load(open(CACHE_288, "rb")).get("DUTY", {})
        for k, v in old.items():
            DUTY.setdefault(k, dict(v, cached_from="v288 census"))
    pr("  %-9s %-24s %10s %10s %12s %-18s | %10s %10s | %12s %12s" % ("route", "arithmetic", "live ticks", "binds", "duty", "95% CI", "in-episode", "outside", "P(cap|bind)", "cap frac"))
    rng5 = np.random.default_rng(5)
    for tag in ALL:
        g = G[tag]; e = g["e4"]
        capf = np.interp(g["t"], e["tgrid"][1:], (np.abs(e["d"]) >= CAP).astype(float)) > 0.5
        if tag in V282_ROUTES:
            variants = [("raw sp (V282)", None, c282)]
        elif tag == V288_TAG:
            variants = [("V288 filter K=4", C88.K_SHIFT, c282), ("filter REMOVED", None, c282)]
        else:
            variants = [("V289 pole 875/2301", None, c289), ("V282 pole 923/1560 (cf)", None, c282)]
        for lab, k, c in variants:
            if (tag, lab) in DUTY:
                r_ = DUTY[(tag, lab)]
                pr("  %-9s %-24s %10d %10d %12.5f [%.5f, %.5f] | %10.5f %10.5f | %12.3f %12.4f   (cached)" % (
                    tag, lab, r_["nlive"], r_["nb"], r_["duty"], *r_["ci"], r_["d_in"], r_["d_out"], r_["pcb"], r_["capfrac"]))
                continue
            live_all, bind_all, hot_all, cap_all = [], [], [], []
            for a, b in C20.runs(g["eng"], int(FS)):
                o = C88.simulate_sp(g, a, b, c, spfilt_k=k)
                n0 = (a - o["seg"].start) * 10; n1 = n0 + (b - a) * 10
                live_all.append(o["live"][n0:n1]); bind_all.append(o["bind"][n0:n1])
                hot_all.append(np.repeat(g["hot"][a:b], 10)); cap_all.append(np.repeat(capf[a:b], 10))
            live = np.concatenate(live_all); bind = np.concatenate(bind_all); hot = np.concatenate(hot_all); capk = np.concatenate(cap_all)
            duty = bind[live].mean()
            nblk = len(live) // 10000
            bl = bind[:nblk * 10000].reshape(nblk, 10000).sum(1); ll = live[:nblk * 10000].reshape(nblk, 10000).sum(1)
            bs = []
            for _ in range(2000):
                j = rng5.integers(0, nblk, nblk); bs.append(bl[j].sum() / max(ll[j].sum(), 1))
            d_in = bind[live & hot].mean() if (live & hot).any() else np.nan
            d_out = bind[live & ~hot].mean() if (live & ~hot).any() else np.nan
            pcb = capk[live & bind].mean() if (live & bind).any() else np.nan
            DUTY[(tag, lab)] = dict(duty=duty, ci=ci(bs), d_in=d_in, d_out=d_out, pcb=pcb, nb=int(bind[live].sum()),
                                    nlive=int(live.sum()), capfrac=float(capk[live].mean()))
            CACHED["DUTY"] = DUTY; pickle.dump(CACHED, open(CACHE_P, "wb"))
            pr("  %-9s %-24s %10d %10d %12.5f [%.5f, %.5f] | %10.5f %10.5f | %12.3f %12.4f" % (
                tag, lab, live.sum(), bind[live].sum(), duty, *ci(bs), d_in, d_out, pcb, capk[live].mean()))
    for tag in V289_ROUTES:
        v = DUTY[(tag, "V289 pole 875/2301")]; u = DUTY[(tag, "V282 pole 923/1560 (cf)")]
        pr("  => %s: the fb-pole move alone changes bind duty %.5f -> %.5f (x%.2f); in-episode %.4f -> %.4f  (the raised pole passes more HF into fb, so MORE binds is the expected sign)" % (
            tag, u["duty"], v["duty"], v["duty"] / max(u["duty"], 1e-12), u["d_in"], v["d_in"]))

    pr("\n  5c. RUNG BELL -- 18-22 Hz BAR ENVELOPE TRIGGERED ON CAPPED-FRAME ONSETS (first capped frame after >= 0.2 s uncapped, engaged -0.5..+1.0 s).")
    pr("      Pre = median envelope -0.5..0 s; post = max 0..+0.5 s; CI resamples events.  V289 predicts a SMALLER post/pre (the ring's overshoot is what the notch removes).")
    EV = {}
    for tag in ALL:
        g, e = G[tag], G[tag]["e4"]
        env = CEN.envelope(g["bar"], 20.0, FS)
        envr = CEN.envelope(g["wire"], 20.0, FS) / V.CPD
        cap = e["cap"]; n = len(cap)
        on = np.flatnonzero(cap[20:] & ~np.array([cap[i - 20:i].any() for i in range(20, n)])) + 20
        rows = []
        for i in on:
            ti = e["tgrid"][i + 1]
            j = int(np.searchsorted(g["t"], ti))
            if j - 50 < 0 or j + 101 >= len(g["t"]) or not g["eng"][j - 50:j + 101].all():
                continue
            rl = 1
            while i + rl < n and cap[i + rl]:
                rl += 1
            pre = np.median(env[j - 50:j]); post = env[j:j + 50].max()
            prer = np.median(envr[j - 50:j]); postr = envr[j:j + 50].max()
            # decay after the post-peak: log-slope of the envelope from its 0..0.5 s peak to +1.0 s
            kpk = j + int(np.argmax(env[j:j + 50]))
            seg = np.log(np.maximum(env[kpk:kpk + 50], 1e-9))
            sl = stats.linregress(np.arange(len(seg)) / FS, seg).slope if len(seg) >= 10 else np.nan
            rows.append(dict(j=j, rl=rl, pre=pre, post=post, prer=prer, postr=postr, dslope=sl, hot=bool(g["hot"][j]),
                             strata={st: bool(SM[tag][st][j]) for st in STRATA_ORDER}, curve=env[j - 50:j + 101]))
        EV[tag] = rows
    pr("  %-9s %-28s %6s | %8s %8s %8s %-16s | %8s %8s %-16s | %-22s | %s" % ("arm", "stratum", "n ev", "pre p50", "post p50", "ratio", "95% CI", "rate pre", "rate post", "ratio CI", "post-peak decay /s [CI]", "P(episode <= 0.5 s)"))

    def ev_row(name, rows, st, gref):
        sel = [r for r in rows if st is None or r["strata"][st]]
        if len(sel) < 5:
            pr("  %-9s %-28s %6d   (thin)" % (name, st or "ALL", len(sel))); return
        pre = np.array([r["pre"] for r in sel]); post = np.array([r["post"] for r in sel])
        prer = np.array([r["prer"] for r in sel]); postr = np.array([r["postr"] for r in sel])
        ds = np.array([r["dslope"] for r in sel]); ds = ds[np.isfinite(ds)]
        ratio = lambda idx: np.median(post[idx]) / max(np.median(pre[idx]), 1e-9)
        ratior = lambda idx: np.median(postr[idx]) / max(np.median(prer[idx]), 1e-9)
        bs = [ratio(rng.integers(0, len(sel), len(sel))) for _ in range(2000)]
        bsr = [ratior(rng.integers(0, len(sel), len(sel))) for _ in range(2000)]
        pe = float(np.mean([gref[r["tag"]]["hot"][r["j"]:r["j"] + 50].any() for r in sel])) if isinstance(gref, dict) else float(np.mean([gref["hot"][r["j"]:r["j"] + 50].any() for r in sel]))
        pr("  %-9s %-28s %6d | %8.1f %8.1f %8.3f [%.3f, %.3f]   | %8.2f %8.2f [%.3f, %.3f]   | %6.2f [%6.2f, %6.2f]  | %.2f" % (
            name, st or "ALL", len(sel), np.median(pre), np.median(post), ratio(np.arange(len(sel))), *ci(bs),
            np.median(prer), np.median(postr), *ci(bsr), np.median(ds), *boot_stat(ds, np.median, rng, 2000), pe))

    for st in (None, "FB-dominated (any)", "REF-dominated (none)", "REF & hands-off |bar|<400", "REF & creep 1-3 m/s", "REF & 3-8 m/s", "REF & 8-15 m/s"):
        for name, tags in ARMS:
            rows = []
            for t in tags:
                for r in EV[t]:
                    rr = dict(r); rr["tag"] = t; rows.append(rr)
            ev_row(name, rows, st, G)
        pr("")
    pr("  5c-ii. Median envelope CURVE around capped onsets, REF-dominated onsets only (raw bar 18-22 envelope at lags, s):")
    lags = (-0.4, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0)
    pr("  %-9s %5s | %s" % ("arm", "n", " ".join("%6.2f" % l for l in lags)))
    for name, tags in ARMS:
        sel = [r for t in tags for r in EV[t] if r["strata"]["REF-dominated (none)"]]
        if len(sel) < 5:
            continue
        cur = np.median(np.array([r["curve"] for r in sel]), 0)
        pr("  %-9s %5d | %s" % (name, len(sel), " ".join("%6.1f" % cur[int(round(50 + l * FS))] for l in lags)))

    # ------------------------------------------------------------------ 6. spectra + revert signatures
    pr("\n" + "=" * 168)
    pr("6. WHOLE-ROUTE SPECTRA -- pooled engaged PSDs (Hann, 50 %% overlap, 0.195 Hz bins), band powers, line scans, REVERT SIGNATURES")
    pr("=" * 168)
    SPEC = {}
    for tag in ALL:
        g = G[tag]
        straight = g["eng"] & (np.abs(g["ang"]) < 5.0)
        for stname, smask in (("ALL", np.ones(len(g["eng"]), bool)), ("REF", SM[tag]["REF-dominated (none)"]), ("FB", SM[tag]["FB-dominated (any)"]),
                              ("STRAIGHT", straight), ("STRAIGHT>=8", straight & (g["vego"] >= 8))):
            msk = g["eng"] & smask
            runs = C20.runs(msk, 512)
            fb_, Pb = C88.seg_psds([g["bar"][a:b] for a, b in runs], FS, 512)
            _, Pw = C88.seg_psds([g["wire"][a:b] / V.CPD for a, b in runs], FS, 512)
            Truns = []
            for a, b in runs:
                s_ = (g["T_t"] >= g["t"][a]) & (g["T_t"] <= g["t"][b - 1])
                Truns.append(g["T"][s_])
            fT, PT = C88.seg_psds(Truns, FST, 256)
            SPEC[(tag, stname)] = dict(f=fb_, bar=Pb, wire=Pw, fT=fT, T=PT, secs=sum(b - a for a, b in runs) / FS)
    bands = ((6, 10), (13, 17), (18, 22), (22, 24), (24, 40), (15, 40))
    pr("\n  6a. Band POWER (bar raw^2 ; wheel rate (deg/s)^2 ; T raw^2), with segment-bootstrap CIs on 18-22 ; ratios of V289 routes to r39 and to r5e_v288:")
    pr("  %-11s %-5s %-9s %6s %6s | %s | %-24s" % ("stratum", "sig", "route", "n seg", "secs", " ".join("%10s" % ("%d-%d" % b) for b in bands), "18-22 CI"))
    BP = {}
    for stname in ("ALL", "REF", "FB", "STRAIGHT", "STRAIGHT>=8"):
        for sig in ("bar", "wire", "T"):
            for tag in ALL:
                S = SPEC[(tag, stname)]
                f = S["fT"] if sig == "T" else S["f"]; P = S[sig]
                if len(P) < 5:
                    pr("  %-11s %-5s %-9s %6d   (thin)" % (stname, sig, tag, len(P))); continue
                bp = [C88.bandpow(f, P, lo, min(hi, f[-1])).mean() for lo, hi in bands]
                c18 = boot_stat(C88.bandpow(f, P, 18, 22), np.mean, rng, 1000)
                BP[(stname, sig, tag)] = bp
                pr("  %-11s %-5s %-9s %6d %6.0f | %s | [%8.3g,%8.3g]" % (stname, sig, tag, len(P), S["secs"], " ".join("%10.3g" % v for v in bp), *c18))
            for t in V289_ROUTES:
                if all((stname, sig, x) in BP for x in (t, "r39", V288_TAG)):
                    pr("  %-11s %-5s %-9s ratio to r39      : %s" % (stname, sig, t, " ".join("%10.2f" % (BP[(stname, sig, t)][i] / BP[(stname, sig, "r39")][i]) for i in range(len(bands)))))
                    pr("  %-11s %-5s %-9s ratio to r5e_v288 : %s" % (stname, sig, t, " ".join("%10.2f" % (BP[(stname, sig, t)][i] / BP[(stname, sig, V288_TAG)][i]) for i in range(len(bands)))))

    pr("\n  6b. LINE SCAN 12-49 Hz (bar and wheel rate; excess = log-PSD minus a +-2 Hz running-median baseline; peaks by excess with a segment-bootstrap CI).")
    pr("      REVERT RULE (pre-stated for V288, applied to V289): NEW = on a V289 route with excess >= 3 dB and CI low > 1 dB, and no V282/V288 route within +-0.5 Hz")
    pr("      with excess >= 2 dB.  The 13-17 and 22-24 Hz windows are V289's pre-registered revert bands; 18-22 is the grind line itself (excluded from NEW).")
    LINES = {}
    for stname in ("ALL", "REF", "STRAIGHT"):
        for sig in ("bar", "wire"):
            for tag in ALL:
                S = SPEC[(tag, stname)]; f = S["f"]; P = S[sig]
                if len(P) < 5:
                    continue
                Pm = P.mean(0); ex = C88.excess_db(f, Pm)
                sel = (f >= 12.0) & (f <= 49.0)
                pk, props = signal.find_peaks(np.where(sel, ex, -99), prominence=1.0)
                order = pk[np.argsort(-ex[pk])][:8]
                rows = []
                for i in order:
                    bs = []
                    for _ in range(300):
                        j = rng.integers(0, len(P), len(P))
                        bs.append(C88.excess_db(f, P[j].mean(0))[i])
                    rows.append((f[i], ex[i], *ci(bs)))
                LINES[(stname, sig, tag)] = rows
                pr("  %-8s %-5s %-9s : %s" % (stname, sig, tag, " ; ".join("%.2f Hz %+.1f dB [%+.1f,%+.1f]" % r for r in rows)))
            for t in V289_ROUTES:
                if (stname, sig, t) not in LINES:
                    continue
                new = []
                for f0, ex0, lo_, hi_ in LINES[(stname, sig, t)]:
                    if 18.0 <= f0 <= 22.0:
                        continue
                    if ex0 >= 3.0 and lo_ > 1.0:
                        seen = any(abs(f0 - r[0]) <= 0.5 and r[1] >= 2.0 for x in V282_ROUTES + (V288_TAG,) for r in LINES.get((stname, sig, x), []))
                        if not seen:
                            new.append("%.2f Hz %+.1f dB [%+.1f,%+.1f]" % (f0, ex0, lo_, hi_))
                pr("  %-8s %-5s NEW lines on %s not on any V282/V288 route: %s" % (stname, sig, t, ", ".join(new) if new else "none"))
    pr("\n  6c. The revert bands, read directly: max excess (dB) in 13-17 Hz and 22-24 Hz, and the 18-22 Hz line's own excess, bar / wheel rate / T; ALL, REF and STRAIGHT strata:")
    pr("  %-8s %-9s | %-44s | %-44s | %-44s" % ("str", "route", "bar: 13-17 max / 18-22 line / 22-24 max", "wheel rate: same", "T: same (50 Hz tap)"))
    for stname in ("ALL", "REF", "STRAIGHT"):
        for tag in ALL:
            parts = []
            for sig in ("bar", "wire", "T"):
                S = SPEC[(tag, stname)]; f = S["fT"] if sig == "T" else S["f"]; P = S[sig]
                if len(P) < 5:
                    parts.append("(thin)"); continue
                ex = C88.excess_db(f, P.mean(0))
                out = []
                for lo, hi in ((13, 17), (18, 22), (22, 24)):
                    sel = (f >= lo) & (f <= hi)
                    i = np.flatnonzero(sel)[np.argmax(ex[sel])]
                    bs = [C88.excess_db(f, P[rng.integers(0, len(P), len(P))].mean(0))[i] for _ in range(200)]
                    out.append("%5.2f %+4.1f[%+.1f,%+.1f]" % (f[i], ex[i], *ci(bs)))
                parts.append(" ".join(out))
            pr("  %-8s %-9s | %s" % (stname, tag, " | ".join("%-44s" % p for p in parts)))
    pr("\n  6d. A SUSTAINED ~16 Hz LINE?  Window census re-run with the peak search moved to 12-18 Hz (same prominence >= 8) and bar 14-17 Hz band >= 40 raw;")
    pr("      fraction of engaged windows present, and of those the fraction where the 15-26 Hz census f0 is ALSO < 18 Hz (i.e. the line itself has moved down):")
    pr("  %-9s %7s %7s %7s %-24s %-22s" % ("route", "n win", "pres16", "%", "f16 mean+-sd of present", "amp 14-17 p50/p90/max"))
    for tag in ALL:
        g = G[tag]; rows = []
        for aa, bb in C20.runs(g["eng"], C88.W):
            for s in range(aa, bb - C88.W + 1, C88.STEP):
                e_ = s + C88.W
                f16, p16 = CEN.line_of(g["bar"][s:e_], FS, 12.0, 18.0)
                rows.append((f16, p16, CEN.band(g["bar"][s:e_], 14, 17)))
        rows = np.array(rows, float)
        p16 = (rows[:, 1] >= 8) & (rows[:, 2] >= 40)
        pr("  %-9s %7d %7d %7.1f %5.2f +- %4.2f               %4.0f/%4.0f/%4.0f" % (tag, len(rows), p16.sum(), 100 * p16.mean(),
                                                                                rows[p16, 0].mean() if p16.any() else np.nan, rows[p16, 0].std() if p16.any() else np.nan,
                                                                                *np.percentile(rows[:, 2], (50, 90)), rows[:, 2].max()))

    # ------------------------------------------------------------------ 7. THE PREDICTION TEST
    pr("\n" + "=" * 168)
    pr("7. THE V289 PREDICTION TEST -- do the 18-22 Hz rings decay faster and stop being sustained?")
    pr("=" * 168)
    pr("  7a. Per-episode envelope slopes (GI.growth_fit: log-envelope slope on the 10->90 %% rise and the 90->10 %% fall about the peak; tau = 1/|slope|;")
    pr("      zeta_dn = |gd| / (2 pi f0)).  CI = bootstrap over episodes.  PREDICTION: |gd| x1.7 on V289 (zeta 0.019 -> 0.024 census fit; 0.016 -> 0.038 step ring).")
    pr("  %-9s %-11s %5s | %-26s %-26s | %-22s %-22s | %-22s | %-14s" % ("arm", "class", "n", "gu /s p50 [CI]", "gd /s p50 [CI]", "tau_up ms p50 [CI]", "tau_dn ms p50 [CI]", "zeta_dn p50 [CI]", "frac gd<=-1/s"))
    GD = {}
    for name, tags in ARMS:
        for cls in ("all", "BURST", "SUSTAINED", "RIDE-ALONG"):
            sel = [e for e in episodes if e["tag"] in tags and (cls == "all" or e["cls"] == cls) and np.isfinite(e["gu"]) and np.isfinite(e["gd"])]
            if len(sel) < 3:
                pr("  %-9s %-11s %5d   (thin)" % (name, cls, len(sel))); continue
            gu = np.array([e["gu"] for e in sel]); gd = np.array([e["gd"] for e in sel]); f0 = np.array([e["f0"] for e in sel])
            z = np.abs(gd) / (2 * np.pi * f0)
            if cls == "all":
                GD[name] = dict(gu=gu, gd=gd, z=z, dur=np.array([e["dur"] for e in sel]), cls=np.array([e["cls"] for e in sel]))
            cgu = boot_stat(gu, np.median, rng, 2000); cgd = boot_stat(gd, np.median, rng, 2000); cz = boot_stat(z, np.median, rng, 2000)
            tu = 1000 / max(np.median(gu), 1e-9); td = 1000 / max(-np.median(gd), 1e-9)
            pr("  %-9s %-11s %5d | %6.2f [%6.2f,%6.2f]      %6.2f [%6.2f,%6.2f]      | %6.0f [%6.0f,%6.0f]   %6.0f [%6.0f,%6.0f]   | %6.4f [%6.4f,%6.4f] | %.2f" % (
                name, cls, len(sel), np.median(gu), *cgu, np.median(gd), *cgd,
                tu, 1000 / max(cgu[1], 1e-9), 1000 / max(cgu[0], 1e-9), td, 1000 / max(-cgd[0], 1e-9), 1000 / max(-cgd[1], 1e-9),
                np.median(z), *cz, np.mean(gd <= -1.0)))
    pr("\n  7b. Decay-rate RATIOS (median |gd| V289 / reference; bootstrap both arms by episode; per V289 route and pooled).  Prediction ~1.7 (>1 = faster decay):")
    for a_ in ("r62_v289", "r63_v289", "V289pool"):
        for b_ in ("r39", V288_TAG, "V282pool"):
            if a_ not in GD or b_ not in GD:
                continue
            ga, gb = np.abs(GD[a_]["gd"]), np.abs(GD[b_]["gd"])
            bs = [np.median(ga[rng.integers(0, len(ga), len(ga))]) / max(np.median(gb[rng.integers(0, len(gb), len(gb))]), 1e-9) for _ in range(4000)]
            za, zb = GD[a_]["z"], GD[b_]["z"]
            bz = [np.median(za[rng.integers(0, len(za), len(za))]) / max(np.median(zb[rng.integers(0, len(zb), len(zb))]), 1e-9) for _ in range(4000)]
            mw = stats.mannwhitneyu(ga, gb, alternative="greater").pvalue
            pr("  |gd| %-9s / %-9s = %.2f [%.2f, %.2f]   zeta ratio %.2f [%.2f, %.2f]   MW p(V289 decays faster) = %.3g   n %d vs %d" % (
                a_, b_, np.median(ga) / np.median(gb), *ci(bs), np.median(za) / np.median(zb), *ci(bz), mw, len(ga), len(gb)))
    pr("\n  7c. SUSTAINED vs DECAYING, by arm: census class shares; the share of episodes whose whole-body envelope trend is flat-or-rising (|slope| < 0.5/s or > 0);")
    pr("      duration p50/p90/max and the share of episodes >= 2 s and >= 4 s.  Prediction: SUSTAINED share and long-episode share FALL on V289.")
    pr("  %-9s %5s | %-24s %-24s | %-18s | %-22s | %-14s %-14s" % ("arm", "n", "SUSTAINED % [CI]", "BURST % [CI]", "body trend >= -0.5/s %", "dur p50 / p90 / max s", ">= 2 s % [CI]", ">= 4 s % [CI]"))
    for name, tags in ARMS:
        es = [e for e in episodes if e["tag"] in tags]
        if len(es) < 3:
            pr("  %-9s %5d   (thin)" % (name, len(es))); continue
        cl = np.array([e["cls"] for e in es]); d = np.array([e["dur"] for e in es])
        trend = []
        for e in es:
            g = G[e["tag"]]
            env = CEN.envelope(g["bar"][max(0, e["a"] - 100):min(len(g["tr"]), e["b"] + 100)], e["f0"], FS)
            body = env[min(100, e["a"]):min(100, e["a"]) + (e["b"] - e["a"])]
            if len(body) >= 20:
                trend.append(stats.linregress(np.arange(len(body)) / FS, np.log(np.maximum(body, 1e-9))).slope)
        trend = np.array(trend)
        fs_ = (cl == "SUSTAINED").astype(float); fb_ = (cl == "BURST").astype(float)
        f2 = (d >= 2).astype(float); f4 = (d >= 4).astype(float)
        pr("  %-9s %5d | %4.0f%% [%3.0f,%3.0f]           %4.0f%% [%3.0f,%3.0f]           | %6.1f              | %5.2f / %5.2f / %5.2f   | %4.0f%% [%3.0f,%3.0f]  %4.0f%% [%3.0f,%3.0f]" % (
            name, len(es), 100 * fs_.mean(), *(100 * np.array(boot_stat(fs_, np.mean, rng, 2000))), 100 * fb_.mean(), *(100 * np.array(boot_stat(fb_, np.mean, rng, 2000))),
            100 * np.mean(trend >= -0.5) if len(trend) else np.nan, np.median(d), np.percentile(d, 90), d.max(),
            100 * f2.mean(), *(100 * np.array(boot_stat(f2, np.mean, rng, 2000))), 100 * f4.mean(), *(100 * np.array(boot_stat(f4, np.mean, rng, 2000)))))
    pr("\n  7d. FREE DECAY (wire_0xe4_burst_damping.py sec. 3): envelope log-slope over command-QUIET stretches (>= 0.3 s, zero capped frames AND mean |dcmd| <= the route's")
    pr("      engaged baseline median) starting at or after an episode's envelope peak.  z = |slope| / (2 pi 20).  This is the closest the wire gets to a free ring.")
    pr("  %-9s %8s %12s %12s %12s %12s %12s %10s" % ("arm", "n quiet", "slope p50 /s", "p25", "p75", "tau p50 ms", "z p50 @20Hz", "frac decay"))
    FD = {}
    for name, tags in ARMS:
        sl = []
        for tag in tags:
            g, e = G[tag], G[tag]["e4"]
            capf = np.interp(g["t"], e["tgrid"][1:], (np.abs(e["d"]) >= CAP).astype(float))
            dabs = np.interp(g["t"], e["tgrid"][1:], np.abs(e["d"]))
            base_med = np.median(np.abs(e["d"])[e["base"] & ~e["hot"]])
            for ep in [x for x in episodes if x["tag"] == tag]:
                s0, s1 = max(0, ep["a"] - 100), min(len(g["tr"]), ep["b"] + 100)
                env = CEN.envelope(g["bar"][s0:s1], ep["f0"], FS); t = g["tr"][s0:s1]
                k = int(np.argmax(env))
                quiet = (capf[s0:s1] < 0.5) & (dabs[s0:s1] <= base_med); quiet[:k] = False
                for a, b in C20.runs(quiet, 30):
                    seg = np.log(np.maximum(env[a:b], 1e-9))
                    if seg.max() - seg.min() < 0.1:
                        continue
                    s = stats.linregress(t[a:b], seg).slope
                    if np.isfinite(s):
                        sl.append(s)
        sl = np.array(sl); FD[name] = sl
        if len(sl) >= 5:
            pr("  %-9s %8d %12.2f %12.2f %12.2f %12.0f %12.4f %10.3f" % (name, len(sl), np.median(sl), np.percentile(sl, 25), np.percentile(sl, 75),
                                                                        1000 / max(abs(np.median(sl)), 1e-9), abs(np.median(sl)) / (2 * np.pi * 20), np.mean(sl < 0)))
        else:
            pr("  %-9s %8d   (thin)" % (name, len(sl)))
    for a_ in ("V289pool", "r62_v289", "r63_v289"):
        for b_ in ("V282pool", "r39", V288_TAG):
            if len(FD.get(a_, [])) >= 5 and len(FD.get(b_, [])) >= 5:
                ga, gb = FD[a_], FD[b_]
                bs = [np.median(ga[rng.integers(0, len(ga), len(ga))]) / np.median(gb[rng.integers(0, len(gb), len(gb))]) for _ in range(4000)]
                pr("  free-decay slope ratio %s / %s = %.2f [%.2f, %.2f]  (>1 = V289 decays faster; MW p(more negative) = %.3g)" % (
                    a_, b_, np.median(ga) / np.median(gb), *ci(bs), stats.mannwhitneyu(ga, gb, alternative="less").pvalue))

    # ------------------------------------------------------------------ 8. H2 re-test
    pr("\n" + "=" * 168)
    pr("8. H2 RE-TEST on these routes -- 0xE4 change cadence, gap histogram, slew-cap hits, and the ECHO test (the line's share in the command vs in the 0x18F rate)")
    pr("=" * 168)
    pr("  %-9s %8s %7s %9s | %-34s | %8s %8s %8s | %-22s | %-22s | %-16s" % (
        "route", "P_e4 ms", "n eng", "chg/frame", "gaps 1 / 2 / 3 / 4 / >=5", "|d|>=122", "|d|=123", "epi cap", "cmd L/S ; epi/base", "rate L/S ; epi/base", "f cmd / f bar"))
    for tag in ALL:
        g, e = G[tag], G[tag]["e4"]
        d = e["d"]; ok = e["base"]
        dd = d[ok]
        chg = np.mean(dd != 0); ch = np.flatnonzero(dd != 0); gaps = np.diff(ch)
        h = [np.mean(gaps == k) for k in (1, 2, 3, 4)] + [np.mean(gaps >= 5)]
        hotf = e["hot"]
        # spectra on own clocks
        fs_e = 1.0 / e["P"]
        fc, Pc, nc = WIRE.welch_pool([e["grid"][a:b] for a, b in C20.runs(e["egrid"], 512)], fs_e, 512)
        fr_, Pr, nr = WIRE.welch_pool([g["wire"][a:b] for a, b in C20.runs(g["eng"], 512)], FS, 512)
        ls = lambda f, P: P[(f >= 18) & (f < 22)].mean() / (0.5 * (P[(f >= 12) & (f < 18)].mean() + P[(f >= 26) & (f < 40)].mean()))
        ce = [WIRE.bandamp(e["grid"][a:b], fs_e, LO, HI) for a, b in C20.runs(e["egrid"] & np.r_[False, hotf], 128)]
        cb = [WIRE.bandamp(e["grid"][a:b], fs_e, LO, HI) for a, b in C20.runs(e["egrid"] & ~np.r_[False, hotf], 128)]
        re_ = [WIRE.bandamp(g["wire"][a:b], FS, LO, HI) for a, b in C20.runs(g["hot"], 128)]
        rb = [WIRE.bandamp(g["wire"][a:b], FS, LO, HI) for a, b in C20.runs(g["eng"] & ~g["hot"], 128)]
        fcm = [WIRE.fine_line(e["grid"][a:b], fs_e, 15, 26)[0] for a, b in C20.runs(e["egrid"] & np.r_[False, hotf], 256)]
        fbr = [WIRE.fine_line(g["bar"][a:b], FS, 15, 26)[0] for a, b in C20.runs(g["hot"], 256)]
        pr("  %-9s %8.4f %7d %9.3f | %s | %8.4f %8.4f %8.4f | %5.2f ; %5.2f            | %5.2f ; %5.2f            | %6.2f / %6.2f" % (
            tag, 1000 * e["P"], ok.sum(), chg, " / ".join("%.3f" % v for v in h), np.mean(np.abs(dd) >= CAP), np.mean(np.abs(dd) == 123),
            np.mean(np.abs(d[ok & hotf]) >= CAP) if (ok & hotf).any() else np.nan,
            ls(fc, Pc), np.median(ce) / max(np.median(cb), 1e-9) if ce and cb else np.nan,
            ls(fr_, Pr), np.median(re_) / max(np.median(rb), 1e-9) if re_ and rb else np.nan,
            np.median(fcm) if fcm else np.nan, np.median(fbr) if fbr else np.nan))
    pr("  L/S = line-to-shoulder ratio of the pooled engaged Welch PSD (mean 18-22 / mean of 12-18 & 26-40); epi/base = median 18-22 Hz band amplitude in episodes / outside.")
    pr("  A 4-frame staircase would put >= 0.8 of gaps at 4-5 frames and change on ~20 %% of frames.  The echo test: if the command's line tracks the bar's line in frequency")
    pr("  and is conditioned on the car grinding (epi/base >> 1, same as the rate's), it is the wheel ring echoed back through openpilot's angle path, not a source.")
    pr("\n  8b. cmd <-> wheel-rate coherence and cross-phase at the bar line, episode frames only (nperseg 256; cmd interpolated to the 0x18F clock; caveat: 0xE4 has no")
    pr("      measured receive latency, so the absolute phase is NOT a lead/lag statement -- the coherence is the echo's strength):")
    pr("  %-9s %8s %10s %10s %8s" % ("route", "coh@f0", "phase deg", "gain c/dps", "n"))
    for tag in ALL:
        g = G[tag]
        f0 = np.median([e["f0"] for e in episodes if e["tag"] == tag]) if any(e["tag"] == tag for e in episodes) else 20.0
        sa, sb = [], []
        for a, b in C20.runs(g["hot"], 256):
            sa.append(g["cmd"][a:b]); sb.append(g["wire"][a:b] / V.CPD)
        f, coh, ph, gain, n = WIRE.csd_pool(sa, sb, FS, 256)
        if n:
            pr("  %-9s %8.2f %10.1f %10.3g %8d" % (tag, WIRE.at(f, coh, f0), WIRE.circ_at(f, ph, f0), WIRE.at(f, gain, f0), n))

    # ------------------------------------------------------------------ 9. inside the grinding windows
    pr("\n" + "=" * 168)
    pr("9. WHAT ELSE IS ON THE WIRE INSIDE A GRINDING WINDOW -- driver torque, speed, angle, command; and b4.5 = sign(S - y) vs the 0x18F wheel rate at the line")
    pr("=" * 168)
    pr("  9a. Episode-body medians (all frames inside episodes) vs the engaged baseline, per arm:")
    pr("  %-9s %-9s %7s | %7s %7s %7s %7s %7s %7s %7s %7s" % ("arm", "frames", "n", "|bar|", "hands>700", "vEgo", "|ang|", "|rate|", "|cmd|", "idx", "|T|"))
    for name, tags in ARMS:
        for lab in ("episode", "baseline"):
            cols_ = {k: [] for k in ("bar", "vego", "ang", "rate", "cmd", "idx", "T100")}
            for t in tags:
                g = G[t]; m = g["eng"] & (g["hot"] if lab == "episode" else ~g["hot"])
                for k in cols_:
                    cols_[k].append(g[k][m])
            cc = {k: np.concatenate(v) for k, v in cols_.items()}
            if len(cc["bar"]) < 100:
                continue
            pr("  %-9s %-9s %7d | %7.0f %7.3f %7.1f %7.0f %7.1f %7.0f %7.0f %7.0f" % (
                name, lab, len(cc["bar"]), np.median(np.abs(cc["bar"])), np.mean(np.abs(cc["bar"]) > 700), np.median(cc["vego"]), np.median(np.abs(cc["ang"])),
                np.median(cc["rate"]), np.median(np.abs(cc["cmd"])), np.median(cc["idx"]), np.median(np.abs(cc["T100"]))))
    pr("\n  9b. 0x14A byte-4 duties (engaged; inside episodes; at episode onsets +-0.25 s).  V289: b5 = sign(S-y) (1 when negative), b7 = |S-y| >= |y| (predicted 0.10-0.11 engaged,")
    pr("      0.12-0.37 in grinding windows).  V282/V288 rows carry their OWN bit semantics (b5 = r24 comparator / sign(y_sp)); only V289 rows are the notch.")
    pr("  %-9s | %-30s | %-30s | %-30s" % ("route", "engaged: b7 b6 b5 b4", "in episodes: b7 b6 b5 b4", "onset +-0.25 s: b7 b6 b5 b4"))
    for tag in ALL:
        g = G[tag]; m = g["eng"]; h = g["eng"] & g["hot"]
        on = np.zeros(len(m), bool)
        for e in episodes:
            if e["tag"] == tag:
                on[max(0, e["a"] - 25):e["a"] + 25] = True
        on &= m
        fmt = lambda s: "  ".join("%.3f" % g["bit%d" % n][s].mean() for n in (7, 6, 5, 4)) if s.sum() else "(none)"
        pr("  %-9s | %-30s | %-30s | %-30s" % (tag, fmt(m), fmt(h), fmt(on)))
    pr("\n  9c. THE LOOP'S PHASE AT 20 Hz, MEASURED: cross-spectrum of n_sign = 1 - 2*b5 (= sign(S - y), the notched-out component of the loop output S) against the 0x18F")
    pr("      wheel rate (raw sign; the PID's operand is x = -rate), on the 0x14A dejittered clock (rate interpolated onto it), episode frames only, nperseg 256.")
    pr("      Phase = angle of n relative to rate (deg, positive = n LEADS rate).  Prediction [BELIEF, from the byte-exact phase budget]: S vs x = -rate at 20.3 Hz on V289 =")
    pr("      fb pole 25 Hz (-38.7 deg) + two two-sample sums (-7.4) + one tick (-7.3) + D lead (+61.6) = ~+8 deg, i.e. S vs +rate ~ -172 deg; and (S - y) ~ S at the notch centre.")
    pr("      Also given: the 0x14A-vs-0x18F on-bus arrival offset (median t14 - nearest t18) -- an UNKNOWN sampling offset of that order is the caveat on every absolute phase.")
    pr("  %-9s %8s %8s %8s %10s %10s %10s %10s | %10s %10s | %8s %8s" % ("route", "f0 Hz", "n frm", "coh", "ph n/rate", "ph CI lo", "ph CI hi", "ph n/-rate", "arr ms", "= deg@f0", "b4 coh", "b4 ph"))
    for tag in ALL:
        g, b = G[tag], B4[tag]
        # rate on the 0x14A clock
        rate14 = np.interp(b["t"], g["t"], g["wire"]) / V.CPD
        hot14 = np.interp(b["t"], g["t"], g["hot"].astype(float)) > 0.5
        have14 = np.interp(b["t"], g["t"], g["have18"].astype(float)) > 0.5
        nsig = 1.0 - 2.0 * b["bit5"]; b4s = 1.0 - 2.0 * b["bit4"]
        eps_t = [e for e in episodes if e["tag"] == tag]
        f0 = np.median([e["f0"] for e in eps_t]) if eps_t else 20.0
        runs = C20.runs(hot14 & have14 & b["eng"], 256)
        sa = [nsig[a_:b_] for a_, b_ in runs]; sb = [rate14[a_:b_] for a_, b_ in runs]; s4 = [b4s[a_:b_] for a_, b_ in runs]
        f, coh, ph, gain, n = WIRE.csd_pool(sa, sb, FS, 256)
        if not n:
            pr("  %-9s   (no episode runs)" % tag); continue
        # bootstrap the phase over runs
        phs = []
        for _ in range(500):
            j = rng.integers(0, len(sa), len(sa))
            fj, cj, pj, gj, nj = WIRE.csd_pool([sa[i] for i in j], [sb[i] for i in j], FS, 256)
            phs.append(WIRE.circ_at(fj, pj, f0))
        phs = np.array(phs); ph0 = WIRE.circ_at(f, ph, f0)
        dphi = (phs - ph0 + 180) % 360 - 180
        f4, c4, p4, _, _ = WIRE.csd_pool(s4, sb, FS, 256)
        # arrival offset 0x14A vs 0x18F
        D18 = dict(np.load(os.path.join(C20.CACHE, tag + ".npz")))
        t18 = D18["t18"]; j = np.clip(np.searchsorted(t18, b["traw"]), 1, len(t18) - 1)
        near = np.where(np.abs(t18[j] - b["traw"]) < np.abs(t18[j - 1] - b["traw"]), t18[j], t18[j - 1])
        arr = np.median(b["traw"] - near) * 1000
        pr("  %-9s %8.2f %8d %8.2f %10.1f %10.1f %10.1f %10.1f | %10.2f %10.1f | %8.2f %8.1f" % (
            tag, f0, n, WIRE.at(f, coh, f0), ph0, ph0 + np.percentile(dphi, 2.5), ph0 + np.percentile(dphi, 97.5), (ph0 + 180 + 180) % 360 - 180,
            arr, arr * 1e-3 * 360 * f0, WIRE.at(f4, c4, f0), WIRE.circ_at(f4, p4, f0)))
    pr("  (b4 = sign(r24), V282's positive-control rung, kept on every build: its coherence with the rate at the line says how much a 1-bit sign channel can show.")
    pr("   On V282/V288 rows b5 is NOT sign(S-y) -- those rows are printed only as a contrast; read the loop phase from the V289 rows alone.)")
    pr("\n  9d. Same cross-spectrum, WHOLE engaged route (not just episodes) and the two REF/FB strata, V289 routes only -- is the notched-out component coherent with the")
    pr("      wheel rate at 20 Hz when the car is NOT grinding (the loop always acts on the mode; the census only sees it when it is loud)?")
    pr("  %-9s %-10s %8s %8s %10s | %8s %8s" % ("route", "stratum", "n frm", "coh@f0", "ph n/rate", "coh@7Hz", "coh@10Hz"))
    for tag in V289_ROUTES:
        g, b = G[tag], B4[tag]
        rate14 = np.interp(b["t"], g["t"], g["wire"]) / V.CPD
        have14 = np.interp(b["t"], g["t"], g["have18"].astype(float)) > 0.5
        nsig = 1.0 - 2.0 * b["bit5"]
        for stname, smask in (("ALL", g["eng"]), ("REF", SM[tag]["REF-dominated (none)"]), ("FB", SM[tag]["FB-dominated (any)"]), ("episodes", g["eng"] & g["hot"])):
            m14 = (np.interp(b["t"], g["t"], smask.astype(float)) > 0.5) & have14 & b["eng"]
            runs = C20.runs(m14, 256)
            f, coh, ph, gain, n = WIRE.csd_pool([nsig[a_:b_] for a_, b_ in runs], [rate14[a_:b_] for a_, b_ in runs], FS, 256)
            if n:
                pr("  %-9s %-10s %8d %8.2f %10.1f | %8.2f %8.2f" % (tag, stname, n, WIRE.at(f, coh, 20.04), WIRE.circ_at(f, ph, 20.04), WIRE.at(f, coh, 7.0), WIRE.at(f, coh, 10.0)))

    with open(os.path.join(SCR, "grind1_census_v289_r62_r63.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote", os.path.join(SCR, "grind1_census_v289_r62_r63.txt"))


if __name__ == "__main__":
    main()
