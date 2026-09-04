# -*- coding: utf-8 -*-
"""Build the v280-format route cache for r39 (V282) plus the 0x14A byte-4 probe cache and the
userBookmark timestamps, in ONE pass over the 16 rlog segments.

Outputs (analysis-2020accord/_scratch/cache/v280/):
  r39.npz     -- exactly the schema v280_map_profiles.read_route emits (t18,tq,rate,sca,t14,ang,t1ab,b0,b1,te4,cmd,req,tcs,vego)
  r39_b4.npz  -- t14b, b4  (V282 cave probe byte on 0x14A byte 4)
  r39_marks.json -- userBookmark logMonoTimes, segment first/last logMonoTime, and route-relative times

Subagent grind39, 2026-09-04.  Mirrors v280_map_profiles.read_route and extract_14a_b4_r36_r38.py exactly.
Run: python extract_r39_v280cache.py
"""
import glob
import json
import os
import sys

import numpy as np
import zstandard

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RLOGS = os.path.join(KIT, "analysis-2020accord", "rlogs")
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")
sys.path.insert(0, os.path.join(KIT, "rlog-tools"))
from cereal import log as clog  # noqa: E402

PREFIX = "75604b0a432fdc89_00000039--f56039af87"
TAG = "r39"


def i16be(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 65536 if v >= 32768 else v


def main():
    segs = sorted(glob.glob(os.path.join(RLOGS, "%s--*--rlog.zst" % PREFIX)),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    print(TAG, len(segs), "segments", flush=True)
    t18, tq, rate, sca, t14, ang, t1ab, b0, b1, te4, cmd, req, tcs, vego = ([] for _ in range(14))
    t14b, b4 = [], []
    marks, seg_span = [], {}
    for p in segs:
        sn = int(os.path.basename(p).split("--")[2])
        with open(p, "rb") as fh:
            data = zstandard.ZstdDecompressor().stream_reader(fh).read()
        it = clog.Event.read_multiple_bytes(data)
        lo, hi = None, None
        while True:
            try:
                evt = next(it)
            except StopIteration:
                break
            except Exception as e:
                print("  truncated: %s" % str(e)[:60]); break
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if lo is None:
                lo = tm
            hi = tm
            if w == "can":
                for m in evt.can:
                    d = bytes(m.dat)
                    if m.src == 1:
                        if m.address == 0x18F and len(d) >= 5:
                            t18.append(tm); tq.append(i16be(d, 0)); rate.append(i16be(d, 2)); sca.append((d[4] >> 3) & 1)
                        elif m.address == 0x14A and len(d) >= 4:
                            t14.append(tm); ang.append(i16be(d, 0) * -0.1)
                            if len(d) >= 5:
                                t14b.append(tm); b4.append(d[4])
                        elif m.address == 0x1AB and len(d) >= 2:
                            t1ab.append(tm); b0.append(d[0]); b1.append(d[1])
                    elif m.src == 129 and m.address == 0x0E4 and len(d) >= 3:
                        te4.append(tm); cmd.append(i16be(d, 0)); req.append((d[2] >> 7) & 1)
            elif w == "carState":
                tcs.append(tm); vego.append(evt.carState.vEgo)
            elif w == "userBookmark":
                marks.append(dict(seg=sn, mono=tm))
        seg_span[sn] = dict(lo=lo, hi=hi)
        print("  read %s" % os.path.basename(p), flush=True)

    A = lambda x, dt=float: np.asarray(x, dt)  # noqa: E731
    D = dict(t18=A(t18), tq=A(tq), rate=A(rate), sca=A(sca, int), t14=A(t14), ang=A(ang),
             t1ab=A(t1ab), b0=A(b0, int), b1=A(b1, int), te4=A(te4), cmd=A(cmd), req=A(req, int),
             tcs=A(tcs), vego=A(vego))
    os.makedirs(CACHE, exist_ok=True)
    np.savez(os.path.join(CACHE, TAG + ".npz"), **D)
    np.savez(os.path.join(CACHE, TAG + "_b4.npz"), t14b=A(t14b), b4=A(b4, int))

    t0 = D["t18"][0]                      # the route clock every study script uses
    for m in marks:
        m["t_route"] = m["mono"] - t0
        m["t_in_seg"] = m["mono"] - seg_span[m["seg"]]["lo"]
    out = dict(t0_mono=float(t0), marks=marks,
               segs={str(k): dict(lo_route=v["lo"] - t0, hi_route=v["hi"] - t0) for k, v in seg_span.items()})
    with open(os.path.join(CACHE, TAG + "_marks.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print("route length %.1f s; %d bookmarks" % (D["t18"][-1] - t0, len(marks)), flush=True)
    for m in marks:
        print("  bookmark seg %d  t_in_seg %.3f  t_route %.3f" % (m["seg"], m["t_in_seg"], m["t_route"]), flush=True)
    u, c = np.unique(A(b4, int), return_counts=True)
    print("b4 census", list(zip(u.tolist(), c.tolist())), flush=True)


if __name__ == "__main__":
    main()
