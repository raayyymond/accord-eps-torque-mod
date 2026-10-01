# -*- coding: utf-8 -*-
r"""h_time.py -- TIME-DOMAIN gates for designer H's whole-loop-reconcile, the F1/F4 resolution:
  (G1) TURN-HOLD by lateral acceleration (refuter F1-nonlinear): the integrator-clamp ceiling vs the spring load.
  (G2) OVERRIDE-RELEASE LURCH (refuter F4 / V283 class): a wound I dumping on release.
  (G3) DWELL-THEN-JUMP on small corrections at the 10-12.5 m/s gain dip (refuter F2-nonlinear).
It tests the coupled F1<->F4 lever (raise ICL to hold the load, BLEED+FREEZE the I on driver torque so the raised
clamp does not lurch) that neither C1 (freeze only) nor C0 (bleed only) carried.

REUSE, do not fork: the plant is harness_time.PlantVec (Karnopp friction, 10 kHz substeps) on the panel's members
(ds_time.member for nominal/J_hi/b_lo; friction variants built here as the scorers do).  The lane is the C1 integer
lane c1_lib.LaneC1F, SUBCLASSED here (LaneHB/LaneHA) to add ONE thing the shared core lacks: a COMBINED freeze+bleed
I policy (the shared cave() does freeze XOR bleed by `pol`).  The subclass overrides cave() only; every other line is
LaneC1F's byte-exact arithmetic.  WHAT I CHANGED is exactly: cave() now, when |gp-0x4f68| > thr, BOTH sets e5:=0
(freeze, Honda's exc=0 return) AND drains I8 -= I8>>bsh (bleed); ramp-not-full still freezes only.

usage:  python h_time.py            # the three gates for H-A, H-B at ICL {4096, 6000, 7500}, writes h_time_out.txt
"""
from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np

os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
for _p in (str(AL / "c1"), str(AL / "panel" / "D-structure"), str(AL.parent / "v295" / "plant"), str(AL)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np                                       # noqa: E402,F811
import harness_time as HT                                # noqa: E402
import c1_lib as C                                       # noqa: E402
import ds_time as DT                                     # noqa: E402
from c1_lib import _C1Core, s32, s32g, s16               # noqa: E402

OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(str(s))


WB, SR = 2.83, 16.0          # wheelbase m, steer ratio (refuter's conversion: 2.0 m/s^2 @17 m/s -> 17.95 deg)


def alat_to_deg(a_lat, v):
    return float(np.degrees(a_lat * WB * SR / v ** 2))


# ---------------------------------------------------------------------------------------------------------------------
# the COMBINED freeze+bleed cave (the only override of the shared LaneC1F)
# ---------------------------------------------------------------------------------------------------------------------
class _FBCore(_C1Core):
    def cave(self, E, tq, ramp, speed):
        G = self.gl[np.arange(self.B), speed & 0xFFFF]
        Ep = np.where(self.cave_on, s32g(E * G) >> 8, E)
        atq = np.minimum(np.abs(tq), 0xFFFF)
        hand = (self.thr > 0) & (atq > self.thr)                    # driver torque above the freeze/bleed threshold
        rampnf = self.rampfrz & ((ramp & 0x8000) == 0)
        frz = self.cave_on & (hand | rampnf)                        # FREEZE accumulation (hand OR ramp-in)
        bl = self.cave_on & hand & (self.bsh > 0)                   # BLEED the wound I only on a hand (not on ramp-in)
        self.I8 = np.where(bl, s32(self.I8 - (self.I8 >> self.bsh)), self.I8)
        return Ep, frz, G


class LaneHB(_FBCore, type("_", (), {})):
    """H-B: held gp-0x6a56 D, corrected-frame; the LaneC1F body with the combined cave."""
    def __init__(self, B, **kw):
        _hb_init(self, B, **kw)

    tick = C.LaneC1F.tick


class LaneHA(_FBCore, type("_", (), {})):
    """H-A: fresh-rate D in the SAME frame as P/I (scored here with the held-rate stand-in on the motor-frame
    feedback, since the Karnopp plant is single-mass -- the fresh vs held difference is a >8 Hz effect the
    frequency gate covers; the time gates F1/F4 are set by P and I, which are identical in H-A and H-B)."""
    def __init__(self, B, **kw):
        _hb_init(self, B, **kw)

    tick = C.LaneC1F.tick


def _hb_init(self, B, cal=None, kp=112, kd=23, ki=56, icl=6000, db=0, tbl=None, thr=512, bsh=7):
    self.c = HT.base_cal() if cal is None else cal
    self.B = B
    f = lambda v: np.broadcast_to(np.asarray(v, np.int64), (B,)).copy()  # noqa: E731
    self.kp, self.kd, self.ki, self.icl, self.db = f(kp), f(kd), f(ki), f(icl), f(db)
    tbl = tbl if tbl is not None else [(714, 1187, 896), (1843, 1434, -6388), (2304, 715, -1779), (2707, 540, 2489),
                                       (3571, 1065, 2781), (4032, 1378, 1297), (6198, 2064, 0), (0xFFFF, 2064, 0)]
    rows = [dict(cave=True, tbl=tbl, thr=thr, bleed_sh=bsh, rampfrz=True, pol="freeze") for _ in range(B)]
    self.setup_cave(B, rows)
    z = lambda: np.zeros(B, np.int64)  # noqa: E731
    self.s, self.lane_ok, self.I8, self.Eprev, self.olag, self.Tprev = z(), z(), z(), z(), z(), z()
    self.log = {}


# ---------------------------------------------------------------------------------------------------------------------
# plant members (reuse ds_time.member; build friction variants as the panel scorers do)
# ---------------------------------------------------------------------------------------------------------------------
def member(name):
    if name == "nominal":
        return DT.member("nominal")
    if name == "J_hi":
        return DT.member("J_hi")
    if name == "b_lo*J_hi":
        m = DT.member("J_hi")
        kw = {k: getattr(m, k) for k in m.__dataclass_fields__}
        kw["name"] = "b_lo*J_hi"
        kw["b"] = np.asarray(kw["b"], float).copy()
        return _Bscale(**kw)
    if name == "F_hi":                                   # nominal, friction x2
        m = DT.member("nominal")
        kw = {k: getattr(m, k) for k in m.__dataclass_fields__}
        kw["name"] = "F_hi"
        kw["Fc"] = np.asarray(kw["Fc"], float) * 2.0
        kw["Fs"] = np.asarray(kw["Fs"], float) * 2.0
        return type(m)(**kw)
    if name == "bc":                                     # b_lo damping + Coulomb x2 at >=10 (x1.3 at 8), the friction bias
        m = DT.member("nominal")
        kw = {k: getattr(m, k) for k in m.__dataclass_fields__}
        kw["name"] = "bc"
        return _Bc(**kw)
    raise ValueError(name)


from v294_plant import PlantFamilyMember  # noqa: E402


class _Bscale(PlantFamilyMember):
    def arrays_at(self, v):
        a = super().arrays_at(v)
        vv = np.asarray(v, float)
        a["b"] = a["b"] * np.where(vv >= 10.0, 1 / 1.8, 0.7)
        return a


class _Bc(PlantFamilyMember):
    def arrays_at(self, v):
        a = super().arrays_at(v)
        vv = np.asarray(v, float)
        a["b"] = a["b"] * np.where(vv >= 10.0, 1 / 1.8, 0.7)
        a["Fc"] = a["Fc"] * np.where(vv >= 10.0, 2.0, np.where(vv >= 8.0, 1.3, 1.0))
        a["Fs"] = a["Fs"] * np.where(vv >= 10.0, 2.0, np.where(vv >= 8.0, 1.3, 1.0))
        return a


# ---------------------------------------------------------------------------------------------------------------------
# the runner: one column, one scenario (ref angle + optional driver hand), 1 kHz; gp-0x6a00 held at 100 Hz AFTER lane
# ---------------------------------------------------------------------------------------------------------------------
def simulate(Lane, mem_name, v, ref_fn, dur, icl, thr=512, bsh=7, tbl=None, hand=None, kd=23, aged=False):
    mem = member(mem_name)
    lane = Lane(1, icl=icl, thr=thr, bsh=bsh, tbl=tbl, kd=kd)
    pl = HT.PlantVec(mem, v, 1)
    n = int(round(dur * 1000))
    spd = int(round(v * 3.6 * 64))
    th = np.zeros(n)
    Trec = np.zeros(n)
    sprec = np.zeros(n)
    held_th = HT.q_angle(pl.th)
    held_x = np.zeros(1, np.int64)
    fifo = []
    cmd = np.zeros(1, np.int64)
    for i in range(n):
        t = i * 1e-3
        if i % 10 == 0:
            thc = float(ref_fn(t))
            raw = int(s16(np.array([-int(round(10.0 * thc))]))[0])
            cmd = np.clip(np.array([s32(-(s16(np.array([raw]))[0] << 2))]), -0x4000, 0x4000)
        # driver hand torque word fed to the lane (gp-0x4f68 magnitude), + hand mechanics on the plant
        tqw, hh = 0, None
        if hand is not None:
            tqw, hh = hand(t, pl.th[0])
        # PlantVec state is in DEGREES; gp-0x6a56 = 8 counts per deg/s, x and dtheta/dt share sign (trace sec 3.4)
        rate_counts = int(round(8.0 * pl.om[0]))
        # LaneC1F.tick signature: (angle, rate, cmd, tq, speed, ramp, act, req, i6830)
        T = int(lane.tick(held_th, np.array([rate_counts]), cmd, np.array([tqw]), np.array([spd]),
                          np.array([0x8000]), np.array([1]), np.array([1]), np.array([0]))[0])
        Trec[i] = T
        sprec[i] = cmd[0] / 40.0
        Tapp = pl.push_T(np.array([float(T)]))
        pl.step(-Tapp, hand=hh)
        th[i] = pl.th[0]
        q_now = HT.q_angle(pl.th)
        if aged:
            fifo.append(q_now.copy())
            if len(fifo) > 11:
                fifo.pop(0)
        if i % 10 == 4:
            held_th = fifo[0] if (aged and fifo) else q_now
    return dict(th=th, T=Trec, sp=sprec)


# ---------------------------------------------------------------------------------------------------------------------
# G1 turn-hold
# ---------------------------------------------------------------------------------------------------------------------
def turn_hold(Lane, icl, kd=23, tbl=None, members=("nominal", "b_lo*J_hi"), speeds=(13, 15, 17, 19, 22),
              alats=(1.0, 1.5, 2.0)):
    pr(f"\n-- G1 turn-hold (ratio over last 2 s; goal >= 0.90)  ICL={icl} Kd={kd} --")
    hdr = "member       a_lat " + " ".join(f"{s:>5}" for s in speeds)
    pr(hdr)
    for mem in members:
        for al in alats:
            row = []
            for v in speeds:
                Adeg = alat_to_deg(al, v)
                ref = lambda t, A=Adeg: np.interp(t, [0, 0.5, 2.0, 99], [0, 0, A, A])
                r = simulate(Lane, mem, v, ref, 11.0, icl, kd=kd, tbl=tbl)
                th = r["th"]
                ratio = th[-2000:].mean() / Adeg
                row.append(ratio)
            pr(f"{mem:12s} {al:4.1f}  " + " ".join(f"{x:5.2f}" for x in row))


# ---------------------------------------------------------------------------------------------------------------------
# G2 release lurch: hold a curve, driver grabs (hand) with word W for 2 s, releases; max overshoot after release
# ---------------------------------------------------------------------------------------------------------------------
def release_lurch(Lane, icl, kd=23, tbl=None, members=("nominal", "b_lo*J_hi"), speeds=(8, 10, 11.75),
                  words=(400, 2048), bsh=7, thr=512):
    pr(f"\n-- G2 override-release lurch (deg past the setpoint after release; rev2-A bar ~10.6, rev2-B 8.0)  "
       f"ICL={icl} Kd={kd} thr={thr} bsh={bsh} --")
    pr("member       word " + " ".join(f"{s:>6}" for s in speeds))
    for mem in members:
        for W in words:
            row = []
            for v in speeds:
                Adeg = alat_to_deg(1.5, v)
                tpush, trel = 3.0, 5.0

                def ref(t, A=Adeg):
                    return np.interp(t, [0, 0.5, 2.0, 99], [0, 0, A, A])

                def hand(t, thp, A=Adeg, W=W, tpush=tpush, trel=trel):
                    if tpush <= t < trel:
                        # a firm-ish hand holding the wheel ~0.6*A (resisting), word W fed to the I bleed
                        thg = np.radians(0.6 * A)
                        return W, (120.0, 8.0, thg)
                    return 0, None

                r = simulate(Lane, mem, v, ref, 8.0, icl, kd=kd, tbl=tbl, thr=thr, bsh=bsh, hand=hand)
                th = r["th"]
                sp = r["sp"]
                post = (np.arange(len(th)) * 1e-3) >= trel
                lurch = float(np.max((th[post] - sp[post]) * np.sign(Adeg)))
                row.append(lurch)
            pr(f"{mem:12s} {W:4d}  " + " ".join(f"{x:6.2f}" for x in row))


# ---------------------------------------------------------------------------------------------------------------------
# G3 dwell-then-jump on small corrections at the gain dip
# ---------------------------------------------------------------------------------------------------------------------
def dwell_jump(th_deg, dt=1e-3):
    """count dwell(>=120 ms still)-then-jump(>=0.15 deg in <=80 ms) events; return (count, max_jump)."""
    om = np.gradient(th_deg) / dt
    still = np.abs(om) < 2.0
    n = len(th_deg)
    cnt, mx = 0, 0.0
    i = 0
    while i < n - 80:
        if still[i:i + 120].all() if i + 120 < n else False:
            j = i + 120
            while j < n and still[j]:
                j += 1
            k = min(j + 80, n - 1)
            jump = abs(th_deg[k] - th_deg[j]) if j < n else 0.0
            if jump >= 0.15:
                cnt += 1
                mx = max(mx, jump)
            i = k
        else:
            i += 1
    return cnt, mx


def dwell_gate(Lane, icl, kd=23, tbl=None, members=("bc", "F_hi"), speeds=(9, 10, 11, 11.75, 12.5),
               amp=0.5, freq=0.2):
    pr(f"\n-- G3 dwell-then-jump, +-{amp} deg @ {freq} Hz (events / max-jump deg over 30 s)  ICL={icl} Kd={kd} --")
    pr("member       " + " ".join(f"{s:>9}" for s in speeds))
    for mem in members:
        row = []
        for v in speeds:
            ref = lambda t: amp * np.sin(2 * np.pi * freq * t)
            r = simulate(Lane, mem, v, ref, 30.0, icl, kd=kd, tbl=tbl)
            c, mx = dwell_jump(r["th"])
            row.append(f"{c:2d}/{mx:.2f}")
        pr(f"{mem:12s} " + " ".join(f"{x:>9}" for x in row))


def main():
    pr("WHOLE-LOOP-RECONCILE (designer H) -- TIME gates (F1 turn-hold, F4 lurch, F4 dwell-then-jump)")
    pr("plant = PlantVec Karnopp friction on the r71b family; lane = LaneC1F + combined freeze+bleed (subclass)")
    for icl in (4096, 6000, 7500):
        pr(f"\n################ ICL = {icl} (contributes ~{icl*0.16016:.0f} T to the hold at the clamp) ################")
        turn_hold(LaneHB, icl)
        if icl in (4096, 7500):
            release_lurch(LaneHB, icl, thr=512, bsh=7)
    pr("\n################ dwell-then-jump at the gain dip (ICL 6000) ################")
    dwell_gate(LaneHB, 6000)
    pr("\n################ release lurch: bleed-threshold sensitivity (ICL 7500, b_lo*J_hi) ################")
    for thr, bsh in ((512, 7), (256, 7), (256, 5), (128, 5)):
        release_lurch(LaneHB, 7500, thr=thr, bsh=bsh, members=("b_lo*J_hi",), speeds=(10,), words=(400, 2048))
    (HERE / "h_time_out.txt").write_text("\n".join(OUT), encoding="utf-8")
    pr("\nwrote h_time_out.txt")


if __name__ == "__main__":
    main()
