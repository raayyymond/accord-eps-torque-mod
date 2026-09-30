# -*- coding: utf-8 -*-
"""d2_time.py -- lens "dynamics": the TIME-DOMAIN screen of the lens's candidates on the shared harness.

  (a) mode B (fork in the loop, recorded planner demand), dists full AND lp, plants nominal AND light_b:
      tracking gain, turn-hold, straight delivery, i-share, cmd rms, r_mid (1-3 Hz rate), hard-turn 1.6-3 Hz, J_err,
      the 1-5 Hz limit-cycle line -- every candidate as a DIFFERENCE from V294 in the same batch (sweep_drive).
  (b) delivered HF torque (1 kHz trace) in 5-9 / 9-13 / 13-17 / 17-23 / 23-30 Hz AND 30-120 Hz (the 100 Hz staircase /
      kick ripple), mode A dist full (the recorded command on r71b's road) on nominal, light_b, mode13, mode20, mode20_lo;
      and mode B dist lp on the stress members (the fork's echo loop through a flexible mode).
  (c) lane-only: the staircase triangle at the slew cap; the sensor-noise torque (x white 1.93 counts rms, sp 0, 60 s).
Output: d2_time_out.txt, d2_time.json
"""
import json
import os
import sys
import time

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
sys.path.insert(0, HERE)
import v295_harness as H  # noqa: E402
from d1_linear import lag_cells  # noqa: E402


def band_rms(x, lo, hi, fs=1000.0):
    b, a = signal.butter(2, [lo / (fs / 2), hi / (fs / 2)], btype="band")
    y = signal.filtfilt(b, a, np.asarray(x, float) - np.mean(x))
    cut = int(0.5 * fs)
    return float(np.sqrt(np.mean(y[cut:-cut] ** 2))) if len(y) > 3 * cut else float("nan")


def hf_all(T):
    d = H.hf_content(T)
    d["30-120"] = band_rms(T, 30.0, 120.0)
    return d


def cands():
    b = H.Cells.v294()
    L7, L8, L10, L12 = (lag_cells(b, f) for f in (7.0, 8.0, 10.0, 12.0))
    out = [L7, L8, L10, L12,
           b.replace(kd_y=(256,) * 4, d_clamp=10240, sum_clamp=15240, name="D256"),
           b.replace(kd_y=(512,) * 4, d_clamp=10240, sum_clamp=15240, name="D512"),
           b.replace(fb_a=1014, name="A1014_bheld"),
           b.replace(fb_a=1017, name="A1017_bheld"),
           L8.replace(fb_a=1014, name="L8+A1014"),
           L10.replace(fb_a=1014, name="L10+A1014")]
    return b, out


def main():
    lines = []
    pr = lambda *a: (print(*a, flush=True), lines.append(" ".join(str(x) for x in a)))  # noqa: E731
    base, C = cands()
    J = {}
    chunks = H.route_chunks()
    fam = H.family()
    pr("d2_time -- %d candidates + V294, %d chunks" % (len(C), len(chunks)))

    # ---------------- (a) mode B drive metrics
    t0 = time.time()
    S = H.sweep_drive(C, plants=("nominal", "light_b"), dists=("full", "lp"), chunks=chunks)
    pr("(a) sweep_drive %.0f s" % (time.time() - t0))
    keys = ("track_gain", "turn_hold", "straight_delivery", "i_share", "cmd_rms", "r_mid", "hard16", "r_hi", "J_err")
    bands = ("0-5", "5-10", "10-15", "15-22", "22+")
    for dist in ("full", "lp"):
        for p in ("nominal", "light_b"):
            V = S[(dist, "V294", p)]
            pr("\n  mode B dist %s plant %s -- V294 absolute | candidate MINUS V294 (ratio for r_mid/hard16/r_hi/cmd_rms/J_err)" % (dist, p))
            for bd in bands:
                if bd not in V:
                    continue
                v = V[bd]
                pr("   %-6s V294 track %.3f hold %.3f strt %.3f ishare %.3f cmd %.0f rmid %.2f hard16 %.2f rhi %.2f Jerr %.3f LC %.2fHz %+.1fdB" % (
                    bd, v["track_gain"], v["turn_hold"], v["straight_delivery"], v["i_share"], v["cmd_rms"], v["r_mid"], v["hard16"],
                    v["r_hi"], v["J_err"], V["limit_cycle"]["f"], V["limit_cycle"]["dB"]))
                for c in C:
                    x = S[(dist, c.name, p)][bd]
                    rr = lambda k: x[k] / v[k] if np.isfinite(v[k]) and v[k] else float("nan")  # noqa: E731
                    pr("        %-12s dtrack %+.4f dhold %+.4f dstrt %+.4f dish %+.4f  cmd x%.3f rmid x%.3f hard16 x%.3f rhi x%.3f Jerr x%.3f" % (
                        c.name, x["track_gain"] - v["track_gain"], x["turn_hold"] - v["turn_hold"],
                        x["straight_delivery"] - v["straight_delivery"], x["i_share"] - v["i_share"], rr("cmd_rms"), rr("r_mid"),
                        rr("hard16"), rr("r_hi"), rr("J_err")))
            pr("   limit-cycle 1-5 Hz line: V294 %.2f Hz %+.1f dB | %s" % (
                V["limit_cycle"]["f"], V["limit_cycle"]["dB"],
                "  ".join("%s %.2fHz %+.1fdB" % (c.name, S[(dist, c.name, p)]["limit_cycle"]["f"], S[(dist, c.name, p)]["limit_cycle"]["dB"]) for c in C)))
    J["modeB"] = H.to_jsonable(S)

    # ---------------- (b) HF content, mode A full (recorded command) and mode B lp (echo loop) on stress members
    CL = [base] + C
    plants = ("nominal", "light_b", "mode13", "mode20", "mode20_lo")
    members = [fam[p] for p in plants]
    for mode, dist in (("A", "full"), ("B", "lp")):
        t0 = time.time()
        R = H.simulate(CL, members, chunks, H.SimOpts(mode=mode, dist=dist), record_1k=True)
        nM, nK = len(members), len(chunks)
        pr("\n(b) delivered HF torque rms (T counts), mode %s dist %s  [%.0f s]" % (mode, dist, time.time() - t0))
        res = {}
        for ci, c in enumerate(CL):
            for mi, p in enumerate(plants):
                rows = [ci * nM * nK + mi * nK + k for k in range(nK)]
                hf = [hf_all(R["T1k"][j, :R["lens"][j] * 10]) for j in rows]
                res[(c.name, p)] = {k: float(np.sqrt(np.mean([h[k] ** 2 for h in hf]))) for k in hf[0]}
        for p in plants:
            b0 = res[("V294", p)]
            pr("   %-9s V294 %s" % (p, {k: round(v, 3) for k, v in b0.items()}))
            for c in C:
                x = res[(c.name, p)]
                pr("        %-12s x V294 %s" % (c.name, {k: round(x[k] / b0[k], 2) for k in b0}))
        J["HF_%s_%s" % (mode, dist)] = H.to_jsonable(res)
        del R

    # ---------------- (c) staircase + sensor noise
    st = H.staircase_hf(CL)
    pr("\n(c) staircase triangle (+-2000 at the 123/frame slew cap), delivered HF rms, and x V294")
    for c, s in zip(CL, st):
        pr("   %-12s %s  x %s" % (c.name, {k: round(v, 2) for k, v in s.items()}, {k: round(s[k] / st[0][k], 2) for k in s}))
    J["staircase"] = {c.name: s for c, s in zip(CL, st)}
    # 30-120 Hz ripple of the staircase (re-run, keep T)
    NF = 1000
    tri = np.zeros(NF)
    v, up = 0.0, True
    for k in range(NF):
        v = v + 123 if up else v - 123
        up = False if v >= 2000 else (True if v <= -2000 else up)
        tri[k] = v
    L = H.Lane(CL)
    Tst = np.zeros((L.B, NF * 10))
    for n in range(NF * 10):
        k = n // 10
        if n % 10 == 0:
            idx, sp, m = L.demand(np.full(L.B, tri[k]))
        t, _ = L.tick(np.zeros(L.B, np.int64), sp, idx, m)
        Tst[:, n] = t
    pr("   staircase 30-120 Hz ripple rms: %s" % {c.name: round(band_rms(Tst[j], 30, 120), 2) for j, c in enumerate(CL)})
    J["staircase_ripple_30_120"] = {c.name: band_rms(Tst[j], 30, 120) for j, c in enumerate(CL)}
    # sensor noise
    rng = np.random.default_rng(1)
    n = 60000
    L = H.Lane(CL)
    xn = np.round(rng.normal(0.0, 1.93, n)).astype(np.int64)
    Tn = np.zeros((L.B, n))
    for i in range(n):
        t, _ = L.tick(np.full(L.B, xn[i]), np.zeros(L.B, np.int64), np.zeros(L.B, np.int64), np.full(L.B, 254))
        Tn[:, i] = t
    pr("\n(c) sensor-noise torque (x white 1.93 counts rms, sp 0, 60 s): T rms and HF bands")
    for j, c in enumerate(CL):
        pr("   %-12s T rms %.3f  %s" % (c.name, float(np.std(Tn[j])), {k: round(v, 3) for k, v in hf_all(Tn[j]).items()}))
    J["noise"] = {c.name: dict(rms=float(np.std(Tn[j])), **hf_all(Tn[j])) for j, c in enumerate(CL)}
    json.dump(J, open(os.path.join(HERE, "d2_time.json"), "w"), indent=1)
    open(os.path.join(HERE, "d2_time_out.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
