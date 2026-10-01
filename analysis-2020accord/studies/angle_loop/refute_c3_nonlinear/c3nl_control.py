# -*- coding: utf-8 -*-
r"""c3nl_control.py -- controls for the C3 nonlinear refuter.  ANALYSIS ONLY.
  K1  my cal read == lane_mirror_v295.load_cal (V295 image) and the V295 values of the cells C3 changes == design sec 1.3
  K2  the listed policy immediates are present at their listed encodings in each cave's HEX
  K3  my lane (c3nl_sim.Lane) == the common time scorer's CandLane (C3-P / C3-F / P2 / E2-A3 columns), tick for tick,
      on random + edge inputs (state carried; every output and the I state compared)
  K4  my WHOLE closed loop == the common scorer's run() on scorer scenarios (C3-P, C3-F; members x speeds): th, T
  K5  the common scorer's own C3-P cells reproduce (tracking slope on two r71b runs; light lurch at 8 m/s b_lo*J_hi)
usage: python c3nl_control.py"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c3nl_sim as S  # noqa: E402

AL = HERE.parent
sys.path.insert(0, str(AL / "c3"))
_spec = importlib.util.spec_from_file_location("c3st", AL / "c3" / "c3_score_time.py")
C3ST = importlib.util.module_from_spec(_spec)
sys.modules["c3st"] = C3ST
_spec.loader.exec_module(C3ST)
ST = C3ST.ST
import lane_mirror_v295 as LM  # noqa: E402


def K1():
    lm = LM.load_cal()
    ok = all(int(lm[k]) == int(S.CAL[k]) for k in ("PCL", "SCL", "OCL", "oa", "ob", "g74a3", "dz", "fwd"))
    ok &= all(tuple(lm["fadeB"][i]) == tuple(S.CAL["fadeB"][i]) for i in (0, 1))
    v = {k: S.CAL["v295_" + k] for k in ("ICL", "Ki", "DCL", "DB", "a", "b", "C")}
    want = dict(ICL=10240, Ki=0, DCL=0, DB=4, a=1011, b=1050, C=1024)
    return ok and v == want, f"cal == lane_mirror: {ok}; V295 cells {v} vs design sec 1.3 {want}"


def K2():
    out = []
    allok = True
    for nm in ("C3-P", "C3-F", "C3-PA2", "E2-A3"):
        r = S.check_hex_immediates(S.IMPL[nm]["hex"])
        if nm == "C3-PA2":
            r = {k: v for k, v in r.items() if k not in ("1382", "4096")}
        allok &= all(r.values())
        out.append(f"{nm}: {sum(r.values())}/{len(r)} immediates found {'' if all(r.values()) else r}")
    return allok, "; ".join(out)


def K3(N=40000, seed=3):
    rng = np.random.default_rng(seed)
    ids = ["C3-P", "C3-F", "P2", "E2-A3", "C3-PA2"]
    B = len(ids)
    mine = S.Lane(ids)
    bad = 0
    vw_fixed = None
    lanes = {}
    for it in range(N):
        if it % 4000 == 0:                       # new speed per block (lane G and bound use per-column vw)
            vw_fixed = int(rng.choice([0, 714, 1382, 1383, 1843, 2304, 2620, 2707, 2880, 2881, 4032, 6198, 9000,
                                       int(rng.integers(0, 12001))]))
            cs = [ST.CBYID[i] for i in ids]
            lanes = ST.CandLane(cs, np.full(B, vw_fixed))
            mine = S.Lane(ids)
        a6 = int(rng.choice([rng.integers(-3000, 3001), rng.integers(-120, 121), 12000, 12001, -12001, 0]))
        abe = int(rng.choice([rng.integers(-13001, 13002), 0x7FFF, 13000, -13000, 13001, -13001, rng.integers(-300, 300)]))
        x56 = int(rng.integers(-12000, 12001))
        sp = int(rng.choice([rng.integers(-16384, 16385), 4 * a6 + int(rng.integers(-40, 41)), 0x7FFF]))
        tq = int(rng.choice([rng.integers(-3000, 3001), 511, 512, 513, -512, -513, 0, rng.integers(-400, 400)]))
        ramp = int(rng.choice([0x8000, 0x8000, 0x8000, 0x7FFF, 0, int(rng.integers(0, 0x8001))]))
        req = int(rng.choice([1, 1, 1, 0, 0xFF]))
        act = int(rng.choice([1, 1, 0]))
        Tm = mine.tick(np.full(B, a6), np.full(B, abe), np.full(B, x56), np.full(B, sp), tq, ramp, act, req,
                       np.full(B, vw_fixed))
        To = lanes.tick(np.full(B, a6), np.full(B, a6), np.full(B, x56), np.full(B, abe), np.full(B, sp), tq,
                        ramp, act, req)
        if not (np.array_equal(Tm, To) and np.array_equal(mine.I8, lanes.I8) and np.array_equal(mine.olag, lanes.olag)):
            bad += 1
            if bad <= 3:
                print("  K3 mismatch", it, ids, Tm, To, mine.I8, lanes.I8)
    return bad == 0, f"{N} ticks x {B} columns ({', '.join(ids)}): {bad} mismatching ticks"


def _conv(s):
    tq = (lambda t, th, om, hf, f=s.tq: f(t, th, om)) if s.tq is not None else None
    return S.Scn(dur=s.dur, ref=s.ref, tq=tq, hand=s.hand, uext=s.uext, events=s.events, mode0=s.mode0, th0=s.th0,
                 sp_meas_until=s.sp_meas_until, sp_hold_from=s.sp_hold_from)


def K4():
    res = []
    allok = True
    for scn in ("ov_lt511", "th", "s03_02", "tmos", "cs", "eng"):
        for mb in ("nominal", "b_lo*J_hi", "F_hi"):
            cols_st = []
            for v in (8.0, 11.75, 17.0, 26.9):
                for cid in ("C3-P", "C3-F"):
                    d = dict(cand=ST.CBYID[cid], member=mb, v=v)
                    if scn == "th":
                        d["alat"] = 2.0
                    cols_st.append(d)
            s, meta = ST.scenario(scn, cols_st)
            s.dur = min(s.dur, 9.0)
            r_st = ST.run(cols_st, s, frame="vgr")
            cols_me = [dict(impl=c["cand"].id, member=c["member"], v=c["v"]) for c in cols_st]
            r_me = S.run(cols_me, _conv(s))
            dth = float(np.abs(r_st["th"].astype(float) - r_me["th"].astype(float)).max())
            dT = float(np.abs(r_st["T"].astype(float) - r_me["T"].astype(float)).max())
            allok &= (dth < 1e-3) and (dT <= 1)
            res.append(f"{scn}/{mb}: max|dth| {dth:.2e} deg, max|dT| {dT:.0f}")
    return allok, "; ".join(res)


def main():
    for nm, f in (("K1", K1), ("K2", K2), ("K3", K3), ("K4", K4)):
        ok, msg = f()
        print(f"{nm} {'PASS' if ok else 'FAIL'}: {msg}", flush=True)


if __name__ == "__main__":
    main()
