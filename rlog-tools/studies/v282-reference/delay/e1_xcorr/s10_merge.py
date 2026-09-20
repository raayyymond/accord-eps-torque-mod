"""Merge several s06 model-based runs over the SAME blocks into one plant grid (concatenate on the plant axis),
then print per-bin blind plant selection (each speed bin chooses its own plant) as a supplement to s09.
usage: python s10_merge.py <out_tag> <tag> [<tag> ...]"""
import sys
import numpy as np
import xc_lib as X
out, tags = sys.argv[1], sys.argv[2:]
Ms = [dict(np.load(X.HERE / "_cache" / f"mb_{t}.npz")) for t in tags]
for M in Ms[1:]:
    assert np.array_equal(M["tstart"], Ms[0]["tstart"]) and np.allclose(M["ny"], Ms[0]["ny"])
D = dict(Ms[0]); D["num"] = np.concatenate([M["num"] for M in Ms]); D["nx"] = np.concatenate([M["nx"] for M in Ms])
D["plants"] = np.concatenate([M["plants"] for M in Ms])
np.savez(X.HERE / "_cache" / f"mb_{out}.npz", **D)
import s09_mb_summary as S
sigs = list(D["sigs"]); dg = D["dgrid"]; P = D["plants"]
print(f"merged {len(P)} plants")
for bi, bn in list(enumerate(X.BIN_NAMES)) + [(None, "all")]:
    sel = np.ones(len(D["bin"]), bool) if bi is None else D["bin"] == bi
    rr = S.rho(D, sel, sigs.index("rate")); pb = int(np.argmax(rr.max(1)))
    line = f"  bin {bn:5s} own-best plant J{P[pb][0]:g} b{P[pb][1]:g} F{P[pb][2]:g} ks{P[pb][3]:g} rho_rate {rr[pb].max():.3f} :"
    for sig in sigs:
        d, r = S.dpeak(S.rho(D, sel, sigs.index(sig), pb), dg); line += f"  {sig} D {d:.1f} (rho {r:.3f})"
    # top-5 plants' D spread for rate
    top = np.argsort(-rr.max(1))[:5]
    line += "   top5 rate D: " + ",".join(f"{S.dpeak(rr[i], dg)[0]:.0f}" for i in top)
    print(line)
