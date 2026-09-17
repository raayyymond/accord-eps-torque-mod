"""Tercile-trend check: does the low->high demand lag/error trend the finding describes ("V282's lag
shrinks by only 0.1-0.15 s lo->hi; T64 is ~2x V282 on small/mid demand") survive independent re-
reduction, with and without the dominant V282 route? pose channel, band 0.15-0.3 and 0.3-0.6, vb 15-22
and >22 (the finding's headline cells). Reuses verify_analyze.py's helpers -- same script family, not
a second independent implementation (that independence already exists between verify_* and s1_*).
"""
import json
from pathlib import Path
import numpy as np
import verify_analyze as A

HERE = Path(__file__).resolve().parent
routes = A.load_all()
group_of = {r: routes[r]["meta"]["group"] for r in routes}
ld_by_route = {r: routes[r]["meta"]["lat_delay"] for r in routes}
V282 = [r for r in routes if group_of[r] == "V282"]
T64 = [r for r in routes if group_of[r] == "T64"]
DOM = "0000006c--2bc842dbac"
variants = {"V282_full": V282, "V282_LOO_no_dom": [r for r in V282 if r != DOM], "T64_full": T64}
TN = ["lo", "mid", "hi"]

out = []
for band_i, band in enumerate(A.BANDS):
    for vb_i, vbn in enumerate(A.VBN):
        if vbn not in ("15-22", ">22"):
            continue
        edges = A.tercile_edges(routes, band_i, vb_i, group_of)
        if edges is None:
            continue
        for name, rsel in variants.items():
            for ti in range(3):
                rid, Amat = A.route_chunk_sums(routes, rsel, band_i, vb_i, edges, "pose", terc_i=ti)
                if Amat.shape[0] == 0 or Amat[:, 0].sum() < 15:
                    out.append(dict(band=f"{band[0]}-{band[1]}", vb=vbn, variant=name, terc=TN[ti],
                                     sec=0, rE_D=None, lag_s=None))
                    continue
                m = A.metrics(Amat.sum(0))
                lag = A.lag_seconds(routes, rsel, band_i, vb_i, edges, "pose", ld_by_route, terc_i=ti)
                out.append(dict(band=f"{band[0]}-{band[1]}", vb=vbn, variant=name, terc=TN[ti],
                                 sec=round(m["sec"], 1), rE_D=round(m["rE_D"], 3), lag_s=round(lag, 3)))

json.dump(out, open(HERE / "verify_terciles.json", "w"), indent=1)
print(f"{'band':10s}{'vb':7s}{'variant':18s}{'terc':5s}{'sec':7s}{'rE_D':7s}{'lag_s':7s}")
for c in out:
    print(f"{c['band']:10s}{c['vb']:7s}{c['variant']:18s}{c['terc']:5s}{c['sec']:<7.1f}"
          f"{'nan' if c['rE_D'] is None else c['rE_D']:<7}{'nan' if c['lag_s'] is None else c['lag_s']:<7}")
