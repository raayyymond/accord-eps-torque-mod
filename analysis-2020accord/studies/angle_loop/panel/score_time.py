# -*- coding: utf-8 -*-
r"""score_time.py -- THE COMMON TIME-DOMAIN SCORER for the angle-loop design panel (created 2026-10-01, reviser 2).

ANALYSIS ONLY.  Builds nothing, flashes nothing, sends nothing; the fork is not touched; no image or .rwd is written.

WHY THIS FILE EXISTS.  The three C2-round-1 refuters each flagged, as a blocking/major finding, that the panel's
COMMON time-domain scorer (`panel/score_time.py`) was never written -- the time scorer halted and produced nothing, so
every candidate's stick-slip / dwell-then-jump / lurch / droop / texture numbers were self-graded under four different
scenario definitions and were "not comparable across designers".  This file closes that gap: ONE identical pipeline,
one scenario suite, one metrics extractor, run on every candidate named in CANDS below.

THE ENGINE (EVIDENCE, reused unchanged): the D-structure time harness `ds_time` -- harness_time's Karnopp plant
(10 kHz sub-steps), its scenarios and its metrics, UNCHANGED, around the integer-exact lane `ds_lane.DSLane` with the
sensor set the structures need (the integer EMA mirror of gp-0x6abe, the 1 kHz accumulator gp-0x6cc4, Honda's
oscillation-detector mirror).  Candidates are built from the SAME source of truth as the freq scorer: `ds_final.CANDS`
(their parameters) and `ds_selftest.lane_cfg` (the integer lane config).  The lane was validated byte-for-byte equal to
c1_lib.LaneC1F (0/40000) and its assembled cave bytes were interpreter-tested 0/60000 (ds_asm H1); this scorer does not
re-assert those, it runs the same lane.

THE MEMBERS.  The nonlinear time symptoms the goal names ride on the Coulomb/stiction terms, so the time gate runs the
FRICTION-bearing members of the brief's credible set: nominal, bc (= b_lo linear + bias-corrected Coulomb), F_hi, F_lo.
The LINEAR combined corners (b_lo*J_hi, b_q*J1.0, +h10 ages, mode13/mode20, ms_free) carry no distinct nonlinear time
signature beyond their frequency-domain margin; those are gated by the COMMON FREQ scorer (score_freq.py), which scores
hold ages 0 AND 10 (= holds 1-10 and 11-20) on every member.  So the two common scorers partition the brief's set:
  - score_freq.py : stability/margin, every member, hold ages 1-20            (the stop-band / PM / GM / 20 Hz gate)
  - score_time.py : nonlinear symptoms, the friction members, native hold age (stick-slip, dj, lurch, droop, texture)
This split is stated so a refuter can reject it if it disagrees; it is not hidden.

usage:   python score_time.py              full suite (members x speeds x scenarios, multiprocessing); writes JSON + table
         python score_time.py quick        nominal + bc only, the track scenarios, faster
         python score_time.py score         re-score the existing JSON cache without re-running the sim
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

HERE = Path(__file__).resolve().parent                        # .../studies/angle_loop/panel
DS = HERE / "D-structure"
for _p in (str(DS), str(HERE.parent / "c1"), str(HERE.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ds_final as F        # noqa: E402  CANDS = the one source of truth for candidate parameters
import ds_selftest as ST    # noqa: E402  lane_cfg(des, table) = the integer lane config
import ds_time as DT        # noqa: E402  the common time engine

OUT = HERE.parent.parent.parent / "_scratch" / "angle_loop" / "panel"
OUT.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------------------------------------------------------
# WHAT TO SCORE.  A successor adds a row here; nothing else changes.  Every id must be a key of ds_final.CANDS.
# ----------------------------------------------------------------------------------------------------------------------
CANDS = ("D2a", "B0r")                     # C2-rev2-B: PRIMARY = D2a, FALLBACK = B0r
MEMBERS = ("nominal", "bc", "F_hi", "F_lo")
SPEEDS = (3.0, 5.0, 8.0, 10.0, 12.5, 15.0, 19.0, 26.0, 30.0)
SCENS = ("rh", "s02", "s05", "ssm", "st", "ov_fade", "ov_light400", "ov_light1000",
         "sen_L16", "sen_R16", "dis_meas", "eng_load")
SCENS_QUICK = ("rh", "s02", "s05", "ssm", "st")

# The GOAL's time-domain bars (THE GOAL, docs/STATE.md).  Each is an absolute, scale-fixed number.
BARS = dict(turnhold=0.90, track_lo=0.95, track_hi=1.05, lurch_firm=8.0, lurch_light=8.0,
            droop=8.0, texture=2.0, sentinel=0.5)


def build_cfgs(ids):
    tb = F.tables()
    return [ST.lane_cfg(F.CANDS[k], tb[k]) for k in ids], list(ids)


# ----------------------------------------------------------------------------------------------------------------------
def run_all(members, scens, speeds, tag):
    cfgs, labels = build_cfgs(CANDS)
    DT.run_suite(cfgs, labels, members, speeds, scens, tag=tag)
    return OUT / f"time_{tag}.json"


def _col(m, key, idx):
    v = m.get(key)
    if v is None:
        return None
    a = np.atleast_1d(np.asarray(v, float))
    return float(a[idx])


def score(tag):
    """read the JSON cache and produce ONE comparable table + a goal-gate verdict per candidate."""
    p = DT.OUT / f"time_{tag}.json"      # ds_time.run_suite writes to its own scratch dir (D-structure/)
    d = json.loads(p.read_text())
    labels = d["labels"]
    res = d["results"]
    B = len(labels)
    # index: (scen, member, v) -> metrics dict
    idx = {(r["name"], r["member"], float(r["v"])): r["metrics"] for r in res}
    speeds = sorted({float(r["v"]) for r in res})
    members = sorted({r["member"] for r in res}, key=lambda x: ("nominal", "bc", "F_hi", "F_lo").index(x)
                     if x in ("nominal", "bc", "F_hi", "F_lo") else 9)
    lines = []

    def P(s=""):
        print(s, flush=True)
        lines.append(s)

    P(f"# COMMON TIME SCORER -- tag {tag}")
    P(f"candidates: {labels}   members: {members}   speeds: {speeds}")
    P("")

    # ---- the condensed per-member table (nominal / bc / F_hi / F_lo), one block per candidate
    gate = {lb: dict() for lb in labels}
    for j, lb in enumerate(labels):
        P("=" * 120)
        P(f"## {lb}: {F.CANDS[labels[j]].name}")
        P("| member | dj 3-5 | dj 8-12.5 | dj 15-30 | stick% 3-5 | slips rh | turn-hold>=8 | s02 gain>=8 "
          "| lurch firm | lurch light400 | droop | texture 5-30 (holds) | tex 40-200 | sentinel push | detector frac |")
        P("|--------|--------|-----------|----------|-----------|----------|--------------|------------"
          "|-----------|---------------|-------|---------------------|-----------|---------------|---------------|")
        for mem in members:
            def band(scns_, key, vlo, vhi, agg="sum"):
                vals = []
                for s in scns_:
                    for v in speeds:
                        if vlo <= v <= vhi and (s, mem, v) in idx:
                            x = _col(idx[(s, mem, v)], key, j)
                            if x is not None:
                                vals.append(x)
                if not vals:
                    return float("nan")
                return float(np.sum(vals)) if agg == "sum" else (float(np.min(vals)) if agg == "min"
                                                                 else float(np.max(vals)))
            dj_lo = band(("s02", "s05", "ssm"), "dj_events", 3.0, 5.0)
            dj_md = band(("s02", "s05", "ssm"), "dj_events", 8.0, 12.5)
            dj_hi = band(("s02", "s05", "ssm"), "dj_events", 15.0, 30.0)
            stick = band(("s02", "s05", "ssm"), "stick_pct", 3.0, 5.0, "max")
            slips = band(("rh",), "hold_slips", 15.0, 30.0)
            th = band(("rh",), "hold_ratio", 8.0, 30.0, "min")
            s02g = band(("s02",), "fit_gain", 8.0, 30.0, "min")
            s02gx = band(("s02",), "fit_gain", 8.0, 30.0, "max")
            lfirm = band(("ov_fade",), "lurch_overshoot", 3.0, 30.0, "max")
            llight = band(("ov_light400",), "lurch_overshoot", 3.0, 30.0, "max")
            droop = band(("eng_load",), "droop", 3.0, 30.0, "max")
            tex = band(("rh",), "T_hf", 3.0, 30.0, "max")
            tex100 = band(("s05",), "T_100", 3.0, 30.0, "max")
            senp = band(("sen_L16", "sen_R16"), "sen_excursion", 3.0, 30.0, "max")
            det = band(("rh", "s05", "ov_fade", "eng_load"), "det_max_frac", 3.0, 30.0, "max")
            P(f"| {mem:6s} | {dj_lo:.0f} | {dj_md:.0f} | {dj_hi:.0f} | {stick:.1f} | {slips:.0f} | {th:.2f} "
              f"| {s02g:.2f}-{s02gx:.2f} | {lfirm:.1f} | {llight:.1f} | {droop:.1f} | {tex:.2f} | {tex100:.2f} "
              f"| {senp:.2f} | {det:.3f} |")
            if mem in ("nominal", "bc"):
                g = gate[lb].setdefault(mem, {})
                g["turnhold"] = th
                g["track_lo"] = s02g
                g["track_hi"] = s02gx
                g["lurch_firm"] = lfirm
                g["lurch_light"] = llight
                g["droop"] = droop
                g["texture"] = tex
                g["sentinel"] = senp
                g["dj_hi"] = dj_hi
                g["det"] = det
        P("")

    # ---- the goal-gate verdict (nominal + bc), each criterion marked PASS / MISS
    P("=" * 120)
    P("## GOAL-GATE VERDICT (nominal + bc; absolute bars from THE GOAL)")
    P("| candidate | member | turn-hold>=0.90 | track 0.95-1.05 | lurch firm<=8 | lurch light<=8 | droop<=8 "
      "| texture<=2.0 | sentinel<=0.5 | dj 15-30=0 | detector<1 |")
    P("|-----------|--------|-----------------|-----------------|---------------|----------------|---------"
      "|--------------|---------------|-----------|------------|")
    verdict = {}
    for lb in labels:
        vv = {}
        for mem in ("nominal", "bc"):
            g = gate[lb].get(mem, {})
            if not g:
                continue
            chk = dict(
                turnhold=g["turnhold"] >= BARS["turnhold"] - 1e-9,
                track=(g["track_lo"] >= BARS["track_lo"] - 1e-9) and (g["track_hi"] <= BARS["track_hi"] + 1e-9),
                lurch_firm=g["lurch_firm"] <= BARS["lurch_firm"] + 1e-9,
                lurch_light=g["lurch_light"] <= BARS["lurch_light"] + 1e-9,
                droop=g["droop"] <= BARS["droop"] + 1e-9,
                texture=g["texture"] <= BARS["texture"] + 1e-9,
                sentinel=g["sentinel"] <= BARS["sentinel"] + 1e-9,
                dj_hi=g["dj_hi"] <= 0.5,
                det=g["det"] < 1.0,
            )
            vv[mem] = chk

            def mk(b):
                return "PASS" if b else "**MISS**"
            P(f"| {lb} | {mem} | {mk(chk['turnhold'])} ({g['turnhold']:.2f}) "
              f"| {mk(chk['track'])} ({g['track_lo']:.2f}-{g['track_hi']:.2f}) "
              f"| {mk(chk['lurch_firm'])} ({g['lurch_firm']:.1f}) | {mk(chk['lurch_light'])} ({g['lurch_light']:.1f}) "
              f"| {mk(chk['droop'])} ({g['droop']:.1f}) | {mk(chk['texture'])} ({g['texture']:.2f}) "
              f"| {mk(chk['sentinel'])} ({g['sentinel']:.2f}) | {mk(chk['dj_hi'])} ({g['dj_hi']:.0f}) "
              f"| {mk(chk['det'])} ({g['det']:.3f}) |")
        verdict[lb] = vv
    (DS.parent / f"SCORE-TIME-{tag}.txt").write_text("\n".join(lines), encoding="utf-8")
    (OUT / f"score_time_verdict_{tag}.json").write_text(json.dumps(verdict, indent=1))
    return verdict


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "full"
    if which == "quick":
        run_all(("nominal", "bc"), SCENS_QUICK, SPEEDS, "c2rev2B_quick")
        score("c2rev2B_quick")
    elif which == "score":
        score(sys.argv[2] if len(sys.argv) > 2 else "c2rev2B")
    else:
        t0 = time.time()
        run_all(MEMBERS, SCENS, SPEEDS, "c2rev2B")
        print(f"[sim {time.time() - t0:.0f} s]", flush=True)
        score("c2rev2B")
