# -*- coding: utf-8 -*-
r"""scalecheck 2026-09-09 -- VERIFICATION of the x4 factor behind the Kp/Kd schedule X axis.

Agent `scalecheck` (subagent of `main`).  Re-derives gp-0x69ae's producer FROM THE BYTES via GhidraMCP
(FUN_00052676, the 0xE4 RX handler) instead of from prior tracer memory, then re-checks the whole
scale chain against an EXACT integer mirror of the disassembly.

Ghidra-verified producer chain (code.bin, byte-identical in the V289 image over 0x526C6-0x526F6):

    0x526C6  jarl 0x00021724,lp     r10 = (u8[gp-0x1428] << 8) | u8[gp-0x1427]   (0xE4 bytes 0,1, BIG-ENDIAN)
    0x526CA  mov  r10,r6
    0x526CC  sxh  r6                r6  = SIGN-EXTEND 16 -> 32          <- STEER_TORQUE is SIGNED
    0x526CE  movea -0x4000,r0,r7    lo  = -16384
    0x526D2  shl  0x2,r6            r6  = raw << 2                      <- the "x4"
    0x526D4  subr r0,r6             r6  = 0 - r6   => -4 * raw          <- the "-"
    0x526D6  movea 0x4000,r0,r8     hi  = +16384
    0x526DA  jarl 0x00049a90,lp     r10 = clamp(r6, lo, hi)             (helper proven a 3-arg clamp)
    0x526F2  st.h r10,-0x69ae[gp]   gp-0x69ae = clamp(-4*raw, +-16384)

    FUN_00049a90:  cmp r8,r7 / cmovgt x3 (orders lo,hi) / cmp r7,r6 / cmovlt / blt / cmp r6,r8 / cmovge
                => return clamp(param1, min(param2,param3), max(param2,param3)).

Run:  python rlog-tools/studies/grind/scalecheck_x4_r62_r63.py
"""
import os
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

FS, SEL = 100.0, 7
FW = LG.FW
IMG289 = FW + ("_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-"
               "NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
IMG288 = FW + ("_v288r2_V288R2-V282BASE-SPFILT.K4.EINIT-KP.FLAT.Y0-CAVE.R24CMP.B6-SPSIGN.B5-"
               "MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
STOCK = os.path.join(os.environ["ACCORD_FIRMWARE_ROOT"], "analysis-2020accord", "stock_fw_dump", "code.bin")
OUT = []


def pr(s=""):
    print(s)
    OUT.append(s)


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def rec(b, addr):
    n = u16(b, addr)
    X = np.array([u16(b, addr + 2 + 2 * i) for i in range(n)], float)
    Y = np.array([u16(b, addr + 2 + 2 * n + 2 * i) for i in range(n)], float)
    return X, Y


def cells(path):
    b = open(path, "rb").read()
    c = {}
    c["lim"] = rec(b, u32(b, 0xCB844 + 4 * SEL))
    c["kp"] = rec(b, u32(b, 0xCB994 + 4 * SEL))
    c["kd"] = rec(b, u32(b, 0xCB7D4 + 4 * SEL))
    c["map"] = rec(b, u32(b, 0xC9A88 + 4 * SEL))
    c["taperS"] = rec(b, u32(b, 0xCB924 + 4 * SEL))
    c["taperO"] = rec(b, u32(b, 0xCB8B4 + 4 * SEL))
    c["spF"] = rec(b, 0xC6974)                       # tp+0x7974  (tp = 0xBF000)
    c["clamp_pos"] = b[0xC64F0]                      # tp+0x74F0
    c["clamp_neg"] = b[0xC64F1]                      # tp+0x74F1
    return c


def ilerp(X, Y, u):
    """LERP mirror; the firmware's divq truncates, np.interp does not -- every table used here is
    flat or piecewise-linear on integer knots, so the difference is at most 1 LSB."""
    return np.interp(np.asarray(u, float), X, Y)


def idx_exact(raw, bar, c):
    """EXACT integer mirror of the disassembly, hop by hop.

    raw = wire 0xE4 STEER_TORQUE, signed 16-bit;  bar = driver torque (gp-0x4f60 domain)."""
    raw = np.asarray(np.round(raw), np.int64)
    # ---- FUN_00052676 (0xE4 RX handler) ----
    S0 = -4 * raw                                                  # 0x526D2 shl 0x2 ; 0x526D4 subr r0,r6
    S0 = np.clip(S0, -0x4000, 0x4000)                              # 0x526DA jarl FUN_00049a90(-0x4000,+0x4000)
    # ---- FUN_00028ea6 ----
    LIM = int(c["lim"][1][0]) & 0xFFFF                             # 0x29036 andi 0xffff  (record is FLAT)
    S = np.clip(S0, -LIM, LIM)                                     # 0x2903A..0x29044
    tx = np.minimum(np.abs(np.asarray(bar, np.int64)) >> 5, 255)   # 0x2904A sar 0x5 (+ abs, cap 255) -> gp-0x682f
    same = np.sign(S0) == np.sign(np.asarray(bar))                 # arm select (both arms near-identical)
    taper = np.where(same, ilerp(*c["taperS"], tx), ilerp(*c["taperO"], tx))
    spF = ilerp(*c["spF"], tx)                                     # FLAT 255
    G = (np.asarray(taper, np.int64) * np.asarray(spF, np.int64)) & 0xFFFF   # 0x29CB4 mulu ; 0x29CB8 andi
    p = G * S                                                      # 0x29CBC mul  (low 32 bits; |p| < 2^31 proven)
    v = p >> 16                                                    # 0x29CC0 sar 0x10   (arithmetic == floor)
    v = v >> 6                                                     # 0x29CD6 sar 0x6
    v = np.clip(v, -int(c["clamp_neg"]), int(c["clamp_pos"]))      # 0x29CDC..0x29CF4
    return np.abs(v), np.where(v < 0, -1.0, 1.0), G


def main():
    C289, C288, CST = cells(IMG289), cells(IMG288), cells(STOCK)

    pr("=" * 118)
    pr("SCALECHECK -- the x4 on gp-0x69ae, re-derived from the bytes")
    pr("=" * 118)
    pr()
    pr("BYTE FACTS (raw LE reads; identical stock vs V289 for every CODE span):")
    sb = open(STOCK, "rb").read()
    vb = open(IMG289, "rb").read()
    for nm, (a, z) in {"0xE4 handler 0x526C6-0x526F6": (0x526C6, 0x526F6),
                       "clamp helper FUN_00049a90": (0x49A90, 0x49AB0),
                       "getter FUN_00021724": (0x21724, 0x21740),
                       "LIM clamp 0x29020-0x29060": (0x29020, 0x29060),
                       "index block 0x29CA8-0x29D20": (0x29CA8, 0x29D20)}.items():
        pr("  %-32s stock == V289: %s" % (nm, sb[a:z] == vb[a:z]))
    pr()
    for nm, c in (("stock", CST), ("V288r2", C288), ("V289", C289)):
        pr("  %-7s  LIM(0xCB844[7]) Y[0] = %d  (flat: %s)" %
           (nm, int(c["lim"][1][0]), bool(np.all(c["lim"][1] == c["lim"][1][0]))))
        pr("           spF(0xC6974) X %s Y %s  (flat 255: %s)" %
           (list(c["spF"][0].astype(int)), list(c["spF"][1].astype(int)), bool(np.all(c["spF"][1] == 255))))
        pr("           idx clamp cals 0xC64F0/0xC64F1 = %d / %d" % (c["clamp_pos"], c["clamp_neg"]))
    pr()

    Gmax = 255 * 255
    scale = 2 ** 22 / Gmax / 4.0
    pr("SCALE, from the verified chain (total right shift 16+6 = 22, wire pre-multiplied by -4):")
    pr("  1 idx LSB = 2**22 / G / 4 = %.6f wire counts of 0xE4 STEER_TORQUE at G = %d" % (scale, Gmax))
    pr("  reqaxis reported 16.1257  ->  %s" % ("CONFIRMED" if abs(scale - 16.1257) < 5e-4 else "DIFFERS"))
    pr()
    pr("  CROSS-CHECK (a) -- where the +-240 index clamp lands vs the wire's own saturation:")
    pr("    idx=240 needs |raw| = %.1f counts" % (240 * scale))
    pr("    handler clamp +-0x4000 = +-16384 = 4 x 4096  (the DBC's stated STEER_TORQUE range +-4096)")
    pr("    stock LIM cal          =  15360 = 4 x 3840  (Honda/openpilot's own STEER_TORQUE max)")
    pr("    => BOTH firmware constants are EXACTLY 4x a wire-domain limit; no other factor does that.")
    for nm, c in (("stock", CST), ("V289", C289)):
        LIM = int(c["lim"][1][0])
        for rawmax in (3840, 4096):
            S = min(4 * rawmax, 16384, LIM)
            pr("    %-6s LIM=%5d  |raw|=%4d -> S=%5d -> v=%3d -> idx=%3d"
               % (nm, LIM, rawmax, S, (Gmax * S) >> 22, min((Gmax * S) >> 22, c["clamp_pos"])))
    pr()

    # ---- CROSS-CHECK (b): exact integer mirror vs the kit's independent GI.demand_live -------------
    pr("  CROSS-CHECK (b) -- EXACT integer mirror vs the kit's GI.demand_live, on the caches:")
    pr("    NOTE: GI.demand_live hard-codes the same '-4.0 * cmd', so this checks the REST of the chain")
    pr("    (clamps, shifts, taper arms, 16-bit masks), NOT the factor itself.  The factor is confirmed")
    pr("    by the disassembly above and by cross-check (a).")
    tags = [("r62_v289", IMG289, C289), ("r63_v289", IMG289, C289), ("r5e_v288", IMG288, C288)]
    for tag, img, c in tags:
        try:
            g = C20.load(tag)
        except Exception as e:                                     # noqa: BLE001
            pr("    %-10s LOAD FAILED: %s" % (tag, e))
            continue
        ix, sg, G = idx_exact(g["cmd"], g["bar"], c)
        gi, _ = GI.demand_live(np.round(g["cmd"]), g["bar"], GI.read_cells(img))
        eng = np.asarray(g["eng"]).astype(bool)
        agree = float(np.mean(np.abs(ix[eng] - gi[eng]) < 0.5))
        pr("    %-10s engaged %6.0f s   exact-int vs GI.demand_live agree = %.4f   (max |diff| = %.0f)"
           % (tag, eng.sum() / FS, agree, np.max(np.abs(ix[eng] - gi[eng]))))
        m = eng & (G == Gmax) & (np.abs(np.round(g["cmd"])) > 200)
        if m.sum() > 100:
            r = np.abs(np.round(np.asarray(g["cmd"])))[m] / np.maximum(ix[m], 1)
            pr("               empirical counts-per-idx-LSB on %d hands-off frames: p50 %.3f (want %.3f)"
               % (m.sum(), np.median(r), scale))
        pr("               G engaged p10/p50/p90 = %d/%d/%d ; taper<255 on %.2f %% of engaged frames"
           % tuple(list(np.percentile(G[eng], [10, 50, 90]).astype(int)) + [100.0 * np.mean(G[eng] < Gmax)]))
    pr()
    pr("KNOTS IN WIRE UNITS (unchanged -- the factor stands):")
    pr("  %-5s %-6s %-6s %-12s" % ("table", "knot", "idx", "0xE4 counts"))
    for lbl, k in (("Kp", C289["kp"][0]), ("Kd", C289["kd"][0])):
        for i, x in enumerate(k):
            pr("  %-5s X[%d]   %-6.0f %-12.0f" % (lbl, i, x, x * scale))

    dst = os.path.join(HERE, "_scratch", "scalecheck_x4_r62_r63.txt")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    print("\nwrote %s" % dst)


if __name__ == "__main__":
    main()
