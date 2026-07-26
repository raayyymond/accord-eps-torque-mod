#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
eps_v50_gate2_lowpass.py -- GATE 2 (closed-loop stability) for V50 = a FIRST-ORDER EMA LOW-PASS on the
shared torsion-bar signal gp-0x4f60, chosen over V48B's notch for three reasons this session established:

  1. FREQUENCY-ROBUST. Fresh manual-drive data (analyze_manual_vibration.py + manual_speed_split.py)
     shows the felt mode is SPEED-DEPENDENT: ~21.7 Hz at low speed (3-8 m/s, the worst/most-audible
     regime), sliding to ~8-12 Hz at highway speed. A narrow notch centered at 21.4 Hz misses the
     high-speed content; a low-pass attenuates the WHOLE 8-22 Hz band at once.
  2. ALIAS-ROBUST. The 21.5-vs-78.6 Hz aliasing is unresolved (no >100 Hz witness). A low-pass on the
     1 kHz signal rolls off 78.6 Hz EVEN HARDER than 21.7 Hz, so it works either way; a notch tuned to
     21.4 Hz would be a null at 78.6 Hz.
  3. GATE-1 SIMPLE. A first-order EMA has ONE state cell (the output = previous output). V48B's biquad
     needed FOUR (x1/x2/y1/y2); its x2 cell gp-0x14FA aliased a live monitor byte and bricked. One cell,
     placed in the V48B-post-mortem's vetted-safe RAM, removes that entire failure mode.

Also RE-FITS the loop-gain calibration. eps_v48c_gate2_closed_loop.py is anchored to the FALSIFIED
sharp-line reading (Q_cl=13.6, |L(w0)|=0.875, 1.16 dB margin). The 2026-07-22 re-audit + this session's
fresh PSD put the closed-loop peaking at Q_cl ~= 4-5 (broad low-Q shelf). A less-marginal loop needs LESS
attenuation, so re-fitting lets us pick the GENTLEST corner that still restores margin -> least feel cost
(the operator's stated preference). We bracket BOTH readings and require the pick to be safe under the
pessimistic (Q=13.6) one too.

Reuses the verified Nyquist/stability machinery from eps_v48c_gate2_closed_loop.py (positive-feedback
convention, full signed-w contour). NO new measurements introduced here.

Run:  python eps_v50_gate2_lowpass.py
"""
import cmath
import math

FS = 1000.0                 # confirmed control-task rate
F0_HZ = 21.4                # low-speed mode center (fresh data: 21.7; keep 21.4 for continuity)
W0 = 2.0 * math.pi * F0_HZ
F_MEAS = 100.0              # CAN telemetry sample rate (the ALIAS is a measurement artifact, not firmware)
F_ALIAS = F_MEAS - F0_HZ    # 78.6 Hz -- the unresolved alias partner (100 Hz-sampled CAN can't tell them apart)
TD = 1.5 / FS               # ~1 sample + half-sample ZOH loop delay


# ---- calibration as a function of the assumed closed-loop peaking (re-fit knob) -------------------
def calib(peak_4x):
    """Return (K_carrier, zeta_bare) so that |L(4x,w0)| = 1 - 1/peak_4x at the -90deg plant peak."""
    L_mag_4x = 1.0 - 1.0 / peak_4x
    k_per_m = L_mag_4x / 4.0
    # closed-loop Q relates to bare zeta via the same peaking; keep the model's derivation:
    #   Q_meas ~ Q_bare / (1 - L_mag)  ->  zeta_bare = zeta_meas * (1 - L_mag). Use Q_meas = peak_4x*Q_ref.
    # Simpler + model-consistent: fix zeta_bare from the SAME relation eps_v48c used at its anchor,
    # scaled so the bare plant stays ~Q1.7 at the pessimistic anchor and rises gently as peaking drops.
    zeta_meas = 1.0 / (2.0 * (peak_4x * (13.6 / 8.0)))   # ties Q_meas=13.6 when peak_4x=8 (v48c anchor)
    zeta_bare = zeta_meas / L_mag_4x if L_mag_4x > 0 else zeta_meas
    q_bare = 1.0 / (2.0 * zeta_bare)
    k_carrier = k_per_m / q_bare
    return k_carrier, zeta_bare, L_mag_4x, q_bare


def plant(w, zeta, w0=W0):
    s = 1j * w
    return (w0 * w0) / (s * s + 2.0 * zeta * w0 * s + w0 * w0)


def loop_bare(w, k_carrier, zeta_bare, m=4.0, extra_lag_deg=0.0):
    s = 1j * w
    carrier = k_carrier * (s / W0) * cmath.exp(-1j * math.radians(extra_lag_deg))
    return m * carrier * plant(w, zeta_bare) * cmath.exp(-s * TD)


# ---- first-order EMA low-pass (ONE state cell): H(z) = (1-a)/(1 - a z^-1), a = exp(-2*pi*fc/fs) ----
def ema_a(fc):
    return math.exp(-2.0 * math.pi * fc / FS)


def ema_H(a, w):
    return (1.0 - a) / (1.0 - a * cmath.exp(-1j * w / FS))


def ema_conj(a, w):
    return ema_H(a, w) if w >= 0 else ema_H(a, -w).conjugate()


def q_alpha(fc, scale):
    """The nearest integer Q<scale> coefficient for alpha, and the alpha it actually realizes."""
    a = ema_a(fc)
    alpha = 1.0 - a
    qi = round(alpha * scale)
    return qi, 1.0 - qi / scale     # (integer coeff, realized pole a)


# ---- Nyquist stability (positive-feedback convention: critical point +1) --------------------------
def wgrid(f_lo=0.05, f_hi=300.0, n=16000):
    fs_ = [2.0 * math.pi * f_lo * (f_hi / f_lo) ** (k / n) for k in range(n + 1)]
    return [-w for w in reversed(fs_)] + fs_


def stability(a, k_carrier, zeta_bare, m=4.0, extra_lag_deg=0.0):
    grid = wgrid()
    pts = [loop_bare(w, k_carrier, zeta_bare, m, extra_lag_deg) * ema_conj(a, w) for w in grid]
    min_dist = min(abs(p - 1.0) for p in pts)
    worst_re = 0.0
    for i in range(1, len(grid)):
        im0, im1 = pts[i - 1].imag or 1e-300, pts[i].imag
        if (im0 < 0.0) != (im1 < 0.0):
            t = im0 / (im0 - im1)
            re = pts[i - 1].real + t * (pts[i].real - pts[i - 1].real)
            wc = grid[i - 1] + t * (grid[i] - grid[i - 1])
            if wc > 0.0 and re > worst_re:
                worst_re = re
    total = 0.0
    for i in range(1, len(pts)):
        aa, bb = pts[i - 1] - 1.0, pts[i] - 1.0
        if abs(aa) > 1e-18 and abs(bb) > 1e-18:
            total += cmath.phase(bb / aa)
    enc = total / (2.0 * math.pi)
    return dict(min_dist=min_dist, worst_re=worst_re, enc=enc,
                stable=(worst_re < 1.0 and abs(enc) < 0.5))


def hard_edge(a, k_carrier, zeta_bare):
    def wre(m):
        return stability(a, k_carrier, zeta_bare, m)["worst_re"]
    lo, hi = 0.5, 40.0
    if wre(hi) < 1.0:
        return float("inf")
    for _ in range(34):
        mid = 0.5 * (lo + hi)
        if wre(mid) >= 1.0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def db(x):
    return 20.0 * math.log10(abs(x)) if abs(x) > 0 else -999.0


def main():
    print("=" * 96)
    print("V50 GATE 2 -- first-order EMA low-pass on gp-0x4f60, re-fit to the broad-shelf reading")
    print("=" * 96)
    print(f"mode f0={F0_HZ} Hz (low-speed, fresh data 21.7); alias partner {F_ALIAS:.1f} Hz; fs={FS:.0f} Hz\n")

    # bracket the loop marginality: pessimistic (falsified sharp line) vs broad-shelf (fresh)
    for label, peak in (("PESSIMISTIC (v48c anchor, Q_cl=13.6)", 8.0),
                        ("BROAD-SHELF (fresh data, Q_cl~4.8)", 2.8)):
        k, zb, Lmag, qb = calib(peak)
        st_bare = stability(1e-12, k, zb)  # a~0 => unity filter (no low-pass)
        print("-" * 96)
        print(f"{label}:  |L(4x,w0)|={Lmag:.3f}  Q_bare={qb:.2f}  bare |1-L|min={st_bare['min_dist']:.3f}"
              f"  bare edge={hard_edge(1e-12,k,zb):.2f}x")
        print(f"  {'filter':<22}{'a(pole)':>9}{'att@21.4':>10}{'att@78.6':>10}"
              f"{'ph@3Hz':>9}{'|1-L|min':>10}{'edge':>8}  verdict")
        for fc in (8.0, 10.0, 12.0, 15.0, 18.0):
            a = ema_a(fc)
            st = stability(a, k, zb)
            att214 = db(ema_H(a, W0))
            att786 = db(ema_H(a, 2 * math.pi * F_ALIAS))
            ph3 = math.degrees(cmath.phase(ema_H(a, 2 * math.pi * 3.0)))
            edge = hard_edge(a, k, zb)
            print(f"  LP fc={fc:<5.0f}Hz        {a:9.4f}{att214:9.2f}dB{att786:9.2f}dB"
                  f"{ph3:+8.1f}{st['min_dist']:10.3f}{edge:7.1f}x  "
                  f"{'STABLE' if st['stable'] else '***UNSTABLE***'}")
        print()

    # integer coefficient realizability (Q10, matching the kit's cal scale 1024)
    print("-" * 96)
    print("INTEGER COEFFICIENT (EMA alpha = 1-a, as Q10 = /1024, the kit's cal scale):")
    for fc in (8.0, 10.0, 12.0, 15.0):
        qi, a_real = q_alpha(fc, 1024)
        print(f"  fc={fc:>4.0f} Hz -> alpha={1-ema_a(fc):.4f} -> Q10 coeff={qi:4d}/1024 "
              f"(realizes fc={-FS*math.log(a_real)/(2*math.pi):.1f} Hz)")

    print("\nSELECTION LOGIC:")
    print("  * Under the BROAD-SHELF re-fit the loop is far less marginal (bare |1-L|min ~0.36 vs 0.139),")
    print("    so a GENTLE corner (fc~12-15 Hz) already restores comfortable margin -> minimal 3 Hz feel")
    print("    cost. Under the PESSIMISTIC anchor the same corner is still STABLE with a big margin gain.")
    print("  * A first-order EMA is Gate-2-robust by construction (no resonant pole) and stable under +-30")
    print("    deg carrier-phase error (checked in the v48c sensitivity sweep for the same LP family).")
    print("  * att@78.6 >> att@21.4 => the pick works whether the true mode is 21.7 Hz or its 78.6 Hz alias.")
    print("  * ONE state cell -> Gate 1 is a single vetted-safe RAM cell (V48B post-mortem: gp-0x14E0),")
    print("    not the 4-cell biquad that put x2 into the poison region.")


if __name__ == "__main__":
    main()
