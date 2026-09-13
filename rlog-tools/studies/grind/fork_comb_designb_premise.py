# -*- coding: utf-8 -*-
"""studies/grind/fork_comb_designb_premise.py -- IS DESIGN (B) A RECONSTRUCTION OF THE PUBLISHED
COMMAND, OR OF A DIFFERENT SIGNAL?   Subagent `combfix`, 2026-09-13.  ANALYSIS ONLY.

Design (B), which the record calls "lag-NEGATIVE up to 50 ms", advances the command between model
frames along the model's OWN published future -- `modelV2.orientationRate.z / velocity.x` on
ModelConstants.T_IDXS -- anchored on the published action so the frame-instant value is untouched:

    kappa_plan(tau) = orientationRate.z(tau) / max(velocity.x(tau), 1)      on T_IDXS
    out(t_k + tau)  = v[k] + (kappa_plan(tau) - kappa_plan(0))

THE PREMISE IT RESTS ON, and it is not obviously true: that the plan trajectory's SHAPE over the
next 50 ms is the shape of the action head's own future.  On this fork they are DIFFERENT OUTPUT
HEADS.  `modelV2.action.desiredCurvature` comes from the model's action head, divided by
max(1, v_ego)**2 (modeld.py:406-408), and then LOW-PASS FILTERED at the model rate by
`smooth_value(..., LAT_SMOOTH_SECONDS = 0.1 s)` (modeld.py:415, :84) -- a one-pole at 1.59 Hz.
`orientationRate` is the plan head, published raw (fill_model_msg.fill_xyzt).  If the two heads do
not agree about what happens in the next 50 ms, (B) does not reconstruct the published command; it
splices a different signal into it.

THE TEST.  For every model frame k, compare
    (i)  what the plan SAYS will happen over the next 50 ms:  d_plan[k] = kappa_plan(0.05) - kappa_plan(0)
    (ii) what the action head ACTUALLY DOES next:             s_next[k] = v[k+1] - v[k]
Correlation, regression slope, and the sign-agreement rate.  A reconstruction is only useful if
d_plan predicts s_next; if it does not, (B) advances the command in a direction the model's own next
frame will contradict, which is worse than holding.

POSITIVE CONTROL: the same statistics for design (A)'s predictor, d_A[k] = v[k] - v[k-1].  (A) uses
the action head's own past, so it is the honest baseline for "how predictable is the next step at all".

Run: python rlog-tools/studies/grind/fork_comb_designb_premise.py [n_segments]
Writes _scratch/fork_comb_designb_premise.txt beside it.
"""
import glob
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
sys.path.insert(0, os.path.join(KIT, "rlog-tools"))
OUTF = os.path.join(HERE, "_scratch", "fork_comb_designb_premise.txt")
OUT = []

ROUTE = "75604b0a432fdc89_00000039--f56039af87"      # r39, V282 -- the one clean mirror route
T_IDXS = [(idx / 32.0) ** 2 * 10.0 for idx in range(33)]   # ModelConstants.T_IDXS, verbatim
DT_MDL = 0.05


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def read_segment(path):
    import zstandard
    from cereal import log as clog
    with open(path, "rb") as fh:
        data = zstandard.ZstdDecompressor().stream_reader(fh).read()
    it = clog.Event.read_multiple_bytes(data)
    o = {k: [] for k in ("t", "fid", "curv", "orz", "vx", "vego")}
    vego = 0.0
    while True:
        try:
            evt = next(it)
        except StopIteration:
            break
        except Exception:
            break
        try:
            w = evt.which()
        except Exception:
            continue
        if w == "carState":
            vego = float(evt.carState.vEgo)
        elif w == "modelV2":
            m = evt.modelV2
            try:
                orz = np.array(m.orientationRate.z, dtype=float)
                vx = np.array(m.velocity.x, dtype=float)
            except Exception:
                continue
            if len(orz) < 33 or len(vx) < 33:
                continue
            o["t"].append(evt.logMonoTime * 1e-9)
            o["fid"].append(float(m.frameId))
            o["curv"].append(float(m.action.desiredCurvature))
            o["orz"].append(orz[:33])
            o["vx"].append(vx[:33])
            o["vego"].append(vego)
    return o


def main():
    nseg = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    paths = sorted(glob.glob(os.path.join(RLOGS, ROUTE + "--*--rlog.zst")))[:nseg]
    pr("=" * 112)
    pr("DESIGN (B) PREMISE TEST -- does the model's published FUTURE predict its own NEXT ACTION STEP?")
    pr("=" * 112)
    pr("route r39 (V282), %d segments" % len(paths))
    acc = {k: [] for k in ("t", "fid", "curv", "orz", "vx", "vego")}
    for p in paths:
        o = read_segment(p)
        for k in acc:
            acc[k].extend(o[k])
        pr("  %s : %d modelV2 frames" % (os.path.basename(p), len(o["t"])))
    t = np.array(acc["t"]); fid = np.array(acc["fid"]); curv = np.array(acc["curv"])
    orz = np.array(acc["orz"]); vx = np.array(acc["vx"]); vego = np.array(acc["vego"])
    pr()
    pr("total %d frames, %.1f s" % (len(t), t[-1] - t[0]))

    # the plan's own curvature trajectory, and its advance over the next 50 ms
    kap = orz / np.maximum(vx, 1.0)
    k0 = np.array([np.interp(0.0, T_IDXS, row) for row in kap])
    k50 = np.array([np.interp(DT_MDL, T_IDXS, row) for row in kap])
    d_plan = k50 - k0

    ok = np.r_[np.diff(fid) > 0, False] & np.isfinite(curv) & np.isfinite(d_plan)
    ok &= np.r_[True, np.diff(t) < 0.12]
    ok[-1] = False
    s_next = np.r_[np.diff(curv), 0.0]
    s_prev = np.r_[0.0, np.diff(curv)]
    m = ok & (vego > 1.0)
    pr("usable frames (consecutive, v_ego > 1 m/s): %d" % m.sum())
    pr()

    pr("PLAN-vs-ACTION SCALE.  The plan head's own curvature at tau=0 against the published action:")
    r = np.corrcoef(k0[m], curv[m])[0, 1]
    sl = np.polyfit(curv[m], k0[m], 1)[0]
    pr("    corr(kappa_plan(0), action.desiredCurvature) = %+0.4f   slope %+0.4f" % (r, sl))
    pr("    rms kappa_plan(0) %.5e   rms action %.5e" % (np.std(k0[m]), np.std(curv[m])))
    pr()

    pr("THE TEST.  Predictors of the NEXT action step  s_next[k] = v[k+1] - v[k]:")
    pr("  %-44s %10s %10s %12s %12s" % ("predictor", "corr", "slope", "sign agree", "rms ratio"))
    pr("  " + "-" * 94)
    for nm, d in (("(B)  plan advance over 50 ms  kap(0.05)-kap(0)", d_plan),
                  ("(A)  the action head's own last step v[k]-v[k-1]", s_prev),
                  ("(B') plan advance, rescaled by the fitted slope", d_plan * np.polyfit(d_plan[m], s_next[m], 1)[0])):
            x, y = d[m], s_next[m]
            c = float(np.corrcoef(x, y)[0, 1])
            sl = float(np.polyfit(x, y, 1)[0])
            sg = float(np.mean(np.sign(x) == np.sign(y)))
            pr("  %-44s %10.4f %10.4f %12.3f %12.4f"
               % (nm, c, sl, sg, float(np.std(x) / max(np.std(y), 1e-30))))
    pr()
    pr("READING.  A predictor is useful for a lag-negative reconstruction only if corr is clearly")
    pr("positive AND the sign agreement is well above 0.5.  A corr near zero means the reconstruction")
    pr("would advance the command in a direction the model's own next frame contradicts half the time,")
    pr("which is WORSE than holding -- it adds in-band energy without removing the knot.")
    with open(OUTF, "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    pr()
    pr("wrote %s" % OUTF)


if __name__ == "__main__":
    main()
