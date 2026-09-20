# -*- coding: utf-8 -*-
"""REGIME B stage 5: is the demand-proportional wheel residual SMOOTH or INTERMITTENT, and is it narrowband?

T4 found the demand-unexplained wheel motion is PROPORTIONAL TO THE DEMAND on torque mode (slope 6-42
deg per m/s^2 of in-band demand, intercept indistinguishable from zero) while on V282 it is mostly a
demand-INDEPENDENT floor.  That already rules out a road floor and a free-running limit cycle as the
owner.  What remains to separate:
  (a) a lightly damped MODE that the loop de-damps  -> narrowband, a local bump in the spectrum, and a
      near-GAUSSIAN amplitude distribution (kurtosis ~3) since it is a filtered linear response;
  (b) a FRICTION / stick-slip generator                -> broadband with no local bump, and a strongly
      INTERMITTENT amplitude distribution (kurtosis >> 3, high crest factor, dwell-then-jump episodes).

Both are demand-proportional, so the discriminator has to be the SHAPE and the STATISTICS, not the size.

  S1  fine per-bin spectrum of the residual wheel angle, power-law fit over 0.4-4 Hz, and the local bump
      left over; plus spectral concentration (most power in any 0.4 Hz window).
  S2  kurtosis and crest factor of the 0.3-4 Hz band-passed steering RATE, matched on speed and demand,
      route-cluster CIs, with a GAUSSIAN positive control through the identical filter chain.
  S3  dwell-then-jump episodes (the operator's "ratchety snapping") counted at 8-22 m/s hands-off engaged.

MEASUREMENT.  ANALYSIS ONLY, read-only.  usage: python b5_intermittency.py > B5-OUT.txt
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
       "00000039--f56039af87": "V282old", "0000003a--283a39a1d6": "V282old", "0000003c--927965c2b4": "V282old",
       "0000006c--68c6e94b17": "T64", "0000006d--05e83bb04f": "T64", "0000006e--6ca3e014fd": "T64B",
       "00000076--d0b7ea7e4d": "T5", "00000075--6c8687d5bd": "T4", "00000074--2bf17ca67d": "T4",
       "00000072--8001fc3048": "T3", "00000073--79fd149dd8": "T3",
       "00000070--717f5a7866": "T2", "00000071--f2c9d073a3": "T2"}
DSEL = {1: (0.004, 0.018), 2: (0.004, 0.026), 3: (0.008, 0.040)}
rng = np.random.default_rng(47)


def brms(C, f1, f2):
    s = (FR >= f1) & (FR < f2)
    return np.sqrt((np.abs(C[:, s]) ** 2).sum(1) * NRM1)


def sel(i, grp):
    dlo, dhi = DSEL[i]
    d = brms(D["X"], 0.6, 1.2)
    return np.flatnonzero((D["cls"] == "E") & (D["sbin"] == i) & np.isin(D["group"], grp) &
                          (d >= dlo) & (d < dhi))


def inc_spec(idx, ch):
    A = D["X"][idx]; B = D[ch][idx]
    Pxx = (np.abs(A) ** 2).sum(0); Pbb = (np.abs(B) ** 2).sum(0); Pxb = (np.conj(A) * B).sum(0)
    return np.maximum(Pbb - np.abs(Pxb) ** 2 / np.maximum(Pxx, 1e-300), 0) / len(idx) * NRM1


def s1_shape():
    print("=" * 140)
    print("S1. FINE SPECTRUM OF THE RESIDUAL WHEEL ANGLE (demand projected out), 0.39-4.0 Hz, df 0.0977 Hz.")
    print("    A power law a*f^-p is fitted over the whole range in log-log; the printed 'bump' is the")
    print("    measured bin divided by that fit.  A lightly damped MODE shows a contiguous run of bump > 1")
    print("    around one frequency.  Concentration = most power in any 0.4 Hz-wide window / total 0.4-4 Hz.")
    print("=" * 140)
    for i in (1, 2, 3):
        print(f"\n  speed {SPDN[i]} m/s (matched demand {DSEL[i]})")
        ka, kb = sel(i, ["V282"]), sel(i, TORQ)
        m = (FR >= 0.39) & (FR <= 4.0)
        out = {}
        for nm, k in (("V282", ka), ("TORQ", kb)):
            p = inc_spec(k, "A")[m]
            sl, ic = np.polyfit(np.log(FR[m]), np.log(np.maximum(p, 1e-30)), 1)
            fit = np.exp(ic) * FR[m] ** sl
            out[nm] = (p, p / fit, sl, len(k))
            tot = p.sum(); best = max(p[(FR[m] >= f) & (FR[m] < f + 0.4)].sum() for f in np.arange(0.4, 3.7, 0.1))
            out[nm] = out[nm] + (best / tot,)
        print(f"    slope of PSD-power vs f (log-log): V282 {out['V282'][2]:+.2f}  TORQ {out['TORQ'][2]:+.2f}  "
              f"(n {out['V282'][3]}/{out['TORQ'][3]})")
        print(f"    concentration (max power in any 0.4 Hz window / total): V282 {out['V282'][4]:.2f}  "
              f"TORQ {out['TORQ'][4]:.2f}   [a pure sine would read 1.00, white noise ~0.11]")
        print(f"    {'f Hz':>6s} " + " ".join(f"{c:>9s}" for c in
                                              ["V282 pow", "V bump", "TORQ pow", "T bump", "ratio"]))
        for j, f in enumerate(FR[m]):
            if f > 3.6:
                break
            pv, bv = out["V282"][0][j], out["V282"][1][j]
            pt, bt = out["TORQ"][0][j], out["TORQ"][1][j]
            print(f"    {f:6.3f} {pv:9.2e} {bv:9.2f} {pt:9.2e} {bt:9.2f} {pt/max(pv,1e-30):9.2f}")


def bp(x, f1, f2):
    sos = sg.butter(3, [f1, f2], btype="band", fs=100.0, output="sos")
    return sg.sosfiltfilt(sos, x)


def s2_stats():
    print("\n" + "=" * 140)
    print("S2. INTERMITTENCY of the 0.3-4 Hz band-passed steering RATE, laterally engaged hands-off,")
    print("    matched on speed and on the same in-band demand RMS window used everywhere else.")
    print("    kurtosis 3.0 = Gaussian.  crest = p99.9(|x|)/rms.  Blocks of 10.24 s, route-cluster CI.")
    print("=" * 140)
    g = rng.standard_normal(200000)
    gb = bp(g, 0.3, 4.0)
    print(f"    POSITIVE CONTROL: Gaussian noise through the identical filter -> kurtosis "
          f"{float(((gb-gb.mean())**4).mean()/((gb-gb.mean())**2).mean()**2):.2f}, crest "
          f"{float(np.percentile(np.abs(gb),99.9)/gb.std()):.2f}")
    rows = {}
    for rk, grp in GRP.items():
        if grp == "V282old":
            continue
        f = V.CACHE / f"{rk}.npz"
        if not f.exists():
            continue
        S = V.load(rk)
        ok = np.isfinite(S["sr"]) & np.isfinite(S["model"]) & np.isfinite(S["v"])
        m = S["active"] & ~S["pressed"] & ok
        n = 1024
        for a, b in V.runs(m, S["t"], min_s=12.0):
            rb = bp(np.nan_to_num(S["sr"][a:b]), 0.3, 4.0)
            xb = bp(np.nan_to_num(S["model"][a:b]), 0.6, 1.2)
            ed = 200                      # discard 2 s of filter edge at each end
            for k in range(a + ed, b - ed - n + 1, n // 2):
                sl = slice(k, k + n); rel = slice(k - a, k - a + n)
                vv = S["v"][sl]; vm = float(np.median(vv))
                i = next((q for q, (lo, hi) in enumerate(SPD) if lo <= vm < hi), None)
                if i is None or i == 0 or float(np.mean((vv >= SPD[i][0]) & (vv < SPD[i][1]))) < 0.8:
                    continue
                dr = float(np.sqrt(np.mean(xb[rel] ** 2)))
                dlo, dhi = DSEL[i]
                if not (dlo <= dr < dhi):
                    continue
                z = rb[rel]; z = z - z.mean()
                s = z.std()
                if s < 1e-9:
                    continue
                rows.setdefault((grp, i), []).append(
                    (rk, float((z ** 4).mean() / s ** 4), float(np.percentile(np.abs(z), 99.9) / s), s, dr))
        del S
    print(f"\n    {'speed':7s} {'group':8s} {'n blk':>6s} {'rate RMS':>9s} {'kurtosis':>9s} {'[95% CI]':>15s} "
          f"{'crest':>7s} {'[95% CI]':>13s}")
    for i in (1, 2, 3):
        for gname, mem in [("V282", ["V282"]), ("TORQ", TORQ)]:
            acc = [r for g2 in mem for r in rows.get((g2, i), [])]
            if len(acc) < 8:
                continue
            rk_ = np.array([r[0] for r in acc]); ku = np.array([r[1] for r in acc])
            cr = np.array([r[2] for r in acc]); sd = np.array([r[3] for r in acc])
            rts = sorted(set(rk_))
            per = {r: np.flatnonzero(rk_ == r) for r in rts}
            bk, bc = [], []
            for _ in range(400):
                kk = np.concatenate([per[r] for r in rng.choice(rts, len(rts))]) if len(rts) >= 2 else np.arange(len(acc))
                bk.append(np.median(ku[kk])); bc.append(np.median(cr[kk]))
            ck = np.percentile(bk, [2.5, 97.5]); cc = np.percentile(bc, [2.5, 97.5])
            print(f"    {SPDN[i]:7s} {gname:8s} {len(acc):6d} {np.median(sd):9.3f} {np.median(ku):9.2f} "
                  f"[{ck[0]:6.2f},{ck[1]:6.2f}] {np.median(cr):7.2f} [{cc[0]:5.2f},{cc[1]:5.2f}]")


def s3_dwell():
    print("\n" + "=" * 140)
    print("S3. DWELL-THEN-JUMP episodes at 8-22 m/s, laterally engaged hands-off, matched demand.")
    print("    A dwell = |steering rate| < 1.0 deg/s for >= 0.25 s; the jump = peak |rate| in the 0.6 s")
    print("    after it, counted only if it exceeds 6 deg/s.  Rate per 100 s of matched exposure, and the")
    print("    p90 jump.  This is the frequency-domain object read in the time domain.")
    print("=" * 140)
    res = {}
    for rk, grp in GRP.items():
        if grp == "V282old":
            continue
        f = V.CACHE / f"{rk}.npz"
        if not f.exists():
            continue
        S = V.load(rk)
        ok = np.isfinite(S["sr"]) & np.isfinite(S["model"]) & np.isfinite(S["v"])
        m = S["active"] & ~S["pressed"] & ok
        n = 1024
        for a, b in V.runs(m, S["t"], min_s=12.0):
            xb = bp(np.nan_to_num(S["model"][a:b]), 0.6, 1.2)
            ed = 200
            for k in range(a + ed, b - ed - n + 1, n):
                sl = slice(k, k + n); rel = slice(k - a, k - a + n)
                vv = S["v"][sl]; vm = float(np.median(vv))
                i = next((q for q, (lo, hi) in enumerate(SPD) if lo <= vm < hi), None)
                if i is None or i not in (1, 2):
                    continue
                if float(np.mean((vv >= SPD[i][0]) & (vv < SPD[i][1]))) < 0.8:
                    continue
                dlo, dhi = DSEL[i]
                dr = float(np.sqrt(np.mean(xb[rel] ** 2)))
                if not (dlo <= dr < dhi):
                    continue
                sr = np.abs(np.nan_to_num(S["sr"][sl]))
                quiet = sr < 1.0
                jumps = []
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
                            jumps.append(pk)
                    q = p + 1
                key = (grp, i)
                d = res.setdefault(key, dict(sec=0.0, j=[], rt=set()))
                d["sec"] += n / 100.0; d["j"] += jumps; d["rt"].add(rk)
        del S
    print(f"\n    {'speed':7s} {'group':8s} {'sec':>7s} {'episodes/100 s':>15s} {'p50 jump deg/s':>15s} "
          f"{'p90 jump deg/s':>15s} {'routes':>7s}")
    for i in (1, 2):
        for gname, mem in [("V282", ["V282"]), ("TORQ", TORQ)]:
            sec = sum(res.get((g2, i), dict(sec=0))["sec"] for g2 in mem)
            js = [x for g2 in mem for x in res.get((g2, i), dict(j=[]))["j"]]
            rt = set().union(*[res.get((g2, i), dict(rt=set()))["rt"] for g2 in mem]) if mem else set()
            if sec < 60:
                continue
            print(f"    {SPDN[i]:7s} {gname:8s} {sec:7.0f} {len(js)/sec*100:15.2f} "
                  f"{(np.percentile(js,50) if js else float('nan')):15.1f} "
                  f"{(np.percentile(js,90) if js else float('nan')):15.1f} {len(rt):7d}")


if __name__ == "__main__":
    s1_shape(); s2_stats(); s3_dwell()
