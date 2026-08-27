#!/usr/bin/env python3
r"""score/score_v102_matched.py -- the three things `score/score_v102_full.py` left open.

  A. MATCHED-SPEED V102/V101 and V102/STOCK on the primary, episode-bootstrapped.  r95 (V101)
     carries NO engaged window above 68 km/h while r96 (V102) puts 39 % of its windows above
     80 km/h, and the shape statistic RISES with speed on every build -- so the unmatched ratio
     is not the endpoint.
  B. THE WHEEL-ORDER TEST on V102's huge ~24.6 Hz highway line (prominence 57).  A tyre line
     moves as 0.489*v Hz per order.  If f0 is flat across a speed sweep it is not a wheel order.
  C. STOCK vs V102 AT MATCHED SPEED as the cleanest available contrast: 49 stock windows at
     v p50 94.8 km/h against 38 V102 windows at v p50 100.0 km/h.

  D. STEER_STATUS 3 on r97 -- 35,291 frames.  Is the stock ECU in a limited state, which would
     change what the stock arm means?
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
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import v102_xb_lib as L  # noqa: E402
import score_v102_full as F  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ARMS = F.ARMS


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104)


def matched_ratio(TA, TB, c="tq", tgt="B23", ctl="CTRL",
                  vedges=(5, 20, 35, 50, 65), nboot=4000, seed=11, unit="epi"):
    """min(n)-weighted mean of per-SPEED-CELL log ratios of medians; both arms group-resampled."""
    rng = np.random.default_rng(seed)
    sA = F.shape(TA, c, tgt, ctl)
    sB = F.shape(TB, c, tgt, ctl)
    gA = TA["epi"] if unit == "epi" else TA["epi"] * 1e6 + np.floor(TA["t0"] / 15.0)
    gB = TB["epi"] if unit == "epi" else TB["epi"] * 1e6 + np.floor(TB["t0"] / 15.0)
    cells = []
    census = []
    for lo, hi in zip(vedges[:-1], vedges[1:]):
        ma = (TA["v"] >= lo) & (TA["v"] < hi)
        mb = (TB["v"] >= lo) & (TB["v"] < hi)
        if ma.sum() >= 8 and mb.sum() >= 8:
            cells.append((sA[ma], gA[ma], sB[mb], gB[mb]))
            census.append((lo, hi, int(ma.sum()), int(mb.sum())))
    if not cells:
        return None, []

    def stat(draw):
        num = den = 0.0
        for (a, ga, b, gb) in draw:
            w = min(len(a), len(b))
            num += w * np.log(np.median(b) / np.median(a))
            den += w
        return float(np.exp(num / den)) if den else np.nan

    pt = stat(cells)
    bs = []
    for _ in range(nboot):
        draw = []
        for (a, ga, b, gb) in cells:
            ka, kb = np.unique(ga), np.unique(gb)
            ia = np.concatenate([np.nonzero(ga == ka[j])[0]
                                 for j in rng.integers(0, len(ka), len(ka))])
            ib = np.concatenate([np.nonzero(gb == kb[j])[0]
                                 for j in rng.integers(0, len(kb), len(kb))])
            draw.append((a[ia], None, b[ib], None))
        v = stat(draw)
        if np.isfinite(v):
            bs.append(v)
    lo95, hi95 = np.percentile(bs, [2.5, 97.5])
    return dict(r=pt, lo=float(lo95), hi=float(hi95), cells=len(cells)), census


if __name__ == "__main__":
    TAB = {r: F.build_table(r) for r, _, _, _ in ARMS}

    # ---------------------------------------------------------------- A
    hdr("A -- 🛑 MATCHED-SPEED PRIMARY.  tq shape B23/CTRL, per-speed-cell, episode bootstrap.\n"
        "     Overlap with V101 is 5-65 km/h ONLY (r95 has zero engaged windows above 68 km/h).")
    for c in ("tq", "rate_f", "cs_ang"):
        for tgt, ctl in (("B23", "CTRL"), ("B23", "HI")):
            print("\n    %s  %s/%s   -- vs V101 (5-65 km/h overlap)" % (c, tgt, ctl))
            for r, lab, gl, _g in ARMS:
                if r == "95":
                    continue
                d, cen = matched_ratio(TAB["95"], TAB[r], c, tgt, ctl)
                de, _ = matched_ratio(TAB["95"], TAB[r], c, tgt, ctl, unit="blk", seed=13)
                if d is None:
                    print("        %-11s %-4s  NO MATCHED CELLS" % (lab, gl))
                    continue
                print("        %-11s %-4s = %6.3f  EPISODE [%5.3f,%6.3f]  BLOCK [%5.3f,%6.3f]  "
                      "cells=%d  %s" % (lab, gl, d["r"], d["lo"], d["hi"], de["lo"], de["hi"],
                                        d["cells"],
                                        " ".join("%d-%d:%d/%d" % x for x in cen)))
    print("\n    -- vs STOCK, FULL speed range 5-115 km/h (both arms have highway) --")
    VE = (5, 20, 35, 50, 65, 80, 95, 115)
    for c in ("tq", "rate_f", "cs_ang"):
        for tgt, ctl in (("B23", "CTRL"), ("B23", "HI"), ("B8", "CTRL")):
            d, cen = matched_ratio(TAB["97"], TAB["96"], c, tgt, ctl, vedges=VE)
            db, _ = matched_ratio(TAB["97"], TAB["96"], c, tgt, ctl, vedges=VE, unit="blk", seed=13)
            if d is None:
                continue
            print("        %-7s %-9s V102/STOCK = %7.3f  EPISODE [%6.3f,%7.3f]  BLOCK "
                  "[%6.3f,%7.3f]  cells=%d" % (c, tgt + "/" + ctl, d["r"], d["lo"], d["hi"],
                                               db["lo"], db["hi"], d["cells"]))
        print("            census: " + " ".join("%d-%d:%d/%d" % x for x in cen))
    print("\n    -- V100 (4x) vs STOCK (1x), same estimator, as a scale reference --")
    for c in ("tq",):
        for tgt, ctl in (("B23", "CTRL"), ("B23", "HI")):
            d, cen = matched_ratio(TAB["97"], TAB["85"], c, tgt, ctl, vedges=VE)
            if d:
                print("        %-7s %-9s V100/STOCK = %7.3f  EPISODE [%6.3f,%7.3f]  cells=%d  %s"
                      % (c, tgt + "/" + ctl, d["r"], d["lo"], d["hi"], d["cells"],
                         " ".join("%d-%d:%d/%d" % x for x in cen)))

    # ---------------------------------------------------------------- B
    hdr("B -- 🛑 IS V102's ~24.6 Hz HIGHWAY LINE A WHEEL ORDER?  Sweep speed; a tyre line moves\n"
        "     as 0.489*v Hz per order (order 1 at 100 km/h = 13.6 Hz, order 2 = 27.2 Hz).")
    NF = 1024
    win = np.hanning(NF)
    f = L.psd(np.zeros(NF), L.FS, win)[0]
    SW = ((50, 65), (65, 80), (80, 95), (95, 105), (105, 115))
    for r, lab, gl, _g in ARMS:
        print("\n    %s (%s)" % (lab, gl))
        for vlo, vhi in SW:
            P, vs = [], []
            for b in L.all_blocks(r):
                vv = b["v_rear"] * 3.6
                m = (b["cc_lat"] > 0.5) & (vv >= vlo) & (vv < vhi)
                i = 0
                while i + NF <= len(m):
                    if m[i:i + NF].mean() >= 0.98:
                        P.append(L.psd(b["tq"][i:i + NF], L.FS, win)[1])
                        vs.append(float(np.median(vv[i:i + NF])))
                    i += NF // 2
            if len(P) < 4:
                print("      %3d-%3d km/h   %2d win -- too thin" % (vlo, vhi, len(P)))
                continue
            pm = np.median(np.asarray(P), axis=0)
            bnd = (f >= 15) & (f <= 32)
            k = int(np.argmax(pm[bnd]))
            base = np.median(pm[bnd])
            vm = float(np.median(vs))
            print("      %3d-%3d km/h   %2d win  v p50 %5.1f   f0 = %5.2f Hz  prom %6.2f   "
                  "wheel order 1 = %5.2f Hz, order 2 = %5.2f Hz"
                  % (vlo, vhi, len(P), vm, f[bnd][k], pm[bnd][k] / base,
                     0.489 * vm / 3.6, 2 * 0.489 * vm / 3.6))

    # ---------------------------------------------------------------- D
    hdr("D -- r97 STEER_STATUS.  35,291 frames read 3.  Is the STOCK ECU in a limited state?")
    for r, lab, _gl, _g in (("97", "V9b STOCK", 0, 0), ("96", "V102", 0, 0)):
        acc = {}
        for s in L.ROUTES[r]["segs"]:
            d = L.load_seg(r, s)
            for k in ("sstat", "cc_lat", "v_rear", "e4tq", "cs_tq"):
                if k in d:
                    acc.setdefault(k, []).append(d[k])
        d = {k: np.concatenate(v) for k, v in acc.items()}
        st = np.asarray(d["sstat"], int)
        eng = d["cc_lat"] > 0.5
        v = d["v_rear"] * 3.6
        u, cnt = np.unique(st, return_counts=True)
        print("\n    r%s (%s)  STEER_STATUS hist %s" % (r, lab,
                                                        {int(a): int(b) for a, b in zip(u, cnt)}))
        for val in u:
            m = st == val
            print("       status %d: n=%-7d  engaged frac %.4f   v p50 %6.1f  p90 %6.1f  "
                  "|e4 cmd| p50 %6.0f" % (val, m.sum(), float(eng[m].mean()),
                                          float(np.percentile(v[m], 50)),
                                          float(np.percentile(v[m], 90)),
                                          float(np.percentile(np.abs(d["e4tq"][m]), 50))))
        m3 = (st == 3) & eng
        print("       ENGAGED-AND-status3: %d frames (%.1f s, %.4f of engaged)"
              % (m3.sum(), m3.sum() / 100.0, m3.sum() / max(eng.sum(), 1)))
