#!/usr/bin/env python3
"""What the V64 drive (route `35`) measured, against V61 (route `31`) and V59 (route `2c`).

V64 raised the torsion-bar torque-RATE damping lane (0xC6440 2048->4096, 0xC643E 1536->3072) but
ONLY while the firmware's hard-reversal detector holds gp-0x671a >= 5. V61 zeroed that same lane
unconditionally and made the grinding worse -- so V64 is the opposite direction, applied
conditionally.

METHOD A is `analyze_r31_manual_vs_engaged.py` verbatim (imported, not re-implemented), so the V64
row is produced by the identical code that produced the published V59/V61 rows. The script
re-derives those two rows every run; if they drift from the published table the comparison is void
and that is printed as a FAIL.

METHOD B is an independent second derivation over the same selections: `_r31_common.windows()`
with NFFT=256 (2.56 s vs Method A's 4.0 s), linear detrending (vs mean removal), and a LOCAL
+/-6 Hz prominence floor (vs Method A's global 8-40 Hz median). Nothing is shared but the cache.
Two methods agreeing on frequency and disagreeing on prominence scale is expected and fine; two
methods disagreeing on frequency is a finding.

🛑 Conventions, all load-bearing (docs/STATE.md METHODOLOGY):
  * engagement = carControl.latActive, corroborated by 0x18F byte4 bit3. NEVER cruiseState.enabled.
  * hands-off / effort = |lowpass(tq, 3 Hz)|, never raw |tq|.
  * LOCATE over 12-30 Hz. A pre-restricted 18-26 Hz search pinned V61 to the band edge.
  * prominence (peak / local median), not raw envelope amplitude.
  * average periodograms across DISJOINT runs; never splice.
  * n is reported as independent EPISODES.
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import analyze_r31_manual_vs_engaged as A          # noqa: E402  -- Method A, verbatim
from _r31_common import peak_prom, runs_of, periodogram, sustained, stat  # noqa: E402

SPEED_CAP = 5.35
PUB = {"V59": dict(n=9, peak=21.18, prom=227.0, power=5.26e8),
       "V61": dict(n=3, peak=18.25, prom=486.0, power=4.15e9)}
POOLS = {"V59  route 2c": str(ROOT / "_cache_r2c" / "r2cs*.npz"),
         "V61  route 31": str(ROOT / "_cache_r31" / "r31s*.npz"),
         "V64  route 35": str(ROOT / "_cache_r35" / "r35s*.npz")}


# ---------------------------------------------------------------- Method B ------------------
def _effort(d, fs):
    return np.abs(sustained(d["tq"], fs))


def method_b(pattern, selector, nfft=256, lo=12.0, hi=30.0, chan="tq"):
    """Per-window (f0, prominence) over disjoint runs. Independent of Method A end to end."""
    f0s, proms, nrun, nwin, secs = [], [], 0, 0, 0.0
    for f in sorted(Path(pattern).parent.glob(Path(pattern).name)):
        d = {k: v for k, v in np.load(f).items()}
        fs = 1.0 / np.median(np.diff(d["t"]))
        gear = d["cs_gear"] if "cs_gear" in d else np.full(len(d["t"]), -1.0)
        m = selector(d["cc_lat"] > 0.5, gear, d["cs_v"], _effort(d, fs))
        for a, b in runs_of(m, d["t"], nfft):
            nrun += 1
            secs += (b - a) / fs
            x = d[chan][a:b]
            for i in range(0, len(x) - nfft + 1, nfft):
                P = periodogram(x[i:i + nfft], fs, nfft, True)
                if P is None:
                    continue
                fr = np.fft.rfftfreq(nfft, 1 / fs)
                pk, pr = peak_prom(fr, P, lo, hi)
                if np.isfinite(pk) and np.isfinite(pr):
                    f0s.append(pk); proms.append(pr); nwin += 1
    return dict(f0=np.array(f0s), prom=np.array(proms), nrun=nrun, nwin=nwin, secs=secs)


def b_line(label, r):
    if not r["nwin"]:
        print(f"  {label:34s}  n=0 windows ({r['nrun']} episodes, {r['secs']:.1f} s) -- NOT COMPUTABLE")
        return
    print(f"  {label:34s}  {r['nrun']:2d} episodes {r['secs']:6.1f} s  {r['nwin']:3d} win | "
          f"f0 med {np.median(r['f0']):5.2f} Hz sd {r['f0'].std(ddof=1) if r['nwin']>1 else 0:4.2f} | "
          f"prom med {np.median(r['prom']):7.1f}x p90 {np.percentile(r['prom'],90):8.1f}x "
          f"max {r['prom'].max():8.1f}x")


# ---------------------------------------------------------------- selectors -----------------
# Method A's selector signature is (lat, gear, v); Method B's adds effort. Kept separate rather
# than unified so Method A is imported UNMODIFIED.
creepA = lambda lat, gear, v: lat & (v > 0.3) & (v <= SPEED_CAP)                      # noqa: E731
fwdA = lambda lat, gear, v: ~lat & (gear == 2) & (v > 0.3)                            # noqa: E731
revA = lambda lat, gear, v: ~lat & (gear == 4) & (v > 0.3)                            # noqa: E731

creepB = lambda lat, g, v, e: lat & (v > 0.3) & (v <= SPEED_CAP)                      # noqa: E731
fwdB = lambda lat, g, v, e: ~lat & (g == 2) & (v > 0.3)                               # noqa: E731
fwd1kB = lambda lat, g, v, e: ~lat & (g == 2) & (v > 0.3) & (e >= 1000)               # noqa: E731
revB = lambda lat, g, v, e: ~lat & (g == 4) & (v > 0.3)                               # noqa: E731
nearstatB = lambda lat, g, v, e: ~lat & (np.abs(v) <= 0.6) & (e >= 2200) & (e <= 3300)  # noqa: E731


def main():
    print("=" * 104)
    print("0.  METHOD-A REPRODUCTION CHECK -- do the published V59/V61 rows come back out?")
    print("=" * 104)
    got = {}
    for label, pat in POOLS.items():
        arrs, fs = A._pool(pat, creepA)
        got[label] = A._report(label, arrs, fs)
    for key, lab in (("V59", "V59  route 2c"), ("V61", "V61  route 31")):
        p, g = PUB[key], got[lab]
        ok = (abs(g["peak"] - p["peak"]) < 0.06 and abs(g["prom"] / p["prom"] - 1) < 0.03
              and abs(g["power"] / p["power"] - 1) < 0.03 and g["n"] == p["n"])
        print(f"  {'PASS' if ok else 'FAIL'}  {key}: published n={p['n']} {p['peak']} Hz "
              f"{p['prom']}x {p['power']:.3g}  vs  reproduced n={g['n']} {g['peak']:.2f} Hz "
              f"{g['prom']:.1f}x {g['power']:.3g}")

    print()
    print("=" * 104)
    print("3.  HEADLINE -- speed-matched ENGAGED CREEP (v <= %.2f m/s), Method A" % SPEED_CAP)
    print("=" * 104)
    print(f"  {'build':16s} {'n':>3s}  {'peak Hz':>8s}  {'prominence':>11s}  {'abs power':>11s}")
    for label in POOLS:
        g = got[label]
        print(f"  {label:16s} {g['n']:3d}  {g['peak']:8.2f}  {g['prom']:10.1f}x  {g['power']:11.3g}")
    v59, v61, v64 = got["V59  route 2c"], got["V61  route 31"], got["V64  route 35"]
    print(f"\n  V64 vs V59: freq {v59['peak']:.2f} -> {v64['peak']:.2f} Hz "
          f"({v64['peak']-v59['peak']:+.2f})  power {v64['power']/v59['power']:.2f}x  "
          f"prom {v64['prom']/v59['prom']:.2f}x")
    print(f"  V64 vs V61: freq {v61['peak']:.2f} -> {v64['peak']:.2f} Hz "
          f"({v64['peak']-v61['peak']:+.2f})  power {v64['power']/v61['power']:.2f}x  "
          f"prom {v64['prom']/v61['prom']:.2f}x")

    print("\n  Method B (independent: NFFT=256, linear detrend, local +/-6 Hz floor)")
    for label, pat in POOLS.items():
        b_line(label, method_b(pat, creepB))

    print()
    print("=" * 104)
    print("4.  THREE-CONDITION TABLE -- route 35 (V64) only.  Method A then Method B")
    print("=" * 104)
    pat35 = POOLS["V64  route 35"]
    for label, sel in (("ENGAGED creep", creepA), ("MANUAL forward (drive)", fwdA),
                       ("MANUAL reverse", revA)):
        arrs, fs = A._pool(pat35, sel)
        secs = sum(len(x) for x in arrs) / fs if arrs else 0.0
        print(f"[{label}]  {len(arrs)} episodes, {secs:.1f} s")
        A._report(label, arrs, fs)
    print("\n  Method B, including the effort-gated and near-stationary arms:")
    for label, sel in (("ENGAGED creep", creepB), ("MANUAL fwd (un-gated)", fwdB),
                       ("MANUAL fwd eff>=1000", fwd1kB), ("MANUAL reverse", revB),
                       ("MANUAL near-stat eff 2200-3300", nearstatB)):
        b_line(label, method_b(pat35, sel))

    print()
    print("=" * 104)
    print("5.  DISENGAGED vs ENGAGED, SPEED- AND EFFORT-MATCHED (the decisive arm)")
    print("=" * 104)
    print("  On V59-class builds the mode was ABSENT disengaged (prom med 122.7x eng vs 3.6x dis).")
    print("  V61 made it APPEAR in manual. Which picture does V64 look like?\n")
    for vlo, vhi, elo, ehi in ((0.3, SPEED_CAP, 0, 10 ** 9), (0.3, SPEED_CAP, 1000, 10 ** 9),
                               (0.3, 2.0, 1000, 10 ** 9), (0.0, 0.6, 2200, 3300)):
        def mk(on):
            return lambda lat, g, v, e: ((lat if on else ~lat) & (np.abs(v) >= vlo)
                                         & (np.abs(v) <= vhi) & (e >= elo) & (e <= ehi))
        print(f"  window |v| {vlo:.1f}-{vhi:.2f} m/s, effort {elo}-{'inf' if ehi > 1e8 else ehi}")
        rE, rD = method_b(pat35, mk(True)), method_b(pat35, mk(False))
        b_line("    ENGAGED", rE)
        b_line("    DISENGAGED", rD)
        if rE["nwin"] and rD["nwin"]:
            print(f"      ratio eng/dis prominence (median): "
                  f"{np.median(rE['prom'])/np.median(rD['prom']):.2f}x")
        print()

    print("=" * 104)
    print("6.  RATCHET CHECK -- is the ~7.4 Hz line present, and is it LKAS-gated?")
    print("=" * 104)
    for label, sel in (("ENGAGED creep", creepB), ("MANUAL fwd", fwdB), ("MANUAL reverse", revB),
                       ("MANUAL near-stat", nearstatB)):
        r6 = method_b(pat35, sel, lo=6.0, hi=10.0)
        r12 = method_b(pat35, sel, lo=12.0, hi=30.0)
        if not r6["nwin"]:
            print(f"  {label:22s} n=0")
            continue
        print(f"  {label:22s} 6-10 Hz: f0 med {np.median(r6['f0']):5.2f} Hz "
              f"prom med {np.median(r6['prom']):7.1f}x p90 {np.percentile(r6['prom'],90):8.1f}x   "
              f"|  12-30 Hz prom med {np.median(r12['prom']) if r12['nwin'] else float('nan'):7.1f}x")
    print("\n  Trap: a 12-30 Hz 'harmonic' far stronger than its own 6-10 Hz fundamental is not a")
    print("  harmonic. Compare the two prominence columns above before calling anything a harmonic.")

    print()
    print("=" * 104)
    print("7.  PER-EPISODE SCATTER of the V64 engaged creep peak (small-n honesty)")
    print("=" * 104)
    for label, pat in POOLS.items():
        arrs, fs = A._pool(pat, creepA)
        nper = int(A.NPER_S * fs)
        pk = []
        for x in arrs:
            if len(x) < nper:
                continue
            fr, p = A._welch(x, fs, nper)
            sel = (fr >= 12) & (fr <= 30)
            pk.append(A._subbin(fr[sel], p[sel], int(np.argmax(p[sel]))))
        print(f"  {label:16s} {stat(pk, 'per-episode peak Hz')}")
        print(f"                   values: {' '.join(f'{x:.2f}' for x in pk)}")


if __name__ == "__main__":
    main()
