#!/usr/bin/env python3
"""S0 -- validity survey for the V81 outer-loop test. Nothing here is a finding; it is the set of
things that must be true before a phase number means anything.

  1  SIGNAL IDENTITY   which column is the torsion bar, which angle-rate copy is un-quantised,
                       and what the 8.000x DBC scale error looks like on THIS route.
  2  SAMPLE RATE       mean rate over gap-free stretches, per segment. Not 1/median(dt).
  3  ZOH LOSS          what fraction of 0x18F frames the held `tq` column drops.
  4  WHERE IT IS       engaged HIGHWAY exposure, and where the bar's HF envelope is largest.
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

import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from v81loop_lib import (CACHE, FS_NOM, band_env, fs_run, load_route,  # noqa: E402
                         load_seg, locate, native_bar, prom_spectrum)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SEGS = list(range(14))


def main():
    R = load_route()
    print("=" * 100)
    print("S0.1  SIGNAL IDENTITY")
    print("=" * 100)
    d = load_seg(8)
    t, ang = d["t"], d["ang"]
    fs = fs_run(t)
    # numerical derivative of the angle, on the angle's OWN samples
    dang = np.gradient(ang, t)
    for k in ("rate_c", "rate_f", "cs_rate"):
        v = d[k]
        m = np.isfinite(v) & np.isfinite(dang)
        r = np.corrcoef(dang[m], v[m])[0, 1]
        # least-squares scale against the true derivative
        sc = float(np.dot(dang[m], v[m]) / np.dot(v[m], v[m]))
        q = np.unique(np.abs(np.diff(np.unique(v))))
        print(f"  {k:8s} corr(d(ang)/dt) = {r:+.4f}   d(ang)/dt = {sc:7.4f} x {k}"
              f"   min quantum {q[0] if len(q) else np.nan:.4g}  ptp {np.ptp(v):.1f}")
    print(f"  rate_c / rate_f least-squares ratio = "
          f"{float(np.dot(d['rate_c'], d['rate_f']) / np.dot(d['rate_f'], d['rate_f'])):.4f}")
    for k in ("tq", "cs_tq", "e4tq", "sc_tq", "co_tqcan"):
        v = np.asarray(d[k], float)
        print(f"  {k:9s} range {np.nanmin(v):9.1f} .. {np.nanmax(v):9.1f}   sd {np.nanstd(v):8.1f}")
    print(f"  corr(tq, cs_tq)   = {np.corrcoef(d['tq'], d['cs_tq'])[0, 1]:+.4f}  "
          f"[cs_tq is carState.steeringTorque = the torsion bar]")
    print(f"  corr(sc_tq, e4tq) = {np.corrcoef(d['sc_tq'], d['e4tq'])[0, 1]:+.4f}  "
          f"[sendcan 0x0E4 vs its bus echo src129]")
    print(f"  corr(sc_tq, co_tqcan) = {np.corrcoef(d['sc_tq'], d['co_tqcan'])[0, 1]:+.4f}")

    print()
    print("=" * 100)
    print("S0.2  SAMPLE RATE + S0.3 ZOH LOSS")
    print("=" * 100)
    print(f"  {'seg':>4} {'n':>6} {'fs_run':>8} {'1/med(dt)':>10} {'gaps>25ms':>10} "
          f"{'v_mean':>7} {'v_max':>7} {'eng%':>6}")
    rate = {}
    for s in SEGS:
        try:
            d = load_seg(s)
        except Exception:
            continue
        t = d["t"]
        f1, f2 = fs_run(t), 1.0 / np.median(np.diff(t))
        rate[s] = f1
        print(f"  {s:>4} {len(t):>6} {f1:>8.3f} {f2:>10.3f} {int((np.diff(t) > 0.025).sum()):>10} "
              f"{d['cs_v'].mean():>7.2f} {d['cs_v'].max():>7.2f} "
              f"{100 * np.mean(d['cc_lat'] > 0.5):>6.1f}")
    tb, qb, drop = native_bar(R)
    print(f"  native 0x18F recovery: {len(tb)} frames of {len(R['raw18_t'])} "
          f"({100 * len(tb) / len(R['raw18_t']):.1f}%), dropped {100 * drop:.2f}% of frames "
          f"that were current")
    print(f"  0x18F native fs = {fs_run(R['raw18_t']):.3f} Hz    "
          f"0x14A native fs = {fs_run(R['raw14_t']):.3f} Hz")
    ht = np.searchsorted(R["raw18_t"], R["t"], side="right") - 1
    age = R["t"] - R["raw18_t"][np.clip(ht, 0, None)]
    print(f"  ZOH hold age of `tq`: mean {1e3 * age.mean():.2f} ms  median "
          f"{1e3 * np.median(age):.2f} ms  p95 {1e3 * np.percentile(age, 95):.2f} ms"
          f"   => {360 * 25 * age.mean():.0f} deg of phase at 25 Hz if left uncorrected")

    print()
    print("=" * 100)
    print("S0.4  WHERE THE HIGHWAY EXPOSURE IS  (engaged = cc_lat, highway = v > 20 m/s)")
    print("=" * 100)
    tot = {}
    for s in SEGS:
        try:
            d = load_seg(s)
        except Exception:
            continue
        eng = d["cc_lat"] > 0.5
        for lab, m in (("all", eng), (">20", eng & (d["cs_v"] > 20)),
                       (">24", eng & (d["cs_v"] > 24)), (">26", eng & (d["cs_v"] > 26))):
            tot.setdefault(lab, {})[s] = float(m.sum()) / rate[s]
    print(f"  {'seg':>4} " + " ".join(f"{k:>9}" for k in tot))
    for s in SEGS:
        if s not in tot["all"]:
            continue
        print(f"  {s:>4} " + " ".join(f"{tot[k][s]:>9.1f}" for k in tot))
    print("  TOTAL " + " ".join(f"{sum(v.values()):>8.1f}s" for v in tot.values()))

    print()
    print("=" * 100)
    print("S0.5  WHERE THE BAR's HF ENERGY IS -- 2.56 s windows, engaged, ranked")
    print("=" * 100)
    rows = []
    for s in SEGS:
        try:
            d = load_seg(s)
        except Exception:
            continue
        t, fs = d["t"], rate[s]
        eng = d["cc_lat"] > 0.5
        n = 256
        for i in range(0, len(t) - n, 128):
            sl = slice(i, i + n)
            if eng[sl].mean() < 0.95:
                continue
            x = np.asarray(d["tq"][sl], float)
            P = np.abs(np.fft.rfft((x - x.mean()) * np.hanning(n))) ** 2
            f = np.fft.rfftfreq(n, 1 / fs)
            Rp = prom_spectrum(f, P)
            f0, p0 = locate(f, P, 4.0, 45.0, R=Rp)
            rows.append(dict(seg=s, t0=float(t[i]), v=float(d["cs_v"][sl].mean()),
                             e_6_10=band_env(x, fs, 6, 10), e_18_26=band_env(x, fs, 18, 26),
                             e_26_34=band_env(x, fs, 26, 34), e_34_46=band_env(x, fs, 34, 46),
                             f0=f0, prom=p0,
                             lchg=float(d["cs_lchg"][sl].max()),
                             brake=float(d["cs_brake"][sl].mean()),
                             e4=float(np.abs(d["sc_tq"][sl]).mean())))
    hw = [r for r in rows if r["v"] > 20]
    print(f"  {len(rows)} engaged windows, {len(hw)} of them highway (>20 m/s)")
    for band in ("e_18_26", "e_26_34", "e_34_46", "e_6_10"):
        print(f"\n  --- top 12 engaged windows by {band} (ALL speeds) ---")
        print(f"  {'seg':>4} {'t0':>7} {'v':>6} {'f0':>6} {'prom':>6} {'6-10':>7} {'18-26':>7} "
              f"{'26-34':>7} {'34-46':>7} {'lchg':>5} {'brk':>5} {'|e4|':>7}")
        for r in sorted(rows, key=lambda r: -r[band])[:12]:
            print(f"  {r['seg']:>4} {r['t0']:>7.1f} {r['v']:>6.2f} {r['f0']:>6.2f} "
                  f"{r['prom']:>6.1f} {r['e_6_10']:>7.1f} {r['e_18_26']:>7.1f} "
                  f"{r['e_26_34']:>7.1f} {r['e_34_46']:>7.1f} {r['lchg']:>5.0f} "
                  f"{r['brake']:>5.2f} {r['e4']:>7.0f}")
    print(f"\n  --- top 12 HIGHWAY (>20 m/s) engaged windows by e_18_26 ---")
    print(f"  {'seg':>4} {'t0':>7} {'v':>6} {'f0':>6} {'prom':>6} {'6-10':>7} {'18-26':>7} "
          f"{'26-34':>7} {'34-46':>7} {'lchg':>5} {'|e4|':>7}")
    for r in sorted(hw, key=lambda r: -r["e_18_26"])[:12]:
        print(f"  {r['seg']:>4} {r['t0']:>7.1f} {r['v']:>6.2f} {r['f0']:>6.2f} {r['prom']:>6.1f} "
              f"{r['e_6_10']:>7.1f} {r['e_18_26']:>7.1f} {r['e_26_34']:>7.1f} "
              f"{r['e_34_46']:>7.1f} {r['lchg']:>5.0f} {r['e4']:>7.0f}")

    (CACHE / "v81loop_survey.json").write_text(json.dumps(
        dict(fs=rate, rows=rows, zoh_age_ms=float(1e3 * age.mean())), indent=0))
    print(f"\n  wrote {CACHE / 'v81loop_survey.json'}")


if __name__ == "__main__":
    main()
