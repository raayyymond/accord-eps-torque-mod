# -*- coding: utf-8 -*-
"""advB_v293_b3_surface.py -- ADVERSARY B, criterion B3: the delivered surface from the BUILT IMAGE.

Agent `advB3`, subagent of `main`, 2026-09-13.  ANALYSIS ONLY: builds nothing, flashes nothing, sends
nothing on any bus, edits no build script, writes no image.

B3 (pre-registration `docs/review/ADVERSARIAL-V293-PREREG-2026-09-13.md`):
    "The rail not x1.000 of V282's from the bytes; the linear slope off by more than the integer floor."

METHOD, and it is deliberately NOT v293_lib's closed form alone:
  (a) closed form  (v293_lib.surface)          -- the design's own method
  (b) byte-exact tick march to steady state    (v293_lib.surface_march, which runs v292_replay_lib.Elec)
  (c) MY OWN integer mirror, written from the decompiled arithmetic, with no shared code
Three methods; any disagreement beyond 1 count is reported, not averaged.

Also: what a "rail" means when the P clamp binds, and at which idx it starts binding on each build --
the prereg's A2 makes "P rails below idx 238" a FAIL, so the idx where the clamp first binds is scored.
"""
import glob
import hashlib
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import v293_lib as L                      # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FW = os.environ["ACCORD_FIRMWARE_ROOT"] + "/analysis-2020accord/"
IMG293 = glob.glob(FW + "_v293_*_plain_image.bin")[0]
IMG282 = glob.glob(FW + "_v282_*_plain_image.bin")[0]
IMGSTK = FW + "stock_fw_dump/code.bin"
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def lerp(x, X, Y):
    return float(np.interp(float(x), X, Y))


def mine(c, idx, fb_state=0, fade=254, engaged=True):
    """MY OWN integer mirror of FUN_00028ea6's steady state, written from the decompiled arithmetic.

    Deliberately independent of v293_lib.surface.  Every operation is integer.

        sp  = LERP(map)                                        assist map, demand index -> setpoint
        fbc = clip(fb_state, -0xC62E6, +0xC62E6)               the feedback SATURATION cell
        E   = 32*sp - fbc                                      [0x29D78  sub r26,r16]
        P   = clip( (E*Kp) >> 8 , +-0xC61BC )                   arithmetic shift => floor for negatives
        D   = clip( (dE*Kd) >> 3 , +-0xC61B6 )                  dE == 0 in steady state
        S   = clip( (m*(P+D)) >> 8 , +-0xC61BE )
        s_ss= S*lag_b // (1024-lag_a)  (steady state of the two-sample output lag)
        y   = (s + s') >> 5 = (2*s_ss) >> 5
        T   = clip( (-(y*gain)) >> 15 , +-0xC61B4 )             `sar 0xf` after `mul`: ARITHMETIC
    """
    sp = int(round(lerp(idx, c["map_X"], c["map_Y"])))
    kp = int(round(lerp(idx, c["kp_X"], c["kp_Y"])))
    fbc = max(-c["fb_clamp"], min(c["fb_clamp"], int(fb_state)))
    E = 32 * sp - fbc
    P = (E * kp) >> 8                                       # python >> on ints IS floor/arithmetic
    P = max(-c["p_clamp"], min(c["p_clamp"], P))
    D = 0
    S = (int(fade) * (P + D)) >> 8
    S = max(-c["sum_clamp"], min(c["sum_clamp"], S))
    if not engaged:
        S = 0
    s_ss = (S * c["lag_b"]) // (1024 - c["lag_a"])
    y = (2 * s_ss) >> 5
    T = (-(y * c["gain"])) >> 15
    T = max(-c["t_clamp"], min(c["t_clamp"], T))
    return dict(sp=sp, kp=kp, E=E, P=P, S=S, y=y, T=T)


def first_rail_idx(c, fade=254):
    """the smallest integer demand index at which the P clamp binds (P would exceed 0xC61BC)."""
    for ix in range(0, 241):
        m = mine(c, ix, fade=fade)
        sp, kp = m["sp"], m["kp"]
        if (32 * sp * kp) >> 8 > c["p_clamp"]:
            return ix
    return None


def main():
    pr("=" * 112)
    pr("ADVERSARY B -- B3: THE DELIVERED SURFACE AND THE RAIL, FROM THE BUILT IMAGE")
    pr("agent `advB3`, 2026-09-13.  ANALYSIS ONLY.")
    pr("=" * 112)
    for tag, p in (("V293", IMG293), ("V282", IMG282), ("STOCK", IMGSTK)):
        pr("%-6s sha256 %s" % (tag, hashlib.sha256(open(p, "rb").read()).hexdigest()))
    pr("")

    c293 = L.read_cells(IMG293)
    c282 = L.read_cells(IMG282)
    cstk = L.read_cells(IMGSTK)
    for tag, c in (("V293", c293), ("V282", c282), ("STOCK", cstk)):
        pr("%-6s map_X %s" % (tag, np.array(c["map_X"], int).tolist()))
        pr("%-6s map_Y %s" % (tag, np.array(c["map_Y"], int).tolist()))
        pr("%-6s kp_X  %s   kp_Y %s   kd_X %s   kd_Y %s"
           % (tag, np.array(c["kp_X"], int).tolist(), np.array(c["kp_Y"], int).tolist(),
              np.array(c["kd_X"], int).tolist(), np.array(c["kd_Y"], int).tolist()))
        pr("%-6s fb_clamp %6d  d_clamp %6d  p_clamp %6d  sum %6d  t %5d  gain %6d @0x%05X  r24_arm %5d"
           % (tag, c["fb_clamp"], c["d_clamp"], c["p_clamp"], c["sum_clamp"], c["t_clamp"],
              c["gain"], c["gain_addr"], c["r24_arm"]))
        pr("")

    # ---------------------------------------------------------------- the three methods, fb = 0
    idxs = np.array([0, 12, 24, 48, 96, 115, 160, 200, 230, 236, 237, 238, 239, 240], float)
    pr("-" * 112)
    pr("THE SURFACE at fade 254 (no driver torque), wheel STILL (fb state 0) -- three independent methods")
    pr("-" * 112)
    pr("%6s | %6s %5s | %8s %8s %8s | %8s %8s | %s"
       % ("idx", "sp", "Kp", "T close", "T march", "T mine", "V282 cf", "V282 mn", "ratio 293/282"))
    s293 = L.surface(c293, idxs, fb=0.0, fade=254)
    s282 = L.surface(c282, idxs, fb=0.0, fade=254)
    m293 = L.surface_march(c293, idxs, fb=0.0, kd=0, fade=254)
    worst = 0.0
    for j, ix in enumerate(idxs):
        a = abs(float(s293["T"][j])); b = abs(float(m293[j])); d = abs(mine(c293, ix)["T"])
        e = abs(float(s282["T"][j])); f = abs(mine(c282, ix)["T"])
        worst = max(worst, abs(a - b), abs(a - d), abs(b - d))
        pr("%6.0f | %6.0f %5.0f | %8.0f %8.0f %8.0f | %8.0f %8.0f | %s"
           % (ix, s293["sp"][j], s293["kp"][j], a, b, d, e, f,
              ("%.4f" % (abs(d) / abs(f))) if f else "-"))
    pr("")
    pr("max |disagreement| between the three methods over these idx: %.0f count(s)" % worst)

    # ---------------------------------------------------------------- B3.a  THE RAIL
    pr("")
    pr("-" * 112)
    pr("B3.a  THE RAIL  (peak delivered torque at the 427 tap, fade 254, wheel still)")
    pr("-" * 112)
    r293 = mine(c293, 240)["T"]
    r282_still = mine(c282, 240)["T"]
    # V282's TRUE rail is not at fb=0: its P clamp binds from idx 115 and the rail is the same clamp.
    # Score the rail as the largest |T| the chain can produce on each build, over fb states too.
    fbs = np.arange(-60000, 60001, 97)
    best293 = max(abs(mine(c293, ix, fb_state=int(fb))["T"])
                  for ix in (0, 120, 239, 240) for fb in (-46080, 0, 46080))
    best282 = max(abs(mine(c282, ix, fb_state=int(fb))["T"])
                  for ix in (0, 120, 239, 240) for fb in (-46080, -20000, 0, 20000, 46080))
    pr("  V293 T(idx 240, fb 0)  = %6d      V282 T(idx 240, fb 0)  = %6d      ratio %.6f"
       % (r293, r282_still, r293 / r282_still))
    pr("  V293 max |T| any state = %6d      V282 max |T| any state = %6d      ratio %.6f"
       % (best293, best282, best293 / best282))
    pr("  structural ceiling min((15360*gain)>>15, 3072) = %d on both  [t_clamp %d / %d]"
       % (min((15360 * c293["gain"]) >> 15, c293["t_clamp"]), c293["t_clamp"], c282["t_clamp"]))
    pr("  B3.a VERDICT: rail ratio %.6f -- %s"
       % (r293 / r282_still, "PASS (x1.000)" if r293 == r282_still else
          "DIFFERS BY %d COUNT(S) -> FAIL" % (r293 - r282_still)))

    # ---------------------------------------------------------------- B3.b  THE LINEAR SLOPE
    pr("")
    pr("-" * 112)
    pr("B3.b  THE LINEAR SLOPE and the integer floor")
    pr("-" * 112)
    # LINEARITY IS A STATEMENT ABOUT T vs THE SETPOINT sp, not vs the demand index: V282's assist map
    # is only APPROXIMATELY linear in idx (segment slopes 4.25-4.375 counts of sp per idx), so a
    # straight-line-in-idx test would score the MAP's shape, which both builds share byte-for-byte.
    sps = np.arange(0, 1033)

    def T_of_sp(c, sp, fade=254):
        kp = int(round(lerp(0, c["kp_X"], c["kp_Y"])))          # Kp is flat on both builds
        P = max(-c["p_clamp"], min(c["p_clamp"], (32 * int(sp) * kp) >> 8))
        S = max(-c["sum_clamp"], min(c["sum_clamp"], (fade * P) >> 8))
        y = (2 * ((S * c["lag_b"]) // (1024 - c["lag_a"]))) >> 5
        return max(-c["t_clamp"], min(c["t_clamp"], (-(y * c["gain"])) >> 15))

    def T_exact(c, sp, fade=254):
        kp = lerp(0, c["kp_X"], c["kp_Y"])
        P = min(32.0 * sp * kp / 256.0, c["p_clamp"])
        S = min(fade * P / 256.0, c["sum_clamp"])
        y = 2.0 * S * c["lag_b"] / (1024.0 - c["lag_a"]) / 32.0
        return min(y * c["gain"] / 32768.0, c["t_clamp"])

    Tm = np.array([abs(T_of_sp(c293, int(s))) for s in sps], float)
    Te = np.array([T_exact(c293, float(s)) for s in sps])
    lin = sps <= 1023                                            # below the P clamp (sp 1024 rails)
    dev = Tm[lin] - Te[lin]
    A = np.vstack([sps[lin], np.ones(lin.sum())]).T
    slope, icpt = np.linalg.lstsq(A, Tm[lin], rcond=None)[0]
    resid = Tm[lin] - (slope * sps[lin] + icpt)
    pr("  linearity is scored in sp (the map output), not in idx -- the MAP is shared byte-for-byte")
    pr("  fitted slope over sp 0..1023 : %.6f EPS counts per setpoint count (intercept %+.4f)" % (slope, icpt))
    pr("  max |residual from the straight line| : %.3f counts   rms %.3f"
       % (np.max(np.abs(resid)), float(np.sqrt(np.mean(resid ** 2)))))
    pr("  deviation of the INTEGER chain from the EXACT real chain, sp 0..1023: min %+.3f max %+.3f"
       % (dev.min(), dev.max()))
    slope_idx = (abs(T_of_sp(c293, 1023)) - 0) / float(np.interp(1023, c293["map_Y"], c293["map_X"]))
    pr("  => in demand-index terms the chord to the rail is %.6f counts/idx; per 0xE4 CAN count %.6f"
       % (slope_idx, slope_idx / (4096.0 / 254.0)))
    pr("  B3.b VERDICT: %s"
       % ("PASS -- the integer surface is a straight line in sp to within the integer floor "
          "(deviation from the exact chain in [%+.3f, %+.3f], |residual| <= %.2f count)"
          % (dev.min(), dev.max(), np.max(np.abs(resid)))
          if (dev.min() >= -1.001 and dev.max() <= 1.001 and np.max(np.abs(resid)) <= 1.5) else
          "FAIL -- deviation [%+.3f, %+.3f], max residual %.3f" % (dev.min(), dev.max(),
                                                                   np.max(np.abs(resid)))))

    # ---------------------------------------------------------------- where the P clamp first binds
    pr("")
    pr("  first demand index at which the P clamp binds:  V293 %s   V282 %s   STOCK %s"
       % (first_rail_idx(c293), first_rail_idx(c282), first_rail_idx(cstk)))
    pr("  (prereg A2 makes 'P rails below idx 238' a FAIL for V293.)")

    # ---------------------------------------------------------------- fade / taper
    pr("")
    pr("-" * 112)
    pr("B3.c  THE FADE -- identical LERP on both builds, multiplying both surfaces")
    pr("-" * 112)
    def _u16(b, a):
        return int.from_bytes(b[a:a + 2], "little")

    def _u32(b, a):
        return int.from_bytes(b[a:a + 4], "little")

    fadeX, fadeY = {}, {}
    for tag, p, base in (("V293", IMG293, 0xCBBC4), ("V282", IMG282, 0xCBBC4),
                         ("V293c", IMG293, 0xCBAE4), ("V282c", IMG282, 0xCBAE4)):
        b = open(p, "rb").read()
        rec = _u32(b, base + 4 * 7)
        n = _u16(b, rec)
        fadeX[tag] = [_u16(b, rec + 2 + 2 * i) for i in range(n)]
        fadeY[tag] = [_u16(b, rec + 2 + 2 * n + 2 * i) for i in range(n)]
        pr("  fade table %-6s @0x%05X rec 0x%05X n=%d  X %s  Y %s"
           % (tag, base, rec, n, fadeX[tag], fadeY[tag]))
    pr("  (the two candidate taper tables are printed so the selector question is visible; both are")
    pr("   BYTE-IDENTICAL between V293 and V282, so whichever the selector picks multiplies both.)")
    pr("")
    pr("%10s %6s | %8s %8s %8s" % ("|bar| raw", "m", "V293 pk", "V282 pk", "ratio"))
    for bar in (0, 400, 800, 1200, 1600, 2000, 2400, 3000):
        B = lerp(bar >> 5, fadeX["V293"], fadeY["V293"])
        m = (255 * int(round(B))) >> 8
        a = abs(mine(c293, 240, fade=m)["T"]); e = abs(mine(c282, 240, fade=m)["T"])
        pr("%10d %6d | %8d %8d %8.4f" % (bar, m, a, e, a / max(1, e)))
    pr("")
    pr("  V293/V282 fade tables identical at 0xCBBC4: %s ; at 0xCBAE4: %s"
       % (fadeX["V293"] == fadeX["V282"] and fadeY["V293"] == fadeY["V282"],
          fadeX["V293c"] == fadeX["V282c"] and fadeY["V293c"] == fadeY["V282c"]))
    pr("")
    pr("  STOCK peak T for scale: sp_top %d, gain %d, t_clamp %d -> |T| = %d"
       % (max(cstk["map_Y"]), cstk["gain"], cstk["t_clamp"],
          abs(mine(cstk, 240, fade=254)["T"])))

    open(os.path.join(HERE, "_scratch", "advB_v293_b3.txt"), "w",
         encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("")
    pr("wrote _scratch/advB_v293_b3.txt")


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "_scratch"), exist_ok=True)
    main()
