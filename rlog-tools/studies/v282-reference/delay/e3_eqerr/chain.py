"""D_ctl: measured carState sample -> the 0xE4 command computed from it leaves (sendcan logMonoTime).

Method (EVIDENCE):
  1. EXACT VALUE MATCH sendcan 0xE4 -> controlsState.  The Honda carcontroller writes
     apply_torque = round(-MAX * output) so e4_cmd[j] == round(K * cs_out[i]) for the controlsState
     that produced it.  K is fitted from the data, then the integer sequence of e4 is matched against
     the integer sequence of round(K*cs_out) at every shift; the shift with the highest exact-match
     rate gives an unambiguous index pairing (and its timestamp difference is D(cs -> sendcan)).
  2. controlsState -> the carState it consumed: controlsd is triggered by carState, so the carState
     immediately PRECEDING each controlsState publish is the one it used.  Verified by the jitter of
     that gap being small and one-sided.
  3. Cycle accounting against card.py's step():  state_update() calls sm.update(0) BEFORE carState is
     published, and controls_update() then actuates self.sm['carControl'] -- i.e. the carControl
     computed from the PREVIOUS carState.  Counted here as the number of carState publishes strictly
     between the consumed carState and the sendcan.

usage: python e3_chain.py
out:   delay/e3_eqerr/chain.json + stdout
"""
import sys, json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V

OUT = HERE
OUT.mkdir(parents=True, exist_ok=True)

TORQUE = ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
          "00000076--d0b7ea7e4d", "00000075--6c8687d5bd"]
V282 = ["0000006c--2bc842dbac", "00000064--ce6b0b0ebb"]


def fit_K(e4, out):
    """Scale between controlsState torqueState.output and the 0xE4 integer, from the coarse-aligned overlap."""
    n = min(len(e4), len(out))
    a, b = e4[:n], out[:n]
    m = np.abs(b) > 0.05
    if m.sum() < 50:
        return np.nan
    return float(np.sum(a[m] * b[m]) / np.sum(b[m] * b[m]))


def match(e4, cs_out, K, max_shift=6):
    """Best integer shift s such that e4[j] == round(K*cs_out[j - s]) most often. Returns (s, rate)."""
    q = np.round(K * cs_out).astype(np.int64)
    p = np.round(e4).astype(np.int64)
    best = (0, -1.0)
    for s in range(-max_shift, max_shift + 1):
        # pair p[j] with q[j - s]
        if s >= 0:
            a, b = p[s:], q[: len(q) - s] if s else q
        else:
            a, b = p[: len(p) + s], q[-s:]
        n = min(len(a), len(b))
        if n < 200:
            continue
        a, b = a[:n], b[:n]
        nz = np.abs(b) > 3               # ignore the huge run of identical zeros (disengaged)
        if nz.sum() < 200:
            continue
        r = float(np.mean(a[nz] == b[nz]))
        if r > best[1]:
            best = (s, r)
    return best


def main():
    res = {}
    for rk in TORQUE + V282:
        D = np.load(V.CACHE / f"{rk}.npz", allow_pickle=True)
        t_cs, cs_out = D["t_cs"], D["cs_out"]
        t_e4, e4 = D["t_e4"], D["e4_cmd"]
        t_cst = D["t_cst"]
        act = D["cs_active"] > 0.5

        # --- step 1: value-match.  Both streams are 100 Hz but can start/stop at different points, so
        # align coarsely on the first engaged frame, then search the residual integer shift.
        K = fit_K(np.interp(t_cs, t_e4, e4), cs_out)
        # resample e4 onto the controlsState index by NEAREST send (no interpolation -- integers)
        j_near = np.searchsorted(t_e4, t_cs)
        j_near = np.clip(j_near, 0, len(t_e4) - 1)
        j_prev = np.clip(j_near - 1, 0, len(t_e4) - 1)
        pick = np.where(np.abs(t_e4[j_near] - t_cs) < np.abs(t_e4[j_prev] - t_cs), j_near, j_prev)
        e4_on_cs = e4[pick]
        s, rate = match(e4_on_cs, cs_out, K)
        # exact pairing: controlsState index i -> sendcan index pick[i + s]
        i = np.arange(len(cs_out) - max(s, 0) - max(-s, 0))
        ii = i + max(-s, 0)
        jj = pick[np.clip(ii + s, 0, len(pick) - 1)]
        ok = act[ii] & (np.abs(cs_out[ii]) > 0.02)
        ok &= np.round(e4[jj]) == np.round(K * cs_out[ii])
        d_cs_e4 = (t_e4[jj[ok]] - t_cs[ii[ok]]) * 1e3

        # --- step 2: the carState each controlsState consumed = the one immediately preceding it
        m = np.searchsorted(t_cst, t_cs[ii[ok]]) - 1
        good = m >= 0
        d_cst_cs = (t_cs[ii[ok]][good] - t_cst[m[good]]) * 1e3
        d_ctl = (t_e4[jj[ok]][good] - t_cst[m[good]]) * 1e3

        # --- step 3: how many carState publishes fall strictly between the consumed carState and the send
        n_between = np.searchsorted(t_cst, t_e4[jj[ok]][good], side="left") - 1 - m[good]

        q = lambda x: [float(np.percentile(x, p)) for p in (5, 50, 95)]
        res[rk] = dict(group=V.ROUTES[rk]["group"], K=K, shift=s, match_rate=rate,
                       n=int(ok.sum()), d_cs_e4=q(d_cs_e4), d_cst_cs=q(d_cst_cs), d_ctl=q(d_ctl),
                       d_ctl_mean=float(np.mean(d_ctl)), d_ctl_sd=float(np.std(d_ctl)),
                       cycles_between=[float(np.percentile(n_between, p)) for p in (5, 50, 95)],
                       frac_between_ge1=float(np.mean(n_between >= 1)))
        print(f"{rk} {V.ROUTES[rk]['group']:6s} K={K:8.1f} shift={s:+d} match={rate*100:5.1f}%  n={int(ok.sum()):6d}\n"
              f"   carState->controlsState {d_cst_cs[1] if False else np.median(d_cst_cs):5.2f} ms "
              f"[{np.percentile(d_cst_cs,5):.2f},{np.percentile(d_cst_cs,95):.2f}]\n"
              f"   controlsState->0xE4     {np.median(d_cs_e4):5.2f} ms "
              f"[{np.percentile(d_cs_e4,5):.2f},{np.percentile(d_cs_e4,95):.2f}]\n"
              f"   D_ctl (cst->0xE4)       {np.median(d_ctl):5.2f} ms "
              f"[{np.percentile(d_ctl,5):.2f},{np.percentile(d_ctl,95):.2f}]  "
              f"mean {np.mean(d_ctl):.2f} sd {np.std(d_ctl):.2f}\n"
              f"   carState publishes strictly between consumed cst and the send: "
              f"median {np.median(n_between):.0f}, frac>=1 {np.mean(n_between>=1)*100:.1f}%", flush=True)
        del D

    # route-cluster CI on the median
    for grp, rks in (("V293 torque", TORQUE), ("V282", V282)):
        med = np.array([np.median(res[r]["d_ctl"][1]) for r in rks])
        rng = np.random.default_rng(3)
        bs = [np.mean(rng.choice(med, len(med))) for _ in range(4000)]
        print(f"\n{grp}: per-route D_ctl medians {np.round(med,2).tolist()} ms  -> mean "
              f"{med.mean():.2f} ms, route-cluster 95% CI [{np.percentile(bs,2.5):.2f},{np.percentile(bs,97.5):.2f}]")
        res[grp] = dict(per_route=med.tolist(), mean=float(med.mean()),
                        ci=[float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))])
    (OUT / "chain.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
