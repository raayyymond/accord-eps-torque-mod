#!/usr/bin/env python3
"""X7 -- the LOOP-GAIN question, done in the one way that is not degenerate.

🛑 THE NAIVE PRODUCT IS IDENTICALLY 1.  If  A = |cmd(f0)| / |meas(f0)|  and
   B = |meas(f0)| / |cmd(f0)|  are both read off the SAME two channels, then A*B == 1 by
   construction, for any data whatsoever.  It carries no information and it is degenerate for
   exactly the reason the phase was: one dominant mode makes every channel a scaled copy of one
   sinusoid.  Formally, with

       cmd  = A * meas                     (openpilot's controller: deterministic, so A IS
                                            identifiable from the ratio, whatever drives meas)
       meas = B * cmd + d                  (plant, plus everything else driving the column)

   substitution gives meas = d / (1 - A*B).  A is identifiable; **B is not**, from these two
   channels alone, because d is unobserved and correlated with cmd through the loop.

   So this file does NOT report |meas|/|cmd| as B.  It bounds the loop gain from FOUR quantities
   that are independent of that degenerate ratio:

     (1) openpilot's slew cap, 123 ct/frame -- MEASURED on native sendcan samples, never exceeded.
         This HARD-CAPS the 27.5 Hz amplitude openpilot can physically emit, whatever it wants.
     (2) the bus->internal intake scale k = 3564/8192 = 0.4351                    [firmware]
     (3) the command-path IIR gp-0x3d3c, pole 992/1024 at a 1 kHz tick => fc 4.97 Hz, and the
         chain is exclusively serial, so |H(27.5)| = 0.181 is the WHOLE forward path  [firmware]
     (4) the plant's own gain and Q, measured at low frequency where the loop is not degenerate.

   The question then becomes concrete and answerable: **what plant gain would openpilot need at
   27.5 Hz for its own physically-maximal command to account for the observed bar oscillation?**
   If that required gain is far above what the plant plausibly has, openpilot cannot be the
   sustaining path however coherent it looks.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from v81loop_lib import (CACHE, FS_NOM, band_env, coherence, fs_run,  # noqa: E402
                         lattice, load_seg, locate, resamp, welch_cross)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NF, HOP = 256, 64
EV = (38.0, 52.0)
F0 = 27.53
K_INTAKE = 3564.0 / 8192.0
FC_IIR = 4.97
SLEW = 123.0
CEILING = 4762.0


def dd(t, *v):
    t = np.asarray(t, float)
    k = np.ones(len(t), bool)
    k[1:] = np.diff(t) > 0
    return (t[k],) + tuple(np.asarray(x, float)[k] for x in v)


def amp_at(x, fs, f0, nf=NF, hop=HOP):
    """Coherent amplitude of the f0 component: median over Welch segments of |X|*2/sum(w)."""
    w = np.hanning(nf)
    f = np.fft.rfftfreq(nf, 1 / fs)
    j = int(np.argmin(np.abs(f - f0)))
    r = np.arange(nf, dtype=float)
    out = []
    for i in range(0, len(x) - nf + 1, hop):
        s = x[i:i + nf]
        s = s - np.polyval(np.polyfit(r, s, 1), r)
        out.append(np.abs(np.fft.rfft(s * w)[j]) * 2.0 / w.sum())
    return np.array(out)


def main():
    N = np.load(CACHE / "v81loop_native_s8.npz")
    tau = lattice(*EV, FS_NOM)
    a = dd(N["a_t"], N["a_ang"])
    b = dd(N["b_t"], N["b_tq"])
    sc = dd(N["sc_t"], N["sc_v"])
    ang = resamp(tau, a[0], a[1])
    bar = resamp(tau, b[0], b[1])
    cmd = resamp(tau, sc[0], sc[1])
    d8 = load_seg(8)
    fs8 = fs_run(d8["t"])
    m8 = (d8["t"] >= EV[0]) & (d8["t"] <= EV[1])
    curv = np.asarray(d8["ct_curv"], float)[m8]

    print("=" * 100)
    print("X7.1  THE DEGENERACY, stated numerically so it cannot be quoted by accident")
    print("=" * 100)
    Ac = amp_at(cmd, FS_NOM, F0)
    Aa = amp_at(ang, FS_NOM, F0)
    Ab = amp_at(bar, FS_NOM, F0)
    print(f"  |cmd(f0)| = {np.median(Ac):8.2f} counts     |ang(f0)| = {np.median(Aa):7.4f} deg"
          f"     |bar(f0)| = {np.median(Ab):8.1f} counts   ({len(Ac)} Welch segments)")
    A_naive = np.median(Ac) / np.median(Aa)
    B_naive = np.median(Aa) / np.median(Ac)
    print(f"  A_naive = |cmd|/|ang| = {A_naive:8.2f} ct/deg")
    print(f"  B_naive = |ang|/|cmd| = {B_naive:8.6f} deg/ct")
    print(f"  A_naive * B_naive     = {A_naive * B_naive:.6f}   <-- IDENTICALLY 1. Vacuous.")
    print("  ⇒ the requested product cannot be formed this way. What follows replaces it.")

    print()
    print("=" * 100)
    print("X7.2  LEG A -- openpilot's controller gain. THIS ONE IS IDENTIFIABLE.")
    print("=" * 100)
    print("  The controller is a deterministic map from its measurement to its command, so the")
    print("  amplitude ratio is its gain regardless of what drives the measurement.")
    Acv = amp_at(np.nan_to_num(curv), fs8, F0)
    lo, hi = np.percentile(Ac / Aa, [2.5, 97.5])
    print(f"  A(angle)     = {np.median(Ac / Aa):8.2f} counts per deg    "
          f"[per-segment IQR {np.percentile(Ac / Aa, 25):.1f}-{np.percentile(Ac / Aa, 75):.1f}]")
    print(f"  A(curvature) = {np.median(Ac) / np.median(Acv):8.3g} counts per (1/m)")

    print()
    print("=" * 100)
    print("X7.3  THE HARD CEILING ON OPENPILOT'S AUTHORITY AT 27.5 Hz")
    print("=" * 100)
    tri_pp = SLEW * (FS_NOM / F0) / 2.0
    tri_amp = tri_pp / 2.0
    tri_fund = (8 / np.pi ** 2) * tri_amp
    print(f"  (1) slew cap {SLEW:.0f} ct/frame, measured, never exceeded. At {F0} Hz the most")
    print(f"      extreme waveform is a triangle: pk-pk {tri_pp:.1f}, amplitude {tri_amp:.1f},")
    print(f"      whose FUNDAMENTAL is (8/pi^2)*amp = {tri_fund:.1f} counts.")
    print(f"      measured |cmd(f0)| = {np.median(Ac):.1f} counts "
          f"({100 * np.median(Ac) / tri_fund:.0f}% of that ceiling)")
    hiir = 1.0 / np.sqrt(1 + (F0 / FC_IIR) ** 2)
    print(f"  (2) bus->internal intake scale k = {K_INTAKE:.4f}")
    print(f"  (3) command-path IIR fc {FC_IIR} Hz, exclusively serial: |H({F0})| = {hiir:.4f}")
    reach_now = np.median(Ac) * K_INTAKE * hiir
    reach_max = tri_fund * K_INTAKE * hiir
    print(f"  ⇒ internal motor-command amplitude at {F0} Hz:")
    print(f"      as actually commanded : {reach_now:6.2f} counts "
          f"= {100 * reach_now / CEILING:.3f}% of the {CEILING:.0f} governor ceiling")
    print(f"      at openpilot's ABSOLUTE MAXIMUM: {reach_max:6.2f} counts "
          f"= {100 * reach_max / CEILING:.3f}% of ceiling")

    print()
    print("=" * 100)
    print("X7.4  WHAT PLANT GAIN WOULD OPENPILOT NEED TO ACCOUNT FOR THE OBSERVED OSCILLATION?")
    print("=" * 100)
    # low-frequency plant gain, from the same event, where the IIR is nearly transparent
    lof = 2.5
    Acl = np.median(amp_at(cmd, FS_NOM, lof))
    Abl = np.median(amp_at(bar, FS_NOM, lof))
    hl = 1.0 / np.sqrt(1 + (lof / FC_IIR) ** 2)
    g_lo = Abl / (Acl * K_INTAKE * hl)
    print(f"  at {lof} Hz: |cmd| {Acl:7.1f} ct -> internal {Acl * K_INTAKE * hl:7.1f} ct;"
          f"  |bar| {Abl:7.1f} ct  ⇒ plant gain {g_lo:6.3f} bar-ct per motor-ct")
    need = np.median(Ab) / reach_now
    need_max = np.median(Ab) / reach_max
    print(f"  at {F0} Hz: |bar| {np.median(Ab):7.1f} ct observed")
    print(f"      required plant gain, as commanded      : {need:8.1f}  "
          f"= {need / g_lo:6.1f}x the {lof} Hz plant gain")
    print(f"      required plant gain, at openpilot's MAX: {need_max:8.1f}  "
          f"= {need_max / g_lo:6.1f}x the {lof} Hz plant gain")
    for Q in (13.6, 23.7, 40.0):
        print(f"      a Q={Q:4.1f} resonance supplies {Q:5.1f}x  ⇒ openpilot could drive "
              f"{reach_max * g_lo * Q:7.1f} bar-ct = "
              f"{100 * reach_max * g_lo * Q / np.median(Ab):5.1f}% of what is observed")
    print("  🛑 Q=23.7 is r67-analyst's measured value for this line; 13.6 is the kit's V44")
    print("     physical-resonance figure; 40 is a deliberately generous upper case.")

    print()
    print("=" * 100)
    print("X7.5  IS THE SLEW CAP BINDING *BECAUSE OF* THE OSCILLATION?")
    print("=" * 100)
    t, v = dd(N["sc_t"], N["sc_v"])
    ev = (t >= EV[0]) & (t <= EV[1])
    fsn = 1.0 / np.median(np.diff(t))
    x = v[ev]
    X = np.fft.rfft(x - x.mean())
    fq = np.fft.rfftfreq(len(x), 1 / fsn)
    for lab, band in (("as transmitted", None), ("with 20-35 Hz removed", (20, 35)),
                      ("with >12 Hz removed", (12, 1e9))):
        Y = X.copy()
        if band:
            Y[(fq >= band[0]) & (fq <= band[1])] = 0
        y = np.fft.irfft(Y, n=len(x)) + x.mean()
        st = np.abs(np.diff(y))
        print(f"  {lab:>24}: max step {st.max():6.1f}  p95 {np.percentile(st, 95):6.1f}  "
              f"% at cap {100 * np.mean(st >= 0.99 * SLEW):6.2f}")
    print("  If removing the 27.5 Hz band drops the cap duty to ~0, the slew limiting is a")
    print("  CONSEQUENCE of the oscillation, not an independent driver of it.")

    print()
    print("=" * 100)
    print("X7.6  HARMONIC STRUCTURE -- relay vs rate-limiter vs pure sinusoid")
    print("=" * 100)
    print(f"  {'channel':>10} {'f0':>9} {'2f0->' + f'{abs(100 - 2 * F0):.1f}':>14} "
          f"{'3f0->' + f'{abs(3 * F0 - 100):.1f}':>14}   [both fold below Nyquist]")
    for nm, x, fs in (("bar", bar, FS_NOM), ("angle", ang, FS_NOM), ("cmd", cmd, FS_NOM)):
        a0 = np.median(amp_at(np.asarray(x, float), fs, F0))
        a2 = np.median(amp_at(np.asarray(x, float), fs, abs(100 - 2 * F0)))
        a3 = np.median(amp_at(np.asarray(x, float), fs, abs(3 * F0 - 100)))
        print(f"  {nm:>10} {a0:>9.2f} {a2:>14.3f} {a3:>14.3f}   "
              f"(2f/f {a2 / a0:.4f}, 3f/f {a3 / a0:.4f})")
    print("  An ideal relay gives 3f/f = 1/3 = 0.333 and 2f/f = 0. A rate-limited sinusoid gives")
    print("  a triangle: 3f/f = 1/9 = 0.111. A pure sinusoid gives both ~0.")


if __name__ == "__main__":
    main()
