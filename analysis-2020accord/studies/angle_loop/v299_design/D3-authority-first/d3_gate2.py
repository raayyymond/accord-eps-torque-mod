# -*- coding: utf-8 -*-
r"""d3_gate2.py -- D3 (authority-first) GATE 2 HEADROOM SCAN: how far can the V298 loop gain rise, per speed, before
GATE 2's margins bind?  ANALYSIS ONLY (no image, no fork file, nothing sent).

MODEL: the C3-r1 STABILITY refuter's INDEPENDENT model (refute_stability/c3r1/c3r1_model.py), UNCHANGED -- the same
model rb_gate2.py used to clear V298 (C3B-P): ZOH-exact plant FRF (rigid J,b,k or two-mass mode13/mode20), 100 Hz hold
at ages e+1..e+10, the 1 kHz gp-0x6abe EMA (37/128), the output lag (oa 992, ob 507), fwd 5346, fade 254/256.
THE CONTROLLER = V298's arithmetic: E = 16(sp - theta) per 0.1 deg; E' = E G(v) >> 8; P = E' Kp >> 8; I += E' Ki/32768;
D = Kd * gp-0x6abe >> 3 (fresh, motor frame, NOT scaled by G).  The scan multiplies G(v) (= the cave table's row at that
speed) by m -- the only lever implementation (a) moves in the small-signal loop.  Kd is held at 48 (also scanned 32/64).

GATES (rb_gate2 / C3-rev2 design section 3): every member of the credible set (SINGLE + COMBINED, incl. the ms_free
products), the frame box (nom, FA.83, FA1.155, FB.83, FB1.155), hold offsets e in {-1, 0, 5, 10}, loops PID and PD
(I frozen = every freeze state): PM >= 45 (tier-A singles, e <= 0) / 30 (else), GM_up >= 6 dB, 5-30 Hz peak <= +3 dB.
REPORTED, not gated here: |L(20 Hz)| / V295's (the goal's "20 Hz <= V295"), and the nominal closed-loop setpoint
bandwidth (-3 dB of theta/theta_sp) for comparison with route 79's measured 0.4-0.6 Hz.

usage: python d3_gate2.py            -> stdout + _scratch/angle_loop/v299-D3/gate2_scan.{txt,json}
"""
import json
import math
import os
import sys
import time
from dataclasses import dataclass
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]                                       # .../studies/angle_loop
KIT = AL.parents[2]
sys.path.insert(0, str(AL / "refute_stability" / "c3r1"))
import c3r1_model as M  # noqa: E402

OUT = KIT / "_scratch" / "angle_loop" / "v299-D3"
OUT.mkdir(parents=True, exist_ok=True)

GB_P = ((714, 1178, 1041), (1843, 1465, -6264), (2304, 760, -2033), (2707, 560, 1570), (4032, 1068, 2118),
        (6198, 2188, 0), (0xFFFF, 2188, 0))               # V298 image @0xC4CDA (asserted in d3_common)
SINGLE = ("nominal", "J_lo", "J_hi", "b_lo", "b_hi", "tau0", "tau6", "mode13", "mode20", "ms_free")
COMBINED = ("b_lo*J_hi", "b_lo*tau6", "J1.0", "b_q", "b_q*J_hi", "b_q*J1.0", "b_q*tau6", "b_lo*ms_free", "b_q*ms_free")
GATED = SINGLE + COMBINED
S_C = 1.155
FRAMES = (("nom", 1.0, 1.0), ("FA.83", 0.83, 1.0), ("FA1.155", 1.155, 1.0), ("FB.83", 0.83, 1 / S_C),
          ("FB1.155", 1.155, 1 / S_C))
ES = (-1, 0, 10)
SPEEDS = (2.0, 3.1, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 11.9, 13.0, 15.0, 17.0, 20.0, 23.0, 26.9, 30.0)
MULTS = (0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0)
KDS = (48, 32, 64)
F = np.unique(np.concatenate([np.logspace(-2.3, math.log10(499.0), 900), [0.1, 0.2, 0.5, 1, 5, 7, 10, 13, 15, 16,
                                                                          17, 20, 25, 30]]))
I20 = int(np.argmin(abs(F - 20.0)))
B530 = (F >= 5) & (F <= 30)


@dataclass
class Des(M.Design):
    mult: float = 1.0

    def G(self, v):
        return M.walk_G(GB_P, M.spd(v)) * self.mult


def bar(mem, e):
    return 45.0 if (mem in SINGLE and e <= 0) else 30.0


def work(args):
    mem, v = args
    pl = M.member(mem, v)
    chans = {jb: M.plant_channels(pl, F, jb) for jb in (1.0, 1 / S_C)}
    V295 = M.designs()["V295"]
    res = []
    for kd in KDS:
        for m in MULTS:
            if kd != 48 and m not in (1.0, 1.5, 2.0, 2.5):
                continue
            des = Des("D3", "fresh", kp=112.0, ki=40.0, kd=float(kd), rows=GB_P, mult=m)
            worst = (1e9, None)
            gmin, pkmax, l20max = 1e9, -1e9, 0.0
            for e in ES:
                CthV, CwV, _ = M.controller(V295, v, F, e, 1.0)
                for noI in (False, True):
                    for fn, kap, jb in FRAMES:
                        Pt, Pw = chans[jb]
                        Cth, Cw, Cref = M.controller(des, v, F, e, kap, noI=noI)
                        K = M.Kout(F)
                        L = -K * (Cth * Pt + Cw * Pw)
                        PM, FC, GMu = M.pm_gm(L, F)
                        Sx = 1 / (1 + L)
                        pk = 20 * math.log10(max(np.abs(L * Sx)[B530].max(), np.abs(K * Cref * Pt * Sx)[B530].max()))
                        LV = -M.Kout(F) * kap * (CwV * Pw)
                        l20 = abs(L[I20]) / abs(LV[I20])
                        mg = PM - bar(mem, e)
                        if mg < worst[0]:
                            worst = (mg, f"{fn} e{e} {'PD' if noI else 'PID'} PM {PM:.1f} fc {FC:.2f}")
                        gmin = min(gmin, GMu)
                        pkmax = max(pkmax, pk)
                        if not noI:
                            l20max = max(l20max, l20)
            res.append(dict(mem=mem, v=v, kd=kd, m=m, margin=worst[0], where=worst[1], gm=gmin, pk=pkmax, l20=l20max))
    return res


def nominal_bw(v, m, kd=48):
    """closed-loop setpoint bandwidth (-3 dB of theta/theta_sp), nominal member, nom frame, e = 0, PID; and the
    0.1 Hz |T| and phase lag (ms)."""
    des = Des("D3", "fresh", kp=112.0, ki=40.0, kd=float(kd), rows=GB_P, mult=m)
    pl = M.member("nominal", v)
    f = np.logspace(-2, 1.3, 600)
    L, Sx, Tr, _ = M.loop(des, pl, v, f=f, e=0)
    a = np.abs(Tr)
    lo = f < 0.05
    ref = a[lo].mean()
    below = np.where(a < ref / math.sqrt(2))[0]
    bw = float(f[below[0]]) if len(below) else float("nan")
    j = int(np.argmin(abs(f - 0.1)))
    lag_ms = -np.angle(Tr[j]) / (2 * math.pi * f[j]) * 1e3
    pkdb = 20 * math.log10(a.max() / ref)
    return bw, float(a[j]), float(lag_ms), float(pkdb)


def main():
    t0 = time.time()
    jobs = [(mm, v) for mm in GATED for v in SPEEDS]
    with Pool(15) as pool:
        R = [r for rr in pool.imap_unordered(work, jobs, chunksize=2) for r in rr]
    lines = [f"D3 GATE-2 headroom scan on c3r1_model (unchanged); V298 = GB-P, Kp 112, Ki 40, Kd 48; G x m.",
             f"gated set: {len(GATED)} members x 5 frames x e {ES} x (PID, PD).  bars: PM 45 (tier-A e<=0) / 30, "
             f"GM_up 6 dB, 5-30 Hz peak +3 dB.  l20 = max |L(20Hz)| / V295's (PID; reported)."]
    out = {}
    for kd in KDS:
        lines.append(f"\n== Kd {kd} ==  per speed: worst PM margin (deg over bar) / min GM_up dB / max pk dB / max l20 ;"
                     f" PASS = all gates")
        hdr = "  v m/s  G_V298 Kp_eff |" + "".join(f"  m={m:<4}            " for m in MULTS if kd == 48 or
                                                    m in (1.0, 1.5, 2.0, 2.5))
        lines.append(hdr)
        for v in SPEEDS:
            g0 = M.walk_G(GB_P, M.spd(v))
            row = f"  {v:5.1f}  {g0:5d}  {112 * g0 / 256:6.0f} |"
            for m in MULTS:
                if kd != 48 and m not in (1.0, 1.5, 2.0, 2.5):
                    continue
                X = [r for r in R if r["v"] == v and r["m"] == m and r["kd"] == kd]
                w = min(X, key=lambda r: r["margin"])
                gm = min(r["gm"] for r in X)
                pk = max(r["pk"] for r in X)
                l20 = max(r["l20"] for r in X)
                ok = w["margin"] >= 0 and gm >= 6 and pk <= 3
                out[f"{kd}|{v}|{m}"] = dict(margin=w["margin"], mem=w["mem"], where=w["where"], gm=gm, pk=pk, l20=l20,
                                            ok=bool(ok))
                row += f" {'P' if ok else 'F'}{w['margin']:+5.1f}/{gm:4.1f}/{pk:+4.1f}/{l20:4.2f}"
            lines.append(row)
        # max passing multiplier per speed
        mx = []
        for v in SPEEDS:
            ok = [m for m in MULTS if (kd == 48 or m in (1.0, 1.5, 2.0, 2.5)) and out[f"{kd}|{v}|{m}"]["ok"]]
            # contiguous from 1.0 upward
            best = None
            for m in sorted(ok):
                if m >= 1.0:
                    best = m
            mx.append((v, best))
        lines.append("  max passing m (largest tested m that passes): " +
                     ", ".join(f"{v}:{b}" for v, b in mx))
        # binding member at the first failing m
        for v in SPEEDS:
            fails = [m for m in MULTS if (kd == 48 or m in (1.0, 1.5, 2.0, 2.5)) and not out[f"{kd}|{v}|{m}"]["ok"]
                     and m >= 1.0]
            if fails:
                m = min(fails)
                o = out[f"{kd}|{v}|{m}"]
                lines.append(f"    v {v:5.1f}: first fail at m={m}: worst {o['mem']} {o['where']} margin {o['margin']:+.1f}"
                             f" GM {o['gm']:.1f} pk {o['pk']:+.1f}")
    # nominal closed-loop bandwidth (vs route 79's measured 0.4-0.6 Hz at 8-25 m/s, 1.1 Hz > 25)
    lines.append("\n== nominal closed-loop setpoint bandwidth (Hz) / |T(0.1Hz)| / 0.1 Hz lag ms / peak dB, Kd 48 ==")
    for v in (3.1, 5.0, 8.0, 11.9, 17.0, 26.9):
        s = f"  v {v:5.1f}: "
        for m in (1.0, 1.5, 2.0, 2.5):
            bw, t01, lag, pkdb = nominal_bw(v, m)
            s += f" m{m}: {bw:4.2f} Hz {t01:4.2f} {lag:5.0f}ms {pkdb:+4.1f}dB |"
            out[f"bw|{v}|{m}"] = dict(bw=bw, t01=t01, lag=lag, pk=pkdb)
        lines.append(s)
    lines.append(f"\nwall time {time.time() - t0:.1f} s")
    txt = "\n".join(lines)
    print(txt)
    (OUT / "gate2_scan.txt").write_text(txt, encoding="utf-8")
    (OUT / "gate2_scan.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
