# -*- coding: utf-8 -*-
"""JUDGE GOAL scoring (panel 2, 2026-10-01): the goal-first rubric applied to the COMMON scorers' own numbers.
Time inputs: panel2/score_time_out/score_time_summary.json (frame vgr, the scorer's primary), plus the judge's graft run
(judge_summary.json, same scorer, same frame, in-batch controls).  Frequency inputs: SCORE-FREQ-2026-10-01.md T0
(constants below, copied from T0 with the row named).  Declaration / verification / hazard points are the judge's
rulings, each with a reason in JUDGE-goal-2026-10-01.md.  usage: python judge_score.py"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_d = HERE
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
KIT = _d.parent
SCR = KIT / "_scratch" / "angle_loop" / "judge-goal"
TS = json.loads((KIT / "analysis-2020accord/studies/angle_loop/panel2/score_time_out/score_time_summary.json")
                .read_text())["vgr"]
J = json.loads((SCR / "judge_summary.json").read_text()) if (SCR / "judge_summary.json").exists() else {}
for k, v in J.items():
    if k.startswith("J-"):
        TS[k] = v


def clip(x, a=0.0, b=1.0):
    return max(a, min(b, x))


HB = ("8-10", "10-12.5", "12.5-15", "15-22", ">22")

# ---- frequency constants: SCORE-FREQ T0 (M20 x V295 ; ReTw 5 Hz ; ReTw 13 Hz, ages 1-10 ; R2-box class)
P2F = (0.68, -0.57, -0.37)
F2F = (0.70, -0.84, -0.84)
FREQ = {"P2": P2F + ("r1",), "F2": F2F + ("r1",), "D2a": P2F + ("r1",), "B0r": F2F + ("r1",),
        "E1-splitP": (0.66, -1.98, -0.67, "rho1"), "E2-K0": (0.68, -0.43, -0.37, "pass"),
        "G-P48d": (0.96, -0.03, -0.37, "decl"), "G-P44d": (0.88, -0.12, -0.36, "decl"),
        "G-P48": (0.96, -0.05, -0.37, "pass"), "G-P44": (0.88, -0.14, -0.36, "pass"),
        "G-F24": (0.82, -0.53, -0.91, "pass"), "G-F24d": (0.82, -0.53, -0.91, "decl"),
        "G-A22": (0.65, -0.94, -0.92, "pass"), "G-A22d": (0.65, -0.94, -0.92, "decl"),
        "G-P48L": (0.97, -0.05, -0.37, "pass"), "G-P48k40": (0.96, -0.17, -0.41, "pass"),
        "H-A": (0.75, -0.40, -0.40, "msf_undecl"), "H-B": (0.79, -0.69, -0.91, "hb"),
        # grafts: the small-signal loop IS the skeleton's (score_freq F1: no integral policy moves GATE 2)
        "J-G48-A3": (0.96, -0.05, -0.37, "pass"), "J-G48-A3-12k": (0.96, -0.05, -0.37, "pass"),
        "J-G44-A3": (0.88, -0.14, -0.36, "pass"), "J-G48d-A3": (0.96, -0.03, -0.37, "decl"),
        "J-F24-A3": (0.82, -0.53, -0.91, "pass")}
for _k in ("E1-reset", "E1-cal", "E1-bleed", "E1-freeze", "E1-sched", "E2-R1", "E2-S", "E2-A2", "E2-A3", "E2-A3-12k",
           "E2-A2-X", "E2-L"):
    FREQ[_k] = P2F + ("p2inh",)
B1 = {"pass": 15, "decl": 12, "msf_undecl": 6, "hb": 5, "p2inh": 3, "r1": 2, "rho1": 0}

# ---- C: verification (6) / declaration accuracy (8) / hazards (6) -- the judge's rulings (reasons in the .md)
C1 = dict.fromkeys(["P2", "F2", "D2a", "B0r", "E1-cal", "E2-R1", "E2-S", "E2-A2", "E2-A3", "E2-A3-12k", "E2-A2-X",
                    "E2-L", "E2-K0", "G-P48d", "G-P44d", "G-P48", "G-P44", "G-F24", "G-F24d", "G-A22", "G-A22d",
                    "G-P48L", "G-P48k40"], 6.0)
C1.update({"E1-reset": 5.0, "E1-freeze": 5.0, "E1-splitP": 5.0, "E1-bleed": 2.0, "E1-sched": 2.0, "H-A": 2.0,
           "H-B": 2.0, "J-G48-A3": 5.5, "J-G48-A3-12k": 5.5, "J-G44-A3": 5.5, "J-G48d-A3": 5.5, "J-F24-A3": 2.0})
C2 = {"P2": 1, "F2": 1, "D2a": 1, "B0r": 1, "E1-reset": 3, "E1-cal": 3, "E1-freeze": 4, "E1-bleed": 5, "E1-sched": 5,
      "E1-splitP": 5, "E2-R1": 7, "E2-S": 7, "E2-A2": 6, "E2-A3": 6, "E2-A3-12k": 6, "E2-A2-X": 6, "E2-L": 7,
      "E2-K0": 7, "H-A": 1, "H-B": 1}
for _k in FREQ:
    if _k.startswith("G-"):
        C2[_k] = 6
    if _k.startswith("J-"):
        C2[_k] = 5
C3 = {}
for _k in FREQ:
    h = 6.0
    fresh = _k in ("P2", "D2a", "H-A") or _k.startswith("E1") or (_k.startswith("E2") and _k != "E2-K0") or \
        _k.startswith("G-P") or _k.startswith("J-G")
    if fresh:
        h -= 1.0                                   # fresh-D sign rests on pol = gp-0x6752 = -1 (H-pol)
    if _k.startswith("E1") and _k != "E1-cal":
        h -= 0.5                                   # new RAM write (the lane's own I cell)
    if _k.startswith("E2-A") or _k.startswith("J-"):
        h -= 0.5                                   # M-E2-4: the bound caps the I under a large constant road load
    if _k == "E2-A2-X":
        h -= 1.0                                   # 0xCBAE4 arm: up to x2.1 lane torque against a hand; fork must keep 2
    if _k == "E2-K0":
        h -= 3.0                                   # fork integral load-bearing, fork code beyond the angle interface
    if _k.startswith("G-A22"):
        h -= 2.0                                   # two RAM words + the untraced gp-0x6cf8 accessor (H-sentinel)
    if _k == "H-A":
        h -= 2.5                                   # fork SR fold load-bearing (1.155x over-turn if wrong); 69ca validity
    C3[_k] = h


def score(cid):
    r = TS[cid]
    b = {h: r[h] for h in HB}

    def t(x):                                      # tracking: 0 at <= 0.90, full at 0.95 (a must-have)
        return clip((x - 0.90) / 0.05)

    def dev(k):
        lo = min(r[f"trk_{k}"], r[f"trkq_{k}"])
        hi = max(r[f"trk_{k}"], r[f"trkq_{k}"])
        return lo if hi <= 1.05 else 2.1 - hi

    def hh(x):                                     # hold: 0 at <= 0.80, full at 0.90
        return clip((x - 0.80) / 0.10)
    a1 = 8 * t(dev("8-15")) + 8 * t(dev("15-22")) + 4 * t(dev(">22"))
    g1 = min(b["8-10"]["th20"], b["10-12.5"]["th20"], r["rhold_8-15"])
    g2 = min(b["12.5-15"]["th20"], r["rhold_8-15"])
    g3 = min(b["15-22"]["th20"], b[">22"]["th20"], r["rhold_15-22"], r["rhold_>22"])
    a2 = 4 * hh(g1) + 4 * hh(g2) + 6 * hh(g3)
    lm = max(max(b[h]["lurch_light"], b[h]["lurch_firm"]) for h in HB)
    a3 = 9 * clip((20.0 - lm) / 12.0)
    gmin = min(b[h]["g_s10_02"] for h in HB)
    dr = max(b[h]["eng_droop"] for h in HB)
    hd = max(b[h]["hard"] for h in HB)
    dj = sum(b[h]["dj10"] for h in HB)              # +-1 deg dwell-then-jump events >= 8 m/s (V282 not simulable)
    a4 = 1.0 * clip((gmin - 0.40) / 0.46) + 0.5 * clip((8.0 - dr) / 4.0) + 1.0 * clip((2.0 - hd) / 1.0) +         2.5 * clip((320.0 - dj) / 92.0)
    lo8 = max(r["<8"]["lurch_light"], r["<8"]["lurch_firm"])   # the declared low-speed frontier: release below 8 m/s
    a4 += 2.0 * clip((20.0 - lo8) / 10.0)
    m20, r5, r13, cls = FREQ[cid]
    b1 = B1[cls]
    b2 = 5 * clip((1.0 - m20) / 0.25) + 5 * clip((1.0 - abs(r5)) / 1.0) + \
        (5.0 if abs(r13) <= 0.47 else 5 * clip((0.95 - abs(r13)) / 0.48))
    c = C1[cid] + C2[cid] + C3[cid]
    nb = sum(1 for h in HB if b[h]["fails"])
    return dict(id=cid, A=a1 + a2 + a3 + a4, a1=a1, a2=a2, a3=a3, a4=a4, B=b1 + b2, b1=b1, b2=b2, C=c,
                total=a1 + a2 + a3 + a4 + b1 + b2 + c, bands_failed=nb, fails={h: b[h]["fails"] for h in HB},
                lurch=lm, lo8=lo8, dj=dj, gmin=gmin, droop=dr, hard=hd, trk=(dev("8-15"), dev("15-22"), dev(">22")),
                hold=(g1, g2, g3))


if __name__ == "__main__":
    rows = [score(k) for k in FREQ if k in TS]
    rows.sort(key=lambda d: -d["total"])
    out = []
    print = out.append  # noqa: A001  (collect the table, then write it and echo it)
    print("| rank | cand | total | A time (trk/hold/lurch/other) | B freq (G2/no-grind) | C | bands failed >=8 | "
          "trk 8-15/15-22/>22 (worst of clean, replay) | hold 8-12.5/12.5-15/15+ | lurch >=8 | lurch <8 | dj +-1 >=8 | gain +-1 0.2 Hz | droop | "
          "hard |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for i, d in enumerate(rows, 1):
        print(f"| {i} | {d['id']} | {d['total']:.1f} | {d['A']:.1f} ({d['a1']:.1f}/{d['a2']:.1f}/{d['a3']:.1f}/"
              f"{d['a4']:.1f}) | {d['B']:.1f} ({d['b1']:.0f}/{d['b2']:.1f}) | {d['C']:.1f} | {d['bands_failed']} | "
              + " / ".join(f"{x:.3f}" for x in d["trk"]) + " | " + " / ".join(f"{x:.3f}" for x in d["hold"])
              + f" | {d['lurch']:.1f} | {d['lo8']:.1f} | {d['dj']:.0f} | {d['gmin']:.2f} | {d['droop']:.1f} | {d['hard']:.2f} |")
    (HERE / "judge_score_out.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")
    txt = chr(10).join(out) + chr(10)
    (HERE / "judge_score_table.md").write_text(txt, encoding="utf-8")
    sys.stdout.write(txt)
