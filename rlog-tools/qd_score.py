#!/usr/bin/env python3
"""DID `0xC40D4` CHANGE THE DAMPING OF THE ~8 Hz LINE?  V86 (6f) vs V86B (70) vs V85 (6e).

V86B carries 0xC40D4 = 573 = STOCK, identical to V85, so
    V86 vs V86B  = the SINGLE-VARIABLE contrast on the cell   (headline)
    V86B vs V85  = the SAME-ALPHA pair = the route-to-route noise floor
and the verdict is the difference-in-differences, not the raw ratio.

WHAT IS MEASURED, AND THE TENSION THAT HAD TO BE RESOLVED
  Linewidth Q needs a LONG window; the resampling unit is a ~10.1 s `blk`.  Worse, the three routes
  do not offer the same longest engaged run (V86 139.8 s, V85 304.0 s, V86B only 36.4 s), and the
  window-limited Q floor is f0.T/1.4416 -- so an unmatched-length comparison returns the ratio of
  the RUN LENGTHS, not of the damping.  Resolution:
    * every linewidth statistic is computed on windows of IDENTICAL length T, swept over
      T = 10.1 / 20.3 / 30.4 s, so the instrument floor is the same number in every arm;
    * each window is tagged with the ~10.1 s blk it starts in and the bootstrap resamples blk;
    * the long-run numbers are reported SEPARATELY as bounds, explicitly not comparable.

  Additionally a set of ENVELOPE observables is scored.  These are the physically correct damping
  readout for a self-sustained cycle -- linewidth measures phase coherence, the envelope measures
  the amplitude-relaxation rate, i.e. the stability margin -- and they are NOT window-limited.

Usage:  python qd_score.py
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import qd_lib as Q                                                      # noqa: E402

import qd_win as W                                                     # noqa: E402
from qd_win import (ROUTES, ALPHA, VBINS, VLO, VHI, CIRC, SIG,          # noqa: E402
                    load, windows, order_clean, score, shared_weights)

TS = [(1024, "10.1 s"), (2048, "20.3 s"), (3072, "30.4 s")]
RNG = np.random.default_rng(8640214)
OUT = {}


def hdr(s):
    print("\n" + "=" * 112 + "\n" + s + "\n" + "=" * 112, flush=True)


# ===========================================================================================
hdr("SS0  THE INSTRUMENT FLOOR IS THE WHOLE BALLGAME -- longest engaged run per route")
runinfo = {}
for b, r in ROUTES.items():
    d = load(r)
    fs = d["fs"]
    lat = np.asarray(d["cc_lat"], float) > 0.5
    sm = lat & (d["cs_v"] >= VLO) & (d["cs_v"] < VHI)
    ra = Q.contiguous_runs(lat, d["t"], int(5 * fs))
    rb = Q.contiguous_runs(sm, d["t"], int(5 * fs))
    la = sorted([(y - x) / fs for x, y in ra], reverse=True)
    lb = sorted([(y - x) / fs for x, y in rb], reverse=True)
    runinfo[b] = dict(eng_s=float(lat.sum() / fs), matched_s=float(sm.sum() / fs),
                      runs_eng=[round(z, 1) for z in la], runs_matched=[round(z, 1) for z in lb],
                      qmax_longest_eng=float(7.79 * la[0] / Q.HANN_FWHM) if la else np.nan,
                      qmax_longest_matched=float(7.79 * lb[0] / Q.HANN_FWHM) if lb else np.nan)
    print(f"  {b:5s} ({r})  alpha(0xC40D4)={ALPHA[b]:4d}   engaged {lat.sum()/fs:6.1f} s   "
          f"speed-matched {sm.sum()/fs:6.1f} s")
    print(f"          engaged runs      {[round(z,1) for z in la[:6]]}   longest -> "
          f"window-limited Q floor {runinfo[b]['qmax_longest_eng']:7.1f}")
    print(f"          +speed-matched    {[round(z,1) for z in lb[:6]]}   longest -> "
          f"window-limited Q floor {runinfo[b]['qmax_longest_matched']:7.1f}")
print("\n  => the three arms CANNOT be compared at their own longest runs: the Q floors differ by"
      "\n     4x, so a ratio of run-limited Qs is a ratio of RUN LENGTHS.  Matched T below.")
OUT["runs"] = runinfo

# ===========================================================================================
hdr("SS1  LONG-RUN LINEWIDTH -- for the record, and to show WHERE the resolution floor bites")
longrun = {}
for b, r in ROUTES.items():
    d = load(r)
    fs = d["fs"]
    lat = np.asarray(d["cc_lat"], float) > 0.5
    x = np.asarray(d[SIG], float)
    rows = []
    for tag, mask in (("engaged", lat),
                      ("engaged+v-matched", lat & (d["cs_v"] >= VLO) & (d["cs_v"] < VHI))):
        rr = sorted(Q.contiguous_runs(mask, d["t"], int(15 * fs)),
                    key=lambda ab: ab[0] - ab[1])[:3]
        for a, bb in rr:
            L = Q.linewidth(x[a:bb], fs)
            excess = L["fwhm"] - L["wl"] if np.isfinite(L["fwhm"]) else np.nan
            rows.append(dict(kind=tag, T=L["T"], f0=L["f0"], fwhm=L["fwhm"], wl=L["wl"],
                             q_app=L["q_app"], q_max=L["q_max"], prom=L["prom"],
                             q_excess=float(L["f0"] / excess) if (np.isfinite(excess)
                                                                  and excess > 0) else np.inf,
                             ratio_fwhm_wl=float(L["fwhm"] / L["wl"])
                             if np.isfinite(L["fwhm"]) else np.nan))
            print(f"  {b:5s} {tag:18s} T={L['T']:6.1f}s  f0={L['f0']:.4f}  "
                  f"FWHM={L['fwhm']:.4f}  window limit={L['wl']:.4f}  "
                  f"FWHM/limit={rows[-1]['ratio_fwhm_wl']:5.2f}  "
                  f"Q_app={L['q_app']:8.1f} (floor {L['q_max']:7.1f})  "
                  f"Q_excess-width={rows[-1]['q_excess']:10.1f}  prom={L['prom']:6.1f}x")
    longrun[b] = rows
OUT["longrun"] = longrun
print("\n  FWHM/limit ~ 1.0  =>  RESOLUTION-LIMITED: Q_app is a LOWER BOUND, Q_excess-width is the"
      "\n  reciprocal of a difference of two near-equal numbers and is not a measurement.")

# ===========================================================================================
hdr("SS2  MATCHED-T LINEWIDTH + ENVELOPE OBSERVABLES  (engaged, speed-matched, order-clean)")
ALL = {}
for nw, tlab in TS:
    arms, drops = {}, {}
    for b in ROUTES:
        raw = score(windows(b, nw))
        rs = order_clean(raw)
        drops[b] = (len(raw), len(rs))
        arms[b] = rs
    w, counts = shared_weights([arms[b] for b in ("V86", "V86B", "V85")])
    print(f"\n  --- T = {tlab}  (nw={nw})   window-limited Q floor = "
          f"{7.79 * nw / (Q.HANN_FWHM * 101.1):.1f}")
    print(f"      windows kept / cut: " + "  ".join(
        f"{b} {drops[b][1]}/{drops[b][0]}" for b in ("V86", "V86B", "V85")) +
        "   (cut = wheel order within 0.8 Hz of the measured line)")
    print(f"      speed-bin window counts  V86 {counts[0]}  V86B {counts[1]}  V85 {counts[2]}"
          f"   shared weights {w.tolist()}")
    for b in ("V86", "V86B", "V85"):
        rs = arms[b]
        nblk = len({r["blk"] for r in rs})
        if not rs:
            print(f"      {b:5s}  NO WINDOWS")
            continue
        qa = Q.block_boot([r["q_app"] for r in rs], [r["blk"] for r in rs], rng=RNG)
        fw = Q.block_boot([r["fwhm"] for r in rs], [r["blk"] for r in rs], rng=RNG)
        f0 = Q.block_boot([r["f0"] for r in rs], [r["blk"] for r in rs], rng=RNG)
        pr = Q.block_boot([r["prom"] for r in rs], [r["blk"] for r in rs], rng=RNG)
        qf = np.nanmedian([r["q_frac"] for r in rs])
        print(f"      {b:5s} n={len(rs):3d} blk={nblk:3d}  f0={f0['pt']:6.3f}  "
              f"FWHM={fw['pt']:.4f} [{fw['lo']:.4f},{fw['hi']:.4f}]  "
              f"Q_app={qa['pt']:6.1f} [{qa['lo']:5.1f},{qa['hi']:6.1f}]  "
              f"Q_app/Q_floor={qf:.3f}  prom={pr['pt']:5.1f}x")
        arms[b + "_stats"] = dict(q_app=qa, fwhm=fw, f0=f0, prom=pr, q_frac=float(qf),
                                  n=len(rs), nblk=nblk)
    ALL[tlab] = dict(arms=arms, w=w.tolist(), counts=counts, nw=nw)

OUT["matched"] = {k: {b: v["arms"][b + "_stats"] for b in ("V86", "V86B", "V85")
                      if b + "_stats" in v["arms"]} | dict(w=v["w"], counts=v["counts"])
                  for k, v in ALL.items()}

# ===========================================================================================
hdr("SS3  THE SAME-ALPHA NOISE FLOOR FIRST  (V86B / V85, both 0xC40D4 = 573), THEN THE EFFECT")
KEYS = [("q_app", "linewidth Q"), ("fwhm", "linewidth FWHM"), ("f0", "line frequency"),
        ("tau_env", "envelope tau (margin)"), ("duty", "burst duty (1.5x med)"),
        ("duty20", "burst duty (2.0x med)"), ("burst_s", "burst duration"),
        ("cv", "envelope CV"), ("env_p99", "envelope p99 (ampl)")]
res = {}
for tlab, blob in ALL.items():
    arms, w = blob["arms"], np.array(blob["w"])
    print(f"\n  ############  T = {tlab}  ############")
    res[tlab] = {}
    for key, lab in KEYS:
        null = Q.boot_ratio(arms["V86B"], arms["V85"], key, rng=RNG, weights=w, vbins=VBINS)
        eff = Q.boot_ratio(arms["V86"], arms["V86B"], key, rng=RNG, weights=w, vbins=VBINS)
        dd = Q.did(arms["V86"], arms["V86B"], arms["V85"], key, rng=RNG, weights=w, vbins=VBINS)
        res[tlab][key] = dict(null=null, effect=eff, did=dd)
        print(f"   {lab:24s}  NULL V86B/V85 = {null['ratio']:6.3f} "
              f"[{null['lo']:6.3f},{null['hi']:6.3f}]  (blk {null['blkB']}/{null['blkA']})")
        print(f"   {'':24s}  EFF  V86/V86B = {eff['ratio']:6.3f} "
              f"[{eff['lo']:6.3f},{eff['hi']:6.3f}]  (blk {eff['blkA']}/{eff['blkB']})   "
              f"| DiD = {dd['did']:6.3f} [{dd['lo']:6.3f},{dd['hi']:6.3f}]")
OUT["contrasts"] = res


# ===========================================================================================
hdr("SS4  RECONCILING THE TWO LOWER BOUNDS: within-run Q vs the ENSEMBLE half-power Q")
rec = {}
for tlab, blob in ALL.items():
    print(f"\n  T = {tlab}")
    for b in ("V86", "V86B", "V85"):
        rs = blob["arms"][b]
        if len(rs) < 2:
            print(f"    {b:5s}  n={len(rs)} -- too few")
            continue
        f0 = np.array([r["f0"] for r in rs])
        qw = np.nanmedian([r["q_app"] for r in rs])
        spread = float(np.percentile(f0, 84) - np.percentile(f0, 16))
        fwhm_w = float(np.nanmedian([r["fwhm"] for r in rs]))
        # an ensemble spectrum is the within-window line SMEARED by the run-to-run f0 wander
        ens_fwhm = float(np.hypot(fwhm_w, 2.355 * np.std(f0)))
        rec.setdefault(tlab, {})[b] = dict(f0_med=float(np.median(f0)), f0_p16_84=spread,
                                           f0_std=float(np.std(f0)), q_within=float(qw),
                                           fwhm_within=fwhm_w, ens_fwhm=ens_fwhm,
                                           q_ensemble=float(np.median(f0) / ens_fwhm), n=len(rs))
        print(f"    {b:5s} n={len(rs):3d}  f0 med {np.median(f0):6.3f}  f0 spread(p16-84) "
              f"{spread:6.3f} Hz  sd {np.std(f0):.3f}")
        print(f"          within-window FWHM {fwhm_w:.4f} Hz -> Q_within {qw:6.1f}   |   "
              f"wander-smeared FWHM {ens_fwhm:.4f} Hz -> Q_ensemble {np.median(f0)/ens_fwhm:5.1f}")
print("\n  => the two published lower bounds are NOT in conflict: Q_ensemble is the SAME line seen"
      "\n     through the run-to-run f0 wander, which dominates the within-window width by ~5-10x.")
OUT["reconcile"] = rec

# ===========================================================================================
hdr("SS5  MANUAL CONTROL -- is there a line to measure at all when not engaged?")
man = {}
for b in ROUTES:
    rs = order_clean(score(windows(b, 1024, engaged=False)))
    en = order_clean(score(windows(b, 1024, engaged=True)))
    if not rs:
        print(f"  {b:5s}  no manual windows in the speed band")
        continue
    pm = np.median([r["prom"] for r in rs])
    pe = np.median([r["prom"] for r in en]) if en else np.nan
    am = np.median([r["env_p99"] for r in rs])
    ae = np.median([r["env_p99"] for r in en]) if en else np.nan
    qm = np.nanmedian([r["q_app"] for r in rs])
    qe = np.nanmedian([r["q_app"] for r in en]) if en else np.nan
    man[b] = dict(n_man=len(rs), n_eng=len(en), prom_man=float(pm), prom_eng=float(pe),
                  amp_man=float(am), amp_eng=float(ae), q_man=float(qm), q_eng=float(qe))
    print(f"  {b:5s} manual n={len(rs):3d} / engaged n={len(en):3d}   "
          f"prominence {pm:6.1f}x vs {pe:6.1f}x   envelope p99 {am:6.2f} vs {ae:6.2f} ct   "
          f"Q_app {qm:6.1f} vs {qe:6.1f}")
print("\n  Manual carries NO comparable line, so there is no within-route control arm; the control"
      "\n  used throughout is the CONTEMPORANEOUS same-alpha route pair V86B/V85 instead.")
OUT["manual"] = man

json.dump(OUT, open(ROOT / "_cache_r6f" / "q_damping_score.json", "w"), indent=1, default=float)
print("\nwrote _cache_r6f/q_damping_score.json")
