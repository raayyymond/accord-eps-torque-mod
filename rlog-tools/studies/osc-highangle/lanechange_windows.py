#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""studies/osc-highangle/lanechange_windows.py -- the lane changes THEMSELVES, from openpilot's own state, and the operator's
two named examples on r32.  Companion to lanechange_osc.py (same caches/conventions; the chain runs with the per-route cells
in lanechange_osc.CHAIN_CFG: r32/r33 = V280 rev 2 line map / clamp 46080, r31 = rev 3, r22/r97 = x1 / 7680).

Inputs: `_scratch/_ha_<route>.npz` (CAN grid) and `_scratch/_lc_<tag>.npz` (modelV2.meta.laneChangeState/laneChangeDirection at
20 Hz, carState.leftBlinker/rightBlinker at 100 Hz, `clocks.wallTimeNanos` and gpsLocationExternal.unixTimestampMillis with
their logMonoTime; written by the scratch extractor extract_lc.py).

  1. WALL-CLOCK ANCHOR.  unix = logMonoTime + offset; offset from gpsLocationExternal (fix-valid samples) and cross-checked against
     the post-sync `clocks` samples (the device clock is wrong before its first sync -- 2026-07-28 -- so the median clocks offset is
     NOT usable; the late/max one agrees with GPS to < 1 s).  The operator's times are local (PDT = UTC-7, the route is at lon -122);
     each is converted, placed on the route-relative grid, and its 60 s segment index is checked against the operator's.
  2. LANE-CHANGE WINDOWS.  Runs of laneChangeState != off (preLaneChange -> laneChangeStarting -> laneChangeFinishing), gaps < 1 s
     merged, extended 2 s after the last non-off sample (the settle).  Every window on r32 and r33 is reported with: direction,
     blinker, speed, angle swing, |cmd| peak, idx peak, the 4-12 Hz rate amplitude, the 2-12 Hz envelope peak, dominant frequency
     (Welch + Hilbert), T amplitude / f_dom / saturation / damping fraction, cmd-vs-rate coherence and phase at f_dom, chain P-rail /
     fb-clamp duty and |E|, whether the automatic OSC detector (lanechange_events.json) fired inside it, and whether an operator
     timestamp falls inside it.
  3. THE OPERATOR'S TWO EXAMPLES, +-10 s, in full: a 0.5 s-bin trace (v, angle, cmd, idx, rate envelope, |T|, laneChangeState) and
     the oscillation statistics of the ringing part.

Run:  python lanechange_windows.py   (writes LANECHANGE-windows.txt beside itself)
"""
import datetime
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import highangle_stutter as H  # noqa: E402
import lanechange_osc as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FS = 100.0
OPERATOR = {"r32": [("09:39:25", 5), ("09:42:41", 9)]}      # local wall clock, operator's segment
TZ_H = -7                                                 # PDT
DATE = "2026-09-02"


def anchor(tag, lc):
    ok = lc["unixms"] > 1.6e12
    off_gps = np.median(lc["unixms"][ok] * 1e-3 - lc["tgps"][ok])
    wall = lc["wall"] * 1e-9 - lc["tclk"]
    off_clk = wall[wall > 1.6e9].max() if (wall > 1.6e9).any() else np.nan       # post-sync samples
    return off_gps, off_clk


def stats_window(G, C, a, b, tag):
    w = slice(a, b)
    rate, T, cmd, ang = G["rate"][w], G["T"][w], G["cmd"][w], G["ang"][w]
    fr, promr = L.fdom(rate)
    fi = L.inst_freq(L.bp(rate, 2, 12)) if b - a >= 40 else np.nan
    fT, _ = L.fdom(T) if tag in L.HAS_TAP else (np.nan, np.nan)
    f0 = fr if np.isfinite(fr) and 3 < fr < 12 else 7.5
    cohc, phc = L.coh_phase(rate, cmd, f0)
    mt = (T != 0) & (rate != 0)
    damp = float(np.mean(np.sign(T[mt]) != np.sign(rate[mt]))) if (tag in L.HAS_TAP and mt.any()) else np.nan
    m = np.zeros(len(G["t"]), bool); m[a:b] = True
    cs = L.chain_stats(C, m)
    return dict(v=float(np.median(G["v"][w])), ang50=float(np.median(ang)), swing=float(ang.max() - ang.min()),
                cmd_pk=float(np.abs(cmd).max()), idx_pk=float(G["idx"][w].max()), tq_pk=float(np.abs(G["tq"][w]).max()),
                amp412=L.band_amp(rate, 4, 12) / 8, env_pk=float(G["env"][w].max()), f_rate=fr, prom=promr, f_inst=fi, f_T=fT,
                amp_T=L.band_amp(T, 4, 12) if tag in L.HAS_TAP else np.nan,
                absT90=float(np.percentile(np.abs(T), 90)) if tag in L.HAS_TAP else np.nan,
                T_sat=float(np.mean((G["fld"][w] & 0x1FF) >= H.T_SAT_FIELD)) if tag in L.HAS_TAP else np.nan,
                damp=damp, coh=cohc, ph=phc, p_rail=cs.get("p_rail", np.nan), fb_cl=cs.get("fb_clamped", np.nan),
                absE50=cs.get("absE_p50", np.nan), absE90=cs.get("absE_p90", np.nan), ref50=cs.get("ref_p50", np.nan),
                eng=float(G["eng"][w].mean()), hw=float(G["hw"][w].mean()))


def main():
    J = json.load(open(os.path.join(HERE, "lanechange_events.json")))
    lines = []
    pr = lambda s="": (print(s), lines.append(s))  # noqa: E731
    out = {}
    for tag in ("r32", "r33"):
        prefix = L.ROUTES[tag][0]
        D = dict(np.load(os.path.join(L.ROUTES[tag][2], "_ha_%s.npz" % prefix)))
        t0 = D["t18"][0]
        G = L.load(tag)
        C = L.chain(G, L.CHAIN_CFG[tag])
        lc = dict(np.load(os.path.join(HERE, "_scratch", "_lc_%s.npz" % tag)))
        off_gps, off_clk = anchor(tag, lc)
        pr("=" * 130)
        pr("ROUTE %s  %s  [%s]" % (tag, prefix, L.CHAIN_CFG[tag]["name"]))
        pr("  wall-clock anchor: unix = logMonoTime + %.3f s (GPS, n=%d)  |  post-sync clocks offset %.3f s  (diff %.3f s)" % (
            off_gps, int((lc["unixms"] > 1.6e12).sum()), off_clk, off_clk - off_gps))
        route_start_utc = datetime.datetime.fromtimestamp(t0 + off_gps, datetime.timezone.utc)
        pr("  first 0x18F frame (route t=0): %s UTC = %s local (UTC%+d)" % (
            route_start_utc.strftime("%H:%M:%S.%f")[:-3], (route_start_utc + datetime.timedelta(hours=TZ_H)).strftime("%H:%M:%S"), TZ_H))
        # lane-change state on the 100 Hz grid
        tl = lc["tm"] - t0
        st = lc["lcs"]; di = lc["lcd"]
        code = np.array([{"off": 0, "preLaneChange": 1, "laneChangeStarting": 2, "laneChangeFinishing": 3}.get(s, 0) for s in st])
        dcode = np.array([{"none": 0, "left": -1, "right": 1}.get(s, 0) for s in di])
        idx = np.clip(np.searchsorted(tl, G["t"], side="right") - 1, 0, len(tl) - 1)
        lcs100 = code[idx]; lcd100 = dcode[idx]
        tb = lc["tb"] - t0
        ib = np.clip(np.searchsorted(tb, G["t"], side="right") - 1, 0, len(tb) - 1)
        blink = np.where(lc["lb"][ib] > 0, -1, 0) + np.where(lc["rb"][ib] > 0, 1, 0)
        G["lcs"] = lcs100
        # operator timestamps
        ops = []
        for hhmmss, seg in OPERATOR.get(tag, []):
            local = datetime.datetime.strptime(DATE + " " + hhmmss, "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone(datetime.timedelta(hours=TZ_H)))
            unix = local.timestamp()
            tr = unix - off_gps - t0
            seg_calc = int((unix - off_gps - (t0 - (t0 - lc["tm"][0]) )) // 60)   # placeholder, replaced below
            ops.append((hhmmss, seg, tr))
        # segment index: rlog segments are 60 s from the route's first event; the first modelV2 sample is ~0.x s after it
        seg0_mono = min(lc["tm"][0], D["t18"][0], lc["tb"][0])
        for k, (hhmmss, seg, tr) in enumerate(ops):
            mono = tr + t0
            seg_calc = int((mono - seg0_mono) // 60)
            pr("  OPERATOR %s local -> route t = %.1f s, computed segment %d (operator said %d)%s" % (
                hhmmss, tr, seg_calc, seg, "  OK" if seg_calc == seg else "  <-- MISMATCH"))
            ops[k] = (hhmmss, seg, tr, seg_calc)
        # windows
        on = lcs100 > 0
        runs = L.merge_runs(on, 1, int(1.0 * FS))
        wins = [(a, min(b + int(2.0 * FS), len(G["t"]))) for a, b in runs]
        osc = [e for e in J["events"][tag] if e["kind"] == "OSC"]
        pr("  LANE-CHANGE WINDOWS (laneChangeState != off, +2 s settle): %d;  state census: %s;  direction census: %s" % (
            len(wins), dict(zip(*np.unique(st, return_counts=True))), dict(zip(*np.unique(di, return_counts=True)))))
        pr("   #    t0   dur dir blk |    v ang50 swing | cmdpk idxpk tqpk | amp412 envpk f_rate prom f_inst  f_T |  ampT |T|90 Tsat damp |  coh  ph | P-rail fb-cl |E|50 |E|90 ref50 | eng  hw | OSC-hit operator")
        rows = []
        for i, (a, b) in enumerate(wins):
            s = stats_window(G, C, a, b, tag)
            dirs = lcd100[a:b]; d = "L" if (dirs < 0).sum() > (dirs > 0).sum() else ("R" if (dirs > 0).any() else "-")
            bl = blink[a:b]; bk = "L" if (bl < 0).sum() > (bl > 0).sum() else ("R" if (bl > 0).any() else "-")
            ta, tb_ = G["t"][a], G["t"][b - 1]
            hit = [e for e in osc if not (e["t0"] + e["dur"] < ta or e["t0"] > tb_)]
            opin = [o[0] for o in ops if ta - 3 <= o[2] <= tb_ + 3]
            s.update(t0=float(ta), dur=float((b - a) / FS), dir=d, blink=bk, osc_hit=[e["t0"] for e in hit], operator=opin)
            rows.append(s)
            pr("  %2d %6.1f %5.1f  %s   %s  | %4.1f %5.1f %5.1f | %5.0f %5.0f %5.0f | %6.1f %5.0f %6.2f %4.0f %6.2f %5.2f | %5.0f %5.0f %4.2f %4.2f | %4.2f %4.0f | %6.4f %6.4f %5.0f %5.0f %5.1f | %4.2f %4.2f | %s %s" % (
                i, ta, s["dur"], d, bk, s["v"], s["ang50"], s["swing"], s["cmd_pk"], s["idx_pk"], s["tq_pk"], s["amp412"], s["env_pk"],
                s["f_rate"], s["prom"], s["f_inst"], s["f_T"], s["amp_T"], s["absT90"], s["T_sat"], s["damp"], s["coh"], s["ph"],
                s["p_rail"], s["fb_cl"], s["absE50"], s["absE90"], s["ref50"], s["eng"], s["hw"],
                ("OSC@" + ",".join("%.1f" % t for t in s["osc_hit"])) if hit else "-", ("OP " + ",".join(opin)) if opin else ""))
        # which OSC episodes are NOT inside a lane-change window?
        orphan = [e["t0"] for e in osc if not any(w for w in wins if not (e["t0"] + e["dur"] < G["t"][w[0]] or e["t0"] > G["t"][w[1] - 1]))]
        pr("  OSC episodes outside any lane-change window: %s" % (["%.1f" % t for t in orphan] or "none"))
        out[tag] = dict(anchor=dict(off_gps=off_gps, off_clk=off_clk, t0=float(t0)), operator=ops, windows=rows, orphan=orphan)
        # operator +-10 s readouts
        for hhmmss, seg, tr, seg_calc in ops:
            a, b = int(round((tr - 10) * FS)), int(round((tr + 10) * FS))
            a, b = max(a, 0), min(b, len(G["t"]))
            pr("  ---- OPERATOR EXAMPLE %s (route t %.1f, seg %d): +-10 s, 0.5 s bins ----" % (hhmmss, tr, seg))
            pr("     t     v   ang   cmd  idx  env |T|  lcState eng")
            names = {0: "off", 1: "pre", 2: "starting", 3: "finishing"}
            for k in range(a, b, 50):
                w = slice(k, min(k + 50, b))
                pr("  %6.1f %5.1f %5.1f %5.0f %4.0f %4.0f %4.0f  %-9s %s" % (
                    G["t"][k], G["v"][w].mean(), G["ang"][w].mean(), G["cmd"][w].mean(), G["idx"][w].mean(), G["env"][w].max(),
                    np.abs(G["T"][w]).mean(), names[int(np.median(lcs100[w]))], "E" if G["eng"][w].mean() > 0.5 else "-"))
            # the ringing part: frames in +-10 s with env > ENV_THR, contiguous
            ring = L.merge_runs((G["env"] > L.ENV_THR) & np.isin(np.arange(len(G["t"])), np.arange(a, b)), int(0.5 * FS), int(0.5 * FS))
            for ra, rb in ring:
                s = stats_window(G, C, ra, rb, tag)
                pr("   RING %.1f-%.1f s: v %.1f  ang %.1f (swing %.1f)  cmd pk %.0f  idx pk %.0f  tq pk %.0f | rate 4-12 amp %.1f deg/s, env pk %.0f, f %.2f Hz (Welch, prom %.0f) / %.2f (Hilbert); T f %.2f, amp %.0f, |T|90 %.0f, sat %.3f, damping %.2f | cmd coh %.2f ph %+.0f | P-rail %.4f fb-clamp %.4f |E| p50/p90 %.0f/%.0f ref %.1f deg/s" % (
                    G["t"][ra], G["t"][rb - 1], s["v"], s["ang50"], s["swing"], s["cmd_pk"], s["idx_pk"], s["tq_pk"], s["amp412"], s["env_pk"],
                    s["f_rate"], s["prom"], s["f_inst"], s["f_T"], s["amp_T"], s["absT90"], s["T_sat"], s["damp"], s["coh"], s["ph"],
                    s["p_rail"], s["fb_cl"], s["absE50"], s["absE90"], s["ref50"]))
            # whole +-10 s spectra of rate and T
            for nm, x in (("rate", G["rate"][a:b]), ("T", G["T"][a:b]), ("cmd", G["cmd"][a:b])):
                f, P = signal.welch(x - x.mean(), fs=FS, nperseg=256)
                sel = (f >= 2) & (f < 15); j = int(np.argmax(P[sel]))
                pr("   spectrum %-4s +-10 s: peak %.2f Hz (prom %.0f), band power 2-4/4-8/8-12: %.0f/%.0f/%.0f" % (
                    nm, f[sel][j], P[sel][j] / np.median(P[sel]), *[P[(f >= lo) & (f < hi)].sum() * (f[1] - f[0]) for lo, hi in ((2, 4), (4, 8), (8, 12))]))
    open(os.path.join(HERE, "LANECHANGE-windows.txt"), "w", encoding="utf-8").write("\n".join(lines))
    json.dump(out, open(os.path.join(HERE, "lanechange_windows.json"), "w"), indent=1, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else (bool(o) if isinstance(o, np.bool_) else str(o)))


if __name__ == "__main__":
    main()
