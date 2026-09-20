# -*- coding: utf-8 -*-
"""c1b: decode the PERSISTED `LiveDelay` param each route booted with, plus the in-route trace of
liveDelay.lateralDelay from the cache.  Tells whether D was a pinned toggle, a seed, or a measurement.

usage: python c1b_livedelay.py
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(KIT, "rlog-tools"))
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "v282-reference"))
from cereal import log as clog  # noqa: E402
import v282cmp as V  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = json.load(open(os.path.join(HERE, "c1_delayparams.json")))
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v282ref")

print("=" * 132)
print("PERSISTED `LiveDelay` param at boot (what the learner had banked) + the in-route liveDelay trace.")
print("D_used is what latcontrol_torque actually received: SteerDelay if UseAutoSteerDelay==0, else liveDelay.lateralDelay")
print("=" * 132)
hdr = ("%-22s %-7s %-6s %-9s | persisted: delay  est     estStd  blocks status   | in-route: med    p5     p95    n_chg" %
       ("route", "group", "UseAu", "SteerDelay"))
print(hdr)
for r in sorted(P):
    d = P[r]
    raw = d.get("_LiveDelay_raw")
    pd = "-"
    if raw:
        try:
            with clog.Event.from_bytes(bytes.fromhex(raw)) as m:
                ld = m.liveDelay
                pd = "%.4f  %.4f  %.4f  %2d     %-8s" % (ld.lateralDelay, ld.lateralDelayEstimate,
                                                         ld.lateralDelayEstimateStd, ld.validBlocks, str(ld.status))
        except Exception as e:
            pd = "decode fail %s" % e
    tr = "-"
    f = os.path.join(CACHE, r + ".npz")
    if os.path.exists(f):
        D = np.load(f, allow_pickle=True)
        if "ld_delay" in D.files and len(D["ld_delay"]):
            x = D["ld_delay"]
            nchg = int(np.count_nonzero(np.abs(np.diff(x)) > 1e-9))
            tr = "%.4f %.4f %.4f %5d" % (np.median(x), np.percentile(x, 5), np.percentile(x, 95), nchg)
    grp = V.ROUTES.get(r, {}).get("group", "?")
    print("%-22s %-7s %-6s %-9s | %s | %s" % (r, grp, d.get("UseAutoSteerDelay", "?"), d.get("SteerDelay", "?"), pd, tr))
