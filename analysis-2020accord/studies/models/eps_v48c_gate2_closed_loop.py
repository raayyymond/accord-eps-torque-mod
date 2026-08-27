#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
studies/models/eps_v48c_gate2_closed_loop.py -- GATE 2 (closed-loop stability) for reviving the 21 Hz notch as V48C.

WHY THIS FILE EXISTS
--------------------
V48B (the 21.4 Hz notch code cave) was FLASHED and bricked violently (full-authority steering
oscillation, parked, no LKAS). Two confirmed defects, one shared gap -- the cave was validated only
IN ISOLATION:
  * GATE 1 (RAM ownership) -- the x2 state cell gp-0x14FA aliased a live monitor byte.  [handled elsewhere]
  * GATE 2 (closed-loop stability) -- THIS FILE. The design only ever inserted the notch's
    single-frequency MAGNITUDE |N(21.4)| into the *LKAS* loop-gain model (studies/models/eps_loop_gain_model.py),
    which predicts the notch HELPS. It never analyzed the notch's MAGNITUDE **and PHASE** across
    frequency inside the loop the signal actually lives in -- the always-on base-assist loop -- which
    is where a notch's own lightly-damped poles (r=0.979, Q~3.2) and its +-25 deg phase swing across
    18-26 Hz can matter. studies/models/eps_loop_gain_model.py Task 4(d) is annotated FALSIFIED for exactly this.

This script closes Gate 2 properly: it builds the base-assist loop transfer function L(jw), inserts a
candidate filter as N * L (the filter sits in the FEEDBACK path -- it filters gp-0x4f60 before the
collocated carriers read it), and runs a full Nyquist / gain+phase-margin analysis across frequency,
for the BARE loop, the V48B notch, and a menu of candidate V48C filters. It answers the one question a
V48C must answer before it can be called flash-ready:

    With this filter inserted, does the base-assist loop keep positive stability margin at EVERY
    frequency -- not just at 21.4 Hz?

PROVENANCE (kept strictly separate; this file introduces NO new measurements)
-----------------------------------------------------------------------------
It reuses the SAME calibrated model as studies/models/eps_loop_gain_model.py (the golden loop-gain reference):
  MEASURED (route b9, V38): f0=21.4 Hz, closed-loop Q(4x)=13.6.
  ANCHOR (model): read "8x amplitude at 4x" as positive-feedback peaking |1/(1-L(jw0))|=8
                  => |L(jw0)|=0.875 at 4x, loop phase ~0 deg (rate carrier through the -90 deg plant peak).
  DERIVED: K_PER_M=0.21875 (|L| per delivered-command multiple), zeta_bare=0.294 (Q_bare~1.7).
The loop's frequency SHAPE (not just its value at w0) is a MODEL: L(s) = m*k*(s/w0)*P(s)*exp(-s*td),
a rate (derivative) carrier through a 2nd-order resonance with a small sample+ZOH loop delay. This
reproduces the model's anchor exactly (|L(4x,w0)|=0.875, angle ~ -11.6 deg) AND gives the off-w0
behaviour Gate 2 needs. Model uncertainty is handled by (a) a discrete cross-check of the notch and
(b) a carrier-phase sensitivity sweep -- the qualitative verdict must not depend on either.

TOPOLOGY (docs/research/VIBRATION-DOSSIER.md sec.4, studies/models/eps_loop_gain_model.py): the 21 Hz feedback closes through
UNFILTERED, 1 kHz, collocated, positive-feedback base-assist lanes that read Sensor-B torque gp-0x4f60
(chiefly FUN_0003a382, which has a raw torque-derivative stage). A notch on gp-0x4f60 sits in that
FEEDBACK path -> L_filtered(jw) = N(jw) * L_bare(jw).

Run:  python studies/models/eps_v48c_gate2_closed_loop.py
"""

import cmath
import math

# ---------------------------------------------------------------------------
# CALIBRATION -- identical to studies/models/eps_loop_gain_model.py (self-consistent by construction)
# ---------------------------------------------------------------------------
F0_HZ       = 21.4
W0          = 2.0 * math.pi * F0_HZ
FS          = 1000.0                       # confirmed control-task rate
Q_MEAS_4X   = 13.6
ZETA_MEAS_4X = 1.0 / (2.0 * Q_MEAS_4X)

PEAK_4X   = 8.0
L_MAG_4X  = 1.0 - 1.0 / PEAK_4X            # 0.875  (|L(jw0)| at 4x)
K_PER_M   = L_MAG_4X / 4.0                 # 0.21875
ZETA_BARE = ZETA_MEAS_4X / (1.0 - L_MAG_4X)  # 0.294  (Q_bare ~1.70)
Q_BARE    = 1.0 / (2.0 * ZETA_BARE)

# rate-carrier normalization so that |L(jw0)| = K_PER_M*m at the -90 deg plant peak:
#   L(jw0) = m*k*(j)*(-j*Q_bare) = m*k*Q_bare  (real +)  =>  k = K_PER_M / Q_bare
K_CARRIER = K_PER_M / Q_BARE
# loop transport delay: ~1 compute sample + half-sample ZOH (matches Task 1's -11.6 deg at w0)
TD = 1.5 / FS

M_V38 = 4.0                                # the on-car multiple we must be safe at

# V48B notch (the built cave's actual Q12 int16 coefficients, scale 4096)
V48B_Q = 4096.0
V48B_NOTCH = (4045 / V48B_Q, -7949 / V48B_Q, 3977 / V48B_Q, -7949 / V48B_Q, 3926 / V48B_Q)


# ---------------------------------------------------------------------------
# PLANT + BARE LOOP (continuous model)
# ---------------------------------------------------------------------------
def plant(w, zeta=ZETA_BARE, w0=W0):
    """Unity-DC 2nd-order resonance."""
    s = 1j * w
    return (w0 * w0) / (s * s + 2.0 * zeta * w0 * s + w0 * w0)


def loop_bare(w, m=M_V38, carrier_extra_lag_deg=0.0):
    """Base-assist open-loop gain L(jw) = m*k*(s/w0)*P(s)*exp(-s*td), rate (derivative) carrier.
    carrier_extra_lag_deg models a non-ideal carrier (mix of derivative + integrator + EMA) as extra
    phase lag at all frequencies -- used only for the sensitivity sweep."""
    s = 1j * w
    carrier = K_CARRIER * (s / W0) * cmath.exp(-1j * math.radians(carrier_extra_lag_deg))
    return m * carrier * plant(w) * cmath.exp(-s * TD)


# ---------------------------------------------------------------------------
# CANDIDATE FILTERS  (all return a complex frequency response at w; the ones in the
# feedback path multiply L_bare). Discrete biquads are evaluated on z = exp(jwT).
# ---------------------------------------------------------------------------
def biquad_H(coeffs, w, fs=FS):
    """Discrete biquad H(e^{jwT}) from normalized (b0,b1,b2,a1,a2)."""
    b0, b1, b2, a1, a2 = coeffs
    z = cmath.exp(1j * w / fs)
    zi = 1.0 / z
    return (b0 + b1 * zi + b2 * zi * zi) / (1.0 + a1 * zi + a2 * zi * zi)


def rbj_peaking(f0, q, gain_db, fs=FS):
    """RBJ peaking EQ (gain_db<0 => finite-depth notch). Returns normalized biquad coeffs."""
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * f0 / fs
    cw, sw = math.cos(w0), math.sin(w0)
    alpha = sw / (2.0 * q)
    b0 = 1.0 + alpha * A
    b1 = -2.0 * cw
    b2 = 1.0 - alpha * A
    a0 = 1.0 + alpha / A
    a1 = -2.0 * cw
    a2 = 1.0 - alpha / A
    return (b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0)


def biquad_pole_radius(coeffs):
    _b0, _b1, _b2, a1, a2 = coeffs
    disc = cmath.sqrt(a1 * a1 - 4.0 * a2)
    return max(abs((-a1 + disc) / 2.0), abs((-a1 - disc) / 2.0))


def first_order_lp(fc, fs=FS):
    """First-order (single real pole) low-pass, matched-Z-ish via bilinear. NO resonant pole."""
    wc = 2.0 * math.pi * fc / fs
    # bilinear: analog 1/(1+s/wc_a) -> use pre-warped. Simpler robust EMA form:
    #   pole a = exp(-wc)  ; H(z) = (1-a)/(1 - a z^-1)  (unity DC, one real pole, no ringing)
    a = math.exp(-wc)
    return ("ema", a)


def ema_H(a, w, fs=FS):
    zi = cmath.exp(-1j * w / fs)
    return (1.0 - a) / (1.0 - a * zi)


def second_order_lp(fc, fs=FS):
    """Critically-damped (zeta=1, two coincident real poles) 2nd-order low-pass = cascade of two EMAs.
    NO resonant peak (zeta>=1)."""
    wc = 2.0 * math.pi * fc / fs
    a = math.exp(-wc)
    return ("ema2", a)


def ema2_H(a, w, fs=FS):
    h = ema_H(a, w, fs)
    return h * h


def filter_response(spec, w):
    """Uniform evaluator. spec is either a 5-tuple biquad or a tagged tuple."""
    if isinstance(spec, tuple) and len(spec) == 5 and not isinstance(spec[0], str):
        return biquad_H(spec, w)
    tag = spec[0]
    if tag == "ema":
        return ema_H(spec[1], w)
    if tag == "ema2":
        return ema2_H(spec[1], w)
    if tag == "unity":
        return 1.0 + 0j
    raise ValueError(spec)


# ---------------------------------------------------------------------------
# NYQUIST / STABILITY  (POSITIVE-FEEDBACK convention: char. eq. 1 - L = 0;
# anti-damping => L real-positive at w0; instability => Nyquist encircles +1.)
# ---------------------------------------------------------------------------
def _wgrid(f_lo=0.05, f_hi=200.0, n=24000):
    """Symmetric log-spaced frequency grid (rad/s) for a full Nyquist contour, dense near the mode."""
    fs_ = []
    for k in range(n + 1):
        f = f_lo * (f_hi / f_lo) ** (k / n)
        fs_.append(2.0 * math.pi * f)
    neg = [-w for w in reversed(fs_)]
    return neg + fs_


def _filter_conj(spec, w):
    # frequency response is conjugate-symmetric for a real filter: H(-w)=conj(H(w))
    if w >= 0:
        return filter_response(spec, w)
    return (filter_response(spec, -w)).conjugate()


def loop_full(w, spec, m=M_V38, carrier_extra_lag_deg=0.0):
    """L(jw) over the FULL (signed-w) contour with correct conjugate symmetry, so the winding
    number of (L-1) is meaningful."""
    return loop_bare(w, m, carrier_extra_lag_deg) * _filter_conj(spec, w)


def stability(spec, m=M_V38, carrier_extra_lag_deg=0.0, grid=None):
    """Return a dict: min distance from the Nyquist curve to +1, list of positive-real-axis crossings
    (f_hz, Re, 'up'/'down'), encirclements of +1 (winding number), and stable?."""
    grid = grid or _wgrid()
    pts = [loop_full(w, spec, m, carrier_extra_lag_deg) for w in grid]
    # min distance to the critical point +1
    min_dist = min(abs(p - 1.0) for p in pts)
    # positive-real-axis crossings (Im changes sign) with Re at the crossing
    crossings = []
    for i in range(1, len(grid)):
        im0, im1 = pts[i - 1].imag, pts[i].imag
        if im0 == 0.0:
            im0 = 1e-300
        if (im0 < 0.0) != (im1 < 0.0):  # sign change
            t = im0 / (im0 - im1)
            re = pts[i - 1].real + t * (pts[i].real - pts[i - 1].real)
            w_c = grid[i - 1] + t * (grid[i] - grid[i - 1])
            if re > 0.0 and w_c > 0.0:  # report the physical (positive-f) positive-Re crossings
                direction = "up" if im1 > im0 else "down"
                crossings.append((w_c / (2.0 * math.pi), re, direction))
    # winding number of (L - 1) around 0 over the closed contour
    total = 0.0
    for i in range(1, len(pts)):
        a = pts[i - 1] - 1.0
        b = pts[i] - 1.0
        if abs(a) < 1e-18 or abs(b) < 1e-18:
            continue
        total += cmath.phase(b / a)
    encirclements = total / (2.0 * math.pi)
    # any positive-f crossing to the RIGHT of +1 => the curve passes the critical point on the unstable side
    worst_re = max((re for _f, re, _d in crossings), default=0.0)
    stable = (worst_re < 1.0) and (abs(encirclements) < 0.5)
    return dict(min_dist=min_dist, crossings=crossings, worst_re=worst_re,
                encirclements=encirclements, stable=stable)


def hard_edge_multiple(spec, carrier_extra_lag_deg=0.0):
    """Smallest LKAS multiple m at which the loop (with this filter) first reaches the +1 point
    (worst positive-real-axis crossing Re -> 1.0). Coarse->fine bisection."""
    def worst_re(m):
        return stability(spec, m, carrier_extra_lag_deg, grid=_wgrid(n=6000))["worst_re"]
    lo, hi = 0.5, 40.0
    if worst_re(hi) < 1.0:
        return float("inf")
    if worst_re(lo) >= 1.0:
        return lo
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if worst_re(mid) >= 1.0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


# ---------------------------------------------------------------------------
# FEEL metrics: how much the filter disturbs the base-assist band (0-5 Hz) and the notch depth/phase.
# ---------------------------------------------------------------------------
def db(x):
    return 20.0 * math.log10(abs(x)) if abs(x) > 0 else -999.0


def feel(spec):
    def at(f):
        h = filter_response(spec, 2.0 * math.pi * f)
        return db(h), math.degrees(cmath.phase(h))
    d1, p1 = at(1.0)
    d3, p3 = at(3.0)
    d5, p5 = at(5.0)
    d214, p214 = at(21.4)
    return dict(d1=d1, p1=p1, d3=d3, p3=p3, d5=d5, p5=p5, d214=d214, p214=p214)


# ===========================================================================
def banner(t):
    print("=" * 92)
    print(t)
    print("=" * 92)


def report_row(name, spec, m=M_V38):
    st = stability(spec, m)
    fl = feel(spec)
    edge = hard_edge_multiple(spec)
    pk_w0 = 1.0 / abs(1.0 - loop_full(W0, spec, m)) if abs(1.0 - loop_full(W0, spec, m)) > 1e-9 else float("inf")
    prad = ""
    if isinstance(spec, tuple) and len(spec) == 5 and not isinstance(spec[0], str):
        prad = f"{biquad_pole_radius(spec):.3f}"
    print("  %-30s  att@21.4=%6.2fdB  ph@21.4=%+6.1f  att@3=%6.2fdB  ph@3=%+5.1f" %
          (name, fl["d214"], fl["p214"], fl["d3"], fl["p3"]))
    print("  %-30s  |1-L| min=%.3f  worstRe=%.3f  peak@w0=%4.1fx  edge=%s  poles r=%s  => %s" %
          ("", st["min_dist"], st["worst_re"], pk_w0,
           ("%.2fx" % edge) if edge != float("inf") else ">40x", prad or "n/a",
           "STABLE" if st["stable"] else "***UNSTABLE***"))
    if st["crossings"]:
        cs = ", ".join("%.1fHz:Re=%.2f" % (f, re) for f, re, _d in st["crossings"])
        print("  %-30s  +Re-axis crossings: %s" % ("", cs))
    print()
    return st


def main():
    print()
    banner("V48C GATE 2  --  CLOSED-LOOP STABILITY OF THE BASE-ASSIST LOOP WITH A 21 Hz FILTER INSERTED")
    print("The check V48B skipped: magnitude AND PHASE across frequency (Nyquist / margin), in the")
    print("always-on base-assist loop, for the actual filter -- not a single-frequency magnitude.")
    print("Positive-feedback convention: critical point = +1; stable iff the Nyquist curve of L stays")
    print("left of +1 (no positive-real-axis crossing with Re>=1, no encirclement).")
    print()
    print("  Model anchor check:  |L_bare(4x, 21.4Hz)| = %.4f  angle = %+.1f deg   (target 0.875, ~-11.6)"
          % (abs(loop_bare(W0)), math.degrees(cmath.phase(loop_bare(W0)))))
    print("  zeta_bare = %.3f (Q_bare %.2f) ; K_PER_M = %.5f ; loop delay td = %.2f ms"
          % (ZETA_BARE, Q_BARE, K_PER_M, TD * 1000))
    print()

    banner("STEP 1 -- THE BARE LOOP (V38, 4x, no filter): how marginal is it, really?")
    print("  This is the on-car-validated starting point. Any V48C must be >= this stable.")
    print()
    st_bare = report_row("BARE loop (V38 4x)", ("unity",))
    print("  READ: the bare 4x loop's Nyquist curve passes only |1-L|min=%.3f from the +1 point --" % st_bare["min_dist"])
    print("  i.e. ~%.1f dB gain margin. That thin margin IS the measured Q=13.6 peaking. This is the" % (20 * math.log10(1 / L_MAG_4X)))
    print("  number a filter must IMPROVE without opening a new approach to +1 at another frequency.")
    print()

    banner("STEP 2 -- THE V48B NOTCH, evaluated as a pure filter (RAM bug removed): is it Gate-2 safe?")
    print("  Isolates the control question from the RAM collision. Same biquad the cave computed.")
    print("  (r=%.3f, Q_pole~%.1f resonator.)" % (biquad_pole_radius(V48B_NOTCH), 1.0 / (2.0 * (1 - biquad_pole_radius(V48B_NOTCH)))))
    print()
    st_v48b = report_row("V48B notch (Q5, -8dB)", V48B_NOTCH)

    banner("STEP 3 -- CANDIDATE V48C FILTERS  (feedback-path; att@3Hz/ph@3Hz = base-assist FEEL cost)")
    print("  A first-order low-pass has NO resonant pole (Gate-2-robust by construction) and its phase")
    print("  LAG rotates the rate-carrier loop AWAY from the +real anti-damping alignment (adds damping).")
    print("  A notch preserves low-frequency feel (unity at DC) but is a lightly-damped resonator.")
    print()
    candidates = [
        ("notch Q5 -8dB (=V48B)",      V48B_NOTCH),
        ("notch Q2 -8dB (damped)",     rbj_peaking(21.4, 2.0, -8.0)),
        ("notch Q1.5 -10dB (damped)",  rbj_peaking(21.4, 1.5, -10.0)),
        ("1st-order LP fc=8Hz",        first_order_lp(8.0)),
        ("1st-order LP fc=10Hz",       first_order_lp(10.0)),
        ("1st-order LP fc=12Hz",       first_order_lp(12.0)),
        ("2nd-order LP fc=12Hz (z=1)", second_order_lp(12.0)),
    ]
    results = {}
    for name, spec in candidates:
        results[name] = (spec, report_row(name, spec))

    banner("STEP 4 -- SENSITIVITY: does the verdict survive carrier-phase model error?")
    print("  The carrier is modeled as a pure derivative (+90 deg). Real net carrier is a mix")
    print("  (derivative + S3 integrator + Stage-A EMA). Re-run the two front-runners with +-30 deg")
    print("  extra carrier lag; the qualitative verdict must not flip.")
    print()
    for name in ("notch Q2 -8dB (damped)", "1st-order LP fc=10Hz"):
        spec = results[name][0]
        for lag in (-30.0, 0.0, 30.0):
            st = stability(spec, M_V38, carrier_extra_lag_deg=lag)
            print("  %-26s carrier lag %+5.1f deg:  |1-L|min=%.3f  worstRe=%.3f  => %s"
                  % (name, lag, st["min_dist"], st["worst_re"], "STABLE" if st["stable"] else "UNSTABLE"))
        print()

    banner("SUMMARY / RECOMMENDATION")
    print("  * BARE 4x loop: |1-L|min = %.3f (~%.1f dB). Marginal by construction (the measured Q=13.6)."
          % (st_bare["min_dist"], 20 * math.log10(1 / L_MAG_4X)))
    print("  * V48B notch as a pure filter: worstRe=%.3f, |1-L|min=%.3f -> %s. (The on-car brick was"
          % (st_v48b["worst_re"], st_v48b["min_dist"], "STABLE" if st_v48b["stable"] else "UNSTABLE"))
    print("    dominated by the RAM collision; this isolates whether the notch ITSELF is Gate-2 safe.)")
    print("  * See the table for which candidate gives the largest |1-L|min AND the smallest 3 Hz feel")
    print("    cost AND the highest hard-edge multiple. That triple is the V48C selection criterion.")
    print("  * Whatever wins here still needs GATE 1 (genuinely-free RAM, writers verified) before build,")
    print("    and first-minutes on-car observation after any flash. Gate 2 is necessary, not sufficient.")
    print("=" * 92)


if __name__ == "__main__":
    main()
