# -*- coding: utf-8 -*-
r"""hold_record_check.py -- THE 100 Hz FEEDBACK HOLD vs THE KIT'S 20 Hz GRIND/RING RECORD.  2026-09-30, subagent (hold-record).
ANALYSIS ONLY: sends nothing, flashes nothing, builds nothing.

Premise (EVIDENCE, re-verified by this script's caller in Ghidra + bytes, see the report):
  * the LKAS lane FUN_00028ea6 is called at 0x22522 inside the slot-0 task body 0x2214A (activated every dispatcher pass);
  * its feedback operand gp-0x6a56 (read at 0x28F4C) has ONE producer, FUN_0003f776, called at 0x22de2 inside the slot-4 body
    0x22CA0, which the dispatcher FUN_00014be4 activates only when (counter % 10) == 4 (0x14C28 mov 0xa,r7; divq; cmp 0x4,r10);
  * FUN_0003f776 is a pure scale of the 1 kHz rate gp-0x6abe: x = pol*((raw*48*cal[0xC613A]=1159)>>15), sat +-12000.  No filter.
  => the lane sees x[n] = x_true[k(n)], age a = n - k(n) in 1..10 ticks (slot 0 runs before slot 4 in the activation tick).
     If the slot-4 write ever lands before the same tick's slot-0 read, ages are 0..9.  Both cases are computed.

Sections
  1. the hold kernel, exact (closed form) + a time-domain least-squares check (second method)
  2. V282's two-sample-sum feedback filter (integer-exact, cals read LE from the V282 image) on a held vs a fresh input
  3. the record items re-read: creep20's "3.9 ms inter-stream offset", the MODE-NATURE back-out vs the tap, the 16.63 Hz pole,
     the V295-family models (fresh x, tau 2 ms), the fold partners
  4. the ANGLE loop's phase budget at 2-4 Hz crossover, and a D term on the held rate
"""
from __future__ import annotations

import hashlib
import struct
import numpy as np

FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
V282 = FW + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
V282_SHA = "0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe"
TP = 0xBF000
DT = 1e-3
N_HOLD = 10
FREQS = [2, 3, 4, 7, 13, 15, 16.63, 17, 19.96, 20, 22, 24, 26]


def P(*a):
    print(*a)


# ================================================================================================================
# 1. THE HOLD KERNEL
# ================================================================================================================
def hold_fund(f, ages=range(1, 11)):
    """fundamental (same-frequency) gain of a 10-tick sample-and-hold read at 1 kHz with the given age set, phase-averaged
    over the sampling phase: H = mean_a exp(-j w a dt).  Exact for the component of the staircase at f."""
    w = 2 * np.pi * np.asarray(f, float)
    return np.mean([np.exp(-1j * w * a * DT) for a in ages], axis=0)


def hold_image(f, m, ages=range(1, 11)):
    """the staircase's component at f + m*100 Hz per unit input at f (m != 0): same kernel, evaluated at the image."""
    return hold_fund(np.asarray(f, float) + 100.0 * m, ages)


def ls_fundamental(y, f, n0=2000):
    t = np.arange(len(y)) * DT
    A = np.c_[np.cos(2 * np.pi * f * t), np.sin(2 * np.pi * f * t)][n0:]
    c, s = np.linalg.lstsq(A, y[n0:], rcond=None)[0]
    return complex(c, -s)            # y ~ Re{ G e^{jwt} } with G = c - j s


def simulate_hold(f, n=40000, phase_tick=4, first_age1=True):
    """time-domain: x_true(n) = cos(w n dt); slot 4 samples at ticks with (n % 10) == phase_tick AFTER slot 0 ran
    (first_age1=True -> the PID on the activation tick still reads the previous sample)."""
    nn = np.arange(n)
    xt = np.cos(2 * np.pi * f * nn * DT)
    held = np.empty(n)
    cur = 0.0
    for i in range(n):
        if first_age1:
            held[i] = cur
            if i % N_HOLD == phase_tick:
                cur = xt[i]
        else:
            if i % N_HOLD == phase_tick:
                cur = xt[i]
            held[i] = cur
    return xt, held


def section1():
    P("=" * 118)
    P("1. THE 10-TICK HOLD AT 1 kHz: fundamental gain/phase (ages 1..10 = the traced order; ages 0..9 = the alternative)")
    P("   vs the delays the record modelled (2 ms, 3 ms pure; creep20/L_fw's one tick; the 3.9 ms 'stream offset')")
    P("=" * 118)
    P("   f Hz | |H| a1-10  ang a1-10  ms   | |H| a0-9  ang a0-9 | 1 ms  2 ms  3 ms  3.9 ms | excess over 2 ms / 3 ms (a1-10) | TD check |H| ang")
    for f in FREQS:
        h1, h0 = hold_fund(f), hold_fund(f, range(0, 10))
        d = lambda ms: -360 * f * ms * 1e-3
        xt, held = simulate_hold(f)
        g = ls_fundamental(held, f) / ls_fundamental(xt, f)
        P("  %5.2f | %.4f  %+7.2f  %4.2f | %.4f  %+7.2f | %+5.1f %+5.1f %+5.1f %+6.1f | %+6.1f / %+6.1f | %.4f %+7.2f" % (
            f, abs(h1), np.degrees(np.angle(h1)), -np.angle(h1) / (2 * np.pi * f) * 1e3, abs(h0), np.degrees(np.angle(h0)),
            d(1), d(2), d(3), d(3.9), np.degrees(np.angle(h1)) - d(2), np.degrees(np.angle(h1)) - d(3), abs(g), np.degrees(np.angle(g))))
    P("\n   images: the held staircase also carries the input at f+-100k Hz (the loop's fold partners).  Per unit input at f:")
    P("   f Hz | |img @ 100-f| |img @ 100+f| |img @ 200-f| | and the reverse fold: a plant line at 100-f / 100+f is read by the lane AS f")
    for f in (7, 16.63, 20, 26):
        P("  %5.2f |   %.3f         %.3f         %.3f      |   100-f = %.2f Hz, 100+f = %.2f Hz" % (
            f, abs(hold_image(-f, 1)), abs(hold_image(f, 1)), abs(hold_image(-f, 2)), 100 - f, 100 + f))


# ================================================================================================================
# 2. V282'S FEEDBACK FILTER ON A HELD INPUT (integer exact, 0x28F86..0x28FA8, op = add (sum) on V282)
# ================================================================================================================
def read_v282():
    b = open(V282, "rb").read()
    assert hashlib.sha256(b).hexdigest() == V282_SHA, "not the V282 image"
    u16 = lambda a: struct.unpack_from("<H", b, a)[0]
    i16 = lambda a: struct.unpack_from("<h", b, a)[0]
    u32 = lambda a: struct.unpack_from("<I", b, a)[0]
    op = {0xD1C9: "sum", 0xD189: "diff"}[u16(0x28FA4)]
    def rec(bank, n):
        p = u32(bank + 4 * 7)
        assert u16(p) == n
        return [u16(p + 2 + 2 * i) for i in range(n)], [u16(p + 2 + 2 * n + 2 * i) for i in range(n)]
    c = dict(a=i16(TP + 0x73E8), b=u16(TP + 0x73EA), C=u16(TP + 0x72E6), op=op, sh=u16(0x29D76) & 0x1F,
             kp=rec(0xCB994, 5)[1][0], kd=rec(0xCB7D4, 4)[1][0], dcl=u16(TP + 0x71B6), la=i16(TP + 0x73EC), lb=u16(TP + 0x73EE),
             gain=i16(TP + 0x7CD0))
    assert (c["a"], c["b"], c["op"], c["kp"], c["kd"], c["la"], c["lb"], c["gain"]) == (923, 1560, "sum", 248, 128, 992, 507, 5346), c
    return c


def fb_integer(x, c):
    """0x28F86 ld.hu b; 0x28F8A ld.h a; mul; sar 0xa x2; add -> s_new; 0x28FA4 add r9,r26 (V282 SUM): r26 = s_old + s_new."""
    s, out = 0, np.empty(len(x), np.int64)
    for i, xi in enumerate(x):
        s_new = ((c["a"] * s) >> 10) + ((int(xi) * c["b"]) >> 10)
        r = s + s_new if c["op"] == "sum" else s_new - s
        out[i] = max(-c["C"], min(c["C"], r))
        s = s_new
    return out


def H_fb(f, c):
    zi = np.exp(-2j * np.pi * np.asarray(f, float) * DT)
    return (c["b"] / 1024) * (1 + zi) / (1 - (c["a"] / 1024) * zi)


def C_lane(f, c, m=254):
    """T counts per x count, sp = 0, clamps off (V282: P + D on E, D = Kd/8 (1 - z^-1) E)."""
    zi = np.exp(-2j * np.pi * np.asarray(f, float) * DT)
    E = -H_fb(f, c)
    PD = (c["kp"] / 256 + c["kd"] / 8 * (1 - zi)) * E
    y = (c["lb"] / 1024) * (1 + zi) / (32 * (1 - (c["la"] / 1024) * zi)) * (m / 256) * PD
    return y * c["gain"] / 32768


def section2(c):
    P("\n" + "=" * 118)
    P("2. V282 FEEDBACK (two-sample SUM, a 923 b 1560, DC %.3f, pole %.2f Hz) ON A HELD INPUT -- integer exact, amplitude 400 counts (50 deg/s)"
      % ((c["b"] / 1024) * 2 / (1 - c["a"] / 1024), -np.log(c["a"] / 1024) / (2 * np.pi * DT)))
    P("=" * 118)
    P("   step response to ONE held update of +400 counts (x changes once, then is held for 10 ticks):")
    x = np.r_[np.zeros(5), np.full(25, 400)].astype(np.int64)
    r = fb_integer(x, c)
    P("   tick: " + " ".join("%5d" % v for v in r[4:20]))
    P("   (the 1+z^-1 'two-sample sum' adds two IDENTICAL input samples on 9 ticks of 10; its zero sits at 500 Hz and does")
    P("    nothing against the 100 Hz staircase; the 16.5 Hz pole moves s only %.0f %% of the way to a new level within one 10-tick hold)"
      % (100 * (1 - (c["a"] / 1024) ** 10)))
    P("\n   f Hz | fresh: |r26/x| ang | held: |r26/x| ang | ratio held/fresh |H| ang | closed form H_fb*H_hold ang | fb image @100-f / fund")
    for f in (7, 16.63, 20, 26):
        xt, held = simulate_hold(f, 40000)
        A = 400
        rf = fb_integer(np.round(A * xt).astype(np.int64), c)
        rh = fb_integer(np.round(A * held).astype(np.int64), c)
        gf = ls_fundamental(rf.astype(float), f) / A
        gh = ls_fundamental(rh.astype(float), f) / A
        gi = ls_fundamental(rh.astype(float), 100 - f) / A
        cf = H_fb(f, c) * hold_fund(f)
        P("  %5.2f | %6.2f %+7.1f | %6.2f %+7.1f | %.3f %+6.1f | %6.2f %+7.1f | %.3f" % (
            f, abs(gf), np.degrees(np.angle(gf)), abs(gh), np.degrees(np.angle(gh)), abs(gh / gf), np.degrees(np.angle(gh / gf)),
            abs(cf), np.degrees(np.angle(cf)), abs(gi) / abs(gh)))
    P("\n   The lane electronics per deg/s of wheel rate (x = 8 counts per deg/s), V282, sp = 0, taper 254, clamps off:")
    P("   f Hz | |C_elec| ang (no hold) | with hold a1-10: |C| ang | MODE-NATURE quoted at 19.96 Hz: |Re| 14.095, ang -75.7")
    for f in (7, 16.63, 19.96):
        e = -8 * C_lane(f, c)          # sign: L = -C*G convention (tap sign); report the opposing-torque electronics
        eh = e * hold_fund(f)
        P("  %5.2f | %6.2f %+7.1f | %6.2f %+7.1f" % (f, abs(e), np.degrees(np.angle(e)), abs(eh), np.degrees(np.angle(eh))))


# ================================================================================================================
# 3. THE RECORD, RE-READ
# ================================================================================================================
def section3():
    P("\n" + "=" * 118)
    P("3. THE RECORD ITEMS")
    P("=" * 118)
    P("3a. creep20 Part 4 (CREEP-20HZ-LOOP-ID-2026-09-03.md 'Timing -- the part earlier readers did not do'): the byte-exact mirror was")
    P("    fed the 0x18F rate UP-SAMPLED with a zero-phase FIR (up1k = resample_poly) -- i.e. WITHOUT the hold.  Measured: T_meas lags T_sim")
    P("    by a constant +23..+33 deg at 20 Hz (= 3.2..4.6 ms), coh 0.98-0.99; 18-22 Hz amp meas/sim r31 70/74, r32 58/60.")
    for ages, lab in ((range(1, 11), "a1-10"), (range(0, 10), "a0-9")):
        h = hold_fund(20, ages)
        P("    hold prediction (%s): lag %+.1f deg = %.2f ms, |H| %.3f    | measured lag 23..33 deg, amp ratio %.3f / %.3f" % (
            lab, -np.degrees(np.angle(h)), -np.angle(h) / (2 * np.pi * 20) * 1e3, abs(h), 70 / 74, 58 / 60))
    P("    a CAN stream-timestamp offset predicts the same lag but |ratio| = 1.000.  Discriminator: the ratio vs f (below).")
    P("    f Hz : |H_hold| a1-10 -> " + "  ".join("%g: %.3f" % (f, abs(hold_fund(f))) for f in (10, 15, 20, 22, 25)))

    P("\n3b. MODE-NATURE-V289-RECENSUS-2026-09-09.md 'THE PLANT, BACKED OUT FROM THE TWO MEASURED LINE FREQUENCIES':")
    P("    plant_backout = -180 - elec_angle, elec WITHOUT the hold.  The tap plant was 'offset-corrected' by multiplying G by")
    P("    exp(-j w 3.9 ms), i.e. the 3.9 ms was charged to the PLANT.  Re-read with the hold charged to the CONTROLLER:")
    rows = [("V282", 19.96, -75.7, -104.3, 20.3, -100.0), ("V289", 16.63, -99.7, -80.3, 16.4, -88.0), ("V282@16.4", 16.63, None, None, 16.4, -87.0)]
    for lab, f0, elec, bo, ftap, tapc in rows:
        tap_raw = tapc + 360 * ftap * 0.0039
        if elec is None:
            P("    %-9s tap(corr) %+6.1f -> tap RAW (no 3.9 ms charged) %+6.1f" % (lab, tapc, tap_raw))
            continue
        for ages, al in ((range(1, 11), "a1-10"), (range(0, 10), "a0-9")):
            hd = np.degrees(np.angle(hold_fund(f0, ages)))
            P("    %-9s f0 %5.2f | record: elec %+6.1f backout %+6.1f vs tap(corr) %+6.1f | with hold %s %+5.1f: physical plant %+6.1f vs tap RAW %+6.1f  diff %+5.1f" % (
                lab, f0, elec, bo, tapc, al, hd, bo - hd, tap_raw, (bo - hd) - tap_raw))
    P("    => the record's L = L_fw x G_tap x exp(-j w 3.9ms) and the true L = L_fw x H_hold x G_tap differ by H_hold / exp(-j w 3.9ms):")
    P("    f Hz | residual phase a1-10 / a0-9 (deg) | residual |.| | crossing shift at the record's L slope (-1.7 elec -7.2 plant = -8.9 deg/Hz)")
    for f in (7, 16.63, 20, 24):
        r1 = hold_fund(f) / np.exp(-2j * np.pi * f * 0.0039)
        r0 = hold_fund(f, range(0, 10)) / np.exp(-2j * np.pi * f * 0.0039)
        P("  %5.2f |  %+5.1f / %+5.1f | %.3f | %+.2f / %+.2f Hz" % (f, np.degrees(np.angle(r1)), np.degrees(np.angle(r0)), abs(r1),
                                                                  np.degrees(np.angle(r1)) / 8.9, np.degrees(np.angle(r0)) / 8.9))
    P("\n3c. the 16.63 Hz pole that took V289's margin: record V282 |L| 1.13 at -150 deg (30 deg PM) with the 3.9 ms inside G.")
    for ages, al in ((range(1, 11), "a1-10"), (range(0, 10), "a0-9")):
        r = hold_fund(16.63, ages) / np.exp(-2j * np.pi * 16.63 * 0.0039)
        P("    true (%s): |L| %.2f at %+.1f deg -> PM %.1f deg; V289 spent -41.6 (notch skirt) +11.5 (fb pole) = -30.1 deg -> PM %+.1f" % (
            al, 1.13 * abs(r), -150 + np.degrees(np.angle(r)), 30 + np.degrees(np.angle(r)), 30 + np.degrees(np.angle(r)) - 30.1))

    P("\n3d. models that fed the lane a FRESH 1 kHz x (V295 harness 'x = plant.sense()' every tick; advlib inner_L; tau 2 ms + 3 ms")
    P("    rate former + ZOH half tick): the hold is MISSING ENTIRELY from these.  Extra phase they omit:")
    P("    f Hz : " + "  ".join("%g: %+.1f deg" % (f, np.degrees(np.angle(hold_fund(f)))) for f in (1, 2, 3, 8, 16.63, 20, 26)))
    P("    their 'tau9' (9 ms) stress row ~ the realistic total: 2 ms + 5.5 ms hold + 1.5 ms former = 9.0 ms.")


# ================================================================================================================
# 4. THE ANGLE LOOP
# ================================================================================================================
def section4(c):
    P("\n" + "=" * 118)
    P("4. ANGLE LOOP: phase budget at a 2-4 Hz crossover, and a D term on the held rate")
    P("=" * 118)
    fir = lambda f: np.exp(-1j * np.pi * f * DT) * np.cos(np.pi * f * DT)        # (1 + z^-1)/2, the 2-tap FIR of the edit set
    P("   f Hz | theta = gp-0x6a00 (held) + 2-tap FIR: deg | theta = gp-0x69ca (fresh 1 kHz) + FIR: deg | hold alone a1-10 / a0-9")
    for f in (1, 2, 3, 4, 5, 8):
        P("  %5.1f |   %+6.2f                                |   %+6.2f                                | %+6.2f / %+6.2f" % (
            f, np.degrees(np.angle(hold_fund(f) * fir(f))), np.degrees(np.angle(fir(f))),
            np.degrees(np.angle(hold_fund(f))), np.degrees(np.angle(hold_fund(f, range(0, 10))))))
    # D on the held rate: damping retained = cos(phase lag of the hold); sign flips where the lag passes 90 deg
    P("\n   D = -Kd*x_rate on the HELD gp-0x6a56: fraction of the D torque that is DAMPING (Re) at a mode of frequency f:")
    for f in (2, 7, 16.63, 20, 26, 35, 45, 50):
        h = hold_fund(f)
        h0 = hold_fund(f, range(0, 10))
        P("   %5.2f Hz : |H| %.3f  lag %5.1f deg  damping share cos %+.3f (a0-9 %+.3f)%s" % (
            f, abs(h), -np.degrees(np.angle(h)), np.cos(np.angle(h)), np.cos(np.angle(h0)),
            "   <-- ANTI-damping" if np.cos(np.angle(h)) < 0 else ""))
    fz = 0.25 / 5.5e-3
    P("   the lag reaches 90 deg (D stops damping) at %.1f Hz (a1-10, 5.5 ms) / %.1f Hz (a0-9, 4.5 ms); Nyquist of the hold = 50 Hz:" % (fz, 0.25 / 4.5e-3))
    P("   a plant line at 100-f is read as f, so a held-rate D feeds 50-100 Hz content back folded and with the wrong phase.")
    # 100 Hz staircase ripple of the angle-loop P through the output lag
    zi = np.exp(-2j * np.pi * 100 * DT)
    Hlag100 = abs((c["lb"] / 1024) * (1 + zi) / (32 * (1 - (c["la"] / 1024) * zi)))
    Hlag0 = (c["lb"] / 1024) * 2 / (32 * (1 - c["la"] / 1024))
    P("\n   100 Hz ripple of a P angle loop on the held angle: wheel rate w deg/s -> held-angle sawtooth p-p = w*10 ms; fundamental")
    P("   amplitude (p-p/pi); E = 16 per 0.1 deg; T = E*Kp/256 * lag * 5346/32768.  Output lag |H(100 Hz)| = %.4f (DC %.4f)." % (Hlag100, Hlag0))
    for w in (10, 50, 200):
        for kp in (960, 4096):
            amp_deg = w * 0.010 / np.pi
            T = 16 * amp_deg * 10 * kp / 256 * Hlag100 * 5346 / 32768
            P("     w %3d deg/s, Kp %4d: sawtooth fund %.3f deg -> T ripple at 100 Hz %.2f lane counts (rail 2461)" % (w, kp, amp_deg, T))


if __name__ == "__main__":
    c = read_v282()
    section1()
    section2(c)
    section3()
    section4(c)
