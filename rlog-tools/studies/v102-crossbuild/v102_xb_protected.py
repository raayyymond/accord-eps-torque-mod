#!/usr/bin/env python3
r"""THE PROTECTED METRIC and THE RAIL.  "Did doubling the gain actually buy more wheel rate?"

P1  Peak DELIVERED firmware torque under a hard command -- did the ceiling move x2 or not at all?
P2  PROTECTED: engaged steering-WHEEL ANGLE RATE under the top decile of |LKAS command|,
    hands-light, matched speed.  (An angle-rate limit is what the operator forbids.)
P3  NOT protected, reference only: command slew d|e4tq|/dt.
P4  RAMP COST: at command-onset edges and at latActive rising edges, 10 %->90 % rise time of the
    wheel rate and the terminal rate.  This prices any ramp-slowing lever (e.g. `0xCBE74`, which is
    DC-blocked and therefore cannot cap terminal rate -- only the ramp).
P5  V100's engaged-vs-manual band contrast AT ROAD SPEED (route 95 has no LKAS-off above 7 km/h).
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

KMH = L.KMH
RAIL = 4096.0            # openpilot's own 0x0E4 STEER_TORQUE_REQUEST rail, identical on both builds
LIGHT = 400.0            # |driver torque| counts -- "hands-light"
VB = [(5, 15), (15, 30), (30, 45), (45, 65)]


def hdr(s):
    print("\n" + "=" * 106)
    print(s)
    print("=" * 106)


D = {}
for route in ("85", "95", "71"):
    B = L.all_blocks(route)
    d = {}
    for k in ("t", "cc_lat", "v_rear", "rate_c", "cs_tq", "e4tq", "cs_ang", "seg"):
        if k == "seg":
            d[k] = np.concatenate([np.full(len(b["t"]), b["_seg"], float) for b in B])
        else:
            d[k] = np.concatenate([b[k] for b in B])
    d["blk"] = np.concatenate([np.full(len(b["t"]), i, float) for i, b in enumerate(B)])
    if "x6b94" in B[0]:
        d["x6b94"] = np.concatenate([b["x6b94"] for b in B])
    d["eng"] = d["cc_lat"] > 0.5
    d["v"] = d["v_rear"] * KMH
    d["ar"] = np.abs(d["rate_c"])
    D[route] = d
    print("   r%s %s: %d rows on the uniform grid, %d gap-free blocks, engaged %.1f s"
          % (route, L.ROUTES[route]["build"], len(d["t"]), len(B), d["eng"].sum() / L.FS))


def boot_ratio(a_vals, a_unit, b_vals, b_unit, q, nboot=3000, seed=3):
    """Ratio of the q-th percentile, resampling 15 s blocks (unit ids) with replacement."""
    rng = np.random.default_rng(seed)
    if len(a_vals) < 30 or len(b_vals) < 30:
        return None
    ua, ub = np.unique(a_unit), np.unique(b_unit)
    ia = {u: np.nonzero(a_unit == u)[0] for u in ua}
    ib = {u: np.nonzero(b_unit == u)[0] for u in ub}
    pt = np.percentile(b_vals, q) / np.percentile(a_vals, q)
    out = []
    for _ in range(nboot):
        sa = np.concatenate([ia[ua[j]] for j in rng.integers(0, len(ua), len(ua))])
        sb = np.concatenate([ib[ub[j]] for j in rng.integers(0, len(ub), len(ub))])
        out.append(np.percentile(b_vals[sb], q) / max(np.percentile(a_vals[sa], q), 1e-9))
    out = np.array([o for o in out if np.isfinite(o)])
    lo, hi = np.percentile(out, [2.5, 97.5])
    return dict(r=float(pt), lo=float(lo), hi=float(hi), nA=len(a_vals), nB=len(b_vals))


def unit(d, m):
    return d["blk"][m] * 1e6 + np.floor(d["t"][m] / 15.0)


# =====================================================================================================
hdr("P0 -- THE RAIL ON THE WIRE.  Where does each channel pile up, and did the ceiling move?")
print("   |e4tq| is openpilot's OWN 0x0E4 command.  Its rail is +/-4096 on BOTH builds.")
for route in ("85", "95"):
    d = D[route]
    m = d["eng"]
    e = np.abs(d["e4tq"][m])
    print("   r%s %s  engaged n=%d   |e4tq| p50=%5.0f p90=%6.0f p99=%6.0f max=%6.0f   "
          "duty at rail 4096 = %.4f"
          % (route, L.ROUTES[route]["build"], m.sum(), *np.percentile(e, [50, 90, 99, 100]),
             float((e >= RAIL).mean())))
print("\n   The DELIVERED firmware torque `x6b94` (= gp-0x6b94, the aggregator output, counts).")
print("   🛑 This is the channel the operator's 'it didn't feel like double' is about.")
for cond, lab in ((None, "all engaged"),
                  ("rail", "engaged AND |e4tq| at the 4096 rail"),
                  ("raillight", "engaged AND at the rail AND hands-light (|tq|<400)")):
    print("   -- %s" % lab)
    for route in ("85", "95"):
        d = D[route]
        m = d["eng"]
        if cond in ("rail", "raillight"):
            m = m & (np.abs(d["e4tq"]) >= RAIL)
        if cond == "raillight":
            m = m & (np.abs(d["cs_tq"]) < LIGHT)
        x = np.abs(d["x6b94"][m])
        if m.sum() < 30:
            print("      r%s  n=%d  (too thin)" % (route, m.sum()))
            continue
        print("      r%s %s  n=%6d   |x6b94| p50=%6.0f p90=%7.0f p99=%7.0f max=%7.0f ct"
              % (route, L.ROUTES[route]["build"], m.sum(), *np.percentile(x, [50, 90, 99, 100])))
    a, b = D["85"], D["95"]
    ma, mb = a["eng"], b["eng"]
    if cond in ("rail", "raillight"):
        ma = ma & (np.abs(a["e4tq"]) >= RAIL)
        mb = mb & (np.abs(b["e4tq"]) >= RAIL)
    if cond == "raillight":
        ma = ma & (np.abs(a["cs_tq"]) < LIGHT)
        mb = mb & (np.abs(b["cs_tq"]) < LIGHT)
    for q in (50, 90, 99):
        r = boot_ratio(np.abs(a["x6b94"][ma]), unit(a, ma), np.abs(b["x6b94"][mb]), unit(b, mb), q)
        if r:
            print("         V101/V100 p%-2d = %5.2f x  [%4.2f, %4.2f]" % (q, r["r"], r["lo"], r["hi"]))

# =====================================================================================================
hdr("P2 -- 🛑 THE PROTECTED METRIC: steering-WHEEL ANGLE RATE under a hard LKAS command")
print("   hands-light = |driver torque| < %d counts.  hard command = |e4tq| at the 4096 rail" % LIGHT)
print("   (the rail's duty is 12.3 %% on r85 and 12.0 %% on r95, so the conditioning is matched).")
for vlo, vhi in VB:
    print("\n   speed %d-%d km/h" % (vlo, vhi))
    sel = {}
    for route in ("85", "95"):
        d = D[route]
        m = (d["eng"] & (d["v"] >= vlo) & (d["v"] < vhi) & (np.abs(d["e4tq"]) >= RAIL)
             & (np.abs(d["cs_tq"]) < LIGHT))
        sel[route] = m
        if m.sum() < 30:
            print("      r%s %s  n=%4d  TOO THIN -- not quoted" % (route, L.ROUTES[route]["build"], m.sum()))
            continue
        ar = d["ar"][m]
        print("      r%s %s  n=%5d (%5.1f s)  |wheel rate| p50=%5.1f p90=%6.1f p99=%6.1f max=%6.1f deg/s"
              % (route, L.ROUTES[route]["build"], m.sum(), m.sum() / L.FS,
                 *np.percentile(ar, [50, 90, 99, 100])))
    if sel["85"].sum() >= 30 and sel["95"].sum() >= 30:
        for q in (50, 90, 99):
            r = boot_ratio(D["85"]["ar"][sel["85"]], unit(D["85"], sel["85"]),
                           D["95"]["ar"][sel["95"]], unit(D["95"], sel["95"]), q, seed=q)
            if r:
                print("         V101/V100 wheel-rate p%-2d = %5.2f x  [%4.2f, %4.2f]"
                      % (q, r["r"], r["lo"], r["hi"]))

print("\n   POOLED over 5-65 km/h (speed-stratified is above; this is the headline number):")
sel = {}
for route in ("85", "95"):
    d = D[route]
    sel[route] = (d["eng"] & (d["v"] >= 5) & (d["v"] < 65) & (np.abs(d["e4tq"]) >= RAIL)
                  & (np.abs(d["cs_tq"]) < LIGHT))
    ar = d["ar"][sel[route]]
    print("      r%s %s  n=%5d (%5.1f s)  p50=%5.1f p90=%6.1f p99=%6.1f max=%6.1f deg/s"
          % (route, L.ROUTES[route]["build"], sel[route].sum(), sel[route].sum() / L.FS,
             *np.percentile(ar, [50, 90, 99, 100])))
for q in (50, 90, 99):
    r = boot_ratio(D["85"]["ar"][sel["85"]], unit(D["85"], sel["85"]),
                   D["95"]["ar"][sel["95"]], unit(D["95"], sel["95"]), q, seed=100 + q)
    if r:
        print("      V101/V100 p%-2d = %5.2f x  [%4.2f, %4.2f]" % (q, r["r"], r["lo"], r["hi"]))

print("\n   UNCONDITIONED (all engaged 5-65 km/h) -- the exposure descriptor, NOT the metric:")
for route in ("85", "95"):
    d = D[route]
    m = d["eng"] & (d["v"] >= 5) & (d["v"] < 65)
    print("      r%s  n=%6d  |wheel rate| p50=%5.1f p90=%6.1f p99=%6.1f max=%6.1f deg/s"
          % (route, m.sum(), *np.percentile(d["ar"][m], [50, 90, 99, 100])))

# =====================================================================================================
hdr("P3 -- NOT PROTECTED (reference): command slew  d|e4tq|/dt, engaged 5-65 km/h")
for route in ("85", "95"):
    d = D[route]
    m = d["eng"] & (d["v"] >= 5) & (d["v"] < 65)
    sl = np.abs(np.diff(d["e4tq"])) * L.FS
    ok = m[:-1] & m[1:] & (np.diff(d["blk"]) == 0)
    print("   r%s %s  n=%6d  |d(e4tq)/dt| p50=%6.0f p90=%7.0f p99=%7.0f max=%7.0f counts/s"
          % (route, L.ROUTES[route]["build"], ok.sum(), *np.percentile(sl[ok], [50, 90, 99, 100])))

# =====================================================================================================
hdr("P4 -- RAMP COST.  Onset edges: 10 %->90 % rise of |wheel rate|, and the terminal rate.")


def edges(d, kind):
    e = np.abs(d["e4tq"])
    if kind == "cmd":
        rise = np.nonzero((e[:-1] < 1000) & (e[1:] >= RAIL) & (np.diff(d["blk"]) == 0)
                          & d["eng"][1:])[0] + 1
    else:
        rise = np.nonzero((~d["eng"][:-1]) & d["eng"][1:] & (np.diff(d["blk"]) == 0))[0] + 1
    return rise


for kind, lab in (("cmd", "COMMAND-ONSET edges  (|e4tq| < 1000 -> at the 4096 rail, engaged)"),
                  ("lat", "latActive RISING edges")):
    print("\n   %s" % lab)
    for route in ("85", "95"):
        d = D[route]
        rt, tr = [], []
        for i in edges(d, kind):
            j = min(i + 100, len(d["t"]))                       # 1.0 s window
            if j - i < 60 or d["blk"][j - 1] != d["blk"][i]:
                continue
            seg = d["ar"][i:j]
            term = float(np.percentile(seg[-40:], 90))          # terminal rate = p90 of 0.6-1.0 s
            if term < 5.0:
                continue                                        # nothing happened; not a ramp
            lo_, hi_ = 0.1 * term, 0.9 * term
            k1 = np.nonzero(seg >= lo_)[0]
            k2 = np.nonzero(seg >= hi_)[0]
            if len(k1) and len(k2) and k2[0] > k1[0]:
                rt.append((k2[0] - k1[0]) / L.FS * 1000.0)
                tr.append(term)
        if len(rt) < 5:
            print("      r%s %s  only %d usable edges -- NOT QUOTED" % (route, L.ROUTES[route]["build"], len(rt)))
            continue
        print("      r%s %s  n=%3d edges   10-90 %% rise: p50=%5.0f p90=%5.0f ms    "
              "terminal |wheel rate|: p50=%5.1f p90=%6.1f deg/s"
              % (route, L.ROUTES[route]["build"], len(rt), np.percentile(rt, 50),
                 np.percentile(rt, 90), np.percentile(tr, 50), np.percentile(tr, 90)))

# =====================================================================================================
hdr("P5 -- V100's ENGAGED-vs-MANUAL BAND CONTRAST AT ROAD SPEED (route 95 cannot supply this)")
W85e = L.windows("85", 256, 128, engaged=True)
W85m = L.windows("85", 256, 128, engaged=False)
for vlo, vhi in ((0, 10), (10, 200)):
    a = L.sel(W85e, vlo=vlo, vhi=vhi)
    b = L.sel(W85m, vlo=vlo, vhi=vhi)
    print("\n   %d-%d km/h   engaged win=%d   manual win=%d" % (vlo, vhi, len(a), len(b)))
    if len(b) < 5:
        print("      no manual exposure here on r85 either -- r85's manual is 0-13 km/h only")
        continue
    for ch in ("tq", "rate_c", "cs_ang"):
        row = []
        for bn in ("6-9", "18-22", "22-26", "26-31", "32-38", "40-49"):
            k = ch + "|" + bn
            va = [r[k] for r in a if k in r]
            vb = [r[k] for r in b if k in r]
            row.append("%s %5.2f" % (bn, np.median(va) / np.median(vb)))
        print("      %-8s engaged/manual band RMS:  %s" % (ch, "  ".join(row)))

print("\n[done]")
