"""Positive control + plant-phase bias: the synthetic torque-mode plant driven by the LOGGED 0xE4 command of the torque
routes (true send times), sampled at the TRUE carState times, quantised (0.1 deg, 1 deg/s), then passed through the
IDENTICAL gridding + band-pass + xcorr + sinc-peak pipeline as the real data, on the SAME blocks.

usage: python s05_synth.py <tag> D_ms J b F [k_scale] [fb_gain fb_delay_ms]
writes out/synth_<tag>.json : pooled sinc/parabolic peak per pair per speed bin and all, plus per route (all bins)
"""
import sys, json, time
import numpy as np
import xc_lib as X

PAIRS = [("u_e4", "acc_r"), ("u_e4", "acc_a"), ("u_e4", "ang"), ("u_e4", "rate")]
WIN = {"acc_r": (-100, 250), "acc_a": (-100, 250), "rate": (-50, 350), "ang": (-50, 400)}


def main():
    tag = sys.argv[1]; D = float(sys.argv[2]) / 1e3; J = float(sys.argv[3]); b = float(sys.argv[4]); F = float(sys.argv[5])
    ks = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0
    fbg = float(sys.argv[7]) if len(sys.argv) > 7 else 0.0
    fbd = float(sys.argv[8]) / 1e3 if len(sys.argv) > 8 else 0.0
    routes = X.TORQUE_ROUTES
    acc = {p: X.XC() for p in PAIRS}
    t0 = time.time()
    for route in routes:
        R = X.load_route(route)
        B = np.load(X.HERE / "_cache" / f"real_blocks_{route}.npz")
        u_val = -R["e4_cmd"] / X.E4_SCALE
        for ts, bi in zip(B["tstart"], B["bin"]):
            span = (ts - 3.0, ts + 12.0 + 0.05)
            i0, i1 = np.searchsorted(R["t_cst"], [span[0] + 0.02, span[1] - 0.02])
            t_s = R["t_cst"][i0:i1]; v_s = R["vego"][i0:i1]
            sa, sr, tt_, uc_ = X.simulate(R["t_e4"], u_val, t_s, v_s, D, J, b, F, k_scale=ks, h=0.001, t_span=span,
                                fb_gain=fbg, fb_delay=fbd if fbg > 0 else 0.011)
            tg = ts + np.arange(1200) * X.DT
            sag = np.interp(tg, t_s, sa); srg = np.interp(tg, t_s, sr)
            ug = -X.zoh(R["t_e4"], R["e4_cmd"], tg) / X.E4_SCALE
            if fbg > 0:
                ug = np.interp(tg, tt_, uc_)   # the command as it would be logged, feedback included
            Y = X.responses(sag, srg)
            for (uk, yk) in PAIRS:
                acc[(uk, yk)].add(ug, Y[yk], int(bi), route)
        del R, B
    out = dict(tag=tag, D_ms=D * 1e3, J=J, b=b, F=F, k_scale=ks, fb_gain=fbg, fb_delay_ms=fbd * 1e3, res={})
    for (uk, yk), xc in acc.items():
        key = f"{uk}|{yk}"; out["res"][key] = {}
        for bi, bn in list(enumerate(X.BIN_NAMES)) + [(None, "all")]:
            cur = xc.curve(None if bi is None else (lambda bl, bi=bi: bl[0] == bi))
            if cur is None:
                continue
            p, s, v = X.peak(cur, +1, *WIN[yk])
            out["res"][key][bn] = dict(par=p, sinc=s, corr=v)
        for r in routes:
            cur = xc.curve(lambda bl, r=r: bl[1] == r)
            if cur is not None:
                p, s, v = X.peak(cur, +1, *WIN[yk])
                out["res"][key]["route:" + r] = dict(par=p, sinc=s, corr=v)
    json.dump(out, open(X.HERE / "out" / f"synth_{tag}.json", "w"), indent=1)
    line = " ".join(f"{k.split('|')[1]}:{v['all']['sinc']:.1f}" for k, v in out["res"].items())
    print(f"{tag} D={D*1e3:.0f} J={J:g} b={b:g} F={F:g} ks={ks:g} fb={fbg:g}  ALL {line}   "
          f"bins acc_r {[round(out['res']['u_e4|acc_r'][bn]['sinc'],1) for bn in X.BIN_NAMES if bn in out['res']['u_e4|acc_r']]}"
          f"  ({time.time()-t0:.0f} s)", flush=True)


if __name__ == "__main__":
    main()
