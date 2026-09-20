# -*- coding: utf-8 -*-
"""CENSUS of the two candidate loop-open controls, before anything leans on them.

1. HANDS-ON engaged frames (carState.steeringPressed while laterally engaged): the driver's
   impedance is in the loop and he is partly closing it himself.
2. LONGITUDINAL-ONLY engaged (controlsState active but carControl.latActive false): a genuine
   lateral-loop-OPEN control -- the EPS sees no LKAS command at all.
Plus the ordinary hands-off usable time, and a check of the log's own instrument identity.

out: u0_census.json, U0-OUT.txt
"""
import json
import numpy as np
import ulib as U

BINS = [(0, 8), (8, 15), (15, 22), (22, 99)]
rows = []
for rt in U.FAMILY:
    S = U.load(rt)
    fs = U.FS
    on = S["active"] & S["pressed"]
    off = S["active"] & ~S["pressed"]
    # carControl.enabled (the whole system engaged) but latActive FALSE -> the LATERAL loop is open.
    # NOTE: cs_active in the cache is torqueState.active, which is already the LATERAL flag, so the
    # longitudinal-only control must be built from carControl.enabled, not from it.
    lon = S["cc_enabled"] & ~S["lat_active"]
    # instrument identity: out == -clip(p+i+f, +/-LAF)/LAF
    pre = S["p"] + S["i"] + S["f"]
    pred = -np.clip(pre, -S["laf"], S["laf"]) / S["laf"]
    m = S["active"]
    ident = float(np.nanmax(np.abs(pred[m] - S["out"][m]))) if m.sum() else float("nan")
    # usable RUN structure (>=41 s, the study's highway-run floor)
    hi = U.usable(S, 15)
    runs41 = U.segments(S, hi, 41.0)
    d = dict(route=rt, fam=S["fam"], laf=S["laf"], kp=S["kp"],
             kp_over_laf=S["kp"] / S["laf"],
             t_act=float(S["active"].sum() / fs), ident_max=ident,
             t_hi_runs41=float(sum(b - a for a, b in runs41) / fs), n_runs41=len(runs41))
    for lo, hig in BINS:
        d[f"on_{lo}_{hig}"] = float((on & (S["v"] >= lo) & (S["v"] < hig)).sum() / fs)
        d[f"off_{lo}_{hig}"] = float((off & (S["v"] >= lo) & (S["v"] < hig)).sum() / fs)
        d[f"lon_{lo}_{hig}"] = float((lon & (S["v"] >= lo) & (S["v"] < hig)).sum() / fs)
    # longest contiguous hands-on run and longest lon-only run at 8-22 m/s
    for nm, mk in (("on", on), ("lon", lon)):
        mm = mk & (S["v"] >= 8) & (S["v"] < 22)
        rr = U.segments(S, mm, 0.0)
        d[f"{nm}_822_total"] = float(sum(b - a for a, b in rr) / fs)
        d[f"{nm}_822_longest"] = float(max([(b - a) for a, b in rr], default=0) / fs)
        d[f"{nm}_822_n_ge10s"] = int(sum(1 for a, b in rr if (b - a) / fs >= 10.0))
        d[f"{nm}_822_t_ge10s"] = float(sum((b - a) for a, b in rr if (b - a) / fs >= 10.0) / fs)
    rows.append(d)
    del S

json.dump(rows, open("u0_census.json", "w"), indent=1)

L = []
L.append("CENSUS -- engaged time by speed, and the two candidate loop-open controls.  EVIDENCE (logged flags).")
L.append("'on' = laterally engaged AND steeringPressed.  'lon' = controlsState active but latActive FALSE.")
L.append("")
hdr = (f"{'route':<22}{'fam':<9}{'LAF':>6}{'kp':>5}{'kp/LAF':>8}{'act s':>8}{'ident':>9}"
       f"{'>=15 runs>=41s':>16}")
L.append(hdr)
for d in rows:
    L.append(f"{U.SHORT[d['route']]:<22}{d['fam']:<9}{d['laf']:>6.2f}{d['kp']:>5.2f}{d['kp_over_laf']:>8.4f}"
             f"{d['t_act']:>8.0f}{d['ident_max']:>9.1e}{d['t_hi_runs41']:>11.0f} s/{d['n_runs41']:<3d}")
L.append("")
L.append("HANDS-OFF usable seconds by speed bin:")
L.append(f"{'route':<22}{'0-8':>9}{'8-15':>9}{'15-22':>9}{'>22':>9}")
for d in rows:
    L.append(f"{U.SHORT[d['route']]:<22}" + "".join(f"{d[f'off_{a}_{b}']:>9.0f}" for a, b in BINS))
L.append("")
L.append("HANDS-ON (steeringPressed, laterally engaged) seconds by speed bin:")
L.append(f"{'route':<22}{'0-8':>9}{'8-15':>9}{'15-22':>9}{'>22':>9}{'8-22 tot':>10}{'longest':>9}{'n>=10s':>8}{'t>=10s':>9}")
for d in rows:
    L.append(f"{U.SHORT[d['route']]:<22}" + "".join(f"{d[f'on_{a}_{b}']:>9.0f}" for a, b in BINS)
             + f"{d['on_822_total']:>10.0f}{d['on_822_longest']:>9.1f}{d['on_822_n_ge10s']:>8d}{d['on_822_t_ge10s']:>9.0f}")
L.append("")
L.append("LONGITUDINAL-ONLY engaged (lateral loop OPEN) seconds by speed bin:")
L.append(f"{'route':<22}{'0-8':>9}{'8-15':>9}{'15-22':>9}{'>22':>9}{'8-22 tot':>10}{'longest':>9}{'n>=10s':>8}{'t>=10s':>9}")
for d in rows:
    L.append(f"{U.SHORT[d['route']]:<22}" + "".join(f"{d[f'lon_{a}_{b}']:>9.0f}" for a, b in BINS)
             + f"{d['lon_822_total']:>10.0f}{d['lon_822_longest']:>9.1f}{d['lon_822_n_ge10s']:>8d}{d['lon_822_t_ge10s']:>9.0f}")
L.append("")
for fam in ("V282", "V282old", "TORQ"):
    g = [d for d in rows if d["fam"] == fam]
    L.append(f"{fam:<8} hands-on 8-22 m/s total {sum(d['on_822_total'] for d in g):7.0f} s "
             f"(in runs >=10 s: {sum(d['on_822_t_ge10s'] for d in g):6.0f} s, "
             f"{sum(d['on_822_n_ge10s'] for d in g):3d} runs) | "
             f"lon-only 8-22 {sum(d['lon_822_total'] for d in g):7.0f} s "
             f"(>=10 s: {sum(d['lon_822_t_ge10s'] for d in g):6.0f} s, "
             f"{sum(d['lon_822_n_ge10s'] for d in g):3d} runs)")
out = "\n".join(L)
open("U0-OUT.txt", "w").write(out)
print(out)
