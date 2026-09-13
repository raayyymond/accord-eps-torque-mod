# -*- coding: utf-8 -*-
"""V292 FLIGHT READ -- deliverable 2: THE PRE-REGISTERED READ (a)-(f), on the three V292 routes flown
2026-09-13, against r6c (V282, 2026-09-12) and r39 (V282, the record's grinding reference).

    r6d_v292 = 75604b0a432fdc89_0000006d--5e7b4d2ceb   (18 segs)
    r6e_v292 = 75604b0a432fdc89_0000006e--64b4a5fef4   (23 segs)
    r6f_v292 = 75604b0a432fdc89_0000006f--d876c761bc   (13 segs)
    r6c      = 75604b0a432fdc89_0000006c--2bc842dbac   (62 segs, V282 from the tap)
    r39      = the record's V282 grinding reference

METHOD FIDELITY: the census pipeline is IMPORTED VERBATIM from grind1_census_v288_r5e.py (which copied it
from grind1_census_v282.main()), exactly as grind1_census_v289_r62_r63.py did -- same window length, same
presence predicate (`prom >= 8 AND 18-22 Hz bar amplitude >= 40`), same episode extractor, same strata.
Loader wire_0xe4_20hz.load_route.  Cells read from the IMAGES.

THE PRE-REGISTERED READ (docs/review/ADVERSARIAL-V292-PREREG-2026-09-13.md, "The read, as amended by A2";
docs/STATE.md "THE READ"):
  (a) 18-22 Hz ring on the 0x18F STEER_ANGLE_RATE in hands-off creep: amplitude, presence rate, envelope
      half-peak decay.  Predicted 545 -> 183 ms.
      *** 545/183 ms are MODEL numbers (DESIGN-V291-FBLP "ring FULL / SUB 582 / 545 ms"; ADV-V291-B
      "180 / 183 ms"), and V292-REPLAY-PREDICTION section 4.2 SHOWED BEFORE THE DRIVE that the DRIVEN
      half-peak metric is confounded: V282 driven 344 ms, V292 driven 441 ms, the disturbance's own
      envelope 276 ms.  So the driven decay is reported as a number, NOT as the test. ***
      The replay's own on-data prediction is the AMPLITUDE: ring x0.55 of V282 (x0.71 vs r6c).
  (b) T (0x1AB, gp-0x6B38 sar0 -- IDENTICAL tap on V282 and V292, read from both images) vs 0x18F rate
      cross-spectrum phase at 10 Hz.  Predicted -14 deg +- 4.
  (c) b3 duty vs ring amplitude.
  (d) the 9-18 Hz shoulder: predicted x1.33-1.70 byte-exact worst-fit sensitivity, replay x1.09-1.17.
  (e) any 22-30 Hz line.
  (f) did the 18-22 Hz object MOVE (V289 moved it to 15-17 Hz)?

ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing.
Run: python rlog-tools/studies/grind/v292_flight_census.py
"""
import hashlib
import io
import json
import os
import pickle
import sys

import numpy as np
from scipy import signal

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
import grind1_census_v282 as CEN              # noqa: E402
import grind1_census_v288_r5e as C88          # noqa: E402
import wire_0xe4_20hz as WIRE                 # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FS1K = 100.0, 1000.0
LO, HI = 18.0, 22.0
V292_IMG = (LG.FW + "_v292_V292-V282BASE-EFCAVE.C4C00.6D74-FBPOLE.10HZ.962.958-R24.4725-B3.FBSTATE-"
            "KP.FLAT.Y0-CAVE.R24CMP.B5.B6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
V292_SHA_PREFIX = "d1128232"
V292_ROUTES = ("r6d_v292", "r6e_v292", "r6f_v292")
V282_REF = ("r6c", "r39")
ALL = V292_ROUTES + V282_REF
CACHE_P = os.path.join(SCR, "v292_flight_census_cache.pkl")
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def ci(x, q=(2.5, 97.5)):
    return C88.ci(x, q)


def boot_ratio(a, b, rng, n=4000):
    """bootstrap CI of median(a)/median(b), resampling each arm independently."""
    a = np.asarray(a, float); a = a[np.isfinite(a)]
    b = np.asarray(b, float); b = b[np.isfinite(b)]
    if len(a) < 3 or len(b) < 3:
        return np.nan, np.nan, np.nan
    r = np.array([np.median(a[rng.integers(0, len(a), len(a))]) / np.median(b[rng.integers(0, len(b), len(b))])
                  for _ in range(n)])
    return float(np.median(a) / np.median(b)), float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5))


def load_b3(tag, g):
    """0x14A b3 on the 0x18F frame axis (nearest), the same way the V289 census did it."""
    B = dict(np.load(os.path.join(C20.CACHE, tag + "_b4.npz")))
    k14, P14, tn14, _ = C20.dejitter(B["t14b"].astype(float), 0.01, 100)
    b4 = B["b4"].astype(int)
    for n in (3, 5, 6, 7):
        g["bit%d" % n] = np.round(np.interp(g["t"], tn14, ((b4 >> n) & 1).astype(float)))
    return g


def psd_of(g, mask, ch, nperseg=512, minrun=None):
    """pooled Welch over contiguous runs of `mask`, on channel `ch` (a key of g)."""
    minrun = minrun or nperseg
    runs = [g[ch][a:b] for a, b in C20.runs(mask, minrun)]
    f, P = C88.seg_psds(runs, FS, nperseg)
    if P.shape[0] == 0:
        return f, None, 0
    return f, P, P.shape[0]


def line_in(f, Pm, lo, hi, half=2.0):
    """(peak frequency, EXCESS in dB over a running-median baseline) inside [lo,hi]."""
    ex = C88.excess_db(f, Pm, half_hz=half)
    sl = (f >= lo) & (f <= hi)
    if not sl.any():
        return np.nan, np.nan
    j = np.argmax(ex[sl])
    return float(f[sl][j]), float(ex[sl][j])


def main():
    rng = np.random.default_rng(20260913)

    # ---------------------------------------------------------------- 0. images and cells
    sha = hashlib.sha256(open(V292_IMG, "rb").read()).hexdigest()
    assert sha.startswith(V292_SHA_PREFIX), "V292 image hash mismatch: %s" % sha
    CEN.IMG["V292"] = V292_IMG
    for t in V292_ROUTES:
        CEN.CELL_OF[t] = "V292"
    CEN.CELL_OF["r6c"] = "V282"
    cells = {k: GI.read_cells(p) for k, p in CEN.IMG.items() if k in ("V282", "V292")}
    c282, c292 = cells["V282"], cells["V292"]
    diffs = []
    for k in c282:
        a_, b_ = c282[k], c292[k]
        same = (np.array_equal(np.asarray(a_[0]), np.asarray(b_[0])) and
                np.array_equal(np.asarray(a_[1]), np.asarray(b_[1]))) \
            if isinstance(a_, tuple) else np.array_equal(np.asarray(a_), np.asarray(b_))
        if not same:
            diffs.append(k)
    pr("=" * 150)
    pr("V292 FLIGHT READ -- THE PRE-REGISTERED READ (a)-(f).  Three V292 routes vs r6c (V282) and r39 (V282).")
    pr("=" * 150)
    pr("V292 image sha256 %s (verified against STATE's d1128232...)" % sha)
    pr("cells read from the V292 image vs the V282 image (GI.read_cells, %d keys): DIFFER in %s" % (len(c282), diffs))
    pr("   fb pole  V282 %d/%d  ->  V292 %d/%d   (16.53 -> 9.94 Hz, DC held)" %
       (c282["fb_a"], c282["fb_b"], c292["fb_a"], c292["fb_b"]))
    pr("   427 tap: IDENTICAL on both images (gp-0x6B38, sar 0) -- verified by extract_route_generic.py --check,")
    pr("            so T is directly comparable between r6c/r39 and the three V292 routes.")
    pr("🛑 CONFOUND, from initData.params: the openpilot fork changed between r6c and these routes --")
    pr("   GitCommit 57410c3b (Sep 10) -> 305732c85 (Sep 12), DrivingModel tsfdo -> gyhu3, and every")
    pr("   Accord* param key present on r6c is ABSENT on r6d/r6e/r6f (params store wiped/migrated).")
    pr("   A different driving model = a different 0xE4 command = a different LKAS excitation.")
    pr("   Bands the command drives are NOT a clean build contrast.  Matched strata are stated where used.")

    # ---------------------------------------------------------------- 1. load
    G = {}
    for tag in ALL:
        G[tag] = load_b3(tag, WIRE.load_route(tag, cells[CEN.CELL_OF[tag]]))
        g = G[tag]
        pr("  loaded %-10s %7.1f s route, %7.1f s engaged-lateral, build cells %s"
           % (tag, g["tr"][-1], g["eng"].sum() / FS, CEN.CELL_OF[tag]))

    # ---------------------------------------------------------------- 2. window census (the record's yardstick)
    CACHED = pickle.load(open(CACHE_P, "rb")) if os.path.exists(CACHE_P) else {}
    if "R" in CACHED and set(CACHED.get("tags", [])) == set(ALL):
        R, pres, episodes = CACHED["R"], CACHED["pres"], CACHED["episodes"]
        for tag in ALL:
            G[tag]["hot"] = CACHED["hot"][tag]
        pr("\n  (window census + episodes loaded from cache)")
    else:
        R, pres = C88.window_census(G, ALL)
        episodes = C88.extract_episodes(G, R, pres, ALL)
        CACHED = dict(R=R, pres=pres, episodes=episodes, hot={t: G[t]["hot"] for t in ALL}, tags=list(ALL))
        pickle.dump(CACHED, open(CACHE_P, "wb"))

    pr("")
    pr("=" * 150)
    pr("1.  WINDOW CENSUS -- the V282 yardstick, unchanged (presence = 18-22 Hz prominence >= 8 AND bar amp >= 40)")
    pr("=" * 150)
    pr("%-10s %-7s %7s %7s %7s | %-38s | %-38s" % ("route", "build", "n_win", "n_pres", "pres%",
                                                   "18-22 Hz RATE amp, deg/s (all present)", "18-22 Hz bar amp (all present)"))
    pr("%-10s %-7s %7s %7s %7s | %8s %8s %8s %10s | %8s %8s %8s" %
       ("", "", "", "", "", "p50", "p90", "max", "95% CI p50", "p50", "p90", "max"))
    tab = {}
    for tag in ALL:
        sel = R["tag"] == tag
        p = sel & pres
        ra = R["ramp"][p]; ba = R["amp"][p]
        lo_, hi_ = ci(np.array([np.median(ra[rng.integers(0, len(ra), len(ra))]) for _ in range(2000)])) if len(ra) > 3 else (np.nan, np.nan)
        tab[tag] = dict(n=int(sel.sum()), npres=int(p.sum()), ramp=ra, amp=ba)
        pr("%-10s %-7s %7d %7d %6.1f%% | %8.3f %8.3f %8.3f [%.3f,%.3f] | %8.1f %8.1f %8.1f" % (
            tag, CEN.CELL_OF[tag], sel.sum(), p.sum(), 100.0 * p.sum() / max(1, sel.sum()),
            np.median(ra) if len(ra) else np.nan, np.percentile(ra, 90) if len(ra) else np.nan,
            ra.max() if len(ra) else np.nan, lo_, hi_,
            np.median(ba) if len(ba) else np.nan, np.percentile(ba, 90) if len(ba) else np.nan,
            ba.max() if len(ba) else np.nan))

    # ---------------------------------------------------------------- 3. (a) matched: HANDS-OFF CREEP
    pr("")
    pr("=" * 150)
    pr("2.  (a) THE RING IN HANDS-OFF CREEP -- the pre-registered stratum.  hands-off = median |bar| < 400;")
    pr("        creep = 1-3 m/s.  ALL engaged windows in the stratum, present or not (so presence RATE is a")
    pr("        result, not a selection).  Ring amplitude is on the 0x18F STEER_ANGLE_RATE, deg/s.")
    pr("=" * 150)
    STRATA = [("hands-off creep 1-3 m/s", lambda R_, s: s & R_["hoff"] & R_["creep"]),
              ("hands-off 3-8 m/s", lambda R_, s: s & R_["hoff"] & (R_["v"] >= 3) & (R_["v"] < 8)),
              ("hands-off 8-15 m/s", lambda R_, s: s & R_["hoff"] & (R_["v"] >= 8) & (R_["v"] < 15)),
              ("hands-off >=15 m/s", lambda R_, s: s & R_["hoff"] & (R_["v"] >= 15)),
              ("hands-ON (|bar|>=400), any v", lambda R_, s: s & ~R_["hoff"]),
              ("ALL engaged", lambda R_, s: s)]
    ratio_rows = {}
    for lab, fn in STRATA:
        pr("")
        pr("  --- %s ---" % lab)
        pr("  %-10s %7s %7s %8s | %9s %9s %9s | %9s" %
           ("route", "n_win", "n_pres", "pres%", "rate p50", "rate p90", "rate mean", "vs r6c"))
        base = None
        for tag in ALL:
            s = R["tag"] == tag
            m = fn(R, s)
            if m.sum() < 12:
                pr("  %-10s %7d   -- too few windows in this stratum --" % (tag, m.sum()))
                continue
            ra = R["ramp"][m]
            npres = int((m & pres).sum())
            if tag == "r6c":
                base = ra
            pr("  %-10s %7d %7d %7.1f%% | %9.4f %9.4f %9.4f | %s" % (
                tag, m.sum(), npres, 100.0 * npres / m.sum(),
                np.median(ra), np.percentile(ra, 90), ra.mean(),
                "(base)" if tag == "r6c" else ""))
            ratio_rows.setdefault(lab, {})[tag] = ra
        if base is not None:
            pr("  ratio of median 18-22 Hz RATE amplitude to r6c (bootstrap 95%% CI):")
            for tag in ALL:
                if tag == "r6c" or tag not in ratio_rows.get(lab, {}):
                    continue
                r_, l_, h_ = boot_ratio(ratio_rows[lab][tag], base, rng)
                pr("     %-10s x%.3f  [%.3f, %.3f]" % (tag, r_, l_, h_))

    # ---------------------------------------------------------------- 4. (a) the driven half-peak decay
    pr("")
    pr("=" * 150)
    pr("3.  (a cont.) THE DRIVEN ENVELOPE HALF-PEAK DECAY -- reported, NOT used as the test.")
    pr("    The pre-registered 545 -> 183 ms are MODEL numbers.  V292-REPLAY-PREDICTION section 4.2 showed")
    pr("    BEFORE the drive that the DRIVEN metric is confounded (V282 driven 344 ms, V292 driven 441 ms,")
    pr("    the disturbance's own envelope 276 ms) -- a driven envelope's decay measures peak-to-background")
    pr("    contrast, not ring-down, and is not matched when the two arms' rings differ in size.")
    pr("=" * 150)
    pr("  %-10s %6s | %9s %9s %9s | %9s %9s | %8s" %
       ("route", "n_ep", "dur p50", "f0 p50", "env p50", "decay p50", "decay p90", "ep/eng.h"))
    ep_by = {}
    for tag in ALL:
        es = [e for e in episodes if e["tag"] == tag]
        ep_by[tag] = es
        if not es:
            pr("  %-10s %6d   -- no episodes --" % (tag, 0))
            continue
        dur = np.array([e["dur"] for e in es])
        f0 = np.array([e["f0"] for e in es])
        env = np.array([e["env"] for e in es])
        gd = np.array([e["gd"] for e in es], float)
        # half-peak decay in ms from the log-envelope decay slope gd (1/s): t_half = ln2 / -gd
        dec = np.where(gd < -1e-9, np.log(2.0) / (-gd) * 1e3, np.nan)
        engh = G[tag]["eng"].sum() / FS / 3600.0
        pr("  %-10s %6d | %8.2fs %8.2fHz %9.1f | %8.0fms %8.0fms | %8.1f" % (
            tag, len(es), np.median(dur), np.median(f0), np.median(env),
            np.nanmedian(dec), np.nanpercentile(dec, 90), len(es) / max(engh, 1e-9)))
    pr("")
    pr("  hands-off creep episodes only (|bar| median < 400 and 1 <= v < 3 m/s over the episode):")
    pr("  %-10s %6s | %9s %9s | %9s" % ("route", "n_ep", "f0 p50", "env p50", "decay p50"))
    for tag in ALL:
        es = [e for e in ep_by[tag] if e["hands"] < 400 and 1.0 <= e["v"] < 3.0]
        if len(es) < 3:
            pr("  %-10s %6d  -- too few --" % (tag, len(es)))
            continue
        gd = np.array([e["gd"] for e in es], float)
        dec = np.where(gd < -1e-9, np.log(2.0) / (-gd) * 1e3, np.nan)
        pr("  %-10s %6d | %8.2fHz %9.1f | %8.0fms" % (
            tag, len(es), np.median([e["f0"] for e in es]), np.median([e["env"] for e in es]), np.nanmedian(dec)))
    pr("")
    pr("  episode CLASS split (BURST / SUSTAINED / RIDE-ALONG):")
    for tag in ALL:
        es = ep_by[tag]
        pr("  %-10s %3d / %3d / %3d   of %d" % (
            tag, sum(1 for e in es if e["cls"] == "BURST"), sum(1 for e in es if e["cls"] == "SUSTAINED"),
            sum(1 for e in es if e["cls"] == "RIDE-ALONG"), len(es)))

    # ---------------------------------------------------------------- 5. (d)(e)(f) the spectrum
    pr("")
    pr("=" * 150)
    pr("4.  (d)(e)(f) THE WHOLE SPECTRUM, 3-45 Hz -- pooled Welch on the 0x18F rate, per stratum,")
    pr("    reported as EXCESS dB over a running-median baseline (+-2 Hz).  This is the two-line census'")
    pr("    instrument: a LINE shows as a positive excess, a broadband shoulder does not.")
    pr("=" * 150)
    SP = [("engaged, hands-off creep 1-3 m/s", lambda g: g["eng"] & (np.abs(g["bar"]) < 400) & (g["vego"] >= 1) & (g["vego"] < 3)),
          ("engaged, hands-off 3-8 m/s", lambda g: g["eng"] & (np.abs(g["bar"]) < 400) & (g["vego"] >= 3) & (g["vego"] < 8)),
          ("engaged, hands-off >=15 m/s", lambda g: g["eng"] & (np.abs(g["bar"]) < 400) & (g["vego"] >= 15)),
          ("engaged, ALL", lambda g: g["eng"]),
          ("DISENGAGED (loop open), ALL", lambda g: ~g["eng"])]
    BANDS = [("5-9", 5, 9), ("9-13", 9, 13), ("13-17", 13, 17), ("17-19", 17, 19),
             ("19-22", 19, 22), ("22-26", 22, 26), ("26-30", 26, 30)]
    spec = {}
    for lab, fn in SP:
        pr("")
        pr("  --- %s ---" % lab)
        pr("  %-10s %6s | %s" % ("route", "n_seg", " | ".join("%-14s" % ("%s Hz" % b[0]) for b in BANDS)))
        pr("  %-10s %6s | %s" % ("", "", " | ".join("%6s %7s" % ("fpk", "exc dB") for _ in BANDS)))
        for tag in ALL:
            g = G[tag]
            f, P, n = psd_of(g, fn(g), "wire", nperseg=512)
            if P is None or n < 6:
                pr("  %-10s %6d  -- too few segments --" % (tag, n))
                continue
            Pm = P.mean(0)
            spec[(lab, tag)] = (f, Pm, n, P)
            cells_ = []
            for _, lo_, hi_ in BANDS:
                fpk, exc = line_in(f, Pm, lo_, hi_)
                cells_.append("%6.2f %+6.2f" % (fpk, exc))
            pr("  %-10s %6d | %s" % (tag, n, " | ".join(cells_)))
        # band POWER ratios vs r6c, same stratum (this is the shoulder test)
        if (lab, "r6c") in spec:
            f6, P6m, n6, P6 = spec[(lab, "r6c")]
            pr("  band POWER ratio vs r6c (amplitude ratio = sqrt), segment bootstrap 95%% CI on the ratio of means:")
            for tag in V292_ROUTES:
                if (lab, tag) not in spec:
                    continue
                f_, Pm_, n_, P_ = spec[(lab, tag)]
                row = []
                for nm, lo_, hi_ in BANDS:
                    sl = (f_ >= lo_) & (f_ <= hi_)
                    a = P_[:, sl].mean(1); b = P6[:, sl].mean(1)
                    rr = np.array([a[rng.integers(0, len(a), len(a))].mean() / b[rng.integers(0, len(b), len(b))].mean()
                                   for _ in range(1500)])
                    row.append("%s %.2f [%.2f,%.2f]" % (nm, np.sqrt(a.mean() / b.mean()),
                                                        np.sqrt(np.percentile(rr, 2.5)), np.sqrt(np.percentile(rr, 97.5))))
                pr("     %-10s %s" % (tag, "  ".join(row)))

    # ---------------------------------------------------------------- 6. (f) fine line location
    pr("")
    pr("=" * 150)
    pr("5.  (f) DID THE 18-22 Hz OBJECT MOVE?  Fine line location (64k FFT) on pooled engaged hands-off")
    pr("    windows, searched over 10-30 Hz, plus the per-window line histogram from the census.")
    pr("=" * 150)
    pr("  %-10s | %-42s | %s" % ("route", "pooled fine line, 10-30 Hz", "per-window f0 (present windows)"))
    pr("  %-10s | %8s %8s %8s %8s | %7s %7s %7s %7s" %
       ("", "f0", "exc dB", "f0 12-17", "exc", "p10", "p50", "p90", "n"))
    for tag in ALL:
        g = G[tag]
        m = g["eng"] & (np.abs(g["bar"]) < 400)
        f, P, n = psd_of(g, m, "wire", nperseg=4096)
        if P is None or n < 4:
            pr("  %-10s | too few segments" % tag)
            continue
        Pm = P.mean(0)
        f1, e1 = line_in(f, Pm, 17.0, 24.0, half=2.0)
        f2, e2 = line_in(f, Pm, 11.0, 17.0, half=2.0)
        sel = (R["tag"] == tag) & pres
        ff = R["f0"][sel]
        pr("  %-10s | %8.3f %+8.2f %8.3f %+8.2f | %7.2f %7.2f %7.2f %7d" % (
            tag, f1, e1, f2, e2,
            np.percentile(ff, 10) if len(ff) else np.nan, np.median(ff) if len(ff) else np.nan,
            np.percentile(ff, 90) if len(ff) else np.nan, len(ff)))

    # ---------------------------------------------------------------- 7. (c) b3 duty vs ring amplitude
    pr("")
    pr("=" * 150)
    pr("6.  (c) b3 DUTY vs RING AMPLITUDE -- per census window, engaged.")
    pr("=" * 150)
    pr("  %-10s | %s" % ("route", " | ".join("%-13s" % ("ramp %s" % q) for q in
                                             ("<p20", "p20-40", "p40-60", "p60-80", ">p80"))))
    for tag in ALL:
        g = G[tag]
        sel = np.flatnonzero(R["tag"] == tag)
        if len(sel) < 50:
            continue
        # b3 duty inside each window
        b3 = g["bit3"]
        tw = R["t"][sel]
        idx = np.searchsorted(g["tr"], tw)
        W = int(C88.W) if hasattr(C88, "W") else 300
        duty = np.array([b3[max(0, i):i + W].mean() if i + 10 < len(b3) else np.nan for i in idx])
        ra = R["ramp"][sel]
        qs = np.percentile(ra, [20, 40, 60, 80])
        cellsx = []
        for a_, b_ in zip([-1e9] + list(qs), list(qs) + [1e9]):
            m = (ra >= a_) & (ra < b_) & np.isfinite(duty)
            cellsx.append("%.3f n%-6d" % (np.nanmean(duty[m]), m.sum()) if m.sum() > 20 else "  --       ")
        pr("  %-10s | %s" % (tag, " | ".join(cellsx)))

    with open(os.path.join(SCR, "v292_flight_census.json"), "w") as fh:
        json.dump(dict(tab={k: dict(n=v["n"], npres=v["npres"],
                                    ramp_p50=float(np.median(v["ramp"])) if len(v["ramp"]) else None)
                            for k, v in tab.items()}), fh, indent=1)
    io.open(os.path.join(SCR, "v292_flight_census.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("\nwrote v292_flight_census.txt")


if __name__ == "__main__":
    main()
