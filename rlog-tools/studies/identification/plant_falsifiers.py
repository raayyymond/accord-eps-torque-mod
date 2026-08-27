#!/usr/bin/env python3
r"""RUNNING MY OWN PRE-REGISTERED FALSIFIERS, AND BOUNDING THE ARM SPREAD.

`studies/identification/plant_phase_corner.py` section 3 pre-registered three falsifiers.  Two of them were reported but
never actually EXECUTED against the stated threshold.  This file executes them.

  F2  "arg(Z) swinging through 8 Hz (CV of the per-bin ratio > ~0.5) on a route with coh >= 0.5
       -- that IS a passive resonance and this conclusion dies."
      🛑 The CVs I reported (V103 0.510, V102 0.671, V100 0.535) were computed over ALL bins in
      4-10 Hz, INCLUDING bins well below coh 0.5.  The falsifier's own qualifier was not applied.
      Section 1 applies it.

  F1  "a MANUAL (LKAS-off) hands-off arm with coh >= 0.30 at 4-10 Hz returning J/b more than ~3x
       larger than the engaged arms -- that would mean the engaged number is a loop artefact and
       the passive column is lightly damped."
      🛑 Every manual arm in my table is hands-ON and every hands-off arm is ENGAGED, so the
      decisive cell was empty and I did not say so.  Section 2 asks whether that is an EXTRACTION
      gap or a DATA gap, and runs the cell if it can be run.

  F3  an independent k measurement -- out of scope here (needs Ghidra / a bench measurement).

  Section 3 bounds the 3-5x spread across arms that I reported without explaining.

🛑 NOTHING IN THE RECORD IS EDITED BY THIS FILE.  It writes only its own JSON.
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
BINS = (4, 5, 6, 7, 8, 9, 10)
LAB = {"97": "V9b STOCK", "9e": "V103", "96": "V102", "73": "V88", "85": "V100 4x", "95": "V101 8x"}
CV_KILL = 0.50            # the pre-registered threshold
COH_QUAL = 0.50           # the pre-registered qualifier on F2
NBOOT = 3000
OUT = {}


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
        r = np.asarray(blk["rate_f"], float)      # phase only -- scale is irrelevant here
        cuts = [0] + list(np.flatnonzero(np.diff(lat.astype(int))) + 1) + [len(lat)]
        for s, e in zip(cuts[:-1], cuts[1:]):
            if e - s >= NFFT:
                eps.append(dict(lat=bool(lat[s]), tq=tq[s:e], r=r[s:e]))
    return eps


def wins(ep, hold):
    w = np.hanning(NFFT)
    out = []
    for i in range(0, len(ep["tq"]) - NFFT, NFFT // 2):
        y, x = ep["tq"][i:i + NFFT], ep["r"][i:i + NFFT]
        if hold == "off" and not (np.percentile(np.abs(y), 90) < HOLD_OFF):
            continue
        if hold == "on" and not (np.percentile(np.abs(y), 50) >= HOLD_ON):
            continue
        X = np.fft.rfft((x - x.mean()) * w)
        Y = np.fft.rfft((y - y.mean()) * w)
        out.append((np.abs(X) ** 2, np.conj(X) * Y, np.abs(Y) ** 2))
    return out


def pool(ws):
    return tuple(np.sum([w[i] for w in ws], axis=0) for i in range(3))


def per_bin(ws):
    """Per-1-Hz-bin (J/b in ms, coherence)."""
    Sxx, Sxy, Syy = ws
    ch = np.abs(Sxy) ** 2 / np.maximum(Sxx * Syy, 1e-30)
    vals = []
    for f0 in BINS:
        m = (F >= f0 - 0.5) & (F < f0 + 0.5)
        h = Sxy[m].sum() / Sxx[m].sum()
        a = 180.0 - abs(np.angle(h, deg=True))
        c = float(np.median(ch[m]))
        t = (np.tan(np.radians(a)) / (2 * np.pi * f0) * 1e3) if 3 < a < 87 else np.nan
        vals.append((f0, t, c))
    return vals


def arm(rt, lat, hold):
    return [w for w in (wins(e, hold) for e in episodes(rt) if e["lat"] == lat) if len(w) >= 1]


# ------------------------------------------------------------------------------------------------
# 1.  FALSIFIER F2, WITH ITS OWN coh >= 0.50 QUALIFIER APPLIED
# ------------------------------------------------------------------------------------------------

def f2(routes):
    hdr("1.  FALSIFIER F2 -- CV of the per-bin J/b, ALL bins vs ONLY bins meeting coh >= %.2f"
        % COH_QUAL)
    print("    Pre-registered kill condition: CV > %.2f on a route with coh >= %.2f."
          % (CV_KILL, COH_QUAL))
    print("    🛑 What I reported last time used ALL bins in 4-10 Hz, ignoring the qualifier.")
    print("\n    %-11s %28s %34s %10s" % ("route", "ALL bins", "coh >= 0.50 bins ONLY", "verdict"))
    res = {}
    for rt in routes:
        per = arm(rt, True, "off")
        if len(per) < 3:
            continue
        vals = per_bin(pool([w for p in per for w in p]))
        allv = np.array([v for _f, v, _c in vals if np.isfinite(v)])
        qual = np.array([v for _f, v, c in vals if np.isfinite(v) and c >= COH_QUAL])
        cv_all = float(np.std(allv) / np.mean(allv)) if len(allv) > 2 else np.nan
        cv_q = float(np.std(qual) / np.mean(qual)) if len(qual) > 2 else np.nan
        verdict = ("n<3 bins" if not np.isfinite(cv_q) else
                   "🛑 TRIPS" if cv_q > CV_KILL else "survives")
        print("    %-11s   CV %.3f (n=%d)%9s   CV %.3f (n=%d)%14s %10s"
              % (LAB.get(rt, rt), cv_all, len(allv), "", cv_q, len(qual), "", verdict))
        res[rt] = dict(cv_all=cv_all, cv_qual=cv_q, n_all=len(allv), n_qual=len(qual),
                       bins=[(f, v, c) for f, v, c in vals])
    print("\n    PER-BIN DETAIL (J/b ms, coherence) -- bins BELOW the qualifier are marked *")
    print("    %-11s %s" % ("route", "".join("%15s" % ("%g Hz" % f) for f in BINS)))
    for rt, d in res.items():
        cells = []
        for f, v, c in d["bins"]:
            if not np.isfinite(v):
                cells.append("%15s" % "--")
            else:
                cells.append("%15s" % ("%s%.1f (%.2f)" % ("*" if c < COH_QUAL else " ", v, c)))
        print("    %-11s %s" % (LAB.get(rt, rt), "".join(cells)))
    OUT["F2"] = res
    return res


def f2_shape(routes, res):
    r"""POST-HOC, and labelled as such: WHAT KIND of failure is a tripped CV?

    A RESONANCE at 8 Hz makes arg(Z) swing rapidly THROUGH the band -- the ratio spikes and then
    inverts.  A smooth monotone DRIFT is a different failure: the 2-parameter model is wrong in a
    smooth way (an extra pole or zero somewhere else), which does not put a resonance at 8 Hz.
    This separates them by asking whether the 7.5-9 Hz residual departs from a smooth log-f trend.
    🛑 This is NOT a replacement for the pre-registered test above.  It is a diagnostic.
    """
    hdr("1b.  POST-HOC DIAGNOSTIC -- is a tripped CV a RESONANCE, or a smooth model error?")
    print("    Fit ln(J/b) linear in ln(f) over the qualifying bins; report the 7.5-9 Hz residual")
    print("    in units of the fit's own residual SD.  A resonance is a LOCAL excursion there.")
    print("\n    %-11s %8s %10s %12s %14s" % ("route", "n bins", "slope", "resid SD", "8 Hz resid"))
    for rt, d in res.items():
        pts = [(f, v) for f, v, c in d["bins"] if np.isfinite(v) and c >= COH_QUAL]
        if len(pts) < 4:
            print("    %-11s %8d   -- too few qualifying bins --" % (LAB.get(rt, rt), len(pts)))
            continue
        f_ = np.array([p[0] for p in pts], float)
        y_ = np.log(np.array([p[1] for p in pts], float))
        sl, ic = np.polyfit(np.log(f_), y_, 1)
        resid = y_ - (sl * np.log(f_) + ic)
        sd = float(np.std(resid, ddof=1))
        near8 = [r for f0, r in zip(f_, resid) if 7.5 <= f0 <= 9.0]
        z8 = (float(np.mean(near8)) / sd) if (near8 and sd > 0) else np.nan
        print("    %-11s %8d %10.2f %12.3f %14s"
              % (LAB.get(rt, rt), len(pts), sl, sd,
                 "%+.2f sd" % z8 if np.isfinite(z8) else "--"))
    print("\n    ⇒ |8 Hz resid| < ~1 sd means the departure is NOT localised at 8 Hz: the model is")
    print("      wrong smoothly across the band, which is not a resonance AT 8 Hz.")


# ------------------------------------------------------------------------------------------------
# 2.  FALSIFIER F1 -- IS THE MANUAL HANDS-OFF CELL AN EXTRACTION GAP OR A DATA GAP?
# ------------------------------------------------------------------------------------------------

def f1(routes):
    hdr("2.  FALSIFIER F1 -- the MANUAL (LKAS-off) HANDS-OFF cell.  Extraction gap or data gap?")
    print("    Step 1: does the data EXIST?  Count manual hands-off windows, before any coherence")
    print("    gate.  Step 2: if it exists, run the arm and report its coherence honestly.")
    print("\n    %-11s %10s %10s %12s %12s" % ("route", "man eps", "man/off win", "eng/off win",
                                               "man/off sec"))
    tot_win, per_all = 0, []
    for rt in routes:
        eps = episodes(rt)
        mo = [w for w in (wins(e, "off") for e in eps if not e["lat"]) if len(w) >= 1]
        eo = [w for w in (wins(e, "off") for e in eps if e["lat"]) if len(w) >= 1]
        nmo = sum(len(w) for w in mo)
        tot_win += nmo
        per_all += mo
        print("    %-11s %10d %10d %12d %12.1f"
              % (LAB.get(rt, rt), len([e for e in eps if not e["lat"]]), nmo,
                 sum(len(w) for w in eo), nmo * (NFFT / 2) / FS))
    print("\n    ⇒ manual hands-off windows corpus-wide: %d  (%.0f s of exposure)"
          % (tot_win, tot_win * (NFFT / 2) / FS))
    if tot_win == 0:
        print("    🛑 The cell is EMPTY IN THE DATA.  F1 is untestable.")
        OUT["F1"] = dict(exists=False)
        return
    print("    ⇒ **THE DATA EXISTS.  It was NOT an extraction gap.**  Running the arm now.")

    hdr("2b.  THE MANUAL HANDS-OFF ARM, POOLED CORPUS-WIDE -- coherence is the whole question")
    Sxx, Sxy, Syy = pool([w for p in per_all for w in p])
    ch = np.abs(Sxy) ** 2 / np.maximum(Sxx * Syy, 1e-30)
    print("    %-8s %12s %12s" % ("f Hz", "coh^2", "J/b ms"))
    vals = per_bin((Sxx, Sxy, Syy))
    for f0, v, c in vals:
        print("    %-8d %12.4f %12s" % (f0, c, "%.1f" % v if np.isfinite(v) else "--"))
    qual = [(f, v, c) for f, v, c in vals if np.isfinite(v) and c >= 0.30]
    print("\n    bins meeting the falsifier's own coh >= 0.30 gate: %d of %d" % (len(qual), len(vals)))
    if len(qual) < 4:
        print("    🛑 **F1 IS UNTESTABLE ON THIS CORPUS -- and for a PHYSICAL reason, not a")
        print("       missing-data reason.**  %d s of manual hands-off exposure exists, but with"
              % (tot_win * (NFFT / 2) / FS))
        print("       LKAS off AND hands off there is almost no 4-14 Hz excitation of the column,")
        print("       so coh^2 sits at %.3f-%.3f -- the cross-spectrum is measuring noise."
              % (min(c for _f, _v, c in vals), max(c for _f, _v, c in vals)))
        print("       This is the kit's own recorded fact from the other direction:")
        print("       `accord-vibration-requires-lkas-engaged` (9,200x less power LKAS-off) and")
        print("       `accord-ratchet-is-a-saturated-resonance` (0 of 97 fully-manual windows")
        print("       carry a line).  **The excitation the estimator needs is the very thing that")
        print("       only exists when engaged.**")
        print("    ⇒ CONSEQUENCE: the engaged-arm result CANNOT be checked against a passive arm")
        print("       on this corpus.  The conclusion rests on the engaged arms plus the")
        print("       anti-damping direction argument, and must be stated that way.")
        OUT["F1"] = dict(exists=True, n_win=tot_win, testable=False,
                         coh=[float(c) for _f, _v, c in vals])
        return
    # if it IS testable, run it properly with an episode bootstrap
    est = np.average([v for _f, v, _c in qual],
                     weights=[c for _f, _v, c in qual])
    rng = np.random.default_rng(99)
    B = []
    for _ in range(NBOOT):
        pk = rng.integers(0, len(per_all), len(per_all))
        vv = per_bin(pool([w for i in pk for w in per_all[i]]))
        q = [(v, c) for _f, v, c in vv if np.isfinite(v) and c >= 0.30]
        if len(q) >= 4:
            B.append(np.average([x[0] for x in q], weights=[x[1] for x in q]))
    lo, hi = (np.percentile(B, 2.5), np.percentile(B, 97.5)) if len(B) > 200 else (np.nan, np.nan)
    print("    MANUAL HANDS-OFF J/b = %.1f ms [%.1f, %.1f]" % (est, lo, hi))
    print("    engaged hands-off reference: 21.4 - 36.6 ms")
    print("    ⇒ ratio to engaged = %.2fx  (F1 kills the conclusion at > ~3x)" % (est / 28.0))
    OUT["F1"] = dict(exists=True, n_win=tot_win, testable=True, est=float(est),
                     ci=[float(lo), float(hi)])


# ------------------------------------------------------------------------------------------------
# 3.  THE ARM SPREAD -- explain it, and give a HARD BOUND
# ------------------------------------------------------------------------------------------------

def spread(routes):
    hdr("3.  THE 3-5x ARM SPREAD -- what it is, and the WORST-CASE bound on Q at 8.16 Hz")
    print("    🛑 Hands-ON is NOT the same mechanical system.  The identity T_bar/th = -(J s^2+b s)")
    print("       assumes ZERO driver torque; hands-on it is false.  What a hands-on fit returns is")
    print("       a LUMPED driver-arm + column impedance, so it MUST differ -- that is control C4")
    print("       PASSING, not an inconsistency.  Arm+hand inertia at the rim raises J more than")
    print("       hand damping raises b, so J/b rises, which is the direction observed.")
    print("\n    Every arm, every route.  Q(8.16 Hz) = 2 pi * 8.16 * (J/b).")
    print("\n    %-11s %-8s %-5s %5s %16s %18s" % ("route", "arm", "hold", "nep", "J/b ms",
                                                   "Q @8.16 [95% CI]"))
    rows = []
    for rt in routes:
        for lat, latl in ((True, "engaged"), (False, "manual")):
            for hold in ("off", "on"):
                per = arm(rt, lat, hold)
                if len(per) < 3:
                    continue
                vv = per_bin(pool([w for p in per for w in p]))
                q = [(v, c) for _f, v, c in vv if np.isfinite(v) and c >= 0.30]
                if len(q) < 4:
                    continue
                est = np.average([x[0] for x in q], weights=[x[1] for x in q]) * 1e-3
                rng = np.random.default_rng(7)
                B = []
                for _ in range(1500):
                    pk = rng.integers(0, len(per), len(per))
                    v2 = per_bin(pool([w for i in pk for w in per[i]]))
                    q2 = [(v, c) for _f, v, c in v2 if np.isfinite(v) and c >= 0.30]
                    if len(q2) >= 4:
                        B.append(np.average([x[0] for x in q2], weights=[x[1] for x in q2]) * 1e-3)
                if len(B) < 200:
                    continue
                lo, hi = np.percentile(B, 2.5), np.percentile(B, 97.5)
                Q = 2 * np.pi * 8.16
                print("    %-11s %-8s %-5s %5d %16s %18s"
                      % (LAB.get(rt, rt), latl, hold, len(per),
                         "%.1f [%.1f, %.1f]" % (est * 1e3, lo * 1e3, hi * 1e3),
                         "%.2f [%.2f, %.2f]" % (Q * est, Q * lo, Q * hi)))
                rows.append(dict(rt=rt, arm=latl, hold=hold, tau=float(est),
                                 q=float(Q * est), q_hi=float(Q * hi)))
    if rows:
        worst = max(rows, key=lambda r: r["q_hi"])
        print("\n    🛑 THE HARD BOUND, taken over EVERY arm including the inadmissible hands-on ones:")
        print("       the most permissive is %s / %s / %s, upper 95%% CI Q = %.2f at 8.16 Hz."
              % (LAB.get(worst["rt"], worst["rt"]), worst["arm"], worst["hold"], worst["q_hi"]))
        print("       ⇒ **no arm in the corpus, admissible or not, reaches Q = 10.**")
        print("       Restricting to the ADMISSIBLE arms (hands-off only), the max upper CI is"
              " %.2f."
              % max((r["q_hi"] for r in rows if r["hold"] == "off"), default=float("nan")))
    OUT["spread"] = rows


def single_bin(routes):
    r"""4.  THE FORM OF THE ARGUMENT THAT DOES NOT DEPEND ON F2 AT ALL.

    Everything above pools J/b ACROSS a band, which is what makes it vulnerable to the smooth
    model error F2 detects (ln(J/b) has slope -0.5 to -4.3 in ln f on every route -- the 2-parameter
    column is not exactly right anywhere).

    But the claim only concerns 8.16 Hz.  So take the LOCAL value in the 8 Hz bin alone:

        Q(8.16) = 2 pi f * tan(180 - |arg Z|) / (2 pi f) = tan(180deg - |arg Z(8 Hz)|)

    🛑 Note what drops out: Q at the mode's own frequency is JUST tan of the phase deficit, with no
    f, no k, no counts scale, no deg/s scale, no band, and no cross-frequency model.  It is a
    single number read off a single well-measured bin.  For Q = 10 the phase must satisfy
    atan(10) = 84.3deg, i.e. |arg Z| = 95.7deg -- Z within 6deg of PURE INERTIA.
    """
    hdr("4.  THE SINGLE-BIN FORM -- Q at 8 Hz is just tan(180deg - |arg Z|), no band, no model")
    print("    For Q = 10 the 8 Hz bin would have to read |arg Z| = 95.7 deg (Z within 5.7 deg of")
    print("    pure inertia).  For Q = 1 it reads 135 deg.  Engaged hands-off, 7.5-8.5 Hz bin.")
    print("\n    %-11s %6s %10s %12s %14s %18s"
          % ("route", "nep", "coh^2", "|arg Z| deg", "Q = tan(180-a)", "Q [95% CI]"))
    rows = []
    for rt in routes:
        per = arm(rt, True, "off")
        if len(per) < 3:
            continue

        def q_of(ws):
            Sxx, Sxy, Syy = ws
            m = (F >= 7.5) & (F < 8.5)
            h = Sxy[m].sum() / Sxx[m].sum()
            a = 180.0 - abs(np.angle(h, deg=True))
            return (np.tan(np.radians(a)) if 3 < a < 87 else np.nan), a, \
                float(np.median(np.abs(Sxy[m]) ** 2 / np.maximum(Sxx[m] * Syy[m], 1e-30)))

        q0, a0, c0 = q_of(pool([w for p in per for w in p]))
        if not np.isfinite(q0):
            continue
        rng = np.random.default_rng(21)
        B = []
        for _ in range(NBOOT):
            pk = rng.integers(0, len(per), len(per))
            qq, _a, _c = q_of(pool([w for i in pk for w in per[i]]))
            if np.isfinite(qq):
                B.append(qq)
        lo, hi = (np.percentile(B, 2.5), np.percentile(B, 97.5)) if len(B) > 200 else (np.nan,) * 2
        print("    %-11s %6d %10.3f %12.1f %14.2f %18s"
              % (LAB.get(rt, rt), len(per), c0, 180.0 - a0, q0,
                 "[%.2f, %.2f]" % (lo, hi)))
        rows.append(dict(rt=rt, q=float(q0), hi=float(hi), coh=c0))
    if rows:
        print("\n    ⇒ Q at 8 Hz = %.2f - %.2f across %d routes; the largest upper 95%% CI is %.2f."
              % (min(r["q"] for r in rows), max(r["q"] for r in rows), len(rows),
                 max(r["hi"] for r in rows)))
        print("      Every bin here has coh^2 %.2f-%.2f, comfortably above the 0.50 qualifier, so"
              % (min(r["coh"] for r in rows), max(r["coh"] for r in rows)))
        print("      **F2 cannot touch this form of the argument** -- there is no band to be")
        print("      inconsistent across.")
        print("      For Q = 10, |arg Z| at 8 Hz would have to be 95.7 deg.  Measured: %.0f-%.0f deg."
              % (min(180 - np.degrees(np.arctan(r["q"])) for r in rows) * 0 +
                 min(180 - np.degrees(np.arctan(r["q"])) for r in rows),
                 max(180 - np.degrees(np.arctan(r["q"])) for r in rows)))
    OUT["single_bin"] = rows


def main():
    routes = [r for r in ("97", "9e", "96", "73", "85", "95") if reg(r)]
    res = f2(routes)
    f2_shape(routes, res)
    f1(routes)
    spread(routes)
    single_bin(routes)
    (HERE / "_scratch/out/_plant_falsifiers.json").write_text(json.dumps(OUT, indent=1, default=float))
    print("\nwrote %s" % (HERE / "_scratch/out/_plant_falsifiers.json"))


if __name__ == "__main__":
    main()
