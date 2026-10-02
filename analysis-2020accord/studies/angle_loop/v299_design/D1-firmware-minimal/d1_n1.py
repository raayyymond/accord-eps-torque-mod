# -*- coding: utf-8 -*-
r"""d1_n1.py -- the N1 / N5 hand-release and reversal lens for D1's integral-policy variants, on the C3 NONLINEAR
refuter's independent loop (refute_c3_nonlinear/c3nl_sim.py + c3nl_lens.py scenarios, unchanged) via rev2-B's
rb_n1.Lane2 (the C3B-P lane, Ki settable), extended here to Lane3 with D1's switches:
    hard  : the hard-freeze threshold on gp-0x4f68 (V298 512)
    sgn   : the opposing-hand threshold (V298 300; 0 = clause removed)
    asym  : D1's ASYMMETRIC A3 bound: when sign(theta) != sign(E') (the I would wind TOWARD CENTRE) the |theta| term is
            dropped, so the inward I is bounded by B = 1250 S (~200 T, the friction allowance) instead of 16|theta|+B
    cap   : the A3 low-speed cap (V298 4096 at v <= 1382 counts)
    mg    : the motion gate deadband A0 for the opposing clause (D1b; -1 = off)
CONTROL: Lane3(V298 settings) == rb_n1.Lane2('theta', 40, 300) BIT FOR BIT on a scenario (asserted).
Scenarios: c3nl_lens.build names -- out_<m>_<w>_<hold> (outward light hand, stiff Kh 2000), part_<frac>_<w>_<hold>
(inward partial drag), nudge_<d>_<w>_<hold> (straight-road nudge), rev_<a> (held-turn reversal, N5).
Metric: release lurch = max(under, over) past the setpoint after release (deg); N5 = ovs2 (fraction of A past -A).
Also: the lane's peak |hand force| during the hold (how hard the lane fights the light hand) -- r['hf'].
usage: python d1_n1.py        (Pool over scenarios; wall time printed; < 30 s)
"""
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
sys.path.insert(0, str(AL / "c3" / "rev2B"))
sys.path.insert(0, str(AL / "refute_c3_nonlinear"))
import rb_n1 as N  # noqa: E402
import c3nl_lens as LN  # noqa: E402

S = N.S
s16, s32 = S.s16, S.s32
VARS = {   # name: (hard, sgn, asym, cap, mg)
    "V298": (512, 300, False, 4096, -1),
    "D1a (1229, opp off)": (1229, 0, False, 4096, -1),
    "D1a-c8k": (1229, 0, False, 8192, -1),
    "D1b (1229, opp300 gated)": (1229, 300, False, 4096, 10),
    "D1c (1229, opp off, ASYM)": (1229, 0, True, 4096, -1),
    "D1c-c8k": (1229, 0, True, 8192, -1),
}
for nm, (hd, sg, asy, cap, mg) in VARS.items():
    S.IMPL["D1|" + nm] = dict(S.IMPL["C3B-P"], hard=hd, sgn=sg, asym=asy, cap_=cap, mg=mg)


class Lane3(N.Lane2):
    def __init__(self, impls, ki=40):
        super().__init__(impls, "theta", ki, 0)
        I = S.IMPL
        g = lambda k, d: np.array([I[i].get(k, d) for i in impls], np.int64)  # noqa: E731
        self.hard = g("hard", 512)
        self.sgnv = g("sgn", 0)
        self.asym = np.array([bool(I[i].get("asym", False)) for i in impls])
        self.cap = g("cap_", 4096)
        self.mg = g("mg", -1)

    def tick(self, a6a00, abe, x6a56, sp69ae, tq, ramp, act, req, vw, pol=-1):
        c = S.CAL
        B = self.B
        bc = lambda a: np.broadcast_to(np.asarray(a, np.int64), (B,))  # noqa: E731
        ramp, act, req, tq, vw = bc(ramp), bc(act), bc(req), bc(tq), bc(vw) & 0xFFFF
        x = s16(a6a00)
        valid = (x >= -12000) & (x <= 12000)
        s_old = np.where(self.lane_ok == 1, self.s, 0)
        s_new = s32((s32(0 * s_old) >> 10) + (s32(x * 8192) >> 10))
        r26 = np.clip(s32(s_old + s_new), -65535, 65535)
        self.s = np.where(valid, s_new, self.s)
        r26 = np.where(valid, r26, 0)
        self.lane_ok = np.where(valid, 1, 2)
        run = valid & (ramp != 0) & (req == 1)
        sp = s16(sp69ae)
        E = s32(s32(sp << 2) - r26)
        ab = s16(abe)
        op = np.where(((ab + 13000) & 0xFFFFFFFF) <= 26000, ab, 0)
        G = self.gl[self.ar, vw]
        prod = E * G
        self.wraps += int(np.count_nonzero(s32(prod) != prod))
        Ep = s32(prod) >> 8
        atq = np.minimum(np.abs(tq), 0xFFFF)
        f_hard = atq > self.hard                                         # [D1] movea THR (512 -> 1229)
        th = s16(a6a00)
        sh = np.where(vw > self.vth, self.sh_hi, self.sh_lo)
        opnd = np.abs(th)
        inward = (th ^ Ep) < 0                                           # [D1c] sign(theta) != sign(E')
        opnd = np.where(self.asym & inward, 0, opnd)                     # [D1c] mov 0,r9: bound = B
        bound = s32((opnd << sh) + self.Bb)
        capon = (self.vcap >= 0) & ~(vw > self.vcap)
        bound = np.where(capon & (bound > self.cap), self.cap, bound)    # [D1] movea CAP (4096 -> 8192)
        Is = self.I8 >> 10
        t = np.where(Ep >= 0, Is, -Is)
        f_arb = self.arb_on & (t >= bound)
        f_ramp = (ramp & 0x8000) == 0
        hs = s16(tq)
        f_opp = (self.sgnv > 0) & (np.abs(hs) > self.sgnv) & ((hs ^ Ep) < 0)
        closing = np.where(Ep >= 0, ab + self.mg < 0, -ab + self.mg < 0)
        f_opp = f_opp & ~((self.mg >= 0) & closing)                      # [D1b] motion gate
        frz = f_hard | (~f_hard & (f_opp | f_arb | f_ramp))
        e5 = np.where(frz, 0, Ep >> 5)
        inc = s32(e5 * self.ki) >> 3
        acc = (self.I8 >> 3) + inc
        self.wraps += int(np.count_nonzero(s32(acc) != acc))
        I = np.clip(s32(acc), -self.icl, self.icl)
        I8n = s32(I << 3)
        P = np.clip(s32(Ep * S.KP) >> 8, -c["PCL"], c["PCL"])
        Dp = s32(self.kd * op) >> 3
        Dh = s32(-self.kd * s16(x6a56)) >> 3
        D = np.clip(np.where(self.fresh, Dp, Dh), -S.DCL, S.DCL)
        Sx = s32((I >> 7) + P + D)
        i682f = np.minimum(np.abs(tq >> 5), 255)
        fB = S.lerp_vec(*c["fadeB"], i682f)
        f = ((S.FA0 * fB) & 0xFFFF) >> 8
        Sf = s32(Sx * f) >> 8
        SCL = c["SCL"]
        Sc = np.where(Sf > SCL, SCL, np.where(Sf < -SCL, -SCL, s16(Sf)))
        Sc = np.where(run, Sc, 0)
        self.I8 = np.where(run, I8n, 0)
        t1 = s32(Sc * c["ob"]) >> 10
        t2 = s32(c["oa"] * self.olag) >> 10
        o_new = s32(t2 + t1)
        y = s32(self.olag + o_new) >> 5
        self.olag = o_new
        yr = s16(s32(y * ramp) >> 15)
        if c["g74a3"] == 1:
            blk = ((s16(y) <= c["dz"]) & (y >= -c["dz"])) | (s32(y * self.Tprev) <= 0)
            yr = np.where((act == 0) & blk, 0, yr)
        k = pol * c["fwd"]
        r11 = s32(yr * k) >> 15
        Tt = np.clip(r11, -c["OCL"], c["OCL"])
        self.Tprev = yr
        self.log = dict(I=np.where(run, I >> 7, 0), P=np.where(run, P, 0), D=np.where(run, D, 0),
                        frz=frz & run, farb=f_arb & ~f_hard & run, bound=bound, Ep=Ep, run=run)
        return s16(Tt)


SPEEDS = (3.1, 5.0, 6.5, 8.0, 10.0, 12.0, 14.0, 18.0, 22.0)
MEMBERS = ("nominal", "bc", "F_hi", "b_lo*J_hi")
SCNS = ["out_2_400_1", "out_2_511_3", "out_2_1000_3", "out_1.5_511_3", "part_0.5_511_3", "part_0.5_1000_3",
        "nudge_5_511_3", "nudge_5_1000_3", "rev_1.5", "rev_2"]


def control():
    cols = [dict(impl="C3B-P", member=m, v=v, age=0) for m in ("nominal", "b_lo*J_hi") for v in (5.0, 12.75)]
    cols3 = [dict(c, impl="D1|V298") for c in cols]
    scn, meta = LN.build("out_2_511_3", cols)
    rO = N.run_with(lambda impls: N.Lane2(impls, "theta", 40, 300), cols, scn)
    rN = N.run_with(lambda impls: Lane3(impls), cols3, scn)
    return float(np.abs(rO["th"] - rN["th"]).max()), int(np.abs(rO["T"].astype(int) - rN["T"].astype(int)).max())


def job(scn_name):
    cols = [dict(impl="D1|" + vn, member=m, v=v, age=0) for vn in VARS for m in MEMBERS for v in SPEEDS]
    scn, meta = LN.build(scn_name, cols)
    r = N.run_with(lambda impls: Lane3(impls), cols, scn)
    mt = LN.metrics(scn_name, meta, r, cols)
    out = {}
    for vn in VARS:
        for band, lo, hi in (("<8", 0, 7.99), ("8-12.5", 8, 12.49), ("12.5-22", 12.5, 99)):
            idx = [i for i, c in enumerate(cols) if c["impl"] == "D1|" + vn and lo <= c["v"] <= hi]
            if scn_name.startswith("rev"):
                val = float(np.max(np.asarray(mt["ovs2"])[idx]))
                hfp = float("nan")
            else:
                under = np.asarray(mt.get("under", mt.get("over")))
                over = np.asarray(mt.get("over"))
                val = float(np.max(np.maximum(under, over)[idx]))
                hfp = float(np.max(np.abs(r["hf"][:, idx])))
            out[(vn, band)] = (val, hfp)
    return scn_name, out


if __name__ == "__main__":
    t0 = time.time()
    dth, dT = control()
    lines = [f"CONTROL Lane3(V298) vs rb_n1.Lane2('theta', 40, 300): max |dth| {dth:.2e} deg, max |dT| {dT} counts"]
    assert dth == 0.0 and dT == 0, "control failed"
    with Pool(10) as pool:
        R = dict(pool.map(job, SCNS))
    lines.append("release lurch past the setpoint (deg, max over members x speeds in band); rev_* = N5 ovs2 (frac of A)")
    lines.append("hf = peak |hand force| the stiff hand needed during the hold (plant torque units) -- how hard the lane")
    lines.append("     fought the light hand; bar: lurch < 8 deg (N1, the judge's), ovs2 <= 0.20")
    for scn in SCNS:
        lines.append(f"-- {scn} --")
        for vn in VARS:
            cells = []
            for band in ("<8", "8-12.5", "12.5-22"):
                val, hfp = R[scn][(vn, band)]
                cells.append(f"{band:7s} {val:6.2f}" + ("" if np.isnan(hfp) else f" (hf {hfp:5.0f})"))
            lines.append(f"   {vn:27s} " + " | ".join(cells))
    lines.append(f"wall {time.time() - t0:.1f} s")
    o = HERE / "out"
    o.mkdir(exist_ok=True)
    (o / "d1_n1.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
