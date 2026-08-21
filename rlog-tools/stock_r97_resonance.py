#!/usr/bin/env python3
r"""stock_r97_resonance.py -- TASKS 3/4/5 on the STOCK route 97.

    R1  is there a RESONANCE on stock at all -- peak frequency and prominence, matched speed
    R2  ring-down zeta / Q on stock, WITH its positive control (the only estimator that passes one)
    R3  Re(Z), the driving-point impedance real part, on the FROZEN `decode_v90_probe` estimator
    R4  the engaged/manual 6-9 Hz band contrast on stock, with an episode-bootstrap CI
    R5  matched cross-build ratios WITH episode-bootstrap CIs

🛑 ENVELOPE CORRECTNESS.  `_r31_common.band_envelope` / `_r2b_common.band_envelope` are BROKEN --
   they set a one-sided `H = 2X` and then call `np.fft.irfft`, which re-imposes Hermitian symmetry
   and returns a REAL band-passed signal, so `abs()` of it is a RECTIFIED waveform, not an analytic
   envelope.  This file NEVER calls them.  R2 uses `scipy.signal.hilbert` on a Butterworth
   band-pass -- the same construction `qd_lib.envelope_stats` and `qd_final.py` used, which is
   correct -- and R1/R4/R5 use no envelope at all.  `_selftest_envelope()` proves the difference.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt, hilbert

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import v102_xb_lib as L          # noqa: E402
import decode_v90_probe as P     # noqa: E402  -- the FROZEN Re(Z) estimator, read-only

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

L.ROUTES["97"] = L._mk("97", "V9b-STOCK", gain=891, clamp=512, leverB=False, idcode=0, bits="stock")
L.ROUTES["96"] = L._mk("96", "V102", gain=5346, clamp=3072, leverB=False, idcode=3, bits="v102")
ARMS = [("97", "V9b STOCK 1x"), ("85", "V100 4x"), ("95", "V101 8x"), ("96", "V102 6x")]
ARMS = [(r, l) for r, l in ARMS if L._segs(r)]

CACHE = ROOT / "analysis-2020accord"
DEG2RAD = np.pi / 180.0
RNG = np.random.default_rng(97_2026)
OUT = {}
SPEED_BINS = [(5, 20), (20, 35), (35, 50), (50, 65), (65, 85), (85, 115)]
RATE_BINS = [(0, 1), (1, 13), (13, 50), (50, 200)]
_W = {}


def hdr(s):
    print("\n" + "=" * 108)
    print(s)
    print("=" * 108)


def wins(route, engaged=True):
    k = (route, engaged)
    if k not in _W:
        _W[k] = L.windows(route, nfft=256, hop=128, engaged=engaged, keep_raw=True)
    return _W[k]


def env_correct(x, fs, lo, hi):
    """The analytic envelope, done right: Butterworth band-pass then |hilbert|."""
    b = butter(2, [max(lo, 0.5), hi], btype="band", fs=fs)
    return np.abs(hilbert(filtfilt(*b, np.asarray(x, float))))


def env_broken(x, fs, lo, hi):
    """`_r31_common.band_envelope`, reproduced so R2's docstring claim is DEMONSTRATED."""
    x = np.asarray(x, float) - np.mean(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / fs)
    H = np.zeros(len(f), complex)
    m = (f >= lo) & (f <= hi)
    H[m] = 2 * X[m]
    return np.abs(np.fft.irfft(H, n=len(x)))


def _selftest_envelope():
    """A pure 8 Hz tone decaying at a KNOWN rate.  The correct envelope recovers it; the kit's
    `band_envelope` returns a rectified carrier whose log-fit is dominated by the rectification."""
    fs, T, f0, lam = 100.0, 8.0, 8.0, 1.0
    t = np.arange(int(T * fs)) / fs
    x = np.exp(-lam * t) * np.sin(2 * np.pi * f0 * t)
    for nm, fn in (("CORRECT |hilbert|", env_correct), ("KIT band_envelope", env_broken)):
        e = fn(x, fs, 6.5, 9.5)
        m = (t > 0.5) & (t < 4.0) & (e > 1e-6)
        c = np.polyfit(t[m], np.log(e[m]), 1)
        print("      %-20s recovered lambda = %6.3f /s   (true 1.000)   envelope CV %.3f"
              % (nm, -c[0], np.std(e[m]) / np.mean(e[m])))


# =========================================================================================
def _order_mask(f, vlo_kmh, vhi_kmh):
    """True where a tyre order 1..6 could sit anywhere inside the speed bin.
    Circumference 2.073-2.088 m and GUARD 0.8 Hz are `decode_v90_probe`'s frozen constants."""
    m = np.zeros(len(f), bool)
    for k in P.ORDERS:
        for c in (P.CIRC_LO, P.CIRC_HI):
            lo = k * (vlo_kmh / 3.6) / c - P.GUARD
            hi = k * (vhi_kmh / 3.6) / c + P.GUARD
            m |= (f >= lo) & (f <= hi)
    return m


def r1():
    hdr("R1 -- IS THERE A RESONANCE ON STOCK AT ALL?\n"
        "     Welch PSD of `tq`, engaged, NFFT 1024 (0.098 Hz), inside NARROW 10 km/h speed bins\n"
        "     so a tyre order cannot smear.  🛑 Orders 1-6 (circumference 2.073-2.088 m, GUARD\n"
        "     0.8 Hz, `decode_v90_probe`'s frozen constants) are MARKED AND VETOED before the\n"
        "     peak search -- otherwise the strongest line in every highway spectrum is a wheel.\n"
        "     PROMINENCE = peak / the median of the 2-50 Hz PSD.")
    OUT["r1"] = {}
    import os
    nfft = int(os.environ.get("R1_NFFT", 1024))
    bw = int(os.environ.get("R1_BW", 10))
    w = np.hanning(nfft)
    bins = [(v, v + bw) for v in range(10, 115, bw)]
    for vlo, vhi in bins:
        arms = []
        for rt, lab in ARMS:
            segs = []
            for blk in L.all_blocks(rt):
                eng = blk["cc_lat"] > 0.5
                v = blk["v_rear"] * L.KMH
                m = eng & (v >= vlo) & (v < vhi)
                idx = np.flatnonzero(m)
                if not len(idx):
                    continue
                brk = np.flatnonzero(np.diff(idx) != 1)
                bounds = [0] + list(brk + 1) + [len(idx)]
                for i0, i1 in zip(bounds[:-1], bounds[1:]):
                    if i1 - i0 < nfft:
                        continue
                    for s in range(idx[i0], idx[i1 - 1] - nfft + 2, nfft // 4):
                        segs.append(blk["tq"][s:s + nfft])
            if len(segs) >= 6:
                arms.append((rt, lab, segs))
        if not arms:
            continue
        _psd = {}
        print("\n  --- speed %d-%d km/h    tyre order 1 = %.2f-%.2f Hz  (order 2 = %.1f-%.1f) ---"
              % (vlo, vhi, (vlo / 3.6) / P.CIRC_HI, (vhi / 3.6) / P.CIRC_LO,
                 2 * (vlo / 3.6) / P.CIRC_HI, 2 * (vhi / 3.6) / P.CIRC_LO))
        for rt, lab, segs in arms:
            acc = None
            for x in segs:
                f, p = L.psd(x, L.FS, w)
                acc = p if acc is None else acc + p
            acc /= len(segs)
            sel = (f >= 2) & (f <= 50)
            fi, pi = f[sel], acc[sel]
            bg = float(np.median(pi))
            om = _order_mask(fi, vlo, vhi)
            free = ~om
            if not free.any():
                continue
            kf = int(np.flatnonzero(free)[np.argmax(pi[free])])
            half = pi[kf] / 2.0
            lo_i = kf
            while lo_i > 0 and pi[lo_i] > half:
                lo_i -= 1
            hi_i = kf
            while hi_i < len(pi) - 1 and pi[hi_i] > half:
                hi_i += 1
            fw = fi[hi_i] - fi[lo_i]
            q = fi[kf] / fw if fw > 0 else np.inf
            ko = int(np.argmax(pi))
            top = sorted(np.flatnonzero(free)[np.argsort(pi[free])[::-1][:6]])
            print("      %-13s n=%3d  ORDER-FREE PEAK %6.2f Hz  prominence %7.1fx  "
                  "-3dB %.2f Hz => Q_app %5.1f    | absolute peak %.2f Hz (%s)"
                  % (lab, len(segs), fi[kf], pi[kf] / bg, fw, q, fi[ko],
                     "A TYRE ORDER" if om[ko] else "order-free"))
            print("                    strongest order-free bins: " +
                  "  ".join("%.1f(%.0fx)" % (fi[i], pi[i] / bg) for i in top))
            OUT["r1"].setdefault("%d-%d" % (vlo, vhi), {})[rt] = dict(
                build=lab, nseg=len(segs), f_peak_orderfree=float(fi[kf]),
                prominence=float(pi[kf] / bg), fwhm=float(fw), q_app=float(q),
                f_peak_absolute=float(fi[ko]), abs_peak_is_order=bool(om[ko]),
                band_rms={bn: float(np.sqrt(pi[(fi >= lo) & (fi < hi)].sum()))
                          for bn, (lo, hi) in L.BANDS.items()})
            _psd[rt] = (fi, pi, om)
        if "97" in _psd and len(_psd) > 1:
            fi, ps, om = _psd["97"]
            edges = np.arange(2, 51, 1.0)
            print("      ratio of band-RMS to STOCK, 1 Hz bins  ('.' = a tyre order sits here):")
            for rt, lab in ARMS:
                if rt == "97" or rt not in _psd:
                    continue
                _f, pm, _o = _psd[rt]
                row = []
                for a, b in zip(edges[:-1], edges[1:]):
                    m = (fi >= a) & (fi < b)
                    if not m.any():
                        continue
                    rr = np.sqrt(pm[m].sum() / ps[m].sum())
                    row.append("%2d%s%s" % (int(a), "." if om[m].any() else ":",
                                            ("%.0f" % rr) if rr >= 1 else "<1"))
                print("        %-12s %s" % (lab, " ".join(row)))


# =========================================================================================
def r2():
    hdr("R2 -- RING-DOWN zeta / Q ON STOCK.  The record calls this the ONLY damping estimator\n"
        "     that PASSES its own control (`q_of` returns 79.00 on white noise).  Estimator is\n"
        "     `qd_final.py`'s, verbatim: |hilbert| of a 2nd-order band-pass around the line, then\n"
        "     a floor-subtracted log fit over the first 2 s after a latActive FALLING edge.")
    print("\n  ENVELOPE SELF-TEST -- a known exp(-1.0 t) decay at 8 Hz:")
    _selftest_envelope()
    OUT["r2"] = {}
    EDGE_PRE, EDGE_POST, FIT_S = 4.0, 4.0, 2.0
    for rt, lab in ARMS:
        rows = []
        for blk in L.all_blocks(rt):
            t = blk["t"]
            x = np.asarray(blk["tq"], float)
            lat = blk["cc_lat"] > 0.5
            v = np.abs(blk["v_rear"])
            fs = L.FS
            npre, npost = int(EDGE_PRE * fs), int(EDGE_POST * fs)
            fe = np.flatnonzero(lat[:-1] & ~lat[1:])
            for i in fe:
                if i - npre < 0 or i + npost >= len(t):
                    continue
                if not lat[i - npre:i + 1].all() or lat[i + 1:i + 1 + npost].any():
                    continue
                if v[i] < 1.0:
                    continue                      # a stationary car has nothing to ring
                pre = x[max(i - int(8 * fs), 0):i]
                f0 = 7.79
                if len(pre) > 256:
                    f, p = L.psd(pre[-256:], fs, np.hanning(256))
                    m = (f >= 5) & (f <= 12)
                    if m.any():
                        f0 = float(f[m][np.argmax(p[m])])
                seg = x[i - npre:i + npost]
                env = env_correct(seg, fs, max(f0 - 1.5, 0.5), f0 + 1.5)
                pre_env = float(np.percentile(env[:npre], 75))
                post = env[npre:]
                floor = float(np.percentile(post[int(2.5 * fs):], 25)) \
                    if len(post) > int(3 * fs) else float(np.percentile(post, 10))
                tt = np.arange(len(post)) / fs
                m = tt <= FIT_S
                y = np.sqrt(np.clip(post[m] ** 2 - floor ** 2, 1e-9, None))
                if np.count_nonzero(y > 1.5e-4) < 20 or pre_env <= 1.2 * floor:
                    continue
                c = np.polyfit(tt[m], np.log(y), 1)
                lam = -float(c[0])
                if not np.isfinite(lam) or lam <= 0:
                    continue
                z = lam / (2 * np.pi * f0)
                rows.append(dict(t=float(t[i]), v=float(v[i]), f0=f0, pre_env=pre_env,
                                 floor=floor, lam=lam, zeta=z, q=1.0 / (2 * z)))
        print("\n  --- %s: %d usable ring-downs ---" % (lab, len(rows)))
        for r in rows:
            print("      t=%7.1f s  v=%5.2f m/s  f0=%5.2f Hz  pre-env %7.1f ct (floor %6.1f)  "
                  "lambda=%6.3f /s  zeta=%.4f  Q=%6.1f"
                  % (r["t"], r["v"], r["f0"], r["pre_env"], r["floor"], r["lam"],
                     r["zeta"], r["q"]))
        if rows:
            z = np.array([r["zeta"] for r in rows])
            print("      => zeta median %.4f  range %.4f-%.4f   Q median %5.1f  range %.1f-%.1f"
                  % (np.median(z), z.min(), z.max(), 1 / (2 * np.median(z)),
                     1 / (2 * z.max()), 1 / (2 * z.min())))
        OUT["r2"][rt] = dict(build=lab, n=len(rows), edges=rows)

    print("\n  POSITIVE CONTROL -- inject a KNOWN-zeta resonance into a MANUAL bed from this very\n"
          "  route and run the identical estimator.  If it cannot recover a known zeta, no zeta\n"
          "  it reports on the car means anything.")
    beds = []
    for blk in L.all_blocks("97"):
        man = blk["cc_lat"] <= 0.5
        idx = np.flatnonzero(man)
        if len(idx) < 800:
            continue
        beds.append(np.asarray(blk["tq"], float)[idx[0]:idx[0] + 800])
    print("      %8s %10s %10s %10s" % ("zeta_true", "zeta_hat", "Q_true", "Q_hat"))
    ctrl = []
    for zt in (0.005, 0.010, 0.020, 0.040, 0.080):
        got = []
        for bed in beds[:12]:
            fs, f0 = L.FS, 7.79
            n = len(bed)
            tt = np.arange(n) / fs
            i0 = n // 2
            amp = np.where(tt < tt[i0], 1.0, np.exp(-zt * 2 * np.pi * f0 * (tt - tt[i0])))
            s = amp * np.sin(2 * np.pi * f0 * tt) * 5.0 * np.std(bed)
            x = bed + s
            env = env_correct(x, fs, f0 - 1.5, f0 + 1.5)
            post = env[i0:]
            floor = float(np.percentile(post[int(2.5 * fs):], 25))
            t2 = np.arange(len(post)) / fs
            m = t2 <= 2.0
            y = np.sqrt(np.clip(post[m] ** 2 - floor ** 2, 1e-9, None))
            c = np.polyfit(t2[m], np.log(y), 1)
            lam = -float(c[0])
            if lam > 0:
                got.append(lam / (2 * np.pi * f0))
        if got:
            zh = float(np.median(got))
            print("      %8.3f %10.4f %10.1f %10.1f" % (zt, zh, 1 / (2 * zt), 1 / (2 * zh)))
            ctrl.append((zt, zh))
    if len(ctrl) >= 3:
        a = np.log([c[0] for c in ctrl])
        b = np.log([c[1] for c in ctrl])
        r = float(np.corrcoef(a, b)[0, 1])
        sl = float(np.polyfit(a, b, 1)[0])
        print("      => log-log r = %+.3f, slope %+.3f   (the record's control gave r = +0.937 "
              "over zeta 0.005-0.02)" % (r, sl))
        OUT["r2"]["control"] = dict(pairs=ctrl, loglog_r=r, slope=sl)


# =========================================================================================
def r3():
    hdr("R3 -- Re(Z), THE DRIVING-POINT IMPEDANCE REAL PART, ON STOCK.\n"
        "     Z = S_(rate,tq) / S_(rate,rate).  Re(Z) < 0 == NEGATIVE DAMPING.  Both channels are\n"
        "     fields of the SAME 0x18F frame, so staleness cancels exactly.  Estimator is the\n"
        "     FROZEN `decode_v90_probe._wins` / `._band_transfer`, imported read-only, at the same\n"
        "     NW_Z=512 (5.12 s) / HOP_Z=256 as routes 77/78/79.  Units: counts.s/rad.")
    OUT["r3"] = {}
    BANDS = [("2-4", 2.0, 4.0), ("4-6", 4.0, 6.0), ("6-9", 6.0, 9.0), ("9-12", 9.0, 12.0),
             ("12-16", 12.0, 16.0), ("16-18", 16.0, 18.0), ("18-22", 18.0, 22.0),
             ("22-26", 22.0, 26.0), ("26-31", 26.0, 31.0), ("31-35", 31.0, 35.0)]
    for rt, lab in ARMS:
        R = L.ROUTES[rt]
        z = np.load(R["cache"] / ("r" + rt + ".npz"), allow_pickle=True)
        t = np.asarray(z["t"], float)
        tq = np.asarray(z["tq"], float)
        rate_f = np.asarray(z["rate_f"], float) * DEG2RAD
        lat = np.asarray(z["cc_lat"], float) > 0.5
        press = np.asarray(z["cs_press"], float) > 0.5
        v = np.abs(np.asarray(z["cs_v"], float))
        fs = 1.0 / float(np.median(np.diff(t)))
        arms = {"ENGAGED hands-off moving": lat & (~press) & (v > 0.5),
                "MANUAL  hands-off moving": (~lat) & (~press) & (v > 0.5),
                "ENGAGED hands-ON  moving": lat & press & (v > 0.5)}
        for nm, mask in arms.items():
            W = P._wins(mask, t, P.NW_Z, P.HOP_Z, (rate_f, tq, v))
            print("\n  --- %s | %s : %d windows of %.2f s (%.1f s of frames) ---"
                  % (lab, nm, len(W), P.NW_Z / fs, mask.sum() / fs))
            if len(W) < 6:
                print("      🛑 TOO FEW WINDOWS -- NOT SCOREABLE, and I am not manufacturing it.")
                OUT["r3"].setdefault(rt, {})[nm] = dict(n=len(W), scoreable=False)
                continue
            print("      %-8s %5s %8s %11s %9s %8s %8s %9s  %s"
                  % ("band", "n", "v med", "Re(Z)", "phase", "coh2", "shuf", "CI(boot)", "trust"))
            got = {}
            for bn, lo, hi in BANDS:
                pairs = [(w[0], w[1]) for w in W]
                r = P._band_transfer(pairs, fs, P.NW_Z, [(bn, lo, hi)])[bn]
                idx = RNG.permutation(len(pairs))
                rs = P._band_transfer([(pairs[i][0], pairs[(idx[i] + 1) % len(pairs)][1])
                                       for i in range(len(pairs))], fs, P.NW_Z, [(bn, lo, hi)])[bn]
                bs = []
                for _ in range(200):
                    j = RNG.integers(0, len(pairs), len(pairs))
                    bs.append(P._band_transfer([pairs[k] for k in j], fs, P.NW_Z,
                                               [(bn, lo, hi)])[bn]["re_over_sxx"])
                blo, bhi = np.percentile(bs, [2.5, 97.5])
                trust = bool(np.isfinite(r["coh2"]) and r["coh2"] >= 0.10
                             and r["coh2"] >= 5.0 * max(rs["coh2"], 1e-9))
                vmed = float(np.median([np.mean(np.abs(w[2])) for w in W]))
                print("      %-8s %5d %8.2f %11.1f %8.1f° %8.3f %8.3f  [%6.0f,%6.0f]  %s"
                      % (bn, len(W), vmed, r["re_over_sxx"], r["phase_deg"], r["coh2"],
                         rs["coh2"], blo, bhi,
                         ("YES " + ("ANTI-DAMPED" if r["re_over_sxx"] < 0 else "damped"))
                         if trust else "NO"))
                got[bn] = dict(n=len(W), re_z=float(r["re_over_sxx"]),
                               phase_deg=float(r["phase_deg"]), coh2=float(r["coh2"]),
                               coh2_shuf=float(rs["coh2"]), lo=float(blo), hi=float(bhi),
                               trust=trust)
            OUT["r3"].setdefault(rt, {})[nm] = got

    hdr("R3b -- STOCK Re(Z) BY WHEEL-RATE REGIME.  The record's strongest anti-damping is in the\n"
        "       MICRO regime (1-13 deg/s): -3480 on the pooled r77/r78/r79 corpus.")
    R = L.ROUTES["97"]
    z = np.load(R["cache"] / "r97.npz", allow_pickle=True)
    t = np.asarray(z["t"], float)
    tq = np.asarray(z["tq"], float)
    rate_f = np.asarray(z["rate_f"], float) * DEG2RAD
    lat = np.asarray(z["cc_lat"], float) > 0.5
    press = np.asarray(z["cs_press"], float) > 0.5
    v = np.abs(np.asarray(z["cs_v"], float))
    fs = 1.0 / float(np.median(np.diff(t)))
    mask = lat & (~press) & (v > 0.5)
    W = P._wins(mask, t, P.NW_Z, P.HOP_Z, (rate_f, tq, v, np.abs(np.asarray(z["rate_c"], float))))
    for rlo, rhi, nm in ((0, 1, "STATIC   <1 deg/s"), (1, 13, "MICRO   1-13 deg/s"),
                         (13, 50, "RATCHET 13-50 deg/s"), (50, 200, "MACRO    >50 deg/s")):
        sel = [w for w in W if rlo <= float(np.median(w[3])) < rhi]
        print("\n  --- STOCK | %s : %d windows ---" % (nm, len(sel)))
        if len(sel) < 6:
            print("      🛑 NOT SCOREABLE (%d windows)." % len(sel))
            continue
        pairs = [(w[0], w[1]) for w in sel]
        for bn, lo, hi in (("6-9", 6.0, 9.0), ("9-12", 9.0, 12.0), ("18-22", 18.0, 22.0),
                           ("22-26", 22.0, 26.0), ("26-31", 26.0, 31.0)):
            r = P._band_transfer(pairs, fs, P.NW_Z, [(bn, lo, hi)])[bn]
            print("      %-8s Re(Z) %10.1f   phase %7.1f°  coh2 %.3f"
                  % (bn, r["re_over_sxx"], r["phase_deg"], r["coh2"]))
            OUT["r3"].setdefault("97_regime", {}).setdefault(nm, {})[bn] = dict(
                n=len(sel), re_z=float(r["re_over_sxx"]), coh2=float(r["coh2"]))


# =========================================================================================
def _matched_boot(A, B, key, nboot=2000, seed=3):
    """min(n)-weighted geometric-mean ratio B/A over matched cells, EPISODE-bootstrapped."""
    rng = np.random.default_rng(seed)
    cells = []
    for vlo, vhi in SPEED_BINS:
        for rlo, rhi in RATE_BINS:
            a = L.sel(L.sel(A, vlo=vlo, vhi=vhi), rlo=rlo, rhi=rhi)
            b = L.sel(L.sel(B, vlo=vlo, vhi=vhi), rlo=rlo, rhi=rhi)
            ga, gb = {}, {}
            for r in a:
                x = r.get(key, np.nan)
                if np.isfinite(x) and x > 0:
                    ga.setdefault((r["seg"], r["epi"]), []).append(x)
            for r in b:
                x = r.get(key, np.nan)
                if np.isfinite(x) and x > 0:
                    gb.setdefault((r["seg"], r["epi"]), []).append(x)
            na = sum(len(v) for v in ga.values())
            nb = sum(len(v) for v in gb.values())
            if na >= 5 and nb >= 5:
                cells.append(([np.asarray(v) for v in ga.values()],
                              [np.asarray(v) for v in gb.values()]))
    if not cells:
        return None

    def stat(C):
        num = den = 0.0
        for ga, gb in C:
            va, vb = np.concatenate(ga), np.concatenate(gb)
            w = min(len(va), len(vb))
            num += w * np.log(np.median(vb) / np.median(va))
            den += w
        return float(np.exp(num / den)) if den else np.nan
    pt = stat(cells)
    bs = []
    for _ in range(nboot):
        C = [([ga[j] for j in rng.integers(0, len(ga), len(ga))],
              [gb[j] for j in rng.integers(0, len(gb), len(gb))]) for ga, gb in cells]
        bs.append(stat(C))
    bs = np.array([x for x in bs if np.isfinite(x)])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return dict(r=pt, lo=float(lo), hi=float(hi), cells=len(cells))


def r4():
    hdr("R4 -- THE ENGAGED/MANUAL BAND CONTRAST ON STOCK, WITH A CI.\n"
        "     The record: engagement multiplies 6-9 Hz 2.8x, band contrast +0.413 [+0.146,+0.667]\n"
        "     over 30 routes / 235 blocks.  Contrast = log(ratio_6-9) - log(ratio_control).\n"
        "     Control band = 32-38 Hz, the kit's PRE-DECLARED negative control.")
    OUT["r4"] = {}
    for rt, lab in ARMS:
        we, wm = wins(rt, True), wins(rt, False)
        if len(wm) < 20:
            print("\n  %-14s only %d manual windows -- NOT SCOREABLE" % (lab, len(wm)))
            continue
        print("\n  --- %s ---" % lab)
        print("      %-8s %28s" % ("band", "matched eng/man  [95% CI]"))
        res = {}
        for bn in ("3-5", "6-9", "10-15", "15-22", "18-22", "22-26", "26-31", "32-38", "40-49"):
            m = _matched_boot(wm, we, "tq|" + bn)
            res[bn] = m
            if m:
                print("      %-8s %10.2f  [%6.2f, %6.2f]   (%d matched cells)"
                      % (bn, m["r"], m["lo"], m["hi"], m["cells"]))
            else:
                print("      %-8s  no matched cell" % bn)
        if res.get("6-9") and res.get("32-38"):
            c = np.log(res["6-9"]["r"] / res["32-38"]["r"])
            print("      ==> BAND CONTRAST log(6-9 / 32-38) = %+.3f   "
                  "(record: +0.413 [+0.146, +0.667])" % c)
            OUT["r4"][rt] = dict(build=lab, bands=res, contrast=float(c))
        else:
            OUT["r4"][rt] = dict(build=lab, bands=res)


def r5():
    hdr("R5 -- MATCHED CROSS-BUILD RATIOS vs STOCK, WITH EPISODE-BOOTSTRAP CIs.\n"
        "     ratio > 1 == the MODDED build carries MORE than stock in that band, at the same\n"
        "     speed and the same wheel rate.  32-38 Hz is the pre-declared negative control.")
    OUT["r5"] = {}
    for ch in ("tq", "rate_c"):
        print("\n  --- channel %s, engaged ---" % ch)
        for rt, lab in ARMS:
            if rt == "97":
                continue
            print("      %s vs STOCK:" % lab)
            for bn in ("3-5", "6-9", "10-15", "15-22", "18-22", "22-26", "26-31",
                       "32-38", "40-49"):
                m = _matched_boot(wins("97", True), wins(rt, True), ch + "|" + bn)
                if m:
                    print("         %-8s %8.2fx  [%6.2f, %6.2f]   (%d cells)"
                          % (bn, m["r"], m["lo"], m["hi"], m["cells"]))
                    OUT["r5"].setdefault(ch, {}).setdefault(rt, {})[bn] = m


PARTS = dict(r1=r1, r2=r2, r3=r3, r4=r4, r5=r5)

if __name__ == "__main__":
    for p in (sys.argv[1:] or list(PARTS)):
        PARTS[p]()
    Path(__file__).with_name("_stock_r97_resonance.json").write_text(
        json.dumps(OUT, indent=1, default=float))
    print("\n  wrote _stock_r97_resonance.json")
