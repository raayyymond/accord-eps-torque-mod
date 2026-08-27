#!/usr/bin/env python3
"""HOW MUCH DATA WOULD IT TAKE?  The energy and Q questions came back UNDERPOWERED.  That is
only useful if it is quantified -- so measure the precision this instrument actually delivers
as a function of block count, and extrapolate to the n a given effect would need.

METHOD.  The same-alpha pair (V86B/r70 vs V85/r6e, both `0xC40D4` = 573) is the null: whatever
spread it shows at n blocks is the floor at n blocks.  Subsample blocks from each arm, form the
ratio, and measure the 95% interval half-width in LOG space.  Width should fall as c/sqrt(n);
fit c on the range actually available and extrapolate.  🛑 The extrapolation is stated as such.
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
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
import v86_freq_test as V           # noqa: E402
from v86_hf_mode import (HFHI, HFLO, band_energy, fit_mode, halfpower)   # noqa: E402

ROOT = V.ROOT
RNG = np.random.default_rng(86_2101)
VBINS = V.VBINS
O = {}
WIN_S = 10.13          # one block


def prep(rs):
    for r in rs:
        f0, Q, A, ar, ok = fit_mode(r["f"], r["P"])
        r["l_f0"], r["l_Q"], r["l_ok"] = f0, Q, ok
        r["hp_Q"], _ = halfpower(r["f"], r["R"])
        r["e_tot"], r["e_floor"], r["e_exc"] = band_energy(r)
        m = (r["f"] >= HFLO) & (r["f"] <= HFHI) & np.isfinite(r["R"])
        r["f_hf"] = float(r["f"][np.argmax(np.where(m, r["R"], -np.inf))])
        r["a_hf"] = V.band_amp(r, 0.5 * (HFLO + HFHI), 4.5)
    return rs


def sub_ratio_width(A, B, key, nblk, nrep=1500):
    """95% half-width, in ln units, of the A/B ratio when each arm is cut to `nblk` blocks."""
    def grp(rs):
        g = {}
        for r in rs:
            if np.isfinite(r.get(key, np.nan)) and r.get(key, 0) > 0:
                g.setdefault(r["blk"], []).append(r[key])
        return g
    gA, gB = grp(A), grp(B)
    kA, kB = list(gA), list(gB)
    if len(kA) < 3 or len(kB) < 3:
        return np.nan
    out = []
    for _ in range(nrep):
        ia = RNG.choice(len(kA), size=min(nblk, len(kA)), replace=nblk > len(kA))
        ib = RNG.choice(len(kB), size=min(nblk, len(kB)), replace=nblk > len(kB))
        a = np.median(np.concatenate([gA[kA[i]] for i in ia]))
        b = np.median(np.concatenate([gB[kB[i]] for i in ib]))
        if a > 0 and b > 0:
            out.append(np.log(a / b))
    if len(out) < 50:
        return np.nan
    lo, hi = np.percentile(out, [2.5, 97.5])
    return float((hi - lo) / 2.0)


def main():
    E = {}
    for name, (c, p, s) in V.ROUTES.items():
        E[name] = prep(V.in_speed(V.spectra(V.windows(name, c, p, s, engaged=True))))
    NULL = ("V86B/r70", "V85/r6e")          # same alpha -- the floor
    EFF = ("V86/r6f", "V85/r6e")            # alpha differs

    V.hdr("N1  PRECISION vs BLOCK COUNT, measured on the SAME-ALPHA null pair.\n"
          "    Half-width of the 95%% interval, in ln units.  A ratio is only readable when the\n"
          "    half-width is smaller than |ln(effect)|.")
    KEYS = [("f_hf", "frequency (argmax)"), ("l_f0", "frequency (Lorentzian f0)"),
            ("e_exc", "ENERGY (excess 18-27)"), ("a_hf", "amplitude (p99 env)"),
            ("hp_Q", "Q (half-power)"), ("l_Q", "Q (Lorentzian)")]
    ns = [4, 5, 6, 7, 8, 10, 12, 15]
    print("    %-26s %s" % ("statistic", "  ".join("n=%-5d" % n for n in ns)))
    O["width"] = {}
    for key, lab in KEYS:
        ws = [sub_ratio_width(E[NULL[0]], E[NULL[1]], key, n) for n in ns]
        print("    %-26s %s" % (lab, "  ".join("%6.3f" % w if np.isfinite(w) else "   -- "
                                               for w in ws)))
        O["width"][key] = dict(label=lab, n=ns, width=[float(w) for w in ws])

    V.hdr("N2  THE n REQUIRED.  Fit half-width = c/sqrt(n) on the range available, then solve\n"
          "    for the n at which a given effect becomes readable.  🛑 EXTRAPOLATION -- stated\n"
          "    as such; it assumes the block-to-block variance keeps behaving as it does now.")
    print("    %-26s %8s | %s" % ("statistic", "c", "blocks needed / engaged MINUTES per arm"))
    print("    %-26s %8s | %11s %11s %11s" % ("", "", "1.2x effect", "1.5x effect", "2.0x effect"))
    O["required_n"] = {}
    for key, lab in KEYS:
        w = np.array(O["width"][key]["width"], float)
        n = np.array(ns, float)
        ok = np.isfinite(w)
        if ok.sum() < 3:
            continue
        c = float(np.mean(w[ok] * np.sqrt(n[ok])))
        cells = []
        row = {}
        for eff in (1.2, 1.5, 2.0):
            need = (c / np.log(eff)) ** 2
            mins = need * WIN_S / 60.0
            cells.append("%6.0f/%4.1fm" % (need, mins))
            row[str(eff)] = dict(blocks=float(need), minutes=float(mins))
        print("    %-26s %8.3f | %s" % (lab, c, " ".join(cells)))
        O["required_n"][key] = dict(label=lab, c=c, **row)
    print("\n    For scale: route 6f delivered 11 blocks (141 s engaged), 6e 15, r70 7.")

    V.hdr("N3  THE JOINT (df, dQ, dE) PATTERN -- gain-set vs phase-set, and whether the data\n"
          "    can distinguish them AT ALL at this n.")
    print("    %-22s | %24s | %24s | %s"
          % ("quantity", "alpha DIFFERS (V86/V85)", "alpha SAME (V86B/V85)", "readable?"))
    O["pattern"] = {}
    for key, lab in KEYS:
        re = V.strat_block_boot_ratio(E[EFF[0]], E[EFF[1]], key=key)
        rn = V.strat_block_boot_ratio(E[NULL[0]], E[NULL[1]], key=key)
        eff_ex = re["hi"] < 1.0 or re["lo"] > 1.0
        null_ex = rn["hi"] < 1.0 or rn["lo"] > 1.0
        if null_ex:
            verdict = "NO -- null itself excludes 1"
        elif eff_ex:
            verdict = "YES"
        else:
            verdict = "no -- UNDERPOWERED"
        print("    %-22s | %6.3f [%6.3f,%6.3f] | %6.3f [%6.3f,%6.3f] | %s"
              % (lab, re["ratio"], re["lo"], re["hi"], rn["ratio"], rn["lo"], rn["hi"], verdict))
        O["pattern"][key] = dict(label=lab, effect=re, null=rn, readable=verdict)
    print("\n    🛑 A statistic whose SAME-ALPHA null already excludes 1.00 is DISQUALIFIED --\n"
          "       it is measuring the route, not the lever.  It is not evidence either way.")

    (ROOT / "_scratch/cache/r6f" / "v86_hf_power.json").write_text(json.dumps(O, indent=1, default=float))
    print("\nwrote %s" % (ROOT / "_scratch/cache/r6f" / "v86_hf_power.json"))


if __name__ == "__main__":
    main()
