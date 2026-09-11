# -*- coding: utf-8 -*-
"""A3 -- gyro/calibration chain (F5), Ackermann small-angle artefact (F3), episode census,
steady-state (F6), engaged-vs-manual and firmware arms (F7), lead/lag (F5)."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import audit_lib as A

TAGS = ["r62", "r63", "r39", "r35", "r97"]
ARM = {"r62": "V289r1/forkHEAD", "r63": "V289r1/forkHEAD", "r39": "V282", "r35": "V281r3", "r97": "STOCK fw"}
BINS = [(2, 5), (5, 10), (10, 20), (20, 35), (35, 50), (50, 75), (75, 120), (120, 400)]
G = {t: A.grid(A.load(t)) for t in TAGS}


def gate(g, lo, hi, eng=True, vmin=4.0, ratemax=20.0):
    sa = g["sa_deg"]
    base = (g["eng"] if eng else g["man"])
    return (base & (g["v"] > vmin) & (np.abs(g["rate"]) < ratemax)
            & (np.abs(sa) >= lo) & (np.abs(sa) < hi) & np.isfinite(g["denom"]))


print("=" * 120)
print("A3a  GYRO-FREE ARBITRATION.  yaw_ws = (v_rr - v_rl)/1.585 from raw CAN 0x1D0 (no gyro, no")
print("     rpyCalib, no Kalman).  scale = TLS slope of yaw_cal on yaw_ws.  A scale that DRIFTS with")
print("     |angle| would manufacture the whole finding; a flat scale exonerates the chain.")
print("=" * 120)
print("   %-5s %-9s %8s %9s %9s %9s" % ("route", "|sa|", "n(s)", "yawcal/ws", "corr", "med|yaw|"))
for t in TAGS:
    g = G[t]
    if "yaw_ws" not in g:
        continue
    for lo, hi in [(0, 400)] + BINS:
        m = gate(g, lo, hi) & np.isfinite(g["yaw_ws"]) & (np.abs(g["yaw_ws"]) > 0.01)
        if m.sum() < 300:
            continue
        s, _ = A.tls0(g["yaw_ws"][m], -g["yaw_cal"][m])
        c = float(np.corrcoef(g["yaw_ws"][m], -g["yaw_cal"][m])[0, 1])
        print("   %-5s %-9s %8.0f %9.4f %9.4f %9.4f" % (
            t, "%d-%d" % (lo, hi), m.sum() / A.FS, s, c, float(np.median(np.abs(g["yaw_cal"][m])))))
    print()

print("=" * 120)
print("A3b  THE SAME sR TABLE, MEASURED WITH THE WHEEL-SPEED YAW instead of the gyro.")
print("     Same estimator, same gate; only the yaw source changes.")
print("=" * 120)
print("   %-5s %-9s %8s %9s %9s %9s" % ("route", "|sa|", "n(s)", "sR(gyro)", "sR(wheel)", "delta"))
for t in TAGS:
    g = G[t]
    if "yaw_ws" not in g:
        continue
    sgn = np.sign(A.tls0(g["yaw_ws"][np.isfinite(g["yaw_ws"])], -g["yaw_cal"][np.isfinite(g["yaw_ws"])])[0])
    den_ws = (sgn * g["yaw_ws"] / np.maximum(g["v"], 1e-3)) - g["rollc"]
    for lo, hi in BINS:
        m = gate(g, lo, hi) & np.isfinite(den_ws)
        if m.sum() < 200:
            continue
        a, _ = A.tls0(g["denom"][m], g["cfac"][m] * g["sa"][m])
        b, _ = A.tls0(den_ws[m], g["cfac"][m] * g["sa"][m])
        print("   %-5s %-9s %8.0f %9.2f %9.2f %9.2f" % (t, "%d-%d" % (lo, hi), m.sum() / A.FS, a, b, b - a))
    print()

print("=" * 120)
print("A3c  ACKERMANN.  openpilot's model is curvature = delta_w / L (SMALL-ANGLE).  The kinematic")
print("     truth is tan(delta_w)/L.  So even a PERFECTLY CONSTANT rack reads")
print("        sR_meas = sR_true * delta_w / tan(delta_w),  delta_w = radians(sa)/sR_true")
print("     i.e. an APPARENT quickening that is pure small-angle approximation.  Size it:")
print("=" * 120)
print("   %-10s %10s %10s %10s" % ("|sa| deg", "delta_w deg", "d/tan(d)", "apparent sR (true 16.8)"))
for sa in (5, 20, 50, 100, 150, 200, 300, 400, 500):
    dw = np.radians(sa) / 16.8
    r = dw / np.tan(dw)
    print("   %-10d %10.2f %10.4f %10.2f" % (sa, np.degrees(dw), r, 16.8 * r))

print()
print("=" * 120)
print("A3d  EPISODE CENSUS of the load-bearing bins.  How many DISTINCT driving events is the")
print("     high-angle number built from?  (contiguous runs separated by > 1 s)")
print("=" * 120)
for t in TAGS:
    g = G[t]
    for lo, hi in ((50, 400), (120, 400)):
        m = gate(g, lo, hi)
        if m.sum() < 50:
            continue
        d = np.diff(m.astype(int)); st = np.flatnonzero(d == 1) + 1; en = np.flatnonzero(d == -1) + 1
        if m[0]: st = np.r_[0, st]
        if m[-1]: en = np.r_[en, len(m)]
        runs = [(a, b) for a, b in zip(st, en) if b - a > 10]
        durs = [(b - a) / A.FS for a, b in runs]
        vs = [float(np.median(g["v"][a:b])) for a, b in runs]
        print("   %-5s |sa| %3d-%3d : %5.1f s in %2d episodes  longest %.2f s  med v %.1f m/s  v range %.1f-%.1f" % (
            t, lo, hi, m.sum() / A.FS, len(runs), max(durs) if durs else 0,
            float(np.median(vs)) if vs else np.nan, min(vs) if vs else np.nan, max(vs) if vs else np.nan))

print()
print("=" * 120)
print("A3e  ENGAGED vs MANUAL (F7).  The instrument claims to read the MECHANICAL rack, so the")
print("     curve must not care whether openpilot is steering.")
print("=" * 120)
print("   %-5s %-16s %-9s %8s %9s" % ("route", "arm", "|sa|", "n(s)", "sR"))
for t in TAGS:
    g = G[t]
    for lbl, eng in (("ENGAGED", True), ("MANUAL", False)):
        for lo, hi in ((2, 10), (10, 35), (35, 120), (120, 400)):
            m = gate(g, lo, hi, eng=eng)
            if m.sum() < 300:
                continue
            s, _ = A.tls0(g["denom"][m], g["cfac"][m] * g["sa"][m])
            print("   %-5s %-16s %-9s %8.0f %9.2f" % (t, ARM[t] + " " + lbl, "%d-%d" % (lo, hi), m.sum() / A.FS, s))
    print()
