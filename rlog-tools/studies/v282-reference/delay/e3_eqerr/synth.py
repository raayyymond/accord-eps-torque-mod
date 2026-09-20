"""POSITIVE CONTROL. Synthetic plant J*acc = u(t-D) - b*rate - k(v)*angle - F*sgn(rate) (Coulomb with stiction),
driven by the ACTUAL logged 0xE4 command of a torque route (ZOH from each sendcan logMonoTime), integrated at 1 ms,
sampled at the real carState logMonoTimes with angle quantised to 0.1 deg and rate to 1 deg/s. The same masks
(engaged, hands-off) and the same estimator (eqlib) are then run on it.
Closed-loop variant: u_sent = u_logged - Kfb * rate_meas(carState before last), i.e. a rate feedback on the synthetic
plant's own quantised measurement with the measured D_ctl chain (command uses the PREVIOUS carState).
usage: python synth.py <route> [out.json]
"""
import sys, json, math, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eqlib as E

CACHE = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v282ref"


def simulate(t_u, u, t_cs, v_cs, D, J, b, F, kfb=0.0, t0=None, t1=None, seed=0, tau=0.0):
    dt = 1e-3
    t0 = max(t_u[0], t_cs[0]) if t0 is None else t0
    t1 = min(t_u[-1], t_cs[-1]) if t1 is None else t1
    nsteps = int((t1 - t0) / dt)
    ang = 0.0; rate = 0.0; ulag = 0.0
    iu = 0; ic = np.searchsorted(t_cs, t0)
    nC = len(t_cs)
    meas_a = np.full(nC, np.nan); meas_r = np.full(nC, np.nan)
    u_sent = u.copy()
    # command application queue: the value active at time t is u_sent[last send with t_u <= t - D]
    ia = np.searchsorted(t_u, t0 - D) - 1
    last_meas = [0.0, 0.0]          # two most recent quantised rate samples
    isend = np.searchsorted(t_u, t0)
    k_v = E.kmap(v_cs)
    kk = k_v[min(ic, nC - 1)]
    for s in range(nsteps):
        t = t0 + s * dt
        # sends happening now (closed-loop modification uses the carState BEFORE the latest one)
        while isend < len(t_u) and t_u[isend] <= t:
            if kfb != 0.0:
                u_sent[isend] = u[isend] - kfb * last_meas[0]
            isend += 1
        while ia + 1 < len(t_u) and t_u[ia + 1] <= t - D:
            ia += 1
        ua_cmd = u_sent[ia] if ia >= 0 else 0.0
        if tau > 0.0:
            ulag += (ua_cmd - ulag) * dt / (tau + dt)
            ua = ulag
        else:
            ua = ua_cmd
        net = ua - kk * ang
        if rate == 0.0:
            if abs(net) > F:
                acc = (net - math.copysign(F, net)) / J
                rate = acc * dt
        else:
            acc = (net - b * rate - math.copysign(F, rate)) / J
            nr = rate + acc * dt
            if nr * rate < 0.0:
                nr = 0.0
            rate = nr
        ang += rate * dt
        while ic < nC and t_cs[ic] <= t:
            meas_a[ic] = round(ang / 0.1) * 0.1
            meas_r[ic] = float(round(rate))
            last_meas = [last_meas[1], meas_r[ic]]
            kk = k_v[ic]
            ic += 1
    return meas_a, meas_r, u_sent


def fit_bins(t_cs, a, r, v, mask, t_u, u, variant="rate", band=(0.3, 6.0)):
    blocks, _ = E.accumulate(t_cs, a, r, v, mask, t_u, u, band=band, variant=variant)
    res = {}
    for bi in range(len(E.BINS)):
        bl = [b for b in blocks if b["bin"] == bi]
        if len(bl) < 3:
            continue
        ssr, th, n = E.solve(bl)
        d, k = E.argmin_sub(ssr)
        res[bi] = dict(D=d, n=n, th=th[k].tolist())
    allb = E.solve(blocks); d, k = E.argmin_sub(allb[0])
    res["all"] = dict(D=d, n=allb[2], th=allb[1][k].tolist())
    return res


if __name__ == "__main__":
    route = sys.argv[1]
    Z = np.load(f"{CACHE}/{route}.npz")
    t_u = Z["t_e4"]; u = -Z["e4_cmd"] / 4089.0
    t_cs = Z["t_cst"]; v = Z["vego"]; press = Z["spress"] > 0.5
    act = (np.interp(t_cs, Z["t_cs"], Z["cs_active"]) > 0.5) & (np.interp(t_cs, Z["t_cc"], Z["lat_active"]) > 0.5)
    mask = act & ~press
    # restrict the simulation to the span that contains engaged data (saves time)
    rr = E.runs(mask, t_cs)
    t0 = t_cs[rr[0][0]] - 5.0; t1 = t_cs[rr[-1][1] - 1] + 1.0
    out = {}
    cases = [(D, J, b, F, kfb) for D in (0.030, 0.060) for (J, b, F) in ((8e-5, 0.003, 0.02), (1e-3, 0.003, 0.02)) for kfb in (0.0, 1e-3)]
    if len(sys.argv) > 3:
        cases = cases[:int(sys.argv[3])]
    for D, J, b, F, kfb in cases:
        a, r, us = simulate(t_u, u, t_cs, v, D, J, b, F, kfb=kfb, t0=t0, t1=t1)
        m = mask & np.isfinite(a)
        key = f"D{int(D*1e3)}_J{J:g}_b{b:g}_F{F:g}_kfb{kfb:g}"
        out[key] = {}
        for variant in ("rate", "angle"):
            out[key][variant] = fit_bins(t_cs, np.nan_to_num(a), np.nan_to_num(r), v, m, t_u, us, variant=variant)
        print(key, {vv: {str(kb): round(x["D"], 1) for kb, x in out[key][vv].items()} for vv in out[key]}, flush=True)
        print("   params(all, rate variant) J b ks F c:", np.round(out[key]["rate"]["all"]["th"], 6), flush=True)
    json.dump(out, open(sys.argv[2] if len(sys.argv) > 2 else f"synth_{route}.json", "w"), indent=1)
