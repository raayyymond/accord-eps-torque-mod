"""Diagnose the >=15 m/s bias: same plant, (a) no quantisation, (b) angle-only quantised, (c) rate-only quantised."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eqlib as E, synth
route = sys.argv[1]
Z = np.load(f"{synth.CACHE}/{route}.npz")
t_u = Z["t_e4"]; u = -Z["e4_cmd"] / 4089.0
t_cs = Z["t_cst"]; v = Z["vego"]; press = Z["spress"] > 0.5
act = (np.interp(t_cs, Z["t_cs"], Z["cs_active"]) > 0.5) & (np.interp(t_cs, Z["t_cc"], Z["lat_active"]) > 0.5)
mask = act & ~press
rr = E.runs(mask, t_cs); t0 = t_cs[rr[0][0]] - 5.0; t1 = t_cs[rr[-1][1] - 1] + 1.0
_round = round
for qa, qr in [(0, 0), (1, 0), (0, 1), (1, 1)]:
    import builtins
    # monkeypatch: simulate with quantisers controlled by wrapping round via a module-level switch
    def sim(D, J):
        a, r, us = synth.simulate(t_u, u, t_cs, v, D, J, 0.003, 0.02, t0=t0, t1=t1)
        return a, r, us
    for D, J in [(0.030, 8e-5), (0.030, 1e-3)]:
        synth.round = (lambda x: x) if not (qa or qr) else _round
        # custom: re-simulate unquantised then quantise here
        synth.round = lambda x: x
        a, r, us = sim(D, J)
        if qa: a = np.round(a / 0.1) * 0.1
        if qr: r = np.round(r)
        m = mask & np.isfinite(a)
        for cfg in [dict(band=(None, 6.0), guard=5, demean_block=True)]:
            bl, _ = E.accumulate(t_cs, np.nan_to_num(a), np.nan_to_num(r), v, m, t_u, us, variant="rate", **cfg)
            ds = [E.argmin_sub(E.solve([x for x in bl if x["bin"] == bi])[0])[0] for bi in range(3)]
            print(f"quantA{qa} quantR{qr} D{D*1e3:.0f} J{J:g}", [round(d, 1) for d in ds], flush=True)
