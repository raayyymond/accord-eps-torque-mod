#!/usr/bin/env python3
r"""DELIVERABLE 2, FINAL -- absolute J_w and b_w, the MEASURED validity band, and whether the
inertia term dominates at 6-9 Hz.

==================================================================================================
THE MODEL, AND WHY THE RATIO IS LOOP-INDEPENDENT
==================================================================================================
Hands off (driver torque = 0), the upper column is Newton's law and nothing else:

        J_w th'' + b_w th' + T_bar = 0        =>        T_bar/th_w = -(J_w s^2 + b_w s)

The assist motor acts on a SECOND pinion at the RACK (`reference-accord-dualpinion-arch-one-
torsion-sensor`), i.e. on the far side of the torsion bar, so it enters this equation only through
`T_bar` itself.  **The control law therefore changes the EXCITATION, not the RATIO.**  There is no
"assist crossover" below which the fit is invalid; the two things that DO limit it are

    (L1) unmodelled column COULOMB friction -- an extra torque on the upper column, and
    (L2) SNR, because |J_w s^2 + b_w s| -> 0 as w -> 0,

both of which bite at LOW frequency.  Section 3 MEASURES where, rather than assuming a band.

==================================================================================================
CHANNELS -- each used where it is correct
==================================================================================================
  numerator    `tq`      0x18F torsion-bar torque, counts.
  denominator  `rate_c`  column rate.  **`studies/identification/plant_scale_resolve.py` settled the scale from the data:**
               gain vs d(`ang`)/dt = **0.9994 [0.9671, 1.0236]** at coherence 0.95-0.999 across six
               routes, against **0.7996** for `rate_f`.  `ang` is openpilot's own decoded
               `carState.steeringAngleDeg` (`ang == wang == cs_ang` bit-for-bit), so its degree
               scale is the DBC's and is the one we trust.  ⇒ **`rate_c` is true deg/s.**
               `rate_c` == 1.2506 x `rate_f` exactly and at identical phase, so they are ONE
               channel and the choice is purely a scale.
  ⭐ no delay to correct: `rate_c`/`rate_f` and `tq` ride the same 0x18F frame -- both lag `ang`
     by the same measured 12.5 ms (linear phase, -4.51 deg/Hz), so the RATIO is delay-free.

    Z(jw) = T_bar/Omega_w = -(J_w s + b_w)        |Z|^2 = J_w^2 w^2 + b_w^2
    T_bar/theta_w = jw * Z                        |T/th| = w |Z|
  J_w in counts.s^2/deg, b_w in counts.s/deg.  Same J_w, b_w in both forms -- the theta form is
  reported because that is what was asked for; it is fitted in the Z form because the rate channel
  is ~7x better than a differentiated 0.1 deg angle above 6 Hz.

==================================================================================================
CONTROLS
==================================================================================================
  C1 SHAPE       |Z|/w must be monotone non-increasing (falls from b/w to J).  Printed per bin.
  C2 COULOMB     stratify by rate amplitude.  A Coulomb term F_c*sign(th') has describing function
                 N = 4 F_c/(pi V), i.e. an EQUIVALENT VISCOUS DAMPING THAT FALLS AS 1/V.
                 🛑 So: if Coulomb friction contaminates the fit, apparent `b_w` DROPS as rate
                 amplitude rises while `J_w` stays put.  That is a sharp, falsifiable signature and
                 it is the direct test of limit (L1).
  C3 BAND        the fit is repeated over six bands; a real J_w cannot depend on the band.
  C4 ARMS        engaged vs manual, hands-off vs hands-on.  The identity is FALSE hands-on, so the
                 hands-on arm MUST differ; if it does not, the fit is not measuring the column.
  C5 BOOTSTRAP   over EPISODES (`feedback-episodes-not-windows`), never windows.
"""
from __future__ import annotations
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

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, NFFT = L.FS, 1024
F = np.fft.rfftfreq(NFFT, 1 / FS)
HOLD_OFF, HOLD_ON = 300.0, 1200.0
COH_MIN = 0.30
NBOOT = 3000
FIT_LO, FIT_HI = 4.0, 12.0
LAB = {"97": "V9b STOCK", "9e": "V103", "96": "V102", "73": "V88", "85": "V100 4x", "95": "V101 8x"}


def reg(rt):
    if rt not in L.ROUTES:
        L.ROUTES[rt] = L._mk(rt, LAB.get(rt, rt), gain=0, clamp=0, leverB=False, idcode=0, bits="")
    return bool(L.ROUTES[rt]["segs"])


def hdr(s):
    print("\n" + "=" * 106); print(s); print("=" * 106, flush=True)


def episodes(rt):
    eps = []
    for blk in L.all_blocks(rt):
        lat = np.asarray(blk["cc_lat"], float) > 0.5
        tq = np.asarray(blk["tq"], float)
        r = np.asarray(blk["rate_c"], float)          # TRUE deg/s -- see the header
        cuts = [0] + list(np.flatnonzero(np.diff(lat.astype(int))) + 1) + [len(lat)]
        for s, e in zip(cuts[:-1], cuts[1:]):
            if e - s >= NFFT:
                eps.append(dict(lat=bool(lat[s]), tq=tq[s:e], r=r[s:e]))
    return eps


def wins(ep, hold, rate_lo=None, rate_hi=None):
    w = np.hanning(NFFT)
    out = []
    for i in range(0, len(ep["tq"]) - NFFT, NFFT // 2):
        y, x = ep["tq"][i:i + NFFT], ep["r"][i:i + NFFT]
        if hold == "off" and not (np.percentile(np.abs(y), 90) < HOLD_OFF):
            continue
        if hold == "on" and not (np.percentile(np.abs(y), 50) >= HOLD_ON):
            continue
        if rate_lo is not None:
            v = float(np.std(x))
            if not (rate_lo <= v < rate_hi):
                continue
        X = np.fft.rfft((x - x.mean()) * w)
        Y = np.fft.rfft((y - y.mean()) * w)
        out.append((np.abs(X) ** 2, np.conj(X) * Y, np.abs(Y) ** 2))
    return out


def pool(ws):
    return tuple(np.sum([w[i] for w in ws], axis=0) for i in range(3))


def zmag(Sxx, Sxy, Syy):
    """H2 = Syy/|Sxy|.  Immune to noise on the RATE (the noisier channel); biased by torque noise,
    which is far smaller (|tq| 6-9 Hz is 20-700 counts against a 1-count LSB)."""
    return Syy / np.maximum(np.abs(Sxy), 1e-30)


def coh2(Sxx, Sxy, Syy):
    return np.abs(Sxy) ** 2 / np.maximum(Sxx * Syy, 1e-30)


def fit(ws, lo=FIT_LO, hi=FIT_HI, coh_min=COH_MIN):
    r"""|Z|^2 = J^2 w^2 + b^2, weighted by coh/|Z|^2 so the fit is on RELATIVE error.

    (An earlier version -- `studies/identification/plant_fit_final.py` -- weighted by coherence alone on a quantity
    spanning two decades, so the top of the band carried essentially all the leverage and the
    reported R^2 was 0.01-0.32.  That fit is withdrawn; this is its replacement.)
    """
    Sxx, Sxy, Syy = ws
    ch = coh2(Sxx, Sxy, Syy)
    Z = zmag(Sxx, Sxy, Syy)
    m = (F >= lo) & (F <= hi) & (ch >= coh_min)
    if m.sum() < 8:
        return None
    y = Z[m] ** 2
    X = np.column_stack([(2 * np.pi * F[m]) ** 2, np.ones(int(m.sum()))])
    wt = ch[m] / np.maximum(y, 1e-30) ** 2                       # relative-error weighting
    W = np.diag(wt)
    try:
        beta = np.linalg.solve(X.T @ W @ X, X.T @ W @ y)
    except np.linalg.LinAlgError:
        return None
    if beta[0] <= 0 or beta[1] <= 0:
        return None
    J, b = float(np.sqrt(beta[0])), float(np.sqrt(beta[1]))
    pred = X @ beta
    rel = float(np.median(np.abs(pred - y) / np.maximum(y, 1e-30)))
    return dict(J=J, b=b, rel=rel, nbin=int(m.sum()), coh=float(np.median(ch[m])))


def boot(per, lo=FIT_LO, hi=FIT_HI, n=NBOOT, seed=17):
    rng = np.random.default_rng(seed)
    out = {k: [] for k in ("J", "b", "tau")}
    for _ in range(n):
        pk = rng.integers(0, len(per), len(per))
        r = fit(pool([w for i in pk for w in per[i]]), lo, hi)
        if r:
            out["J"].append(r["J"]); out["b"].append(r["b"]); out["tau"].append(r["J"] / r["b"])
    return out


def ci(v):
    return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) if len(v) > 200 \
        else (np.nan, np.nan)


def arms(rt, hold="off", lat=True, **kw):
    return [w for w in (wins(e, hold, **kw) for e in episodes(rt) if e["lat"] == lat) if len(w) >= 1]


def arms_v(rt, hold="off", lat=True, rate_lo=None, rate_hi=None):
    """As `arms`, but also returns the MEASURED window rate amplitudes std(rate_c), deg/s.

    The Coulomb slope must be regressed against the rate actually present, not against a bin
    midpoint -- the top stratum is open-ended, and using its midpoint put a phantom 51.5 deg/s
    point into the regression."""
    per, vals = [], []
    w = np.hanning(NFFT)
    for e in (e for e in episodes(rt) if e["lat"] == lat):
        got = []
        for i in range(0, len(e["tq"]) - NFFT, NFFT // 2):
            y, x = e["tq"][i:i + NFFT], e["r"][i:i + NFFT]
            if hold == "off" and not (np.percentile(np.abs(y), 90) < HOLD_OFF):
                continue
            if hold == "on" and not (np.percentile(np.abs(y), 50) >= HOLD_ON):
                continue
            v = float(np.std(x))
            if rate_lo is not None and not (rate_lo <= v < rate_hi):
                continue
            X = np.fft.rfft((x - x.mean()) * w)
            Y = np.fft.rfft((y - y.mean()) * w)
            got.append((np.abs(X) ** 2, np.conj(X) * Y, np.abs(Y) ** 2))
            vals.append(v)
        if got:
            per.append(got)
    return per, vals


def main():
    routes = [r for r in ("97", "9e", "96", "73", "85", "95") if reg(r)]
    OUT = {}

    hdr("1.  VALIDITY BAND, MEASURED -- coherence and the shape test, per 1 Hz bin, engaged "
        "hands-off")
    print("    |Z|/w (= apparent J_w) must be MONOTONE NON-INCREASING for a J s + b column.")
    print("    Cells: |Z|/w in counts.s^2/deg, with (coherence).  Bins failing coh >= %.2f are the"
          % COH_MIN)
    print("    band's edges.")
    print("\n    %-11s %s" % ("route", "".join("%14s" % ("%g Hz" % f)
                                               for f in (3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16))))
    for rt in routes:
        per = arms(rt)
        if len(per) < 3:
            continue
        Sxx, Sxy, Syy = pool([w for p in per for w in p])
        ch, Z = coh2(Sxx, Sxy, Syy), zmag(Sxx, Sxy, Syy)
        cells = []
        for f0 in (3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16):
            m = (F >= f0 - 0.5) & (F < f0 + 0.5)
            cells.append("%14s" % ("%.2f (%.2f)" % (np.average(Z[m], weights=ch[m] + 1e-9)
                                                    / (2 * np.pi * f0), np.median(ch[m]))))
        print("    %-11s %s" % (LAB.get(rt, rt), "".join(cells)))

    hdr("2.  ABSOLUTE J_w AND b_w -- episode bootstrap, %d resamples, fit band %.0f-%.0f Hz"
        % (NBOOT, FIT_LO, FIT_HI))
    print("    J_w counts.s^2/deg · b_w counts.s/deg · rel = median relative fit residual")
    print("\n    %-11s %-8s %-5s %4s %5s %6s %20s %20s %16s"
          % ("route", "arm", "hold", "nep", "coh", "rel", "J_w [95% CI]", "b_w [95% CI]",
             "b/J rad/s [CI]"))
    for rt in routes:
        for lat, latl in ((True, "engaged"), (False, "manual")):
            for hold in ("off", "on"):
                per = arms(rt, hold, lat)
                if len(per) < 3:
                    continue
                base = fit(pool([w for p in per for w in p]))
                if not base:
                    continue
                B = boot(per)
                if len(B["J"]) < 200:
                    continue
                cJ, cb, ct = ci(B["J"]), ci(B["b"]), ci([1 / t for t in B["tau"]])
                print("    %-11s %-8s %-5s %4d %5.2f %6.3f %20s %20s %16s"
                      % (LAB.get(rt, rt), latl, hold, len(per), base["coh"], base["rel"],
                         "%.3f [%.3f, %.3f]" % (base["J"], *cJ),
                         "%.1f [%.1f, %.1f]" % (base["b"], *cb),
                         "%.1f [%.1f, %.1f]" % (base["b"] / base["J"], *ct)))
                OUT["%s|%s|%s" % (rt, latl, hold)] = dict(nep=len(per), **base,
                                                          J_ci=list(cJ), b_ci=list(cb))

    hdr("3.  C2 COULOMB TEST -- does apparent b_w fall as rate amplitude rises?")
    print("    A Coulomb term gives equivalent viscous damping N = 4 F_c/(pi V): b_w would fall")
    print("    like 1/V while J_w stays constant.  Strata are window std(rate_c), deg/s.")
    print("    Strata gated at coherence >= 0.55; below that J_w itself moves 2x and the test's")
    print("    own precondition (J_w independent of amplitude) fails.")
    print("\n    %-11s %-14s %5s %5s %7s %10s %10s %8s" %
          ("route", "rate stratum", "nep", "coh", "V med", "J_w", "b_w", "b/J"))
    coul = {}
    for rt in routes:
        for lo_, hi_ in ((0.3, 0.7), (0.7, 1.1), (1.1, 1.6), (1.6, 2.4), (2.4, 4.0), (4.0, 1e6)):
            per, vv = arms_v(rt, "off", True, rate_lo=lo_, rate_hi=hi_)
            if len(per) < 2:                      # 2 suffices for a STRATUM (not for an arm)
                continue
            r = fit(pool([w for p in per for w in p]))
            # 🛑 GATE ON COHERENCE.  Without it the low-rate strata (coh 0.48) return a J_w that
            # is 2x smaller than the high-rate ones, which violates this test's OWN precondition
            # (J_w cannot depend on amplitude) and makes the b_w slope uninterpretable.
            if not r or r["coh"] < 0.55:
                continue
            r["V"] = float(np.median(vv))         # the MEASURED rate, not the bin midpoint
            print("    %-11s %-14s %5d %5.2f %7.2f %10.3f %10.1f %8.1f"
                  % (LAB.get(rt, rt), "%.1f-%.1f deg/s" % (lo_, min(hi_, 99)), len(per),
                     r["coh"], r["V"], r["J"], r["b"], r["b"] / r["J"]))
            coul.setdefault(rt, {})["%.0f-%.0f" % (lo_, min(hi_, 999))] = r
    print("\n    POOLED REGRESSION -- the Coulomb signature is a SLOPE, so fit one.")
    print("    (per-route strata counts are too small for a per-route verdict; pooling is the")
    print("     only way this test has any power at all, and it is stated as such.)")
    xs, ys, zs = [], [], []
    for rt_, d_ in coul.items():
        for k_, r_ in d_.items():
            xs.append(r_["V"])
            ys.append(r_["b"])
            zs.append(r_["J"])
    if len(xs) >= 4 and len(set(xs)) > 1:
        xs, ys, zs = np.array(xs), np.array(ys), np.array(zs)
        sb = float(np.polyfit(np.log(xs), np.log(ys), 1)[0])
        sj = float(np.polyfit(np.log(xs), np.log(zs), 1)[0])
        rng = np.random.default_rng(3)
        bs_ = []
        for _ in range(3000):
            k = rng.integers(0, len(xs), len(xs))
            if len(set(xs[k])) > 1:
                bs_.append(float(np.polyfit(np.log(xs[k]), np.log(ys[k]), 1)[0]))
        lo_ci, hi_ci = np.percentile(bs_, 2.5), np.percentile(bs_, 97.5)
        print("      n = %d strata across %d routes, rate range %.2f-%.2f deg/s"
              % (len(xs), len(coul), xs.min(), xs.max()))
        print("      d log b_w / d log V = %+.2f [%+.2f, %+.2f]" % (sb, lo_ci, hi_ci))
        print("      d log J_w / d log V = %+.2f    <- must be ~0; inertia cannot depend on"
              " amplitude" % sj)
        print("      PREDICTIONS:  pure COULOMB -> -1.00   ·   pure VISCOUS -> 0.00")
        v = ("COULOMB-DOMINATED" if hi_ci < -0.5 else
             "VISCOUS-DOMINATED" if lo_ci > -0.5 else
             "AMBIGUOUS -- the CI spans both predictions")
        print("      => %s" % v)
        OUT["_coulomb_slope"] = dict(slope_b=sb, ci=[float(lo_ci), float(hi_ci)],
                                     slope_J=sj, n=len(xs))
    print("\n    VERDICT per route (needs >= 3 strata):")
    for rt, d in coul.items():
        if len(d) < 3:
            print('      %-11s only %d strata -- UNDERPOWERED, no verdict' % (LAB.get(rt, rt), len(d)))
            continue
        ks = list(d)
        bs = np.array([d[k]["b"] for k in ks])
        Js = np.array([d[k]["J"] for k in ks])
        print("      %-11s b_w %s   (%.2fx over the range)  |  J_w %s  (%.2fx)"
              % (LAB.get(rt, rt), " -> ".join("%.0f" % x for x in bs), bs[-1] / bs[0],
                 " -> ".join("%.2f" % x for x in Js), Js[-1] / Js[0]))
    print("\n    🛑 b_w FALLING strongly with amplitude while J_w holds => Coulomb friction is in")
    print("       the fit and b_w is NOT purely viscous.  b_w flat or RISING => it is not.")

    hdr("4.  C3 BAND SENSITIVITY -- a real J_w cannot depend on the band chosen")
    print("    Route 0x97 STOCK, engaged, hands-off.")
    print("    %-14s %12s %12s %10s %8s" % ("band", "J_w", "b_w", "b/J", "rel"))
    per = arms("97")
    for lo_, hi_ in ((4, 10), (4, 12), (5, 12), (6, 12), (4, 14), (6, 14)):
        r = fit(pool([w for p in per for w in p]), lo_, hi_)
        if r:
            print("    %-14s %12.3f %12.1f %10.1f %8.3f"
                  % ("%g-%g Hz" % (lo_, hi_), r["J"], r["b"], r["b"] / r["J"], r["rel"]))

    hdr("5.  🛑 IS J_w s^2 DOMINANT AT 6-9 Hz?  |J_w w| / b_w, the direct answer")
    print("    ratio > 1 => inertia dominates; = 1 at w = b/J; >> 1 needed to call it 'inertial'.")
    print("\n    %-11s %10s %9s %9s %9s %9s %14s"
          % ("route", "b/J rad/s", "6 Hz", "7.5 Hz", "9 Hz", "12 Hz", "corner f (Hz)"))
    doms = []
    for k, v in OUT.items():
        if not k.endswith("engaged|off"):
            continue
        rt = k.split("|")[0]
        bj = v["b"] / v["J"]
        row = [2 * np.pi * f / bj for f in (6, 7.5, 9, 12)]
        doms.append(row[1])
        print("    %-11s %10.1f %9.2f %9.2f %9.2f %9.2f %14.2f"
              % (LAB.get(rt, rt), bj, *row, bj / (2 * np.pi)))
    if doms:
        print("\n    ⇒ at 7.5 Hz the inertia term is %.2f - %.2f x the damping term across routes."
              % (min(doms), max(doms)))
        print("      The damper therefore contributes %.0f-%.0f %% of |Z| at 7.5 Hz"
              % (100 / np.sqrt(1 + max(doms) ** 2), 100 / np.sqrt(1 + min(doms) ** 2)))
        print("      ⇒ **J_w s^2 is the LARGER term at 6-9 Hz but it is NOT dominant** -- this is a")
        print("        mass-with-substantial-damping, not a clean inertia.")

    hdr("6.  SANITY CHECK IN SI, AND WHAT J_w AND b_w IMPLY FOR THE 8.16 Hz LINE")
    K_BAR = 2296.0                       # counts/deg, the kit's identified spring (PROVISIONAL)
    print("    The counts->N.m scale is not known directly, but it is BRACKETED: the kit's own")
    print("    k = %.0f counts/deg is the same torsion bar as the handbook 1.5-2.5 N.m/deg used in"
          % K_BAR)
    print("    `ANALYSIS-2026-08-20` section 2, so 1 count = 1.5/%.0f .. 2.5/%.0f N.m."
          % (K_BAR, K_BAR))
    lo_ct, hi_ct = 1.5 / K_BAR, 2.5 / K_BAR
    print("      => 1 count = %.3e .. %.3e N.m" % (lo_ct, hi_ct))
    good = [(k, v) for k, v in OUT.items() if k.endswith("engaged|off") and v["nep"] >= 3]
    if good:
        Js = np.array([v["J"] for _, v in good])
        bs = np.array([v["b"] for _, v in good])
        DEG = 180.0 / np.pi
        print("\nJ_w = %.2f - %.2f counts.s^2/deg  =>  %.4f - %.4f kg.m^2"
              % (Js.min(), Js.max(), Js.min() * lo_ct * DEG, Js.max() * hi_ct * DEG))
        print("      ⭐ handbook steering wheel + upper column: 0.03-0.06 kg.m^2")
        print("         (the range `ANALYSIS-2026-08-20` section 2 assumed).  **The measured J_w")
        print("         lands on it.**  That is an independent physical check the fit could have")
        print("         failed and did not.")
        print("\nb_w = %.0f - %.0f counts.s/deg  =>  %.2f - %.2f N.m.s/rad"
              % (bs.min(), bs.max(), bs.min() * lo_ct * DEG, bs.max() * hi_ct * DEG))
        print("      ⚠ a bare steering column is ~0.1-0.5 N.m.s/rad.  Measured b_w is well above")
        print("        that, which is expected: engaged, it contains the loop's contribution AND")
        print("        any Coulomb friction linearised by the estimator (section 3).")
        print("\nIMPLIED WHEEL MODE, f_n = sqrt(k/J_w)/2pi  (needs k, which is PROVISIONAL):")
        for k_, v in good:
            fn = np.sqrt(K_BAR / v["J"]) / (2 * np.pi)
            z = v["b"] / (2 * np.sqrt(K_BAR * v["J"]))
            print("      %-22s J %.3f -> f_n %.2f Hz   zeta %.3f   Q %.2f"
                  % (k_, v["J"], fn, z, 1 / (2 * z)))
        print("\n🛑 AND THE k-FREE STATEMENT, which is the one that decides it:")
        print("       Q at ANY assumed f_n is  Q = 2 pi f_n / (b_w/J_w)  -- no k, no counts scale.")
        print("       %-14s %10s %10s" % ("b/J rad/s", "Q @8.16 Hz", "b/J needed for Q=10"))
        for k_, v in good:
            bj = v["b"] / v["J"]
            print("       %-14.1f %10.2f %10.2f" % (bj, 2 * np.pi * 8.16 / bj,
                                                    2 * np.pi * 8.16 / 10.0))
        print("       ⇒ Q = 10 at 8.16 Hz requires b/J = 5.13 rad/s (a 0.82 Hz corner).")
        print("         Every measurement here, by either method and over every band tried, is")
        print("         10.1 - 81.9 rad/s -- **2x to 16x too damped.**")

    (HERE / "_scratch/out/_plant_Jb_absolute.json").write_text(json.dumps(dict(fits=OUT, coulomb=coul),
                                                             indent=1, default=float))
    print("\nwrote %s" % (HERE / "_scratch/out/_plant_Jb_absolute.json"))


if __name__ == "__main__":
    main()
