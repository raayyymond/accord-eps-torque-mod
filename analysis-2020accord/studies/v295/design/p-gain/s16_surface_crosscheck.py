# -*- coding: utf-8 -*-
"""s16_surface_crosscheck.py -- SECOND METHOD for the recommendation's Kp LERP and surface: an independent integer march
that re-implements the Kp LERP the way the listing does it (0x29E14..0x29E32: sub, mul, divq SIGNED trunc-toward-zero,
add, zxh), not via the golden model, compared on idx 0..240 with the golden lkas_rate_lerp and lkas_rate_pid_surface.
(First run inline on 2026-09-30; output out/s16_surface_crosscheck_out.txt.)  ANALYSIS ONLY."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pg_lib as G  # noqa: E402
H = G.H
from s8_finalists import finalists  # noqa: E402


def lerp_listing(X, Y, x):
    if not X[0] < x:                          # 0x29DEA cmp ; bh
        return Y[0]
    if not x < X[4]:                          # 0x29DF6 cmp ; bnc -> ld.hu 0x8(r10) = Y[4]
        return Y[4]
    k = 1
    while X[k] <= x:                          # 0x29E0A..0x29E12 walk
        k += 1
    num = (Y[k] - Y[k - 1]) * (x - X[k - 1])  # 0x29E20 sub ; 0x29E24 sub ; 0x29E26 mul (low word)
    den = X[k] - X[k - 1]                     # 0x29E2A sub
    q = abs(num) // den
    q = -q if num < 0 else q                  # 0x29E2C divq: signed, truncates toward zero
    return (Y[k - 1] + q) & 0xFFFF            # 0x29E30 add ; 0x29E32 zxh


def main():
    base, F = finalists()
    rec = F[0]
    tab = H.lerp_table(rec.kp_x, rec.kp_y, 241)
    bad = sum(lerp_listing(rec.kp_x, rec.kp_y, i) != int(tab[i]) for i in range(241))
    print("Kp LERP, listing-style vs golden lkas_rate_lerp over idx 0..240: mismatches", bad)
    mt = H.lerp_table(rec.map_x, rec.map_y, 241)

    def T_of(i):
        P = min(15360, ((int(mt[i]) << 2) * lerp_listing(rec.kp_x, rec.kp_y, i)) >> 8)
        S = min(15360, (254 * P) >> 8)
        o, seen = 0, set()
        while o not in seen:
            seen.add(o)
            o2 = ((992 * o) >> 10) + ((S * 507) >> 10)
            y = (o + o2) >> 5
            o = o2
        return min(3072, (y * 5346) >> 15)
    S = G.surface_table(rec)
    mm = [(i, T_of(i), int(S[i])) for i in range(241) if T_of(i) != int(S[i])]
    print("surface, hand march vs golden march over idx 0..240: mismatches", len(mm), mm[:5])


if __name__ == "__main__":
    main()
