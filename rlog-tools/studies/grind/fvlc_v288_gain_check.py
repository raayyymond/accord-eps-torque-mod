# -*- coding: utf-8 -*-
"""fvlc_v288_gain_check.py -- INDEPENDENT re-derivation of V288's ACTUAL gain at the ring frequency.
Subagent cyclekind, 2026-09-10.  ANALYSIS ONLY.

Why: the FORCED-VS-LIMIT-CYCLE report's PART 7 assumed |F(20 Hz)| = 0.457 (the LTI pole).  The cave is
NOT LTI -- it carries an anti-stick branch that makes it a 1-count/tick follower for |d| < 2^K -- so the
gain at the ring depends on the ring's own amplitude.  This re-derives the amplitude-dependent gain from
the cave's integer arithmetic, mirrored EXACTLY, rather than taking either number on trust.

The cave body, from build_v288_tva.py filter_cave() (V850 `sar` is ARITHMETIC, floors toward -inf):
    d    = sp - y                 # 32-bit signed
    step = d >> K                 # K = 4 flown
    if step == 0 and d != 0:      # ANTI-STICK: reached only for 0 < d < 2^K, since sar never
        step = 1                  # rounds a NEGATIVE d to 0
    y    = y + step               # published to the 16-bit cell gp-0x6a32
Sample rate: the hook is on the 1 kHz control task (V288's own docstring: tau = 15.5 ms at 16 ticks
=> Ts ~ 0.97 ms).  Every number below scales with that assumption and it is flagged, not hidden.
"""
import numpy as np

FS = 1000.0
K = 4


def cave(sp, k=K):
    y = 0
    out = np.empty(len(sp), np.int64)
    for i, s in enumerate(sp):
        d = int(s) - y
        step = d >> k                  # python >> on ints floors toward -inf, same as V850 sar
        if step == 0 and d != 0:
            step = 1
        y += step
        out[i] = y
    return out


def lti(sp, k=K):
    a = 1.0 - 2.0 ** -k
    y = np.empty(len(sp))
    v = 0.0
    for i, s in enumerate(sp):
        v = a * v + (1 - a) * s
        y[i] = v
    return y


def gain_at(x, y, f0, fs=FS):
    n = len(x)
    t = np.arange(n) / fs
    c = np.exp(-2j * np.pi * f0 * t)
    keep = slice(n // 4, None)                     # drop the start-up transient
    X = np.vdot(c[keep].conj(), x[keep])
    Y = np.vdot(c[keep].conj(), y[keep])
    return abs(Y) / abs(X), np.angle(Y / X, deg=True)


def main():
    f0 = 20.3
    n = int(6.0 * FS)
    t = np.arange(n) / FS
    print("V288 cave (K=%d), fundamental gain at %.1f Hz vs SETPOINT AMPLITUDE" % (K, f0))
    print("LTI reference (the number PART 7 assumed): |H| = %.4f\n"
          % (abs(1 / (1 + 1j * f0 / (FS * 2 ** -K / (2 * np.pi))))))
    a = 1.0 - 2.0 ** -K
    w = 2 * np.pi * f0 / FS
    z = np.exp(1j * w)
    Hlti = (1 - a) / (1 - a / z)
    print("  exact discrete 1-pole |H(e^jw)| = %.4f   (corner %.2f Hz)"
          % (abs(Hlti), FS * (1 - a) / (2 * np.pi)))
    print()
    print("  %8s | %10s %10s | %10s %10s | %s"
          % ("A (sp)", "|H| cave", "phase", "|H| LTI", "phase", "regime"))
    for A in (2, 4, 6, 8, 12, 16, 24, 40, 80, 200, 600):
        sp = np.round(A * np.sin(2 * np.pi * f0 * t)).astype(np.int64)
        yc = cave(sp).astype(float)
        yl = lti(sp.astype(float))
        gc, pc = gain_at(sp.astype(float), yc, f0)
        gl, pl = gain_at(sp.astype(float), yl, f0)
        rail = A * 2 * np.pi * f0 / FS              # peak per-tick slope of the input, in counts/tick
        reg = "anti-stick follower (peak |d/dt| %.2f <= 1 ct/tick)" % rail if rail <= 1.0 \
            else "mixed" if rail <= 3.0 else "IIR proper"
        print("  %8d | %10.3f %9.1f deg | %10.3f %9.1f deg | %s" % (A, gc, pc, gl, pl, reg))
    print()
    print("TWO-TONE: a LARGE low-frequency steering command carrying a SMALL 20.3 Hz ripple.")
    print("This is the realistic case -- the LF slew keeps |d| large, so the >>K path stays active and the")
    print("ripple sees the LTI gain.  The single-tone table above is the OPPOSITE extreme (sp quasi-static).")
    print("  %8s %8s | %10s %10s" % ("A_lf", "A_ring", "|H| ring", "|H| LTI"))
    for Alf in (0, 20, 60, 200, 600):
        for Ar in (4, 8):
            lf = Alf * np.sin(2 * np.pi * 0.7 * t)
            sp = np.round(lf + Ar * np.sin(2 * np.pi * f0 * t)).astype(np.int64)
            yc = cave(sp).astype(float)
            gc, _ = gain_at(sp.astype(float), yc, f0)
            yl = lti(sp.astype(float))
            gl, _ = gain_at(sp.astype(float), yl, f0)
            print("  %8d %8d | %10.3f %10.3f" % (Alf, Ar, gc, gl))
    print()
    print("NOTE the 0.7 Hz carrier's own peak slope is A_lf*2*pi*0.7/1000 counts/tick, i.e. 1 count/tick")
    print("at A_lf = 227.  Below that the carrier alone does not hold the >>K path open either.")


if __name__ == "__main__":
    main()
