# -*- coding: utf-8 -*-
r"""d1_time.py -- the panel-2 COMMON TIME SCORER (panel2/score_time.py, imported UNCHANGED) on D1's variants, plus
three REACTION-TWIST scenarios the scorer does not run (the hands-off torque word = the r79-measured reaction model).

What is added (and controlled):
  * D1Lane = score_time.CandLane with D1c's ASYMMETRIC A3 bound (the |theta| term dropped when sign(theta) != sign(E'),
    so the I may wind toward centre only to B = 1250 S).  CONTROL: D1Lane with asym off == CandLane bit for bit.
  * Cands (score_time.Cand switches): V298 = GB-P, fresh D Kd 48, Ki 40, ICL 8192, A3, opposing 300, hard 512,
    dir-2 ramp (328/66), fade = the stock arm (V298 re-wrote 0xE54FC := 0xE564C, so its arm-2 fade IS the stock one).
    D1c = hard 1229, opposing clause removed (sgn 0), asym bound.  D1c-c8k = D1c + cap 8192.
  * Twist scenarios (BELIEF: a model of the measured word): word = J a + b w + Fc tanh(w/2) + k th + c0 + AR(1) noise,
    coefficients and noise (std, lag-1 autocorr at 100 Hz) from d1_r79.py's fit on route 79 (settled, hands-off),
    held at 100 Hz like the 0x18F word.  hardT = 'hard' + twist; stT = 'st' + twist; thT = 'th' (a 1.0 / 2.5) + twist.
    Extra metrics: hand-freeze duty and toggles/s, 4-8 Hz wheel-rate rms (the ratchet band), slips (stick events).
usage: python d1_time.py      (Pool over scenarios; wall time printed)
"""
import importlib.util
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
sys.path.insert(0, str(AL / "c3" / "rev2B"))
import rb_table as TB  # noqa: E402

_st = importlib.util.spec_from_file_location("p2_st_d1", AL / "panel2" / "score_time.py")
ST = importlib.util.module_from_spec(_st)
sys.modules["p2_st_d1"] = ST
_st.loader.exec_module(ST)
s16, s32 = ST.s16, ST.s32
GBP = tuple(tuple(r) for r in TB.GB_P)
ARB_C8 = (6, 4, 2880, 1250, 1382, 8192)
REACT = json.loads((HERE / "out" / "d1_r79.json").read_text())["reaction"]


def rows_g0(g0):
    r = [list(x) for x in GBP]
    r[0][1] = g0
    r[0][2] = int(round((r[1][1] - g0) * 4096 / (r[1][0] - r[0][0])))
    return tuple(tuple(x) for x in r)


def mk(cid, thr, sgn, asym, arb, rows=GBP, mg=-1):
    c = ST.Cand(cid, "D1", rows, "fresh", 48, ki=40, icl=8192, arb=arb, sgn_thr=sgn, thr=thr, ramp_in=328, ramp_out=66,
                note="D1 variant")
    c.asym = asym
    c.mg = mg
    return c


CANDS = [mk("V298", 512, 300, False, ST.ARB_A3), mk("D1c", 1229, 0, True, ST.ARB_A3),
         mk("D1c-G0", 1229, 0, True, ST.ARB_A3, rows=rows_g0(1400)), mk("D1b", 1229, 300, False, ST.ARB_A3, mg=10)]
CANDS_C8 = [mk("V298", 512, 300, False, ST.ARB_A3), mk("D1c", 1229, 0, True, ST.ARB_A3),
            mk("D1c-c8k", 1229, 0, True, ARB_C8)]


class D1Lane(ST.CandLane):
    def __init__(self, cands, vw):
        super().__init__(cands, vw)
        self.asym = np.array([bool(getattr(c, "asym", False)) for c in cands])
        self.hf = np.zeros(self.B, np.int64)          # hand-freeze count, toggles
        self.htog = np.zeros(self.B, np.int64)
        self.hprev = np.zeros(self.B, bool)
        self.mg = np.array([getattr(c, "mg", -1) for c in cands], np.int64)
        self.a3n = np.zeros(self.B, np.int64)
        self.a3tog = np.zeros(self.B, np.int64)
        self.a3prev = np.zeros(self.B, bool)
        D1Lane.LAST = self

    def cave_stage(self, sp, r26, ramp, a6a00, abe, tq, I8, Eprev, bxC, bxW):
        E = s32((sp << 2) - r26)
        prod = E * self.G
        wr = int(np.count_nonzero(s32(prod) != prod))
        Ep = s32(prod) >> 8
        atq = np.minimum(np.abs(tq), 0xFFFF)
        lk_on = self.leak_s > 0
        c1 = atq > np.where(lk_on, self.leak_thr, self.thr)
        hs = s16(tq)
        c2 = (self.sgn > 0) & (np.abs(hs) > self.sgn) & ((hs ^ Ep) < 0)
        ab0 = s16(abe)
        closing = np.where(Ep >= 0, ab0 + self.mg < 0, -ab0 + self.mg < 0)
        c2 = c2 & ~((self.mg >= 0) & closing)                                   # [D1b] motion gate
        I_S = I8 >> 10
        t = np.where(Ep >= 0, I_S, -I_S)
        th6 = s16(a6a00)
        sh = np.where((self.arb_sh_lo >= 0) & ((self.vw & 0xFFFF) <= self.arb_vth), self.arb_sh_lo, self.arb_sh)
        opnd = np.where(self.asym & ((th6 ^ Ep) < 0), 0, np.abs(th6))          # [D1c] the asymmetric bound
        bound = s32((opnd << np.where(self.arb_on, sh, 0)) + self.arb_B)
        capon = (self.arb_vcap >= 0) & ((self.vw & 0xFFFF) <= self.arb_vcap)
        bound = np.where(capon & (bound > self.arb_cap), self.arb_cap, bound)
        c3 = self.arb_on & (t >= bound)
        c4 = self.ramp_frz & ((np.asarray(ramp, np.int64) & 0x8000) == 0)
        leak = c1 & lk_on
        frz = (c1 & ~lk_on) | (~c1 & c2) | (~c1 & ~c2 & (c3 | c4))
        hand = (c1 & ~lk_on) | (~c1 & c2)
        self.hf += hand
        self.htog += hand != self.hprev
        self.hprev = hand
        a3 = ~hand & c3
        self.a3n += a3
        self.a3tog += a3 != self.a3prev
        self.a3prev = a3
        I8c = I8
        I8c = np.where(frz & (atq > self.reset), 0, I8c)
        I8c = np.where(~frz & ~leak & (atq > self.eb_lo), s32(I8c - (I8c >> self.eb_sh)), I8c)
        I8c = np.where((self.hb_sh > 0) & c1 & ~lk_on, s32(I8c - (I8c >> self.hb_sh)), I8c)
        r6 = np.where(leak, s32(-(I8 >> np.where(lk_on, self.leak_s, 31))), 0)
        ab = s16(abe)
        abv = ((ab + 13000) & 0xFFFFFFFF) <= 26000
        op_f = np.where(abv, ab, 0)
        op = np.where(self.dop == 0, op_f, r26)
        return dict(Ep=Ep, leak=leak, frz=frz, r6=r6, op=op, I8c=I8c, bxC=bxC, bxW=bxW, wraps=wr)


def twist_tq(B, seed=3):
    rng = np.random.default_rng(seed)
    st = dict(om=None, k=-1, nz=np.zeros(B), word=np.zeros(B), af=np.zeros(B))
    g8 = 1.0 - np.exp(-2 * np.pi * 8.0 / 1000.0)                 # alpha low-passed at 8 Hz, as in the r79 fit
    J, b, Fc, k, c0 = (REACT[x] for x in ("J", "b", "Fc", "k", "c0"))
    sd, ac = REACT["res_std"], REACT["ac1"]

    def tq(t, th, om):
        kk = int(round(t * 1000))
        if st["om"] is None:
            st["om"] = om.copy()
        a = (om - st["om"]) * 1000.0
        st["om"] = om.copy()
        st["af"] = st["af"] + (a - st["af"]) * g8
        if kk % 10 == 0:                                       # the 0x18F word refreshes at 100 Hz
            st["nz"] = ac * st["nz"] + np.sqrt(1 - ac * ac) * sd * rng.normal(size=B)
            st["word"] = J * st["af"] + b * om + Fc * np.tanh(om / 2.0) + k * th + c0 + st["nz"]
        return st["word"]
    return tq


def run_scn(args):
    name, cand_set = args
    cands = CANDS if cand_set == "main" else CANDS_C8
    t0 = time.time()
    base = {"hardT": "hard", "stT": "st", "thT": "th"}.get(name, name)
    out = {}
    MEMB = ("nominal", "bc", "F_hi", "b_lo*J_hi")
    cols = [dict(cand=c, member=mb, v=v, alat=a) for mb in MEMB for v in SPEEDS
            for a in ((1.0, 2.5) if (base == "th" and v >= 8) else (0.0,)) for c in cands]
    scn, meta = ST.scenario(base, cols)
    if name in ("hardT", "stT", "thT"):
        scn.tq = twist_tq(len(cols))
        scn.dur = min(scn.dur, 8.0)
    orig = ST.CandLane
    ST.CandLane = D1Lane
    try:
        r = ST.run(cols, scn)
    finally:
        ST.CandLane = orig
    m = ST.metrics(base, meta, r, cols)
    lane = D1Lane.LAST
    om = r["om"].astype(float)
    nT = om.shape[0]
    w = slice(min(1500, nT // 4), nT)
    m["r48"] = np.sqrt(np.mean(ST._bp(om, 4.0, 8.0)[w] ** 2, 0))
    m["hand_duty"] = lane.hf / nT
    m["hand_tog_per_s"] = lane.htog / (nT / 1000.0)
    m["a3_duty"] = lane.a3n / nT
    m["a3_tog_per_s"] = lane.a3tog / (nT / 1000.0)
    m["slips_all"] = ST.NS.slips(r["th"][w].astype(float), om[w]).astype(float)
    for j, c in enumerate(cols):
        key = (c["cand"].id, c["member"], c["v"], c.get("alat", 0.0))
        out[key] = {kk: float(np.asarray(vv)[j]) for kk, vv in m.items()
                    if isinstance(vv, np.ndarray) and vv.shape == (len(cols),)}
    return name, cand_set, out, time.time() - t0


SPEEDS = (3.1, 5.0, 8.0, 11.9, 17.0, 26.9)
SCNS = ("ov_lt511", "ov_lt1000", "cs", "st", "hard", "th", "s10_02", "hardT", "stT", "thT", "db")
KEYS = {"ov_lt400": ("lurch", "droop"), "ov_lt511": ("lurch", "droop"), "ov_lt1000": ("lurch", "droop"),
        "ov_fm2400": ("lurch", "droop"), "cs": ("lurch", "droop"), "eng": ("droop", "ovs"),
        "st": ("ovs_pct", "settle", "slips"), "hard": ("hard_ratio", "ovs", "hold"), "th": ("hold", "ovs", "slips"),
        "s10_02": ("gain", "phase", "dj"), "db": ("lag", "stuck_pct"), "tmo": ("exc", "T_after"),
        "sen": ("T_50ms", "exc"), "dis": ("exc", "T_150ms"),
        "hardT": ("hard_ratio", "ovs", "r48", "hand_duty", "hand_tog_per_s", "a3_duty", "a3_tog_per_s", "slips_all"),
        "stT": ("ovs_pct", "settle", "r48", "hand_duty", "hand_tog_per_s", "a3_duty", "a3_tog_per_s", "slips_all"),
        "thT": ("ovs", "r48", "hand_duty", "hand_tog_per_s", "a3_duty", "a3_tog_per_s", "slips_all")}


def control():
    """D1Lane with asym off and V298's switches == CandLane, bit for bit (one scenario, two members, 3 speeds)."""
    c0 = mk("V298", 512, 300, False, ST.ARB_A3)
    cols = [dict(cand=c0, member=m, v=v) for m in ("nominal", "b_lo*J_hi") for v in (3.1, 11.9, 26.9)]
    scn, meta = ST.scenario("ov_lt511", cols)
    rA = ST.run(cols, scn)
    orig = ST.CandLane
    ST.CandLane = D1Lane
    try:
        rB = ST.run(cols, scn)
    finally:
        ST.CandLane = orig
    return float(np.abs(rA["th"] - rB["th"]).max()), int(np.abs(rA["T"].astype(int) - rB["T"].astype(int)).max())


if __name__ == "__main__":
    T0 = time.time()
    o = HERE / "out"
    if len(sys.argv) > 1 and sys.argv[1] == "control":
        dth, dT = control()
        assert dth == 0.0 and dT == 0, (dth, dT)
        msg = (f"CONTROL D1Lane(asym off, V298 switches) == score_time.CandLane: max |dth| {dth:.1e}, |dT| {dT}  "
               f"({time.time() - T0:.1f} s)")
        (o / "d1_time_control.txt").write_text(msg, encoding="utf-8")
        print(msg)
        sys.exit(0)
    with Pool(len(SCNS)) as pool:
        RR = pool.map(run_scn, [(s_, "main") for s_ in SCNS])
    ids = [c.id for c in CANDS]
    lines = ["worst over members (nominal, bc, F_hi, b_lo*J_hi) at each speed; cells " + " / ".join(ids)]
    js = {}
    for name, cs_, out, wt in RR:
        lines.append(f"-- {name} ({wt:.1f} s) --")
        for key in KEYS[name]:
            how = min if key in ("hold", "gain") else max
            row = []
            for v in SPEEDS:
                vals = []
                for cid in ids:
                    xs = [ov[key] for (c, mbr, vv, a_), ov in out.items() if c == cid and vv == v and key in ov]
                    vals.append(how(xs) if xs else float("nan"))
                row.append("/".join("%.2f" % x for x in vals))
                js[f"{name}|{key}|{v}"] = vals
            lines.append(f"   {key:15s} " + "  ".join(f"{v:>4}: {r_}" for v, r_ in zip(SPEEDS, row)))
    lines.append(f"wall {time.time() - T0:.1f} s")
    (o / "d1_time.txt").write_text(chr(10).join(lines), encoding="utf-8")
    (o / "d1_time.json").write_text(json.dumps(js), encoding="utf-8")
    print(chr(10).join(lines))
