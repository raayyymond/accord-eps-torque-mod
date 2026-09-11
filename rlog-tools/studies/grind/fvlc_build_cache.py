# -*- coding: utf-8 -*-
"""Build the fvlc per-route caches (analysis only)."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fvlc_lib as F

tags = sys.argv[1:] or list(F.ROUTES)
for t in tags:
    t0 = time.time()
    try:
        g = F.load(t)
        print("%-10s build=%-7s n=%7d eng=%.3f eps=%3d hot=%.4f  (%.0f s)"
              % (t, F.BUILD[t], len(g["t"]), g["eng"].mean(), len(g["eps"]), g["hot"].mean(), time.time() - t0), flush=True)
    except Exception as e:
        print("%-10s FAILED %s" % (t, repr(e)[:200]), flush=True)
