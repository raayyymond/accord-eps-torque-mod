# -*- coding: utf-8 -*-
r"""reqaxis 2026-09-09 -- WHERE THE Kp/Kd SCHEDULE KNOTS FALL ON THE WIRE.

The Kp record (0xE5378, slot 7) and the Kd record (0xE511C, slot 7) are LERPs on ONE axis:
the demand index `idx` published to gp-0x674b (byte) / gp-0x697a (halfword) by FUN_00028ea6.
Traced this session (code.bin, byte-identical in the V289 image over 0x29CA8-0x29EC0):

    0x29032  ld.h  -0x69ae,gp,r13     cmd  = gp-0x69ae = clamp(-4 * wire 0xE4 STEER_TORQUE, +-0x4000)
    0x29036  andi  0xffff,r16,r22     LIM  = LERP(0xCB844[sel])            (flat; 15360 stock, 16384 V280+)
    0x2903A..0x29044                  r22  = clamp(cmd, -LIM, +LIM)
    0x29A80..0x29CB2                  taper= LERP(0xCB924[sel] same-sign | 0xCB8B4[sel] opposite-sign,
                                              index |driver torque| >> 5)          (0..255)
    (0x29AF0-ish)                     spF  = LERP(tp+0x7974 = 0xC6974) == 255 FLAT
    0x29CB4  mulu  r6,r10,r0
    0x29CB8  andi  0xffff,r10,r7      G    = (taper * spF) & 0xFFFF        (65025 max)
    0x29CBC  mul   r22,r7,r0
    0x29CC0  sar   0x10,r7            v    = (G * r22) >> 16               (arithmetic)
    0x29CD6  sar   0x6,r7             v  >>= 6
    0x29CDC..0x29CF4                  v    = clamp(v, -cal(0xC64F1)=240, +cal(0xC64F0)=240)
    0x29CFA  subr  r0,r7              idx  = |v|
    0x29D12  zxb   r22                map key  = idx & 0xFF      -> also gp-0x674b @0x29D14
    0x29DDA  st.h  r7,-0x697a,gp      (idx halfword published)
    0x29DE8  zxh   r7                 Kp  key  = idx & 0xFFFF    (0x29DC6 bank 0xCB994)
    0x29E92  mov   r22,r13            Kd  key  = idx & 0xFF      (0x29E76 bank 0xCB7D4)

  => 1 idx LSB = 2**22 / G / 4 wire counts of 0xE4 STEER_TORQUE = 16.1257 counts at G = 255*255.

This script places the Kp knots (0,68,112,136,208) and the Kd knots (0,11,22,32) on the measured
wire, engaged, split by the four regimes the brief names.  Analysis only; builds nothing.

Run:  python rlog-tools/studies/grind/kpkd_axis_r62_r63.py
"""
import os
import pickle
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402
import grind_incident_r35 as GI               # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
SEL = 7
FW = LG.FW
IMGS = {
    "V289": FW + ("_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-"
                  "NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"),
    "V288": FW + ("_v288r2_V288R2-V282BASE-SPFILT.K4.EINIT-KP.FLAT.Y0-CAVE.R24CMP.B6-SPSIGN.B5-"
                  "MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"),
    "stock": FW + "stock_fw_dump/code.bin",
}
TAG_IMG = {"r62_v289": "V289", "r63_v289": "V289", "r5e_v288": "V288"}
CENSUS_PKL = os.path.join(HERE, "_scratch", "grind1_census_v289_r62_r63_cache.pkl")
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def rec(b, base):
    """The firmware record: n(halfword) X[n] Y[n] pad.  X[0] at base+2, Y[0] at base+2+2n (0x29DDE/0x29DE2)."""
    n = u16(b, base)
    X = np.array([u16(b, base + 2 + 2 * i) for i in range(n)], float)
    Y = np.array([u16(b, base + 2 + 2 * n + 2 * i) for i in range(n)], float)
    return n, X, Y


def cells(name):
    b = open(IMGS[name], "rb").read()
    c = {"img": name}
    for key, bank in (("kp", 0xCB994), ("kd", 0xCB7D4), ("map", 0xC9A88), ("lim", 0xCB844),
                      ("taperS", 0xCB924), ("taperO", 0xCB8B4)):
        base = u32(b, bank + 4 * SEL)
        n, X, Y = rec(b, base)
        c[key] = dict(base=base, n=n, X=X, Y=Y)
    c["clamp_pos"] = b[0xC64F0]
    c["clamp_neg"] = b[0xC64F1]
    c["spF"] = rec(b, 0xC6974)[2]        # tp+0x7974 grab-rate taper; flat 255 => G = taper*255
    return c


def demand(cmd, bar, c):
    """idx and sign, integer-for-integer (0x29032 -> 0x29CFA).  cmd = wire 0xE4 counts, bar = driver torque."""
    LIM = float(c["lim"]["Y"][0])                                     # flat record
    S = np.clip(-4.0 * np.round(cmd), -LIM, LIM)                      # gp-0x69ae then 0x2903A clamp
    same = np.sign(S) == np.sign(bar)
    tx = np.abs(bar) // 32                                            # gp-0x682f
    taper = np.where(same, np.interp(tx, c["taperS"]["X"], c["taperS"]["Y"]),
                     np.interp(tx, c["taperO"]["X"], c["taperO"]["Y"]))
    G = (taper * float(c["spF"][0])).astype(np.int64) & 0xFFFF        # 0x29CB8 andi 0xffff
    v = np.floor(G * S / 65536.0)                                     # 0x29CC0 sar 0x10
    v = np.floor(v / 64.0)                                            # 0x29CD6 sar 0x6
    v = np.clip(v, -float(c["clamp_neg"]), float(c["clamp_pos"]))     # 0x29CDC..0x29CF4
    return np.abs(v), np.where(v < 0, -1.0, 1.0), G


def hist_by_knots(idx, w, knots, hi=241.0):
    edges = list(knots) + [hi]
    out = []
    tot = w.sum()
    for i in range(len(edges) - 1):
        lo, up = edges[i], edges[i + 1]
        m = (idx >= lo) & (idx < up) if i < len(edges) - 2 else (idx >= lo)
        out.append((lo, up, w[m].sum(), (w[m].sum() / tot * 100.0) if tot else 0.0))
    return out


def main():
    pr("=" * 118)
    pr("Kp / Kd SCHEDULE X AXIS -- knots placed on the measured wire (reqaxis, 2026-09-09)")
    pr("=" * 118)

    C = {n: cells(n) for n in IMGS}
    for n, c in C.items():
        pr("  %-6s Kp @0x%X n=%d X=%s Y=%s" % (n, c["kp"]["base"], c["kp"]["n"],
                                               c["kp"]["X"].astype(int).tolist(), c["kp"]["Y"].astype(int).tolist()))
        pr("         Kd @0x%X n=%d X=%s Y=%s" % (c["kd"]["base"], c["kd"]["n"],
                                                 c["kd"]["X"].astype(int).tolist(), c["kd"]["Y"].astype(int).tolist()))
        pr("         map@0x%X n=%d X=%s Y=%s" % (c["map"]["base"], c["map"]["n"],
                                                 c["map"]["X"].astype(int).tolist(), c["map"]["Y"].astype(int).tolist()))
        pr("         LIM=%d  idx clamp +%d/-%d  taperS X%s Y%s  taperO X%s Y%s  spF=%s" % (
            c["lim"]["Y"][0], c["clamp_pos"], c["clamp_neg"],
            c["taperS"]["X"].astype(int).tolist(), c["taperS"]["Y"].astype(int).tolist(),
            c["taperO"]["X"].astype(int).tolist(), c["taperO"]["Y"].astype(int).tolist(),
            c["spF"].astype(int).tolist()))
    pr()

    # ---- the axis in wire units -------------------------------------------------------------------
    Gmax = 255 * 255
    pr("AXIS SCALE (hands-off, taper = 255, spF = 255 => G = %d):" % Gmax)
    pr("  1 idx LSB = 2**22 / G / 4 = %.4f wire counts of 0xE4 STEER_TORQUE" % (2 ** 22 / Gmax / 4.0))
    pr("  idx = 240 (the 0xC64F0 clamp) at |cmd| = %.0f wire counts; the 0xE4 field itself saturates at 3840."
       % (240 * 2 ** 22 / Gmax / 4.0))
    pr("  openpilot slew cap 123 counts/frame  = %.2f idx per 100 Hz frame." % (123 * Gmax * 4 / 2 ** 22))
    pr()
    c289 = C["V289"]
    pr("  KNOTS IN WIRE UNITS  (cmd counts = idx * %.4f ; setpoint from the LIVE map %s)"
       % (2 ** 22 / Gmax / 4.0, c289["map"]["base"] and "0x%X" % c289["map"]["base"]))
    pr("    %-6s %-8s %-12s %-14s %-14s" % ("table", "knot", "idx", "0xE4 counts", "setpoint (map Y)"))
    for lbl, k in (("Kp", c289["kp"]["X"]), ("Kd", c289["kd"]["X"])):
        for i, x in enumerate(k):
            sp = np.interp(x, c289["map"]["X"], c289["map"]["Y"])
            pr("    %-6s X[%d]     %-12.0f %-14.0f %-14.0f" % (lbl, i, x, x * 2 ** 22 / Gmax / 4.0, sp))
    pr()

    # ---- routes -----------------------------------------------------------------------------------
    ep = {}
    if os.path.exists(CENSUS_PKL):
        P = pickle.load(open(CENSUS_PKL, "rb"))
        for e in P["episodes"]:
            ep.setdefault(e["tag"], []).append(e)
        pr("census episodes loaded from %s: %s" % (os.path.basename(CENSUS_PKL),
                                                   {k: len(v) for k, v in ep.items()}))
    pr()

    tags = ["r62_v289", "r63_v289", "r5e_v288"]
    G = {}
    for tag in tags:
        g = C20.load(tag)
        c = C[TAG_IMG[tag]]
        g["idx"], g["sgn"], g["Gg"] = demand(np.round(g["cmd"]), g["bar"], c)
        gi, _ = GI.demand_live(np.round(g["cmd"]), g["bar"], GI.read_cells(IMGS[TAG_IMG[tag]]))
        g["idx_kit"] = gi
        G[tag] = g

    dt = 1.0 / FS
    for tag in tags:
        g = G[tag]
        eng = g["eng"]
        idx = g["idx"]
        v = g["vego"]
        ang = np.abs(g["ang"])
        dcmd = np.abs(np.r_[0.0, np.diff(np.round(g["cmd"]))])
        agree = float(np.mean(np.abs(idx - g["idx_kit"]) < 0.5))
        pr("=" * 118)
        pr("%s  (%s)  %.0f s total, %.0f s engaged;  idx vs the kit's GI.demand_live: %.4f agree"
           % (tag, TAG_IMG[tag], len(g["t"]) * dt, eng.sum() * dt, agree))
        pr("  G distribution engaged: p10 %d p50 %d p90 %d   (max %d);  taper < 255 on %.2f %% of engaged frames"
           % tuple(list(np.percentile(g["Gg"][eng], [10, 50, 90]).astype(int)) +
                   [int(g["Gg"][eng].max()), 100.0 * np.mean(g["Gg"][eng] < Gmax)]))

        regimes = {
            "ALL engaged": eng,
            "(a) capped step |dcmd|>=122": eng & (dcmd >= 122),
            "(b) low-speed turn 2-5 m/s, |ang| 70-140": eng & (v >= 2) & (v <= 5) & (ang >= 70) & (ang <= 140),
            "(c) cruise v>=22 m/s, |ang|<5": eng & (v >= 22) & (ang < 5),
            "(d) idx >= 20": eng & (idx >= 20),
        }
        if tag in ep:
            m = np.zeros(len(g["t"]), bool)
            for e in ep[tag]:
                m[int(e["a"]):int(e["b"])] = True
            regimes["(d') census grind episodes"] = eng & m
            f0 = np.array([e["f0"] for e in ep[tag]])
            pr("  census episodes: n=%d, line f0 p10/p50/p90 = %.1f / %.1f / %.1f Hz"
               % (len(f0), *np.percentile(f0, [10, 50, 90])))

        for lbl, m in regimes.items():
            w = m.astype(float) * dt
            n = w.sum()
            if n < 0.5:
                pr("  %-42s  (%.1f s -- too little)" % (lbl, n))
                continue
            q = np.percentile(idx[m], [10, 50, 90])
            pr("  %-42s  %7.1f s  idx p10/p50/p90 = %5.0f /%5.0f /%5.0f   share idx=0 %.3f"
               % (lbl, n, q[0], q[1], q[2], np.mean(idx[m] == 0)))
            wm = np.full(int(m.sum()), dt)
            rows = hist_by_knots(idx[m], wm, c289["kp"]["X"])
            pr("      Kp knot intervals: " + "  ".join(
                "[%d,%s) %5.1f%%" % (lo, ("%d" % up) if up < 241 else "inf", pc) for lo, up, s, pc in rows))
            rows = hist_by_knots(idx[m], wm, c289["kd"]["X"])
            pr("      Kd knot intervals: " + "  ".join(
                "[%d,%s) %5.1f%%" % (lo, ("%d" % up) if up < 241 else "inf", pc) for lo, up, s, pc in rows))
        pr()

    # ---- pooled V289 -------------------------------------------------------------------------------
    pr("=" * 118)
    pr("POOLED V289 (r62+r63), engaged:")
    idx = np.concatenate([G[t]["idx"][G[t]["eng"]] for t in ("r62_v289", "r63_v289")])
    w = np.full(len(idx), dt)
    for lbl, kn in (("Kp", c289["kp"]["X"]), ("Kd", c289["kd"]["X"])):
        rows = hist_by_knots(idx, w, kn)
        pr("  %s knot intervals: " % lbl + "  ".join(
            "[%d,%s) %.1f%% (%.0f s)" % (lo, ("%d" % up) if up < 241 else "inf", pc, s) for lo, up, s, pc in rows))
    pr("  idx percentiles engaged: " + " ".join("p%d=%.0f" % (p, np.percentile(idx, p))
                                                for p in (5, 10, 25, 50, 75, 90, 95, 99)))
    pr("  share of engaged time with idx <= 32 (the whole Kd schedulable range): %.1f %%"
       % (100.0 * np.mean(idx <= 32)))
    pr("  share of engaged time with idx <  68 (Kp segment 0, X[0]..X[1]):        %.1f %%"
       % (100.0 * np.mean(idx < 68)))

    p = os.path.join(HERE, "_scratch", "kpkd_axis_r62_r63.txt")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("\nwritten: %s" % p)


if __name__ == "__main__":
    main()
