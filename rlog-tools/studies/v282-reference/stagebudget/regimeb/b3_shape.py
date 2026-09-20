# -*- coding: utf-8 -*-
"""REGIME B stage 3: the SHAPE of what survives matching, per channel, per speed -- and the loop-open control.

b2 showed the 0.60-1.20 Hz coherent GAIN gap is an artefact of the open-ended A3 stratum: at matched in-band
demand RMS the two builds read the same |H|.  What survives is the INCOHERENT part (the motion the demand
does not explain), 1.4-2.9x V282 at matched demand.  This script asks what that object IS:

  1  SPECTRAL SHAPE 0.3-4.5 Hz of the incoherent residual, per channel, per speed, both builds.
     A distinct 0.6-1.2 Hz object shows a bump there.  The low skirt of the known 1.8-3.5 Hz shake shows a
     ratio that climbs monotonically toward 2-3 Hz with no separate feature.
  2  WHICH CHANNEL: command U, wheel angle A, steering rate R, controller-measured M, achieved yaw Y.
     In U and A and Y -> loop-generated.  In Y only -> body/tyre/road/sensor.
  3  DOES ITS FREQUENCY MOVE WITH SPEED: a plant/tyre/body mode scales with speed, a steering mode and a
     fork filter do not.
  4  LOOP-OPEN CONTROL: the same residual on DISENGAGED windows, matched on speed and wheel angle.  A mode
     that is present with the loop open is not the controller's.

"Incoherent" here = the part of a channel's in-band power not linearly predictable from the demand X,
computed per frequency bin from pooled cross-spectra: Pnn(f) = Pcc(f) - |Pxc(f)|^2 / Pxx(f).

MEASUREMENT.  ANALYSIS ONLY, read-only.  usage: python b3_shape.py > B3-OUT.txt
"""
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V  # noqa: E402

D = np.load(HERE / "b1_spec.npz", allow_pickle=True)
W = float(D["W"][0]); FR = np.arange(D["X"].shape[1]) / W
SPDN = ["0-8", "8-15", "15-22", "22+"]
TORQ = ["T64", "T64B", "T5", "T4", "T3", "T2"]
CH = ["U", "A", "R", "M", "Y"]
rng = np.random.default_rng(23)


def band_rms(C, f1, f2):
    s = (FR >= f1) & (FR < f2)
    return np.sqrt((np.abs(C[:, s]) ** 2).sum(1) * 16.0 / (3.0 * (W * 100.0) ** 2))


def perbin(idx, ch):
    """Pooled per-bin: total power, demand-coherent power, incoherent power, in RMS-per-sqrt(Hz)-ish units."""
    X = D["X"][idx]; C = D[ch][idx]
    Pxx = (np.abs(X) ** 2).sum(0); Pcc = (np.abs(C) ** 2).sum(0)
    Pxc = (np.conj(X) * C).sum(0)
    coh_pow = np.abs(Pxc) ** 2 / np.maximum(Pxx, 1e-300)
    nrm = 16.0 / (3.0 * (W * 100.0) ** 2 * len(idx))
    return dict(tot=Pcc * nrm, coh=coh_pow * nrm, inc=np.maximum(Pcc - coh_pow, 0) * nrm,
                Pxx=Pxx * nrm, n=len(idx))


def boot_ratio(ka, kb, ch, f1, f2, which="inc", nb=400):
    """Route-cluster bootstrap on the in-band RMS ratio (group a / group b) of the chosen component."""
    def draw(k):
        rts = sorted(set(D["route"][k]))
        per = {r: k[D["route"][k] == r] for r in rts}
        return np.concatenate([per[r] for r in rng.choice(rts, len(rts))]) if len(rts) >= 2 else k
    s = (FR >= f1) & (FR < f2)
    v = []
    for _ in range(nb):
        a = perbin(draw(ka), ch)[which][s].sum()
        b = perbin(draw(kb), ch)[which][s].sum()
        v.append(np.sqrt(a / max(b, 1e-300)))
    return tuple(float(x) for x in np.percentile(v, [2.5, 97.5]))


def sel(cls, sbin, grp, amin=None, amax=None, dmin=None, dmax=None):
    m = (D["cls"] == cls) & (D["sbin"] == sbin) & np.isin(D["group"], grp)
    if amin is not None:
        m &= D["sa_p95"] >= amin
    if amax is not None:
        m &= D["sa_p95"] < amax
    if dmin is not None:
        m &= band_rms(D["X"], 0.6, 1.2) >= dmin
    if dmax is not None:
        m &= band_rms(D["X"], 0.6, 1.2) < dmax
    return np.flatnonzero(m)


FBINS = [(0.30, 0.45), (0.45, 0.60), (0.60, 0.80), (0.80, 1.00), (1.00, 1.20), (1.20, 1.50),
         (1.50, 1.80), (1.80, 2.20), (2.20, 2.70), (2.70, 3.30), (3.30, 4.00), (4.00, 4.60)]


def show_shape(title, ka, kb, chans=CH, comp="inc"):
    print(f"\n  {title}")
    print(f"    V282 n={len(ka)}  TORQ n={len(kb)}")
    hdr = "    " + f"{'band Hz':>11s} " + " ".join(f"{c+' V/T/x':>21s}" for c in chans)
    print(hdr)
    for f1, f2 in FBINS:
        s = (FR >= f1) & (FR < f2)
        row = f"    {f1:.2f}-{f2:.2f}   "
        for c in chans:
            a = np.sqrt(perbin(ka, c)[comp][s].sum())
            b = np.sqrt(perbin(kb, c)[comp][s].sum())
            row += f" {a:8.4f}/{b:8.4f}/{b/max(a,1e-12):4.2f}"
        print(row)


def main():
    dmd = band_rms(D["X"], 0.6, 1.2)
    print("=" * 170)
    print("1+2+3. INCOHERENT (demand-unexplained) spectrum per channel, MATCHED on in-band demand RMS, hands-off engaged.")
    print("   Columns are RMS of the incoherent part in each band: V282 / TORQ / ratio.")
    print("   Units: U torque [-1,1]; A deg; R deg/s; M and Y m/s^2.")
    print("=" * 170)
    for i, (dlo, dhi) in [(1, (0.004, 0.018)), (2, (0.004, 0.026)), (3, (0.008, 0.040))]:
        ka = sel("E", i, ["V282"], dmin=dlo, dmax=dhi)
        kb = sel("E", i, TORQ, dmin=dlo, dmax=dhi)
        show_shape(f"speed {SPDN[i]} m/s, in-band demand RMS {dlo}-{dhi} (common support)", ka, kb)
        for f1, f2 in [(0.60, 1.20), (1.80, 3.50)]:
            print(f"      ratio CIs {f1}-{f2} Hz: " + "  ".join(
                f"{c} x{np.sqrt(perbin(kb,c)['inc'][(FR>=f1)&(FR<f2)].sum()/max(perbin(ka,c)['inc'][(FR>=f1)&(FR<f2)].sum(),1e-300)):.2f}"
                f"[{boot_ratio(kb,ka,c,f1,f2)[0]:.2f},{boot_ratio(kb,ka,c,f1,f2)[1]:.2f}]" for c in CH))

    print("\n" + "=" * 170)
    print("1b. SAME but the TOTAL spectrum (not just the incoherent part) -- to check the incoherent split is not")
    print("    doing the work by itself")
    print("=" * 170)
    for i, (dlo, dhi) in [(1, (0.004, 0.018)), (2, (0.004, 0.026))]:
        ka = sel("E", i, ["V282"], dmin=dlo, dmax=dhi); kb = sel("E", i, TORQ, dmin=dlo, dmax=dhi)
        show_shape(f"speed {SPDN[i]} m/s TOTAL power", ka, kb, comp="tot")

    print("\n" + "=" * 170)
    print("3b. DOES THE PEAK MOVE WITH SPEED?  Peak of the TORQ/V282 incoherent RATIO and of the TORQ incoherent")
    print("    spectrum itself, on a fine 0.0977 Hz grid, 0.4-4.5 Hz, per speed bin, channel R (steering rate)")
    print("    and channel Y (achieved yaw accel).")
    print("=" * 170)
    for ch in ["R", "A", "Y", "U"]:
        print(f"\n   channel {ch}")
        print(f"    {'speed':7s} {'TORQ peak f':>12s} {'ratio peak f':>13s} {'ratio@0.6-1.2':>14s} {'ratio@1.8-3.5':>14s}")
        for i in (0, 1, 2, 3):
            dlo, dhi = (0.004, 0.026)
            ka = sel("E", i, ["V282"], dmin=dlo, dmax=dhi); kb = sel("E", i, TORQ, dmin=dlo, dmax=dhi)
            if len(ka) < 6 or len(kb) < 6:
                print(f"    {SPDN[i]:7s}  n<6 (V282 {len(ka)}, TORQ {len(kb)})"); continue
            pa = perbin(ka, ch)["inc"]; pb = perbin(kb, ch)["inc"]
            m = (FR >= 0.40) & (FR <= 4.50)
            rt = np.where(m, pb / np.maximum(pa, 1e-300), 0.0)
            fp_t = FR[np.argmax(np.where(m, pb, 0))]
            fp_r = FR[np.argmax(rt)]
            r1 = np.sqrt(pb[(FR >= .6) & (FR < 1.2)].sum() / max(pa[(FR >= .6) & (FR < 1.2)].sum(), 1e-300))
            r2 = np.sqrt(pb[(FR >= 1.8) & (FR < 3.5)].sum() / max(pa[(FR >= 1.8) & (FR < 3.5)].sum(), 1e-300))
            print(f"    {SPDN[i]:7s} {fp_t:12.3f} {fp_r:13.3f} {r1:14.2f} {r2:14.2f}")

    print("\n" + "=" * 170)
    print("4. LOOP-OPEN CONTROL: DISENGAGED windows, matched on speed and wheel-angle p95.  If the object is")
    print("   present with the loop open at the same size, it is not the controller's.")
    print("   Total (not incoherent) band RMS, because with the loop open the demand drives nothing.")
    print("=" * 170)
    AE = [(0, 5), (5, 12), (12, 25), (25, 400)]
    for i in (1, 2, 3):
        print(f"\n   speed {SPDN[i]} m/s")
        print(f"    {'sa95':>10s} {'class':>7s} {'group':7s} {'n':>4s} " +
              " ".join(f"{c+' .6-1.2':>12s} {c+' 1.8-3.5':>12s}" for c in ["R", "A", "Y"]))
        for alo, ahi in AE:
            for g, mem in [("V282", ["V282"]), ("TORQ", TORQ)]:
                for cl in ("E", "D"):
                    k = sel(cl, i, mem, amin=alo, amax=ahi)
                    if len(k) < 5:
                        continue
                    row = f"    {alo:3d}-{ahi:3d}   {cl:>7s} {g:7s} {len(k):4d} "
                    for c in ["R", "A", "Y"]:
                        p = perbin(k, c)["tot"]
                        row += f" {np.sqrt(p[(FR>=.6)&(FR<1.2)].sum()):12.4f} {np.sqrt(p[(FR>=1.8)&(FR<3.5)].sum()):12.4f}"
                    print(row)


if __name__ == "__main__":
    main()
