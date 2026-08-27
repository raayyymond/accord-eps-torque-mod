#!/usr/bin/env python3
"""The V62 trade: did it swap 21 Hz grinding for 7.4 Hz ratchet, and is that gated on effort?

Speed x effort grid, engaged, drive gear, disjoint NFFT=256 windows. Both bands reported in
PHYSICAL units (band RMS and envelope p99, torque counts) with prominence alongside, because on
this route the two disagree in sign: V62 has a HIGHER broadband floor at creep, so its prominence
ratio understates an amplitude that is actually the largest on record.

Speeds are capped at 11 m/s throughout -- wheel order 1 (0.489*v) enters the 6-9 Hz band at
12.3 m/s, so no ratchet number above ~11 m/s is usable.

Controls are the V59-family routes (2c and 35). V61 is shown where it has exposure but it only
ever ran at creep.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import _r31_common as C  # noqa: E402
import _r37_ratchet_lib as L  # noqa: E402

VCELLS = [(0.3, 2.5), (2.5, 6.0), (6.0, 11.0)]
ECELLS = [(0, 200), (200, 500), (500, 1000), (1000, 2000), (2000, 1e9)]


def eng(d):
    lat = d["cc_lat"] > 0.5
    g = (d["cs_gear"] == 2.0) if "cs_gear" in d else np.ones(len(d["t"]), bool)
    return lat & g & (d["cs_v"] > 0.3)


def main():
    store = {nm: L.collect(ca, pf, sg, mask_fn=eng) for nm, ca, pf, sg in L.ROUTES}
    V62, V59, V64 = store["37/V62"], store["2c/V59"], store["35/V64=V59"]
    CTRL = V59 + V64          # the V59-family control (V64 is spectrally identical to V59)

    def cell(rs, v, e):
        return [r for r in rs if v[0] <= r["v"] < v[1] and e[0] <= r["eff"] < e[1]]

    for vlo, vhi in VCELLS:
        print(f"\n{'='*138}\nSPEED {vlo}-{vhi} m/s  ({2.237*vlo:.0f}-{2.237*vhi:.0f} mph), "
              f"engaged, drive gear\n{'='*138}")
        print(f"  {'effort':>11s} | {'arm':>12s} {'nwin':>5s} {'nep':>4s} | "
              f"{'RATCHET 6-9 Hz':^38s} | {'GRINDING 18-26 Hz':^38s}")
        print(f"  {'':>11s} | {'':>12s} {'':>5s} {'':>4s} | "
              f"{'f0':>5s} {'RMS':>7s} {'env99':>8s} {'prom':>7s} {'pres':>6s} | "
              f"{'f0':>5s} {'RMS':>7s} {'env99':>8s} {'prom':>7s} {'pres':>6s}")
        for elo, ehi in ECELLS:
            rows = []
            for lbl, rs in (("V62", V62), ("V59-family", CTRL)):
                c = cell(rs, (vlo, vhi), (elo, ehi))
                if not c:
                    print(f"  {elo:5.0f}-{ehi if ehi < 1e8 else 9999:5.0f} | {lbl:>12s} "
                          f"{0:5d} {0:4d} | (none)")
                    rows.append(None)
                    continue
                g = lambda k: np.nanmedian([r[k] for r in c])  # noqa: E731
                pres_r = 100 * np.mean([r["pr"] >= 10 for r in c])
                pres_g = 100 * np.mean([r["pg"] >= 10 for r in c])
                print(f"  {elo:5.0f}-{ehi if ehi < 1e8 else 9999:5.0f} | {lbl:>12s} "
                      f"{len(c):5d} {len(L.episodes(c)):4d} | "
                      f"{g('fr'):5.2f} {g('rms_r'):7.1f} {g('env_r'):8.1f} {g('pr'):7.1f} "
                      f"{pres_r:5.0f}% | "
                      f"{g('fg'):5.2f} {g('rms_g'):7.1f} {g('env_g'):8.1f} {g('pg'):7.1f} "
                      f"{pres_g:5.0f}%")
                rows.append((g("rms_r"), g("rms_g")))
            if rows[0] and rows[1]:
                print(f"  {'':>11s} | {'RATIO V62/ctrl':>12s} {'':>5s} {'':>4s} | "
                      f"{'':>5s} {rows[0][0]/max(rows[1][0],1e-9):6.2f}x {'':>8s} {'':>7s} "
                      f"{'':>6s} | {'':>5s} {rows[0][1]/max(rows[1][1],1e-9):6.2f}x")

    # ---- headline trade, pooled over the clean speed range ------------------------------------
    print(f"\n{'='*138}\nPOOLED TRADE, engaged, drive, 0.3-11 m/s (order 1 clear of the band)"
          f"\n{'='*138}")
    print(f"  {'effort':>11s} | {'n V62':>6s} {'n ctrl':>7s} | "
          f"{'ratchet RMS V62':>16s} {'ctrl':>8s} {'ratio':>7s} | "
          f"{'grind RMS V62':>14s} {'ctrl':>8s} {'ratio':>7s}")
    for elo, ehi in ECELLS:
        a = [r for r in V62 if 0.3 <= r["v"] < 11 and elo <= r["eff"] < ehi]
        b = [r for r in CTRL if 0.3 <= r["v"] < 11 and elo <= r["eff"] < ehi]
        if not a or not b:
            continue
        ar, br_ = np.nanmedian([r["rms_r"] for r in a]), np.nanmedian([r["rms_r"] for r in b])
        ag, bg = np.nanmedian([r["rms_g"] for r in a]), np.nanmedian([r["rms_g"] for r in b])
        print(f"  {elo:5.0f}-{ehi if ehi < 1e8 else 9999:5.0f} | {len(a):6d} {len(b):7d} | "
              f"{ar:16.1f} {br_:8.1f} {ar/max(br_,1e-9):6.2f}x | "
              f"{ag:14.1f} {bg:8.1f} {ag/max(bg,1e-9):6.2f}x")

    # ---- sanity check on huge prominences ------------------------------------------------------
    print(f"\n{'='*138}\nPROMINENCE SANITY CHECK -- are the very large ratios real energy?"
          f"\n{'='*138}")
    allr = [r for r in V62 if np.isfinite(r["pr"])]
    allr.sort(key=lambda r: -r["pr"])
    print(f"  {'seg':>3s} {'t0':>7s} {'prom':>10s} {'RMS':>8s} {'env99':>8s} {'band pow':>10s} "
          f"{'floor RMS':>10s} {'v':>6s} {'eff':>6s}  verdict")
    for r in allr[:15]:
        # floor RMS: broadband amplitude outside the band, same window -- the denominator's scale
        floor = np.sqrt(max(r["pow_r"], 1e-30) / max(r["pr"], 1e-9)) / 16.0
        verdict = "REAL energy" if r["rms_r"] > 150 else ("quiet floor" if r["rms_r"] < 50
                                                          else "moderate")
        print(f"  {r['seg']:3d} {r['t0']:7.2f} {r['pr']:10.1f} {r['rms_r']:8.1f} "
              f"{r['env_r']:8.1f} {r['pow_r']:10.3g} {floor:10.1f} {r['v']:6.2f} "
              f"{r['eff']:6.0f}  {verdict}")


if __name__ == "__main__":
    main()
