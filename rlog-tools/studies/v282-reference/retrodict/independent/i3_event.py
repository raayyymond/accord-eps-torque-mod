# -*- coding: utf-8 -*-
"""i3 -- characterise ONE oscillation event in detail, from the log.

Prints the exact line frequency (long FFT + zero-padded peak), the amplitude envelope cycle by cycle,
the driving conditions, and the phase of the command relative to the measured angle at that line --
which says whether the command is DRIVING the oscillation (in phase with rate, i.e. negative damping)
or merely following it.

ANALYSIS ONLY.  python i3_event.py <route> <t0> <t1>
"""
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V  # noqa: E402

FS = 100.0


def main(route, t0, t1):
    S = V.load(route)
    t = S["t"]
    a = int(np.searchsorted(t, t0))
    b = int(np.searchsorted(t, t1))
    sl = slice(a, b)
    n = b - a
    print(f"=== {route}  t {t[a]:.2f} - {t[b-1]:.2f} s  ({n/FS:.2f} s, {n} samples) ===")
    print(f"    engaged {S['active'][sl].mean()*100:.0f} %   pressed {S['pressed'][sl].mean()*100:.0f} %   "
          f"saturated {S['sat'][sl].mean()*100:.0f} %")
    print(f"    v  {np.median(S['v'][sl]):5.1f} m/s  ({S['v'][sl].min():.1f}-{S['v'][sl].max():.1f})   "
          f"sa {np.median(S['sa'][sl]):+7.1f} deg  ({S['sa'][sl].min():+.1f}..{S['sa'][sl].max():+.1f})")
    print(f"    setpoint (la_des) {np.nanmedian(S['setpoint'][sl]):+6.2f}  la_act {np.nanmedian(S['la_act'][sl]):+6.2f} m/s^2   "
          f"|out| med {np.nanmedian(np.abs(S['out'][sl])):.3f}")

    sa = signal.detrend(np.nan_to_num(S["sa"][sl]))
    sr = signal.detrend(np.nan_to_num(S["sr"][sl]))
    u = signal.detrend(np.nan_to_num(S["out"][sl]))
    e = signal.detrend(np.nan_to_num(S["p"][sl]))     # p is kp * error_with_lsf
    w = signal.get_window("hann", n)
    NFFT = 1 << (int(np.ceil(np.log2(n))) + 4)
    f = np.fft.rfftfreq(NFFT, 1.0 / FS)
    SA = np.fft.rfft(sa * w, NFFT)
    SR = np.fft.rfft(sr * w, NFFT)
    U = np.fft.rfft(u * w, NFFT)
    E = np.fft.rfft(e * w, NFFT)
    band = (f >= 1.2) & (f <= 6.0)
    k = int(np.where(band)[0][0]) + int(np.argmax(np.abs(SA[band])))
    fpk = f[k]
    amp = 2.0 * np.abs(SA[k]) / np.sum(w)
    print(f"\n    LINE  f = {fpk:.3f} Hz   angle amplitude = {amp:.3f} deg (peak), "
          f"{amp*2:.2f} deg peak-to-peak")
    print(f"          rate amplitude = {2*np.abs(SR[k])/np.sum(w):.2f} deg/s "
          f"(2*pi*f*A would be {2*np.pi*fpk*amp:.2f})")
    ph_u_sa = np.degrees(np.angle(U[k] / SA[k]))
    ph_u_sr = np.degrees(np.angle(U[k] / SR[k]))
    ph_e_sa = np.degrees(np.angle(E[k] / SA[k]))
    print(f"          phase(command u  vs angle) {ph_u_sa:+7.1f} deg    vs rate {ph_u_sr:+7.1f} deg")
    print(f"          phase(pid p      vs angle) {ph_e_sa:+7.1f} deg")
    print(f"          |u| at line = {2*np.abs(U[k])/np.sum(w):.4f} output units")
    print("          (u in phase with RATE = pumping; 180 deg from rate = damping)")

    # cycle-by-cycle envelope via a narrow bandpass + Hilbert
    sos = signal.butter(4, [max(fpk - 0.6, 0.3), fpk + 0.6], btype="band", fs=FS, output="sos")
    env = np.abs(signal.hilbert(signal.sosfiltfilt(sos, sa)))
    step = int(round(FS / fpk))
    print("\n    envelope (deg, one point per cycle):")
    vals = [f"{env[i]:.2f}" for i in range(0, len(env), step)]
    for j in range(0, len(vals), 16):
        print("      " + " ".join(vals[j:j + 16]))
    # growth rate over the rising part
    lg = np.log(np.maximum(env, 1e-6))
    kk = int(np.argmax(env))
    if kk > int(2 * FS):
        tt = np.arange(kk) / FS
        sl2 = slice(max(0, kk - int(4 * FS)), kk)
        A = np.polyfit(np.arange(sl2.start, sl2.stop) / FS, lg[sl2], 1)
        zeta = -A[0] / (2 * np.pi * fpk)
        print(f"\n    rise: d(ln A)/dt = {A[0]:+.3f} /s over the { (sl2.stop-sl2.start)/FS:.1f} s before the peak"
              f"  => effective zeta = {zeta:+.4f}")
    sl3 = slice(kk, min(len(env), kk + int(4 * FS)))
    if sl3.stop - sl3.start > int(2 * FS):
        A = np.polyfit(np.arange(sl3.start, sl3.stop) / FS, lg[sl3], 1)
        print(f"    decay: d(ln A)/dt = {A[0]:+.3f} /s after the peak  "
              f"=> effective zeta = {-A[0]/(2*np.pi*fpk):+.4f}")
    del S


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]))
