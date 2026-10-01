# -*- coding: utf-8 -*-
r"""e2_data_r71b.py -- DATA FACTS the integral policy rests on, read from route r71b (V294, 00000071--a7b8ba5d9d) via the
kit's cache analysis-2020accord/_scratch/cache/tau/r71b_v294_ident.npz (extract_r71b.py).  ANALYSIS ONLY.

(1) SIGN: carState.steeringTorque (npz 'storque' = -raw 0x18F field; the raw field = -floor(gp-0x4f60*125/128), speed/
    driver-torque trace sec 3.3) vs the steering angle/rate while the DRIVER alone steers (lateral inactive):
    => sign(gp-0x4f60) = sign(carState torque) = the direction the hand pushes in the gp-0x6a00 (= openpilot) frame.
(2) HANDS-OFF BAR REACTION (engaged, steeringPressed false): OLS of carState torque on [1, rate, accel, sign(rate)] per
    speed band, plus the residual quantiles -- the model the sign-aware freeze must not trip on in normal driving.
(3) CURVE SIZES: engaged |a_lat| (= v * yaw rate) and |steering angle| quantiles per goal band, and the largest
    sustained (>= 3 s) |a_lat| -- sizes the turn-hold test from r71b, not from A_TURN.
(4) HANDS-OFF |torque| quantiles by |rate| on r71b (the freeze-duty input), the route-a6 table's twin.
usage: python e2_data_r71b.py   (writes e2_data_r71b_out.txt + _scratch/.../e2_data_r71b.json)"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[4]
SRC = KIT / "analysis-2020accord" / "_scratch" / "cache" / "tau" / "r71b_v294_ident.npz"
OUT = KIT / "_scratch" / "angle_loop" / "E2-integral-most-margin"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    d = np.load(SRC)
    t, v, sa, sr, sp, st = d["t_cst"], d["vego"], d["sa_deg"], d["sr_deg"], d["spress"], d["storque"]
    lat = np.interp(t, d["t_cc"], d["lat_active"]) > 0.5
    yaw = d["cs_yaw"]
    fs = 1.0 / np.median(np.diff(t))
    acc = np.gradient(sr) * fs
    L = [f"# e2_data_r71b: route r71b, {len(t)} carState frames at {fs:.1f} Hz; lateral active {lat.mean():.3f}"]
    raw = np.interp(t, d["t18"], d["tq"])
    L.append(f"(0) npz tq (raw 0x18F field) vs carState torque: slope {np.polyfit(raw, st, 1)[0]:+.4f}, corr "
             f"{np.corrcoef(raw, st)[0, 1]:+.5f}  => carState torque = -raw = +gp-0x4f60*125/128 (trace sec 3.3)")
    out = {}
    # (1) sign
    for lab, m in (("driver alone (lateral inactive, v > 1)", (~lat) & (v > 1)),
                   ("engaged, steeringPressed", lat & (sp > 0.5) & (v > 1)),
                   ("engaged, hands-off", lat & (sp < 0.5) & (v > 1))):
        L.append(f"(1) {lab:40s} n {int(m.sum()):6d}  corr(tq, angle) {np.corrcoef(st[m], sa[m])[0, 1]:+.3f}  "
                 f"corr(tq, rate) {np.corrcoef(st[m], sr[m])[0, 1]:+.3f}  corr(tq, accel) {np.corrcoef(st[m], acc[m])[0, 1]:+.3f}")
    # holding a turn alone: torque sign vs angle sign at |angle| > 10, |rate| < 5
    m = (~lat) & (v > 1) & (np.abs(sa) > 10) & (np.abs(sr) < 5) & (np.abs(st) > 100)
    agree = float(np.mean(np.sign(st[m]) == np.sign(sa[m]))) if m.any() else float("nan")
    L.append(f"(1) driver holding a turn alone (|angle|>10, |rate|<5, |tq|>100): n {int(m.sum())}, "
             f"sign(tq) == sign(angle) in {agree:.3f} of frames")
    out["sign_agree_hold"] = agree
    # (2) bar reaction model, hands-off engaged
    bands = ((1, 5), (5, 8), (8, 15), (15, 22), (22, 40))
    out["bar"] = {}
    for lo, hi in bands:
        m = lat & (sp < 0.5) & (v >= lo) & (v < hi)
        X = np.vstack([np.ones(m.sum()), sr[m], acc[m], np.sign(sr[m])]).T
        b, *_ = np.linalg.lstsq(X, st[m], rcond=None)
        res = st[m] - X @ b
        r2 = 1 - res.var() / st[m].var()
        q = np.percentile(np.abs(res), [50, 90, 95, 99])
        L.append(f"(2) hands-off {lo:2d}-{hi:2d} m/s n {int(m.sum()):6d}: tq = {b[0]:+6.1f} {b[1]:+6.2f}*rate "
                 f"{b[2]:+7.4f}*accel {b[3]:+6.1f}*sgn(rate)  R2 {r2:.3f}; |resid| p50 {q[0]:.0f} p90 {q[1]:.0f} "
                 f"p95 {q[2]:.0f} p99 {q[3]:.0f}; |tq| p50 {np.percentile(np.abs(st[m]), 50):.0f} "
                 f"p95 {np.percentile(np.abs(st[m]), 95):.0f}")
        out["bar"][f"{lo}-{hi}"] = dict(c0=b[0], c_rate=b[1], c_acc=b[2], c_sgn=b[3], r2=r2, resid_q=list(q))
    # (3) curve sizes
    out["curves"] = {}
    alat = v * yaw
    for lo, hi in ((8, 15), (15, 22), (22, 40)):
        m = lat & (v >= lo) & (v < hi)
        qa = np.percentile(np.abs(alat[m]), [50, 90, 95, 99, 99.9])
        qs = np.percentile(np.abs(sa[m]), [50, 90, 95, 99, 99.9])
        # sustained: the largest |a_lat| held (>= 90 % of it) for >= 3 s inside one engaged run in the band
        k = int(round(3.0 * fs))
        a_s = np.abs(alat) * m
        sus = 0.0
        sa_sus = 0.0
        for i in range(0, len(a_s) - k, 10):
            w = a_s[i:i + k]
            if m[i:i + k].all():
                lo_w = w.min()
                if lo_w > sus:
                    sus = float(lo_w)
                    sa_sus = float(np.abs(sa[i:i + k]).min())
        L.append(f"(3) engaged {lo:2d}-{hi:2d} m/s n {int(m.sum()):6d}: |a_lat| p50 {qa[0]:.2f} p90 {qa[1]:.2f} p95 "
                 f"{qa[2]:.2f} p99 {qa[3]:.2f} p99.9 {qa[4]:.2f} m/s2 | |angle| p50 {qs[0]:.1f} p90 {qs[1]:.1f} p95 "
                 f"{qs[2]:.1f} p99 {qs[3]:.1f} p99.9 {qs[4]:.1f} deg | largest 3-s sustained |a_lat| {sus:.2f} m/s2 "
                 f"(|angle| >= {sa_sus:.1f} deg)")
        out["curves"][f"{lo}-{hi}"] = dict(alat_q=list(qa), sa_q=list(qs), sus3=sus, sa_sus3=sa_sus)
    # (4) hands-off |tq| by |rate|
    m0 = lat & (sp < 0.5)
    for lo, hi in ((0, 10), (10, 30), (30, 60), (60, 1000)):
        m = m0 & (np.abs(sr) >= lo) & (np.abs(sr) < hi)
        if m.sum() > 50:
            q = np.percentile(np.abs(st[m]), [50, 90, 95, 99])
            fr = [float(np.mean(np.abs(st[m]) > x)) for x in (64, 128, 256, 512)]
            # the sign-aware freeze fires on an OPPOSING reading: sign(tq) != sign(rate) is the reaction's sign
            opp = [float(np.mean((np.abs(st[m]) > x) & (np.sign(st[m]) != np.sign(sr[m])))) for x in (64, 128, 256, 512)]
            L.append(f"(4) hands-off |rate| {lo:3d}-{hi:4d} deg/s n {int(m.sum()):6d}: |tq| p50 {q[0]:.0f} p90 {q[1]:.0f} "
                     f"p95 {q[2]:.0f} p99 {q[3]:.0f}; frac > 64/128/256/512 " + " ".join(f"{x:.3f}" for x in fr)
                     + "; of which against the motion " + " ".join(f"{x:.3f}" for x in opp))
    txt = "\n".join(L)
    print(txt)
    (HERE / "e2_data_r71b_out.txt").write_text(txt + "\n", encoding="utf-8")
    (OUT / "e2_data_r71b.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
