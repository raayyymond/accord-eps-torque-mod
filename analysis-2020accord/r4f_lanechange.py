#!/usr/bin/env python3
"""Route `4f` (V69): did the ~28 Hz LANE-CHANGE transient survive?

WHAT IS BEING REPLICATED. On V68 route `4e`, segment 33, t = 51.3 s, openpilot fired
`preLaneChangeRight` and the torsion bar ran **1468 counts peak-to-peak** at **28.12 / 28.51 Hz**
with prominence up to 107, a **26-30 Hz envelope of 614 against a route median of 31 (20x)**, while
**40-49 Hz read 69 in the same window**. That is the operator's felt lane-change vibration, and it
is NOT grind #2 (HANDOFF-2026-08-03 §5).

⚠ IT IS n = 1. One well-characterised event is a capture, not a rate. This script therefore reports
EVERY lane-change instance on `4f` -- not the loudest -- with the same three numbers each time, plus
the route's own median so a "20x" claim is always relative to a stated floor.

EVENT SOURCES, all three, because they disagree and each has a failure mode:
  ALC       openpilot's own `laneChange` / `preLaneChangeLeft` / `preLaneChangeRight` onroadEvents.
            The cleanest anchor -- it is the state machine that COMMANDED the maneuver.
  BLINKER   carState.left/rightBlinker. Fires on driver-initiated changes the ALC machine never saw,
            and also on turns.
  RATE      |steering rate| transients above an absolute threshold. Catches a maneuver whose blinker
            was never used, and is the only source that does not depend on openpilot's view.

🛑 THE FLOOR IS COMPUTED FIRST. The route-median 26-30 Hz envelope over ALL engaged highway windows
is printed BEFORE any event, so no event's ratio can be quoted against a floor chosen after seeing
it.

Usage:  python r4f_lanechange.py [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G                                     # noqa: E402
import _r4f_lib as L                                        # noqa: E402
from _r31_common import load, periodogram, runs_of          # noqa: E402

G.BANDS["26-30"] = (26.0, 30.0)
NFFT, HOP = G.NFFT, G.HOP
HWY = 20.0
CIRC = (2.073 + 2.088) / 2
RATE_EVT = 25.0             # deg/s -- an absolute |rate| transient cut, stated before use
SCAN_S = 4.0                # s -- how far either side of a marker the burst is searched for
BANDS_RPT = ["1-4", "18-22", "24-28", "26-30", "30-40", "40-49"]

ROUTES = {
    "4f/V69": dict(cache=ROOT / "_cache_r4f", pfx="r4fs", segs=list(range(8))),
    "4e/V68": dict(cache=ROOT / "_cache_v68", pfx="4es", segs=[31, 32, 33, 34]),
}
RES: dict = {}


def hdr(s):
    print(f"\n{'=' * 112}\n{s}\n{'=' * 112}")


def segs_of(route):
    B = ROUTES[route]
    for s in B["segs"]:
        p = B["cache"] / f"{B['pfx']}{s}.npz"
        if p.exists():
            yield s, load(s, B["cache"], B["pfx"])


def events_of(route, seg):
    B = ROUTES[route]
    p = B["cache"] / f"{B['pfx']}{seg}_events.json"
    return json.loads(p.read_text()) if p.exists() else []


def window_at(d, fs, i0, tag, seg):
    """Every reported quantity for ONE 2.56 s window starting at index i0."""
    sl = slice(i0, i0 + NFFT)
    x = np.asarray(d["tq"][sl], float)
    if len(x) < NFFT or not np.all(np.isfinite(x)):
        return None
    taper = np.hanning(NFFT) + 1e-3
    cw = slice(int(0.2 * NFFT), int(0.8 * NFFT))
    f = np.fft.rfftfreq(NFFT, 1 / fs)
    P = periodogram(x, fs, NFFT, True)
    if P is None:
        return None
    R = G.prom_spectrum(f, P)
    r = dict(tag=tag, seg=int(seg), t0=float(d["t"][i0]))
    for k in BANDS_RPT:
        lo, hi = G.BANDS[k]
        r["e_" + k] = G.win_env(x, fs, lo, hi, taper, cw)
        r["f_" + k], r["p_" + k] = G.locate(f, P, lo, hi, R=R)
    r["pp"] = float(x.max() - x.min())
    r["v"] = float(np.mean(np.abs(d["cs_v"][sl])))
    r["rpm"] = float(np.mean(d["rpm"][sl])) if "rpm" in d else np.nan
    r["ang_sw"] = float(np.max(d["ang"][sl]) - np.min(d["ang"][sl]))
    r["ratepk"] = float(np.max(np.abs(d["rate_c"][sl])))
    r["eng"] = float(np.mean(d["cc_lat"][sl] > 0.5))
    r["blink"] = float(np.mean(d["cs_lchg"][sl])) if "cs_lchg" in d else np.nan
    # the three top lines in 24-32 Hz, for the identity table
    m = (f >= 24) & (f <= 32) & np.isfinite(R)
    if m.any():
        idx = np.argsort(np.where(m, R, -np.inf))[::-1][:3]
        r["lines"] = [(float(f[j]), float(R[j])) for j in idx]
    else:
        r["lines"] = []
    r["w1"] = r["v"] / CIRC
    r["w2"] = 2 * r["v"] / CIRC
    r["w3"] = 3 * r["v"] / CIRC
    r["e1"] = r["rpm"] / 60.0 if np.isfinite(r["rpm"]) else np.nan
    return r


def floor_of(route, vmin=HWY):
    """Median (and p90) of every band over ALL engaged windows above `vmin` -- computed FIRST."""
    rows = []
    for s, d in segs_of(route):
        fs = L.fs_lattice(d)
        le = d["cc_lat"] > 0.5
        for a, b in runs_of(le, d["t"], NFFT):
            for i in range(a, b - NFFT + 1, HOP):
                if float(np.mean(np.abs(d["cs_v"][i:i + NFFT]))) < vmin:
                    continue
                r = window_at(d, fs, i, "floor", s)
                if r:
                    rows.append(r)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(HERE / "_r4f_lanechange.json"))
    a = ap.parse_args()
    RES["floor"] = {}

    hdr("0.  THE FLOOR, COMPUTED BEFORE ANY EVENT IS LOOKED AT")
    F = {}
    for route in ROUTES:
        rows = floor_of(route)
        F[route] = rows
        print(f"   {route}: {len(rows)} engaged windows above {HWY:.0f} m/s")
        line = f"      {'band':8s}"
        for k in BANDS_RPT:
            line += f" {k:>9s}"
        print(line)
        for stat, fn in (("median", np.median), ("p90", lambda v: np.percentile(v, 90)),
                         ("max", np.max)):
            s = f"      {stat:8s}"
            for k in BANDS_RPT:
                s += f" {fn([r['e_' + k] for r in rows]):9.1f}"
            print(s)
        RES["floor"][route] = {k: dict(median=float(np.median([r["e_" + k] for r in rows])),
                                       p90=float(np.percentile([r["e_" + k] for r in rows], 90)),
                                       mx=float(np.max([r["e_" + k] for r in rows])))
                               for k in BANDS_RPT}
        print()
    print("   ⚠ 4e's floor is quoted here only so the 4f numbers can be read beside the recorded")
    print("     V68 event. The two routes are different roads on different days.")

    # ------------------------------------------------------------------ events ------------------
    hdr("1.  LANE-CHANGE INSTANCES ON 4f -- all three sources")
    RES["events"] = {}
    for route in ROUTES:
        print(f"\n   ================ route {route} ================")
        evs = []
        for s, d in segs_of(route):
            fs = L.fs_lattice(d)
            t = np.asarray(d["t"], float)
            # --- ALC ---------------------------------------------------------------------------
            names = ("laneChange", "preLaneChangeLeft", "preLaneChangeRight")
            fired = [(e["t"], e["name"]) for e in events_of(route, s) if e["name"] in names]
            # collapse to onsets: an ALC event repeats every frame while active
            onsets = []
            for tt, nm in sorted(fired):
                if not onsets or tt - onsets[-1][0] > 3.0:
                    onsets.append((tt, nm))
            for tt, nm in onsets:
                evs.append((s, float(tt), f"ALC:{nm}"))
            # --- BLINKER -----------------------------------------------------------------------
            bl = np.asarray(d.get("cs_lchg", np.zeros(len(t))), float) > 0.5
            for aa, bb in runs_of(bl, t, 10):
                evs.append((s, float(t[aa]), "BLINK"))
            # --- RATE --------------------------------------------------------------------------
            rp = np.abs(np.asarray(d["rate_c"], float))
            hot = rp >= RATE_EVT
            for aa, bb in runs_of(hot, t, 3):
                if float(np.mean(np.abs(d["cs_v"][aa:bb]))) >= HWY:
                    evs.append((s, float(t[aa]), "RATE"))
        # de-duplicate on the MARKER, then again on the CHOSEN WINDOW.
        # 🛑 The second pass is not redundant: two markers 5 s apart can both select the SAME
        # 2.56 s burst inside their +-SCAN_S search, which double-counts one physical event. The
        # first version of this script did exactly that and printed one seg-6 burst three times.
        evs.sort(key=lambda e: (e[0], e[1]))
        keep = []
        for s, tt, src in evs:
            if keep and keep[-1][0] == s and tt - keep[-1][1] < 4.0:
                keep[-1] = (s, keep[-1][1], keep[-1][2] + "+" + src.split(":")[0])
                continue
            keep.append((s, tt, src))
        print(f"   {len(evs)} raw markers -> {len(keep)} distinct maneuver markers "
              f"(4 s coalescing window)")

        med26 = np.median([r["e_26-30"] for r in F[route]])
        cand = []
        for s, tt, src in keep:
            d = load(s, ROUTES[route]["cache"], ROUTES[route]["pfx"])
            fs = L.fs_lattice(d)
            t = np.asarray(d["t"], float)
            # scan +-SCAN_S around the marker at hop/2, keep the window with the largest 26-30 Hz
            i0 = int(np.argmin(np.abs(t - tt)))
            best = None
            for j in range(max(0, i0 - int(SCAN_S * fs)),
                           min(len(t) - NFFT, i0 + int(SCAN_S * fs)), HOP // 2):
                r = window_at(d, fs, j, src, s)
                if r and (best is None or r["e_26-30"] > best["e_26-30"]):
                    best = r
            if best is None:
                continue
            best["t_mark"] = float(tt)
            cand.append(best)
        # second pass: collapse chosen windows that OVERLAP in time, keeping the loudest
        cand.sort(key=lambda r: (r["seg"], r["t0"]))
        rows = []
        for r in cand:
            if rows and rows[-1]["seg"] == r["seg"] and \
                    r["t0"] - rows[-1]["t0"] < NFFT / 100.0:
                if r["e_26-30"] > rows[-1]["e_26-30"]:
                    r["tag"] = rows[-1]["tag"] + "+" + r["tag"].split(":")[0]
                    rows[-1] = r
                else:
                    rows[-1]["tag"] += "+" + r["tag"].split(":")[0]
                continue
            rows.append(r)
        print(f"   -> {len(rows)} DISTINCT bursts after collapsing overlapping chosen windows")

        print(f"\n   {'seg':>4s} {'mark':>7s} {'win t0':>7s} {'src':18s} {'v':>6s} {'rpm':>5s} "
              f"{'angsw':>6s} {'ratpk':>6s} {'bar p-p':>8s} "
              f"{'26-30':>7s} {'xmed':>5s} {'40-49':>7s} {'18-22':>7s} "
              f"{'top line':>16s} {'w2':>6s} {'e1':>6s}")
        for best in rows:
            ln = best["lines"][0] if best["lines"] else (np.nan, np.nan)
            hw = "HWY" if best["v"] >= HWY else "low"
            print(f"   {best['seg']:4d} {best['t_mark']:7.2f} {best['t0']:7.2f} "
                  f"{(hw + ' ' + best['tag'].split('+')[0])[:18]:18s} {best['v']:6.2f} "
                  f"{best['rpm']:5.0f} {best['ang_sw']:6.1f} "
                  f"{best['ratepk']:6.1f} {best['pp']:8.0f} "
                  f"{best['e_26-30']:7.1f} {best['e_26-30'] / med26:5.1f} "
                  f"{best['e_40-49']:7.1f} {best['e_18-22']:7.1f} "
                  f"{f'{ln[0]:.2f}@{ln[1]:.0f}':>16s} {best['w2']:6.2f} {best['e1']:6.2f}")
        RES["events"][route] = [{k: v for k, v in r.items() if k != "lines"} | {"lines": r["lines"]}
                                for r in rows]

        hwy_rows = [r for r in rows if r["v"] >= HWY]
        print(f"\n   of which {len(hwy_rows)} are HIGHWAY (v >= {HWY:.0f} m/s) -- the only ones")
        print("   comparable to V68's recorded lane-change event; the rest are low-speed turns.")
        if hwy_rows:
            top = max(hwy_rows, key=lambda r: r["e_26-30"])
            print(f"\n   ---- LOUDEST 26-30 Hz HIGHWAY MANEUVER ON {route}: seg {top['seg']} "
                  f"t = {top['t0']:.2f} s ----")
            print(f"     speed {top['v']:.2f} m/s   rpm {top['rpm']:.0f}   engaged "
                  f"{100 * top['eng']:.0f}%   blinker {100 * top['blink']:.0f}%")
            print(f"     steering swing {top['ang_sw']:.2f} deg   |rate| peak "
                  f"{top['ratepk']:.1f} deg/s")
            print(f"     torsion-bar peak-to-peak {top['pp']:.0f} counts")
            for k in BANDS_RPT:
                print(f"     {k:>6s} Hz envelope {top['e_' + k]:8.1f}  "
                      f"(route median {np.median([r['e_' + k] for r in F[route]]):6.1f}, "
                      f"x{top['e_' + k] / np.median([r['e_' + k] for r in F[route]]):.1f})   "
                      f"peak {top['f_' + k]:5.2f} Hz prom {top['p_' + k]:6.2f}")
            print(f"     top 24-32 Hz lines: "
                  + ", ".join(f"{f:.2f} Hz @ prom {p:.1f}" for f, p in top["lines"]))
            print(f"     ORDER CHECK  wheel 1 {top['w1']:.2f}  wheel 2 {top['w2']:.2f}  "
                  f"wheel 3 {top['w3']:.2f}  engine 1 {top['e1']:.2f}  "
                  f"engine 2 {2 * top['e1']:.2f} Hz")

    # ------------------------------------------------------------------ comparison --------------
    hdr("2.  DID THE ~28 Hz LANE-CHANGE TRANSIENT SURVIVE V69?")
    for route in ROUTES:
        rows = [r for r in RES["events"][route] if r["v"] >= HWY]
        if not rows:
            continue
        e = np.array([r["e_26-30"] for r in rows], float)
        pp = np.array([r["pp"] for r in rows], float)
        med = RES["floor"][route]["26-30"]["median"]
        print(f"   {route}: {len(rows)} HIGHWAY maneuvers   26-30 Hz envelope "
              f"median {np.median(e):7.1f}  max {e.max():7.1f}   "
              f"route floor {med:5.1f}  ⇒ median/floor {np.median(e) / med:.1f}x, "
              f"max/floor {e.max() / med:.1f}x   bar p-p max {pp.max():.0f}")
        print("      per-event (26-30 env, xmed, bar p-p, top line, wheel-order-2, engine-order-1):")
        for r in sorted(rows, key=lambda z: -z["e_26-30"]):
            ln = r["lines"][0] if r["lines"] else (np.nan, np.nan)
            d2 = abs(ln[0] - r["w2"]) if np.isfinite(ln[0]) else np.nan
            d1 = abs(ln[0] - r["e1"]) if np.isfinite(ln[0]) and np.isfinite(r["e1"]) else np.nan
            print(f"        seg{r['seg']:2d} t={r['t0']:6.2f}  {r['e_26-30']:7.1f}  "
                  f"x{r['e_26-30'] / med:5.1f}  {r['pp']:6.0f}  "
                  f"{ln[0]:6.2f} Hz @ {ln[1]:5.1f}   w2 {r['w2']:6.2f} (d {d2:5.2f})   "
                  f"e1 {r['e1']:6.2f} (d {d1:5.2f})")
    print("\n   🛑 The recorded V68 event was 614 counts of 26-30 Hz envelope at 20x its route")
    print("     median, 1468 counts p-p, lines 27.73/28.12/28.51 Hz at prominence 100-107.")
    print("     ⚠ CROSS-ROUTE: different road, different day. The within-route x-median ratio is")
    print("     the comparable quantity, not the raw envelope.")

    Path(a.json).write_text(json.dumps(RES, indent=1, default=str))
    print(f"\nwrote {a.json}")


if __name__ == "__main__":
    main()
