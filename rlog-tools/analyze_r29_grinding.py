#!/usr/bin/env python3
"""analyze_r29_grinding.py -- what is the parking-lot "grinding" on V57, spectrally?

Route 75604b0a432fdc89_00000029 seg 0 (61.5 s), V57 on the car, operator demonstrating "grinding"
in a parking lot.

*** THE ENGAGEMENT TRAP THIS SCRIPT EXISTS TO AVOID ***
carState.cruiseState.enabled is TRUE in only 46/6150 frames on this route, which reads as "99.3%
disengaged". That is WRONG as a proxy for "openpilot is applying steering torque". The fork runs
lateral independently of cruise: carControl.latActive, the EPS's own STEER_CONTROL_ACTIVE (0x18F
byte4 bit3) and openpilot's own TX'd 0xE4 STEER_TORQUE_REQUEST all agree on 1581-1584 frames
(25.7%), and they agree with EACH OTHER to 99.85-99.93%. Use STEER_CONTROL_ACTIVE.

CONVENTIONS (kept identical to decode_two_angles.py so numbers are comparable across the kit):
  - raw periodogram, Hann window, NON-OVERLAPPING segments, per-segment detrend.
    P = mean over segments of |rfft(detrend(seg) * hann)|^2 . No 1/fs or 1/U normalisation.
  - band power = MEAN of P over the band's bins (not the sum).
  - K is the TRUE number of independent segments. Conditioned spectra are computed only inside
    CONTIGUOUS runs of the condition -- masked concatenation splices discontinuities into the
    series and manufactures broadband power. `--concat` reproduces the kit's older masked-
    concatenation behaviour for back-comparison.

  ⚠ fs = 100.01 Hz. A line at f is indistinguishable from one at (fs - f). Every frequency below
  is quoted as the sub-Nyquist alias; 22 Hz could be 78 Hz. The comma IMU cannot break the tie --
  it is also ~101 Hz, with 26-30 dropouts and a 2.7 s max gap on this route.

Usage:  python analyze_r29_grinding.py CACHE.npz [--concat]
        (build the cache with r29_extract.py, or pass rlogs to --build)
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

FS = 100.0146          # measured: 6150 samples / 61.4911 s
NFFT = 256             # 2.56 s, 0.3907 Hz bins -- the kit's standard
NFFT_HI = 512          # 5.12 s, 0.1954 Hz bins -- used for peak frequency / Q
BAND = (15.0, 27.0)    # the kit's standard comparison band


# ----------------------------------------------------------------------------- spectral primitives
def _blocks(x, nfft, detrend=True):
    """Yield detrended, Hann-windowed FFT power for each non-overlapping nfft block."""
    win = np.hanning(nfft)
    ramp = np.arange(nfft)
    for i in range(0, len(x) - nfft + 1, nfft):
        seg = np.asarray(x[i:i + nfft], float)
        if not np.all(np.isfinite(seg)):
            continue
        if detrend:
            c = np.polyfit(ramp, seg, 1)
            seg = seg - (c[0] * ramp + c[1])
        else:
            seg = seg - seg.mean()
        yield np.abs(np.fft.rfft(seg * win)) ** 2


def runs_of(mask, minlen):
    """Contiguous [start, stop) runs where mask is True and stop-start >= minlen."""
    m = np.asarray(mask, bool).astype(np.int8)
    d = np.diff(np.concatenate(([0], m, [0])))
    starts, stops = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    return [(a, b) for a, b in zip(starts, stops) if b - a >= minlen]


def spectrum(x, mask=None, nfft=NFFT, concat=False, detrend=True):
    """(freqs, P, K, nruns). Segments taken only inside contiguous runs unless concat=True."""
    x = np.asarray(x, float)
    f = np.fft.rfftfreq(nfft, 1 / FS)
    if mask is None:
        mask = np.ones(len(x), bool)
    acc, K, nr = np.zeros(len(f)), 0, 0
    if concat:
        seq = [x[np.asarray(mask, bool)]]
        nr = 1
    else:
        rr = runs_of(mask, nfft)
        seq = [x[a:b] for a, b in rr]
        nr = len(rr)
    for s in seq:
        for P in _blocks(s, nfft, detrend):
            acc += P
            K += 1
    return (f, acc / K, K, nr) if K else (f, None, 0, nr)


def bandpower(P, f, lo=BAND[0], hi=BAND[1]):
    sel = (f >= lo) & (f <= hi)
    return float(P[sel].mean()) if P is not None and sel.any() else np.nan


def peak_table(f, P, fmin=0.6, fmax=50.0, halfwin=6.0, exclude=1.5, min_prom=2.5):
    """Every local maximum in [fmin,fmax] with its local-floor prominence and -3 dB Q.

    floor(f0) = median of P over |f-f0| <= halfwin, excluding |f-f0| <= exclude.
    Q from the -3 dB points walked outward from the peak. The Hann main lobe sets a hard resolution
    floor on measurable Q: BW_min ~ 1.44 * fs/nfft, so Q_max ~ f0 / BW_min.
    """
    out = []
    df = f[1] - f[0]
    for j in range(1, len(P) - 1):
        if not (fmin <= f[j] <= fmax):
            continue
        if not (P[j] > P[j - 1] and P[j] >= P[j + 1]):
            continue
        near = (np.abs(f - f[j]) <= halfwin) & (np.abs(f - f[j]) > exclude) & (f > 0.3)
        if near.sum() < 5:
            continue
        floor = float(np.median(P[near]))
        prom = P[j] / floor if floor > 0 else np.inf
        if prom < min_prom:
            continue
        # parabolic peak refinement in log power
        y0, y1, y2 = np.log(P[j - 1] + 1e-300), np.log(P[j] + 1e-300), np.log(P[j + 1] + 1e-300)
        den = (y0 - 2 * y1 + y2)
        delta = 0.5 * (y0 - y2) / den if den != 0 else 0.0
        f0 = f[j] + np.clip(delta, -0.5, 0.5) * df
        # -3 dB width
        half = P[j] / 2.0
        lo = j
        while lo > 1 and P[lo] > half and P[lo - 1] < P[lo]:
            lo -= 1
        hi = j
        while hi < len(P) - 2 and P[hi] > half and P[hi + 1] < P[hi]:
            hi += 1
        bw = max(f[hi] - f[lo], df)
        out.append(dict(f=f0, P=float(P[j]), prom=float(prom), bw=float(bw),
                        Q=float(f0 / bw) if bw > 0 else np.inf, floor=floor))
    out.sort(key=lambda r: -r["prom"])
    return out


# ----------------------------------------------------------------------------------------- report
def hdr(s):
    print(f"\n{'=' * 100}\n{s}\n{'=' * 100}")


def main(cache, concat=False):
    d = dict(np.load(cache))
    n = len(d["t"])
    dur = d["t"][-1] - d["t"][0]
    sca = d["sca"] > 0.5                      # STEER_CONTROL_ACTIVE -- the real engagement flag
    eng = d["cs_eng"] > 0.5                   # cruiseState.enabled  -- the misleading one
    lat = d["cc_lat"] > 0.5
    hands = np.abs(d["tq"]) > 200
    v, ang = d["cs_v"], d["ang"]
    tq, rf, rc = d["tq"], d["rate_f"], d["rate_c"]
    probe = d["probe"].astype(int)
    res_nf = 1.44 * FS / NFFT
    res_hi = 1.44 * FS / NFFT_HI

    hdr(f"ROUTE 29 seg 0   n={n}  {dur:.2f} s  fs={FS:.4f} Hz   "
        f"[{'CONCAT (kit-legacy)' if concat else 'CONTIGUOUS-RUN segmentation'}]")
    print(f"  engagement:  cruiseState.enabled {eng.sum():5d} ({100*eng.mean():5.2f}%)   "
          f"latActive {lat.sum():5d} ({100*lat.mean():5.2f}%)   "
          f"STEER_CONTROL_ACTIVE {sca.sum():5d} ({100*sca.mean():5.2f}%)")
    print(f"  vEgo {v.min():.2f}..{v.max():.2f} m/s (mean {v.mean():.2f})   "
          f"angle {ang.min():.0f}..{ang.max():.0f} deg   |driver tq|>200 in {100*hands.mean():.1f}%")
    print(f"  0xE4 commanded |torque| : SCA=1 mean {np.abs(d['e4tq'][sca]).mean():.0f}  "
          f"(p95 4096 = RAIL)   SCA=0 mean {np.abs(d['e4tq'][~sca]).mean():.2f}")
    print(f"  resolution floor on Q: nfft={NFFT} -> BW>={res_nf:.3f} Hz (Q<={22/res_nf:.0f} at 22 Hz);"
          f"  nfft={NFFT_HI} -> BW>={res_hi:.3f} Hz (Q<={22/res_hi:.0f})")

    chans = [("TORQUE 0x18F (counts)", tq), ("RATE_fine 0x18F (deg/s)", rf),
             ("RATE_coarse 0x14A (deg/s)", rc), ("ANGLE 0x14A (deg)", ang)]

    # ---------------------------------------------------------------- A. whole-band peak inventory
    hdr("A. WHOLE-ROUTE SPECTRA, 0.6-50 Hz -- every line above 2.5x the local floor")
    for name, x in chans:
        for nf in (NFFT_HI, NFFT):
            f, P, K, nr = spectrum(x, None, nf, concat)
            if P is None:
                continue
            pk = peak_table(f, P)
            print(f"\n  {name}   nfft={nf}  K={K} independent segments  ({nf/FS:.2f} s each, "
                  f"{FS/nf:.4f} Hz bins)")
            if not pk:
                print("     no line above 2.5x floor")
                continue
            print(f"     {'f (Hz)':>8s} {'power':>12s} {'prom':>7s} {'-3dB BW':>9s} {'Q':>7s}")
            for r in pk[:10]:
                qs = "  >res" if r["bw"] <= 1.01 * (1.44 * FS / nf) else f"{r['Q']:7.1f}"
                print(f"     {r['f']:8.2f} {r['P']:12.4g} {r['prom']:6.1f}x {r['bw']:9.3f}{qs}")

    # ------------------------------------------------------------------------- B. conditioned bands
    hdr(f"B. CONDITIONED {BAND[0]:.0f}-{BAND[1]:.0f} Hz BAND POWER   "
        f"(nfft={NFFT}; K = true independent segments; n<50 => refused)")
    conds = [
        ("ALL frames", np.ones(n, bool)),
        ("-- ENGAGEMENT --", None),
        ("cruiseState.enabled=1", eng),
        ("cruiseState.enabled=0", ~eng),
        ("STEER_CONTROL_ACTIVE=1", sca),
        ("STEER_CONTROL_ACTIVE=0", ~sca),
        ("SCA=1 + hands-off(|tq|<=200)", sca & ~hands),
        ("SCA=1 + hands-on (|tq|>200)", sca & hands),
        ("SCA=0 + hands-off", ~sca & ~hands),
        ("SCA=0 + hands-on", ~sca & hands),
        ("-- SPEED (m/s) --", None),
        ("v<0.05 (stopped)", v < 0.05),
        ("0.05<=v<0.5", (v >= 0.05) & (v < 0.5)),
        ("0.5<=v<1.0", (v >= 0.5) & (v < 1.0)),
        ("1.0<=v<1.5", (v >= 1.0) & (v < 1.5)),
        ("v>=1.5", v >= 1.5),
        ("-- |ANGLE| (deg) --", None),
        ("|ang| 0-2", np.abs(ang) < 2),
        ("|ang| 2-5", (np.abs(ang) >= 2) & (np.abs(ang) < 5)),
        ("|ang| 5-10", (np.abs(ang) >= 5) & (np.abs(ang) < 10)),
        ("|ang| 10-20", (np.abs(ang) >= 10) & (np.abs(ang) < 20)),
        ("|ang| >=20", np.abs(ang) >= 20),
    ]
    print(f"  {'condition':30s} {'n':>6s} {'K':>4s} {'runs':>5s} | "
          + " ".join(f"{c[0].split()[0]:>12s}" for c in chans) + " |  peak/prom (TORQUE)")
    for nm, sel in conds:
        if sel is None:
            print(f"  {nm}")
            continue
        if sel.sum() < 50:
            print(f"  {nm:30s} {int(sel.sum()):6d}   -- n<50, REFUSED --")
            continue
        row, K, nr = "", 0, 0
        for _, x in chans:
            f, P, k, r = spectrum(x, sel, NFFT, concat)
            K, nr = max(K, k), max(nr, r)
            row += f"{bandpower(P, f):13.4g}" if P is not None else f"{'--':>13s}"
        f, P, k, _ = spectrum(tq, sel, NFFT, concat)
        tail = "   (no complete segment)"
        if P is not None:
            b = (f >= BAND[0]) & (f <= BAND[1])
            ref = (f >= 6) & (f <= 40) & ~b
            j = int(np.argmax(np.where(b, P, -np.inf)))
            tail = f"   {f[j]:5.2f} Hz {P[j]/np.median(P[ref]):5.2f}x"
        print(f"  {nm:30s} {int(sel.sum()):6d} {K:4d} {nr:5d} |{row} |{tail}")

    # ----------------------------------------------------------- angle-controlled engagement effect
    hdr("B2. SCA=1 vs SCA=0 CONTROLLED ON |ANGLE| (the kit's known 2 Hz angle confound)")
    print(f"  {'|angle| bin':>12s} | {'n(SCA1)':>8s} {'K':>3s} {'P15-27':>11s} {'peak':>7s} "
          f"{'prom':>6s} | {'n(SCA0)':>8s} {'K':>3s} {'P15-27':>11s} {'peak':>7s} {'prom':>6s} | "
          f"{'ratio':>8s}")
    for lo, hi in ((0, 2), (2, 5), (5, 10), (10, 20), (20, 1e9)):
        ab = (np.abs(ang) >= lo) & (np.abs(ang) < hi)
        cells = []
        for m in (ab & sca, ab & ~sca):
            f, P, K, _ = spectrum(tq, m, NFFT, concat)
            if P is None:
                cells.append((int(m.sum()), K, np.nan, np.nan, np.nan))
                continue
            b = (f >= BAND[0]) & (f <= BAND[1])
            ref = (f >= 6) & (f <= 40) & ~b
            j = int(np.argmax(np.where(b, P, -np.inf)))
            cells.append((int(m.sum()), K, bandpower(P, f), f[j], P[j] / np.median(P[ref])))
        (n1, k1, p1, f1, r1), (n0, k0, p0, f0, r0) = cells
        rat = p1 / p0 if (np.isfinite(p1) and np.isfinite(p0) and p0 > 0) else np.nan
        fmt = lambda x, w, p: (f"{x:{w}.{p}f}" if np.isfinite(x) else f"{'--':>{w}s}")
        print(f"  {f'{lo}-{hi:g}':>12s} | {n1:8d} {k1:3d} {p1:11.4g} {fmt(f1,7,2)} {fmt(r1,6,2)} | "
              f"{n0:8d} {k0:3d} {p0:11.4g} {fmt(f0,7,2)} {fmt(r0,6,2)} | {fmt(rat,8,2)}")

    # -------------------------------------------------------------------------- C. time-localisation
    hdr("C. TIME-LOCALISATION -- 1.28 s hops, nfft=256 (overlapped for DISPLAY ONLY; K not quotable)")
    nf, hop = NFFT, NFFT // 2
    f = np.fft.rfftfreq(nf, 1 / FS)
    b = (f >= BAND[0]) & (f <= BAND[1])
    ref = (f >= 6) & (f <= 40) & ~b
    lowb = (f >= 1.0) & (f <= 8.0)
    rows = []
    for i in range(0, n - nf + 1, hop):
        seg = tq[i:i + nf]
        c = np.polyfit(np.arange(nf), seg, 1)
        P = np.abs(np.fft.rfft((seg - np.polyval(c, np.arange(nf))) * np.hanning(nf))) ** 2
        j = int(np.argmax(np.where(b, P, -np.inf)))
        rows.append((d["t"][i], d["t"][i + nf - 1], P[b].mean(), f[j], P[j] / np.median(P[ref]),
                     P[lowb].mean(), sca[i:i + nf].mean(), np.abs(tq[i:i + nf]).mean(),
                     v[i:i + nf].mean(), np.abs(ang[i:i + nf]).mean(),
                     np.abs(rf[i:i + nf]).mean()))
    R = np.array(rows)
    order = np.argsort(-R[:, 2])
    print(f"  {'t0':>6s} {'t1':>6s} {'P15-27':>11s} {'fpk':>6s} {'prom':>6s} {'P1-8':>11s} "
          f"{'SCA%':>5s} {'|tq|':>6s} {'v':>5s} {'|ang|':>7s} {'|rate|':>7s}")
    print("  --- TOP 12 WINDOWS BY 15-27 Hz POWER ---")
    for i in order[:12]:
        r = R[i]
        print(f"  {r[0]:6.2f} {r[1]:6.2f} {r[2]:11.4g} {r[3]:6.2f} {r[4]:6.2f} {r[5]:11.4g} "
              f"{100*r[6]:4.0f}% {r[7]:6.0f} {r[8]:5.2f} {r[9]:7.1f} {r[10]:7.1f}")
    print("  --- TOP 8 WINDOWS BY 15-27 Hz PROMINENCE (a resonance, not just activity) ---")
    for i in np.argsort(-R[:, 4])[:8]:
        r = R[i]
        print(f"  {r[0]:6.2f} {r[1]:6.2f} {r[2]:11.4g} {r[3]:6.2f} {r[4]:6.2f} {r[5]:11.4g} "
              f"{100*r[6]:4.0f}% {r[7]:6.0f} {r[8]:5.2f} {r[9]:7.1f} {r[10]:7.1f}")
    print("  --- FULL TIMELINE (every 4th window = 5.12 s) ---")
    for i in range(0, len(R), 4):
        r = R[i]
        print(f"  {r[0]:6.2f} {r[1]:6.2f} {r[2]:11.4g} {r[3]:6.2f} {r[4]:6.2f} {r[5]:11.4g} "
              f"{100*r[6]:4.0f}% {r[7]:6.0f} {r[8]:5.2f} {r[9]:7.1f} {r[10]:7.1f}")
    print(f"\n  correlation of window 15-27 Hz power with:  |driver tq| "
          f"{np.corrcoef(R[:,2], R[:,7])[0,1]:+.3f}   |rate| {np.corrcoef(R[:,2], R[:,10])[0,1]:+.3f}"
          f"   SCA frac {np.corrcoef(R[:,2], R[:,6])[0,1]:+.3f}   vEgo "
          f"{np.corrcoef(R[:,2], R[:,8])[0,1]:+.3f}   |angle| {np.corrcoef(R[:,2], R[:,9])[0,1]:+.3f}")
    print(f"  same for 15-27 Hz PROMINENCE:               |driver tq| "
          f"{np.corrcoef(R[:,4], R[:,7])[0,1]:+.3f}   |rate| {np.corrcoef(R[:,4], R[:,10])[0,1]:+.3f}"
          f"   SCA frac {np.corrcoef(R[:,4], R[:,6])[0,1]:+.3f}   vEgo "
          f"{np.corrcoef(R[:,4], R[:,8])[0,1]:+.3f}   |angle| {np.corrcoef(R[:,4], R[:,9])[0,1]:+.3f}")

    # ------------------------------------------------------------------------ D. baseline comparison
    hdr("D. COMPARISON TO THE KIT'S RECORDED PARKING-LOT BASELINES (TORQUE, 15-27 Hz, nfft=256)")
    print("  recorded: V56 route24 7.66e4 | V55 route1c 1.94e5 | R13 6.59e4   "
          "(engaged + hands-off, counts^2)")
    print(f"  ⚠ those were computed with MASKED CONCATENATION. Both conventions are given here.")
    print(f"  {'V57 subset':38s} {'n':>6s} {'K':>4s} {'runs':>5s} {'P15-27 (counts^2)':>19s}")
    subsets = [("SCA=1 + hands-off (like-for-like)", sca & ~hands),
               ("SCA=1 (any hands)", sca),
               ("SCA=0 + hands-off", ~sca & ~hands),
               ("cruiseState=1 (n=46)", eng),
               ("ALL frames", np.ones(n, bool))]
    for mode, lbl in ((False, "contiguous-run"), (True, "masked-concat (kit-legacy)")):
        print(f"   [{lbl}]")
        for nm, sel in subsets:
            f, P, K, nr = spectrum(tq, sel, NFFT, mode)
            val = f"{bandpower(P, f):19.4g}" if P is not None else f"{'-- no segment --':>19s}"
            print(f"   {nm:38s} {int(sel.sum()):6d} {K:4d} {nr:5d} {val}")
    f1, P1, K1, _ = spectrum(tq, sca & ~hands, NFFT, concat)
    f0, P0, K0, _ = spectrum(tq, ~sca & ~hands, NFFT, concat)
    if P1 is not None and P0 is not None:
        a1, a0 = bandpower(P1, f1), bandpower(P0, f0)
        print(f"\n  V57 SCA=1/SCA=0 ratio, hands-off, 15-27 Hz = {a1/a0:.2f}x   "
              f"(absolute: {a1:.4g} vs {a0:.4g}, K={K1}/{K0})")
        print(f"  recorded engaged/disengaged ratios on the SENSOR: V56 786x, V55 877x, "
              f"one test 14750x")

    # ------------------------------------------------------------------------------- E. V57 probe
    hdr("E. THE V57 DEADBAND-GATE PROBE (CAN 0x14A byte4)")
    BIT = dict(LIVE=0x80, GATE=0x40, RAMP=0x20, ZERO=0x10, NEG=0x08)
    field = (probe >> 3) & 0x1F
    print(f"  field==0 (CAVE DID NOT FIRE): {int((field == 0).sum())}/{n}   "
          f"bit7 LIVENESS set: {int((probe & 0x80 != 0).sum())}/{n}")
    print(f"\n  {'byte4':>6s} {'count':>6s} {'%':>6s}  {'bit7':>4s} {'bit6':>4s} {'bit5':>4s} "
          f"{'bit4':>4s} {'bit3':>4s}  {'bits2:0':>7s}   meaning")
    mean_names = {"bit7": "LIVENESS", "bit6": "gate ENABLED (gp-0x6806==0)",
                  "bit5": "ramp gain LIVE (gp-0x69b0!=0)", "bit4": "gate out == 0",
                  "bit3": "gate out < 0"}
    for val, c in Counter(probe.tolist()).most_common():
        bits = [(val >> k) & 1 for k in (7, 6, 5, 4, 3)]
        txt = ", ".join(nm for nm, bb in zip(["LIVE", "gateEN", "rampLIVE", "out==0", "out<0"], bits)
                        if bb) or "(none set)"
        print(f"  0x{val:02X}   {c:6d} {100*c/n:5.1f}%  " +
              "".join(f"{b:4d}" for b in bits) + f"  {val & 7:7d}   {txt}")
    print(f"\n  bit meanings: " + "; ".join(f"{k}={v}" for k, v in mean_names.items()))

    gate = (probe & BIT["GATE"]) != 0
    ramp = (probe & BIT["RAMP"]) != 0
    zero = (probe & BIT["ZERO"]) != 0
    neg = (probe & BIT["NEG"]) != 0
    print(f"\n  {'condition':32s} {'n':>6s} {'gateEN':>8s} {'rampLIVE':>9s} {'out==0':>8s} "
          f"{'out<0':>8s} {'out>0':>8s}")
    for nm, sel in [("ALL", np.ones(n, bool)), ("STEER_CONTROL_ACTIVE=1", sca),
                    ("STEER_CONTROL_ACTIVE=0", ~sca), ("SCA=1 + hands-off", sca & ~hands),
                    ("SCA=1 + hands-on", sca & hands), ("SCA=0 + hands-off", ~sca & ~hands),
                    ("SCA=0 + hands-on", ~sca & hands),
                    ("cruiseState.enabled=1", eng),
                    ("v<0.5 m/s", v < 0.5), ("v>=0.5 m/s", v >= 0.5),
                    ("|ang|<2", np.abs(ang) < 2), ("|ang|>=20", np.abs(ang) >= 20)]:
        if sel.sum() < 50:
            print(f"  {nm:32s} {int(sel.sum()):6d}   -- n<50, REFUSED --")
            continue
        pos = (~zero) & (~neg)
        print(f"  {nm:32s} {int(sel.sum()):6d} {100*gate[sel].mean():7.2f}% "
              f"{100*ramp[sel].mean():8.2f}% {100*zero[sel].mean():7.2f}% "
              f"{100*neg[sel].mean():7.2f}% {100*pos[sel].mean():7.2f}%")
    print(f"\n  corr(bit6 gateEN, STEER_CONTROL_ACTIVE) = "
          f"{np.corrcoef(gate.astype(float), sca.astype(float))[0,1]:+.4f}   "
          f"(gate ENABLED means gp-0x6806==0, i.e. NOT steering => expect ~-1)")
    print(f"  bit6 transitions: {int((np.diff(gate.astype(int))!=0).sum())}   "
          f"bit4 transitions: {int((np.diff(zero.astype(int))!=0).sum())}   "
          f"bit3 transitions: {int((np.diff(neg.astype(int))!=0).sum())}")

    print(f"\n  -- SPECTRUM OF bit4 (gate output == 0): is there a chattering sign relay? --")
    for nm, sel in [("ALL frames", np.ones(n, bool)), ("SCA=1", sca), ("SCA=0", ~sca),
                    ("SCA=1 + hands-off", sca & ~hands), ("SCA=0 + hands-on", ~sca & hands)]:
        f, P, K, nr = spectrum(zero.astype(float), sel, NFFT, concat, detrend=False)
        if P is None:
            print(f"    {nm:22s} n={int(sel.sum()):5d}  no complete segment")
            continue
        b = (f >= BAND[0]) & (f <= BAND[1])
        ref = (f >= 6) & (f <= 40) & ~b
        j = int(np.argmax(np.where(b, P, -np.inf)))
        fl = np.median(P[ref])
        print(f"    {nm:22s} n={int(sel.sum()):5d} K={K:3d} runs={nr:2d}  peak {f[j]:5.2f} Hz  "
              f"prom {P[j]/fl:5.2f}x   P(15-27)={bandpower(P,f):.4g}")
    print("    (a real relay chattering at the mode frequency gives a SHARP high-prominence line;")
    print("     prominence ~1-3 with a wandering peak is noise)")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(1)
    sys.exit(main(Path(args[0]), "--concat" in sys.argv))
