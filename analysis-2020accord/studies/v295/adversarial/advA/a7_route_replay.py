# -*- coding: utf-8 -*-
"""ADV-A a7: replay route r71b (75604b0a432fdc89_00000071--a7b8ba5d9d, V294 flown) command + wheel rate through the
BUILT cells, byte-exact, 1 kHz: V294 (control: must reproduce the plant cache's own V294 march tick for tick), V295,
and FF-only (fb clamp 0 -> r26 = 0).  Inputs are the plant cache's (plib.build): idx/sgn/taper m per 100 Hz frame
(from the V294 demand chain, unchanged in V295), x1k = resample_poly(wire, 10) (the kit's march convention, sg = +1).
OPEN LOOP: V295 is driven with V294's recorded motion (BELIEF that this bounds the arithmetic; the closed loop
would move differently).  Reports C binds, P binds, max |T|, trim rms/p99 by speed band, override resistance on
hands-on frames, |trim| > 300 dwell, mean T shift (DC) by band."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import advA_lane as A  # noqa: E402

J = json.load(open(os.path.join(HERE, "a1_cells.json")))
d = dict(np.load("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/plant/_scratch/cache/plant_r71b_v294.npz"))
n100 = len(d["idx"]); n = n100 * 10
x_raw = d["x1k"][:n]
print("route frames %d, ticks %d ; |x1k| > 12000 before rounding: %d ticks (no bails on this route)" % (n100, n, int(np.sum(np.abs(x_raw) > 12000))))
x1k = np.clip(np.round(x_raw), -12000, 12000).astype(int).tolist()


def march(c, C_override=None):
    """scalar, inlined copy of advA_lane.Lane.tick (engaged, gate off, ramp 0x8000, pol +1, addend 0); verified
    against advA_lane.Lane on the first 30,000 ticks below."""
    a, b = c["fb_a"], c["fb_b"]; C = c["fb_clamp"] if C_override is None else C_override
    kp = A.lerp(c["kp_x"], c["kp_y"], 0); assert all(v == kp for v in c["kp_y"])
    pcl, scl, la, lb, gain, tcl = c["p_clamp"], c["sum_clamp_u"], c["lag_a"], c["lag_b"], c["gain"], c["t_clamp_u"]
    LERP = [A.lerp(c["map_x"], c["map_y"], i) for i in range(241)]
    sp_k = [int(s) * LERP[int(i)] for s, i in zip(d["sgn"], d["idx"])]
    m_k = [int(v) for v in d["m"]]
    T = np.zeros(n, np.int32); R26 = np.zeros(n, np.int32); RAW = np.zeros(n, np.int32); P_ = np.zeros(n, np.int32)
    s = 0; sent = 0; o = 0; mx_as = 0
    for i in range(n):
        k = i // 10
        s_old = s if sent == 1 else 0
        pr = a * s_old
        if abs(pr) > mx_as:
            mx_as = abs(pr)
        s_new = (pr >> 10) + ((x1k[i] * b) >> 10)
        r26 = s_new - s_old
        RAW[i] = r26
        s = s_new; sent = 1
        r26 = C if r26 > C else (-C if r26 < -C else r26)
        E = (sp_k[k] << 2) - r26
        P = (E * kp) >> 8
        P = pcl if P > pcl else (-pcl if P < -pcl else P)
        S = (m_k[k] * P) >> 8
        S = scl if S > scl else (-scl if S < -scl else S)
        o2 = ((la * o) >> 10) + ((S * lb) >> 10)
        y = (o + o2) >> 5
        o = o2
        t = (y * gain) >> 15
        T[i] = tcl if t > tcl else (-tcl if t < -tcl else t)
        R26[i] = r26; P_[i] = P
    assert mx_as < 2 ** 31
    return dict(T=T, r26=R26, raw=RAW, P=P_, max_as=mx_as)


# ---- control 1: the inlined march == my scalar mirror class on the first 30,000 ticks
L = A.Lane(J["v295"]); bad = 0
R5 = march(J["v295"])
LERP5 = [A.lerp(J["v295"]["map_x"], J["v295"]["map_y"], i) for i in range(241)]
for i in range(30000):
    k = i // 10
    t = L.tick(x1k[i], int(d["sgn"][k]) * LERP5[int(d["idx"][k])], int(d["idx"][k]), m=int(d["m"][k]))
    bad += (t != R5["T"][i])
print("control 1: inlined march vs advA_lane.Lane, 30,000 ticks: differing ticks =", bad)
R4 = march(J["v294"]); RF = march(J["v295"], C_override=0)
# ---- control 2: my V294 march == the plant cache's own V294 march (T1k_live / sg) tick for tick
sg = int(d["sg"])
d4 = int(np.sum(R4["T"] != (d["T1k_live"][:n] / sg).astype(int)))
dF = int(np.sum(RF["T"] != (d["T1k_null"][:n] / sg).astype(int)))
print("control 2: my V294 march vs plib T1k_live: differing ticks %d ; my FF-only vs plib T1k_null: %d" % (d4, dF))
# ---- control 3: the tap (50 Hz, quantised to 8) vs my V294 march on hands-off engaged frames
tick = d["tick_tap"]; ho_tap = d["eng"][d["j100"]] & (np.abs(d["bar"][d["j100"]]) < 400)
q = lambda T: np.sign(T) * (np.abs(T).astype(np.int64) >> 3) * 8  # noqa: E731
res = d["T_tap"][ho_tap] - sg * q(R4["T"][tick[ho_tap]])
print("control 3: tap - quant(V294 march) on %d hands-off engaged tap frames: rms %.2f T, p99 |.| %.0f"
      % (int(ho_tap.sum()), float(np.sqrt(np.mean(res ** 2))), float(np.percentile(np.abs(res), 99))))

eng = np.repeat(d["eng"], 10)[:n]
v1k = np.repeat(d["v"], 10)[:n]
bar1k = np.repeat(d["bar"], 10)[:n]
press1k = np.repeat(d["cs_pressed"] > 0.5, 10)[:n]
hands_on = eng & (press1k | (np.abs(bar1k) >= 400))
hands_off = eng & ~press1k & (np.abs(bar1k) < 400)
C5 = J["v295"]["fb_clamp"]; PCL = J["v295"]["p_clamp"]
out = {}
print("\nengaged ticks %d (%.1f s) ; hands-on engaged %.1f s ; hands-off engaged %.1f s"
      % (int(eng.sum()), eng.sum() / 1000, hands_on.sum() / 1000, hands_off.sum() / 1000))
for nm, R in (("V294", R4), ("V295", R5)):
    trim = R["T"].astype(int) - RF["T"].astype(int)
    R["trim"] = trim
    e = eng
    print("%s (engaged): r26 clamp binds %d ticks (%.4f %%) ; P at clamp %d ticks (%.4f %%) ; max|T| %d ; max|r26 raw| %d ; "
          "p99.9|r26| %.0f ; max|a*s| %d (margin %.2f)"
          % (nm, int(np.sum(np.abs(R["raw"][e]) > C5)), 100 * np.mean(np.abs(R["raw"][e]) > C5),
             int(np.sum(np.abs(R["P"][e]) == PCL)), 100 * np.mean(np.abs(R["P"][e]) == PCL), int(np.abs(R["T"][e]).max()),
             int(np.abs(R["raw"][e]).max()), float(np.percentile(np.abs(R["r26"][e]), 99.9)), R["max_as"], 2 ** 31 / max(R["max_as"], 1)))
    print("   whole route (incl. disengaged, the fb filter runs regardless): r26 clamp binds %d ticks ; max|r26 raw| %d"
          % (int(np.sum(np.abs(R["raw"]) > C5)), int(np.abs(R["raw"]).max())))
print("\ntrim = T_live - T_FFonly (T counts), ENGAGED, by speed band [m/s]:")
BANDS = (("0-5", 0, 5), ("5-10", 5, 10), ("10-15", 10, 15), ("15-22", 15, 22), ("22+", 22, 99))
for bn, lo, hi in BANDS:
    mk = eng & (v1k >= lo) & (v1k < hi)
    if mk.sum() == 0:
        continue
    t4, t5 = R4["trim"][mk], R5["trim"][mk]
    dT = (R5["T"][mk].astype(int) - R4["T"][mk].astype(int))
    print("  %-6s %6.1f s | V294 rms %6.1f p99 %5.0f max %4d | V295 rms %6.1f p99 %5.0f max %4d | ratio rms x%.3f | "
          "mean(T295-T294) %+.2f T, rms %.1f"
          % (bn, mk.sum() / 1000, np.sqrt(np.mean(t4 ** 2)), np.percentile(np.abs(t4), 99), np.abs(t4).max(),
             np.sqrt(np.mean(t5 ** 2)), np.percentile(np.abs(t5), 99), np.abs(t5).max(),
             np.sqrt(np.mean(t5 ** 2)) / max(np.sqrt(np.mean(t4 ** 2)), 1e-9), dT.mean(), np.sqrt(np.mean(dT ** 2))))
print("\ndriver-override resistance, HANDS-ON engaged ticks (%.1f s): trim opposing the driver = -sign(bar)*trim"
      % (hands_on.sum() / 1000))
for nm, R in (("V294", R4), ("V295", R5)):
    t = R["trim"][hands_on]; opp = -np.sign(bar1k[hands_on]) * t
    print("  %s |trim| p50 %.0f p99 %.0f max %d | opposing part: p99 %.0f max %.0f, mean %+.1f ; frac of ticks opposing %.3f"
          % (nm, np.percentile(np.abs(t), 50), np.percentile(np.abs(t), 99), np.abs(t).max(), np.percentile(opp, 99),
             opp.max(), opp.mean(), np.mean(opp > 0)))
print("\n|trim| > 300 T dwell (engaged): V294 %.3f s, V295 %.3f s ; > 450: V294 %.3f s V295 %.3f s ; hands-off only > 300: V294 %.3f V295 %.3f"
      % (np.sum(np.abs(R4["trim"][eng]) > 300) / 1000, np.sum(np.abs(R5["trim"][eng]) > 300) / 1000,
         np.sum(np.abs(R4["trim"][eng]) > 450) / 1000, np.sum(np.abs(R5["trim"][eng]) > 450) / 1000,
         np.sum(np.abs(R4["trim"][hands_off]) > 300) / 1000, np.sum(np.abs(R5["trim"][hands_off]) > 300) / 1000))
dT = R5["T"].astype(int) - R4["T"].astype(int)
print("V295 - V294 delivered T on engaged ticks: rms %.1f, p99 %.0f, max %d ; mean %+.3f"
      % (np.sqrt(np.mean(dT[eng] ** 2)), np.percentile(np.abs(dT[eng]), 99), np.abs(dT[eng]).max(), dT[eng].mean()))
# trim/r26 ratio V295 vs V294 where neither binds (the pure x1.852 check on real motion)
mk = eng & (np.abs(R4["raw"]) <= C5) & (np.abs(R5["raw"]) <= C5) & (np.abs(R4["r26"]) > 20)
print("r26 ratio V295/V294 on %d unclamped engaged ticks with |r26_294| > 20: median %.4f (b ratio %.4f)"
      % (int(mk.sum()), float(np.median(R5["r26"][mk] / R4["r26"][mk])), J["v295"]["fb_b"] / J["v294"]["fb_b"]))
json.dump(dict(ok=True), open(os.path.join(HERE, "a7_done.json"), "w"))
np.savez_compressed(os.path.join(HERE, "_a7_traces.npz"), T4=R4["T"], T5=R5["T"], TF=RF["T"], r4=R4["r26"], r5=R5["r26"])
