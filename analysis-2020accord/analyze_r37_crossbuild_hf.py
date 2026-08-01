#!/usr/bin/env python3
"""Is the >26 Hz torsion-bar activity on V62 (route 37) NEW, or was it always there?

Runs one identical detector over every cached route the kit holds. Nothing here depends on the
operator's memory of when the grinding happened -- it is a whole-route census.

  route 2b / 2c : earlier builds (see docs/BUILD-LINEAGE.md)
  route 31      : V61
  route 35      : V64 (spectrally identical to V59 -- the detector never armed)
  route 37      : V62   <- the build under test

Detector: NFFT=256, hop=64, per-window 26-45 Hz analytic envelope p99 on `tq`, plus the free
26-45 Hz peak with its local prominence and Q. Reported as a distribution, not a single number,
because the phenomenon is bursty. Exposure differs sharply between routes, so counts are ALSO
given as a rate per 1000 windows.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _r31_common as C  # noqa: E402

NFFT = 256
B_HI = (26.0, 45.0)

ROUTES = [
    ("2b", C.ROOT / "_cache_r2b", "r2bs", [0, 1, 2, 11, 12, 13]),
    ("2c", C.ROOT / "_cache_r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12]),
    ("31 (V61)", C.ROOT / "_cache_r31", "r31s", [0, 1, 2, 3]),
    ("35 (V64=V59)", C.ROOT / "_cache_r35", "r35s", [0, 1, 2]),
    ("37 (V62)", C.ROOT / "_cache_r37", "r37s", list(range(1, 15))),
]


def scan(cache, pfx, segs):
    rows = []
    for s in segs:
        f = cache / f"{pfx}{s}.npz"
        if not f.exists():
            continue
        d = C.load(s, cache, pfx)
        fs = C.fs_of(d)
        x = d["tq"]
        if len(x) < NFFT:
            continue
        ehi = C.band_envelope(x, fs, *B_HI)
        ff = np.fft.rfftfreq(NFFT, 1 / fs)
        for i in range(0, len(x) - NFFT + 1, NFFT // 4):
            P = C.periodogram(x[i:i + NFFT], fs, NFFT)
            if P is None:
                continue
            sl = slice(i, i + NFFT)
            fh, ph = C.peak_prom(ff, P, *B_HI)
            rows.append((float(np.percentile(ehi[sl], 99)), fh, ph,
                         C.q_of(ff, P, fh) if np.isfinite(fh) else np.nan,
                         float(np.mean(d["cs_v"][sl])),
                         float(np.mean(d["cc_lat"][sl] > 0.5)),
                         float(np.max(np.abs(np.diff(x[sl])))), s, float(d["t"][i]), fs))
    return rows


def main():
    print(f"26-45 Hz TORSION-BAR ENVELOPE, one detector across every cached route "
          f"(NFFT={NFFT}, hop=64)\n")
    print(f"{'route':14s} {'nwin':>5s} {'fs':>6s} | {'env p50':>8s} {'p90':>7s} {'p99':>8s} "
          f"{'max':>8s} | {'>500':>6s} {'>900':>6s} {'>2000':>6s} | {'per-1000 windows':>18s} | "
          f"{'maxjump':>8s} {'f@max':>6s} {'Q@max':>6s}")
    store = {}
    for name, cache, pfx, segs in ROUTES:
        r = scan(cache, pfx, segs)
        store[name] = r
        if not r:
            print(f"{name:14s} (no data)")
            continue
        e = np.array([x[0] for x in r])
        jm = np.array([x[6] for x in r])
        k = int(np.argmax(e))
        n5, n9, n20 = int((e > 500).sum()), int((e > 900).sum()), int((e > 2000).sum())
        print(f"{name:14s} {len(r):5d} {r[0][9]:6.2f} | {np.median(e):8.1f} "
              f"{np.percentile(e,90):7.1f} {np.percentile(e,99):8.1f} {e.max():8.1f} | "
              f"{n5:6d} {n9:6d} {n20:6d} | "
              f">500 {1000*n5/len(r):6.1f}  >900 {1000*n9/len(r):5.1f} | "
              f"{jm.max():8.0f} {r[k][1]:6.2f} {r[k][3]:6.1f}")

    # ---- where does the 26-45 Hz peak SIT on each route? -------------------------------------
    print("\nFree 26-45 Hz argmax, restricted to windows whose 26-45 envelope is in that route's "
          "top decile:")
    print(f"{'route':14s} {'n':>4s} | {'f med':>6s} {'f sd':>6s} | histogram, 2 Hz bins "
          "26|28|30|32|34|36|38|40|42|44")
    for name, r in store.items():
        if not r:
            continue
        e = np.array([x[0] for x in r])
        thr = np.percentile(e, 90)
        top = [x for x in r if x[0] >= thr and np.isfinite(x[1])]
        fv = np.array([x[1] for x in top])
        h, _ = np.histogram(fv, bins=np.arange(26, 47, 2))
        print(f"{name:14s} {len(top):4d} | {np.median(fv):6.2f} {fv.std(ddof=1):6.2f} | " +
              " ".join(f"{v:3d}" for v in h))

    # ---- worst single window on each route ---------------------------------------------------
    print("\nWorst single window per route:")
    print(f"{'route':14s} {'seg':>4s} {'t0':>7s} {'env':>8s} {'f':>6s} {'prom':>7s} {'Q':>6s} "
          f"{'v':>6s} {'lat':>4s} {'maxjump':>8s}")
    for name, r in store.items():
        if not r:
            continue
        x = max(r, key=lambda z: z[0])
        print(f"{name:14s} {x[7]:4d} {x[8]:7.2f} {x[0]:8.1f} {x[1]:6.2f} {x[2]:7.2f} {x[3]:6.1f} "
              f"{x[4]:6.2f} {x[5]:4.2f} {x[6]:8.0f}")

    # ---- large single-sample jumps: a build-independent, FFT-free second method ---------------
    print("\nSecond method (no FFT): count of single-sample |d(tq)| jumps, per 1000 samples.")
    print(f"{'route':14s} {'nsamp':>7s} | {'>800':>8s} {'>1500':>8s} {'>2500':>8s} | "
          f"{'rate>1500':>10s}")
    for name, cache, pfx, segs in ROUTES:
        tot = j8 = j15 = j25 = 0
        for s in segs:
            f = cache / f"{pfx}{s}.npz"
            if not f.exists():
                continue
            d = C.load(s, cache, pfx)
            dd = np.abs(np.diff(d["tq"]))
            tot += len(dd)
            j8 += int((dd > 800).sum())
            j15 += int((dd > 1500).sum())
            j25 += int((dd > 2500).sum())
        if tot:
            print(f"{name:14s} {tot:7d} | {j8:8d} {j15:8d} {j25:8d} | {1000*j15/tot:10.3f}")


if __name__ == "__main__":
    main()
