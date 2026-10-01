# -*- coding: utf-8 -*-
"""c1_selftest.py -- the C1 mirror's controls (EVIDENCE when it prints 0 mismatches):
  1. LaneC1 with the cave OFF and no I policy == harness_time's ORIGINAL LaneVec (A2 guard) on the same row, tick for
     tick (T and I), random inputs incl. skips and driver torque (so the fade is exercised).
  2. LaneC1F (fric_lib adapter) with C0's table, 450/199 and the bleed == the friction refuter's fric_lib.LaneC0 (the C0
     listing's arithmetic), tick for tick.
  3. The freeze path: Honda's exc code 0x29D7E..0x29D9A as DECODED (Ghidra dry-run, this session: cmp r10,r6 ; mov 0,r9 ;
     ble ; ld.hu DB,r9 ; subr r6,r9 ; br ; ld.hu DB,r13 ; subr r0,r13 ; cmp r13,r6 ; bge ; ld.hu DB,r9 ; add r6,r9)
     emulated register by register with r6 = 0 (the cave's FRZ return) gives exc = 0 for every DB in 0..65535, and with
     r6 = e5 equals the mirror's dead-zone formula, over random e5.
  4. The e5 quantiser: +1 / -1 angle LSB of error -> e5 at every speed 0..35 m/s, C0 vs C1 (the refuter's F2 defect).
  5. The C1 table walk vs the exact real LERP over every gp-0x6a5e count 0..65535; the knots; G monotone; walk bounds.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib as C  # noqa: E402
import harness_time as HT  # noqa: E402

ORIG_LANEVEC = HT.LaneVec


def check1(n=40000, seed=3):
    rng = np.random.default_rng(seed)
    row = C.c1_row(C.make_table(C.C0_KNOTS_X2), "ctl", kp_base=450, ki_base=199, kd=16, db=0, icl=4096, cave=False,
                   pol="none", rampfrz=False, thr=0)
    cal = HT.base_cal()
    a = ORIG_LANEVEC(cal, HT.Cfg([row]))
    b = C.LaneC1(cal, HT.Cfg([row]))
    ang = rate = tq = 0
    raw = 0
    mism = 0
    for t in range(n):
        ang = int(np.clip(ang + rng.integers(-40, 41), -6000, 6000))
        rate = int(np.clip(rate + rng.integers(-30, 31), -3000, 3000))
        if t % 10 == 0:
            raw = int(rng.integers(-4000, 4000))
        tq = int(np.clip(tq + rng.integers(-100, 101), -3000, 3000))
        sk = (t // 500) % 7 == 3
        ramp, req = (0, 0) if sk else (0x8000, 1)
        cmd = int(np.clip(-(raw << 2), -0x4000, 0x4000))
        spd = int(rng.integers(0, 8000))
        Ta = a.tick(ang, rate, cmd, tq, 0, spd, ramp, 1, req)
        Tb = b.tick(ang, rate, cmd, tq, 0, spd, ramp, 1, req)
        if int(Ta[0]) != int(Tb[0]) or int(a.log["I"][0]) != int(b.log["I"][0]):
            mism += 1
    return mism


def check2(n=40000, seed=4):
    import fric_lib as F0
    rng = np.random.default_rng(seed)
    a = F0.LaneC0(1)                                          # the refuter's C0 lane (C0 listing arithmetic)
    b = C.LaneC1F(1, kp=450, ki=199, kd=16, icl=4096, db=0,
                  cols=[dict(tbl=C.C0_TABLE, pol="bleed", bleed_thr=1024, bleed_sh=6, rampfrz=False, thr=0)])
    ang = rate = tq = 0
    raw = 0
    mism = 0
    for t in range(n):
        ang = int(np.clip(ang + rng.integers(-40, 41), -6000, 6000))
        rate = int(np.clip(rate + rng.integers(-30, 31), -3000, 3000))
        if t % 10 == 0:
            raw = int(rng.integers(-4000, 4000))
        tq = int(np.clip(tq + rng.integers(-150, 151), -3000, 3000))
        sk = (t // 500) % 7 == 3
        ramp, req = (0, 0) if sk else (0x8000, 1)
        cmd = int(np.clip(-(raw << 2), -0x4000, 0x4000))
        spd = int(rng.integers(0, 8000))
        Ta = a.tick(ang, rate, cmd, tq, spd, ramp, 1, req)
        Tb = b.tick(ang, rate, cmd, tq, spd, ramp, 1, req)
        if int(Ta[0]) != int(Tb[0]) or int(a.log["I"][0]) != int(b.log["I"][0]):
            mism += 1
    return mism


def honda_exc(r6, DB):
    """0x29D7E..0x29D9A, register by register (DB = the u16 cal at tp+0x72E4; r10 holds the same value)."""
    r10 = DB
    r9 = 0                                          # 0x29D80 mov 0,r9
    if not (r6 <= r10):                             # 0x29D7E cmp r10,r6 ; 0x29D82 ble 0x29D8C  (signed)
        return r6 - DB                              # 0x29D84 ld.hu DB,r9 ; 0x29D88 subr r6,r9 (r9 = r6 - r9)
    r13 = -DB                                       # 0x29D8C ld.hu DB,r13 ; 0x29D90 subr r0,r13
    if r6 >= r13:                                   # 0x29D92 cmp r13,r6 ; 0x29D94 bge 0x29D9C
        return r9
    return DB + r6                                  # 0x29D96 ld.hu DB,r9 ; 0x29D9A add r6,r9


def check3(seed=5):
    rng = np.random.default_rng(seed)
    bad_frz = sum(1 for DB in list(range(0, 70)) + list(rng.integers(0, 65536, 2000)) if honda_exc(0, int(DB)) != 0)
    bad_mirror = 0
    for _ in range(20000):
        e5 = int(rng.integers(-200000, 200000)) if rng.random() < 0.5 else int(rng.integers(-20, 20))
        DB = int(rng.choice([0, 1, 4, int(rng.integers(0, 65536))]))
        mirror = e5 - DB if e5 > DB else (e5 + DB if e5 < -DB else 0)
        if honda_exc(e5, DB) != mirror:
            bad_mirror += 1
    return bad_frz, bad_mirror


def check4(tbl):
    out = []
    for v in np.arange(0.0, 35.01, 0.5):
        spd = C.spd_counts(v)
        g0, g1 = C.cave_G(spd, C.C0_TABLE), C.cave_G(spd, tbl)
        e = []
        for G in (g0, g1):
            for lsb in (+1, -1):
                E = 16 * lsb
                Ep = int(C.LM.s32(E * G)) >> 8
                e.append(Ep >> 5)
        out.append((v, g0, g1, e))
    return out


def check5(tbl):
    X = [r[0] for r in tbl[:-1]]
    Y = [r[1] for r in tbl[:-1]]
    g = C.glut(tbl)
    exact = np.interp(np.arange(65536), X, Y)
    d = g - exact
    mono = bool(np.all(np.diff(g) >= 0))
    return float(d.min()), float(d.max()), mono, [int(g[x]) for x in X], int(g[0]), int(g[65535])


if __name__ == "__main__":
    tbl = C.c1_table()
    print("CHECK 1  LaneC1(cave off, no I policy) vs harness_time ORIGINAL LaneVec, 40000 random ticks: %d mismatches"
          % check1())
    print("CHECK 2  LaneC1F(C0 table, 450/199, bleed 1024) vs fric_lib.LaneC0 (C0 listing), 40000 ticks: %d mismatches"
          % check2())
    bf, bm = check3()
    print("CHECK 3  Honda exc with r6 = 0 (freeze): nonzero for %d of 2070 DB values ; Honda exc vs mirror dead-zone "
          "formula: %d mismatches of 20000" % (bf, bm))
    print("CHECK 4  e5 for a +1 / -1 LSB error   (C0: G, e5+, e5-  |  C1: G, e5+, e5-)")
    for v, g0, g1, e in check4(tbl):
        if v in (0.0, 3.0, 5.0, 8.0, 10.0, 11.5, 12.0, 12.5, 15.0, 19.0, 26.0, 30.0):
            print(f"         v {v:5.1f}  C0 G {g0:5d} e5 {e[0]:+d}/{e[1]:+d}   |  C1 G {g1:5d} e5 {e[2]:+d}/{e[3]:+d}")
    blind = [v for v, g0, g1, e in check4(tbl) if e[2] == 0]
    print("         C1 speeds with e5 = 0 for +1 LSB: %s" % (blind or "NONE"))
    lo, hi, mono, gk, g0, g65535 = check5(tbl)
    print("CHECK 5  C1 walk - exact LERP over 0..65535: min %.2f max %.2f ; monotone %s ; G at knots %s ; G(0) %d "
          "G(65535) %d" % (lo, hi, mono, gk, g0, g65535))
