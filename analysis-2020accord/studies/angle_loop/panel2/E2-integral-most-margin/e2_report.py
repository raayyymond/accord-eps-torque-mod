# -*- coding: utf-8 -*-
r"""e2_report.py -- every table of the E2 design page, generated from the cached runs (e2_final.py ext / suite,
e2_k0.py, e2_freq.py).  ANALYSIS ONLY.  usage: python e2_report.py  (writes e2_report_out.md)"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from e2_common import OUT  # noqa: E402
import e2_exp as X  # noqa: E402
import e2_explore as EX  # noqa: E402
import e2_final as F  # noqa: E402

LAB = F.LAB
O = []


def P(s=""):
    O.append(s)
    print(s)


def tab(head, rows):
    P("| " + " | ".join(head) + " |")
    P("|" + "|".join(["---"] * len(head)) + "|")
    for r in rows:
        P("| " + " | ".join(str(x) for x in r) + " |")
    P()


def ext():
    res = json.loads((OUT / "exp_final_ext.json").read_text())
    # ---------------- turn-hold
    P("### T1. Turn-hold sized from r71b (min hold ratio over 8-30 m/s; target = a * L * SR / v^2, capped 90 deg)")
    rows = []
    for m in EX.MEM4:
        for a in EX.ALAT:
            rr = [x for x in res if x["spec"][0] == "th" and x["member"] == m and abs(x["spec"][2] - EX.tgt(x["spec"][1], a)) < 1e-9]
            mn = np.min([x["m"]["hold"] for x in rr], axis=0)
            rows.append([m, f"{a:.1f}"] + [f"{h:.3f}" for h in mn])
    tab(["member", "a (m/s2)"] + LAB, rows)
    # ---------------- r71b goal metric
    P("### T2. The goal's tracking metric on r71b's own angle paths (OLS slope, 0.5 Hz LPF), clean / with r71b's torque word replayed")
    sl = X.rr_slopes(res, len(LAB))
    rows = []
    for band in ("8-15", "15-22", ">22"):
        for rp in (False, True):
            vals = np.min([sl[(band, rp, m)] for m in EX.MEM4], axis=0)
            rows.append([band, "replay" if rp else "clean", "min of 4 members"] + [f"{x:.3f}" for x in vals])
    for rp in (False, True):
        du = np.mean([x["m"]["frz_duty"] for x in res if x["spec"][0] == "rr" and x["spec"][3] == rp], axis=0)
        rows.append(["all", "replay" if rp else "clean", "I freeze/leak duty"] + [f"{d:.3f}" for d in du])
    tab(["band", "torque word", "statistic"] + LAB, rows)
    # ---------------- lurch
    P("### T3. Release lurch (overshoot past the setpoint after the hand lets go), max over speeds; >= 8 m/s | < 8 m/s")
    kinds = [("lh", 100), ("lh", 200), ("lh", 400), ("lh", 511), ("lk", 0.15), ("lk", 0.6), ("lk", 2.0),
             ("ls", 300.0, 0.6), ("ls", 300.0, 2.0), ("ov", 33)]
    names = {("lh", 100): "stiff hand, word 100", ("lh", 200): "stiff hand, word 200", ("lh", 400): "stiff hand, word 400",
             ("lh", 511): "stiff hand, word 511", ("lk", 0.15): "stiff hand, sensor kappa 0.15",
             ("lk", 0.6): "stiff hand, sensor kappa 0.6", ("lk", 2.0): "stiff hand, sensor kappa 2.0",
             ("ls", 300.0, 0.6): "300 T torque hand, word 500", ("ls", 300.0, 2.0): "300 T torque hand, word 150",
             ("ov", 33): "FIRM hand, word 2400"}
    worst = {}
    for m in EX.LURCH_MEM:
        rows = []
        for kd in kinds:
            rr = [x for x in res if x["member"] == m and tuple(x["spec"][:1] + x["spec"][2:]) == kd]
            hi = np.max([x["m"]["lurch"] for x in rr if x["spec"][1] >= 8.0], axis=0)
            lo = np.max([x["m"]["lurch"] for x in rr if x["spec"][1] < 8.0], axis=0)
            rows.append([names[kd]] + [f"{h:.2f} / {l:.1f}" for h, l in zip(hi, lo)])
            worst.setdefault(m, []).append(hi)
        P(f"**{m}**")
        tab(["hand"] + LAB, rows)
    P("**worst lurch over every hand model, >= 8 m/s**")
    tab(["member"] + LAB, [[m] + [f"{x:.2f}" for x in np.max(worst[m], axis=0)] for m in EX.LURCH_MEM])
    P("### T3b. After the release: return time to within 10 % (s) and the shortfall 0.5-3 s after (deg), max over >= 8 m/s")
    rows = []
    for m in ("nominal", "b_lo*J_hi"):
        for kd in (("lh", 400), ("lk", 0.6), ("ov", 33)):
            rr = [x for x in res if x["member"] == m and tuple(x["spec"][:1] + x["spec"][2:]) == kd and x["spec"][1] >= 8]
            rs = np.max([x["m"]["return_s"] for x in rr], axis=0)
            un = np.max([x["m"]["under"] for x in rr], axis=0)
            rows.append([m, names[kd]] + [f"{a:.2f} s / {b:.2f}" for a, b in zip(rs, un)])
    tab(["member", "hand"] + LAB, rows)
    # ---------------- droop
    P("### T4. Engage under a handed-over load: max droop (deg), >= 8 m/s | all speeds; stock ramp-in (0.99 s) and the 6803 == 2 ramp-in (0.10 s)")
    rows = []
    for m in EX.LURCH_MEM:
        for ri in (33, 328):
            rr = [x for x in res if x["spec"][0] == "eng" and x["member"] == m and x["spec"][2] == ri]
            hi = np.max([x["m"]["droop"] for x in rr if x["spec"][1] >= 8.0], axis=0)
            al = np.max([x["m"]["droop"] for x in rr], axis=0)
            ov = np.max([x["m"]["eng_ovs"] for x in rr], axis=0)
            rows.append([m, "0.99 s" if ri == 33 else "0.10 s"] + [f"{h:.2f} / {a:.2f} (ovs {o:.2f})" for h, a, o in zip(hi, al, ov)])
    tab(["member", "ramp-in"] + LAB, rows)


def suite():
    p = OUT / "final_suite.json"
    if not p.exists():
        P("(final_suite.json not present)")
        return
    d = json.loads(p.read_text())
    res = d["results"]
    P("### T5. THE COMMON TIME SCORER, its own scenarios / speeds / members / metrics (score_time.SCENS x SPEEDS x MEMBERS)")

    def agg(name, key, fn, vmin=None):
        rr = [x for x in res if x["name"] == name and (vmin is None or x["v"] >= vmin)]
        if not rr:
            return [np.nan] * len(LAB)
        return fn(np.array([x["metrics"][key] for x in rr]), axis=0)
    rows = [
        ["rh hold ratio, min >= 8 m/s (bar >= 0.90)", agg("rh", "hold_ratio", np.min, 8.0)],
        ["T 5-30 Hz in holds, max (bar <= 2.0)", agg("rh", "T_hf", np.max)],
        ["detector reversals, max (bar 0)", np.max([agg(s, "det_count", np.max) for s in ("rh", "s02", "s05", "ssm", "st")], axis=0)],
        ["sentinel push toward, max deg (bar <= 0.1)", np.max([agg(s, "sen_excursion", np.max) for s in ("sen_L16", "sen_R16")], axis=0)],
        ["tmo abs(T) after sentinel + 0.25 s, max (bar < 50)", agg("tmo", "tmo_T_after", np.max)],
        ["int32 wraps", np.max([agg(s, "wraps", np.max) for s in ("rh", "s02", "ov_fade", "tmo")], axis=0)],
        ["s02 wire gain, min >= 8 m/s", agg("s02", "track_gain", np.min, 8.0)],
        ["s05 wire gain, min >= 8 m/s", agg("s05", "track_gain", np.min, 8.0)],
        ["dwell-then-jump events s02+s05+ssm, sum >= 8 m/s", np.sum([agg(s, "dj_events", np.sum, 8.0) for s in ("s02", "s05", "ssm")], axis=0)],
        ["dwell-then-jump events s02+s05+ssm, sum < 8 m/s", np.sum([np.sum([x["metrics"]["dj_events"] for x in res if x["name"] == s and x["v"] < 8], axis=0) for s in ("s02", "s05", "ssm")], axis=0)],
        ["ov_light400 (unsigned word) lurch, max >= 8 m/s", agg("ov_light400", "lurch_overshoot", np.max, 8.0)],
        ["ov_light1000 lurch, max >= 8 m/s", agg("ov_light1000", "lurch_overshoot", np.max, 8.0)],
        ["ov_fade (firm) lurch, max >= 8 m/s", agg("ov_fade", "lurch_overshoot", np.max, 8.0)],
        ["eng_load droop, max >= 8 m/s", agg("eng_load", "droop", np.max, 8.0)],
        ["co-steer release droop, max", agg("cs", "cs_droop", np.max)],
        ["dead band lag, max >= 8 m/s", agg("db", "db_lag", np.max, 8.0)],
        ["tmo hold deviation, max", agg("tmo", "tmo_hold_dev", np.max)],
        ["hard turn 1.6-3 Hz / command's own, max >= 8 m/s", np.max(np.array([x["metrics"]["hard16"] for x in res if x["name"] == "hard" and x["v"] >= 8]) / np.maximum(np.array([x["metrics"]["hard16_ref"] for x in res if x["name"] == "hard" and x["v"] >= 8]), 1e-9), axis=0)],
    ]
    tab(["metric (every member)"] + LAB, [[r[0]] + [f"{x:.3f}" if isinstance(x, (float, np.floating)) and abs(x) < 100 else f"{x}" for x in r[1]] for r in rows])


if __name__ == "__main__":
    P("# E2 report tables (generated by e2_report.py)")
    P()
    ext()
    suite()
    (HERE / "e2_report_out.md").write_text("\n".join(O) + "\n", encoding="utf-8")
