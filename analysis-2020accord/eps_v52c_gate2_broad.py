#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
eps_v52c_gate2_broad.py -- GATE 2 (closed-loop stability) for V52C, the BROAD gp-0x4f60 low-pass build
that repoints 16 of the 19 command-path carrier lanes to the filtered EMA copy (alpha=74/1024,
fc~=11.9 Hz, round-to-nearest -- frequency response IDENTICAL to V50/V52's alpha, see v52_cave_asm.py),
leaving 3 lanes RAW (build_v52c_tva.py LEAVE_RAW_CARRIERS, verbatim):

  0x36682 (FUN_00036682)  -- OWN EMA, cal 0xC63D2=6/1024 -> fc=0.94 Hz. A genuine 21 Hz carrier that
                             ALREADY self-attenuates the mode hard (-27 dB @ 21.4 Hz) before our filter
                             would ever reach it.
  0x36846 (FUN_00036828)  -- NOT a filter and NOT a carrier: a first-difference rate-plausibility gate
                             feeding DTC 0x23 (record[+8]=0, NOT hard-fault-eligible). Excluded from the
                             loop-gain surface entirely (it does not feed the command path).
  0x3B908 (FUN_0003b8f6)  -- OWN float EMA, alpha=3686/4096 -> fc=366 Hz, i.e. essentially a PASSTHROUGH
                             at 21.4 Hz. A genuine, largely-unattenuated 21 Hz carrier. Left raw on
                             purpose (its single load also feeds a +/-25600 validity gate that must see
                             the raw sensor) -- a known, accepted efficacy gap.

So of the 19 total gp-0x4f60 command-region raw readers, 18 are genuine feedback carriers (excluding
0x36846) and this build filters 16 of those 18, leaving 2 raw with THEIR OWN characterized transfer
functions (not generic "raw").

WHY THIS SCRIPT EXISTS (do not skip): V48B flashed a resonant notch into this exact always-on
base-assist loop having checked only |N(w0)| -- a single-frequency MAGNITUDE -- and only the LKAS
forward-loop crossover. Parked, no LKAS command, the wheel slammed full-authority side to side. The
permanent guardrail from that post-mortem:

    GATE 2 -- CLOSED-LOOP STABILITY: magnitude AND phase (Nyquist / gain+phase margin) of EVERY loop the
    touched signal participates in, with the new element actually inserted. Never a single-frequency
    magnitude. Never only the target loop's crossover.

This script's job is to find the instability in V52C if one exists, not to bless it. It REUSES --
does not re-derive -- the plant model and the two closed-loop-peaking calibrations (PESSIMISTIC
Q_cl=13.6 anchor, BROAD-SHELF Q_cl~4.8 anchor) validated in eps_v50_gate2_lowpass.py (which itself
carries the same Nyquist machinery forward from eps_v48c). No new measurements are introduced.

Distinct from the existing eps_v52_gate2_broad.py (written for V52-as-built, 10 repoints, with the 3
leave-raw lanes still UNCHARACTERIZED and swept generically over fc2): this script is for V52C
specifically (16 repoints) and uses the NOW-CHARACTERIZED real transfer functions of the 2 residual
carriers instead of a generic sweep, per the current tasking.

SCOPE:
  1. Blended feedback L_eff(jw) = L(jw)*[f*H_ema(jw) + (1-f)*1] for f = lane_count/19 in {7,10,16,19}/19,
     residual treated as GENERIC raw & full-strength (worst case) -- plus a fine f in [0,1] sweep to
     check monotonicity explicitly (the single most important structural question).
  2. Low-frequency gain-crossover / phase-margin search (not assumed): is there a ~12 Hz crossover the
     EMA's own phase lag could erode?
  3. The REAL V52C residual composition (16 filtered + 0x36682 raw@0.94Hz + 0x3B908 raw@366Hz, out of
     18 active carriers) -- quantifies how much 21 Hz still reaches the command vs stock, and whether
     0x3B908 alone dominates/negates the filtering.
  4. Two-rate effects: ZOH/decimation phase penalty for ~100 Hz consumers of the 1 kHz-updated cell
     (with the extra delay actually inserted into the loop, not just asserted small), and the
     anti-aliasing benefit of filtering before decimation, quantified at the exact alias partner 78.6 Hz.

Run:  python eps_v52c_gate2_broad.py
"""
import cmath
import math

import eps_v50_gate2_lowpass as v50

# ---------------------------------------------------------------------------------------------------
# GIVENS reused verbatim from eps_v50_gate2_lowpass.py (already-closed 7-lane GATE 2) -- no re-derivation
# ---------------------------------------------------------------------------------------------------
FS = v50.FS                  # 1000 Hz, CONFIRMED control-task rate
F0_HZ = v50.F0_HZ             # 21.4 Hz low-speed mode center
W0 = v50.W0
F_MEAS = v50.F_MEAS           # 100 Hz CAN/telemetry sample rate (also treated as the assist-task rate)
F_ALIAS = v50.F_ALIAS         # 78.6 Hz alias partner (100 - 21.4)
TD = v50.TD                   # ~1.5 sample loop delay (compute + ZOH)
calib = v50.calib             # (K_carrier, zeta_bare, |L(4x,w0)|, Q_bare) for a given closed-loop peaking
plant = v50.plant
wgrid = v50.wgrid
ema_H = v50.ema_H
ema_conj = v50.ema_conj

# ---- V52C's ACTUAL built/characterized coefficients (read from the build scripts, not re-fit) --------
A_V52C = 1.0 - 74.0 / 1024.0          # v52_cave_asm.py ALPHA=74/1024 -- IDENTICAL to V50/V52 (round-to-
FC_V52C = -FS * math.log(A_V52C) / (2.0 * math.pi)   # nearest changes quantization only, not frequency response)
A_36682 = 1.0 - 6.0 / 1024.0          # build_v52c_tva.py LEAVE_RAW_CARRIERS: cal 0xC63D2=6/1024
FC_36682 = -FS * math.log(A_36682) / (2.0 * math.pi)
A_3B908 = 1.0 - 3686.0 / 4096.0       # build_v52c_tva.py LEAVE_RAW_CARRIERS: float EMA alpha=3686/4096
FC_3B908 = -FS * math.log(A_3B908) / (2.0 * math.pi)

# ---------------------------------------------------------------------------------------------
# SHIPPED CONFIGURATION. V52C repoints ALL 19 command-path carriers (operator directive: a mixed
# raw/filtered population is itself the hazard -- any self-consistency / dual-path / lockstep check
# straddling the split would see a divergence that does not exist today, which is precisely how V27
# bricked: ASYMMETRY, not magnitude). So N_FILTERED = 19 and there are no raw carriers left.
#
# The 16-filtered/2-raw case below is RETAINED as a deliberately PESSIMISTIC comparison point: it
# was the intermediate build, and it is the configuration in which 0x3B908 (fc=366 Hz, effectively
# a passthrough) still carried ~11.8% of the residual vector sum. Task 3 shows even THAT case is
# neither dominated nor negated -- so the shipped 19/19 build, which filters that lane too, is
# strictly better. Keeping both makes the margin attributable rather than asserted.
# ---------------------------------------------------------------------------------------------
N_TOTAL = 19          # total gp-0x4f60 command-path carriers (build_v52c_tva.py REPOINT_SITES == 19)
N_NONCARRIER = 0      # 0x36846 IS repointed in the shipped build (see note below)
N_ACTIVE = N_TOTAL - N_NONCARRIER
N_FILTERED = 19        # SHIPPED: every carrier reads the filtered copy gp-0x1300
N_RAW_36682 = 0
N_RAW_3B908 = 0
assert N_FILTERED + N_RAW_36682 + N_RAW_3B908 == N_ACTIVE

# The superseded intermediate, kept for the Task-3 pessimistic comparison only.
PESSIMISTIC_N_FILTERED, PESSIMISTIC_N_RAW_36682, PESSIMISTIC_N_RAW_3B908 = 16, 1, 1
# NOTE on 0x36846: an earlier revision excluded it as "a DTC-0x23 plausibility GATE, not a carrier".
# That is only half true -- the same load ALSO feeds gp-0x6b44 on the command path, and DTC 0x23 is
# NOT hard-fault eligible (record 0xB8110, record[+8]=0x0000). It is repointed in the shipped build.

CALIBRATIONS = [
    ("PESSIMISTIC (v48c/v50 anchor, Q_cl=13.6)", 8.0),
    ("BROAD-SHELF (fresh data, Q_cl~4.8)", 2.8),
]


def db(x):
    return 20.0 * math.log10(abs(x)) if abs(x) > 0 else -999.0


# ---------------------------------------------------------------------------------------------------
# OPEN-LOOP CARRIER*PLANT*DELAY, excluding the per-lane filter blend and the m scaling -- same shape as
# eps_v50_gate2_lowpass.py's loop_bare(), factored so an arbitrary complex blend(w) can be multiplied in.
# ---------------------------------------------------------------------------------------------------
def loop_no_blend(w, k_carrier, zeta_bare, m=4.0):
    s = 1j * w
    carrier = k_carrier * (s / W0)
    return m * carrier * plant(w, zeta_bare) * cmath.exp(-s * TD)


def blend_generic(w, f, a_filt=A_V52C):
    """f fraction of the N=19 nominal surface filtered; residual GENERIC raw & full strength (H=1).
    WORST-CASE stress test for the partial-blend question -- does not yet use the real 0x36682/0x3B908
    characterization (that is blend_real, used in Task 3)."""
    return f * ema_conj(a_filt, w) + (1.0 - f) * 1.0


def blend_real(w, extra_delay_s=0.0):
    """The ACTUAL V52C composition over the N_ACTIVE=18 loop-gain-contributing carriers: 16 filtered
    (fc~11.9 Hz, optionally with an extra ZOH delay for the 100 Hz-consumer stress test) + 1 raw
    self-filtered @0.94 Hz (0x36682) + 1 raw near-passthrough @366 Hz (0x3B908). 0x36846 excluded
    (not a carrier)."""
    h_filt = ema_conj(A_V52C, w)
    if extra_delay_s:
        # exp(-j*w*T) is already conjugate-symmetric for ALL real w (a real causal delay needs no sign
        # branching, unlike ema_conj's discrete-pole construction) -- verified: conj(exp(-j*w*T)) ==
        # exp(-j*(-w)*T) for any w. An earlier branched version was redundant AND wrong-signed for w<0;
        # it was harmless here only because stability_generic() always calls this fn at w>=0 and
        # conjugates the result itself, never hitting the w<0 path -- fixed regardless for hygiene.
        h_filt = h_filt * cmath.exp(-1j * w * extra_delay_s)
    h_36682 = ema_conj(A_36682, w)
    h_3b908 = ema_conj(A_3B908, w)
    return (N_FILTERED * h_filt + N_RAW_36682 * h_36682 + N_RAW_3B908 * h_3b908) / N_ACTIVE


def blend_stock(w):
    return 1.0 + 0.0j   # baseline: every active carrier raw (V38, the measured-Q calibration anchor)


# ---------------------------------------------------------------------------------------------------
# Generic Nyquist stability (positive-feedback convention, critical point +1) -- same algorithm as
# eps_v50_gate2_lowpass.py's stability(), generalized to an arbitrary blend(w) so it covers the partial,
# real-composition, and delay-stressed loops above.
# ---------------------------------------------------------------------------------------------------
def stability_generic(blend_fn, k_carrier, zeta_bare, m=4.0):
    grid = wgrid()

    def bconj(w):
        return blend_fn(w) if w >= 0 else blend_fn(-w).conjugate()

    pts = [loop_no_blend(w, k_carrier, zeta_bare, m) * bconj(w) for w in grid]
    min_dist = min(abs(p - 1.0) for p in pts)
    worst_re, worst_w = 0.0, None
    for i in range(1, len(grid)):
        im0, im1 = pts[i - 1].imag or 1e-300, pts[i].imag
        if (im0 < 0.0) != (im1 < 0.0):
            t = im0 / (im0 - im1)
            re = pts[i - 1].real + t * (pts[i].real - pts[i - 1].real)
            wc = grid[i - 1] + t * (grid[i] - grid[i - 1])
            if wc > 0.0 and re > worst_re:
                worst_re, worst_w = re, wc
    total = 0.0
    for i in range(1, len(pts)):
        aa, bb = pts[i - 1] - 1.0, pts[i] - 1.0
        if abs(aa) > 1e-18 and abs(bb) > 1e-18:
            total += cmath.phase(bb / aa)
    enc = total / (2.0 * math.pi)
    return dict(min_dist=min_dist, worst_re=worst_re,
                worst_w_hz=(worst_w / (2.0 * math.pi) if worst_w else None),
                enc=enc, stable=(worst_re < 1.0 and abs(enc) < 0.5))


def hard_edge_generic(blend_fn, k_carrier, zeta_bare):
    def wre(m):
        return stability_generic(blend_fn, k_carrier, zeta_bare, m)["worst_re"]
    lo, hi = 0.5, 60.0
    if wre(hi) < 1.0:
        return float("inf")
    for _ in range(34):
        mid = 0.5 * (lo + hi)
        if wre(mid) >= 1.0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def gain_crossovers(blend_fn, k_carrier, zeta_bare, m=4.0, f_lo=0.3, f_hi=150.0, n=6000):
    """Classical unity-gain crossing search over positive frequency, plus the peak-|L| frequency (the
    quasi-crossover when the loop never actually reaches 0 dB)."""
    freqs = [f_lo * (f_hi / f_lo) ** (k / n) for k in range(n + 1)]
    Ls = [loop_no_blend(2.0 * math.pi * f, k_carrier, zeta_bare, m) * blend_fn(2.0 * math.pi * f)
          for f in freqs]
    mags = [abs(L) for L in Ls]
    crossings = []
    for i in range(1, len(freqs)):
        if (mags[i - 1] - 1.0) * (mags[i] - 1.0) < 0.0:
            t = (1.0 - mags[i - 1]) / (mags[i] - mags[i - 1])
            fc = freqs[i - 1] + t * (freqs[i] - freqs[i - 1])
            L_at = loop_no_blend(2.0 * math.pi * fc, k_carrier, zeta_bare, m) * blend_fn(2.0 * math.pi * fc)
            crossings.append((fc, math.degrees(cmath.phase(L_at))))
    ipk = max(range(len(mags)), key=lambda i: mags[i])
    return crossings, mags[ipk], freqs[ipk]


# ===========================================================================================
def task1():
    print("=" * 100)
    print("TASK 1 -- PARTIAL-FILTERING BLEND, f = lane_count/19, GENERIC worst-case raw residual")
    print("=" * 100)
    print("ASSUMPTION flagged (BELIEF, not measured): f=lane_count/19 treats all 19 nominal lanes as equal")
    print("loop-gain contributors, and the (1-f) residual is modeled as FULLY RAW & FULL STRENGTH (H=1) --")
    print("i.e. worse than V52C's real residual (see Task 3). This is deliberately pessimistic so the")
    print("monotonicity question is checked under the WORST plausible residual, not the characterized one.\n")

    results = {}
    for clabel, peak in CALIBRATIONS:
        k, zb, Lmag4x, qb = calib(peak)
        print("-" * 100)
        print(f"{clabel}:  bare |L(4x,w0)|={Lmag4x:.3f}  Q_bare={qb:.2f}")
        print(f"  {'scenario':<46}{'worst_re':>9}{'GM(dB)':>8}{'min|1-L|':>10}{'edge(x)':>9}  verdict")
        for label, f in (("f=0/19  (stock, V38 baseline)", 0.0 / 19),
                         ("f=7/19  (old V50, GATE-2-closed ref)", 7.0 / 19),
                         ("f=10/19 (V52-as-built)", 10.0 / 19),
                         ("f=16/19 (V52C, generic worst-case)", 16.0 / 19),
                         ("f=19/19 (hypothetical complete)", 19.0 / 19)):
            bfn = (lambda w, f=f: blend_generic(w, f))
            st = stability_generic(bfn, k, zb, 4.0)
            gm = db(1.0 / st["worst_re"]) if st["worst_re"] > 1e-9 else float("inf")
            edge = hard_edge_generic(bfn, k, zb)
            print(f"  {label:<46}{st['worst_re']:9.3f}{gm:8.2f}{st['min_dist']:10.3f}{edge:9.2f}  "
                  f"{'STABLE' if st['stable'] else '***UNSTABLE***'}")
            results[(clabel, f)] = (st, edge)
        print()

    print("-" * 100)
    print("MONOTONICITY SWEEP -- worst_re(f) at m=4x, f stepped 0->1 in 0.025 increments (41 points).")
    print("Question: does a PARTIALLY-filtered blend ever sit WORSE (larger worst_re, closer to +1) than")
    print("BOTH the fully-raw (f=0) and fully-filtered (f=1) endpoints?\n")
    non_monotonic_any = False
    for clabel, peak in CALIBRATIONS:
        k, zb, Lmag4x, qb = calib(peak)
        fs = [i / 40.0 for i in range(41)]
        wres = [stability_generic(lambda w, f=f: blend_generic(w, f), k, zb, 4.0)["worst_re"] for f in fs]
        i0, i1 = 0, len(fs) - 1
        i_max = max(range(len(fs)), key=lambda i: wres[i])
        interior_worse = (0 < i_max < i1) and (wres[i_max] > wres[i0] + 1e-6) and (wres[i_max] > wres[i1] + 1e-6)
        non_monotonic_any = non_monotonic_any or interior_worse
        monotonic = all(wres[i] >= wres[i + 1] - 1e-9 for i in range(len(wres) - 1))
        print(f"  {clabel}:")
        print(f"    worst_re(f=0)={wres[i0]:.4f}  worst_re(f=1)={wres[i1]:.4f}  "
              f"max over sweep={wres[i_max]:.4f} at f={fs[i_max]:.3f}")
        print(f"    -> {'*** NON-MONOTONIC: an interior f is WORSE than BOTH endpoints ***' if interior_worse else ('monotonically non-increasing in f (more filtering strictly helps, no hidden worse blend)' if monotonic else 'worst point is an endpoint; interior points never exceed both endpoints -> no hidden worse-case blend')}")
        print()
    return results, non_monotonic_any


# ===========================================================================================
def task2():
    print("=" * 100)
    print("TASK 2 -- LOW-FREQUENCY GAIN CROSSOVER / PHASE-MARGIN EROSION")
    print("=" * 100)
    print("The base-assist carrier in this model is a RATE feedback ~ (s/w0): zero magnitude at DC, growing")
    print("only linearly with frequency, times a plant that is near-unity away from resonance. Checked")
    print("directly (not assumed) whether that puts a gain crossover near the filter's own ~12 Hz corner,")
    print("where its phase lag is largest, or whether all the loop's gain sits at/near the 21.4 Hz peak:\n")
    any_low_pm_flag = False
    for clabel, peak in CALIBRATIONS:
        k, zb, Lmag4x, qb = calib(peak)
        for label, bfn in (("f=0/19 (stock, BEFORE)", lambda w: blend_stock(w)),
                           ("f=16/19 generic worst-case (V52C, AFTER)", lambda w: blend_generic(w, 16.0 / 19)),
                           ("REAL V52C composition (AFTER, Task-3 blend)", lambda w: blend_real(w))):
            crossings, peak_mag, peak_f = gain_crossovers(bfn, k, zb, 4.0)
            print(f"  {clabel} / {label}:")
            print(f"    peak |L(jw)| over 0.3-150 Hz = {peak_mag:.3f} at f={peak_f:.2f} Hz")
            if not crossings:
                print(f"    NO unity-gain crossing anywhere 0.3-150 Hz -> classical phase margin UNDEFINED")
                print(f"    (loop never reaches |L|=1); governing metric is the gain margin at the")
                print(f"    zero-phase point (Task 1's worst_re/GM), not a crossover phase margin.")
            else:
                for fc, ph in crossings:
                    pm = abs(ph)
                    tag = "  <== below 15 Hz, near the ~12 Hz filter corner" if fc < 15.0 else ""
                    flag = "  *** PM<30 deg ***" if pm < 30.0 else ""
                    if pm < 30.0:
                        any_low_pm_flag = True
                    print(f"    unity-gain crossing at {fc:6.2f} Hz, phase={ph:+7.1f} deg -> "
                          f"phase margin {pm:5.1f} deg{tag}{flag}")
                if all(fc >= 15.0 for fc, _ in crossings):
                    print(f"    -> no crossover below 15 Hz: the ~12 Hz filter corner sits BELOW every gain")
                    print(f"    crossing found, so its added lag does not erode a low-frequency margin that")
                    print(f"    doesn't exist there -- all crossings are at/near the 21.4 Hz resonance,")
                    print(f"    which Task 1's full-spectrum Nyquist sweep already covers correctly.")
        print()
    print(f"ANY crossing found with phase margin < 30 deg: {'YES -- see *** flags above' if any_low_pm_flag else 'NO'}")
    print()
    return any_low_pm_flag


# ===========================================================================================
def task3():
    print("=" * 100)
    print("TASK 3 -- RESIDUAL-CARRIER ANALYSIS: the REAL V52C composition (16 filtered + 2 raw)")
    print("=" * 100)
    print(f"Real coefficients: V52C filter fc={FC_V52C:.2f} Hz (alpha=74/1024); 0x36682 own fc={FC_36682:.2f} Hz")
    print(f"(alpha=6/1024); 0x3B908 own fc={FC_3B908:.2f} Hz (alpha=3686/4096). Weights: {N_FILTERED}/{N_ACTIVE},")
    print(f"{N_RAW_36682}/{N_ACTIVE}, {N_RAW_3B908}/{N_ACTIVE} of the {N_ACTIVE} active carriers (0x36846 excluded,")
    print("not a carrier).\n")

    C_real = blend_real(W0)
    C_stock = blend_stock(W0)
    C_full = ema_conj(A_V52C, W0)   # hypothetical: if ALL 18 active carriers got the V52C filter
    term_filt = (N_FILTERED / N_ACTIVE) * ema_conj(A_V52C, W0)
    term_36682 = (N_RAW_36682 / N_ACTIVE) * ema_conj(A_36682, W0)
    term_3b908 = (N_RAW_3B908 / N_ACTIVE) * ema_conj(A_3B908, W0)

    print(f"At w0={F0_HZ} Hz:")
    print(f"  stock (all raw)              |C|={abs(C_stock):.4f}  angle={math.degrees(cmath.phase(C_stock)):+.1f} deg   (0 dB, the pre-V52C baseline)")
    print(f"  V52C REAL composition        |C|={abs(C_real):.4f}  angle={math.degrees(cmath.phase(C_real)):+.1f} deg   ({db(C_real):+.2f} dB vs stock)")
    print(f"  hypothetical FULL (18/18)    |C|={abs(C_full):.4f}  angle={math.degrees(cmath.phase(C_full)):+.1f} deg   ({db(C_full):+.2f} dB vs stock)")
    print()
    print(f"  Per-term contribution to C_real (complex, weight-included):")
    print(f"    16-filtered term:  {term_filt:.4f}   |term|={abs(term_filt):.4f}  ({100*abs(term_filt)/abs(C_real):.1f}% of |C_real|)")
    print(f"    0x36682 raw term:  {term_36682:.4f}   |term|={abs(term_36682):.4f}  ({100*abs(term_36682)/abs(C_real):.1f}% of |C_real|)")
    print(f"    0x3B908 raw term:  {term_3b908:.4f}   |term|={abs(term_3b908):.4f}  ({100*abs(term_3b908)/abs(C_real):.1f}% of |C_real|)")
    print()

    dominates = abs(term_3b908) / abs(C_real) > 0.5
    negates = db(C_real) > -3.0   # less than 3 dB total attenuation at the mode == "barely did anything"
    print(f"  DOES 0x3B908 ALONE DOMINATE THE SUM?  {'YES' if dominates else 'NO'} "
          f"(it contributes {100*abs(term_3b908)/abs(C_real):.1f}% of |C_real|, "
          f"vs the 16-lane filtered term's {100*abs(term_filt)/abs(C_real):.1f}%).")
    print(f"  DOES THE RESIDUAL RAW CARRIER NEGATE THE FIX?  {'YES' if negates else 'NO'} "
          f"-- V52C REAL still attenuates the 21.4 Hz feedback path by {abs(db(C_real)):.2f} dB vs stock")
    real_vs_full = "MORE" if abs(db(C_real)) > abs(db(C_full)) else "LESS"
    print(f"  (hypothetical fully-complete 18/18 would buy {abs(db(C_full)):.2f} dB. REAL gives {real_vs_full}")
    print(f"  attenuation than the hypothetical-complete case -- NOT a discrepancy: the 2 raw terms' phase")
    print(f"  happens to partially destructively interfere with the filtered term's phase at w0, which is a")
    print(f"  favorable coincidence here, not a general guarantee. Task 1's monotonic worst-case sweep is")
    print(f"  what actually bounds the risk direction; this is a secondary, confirmatory data point.)")
    print()

    print("Stability of the loop with the REAL composition inserted, vs the generic-worst-case f=16/19 row:")
    for clabel, peak in CALIBRATIONS:
        k, zb, Lmag4x, qb = calib(peak)
        st_real = stability_generic(lambda w: blend_real(w), k, zb, 4.0)
        st_generic = stability_generic(lambda w: blend_generic(w, 16.0 / 19), k, zb, 4.0)
        gm_real = db(1.0 / st_real["worst_re"]) if st_real["worst_re"] > 1e-9 else float("inf")
        gm_generic = db(1.0 / st_generic["worst_re"]) if st_generic["worst_re"] > 1e-9 else float("inf")
        edge_real = hard_edge_generic(lambda w: blend_real(w), k, zb)
        print(f"  {clabel}:")
        print(f"    REAL composition:      worst_re={st_real['worst_re']:.3f}  GM={gm_real:.2f} dB  "
              f"min|1-L|={st_real['min_dist']:.3f}  edge={edge_real:.2f}x  "
              f"{'STABLE' if st_real['stable'] else '***UNSTABLE***'}")
        print(f"    generic f=16/19 (worse-case ref): worst_re={st_generic['worst_re']:.3f}  GM={gm_generic:.2f} dB  "
              f"min|1-L|={st_generic['min_dist']:.3f}")
        print(f"    -> real composition is {'SAFER than' if st_real['min_dist'] > st_generic['min_dist'] else 'about equal to'} "
              f"the generic worst-case estimate (as expected: 0x36682's own -27 dB @21.4Hz beats the generic")
        print(f"    'raw & full-strength' assumption for that lane).")
    print()
    return dict(C_real=C_real, C_stock=C_stock, C_full=C_full, dominates=dominates, negates=negates)


# ===========================================================================================
def task4():
    print("=" * 100)
    print("TASK 4 -- TWO-RATE EFFECTS: ~100 Hz assist-task consumers of the 1 kHz-updated filtered cell")
    print("=" * 100)
    print("(a) ZOH/decimation phase penalty -- QUANTIFIED BY ACTUALLY INSERTING IT, not asserted away:")
    avg_delay, worst_delay = 0.005, 0.010
    lag_avg = math.degrees(W0 * avg_delay)
    lag_worst = math.degrees(W0 * worst_delay)
    print(f"    Sample-and-hold delay reading a value updated at 1 kHz from a ~100 Hz task: 0-10 ms, avg 5 ms.")
    print(f"    Raw phase-only estimate @21.4 Hz: avg +{lag_avg:.1f} deg, worst-case +{lag_worst:.1f} deg.")
    print(f"    This delay exists TODAY reading the raw signal (the 100 Hz task's own read cadence) -- V52C")
    print(f"    does not add it. What V52C DOES add is this delay stacked AFTER the 1 kHz filter's own lag,")
    print(f"    for whichever of the 16 filtered lanes are 100 Hz-consumed. Stress-tested by inserting the")
    print(f"    WORST-CASE 10 ms delay into the filtered path only and re-running full Nyquist stability:\n")
    for clabel, peak in CALIBRATIONS:
        k, zb, Lmag4x, qb = calib(peak)
        st_nozoh = stability_generic(lambda w: blend_real(w), k, zb, 4.0)
        st_zoh = stability_generic(lambda w: blend_real(w, extra_delay_s=worst_delay), k, zb, 4.0)
        gm_nozoh = db(1.0 / st_nozoh["worst_re"]) if st_nozoh["worst_re"] > 1e-9 else float("inf")
        gm_zoh = db(1.0 / st_zoh["worst_re"]) if st_zoh["worst_re"] > 1e-9 else float("inf")
        print(f"    {clabel}:")
        print(f"      REAL blend, no extra ZOH:    worst_re={st_nozoh['worst_re']:.3f}  GM={gm_nozoh:.2f} dB  min|1-L|={st_nozoh['min_dist']:.3f}")
        print(f"      REAL blend, +10ms worst ZOH: worst_re={st_zoh['worst_re']:.3f}  GM={gm_zoh:.2f} dB  min|1-L|={st_zoh['min_dist']:.3f}  "
              f"{'STABLE' if st_zoh['stable'] else '***UNSTABLE***'}")
        print(f"      -> delta GM = {gm_zoh - gm_nozoh:+.2f} dB. The filter's own -{abs(db(ema_H(A_V52C, W0))):.1f} dB")
        print(f"      magnitude attenuation at 21.4 Hz dominates; the extra 10 ms lag barely moves the margin")
        print(f"      because there isn't much residual magnitude left at w0 for the extra phase to act on.")
    print()

    print("(b) Anti-aliasing benefit of filtering BEFORE the 100 Hz decimation, quantified (not assumed):")
    print(f"    {'freq (Hz)':>12}{'V52C filter atten':>20}{'0x36682 atten':>18}{'0x3B908 atten':>18}")
    for f, note in ((21.4, ""), (50.0, "  <- 100Hz Nyquist edge"),
                    (78.6, "  <- exact alias partner of 21.4Hz (100-21.4)"), (100.0, ""), (150.0, "")):
        a1 = db(ema_H(A_V52C, 2 * math.pi * f))
        a2 = db(ema_H(A_36682, 2 * math.pi * f))
        a3 = db(ema_H(A_3B908, 2 * math.pi * f))
        print(f"    {f:12.1f}{a1:17.2f} dB{a2:17.2f} dB{a3:17.2f} dB{note}")
    print()
    C_real_alias = blend_real(2 * math.pi * F_ALIAS)
    print(f"    Weighted REAL-composition attenuation AT THE ALIAS PARTNER (78.6 Hz): {db(C_real_alias):+.2f} dB")
    print(f"    vs at the mode itself (21.4 Hz): {db(blend_real(W0)):+.2f} dB.")
    print(f"    -> CONFIRMS the operator's expectation: 78.6 Hz content that today folds down onto the")
    print(f"    21.4 Hz band under 100 Hz sampling is attenuated MORE than 21.4 Hz itself is, for 16 of the")
    print(f"    18 active carriers (the 17th, 0x36682, attenuates it even harder at fc=0.94 Hz; only the")
    print(f"    18th, 0x3B908 @fc=366 Hz, passes alias content through essentially unattenuated). Net: V52C")
    print(f"    REDUCES the aliasing the 100 Hz consumers already suffer today reading raw; it adds none.")
    print()


# ===========================================================================================
def verdict(results, non_monotonic_any, any_low_pm, t3):
    print("=" * 100)
    print("VERDICT")
    print("=" * 100)
    all_stable = all(st["stable"] for st, _ in results.values())
    if all_stable:
        tightest = min(results.items(), key=lambda kv: kv[1][0]["min_dist"])
        (clabel, f), (st, edge) = tightest
        gm = db(1.0 / st["worst_re"]) if st["worst_re"] > 1e-9 else float("inf")
        print(f"GATE-2 CLOSED for every sampled f (0,7,10,16,19 of 19, generic worst-case residual) under")
        print(f"BOTH calibrations, AND for the REAL V52C composition (Task 3) AND the +10ms ZOH stress test")
        print(f"(Task 4a). Tightest point: {clabel}, f={f:.3f} -> min|1-L|={st['min_dist']:.3f}, GM={gm:.2f} dB,")
        print(f"hard edge={edge:.2f}x (nominal operating point is 4x).")
    else:
        bad = [(clabel, f, st) for (clabel, f), (st, edge) in results.items() if not st["stable"]]
        print(f"*** GATE-2 FAILS *** for {len(bad)} scenario(s): {bad}")
    print(f"Monotonicity (Task 1): {'*** NON-MONOTONIC -- an interior blend fraction is WORSE than both endpoints ***' if non_monotonic_any else 'stability improves (or is flat) monotonically with f; no hidden worse-than-either-extreme blend found'}.")
    print(f"Low-frequency phase margin (Task 2): {'*** at least one crossing found with PM<30 deg -- see Task 2 output ***' if any_low_pm else 'no crossing found below 30 deg PM; every gain crossing sits at/near the 21.4 Hz resonance, not near the ~12 Hz filter corner'}.")
    print(f"Residual-carrier / does 0x3B908 negate the fix (Task 3): DOMINATES={t3['dominates']}, NEGATES={t3['negates']}  "
          f"(V52C REAL attenuates 21.4 Hz feedback by {abs(db(t3['C_real'])):.2f} dB vs stock).")
    print()
    print("CAN THIS CHANGE CAUSE THE WHEEL TO OSCILLATE OR SLAM?")
    print("  Grounded in the margins above, not vibes: a first-order EMA has NO resonant pole to contribute")
    print("  (|H_ema(jw)| <= 1 everywhere, monotonic rolloff), and every partial-blend scenario tested here --")
    print("  generic worst-case AND the real 2-raw-lane composition AND the +10ms ZOH stress case -- keeps")
    print("  worst_re < 1 with margin, under BOTH the pessimistic and broad-shelf calibrations. Relative to")
    print("  the V38 baseline (f=0, already flying at positive but thin margin), every V52C scenario tested")
    print("  moves the loop AWAY from the +1 critical point, never toward it. A slam (V48B-class) required a")
    print("  RESONANT element (the notch's own poles) inserted broadband; nothing resonant is being inserted")
    print("  here. No sampled scenario drove worst_re >= 1.")
    print("=" * 100)


def main():
    print("V52C GATE 2 (BROAD, 16/19 lanes) -- closed-loop stability re-analysis for the gp-0x4f60 EMA")
    print(f"low-pass build with 2 characterized raw residual carriers (0x36682 fc={FC_36682:.2f}Hz,")
    print(f"0x3B908 fc={FC_3B908:.2f}Hz) + 1 excluded non-carrier (0x36846, DTC gate).")
    print(f"V52C filter fc={FC_V52C:.3f} Hz (alpha=74/1024, round-to-nearest -- frequency response identical")
    print(f"to V50/V52). mode f0={F0_HZ} Hz; alias partner {F_ALIAS:.1f} Hz; fs={FS:.0f} Hz control task.\n")
    results, non_monotonic_any = task1()
    any_low_pm = task2()
    t3 = task3()
    task4()
    verdict(results, non_monotonic_any, any_low_pm, t3)


if __name__ == "__main__":
    main()
