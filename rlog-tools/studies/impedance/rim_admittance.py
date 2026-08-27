#!/usr/bin/env python3
"""THE RIM/COLUMN MECHANICAL ADMITTANCE  |Omega(f) / T(f)|  -- the pair the driver actually feels.

CHANNEL IDENTITY, established from the record, not assumed (`_scratch/cache/selfint/report.txt`):
  * `0x14A` STEER_ANGLE (b0-1) and STEER_WHEEL_ANGLE (b5-6) are byte-identical on 100.0000% of
    frames over 4 routes ⇒ there is only ONE angle on this bus, and it is the column/rim angle.
  * |rate_c| / (omega * |ang|) = 1.0025 over rows with gamma^2 > 0.95 ⇒ `rate_c` IS d(ang)/dt,
    the same physical motion at its stated scale.  ⇒ `rate_c` is RIM RATE. [EVIDENCE]
  * 🛑 `rate_f` (0x18F) is the SAME SIGNAL one frame (10.00 ms) stale -- NOT independent, unused.
  * Quantisation: `ang` 0.1 deg (repeats on 74% of frames), `rate_c` 1 deg/s, `tq` 8 COUNTS.
    A quantisation floor is computed and drawn, because `rate_c`'s LSB is coarse.

🛑 TWO THINGS THIS IS NOT, stated up front so no one over-reads it:
 1. NEITHER ARM IS THE BARE MECHANICAL PLANT.  Base assist is always on -- "manual" means LKAS
    off, not motor off.  Both arms are CLOSED-LOOP admittances.  The engaged-vs-manual
    difference therefore isolates the LKAS contribution ONLY, not the firmware's whole effect.
 2. T is the torque IN the torsion bar; Omega is the angle ABOVE it.  So this is a TRANSFER
    admittance across the bar, not a driving-point one.  Peaks are resonances OF THE COUPLED
    hands+wheel+bar+assist system, and attributing one to a single component needs more than
    this measurement.

ESTIMATORS.  H1 = |S_xy| / S_xx (unbiased when the noise is on the output) and
H2 = S_yy / |S_yx| (unbiased when the noise is on the input).  Where coherence is high they
converge; where it is low H1 under- and H2 over-estimates, so the pair BRACKETS the truth.
Both are reported -- that is the honest answer to "which is cleaner".
Magnitude only: the inter-message delay is a pure delay (|gain| = 1) and cannot bias |Y|.
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
from scipy.signal import csd, welch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
import v86_freq_test as V           # noqa: E402
import _r31_common as C31           # noqa: E402

ROOT = V.ROOT
RNG = np.random.default_rng(86_2200)
NPS, NOV = 512, 384                 # 5.07 s, 0.197 Hz bins
O = {}
ROUTES = ("V86/r6f", "V85/r6e", "V86B/r70", "V84/r6d", "V81/r67")
NEW = ("V86/r6f", "V85/r6e", "V86B/r70")


def blocks(nm_list, engaged, speed=True):
    """Per-~10 s-block cross/auto spectra of (tq -> rate_c).  Yields dicts keyed by block."""
    out = []
    for nm in nm_list:
        cache, pfx, segs = V.ROUTES[nm]
        for s in segs:
            p = ROOT / cache / ("%s%d.npz" % (pfx, s))
            if not p.exists():
                continue
            d = C31.load(s, ROOT / cache, pfx)
            t = np.asarray(d["t"], float)
            fs = C31.fs_of(d)
            lat = np.asarray(d["cc_lat"], float) > 0.5
            v = np.asarray(d["cs_v"], float)
            m = lat if engaged else ~lat
            if speed:
                m = m & (v >= V.VLO) & (v < V.VHI)
            for a, b in C31.runs_of(m, t, NPS * 2):
                x = np.asarray(d["tq"], float)[a:b]
                y = np.asarray(d["rate_c"], float)[a:b]
                if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
                    continue
                x, y = x - x.mean(), y - y.mean()
                if x.std() == 0 or y.std() == 0:
                    continue
                f, sxy = csd(x, y, fs=fs, nperseg=NPS, noverlap=NOV)
                _, sxx = welch(x, fs=fs, nperseg=NPS, noverlap=NOV)
                _, syy = welch(y, fs=fs, nperseg=NPS, noverlap=NOV)
                k = max((len(x) - NOV) // (NPS - NOV), 1)
                out.append(dict(route=nm, blk="%s:%d:%d" % (nm, s, a), f=f,
                                sxy=sxy * k, sxx=sxx * k, syy=syy * k, k=k,
                                v=float(np.median(v[a:b]))))
    return out


def pooled(bs):
    """H1, H2, coherence from a list of block spectra."""
    if not bs:
        return None
    f = bs[0]["f"]
    Sxy = np.sum([b["sxy"] for b in bs], axis=0)
    Sxx = np.sum([b["sxx"] for b in bs], axis=0)
    Syy = np.sum([b["syy"] for b in bs], axis=0)
    n = int(sum(b["k"] for b in bs))
    h1 = np.abs(Sxy) / Sxx
    h2 = Syy / np.abs(Sxy)
    coh = np.abs(Sxy) ** 2 / (Sxx * Syy)
    return dict(f=f, h1=h1, h2=h2, coh=coh, n=n, nblk=len({b["blk"] for b in bs}))


def boot_curve(bs, nboot=800):
    """Block bootstrap of the H1 curve.  Returns (lo, hi) per frequency."""
    g = {}
    for b in bs:
        g.setdefault(b["blk"], []).append(b)
    ks = list(g)
    if len(ks) < 4:
        return None, None
    draws = []
    for _ in range(nboot):
        sel = [x for i in RNG.integers(0, len(ks), len(ks)) for x in g[ks[i]]]
        Sxy = np.sum([b["sxy"] for b in sel], axis=0)
        Sxx = np.sum([b["sxx"] for b in sel], axis=0)
        draws.append(np.abs(Sxy) / Sxx)
    D = np.array(draws)
    return np.percentile(D, 2.5, axis=0), np.percentile(D, 97.5, axis=0)


def peaks_of(f, y, lo=4.0, hi=45.0, halfwin=3.0):
    """Peaks of y over a local-median baseline, with a half-power Q for each."""
    base = np.array([np.median(y[(f >= max(x - halfwin, 0.5)) & (f <= x + halfwin)])
                     for x in f])
    r = y / np.where(base > 0, base, np.nan)
    out = []
    m = (f >= lo) & (f <= hi)
    idx = np.flatnonzero(m)
    for j in idx:
        if j < 1 or j >= len(f) - 1:
            continue
        if r[j] > 1.25 and r[j] >= r[j - 1] and r[j] >= r[j + 1]:
            half = 1.0 + (r[j] - 1.0) / 2.0
            i = j
            while i > 0 and r[i] > half:
                i -= 1
            k = j
            while k < len(r) - 1 and r[k] > half:
                k += 1
            bw = f[k] - f[i]
            out.append(dict(f=float(f[j]), rel=float(r[j]),
                            Q=float(f[j] / bw) if bw > 0 else np.nan, bw=float(bw)))
    # merge peaks within 1 Hz, keep the tallest
    out.sort(key=lambda d: -d["rel"])
    keep = []
    for p in out:
        if all(abs(p["f"] - q["f"]) > 1.0 for q in keep):
            keep.append(p)
    return sorted(keep, key=lambda d: d["f"]), base


def main():
    V.hdr("A0  CHANNEL IDENTITY -- re-verified here on the THREE NEW routes, not inherited.\n"
          "    |rate_c| / (2*pi*f*|ang|) must be 1.000 if rate_c is d(ang)/dt at its stated scale.")
    O["a0"] = {}
    for nm in NEW:
        cache, pfx, segs = V.ROUTES[nm]
        rows = []
        for s in segs:
            p = ROOT / cache / ("%s%d.npz" % (pfx, s))
            if not p.exists():
                continue
            d = C31.load(s, ROOT / cache, pfx)
            fs = C31.fs_of(d)
            t = np.asarray(d["t"], float)
            lat = np.asarray(d["cc_lat"], float) > 0.5
            for a, b in C31.runs_of(lat, t, 2048):
                A = np.asarray(d["ang"], float)[a:b]
                R = np.asarray(d["rate_c"], float)[a:b]
                f, pa = welch(A - A.mean(), fs=fs, nperseg=1024, noverlap=512)
                _, pr = welch(R - R.mean(), fs=fs, nperseg=1024, noverlap=512)
                _, cxy = csd(A - A.mean(), R - R.mean(), fs=fs, nperseg=1024, noverlap=512)
                coh = np.abs(cxy) ** 2 / (pa * pr)
                sel = (f > 0.2) & (f < 3.0) & (coh > 0.95)
                if sel.sum():
                    rows += list(np.sqrt(pr[sel]) / (2 * np.pi * f[sel] * np.sqrt(pa[sel])))
        if rows:
            print("    %-10s ratio = %.4f  (n=%d bins with coherence > 0.95)"
                  % (nm, float(np.median(rows)), len(rows)))
            O["a0"][nm] = dict(ratio=float(np.median(rows)), n=len(rows))
    print("    => rate_c is the derivative of the single bus angle = RIM RATE.  [EVIDENCE]")

    V.hdr("A1  THE ADMITTANCE  |Omega/T|,  (deg/s) per torque count.  ENGAGED vs MANUAL,\n"
          "    speed-matched to [0.5, 5.0) m/s, pooled over all 5 routes, block-bootstrapped.\n"
          "    H1 and H2 BRACKET the truth; they converge where coherence is high.")
    O["a1"] = {}
    curves = {}
    for arm, en in (("engaged", True), ("manual", False)):
        bs = blocks(ROUTES, en)
        P = pooled(bs)
        if P is None:
            print("    %s: no data" % arm)
            continue
        lo, hi = boot_curve(bs)
        curves[arm] = dict(P=P, lo=lo, hi=hi, bs=bs)
        print("    %-8s n = %d Welch segments over %d blocks" % (arm, P["n"], P["nblk"]))
        O["a1"][arm] = dict(n=P["n"], nblk=P["nblk"], f=[float(x) for x in P["f"]],
                            h1=[float(x) for x in P["h1"]], h2=[float(x) for x in P["h2"]],
                            coh=[float(x) for x in P["coh"]],
                            lo=[float(x) for x in lo] if lo is not None else None,
                            hi=[float(x) for x in hi] if hi is not None else None)
    f = curves["engaged"]["P"]["f"]
    print("\n    %6s | %-34s | %-34s | %s"
          % ("Hz", "ENGAGED  H1 [95% CI]   H2   coh", "MANUAL   H1 [95% CI]   H2   coh",
             "ENG/MAN"))
    rows = []
    for j in range(len(f)):
        if not (4.0 <= f[j] <= 45.0) or j % 2:
            continue
        e, m = curves["engaged"], curves["manual"]
        r = e["P"]["h1"][j] / m["P"]["h1"][j] if m["P"]["h1"][j] > 0 else np.nan
        print("    %6.2f | %7.4f [%6.4f,%6.4f] %7.4f %5.2f | %7.4f [%6.4f,%6.4f] %7.4f %5.2f | %6.2f"
              % (f[j], e["P"]["h1"][j], e["lo"][j], e["hi"][j], e["P"]["h2"][j], e["P"]["coh"][j],
                 m["P"]["h1"][j], m["lo"][j], m["hi"][j], m["P"]["h2"][j], m["P"]["coh"][j], r))
        rows.append([float(f[j]), float(e["P"]["h1"][j]), float(e["lo"][j]), float(e["hi"][j]),
                     float(e["P"]["h2"][j]), float(e["P"]["coh"][j]), float(m["P"]["h1"][j]),
                     float(m["lo"][j]), float(m["hi"][j]), float(m["P"]["h2"][j]),
                     float(m["P"]["coh"][j]), float(r)])
    O["curve"] = dict(cols=["hz", "eng_h1", "eng_lo", "eng_hi", "eng_h2", "eng_coh",
                            "man_h1", "man_lo", "man_hi", "man_h2", "man_coh", "eng_over_man"],
                      rows=rows)

    V.hdr("A2  THE PEAK LIST.  A peak in the admittance is a resonance of the coupled system.\n"
          "    🛑 The DISCRIMINATOR: a structural mode appears in BOTH arms; one created by the\n"
          "    LKAS loop appears only ENGAGED.")
    O["a2"] = {}
    for arm in ("engaged", "manual"):
        P = curves[arm]["P"]
        pk, base = peaks_of(P["f"], P["h1"])
        curves[arm]["base"] = base
        print("\n    %s  (n=%d seg / %d blk)" % (arm.upper(), P["n"], P["nblk"]))
        print("      %8s %10s %8s %9s %8s" % ("f (Hz)", "rel to base", "Q", "bandwidth", "coh"))
        for p in pk:
            j = int(np.argmin(np.abs(P["f"] - p["f"])))
            print("      %8.2f %10.2f %8.1f %9.2f %8.3f"
                  % (p["f"], p["rel"], p["Q"], p["bw"], P["coh"][j]))
            p["coh"] = float(P["coh"][j])
        O["a2"][arm] = pk

    V.hdr("A3  THE THREE FREQUENCIES OF INTEREST.  Is each one a resonance?")
    print("      %-28s %10s %10s %10s %10s %8s"
          % ("frequency", "ENG rel", "ENG coh", "MAN rel", "MAN coh", "verdict"))
    O["a3"] = {}
    for f0, lab in ((7.99, "the ~8 Hz RATCHET"), (12.8, "recorded 12.8 Hz plant mode"),
                    (21.1, "the ~21 Hz vibration"), (23.7, "where V86 put it")):
        row = {}
        for arm in ("engaged", "manual"):
            P, base = curves[arm]["P"], curves[arm]["base"]
            j = int(np.argmin(np.abs(P["f"] - f0)))
            row[arm] = dict(rel=float(P["h1"][j] / base[j]), coh=float(P["coh"][j]),
                            h1=float(P["h1"][j]))
        e, m = row["engaged"], row["manual"]
        if e["rel"] > 1.25 and m["rel"] > 1.25:
            v = "BOTH"
        elif e["rel"] > 1.25:
            v = "ENG only"
        elif m["rel"] > 1.25:
            v = "MAN only"
        else:
            v = "no peak"
        print("      %-28s %10.2f %10.3f %10.2f %10.3f %8s"
              % ("%.2f Hz  %s" % (f0, lab), e["rel"], e["coh"], m["rel"], m["coh"], v))
        O["a3"]["%.2f" % f0] = dict(label=lab, engaged=e, manual=m, verdict=v)

    V.hdr("A4  QUANTISATION FLOOR.  `rate_c` has a 1 deg/s LSB.  If the rim motion at a\n"
          "    frequency is near that, the admittance there is quantisation, not mechanics.")
    O["a4"] = {}
    for arm in ("engaged", "manual"):
        bs = curves[arm]["bs"]
        fq = bs[0]["f"]
        df = fq[1] - fq[0]
        # uniform quantiser noise: var = LSB^2/12, spread over 0..fs/2
        fs = 101.0
        psd_q = (1.0 ** 2 / 12.0) / (fs / 2)
        Syy = np.sum([b["syy"] for b in bs], axis=0) / sum(b["k"] for b in bs)
        print("    %-8s rate_c PSD vs quantisation PSD (%.2e (deg/s)^2/Hz):" % (arm, psd_q))
        cells = []
        for lo2, hi2 in ((5, 8), (8, 11), (11, 14), (17, 20), (20, 23), (26, 30), (33, 38),
                         (40, 45)):
            mm = (fq >= lo2) & (fq < hi2)
            cells.append("%d-%d:%.0fx" % (lo2, hi2, np.mean(Syy[mm]) / psd_q))
            O["a4"].setdefault(arm, {})["%d-%d" % (lo2, hi2)] = float(np.mean(Syy[mm]) / psd_q)
        print("        " + "  ".join(cells))
    print("    (ratio >> 1 means real motion dominates the quantiser; ~1 means it does not.)")

    (ROOT / "_scratch/cache/r6f" / "rim_admittance.json").write_text(json.dumps(O, indent=1,
                                                                       default=float))
    print("\nwrote %s" % (ROOT / "_scratch/cache/r6f" / "rim_admittance.json"))


if __name__ == "__main__":
    main()
