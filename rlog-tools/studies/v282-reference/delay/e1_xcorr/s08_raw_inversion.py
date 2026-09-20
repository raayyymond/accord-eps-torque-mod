"""Positive control for the PLAIN xcorr (u_e4 vs acc from rate, 1-6 Hz, sinc peak) with plant-phase bias correction by
inversion of the synthetic raw-peak(D) map. The map for a plant is built from D in {0,15,45,75,90,120} (30 and 60 are
held OUT) and inverted by linear interpolation; recovery is tested on the synthetic raw peaks at D = 30 and 60, both at
the SAME plant and across plants (the realistic case: J is not known). Then the real raw peak is inverted per plant.
"""
import json, itertools
import numpy as np
import xc_lib as X

PL = ["J8e-5_b0.0006_F0.02", "J3e-4_b0.0006_F0.02", "J1e-3_b0.0006_F0.02"]
TRAIN = [0, 15, 45, 75, 90, 120]; TEST = [30, 60]
real = json.load(open(X.HERE / "out" / "real_summary.json"))
out = {}


def raw(pl, D, key="u_e4|acc_r", bn="all"):
    return json.load(open(X.HERE / "out" / f"synth_scan_{pl}_D{D}.json"))["res"][key][bn]["sinc"]


def inv(pl, val, bn="all"):
    xs = np.array([raw(pl, D, bn=bn) for D in TRAIN]); ys = np.array(TRAIN, float)
    mono = bool(np.all(np.diff(xs) > 0))
    return float(np.interp(val, xs, ys, left=np.nan, right=np.nan)), mono, xs.tolist()


print("raw sinc peak (ms) of u_e4 vs acc_r on the synthetic plant, all speeds pooled")
for pl in PL:
    print(f"  {pl:22s} " + " ".join(f"D{D}:{raw(pl, D):6.1f}" for D in sorted(TRAIN + TEST)))
print("\nrecovery (map plant -> truth plant): recovered D for true 30 / 60")
for mp, tp in itertools.product(PL, PL):
    rec = [inv(mp, raw(tp, D))[0] for D in TEST]
    ok = all(abs(r - D) <= 5 for r, D in zip(rec, TEST))
    out[f"{mp}->{tp}"] = dict(rec30=rec[0], rec60=rec[1], pass5ms=ok, map_monotone=inv(mp, 0)[1])
    print(f"  map {mp:22s} truth {tp:22s}  30->{rec[0]:6.1f}  60->{rec[1]:6.1f}  {'PASS' if ok else 'FAIL'}  monotone {inv(mp,0)[1]}")
print("\nreal torque-route raw peak inverted through each plant's map")
for bn in ["<8", "8-15", ">=15", "all"]:
    v = real["torque|u_e4|acc_r"][bn]["pooled"]["sinc"]
    lo, hi = real["torque|u_e4|acc_r"][bn]["pooled"]["ci_route"]
    line = f"  bin {bn:5s} raw {v:5.1f} [{lo:.1f},{hi:.1f}] ->"
    for pl in PL:
        d, m, _ = inv(pl, v); dl, _, _ = inv(pl, lo); dh, _, _ = inv(pl, hi)
        line += f"  {pl.split('_')[0]}: {d:5.1f} [{dl:.1f},{dh:.1f}]"
        out[f"real_{bn}_{pl}"] = dict(D=d, lo=dl, hi=dh)
    print(line)
json.dump(out, open(X.HERE / "out" / "raw_inversion.json", "w"), indent=1)
