# -*- coding: utf-8 -*-
r"""m4_episodes.py -- M4: the STALL-SURGE ("ratchet in motion") census on every route, the fork's O1 override relay,
the worst-10 episode table, and the mechanism coincidence tests (1, 4, 5, 7) on route 79 (V298).

    python m4_episodes.py         (~5 s; needs m4_dwell.py's json for the dwell-then-jump events)

STALL-SURGE (route-agnostic, on the 0x18F rate only, so V298 and V282/V294 compare like for like):
  mbar = 0.5 s centred mean of w18 (deg/s); TURNING frames |mbar| >= 10 deg/s (engaged);  u = w18 * sign(mbar);
  f3 = 30 ms centred mean of u.  A STALL = >= 2 consecutive turning frames with f3 < 0.25 |mbar|, followed within
  0.25 s by a SURGE f3 > 0.75 |mbar|.  Depth = 1 - min(f3)/|mbar|.  Per minute of TURNING time, per speed band.
  The existing dwell instruments cannot see these: a stall lasts 20-60 ms, under their 100-200 ms minimum dwell.
O1 RELAY (route 79): the fork's driver-override O1 (honda/carcontroller.py _update_angle: |steeringTorque| > 600 on,
  <= 500 off; setpoint := theta + 0.06 * rate) reconstructed from source by m4_common.limiter_reconstruct, which
  reproduces the published carOutput steeringAngleDeg on 99.994 % of latActive frames (EVIDENCE).
"""
from __future__ import annotations

import json

import numpy as np
from scipy import signal

import m4_common as C

DEPTH_LO, DEPTH_HI, TURN_MIN = 0.25, 0.75, 10.0


def mov(x, n):
    return np.convolve(x, np.ones(n) / n, "same")


def stall_surge(G, mask):
    w = G["w18"]
    mbar = mov(w, 50)
    turn = mask & (np.abs(mbar) >= TURN_MIN)
    u = w * np.sign(mbar)
    f3 = mov(u, 3)
    stall = turn & (f3 < DEPTH_LO * np.abs(mbar))
    surge = turn & (f3 > DEPTH_HI * np.abs(mbar))
    R = C.runs(stall, 2)
    # next surge frame after each stall run end (vectorised via a "next True index" array)
    nxt = np.full(len(w) + 1, len(w), np.int64)
    idx = np.flatnonzero(surge)
    nxt_idx = np.searchsorted(idx, R[:, 1])
    ns = np.where(nxt_idx < len(idx), idx[np.minimum(nxt_idx, len(idx) - 1)], len(w))
    ok = (ns - R[:, 1]) <= 25
    # the stall must also be PRECEDED by motion (f3 > 0.75 |mbar| within 0.25 s before) -> a stall inside a turn
    prv_idx = np.searchsorted(idx, R[:, 0]) - 1
    ps = np.where(prv_idx >= 0, idx[np.maximum(prv_idx, 0)], -10 ** 9)
    ok &= (R[:, 0] - ps) <= 25
    R = R[ok]
    ns = ns[ok]
    depth = np.array([1.0 - f3[a:b].min() / abs(mbar[a:b]).mean() for a, b in R]) if len(R) else np.zeros(0)
    return dict(R=R, surge=ns, depth=depth, turn=turn, mbar=mbar, f3=f3)


def per_band(G, ss, extra=None):
    out = {}
    v = G["vego"]
    for nm, lo, hi in C.SYM_BANDS:
        tb = ss["turn"] & (v >= lo) & (v < hi)
        secs = tb.sum() / C.FS
        sel = (v[ss["R"][:, 0]] >= lo) & (v[ss["R"][:, 0]] < hi) if len(ss["R"]) else np.zeros(0, bool)
        n = int(sel.sum())
        out[nm] = dict(turn_s=float(secs), n=n, per_min=float(60 * n / secs) if secs > 5 else np.nan,
                       depth_p50=float(np.median(ss["depth"][sel])) if n else np.nan)
    return out


def trains(G, ss, gap_lo=0.08, gap_hi=0.40, nmin=3):
    """RATCHET TRAINS: >= nmin consecutive stall-surge events whose stall starts are 0.08-0.40 s apart (a periodic
    2.5-12 Hz stall-surge cycle), per minute of turning time and as a share of turning time, per band."""
    R = ss["R"]
    v = G["vego"]
    out = {}
    if len(R) < nmin:
        tr = []
    else:
        g = np.diff(R[:, 0]) / C.FS
        okg = (g >= gap_lo) & (g <= gap_hi)
        tr = [(R[a, 0], R[b, 1]) for a, b in C.runs(okg, nmin - 1)]
    for nm, lo, hi in C.SYM_BANDS:
        tb = ss["turn"] & (v >= lo) & (v < hi)
        secs = tb.sum() / C.FS
        sel = [(a, b) for a, b in tr if lo <= v[a] < hi]
        out[nm] = dict(n=len(sel), per_min=float(60 * len(sel) / secs) if secs > 5 else np.nan,
                       share=float(sum(b - a for a, b in sel) / max(tb.sum(), 1)) if secs > 5 else np.nan,
                       freq_p50=float(np.median([1.0 / (np.median(np.diff(ss["R"][(ss["R"][:, 0] >= a) & (ss["R"][:, 0] <= b), 0])) / C.FS)
                                                 for a, b in sel])) if sel else np.nan)
    return out, tr


def rate_spectrum_in_turn(G, mask, nper=128):
    """PSD of u = w18*sign(mbar) - mbar (the in-turn rate modulation) over turning runs >= 1.28 s; 2-10 Hz."""
    w = G["w18"]
    mbar = mov(w, 50)
    turn = mask & (np.abs(mbar) >= TURN_MIN)
    segs = C.runs(turn, nper)
    win = np.hanning(nper)
    P = []
    for a, b in segs:
        x = (w[a:b] - mbar[a:b]) * np.sign(mbar[a:b])
        for s in range(0, len(x) - nper + 1, nper // 2):
            q = x[s:s + nper] - x[s:s + nper].mean()
            P.append(np.abs(np.fft.rfft(q * win)) ** 2)
    if len(P) < 4:
        return None
    f = np.fft.rfftfreq(nper, 1 / C.FS)
    Pm = np.mean(P, 0) / ((win ** 2).sum() * C.FS) * 2
    b = (f >= 2) & (f <= 10)
    fpk = float(f[b][np.argmax(Pm[b])])
    return dict(n=len(P), fpk=fpk, rms_2_10=float(np.sqrt(Pm[b].sum() * (f[1] - f[0]))),
                rms_4_8=float(np.sqrt(Pm[(f >= 4) & (f <= 8)].sum() * (f[1] - f[0]))))


def o1_relay(G, F, L):
    t = L["t"]
    ovr, lat = L["ovr"], L["lat"]
    R = C.runs(ovr, 1)
    d = R[:, 1] - R[:, 0]
    v = L["v"]
    press = np.r_[False, F["cs_press"][:-1].astype(bool)]
    # setpoint step at O1 onset and at release (fork axis, deg)
    co = L["co"]
    on_step = co[R[:, 0]] - co[R[:, 0] - 1]
    err_before = co[R[:, 0] - 1] - L["th"][R[:, 0] - 1]
    rel_step = co[np.minimum(R[:, 1], len(co) - 1)] - co[R[:, 1] - 1]
    # inertial + friction prediction of the hands-off bar (fit on |bar| < 450 engaged frames of the grid)
    w = G["w18"]
    a = np.gradient(signal.sosfiltfilt(signal.butter(2, 8, fs=C.FS, output="sos"), w)) * C.FS
    m = G["eng"] & (np.abs(G["bar"]) < 450)
    X = np.c_[a, w, np.sign(w), np.ones(len(w))]
    beta = np.linalg.lstsq(X[m], G["bar"][m] / 1.024, rcond=None)[0]   # in cs_tq counts
    pred = np.abs(X @ beta)
    gi = np.clip(np.searchsorted(G["t"], t) - 1, 0, len(G["t"]) - 1)
    pk_tq = np.array([L["tq"][x:y].max() for x, y in R])
    pk_pred = np.array([pred[gi[max(x - 2, 0)]:gi[min(y + 1, len(gi) - 1)] + 1].max() for x, y in R])
    # clusters: >= 3 O1 episodes with gaps < 0.5 s
    cl, i = [], 0
    while i < len(R):
        j = i
        while j + 1 < len(R) and R[j + 1, 0] - R[j, 1] < 50:
            j += 1
        if j - i + 1 >= 3:
            cl.append((i, j))
        i = j + 1
    periods = np.concatenate([np.diff(R[i:j + 1, 0]) for i, j in cl]) / C.FS if cl else np.zeros(0)
    bands = {}
    for nm, lo, hi in C.SYM_BANDS:
        mb = lat & (v >= lo) & (v < hi)
        secs = mb.sum() / C.FS
        sel = (v[R[:, 0]] >= lo) & (v[R[:, 0]] < hi)
        bands[nm] = dict(lat_s=float(secs), ovr_frac=float(np.mean(ovr[mb])) if mb.any() else np.nan,
                         onsets_per_min=float(60 * sel.sum() / secs) if secs > 5 else np.nan,
                         short_frac=float(np.mean(d[sel] <= 5)) if sel.any() else np.nan)
    short = d <= 5
    return dict(n=len(R), n_short=int(short.sum()), bands=bands, n_clusters=len(cl),
                cluster_s=float(sum((R[j, 1] - R[i, 0]) for i, j in cl) / C.FS),
                period_p25_50_75=np.percentile(periods, [25, 50, 75]).tolist() if len(periods) else None,
                onset_step_abs_p50_90=np.percentile(np.abs(on_step), [50, 90]).tolist(),
                onset_step_toward_wheel=float(np.mean(np.sign(on_step) == -np.sign(err_before))),
                err_before_abs_p50_90=np.percentile(np.abs(err_before), [50, 90]).tolist(),
                release_step_abs_p50_90=np.percentile(np.abs(rel_step), [50, 90]).tolist(),
                short_pk_tq_p50_90=np.percentile(pk_tq[short], [50, 90]).tolist(),
                short_pred_inertial_p50_90=np.percentile(pk_pred[short], [50, 90]).tolist(),
                short_pressed_frac=float(np.mean([press[x:y].any() for x, y in R[short]])),
                long_pressed_frac=float(np.mean([press[x:y].any() for x, y in R[d > 50]])) if (d > 50).any() else None,
                bar_fit_beta=beta.tolist(), clusters=[(float(t[R[i, 0]]), float(t[R[j, 1]]), int(j - i + 1),
                                                       float(v[R[i, 0]])) for i, j in cl], R=R)


def freeze_states(G):
    """the V298 cave's integrator-freeze predicates on the wire (BELIEF: tq4f68 ~ |bar|, tq4f60 ~ -bar -- the
    drive-read's own reading, angle_loop_drive_read 'gp-0x4f60 ~= -bar')."""
    bar, err = G["bar"], G["err"]
    hard = np.abs(bar) > 512
    opp = (np.abs(bar) > 300) & (np.sign(-bar) != np.sign(err)) & (err != 0)
    return hard | opp, hard, opp


def coincidence(G, L, win_ev, base_mask, rng_seed=7):
    """for a list of (i0, i1) grid windows: fraction carrying each candidate's marker, and the same fraction over
    random windows of the same lengths drawn from base_mask (the base rate)."""
    t = G["t"]
    stg = C.zoh(L["t"], L["stage"], t, fill=0)
    frz, hard, opp = freeze_states(G)
    frz_tog = np.r_[False, frz[1:] != frz[:-1]]
    req = G["req"]
    reqd = np.r_[False, req[1:] != req[:-1]]
    st = G.get("status", np.zeros(len(t)))
    b4 = G.get("b4", np.full(len(t), 7.0))
    lowv = G["vego"] < 8.0
    markers = dict(o1=(stg == 3), rate_lim=(stg == 1), err_clip=(stg == 4), freeze_toggle=frz_tog,
                   req_change=reqd, status_bad=(np.nan_to_num(st) != 0), b4_bad=((np.nan_to_num(b4).astype(int) & 7) != 7),
                   low_speed=lowv)
    cum = {k: np.r_[0, np.cumsum(m.astype(int))] for k, m in markers.items()}

    def frac(wins):
        if not len(wins):
            return {k: np.nan for k in markers}
        a = np.clip(wins[:, 0], 0, len(t)); b = np.clip(wins[:, 1], 0, len(t))
        return {k: float(np.mean((c[b] - c[a]) > 0)) for k, c in cum.items()}
    W = np.asarray(win_ev, int).reshape(-1, 2)
    ev = frac(W)
    rng = np.random.default_rng(rng_seed)
    cand = np.flatnonzero(base_mask)
    if len(cand) and len(W):
        st0 = rng.choice(cand, size=min(4000, 20 * len(W)))
        L_ = rng.choice(W[:, 1] - W[:, 0], size=len(st0))
        base = frac(np.c_[st0, st0 + L_])
    else:
        base = {k: np.nan for k in markers}
    return dict(n=len(W), ev=ev, base=base)


def main():
    tm = C.timer()
    F = C.fork_cache()
    L = C.limiter_reconstruct(F)
    D = json.load(open(C.OUT / "m4_dwell.json"))
    res = dict(stall={}, spec={})
    SS = {}
    for tag in (C.TAG79,) + C.REFS:
        G = C.build_grid(tag)
        ss = stall_surge(G, G["eng"])
        SS[tag] = (G, ss)
        res["stall"][tag] = per_band(G, ss)
        res["spec"][tag] = {nm: rate_spectrum_in_turn(G, G["eng"] & (G["vego"] >= lo) & (G["vego"] < hi))
                            for nm, lo, hi in C.SYM_BANDS}
        res.setdefault("trains", {})[tag], _ = trains(G, ss)
    G, ss = SS[C.TAG79]
    t = G["t"]
    stg = C.zoh(L["t"], L["stage"], t, fill=0)
    O1 = o1_relay(G, F, L)
    R_o1 = O1.pop("R")
    res["o1"] = O1
    # stall-surge on r79 split by O1 involvement (O1 active within the stall .. surge window +- 30 ms)
    Rs, ns = ss["R"], ss["surge"]
    win = np.c_[Rs[:, 0] - 3, np.minimum(ns + 4, len(t))]
    cum_o1 = np.r_[0, np.cumsum(stg == 3)]
    with_o1 = (cum_o1[win[:, 1]] - cum_o1[win[:, 0]]) > 0
    v = G["vego"]
    res["stall_o1"] = {nm: dict(n=int(np.sum((v[Rs[:, 0]] >= lo) & (v[Rs[:, 0]] < hi))),
                                frac_o1=float(np.mean(with_o1[(v[Rs[:, 0]] >= lo) & (v[Rs[:, 0]] < hi)]))
                                if np.any((v[Rs[:, 0]] >= lo) & (v[Rs[:, 0]] < hi)) else np.nan)
                       for nm, lo, hi in C.SYM_BANDS}
    # O1-free turning time: stall rate when no O1 within +-0.5 s
    o1_near = mov((stg == 3).astype(float), 101) > 0
    tb = ss["turn"] & ~o1_near
    n_free = np.sum(~with_o1 & ~o1_near[Rs[:, 0]])
    res["stall_without_o1_per_min"] = float(60 * n_free / max(tb.sum() / C.FS, 1e-9))
    res["stall_with_o1_per_min_of_o1_turn"] = float(60 * np.sum(with_o1) / max((ss["turn"] & o1_near).sum() / C.FS, 1e-9))
    # in-turn rate modulation on r79 split by O1 within 0.5 s (the record's ratchet band 4-8 Hz)
    res["spec_r79_o1split"] = {}
    for nm, lo, hi in C.SYM_BANDS[:3]:
        mb = G["eng"] & (v >= lo) & (v < hi)
        res["spec_r79_o1split"][nm] = dict(o1_near=rate_spectrum_in_turn(G, mb & o1_near),
                                           o1_free=rate_spectrum_in_turn(G, mb & ~o1_near))
    _, tr79 = trains(G, ss)
    cum_o1b = np.r_[0, np.cumsum(stg == 3)]
    res["trains_r79_o1"] = float(np.mean([(cum_o1b[b] - cum_o1b[a]) > 0 for a, b in tr79])) if tr79 else np.nan
    res["trains_r79_list"] = [(float(t[a]), float((b - a) / C.FS), float(v[a])) for a, b in tr79]
    # ORDER test (separates the relay from plain stick-slip): for every stall, the time since the last O1 frame and the
    # setpoint error at the stall start; and how many stalls fall inside a ratchet train
    o1f = np.flatnonzero(stg == 3)
    k = np.searchsorted(o1f, Rs[:, 0]) - 1
    dt_o1 = np.where(k >= 0, (Rs[:, 0] - o1f[np.maximum(k, 0)]) / C.FS, np.inf)
    e_st = np.abs(G["err"][Rs[:, 0]])
    after = dt_o1 <= 0.15
    intrain = np.zeros(len(Rs), bool)
    for a_, b_ in tr79:
        intrain |= (Rs[:, 0] >= a_) & (Rs[:, 0] <= b_)
    res["order"] = dict(n=int(len(Rs)), frac_after_o1_150ms=float(np.mean(after)),
                        frac_after_o1_150ms_in_trains=float(np.mean(after[intrain])) if intrain.any() else np.nan,
                        n_in_trains=int(intrain.sum()),
                        err_at_stall_after_o1_p50_90=np.percentile(e_st[after], [50, 90]).tolist() if after.any() else None,
                        err_at_stall_no_o1_p50_90=np.percentile(e_st[~after], [50, 90]).tolist() if (~after).any() else None,
                        dt_o1_p50_in_trains=float(np.median(dt_o1[intrain])) if intrain.any() else np.nan)
    tf = np.flatnonzero(ss["turn"])
    kk = np.searchsorted(o1f, tf) - 1
    res["order"]["base_after_o1_150ms_turning"] = float(np.mean(np.where(kk >= 0, (tf - o1f[np.maximum(kk, 0)]) / C.FS, np.inf) <= 0.15))
    for nm, lo, hi in C.SYM_BANDS[:3]:
        sb = (v[Rs[:, 0]] >= lo) & (v[Rs[:, 0]] < hi)
        tb_ = tf[(v[tf] >= lo) & (v[tf] < hi)]
        kb = np.searchsorted(o1f, tb_) - 1
        res["order"]["band_" + nm] = (float(np.mean(after[sb])) if sb.any() else np.nan,
                                      float(np.mean(np.where(kb >= 0, (tb_ - o1f[np.maximum(kb, 0)]) / C.FS, np.inf) <= 0.15)) if len(tb_) else np.nan)
    # ---- coincidence tests
    base_turn = ss["turn"]
    res["coinc_stall"] = coincidence(G, L, win, base_turn)
    ev_a = D[C.TAG79]["events_a"]
    W_a = np.array([[e["i_dw0"], e["i_end"] + 1] for e in ev_a])
    res["coinc_dwelljump"] = coincidence(G, L, W_a, G["eng"])
    # dwell-then-jump: breakaway error vs the predicted P dead zone (drive-read Fc / c_P per band)
    res["dj_err_end"] = [float(G["err"][e["i_dw1"] - 1]) for e in ev_a]
    res["eng_err_median"] = float(np.median(G["err"][G["eng"] & (stg != 3)]))
    # ---- worst-10 table: merge stall-surge events into episodes (gap < 1 s), rank by cycles; add dwell-jumps
    eps = []
    if len(Rs):
        g0 = 0
        for k in range(1, len(Rs) + 1):
            if k == len(Rs) or Rs[k, 0] - Rs[k - 1, 1] > 100:
                a, b = Rs[g0, 0], ns[k - 1]
                eps.append(dict(kind="stall-surge", i0=int(a), i1=int(b), cycles=int(k - g0),
                                depth=float(np.max(ss["depth"][g0:k]))))
                g0 = k
    for e in ev_a:
        eps.append(dict(kind="dwell-jump", i0=int(e["i_dw0"]), i1=int(e["i_end"]), cycles=1, depth=float(e["jump"])))
    eps.append(dict(kind="R3* 3.85 Hz", i0=int(np.searchsorted(t, 1089.41)), i1=int(np.searchsorted(t, 1090.46)),
                    cycles=4, depth=np.nan))
    frz, hard, opp = freeze_states(G)
    rows = []
    for e in eps:
        a, b = e["i0"], max(e["i1"], e["i0"] + 1)
        sl = slice(a, b + 1)
        rows.append(dict(kind=e["kind"], t=float(t[a]), dur=float((b - a) / C.FS), cycles=e["cycles"],
                         depth_or_jump=e["depth"], v=float(v[a]), th0=float(G["theta"][a]), th1=float(G["theta"][b]),
                         rate_absmax=float(np.max(np.abs(G["w18"][sl]))), rate_min_abs=float(np.min(np.abs(G["w18"][sl]))),
                         err_absmax=float(np.max(np.abs(G["err"][sl]))), err_mean=float(np.mean(G["err"][sl])),
                         tap_min=float(np.min(G["tap"][sl])), tap_max=float(np.max(G["tap"][sl])),
                         bar_absmax=float(np.max(np.abs(G["bar"][sl]))), req_min=int(G["req"][sl].min()),
                         status=sorted(set(np.nan_to_num(G["status"][sl]).astype(int).tolist())),
                         b4_07=sorted(set((np.nan_to_num(G["b4"][sl]).astype(int) & 7).tolist())),
                         o1=float(np.mean(stg[sl] == 3)), ratelim=float(np.mean(stg[sl] == 1)),
                         errclip=float(np.mean(stg[sl] == 4)), freeze=float(np.mean(frz[sl])),
                         pressed=float(np.nanmean(G["pressed"][sl]))))
    ss_rows = sorted([r for r in rows if r["kind"] == "stall-surge"], key=lambda r: (-r["cycles"], -r["depth_or_jump"]))
    dj_rows = sorted([r for r in rows if r["kind"] == "dwell-jump"], key=lambda r: -r["depth_or_jump"])
    r3 = [r for r in rows if r["kind"].startswith("R3")]
    res["worst10"] = ss_rows[:6] + dj_rows[:3] + r3
    res["n_stall_episodes"] = len(ss_rows)
    res["wall_s"] = tm()
    with open(C.OUT / "m4_episodes.json", "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    # ---- print
    print("M4 EPISODES  (wall %.1f s)" % res["wall_s"])
    print("STALL-SURGE per min of turning time (|0.5 s mean rate| >= 10 deg/s) [n, turn_s, depth p50]")
    for tag in (C.TAG79,) + C.REFS:
        print("  %-10s %s" % (tag[:10], {k: (round(x["per_min"], 2), x["n"], round(x["turn_s"]), round(x["depth_p50"], 2) if x["n"] else None)
                                       for k, x in res["stall"][tag].items()}))
    print("  r79 stall-surge with O1 in window, by band:", {k: (x["n"], round(x["frac_o1"], 2)) for k, x in res["stall_o1"].items()})
    print("  r79 stall-surge /min, turning time with NO O1 within 0.5 s: %.2f ; per min of turning time WITH O1 near: %.2f" % (
        res["stall_without_o1_per_min"], res["stall_with_o1_per_min_of_o1_turn"]))
    print("IN-TURN RATE MODULATION spectrum (2-10 Hz peak, rms 2-10, rms 4-8 deg/s)")
    for tag in (C.TAG79,) + C.REFS:
        print("  %-10s %s" % (tag[:10], {k: (None if x is None else (x["n"], x["fpk"], round(x["rms_2_10"], 2), round(x["rms_4_8"], 2)))
                                       for k, x in res["spec"][tag].items()}))
    print("RATCHET TRAINS (>= 3 stall-surges, 0.08-0.40 s apart) per min of turning [n, per_min, share of turning time, freq p50]")
    for tag in (C.TAG79,) + C.REFS:
        print("  %-10s %s" % (tag[:10], {k: (x["n"], round(x["per_min"], 2), round(x["share"], 3), round(x["freq_p50"], 1))
                                       for k, x in res["trains"][tag].items()}))
    print("  r79 trains with O1 inside: %.2f ; list (t, dur, v): %s" % (res["trains_r79_o1"],
          [(round(a, 1), round(b, 2), round(c, 1)) for a, b, c in res["trains_r79_list"]]))
    print("  r79 in-turn modulation split by O1 within 0.5 s:", {k: {kk: (None if vv is None else (vv["n"], round(vv["rms_2_10"], 2), round(vv["rms_4_8"], 2))) for kk, vv in x.items()} for k, x in res["spec_r79_o1split"].items()})
    od = res["order"]
    print("ORDER: stalls %d; started <= 0.15 s after an O1 frame %.2f (in trains %.2f, n %d, dt p50 %.3f s); |err| at stall start: after-O1 p50/90 %s, no-O1 %s" % (
        od["n"], od["frac_after_o1_150ms"], od["frac_after_o1_150ms_in_trains"], od["n_in_trains"], od["dt_o1_p50_in_trains"],
        None if od["err_at_stall_after_o1_p50_90"] is None else np.round(od["err_at_stall_after_o1_p50_90"], 2),
        None if od["err_at_stall_no_o1_p50_90"] is None else np.round(od["err_at_stall_no_o1_p50_90"], 2)))
    print("   base rate (turning frames with an O1 frame in the previous 0.15 s): %.2f ; by band (stalls, base): %s" % (
        od["base_after_o1_150ms_turning"], {k[5:]: tuple(round(x, 2) for x in v_) for k, v_ in od.items() if k.startswith("band_")}))
    o = res["o1"]
    print("O1 RELAY: episodes %d (short <= 5 fr: %d), clusters %d (%.1f s), onset-onset period p25/50/75 %s s" % (
        o["n"], o["n_short"], o["n_clusters"], o["cluster_s"], np.round(o["period_p25_50_75"], 3)))
    print("   by band:", {k: (round(x["ovr_frac"], 3), round(x["onsets_per_min"], 1), round(x["short_frac"], 2)) for k, x in o["bands"].items()})
    print("   onset step |d setpoint| p50/p90 %s deg (toward the wheel %.2f); error before onset p50/p90 %s; release step %s" % (
        np.round(o["onset_step_abs_p50_90"], 2), o["onset_step_toward_wheel"], np.round(o["err_before_abs_p50_90"], 2),
        np.round(o["release_step_abs_p50_90"], 2)))
    print("   short episodes: peak |steeringTorque| p50/p90 %s, hands-off inertia+friction fit predicts %s, pressed %.2f; long pressed %s" % (
        np.round(o["short_pk_tq_p50_90"]), np.round(o["short_pred_inertial_p50_90"]), o["short_pressed_frac"], o["long_pressed_frac"]))
    print("   bar fit (cs_tq counts) = %.3f*alpha + %.3f*w + %.1f*sgn(w) + %.1f" % tuple(o["bar_fit_beta"]))
    for k in ("coinc_stall", "coinc_dwelljump"):
        c = res[k]
        print("COINCIDENCE %s n %d:" % (k, c["n"]), {m: (round(c["ev"][m], 2), round(c["base"][m], 2)) for m in c["ev"]})
    print("dwell-jump err at dwell end:", np.round(res["dj_err_end"], 2), " engaged median err %.2f" % res["eng_err_median"])
    print("WORST EPISODES")
    for r in res["worst10"]:
        print("  %-12s t %7.2f dur %4.2f cyc %2d d/j %5.2f v %4.1f th %6.1f->%6.1f |w|max %5.1f min %4.1f |err|max %5.1f tap %5.0f..%5.0f |bar| %5.0f req %d st %s b4 %s O1 %.2f RL %.2f EC %.2f frz %.2f prs %.2f" % (
            r["kind"], r["t"], r["dur"], r["cycles"], r["depth_or_jump"], r["v"], r["th0"], r["th1"], r["rate_absmax"],
            r["rate_min_abs"], r["err_absmax"], r["tap_min"], r["tap_max"], r["bar_absmax"], r["req_min"], r["status"],
            r["b4_07"], r["o1"], r["ratelim"], r["errclip"], r["freeze"], r["pressed"]))
    print("wall %.1f s" % tm())


if __name__ == "__main__":
    main()
