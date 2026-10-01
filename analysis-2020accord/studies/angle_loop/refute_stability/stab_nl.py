# -*- coding: utf-8 -*-
"""REFUTER: independent NONLINEAR time-domain check of the corner cases the linear scans flagged.
Own integer lane (C0 edits + cave) written from lane_mirror_v295 semantics + the design's cave listing; own plant
integrator (Karnopp friction, 10 kHz substeps); 0.1 deg angle quantisation and 1/8 deg/s rate quantisation; 100 Hz
slot-4 hold; 2 ms transport; hands-off fade 254.  Not the design's harness."""
import sys, math
import numpy as np
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import stab_lin as S
import v294_plant as VP

PCL, SCL, OCL, OA, OB, FWD = 15360, 15360, 3072, 992, 507, 5346
KP, KI, KD, ICL, DCL, DB = 450, 199, 16, 4096, 10240, 0


def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def run(J, b, k, Fc, Fs, v, sp_fn, secs=6.0, tau=2, sat=1e9, d_noise=None, seed=0):
    G = S.G_of_v(v)
    n = int(secs * 1000)
    sub = 10; h = 1e-3 / sub
    th, om, stuck = 0.0, 0.0, True
    th_h, x_h = 0, 0                      # held gp-0x6a00 counts, held gp-0x6a56 counts
    s_old, I8, olag = 0, 0, 0
    ubuf = [0.0] * (tau + 1)
    icl = (ICL << 10) >> 3
    rng = np.random.default_rng(seed)
    TH = np.zeros(n); T_out = np.zeros(n); OM = np.zeros(n)
    for t in range(n):
        th_sp = sp_fn(t * 1e-3)
        raw = -int(round(th_sp * 10))
        sp = clamp(-(raw << 2), -0x4000, 0x4000)           # 0xE4 handler -> gp-0x69ae
        # ---- lane (slot 0) ----
        x = th_h
        s_new = (8192 * x) >> 10                             # a = 0
        r26 = clamp(s_old + s_new, -65535, 65535)            # add (E2), C = 65535
        s_old = s_new
        E = (sp << 2) - r26                                  # cave: displaced shl 2 ; sub
        E = s32(E * G) >> 8                                  # cave: E' = E*G >> 8
        e5 = E >> 5
        exc = e5 - DB if e5 > DB else (e5 + DB if e5 < -DB else 0)
        I = clamp((I8 >> 3) + (s32(exc * KI) >> 3), -icl, icl)
        P = clamp(s32(E * KP) >> 8, -PCL, PCL)
        D = clamp(s32(-KD * x_h) >> 3, -DCL, DCL)
        Ssum = (I >> 7) + P + D
        Sf = s32(Ssum * 254) >> 8
        Sc = clamp(Sf, -SCL, SCL)
        I8 = I << 3
        t1 = s32(Sc * OB) >> 10
        t2 = s32(OA * olag) >> 10
        o_new = t2 + t1
        y = (olag + o_new) >> 5
        olag = o_new
        yr = (y * 0x8000) >> 15
        r11 = s32(yr * (-FWD)) >> 15                         # pol -1
        T = clamp(r11, -OCL, OCL)
        u_cmd = -T                                           # plant input, + left
        ubuf.append(u_cmd)
        u = ubuf.pop(0) if tau > 0 else u_cmd
        # ---- slot 4 (after the PID on its tick) ----
        if t % 10 == 4:
            th_h = int(math.floor(th * 10.0))
            x_h = int(round(8.0 * om))
        # ---- plant, Karnopp ----
        dist = d_noise[t] if d_noise is not None else 0.0
        for _ in range(sub):
            spring = k * sat * math.tanh(th / sat)
            F = u + dist - spring
            if stuck:
                if abs(F) > Fs:
                    stuck = False
                    om = 0.0
                else:
                    om = 0.0
                    continue
            acc = (F - b * om - Fc * math.copysign(1.0, om if om != 0 else F)) / J
            om_new = om + acc * h
            if om != 0 and (om_new == 0 or (om_new > 0) != (om > 0)):
                # velocity reversal -> try to stick
                if abs(F) <= Fs:
                    om = 0.0; stuck = True
                    continue
            om = om_new
            th += om * h
        TH[t] = th; T_out[t] = T; OM[t] = om
    return TH, T_out, OM


def ring_metrics(TH, T, t0, sp_final, fs=1000.0):
    seg = TH[int(t0 * fs):]
    err = seg - sp_final
    over = float(np.max(err)) if sp_final > 0 else float(-np.min(err))
    # count zero crossings of the error after the first crossing within 3 s
    z = np.where(np.diff(np.sign(err[: int(3 * fs)])) != 0)[0]
    return over, len(z)


def band_rms(sig, lo, hi, fs=1000.0):
    X = np.fft.rfft(sig - np.mean(sig))
    f = np.fft.rfftfreq(len(sig), 1 / fs)
    m = (f >= lo) & (f <= hi)
    return float(np.sqrt(2 * np.sum(np.abs(X[m]) ** 2)) / len(sig))


if __name__ == "__main__":
    fam = VP.family()
    print("A. 2 deg setpoint step at 1 s, held; v = 12 m/s. overshoot (deg), error zero-crossings in 3 s, T rms 1.6-3 Hz "
          "and 4-6 Hz after the step")
    for nm, mk in (("nominal", lambda v: fam["nominal"].at(v)),
                   ("J_hi", lambda v: fam["J_hi"].at(v)),
                   ("b_lo", lambda v: fam["b_lo"].at(v))):
        for v in (11.9, 12.5):
            p = mk(v)
            for bs, lab in ((1.0, ""), ((1 / 1.8), " *b/1.8")):
                if nm != "J_hi" and bs != 1.0:
                    continue
                TH, T, OM = run(p.J, p.b * bs, p.k, p.Fc, p.Fs, v, lambda t: 0.0 if t < 1.0 else 2.0, secs=6.0, sat=p.sat)
                over, zc = ring_metrics(TH, T, 1.0, 2.0)
                print(f"   {nm+lab:12s} v {v:5.1f}: overshoot {over:5.2f} deg, crossings {zc:3d}, "
                      f"T 1.6-3 Hz {band_rms(T[1000:], 1.6, 3.0):6.1f}, 4-6 Hz {band_rms(T[1000:], 4.0, 6.0):6.1f}, "
                      f"peak |T| {np.max(np.abs(T[1000:])):.0f}")
    print("\nB. highway, motor-side damping at the 'mechanical' value (b = 5, J 0.2, nominal k and friction): 0.3 deg "
          "step at 1 s; does a 4-6 Hz oscillation grow / persist?")
    for v in (19.0, 26.0, 30.0):
        p = fam["nominal"].at(v)
        for b in (p.b, p.b / 1.8, 9.5, 7.0, 5.0):
            TH, T, OM = run(p.J, b, p.k, p.Fc, p.Fs, v, lambda t: 0.0 if t < 1.0 else 0.3, secs=8.0, sat=p.sat)
            late = T[5000:]
            print(f"   v {v:4.1f} b {b:6.2f}: T rms 4-6 Hz in 4-8 s {band_rms(late, 4.0, 6.0):7.1f} | peak |T| 4-8 s "
                  f"{np.max(np.abs(late)):6.0f} | wheel p-p 4-8 s {np.ptp(TH[5000:]):.3f} deg")
