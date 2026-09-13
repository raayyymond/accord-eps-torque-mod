# -*- coding: utf-8 -*-
"""studies/grind/r24_lane_transfer.py -- L_r24(f), the ENGAGED-ONLY r24 BASE-ASSIST RATE LANE's contribution to
the return ratio around the wheel, 3-30 Hz, in the SAME units and sign convention as loopshape20_loop_model's
servo arm R(f), so the two can be SUMMED:   L_tot(f) = L_servo(f) + L_r24(f).
Subagent r24lane, 2026-09-13.  ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing on any bus.

THE LANE, from the bytes (the kit's own mirror, v282_r24_tap_read.r24_series, re-derived by the tracer 2026-09-13):
    u        = bar torque (gp-0x4f62, the dual-channel lockstep-mirrored torsion-bar sensor), 1 kHz
    d[n]     = 0.5 * (u[n] - u[n-4])          lag-4 backward difference at 1 kHz  (4 ms)
    d        = clip(d, -5120, +5120)          pre-gain clamp
    s        = trunc(d * gain / 1024)         gain = 0xC6446 = 5244 when engaged (Q10, signed mul + sar 0xa)
    s        = 0 if |s| <= 3 else s - sign(s)*3           deadband, cal 0xC61F6 = 3
    gp-0x6ada= clip(-s, -8192, +8192)         NOTE THE NEGATION; then summed with UNIT COEFFICIENT into the
                                              aggregator gp-0x6b94 (clamp +-0x2800) alongside the LKAS lane T.
So, LINEARISED (deadband and both clamps set aside -- see DEADBAND below):
    R_r24(f) = -(gain/1024) * D4(f) * B(f),   D4(f) = 0.5*(1 - exp(-j 2 pi f * 0.004))
    L_r24(f) = R_r24(f) * CPD * G_d(f)        CPD = 8 raw rate counts per deg/s; G_d = the same plant the
                                              servo arm sees, because the two lanes are 1:1 in the aggregator.

B(f) = bar counts per raw rate count, MEASURED on V282 routes r39 + r6c by sibling agent `bof`
(b_of_f_v282.py, B-OF-F-V282-2026-09-13.md).  This module fits B to a CAUSAL DISCRETE RATIONAL so the
r24 arm can enter the characteristic polynomial exactly (adv_v290_physics.poles works in w = z^-1).

CONVENTION (pinned three ways, see TRACE-2026-09-13-r24-lane-transfer.md):
    x = gp-0x6a56 = -(0x18F wire rate).  Both arms are "aggregator counts per raw count of x".
    POSITIVE REAL PART = DAMPING.  Char. eq. 1 + L_tot = 0 (adv_v290_physics.poles / loopshape20.margins).
    The 7.3 Hz gate of LOOPSHAPE-LAGPOLE-KD Sec.4 lives in the OTHER (positive-return, critical point +1)
    convention and is a NORMALISED split (Ls + Lr == 1); gate73_gen() below generalises it and is
    scale-free -- it never needs |r24| in absolute counts.

MAGNITUDE UNCERTAINTY -- READ THIS BEFORE USING |L_r24|:
    kappa scales |R_r24|.  kappa = 1.0 is the closed form at the flown 0xC6446 = 5244.
    The cave's own bit-6 comparator (|r24| >= |T|, computed INSIDE the ECU at full precision, so scale-free
    in r24-vs-T) inverts to an effective arm 2268-2747 over 8 strata x 2 routes => kappa = 0.45.
    The record's normalised 7.3 Hz split (LS73/LR73) implies kappa ~ 1.45 instead.  The two disagree by 3x
    and THE KIT HAS NEVER CLOSED THIS.  Default here is KAPPA_WIRE = 0.45 (the scale-free instrument);
    every headline is also reported at kappa = 1.0.  PHASE is unaffected and is confirmed to -14..+8 deg.

Run:  python r24_lane_transfer.py           (writes _scratch/r24_lane_transfer.txt and .json beside it)
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import adv_v290_physics as A                   # noqa: E402  Blocks/Plant/poles/mode_pole/pmul/padd/pev/LS73/LR73
import b_of_f_v282 as BF                       # noqa: E402  the measured B(f)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TS, FS, CPD = A.TS, A.FS, A.CPD
GAIN_FLOWN = 5244.0
KAPPA_WIRE = 0.45                 # bit-6 duty inversion, 8 strata x 2 routes (b_of_f_v282.GAIN_EFFECTIVE/5244)
FREQS = [3.0, 3.9, 5.0, 6.0, 7.3, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.3, 22.0, 25.0, 30.0]
F_RING, F_STUT = 20.3, 7.3
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def w_of(f):
    return np.exp(-2j * np.pi * np.asarray(f, float) * TS)      # w = z^-1


# ------------------------------------------------------------------------------------------- B(f) as a rational
def fit_B(stratum, route="V282pool", which="Hv", nb=1, nd=4, iters=25, fmin=3.0, fmax=30.0):
    """Sanathanan-Koerner fit of a causal discrete rational B(w) = (1-w)(1+w)*Nb(w)/Db(w) to the MEASURED B.

    TWO STRUCTURAL ZEROS ARE IMPOSED, and both are physics, not convenience:
      (1-w)  =>  B -> 0 at DC.  The bar twist vanishes for a steady rate; the measurement independently
                 prefers this (bof Sec.4: the 'spring'/integrator form fits ~3x worse).
      (1+w)  =>  B -> 0 at Nyquist.  Above the column/rack mode the pinion is inertially pinned, so the
                 bar reads k_tb * integral(rate) and |B| ~ 1/f.  The data agree (|B| 3.10 -> 2.83 -> 2.14
                 over 18 -> 20.3 -> 25 Hz).
    WITHOUT the Nyquist zero the fit is IMPROPER and extrapolates to |B| = 16,000 at 400 Hz against a
    measured ~2 -- which injects a fictitious 80,000-count r24 arm into the characteristic polynomial and
    silently destroys every pole computation.  nb + 2 <= nd is enforced for the same reason.
    Weighted by coherence; unusable points (coh < 0.40) dropped.  Returns (num, den) in w + residuals."""
    if nb + 2 > nd:
        raise ValueError("fit_B needs nb + 2 <= nd for a proper, HF-rolling-off B; got nb=%d nd=%d" % (nb, nd))
    r = BF._rows(stratum, route)
    col = {"H1": 1, "Hv": 2, "H2": 3}[which]
    ok = (r[:, 5] >= BF.COH_MIN) & (r[:, 0] >= fmin) & (r[:, 0] <= fmax)
    f, mag, ph, coh = r[ok, 0], r[ok, col], np.radians(r[ok, 4]), r[ok, 5]
    # densify: the 15 tabulated points are few for a 6-parameter fit, so interpolate the USABLE ones
    fd = np.geomspace(f.min(), f.max(), 160)
    Bd = BF.B_table(fd, stratum, route, which=which)
    cd = np.interp(fd, r[:, 0], r[:, 5])
    wgt = np.interp(fd, f, coh) * cd
    w = w_of(fd)
    zero = (1.0 - w) * (1.0 + w)                       # enforced zeros at DC and at Nyquist
    Dprev = np.ones_like(w)
    num = den = None
    for _ in range(iters):
        # rows: [zero*w^0 .. zero*w^nb | -B*w^1 .. -B*w^nd] . [nb+1 num coefs, nd den coefs] = B  (den[0]=1)
        M = np.zeros((len(w), nb + 1 + nd), complex)
        for k in range(nb + 1):
            M[:, k] = zero * w ** k
        for k in range(nd):
            M[:, nb + 1 + k] = -Bd * w ** (k + 1)
        rhs = Bd
        sw = (wgt / np.abs(Dprev))[:, None]
        Mr = np.vstack([np.real(M * sw), np.imag(M * sw)])
        rr = np.concatenate([np.real(rhs * sw[:, 0]), np.imag(rhs * sw[:, 0])])
        sol, *_ = np.linalg.lstsq(Mr, rr, rcond=None)
        nc, dc = sol[:nb + 1], np.concatenate([[1.0], sol[nb + 1:]])
        num = A.pmul(np.array([1.0, 0.0, -1.0]), nc)   # (1 - w)(1 + w) * Nb(w)
        den = dc
        Dnew = A.pev(den, fd)
        if np.max(np.abs(Dnew - Dprev)) < 1e-12:
            Dprev = Dnew; break
        Dprev = Dnew
    Bfit = A.pev(num, fd) / A.pev(den, fd)
    err_db = float(np.sqrt(np.mean((wgt * (np.abs(np.log(np.abs(Bfit / Bd))))) ** 2) / np.mean(wgt ** 2)))
    err_ph = float(np.degrees(np.sqrt(np.mean((wgt * np.angle(Bfit / Bd)) ** 2) / np.mean(wgt ** 2))))
    stable = bool(np.all(np.abs(np.roots(den[::-1])) > 1.0)) if len(den) > 1 else True   # |w| > 1 <=> |z| < 1
    return dict(num=num, den=den, rms_ln_mag=err_db, rms_phase_deg=err_ph, stable=stable,
                n=int(ok.sum()), stratum=stratum, route=route, which=which)


def D4_poly():
    """0.5 * (1 - w^4), exactly the firmware's lag-4 backward difference at 1 kHz."""
    return np.array([0.5, 0.0, 0.0, 0.0, -0.5]), np.array([1.0])


def R_r24_poly(bfit, gain=GAIN_FLOWN, kappa=1.0, extra=None):
    """(num, den) in w for R_r24 = -kappa*(gain/1024)*D4(w)*B(w)*extra(w).  extra = an optional added filter."""
    dn, dd = D4_poly()
    num = A.pmul(dn, bfit["num"]) * (-kappa * gain / 1024.0)
    den = A.pmul(dd, bfit["den"])
    if extra is not None:
        num, den = A.pmul(num, extra[0]), A.pmul(den, extra[1])
    return num, den


def Rf(poly, f):
    return A.pev(poly[0], f) / A.pev(poly[1], f)


# ------------------------------------------------------------------------------------- loop with BOTH arms
def loop2(el, pl, r24):
    """(num, den) of L_tot = (R_servo + R_r24) * CPD * G, in w.  Same shape as adv_v290_physics.loop()."""
    rn, rd = el.R()
    sn, sd = r24
    tn = A.padd(A.pmul(rn, sd), A.pmul(sn, rd))
    td = A.pmul(rd, sd)
    return A.pmul(tn, pl.num) * CPD, A.pmul(td, pl.den)


def poles2(el, pl, r24):
    n, d = loop2(el, pl, r24)
    ch = A.padd(d, n)
    w = np.roots(ch[::-1]); w = w[np.abs(w) > 1e-12]
    z = 1.0 / w
    s = np.log(z) * FS
    return np.abs(s.imag) / (2 * np.pi), -s.real / np.abs(s), z


def mode2(el, pl, r24, lo=12.0, hi=32.0):
    f, zeta, z = poles2(el, pl, r24)
    m = (f >= lo) & (f <= hi)
    if not m.any():
        return np.nan, np.nan
    k = int(np.argmin(zeta[m]))
    return float(f[m][k]), float(zeta[m][k])


def unstable2(el, pl, r24):
    _, _, z = poles2(el, pl, r24)
    return bool(np.any(np.abs(z) >= 1.0))


# ------------------------------------------------------------------------------------------ the 7.3 Hz gate
def gate73_gen(Rs_ratio=1.0, Rr_ratio=1.0):
    """GENERALISED LOOPSHAPE-LAGPOLE-KD Sec.4 gate: |Ls*Rs + Lr*Rr| with Ls+Lr == 1 (normalised split).
    Rs_ratio = the SERVO arm's new/today ratio at 7.3 Hz; Rr_ratio = the r24 arm's.  Both are RATIOS, so
    this inherits none of the |r24| scale problem.  Today = |Ls + Lr| = 1.003.  <= 1.000 is the record's gate."""
    return float(abs(A.LS73 * Rs_ratio + A.LR73 * Rr_ratio))


# ------------------------------------------------------------------------------------------------ candidates
def bp_cave(f0, Q, kind="hp", fs=FS):
    """A first/second-order shaping block that a cave could add on r24, as (num, den) in w, DC-exact forms:
       'hp'  one-pole high-pass  y = x - lp(x),  lp = (1-a)/(1-a w),  a = exp(-2 pi f0 / fs)   [kills DC]
       'bp'  hp(f0) * lp(fhi=Q)  (Q reused as the upper corner in Hz)
       'notch'/'lead' are already in adv_v290_physics; not repeated here."""
    a = float(np.exp(-2 * np.pi * f0 / fs))
    lp = (np.array([1 - a]), np.array([1.0, -a]))
    hp = (A.padd(lp[1], -lp[0]), lp[1])                       # 1 - lp
    if kind == "hp":
        return hp
    if kind == "bp":
        a2 = float(np.exp(-2 * np.pi * Q / fs))
        lp2 = (np.array([1 - a2]), np.array([1.0, -a2]))
        return A.pmul(hp[0], lp2[0]), A.pmul(hp[1], lp2[1])
    raise ValueError(kind)


def main():
    c, _ = A.read_v289()
    c282 = dict(c); c282["fb_a"], c282["fb_b"] = 923, 1560
    el282 = A.Blocks(c282, False, 0.0)

    pr("=" * 118)
    pr("L_r24(f) -- the r24 base-assist rate lane's arm of the return ratio.  V282.  r24lane, 2026-09-13.")
    pr("=" * 118)
    pr("convention: aggregator counts per raw count of x = gp-0x6a56 = -(0x18F rate); POSITIVE REAL = DAMPING;")
    pr("            char. eq. 1 + L_tot = 0 with L_tot = L_servo + L_r24 (unit-coefficient aggregator, 1:1).")
    pr("R_r24(f) = -kappa*(5244/1024)*D4(f)*B(f);  D4 = 0.5*(1 - exp(-j2pi f 0.004));  B measured r39+r6c.")
    pr("kappa = 1.00 closed form at the flown 0xC6446 = 5244;  kappa = 0.45 the cave bit-6 duty inversion.")
    pr("")

    # ---- 1. B(f) fits
    pr("-" * 118)
    pr("1.  B(f) fitted to a CAUSAL DISCRETE RATIONAL (SK iteration, coherence-weighted, DC zero enforced)")
    pr("-" * 118)
    fits = {}
    pr("%-20s %5s %5s %10s %10s %8s" % ("stratum", "nb", "nd", "rms ln|B|", "rms ph deg", "stable"))
    for st in ("creep_1_3med", "loaded_idx68med", "creep_1_3", "loaded_any", "all_eng"):
        best = None
        for nb in (0, 1, 2, 3):
            for nd in (nb + 2, nb + 3, nb + 4):
                try:
                    fb = fit_B(st, nb=nb, nd=nd)
                except Exception:
                    continue
                if not fb["stable"]:
                    continue
                sc = fb["rms_ln_mag"] + fb["rms_phase_deg"] / 60.0
                if best is None or sc < best[0]:
                    best = (sc, nb, nd, fb)
        if best is None:
            pr("%-20s  NO STABLE FIT" % st); continue
        _, nb, nd, fb = best
        fits[st] = fb
        pr("%-20s %5d %5d %10.4f %10.2f %8s" % (st, nb, nd, fb["rms_ln_mag"], fb["rms_phase_deg"], fb["stable"]))
    pr("")

    # ---- 2. the transfer table
    pr("-" * 118)
    pr("2.  R_r24(f) AND L_servo(f)'s arm R(f), both 'counts per raw rate count'.  kappa = 1.00 (closed form)")
    pr("-" * 118)
    st_ring, st_stut = "creep_1_3med", "loaded_idx68med"
    r24_ring = R_r24_poly(fits[st_ring]); r24_stut = R_r24_poly(fits[st_stut])
    pr("%6s | %9s %8s %8s | %9s %8s %8s | %9s %8s | %7s %7s" %
       ("f Hz", "|R_r24|c", "ang", "Re", "|R_r24|l", "ang", "Re", "|R_srv|", "ang", "cohC", "cohL"))
    tab = []
    for f in FREQS:
        rc, rl, rs = Rf(r24_ring, f), Rf(r24_stut, f), el282.Rf(f)
        tab.append(dict(f=f, r24_creep=[abs(rc), float(np.degrees(np.angle(rc)))],
                        r24_loaded=[abs(rl), float(np.degrees(np.angle(rl)))],
                        servo=[abs(rs), float(np.degrees(np.angle(rs)))],
                        coh_creep=float(BF.coherence(f, st_ring)), coh_loaded=float(BF.coherence(f, st_stut))))
        pr("%6.1f | %9.3f %+8.1f %+8.3f | %9.3f %+8.1f %+8.3f | %9.3f %+8.1f | %7.2f %7.2f" %
           (f, abs(rc), np.degrees(np.angle(rc)), rc.real, abs(rl), np.degrees(np.angle(rl)), rl.real,
            abs(rs), np.degrees(np.angle(rs)), BF.coherence(f, st_ring), BF.coherence(f, st_stut)))
    pr("  (c = creep 1-3 m/s median-gated; l = loaded idx>=68 median-gated.  coh < 0.40 => B NOT IDENTIFIED:")
    pr("   10-14 Hz is a FIT, not a measurement, in every stratum.)")
    pr("")

    # ---- 3. the damping budget at the ring -- PLANT-FREE
    pr("-" * 118)
    pr("3.  THE 20 Hz DAMPING BUDGET -- PLANT-FREE.  Both lanes enter the SAME aggregator with UNIT")
    pr("    coefficients, so dzeta_lane is proportional to Re(R_lane) with the SAME constant of")
    pr("    proportionality.  The RATIO needs no plant, no scale and no sign convention.")
    pr("-" * 118)
    pr("  %-34s | %8s %8s %8s | %8s" % ("term at 20.3 Hz (creep)", "|R|", "ang", "Re", "share"))
    rs = el282.Rf(F_RING)
    budget = {}
    for kappa in (1.00, 0.45):
        rr = Rf(R_r24_poly(fits[st_ring], kappa=kappa), F_RING)
        tot = rs.real + rr.real
        budget[kappa] = dict(servo=[abs(rs), float(np.degrees(np.angle(rs))), rs.real],
                             r24=[abs(rr), float(np.degrees(np.angle(rr))), rr.real],
                             share_r24=rr.real / tot)
        pr("  %-34s | %8.3f %+8.1f %+8.3f | %7.1f%%" %
           ("r24 at 5244, kappa %.2f" % kappa, abs(rr), np.degrees(np.angle(rr)), rr.real, 100 * rr.real / tot))
    pr("  %-34s | %8.3f %+8.1f %+8.3f | %7.1f%%" %
       ("LKAS servo (model, Kp 248)", abs(rs), np.degrees(np.angle(rs)), rs.real,
        100 * rs.real / (rs.real + Rf(R_r24_poly(fits[st_ring]), F_RING).real)))
    pr("  %-34s | %8.3f %+8.1f %+8.3f | %8s" % ("LKAS servo (MEASURED, 427 tap)", 1.90, -69.0, 0.68, "record"))
    pr("  %-34s | %8.3f %+8.1f %+8.3f | %8s" % ("r24 (record closed form)", 3.23, +5.0, 3.22, "record"))
    pr("  => r24 supplies %.0f%% (kappa 1.00) to %.0f%% (kappa 0.45) of the ELECTRONIC damping at the ring."
       % (100 * budget[1.00]["share_r24"], 100 * budget[0.45]["share_r24"]))
    pr("     The record's figure was 83%. The claim SURVIVES at BOTH ends of the scale bracket.")
    pr("")
    pr("  SAME BUDGET AT 7.3 Hz LOADED (the strong-turn stutter), where the sign REVERSES:")
    rs7 = el282.Rf(F_STUT)
    for kappa in (1.00, 0.45):
        rr7 = Rf(R_r24_poly(fits[st_stut], kappa=kappa), F_STUT)
        pr("  kappa %.2f : servo Re %+7.3f  +  r24 Re %+7.3f  =  NET %+7.3f   (%s)"
           % (kappa, rs7.real, rr7.real, rs7.real + rr7.real,
              "net DAMPING" if rs7.real + rr7.real > 0 else "net PUMPING"))
    pr("  On the car, V281 rev 3 (this Kp 248) EXTINGUISHED the self-sustained 7 Hz cycle (F7 0.0 / 100 s).")
    pr("  Only the kappa 0.45 row is consistent with that. [EVIDENCE arithmetic; BELIEF the inference]")
    pr("")

    # ---- 4. the pole, on a family RE-FITTED with r24 in the loop
    pr("-" * 118)
    pr("4.  THE CLOSED-LOOP POLE, on a plant family RE-FITTED WITH r24 IN THE LOOP")
    pr("    (the existing design290b family fitted a loop MISSING ~65 % of its own return ratio at 20 Hz,")
    pr("     so its g0/zp have ABSORBED r24; adding r24 on top of it double-counts and 0 of 304 survive)")
    pr("-" * 118)
    res, dz = {}, {}
    rfp = os.path.join(SCR, "r24_plant_refit.json")
    if not os.path.exists(rfp):
        pr("  _scratch/r24_plant_refit.json not present -- run r24_plant_refit.py first.  SKIPPED.")
    else:
        fam = json.load(open(rfp))
        for kappa in (1.00, 0.45):
            key = "k%.2f_s+1" % kappa
            ps = fam.get(key, [])
            keep = [(p, A.Plant(dict(g0=p["g0"], tau=p["tau"], f1=p["f1"], fp=p["fp"], zp=p["zp"],
                                     kappa=p["kappa"], label="m"), 1.0, "m"), p["f282"], p["z282"]) for p in ps]
            res[kappa] = keep
            n289 = sum(1 for p in ps if p.get("ok289"))
            pr("  kappa %.2f : %5d plants reproduce the measured V282 pole WITH r24 in;  %d of them ALSO"
               " reproduce V289's measured 16.5 Hz pole" % (kappa, len(keep), n289))
        pr("")
        pr("  🛑 THE V289 CONSTRAINT IS THE PROBLEM, AND IT IS INFORMATIVE.  V289 relocated the mode")
        pr("     20.1 -> 16.5 Hz with a notch that sits ONLY IN THE SERVO ARM, and that is MEASURED on the")
        pr("     car (18-22 Hz band empty, 0 of 1414 windows).  A servo-side notch can only do that if the")
        pr("     servo arm is most of the loop at 20 Hz.  If r24 really carried 65 % of it, the notch would")
        pr("     have had far less authority.  => V289's on-car result BOUNDS |r24| FROM ABOVE, independently")
        pr("     of the bit-6 duty.  See _scratch/kappa_scan.py for the scan that sizes that bound.")
        pr("")
        for kappa in (1.00, 0.45):
            keep = res.get(kappa) or []
            if not keep:
                continue
            rows = []
            for k in (1.00, 0.75, 0.50, 0.33, 0.10, 0.00):
                r24k = R_r24_poly(fits[st_ring], kappa=kappa * k)
                fz = [mode2(el282, pl, r24k) for _, pl, _, _ in keep]
                z_ = np.array([b for a, b in fz]); f_ = np.array([a for a, b in fz])
                un = float(np.mean([unstable2(el282, pl, r24k) for _, pl, _, _ in keep]))
                rows.append((k, float(np.nanmedian(f_)), float(np.nanmedian(z_)),
                             float(np.nanpercentile(z_, 10)), float(np.nanpercentile(z_, 90)), un))
            dz[kappa] = rows
            pr("  kappa %.2f  (%d plants)" % (kappa, len(keep)))
            pr("  %8s | %8s | %8s %8s %8s | %8s | %8s" %
               ("0xC6446", "f_cl Hz", "zeta md", "z p10", "z p90", "unstable", "gate73"))
            for k, fm, zm, z10, z90, un in rows:
                pr("  %8.0f | %8.2f | %8.4f %8.4f %8.4f | %8.2f | %8.4f" %
                   (k * GAIN_FLOWN, fm, zm, z10, z90, un, gate73_gen(1.0, k)))
            pr("  => on THIS family, r24 at 5244 contributes dzeta(20 Hz) = %+.4f (zeta %.4f with, %.4f without)"
               % (rows[0][2] - rows[-1][2], rows[0][2], rows[-1][2]))
            pr("")

    # ---- 5. options priced
    pr("-" * 118)
    pr("5.  THE r24 DESIGN AXIS, PRICED ON BOTH SYMPTOMS")
    pr("-" * 118)
    pr("  gate73 = |Ls*Rs(7.3) + Lr*Rr(7.3)|, Ls 0.55/+96, Lr 1.19/-27, TODAY = %.4f.  <= 1.000 = the record's"
       % gate73_gen(1.0, 1.0))
    pr("  gate; >= 1.000 re-arms the 7 Hz strong-turn cycle.  Rs held at 1.0 here (servo unchanged).")
    pr("")
    cands = [("(a) 0xC6446 x0.75 -> 3933", ("scale", 0.75)),
             ("(a) 0xC6446 x0.50 -> 2622", ("scale", 0.50)),
             ("(a) 0xC6446 x0.33 -> 1731", ("scale", 0.33)),
             ("(a) 0xC6446 x0.10 ->  524", ("scale", 0.10)),
             ("(a) 0xC6446 -> 2048 (Honda)", ("scale", 2048.0 / 5244.0)),
             ("(b) HP 5 Hz on r24 (cave)", ("filt", ("hp", 5.0, None))),
             ("(b) HP 8 Hz on r24 (cave)", ("filt", ("hp", 8.0, None))),
             ("(b) HP 12 Hz on r24 (cave)", ("filt", ("hp", 12.0, None))),
             ("(b) BP 8-40 Hz on r24 (cave)", ("filt", ("bp", 8.0, 40.0))),
             ("(b) BP 12-60 Hz on r24 (cave)", ("filt", ("bp", 12.0, 60.0)))]
    pr("  %-30s | %8s | %8s %8s | %9s %8s | %8s" %
       ("candidate", "gate73", "|Rr|7.3", "ang", "|Rr|20.3", "ang", "dzeta20"))
    base_ring = Rf(R_r24_poly(fits[st_ring]), F_RING)
    base_stut = Rf(R_r24_poly(fits[st_stut]), F_STUT)
    opt = []
    for name, (kind, arg) in cands:
        if kind == "scale":
            ex = None; sc = arg
        else:
            k2, f0, fh = arg
            ex = bp_cave(f0, fh if fh else 0.0, kind=k2); sc = 1.0
        rr73 = Rf(R_r24_poly(fits[st_stut], kappa=sc, extra=ex), F_STUT) / base_stut
        rr203 = Rf(R_r24_poly(fits[st_ring], kappa=sc, extra=ex), F_RING) / base_ring
        row = dict(name=name, gate73=gate73_gen(1.0, rr73),
                   rr73=[abs(rr73), float(np.degrees(np.angle(rr73)))],
                   rr203=[abs(rr203), float(np.degrees(np.angle(rr203)))])
        for kappa in (1.00, 0.45):
            keep = res.get(kappa) or []
            if not keep:
                continue
            r24n = R_r24_poly(fits[st_ring], kappa=kappa * sc, extra=ex)
            fz = [mode2(el282, pl, r24n) for _, pl, _, _ in keep]
            z_ = np.array([b for a, b in fz]); f_ = np.array([a for a, b in fz])
            zbase = np.nanmedian([b for a, b in [mode2(el282, pl, R_r24_poly(fits[st_ring], kappa=kappa))
                                                 for _, pl, _, _ in keep]])
            row["dz_k%.2f" % kappa] = float(np.nanmedian(z_) - zbase)
            row["f_k%.2f" % kappa] = float(np.nanmedian(f_))
            row["unst_k%.2f" % kappa] = float(np.mean([unstable2(el282, pl, r24n) for _, pl, _, _ in keep]))
        opt.append(row)
        pr("  %-30s | %8.4f | %8.3f %+8.1f | %9.3f %+8.1f | %+8.4f / %+.4f" %
           (name, row["gate73"], row["rr73"][0] * abs(base_stut), row["rr73"][1] + np.degrees(np.angle(base_stut)),
            row["rr203"][0] * abs(base_ring), row["rr203"][1] + np.degrees(np.angle(base_ring)),
            row.get("dz_k1.00", np.nan), row.get("dz_k0.45", np.nan)))
    pr("  (dzeta columns: kappa 1.00 / kappa 0.45.  NEGATIVE dzeta = LESS damped = WORSE grinding.)")
    pr("")

    json.dump(dict(table=tab, options=opt,
                   fits={k: dict(num=list(v["num"]), den=list(v["den"]), rms_ln_mag=v["rms_ln_mag"],
                                 rms_phase_deg=v["rms_phase_deg"]) for k, v in fits.items()},
                   dzeta={str(k): v for k, v in dz.items()},
                   n_plants={str(k): len(v) for k, v in res.items()},
                   gate73_today=gate73_gen(1.0, 1.0), kappa_wire=KAPPA_WIRE, gain_flown=GAIN_FLOWN),
              open(os.path.join(SCR, "r24_lane_transfer.json"), "w"), indent=1)
    open(os.path.join(SCR, "r24_lane_transfer.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("wrote _scratch/r24_lane_transfer.{txt,json}")


if __name__ == "__main__":
    os.makedirs(SCR, exist_ok=True)
    main()
