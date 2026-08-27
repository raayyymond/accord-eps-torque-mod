#!/usr/bin/env python
"""
V107 fork: (2) can moving the gp-0x6c2c EMA poles rotate the torque phasor into the
90-180 deg sector (damping AND REDUCED inertia)?  (3) exact reshape specs.

Poles are INTEGER cals:  a1 = cal(0xC643C)/128,  a2 = cal(0xC40DC)/64.
Stock 37/128 and 22/64 -> r1 = 0.7109375, r2 = 0.65625.
Both are 37/22 on ALL 102 build images -> VIRGIN.
"""
import cmath
import math

F0 = 21.73          # the mode
FS = 1000.0
Y0_STOCK = -9830
K_OF_Y = 273.0 / 2 ** 24
INT16_MAX = 32767


def H(f, K1, K2, fs=FS):
    a1, a2 = K1 / 128.0, K2 / 64.0
    z1 = cmath.exp(-2j * math.pi * f / fs)
    return 1024 * (a1 / (1 - (1 - a1) * z1)) * (1 - z1) * 32 * (a2 / (1 - (1 - a2) * z1)) / 512


def report(K1, K2, f=F0):
    h = H(f, K1, K2)
    return abs(h), math.degrees(cmath.phase(h))


def main():
    m0, p0 = report(37, 22)
    print("=" * 92)
    print("FORK 2 -- POLE PLACEMENT.  Can the phasor reach the 90-180 deg sector?")
    print("=" * 92)
    print("  differencer alone at %.2f Hz: 90 - 180*f/fs = %+.2f deg" % (F0, 90 - 180 * F0 / FS))
    print("  stock poles (37/128, 22/64) contribute %+.2f deg  =>  phase(H) = %+.2f deg, |H| = %.3f"
          % (p0 - (90 - 180 * F0 / FS), p0, m0))
    print("  phasor sits at phase(H)+180 = %.2f deg  =>  DAMPING + ADDED inertia." % (p0 + 180))
    print("  To enter 90-180 (damping + REDUCED inertia) we need phase(H) < 0, i.e. the two")
    print("  poles must contribute more than %.2f deg of lag." % (90 - 180 * F0 / FS))
    print()

    # ---- the reachable set, over the ACTUAL integer cal grid --------------------
    best = {}
    for K1 in range(1, 128):
        for K2 in range(1, 64):
            m, p = report(K1, K2)
            b = int(round(p))
            if b not in best or m > best[b][0]:
                best[b] = (m, K1, K2)
    print("  Best achievable |H| at each phase, over the FULL integer cal grid (127 x 63):")
    print("   phase(H)   best |H|   K1(/128)  K2(/64)   |H| vs stock   deliverable REDUCED-inertia")
    print("                                                            (|H|*|sin(ph)|, x-inertia today)")
    tgt = m0 * abs(math.sin(math.radians(p0)))
    for b in (80, 60, 40, 20, 0, -10, -20, -40, -60, -80):
        if b in best:
            m, K1, K2 = best[b]
            deliv = m * abs(math.sin(math.radians(b)))
            print("   %+7d   %8.4f   %6d   %6d   %10.4f   %s%.4f  (%.4fx)"
                  % (b, m, K1, K2, m / m0, "  " if b >= 0 else "  ", deliv, deliv / tgt))
    print()
    print("  ANSWER: the 90-180 sector IS geometrically reachable -- phase(H) goes negative")
    print("  from about K2 <= 3 at stock K1, and much further with both poles lowered.")
    print("  BUT the -20 dB/decade cost is brutal and it lands on the wrong quantity:")
    print("  today's phasor delivers |H|*sin = %.3f of ADDED inertia; the best REDUCED-inertia" % tgt)
    print("  the grid can deliver is far smaller, and Y cannot compensate because Y is")
    print("  already at 90%% of its int16 cap (max further gain x1.111).")
    print()
    print("  The Y-compensated verdict -- can a x1.111 Y raise buy back the loss?")
    print("   phase(H)   |H|/|H|_stock   needed Y multiple   available (int16)   VERDICT")
    for b in (0, -10, -20, -40):
        if b in best:
            m, K1, K2 = best[b]
            need = m0 / m
            print("   %+7d   %13.4f   %17.2fx   %17.3fx   %s"
                  % (b, m / m0, need, INT16_MAX / abs(Y0_STOCK) / 3.0,
                     "IMPOSSIBLE" if need > INT16_MAX / abs(Y0_STOCK) / 3.0 else "possible"))
    print()
    print("  K1-ONLY and K2-ONLY sweeps (the other held at stock):")
    print("   cal        value   phase(H)     |H|    |H|/stock   note")
    for K2 in (22, 10, 5, 3, 2, 1):
        m, p = report(37, K2)
        print("   0xC40DC  %6d   %+7.2f  %7.4f   %8.4f   %s"
              % (K2, p, m, m / m0, "STOCK" if K2 == 22 else ("SECTOR REACHED" if p < 0 else "")))
    for K1 in (37, 15, 8, 4, 2, 1):
        m, p = report(K1, 22)
        print("   0xC643C  %6d   %+7.2f  %7.4f   %8.4f   %s"
              % (K1, p, m, m / m0, "STOCK" if K1 == 37 else ("SECTOR REACHED" if p < 0 else "")))

    # ---- FORK 3: reshape specs --------------------------------------------------
    X = (0, 1280, 5760)

    def lerp(v_kmh, Y):
        s = int(round(v_kmh * 64))
        if s <= X[0]:
            return Y[0]
        if s >= X[2]:
            return Y[2]
        i = 1 if s >= X[1] else 0
        num = (Y[i + 1] - Y[i]) * (s - X[i])
        den = X[i + 1] - X[i]
        q = int(num / den) if num * den < 0 else num // den
        return Y[i] + q

    V106 = (-29490, -17202, -5898)
    cands = [
        ("V106 (on the car now)", V106),
        ("RESHAPE A  maximal", (-29490, -29490, -29490)),
        ("RESHAPE B  intermediate", (-29490, -24000, -16000)),
        ("RESHAPE C  conservative", (-29490, -29490, -20000)),
    ]
    print()
    print("=" * 92)
    print("FORK 3 -- RESHAPE SPECS.  Y arrays at 0xD7A5C (mode 26) and 0xD7A6C (mode 27).")
    print("=" * 92)
    speeds = [(8.05, "5 mph"), (20, "20 km/h"), (50, "50 km/h"), (90, "90+ km/h")]
    for nm, Y in cands:
        print()
        print("  %s   Y = %s" % (nm, Y))
        print("    int16 headroom:  Y[0] %6d (%.1f%% of 32767)   Y[1] %6d (%.1f%%)   Y[2] %6d (%.1f%%)"
              % (Y[0], 100 * abs(Y[0]) / INT16_MAX, Y[1], 100 * abs(Y[1]) / INT16_MAX,
                 Y[2], 100 * abs(Y[2]) / INT16_MAX))
        print("    LE bytes: %s" % " ".join("%02x%02x" % (y & 0xFF, (y >> 8) & 0xFF) for y in Y))
        row = "    delivered:"
        rat = "    vs V106:  "
        knee = "    clamp knee (|gp-0x6c2c|):"
        for v, lbl in speeds:
            a = lerp(v, Y)
            b = lerp(v, V106)
            row += "  %s %7d" % (lbl, a)
            rat += "  %s %6.2fx" % (lbl, abs(a) / abs(b))
            knee += "  %s %5.0f" % (lbl, 511 / (abs(a) * K_OF_Y))
        print(row)
        print(rat)
        print(knee)
    print()
    print("  Creep (<=16 km/h) clamp duty is MEASURED: ~10%% at V106's Y[0], and every candidate")
    print("  holds Y[0] EXACTLY at -29490, so creep duty and the relay index are UNCHANGED.")
    print("  !! HIGHWAY clamp duty is UNKNOWN pending a6-score's |gp-0x6c2c| above 16 km/h.")
    print("     If highway |gp-0x6c2c| resembles creep's (p90 ~1064), RESHAPE A's knee of 1065")
    print("     would put highway duty at ~10%% too; RESHAPE B's 1963 keeps it near ~1%%.")


if __name__ == "__main__":
    main()
