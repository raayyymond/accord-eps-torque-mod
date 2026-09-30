# -*- coding: utf-8 -*-
"""ADV-A a6: the acceleration trim's gain and phase vs frequency, 0.3-30 Hz, by SINUSOID MARCH through my integer
mirror (idx 0, sp = 0, so P = -3.75*r26 and nothing else) vs the CLOSED FORM from the cells:
   r26/x = (b/1024)(1 - z^-1)/(1 - (a/1024) z^-1)          [0x28F86..0x28FA4, the difference operand]
   P/r26 = -Kp/256 (sp = 0) ; S = (m/256) P ; o = (lb/1024) S/(1 - (la/1024) z^-1) ; y = (1 + z^-1) o / 32 ;
   T = y * gain / 32768                                        [0x29E36, 0x2A0BE, 0x2A174..0x2A1AC, 0x2A1FE]
Amplitude chosen per f so |r26| peaks near 500 (unclamped, >> the floor LSB).  Also |P/x| at 20 Hz, K_alpha, and the
amplitude at which the r26 clamp first binds (in deg/s^2 of wheel acceleration)."""
import json, os, sys, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import advA_vec as V  # noqa: E402

J = json.load(open(os.path.join(HERE, "a1_cells.json")))
FS = 1000.0


def closed(c, f, m=254):
    z = np.exp(1j * 2 * np.pi * f / FS)
    a, b = c["fb_a"] / 1024.0, c["fb_b"] / 1024.0
    Hr = b * (1 - 1 / z) / (1 - a / z)
    kp = c["kp_y"][0]
    Hp = -(kp / 256.0) * Hr
    Hs = (m / 256.0) * Hp
    Ho = (c["lag_b"] / 1024.0) / (1 - (c["lag_a"] / 1024.0) / z)
    Hy = (1 + 1 / z) / 32.0 * Ho * Hs
    Ht = Hy * c["gain"] / 32768.0
    return Hr, Hp, Ht


def fit(sig, f, n0):
    t = np.arange(len(sig)) / FS
    X = np.vstack([np.sin(2 * np.pi * f * t), np.cos(2 * np.pi * f * t), np.ones_like(t)]).T
    co = np.linalg.lstsq(X[n0:], sig[n0:], rcond=None)[0]
    return complex(co[0], co[1])      # phasor relative to sin: A*sin + B*cos = Im-part convention below


freqs = [0.3, 0.5, 1.0, 1.5, 2.0, 2.4, 3.0, 4.0, 5.0, 7.0, 10.0, 15.0, 20.0, 25.0, 30.0]
rows = []
for nm in ("v294", "v295"):
    c = J[nm]
    B = len(freqs)
    amps = []
    for f in freqs:
        Hr, _, _ = closed(c, f)
        amps.append(min(12000, int(500 / abs(Hr))))
    VL = V.VecLane(c, B)
    periods = [max(8, int(math.ceil(4 * f))) for f in freqs]
    n = int(max(p / f for p, f in zip(periods, freqs)) * FS) + 6000
    t = np.arange(n) / FS
    X = np.array([np.round(A_ * np.sin(2 * np.pi * f * t)).astype(np.int64) for A_, f in zip(amps, freqs)])
    R26 = np.zeros((B, n)); P = np.zeros((B, n)); T = np.zeros((B, n))
    for k in range(n):
        T[:, k] = VL.tick(X[:, k], np.zeros(B, np.int64), np.zeros(B, np.int64))
        R26[:, k] = VL.last["r26"]; P[:, k] = VL.last["P"]
    for j, f in enumerate(freqs):
        xin = X[j].astype(float)
        n0 = 6000
        px = fit(xin, f, n0)
        out = {}
        for key, sig in (("r26", R26[j]), ("P", P[j]), ("T", T[j])):
            out[key] = fit(sig, f, n0) / px
        Hr, Hp, Ht = closed(c, f)
        # the fitted phasor uses (sin, cos) coefficients; convert closed form to the same convention:
        # x = A sin(wt) -> y = |H| A sin(wt + ph) = |H|A cos(ph) sin + |H|A sin(ph) cos -> phasor (cos ph, sin ph)
        conv = lambda H: complex(abs(H) * math.cos(np.angle(H)), abs(H) * math.sin(np.angle(H)))  # noqa: E731
        rows.append((nm, f, amps[j], out, conv(Hr), conv(Hp), conv(Ht), int(np.abs(R26[j, n0:]).max())))

print("%-5s %5s %6s | %-24s | %-24s | %-26s | %s" % ("img", "f Hz", "A", "|r26/x| march/closed", "|P/x| march/closed",
                                                     "|T/x| march/closed  dphase", "max|r26|"))
worst_mag = worst_ph = 0.0
for nm, f, A_, out, Hr, Hp, Ht, mr in rows:
    em = abs(abs(out["T"]) / abs(Ht) - 1); eph = abs(math.degrees(np.angle(out["T"] / Ht)))
    worst_mag = max(worst_mag, abs(abs(out["P"]) / abs(Hp) - 1)); worst_ph = max(worst_ph, abs(math.degrees(np.angle(out["P"] / Hp))))
    print("%-5s %5.1f %6d | %9.4f / %9.4f | %9.4f / %9.4f | %8.5f / %8.5f %+6.2f deg | %d  ph(T)=%+7.1f deg"
          % (nm, f, A_, abs(out["r26"]), abs(Hr), abs(out["P"]), abs(Hp), abs(out["T"]), abs(Ht),
             math.degrees(np.angle(out["T"] / Ht)), mr, math.degrees(np.angle(out["T"]))))
print("worst |P| magnitude error march vs closed %.4f %% ; worst P phase error %.3f deg" % (100 * worst_mag, worst_ph))

# V295 / V294 ratios from the march
r4 = {f: out for nm, f, A_, out, *_ in rows if nm == "v294"}
r5 = {f: out for nm, f, A_, out, *_ in rows if nm == "v295"}
print("ratio V295/V294 |T/x| by f:", ", ".join("%.1f:%.3f" % (f, abs(r5[f]["T"]) / abs(r4[f]["T"])) for f in freqs))
# physical: T per deg/s of wheel rate (x = 8 counts per deg/s), and K_alpha (T per deg/s^2) at low f
for nm in ("v294", "v295"):
    c = J[nm]
    _, _, Ht = closed(c, 0.3)
    w = 2 * math.pi * 0.3
    print("%s: |T| per deg/s of wheel rate at 2.4 Hz = %.3f, at 20 Hz = %.3f ; K_alpha (0.3 Hz, |T|/(|alpha| deg/s^2)) = %.4f ; closed DC-limit K_alpha = %.4f"
          % (nm, 8 * abs(closed(c, 2.4)[2]), 8 * abs(closed(c, 20.0)[2]), 8 * abs(Ht) / w,
             3.75 * (c["fb_b"] / (1024 - c["fb_a"])) * 0.008 * (254 / 256) * (2 * c["lag_b"] / ((1024 - c["lag_a"]) * 32)) * c["gain"] / 32768))
    print("     |P/x| at 20 Hz closed = %.4f" % abs(closed(c, 20.0)[1]))
    # r26 clamp onset in wheel acceleration (low f): r26 = (b/(1024-a)) * 0.008 * alpha
    print("     r26 clamp (1024) binds at |alpha| >= %.0f deg/s^2 (low-f) ; at 2.4 Hz a %.0f deg/s wheel-rate amplitude"
          % (1024 / ((c["fb_b"] / (1024 - c["fb_a"])) * 0.008), 1024 / abs(closed(c, 2.4)[0]) / 8))
