# -*- coding: utf-8 -*-
"""studies/grind/h1_table_resolution.py -- TEST OF COLLEAGUE HYPOTHESIS H1 (2026-09-09, subagent `hyptable`):
"OP is just switching between two points on that torque table; as you scale it they get further apart, so
you lose resolution."   ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing.

Four readings, each tested against the BYTES and the WIRE:
  A  IMAGE   the EPS assist map 0xC9A88 (slot 7 -> 0xE502C), stock / V112 / V282 / V289: knots, the LERP mirrored
             in integer Python from the disassembly of 0x29CB4-0x29D6C (mulu/andi/mul/sar/sar/clamp/abs, then the
             knot walk + divq), the index quantisation (raw 0xE4 counts per idx LSB), the setpoint LSB in deg/s,
             the per-idx setpoint and torque step through Kp 248 and the gain 5346>>15, the truncation ripple.
  B  OPENPILOT  the fork's own "torque table" on the Accord path (torqueBP/torqueV -> STEER_LOOKUP, np.interp,
             int(), rate_limit 0.03/frame): can any scaled table there dither between two points?
  C  WIRE    r39 (V282) and r5e_v288 (V288 rev 2; map + loop byte-identical to V282/V289): raw 0xE4 on its own
             dejittered 100 Hz clock: |dcmd| histogram in grinding vs baseline, +-1 sign-alternation runs, the
             fraction of 100 ms windows on exactly two command values / two idx values / one idx value, the idx
             bin-crossing rate, and the QUANTISATION RESIDUAL of the map (staircase minus continuous) pushed
             through P and the gain and compared with the measured 18-22 Hz torque on the tap in the same windows.
             Census windows (2 s / 0.5 s step, present = 15-26 Hz prominence >= 8 AND bar 18-22 >= 40 raw) are
             grind1_census_v282.py's recipe via wire_0xe4_20hz.episodes_of -- the same yardstick as the record.
  D  RECORD  what H1 predicts for the line's frequency / presence vs map scale and Kp, against the mode-nature
             census on disk (loopshape20_mode_nature.txt) and the ledger's stock-map-era evidence.

Run: python h1_table_resolution.py     (writes _scratch/h1_table_resolution.txt beside it)
"""
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import grind_incident_r35 as GI               # noqa: E402
import wire_0xe4_20hz as W                    # noqa: E402  (has a __main__ guard; we reuse load_route / episodes_of)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FW = os.environ["ACCORD_FIRMWARE_ROOT"] + "/analysis-2020accord/"
IMAGES = {
    "stock": "stock_fw_dump/code.bin",
    "V112": "_v112_V112-V111BASE-RELAY.KNEE1800.K1.612_plain_image.bin",
    "V282": "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
    "V289": "_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-NOTCHCMP.B7-"
            "MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
}
SEL = 7                       # live variant selector (record 11 TVCA4, measured on the wire)
FS = 100.0
LO, HI = 18.0, 22.0
W2, STEP = 200, 50
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def rec(b, base, n):
    """firmware LERP record: hdr@+0 (= n), X[n]@+2, Y[n]@+2+2n, all u16 LE."""
    return [u16(b, base + 2 + 2 * i) for i in range(n)], [u16(b, base + 2 + 2 * n + 2 * i) for i in range(n)]


# ======================================================================================================
# A. the firmware arithmetic, mirrored exactly (stock code.bin, dry-run disassembly 0x29CB0-0x29D7C)
# ======================================================================================================
def idx_of_cmd(cmd, taper=254, speedF=255, limit=16384, idx_clamp=240):
    """0x29032..0x29CFA: raw 0xE4 command -> map index.  -4*cmd is the CAN decode stage of the kit's standing
    mirror (v280_map_profiles.demand); taper 254 = the same-sign taper LERP below |bar| 70*32; speedF 255."""
    S = max(-limit, min(limit, -4 * int(cmd)))    # 0x29032 ld.h ; +-L clamp 0x29036-0x29044
    r7 = (taper * speedF) & 0xFFFF                # 0x29CB4 mulu ; 0x29CB8 andi 0xffff
    r7 = (r7 * S) >> 16                           # 0x29CBC mul  ; 0x29CC0 sar 0x10   (arithmetic)
    r7 = r7 >> 6                                  # 0x29CD6 sar 0x6
    r7 = max(-idx_clamp, min(idx_clamp, r7))      # 0x29CDC-0x29CF4 clamp to +-cal(0xC64F0)=240
    return abs(r7)                                # 0x29CF6 cmp / 0x29CFA subr


def lerp_fw(X, Y, idx):
    """0x29D18-0x29D68: the memoryless knot walk.  Y[k] + ((idx-X[k])*(Y[k+1]-Y[k])) divq (X[k+1]-X[k]);
    divq is a signed integer divide truncating toward zero; every operand is >= 0 here so it is a floor."""
    idx = int(idx)
    if idx <= X[0]:                               # 0x29D22 cmp r10,r9 ; bh  -> not higher: Y[0]
        return Y[0]
    if idx >= X[-1]:                              # 0x29D2E cmp r13,r9 ; bnc -> Y[n-1]
        return Y[-1]
    k = 0
    while idx >= X[k + 1]:                        # 0x29D36 / 0x29D48 cmp ; bnc  (walk while idx >= X[k+1])
        k += 1
    return Y[k] + ((idx - X[k]) * (Y[k + 1] - Y[k])) // (X[k + 1] - X[k])   # 0x29D58 sub, 0x29D5C sub, 0x29D5E mul, 0x29D62 sub, 0x29D64 divq, 0x29D68 add


def lerp_cont(X, Y, x):
    return float(np.interp(x, X, Y))


def section_A():
    pr("=" * 110)
    pr("A. THE BYTES -- assist map 0xC9A88[7] -> 0xE502C, LERP mirrored from 0x29CB4-0x29D6C (stock code.bin dry-run disasm)")
    pr("=" * 110)
    maps = {}
    for name, f in IMAGES.items():
        b = open(FW + f, "rb").read()
        p = u32(b, 0xC9A88 + 4 * SEL)
        X, Y = rec(b, p, 10)
        kX, kY = rec(b, u32(b, 0xCB994 + 4 * SEL), 5)
        dX, dY = rec(b, u32(b, 0xCB7D4 + 4 * SEL), 4)
        c = dict(X=X, Y=Y, kpX=kX, kpY=kY, kdY=dY, idx_clamp=b[0xC64F0], fb_clamp=u16(b, 0xC62E6),
                 p_clamp=u16(b, 0xC61BC), d_clamp=u16(b, 0xC61B6), sum_clamp=u16(b, 0xC61BE), out_clamp=u16(b, 0xC61B4),
                 fb_a=u16(b, 0xC63E8), fb_b=u16(b, 0xC63EA), rec_at=p)
        maps[name] = c
        pr("%-6s map @%X  X=%s" % (name, p, X))
        pr("       Y=%s   Kp Y=%s  Kd=%s  idx clamp %d  fb clamp %d  fb pole %d/%d" %
           (Y, kY, dY, c["idx_clamp"], c["fb_clamp"], c["fb_a"], c["fb_b"]))
    same = all(maps[n]["X"] == maps["stock"]["X"] for n in maps)
    pr("X knots identical across stock/V112/V282/V289: %s   (V282 == V289 map: %s)" %
       (same, maps["V282"]["Y"] == maps["V289"]["Y"]))
    pr()
    # ---- index quantisation: raw 0xE4 counts per idx LSB -- independent of the map -------------------
    pr("A1. INDEX QUANTISATION (the only quantisation the command meets before the map) -- MAP-INDEPENDENT")
    cmds = np.arange(0, 4097)
    idx = np.array([idx_of_cmd(c) for c in cmds])
    edges = np.flatnonzero(np.diff(idx) != 0) + 1
    widths = np.diff(edges)
    pr("  idx = ((254*255 & 0xFFFF) * clip(-4*cmd, +-16384)) >> 16 >> 6, |.|, clamp 240")
    pr("  exact: 1 idx LSB = 2^22 / (64770*4) = %.3f raw 0xE4 counts;  idx 240 reached at cmd = %d;  idx==0 for |cmd| <= %d" %
       (2 ** 22 / (64770 * 4), int(np.flatnonzero(idx >= 240)[0]), int(edges[0] - 1)))
    pr("  measured bin widths over cmd 0..4096: %d bins, width %d..%d counts (median %d)" %
       (len(widths), widths.min(), widths.max(), int(np.median(widths))))
    pr("  => the command is quantised to ~16 raw counts (0.40 %% of 4096) BEFORE the map, identically on every build.")
    pr()
    # ---- per-idx setpoint step, LSB in deg/s, torque step -------------------------------------------
    FB_DC = 2 * 1560 / (1024 - 923)          # 30.89 E-units per raw rate count (V282 pole; V289 875/2301 -> 30.886)
    CPD = 8.0                                # raw 0x18F counts per deg/s
    sp_lsb_degs = 32.0 / (FB_DC * CPD)
    pr("A2. SETPOINT LSB: E = 32*sp - fb, fb DC = %.2f per raw rate count, 8 raw/deg/s  => 1 sp count = %.4f deg/s (every build)" %
       (FB_DC, sp_lsb_degs))
    pr("    torque per sp count through P: (32*248)>>8 = %d E->P counts, x5346>>15 = %.2f output counts (out clamp 3072, tap LSB 8)" %
       ((32 * 248) >> 8, ((32 * 248) >> 8) * 5346 / 32768))
    pr()
    pr("A3. PER-IDX SETPOINT STEP (sp counts and deg/s), PER BREAKPOINT INTERVAL, and the per-idx torque step (P only, Kp 248, gain 5346>>15):")
    pr("    %-10s %-8s | %-22s | %-22s | %-22s" % ("interval", "d(cmd)", "stock  dsp  deg/s  Tout", "V282/V289 dsp deg/s Tout", "V112 (=stock map)"))
    X = maps["stock"]["X"]
    for k in range(len(X) - 1):
        row = "    %3d-%-6d %6.0f   |" % (X[k], X[k + 1], (X[k + 1] - X[k]) * 16.19)
        for n in ("stock", "V282", "V112"):
            Y = maps[n]["Y"]
            s = (Y[k + 1] - Y[k]) / (X[k + 1] - X[k])
            tout = 32 * s * 248 / 256 * 5346 / 32768
            row += " %5.3f  %6.3f  %6.2f  |" % (s, s * sp_lsb_degs, tout)
        pr(row)
    pr("    (V282 Y/X = 1032/240 = 4.30 on every interval -- a straight line; stock is concave, 2.0 -> 0.075 sp/idx)")
    pr()
    # ---- truncation ripple of the integer LERP ---------------------------------------------------------
    pr("A4. INTEGER-LERP TRUNCATION (divq floors): sp_fw(idx) - sp_exact(idx) over idx 0..240, and the per-idx step multiset")
    for n in ("stock", "V282"):
        X, Y = maps[n]["X"], maps[n]["Y"]
        spf = np.array([lerp_fw(X, Y, i) for i in range(241)])
        spx = np.array([lerp_cont(X, Y, i) for i in range(241)])
        d = np.diff(spf)
        vals, cnt = np.unique(d, return_counts=True)
        pr("  %-5s ripple min/max %.2f/%.2f sp counts (%.4f/%.4f deg/s); per-idx steps: %s" %
           (n, (spf - spx).min(), (spf - spx).max(), (spf - spx).min() * sp_lsb_degs, (spf - spx).max() * sp_lsb_degs,
            ", ".join("%d x%d" % (v, c) for v, c in zip(vals, cnt))))
        # relative resolution: step / value at a few idx
        pr("        relative step dsp/sp at idx 6/12/30/60/120/200: %s" %
           "  ".join("%.3f" % (d[i - 1] / max(1, spf[i])) for i in (6, 12, 30, 60, 120, 200)))
    pr("  => the truncation error is bounded by ONE sp count on both maps; relative to the setpoint it is 6x SMALLER on the 6x map.")
    pr("  => a knot is a slope change, not a jump: the LERP is continuous, so 'straddling a breakpoint' moves sp by the local slope only.")
    pr()
    # ---- what a 1-idx step does to the D term (the honest cost of a coarser map) ----------------------
    pr("A5. THE ONE REAL COST OF SCALE: a 1-idx command step is a 1-tick E step of 32*dsp -> D = (dE*128)>>3 for ONE 1 kHz tick")
    for n, dsp in (("stock @idx<12", 2), ("stock @idx 32-64", 1.19), ("V282 any idx", 4.3)):
        dE = 32 * dsp
        D = (dE * 128) / 8
        pr("  %-18s dE %6.0f  D one-tick %6.0f (clamp 10240)  x gain -> %5.0f out counts for 1 ms, then the 5.05 Hz output lag (x~0.03 at 1 tick)" %
           (n, dE, D, D * 5346 / 32768))
    pr("  and a slew-capped frame (123 raw = 7.6 idx): dE = %d (V282) vs %d (stock @low idx): the cap, not the LSB, sets the kick." %
       (int(32 * 4.3 * 7.6), int(32 * 2 * 7.6)))
    return maps


# ======================================================================================================
# B. the openpilot side (read from the operator's fork, values quoted in the report with file refs)
# ======================================================================================================
def section_B():
    pr("=" * 110)
    pr("B. THE OPENPILOT SIDE -- is there a table on the Accord path that can dither between two points?")
    pr("=" * 110)
    torqueBP, torqueV = [0, 4096], [0, 4096]     # opendbc honda/interface.py, CAR.HONDA_ACCORD branch
    BP = [-v for v in torqueBP][1:][::-1] + torqueBP
    V = [-v for v in torqueV][1:][::-1] + torqueV
    pr("  interface.py HONDA_ACCORD: torqueBP %s torqueV %s -> STEER_MAX %d, STEER_LOOKUP_BP %s / V %s" % (torqueBP, torqueV, torqueBP[-1], BP, V))
    x = np.linspace(-1, 1, 20001)
    y = np.interp(-x * 4096, BP, V)
    pr("  np.interp over the whole range: max |interp(u) - u| = %.3g  => IDENTITY. int() then truncates toward zero: 1 LSB = 1/4096 = %.4f %%" %
       (np.max(np.abs(y + x * 4096)), 100 / 4096))
    up = 3 * 0.01
    pr("  rate_limit(torque, last, -%.2f, +%.2f) per 10 ms frame -> %.2f raw counts/frame (the 123-count cap the wire study measured)" % (up, up, up * 4096))
    pr("  latcontrol_torque.py: every np.interp on the Accord path is indexed by SPEED (KP_INTERP, LOW_SPEED, roll-offset fade) or by")
    pr("  |setpoint| lat-accel (center-chatter weight) -- continuous piecewise-linear maps of slowly varying inputs; none is indexed by the")
    pr("  command itself, so none can alternate between two knots at 100 Hz.")
    pr("  => 'scaling the torque table' on the openpilot side is a no-op: the Accord's table is the 2-point identity [0,4096]->[0,4096].")
    pr()


# ======================================================================================================
# C. the wire
# ======================================================================================================
def win_stats(g, e, a, b, X6, Y6, Xs, Ys):
    """per 2-s census window on the 18F axis [a,b): bar line, the raw command's cadence on the e4 grid, idx cadence,
    and the map quantisation residual pushed to output counts (V282 map and stock map on the same command)."""
    ta, tb = g["t"][a], g["t"][b - 1]
    ka = int(np.searchsorted(e["tgrid"], ta)); kb = int(np.searchsorted(e["tgrid"], tb))
    if kb - ka < 150:
        return None
    have = e["have"][ka:kb]
    if have.mean() < 0.9:
        return None
    cmd = np.round(e["grid"][ka:kb]).astype(int)
    bar_e = np.interp(e["tgrid"][ka:kb], g["t"], g["bar"])
    idx, sgn = GI.demand_live(cmd, bar_e, CELLS)
    idx = idx.astype(int)
    d = np.diff(cmd)
    di = np.diff(idx)
    f0, prom, _, _ = GI.line_of(g["bar"][a:b], FS, 15.0, 26.0)
    amp = GI.band(g["bar"][a:b], LO, HI, FS)
    present = (prom >= 8) and (amp >= 40)
    # +-1 alternation: consecutive nonzero steps of opposite sign, both |d| <= 2
    alt = (d[1:] * d[:-1] < 0) & (np.abs(d[1:]) <= 2) & (np.abs(d[:-1]) <= 2)
    # 100 ms windows on exactly two command values / two idx values / one idx value
    n10 = (kb - ka) // 10
    c10 = cmd[:n10 * 10].reshape(n10, 10); i10 = idx[:n10 * 10].reshape(n10, 10)
    nvals_c = np.array([len(np.unique(r)) for r in c10]); nvals_i = np.array([len(np.unique(r)) for r in i10])
    # knot crossings of idx (any knot of the map X between consecutive idx)
    knots = np.array(X6[1:-1])
    cross = np.sum([(np.minimum(idx[:-1], idx[1:]) < kx) & (np.maximum(idx[:-1], idx[1:]) >= kx) for kx in knots], axis=0)
    # quantisation residual of the map: staircase (integer idx + integer LERP) minus the continuous map of the continuous index
    cont_idx = np.abs(np.clip(-4.0 * cmd, -16384, 16384)) * 64770 / 65536.0 / 64.0
    cont_idx = np.minimum(cont_idx, 240.0)
    sp6 = np.array([lerp_fw(X6, Y6, i) for i in idx]) * sgn
    sp6c = np.interp(cont_idx, X6, Y6) * sgn
    sps = np.array([lerp_fw(Xs, Ys, i) for i in idx]) * sgn
    spsc = np.interp(cont_idx, Xs, Ys) * sgn
    gain_out = 248 / 256 * 5346 / 32768 * 32          # E -> P -> output counts, per sp count
    q6 = (sp6 - sp6c) * gain_out
    qs = (sps - spsc) * gain_out
    Tw = g["T100"][a:b]
    return dict(f0=f0, prom=prom, amp=amp, present=present, n=len(cmd),
                v=float(np.median(g["vego"][a:b])), bar=float(np.median(np.abs(g["bar"][a:b]))),
                idxmed=float(np.median(idx)), cmdmed=float(np.median(np.abs(cmd))),
                h=np.histogram(np.abs(d), bins=[0, 1, 2, 3, 8, 16, 64, 122, 10 ** 6])[0],
                alt_frac=float(alt.mean()), alt_maxrun=int(max([len(s) for s in "".join("1" if v else "0" for v in alt).split("0")] + [0])),
                two_c=float(np.mean(nvals_c == 2)), two_i=float(np.mean(nvals_i == 2)), one_i=float(np.mean(nvals_i == 1)),
                idx_change_duty=float(np.mean(di != 0)), idx_cross_rate=float(np.sum(di != 0) / (len(cmd) / FS)),
                knot_rate=float(cross.sum() / (len(cmd) / FS)),
                q6_band=GI.band(q6, LO, HI, FS), q6_hf=GI.band(q6, 30.0, 49.0, FS), q6_rms=float(np.std(q6)),
                qs_band=GI.band(qs, LO, HI, FS), qs_rms=float(np.std(qs)),
                cmd_band=GI.band(cmd.astype(float), LO, HI, FS), cmd_hf=GI.band(cmd.astype(float), 30.0, 49.0, FS),
                T_band=GI.band(Tw, LO, HI, FS), rate_band=GI.band(g["wire"][a:b], LO, HI, FS))


def q(v, p):
    return np.percentile(v, p) if len(v) else np.nan


def section_C(maps):
    pr("=" * 110)
    pr("C. THE WIRE -- r39 (V282) and r5e_v288 (V288 rev 2): does 0xE4 'switch between two points'?")
    pr("=" * 110)
    X6, Y6 = maps["V282"]["X"], maps["V282"]["Y"]
    Xs, Ys = maps["stock"]["X"], maps["stock"]["Y"]
    allw = []
    for tag in ("r39", "r5e_v288"):
        g = W.load_route(tag, CELLS)
        e = g["e4"]
        eps, hot = W.episodes_of(g)
        inep = np.zeros(len(g["t"]), bool)
        for a, b, _ in eps:
            inep[a:b] = True
        pr("route %s: engaged %.0f s, %d episodes (%.1f s), e4 frames %d, dejitter resid p50 %.1f ms" %
           (tag, g["eng"].sum() / FS, len(eps), inep.sum() / FS, e["K"] + 1, 1e3 * np.percentile(e["resid"], 50)))
        rows = []
        for aa, bb in C20.runs(g["eng"], W2):
            for s in range(aa, bb - W2 + 1, STEP):
                r = win_stats(g, e, s, s + W2, X6, Y6, Xs, Ys)
                if r is None:
                    continue
                r["grind"] = bool(inep[s:s + W2].mean() > 0.5)
                r["tag"] = tag
                rows.append(r)
        allw += rows
        G = [r for r in rows if r["grind"]]
        B = [r for r in rows if not r["grind"] and r["v"] < 12 and r["bar"] < 400]
        Ball = [r for r in rows if not r["grind"]]
        pr("  windows: %d total, %d grinding (episode-majority), %d matched baseline (engaged, v<12 m/s, |bar|<400), %d all-baseline" %
           (len(rows), len(G), len(B), len(Ball)))
        for lab, S in (("GRINDING", G), ("BASELINE matched", B), ("BASELINE all", Ball)):
            if not S:
                continue
            H = np.sum([r["h"] for r in S], axis=0); H = H / H.sum()
            pr("  %-17s |dcmd| histogram  0:%.3f 1:%.3f 2:%.3f 3-7:%.3f 8-15:%.3f 16-63:%.3f 64-121:%.3f >=122(cap):%.3f" % ((lab,) + tuple(H)))
            pr("  %-17s +-1 alternation frac p50/p90 %.3f/%.3f, longest alternating run p50/p90/max %d/%d/%d frames" %
               (lab, q([r["alt_frac"] for r in S], 50), q([r["alt_frac"] for r in S], 90),
                q([r["alt_maxrun"] for r in S], 50), q([r["alt_maxrun"] for r in S], 90), max(r["alt_maxrun"] for r in S)))
            pr("  %-17s 100 ms windows: exactly-2 cmd values %.3f, exactly-2 idx values %.3f, ONE idx value %.3f (p50 of window fractions)" %
               (lab, q([r["two_c"] for r in S], 50), q([r["two_i"] for r in S], 50), q([r["one_i"] for r in S], 50)))
            pr("  %-17s idx change duty p50 %.3f, idx bin-crossing rate p10/p50/p90 %.1f/%.1f/%.1f /s, knot-crossing rate p50 %.2f /s" %
               (lab, q([r["idx_change_duty"] for r in S], 50), q([r["idx_cross_rate"] for r in S], 10), q([r["idx_cross_rate"] for r in S], 50),
                q([r["idx_cross_rate"] for r in S], 90), q([r["knot_rate"] for r in S], 50)))
            pr("  %-17s cmd 18-22 amp p50 %.1f, cmd 30-49 amp p50 %.1f (raw); bar 18-22 p50 %.0f; tap T 18-22 p50 %.1f counts; rate 18-22 p50 %.1f raw" %
               (lab, q([r["cmd_band"] for r in S], 50), q([r["cmd_hf"] for r in S], 50), q([r["amp"] for r in S], 50),
                q([r["T_band"] for r in S], 50), q([r["rate_band"] for r in S], 50)))
            pr("  %-17s MAP QUANTISATION RESIDUAL -> output counts: V282 map rms p50 %.2f, 18-22 amp p50 %.2f (30-49: %.2f); stock map rms %.2f, 18-22 %.2f" %
               (lab, q([r["q6_rms"] for r in S], 50), q([r["q6_band"] for r in S], 50), q([r["q6_hf"] for r in S], 50),
                q([r["qs_rms"] for r in S], 50), q([r["qs_band"] for r in S], 50)))
            if lab == "GRINDING":
                ratio = [r["T_band"] / max(r["q6_band"], 1e-6) for r in S]
                pr("  %-17s measured tap 18-22 / quantisation-residual 18-22 (open loop, V282 map): p10/p50/p90 = %.0f/%.0f/%.0f  (Ms bound x3.8 leaves %.0f/%.0f/%.0f)" %
                   (lab, q(ratio, 10), q(ratio, 50), q(ratio, 90), q(ratio, 10) / 3.8, q(ratio, 50) / 3.8, q(ratio, 90) / 3.8))
        # within-route: line presence & amplitude vs how much the idx moved in the window
        pr("  line vs idx motion (all engaged windows, this route):")
        for lab, lo, hi in (("idx FROZEN (0 changes)", -1, 0), ("1-5 changes", 0, 5), ("6-20", 5, 20), ("21-60", 20, 60), (">60 changes", 60, 10 ** 9)):
            S = [r for r in rows if lo < r["idx_cross_rate"] * 2 <= hi]
            if not S:
                pr("    %-24s n=0" % lab); continue
            pr("    %-24s n=%4d  present %.3f  bar 18-22 p50/p90 %.0f/%.0f  f0 p50 %.2f  v p50 %.1f  |bar| p50 %.0f" %
               (lab, len(S), np.mean([r["present"] for r in S]), q([r["amp"] for r in S], 50), q([r["amp"] for r in S], 90),
                np.nanmedian([r["f0"] for r in S if r["present"]]) if any(r["present"] for r in S) else np.nan,
                q([r["v"] for r in S], 50), q([r["bar"] for r in S], 50)))
        # H1's frequency prediction: a ramp through idx bins tones at the bin-crossing rate
        G2 = [r for r in G if r["present"]]
        if G2:
            xr = np.array([r["idx_cross_rate"] for r in G2]); f0 = np.array([r["f0"] for r in G2])
            from scipy import stats
            rho, p = stats.spearmanr(xr, f0)
            pr("  in grinding windows: idx bin-crossing rate p10/p50/p90 = %.1f/%.1f/%.1f /s vs line f0 p10/p50/p90 = %.2f/%.2f/%.2f Hz; Spearman rho %.2f (p %.3f)" %
               (q(xr, 10), q(xr, 50), q(xr, 90), q(f0, 10), q(f0, 50), q(f0, 90), rho, p))
        pr()
    np.savez(os.path.join(SCR, "h1_table_resolution_windows.npz"),
             **{k: np.array([r[k] for r in allw]) for k in allw[0] if k not in ("h",)},
             h=np.array([r["h"] for r in allw]))
    return allw


def section_D():
    pr("=" * 110)
    pr("D. THE RECORD -- what H1 predicts vs what the census on disk shows")
    pr("=" * 110)
    pr("H1 predicts: (i) excitation amplitude proportional to the map scale (stock 1x -> x2 -> x6): no line, or a ~6x smaller one, on the")
    pr("  stock-map builds; (ii) a frequency set by the command's dwell/dither cadence (50 Hz for a strict two-value alternation, the")
    pr("  bin-crossing rate for a ramp, broadband for random dwell) -- i.e. moving with command slope and speed, not fixed; (iii) nothing")
    pr("  when the idx is frozen inside a window; (iv) independence from the loop gain Kp (the quantiser sits before the loop).")
    f = os.path.join(SCR, "loopshape20_mode_nature.txt")
    if os.path.exists(f):
        txt = open(f, encoding="utf-8", errors="replace").read().splitlines()
        pr("loopshape20_mode_nature.txt (on disk, 2026-09-08) -- f0 by build (map x2 concave on V278r3; x6 linear on V280r2/V281r3/V282/V288):")
        for ln in txt:
            if ln.strip().startswith(("V278r3  f0", "V280r2  f0", "V281r3  f0", "V282    f0", "V288    f0")) or \
               ln.strip().startswith(("Kp-LERP  Kp", "flat-Kp  idx")):
                pr("  " + ln.rstrip())
    pr("ledger (GRINDING-ROOT-CAUSE-LEDGER-2026-09-03.md, grind #1 row): the 18-22 Hz band is named in the V62 era and 21-26 Hz in the")
    pr("  V112 era -- both STOCK MAP (x1) -- and r97 (stock creep) carries 29 raw in the band vs ~113-146 raw pooled on x2/x6 builds.")


if __name__ == "__main__":
    os.makedirs(SCR, exist_ok=True)
    CELLS = GI.read_cells(FW + IMAGES["V282"])
    maps = section_A()
    section_B()
    section_C(maps)
    section_D()
    open(os.path.join(SCR, "h1_table_resolution.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("wrote " + os.path.join(SCR, "h1_table_resolution.txt"))
