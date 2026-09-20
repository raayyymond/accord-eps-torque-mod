"""MODEL-BASED cross-correlation delay estimator (plant-phase-corrected xcorr).

The plain xcorr of command vs steering acceleration is biased by the plant's phase (s05: up to -70 ms and NOT additive
in D). The correction done properly: simulate the plant with ZERO delay from the logged command, then find the time
shift d that best aligns the simulated response with the measured one:
    rho(d) = sum_blocks <bp(y_meas)(t), bp(y_sim0)(t - d)> / norms          d in [-30, 150] ms, 1 ms step
Because the plant (up to the slow speed schedule of k) is time-invariant, y_meas(t) = y_sim0(t - D) exactly when the
model is right, so the peak sits at D with no plant-phase bias. The plant is chosen BLINDLY from a grid (J, b, F, k
scale) by the highest pooled rho of the rate response, jointly with d (output-error system identification).

usage:
  python s06_mb.py real   <tag>                              # real torque-route data
  python s06_mb.py synth  <tag> D_ms J b F ks [fb_gain]      # synthetic truth (quantised, carState-timed) = control
writes _cache/mb_<tag>.npz : num[plant, block, sig, d], nx[plant, block, sig], ny[block, sig], block meta
"""
import sys, time, itertools
import numpy as np
from scipy import signal
import xc_lib as X

DGRID = np.arange(-30, 151, 1) / 1e3
SIGS = ["rate", "acc_r", "ang"]
GRID_J = [8e-5, 1.5e-4, 3e-4, 1e-3]
GRID_B = [3e-4, 6e-4, 1.5e-3, 3e-3]
GRID_F = [0.0, 0.01, 0.02, 0.03]
GRID_KS = [1.0]
import os, json as _json
if os.environ.get("MB_GRID"):
    _g = _json.loads(os.environ["MB_GRID"]); GRID_J, GRID_B, GRID_F, GRID_KS = _g["J"], _g["b"], _g["F"], _g["ks"]
EDGE = 100


def bp(x):
    x = x - x.mean(axis=-1, keepdims=True)
    return signal.sosfiltfilt(X.SOS, x, axis=-1)[..., EDGE:-EDGE]


def meas_signals(sa, sr):
    Y = X.responses(sa, sr)
    return np.stack([bp(Y[s]) for s in SIGS])      # (sig, N)


def main():
    mode, tag = sys.argv[1], sys.argv[2]
    plants = list(itertools.product(GRID_J, GRID_B, GRID_F, GRID_KS))
    if len(sys.argv) > 9 and sys.argv[9] == "small":
        plants = [p for p in plants if p[2] in (0.0, 0.02)]
    truth = None
    if mode == "synth":
        truth = dict(D=float(sys.argv[3]) / 1e3, J=float(sys.argv[4]), b=float(sys.argv[5]), F=float(sys.argv[6]),
                     ks=float(sys.argv[7]), fb=float(sys.argv[8]) if len(sys.argv) > 8 else 0.0,
                     dist=float(os.environ.get("MB_DIST", "0")))
    num_l, nx_l, ny_l, meta = [], [], [], []
    t0 = time.time()
    for route in X.TORQUE_ROUTES:
        R = X.load_route(route)
        B = np.load(X.HERE / "_cache" / f"real_blocks_{route}.npz")
        if mode == "real":
            G = X.grid_route(R)
        u_val = -R["e4_cmd"] / X.E4_SCALE
        for ts, bi, vmed in zip(B["tstart"], B["bin"], B["vmed"]):
            span = (ts - 3.0, ts + 12.2)
            i0, i1 = np.searchsorted(R["t_cst"], [span[0] + 0.02, span[1] - 0.02])
            t_s = R["t_cst"][i0:i1]; v_s = R["vego"][i0:i1]
            tg = ts + np.arange(1200) * X.DT
            if mode == "real":
                k = int(round((ts - G["t"][0]) / X.DT))
                sa_m, sr_m = G["sa"][k:k + 1200], G["sr"][k:k + 1200]
                t_u, uv = R["t_e4"], u_val
            else:
                sa_q, sr_q, tt_, uc_ = X.simulate(R["t_e4"], u_val, t_s, v_s, truth["D"], truth["J"], truth["b"],
                                                  truth["F"], k_scale=truth["ks"], t_span=span, fb_gain=truth["fb"],
                                                  dist_std=truth["dist"], dist_seed=int(ts * 100) % 2**31)
                sa_m = np.interp(tg, t_s, sa_q); sr_m = np.interp(tg, t_s, sr_q)
                if truth["fb"] > 0:            # the estimator sees the command as logged, feedback included
                    t_u, uv = tt_, uc_
                else:
                    t_u, uv = R["t_e4"], u_val
            ym = meas_signals(sa_m, sr_m)                     # (S, N)
            ny_l.append((ym ** 2).sum(-1))
            nums = np.zeros((len(plants), len(SIGS), len(DGRID))); nxs = np.zeros((len(plants), len(SIGS)))
            for pi, (J, b, F, ks) in enumerate(plants):
                tt, ang, rate, _ = X.sim_fine(t_u, uv, t_s, v_s, 0.0, J, b, F, k_scale=ks, t_span=span)
                tq = tg[None, :] - DGRID[:, None]            # (d, N) sample the zero-delay sim d earlier
                sa_s = np.interp(tq, tt, ang); sr_s = np.interp(tq, tt, rate)
                ys = [bp(sr_s), bp(np.gradient(sr_s, axis=-1) * X.FS), bp(sa_s)]
                for si in range(len(SIGS)):
                    nums[pi, si] = ys[si] @ ym[si]
                    nxs[pi, si] = float(np.mean((ys[si] ** 2).sum(-1)))
            num_l.append(nums); nx_l.append(nxs); meta.append((route, float(ts), int(bi), float(vmed)))
        print(f"  {tag} {route} blocks {len(B['tstart'])} ({time.time()-t0:.0f} s)", flush=True)
        del R, B
        if mode == "real":
            del G
    np.savez(X.HERE / "_cache" / f"mb_{tag}.npz", num=np.array(num_l).transpose(1, 0, 2, 3), nx=np.array(nx_l).transpose(1, 0, 2),
             ny=np.array(ny_l), plants=np.array(plants), dgrid=DGRID, sigs=np.array(SIGS),
             route=np.array([m[0] for m in meta]), tstart=np.array([m[1] for m in meta]),
             bin=np.array([m[2] for m in meta]), vmed=np.array([m[3] for m in meta]),
             truth=np.array([truth[k] for k in ["D", "J", "b", "F", "ks", "fb", "dist"]]) if truth else np.array([]))
    print(f"done {tag} ({time.time()-t0:.0f} s)")


if __name__ == "__main__":
    main()
