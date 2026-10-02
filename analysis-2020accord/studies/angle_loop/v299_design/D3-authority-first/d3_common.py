# -*- coding: utf-8 -*-
r"""d3_common.py -- D3 (authority-first) shared definitions: the V298 image cells read from the BUILT image, the
candidate cells, the byte edits, and the fork-side schedules.  ANALYSIS ONLY.

Every V298 number is read from `_v298_*_plain_image.bin` (sha256 177abf04...) and asserted; nothing is taken from
the build script's constants.  The cave immediates were located by Ghidra (ADVIG_V298_177abf04.bin, disassemble_bytes
0xC4C00..0xC4CDA, dry run) and are re-asserted here by a Python LE byte read (two methods).
"""
from __future__ import annotations

import glob
import hashlib
import math
import os
import struct
from pathlib import Path

import numpy as np

os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
KIT = AL.parents[2]
OUT = KIT / "_scratch" / "angle_loop" / "v299-D3"
OUT.mkdir(parents=True, exist_ok=True)
V298_SHA = "177abf043550851789e1063b6625a0e17115a1beb50851571f1b38780bf32066"


def v298_image():
    p = sorted(glob.glob(os.path.join(os.environ["ACCORD_FIRMWARE_ROOT"], "analysis-2020accord",
                                      "_v298_*_plain_image.bin")))
    assert len(p) == 1, p
    b = Path(p[0]).read_bytes()
    assert hashlib.sha256(b).hexdigest() == V298_SHA
    return b


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def i16(b, a):
    return struct.unpack_from("<h", b, a)[0]


# ---- the cave immediates (Ghidra dry-run decode of 0xC4C00..0xC4CD9 on the V298 image, re-read here) ----------------
#  addr of the INSTRUCTION, addr of the patched halfword, decoded instruction, V298 value, the loop term
CAVE_IMM = {
    "thr":   (0xC4C62, 0xC4C64, "movea 0x200,r0,r13 ; cmp r13,r8 ; bh FRZ", 512, "hard hand freeze |gp-0x4f68| > thr"),
    "sgn":   (0xC4C6A, 0xC4C6C, "movea 0x12c,r0,r13 ; cmp r13,r8 ; bnh N", 300, "opposing-hand freeze |tq| > sgn"),
    "vth":   (0xC4C88, 0xC4C8A, "movea 0xb40,r0,r13 ; cmp r13,r8 ; bh", 2880, "A3 slope switch speed (45 km/h)"),
    "B":     (0xC4C96, 0xC4C98, "addi 0x4e2,r9,r9", 1250, "A3 bound offset B (S counts)"),
    "vcap":  (0xC4C9A, 0xC4C9C, "movea 0x566,r0,r13 ; cmp r13,r8 ; bh", 1382, "A3 low-speed cap speed (21.6 km/h)"),
    "cap":   (0xC4CA2, 0xC4CA4, "movea 0x1000,r0,r13 ; cmp r13,r9 ; cmovh", 4096, "A3 low-speed cap (S counts)"),
}
SHL_LO = (0xC4C90, "shl 0x4,r9", 0x4AC4)          # A3 slope below vth: |theta| << 4 (halfword 0x4AC4 = c4 4a)
SHL_HI = (0xC4C94, "shl 0x6,r9", 0x4AC6)
TABLE = 0xC4CDA                                    # GB-P, 7 rows of (X u16, G u16, S i16)
GB_P = ((714, 1178, 1041), (1843, 1465, -6264), (2304, 760, -2033), (2707, 560, 1570), (4032, 1068, 2118),
        (6198, 2188, 0), (0xFFFF, 2188, 0))
CALS = {"Ki": (0xC63E6, 40), "ICL": (0xC61BA, 8192), "DCL": (0xC61B6, 10240), "PCL": (0xC61BC, 15360),
        "SCL": (0xC61BE, 15360), "OCL": (0xC61B4, 3072), "fwd": (0xC6CD0, 5346), "oa": (0xC63EC, 992),
        "ob": (0xC63EE, 507), "KpY0": (0xE5384, 112), "KdY0": (0xE5126, 48)}


def assert_v298(b=None):
    b = b or v298_image()
    for k, (ia, ha, txt, val, _) in CAVE_IMM.items():
        assert u16(b, ia) == 0x6E20 or k == "B", (k, hex(u16(b, ia)))     # movea r0->r13 halfword (B is an addi)
        assert u16(b, ha) == val, (k, u16(b, ha), val)
    assert u16(b, SHL_LO[0]) == SHL_LO[2] and u16(b, SHL_HI[0]) == SHL_HI[2]
    rows = tuple((u16(b, TABLE + 6 * k), u16(b, TABLE + 6 * k + 2), i16(b, TABLE + 6 * k + 4)) for k in range(7))
    assert rows == GB_P, rows
    for k, (a, val) in CALS.items():
        got = i16(b, a) if k in ("oa", "fwd") else u16(b, a)
        assert got == val, (k, hex(a), got, val)
    for j in range(5):
        assert u16(b, 0xE5384 + 2 * j) == 112, j                  # Kp Y knots (flat)
    for j in range(4):
        assert u16(b, 0xE5126 + 2 * j) == 48, j                   # Kd Y knots (flat)
    return rows


# ---- the speed table ---------------------------------------------------------------------------------------------
def spd(v):
    return int(math.floor(v * 3.6 * 64.0 + 1e-9))                 # gp-0x6a5e, 64 counts per km/h


def walk_G(rows, vc):
    v = vc & 0xFFFF
    if not v > rows[0][0]:
        return rows[0][1]
    i = 0
    while not v <= rows[i + 1][0]:
        i += 1
    X, G, S = rows[i]
    return G + (((v - X) * S) >> 12)


def scaled_rows(mult_lo, rows=GB_P, mult_8=None):
    """D3 table: knot 0 (3.1 m/s, X 714) G x mult_lo, knot 1 (8.0 m/s, X 1843) G x mult_8 (default = mult_lo), then the
    V298 descent to 10.0 m/s (X 2304, G 760); every knot >= 2304 byte-identical.  Slopes re-fit so the walk hits the
    knots (S = round((G_next - G) 4096 / dX))."""
    (x0, g0, _), (x1, g1, _), (x2, g2, s2) = rows[0], rows[1], rows[2]
    G0 = int(round(g0 * mult_lo))
    G1 = int(round(g1 * (mult_lo if mult_8 is None else mult_8)))
    S0 = int(round((G1 - G0) * 4096 / (x1 - x0)))
    S1 = int(round((g2 - G1) * 4096 / (x2 - x1)))
    assert -32768 <= S0 < 32768 and -32768 <= S1 < 32768
    return ((x0, G0, S0), (x1, G1, S1)) + tuple(rows[2:])


# ---- delivered-torque units (EVIDENCE: lane chain constants read from the image; = drive-read's 0.02003 tap/S) ------
FADE0 = 254.0 / 256.0                                              # ((255*255)&0xFFFF)>>8 / 256, hands-off
HOUT0 = (507 / 1024.0) * 2.0 / 32.0 / (1.0 - 992 / 1024.0)        # output-lag DC gain (0.990)
T_PER_S = FADE0 * HOUT0 * 5346 / 32768.0                          # T counts per lane S count (0.1603)
TAP_PER_S = T_PER_S / 8.0                                          # 0x1AB tap LSB per S count (0.0200)


def Kp_eff(rows, v, kp=112):
    return kp * walk_G(rows, spd(v)) / 256.0


def cP_T_per_deg(rows, v, kp=112):
    """P stiffness, T counts per degree of (theta_sp - theta): E = 160/deg, P = E G Kp >> 16."""
    return 160.0 * walk_G(rows, spd(v)) * kp / 65536.0 * T_PER_S


def cD_T_per_dps(kd=48):
    """D = (Kd * gp-0x6abe) >> 3, gp-0x6abe = -4.712 counts per deg/s (motor frame), pol -1 => opposes motion."""
    return kd / 8.0 * 4.712 * T_PER_S                               # 4.53 T per deg/s (0.566 tap) at Kd 48


# ---- fork-side schedules (V298 = Dom 2712e1336 values.py) ------------------------------------------------------------
EMAX_BP = [3.1, 8.0, 10.0, 11.75, 17.5, 26.9]
EMAX_V298 = [17.0, 15.5, 19.5, 17.0, 8.5, 4.5]
CAP_V298 = 120.0                                                   # deg/s (MAX_ANGLE_RATE 1.2 deg/frame)
O1_V298 = (600, 500)


def vm_rate(v):
    """the VM lateral-jerk cap in deg/s (3.589 m/s^3; M2's computed 49/38/30/20 deg/s at 15/17.5/20/26.9 m/s,
    ~ 11000/v^2 below) -- an approximation used only to bound the sims; the fork computes it with its VM."""
    return float(np.interp(v, [3.0, 8.0, 10.0, 15.0, 17.5, 20.0, 26.9, 35.0],
                           [1220.0, 172.0, 110.0, 49.0, 38.0, 30.0, 20.0, 12.0]))
