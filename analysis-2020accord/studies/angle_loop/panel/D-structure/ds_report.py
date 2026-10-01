# -*- coding: utf-8 -*-
"""ds_report.py -- collects every D-structure result file into the markdown tables the design page quotes (so every
number on the page comes from a script run, not from prose).  ANALYSIS ONLY.  usage: python ds_report.py
Inputs (_scratch/angle_loop/D-structure/): final_env.json, final_tables.json, gate_final_<id>.json, final_retw.json,
time_final.json.  Output: panel/D-structure/ds_report_out.md"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ds_gate2 as G2  # noqa: E402
import ds_final as F  # noqa: E402
import ds_explore as X  # noqa: E402

OUT = G2.OUT
IDS = list(F.CANDS)
L = []


def P(s=""):
    L.append(s)


def fmt(x, n=1):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "inf" if x == float("inf") else "-"
    return f"{x:.{n}f}"


def gate_tables():
    tb = F.tables()
    res = {k: json.loads((OUT / f"gate_final_{k}.json").read_text()) for k in IDS if (OUT / f"gate_final_{k}.json").exists()}
    P("### GATE 2, full grid (1-35 m/s at 0.25 + the plant knots, 145 speeds), every member: min PM (deg) and the speed")
    P("")
    P("Tier A bar 45 deg, tier B bar 30 deg; `+h10` = slot 4 ten ticks late (hold ages 11-20).  **bold** = below the bar.")
    P("")
    P("| member | tier | " + " | ".join(IDS) + " |")
    P("|---|---|" + "---|" * len(IDS))
    for m in G2.ALL:
        t = G2.tier(m)
        cells = []
        for k in IDS:
            rr = [r for r in res.get(k, []) if r["member"] == m]
            if not rr:
                cells.append("-")
                continue
            r = min(rr, key=lambda q: q["pm"] if math.isfinite(q["pm"]) else 999)
            bar = G2.PMBAR.get(m, 30.0)
            s = f"{r['pm']:.1f} ({r['v']:g})"
            cells.append(f"**{s}**" if (t != "report" and r["pm"] < bar) else s)
        P(f"| {m} | {t} | " + " | ".join(cells) + " |")
    P("")
    P("### GATE 2 summary per candidate (gated members only unless stated)")
    P("")
    P("| id | gated points | FAILS (PM/GM/rho/T530/M20/L20) | min exact GM dB (member, v) | max rho | least-damped 0.3-8 Hz "
      "pole (member, v) | max M20 (V295) | max L20/V295 | max T530 dB | max Tr 1.6-3 Hz (member) | report: worst PM "
      "(member, v) |")
    P("|---|---|---|---|---|---|---|---|---|---|---|")
    for k in IDS:
        rr = res.get(k, [])
        if not rr:
            continue
        g = [r for r in rr if G2.tier(r["member"]) in ("A", "B")]
        fl = G2.fails(rr)
        gm = min(g, key=lambda r: r.get("gm_exact", r["gm_lti"]))
        lo = min(g, key=lambda r: r["low"][1] if math.isfinite(r["low"][1]) else 9)
        tr = max(g, key=lambda r: r.get("Tr163", 0))
        rep = [r for r in rr if G2.tier(r["member"]) == "report"]
        wr = min(rep, key=lambda r: r["pm"] if math.isfinite(r["pm"]) else 999)
        kinds = {}
        for f_ in fl:
            for b in f_[2]:
                kinds[b] = kinds.get(b, 0) + 1
        fs = ", ".join(f"{a} {b}" for a, b in kinds.items()) or "0"
        P(f"| {k} | {len(g)} | {len(fl)} ({fs}) | {gm.get('gm_exact', gm['gm_lti']):.1f} ({gm['member']}, {gm['v']:g}) | "
          f"{max(r['rho'] for r in g):.4f} | {lo['low'][0]:.2f} Hz z {lo['low'][1]:.3f} ({lo['member']}, {lo['v']:g}) | "
          f"{max(r['M20'] for r in g):.2f} ({max(r['M20_v295'] for r in g):.2f}) | "
          f"{max(r['L20'] / r['L20_v295'] for r in g):.3f} | "
          f"{max(max(r['Tc530'], r.get('Tr530', -99)) for r in g):+.1f} | {tr.get('Tr163', 0):.2f} ({tr['member']}, "
          f"{tr['v']:g}) | {wr['pm']:.1f} ({wr['member']}, {wr['v']:g}) |")
    P("")
    P("### The gated fails, listed")
    for k in IDS:
        fl = G2.fails(res.get(k, []))
        if fl:
            by = {}
            for m, v, b in fl:
                by.setdefault((m, tuple(b)), []).append(v)
            P(f"- **{k}**: " + "; ".join(f"{m} {'/'.join(b)} at {min(vs):g}-{max(vs):g} m/s ({len(vs)} pts)"
                                       for (m, b), vs in by.items()))
        else:
            P(f"- **{k}**: none")
    return res


def env_tables():
    env = json.loads((OUT / "final_env.json").read_text())
    tb = F.tables()
    vs = (1.0, 3.1, 5.0, 8.0, 10.0, 11.75, 12.5, 15.0, 17.0, 19.0, 22.0, 26.9, 30.0)
    P("### What each structure buys: the angle stiffness of the FITTED table (T counts per degree of error at DC, "
      "P path), and the envelope it sits under")
    P("")
    P("| id | " + " | ".join(f"{v:g}" for v in vs) + " |")
    P("|---|" + "---|" * len(vs))
    for k, des in F.CANDS.items():
        P(f"| {k} | " + " | ".join(f"{0.1602 * X.p_per_deg(des, G2.G_at(v, tb[k])):.0f}" for v in vs) + " |")
    P("")
    P("| id (envelope binding member at 3.1 / 11.75 / 17 / 26.9 m/s) | " + " | ".join(f"{v:g}" for v in (3.1, 11.75, 17.0,
                                                                                                         26.9)) + " |")
    P("|---|---|---|---|---|")
    for k in IDS:
        e = env[k]
        b = e["bind"]
        g = {float(a): x for a, x in b.items()}
        P(f"| {k} | " + " | ".join(str(g[min(g, key=lambda q: abs(q - v))]) for v in (3.1, 11.75, 17.0, 26.9)) + " |")


def retw_table():
    r = json.loads((OUT / "final_retw.json").read_text())
    fr = (5, 7, 10, 13, 15, 17, 20, 25)
    P("### Re(T/w), T counts per deg/s (> 0 damps), worst over 1-35 m/s, the EMA rate model; V294/V295/V282 same model")
    P("")
    P("| ctl | age | " + " | ".join(f"{f} Hz" for f in fr) + " |")
    P("|---|---|" + "---|" * len(fr))
    for ea in ("0", "10"):
        for nm in ("V294", "V295", "V282"):
            P(f"| {nm} | {ea} | " + " | ".join(f"{x:+.2f}" for x in r["B0"][ea][nm]) + " |")
        for k in IDS:
            P(f"| {k} | {ea} | " + " | ".join(f"{x:+.2f}" for x in r[k][ea]["worst"]) + " |")


def time_tables():
    p = OUT / "time_final.json"
    if not p.exists():
        P("(time suite not run)")
        return
    d = json.loads(p.read_text())
    labels = d["labels"]
    res = d["results"]

    def get(name, v, mem, key):
        for r in res:
            if r["name"] == name and abs(r["v"] - v) < 1e-9 and r["member"] == mem and key in r["metrics"]:
                return r["metrics"][key]
        return None
    speeds = sorted(set(r["v"] for r in res))
    for mem in ("nominal", "bc"):
        P(f"### Time domain, member **{mem}** (ds_time.run: harness_time's plant / scenarios / metrics, the integer lane, "
          f"EMA rate sensor, fixed seed 11)")
        P("")
        rows = [("tracking 0.2 Hz fit gain", "s02", "fit_gain", 2), ("tracking 0.2 Hz phase deg", "s02", "phase_deg", 0),
                ("tracking 0.5 Hz fit gain", "s05", "fit_gain", 2), ("turn-hold ratio", "rh", "hold_ratio", 3),
                ("dwell-then-jump events (s02+s05+ssm)", ("s02", "s05", "ssm"), "dj_events", 0),
                ("stick % (s02)", "s02", "stick_pct", 0), ("+-1 deg fit gain (ssm)", "ssm", "fit_gain", 2),
                ("hold slips (rh)", "rh", "hold_slips", 0), ("dead zone: hold error deg (rh)", "rh", "ess_turn", 2),
                ("hunt p2p deg (rh holds)", "rh", "hunt_p2p", 2), ("step overshoot %", "st", "overshoot_pct", 0),
                ("lurch, FIRM hand (tq 2400): overshoot deg", "ov_fade", "lurch_overshoot", 2),
                ("lurch, LIGHT hand tq 400: overshoot deg", "ov_light400", "lurch_overshoot", 2),
                ("lurch, light hand tq 1000: overshoot deg", "ov_light1000", "lurch_overshoot", 2),
                ("override-latch overshoot deg", "ov_latch", "lurch_overshoot", 2),
                ("engage droop deg", "eng_load", "droop", 2), ("engage peak T", "eng_load", "peakT", 0),
                ("sentinel push deg toward the sentinel (L / R worst; <= 0 = none)", ("sen_L16", "sen_R16"), "sen_excursion", 2),
                ("request-drop excursion deg (meas / zero worst)", ("dis_meas", "dis_zero"), "dis_excursion", 2),
                ("5-30 Hz T rms in holds (texture)", "rh", "T_hf", 2), ("5-30 Hz T rms (s05)", "s05", "T_hf", 2),
                ("40-200 Hz T rms (s05)", "s05", "T_100", 2),
                ("hard-turn 1.6-3 Hz wheel rate rms / ref", "rh", ("hard16", "hard16_ref"), 2),
                ("detector max abs(gp-0x6c2c) / 12800 (all scen.)", "ALL", "det_max_frac", 2),
                ("detector max reversals (all scen.)", "ALL", "det_count", 0),
                ("int32 wraps (all scen.)", "ALL", "wraps", 0)]
        for v in speeds:
            P(f"**{v:g} m/s**")
            P("")
            P("| metric | " + " | ".join(labels) + " |")
            P("|---|" + "---|" * len(labels))
            for title, scn, key, nd in rows:
                vals = []
                for j in range(len(labels)):
                    if scn == "ALL":
                        xs = [r["metrics"][key][j] for r in res if abs(r["v"] - v) < 1e-9 and r["member"] == mem
                              and key in r["metrics"]]
                        x = max(xs) if xs else None
                    elif isinstance(scn, tuple):
                        xs = [get(s, v, mem, key) for s in scn]
                        xs = [q[j] for q in xs if q is not None]
                        x = (sum(xs) if key == "dj_events" else max(xs)) if xs else None
                    elif isinstance(key, tuple):
                        a, b = get(scn, v, mem, key[0]), get(scn, v, mem, key[1])
                        x = f"{a[j]:.2f}/{b[j]:.2f}" if a is not None else None
                    else:
                        q = get(scn, v, mem, key)
                        x = q[j] if q is not None else None
                    vals.append(x if isinstance(x, str) else (fmt(x, nd) if x is not None else "-"))
                P(f"| {title} | " + " | ".join(vals) + " |")
            P("")


if __name__ == "__main__" and not (len(sys.argv) > 1 and sys.argv[1] == "summary"):
    which = sys.argv[1:] or ["env", "gate", "retw", "time"]
    if "env" in which:
        env_tables()
        P("")
    if "gate" in which:
        gate_tables()
        P("")
    if "retw" in which:
        retw_table()
        P("")
    if "time" in which:
        time_tables()
    (HERE / "ds_report_out.md").write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {len(L)} lines")


def time_summary():
    """one row per candidate: the time-domain gates condensed by speed band (max or sum as labelled)."""
    p = OUT / "time_final.json"
    d = json.loads(p.read_text())
    labels, res = d["labels"], d["results"]

    def vals(name, key, mem, vlo, vhi, j, agg=max):
        xs = [r["metrics"][key][j] for r in res if r["name"] in (name if isinstance(name, tuple) else (name,))
              and r["member"] == mem and vlo <= r["v"] <= vhi and key in r["metrics"]]
        return agg(xs) if xs else None
    P("### Time-domain gates condensed (nominal / bc); speeds 3 5 8 10 12.5 15 19 26 30 m/s")
    P("")
    P("| id | dj events 3-5 m/s (s02+s05+ssm) | dj 8-12.5 | dj 15-30 | stick % 3 m/s | hold slips 15-30 (rh) | "
      "turn-hold min >= 8 | s02 fit gain >= 8 (min-max) | s05 fit gain >= 8 (min-max) | step overshoot % max | "
      "lurch firm deg max | lurch light 400 max | light 1000 max | engage droop max | sentinel push deg (toward the sentinel, max) | "
      "T 5-30 Hz rms max (holds) | T 40-200 Hz rms max (s05) | detector max frac / reversals | int32 wraps |")
    P("|" + "---|" * 20)
    for j, k in enumerate(labels):
        cells = []
        for mem in ("nominal", "bc"):
            pass

        def both(fn):
            a, b = fn("nominal"), fn("bc")
            f = lambda x: "-" if x is None else (x if isinstance(x, str) else f"{x:.2f}".rstrip("0").rstrip("."))  # noqa
            return f"{f(a)} / {f(b)}"
        dj = lambda lo, hi: (lambda m: vals(("s02", "s05", "ssm"), "dj_events", m, lo, hi, j, sum))  # noqa: E731
        cells.append(both(dj(3, 5)))
        cells.append(both(dj(8, 12.5)))
        cells.append(both(dj(15, 30)))
        cells.append(both(lambda m: vals("s02", "stick_pct", m, 3, 3, j)))
        cells.append(both(lambda m: vals("rh", "hold_slips", m, 15, 30, j, sum)))
        cells.append(both(lambda m: vals("rh", "hold_ratio", m, 8, 30, j, min)))
        cells.append(both(lambda m: f"{vals('s02', 'fit_gain', m, 8, 30, j, min):.2f}-{vals('s02', 'fit_gain', m, 8, 30, j, max):.2f}"))
        cells.append(both(lambda m: f"{vals('s05', 'fit_gain', m, 8, 30, j, min):.2f}-{vals('s05', 'fit_gain', m, 8, 30, j, max):.2f}"))
        cells.append(both(lambda m: vals("st", "overshoot_pct", m, 3, 30, j)))
        cells.append(both(lambda m: vals("ov_fade", "lurch_overshoot", m, 3, 30, j)))
        cells.append(both(lambda m: vals("ov_light400", "lurch_overshoot", m, 3, 30, j)))
        cells.append(both(lambda m: vals("ov_light1000", "lurch_overshoot", m, 3, 30, j)))
        cells.append(both(lambda m: vals("eng_load", "droop", m, 3, 30, j)))
        cells.append(both(lambda m: vals(("sen_L16", "sen_R16"), "sen_excursion", m, 3, 30, j)))
        cells.append(both(lambda m: vals("rh", "T_hf", m, 3, 30, j)))
        cells.append(both(lambda m: vals("s05", "T_100", m, 3, 30, j)))
        cells.append(both(lambda m: f"{max(r['metrics']['det_max_frac'][j] for r in res if r['member'] == m):.3f}/"
                                    f"{int(max(r['metrics']['det_count'][j] for r in res if r['member'] == m))}"))
        cells.append(both(lambda m: int(sum(r["metrics"]["wraps"][j] for r in res if r["member"] == m and "wraps" in r["metrics"]))))
        P(f"| {k} | " + " | ".join(cells) + " |")
    P("")


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "summary":
    L.clear()
    time_summary()
    (HERE / "ds_report_summary.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
