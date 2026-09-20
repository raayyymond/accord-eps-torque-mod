"""(1) D_ctl and (2) sendcan -> on-bus, by exact value propagation through the message chain.

Chain per 10 ms cycle, each link established by EXACT value identity, not by timing:
  0x14A batch  --(angle equal)-->  carState  --(actualLateralAccel responds to the angle step)-->  controlsState
  controlsState.output == carControl.actuators.torque (float identity)
  carControl.torque == carOutput.actuatorsOutput.torque (float identity; carOutput logs the PREVIOUS send)
  carOutput.torqueOutputCan == sendcan 0xE4 STEER_TORQUE
  sendcan 0xE4 5-byte payload (incl. counter + checksum) == 0xE4 TX echo src 129 in the can stream
Usage: python chain_software.py <counter--hash> [...]
"""
import sys, json
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent


def lagtest_index(t_a, t_b, va, vb, Ls, tol=0.0):
    """for each b, pair with the L-th most recent a (a strictly before b); fraction of exact equality."""
    j = np.searchsorted(t_a, t_b, side="left") - 1
    out = {}
    for L in Ls:
        jj = j - L
        ok = (jj >= 0) & (jj < len(t_a))
        eq = np.abs(va[jj[ok]] - vb[ok]) <= tol
        out[L] = (float(eq.mean()) if ok.sum() else np.nan, int(ok.sum()))
    return out


def analyse(route):
    D = dict(np.load(HERE / "cache" / f"{route}.npz"))
    R = {"route": route}
    cs_t, ct_t, cc_t, co_t, sc_t = D["cs_t"], D["ct_t"], D["cc_t"], D["co_t"], D["sc_t"]
    # --- carState <- 0x14A: which batch's angle does carState carry?
    j = np.searchsorted(D["f14_t"], cs_t, side="right") - 1
    res = {}
    for L in (0, 1, 2):
        jj = j - L
        ok = jj >= 1
        ch = np.zeros(len(jj), bool)
        ch[ok] = np.abs(D["ang14"][jj[ok]] - D["ang14"][jj[ok] - 1]) > 0.05
        eq = np.abs(D["cs_ang"][ok & ch] - D["ang14"][jj[ok & ch]]) < 0.051
        res[L] = float(eq.mean())
    R["carState_carries_0x14A_batch_lag"] = res
    dtb = cs_t - D["f14_t"][np.clip(j, 0, None)]
    R["carState_minus_its_can_batch_ms"] = np.percentile(dtb * 1e3, [5, 25, 50, 75, 95]).round(2).tolist()
    # --- controlsState <- carState: first differences of actualLateralAccel vs steeringAngle
    jc = np.searchsorted(cs_t, ct_t, side="right") - 1
    act = np.where(D["ct_active"] > 0, D["ct_act"], np.nan)
    dact = np.diff(act, prepend=np.nan)
    res = {}
    for L in (0, 1, 2):
        jj = jc - L
        ok = jj >= 1
        dang = np.full(len(jj), np.nan)
        dang[ok] = D["cs_ang"][jj[ok]] - D["cs_ang"][jj[ok] - 1]
        m = ok & np.isfinite(dact) & (np.abs(dang) > 0.05) & (np.abs(dact) > 1e-6)
        s = np.sign(dact[m]) * np.sign(dang[m])
        res[L] = dict(n=int(m.sum()), sign_agree=float(np.mean(s)) if m.sum() else np.nan,
                      corr=float(np.corrcoef(dact[m], dang[m])[0, 1]) if m.sum() > 10 else np.nan)
    R["controlsState_consumes_carState_lag"] = res
    R["controlsState_minus_carState_ms"] = np.percentile((ct_t - cs_t[np.clip(jc, 0, None)]) * 1e3, [5, 25, 50, 75, 95]).round(2).tolist()
    # --- carControl.torque == nearest controlsState.output
    jct = np.clip(np.searchsorted(ct_t, cc_t, side="left"), 0, len(ct_t) - 1)
    jprev = np.clip(jct - 1, 0, None)
    jn = np.where(np.abs(ct_t[jprev] - cc_t) < np.abs(ct_t[jct] - cc_t), jprev, jct)
    nz = np.abs(D["cc_tq"]) > 1e-4
    R["carControl_torque_eq_nearest_controlsState_output"] = float(np.mean(D["cc_tq"][nz] == D["ct_out"][jn[nz]]))
    R["carControl_minus_controlsState_ms"] = np.percentile((cc_t - ct_t[jn]) * 1e3, [5, 50, 95]).round(2).tolist()
    # --- carOutput.torque == L-th most recent carControl.torque
    chg = np.abs(np.diff(D["co_tq"], prepend=0)) > 1e-4
    co_sel = chg & (np.abs(D["co_tq"]) > 1e-4)
    r = lagtest_index(cc_t, co_t[co_sel], D["cc_tq"], D["co_tq"][co_sel], range(0, 4))
    R["carOutput_torque_eq_Lth_recent_carControl"] = {k: round(v[0], 4) for k, v in r.items()}
    # --- sendcan cmd == L-th NEXT carOutput torqueOutputCan
    jn2 = np.searchsorted(co_t, sc_t, side="right")
    res = {}
    chs = np.abs(np.diff(D["sc_cmd"], prepend=0)) > 0
    for L in (0, 1, 2):
        jj = jn2 + L
        ok = (jj < len(co_t)) & chs
        res[L] = float(np.mean(D["co_can"][jj[ok]] == D["sc_cmd"][ok]))
    R["sendcan_eq_Lth_next_carOutput_can"] = res
    Lco = max(res, key=res.get)
    Lcc = max(R["carOutput_torque_eq_Lth_recent_carControl"], key=R["carOutput_torque_eq_Lth_recent_carControl"].get)
    jco = jn2 + Lco
    okc = jco < len(co_t)
    jcc = np.full(len(sc_t), -1)
    jcc[okc] = np.searchsorted(cc_t, co_t[jco[okc]], side="left") - 1 - Lcc
    ok = okc & (jcc >= 0)
    ident = np.zeros(len(sc_t), bool)
    ident[ok] = (D["co_can"][jco[ok]] == D["sc_cmd"][ok]) & (D["cc_tq"][jcc[ok]] == D["co_tq"][jco[ok]])
    jct2 = np.full(len(sc_t), -1)
    jct2[ok] = jn[jcc[ok]]
    best = max(R["controlsState_consumes_carState_lag"].items(),
               key=lambda kv: abs(kv[1]["sign_agree"]) if np.isfinite(kv[1]["sign_agree"]) else -9)
    Lcs = best[0]
    jcs = np.full(len(sc_t), -1)
    jcs[ok] = np.searchsorted(cs_t, ct_t[jct2[ok]], side="right") - 1 - Lcs
    L14 = max(R["carState_carries_0x14A_batch_lag"], key=R["carState_carries_0x14A_batch_lag"].get)
    j14 = np.full(len(sc_t), -1)
    g = ok & (jcs >= 0)
    j14[g] = np.searchsorted(D["f14_t"], cs_t[jcs[g]], side="right") - 1 - L14
    # --- echo match by full 5-byte payload
    fe_t, fe_raw = D["fe4_t"], D["fe4_raw"]
    echo_t = np.full(len(sc_t), np.nan)
    echo_bi = np.full(len(sc_t), -1)
    je = np.searchsorted(fe_t, sc_t - 0.0005, side="left")
    for i in range(len(sc_t)):
        k = je[i]
        while k < len(fe_t) and fe_t[k] < sc_t[i] + 0.08:
            if fe_raw[k] == D["sc_raw"][i]:
                echo_t[i] = fe_t[k]
                echo_bi[i] = D["fe4_bi"][k]
                break
            k += 1
    press = np.zeros(len(sc_t), bool)
    press[g] = D["cs_press"][jcs[g]] > 0
    v = np.full(len(sc_t), np.nan)
    v[g] = D["cs_v"][jcs[g]]
    m = ident & g & (D["sc_req"] > 0) & ~press & (j14 >= 0) & np.isfinite(echo_t)
    R["n_sendcan"] = int(len(sc_t))
    R["n_engaged_handsoff_identity"] = int(m.sum())
    R["identity_rate_engaged"] = float(ident[(D["sc_req"] > 0)].mean())
    R["echo_found_rate_engaged"] = float(np.isfinite(echo_t[(D["sc_req"] > 0)]).mean())
    dctl = (sc_t - cs_t[np.clip(jcs, 0, None)]) * 1e3
    d14 = (sc_t - D["f14_t"][np.clip(j14, 0, None)]) * 1e3
    decho = (echo_t - sc_t) * 1e3
    pct = lambda x: np.percentile(x, [5, 25, 50, 75, 95]).round(2).tolist()
    R["D_ctl_carState_to_sendcan_ms_pct"] = pct(dctl[m])
    R["D_ctl_mean"] = float(dctl[m].mean())
    R["batch14_to_sendcan_ms_pct"] = pct(d14[m])
    R["batch14_to_sendcan_mean"] = float(d14[m].mean())
    R["sendcan_to_echo_batch_ms_pct"] = pct(decho[m])
    R["sendcan_to_echo_mean"] = float(decho[m].mean())
    # batches between the send and its echo (1 = the very next can batch)
    nb = np.searchsorted(D["cb_t"], sc_t, side="right")        # index of first batch after the send
    R["echo_batch_offset_hist"] = {int(k): int(c) for k, c in zip(*np.unique((echo_bi - nb)[m], return_counts=True))}
    jcs_send = np.searchsorted(cs_t, sc_t, side="right") - 1
    R["carState_loops_stale_hist"] = {int(k): int(c) for k, c in zip(*np.unique((jcs_send - jcs)[m], return_counts=True))}
    bins = {"<8": v < 8, "8-15": (v >= 8) & (v < 15), ">=15": v >= 15}
    R["by_speed"] = {k: dict(n=int((m & b).sum()),
                             D_ctl_mean=float(dctl[m & b].mean()) if (m & b).sum() else None,
                             batch14_to_send_mean=float(d14[m & b].mean()) if (m & b).sum() else None,
                             send_to_echo_mean=float(decho[m & b].mean()) if (m & b).sum() else None)
                     for k, b in bins.items()}
    sgn = np.sign(D["sc_cmd"])
    stepi = np.where(m & (np.abs(np.diff(D["sc_cmd"], prepend=0)) > 60))[0]
    flips = np.where(m & (sgn * np.roll(sgn, 1) < 0))[0]
    t0 = cs_t[0]
    ex = []
    for i in list(stepi[:3]) + list(flips[:3]):
        ex.append(dict(sendcan_t=round(sc_t[i] - t0, 4), cmd=int(D["sc_cmd"][i]), prev_cmd=int(D["sc_cmd"][i - 1]),
                       carOutput_t=round(co_t[jco[i]] - t0, 4), co_can=int(D["co_can"][jco[i]]),
                       carControl_t=round(cc_t[jcc[i]] - t0, 4), cc_tq=float(D["cc_tq"][jcc[i]]),
                       controlsState_t=round(ct_t[jct2[i]] - t0, 4), ct_out=float(D["ct_out"][jct2[i]]),
                       carState_t=round(cs_t[jcs[i]] - t0, 4), cs_ang=float(D["cs_ang"][jcs[i]]),
                       batch14_t=round(D["f14_t"][j14[i]] - t0, 4), ang14=float(D["ang14"][j14[i]]),
                       echo_t=round(echo_t[i] - t0, 4)))
    R["n_steps_gt60"] = int(len(stepi))
    R["n_sign_flips"] = int(len(flips))
    R["traced_examples_steps_and_flips"] = ex
    np.savez_compressed(HERE / "cache" / f"{route}_chain.npz", sc_t=sc_t, sc_cmd=D["sc_cmd"], echo_t=echo_t,
                        cs_used_t=np.where(jcs >= 0, cs_t[np.clip(jcs, 0, None)], np.nan),
                        b14_used_t=np.where(j14 >= 0, D["f14_t"][np.clip(j14, 0, None)], np.nan), mask=m, v=v)
    return R


if __name__ == "__main__":
    for r in sys.argv[1:]:
        R = analyse(r)
        (HERE / "out").mkdir(exist_ok=True)
        json.dump(R, open(HERE / "out" / f"chain_{r}.json", "w"), indent=1, default=float)
        print(json.dumps(R, indent=1, default=float))
