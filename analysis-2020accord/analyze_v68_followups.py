#!/usr/bin/env python3
"""Three follow-ups the first V68 pass forced. Run after analyze_v68_highway_arms.py.

A. WHY THE CELL MATCHER RETURNED ZERO CELLS. The (speed, effort, |rate|) matcher found no cell
   with >= 4 windows in both arms. That is not a bug to relax away -- it is the headline caveat:
   an engaged highway run and a manual one are not the same driving. Quantified here, then a
   REDUCED match on (speed, |rate|) is run with the effort imbalance reported alongside.

B. NULLS AND COMMON THRESHOLDS FOR THE MANEUVER CONTRAST. Section 4 of the first pass used a
   per-arm decile cut (19.0 vs 18.0 deg/s) and quoted no split-half null. Both are fixed: one
   ABSOLUTE threshold for both arms, and every ratio against a null from the identical estimator.
   🛑 Without a null a ratio is not a finding -- the standing rule.

C. THE 28 Hz LINE. The order veto found 30-49.5 Hz empty (prominence 1.81-2.45 vs a >4 criterion)
   but turned up a prominence-52.7 peak at 28.13 Hz on the ENGAGED route, in the band the kit
   pre-declared as its NEGATIVE CONTROL (24-28 Hz). Two things must be ruled out before it is
   called a mode, and this kit has come close to publishing a wheel order as a firmware effect
   three times:
     - WHEEL ORDER: f0 must be tracked ACROSS a speed sweep, not tested at one speed. Order n
       predicts f0 = n * 0.4808 * v (circumference 2.088 m -> 0.4808 Hz per m/s).
     - The estimator itself: averaged periodogram FIRST, then peak-find (HANDOFF-2026-08-03 §5b).
   A line that stays put as v sweeps is a MODE; one that rides 0.4808*n*v is a tyre.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import _grind2_lib as G  # noqa: E402
from _r31_common import periodogram, runs_of  # noqa: E402
from analyze_v68_highway_arms import (HWY, NFFT, HOP, boot_ratio, mean_fs,  # noqa: E402
                                      segs_of, split_null, wrecs_v68)

CIRC = 2.088          # m, the kit's measured wheel circumference (order 1 = 0.4808 Hz per m/s)
ORD1 = 1.0 / CIRC     # 0.4789 Hz per m/s ... the kit's fitted value is 0.4808; both are shown


def main():
    rng = np.random.default_rng(20260803)
    G.EPKEY = "blk"
    res = {}
    W = {r: wrecs_v68(r) for r in ("4c", "4e")}
    OFF = [w for w in W["4c"] if not w["eng"] and w["v"] >= HWY]
    ON = [w for w in W["4e"] if w["eng"] and w["v"] >= HWY]

    # ---------------------------------------------------------------- A -------------------------
    G.hdr("A. WHY THE CELL MATCHER FOUND NOTHING -- the arms do not overlap in EFFORT")
    for nm, arm in (("ON  (4e, engaged)", ON), ("OFF (4c, manual) ", OFF)):
        e = G.col(arm, "eff")
        print(f"  {nm}: |sustained torque| p10 {np.percentile(e, 10):6.0f}  "
              f"p50 {np.percentile(e, 50):6.0f}  p90 {np.percentile(e, 90):6.0f}   "
              f"E_BINS hist {np.bincount([G.binof(x, G.E_BINS) for x in e], minlength=4)}")
    eON, eOFF = G.col(ON, "eff"), G.col(OFF, "eff")
    ov = (min(eON.max(), eOFF.max()) - max(eON.min(), eOFF.min()))
    print(f"\n  raw effort overlap span {max(0.0, ov):.0f} counts; "
          f"fraction of OFF windows below ON's p90: "
          f"{100 * np.mean(eOFF < np.percentile(eON, 90)):.1f}%")
    print("  ⇒ the driver supplies the torque when LKAS is off and the motor supplies it when")
    print("    LKAS is on. The 1-4 Hz check in the first pass (ratio 0.213) reports exactly this.")
    print("    🛑 THEREFORE THE RAW ARM CONTRAST IS AN EXPOSURE CONTRAST, NOT A FIRMWARE ONE.")
    res["effort"] = dict(on_p50=float(np.median(eON)), off_p50=float(np.median(eOFF)))

    print("\n  REDUCED match on (speed, |rate|) only, effort left unmatched and reported:")
    cells = sorted(set((w["cell"][0], w["cell"][2]) for w in ON) &
                   set((w["cell"][0], w["cell"][2]) for w in OFF))
    res["reduced"] = {}
    for band in ("1-4", "18-22", "24-28", "30-40", "40-49"):
        k, num, den, w_ = "e_" + band, [], [], []
        for c in cells:
            A = [w for w in ON if (w["cell"][0], w["cell"][2]) == c]
            B = [w for w in OFF if (w["cell"][0], w["cell"][2]) == c]
            if len(A) >= 4 and len(B) >= 4:
                num.append(np.median(G.col(A, k))); den.append(np.median(G.col(B, k)))
                w_.append(min(len(A), len(B)))
        if not w_:
            print(f"    {band:8} no usable cell")
            continue
        w_ = np.array(w_, float); w_ /= w_.sum()
        r = float(np.sum(w_ * np.array(num)) / np.sum(w_ * np.array(den)))
        res["reduced"][band] = dict(ratio=r, ncells=len(w_))
        print(f"    {band:8} {r:7.3f}   ({len(w_)} cells)")

    # ---------------------------------------------------------------- B -------------------------
    G.hdr("B. THE MANEUVER CONTRAST -- common thresholds, and a NULL for every ratio")
    allpk = np.concatenate([G.col(ON, "ratepk"), G.col(OFF, "ratepk")])
    HI, LO = float(np.percentile(allpk, 90)), float(np.percentile(allpk, 50))
    print(f"  ONE absolute pair of cuts for both arms: maneuver |rate|pk >= {HI:.1f} deg/s, "
          f"control <= {LO:.1f} deg/s\n")
    res["maneuver"] = {}
    for nm, arm in (("ON  (4e)", ON), ("OFF (4c)", OFF)):
        mv = [w for w in arm if w["ratepk"] >= HI]
        ct = [w for w in arm if w["ratepk"] <= LO]
        print(f"  {nm}: {len(mv)} maneuver windows / {len(ct)} controls "
              f"({len(G.episodes(mv))} / {len(G.episodes(ct))} blocks)")
        res["maneuver"][nm.split()[0]] = {}
        for band in ("1-4", "18-22", "24-28", "30-40", "40-49"):
            k = "e_" + band
            pt, ci = boot_ratio(mv, ct, k, rng)
            nl = split_null(ct, k, rng)
            sig = ""
            if np.isfinite(ci[0]) and np.isfinite(nl[1]) and ci[0] > nl[1]:
                sig = "  *** outside the null"
            res["maneuver"][nm.split()[0]][band] = dict(ratio=pt, ci=ci, null=nl,
                                                        n_mv=len(mv), n_ct=len(ct))
            print(f"      {band:8} {pt:7.3f} [{ci[0]:6.3f}, {ci[1]:6.3f}]   "
                  f"null [{nl[0]:5.2f}, {nl[1]:5.2f}]{sig}")
        print()
    print("  ⇒ read the 40-49 Hz row ACROSS the two arms: that is the operator's 'only when")
    print("    engaged' claim, tested inside each arm against its own control.")

    # ---------------------------------------------------------------- C -------------------------
    G.hdr("C. THE 28 Hz LINE -- mode or wheel order? Track it across a SPEED SWEEP")
    print("  averaged periodogram per narrow speed bin, THEN peak-find in 24-30 Hz.")
    print(f"  order n predicts f0 = n * 0.4808 * v   (measured circumference {CIRC} m)\n")
    res["line28"] = {}
    for route, eng in (("4e", True), ("4c", False)):
        print(f"  --- route {route} ({'ENGAGED' if eng else 'MANUAL'}) ---")
        rows = []
        for vlo, vhi in ((19, 21), (21, 23), (23, 25), (25, 27), (27, 29), (29, 32)):
            acc, n, fref, vs = None, 0, None, []
            for s, d in segs_of(route):
                fs = mean_fs(d["t"])
                f = np.fft.rfftfreq(NFFT, 1 / fs)
                le = d["cc_lat"] > 0.5
                for a, b in runs_of(le if eng else ~le, d["t"], NFFT):
                    for i in range(0, (b - a) - NFFT + 1, HOP):
                        sl = slice(a + i, a + i + NFFT)
                        v = float(np.mean(d["cs_v"][sl]))
                        if not (vlo <= v < vhi):
                            continue
                        P = periodogram(d["tq"][a + i:a + i + NFFT], fs, NFFT, True)
                        if P is None:
                            continue
                        if acc is None:
                            acc, fref = np.zeros_like(P), f
                        if len(P) == len(acc):
                            acc += P; n += 1; vs.append(v)
            if n < 8:
                print(f"    v={vlo}-{vhi}: n={n} -- too few")
                continue
            Pm = acc / n
            R = G.prom_spectrum(fref, Pm)
            f0, pr = G.locate(fref, Pm, 24.0, 30.0, R=R)
            f1, pr1 = G.locate(fref, Pm, 8.0, 18.0, R=R)
            vm = float(np.mean(vs))
            rows.append((vm, f0, pr, n))
            print(f"    v={vlo}-{vhi} (n={n:3d}, mean {vm:5.2f}): "
                  f"24-30 Hz peak {f0:6.2f} prom {pr:6.2f}   "
                  f"order = {f0 / (0.4808 * vm):5.3f}   |   "
                  f"8-18 Hz peak {f1:5.2f} prom {pr1:5.2f} (order {f1 / (0.4808 * vm):5.3f})")
        res["line28"][route] = rows
        if len(rows) >= 3:
            vv = np.array([r[0] for r in rows]); ff = np.array([r[1] for r in rows])
            # Theil-Sen slope: robust, and the estimator the kit used to confirm order 1
            sl = np.median([(ff[j] - ff[i]) / (vv[j] - vv[i])
                            for i in range(len(vv)) for j in range(i + 1, len(vv))
                            if vv[j] != vv[i]])
            print(f"    Theil-Sen slope {sl:+.4f} Hz per m/s   "
                  f"(order 1 = +0.4808, order 2 = +0.9616, a fixed MODE = 0.0000)")
            res["line28"][route + "_slope"] = float(sl)
        print()

    Path(HERE / "_v68_followups.json").write_text(json.dumps(res, indent=1, default=str))
    print(f"wrote {HERE / '_v68_followups.json'}")


if __name__ == "__main__":
    main()
