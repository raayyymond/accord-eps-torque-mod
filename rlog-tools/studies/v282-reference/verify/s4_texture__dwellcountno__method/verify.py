"""Independent re-derivation of the dj_per100deg / jump_p90 / stall / conc numbers in
finding dwell-count-not-a-separator-jumps-bigger, straight from the s4_texture npz caches,
NOT via s4_events.py's boot_ratio() or s4_compare.py's matched_effect(). Simple pooled
ratios (no route-cluster bootstrap machinery reused) as a sanity cross-check on the point
estimates, plus checks on estimator/window/sign issues per the METHOD lens.
"""
import sys, json
import numpy as np

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

D_DIR = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture/data'
GROUPS = ['V282', 'V282old', 'T64', 'T64B', 'T5', 'T4']
routes = {g: [rk for rk, m in V.ROUTES.items() if m['group'] == g] for g in GROUPS}


def load(rk):
    D = np.load(f'{D_DIR}/{rk}.npz', allow_pickle=True)
    keys = [str(k) for k in D['keys']]
    c = {k: D['rows'][:, i] for i, k in enumerate(keys)}
    return dict(c=c, DJ=D['DJ'])


def dj_rate(R, s0, s1):
    """Simple pooled: total DJ events in speed band / total travel (deg)/100, POOLING ALL ROUTES TOGETHER
    (not weighting by route) -- a different aggregation than the per-route-then-bootstrap approach, as a
    cross-check that the answer isn't an artifact of the weighting scheme."""
    n = 0; travel = 0.0
    per_route = {}
    for rk, d in R.items():
        DJ = d['DJ']; c = d['c']
        m = (DJ[:, 0] >= s0) & (DJ[:, 0] < s1) if len(DJ) else np.array([], bool)
        nn = int(m.sum())
        mt = (c['v'] >= s0) & (c['v'] < s1)
        tt = float(c['travel'][mt].sum())
        n += nn; travel += tt
        per_route[rk] = (nn / (tt / 100.0)) if tt > 0 else np.nan
    return (n / (travel / 100.0) if travel > 0 else np.nan), n, travel, per_route


def jump_p90(R, s0, s1):
    J = []
    for rk, d in R.items():
        DJ = d['DJ']
        if len(DJ) == 0:
            continue
        m = (DJ[:, 0] >= s0) & (DJ[:, 0] < s1)
        J.append(DJ[m, 3])
    J = np.concatenate(J) if J else np.array([])
    return (float(np.percentile(J, 90)) if len(J) else np.nan), len(J)


def stall_pooled(R, sel):
    """Pooled stall fraction (block-average weighted by mv_frames), NOT the matched-cell approach --
    a cruder but independent cross-check of direction and rough magnitude."""
    num = 0.0; den = 0.0
    for rk, d in R.items():
        c = d['c']
        s = sel(c)
        w = c['mv_frames'][s]
        st = c['stall'][s]
        ok = np.isfinite(st) & (w >= 50)
        num += float(np.sum(st[ok] * w[ok])); den += float(np.sum(w[ok]))
    return num / den if den > 0 else np.nan


def conc_pooled(R, sel):
    vals = []
    for rk, d in R.items():
        c = d['c']
        s = sel(c)
        vals.append(c['conc'][s])
    v = np.concatenate(vals)
    v = v[np.isfinite(v)]
    return float(np.median(v)), len(v)


def main():
    R = {g: {rk: load(rk) for rk in routes[g]} for g in GROUPS}

    print("=== dj_per100deg (simple pooled, unweighted-by-route cross-check) ===")
    for (s0, s1) in [(0, 15), (15, 40), (0, 8)]:
        print(f"-- band {s0}-{s1} m/s")
        for g in GROUPS:
            est, n, travel, per = dj_rate(R[g], s0, s1)
            jp90, njp = jump_p90(R[g], s0, s1)
            print(f"  {g:8s} rate={est:6.3f} n={n:4d} travel_deg={travel:8.1f}  jump_p90={jp90:6.3f} (n={njp})  per_route={ {k: round(x,3) for k,x in per.items()} }")

    print()
    print("=== stall fraction, pooled by mv_frames weight (all speeds, no cell matching) ===")
    for g in GROUPS:
        sall = stall_pooled(R[g], lambda c: np.ones(len(c['v']), bool))
        slt15 = stall_pooled(R[g], lambda c: c['v'] < 15)
        print(f"  {g:8s} stall_all={sall:.4f}  stall_lt15={slt15:.4f}")

    print()
    print("=== travel concentration (median block conc, pooled, no cell matching) ===")
    for g in GROUPS:
        m_all, n_all = conc_pooled(R[g], lambda c: np.ones(len(c['v']), bool))
        m_lt15, n_lt15 = conc_pooled(R[g], lambda c: c['v'] < 15)
        print(f"  {g:8s} conc_all={m_all:.4f} (n={n_all})  conc_lt15={m_lt15:.4f} (n={n_lt15})")

    print()
    print("=== sanity: mode_rms (2-2.7Hz band) ratio vs V282, matched roughly by speed band only ===")
    for g in GROUPS:
        for (s0, s1) in [(0, 15), (15, 40)]:
            def med(gg):
                vals = []
                for rk, d in R[gg].items():
                    c = d['c']; s = (c['v'] >= s0) & (c['v'] < s1)
                    vals.append(c['mode_rms'][s])
                v = np.concatenate(vals); v = v[np.isfinite(v)]
                return float(np.median(v)) if len(v) else np.nan
            mv = med('V282'); mg = med(g)
            print(f"  {g:8s} band {s0}-{s1}: mode_rms median={mg:.4f} vs V282={mv:.4f}  ratio={mg/mv if mv else float('nan'):.3f}")

    # ---- estimator sanity checks (METHOD lens) ----
    print()
    print("=== estimator sanity ===")
    print("FS =", V.FS, " (expect 100.0)")
    D0 = np.load(f'{D_DIR}/{routes["V282"][0]}.npz', allow_pickle=True)
    keys = [str(k) for k in D0['keys']]
    print("block row keys:", keys)
    DJ0 = D0['DJ']
    print("DJ columns (v, |sa|, dwell_s, jump, pre, rate_after, act):", DJ0.shape, "dtype", DJ0.dtype)
    print("dwell_s range:", DJ0[:,2].min(), DJ0[:,2].max(), " (min should be >= 0.12 s = 12/100)")
    print("jump(col3) vs recompute-from-nothing not possible without raw sa/sr here (that's inside s4_extract, "
          "already checked against the source loop logic by inspection: jump = |sa[j+30]-sa[j]|, 0.3s after dwell end).")


if __name__ == '__main__':
    main()
