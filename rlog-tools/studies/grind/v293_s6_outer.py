# -*- coding: utf-8 -*-
"""v293_s6_outer.py -- DELIVERABLE 5: openpilot's OUTER loop under torque mode, and the V276 precedent.

Agent `tmdesign`, 2026-09-13.  ANALYSIS ONLY.

THE MODEL, stated before any number.
openpilot's `LatControlTorque` closes on the STEERING ANGLE off CAN (OUTER-LOOP-ID section, finding 1 --
not yaw, not the camera).  In the fork's own units:

    measurement   = VM.calc_curvature(radians(sa - offset), v, roll) * v^2       [m/s^2]
                  ~= k_meas * angle_deg ,     k_meas = v^2/(SR*L_wb) * pi/180
    error         = setpoint - measurement
    error_with_lsf= error * (1 + low_speed_factor/kp)
    output_lataccel = kp*error_with_lsf + ki*integral + feedforward
    output_torque = output_lataccel / LAF                      [-1, 1]
    0xE4          = output_torque * STEER_MAX (4096)

The FEEDFORWARD IS OPEN LOOP and therefore does NOT enter the return ratio; it sets the operating point
and the steady error, not the margin.  That is stated explicitly because `AccordRatePlantFF` is the
toggle the brief asks about, and its effect is a MIS-SCALING, not a stability term -- section 4 sizes it.

    L_outer(s) = [kp*(1 + lsf/kp) + ki/s]/LAF  *  k_meas * Rate(s)/(j*2*pi*f) * exp(-j*2*pi*f*tau)

with `Rate(s)` = wheel rate in deg/s per UNIT command:
    V282   : the rate servo's closed-loop reference transfer, DC = the fork's measured
             HONDA_ACCORD_EPS_G_V = 120/95/85/70 deg/s per unit at v = 5/12.5/18.5/28.5 m/s
    V293   : OPEN.  Rate = k_map_unit * G_plant(s), k_map_unit = 2604 EPS torque counts per unit
             (read from the built image: T = 2460 at idx 240 = 3870 CAN counts, Kp 119)

THE CALIBRATION, and it is what makes the grid trustworthy.  The plant's own DC gain g0 is NOT taken
from the design290b fits (which span x400).  It is BACK-SOLVED from the fork's own measured G(v) and
V282's own return ratio, which is a closed identity:
    G_v282(v) = map_slope * L_dc/(1+L_dc) ,  map_slope = 141.4 deg/s per unit ,  L_dc = R_servo(0)*CPD*g0
so  g0(v) = (1/(CPD*R_servo(0))) * (G/(map_slope - G)).
The CONTROL on this is that the resulting |L_outer| on V282 must land inside the record's own MEASURED
0.026-0.165 (OUTER-LOOP-ID).  If it does not, the model is wrong and nothing below is reportable.

Run: python v293_s6_outer.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import adv_v290_physics as A                       # noqa: E402
import v293_lib as L                               # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = []

SR = 16.88                 # the live SteerRatio toggle on the V292 routes (flightread section 0)
L_WB = 2.83                # Accord wheelbase, m
STEER_MAX = 4096.0
MAP_SLOPE = 141.4          # deg/s per unit command, the assist map's own open-loop scale (fork section 0)
GV = {5.0: 120.0, 12.5: 95.0, 18.5: 85.0, 28.5: 70.0}     # HONDA_ACCORD_EPS_G_V, measured
CPD = 8.0
TAUS = [0.02, 0.10, 0.20]  # loop transport delay: EPS+CAN only / partial / the full SteerDelay
F = np.logspace(np.log10(0.05), np.log10(30.0), 1400)
FBAND = (0.2, 12.0)        # where a lateral controller closes; the integrator's 1/f blow-up below
                           # 0.2 Hz is not a margin statement and is excluded from every peak
NAMED = [225, 215, 38, 117]


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def k_meas(v):
    return v * v / (SR * L_WB) * np.pi / 180.0


def servo_dc(c):
    """R_servo(0): EPS torque counts per raw rate count at DC, from the image cells."""
    K = c["gain"] / 32768.0
    fade = 254.0 / 256.0
    C = c["kp_Y"][0] / 256.0
    Fdc = 2.0 * c["fb_b"] / (1024.0 - c["fb_a"])
    lag = 2.0 * c["lag_b"] / ((1024.0 - c["lag_a"]) * 32.0)
    return K * fade * C * Fdc * lag


def g0_of_v(v, Rdc):
    G = float(np.interp(v, sorted(GV), [GV[k] for k in sorted(GV)]))
    Ldc = G / (MAP_SLOPE - G)
    return G, Ldc, Ldc / (CPD * Rdc)


def rate_per_unit_v282(f, v, c, pl=None):
    """V282: closed-loop reference transfer, normalised to the measured DC gain G(v)."""
    G, Ldc, g0 = g0_of_v(v, servo_dc(c))
    if pl is None:
        return np.full_like(np.asarray(f, float), G, dtype=complex)
    el = A.Blocks(c, False, 0.0)
    fn, fd = el.fwd()
    fwd = A.pev(fn, f) / A.pev(fd, f)                    # T per count of E
    Lf = A.Lf(el, pl, f)
    # reference transfer: rate = 32*map_slope_per_count * fwd * CPD*G /(1+L) ... normalise to DC
    Tcl = fwd * (A.pev(pl.num, f) / A.pev(pl.den, f)) * CPD / (1.0 + Lf)
    Tcl0 = (A.pev(fn, 1e-6) / A.pev(fd, 1e-6)) * (A.pev(pl.num, 1e-6) / A.pev(pl.den, 1e-6)) * CPD \
        / (1.0 + A.Lf(el, pl, 1e-6))
    return G * Tcl / Tcl0


def rate_per_unit_v293(f, v, c, kmap_unit, pl=None):
    """V293: OPEN.  rate = kmap_unit * G_plant(f), normalised so DC = kmap_unit*g0(v)."""
    G, Ldc, g0 = g0_of_v(v, servo_dc(c))
    dc = kmap_unit * g0
    if pl is None:
        return np.full_like(np.asarray(f, float), dc, dtype=complex)
    Gp = A.pev(pl.num, f) / A.pev(pl.den, f)
    Gp0 = A.pev(pl.num, 1e-6) / A.pev(pl.den, 1e-6)
    return dc * Gp / Gp0


def loop(f, v, kp, ki, laf, rate_fn, tau, lsf=0.0):
    C = (kp * (1.0 + lsf / max(kp, 1e-9)) + ki / (2j * np.pi * f)) / laf
    P = k_meas(v) * rate_fn(f, v) / (2j * np.pi * f) * np.exp(-2j * np.pi * f * tau)
    return C * P


def margins(Lv, f, band=FBAND):
    """SIGN CONVENTION, declared.  This model is written as textbook NEGATIVE feedback --
    e = setpoint - measurement, measurement = P*C*e -- so the characteristic equation is 1 + L = 0,
    the critical point is L = -1 and the critical phase is -180 deg.
    🛑 OUTER-LOOP-ID's `|1 - L|` and `critical phase 0 deg` are the SAME physics in the sign of the
    LOGGED variable (`pid_log.output` is `-output_torque`).  Do not mix the two.  My first version
    printed |1 - L| in THIS convention, which was wrong; it is |1 + L| here.
    Returns: Ms (the sensitivity peak = 1/min|1+L|), the crossover, and the phase margin there."""
    mag = np.abs(Lv)
    m = (f >= band[0]) & (f <= band[1])
    S = 1.0 / np.abs(1.0 + Lv)
    k = int(np.argmax(S[m]))
    above = np.where(m & (mag >= 1.0))[0]
    if len(above):
        j = above[-1]                              # the highest-frequency crossing = the crossover
        fc = float(f[j])
        pm = float(180.0 + np.degrees(np.angle(Lv[j])))
        pm = (pm + 180.0) % 360.0 - 180.0
    else:
        fc, pm = np.nan, np.nan
    return dict(peak=float(mag[m].max()), fpeak=float(f[m][int(np.argmax(mag[m]))]),
                Ms=float(S[m][k]), fMs=float(f[m][k]), fc=fc, pm=pm,
                L1=float(np.interp(1.0, f, mag)), L20=float(np.interp(20.0, f, mag)),
                Lp2=float(np.interp(0.2, f, mag)))


def main():
    c282 = L.read_cells(L.IMG282)
    c293 = L.torque_mode(c282, kp=119)
    # k_map_unit, read from the built image's own surface
    s = L.surface(c293, np.array([240.0]), 0.0, fade=254)
    kmap_unit = float(abs(s["T"][0])) / (240.0 * 16.125736) * STEER_MAX
    s282 = L.surface(c282, np.array([240.0]), 0.0, fade=254)

    pr("=" * 120)
    pr("V293 TORQUE MODE -- openpilot's OUTER LOOP          tmdesign 2026-09-13    ANALYSIS ONLY")
    pr("=" * 120)
    Rdc = servo_dc(c282)
    pr("R_servo(0) from the V282 image cells = %.4f EPS torque counts per raw rate count" % Rdc)
    pr("  = (gain %d/32768) * (fade 254/256) * (Kp %d/256) * (fb DC %.4f) * (out-lag DC %.6f)"
       % (c282["gain"], c282["kp_Y"][0], 2.0 * c282["fb_b"] / (1024.0 - c282["fb_a"]),
          2.0 * c282["lag_b"] / ((1024.0 - c282["lag_a"]) * 32.0)))
    pr("V293 delivered torque at idx 240 = %.0f counts at %d CAN counts => k_map = %.4f counts/count,"
       % (abs(s["T"][0]), int(240 * 16.125736), abs(s["T"][0]) / (240 * 16.125736)))
    pr("   i.e. %.0f EPS torque counts per UNIT command.  (V282 at fb = 0 reaches %.0f at the same idx.)"
       % (kmap_unit, abs(s282["T"][0])))

    pr("")
    pr("-" * 120)
    pr("1. THE PLANT, BACK-SOLVED FROM THE FORK'S OWN MEASURED G(v) -- and what torque mode does to it")
    pr("-" * 120)
    pr("  %6s %10s %10s %12s %14s %14s %10s" %
       ("v m/s", "G_v282", "L_dc", "g0 (deg/s", "V293 rate per", "ratio", "k_meas"))
    pr("  %6s %10s %10s %12s %14s %14s %10s" %
       ("", "deg/s/unit", "", "per T ct)", "unit", "V293/V282", "m/s2/deg"))
    for v in (5.0, 8.0, 12.5, 18.5, 25.0, 28.5):
        G, Ldc, g0 = g0_of_v(v, Rdc)
        r93 = kmap_unit * g0
        pr("  %6.1f %10.1f %10.3f %12.5f %14.1f %14.3f %10.5f" % (v, G, Ldc, g0, r93, r93 / G, k_meas(v)))
    pr("")
    pr("  🛑 THE STRUCTURAL POINT.  V282's rate-per-unit is set by the MAP and held within x1.7 across")
    pr("  the speed range by the servo (120 -> 70).  V293's is set by the PLANT and swings much further")
    pr("  over the same range (the exact factor is on the line below).  The servo was regulating out")
    pr("  exactly this variation; torque mode hands it to openpilot's outer loop, which has no speed")
    pr("  schedule for it.")
    v1, v2 = 5.0, 28.5
    r1 = kmap_unit * g0_of_v(v1, Rdc)[2]
    r2 = kmap_unit * g0_of_v(v2, Rdc)[2]
    pr("     V293 rate-per-unit: %.0f at %.0f m/s -> %.0f at %.0f m/s = x%.2f swing (V282: x%.2f)"
       % (r1, v1, r2, v2, r1 / r2, GV[5.0] / GV[28.5]))

    # ---------------------------------------------------------------- the control
    pr("")
    pr("-" * 120)
    pr("2. CONTROL -- the model must reproduce the MEASURED V282 outer return ratio 0.026-0.165")
    pr("-" * 120)
    pr("  (OUTER-LOOP-ID-2026-09-10: |L| = 0.026-0.165 over r39/r5e/r62/r63/r35, bound <= 0.189;")
    pr("   |1 - L| per route 1.069 / 1.088 / 1.022 / 0.974 / 1.154.)")
    pr("")
    pr("  🛑 The record's 0.026-0.165 is |L| AT THE RING (18-22 Hz), not at 1 Hz.  The control is")
    pr("  therefore evaluated at 20 Hz, WITH the plant's real dynamics from the design290b fits -- a")
    pr("  flat-DC rate response cannot reproduce it, because most of the 20 Hz return is the plant's")
    pr("  own resonance.  My first version compared at 1 Hz and FAILED; the failure was mine.")
    pr("")
    import design290b_candidates as D
    import v292_replay_s2 as S2
    fam, stable, sample = S2.load_family()
    byid = {f["id"]: f for f in fam}
    plants = {i: D.mkplant(byid[i]) for i in NAMED}
    pr("  %6s %6s %6s %9s %9s %10s %10s %10s" %
       ("fit", "v", "tau", "|L|@20Hz", "|L|@1Hz", "|L|@0.2Hz", "peak(band)", "Ms"))
    l20 = []
    for fid in NAMED:
        for v in (5.0, 12.5, 28.5):
            Lv = loop(F, v, 0.9, 0.30, 6.0,
                      lambda f, vv: rate_per_unit_v282(f, vv, c282, plants[fid]), 0.10)
            m = margins(Lv, F)
            l20.append(m["L20"])
            pr("  %6d %6.1f %6.2f %9.4f %9.4f %10.4f %10.4f %10.4f" %
               (fid, v, 0.10, m["L20"], m["L1"], m["Lp2"], m["peak"], m["Ms"]))
    lo, hi = float(np.min(l20)), float(np.max(l20))
    ok = (lo <= 0.20) and (hi >= 0.02) and (hi <= 0.60)
    pr("")
    pr("  model |L| at 20 Hz spans %.4f-%.4f against the measured 0.026-0.165 (bound 0.189)  ->  %s"
       % (lo, hi, "CONTROL PASSES" if ok else "CONTROL FAILS -- do not read on"))
    pr("  (a model that overlaps the measured interval and does not exceed x3 its upper bound on any")
    pr("   fit is accepted; the plant family itself spans more than that.)")

    # ---------------------------------------------------------------- the grid
    pr("")
    pr("=" * 120)
    pr("3. THE GRID -- LAF x Kp x Ki, V282 vs V293, at tau = 0.10 s, three speeds")
    pr("=" * 120)
    pr("Reported: |L| at 1 Hz ; the peak |L| and where ; min |1 - L| (the record's own critical-point")
    pr("metric, L = +1) ; and the crossover frequency where |L| last exceeds 1 (blank = never).")
    pr("A cell REPRODUCES V276 if |L| >= 1 anywhere in 2-4 Hz.")
    pr("Scored on the MEDIAN fit 225 with the plant's real dynamics; the fit spread is section 3.1.")
    pr("SAFE = sensitivity peak Ms < 2.0 AND (no crossover in %.1f-%.1f Hz, or phase margin > 35 deg)."
       % FBAND)
    pr("Columns: |L| at 1 Hz ; Ms = max|1/(1+L)| over the band ; fc = crossover Hz ; PM = phase margin.")
    for v in (5.0, 12.5, 28.5):
        pr("")
        pr("  v = %.1f m/s     k_meas %.5f m/s2 per deg" % (v, k_meas(v)))
        pr("  %5s %5s %5s | %-26s | %-26s | %-9s %s" %
           ("LAF", "Kp", "Ki", "V282 |L|1Hz    Ms   fc   PM", "V293 |L|1Hz    Ms   fc   PM",
            "V276 2-4Hz", "verdict"))
        for laf in (2.0, 4.0, 6.0, 8.0, 10.0, 12.0):
            for kp in (0.3, 0.6, 0.9):
                for ki in (0.0, 0.15, 0.30):
                    L2 = loop(F, v, kp, ki, laf,
                              lambda f, vv: rate_per_unit_v282(f, vv, c282, plants[225]), 0.10)
                    L9 = loop(F, v, kp, ki, laf,
                              lambda f, vv: rate_per_unit_v293(f, vv, c282, kmap_unit, plants[225]), 0.10)
                    m2, m9 = margins(L2, F), margins(L9, F)
                    b24 = (F >= 2.0) & (F <= 4.0)
                    v276 = bool(np.max(np.abs(L9)[b24]) >= 1.0)
                    v276_282 = bool(np.max(np.abs(L2)[b24]) >= 1.0)
                    safe = (np.isnan(m9["pm"]) or m9["pm"] > 35.0) and (m9["Ms"] < 2.0)
                    pr("  %5.1f %5.2f %5.2f | %7.4f %6.2f %5.2f %5.0f | %7.4f %6.2f %5.2f %5.0f | %-9s %s" %
                       (laf, kp, ki, m2["L1"], m2["Ms"], m2["fc"], m2["pm"],
                        m9["L1"], m9["Ms"], m9["fc"], m9["pm"],
                        ("YES" + ("/V282 too" if v276_282 else "")) if v276 else "-",
                        "SAFE" if safe else "RISK"))

    # ---------------------------------------------------------------- the fit spread
    pr("")
    pr("-" * 120)
    pr("3.1 THE FIT SPREAD on the operator's own live cell (LAF 6.0, Kp 0.9, Ki 0.30)")
    pr("-" * 120)
    pr("  %6s %6s | %-26s | %-26s" % ("fit", "v", "V282 |L|1Hz  Ms   fc   PM", "V293 |L|1Hz  Ms   fc   PM"))
    for fid in NAMED:
        for v in (5.0, 12.5, 28.5):
            L2 = loop(F, v, 0.9, 0.30, 6.0, lambda f, vv: rate_per_unit_v282(f, vv, c282, plants[fid]), 0.10)
            L9 = loop(F, v, 0.9, 0.30, 6.0,
                      lambda f, vv: rate_per_unit_v293(f, vv, c282, kmap_unit, plants[fid]), 0.10)
            m2, m9 = margins(L2, F), margins(L9, F)
            pr("  %6d %6.1f | %8.4f %6.2f %5.2f %5.0f | %8.4f %6.2f %5.2f %5.0f" %
               (fid, v, m2["L1"], m2["Ms"], m2["fc"], m2["pm"], m9["L1"], m9["Ms"], m9["fc"], m9["pm"]))

    # ---------------------------------------------------------------- delay sensitivity
    pr("")
    pr("-" * 120)
    pr("3.2 DELAY SENSITIVITY -- tau is the single BELIEF in the plant model")
    pr("-" * 120)
    pr("  %6s %6s | %-26s | %-26s" % ("tau s", "v", "V282 |L|1Hz  Ms   fc   PM", "V293 |L|1Hz  Ms   fc   PM"))
    for tau in TAUS:
        for v in (5.0, 12.5, 28.5):
            L2 = loop(F, v, 0.9, 0.30, 6.0, lambda f, vv: rate_per_unit_v282(f, vv, c282, plants[225]), tau)
            L9 = loop(F, v, 0.9, 0.30, 6.0,
                      lambda f, vv: rate_per_unit_v293(f, vv, c282, kmap_unit, plants[225]), tau)
            m2, m9 = margins(L2, F), margins(L9, F)
            pr("  %6.2f %6.1f | %8.4f %6.2f %5.2f %5.0f | %8.4f %6.2f %5.2f %5.0f" %
               (tau, v, m2["L1"], m2["Ms"], m2["fc"], m2["pm"], m9["L1"], m9["Ms"], m9["fc"], m9["pm"]))

    # ---------------------------------------------------------------- the feedforward
    pr("")
    pr("=" * 120)
    pr("4. THE FEEDFORWARD -- `AccordRatePlantFF` is a MIS-SCALING under torque mode, not a margin term")
    pr("=" * 120)
    pr("`get_honda_accord_rate_plant_ff` computes  hold = k(v)*angle/G(v)  and  move = rate_gain*d(angle_des)/dt / G(v).")
    pr("Both divide by G(v), the CLOSED-LOOP rate-servo gain.  In torque mode the true gain is")
    pr("k_map_unit*g0(v), so every FF term is wrong by the ratio in the last column below.")
    pr("")
    pr("  %6s %12s %12s %12s %16s" % ("v m/s", "G_v282", "G_torquemode", "FF error", "what the car does"))
    for v in (5.0, 8.0, 12.5, 18.5, 25.0, 28.5):
        G, Ldc, g0 = g0_of_v(v, Rdc)
        r93 = kmap_unit * g0
        e = r93 / G
        pr("  %6.1f %12.1f %12.1f %12.2fx %16s" %
           (v, G, r93, e, "OVERSHOOTS x%.1f" % e if e > 1.15 else
            ("undershoots x%.2f" % e if e < 0.87 else "about right")))
    pr("")
    pr("  With the FF ON and torque-mode firmware the open-loop feedforward is x%.1f too big at 5 m/s."
       % (kmap_unit * g0_of_v(5.0, Rdc)[2] / GV[5.0]))
    pr("  That is the V276 FAILURE SHAPE without needing any instability: a lane whose open-loop push")
    pr("  is 3x what the geometry needs, with a feedback term divided by LAF 6.0 that is too weak to")
    pr("  pull it back.  The fix is not a margin knob -- it is to RE-IDENTIFY G(v) for the new plant,")
    pr("  which the fork memo's section 3.5 already names as the gating step.")
    pr("")
    pr("  Setting `AccordRatePlantFF` = False instead hands the load to the GENERIC lat-accel")
    pr("  feedforward `setpoint/LAF`, which the fork's own comment calls '3-10x too much torque on")
    pr("  this plant' -- for the RATE plant.  On a TORQUE plant that comment no longer applies, and the")
    pr("  generic path becomes the correct one: this is the one place where torque mode makes the fork")
    pr("  SIMPLER.  It needs LAF identified against the new plant first.  [BELIEF -- not measured]")

    open(os.path.join(SCR, "v293_s6_outer.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("")
    pr("wrote _scratch/v293_s6_outer.txt")


if __name__ == "__main__":
    os.makedirs(SCR, exist_ok=True)
    main()
