#!/usr/bin/env python3
"""H1 PRE-REGISTERED TEST: "the highway resonance is grind #2's MECHANISM at a higher mode."

H1's chain: `gp-0x4f62` is a 4-sample finite difference at 1 kHz, so its gain RISES with frequency
(1.93x at 41.6 Hz vs 20.9 Hz). V62's flat x2 cut grind #1 by 2.9x and raised grind #2 by 11.7x.
V67 keeps the x2 but LKAS-gates it, and because a flat scalar replaces a surface Honda rolls off
with speed, V67 delivers its MAXIMUM dose -- 2.44x -- at highway.

PREDICTIONS, recorded before the numbers below were produced:
  P1  events are LKAS-engaged                    (base rate is 100% by construction -- untestable)
  P2  event RATE rises with dose, 1.00 < 2.00 < 2.44          *** THE SHARP TEST ***
  P3  event amplitude at matched trigger rises with dose
  P4  event f0 sits above 20.9 Hz, at/above 44.6, possibly aliased from >50
  P5  a command<->bar relationship at the event frequency, as grind #1 had (0.917 @ 21.09 Hz)

🛑 The pre-committed reading: P2 holds => a real lever and the published null was a
   statistic-choice artefact. P2 fails WITH POWER => H1 refuted. Too few events => say so and
   convert it into a drive. This file computes the power and the required drive length either way.

🛑 The veto that runs first: if the events are wheel order 3 (44.3 Hz at 30.8 m/s, one bin from
   grind #2), H1 is "true" only because the tyre was detected. `studies/highway/highway_meanspec.py` runs that
   veto and its answer is imported into the verdict below rather than re-derived.

Usage:  python studies/highway/highway_h1_test.py
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G          # noqa: E402
import highway_event_hunt as H   # noqa: E402

RNG = np.random.default_rng(20260803)
OUT = HERE / "_scratch/out/_hwy_h1.json"
Z = 2.80                          # z_{0.025} + z_{0.20}, i.e. 80% power at alpha 0.05 two-sided


def rate_ci(bl, kd, rng, nboot=3000):
    """Events per hour for one dose with a 10 s block bootstrap."""
    P = [b for b in bl if b["kd"] == kd]
    if not P:
        return np.nan, np.nan, np.nan, 0, 0.0
    h, e = sum(x["hit"] for x in P), sum(x["expo"] for x in P)
    dr = np.empty(nboot)
    for k in range(nboot):
        i = rng.integers(0, len(P), len(P))
        hh = sum(P[j]["hit"] for j in i)
        ee = sum(P[j]["expo"] for j in i)
        dr[k] = 3600 * hh / max(ee, 1e-9)
    return (3600 * h / max(e, 1e-9), float(np.percentile(dr, 2.5)),
            float(np.percentile(dr, 97.5)), h, e)


def seconds_needed(rate_per_h, ratio=2.0):
    """Engaged-highway seconds PER ARM to detect `ratio` at 80% power, alpha 0.05.
    Var(log R) = 1/n1 + 1/n2 with n1 = lam*T, n2 = ratio*lam*T
    => T = (1 + 1/ratio) / (lam * (ln ratio / Z)^2)."""
    lam = rate_per_h / 3600.0
    if lam <= 0:
        return np.inf
    return float((1 + 1 / ratio) / (lam * (np.log(ratio) / Z) ** 2))


def main():
    store = {}
    runs = H.collect_envelopes("tq")
    for k, v in H.WIDE.items():
        H.BANDS[k] = v
    for r in runs:
        for k, (lo, hi) in H.WIDE.items():
            if "e_" + k not in r:
                r["e_" + k] = H.band_env_run(r["tq"], r["fs"], lo, hi)

    for VMIN in (12.0, 22.0, 28.0):
        H.VMIN = VMIN
        G.hdr(f"H1 / P2 -- EVENT RATE BY DOSE, engaged, v >= {VMIN:g} m/s.  "
              f"H1 predicts 1.00 < 2.00 < 2.44.")
        wins = [w for w in H.window_records(runs) if w["v"] >= VMIN]
        print(f"    {len(wins)} windows.  " + "  ".join(
            f"Kd{k:.2f}: {sum(1 for w in wins if w['kd'] == k) * 1.28:.0f} s"
            for k in (1.0, 2.0, 2.44)))
        print(f"\n    {'band':>7}{'Kd=1.00 /h':>26}{'Kd=2.00 /h':>26}{'Kd=2.44 /h':>26}"
              f"{'  monotone?':>12}")
        for band in ("18-22", "30-40", "40-49", "10-49"):
            f50 = H.floor_table(runs, band, q=50)
            evs = H.characterise(runs, H.find_events(
                runs, band, {i: 10 * f50[i] for i in f50}, vmin=VMIN))
            keys = set()
            for e in evs:
                for k in range(e["i0"] - H.NFFT, e["i1"] + 1):
                    keys.add((e["run"], (k // (H.NFFT // 2)) * (H.NFFT // 2)))
            bl = H.blocks_of(wins, keys)
            cells, txt = [], ""
            for kd in (1.0, 2.0, 2.44):
                r, lo, hi, n, e = rate_ci(bl, kd, RNG)
                cells.append(r)
                txt += f"{r:8.1f} [{lo:5.1f},{hi:6.1f}] n={n:<4d}"
            mono = "YES" if cells[0] < cells[1] < cells[2] else "NO"
            print(f"    {band:>7}{txt}{mono:>12}")
            store.setdefault(f"v{VMIN:g}", {})[band] = dict(
                rates=cells, monotone=(mono == "YES"))
            # power, from the two arms actually being compared
            n1 = sum(x["hit"] for x in bl if x["kd"] == 1.0)
            n2 = sum(x["hit"] for x in bl if x["kd"] == 2.44)
            var = 1.0 / max(n1, 0.5) + 1.0 / max(n2, 0.5)
            mdr = float(np.exp(Z * np.sqrt(var)))
            need = seconds_needed(cells[0] if cells[0] > 0 else np.nan)
            print(f"    {'':>7}  POWER 2.44 vs 1.00: n={n1}+{n2} events, Var(logR)={var:.4f} "
                  f"=> smallest ratio detectable at 80% power = {mdr:.2f}x"
                  f"{'  (2.0x IS detectable)' if mdr <= 2.0 else '  (2.0x is NOT detectable)'}")
            print(f"    {'':>7}  DRIVE NEEDED for a 2.0x test at this event rate: "
                  f"{need:.0f} s ({need / 60:.1f} min) of engaged highway PER DOSE ARM")
            store[f"v{VMIN:g}"][band].update(n1=int(n1), n2=int(n2), min_detect=mdr,
                                             sec_needed=need)

    # ---------------------------------------------------------------- P3 ------------------------
    H.VMIN = 22.0
    G.hdr("H1 / P3 -- EVENT AMPLITUDE at a MATCHED trigger, by dose (v >= 22 m/s)\n"
          "    Cells are (speed bin x rate_peak bin) so a bigger steering transient on one\n"
          "    build cannot masquerade as a bigger event.")
    for band in ("30-40", "40-49"):
        f50 = H.floor_table(runs, band, q=50)
        evs = H.characterise(runs, H.find_events(
            runs, band, {i: 10 * f50[i] for i in f50}, vmin=22.0))
        evs = [e for e in evs if e["v_mean"] >= 22.0]
        cell = {}
        for e in evs:
            c = (H.vbin(e["v_mean"]), int(np.clip(np.log2(max(e["rate_pk"], 1)), 0, 6)))
            cell.setdefault((e["kd"], c), []).append(e["amp"])
        print(f"\n    band {band} Hz -- {len(evs)} events")
        num = {1.0: [], 2.0: [], 2.44: []}
        for (kd, c), v in sorted(cell.items()):
            if len(v) >= 3:
                num[kd].append((c, float(np.median(v)), len(v)))
        for kd in (1.0, 2.0, 2.44):
            if num[kd]:
                print(f"      Kd={kd:.2f}  cells={len(num[kd])}  median event amp over cells "
                      f"{np.median([x[1] for x in num[kd]]):.0f}  "
                      f"(n={sum(x[2] for x in num[kd])} events)")
            else:
                print(f"      Kd={kd:.2f}  no cell with >= 3 events")
        shared = (set(c for c, _, _ in num[1.0]) & set(c for c, _, _ in num[2.44]))
        if shared:
            lr = [np.log(dict((c, m) for c, m, _ in num[2.44])[c]
                         / dict((c, m) for c, m, _ in num[1.0])[c]) for c in shared]
            print(f"      matched-cell amplitude ratio 2.44/1.00 = "
                  f"{np.exp(np.mean(lr)):.3f} over {len(shared)} shared cells")
            store.setdefault("P3", {})[band] = float(np.exp(np.mean(lr)))
        else:
            print("      🛑 NO cell is occupied by both Kd=1.00 and Kd=2.44 with >= 3 events "
                  "=> P3 is UNTESTABLE at this exposure")
            store.setdefault("P3", {})[band] = None

    OUT.write_text(json.dumps(store, indent=1, default=float))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
