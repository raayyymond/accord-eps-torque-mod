#!/usr/bin/env python3
r"""THE PROTECTED METRIC and THE RAIL -- corrected pass.

Two defects in `v102_xb_protected.py`, both fixed here and both stated because they changed numbers:
  1. It read percentile/max statistics off the UNIFORM-GRID RESAMPLE.  `np.interp` cannot exceed its
     neighbours, so grid points that miss an extreme sample ATTENUATE the tails: r85's |x6b94| max
     came out 1548 ct against the cache's own 1932.8.  All distribution statistics here are taken
     from the RAW per-segment arrays, untouched.
  2. Its command-onset edge test required |e4tq| to jump from <1000 to the rail in ONE 10 ms sample.
     openpilot ramps, so it found zero edges.  An onset is now "first frame at the rail after >=0.2 s
     below 1000".
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KMH = L.KMH
RAIL = 4096.0
LIGHT = 400.0
VB = [(5, 15), (15, 30), (30, 45), (45, 65)]


def hdr(s):
    print("\n" + "=" * 106)
    print(s)
    print("=" * 106)


RAW = {}
for route in ("85", "95"):
    R = L.ROUTES[route]
    acc = {}
    for s in R["segs"]:
        d = L.load_seg(route, s)
        n = len(d["t"])
        for k in ("t", "cc_lat", "v_rear", "rate_c", "cs_tq", "e4tq", "x6b94", "cs_ang"):
            acc.setdefault(k, []).append(d[k] if k in d else np.full(n, np.nan))
        acc.setdefault("seg", []).append(np.full(n, s, float))
    d = {k: np.concatenate(v) for k, v in acc.items()}
    d["eng"] = d["cc_lat"] > 0.5
    d["v"] = d["v_rear"] * KMH
    d["ar"] = np.abs(d["rate_c"])
    d["unit"] = d["seg"] * 1e6 + np.floor(d["t"] / 15.0)
    RAW[route] = d
    print("   r%s %s  raw rows=%d  engaged=%d  |x6b94| max=%.1f ct (cache lane427 says %s)"
          % (route, R["build"], len(d["t"]), d["eng"].sum(), np.nanmax(np.abs(d["x6b94"])),
             {"85": "1932.8", "95": "3148.8"}[route]))


def bootq(a, ua, b, ub, q, nboot=3000, seed=3):
    rng = np.random.default_rng(seed)
    if len(a) < 25 or len(b) < 25:
        return None
    Ua, Ub = np.unique(ua), np.unique(ub)
    ia = {u: np.nonzero(ua == u)[0] for u in Ua}
    ib = {u: np.nonzero(ub == u)[0] for u in Ub}
    pt = np.percentile(b, q) / max(np.percentile(a, q), 1e-9)
    out = []
    for _ in range(nboot):
        sa = np.concatenate([ia[Ua[j]] for j in rng.integers(0, len(Ua), len(Ua))])
        sb = np.concatenate([ib[Ub[j]] for j in rng.integers(0, len(Ub), len(Ub))])
        out.append(np.percentile(b[sb], q) / max(np.percentile(a[sa], q), 1e-9))
    out = np.array([o for o in out if np.isfinite(o)])
    lo, hi = np.percentile(out, [2.5, 97.5])
    return dict(r=float(pt), lo=float(lo), hi=float(hi), nA=len(a), nB=len(b),
                uA=len(Ua), uB=len(Ub))


def show(tag, mask_fn, chan="x6b94", unit_lbl="ct", vbins=None, qs=(50, 90, 99)):
    print("\n   %s" % tag)
    for vlo, vhi in (vbins or [(5, 65)]):
        sel = {}
        for route in ("85", "95"):
            d = RAW[route]
            m = mask_fn(d) & (d["v"] >= vlo) & (d["v"] < vhi)
            sel[route] = m
            x = np.abs(d[chan][m])
            x = x[np.isfinite(x)]
            if len(x) < 25:
                print("      %2d-%2d km/h  r%s  n=%4d  TOO THIN -- not quoted" % (vlo, vhi, route, len(x)))
                continue
            print("      %2d-%2d km/h  r%s %-5s n=%6d (%6.1f s)  p50=%7.1f p90=%8.1f p99=%8.1f "
                  "max=%8.1f %s"
                  % (vlo, vhi, route, L.ROUTES[route]["build"], len(x), len(x) / L.FS,
                     *np.percentile(x, [50, 90, 99, 100]), unit_lbl))
        a, b = RAW["85"], RAW["95"]
        xa = np.abs(a[chan][sel["85"]]); xa = xa[np.isfinite(xa)]
        xb = np.abs(b[chan][sel["95"]]); xb = xb[np.isfinite(xb)]
        ua = a["unit"][sel["85"]][np.isfinite(np.abs(a[chan][sel["85"]]))]
        ub = b["unit"][sel["95"]][np.isfinite(np.abs(b[chan][sel["95"]]))]
        line = []
        for q in qs:
            r = bootq(xa, ua, xb, ub, q, seed=q + vlo)
            line.append("p%-2d %5.2fx[%4.2f,%5.2f]" % (q, r["r"], r["lo"], r["hi"]) if r else "p%-2d n/a" % q)
        if any("n/a" not in s for s in line):
            print("         V101/V100  " + "   ".join(line)
                  + ("   blocks %d/%d" % (r["uA"], r["uB"]) if r else ""))


ENG = lambda d: d["eng"]                                                        # noqa: E731
RAILM = lambda d: d["eng"] & (np.abs(d["e4tq"]) >= RAIL)                         # noqa: E731
RAILL = lambda d: (d["eng"] & (np.abs(d["e4tq"]) >= RAIL)                        # noqa: E731
                   & (np.abs(d["cs_tq"]) < LIGHT))

# =====================================================================================================
hdr("P0 -- THE RAIL.  Did the DELIVERED torque ceiling move x2, or not at all?  (RAW arrays)")
print("   |e4tq| = openpilot's own 0x0E4 command.  Rail +/-4096 on BOTH builds:")
for route in ("85", "95"):
    d = RAW[route]
    e = np.abs(d["e4tq"][d["eng"]])
    print("      r%s %s  engaged n=%d  p50=%5.0f p90=%6.0f p99=%6.0f max=%6.0f   duty at rail=%.4f"
          % (route, L.ROUTES[route]["build"], len(e), *np.percentile(e, [50, 90, 99, 100]),
             float((e >= RAIL).mean())))
print("\n   |x6b94| = gp-0x6b94, the AGGREGATOR OUTPUT -- the firmware's delivered torque demand.")
show("(i) ALL ENGAGED, speed-stratified", ENG, vbins=VB)
show("(ii) ENGAGED AND |e4tq| AT THE 4096 RAIL -- 'LKAS asking for everything it can'", RAILM, vbins=VB)
show("(iii) THE SAME, HANDS-LIGHT (|driver torque| < 400)", RAILL, vbins=[(5, 30)])

# =====================================================================================================
hdr("P2 -- 🛑 PROTECTED: steering-WHEEL ANGLE RATE under a hard LKAS command (RAW arrays)")
show("(a) at the rail, speed-stratified -- the large-n version (driver torque NOT controlled)",
     RAILM, chan="rate_c", unit_lbl="deg/s", vbins=VB)
show("(b) at the rail AND hands-light -- the clean version, and it is THIN",
     RAILL, chan="rate_c", unit_lbl="deg/s", vbins=[(5, 15), (15, 30), (5, 30)])
print("\n   UNCONDITIONED exposure descriptor (all engaged), NOT the metric:")
for vlo, vhi in VB:
    for route in ("85", "95"):
        d = RAW[route]
        m = d["eng"] & (d["v"] >= vlo) & (d["v"] < vhi)
        if m.sum() < 25:
            continue
        print("      %2d-%2d km/h  r%s  n=%6d  |wheel rate| p50=%5.1f p90=%6.1f p99=%6.1f max=%6.1f"
              % (vlo, vhi, route, m.sum(), *np.percentile(d["ar"][m], [50, 90, 99, 100])))

# =====================================================================================================
hdr("P4 -- RAMP COST.  10 %->90 % rise of |wheel rate| at onset, and the terminal rate.")


def onsets(d, kind):
    e = np.abs(d["e4tq"])
    n = len(e)
    out = []
    if kind == "cmd":
        low = e < 1000
        run = 0
        for i in range(1, n):
            run = run + 1 if low[i - 1] else 0
            if run >= 20 and e[i] >= RAIL and d["eng"][i] and d["seg"][i] == d["seg"][i - 1]:
                out.append(i)
                run = 0
    else:
        for i in range(1, n):
            if d["eng"][i] and not d["eng"][i - 1] and d["seg"][i] == d["seg"][i - 1]:
                out.append(i)
    return out


for kind, lab in (("cmd", "COMMAND-ONSET  (|e4tq| below 1000 for >=0.2 s, then at the 4096 rail)"),
                  ("lat", "latActive RISING edges")):
    print("\n   %s" % lab)
    for route in ("85", "95"):
        d = RAW[route]
        rt, tr = [], []
        idx = onsets(d, kind)
        for i in idx:
            j = min(i + 100, len(d["t"]))
            if j - i < 60 or d["seg"][j - 1] != d["seg"][i]:
                continue
            seg = d["ar"][i:j]
            term = float(np.percentile(seg[-40:], 90))
            if term < 5.0:
                continue
            k1 = np.nonzero(seg >= 0.1 * term)[0]
            k2 = np.nonzero(seg >= 0.9 * term)[0]
            if len(k1) and len(k2) and k2[0] > k1[0]:
                rt.append((k2[0] - k1[0]) / L.FS * 1000.0)
                tr.append(term)
        if len(rt) < 5:
            print("      r%s %s  %d candidate edges, %d usable -- NOT QUOTED"
                  % (route, L.ROUTES[route]["build"], len(idx), len(rt)))
            continue
        print("      r%s %s  %d edges (%d candidates)   10-90 %% rise p50=%5.0f p90=%5.0f ms   "
              "terminal |wheel rate| p50=%5.1f p90=%6.1f deg/s"
              % (route, L.ROUTES[route]["build"], len(rt), len(idx), np.percentile(rt, 50),
                 np.percentile(rt, 90), np.percentile(tr, 50), np.percentile(tr, 90)))

print("\n[done]")
