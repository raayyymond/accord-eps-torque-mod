# -*- coding: utf-8 -*-
"""studies/grind/grind1_census_v282.py -- episode census of GRIND #1 (18-22 Hz, the LKAS rate loop's
crossover resonance) on V282 (r39, r3a, r3c), against r35 (V281 rev 3) and r36/r37/r38 (V283 = V282 +
Ki 50).  Subagent census, 2026-09-06.  Analysis only: builds nothing, sends nothing.

Operator's question (2026-09-06): "The only remaining big issue with V282 is the rare grinding
(grind #1). Seems to generally open on large turn transients, but I'm not sure."

Method, built entirely on existing instruments (nothing re-extracted; every cache and function below
already exists on disk):
  * caches: analysis-2020accord/_scratch/cache/v280/{r39,r3a,r3c,r35,r36,r37,r38}.npz (+ _b4.npz),
    loaded via creep20_loop_id.load() -- "eng" = LATERAL engaged (0x18F STEER_CONTROL_ACTIVE AND
    0xE4 STEER_REQUEST src 129), gap frames (r3a's ~60 s segment-10 hole) already excluded because
    `have18` gates `eng`.  "bar" = driver torque raw x 1.024, "wire"/CPD = wheel rate deg/s, "T100" =
    the 427 delivered-torque tap on the frame clock, "idx" recomputed per-image below.
  * V282's calibration is IDENTICAL to V281 rev 3 (V282-READ-r39-2026-09-04.md Sec: "V282 and V281 rev 3
    differ in NO calibration cell" -- only the read-only cave decode changed).  Cells for r39/r3a/r3c are
    therefore read from the V282 image directly (byte-identical arithmetic to V281r3); V283 cells for
    r36-r38; V281r3 cells for r35.  demand_live/read_cells/simulate/eval_window/envelope/growth_fit/
    line_of/band all reused verbatim from grind_incident_r35.py (module GI) -- the r35 incident's own
    instrument, not a re-derivation.
  * windowed line-present census: 2 s windows, step 0.5 s, engaged, "present" = most prominent 15-26 Hz
    peak has prominence >= 8 AND bar 18-22 raw amplitude >= 40 (v283_grind_census.py's threshold,
    unchanged, so all builds are read with the same yardstick).
  * EPISODE = a contiguous run (>= 0.5 s) of frames whose nearest census window is "present", inside an
    engaged run.  Class:
      BURST      exponential growth (log-envelope slope >= +1.0 /s) then collapse (<= -1.0 /s), the r35
                 incident's own signature (measured there: +1.42 / -3.9 /s).
      RIDE-ALONG bar 6-10 Hz (the strong-turn 7 Hz companion) concurrent amplitude >= 1.2x the 18-22 Hz
                 amplitude AND the two bands' 0.25 s envelopes correlate >= 0.5 -- the r39 bookmark
                 class (20 Hz riding under a 7 Hz ring), not independently growing.
      SUSTAINED  everything else (a presence stretch with neither a clean burst shape nor a dominant,
                 co-modulated 7 Hz partner).
    This is a DESIGN CHOICE (BELIEF on the boundary, EVIDENCE on the measured growth/amplitude/corr
    numbers that feed it) -- flagged in the report.
  * TRANSIENT, at an episode onset t0: |d(angle)/dt| > 30 deg/s, OR d(idx)/dt > 40 /s, OR |rate| > 30
    deg/s, evaluated on 0.1 s steps anywhere in [t0-1.5, t0+1.5] (the operator's "opens on large turn
    transients", operationalised). STEADY CREEP at onset: v in [1,3) m/s, hands off (|bar|<400), and
    |rate| < 10 deg/s at t0 itself.
  * ENRICHMENT = P(transient | episode onset) / P(transient | baseline engaged frames), where the
    baseline draws one instant per second of engaged time (so it is not dominated by the 100 Hz frame
    rate) and asks the same three-part transient predicate at each draw. Episode-level bootstrap
    (resample EPISODES, not windows) gives the CI on the numerator; the baseline (n in the thousands)
    is treated as fixed.

Run: python grind1_census_v282.py      (writes _scratch/grind1_census_v282.txt beside it)
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
import grind_incident_r35 as GI               # noqa: E402  read_cells, demand_live, simulate, eval_window,
                                                #             envelope, growth_fit, line_of, band

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FST = 100.0, 50.0
CACHE = C20.CACHE
W, STEP = 200, 50                              # 2 s windows, 0.5 s step -- the kit standard
V282_ROUTES = ("r39", "r3a", "r3c")
V283_ROUTES = ("r36", "r37", "r38")
ALL = V282_ROUTES + ("r35",) + V283_ROUTES
GRP = {"r39": "V282 LAF2.11", "r3a": "V282 LAF4.00", "r3c": "V282 LAF3.60",
       "r35": "V281r3 LAF2.11 SR12.5", "r36": "V283", "r37": "V283", "r38": "V283"}
IMG = {"V282": LG.FW + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
       "V283": LG.FW + "_v283_V283-V282BASE-KI50.KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
       "V281r3": LG.FW + "_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"}
CELL_OF = {"r39": "V282", "r3a": "V282", "r3c": "V282", "r35": "V281r3", "r36": "V283", "r37": "V283", "r38": "V283"}
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def growth_fit(t, env):
    gu, _, gd, _ = GI.growth_fit(t, env)
    return gu, gd


def envelope(x, f0, fs, bw=2.0):
    return GI.envelope(x, f0, fs, bw)


def line_of(x, fs, lo=15.0, hi=26.0, nfft=4096):
    f0, prom, _, _ = GI.line_of(x, fs, lo, hi, nfft)
    return f0, prom


def band(x, lo, hi, fs=FS):
    return GI.band(x, lo, hi, fs)


def load_route(tag, cells):
    g = C20.load(tag)
    g["tr"] = g["t"] - g["t"][0]
    c = cells[CELL_OF[tag]]
    g["idx"], _ = GI.demand_live(np.round(g["cmd"]), g["bar"], c)
    B = np.load(os.path.join(CACHE, tag + "_b4.npz"))
    k14, P14, tn14, _ = C20.dejitter(B["t14b"], 0.01, 100)
    b4 = B["b4"].astype(int)
    for bit in (4, 5, 6, 7):
        g["bit%d" % bit] = np.round(np.interp(g["t"], tn14, ((b4 >> bit) & 1).astype(float)))
    g["rate"] = np.abs(g["wire"]) / V.CPD
    return g


def onset_transient(g, i0, half=150):
    """does the 3-part transient predicate hold anywhere within +-1.5 s (150 frames) of frame i0?"""
    a, b = max(0, i0 - half), min(len(g["tr"]), i0 + half + 1)
    ang = g["ang"][a:b]; idx = g["idx"][a:b]; rate = g["rate"][a:b]
    dang = np.abs(np.gradient(ang, 1.0 / FS))      # deg/s, central diff over the whole 3 s window
    didx = np.abs(np.gradient(idx, 1.0 / FS))
    # smooth the raw per-sample gradients over 1 s so this reads a TREND, not frame noise
    k = int(FS)
    dang_s = np.convolve(dang, np.ones(k) / k, mode="same")
    didx_s = np.convolve(didx, np.ones(k) / k, mode="same")
    return bool((dang_s > 30).any() or (didx_s > 40).any() or (rate > 30).any())


def steady_creep_at(g, i0):
    v = g["vego"][i0]; hoff = abs(g["bar"][i0]) < 400; r = g["rate"][i0]
    return bool(1.0 <= v < 3.0 and hoff and r < 10.0)


def main():
    cells = {k: GI.read_cells(p) for k, p in IMG.items()}
    G = {tag: load_route(tag, cells) for tag in ALL}
    for tag in ALL:
        print("loaded %s: %.1f s, %.1f s engaged" % (tag, G[tag]["tr"][-1], G[tag]["eng"].sum() / FS), flush=True)

    # ================================================================================================ 1. windowed census
    pr("=" * 168)
    pr("GRIND #1 (18-22 Hz) EPISODE CENSUS -- V282 (r39/r3a/r3c) vs V281r3 (r35) and V283 (r36/r37/r38)")
    pr("=" * 168)
    rows = []
    for tag in ALL:
        g = G[tag]
        msk = g["eng"]
        for aa, bb in C20.runs(msk, W):
            for s in range(aa, bb - W + 1, STEP):
                e = s + W
                f0w, promw = line_of(g["bar"][s:e], FS)
                fq, pq = line_of(g["bar"][s:e], FS, 5, 12)
                rows.append(dict(
                    tag=tag, t=g["tr"][s], f0=f0w, prom=promw, f610=fq, p610=pq,
                    amp=band(g["bar"][s:e], 18, 22), amp610=band(g["bar"][s:e], 6, 10),
                    ramp=band(g["wire"][s:e], 18, 22) / V.CPD,
                    rate=float(np.mean(g["rate"][s:e])),
                    v=float(g["vego"][s:e].mean()), ang=float(np.median(np.abs(g["ang"][s:e]))),
                    T=float(np.median(np.abs(g["T100"][s:e]))), idx=float(np.median(g["idx"][s:e])),
                    tq=float(np.median(np.abs(g["bar"][s:e]))),
                    creep=bool(1.0 <= g["vego"][s:e].mean() < 3.0),
                    hoff=bool(np.median(np.abs(g["bar"][s:e])) < 400)))
    R = {k: np.array([r[k] for r in rows]) for k in rows[0]}
    pres = (R["prom"] >= 8) & (R["amp"] >= 40)

    pr("\n1a. Presence census (2 s windows, step 0.5 s, engaged lateral; present = 15-26 Hz peak prominence >= 8 AND bar 18-22 >= 40 raw)")
    pr("  %-5s %-22s %6s %6s %6s | %-22s | %-20s" % ("route", "build/tune", "n", "pres", "%", "f mean sd p10/p90", "amp p50/p90/max raw"))
    for tag in ALL:
        sel = R["tag"] == tag; ps = sel & pres
        pr("  %-5s %-22s %6d %6d %6.0f | %.2f %.2f %.2f/%.2f | %4.0f/%4.0f/%4.0f" % (
            tag, GRP[tag], sel.sum(), ps.sum(), 100 * pres[sel].mean(),
            R["f0"][ps].mean() if ps.any() else np.nan, R["f0"][ps].std() if ps.any() else np.nan,
            *(np.percentile(R["f0"][ps], (10, 90)) if ps.any() else (np.nan, np.nan)),
            *np.percentile(R["amp"][sel], (50, 90)), R["amp"][sel].max()))

    pr("\n1b. Operator's own stratum -- engaged, hands-off (|bar| < 400), creep 1-3 m/s:")
    pr("  %-5s %-22s %7s %7s %7s %9s %9s %9s" % ("route", "build/tune", "n win", "pres", "%", "amp p50", "amp p90", "amp max"))
    for tag in ALL:
        sel = (R["tag"] == tag) & R["creep"] & R["hoff"]
        if sel.sum() < 5:
            pr("  %-5s %-22s %7d   (too thin)" % (tag, GRP[tag], sel.sum())); continue
        pr("  %-5s %-22s %7d %7d %7.0f %9.0f %9.0f %9.0f" % (
            tag, GRP[tag], sel.sum(), (sel & pres).sum(), 100 * pres[sel].mean(),
            np.median(R["amp"][sel]), np.percentile(R["amp"][sel], 90), R["amp"][sel].max()))

    # ================================================================================================ episode extraction
    pr("\n" + "=" * 168)
    pr("2. EPISODES (contiguous >= 0.5 s line-present stretches, engaged) -- detection, classification, per-episode covariates")
    pr("=" * 168)
    episodes = []
    for tag in ALL:
        g = G[tag]
        sel = np.flatnonzero(R["tag"] == tag)
        wt, wp = R["t"][sel], pres[sel]
        j = np.clip(np.searchsorted(wt, g["tr"] - 1.0), 0, len(wt) - 1)
        near = np.abs(wt[j] + 1.0 - g["tr"]) < 1.5
        hot = g["eng"] & near & wp[j]
        for a, b in C20.runs(hot, int(0.5 * FS)):
            f0, prom = line_of(g["bar"][a:b], FS)
            if not np.isfinite(f0):
                continue
            env = envelope(g["bar"][max(0, a - 100):min(len(g["tr"]), b + 100)], f0, FS)
            env7 = envelope(g["bar"][max(0, a - 100):min(len(g["tr"]), b + 100)], 7.5, FS, bw=2.5)
            tloc = g["tr"][max(0, a - 100):min(len(g["tr"]), b + 100)]
            gu, gd = growth_fit(tloc, env)
            amp = band(g["bar"][a:b], 18, 22); amp6 = band(g["bar"][a:b], 6, 10)
            # 0.25 s envelope correlation between the two bands over the episode window
            n25 = max(4, int(0.25 * FS))
            e20 = env[100:100 + (b - a)] if b - a <= len(env) - 100 else env[:b - a]
            e7 = env7[100:100 + (b - a)] if b - a <= len(env7) - 100 else env7[:b - a]
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
            hands = float(np.median(np.abs(g["bar"][a:b])))
            trans = onset_transient(g, a)
            creepy = steady_creep_at(g, a)
            episodes.append(dict(
                tag=tag, a=a, b=b, t0=g["tr"][a], t1=g["tr"][b - 1], dur=(b - a) / FS, f0=f0, cls=cls,
                env=float(np.nanmax(env)), amp=amp, amp6=amp6, corr7=corr7, gu=gu, gd=gd,
                v=float(g["vego"][a:b].mean()), ang0=float(g["ang"][a]),
                dang1s=float(g["ang"][a] - g["ang"][max(0, a - int(FS))]),
                rate=float(g["rate"][a:b].mean()), rate0=float(g["rate"][a]),
                idx0=float(g["idx"][a]), didx1s=float(g["idx"][a] - g["idx"][max(0, a - int(FS))]),
                hands=hands, T=float(np.median(np.abs(g["T100"][a:b]))),
                trans=trans, creep_onset=creepy))
    pr("  total episodes: %d  (%s)" % (len(episodes), ", ".join("%s=%d" % (t, sum(1 for e in episodes if e['tag'] == t)) for t in ALL)))
    pr("\n  %-5s %-9s %6s %6s %6s %10s %8s %8s %8s %6s %6s %6s %6s %7s %6s %6s" % (
        "route", "class", "t0 s", "dur", "f0", "env pk", "18-22", "6-10", "corr7", "v", "|ang|", "rate", "idx", "|tq|", "trans", "creep"))
    for e in episodes:
        pr("  %-5s %-9s %6.1f %6.2f %6.1f %10.0f %8.0f %8.0f %8.2f %6.1f %6.0f %6.1f %6.0f %7.0f %6s %6s" % (
            e["tag"], e["cls"], e["t0"], e["dur"], e["f0"], e["env"], e["amp"], e["amp6"],
            e["corr7"] if np.isfinite(e["corr7"]) else -9, e["v"], abs(e["ang0"]), e["rate0"], e["idx0"], e["hands"],
            "Y" if e["trans"] else "n", "Y" if e["creep_onset"] else "n"))

    pr("\n  Per-route class split:")
    pr("  %-5s %-22s %6s %8s %10s %10s" % ("route", "build/tune", "n ep", "BURST", "SUSTAINED", "RIDE-ALONG"))
    for tag in ALL:
        es = [e for e in episodes if e["tag"] == tag]
        pr("  %-5s %-22s %6d %8d %10d %10d" % (tag, GRP[tag], len(es),
            sum(1 for e in es if e["cls"] == "BURST"), sum(1 for e in es if e["cls"] == "SUSTAINED"),
            sum(1 for e in es if e["cls"] == "RIDE-ALONG")))
    pr("\n  Pooled V282 (r39+r3a+r3c): %d BURST, %d SUSTAINED, %d RIDE-ALONG (n=%d)" % (
        sum(1 for e in episodes if e["tag"] in V282_ROUTES and e["cls"] == "BURST"),
        sum(1 for e in episodes if e["tag"] in V282_ROUTES and e["cls"] == "SUSTAINED"),
        sum(1 for e in episodes if e["tag"] in V282_ROUTES and e["cls"] == "RIDE-ALONG"),
        sum(1 for e in episodes if e["tag"] in V282_ROUTES)))

    # ================================================================================================ 3. transient hypothesis
    pr("\n" + "=" * 168)
    pr("3. TRANSIENT HYPOTHESIS -- does grind #1 open on large turn transients?")
    pr("   transient @ onset = any of: |d(angle)/dt|>30 deg/s, d(idx)/dt>40/s, |rate|>30 deg/s within +-1.5 s of onset (1 s smoothed).")
    pr("   steady creep @ onset = v in [1,3), hands-off (|bar|<400), |rate|<10 deg/s AT t0.")
    pr("=" * 168)
    v282_eps = [e for e in episodes if e["tag"] in V282_ROUTES]
    n_ep = len(v282_eps)
    n_trans = sum(1 for e in v282_eps if e["trans"])
    n_creep = sum(1 for e in v282_eps if e["creep_onset"])
    energy = np.array([e["env"] for e in v282_eps])
    e_trans_frac = energy[[e["trans"] for e in v282_eps]].sum() / energy.sum() if energy.sum() > 0 else np.nan
    pr("  V282 (r39+r3a+r3c) episodes: n=%d, at a TRANSIENT onset: %d (%.0f%%), in STEADY CREEP at onset: %d (%.0f%%)" % (
        n_ep, n_trans, 100 * n_trans / max(n_ep, 1), n_creep, 100 * n_creep / max(n_ep, 1)))
    pr("  envelope-weighted energy fraction starting at a transient: %.0f%%" % (100 * e_trans_frac))

    # baseline: one draw per second of engaged time across the V282 routes
    base_trans = []
    for tag in V282_ROUTES:
        g = G[tag]
        idxs = np.flatnonzero(g["eng"])
        for i in idxs[::int(FS)]:
            base_trans.append(onset_transient(g, i))
    base_trans = np.array(base_trans)
    p_base = base_trans.mean()
    p_ep = n_trans / max(n_ep, 1)
    enrich = p_ep / p_base if p_base > 0 else np.nan
    pr("\n  baseline P(transient) over engaged 1 Hz-sampled frames (n=%d): %.3f" % (len(base_trans), p_base))
    pr("  episode-onset P(transient) (n=%d): %.3f  =>  ENRICHMENT RATIO %.2fx" % (n_ep, p_ep, enrich))
    # bootstrap over episodes
    rng = np.random.default_rng(0)
    trans_flags = np.array([e["trans"] for e in v282_eps])
    boots = []
    if n_ep >= 3:
        for _ in range(4000):
            samp = rng.integers(0, n_ep, n_ep)
            boots.append(trans_flags[samp].mean() / p_base if p_base > 0 else np.nan)
        lo, hi = np.nanpercentile(boots, (2.5, 97.5))
        pr("  bootstrap (resample EPISODES, n=4000): enrichment 95%% CI [%.2f, %.2f]x" % (lo, hi))
    else:
        pr("  too few episodes to bootstrap (n=%d)" % n_ep)

    pr("\n  Operating-point distribution of V282 episode ONSETS vs ALL V282 engaged frames:")
    pr("  %-22s %8s %8s %8s %8s %8s" % ("stratum", "n", "v p50", "|ang| p50", "rate p50", "idx p50"))
    all_v = np.concatenate([G[t]["vego"][G[t]["eng"]] for t in V282_ROUTES])
    all_ang = np.concatenate([np.abs(G[t]["ang"][G[t]["eng"]]) for t in V282_ROUTES])
    all_rate = np.concatenate([G[t]["rate"][G[t]["eng"]] for t in V282_ROUTES])
    all_idx = np.concatenate([G[t]["idx"][G[t]["eng"]] for t in V282_ROUTES])
    pr("  %-22s %8d %8.1f %8.0f %8.1f %8.0f" % ("all engaged frames", len(all_v), np.median(all_v), np.median(all_ang), np.median(all_rate), np.median(all_idx)))
    if n_ep:
        ev = np.array([e["v"] for e in v282_eps]); eang = np.abs(np.array([e["ang0"] for e in v282_eps]))
        erate = np.array([e["rate0"] for e in v282_eps]); eidx = np.array([e["idx0"] for e in v282_eps])
        pr("  %-22s %8d %8.1f %8.0f %8.1f %8.0f" % ("episode onsets (all)", n_ep, np.median(ev), np.median(eang), np.median(erate), np.median(eidx)))
        for cls in ("BURST", "SUSTAINED", "RIDE-ALONG"):
            m = np.array([e["cls"] == cls for e in v282_eps])
            if m.any():
                pr("  %-22s %8d %8.1f %8.0f %8.1f %8.0f" % (
                    "  onsets: " + cls, m.sum(), np.median(ev[m]), np.median(eang[m]), np.median(erate[m]), np.median(eidx[m])))

    # ================================================================================================ 4. loudest ranking
    pr("\n" + "=" * 168)
    pr("4. LOUDEST EPISODES -- top 3 per route, ranked by envelope peak; per-second trace for the loudest")
    pr("=" * 168)
    for tag in ALL:
        es = sorted([e for e in episodes if e["tag"] == tag], key=lambda e: -e["env"])[:3]
        if not es:
            pr("  %-5s : no episodes" % tag); continue
        pr("\n  %-5s (%s):" % (tag, GRP[tag]))
        for e in es:
            pr("    t %.1f-%.1f s (%.2f s), class %s, f0 %.1f Hz, env pk %.0f raw, 18-22 %.0f, 6-10 %.0f, corr7 %.2f, grow %+.2f/%+.2f /s" % (
                e["t0"], e["t1"], e["dur"], e["cls"], e["f0"], e["env"], e["amp"], e["amp6"],
                e["corr7"] if np.isfinite(e["corr7"]) else float("nan"), e["gu"], e["gd"]))
            pr("      onset: v %.1f m/s, |ang| %.0f deg (d/dt 1s %+.0f), rate %.1f deg/s, idx %.0f (d/dt 1s %+.0f), |tq| %.0f raw, |T| %.0f -- transient=%s creep=%s" % (
                e["v"], abs(e["ang0"]), e["dang1s"], e["rate0"], e["idx0"], e["didx1s"], e["hands"], e["T"],
                e["trans"], e["creep_onset"]))
        # per-second trace of the single loudest episode on this route
        e = es[0]; g = G[tag]; a0 = max(0, e["a"] - int(2 * FS)); b0 = min(len(g["tr"]), e["b"] + int(2 * FS))
        pr("    per-second trace of the loudest episode (t / v / |ang| / cmd / idx / |tq| / T / bar18-22 / bar6-10 / rate18-22 / rate):")
        for s0 in range(a0, b0, int(FS)):
            s1 = min(s0 + int(FS), b0)
            if s1 - s0 < 20:
                continue
            ev = eval_row = None
            pr("      %6.1f  v %4.1f  ang %5.0f  cmd %6.0f  idx %4.0f  |tq| %4.0f  T %5.0f  b18-22 %4.0f  b6-10 %4.0f  rate18-22 %5.2f  rate %5.1f" % (
                g["tr"][s0], g["vego"][s0:s1].mean(), g["ang"][s0], g["cmd"][s0], g["idx"][s0:s1].mean(),
                np.median(np.abs(g["bar"][s0:s1])), np.median(np.abs(g["T100"][s0:s1])),
                band(g["bar"][s0:s1], 18, 22), band(g["bar"][s0:s1], 6, 10),
                band(g["wire"][s0:s1], 18, 22) / V.CPD, g["rate"][s0:s1].mean()))

    # rail check via the chain mirror on the top V282 episode overall
    pr("\n  RAIL CHECK (chain mirror, live fade, ZOH command, V282 cells) on the loudest V282 episode overall:")
    v282_eps_sorted = sorted(v282_eps, key=lambda e: -e["env"])
    for e in v282_eps_sorted[:3]:
        g = G[e["tag"]]; c = cells[CELL_OF[e["tag"]]]
        ev = GI.eval_window(g, e["a"], e["b"], c)
        pr("    %-5s t %.1f-%.1f s: prail %.3f drail %.3f srail %.3f tcap %.3f fbclamp %.3f fade p50/min %.2f/%.2f  (Tmeas/Tsim %.0f/%.0f, corr %.2f)" % (
            e["tag"], e["t0"], e["t1"], ev["prail"], ev["drail"], ev["srail"], ev["tcap"], ev["fbclp"],
            ev["fade"], ev["fademin"], ev["Tmeas"], ev["Tsim"], ev["corr"]))

    # r39 t 883.2 check
    pr("\n  r39 t ~883.2 s check (V282-READ-r39 Sec 6, un-bookmarked louder episode):")
    r39_near = [e for e in episodes if e["tag"] == "r39" and abs(e["t0"] - 883.2) < 5.0 or (e["tag"] == "r39" and e["t0"] <= 883.2 <= e["t1"])]
    if r39_near:
        for e in r39_near:
            pr("    FOUND: t %.1f-%.1f s, class %s, env pk %.0f raw, 18-22 %.0f, transient=%s" % (
                e["t0"], e["t1"], e["cls"], e["env"], e["amp"], e["trans"]))
    else:
        pr("    NOT in the >=0.5 s episode list at this presence threshold (prominence>=8, amp>=40) -- see the full r39 episode list above for the nearest stretch.")

    # ================================================================================================ 5. Honda oscillation-reversal detector test
    pr("\n" + "=" * 168)
    pr("5. HONDA OSCILLATION-REVERSAL DETECTOR (FUN_000428d4) TEST -- requested by team-lead 2026-09-06")
    pr("   Detector: 39 Hz-filtered d(rotor angle)/dt, >10 Hz alternate-crossing reversals of +-40%% FS, 15-20 reversals")
    pr("   (375-500 ms at 20 Hz) ramps a MULTIPLICATIVE governor cut to x0.600 (slew-limited, 0xC694A: 0/15/20/25 -> 1.0/1.0/0.6/0.6).")
    pr("   The 427 tap T is UPSTREAM of the cut -> if it fires, delivered MOTION per unit T should fall ~0.6x, timed")
    pr("   0.375-0.5 s after onset, and episode DURATION should pile up at 0.4-0.6 s (the detector's own reset window).")
    pr("   Test: |rate|18-22 / |T|18-22-style envelope ratio and |bar|/|T| quasi-static ratio, first 0.3 s of the episode")
    pr("   vs last 0.3 s vs 0.5 s AFTER the episode ends.  All episodes >= 0.4 s (this route set's presence threshold).")
    pr("=" * 168)

    def win_ratio(rel, env_rate, env_T, bar_ctx, T_ctx, lo, hi):
        m = (rel >= lo) & (rel < hi)
        if m.sum() < 5:
            return np.nan, np.nan
        rr = np.median(env_rate[m]) / max(np.median(env_T[m]), 1e-6)
        br = np.median(np.abs(bar_ctx[m])) / max(np.median(np.abs(T_ctx[m])), 1e-6)
        return rr, br

    det_rows = []
    for e in [e for e in episodes if e["dur"] >= 0.4]:
        g = G[e["tag"]]; a, b = e["a"], e["b"]; f0 = e["f0"]
        ctx0, ctx1 = max(0, a - 100), min(len(g["tr"]), b + 150)
        bar_ctx, wire_ctx, T_ctx = g["bar"][ctx0:ctx1], g["wire"][ctx0:ctx1], g["T100"][ctx0:ctx1]
        env_rate = envelope(wire_ctx, f0, FS) / V.CPD
        env_T = envelope(T_ctx, f0, FS)
        rel = g["tr"][ctx0:ctx1] - g["tr"][a]
        rr0, br0 = win_ratio(rel, env_rate, env_T, bar_ctx, T_ctx, 0.0, 0.3)
        rr1, br1 = win_ratio(rel, env_rate, env_T, bar_ctx, T_ctx, max(0.0, e["dur"] - 0.3), e["dur"])
        rr2, br2 = win_ratio(rel, env_rate, env_T, bar_ctx, T_ctx, e["dur"], e["dur"] + 0.5)
        drop_rr = rr2 / rr0 if rr0 and np.isfinite(rr0) and rr0 > 0 else np.nan
        drop_br = br2 / br0 if br0 and np.isfinite(br0) and br0 > 0 else np.nan
        det_rows.append(dict(tag=e["tag"], t0=e["t0"], dur=e["dur"], rr0=rr0, rr1=rr1, rr2=rr2, drop_rr=drop_rr,
                              br0=br0, br1=br1, br2=br2, drop_br=drop_br))
    pr("  %-5s %6s %6s | %8s %8s %8s %8s | %8s %8s %8s %8s | %s" % (
        "route", "t0", "dur", "rr@0-.3", "rr@end", "rr@+.5", "drop", "br@0-.3", "br@end", "br@+.5", "drop", "flag"))
    hits = []
    for r in det_rows:
        flag = ""
        if np.isfinite(r["drop_rr"]) and r["drop_rr"] <= 0.75 and 0.30 <= r["dur"] <= 0.65:
            flag = "<-- CANDIDATE (rate/T drop, duration in reset window)"
            hits.append(r)
        elif np.isfinite(r["drop_br"]) and r["drop_br"] <= 0.75 and 0.30 <= r["dur"] <= 0.65:
            flag = "<-- CANDIDATE (bar/T drop, duration in reset window)"
            hits.append(r)
        pr("  %-5s %6.1f %6.2f | %8.3f %8.3f %8.3f %8.2f | %8.3f %8.3f %8.3f %8.2f | %s" % (
            r["tag"], r["t0"], r["dur"], r["rr0"], r["rr1"], r["rr2"], r["drop_rr"],
            r["br0"], r["br1"], r["br2"], r["drop_br"], flag))
    pr("\n  %d/%d episodes >= 0.4 s show a >=25%% drop in rate/T or bar/T timed with a 0.3-0.65 s duration -- %s" % (
        len(hits), len(det_rows),
        "EVIDENCE the detector may be acting on some episodes -- verify each by hand before concluding" if hits else
        "NO episode matches the detector's signature (EVIDENCE, this dataset and this ratio test)"))

    pr("\n  Duration histogram (all episodes, all routes) -- a pile-up at 0.4-0.6 s would be the detector's own signature:")
    durs = np.array([e["dur"] for e in episodes])
    for lo, hi in ((0.5, 0.6), (0.6, 0.8), (0.8, 1.0), (1.0, 1.5), (1.5, 2.5), (2.5, 100)):
        m = (durs >= lo) & (durs < hi)
        pr("    %.1f-%.1f s: %3d  (%.0f%%)" % (lo, hi, m.sum(), 100 * m.mean() if len(durs) else 0))
    if len(durs):
        pr("    -> %s" % ("a pile-up sits at 0.4-0.6 s (BELIEF: consistent with, not proof of, the detector's reset window)"
                           if (durs < 0.6).mean() > 0.35 else "no pile-up at 0.4-0.6 s (EVIDENCE against a dominant detector signature in this duration distribution)"))

    pr("\n  DIRECT TEST on the r35 23:48:21 burst (rise 1016.3-1017.2, decay to ~1017.65, per GRIND-INCIDENT-r35-2026-09-03.md):")
    if "r35" in G:
        g = G["r35"]
        a35 = int(np.searchsorted(g["tr"], 1016.3)); b35 = int(np.searchsorted(g["tr"], 1017.65))
        ctx0, ctx1 = max(0, a35 - 100), min(len(g["tr"]), b35 + 150)
        bar_ctx, wire_ctx, T_ctx = g["bar"][ctx0:ctx1], g["wire"][ctx0:ctx1], g["T100"][ctx0:ctx1]
        f0, _ = line_of(g["bar"][a35:b35], FS)
        f0 = f0 if np.isfinite(f0) else 20.1
        env_rate = envelope(wire_ctx, f0, FS) / V.CPD
        env_T = envelope(T_ctx, f0, FS)
        rel = g["tr"][ctx0:ctx1] - g["tr"][a35]
        dur35 = g["tr"][b35] - g["tr"][a35]
        rr0, br0 = win_ratio(rel, env_rate, env_T, bar_ctx, T_ctx, 0.0, 0.3)
        rr1, br1 = win_ratio(rel, env_rate, env_T, bar_ctx, T_ctx, max(0.0, dur35 - 0.3), dur35)
        rr2, br2 = win_ratio(rel, env_rate, env_T, bar_ctx, T_ctx, dur35, dur35 + 0.5)
        pr("    f0 %.2f Hz, dur %.2f s: rate/T ratio @0-0.3s %.3f, @episode-end %.3f, @+0.5s %.3f (drop vs onset %.2fx)" % (
            f0, dur35, rr0, rr1, rr2, rr2 / rr0 if rr0 else float("nan")))
        pr("    bar/T ratio @0-0.3s %.3f, @episode-end %.3f, @+0.5s %.3f (drop vs onset %.2fx)" % (
            br0, br1, br2, br2 / br0 if br0 else float("nan")))
        pr("    the study's own note: collapse -3.91 /s over 0.44 s coincides with |tq| rising 270->1200 (hands tightening) a full")
        pr("    second BEFORE the 2500-raw grab -- this test asks whether the collapse is ALSO a detector cut, not only the hands.")
        verdict = "the delivered-response ratio drops >=25%% timed with the collapse -- CONSISTENT with (not proof of) a detector cut layered under the hands" \
            if (np.isfinite(rr2 / rr0) and rr2 / rr0 <= 0.75) or (np.isfinite(br2 / br0) and br2 / br0 <= 0.75) \
            else "the delivered-response ratio does NOT drop >=25%% -- no detector signature found on this burst (EVIDENCE against, this test)"
        pr("    VERDICT: %s" % verdict)
    else:
        pr("    r35 not loaded in this run.")

    # ================================================================================================ 6. sharper onset predicate (team-lead, 2026-09-06)
    pr("\n" + "=" * 168)
    pr("6. SHARPER ONSET PREDICATE -- top-1%% |d(cmd)| OR top-1%% d(idx) ticks (the V287 D-clamp's own predicate,")
    pr("   GRIND1-LOOP-SHAPE-V287-2026-09-06.md Appendix B3: 'onset = the 0.5 s after a |dsp| in its top 1%% of non-zero")
    pr("   steps').  Symmetric +-0.5 s window here (team-lead's phrasing).  Threshold pooled over V282 engaged frames.")
    pr("=" * 168)
    dcmd_all, didx_all = [], []
    for tag in V282_ROUTES:
        g = G[tag]
        dcmd = np.abs(np.diff(g["cmd"], prepend=g["cmd"][0]))
        didx = np.abs(np.diff(g["idx"], prepend=g["idx"][0]))
        dcmd_all.append(dcmd[g["eng"]]); didx_all.append(didx[g["eng"]])
    dcmd_all = np.concatenate(dcmd_all); didx_all = np.concatenate(didx_all)
    thr_cmd = np.percentile(dcmd_all[dcmd_all > 0], 99)
    thr_idx = np.percentile(didx_all[didx_all > 0], 99)
    pr("  pooled V282 engaged frames: top-1%% |d(cmd)| threshold = %.0f raw/frame (n nonzero=%d), top-1%% d(idx) threshold = %.1f/frame (n nonzero=%d)" % (
        thr_cmd, (dcmd_all > 0).sum(), thr_idx, (didx_all > 0).sum()))

    near_tick = {}
    for tag in V282_ROUTES:
        g = G[tag]
        dcmd = np.abs(np.diff(g["cmd"], prepend=g["cmd"][0]))
        didx = np.abs(np.diff(g["idx"], prepend=g["idx"][0]))
        big = (dcmd >= thr_cmd) | (didx >= thr_idx)
        # "within 0.5 s" -- any big tick in a +-50 frame (0.5 s) window, per route (no cross-route bleed)
        k = 50
        pad = np.r_[np.zeros(k, bool), big, np.zeros(k, bool)]
        csum = np.cumsum(np.r_[0, pad.astype(int)])
        near = (csum[2 * k + 1:] - csum[:-(2 * k + 1)]) > 0   # length == len(big)
        near_tick[tag] = near

    v282_eps = [e for e in episodes if e["tag"] in V282_ROUTES]
    for e in v282_eps:
        e["near_tick"] = bool(near_tick[e["tag"]][e["a"]])

    pr("\n  Per-class fraction of V282 episode ONSETS within +-0.5 s of a top-1%% |d(cmd)| or d(idx) tick:")
    pr("  %-12s %6s %10s %8s" % ("class", "n", "near tick", "%"))
    for cls in ("BURST", "SUSTAINED", "RIDE-ALONG", "ALL"):
        es = v282_eps if cls == "ALL" else [e for e in v282_eps if e["cls"] == cls]
        n = len(es); nt = sum(1 for e in es if e["near_tick"])
        pr("  %-12s %6d %10d %8.0f" % (cls, n, nt, 100 * nt / max(n, 1)))

    # baseline: 1 Hz-sampled engaged frames, pooled V282
    base_near = []
    for tag in V282_ROUTES:
        g = G[tag]; idxs = np.flatnonzero(g["eng"])
        base_near.append(near_tick[tag][idxs[::int(FS)]])
    base_near = np.concatenate(base_near)
    p_base = base_near.mean()
    p_ep = sum(1 for e in v282_eps if e["near_tick"]) / max(len(v282_eps), 1)
    enrich = p_ep / p_base if p_base > 0 else np.nan
    pr("\n  baseline P(near a top-1%% tick), 1 Hz-sampled V282 engaged frames (n=%d): %.3f" % (len(base_near), p_base))
    pr("  episode-onset P(near a top-1%% tick), ALL classes (n=%d): %.3f  =>  ENRICHMENT RATIO %.2fx" % (len(v282_eps), p_ep, enrich))
    rng2 = np.random.default_rng(1)
    flags_all = np.array([e["near_tick"] for e in v282_eps])
    if len(v282_eps) >= 3:
        boots = [flags_all[rng2.integers(0, len(v282_eps), len(v282_eps))].mean() / p_base for _ in range(4000)] if p_base > 0 else []
        if boots:
            lo, hi = np.percentile(boots, (2.5, 97.5))
            pr("  bootstrap (resample EPISODES, n=4000), ALL classes: enrichment 95%% CI [%.2f, %.2f]x" % (lo, hi))
    pr("\n  Per-class enrichment (bootstrap over that class's own episodes; small-n classes will have wide CIs):")
    for cls in ("BURST", "SUSTAINED", "RIDE-ALONG"):
        es = [e for e in v282_eps if e["cls"] == cls]
        if len(es) < 3:
            pr("    %-12s n=%d -- too few to bootstrap" % (cls, len(es))); continue
        flags = np.array([e["near_tick"] for e in es])
        p_c = flags.mean(); enr_c = p_c / p_base if p_base > 0 else np.nan
        boots_c = [flags[rng2.integers(0, len(es), len(es))].mean() / p_base for _ in range(4000)] if p_base > 0 else []
        lo_c, hi_c = (np.percentile(boots_c, (2.5, 97.5)) if boots_c else (np.nan, np.nan))
        pr("    %-12s n=%3d  P(near tick)=%.2f  enrichment %.2fx  95%% CI [%.2f, %.2f]x" % (cls, len(es), p_c, enr_c, lo_c, hi_c))

    with open(os.path.join(SCR, "grind1_census_v282.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote", os.path.join(SCR, "grind1_census_v282.txt"))


if __name__ == "__main__":
    main()
