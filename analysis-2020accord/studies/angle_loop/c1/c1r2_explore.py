# -*- coding: utf-8 -*-
"""c1r2_explore.py -- first look for C1 rev 2: the G(v) envelope against the rev-2 member set (c1r2_members), as a
function of Kd (and optionally Ki_base), and the 20 Hz anti-damping Re(T/omega) at the envelope.  ANALYSIS ONLY.

Same factored method as c1_design_G (L = g*A + B, linear in g = G/256; PM scanned UP from G = 128 on an 8-count grid,
stopping at the first failure), with c1r2_members.member().  Prints per speed: the envelope G, its binding member,
Kp_eff, and Re(T/w) at 13 and 20 Hz at that G (stab_hf's torque_per_rate convention, d = 2, age 0).
usage: python c1r2_explore.py <kd> [ki_base] [vmin vmax step] [tierB-only names comma-separated]"""
from __future__ import annotations

import math
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib as C  # noqa: E402
import c1r2_members as M  # noqa: E402
import stab_lin as S  # noqa: E402

F = np.logspace(math.log10(0.005), math.log10(120.0), 3000)
GGRID = np.arange(64, 6001, 8)


def AB(name, v, kp, ki, kd):
    pl, tau, ea, _ = M.member(name, v)
    A_, B_, Ct, Cw = pl
    Ad, Bd = S.c2d(A_, B_)
    z = np.exp(1j * 2 * np.pi * F * S.TS)
    zi = 1 / z
    a, b, c, d = Ad[0, 0], Ad[0, 1], Ad[1, 0], Ad[1, 1]
    det = (z - a) * (z - d) - b * c
    Pt = ((z - d) * Bd[0, 0] + b * Bd[1, 0]) / det
    Pw = (c * Bd[0, 0] + (z - a) * Bd[1, 0]) / det
    hold = sum(zi ** (q + ea) for q in range(1, 11)) / 10
    Hout = (S.OB / 1024) * (1 + zi) / (32 * (1 - (S.OA / 1024) * zi))
    K = S.FADE * S.FWD * Hout * zi ** tau
    PI = kp / 256 + (ki / 32768) / (1 - zi)
    return K * PI * 80 * (1 + zi) * hold * Pt, K * kd * hold * Pw


def pm_of(L):
    mag = np.abs(L)
    ph = np.unwrap(np.angle(L)) * 180 / np.pi
    s = np.sign(mag - 1)
    idx = np.where(s[:-1] * s[1:] <= 0)[0]
    if len(idx) == 0:
        return float("nan")
    pms = []
    for i in idx:
        if mag[i] == mag[i + 1]:
            continue
        t = (1 - mag[i]) / (mag[i + 1] - mag[i])
        p = ph[i] + t * (ph[i + 1] - ph[i])
        pms.append(((p + 180) + 180) % 360 - 180)
    return min(pms)


def gmax(name, v, thr, kp, ki, kd):
    A, B = AB(name, v, kp, ki, kd)
    best = 0
    for G in GGRID:
        if not (pm_of((G / 256) * A + B) >= thr):
            break
        best = int(G)
    return best


def tpr(G, kp, ki, kd, f, d=2, age=0):
    z = np.exp(1j * 2 * np.pi * f * S.TS); zi = 1 / z
    hold = sum(zi ** (a + age) for a in range(1, 11)) / 10.0
    Hout = (S.OB / 1024) * (1 + zi) / (32 * (1 - (S.OA / 1024) * zi))
    K = S.FADE * S.FWD * Hout * zi ** d
    PI = kp / 256.0 + (ki / 32768.0) / (1 - zi)
    w = 2 * math.pi * f
    return (K * ((G / 256) * PI * 80 * (1 + zi) * hold / (1j * w) + kd * hold)).real


def job(args):
    v, kp, ki, kd, names = args
    out = {}
    for n in names:
        out[n] = gmax(n, v, M.TIER_PM.get(n, 30.0), kp, ki, kd)
    return v, out


V295_RE20 = -0.633


def main():
    kd = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    ki = int(sys.argv[2]) if len(sys.argv) > 2 else C.KI_BASE
    vmin, vmax, vst = (float(x) for x in sys.argv[3:6]) if len(sys.argv) > 5 else (1.0, 35.0, 0.5)
    names = sys.argv[6].split(",") if len(sys.argv) > 6 else list(M.TIER_A + M.TIER_B)
    kp = C.KP_BASE
    speeds = [round(x, 3) for x in np.arange(vmin, vmax + 1e-9, vst)]
    with Pool(14) as pool:
        res = dict(pool.map(job, [(v, kp, ki, kd, names) for v in speeds]))
    print(f"# kd {kd} ki_base {ki} kp_base {kp}; members {len(names)}")
    print("    v   envG  Kp_eff  binding            2nd                 Re13      Re20  Re20/V295")
    for v in speeds:
        r = res[v]
        srt = sorted(r.items(), key=lambda t: t[1])
        G = srt[0][1]
        print(f"{v:6.2f} {G:5d} {kp * G / 256:7.0f}  {srt[0][0]:18s} {srt[1][0]:14s}({srt[1][1]:5d})"
              f" {tpr(G, kp, ki, kd, 13):+8.3f} {tpr(G, kp, ki, kd, 20):+8.3f} {tpr(G, kp, ki, kd, 20) / V295_RE20:7.3f}")


if __name__ == "__main__":
    main()
