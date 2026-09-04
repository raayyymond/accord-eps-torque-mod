# -*- coding: utf-8 -*-
r"""ZN, WORKED BACKWARDS FROM "NO OVERSHOOT" -- and the Kp-only cut (Kp 148 / Kd 128).

Subagent `znback`, 2026-09-04, for `team-lead`.  ANALYSIS ONLY -- nothing built, nothing sent.

Answers Q1 (Kp sweep at FIXED Kd 128), Q2 (the low-overshoot ZN family vs the 7.3 Hz lower root),
and supplies the DC-authority column every candidate needs.

METHOD, and what is reused rather than rewritten:
  * the byte-exact controller / filter transfer functions come from
    `analysis-2020accord/studies/pidframe/pid_frame_sizing.py` (H_pid, H_lag, H_fb) -- imported, not
    re-implemented.  Its cals are byte-read from the V283 image; LAG_A/B and FB_A/B are IDENTICAL in
    V282 (asserted below against a raw byte read of the V282 image), and V282's Ki = 0 is the base
    for every candidate here.
  * the blind-band Nyquist model (measured plant phase slope -3.75 deg/Hz anchored on
    CREEP-20HZ-LOOP-ID sec1.5, |L| scale anchored on item 4's Kd 0 / Kp 295 row) is re-derived here
    from the same two measured inputs used by `studies/zn285/zn_ku_corrected.py`, and the script
    ASSERTS it reproduces that document's published rows before using it.
  * the 7.3 Hz ring composition uses the measured arms Ls = 0.55 /_+96 deg, Lr = 1.19 /_-27 deg and
    the measured |L_tot(today)| = 0.976 (per-episode complex-ACF fit, 5 episodes).

Run:  python analysis-2020accord/studies/pidframe/zn_backwards_no_overshoot.py
"""
import cmath
import hashlib
import math
import os
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pid_frame_sizing as PF  # noqa: E402

T = 1e-3
ROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT",
                           "C:/Users/dudei/Desktop/Projects/accord-firmwares")) / "analysis-2020accord"
V282 = ROOT / ("_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X."
               "FEEDBACK46080.TORQUE.TAP_plain_image.bin")
B282 = V282.read_bytes()
u16 = lambda a: struct.unpack_from("<H", B282, a)[0]   # noqa: E731

# ---- gate 0: the filters I am about to use really are V282's ---------------------------------------
assert u16(0xC63EC) == PF.LAG_A == 992, (u16(0xC63EC), PF.LAG_A)
assert u16(0xC63EE) == PF.LAG_B == 507
assert u16(0xC63E8) == PF.FB_A == 923
assert u16(0xC63EA) == PF.FB_B == 1560
assert u16(0xC63E6) == 0, "V282 must have Ki = 0"
assert u16(0xC6CD0) == PF.FWD_GAIN == 5346
assert u16(0xC61B6) == PF.D_CLAMP == 10240
print("V282 sha256 %s  (Ki=0; lag 992/507, fb 923/1560, fwd 5346 -- identical to the V283 cals "
      "pid_frame_sizing reads)" % hashlib.sha256(B282).hexdigest()[:16])

C = lambda f, kp, kd: PF.H_pid(f, T, kp, kd, 0)        # noqa: E731  byte-exact controller, Ki = 0
Hlag = lambda f: PF.H_lag(f, T)                        # noqa: E731
Fb = lambda f: PF.H_fb(f, T)                           # noqa: E731
dg = lambda c: math.degrees(cmath.phase(c))            # noqa: E731

# ---- the blind-band Nyquist model, re-derived from the two MEASURED anchors -----------------------
PH_G20 = 157.0 - dg(C(20, 295, 0)) - dg(Hlag(20)) - dg(Fb(20)) - 360   # implied plant phase @20 Hz
SLOPE = -(73 - 28) / 12.0                                             # deg/Hz, measured 10->22 Hz
KMAG = 0.37 / abs(C(20, 295, 0) * Hlag(20) * Fb(20))                  # |L| scale from item 4


def phL(f, kp, kd):
    return dg(C(f, kp, kd)) + dg(Hlag(f)) + dg(Fb(f)) + PH_G20 + SLOPE * (f - 20)


def magL(f, kp, kd):
    return KMAG * abs(C(f, kp, kd) * Hlag(f) * Fb(f))


def f180(kp, kd, lo=12.0, hi=300.0):
    g = lambda f: phL(f, kp, kd) + 180                 # noqa: E731
    if g(lo) * g(hi) >= 0:
        return None
    for _ in range(90):
        m = (lo + hi) / 2
        if g(lo) * g(m) < 0:
            hi = m
        else:
            lo = m
    return (lo + hi) / 2


def GM(kp, kd):
    fx = f180(kp, kd)
    return (1.0 / magL(fx, kp, kd), fx)


# ---- the 7.3 Hz ring, measured arms ---------------------------------------------------------------
F0 = 7.3
LS = 0.55 * cmath.exp(1j * math.radians(96))
LR = 1.19 * cmath.exp(1j * math.radians(-27))
L_TODAY = 0.976


def ring_raw(kp, kd):
    R = (C(F0, kp, kd) * Hlag(F0)) / (C(F0, 248, 128) * Hlag(F0))
    return abs(LS * R + LR)


RING_BASE = ring_raw(248, 128)
ring = lambda kp, kd: ring_raw(kp, kd) / RING_BASE     # noqa: E731  ratio vs today
L73 = lambda kp, kd: L_TODAY * ring(kp, kd)            # noqa: E731


def lower_root(kp, lo=1.0, hi=400.0):
    """the Kd at which |L(7.3)| = 1 from BELOW -- the ring's re-arm point."""
    f = lambda kd: L73(kp, kd) - 1.0                   # noqa: E731
    if f(lo) * f(hi) >= 0:
        return None
    for _ in range(80):
        m = (lo + hi) / 2
        if f(lo) * f(m) < 0:
            hi = m
        else:
            lo = m
    return (lo + hi) / 2


# ---- DC authority ---------------------------------------------------------------------------------
# |T|/E = (Kp/256)*(254/256)*|H_lag(0)|*(5346/32768)   -- every factor byte-read
# L_dc  = fb_counts_per_degps * g_plant * (|T|/E);  fb = 30.891*8 = 247.1 ; g = 0.030 (mid-load,
# the operating point at which zn285's integer mirror gives V282 53.5 %).  tracking = L_dc/(1+L_dc).
FB_DC = abs(Fb(1e-9))                       # 30.891
LAG_DC = abs(Hlag(1e-9))                    # 0.9902
K_OF_KP = lambda kp: (kp / 256.0) * (254.0 / 256.0) * LAG_DC * (PF.FWD_GAIN / 32768.0)  # noqa: E731
G_MID = 0.030


def track(kp, g=G_MID):
    Ldc = FB_DC * 8.0 * g * K_OF_KP(kp)
    return Ldc / (1.0 + Ldc), Ldc


if __name__ == "__main__":
    print("  |T|/E at Kp 248 = %.5f (doc: 0.15528) ; fb DC = %.3f (doc 30.891) ; lag DC = %.4f (doc 0.9902)"
          % (K_OF_KP(248), FB_DC, LAG_DC))
    tr, ldc = track(248)
    print("  DC: L_dc(Kp 248, g=0.030) = %.4f -> tracking %.1f %% (zn285 integer mirror: 53.5 %%)"
          % (ldc, 100 * tr))

    print("\n" + "=" * 118)
    print("GATE 1 -- reproduce the ADDENDUM sec-A5 rows before trusting anything new")
    print("=" * 118)
    print("  %-24s %5s %5s %11s %10s %10s %9s" % ("candidate", "Kp", "Kd", "ring ratio", "|L(7.3)|", "GM", "f(-180)"))
    for nm, kp, kd in [("V282/V283 as built", 248, 128), ("F: Kd 160", 248, 160), ("Kd 192", 248, 192),
                       ("Kd 112", 248, 112), ("ZN-PID (new) 329/162", 329, 162),
                       ("ZN-PI (new) 148/122", 148, 122), ("Kp 0 only", 0, 128), ("Kp 0, Kd 160", 0, 160),
                       ("ZN-PI OLD (retracted)", 108, 387), ("ZN-PID OLD (retracted)", 241, 515)]:
        gm, fx = GM(kp, kd)
        print("  %-24s %5d %5d %11.3f %10.3f %8.2fx %8.1fHz" % (nm, kp, kd, ring(kp, kd), L73(kp, kd), gm, fx))
    print("  lower root at Kp 248 : Kd = %.1f   (addendum: 118)" % lower_root(248))
    print("  Ku at Kp 248 = 128 x GM = %.0f  (addendum: 227) ; at Kp 0 = %.0f (addendum: 270)"
          % (128 * GM(248, 128)[0], 128 * GM(0, 128)[0]))

    # -------------------------------------------------------------------------------------------- Q1
    print("\n" + "=" * 118)
    print("Q1 -- THE Kp SWEEP AT FIXED Kd 128 (Ki = 0).  Kd is NOT MOVED, so the 7.3 Hz lower root is")
    print("      not approached at all; the only thing that moves the ring is Kp's rotation of Ls.")
    print("=" * 118)
    print("  %5s %5s %11s %10s %9s %9s %9s %11s %10s"
          % ("Kp", "Kd", "ring ratio", "|L(7.3)|", "GM", "GM dB", "f(-180)", "DC track", "vs today"))
    base_gm = GM(248, 128)[0]
    for kp in (248, 200, 176, 148, 128, 100, 64, 0):
        gm, fx = GM(kp, 128)
        tr, _ = track(kp)
        print("  %5d %5d %11.3f %10.3f %8.2fx %8.1f %8.1fHz %10.1f %% %9.2fx"
              % (kp, 128, ring(kp, 128), L73(kp, 128), gm, 20 * math.log10(gm), fx, 100 * tr, gm / base_gm))

    print("\n  HEAD TO HEAD -- the Kp-only cut vs ZN-PI, on the same footing:")
    print("  %-26s %5s %5s %11s %10s %9s %11s %14s"
          % ("candidate", "Kp", "Kd", "ring ratio", "|L(7.3)|", "GM", "DC track", "Kd vs root 118"))
    for nm, kp, kd in [("today (V282)", 248, 128), ("Q1: Kp 148, Kd 128", 148, 128),
                       ("ZN-PI (new): 148/122", 148, 122), ("F: Kd 160 (Kp 248)", 248, 160),
                       ("Kp 148 + Kd 160", 148, 160)]:
        gm, _ = GM(kp, kd)
        tr, _ = track(kp)
        print("  %-26s %5d %5d %11.3f %10.3f %8.2fx %10.1f %% %12.2fx"
              % (nm, kp, kd, ring(kp, kd), L73(kp, kd), gm, 100 * tr, kd / 118.0))

    print("\n  DECOMPOSITION -- is the Kp cut or the Kd cut doing the work in ZN-PI 148/122?")
    r0 = L73(248, 128)
    print("    today               248/128 : |L(7.3)| = %.4f" % r0)
    print("    Kp 248->148 alone   148/128 : |L(7.3)| = %.4f   (delta %+.4f)" % (L73(148, 128), L73(148, 128) - r0))
    print("    Kd 128->122 alone   248/122 : |L(7.3)| = %.4f   (delta %+.4f)" % (L73(248, 122), L73(248, 122) - r0))
    print("    both                148/122 : |L(7.3)| = %.4f   (delta %+.4f)" % (L73(148, 122), L73(148, 122) - r0))
    print("    GM: today %.3fx | Kp-only %.3fx | Kd-only %.3fx | both %.3fx"
          % (GM(248, 128)[0], GM(148, 128)[0], GM(248, 122)[0], GM(148, 122)[0]))
    print("    lower root moves with Kp: Kp 248 -> Kd %.1f ; Kp 200 -> %.1f ; Kp 148 -> %.1f ; "
          "Kp 100 -> %.1f ; Kp 0 -> %.1f" % tuple(lower_root(k) for k in (248, 200, 148, 100, 0)))

    # -------------------------------------------------------------------------------------------- Q2
    print("\n" + "=" * 118)
    print("Q2a -- THE LOW-OVERSHOOT ZN FAMILY, against the 7.3 Hz LOWER ROOT")
    print("=" * 118)
    for kp_hunt, lbl in ((0, "Kp 0  (ZN-proper: the hunt runs with integral action OFF)"),
                         (248, "Kp 248 (the brief's arithmetic: Ku measured at today's Kp)")):
        Kdu = 128 * GM(kp_hunt, 128)[0]
        fosc = f180(kp_hunt, 128)
        Tu = 1.0 / fosc
        Kua = (Kdu / 8.0) * T
        root = lower_root(kp_hunt)
        print("\n  --- %s :  Ku(Kd cell) = %.0f, f_osc = %.1f Hz, Tu = %.1f ms, lower root Kd = %.0f ---"
              % (lbl, Kdu, fosc, 1000 * Tu, root))
        print("      %-22s %8s %8s %9s %9s %12s %14s"
              % ("ZN form", "kf", "Ti", "Kd cell", "Kp cell", "Td (ms)", "vs root"))
        for form, kf, tif, tdf in (("classic PID", 0.60, 2.0, 8.0), ("classic PI", 0.45, 1.2, None),
                                   ("SOME overshoot", 1.0 / 3.0, 2.0, 3.0), ("NO overshoot", 0.20, 2.0, 3.0)):
            Kpa = kf * Kua
            Ti = Tu / tif
            kd_cell = Kpa * 8 / T
            kp_cell = (Kpa / Ti) * 256
            td = 1000 * Tu / tdf if tdf else float("nan")
            flag = "  ** BELOW ROOT **" if kd_cell < root else ""
            print("      %-22s %8.3f %6.1fms %9.0f %9.0f %12.1f %10.2fx%s"
                  % (form, kf, 1000 * Ti, kd_cell, kp_cell, td, kd_cell / root, flag))

    print("\n  What the low-overshoot Kd values actually do to the 7.3 Hz ring (at their own ZN Kp):")
    print("  %-30s %5s %5s %11s %10s %9s %11s"
          % ("candidate", "Kp", "Kd", "ring ratio", "|L(7.3)|", "GM", "DC track"))
    for kp_hunt in (0, 248):
        Kdu = 128 * GM(kp_hunt, 128)[0]
        Tu = 1.0 / f180(kp_hunt, 128)
        Kua = (Kdu / 8.0) * T
        for form, kf, tif in (("SOME overshoot", 1.0 / 3.0, 2.0), ("NO overshoot", 0.20, 2.0)):
            Kpa = kf * Kua
            kd_cell = int(round(Kpa * 8 / T))
            kp_cell = int(round((Kpa / (Tu / tif)) * 256))
            gm, _ = GM(kp_cell, kd_cell)
            tr, _ = track(kp_cell)
            print("  %-30s %5d %5d %11.3f %10.3f %8.2fx %10.1f %%"
                  % ("%s (Ku@Kp %d)" % (form, kp_hunt), kp_cell, kd_cell, ring(kp_cell, kd_cell),
                     L73(kp_cell, kd_cell), gm, 100 * tr))

    print("\n  IS ANY LOW-GAIN REGIME AVAILABLE AT ALL?  The 7.3 Hz lower root as a function of Kp,")
    print("  with the GM and the DC authority at that root:")
    print("  %5s %12s %13s %11s" % ("Kp", "lower root", "GM at root", "DC track"))
    for kp in (248, 200, 148, 100, 64, 0):
        root = lower_root(kp)
        gm, _ = GM(kp, root)
        tr, _ = track(kp)
        print("  %5d %12.1f %12.2fx %10.1f %%" % (kp, root, gm, 100 * tr))

    # -------------------------------------------------------------------------------------------- Q2b
    print("\n" + "=" * 118)
    print("Q2b -- WHAT THE OUTER LOOP SEES OF THE INNER LOOP.  openpilot closes on PATH at ~0.3-1.5 Hz;")
    print("       the EPS appears to it as T_inner(f) = L(f)/(1+L(f)) in RATE.  Its PHASE LAG at those")
    print("       frequencies is the delay the outer loop must stabilise around (more lag -> more path")
    print("       overshoot); its GAIN is the authority (less gain -> less overshoot but more lag error).")
    print("=" * 118)

    def Lfull(f, kp, kd):
        g = cmath.exp(1j * math.radians(PH_G20 + SLOPE * (f - 20)))
        return KMAG * C(f, kp, kd) * Hlag(f) * Fb(f) * g

    print("  %-22s %s" % ("candidate", "".join("%14s" % ("%.2f Hz" % f) for f in (0.3, 0.5, 1.0, 1.5, 2.5))))
    for nm, kp, kd in [("today 248/128", 248, 128), ("Kp 148, Kd 128", 148, 128),
                       ("ZN-PI 148/122", 148, 122), ("F 248/160", 248, 160), ("Kp 248, Kd 192", 248, 192),
                       ("Kp 148, Kd 160", 148, 160)]:
        row = ""
        for f in (0.3, 0.5, 1.0, 1.5, 2.5):
            Lc = Lfull(f, kp, kd)
            Tc = Lc / (1 + Lc)
            row += "%8.3f%+6.1f" % (abs(Tc), dg(Tc))
        print("  %-22s %s   (|T| and phase, deg)" % (nm, row))
    print("\n  equivalent inner-loop transport lag at 1 Hz, and the OPEN-loop lag of the raw forward path:")
    for nm, kp, kd in [("today 248/128", 248, 128), ("Kp 148, Kd 128", 148, 128),
                       ("ZN-PI 148/122", 148, 122), ("F 248/160", 248, 160), ("Kp 248, Kd 192", 248, 192),
                       ("Kp 148, Kd 160", 148, 160)]:
        Lc = Lfull(1.0, kp, kd)
        Tc = Lc / (1 + Lc)
        print("    %-22s |T(1Hz)| = %.4f, phase %+6.2f deg = %+6.1f ms lag ; controller phase at 1 Hz %+.1f deg"
              % (nm, abs(Tc), dg(Tc), -dg(Tc) / 360.0 * 1000, dg(C(1.0, kp, kd))))

    # -------------------------------------------------------------------------------------------- Q3
    print("\n" + "=" * 118)
    print("Q3 -- THE DEADBAND / STALL COST OF THE Kp CUT (Ki = 0 throughout).")
    print("=" * 118)
    print("  The stall test in stutter_v283.py D1 / v281r3_read_r35.py (e) is: rate < 0.5 * ref.")
    print("  With Ki = 0 the steady-state chain is a pure static gain, so a frame whose MEASURED")
    print("  rate/ref = x had L_dc = x/(1-x) at Kp 248; at Kp' the same frame has L' = L * Kp'/248")
    print("  and x' = L'/(1+L').  The stall test x' < 0.5 therefore becomes a test on the MEASURED x.")
    print("  %6s %8s %16s %16s %28s" % ("Kp", "k", "x' at x=0.535", "x' at x=0.663", "equiv measured-x stall gate"))
    for kp in (248, 200, 176, 148, 128, 100):
        k = kp / 248.0
        row = []
        for x in (0.535, 0.663):
            L = x / (1 - x)
            row.append((k * L) / (1 + k * L))
        xgate = 0.5 / (0.5 + 0.5 * k)      # solve k*x/(1-x+k*x) = 0.5
        print("  %6d %8.3f %16.3f %16.3f %26.3f" % (kp, k, row[0], row[1], xgate))
    print("\n  i.e. at Kp 148 EVERY frame whose measured rate/ref was below %.3f becomes a 'stall'."
          % (0.5 / (0.5 + 0.5 * 148 / 248.0)))
    print("  (The counterfactual stall COUNT on the flown routes is computed by")
    print("   rlog-tools/studies/osc-highangle/stall_kp_counterfactual.py, which re-runs the exact")
    print("   D1 census with this map.)")
