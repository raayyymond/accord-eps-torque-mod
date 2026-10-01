# -*- coding: utf-8 -*-
"""f5: SECOND METHOD for the turn-hold prediction -- a quasi-static fixed point built from r71b's own wire, no
simulated plant.
  (1) LAF_true(v) per band = slope of the fork's measured lat accel (controlsState la_act) on the delivered torque
      (carOutput torque, torque units) over steady-turn frames (|plan| 0.8-1.5 m/s^2, |d plan/dt| < 0.5; the
      drive_metrics turn-hold mask), hands-off chunks, with an intercept (roll / crown / offset).  EVIDENCE of the
      drive's static gain, with the P/I/relay all live.
  (2) the integrator's equivalent static gain beta = median(i / e) on the same frames (e = setpoint - la_act, m/s^2;
      i = torqueState.i, lat-accel units), measured on r1.  For a candidate, beta scales with Ki_eff = Ki(v)(1+lsf/Kp)
      (the same time since turn entry): beta_c = beta_r1 * Ki_eff_c / Ki_eff_r1.  BELIEF (a quasi-static proxy).
  (3) fixed point: a = s * [ (a_p + (Kp+lsf) e + beta e + Frelay) / LAF ] + c, e = a_p - a, relay saturated at
      +F*LAF (e_lsf >> 0.30 in a hold at these speeds -- checked), s and c from (1).  Solve for a / a_p at a_p = the
      band's median steady-turn plan.  The r1 row must reproduce the measured turn-hold (consistency, not
      independence); the candidate rows are the prediction."""
import sys, json
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/fork-config")
import numpy as np
import fc_lib as F
H = F.H

d = H.route()
ch = H.route_chunks()
BANDS = [("5-10", 5, 10), ("10-15", 10, 15), ("15-22", 15, 22), ("22+", 22, 99), ("8-22", 8, 22)]


def band_frames(lo, hi):
    V, P, A, T, I, S, E = [], [], [], [], [], [], []
    for a, b in ch:
        v = d["v"][a:b]
        plan = d["ctl_des_curv_f"][a:b] * v ** 2
        dpl = np.gradient(plan) * 100.0
        mk = (v >= lo) & (v < hi) & (np.abs(plan) >= 0.8) & (np.abs(plan) < 1.5) & (np.abs(dpl) < 0.5)
        V.append(v[mk]); P.append(plan[mk]); A.append(d["ctl_la_act_f"][a:b][mk])
        T.append(-d["co_torque_f"][a:b][mk])            # carOutput torque is the +right frame; the fork's output = -it
        I.append(d["ctl_i_f"][a:b][mk]); S.append(d["ctl_la_des_f"][a:b][mk])
    return [np.concatenate(x) for x in (V, P, A, T, I, S)]


def solve(fork, s, c, beta_r1, v, ap):
    kp, laf, fr = fork.kp, float(np.float32(fork.laf)), float(np.float32(fork.fric))
    lsf = F.lsf_of(v)
    kie_c = float(fork.ki_at(v)) * (1 + lsf / kp)
    kie_1 = 0.3 * (1 + lsf / 0.9)
    beta = beta_r1 * kie_c / kie_1
    # a = s*(ap + (kp+lsf+beta)(ap - a) + fr*laf)/laf + c  -> linear in a
    g = (kp + lsf + beta)
    num = s * (ap + g * ap + fr * laf * np.sign(ap)) / laf + c
    den = 1 + s * g / laf
    return (num / den) / ap


out = {}
cands = [F.R1,
         F.Fork("L12.5_fix", laf=12.5), F.Fork("L11_fix", laf=11.0), F.Fork("L10_fix", laf=10.0),
         F.Fork("L12.5_iso", laf=12.5, kp=round(0.9 * 12.5 / 14, 3)), F.Fork("L11_iso", laf=11.0, kp=round(0.9 * 11 / 14, 3)),
         F.Fork("Ki0.5", ki=0.5), F.Fork("KiH1", ki_high=1.0), F.Fork("KiH2", ki_high=2.0),
         F.Fork("L11_KiH1", laf=11.0, ki_high=1.0), F.Fork("L12.5_KiH1", laf=12.5, ki_high=1.0),
         F.Fork("A_Kp0.75_Ki0.40_0.8", kp=0.75, ki=0.4, ki_high=0.8), F.Fork("B_Kp0.75_Ki0.40_0.6", kp=0.75, ki=0.4, ki_high=0.6),
         F.Fork("C_Kp0.90_Ki0.30_0.8", kp=0.9, ki=0.3, ki_high=0.8), F.Fork("D_Kp0.70_Ki0.40_0.8", kp=0.7, ki=0.4, ki_high=0.8),
         F.Fork("E_Kp0.90_Ki0.50_flat", kp=0.9, ki=0.5)]
for nm, lo, hi in BANDS:
    V, P, A, T, I, S = band_frames(lo, hi)
    if len(V) < 200:
        print("%s: %d frames, skipped" % (nm, len(V)))
        continue
    sg = np.sign(P)
    Pa, Aa, Ta, Ia, Sa = P * sg, A * sg, T * sg, I * sg, S * sg      # fold both turn directions onto +
    s, c = np.polyfit(Ta, Aa, 1)
    e = Sa - Aa
    ok = np.abs(e) > 0.05
    beta = float(np.median(Ia[ok] / e[ok]))
    vm, apm = float(np.median(V)), float(np.median(Pa))
    hold_meas = float(np.median(Aa / Pa))
    print("\n%s  n %d (%.1f s)  v %.1f  plan %.2f  | LAF_true slope s %.2f (m/s^2 per torque) c %+.3f  R2 %.3f | beta(r1) %.2f"
          % (nm, len(V), len(V) / 100, vm, apm, s, c, np.corrcoef(Ta, Aa)[0, 1] ** 2, beta))
    print("   measured turn-hold %.3f ; r1 static fixed point %.3f (consistency)" % (hold_meas, solve(F.R1, s, c, beta, vm, apm)))
    s0 = float(np.median(Aa / Ta))                       # through-origin form: the static gain incl. every offset
    print("   through-origin s0 = median(a/torque) %.2f ; r1 fixed point with s0, c 0: %.3f" % (s0, solve(F.R1, s0, 0.0, beta, vm, apm)))
    for fk in cands[1:]:
        h = solve(fk, s, c, beta, vm, apm)
        h0 = solve(fk, s0, 0.0, beta, vm, apm)
        print("   %-12s %-40s hold %.3f  (%+.3f vs r1 fp) | through-origin %.3f (%+.3f)" % (
            fk.name, fk.short(), h, h - solve(F.R1, s, c, beta, vm, apm), h0, h0 - solve(F.R1, s0, 0.0, beta, vm, apm)))
        out[(nm, fk.name)] = h
        out[(nm, fk.name + "_s0")] = h0
    out[(nm, "r1")] = solve(F.R1, s, c, beta, vm, apm)
    out[(nm, "r1_s0")] = solve(F.R1, s0, 0.0, beta, vm, apm)
    out[(nm, "meas")] = hold_meas
json.dump({"|".join(k): v for k, v in out.items()}, open("out/f5_static.json", "w"), indent=1)
