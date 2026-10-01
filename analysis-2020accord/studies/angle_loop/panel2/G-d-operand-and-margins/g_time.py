# -*- coding: utf-8 -*-
r"""g_time.py -- designer G's implementations through THE COMMON TIME SCORER (c2/rev2A/score_time.py), EXTENDED, not
forked.  What is changed, and only this:
  * ds_lane.DSLane is rebound (in this process only) to g_lane.GLane, a SUBCLASS that adds the angle-own 'box10' D
    operand through DSLane's own 'fine' path; every other column runs DSLane's arithmetic unchanged (GLane with no
    box10 column is DSLane -- g_time selftest CONTROL A checks it bit for bit against score_time.run on rev2-A's P2/F2).
  * the columns are designer G's implementations + rev2-A's P2 and F2 as same-batch references.
  * results go to _scratch/angle_loop/G-dop/time_<tag>.json, and the tables are made by rev2-A's own
    r2a_time_report.main with its paths pointed at this folder (score_time_out.md here).
Scenarios, members, speeds, sensors, plant, metrics and bars are score_time's, unchanged.  ANALYSIS ONLY.
usage: python g_time.py selftest | run | dense | report"""
from __future__ import annotations

import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g_ext as X  # noqa: E402
sys.path.insert(0, str(X.AL / "c2" / "rev2A"))
import r2a_common as R  # noqa: E402
import score_time as ST  # noqa: E402
import g_lane as GL  # noqa: E402
import ds_lane as DL  # noqa: E402
import ds_selftest as DST  # noqa: E402

_DSLANE_ORIG = DL.DSLane
DL.DSLane = GL.GLane                       # the extension (this process only)
OUT = X.OUT


SNAP = OUT / "g_impls_time_snapshot.json"


def columns():
    """the column set, from a SNAPSHOT of g_impls.json taken when a suite starts (so a later fit cannot change the
    columns of a running suite); falls back to g_impls.json."""
    imps = json.loads((SNAP if SNAP.exists() else OUT / "g_impls.json").read_text())
    cols = []
    for iid, im in imps.items():
        if iid.startswith("rev2A-"):
            continue                              # the references are added below from rev2-A's own tables
        rows = [tuple(r) for r in im["rows"]]
        if im["dkind"] == "fresh":
            cfg = DST.lane_cfg(X.DM.Des(dsrc="op", dop="fresh_rate", kd=im["kd"]), rows)
        elif im["dkind"] == "held":
            cfg = DST.lane_cfg(X.DM.Des(dsrc="rate_held", kd=im["kd"]), rows)
        else:
            cfg = dict(kind="angle", tbl=rows, kp=112, ki=int(im.get("ki", 56)), kd=int(im["kd"]), db=0, icl=4096, dcl=10240, thr=512,
                       dsrc="op", dop="box10", bx_sh=int(im.get("sh", 6)))
        cfg["ki"] = int(im.get("ki", 56))
        cols.append((iid, cfg))
    tabs = R.tables()
    for k in ("P2", "F2"):
        cols.append(("rev2A-" + k, R.lane_cfg(k, tabs[k])))
    return cols


def job(args):
    name, v, mem = args
    cc = columns()
    cfgs = [c for _, c in cc]
    scn = ST.scenario(name, v)
    t0 = time.time()
    r = ST.run(scn, cfgs, [], mem, v)
    m = ST.metrics(name, scn, r, v)
    return dict(name=name, v=v, member=mem, metrics={k: np.asarray(x).tolist() for k, x in m.items()},
                sec=time.time() - t0)


def run_suite(scens, speeds, members, tag, procs=5, snapshot=True, only=None):
    if snapshot:
        imps = json.loads((OUT / "g_impls.json").read_text())
        if only:
            imps = {k: v for k, v in imps.items() if k in only}
        SNAP.write_text(json.dumps(imps))
    jobs = [(s, v, m) for m in members for v in speeds for s in scens]
    t0 = time.time()
    out = []
    with Pool(procs) as pool:
        for i, res in enumerate(pool.imap_unordered(job, jobs, chunksize=1)):
            out.append(res)
            if (i + 1) % 60 == 0 or i + 1 == len(jobs):
                print(f"  {tag}: {i + 1}/{len(jobs)}, {time.time() - t0:.0f} s", flush=True)
    (OUT / f"time_{tag}.json").write_text(json.dumps(dict(labels=[k for k, _ in columns()], results=out)))
    return out


def selftest():
    """CONTROL A: GLane (no box10 column) == the original DSLane through score_time.run, bit for bit, on rev2-A's P2 / F2
    and every non-box10 G column.  CONTROL B: GLane's box10 operand == g_cave.box10_ref (the listing's arithmetic, which
    the assembled bytes match in H1) tick by tick over a scenario."""
    import g_cave as GC
    lines = []
    cc = [c for c in columns()]
    nb = [(k, c) for k, c in cc if c.get("dop") != "box10"]
    cfgs = [c for _, c in nb]
    for nm, v in (("rh", 8.0), ("s05", 26.9), ("ov_fade", 3.1)):
        scn = ST.scenario(nm, v)
        DL.DSLane = GL.GLane
        r1 = ST.run(scn, cfgs, [], "nominal", v)
        DL.DSLane = _DSLANE_ORIG
        r2 = ST.run(scn, cfgs, [], "nominal", v)
        DL.DSLane = GL.GLane
        d = int(np.abs(r1["T"].astype(int) - r2["T"].astype(int)).max())
        lines.append(f"CONTROL A {nm}@{v}: GLane vs DSLane through score_time.run, {len(cfgs)} columns: max|dT| {d}  "
                     f"{'OK' if d == 0 else 'FAIL'}")
    # CONTROL B
    bx = [(k, c) for k, c in cc if c.get("dop") == "box10"]
    if bx:
        k, c = bx[0]
        lane = GL.GLane(ST.HT.base_cal(), [c])
        rng = np.random.default_rng(3)
        th = 0
        bad = 0
        Cc, W = 0, 0
        Eprev_sent = True
        for n in range(4000):
            if n % 10 == 5:
                th += int(rng.integers(-3, 4)) if rng.random() < 0.6 else 0
            ramp = 0x8000 if not (1500 <= n < 1530) else 0
            first = lane.Eprev[0] == GL.SENT
            op, Cn, Wn, run = lane.box_op(th, ramp, 1)
            # reference (g_cave.box10_ref semantics)
            cells = {"6cf8": GL.SENT if first else 0, "6a00": th, "6c44": int(lane.bxC[0]), "6c40": int(lane.bxW[0]),
                     "6a5e": 0, "4f68": 0}
            _, _, _, op_ref, c2 = GC.box10_ref(c["tbl"], c["bx_sh"], 512, 0, 0, 0, 0, 0x8000, cells)
            if run[0] and (op[0] != op_ref or Wn[0] != c2["6c40"] or Cn[0] != c2["6c44"]):
                bad += 1
            lane.tick(th, 0, 4 * th, 0, 0, 2304, ramp, 1, 1)
        lines.append(f"CONTROL B box10 ({k}): GLane operand vs g_cave.box10_ref over 4000 ticks (refreshes every 10, "
                     f"a 30-tick skip): {bad} mismatches  {'OK' if bad == 0 else 'FAIL'}")
    out = "\n".join(lines)
    print(out)
    (HERE / "g_time_selftest.txt").write_text(out + "\n", encoding="utf-8")


def report():
    import r2a_time_report as RT
    R.OUT = OUT
    R.HERE = HERE
    RT.R.OUT = OUT
    RT.R.HERE = HERE
    RT.main()


def report_late():
    """the late suite's tables by the same r2a_time_report.main, written to score_time_late_out.md (no dense)."""
    import shutil
    import tempfile
    import r2a_time_report as RT
    tmp = Path(tempfile.mkdtemp())
    orig_load = RT.load
    RT.load = lambda tag: orig_load("late") if tag == "full" else (_ for _ in ()).throw(FileNotFoundError(tag))
    R.OUT, R.HERE = OUT, tmp
    RT.R.OUT, RT.R.HERE = OUT, tmp
    try:
        RT.main()
    finally:
        RT.load = orig_load
    shutil.move(str(tmp / "score_time_out.md"), str(HERE / "score_time_late_out.md"))


if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else "run"
    if w == "selftest":
        selftest()
    elif w == "run":
        run_suite(ST.SCENS, ST.SPEEDS, ST.MEMBERS, "full")
    elif w == "dense":
        # reduced from score_time's own dense (3-30 every 0.25, s02/rh/ssm) for compute: every 0.5 m/s, s02 + rh
        sp = tuple(round(x, 2) for x in np.arange(3.0, 30.01, 0.5))
        run_suite(("s02", "rh"), sp, ("nominal", "bc"), "dense", snapshot=False)
    elif w == "late":
        # a late-fitted implementation through the identical suite, with rev2-A's P2 / F2 again as same-batch references
        run_suite(ST.SCENS, ST.SPEEDS, ST.MEMBERS, "late", only=set(sys.argv[2:]))
    elif w == "report":
        report()
    elif w == "report_late":
        report_late()
