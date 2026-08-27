#!/usr/bin/env python3
"""Route-37 (V62) inventory, flight-health verdict, and candidate "new grinding" windows.

Three questions, kept separate:
  1. INVENTORY  -- what the route contains, per segment.
  2. FLIGHT HEALTH -- did the ECU stay clean, did the probe stay live, did the bus stay up.
  3. CANDIDATE WINDOWS -- every stretch matching the operator's description of the NEW symptom
     (manual steering effort, LKAS engaged, 8-22 mph) found WITHOUT using their recollection, so
     the spectral pass has a target list that is independent of memory.

Conventions from _r31_common: engagement is LATERAL (cc_lat / 0x18F bit3), effort is SUSTAINED
(3 Hz lowpass), STEER_STATUS is 0x18F byte4 bits 7:4.

Usage:  python studies/sessions/r37/r37_inventory.py
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
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "analysis-2020accord"))
from _r31_common import GEAR, runs_of, sustained  # noqa: E402

CACHE = Path(os.environ.get("R37_CACHE", ROOT / "_scratch/cache/r37"))
SEGS = list(range(15))
WATCH = ["steerUnavailable", "steerTempUnavailable", "canError", "controlsMismatch",
         "steerSaturated"]

# candidate-window criteria for the NEW symptom
V_LO, V_HI = 3.5, 10.0      # m/s  ~ 8-22 mph
TQ_MIN = 300.0              # sustained |torsion-bar torque|
MIN_S = 0.5                 # shortest window worth reporting


def load(s):
    return {k: v for k, v in np.load(CACHE / f"r37s{s}.npz").items()}


def ev(s):
    return json.loads((CACHE / f"r37s{s}_events.json").read_text())


def main():
    D = {s: load(s) for s in SEGS}
    E = {s: ev(s) for s in SEGS}

    # ---------------- 1. INVENTORY ------------------------------------------------------------
    print("=" * 130)
    print("1. ROUTE INVENTORY  (V62, route 75604b0a432fdc89_00000037--6231e33f3d)")
    print("=" * 130)
    hdr = (f"{'seg':>3s} {'dur':>6s} {'n':>6s} {'fs':>6s} | {'vEgo min/med/max':>22s} | "
           f"{'lat%':>6s} | {'|ang| p50/p95':>15s} | {'|tq| p50/p95':>14s} | "
           f"{'|csTq| p50/p95':>14s} | gears")
    print(hdr)
    print("-" * 130)
    tot = Counter()
    for s in SEGS:
        d = D[s]
        fs = 1.0 / np.median(np.diff(d["t"]))
        v = d["cs_v"]; ang = np.abs(d["ang"]); tq = np.abs(d["tq"]); ct = np.abs(d["cs_tq"])
        g = Counter()
        for gv in np.unique(d["cs_gear"]):
            g[GEAR[int(gv)]] = int((d["cs_gear"] == gv).sum())
        tot.update(g)
        gs = " ".join(f"{k}:{c}" for k, c in g.most_common())
        print(f"{s:3d} {d['t'][-1]:6.2f} {len(d['t']):6d} {fs:6.2f} | "
              f"{v.min():6.2f}/{np.median(v):6.2f}/{v.max():6.2f} | "
              f"{100 * (d['cc_lat'] > 0.5).mean():5.1f}% | "
              f"{np.median(ang):6.1f}/{np.percentile(ang, 95):7.1f} | "
              f"{np.median(tq):6.0f}/{np.percentile(tq, 95):6.0f} | "
              f"{np.median(ct):6.0f}/{np.percentile(ct, 95):6.0f} | {gs}")
    allv = np.concatenate([D[s]["cs_v"] for s in SEGS])
    alllat = np.concatenate([D[s]["cc_lat"] for s in SEGS]) > 0.5
    n_all = len(allv)
    print("-" * 130)
    print(f"ROUTE  {sum(D[s]['t'][-1] for s in SEGS):6.2f}s {n_all:6d} frames | "
          f"vEgo {allv.min():.2f}/{np.median(allv):.2f}/{allv.max():.2f} | "
          f"lat {100 * alllat.mean():.1f}% | gears {dict(tot)}")
    ctq = np.concatenate([D[s]["cs_tq"] for s in SEGS])
    btq = np.concatenate([D[s]["tq"] for s in SEGS])
    print(f"       corr(carState.steeringTorque, 0x18F torsion-bar) = "
          f"{np.corrcoef(ctq, btq)[0, 1]:+.5f}   max|diff| = {np.max(np.abs(ctq - btq)):.1f}")

    # ---- STEER_STATUS histogram (0x18F byte4 bits 7:4) ----
    print(f"\n{'seg':>3s} | STEER_STATUS (0x18F b4 bits7:4) histogram")
    print("-" * 130)
    sst_all = Counter()
    for s in SEGS:
        c = Counter(D[s]["sstat"].astype(int).tolist())
        sst_all.update(c)
        print(f"{s:3d} | " + "  ".join(f"{k}:{v}" for k, v in sorted(c.items())))
    print(f"ALL | " + "  ".join(f"{k}:{v}" for k, v in sorted(sst_all.items())))

    # ---- onroadEvents ----
    print(f"\n{'seg':>3s} | " + "  ".join(f"{w[:13]:>13s}" for w in WATCH) +
          f" | {'immDis':>7s} {'softDis':>7s} | {'total':>6s}")
    print("-" * 130)
    names_all = Counter()
    tot_row = Counter()
    for s in SEGS:
        c = Counter(e["name"] for e in E[s])
        names_all.update(c)
        imm = sum(1 for e in E[s] if e["immediate"])
        soft = sum(1 for e in E[s] if e["soft"])
        tot_row["imm"] += imm; tot_row["soft"] += soft; tot_row["tot"] += len(E[s])
        print(f"{s:3d} | " + "  ".join(f"{c.get(w, 0):13d}" for w in WATCH) +
              f" | {imm:7d} {soft:7d} | {len(E[s]):6d}")
    print(f"ALL | " + "  ".join(f"{names_all.get(w, 0):13d}" for w in WATCH) +
          f" | {tot_row['imm']:7d} {tot_row['soft']:7d} | {tot_row['tot']:6d}")
    print("\n  all onroadEvent names seen: " +
          ", ".join(f"{k}={v}" for k, v in names_all.most_common()))

    # ---------------- 2. FLIGHT HEALTH --------------------------------------------------------
    print("\n" + "=" * 130)
    print("2. FLIGHT HEALTH")
    print("=" * 130)
    # 🛑 POLARITY. STEER_STATUS==4 is `no_torque_alert_2` -- the GENTLE EME, a FAULT. The kit's
    # clean-flight criterion is ST==0 everywhere with ZERO ST==4 (V57 0/37,922 + V58 0/83,959 ...).
    # ST==3 is `low_speed_lockout`, the expected sub-5 km/h state (cal 0xC62EA), not a fault.
    order = sorted(SEGS, key=lambda s: float(D[s]["t0_mono"][0]))
    sst = np.concatenate([D[s]["sstat"] for s in order])
    seglen = [len(D[s]["t"]) for s in order]
    bnd = np.cumsum([0] + seglen)
    hist = Counter(sst.astype(int).tolist())
    print(f"   STEER_STATUS histogram (0=normal, 3=low_speed_lockout, 4=no_torque_alert_2/EME, "
          f"5=fault): {dict(sorted(hist.items()))}")
    n4 = hist.get(4, 0)
    n5 = hist.get(5, 0)
    n0 = hist.get(0, 0)
    print(f"   ST == 4 (gentle EME) : {n4} / {len(sst)}     ST == 5 (fault) : {n5}")
    print(f"   ST == 0 (normal)     : {n0} / {len(sst)}  ({100 * n0 / len(sst):.3f}%)")
    print(f"   => the zero-ST==4 streak {'SURVIVES' if n4 == 0 and n5 == 0 else 'IS BROKEN'}; "
          f"this route extends it by {len(sst)} frames "
          f"(>143,000 + {len(sst)} = >{143000 + len(sst)})")
    for val in (3, 4, 5):
        idx = np.flatnonzero(sst == val)
        if not len(idx):
            continue
        loc = Counter()
        for i in idx:
            k = int(np.searchsorted(bnd, i, side="right") - 1)
            loc[order[k]] += 1
        spans = []
        for k, _ in sorted(loc.items()):
            j = np.flatnonzero(D[k]["sstat"] == val)
            spans.append(f"seg{k} n={len(j)} t={D[k]['t'][j[0]]:.2f}-{D[k]['t'][j[-1]]:.2f}s "
                         f"vEgo {D[k]['cs_v'][j].min():.2f}-{D[k]['cs_v'][j].max():.2f}")
        print(f"      ST=={val}: " + " | ".join(spans))

    # message rates
    print("\n   CAN message rates (src 1 arrivals, per segment):")
    print(f"   {'seg':>3s} {'0x14A n':>8s} {'Hz':>7s} {'gap max':>8s} | "
          f"{'0x18F n':>8s} {'Hz':>7s} {'gap max':>8s} | {'0x1FA n':>8s} {'Hz':>7s}")
    for s in SEGS:
        d = D[s]
        row = f"   {s:3d}"
        for a in ("14A", "18F"):
            r = d[f"raw{a}"]
            dur = r[-1] - r[0]
            row += (f" {len(r):8d} {len(r) / dur:7.2f} {np.max(np.diff(r)) * 1e3:7.1f}m |")
        r = d["raw1FA"]
        row += (f" {len(r):8d} {len(r) / max(r[-1] - r[0], 1e-9):7.2f}" if len(r) > 1
                else f" {len(r):8d} {0:7.2f}")
        print(row)

    # probe liveness
    print("\n   V59 PROBE LIVENESS (0x14A byte4):")
    pb = np.concatenate([D[s]["probe"] for s in order]).astype(int)
    field = (pb >> 3) & 0x1F
    low3 = pb & 0x07
    lt512 = (pb & 0x20) != 0
    lt1k = (pb & 0x10) != 0
    lt2k = (pb & 0x08) != 0
    viol = (lt512 & ~lt1k) | (lt1k & ~lt2k)
    print(f"      bit7 (liveness) set : {int(((pb & 0x80) != 0).sum())} / {len(pb)}")
    print(f"      field == 0 (VOID)   : {int((field == 0).sum())} / {len(pb)}")
    print(f"      stock low bits &0x07: {dict(Counter(low3.tolist()))}   "
          f"(stock STEER_SENSOR_STATUS, must be preserved)")
    print(f"      thermometer violations (bit5=>bit4=>bit3): {int(viol.sum())} / {len(pb)}  "
          f"({100 * viol.mean():.4f}%)")
    print(f"      fault sentinel bit6 : {int(((pb & 0x40) != 0).sum())} / {len(pb)}")
    print(f"      byte4 histogram     : " +
          "  ".join(f"0x{v:02X}x{c}" for v, c in Counter(pb.tolist()).most_common(10)))
    print(f"      index<512 {100 * lt512.mean():.2f}%  <1024 {100 * lt1k.mean():.2f}%  "
          f"<2048 {100 * lt2k.mean():.2f}%  >=2048 {100 * (~lt2k).mean():.2f}%")

    # ---------------- 3. CANDIDATE WINDOWS ----------------------------------------------------
    print("\n" + "=" * 130)
    print(f"3. CANDIDATE 'NEW GRINDING' WINDOWS  --  vEgo in [{V_LO},{V_HI}] m/s "
          f"({V_LO * 2.237:.1f}-{V_HI * 2.237:.1f} mph) AND latActive AND "
          f"sustained |tq| > {TQ_MIN:.0f}")
    print("=" * 130)
    import time as _t
    WALL_OFF = 1785517810.5370        # from studies/sessions/r37/r37_wallclock.py

    def scan(v_lo, v_hi, tq_min, label, collect=None):
        print(f"\n   [{label}]  vEgo {v_lo}-{v_hi} m/s ({v_lo * 2.237:.1f}-{v_hi * 2.237:.1f} mph)"
              f", latActive, sustained |tq| > {tq_min:.0f}, >= {MIN_S}s")
        print(f"   {'seg':>3s} {'t_start':>8s} {'t_end':>8s} {'dur':>6s} {'wall':>9s} | "
              f"{'vEgo m/s':>21s} | {'|ang| deg':>19s} | {'sust|tq|':>19s} | "
              f"{'|tq|max':>7s} {'prs%':>5s}")
        n_win, tot_s = 0, 0.0
        for s in SEGS:
            d = D[s]
            fs = 1.0 / np.median(np.diff(d["t"]))
            sus = sustained(d["tq"], fs)      # whole segment is one contiguous 100 Hz record
            m = ((d["cs_v"] >= v_lo) & (d["cs_v"] <= v_hi) & (d["cc_lat"] > 0.5)
                 & (sus > tq_min))
            for a, b in runs_of(m, d["t"], int(MIN_S * fs)):
                t0, t1 = d["t"][a], d["t"][b - 1]
                w = _t.strftime("%H:%M:%S", _t.localtime(float(d["t0_mono"][0]) + WALL_OFF + t0))
                v = d["cs_v"][a:b]; an = np.abs(d["ang"][a:b]); su = sus[a:b]
                tqm = float(np.max(np.abs(d["tq"][a:b])))
                prs = 100 * float((d["cs_press"][a:b] > 0.5).mean())
                print(f"   {s:3d} {t0:8.2f} {t1:8.2f} {t1 - t0:6.2f} {w:>9s} | "
                      f"{v.min():5.2f}-{v.max():5.2f} (med{np.median(v):5.2f}) | "
                      f"{an.min():4.0f}-{an.max():4.0f} (med{np.median(an):4.0f}) | "
                      f"{su.min():4.0f}-{su.max():4.0f} (med{np.median(su):4.0f}) | "
                      f"{tqm:7.0f} {prs:4.0f}%")
                n_win += 1; tot_s += t1 - t0
                if collect is not None:
                    collect.append(dict(seg=s, t0=float(t0), t1=float(t1), wall=w,
                                        v_min=float(v.min()), v_max=float(v.max()),
                                        v_med=float(np.median(v)),
                                        ang_med=float(np.median(an)), ang_max=float(an.max()),
                                        sus_med=float(np.median(su)), tq_max=tqm,
                                        pressed_pct=prs))
        print(f"   -> {n_win} windows, {tot_s:.1f} s total")
        return n_win, tot_s

    windows = []
    scan(V_LO, V_HI, TQ_MIN, "PRIMARY -- the operator's stated 8-22 mph band", windows)
    (CACHE / "r37_candidate_windows.json").write_text(json.dumps(windows, indent=1))
    print(f"\n   written: {CACHE / 'r37_candidate_windows.json'}")
    scan(2.0, 12.0, TQ_MIN, "SENSITIVITY -- band widened to 4.5-27 mph")

    # ---------------- 4. ROUGHNESS -- a target list with no free parameters -------------------
    # Sample-to-sample |d(tq)| on the 100 Hz torsion-bar channel. No speed/engagement/effort
    # thresholds at all, so it cannot be tuned to hit the operator's remembered times -- which
    # makes it the honest independent check on the criterion-based windows above.
    print("\n" + "=" * 130)
    print("4. TORSION-BAR ROUGHNESS  --  |d(tq)| per 10 ms sample, no criteria applied")
    print("=" * 130)
    print(f"   {'seg':>3s} {'p50':>6s} {'p95':>6s} {'p99':>6s} {'max':>7s} "
          f"{'n>1000':>7s} {'n>2000':>7s}")
    for s in SEGS:
        g = np.abs(np.diff(D[s]["tq"]))
        print(f"   {s:3d} {np.median(g):6.0f} {np.percentile(g, 95):6.0f} "
              f"{np.percentile(g, 99):6.0f} {g.max():7.0f} "
              f"{int((g > 1000).sum()):7d} {int((g > 2000).sum()):7d}")

    for JUMP in (2000.0, 1000.0):
        bursts = []
        for s in SEGS:
            d = D[s]
            g = np.abs(np.diff(d["tq"]))
            idx = np.flatnonzero(g > JUMP)
            if not len(idx):
                continue
            st = pv = idx[0]
            for k in list(idx[1:]) + [None]:
                if k is None or k - pv > 50:
                    bursts.append((s, float(d["t"][st]), float(d["t"][pv + 1]),
                                   int(((idx >= st) & (idx <= pv)).sum()),
                                   float(g[st:pv + 1].max()), float(d["cs_v"][st]),
                                   float(d["cc_lat"][st]), float(abs(d["ang"][st]))))
                    st = k
                pv = k if k is not None else pv
        print(f"\n   BURSTS with |d(tq)| > {JUMP:.0f} counts/10 ms  ({len(bursts)} found):")
        for s, t0, t1, n, mx, v, lat, an in bursts:
            w = _t.strftime("%H:%M:%S", _t.localtime(float(D[s]["t0_mono"][0]) + WALL_OFF + t0))
            print(f"      seg {s:2d} t={t0:6.2f}-{t1:6.2f}s  wall {w}  n={n:3d}  "
                  f"maxjump={mx:5.0f}  vEgo={v:5.2f} m/s ({v * 2.237:4.1f} mph)  "
                  f"lat={lat:.0f}  |ang|={an:3.0f}deg")

    # the two operator-remembered instants, with a +/-15 s context readout
    print("\n   OPERATOR-REMEMBERED INSTANTS (context readout, +/-15 s):")
    for q, seg_, offs in (("10:12:15", 1, 9.67), ("10:23:24", 12, 18.63)):
        d = D[seg_]
        k = (np.abs(d["t"] - offs)).argmin()
        w = slice(max(0, k - 1500), min(len(d["t"]), k + 1500))
        fs = 1.0 / np.median(np.diff(d["t"]))
        sus = sustained(d["tq"], fs)
        print(f"      {q} = seg {seg_} t={offs:.2f}s : vEgo {d['cs_v'][k]:.2f} m/s "
              f"({d['cs_v'][k] * 2.237:.1f} mph), lat {d['cc_lat'][k]:.0f}, "
              f"ang {d['ang'][k]:+.1f}deg, tq {d['tq'][k]:+.0f}, sust|tq| {sus[k]:.0f}")
        print(f"         +/-15 s: vEgo {d['cs_v'][w].min():.2f}-{d['cs_v'][w].max():.2f}, "
              f"lat {100 * (d['cc_lat'][w] > 0.5).mean():.0f}%, "
              f"|ang| med {np.median(np.abs(d['ang'][w])):.0f} max {np.max(np.abs(d['ang'][w])):.0f}, "
              f"sust|tq| med {np.median(sus[w]):.0f} max {sus[w].max():.0f}")


if __name__ == "__main__":
    main()
