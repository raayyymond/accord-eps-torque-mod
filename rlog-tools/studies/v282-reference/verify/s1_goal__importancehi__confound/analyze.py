"""Analyze verify_importance_raw.json for the CONFOUND checks (see verify_importance.py docstring)."""
import json
import numpy as np

R = json.load(open("verify_importance_raw.json"))
VBN = ["2-8", "8-15", "15-22", ">22"]
BANDS = ["0.15-0.3", "0.3-0.6"]
HI_CELLS = [(vb, ba) for vb in ("15-22", ">22") for ba in BANDS]


def agg(rows):
    """sum Sxx, SSE, sec over a set of rows -> Sxx, SSE, sec, rE^2"""
    Sxx = sum(r["Sxx"] for r in rows); SSE = sum(r["SSE"] for r in rows); sec = sum(r["sec"] for r in rows)
    return Sxx, SSE, sec, (SSE / Sxx if Sxx > 0 else float("nan"))


def rE(rows, group, vb, band, chan, routes=None):
    sel = [r for r in rows if r["group"] == group and r["vb"] == vb and r["band"] == band and r["chan"] == chan
           and (routes is None or r["route"] in routes)]
    if not sel:
        return None
    return agg(sel)


def importance_table(chan, base_routes=None, test_routes=None, base_group="V282", test_group="T64", verbose=True):
    """Per (vb,band) cell over ALL vb x BANDS: excess = Sxx_test*(rE_test^2 - rE_base^2); shares of positive total."""
    cells = {}
    tot_test_err = 0.0
    for vb in VBN:
        for ba in BANDS:
            b = rE(R, base_group, vb, ba, chan, base_routes)
            te = rE(R, test_group, vb, ba, chan, test_routes)
            if te is None:
                continue
            Sxx_t, SSE_t, sec_t, rE2_t = te
            tot_test_err += SSE_t
            if b is None:
                cells[(vb, ba)] = dict(excess=None, sec=sec_t, rE2_t=rE2_t, SSE_t=SSE_t)
                continue
            Sxx_b, SSE_b, sec_b, rE2_b = b
            excess = Sxx_t * (rE2_t - rE2_b)
            cells[(vb, ba)] = dict(excess=excess, sec=sec_t, rE2_t=rE2_t, rE2_b=rE2_b, SSE_t=SSE_t, sec_b=sec_b)
    tot_pos = sum(max(c["excess"], 0) for c in cells.values() if c["excess"] is not None)
    for k, c in cells.items():
        c["excess_share"] = (max(c["excess"], 0) / tot_pos) if (tot_pos > 0 and c["excess"] is not None) else None
    hi_share = sum(c["excess_share"] for k, c in cells.items() if k in HI_CELLS and c["excess_share"] is not None)
    hi_excess_over_own_err = sum(max(c["excess"], 0) for k, c in cells.items() if k in HI_CELLS and c["excess"] is not None) / tot_test_err if tot_test_err > 0 else float("nan")
    tot_excess_over_own_err = tot_pos / tot_test_err if tot_test_err > 0 else float("nan")
    if verbose:
        print(f"  chan={chan} base={base_group}/{base_routes} test={test_group}/{test_routes}: "
              f"hi_share={hi_share*100:.1f}%  hi_excess/own_err={hi_excess_over_own_err*100:.1f}%  "
              f"tot_excess/own_err={tot_excess_over_own_err*100:.1f}%  tot_test_sec_hi={sum(c['sec'] for k,c in cells.items() if k in HI_CELLS):.0f}")
        for k in sorted(cells, key=lambda k: -(cells[k]['excess_share'] or -1)):
            c = cells[k]
            es = f"{c['excess_share']*100:5.1f}%" if c['excess_share'] is not None else "  n/a"
            print(f"      {k[0]:5s} {k[1]:9s} excess_share={es}  sec={c['sec']:.0f}")
    return hi_share, hi_excess_over_own_err, tot_excess_over_own_err, cells


V282_ALL = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]
V282_NO6C = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd"]
V282_ONLY6C = ["0000006c--2bc842dbac"]
T64_ALL = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]
T64_6C = ["0000006c--68c6e94b17"]
T64_6D = ["0000006d--05e83bb04f"]

print("=" * 100)
print("1. POOLED replication (independent estimator, pose channel, no demand-tercile matching):")
importance_table("la_pose")

print("\n" + "=" * 100)
print("2. LEAVE-ONE-ROUTE-OUT on V282 baseline (pose channel, T64 = both routes):")
print(" -- baseline = 64+65 only (DROP the dominant 2bc842dbac route) --")
importance_table("la_pose", base_routes=V282_NO6C)
print(" -- baseline = 2bc842dbac ONLY (the dominant route alone) --")
importance_table("la_pose", base_routes=V282_ONLY6C)

print("\n" + "=" * 100)
print("3. PER-ROUTE T64 (pose channel, V282 baseline = all 3 routes as in original):")
print(" -- T64 = 68c6e94b17 ONLY --")
importance_table("la_pose", test_routes=T64_6C)
print(" -- T64 = 05e83bb04f ONLY --")
importance_table("la_pose", test_routes=T64_6D)

print("\n" + "=" * 100)
print("4. CHANNEL SWAP (all routes as in original, base=V282 all, test=T64 all):")
print(" -- la_act channel --")
importance_table("la_act")
print(" -- la_yaw channel --")
importance_table("la_yaw")

print("\n" + "=" * 100)
print("5. Reference-side homogeneity: per-route V282 rE^2 and mean|x| in the 4 highway cells (pose):")
for route in V282_ALL:
    for vb, ba in HI_CELLS:
        r = rE(R, "V282", vb, ba, "la_pose", [route])
        rx = [x for x in R if x["route"] == route and x["vb"] == vb and x["band"] == ba and x["chan"] == "la_pose"]
        mx = rx[0]["mean_abs_x"] if rx else float("nan")
        if r:
            Sxx, SSE, sec, rE2 = r
            print(f"  {route:24s} {vb:5s} {ba:9s} rE={np.sqrt(rE2):.3f}  sec={sec:.0f}  mean|x|={mx:.3f}")

print("\n" + "=" * 100)
print("6. Test-side (T64) per-route mean|x| in the 4 highway cells, to check demand-amplitude match with V282:")
for route in T64_ALL:
    for vb, ba in HI_CELLS:
        rx = [x for x in R if x["route"] == route and x["vb"] == vb and x["band"] == ba and x["chan"] == "la_pose"]
        if rx:
            print(f"  {route:24s} {vb:5s} {ba:9s} sec={rx[0]['sec']:.0f}  mean|x|={rx[0]['mean_abs_x']:.3f}")
for route in V282_ALL:
    for vb, ba in HI_CELLS:
        rx = [x for x in R if x["route"] == route and x["vb"] == vb and x["band"] == ba and x["chan"] == "la_pose"]
        if rx:
            print(f"  {route:24s} {vb:5s} {ba:9s} sec={rx[0]['sec']:.0f}  mean|x|={rx[0]['mean_abs_x']:.3f}")
