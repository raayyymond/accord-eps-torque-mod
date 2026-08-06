"""v77 GATE 2 -- the SAMPLED-AND-HELD describing function, and the per-tick step budget.

The damper `gp-0x6bd0` is recomputed by `FUN_00034350` on a 100 Hz task and HELD; every downstream
consumer (the 1 kHz task) sees the staircase, not the surface. So the correct nonlinearity for GATE 2
is the sample-and-hold composition, whose describing function is COMPLEX (magnitude AND phase) and
depends on the number of samples per cycle -- at 21 Hz there are only 4.76 of them.

  N_sampled(A, f) = (2/T) * integral over one period of  u_held(t) * exp(-j*w*t) dt   /  A
  averaged over the sampling PHASE (which is not observable and drifts).

Everything about the surface is byte-read; the 100 Hz task rate is relayed from the coordinator's own
`FUN_00034350 <- FUN_00022ca0` (task 5) determination and is NOT re-derived here -- flagged.
"""
import cmath
import math
from v77_gate2_describing_function import Surface, N_closed, CX, STOCK, V74, V75

TS = 0.010                      # 100 Hz damper task
NPHASE = 96                     # sampling phases averaged over
NCYC = 400                      # cycles simulated per phase (long enough for phase drift too)


def mk(name, cy0, ex, ey):
    return Surface(name, CX, [cy0, 234, 429, 908], list(ex), list(ey))


V77A = mk("V77-a C566 X1=400", 566, [12, 400, 2500, 4000], [0, 539, 539, 927])
V77B = mk("V77-b C566 X1=525", 566, [12, 525, 2500, 4000], [0, 539, 539, 927])
V77L = mk("V77-lo C500 X1=400", 500, [12, 400, 2500, 4000], [0, 539, 539, 927])
YDOWN = mk("Y1=140 X1=400", 566, [12, 400, 2500, 4000], [0, 140, 539, 927])
BUILDS = [STOCK, V74, V75, V77A, V77B, V77L, YDOWN]


# ==================================================================================================
# 0. CHECK THE COORDINATOR'S SAMPLING ARITHMETIC -- exact, not the small-angle form
# ==================================================================================================
print("=" * 104)
print("0. THE ZERO-CROSSING TRANSIT TIME -- exact:  t = 2*arcsin(X1/A)/w   (NOT the linear 2*X1/(A*w))")
print("=" * 104)
print(f"   {'symptom':12s} {'A':>6s} {'f':>7s} {'A*w (ct/s)':>11s} {'ct per 10ms':>12s}"
      f" {'X1':>5s} {'transit ms':>11s} {'samples':>8s} {'linear-approx ms':>17s}")
for nm, A, f in (("grind #1", 1184, 21.0), ("ratchet", 461, 7.79)):
    w = 2 * math.pi * f
    for x1 in (200, 400, 525):
        if x1 >= A:
            continue
        t_exact = 2 * math.asin(x1 / A) / w
        t_lin = 2 * x1 / (A * w)
        print(f"   {nm:12s} {A:6d} {f:7.2f} {A*w:11.0f} {A*w*TS:12.0f}"
              f" {x1:5d} {t_exact*1e3:11.2f} {t_exact/TS:8.2f} {t_lin*1e3:17.2f}")
print()
print("   VERDICT ON THE COORDINATOR'S NUMBERS:")
print("     grind  2.6 ms @X1=200 and 5.2 ms @X1=400  -- CORRECT, matches the exact formula.")
print("     ratchet 27 ms / 55 ms                     -- 🛑 TOO HIGH. Exact is 18.3 ms / 42.9 ms.")
print("     The CONCLUSION is unchanged in direction but SHARPENED: at V75's X1=200 the ratchet")
print("     crossing occupies 1.83 samples, NOT 2.7 -- i.e. V75 pushed the ratchet crossing from")
print("     'comfortably resolved' (V74, 4.29 samples) to 'marginally resolved'. That is a bigger")
print("     effect than the 27/55 figures imply, and it lands at the ratchet, not the grind.")


# ==================================================================================================
# 1. THE SAMPLED-AND-HELD DESCRIBING FUNCTION
# ==================================================================================================
def sampled_df(surf, A, f, ts=TS, nphase=NPHASE, ncyc=NCYC):
    """Complex N for the 100 Hz sample-and-held odd nonlinearity, averaged over sampling phase."""
    w = 2 * math.pi * f
    acc = 0j
    for p in range(nphase):
        phi = 2 * math.pi * p / nphase
        # simulate ncyc cycles of the input; sample times are t_k = k*ts
        Tsim = ncyc / f
        nsamp = int(Tsim / ts) + 2
        num, den = 0j, 0.0
        for k in range(nsamp):
            t0, t1 = k * ts, (k + 1) * ts
            r = A * math.sin(w * t0 + phi)
            u = surf.u(r)
            # exact integral of u*exp(-j w t) over the held interval
            num += u * (cmath.exp(-1j * w * t0) - cmath.exp(-1j * w * t1)) / (1j * w)
            den += ts
        # correlating with exp(-jwt) leaves a factor exp(+j*phi) from the input's own phase;
        # de-rotate by exp(-j*phi), then by +j so a pure in-phase (viscous) term reads REAL POSITIVE.
        acc += 1j * (2.0 / den) * num / A * cmath.exp(-1j * phi)
    return acc / nphase


def step_stats(surf, A, f, ts=TS, nphase=NPHASE, ncyc=60):
    """Per-tick step |u[n]-u[n-1]| in counts: the max and the 95th pct over sampling phase."""
    w = 2 * math.pi * f
    steps = []
    for p in range(nphase):
        phi = 2 * math.pi * p / nphase
        nsamp = int(ncyc / f / ts) + 2
        prev = None
        for k in range(nsamp):
            u = surf.u(A * math.sin(w * k * ts + phi))
            if prev is not None:
                steps.append(abs(u - prev))
            prev = u
    steps.sort()
    return max(steps), steps[int(0.99 * len(steps))], steps[int(0.5 * len(steps))]


print()
print("=" * 104)
print("1. SAMPLED-AND-HELD DESCRIBING FUNCTION vs the CONTINUOUS one")
print("   |N| = equivalent damping (ct torque per ct rate); ang N = the phase it INTRODUCES.")
print("   A damper only damps through cos(ang); a lag beyond -90 deg turns it into an ANTI-damper.")
print("=" * 104)
for A, f, nm in ((1184, 21.0, "grind #1"), (461, 7.79, "ratchet"), (300, 7.79, "ratchet, small")):
    print(f"\n   -- {nm}:  A = {A} ct, f = {f} Hz, {1/(f*TS):.2f} samples/cycle --")
    print(f"      {'build':22s} {'N_cont':>8s} {'|N_smp|':>8s} {'ang N':>8s} {'cos(ang)':>9s}"
          f" {'eff damp':>9s} {'step max':>9s} {'step p99':>9s} {'step p50':>9s}")
    for s in BUILDS:
        nc = N_closed(s, A)
        ns = sampled_df(s, A, f)
        mx, p99, p50 = step_stats(s, A, f)
        ang = math.degrees(cmath.phase(ns)) if abs(ns) > 1e-9 else 0.0
        print(f"      {s.name:22s} {nc:8.3f} {abs(ns):8.3f} {ang:8.2f} {math.cos(math.radians(ang)):9.3f}"
              f" {abs(ns)*math.cos(math.radians(ang)):9.3f} {mx:9.0f} {p99:9.0f} {p50:9.0f}")
print()
print("   ZOH reference lag  -w*Ts/2 :"
      f"  7.79 Hz -> {-180*7.79*TS:.1f} deg   21 Hz -> {-180*21.0*TS:.1f} deg")


# ==================================================================================================
# 2. THE STEP BUDGET, as a first-class output
# ==================================================================================================
print()
print("=" * 104)
print("2. PER-TICK STEP BUDGET (counts of gp-0x6bd0 change in ONE 10 ms tick)")
print("   The plateau height M is 2*M for a full sign flip. This is the edge the trip sees.")
print("=" * 104)
print(f"   {'build':22s} {'M':>5s} {'2M (full flip)':>15s} {'grind step p99':>15s}"
      f" {'ratchet step p99':>17s} {'X1':>5s} {'entries/s creep':>16s}")
SIGMA = 169.6
for s in BUILDS:
    M = s.g(2000)
    _, g99, _ = step_stats(s, 1184, 21.0)
    _, r99, _ = step_stats(s, 461, 7.79)
    rate_per_s = 7.25 * math.exp(-(s.EX[1] ** 2 - 200 ** 2) / (2 * SIGMA ** 2))
    print(f"   {s.name:22s} {M:5d} {2*M:15d} {g99:15.0f} {r99:17.0f} {s.EX[1]:5d}"
          f" {rate_per_s:16.2f}")
print("   'entries/s creep' extrapolates the coordinator's measured 7.25/s (V75, X1=200) and")
print("   0.53/s (V74, X1=400) via Rice's formula; the two anchor sigma = 169.6 ct independently")
print("   of the earlier 282/35 pair, and give the SAME sigma -- a third consistency check.")
sig2 = math.sqrt((400 ** 2 - 200 ** 2) / (2 * math.log(7.25 / 0.53)))
print(f"   sigma from the /s pair (7.25 -> 0.53) = {sig2:.1f} ct  vs {SIGMA:.1f} from the count pair.")
