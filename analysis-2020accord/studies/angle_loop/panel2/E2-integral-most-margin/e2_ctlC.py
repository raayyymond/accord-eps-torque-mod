# -*- coding: utf-8 -*-
r"""e2_ctlC.py -- CONTROL C: the vectorised E2Lane (the lane every time-domain number in this design comes from) makes
the SAME integral decision as e2_asm.cave_ref (the scalar statement the cave BYTES are checked against in H1), so the
chain bytes -> cave_ref -> E2Lane is closed.  Random one-tick states (I8, the held angle, the previous fb state, the
setpoint, the signed hand word, the ramp, the speed), every implementation of e2_asm.IMPL except K0; compared: the I
after Honda's update (0x29DA4..0x29DC2) and E'.  ANALYSIS ONLY."""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e2_asm as EA  # noqa: E402
import e2_lane as EL  # noqa: E402
import e2_exp as X  # noqa: E402
import harness_time as HT  # noqa: E402

KEYMAP = dict(sgn="sgn_thr", arb_sh="arb_sh", arb_B="arb_B", leak="leak_s", ramp="ramp_frz", arb_sh_lo="arb_sh_lo",
              arb_vth="arb_vth", leak_opp="leak_opp", leak_hard="leak_hard", opp_first="opp_first",
              arb_vcap="arb_vcap", arb_cap="arb_cap")


def lane_cfg(pol, icl):
    c = X.col(icl=icl)
    for k, v in pol.items():
        if k in KEYMAP:
            c[KEYMAP[k]] = v
    if "leak" in pol:
        c["leak_thr"] = pol.get("thr", 512)
    return c


def main():
    rng = np.random.default_rng(5)
    tbl = [tuple(r) for r in EA.R.tables()["P2"]]
    cal = HT.base_cal()
    lines = []
    for cid, pol in EA.IMPL.items():
        if pol.get("nopol"):
            continue
        bad = 0
        for rep in range(40):
            B = 200
            icl = 16383
            cfg = lane_cfg(pol, icl)
            ln = EL.E2Lane(cal, [cfg] * B)
            th = rng.integers(-12000, 12001, B)
            s_old = rng.integers(-96000, 96001, B)
            ln.s[:] = s_old
            ln.lane_ok[:] = 1
            r26 = np.clip(s_old + 8 * th, -65535, 65535)
            sp = rng.integers(-4096, 4097, B)
            tq = np.where(rng.random(B) < 0.5, rng.integers(-3000, 3001, B),
                          rng.choice([0, 300, 301, -300, -301, 200, 201, -200, -201, 512, 513, -512, -513], B))
            ramp = np.where(rng.random(B) < 0.75, 0x8000, rng.integers(1, 0x8000, B))
            v = np.where(rng.random(B) < 0.7, rng.integers(0, 9000, B), rng.choice([1381, 1382, 1383, 2879, 2880, 2881], B))
            i8 = rng.integers(-(icl << 10), icl << 10, B)
            if pol.get("arb_sh"):
                shv = np.where((pol.get("arb_sh_lo") is not None) & (v <= pol.get("arb_vth", -1)),
                               pol.get("arb_sh_lo", 0) or 0, pol["arb_sh"])
                bnd = (np.abs(th) << shv) + pol["arb_B"]
                if pol.get("arb_vcap") is not None:
                    bnd = np.where((v <= pol["arb_vcap"]) & (bnd > pol["arb_cap"]), pol["arb_cap"], bnd)
                pick = rng.random(B) < 0.5
                i8 = np.where(pick, (bnd + rng.integers(-2, 3, B)) * 1024 * np.where(rng.random(B) < 0.5, 1, -1)
                              + rng.integers(0, 1024, B), i8)
            ln.I8[:] = i8
            ln.abe[:] = 0
            ln.tick(th, 0, sp, tq, 0, v, ramp, 1, 1)
            I_lane = ln.log["I"]
            E_lane = ln.log["E"]
            for j in range(B):
                cells = {"6a5e": int(v[j]), "4f68": min(abs(int(tq[j])), 0xFFFF), "4f60": int(tq[j]), "6abe": 0,
                         "6a00": int(th[j]), "6dd0": int(i8[j])}
                r16, ex, r6, op = EA.cave_ref(pol, tbl, int(sp[j]), int(r26[j]), cells, int(ramp[j]))
                e5 = (r16 >> 5) if ex == EA.RET else r6
                inc = (e5 * 56) >> 3
                Ic = int(np.clip((int(i8[j]) >> 3) + inc, -((icl << 10) >> 3), (icl << 10) >> 3))
                if not (Ic == int(I_lane[j]) and r16 == int(E_lane[j])):
                    bad += 1
        lines.append(f"CONTROL C {cid:5s}: E2Lane one-tick I update and E' == cave_ref (the H1 reference), 8000 random "
                     f"states: {bad} mismatches")
        print(lines[-1], flush=True)
    (HERE / "e2_ctlC_out.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
