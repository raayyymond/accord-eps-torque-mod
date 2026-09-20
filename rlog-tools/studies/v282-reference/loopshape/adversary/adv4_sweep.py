"""ADVERSARY 4 -- the frequency sweep: crossover, margins, and WHERE THE DATA CAN AND CANNOT SUPPORT THEM.

L(jw) = C_fb(jw) * G(jw), both measured from logged signals:
   C_fb = P_{E,(P+I)} / P_{EE}        E = setpoint - achieved   (exact: P+I is a deterministic function of E)
   G    = P_{f,Y} / P_{f,U}           instrument = the feedforward   (IV; validity checked in adv3)
Speed-stratified, because the vehicle leg M->Y is a strong function of speed and the families are not
speed-matched.  Also reports the EXCITATION SPECTRUM -- how much exogenous reference power there is at each
frequency -- because that is what decides whether a margin at 2-3 Hz is identifiable at all.
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
NPS = 2048          # 20.48 s -> df 0.0488 Hz; shorter so more runs qualify and the speed bins stay clean
FAM = {"00000064--ce6b0b0ebb": "V282", "00000065--b9f78988bd": "V282", "0000006c--2bc842dbac": "V282",
       "00000039--f56039af87": "V282old", "0000003a--283a39a1d6": "V282old", "0000003c--927965c2b4": "V282old",
       "0000006c--68c6e94b17": "TORQ", "0000006d--05e83bb04f": "TORQ", "0000006e--6ca3e014fd": "TORQ",
       "00000075--6c8687d5bd": "TORQ", "00000076--d0b7ea7e4d": "TORQ"}
SPEEDS = [(15.0, 22.0), (22.0, 99.0)]


def acc(store, key, x, y):
    if len(x) < NPS:
        return
    x, y = x[:len(x) // NPS * NPS], y[:len(y) // NPS * NPS]
    xs, ys = x - x.mean(), y - y.mean()
    f, pxx = signal.welch(xs, FS, nperseg=NPS, noverlap=NPS // 2)
    _, pyy = signal.welch(ys, FS, nperseg=NPS, noverlap=NPS // 2)
    _, pxy = signal.csd(xs, ys, FS, nperseg=NPS, noverlap=NPS // 2)
    d = store.setdefault(key, dict(Pxx=0, Pyy=0, Pxy=0, n=0, f=f))
    d["Pxx"] = d["Pxx"] + pxx; d["Pyy"] = d["Pyy"] + pyy; d["Pxy"] = d["Pxy"] + pxy; d["n"] += 1


def collect():
    out = {}
    for rk, fam in FAM.items():
        if not (V.CACHE / f"{rk}.npz").exists():
            continue
        S = V.load(rk)
        for (v1, v2) in SPEEDS:
            m = V.usable(S, v1, v2)
            st = out.setdefault((fam, v1), {})
            for a, b in V.runs(m, S["t"], min_s=NPS / FS):
                Z = np.nan_to_num(S["setpoint"][a:b]); Y = np.nan_to_num(S["la_act"][a:b])
                p = np.nan_to_num(S["p"][a:b]); i_ = np.nan_to_num(S["i"][a:b]); ff = np.nan_to_num(S["f"][a:b])
                M = np.nan_to_num(S["sa"][a:b])
                U = p + i_ + ff; E = Z - Y; PI = p + i_
                acc(st, "EPI", E, PI); acc(st, "FY", ff, Y); acc(st, "FU", ff, U)
                acc(st, "UY", U, Y);   acc(st, "ZZ", Z, Z);  acc(st, "ZY", Z, Y)
                acc(st, "ZM", Z, M);   acc(st, "MM", M, M)
        del S
    return out


def margins(f, L, fmin=0.05, fmax=4.0):
    s = (f >= fmin) & (f <= fmax)
    ff, LL = f[s], L[s]
    mag = np.abs(LL); ph = np.degrees(np.unwrap(np.angle(LL)))
    out = dict(fc=np.nan, pm=np.nan, f180=np.nan, gm=np.nan, Ms=float(np.max(np.abs(1 / (1 + LL)))),
               fMs=float(ff[np.argmax(np.abs(1 / (1 + LL)))]), maxL=float(mag.max()), fmaxL=float(ff[np.argmax(mag)]))
    k = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0]
    if len(k):
        i = k[0]
        out["fc"] = float(np.interp(0, [np.log(mag[i + 1]), np.log(mag[i])], [ff[i + 1], ff[i]]))
        out["pm"] = float(180 + np.interp(out["fc"], ff, ph))
    k2 = np.where((ph[:-1] >= -180) & (ph[1:] < -180))[0]
    if len(k2):
        i = k2[0]
        out["f180"] = float(ff[i]); out["gm"] = float(1 / max(mag[i], 1e-9))
    return out


if __name__ == "__main__":
    ST = collect()
    print("=" * 122)
    print("A.  L(jw) = C_fb * G_IV, SPEED-STRATIFIED.  Values are band medians of the complex transfer.")
    print("=" * 122)
    grid = [(0.08, 0.15), (0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.00), (2.00, 3.00), (3.00, 4.50)]
    curves = {}
    for (fam, v1), st in sorted(ST.items()):
        f = st["EPI"]["f"]
        Cfb = st["EPI"]["Pxy"] / st["EPI"]["Pxx"]
        G = st["FY"]["Pxy"] / st["FU"]["Pxy"]
        L = Cfb * G
        curves[(fam, v1)] = (f, L, st)
        print(f"\n  {fam}  {v1:.0f}+ m/s   ({st['EPI']['n']} windows of {NPS/FS:.0f} s)")
        print(f"    {'band Hz':12s} {'|C_fb|':>7s} {'|G|':>7s} {'<G':>7s} {'|L|':>7s} {'<L':>7s} "
              f"{'|S|=1/|1+L|':>11s} {'coh(f,Y)':>9s} {'refPSD %':>9s}")
        tot = float(np.sum(st["ZZ"]["Pxx"][(f >= 0.05) & (f <= 4.5)]))
        for (a, b) in grid:
            s = (f >= a) & (f < b)
            if s.sum() == 0: continue
            w = st["ZZ"]["Pxx"][s]
            c = np.average(Cfb[s], weights=w); g = np.average(G[s], weights=w); l = np.average(L[s], weights=w)
            coh = np.average(np.abs(st["FY"]["Pxy"][s]) ** 2 / (st["FY"]["Pxx"][s] * st["FY"]["Pyy"][s]), weights=w)
            sens = float(np.average(np.abs(1 / (1 + L[s])), weights=w))
            print(f"    {a:.2f}-{b:.2f}   {abs(c):7.3f} {abs(g):7.3f} {np.degrees(np.angle(g)):7.1f} "
                  f"{abs(l):7.3f} {np.degrees(np.angle(l)):7.1f} {sens:11.3f} {coh:9.3f} "
                  f"{100*float(np.sum(w))/tot:9.2f}")

    print("\n" + "=" * 122)
    print("B.  MARGINS (0.05-4.5 Hz).  Ms = peak sensitivity.  'no crossover' means |L| never reaches 1.")
    print("=" * 122)
    print(f"  {'fam':8s} {'speed':7s} | {'fc Hz':>7s} {'PM deg':>7s} | {'f180':>6s} {'GM':>6s} | {'Ms':>5s} "
          f"{'f(Ms)':>6s} | {'max|L|':>7s} {'at Hz':>6s}")
    for (fam, v1), (f, L, st) in sorted(curves.items()):
        m = margins(f, L)
        fc = f"{m['fc']:.3f}" if np.isfinite(m["fc"]) else "  none"
        pm = f"{m['pm']:.1f}" if np.isfinite(m["pm"]) else "    - "
        f180 = f"{m['f180']:.2f}" if np.isfinite(m["f180"]) else "  -  "
        gm = f"{m['gm']:.2f}" if np.isfinite(m["gm"]) else "  -  "
        print(f"  {fam:8s} {v1:.0f}+     | {fc:>7s} {pm:>7s} | {f180:>6s} {gm:>6s} | {m['Ms']:5.2f} "
              f"{m['fMs']:6.2f} | {m['maxL']:7.2f} {m['fmaxL']:6.2f}")

    print("\n" + "=" * 122)
    print("C.  WHAT A SteerKP DOSE WOULD DO, ARITHMETICALLY.  L scales with C_fb, so k x SteerKP -> k x L.")
    print("    Reported: the k needed to reach V282's |L| at 0.15-0.30 Hz, and what that k does to the")
    print("    1.2-3.0 Hz band where the shake lives -- and whether the data can see that band at all.")
    print("=" * 122)
    ref = {}
    for (fam, v1), (f, L, st) in curves.items():
        s = (f >= 0.15) & (f < 0.30)
        w = st["ZZ"]["Pxx"][s]
        ref[(fam, v1)] = abs(np.average(L[s], weights=w))
    for v1 in [15.0, 22.0]:
        if ("V282", v1) not in ref or ("TORQ", v1) not in ref: continue
        k = ref[("V282", v1)] / ref[("TORQ", v1)]
        f, L, st = curves[("TORQ", v1)]
        tot = float(np.sum(st["ZZ"]["Pxx"][(f >= 0.05) & (f <= 4.5)]))
        s = (f >= 1.2) & (f < 3.0)
        w = st["ZZ"]["Pxx"][s]
        Lb = abs(np.average(L[s], weights=w))
        coh = float(np.average(np.abs(st["FY"]["Pxy"][s]) ** 2 /
                               (st["FY"]["Pxx"][s] * st["FY"]["Pyy"][s]), weights=w))
        m = margins(f, L * k)
        print(f"  {v1:.0f}+ m/s: V282 |L|={ref[('V282',v1)]:.3f}  TORQ |L|={ref[('TORQ',v1)]:.3f}  -> k = {k:.2f}x SteerKP "
              f"(0.85 -> {0.85*k:.2f})")
        print(f"      at k: |L| 1.2-3.0 Hz goes {Lb:.3f} -> {Lb*k:.3f};  Ms {margins(f,L)['Ms']:.2f} -> {m['Ms']:.2f}"
              f" at {m['fMs']:.2f} Hz;  crossover -> "
              f"{('%.2f Hz, PM %.0f deg' % (m['fc'], m['pm'])) if np.isfinite(m['fc']) else 'still none'}")
        print(f"      BUT the exogenous reference carries only {100*float(np.sum(w))/tot:.2f} % of its 0.05-4.5 Hz power")
        print(f"      in 1.2-3.0 Hz, and coh(ff, Y) there is {coh:.2f} -- the band the dose would load is the band")
        print(f"      the logs identify worst.")
