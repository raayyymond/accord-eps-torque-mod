#!/usr/bin/env python3
r"""studies/v103-r9e/v103_r9e_final.py -- the four things the first four scripts left open.

1  b3's RUN-LENGTH vs a BERNOULLI-PER-FRAME NULL.  `studies/v103-r9e/v103_r9e_b3.py` found NO spectral line and an
   UNSTABLE split-half everywhere, so the cave script's "peak 24.3 Hz x2.86" is WITHDRAWN -- it had
   no null behind it.  The right question is now: does b3 carry ANY temporal structure at 100 Hz,
   or is it a coin flip per frame?
2  b3's 20-28 Hz BAND SHARE, engaged vs manual, WITH a bootstrap CI over episodes.
3  b7's sign-vs-command agreement on ROUTE 96 (V102) under the SAME conditioning -- to decide
   whether the 0.76 on route 9e is a BUILD difference or a METHOD difference against V98's 52.80 %.
4  COMMAND RAIL DUTY BY REGIME -- the decision input for "would a wider accepted range buy anything?"
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))

import v103_r9e_lib as V          # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RNG = np.random.default_rng(6103)
NW = 512
RAIL = 4096.0
OUT = {}


def hdr(s):
    print("\n" + "=" * 108)
    print(s)
    print("=" * 108)


def main():
    z = V.load("9e")
    M = V.masks(z)
    t = np.asarray(z["t"], float)
    fs = 1.0 / float(np.median(np.diff(t)))
    eng, press = M["eng"], M["press"]
    v, rate = M["v"], M["rate"]
    b3 = np.asarray(z["v103_b3"], float) > 0.5

    # ---------------------------------------------------------------- 1 RUN LENGTHS vs BERNOULLI
    hdr("1 -- IS b3 ANYTHING MORE THAN A COIN FLIP PER FRAME?  If its run lengths are geometric,\n"
        "     the rung is UNDER-SAMPLED at 100 Hz and carries no resolvable temporal structure.\n"
        "     🛑 The cave script's 'peak 24.3 Hz x2.86' is WITHDRAWN: it had no null behind it,\n"
        "        and with a proper chi²₂ null the split-half is UNSTABLE on every arm.")
    for nm, m in (("ALL", np.ones(len(t), bool)), ("ENGAGED", eng), ("MANUAL", ~eng),
                  ("ENG hands-off 29-86", eng & (~press) & (v >= 8.0) & (v < 24.0))):
        x = b3[m].astype(int)
        ch = np.where(np.diff(x) != 0)[0]
        rl = np.diff(np.concatenate(([0], ch + 1, [len(x)])))
        p_stay = 1.0 - len(ch) / max(len(x) - 1, 1)
        obs = np.array([np.mean(rl == k) for k in range(1, 9)])
        geo = np.array([(p_stay ** (k - 1)) * (1 - p_stay) for k in range(1, 9)])
        chi = float(np.sum((obs - geo) ** 2 / np.maximum(geo, 1e-9)) * len(rl))
        print("\n  %-22s n=%6d frames  duty %.4f  P(stay)=%.4f  mean run %.2f frames"
              % (nm, len(x), x.mean(), p_stay, rl.mean()))
        print("      run len k          " + " ".join("%7d" % k for k in range(1, 9)))
        print("      OBSERVED           " + " ".join("%7.3f" % o for o in obs))
        print("      GEOMETRIC null     " + " ".join("%7.3f" % g for g in geo))
        print("      => %s  (scaled chi2 = %.0f over 8 cells)"
              % ("INDISTINGUISHABLE from a per-frame coin flip -- the rung is UNDER-SAMPLED"
                 if chi < 60 else "STRUCTURED -- departs from geometric", chi))
        OUT.setdefault("runlength", {})[nm] = dict(n=int(len(x)), duty=float(x.mean()),
                                                   p_stay=float(p_stay),
                                                   mean_run=float(rl.mean()),
                                                   obs=[float(o) for o in obs],
                                                   geo=[float(g) for g in geo], chi2=chi)

    # ---------------------------------------------------------------- 2 BAND SHARE + CI
    hdr("2 -- b3's 20-28 Hz SIGN-POWER SHARE, engaged hands-off vs manual, BOOTSTRAPPED OVER\n"
        "     EPISODES.  Share, not absolute power -- a sign sequence has no amplitude.")
    s3 = np.where(b3, -1.0, 1.0)
    f = np.fft.rfftfreq(NW, 1.0 / fs)
    sel = (f >= 1.0) & (f <= 45.0)
    tgt = (f >= 20.0) & (f <= 28.0)

    def shares(mask):
        G = []
        for a, b in V.episodes(mask, t, NW):
            ep = []
            for i in range(0, (b - a) - NW + 1, NW // 2):
                w = slice(a + i, a + i + NW)
                x = s3[w]
                S = np.abs(np.fft.rfft((x - x.mean()) * np.hanning(NW))) ** 2
                ep.append(S)
            if ep:
                G.append(ep)
        return G

    def share_of(G):
        allS = np.array([s for ep in G for s in ep])
        if not len(allS):
            return np.nan
        a = allS.mean(axis=0)
        return float(a[tgt].sum() / a[sel].sum())

    res = {}
    for nm, m in (("ENG hands-off 29-86", eng & (~press) & (v >= 8.0) & (v < 24.0)),
                  ("ENG all moving", eng & (v > 0.5)),
                  ("MANUAL moving", (~eng) & (v > 0.5)),
                  ("STANDSTILL", v <= 0.5)):
        G = shares(m)
        if not G:
            continue
        pt = share_of(G)
        bs = []
        for _ in range(600):
            idx = RNG.integers(0, len(G), len(G))
            bs.append(share_of([G[k] for k in idx]))
        lo, hi = V.ci(bs)
        n = sum(len(ep) for ep in G)
        res[nm] = dict(share=pt, lo=lo, hi=hi, n_win=n, n_ep=len(G))
        print("  %-22s n=%3d win / %2d ep   20-28 Hz share %.4f  [%.4f, %.4f]"
              % (nm, n, len(G), pt, lo, hi))
    if "ENG all moving" in res and "MANUAL moving" in res:
        a, b = res["ENG all moving"], res["MANUAL moving"]
        print("  ==> ENGAGED / MANUAL share ratio = %.3f   CIs %s"
              % (a["share"] / b["share"],
                 "DISJOINT" if (a["lo"] > b["hi"] or b["lo"] > a["hi"]) else "OVERLAP"))
        print("      A flat/white sign sequence puts %.3f of its 1-45 Hz power in 20-28 Hz by\n"
              "      bandwidth alone -- that is the number to beat." % (8.0 / 44.0))
    OUT["b3_band_share"] = res

    # ---------------------------------------------------------------- 3 b7 ON V102's OWN ROUTE
    hdr("3 -- b7 SIGN-vs-COMMAND on ROUTE 96 (V102) under the IDENTICAL conditioning.\n"
        "     V103 gave 0.76-0.66; the record (`accord-gp6b4c-is-an-11-slot-assist-sum`, from V98\n"
        "     on route 0x81) says 52.80 % == CHANCE.  This decides BUILD vs METHOD.")
    print("      %-8s %-14s %8s %11s" % ("route", "|0x0E4| floor", "n", "agreement"))
    for rt, lab in (("96", "V102"), ("9e", "V103")):
        zz = V.load(rt)
        MM = V.masks(zz)
        e4 = np.asarray(zz["e4tq"], float)
        x6 = np.asarray(zz["x6b4c"], float)
        W = MM["eng"] & (MM["v"] > 0.5)
        for flo in (0, 100, 400, 1600):
            m = W & (np.abs(e4) > flo) & (np.abs(x6) > 0)
            if m.sum() < 200:
                continue
            a = float(np.mean(np.sign(x6[m]) == np.sign(e4[m])))
            print("      %-8s %-14s %8d %11.4f" % (lab, ">%d" % flo, m.sum(), a))
            OUT.setdefault("b7_sign_agreement", {}).setdefault(lab, {})[str(flo)] = \
                dict(n=int(m.sum()), agree=a)
    print("      => if V102 and V103 AGREE, the 52.80 %% figure is a METHOD/CONDITIONING\n"
          "         difference against V98, not a change in the firmware.  Reported, not retracted.")

    # ---------------------------------------------------------------- 4 RAIL DUTY BY REGIME
    hdr("4 -- COMMAND RAIL DUTY BY REGIME.  Decides whether widening openpilot's accepted range\n"
        "     would buy finer control, or whether the command already lives far from the rail.")
    e4 = np.abs(np.asarray(z["e4tq"], float))
    REG = [("ENGAGED all", eng),
           ("ENG <30 km/h  (grind #1)", eng & (v > 0.5) & (v < 8.33)),
           ("ENG 30-60 km/h", eng & (v >= 8.33) & (v < 16.67)),
           ("ENG 60-85 km/h", eng & (v >= 16.67) & (v < 23.6)),
           ("ENG >85 km/h", eng & (v >= 23.6)),
           ("ENG rate >=13 (ratchet)", eng & (rate >= 13)),
           ("ENG rate <1 (straight)", eng & (rate < 1)),
           ("ENG hands-off 29-86", eng & (~press) & (v >= 8.0) & (v < 24.0)),
           ("ENG hands-ON", eng & press)]
    print("      %-26s %8s %8s %8s %8s %9s %9s %9s"
          % ("regime", "sec", "p50", "p90", "p99", "@rail%", ">=90%", ">=50%"))
    for nm, m in REG:
        if m.sum() < 200:
            continue
        a = e4[m]
        row = dict(sec=float(m.sum() * 0.01), p50=float(np.percentile(a, 50)),
                   p90=float(np.percentile(a, 90)), p99=float(np.percentile(a, 99)),
                   rail=float(np.mean(a >= RAIL)), r90=float(np.mean(a >= 0.9 * RAIL)),
                   r50=float(np.mean(a >= 0.5 * RAIL)))
        OUT.setdefault("rail_by_regime", {})[nm] = row
        print("      %-26s %8.1f %8.0f %8.0f %8.0f %9.3f %9.3f %9.3f"
              % (nm, row["sec"], row["p50"], row["p90"], row["p99"],
                 100 * row["rail"], 100 * row["r90"], 100 * row["r50"]))
    # how long are the rail EXCURSIONS?
    at = eng & (e4 >= RAIL)
    w = np.where(at)[0]
    if len(w):
        runs = np.split(w, np.where(np.diff(w) != 1)[0] + 1)
        L = np.array([len(r) * 0.01 for r in runs])
        print("\n      rail EXCURSIONS while engaged: %d runs   total %.1f s   duration p50 %.2f s "
              " p90 %.2f s  max %.2f s" % (len(runs), L.sum(), np.percentile(L, 50),
                                           np.percentile(L, 90), L.max()))
        print("      longest excursions at t = " + "  ".join(
            "%.0f s (%.1f s)" % (t[r[0]], len(r) * 0.01)
            for r in sorted(runs, key=len, reverse=True)[:8]))
        OUT["rail_excursions"] = dict(n=len(runs), total_s=float(L.sum()),
                                      p50=float(np.percentile(L, 50)),
                                      p90=float(np.percentile(L, 90)), max=float(L.max()))
    # quantisation, restated as the decision
    u = np.unique(np.asarray(z["e4tq"], float)[eng])
    d = np.diff(np.sort(u))
    d = d[d > 0]
    print("\n      QUANTISATION: %d distinct codes, adjacent-code gap min %.0f / p50 %.0f LSB.\n"
          "      1 LSB of 0x0E4 = 1/4096 of full scale; at the 6x forward gain (0xC6CD0=5346)\n"
          "      one LSB is %.4f counts of assist (4*gain/32768 = %.4f ct/LSB)."
          % (len(u), d.min(), np.median(d), 4 * 5346 / 32768.0, 4 * 5346 / 32768.0))
    OUT["quantisation"] = dict(distinct=int(len(u)), gap_min=float(d.min()),
                               gap_p50=float(np.median(d)),
                               ct_per_lsb=float(4 * 5346 / 32768.0))

    Path(HERE / "_scratch/out/_v103_r9e_final.json").write_text(json.dumps(OUT, indent=1, default=float))
    print("\n  wrote _scratch/out/_v103_r9e_final.json")


if __name__ == "__main__":
    main()
