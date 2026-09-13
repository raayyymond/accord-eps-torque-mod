# -*- coding: utf-8 -*-
"""Build the v280-format route cache for the THREE V292 flight routes flown 2026-09-13:

    75604b0a432fdc89_0000006d--5e7b4d2ceb   (18 segments, 0..17)   TAG r6d_v292
    75604b0a432fdc89_0000006e--64b4a5fef4   (23 segments, 0..22)   TAG r6e_v292
    75604b0a432fdc89_0000006f--d876c761bc   (13 segments, 0..12)   TAG r6f_v292

Copied VERBATIM in decode and field names from extract_r62_r63_v280cache.py (<- extract_r5e_v280cache.py
<- extract_r3c_v280cache.py <- extract_r39_v280cache.py) so every census tool reads these routes with the
same yardstick.  Only PREFIX / TAG / NSEG_NOMINAL differ.

*** ROUTE-NUMBER COLLISION -- READ THIS.  The dongle's route counter was RESET earlier this year.  The
AUGUST routes r6d / r6e / r6f (V84/V85 era, extract_r6d_r68.py etc.) are DIFFERENT ROUTES with the same
counter.  That is why these TAGs carry the `_v292` suffix, exactly as r5e_v288 / r62_v289 did.  Never key
a cache on the bare counter. ***

Adds, beyond the r62/r63 extractor:
  - initData.params  -> <TAG>_params.json   (the fork's Accord lateral toggles + the device git commit),
    read from the FIRST segment only (params are stamped once per process start).
  - carState.steeringAngleDeg / steeringTorque / steeringPressed -> extra arrays, for the high-angle read.
    (0x14A byte 0-1 `ang` is kept too, identical to the record's field, so nothing downstream changes.)

Outputs (analysis-2020accord/_scratch/cache/v280/): <TAG>.npz, <TAG>_b4.npz, <TAG>_marks.json,
<TAG>_params.json  -- plus a pointer copy under rlog-tools/_scratch/cache/<full route id>/.
Run: python rlog-tools/studies/grind/extract_v292_routes.py r6d        (or r6e / r6f / all)
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
PTRCACHE = os.path.join(KIT, "rlog-tools", "_scratch", "cache")
sys.path.insert(0, os.path.join(KIT, "rlog-tools"))
from cereal import log as clog  # noqa: E402

ROUTES = {"r6d": ("75604b0a432fdc89_0000006d--5e7b4d2ceb", "r6d_v292", 18),
          "r6e": ("75604b0a432fdc89_0000006e--64b4a5fef4", "r6e_v292", 23),
          "r6f": ("75604b0a432fdc89_0000006f--d876c761bc", "r6f_v292", 13)}
PREFIX = TAG = NSEG_NOMINAL = None

# the fork toggles the brief names, plus everything that looks Accord-lateral, plus the commit
WANT_PARAMS = ["AccordRatePlantFF", "AccordFFRateGain", "AccordTorqueKi", "AccordVariableSteerRatio",
               "SteerRatio", "SteerLatAccel", "SteerFriction", "SteerKP", "AccordCurvatureLead",
               "AccordCurvatureLeadGain", "ForceAutoTune", "ForceTorqueController",
               "AccordEpsGainScale", "AccordEpsSpringScale", "AccordTurnFFTaper",
               "GitCommit", "GitBranch", "GitRemote", "GitCommitDate", "Version", "TermsVersion",
               "CarParams", "DongleId"]


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
    cs_ang, cs_tq, cs_press, cs_sr = [], [], [], []          # carState extras, on the tcs axis
    marks, seg_span = [], {}
    failed = []
    params_dump = None
    for p in segs:
        sn = int(os.path.basename(p).split("--")[2])
        with open(p, "rb") as fh:
            data = zstandard.ZstdDecompressor().stream_reader(fh).read()
        it = clog.Event.read_multiple_bytes(data)
        lo, hi = None, None
        n18_at_seg_start = len(t18)
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
                cs = evt.carState
                tcs.append(tm); vego.append(cs.vEgo)
                cs_ang.append(cs.steeringAngleDeg)
                cs_tq.append(cs.steeringTorque)
                cs_press.append(1 if cs.steeringPressed else 0)
                try:
                    cs_sr.append(cs.steeringRateDeg)
                except Exception:
                    cs_sr.append(float("nan"))
            elif w == "userBookmark":
                marks.append(dict(seg=sn, mono=tm))
            elif w == "initData" and params_dump is None:
                try:
                    pd = {}
                    for e in evt.initData.params.entries:
                        k = e.key
                        if k in WANT_PARAMS:
                            try:
                                pd[k] = bytes(e.value).decode("utf-8", "replace")
                            except Exception:
                                pd[k] = repr(bytes(e.value)[:200])
                    pd["_all_keys_n"] = len(list(evt.initData.params.entries))
                    pd["_seg"] = sn
                    params_dump = pd
                except Exception as e:
                    print("  initData.params read failed: %s" % str(e)[:120], flush=True)
        seg_span[sn] = dict(lo=lo, hi=hi,
                            lo_can=(t18[n18_at_seg_start]
                                    if len(t18) > n18_at_seg_start else lo))
        print("  read %s" % os.path.basename(p), flush=True)

    A = lambda x, dt=float: np.asarray(x, dt)  # noqa: E731
    D = dict(t18=A(t18), tq=A(tq), rate=A(rate), sca=A(sca, int), t14=A(t14), ang=A(ang),
             t1ab=A(t1ab), b0=A(b0, int), b1=A(b1, int), te4=A(te4), cmd=A(cmd), req=A(req, int),
             tcs=A(tcs), vego=A(vego),
             cs_ang=A(cs_ang), cs_tq=A(cs_tq), cs_press=A(cs_press, int), cs_rate=A(cs_sr))
    os.makedirs(CACHE, exist_ok=True)
    np.savez(os.path.join(CACHE, TAG + ".npz"), **D)
    np.savez(os.path.join(CACHE, TAG + "_b4.npz"), t14b=A(t14b), b4=A(b4, int))

    t0 = D["t18"][0]
    for m in marks:
        m["t_route"] = m["mono"] - t0
        m["t_in_seg"] = m["mono"] - seg_span[m["seg"]]["lo_can"]
    order = sorted(seg_span)
    gaps = [dict(after_seg=a_, before_seg=b_,
                 gap_s=round(seg_span[b_]["lo_can"] - seg_span[a_]["hi"], 3),
                 contiguous_index=(b_ == a_ + 1))
            for a_, b_ in zip(order, order[1:])]
    out = dict(t0_mono=float(t0), route_prefix=PREFIX, tag=TAG, marks=marks,
               present_segments=order, missing_segments=missing, failed_segments=failed,
               gaps=gaps,
               gap_warning=("A missing segment leaves a REAL hole in the concatenated axes."),
               segs={str(k): dict(lo_route=v["lo"] - t0, hi_route=v["hi"] - t0,
                                  lo_can_route=v["lo_can"] - t0)
                     for k, v in seg_span.items()},
               lo_route_note="use lo_can_route; lo_route is initData's process-start stamp")
    with open(os.path.join(CACHE, TAG + "_marks.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    with open(os.path.join(CACHE, TAG + "_params.json"), "w") as fh:
        json.dump(params_dump or {}, fh, indent=1)

    # pointer copy so the study's own cache dir names the FULL route id (brief's requirement)
    pd_ = os.path.join(PTRCACHE, PREFIX)
    os.makedirs(pd_, exist_ok=True)
    with open(os.path.join(pd_, "CACHE-POINTER.json"), "w") as fh:
        json.dump(dict(route=PREFIX, tag=TAG,
                       v280_cache=os.path.join(CACHE, TAG + ".npz"),
                       b4_cache=os.path.join(CACHE, TAG + "_b4.npz"),
                       marks=os.path.join(CACHE, TAG + "_marks.json"),
                       params=os.path.join(CACHE, TAG + "_params.json"),
                       note=("v280-format cache, identical decode to extract_r62_r63_v280cache.py; "
                             "load with creep20_loop_id.load('%s'). The August r6d/r6e/r6f caches are "
                             "DIFFERENT ROUTES -- the dongle counter reset." % TAG)), fh, indent=1)

    print("route length %.1f s; %d bookmarks; %d segments" % (D["t18"][-1] - t0, len(marks), len(order)), flush=True)
    for m in marks:
        print("  bookmark seg %d  t_in_seg %.3f  t_route %.3f" % (m["seg"], m["t_in_seg"], m["t_route"]), flush=True)
    for g in gaps:
        if not g["contiguous_index"] or g["gap_s"] > 5.0:
            print("  GAP seg %d -> %d : %.3f s  (contiguous_index=%s)"
                  % (g["after_seg"], g["before_seg"], g["gap_s"], g["contiguous_index"]), flush=True)
    u, c = np.unique(A(b4, int), return_counts=True)
    print("b4 census", list(zip(u.tolist(), c.tolist())), flush=True)
    if params_dump:
        print("PARAMS (seg %s, %d keys total):" % (params_dump.get("_seg"), params_dump.get("_all_keys_n", -1)), flush=True)
        for k in WANT_PARAMS:
            if k in params_dump and k != "CarParams":
                print("   %-26s = %s" % (k, params_dump[k][:120]), flush=True)
    else:
        print("*** NO initData.params captured ***", flush=True)


if __name__ == "__main__":
    which = sys.argv[1:] or ["r6d", "r6e", "r6f"]
    if which == ["all"]:
        which = ["r6d", "r6e", "r6f"]
    for w in which:
        PREFIX, TAG, NSEG_NOMINAL = ROUTES[w]
        main()
