# -*- coding: utf-8 -*-
"""flight_read_crosstab.py -- tabulate the v293_flight_read scorecards of r71b_v294 against EVERY V293 flight on disk
(r70 rev1, r71-old rev2, r72/r73 rev3, r75 rev4, r76 rev5) and the V282 references (r6c/r39/r35 via the scorer's own
symptom-ref and flight-ref tables).  Reads the scorer's JSON outputs only; computes nothing new except ratios.
Subagent "bands", 2026-09-30.  EVIDENCE: every number is the scorer's.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, *[".."] * 5))
SCR = os.path.join(KIT, "rlog-tools", "studies", "grind", "_scratch")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROUTES = [("r71b_v294", os.path.join(HERE, "v293_flight_read_r71b_v294.json")),
          ("r70_v293", os.path.join(SCR, "v293_flight_read_r70_v293.json")),
          ("r71_v293r2", os.path.join(SCR, "v293_flight_read_r71_v293r2.json")),
          ("r72_v293r3", os.path.join(SCR, "v293_flight_read_r72_v293r3.json")),
          ("r73_v293r3", os.path.join(SCR, "v293_flight_read_r73_v293r3.json")),
          ("r75_v293r4", os.path.join(SCR, "v293_flight_read_r75_v293r4.json")),
          ("r76_v293r5", os.path.join(HERE, "v293_flight_read_r76_v293r5.json"))]
OUT = []


def pr(s=""):
    print(s); OUT.append(s)


def g(d, *p):
    for k in p:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def f(x, fmt="%.3f"):
    try:
        return fmt % x
    except TypeError:
        return "-"


def main():
    D = {t: json.load(open(p)) for t, p in ROUTES if os.path.exists(p)}
    tags = list(D)
    refs = json.load(open(os.path.join(SCR, "v293_symptom_refs.json")))
    RR = refs.get("routes", refs)
    pr("routes: " + " ".join(tags))
    rows = [
        ("identity R2 V293/bar", lambda d: g(d, "identity", "V293/bar/lag0", "r2")),
        ("identity resid", lambda d: g(d, "identity", "V293/bar/lag0", "resid")),
        ("engaged s", lambda d: g(d, "symptom", "eng_s")),
        ("18-22 eng/dis", lambda d: g(d, "engdis", "18-22")),
        ("13-17 eng/dis", lambda d: g(d, "engdis", "13-17")),
        ("5-9 eng/dis", lambda d: g(d, "engdis", "5-9")),
        ("ring presence %", lambda d: g(d, "presence", "all_engaged", "pres_pct")),
        ("ring n_pres", lambda d: g(d, "presence", "all_engaged", "n_pres")),
        ("ring amp p50 dps", lambda d: g(d, "presence", "all_engaged", "amp_p50")),
        ("ring f0 p50 Hz", lambda d: g(d, "presence", "all_engaged", "f0_p50")),
        ("F7 /100 s", lambda d: g(d, "strongturn", "f7_per100")),
        ("rip/L p50", lambda d: g(d, "strongturn", "ripL_p50_all")),
        ("rip ABS p50 cnt", lambda d: g(d, "strongturn", "rip_abs_p50_all")),
        ("|T| p50 loaded", lambda d: g(d, "strongturn", "lvl_p50_all")),
        ("13-17 hands-off 8-15 dps", lambda d: g(d, "spectra", "hands-off 8-15 m/s", "amps", "13-17")),
        ("5-9 hands-off 8-15 dps", lambda d: g(d, "spectra", "hands-off 8-15 m/s", "amps", "5-9")),
        ("outer ang14 0-5 deg", lambda d: g(d, "outer", "0-5 m/s", "ang14_deg")),
        ("outer ang14 5-10 deg", lambda d: g(d, "outer", "5-10 m/s", "ang14_deg")),
        ("outer ang14 10-20 deg", lambda d: g(d, "outer", "10-20 m/s", "ang14_deg")),
        ("outer ang14 >=20 deg", lambda d: g(d, "outer", ">=20 m/s", "ang14_deg")),
        ("outer cmd14 5-10 cnt", lambda d: g(d, "outer", "5-10 m/s", "cmd14")),
        ("cave b7 engaged", lambda d: g(d, "cave", "engaged", "b7")),
        ("cave b6 engaged", lambda d: g(d, "cave", "engaged", "b6")),
        ("cave b5 engaged", lambda d: g(d, "cave", "engaged", "b5")),
        ("cave b4 engaged (neg ctl)", lambda d: g(d, "cave", "engaged", "b4")),
        ("cave b3 engaged", lambda d: g(d, "cave", "engaged", "b3")),
        ("cave b4 SCA=0", lambda d: g(d, "cave", "SCA=0", "b4")),
    ]
    for bn in ("0-5", "5-10", "10-20", ">20"):
        rows.append(("dwells/min th.25 %s" % bn, lambda d, bn=bn: g(d, "symptom", "dwell_eng", bn, "per_min_025")))
    for bn in ("0-5", "5-10", "10-20", ">20"):
        rows.append(("dwell p90 s %s" % bn, lambda d, bn=bn: g(d, "symptom", "dwell_eng", bn, "dwell_p90")))
    for bn in ("0-5", "5-10", "10-20", ">20"):
        rows.append(("snap p90 deg %s" % bn, lambda d, bn=bn: g(d, "symptom", "dwell_eng", bn, "snap_p90")))
    rows.append(("concentration q75-90", lambda d: g(d, "symptom", "conc", "rate", "q75-90")))
    for bn in ("0-5", "5-10", "10-20", ">20"):
        rows.append(("1-4 Hz prominence dB %s" % bn, lambda d, bn=bn: g(d, "symptom", "prom", bn, "prom")))
    for bn in ("0-5", "5-10", "10-20", ">20"):
        rows.append(("1-4 Hz rate content dps %s" % bn, lambda d, bn=bn: g(d, "symptom", "prom", bn, "rate")))
    for bn in ("<8", "8-15", "15-22", ">22"):
        rows.append(("tracking gain %s" % bn, lambda d, bn=bn: g(d, "symptom", "track", bn, "slope")))
    for bn in ("<8", "8-15", "15-22", ">22"):
        rows.append(("integrator share %s" % bn, lambda d, bn=bn: g(d, "symptom", "shares", bn, "i")))
    for bn in ("0-5", "5-10", "10-20", ">20"):
        rows.append(("turn-hold ratio %s" % bn, lambda d, bn=bn: g(d, "symptom", "hold", "bands", bn)))
    for bn in ("0-5", "5-10", "10-20", ">20"):
        rows.append(("rel overshoot %s" % bn, lambda d, bn=bn: g(d, "symptom", "step", "bands", bn)))
    for rg in ("straight", "turn entry", "turn hold", "turn exit", "low-speed manoeuvre"):
        rows.append(("delivery %s" % rg, lambda d, rg=rg: g(d, "symptom", "regime", rg, "deliver")))
    for bn in ("0-5", "5-10", "10-20", ">20"):
        rows.append(("loop stiffness t/deg %s" % bn, lambda d, bn=bn: g(d, "symptom", "stiff", bn, "tq_per_deg")))
    pr("%-30s " % "metric" + " ".join("%11s" % t[:11] for t in tags))
    table = {}
    for name, fn in rows:
        vals = []
        for t in tags:
            try:
                v = fn(D[t])
            except Exception:
                v = None
            if isinstance(v, dict):
                v = v.get("ratio", v.get("rel", v.get("med", v.get("ov", v.get("value", None)))))
            vals.append(v)
        table[name] = dict(zip(tags, vals))
        pr("%-30s " % name + " ".join("%11s" % (f(v) if isinstance(v, (int, float)) and v is not None else "-") for v in vals))
    json.dump(table, open(os.path.join(HERE, "flight_read_crosstab_out.json"), "w"), indent=1, default=str)
    open(os.path.join(HERE, "flight_read_crosstab_out.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
