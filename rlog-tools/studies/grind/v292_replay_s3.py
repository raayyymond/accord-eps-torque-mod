# -*- coding: utf-8 -*-
"""v292_replay_s3.py -- TASK 3 (the strong-turn 6-9 Hz check, in situ) and TASK 4 (r6c, the freshest
V282 route).  Agent `replay`, 2026-09-13.  ANALYSIS ONLY.

Run: python v292_replay_s3.py
"""
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import burst_echo_sizing as ES                     # noqa: E402
import creep20_loop_id as C20                      # noqa: E402
import design290b_candidates as D                  # noqa: E402
import v292_replay_lib as R                        # noqa: E402
import v292_replay_s2 as S                         # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FS = 100.0
OUT = S.OUT


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def main():
    fam, stable, sample = S.load_family()
    byid = {f["id"]: f for f in fam}
    named = [byid[i] for i in S.NAMED]
    spread = named + [f for f in stable[::12] if f["id"] not in S.NAMED]

    # ============================================================================== TASK 3
    pr("")
    pr("=" * 126)
    pr("TASK 3  THE STRONG-TURN CHECK -- the 7.3 Hz gate (B5) in situ, on real loaded high-angle episodes")
    pr("=" * 126)
    pr("B5's pre-registered limit is a 5-9 Hz sensitivity bump < 1.0 on the worst fit; the operator-facing")
    pr("version of it is the 6-9 Hz torque ripple on a loaded turn.  Limit here: x1.05.")
    pr("")
    pr("r35 is V281 rev 3.  Its LKAS rate-loop cells are BYTE-IDENTICAL to V282's -- fb 923/1560,")
    pr("lag 992/507, gain 5346, r24 arm 5244, Kp flat [248]x5 -- read from both images, so replaying its")
    pr("episodes through 'V282 electronics' is exact, not an approximation.  [EVIDENCE]")

    for tag, note in (("r35", "V281r3 -- the 'largely pronounced grinding incident' route"),
                      ("r39", "V282 -- loaded high-angle windows")):
        g = S.route(tag, (18.0, 22.0))
        wins = S.high_angle_windows(g, n=6)
        if not wins:
            pr("")
            pr("  %s: no loaded high-angle window survives the gate (engaged, idx >= 60, v < 6 m/s)" % tag)
            continue
        bp = C20.bandpass(g["bar"], 6.0, 9.0, FS)
        pr("")
        pr("  %s (%s): %d windows, idx/speed/6-9 Hz bar ripple at each" % (tag, note, len(wins)))
        for (a0, b0, p0) in wins:
            pr("      t %7.1f s   idx p50 %5.0f   v %4.1f m/s   bar 6-9 Hz rms %6.1f" %
               (g["t"][p0] - g["t"][0], np.median(g["idx_live"][a0:b0]), np.median(g["vego"][a0:b0]),
                np.sqrt(np.mean(bp[a0:b0] ** 2))))
        _, _, res, dt = S.run_route(tag, (18.0, 22.0), fits=spread, gload=g, wins=wins)
        S.table(res, spread, "  3.%s  %s -- V292/V282 on loaded high-angle episodes  (%.0f s)" %
                ("1" if tag == "r35" else "2", tag, dt),
                keys=("T_turn", "T_low", "T_ring", "T_shoulder", "auth_oob", "auth_lf", "auth_absmean", "W_ring"))

    # ============================================================================== TASK 4
    pr("")
    pr("=" * 126)
    pr("TASK 4  r6c -- the FRESHEST V282 route (3701 s, 62 segments, mostly motorway)")
    pr("=" * 126)
    for band, lab in (((18.0, 22.0), "the ring band"), ((12.0, 17.0), "the 12-17 Hz band")):
        g = S.route("r6c", band)
        wins = ES.loud_windows(g, n=5)
        pr("")
        pr("  r6c, %s: f0 %.3f Hz, %d loudest engaged 3 s windows" % (lab, g["f0"], len(wins)))
        for (a0, b0, p0) in wins:
            pr("      t %7.1f s   idx p50 %5.0f   v %4.1f m/s   env peak %6.1f" %
               (g["t"][p0] - g["t"][0], np.median(g["idx_live"][a0:b0]), np.median(g["vego"][a0:b0]),
                g["env"][p0]))
        if not wins:
            pr("      (none)")
            continue
        S.BANDS["sel"] = band
        _, _, res, dt = S.run_route("r6c", band, fits=spread, gload=g, wins=wins)
        S.table(res, spread, "  4.x  r6c / %s -- V292/V282  (%.0f s)" % (lab, dt),
                keys=("T_sel", "T_ring", "W_ring", "T_shoulder", "T_low", "auth_oob", "auth_lf", "auth_absmean"))
        rd, lin = S.ringdown(g, wins, g["cells"], named, nwin=5)
        pr("")
        pr("      matched free ring-down at these operating points:")
        for f in named:
            rr = rd[f["id"]]
            pr("        fit %-4s  V282 %6.0f ms -> V292 %6.0f ms   ratio %.3f   (r2 %.2f)" %
               (f["id"], np.median(rr[:, 0]), np.median(rr[:, 1]), np.median(rr[:, 2]), np.median(rr[:, 4])))

    with open(os.path.join(S.SCR, "v292_replay_s3.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/v292_replay_s3.txt")


if __name__ == "__main__":
    main()
