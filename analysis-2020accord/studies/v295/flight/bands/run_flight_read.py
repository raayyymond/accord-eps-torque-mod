# -*- coding: utf-8 -*-
"""run_flight_read.py -- run rlog-tools/studies/grind/v293_flight_read.py UNCHANGED, working around one defect.

DEFECT (found 2026-09-30 by subagent "bands"; reported, NOT fixed in the kit file): the rev-5 edit of 2026-09-15
(commit 2ef033a) added an observer block to `print_scorecard` that reads a name `g` which is never defined in that
function (lines ~1876-1884: `dob = g.get("sp_dob") ...`).  Python resolves it as a module GLOBAL, so every run since
that commit dies with NameError after all the scoring is done and before anything is printed or saved.
The r75_v293r4 json on disk predates the edit.

WORKAROUND: define the module global `g = {}` before calling main().  Then `dob is None`, the observer print is skipped
(both branches of that `if` are print-only; no verdict depends on them), and every other line of the scorer runs
exactly as written.  The observer is read separately (v293r5_observer_read O1; on r71b accordObserverTorque is
identically 0 -- EVIDENCE, the extract agent's census).

usage: python run_flight_read.py <route or tag> [v293_flight_read args...]
"""
import os
import sys

KIT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *[".."] * 5))
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "grind"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import v293_flight_read as FR  # noqa: E402

FR.g = {}
sys.argv = ["v293_flight_read.py"] + sys.argv[1:]
FR.main()
