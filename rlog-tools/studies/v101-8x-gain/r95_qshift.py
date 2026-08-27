#!/usr/bin/env python3
r"""V101 vs V100 -- IS THE 23 Hz PEAK TALLER *AND NARROWER*?

  MORE EXCITATION into an unchanged resonance  =>  peak height up, -3 dB WIDTH UNCHANGED.
  MORE LOOP GAIN (a pole moving toward the imaginary axis) => height up AND WIDTH DOWN,
  usually with a small frequency shift.

Matched speed: only the 20-70 km/h bins, which both routes cover.  Welch nfft=1024
(df = 0.099 Hz) inside contiguous engaged runs, so the width is resolved to ~10 bins.

Also re-runs the GRIP/RELEASE event profiles at full time resolution so the decay/re-growth
time constant can be read off rather than reported as "0.00 s".
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
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2].parent
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import r95_lib as L  # noqa: E402

ROUTES = {"95": ("V101", "_scratch/cache/r95/r95.npz"), "85": ("V100", "_scratch/cache/r85/r85.npz")}
out = {}


def runs_break(mask, t, min_n):
    idx = np.where(mask)[0]
    if not len(idx):
        return []
    o, s, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i != prev + 1 or (t[i] - t[prev]) > 0.05:
            if prev - s + 1 >= min_n:
                o.append((s, prev + 1))
            s = i
        prev = i
    if prev - s + 1 >= min_n:
        o.append((s, prev + 1))
    return o


NFFT = 1024
print("=" * 100)
print("PEAK HEIGHT AND -3 dB WIDTH, 20-70 km/h engaged, Welch nfft=1024")
print("=" * 100)
for ch in ("tq", "rate_f"):
    print(f"\n### {ch}")
    print(f"    {'route':6s} {'build':6s} {'K':>4s} {'f_peak':>8s} {'PSD_peak':>11s} "
          f"{'-3dB width':>11s} {'Q=f/BW':>8s} {'floor(15-19Hz)':>15s} {'peak/floor':>11s}")
    rec = {}
    for r, (lab, stem) in ROUTES.items():
        z = dict(np.load(ROOT / "analysis-2020accord" / stem, allow_pickle=True))
        t = np.asarray(z["t"], float)
        FS = 1.0 / np.median(np.diff(t))
        lat = np.asarray(z["cc_lat"], float) > 0.5
        vk = np.abs(np.asarray(z["cs_v"], float)) * 3.6
        m = lat & (vk >= 20) & (vk < 70)
        x = np.asarray(z[ch], float)
        win = np.hanning(NFFT)
        f = np.fft.rfftfreq(NFFT, 1 / FS)
        P = np.zeros(len(f))
        K = 0
        for a, b in runs_break(m, t, NFFT):
            for i in range(a, b - NFFT + 1, NFFT // 2):
                seg = np.nan_to_num(x[i:i + NFFT] - np.nanmean(x[i:i + NFFT]))
                P += np.abs(np.fft.rfft(seg * win)) ** 2
                K += 1
        if K == 0:
            print(f"    {r:6s} {lab:6s}   no windows")
            continue
        P /= K * (win ** 2).sum() * FS
        band = (f >= 19.0) & (f <= 29.0)
        fb, Pb = f[band], P[band]
        i = int(np.argmax(Pb))
        pk, fpk = float(Pb[i]), float(fb[i])
        half = pk / 2
        j = i
        while j > 0 and Pb[j] > half:
            j -= 1
        kk = i
        while kk < len(Pb) - 1 and Pb[kk] > half:
            kk += 1
        bw = float(fb[kk] - fb[j])
        floor_ = float(np.median(P[(f >= 15) & (f <= 19)]))
        print(f"    {r:6s} {lab:6s} {K:4d} {fpk:8.2f} {pk:11.4g} {bw:11.2f} "
              f"{fpk/max(bw,1e-9):8.1f} {floor_:15.4g} {pk/floor_:11.1f}")
        rec[lab] = dict(K=K, f=fpk, psd=pk, bw=bw, Q=fpk / max(bw, 1e-9), floor=floor_,
                        peak_over_floor=pk / floor_)
    if "V101" in rec and "V100" in rec:
        a, b = rec["V101"], rec["V100"]
        print(f"    ⇒ V101/V100:  peak PSD x{a['psd']/b['psd']:.1f}   "
              f"width x{a['bw']/b['bw']:.2f}   Q x{a['Q']/b['Q']:.2f}   "
              f"peak/floor x{a['peak_over_floor']/b['peak_over_floor']:.1f}   "
              f"freq {b['f']:.2f} -> {a['f']:.2f} Hz ({a['f']-b['f']:+.2f})")
        print(f"       MORE EXCITATION predicts width x1.0 and Q x1.0;  A MOVING POLE predicts "
              f"width < 1 and Q > 1.")
    out[ch] = rec

# ======================================================================================
print("\n" + "=" * 100)
print("GRIP / RELEASE PROFILES AT FULL TIME RESOLUTION (route 95 only)")
print("=" * 100)
FS = L.fs()
lat = L.engaged()
tq = L.col("tq")
ts = np.abs(L.lowpass(tq, FS, 3.0, mask=lat))
LOW, HIGH = 200.0, 500.0
HOLD, MAXT = int(1.0 * FS), int(2.0 * FS)


def find_events(direction):
    ev = []
    lo_m, hi_m = ts < LOW, ts > HIGH
    a_m, b_m = (lo_m, hi_m) if direction == "grip" else (hi_m, lo_m)
    n = len(ts)
    i = HOLD + MAXT
    while i < n - HOLD - int(3 * FS):
        if not b_m[i] or b_m[i - 1] or not b_m[i:i + HOLD].all():
            i += 1
            continue
        j = i - 1
        while j > i - MAXT and not a_m[j]:
            j -= 1
        if j <= i - MAXT or not a_m[j - HOLD:j].all() or not lat[j - HOLD:i + int(3 * FS)].all():
            i += 1
            continue
        ev.append((j, i))          # j = last frame in the OLD state, i = first in the NEW
        i += HOLD
    return ev


for tag, dirn in (("GRIP", "grip"), ("RELEASE", "release")):
    EV = find_events(dirn)
    print(f"\n  {tag}: {len(EV)} events.  t=0 is the LAST frame of the old torque state (j);")
    print(f"     the torque transition itself takes t=0 -> t_cross, listed per event.")
    for bn, (lo, hi) in (("B8", (7.3, 9.3)), ("B23", (21.5, 25.5)), ("CTRL", (2.5, 4.5))):
        env = L.band_envelope(tq, FS, lo, hi, mask=lat)
        sm = np.convolve(np.nan_to_num(env), np.ones(int(0.12 * FS)) / int(0.12 * FS),
                         mode="same")
        PRE, POST = int(1.5 * FS), int(2.5 * FS)
        M = np.array([sm[j - PRE:j + POST] for j, i in EV if j >= PRE and j + POST <= len(sm)])
        cross = np.array([(i - j) / FS for j, i in EV])
        if len(M) < 3:
            continue
        prof = np.median(M, axis=0)
        tt = (np.arange(len(prof)) - PRE) / FS
        pre = float(np.median(prof[:PRE - int(0.2 * FS)]))
        post = float(np.median(prof[PRE + int(1.5 * FS):]))
        tgt = pre + 0.632 * (post - pre)
        after = prof[PRE:]
        hit = (after <= tgt) if post < pre else (after >= tgt)
        tau = float(np.argmax(hit) / FS) if hit.any() else float("nan")
        samp = "  ".join(f"{tt[PRE+int(s*FS)]:+.1f}s:{prof[PRE+int(s*FS)]:7.0f}"
                         for s in (-1.0, -0.5, 0.0, 0.25, 0.5, 1.0, 1.5, 2.0)
                         if 0 <= PRE + int(s * FS) < len(prof))
        print(f"    {bn:5s} pre {pre:7.1f} -> post {post:7.1f} ({post/max(pre,1e-9):5.2f}x)  "
              f"tau63 {tau:4.2f} s   torque-transition {np.median(cross):.2f} s")
        print(f"          profile: {samp}")
        out.setdefault("events", []).append(
            dict(event=tag, band=bn, n=int(len(M)), pre=pre, post=post,
                 ratio=float(post / max(pre, 1e-9)), tau63=tau,
                 torque_transition_s=float(np.median(cross))))

(L.CACHE / "r95_qshift.json").write_text(json.dumps(out, indent=1, default=float))
print(f"\nwrote {L.CACHE / 'r95_qshift.json'}")
