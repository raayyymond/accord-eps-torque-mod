# -*- coding: utf-8 -*-
"""REGIME B stage 4: discriminate the candidates with structure.

b2: at MATCHED in-band demand RMS the 0.60-1.20 Hz coherent gain gap is gone (both builds read the same
|H|); what survives is the INCOHERENT part, x1.3-2.9 in the yaw and x3-5 in the wheel.
b3: the wheel-channel excess ratio climbs monotonically from 0.3 Hz to a maximum at 1.8-2.7 Hz -- there is
no separate 0.6-1.2 Hz feature in the wheel; in the yaw the ratio instead FALLS with frequency.

This script tests the readings that would each name a different owner:

  T3  Is the yaw excess at 0.6-1.2 Hz just the WHEEL excess transmitted?  Measure the wheel->yaw transfer
      |P_AY|/P_AA per build per speed from the data, and ask whether the measured yaw excess equals the
      measured wheel excess times that transfer.  If yes, Regime B is not a yaw-side object at all.
  T4  Does the demand-unexplained wheel motion SCALE WITH DEMAND (nonlinear response to the demand) or sit
      at a demand-independent FLOOR (road / free-running limit cycle)?  Per-window regression of the
      residual band RMS on the demand band RMS, slope + intercept, route-cluster CIs, held-out transfer.
  T5  How much of the residual wheel motion is linearly predictable from the COMMAND (partial coherence of
      A on U with the demand removed)?  Loop-generated vs plant/road.
  T7  Does its frequency move with speed?  Spectral centroid and peak of the residual wheel spectrum.
  T8  CANDIDATE (iv): is there a 0.4-1 Hz GAIN BUMP in the fork's own setpoint stage?  Measure |H_XZ|(f)
      per fork rev -- the delay canceller and its jerk filter F_j live entirely inside that transfer.

MEASUREMENT of logged channels.  No simulator, no chained model prediction.
ANALYSIS ONLY, read-only.  usage: python b4_mechanism.py > B4-OUT.txt
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
NRM1 = 16.0 / (3.0 * (W * 100.0) ** 2)          # per-window Hann band-RMS^2 scale
rng = np.random.default_rng(31)
FBINS = [(0.30, 0.45), (0.45, 0.60), (0.60, 0.80), (0.80, 1.00), (1.00, 1.20), (1.20, 1.50),
         (1.50, 1.80), (1.80, 2.20), (2.20, 2.70), (2.70, 3.30), (3.30, 4.00)]


def brms(C, f1, f2):
    s = (FR >= f1) & (FR < f2)
    return np.sqrt((np.abs(C[:, s]) ** 2).sum(1) * NRM1)


def sel(cls, sbin, grp, dmin=None, dmax=None):
    m = (D["cls"] == cls) & (D["sbin"] == sbin) & np.isin(D["group"], grp)
    if dmin is not None:
        d = brms(D["X"], 0.6, 1.2); m &= (d >= dmin) & (d < dmax)
    return np.flatnonzero(m)


def pooled(idx, a, b):
    A = D[a][idx]; B = D[b][idx]
    return ((np.abs(A) ** 2).sum(0), (np.abs(B) ** 2).sum(0), (np.conj(A) * B).sum(0))


def inc_spec(idx, ch):
    Pxx, Pcc, Pxc = pooled(idx, "X", ch)
    return np.maximum(Pcc - np.abs(Pxc) ** 2 / np.maximum(Pxx, 1e-300), 0) / len(idx) * NRM1


def bandsum(sp, f1, f2):
    s = (FR >= f1) & (FR < f2)
    return float(sp[s].sum())


DSEL = {1: (0.004, 0.018), 2: (0.004, 0.026), 3: (0.008, 0.040)}


def t3_transmission():
    print("=" * 140)
    print("T3. IS THE YAW EXCESS THE WHEEL EXCESS, TRANSMITTED?")
    print("    G_AY(f) = |P_AY|/P_AA measured on each build's own engaged windows (wheel angle -> achieved")
    print("    lateral accel).  It is a vehicle property, so it should agree between builds; it is printed")
    print("    for both.  Predicted yaw excess = G_AY * (wheel excess), where 'excess' = sqrt(P_torque - P_V282)")
    print("    of the demand-incoherent part.  Compared against the MEASURED yaw excess.")
    print("=" * 140)
    for i in (1, 2, 3):
        dlo, dhi = DSEL[i]
        ka = sel("E", i, ["V282"], dlo, dhi); kb = sel("E", i, TORQ, dlo, dhi)
        print(f"\n  speed {SPDN[i]} m/s   V282 n={len(ka)}  TORQ n={len(kb)}   (matched in-band demand RMS {dlo}-{dhi})")
        print(f"   {'band Hz':>11s} {'G_AY V282':>10s} {'G_AY TORQ':>10s} {'A excess deg':>13s} "
              f"{'Y excess pred':>14s} {'Y excess meas':>14s} {'meas/pred':>10s}")
        for f1, f2 in FBINS:
            s = (FR >= f1) & (FR < f2)
            g = {}
            for nm, k in (("V", ka), ("T", kb)):
                Paa, Pyy, Pay = pooled(k, "A", "Y")
                g[nm] = float(np.average(np.abs(Pay[s]) / np.maximum(Paa[s], 1e-300), weights=Paa[s]))
            ia, ib = inc_spec(ka, "A"), inc_spec(kb, "A")
            ya, yb = inc_spec(ka, "Y"), inc_spec(kb, "Y")
            dA = max(bandsum(ib, f1, f2) - bandsum(ia, f1, f2), 0) ** 0.5
            dY = max(bandsum(yb, f1, f2) - bandsum(ya, f1, f2), 0) ** 0.5
            pred = g["V"] * dA
            print(f"   {f1:.2f}-{f2:.2f}   {g['V']:10.4f} {g['T']:10.4f} {dA:13.4f} {pred:14.4f} {dY:14.4f} "
                  f"{(dY/pred if pred > 1e-9 else float('nan')):10.2f}")


def resid_rms(idx, ch, f1, f2, fit_idx=None):
    """Per-window band RMS of the channel AFTER removing the best linear prediction from the demand.
    The transfer is fitted on fit_idx (a disjoint half) so the residual is not shrunk by overfitting."""
    fi = fit_idx if fit_idx is not None else idx
    Pxx, _, Pxc = pooled(fi, "X", ch)
    T = Pxc / np.maximum(Pxx, 1e-300)
    R = D[ch][idx] - T[None, :] * D["X"][idx]
    s = (FR >= f1) & (FR < f2)
    return np.sqrt((np.abs(R[:, s]) ** 2).sum(1) * NRM1)


def t4_scaling():
    print("\n" + "=" * 140)
    print("T4. DOES THE DEMAND-UNEXPLAINED WHEEL MOTION SCALE WITH THE DEMAND?")
    print("    y = residual wheel-angle band RMS (deg), x = in-band demand RMS (m/s^2), per 10.24 s window.")
    print("    Transfer for the residual fitted on the ODD windows, residual evaluated on the EVEN ones.")
    print("    A demand-PROPORTIONAL object has slope >> 0 and intercept ~ 0 (the demand generates it, but")
    print("    not linearly/phase-locked).  A road floor or a free-running limit cycle is the opposite.")
    print("=" * 140)
    for band in [(0.60, 1.20), (1.80, 3.50)]:
        print(f"\n  band {band[0]}-{band[1]} Hz")
        print(f"   {'speed':7s} {'group':8s} {'n':>4s} {'slope deg/(m/s2)':>17s} {'[95% CI]':>17s} "
              f"{'intercept deg':>14s} {'[95% CI]':>17s} {'R2':>5s} {'frac from slope @median':>24s}")
        for i in (1, 2, 3):
            dlo, dhi = DSEL[i]
            for g, mem in [("V282", ["V282"]), ("TORQ", TORQ)]:
                k = sel("E", i, mem, dlo, dhi)
                if len(k) < 12:
                    continue
                ev, od = k[0::2], k[1::2]
                y = resid_rms(ev, "A", band[0], band[1], fit_idx=od)
                x = brms(D["X"][ev], 0.6, 1.2)
                Amat = np.vstack([x, np.ones_like(x)]).T
                sl, ic = np.linalg.lstsq(Amat, y, rcond=None)[0]
                pr = Amat @ [sl, ic]
                r2 = 1 - ((y - pr) ** 2).sum() / max(((y - y.mean()) ** 2).sum(), 1e-30)
                bs = []
                rts = sorted(set(D["route"][ev]))
                per = {r: ev[D["route"][ev] == r] for r in rts}
                for _ in range(400):
                    kk = np.concatenate([per[r] for r in rng.choice(rts, len(rts))]) if len(rts) >= 2 else ev
                    yy = resid_rms(kk, "A", band[0], band[1], fit_idx=od)
                    xx = brms(D["X"][kk], 0.6, 1.2)
                    Am = np.vstack([xx, np.ones_like(xx)]).T
                    bs.append(np.linalg.lstsq(Am, yy, rcond=None)[0])
                bs = np.array(bs)
                cs, ci_ = np.percentile(bs[:, 0], [2.5, 97.5]), np.percentile(bs[:, 1], [2.5, 97.5])
                xm = float(np.median(x))
                frac = sl * xm / max(sl * xm + ic, 1e-12)
                print(f"   {SPDN[i]:7s} {g:8s} {len(ev):4d} {sl:17.2f} [{cs[0]:7.2f},{cs[1]:7.2f}] "
                      f"{ic:14.4f} [{ci_[0]:7.4f},{ci_[1]:7.4f}] {r2:5.2f} {frac*100:23.0f}%")


def t5_command():
    print("\n" + "=" * 140)
    print("T5. HOW MUCH OF THE RESIDUAL WHEEL MOTION IS LINEARLY PREDICTABLE FROM THE COMMAND?")
    print("    Partial coherence of wheel angle A on command U with the demand X projected out of both.")
    print("    High => the wheel residual and the command residual move together (loop-borne).")
    print("    Low  => the wheel is moving in a way the command does not contain (plant / road / friction")
    print("    breakaway between command samples).   |T_UA| is each build's own command->wheel size; it is")
    print("    NOT comparable across builds (V282's command is a RATE request, torque mode's is a TORQUE")
    print("    request), so read the coherence, not the gain.")
    print("=" * 140)
    for i in (1, 2, 3):
        dlo, dhi = DSEL[i]
        print(f"\n  speed {SPDN[i]} m/s")
        print(f"   {'band Hz':>11s} " + " ".join(f"{g+' coh2  |T|':>22s}" for g in ("V282", "TORQ")))
        ka = sel("E", i, ["V282"], dlo, dhi); kb = sel("E", i, TORQ, dlo, dhi)
        for f1, f2 in FBINS:
            s = (FR >= f1) & (FR < f2)
            row = f"   {f1:.2f}-{f2:.2f}   "
            for k in (ka, kb):
                Pxx, _, Pxu = pooled(k, "X", "U")
                _, _, Pxa = pooled(k, "X", "A")
                Tu = Pxu / np.maximum(Pxx, 1e-300); Ta = Pxa / np.maximum(Pxx, 1e-300)
                Ur = D["U"][k] - Tu[None, :] * D["X"][k]
                Ar = D["A"][k] - Ta[None, :] * D["X"][k]
                Puu = (np.abs(Ur) ** 2).sum(0); Paa = (np.abs(Ar) ** 2).sum(0)
                Pua = (np.conj(Ur) * Ar).sum(0)
                c2 = np.abs(Pua) ** 2 / np.maximum(Puu * Paa, 1e-300)
                T = np.abs(Pua) / np.maximum(Puu, 1e-300)
                row += f" {float(np.average(c2[s], weights=Puu[s])):9.2f} {float(np.average(T[s], weights=Puu[s])):11.1f}"
            print(row)
        n_ind = max(2, len(kb) // 2)
        print(f"     (95% null floor for coherence^2 at n_ind~{n_ind}: {1-0.05**(1/max(n_ind-1,1)):.3f})")


def t7_frequency():
    print("\n" + "=" * 140)
    print("T7. DOES THE OBJECT'S FREQUENCY MOVE WITH SPEED?  Spectral centroid and peak of the demand-")
    print("    incoherent WHEEL-ANGLE spectrum, 0.4-4.0 Hz, per speed bin, both builds, matched demand.")
    print("    A plant/tyre/body mode moves with speed; a steering-column mode and a fork filter do not.")
    print("=" * 140)
    print(f"   {'speed':7s} {'group':8s} {'n':>4s} {'centroid Hz':>12s} {'peak Hz':>9s} {'excess centroid Hz':>19s}")
    for i in (0, 1, 2, 3):
        dlo, dhi = DSEL.get(i, (0.004, 0.026))
        ka = sel("E", i, ["V282"], dlo, dhi); kb = sel("E", i, TORQ, dlo, dhi)
        if len(ka) < 6 or len(kb) < 6:
            print(f"   {SPDN[i]:7s} n<6 (V282 {len(ka)}, TORQ {len(kb)})"); continue
        m = (FR >= 0.40) & (FR <= 4.00)
        pa, pb = inc_spec(ka, "A"), inc_spec(kb, "A")
        ex = np.maximum(pb - pa, 0)
        for nm, p, n in (("V282", pa, len(ka)), ("TORQ", pb, len(kb))):
            cen = float((FR[m] * p[m]).sum() / p[m].sum()); pk = float(FR[m][np.argmax(p[m])])
            exc = float((FR[m] * ex[m]).sum() / max(ex[m].sum(), 1e-300))
            print(f"   {SPDN[i]:7s} {nm:8s} {n:4d} {cen:12.3f} {pk:9.3f} {exc:19.3f}")


def t8_setpoint():
    print("\n" + "=" * 140)
    print("T8. CANDIDATE (iv): THE FORK'S OWN SETPOINT STAGE.  |H_XZ|(f) = |P_XZ|/P_XX, model demand ->")
    print("    the controller's logged shaped setpoint.  The delay canceller, its jerk filter F_j and the")
    print("    AccordRefFilter all live inside this one transfer, so a 0.4-1 Hz gain bump would appear here.")
    print("    Read as SHAPE vs frequency, per fork rev (rev 6.4 = T64/T64B, jerk LP 4.0 Hz; T5/T4/T3/T2 =")
    print("    earlier revs at 1.2 Hz; V282 = the reference-era commits, no Accord ref filter at all).")
    print("=" * 140)
    for i in (2, 3):
        print(f"\n  speed {SPDN[i]} m/s, hands-off engaged, all amplitudes")
        grps = [("V282", ["V282"]), ("T64F", ["T64", "T64B"]), ("T5", ["T5"]), ("T4", ["T4"]),
                ("T3", ["T3"]), ("T2", ["T2"])]
        print(f"   {'band Hz':>11s} " + " ".join(f"{g:>13s}" for g, _ in grps))
        print(f"   {'':>11s} " + " ".join(f"{'|H| lag_ms':>13s}" for _ in grps))
        for f1, f2 in [(0.10, 0.20), (0.20, 0.30), (0.30, 0.45), (0.45, 0.60), (0.60, 0.80),
                       (0.80, 1.00), (1.00, 1.20), (1.20, 1.50), (1.50, 2.00)]:
            s = (FR >= f1) & (FR < f2)
            row = f"   {f1:.2f}-{f2:.2f}   "
            for g, mem in grps:
                k = sel("E", i, mem)
                if len(k) < 6:
                    row += f" {'--':>12s}"; continue
                Pxx, Pzz, Pxz = pooled(k, "X", "Z")
                H = float(np.average(np.abs(Pxz[s]) / np.maximum(Pxx[s], 1e-300), weights=Pxx[s]))
                fc = float(np.average(FR[s], weights=Pxx[s]))
                ph = float(np.angle((Pxz[s] * Pxx[s]).sum()))
                lag = -np.degrees(ph) / 360.0 / max(fc, 1e-9) * 1000
                row += f" {H:6.3f}{lag:7.0f}"
            print(row)
        print("   n: " + " ".join(f"{g}={len(sel('E', i, mem))}" for g, mem in grps))


if __name__ == "__main__":
    t3_transmission(); t4_scaling(); t5_command(); t7_frequency(); t8_setpoint()
