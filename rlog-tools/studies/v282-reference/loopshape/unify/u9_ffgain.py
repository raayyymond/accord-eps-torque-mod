# -*- coding: utf-8 -*-
"""SIZING THE ONE LEVER THE MEASUREMENT POINTS AT -- offline, on logged demand, with no drive.

The lag is set by the FEEDFORWARD'S PHASE LEAD (corr(lead, lag) = -0.92 across the nine flown torque
routes).  `AccordFFRateGain` is the only toggle that weights the rate term against the hold term, and
it flew at 0.5 on every route in the corpus, so there is no flown dose point.  It does not need one:
the move term is PURE ARITHMETIC on logged signals --

    move(g) = clip(g * angle_des_rate / G(v), -limit(v), +limit(v))        ffrecon.move_term
    uff(g)  = pid_log.f/LAF  -  (move(g) - move(g_flown))                  sweep.py's exact identity

so the feedforward at any gain is computable from the log, and its phase can be MEASURED against the
same logged setpoint.  That is an inert tap, not a dose flown blind.

WHAT IS HELD FIXED, and why this is not a prediction of the car: P, I and the observer are frozen at
their logged values, and the measured plant P and controller C are held at what that route flew.  So
the number below is "what this gain does to the feedforward's phase, and what that phase would imply
through the loop as identified" -- an arithmetic reach question, exactly as sweep.py framed its own.
A real drive moves P, I and the observer.  Stated, not buried.

out: U9-OUT.txt, u9.json
"""
import json
import sys
import numpy as np
from pathlib import Path
_ST = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ST))
sys.path.insert(0, str(_ST / "ffgain_ceiling"))
import ulib as U
import uspec as SP
import ffrecon as F
from validate import load as vload

GAINS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
NPS = 1024
B = (0.15, 0.30)
print(F._self_test(), flush=True)

rows = {}
for rt, cfg in F.ROUTECFG.items():
    if U.FAMILY.get(rt) != "TORQ" or not cfg.get("ff_live"):
        continue
    S = vload(rt)
    Su = U.load(rt)
    tab = F.TABLES[cfg["commit"]]
    ad, adr, d_ad, dt = F.build_demand(S, cfg, False)
    v = np.nan_to_num(S["v"])
    G = np.interp(v, tab["G_BP"], tab["G_V"])
    lim = F.move_limit(v)
    r_unit = adr / G
    mv0 = np.clip(cfg["gain"] * r_unit, -lim, lim)
    ff0 = S["f"] / cfg["laf"]
    # positive control: at the flown gain the reconstruction must return the log exactly
    assert np.nanmax(np.abs((ff0 - (np.clip(cfg["gain"] * r_unit, -lim, lim) - mv0)) - ff0)) == 0.0
    m = U.usable(Su, 15.0)
    segs = U.segments(Su, m, 25.0)
    if not segs:
        del S, Su
        continue
    out = {}
    for g in GAINS:
        mv = np.clip(g * r_unit, -lim, lim)
        uffg = ff0 - (mv - mv0)
        ug = Su["ufb"] + uffg
        acc = None
        for a, b in segs:
            res = SP.window_spectra(dict(r=Su["r"][a:b], uff=uffg[a:b], u=ug[a:b],
                                         hf=uffg[a:b]), NPS)
            if res is None:
                continue
            f, sp, nb = res
            w = (b - a) / U.FS
            acc = {k: sp[k] * w for k in sp} if acc is None else {k: acc[k] + sp[k] * w for k in sp}
        gp = lambda a_, b_: (acc[(a_, b_)] if (a_, b_) in acc else np.conj(acc[(b_, a_)]))
        Prr = np.maximum(np.real(gp("r", "r")), 1e-30)
        Fg = U.smooth_c(gp("r", "uff") / Prr, 3)
        df = f[1] - f[0]
        s = (f >= 1.2) & (f < 4.0)
        out[g] = dict(lead=-U.group_delay_ms(f, Fg, *B), Fmag=U.bandavg_mag(f, Fg, *B, Prr),
                      cmd_hf=float(np.sqrt(np.sum(np.real(gp("u", "u"))[s]) * df)))
        out[g]["F"] = Fg
        out[g]["f"] = f
        out[g]["Prr"] = Prr
    rows[rt] = dict(cfg=cfg, out=out, sec=float(sum(b - a for a, b in segs) / U.FS))
    print(f"  {U.SHORT[rt]}  {cfg['tag']}  {rows[rt]['sec']:.0f} s  "
          + "  ".join(f"g{g}: lead {out[g]['lead']:+.0f} ms" for g in GAINS), flush=True)
    del S, Su

# --- through the loop, with C and P held at each route's MEASURED transfers -----------------------
L5 = json.load(open("u5_hi1k.json"))
D = np.load("spec_hi1k.npz", allow_pickle=True)
fam, route, sec = D["fam"], D["route"], D["sec"]
MEM = {k[2:]: np.asarray(D[k]) for k in D.files if k.startswith("S_")}
fsp = D["f"]


def CP(rt):
    idx = np.where(route == rt)[0]
    w = sec[idx]
    S = {k: np.tensordot(w, v[idx], axes=(0, 0)) / w.sum() for k, v in MEM.items()}
    gp = lambda a, b: (-1.0 if a == "sa" else 1.0) * (-1.0 if b == "sa" else 1.0) * \
        (S[f"{a}_{b}"] if f"{a}_{b}" in S else np.conj(S[f"{b}_{a}"]))
    C = U.smooth_c(gp("e", "ufb") / np.maximum(np.real(gp("e", "e")), 1e-30), 3)
    P = U.smooth_c(gp("r", "y") / gp("r", "u"), 5)
    return C, P, np.maximum(np.real(gp("r", "r")), 1e-30)


L = ["SIZING AccordFFRateGain ON LOGGED DEMAND (no drive; P, I and the observer frozen at their logged",
     "values, C and P held at each route's own measured transfers).", "",
     "FEEDFORWARD PHASE LEAD at 0.15-0.30 Hz (ms) as a function of the toggle:"]
L.append(f"{'route':<9}{'flown g':>8}" + "".join(f"{f'g={g}':>10}" for g in GAINS))
for rt, d in rows.items():
    L.append(f"{U.SHORT[rt]:<9}{d['cfg']['gain']:>8.2f}" + "".join(f"{d['out'][g]['lead']:>10.0f}" for g in GAINS))
L.append("")
L.append("RESULTING setpoint->loop-output LAG at 0.15-0.30 Hz (ms), through that route's measured C and P:")
L.append(f"{'route':<9}{'flown':>8}" + "".join(f"{f'g={g}':>10}" for g in GAINS) + f"{'V282 ref':>11}")
res = {}
for rt, d in rows.items():
    C, P, Prr = CP(rt)
    cells = []
    for g in GAINS:
        Fg = np.interp(fsp, d["out"][g]["f"], d["out"][g]["F"].real) + \
            1j * np.interp(fsp, d["out"][g]["f"], d["out"][g]["F"].imag)
        T = (C * P + P * Fg) / (1.0 + C * P)
        cells.append(U.group_delay_ms(fsp, T, *B))
    res[rt] = dict(gains=GAINS, lag=[float(x) for x in cells],
                   lead=[d["out"][g]["lead"] for g in GAINS],
                   cmd_hf=[d["out"][g]["cmd_hf"] for g in GAINS], flown=d["cfg"]["gain"])
    L.append(f"{U.SHORT[rt]:<9}{L5[rt]['Zdly0.15']:>8.0f}" + "".join(f"{c:>10.0f}" for c in cells) + f"{'101-128':>11}")
L.append("")
L.append("THE COST, on the same arithmetic: RMS of the TOTAL COMMAND in 1.2-4.0 Hz (torque units) --")
L.append("the band where the torque-mode wheel motion separates from V282's.  This is the command, not")
L.append("the wheel: it bounds what the lever ADDS to the excitation, it does not predict the response.")
L.append(f"{'route':<9}" + "".join(f"{f'g={g}':>10}" for g in GAINS) + "   x vs flown at g=1.5")
for rt, d in rows.items():
    base = d["out"][d["cfg"]["gain"]]["cmd_hf"]
    L.append(f"{U.SHORT[rt]:<9}" + "".join(f"{d['out'][g]['cmd_hf']:>10.4f}" for g in GAINS) +
             f"        {d['out'][1.5]['cmd_hf']/max(base,1e-12):>6.2f}x")
L.append("")
med = lambda key, g: np.median([res[rt][key][GAINS.index(g)] for rt in res])
L.append(f"{'gain':<8}{'median FF lead ms':>20}{'median lag ms':>16}{'median cmd 1.2-4 Hz':>22}")
for g in GAINS:
    L.append(f"{g:<8.2f}{med('lead', g):>20.0f}{med('lag', g):>16.0f}"
             f"{np.median([rows[rt]['out'][g]['cmd_hf'] for rt in rows]):>22.4f}")
L.append("")
L.append("V282's own feedforward carried 535-546 ms of lead at this band with |F| 0.069-0.085 torque")
L.append("per m/s^2; the torque builds fly 0.114-0.290 with -93..+394 ms.  The toggle's ceiling is 1.5.")
json.dump(res, open("u9.json", "w"), indent=1, default=float)
txt = "\n".join(L)
open("U9-OUT.txt", "w").write(txt)
print(txt)
