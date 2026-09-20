# -*- coding: utf-8 -*-
"""i10 -- THE RETRODICTION TABLE.  Every flown V293 controller, on its own operating point and on
every other route's, against the known outcome.

An operating point is (v, g): the route's median engaged hands-off speed at >= 15 m/s and its
MEASURED angle -> measurement map gain there.  The plant's k, J, b are physical and shared.

Reported per cell: the first -180 deg crossing above 0.8 Hz, |L| there, and the peak |L| in 0.8-8 Hz.
|L| >= 1 at the crossing  =>  predicted LIMIT CYCLE.

ANALYSIS ONLY.  python i10_table.py
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import i9_loop as M  # noqa: E402

F = np.linspace(0.3, 8.0, 30801)          # 0.25 mHz grid


def op_points():
    """(v, g) per route from i5's measured windows (>=15 m/s bin)."""
    d = json.load(open(HERE / "out_i5_plant.json"))
    out = {}
    for tag, c in M.CTRL.items():
        r = c["route"]
        if r in d and "15+" in d[r]:
            out[tag] = dict(v=d[r]["15+"]["v"], g=-d[r]["15+"]["g"], n=d[r]["15+"]["n"])
    return out


def ndf_of():
    d = json.load(open(HERE / "out_i8_relay.json"))
    out = {}
    for tag, c in M.CTRL.items():
        r = c["route"]
        if r in d and "15+" in d[r]:
            out[tag] = dict(frac=d[r]["15+"]["frac_linear"], band=d[r]["15+"]["df_band"])
    return out


def cell(c, v, g, ndf, **kw):
    L, P, D = M.L_of(F, c, v, g, ndf=ndf, **kw)
    cx = M.crossing(F, L)
    pk = M.peak_mag(F, L)
    return dict(fx=None if cx is None else cx[0], Lx=None if cx is None else cx[1],
                ncross=0 if cx is None else cx[2], fpk=pk[0], Lpk=pk[1])


if __name__ == "__main__":
    OP = op_points()
    ND = ndf_of()
    print("OPERATING POINTS (>=15 m/s, engaged hands-off, measured)")
    for t, o in OP.items():
        print(f"   {t:5s} v {o['v']:5.1f} m/s  g {o['g']:.5f} m/s^2/deg  k(v) {M.k_of(o['v']):.5f}  "
              f"fn {M.mode_hz(o['v'], M.HOLD_K_V_REV4):.3f} Hz  lsf {M.lsf_of(o['v']):.4f}  "
              f"windows {o['n']}")
    print("\nRELAY DERATING (measured from the logged error_with_lsf, >=15 m/s)")
    for t, o in ND.items():
        live = M.CTRL[t]["relay_live"]
        print(f"   {t:5s} relay_live {str(live):5s} fric {M.CTRL[t]['fric']:.4f}  "
              f"frac|x|<0.30 {o['frac']:.3f}  band DF {o['band']:.3f}  "
              f"small-signal relay/P {M.CTRL[t]['fric']*M.CTRL[t]['laf']/(0.30*M.CTRL[t]['kp']):.3f}")

    for tau in (0.055, 0.060, 0.075):
        print(f"\n{'='*104}\nSELF CELLS -- each controller on its OWN operating point,  tau = {tau*1000:.0f} ms, "
              f"k x1.0, b x1.0")
        print(f"   {'ctrl':6s} {'v':>5s} {'outcome':22s} {'f_-180':>8s} {'|L| there':>10s} "
              f"{'n_cross':>8s} {'f_peak':>7s} {'|L|peak':>8s}  verdict")
        for t, c in M.CTRL.items():
            if t not in OP:
                continue
            o, nd = OP[t], ND.get(t, dict(frac=1.0, band=1.0))
            r = cell(c, o["v"], o["g"], nd["band"] if np.isfinite(nd["band"]) else nd["frac"], tau=tau)
            verd = "LIMIT CYCLE" if (r["Lx"] is not None and r["Lx"] >= 1.0) else "stable"
            print(f"   {t:6s} {o['v']:5.1f} {M.OUTCOME[t]:22s} "
                  f"{('%8.3f' % r['fx']) if r['fx'] else '      --':>8s} "
                  f"{('%10.3f' % r['Lx']) if r['Lx'] else '        --':>10s} {r['ncross']:8d} "
                  f"{r['fpk']:7.3f} {r['Lpk']:8.3f}  {verd}")

    print(f"\n{'='*104}\nCROSS TABLE  |L| at the first -180 crossing   (tau 60 ms, k x1.0, b x1.0)")
    tags = [t for t in M.CTRL if t in OP]
    print("   ctrl \\ plant  " + "".join(f"{t:>10s}" for t in tags) + "     worst-on")
    store = {}
    for t in tags:
        row, best, bestv = [], None, -1
        for p in tags:
            o = OP[p]
            nd = ND.get(t, dict(frac=1.0, band=1.0))
            r = cell(M.CTRL[t], o["v"], o["g"], nd["band"] if np.isfinite(nd["band"]) else nd["frac"])
            row.append(r["Lx"])
            store[f"{t}|{p}"] = r
        print(f"   {t:12s}  " + "".join(("%10.3f" % x) if x else "        --" for x in row))
    print("\n   RANK per plant column (riskiest first, by |L| at the crossing; '--' = no crossing = safest)")
    for p in tags:
        vals = []
        for t in tags:
            x = store[f"{t}|{p}"]["Lx"]
            vals.append((t, x if x is not None else -1.0))
        vals.sort(key=lambda z: -z[1])
        print(f"   plant {p:6s} (v {OP[p]['v']:4.1f}): " +
              "  ".join(f"{t}{'' if x < 0 else '=%.2f' % x}" for t, x in vals))
    json.dump({k: v for k, v in store.items()}, open(HERE / "out_i10_table.json", "w"), indent=1)
    json.dump(dict(OP=OP, ND=ND), open(HERE / "out_i10_op.json", "w"), indent=1)
