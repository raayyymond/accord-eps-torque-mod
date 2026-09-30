# -*- coding: utf-8 -*-
"""hardturn_events.py -- list every medium-speed hard turn on r71b_v294 so the orchestrator can ask the operator
about SPECIFIC moments ("jerky on hard turns at medium speed" is his phrase; this does not score it).

Event = a contiguous engaged run with v in [8, 22) m/s and |planner D| >= 1.0 m/s^2 lasting >= 1.0 s (the
v293r3_read S4 / N2 hard-turn definition family), padded 1 s either side for the statistics.  Per event:
  wall clock (PDT, from the extract agent's GPS anchor: route t0 = 2026-09-30 03:10:06 UTC; UTC-7 is BELIEF),
  route time, v, peak |D|, peak |angle|, hold ratio (median act/des over the |D|>=1.0 core), lag des->act (ncc),
  1.6-3 Hz rate rms, |d rate/dt| p95, command step p99, pressed share, integrator share at the core, and the
  tap residual rms (T - the V293 surface from the scorer's own identity predictor) in 1.6-3 Hz -- i.e. the trim's
  delivered 2 Hz torque.  EVIDENCE for every number; the link to what he felt is BELIEF.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, *[".."] * 5))
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "grind"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import v293_ident_lib as L   # noqa: E402
import v293r3_read as R3     # noqa: E402

FS = 100.0
T0_UTC_S = 3 * 3600 + 10 * 60 + 6          # 03:10:06 UTC, the extract agent's GPS anchor for the first CAN frame


def main(tag="r71b_v294"):
    g = R3.load_plus(tag)
    v = g["v"]; ang = g["ang"]; rate = np.nan_to_num(g["rate_dps"])
    D = np.nan_to_num(g["des_curv"] * v ** 2)
    eng = g["eng"] & (g["cs_active"] > 0.5)
    core = eng & (v >= 8) & (v < 22) & (np.abs(D) >= 1.0)
    ev = L.stretches(core, int(1.0 * FS))
    t18_0 = g["raw"]["t18"][0]; tg0 = min(g["raw"]["t18"][0], g["raw"]["t_cc"][0])
    off = t18_0 - tg0                   # grid time of the first 0x18F frame
    rows = []
    for a, b in ev:
        a0, b0 = max(0, a - 100), min(g["n"], b + 100)
        tr = g["t"][a] - off
        hh = int((T0_UTC_S + tr) // 3600) - 7; mm = int(((T0_UTC_S + tr) % 3600) // 60); ss = (T0_UTC_S + tr) % 60
        la = g["la_act"][a:b]; ld = D[a:b]
        hold = float(np.median(np.abs(la) / np.maximum(np.abs(ld), 1e-3)))
        lag, _ = L.ncc_lag(D[a0:b0] - D[a0:b0].mean(), g["la_act"][a0:b0] - g["la_act"][a0:b0].mean(), lo=-0.2, hi=1.0)
        r16 = float(np.sqrt(np.mean(L.bandpass(rate[a0:b0], 1.6, 3.0) ** 2))) if b0 - a0 > 60 else np.nan
        acc = np.abs(np.gradient(rate[a0:b0], 1 / FS))
        dc = np.abs(np.diff(g["cmd"][a0:b0]))
        tot = np.abs(g["p"][a:b]) + np.abs(g["i"][a:b]) + np.abs(g["f"][a:b])
        ish = float(np.mean(np.abs(g["i"][a:b]) / np.maximum(tot, 1e-6)))
        T16 = float(np.sqrt(np.mean(L.bandpass(np.nan_to_num(g["T"][a0:b0]), 1.6, 3.0) ** 2))) if b0 - a0 > 60 else np.nan
        pdt = ("%02d:%02d:%04.1f" % (hh % 24, mm, ss)) if tag == "r71b_v294" else "   (n/a)  "   # the anchor is r71b's only
        rows.append(dict(t_route=round(float(tr), 1), pdt=pdt, dur=(b - a) / FS,
                         v=float(np.median(v[a:b])), Dpk=float(np.max(np.abs(ld))), angpk=float(np.max(np.abs(ang[a:b]))),
                         hold=hold, lag=float(lag), r16=r16, acc95=float(np.percentile(acc, 95)),
                         dcmd99=float(np.percentile(dc, 99)), pressed=float(np.mean(g["press"][a0:b0] > 0.5)), ishare=ish,
                         tap16=T16))
    print("MEDIUM-SPEED HARD TURNS on %s: v 8-22 m/s, |D| >= 1.0 for >= 1 s, engaged -- %d events" % (tag, len(rows)))
    print("  PDT(BELIEF)  t_route  dur   v    |D|pk |ang|pk hold  lag   r16dps |dr/dt|p95 dcmd99 pressed i-share tap16")
    for r in rows:
        print("  %s %7.1f %4.1f %5.1f %5.2f %6.1f  %4.2f %5.2f %6.2f %8.0f %6.0f %6.2f %6.2f %6.1f"
              % (r["pdt"], r["t_route"], r["dur"], r["v"], r["Dpk"], r["angpk"], r["hold"], r["lag"], r["r16"], r["acc95"],
                 r["dcmd99"], r["pressed"], r["ishare"], r["tap16"]))
    json.dump(rows, open(os.path.join(HERE, "hardturn_events_out.json"), "w"), indent=1)
    return rows


if __name__ == "__main__":
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
        for ref in ("r75_v293r4", "r76_v293r5"):
            print()
            main(ref)
    sys.stdout.write(buf.getvalue())
    open(os.path.join(HERE, "hardturn_events_out.txt"), "w", encoding="utf-8").write(buf.getvalue())
