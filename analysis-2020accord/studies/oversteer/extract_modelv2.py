# -*- coding: utf-8 -*-
"""extract_modelv2.py -- pull modelV2 (lane lines, road edges, planned path, desiredCurvature)
for r39 / r3a / r3c, plus initData.params, for the PLAN-vs-EXECUTION read (2026-09-05).

Nothing in the existing `_backcalc.npz` family carries modelV2: every prior measurement in this kit
compared `achieved` against the CONTROLLER'S OWN SETPOINT and so cannot see a planner error.

Channels (all on the modelV2 event clock, logMonoTime seconds):
  mdl_t                     (N,)      logMonoTime
  mdl_x                     (33,)     the model's x grid (asserted constant across the route)
  mdl_ll1_y / mdl_ll2_y     (N,33)    laneLines[1] (left) / [2] (right) lateral, device frame
  mdl_re0_y / mdl_re1_y     (N,33)    roadEdges[0] / [1]
  mdl_pos_y                 (N,33)    position.y -- the model's planned path
  mdl_pos_ystd              (N,33)    position.yStd
  mdl_llprob                (N,4)     laneLineProbs
  mdl_llstd                 (N,4)     laneLineStds
  mdl_descurv               (N,)      action.desiredCurvature   <-- the PLAN
  mdl_lcs / mdl_lcd         (N,)      meta.laneChangeState / laneChangeDirection (ints)
  mdl_frameid               (N,)
  params_json               ()        initData.params, first segment (str->str, undecodable -> hex)
Run: python extract_modelv2.py r39 r3a r3c
"""
import glob, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "rlog-tools"))
RLOGS = os.path.join(ROOT, "analysis-2020accord", "rlogs")
OUT = os.path.join(HERE, "_scratch"); os.makedirs(OUT, exist_ok=True)

ROUTES = {
    "r39": ("75604b0a432fdc89_00000039--f56039af87", "V282-laf2.11-rdf43"),
    "r3a": ("75604b0a432fdc89_0000003a--283a39a1d6", "V282-laf4.0-tsfdo"),
    "r3c": ("75604b0a432fdc89_0000003c--927965c2b4", "V282-laf3.6-tsfdo"),
}
NPT = 33

_LCS = {"off": 0, "preLaneChange": 1, "laneChangeStarting": 2, "laneChangeFinishing": 3}
_LCD = {"none": 0, "left": 1, "right": 2}


def _fixlen(v):
    a = np.asarray(v, dtype=np.float32)
    if a.size == NPT:
        return a
    b = np.full(NPT, np.nan, np.float32)
    b[:min(a.size, NPT)] = a[:NPT]
    return b


def read_segment(path, out, holder):
    import zstandard
    from cereal import log as clog
    with open(path, "rb") as fh:
        data = zstandard.ZstdDecompressor().stream_reader(fh).read()
    it = clog.Event.read_multiple_bytes(data)
    n = 0
    while True:
        try:
            evt = next(it)
        except StopIteration:
            break
        except Exception as exc:
            print("    torn after %d events: %s" % (n, str(exc).splitlines()[0][:70]))
            break
        n += 1
        try:
            w = evt.which()
        except Exception:
            continue
        if w == "initData" and holder.get("params") is None:
            p = {}
            try:
                for e in evt.initData.params.entries:
                    k = str(e.key)
                    try:
                        p[k] = bytes(e.value).decode("utf-8")
                    except Exception:
                        p[k] = "0x" + bytes(e.value).hex()
            except Exception as exc:
                p = {"_error": str(exc)[:200]}
            holder["params"] = p
        elif w == "modelV2":
            m = evt.modelV2
            try:
                ll = m.laneLines
                re = m.roadEdges
                pos = m.position
                if len(ll) < 3 or len(re) < 2:
                    continue
                if holder.get("x") is None:
                    holder["x"] = np.asarray(pos.x, np.float32)[:NPT]
                A = out.setdefault
                A("mdl_t", []).append(evt.logMonoTime * 1e-9)
                A("mdl_frameid", []).append(float(m.frameId))
                A("mdl_ll1_x", []).append(_fixlen(ll[1].x))
                A("mdl_pos_x", []).append(_fixlen(pos.x))
                A("mdl_ll1_y", []).append(_fixlen(ll[1].y))
                A("mdl_ll2_y", []).append(_fixlen(ll[2].y))
                A("mdl_re0_y", []).append(_fixlen(re[0].y))
                A("mdl_re1_y", []).append(_fixlen(re[1].y))
                A("mdl_pos_y", []).append(_fixlen(pos.y))
                A("mdl_pos_ystd", []).append(_fixlen(pos.yStd))
                A("mdl_ori_z", []).append(_fixlen(m.orientation.z))
                A("mdl_pos_t", []).append(_fixlen(pos.t))
                pr = np.asarray(m.laneLineProbs, np.float32)
                st = np.asarray(m.laneLineStds, np.float32)
                A("mdl_llprob", []).append(pr[:4] if pr.size >= 4 else np.pad(pr, (0, 4 - pr.size), constant_values=np.nan))
                A("mdl_llstd", []).append(st[:4] if st.size >= 4 else np.pad(st, (0, 4 - st.size), constant_values=np.nan))
                A("mdl_descurv", []).append(float(m.action.desiredCurvature))
                A("mdl_lcs", []).append(float(_LCS.get(str(m.meta.laneChangeState), -1)))
                A("mdl_lcd", []).append(float(_LCD.get(str(m.meta.laneChangeDirection), -1)))
            except Exception:
                continue
    return n


def main(tag):
    prefix, build = ROUTES[tag]
    segs = sorted(glob.glob(os.path.join(RLOGS, "%s--*--rlog.zst" % prefix)),
                  key=lambda p: int(os.path.basename(p).split("--")[2]))
    have = [int(os.path.basename(p).split("--")[2]) for p in segs]
    missing = [i for i in range(max(have) + 1) if i not in have] if have else []
    if missing:
        print("  *** SEGMENTS MISSING FROM DISK: %s ***" % missing, flush=True)
    out, holder = {}, {}
    for p in segs:
        print("  %s" % os.path.basename(p), flush=True)
        read_segment(p, out, holder)
    D = {}
    for k, v in out.items():
        D[k] = np.asarray(v, np.float32) if isinstance(v[0], np.ndarray) else np.asarray(v, np.float64)
    D["mdl_x"] = holder.get("x", np.full(NPT, np.nan, np.float32))
    t = D["mdl_t"]; dt = np.diff(t); big = np.flatnonzero(dt > 5.0)
    D["gap_starts"] = np.asarray([t[i] for i in big], float)
    D["gap_ends"] = np.asarray([t[i + 1] for i in big], float)
    D["segments_present"] = np.asarray(have, float)
    D["segments_missing"] = np.asarray(missing, float)
    D["params_json"] = np.array(json.dumps(holder.get("params")))
    D["build"] = np.array(build); D["prefix"] = np.array(prefix)
    np.savez(os.path.join(OUT, "%s_modelv2.npz" % tag), **D)
    print("wrote %s: n=%d  keys=%d" % (tag, len(t), len(D)), flush=True)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        main(a)
