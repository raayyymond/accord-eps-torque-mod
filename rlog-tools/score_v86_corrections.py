#!/usr/bin/env python3
"""THE THREE CORRECTIONS APPLIED TO THE V86 / V86B SCORING.

X1  CREEP-CUT FAMILY.  Print the FULL `<10 km/h` stratum medians (family A) so this session's
    numbers sit on the SAME ruler as the reference table, and print the `<20 km/h` (family B)
    column beside them so the ~6x cut effect is visible rather than assumed.

X2  THE MOVED MODE.  The 18-27 Hz argmax moved 20.97 -> 23.66 Hz on V86 (ratio 1.106).  A fixed
    18-22 Hz window then reads V86 as "improved" when the energy merely left the window.  The
    corpus already carries `e_18-26` and `e_12-30`; both are used here as the wider windows, so
    no band is invented and no records are rebuilt.

X3  NYQUIST.  Grind #2's acoustic centroid is 63.5 Hz [54.2, 79.6], above BOTH Nyquists
    (CAN 50.00, IMU 50.51).  fs ~ 100.2 Hz folds f -> |fs - f|, so:
        63.5 Hz  -> 36.7 Hz   *** inside the 32-38 Hz NEGATIVE CONTROL ***
        54.2 Hz  -> 46.0 Hz   (inside 40-49)
        79.6 Hz  -> 20.6 Hz   (inside 18-22)
    ⇒ the 32-38 Hz control is NOT clean for grind #2, and the whole fold map has to be printed
    beside any 40-49 Hz claim.  This section prints e_32-38 on every burst window so the reader
    can see whether the control moved with the band.

Usage: python score_v86_corrections.py
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import score_v86_r6f_r70 as V86  # noqa: E402  -- owns the registration and the records
import score_v84_r6d as S  # noqa: E402
import compare_v75_v76_v80_grind as M  # noqa: E402
import _grind2_lib as G  # noqa: E402

RNG = np.random.default_rng(86_7016)
LADDER = V86.LADDER
OUT = {}
CUT10 = 10 / 3.6          # 2.778 m/s -- family A, the modern ladder
CUT20 = 20 / 3.6          # 5.556 m/s -- family B, the BUILD-LINEAGE / LEDGER yardstick
FS = 100.2                # measured lattice rate on these caches


def main():
    G.EPKEY = "blk"
    R = V86.build_records()
    for b in LADDER:
        S._add_imu2049(R[b])

    # ============================================================ X1  THE CREEP CUT ===============
    S.hdr("X1  🛑 CREEP-CUT FAMILY.  The SAME builds on the two cuts.  Family A = <10 km/h\n"
          "    (the modern ladder, and what every number I reported uses).  Family B = <20 km/h\n"
          "    (the `e_18-22` yardstick quoted in BUILD-LINEAGE / LEDGER).  Median [2.5,97.5],\n"
          "    ~10.24 s blocks resampled, engaged only.")
    OUT["cut_families"] = {}
    for cut, lbl in ((CUT10, "A: <10 km/h"), (CUT20, "B: <20 km/h")):
        print(f"\n  ---- family {lbl} ----")
        print(f"  {'build':10s} {'n':>4s} {'blk':>4s} | " + " ".join(
            f"{bd:>24s}" for bd in ("6-9", "18-22", "40-49", "32-38")))
        for b in LADDER:
            s = V86.eng(R[b], b, 0.0, cut)
            if len(s) < 3:
                print(f"  {b:10s} {len(s):4d}  -- too few --")
                OUT["cut_families"].setdefault(lbl, {})[b] = dict(n=len(s))
                continue
            cells, rec = [], dict(n=len(s), blk=G.col(s, "v").size and len({r["blk"] for r in s}))
            for bd in ("6-9", "18-22", "40-49", "32-38"):
                ee = G.boot_median_ci(s, "e_" + bd, RNG, nboot=1500)
                cells.append(f"{ee[0]:8.1f} [{ee[1]:6.1f},{ee[2]:7.1f}]")
                rec[bd] = list(ee)
            print(f"  {b:10s} {len(s):4d} {rec['blk']:4d} | " + " ".join(cells))
            OUT["cut_families"].setdefault(lbl, {})[b] = rec
    print("\n  ⇒ read the two V67 rows against each other: the CUT alone moves the build.")

    # ============================================================ X2  THE MOVED MODE ==============
    S.hdr("X2  🛑 THE MOVED MODE.  V86's 18-27 Hz argmax is 23.66 Hz vs V85's 20.97 (ratio 1.106,\n"
          "    CI disjoint); V86B's is 21.75 (null).  A FIXED 18-22 Hz window therefore reads V86\n"
          "    as improved when the energy has left the window.  `e_18-26` and `e_12-30` are the\n"
          "    corpus's OWN wider bands and both contain 23.66 Hz -- no band is invented here.")
    nulls = {}
    print(f"\n  split-half nulls FIRST, engaged creep <10 km/h:")
    for bd in ("18-22", "18-26", "12-30"):
        for b in ("V85/r6e", "V86/r6f", "V86B/r70"):
            s = V86.eng(R[b], b, 0.0, CUT10)
            n = G.split_half_null(s, "e_" + bd, RNG, nrep=400, min_ep=1, min_win=3)
            nulls[(bd, b)] = n
            print(f"    {bd:6s} {b:10s} {n[0]:7.3f} [{n[1]:7.3f}, {n[2]:7.3f}]")
    print(f"\n  {'pair':22s} {'band':7s} {'medA':>9s} {'medB':>9s} {'ratio':>8s} "
          f"{'95% CI':>20s} {'cells':>6s}  verdict")
    OUT["moved_mode"] = {}
    for A, B in (("V86/r6f", "V85/r6e"), ("V86B/r70", "V85/r6e"), ("V86B/r70", "V86/r6f")):
        for bd in ("18-22", "18-26", "12-30", "26-31", "32-38"):
            a, b_ = V86.eng(R[A], A, 0.0, CUT10), V86.eng(R[B], B, 0.0, CUT10)
            res = G.boot_cellwise(a, b_, "e_" + bd, RNG, nboot=1500, min_ep=1, min_win=3)
            nA, nB = nulls.get((bd, A)), nulls.get((bd, B))
            if nA and nB and np.isfinite(nA[1]) and np.isfinite(nB[1]):
                nlo, nhi = min(nA[1], nB[1]), max(nA[2], nB[2])
                v = V86.verdict(res[0], res[1], res[2], nlo, nhi)
            else:
                v = "no defined null"
            ma = float(np.nanmedian(G.col(a, "e_" + bd)))
            mb = float(np.nanmedian(G.col(b_, "e_" + bd)))
            print(f"  {A.split('/')[0]+' / '+B.split('/')[0]:22s} {bd:7s} {ma:9.1f} {mb:9.1f} "
                  f"{res[0]:8.3f} [{res[1]:8.3f},{res[2]:8.3f}] {res[3]:6d}  {v}")
            OUT["moved_mode"].setdefault(f"{A}|{B}", {})[bd] = dict(
                ratio=res[0], lo=res[1], hi=res[2], cells=res[3], medA=ma, medB=mb, verdict=v)
        print()
    print("  ⇒ if 18-22 falls but 18-26 / 12-30 do NOT, the energy MOVED, it did not go away.")

    # ============================================================ X3  NYQUIST FOLD ================
    S.hdr("X3  🛑 NYQUIST.  Grind #2's acoustic centroid is 63.5 Hz [54.2, 79.6] -- ABOVE both\n"
          "    Nyquists (CAN 50.00, IMU 50.51).  On fs = 100.2 Hz a true f folds to |fs - f|:")
    for f in (54.2, 60.0, 63.5, 66.0, 70.0, 79.6):
        fold = abs(FS - f)
        where = ("18-22" if 18 <= fold <= 22 else "26-31" if 26 <= fold <= 31 else
                 "32-38 🛑 THE NEGATIVE CONTROL" if 32 <= fold <= 38 else
                 "40-49" if 40 <= fold <= 49 else "outside every band")
        print(f"      true {f:5.1f} Hz  ->  observed {fold:5.1f} Hz   ({where})")
    print("\n  ⇒ TWO consequences, both of which change how my Section B must be read:\n"
          "    (a) the 40-49 Hz band is the SKIRT of the object, not the object;\n"
          "    (b) the 32-38 Hz NEGATIVE CONTROL receives the fold of 62-68 Hz, i.e. the\n"
          "        centroid itself ⇒ 🛑 IT IS NOT A CLEAN CONTROL FOR GRIND #2.  It remains a\n"
          "        valid control for grind #1 (18-22) and the ratchet (6-9), whose folds land\n"
          "        at 78-82 and 91-94 Hz, where nothing is claimed to live.")

    S.hdr("X3b THE BURST WINDOWS WITH THE CONTROL BESIDE THEM.  If e_32-38 rises WITH e_40-49\n"
          "    on the same window, that is consistent with ONE out-of-band object folding into\n"
          "    both -- not with a broadband floor shift AND not with a clean band effect.")
    OUT["bursts"] = {}
    for b in ("V86/r6f", "V86B/r70", "V85/r6e"):
        e = V86.eng(R[b], b, 0.0, CUT10)
        med = {bd: float(np.nanmedian(G.col(e, "e_" + bd))) for bd in
               ("6-9", "18-22", "26-31", "32-38", "40-49")}
        top = sorted(e, key=lambda r: -(r["e_40-49"] if np.isfinite(r["e_40-49"]) else -1))[:5]
        print(f"\n  ---- {b} ----  route creep medians: " + " ".join(
            f"{k} {v:.1f}" for k, v in med.items()))
        print(f"    {'seg':>3s} {'t0':>7s} {'v':>5s} {'|ang|':>6s} {'e40-49':>8s} {'e32-38':>8s} "
              f"{'e26-31':>8s} {'e18-22':>8s} {'e6-9':>8s} {'imu40':>7s} {'zig':>4s} | "
              f"{'40-49 / its median':>18s} {'32-38 / its median':>18s}")
        rows = []
        for r in top:
            x40 = r["e_40-49"] / max(med["40-49"], 1e-9)
            x32 = r["e_32-38"] / max(med["32-38"], 1e-9)
            print(f"    {r['seg']:3d} {r['t0']:7.1f} {r['v']:5.2f} {r['ang']:6.1f} "
                  f"{r['e_40-49']:8.1f} {r['e_32-38']:8.1f} {r['e_26-31']:8.1f} "
                  f"{r['e_18-22']:8.1f} {r['e_6-9']:8.1f} {r.get('imu40', np.nan):7.3f} "
                  f"{r.get('zig', 0):4d} | {x40:18.1f} {x32:18.1f}")
            rows.append(dict(seg=int(r["seg"]), t0=float(r["t0"]), v=r["v"], ang=r["ang"],
                             e40=r["e_40-49"], e32=r["e_32-38"], e26=r["e_26-31"],
                             e18=r["e_18-22"], e6=r["e_6-9"],
                             imu40=float(r.get("imu40", np.nan)), zig=int(r.get("zig", 0)),
                             x40=x40, x32=x32))
        OUT["bursts"][b] = dict(medians=med, top=rows)

    S.hdr("X3c 🛑 THE ONE TEST THE FOLD CANNOT FAKE.  `zigzag` counts SIGN-ALTERNATING turning\n"
          "    points above a threshold -- it is FFT-free and leakage-immune, and a signal near\n"
          "    fs/2 reverses almost every sample whatever its true frequency is.  It cannot tell\n"
          "    54 Hz from 46 Hz (they alias to each other) but it CAN tell 'there is near-Nyquist\n"
          "    content' from 'there is not', without any spectral assumption.")
    print(f"\n  engaged creep <10 km/h, zigzag count at 300 ct and 800 ct thresholds:")
    print(f"  {'build':10s} {'n':>4s} | {'zig300 median':>14s} {'p95':>7s} {'max':>7s} | "
          f"{'zig800 median':>14s} {'p95':>7s} {'max':>7s} | {'frac zig300>20':>15s}")
    OUT["zig"] = {}
    for b in LADDER:
        s = V86.eng(R[b], b, 0.0, CUT10)
        if len(s) < 3:
            continue
        z3, z8 = G.col(s, "zig"), G.col(s, "zig800")
        f20 = M.frac_ci(s, "zig", 20.0, RNG, nboot=2000)
        print(f"  {b:10s} {len(s):4d} | {np.median(z3):14.1f} {np.percentile(z3,95):7.1f} "
              f"{z3.max():7.0f} | {np.median(z8):14.1f} {np.percentile(z8,95):7.1f} "
              f"{z8.max():7.0f} | {100*f20[0]:6.1f}% [{100*f20[1]:4.1f},{100*f20[2]:5.1f}]")
        OUT["zig"][b] = dict(n=len(s), zig300_med=float(np.median(z3)),
                             zig300_p95=float(np.percentile(z3, 95)), zig300_max=float(z3.max()),
                             zig800_med=float(np.median(z8)), zig800_max=float(z8.max()),
                             frac_gt20=list(f20))
    print("\n  MANUAL arm, same cut, same statistic (the engagement test the fold cannot fake):")
    for b in LADDER:
        s = V86.man(R[b], b, 0.0, CUT10, fwd_only=True)
        if len(s) < 3:
            continue
        z3 = G.col(s, "zig")
        f20 = M.frac_ci(s, "zig", 20.0, RNG, nboot=2000)
        print(f"  {b:10s} {len(s):4d} | {np.median(z3):14.1f} {np.percentile(z3,95):7.1f} "
              f"{z3.max():7.0f} |                              | "
              f"{100*f20[0]:6.1f}% [{100*f20[1]:4.1f},{100*f20[2]:5.1f}]")
        OUT.setdefault("zig_manual", {})[b] = dict(n=len(s), med=float(np.median(z3)),
                                                   max=float(z3.max()), frac_gt20=list(f20))

    # ============================================================ X4  IMU ABOVE ITS OWN BAND ======
    S.hdr("X4  THE CHASSIS CHANNEL.  Grind #1 is a torsional COLUMN mode and never reaches the\n"
          "    chassis; grind #2 does (IMU coherence 0.82-0.88 on record).  `imu40` is the\n"
          "    40-49 Hz chassis envelope -- the same skirt, on an INDEPENDENT sensor with an\n"
          "    independent (50.51 Hz) Nyquist.  Engaged creep <10 km/h.")
    print(f"  {'build':10s} {'n':>4s} | {'imu40 median':>26s} | {'p95':>8s} {'max':>8s}")
    OUT["imu40"] = {}
    for b in LADDER:
        s = [r for r in V86.eng(R[b], b, 0.0, CUT10) if np.isfinite(r.get("imu40", np.nan))]
        if len(s) < 3:
            print(f"  {b:10s} {len(s):4d} |  -- no IMU in this cache --")
            continue
        ee = G.boot_median_ci(s, "imu40", RNG, nboot=1500)
        v = G.col(s, "imu40")
        print(f"  {b:10s} {len(s):4d} |{ee[0]:9.4f} [{ee[1]:7.4f},{ee[2]:7.4f}] |"
              f"{np.percentile(v,95):8.4f} {v.max():8.4f}")
        OUT["imu40"][b] = dict(n=len(s), e=list(ee), p95=float(np.percentile(v, 95)),
                               max=float(v.max()))
    for A, B in (("V86/r6f", "V85/r6e"), ("V86B/r70", "V85/r6e"), ("V86B/r70", "V86/r6f")):
        a = [r for r in V86.eng(R[A], A, 0.0, CUT10) if np.isfinite(r.get("imu40", np.nan))]
        b_ = [r for r in V86.eng(R[B], B, 0.0, CUT10) if np.isfinite(r.get("imu40", np.nan))]
        if min(len(a), len(b_)) < 5:
            continue
        res = G.boot_cellwise(a, b_, "imu40", RNG, nboot=1500, min_ep=1, min_win=3)
        rr = G.boot_cellwise(a, b_, "imu2049", RNG, nboot=1500, min_ep=1, min_win=3)
        print(f"    {A.split('/')[0]+' / '+B.split('/')[0]:22s} imu40 {res[0]:7.3f} "
              f"[{res[1]:6.3f},{res[2]:6.3f}] c={res[3]:2d}   "
              f"imu2049 (roughness) {rr[0]:6.3f} [{rr[1]:6.3f},{rr[2]:6.3f}]")
        OUT.setdefault("imu40_ratio", {})[f"{A}|{B}"] = dict(
            imu40=[res[0], res[1], res[2], res[3]], imu2049=[rr[0], rr[1], rr[2], rr[3]])

    def _san(o):
        if isinstance(o, dict):
            return {str(k): _san(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [_san(x) for x in o]
        if isinstance(o, (np.floating, np.integer, float)):
            f = float(o)
            return None if not np.isfinite(f) else f
        return o
    for p in (ROOT / "_cache_r6f" / "score_v86_corrections.json",
              ROOT / "_cache_r70" / "score_v86b_corrections.json"):
        p.write_text(json.dumps(_san(OUT), indent=1))
        print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
