# -*- coding: utf-8 -*-
"""d11 -- run the EXACT proposed fork code and check it, before it is offered.

Copies get_honda_accord_id_probe and the caller's ramp/reset logic verbatim from the patch, then:
  V1  off      AccordIdProbe = 0 returns exactly 0.0 on every frame (byte-for-byte the current path)
  V2  periodic x[k] == x[k+1024] to machine precision; the analysis sees only the four tone bins
  V3  peak     the peak equals the toggle value, and the crest factor is what was claimed
  V4  slew     max |x[k]-x[k-1]| as a fraction of the Honda 0.03/frame limiter
  V5  engage   the value on the first armed frame, and the largest single-frame step at engage/disengage
  V6  reset    a disengage-reengage restarts the phase at zero
  V7  speed    the arm fades 12 -> 15 m/s and is exactly 0 below 12
  V8  skirt    a tone on bin k puts exactly half its amplitude on k+-1 (control C1)
  V9  empty    the inter-tone bins carry exactly zero probe power (control C2)
  V10 estimator  a synthetic closed loop with a KNOWN L: does 1+L = S_WW/S_W,u_p recover it?
"""
import math
import sys
from pathlib import Path

import numpy as np
from scipy import signal as sg

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------- verbatim from the patch
HONDA_ACCORD_ID_PROBE_PERIOD = 1024
HONDA_ACCORD_ID_PROBE_PEAK = 0.017546
HONDA_ACCORD_ID_PROBE_V_BP = [12.0, 15.0]
HONDA_ACCORD_ID_PROBE_RAMP_S = 0.30
HONDA_ACCORD_ID_PROBE_TONES = (
    (7, 0.009926, +0.804261),
    (10, 0.004997, +1.695385),
    (13, 0.004823, -1.778602),
    (16, 0.006338, +2.560431),
)


def get_honda_accord_id_probe(peak, frame, dt, v_ego=0.0):
    if peak <= 0.0:
        return 0.0
    arm = float(np.interp(v_ego, HONDA_ACCORD_ID_PROBE_V_BP, [0.0, 1.0]))
    if arm <= 0.0:
        return 0.0
    k = int(frame) % HONDA_ACCORD_ID_PROBE_PERIOD
    x = 0.0
    for b, a, ph in HONDA_ACCORD_ID_PROBE_TONES:
        x += a * math.cos(2.0 * math.pi * b * k / HONDA_ACCORD_ID_PROBE_PERIOD + ph)
    return arm * x * float(peak) / HONDA_ACCORD_ID_PROBE_PEAK


class Caller:
    """The caller's ramp / counter / reset logic, verbatim."""

    def __init__(self, dt=0.01):
        self.dt = dt
        self.frame = 0
        self.ramp = 0.0

    def engage_reset(self):
        self.frame = 0
        self.ramp = 0.0

    def step(self, peak, on, v):
        rs = self.dt / max(HONDA_ACCORD_ID_PROBE_RAMP_S, self.dt)
        self.ramp = float(np.clip(self.ramp + (rs if on else -rs), 0.0, 1.0))
        if self.ramp > 0.0:
            self.frame += 1
            return self.ramp * get_honda_accord_id_probe(peak, self.frame, self.dt, v)
        self.frame = 0
        return 0.0


PEAK = 0.017546
LSB = 1.0 / 4089.0
NPS, G = 1024, 256.0
ok = lambda b: "PASS" if b else "**FAIL**"

if __name__ == "__main__":
    print("VERIFICATION of the proposed code, run as written\n")

    # V1 -- off
    c = Caller()
    z = [c.step(0.0, True, 25.0) for _ in range(3000)]
    print(f"V1  off          max|x| with AccordIdProbe=0 : {max(map(abs, z)):.3e}   {ok(max(map(abs,z))==0.0)}")

    # V2/V3/V4 -- steady state
    x = np.array([get_honda_accord_id_probe(PEAK, k, 0.01, 25.0) for k in range(4096)])
    per = float(np.max(np.abs(x[:1024] - x[1024:2048])))
    pk, rms = float(np.max(np.abs(x))), float(np.sqrt(np.mean(x[:1024] ** 2)))
    slew = float(np.max(np.abs(np.diff(x))))
    print(f"V2  periodic     max|x[k]-x[k+1024]|          : {per:.3e}   {ok(per < 1e-15)}")
    print(f"V3  peak         {pk:.6f} (toggle {PEAK:.6f}, {pk/LSB:.1f} counts) crest {pk/rms:.3f}   "
          f"{ok(abs(pk-PEAK) < 1e-6)}")
    print(f"V4  slew         {slew:.6f}/frame = {slew/0.03*100:.1f} % of the Honda 0.03 limiter   "
          f"{ok(slew < 0.03*0.10)}")

    # V5/V6 -- engage behaviour and reset
    c = Caller()
    seq = [c.step(PEAK, True, 25.0) for _ in range(200)]
    print(f"V5  engage       first armed frame {seq[0]:+.6f} | largest step in the first 0.5 s "
          f"{max(abs(b-a) for a, b in zip(seq, seq[1:])):.6f} ({max(abs(b-a) for a,b in zip(seq,seq[1:]))/0.03*100:.1f} % of the limiter)   "
          f"{ok(abs(seq[0]) < 2e-4)}")
    for _ in range(200):
        c.step(PEAK, False, 25.0)          # disengage: ramp down, counter zeroed
    f_after = c.frame
    seq2 = [c.step(PEAK, True, 25.0) for _ in range(5)]
    print(f"V6  reset        frame after disengage {f_after} | re-engage first values "
          f"{' '.join(f'{q:+.2e}' for q in seq2)}   {ok(f_after == 0)}")

    # V7 -- speed arming
    row = [(v, get_honda_accord_id_probe(PEAK, 250, 0.01, v)) for v in (5, 11.9, 12.0, 13.5, 15.0, 30.0)]
    full = row[-1][1]
    print("V7  speed arm    " + "  ".join(f"{v:.1f}m/s {q/full if full else 0:+.2f}" for v, q in row)
          + f"   {ok(row[0][1] == 0.0 and row[1][1] == 0.0 and abs(row[3][1]/full - 0.5) < 0.02)}")

    # V8/V9 -- the two free controls
    w = sg.get_window("hann", NPS)
    X = np.abs(np.fft.rfft(sg.detrend(x[:NPS]) * w))
    tb = [t[0] for t in HONDA_ACCORD_ID_PROBE_TONES]
    print("V8  skirt        " + "  ".join(
        f"bin{b}: |X[k+-1]|/|X[k]| = {0.5*(X[b-1]+X[b+1])/X[b]:.4f}" for b in tb)
        + f"   {ok(all(abs(0.5*(X[b-1]+X[b+1])/X[b] - 0.5) < 0.01 for b in tb))}")
    empty = [j for j in range(3, 40) if j not in tb and all(abs(j - b) > 1 for b in tb)]
    lk = max(X[j] for j in empty) / X[min(tb, key=lambda b: X[b])]
    print(f"V9  empty bins   detrend leakage into the {len(empty)} inter-tone bins = {lk:.2e} of the "
          f"smallest tone ({20*np.log10(lk):.0f} dB); road power there is ~{0.361/0.0089:.0f}x it   {ok(lk < 0.02)}")

    # V10 -- does the estimator recover a KNOWN loop?
    print("\nV10 ESTIMATOR POSITIVE CONTROL: a synthetic closed loop with a known L, driven by the real")
    print("    probe plus coloured road noise.  1 + L must come back as S_WW / S_W,u_p.")
    rng = np.random.default_rng(1)
    N = 1024 * 80
    dt = 0.01
    # plant: gain 4, 55 ms delay, 5.05 Hz pole ; controller: Kp 1.0 / LAF 14 with a 1.3 Hz lag
    D = 6
    bp, ap = sg.butter(1, 5.05, fs=100, btype="low")
    bc, ac = sg.butter(1, 1.3, fs=100, btype="low")
    Kplant, Kctl = 4.0, 1.0 / 14.0 * 6.0
    probe = np.array([get_honda_accord_id_probe(PEAK, k, dt, 25.0) for k in range(N)])
    road = sg.sosfilt(sg.butter(2, 1.0, fs=100, btype="low", output="sos"), rng.standard_normal(N)) * 0.5
    m = np.zeros(N); uc = np.zeros(N); up = np.zeros(N)
    mem_p = sg.lfilter_zi(bp, ap) * 0.0
    mem_c = sg.lfilter_zi(bc, ac) * 0.0
    upd = np.zeros(N)
    for k in range(1, N):
        up[k] = uc[k - 1] + probe[k]
        upd[k] = up[k - D] if k >= D else 0.0
        yk, mem_p = sg.lfilter(bp, ap, [Kplant * upd[k]], zi=mem_p)
        m[k] = yk[0] + road[k]
        ck, mem_c = sg.lfilter(bc, ac, [-Kctl * m[k]], zi=mem_c)
        uc[k] = ck[0]
    wnd = sg.get_window("hann", NPS)
    f = np.fft.rfftfreq(NPS, dt)
    Sww = np.zeros(NPS // 2 + 1, complex); Swu = np.zeros(NPS // 2 + 1, complex); nn = 0
    for s in range(NPS, N - NPS, NPS // 2):
        Wf = np.fft.rfft(sg.detrend(probe[s:s + NPS]) * wnd)
        Uf = np.fft.rfft(sg.detrend(up[s:s + NPS]) * wnd)
        Sww += np.conj(Wf) * Wf; Swu += np.conj(Wf) * Uf; nn += 1
    # truth: L = Kctl*C(z) * Kplant*P(z)*z^-D
    zz = np.exp(-2j * np.pi * f * dt)
    Cz = Kctl * np.polyval(bc[::-1], zz) / np.polyval(ac[::-1], zz)
    Pz = Kplant * np.polyval(bp[::-1], zz) / np.polyval(ap[::-1], zz) * zz ** D
    Ltrue = Cz * Pz * zz          # the extra z^-1 of the caller's uc[k-1] hold
    print(f"    {'f Hz':>7s} {'|1+L| true':>11s} {'|1+L| meas':>11s} {'err %':>7s} | "
          f"{'arg true':>9s} {'arg meas':>9s} {'err deg':>8s}")
    for b in tb:
        est = Sww[b] / Swu[b]
        tr = 1 + Ltrue[b]
        print(f"    {f[b]:7.3f} {abs(tr):11.4f} {abs(est):11.4f} "
              f"{(abs(est)/abs(tr)-1)*100:+7.2f} | {np.degrees(np.angle(tr)):9.1f} "
              f"{np.degrees(np.angle(est)):9.1f} {np.degrees(np.angle(est/tr)):+8.2f}")
