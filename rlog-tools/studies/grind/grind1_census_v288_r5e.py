# -*- coding: utf-8 -*-
"""studies/grind/grind1_census_v288_r5e.py -- the V282 GRIND #1 census (grind1_census_v282.py), UNCHANGED in
every threshold, run on the first V288 rev 2 route r5e_v288 (75604b0a432fdc89_0000005e--03a9714d78, 2026-09-08)
against V282's r39 / r3a / r3c, plus the endpoints pre-registered for V288
(docs/review/ADVERSARIAL-V288-PREREG-2026-09-07.md, STATE "RISK BEFORE THE DRIVE"):

  (a) D-clamp bind duty (1 kHz mirror, V282 cells; for V288 the mirror carries the cave's own setpoint
      filter, integer-exact from build_v288_tva.sp_filter_tick) and the 18-22 Hz bar envelope triggered on
      CAPPED-FRAME ONSETS (|dcmd| >= 122 raw/frame = openpilot's 122.88 slew cap, wire_0xe4_slewcap.py);
  (b) the same, stratified: FEEDBACK-dominated (hands-on |bar| > 700, |ang| > 60 deg, wheel > 25 deg/s --
      NOT expected to move) vs REFERENCE-dominated (none of those);
  (c) exposure per stratum (engaged s), flagging any V288 stratum under 30 s;
  (d) whole-route pooled engaged PSDs of bar / wheel rate / 427 tap, 3-50 Hz, 6-10 and 18-22 Hz band powers
      and a scan for any NEW line above 22 Hz.

METHOD FIDELITY.  grind1_census_v282.py keeps its pipeline inside main(), so the window census, the episode
extraction/classification and the two enrichment tests are COPIED here verbatim into functions (the only
edits are `ALL`/`V282_ROUTES` becoming arguments).  The script first re-runs them on r39/r3a/r3c and asserts
the counts against the stored _scratch/grind1_census_v282.txt (presence n/present per route, episodes per
route, class split, the two enrichment ratios and CIs, the top-1 % thresholds).  If that assertion fails the
run stops -- nothing about V288 is reported on an unproven yardstick.  Loader: wire_0xe4_20hz.load_route
(= creep20_loop_id.load + demand_live + the raw 0xE4 grid); cells: V288 image (calibration byte-identical
to V282 -- asserted cell by cell below).  Subagent `census288`, 2026-09-08.  Analysis only: builds nothing,
sends nothing.

Run: python grind1_census_v288_r5e.py     (writes _scratch/grind1_census_v288_r5e.txt beside it)
"""
import hashlib
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
import grind1_census_v282 as CEN              # noqa: E402  (module-level helpers + dicts; main() not run)
import wire_0xe4_20hz as WIRE                 # noqa: E402  load_route, episodes_of, fine_line

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FS1K, FST = 100.0, 1000.0, 50.0
W, STEP = CEN.W, CEN.STEP
LO, HI = 18.0, 22.0
CAP = 122
V282_ROUTES = ("r39", "r3a", "r3c")
V288_TAG = "r5e_v288"
ALL = V282_ROUTES + (V288_TAG,)
V288_IMG = (LG.FW + "_v288r2_V288R2-V282BASE-SPFILT.K4.EINIT-KP.FLAT.Y0-CAVE.R24CMP.B6-SPSIGN.B5-"
            "MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
V288_SHA = "94cabdefd39a103ad10ec34b9c64b6ac94d6552b80bfe7cc192a8977cbbdbd8c"
K_SHIFT = 4
CEN.IMG["V288"] = V288_IMG
CEN.CELL_OF[V288_TAG] = "V288"
CEN.GRP[V288_TAG] = "V288r2 (r5e)"
GRP = CEN.GRP
NB = 4000
CACHE_P = os.path.join(SCR, "grind1_census_v288_r5e_cache.pkl")   # stage cache: census tables + whole-route mirror
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def ci(x, q=(2.5, 97.5)):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return tuple(np.percentile(x, q)) if len(x) else (np.nan, np.nan)


def boot_stat(vals, fn, rng, n=NB):
    vals = np.asarray(vals)
    if len(vals) < 3:
        return (np.nan, np.nan)
    return ci([fn(vals[rng.integers(0, len(vals), len(vals))]) for _ in range(n)])


# =====================================================================================================
# 1. the census pipeline, COPIED VERBATIM from grind1_census_v282.main() (ALL -> tags argument)
# =====================================================================================================
def window_census(G, tags):
    rows = []
    for tag in tags:
        g = G[tag]
        msk = g["eng"]
        for aa, bb in C20.runs(msk, W):
            for s in range(aa, bb - W + 1, STEP):
                e = s + W
                f0w, promw = CEN.line_of(g["bar"][s:e], FS)
                fq, pq = CEN.line_of(g["bar"][s:e], FS, 5, 12)
                rows.append(dict(
                    tag=tag, t=g["tr"][s], f0=f0w, prom=promw, f610=fq, p610=pq,
                    amp=CEN.band(g["bar"][s:e], 18, 22), amp610=CEN.band(g["bar"][s:e], 6, 10),
                    ramp=CEN.band(g["wire"][s:e], 18, 22) / V.CPD,
                    rate=float(np.mean(g["rate"][s:e])),
                    v=float(g["vego"][s:e].mean()), ang=float(np.median(np.abs(g["ang"][s:e]))),
                    T=float(np.median(np.abs(g["T100"][s:e]))), idx=float(np.median(g["idx"][s:e])),
                    tq=float(np.median(np.abs(g["bar"][s:e]))),
                    creep=bool(1.0 <= g["vego"][s:e].mean() < 3.0),
                    hoff=bool(np.median(np.abs(g["bar"][s:e])) < 400)))
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
        g["hot"] = hot
        for a, b in C20.runs(hot, int(0.5 * FS)):
            f0, prom = CEN.line_of(g["bar"][a:b], FS)
            if not np.isfinite(f0):
                continue
            env = CEN.envelope(g["bar"][max(0, a - 100):min(len(g["tr"]), b + 100)], f0, FS)
            env7 = CEN.envelope(g["bar"][max(0, a - 100):min(len(g["tr"]), b + 100)], 7.5, FS, bw=2.5)
            tloc = g["tr"][max(0, a - 100):min(len(g["tr"]), b + 100)]
            gu, gd = CEN.growth_fit(tloc, env)
            amp = CEN.band(g["bar"][a:b], 18, 22); amp6 = CEN.band(g["bar"][a:b], 6, 10)
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
            trans = CEN.onset_transient(g, a)
            creepy = CEN.steady_creep_at(g, a)
            episodes.append(dict(
                tag=tag, a=a, b=b, t0=g["tr"][a], t1=g["tr"][b - 1], dur=(b - a) / FS, f0=f0, cls=cls,
                env=float(np.nanmax(env)), amp=amp, amp6=amp6, corr7=corr7, gu=gu, gd=gd,
                v=float(g["vego"][a:b].mean()), ang0=float(g["ang"][a]),
                dang1s=float(g["ang"][a] - g["ang"][max(0, a - int(FS))]),
                rate=float(g["rate"][a:b].mean()), rate0=float(g["rate"][a]),
                idx0=float(g["idx"][a]), didx1s=float(g["idx"][a] - g["idx"][max(0, a - int(FS))]),
                hands=hands, T=float(np.median(np.abs(g["T100"][a:b]))),
                trans=trans, creep_onset=creepy))
    return episodes


def transient_enrichment(G, episodes, tags, seed=0):
    """§3 of the V282 census: loose 3-part transient predicate, baseline 1 Hz-sampled engaged frames."""
    eps = [e for e in episodes if e["tag"] in tags]
    base = []
    for tag in tags:
        g = G[tag]
        idxs = np.flatnonzero(g["eng"])
        for i in idxs[::int(FS)]:
            base.append(CEN.onset_transient(g, i))
    base = np.array(base)
    p_base = base.mean()
    flags = np.array([e["trans"] for e in eps])
    p_ep = flags.mean() if len(eps) else np.nan
    rng = np.random.default_rng(seed)
    boots = [flags[rng.integers(0, len(eps), len(eps))].mean() / p_base for _ in range(NB)] if len(eps) >= 3 and p_base > 0 else []
    return dict(n=len(eps), n_trans=int(flags.sum()), n_creep=sum(1 for e in eps if e["creep_onset"]),
                n_base=len(base), p_base=p_base, p_ep=p_ep, enrich=p_ep / p_base if p_base > 0 else np.nan,
                ci=ci(boots) if boots else (np.nan, np.nan))


def tick_thresholds(G, tags):
    dcmd_all, didx_all = [], []
    for tag in tags:
        g = G[tag]
        dcmd = np.abs(np.diff(g["cmd"], prepend=g["cmd"][0]))
        didx = np.abs(np.diff(g["idx"], prepend=g["idx"][0]))
        dcmd_all.append(dcmd[g["eng"]]); didx_all.append(didx[g["eng"]])
    dcmd_all = np.concatenate(dcmd_all); didx_all = np.concatenate(didx_all)
    return np.percentile(dcmd_all[dcmd_all > 0], 99), np.percentile(didx_all[didx_all > 0], 99)


def tick_enrichment(G, episodes, tags, thr_cmd, thr_idx, seed=1):
    """§6 of the V282 census: top-1 % |dcmd| or didx tick within +-0.5 s of onset."""
    near_tick = {}
    for tag in tags:
        g = G[tag]
        dcmd = np.abs(np.diff(g["cmd"], prepend=g["cmd"][0]))
        didx = np.abs(np.diff(g["idx"], prepend=g["idx"][0]))
        big = (dcmd >= thr_cmd) | (didx >= thr_idx)
        k = 50
        pad = np.r_[np.zeros(k, bool), big, np.zeros(k, bool)]
        csum = np.cumsum(np.r_[0, pad.astype(int)])
        near_tick[tag] = (csum[2 * k + 1:] - csum[:-(2 * k + 1)]) > 0
    eps = [e for e in episodes if e["tag"] in tags]
    for e in eps:
        e["near_tick"] = bool(near_tick[e["tag"]][e["a"]])
    base_near = []
    for tag in tags:
        g = G[tag]; idxs = np.flatnonzero(g["eng"])
        base_near.append(near_tick[tag][idxs[::int(FS)]])
    base_near = np.concatenate(base_near)
    p_base = base_near.mean()
    flags = np.array([e["near_tick"] for e in eps])
    p_ep = flags.mean() if len(eps) else np.nan
    rng2 = np.random.default_rng(seed)
    out = dict(n=len(eps), n_base=len(base_near), p_base=p_base, p_ep=p_ep, enrich=p_ep / p_base if p_base > 0 else np.nan)
    out["ci"] = ci([flags[rng2.integers(0, len(eps), len(eps))].mean() / p_base for _ in range(NB)]) if len(eps) >= 3 and p_base > 0 else (np.nan, np.nan)
    out["cls"] = {}
    for cls in ("BURST", "SUSTAINED", "RIDE-ALONG"):
        es = [e for e in eps if e["cls"] == cls]
        if len(es) < 3:
            out["cls"][cls] = (len(es), np.nan, np.nan, (np.nan, np.nan)); continue
        fl = np.array([e["near_tick"] for e in es])
        out["cls"][cls] = (len(es), fl.mean(), fl.mean() / p_base,
                           ci([fl[rng2.integers(0, len(es), len(es))].mean() / p_base for _ in range(NB)]))
    return out


# =====================================================================================================
# 2. the 1 kHz mirror with an optional V288 setpoint filter (GI.simulate copied; ONE insertion)
# =====================================================================================================
def sp_filter_series(sp_int, k):
    """build_v288_tva.sp_filter_tick, vectorised over a tick series with y := sp on the first tick
    (the engage init).  Integer-exact: Python >> floors like V850 sar."""
    y = int(sp_int[0]); out = np.empty(len(sp_int), np.int64)
    for i in range(len(sp_int)):
        d = int(sp_int[i]) - y
        step = d >> k
        if step == 0 and d != 0:
            step = 1
        y = y + step
        out[i] = y
    return out


def simulate_sp(g, a, b, c, spfilt_k=None, kd=128, lag=(992, 507)):
    """GI.simulate (fade=True, ZOH, no rate filter) with `sp` optionally passed through the V288 cave."""
    seg = slice(max(0, a - 50), min(len(g["t"]), b + 10))
    n1 = (seg.stop - seg.start) * 10
    t1k = g["t"][seg.start] + np.arange(n1) * g["P18"] / 10
    wire = C20.up1k(g["wire"][seg])
    x = -wire
    s = 0.0; fb = np.empty(n1)
    for i in range(n1):
        s_new = np.floor((c["fb_a"] * s + c["fb_b"] * x[i]) / 1024.0)
        fb[i] = s + s_new
        s = s_new
    fb = np.clip(fb, -c["fb_clamp"], c["fb_clamp"])
    cmd = g["cmd"][seg]; bar = g["bar"][seg]
    cmd1k = np.repeat(cmd, 10); bar1k = np.repeat(bar, 10)
    idx, sgn = GI.demand_live(cmd1k, bar1k, c); idx = np.round(idx)
    sp = sgn * GI.lerp(c["map_X"], c["map_Y"], idx)
    kp = GI.lerp(c["kp_X"], c["kp_Y"], idx)
    sp_used = sp
    if spfilt_k is not None:                                   # <-- the ONLY insertion vs GI.simulate
        sp_used = sp_filter_series(np.round(sp).astype(np.int64), spfilt_k).astype(float)
    E = 32 * sp_used - fb
    P = np.clip(np.floor(E * kp / 256), -V.P_CLAMP, V.P_CLAMP)
    dE = np.r_[0.0, np.diff(E)]
    D = np.clip(np.floor(dE * kd / 8), -V.D_CLAMP, V.D_CLAMP)
    eng1k = np.repeat(g["eng"][seg], 10)
    B = GI.lerp(c["fadeB"][0], c["fadeB"][1], np.abs(bar1k) // 32)
    m = ((255.0 * B).astype(np.int64) & 0xFFFF) >> 8

    def post(u):
        S = np.clip(np.floor(m * u / 256), -V.SUM_CLAMP, V.SUM_CLAMP); S[~eng1k] = 0.0
        st = signal.lfilter([lag[1] / 1024.0], [1.0, -lag[0] / 1024.0], S); y = (np.r_[0.0, st[:-1]] + st) / 32.0
        return np.clip(np.floor(-y * c["gain"] / 32768), -V.OUT_CAP, V.OUT_CAP)
    T = post(P + D)
    live = eng1k
    bind = np.abs(dE * kd / 8) > V.D_CLAMP
    return dict(t1k=t1k, T=T, E=E, dE=dE, sp=sp, sp_used=sp_used, seg=seg, live=live, bind=bind,
                prail=float(np.mean(np.abs(E * kp / 256)[live] >= V.P_CLAMP)) if live.any() else np.nan,
                drail=float(np.mean(bind[live])) if live.any() else np.nan)


# =====================================================================================================
# 3. strata
# =====================================================================================================
def strata_masks(g):
    """per-frame strata.  FB-dominated = any of the three prereg conditions; REF-dominated = none."""
    hands = np.abs(g["bar"]) > 700
    hiang = np.abs(g["ang"]) > 60
    fast = g["rate"] > 25
    fb = hands | hiang | fast
    ref = ~fb
    v = g["vego"]
    return {"FB: hands-on |bar|>700": hands, "FB: |ang|>60 deg": hiang, "FB: wheel>25 deg/s": fast,
            "FB-dominated (any)": fb, "REF-dominated (none)": ref,
            "REF & creep 1-3 m/s": ref & (v >= 1) & (v < 3), "REF & 3-8 m/s": ref & (v >= 3) & (v < 8),
            "REF & 8-15 m/s": ref & (v >= 8) & (v < 15), "REF & >=15 m/s": ref & (v >= 15),
            "REF & hands-off |bar|<400": ref & (np.abs(g["bar"]) < 400)}


STRATA_ORDER = ("FB: hands-on |bar|>700", "FB: |ang|>60 deg", "FB: wheel>25 deg/s", "FB-dominated (any)",
                "REF-dominated (none)", "REF & creep 1-3 m/s", "REF & 3-8 m/s", "REF & 8-15 m/s", "REF & >=15 m/s",
                "REF & hands-off |bar|<400")


# =====================================================================================================
# 4. spectra: segment-wise Welch with a segment bootstrap
# =====================================================================================================
def seg_psds(x_runs, fs, nperseg):
    """list of arrays -> (f, matrix of per-segment Hann periodograms, 50 % overlap), Welch = mean."""
    P = []
    win = np.hanning(nperseg); U = (win ** 2).sum() * fs
    for x in x_runs:
        x = np.asarray(x, float)
        if len(x) < nperseg:
            continue
        for s in range(0, len(x) - nperseg + 1, nperseg // 2):
            seg = x[s:s + nperseg]; seg = seg - seg.mean()
            X = np.fft.rfft(seg * win)
            p = (np.abs(X) ** 2) / U; p[1:-1] *= 2
            P.append(p)
    f = np.fft.rfftfreq(nperseg, 1.0 / fs)
    return f, (np.array(P) if P else np.zeros((0, len(f))))


def bandpow(f, P, lo, hi):
    m = (f >= lo) & (f < hi)
    return P[:, m].mean(1) * (hi - lo)          # per-segment band power (units^2)


def excess_db(f, Pm, half_hz=2.0):
    """log-PSD minus a running-median baseline over +-half_hz -- the line-vs-shoulder excess."""
    L = 10 * np.log10(np.maximum(Pm, 1e-30))
    k = int(round(half_hz / (f[1] - f[0])))
    base = np.array([np.median(L[max(0, i - k):i + k + 1]) for i in range(len(L))])
    return L - base


# =====================================================================================================
def main():
    rng = np.random.default_rng(20260908)
    # ------------------------------------------------------------------ image + cells
    sha = hashlib.sha256(open(V288_IMG, "rb").read()).hexdigest()
    assert sha == V288_SHA, "V288 image hash mismatch: %s" % sha
    cells = {k: GI.read_cells(p) for k, p in CEN.IMG.items() if k in ("V282", "V288")}
    c282, c288 = cells["V282"], cells["V288"]
    diffs = []
    for k in c282:
        a_, b_ = c282[k], c288[k]
        same = (np.array_equal(np.asarray(a_[0]), np.asarray(b_[0])) and np.array_equal(np.asarray(a_[1]), np.asarray(b_[1]))) \
            if isinstance(a_, tuple) else np.array_equal(np.asarray(a_), np.asarray(b_))
        if not same:
            diffs.append(k)
    pr("=" * 168)
    pr("GRIND #1 (18-22 Hz) EPISODE CENSUS -- V288 rev 2 first route r5e_v288 vs V282 (r39/r3a/r3c), SAME YARDSTICK")
    pr("=" * 168)
    pr("V288 image sha256 %s (verified)" % sha)
    pr("cells read from the V288 image vs the V282 image (GI.read_cells, %d keys): %s" % (
        len(c282), "IDENTICAL" if not diffs else "DIFFER in %s" % diffs))
    assert not diffs, "V288 calibration is supposed to be byte-identical to V282"

    G = {}
    for tag in ALL:
        G[tag] = WIRE.load_route(tag, cells[CEN.CELL_OF[tag]])
        g = G[tag]
        print("loaded %s: %.1f s, %.1f s engaged" % (tag, g["tr"][-1], g["eng"].sum() / FS), flush=True)

    # ------------------------------------------------------------------ 0. reproduction of the V282 census
    pr("\n0. REPRODUCTION of grind1_census_v282.py on r39/r3a/r3c with the copied pipeline, vs the stored output")
    ref_txt = open(os.path.join(SCR, "grind1_census_v282.txt"), encoding="utf-8").read()
    CACHED = pickle.load(open(CACHE_P, "rb")) if os.path.exists(CACHE_P) else {}
    if "R" in CACHED:
        R, pres, episodes = CACHED["R"], CACHED["pres"], CACHED["episodes"]
        for tag in ALL:
            G[tag]["hot"] = CACHED["hot"][tag]
        pr("  (window census + episodes loaded from %s)" % os.path.basename(CACHE_P))
    else:
        R, pres = window_census(G, ALL)
        episodes = extract_episodes(G, R, pres, ALL)
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
    tr282 = transient_enrichment(G, episodes, V282_ROUTES)
    thr_cmd, thr_idx = tick_thresholds(G, V282_ROUTES)
    tk282 = tick_enrichment(G, episodes, V282_ROUTES, thr_cmd, thr_idx)
    ref_tr = re.search(r"ENRICHMENT RATIO ([\d.]+)x\n.*?CI \[([\d.]+), ([\d.]+)\]x", ref_txt).groups()
    ref_tk = re.findall(r"ENRICHMENT RATIO ([\d.]+)x\n.*?CI \[([\d.]+), ([\d.]+)\]x", ref_txt)[-1]
    ref_thr = re.search(r"threshold = (\d+) raw/frame .*? threshold = ([\d.]+)/frame", ref_txt).groups()
    s_tr = ("%.2f" % tr282["enrich"], "%.2f" % tr282["ci"][0], "%.2f" % tr282["ci"][1])
    s_tk = ("%.2f" % tk282["enrich"], "%.2f" % tk282["ci"][0], "%.2f" % tk282["ci"][1])
    s_thr = ("%.0f" % thr_cmd, "%.1f" % thr_idx)
    pr("  transient enrichment %s vs stored %s ; top-1%% tick enrichment %s vs stored %s ; thresholds %s vs stored %s" % (
        s_tr, ref_tr, s_tk, ref_tk, s_thr, ref_thr))
    ok &= (s_tr == ref_tr) and (s_tk == ref_tk) and (s_thr == ref_thr)
    pr("  => REPRODUCTION %s" % ("EXACT (all counts, thresholds, ratios and CIs identical)" if ok else "FAILED -- stop"))
    assert ok, "the copied pipeline does not reproduce the stored V282 census"

    # ------------------------------------------------------------------ 1. exposure
    pr("\n" + "=" * 168)
    pr("1. EXPOSURE -- engaged (lateral) seconds per route and per stratum; V288 strata under 30 s are flagged")
    pr("=" * 168)
    SM = {tag: strata_masks(G[tag]) for tag in ALL}
    eng_s = {tag: G[tag]["eng"].sum() / FS for tag in ALL}
    pr("  %-28s %9s %9s %9s %11s | %9s %7s" % ("stratum", "r39 s", "r3a s", "r3c s", "V282 pool s", "V288 s", "flag"))
    pr("  %-28s %9.0f %9.0f %9.0f %11.0f | %9.0f" % ("ALL engaged", eng_s["r39"], eng_s["r3a"], eng_s["r3c"],
                                                      sum(eng_s[t] for t in V282_ROUTES), eng_s[V288_TAG]))
    expo = {}
    for st in STRATA_ORDER:
        row = {tag: (G[tag]["eng"] & SM[tag][st]).sum() / FS for tag in ALL}
        expo[st] = row
        pr("  %-28s %9.0f %9.0f %9.0f %11.0f | %9.0f %7s" % (st, row["r39"], row["r3a"], row["r3c"],
                                                           sum(row[t] for t in V282_ROUTES), row[V288_TAG],
                                                           "<30 s" if row[V288_TAG] < 30 else ""))
    pr("  speed profile (engaged): v p10/p50/p90 m/s -- " + " ; ".join(
        "%s %.1f/%.1f/%.1f" % ((tag,) + tuple(np.percentile(G[tag]["vego"][G[tag]["eng"]], (10, 50, 90)))) for tag in ALL))
    pr("  hands-on share (|bar|>700, engaged): " + " ; ".join(
        "%s %.1f%%" % (tag, 100 * np.mean(np.abs(G[tag]["bar"][G[tag]["eng"]]) > 700)) for tag in ALL))
    pr("  median idx (engaged): " + " ; ".join("%s %.0f" % (tag, np.median(G[tag]["idx"][G[tag]["eng"]])) for tag in ALL))

    # ------------------------------------------------------------------ 2. presence census
    pr("\n" + "=" * 168)
    pr("2. PRESENCE CENSUS (2 s windows, step 0.5 s, engaged; present = 15-26 Hz prominence >= 8 AND bar 18-22 >= 40 raw) -- unchanged")
    pr("=" * 168)
    pr("  %-9s %-14s %6s %6s %6s [95%% CI]      | %-24s | %-20s" % ("route", "build", "n", "pres", "%", "f mean sd p10/p90", "amp p50/p90/max raw"))
    for tag in ALL + ("V282pool",):
        sel = np.isin(R["tag"], V282_ROUTES) if tag == "V282pool" else (R["tag"] == tag)
        ps = sel & pres
        pc = boot_stat(pres[sel].astype(float), np.mean, rng, 1000)
        pr("  %-9s %-14s %6d %6d %6.1f [%4.1f,%4.1f] | %.2f %.2f %.2f/%.2f | %4.0f/%4.0f/%4.0f" % (
            tag, GRP.get(tag, "V282 pooled"), sel.sum(), ps.sum(), 100 * pres[sel].mean(), 100 * pc[0], 100 * pc[1],
            R["f0"][ps].mean() if ps.any() else np.nan, R["f0"][ps].std() if ps.any() else np.nan,
            *(np.percentile(R["f0"][ps], (10, 90)) if ps.any() else (np.nan, np.nan)),
            *np.percentile(R["amp"][sel], (50, 90)), R["amp"][sel].max()))
    pr("  (window CI = bootstrap over windows; windows overlap 4x, so these CIs are optimistic by ~2x)")
    pr("\n  2b. Operator's stratum -- engaged, hands-off (|bar| < 400), creep 1-3 m/s:")
    pr("  %-9s %7s %7s %7s %9s %9s %9s" % ("route", "n win", "pres", "%", "amp p50", "amp p90", "amp max"))
    for tag in ALL:
        sel = (R["tag"] == tag) & R["creep"] & R["hoff"]
        if sel.sum() < 5:
            pr("  %-9s %7d   (too thin)" % (tag, sel.sum())); continue
        pr("  %-9s %7d %7d %7.0f %9.0f %9.0f %9.0f" % (tag, sel.sum(), (sel & pres).sum(), 100 * pres[sel].mean(),
                                                     np.median(R["amp"][sel]), np.percentile(R["amp"][sel], 90), R["amp"][sel].max()))

    # per-stratum presence and band amplitude (window classified by its median frame values)
    pr("\n  2c. Presence and bar 18-22 amplitude PER STRATUM (window assigned by its median |bar| / |ang| / mean rate):")
    pr("  %-28s | %-30s | %-30s" % ("stratum", "V282 pooled: n win, pres %, amp p50/p90", "V288: n win, pres %, amp p50/p90"))
    wfb = {"FB: hands-on |bar|>700": R["tq"] > 700, "FB: |ang|>60 deg": R["ang"] > 60, "FB: wheel>25 deg/s": R["rate"] > 25}
    wfb["FB-dominated (any)"] = wfb["FB: hands-on |bar|>700"] | wfb["FB: |ang|>60 deg"] | wfb["FB: wheel>25 deg/s"]
    wfb["REF-dominated (none)"] = ~wfb["FB-dominated (any)"]
    wfb["REF & creep 1-3 m/s"] = wfb["REF-dominated (none)"] & (R["v"] >= 1) & (R["v"] < 3)
    wfb["REF & 3-8 m/s"] = wfb["REF-dominated (none)"] & (R["v"] >= 3) & (R["v"] < 8)
    wfb["REF & 8-15 m/s"] = wfb["REF-dominated (none)"] & (R["v"] >= 8) & (R["v"] < 15)
    wfb["REF & >=15 m/s"] = wfb["REF-dominated (none)"] & (R["v"] >= 15)
    wfb["REF & hands-off |bar|<400"] = wfb["REF-dominated (none)"] & (R["tq"] < 400)
    strat_pres = {}
    for st in STRATA_ORDER:
        s282 = np.isin(R["tag"], V282_ROUTES) & wfb[st]; s288 = (R["tag"] == V288_TAG) & wfb[st]
        f = lambda s: ("%5d %5.1f%% %5.0f/%5.0f" % (s.sum(), 100 * pres[s].mean(), np.median(R["amp"][s]), np.percentile(R["amp"][s], 90))) if s.sum() >= 5 else ("%5d   (thin)" % s.sum())
        strat_pres[st] = (s282, s288)
        pr("  %-28s | %-30s | %-30s" % (st, f(s282), f(s288)))

    # ------------------------------------------------------------------ 3. episodes
    pr("\n" + "=" * 168)
    pr("3. EPISODES (contiguous >= 0.5 s line-present, engaged) -- rate, class split, duration, amplitude, frequency")
    pr("=" * 168)
    pr("  total: %s" % ", ".join("%s=%d" % (t, sum(1 for e in episodes if e["tag"] == t)) for t in ALL))
    pr("\n  %-9s %-9s %6s %6s %6s %10s %8s %8s %8s %6s %6s %6s %6s %7s %6s %6s" % (
        "route", "class", "t0 s", "dur", "f0", "env pk", "18-22", "6-10", "corr7", "v", "|ang|", "rate", "idx", "|tq|", "trans", "creep"))
    for e in [e for e in episodes if e["tag"] == V288_TAG]:
        pr("  %-9s %-9s %6.1f %6.2f %6.1f %10.0f %8.0f %8.0f %8.2f %6.1f %6.0f %6.1f %6.0f %7.0f %6s %6s" % (
            e["tag"], e["cls"], e["t0"], e["dur"], e["f0"], e["env"], e["amp"], e["amp6"],
            e["corr7"] if np.isfinite(e["corr7"]) else -9, e["v"], abs(e["ang0"]), e["rate0"], e["idx0"], e["hands"],
            "Y" if e["trans"] else "n", "Y" if e["creep_onset"] else "n"))
    marks = [129.33, 331.54, 820.12]
    pr("\n  operator bookmarks (route-relative s) vs V288 episodes: " + " ; ".join(
        "%.1f -> %s" % (mk, ", ".join("%.1f-%.1f %s" % (e["t0"], e["t1"], e["cls"]) for e in episodes
                                       if e["tag"] == V288_TAG and e["t0"] - 5 <= mk <= e["t1"] + 5) or "no episode within 5 s") for mk in marks))

    # rate per engaged hour with a 30 s engaged-block bootstrap
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
    arms = [(t, (t,)) for t in ALL] + [("V282pool", V282_ROUTES)]
    for name, tags in arms:
        c, x = rate_blocks(tags)
        r = 3600 * c.sum() / x.sum()
        bs = []
        for _ in range(NB):
            j = rng.integers(0, len(c), len(c)); bs.append(3600 * c[j].sum() / max(x[j].sum(), 1))
        es = [e for e in episodes if e["tag"] in tags]
        cl = np.array([e["cls"] for e in es])
        parts = []
        for k in ("BURST", "SUSTAINED", "RIDE-ALONG"):
            fr = (cl == k).astype(float)
            cc = boot_stat(fr, np.mean, rng) if len(fr) >= 3 else (np.nan, np.nan)
            parts.append("%4.0f%% [%3.0f,%3.0f]" % (100 * fr.mean() if len(fr) else np.nan, 100 * cc[0], 100 * cc[1]))
        pr("  %-9s %6d %8.0f %10.0f [%5.0f, %5.0f]     | %-22s %-22s %-22s" % (name, len(es), x.sum(), r, *ci(bs), *parts))

    pr("\n  3b. Duration and amplitude distributions (bootstrap CI on the median, resample episodes):")
    pr("  %-9s %6s | %-28s | %-28s | %-28s | %8s" % ("arm", "n", "dur s p50 [CI] / p90 / max", "env peak raw p50 [CI] / p90 / max",
                                                     "bar 18-22 raw p50 [CI] / p90 / max", "mean env"))
    for name, tags in arms:
        es = [e for e in episodes if e["tag"] in tags]
        if not es:
            pr("  %-9s %6d   (none)" % (name, 0)); continue
        d = np.array([e["dur"] for e in es]); ev = np.array([e["env"] for e in es]); am = np.array([e["amp"] for e in es])
        fmt = lambda x: "%5.2f [%5.2f,%5.2f] %6.2f %6.2f" % (np.median(x), *boot_stat(x, np.median, rng, 2000), np.percentile(x, 90), x.max())
        pr("  %-9s %6d | %-28s | %-28s | %-28s | %8.0f" % (name, len(es), fmt(d), fmt(ev), fmt(am), ev.mean()))
    d282 = np.array([e["env"] for e in episodes if e["tag"] in V282_ROUTES]); d288 = np.array([e["env"] for e in episodes if e["tag"] == V288_TAG])
    if len(d288) >= 3:
        pr("  Mann-Whitney env peak V288 vs V282 pooled: U p = %.3g ; duration p = %.3g" % (
            stats.mannwhitneyu(d288, d282).pvalue,
            stats.mannwhitneyu([e["dur"] for e in episodes if e["tag"] == V288_TAG], [e["dur"] for e in episodes if e["tag"] in V282_ROUTES]).pvalue))

    pr("\n  3c. LINE FREQUENCY -- census f0 of present windows (the yardstick), and a fine (zero-padded, parabolic) line per episode >= 1 s:")
    pr("  %-9s %6s %7s %7s %7s %7s | %-40s | %-30s" % ("arm", "n win", "mean", "sd", "p10", "p90", "share 15-18/18-19.5/19.5-20.5/20.5-22/22-26", "fine f0 per episode p25/p50/p75 (n)"))
    for name, tags in arms:
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
    f288 = R["f0"][(R["tag"] == V288_TAG) & pres]; f282 = R["f0"][np.isin(R["tag"], V282_ROUTES) & pres]
    if len(f288) >= 5:
        pr("  KS test, present-window f0, V288 vs V282 pooled: D = %.3f, p = %.3g ; median %.2f vs %.2f Hz" % (
            *stats.ks_2samp(f288, f282)[:2], np.median(f288), np.median(f282)))

    # ------------------------------------------------------------------ 4. transient / tick enrichment, creep share
    pr("\n" + "=" * 168)
    pr("4. ONSET PREDICATES -- the V282 census's two enrichment tests, thresholds FROZEN at the pooled-V282 values")
    pr("=" * 168)
    pr("  top-1%% thresholds (pooled V282, frozen): |dcmd| >= %.0f raw/frame, didx >= %.1f/frame.  V288's own top-1%%: |dcmd| %.0f, didx %.1f (information only)" % (
        thr_cmd, thr_idx, *tick_thresholds(G, (V288_TAG,))))
    tr288 = transient_enrichment(G, episodes, (V288_TAG,), seed=0)
    tk288 = tick_enrichment(G, episodes, (V288_TAG,), thr_cmd, thr_idx, seed=1)
    pr("  %-9s %5s | %-44s | %-44s | %s" % ("arm", "n ep", "loose transient: P(base) P(onset) enrich [CI]", "top-1% tick: P(base) P(onset) enrich [CI]", "steady-creep onsets"))
    for name, tr, tk in (("V282pool", tr282, tk282), (V288_TAG, tr288, tk288)):
        pr("  %-9s %5d | %.3f  %.3f  %.2fx [%.2f, %.2f]                | %.3f  %.3f  %.2fx [%.2f, %.2f]                | %d (%.0f%%)" % (
            name, tr["n"], tr["p_base"], tr["p_ep"], tr["enrich"], *tr["ci"], tk["p_base"], tk["p_ep"], tk["enrich"], *tk["ci"],
            tr["n_creep"], 100 * tr["n_creep"] / max(tr["n"], 1)))
    pr("  per-class top-1%% tick enrichment: " + " | ".join(
        "%s: %s" % (name, ", ".join("%s n=%d %.2fx [%.2f,%.2f]" % (k, v[0], v[2], *v[3]) for k, v in tk["cls"].items())) for name, tk in (("V282pool", tk282), ("V288", tk288))))
    pr("\n  Operating point at onset (medians) vs all engaged frames:")
    pr("  %-26s %8s %8s %8s %8s %8s" % ("stratum", "n", "v p50", "|ang|p50", "rate p50", "idx p50"))
    for name, tags in (("V282pool", V282_ROUTES), (V288_TAG, (V288_TAG,))):
        allv = np.concatenate([G[t]["vego"][G[t]["eng"]] for t in tags]); alla = np.concatenate([np.abs(G[t]["ang"][G[t]["eng"]]) for t in tags])
        allr = np.concatenate([G[t]["rate"][G[t]["eng"]] for t in tags]); alli = np.concatenate([G[t]["idx"][G[t]["eng"]] for t in tags])
        pr("  %-26s %8d %8.1f %8.0f %8.1f %8.0f" % (name + " engaged frames", len(allv), np.median(allv), np.median(alla), np.median(allr), np.median(alli)))
        es = [e for e in episodes if e["tag"] in tags]
        if es:
            pr("  %-26s %8d %8.1f %8.0f %8.1f %8.0f" % (name + " onsets", len(es), np.median([e["v"] for e in es]), np.median([abs(e["ang0"]) for e in es]),
                                                     np.median([e["rate0"] for e in es]), np.median([e["idx0"] for e in es])))

    # episodes per stratum (onset frame's stratum) per engaged hour of that stratum
    pr("\n  4b. Episode ONSETS per engaged hour, by the onset frame's stratum (exposure = engaged s in that stratum):")
    pr("  %-28s | %-34s | %-34s | %s" % ("stratum", "V282 pooled: n / exposure s / ep per h", "V288: n / exposure s / ep per h", "ratio V288/V282 [CI, Poisson-ish]"))
    for st in STRATA_ORDER:
        row = []
        for tags in (V282_ROUTES, (V288_TAG,)):
            n = sum(1 for e in episodes if e["tag"] in tags and SM[e["tag"]][st][e["a"]])
            x = sum(expo[st][t] for t in tags)
            row.append((n, x, 3600 * n / x if x > 0 else np.nan))
        r282, r288 = row
        if r282[2] and r282[2] > 0 and np.isfinite(r288[2]) and r288[1] >= 30:
            # gamma-Poisson CI on the ratio
            lo_ = (stats.chi2.ppf(0.025, 2 * r288[0]) / 2 / r288[1]) / (r282[0] / r282[1]) if r288[0] > 0 else 0.0
            hi_ = (stats.chi2.ppf(0.975, 2 * r288[0] + 2) / 2 / r288[1]) / (r282[0] / r282[1])
            rr = "%.2f [%.2f, %.2f]" % (r288[2] / r282[2], lo_, hi_)
        else:
            rr = "(thin)"
        pr("  %-28s | %4d / %6.0f / %6.0f                 | %4d / %6.0f / %6.0f                 | %s" % (st, *r282, *r288, rr))

    # ------------------------------------------------------------------ 5. capped frames
    pr("\n" + "=" * 168)
    pr("5. PRE-REGISTERED ENDPOINT (a): the 122.88 slew cap -- capped-frame enrichment, D-clamp bind duty, 18-22 Hz envelope at capped onsets")
    pr("=" * 168)
    for tag in ALL:
        g, e = G[tag], G[tag]["e4"]
        d = np.diff(e["grid"]); base = e["egrid"][1:] & e["egrid"][:-1]
        e["d"], e["base"], e["cap"] = d, base, base & (np.abs(d) >= CAP)
        e["hot"] = np.interp(e["tgrid"], g["t"], g["hot"].astype(float))[1:] > 0.5
        e["onsets"] = np.array([int(np.searchsorted(e["tgrid"], g["t"][ep["a"]])) for ep in episodes if ep["tag"] == tag], int)
    pr("\n  5a. |dcmd| wall check and capped-frame fraction by stratum (wire_0xe4_slewcap.py (a), unchanged):")
    pr("  %-9s %9s | %s | %s" % ("route", "n frames", "  ".join("|d|=%d" % v for v in range(120, 125)), "frac capped (all engaged)"))
    for tag in ALL:
        e = G[tag]["e4"]; a_ = np.abs(e["d"])[e["base"]]
        pr("  %-9s %9d | %s | %.4f" % (tag, len(a_), "  ".join("%6d" % (a_ == v).sum() for v in range(120, 125)), np.mean(a_ >= CAP)))
    pr("\n  %-9s %-14s %9s %11s %11s %9s" % ("route", "stratum", "n frames", "frac capped", "vs baseline", "mean |d|"))
    for tag in ALL:
        e = G[tag]["e4"]; n = len(e["d"])
        w = np.zeros(n, bool); wp = np.zeros(n, bool)
        for i0 in e["onsets"]:
            w[max(0, i0 - 50):min(n, i0 + 51)] = True; wp[max(0, i0 - 50):min(n, i0)] = True
        sel = {"onset +-0.5 s": e["base"] & w, "pre-onset": e["base"] & wp, "episode body": e["base"] & e["hot"], "baseline": e["base"] & ~e["hot"]}
        fb_ = np.mean(np.abs(e["d"])[sel["baseline"]] >= CAP)
        for lab in ("onset +-0.5 s", "pre-onset", "episode body", "baseline"):
            s = sel[lab]
            if s.sum() == 0:
                pr("  %-9s %-14s %9d" % (tag, lab, 0)); continue
            fr = np.mean(np.abs(e["d"])[s] >= CAP)
            pr("  %-9s %-14s %9d %11.4f %11s %9.2f" % (tag, lab, s.sum(), fr, "%.1fx" % (fr / fb_) if lab != "baseline" and fb_ > 0 else "-", np.abs(e["d"])[s].mean()))
    pr("\n  episode-level: P(a capped frame within +-0.5 s of onset) vs 1 Hz-sampled engaged baseline; CI resamples episodes:")
    pr("  %-9s %7s %14s %14s %11s %-22s" % ("route", "n eps", "P(cap +-0.5s)", "baseline P", "enrich", "95 % CI"))
    for tag in ALL:
        e = G[tag]["e4"]; n = len(e["d"])
        hit = np.array([bool((e["base"][max(0, i0 - 50):min(n, i0 + 51)] & (np.abs(e["d"])[max(0, i0 - 50):min(n, i0 + 51)] >= CAP)).any()) for i0 in e["onsets"]], bool)
        idx = np.flatnonzero(e["base"])[::100]
        bh = np.array([bool((e["base"][max(0, i - 50):min(n, i + 51)] & (np.abs(e["d"])[max(0, i - 50):min(n, i + 51)] >= CAP)).any()) for i in idx])
        pb = bh.mean()
        if len(hit) >= 3 and pb > 0:
            bs = [hit[rng.integers(0, len(hit), len(hit))].mean() / pb for _ in range(NB)]
            pr("  %-9s %7d %14.3f %14.3f %11.2fx [%.2f, %.2f]x" % (tag, len(hit), hit.mean(), pb, hit.mean() / pb, *ci(bs)))
        else:
            pr("  %-9s %7d %14s %14.3f" % (tag, len(hit), "(thin)", pb))

    # ---- 5b. D-clamp bind duty: whole engaged route through the mirror
    pr("\n  5b. D-CLAMP BIND DUTY, 1 kHz mirror over EVERY engaged run >= 1 s (V282 cells; |dE*128/8| > 10240):")
    pr("      V282 routes: raw setpoint (as flown).  V288: the cave filter in the setpoint path (as flown) AND the same route")
    pr("      with the filter removed (counterfactual 'V282 arithmetic on V288's drive') -- the within-route effect of the filter.")
    pr("      CI = bootstrap over 10 s tick blocks.  P(cap|bind) = fraction of binding ticks on a capped command frame.")
    # self-check: simulate_sp(spfilt_k=None) == GI.simulate bit for bit on a test window
    g0 = G["r39"]; a0, b0 = [(e["a"], e["b"]) for e in episodes if e["tag"] == "r39"][0]
    o1 = GI.simulate(g0, a0, b0, c282); o2 = simulate_sp(g0, a0, b0, c282)
    assert np.array_equal(o1["T"], o2["T"]) and o1["drail"] == o2["drail"], "simulate_sp diverges from GI.simulate"
    pr("      self-check: simulate_sp(no filter) reproduces GI.simulate bit-for-bit on r39 t %.1f (T identical, drail %.4f) -- OK" % (g0["tr"][a0], o1["drail"]))
    pr("  %-9s %-22s %10s %10s %12s %-18s | %10s %10s | %12s %12s" % ("route", "arithmetic", "live ticks", "binds", "duty", "95% CI", "in-episode", "outside", "P(cap|bind)", "cap frac"))
    DUTY = CACHED.get("DUTY", {})
    rng5 = np.random.default_rng(5)
    for tag in ALL:
        g = G[tag]; c = cells[CEN.CELL_OF[tag]]
        e = g["e4"]
        capf = np.interp(g["t"], e["tgrid"][1:], (np.abs(e["d"]) >= CAP).astype(float)) > 0.5
        variants = [("raw sp (V282)", None)] if tag != V288_TAG else [("V288 filter K=4", K_SHIFT), ("filter REMOVED", None)]
        for lab, k in variants:
            if (tag, lab) in DUTY:
                r_ = DUTY[(tag, lab)]
                pr("  %-9s %-22s %10d %10d %12.5f [%.5f, %.5f] | %10.5f %10.5f | %12.3f %12.4f   (cached)" % (
                    tag, lab, r_["nlive"], r_["nb"], r_["duty"], *r_["ci"], r_["d_in"], r_["d_out"], r_["pcb"], r_["capfrac"]))
                continue
            live_all, bind_all, hot_all, cap_all = [], [], [], []
            for a, b in C20.runs(g["eng"], int(FS)):
                o = simulate_sp(g, a, b, c, spfilt_k=k)
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
            pr("  %-9s %-22s %10d %10d %12.5f [%.5f, %.5f] | %10.5f %10.5f | %12.3f %12.4f" % (
                tag, lab, live.sum(), bind[live].sum(), duty, *ci(bs), d_in, d_out, pcb, capk[live].mean()))
    v = DUTY[(V288_TAG, "V288 filter K=4")]; u = DUTY[(V288_TAG, "filter REMOVED")]
    pr("  => within-route filter effect on V288's drive: duty %.5f -> %.5f (x%.3f); in-episode %.4f -> %.4f" % (
        u["duty"], v["duty"], v["duty"] / max(u["duty"], 1e-12), u["d_in"], v["d_in"]))
    pr("     (the per-tick D kick is /16 by construction; a residual bind on V288 means |dsp| per TICK still exceeded 640 after filtering,")
    pr("      i.e. |sp - y| > 10240, which the +-1032 setpoint range cannot reach -- so V288 residual binds are FEEDBACK-driven (dfb > 10240/tick).)")

    # ---- 5c. envelope triggered on capped-frame onsets
    pr("\n  5c. 18-22 Hz BAR ENVELOPE TRIGGERED ON CAPPED-FRAME ONSETS (first capped frame after >= 0.2 s uncapped, engaged for the whole")
    pr("      -0.5..+1.0 s window).  Pre = median envelope over -0.5..0 s; post-peak = max over 0..+0.5 s.  CI = bootstrap over events.")
    pr("      Stratum = the onset frame's stratum.  This is the rung-bell test: does a capped step ring the 20 Hz mode less on V288?")
    EV = {}
    for tag in ALL:
        g, e = G[tag], G[tag]["e4"]
        env = CEN.envelope(g["bar"], 20.0, FS)                     # 18-22 Hz Hilbert envelope on the frame axis
        envr = CEN.envelope(g["wire"], 20.0, FS) / V.CPD
        cap = e["cap"]
        n = len(cap)
        on = np.flatnonzero(cap[20:] & ~np.array([cap[i - 20:i].any() for i in range(20, n)])) + 20
        rows = []
        for i in on:
            ti = e["tgrid"][i + 1]
            j = int(np.searchsorted(g["t"], ti))
            if j - 50 < 0 or j + 101 >= len(g["t"]) or not g["eng"][j - 50:j + 101].all():
                continue
            # run length of this capped run (frames)
            rl = 1
            while i + rl < n and cap[i + rl]:
                rl += 1
            pre = np.median(env[j - 50:j]); post = env[j:j + 50].max(); post2 = env[j + 50:j + 100].max()
            prer = np.median(envr[j - 50:j]); postr = envr[j:j + 50].max()
            rows.append(dict(j=j, rl=rl, pre=pre, post=post, post2=post2, prer=prer, postr=postr, hot=bool(g["hot"][j]),
                             strata={st: bool(SM[tag][st][j]) for st in STRATA_ORDER},
                             curve=env[j - 50:j + 101]))
        EV[tag] = rows
    pr("  %-9s %-28s %6s | %8s %8s %8s %-16s | %8s %8s %-16s | %s" % ("arm", "stratum", "n ev", "pre p50", "post p50", "ratio", "95% CI", "rate pre", "rate post", "ratio CI", "P(episode within 0.5 s)"))

    def ev_row(name, rows, st, gref):
        sel = [r for r in rows if st is None or r["strata"][st]]
        if len(sel) < 5:
            pr("  %-9s %-28s %6d   (thin)" % (name, st or "ALL", len(sel))); return
        pre = np.array([r["pre"] for r in sel]); post = np.array([r["post"] for r in sel])
        prer = np.array([r["prer"] for r in sel]); postr = np.array([r["postr"] for r in sel])
        ratio = lambda idx: np.median(post[idx]) / max(np.median(pre[idx]), 1e-9)
        ratior = lambda idx: np.median(postr[idx]) / max(np.median(prer[idx]), 1e-9)
        bs = [ratio(rng.integers(0, len(sel), len(sel))) for _ in range(2000)]
        bsr = [ratior(rng.integers(0, len(sel), len(sel))) for _ in range(2000)]
        # episode within 0.5 s after the onset
        pe = float(np.mean([gref["hot"][r["j"]:r["j"] + 50].any() for r in sel]))
        pr("  %-9s %-28s %6d | %8.1f %8.1f %8.3f [%.3f, %.3f]   | %8.2f %8.2f [%.3f, %.3f]   | %s" % (
            name, st or "ALL", len(sel), np.median(pre), np.median(post), ratio(np.arange(len(sel))), *ci(bs),
            np.median(prer), np.median(postr), *ci(bsr), "%.2f" % pe if np.isfinite(pe) else "-"))

    for st in (None, "FB-dominated (any)", "REF-dominated (none)", "REF & hands-off |bar|<400", "REF & creep 1-3 m/s", "REF & 3-8 m/s", "REF & 8-15 m/s"):
        for tag in ALL:
            ev_row(tag, EV[tag], st, G[tag])
        pooled = [r for t in V282_ROUTES for r in EV[t]]
        sel = [r for r in pooled if st is None or r["strata"][st]]
        if len(sel) >= 5:
            pre = np.array([r["pre"] for r in sel]); post = np.array([r["post"] for r in sel])
            bs = [np.median(post[j]) / max(np.median(pre[j]), 1e-9) for j in (rng.integers(0, len(sel), len(sel)) for _ in range(2000))]
            pr("  %-9s %-28s %6d | %8.1f %8.1f %8.3f [%.3f, %.3f]" % ("V282pool", st or "ALL", len(sel), np.median(pre), np.median(post), np.median(post) / np.median(pre), *ci(bs)))
        pr("")
    pr("  5c-ii. Median envelope CURVE around capped onsets, REF-dominated onsets only (raw bar 18-22 envelope at lags, s):")
    lags = (-0.4, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0)
    pr("  %-9s %5s | %s" % ("arm", "n", " ".join("%6.2f" % l for l in lags)))
    for name, tags in arms:
        sel = [r for t in tags for r in EV[t] if r["strata"]["REF-dominated (none)"]]
        if len(sel) < 5:
            continue
        cur = np.median(np.array([r["curve"] for r in sel]), 0)
        pr("  %-9s %5d | %s" % (name, len(sel), " ".join("%6.1f" % cur[int(round(50 + l * FS))] for l in lags)))
    pr("  5c-iii. Same, split by capped-run length (a single capped frame vs a >= 3-frame ramp), REF-dominated, post/pre ratio:")
    for name, tags in arms:
        sel = [r for t in tags for r in EV[t] if r["strata"]["REF-dominated (none)"]]
        parts = []
        for lab, f in (("run=1", lambda r: r["rl"] == 1), ("run 2", lambda r: r["rl"] == 2), ("run>=3", lambda r: r["rl"] >= 3)):
            ss = [r for r in sel if f(r)]
            if len(ss) < 5:
                parts.append("%s n=%d (thin)" % (lab, len(ss))); continue
            pre = np.array([r["pre"] for r in ss]); post = np.array([r["post"] for r in ss])
            bs = [np.median(post[j]) / max(np.median(pre[j]), 1e-9) for j in (rng.integers(0, len(ss), len(ss)) for _ in range(2000))]
            parts.append("%s n=%d pre %.0f post %.0f ratio %.3f [%.3f,%.3f]" % (lab, len(ss), np.median(pre), np.median(post), np.median(post) / np.median(pre), *ci(bs)))
        pr("  %-9s | %s" % (name, " | ".join(parts)))

    # ------------------------------------------------------------------ 6. spectra
    pr("\n" + "=" * 168)
    pr("6. WHOLE-ROUTE SPECTRAL SHIFT -- pooled engaged PSDs (Hann, 50 %% overlap, 0.195 Hz bins), band powers and a scan for NEW lines > 22 Hz")
    pr("=" * 168)
    SPEC = {}
    for tag in ALL:
        g = G[tag]
        for stname, smask in (("ALL", np.ones(len(g["eng"]), bool)), ("REF", SM[tag]["REF-dominated (none)"]), ("FB", SM[tag]["FB-dominated (any)"])):
            msk = g["eng"] & smask
            runs = C20.runs(msk, 512)
            fb_, Pb = seg_psds([g["bar"][a:b] for a, b in runs], FS, 512)
            _, Pw = seg_psds([g["wire"][a:b] / V.CPD for a, b in runs], FS, 512)
            Truns = []
            for a, b in runs:
                s_ = (g["T_t"] >= g["t"][a]) & (g["T_t"] <= g["t"][b - 1])
                Truns.append(g["T"][s_])
            fT, PT = seg_psds(Truns, FST, 256)
            SPEC[(tag, stname)] = dict(f=fb_, bar=Pb, wire=Pw, fT=fT, T=PT)
    pr("\n  6a. Band POWER (units^2: bar raw^2, wheel rate (deg/s)^2, T raw^2), engaged, with segment-bootstrap CIs; ratio V288 / each V282 route:")
    pr("  %-4s %-5s %-9s %7s | %-26s %-26s %-16s" % ("str", "sig", "route", "n seg", "6-10 Hz p [CI]", "18-22 Hz p [CI]", "22-49 Hz p"))
    BP = {}
    for stname in ("ALL", "REF", "FB"):
        for sig in ("bar", "wire", "T"):
            for tag in ALL:
                S = SPEC[(tag, stname)]
                f = S["fT"] if sig == "T" else S["f"]; P = S[sig]
                if len(P) < 5:
                    pr("  %-4s %-5s %-9s %7d   (thin)" % (stname, sig, tag, len(P))); continue
                b6 = bandpow(f, P, 6, 10); b18 = bandpow(f, P, 18, 22); b22 = bandpow(f, P, 22, min(49, f[-1]))
                c6 = boot_stat(b6, np.mean, rng, 1000); c18 = boot_stat(b18, np.mean, rng, 1000)
                BP[(stname, sig, tag)] = (b6.mean(), b18.mean(), b22.mean())
                pr("  %-4s %-5s %-9s %7d | %9.3g [%8.3g,%8.3g] %9.3g [%8.3g,%8.3g] %9.3g" % (stname, sig, tag, len(P), b6.mean(), *c6, b18.mean(), *c18, b22.mean()))
            if all((stname, sig, t) in BP for t in ALL):
                pr("  %-4s %-5s %-9s         | ratios V288/r39, /r3a, /r3c : 6-10 Hz %.2f %.2f %.2f | 18-22 Hz %.2f %.2f %.2f | (18-22)/(6-10) V288 %.3f vs V282 %.3f %.3f %.3f" % (
                    stname, sig, "RATIO", *[BP[(stname, sig, V288_TAG)][0] / BP[(stname, sig, t)][0] for t in V282_ROUTES],
                    *[BP[(stname, sig, V288_TAG)][1] / BP[(stname, sig, t)][1] for t in V282_ROUTES],
                    BP[(stname, sig, V288_TAG)][1] / BP[(stname, sig, V288_TAG)][0], *[BP[(stname, sig, t)][1] / BP[(stname, sig, t)][0] for t in V282_ROUTES]))
    pr("\n  6b. LINE SCAN above 22 Hz (bar and wheel rate, 100 Hz streams; the tap is 50 Hz and cannot see > 25 Hz).  Excess = log-PSD minus a")
    pr("      +-2 Hz running-median baseline; peaks by excess with a segment-bootstrap CI.  'NEW' = on V288 with excess >= 3 dB and CI low > 1 dB,")
    pr("      and no V282 route within +-0.5 Hz with excess >= 2 dB.  Known: the 39.9 Hz second harmonic of the 20 Hz line is on every V282 route.")
    LINES = {}
    for stname in ("ALL", "REF"):
        for sig in ("bar", "wire"):
            for tag in ALL:
                S = SPEC[(tag, stname)]; f = S["f"]; P = S[sig]
                if len(P) < 5:
                    continue
                Pm = P.mean(0); ex = excess_db(f, Pm)
                sel = (f >= 22.5) & (f <= 49.0)
                pk, props = signal.find_peaks(np.where(sel, ex, -99), prominence=1.0)
                order = pk[np.argsort(-ex[pk])][:6]
                rows = []
                for i in order:
                    bs = []
                    for _ in range(300):
                        j = rng.integers(0, len(P), len(P))
                        bs.append(excess_db(f, P[j].mean(0))[i])
                    rows.append((f[i], ex[i], *ci(bs)))
                LINES[(stname, sig, tag)] = rows
                pr("  %-4s %-5s %-9s : %s" % (stname, sig, tag, " ; ".join("%.2f Hz %+.1f dB [%+.1f,%+.1f]" % r for r in rows)))
            if (stname, sig, V288_TAG) in LINES:
                new = []
                for f0, ex0, lo_, hi_ in LINES[(stname, sig, V288_TAG)]:
                    if ex0 >= 3.0 and lo_ > 1.0:
                        seen = any(abs(f0 - r[0]) <= 0.5 and r[1] >= 2.0 for t in V282_ROUTES for r in LINES.get((stname, sig, t), []))
                        if not seen:
                            new.append("%.2f Hz %+.1f dB" % (f0, ex0))
                pr("  %-4s %-5s NEW lines on V288 not on any V282 route: %s" % (stname, sig, ", ".join(new) if new else "none"))
    # the 18-22 line itself, same excess metric (is the LINE weaker, not just the band?)
    pr("\n  6c. The 18-22 Hz LINE's own excess over its shoulder (same metric, peak in 18-22), bar / wheel rate / T, ALL and REF strata:")
    pr("  %-4s %-9s | %-28s | %-28s | %-28s" % ("str", "route", "bar: f, excess dB [CI]", "wheel rate: f, excess dB [CI]", "T: f, excess dB [CI]"))
    for stname in ("ALL", "REF", "FB"):
        for tag in ALL:
            parts = []
            for sig in ("bar", "wire", "T"):
                S = SPEC[(tag, stname)]; f = S["fT"] if sig == "T" else S["f"]; P = S[sig]
                if len(P) < 5:
                    parts.append("(thin)"); continue
                ex = excess_db(f, P.mean(0)); sel = (f >= 18) & (f <= 22)
                i = np.flatnonzero(sel)[np.argmax(ex[sel])]
                bs = [excess_db(f, P[rng.integers(0, len(P), len(P))].mean(0))[i] for _ in range(300)]
                parts.append("%.2f Hz %+5.1f dB [%+.1f,%+.1f]" % (f[i], ex[i], *ci(bs)))
            pr("  %-4s %-9s | %-28s | %-28s | %-28s" % (stname, tag, *parts))

    with open(os.path.join(SCR, "grind1_census_v288_r5e.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote", os.path.join(SCR, "grind1_census_v288_r5e.txt"))


if __name__ == "__main__":
    main()
