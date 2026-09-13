# -*- coding: utf-8 -*-
"""v293_b6_outer.py -- ADVERSARIAL criterion B6: openpilot's OUTER loop under V293 torque mode.

Subagent `B6` of `advB3`, 2026-09-13.  ANALYSIS ONLY -- builds nothing, flashes nothing, sends
nothing on any bus, edits no build script, writes no image.

WHAT THIS DOES THAT `v293_s6_outer.py` DOES NOT.  Three terms of the fork's own controller that
s6 omits, each re-read from the fork source this session:

  (1) low_speed_factor.  `latcontrol_torque.py:332-335`
          low_speed_factor = (interp(v, [0,10,20,30], [12,10.5,8,5]) / max(v, MIN_SPEED=1.0))**2
          error_with_lsf   = error * (1 + low_speed_factor / max(current_kp, 1e-3))
      s6 passes lsf = 0.0 at EVERY speed.  The effective proportional gain is (kp + lsf), so at
      5 m/s lsf = 5.0625 and the preset's kp 0.3 becomes 5.3625 -- x17.9.  This is the single
      largest error in s6 and it is concentrated exactly where B6 has to look.

  (2) the friction compensator.  `opendbc/car/lateral.py:190-198` + `latcontrol_torque.py:592`
          ff += friction_scale * get_friction(error_with_lsf + 0.22*friction_jerk, deadzone, thr, tp)
          get_friction = interp(err, [-thr, thr], [-friction*LAF, +friction*LAF])
      In TORQUE units (output_torque = output_lataccel/LAF) that is a SATURATION of small-signal
      slope (friction/thr) per unit of error_with_lsf, i.e. (friction/thr)*(1+lsf/kp) per unit of
      RAW error, saturating at +-friction.  It is LAF-independent.  s6 omits it entirely.
      thr = get_standard_friction_threshold(v) = max(gm_default(v) <= 0.27, 0.30) = 0.30 EXACTLY
      at every speed.  deadzone = 0 (steeringAngleDeadzoneDeg is never set for the Accord).

  (3) tau = 0.20 s, the record's own `liveDelay.lateralDelay`, not s6's 0.10 s.

THE NONLINEARITY THAT MATTERS.  (2) is a saturation: HIGH gain at small error, falling as 1/E.
That is the destabilising-at-small-amplitude shape, and it is the classical Coulomb-compensator
limit-cycle generator.  Its describing function is solved here, and the verdict is cross-checked
by a full nonlinear time-domain simulation at the fork's own dt = 0.01 s.

THE MODEL, and the two places it is DELIBERATELY PESSIMISTIC (both stated, both quantified):
  a. The plant is design290b's `Plant` = g0/(1+s/w1) * resonance, NO self-aligning spring.  The
     fork's own identification (`HONDA_ACCORD_EPS_K_V` = 0.17..0.50 1/s) says the real plant is
     rate/torque = G*s/(s+k), whose angle/torque rolls off below k/2pi = 0.027-0.080 Hz.  Omitting
     it costs phase LEAD, so the model UNDER-states phase margin.  Sized in section 6.
  b. tau is the physical transport delay.  Under V293 the lane is a static map and under V282 it
     is a servo, so V293's true tau is probably SMALLER.  Using the same tau for both is
     pessimistic for V293.  [BELIEF]

Run: python v293_b6_outer.py
"""
import glob
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import adv_v290_physics as A                       # noqa: E402
import v293_lib as L                               # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


# ---------------------------------------------------------------------------- the fork, byte for byte
SR, L_WB, STEER_MAX = 16.88, 2.83, 4096.0
MAP_SLOPE = 141.4                      # deg/s per unit command (V282's map top: 133.6 deg/s at 3870/4096)
GV_BP = [5.0, 12.5, 18.5, 28.5]
GV_V = [120.0, 95.0, 85.0, 70.0]       # HONDA_ACCORD_EPS_G_V
KV_BP = [4.0, 8.0, 12.5, 18.5, 28.5]
KV_V = [0.17, 0.28, 0.35, 0.45, 0.50]  # HONDA_ACCORD_EPS_K_V, 1/s -- the self-aligning spring
CPD = 8.0
LOW_SPEED_X, LOW_SPEED_Y = [0, 10, 20, 30], [12, 10.5, 8, 5]
MIN_SPEED = 1.0
FRIC_THR = 0.30                        # get_standard_friction_threshold == max(<=0.27, 0.30)

# the two tunes under test, both read from the fork source this session
PRESET = dict(name="TORQUE-MODE PRESET", laf=6.0, kp=0.3, ki=0.15, fric=0.01, ff="OFF")
LIVE = dict(name="OPERATOR LIVE TUNE", laf=6.0, kp=0.9, ki=0.30, fric=0.01, ff="ON (rate-plant)")

SPEEDS = [5.0, 8.0, 12.5, 18.5, 28.5]
TAUS = [0.15, 0.20, 0.30]
KAPPAS = np.round(np.arange(0.50, 2.001, 0.05), 3)     # the swept true-plant-gain multiplier
F = np.logspace(np.log10(0.05), np.log10(50.0), 4000)
FBAND = (0.2, 12.0)
NAMED = [225, 215, 38, 117]


def lsf_of(v):
    return float((np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / max(v, MIN_SPEED)) ** 2)


def k_meas(v):
    return v * v / (SR * L_WB) * np.pi / 180.0


def servo_dc(c):
    K = c["gain"] / 32768.0
    fade = 254.0 / 256.0
    C = c["kp_Y"][0] / 256.0
    Fdc = 2.0 * c["fb_b"] / (1024.0 - c["fb_a"])
    lag = 2.0 * c["lag_b"] / ((1024.0 - c["lag_a"]) * 32.0)
    return K * fade * C * Fdc * lag


def g0_of_v(v, Rdc, map_slope=MAP_SLOPE):
    G = float(np.interp(v, GV_BP, GV_V))
    Ldc = G / (map_slope - G)
    return G, Ldc, Ldc / (CPD * Rdc)


# ---------------------------------------------------------------------------- controller, exactly
def C_lin(f, v, tune):
    """PI part in TORQUE units per unit of RAW lateral-accel error.  Excludes the friction DF."""
    lsf, kp, ki, laf = lsf_of(v), tune["kp"], tune["ki"], tune["laf"]
    A_lsf = 1.0 + lsf / max(kp, 1e-3)
    return ((kp + lsf) + ki * A_lsf / (2j * np.pi * f)) / laf


def fric_slope(v, tune):
    """small-signal friction gain in TORQUE units per unit of RAW lateral-accel error."""
    return (tune["fric"] / FRIC_THR) * (1.0 + lsf_of(v) / max(tune["kp"], 1e-3))


def psi_sat(x):
    """describing function of a unit-slope saturation with unit limit, input amplitude x."""
    x = np.asarray(x, float)
    out = np.ones_like(x)
    m = x > 1.0
    xm = x[m]
    out[m] = (2.0 / np.pi) * (np.arcsin(1.0 / xm) + (1.0 / xm) * np.sqrt(1.0 - 1.0 / xm ** 2))
    return out


def P_of(f, v, rate_fn, tau, kappa, spring=False):
    """plant: raw lat-accel measured per unit of TORQUE command."""
    R = kappa * rate_fn(f, v)                                   # deg/s per unit
    ang = R / (2j * np.pi * f)                                  # deg per unit
    if spring:                                                  # rate/torque = G s/(s+k) => angle rolls off
        k = float(np.interp(v, KV_BP, KV_V))
        ang = ang * (2j * np.pi * f) / (2j * np.pi * f + k)
    return k_meas(v) * ang * np.exp(-2j * np.pi * f * tau)


def margins(Lv, f, band=FBAND):
    mag = np.abs(Lv)
    m = (f >= band[0]) & (f <= band[1])
    S = 1.0 / np.abs(1.0 + Lv)
    above = np.where(m & (mag >= 1.0))[0]
    if len(above):
        j = above[-1]
        fc = float(f[j])
        pm = (180.0 + np.degrees(np.angle(Lv[j])) + 180.0) % 360.0 - 180.0
    else:
        fc, pm = np.nan, np.nan
    # widest-band stability read: any -180 crossing with |L| >= 1 anywhere 0.05-50 Hz
    ph = np.unwrap(np.angle(Lv))
    return dict(Ms=float(S[m].max()), fMs=float(f[m][int(np.argmax(S[m]))]), fc=fc, pm=pm,
                magmax=float(mag.max()), fmagmax=float(f[int(np.argmax(mag))]), ph=ph)


def nyquist_unstable(Lv, f):
    """Robust encirclement read for a loop with free integrators.

    The Nyquist contour indents to the RIGHT of the origin poles, so their image is a large
    clockwise arc from +N*90 deg down.  For this loop shape (PI x 1/s x delay, no RHP open-loop
    poles) closed-loop stability is equivalent to: at every -180 deg phase crossing on the way
    DOWN in phase as f rises, |L| < 1.  Implemented directly and cross-checked in section 5 by a
    nonlinear time-domain simulation, which is the instrument of record.
    """
    ph = np.degrees(np.unwrap(np.angle(Lv)))
    mag = np.abs(Lv)
    bad = []
    for i in range(len(f) - 1):
        for k in (-180.0, -540.0, -900.0):
            if (ph[i] - k) * (ph[i + 1] - k) < 0:
                w = (k - ph[i]) / (ph[i + 1] - ph[i])
                mg = mag[i] + w * (mag[i + 1] - mag[i])
                if mg >= 1.0:
                    bad.append((float(f[i]), float(mg)))
    return (len(bad) > 0), bad


# ---------------------------------------------------------------------------- the rate transfers
def make_rate_fns(c282, c293, plants, fid):
    Rdc = servo_dc(c282)
    s = L.surface(c293, np.array([240.0]), 0.0, fade=254)
    kmap_unit = float(abs(s["T"][0])) / (240.0 * 16.125736) * STEER_MAX
    pl = plants[fid]

    def v282(f, v):
        G, Ldc, g0 = g0_of_v(v, Rdc)
        el = A.Blocks(c282, False, 0.0)
        fn, fd = el.fwd()
        fwd = A.pev(fn, f) / A.pev(fd, f)
        Lf = A.Lf(el, pl, f)
        Tcl = fwd * (A.pev(pl.num, f) / A.pev(pl.den, f)) * CPD / (1.0 + Lf)
        T0 = (A.pev(fn, 1e-6) / A.pev(fd, 1e-6)) * (A.pev(pl.num, 1e-6) / A.pev(pl.den, 1e-6)) * CPD \
            / (1.0 + A.Lf(el, pl, 1e-6))
        return G * Tcl / T0

    def v293(f, v):
        G, Ldc, g0 = g0_of_v(v, Rdc)
        dc = kmap_unit * g0
        Gp = A.pev(pl.num, f) / A.pev(pl.den, f)
        Gp0 = A.pev(pl.num, 1e-6) / A.pev(pl.den, 1e-6)
        return dc * Gp / Gp0

    return v282, v293, kmap_unit, Rdc


def stock_rate_fn(cstock, c282, plants, fid):
    """STOCK's rate-per-unit, by the SAME back-solve: the plant g0 is a property of the CAR, so it
    carries across firmwares; only R_servo(0) and the map slope change."""
    Rdc282, Rdc_s = servo_dc(c282), servo_dc(cstock)
    slope_s = float(np.max(cstock["map_Y"])) * 32.0 / 32.0      # placeholder, replaced by caller
    pl = plants[fid]

    def fn(f, v, slope_stock=slope_s):
        _, _, g0 = g0_of_v(v, Rdc282)                            # the CAR's plant, from V282
        Ldc = Rdc_s * CPD * g0
        G = slope_stock * Ldc / (1.0 + Ldc)
        el = A.Blocks(cstock, False, 0.0)
        fnum, fden = el.fwd()
        fwd = A.pev(fnum, f) / A.pev(fden, f)
        Lf = A.Lf(el, pl, f)
        Tcl = fwd * (A.pev(pl.num, f) / A.pev(pl.den, f)) * CPD / (1.0 + Lf)
        T0 = (A.pev(fnum, 1e-6) / A.pev(fden, 1e-6)) * (A.pev(pl.num, 1e-6) / A.pev(pl.den, 1e-6)) * CPD \
            / (1.0 + A.Lf(el, pl, 1e-6))
        return G * Tcl / T0
    return fn, Rdc_s


# ---------------------------------------------------------------------------- nonlinear time sim
def sim(v, tune, rate_dc, tau, kappa, pl, T=40.0, dt=0.01, kick=0.02, spring=True):
    """Full nonlinear loop at the fork's own dt.  Returns (grew, f_osc, amp_torque, amp_err).

    Chain per tick, in the controller's own order:
        err          = setpoint(0) - measurement
        err_lsf      = err * (1 + lsf/kp)
        p            = kp * err_lsf
        i           += ki * err_lsf * dt         (lat-accel space, clamped to the PID limits)
        ff_friction  = clip(err_lsf/thr, -1, 1) * friction * LAF
        out_lataccel = p + i + ff_friction
        torque       = clip(out_lataccel / LAF, -1, 1)
        rate         = kappa * rate_dc * H(torque delayed by tau)     H = plant shape, DC 1
        angle       += (rate - k_spring*angle) * dt                   the fork's own identified plant
        measurement  = k_meas * angle
    """
    n = int(T / dt)
    lsf, kp, ki, laf, fric = lsf_of(v), tune["kp"], tune["ki"], tune["laf"], tune["fric"]
    A_lsf = 1.0 + lsf / max(kp, 1e-3)
    kspr = float(np.interp(v, KV_BP, KV_V)) if spring else 0.0
    km = k_meas(v)
    # plant shape at 100 Hz: first-order lag f1 x resonance (fp, zp, kappa-blend), DC gain 1
    w1 = 2 * np.pi * pl.f1
    num, den = np.array([w1]), np.array([1.0, w1])
    if pl.fp:
        wp = 2 * np.pi * pl.fp
        mden = np.array([1.0, 2 * pl.zp * wp, wp ** 2])
        mnum = np.array([wp ** 2])
        if pl.kappa is not None:
            mnum = np.polyadd((1 - pl.kappa) * mden, pl.kappa * mnum)
        num, den = np.polymul(num, mnum), np.polymul(den, mden)
    bz, az, _ = signal.cont2discrete((num, den), dt, method="tustin")
    bz, az = np.atleast_1d(np.squeeze(bz)), np.atleast_1d(np.squeeze(az))
    nb, na = len(bz), len(az)
    xb, yb = np.zeros(nb), np.zeros(na)
    nd = max(int(round((tau + pl.tau) / dt)), 1)
    dl = np.zeros(nd)
    ilim = laf * 1.0                                  # PID limits = +-steer_max converted through LAF
    ii, ang, meas = 0.0, 0.0, 0.0
    tq = np.zeros(n)
    er = np.zeros(n)
    for t in range(n):
        err = (kick if t == 0 else 0.0) - meas        # a single-tick lat-accel kick, then free
        el = err * A_lsf
        ii = float(np.clip(ii + ki * el * dt, -ilim, ilim))
        ffr = float(np.clip(el / FRIC_THR, -1.0, 1.0)) * fric * laf
        out = kp * el + ii + ffr
        torque = float(np.clip(out / laf, -1.0, 1.0))
        tq[t], er[t] = torque, err
        dl = np.roll(dl, 1)
        dl[0] = torque
        u = dl[-1]
        xb = np.roll(xb, 1)
        xb[0] = u
        yk = (np.dot(bz, xb) - np.dot(az[1:], yb[:na - 1])) / az[0]
        yb = np.roll(yb, 1)
        yb[0] = yk
        rate = kappa * rate_dc * yk
        ang += (rate - kspr * ang) * dt
        meas = km * ang
    half = n // 2
    a1 = float(np.max(np.abs(tq[:half]))) if half else 0.0
    a2 = float(np.max(np.abs(tq[half:])))
    tail = tq[int(0.6 * n):]
    fo = np.nan
    if a2 > 1e-6:
        w = tail - tail.mean()
        sp = np.abs(np.fft.rfft(w * np.hanning(len(w))))
        ff = np.fft.rfftfreq(len(w), dt)
        k = int(np.argmax(sp[1:])) + 1
        fo = float(ff[k])
    return dict(grew=bool(a2 > max(a1, 1e-9) * 0.98 and a2 > 1e-4), a_early=a1, a_late=a2,
                fosc=fo, sat=bool(np.max(np.abs(tq)) >= 0.999))


# ---------------------------------------------------------------------------- main
def main():
    pr("=" * 118)
    pr("B6 -- openpilot's OUTER LOOP under V293 TORQUE MODE.   subagent B6 of advB3, 2026-09-13.")
    pr("ADVERSARIAL.  The pass is written to be able to return FAIL; the FAIL criteria are in")
    pr("_scratch/B6_FAIL_CRITERIA_PREREG.txt, written before any number below existed.")
    pr("=" * 118)

    # ---------------- 0. the images
    c282 = L.read_cells(L.IMG282)
    g = sorted(glob.glob(L.FW + "_v293_*_plain_image.bin"))
    if g:
        import hashlib
        img = g[-1]
        c293 = L.read_cells(img)
        h = hashlib.sha256(open(img, "rb").read()).hexdigest()
        src = "BUILT IMAGE  %s\n   sha256 %s" % (os.path.basename(img), h)
    else:
        c293 = L.torque_mode(c282, kp=120, r24_arm=2048)
        src = "NO BUILT IMAGE ON DISK YET -- modelled from V282 cells + the orchestrator's stated edits\n" \
              "   (Kp 120 flat, fb clamp 0, Kd 0, D clamp 0, r24 2048).  RE-RUN WHEN THE IMAGE LANDS."
    pr("")
    pr("0. THE CELLS, read little-endian from the image")
    pr("-" * 118)
    pr("   V282  %s" % os.path.basename(L.IMG282))
    pr("   V293  %s" % src)
    pr("   %-14s %10s %10s" % ("cell", "V282", "V293"))
    for k, lab in (("fb_clamp", "0xC62E6 fb clamp"), ("d_clamp", "0xC61B6 D clamp"),
                   ("p_clamp", "0xC61BC P clamp"), ("sum_clamp", "0xC61BE sum"),
                   ("t_clamp", "0xC61B4 T clamp"), ("r24_arm", "0xC6446 r24 arm"),
                   ("ki", "0xC63E6 Ki"), ("gain", "gain")):
        pr("   %-14s %10s %10s" % (lab, c282[k], c293[k]))
    pr("   %-14s %10s %10s" % ("Kp bank Y", str(c282["kp_Y"]), str(c293["kp_Y"])))
    pr("   %-14s %10s %10s" % ("Kd bank Y", str(c282["kd_Y"]), str(c293["kd_Y"])))

    import design290b_candidates as D
    import v292_replay_s2 as S2
    fam, stable, sample = S2.load_family()
    byid = {f["id"]: f for f in fam}
    plants = {i: D.mkplant(byid[i]) for i in NAMED}
    r282, r293, kmap_unit, Rdc = make_rate_fns(c282, c293, plants, 225)

    # ---------------- 1. the back-solve, checked
    pr("")
    pr("1. THE BACK-SOLVE -- the load-bearing step, re-derived and audited")
    pr("-" * 118)
    s293 = L.surface(c293, np.array([240.0]), 0.0, fade=254)
    s282 = L.surface(c282, np.array([240.0]), 0.0, fade=254)
    m293 = L.surface_march(c293, np.array([240.0]), 0.0, kd=0, fade=254)
    pr("   V293 delivered T at idx 240 (closed form) = %.0f counts ; byte-exact tick march = %.0f"
       % (abs(s293["T"][0]), m293[0]))
    pr("   V282 at fb = 0, same idx                  = %.0f counts" % abs(s282["T"][0]))
    pr("   => k_map_unit = %.1f EPS torque counts per UNIT of openpilot command" % kmap_unit)
    pr("   R_servo(0) from the V282 cells = %.4f   [K %.5f * fade %.5f * Kp %.5f * Fdc %.4f * lag %.6f]"
       % (Rdc, c282["gain"] / 32768.0, 254.0 / 256.0, c282["kp_Y"][0] / 256.0,
          2.0 * c282["fb_b"] / (1024.0 - c282["fb_a"]),
          2.0 * c282["lag_b"] / ((1024.0 - c282["lag_a"]) * 32.0)))
    br = kmap_unit / (CPD * Rdc * MAP_SLOPE)
    pr("")
    pr("   The identity, written out:   ratio(v) = V293_rate_per_unit / G_v282(v)")
    pr("       g0   = L_dc/(CPD*R_servo(0)) ,  L_dc = G/(MAP_SLOPE - G)")
    pr("       => ratio(v) = [k_map_unit/(CPD*R_servo(0)*MAP_SLOPE)] * (1 + L_dc(v))")
    pr("       the bracket is SPEED-INDEPENDENT and equals %.4f from the bytes." % br)
    pr("   ⇒ THE WHOLE x3.17 AT 5 m/s IS (1+L_dc) RISING AT LOW SPEED.  It is not a plant fact; it")
    pr("     is the statement that V282's servo loop gain is 5.6 at 5 m/s and 0.98 at 28.5 m/s.")
    pr("   %6s %9s %8s %10s %12s %9s %9s" % ("v", "G_v282", "L_dc", "g0", "V293 rate", "ratio", "check"))
    for v in SPEEDS:
        G, Ldc, g0 = g0_of_v(v, Rdc)
        r = kmap_unit * g0
        pr("   %6.1f %9.1f %8.3f %10.5f %12.1f %9.3f %9.3f"
           % (v, G, Ldc, g0, r, r / G, br * (1.0 + Ldc)))
    pr("")
    pr("   🛑 WHAT THE BACK-SOLVE IS AND IS NOT.  `G_v282 = MAP_SLOPE*L/(1+L)` is a MID-BAND")
    pr("   identity, not a true-DC one.  The fork's OWN identification is `rate = G*tq - k*angle`")
    pr("   with k = 0.17..0.50 1/s, i.e. rate/torque = G*s/(s+k): the true DC rate-per-torque is")
    pr("   ZERO and L_dc would be 0, giving G = 0.  It is not 0 because G was measured ABOVE the")
    pr("   spring corner k/2pi = %.3f-%.3f Hz.  The whole B6 band (0.2-12 Hz) sits in that same"
       % (KV_V[0] / (2 * np.pi), KV_V[-1] / (2 * np.pi)))
    pr("   plateau, so the back-solve is VALID HERE.  [EVIDENCE for the algebra and the cells;")
    pr("   BELIEF that HONDA_ACCORD_EPS_G_V, measured on r34-r3c, transfers to V282's map.]")

    # ---------------- 2. the controller terms s6 omits
    pr("")
    pr("2. THE THREE TERMS `v293_s6_outer.py` OMITS -- sized before anything is scored")
    pr("-" * 118)
    pr("   %6s %9s | %-28s | %-28s" % ("v", "lsf", "PRESET kp 0.3 / ki 0.15", "LIVE kp 0.9 / ki 0.30"))
    pr("   %6s %9s | %9s %9s %8s | %9s %9s %8s"
       % ("", "", "kp+lsf", "fric gain", "total", "kp+lsf", "fric gain", "total"))
    for v in SPEEDS:
        lsf = lsf_of(v)
        row = [v, lsf]
        for t in (PRESET, LIVE):
            pp = (t["kp"] + lsf) / t["laf"]
            fr = fric_slope(v, t)
            row += [t["kp"] + lsf, fr, pp + fr]
        pr("   %6.1f %9.4f | %9.4f %9.4f %8.4f | %9.4f %9.4f %8.4f" % tuple(row))
    pr("")
    pr("   🛑 THE PRESET DOES NOT LOWER THE LOW-SPEED LOOP GAIN.  (kp+lsf) at 5 m/s is 5.36 at the")
    pr("   preset vs 5.96 live -- only x0.90 -- because lsf 5.06 dominates kp.  And the FRICTION")
    pr("   term scales as (1+lsf/kp), which is LARGER at the smaller kp: %.4f vs %.4f."
       % (fric_slope(5.0, PRESET), fric_slope(5.0, LIVE)))
    pr("   ⇒ at 5 m/s the preset's total small-signal gain is %.4f, the live tune's %.4f: the"
       % ((PRESET["kp"] + lsf_of(5)) / 6.0 + fric_slope(5, PRESET),
          (LIVE["kp"] + lsf_of(5)) / 6.0 + fric_slope(5, LIVE)))
    pr("   PRESET IS THE HIGHER-GAIN CONFIGURATION AT CREEP SPEED.  [EVIDENCE -- fork source.]")

    # ---------------- 3. the control: reproduce the measured V282 |L|
    pr("")
    pr("3. CONTROL -- does the model reproduce the record's MEASURED V282 outer |L| at the ring?")
    pr("-" * 118)
    l20 = []
    for fid in NAMED:
        for v in (5.0, 12.5, 28.5):
            r2, _, _, _ = make_rate_fns(c282, c293, plants, fid)
            Lv = (C_lin(F, v, LIVE) + fric_slope(v, LIVE)) * P_of(F, v, r2, 0.20, 1.0)
            l20.append(float(np.interp(20.0, F, np.abs(Lv))))
    lo, hi = min(l20), max(l20)
    ok = (lo <= 0.20) and (hi >= 0.02) and (hi <= 0.60)
    pr("   model |L| at 20 Hz over 4 fits x 3 speeds spans %.4f - %.4f  vs measured 0.026-0.165" % (lo, hi))
    pr("   (bound 0.189; accepted if it overlaps and does not exceed x3 the bound)  ->  %s"
       % ("CONTROL PASSES" if ok else "CONTROL FAILS -- nothing below is reportable"))

    # ---------------- 4. THE B6 GRID
    pr("")
    pr("=" * 118)
    pr("4. THE B6 GRID -- speeds x kappa (0.50..2.00 step 0.05) x tau, fit 225")
    pr("   FAIL = unstable, or PM < 30 deg, or a 1-4 Hz limit cycle.  For each (build, tune, tau)")
    pr("   the WORST cell over the whole kappa sweep is reported, with the kappa and speed it is at.")
    pr("=" * 118)
    cases = [("V293", r293, PRESET), ("V293", r293, LIVE), ("V282", r282, PRESET), ("V282", r282, LIVE)]
    worst = {}
    for name, rfn, tune in cases:
        for tau in TAUS:
            rows = []
            for v in SPEEDS:
                base = C_lin(F, v, tune) + fric_slope(v, tune)
                for kap in KAPPAS:
                    Lv = base * P_of(F, v, rfn, tau, kap)
                    m = margins(Lv, F)
                    uns, bad = nyquist_unstable(Lv, F)
                    pmv = m["pm"] if np.isfinite(m["pm"]) else 999.0
                    rows.append((pmv, uns, v, kap, m))
            rows.sort(key=lambda r: (not r[1], r[0]))
            pmv, uns, v, kap, m = rows[0]
            nfail = sum(1 for r in rows if r[1] or r[0] < 30.0)
            worst[(name, tune["name"], tau)] = (pmv, uns, v, kap, m, nfail, len(rows))
            pr("   %-5s %-20s tau %.2f | worst: v %4.1f kappa %.2f | PM %7.1f  Ms %5.2f  fc %5.2f Hz"
               "  %s | cells failing %d/%d"
               % (name, tune["name"], tau, v, kap, pmv if pmv < 900 else float("nan"),
                  m["Ms"], m["fc"], "UNSTABLE" if uns else "stable", nfail, len(rows)))

    # ---------------- 5. per-speed detail at tau 0.20, the record's delay
    pr("")
    pr("5. DETAIL at tau = 0.20 s (the record's own liveDelay.lateralDelay)")
    pr("-" * 118)
    for name, rfn, tune in cases:
        pr("")
        pr("   %s  --  %s   (LAF %.1f Kp %.2f Ki %.2f friction %.2f)"
           % (name, tune["name"], tune["laf"], tune["kp"], tune["ki"], tune["fric"]))
        pr("   %6s | %-34s | %-34s | %-34s" % ("v", "kappa 0.50", "kappa 1.00", "kappa 2.00"))
        pr("   %6s | %8s %6s %6s %7s | %8s %6s %6s %7s | %8s %6s %6s %7s"
           % ("", "|L|1Hz", "Ms", "fc", "PM", "|L|1Hz", "Ms", "fc", "PM", "|L|1Hz", "Ms", "fc", "PM"))
        for v in SPEEDS:
            base = C_lin(F, v, tune) + fric_slope(v, tune)
            cells = []
            for kap in (0.5, 1.0, 2.0):
                Lv = base * P_of(F, v, rfn, 0.20, kap)
                m = margins(Lv, F)
                uns, _ = nyquist_unstable(Lv, F)
                cells += [float(np.interp(1.0, F, np.abs(Lv))), m["Ms"], m["fc"],
                          (-999.0 if uns and not np.isfinite(m["pm"]) else m["pm"])]
            pr("   %6.1f | %8.4f %6.2f %6.2f %7.1f | %8.4f %6.2f %6.2f %7.1f | %8.4f %6.2f %6.2f %7.1f"
               % tuple([v] + cells))

    # ---------------- 6. the limit-cycle test (describing function + nonlinear sim)
    pr("")
    pr("=" * 118)
    pr("6. THE 1-4 Hz LIMIT CYCLE -- describing function, then a full nonlinear simulation")
    pr("=" * 118)
    pr("   The friction compensator is a SATURATION: gain (fric/thr)*(1+lsf/kp) at small error,")
    pr("   falling as 1/E above err_lsf = thr = 0.30, i.e. above a RAW error of thr/(1+lsf/kp).")
    pr("   If the loop is unstable at SMALL amplitude and stable at LARGE, a stable limit cycle")
    pr("   exists -- this is the classical Coulomb-compensator cycle and it is the V276 shape.")
    pr("")
    pr("   %-5s %-20s %5s %5s %6s | %-24s | %-26s" %
       ("bld", "tune", "v", "kappa", "tau", "small-amp / large-amp", "limit cycle?"))
    lc_hits = []
    for name, rfn, tune in cases:
        for tau in (0.20,):
            for v in SPEEDS:
                for kap in (0.5, 1.0, 1.5, 2.0):
                    small = C_lin(F, v, tune) + fric_slope(v, tune)
                    large = C_lin(F, v, tune)
                    Ls = small * P_of(F, v, rfn, tau, kap)
                    Ll = large * P_of(F, v, rfn, tau, kap)
                    us, bs = nyquist_unstable(Ls, F)
                    ul, bl = nyquist_unstable(Ll, F)
                    if not us:
                        continue
                    fcyc = bs[0][0] if bs else np.nan
                    inband = (not ul) and (1.0 <= fcyc <= 4.0)
                    lc_hits.append((name, tune["name"], v, kap, fcyc, inband, us, ul))
                    pr("   %-5s %-20s %5.1f %5.2f %6.2f | %-24s | %s at %.2f Hz %s" %
                       (name, tune["name"], v, kap, tau,
                        ("UNSTABLE / " + ("UNSTABLE" if ul else "stable")),
                        "LIMIT CYCLE" if inband else ("divergent" if ul else "cycle"),
                        fcyc, "<-- 1-4 Hz, B6 FAIL" if inband else ""))
    if not lc_hits:
        pr("   (no cell of any build/tune is unstable at small amplitude -- no limit cycle predicted)")

    pr("")
    pr("   NONLINEAR TIME-DOMAIN CONTROL (dt = 0.01 s, the fork's own; 0.02 m/s^2 kick; 40 s;")
    pr("   plant = fit 225 shape + the fork's identified spring k(v); actuator clip +-1):")
    pr("   %-5s %-20s %5s %5s | %9s %9s %8s %7s" %
       ("bld", "tune", "v", "kappa", "amp early", "amp late", "f_osc", "verdict"))
    for name, rfn, tune in cases:
        for v in (5.0, 8.0, 12.5, 28.5):
            for kap in (1.0, 2.0):
                dc = float(np.real(rfn(np.array([1e-4]), v)[0]))
                s = sim(v, tune, dc, 0.20, kap, plants[225])
                vd = "GROWS" if s["grew"] else "decays"
                pr("   %-5s %-20s %5.1f %5.2f | %9.5f %9.5f %8.3f %7s"
                   % (name, tune["name"], v, kap, s["a_early"], s["a_late"], s["fosc"], vd))

    # ---------------- 7. the broken-check on STOCK
    pr("")
    pr("=" * 118)
    pr("7. THE BROKEN-CHECK -- the identical criterion on V282 (FLOWN) and on STOCK")
    pr("=" * 118)
    sp = L.FW + "stock_fw_dump/code.bin"
    if os.path.exists(sp):
        try:
            cs = L.read_cells(sp)
            slope_stock = 141.4 * (float(np.max(cs["map_Y"])) / float(np.max(c282["map_Y"])))
            fnS, RdcS = stock_rate_fn(cs, c282, plants, 225)
            pr("   stock cells: Kp bank %s   fb clamp %s   r24 arm %s   map top %s (V282 %s)"
               % (cs["kp_Y"], cs["fb_clamp"], cs["r24_arm"], int(np.max(cs["map_Y"])),
                  int(np.max(c282["map_Y"]))))
            pr("   R_servo(0) stock = %.4f (V282 %.4f) ; stock map slope = %.1f deg/s per unit"
               % (RdcS, Rdc, slope_stock))
            pr("   %6s | %-30s | %-30s" % ("v", "STOCK preset kappa 1 / 2", "STOCK live kappa 1 / 2"))
            for v in SPEEDS:
                out = [v]
                for tune in (PRESET, LIVE):
                    for kap in (1.0, 2.0):
                        base = C_lin(F, v, tune) + fric_slope(v, tune)
                        Lv = base * P_of(F, v, lambda f, vv: fnS(f, vv, slope_stock), 0.20, kap)
                        m = margins(Lv, F)
                        uns, _ = nyquist_unstable(Lv, F)
                        out += [(-999.0 if uns else (m["pm"] if np.isfinite(m["pm"]) else 999.0))]
                pr("   %6.1f | PM %8.1f  %8.1f          | PM %8.1f  %8.1f" % tuple(out))
        except Exception as e:                                            # noqa: BLE001
            pr("   stock cells unreadable by the V282 cell map: %s" % e)
    else:
        pr("   stock image not at %s" % sp)

    # ---------------- 8. the feedforward hazard
    pr("")
    pr("=" * 118)
    pr("8. THE HAZARD OF FLYING V293 WITHOUT THE PRESET -- the feedforward, sized")
    pr("=" * 118)
    pr("   `get_honda_accord_rate_plant_ff`: hold = k(v)*angle/G(v) ; move = 0.5*d(angle)/dt/G(v).")
    pr("   Both divide by G(v) = the RATE-SERVO closed-loop gain.  In torque mode the true gain is")
    pr("   k_map_unit*g0(v), so every FF term is over-commanded by exactly the ratio below.")
    pr("   %6s %10s %12s %10s %14s %14s" %
       ("v", "G_v282", "V293 rate", "FF x", "hold tq @10deg", "delivered angle"))
    for v in SPEEDS:
        G, Ldc, g0 = g0_of_v(v, Rdc)
        r = kmap_unit * g0
        kk = float(np.interp(v, KV_BP, KV_V))
        hold = kk * 10.0 / G
        # what that torque actually holds on the torque-mode plant: angle = rate/k = tq*r/k
        ang = hold * r / kk
        pr("   %6.1f %10.1f %12.1f %10.2f %14.4f %12.1f deg" % (v, G, r, r / G, hold, ang))
    pr("")
    pr("   The `hold` term asks for the torque that holds 10 deg on the RATE plant; on the TORQUE")
    pr("   plant the same torque settles at the angle in the last column.  The over-command IS the")
    pr("   ratio column.  [EVIDENCE for the arithmetic; BELIEF for the settling model, which uses")
    pr("   the fork's own k(v) and the back-solved plant gain.]")

    open(os.path.join(SCR, "v293_b6_outer.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("")
    pr("wrote _scratch/v293_b6_outer.txt")


if __name__ == "__main__":
    os.makedirs(SCR, exist_ok=True)
    main()
