#!/usr/bin/env python3
r"""THREE CLOSE-OUT ITEMS: E3's free choices, the 0x97 ring-down redo, and the Q = 10.21 bracket.

A.  🛑 APPLY THE E1/E2 LESSON TO E3 ITSELF.
    E1 and E2 were killed because a free ANALYST choice -- the fit-window length -- moved the
    answer 3.5x / 6.3x.  During validation I introduced two free choices into E3:
      (i)  POLE SELECTION -- by residue (chosen) vs by minimum zeta (the first version), and
      (ii) the VARIANCE-EXPLAINED GATE `r2_min`, set to 0.35 by hand.
    Both are swept here against every E3-derived number this session quotes.  If either moves an
    answer materially it is said so BEFORE the number is used.

B.  ROUTE 0x97 (STOCK) RING-DOWN, redone with E3 at the criteria `studies/stock-baseline/stock_r97_ringdown.py` used --
    FROZEN (4.0 s pre / 4.0 s post) and RELAXED (2.5 / 3.0) -- so the replacement for
    `_scratch/out/_stock_r97_ringdown.json` is like-for-like.
    🛑 That file is NOT edited or deleted here.  Reporting the defect, not fixing the record.

C.  THE Q = 10.21 BRACKET.  `studies/damping-q/ringdown_validate.py` section 5 showed the 2-pole PSD fit is nearly
    unbiased on a CLEAN 2-pole (1.07x at zeta 0.049) but biased HIGH by 1.9x when a broadband
    background of EQUAL 4-14 Hz power is added.  "Equal" was a guess.  This measures the REAL
    background fraction on engaged data and re-runs the control AT that value, so
    `docs/ANALYSIS-2026-08-20` section 2's `zeta = 0.0490 / Q 10.21` resolves to a range.
    Direction, established earlier: background inflates zeta ⇒ **Q is UNDERSTATED, not overstated.**
"""
from __future__ import annotations
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
from scipy.signal import lfilter, welch

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import v102_xb_lib as L                                   # noqa: E402
import ringdown_validate as RV                            # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = L.FS
LAB = {"97": "V9b STOCK", "9e": "V103", "96": "V102", "73": "V88", "85": "V100 4x", "95": "V101 8x"}
FN = 8.16


def reg(rt):
    if rt not in L.ROUTES:
        L.ROUTES[rt] = L._mk(rt, LAB.get(rt, rt), gain=0, clamp=0, leverB=False, idcode=0, bits="")
    return bool(L.ROUTES[rt]["segs"])


def hdr(s):
    print("\n" + "=" * 106); print(s); print("=" * 106, flush=True)


# ------------------------------------------------------------------------------------------------
# A.  E3 SENSITIVITY
# ------------------------------------------------------------------------------------------------

def pencil(x, fs, r2_min, select, f_lo=4.0, f_hi=14.0, order=2, pencil_frac=0.4):
    """E3 with BOTH free choices exposed.  `select` in {'residue', 'minzeta'}."""
    x = np.asarray(x, float) - np.mean(x)
    N = len(x)
    if N < 40:
        return np.nan, np.nan
    Lp = int(pencil_frac * N)
    if Lp < order + 2 or N - Lp < order + 2:
        return np.nan, np.nan
    Y = np.lib.stride_tricks.sliding_window_view(x, Lp + 1)
    Y0, Y1 = Y[:, :-1], Y[:, 1:]
    try:
        U, s, Vh = np.linalg.svd(Y0, full_matrices=False)
    except np.linalg.LinAlgError:
        return np.nan, np.nan
    M = min(order * 2, int(np.count_nonzero(s > s[0] * 1e-10)))
    if M < 2:
        return np.nan, np.nan
    A = np.diag(1.0 / s[:M]) @ U[:, :M].T @ Y1 @ Vh[:M].conj().T
    if not np.all(np.isfinite(A)):
        return np.nan, np.nan
    lam = np.linalg.eigvals(A)
    lam = lam[np.abs(lam) > 1e-12]
    if not len(lam):
        return np.nan, np.nan
    sp = np.log(lam.astype(complex)) * fs
    f, sig = np.abs(sp.imag) / (2 * np.pi), sp.real
    ok = (f >= f_lo) & (f <= f_hi) & (sig < 0) & (np.abs(sig) < 2 * np.pi * f)
    if not ok.any():
        return np.nan, np.nan
    cand = np.flatnonzero(ok)
    n_ = np.arange(N)
    V = np.power(lam[cand][None, :].astype(complex), n_[:, None])
    try:
        amp, *_ = np.linalg.lstsq(V, x.astype(complex), rcond=None)
    except np.linalg.LinAlgError:
        return np.nan, np.nan
    if select == "residue":
        k = cand[int(np.argmax(np.abs(amp)))]
        j = int(np.argmax(np.abs(amp)))
    else:                                        # 'minzeta' -- the first, defective version
        zz = -sig[cand] / np.sqrt(sig[cand] ** 2 + (2 * np.pi * f[cand]) ** 2)
        j = int(np.argmin(zz))
        k = cand[j]
    zk = -sig[k] / np.sqrt(sig[k] ** 2 + (2 * np.pi * f[k]) ** 2)
    recon = 2.0 * np.real(amp[j] * np.power(lam[k].astype(complex), n_))
    frac = 1.0 - float(np.sum((x - recon) ** 2)) / max(float(np.sum(x ** 2)), 1e-30)
    if frac < r2_min:
        return np.nan, np.nan
    return float(f[k]), float(zk)


GATES = (0.15, 0.25, 0.35, 0.50, 0.65)
SELECTS = ("residue", "minzeta")


def a_sensitivity(real_edges):
    hdr("A1.  RECOVERY vs the two free choices -- truth zeta, 30 reps, 1.5 s post-edge, SNR 20 dB")
    print("    %-9s %-6s %s" % ("select", "gate", "".join("%13s" % ("z=%.3f" % z)
                                                          for z in RV.ZETAS)))
    for sel in SELECTS:
        for g in GATES:
            cells = []
            for zt in RV.ZETAS:
                got = []
                for r in range(30):
                    rng = np.random.default_rng(1000 + r)
                    x, n = RV.make_ringdown(FN, zt, dur=1.5, snr_db=20.0, rng=rng)
                    _, z = pencil(x[n:], FS, g, sel)
                    if np.isfinite(z):
                        got.append(z)
                cells.append("%13s" % ("%.4f(%2d)" % (np.median(got), len(got)) if got else "--"))
            print("    %-9s %-6.2f %s" % (sel, g, "".join(cells)))

    hdr("A2.  THE THREE NULLS vs the two free choices -- fits returned out of 40 (want 0)")
    print("    %-9s %-6s %12s %12s %12s" % ("select", "gate", "white noise", "perfect step",
                                            "phase-rand"))
    for sel in SELECTS:
        for g in GATES:
            cnt = []
            for maker in ("white", "step", "phase"):
                n_ok = 0
                for r in range(40):
                    rng = np.random.default_rng(5000 + r)
                    if maker == "white":
                        x, n = RV.make_white(dur=1.5, rng=rng)
                    elif maker == "step":
                        x, n = RV.make_perfect_step(FN, dur=1.5, snr_db=20.0, rng=rng)
                    else:
                        seg = real_edges[r % len(real_edges)][1]
                        x, n = RV.phase_randomise(seg, rng=rng), 0
                    _, z = pencil(x[n:], FS, g, sel)
                    n_ok += int(np.isfinite(z))
                cnt.append(n_ok)
            print("    %-9s %-6.2f %12d %12d %12d" % (sel, g, *cnt))

    hdr("A3.  THE POWER TABLE vs the free choices -- injected zeta=0.05 at A x pre-edge band RMS")
    print("    🛑 A THIRD FREE CHOICE, found while running this sweep and NOT flagged earlier:")
    print("       the ANALYSIS WINDOW LENGTH.  The variance-explained gate is a RATIO over the")
    print("       window, and a zeta=0.05 ring at 8 Hz is gone in ~0.4 s -- so lengthening the")
    print("       window dilutes the mode's share and the gate rejects it.  This is the SAME class")
    print("       of defect that killed E1/E2 (their answer moved with the fit-window length), so")
    print("       it is swept here rather than fixed by choosing a favourable value.")
    print("    detections out of %d real post-edge segments, and the recovered median"
          % len(real_edges))
    w = np.hanning(256)
    print("\n    (a) WINDOW SWEEP at select=residue, gate=0.35")
    print("    %-10s %s" % ("window s", "".join("%16s" % ("A=%.1f" % a) for a in (1.0, 2.0, 4.0))))
    for win_s in (0.75, 1.0, 1.5, 2.0, 3.0):
        cells = []
        nn = int(win_s * FS)
        for A in (1.0, 2.0, 4.0):
            got = []
            for _rt, post, pre in real_edges:
                if len(post) < nn:
                    continue
                amp = L.bandrms(pre[-256:], FS, 6, 9, w) * A
                t = np.arange(nn) / FS
                inj = post[:nn] + amp * np.exp(-0.05 * 2 * np.pi * 8.0 * t) * np.sin(
                    2 * np.pi * 8.0 * t)
                _, z = pencil(inj, FS, 0.35, "residue")
                if np.isfinite(z):
                    got.append(z)
            cells.append("%16s" % ("%2d/%2d  %.3f" % (len(got), len(real_edges), np.median(got))
                                   if got else "%2d/%2d" % (0, len(real_edges))))
        print("    %-10.2f %s" % (win_s, "".join(cells)))
    print("\n    (b) SELECT x GATE at the window that maximises power (1.0 s)")
    print("    %-9s %-6s %s" % ("select", "gate",
                                "".join("%16s" % ("A=%.1f" % a) for a in (1.0, 2.0, 4.0))))
    nn = int(1.0 * FS)
    for sel in SELECTS:
        for g in GATES:
            cells = []
            for A in (1.0, 2.0, 4.0):
                got = []
                for _rt, post, pre in real_edges:
                    if len(post) < nn:
                        continue
                    amp = L.bandrms(pre[-256:], FS, 6, 9, w) * A
                    t = np.arange(nn) / FS
                    inj = post[:nn] + amp * np.exp(-0.05 * 2 * np.pi * 8.0 * t) * np.sin(
                        2 * np.pi * 8.0 * t)
                    _, z = pencil(inj, FS, g, sel)
                    if np.isfinite(z):
                        got.append(z)
                cells.append("%16s" % ("%2d/%2d  %.3f" % (len(got), len(real_edges),
                                                          np.median(got)) if got else
                                       "%2d/%2d" % (0, len(real_edges))))
            print("    %-9s %-6.2f %s" % (sel, g, "".join(cells)))

    hdr("A4.  THE REAL EDGES vs ALL THREE free choices -- fits returned (the 0/7 result)")
    print("    %-9s %-6s %s" % ("select", "gate",
                                "".join("%12s" % ("%.2f s" % w_) for w_ in (0.75, 1.0, 1.5, 2.0,
                                                                            3.0))))
    for sel in SELECTS:
        for g in GATES:
            cells = []
            for w_ in (0.75, 1.0, 1.5, 2.0, 3.0):
                nn = int(w_ * FS)
                n_ok = sum(int(np.isfinite(pencil(post[:nn], FS, g, sel)[1]))
                           for _rt, post, _pre in real_edges if len(post) >= nn)
                cells.append("%12s" % ("%d / %d" % (n_ok, len(real_edges))))
            print("    %-9s %-6.2f %s" % (sel, g, "".join(cells)))
    print("\n    🛑 If this is 0 at EVERY setting, the null is robust to the analyst's choices.")
    print("       Read it beside A3(a): the null is only INTERPRETABLE where A3 shows real power.")


# ------------------------------------------------------------------------------------------------
# B.  ROUTE 0x97 RING-DOWN REDO
# ------------------------------------------------------------------------------------------------

def collect_edges(routes, pre_s=3.0, post_s=3.0):
    out = []
    for rt in routes:
        for blk in L.all_blocks(rt):
            lat = np.asarray(blk["cc_lat"], float) > 0.5
            x = np.asarray(blk["tq"], float)
            v = np.abs(np.asarray(blk.get("v_rear", blk["cs_v"]), float))
            npre, npost = int(pre_s * FS), int(post_s * FS)
            for i in np.flatnonzero(np.diff(lat.astype(int)) < 0) + 1:
                if i - npre < 0 or i + npost >= len(x):
                    continue
                if not (lat[i - npre:i].all() and not lat[i:i + npost].any()):
                    continue
                if v[i] < 1.0:
                    continue
                out.append((rt, x[i:i + npost].copy(), x[max(i - int(4 * FS), 0):i].copy()))
    return out


def b_route97():
    hdr("B.  ROUTE 0x97 (STOCK) RING-DOWN, E3, at `studies/stock-baseline/stock_r97_ringdown.py`'s own two criteria")
    print("    🛑 `rlog-tools/_scratch/out/_stock_r97_ringdown.json` is NOT touched.  This is the replacement")
    print("       NUMBER; folding it into the record is the orchestrator's call.")
    w = np.hanning(256)
    for pre_s, post_s, tag in ((4.0, 4.0, "FROZEN (4.0/4.0)"), (2.5, 3.0, "RELAXED (2.5/3.0)")):
        eds = collect_edges(["97"], pre_s, post_s)
        print("\n    --- %s : %d qualifying edges on route 0x97 ---" % (tag, len(eds)))
        if not eds:
            print("        none")
            continue
        for k, (_rt, post, pre) in enumerate(eds):
            amp = L.bandrms(pre[-256:], FS, 6, 9, w)
            f3, z3 = pencil(post[:int(1.5 * FS)], FS, 0.35, "residue")
            _, z1 = RV.e1_hilbert_env(post, FS, 7.79, fit_s=2.0)
            print("        edge%-2d pre-edge 6-9 Hz RMS %7.1f ct   E3: %-12s   E1(fit_s=2.0): %s"
                  % (k, amp, "%.2f Hz z=%.4f" % (f3, z3) if np.isfinite(z3) else "REFUSED",
                     "%.4f" % z1 if np.isfinite(z1) else "--"))
        print("        ⇒ E3 accepted %d of %d."
              % (sum(np.isfinite(pencil(p[:int(1.5 * FS)], FS, 0.35, "residue")[1])
                     for _r, p, _q in eds), len(eds)))


# ------------------------------------------------------------------------------------------------
# C.  THE Q BRACKET
# ------------------------------------------------------------------------------------------------

def twopole_plus_floor(f, p, f_lo=4.0, f_hi=16.0):
    """Fit p(f) = g/((1-r^2)^2+(2 z r)^2) + c over the band.  Returns (fn, zeta, peak/floor)."""
    m = (f >= f_lo) & (f <= f_hi)
    ff, pp = f[m], p[m]
    best = (np.inf, np.nan, np.nan, np.nan, np.nan)
    for fn in np.linspace(f_lo + 0.5, f_hi - 0.5, 100):
        r = ff / fn
        for z in np.logspace(np.log10(0.005), np.log10(0.5), 70):
            shape = 1.0 / ((1 - r ** 2) ** 2 + (2 * z * r) ** 2)
            X = np.column_stack([shape, np.ones_like(shape)])
            try:
                beta, *_ = np.linalg.lstsq(X, pp, rcond=None)
            except np.linalg.LinAlgError:
                continue
            if beta[0] <= 0 or beta[1] < 0:
                continue
            res = float(np.sum((pp - X @ beta) ** 2))
            if res < best[0]:
                best = (res, fn, z, float(beta[0]), float(beta[1]))
    _, fn, z, g, c = best
    if not np.isfinite(fn):
        return None
    peak = g / (2 * z) ** 2                      # 2-pole peak height
    return dict(fn=fn, zeta=z, peak=peak, floor=c, ratio=float(c / max(peak, 1e-30)))


def c_qbracket(routes):
    hdr("C1.  THE REAL BROADBAND BACKGROUND FRACTION in the T_s auto-spectrum, engaged hands-off")
    print("    Model: 2-pole peak + a FLAT floor.  `frac` = floor / peak height -- the quantity")
    print("    `studies/damping-q/ringdown_validate.py` section 5 had to GUESS (it assumed equal band power).")
    print("    🛑 RUN OVER TWO BANDS.  A free 4-16 Hz fit does NOT lock onto 8.16 Hz -- it lands on")
    print("       a ~12.4 Hz feature on four of five routes.  The bias that matters for the")
    print("       2026-08-20 number is the one AT 8.16 Hz, so a 6-11 Hz fit is carried alongside")
    print("       and it is the 6-11 Hz `frac` that is used in C2.")
    fr = None
    for blo, bhi, tag in ((4.0, 16.0, "FREE 4-16 Hz"), (6.0, 11.0, "TARGETED 6-11 Hz")):
        print("\n    --- %s ---" % tag)
        print("    %-12s %6s %8s %8s %10s %10s" % ("route", "nwin", "f_n", "zeta", "peak/floor",
                                                   "frac"))
        fracs = []
        for rt in routes:
            segs = []
            for blk in L.all_blocks(rt):
                lat = np.asarray(blk["cc_lat"], float) > 0.5
                x = np.asarray(blk["tq"], float)
                for i in range(0, len(x) - 512, 512):
                    if lat[i:i + 512].mean() >= 0.98 and \
                            np.percentile(np.abs(x[i:i + 512]), 90) < 300:
                        segs.append(x[i:i + 512])
            if len(segs) < 8:
                continue
            f, p = welch(np.concatenate(segs), fs=FS, nperseg=512, noverlap=256)
            r = twopole_plus_floor(f, p, blo, bhi)
            if not r:
                continue
            print("    %-12s %6d %8.2f %8.4f %10.3f %10.3f"
                  % (LAB.get(rt, rt), len(segs), r["fn"], r["zeta"], 1 / max(r["ratio"], 1e-9),
                     r["ratio"]))
            fracs.append(r["ratio"])
        if fracs:
            m = float(np.median(fracs))
            print("    median background fraction (floor / peak) = %.3f" % m)
            if tag.startswith("TARGETED"):
                fr = m
    if fr is None:
        print("    no route produced a 6-11 Hz fit")
        return

    hdr("C2.  THE 2-POLE PSD FIT'S BIAS AT THAT MEASURED CONTAMINATION -- the Q = 10.21 bracket")
    print("    White-noise-driven 2-pole of KNOWN zeta + a flat background at the MEASURED")
    print("    floor/peak = %.3f, 400 s at 100 Hz, Welch NFFT 512 -- the 2026-08-20 configuration."
          % fr)
    print("\n    %10s %14s %10s" % ("truth zeta", "recovered", "bias"))
    rows = {}
    for zt in (0.02, 0.035, 0.049, 0.07, 0.10, 0.15):
        got = []
        for r in range(10):
            rng = np.random.default_rng(700 + r)
            n = int(400 * FS)
            wn = 2 * np.pi * FN / FS
            rr = np.exp(-zt * wn)
            a = [1.0, -2 * rr * np.cos(wn * np.sqrt(max(1 - zt ** 2, 1e-9))), rr ** 2]
            x = lfilter([1.0], a, rng.normal(0, 1, n))
            x = x / np.std(x) * 400.0
            f_, p_ = welch(x, fs=FS, nperseg=512, noverlap=256)
            pk = float(np.max(p_[(f_ >= 6) & (f_ <= 11)]))
            noise = rng.normal(0, 1, n)
            noise = noise / np.std(noise) * np.sqrt(pk * fr * FS / 2)
            _, z_ = RV.e4_twopole_psd(x + noise, FS, nfft=512)
            if np.isfinite(z_):
                got.append(z_)
        m = float(np.median(got)) if got else np.nan
        print("    %10.4f %14.4f %10.2fx" % (zt, m, m / zt))
        rows["%.3f" % zt] = m
    print("\n    🛑 INVERT THIS FOR THE REPORTED 0.0490:")
    ks = sorted(rows, key=lambda k: rows[k])
    tv = [float(k) for k in ks]
    rv = [rows[k] for k in ks]
    if all(np.isfinite(rv)):
        true049 = float(np.interp(0.0490, rv, tv))
        print("       recovered 0.0490  =>  TRUE zeta ~ %.4f  =>  TRUE Q ~ %.1f"
              % (true049, 1 / (2 * true049)))
        print("       (the reported figure was zeta 0.0490 / Q 10.21)")
    print("    Direction of the bias, as established: a background INFLATES the fitted zeta, so")
    print("    the true mode is LESS damped than reported and Q is UNDERSTATED, not overstated.")


def main():
    routes = [r for r in ("97", "9e", "96", "73", "85", "95") if reg(r)]
    edges = collect_edges(routes, 3.0, 3.0)
    print("real disengage edges available for the sensitivity sweep: %d" % len(edges))
    a_sensitivity(edges)
    b_route97()
    c_qbracket(routes)


if __name__ == "__main__":
    main()
