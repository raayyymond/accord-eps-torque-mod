import numpy as np, time
import xc_lib as X
from scipy import signal
route = "0000006e--6ca3e014fd"
R = X.load_route(route); B = np.load(X.HERE / "_cache" / f"real_blocks_{route}.npz")
G = X.grid_route(R)
u_val = -R["e4_cmd"] / X.E4_SCALE
for (J, b, F) in [(8e-5, 6e-4, 0.02), (8e-5, 6e-4, 0.0), (8e-5, 3e-3, 0.02), (3e-4, 6e-4, 0.02), (1e-3, 6e-4, 0.02)]:
    rr = []; rs = []; ra = []; ras = []
    t0 = time.time()
    for ts in B["tstart"][:20]:
        span = (ts - 3, ts + 12.05)
        i0, i1 = np.searchsorted(R["t_cst"], [span[0] + .02, span[1] - .02])
        sa, sr = X.simulate(R["t_e4"], u_val, R["t_cst"][i0:i1], R["vego"][i0:i1], 0.03, J, b, F, h=0.001, t_span=span)
        tg = ts + np.arange(1200) * X.DT
        sag = np.interp(tg, R["t_cst"][i0:i1], sa); srg = np.interp(tg, R["t_cst"][i0:i1], sr)
        k = np.searchsorted(G["t"], ts)
        bp = lambda x: signal.sosfiltfilt(X.SOS, x - x.mean())[100:-100]
        rr.append(np.std(bp(G["sr"][k:k+1200]))); rs.append(np.std(bp(srg)))
        ra.append(np.std(G["sa"][k:k+1200])); ras.append(np.std(sag))
        stuck = np.mean(srg == 0)
    print(J, b, F, "band rate rms real %.2f sim %.2f ; angle std real %.2f sim %.2f ; frac rate==0 sim %.2f  %.1fs" % (np.mean(rr), np.mean(rs), np.mean(ra), np.mean(ras), stuck, time.time()-t0))
