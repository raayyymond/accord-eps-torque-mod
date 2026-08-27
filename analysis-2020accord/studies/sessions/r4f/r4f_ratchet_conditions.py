#!/usr/bin/env python3
"""studies/sessions/r4f/r4f_ratchet_conditions.py -- WHAT the route-4f ratchet is conditional on.

`studies/sessions/r4f/r4f_ratchet_inventory.py` establishes the episodes, the frequency, the amplitude and the order
veto. This file asks the questions a LEVER needs answered:

  C1  ENGAGED vs MANUAL, speed-matched. If the line is engagement-conditional, the fix may be
      LKAS-gated (V67's design); if it is present manually too, it is base assist.
  C2  THE openpilot COMMAND as a CO-FACTOR. Route 4f's loudest ratchet segment (seg 3) has
      |e4tq| >= 4000 -- openpilot's own +/-4096 rail -- in 33.8% of frames. Is the ratchet a
      LARGE-COMMAND phenomenon?
  C3  ENVELOPE TRACKING inside episodes: does the 6-9 Hz bar envelope follow |command|, |angle
      rate| or driver effort, and at what lag?
  C4  THE COMMAND'S OWN SPECTRUM. The line has to enter the loop somewhere. `e4tq` is measured
      BEFORE the EPS, so if it carries no 6-9 Hz line the loop closes inside the EPS + plant.
      🛑 Guarded against the obvious objection: a railed command cannot show a small line, so the
      test is repeated on UNRAILED frames only.

🛑 NULL FIRST, EPISODES NOT WINDOWS. Every ratio is bootstrapped over episodes and reported
against a split-half null built from the same data by splitting each episode in half.
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

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from _r31_common import band_envelope, peak_prom, periodogram, sustained  # noqa: E402

NFFT = 256
RATCH = (6.0, 9.0)
CTRL = (24.0, 27.0)
RAIL = 4000          # openpilot's command rail is +/-4096
SEGS = list(range(8))


def load(s):
    return {k: v for k, v in np.load(ROOT / "_scratch/cache/r4f" / f"r4fs{s}.npz").items()}


def fs_mean(d):
    t = d["t"]
    return (len(t) - 1) / (t[-1] - t[0])


def hdr(s):
    print("\n" + "=" * 102)
    print(s)
    print("=" * 102)


def windows():
    """Disjoint 2.56 s windows over the whole route with everything C1-C4 need."""
    out = []
    for s in SEGS:
        d = load(s)
        fs = fs_mean(d)
        n = len(d["t"])
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        env = band_envelope(d["tq"], fs, *RATCH)
        eff = np.abs(sustained(d["tq"], fs))
        lat = d["cc_lat"] > 0.5
        v = np.abs(d["cs_v"])
        e4 = d["e4tq"]
        for i in range(0, n - NFFT + 1, NFFT):
            w = slice(i, i + NFFT)
            P = periodogram(d["tq"][w], fs, NFFT)
            if P is None:
                continue
            fb, pb = peak_prom(f, P, *RATCH)
            _, pc = peak_prom(f, P, *CTRL)
            out.append(dict(seg=s, i0=i, t0=float(d["t"][i]), fs=fs, fb=fb, pb=pb, pc=pc,
                            env=float(np.percentile(env[w], 99)),
                            v=float(v[w].mean()),
                            lat=float(lat[w].mean()),
                            eff=float(np.median(eff[w])),
                            e4p99=float(np.percentile(np.abs(e4[w]), 99)),
                            e4rail=float(np.mean(np.abs(e4[w]) >= RAIL)),
                            rate90=float(np.percentile(np.abs(d["rate_c"][w]), 90)),
                            ang=float(np.mean(np.abs(d["ang"][w])))))
    return out


def col(rs, k):
    return np.array([r[k] for r in rs], float)


def boot_ratio(A, B, key, n=4000, rng=None):
    """Episode-clustered bootstrap of median(A)/median(B). Episodes = (seg, contiguous block)."""
    rng = rng or np.random
    ea, eb = group(A), group(B)
    if not ea or not eb:
        return np.nan, np.nan, np.nan
    vals = []
    for _ in range(n):
        fa = [x[key] for j in rng.randint(0, len(ea), len(ea)) for x in ea[j]]
        fb = [x[key] for j in rng.randint(0, len(eb), len(eb)) for x in eb[j]]
        fa = [x for x in fa if np.isfinite(x)]
        fb = [x for x in fb if np.isfinite(x)]
        if fa and fb and np.median(fb) > 0:
            vals.append(np.median(fa) / np.median(fb))
    obs = np.median(col(A, key)) / max(np.median(col(B, key)), 1e-9)
    return obs, np.percentile(vals, 2.5), np.percentile(vals, 97.5)


def group(rs):
    """Split records into episodes: contiguous window blocks inside one segment."""
    eps, cur = [], []
    for r in sorted(rs, key=lambda x: (x["seg"], x["i0"])):
        if cur and r["seg"] == cur[-1]["seg"] and r["i0"] == cur[-1]["i0"] + NFFT:
            cur.append(r)
        else:
            if cur:
                eps.append(cur)
            cur = [r]
    if cur:
        eps.append(cur)
    return eps


def split_half_null(rs, key, n=4000):
    """Score each episode's first half against its second half -- the noise floor for a ratio."""
    eps = [e for e in group(rs) if len(e) >= 2]
    if len(eps) < 2:
        return np.nan, np.nan
    vals = []
    for _ in range(n):
        a, b = [], []
        for j in np.random.randint(0, len(eps), len(eps)):
            e = eps[j]
            m = len(e) // 2
            a += [x[key] for x in e[:m]]
            b += [x[key] for x in e[m:]]
        a = [x for x in a if np.isfinite(x)]
        b = [x for x in b if np.isfinite(x)]
        if a and b and np.median(b) > 0:
            vals.append(np.median(a) / np.median(b))
    return np.percentile(vals, 2.5), np.percentile(vals, 97.5)


# ------------------------------------------------------------------ C1 ------------------------
def c1_engaged(rs):
    hdr("C1.  ENGAGED vs MANUAL, SPEED-MATCHED -- is the ratchet LKAS-conditional?")
    eng = [r for r in rs if r["lat"] > 0.9]
    man = [r for r in rs if r["lat"] < 0.1]
    print(f"   raw exposure: engaged {len(eng)} windows ({len(eng) * 2.56:.0f} s), "
          f"manual {len(man)} windows ({len(man) * 2.56:.0f} s)")
    ve, vm = col(eng, "v"), col(man, "v")
    print(f"   |v| p10/50/90  engaged {np.percentile(ve, 10):.2f}/{np.percentile(ve, 50):.2f}/"
          f"{np.percentile(ve, 90):.2f}   manual {np.percentile(vm, 10):.2f}/"
          f"{np.percentile(vm, 50):.2f}/{np.percentile(vm, 90):.2f}")
    print("   ⇒ the distributions differ, so the raw comparison is confounded. Matched below.")

    print("\n   speed-stratified 6-9 Hz envelope p99 (counts) and prominence:")
    print(f"   {'|v| m/s':>10s} {'n eng':>6s} {'env eng':>8s} {'prom eng':>9s} "
          f"{'n man':>6s} {'env man':>8s} {'prom man':>9s} {'env ratio':>10s}")
    edges = [0, 1, 2, 3, 4, 6, 9, 14, 30]
    for lo, hi in zip(edges[:-1], edges[1:]):
        A = [r for r in eng if lo <= r["v"] < hi]
        B = [r for r in man if lo <= r["v"] < hi]
        if not A or not B:
            print(f"   {lo:4d}-{hi:<5d} {len(A):6d} "
                  f"{np.median(col(A, 'env')) if A else float('nan'):8.0f} "
                  f"{np.nanmedian(col(A, 'pb')) if A else float('nan'):9.1f} {len(B):6d} "
                  f"{np.median(col(B, 'env')) if B else float('nan'):8.0f} "
                  f"{np.nanmedian(col(B, 'pb')) if B else float('nan'):9.1f} "
                  f"{'(no pair)':>10s}")
            continue
        print(f"   {lo:4d}-{hi:<5d} {len(A):6d} {np.median(col(A, 'env')):8.0f} "
              f"{np.nanmedian(col(A, 'pb')):9.1f} {len(B):6d} {np.median(col(B, 'env')):8.0f} "
              f"{np.nanmedian(col(B, 'pb')):9.1f} "
              f"{np.median(col(A, 'env')) / max(np.median(col(B, 'env')), 1e-9):10.2f}")

    # nearest-neighbour matched, episode-clustered
    vmB = col(man, "v")
    A, B = [], []
    for r in eng:
        j = int(np.argmin(np.abs(vmB - r["v"])))
        if abs(vmB[j] - r["v"]) <= 0.6:
            A.append(r)
            B.append(man[j])
    if A:
        o, l, h = boot_ratio(A, B, "env")
        nl, nh = split_half_null(eng, "env")
        print(f"\n   ★ nearest-neighbour matched (|dv| <= 0.6 m/s), n = {len(A)} pairs")
        print(f"     6-9 Hz envelope ENGAGED / MANUAL = {o:.2f}x  [{l:.2f}, {h:.2f}]  "
              f"(episode-clustered)")
        print(f"     split-half null from the engaged arm alone: [{nl:.2f}, {nh:.2f}]")
        print("     ⇒ a ratio is only a claim if its CI lies OUTSIDE the null interval.")
    # a raw contingency on detections, for the record
    from math import comb
    floor = np.nanpercentile(col(rs, "pc"), 95)
    de = int(np.sum(col(eng, "pb") >= floor))
    dm = int(np.sum(col(man, "pb") >= floor))
    print(f"\n   detections at the control-band p95 floor ({floor:.1f}): "
          f"engaged {de}/{len(eng)}, manual {dm}/{len(man)}")
    if dm == 0 and de > 0:
        # one-sided Fisher p for the observed table under the marginal
        n1, n2, k = len(eng), len(man), de
        p = comb(n1, k) * comb(n2, 0) / comb(n1 + n2, k)
        print(f"   one-sided Fisher exact p (all {de} detections in the engaged arm) = {p:.2e}")
        print("   ⚠ This ignores the speed confound; read it beside the stratified table above.")


# ------------------------------------------------------------------ C2 ------------------------
def c2_command(rs):
    hdr("C2.  THE openpilot COMMAND AS A CO-FACTOR -- is the ratchet a LARGE-COMMAND phenomenon?")
    eng = [r for r in rs if r["lat"] > 0.9]
    floor = np.nanpercentile(col(rs, "pc"), 95)
    det = [r for r in eng if r["pb"] >= floor]
    non = [r for r in eng if r["pb"] < floor]
    print(f"   engaged windows: {len(det)} with a 6-9 Hz line (>= {floor:.1f}), {len(non)} without")
    for lbl, g in (("WITH a 6-9 Hz line", det), ("WITHOUT", non)):
        if not g:
            continue
        print(f"   {lbl:22s} |e4| p99 med {np.median(col(g, 'e4p99')):6.0f}   "
              f"rail duty med {np.median(col(g, 'e4rail')):6.3f} mean {np.mean(col(g, 'e4rail')):6.3f}   "
              f"|v| med {np.median(col(g, 'v')):5.2f}   eff med {np.median(col(g, 'eff')):5.0f}   "
              f"|rate|p90 med {np.median(col(g, 'rate90')):5.0f}   |ang| med "
              f"{np.median(col(g, 'ang')):6.1f}")
    if det and non:
        print("\n   🛑 A RATIO IS DEGENERATE FOR RAIL DUTY -- the NO-LINE median is exactly 0.000,")
        print("      so median(A)/median(B) explodes. Reported as a DIFFERENCE of means instead.")
        ra, rb = col(det, "e4rail"), col(non, "e4rail")
        print(f"   ★ command-rail duty, mean: LINE {ra.mean():.3f}  vs  NO-LINE {rb.mean():.3f}  "
              f"(difference {ra.mean() - rb.mean():+.3f})")
        ea, eb = group(det), group(non)
        dif = []
        for _ in range(4000):
            A = [x["e4rail"] for j in np.random.randint(0, len(ea), len(ea)) for x in ea[j]]
            B = [x["e4rail"] for j in np.random.randint(0, len(eb), len(eb)) for x in eb[j]]
            dif.append(np.mean(A) - np.mean(B))
        print(f"     episode-clustered 95% CI on the difference: "
              f"[{np.percentile(dif, 2.5):+.3f}, {np.percentile(dif, 97.5):+.3f}]")
        o2, l2, h2 = boot_ratio(det, non, "e4p99")
        print(f"     |command| p99,   LINE / NO-LINE = {o2:.2f}x  [{l2:.2f}, {h2:.2f}]")
        o3, l3, h3 = boot_ratio(det, non, "rate90")
        print(f"     |angle rate| p90, LINE / NO-LINE = {o3:.2f}x  [{l3:.2f}, {h3:.2f}]")
        o4, l4, h4 = boot_ratio(det, non, "eff")
        print(f"     driver effort,    LINE / NO-LINE = {o4:.2f}x  [{l4:.2f}, {h4:.2f}]"
              "   ⇐ NEGATIVE CONTROL")
        nl, nh = split_half_null(eng, "e4p99")
        print(f"     split-half null on |command| p99 (engaged arm): [{nl:.2f}, {nh:.2f}]")

    print("\n   contingency: 6-9 Hz detection rate by command-rail duty, engaged windows only")
    print(f"   {'rail duty':>14s} {'n':>5s} {'det':>5s} {'rate':>7s} {'env99 med':>10s}")
    for lo, hi in ((0.0, 0.02), (0.02, 0.10), (0.10, 0.30), (0.30, 0.60), (0.60, 1.01)):
        g = [r for r in eng if lo <= r["e4rail"] < hi]
        if not g:
            continue
        dd = int(np.sum(col(g, "pb") >= floor))
        print(f"   {lo:5.2f}-{hi:<8.2f} {len(g):5d} {dd:5d} {dd / len(g):7.3f} "
              f"{np.median(col(g, 'env')):10.0f}")


# ------------------------------------------------------------------ C3 ------------------------
def c3_tracking(rs):
    hdr("C3.  ENVELOPE TRACKING INSIDE EPISODES -- what does the 6-9 Hz amplitude follow?")
    print("   Per episode: cross-correlation of the 6-9 Hz bar envelope against |command|,")
    print("   |angle rate| and driver effort, all lowpassed to 2 Hz. Peak r and its lag.")
    print("   +lag = the envelope FOLLOWS that channel by that many ms.")
    floor = np.nanpercentile(col(rs, "pc"), 95)
    eng = [r for r in rs if r["lat"] > 0.9 and r["pb"] >= floor]
    eps = group(eng)
    cache = {}
    print(f"\n   {'ep':>2s} {'seg':>3s} {'t0':>6s} " + "".join(
        f"{n:>21s}" for n in ("|cmd|", "|angle rate|", "driver effort")))
    for k, e in enumerate(eps):
        s = e[0]["seg"]
        if s not in cache:
            cache[s] = load(s)
        d = cache[s]
        fs = e[0]["fs"]
        a = max(0, e[0]["i0"] - NFFT)
        b = min(len(d["t"]), e[-1]["i0"] + 2 * NFFT)
        env = band_envelope(d["tq"][a:b], fs, *RATCH)

        def lp(x, fc=2.0):
            x = np.asarray(x, float)
            X = np.fft.rfft(x - x.mean())
            f = np.fft.rfftfreq(len(x), 1 / fs)
            X[f > fc] = 0
            return np.fft.irfft(X, n=len(x))
        row = f"   {k:2d} {s:3d} {e[0]['t0']:6.1f} "
        ye = lp(env)
        for ch in (np.abs(d["e4tq"][a:b]), np.abs(d["rate_c"][a:b]),
                   np.abs(sustained(d["tq"], fs)[a:b])):
            yc = lp(ch)
            m = min(len(ye), len(yc))
            if m < 64 or ye.std() == 0 or yc.std() == 0:
                row += f"{'--':>21s}"
                continue
            L = int(0.5 * fs)
            cc = [np.corrcoef(ye[max(0, l):m + min(0, l)],
                              yc[max(0, -l):m + min(0, -l)])[0, 1]
                  for l in range(-L, L + 1)]
            j = int(np.argmax(np.abs(cc)))
            row += f"  r{cc[j]:+.2f} @{1000 * (j - L) / fs:+6.0f} ms"
        print(row)
    print("\n   ⚠ Both series are heavily lowpassed, so |r| is inflated relative to an")
    print("     independent-sample correlation. Use the SIGN and the LAG, not the magnitude.")


# ------------------------------------------------------------------ C4 ------------------------
def c4_command_spectrum(rs):
    hdr("C4.  THE COMMAND'S OWN 6-9 Hz CONTENT -- where does the line enter the loop?")
    print("   `e4tq` is openpilot's request measured on sendcan, BEFORE the EPS acts on it.")
    print("   🛑 THE RAIL OBJECTION, tested rather than argued: a command pinned at +/-4096")
    print("      cannot show a small line, so each window is scored twice -- as-is, and after")
    print("      dropping every window whose rail duty exceeds 2%.")
    floor = np.nanpercentile(col(rs, "pc"), 95)
    eng = [r for r in rs if r["lat"] > 0.9]
    det = [r for r in eng if r["pb"] >= floor]
    cache = {}
    print(f"\n   {'ep':>2s} {'seg':>3s} {'t0':>6s} {'bar f0':>7s} {'bar prom':>9s} "
          f"{'cmd prom':>9s} {'cmd f':>7s} {'rate prom':>10s} {'rate f':>7s} "
          f"{'angle prom':>11s} {'rail':>6s}")
    rows = []
    for k, r in enumerate(sorted(det, key=lambda x: -x["pb"])):
        s = r["seg"]
        if s not in cache:
            cache[s] = load(s)
        d = cache[s]
        fs = r["fs"]
        w = slice(r["i0"], r["i0"] + NFFT)
        f = np.fft.rfftfreq(NFFT, 1 / fs)
        out = []
        for ch in ("e4tq", "rate_c", "ang"):
            P = periodogram(d[ch][w], fs, NFFT)
            out.append(peak_prom(f, P, *RATCH) if P is not None else (np.nan, np.nan))
        rows.append((r, out))
        print(f"   {k:2d} {s:3d} {r['t0']:6.1f} {r['fb']:7.2f} {r['pb']:9.1f} "
              f"{out[0][1]:9.1f} {out[0][0]:7.2f} {out[1][1]:10.1f} {out[1][0]:7.2f} "
              f"{out[2][1]:11.1f} {r['e4rail']:6.3f}")
    cm = np.array([o[0][1] for _, o in rows], float)
    rt = np.array([o[1][1] for _, o in rows], float)
    rl = np.array([r["e4rail"] for r, _ in rows], float)
    q = rl <= 0.02
    print(f"\n   COMMAND 6-9 Hz prominence over {len(cm)} detection windows: "
          f"median {np.nanmedian(cm):.1f}  max {np.nanmax(cm):.1f}")
    print(f"   ...restricted to windows with rail duty <= 2% (n = {int(q.sum())}): "
          f"median {np.nanmedian(cm[q]) if q.any() else float('nan'):.1f}  "
          f"max {np.nanmax(cm[q]) if q.any() else float('nan'):.1f}")
    print(f"   ANGLE-RATE 6-9 Hz prominence over the same windows: "
          f"median {np.nanmedian(rt):.1f}  max {np.nanmax(rt):.1f}")
    print("\n   The kit's PRESENCE threshold is prominence >= 10 (studies/sessions/r37/analyze_r37_v62_creep.py).")
    print("   ⇒ Read the two medians against 10, and against the bar's own column.")


def main():
    np.random.seed(20260804)
    print(__doc__)
    rs = windows()
    c1_engaged(rs)
    c2_command(rs)
    c3_tracking(rs)
    c4_command_spectrum(rs)


if __name__ == "__main__":
    main()
