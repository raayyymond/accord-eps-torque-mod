# -*- coding: utf-8 -*-
"""s3_second_methods.py -- trim-ratio lens: SECOND METHODS for every load-bearing number (the first methods are the
harness's closed forms used in s1_plane).

(a) FF identity: golden-model surface T(idx) at fb = 0 for every candidate vs V294, all 241 idx x taper {254, 179, 77};
    plus a byte-exact Lane march at x = 0 on 3000 random 100 Hz commands, tick for tick, vs V294.
(b) |T/x| in 10-25 Hz: time-domain sinusoids of x through the byte-exact Lane (sp = 0), lock-in amplitude, vs
    the analytic lane_ctf.
(c) K_alpha: a constant-acceleration ramp of x through the Lane (sp = 0): steady T / alpha vs the closed form.
(d) inner closed-loop poles: harness closed_loop_modes vs v294_plant.linear_poles (independent state-space code) for
    V294-structure lanes, on nominal, light_b and the three stress members.
(e) the trim cap / zero-command torque and the restart pulse by direct march.
Analysis only."""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
sys.path.insert(0, HERE)
import v295_harness as H  # noqa: E402
import v294_plant as VP  # noqa: E402
from s1_plane import realise  # noqa: E402

BASE = H.Cells.v294()
C_LIST = [BASE] + [realise(a, G) for a, G in ((1011, 1.5), (1011, 2.0), (1011, 2.5), (1011, 3.0), (1017, 1.0),
                                                (1014, 2.0), (1017, 2.0))]


def ff_identity():
    print("(a) FF identity (golden surface at fb 0, 241 idx x 3 tapers; Lane march at x = 0 on random commands)")
    ref = {m: H.surface(BASE, m=m) for m in (254, 179, 77)}
    rng = np.random.default_rng(5)
    NF = 3000
    wire = np.clip(np.cumsum(rng.integers(-123, 124, NF)), -3900, 3900)
    for c in C_LIST[1:]:
        bad = sum(int(np.sum(H.surface(c, m=m) != ref[m])) for m in ref)
        L = H.Lane([BASE, c])
        T = np.zeros((2, NF * 10), np.int64)
        for n in range(NF * 10):
            if n % 10 == 0:
                idx, sp, m = L.demand(np.full(2, wire[n // 10]))
            t, _ = L.tick(np.zeros(2, np.int64), sp, idx, m)
            T[:, n] = t
        mm = int(np.sum(T[0] != T[1]))
        print("   %-12s surface mismatches %d / 723 ; Lane march x=0: %d / %d ticks differ ; max|T| %d" % (
            c.name, bad, mm, NF * 10, int(np.abs(T[1]).max())))


def hf_gain():
    print("(b) |T/x| by time-domain sinusoid (amplitude 400 counts = 50 deg/s, 2 s) vs analytic lane_ctf")
    fs = (10.0, 13.0, 17.0, 20.0, 25.0)
    for c in C_LIST:
        row = []
        for f in fs:
            n = np.arange(3000)
            x = np.round(400 * np.sin(2 * np.pi * f * n * 1e-3)).astype(np.int64)
            L = H.Lane([c])
            T = np.zeros(len(n))
            for i in n:
                t, _ = L.tick(np.array([x[i]]), np.zeros(1, np.int64), np.zeros(1, np.int64), np.full(1, 254, np.int64))
                T[i] = t[0]
            k = n >= 1000
            ph = 2 * np.pi * f * n[k] * 1e-3
            amp = 2 * abs(np.mean(T[k] * np.exp(-1j * ph)))
            row.append((amp / 400.0, abs(H.lane_ctf(c, np.array([f]))[0])))
        print("   %-12s " % c.name + "  ".join("%4.0fHz td %.4f an %.4f" % (f, a, b) for f, (a, b) in zip(fs, row)))


def k_alpha():
    print("(c) K_alpha by constant-acceleration ramp (alpha = 200 deg/s^2, x = 8*alpha*t) vs closed form")
    for c in C_LIST:
        L = H.Lane([c])
        al = 200.0
        T = []
        for i in range(4000):
            x = int(round(8 * al * (i * 1e-3 - 2.0)))        # passes through 0 at t = 2 s, |x| <= 3200
            t, _ = L.tick(np.array([x]), np.zeros(1, np.int64), np.zeros(1, np.int64), np.full(1, 254, np.int64))
            T.append(int(t[0]))
        Tss = np.mean(T[3000:])
        t0 = H.trim_T_per_omega(c, np.array([0.05]))[0]
        Ka_cf = t0.imag / (2 * np.pi * 0.05)
        # sign: x = +0x18F raw = -8*omega_left; the lane opposes the x-acceleration: T = -Ka * (x_dot/8)... report |T|/alpha
        print("   %-12s ramp |T|/alpha %.4f  closed form %.4f  (ratio %.3f)" % (c.name, abs(Tss) / al, Ka_cf,
                                                                              abs(Tss) / al / Ka_cf))


def poles():
    print("(d) inner closed-loop poles: harness closed_loop_modes vs v294_plant.linear_poles (0.3-40 Hz pairs)")
    fam = H.family()
    for c in (C_LIST[0], C_LIST[2], C_LIST[4], C_LIST[7]):
        for nm in ("nominal", "light_b", "mode13", "mode20", "mode20_lo"):
            for v in (5.0, 12.0, 25.0):
                p = fam[nm].at(v)
                m1, _ = H.closed_loop_modes(p, c)
                m2 = H.linear_modes(p, c)
                a = sorted([(round(f, 2), round(z, 3)) for f, z in m1 if 0.3 < f < 40])
                b = sorted([(round(f, 2), round(z, 3)) for f, z, _ in (m2 or []) if 0.3 < f < 40])
                agree = len(a) == len(b) and all(abs(x[0] - y[0]) < 0.02 and abs(x[1] - y[1]) < 0.003 for x, y in zip(a, b))
                if not agree or nm in ("mode20_lo",) or v == 12.0:
                    print("   %-12s %-10s v %4.1f  harness %s | v294_plant %s  %s" % (c.name, nm, v, a, b,
                                                                                     "AGREE" if agree else "DIFFER"))


def cap_restart():
    print("(e) trim cap (T at zero command, fb held at +-C) and restart pulse, by harness m_safe pieces")
    for c in C_LIST:
        capP = H.surface(c, [0], fb=c.fb_clamp)[0]
        capN = H.surface(c, [0], fb=-c.fb_clamp)[0]
        rp = H.restart_pulse(c)
        im = H.int32_margins(c)
        print("   %-12s cap +%d/%d T ; restart peak %s ; int32 min margin %.2f (%s)" % (
            c.name, capP, capN, {k: v["peak"] for k, v in rp.items()}, *min((v["margin"], k) for k, v in im.items())))


if __name__ == "__main__":
    ff_identity()
    hf_gain()
    k_alpha()
    poles()
    cap_restart()
