#!/usr/bin/env python3
"""THE ZERO-BYTE RETRODICTION: does the DC bias the engaged damper injects into the residual
RESCUE relay #2 from chattering -- so that DELETING the damper made the ~7.79 Hz macro-ratchet
WORSE on V84/V85 than on the builds that carried it?

🛑 THE PREMISE WAS CORRECTED FROM THE IMAGES BEFORE ANY MEASUREMENT.  The brief said `0xC63A0`
was "doubled on V72/V73/V74/V75/V81 and silently reverted at V84".  Read from the plain images:

    build      0xC63A0   FactorC m26 Y            <- Y[0] IS the zero-rate output = THE DC BIAS
    STOCK         1024   [  0, 234, 429, 908]
    V74/r5d       2048   [429, 234, 429, 908]
    V75/r5e       2048   [566, 234, 429, 908]
    V76/r65       1024   [566, 566, 566, 908]     <- 🛑 1024, NOT 2048
    V80/r66       1024   [566, 566, 566, 566]     <- 🛑 1024
    V81/r67       2048   [566, 234, 429, 908]
    V83a/r68      1024   [566, 234, 429, 908]
    V84/r6d       1024   [  0, 234, 429, 908]     <- bias DELETED
    V85/r6e       1024   [  0, 234, 429, 908]     <- bias DELETED

⇒ the revert of `0xC63A0` happened at **V76/V80, not V84**, and `0xC63A0` is therefore INTERLEAVED
with build order (V74,V75 = 2048 · V76,V80 = 1024 · V81 = 2048 · V83a,V84,V85 = 1024).  That is a
BETTER test than the brief's before/after: a quantity that tracks the DOSE while crossing build
order twice cannot be explained by "things drifted over time".

THE DOSE.  `gp-0x6bd0` (the damper output) enters the residual weighted by `0xC63A0`, and FactorC's
first breakpoint governs up to ~35 km/h (axis = voted speed at 64 ct/km/h, X = 35/60/80/140).  So at
the creep speeds where the ratchet lives the injected DC bias is  `FactorC_m26_Y[0] * 0xC63A0`:

    V84, V85            0            <- relay #2 sits on B = 0, its worst point
    V76, V80, V83a    579,584
    V74               878,592
    V75, V81        1,159,168

TWO TESTS, and the second is immune to road/route differences:
  R1 CROSS-BUILD, speed-matched: `a779` (7.2-8.4 Hz band amplitude) vs dose.
  R2 WITHIN-ROUTE engaged/manual: the damper is ENGAGED-ONLY (modes 26/27), so the bias exists only
     in the engaged arm.  🛑 If the bias rescues the relay, the engaged/manual ratio at 7.79 Hz must
     be LOWER on the bias builds and HIGHER on V84/V85.  Same road, same tyres, same drive.
  NEG 32-38 Hz measured identically, so a broadband shift cannot masquerade as the line moving.

Usage:
    python studies/misc/retrodiction_bias_r6e.py
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
import struct
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt, hilbert

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import score_v85_r6e_bands as SB  # noqa: E402  -- owns the registered build table
import _grind2_lib as G  # noqa: E402
import _r31_common as C31  # noqa: E402

FWROOT = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
IMAGES = {
    "STOCK":    FWROOT / "stock_fw_dump" / "code.bin",
    "V74/r5d":  "_v74_engagedcols_x0_12_addonly_plain_image.bin",
    "V75/r5e":  "_v75_CY0.566-EX1.200_magprobe_plain_image.bin",
    "V76/r65":  "_v76_v38base_relu_damper_plain_image.bin",
    "V80/r66":  "_v80_v79base_flatC566_ratchet454FE_dose412_plain_image.bin",
    "V81/r67":  "_v81_C407E.511-FRICTION.STOCK_plain_image.bin",
    "V83a/r68": "_v83a_FACTORE.STOCK-GAINA.STOCK-C63A0.1024_plain_image.bin",
    "V84/r6d":  "_v84_LEVERB.ARM5244-DAMPER.HONDA.M26.M27-PROBE.R24.6ADA-FD.67FE.6A10"
                "_plain_image.bin",
    "V85/r6e":  "_v85_FRICTION.C40BC.6000-PROBE.RATE.6ABC-FRIC.6AE2_plain_image.bin",
}
ORDER = ["V74/r5d", "V75/r5e", "V76/r65", "V80/r66", "V81/r67", "V83a/r68", "V84/r6d", "V85/r6e"]
FACTORC_PTR = 0xC9E9C
C63A0 = 0xC63A0
NW = 512                       # 5.06 s -- short enough to give the small MANUAL arms real n
HOPW = 256
LINE = (7.2, 8.4)              # the macro-ratchet line
NEG = (32.0, 38.0)             # pre-declared negative control
V_CREEP = 35.0 / 3.6           # FactorC's first breakpoint, 35 km/h -> 9.72 m/s
RNG = np.random.default_rng(85_6339)
OUT = {}


def hdr(s):
    print("\n" + "=" * 110 + f"\n{s}\n" + "=" * 110, flush=True)


def boot_med(vals, units, nboot=2000):
    vals = np.asarray(vals, float)
    ok = np.isfinite(vals)
    vals, units = vals[ok], np.asarray(units)[ok]
    if len(vals) < 4:
        return np.nan, np.nan, np.nan, len(vals)
    gr = {}
    for v, u in zip(vals, units):
        gr.setdefault(u, []).append(v)
    keys = list(gr)
    d = np.empty(nboot)
    for k in range(nboot):
        i = RNG.integers(0, len(keys), len(keys))
        d[k] = np.median(np.concatenate([gr[keys[j]] for j in i]))
    return (float(np.median(vals)), float(np.percentile(d, 2.5)),
            float(np.percentile(d, 97.5)), len(vals))


# =====================================================================================================
#  R0 -- the byte ledger, read from the IMAGES.  [EVIDENCE]
# =====================================================================================================
def r0():
    hdr("R0  THE DOSE, READ FROM THE PLAIN IMAGES (not from build scripts, not from the brief).\n"
        "    bias = FactorC mode-26 Y[0] * 0xC63A0.  Y[0] is the damper's output at ZERO motor\n"
        "    rate ⇒ it IS the DC offset injected into the residual, and it governs to ~35 km/h.")
    print(f"    {'build':10s} {'0xC63A0':>8s} {'0xC63AC':>8s} {'FactorC m26 Y':>26s} {'bias':>12s}")
    dose = {}
    for b in ["STOCK"] + ORDER:
        f = IMAGES[b]
        p = f if isinstance(f, Path) else FWROOT / f
        if not p.exists():
            print(f"    {b:10s}  -- image missing --")
            continue
        d = p.read_bytes()
        w = struct.unpack_from("<h", d, C63A0)[0]
        iir = struct.unpack_from("<h", d, 0xC63AC)[0]
        base = struct.unpack_from("<I", d, FACTORC_PTR + 4 * 26)[0]
        n = struct.unpack_from("<H", d, base)[0]
        ys = list(struct.unpack_from(f"<{n}h", d, base + 2 + 2 * n))
        bias = ys[0] * w
        dose[b] = dict(c63a0=w, c63ac=iir, factorC_y=ys, bias=bias)
        print(f"    {b:10s} {w:8d} {iir:8d} {str(ys):>26s} {bias:12,d}")
    OUT["dose"] = dose
    print("\n    🛑 `0xC63A0` is INTERLEAVED with build order: 2048 on V74,V75,V81 and 1024 on\n"
          "       V76,V80,V83a,V84,V85.  The brief's 'reverted at V84' is WRONG -- it reverted at\n"
          "       V76/V80, came back for V81, and went again at V83a.  That interleaving is what\n"
          "       makes a dose-response here more than a chronological trend.")
    print(f"    ⊕ `0xC63AC` = 102 on EVERY build -- the residual EMA coefficient has NEVER been\n"
          f"      touched, so it cannot explain any cross-build difference.  Its corner is\n"
          f"      addressed separately in R4.")
    return dose


# =====================================================================================================
#  windowing
# =====================================================================================================
def windows(build):
    B = G.BUILDS[build]
    parked = SB.S.PARKED.get(build, [])
    b_line = butter(2, list(LINE), btype="band", fs=101.0)
    b_neg = butter(2, list(NEG), btype="band", fs=101.0)
    out = []
    for s in B["segs"]:
        if s in parked:
            continue
        p = B["cache"] / f"{B['pfx']}{s}.npz"
        if not p.exists():
            continue
        d = C31.load(s, B["cache"], B["pfx"])
        t = np.asarray(d["t"], float)
        if "tq" not in d or "cs_v" not in d or "cc_lat" not in d:
            continue
        tq = np.asarray(d["tq"], float)
        v = np.asarray(d["cs_v"], float)
        lat = np.asarray(d["cc_lat"], float) > 0.5
        eff = np.abs(np.asarray(d["cs_tq"], float)) if "cs_tq" in d else np.zeros_like(v)
        rate = np.abs(np.asarray(d["rate_c"], float)) if "rate_c" in d else np.zeros_like(v)
        imu = np.asarray(d["imu_vert"], float) if "imu_vert" in d else None
        for arm, mask in (("engaged", lat), ("manual", ~lat)):
            for a, b in C31.runs_of(mask, t, NW):
                xl = filtfilt(*b_line, tq[a:b])
                xn = filtfilt(*b_neg, tq[a:b])
                el, en = np.abs(hilbert(xl)), np.abs(hilbert(xn))
                for j in range(0, (b - a) - NW + 1, HOPW):
                    sl = slice(j, j + NW)
                    if not np.all(np.isfinite(tq[a:b][sl])):
                        continue
                    out.append(dict(
                        build=build, arm=arm, seg=int(s), ep=f"{arm}:{s}:{a}",
                        blk=f"{arm}:{s}:{a}:{j // (HOPW * 4)}",
                        v=float(np.median(v[a:b][sl])), eff=float(np.median(eff[a:b][sl])),
                        rate=float(np.median(rate[a:b][sl])),
                        a779=float(np.percentile(el[sl], 99)),
                        aneg=float(np.percentile(en[sl], 99)),
                        imu=float(np.nanmedian(np.abs(imu[a:b][sl]))) if imu is not None
                        else np.nan))
    return out


VB = [(0.0, 1.0), (1.0, 2.0), (2.0, 3.0), (3.0, 4.5), (4.5, 6.0), (6.0, 8.0), (8.0, 9.72)]


def binned_ratio(A, B, key, vb=VB, min_n=4):
    """Equal-weight-per-speed-bin log ratio A/B, with an episode bootstrap over both sides."""
    def point(a, b):
        lr = []
        for lo, hi in vb:
            x = [r[key] for r in a if lo <= r["v"] < hi]
            y = [r[key] for r in b if lo <= r["v"] < hi]
            if len(x) >= min_n and len(y) >= min_n:
                lr.append(np.log(np.median(x) / np.median(y)))
        return (float(np.exp(np.mean(lr))), len(lr)) if lr else (np.nan, 0)
    p, nb = point(A, B)
    if nb == 0:
        return np.nan, np.nan, np.nan, 0
    ea, eb = {}, {}
    for r in A:
        ea.setdefault(r["blk"], []).append(r)
    for r in B:
        eb.setdefault(r["blk"], []).append(r)
    ka, kb = list(ea), list(eb)
    d = []
    for _ in range(1200):
        ia = RNG.integers(0, len(ka), len(ka))
        ib = RNG.integers(0, len(kb), len(kb))
        aa = [r for i in ia for r in ea[ka[i]]]
        bb = [r for i in ib for r in eb[kb[i]]]
        val = point(aa, bb)[0]
        if np.isfinite(val):
            d.append(val)
    if not d:
        return p, np.nan, np.nan, nb
    return p, float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)), nb


def main():
    dose = r0()
    SB.register()
    W = {}
    for b in ORDER:
        rs = windows(b)
        W[b] = rs
        e = [r for r in rs if r["arm"] == "engaged" and r["v"] < V_CREEP]
        m = [r for r in rs if r["arm"] == "manual" and r["v"] < V_CREEP]
        print(f"  {b:10s} {len(rs):5d} windows   <35 km/h: engaged {len(e):4d} manual {len(m):4d}",
              flush=True)

    # ---------------------------------------------------------------- R1 ------------------------
    hdr("R1  CROSS-BUILD, ENGAGED, <35 km/h (FactorC's first segment), SPEED-BIN MATCHED.\n"
        "    Reference = V85/r6e.  🛑 The prediction says the ZERO-bias builds (V84, V85) carry the\n"
        "    LARGEST ~7.79 Hz line, so every bias build should read BELOW 1.")
    print(f"    {'build':10s} {'bias':>12s} {'n':>5s} | {'a779 vs V85':>24s} {'bins':>5s} | "
          f"{'NEG 32-38 vs V85':>24s}")
    ref = [r for r in W["V85/r6e"] if r["arm"] == "engaged" and r["v"] < V_CREEP]
    OUT["r1"] = {}
    for b in ORDER:
        e = [r for r in W[b] if r["arm"] == "engaged" and r["v"] < V_CREEP]
        if len(e) < 8:
            print(f"    {b:10s} {dose[b]['bias']:12,d} {len(e):5d} |  -- too few windows --")
            continue
        r1 = binned_ratio(e, ref, "a779")
        r2 = binned_ratio(e, ref, "aneg")
        print(f"    {b:10s} {dose[b]['bias']:12,d} {len(e):5d} | "
              f"{r1[0]:7.3f} [{r1[1]:6.3f},{r1[2]:6.3f}] {r1[3]:5d} | "
              f"{r2[0]:7.3f} [{r2[1]:6.3f},{r2[2]:6.3f}]")
        OUT["r1"][b] = dict(bias=dose[b]["bias"], n=len(e), line=list(r1), neg=list(r2))

    # ---------------------------------------------------------------- R2 ------------------------
    hdr("R2  🛑 THE CONFOUND-FREE TEST -- WITHIN-ROUTE engaged/manual at the line, <35 km/h.\n"
        "    The damper is ENGAGED-ONLY (modes 26/27), so the bias exists in the engaged arm and\n"
        "    NOT in the manual arm of the SAME drive: same road, same tyres, same session.\n"
        "    PREDICTION: eng/man at 7.79 Hz LOWER on bias builds, HIGHER on V84/V85.")
    print(f"    {'build':10s} {'bias':>12s} {'nE':>5s} {'nM':>5s} | {'eng/man LINE':>24s} {'bins':>4s}"
          f" | {'eng/man NEG 32-38':>24s}")
    OUT["r2"] = {}
    for b in ORDER:
        e = [r for r in W[b] if r["arm"] == "engaged" and r["v"] < V_CREEP]
        m = [r for r in W[b] if r["arm"] == "manual" and r["v"] < V_CREEP]
        if len(e) < 8 or len(m) < 8:
            print(f"    {b:10s} {dose[b]['bias']:12,d} {len(e):5d} {len(m):5d} |  "
                  f"-- insufficient manual arm --")
            OUT["r2"][b] = None
            continue
        r1 = binned_ratio(e, m, "a779")
        r2 = binned_ratio(e, m, "aneg")
        print(f"    {b:10s} {dose[b]['bias']:12,d} {len(e):5d} {len(m):5d} | "
              f"{r1[0]:7.3f} [{r1[1]:6.3f},{r1[2]:6.3f}] {r1[3]:4d} | "
              f"{r2[0]:7.3f} [{r2[1]:6.3f},{r2[2]:6.3f}]")
        OUT["r2"][b] = dict(bias=dose[b]["bias"], nE=len(e), nM=len(m),
                            line=list(r1), neg=list(r2))

    # ---------------------------------------------------------------- R3 ------------------------
    hdr("R3  DOSE-RESPONSE.  Spearman of the R1 ratio against the bias dose, and the grouped\n"
        "    contrast ZERO-bias (V84,V85) vs NON-ZERO.  🛑 Reported with the NEGATIVE CONTROL's\n"
        "    same-shaped statistic beside it -- if the control moves too, nothing band-specific.")
    rows = [(b, OUT["r1"][b]["bias"], OUT["r1"][b]["line"][0], OUT["r1"][b]["neg"][0])
            for b in ORDER if b in OUT["r1"]]
    if len(rows) >= 4:
        from scipy.stats import spearmanr
        d_ = np.array([r[1] for r in rows], float)
        l_ = np.array([r[2] for r in rows], float)
        n_ = np.array([r[3] for r in rows], float)
        print(f"    n builds = {len(rows)}")
        print(f"    Spearman(bias, a779 ratio)  rho = {spearmanr(d_, l_).statistic:+.3f}  "
              f"p = {spearmanr(d_, l_).pvalue:.3f}")
        print(f"    Spearman(bias, NEG  ratio)  rho = {spearmanr(d_, n_).statistic:+.3f}  "
              f"p = {spearmanr(d_, n_).pvalue:.3f}   <- the control")
        z = [r for r in rows if r[1] == 0]
        nz = [r for r in rows if r[1] > 0]
        print(f"\n    zero-bias builds  ({', '.join(r[0] for r in z)}): "
              f"line ratio median {np.median([r[2] for r in z]):.3f}  "
              f"neg {np.median([r[3] for r in z]):.3f}")
        print(f"    bias builds       ({', '.join(r[0] for r in nz)}): "
              f"line ratio median {np.median([r[2] for r in nz]):.3f}  "
              f"neg {np.median([r[3] for r in nz]):.3f}")
        OUT["r3"] = dict(rows=[[r[0], r[1], r[2], r[3]] for r in rows],
                         rho_line=float(spearmanr(d_, l_).statistic),
                         p_line=float(spearmanr(d_, l_).pvalue),
                         rho_neg=float(spearmanr(d_, n_).statistic))

    # ---------------------------------------------------------------- R4 ------------------------
    hdr("R4  THE `0xC63AC` = 102 CORNER (~16.7 Hz), which sits INSIDE the 18-22 Hz band.\n"
        "    🛑 `0xC63AC` is 102 on EVERY build ever made (R0), so it can explain no cross-build\n"
        "    difference.  What it CAN do is shape the band.  Averaged engaged spectra, 10-30 Hz,\n"
        "    normalised at 12 Hz, to see whether a corner is visible at all.")
    from _r31_common import periodogram
    OUT["r4"] = {}
    for b in ("V85/r6e", "V84/r6d", "V81/r67"):
        B = G.BUILDS[b]
        acc, f = [], None
        for s in B["segs"]:
            if s in SB.S.PARKED.get(b, []):
                continue
            p = B["cache"] / f"{B['pfx']}{s}.npz"
            if not p.exists():
                continue
            d = C31.load(s, B["cache"], B["pfx"])
            t = np.asarray(d["t"], float)
            tq = np.asarray(d["tq"], float)
            lat = np.asarray(d["cc_lat"], float) > 0.5
            fs = C31.fs_of(d)
            for a, bb in C31.runs_of(lat, t, 1024):
                for j in range(0, (bb - a) - 1024 + 1, 512):
                    P = periodogram(tq[a:bb][j:j + 1024], fs, nfft=1024, detrend=True)
                    if P is not None:
                        acc.append(P)
                        f = np.fft.rfftfreq(1024, 1.0 / fs)
        if not acc:
            continue
        M = np.median(np.array(acc), axis=0)
        i12 = int(np.argmin(np.abs(f - 12.0)))
        M = M / M[i12]
        pts = [10, 12, 14, 16.7, 18, 20, 22, 25, 28]
        vals = [float(M[int(np.argmin(np.abs(f - x)))]) for x in pts]
        print(f"    {b:10s} n={len(acc):4d}  " +
              "  ".join(f"{x:g}Hz {10*np.log10(v):+6.1f}dB" for x, v in zip(pts, vals)))
        OUT["r4"][b] = dict(n=len(acc), freqs=pts, db=[float(10 * np.log10(v)) for v in vals])
    print("\n    READ: a real corner at 16.7 Hz shows as a SLOPE CHANGE there.  A smooth roll-off\n"
          "    through 16.7 Hz means the EMA is not shaping the band at a level the bar can see.")

    (ROOT / "_scratch/cache/r6e" / "retrodiction_bias.json").write_text(json.dumps(OUT, indent=1,
                                                                          default=float))
    print(f"\nwrote {ROOT / '_scratch/cache/r6e' / 'retrodiction_bias.json'}")


if __name__ == "__main__":
    main()
