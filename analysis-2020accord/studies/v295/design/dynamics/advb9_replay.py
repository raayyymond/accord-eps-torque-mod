"""ADV-bytes step 9: the design's r71b open-loop replay internals re-derived with plib.march (want=True):
max |r26|, fb-clamp binds, P-clamp binds, trim rms / p99 / max, int32 max |a*s| on the drive, and the longest dwell of
|trim| above 300 T (soft-EME residency proxy; the V294 adversary's 75 ms)."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
V295 = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(V295, "plant"), os.path.join(V295, "lib")):
    sys.path.insert(0, p)
import plib as P  # noqa: E402
import r71b_cache as RC  # noqa: E402
d = P.load(); c = RC.v294_cells(); sg = d["sg"]
eng1k = np.repeat(d["eng"].astype(bool), 10)[:len(d["T1k_null"])]
Tn = d["T1k_null"]
out = []
for a in (1011, 1017):
    T, R26, PP, SF, OL = P.march(d["sgn"], d["idx"], d["m"], c, x1k=d["x1k"], trim=True, fb_a=a, want=True)
    trim = sg * T - Tn
    tr = trim[eng1k]
    # longest run of |trim| > 300 (ms)
    hi = np.abs(trim) > 300
    dd = np.diff(np.r_[0, hi.astype(int), 0]); runs = np.flatnonzero(dd == -1) - np.flatnonzero(dd == 1)
    sabs = np.abs(SF.astype(float)) * a
    s = (f"a={a}: max|r26| {np.abs(R26).max()} (fb-clamp binds {int(np.sum(np.abs(R26) >= 1024))}) ; P-clamp binds "
         f"{int(np.sum(np.abs(PP) >= 15360))} ticks ; trim (engaged) rms {np.sqrt(np.mean(tr**2)):.1f} p99 {np.percentile(np.abs(tr),99):.0f} "
         f"max {np.abs(tr).max():.0f} T ; |trim|>300 T: {int(hi.sum())} ticks, longest {runs.max() if len(runs) else 0} ms ; "
         f"max|a*s| on the drive (frame starts) {sabs.max():.3e} margin {2**31/sabs.max():.1f} ; max|T| {np.abs(T).max():.0f}")
    print(s); out.append(s)
open(os.path.join(HERE, "advb9_replay_out.txt"), "w").write("\n".join(out) + "\n")
