"""AGGREGATE the blocks into the |H| surface (speed x demand AMPLITUDE x frequency) and carry the
covariates every mechanism's signature needs.  MEASUREMENT only -- no model of the car anywhere.

|H| per cell: per-bin H = |sum_blocks Pxy| / sum_blocks Pxx  (the H1 estimator at that frequency),
then averaged ACROSS BINS as MAGNITUDES weighted by input power.  Never a phasor average across bins.
Coherence from the same cross-block sums; the estimator's own upward bias is ~1/n_blocks, printed.
Split-half floor: 200 random block splits (and, where a cell holds >1 route, 200 route-cluster splits);
reported as the median |H_a - H_b| / H_cell.
"""
import sys, json, itertools
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V
from surf import INSTR, BANDS, SPD, OUT

COH_MIN = 0.45
NMIN = 4
rng = np.random.default_rng(7)


def load_all():
    B = {}
    for rk in V.ROUTES:
        p = OUT / f"blocks_{rk}.npz"
        if not p.exists():
            continue
        B[rk] = dict(np.load(p, allow_pickle=True))
    return B


def band_amp(d, key, f1, f2):
    f = d[f"{key}_f"]; s = (f >= f1) & (f < f2); df = f[1] - f[0]
    return np.sqrt(np.sum(d[f"{key}_pxx"][:, s], axis=1) * df), s, df


def cell_H(P):
    """P = list of (pxx, pyy, pxy) per block, already restricted to the band's bins."""
    Pxx = np.sum([p[0] for p in P], axis=0)
    Pyy = np.sum([p[1] for p in P], axis=0)
    Pxy = np.sum([p[2] for p in P], axis=0)
    H = np.abs(Pxy) / np.maximum(Pxx, 1e-30)
    coh = np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-30)
    w = Pxx
    ph = np.degrees(np.angle(Pxy))
    return (float(np.average(H, weights=w)), float(np.average(coh, weights=w)),
            float(np.average(ph, weights=w)), Pxx, Pyy, Pxy)


def build():
    B = load_all()
    groups = {}
    for rk, d in B.items():
        groups.setdefault(str(d["group"][0]), []).append(rk)
    rows = []
    for key in INSTR:
        for f1, f2 in BANDS[key]:
            # pooled amplitude quantile edges per speed bin, over ALL groups (matched bins)
            pool = {si: [] for si in range(len(SPD))}
            per = {}
            for rk, d in B.items():
                amp, s, df = band_amp(d, key, f1, f2)
                vv = d[f"{key}_v"]
                per[rk] = (amp, s, df, vv)
                for si, (lo, hi) in enumerate(SPD):
                    pool[si].extend(amp[(vv >= lo) & (vv < hi)].tolist())
            for si, (lo, hi) in enumerate(SPD):
                pv = np.array(pool[si])
                if len(pv) < 12:
                    continue
                edges = [0.0] + list(np.quantile(pv, [0.35, 0.65, 0.875])) + [np.inf]
                for ai in range(4):
                    for g, rks in groups.items():
                        P, cov, rl = [], [], []
                        for rk in rks:
                            d = B[rk]; amp, s, df, vv = per[rk]
                            m = (vv >= lo) & (vv < hi) & (amp >= edges[ai]) & (amp < edges[ai + 1])
                            idx = np.flatnonzero(m)
                            for j in idx:
                                P.append((d[f"{key}_pxx"][j, s], d[f"{key}_pyy"][j, s], d[f"{key}_pxy"][j, s]))
                                cov.append((rk, amp[j], d[f"{key}_ang_med"][j], d[f"{key}_ang_max"][j],
                                            d[f"{key}_rail"][j], d[f"{key}_i_abs"][j], d[f"{key}_f_abs"][j],
                                            d[f"{key}_p_abs"][j], d[f"{key}_cmd_abs"][j], d[f"{key}_out_p99"][j]))
                            rl.append(None)
                        if len(P) < NMIN:
                            continue
                        H, coh, ph, Pxx, Pyy, Pxy = cell_H(P)
                        # split-half floors
                        sh = []
                        for _ in range(200):
                            pm = rng.permutation(len(P)); h = len(P) // 2
                            if h < 2:
                                break
                            a = cell_H([P[i] for i in pm[:h]])[0]
                            b = cell_H([P[i] for i in pm[h:]])[0]
                            sh.append(abs(a - b))
                        rsplit = np.nan
                        rr = sorted(set(c[0] for c in cov))
                        if len(rr) > 1:
                            tmp = []
                            for _ in range(200):
                                pick = set(rng.choice(rr, max(1, len(rr) // 2), replace=False).tolist())
                                A = [P[i] for i, c in enumerate(cov) if c[0] in pick]
                                Bb = [P[i] for i, c in enumerate(cov) if c[0] not in pick]
                                if len(A) >= 2 and len(Bb) >= 2:
                                    tmp.append(abs(cell_H(A)[0] - cell_H(Bb)[0]))
                            rsplit = float(np.median(tmp)) if tmp else np.nan
                        nblk = len(P)
                        secs = nblk * INSTR[key] / V.FS
                        unexp = float(np.sum((1 - np.clip(np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-30), 0, 1)) * Pyy))
                        cA = np.array([[c[1], c[2], c[3], c[4], c[5], c[6], c[7], c[8], c[9]] for c in cov], float)
                        rows.append(dict(
                            instr=key, band=f"{f1:.2f}-{f2:.2f}", f1=f1, f2=f2, fc=0.5 * (f1 + f2),
                            spd=f"{lo}-{hi}", si=si, ai=ai, amp_lo=float(edges[ai]),
                            amp_hi=(None if not np.isfinite(edges[ai + 1]) else float(edges[ai + 1])),
                            group=g, n=nblk, secs=secs, routes=len(rr),
                            H=H, coh=coh, phase=ph, lag_eq=-ph / (360.0 * (0.5 * (f1 + f2))),
                            floor_split=float(np.median(sh)) if sh else np.nan,
                            floor_route=rsplit, coh_bias=1.0 / nblk,
                            amp_med=float(np.median(cA[:, 0])), ang_med=float(np.median(cA[:, 1])),
                            ang_max=float(np.max(cA[:, 2])), rail_duty=float(np.mean(cA[:, 3])),
                            rail_secs=float(np.sum(cA[:, 3]) * INSTR[key] / V.FS),
                            i_abs=float(np.median(cA[:, 4])), f_abs=float(np.median(cA[:, 5])),
                            p_abs=float(np.median(cA[:, 6])), cmd_abs=float(np.median(cA[:, 7])),
                            out_p99=float(np.median(cA[:, 8])),
                            out_pow=float(np.sum(Pyy)), in_pow=float(np.sum(Pxx)), unexp_pow=unexp))
    json.dump(rows, open(OUT / "surface.json", "w"), indent=1)
    return rows


def show(rows, groups=("V282", "T64", "T64B", "T5", "T4", "V282old")):
    print("\n" + "=" * 132)
    print("|H| SURFACE  model-desired lateral accel -> livePose yaw*v.  x = amplitude bin (in-band demand RMS, m/s^2)")
    print("cells shown only where coherence >= %.2f and n >= %d.  'floor' = median split-half |dH|." % (COH_MIN, NMIN))
    print("=" * 132)
    for key in INSTR:
        for f1, f2 in BANDS[key]:
            bn = f"{f1:.2f}-{f2:.2f}"
            print(f"\n--- band {bn} Hz  (instrument {key}, {INSTR[key]/V.FS:.2f} s blocks) ---")
            print(f"{'speed':7s} {'amp bin':16s} {'n/sec (V282)':14s} " + "".join(f"{g:>18s}" for g in groups))
            for si, (lo, hi) in enumerate(SPD):
                for ai in range(4):
                    sel = [r for r in rows if r["band"] == bn and r["si"] == si and r["ai"] == ai]
                    if not sel:
                        continue
                    ref = next((r for r in sel if r["group"] == "V282"), None)
                    alo = sel[0]["amp_lo"]; ahi = sel[0]["amp_hi"]
                    ab = f"{alo:.3f}-{'inf' if ahi is None else f'{ahi:.3f}'}"
                    line = f"{lo}-{hi:<4d} {ab:16s} "
                    line += f"{(str(ref['n'])+'/'+str(int(ref['secs']))+'s') if ref else '--':14s} "
                    for g in groups:
                        r = next((x for x in sel if x["group"] == g), None)
                        if r is None:
                            line += f"{'--':>18s}"; continue
                        flag = "" if (r["coh"] >= COH_MIN) else "*"
                        line += f"{r['H']:8.2f}{flag:1s}c{r['coh']:.2f}f{r['floor_split']:.2f}"
                    print(line)


if __name__ == "__main__":
    rows = build()
    show(rows)
    print(f"\n{len(rows)} cells written to {OUT/'surface.json'}")
