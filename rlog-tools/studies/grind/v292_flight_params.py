# -*- coding: utf-8 -*-
"""V292 FLIGHT READ -- deliverable 4: the fork's params from initData, segment 0 of each of the three
V292 routes flown 2026-09-13, plus the device git commit.  Dumps EVERY key whose name matches the
lateral families (Accord*, Steer*, *Torque*, Force*, Lat*) so an ABSENT toggle is visible as absent
rather than silently read as its default.

ANALYSIS ONLY. Reads rlogs; writes only to _scratch.
Run: python rlog-tools/studies/grind/v292_flight_params.py
"""
import io
import json
import os
import re
import sys

import zstandard

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, os.path.join(KIT, "rlog-tools"))
from cereal import log as clog  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROUTES = [("r6d_v292", "75604b0a432fdc89_0000006d--5e7b4d2ceb"),
          ("r6e_v292", "75604b0a432fdc89_0000006e--64b4a5fef4"),
          ("r6f_v292", "75604b0a432fdc89_0000006f--d876c761bc"),
          ("r6c_V282ref", "75604b0a432fdc89_0000006c--2bc842dbac")]

# the brief's list, verbatim -- reported even when ABSENT
BRIEF = ["AccordRatePlantFF", "AccordFFRateGain", "AccordTorqueKi", "AccordVariableSteerRatio",
         "SteerRatio", "SteerLatAccel", "SteerFriction", "SteerKP", "AccordCurvatureLead",
         "AccordCurvatureLeadGain", "ForceAutoTune", "ForceTorqueController",
         "AccordEpsGainScale", "AccordEpsSpringScale", "AccordTurnFFTaper"]
PAT = re.compile(r"Accord|Steer|Torque|Force|LatAccel|Friction|Curvature|Tune|GitCommit|GitBranch|GitRemote|Version",
                 re.I)
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def read_params(prefix, seg=0):
    path = os.path.join(RLOGS, "%s--%d--rlog.zst" % (prefix, seg))
    with open(path, "rb") as fh:
        data = zstandard.ZstdDecompressor().stream_reader(fh).read()
    it = clog.Event.read_multiple_bytes(data)
    while True:
        try:
            evt = next(it)
        except StopIteration:
            return None
        except Exception:
            return None
        try:
            if evt.which() != "initData":
                continue
        except Exception:
            continue
        d = {}
        for e in evt.initData.params.entries:
            try:
                d[e.key] = bytes(e.value).decode("utf-8", "replace")
            except Exception:
                d[e.key] = repr(bytes(e.value)[:120])
        return d


def main():
    allp = {}
    for tag, prefix in ROUTES:
        pr("=" * 104)
        pr("%s   %s   segment 0 initData.params" % (tag, prefix))
        pr("=" * 104)
        d = read_params(prefix, 0)
        if d is None:
            pr("  *** no initData in segment 0 ***")
            continue
        allp[tag] = d
        pr("  %d params keys total" % len(d))
        pr("")
        pr("  --- THE BRIEF'S LIST (ABSENT = the key is not in the params store; openpilot then uses the code default) ---")
        for k in BRIEF:
            v = d.get(k)
            pr("    %-26s = %s" % (k, ("ABSENT" if v is None else repr(v)[:90])))
        pr("")
        pr("  --- every other matching key ---")
        for k in sorted(d):
            if k in BRIEF:
                continue
            if PAT.search(k) and k != "CarParams":
                pr("    %-26s = %s" % (k, repr(d[k])[:110]))
    with open(os.path.join(SCR, "v292_flight_params.json"), "w") as fh:
        json.dump(allp, fh, indent=1, default=str)
    io.open(os.path.join(SCR, "v292_flight_params.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("")
    pr("wrote %s" % os.path.join(SCR, "v292_flight_params.txt"))


if __name__ == "__main__":
    main()
