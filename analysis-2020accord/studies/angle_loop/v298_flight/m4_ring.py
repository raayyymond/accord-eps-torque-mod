# -*- coding: utf-8 -*-
r"""m4_ring.py -- M4 mechanisms (6) and (8): the R3* 3.85 Hz event at t ~ 1089.4 s on route 79 (V298), characterised
on every channel, and the design's EXACT closed-loop poles at that speed with Kd = +48 (as built, opposing), 0 and -48
(aiding), from the panel-2 common frequency scorer's lifted periodic model (panel2/score_freq.py lifted_for /
Lifted2.exact, C3B-P = GB-P table, Kp 112, Ki 40, fresh-rate D), imported unchanged.

    python m4_ring.py             (~3 s)

Event read: zero-phase 2.5-5.5 Hz band-pass (2nd-order Butterworth, sosfiltfilt over a 6 s span) of theta, theta_sp,
w18, the tap (100 Hz ZOH of the 50 Hz field) and the bar; half-cycle peaks; decay r = a(i+2)/a(i) (geometric mean)
-> zeta = ln(1/r) / sqrt(4 pi^2 + ln(r)^2); the phase of tap vs w18 at the event frequency (cross-spectrum over the
event span): tap IN PHASE with w18 = the motor torque u = -T OPPOSES the motion (damping); 180 deg = aiding.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import math
import sys

import numpy as np
from scipy import signal

import m4_common as C

T_EV, DUR_EV = 1089.412, 1.05


def halfcycles(x):
    s = np.signbit(x)
    zc = np.flatnonzero(s[1:] != s[:-1]) + 1
    return [(a, b, float(np.max(np.abs(x[a:b])))) for a, b in zip(zc[:-1], zc[1:]) if b > a]


def characterise(G, F, L):
    t = G["t"]
    i0 = np.searchsorted(t, T_EV - 3.0)
    i1 = np.searchsorted(t, T_EV + 3.0)
    e0 = np.searchsorted(t, T_EV) - i0
    e1 = np.searchsorted(t, T_EV + DUR_EV) - i0
    sos = signal.butter(2, [2.5, 5.5], "bandpass", fs=C.FS, output="sos")
    out = {}
    chans = dict(theta=G["theta"], theta_sp=G["theta_sp"], err=G["err"], w18=G["w18"],
                 sp_rate=np.gradient(G["theta_sp"]) * C.FS, tap=G["tap"], bar=G["bar"])
    bp = {}
    for k, x in chans.items():
        seg = np.nan_to_num(x[i0:i1])
        y = signal.sosfiltfilt(sos, seg - seg.mean())
        bp[k] = y
        hc = [h for h in halfcycles(y) if h[0] >= e0 - 5 and h[1] <= e1 + 5]
        amps = np.array([h[2] for h in hc])
        r = amps[2:] / amps[:-2] if len(amps) > 2 else np.array([np.nan])
        gm = float(np.exp(np.mean(np.log(np.maximum(r, 1e-6))))) if len(amps) > 2 else np.nan
        zeta = float(math.log(1 / gm) / math.sqrt(4 * math.pi ** 2 + math.log(gm) ** 2)) if np.isfinite(gm) and gm > 0 else np.nan
        out[k] = dict(n_half=len(hc), amp_max=float(amps.max()) if len(amps) else np.nan,
                      amps=amps.round(3).tolist(), r_gm=gm, zeta=zeta,
                      rms_event=float(np.std(y[e0:e1])), rms_before=float(np.std(y[max(e0 - 200, 0):e0])))
    # phases at f0 over the event span (complex demodulation)
    f0 = 3.85
    n = np.arange(e0, e1)
    ph = {}
    ref = np.sum(bp["w18"][n] * np.exp(-2j * np.pi * f0 * n / C.FS))
    for k in ("theta", "theta_sp", "err", "tap", "bar", "sp_rate"):
        z = np.sum(bp[k][n] * np.exp(-2j * np.pi * f0 * n / C.FS))
        ph[k] = dict(phase_vs_w18_deg=float(np.degrees(np.angle(z / ref))), gain_vs_w18=float(abs(z) / abs(ref)))
    out["phase"] = ph
    # context over the event: setpoint step, request, O1 / limiter stage, speed, angle
    stg = C.zoh(L["t"], L["stage"], t, fill=0)
    sl = slice(i0 + e0 - 100, i0 + e1 + 50)
    out["context"] = dict(v=float(np.median(G["vego"][sl])), theta_range=[float(G["theta"][sl].min()), float(G["theta"][sl].max())],
                          sp_range=[float(G["theta_sp"][sl].min()), float(G["theta_sp"][sl].max())],
                          sp_rate_absmax=float(np.max(np.abs(chans["sp_rate"][sl]))),
                          w_absmax=float(np.max(np.abs(G["w18"][sl]))), bar_absmax=float(np.max(np.abs(G["bar"][sl]))),
                          req_min=int(G["req"][sl].min()), stages=sorted(set(stg[sl].astype(int).tolist())),
                          tap_range=[float(G["tap"][sl].min()), float(G["tap"][sl].max())])
    # 0.1 s samples for the report
    k = np.arange(i0 + e0 - 50, i0 + e1 + 30, 5)
    out["trace"] = [dict(t=float(t[j]), th=float(G["theta"][j]), sp=float(G["theta_sp"][j]), w=float(G["w18"][j]),
                         tap=float(G["tap"][j]), bar=float(G["bar"][j]), st=int(stg[j])) for j in k]
    return out


def predicted_poles(v=12.0):
    sys.path.insert(0, str(C.AL / "c3" / "rev2B"))
    with contextlib.redirect_stdout(io.StringIO()):
        import rb_table as T
        sp = importlib.util.spec_from_file_location("p2_sf_m4", C.AL / "panel2" / "score_freq.py")
        SF = importlib.util.module_from_spec(sp)
        sys.modules["p2_sf_m4"] = SF
        sp.loader.exec_module(SF)
    members = ("nominal", "J_lo", "J_hi", "b_lo", "b_hi", "F_lo", "F_hi", "tau6", "ms_free", "light_b")
    out = {}
    for kd in (48, 0, -48):
        s = SF.Spec("C3B-P", "m4", list(T.GB_P), kd, ki=40, dkind="fresh")
        rows = {}
        for mem in members:
            for vi in (0, 5):                         # 'nom' and 'FAc' (the physical frame near centre)
                try:
                    lp = SF.lifted_for(s, mem, v, vi)
                    rho, poles = lp.exact()
                except Exception as e:                # pragma: no cover
                    rows["%s|%s" % (mem, SF.VARIANTS[vi][0])] = dict(err=str(e)[:80])
                    continue
                band = sorted([(float(f), float(z)) for f, z in poles if 0.2 <= f <= 30.0])
                b25 = [q for q in band if 2.0 <= q[0] <= 6.0]
                rows["%s|%s" % (mem, SF.VARIANTS[vi][0])] = dict(rho=float(rho), modes=band[:8],
                                                                 m2_6=b25, least=min(band, key=lambda q: q[1]) if band else None)
        out[kd] = rows
    return out


def main():
    tm = C.timer()
    G = C.build_grid(C.TAG79)
    F = C.fork_cache()
    L = C.limiter_reconstruct(F)
    R = dict(event=characterise(G, F, L))
    t1 = C.timer()
    R["poles"] = predicted_poles(float(R["event"]["context"]["v"]))
    R["poles_wall_s"] = t1()
    R["wall_s"] = tm()
    with open(C.OUT / "m4_ring.json", "w") as fh:
        json.dump(R, fh, indent=1, default=float)
    E = R["event"]
    print("M4 RING  (wall %.1f s; poles %.1f s)" % (R["wall_s"], R["poles_wall_s"]))
    print("R3* event t %.2f +%.2f s, context %s" % (T_EV, DUR_EV, E["context"]))
    for k in ("theta", "theta_sp", "err", "w18", "sp_rate", "tap", "bar"):
        e = E[k]
        print("  %-8s half-cycles %2d amp_max %7.3f r_gm %.3f zeta %.3f  rms event %.3f / before %.3f  amps %s" % (
            k, e["n_half"], e["amp_max"], e["r_gm"], e["zeta"], e["rms_event"], e["rms_before"], e["amps"][:10]))
    print("  phase vs w18 at 3.85 Hz:", {k: (round(v["phase_vs_w18_deg"]), round(v["gain_vs_w18"], 3)) for k, v in E["phase"].items()})
    print("  trace (0.05 s):")
    for r in E["trace"]:
        print("    t %.2f th %6.2f sp %6.2f w %6.2f tap %5.0f bar %5.0f st %d" % (r["t"], r["th"], r["sp"], r["w"], r["tap"], r["bar"], r["st"]))
    print("PREDICTED closed-loop modes at v = %.1f m/s (f Hz, zeta), 2-6 Hz and least-damped in 0.2-30 Hz:" % E["context"]["v"])
    for kd, rows in R["poles"].items():
        print("  Kd %+d" % kd)
        for k, r in rows.items():
            if "err" in r:
                print("    %-18s ERR %s" % (k, r["err"])); continue
            print("    %-18s rho %.4f  2-6 Hz %s  least %s" % (k, r["rho"], [(round(f, 2), round(z, 3)) for f, z in r["m2_6"]],
                                                         None if r["least"] is None else (round(r["least"][0], 2), round(r["least"][1], 3))))


if __name__ == "__main__":
    main()
