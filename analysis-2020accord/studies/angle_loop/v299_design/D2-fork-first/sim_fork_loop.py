# -*- coding: utf-8 -*-
r"""sim_fork_loop.py -- D2 (FORK-FIRST) CLOSED-LOOP time scenarios: the V298 lane (byte-exact CandLane of the panel-2
COMMON time scorer, unchanged) + the identified r71b plant family (Karnopp stick-slip, 10 kHz) + the FORK'S
_update_angle limiter, O1 gate, release takeover, setpoint lead and 20 Hz model staircase, at 100 Hz.

ANALYSIS ONLY.  Writes _scratch/v299_D2/sim_fork_loop.{txt,json}.  4 scenarios in 4 processes; each process ~4-8 s.

What is NEW here vs score_time.run (and is BELIEF, not identified):
  * the fork model: the limiter of honda/carcontroller.py _update_angle (rate cap, VM jerk + accel, O1 hysteresis,
    error clip, the release restart), with the D2 terms as per-column switches;
  * the hands-off torque WORD gp-0x4f60 = M3's reaction fit (alpha, omega of the plant, 8 Hz) + 8 Hz noise of sd 132 gp
    (the residual sd re-fitted on route 79 by cf_fork_r79.py), so the cave's 300/512 freezes, the fade and the O1 gate
    all see a realistic twist;
  * the fork reads the wheel 3 frames (30 ms) after the plant (the refuters' best time-domain lag +30/+40 ms);
  * a HAND (S4) = a stiff position-holding spring on the plant (Kh 150 T/deg, Bh 8), its word = its torque x 1.0 (scale
    BELIEF; only "above 1200" matters).
Every run uses frame='vgr' like the primary scorer.  Plant member 'nominal' and 'F_hi' (higher Coulomb).
"""
from __future__ import annotations

import json
import math
import sys
import time
from multiprocessing import Pool

import numpy as np

import d2_common as C

SENT = 0x7FFF
ERR_A = (29.0, 24.0, 32.0, 25.0, 8.5, 4.5)
LEAD_B_BP = (3.1, 8.0, 10.0, 11.75, 14.0, 17.5, 22.0, 26.9)
LEAD_B_V = (0.05, 0.10, 0.15, 0.25, 0.32, 0.35, 0.22, 0.10)  # s ~ Tin group delay (gate2_fork 3) + 0.04 - 0.15; >= 0.05
#                                                                 at <= 8 m/s, where the stick (drift) needs the lead

CFG = {
    "V298": dict(cap=1.2, err_v=C.CUR["err_v"], deb=0, hard=600.0, lead_o1=0.06, take=0.0, acc=0.0, plead=0.0, stair=1),
    "A-G8": dict(cap=3.0, err_v=ERR_A, deb=8, hard=1200.0, debh=3, lead_o1=0.0, take=0.4, acc=0.0, plead=0.10, stair=1),
    "A": dict(cap=3.0, err_v=ERR_A, deb=8, hard=1200.0, lead_o1=0.0, take=0.4, acc=0.0, plead=0.10, stair=1),
    "A-nolead": dict(cap=3.0, err_v=ERR_A, deb=8, hard=1200.0, lead_o1=0.0, take=0.4, acc=0.0, plead=0.0, stair=1),
    "A-curclip": dict(cap=3.0, err_v=C.CUR["err_v"], deb=8, hard=1200.0, lead_o1=0.0, take=0.4, acc=0.0, plead=0.10,
                      stair=1),
    "A+hold": dict(cap=3.0, err_v=ERR_A, deb=8, hard=1200.0, offhold=20, lead_o1=0.0, take=0.4, acc=0.0, plead=0.10,
                   stair=1),
    "B": dict(cap=3.0, err_v=ERR_A, deb=8, hard=1200.0, lead_o1=0.0, take=0.4, acc=1500.0, plead=-1.0, stair=0),
}


def lc_amp(v):
    return float(np.degrees(C.STEER_FROM_CURV(1.45 / v ** 2, v)))


def ref_fn(scn, v):
    if scn == "turn90":
        def f(t):
            up = np.clip((t - 0.3) * 320.0, 0, 90.0)
            dn = np.clip((t - 2.3) * 320.0, 0, 90.0)
            return up - dn
        return f, 4.0
    if scn == "lc":
        A = lc_amp(v)

        def f(t):
            x = np.clip((t - 0.5) / 4.0, 0, 1)
            return A * np.sin(2 * np.pi * x) * ((t >= 0.5) & (t <= 4.5))
        return f, 5.5
    if scn == "drift":
        def f(t):
            return np.clip((t - 0.5) * 1.5, 0, 3.75)
        return f, 4.5
    if scn == "release":
        def f(t):
            return np.clip((t - 0.3) * 200.0, 0, 60.0)
        return f, 4.0
    raise KeyError(scn)


SCN_SPEEDS = {"turn90": (3.0, 5.0), "lc": (17.5, 26.9), "drift": (8.0, 15.0), "release": (5.0,)}
MEMBERS = ("nominal", "F_hi")
WORDS = ("none", "twist")


def run_scn(scn):
    ST = C.load_st()
    cand = C.v298_cand(ST)
    cols = [dict(cfg=k, v=v, member=m, word=w) for k in CFG for v in SCN_SPEEDS[scn] for m in MEMBERS for w in WORDS]
    B = len(cols)
    vv = np.array([c["v"] for c in cols])
    P = {key: np.array([CFG[c["cfg"]].get(key, 0.0) for c in cols], float)
         for key in ("cap", "deb", "hard", "debh", "offhold", "confirm", "lead_o1", "take", "acc", "plead", "stair")}
    wsel = np.array([c["word"] == "twist" for c in cols])
    plead = np.where(P["plead"] < 0, np.interp(vv, LEAD_B_BP, LEAD_B_V), P["plead"])
    emax = np.array([np.interp(c["v"], C.CUR["err_bp"], CFG[c["cfg"]]["err_v"]) for c in cols])
    dmax0 = np.minimum(C.vm_dmax_jerk(vv), P["cap"])
    amax = C.vm_amax(vv)
    refs = [ref_fn(scn, c["v"])[0] for c in cols]
    dur = ref_fn(scn, cols[0]["v"])[1]
    lane = ST.CandLane([cand] * B, np.round(vv * 3.6 * 64).astype(np.int64))
    pl = ST.Plant([dict(member=c["member"], v=c["v"]) for c in cols])
    rng = np.random.default_rng(11)
    nT = int(round(dur * 1000))
    # 8 Hz-filtered word noise, sd 132 gp (cf_fork_r79 residual), fixed seed
    from scipy import signal
    sos = signal.butter(2, 8.0, fs=1000.0, output="sos")
    wn = signal.sosfilt(sos, np.random.default_rng(5).normal(0, 1, (nT + 3000, 1)), axis=0)[3000:]
    wn = np.repeat(wn / wn.std() * 132.0, B, axis=1)        # the SAME twist-noise realisation in every column
    # hand (S4)
    hand_on = (lambda t: 0.2 <= t < 2.0) if scn == "release" else (lambda t: False)
    Kh, Bh, th_h = 150.0, 8.0, 20.0
    # state
    held_th = np.zeros(B, np.int64)
    held_x = np.zeros(B, np.int64)
    st = np.zeros(B, np.int64)
    cmd = np.zeros(B, np.int64)
    ramp = np.full(B, 0x8000, np.int64)
    wire, wom, wtq = [], [], []
    prev = np.zeros(B)
    prev_rate = np.zeros(B)
    since = np.full(B, 1e9)
    gate = np.zeros(B, bool)
    rl600 = np.zeros(B)
    rlh = np.zeros(B)
    rloff = np.zeros(B)
    ep_h = np.zeros(B)
    ep_n = np.zeros(B)
    om_f = np.zeros(B)
    al_f = np.zeros(B)
    a1 = math.exp(-2 * math.pi * 8.0 / 1000.0)
    rec = {k: np.zeros((nT, B), np.float32) for k in ("th", "om", "T", "sp", "word", "al")}
    g_rec = np.zeros((nT // 10 + 1, B), bool)
    stg = np.zeros((nT // 10 + 1, B), np.int8)
    frz_n = np.zeros(B)
    run_n = np.zeros(B)
    for n in range(nT):
        t = n * 1e-3
        if n % 10 == 0:
            k = len(wire)
            if k >= 4:
                thm = wire[k - 3] / 10.0
                omm = wom[k - 3]
                tqm = np.abs(wtq[k - 3]) / 1.024
            else:
                thm, omm, tqm = pl.th.copy(), pl.om.copy(), np.zeros(B)
            # O1 gate: hysteresis; set = (run of |tq| > 600 >= deb frames) or |tq| > hard ; reset |tq| <= 500
            rl600 = np.where(tqm > 600.0, rl600 + 1, 0)
            rlh = np.where(tqm > P["hard"], rlh + 1, 0)
            hard_ok = np.where(P["debh"] > 0, rlh >= P["debh"], tqm > P["hard"])
            setg = np.where(P["deb"] > 0, (rl600 >= P["deb"]) | hard_ok, tqm > 600.0)
            rloff = np.where(tqm <= 500.0, rloff + 1, 0)
            confirmed = (ep_h >= 10) | (ep_n >= 30)          # (b): a HAND = >= 100 ms above 1200 or >= 300 ms of O1
            need_hold = (P["offhold"] > 0) & ((P["confirm"] == 0) | confirmed)
            reset = np.where(need_hold, rloff >= P["offhold"], tqm <= 500.0)
            g_new = np.where(setg, True, np.where(reset, False, gate))
            released = gate & ~g_new
            gate = g_new
            ep_h = np.where(gate, ep_h + (tqm > 1200.0), 0)
            ep_n = np.where(gate, ep_n + 1, 0)
            prev = np.where(released, thm, prev)
            prev_rate = np.where(released, 0.0, prev_rate)
            since = np.where(released, 0.0, since)
            tp = t + plead
            tps = np.where(P["stair"] > 0, np.floor(tp / 0.05) * 0.05, tp)
            des = np.array([refs[i](tps[i]) for i in range(B)], float)
            dm = np.where((P["take"] > 0) & (since < P["take"]), dmax0 * since / np.maximum(P["take"], 1e-9), dmax0)
            acc = P["acc"] * 1e-4
            # (b) second-order limiter: the rate toward des is capped by the braking curve sqrt(2 acc |d|), and the rate
            # may change by at most acc per frame (deg/frame^2); (a) = the stock first-order limiter
            dd = des - prev
            rb = np.sign(dd) * np.sqrt(2.0 * acc * np.abs(dd))
            rcmd = np.clip(np.where(acc > 0, rb, dd), -dm, dm)
            rnew = np.where(acc > 0, np.clip(rcmd, prev_rate - acc, prev_rate + acc), rcmd)
            r1 = prev + rnew
            r2 = np.clip(r1, -amax, amax)
            r3 = np.where(gate, thm + omm * P["lead_o1"], r2)
            # takeover: the error clip ramps 0 -> emax with the rate limit over T_take after a release (D2 a/b)
            em = np.where((P["take"] > 0) & (since < P["take"]), emax * since / np.maximum(P["take"], 1e-9), emax)
            r4 = np.clip(np.clip(r3, thm - em, thm + em), -400, 400)
            s_ = np.zeros(B, np.int8)
            s_[np.abs(r1 - des) > 1e-3] = 1
            s_[gate] = 3
            s_[np.abs(r4 - r3) > 1e-3] = 4
            stg[n // 10] = s_
            g_rec[n // 10] = gate
            prev_rate = r4 - prev
            prev = r4
            since = since + 0.01
            raw = np.floor(-10.0 * r4 + 0.5).astype(np.int64)
            cmd = np.clip(-(raw << 2), -0x4000, 0x4000)
        # the torque word: hands-off reaction (+ noise) or the hand's torque
        om_f_new = a1 * om_f + (1 - a1) * pl.om
        al_f = a1 * al_f + (1 - a1) * (om_f_new - om_f) * 1000.0
        om_f = om_f_new
        if hand_on(t):
            word = Kh * (th_h - pl.th) - Bh * pl.om
        else:
            word = np.where(wsel, C.reaction_word(al_f, om_f) + wn[n], 0.0)
        tqv = np.clip(np.round(word), -0x7FFF, 0x7FFF).astype(np.int64)
        om_m = pl.om / ST.FRAME.kappa(pl.th)
        g4f50 = ST.s16(np.round(ST.ABE_PER * om_m + rng.normal(0.0, ST.N4F50, B)).astype(np.int64))
        st = st + (((g4f50 * 1024 - st) * 37) >> 7)
        abe = ST.s16(st >> 10)
        x69 = np.floor(10.0 * ST.FRAME.cinv(pl.th) + 0.5).astype(np.int64)
        T = lane.tick(held_th, x69, held_x, abe, cmd, tqv, ramp, 1, 1)
        frz_n += lane.log["frz"] & lane.log["run"]
        run_n += lane.log["run"]
        q_now = np.floor(10.0 * pl.th + 0.5).astype(np.int64)
        if n % 10 == 4:
            held_th = q_now
            held_x = np.clip(-((ST.s16(st >> 10) * 48 * 1159) >> 15), -12000, 12000)
            wire.append(q_now.copy())
            wom.append(pl.om.copy())
            wtq.append(word.copy() if np.ndim(word) else np.full(B, word))
        Tapp = pl.delay(T.astype(float))
        if hand_on(t):
            pl.step(-Tapp, np.full(B, Kh), np.full(B, Bh), np.full(B, th_h))
        else:
            pl.step(-Tapp)
        rec["th"][n], rec["om"][n], rec["T"][n], rec["sp"][n], rec["word"][n] = pl.th, pl.om, T, cmd / -40.0, word
        rec["al"][n] = al_f
    tt = np.arange(nT) * 1e-3
    ref = np.stack([refs[i](tt) for i in range(B)], 1)
    out = []
    for i, c in enumerate(cols):
        th, om, T, sp = rec["th"][:, i], rec["om"][:, i], rec["T"][:, i], rec["sp"][:, i]
        tap = np.abs(T) / 8.0
        g = g_rec[:, i]
        d = dict(scn=scn, cfg=c["cfg"], v=c["v"], member=c["member"], word=c["word"], tap_pk=float(tap.max()),
                 om_pk=float(np.abs(om).max()), o1_eps=int(np.sum(g[1:] & ~g[:-1])), o1_s=float(g.sum() / 100),
                 frz=float(frz_n[i] / max(run_n[i], 1)), clip_frac=float(np.mean(stg[:, i] == 4)),
                 rate_frac=float(np.mean(stg[:, i] == 1)))
        if scn == "turn90":
            a = int(np.argmax(th >= 81.0)) if (th >= 81.0).any() else -1
            b = int(np.argmax((tt > 2.3) & (th <= 9.0))) if ((tt > 2.3) & (th <= 9.0)).any() else -1
            sosb = signal.butter(2, [1.6, 3.0], btype="band", fs=1000.0, output="sos")
            d.update(r163=float(np.sqrt(np.mean(signal.sosfiltfilt(sosb, om) ** 2))), o1_s=float(g.sum() / 100), t90_in=(a - 300) / 1000 if a >= 0 else None, t90_out=(b - 2300) / 1000 if b >= 0 else None,
                     over=float(th[(tt > 0.3) & (tt < 2.3)].max() - 90.0), under=float(-th[tt > 2.3].min()),
                     om_pk_in=float(om[tt < 2.3].max()), om_pk_out=float(-om[tt > 2.3].min()),
                     word_pk=float(np.abs(rec["word"][:, i]).max()))
        elif scn == "lc":
            A = lc_amp(c["v"])
            e = th - ref[:, i]
            lags = np.arange(0, 600, 5)
            m = (tt > 0.5) & (tt < 5.0)
            cc = [np.dot(th[m], np.roll(ref[:, i], L)[m]) / (np.linalg.norm(th[m]) * np.linalg.norm(np.roll(ref[:, i], L)[m]))
                  for L in lags]
            d.update(A=A, err_pk=float(np.abs(e[m]).max()), gain=float(np.abs(th[m]).max() / A),
                     lag_ms=int(lags[int(np.argmax(cc))]))
        elif scn == "drift":
            m = (tt > 0.5) & (tt < 3.0)
            slow = (np.abs(om) < 0.25) & m
            dd = np.diff(np.r_[0, slow.astype(int), 0])
            sa, sb = np.flatnonzero(dd == 1), np.flatnonzero(dd == -1)
            dw = int(np.sum((sb - sa) >= 200))
            e = th - ref[:, i]
            d.update(dwells=dw, err_max=float(np.abs(e[m]).max()), err_rms=float(np.sqrt(np.mean(e[m] ** 2))),
                     lag_end=float(ref[2999, i] - th[2999]), err_final=float(e[-1]))
        elif scn == "release":
            m = tt >= 2.0
            a = int(np.argmax(m & (th >= 54.0))) if (m & (th >= 54.0)).any() else -1
            d.update(om_rel_pk=float(om[m].max()), over_rel=float(th[m].max() - 60.0),
                     t90_rel=(a - 2000) / 1000 if a >= 0 else None, tap_hold=float(tap[(tt > 1.0) & (tt < 2.0)].mean()),
                     tap_rel_pk=float(tap[m].max()), alpha_rel_pk=float(np.abs(rec["al"][:, i][m]).max()))
        out.append(d)
    return out


def main():
    t0 = time.perf_counter()
    with Pool(4) as p:
        res = p.map(run_scn, ["turn90", "lc", "drift", "release"])
    rows = [r for rr in res for r in rr]
    L = ["sim_fork_loop: V298 lane (CandLane) x r71b plant x fork model; wall %.1f s" % (time.perf_counter() - t0)]
    keys = {"turn90": ("r163", "o1_s", "t90_in", "t90_out", "om_pk_in", "om_pk_out", "over", "under", "tap_pk", "o1_eps", "frz",
                       "clip_frac", "rate_frac", "word_pk"),
            "lc": ("A", "gain", "lag_ms", "err_pk", "tap_pk", "o1_eps", "frz"),
            "drift": ("dwells", "err_max", "err_rms", "lag_end", "err_final", "tap_pk", "o1_eps", "frz"),
            "release": ("om_rel_pk", "over_rel", "t90_rel", "alpha_rel_pk", "tap_hold", "tap_rel_pk", "o1_eps", "frz")}
    for scn, ks in keys.items():
        L.append("\n[%s]  cfg | v | member | %s" % (scn, " | ".join(ks)))
        for r in rows:
            if r["scn"] != scn:
                continue
            vals = []
            for k in ks:
                x = r.get(k)
                vals.append("-" if x is None else (("%.3f" % x) if isinstance(x, float) else str(x)))
            L.append("  %-9s | %4.1f | %-7s | %-5s | %s" % (r["cfg"], r["v"], r["member"], r["word"], " | ".join(vals)))
    txt = "\n".join(L)
    print(txt)
    (C.OUT / "sim_fork_loop.txt").write_text(txt + "\n", encoding="utf-8")
    (C.OUT / "sim_fork_loop.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
