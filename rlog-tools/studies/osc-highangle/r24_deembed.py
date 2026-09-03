# -*- coding: utf-8 -*-
"""studies/osc-highangle/r24_deembed.py -- SETTLE the r24-vs-servo dispute at the 7 Hz strong-turn episodes,
and DE-EMBED the r24 twist-derivative lane from the tap-identified plant so the two loops can be sized
SEPARATELY.  Subagent (deep analysis), 2026-09-03.

Deliberately STANDALONE: reads the npz caches directly and re-implements every transfer, so nothing here
inherits a constant from twist_taper_loop.py / kpflat_sizing.py / v280_map_profiles.py.

Sections
  A  per-episode complex demodulation at f0: amplitude and RELATIVE PHASE of wire rate, bar torque, tap T,
     0xE4 command; the measured plant G(f0) = rate/T straight off the wire (no parametric fit).
  B  r24 in closed form from the decompiled arithmetic, its phase re the wheel rate, the r24 return ratio,
     and the DE-EMBEDDED bare plant G0 = G / (1 + G*R).
  C  the discriminator: does f0 track Kp(idx)?  (servo crossover cycle) or not (column mode pumped by r24)?
  D  broadband B(f) = bar/rate over the high-angle stratum -> R(f) -> Bode of the r24 loop and of the
     servo loop with and without r24, at Kp as-is / 341 / 248, and 0xC6446 at 5244 / 3072 / 512.
  E  predicted in-episode ripple/level for the 2x3 build grid.

Run:  python r24_deembed.py     (needs analysis-2020accord/_scratch/cache/v280/r3{2,3,4}.npz)
"""
import os
import sys

import numpy as np
from scipy import signal

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")

FS = 100.0
CPD = 8.0                       # 0x18F rate wire counts per deg/s
TQ_RAW = 1.024                  # gp-0x4f60 = -(wire torque) * 1.024   (frame builder -(gp4f60*125>>7))

# ---- firmware constants, read from the kit's record and re-checked against the V280 rev 2 image below ----
A_FB, B_FB = 923, 1560          # feedback two-sample lag sum
OA, OB = 992, 507               # output lag
GAIN = 5346                     # 0xC6CD0
KD = 128
KP_X = np.array([0, 68, 112, 136, 208], float)
KP_Y = np.array([248, 512, 645, 696, 696], float)      # slot 7 @0xE5378
MAP_X = np.array([0, 12, 20, 24, 32, 64, 96, 128, 160, 240], float)
MAP_V280 = np.array([0, 52, 86, 103, 138, 275, 413, 550, 688, 1032], float)
R24_GAIN_Q10 = 5244             # 0xC6446 on V280 rev 2 (stock 512; Honda LERP ~3072 at creep)
R24_TAPS = 4                    # 0xC6C42, the backward-difference span in 1 kHz ticks
GP6752 = -1                     # assist polarity

# The 18 F7 episodes (|angle| >= 30, fdom >= 6 Hz) -- HIGHANGLE-r32-r33 / HIGHANGLE-r34 episode lists.
EPIS = {
    "r32": [(620.7, 3.8), (692.8, 2.8), (726.5, 1.7)],
    "r33": [(100.8, 1.6), (212.5, 1.4), (224.1, 1.1), (833.5, 3.6)],
    "r34": [(35.5, 1.5), (77.7, 1.2), (133.1, 2.1), (182.4, 4.1), (188.2, 1.1), (343.7, 1.6),
            (372.9, 1.6), (475.7, 3.5), (480.9, 3.8), (667.7, 1.7), (1003.6, 1.0)],
}
CONTROL = ("r34", 250.0, 14.0)          # the hands-on stalled control window


# ------------------------------------------------------------------------------------------------------
def load(tag):
    D = dict(np.load(os.path.join(CACHE, tag + ".npz")))
    t0 = D["t18"][0]
    T18 = D["t18"] - t0
    tg = np.arange(0.0, T18[-1], 1 / FS)
    g = dict(t=tg, tag=tag)
    g["rate"] = np.interp(tg, T18, D["rate"])                  # wire rate, counts (8/deg/s)
    g["bar"] = np.interp(tg, T18, D["tq"])                     # wire driver torque, counts
    g["sca"] = np.interp(tg, T18, D["sca"]) > 0.5
    g["ang"] = np.interp(tg, D["t14"] - t0, D["ang"])
    g["cmd"] = np.interp(tg, D["te4"] - t0, D["cmd"])
    g["req"] = np.interp(tg, D["te4"] - t0, D["req"]) > 0.5
    g["v"] = np.interp(tg, D["tcs"] - t0, D["vego"])
    g["eng"] = g["sca"] & g["req"]
    fld = ((D["b0"].astype(int) & 3) << 8) | D["b1"].astype(int)
    Tm = np.where(fld >= 512, -1.0, 1.0) * (fld & 511) * 8
    g["T"] = np.interp(tg, D["t1ab"] - t0, Tm)                 # CAN-427 delivered-torque tap, counts
    g["fld"] = fld
    return g


def demand_idx(cmd, bar_wire):
    """LIVE arms (twistloop 2026-09-03): setpoint taper 0xCB924/0xCB8B4 = 255 flat to byte 80, 0 at 112,
    i.e. flat to 2560 raw.  |tq| raw = |bar_wire| * 1.024."""
    S = np.clip(-4.0 * np.round(cmd), -16384, 16384)
    byte = np.minimum(np.abs(bar_wire) * TQ_RAW // 32, 255)
    taper = np.interp(byte, [32, 42, 80, 112], [255, 255, 255, 0])
    v = np.floor(np.floor(((taper * 255).astype(np.int64) & 0xFFFF) * S / 65536.0) / 64.0)
    v = np.clip(v, -240, 240)
    return np.abs(v)


def demod(x, t, f0):
    """Complex amplitude of x at f0 over the window (Hann-tapered), phase in the exp(+j2 pi f t) convention."""
    w = np.hanning(len(x))
    w = w / w.sum()
    z = np.sum((x - x.mean()) * w * np.exp(-2j * np.pi * f0 * t))
    return 2 * z                    # amplitude = |z|, phase = angle(z)


def d4(f, taps=R24_TAPS):
    """gp-0x4f62 = 0.5*(gp4f60[n] - gp4f60[n-taps]) at 1 kHz."""
    return 0.5 * (1 - np.exp(-2j * np.pi * f * taps / 1000.0))


def r24_from_bar(f):
    """r24 (aggregator counts) per wire-torque count, complex, at frequency f.
       gp4f60 = -1.024*bar_wire ; gp4f62 = d4 * gp4f60 ; scaled = *G/1024 ; r24 = gp6752 * scaled."""
    return GP6752 * (R24_GAIN_Q10 / 1024.0) * d4(f) * (-TQ_RAW)


def H_fb(f):
    z1 = np.exp(-2j * np.pi * f / 1000.0)
    return (1 + z1) * (B_FB / 1024.0) / (1 - (A_FB / 1024.0) * z1)


def H_lag(f):
    z1 = np.exp(-2j * np.pi * f / 1000.0)
    return (OB / 1024.0) / (1 - (OA / 1024.0) * z1) * (1 + z1) / 32.0


def C_ctrl(f, kp, kd=KD, m=178.0):
    """Controller: E (counts) -> T (counts), times the fb path (deg/s -> E counts).
       Returns L/G, i.e. counts of T per deg/s of wheel rate, with the sign of NEGATIVE feedback folded out."""
    z1 = np.exp(-2j * np.pi * f / 1000.0)
    pid = kp / 256.0 + (kd / 8.0) * (1 - z1)
    return pid * (m / 256.0) * H_lag(f) * (GAIN / 32768.0) * H_fb(f) * CPD * z1


def f0_refine(x, lo=5.5, hi=9.5):
    n = len(x)
    nfft = max(4096, 1 << int(np.ceil(np.log2(n * 8))))
    w = np.hanning(n)
    X = np.abs(np.fft.rfft((x - x.mean()) * w, nfft))
    fr = np.fft.rfftfreq(nfft, 1 / FS)
    m = (fr >= lo) & (fr <= hi)
    return float(fr[m][np.argmax(X[m])])


def episode_row(g, t0, dur):
    s, e = int(round(t0 * FS)), int(round((t0 + dur) * FS))
    sl = slice(s, e)
    t = g["t"][sl]
    rate, bar, T, cmd = g["rate"][sl], g["bar"][sl], g["T"][sl], g["cmd"][sl]
    f0 = f0_refine(rate)
    zr, zb, zT, zc = (demod(x, t, f0) for x in (rate, bar, T, cmd))
    idx = np.median(demand_idx(cmd, bar))
    kp = float(np.interp(idx, KP_X, KP_Y))
    Gw = zr / zT                                     # wire rate counts per T count  (= G*CPD)
    R = r24_from_bar(f0) * zb / zr                   # aggregator counts of r24 per wire rate count
    G0w = Gw / (1 + Gw * R)
    ret = G0w * R                                    # r24 loop return ratio (positive-feedback sign)
    Lsv = C_ctrl(f0, kp) * (Gw / CPD)                # servo loop gain with r24 CLOSED (uses measured G)
    Lsv0 = C_ctrl(f0, kp) * (G0w / CPD)              # servo loop gain on the BARE plant
    return dict(tag=g["tag"], t0=t0, dur=dur, f0=f0, idx=idx, kp=kp,
                v=float(np.mean(g["v"][sl])), ang=float(np.median(np.abs(g["ang"][sl]))),
                Arate=abs(zr) / CPD, Abar=abs(zb), AT=abs(zT), Acmd=abs(zc),
                Tlev=float(np.median(np.abs(T))), rl=abs(zT) / max(np.median(np.abs(T)), 1.0),
                ph_bar=np.degrees(np.angle(zb / zr)), ph_T=np.degrees(np.angle(zT / zr)),
                ph_cmd=np.degrees(np.angle(zc / zr)),
                Ar24=abs(r24_from_bar(f0) * zb), ph_r24=np.degrees(np.angle(r24_from_bar(f0) * zb / zr)),
                Gw=Gw, R=R, G0w=G0w, ret=ret, Lsv=Lsv, Lsv0=Lsv0)


def sec_A_B(rows):
    print("=" * 175)
    print("SECTION A/B -- per-episode complex demodulation at f0, and the r24 de-embedding.  Phases in degrees RE THE WIRE RATE (+ = leads).")
    print("=" * 175)
    hd = ("route  t0     dur  f0    idx  Kp  | rate  bar    T   T_p50  rip/L | ph(bar) ph(T) ph(cmd)| r24_amp ph(r24) |"
          "  |G|deg/s/ct  ang |  |R|  ang | r24 return ratio | L_servo(f0) | L_servo0(f0)")
    print(hd)
    for r in rows:
        print("%-5s %6.1f %4.1f %5.2f %5.0f %4.0f | %5.1f %6.0f %5.0f %5.0f %5.2f | %6.0f %5.0f %6.0f | %6.0f %6.0f | %8.4f %5.0f | %5.2f %5.0f | %5.2f @ %6.0f | %5.2f @ %6.0f | %5.2f @ %6.0f"
              % (r["tag"], r["t0"], r["dur"], r["f0"], r["idx"], r["kp"], r["Arate"], r["Abar"], r["AT"], r["Tlev"], r["rl"],
                 r["ph_bar"], r["ph_T"], r["ph_cmd"], r["Ar24"], r["ph_r24"],
                 abs(r["Gw"]) / CPD, np.degrees(np.angle(r["Gw"])), abs(r["R"]), np.degrees(np.angle(r["R"])),
                 abs(r["ret"]), np.degrees(np.angle(r["ret"])), abs(r["Lsv"]), np.degrees(np.angle(r["Lsv"])),
                 abs(r["Lsv0"]), np.degrees(np.angle(r["Lsv0"]))))
    med = lambda k: np.median([r[k] for r in rows])                      # noqa: E731
    cmed = lambda k: (np.median([abs(r[k]) for r in rows]), np.median([np.degrees(np.angle(r[k])) for r in rows]))  # noqa: E731
    print("-" * 175)
    print("MEDIAN (n=%d): f0 %.2f Hz | rate %.1f deg/s  bar %.0f  T %.0f  rip/L %.2f | ph(bar) %+.0f  ph(T) %+.0f  ph(cmd) %+.0f | r24 %.0f ct at %+.0f"
          % (len(rows), med("f0"), med("Arate"), med("Abar"), med("AT"), med("rl"),
             med("ph_bar"), med("ph_T"), med("ph_cmd"), med("Ar24"), med("ph_r24")))
    for k, lab in (("Gw", "G  (rate/T, r24 CLOSED)"), ("R", "R  (r24 per rate ct)"), ("G0w", "G0 (bare plant)"),
                   ("ret", "r24 RETURN RATIO G0*R"), ("Lsv", "L_servo (measured G)"), ("Lsv0", "L_servo on G0")):
        a, p = cmed(k)
        print("    %-26s |.| %8.4f   angle %+7.1f deg" % (lab, a, p))
    print("    r24 / T amplitude ratio  median %.2f     r24 projection on the rate  median %.2f x |r24|"
          % (np.median([r["Ar24"] / r["AT"] for r in rows]), np.median([np.cos(np.radians(r["ph_r24"])) for r in rows])))
    print("    T   projection on the rate  median %.2f x |T|   (negative = damping under the aggregator convention)"
          % np.median([np.cos(np.radians(r["ph_T"])) for r in rows]))
    print("    NET in-phase-with-rate counts: r24 %+.0f   T %+.0f   sum %+.0f"
          % (np.median([r["Ar24"] * np.cos(np.radians(r["ph_r24"])) for r in rows]),
             np.median([r["AT"] * np.cos(np.radians(r["ph_T"])) for r in rows]),
             np.median([r["Ar24"] * np.cos(np.radians(r["ph_r24"])) + r["AT"] * np.cos(np.radians(r["ph_T"])) for r in rows])))


# ------------------------------------------------------------------------------------------------------
def sec_C(rows):
    from scipy import stats
    print()
    print("=" * 175)
    print("SECTION C -- THE DISCRIMINATOR.  A servo crossover limit cycle must move f0 DOWN as Kp goes UP")
    print("(the kit's own model puts f_180 at 10.3 Hz for Kp 349 and 8.2 Hz for Kp 696).  A column mode")
    print("pumped by a rate-proportional lane sits at the structure's frequency and does NOT track Kp.")
    print("=" * 175)
    y = np.array([r["f0"] for r in rows])
    cols = dict(Kp=np.array([r["kp"] for r in rows]), idx=np.array([r["idx"] for r in rows]),
                v=np.array([r["v"] for r in rows]), ang=np.array([r["ang"] for r in rows]),
                Tlev=np.array([r["Tlev"] for r in rows]), rate=np.array([r["Arate"] for r in rows]),
                bar=np.array([r["Abar"] for r in rows]))
    n = len(y)
    print("  n = %d episodes;  f0 %.2f - %.2f Hz (median %.2f, sd %.3f)" % (n, y.min(), y.max(), np.median(y), y.std(ddof=1)))
    print("  %-6s %8s %8s %11s %11s   %s" % ("x", "r", "p(t)", "slope", "se", "predicted swing over the observed x range"))
    for k, x in cols.items():
        if x.std() == 0:
            continue
        rr = np.corrcoef(x, y)[0, 1]
        b, a = np.polyfit(x, y, 1)
        resid = y - (a + b * x)
        se = np.sqrt((resid @ resid) / (n - 2) / ((x - x.mean()) @ (x - x.mean())))
        p = 2 * (1 - stats.t.cdf(abs(b / se), n - 2))
        print("  %-6s %8.3f %8.3f %11.5f %11.5f   %+.2f Hz over %.0f..%.0f" % (k, rr, p, b, se, b * (x.max() - x.min()), x.min(), x.max()))
    X = np.column_stack([np.ones(n), cols["Kp"], cols["v"]])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    cov = (res @ res) / (n - 3) * np.linalg.inv(X.T @ X)
    print("  MULTIPLE f0 ~ 1 + Kp + v :  b_Kp = %+.5f (se %.5f, t %.2f)   b_v = %+.4f (se %.4f)"
          % (beta[1], np.sqrt(cov[1, 1]), beta[1] / np.sqrt(cov[1, 1]), beta[2], np.sqrt(cov[2, 2])))
    print("  SERVO-CYCLE PREDICTION for b_Kp, from the kit's own f_180 table (349 -> 696 gives 10.3 -> 8.2 Hz): %+.5f Hz per Kp count"
          % ((8.2 - 10.3) / (696 - 349)))
    print("  95%% CI on the measured b_Kp: %+.5f .. %+.5f"
          % (beta[1] - 2.16 * np.sqrt(cov[1, 1]), beta[1] + 2.16 * np.sqrt(cov[1, 1])))


def stratum_mask(g, vmax=10.0, angmin=30.0):
    return g["eng"] & (g["v"] <= vmax) & (np.abs(g["ang"]) >= angmin)


def sec_D(gs):
    print()
    print("=" * 175)
    print("SECTION D -- broadband B(f) = bar / wire-rate in the loaded high-angle stratum (Welch, engaged, v<=10, |ang|>=30)")
    print("=" * 175)
    nper = 256
    Sxy = Sxx = Syy = None
    ntot = 0
    f = None
    for g in gs.values():
        m = stratum_mask(g)
        d = np.diff(np.r_[0, m.astype(int), 0])
        for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
            if b - a < nper:
                continue
            x = signal.detrend(g["rate"][a:b])
            yv = signal.detrend(g["bar"][a:b])
            f, pxy = signal.csd(x, yv, fs=FS, nperseg=nper)
            _, pxx = signal.welch(x, fs=FS, nperseg=nper)
            _, pyy = signal.welch(yv, fs=FS, nperseg=nper)
            w = b - a
            Sxy = pxy * w if Sxy is None else Sxy + pxy * w
            Sxx = pxx * w if Sxx is None else Sxx + pxx * w
            Syy = pyy * w if Syy is None else Syy + pyy * w
            ntot += w
    B = Sxy / Sxx
    coh = np.abs(Sxy) ** 2 / (Sxx * Syy)
    print("  stratum: %.0f s of engaged high-angle frames" % (ntot / FS))
    print("  %-7s %10s %8s %8s | %9s %8s | %s" % ("f Hz", "|B| ct/ct", "ph(B)", "coh", "|R|", "ph(R)", "r24 counts per deg/s of rate"))
    for fi in (2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 25, 30):
        i = int(np.argmin(np.abs(f - fi)))
        Rv = r24_from_bar(f[i]) * B[i]
        print("  %-7.2f %10.2f %8.0f %8.2f | %9.3f %8.0f | %.2f"
              % (f[i], abs(B[i]), np.degrees(np.angle(B[i])), coh[i], abs(Rv), np.degrees(np.angle(Rv)), abs(Rv) * CPD))
    return f, B, coh


def plant_fit(f):
    """Kit fit 1 (KPFLAT-SIZING sec 2, pole+delay, driver-torque IV): K 0.382, pole 0.80 Hz, delay 8.4 ms.
       G in deg/s per T count, r24 CLOSED (it is what the tap identifies)."""
    return 0.382 / (1 + 1j * f / 0.80) * np.exp(-2j * np.pi * f * 0.0084)


def margins(L, f):
    mag, ph = np.abs(L), np.unwrap(np.angle(L))
    pm = gm = fc = f180 = np.nan
    i = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0]
    if len(i):
        k = i[0]
        fc = float(np.interp(0.0, [np.log(mag[k + 1]), np.log(mag[k])], [f[k + 1], f[k]]))
        pm = float(np.degrees(np.interp(fc, f, ph)) + 180)
    j = np.where((ph[:-1] > -np.pi) & (ph[1:] <= -np.pi))[0]
    if len(j):
        k = j[0]
        f180 = float(np.interp(-np.pi, [ph[k + 1], ph[k]], [f[k + 1], f[k]]))
        gm = float(1.0 / np.interp(f180, f, mag))
    return pm, gm, fc, f180


def sec_E(f_grid, B, use_measured_G=None):
    print()
    print("=" * 175)
    print("SECTION E -- the two loops on the DE-EMBEDDED bare plant.  r24 is a POSITIVE rate feedback:")
    print("  rate = G0*(T + r24),  r24 = R*rate,  T = -C*rate + setpoint   =>   char. eq.  1 + G0*C - G0*R = 0")
    print("  The tap-identified plant G = rate/T = G0/(1 - G0*R) ALREADY CONTAINS r24 at 5244.")
    print("=" * 175)
    ff = np.arange(0.5, 40.0, 0.02)
    Bi = np.interp(ff, f_grid, B.real) + 1j * np.interp(ff, f_grid, B.imag)
    Gw = plant_fit(ff) * CPD                      # wire-rate counts per T count, r24 at 5244 closed
    R5 = GP6752 * (5244 / 1024.0) * d4(ff) * (-TQ_RAW) * Bi
    G0w = Gw / (1 + Gw * R5)
    i7 = int(np.argmin(np.abs(ff - 7.0)))
    print("  at 7.0 Hz:  identified G %.4f deg/s/ct @ %+.0f | R(5244) %.3f @ %+.0f | DE-EMBEDDED G0 %.4f deg/s/ct @ %+.0f"
          % (abs(Gw[i7]) / CPD, np.degrees(np.angle(Gw[i7])), abs(R5[i7]), np.degrees(np.angle(R5[i7])),
             abs(G0w[i7]) / CPD, np.degrees(np.angle(G0w[i7]))))
    for r24g in (5244, 3072, 512, 0):
        Rf = GP6752 * (r24g / 1024.0) * d4(ff) * (-TQ_RAW) * Bi
        Gw_new = G0w / (1 - G0w * Rf)
        print()
        print("  === 0xC6446 = %-5s ===  (V280 rev 2 flies 5244; the cell's stock value is 512; Honda's LERP arm ~3072 at creep)" % r24g)
        print("      7 Hz: r24 return ratio G0*R = %.3f @ %+.0f deg   |   plant the servo sees: %.4f deg/s/ct @ %+.0f deg"
              % (abs((G0w * Rf)[i7]), np.degrees(np.angle((G0w * Rf)[i7])), abs(Gw_new[i7]) / CPD, np.degrees(np.angle(Gw_new[i7]))))
        pm, gm, fc, f180 = margins(-(G0w * Rf), ff)
        print("      r24 LOOP ALONE (servo off; char eq 1 - G0*R = 0): GM %s @ %s Hz  [GM < 1x = the twist loop self-oscillates]"
              % (("%.2fx" % gm) if np.isfinite(gm) else "n/a (never crosses -180)", ("%.2f" % f180) if np.isfinite(f180) else "n/a"))
        for kp in (696, 645, 512, 341, 295, 248):
            L = C_ctrl(ff, kp) * (Gw_new / CPD)
            pm, gm, fc, f180 = margins(L, ff)
            Ms = np.abs(1 / (1 + L))
            print("      Kp %3d :  PM %+6.1f deg @ %5.2f Hz | GM %5.2fx @ %5.2f Hz | |L(7Hz)| %5.2f | Ms %5.2f @ %5.2f Hz"
                  % (kp, pm, fc, gm, f180, abs(L[i7]), float(Ms.max()), float(ff[np.argmax(Ms)])))




# ======================================================================================================
# SECTION F -- what actually predicts the ripple: the twist-loop gain |R|, or Kp?
# ======================================================================================================
def sec_F(rows):
    from scipy import stats
    print()
    print("=" * 175)
    print("SECTION F -- WHICH LOOP GAIN PREDICTS THE CYCLE?  The servo hypothesis says the cycle strength")
    print("tracks Kp (or K_eff).  The twist hypothesis says it tracks |R| = the r24 counts fed back per")
    print("count of wheel rate, which is set by the bar-per-rate ratio |B| and NOT by Kp at all.")
    print("=" * 175)
    n = len(rows)
    R = np.array([abs(r["R"]) for r in rows])
    B = np.array([r["Abar"] / (r["Arate"] * CPD) for r in rows])
    Kp = np.array([r["kp"] for r in rows])
    for name, y in (("tap ripple/level", np.array([r["rl"] for r in rows])),
                    ("rate ripple deg/s", np.array([r["Arate"] for r in rows])),
                    ("r24 return |G0*R|", np.array([abs(r["ret"]) for r in rows])),
                    ("f0 Hz", np.array([r["f0"] for r in rows]))):
        print("  %-20s" % name, end="")
        for xn, x in (("|R|", R), ("|B|", B), ("Kp", Kp)):
            rr = np.corrcoef(x, y)[0, 1]
            p = 2 * (1 - stats.t.cdf(abs(rr) * np.sqrt((n - 2) / max(1 - rr ** 2, 1e-9)), n - 2))
            print("   vs %-4s r %+6.3f (p %.4f)" % (xn, rr, p), end="")
        print()
    print()
    print("  Partial: ripple/level ~ 1 + |R| + Kp")
    y = np.array([r["rl"] for r in rows])
    X = np.column_stack([np.ones(n), R, Kp])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    cov = (res @ res) / (n - 3) * np.linalg.inv(X.T @ X)
    for i, nm in enumerate(("const", "|R|", "Kp")):
        print("      b_%-6s %+10.5f  se %9.5f  t %+6.2f" % (nm, beta[i], np.sqrt(cov[i, i]), beta[i] / np.sqrt(cov[i, i])))
    print("      R^2 = %.3f" % (1 - res @ res / ((y - y.mean()) @ (y - y.mean()))))


# ======================================================================================================
# SECTION G -- hands-ON vs hands-light, and manual vs engaged, at high angle: does the 7 Hz line need
#              (a) a light hand on the wheel and (b) LKAS engaged?
# ======================================================================================================
def band_amp(x, lo, hi):
    if len(x) < 64:
        return np.nan
    sos = signal.butter(4, [lo, hi], btype="bandpass", fs=FS, output="sos")
    return float(np.sqrt(2) * signal.sosfiltfilt(sos, signal.detrend(x)).std())


def sec_G(gs):
    print()
    print("=" * 175)
    print("SECTION G -- the 7 Hz rate line by REGIME (1 s windows, |angle| >= 30, v <= 10).  hands-on =")
    print("median |driver torque| >= 1216 raw wire counts in the window; the r24 5244 arm is ENGAGED-ONLY.")
    print("=" * 175)
    print("  %-6s %-24s %6s %10s %10s %10s %10s" % ("route", "regime", "n win", "rate7 p50", "rate7 p90", "bar7 p50", "|B| p50"))
    for tag, g in gs.items():
        base = (np.abs(g["ang"]) >= 30) & (g["v"] <= 10)
        for lab, m in (("ENGAGED hands-light", base & g["eng"]),
                       ("ENGAGED hands-ON", base & g["eng"]),
                       ("MANUAL (disengaged)", base & ~g["eng"])):
            w = int(FS)
            r7, b7, bb = [], [], []
            for a in range(0, len(g["t"]) - w, w // 2):
                sl = slice(a, a + w)
                if not m[sl].all():
                    continue
                tqm = np.median(np.abs(g["bar"][sl])) * TQ_RAW
                if lab.endswith("hands-ON") and tqm < 1216:
                    continue
                if lab.endswith("hands-light") and tqm >= 1216:
                    continue
                ar = band_amp(g["rate"][sl], 6.0, 8.5) / CPD
                ab = band_amp(g["bar"][sl], 6.0, 8.5)
                r7.append(ar); b7.append(ab); bb.append(ab / max(ar * CPD, 1e-6))
            if not r7:
                print("  %-6s %-24s %6d %10s" % (tag, lab, 0, "-"))
                continue
            print("  %-6s %-24s %6d %10.2f %10.2f %10.0f %10.2f"
                  % (tag, lab, len(r7), np.median(r7), np.percentile(r7, 90), np.median(b7), np.median(bb)))


# ======================================================================================================
# SECTION H -- parametric B(f), the de-embedded bare plant G0(f), and rigorous Nyquist on both loops
# ======================================================================================================
def fit_B(f, B, coh, lo=4.5, hi=9.0):
    """B(s) = K * s / (1 + 2*zeta*s/wn + (s/wn)^2)   (an inertia term with the free-wheel torsion-bar mode)."""
    from scipy.optimize import least_squares
    m = (f >= lo) & (f <= hi)
    fw, Bw, cw = f[m], B[m], np.sqrt(coh[m])

    def model(p):
        K, fn, z = p
        s = 2j * np.pi * fw
        wn = 2 * np.pi * fn
        return K * s / (1 + 2 * z * s / wn + (s / wn) ** 2)

    def resid(p):
        d = (model(p) - Bw) * cw
        return np.r_[d.real, d.imag]

    best = None
    for fn0 in (8.0, 9.0, 10.0, 12.0):
        for z0 in (0.05, 0.15, 0.3):
            r = least_squares(resid, [-0.2, fn0, z0], bounds=([-5, 6.0, 0.01], [5, 25.0, 1.5]))
            if best is None or r.cost < best.cost:
                best = r
    K, fn, z = best.x
    print("  B(f) fit over %.1f-%.1f Hz (coherence-weighted): K %+.4f, fn %.2f Hz, zeta %.3f   rms resid %.2f ct/ct"
          % (lo, hi, K, fn, z, np.sqrt(2 * best.cost / m.sum())))
    return lambda ff: K * (2j * np.pi * ff) / (1 + 2 * z * (2j * np.pi * ff) / (2 * np.pi * fn) + ((2j * np.pi * ff) / (2 * np.pi * fn)) ** 2)


def encirclements(L):
    """Net clockwise encirclements of -1 by L(jw) for w: 0 -> inf, mirrored (real system)."""
    z = L + 1.0
    ang = np.unwrap(np.angle(z))
    return -(ang[-1] - ang[0]) / np.pi          # x2 for the mirrored half, /2pi  ->  /pi


def sec_H(f_grid, B, coh, extra_delay_ms=0.0):
    print()
    print("=" * 175)
    print("SECTION H -- parametric B(f), the de-embedded bare plant G0(f), and NYQUIST on both loops.")
    print("  rate = G0*(T + r24),  r24 = R*rate,  T = -C*rate  =>  char eq  1 + G0*C - G0*R = 0")
    print("  L_tot = G0*C - G0*R is open-loop stable, so closed-loop stability <=> 0 net encirclements of -1.")
    print("  extra plant delay applied to the kit's fit 1: %.1f ms" % extra_delay_ms)
    print("=" * 175)
    Bf = fit_B(f_grid, B, coh)
    ff = np.arange(0.2, 60.0, 0.01)
    Gw = plant_fit(ff) * CPD * np.exp(-2j * np.pi * ff * extra_delay_ms / 1000.0)
    R5 = GP6752 * (5244 / 1024.0) * d4(ff) * (-TQ_RAW) * Bf(ff)
    G0w = Gw / (1 + Gw * R5)
    print()
    print("  %-7s %14s %8s | %10s %8s | %14s %8s | %s" % ("f Hz", "|G| id", "ph", "|R| 5244", "ph", "|G0| bare", "ph", "|G0*R| 5244"))
    for fi in (2, 3, 4, 5, 6, 7, 7.3, 8, 9, 10, 12, 15, 20):
        i = int(np.argmin(np.abs(ff - fi)))
        print("  %-7.2f %14.4f %8.0f | %10.3f %8.0f | %14.4f %8.0f | %.3f"
              % (ff[i], abs(Gw[i]) / CPD, np.degrees(np.angle(Gw[i])), abs(R5[i]), np.degrees(np.angle(R5[i])),
                 abs(G0w[i]) / CPD, np.degrees(np.angle(G0w[i])), abs((G0w * R5)[i])))
    enc0 = encirclements(-(Gw * R5))
    print("  CONSISTENCY: encirclements of -1 by (-G*R) with the IDENTIFIED G = %.2f  (must be 0 for the de-embedded G0 to be a stable plant)" % enc0)

    print()
    print("  %-8s %-6s | %-9s | %-38s | %s" % ("0xC6446", "Kp", "N* (DF)", "linear: enc / Ms / f_peak / PM / GM", "verdict"))
    for r24g in (5244, 3072, 2048, 1024, 512, 0):
        Rf = GP6752 * (r24g / 1024.0) * d4(ff) * (-TQ_RAW) * Bf(ff)
        i7 = int(np.argmin(np.abs(ff - 7.3)))
        ret = (G0w * Rf)[i7]
        print("  --- 0xC6446 = %-5d : r24 return ratio at 7.3 Hz = %.3f @ %+.0f deg ---" % (r24g, abs(ret), np.degrees(np.angle(ret))))
        for kp in (696, 645, 512, 425, 341, 295, 248, 0):
            Ns = np.nan
            for N in np.arange(1.0, 0.04, -0.01):
                LN = G0w * (C_ctrl(ff, kp * N) - Rf) if kp else -G0w * Rf
                if abs(encirclements(LN)) > 0.5:
                    Ns = N
                    break
            L = G0w * (C_ctrl(ff, kp) - Rf) if kp else -G0w * Rf
            S = np.abs(1 / (1 + L))
            pm, gm, fc, f180 = margins(L, ff)
            e = encirclements(L)
            verdict = "LIMIT CYCLE (N*=%.2f)" % Ns if np.isfinite(Ns) else ("no cycle; ring Ms %.1f @ %.1f Hz" % (S.max(), ff[np.argmax(S)]))
            print("      Kp %3d : enc %+.2f  Ms %6.2f @ %5.2f Hz  PM %+6.1f @ %5.2f  GM %5.2fx @ %5.2f | %s"
                  % (kp, e, S.max(), ff[np.argmax(S)], pm, fc, gm, f180, verdict))
    return Bf, G0w, ff




# ======================================================================================================
# SECTION I -- THE CONVENTION-FREE LOOP DECOMPOSITION.
#
#   Both lanes are added with UNIT COEFFICIENTS into the same 1 kHz sum (FUN_0003aa2c: the LKAS lane
#   arrives as gp-0x6b4c, r24 as the clamped iVar16, `iVar19 = ... + iVar21 + iVar16`, then clamp
#   +-0x2800 -> gp-0x6b94).  So  drive = T + r24  in ONE set of counts, and
#
#        rate = G0 * drive        with G0 the BARE plant from that node to the 0x18F rate.
#
#   A sustained sinusoid at f0 requires the return ratio L_tot = (drive/rate) * G0 = 1 exactly -- which
#   makes G0 = rate/(T + r24) a DIRECT MEASUREMENT at f0, with no plant fit and no sign convention.
#   Then       L_r24 = (r24/rate)*G0        L_servo = (T/rate)*G0        L_r24 + L_servo = 1.
# ======================================================================================================
def sec_I(rows):
    print()
    print("=" * 175)
    print("SECTION I -- LOOP DECOMPOSITION AT f0, convention-free.  L_r24 + L_servo = 1 by construction;")
    print("the split says which lane carries the mode.  |L| > 1 alone = that lane could sustain it on its own")
    print("if its phase reached 0; |L| < 1 alone = it cannot, at this frequency, whatever its phase.")
    print("=" * 175)
    print("  %-5s %6s %5s | %-22s | %-20s | %-20s | %s"
          % ("route", "t0", "f0", "G0 = rate/(T+r24)", "L_r24", "L_servo", "T/rate vs firmware C(f)"))
    out = []
    for r in rows:
        w = r["Arate"] * CPD                                   # wire-rate counts, phase 0 by definition
        zr24 = r["Ar24"] * np.exp(1j * np.radians(r["ph_r24"]))
        zT = r["AT"] * np.exp(1j * np.radians(r["ph_T"]))
        G0 = w / (zT + zr24)
        L24 = (zr24 / w) * G0
        Lsv = (zT / w) * G0
        Cfw = C_ctrl(r["f0"], r["kp"]) / CPD                   # T counts per wire-rate count (firmware)
        out.append(dict(f0=r["f0"], G0=G0, L24=L24, Lsv=Lsv, Tw=zT / w, Cfw=Cfw, kp=r["kp"], r=r))
        print("  %-5s %6.1f %5.2f | %8.4f @ %+6.1f deg | %6.3f @ %+6.1f | %6.3f @ %+6.1f | meas %5.2f @ %+6.0f  fw %5.2f @ %+6.0f"
              % (r["tag"], r["t0"], r["f0"], abs(G0) / CPD, np.degrees(np.angle(G0)),
                 abs(L24), np.degrees(np.angle(L24)), abs(Lsv), np.degrees(np.angle(Lsv)),
                 abs(zT / w), np.degrees(np.angle(zT / w)), abs(Cfw), np.degrees(np.angle(-Cfw))))
    m = lambda k: (np.median([abs(o[k]) for o in out]), np.median([np.degrees(np.angle(o[k])) for o in out]))  # noqa: E731
    print("-" * 175)
    for k, lab in (("G0", "G0 = rate/(T+r24)  [wire ct per aggregator ct]"), ("L24", "L_r24"), ("Lsv", "L_servo"),
                   ("Tw", "T/rate measured"), ("Cfw", "-C(f) firmware chain, live m=178")):
        a, p = m(k)
        print("    MEDIAN %-46s %8.4f  @ %+7.1f deg" % (lab, a, p))
    print()
    print("    => at f0 the servo lane alone has |L| = %.2f (median) and is %.0f deg from the critical point;"
          % (m("Lsv")[0], abs(m("Lsv")[1])))
    print("       r24 alone has |L| = %.2f and is %.0f deg from it.  Neither closes alone; their SUM is 1 by construction."
          % (m("L24")[0], abs(m("L24")[1])))
    return out


def sec_J(out):
    """G0 over 6.5-7.8 Hz from the 18 direct measurements, then the build grid."""
    from scipy import stats
    print()
    print("=" * 175)
    print("SECTION J -- the BARE plant G0 across the episode band, and the predicted loop for each build")
    print("=" * 175)
    f = np.array([o["f0"] for o in out])
    lg = np.log(np.array([abs(o["G0"]) for o in out]) / CPD)
    ph = np.array([np.degrees(np.angle(o["G0"])) for o in out])
    for nm, y in (("ln|G0|", lg), ("phase(G0) deg", ph)):
        b, a = np.polyfit(f, y, 1)
        rr = np.corrcoef(f, y)[0, 1]
        p = 2 * (1 - stats.t.cdf(abs(rr) * np.sqrt(16 / max(1 - rr ** 2, 1e-9)), 16))
        print("    %-16s = %+8.4f * f %+8.4f    (r %+.2f, p %.3f) -> at 7.0 Hz %8.4f" % (nm, b, a, rr, p, a + b * 7.0))
    bl, al = np.polyfit(f, lg, 1)
    bp, ap = np.polyfit(f, ph, 1)

    def G0f(ff):
        return np.exp(al + bl * ff) * CPD * np.exp(1j * np.radians(ap + bp * ff))

    # r24's own transfer, measured: R(f) = r24/rate, from the same episodes
    R = np.array([o["r"]["Ar24"] / (o["r"]["Arate"] * CPD) * np.exp(1j * np.radians(o["r"]["ph_r24"])) for o in out])
    blr, alr = np.polyfit(f, np.log(np.abs(R)), 1)
    bpr, apr = np.polyfit(f, np.degrees(np.angle(R)), 1)

    def Rf(ff, gain=5244.0):
        return (gain / 5244.0) * np.exp(alr + blr * ff) * np.exp(1j * np.radians(apr + bpr * ff))

    print("    R(f) = r24/rate:  |R| = exp(%+.4f f %+.4f), phase = %+.2f f %+.2f deg" % (blr, alr, bpr, apr))
    print()
    ff = np.arange(5.5, 9.5, 0.005)
    print("    Interpolating BOTH transfers only inside the measured band 6.6-7.8 Hz (extrapolation to 5.5/9.5 Hz is BELIEF).")
    print()
    print("    %-9s %-6s | %-30s | %-30s | %s" % ("0xC6446", "Kp", "L_tot peak |L| @ f", "closest approach to 1+j0", "verdict at 5.5-9.5 Hz"))
    for g in (5244, 3072, 2048, 1024, 512):
        for kp in (696, 645, 512, 341, 295, 248):
            L = Rf(ff, g) * G0f(ff) - C_ctrl(ff, kp) * G0f(ff) / CPD
            i = int(np.argmin(np.abs(L - 1.0)))
            j = int(np.argmax(np.abs(L)))
            d = abs(L[i] - 1.0)
            v = "OSCILLATES" if d < 0.10 else ("marginal" if d < 0.35 else "no sustained mode")
            print("    %-9d %-6d | %6.3f @ %5.2f Hz              | %6.3f  (at %5.2f Hz, L = %5.2f @ %+6.1f) | %s"
                  % (g, kp, abs(L[j]), ff[j], d, ff[i], abs(L[i]), np.degrees(np.angle(L[i])), v))
        print()
    print("    Ripple scaling, at the flown operating point (linearised about the measured cycle):")
    print("      the closed-loop gain from a broadband road input to the 7.3 Hz rate is 1/|1 - L_tot|.")
    print("      %-9s %-6s %12s %14s" % ("0xC6446", "Kp", "|1 - L_tot|", "ring gain 1/|1-L|"))
    i7 = int(np.argmin(np.abs(ff - 7.3)))
    for g in (5244, 3072, 2048, 1024, 512):
        for kp in (696, 341, 248):
            L = Rf(ff, g)[i7] * G0f(ff[i7]) - C_ctrl(ff[i7], kp) * G0f(ff[i7]) / CPD
            print("      %-9d %-6d %12.3f %14.2f" % (g, kp, abs(1 - L), 1 / max(abs(1 - L), 1e-3)))




# ======================================================================================================
# SECTION K -- THE PLANT-FREE IDENTITY, THE DECISION THRESHOLD, AND THE BUILD GRID
#
#   Because both lanes sum with unit coefficients into ONE node and the plant from that node to the
#   measured rate is common to both, the plant CANCELS:
#
#        L_servo = zT / (zT + zr24)        L_r24 = zr24 / (zT + zr24)        L_servo + L_r24 = 1
#
#   No plant fit, no aggregator sign convention, no units.  |L_lane| > 1 means that lane's own return
#   ratio exceeds unity at f0: it could sustain the mode by itself if its phase reached the critical
#   point.  |L_lane| < 1 means it could NOT, at this frequency, whatever its phase.
# ======================================================================================================
def sec_K(rows):
    print()
    print("=" * 175)
    print("SECTION K -- plant-free split, the r24 amplitude that flips the verdict, and the build grid")
    print("=" * 175)
    print("  %-5s %6s %5s | %6s %6s | %8s %8s | %10s | %12s | %s"
          % ("route", "t0", "f0", "|T|", "|r24|", "L_servo", "L_r24", "|T+r24|", "r24 flip thr", "verdict"))
    thrs, ls, lr = [], [], []
    for r in rows:
        zT = r["AT"] * np.exp(1j * np.radians(r["ph_T"]))
        zr = r["Ar24"] * np.exp(1j * np.radians(r["ph_r24"]))
        tot = zT + zr
        Ls, Lr = zT / tot, zr / tot
        # |L_servo| = 1  <=>  |zr| = -2|zT| cos(angle(zr)-angle(zT))
        c = np.cos(np.angle(zr) - np.angle(zT))
        thr = -2 * abs(zT) * c
        thrs.append(thr); ls.append(abs(Ls)); lr.append(abs(Lr))
        print("  %-5s %6.1f %5.2f | %6.0f %6.0f | %5.2f@%+4.0f %5.2f@%+4.0f | %10.0f | %12.0f | %s"
              % (r["tag"], r["t0"], r["f0"], abs(zT), abs(zr), abs(Ls), np.degrees(np.angle(Ls)),
                 abs(Lr), np.degrees(np.angle(Lr)), abs(tot), thr,
                 "r24 is the lane above unity" if abs(Lr) > 1 >= abs(Ls) else
                 ("servo above unity" if abs(Ls) > 1 else "neither")))
    print("-" * 175)
    print("  |L_servo| : median %.2f, range %.2f-%.2f ; ABOVE 1 on %d of %d episodes"
          % (np.median(ls), min(ls), max(ls), sum(x > 1 for x in ls), len(ls)))
    print("  |L_r24|   : median %.2f, range %.2f-%.2f ; ABOVE 1 on %d of %d episodes"
          % (np.median(lr), min(lr), max(lr), sum(x > 1 for x in lr), len(lr)))
    print("  r24 amplitude at which the verdict FLIPS (|L_servo| = 1): median %.0f counts (range %.0f-%.0f);"
          % (np.median(thrs), min(thrs), max(thrs)))
    print("     measured r24 median %.0f counts -> margin x%.2f ; equivalent 0xC6446 threshold = %.0f (flown 5244)"
          % (np.median([r["Ar24"] for r in rows]), np.median([r["Ar24"] for r in rows]) / np.median(thrs),
             5244 * np.median(thrs) / np.median([r["Ar24"] for r in rows])))

    # ---- build grid, linearised about the measured cycle at f0 (EXACT at f0: no extrapolation) ----
    print()
    print("  BUILD GRID -- L_tot(new) = kappa * L_servo + alpha * L_r24, evaluated at the measured f0 of each")
    print("  episode and then pooled.  kappa = pid(Kp_new,N=1) / pid_eff(Kp_now, N), alpha = gain_new/5244.")
    print("  pid(Kp,N) = N*Kp/256 + (Kd/8)*(1 - z^-1) at f0.  N = the P clamp's describing-function gain now.")
    print()
    for N in (1.00, 0.70):
        print("  --- assuming the P clamp's present describing-function gain N = %.2f ---" % N)
        print("    %-9s %-6s | %-24s | %-14s | %s" % ("0xC6446", "Kp", "L_tot at f0 (pooled median)", "|1 - L_tot|", "reading"))
        for g in (5244, 3072, 2048, 1024, 512):
            for kp in (696, 645, 512, 341, 295, 248):
                vals = []
                for r in rows:
                    zT = r["AT"] * np.exp(1j * np.radians(r["ph_T"]))
                    zr = r["Ar24"] * np.exp(1j * np.radians(r["ph_r24"]))
                    tot = zT + zr
                    z1 = np.exp(-2j * np.pi * r["f0"] / 1000.0)
                    dpart = (KD / 8.0) * (1 - z1)
                    pid_now = N * r["kp"] / 256.0 + dpart
                    pid_new = kp / 256.0 + dpart
                    kappa = pid_new / pid_now
                    vals.append(kappa * (zT / tot) + (g / 5244.0) * (zr / tot))
                L = np.median([abs(v) for v in vals]) * np.exp(1j * np.radians(np.median([np.degrees(np.angle(v)) for v in vals])))
                q = 1 / max(abs(1 - L), 1e-3)
                rd = ("SUSTAINS the cycle" if abs(L) >= 0.99 and abs(np.degrees(np.angle(L))) < 25 else
                      ("cycle stops; ring gain %.1f" % q))
                print("    %-9d %-6d | %6.3f @ %+6.1f deg        | %14.3f | %s" % (g, kp, abs(L), np.degrees(np.angle(L)), abs(1 - L), rd))
            print()


def main():
    gs = {t: load(t) for t in ("r32", "r33", "r34")}
    rows = [episode_row(gs[t], a, b) for t in ("r32", "r33", "r34") for a, b in EPIS[t]]
    sec_A_B(rows)
    print()
    c = episode_row(gs["r34"], CONTROL[1], CONTROL[2])
    print("  CONTROL (r34 250.0 s, 14 s hands-ON stalled window, no 7 Hz line):")
    print("    f0 %.2f  rate %.1f deg/s  bar %.0f  T %.0f (level %.0f, rip/L %.2f)  ph(bar) %+.0f  ph(T) %+.0f  r24 %.0f ct @ %+.0f"
          % (c["f0"], c["Arate"], c["Abar"], c["AT"], c["Tlev"], c["rl"], c["ph_bar"], c["ph_T"], c["Ar24"], c["ph_r24"]))
    sec_C(rows)
    f, B, coh = sec_D(gs)
    sec_F(rows)
    sec_G(gs)
    sec_H(f, B, coh, extra_delay_ms=0.0)
    o = sec_I(rows)
    sec_J(o)
    sec_K(rows)


if __name__ == "__main__":
    main()
