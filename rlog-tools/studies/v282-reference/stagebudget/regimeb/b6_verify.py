# -*- coding: utf-8 -*-
"""REGIME B stage 6: reproduce the original cell, size the named object in NRMSE, and test the stick-slip
signature directly in the time domain.

  V1  REPRODUCE the surface stream's Regime B cell with this stream's independent window store, so the
      dissolution in b2 is a re-read of the SAME number and not a different measurement.
  V2  NRMSE budget at matched demand: M_coh (the goal's own metric) and M_inc, both builds, 0.60-1.20 Hz,
      so the named object can be sized against the gap it is supposed to own.
  V3  THE STICK-SLIP SIGNATURE.  During a dwell (the wheel not moving) does the COMMAND keep moving, and
      is the size of the jump that ends the dwell predicted by how far the command travelled during it?
      That is the textbook Coulomb-breakaway test and it does not need a model of the plant.
  V4  Does the jump SIZE scale with the demand, or is it fixed (a fixed breakaway would give a fixed jump)?
  V5  Does the residual envelope follow the demand's RATE or its LEVEL?

MEASUREMENT.  ANALYSIS ONLY, read-only.  usage: python b6_verify.py > B6-OUT.txt
"""
import sys
from pathlib import Path
import numpy as np
from scipy import signal as sg

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V  # noqa: E402

D = np.load(HERE / "b1_spec.npz", allow_pickle=True)
W = float(D["W"][0]); FR = np.arange(D["X"].shape[1]) / W
NRM1 = 16.0 / (3.0 * (W * 100.0) ** 2)
SPDN = ["0-8", "8-15", "15-22", "22+"]
SPD = [(0.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 40.0)]
TORQ = ["T64", "T64B", "T5", "T4", "T3", "T2"]
GRP = {"00000064--ce6b0b0ebb": "V282", "00000065--b9f78988bd": "V282", "0000006c--2bc842dbac": "V282",
       "0000006c--68c6e94b17": "T64", "0000006d--05e83bb04f": "T64", "0000006e--6ca3e014fd": "T64B",
       "00000076--d0b7ea7e4d": "T5", "00000075--6c8687d5bd": "T4", "00000074--2bf17ca67d": "T4",
       "00000072--8001fc3048": "T3", "00000073--79fd149dd8": "T3",
       "00000070--717f5a7866": "T2", "00000071--f2c9d073a3": "T2"}
DSEL = {1: (0.004, 0.018), 2: (0.004, 0.026), 3: (0.008, 0.040)}
rng = np.random.default_rng(59)


def brms(C, f1, f2):
    s = (FR >= f1) & (FR < f2)
    return np.sqrt((np.abs(C[:, s]) ** 2).sum(1) * NRM1)


def cellM(idx, f1=0.60, f2=1.20):
    s = (FR >= f1) & (FR < f2)
    X = D["X"][idx][:, s]; Y = D["Y"][idx][:, s]
    Pxx = (np.abs(X) ** 2).sum(0); Pyy = (np.abs(Y) ** 2).sum(0); Pxy = (np.conj(X) * Y).sum(0)
    w = Pxx; Hb = Pxy / np.maximum(Pxx, 1e-300); aH = np.abs(Hb); ph = np.angle(Hb)
    mg2 = float(np.average((aH - 1) ** 2, weights=w)); mp2 = float(np.average(2 * aH * (1 - np.cos(ph)), weights=w))
    inc = float(np.average(np.maximum(Pyy - np.abs(Pxy) ** 2 / np.maximum(Pxx, 1e-300), 0) /
                           np.maximum(Pxx, 1e-300), weights=w))
    return dict(n=len(idx), H=float(np.average(aH, weights=w)), Mgain=mg2 ** .5, Mphase=mp2 ** .5,
                Mcoh=(mg2 + mp2) ** .5, Minc=inc ** .5, M=(mg2 + mp2 + inc) ** .5,
                sa95=float(np.median(D["sa_p95"][idx])), dmd=float(np.median(brms(D["X"][idx], f1, f2))))


def v1_reproduce():
    print("=" * 130)
    print("V1. REPRODUCTION of the surface stream's Regime B cell from this stream's own window store.")
    print("    Cell = laterally engaged hands-off, speed bin, p95|model lateral accel| >= 1.0 (the A3 stratum).")
    print("    Published (SURFACE-OUT.txt, 0.60-1.20 Hz): 8-15 V282 1.097 / TORQ 2.503 ; 15-22 1.226 / 1.979.")
    print("=" * 130)
    print(f"   {'speed':7s} {'group':8s} {'n':>4s} {'|H| here':>9s} {'published':>10s} {'sa95':>7s} "
          f"{'demand RMS':>11s} {'Mcoh':>6s} {'Minc':>6s}")
    pub = {(1, "V282"): 1.097, (1, "TORQ"): 2.503, (2, "V282"): 1.226, (2, "TORQ"): 1.979}
    for i in (1, 2):
        for g, mem in [("V282", ["V282"]), ("TORQ", TORQ)]:
            k = np.flatnonzero((D["cls"] == "E") & (D["sbin"] == i) & (D["am_p95"] >= 1.0) &
                               np.isin(D["group"], mem))
            c = cellM(k)
            print(f"   {SPDN[i]:7s} {g:8s} {c['n']:4d} {c['H']:9.3f} {pub[(i,g)]:10.3f} {c['sa95']:7.1f} "
                  f"{c['dmd']:11.4f} {c['Mcoh']:6.3f} {c['Minc']:6.3f}")


def v2_budget():
    print("\n" + "=" * 130)
    print("V2. NRMSE BUDGET at 0.60-1.20 Hz on MATCHED in-band demand RMS (the b2 matching).")
    print("    M_coh is the goal's own metric (RMS of achieved-minus-desired that the demand explains, in")
    print("    units of the demand's own in-band RMS); M_inc is the part the demand does not explain.")
    print("=" * 130)
    print(f"   {'speed':7s} {'group':8s} {'n':>4s} {'|H|':>6s} {'Mgain':>6s} {'Mphase':>7s} {'Mcoh':>6s} "
          f"{'Minc':>6s} {'M total':>8s} {'inc share of M^2':>17s}")
    for i in (1, 2, 3):
        dlo, dhi = DSEL[i]
        d = brms(D["X"], 0.6, 1.2)
        for g, mem in [("V282", ["V282"]), ("TORQ", TORQ)]:
            k = np.flatnonzero((D["cls"] == "E") & (D["sbin"] == i) & np.isin(D["group"], mem) &
                               (d >= dlo) & (d < dhi))
            c = cellM(k)
            print(f"   {SPDN[i]:7s} {g:8s} {c['n']:4d} {c['H']:6.3f} {c['Mgain']:6.3f} {c['Mphase']:7.3f} "
                  f"{c['Mcoh']:6.3f} {c['Minc']:6.3f} {c['M']:8.3f} {c['Minc']**2/c['M']**2*100:16.0f}%")


def bp(x, f1, f2):
    return sg.sosfiltfilt(sg.butter(3, [f1, f2], btype="band", fs=100.0, output="sos"), x)


def v345():
    print("\n" + "=" * 130)
    print("V3/V4/V5. STICK-SLIP SIGNATURE, 8-22 m/s, laterally engaged hands-off, matched demand.")
    print("   A dwell = |steering rate| < 1.0 deg/s for >= 0.25 s.  For each dwell that ends in a jump")
    print("   (peak |rate| >= 6 deg/s within 0.6 s) I record: the travel of the COMMAND during the dwell,")
    print("   the travel of the SETPOINT, the jump's peak rate and its angle excursion, and the window's")
    print("   in-band demand RMS.  If the command keeps moving while the wheel does not, and the jump")
    print("   tracks how far it moved, the object is a Coulomb breakaway, not a mode.")
    print("=" * 130)
    rec = {}
    env = {}
    for rk, grp in GRP.items():
        f = V.CACHE / f"{rk}.npz"
        if not f.exists():
            continue
        S = V.load(rk)
        ok = np.isfinite(S["sr"]) & np.isfinite(S["model"]) & np.isfinite(S["v"]) & np.isfinite(S["sa"])
        m = S["active"] & ~S["pressed"] & ok
        n = 1024
        for a, b in V.runs(m, S["t"], min_s=12.0):
            xb = bp(np.nan_to_num(S["model"][a:b]), 0.6, 1.2)
            rb = bp(np.nan_to_num(S["sr"][a:b]), 0.3, 4.0)
            ed = 200
            for k in range(a + ed, b - ed - n + 1, n):
                sl = slice(k, k + n); rel = slice(k - a, k - a + n)
                vv = S["v"][sl]; vm = float(np.median(vv))
                i = next((q for q, (lo, hi) in enumerate(SPD) if lo <= vm < hi), None)
                if i not in (1, 2) or float(np.mean((vv >= SPD[i][0]) & (vv < SPD[i][1]))) < 0.8:
                    continue
                dlo, dhi = DSEL[i]
                dr = float(np.sqrt(np.mean(xb[rel] ** 2)))
                if not (dlo <= dr < dhi):
                    continue
                # V5: does the residual envelope follow the demand's LEVEL or its RATE?
                envl = np.abs(sg.hilbert(rb[rel]))
                mdl = np.nan_to_num(S["model"][sl]); lev = np.abs(mdl - mdl.mean())
                rat = np.abs(np.gradient(mdl) * 100.0)
                lo_ = lambda z: sg.sosfiltfilt(sg.butter(2, 0.3, fs=100.0, output="sos"), z)
                e_, l_, r_ = lo_(envl), lo_(lev), lo_(rat)
                env.setdefault((grp, i), []).append(
                    (rk, float(np.corrcoef(e_, l_)[0, 1]), float(np.corrcoef(e_, r_)[0, 1])))
                sr = np.abs(np.nan_to_num(S["sr"][sl])); u = np.nan_to_num(S["out"][sl])
                z = np.nan_to_num(S["setpoint"][sl]); ang = np.nan_to_num(S["sa"][sl])
                quiet = sr < 1.0
                q = 0
                while q < n:
                    if not quiet[q]:
                        q += 1; continue
                    p = q
                    while p + 1 < n and quiet[p + 1]:
                        p += 1
                    if (p - q) >= 25 and p + 60 < n:
                        pk = float(sr[p + 1:p + 61].max())
                        if pk >= 6.0:
                            rec.setdefault((grp, i), []).append(
                                (rk, float(abs(u[p] - u[q])), float(abs(z[p] - z[q])),
                                 float((p - q) / 100.0), pk,
                                 float(abs(ang[min(p + 60, n - 1)] - ang[p])), dr))
                    q = p + 1
        del S
    print(f"\n V3: {'speed':7s} {'group':8s} {'nep':>5s} {'dwell s':>8s} {'|dU| during dwell':>18s} "
          f"{'|dZ| m/s2':>10s} {'jump deg/s':>11s} {'jump deg':>9s} {'corr(jump,|dU|)':>16s}")
    for i in (1, 2):
        for g, mem in [("V282", ["V282"]), ("TORQ", TORQ)]:
            acc = [r for g2 in mem for r in rec.get((g2, i), [])]
            if len(acc) < 8:
                print(f"     {SPDN[i]:7s} {g:8s} {len(acc):5d}  (too few episodes to characterise)")
                continue
            du = np.array([r[1] for r in acc]); dz = np.array([r[2] for r in acc])
            dw = np.array([r[3] for r in acc]); jp = np.array([r[4] for r in acc])
            ja = np.array([r[5] for r in acc]); dm = np.array([r[6] for r in acc])
            print(f"     {SPDN[i]:7s} {g:8s} {len(acc):5d} {np.median(dw):8.2f} {np.median(du):18.4f} "
                  f"{np.median(dz):10.4f} {np.median(jp):11.1f} {np.median(ja):9.2f} "
                  f"{np.corrcoef(du, jp)[0,1]:16.2f}")
    print("\n V4: jump size vs the window's in-band demand RMS (torque mode, pooled 8-22 m/s)")
    acc = [r for g2 in TORQ for i in (1, 2) for r in rec.get((g2, i), [])]
    if acc:
        dm = np.array([r[6] for r in acc]); jp = np.array([r[4] for r in acc]); ja = np.array([r[5] for r in acc])
        du = np.array([r[1] for r in acc])
        for lo, hi in [(0.004, 0.008), (0.008, 0.012), (0.012, 0.018), (0.018, 0.026), (0.026, 0.100)]:
            s = (dm >= lo) & (dm < hi)
            if s.sum() < 5:
                continue
            print(f"     demand {lo:.3f}-{hi:.3f}: n {s.sum():4d}  p50 jump {np.median(jp[s]):6.1f} deg/s  "
                  f"p90 {np.percentile(jp[s],90):6.1f}  p50 angle excursion {np.median(ja[s]):5.2f} deg  "
                  f"p50 |dU| {np.median(du[s]):.4f}")
    print("\n V5: correlation of the 0.3-4 Hz residual ENVELOPE with the demand's LEVEL vs its RATE")
    print(f"     {'speed':7s} {'group':8s} {'nblk':>5s} {'corr with |demand|':>19s} {'corr with |d demand/dt|':>24s}")
    for i in (1, 2):
        for g, mem in [("V282", ["V282"]), ("TORQ", TORQ)]:
            acc = [r for g2 in mem for r in env.get((g2, i), [])]
            if len(acc) < 8:
                continue
            cl = np.array([r[1] for r in acc]); cr = np.array([r[2] for r in acc])
            print(f"     {SPDN[i]:7s} {g:8s} {len(acc):5d} {np.nanmedian(cl):19.2f} {np.nanmedian(cr):24.2f}")


if __name__ == "__main__":
    v1_reproduce(); v2_budget(); v345()
