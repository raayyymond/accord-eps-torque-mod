#!/usr/bin/env python3
r"""THE GAIN DOSE-RESPONSE, and the torque-vs-vibration trade the operator has to choose from.

🛑 THERE IS NO THIRD RUNG.  Every cached route on disk is `0xC6CD0` = 3564 (4x) except r95 (8x):
   the 4x has been frozen on every build since V38 and V57 merely migrated the cell.  r28/r29 are
   V57-era, already 4x.  ⇒ **the exponent below is calibrated on TWO POINTS and is an ASSUMPTION,
   not a fit.**  Stated as such everywhere.

🛑 AND A MEASURED FACT THAT RULES OUT THE OBVIOUS MODEL.  Within either route, the 22-26 Hz band
   does NOT scale with the LKAS command amplitude: slope of log(band) on log(command RMS) is
   +0.01 [-0.36, +0.31] on V101 and +0.12 [+0.01, +0.40] on V100 (studies/v102-crossbuild/v102_xb_line23b.py, L1), over a
   >10x command range.  ⇒ the command is NOT the excitation.  The excitation is the road and the
   driver; the LKAS gain acts on the LOOP that shapes it.  A "vibration scales with the command"
   model is REFUTED, and a plain power law in the gain has no mechanism behind it.

   The mechanism the data supports:  raising the forward gain raises loop gain, which lowers damping
   (Q rises) and moves the pole up in frequency -- both measured.  For a second-order loop driven by
   a fixed disturbance, the resonant response goes as  A(m) proportional to m * Q(m).
   With zeta = 1/(2Q) falling linearly in m, that is a two-parameter model pinned by two points --
   exactly determined, zero residual.  It is a MODEL, not a fit.  Both it and the power law are
   reported so the disagreement between them is visible.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NFFT_Q, HOP_Q = 1024, 512          # 10.24 s, df = 0.098 Hz -- a Q of 30-47 at 22 Hz is ~6 bins wide
CH3 = ("tq", "rate_c", "cs_ang")


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104)


# =====================================================================================================
hdr("A -- Q AND PEAK FREQUENCY, measured here, NFFT=1024 (df 0.098 Hz).  Engaged, 5-65 km/h.")
print("   At NFFT=256 (df 0.39 Hz) a Q of 35 at 22 Hz is 1.6 bins wide and CANNOT be measured;")
print("   that is why this section alone uses 10.24 s windows.  Frequency drift within a window")
print("   broadens the peak, so every Q here is a LOWER BOUND.\n")
win = np.hanning(NFFT_Q)
QM = {}
for route in ("85", "95"):
    P, n = [], 0
    for b in L.all_blocks(route):
        eng = b["cc_lat"] > 0.5
        v = b["v_rear"] * 3.6
        m = eng & (v >= 5) & (v < 65)
        i = 0
        while i + NFFT_Q <= len(m):
            if m[i:i + NFFT_Q].mean() >= 0.98:
                P.append([L.psd(b[ch][i:i + NFFT_Q], L.FS, win)[1] for ch in CH3])
                n += 1
            i += HOP_Q
    if n < 3:
        print("   r%s: only %d windows -- Q NOT QUOTED" % (route, n))
        continue
    f = L.psd(np.zeros(NFFT_Q), L.FS, win)[0]
    med = np.median(np.asarray(P), axis=0)
    out = []
    for j, ch in enumerate(CH3):
        p = med[j]
        band = (f >= 19) & (f <= 27)
        fb, pb = f[band], p[band]
        k = int(np.argmax(pb))
        f0, pk = fb[k], pb[k]
        base = np.median(p[(f >= 15) & (f <= 32)])
        half = base + 0.5 * (pk - base)
        lo = k
        while lo > 0 and pb[lo] > half:
            lo -= 1
        hi = k
        while hi < len(pb) - 1 and pb[hi] > half:
            hi += 1
        bw = fb[hi] - fb[lo]
        q = f0 / bw if bw > 0 else np.nan
        out.append((ch, f0, q, pk / base))
        QM[(route, ch)] = dict(f0=f0, Q=q, prom=pk / base)
    print("   r%s %-5s  %2d windows   " % (route, L.ROUTES[route]["build"], n)
          + "   ".join("%s: f0=%5.2f Hz Q=%5.1f prom=%4.2f" % o for o in out))

print("\n   %-9s %10s %10s   %10s %10s   %8s %8s" %
      ("channel", "f0 4x", "f0 8x", "Q 4x", "Q 8x", "Q ratio", "df"))
for ch in CH3:
    a, b = QM.get(("85", ch)), QM.get(("95", ch))
    if not a or not b:
        continue
    print("   %-9s %9.2f %9.2f   %10.1f %10.1f   %8.2f %+7.2f"
          % (ch, a["f0"], b["f0"], a["Q"], b["Q"], b["Q"] / a["Q"], b["f0"] - a["f0"]))

# =====================================================================================================
hdr("B -- THE TWO MODELS, both calibrated on the SAME two points (4x and 8x)")
G_LO, G_MID, G_HI = 2.69, 3.34, 3.89        # measured shape-ratio G at 22-26 Hz (rate_c / tq / cs_ang)
qs = [QM[("95", c)]["Q"] / QM[("85", c)]["Q"] for c in CH3 if ("95", c) in QM and ("85", c) in QM]
QR = float(np.exp(np.mean(np.log(qs)))) if qs else np.nan
Q4 = float(np.exp(np.mean(np.log([QM[("85", c)]["Q"] for c in CH3 if ("85", c) in QM])))) if qs else np.nan
print("   MEASURED ANCHORS")
print("      G (22-26 Hz shape, V101/V100) = %.2f  [channel range %.2f - %.2f]   (studies/v102-crossbuild/v102_xb_deconf.py)"
      % (G_MID, G_LO, G_HI))
print("      Q ratio 8x/4x (measured here) = %.2f ;  Q at 4x = %.1f" % (QR, Q4))
print("      m * Q(m) prediction of G      = 2.00 * %.2f = %.2f    <-- compare with G above" % (QR, 2 * QR))
p_pow = np.log(G_MID) / np.log(2.0)
print("\n   MODEL 1  POWER LAW      A(m) proportional to m^p,  p = log(G)/log(2) = %.2f"
      "   [range %.2f - %.2f]" % (p_pow, np.log(G_LO) / np.log(2), np.log(G_HI) / np.log(2)))
z4 = 1.0 / (2 * Q4)
z8 = 1.0 / (2 * Q4 * QR)
c = (z4 - z8) / 4.0
print("   MODEL 2  RESONANCE      zeta(m) = %.5f - %.5f*(m-4),  A(m) proportional to m*Q(m)"
      % (z4, c))
print("            zeta(4x) = %.5f (Q %.1f) ;  zeta(8x) = %.5f (Q %.1f)" % (z4, Q4, z8, Q4 * QR))
m_unstable = 4 + z4 / c
print("            🛑 zeta reaches ZERO at m = %.1fx  ->  EXTRAPOLATION ONLY, far outside the data,"
      % m_unstable)
print("               but it says the margin is finite and the direction of travel is toward it.")


def a_pow(m):
    return (m / 8.0) ** p_pow


def a_res(m):
    z = z4 - c * (m - 4.0)
    z8_ = z4 - c * 4.0
    return (m * (1.0 / (2 * z))) / (8.0 * (1.0 / (2 * z8_)))


# =====================================================================================================
hdr("C -- WHAT HE LOSES.  Authority scaling from the PROTECTED METRIC already measured.")
print("""   Wheel-angle rate under a hard LKAS command, V101/V100 (a 2x gain step):
      frame-level, at the rail + hands-light, 5-30 km/h : p50 2.06 [1.35,2.87], p90 2.01 [1.49,3.30]
      event-level, matched command ramp                 : p90 1.68 [0.91,3.41], peak 1.84 [1.00,3.08]
   => authority exponent q = log(ratio)/log(2):""")
for lab, r in (("event peak 1.84", 1.84), ("event p90 1.68", 1.68), ("frame p50 2.06", 2.06)):
    print("      %-18s q = %.2f" % (lab, np.log(r) / np.log(2)))
Q_AUTH = np.log(1.84) / np.log(2.0)
print("   Using q = %.2f (the event-level peak -- the best-powered, command-ramp-matched estimate)."
      % Q_AUTH)

# =====================================================================================================
hdr("D -- 🛑 THE TRADE TABLE.  Everything relative to TODAY (V101, 8x) and to V100 (4x).")
print("   %-9s %-7s | %-28s | %-28s | %s" %
      ("0xC6CD0", "mult", "22-26 Hz vs TODAY (8x)", "22-26 Hz vs V100 (4x)", "wheel rate vs TODAY"))
print("   %-9s %-7s | %-13s %-14s | %-13s %-14s | %s" %
      ("", "", "power law", "resonance", "power law", "resonance", ""))
ROWS = [(7128, 8.0, "TODAY, flown"), (6413, 7.2, "interpolation"), (5346, 6.0, "interpolation"),
        (4455, 5.0, "interpolation"), (3564, 4.0, "V100/V88-V100, flown"),
        (2673, 3.0, "EXTRAPOLATION - no data"), (1782, 2.0, "EXTRAPOLATION - no data")]
for cell, m, note in ROWS:
    ap, ar = a_pow(m), a_res(m)
    bp, br = ap * G_MID, ar * G_MID
    wr = (m / 8.0) ** Q_AUTH
    print("   %-9d %-7s | %-13s %-14s | %-13s %-14s | %-6s   %s"
          % (cell, "%.1fx" % m, "%.2fx" % ap, "%.2fx" % ar, "%.2fx" % bp, "%.2fx" % br,
             "%.2fx" % wr, note))
print("""
   READING IT.  At 6x the buzz drops to about 0.6x of today while the wheel keeps about 0.8x of
   today's rate under a hard command -- still ~1.4x what V100 gave him.  At 5x the buzz is ~0.45x
   of today and authority ~0.68x of today (~1.2x V100).  The asymmetry is real and it is the whole
   point: vibration goes as m^%.2f and authority as m^%.2f, so every step down buys about
   %.1f%% less buzz for %.1f%% less torque."""
      % (p_pow, Q_AUTH, 100 * (1 - (7.0 / 8.0) ** p_pow), 100 * (1 - (7.0 / 8.0) ** Q_AUTH)))
print("""   🛑 CAVEATS, in order of importance:
     1. TWO POINTS.  No 1x or 2x route survives with usable channels, so neither model is tested
        against a third rung.  The two models agree to ~5 % between 4x and 8x and DIVERGE outside it.
     2. Rows at 3x and 2x are EXTRAPOLATION and are marked so.  Do not quote them to the operator
        as predictions.
     3. The authority exponent rests on a CI that touches 1.0 (event-level 1.84 [1.00, 3.08]) and on
        1.2 s of hands-light V101 exposure at the frame level.  It is the weaker half of the trade.
     4. The 22-26 Hz anchor G is a SHAPE ratio against the 32-38 Hz control band, floor 1.45x.""")

# =====================================================================================================
hdr("E -- DOES THE 6-9 Hz LEVER-B WIN HOLD ABOVE CREEP?")
print("""   The Lever-B arm (V87 route 71) is creep-only, so the isolated answer cannot be extended.
   What CAN be extended is the CONFOUNDED V101/V100 contrast at road speed, decomposed with the
   gain's own 6-9 Hz effect measured at creep (V101/V87 shape 6-9 = 1.37 / 0.80 / 1.58, i.e. ~1.0).
   If the gain does ~nothing at 6-9 Hz, then V101/V100 at 6-9 Hz IS essentially Lever B.""")
W = {}
for r in ("85", "95"):
    w = L.windows(r, 256, 128, engaged=True)
    for x in w:
        x["arm"] = r
        for ch in CH3:
            cc = x.get(ch + "|32-38", np.nan)
            if np.isfinite(cc) and cc > 0:
                for bn in ("6-9", "22-26"):
                    x["s:" + ch + "|" + bn] = x[ch + "|" + bn] / cc
    W[r] = w
RB = [(1, 8), (8, 20), (20, 45), (45, 120)]
for vlo, vhi, lab in ((5, 15, "creep 5-15 km/h"), (15, 35, "15-35 km/h"), (35, 65, "35-65 km/h")):
    pack = []
    for rlo, rhi in RB:
        a = L.sel(L.sel(W["85"], vlo=vlo, vhi=vhi), rlo=rlo, rhi=rhi)
        b = L.sel(L.sel(W["95"], vlo=vlo, vhi=vhi), rlo=rlo, rhi=rhi)
        if len(a) >= 5 and len(b) >= 5:
            pack.append((a, b))
    if not pack:
        print("   %-18s no matched cells" % lab)
        continue
    cells = []
    for ch in CH3:
        num = den = 0.0
        for a, b in pack:
            va = np.array([x["s:" + ch + "|6-9"] for x in a if "s:" + ch + "|6-9" in x])
            vb = np.array([x["s:" + ch + "|6-9"] for x in b if "s:" + ch + "|6-9" in x])
            if len(va) < 3 or len(vb) < 3:
                continue
            w_ = min(len(va), len(vb))
            num += w_ * np.log(np.median(vb) / np.median(va))
            den += w_
        cells.append("%s %.2f" % (ch, np.exp(num / den)) if den else "%s -" % ch)
    print("   %-18s cells=%d   V101/V100 6-9 Hz shape:  %s" % (lab, len(pack), "   ".join(cells)))
print("""
   Floor at 6-9 Hz is 1.35x (so anything below 0.74 counts).""")

print("\n[done]")
