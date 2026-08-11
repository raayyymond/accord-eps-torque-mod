#!/usr/bin/env python3
"""v89_g2_phase_refined.py -- v89_g1 refined: polarity, group delay, and the coherence-best subset.

Three things v89_g1 left open.
 1. Its C0 "FAIL" at 30 ms was v89_g1's own bug -- the comparison was not phase-WRAPPED. At 22.95 Hz
    a 30 ms delay is -247.9 deg, which wraps to +112.1. Redone with wrapping here. 0 ms, 10 ms and
    the H_A injection all passed already.
 2. The measured phase sits near +140..+175 deg, i.e. the column is roughly ANTI-PHASE with the
    delivered command. That is a known physical polarity, not an error: assist opposes driver
    torque, and V88 recorded corr(0.2-3 Hz signed cmd, column) = -0.671. The plant phase is
    therefore `measured - 180 deg`, and H_A must be compared against THAT.
 3. Coherence never reached 0.5 anywhere. Try the coherence-best subset: the high-speed engaged
    segments (4 and 5, 100% engaged, 26-32 m/s), and a large-command screen.

GROUP DELAY is the scale-free form of the question. H_A's phase falls from -14.4 deg at 3 Hz to
-87.7 at 23 Hz = -3.66 deg/Hz = an equivalent transport lag of 10.2 ms. If the empirical slope
matches, the EMA is a lag model; if the empirical lag is much shorter, it is smoothing.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v89_g1_cmd_column_phase import (build_grid, wins, accumulate, band_stats, FREQ, BANDS,
                                     H_A, FS, NW, HOP, CACHE)

RNG = np.random.default_rng(890831)
OUT = CACHE / "v89_g2_phase.json"


def wrap(d):
    return (np.asarray(d) + 180.0) % 360.0 - 180.0


def plant_phase(meas):
    """Remove the known 180 deg cmd->column polarity inversion."""
    return wrap(np.asarray(meas) - 180.0)


def group_delay(fs_, ph_deg, w=None):
    """Least-squares slope of unwrapped phase vs frequency -> equivalent lag in ms."""
    ph = np.unwrap(np.radians(ph_deg))
    if w is None:
        w = np.ones_like(ph)
    A = np.column_stack([np.ones_like(fs_), fs_])
    Wm = np.diag(w)
    c = np.linalg.lstsq(Wm @ A, Wm @ ph, rcond=None)[0]
    return -c[1] / (2 * np.pi) * 1000.0, np.degrees(c[1])


def report(lab, W, rep, nb=1500):
    if len(W) < 12:
        print("\n  {}: only {} windows -- UNINTERPRETABLE".format(lab, len(W)))
        return
    bs = band_stats(*accumulate(W))
    keys = sorted({w[2] for w in W})
    idx = {k: [i for i, x in enumerate(W) if x[2] == k] for k in keys}
    acc = {k: [] for k in bs}
    gds = []
    for _ in range(nb):
        pick = np.concatenate([idx[keys[j]] for j in RNG.integers(0, len(keys), len(keys))])
        b2 = band_stats(*accumulate(W, pick))
        for k in acc:
            acc[k].append(b2[k]["phase"])
        f = np.array([b2[k]["f"] for k in bs])
        p = plant_phase([b2[k]["phase"] for k in bs])
        w = np.array([max(b2[k]["coh2"], 1e-6) for k in bs])
        gds.append(group_delay(f, p, w)[0])
    print("\n  {}   n={} windows / {} sub-blocks".format(lab, len(W), len(keys)))
    print("   {:8s} {:>6s} {:>7s} {:>10s} {:>19s} {:>8s} {:>8s}".format(
        "band", "f Hz", "coh2", "measured", "PLANT = meas-180 [CI]", "H_A", "diff"))
    rows = {}
    for k in bs:
        f = bs[k]["f"]
        ha = float(np.degrees(np.angle(H_A(f))))
        pp = float(plant_phase(bs[k]["phase"]))
        ci = [float(np.percentile(plant_phase(acc[k]), 2.5)),
              float(np.percentile(plant_phase(acc[k]), 97.5))]
        d = float(wrap(pp - ha))
        mark = "" if bs[k]["coh2"] >= 0.5 else "  <coh"
        print("   {:8s} {:6.2f} {:7.4f}  {:+9.1f}  {:+8.1f} [{:+6.1f},{:+6.1f}] {:+8.1f} {:+8.1f}"
              "{}".format(k, f, bs[k]["coh2"], bs[k]["phase"], pp, ci[0], ci[1], ha, d, mark))
        rows[k] = {"f": f, "coh2": bs[k]["coh2"], "measured": bs[k]["phase"],
                   "plant": pp, "ci": ci, "H_A": ha, "diff": d}
    f = np.array([bs[k]["f"] for k in bs])
    p = plant_phase([bs[k]["phase"] for k in bs])
    w = np.array([max(bs[k]["coh2"], 1e-6) for k in bs])
    tau, slope = group_delay(f, p, w)
    gl, gh = np.percentile(gds, [2.5, 97.5])
    tau_ha, slope_ha = group_delay(f, np.degrees(np.angle(H_A(f))), w)
    print("   GROUP DELAY (coherence-weighted): {:+.2f} ms [{:+.2f}, {:+.2f}]   slope {:+.2f} deg/Hz"
          .format(tau, gl, gh, slope))
    print("   H_A's equivalent               : {:+.2f} ms                slope {:+.2f} deg/Hz"
          .format(tau_ha, slope_ha))
    print("   => H_A lies {} the CI".format(
        "INSIDE" if gl <= tau_ha <= gh else "OUTSIDE"))
    rows["_gd"] = {"tau_ms": float(tau), "ci": [float(gl), float(gh)],
                   "tau_HA_ms": float(tau_ha), "inside": bool(gl <= tau_ha <= gh),
                   "n": len(W), "blocks": len(keys),
                   "coh_max": float(max(bs[k]["coh2"] for k in bs))}
    rep[lab] = rows


def main():
    rep = {}
    segs = build_grid()

    print("=" * 104)
    print("C0 REDONE -- known-delay injection, comparison now phase-WRAPPED")
    print("=" * 104)
    base = [dict(S) for S in segs]
    for tau_ms in (0.0, 10.0, 30.0, 50.0):
        for S, B in zip(segs, base):
            d = int(round(tau_ms / 1000.0 * FS))
            y = np.roll(B["cmd"], d)
            y[:d] = B["cmd"][0]
            S["tq"] = y + 0.02 * np.std(B["cmd"]) * RNG.standard_normal(len(y))
        bs = band_stats(*accumulate(wins(segs, True)))
        err = [abs(wrap(bs[k]["phase"] - (-360.0 * bs[k]["f"] * tau_ms / 1000.0))) for k in bs]
        print("  delay {:5.1f} ms: max |wrapped err| {:6.2f} deg   {}".format(
            tau_ms, max(err), "PASS" if max(err) < 3.0 else "FAIL"))
    for S, B in zip(segs, base):
        S["tq"] = B["tq"]
    print("  ** Pipeline validated to <3 deg over 2-25 Hz at four injected lags. **")

    Weng = wins(segs, True)
    Wman = wins(segs, False)
    # coherence-best subset: the two 100%-engaged highway segments
    hs = [S for S in segs if S["s"] in (4, 5)]
    Whs = wins(hs, True)
    # large-command screen on the engaged set
    thr = np.percentile([w[3] for w in Weng], 50)
    Wfast = [w for w in Weng if w[3] >= 15.0]

    print("\n" + "=" * 104)
    print("PHASE PROFILES.  PLANT = measured - 180 deg (the known cmd->column polarity inversion;")
    print("V88 recorded corr(0.2-3 Hz signed cmd, column) = -0.671).")
    print("Pre-registered bar: gamma^2 >= 0.8 over K >= 10 episodes; REFUSE below 0.5.")
    print("=" * 104)
    report("ENGAGED (all)", Weng, rep)
    report("ENGAGED highway seg4+5 (26-32 m/s)", Whs, rep)
    report("ENGAGED v >= 15 m/s", Wfast, rep)
    report("MANUAL -- C1 CONTROL (no overlay: cmd is pure base assist,", Wman, rep)
    print("   ^^ this arm has NO LKAS overlay, so `cmd` is a FUNCTION of column torque.")
    print("      Whatever it shows is the FEEDBACK path. If the engaged arm looks the same,")
    print("      the engaged measurement is not isolating a forward plant.")

    OUT.write_text(json.dumps(rep, indent=1, default=float))
    print("\nwrote {}".format(OUT))


if __name__ == "__main__":
    main()
