# -*- coding: utf-8 -*-
"""p6_hf_noise.py -- TASK 3: high-frequency plant facts and the acceleration operand's noise floor.
python p6_hf_noise.py -> p6_hf_noise_out.txt, _scratch/p6_hf.npz

(a) WHAT IS IDENTIFIABLE above 5 Hz.  T -> om coherence 5-30 Hz (IV on the FF torque, and direct), and the diagnostic
    that decides what the DIRECT estimate is at HF: with the trim closed on the rate, H_dir -> -1/C (the inverse of the
    controller) wherever the rate's own noise dominates the input -- compare |H_dir| and phase with -1/C(f).
(b) THE STEERING-WHEEL-ON-TORSION-BAR MODE, measured.  Hands-off, the bar torque is the torsion bar's twist:
    bar = K (th_w - th_m), and the wheel side obeys J_w th_w'' = -K (th_w - th_m) - c (om_w - om_m) (no driver), so
        bar / om_m = -A s / (1 + 2 z s/w_t + s^2/w_t^2),   w_t = sqrt(K/J_w)  (the free-wheel torsion-bar mode)
    The motor-side rate om_m (= x/8) is the INPUT here and the bar is a pure OUTPUT of it, so the direct FRF om -> bar is
    unbiased by the LKAS loop.  Fit A, f_t, zeta_t (coherence-weighted, 1-40 Hz).  In the collocated two-mass plant the
    flexible mode then sits at f2 = f_t / sqrt(1 - r2) (r2 = J_w/J), with the antiresonance at f_t.
(c) THE RATE SENSOR NOISE FLOOR.  x (counts, 8 per deg/s) at standstill, not engaged, wheel untouched; and in engaged
    quiet cruise (|om| LPF < 1 deg/s): variance, lag-1 autocorrelation, spectrum.
(d) THE OPERAND AND TORQUE NOISE.  The byte-exact lane (Lane294) driven by x = integer noise of that variance (white at
    1 kHz: the 100 Hz samples cannot see the 1 kHz colour -- stated), sp = 0: rms of r26 and of T, and T by band
    5-10/10-15/15-20/20-30 Hz, for the shipped pole (2.03 Hz) and poles 4 / 8 / 16.5 Hz with b rescaled to keep K_alpha
    (the DC gain alpha -> r26) and with b kept at 567; and per unit of extra Kp (T noise is linear in Kp).
(e) The tap's own HF content vs the live march in quiet cruise: an upper bound on any unmodelled HF torque.
"""
import math
import os
import sys

import numpy as np
from scipy import optimize, signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import frf as FRF  # noqa: E402
import oe_lib as O  # noqa: E402
import plib as P  # noqa: E402
import v294_plant as VP  # noqa: E402

OUT = []
FS = 100.0


def pr(s=""):
    print(s, flush=True)
    OUT.append(str(s))


def analytic_trim(f, c, fb_a=None, fb_b=None, kp=None, taper=254, fs=1000.0):
    """T_trim/om (T counts per deg/s, tap sign) of the linear 1 kHz lane (as p2_trim.analytic_trim, with overrides)."""
    z = np.exp(1j * 2 * np.pi * np.asarray(f, float) / fs)
    a = (c["fb_a"] if fb_a is None else fb_a) / 1024.0
    g = (c["fb_b"] if fb_b is None else fb_b) / 1024.0
    kp = c["kp_Y"][0] if kp is None else kp
    R = g * (1 - 1 / z) / (1 - a / z)
    Hout = (c["lag_b"] / 1024.0) * (1 + 1 / z) / 32.0 / (1 - (c["lag_a"] / 1024.0) / z)
    return (-8.0) * R * (-(kp / 256.0)) * (taper / 256.0) * Hout * (c["gain"] / 32768.0)


def tb_model(f, A, ft, zt):
    s = 2j * np.pi * f
    wt = 2 * np.pi * ft
    return -A * s / (1 + 2 * zt * s / wt + (s / wt) ** 2)


def main():
    d = P.load()
    c = VP.v294_cells()
    c = dict(c)
    c["kp_Y"] = [float(c["kp_Y"][0])]
    om, bar = d["om"], d["bar"]
    u = d["u"]
    uff = d["u_ff"]
    mrel = O.mask_relaxed(d) & (d["v"] > 0.3)
    runs = P.runs(mrel, min_len=256)
    f, nw, S = FRF.cross(dict(u=u, uff=uff, om=om, bar=bar), runs, 256, FS)
    pr("(a) T -> om above 5 Hz, relaxed hands-off engaged, %d windows of 2.56 s (u = -T, + LEFT)" % nw)
    Hd = FRF.H_dir(S, "u", "om")
    Hiv = FRF.H_iv(S, "uff", "u", "om")
    Ct = analytic_trim(f, c)                      # T per deg/s ; u = -T  =>  u/om = -Ct ; inverse-controller H = -1/Ct
    Hinv = -1.0 / Ct
    cd = FRF.coh(S, "u", "om")
    ci = FRF.coh(S, "uff", "om")
    pr("  %6s | %7s %6s | %7s %6s | %6s %6s | %8s %6s" % ("f Hz", "|Hdir|", "ph", "|-1/C|", "ph", "c_dir", "c_IV", "|HIV|", "ph"))
    for ff in (3, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 25, 30, 35, 40, 45):
        i = int(np.argmin(np.abs(f - ff)))
        pr("  %6.2f | %7.3f %6.0f | %7.3f %6.0f | %6.2f %6.2f | %8.3f %6.0f" % (
            f[i], abs(Hd[i]), np.degrees(np.angle(Hd[i])), abs(Hinv[i]), np.degrees(np.angle(Hinv[i])), cd[i], ci[i],
            abs(Hiv[i]), np.degrees(np.angle(Hiv[i]))))
    sel = (f >= 8) & (f <= 30)
    r = np.abs(Hd[sel]) / np.abs(Hinv[sel])
    dp = np.degrees(np.angle(Hd[sel] / Hinv[sel]))
    pr("  8-30 Hz: |Hdir|/|-1/C| median %.2f (IQR %.2f-%.2f), phase diff median %+.0f deg; IV coherence max %.2f -> %s" % (
        np.median(r), np.percentile(r, 25), np.percentile(r, 75), np.median(dp), ci[sel].max(),
        "the DIRECT HF estimate tracks the INVERSE CONTROLLER, not the plant; the IV has no HF coherence: T -> om above"
        " ~8 Hz is NOT identifiable from this drive" if ci[sel].max() < 0.3 else "see table"))
    # (b) torsion-bar mode
    pr("")
    pr("(b) om_m -> bar (hands-off: the bar is a pure output of the motor-side rate), direct FRF, fit 1-40 Hz coh-weighted")
    res_tb = {}
    for nm, mk in (("relaxed hands-off engaged", mrel), ("strict hands-off (|bar|<400) engaged", d["ho"] & (d["v"] > 0.3)),
                   ("NOT engaged, v>1, not pressed", (~d["eng"]) & (d["v"] > 1) & ~d["pressed"])):
        rr = P.runs(mk, min_len=256)
        if not rr:
            continue
        f2, nw2, S2 = FRF.cross(dict(om=om, bar=bar), rr, 256, FS)
        H = FRF.H_dir(S2, "om", "bar")
        cc = FRF.coh(S2, "om", "bar")
        s = (f2 >= 1.0) & (f2 <= 40.0) & (cc >= 0.3)
        w = cc[s] / (1 - np.minimum(cc[s], 0.95))

        def resid(p, sgn):
            e = np.log(sgn * tb_model(f2[s], math.exp(p[0]), math.exp(p[1]), math.exp(p[2]))) - np.log(H[s])
            return np.r_[np.sqrt(w) * e.real, np.sqrt(w) * np.angle(np.exp(1j * e.imag))]
        best = None
        a0 = math.log(max(abs(H[s][0]) / (2 * np.pi * f2[s][0]), 1e-6))
        for sgn in (+1, -1):
            for ft0 in (6.0, 9.0, 12.0, 16.0, 20.0):
                sol = optimize.least_squares(resid, [a0, math.log(ft0), math.log(0.1)], args=(sgn,),
                                             bounds=([a0 - 8, math.log(1.0), math.log(0.005)], [a0 + 8, math.log(60.0), math.log(3.0)]))
                if best is None or sol.cost < best[0].cost:
                    best = (sol, sgn)
        best, sgn_tb = best
        A, ft, zt = (math.exp(v) for v in best.x)
        A = sgn_tb * A
        # bootstrap over windows would need per-window spectra; report the fit and the coherence band
        pr("  %-38s %3d windows: A %.2f bar/(deg/s) at low f, f_t %.2f Hz, zeta_t %.3f ; coherent bins %d ; |H| peak at %.1f Hz" % (
            nm, nw2, A, ft, zt, s.sum(), f2[np.argmax(np.where((f2 > 2) & (f2 < 40), np.abs(H), 0))]))
        for ff in (2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 25, 30, 40):
            i = int(np.argmin(np.abs(f2 - ff)))
            mm = tb_model(np.array([f2[i]]), A, ft, zt)[0]
            pr("      %5.1f Hz |H| %8.2f ph %5.0f coh %.2f   model |H| %8.2f ph %5.0f" % (
                f2[i], abs(H[i]), np.degrees(np.angle(H[i])), cc[i], abs(mm), np.degrees(np.angle(mm))))
        res_tb[nm] = (A, ft, zt)
    # (c) rate noise floor
    pr("")
    pr("(c) RATE SENSOR NOISE FLOOR (x counts; 8 counts per deg/s; 0x18F carries x at full resolution, 100 Hz)")
    x = -d["wire"]
    still = (d["v"] < 0.05) & (~d["eng"]) & (np.abs(d["bar"]) < 150)
    rs = P.runs(still, min_len=200)
    xs = np.concatenate([x[a:b] - np.mean(x[a:b]) for a, b in rs]) if rs else np.array([0.0])
    ac1 = np.mean([np.corrcoef(x[a:b - 1], x[a + 1:b])[0, 1] for a, b in rs if np.std(x[a:b]) > 0]) if rs else np.nan
    vals, cnts = np.unique(np.concatenate([x[a:b] for a, b in rs]), return_counts=True) if rs else ([], [])
    pr("  standstill, not engaged, |bar|<150: %.0f s in %d runs ; x std %.3f counts (%.4f deg/s) ; lag-1 (10 ms) autocorr %.2f ;"
       " values %s" % (len(xs) / FS, len(rs), np.std(xs), np.std(xs) / 8, ac1,
                       dict(zip([int(v) for v in vals[np.argsort(-cnts)][:7]], [int(c_) for c_ in np.sort(cnts)[::-1][:7]]))))
    lpo = P.lp1(om, 1.0)
    quiet = O.mask_relaxed(d) & (np.abs(lpo) < 1.0) & (d["v"] > 3)
    rq = P.runs(quiet, min_len=256)
    fq, nq, Sq = FRF.cross(dict(x=x), rq, 256, FS)
    Pxx = np.real(Sq[("x", "x")])
    hf = (fq >= 15) & (fq <= 50)
    pr("  engaged quiet cruise (|LPF1Hz om| < 1 deg/s, v > 3): %d windows ; x PSD 15-50 Hz mean %.3f counts^2/Hz -> white-equivalent"
       " std at 100 Hz sampling %.3f counts" % (nq, np.mean(Pxx[hf]), math.sqrt(np.mean(Pxx[hf]) * 50.0)))
    for ff in (5, 10, 15, 20, 25, 30, 40, 49):
        i = int(np.argmin(np.abs(fq - ff)))
        pr("      x PSD at %4.1f Hz: %.3f counts^2/Hz" % (fq[i], Pxx[i]))
    sig_x = max(np.std(xs), 0.3)
    # (d) operand and torque noise through the byte-exact lane
    pr("")
    pr("(d) OPERAND / TORQUE NOISE: Lane294 at sp = 0 driven by x = round(N(0, sigma)) white at 1 kHz, 60 s per case")
    for sigma in (sig_x, 1.0, 2.0):
        pr("  sigma_x = %.2f counts" % sigma)
        pr("    %-28s %6s %6s | %8s | %7s %7s %7s %7s | %7s" % ("case", "a", "b", "r26 rms", "T rms", "5-10", "10-15", "15-20",
                                                              "20-30"))
        rng = np.random.default_rng(5)
        n = 60000
        xn = np.round(rng.normal(0.0, sigma, (1, n))).astype(np.int64)
        base_Ka = 567.0 / (1024 - 1011)
        for lab, fp, keepK in (("shipped 2.03 Hz", 2.033, True), ("pole 4 Hz, K_alpha kept", 4.0, True),
                               ("pole 8 Hz, K_alpha kept", 8.0, True), ("pole 16.5 Hz, K_alpha kept", 16.5, True),
                               ("pole 4 Hz, b 567 kept", 4.0, False), ("pole 8 Hz, b 567 kept", 8.0, False),
                               ("pole 16.5 Hz, b 567 kept", 16.5, False)):
            a = int(round(1024 * math.exp(-2 * math.pi * fp * 1e-3)))
            b = int(round(base_Ka * (1024 - a))) if keepK else 567
            ln = VP.Lane294(c, 1, fb_a=a, fb_b=b)
            T = np.zeros(n)
            R = np.zeros(n)
            for i in range(n):
                t_, r_ = ln.tick(xn[:, i], np.zeros(1, np.int64), np.full(1, 254, np.int64))
                T[i], R[i] = t_[0], r_[0]
            T = T[2000:] - np.mean(T[2000:])
            ff_, Pt = signal.welch(T, fs=1000.0, nperseg=4096)
            bands = []
            for lo, hi in ((5, 10), (10, 15), (15, 20), (20, 30)):
                mb = (ff_ >= lo) & (ff_ < hi)
                bands.append(math.sqrt(np.sum(Pt[mb]) * (ff_[1] - ff_[0])))
            pr("    %-28s %6d %6d | %8.3f | %7.3f %7.3f %7.3f %7.3f %7.3f" % (lab, a, b, np.std(R[2000:]), np.std(T), *bands))
    pr("  T noise is LINEAR in Kp (P = (E*Kp)>>8 before the lag): x2 Kp doubles every column above (floors aside).")
    # (e) the tap's HF content vs the live march in quiet cruise
    pr("")
    j = d["j100"]
    qt = quiet[j]
    rr = P.runs(qt & (np.diff(np.r_[d["t_tap"][0] - 0.02, d["t_tap"]]) < 0.03), min_len=128)
    ft_, nwt, St = FRF.cross(dict(tap=d["T_tap"], mod=P.quant(d["T1k_live"][d["tick_tap"]])), rr, 128, 50.0)
    Pt = np.real(St[("tap", "tap")])
    Pm = np.real(St[("mod", "mod")])
    res_ = d["T_tap"] - P.quant(d["T1k_live"][d["tick_tap"]])
    _, _, Sr = FRF.cross(dict(r=res_), rr, 128, 50.0)
    Pr = np.real(Sr[("r", "r")])
    df = ft_[1] - ft_[0]
    pr("(e) 427 tap vs the live march in engaged quiet cruise (%d windows of 2.56 s at 50 Hz): band rms, T counts" % nwt)
    for lo, hi in ((5, 10), (10, 15), (15, 20), (20, 25)):
        mb = (ft_ >= lo) & (ft_ < hi)
        pr("    %2d-%2d Hz: tap %.2f  march %.2f  residual %.2f   (the 8-count quantiser's white floor in this band: %.2f)" % (
            lo, hi, math.sqrt(np.sum(Pt[mb]) * df), math.sqrt(np.sum(Pm[mb]) * df), math.sqrt(np.sum(Pr[mb]) * df),
            math.sqrt(2 * (8 ** 2 / 12.0) * (hi - lo) / 25.0)))
    np.savez(os.path.join(HERE, "_scratch", "p6_hf.npz"), f=f, Hd=Hd, Hiv=Hiv, Hinv=Hinv, cd=cd, ci=ci)
    open(os.path.join(HERE, "p6_hf_noise_out.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
