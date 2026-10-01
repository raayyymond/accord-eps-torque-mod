# -*- coding: utf-8 -*-
"""REFUTER: (1) self-consistent J-profile rows (J 0.3 / 1.3 refits) x b bias; (2) the fork outer-loop stand-in on
the corner members; (3) two-mass with the lumped (vehicle) b removed from the 13 Hz mode; (4) V289-like reference at
15-17 Hz."""
import sys, math
import numpy as np
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import stab_lin as S
import stab_hf as H
import v294_plant as VP

fam = VP.family()
TS = S.TS


def sec(t):
    print("\n" + "=" * 110 + "\n" + t + "\n" + "=" * 110)


# ---------------------------------------------------------------- 1. J-profile rows
sec("1. SELF-CONSISTENT J-PROFILE ROWS (p5c refits at fixed J) with and without the G3a b-bias correction (/1.8 at >=10 m/s)")
import os
rows = VP._profile_rows(os.path.join(os.path.dirname(VP.__file__), "_scratch", "p5c.json"))
print("  profile J values available:", sorted(rows))
for Jrow in sorted(rows):
    b0, k0, F0, Fs0 = rows[Jrow]
    mem = VP.PlantFamilyMember(f"J{Jrow}", J=np.full(5, Jrow), b=b0, k=k0, Fc=F0, Fs=Fs0, tau_ms=2)
    for bfix in (False, True):
        res = []
        for v in np.arange(3.0, 35.01, 0.5):
            p = mem.at(v)
            bs = (1 / 1.8 if v >= 10 else 0.7) if bfix else 1.0
            pl = S.rigid(p.J, p.b * bs, p.k)
            c = S.Ctl(v, d=2)
            mg = S.margins(c, pl, npts=3000)
            res.append((mg['pm'], v, mg['fc']))
        res.sort()
        sub30 = [r[1] for r in res if r[0] < 30]; sub45 = [r[1] for r in res if r[0] < 45]
        print(f"  J {Jrow:4.2f} {'b/1.8' if bfix else 'b fit'}: min PM {res[0][0]:6.1f} at {res[0][1]:5.1f} m/s (fc {res[0][2]:.2f}) "
              f"| PM<45 at {len(sub45)} speeds [{min(sub45) if sub45 else '-'}..{max(sub45) if sub45 else '-'}] "
              f"| PM<30 at {len(sub30)} [{min(sub30) if sub30 else '-'}..{max(sub30) if sub30 else '-'}]")

# ---------------------------------------------------------------- 2. outer loop stand-in
sec("2. FORK OUTER-LOOP STAND-IN  L_o = T_ref * e^{-0.06 s} / (tau_o s)  (100 Hz fork, 60 ms round trip): PM / GM / peak |T_ref|")


def Tref(ctl, plant, f):
    L, KCth, KCw, Pt, Pw = S.frf(ctl, plant, f)
    z = np.exp(1j * 2 * np.pi * f * TS); zi = 1 / z
    Hout = (S.OB / 1024) * (1 + zi) / (32 * (1 - (S.OA / 1024) * zi))
    K = ctl.fade * S.FWD * Hout * zi ** ctl.d
    g = ctl.G / 256
    PI = ctl.kp / 256 + (ctl.ki / 32768) / (1 - zi)
    Cref = K * g * PI * 160
    return Cref * Pt / (1 + L)


f = np.logspace(-2, 1.7, 4000)
cases = [("nominal", lambda v: S.member_at(fam, "nominal", v)[1]),
         ("b_lo", lambda v: S.member_at(fam, "b_lo", v)[1]),
         ("J_hi", lambda v: S.member_at(fam, "J_hi", v)[1]),
         ("b_lo*J_hi", lambda v: S.rigid(fam["J_hi"].at(v).J, fam["J_hi"].at(v).b * (1 / 1.8 if v >= 10 else 0.7), fam["J_hi"].at(v).k))]
for nm, mk in cases:
    for v in (3, 8, 12, 19, 26):
        pl = mk(v); c = S.Ctl(v, d=2)
        Tr = Tref(c, pl, f)
        out = [f"{nm:10s} v {v:4g}: |Tref| peak {np.max(np.abs(Tr)):.2f} at {f[np.argmax(np.abs(Tr))]:.2f} Hz"]
        for tau_o in (0.3, 0.5, 1.0):
            Lo = Tr * np.exp(-1j * 2 * np.pi * f * 0.06) / (tau_o * 1j * 2 * np.pi * f)
            mag = np.abs(Lo); ph = np.unwrap(np.angle(Lo)) * 180 / np.pi
            i = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0]
            pm = (ph[i[0]] + 180) if len(i) else float('nan')
            j = np.where((ph[:-1] > -180) & (ph[1:] <= -180))[0]
            gm = min([-20 * math.log10(mag[k]) for k in j], default=float('inf'))
            out.append(f"tau_o {tau_o}: PM {pm:5.1f} GM {gm:5.1f} dB")
        print("  " + " | ".join(out))

# ---------------------------------------------------------------- 3. two-mass with the lumped b off the mode
sec("3. TWO-MASS (fz 13/16 Hz) at SPEED with the motor-side b = the low-speed (mechanical) value 5.0 instead of the lumped "
    "20-26: least-damped HF pole, C0 vs V294/V295")
for v in (19, 26, 30):
    p = fam["nominal"].at(v)
    for fz in (13.0, 16.0):
        for r2 in (0.1, 0.2, 0.3, 0.5):
            for zw in (0.01, 0.02, 0.05):
                pl = S.two_mass(p.J, 5.0, p.k, r2, fz, zw)
                res = {}
                for c in (S.Ctl(v, d=2), H.V294, H.V295):
                    nm = c.name if isinstance(c, H.Rate) else "C0"
                    rho, hf = H.exact_any(c, pl)
                    res[nm] = (rho, hf[0] if hf else (float('nan'), float('nan')))
                print(f"  v {v:3g} fz {fz:4g} r2 {r2:.1f} zw {zw:.2f}: C0 {res['C0'][1][0]:5.1f} Hz z{res['C0'][1][1]:+.4f} rho {res['C0'][0]:.4f}"
                      f" | V294 {res['V294'][1][0]:5.1f} Hz z{res['V294'][1][1]:+.4f} | V295 {res['V295'][1][0]:5.1f} Hz z{res['V295'][1][1]:+.4f}")

# ---------------------------------------------------------------- 4. V289-like reference
sec("4. V289-like reference (V282 + fb pole 25 Hz DC-held + 20.04 Hz Q3 notch on the loop output): Re(T/omega) 10-20 Hz")
def tpr_v289(f):
    z = np.exp(1j * 2 * np.pi * f * TS); zi = 1 / z
    hold = sum(zi ** a for a in range(1, 11)) / 10
    Hout = (S.OB / 1024) * (1 + zi) / (32 * (1 - (S.OA / 1024) * zi))
    K = S.FADE * S.FWD * Hout * zi ** 2
    a = 1024 * math.exp(-2 * math.pi * 25 * TS); b = 30.89 * (1024 - a) / 2
    R = (b / 1024) * (1 + zi) / (1 - (a / 1024) * zi)
    g = 248 / 256 + (128 / 8) * (1 - zi)
    w0 = 2 * math.pi * 20.04 * TS; Q = 3.0; al = math.sin(w0) / (2 * Q)
    num = (1 - 2 * math.cos(w0) * zi + zi ** 2); den = (1 + al) - 2 * math.cos(w0) * zi + (1 - al) * zi ** 2
    N = num / den * (1 + al)
    return K * g * R * 8 * hold * N
fr = (10, 13, 15, 16, 17, 20)
print("  V289~ " + "  ".join(f"{q}Hz {tpr_v289(q).real:+.2f}|{abs(tpr_v289(q)):.2f}" for q in fr))
print("  V282  " + "  ".join(f"{q}Hz {H.torque_per_rate(H.V282, q).real:+.2f}|{abs(H.torque_per_rate(H.V282, q)):.2f}" for q in fr))
for v in (12.5, 19, 26):
    c = S.Ctl(v, d=2)
    print(f"  C0@{v:<4g}" + "  ".join(f"{q}Hz {H.torque_per_rate(c, q).real:+.2f}|{abs(H.torque_per_rate(c, q)):.2f}" for q in fr))
