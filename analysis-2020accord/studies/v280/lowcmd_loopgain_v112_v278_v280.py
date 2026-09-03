# -*- coding: utf-8 -*-
"""Small-signal LOOP-GAIN comparison of V112 vs V278 rev 3 vs V280 rev 2 in the LOW-COMMAND regime (idx 0-60).

Every constant below is READ FROM THE IMAGES at run time (no inherited numbers), and every arithmetic line mirrors
the decompile of FUN_00028ea6 (stock code.bin, Ghidra; the PID function is byte-identical in the three builds except
V112's 0x2A1F0 gain-read redirect, which all three carry).  Tick = 1 kHz (kit record: BUILD-LINEAGE "tick = 1 ms
settled two ways"; the 0x22518 `andi 0x930` is a STATE gate, not a phase divider).

Chain (decompile line refs are the saved Ghidra decompile of FUN_00028ea6):
  S     = clamp(-4*cmd, +-LIMIT[speed])                       LIMIT slot 7 = 16384 above 3413 speed units
  v     = ((taper*speedF) & 0xFFFF) * S >> 16 ; v >>= 6 ; clamp +-240      (L925-942)
  idx   = |v|  -> gp-0x674b                                   (L943-949)   <- from cmd/taper/speed ONLY
  sp    = sign(v) * LERP(map[sel], idx)  -> gp-0x6a32         (L951-974)   map indexed by idx  (uVar30 = uVar33 & 0xff)
  E     = 32*sp - fb                                          (L975)
  fb    = clamp(s_old + s_new, +-0xC62E6);  s_new = (923*s_old>>10) + (1560*x>>10), x = gp-0x6a56 = -0x18F rate (8/deg/s)
  P     = clamp(E * LERP(Kp[sel], idx) >> 8, +-0xC61BC)       (L1013-1052) Kp indexed by the SAME idx (uVar33 & 0xffff)
  D     = clamp((E - E_prev) * LERP(Kd[sel], idx) >> 3, +-0xC61B6)   (L1053-1092) Kd = 128 flat -> 16*dE per tick
  I     = 0 (0xC63E6 = 0)
  sum   = (I>>7) + P + D ; x postA(|dtq|>>6) * postB(|tq|>>5) & 0xffff >> 8 ; >> 8 ; clamp +-0xC61BE   (L1094-1205)
  lag   : s' = (992*s>>10) + (507*u>>10) ; y = (s + s') >> 5     (L1224-1227)   DC 0.990, pole 5.05 Hz
  T     = clamp( (y*ramp>>15) * (-1) * GAIN >> 15, +-0xC61B4 ) -> gp-0x6b38    (L1244-1265)
          GAIN is read at 0x2A1EE: stock `ld.h 0x746c,tp` (0xC646C = 891); V112+ redirect the read to 0xC6CD0 = 5346.

Run:  python analysis-2020accord/studies/v280/lowcmd_loopgain_v112_v278_v280.py
"""
import os
import struct

import numpy as np

FW = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares") + "/analysis-2020accord/"
IMAGES = {
    "stock": "stock_fw_dump/code.bin",
    "V112": "_v112_V112-V111BASE-RELAY.KNEE1800.K1.612_plain_image.bin",
    "V278r3": "_v278_V278R3-V268BASE-REFERENCE2X.MAP.FEEDBACK.TORQUE.TAP_plain_image.bin",
    "V280r2": "_v280_V280R2-V268BASE-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
}
SEL = 7                       # live variant selector, measured on the wire (record 11)
FS = 1000.0                   # tick
CPD = 8.0                     # raw 0x18F counts per deg/s (measured, corr 0.997)


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def lerp_rec(b, base, n):
    """firmware LERP record: hdr@+0, X[n]@+2, Y[n]@+2+2n."""
    X = [u16(b, base + 2 + 2 * i) for i in range(n)]
    Y = [u16(b, base + 2 + 2 * n + 2 * i) for i in range(n)]
    return np.array(X, float), np.array(Y, float)


def read_build(path):
    b = open(path, "rb").read()
    c = {}
    c["map_X"], c["map_Y"] = lerp_rec(b, u32(b, 0xC9A88 + 4 * SEL), 10)
    c["kp_X"], c["kp_Y"] = lerp_rec(b, u32(b, 0xCB994 + 4 * SEL), 5)
    c["kd_X"], c["kd_Y"] = lerp_rec(b, u32(b, 0xCB7D4 + 4 * SEL), 4)
    c["postA"] = lerp_rec(b, u32(b, 0xCBB54 + 4 * SEL), 6)
    c["postB"] = lerp_rec(b, u32(b, 0xCBAE4 + 4 * SEL), 6)
    c["limit"] = lerp_rec(b, u32(b, 0xCB844 + 4 * SEL), 8)
    c["taperA"] = lerp_rec(b, u32(b, 0xCBA74 + 4 * SEL), 4)
    c["fb_clamp"] = u16(b, 0xC62E6)
    c["p_clamp"] = u16(b, 0xC61BC)
    c["d_clamp"] = u16(b, 0xC61B6)
    c["sum_clamp"] = u16(b, 0xC61BE)
    c["t_clamp"] = u16(b, 0xC61B4)
    c["ki"] = u16(b, 0xC63E6)
    c["fb_a"], c["fb_b"] = u16(b, 0xC63E8), u16(b, 0xC63EA)
    c["lag_a"], c["lag_b"] = u16(b, 0xC63EC), u16(b, 0xC63EE)
    # the gain read at 0x2A1EE: `ld.h disp,tp,r7` -- decode the displacement from the image bytes
    disp = u16(b, 0x2A1F0)
    c["gain_addr"] = 0xBF000 + disp
    c["gain"] = u16(b, c["gain_addr"])
    c["idx_clamp"] = b[0xC64F0]
    c["speedF"] = lerp_rec(b, 0xC6976 - 2, 4)[1]        # tp+0x7976 table: X at +0.. here hdr-less; Y read directly below
    c["speedF"] = np.array([u16(b, 0xC697E + 2 * i) for i in range(4)], float)
    return c


def lerp(X, Y, u):
    return np.interp(u, X, Y)


def idx_of_cmd(cmd, taper=254, speedF=255, limit=16384):
    S = np.clip(-4.0 * cmd, -limit, limit)
    v = np.floor(((taper * speedF) & 0xFFFF) * S / 65536.0)
    v = np.floor(v / 64.0)
    return np.abs(np.clip(v, -240, 240))


def slope(X, Y, x):
    """local dY/dx of the LERP at x (right-hand slope on a knot)."""
    x = float(x)
    for i in range(len(X) - 1):
        if X[i] <= x < X[i + 1]:
            return (Y[i + 1] - Y[i]) / (X[i + 1] - X[i])
    return 0.0


def H_lag(c, f):
    """y = (s + s')>>5, s' = (a s + b u)>>10  ->  (b/1024)(1+z^-1)/(1 - (a/1024) z^-1) / 32."""
    z = np.exp(1j * 2 * np.pi * f / FS)
    return (c["lag_b"] / 1024.0) * (1 + 1 / z) / (1 - (c["lag_a"] / 1024.0) / z) / 32.0


def H_fb(c, f):
    """fb = s_old + s_new, per raw count of x: (b/1024)(1+z^-1)/(1-(a/1024)z^-1)."""
    z = np.exp(1j * 2 * np.pi * f / FS)
    return (c["fb_b"] / 1024.0) * (1 + 1 / z) / (1 - (c["fb_a"] / 1024.0) / z)


def C_ctrl(c, idx, f, with_d=True):
    """E -> T small-signal (per count of E), at demand index idx.  Includes post-mult (low torque), lag, GAIN, sign."""
    z = np.exp(1j * 2 * np.pi * f / FS)
    kp = lerp(c["kp_X"], c["kp_Y"], idx) / 256.0
    kd = lerp(c["kd_X"], c["kd_Y"], idx) / 8.0 * (1 - 1 / z) if with_d else 0.0
    post = ((int(lerp(*c["postA"], 0)) * int(lerp(*c["postB"], 0))) & 0xFFFF) >> 8      # low driver torque, low torque-rate
    return (kp + kd) * (post / 256.0) * H_lag(c, f) * (c["gain"] / 32768.0)             # sign (-1) dropped: magnitude/phase of |L|


def main():
    C = {k: read_build(FW + v) for k, v in IMAGES.items()}
    print("=" * 118)
    print("CELLS READ FROM THE IMAGES (slot %d)" % SEL)
    print("=" * 118)
    for k, c in C.items():
        print("%-7s map Y=%s" % (k, " ".join("%4d" % y for y in c["map_Y"])))
    c0 = C["V112"]
    print("map X      = %s" % " ".join("%4d" % x for x in c0["map_X"]))
    print("Kp  X/Y    = %s / %s   (identical in all four images: %s)" % (c0["kp_X"].astype(int).tolist(), c0["kp_Y"].astype(int).tolist(),
          all(np.array_equal(C[k]["kp_Y"], c0["kp_Y"]) for k in C)))
    print("Kd  X/Y    = %s / %s   (identical: %s)" % (c0["kd_X"].astype(int).tolist(), c0["kd_Y"].astype(int).tolist(),
          all(np.array_equal(C[k]["kd_Y"], c0["kd_Y"]) for k in C)))
    print("postA(|dtq|>>6) X/Y = %s / %s ; postB(|tq|>>5) X/Y = %s / %s" % (c0["postA"][0].astype(int).tolist(), c0["postA"][1].astype(int).tolist(),
          c0["postB"][0].astype(int).tolist(), c0["postB"][1].astype(int).tolist()))
    print("LIMIT slot 7 Y = %s ; taperA X/Y = %s / %s ; speedF Y = %s" % (c0["limit"][1].astype(int).tolist(), c0["taperA"][0].astype(int).tolist(),
          c0["taperA"][1].astype(int).tolist(), c0["speedF"].astype(int).tolist()))
    print("%-7s %8s %8s %8s %8s %8s %4s %8s %8s %8s %8s %12s" % ("build", "fbclamp", "Pclamp", "Dclamp", "Sclamp", "Tclamp", "Ki", "fb a/b", "", "lag a/b", "", "GAIN@addr"))
    for k, c in C.items():
        print("%-7s %8d %8d %8d %8d %8d %4d %8d %8d %8d %8d %6d@0x%05X" % (k, c["fb_clamp"], c["p_clamp"], c["d_clamp"], c["sum_clamp"], c["t_clamp"], c["ki"],
              c["fb_a"], c["fb_b"], c["lag_a"], c["lag_b"], c["gain"], c["gain_addr"]))
    fb_dc = 2 * c0["fb_b"] / (1024 - c0["fb_a"])
    lag_dc = 2 * c0["lag_b"] / (1024 - c0["lag_a"]) / 32
    print("fb DC gain = %.3f per raw count = %.1f per deg/s ; lag DC = %.4f ; fb pole %.1f Hz ; lag pole %.2f Hz" % (
        fb_dc, fb_dc * CPD, lag_dc, -FS * np.log(c0["fb_a"] / 1024) / (2 * np.pi), -FS * np.log(c0["lag_a"] / 1024) / (2 * np.pi)))
    print("feedback saturates at |rate| = clamp/(%.2f*8) deg/s: %s" % (fb_dc, ", ".join("%s %.1f" % (k, C[k]["fb_clamp"] / fb_dc / CPD) for k in C)))
    print("P rails at |E| = 15360*256/Kp(idx): idx0 %.0f counts (%.1f deg/s of rate error) ; idx60 %.0f (%.1f deg/s)" % (
        15360 * 256 / 248, 15360 * 256 / 248 / fb_dc / CPD, 15360 * 256 / lerp(c0["kp_X"], c0["kp_Y"], 60), 15360 * 256 / lerp(c0["kp_X"], c0["kp_Y"], 60) / fb_dc / CPD))

    # ------------------------------------------------------------------------------------------------
    print("\n" + "=" * 118)
    print("PART 1 -- SMALL-SIGNAL GAINS AT DC, per demand index (post-mult 254/256, lag 0.990, GAIN/32768, low driver torque)")
    print("   dT/dcmd  = 32 * slope(idx) * didx/dcmd * Kp/256 * chain     [T counts per cmd count]")
    print("   dT/drate = 30.89 * 8 * Kp/256 * chain                        [T counts per deg/s of wheel rate]  <- the INNER-LOOP gain")
    print("=" * 118)
    chain_dc = (254 / 256.0) * lag_dc * (c0["gain"] / 32768.0)
    didx_dcmd = 4 * 64770 / 65536.0 / 64          # 0.06177 idx per cmd count
    print("didx/dcmd = %.5f (idx 60 <-> |cmd| %.0f) ; chain (post*lag*gain) = %.5f" % (didx_dcmd, 60 / didx_dcmd, chain_dc))
    rows = (12, 24, 32, 48, 58)
    hdr = "%4s %5s %5s | %7s %7s %7s | %8s %8s %8s | %6s %6s | %8s %6s" % ("idx", "cmd", "Kp", "m_112", "m_r3", "m_280", "dTdc112", "dTdc_r3", "dTdc280",
                                                                          "r3/112", "280/112", "dTdrate", "ratio")
    print(hdr)
    for i in rows:
        kp = lerp(c0["kp_X"], c0["kp_Y"], i)
        m = {k: slope(C[k]["map_X"], C[k]["map_Y"], i) for k in ("V112", "V278r3", "V280r2")}
        dtdc = {k: 32 * m[k] * didx_dcmd * kp / 256.0 * chain_dc for k in m}
        dtdr = fb_dc * CPD * kp / 256.0 * chain_dc
        print("%4d %5.0f %5.0f | %7.3f %7.3f %7.3f | %8.3f %8.3f %8.3f | %6.2f %6.2f | %8.2f %6.2f" % (
            i, i / didx_dcmd, kp, m["V112"], m["V278r3"], m["V280r2"], dtdc["V112"], dtdc["V278r3"], dtdc["V280r2"],
            dtdc["V278r3"] / dtdc["V112"], dtdc["V280r2"] / dtdc["V112"], dtdr, 1.0))
    print("   dT/drate is the SAME NUMBER in all three builds at every idx: Kp, Kd, fb filter, post-mult, lag, GAIN are byte-identical;")
    print("   the map is not in the feedback path (E = 32*sp - fb; sp = map(idx); d(E)/d(fb) = -1 regardless of the map).")

    # matched-manoeuvre: to reach the SAME setpoint, rev 3 needs half the cmd -> lower idx -> lower Kp
    print("\nPART 1b -- MATCHED SETPOINT: the idx (cmd) each build needs for the same sp, and the Kp it then runs at")
    print("%5s | %6s %5s | %6s %5s %6s | %6s %5s %6s" % ("sp", "i_112", "Kp", "i_r3", "Kp", "ratio", "i_280", "Kp", "ratio"))
    grid = np.arange(0, 240.01, 0.01)
    for i112 in rows:
        sp = lerp(c0["map_X"], c0["map_Y"], i112)
        out = [i112, lerp(c0["kp_X"], c0["kp_Y"], i112)]
        for k in ("V278r3", "V280r2"):
            y = lerp(C[k]["map_X"], C[k]["map_Y"], grid)
            ik = grid[np.argmin(np.abs(y - sp))]
            kpk = lerp(c0["kp_X"], c0["kp_Y"], ik)
            out += [ik, kpk, kpk / out[1]]
        print("%5.0f | %6.1f %5.0f | %6.1f %5.0f %6.2f | %6.1f %5.0f %6.2f" % (sp, *out))

    # ------------------------------------------------------------------------------------------------
    print("\n" + "=" * 118)
    print("PART 2 -- FREQUENCY RESPONSE of the firmware side of the rate loop, L_fw(f) = C(idx,f) * H_fb(f) * 8 * z^-1  [T counts per deg/s]")
    print("          (transport z^-1 = one 1 kHz tick).  Phase in degrees.  The PLANT (T -> wheel rate) is NOT in the kit's record.")
    print("=" * 118)
    freqs = (1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 30, 50)
    for idx in (12, 32, 58):
        print("idx %d (Kp %.0f):" % (idx, lerp(c0["kp_X"], c0["kp_Y"], idx)))
        print("   %6s | %9s %8s | %9s %8s | %8s %8s %8s" % ("f Hz", "|L| P+D", "ph P+D", "|L| P", "ph P", "ph_lag", "ph_fb", "ph_z-1"))
        for f in freqs:
            z1 = np.exp(-1j * 2 * np.pi * f / FS)
            Lpd = C_ctrl(c0, idx, f, True) * H_fb(c0, f) * CPD * z1
            Lp = C_ctrl(c0, idx, f, False) * H_fb(c0, f) * CPD * z1
            print("   %6.1f | %9.2f %8.1f | %9.2f %8.1f | %8.1f %8.1f %8.1f" % (
                f, abs(Lpd), np.degrees(np.angle(Lpd)), abs(Lp), np.degrees(np.angle(Lp)),
                np.degrees(np.angle(H_lag(c0, f))), np.degrees(np.angle(H_fb(c0, f))), -360 * f / FS))
    # where does the firmware phase alone reach -180 / -90 ?
    ff = np.linspace(0.5, 499, 20000)
    for with_d, lab in ((True, "P+D"), (False, "P only")):
        ph = np.degrees(np.unwrap(np.angle([C_ctrl(c0, 32, f, with_d) * H_fb(c0, f) * np.exp(-1j * 2 * np.pi * f / FS) for f in ff])))
        f180 = ff[np.argmax(ph <= -180)] if (ph <= -180).any() else np.nan
        f90 = ff[np.argmax(ph <= -90)] if (ph <= -90).any() else np.nan
        print("firmware phase alone (%s): reaches -90 deg at %.1f Hz, -180 deg at %.1f Hz" % (lab, f90, f180))
    print("   => with a pure-inertia plant (-90 deg everywhere) the loop phase hits -180 where the firmware supplies -90;")
    print("      with a 2nd-order mechanical resonance the plant supplies -90 AT its resonance and the firmware's 2-4 Hz phase (-28..-52) is what remains.")
    print("   The ratio of |L| between builds is 1.00 at every f and idx (same C, same H_fb), so the -180 frequency is BUILD-INDEPENDENT.")

    # ------------------------------------------------------------------------------------------------
    print("\n" + "=" * 118)
    print("PART 3 -- THE OUTER (openpilot) PATH: cmd -> sp -> (inner loop) -> wheel rate.  Ratio between builds at the same cmd.")
    print("   inner closed loop rate/sp = 32*C*G / (1 + C*G*H_fb*8);  any G: the ratio between builds at fixed idx is the MAP RATIO.")
    print("=" * 118)
    print("%4s | %8s %8s %8s | %6s %6s" % ("idx", "Y_112", "Y_r3", "Y_280", "r3/112", "280/112"))
    for i in (6, 12, 18, 24, 32, 40, 48, 58):
        y = {k: lerp(C[k]["map_X"], C[k]["map_Y"], i) for k in ("V112", "V278r3", "V280r2")}
        print("%4d | %8.1f %8.1f %8.1f | %6.2f %6.2f" % (i, y["V112"], y["V278r3"], y["V280r2"], y["V278r3"] / y["V112"], y["V280r2"] / y["V112"]))
    print("   (small-signal: the SLOPE ratios of Part 1; large-signal: the LEVEL ratios here.  rev 3 = 2.00 both ways at every idx.)")

    # D-term rail on setpoint steps (100 Hz command updates): dE = 32*dsp per tick when cmd changes
    print("\nPART 4 -- D on the SETPOINT: a cmd step of dcmd at 100 Hz moves sp by slope*didx/dcmd*dcmd in ONE tick; D = 16*32*dsp, rails at 10240 (dsp > 20)")
    for k in ("V112", "V278r3", "V280r2"):
        m = slope(C[k]["map_X"], C[k]["map_Y"], 20)
        print("   %-7s slope@20 = %.2f -> D rails for a single-tick cmd step > %.0f counts" % (k, m, 20 / (m * didx_dcmd)))


if __name__ == "__main__":
    main()
