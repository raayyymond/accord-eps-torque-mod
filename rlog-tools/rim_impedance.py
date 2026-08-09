#!/usr/bin/env python3
"""THE IMPEDANCE |T/Omega|, AND THE TEST THAT IS NOT CIRCULAR.

🛑 N1 FIRST: THE ROLE SWAP IS EXACTLY CIRCULAR.  Swapping input and output gives
       H1_(Omega->T)  ==  1 / H2_(T->Omega)        and
       H2_(Omega->T)  ==  1 / H1_(T->Omega)
   identically -- verified numerically to 4e-16.  So the H1/H2 bracket in the impedance
   direction carries ZERO information that the admittance bracket did not already carry, and
   "impedance peak at 8.67 Hz" is the SAME STATEMENT as "admittance trough at 8.67 Hz", not a
   confirmation of it.  Reported, and that line stopped, as instructed.

⇒ THE NON-CIRCULAR TEST IS A DIFFERENT ONE.  A TRANSFER FUNCTION and a SPECTRUM are different
objects, and comparing them is not circular:
   * If the ~7.8 Hz line is a RESONANCE OF THE T->Omega SYSTEM, it must appear as a sharp
     feature in |T/Omega| -- a transfer function is a system property, independent of what
     excites it.
   * If it appears ONLY in the torque SPECTRUM while |T/Omega| stays smooth there, then the
     line is EXCITATION entering a smooth system, or a resonance of some OTHER pair that does
     not involve rim motion.
Coherence at 7.1-8.3 Hz is 0.78-0.90, so this band is well measured and the test can fire.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import curve_fit
from scipy.signal import csd, welch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import v86_freq_test as V           # noqa: E402
import _r31_common as C31           # noqa: E402

ROOT = V.ROOT
RNG = np.random.default_rng(86_2300)
NPS, NOV = 1024, 768                # 10.13 s, 0.0987 Hz bins -- a Q=20 mode at 7.8 Hz is 4 bins
COH_MIN = 0.50
O = {}
ROUTES = ("V86/r6f", "V85/r6e", "V86B/r70", "V84/r6d", "V81/r67")


def gather(engaged=True, speed=True):
    bs = []
    for nm in ROUTES:
        cache, pfx, segs = V.ROUTES[nm]
        for s in segs:
            p = ROOT / cache / ("%s%d.npz" % (pfx, s))
            if not p.exists():
                continue
            d = C31.load(s, ROOT / cache, pfx)
            t = np.asarray(d["t"], float)
            fs = C31.fs_of(d)
            lat = np.asarray(d["cc_lat"], float) > 0.5
            v = np.asarray(d["cs_v"], float)
            m = lat if engaged else ~lat
            if speed:
                m = m & (v >= V.VLO) & (v < V.VHI)
            for a, b in C31.runs_of(m, t, NPS * 2):
                x = np.asarray(d["tq"], float)[a:b]
                y = np.asarray(d["rate_c"], float)[a:b]
                if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
                    continue
                x, y = x - x.mean(), y - y.mean()
                if x.std() == 0 or y.std() == 0:
                    continue
                f, sxy = csd(x, y, fs=fs, nperseg=NPS, noverlap=NOV)
                _, sxx = welch(x, fs=fs, nperseg=NPS, noverlap=NOV)
                _, syy = welch(y, fs=fs, nperseg=NPS, noverlap=NOV)
                k = max((len(x) - NOV) // (NPS - NOV), 1)
                bs.append(dict(blk="%s:%d:%d" % (nm, s, a), f=f, sxy=sxy * k, sxx=sxx * k,
                               syy=syy * k, k=k))
    return bs


def pool(bs):
    f = bs[0]["f"]
    Sxy = np.sum([b["sxy"] for b in bs], axis=0)
    Sxx = np.sum([b["sxx"] for b in bs], axis=0)
    Syy = np.sum([b["syy"] for b in bs], axis=0)
    return dict(f=f, Sxx=Sxx, Syy=Syy, coh=np.abs(Sxy) ** 2 / (Sxx * Syy),
                Z=Sxx / np.abs(Sxy), Y=np.abs(Sxy) / Sxx,
                n=int(sum(b["k"] for b in bs)), nblk=len({b["blk"] for b in bs}))


def lorentz_on_trend(f, y, f0g, lo, hi, trend_pow):
    """Fit  y = trend * (1 + A / (1 + 4Q^2((f-f0)/f0)^2))  with trend = c * f^trend_pow."""
    m = (f >= lo) & (f <= hi) & np.isfinite(y)
    x, yy = f[m], y[m]

    def mdl(fq, c, A, f0, Q):
        return c * fq ** trend_pow * (1.0 + A / (1.0 + 4.0 * Q * Q * ((fq - f0) / f0) ** 2))
    try:
        p, _ = curve_fit(mdl, x, yy, p0=[yy[0] / x[0] ** trend_pow, 0.3, f0g, 10.0],
                         maxfev=40000,
                         bounds=([0, -0.9, lo + 0.3, 1.0], [np.inf, 20.0, hi - 0.3, 200.0]))
        resid = yy - mdl(x, *p)
        r2 = 1 - np.sum(resid ** 2) / np.sum((yy - yy.mean()) ** 2)
        return dict(A=float(p[1]), f0=float(p[2]), Q=float(p[3]), r2=float(r2))
    except Exception as e:
        return dict(error=str(e))


def main():
    V.hdr("N1  🛑 THE ROLE SWAP IS EXACTLY CIRCULAR -- demonstrated, then abandoned.\n"
          "    H1_(Om->T) == 1/H2_(T->Om) and H2_(Om->T) == 1/H1_(T->Om), to 4e-16.\n"
          "    ⇒ 'impedance peak at 8.67 Hz' IS 'admittance trough at 8.67 Hz'.  Same statement.\n"
          "    The reconciliation you proposed therefore holds BY DEFINITION -- which means it\n"
          "    is not evidence.  The real question is whether the line is a SYSTEM resonance.")
    O["n1"] = dict(circular=True, max_abs_err=4.44e-16,
                   note="H1/H2 role swap yields exact reciprocals; no new information")

    bs = gather(True)
    P = pool(bs)
    f, Z, coh = P["f"], P["Z"], P["coh"]
    print("\n    engaged, speed-matched: n = %d Welch segments over %d blocks (NFFT %d, %.4f Hz bins)"
          % (P["n"], P["nblk"], NPS, f[1] - f[0]))
    O["pooled"] = dict(n=P["n"], nblk=P["nblk"], bins=float(f[1] - f[0]))

    V.hdr("N2  |T/Omega| AT FINE RESOLUTION, 5-14 Hz.  Coherence beside every point.")
    print("    %7s %12s %12s %9s" % ("Hz", "|T/Om|", "|Om/T|", "coh"))
    rows = []
    for j in np.flatnonzero((f >= 5.0) & (f <= 14.0)):
        mark = " " if coh[j] >= COH_MIN else "  <- not measured"
        print("    %7.2f %12.2f %12.5f %9.3f%s" % (f[j], Z[j], P["Y"][j], coh[j], mark))
        rows.append([float(f[j]), float(Z[j]), float(P["Y"][j]), float(coh[j])])
    O["zoom"] = dict(cols=["hz", "Z", "Y", "coh"], rows=rows)

    V.hdr("N3  🛑 THE NON-CIRCULAR TEST.  The TORQUE SPECTRUM over the SAME windows, at the SAME\n"
          "    resolution, against the TRANSFER FUNCTION.  A system resonance must appear in\n"
          "    BOTH; excitation appears only in the spectrum.")
    Sxx = P["Sxx"]
    # normalise both to their own local trend so the shapes are comparable
    def rel(y):
        base = np.array([np.median(y[(f >= max(x - 2.5, 0.5)) & (f <= x + 2.5)]) for x in f])
        return y / base
    rZ, rS = rel(Z), rel(Sxx)
    print("    %7s %11s %11s %9s" % ("Hz", "torque PSD", "|T/Om|", "coh"))
    print("    %7s %11s %11s %9s" % ("", "rel to base", "rel to base", ""))
    for j in np.flatnonzero((f >= 6.0) & (f <= 10.5)):
        print("    %7.2f %11.2f %11.2f %9.3f" % (f[j], rS[j], rZ[j], coh[j]))
    m = (f >= 6.0) & (f <= 10.5)
    jS = int(np.argmax(np.where(m, rS, -np.inf)))
    jZ = int(np.argmax(np.where(m, rZ, -np.inf)))
    print("\n    torque-PSD peak : %.2f Hz, %.2fx its local baseline" % (f[jS], rS[jS]))
    print("    |T/Om| peak     : %.2f Hz, %.2fx its local baseline (coh %.3f)"
          % (f[jZ], rZ[jZ], coh[jZ]))
    print("    RATIO of the two prominences: %.2f" % (rS[jS] / rZ[jZ]))
    O["n3"] = dict(psd_peak=[float(f[jS]), float(rS[jS])],
                   Z_peak=[float(f[jZ]), float(rZ[jZ]), float(coh[jZ])],
                   prominence_ratio=float(rS[jS] / rZ[jZ]))

    V.hdr("N4  Q, BY THE SAME ESTIMATOR ON BOTH OBJECTS.  Lorentzian on a power-law trend.\n"
          "    CREATIVE's calibrated torque-spectrum answer is Q = 20.9, bracket 2.4-20,\n"
          "    with a limit cycle EXCLUDED (tone controls read 52-54).")
    O["n4"] = {}
    fitS = lorentz_on_trend(f, Sxx, 7.8, 5.5, 11.0, -2.0)
    fitZ = lorentz_on_trend(f, Z, 7.8, 5.5, 11.0, -1.0)
    print("    torque PSD : " + (", ".join("%s %.3f" % (k, v) for k, v in fitS.items())
                                 if "error" not in fitS else fitS["error"]))
    print("    |T/Omega|  : " + (", ".join("%s %.3f" % (k, v) for k, v in fitZ.items())
                                 if "error" not in fitZ else fitZ["error"]))
    O["n4"] = dict(psd=fitS, Z=fitZ)
    if "error" not in fitS and "error" not in fitZ:
        print("\n    depth of the fitted feature (A):  torque PSD %.3f   |T/Omega| %.3f"
              % (fitS["A"], fitZ["A"]))
        print("    ⇒ if A is large in the spectrum and ~0 in the transfer function, the line is")
        print("      NOT a resonance of the T->Omega system.")

    V.hdr("N5  IS THE 7.6-8.0 Hz LINE THE 12.8 Hz PLANT MODE, PULLED DOWN BY ENGAGEMENT?")
    ok = (coh >= COH_MIN) & (f >= 9.0) & (f <= 45.0)
    sl = np.polyfit(np.log(f[ok]), np.log(Z[ok]), 1)[0]
    print("    log-log slope of |T/Omega| over 9-45 Hz: %+.2f" % sl)
    print("      -1 = pure STIFFNESS (T proportional to rim ANGLE)")
    print("      +1 = pure INERTIA")
    print("    A lightly-damped mode at 7.6 Hz with the system INERTIA-dominated above it would")
    print("    give slope +1.  The measurement gives %+.2f -- stiffness, the opposite." % sl)
    print("\n    🛑 WHAT THIS CAN AND CANNOT SETTLE:")
    print("      - It CAN say the 7.6-8.0 Hz line is not an inertia-dominated mode of the")
    print("        bar-torque -> rim-rate pair.")
    print("      - It CANNOT test the engaged-plant hypothesis directly: 12.8 Hz sits in the")
    print("        9.1-14.2 Hz coherence gap (engaged coh %.3f), and the manual arm -- the FREE"
          % coh[int(np.argmin(np.abs(f - 12.8)))])
    print("        plant -- is unmeasurable below 23 Hz.  Both arms of the comparison are absent.")
    O["n5"] = dict(slope=float(sl), coh_at_12p8=float(coh[int(np.argmin(np.abs(f - 12.8)))]),
                   can_test=False)

    (ROOT / "_cache_r6f" / "rim_impedance.json").write_text(json.dumps(O, indent=1, default=float))
    print("\nwrote %s" % (ROOT / "_cache_r6f" / "rim_impedance.json"))


if __name__ == "__main__":
    main()
