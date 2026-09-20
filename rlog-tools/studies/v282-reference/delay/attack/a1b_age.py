"""ADVERSARY a1b: the SAMPLE AGE leg (claimed 7.59 ms), measured my own way.

The global lower-envelope clock fit is fragile over 6 minutes (one mis-rounded drop tilts it), so do it
LOCALLY: windows of N consecutive 0x14A frames with no drop, LP-fit t_true = a + T*i inside the window,
lag = batch stamp - true arrival. Report E[lag] over windows, plus the batch-occupancy structure that
explains it (if the EPS clock and pandad's poll clock are incommensurate, E[lag] -> half the poll interval).
Also settle the carState<->0x14A payload identity (byte offset / scale / sign) by regression.
"""
import sys
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent / "out"


def local_lag(tb, W=200, Tlo=None, Thi=None):
    """E[batch stamp - true arrival] from windowed LP fits. Splits at any gap > 1.5 median."""
    Tg = np.median(np.diff(tb))
    lags, Ts = [], []
    brk = np.where(np.diff(tb) > 1.5 * Tg)[0]
    segs, s0 = [], 0
    for b in brk:
        segs.append((s0, b + 1)); s0 = b + 1
    segs.append((s0, len(tb)))
    for a0, a1 in segs:
        for i in range(a0, a1 - W, W):
            x = tb[i:i + W]
            ii = np.arange(W, dtype=np.float64)
            best = (np.inf, None)
            for T in np.arange(Tg - 3e-4, Tg + 3e-4, 5e-7):
                a = np.min(x - T * ii)
                r = np.mean(x - T * ii - a)
                if r < best[0]:
                    best = (r, T)
            lags.append(best[0]); Ts.append(best[1])
    return np.array(lags), np.array(Ts)


def main(route):
    D = np.load(OUT / f"raw_{route}.npz")
    cb, addr, src, bi, idxin = D["cb"], D["cf_addr"], D["cf_src"], D["cf_bi"], D["cf_idx"]
    t_cst, sa, sr = D["t_cst"], D["sa"], D["sr"]
    s14 = (addr == 0x14A) & (src == 1)
    tb14, b0, b1 = cb[bi[s14]], D["cf_b0"][s14], D["cf_b1"][s14]
    print(f"=== {route}  n(0x14A)={len(tb14)} ===")

    # --- payload identity ---
    k = np.searchsorted(tb14, t_cst, side="right") - 1
    g = k >= 2
    for nm, raw in (("i16[0:2]*0.1", b0 * 0.1), ("i16[2:4]*0.1", b1 * 0.1)):
        for L in (0, 1):
            x, y = raw[k[g] - L], sa[g]
            A = np.polyfit(x, y, 1)
            r = y - (A[0] * x + A[1])
            print(f"  carState.sa vs 0x14A {nm} {L}-back: slope {A[0]:+.5f} off {A[1]:+.4f} "
                  f"resid rms {r.std():.4f} deg  frac|r|<0.05 {np.mean(np.abs(r)<0.05):.5f}")
    # best: fixed offset from the identity above, then which frame does carState carry?
    sgn = np.sign(np.polyfit(b0[k[g]] * 0.1, sa[g], 1)[0])
    print(f"  sign {sgn:+.0f}: carState.sa = {sgn:+.0f} * 0.1 * i16(0x14A[0:2])")
    for L in (0, 1, 2):
        r = np.abs(sa[g] - sgn * b0[k[g] - L] * 0.1)
        print(f"    {L}-back: frac|err|<0.001 {np.mean(r<1e-3):.5f}  median|err| {np.median(r):.4f} deg")

    # --- batch occupancy ---
    nb_of = np.bincount(bi[s14])
    occ = nb_of[nb_of > 0]
    vals, cnt = np.unique(occ, return_counts=True)
    print(f"  0x14A frames per can batch: {dict(zip(vals.tolist(), (cnt/cnt.sum()).round(4).tolist()))}")
    dbatch = np.diff(np.unique(cb))
    dbatch = dbatch[(dbatch > 0) & (dbatch < 0.04)]
    print(f"  poll (can batch) interval median {np.median(dbatch)*1e3:.4f} ms, mean {dbatch.mean()*1e3:.4f}")
    print(f"  0x14A inter-arrival (batch stamps) median {np.median(np.diff(tb14))*1e3:.4f} ms")

    # --- local LP lag ---
    for W in (100, 200, 400):
        lags, Ts = local_lag(tb14, W)
        print(f"  W={W:4d} windows={len(lags)}: E[batch stamp - true arrival] = {lags.mean():.3f} ms-> "
              f"{lags.mean()*1e3:.3f} ms   (median {np.median(lags)*1e3:.3f})  fitted T {np.median(Ts)*1e3:.4f} ms")
    lags, Ts = local_lag(tb14, 200)
    Elag = lags.mean() * 1e3
    bat2cs = np.median((t_cst[g] - tb14[k[g]]) * 1e3)
    print(f"  ==> SAMPLE AGE = E[lag] {Elag:.3f} + batch->carState {bat2cs:.3f} = {Elag+bat2cs:.3f} ms")
    # sanity: uniform-phase prediction
    print(f"  uniform-phase prediction: half the poll interval {np.median(dbatch)*1e3/2:.3f} + {bat2cs:.3f} "
          f"= {np.median(dbatch)*1e3/2+bat2cs:.3f} ms")


if __name__ == "__main__":
    main(sys.argv[1])
