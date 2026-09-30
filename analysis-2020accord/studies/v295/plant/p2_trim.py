# -*- coding: utf-8 -*-
"""p2_trim.py -- TASK 2: the acceleration trim AS MEASURED vs the byte-exact 1 kHz model.
python p2_trim.py -> p2_trim_out.txt, p2_trim.npz

(a) FRF  wheel rate om (deg/s) -> trim torque (T counts), 0.3-20 Hz, at the 50 Hz tap instants, hands-off engaged:
      measured trim = T_tap - quant(T_null)      (the tap minus the byte-exact FEEDFORWARD march)
      model trim    = T_live - T_null            (the byte-exact march with the trim, from the same 100 Hz rate)
      analytic      = the linear z-domain chain at 1 kHz from the IMAGE cells (a, b, Kp, taper 254, output lag, gain)
    gain ratio and phase difference measured/analytic with coherence; F3 fires if > 20 % or > 20 deg anywhere in 0.5-5 Hz
    where coherence >= 0.5.  Done at the tap offset -4 ms (live-march / V293 FF-only) AND 0 ms (null-march low-al) --
    the phase sensitivity to that unresolved 4 ms is reported, not hidden.
(b) the fb clamp census is in p1_gates_out.txt (never binds).
(c) trim vs FF size by band: rms and p99, model (100 Hz block means) and measured (tap - null), hands-off engaged.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import frf as FRF  # noqa: E402
import plib as P  # noqa: E402

OUT = []
HERE = os.path.dirname(os.path.abspath(__file__))


def pr(s=""):
    print(s, flush=True)
    OUT.append(str(s))


def analytic_trim(f, c, taper=254, fs=1000.0):
    """T_trim / om  (T counts per deg/s, tap sign, om + = left) of the linear 1 kHz chain, from the image cells.
    x = -8*om (march convention x = +wire); R = g(1-z^-1)/(1-p z^-1); P = -(Kp/256) r26; S = taper/256 P;
    output lag Y/S = (lb/1024)(1+z^-1)/32 / (1 - (la/1024) z^-1); T = gain/32768 * Y."""
    z = np.exp(1j * 2 * np.pi * f / fs)
    p, g = c["fb_a"] / 1024.0, c["fb_b"] / 1024.0
    R = g * (1 - 1 / z) / (1 - p / z)
    Hout = (c["lag_b"] / 1024.0) * (1 + 1 / z) / 32.0 / (1 - (c["lag_a"] / 1024.0) / z)
    return (-8.0) * R * (-(c["kp_Y"][0] / 256.0)) * (taper / 256.0) * Hout * (c["gain"] / 32768.0)


def main():
    d = P.load()
    import r71b_cache as RC
    c = RC.v294_cells()
    c = {k: (float(v[0]) if k == "kp_Y" else v) for k, v in c.items()} | {"kp_Y": [float(c["kp_Y"][0])]}
    j = d["j100"]
    ho = d["ho"][j]
    runs = P.runs(ho & (np.diff(np.r_[d["t_tap"][0] - 0.02, d["t_tap"]]) < 0.03), min_len=256)
    pr("hands-off engaged tap stretches >= 5.12 s: %d, %.0f s" % (len(runs), sum(b - a for a, b in runs) / 50.0))
    res = {}
    for dms in (d["dms"], 0):
        tk = np.clip(10 * j + d["sub"] + dms, 0, len(d["T1k_live"]) - 1)
        om_t = -d["x1k"][tk] / 8.0
        meas = d["T_tap"] - P.quant(d["T1k_null"][tk])
        model = d["T1k_live"][tk] - d["T1k_null"][tk]
        f, nw, S = FRF.cross(dict(om=om_t, meas=meas, model=model), runs, 256, 50.0)
        Hm = FRF.H_dir(S, "om", "meas")
        Hmod = FRF.H_dir(S, "om", "model")
        Ha = analytic_trim(f, c)
        cm = FRF.coh(S, "om", "meas")
        res[dms] = (f, Hm, Hmod, Ha, cm, nw)
        pr("")
        pr("(a) om -> trim FRF, tap tick offset %+d ms, %d windows of 5.12 s (T counts per deg/s; phase deg)" % (dms, nw))
        pr("    %6s | %8s %7s | %8s %7s | %8s %7s | %6s | %7s %8s" % ("f Hz", "|meas|", "ph", "|model|", "ph", "|analyt|", "ph",
                                                                     "coh", "gain r", "dphase"))
        for ff in (0.3, 0.5, 0.8, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 18.0, 20.0):
            i = int(np.argmin(np.abs(f - ff)))
            pr("    %6.2f | %8.3f %7.1f | %8.3f %7.1f | %8.3f %7.1f | %6.3f | %7.3f %+8.1f" % (
                f[i], abs(Hm[i]), np.degrees(np.angle(Hm[i])), abs(Hmod[i]), np.degrees(np.angle(Hmod[i])), abs(Ha[i]),
                np.degrees(np.angle(Ha[i])), cm[i], abs(Hm[i]) / abs(Ha[i]), np.degrees(np.angle(Hm[i] / Ha[i]))))
        sel = (f >= 0.5) & (f <= 5.0) & (cm >= 0.5)
        gr = np.abs(Hm[sel]) / np.abs(Ha[sel])
        dp = np.degrees(np.angle(Hm[sel] / Ha[sel]))
        pr("    0.5-5 Hz bins with coh >= 0.5: %d ; gain ratio meas/analytic %.3f..%.3f (median %.3f) ; dphase %+.1f..%+.1f"
           " (median %+.1f) deg -> F3 %s" % (sel.sum(), gr.min(), gr.max(), np.median(gr), dp.min(), dp.max(),
                                             np.median(dp), "FIRES" if (np.any(np.abs(gr - 1) > 0.2) or np.any(np.abs(dp) > 20))
                                             else "does not fire"))
        grm = np.abs(Hmod[sel]) / np.abs(Ha[sel])
        dpm = np.degrees(np.angle(Hmod[sel] / Ha[sel]))
        pr("    model march vs analytic in the same bins: gain %.3f..%.3f, dphase %+.1f..%+.1f deg (checks the 100 Hz-rate"
           " up-sampling, not the ECU)" % (grm.min(), grm.max(), dpm.min(), dpm.max()))
        # equivalent pure delay of the measured trim vs the analytic: slope of dphase over 1-8 Hz with coh >= 0.3
        s2 = (f >= 1) & (f <= 8) & (cm >= 0.3)
        if s2.sum() > 3:
            k = np.polyfit(f[s2], np.unwrap(np.angle(Hm[s2] / Ha[s2])), 1)
            pr("    equivalent extra delay of the MEASURED trim vs analytic (1-8 Hz, coh >= 0.3): %.2f ms" % (-k[0] / (2 * np.pi) * 1000))
    # (c) trim vs FF by band
    pr("")
    pr("(c) TRIM vs FEEDFORWARD, hands-off laterally engaged (T counts).  model = 100 Hz block means of the 1 kHz march;"
       " meas = tap - null march at the 50 Hz tap instants")
    pr("    %-6s %6s | %8s %8s | %8s %8s | %8s %8s | %7s" % ("band", "s", "FF rms", "FF p99", "trim rms", "trim p99",
                                                          "meas rms", "meas p99", "trim/FF"))
    tk = d["tick_tap"]
    meas = d["T_tap"] - P.quant(d["T1k_null"][tk])
    for nm, lo, hi in (("all", 0, 99),) + P.BANDS:
        m = d["ho"] & P.band_mask(d, lo, hi)
        mt = ho & (d["v"][j] >= lo) & (d["v"][j] < hi)
        ff, tr = d["T_null"][m], d["T_trim"][m]
        pr("    %-6s %6.0f | %8.1f %8.1f | %8.1f %8.1f | %8.1f %8.1f | %7.3f" % (
            nm, m.sum() / 100, np.sqrt(np.mean(ff ** 2)), np.percentile(np.abs(ff), 99), np.sqrt(np.mean(tr ** 2)),
            np.percentile(np.abs(tr), 99), np.sqrt(np.mean(meas[mt] ** 2)), np.percentile(np.abs(meas[mt]), 99),
            np.sqrt(np.mean(tr ** 2)) / np.sqrt(np.mean(ff ** 2))))
    # all engaged (incl. driver-pressed), for completeness
    m = d["eng"]
    pr("    engaged incl. hands-on: FF rms %.1f p99 %.1f ; trim rms %.1f p99 %.1f ; max |trim| %.1f" % (
        np.sqrt(np.mean(d["T_null"][m] ** 2)), np.percentile(np.abs(d["T_null"][m]), 99), np.sqrt(np.mean(d["T_trim"][m] ** 2)),
        np.percentile(np.abs(d["T_trim"][m]), 99), np.max(np.abs(d["T_trim"][m]))))
    f, Hm, Hmod, Ha, cm, nw = res[d["dms"]]
    np.savez(os.path.join(HERE, "_scratch", "p2_trim.npz"), f=f, Hm=Hm, Hmod=Hmod, Ha=Ha, cm=cm,
             f0=res[0][0], Hm0=res[0][1])
    open(os.path.join(HERE, "p2_trim_out.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
