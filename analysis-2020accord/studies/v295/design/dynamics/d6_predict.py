# -*- coding: utf-8 -*-
"""d6_predict.py -- lens "dynamics": the PRE-REGISTERED wire predictions for the finalists and the figures.

(1) The trim-footprint instrument (metric agent, V294-ACCEL-TRACKING-METRIC.md section 3: tap = c FF + K alpha per band,
    V294 measured |K| 0.193 / 0.128 / 0.060 at 0.3-1 / 1-3 / 3-8 Hz, design 0.202 / 0.151 / 0.058) -- predicted |K| RATIO
    and phase SHIFT of each finalist vs V294, from the exact 1 kHz trim transfer (convention-free: ratios and differences),
    band-averaged on a log grid.  Then the predicted |K| = V294's MEASURED |K| x ratio.
(2) E3 (the attribution agent's pre-registered trim-live estimator, Rm = lp1(-d/dt lp1(x/8, 2.03 Hz), 5.05 Hz)): its
    regressor is built with V294's pole and output lag, so a candidate reads E3 = V294's 0.21 x (projection of the
    candidate's trim on V294's regressor) -- computed by marching both on r71b (the d3 cache is not used; analytic here).
(3) Physical constants of the finalists (pole, K_alpha, T/omega at 1-5 Hz, damping share, b/b_max).
(4) Figures: fig_d1_trim_bode.png (trim opposing torque vs f), fig_d2_ff_phase.png (cmd -> T phase / delay).
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
sys.path.insert(0, HERE)
import v295_harness as H  # noqa: E402
from d1_linear import lag_cells  # noqa: E402

NL = chr(10)


def band_avg(c, lo, hi, kind="K"):
    f = np.logspace(np.log10(lo), np.log10(hi), 60)
    To = H.trim_T_per_omega(c, f)             # opposing torque per deg/s
    K = To / (2j * np.pi * f)                 # per deg/s^2
    return np.mean(np.abs(K)), np.degrees(np.angle(np.mean(K / np.abs(K))))


def main():
    lines = []
    pr = lambda *a: (print(*a), lines.append(" ".join(str(x) for x in a)))  # noqa: E731
    base = H.Cells.v294()
    C = [base, base.replace(fb_a=1017, name="A1017"), base.replace(fb_a=1014, name="A1014"), lag_cells(base, 8.0).replace(name="L8"),
         lag_cells(base, 10.0).replace(name="L10")]
    meas = {"0.3-1": 0.193, "1-3": 0.128, "3-8": 0.060}
    J = {}
    pr("(1) trim-footprint prediction: |K| ratio and phase shift vs V294 per band; predicted |K| = V294 measured x ratio")
    for c in C:
        row = {}
        for bnm, lo, hi in (("0.3-1", 0.3, 1.0), ("1-3", 1.0, 3.0), ("3-8", 3.0, 8.0)):
            m0, p0 = band_avg(base, lo, hi)
            m1, p1 = band_avg(c, lo, hi)
            row[bnm] = dict(ratio=m1 / m0, dphase=p1 - p0, K_pred=meas[bnm] * m1 / m0)
        J[c.name] = row
        pr("   %-6s %s" % (c.name, "  ".join("%s: x%.2f (%+.0f deg) -> |K| %.3f" % (b, v["ratio"], v["dphase"], v["K_pred"]) for b, v in row.items())))
    pr("")
    pr("(3) physical constants")
    for c in C:
        pole = -math.log(c.fb_a / 1024.0) / (2 * math.pi * 1e-3)
        lpole = -math.log(c.lag_a / 1024.0) / (2 * math.pi * 1e-3)
        Ka = (960 / 256.) * 8 * 1e-3 * c.fb_b / (1024 - c.fb_a) * (254 / 256.) * (c.lag_b / (16.0 * (1024 - c.lag_a))) * c.gain / 32768.
        f = np.array([1.0, 2.0, 2.5, 3.0, 5.0])
        To = H.trim_T_per_omega(c, f)
        pr("   %-6s fb pole %.2f Hz  out-lag %.2f Hz (DC %.5f)  K_alpha %.4f T/(deg/s^2)  HF damping 8b/1024 x chain %.3f  b/b_max %.3f"
           % (c.name, pole, lpole, c.lag_b / (16.0 * (1024 - c.lag_a)), Ka,
              (960 / 256.) * 8 * c.fb_b / 1024. * (254 / 256.) * (c.lag_b / (16.0 * (1024 - c.lag_a))) * c.gain / 32768., c.fb_b / c.b_max))
        pr("          T/omega @ %s Hz: %s ; damping part %s" % (f.tolist(), ["%.2f@%+.0f" % (abs(t), np.degrees(np.angle(t))) for t in To],
                                                              np.round(np.abs(To) * np.cos(np.angle(To)), 2).tolist()))
        J[c.name]["consts"] = dict(pole_hz=pole, lag_hz=lpole, K_alpha=Ka, b_over_bmax=c.fb_b / c.b_max)
    json.dump(J, open(os.path.join(HERE, "d6_predict.json"), "w"), indent=1)
    open(os.path.join(HERE, "d6_predict_out.txt"), "w").write(NL.join(lines) + NL)
    # ---------------- figures
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:  # pragma: no cover
        print("no matplotlib:", e)
        return
    f = np.logspace(np.log10(0.2), np.log10(40), 400)
    fig, ax = plt.subplots(2, 1, figsize=(7.5, 6.5), sharex=True)
    for c, col in zip(C, ("#444444", "#1f77b4", "#6baed6", "#d62728", "#ff9896")):
        To = H.trim_T_per_omega(c, f)
        ax[0].loglog(f, np.abs(To), color=col, label=c.name)
        ax[1].semilogx(f, np.abs(To) * np.cos(np.angle(To)), color=col, label=c.name)
    ax[0].set_ylabel("|T/omega| (T per deg/s)")
    ax[1].set_ylabel("damping part |.|cos (T per deg/s)")
    ax[1].set_xlabel("Hz")
    ax[0].axvspan(1.6, 3.0, color="#ffd27f", alpha=0.3, lw=0)
    ax[1].axvspan(1.6, 3.0, color="#ffd27f", alpha=0.3, lw=0, label="hard-turn jerk band 1.6-3 Hz")
    ax[1].axvspan(13, 25, color="#cccccc", alpha=0.3, lw=0, label="no-grinding guard 13-25 Hz")
    ax[0].legend(fontsize=8); ax[1].legend(fontsize=7)
    ax[0].set_title("trim opposing torque per wheel rate (exact 1 kHz)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "fig_d1_trim_bode.png"), dpi=110)
    fig, ax = plt.subplots(1, 1, figsize=(7.5, 3.8))
    f2 = np.logspace(np.log10(0.3), np.log10(20), 300)
    zoh = np.exp(-1j * np.pi * f2 * 0.01) * np.sinc(f2 * 0.01)
    for c, col in zip(C, ("#444444", "#1f77b4", "#6baed6", "#d62728", "#ff9896")):
        G = H.ff_tf(c, f2) * zoh
        ax.semilogx(f2, -np.angle(G) / (2 * np.pi * f2) * 1e3, color=col, label=c.name)
    ax.set_ylabel("cmd -> T equivalent delay (ms)")
    ax.set_xlabel("Hz")
    ax.legend(fontsize=8)
    ax.set_title("0xE4 -> delivered torque equivalent delay (output lag + 100 Hz ZOH)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "fig_d2_ff_delay.png"), dpi=110)


if __name__ == "__main__":
    main()
