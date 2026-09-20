"""D_ctl, method 2: timestamp topology only -- no value matching, so it works on every route.

card.py step() is, in order:  state_update() [drain can -> CS; sm.update(0) picks up whatever carControl
has arrived] -> state_publish() [pm.send('carState')] -> controls_update(CS, self.sm['carControl'])
[CI.apply -> pm.send('sendcan')].  So within ONE card cycle carState is published a few hundred us before
the 0xE4 that is actuated, and the carControl being actuated is the one controlsd produced from the
PREVIOUS carState.  That gives three measurable gaps:

  g0 = t(sendcan) - t(carState published in the SAME cycle)      -- should be ~0.2-2 ms, one-sided
  g1 = t(sendcan) - t(carState one cycle earlier)  = D_ctl       -- the sample the command actually used
  lag_xc = integer frame lag that maximises corr(e4, cs_out)     -- confirms the 1-cycle offset without
                                                                    relying on exact integer equality

Plus: corr(e4, cs_out) at the best lag, to show whether e4 is a clean scalar multiple of cs_out on that
route (if not, the exact-value match in chain.py is expected to be unreliable there -- that is the only
thing it was used for).
"""
import sys, json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V

TORQUE = ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
          "00000076--d0b7ea7e4d", "00000075--6c8687d5bd"]
V282 = ["0000006c--2bc842dbac", "00000064--ce6b0b0ebb"]
q = lambda x, *p: [float(np.percentile(x, pp)) for pp in (p or (5, 50, 95))]

res = {}
for rk in TORQUE + V282:
    D = np.load(V.CACHE / f"{rk}.npz", allow_pickle=True)
    t_cs, cs_out, act = D["t_cs"], D["cs_out"], D["cs_active"] > 0.5
    t_e4, e4 = D["t_e4"], D["e4_cmd"]
    t_cst = D["t_cst"]
    # only engaged, command actually moving (so 'nearest' is meaningful and the correlation has content)
    eng = np.interp(t_e4, t_cs, act.astype(float)) > 0.5
    mov = np.abs(e4) > 50
    sel = eng & mov & (t_e4 > t_cst[2])
    te = t_e4[sel]
    k = np.searchsorted(t_cst, te) - 1            # carState published in the same card cycle
    ok = (k >= 1) & (k < len(t_cst) - 1)
    k, te = k[ok], te[ok]
    g0 = (te - t_cst[k]) * 1e3
    g1 = (te - t_cst[k - 1]) * 1e3
    dcst = np.diff(t_cst) * 1e3

    # integer-frame lag of e4 vs cs_out, on the controlsState clock (nearest send, no interpolation)
    jn = np.clip(np.searchsorted(t_e4, t_cs), 0, len(t_e4) - 1)
    jp = np.clip(jn - 1, 0, len(t_e4) - 1)
    pick = np.where(np.abs(t_e4[jn] - t_cs) < np.abs(t_e4[jp] - t_cs), jn, jp)
    E = e4[pick]
    m = act & (np.abs(cs_out) > 0.02)
    best = (0, 0.0)
    for s in range(-4, 5):                        # E[i+s] vs cs_out[i]
        idx = np.arange(len(cs_out))
        j = idx + s
        v = m & (j >= 0) & (j < len(E))
        a, b = E[np.clip(j, 0, len(E) - 1)][v], cs_out[v]
        if v.sum() < 500:
            continue
        c = float(np.corrcoef(a, b)[0, 1])
        if abs(c) > abs(best[1]):
            best = (s, c)
    res[rk] = dict(group=V.ROUTES[rk]["group"], n=int(len(te)),
                   g0=q(g0), g1=q(g1), g1_mean=float(g1.mean()), g1_sd=float(g1.std()),
                   cst_dt=q(dcst), xc_lag_frames=best[0], xc_corr=best[1])
    print(f"{rk} {V.ROUTES[rk]['group']:6s} n={len(te):6d}  carState dt median {np.median(dcst):.2f} ms\n"
          f"   g0 same-cycle carState -> 0xE4 : {np.median(g0):6.2f} ms [{np.percentile(g0,5):.2f},{np.percentile(g0,95):.2f}]\n"
          f"   g1 = D_ctl (one cycle earlier) : {np.median(g1):6.2f} ms [{np.percentile(g1,5):.2f},{np.percentile(g1,95):.2f}]"
          f"  mean {g1.mean():.2f} sd {g1.std():.2f}\n"
          f"   xcorr lag e4 vs cs_out         : {best[0]:+d} frames, corr {best[1]:+.4f}", flush=True)
    del D

for grp, rks in (("V293 torque", TORQUE), ("V282", V282)):
    med = np.array([res[r]["g1"][1] for r in rks])
    rng = np.random.default_rng(3)
    bs = [np.mean(rng.choice(med, len(med))) for _ in range(5000)]
    print(f"\n{grp} D_ctl per route {np.round(med,2).tolist()} ms -> mean {med.mean():.2f}, "
          f"route-cluster 95% CI [{np.percentile(bs,2.5):.2f},{np.percentile(bs,97.5):.2f}]")
    res[grp] = dict(per_route=med.tolist(), mean=float(med.mean()),
                    ci=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
(HERE / "chain2.json").write_text(json.dumps(res, indent=1))
