# -*- coding: utf-8 -*-
"""prom14_cmd.py -- the 1-4 Hz PROMINENCE in the COMMAND as well as the angle (the V276 signature needs both).

The scorer's section 7.5 (`v293_symptom_instruments.prominence_1_4`) computes the shoulder-fitted prominence on the
ANGLE only and carries the command as an amplitude.  This calls the SAME function, unchanged, twice per route on the
scorer's own grid (`v293_flight_read.sym_grid`) and mask (all lateral-engaged): once as written (angle) and once with
the command passed in the angle slot, so the command gets the identical estimator.  Nothing else is new.
Pre-registered (HOWTO 7.5): prominence < 3 dB in every band.  Subagent "bands", 2026-09-30.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, *[".."] * 5))
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "grind"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import v293_flight_read as FR          # noqa: E402
import v293_symptom_instruments as SI  # noqa: E402

TAGS = ["r71b_v294", "r70_v293", "r71_v293r2", "r72_v293r3", "r73_v293r3", "r75_v293r4", "r76_v293r5", "r6c", "r39", "r35"]
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def main():
    pr("1-4 Hz prominence, dB above the log-log shoulder fit (0.6-0.9 / 4-7 Hz), all lateral-engaged -- ANGLE | COMMAND")
    pr("  %-12s " % "route" + " ".join("%-22s" % b for b in SI.SBNAME))
    for t in TAGS:
        try:
            g = FR.sym_grid(t)
        except Exception as e:
            pr("  %-12s unavailable (%s)" % (t, str(e)[:60])); continue
        A = SI.prominence_1_4(g["ang"], g["cmd"], g["rate"], g["v"], g["eng"])
        C = SI.prominence_1_4(g["cmd"], g["cmd"], g["rate"], g["v"], g["eng"])
        cells = []
        for b in SI.SBNAME:
            a, c = A.get(b, {}), C.get(b, {})
            if a.get("prom") is None:
                cells.append("%-22s" % "-")
            else:
                cells.append("%-22s" % ("%+5.2f @%.2f | %+5.2f @%.2f" % (a["prom"], a["f_peak"], c["prom"], c["f_peak"])))
        pr("  %-12s " % t + " ".join(cells))
    open(os.path.join(HERE, "prom14_cmd_out.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
