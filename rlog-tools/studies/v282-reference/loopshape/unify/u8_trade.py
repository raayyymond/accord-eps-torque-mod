# -*- coding: utf-8 -*-
"""THE TRADE CURVE THAT THE NINE FLOWN TORQUE CONFIGURATIONS ALREADY DRAW, and what the margins allow.

No simulation: each point is one flown route, measured two ways --
  x = the lag of the shaped setpoint -> wheel angle at 0.15-0.30 Hz (Regime A, the tracking gap)
  y = the RMS of the wheel angle the setpoint does NOT explain, 1.2-4.0 Hz (Regime B, the shake)
V282's three routes are the target box.  Whether any flown fork configuration reaches it is then a
matter of looking, not of predicting.

Also: the CONTROLLER estimate is checked against each route's own flown gains (a positive control on
|C|), and the gain-raise question is taken as far as the logs actually support and no further.

out: U8-OUT.txt, u8.json
"""
import json
import numpy as np
import ulib as U

L5 = json.load(open("u5_hi1k.json"))
L6 = json.load(open("u6_hi1k.json"))

rows = []
for rt in L5:
    d5, d6 = L5[rt], L6[rt]
    kp, laf = U.kp(rt), U.laf(rt)
    p = U.PARAMS[rt]
    ki = float(p["AccordTorqueKi"]) if p["AccordTorqueKi"] != "ABSENT" else (0.0 if U.FAMILY[rt] == "V282old" else 0.0)
    kih = float(p["AccordTorqueKiHigh"]) if p["AccordTorqueKiHigh"] != "ABSENT" else 0.0
    # the fork's Ki schedule: AccordTorqueKi below 8 m/s -> AccordTorqueKiHigh from 18 m/s (rev 4)
    v = d5["v"]
    ki_eff = ki if kih <= 0 else float(np.interp(v, [8.0, 18.0], [ki, kih]))
    fc = np.sqrt(0.15 * 0.30)
    Cpred = abs(complex(kp / laf, -ki_eff / (2 * np.pi * fc) / laf))
    rows.append(dict(rt=rt, short=U.SHORT[rt], fam=U.FAMILY[rt], v=v, sec=d5["sec"],
                     lag=d5["Zdly0.15"], L=d5["L0.15"], C=d5["C0.15"], Cpred=Cpred,
                     P=d5["P0.15"], F=d5["F0.15"], Fdly=d5["Fdly0.15"],
                     inc12=d6["inc1.2"], inc24=d6["inc2.4"], inc06=d6["inc0.6"],
                     inc_hi=float(np.hypot(d6["inc1.2"], d6["inc2.4"])),
                     cfg=d6["cfg"]))

L = ["POSITIVE CONTROL ON |C|: the measured feedback gain against the one computed from each route's",
     "OWN flown SteerKP / SteerLatAccel / AccordTorqueKi(High) at the band centre 0.212 Hz.", ""]
L.append(f"{'route':<9}{'fam':<8}{'kp/LAF':>8}{'ki_eff':>8}{'|C| pred':>10}{'|C| meas':>10}{'ratio':>8}")
for d in rows:
    L.append(f"{d['short']:<9}{d['fam']:<8}{U.kp(d['rt'])/U.laf(d['rt']):>8.4f}"
             f"{'':>8}{d['Cpred']:>10.4f}{d['C']:>10.4f}{d['C']/max(d['Cpred'],1e-9):>8.2f}")
rr = [d["C"] / d["Cpred"] for d in rows]
L.append(f"   ratio across all 15 routes: median {np.median(rr):.2f}, range {min(rr):.2f}-{max(rr):.2f}")
L.append("")
L.append("THE TRADE CURVE (each point is one flown route; nothing is simulated):")
L.append(f"{'route':<9}{'fam':<8}{'s':>5}{'v':>5}{'LAG ms':>8}{'SHAKE 1.2-4':>13}{'inc .6-1.2':>12}"
         f"{'|L|':>7}{'|F|':>7}{'F lead ms':>11}  config")
for d in sorted(rows, key=lambda z: z["lag"]):
    L.append(f"{d['short']:<9}{d['fam']:<8}{d['sec']:>5.0f}{d['v']:>5.1f}{d['lag']:>8.0f}"
             f"{d['inc_hi']:>13.4f}{d['inc06']:>12.4f}{d['L']:>7.3f}{d['F']:>7.3f}{-d['Fdly']:>11.0f}  {d['cfg']}")
L.append("")
V = [d for d in rows if d["fam"] == "V282"]
T = [d for d in rows if d["fam"] == "TORQ"]
box = (min(d["lag"] for d in V), max(d["lag"] for d in V),
       min(d["inc_hi"] for d in V), max(d["inc_hi"] for d in V))
L.append(f"V282 TARGET BOX: lag {box[0]:.0f}-{box[1]:.0f} ms, shake {box[2]:.4f}-{box[3]:.4f} deg")
inb = [d for d in T if d["lag"] <= box[1] and d["inc_hi"] <= box[3]]
L.append(f"torque routes inside the box: {len(inb)} of {len(T)}")
L.append(f"torque routes inside on LAG only  : {[d['short'] for d in T if d['lag'] <= box[1]]}")
L.append(f"torque routes inside on SHAKE only: {[d['short'] for d in T if d['inc_hi'] <= box[3]]}")
L.append(f"best torque shake {min(d['inc_hi'] for d in T):.4f} deg = "
         f"{min(d['inc_hi'] for d in T)/box[3]:.2f}x the WORST V282 route")
L.append(f"best torque lag   {min(d['lag'] for d in T):.0f} ms  vs V282 {box[0]:.0f}-{box[1]:.0f} ms")
cc = np.corrcoef([d["lag"] for d in T], [d["inc_hi"] for d in T])[0, 1]
L.append(f"corr(lag, shake) across the 9 torque routes = {cc:+.3f}  "
         f"(n=9; a strong negative value would mean the two trade one-for-one)")
# Pareto front among torque routes
par = []
for d in T:
    if not any((o["lag"] <= d["lag"] and o["inc_hi"] <= d["inc_hi"] and o is not d) for o in T):
        par.append(d)
L.append("PARETO FRONT (no flown torque route beats these on both axes): " +
         ", ".join(f"{d['short']}({d['lag']:.0f} ms, {d['inc_hi']:.4f})" for d in sorted(par, key=lambda z: z['lag'])))
L.append("")
L.append("WHAT A GAIN RAISE WOULD HAVE TO DO, and where the logs stop supporting the question:")
u2 = json.load(open("u2_hi.json"))
bandkeys = ["0.08-0.15", "0.15-0.30", "0.30-0.60", "0.60-1.20", "1.20-2.40", "2.40-4.00"]
lv = [u2["V282"]["m"][f"L|{b}"] for b in bandkeys]
lt = [u2["TORQ"]["m"][f"L|{b}"] for b in bandkeys]
cohv = [u2["V282"]["m"][f"coh_ru|{b}"] for b in bandkeys]
coht = [u2["TORQ"]["m"][f"coh_ru|{b}"] for b in bandkeys]
L.append(f"   {'band':<12}{'|L| V282':>10}{'|L| TORQ':>10}{'x needed':>10}{'|L|x3.3':>10}"
         f"{'coh ru V':>10}{'coh ru T':>10}")
for b, a, c, dv, dt in zip(bandkeys, lv, lt, cohv, coht):
    L.append(f"   {b:<12}{a:>10.3f}{c:>10.3f}{a/c:>10.2f}{c*3.30:>10.3f}{dv:>10.3f}{dt:>10.3f}")
L.append("   Matching V282's |L| at 0.15-0.30 Hz needs x3.30 on the feedback gain.  At that gain the")
L.append("   torque loop's |L| first reaches 1 somewhere between 0.6 and 1.8 Hz -- INSIDE the band")
L.append("   where the uncommanded wheel motion lives, and where the reference has so little power")
L.append("   that the measured phase of L is not trustworthy (coherence r-u falls to "
         f"{coht[3]:.2f} / {coht[4]:.2f}).")
L.append("   => the PHASE MARGIN at the new crossover is NOT measurable from these logs.  That is a")
L.append("   missing instrument, not a small number: it is the one quantity that decides whether a")
L.append("   gain raise buys tracking or buys shake.")
json.dump(rows, open("u8.json", "w"), indent=1, default=float)
txt = "\n".join(L)
open("U8-OUT.txt", "w").write(txt)
print(txt)
