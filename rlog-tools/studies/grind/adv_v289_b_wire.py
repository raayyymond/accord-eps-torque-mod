# -*- coding: utf-8 -*-
"""studies/grind/adv_v289_b_wire.py -- ADVERSARY B, B4 for V289 rev 1: the byte-exact V289 chain mirror run on the LOGGED
setpoints of r39 (V282) and r5e_v288 (V288) over the whole laterally-engaged route, open loop on the measured wheel rate
(the same convention as grind_incident_r35.simulate).  Reports the 18-22 Hz content of the clamped sum S before vs after
the notch (FAIL if the reduction < 6 dB), the residual at 17 and 23 Hz, the rms of the removed component n = S - y, and the
predicted duties of 0x14A b4.5 = sign(n) and b4.7 = |n| >= |y| so the first drive can be read.   Subagent advB, 2026-09-08.
Analysis only.  Writes _scratch/adv_v289_b_wire.txt beside it.

The notch mirror below is a Python transcription of the cave as DECODED by adv_v289_b_cave (not of the build script) and
is validated tick-for-tick against the interpreter on 20,000 random ticks before it is used.
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import adv_v289_b_cave as CV          # noqa: E402
import adv_v289_b_loop as LP          # noqa: E402
import creep20_loop_id as C20         # noqa: E402
import grind_incident_r35 as GI       # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS1K = 1000.0
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def notch_mirror(x, nc, clamp):
    """TDF-II + first-order error feedback + output clamp, exactly as decoded: returns y (clamped), n = x - y_linear, flag."""
    b0, b1, a2 = nc["b0"], nc["b1"], nc["a2"]
    s1 = s2 = e = 0
    y = np.empty(len(x), np.int64); n_ = np.empty(len(x), np.int64); fl = np.empty(len(x), np.int64)
    for i, xi in enumerate(x):
        xi = int(xi)
        acc = s1 + e + b0 * xi
        yl = acc >> 14
        e = acc & 0x3FFF
        s2n = b0 * xi - a2 * yl
        n = xi - yl
        s1 = s2 + b1 * n
        s2 = s2n
        f = (0x20 if n < 0 else 0) | (0x80 if abs(n) >= abs(yl) else 0)
        yc = max(-clamp, min(clamp, yl))
        y[i] = yc; n_[i] = n; fl[i] = f
    return y, n_, fl


def validate_mirror(img, nc, clamp, n=20000, seed=1):
    rng = np.random.default_rng(seed)
    x = np.concatenate([rng.integers(-15360, 15361, n // 2), np.round(15360 * np.sin(2 * np.pi * 20.04 * np.arange(n // 2) / FS1K) * rng.uniform(0.5, 1.0, n // 2)).astype(int)])
    cv = CV.Cave(img)
    ys = np.empty(n, np.int64); fs = np.empty(n, np.int64)
    for i, v in enumerate(x):
        ys[i] = cv.tick(int(v)); fs[i] = cv.flag()
    y, n_, fl = notch_mirror(x, nc, clamp)
    return bool(np.array_equal(ys, y) and np.array_equal(fs, fl)), int(np.sum(ys != y)), int(np.sum(fs != fl))


def chain(g, c, nc=None, clamp=15360):
    """The FUN_00028ea6 mirror over the WHOLE route at 1 kHz, open loop on the measured rate, ZOH command per 100 Hz frame.
    Integer-exact where the firmware is integer (fb filter, P, D, sum, notch); returns S (pre-notch), y (post), n, flag, eng1k."""
    n1 = len(g["t"]) * 10
    wire = C20.up1k(g["wire"])
    x = np.clip(-wire, -12000, 12000).astype(np.int64)
    # fb filter, exact ints
    s = 0; fb = np.empty(n1, np.int64)
    fa, fbb, fcl = int(c["fb_a"]), int(c["fb_b"]), int(c["fb_clamp"])
    for i in range(n1):
        s_new = ((fa * s) >> 10) + ((fbb * int(x[i])) >> 10)
        v = s + s_new; fb[i] = -fcl if v < -fcl else (fcl if v > fcl else v); s = s_new
    cmd1k = np.repeat(g["cmd"], 10); bar1k = np.repeat(g["bar"], 10)
    idx, sgn = GI.demand_live(cmd1k, bar1k, c); idx = np.round(idx)
    sp = np.round(sgn * GI.lerp(c["map_X"], c["map_Y"], idx)).astype(np.int64)
    kp = int(c["kp_Y"][0]); kd = int(c["kd_Y"][0])
    E = 32 * sp - fb
    P = np.clip((E * kp) >> 8, -int(c["p_clamp"]), int(c["p_clamp"]))
    dE = np.r_[0, np.diff(E)]
    D = np.clip((dE * kd) >> 3, -int(c["d_clamp"]), int(c["d_clamp"]))
    eng1k = np.repeat(g["eng"], 10)
    B = GI.lerp(c["fadeB"][0], c["fadeB"][1], np.abs(bar1k) // 32)
    m = (((255.0 * B).astype(np.int64) & 0xFFFF) >> 8).astype(np.int64)
    S = np.clip((m * (P + D)) >> 8, -int(c["sum_clamp"]), int(c["sum_clamp"]))
    S[~eng1k] = 0
    if nc is None:
        return dict(S=S, y=S.copy(), n=np.zeros_like(S), flag=np.zeros_like(S), eng=eng1k, E=E, P=P, D=D, sp=sp, fb=fb)
    y, n_, fl = notch_mirror(S, nc, clamp)
    return dict(S=S, y=y, n=n_, flag=fl, eng=eng1k, E=E, P=P, D=D, sp=sp, fb=fb)


def lag_T(u, c):
    st = signal.lfilter([c["lag_b"] / 1024.0], [1.0, -c["lag_a"] / 1024.0], u.astype(float)); yy = (np.r_[0.0, st[:-1]] + st) / 32.0
    return np.clip(np.floor(-yy * c["gain"] / 32768), -int(c["t_clamp"]), int(c["t_clamp"]))


def band_amp(x, lo, hi, fs=FS1K):
    """rms amplitude in a band, Welch, engaged samples only handled by caller (x already masked/segmented)."""
    f, P = signal.welch(x, fs=fs, nperseg=4096)
    sel = (f >= lo) & (f <= hi)
    return float(np.sqrt(np.trapezoid(P[sel], f[sel]) * 2)), f, P


def main():
    img289 = open(CV.IMG289, "rb").read()
    c289 = GI.read_cells(CV.IMG289); c282 = GI.read_cells(CV.IMG282)
    nc = LP.notch_ints(img289)
    clamp = int(c289["sum_clamp"])
    ok, ny, nf = validate_mirror(img289, nc, clamp)
    pr("mirror vs interpreter on 20,000 ticks: identical = %s (y mismatches %d, flag mismatches %d)" % (ok, ny, nf))
    assert ok
    pr("cells: V282 fb %d/%d ; V289 fb %d/%d ; notch %s ; clamp %d" % (c282["fb_a"], c282["fb_b"], c289["fb_a"], c289["fb_b"], nc, clamp))
    res = {}
    for tag in ("r39", "r5e_v288"):
        g = C20.load(tag)
        marks = json.load(open(os.path.join(C20.CACHE, tag + "_marks.json")))
        eng = g["eng"]; ne = int(eng.sum())
        pr("\n=== %s : %d frames, %d engaged (%.0f s), marks at %s" % (tag, len(g["t"]), ne, ne / 100.0, [round(m["t_route"], 1) for m in marks["marks"]]))
        A = chain(g, c282, None)                # V282 as-built: S
        B = chain(g, c289, nc, clamp)           # V289: S (pre-notch, with the fb pole moved) and y (post)
        Bn = chain(g, c282, nc, clamp)          # notch only on V282 cells (isolates the notch from the fb pole)
        eng1k = A["eng"]
        # engaged runs >= 5 s for spectra
        runs = C20.runs(eng1k, 5000)
        def pooled(xs, lo, hi):
            num = 0.0; den = 0
            for a, b in runs:
                amp, f, P = band_amp(xs[a:b], lo, hi); num += amp ** 2 * (b - a); den += (b - a)
            return np.sqrt(num / den) if den else np.nan
        def pooled_psd(xs):
            acc = None; den = 0
            for a, b in runs:
                f, P = signal.welch(xs[a:b].astype(float), fs=FS1K, nperseg=4096)
                acc = P * (b - a) if acc is None else acc + P * (b - a); den += (b - a)
            return f, acc / den
        for lo, hi, nm in ((18, 22, "18-22"), (16.5, 17.5, "17"), (22.5, 23.5, "23"), (13, 17, "13-17"), (25, 33, "25-33"), (2, 6, "2-6"), (6, 10, "6-10")):
            a282 = pooled(A["S"].astype(float), lo, hi); s289 = pooled(B["S"].astype(float), lo, hi); y289 = pooled(B["y"].astype(float), lo, hi); yn = pooled(Bn["y"].astype(float), lo, hi)
            pr("  %-6s Hz rms of S: V282 %7.1f | V289 pre-notch %7.1f | V289 post-notch y %7.1f  -> post/pre %.3f (%+.1f dB) ; post vs V282 %.3f (%+.1f dB) ; notch-only on V282 cells %.3f (%+.1f dB)" % (
                nm, a282, s289, y289, y289 / s289, 20 * np.log10(y289 / s289), y289 / a282, 20 * np.log10(y289 / a282), yn / a282, 20 * np.log10(yn / a282)))
        # the delivered torque T after the lag: 18-22 Hz
        T282 = lag_T(A["S"], c282); T289 = lag_T(B["y"], c289)
        pr("  T (after lag/gain/cap) 18-22 Hz rms: V282 %.2f  V289 %.2f  (x%.3f, %+.1f dB) ; T rms overall engaged %.1f -> %.1f" % (
            pooled(T282, 18, 22), pooled(T289, 18, 22), pooled(T289, 18, 22) / pooled(T282, 18, 22), 20 * np.log10(pooled(T289, 18, 22) / pooled(T282, 18, 22)), np.sqrt(np.mean(T282[eng1k] ** 2)), np.sqrt(np.mean(T289[eng1k] ** 2))))
        # rails: does the fb pole's HF gain rise make the D clamp bind more?
        for nm, X in (("V282", A), ("V289", B)):
            dd = np.r_[0, np.diff(X["E"])] * int(c282["kd_Y"][0]) >> 3
            pr("  %s rail duties engaged: D clamp %.4f ; P clamp %.4f ; sum clamp %.4f ; fb clamp %.4f ; rms D %.0f rms P %.0f" % (
                nm, np.mean(np.abs(dd[eng1k]) >= 10240), np.mean(np.abs(X["P"][eng1k]) >= 15360), np.mean(np.abs(X["S"][eng1k]) >= 15360), np.mean(np.abs(X["fb"][eng1k]) >= 46080), np.sqrt(np.mean(X["D"][eng1k].astype(float) ** 2)), np.sqrt(np.mean(X["P"][eng1k].astype(float) ** 2))))
        # removed component n and the bits
        n = B["n"]; fl = B["flag"]
        e = eng1k
        pr("  removed component n = S - y over engaged ticks: rms %.1f, p50 |n| %.1f, p90 %.1f, p99 %.1f, max %d ; rms S %.1f ; n/S rms %.3f" % (
            np.sqrt(np.mean(n[e].astype(float) ** 2)), *np.percentile(np.abs(n[e]), (50, 90, 99)), np.max(np.abs(n[e])), np.sqrt(np.mean(B["S"][e].astype(float) ** 2)), np.sqrt(np.mean(n[e].astype(float) ** 2)) / max(np.sqrt(np.mean(B["S"][e].astype(float) ** 2)), 1)))
        b5 = (fl & 0x20) > 0; b7 = (fl & 0x80) > 0
        pr("  PREDICTED duties (1 kHz ticks, engaged): b4.5 = sign(n)<0 : %.3f ; b4.7 = |n|>=|y| : %.3f ; at 100 Hz sample instants (every 10th tick): %.3f / %.3f ; disengaged: %.3f / %.3f" % (
            b5[e].mean(), b7[e].mean(), b5[e][::10].mean(), b7[e][::10].mean(), b5[~e].mean(), b7[~e].mean()))
        # b7 conditional on |S|: steady creep vs episodes
        Sabs = np.abs(B["S"])
        for lo, hi in ((0, 100), (100, 1000), (1000, 5000), (5000, 15360), (15360, 15361)):
            sel = e & (Sabs >= lo) & (Sabs < hi) if hi > lo + 1 else e & (Sabs == 15360)
            if sel.sum() > 100:
                pr("    |S| in [%5d,%5d): share %.3f  b5 %.3f  b7 %.3f  rms n %.1f" % (lo, hi, sel.mean(), b5[sel].mean(), b7[sel].mean(), np.sqrt(np.mean(n[sel].astype(float) ** 2))))
        # bookmark windows
        t1k = np.repeat(g["t"], 10)
        for m in marks["marks"]:
            tm = m["t_route"] + marks.get("t0_mono", 0) - marks.get("t0_mono", 0)
            # marks t_route is route-relative; g["t"] is the nominal frame time -- find the frame axis offset
            tr = m["t_route"]
            sel = (t1k >= g["t"][0] + tr - 6.0) & (t1k <= g["t"][0] + tr + 0.5) & e
            if sel.sum() < 1000:
                continue
            a1, f1, P1 = band_amp(B["S"][sel].astype(float), 18, 22); a2, _, _ = band_amp(B["y"][sel].astype(float), 18, 22); a0, _, _ = band_amp(A["S"][sel].astype(float), 18, 22)
            pr("  mark t=%.1f s window [-6,+0.5] s (%d ticks engaged): S 18-22 rms V282 %.0f, V289 pre %.0f, post %.0f (%+.1f dB) ; b5 duty %.3f b7 duty %.3f ; rms n %.0f ; max|S| %d" % (
                tr, sel.sum(), a0, a1, a2, 20 * np.log10(a2 / a1), b5[sel].mean(), b7[sel].mean(), np.sqrt(np.mean(n[sel].astype(float) ** 2)), np.max(Sabs[sel])))
        # spectral ratio around the line: pooled PSD S pre vs y post
        f, Ps = pooled_psd(B["S"]); _, Py = pooled_psd(B["y"]); _, Pa = pooled_psd(A["S"])
        pr("  pooled PSD ratio post/pre (dB) at: " + "  ".join("%g Hz %+.1f" % (fx, 10 * np.log10(Py[np.argmin(np.abs(f - fx))] / Ps[np.argmin(np.abs(f - fx))])) for fx in (5, 10, 15, 17, 18, 19, 20, 21, 22, 23, 25, 30, 40)))
        pr("  pooled PSD ratio V289 pre-notch / V282 (the fb pole alone, dB) at: " + "  ".join("%g Hz %+.1f" % (fx, 10 * np.log10(Ps[np.argmin(np.abs(f - fx))] / Pa[np.argmin(np.abs(f - fx))])) for fx in (5, 10, 15, 20, 25, 30, 40, 60, 100)))
        # how often does the output clamp bind on y (the notch overshoot) vs S rail
        pr("  rail duty engaged: |S|=15360 pre-notch %.4f ; |y| clamped at 15360 %.4f ; |y_linear| > 15360 (clamp binding on overshoot) %.4f" % (
            np.mean(Sabs[e] == clamp), np.mean(np.abs(B["y"][e]) == clamp), np.mean(np.abs(B["S"][e] - n[e]) > clamp)))
        res[tag] = dict(red_db=20 * np.log10(pooled(B["y"].astype(float), 18, 22) / pooled(B["S"].astype(float), 18, 22)), b5=float(b5[e].mean()), b7=float(b7[e].mean()))
    pr("\nVERDICT B4: 18-22 Hz reduction of S through the notch: " + " ; ".join("%s %+.1f dB" % (k, v["red_db"]) for k, v in res.items()) + "  (FAIL if > -6 dB)")
    with open(os.path.join(SCR, "adv_v289_b_wire.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    pr("wrote _scratch/adv_v289_b_wire.txt")


if __name__ == "__main__":
    main()
