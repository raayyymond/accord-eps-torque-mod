#!/usr/bin/env python3
"""CROSS-BUILD RINGDOWN Q, done properly.  Supersedes `studies/damping-q/r67_ringdown_q.py`, which FAILED.

WHY THE FIRST ATTEMPT FAILED, so this one can be audited against it
  1. NO GOODNESS-OF-FIT GATE. It fitted envelopes that were not decays and returned Q = 1028
     (tau = 11.8 s) on V80 seg13. Fixed: R^2 and the fitted decay RANGE are reported for every
     edge, and a gate rejects anything below threshold.
  2. FILTER TRANSIENT. The narrowband was 6 Hz wide, so its impulse response (~1/6 Hz = 0.17 s) is
     COMPARABLE TO THE DECAY BEING MEASURED -- the first one or two 0.1 s bins were the filter,
     not the plant, which is what produced the spurious "Q = 7 at high amplitude". Fixed: COMPLEX
     DEMODULATION at f0 with an explicitly stated lowpass bandwidth, so the time resolution is a
     declared parameter (tau_filter = 1/(2*pi*B_lp)) rather than an accident of the band edges.
  3. THE FLOOR WAS NOT A FLOOR. The post-edge envelope is still decaying at t+2..+5, so "the floor"
     depended entirely on the window: I measured 8.7 ct and v81loop measured 16.3 ct on the same
     edge. Fixed: the floor is taken from the LATEST available quiet disengaged stretch, its window
     is printed, and the fit is truncated at 3x it.

🛑 THE CONFOUND, STATED UP FRONT: the falling edge switches mode 26 -> 24, and mode 24 is
   BYTE-STOCK on all three builds (V75/V81's CY0 lever dosed the ENGAGED column only). So this
   measures the DISENGAGED plant. **PREDICTION: no dose ladder.** A ladder would mean the dosed
   column is still live after disengage, which would be the more interesting outcome.

Usage:  python studies/damping-q/r67_ringdown_q2.py
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

RLOGDIR = ROOT / "analysis-2020accord" / "rlogs"
BUILDS = {
    "V76/r65": ("75604b0a432fdc89_00000065--ae43aa0f27", ROOT / "_scratch/cache/r65", "r65s", 11, 1.3866),
    "V81/r67": ("75604b0a432fdc89_00000067--9b3ebbe218", ROOT / "_scratch/cache/r67x", "r67xs", 14, 1.5798),
    "V80/r66": ("75604b0a432fdc89_00000066--276b942769", ROOT / "_scratch/cache/r66x", "r66xs", 15, 4.1597),
}

B_LP = 4.0            # demodulation lowpass, Hz -> analysis bandwidth 8 Hz, tau_filter 0.040 s
FIT_START = 0.15      # s after the edge; > 3 tau_filter, so the filter has settled
PRE_MIN = 120.0       # ct: the pre-edge ring must be this big to have anything to decay
R2_MIN = 0.95
RANGE_MIN = 4.0       # the fit must span at least this much amplitude decay
N_MIN = 15
OUT = {}


def hdr(s):
    print("\n" + "=" * 106)
    print(s)
    print("=" * 106, flush=True)


def i16(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 0x10000 if v & 0x8000 else v


def candidate_segments(build):
    """Cheap pass over the CACHE: which segments hold a clean falling edge with a real ring?"""
    _, cache, pfx, nseg, _ = BUILDS[build]
    out = []
    for s in range(nseg):
        p = cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = {k: v for k, v in np.load(p).items()}
        t, lat = np.asarray(d["t"], float), np.asarray(d["cc_lat"], float) > 0.5
        fs = 1.0 / np.median(np.diff(t))
        g = int(3 * fs)
        for i in np.flatnonzero(np.diff(lat.astype(int)) < 0) + 1:
            if i - g < 0 or i + g >= len(t):
                continue
            if lat[i - g:i].mean() > 0.95 and lat[i:i + g].mean() < 0.05:
                out.append(s)
                break
    return sorted(set(out))


def native(route, seg):
    from rlog_parse import read_messages
    p = RLOGDIR / f"{route}--{seg}--rlog.zst"
    if not p.exists():
        return None
    t, q, lt, lv, vt, vv = [], [], [], [], [], []
    for e in read_messages(p):
        try:
            w = e.which()
        except Exception:
            continue
        tm = e.logMonoTime * 1e-9
        if w == "can":
            for m in e.can:
                if int(m.src) == 1 and int(m.address) == 0x18F:
                    d = bytes(m.dat)
                    if len(d) >= 2:
                        t.append(tm); q.append(i16(d, 0) * -1.0)
        elif w == "carControl":
            lt.append(tm); lv.append(float(bool(e.carControl.latActive)))
        elif w == "carState":
            vt.append(tm); vv.append(float(e.carState.vEgo))
    if len(t) < 1000 or not lt:
        return None
    t = np.array(t); q = np.array(q); t0 = t[0]; t -= t0
    lat = np.interp(t, np.array(lt) - t0, np.array(lv)) > 0.5
    v = (np.interp(t, np.array(vt) - t0, np.array(vv)) if vt else np.full(len(t), np.nan))
    return t, q, lat, v


def demod(t, q, fs, f0, b_lp=B_LP):
    """Complex demodulation at f0 with a stated lowpass. Envelope = |lowpass(x * e^{-i2*pi*f0*t})|.

    Time resolution is an explicit parameter: tau_filter = 1/(2*pi*b_lp) = 0.040 s at b_lp = 4 Hz,
    against decays of 0.1-0.3 s. The first `FIT_START` s after an edge is discarded regardless.
    """
    z = (q - q.mean()) * np.exp(-2j * np.pi * f0 * t)
    Z = np.fft.fft(z)
    f = np.fft.fftfreq(len(z), 1 / fs)
    Z[np.abs(f) > b_lp] = 0
    return 2.0 * np.abs(np.fft.ifft(Z))


def peak_f0(q, fs, lo=22.0, hi=34.0):
    w = np.hanning(len(q))
    X = np.abs(np.fft.rfft((q - q.mean()) * w))
    f = np.fft.rfftfreq(len(q), 1 / fs)
    k = int(np.argmax(np.where((f >= lo) & (f <= hi), X, 0)))
    if k <= 0 or k >= len(X) - 1:
        return float(f[k])
    y0, y1, y2 = np.log(X[k - 1] + 1e-30), np.log(X[k] + 1e-30), np.log(X[k + 1] + 1e-30)
    den = y0 - 2 * y1 + y2
    return float(f[k] + (0.5 * (y0 - y2) / den if den else 0.0) * (f[1] - f[0]))


def analyse_edge(t, q, lat, v, fs, i):
    te = float(t[i])
    pre = (t >= te - 3.0) & (t < te - 0.05)
    if pre.sum() < int(1.5 * fs):
        return None
    f0 = peak_f0(q[pre], fs)
    if not (22.0 < f0 < 34.0):
        return None
    env = demod(t, q, fs, f0)
    a_pre = float(np.percentile(env[pre], 90))

    # floor: the LATEST quiet disengaged stretch available on this segment
    fl_win = None
    for lo, hi in ((6.0, 12.0), (4.0, 8.0), (3.0, 6.0)):
        m = (~lat) & (t > te + lo) & (t < te + hi)
        if m.sum() > int(0.8 * fs):
            fl_win = (lo, hi)
            floor = float(np.median(env[m]))
            break
    if fl_win is None:
        return None

    m = (t >= te + FIT_START) & (t <= te + 4.0) & (env > 3 * floor)
    if m.sum() < N_MIN:
        return dict(te=te, f0=f0, pre=a_pre, floor=floor, fl_win=fl_win, n=int(m.sum()),
                    rng=np.nan, tau=np.nan, Q=np.nan, r2=np.nan,
                    v=float(np.nanmean(np.abs(v[pre]))) * 3.6, ok=False,
                    why="fewer than %d samples above 3x floor" % N_MIN)
    # contiguity: stop at the first gap so a re-excitation cannot join the fit
    idx = np.flatnonzero(m)
    brk = np.flatnonzero(np.diff(idx) > 1)
    if len(brk):
        idx = idx[:brk[0] + 1]
    if len(idx) < N_MIN:
        return dict(te=te, f0=f0, pre=a_pre, floor=floor, fl_win=fl_win, n=len(idx),
                    rng=np.nan, tau=np.nan, Q=np.nan, r2=np.nan,
                    v=float(np.nanmean(np.abs(v[pre]))) * 3.6, ok=False,
                    why="contiguous run too short")
    tt, ee = t[idx] - te, env[idx]
    y = np.log(ee)
    sl, ic = np.polyfit(tt, y, 1)
    yh = sl * tt + ic
    ss = float(1 - np.sum((y - yh) ** 2) / max(np.sum((y - y.mean()) ** 2), 1e-30))
    rng = float(ee[0] / ee[-1]) if ee[-1] > 0 else np.nan
    tau = -1.0 / sl if sl < 0 else np.nan
    Q = tau * np.pi * f0 if np.isfinite(tau) else np.nan
    ok = bool(np.isfinite(Q) and ss >= R2_MIN and rng >= RANGE_MIN and len(idx) >= N_MIN)
    return dict(te=te, f0=f0, pre=a_pre, floor=floor, fl_win=fl_win, n=len(idx), rng=rng,
                tau=tau, Q=Q, r2=ss, v=float(np.nanmean(np.abs(v[pre]))) * 3.6, ok=ok,
                why="" if ok else f"R2 {ss:.3f} / range {rng:.1f}x")


def main():
    print(f"  demodulation lowpass B = {B_LP} Hz  (analysis bandwidth {2 * B_LP} Hz, "
          f"tau_filter = {1 / (2 * np.pi * B_LP):.3f} s)")
    print(f"  fit starts {FIT_START} s after the edge (> 3 tau_filter), truncated at 3x floor")
    print(f"  gates: R2 >= {R2_MIN}, decay range >= {RANGE_MIN}x, n >= {N_MIN}, "
          f"pre-edge ring >= {PRE_MIN} ct")
    for b, (route, cache, pfx, nseg, k) in BUILDS.items():
        hdr(f"{b}   k = {k}")
        segs = candidate_segments(b)
        print(f"  segments with a clean falling edge (3 s guard both sides): {segs}")
        rows = []
        for s in segs:
            r = native(route, s)
            if r is None:
                continue
            t, q, lat, v = r
            fs = (len(t) - 1) / (t[-1] - t[0])
            g = int(3 * fs)
            for i in np.flatnonzero(np.diff(lat.astype(int)) < 0) + 1:
                if i - g < 0 or i + g >= len(t):
                    continue
                if not (lat[i - g:i].mean() > 0.95 and lat[i:i + g].mean() < 0.05):
                    continue
                a = analyse_edge(t, q, lat, v, fs, i)
                if a is None:
                    continue
                a["seg"] = s
                rows.append(a)
        if not rows:
            print("  no analysable edge on this build.")
            OUT[b] = dict(k=k, edges=[])
            continue
        print(f"\n  {'seg':>3s} {'t_e':>7s} {'v kmh':>6s} {'f0':>6s} {'pre p90':>8s} "
              f"{'floor':>6s} {'flwin':>9s} {'n':>4s} {'range':>7s} {'tau':>7s} {'Q':>7s} "
              f"{'R2':>6s}  verdict")
        for a in sorted(rows, key=lambda z: -z["pre"]):
            vd = "USE" if a["ok"] else ("no ring" if a["pre"] < PRE_MIN else "REJECT " + a["why"])
            print(f"  {a['seg']:3d} {a['te']:7.2f} {a['v']:6.1f} {a['f0']:6.2f} {a['pre']:8.1f} "
                  f"{a['floor']:6.1f} {str(a['fl_win']):>9s} {a['n']:4d} "
                  f"{a['rng']:7.1f} {a['tau']:7.3f} {a['Q']:7.1f} {a['r2']:6.3f}  {vd}")
        good = [a for a in rows if a["ok"] and a["pre"] >= PRE_MIN]
        OUT[b] = dict(k=k, edges=rows, n_good=len(good),
                      Q=[a["Q"] for a in good], v=[a["v"] for a in good])
        if good:
            qs = np.array([a["Q"] for a in good])
            print(f"\n  ACCEPTED: n={len(good)}  Q median {np.median(qs):.1f}  "
                  f"range [{qs.min():.1f}, {qs.max():.1f}]  "
                  f"speeds {[round(a['v']) for a in good]} km/h")
        else:
            print("\n  ACCEPTED: none -- see the verdict column for why.")

    hdr("THE LADDER")
    print(f"  {'build':10s} {'k':>7s} {'n':>3s} {'Q median':>9s} {'Q range':>16s} "
          f"{'speeds (km/h)':>22s}")
    for b, (_, _, _, _, k) in BUILDS.items():
        g = OUT[b].get("Q") or []
        if g:
            print(f"  {b:10s} {k:7.4f} {len(g):3d} {np.median(g):9.1f} "
                  f"[{min(g):6.1f},{max(g):6.1f}] "
                  f"{str([round(x) for x in OUT[b]['v']]):>22s}")
        else:
            print(f"  {b:10s} {k:7.4f}   0  {'-- none --':>9s}")
    print("\n  🛑 Compare against the PREDICTION at the top of this file: mode 24 is byte-stock on")
    print("     all three builds, so NO dose ladder is expected. This measures the DISENGAGED")
    print("     plant and cannot speak to the engaged damper directly.")
    (ROOT / "_scratch/cache/r67x" / "r67_ringdown_q2.json").write_text(
        json.dumps(OUT, indent=1, default=lambda o: None if o is None else
                   (float(o) if isinstance(o, (int, float, np.floating)) else str(o))))
    print(f"\nwrote {ROOT / '_scratch/cache/r67x' / 'r67_ringdown_q2.json'}")


if __name__ == "__main__":
    main()
