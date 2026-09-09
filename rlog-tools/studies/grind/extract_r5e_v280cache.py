# -*- coding: utf-8 -*-
"""Build the v280-format route cache for the FIRST V288 rev 2 route -- 75604b0a432fdc89_0000005e--03a9714d78
(2026-09-08, 15 segments) -- plus the 0x14A byte-4 probe cache and the userBookmark timestamps, in ONE
pass.  Copied VERBATIM from extract_r3c_v280cache.py (itself verbatim from extract_r39_v280cache.py) --
SAME field names, SAME grid, SAME decode; only PREFIX, TAG and NSEG_NOMINAL differ, so the V282 grind
census reads this route with the same yardstick.

*** ROUTE-NUMBER COLLISION: the counter reset; `_scratch/cache/r5e/` and any `r5e.npz` are the 2026-08-06
V65-era route.  This route is TAG r5e_v288 everywhere.  Match on the full id, never the counter. ***

*** V288 DECODER NOTE: 0x14A byte 4 bit 5 = sign(filtered setpoint y) (1 when y < 0); it was V282's
|r24| >= |aggregator| comparator.  Bit 6 = |r24| >= |T|, bits 3/4/7 = the three-sign rung, bits 0-2 stock. ***

Outputs (analysis-2020accord/_scratch/cache/v280/): r5e_v288.npz, r5e_v288_b4.npz, r5e_v288_marks.json.
Run: python rlog-tools/studies/grind/extract_r5e_v280cache.py
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

PREFIX = "75604b0a432fdc89_0000005e--03a9714d78"
TAG = "r5e_v288"
NSEG_NOMINAL = 15          # 0..14, all present on disk (2026-09-08)


def i16be(d, i):
    v = (d[i] << 8) | d[i + 1]
    return v - 65536 if v >= 32768 else v


def main():
    segs = sorted(glob.glob(os.path.join(RLOGS, "%s--*--rlog.zst" % PREFIX)),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    have = [int(os.path.basename(p).split("--")[2]) for p in segs]
    missing = [i for i in range(NSEG_NOMINAL) if i not in have]
    print(TAG, len(segs), "segments on disk:", have, flush=True)
    if missing:
        print("  *** MISSING from disk: %s -- concatenated time axis WILL carry a hole ***"
              % missing, flush=True)
    t18, tq, rate, sca, t14, ang, t1ab, b0, b1, te4, cmd, req, tcs, vego = ([] for _ in range(14))
    t14b, b4 = [], []
    marks, seg_span = [], {}
    failed = []
    for p in segs:
        sn = int(os.path.basename(p).split("--")[2])
        with open(p, "rb") as fh:
            data = zstandard.ZstdDecompressor().stream_reader(fh).read()
        it = clog.Event.read_multiple_bytes(data)
        lo, hi = None, None
        n18_at_seg_start = len(t18)     # -> lo_can, the first REAL CAN arrival
        while True:
            try:
                evt = next(it)
            except StopIteration:
                break
            except Exception as e:
                print("  truncated: %s" % str(e)[:60]); failed.append(dict(seg=sn, err=str(e)[:120])); break
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
        seg_span[sn] = dict(lo=lo, hi=hi,
                            lo_can=(t18[n18_at_seg_start]
                                    if len(t18) > n18_at_seg_start else lo))
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
        m["t_in_seg"] = m["mono"] - seg_span[m["seg"]]["lo_can"]
    order = sorted(seg_span)
    gaps = [dict(after_seg=a_, before_seg=b_,
                 gap_s=round(seg_span[b_]["lo_can"] - seg_span[a_]["hi"], 3),
                 contiguous_index=(b_ == a_ + 1))
            for a_, b_ in zip(order, order[1:])]
    out = dict(t0_mono=float(t0), marks=marks,
               present_segments=order, missing_segments=missing, failed_segments=failed,
               gaps=gaps,
               gap_warning=("A missing segment leaves a REAL hole in the concatenated t18/t14/te4/"
                            "tcs axes. Time-indexed code is unaffected; any fixed-rate resample, "
                            "FFT or np.diff-based rate estimate will silently bridge it."),
               segs={str(k): dict(lo_route=v["lo"] - t0, hi_route=v["hi"] - t0,
                                  lo_can_route=v["lo_can"] - t0)
                     for k, v in seg_span.items()},
               lo_route_note=("`lo_route` is the r39 field, kept byte-compatible: it is the "
                              "logMonoTime of the segment's first EVENT, which is initData's "
                              "process-start stamp, NOT the segment start. Use `lo_can_route`."))
    with open(os.path.join(CACHE, TAG + "_marks.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print("route length %.1f s; %d bookmarks" % (D["t18"][-1] - t0, len(marks)), flush=True)
    for m in marks:
        print("  bookmark seg %d  t_in_seg %.3f  t_route %.3f" % (m["seg"], m["t_in_seg"], m["t_route"]), flush=True)
    for g in gaps:
        if not g["contiguous_index"] or g["gap_s"] > 5.0:
            print("  GAP seg %d -> %d : %.3f s  (contiguous_index=%s)"
                  % (g["after_seg"], g["before_seg"], g["gap_s"], g["contiguous_index"]), flush=True)
    u, c = np.unique(A(b4, int), return_counts=True)
    print("b4 census", list(zip(u.tolist(), c.tolist())), flush=True)


if __name__ == "__main__":
    main()
