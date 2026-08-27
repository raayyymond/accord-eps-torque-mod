"""K1 (`0xC40D2`) dose sizing for FUN_0003b8f6's modelled Coulomb friction.

Question: did V89 double a term running at well under 1% of its authority?
Answer: yes -- 0.3-0.4% of the +-10 clamp, and that clamp is structurally
unreachable at K1=204. But the dose that WOULD matter manufactures a V80-class
relay through the CLAMP (not through the `ratio` nonlinearity, which K1 cannot
affect at all).

Every constant byte-read little-endian from the V89 image. Each arithmetic line
annotated with the instruction address it mirrors. Self-checking: the describing
function reproduces the kit's own recorded relay index 7.87 before anything else
is computed.

Study/analysis only. No build is proposed here.
"""

import math
import os
import struct
import sys

ROOT = os.environ.get(
    "ACCORD_FIRMWARE_ROOT", r"C:/Users/dudei/Desktop/Projects/accord-firmwares"
)
V89 = os.path.join(
    ROOT, "analysis-2020accord",
    "_v89_V88BASE-FRICTION.C40D2.204-CAVE.6AE2.SIGN.MAG64_plain_image.bin",
)
TP = 0x000BF000  # tp+0x6000 = 0xC5000, NOT 0xC6000 -- compute, never eyeball

with open(V89, "rb") as fh:
    IMAGE = fh.read()
assert len(IMAGE) == 0x100000, len(IMAGE)


def u16(addr):
    return struct.unpack_from("<H", IMAGE, addr)[0]


K1 = u16(TP + 0x50D2)      # 0xC40D2  |model|-proportional Coulomb friction
K0 = u16(TP + 0x5080)      # 0xC4080  PURE Coulomb -- NEVER RAISE
CAL_BC = u16(TP + 0x50BC)  # 0xC40BC  relay denominator; encoded 0x50BD (disp|1)
A_FRIC = u16(TP + 0x50D0)  # 0xC40D0  friction EMA alpha numerator, /4096

DELTA = CAL_BC / 12.0      # ratio saturates at |gp-0x6abc| = cal/12   @0x3BAB0
CLAMP = 10.0               # the +-10.0 FRICTION clamp

# Measured proxies. NOT from the V89 routes -- see the report; substituted from
# V87 route-71 (engaged gp-0x6b98) and the recorded 0xC40BC sizing (gp-0x6abc).
CMD = {"p50": 208, "p90": 966, "p99": 1637}
RATE_P50, RATE_P90, RING_A = 35, 228, 5


def selfcheck():
    assert (K1, K0, CAL_BC, A_FRIC) == (204, 0, 600, 408), (K1, K0, CAL_BC, A_FRIC)
    idx = N_sat(50, DELTA) / N_sat(500, DELTA)
    assert abs(idx - 7.87) < 0.01, idx
    print(f"[ok] V89 cals: K1={K1} K0={K0} 0xC40BC={CAL_BC} 0xC40D0={A_FRIC}")
    print(f"[ok] describing-function index N(50)/N(500) = {idx:.3f} "
          f"reproduces the kit's recorded 7.87 -> model validated")


def N_sat(A, d):
    """Describing function of clamp(x/d, +-1) for a zero-mean sinusoid amplitude A.

    Mirrors  ratio = clamp(pol * gp-0x6abc * 12 / cal(0xC40BC), +-1)   @0x3BAB4
    (the two *0.5 factors in the decompiled divide cancel exactly).
    """
    if A <= d:
        return 1.0 / d
    r = d / A
    return (2 / math.pi) * (math.asin(r) + r * math.sqrt(1 - r * r)) / d


def ratio(x, d):
    return max(-1.0, min(1.0, x / d))


def friction(model_abs, rat, k1):
    """FRICTION = |model|*ratio*K1/1024 + K0/1024*ratio, pre-EMA, pre-clamp.

    Mirrors @0x3BAE8-0x3BB0C. K0 == 0 on every build, so the second term vanishes.
    """
    return model_abs * rat * k1 / 1024.0 + (K0 / 1024.0) * rat


def report_index_invariance():
    print("\n[index] K1 multiplies the OUTPUT of the nonlinearity, so it cannot enter N():")
    for k in (102, K1, 5041, 25206):
        print(f"    K1={k:6d} -> index {N_sat(50, DELTA)/N_sat(500, DELTA):.3f}")
    print("  => INVARIANT. On the Honda-1.00 / V75-1.45 / V80-3.27 scale K1 does not move.")


def report_biased_df():
    print(f"\n[biased DF] delta = {CAL_BC}/12 = {DELTA:.0f} counts of gp-0x6abc")
    for B, lbl in ((RATE_P50, "p50"), (RATE_P90, "p90"), (int(DELTA), "B == delta")):
        lo, hi = B - RING_A, B + RING_A
        if hi <= DELTA:
            st = "FULLY LINEAR (index 1.00) -- NOT a relay"
        elif lo >= DELTA:
            st = "FULLY SATURATED -- ring sees ~ZERO incremental gain"
        else:
            st = "*** switching region: the only place relay behaviour lives ***"
        print(f"    B={B:4d} ({lbl:10s}) span [{lo},{hi}] vs {DELTA:.0f} -> {st}")
    print("  => the golden model's 'pinned at +-1 across 99.62%' is over the +-13000 VALID")
    print("     range, not the OBSERVED distribution. At p50 the term is on the linear ramp.")


def report_ladder():
    print("\n[ladder] FRICTION median as a fraction of the +-10 clamp")
    for rat, tag in ((1.00, "ratio=1.00 (saturated)"), (0.70, "ratio=0.70 (p50, linear)")):
        m50 = CMD["p50"] / 1024.0
        f = friction(m50, rat, K1)
        print(f"  --- {tag} ---")
        print(f"      V89 K1={K1}: {f*1024:6.1f} counts = {100*f/CLAMP:.3f}% of clamp")
        for pct in (10, 25, 50):
            k = pct / 100 * CLAMP * 1024 / (m50 * rat)
            print(f"      median {pct:2d}% -> K1 = {k:8.0f} ({k/K1:5.1f}x V89)")
    need = CLAMP * 1024 / K1
    print(f"\n  clamp needs |model| >= {need:.1f}; max reachable ~24 "
          f"(cmd <= 8192/1024 = 8.0, sensor <= 15*LERP ~ 15.9)")
    print("  => AT V89 THE CLAMP IS STRUCTURALLY UNREACHABLE. It never binds.")


def report_clamp_hazard():
    print("\n[hazard] the +-10 CLAMP, not `ratio`, is what manufactures a relay at dose:")
    for pct in (10, 25, 50):
        k = pct / 100 * CLAMP * 1024 / (CMD["p50"] / 1024.0)
        row = "".join(
            f"  {lbl}->{100*friction(c/1024.0, 1.0, k)/CLAMP:6.1f}%"
            f"{' CLAMPED' if friction(c/1024.0, 1.0, k) >= CLAMP else '        '}"
            for lbl, c in CMD.items())
        print(f"    K1={k:7.0f} (median {pct:2d}%):{row}")
    print("  p90/p50 = 4.6x, so setting the MEDIAN to 25% necessarily clamps the top decile.")
    print("  => only the ~10% rung stays off the bound across the measured distribution.")


def report_c40bc_confound():
    print("\n[item 4] is 0xC40BC index-only?  NO -- in the linear region ratio = x/delta,")
    print("  so raising delta DIVIDES the friction gain. It moves gain AND index together.")
    mu = math.log(RATE_P50)
    sig = (math.log(RATE_P90) - math.log(RATE_P50)) / 1.2816
    zs = [-2.0, -1.5, -1.0, -0.5, 0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    xs = [math.exp(mu + sig * z) for z in zs]
    w = [math.exp(-z * z / 2) for z in zs]
    g6 = sum(wi * ratio(x, 50) for wi, x in zip(w, xs)) / sum(w)
    g60 = sum(wi * ratio(x, 500) for wi, x in zip(w, xs)) / sum(w)
    print(f"    distribution-weighted mean ratio: cal600 {g6:.4f} vs cal6000 {g60:.4f}"
          f"  => {g6/g60:.2f}x FRICTION-GAIN contrast")
    print("  => the flown 600-vs-6000 result is CONFOUNDED (gain + index). Suggestive of the")
    print("     K1 direction, NOT corroborating.")


def main():
    selfcheck()
    report_index_invariance()
    report_biased_df()
    report_ladder()
    report_clamp_hazard()
    report_c40bc_confound()
    print("\n[GATE 2] NOT statically closable: FRICTION -> model -> gp-0x6bfc -> resid ->")
    print("  gp-0x6b70 is Path 2, whose loop gain is runtime gain-scheduled by iVar32/iVar33")
    print("  via FUN_0003897a. No loop-gain number is produced here, by design.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
