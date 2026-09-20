# -*- coding: utf-8 -*-
"""REGIME B stage 7: does any FLOWN toggle move the named object, and what is left unmeasured?

  L1  per torque REV: the demand-normalised incoherent wheel residual.  The revs differ in
      AccordRefFilter (T2 absent / T3,T4,T5 0.12 / T64 0.06), AccordDobHz (T5,T64 0.6 / others absent),
      AccordTorqueKi, SteerFriction, SteerKP -- all read from each route's OWN initData.  If the object
      is indifferent to all of them, no flown toggle is a lever on it.
  L2  the STRUCTURAL HOLE: |H| and the residual inside torque mode at demand levels where V282 has no
      windows at all, so the published A3 number is placed honestly.
  L3  exposure-weighted restatement of Regime B using the matched read.

MEASUREMENT.  ANALYSIS ONLY, read-only.  usage: python b7_levers.py > B7-OUT.txt
"""
import sys, json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V  # noqa: E402

D = np.load(HERE / "b1_spec.npz", allow_pickle=True)
W = float(D["W"][0]); FR = np.arange(D["X"].shape[1]) / W
NRM1 = 16.0 / (3.0 * (W * 100.0) ** 2)
SPDN = ["0-8", "8-15", "15-22", "22+"]
TORQ = ["T64", "T64B", "T5", "T4", "T3", "T2"]
DSEL = {1: (0.004, 0.018), 2: (0.004, 0.026), 3: (0.008, 0.040)}
PAR = json.load(open(HERE.parents[1] / "hsurface" / "surface" / "params_all.json"))
rng = np.random.default_rng(71)


def brms(C, f1, f2):
    s = (FR >= f1) & (FR < f2)
    return np.sqrt((np.abs(C[:, s]) ** 2).sum(1) * NRM1)


def resid(idx, ch, f1, f2, fit=None):
    fi = fit if fit is not None else idx
    Pxx = (np.abs(D["X"][fi]) ** 2).sum(0)
    Pxc = (np.conj(D["X"][fi]) * D[ch][fi]).sum(0)
    T = Pxc / np.maximum(Pxx, 1e-300)
    R = D[ch][idx] - T[None, :] * D["X"][idx]
    s = (FR >= f1) & (FR < f2)
    return np.sqrt((np.abs(R[:, s]) ** 2).sum(1) * NRM1)


def main():
    d = brms(D["X"], 0.6, 1.2)
    print("=" * 150)
    print("L1. PER FORK REV: demand-normalised incoherent WHEEL-ANGLE residual (deg of residual per m/s^2 of")
    print("    in-band demand), 0.60-1.20 Hz and 1.80-3.50 Hz, matched speed, hands-off engaged.")
    print("    Params are each route's OWN flown initData.  V282 is the reference row.")
    print("=" * 150)
    revs = [("V282", ["V282"]), ("T2", ["T2"]), ("T3", ["T3"]), ("T4", ["T4"]), ("T5", ["T5"]),
            ("T64", ["T64"]), ("T64B", ["T64B"])]
    print(f"   {'rev':6s} {'RefFilt':>8s} {'DobHz':>6s} {'Ki':>5s} {'Fric':>7s} {'KP':>5s} | " +
          " ".join(f"{SPDN[i]:>22s}" for i in (1, 2, 3)))
    print(f"   {'':6s} {'':>8s} {'':>6s} {'':>5s} {'':>7s} {'':>5s} | " +
          " ".join(f"{'n  .6-1.2  1.8-3.5':>22s}" for i in (1, 2, 3)))
    for nm, mem in revs:
        rts = [r for r in PAR if r in set(D["route"][np.isin(D["group"], mem)])]
        p = PAR[rts[0]] if rts else {}
        row = (f"   {nm:6s} {str(p.get('AccordRefFilter','-'))[:8]:>8s} {str(p.get('AccordDobHz','-'))[:6]:>6s} "
               f"{str(p.get('AccordTorqueKi','-'))[:5]:>5s} {str(p.get('SteerFriction','-'))[:7]:>7s} "
               f"{str(p.get('SteerKP','-'))[:5]:>5s} |")
        for i in (1, 2, 3):
            dlo, dhi = DSEL[i]
            k = np.flatnonzero((D["cls"] == "E") & (D["sbin"] == i) & np.isin(D["group"], mem) &
                               (d >= dlo) & (d < dhi))
            if len(k) < 6:
                row += f" {len(k):4d}{'--':>9s}{'--':>9s}"
                continue
            fit = np.flatnonzero((D["cls"] == "E") & (D["sbin"] == i) & np.isin(D["group"], TORQ if nm != "V282" else ["V282"]))
            r1 = np.median(resid(k, "A", 0.6, 1.2, fit) / np.maximum(d[k], 1e-9))
            r2 = np.median(resid(k, "A", 1.8, 3.5, fit) / np.maximum(d[k], 1e-9))
            row += f" {len(k):4d} {r1:8.1f} {r2:8.1f}"
        print(row)
    print("\n   (units: deg of demand-unexplained wheel angle per m/s^2 of in-band demand RMS; the ratio is")
    print("    taken per window then median-ed, so it is not driven by one loud window.)")

    print("\n" + "=" * 150)
    print("L2. THE STRUCTURAL HOLE.  |H| X->Y at 0.60-1.20 Hz inside torque mode across the WHOLE demand")
    print("    range, with the V282 window count alongside.  The published A3 number (2.503 at 8-15) is")
    print("    measured where V282 has n<6, so it is not a measured contrast there.")
    print("=" * 150)
    EDG = [0.004, 0.008, 0.012, 0.018, 0.026, 0.040, 0.070, 0.150]
    for i in (1, 2):
        print(f"\n   speed {SPDN[i]} m/s")
        print(f"    {'demand RMS':>14s} {'TORQ n':>7s} {'TORQ |H|':>9s} {'TORQ Minc':>10s} {'V282 n':>7s} "
              f"{'V282 |H|':>9s} {'V282 Minc':>10s} {'TORQ exposure':>14s}")
        kt_all = np.flatnonzero((D["cls"] == "E") & (D["sbin"] == i) & np.isin(D["group"], TORQ))
        for lo, hi in zip(EDG[:-1], EDG[1:]):
            out = []
            for mem in (TORQ, ["V282"]):
                k = np.flatnonzero((D["cls"] == "E") & (D["sbin"] == i) & np.isin(D["group"], mem) &
                                   (d >= lo) & (d < hi))
                if len(k) == 0:
                    out.append((0, float("nan"), float("nan"))); continue
                s = (FR >= 0.6) & (FR < 1.2)
                X = D["X"][k][:, s]; Y = D["Y"][k][:, s]
                Pxx = (np.abs(X) ** 2).sum(0); Pyy = (np.abs(Y) ** 2).sum(0); Pxy = (np.conj(X) * Y).sum(0)
                H = float(np.average(np.abs(Pxy) / np.maximum(Pxx, 1e-300), weights=Pxx))
                mi = float(np.sqrt(np.average(np.maximum(Pyy - np.abs(Pxy) ** 2 / np.maximum(Pxx, 1e-300), 0) /
                                              np.maximum(Pxx, 1e-300), weights=Pxx)))
                out.append((len(k), H, mi))
            exp = np.mean((d[kt_all] >= lo) & (d[kt_all] < hi)) * 100
            print(f"    {lo:.3f}-{hi:.3f}   {out[0][0]:7d} {out[0][1]:9.3f} {out[0][2]:10.3f} {out[1][0]:7d} "
                  f"{out[1][1]:9.3f} {out[1][2]:10.3f} {exp:13.1f}%")

    print("\n" + "=" * 150)
    print("L3. EXPOSURE-WEIGHTED RESTATEMENT at 0.60-1.20 Hz, matched demand.  dM^2 split into the coherent")
    print("    and incoherent legs; exposure = each speed bin's share of the torque car's engaged windows")
    print("    in the matched demand range.")
    print("=" * 150)
    tot = 0.0; acc = []
    for i in (1, 2, 3):
        dlo, dhi = DSEL[i]
        st = {}
        for g, mem in [("V282", ["V282"]), ("TORQ", TORQ)]:
            k = np.flatnonzero((D["cls"] == "E") & (D["sbin"] == i) & np.isin(D["group"], mem) &
                               (d >= dlo) & (d < dhi))
            s = (FR >= 0.6) & (FR < 1.2)
            X = D["X"][k][:, s]; Y = D["Y"][k][:, s]
            Pxx = (np.abs(X) ** 2).sum(0); Pyy = (np.abs(Y) ** 2).sum(0); Pxy = (np.conj(X) * Y).sum(0)
            Hb = Pxy / np.maximum(Pxx, 1e-300); aH = np.abs(Hb); ph = np.angle(Hb)
            mc2 = float(np.average((aH - 1) ** 2 + 2 * aH * (1 - np.cos(ph)), weights=Pxx))
            inc = float(np.average(np.maximum(Pyy - np.abs(Pxy) ** 2 / np.maximum(Pxx, 1e-300), 0) /
                                   np.maximum(Pxx, 1e-300), weights=Pxx))
            st[g] = (mc2, inc, len(k))
        acc.append((i, st)); tot += st["TORQ"][2]
    print(f"   {'speed':7s} {'exposure':>9s} {'M V282':>8s} {'M TORQ':>8s} {'dM':>7s} {'d(Mcoh^2)':>10s} "
          f"{'d(Minc^2)':>10s} {'incoherent share of dM^2':>26s}")
    for i, st in acc:
        mv = (st["V282"][0] + st["V282"][1]) ** .5; mt = (st["TORQ"][0] + st["TORQ"][1]) ** .5
        dc = st["TORQ"][0] - st["V282"][0]; di = st["TORQ"][1] - st["V282"][1]
        print(f"   {SPDN[i]:7s} {st['TORQ'][2]/tot*100:8.1f}% {mv:8.3f} {mt:8.3f} {mt-mv:7.3f} {dc:10.3f} "
              f"{di:10.3f} {di/max(dc+di,1e-9)*100:25.0f}%")


if __name__ == "__main__":
    main()
