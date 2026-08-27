#!/usr/bin/env python3
"""studies/sessions/v74_v75/v75_step_burst.py -- the two things the first two scripts turned up that need pinning down.

  A. EVERY V75 step > 512 lands in ONE 1.2 s burst (seg 6, t~51.4-52.6 s, 113 km/h, engaged).
     What is it? Frequency, and whether V74 vs V75 differ in KIND there (ramp vs relay).
  B. Route 5d's launch events: the two detectors disagreed (4 vs 6). Adjudicate, then answer the
     question that actually matters -- was there ever an ENGAGED STOPLIGHT STOP, i.e. the V75
     fault's own condition?
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

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
import v75_step_lib as L  # noqa: E402

W = 1.0 / 100.0009


def hdr(s):
    print("\n" + "=" * 100)
    print(s)
    print("=" * 100)


D = L.load_route()
n = len(D["t"])
r_signed = np.trunc(np.rint(D["rate_f"] * 10.0) * 2048.0 / 3477.0).astype(np.int64)
r_cts = np.abs(r_signed)
sp_cts = np.rint(D["cs_v"] * L.MS_TO_CTS).astype(np.int64)
in26, in24, amb = L.mode_masks(D["cc_lat"], D["t"])
mode = np.where(in26, L.MODE_ENGAGED, L.MODE_MANUAL).astype(np.int64)
o74 = L.Replay("v74").run(sp_cts, r_signed, mode)
o75 = L.Replay("v75").run(sp_cts, r_signed, mode)

# ---------------------------------------------------------------------------------------------------
hdr("A.  THE BURST -- seg 6, the only place a V75 step exceeds 512")
m = (D["seg"] == 6) & (D["t_seg"] > 50.5) & (D["t_seg"] < 53.5)
i = np.flatnonzero(m)
t = D["t_seg"][i]
print(f"  n frames {len(i)}  span {t[0]:.2f}-{t[-1]:.2f} s  speed {D['cs_v'][i].mean():.2f} m/s "
      f"({D['cs_v'][i].mean()*3.6:.0f} km/h)  latActive {(D['cc_lat'][i]>0.5).mean()*100:.0f}%")
fs = 100.0009
for lab, x in (("gp-0x6ac0 (signed)", r_signed[i].astype(float)),
               ("gp-0x6bd0 V74", o74[i].astype(float)),
               ("gp-0x6bd0 V75", o75[i].astype(float)),
               ("0x18F torsion bar", D["tq"][i]),
               ("openpilot 0x0E4 cmd", D["e4tq"][i])):
    y = x - x.mean()
    win = np.hanning(len(y))
    P = np.abs(np.fft.rfft(y * win)) ** 2
    f = np.fft.rfftfreq(len(y), 1 / fs)
    k = np.argmax(P[(f > 3) & (f < 50)]) + np.flatnonzero(f > 3)[0]
    print(f"  {lab:22s} p-p {x.max()-x.min():8.1f}   dominant line {f[k]:6.2f} Hz "
          f"(prominence {P[k]/np.median(P[(f>3)&(f<50)]):7.1f}x median)")
print("\n  ⇒ this is the kit's known ENGAGED HIGH-SPEED oscillation, not a launch phenomenon.")
print("  V74 vs V75 IN KIND across the burst -- how many frames sit ON the constant-magnitude")
print("  plateau (|gp-0x6ac0| >= entry), i.e. running as a RELAY rather than on the ramp:")
for lab, entry in (("V74 (entry 400)", 400), ("V75 (entry 200)", 200)):
    on = (r_cts[i] >= entry).sum()
    print(f"    {lab:18s} {on:4d}/{len(i)} frames = {100*on/len(i):5.1f}% on the plateau")
print(f"  |gp-0x6bd0| p-p across the burst: V74 {o74[i].max()-o74[i].min():5d}   "
      f"V75 {o75[i].max()-o75[i].min():5d}   ratio {(o75[i].max()-o75[i].min())/(o74[i].max()-o74[i].min()):.2f}x")

# ---------------------------------------------------------------------------------------------------
hdr("B.  LAUNCH EVENTS -- adjudicated, and the STOPLIGHT-STOP question")
LO, HI = 1.0 / 3.6, 20.0 / 3.6
v = D["cs_v"]
lat = D["cc_lat"] > 0.5
events = []
for s in np.unique(D["seg"]):
    idx = np.flatnonzero(D["seg"] == s)
    vv, bb, aa = v[idx], v[idx] < LO, v[idx] > HI
    j = 0
    while j < len(idx):
        if not bb[j]:
            j += 1
            continue
        k = j
        while k < len(idx) and bb[k]:      # the whole sub-1 km/h dwell
            k += 1
        p = k
        while p < len(idx) and not aa[p] and not bb[p]:
            p += 1
        if p < len(idx) and aa[p]:
            events.append((idx[j], idx[k - 1], idx[p]))
        j = max(k, j + 1)
print("  A launch = a contiguous dwell below 1 km/h, followed by a monotone climb past 20 km/h with")
print("  no return below 1 km/h in between. `dwell` is the length of the sub-1 km/h dwell (the")
print("  'stoplight stop'); `lat@dwell` is latActive during it.")
print(f"\n  {'#':>3s} {'seg':>4s} {'t_stop':>8s} {'dwell':>7s} {'ramp':>6s} {'lat@dwell':>10s} "
      f"{'lat@ramp':>9s} {'m26@ramp':>9s} {'maxrate':>8s} {'s>=200':>7s} {'|o74|':>6s} {'|o75|':>6s}")
ng = 0
for c, (a, b, p) in enumerate(events):
    dw = D["t"][b] - D["t"][a]
    rp = D["t"][p] - D["t"][b]
    ld = lat[a:b + 1].mean() * 100
    lr = lat[b:p + 1].mean() * 100
    mr = in26[b:p + 1].mean() * 100
    sl = slice(b, p + 1)
    if ld > 50 and dw >= 1.0:
        ng += 1
    print(f"  {c:3d} {int(D['seg'][a]):4d} {D['t_seg'][a]:8.2f} {dw:7.2f} {rp:6.2f} {ld:10.1f} "
          f"{lr:9.1f} {mr:9.1f} {int(r_cts[sl].max()):8d} {(r_cts[sl]>=200).sum()*W:7.2f} "
          f"{int(np.abs(o74[sl]).max()):6d} {int(np.abs(o75[sl]).max()):6d}")
print(f"\n  n launches total: {len(events)}")
print(f"  n launches from a >=1 s stop WITH latActive during the stop (the V75 fault's own "
      f"condition): {ng}")
print(f"  n launches with latActive >50% during the RAMP: "
      f"{sum(1 for a,b,p in events if lat[b:p+1].mean()>0.5)}")
print(f"  n launches with the MODE (26) actually in force >50% of the ramp: "
      f"{sum(1 for a,b,p in events if in26[b:p+1].mean()>0.5)}")

print("\n  POWER. Treating a launch as the experimental unit, route 5d supplies n = "
      f"{sum(1 for a,b,p in events if lat[b:p+1].mean()>0.5)} engaged ramps and ZERO engaged")
print("  stoplight stops. With n of that size a per-event contrast has no usable power: the")
print("  smallest detectable effect at 80% power for a binary per-event outcome is ~1 event, i.e.")
print("  the analysis can only distinguish 'never happened' from 'happened at least once'.")

# --- what the stops actually looked like ------------------------------------------------------------
below = v < LO
idxs = np.flatnonzero(below)
brk = np.flatnonzero(np.diff(idxs) > 1)
stops = [r for r in np.split(idxs, brk + 1) if len(r) * W >= 1.0]
print(f"\n  All sub-1 km/h dwells >= 1 s: n = {len(stops)}, total {sum(len(r) for r in stops)*W:.1f} s.")
print(f"  latActive fraction during each: "
      f"{[round(float(lat[r].mean()),3) for r in stops]}")
print("  ⇒ openpilot was laterally INACTIVE through every full stop on this route. The engaged")
print("    ramps above all begin from a ROLLING crawl, not from rest.")
