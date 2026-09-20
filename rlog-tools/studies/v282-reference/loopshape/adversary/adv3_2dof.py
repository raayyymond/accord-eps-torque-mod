"""ADVERSARY 3 -- the architecture attack, and a consistent (IV) plant estimate where one is available.

The fork is a TWO-DEGREE-OF-FREEDOM controller:  U = C_fb(Z-Y) + C_ff(Z).  Then
    T = Y/Z = G(C_fb+C_ff)/(1+G C_fb)      and      1 - T = (1 - G C_ff)/(1 + G C_fb)
so  T/(1-T) = G(C_fb+C_ff)/(1 - G C_ff)  which is NOT the open-loop gain L = G C_fb, and (Z-Y) is NOT
the sensitivity.  Identifying L therefore needs the COMMAND, and the command node is exactly where the
closed-loop bias lives.  This script measures:
  1. how much of the in-band command is feedforward (the path no loop shaping touches),
  2. whether the feedforward is a clean instrument (coh with the setpoint) -- per family,
  3. the DIRECT plant estimate vs the IV plant estimate = the closed-loop identification bias, measured,
  4. L = C_fb * G, crossover and phase margin, where the identification is admissible.
Positive controls for 3 are run first on a synthetic closed loop with a KNOWN plant.
"""
import sys
from pathlib import Path
import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
import v282cmp as V

FS = 100.0
NPS = 4096
BANDS = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20)]
FAM = {"00000064--ce6b0b0ebb": "V282", "00000065--b9f78988bd": "V282", "0000006c--2bc842dbac": "V282",
       "00000039--f56039af87": "V282old", "0000003a--283a39a1d6": "V282old", "0000003c--927965c2b4": "V282old",
       "0000006c--68c6e94b17": "TORQ", "0000006d--05e83bb04f": "TORQ", "0000006e--6ca3e014fd": "TORQ",
       "00000075--6c8687d5bd": "TORQ", "00000076--d0b7ea7e4d": "TORQ"}


def spec(segs):
    Pxx = Pyy = Pxy = None; fr = None
    for x, y in segs:
        if len(x) < NPS: continue
        xs, ys = x - x.mean(), y - y.mean()
        f, pxx = signal.welch(xs, FS, nperseg=NPS, noverlap=NPS // 2)
        _, pyy = signal.welch(ys, FS, nperseg=NPS, noverlap=NPS // 2)
        _, pxy = signal.csd(xs, ys, FS, nperseg=NPS, noverlap=NPS // 2)
        Pxx = pxx if Pxx is None else Pxx + pxx
        Pyy = pyy if Pyy is None else Pyy + pyy
        Pxy = pxy if Pxy is None else Pxy + pxy
        fr = f
    return fr, Pxx, Pyy, Pxy


def control_iv():
    """Known plant G = 1/(tau s+1)^2 with delay, 2-DOF controller (ff = a*Z, fb = kp*(Z-Y)), output
    disturbance d correlated with nothing. Direct estimate must be biased, IV (instrument = ff) must not."""
    rng = np.random.default_rng(11)
    n = int(900 * FS); dt = 1 / FS
    tau, D, kp, a = 0.12, 6, 1.4, 0.75
    z = V.lowpass(rng.standard_normal(n), 0.8) * 2.0
    d = V.lowpass(rng.standard_normal(n), 3.0) * 0.6
    y = np.zeros(n); u = np.zeros(n); ffc = np.zeros(n); x1 = x2 = 0.0
    for i in range(1, n):
        ffc[i] = a * z[i]
        u[i] = kp * (z[i] - y[i - 1]) + ffc[i]
        ud = u[i - D] if i >= D else 0.0
        x1 += dt * (ud - x1) / tau
        x2 += dt * (x1 - x2) / tau
        y[i] = x2 + d[i]
    sg = lambda A, B: [(A[j:j + NPS], B[j:j + NPS]) for j in range(0, n - NPS, NPS)]
    f, Puu, Pyy, Puy = spec(sg(u, y))
    _, Pff, _, Pfy = spec(sg(ffc, y))
    _, _, _, Pfu = spec(sg(ffc, u))
    Gd = Puy / Puu
    Giv = Pfy / Pfu
    w = 2 * np.pi * f
    Gt = np.exp(-1j * w * D * dt) / (1 + 1j * w * tau) ** 2
    print(f"  CONTROL (known plant, closed loop, output disturbance; reference rolls off at 0.8 Hz):")
    res = {}
    for lo, hi in [(0.1, 0.5), (0.5, 1.0), (1.0, 2.0)]:
        s = (f > lo) & (f < hi)
        ed = float(np.median(np.abs(Gd[s] - Gt[s]) / np.abs(Gt[s])))
        ei = float(np.median(np.abs(Giv[s] - Gt[s]) / np.abs(Gt[s])))
        res[(lo, hi)] = (ed, ei)
        print(f"    {lo}-{hi} Hz   DIRECT |err| {ed*100:6.1f} %    IV |err| {ei*100:6.1f} %")
    ed, ei = res[(0.1, 0.5)]
    assert ei < 0.08 and ed > 1.4 * ei, "IV control FAILED where the reference HAS power"
    assert res[(1.0, 2.0)][0] > 0.5, "control did not reproduce the known collapse above the reference's corner"
    print("    => both estimators are only usable where the EXOGENOUS reference carries power; above its")
    print("       corner the DIRECT estimate is ~95 % wrong even with a perfectly known plant.")
    return True


def run():
    print("=" * 118)
    print("POSITIVE CONTROL")
    print("=" * 118)
    control_iv()

    R = {}
    for rk, fam in FAM.items():
        if not (V.CACHE / f"{rk}.npz").exists():
            continue
        S = V.load(rk)
        m = V.usable(S, 15.0)
        segs = dict(ZF=[], ZU=[], UY=[], FY=[], FU=[], EPI=[], ZY=[], PIY=[])
        comp = []
        for a, b in V.runs(m, S["t"], min_s=NPS / FS):
            Z = np.nan_to_num(S["setpoint"][a:b]); Y = np.nan_to_num(S["la_act"][a:b])
            p = np.nan_to_num(S["p"][a:b]); i_ = np.nan_to_num(S["i"][a:b]); ff = np.nan_to_num(S["f"][a:b])
            U = p + i_ + ff                      # the command in lateral-accel units, pre-clip
            E = Z - Y                            # the ACTUAL error the loop closes on
            PI = p + i_
            segs["ZF"].append((Z, ff)); segs["ZU"].append((Z, U)); segs["UY"].append((U, Y))
            segs["FY"].append((ff, Y)); segs["FU"].append((ff, U)); segs["EPI"].append((E, PI))
            segs["ZY"].append((Z, Y)); segs["PIY"].append((PI, Y))
            comp.append((p, i_, ff, U))
        if not segs["ZY"]:
            continue
        rec = dict(fam=fam, comp=comp); bad = False
        for k, sg in segs.items():
            f, Pxx, Pyy, Pxy = spec(sg)
            if f is None:
                bad = True; break
            rec["f"] = f
            rec[k] = dict(H=Pxy / np.maximum(Pxx, 1e-30), coh=np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-30),
                          Pxx=Pxx, Pyy=Pyy, Pxy=Pxy)
        if bad:
            print(f"  (skip {rk}: no run >= {NPS/FS:.0f} s at >=15 m/s)"); del S; continue
        R[rk] = rec
        del S
    return R


def bp_rms(x, f1, f2):
    sos = signal.butter(4, [f1, f2], btype="band", fs=FS, output="sos")
    return float(np.sqrt(np.mean(signal.sosfiltfilt(sos, x) ** 2)))


if __name__ == "__main__":
    R = run()

    print("\n" + "=" * 118)
    print("1.  WHAT FRACTION OF THE IN-BAND COMMAND IS FEEDFORWARD?  (>=15 m/s; band-pass RMS of each term,")
    print("    and the share of the command's in-band VARIANCE that the feedforward alone explains)")
    print("=" * 118)
    print(f"  {'fam':8s} {'band':10s} | {'rms(f)/rms(U)':>13s} {'rms(P)/rms(U)':>13s} {'rms(I)/rms(U)':>13s} | "
          f"{'R2(U~f)':>8s}")
    for fam in ["V282", "V282old", "TORQ"]:
        for (f1, f2) in BANDS:
            rows = []
            for rec in R.values():
                if rec["fam"] != fam: continue
                for (p, i_, ff, U) in rec["comp"]:
                    ru = bp_rms(U, f1, f2)
                    if ru <= 0: continue
                    fb = signal.sosfiltfilt(signal.butter(4, [f1, f2], btype="band", fs=FS, output="sos"), ff)
                    ub = signal.sosfiltfilt(signal.butter(4, [f1, f2], btype="band", fs=FS, output="sos"), U)
                    r2 = float(np.corrcoef(fb, ub)[0, 1] ** 2)
                    rows.append([bp_rms(ff, f1, f2) / ru, bp_rms(p, f1, f2) / ru, bp_rms(i_, f1, f2) / ru, r2])
            if rows:
                a = np.median(np.array(rows), axis=0)
                print(f"  {fam:8s} {f1:.2f}-{f2:.2f} | {a[0]:13.3f} {a[1]:13.3f} {a[2]:13.3f} | {a[3]:8.3f}")

    print("\n" + "=" * 118)
    print("2.  IS THE FEEDFORWARD A VALID INSTRUMENT?  coh(setpoint, ff) must be ~1 for the IV estimate to be")
    print("    consistent.  On the torque routes the fork's own rate loop and observer put MEASURED state")
    print("    into ff, so it is not.")
    print("=" * 118)
    print(f"  {'fam':8s} {'band':10s} | {'coh(Z,f)':>9s} | {'coh(Z,U)':>9s} | {'coh(U,Y)':>9s}")
    for fam in ["V282", "V282old", "TORQ"]:
        for (f1, f2) in BANDS:
            vals = []
            for rec in R.values():
                if rec["fam"] != fam: continue
                f = rec["f"]; s = (f >= f1) & (f < f2)
                w = rec["ZF"]["Pxx"][s]
                vals.append([np.average(rec["ZF"]["coh"][s], weights=w),
                             np.average(rec["ZU"]["coh"][s], weights=w),
                             np.average(rec["UY"]["coh"][s], weights=rec["UY"]["Pxx"][s])])
            if vals:
                a = np.median(np.array(vals), axis=0)
                print(f"  {fam:8s} {f1:.2f}-{f2:.2f} | {a[0]:9.3f} | {a[1]:9.3f} | {a[2]:9.3f}")

    print("\n" + "=" * 118)
    print("3.  THE CLOSED-LOOP IDENTIFICATION BIAS, MEASURED.  G = plant from commanded lat-accel to achieved.")
    print("    DIRECT = P_UY/P_UU (what a naive identification returns).  IV = P_fY/P_fU (consistent iff ff is")
    print("    exogenous).  Their ratio IS the bias.")
    print("=" * 118)
    print(f"  {'fam':8s} {'band':10s} | {'|G_direct|':>10s} {'<':>6s} | {'|G_IV|':>8s} {'<':>6s} | "
          f"{'bias |.|':>9s} {'bias <':>7s}")
    for fam in ["V282", "V282old", "TORQ"]:
        for (f1, f2) in BANDS:
            vals = []
            for rec in R.values():
                if rec["fam"] != fam: continue
                f = rec["f"]; s = (f >= f1) & (f < f2)
                w = rec["UY"]["Pxx"][s]
                Gd = np.average(rec["UY"]["H"][s], weights=w)
                Giv = np.average(rec["FY"]["Pxy"][s], weights=None) / np.average(rec["FU"]["Pxy"][s], weights=None)
                vals.append([abs(Gd), np.degrees(np.angle(Gd)), abs(Giv), np.degrees(np.angle(Giv)),
                             abs(Gd) / abs(Giv), np.degrees(np.angle(Gd / Giv))])
            if vals:
                a = np.median(np.array(vals), axis=0)
                print(f"  {fam:8s} {f1:.2f}-{f2:.2f} | {a[0]:10.4f} {a[1]:6.1f} | {a[2]:8.4f} {a[3]:6.1f} | "
                      f"{a[4]:9.3f} {a[5]:7.1f}")

    print("\n" + "=" * 118)
    print("4.  L = C_fb * G  (C_fb = (P+I)/E measured; G from both estimators) -- and T/(1-T), the quantity a")
    print("    1-DOF reading would call L.  If the architecture argument is right these disagree badly.")
    print("=" * 118)
    print(f"  {'fam':8s} {'band':10s} | {'|C_fb|':>7s} | {'|L| IV':>7s} {'<L IV':>7s} | {'|L| dir':>8s} {'<L dir':>7s} "
          f"| {'|T/(1-T)|':>10s} {'<':>7s}")
    for fam in ["V282", "V282old", "TORQ"]:
        for (f1, f2) in BANDS:
            vals = []
            for rec in R.values():
                if rec["fam"] != fam: continue
                f = rec["f"]; s = (f >= f1) & (f < f2)
                Cfb = np.average(rec["EPI"]["H"][s], weights=rec["EPI"]["Pxx"][s])
                Gd = np.average(rec["UY"]["H"][s], weights=rec["UY"]["Pxx"][s])
                Giv = np.average(rec["FY"]["Pxy"][s]) / np.average(rec["FU"]["Pxy"][s])
                T = np.average(rec["ZY"]["H"][s], weights=rec["ZY"]["Pxx"][s])
                Liv, Ld, Tt = Cfb * Giv, Cfb * Gd, T / (1 - T)
                vals.append([abs(Cfb), abs(Liv), np.degrees(np.angle(Liv)), abs(Ld), np.degrees(np.angle(Ld)),
                             abs(Tt), np.degrees(np.angle(Tt))])
            if vals:
                a = np.median(np.array(vals), axis=0)
                print(f"  {fam:8s} {f1:.2f}-{f2:.2f} | {a[0]:7.3f} | {a[1]:7.3f} {a[2]:7.1f} | {a[3]:8.3f} {a[4]:7.1f} "
                      f"| {a[5]:10.3f} {a[6]:7.1f}")
