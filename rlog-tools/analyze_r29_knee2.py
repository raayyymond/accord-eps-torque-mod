#!/usr/bin/env python3
"""analyze_r29_knee2.py -- resolve WHERE the driver-torque collapse happens, and check that the
"hands-on" definition the kit uses is not measuring the oscillation instead of the driver.

Fixed torque bins starve: inside the LKAS episode the driver's sustained effort is bimodal (median
100 counts, p90 1774), so every bin between 500 and 2560 has n<50 and gets refused. QUANTILE bins
guarantee n and therefore locate the transition, which is the whole point of a knee test.

CONTAMINATION CHECK. The kit's hands-on test is |0x18F torque| > 200. But the grinding IS a
+-1400-count oscillation ON that same channel, so a light-handed driver inside the burst trips the
test on the oscillation alone. Quantified here against the low-passed sustained effort.

ROBUSTNESS. "Sustained driver effort" is computed three ways (zero-phase low-pass at 3 Hz and 1 Hz,
and raw |torque|) because the choice of corner is a judgement call and the conclusion must not
depend on it.

Usage:  python analyze_r29_knee2.py CACHE.npz
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from analyze_r29_grinding import FS, NFFT, BAND, spectrum, bandpower, runs_of  # noqa
from analyze_r29_knee import (analytic_env, lowpass, B_MODE, B_LOW, B_FLOOR,  # noqa
                              KNEE_LO, KNEE_HI)


def hdr(s):
    print(f"\n{'=' * 100}\n{s}\n{'=' * 100}")


def main(cache):
    d = dict(np.load(cache))
    n = len(d["t"])
    sca = d["sca"] > 0.5
    tq, rc, ang, v, e4 = d["tq"], d["rate_c"], d["ang"], d["cs_v"], d["e4tq"]
    eng = d["cs_eng"] > 0.5
    rr = runs_of(sca, 50)

    # ---------------------------------------------------------------- 1. CONTAMINATION CHECK
    hdr("1. IS THE KIT'S |torque|>200 'HANDS-ON' TEST MEASURING THE DRIVER, OR THE GRINDING?")
    a, b = rr[0]
    seg = slice(a, b)
    x_tq = tq[seg]
    eff3 = np.abs(lowpass(x_tq, 3.0))
    raw = np.abs(x_tq)
    print(f"  main LKAS episode, n={b-a}")
    print(f"  raw |torque|            : med {np.median(raw):6.0f}  p10 {np.percentile(raw,10):6.0f}"
          f"  p90 {np.percentile(raw,90):6.0f}  >200 in {100*(raw>200).mean():5.1f}%")
    print(f"  |lowpass(torque, 3 Hz)| : med {np.median(eff3):6.0f}  p10 {np.percentile(eff3,10):6.0f}"
          f"  p90 {np.percentile(eff3,90):6.0f}  >200 in {100*(eff3>200).mean():5.1f}%")
    hot = raw > 200
    print(f"\n  of the {int(hot.sum())} frames the kit would call HANDS-ON (raw>200), "
          f"{int((eff3[hot] < 200).sum())} ({100*(eff3[hot]<200).mean():.1f}%) have sustained "
          f"effort BELOW 200.")
    print(f"  => the kit's hands-on/hands-off split is contaminated by the oscillation it is trying")
    print(f"     to condition on. Sustained effort is the defensible variable inside a burst.")
    print(f"  whole route: raw>200 in {100*(np.abs(tq)>200).mean():.1f}% of frames; inside the LKAS")
    print(f"     episode {100*hot.mean():.1f}%, outside {100*(np.abs(tq[~sca])>200).mean():.1f}%")

    # ---------------------------------------------------------------- 2. QUANTILE KNEE SWEEP
    hdr("2. QUANTILE-BINNED EFFORT SWEEP -- where does the grinding actually collapse?")
    envs = {}
    for cn, ch in (("TQ", x_tq), ("RATE", rc[seg])):
        for bn, (lo, hi) in (("mode", B_MODE), ("low", B_LOW), ("floor", B_FLOOR)):
            envs[f"{cn}_{bn}"], _ = analytic_env(ch, lo, hi)
    keep = np.ones(b - a, bool)
    k = max(int(0.05 * (b - a)), 8)
    keep[:2 * k] = keep[-2 * k:] = False

    for effname, eff in (("lowpass 3 Hz", eff3), ("lowpass 1 Hz", np.abs(lowpass(x_tq, 1.0))),
                         ("raw |torque|", raw)):
        e = eff[keep]
        qs = np.quantile(e, np.linspace(0, 1, 13))
        print(f"\n  -- effort = {effname} --  (12 quantile bins, ~{int(keep.sum()/12)} samples each)")
        print(f"  {'effort range':>16s} {'n':>5s} {'med eff':>8s} | {'TQ 18-25':>9s} "
              f"{'18-25/fl':>9s} | {'TQ 6-9':>9s} {'6-9/fl':>8s} | {'RATE 18-25':>11s} {'R/fl':>6s}")
        for i in range(12):
            lo, hi = qs[i], qs[i + 1]
            m = keep & (eff >= lo) & (eff <= hi if i == 11 else eff < hi)
            if m.sum() < 40:
                continue
            md = lambda k_: np.median(envs[k_][m])
            mark = ""
            if lo <= KNEE_LO <= hi:
                mark = "  <== 2240 knee"
            elif lo <= KNEE_HI <= hi:
                mark = "  <== 2560 (authority 0)"
            print(f"  {f'{lo:.0f}-{hi:.0f}':>16s} {int(m.sum()):5d} {np.median(eff[m]):8.0f} | "
                  f"{md('TQ_mode'):9.1f} {md('TQ_mode')/md('TQ_floor'):9.2f} | "
                  f"{md('TQ_low'):9.1f} {md('TQ_low')/md('TQ_floor'):8.2f} | "
                  f"{md('RATE_mode'):11.3f} {md('RATE_mode')/md('RATE_floor'):6.2f}{mark}")

    # ---------------------------------------------------------------- 3. SECOND EPISODE REPLICATE
    hdr("3. SECOND LKAS EPISODE (t=61.10-62.91 s, n=182) AS AN INDEPENDENT REPLICATE")
    if len(rr) > 1:
        a2, b2 = rr[1]
        s2 = slice(a2, b2)
        x2 = tq[s2]
        e2 = np.abs(lowpass(x2, 3.0))
        env2 = {}
        for bn, (lo, hi) in (("mode", B_MODE), ("low", B_LOW), ("floor", B_FLOOR)):
            env2[bn], _ = analytic_env(x2, lo, hi)
        k2 = max(int(0.05 * (b2 - a2)), 8)
        kp2 = np.ones(b2 - a2, bool)
        kp2[:2 * k2] = kp2[-2 * k2:] = False
        print(f"  n={b2-a2} ({int(kp2.sum())} after taper)  effort med {np.median(e2[kp2]):.0f}  "
              f"max {e2[kp2].max():.0f}  vEgo {v[s2].min():.2f}-{v[s2].max():.2f}  "
              f"angle {ang[s2].min():.1f}..{ang[s2].max():.1f}")
        print(f"  envelopes: TQ 18-25 med {np.median(env2['mode'][kp2]):.1f} "
              f"(/floor {np.median(env2['mode'][kp2])/np.median(env2['floor'][kp2]):.2f})   "
              f"TQ 6-9 med {np.median(env2['low'][kp2]):.1f} "
              f"(/floor {np.median(env2['low'][kp2])/np.median(env2['floor'][kp2]):.2f})")
        print(f"  compare episode 1 below the knee: TQ 18-25 /floor 10.92, TQ 6-9 /floor 33.31")
        lo_m = kp2 & (e2 < 500)
        hi_m = kp2 & (e2 >= 500)
        for nm, m in (("effort <500", lo_m), ("effort >=500", hi_m)):
            if m.sum() < 40:
                print(f"    {nm:14s} n={int(m.sum()):4d}  -- n<40, REFUSED --")
                continue
            print(f"    {nm:14s} n={int(m.sum()):4d}  TQ 18-25 {np.median(env2['mode'][m]):7.1f} "
                  f"(/fl {np.median(env2['mode'][m])/np.median(env2['floor'][m]):5.2f})  "
                  f"TQ 6-9 {np.median(env2['low'][m]):7.1f} "
                  f"(/fl {np.median(env2['low'][m])/np.median(env2['floor'][m]):5.2f})")

    # ---------------------------------------------------------------- 4. DELIVERABLE D, CORRECTED
    hdr("4. DELIVERABLE D -- 15-27 Hz TORQUE POWER (counts^2), nfft=256, BOTH SEGMENTS")
    print("  kit's recorded parking-lot creep numbers: V56 r24 7.66e4 | V55 r1c 1.94e5 | R13 6.59e4")
    print("  ⚠ those were computed on the LEGACY cruiseState proxy and by masked concatenation.")
    hands_raw = np.abs(tq) > 200
    eff_full = np.zeros(n)
    eff_full[seg] = eff3
    if len(rr) > 1:
        eff_full[rr[1][0]:rr[1][1]] = np.abs(lowpass(tq[rr[1][0]:rr[1][1]], 3.0))
    hands_eff = eff_full > 200
    subs = [("SCA=1 (LATERAL, correct)", sca),
            ("SCA=1 + hands-off (raw>200)", sca & ~hands_raw),
            ("SCA=1 + hands-off (sustained)", sca & ~hands_eff),
            ("SCA=1 + hands-on (sustained)", sca & hands_eff),
            ("SCA=0", ~sca),
            ("SCA=0 + hands-off (raw)", ~sca & ~hands_raw),
            ("cruiseState=1 [LEGACY proxy]", eng),
            ("ALL frames", np.ones(n, bool))]
    print(f"\n  {'subset':34s} {'n':>6s} | {'K':>3s} {'contig-run':>12s} | {'K':>3s} "
          f"{'masked-concat':>14s}")
    for nm, sel in subs:
        if sel.sum() < 50:
            print(f"  {nm:34s} {int(sel.sum()):6d} |  -- n<50, REFUSED --")
            continue
        cells = []
        for mode in (False, True):
            f, P, K, _ = spectrum(tq, sel, NFFT, mode)
            cells.append((K, bandpower(P, f) if P is not None else np.nan))
        (k1, v1), (k2, v2) = cells
        s1 = f"{v1:12.4g}" if np.isfinite(v1) else f"{'no segment':>12s}"
        s2 = f"{v2:14.4g}" if np.isfinite(v2) else f"{'no segment':>14s}"
        print(f"  {nm:34s} {int(sel.sum()):6d} | {k1:3d} {s1} | {k2:3d} {s2}")
    f1, P1, K1, _ = spectrum(tq, sca, NFFT)
    f0, P0, K0, _ = spectrum(tq, ~sca, NFFT)
    p1, p0 = bandpower(P1, f1), bandpower(P0, f0)
    print(f"\n  LATERAL-ON / LATERAL-OFF ratio, 15-27 Hz = {p1/p0:.1f}x   "
          f"(absolute {p1:.4g} vs {p0:.4g}, K={K1}/{K0})")
    b69 = (f1 >= 6) & (f1 <= 9)
    print(f"  same for 6-9 Hz = {P1[b69].mean()/P0[b69].mean():.1f}x   "
          f"(absolute {P1[b69].mean():.4g} vs {P0[b69].mean():.4g})")
    print(f"  recorded engaged/disengaged ratios on the sensor: V56 786x, V55 877x")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    sys.exit(main(Path(sys.argv[1])))
