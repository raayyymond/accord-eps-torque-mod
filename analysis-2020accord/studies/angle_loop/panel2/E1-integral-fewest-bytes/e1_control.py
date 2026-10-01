# -*- coding: utf-8 -*-
r"""e1_control.py -- CONTROL: the E1 lane at the BASELINE policy (icl flat 4096, no reset, no bleed, kp 112) must
reproduce the refuter's controlled engine nl_sim.run bit for bit, so every E1 number below is anchored to the engine
the C2 refutation itself used.  Also: a positive control that the mirror's cave G-walk reproduces nl_cave.walk_G.
ANALYSIS ONLY."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e1_lane as E1
import nl_sim as NS
import nl_cave as NC

OUT = E1.KIT / "_scratch" / "angle_loop" / "E1-integral-fewest-bytes"
OUT.mkdir(parents=True, exist_ok=True)


def run_e1(cols, scn, policy=None, seed=11):
    """nl_sim.run, but the lane is E1Lane.  Copied from nl_sim.run with the single line lane=... changed, so the rest of
    the controlled loop (plant, sensors, fork, events) is byte-identical to the refuter's engine.  `policy` applies to all
    columns, OR each column may carry its own in cols[i]['pol']."""
    B = len(cols)
    impls = [c["impl"] for c in cols]
    vw = np.array([int(round(c["v"] * 3.6 * 64)) for c in cols], np.int64)
    aged = np.array([c.get("age", 0) == 10 for c in cols])
    pols = [c["pol"] for c in cols] if all("pol" in c for c in cols) else policy
    lane = E1.E1Lane(impls, vw, pols)
    pl = NS.Plant(cols)
    if scn.th0 is not None:
        pl.th = np.asarray(scn.th0, float).copy()
    rng = np.random.default_rng(seed)
    nT = int(round(scn.dur * 1000))
    th_r = np.zeros((nT, B), np.float32)
    om_r = np.zeros((nT, B), np.float32)
    T_r = np.zeros((nT, B), np.int16)
    sp_r = np.zeros((nT, B), np.int32)
    I_r = np.zeros((nT, B), np.int32)
    fz_r = np.zeros((nT, B), bool)
    wire = []
    held_th = np.floor(10 * pl.th + 0.5).astype(np.int64)
    held_x = np.zeros(B, np.int64)
    fifo = []
    st = np.zeros(B, np.int64)
    cmd = 4 * held_th
    mode = scn.mode0
    ramp = 0x8000 if mode == "engaged" else 0
    act = req = 1 if mode == "engaged" else 0
    ev = sorted(scn.events)
    ei = 0
    sen = False
    stopped = False
    for n in range(nT):
        t = n * 1e-3
        while ei < len(ev) and t >= ev[ei][0] - 1e-9:
            kind = ev[ei][1]
            if kind == "fault":
                sen, mode = True, "fault"
            elif kind == "stop":
                stopped = True
            elif kind == "dis":
                mode = "dis"
            elif kind == "latch":
                mode = "latch"
            elif kind in ("relatch", "engage"):
                mode = "relatch"
            ei += 1
        if mode == "engaged":
            ramp, act, req = 0x8000, 1, 1
        elif mode in ("fault", "dis"):
            ramp, act, req = max(0, ramp - 16), 0, (0xFF if mode == "fault" else 0)
        elif mode == "latch":
            ramp, act, req = max(0, ramp - 328), 0, 1
        elif mode == "relatch":
            ramp, act, req = min(0x8000, ramp + 33), 1, 1
        elif mode == "off":
            ramp, act, req = max(0, ramp - 16), 0, 0
        if n % 10 == 0 and not sen and not stopped:
            k6 = max(len(wire) - 6, 0)
            th_meas = wire[k6] / 10.0 if wire else pl.th.copy()
            if mode in ("dis", "off") or (scn.sp_meas_until is not None and t < scn.sp_meas_until):
                thc = th_meas
                cmd = np.clip(-(NS.s16(-np.floor(10.0 * thc + 0.5).astype(np.int64)) << 2), -0x4000, 0x4000)
            elif scn.sp_hold_from is not None and t >= scn.sp_hold_from:
                pass
            else:
                thc = np.asarray(scn.ref(t), float) * np.ones(B)
                raw = NS.s16(-np.floor(10.0 * thc + 0.5).astype(np.int64))
                cmd = np.clip(NS.s32(-(raw << 2)), -0x4000, 0x4000)
        cmd_in = np.full(B, NS.SENT, np.int64) if sen else cmd
        tq = np.zeros(B, np.int64) if scn.tq is None else np.round(np.asarray(scn.tq(t, pl.th, pl.om), float) *
                                                                   np.ones(B)).astype(np.int64)
        g4f50 = NS.s16(np.round(NS.ABE_PER * pl.om + rng.normal(0.0, NS.N4F50, B)).astype(np.int64))
        st = st + (((g4f50 * 1024 - st) * 37) >> 7)
        abe = NS.s16(st >> 10)
        T = lane.tick(held_th, held_x, abe, cmd_in, tq, ramp, act, req)
        q_now = np.floor(10.0 * pl.th + 0.5).astype(np.int64)
        x_now = np.clip(-((NS.s16(st >> 10) * 48 * 1159) >> 15), -12000, 12000)
        fifo.append((q_now, x_now))
        if len(fifo) > 11:
            fifo.pop(0)
        if n % 10 == 4:
            held_th = np.where(aged, fifo[0][0], q_now)
            held_x = np.where(aged, fifo[0][1], x_now)
            wire.append(q_now.copy())
        Tapp = pl.delay(T.astype(float))
        u = -Tapp + (np.asarray(scn.uext(t), float) if scn.uext is not None else 0.0)
        hh = scn.hand(t) if scn.hand is not None else None
        if hh is None:
            pl.step(u)
        else:
            pl.step(u, *hh)
        th_r[n], om_r[n], T_r[n], sp_r[n] = pl.th, pl.om, T, cmd_in
        I_r[n] = lane.log["I"]
        fz_r[n] = lane.log["frz"]
    return dict(th=th_r, om=om_r, T=T_r, sp=sp_r, I=I_r, frz=fz_r, wire=np.array(wire), wraps=lane.wraps)


BASELINE = E1.Policy("baseline", icl_flat=4096, reset_firm=None, bleed_lo=None, kp=112)


def main():
    lines = []
    # CONTROL 1: E1Lane(baseline) == nl_sim.Lane on nl_sim.run, several scenarios/speeds/members/impls
    cases = [("P2", "nominal", 11.9), ("P2", "b_lo*J_hi", 17.0), ("F2", "bc", 17.0), ("F2", "F_hi", 26.9),
             ("P2", "nominal", 5.0), ("F2", "nominal", 11.9)]
    def rh(tgt):
        return NS.Scn(dur=11.0, ref=lambda t: tgt * np.interp(t, [0, 0.5, 2.0, 99], [0, 0, 1, 1]))
    maxdT = maxdth = 0
    for im, mem, v in cases:
        tgt = 2.0 * 2.83 * 16.0 / v ** 2 * 180 / np.pi
        cols = [dict(impl=im, member=mem, v=v, age=0)]
        scn = rh(np.array([tgt]))
        r_ref = NS.run(cols, scn)
        r_e1 = run_e1(cols, scn, BASELINE)
        maxdT = max(maxdT, int(np.abs(r_ref["T"].astype(int) - r_e1["T"].astype(int)).max()))
        maxdth = max(maxdth, float(np.abs(r_ref["th"] - r_e1["th"]).max()))
    lines.append(f"CONTROL 1 E1Lane(baseline) vs nl_sim.Lane over {len(cases)} cases (rh turn-hold 2 m/s^2): "
                 f"max|dT| {maxdT}, max|dtheta| {maxdth:.2e}  {'OK' if maxdT == 0 and maxdth == 0 else 'FAIL'}")
    # CONTROL 2: the ICL walk reproduces a flat table == flat cal
    rows = ((0, 4096), (0xFFFF, 4096))
    ok = all(E1._icl_walk(rows, v) == 4096 for v in (0, 500, 6000, 12000))
    lines.append(f"CONTROL 2 flat ICL table == flat cal 4096: {'OK' if ok else 'FAIL'}")
    # CONTROL 3: nl_cave.walk_G (independent) vs the table I use for P2 (sanity that tables parse)
    rowsP2 = NC.parse_table(NC.load_hex("P2"))[1]
    gref = [NC.walk_G(rowsP2, v) for v in (714, 1843, 2304, 2707, 4032, 6198)]
    lines.append(f"CONTROL 3 P2 table G at knots: {gref}")
    out = "\n".join(lines)
    print(out)
    (OUT / "control_out.txt").write_text(out + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
