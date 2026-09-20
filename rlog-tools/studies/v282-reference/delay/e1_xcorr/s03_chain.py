"""D_ctl from the message chain, identified BY VALUE (not by assumed ordering):
  0x14A CAN batch -> carState          : carState.steeringAngleDeg == -0.1 * int16(0x14A b0..1) of which batch
  carState -> controlsState            : controlsState.curvature is computed from CS.steeringAngleDeg; which carState
                                         (latest-before vs one-older) explains d(curvature) best, by regression R^2
  controlsState -> carControl          : actuators.torque == torqueState.output (same cycle)
  carControl -> sendcan 0xE4           : int16 == round(-4089 * actuators.torque) of which carControl
  sendcan -> TX echo (can src 129)     : first echo batch carrying the same int16
D_ctl = t(sendcan) - t(carState that the command was computed from).
usage: python s03_chain.py
"""
import json
import numpy as np
import xc_lib as X

ROUTES = X.TORQUE_ROUTES + X.V282_ROUTES
SC = 4089.0
res = {}


def latest_before(t_ref, t_q, strict=True):
    return np.searchsorted(t_ref, t_q, side="left" if strict else "right") - 1


for route in ROUTES:
    D = dict(np.load(X.HERE / "_cache" / f"{route}_chain.npz"))
    r = {}
    # --- 1. carState <- 0x14A batch
    ib = latest_before(D["t14a"], D["tcst"])
    ok = ib >= 1
    m0 = np.isclose(D["sa"][ok], -0.1 * D["a14a"][ib[ok]], atol=0.051)
    m1 = np.isclose(D["sa"][ok], -0.1 * D["a14a"][ib[ok] - 1], atol=0.051)
    moving = D["a14a"][ib[ok]] != D["a14a"][ib[ok] - 1]
    r["cst_from_latest_batch_frac_moving"] = float(m0[moving].mean())
    r["cst_from_older_batch_frac_moving"] = float(m1[moving].mean())
    lat_b = D["tcst"][ok] - D["t14a"][ib[ok]]
    r["batch_to_carState_ms_p5_50_95"] = [float(x) for x in np.percentile(lat_b, [5, 50, 95]) * 1e3]
    # --- 2. controlsState <- carState (curvature vs angle), use differences so the offset/roll drop out
    ic = latest_before(D["tcst"], D["tcs"])
    good = (ic >= 3) & (ic < len(D["tcst"]))
    tcs = D["tcs"][good]; ic = ic[good]; curv = D["curv"][good]
    dcurv = np.diff(curv)
    fits = {}
    for off in [0, 1, 2]:
        ang = D["sa"][ic - off]; vv = D["v"][ic - off]
        dang = np.diff(ang)
        s = (np.abs(dcurv) > 0) & (vv[1:] > 3)
        # curvature ~ -angle/(sR*L*(1+K v^2)); locally linear: regress dcurv on dang
        a_, b_ = dang[s], dcurv[s]
        g = np.dot(a_, b_) / np.dot(a_, a_)
        r2 = 1 - np.sum((b_ - g * a_) ** 2) / np.sum((b_ - b_.mean()) ** 2)
        fits[off] = float(r2)
    r["controlsState_curv_vs_carState_R2_by_offset(0=latest-before)"] = fits
    best_off = max(fits, key=fits.get)
    lag_cs = tcs - D["tcst"][ic - best_off]
    r["carState_to_controlsState_ms_p5_50_95"] = [float(x) for x in np.percentile(lag_cs, [5, 50, 95]) * 1e3]
    # --- 3. carControl <- controlsState, same cycle
    icc = latest_before(D["tcs"], D["tcc"] + 0.002)   # cc published ~0.2 ms after cs of the same cycle
    gg = icc >= 0
    act = D["act"][icc[gg]] > 0.5
    r["cc_torque_eq_cs_output_frac_active"] = float(np.isclose(D["tq"][gg][act], D["out"][icc[gg]][act], atol=1e-6).mean())
    r["controlsState_to_carControl_ms_median"] = float(np.median(D["tcc"][gg] - D["tcs"][icc[gg]]) * 1e3)
    # --- 4. sendcan <- carControl by value
    j0 = latest_before(D["tcc"], D["tsc"])
    s_ok = (j0 >= 2)
    tsc = D["tsc"][s_ok]; vsc = D["vsc"][s_ok]; j0 = j0[s_ok]
    nz = (vsc != 0) & (D["lat"][j0] > 0.5)
    matches = {}
    for off in [0, 1]:
        pred = np.round(-SC * D["tq"][j0 - off])
        matches[off] = float(np.mean(np.abs(pred[nz] - vsc[nz]) <= 1))
    r["sendcan_eq_carControl_frac(0=latest-before,1=one older)"] = matches
    # changing commands only (where the two candidates differ by > 2 LSB)
    diff_ = np.abs(np.round(-SC * D["tq"][j0]) - np.round(-SC * D["tq"][j0 - 1])) > 2
    mm = nz & diff_
    r["sendcan_eq_carControl_frac_when_candidates_differ"] = {
        off: float(np.mean(np.abs(np.round(-SC * D["tq"][j0 - off])[mm] - vsc[mm]) <= 1)) for off in [0, 1]}
    r["n_sendcan_nonzero"] = int(nz.sum())
    # --- 5. D_ctl: sendcan <- carControl(j0) <- controlsState <- carState
    icc2 = latest_before(D["tcs"], D["tcc"][j0] + 0.002)
    ics = latest_before(D["tcst"], D["tcs"][icc2]) - best_off
    dctl = (tsc - D["tcst"][ics]) * 1e3
    ib2 = latest_before(D["t14a"], D["tcst"][ics])
    dctl_can = (tsc - D["t14a"][ib2]) * 1e3
    v_at = D["v"][ics]; pr = D["pr"][ics] > 0.5
    use = nz & ~pr
    r["D_ctl_ms_all_p5_50_95_mean"] = [float(x) for x in np.percentile(dctl[use], [5, 50, 95])] + [float(dctl[use].mean())]
    r["D_ctl_from_CANbatch_ms_p5_50_95"] = [float(x) for x in np.percentile(dctl_can[use], [5, 50, 95])]
    for (lo, hi), bn in zip(X.SPEED_BINS, X.BIN_NAMES):
        sb = use & (v_at >= lo) & (v_at < hi)
        if sb.sum() > 50:
            r[f"D_ctl_ms_bin{bn}_p5_50_95_mean_n"] = [float(x) for x in np.percentile(dctl[sb], [5, 50, 95])] + \
                [float(dctl[sb].mean()), int(sb.sum())]
    # command cycles dropped / repeated: sendcan with the same carControl as the previous sendcan
    r["frac_sendcan_reusing_previous_carControl"] = float(np.mean(np.diff(j0)[nz[1:]] == 0))
    # --- 6. TX echo
    ie = np.searchsorted(D["tech"], tsc, side="left")
    ie = np.clip(ie, 0, len(D["tech"]) - 1)
    ech = []
    for k in np.where(nz)[0][::5]:
        e = ie[k]
        for q in range(e, min(e + 4, len(D["tech"]))):
            if D["vech"][q] == vsc[k]:
                ech.append(D["tech"][q] - tsc[k]); break
    ech = np.array(ech) * 1e3
    r["sendcan_to_echo_batch_ms_p5_50_95"] = [float(x) for x in np.percentile(ech, [5, 50, 95])] if len(ech) else None
    res[route] = r
    print(route, json.dumps(r, indent=1), flush=True)
    del D

json.dump(res, open(X.HERE / "out" / "chain_summary.json", "w"), indent=1)
