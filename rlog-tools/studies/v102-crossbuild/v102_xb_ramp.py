#!/usr/bin/env python3
r"""THE PROTECTED METRIC, done on EVENTS instead of frames: what the wheel does on a COMMAND RAMP.

Frame-level conditioning on "|e4tq| at the rail AND hands-light" leaves only 1.2 s of V101 exposure.
An EVENT-level test is far better powered and is also the physically right question: for the SAME
command ramp, how fast does the wheel actually turn?

EDGE = an upward crossing of |e4tq| through HI whose last crossing below LO was within MAXRAMP.
openpilot NEVER steps its command -- a "<1000 then >=4096 next sample" test finds ZERO edges on both
routes -- so the edge must be defined by crossings, not by a one-sample jump.

Bootstrap unit = the EDGE (each is a separate manoeuvre).
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

FS = L.FS
LO, HI, MAXRAMP = 500.0, 3000.0, 100
LIGHT = 400.0


def hdr(s):
    print("\n" + "=" * 100)
    print(s)
    print("=" * 100)


RAW = {}
for route in ("85", "95", "71"):
    acc = {}
    for s in L.ROUTES[route]["segs"]:
        d = L.load_seg(route, s)
        n = len(d["t"])
        for k in ("t", "cc_lat", "v_rear", "rate_c", "cs_tq", "e4tq"):
            acc.setdefault(k, []).append(d[k])
        acc.setdefault("seg", []).append(np.full(n, s, float))
    d = {k: np.concatenate(v) for k, v in acc.items()}
    d["eng"] = d["cc_lat"] > 0.5
    d["ar"] = np.abs(d["rate_c"])
    d["v"] = d["v_rear"] * 3.6
    RAW[route] = d


def events(route):
    d = RAW[route]
    e = np.abs(d["e4tq"])
    out, last_lo = [], None
    for i in range(1, len(e)):
        if d["seg"][i] != d["seg"][i - 1]:
            last_lo = None
            continue
        if e[i] < LO:
            last_lo = i
        if e[i] >= HI and e[i - 1] < HI and d["eng"][i] and last_lo is not None \
                and 0 < i - last_lo <= MAXRAMP:
            j = min(i + 50, len(e))
            if d["seg"][j - 1] == d["seg"][i] and j - i >= 40:
                seg = d["ar"][i:j]
                out.append(dict(route=route, i0=i,
                                ramp_ms=(i - last_lo) / FS * 1000.0,
                                v=float(np.median(d["v"][last_lo:j])),
                                tq=float(np.median(np.abs(d["cs_tq"][last_lo:j]))),
                                wr90=float(np.percentile(seg, 90)),
                                wrpk=float(seg.max()),
                                t2p=float(np.argmax(seg) / FS * 1000.0)))
            last_lo = None
    return out


def boot(A, B, key, nboot=5000, seed=7, q=50):
    rng = np.random.default_rng(seed)
    a = np.array([x[key] for x in A])
    b = np.array([x[key] for x in B])
    if len(a) < 5 or len(b) < 5:
        return None
    pt = np.percentile(b, q) / max(np.percentile(a, q), 1e-9)
    out = [np.percentile(b[rng.integers(0, len(b), len(b))], q)
           / max(np.percentile(a[rng.integers(0, len(a), len(a))], q), 1e-9) for _ in range(nboot)]
    lo, hi = np.percentile(out, [2.5, 97.5])
    return dict(r=float(pt), lo=float(lo), hi=float(hi), nA=len(a), nB=len(b))


EV = {r: events(r) for r in ("85", "95", "71")}
hdr("COMMAND-RAMP EVENTS  (|e4tq| %d -> %d within %.1f s, engaged)" % (LO, HI, MAXRAMP / FS))
for r in ("85", "95", "71"):
    E = EV[r]
    print("   r%s %-5s  %3d events   v p50=%5.1f km/h   |driver tq| p50=%6.0f   command ramp p50=%4.0f ms"
          % (r, L.ROUTES[r]["build"], len(E),
             np.median([x["v"] for x in E]) if E else np.nan,
             np.median([x["tq"] for x in E]) if E else np.nan,
             np.median([x["ramp_ms"] for x in E]) if E else np.nan))
print("""
   The COMMAND ramp time is the control: if it is the same on both builds, any difference in what
   the wheel does is the CAR's response to the same demand, not a different demand.""")

for lbl, filt in (("ALL EVENTS", lambda x: True),
                  ("HANDS-LIGHT (|driver tq| < 400)", lambda x: x["tq"] < LIGHT),
                  ("5-30 km/h", lambda x: 5 <= x["v"] < 30),
                  ("5-30 km/h AND HANDS-LIGHT", lambda x: 5 <= x["v"] < 30 and x["tq"] < LIGHT)):
    A = [x for x in EV["85"] if filt(x)]
    B = [x for x in EV["95"] if filt(x)]
    print("\n   -- %s   (V100 n=%d, V101 n=%d)" % (lbl, len(A), len(B)))
    if len(A) < 5 or len(B) < 5:
        print("      TOO FEW EVENTS -- not quoted")
        continue
    for key, nm, unit in (("ramp_ms", "command ramp   (CONTROL, must match)", "ms"),
                          ("wr90", "🛑 PROTECTED wheel rate p90 in 0.5 s", "deg/s"),
                          ("wrpk", "🛑 PROTECTED peak |wheel rate|", "deg/s"),
                          ("t2p", "time to peak wheel rate (ramp cost baseline)", "ms")):
        a = np.array([x[key] for x in A])
        b = np.array([x[key] for x in B])
        rr = boot(A, B, key)
        print("      %-42s V100 p50=%6.1f  V101 p50=%6.1f %-6s  ratio %5.2f x [%4.2f, %5.2f]"
              % (nm, np.median(a), np.median(b), unit, rr["r"], rr["lo"], rr["hi"]))

hdr("V87 (route 71, 4x, Lever B REMOVED) on the same test -- creep only, so read it as such")
A = [x for x in EV["71"] if 5 <= x["v"] < 30]
B = [x for x in EV["95"] if 5 <= x["v"] < 30]
C = [x for x in EV["85"] if 5 <= x["v"] < 30]
print("   5-30 km/h events: V87 n=%d  V100 n=%d  V101 n=%d" % (len(A), len(C), len(B)))
for pair, lbl in (((A, B), "V101 / V87   (isolates the 8x gain)"),
                  ((C, A), "V87  / V100  (isolates Lever B)")):
    if len(pair[0]) < 5 or len(pair[1]) < 5:
        print("   %-34s TOO FEW EVENTS -- not quoted" % lbl)
        continue
    for key, nm in (("ramp_ms", "command ramp (control)"), ("wr90", "wheel rate p90"),
                    ("wrpk", "peak wheel rate")):
        rr = boot(pair[0], pair[1], key)
        print("   %-34s %-24s %5.2f x [%4.2f, %5.2f]  n=%d/%d"
              % (lbl, nm, rr["r"], rr["lo"], rr["hi"], rr["nA"], rr["nB"]))

print("\n[done]")
