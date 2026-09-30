# -*- coding: utf-8 -*-
"""j_metric_r71b.py -- the operator's GOAL METRIC J on route 75604b0a432fdc89_00000071--a7b8ba5d9d (V294, r1 fork config).

Subagent "bands", 2026-09-30.  ANALYSIS ONLY.  Reuses the record's own implementation, unchanged:
    rlog-tools/studies/v282-reference/shapedgain/frontier/f1_extract.py  (per-window FFTs, the metric's population)
    rlog-tools/studies/v282-reference/shapedgain/frontier/f2_metric.py   (J = in-band error power / in-band demand power)
J = total (model-desired - achieved) lateral-accel power over 0.15-2.4 Hz / in-band demand power, ONE denominator,
>= 15 m/s, laterally engaged hands-off runs >= 30 s, unsaturated 10.24 s windows (Hann, hop 512).
Achieved = livePose yaw rate * v (independent of the controller's own measurement).

Only two things are changed, both by monkeypatch so the record's files are untouched:
  * the route->group map gains "00000071--a7b8ba5d9d": "V294";
  * f1's output directory is redirected to this study's _scratch (the record's frontier/out is not written).

POSITIVE CONTROL (must pass or J is void): the same code re-run here on 00000064--ce6b0b0ebb (V282, 0.4653 in
f2_metric.json) and 00000075--6c8687d5bd (rev 4, 1.0151) must reproduce the record to 1e-3.
The per-route sign/alignment control is f2's own Vscalar (coherent gain of achieved on the controller measurement);
V282/T routes read |V| 0.92-0.96 at -10..-14 deg -- a sign error would read ~180 deg.
"""
import json
import sys
from pathlib import Path

import numpy as np

KIT = Path(__file__).resolve().parents[5]
REF = KIT / "rlog-tools" / "studies" / "v282-reference"
FRONT = REF / "shapedgain" / "frontier"
sys.path.insert(0, str(REF)); sys.path.insert(0, str(FRONT)); sys.path.insert(0, str(REF / "loopshape" / "loopshape"))
import lp_lib as LP        # noqa: E402
import v282cmp as V        # noqa: E402
import f1_extract as F1    # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROUTE = "00000071--a7b8ba5d9d"
LP.GROUPS[ROUTE] = "V294"
V.ROUTES[ROUTE] = dict(group="V294", eps="V294", fork="20d24ab7", note="V294 + toggle-config_V294_accel-trim_r1")
OUT = Path(__file__).resolve().parent / "_scratch" / "jmetric"
OUT.mkdir(parents=True, exist_ok=True)
F1.OUT = OUT
BAND = (0.15, 2.4)
SUB = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40)]
REC = json.load(open(FRONT / "out" / "f2_metric.json"))


def metric(route):
    D = np.load(OUT / f"f1_{route}.npz")
    f = D["f"]
    b = (f >= BAND[0]) & (f <= BAND[1])
    X, Y, M = D["X"], D["Y"], D["M"]
    num = np.sum(np.conj(M[:, b]) * Y[:, b]); den = np.sum(np.abs(M[:, b]) ** 2)
    Vsc = num / den
    E = X - Y
    px = float(np.sum(np.abs(X[:, b]) ** 2))
    pe = float(np.sum(np.abs(E[:, b]) ** 2))
    bands = [float(np.sum(np.abs(E[:, (f >= lo) & (f < hi)]) ** 2)) / px for lo, hi in SUB]
    # gain vs timing split in-band: |X|-|Y| magnitude-only error share (per bin) vs the full complex error
    mag_only = float(np.sum((np.abs(X[:, b]) - np.abs(Y[:, b])) ** 2)) / px
    # achieved/desired transfer in-band, power weighted (H1)
    H = np.sum(np.conj(X[:, b]) * Y[:, b], axis=0) / np.maximum(np.sum(np.abs(X[:, b]) ** 2, axis=0), 1e-30)
    fb = f[b]
    Hs = {}
    for lo, hi in SUB:
        s = (fb >= lo) & (fb < hi)
        w = np.sum(np.abs(X[:, b][:, s]) ** 2, axis=0)
        Hs["%.2f-%.2f" % (lo, hi)] = (float(np.average(np.abs(H[s]), weights=w)),
                                      float(np.degrees(np.angle(np.sum(np.conj(X[:, b][:, s]) * Y[:, b][:, s])))))
    return dict(nwin=int(X.shape[0]), metric=pe / px, bands=bands, mag_only=mag_only, Vabs=float(abs(Vsc)),
                Varg=float(np.degrees(np.angle(Vsc))), vmed=float(np.median(D["vmed"])), laf=float(D["laf"]), H=Hs)


def main():
    print("=" * 110)
    print("J METRIC -- the record's f1/f2 code, unchanged; route", ROUTE)
    print("=" * 110)
    rows = {}
    for r in ("00000064--ce6b0b0ebb", "00000075--6c8687d5bd", "00000076--d0b7ea7e4d", ROUTE):
        m = F1.do_route(r)
        if m["nwin"] == 0:
            print(f"  {r}: 0 windows -- J not defined"); continue
        rows[r] = metric(r); rows[r].update(sec=m["sec"])
    print()
    print("POSITIVE CONTROL -- this run vs f2_metric.json (must agree to 1e-3)")
    ok_all = True
    for r in ("00000064--ce6b0b0ebb", "00000075--6c8687d5bd", "00000076--d0b7ea7e4d"):
        want = REC[r]["metric_inband"]; got = rows[r]["metric"]
        ok = abs(got - want) < 1e-3
        ok_all &= ok
        print(f"  {r} {LP.GROUPS[r]:5s} J {got:.4f}  record {want:.4f}  nwin {rows[r]['nwin']} vs {REC[r]['nwin']}  {'PASS' if ok else 'FAIL'}")
    print("  positive control:", "PASS" if ok_all else "FAIL -- J below is VOID")
    print()
    print("J BY ROUTE  (one denominator; sub-band terms sum to J)")
    print(f"{'route':24s} {'grp':5s} {'nwin':>5s} {'sec':>6s} {'v med':>6s} {'J':>7s} | {'0.15-0.3':>8s} {'0.3-0.6':>8s} {'0.6-1.2':>8s} {'1.2-2.4':>8s} | {'|V|':>5s} {'argV':>6s} | {'mag-only':>8s}")
    for r, d in rows.items():
        print(f"{r:24s} {LP.GROUPS[r]:5s} {d['nwin']:5d} {d['sec']:6.0f} {d['vmed']:6.1f} {d['metric']:7.4f} | "
              + " ".join("%8.4f" % x for x in d["bands"]) + f" | {d['Vabs']:5.3f} {d['Varg']:+6.1f} | {d['mag_only']:8.4f}")
    print()
    print("des -> achieved |H| and phase by sub-band (H1, demand-power weighted)")
    for r, d in rows.items():
        print(f"  {r:24s} " + "  ".join("%s: %.3f @ %+.0f deg" % (k, v[0], v[1]) for k, v in d["H"].items()))
    # the pooled references from the record
    fam = {}
    for r, d in REC.items():
        a = fam.setdefault(d["group"], [0.0, 0.0, 0, 0.0]); a[0] += d["pe"]; a[1] += d["px"]; a[2] += d["nwin"]; a[3] += d["sec"]
    print()
    print("RECORD families (f2_metric.json, pooled pe/px):  " + "  ".join("%s %.3f (%d win)" % (g, a[0] / a[1], a[2]) for g, a in fam.items()))
    print("brief's reference values: V282 0.442 (re-derived 0.471 in f5_frontier), rev 6.4 as flown 1.3512")
    json.dump(dict(rows=rows, control_pass=bool(ok_all), fam={g: a[0] / a[1] for g, a in fam.items()}),
              open(Path(__file__).resolve().parent / "j_metric_r71b_out.json", "w"), indent=1)


if __name__ == "__main__":
    main()
