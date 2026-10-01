"""reconcile: run the TIME harness (harness_time.py, unmodified) on the FREQ harness's E-gain schedules, with the
E-gain stage emulated EXACTLY as a cave would compute it:  E' = (E * G(v)) >> 8 after 0x29D78, G = Honda-style
integer LERP over gp-0x6a5e (Q8), and an optional driver-torque I bleed / I freeze.  Everything else is LaneVec's
byte-exact arithmetic (copied below with the single insertion marked  # >>> CAVE).  Analysis only."""
import sys, os, json, time
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1"); os.environ.setdefault("OMP_NUM_THREADS", "1")
from pathlib import Path
HERE = Path(r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\analysis-2020accord\studies\angle_loop")
sys.path.insert(0, str(HERE))
import numpy as np
import harness_time as HT
from harness_time import s32, s32g, s16, vlerp, LM

OUT = Path(r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\_scratch\angle_loop\reconcile")


class LaneCave(HT.LaneVec):
    """LaneVec + the E-gain cave (and optional I bleed).  Row fields: gX, gY (Q8 gain vs gp-0x6a5e), bleed_thr
    (|gp-0x4f60| threshold, internal counts; 0 = off), bleed_sh (I_stored -= I_stored >> sh per tick when above)."""

    def __init__(self, cal, cfg):
        super().__init__(cal, cfg)
        rows = cfg.rows
        self.has_g = np.array([("gX" in r) for r in rows])
        nX = max(len(r.get("gX", (0, 1))) for r in rows)
        def pad(t, n):
            t = list(t)
            return t + [t[-1]] * (n - len(t))
        self.gX = np.array([pad(r.get("gX", (0, 1)), nX) for r in rows], np.int64)
        # pad X strictly increasing for vlerp: extend with +1 steps
        for i in range(self.gX.shape[0]):
            for j in range(1, nX):
                if self.gX[i, j] <= self.gX[i, j - 1]:
                    self.gX[i, j] = self.gX[i, j - 1] + 1
        self.gY = np.array([pad(r.get("gY", (256, 256)), nX) for r in rows], np.int64)
        self.bthr = np.array([r.get("bleed_thr", 0) for r in rows], np.int64)
        self.bsh = np.array([r.get("bleed_sh", 6) for r in rows], np.int64)
        self.freeze = np.array([bool(r.get("freeze", False)) for r in rows])

    def tick(self, angle, rate, cmd, tq, i6830, speed, ramp, act, req, pol=-1):
        c, g = self.c, self.cfg
        B = g.B
        full = lambda v: np.broadcast_to(np.asarray(v, np.int64), (B,)).copy()  # noqa: E731
        uniform = all(np.ndim(q) == 0 for q in (cmd, tq, i6830, speed))
        if uniform:
            cmd_s, tq_s, i6830_s, spd_s = int(cmd), int(tq), int(i6830), int(speed)
        angle, rate, cmd, tq, i6830, speed = map(full, (angle, rate, cmd, tq, i6830, speed))
        ramp, act, req = full(ramp), full(act), full(req)
        x = s16(angle)
        valid = (x >= -12000) & (x <= 12000)
        s_old = np.where(self.lane_ok == 1, self.s, 0)
        bx = s32g(x * (c["b"] & 0xFFFF))
        as_ = s32g(int(LM.s16(c["a"])) * s_old)
        s_new = s32((as_ >> 10) + (bx >> 10))
        r26 = s32(s_old + s_new)
        C = c["C"] & 0xFFFF
        r26 = np.clip(r26, -C, C)
        self.s = np.where(valid, s_new, self.s)
        r26 = np.where(valid, r26, 0)
        self.lane_ok = np.where(valid, 1, 2)
        run = valid & np.where(g.guard_and, (ramp != 0) & (req == 1), (ramp != 0) | ((~g.e6) & (req == 1)))
        if uniform:
            idx_s, _, _ = LM.setpoint_chain(cmd_s, c, tq=tq_s, i6830=i6830_s, speed=spd_s)
            idx = np.full(B, idx_s, np.int64)
            i682f = np.full(B, min(abs(tq_s >> 5), 255), np.int64)
        else:
            r13 = s16(cmd)
            LIM = vlerp(*c["lim"], speed) & 0xFFFF
            r22 = np.clip(r13, -LIM, LIM)
            i682f = np.minimum(np.abs(tq >> 5), 255)
            same = (r22 < 0) == (tq < 0)
            taper = np.where(same, vlerp(*c["tap_same"], i682f), vlerp(*c["tap_opp"], i682f))
            spF = vlerp(*c["spF"], i6830)
            Gt = (spF * taper) & 0xFFFF
            v = s32(Gt * r22) >> 16
            v = np.where(i682f > c["cut"], 0, v)
            v = v >> 6
            v = np.clip(v, -c["idx_lo"], c["idx_hi"])
            idx = np.abs(v)
        sp = s16(cmd)
        E = s32g((sp << 2) - r26)
        # >>> CAVE: E' = (E * G(speed)) >> 8 ; optional I bleed / freeze on |driver torque| ------------------------
        G = vlerp(self.gX, self.gY, speed)
        E = np.where(self.has_g, s32g(E * G) >> 8, E)
        atq = np.abs(tq)
        over = (self.bthr > 0) & (atq > self.bthr)
        I8b = np.where(over & ~self.freeze, s32(self.I8 - ((self.I8 >> 3) >> self.bsh << 3)), self.I8)
        self.I8 = I8b
        # <<< CAVE ---------------------------------------------------------------------------------------------
        e5 = E >> 5
        DB = g.DB & 0xFFFF
        exc = np.where(e5 > DB, e5 - DB, np.where(e5 < -DB, e5 + DB, 0))
        exc = np.where(over & self.freeze, 0, exc)
        icl = ((g.ICL & 0xFFFF) << 10) >> 3
        inc = s32g(exc * (g.Ki & 0xFFFF)) >> 3
        I = np.clip(s32g((self.I8 >> 3) + inc), -icl, icl)
        I8_new = s32g(I << 3)
        key = np.where(g.key_speed, (speed >> 8) & 0xFF, idx)
        kp = vlerp(g.kpX, g.kpY, key & 0xFFFF) & 0xFFFF
        P = np.clip(s32g(E * kp) >> 8, -c["PCL"], c["PCL"])
        kd_l = vlerp(g.kdX, g.kdY, key & 0xFF)
        r27 = np.where((self.Eprev >= -768000) & (self.Eprev <= 768000), self.Eprev, E)
        kd = np.where(g.d_rate, s32(-(kd_l & 0xFFFF)), kd_l & 0xFFFF)
        r8 = np.where(g.d_rate, s16(rate), s32(E - r27))
        D = np.clip(s32g(kd * r8) >> 3, -g.DCL, g.DCL)
        S = s32g((I >> 7) + P + D)
        if uniform:
            f = ((LM.lerp(*c["fadeA"], i6830_s) * LM.lerp(*c["fadeB"], int(i682f[0]))) & 0xFFFF) >> 8
        else:
            f = ((vlerp(*c["fadeA"], i6830) * vlerp(*c["fadeB"], i682f)) & 0xFFFF) >> 8
        Sf = s32g(S * f) >> 8
        SCL = c["SCL"] & 0xFFFF
        Sc = np.where(Sf > SCL, LM.s16(c["SCL"]), np.where(Sf < -SCL, LM.s16(-SCL), s16(Sf)))
        Sc = np.where(run, Sc, 0)
        self.I8 = np.where(run, I8_new, 0)
        self.Eprev = np.where(run, E, 0x7FFFFFFF)
        t1 = s32g(Sc * (g.ob & 0xFFFF)) >> 10
        t2 = s32g(s16(g.oa) * self.olag) >> 10
        o_new = s32(t2 + t1)
        y = s32(self.olag + o_new) >> 5
        self.olag = o_new
        yr_pass = s16(s32g(y * ramp) >> 15)
        if c["g74a3"] == 1:
            dz = c["dz"]
            block = ((s16(y) <= dz) & (y >= -(dz & 0xFFFF))) | (s32g(y * self.Tprev) <= 0)
            yr = np.where((act == 0) & block, 0, yr_pass)
        else:
            yr = yr_pass
        k = int(LM.s32(LM.s16(pol) * LM.s16(c["fwd"])))
        r11 = s32g(yr * k) >> 15
        OCL = c["OCL"] & 0xFFFF
        T = np.where(r11 > OCL, LM.s16(c["OCL"]), np.where(r11 < -OCL, -OCL, r11))
        self.Tprev = yr
        self.log = dict(r26=r26, E=np.where(run, E, 0), I=np.where(run, I, 0), P=np.where(run, P, 0),
                        D=np.where(run, D, 0), Sc=Sc, y=y, yr=yr, idx=idx, kp=kp, run=run)
        return s16(T)


HT.LaneVec = LaneCave        # harness_time.run() looks LaneVec up at call time


def spd_counts(v):
    return int(round(v * 3.6 * 64))


SPEEDS = HT.SPEEDS
ROB = (637, 682, 730, 1178, 3070, 3520, 3520)
DES = (896, 960, 1028, 2335, 4628, 4628, 4628)


def egain_row(S, base, fi=0.3, kd=16, DB=4, ICL=10240, label="", guard_and=True, **kw):
    """S = per-speed Kp_eff; G = S/base in Q8 at the speed knots; Ki_base for PI corner fi at the base."""
    import math
    gX = tuple(spd_counts(v) for v in SPEEDS)
    gY = tuple(int(round(256.0 * s / base)) for s in S)
    Ki = int(round(2 * math.pi * fi * base / 7.8125))
    r = HT.row(base, Ki=Ki, ICL=ICL, DB=DB, Kd=kd, label=label)
    r.update(gX=gX, gY=gY, guard_and=guard_and, **kw)
    return r


def rekey_row(Ki=300, DB=1, ICL=10240, label="", guard_and=True):
    k = lambda v: spd_counts(v) >> 8  # noqa: E731
    r = HT.row(0, kpX=(k(3.0), k(8.0), k(12.5), k(19.0), k(26.0)), kpY=(637, 730, 1178, 3070, 3520),
               kdX=(k(3.0), k(12.5), k(19.0), k(26.0)), kdY=(28, 28, 24, 20), key="speed", Ki=Ki, ICL=ICL, DB=DB,
               label=label)
    r.update(guard_and=guard_and)
    return r


def cands():
    c = []
    c.append(egain_row(ROB, 637, label="ROBUST E-gain base637 Ki154 Kd16 DB4 ICL10240 A2"))
    c.append(egain_row(DES, 896, label="DESIGN E-gain base896 Ki216 Kd16 DB4 ICL10240 A2"))
    c.append(egain_row(ROB, 637, ICL=4096, label="ROBUST ICL4096 A2"))
    c.append(egain_row(ROB, 637, DB=1, label="ROBUST DB1 A2"))
    c.append(rekey_row(300, 1, label="REKEY-300 Kp(v)=ROBUST Kd(v) 28/28/24/20 Ki300 DB1 A2 (zero cave)"))
    c.append(rekey_row(300, 4, label="REKEY-300 DB4 A2 (zero cave)"))
    c.append(egain_row(ROB, 637, fi=0.4, label="ROBUST fI0.4 A2"))
    c.append(egain_row(ROB, 637, label="ROBUST + I-freeze |tq|>1024 A2", bleed_thr=1024, freeze=True))
    c.append(egain_row(ROB, 637, label="ROBUST + I-bleed |tq|>1024 tau64ms A2", bleed_thr=1024, bleed_sh=6))
    return c


MEMBERS_ROB = ("J_lo", "J_hi", "b_lo", "b_hi", "F_lo", "F_hi", "tau0", "tau6", "light_b", "ms_free", "J_hi2",
               "nominal+mode13Hz", "nominal+mode20Hz")


def main(which):
    rows = cands()
    if which == "nominal":
        jobs = [(nm, v, rows, "nominal", "ff", 0) for v in SPEEDS for nm in HT.SCENARIOS]
        res = HT.merge(HT.run_jobs(jobs, procs=6, tag="rec-nominal"))
        (OUT / "rec_time_nominal.json").write_text(json.dumps(dict(rows=rows, results=res)))
    elif which == "robust":
        jobs = [(nm, v, rows, m, "ff", 0) for m in MEMBERS_ROB for v in SPEEDS for nm in HT.SC_TRACK]
        res = HT.merge(HT.run_jobs(jobs, procs=6, tag="rec-robust"))
        (OUT / "rec_time_robust.json").write_text(json.dumps(dict(rows=rows, members=MEMBERS_ROB, results=res)))
    elif which == "pi":
        jobs = [(nm, v, rows, "nominal", "pi", 0) for v in SPEEDS for nm in HT.SC_TRACK]
        res = HT.merge(HT.run_jobs(jobs, procs=6, tag="rec-pi"))
        (OUT / "rec_time_pi.json").write_text(json.dumps(dict(rows=rows, results=res)))


if __name__ == "__main__":
    main(sys.argv[1])
