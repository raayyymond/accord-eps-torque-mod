# -*- coding: utf-8 -*-
"""v295_harness.py -- THE SHARED CLOSED-LOOP DESIGN HARNESS for the V295 LKAS-PID tuning session (subagent `harness`).

README
======
What it is.  A 1 kHz simulation of  planner demand -> the REAL fork's generic torque controller (Dom 20d24ab79, r1 config,
100 Hz, vectorised port proven equal to the real code) -> Honda rate limiter -> 0xE4 -> the BYTE-EXACT V294-class LKAS
lane (every cal knob a parameter; int32 overflow RAISES) -> the identified plant family (v294_plant, Karnopp friction,
transport delay, optional kappa(angle) rack/wheel map, two-mass stress modes) -> angle / rate -> back to the fork and to
the lane.  Two modes: A = the recorded 0xE4 command replayed (exogenous), B = the recorded planner demand, fork in the loop.

Trust map (details and the retrodiction table in V295-HARNESS.md):
  * the LANE is EVIDENCE: equal to the golden model tick for tick (h1_lane_gate.py, 90,000 ticks incl. Ki/Kd live) and
    bit-exact to the plant study's march on all 1.02 M ticks of r71b (tap residual 3.64 counts).
  * the FORK is EVIDENCE: the real LatControlTorque @20d24ab79 replays r71b's torqueState to float32 precision once the
    liveParameters message it held is identified (h3_fork_replay.py); the vectorised port == the real code bit for bit
    on the replay and on closed-loop trajectories (h3b_port_gate.py).
  * the PLANT ALONE (dist "c0"/"lp") is NOT FIT in every speed band by the pre-registered rule: it makes only 5-20 % of
    the drive's 1-8 Hz wheel motion.  Its OUTER-LOOP numbers under dist "lp" (tracking gain, turn hold, integrator share,
    command rms) are FIT in most bands (h4_retrodict_out.txt).  With the drive's disturbance replayed (dist "full") every
    band is FIT -- a CONSISTENCY check of the loop assembly, and the basis for COUNTERFACTUALS relative to V294 (same
    road, different cells).  A counterfactual under "full" is biased toward "no change" wherever the real plant has
    feedback-dependent dynamics the model lacks -- bracket it with light_b.
  * dwells/min in the SIM is dominated by the sensor-noise model (h6: 19-50 /min at 0 noise, 0 at 4 counts): do not use it.
  * Nothing above ~8 Hz is identified: every HF statement rests on the stress members (mode13, mode20, mode20_lo).

Runtimes (this PC, numpy, no numba): Cells.v294() 0.1 s; score(c, quick=True) ~5 s; score(c) ~80-100 s (candidate +
V294 in one batch, 6-8 plants, modes A and B, dists full and lp); simulate(mode B, 21 chunks = 608 s of driving) ~15-20 s
for up to ~250 lanes; sweep_drive([c1..cN]) ~20 s per disturbance model for N x plants x 21 lanes up to ~250;
Lane.march 1 M ticks ~90 s per call with the int32 guard on (any batch width up to a few hundred).

How to use (B lanes run in parallel for roughly the price of one):

    import sys; sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness")
    import v295_harness as H
    base = H.Cells.v294()                                  # every knob read from the V294 IMAGE (hash-checked)
    cand = base.replace(fb_b=1134)                          # any knob: fb_a fb_b fb_clamp fb_op e_shift kp_x kp_y kd_x kd_y
                                                            #  d_clamp ki deadband i_clamp p_clamp sum_clamp lag_a lag_b gain
                                                            #  t_clamp map_x map_y idx_clamp G_same G_opp taperB taperD
    cand.problems()                                         # static checks: b > b_max, Y > 32767, taper wrap ... (list)
    r = H.score(cand, plants=("nominal", "b_lo", "light_b"), bands="all", modes=("A", "B"))   # dict, see score()
    H.print_score(r)
    H.score(cand, quick=True)                               # M_LOOP + M_SAFE + M_HF(linear) only, no simulation [~1 s]

    many candidates at once (fast): H.sweep_drive([c1, c2, ...], plants=("nominal", "light_b"), dists=("full", "lp"))
    ALWAYS report a candidate as a DIFFERENCE from V294 in the same batch, under BOTH "full" and "lp", on nominal AND light_b.

    lower level:
    L = H.Lane([base, cand])                                # a batch of 2 lanes (cells may differ per lane)
    H.loop_frf(cand, H.family()["nominal"].at(12.0), f)     # the inner return ratio L(f) (complex array)
    sim = H.simulate(cells_list, member, mode="B", chunks=H.route_chunks())   # raw closed-loop traces

Units: T = delivered lane torque gp-0x6b38, T counts, + = steer RIGHT (the 427 tap); wire = 0xE4 counts (+ right);
x = the rate operand in counts (8 per deg/s); angle deg + LEFT; plant input u = -T (T counts, + left).
Sign convention of the lane driver = the kit's validated march (plib.march / r71b_attribution.march): sp = sign(wire)*map(idx),
x_lane = +0x18F raw rate = -8 * omega_left; output in the tap's sign.  (The firmware's own polarity flag cancels in the loop;
the two conventions differ only by floor() asymmetry at the 1-LSB level, invisible to the 8-count tap -- BELIEF.)

ANALYSIS ONLY.  Sends nothing, flashes nothing, builds no image, touches no fork or firmware file.
"""
import hashlib
import json
import math
import os
import sys
import time
from dataclasses import dataclass, field, replace, asdict

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
for _p in (os.path.join(KIT, "analysis-2020accord", "studies", "v295", "lib"),
           os.path.join(KIT, "analysis-2020accord", "studies", "v295", "plant"),
           os.path.join(KIT, "analysis-2020accord", "model"), HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

IMG = dict(
    V294=(FW + "_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-"
          "MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin", "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85"),
    V293=(FW + "_v293_V293-V282BASE-TORQUEMODE.FB0-KD0.BANK.ALL+DCLAMP0-KP.FLAT.120.ALL-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_"
          "plain_image.bin", None),
    V282=(FW + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
          None),
)
SEL = 7                                   # the live variant selector (EVIDENCE in the record, measured on the wire)
I32 = 1 << 31
DT = 1e-3
BANDS = (("0-5", 0.0, 5.0), ("5-10", 5.0, 10.0), ("10-15", 10.0, 15.0), ("15-22", 15.0, 22.0), ("22+", 22.0, 99.0))
WIRE_PER_IDX = 2 ** 22 / (4 * 65025)      # 16.12573 wire counts per demand-index LSB (census, re-derived)


class Int32Overflow(ArithmeticError):
    """an intermediate the firmware holds in a 32-bit register (or a 16-bit sxh) left its range -- the real ECU would
    WRAP silently here; the harness refuses to continue."""


# ======================================================================================================================
# SECTION 1 -- the cells: every knob of the lane, read by ADDRESS from an image
# ======================================================================================================================
def _u16(b, a):
    return int.from_bytes(b[a:a + 2], "little")


def _s16(b, a):
    return int.from_bytes(b[a:a + 2], "little", signed=True)


def _u32(b, a):
    return int.from_bytes(b[a:a + 4], "little")


def _rec(b, bank, n=None):
    """per-variant bank: LE32 record pointer at bank + 4*SEL; record = u16 n, X[n], Y[n] (the kit's layout, EVIDENCE:
    v293_lib.read_cells / adv_v290_null.read_cells read Kp and Kd this way and match the golden model)."""
    r = _u32(b, bank + 4 * SEL)
    nn = _u16(b, r)
    if n is not None and nn != n:
        raise ValueError("record at 0x%X has %d knots, expected %d" % (r, nn, n))
    X = tuple(_u16(b, r + 2 + 2 * i) for i in range(nn))
    Y = tuple(_u16(b, r + 2 + 2 * nn + 2 * i) for i in range(nn))
    return X, Y


@dataclass(frozen=True)
class Cells:
    """every calibration knob of the LKAS lane (census V294-LKAS-PID-DESIGN-SPACE.md section 3), plus the two in-place
    opcodes (fb_op at 0x28FA4, e_shift at 0x29D76).  Knot COUNTS are fixed by code: Kp 5, Kd 4, map 10, G 4, tapers 6."""
    name: str = "cells"
    fb_a: int = 1011            # 0xC63E8 s16  fb-lag pole
    fb_b: int = 567             # 0xC63EA u16  fb-lag gain
    fb_clamp: int = 1024        # 0xC62E6 u16  clamp on r26
    fb_op: str = "diff"         # 0x28FA4 subr ("diff", V294) / add ("sum", every other image)
    e_shift: int = 2            # 0x29D76 shl imm5 (2 on V294, 5 elsewhere)
    kp_x: tuple = (0, 68, 112, 136, 208)          # 0xCB994 -> rec
    kp_y: tuple = (960, 960, 960, 960, 960)
    kd_x: tuple = (0, 11, 22, 32)                 # 0xCB7D4 -> rec
    kd_y: tuple = (0, 0, 0, 0)
    d_clamp: int = 0            # 0xC61B6
    ki: int = 0                 # 0xC63E6
    deadband: int = 4           # 0xC62E4
    i_clamp: int = 10240        # 0xC61BA
    p_clamp: int = 15360        # 0xC61BC
    sum_clamp: int = 15360      # 0xC61BE (<= 32767: ld.h assign)
    lag_a: int = 992            # 0xC63EC s16 output-lag pole
    lag_b: int = 507            # 0xC63EE u16
    gain: int = 5346            # 0xC6CD0 (via the displacement at 0x2A1F0)
    t_clamp: int = 3072         # 0xC61B4 lane clamp (<= 32767)
    map_x: tuple = (0, 12, 20, 24, 32, 64, 96, 128, 160, 240)          # 0xC9A88 -> rec
    map_y: tuple = (0, 52, 86, 103, 138, 275, 413, 550, 688, 1032)
    idx_clamp: int = 240        # 0xC64F0/0xC64F1 (byte)
    G_same: tuple = ((32, 42, 80, 112), (255, 255, 255, 0))           # 0xCB924 (demand arm, |bar>>5| axis)
    G_opp: tuple = ((32, 38, 80, 112), (255, 255, 255, 0))            # 0xCB8B4
    taperB: tuple = ((0, 3, 6, 8, 10, 20), (255, 255, 255, 255, 255, 205))   # 0xCBC34  F1 on gp-0x6830
    taperD: tuple = ((16, 26, 38, 48, 64, 96), (255, 243, 218, 179, 77, 77))  # 0xCBBC4  F2 on |bar>>5|
    image_sha256: str = ""

    def replace(self, **kw):
        kw.setdefault("name", self.name + "*")
        return replace(self, **kw)

    # -------- readers
    @staticmethod
    def from_image(path, name="image", sha=None):
        b = open(path, "rb").read()
        h = hashlib.sha256(b).hexdigest()
        if sha is not None and h != sha:
            raise RuntimeError("image hash mismatch %s: %s" % (path, h))
        hw = _u16(b, 0x29D76)
        if (hw >> 5) & 0x3F != 0x16:
            raise ValueError("0x29D76 is not shl imm5")
        op = (_u16(b, 0x28FA4) >> 5) & 0x3F
        fb_op = {0x0E: "sum", 0x0C: "diff"}[op]
        kpx, kpy = _rec(b, 0xCB994, 5)
        kdx, kdy = _rec(b, 0xCB7D4, 4)
        mx, my = _rec(b, 0xC9A88, 10)
        gain_addr = 0xBF000 + _u16(b, 0x2A1F0)
        return Cells(name=name, fb_a=_s16(b, 0xC63E8), fb_b=_u16(b, 0xC63EA), fb_clamp=_u16(b, 0xC62E6), fb_op=fb_op,
                     e_shift=hw & 0x1F, kp_x=kpx, kp_y=kpy, kd_x=kdx, kd_y=kdy, d_clamp=_u16(b, 0xC61B6),
                     ki=_u16(b, 0xC63E6), deadband=_u16(b, 0xC62E4), i_clamp=_u16(b, 0xC61BA), p_clamp=_u16(b, 0xC61BC),
                     sum_clamp=_u16(b, 0xC61BE), lag_a=_s16(b, 0xC63EC), lag_b=_u16(b, 0xC63EE), gain=_s16(b, gain_addr),
                     t_clamp=_u16(b, 0xC61B4), map_x=mx, map_y=my, idx_clamp=b[0xC64F0],
                     G_same=_rec(b, 0xCB924, 4), G_opp=_rec(b, 0xCB8B4, 4), taperB=_rec(b, 0xCBC34, 6),
                     taperD=_rec(b, 0xCBBC4, 6), image_sha256=h)

    @staticmethod
    def v294():
        return Cells.from_image(IMG["V294"][0], "V294", IMG["V294"][1])

    @staticmethod
    def v293():
        return Cells.from_image(IMG["V293"][0], "V293")

    @staticmethod
    def v282():
        return Cells.from_image(IMG["V282"][0], "V282")

    # -------- static facts
    @property
    def b_max(self):
        """census: the fb state at the |x| = 12000 bail edge must stay below 2^31: a*b*12000/(1024-a) < 2^31."""
        if self.fb_op != "diff" and self.fb_op != "sum":
            return float("nan")
        return (2 ** 31) * (1024 - self.fb_a) / (12000.0 * self.fb_a) if 0 < self.fb_a < 1024 else float("inf")

    def problems(self):
        """static checks against the firmware's hard limits (census sections 3-5).  Returns a list of strings; an empty
        list means none found.  These are LATENT DEFECTS of the arithmetic, not stability claims."""
        p = []
        if not (0 <= self.fb_a <= 1023):
            p.append("fb_a %d outside 0..1023 (1024 = integrator; ld.h signed)" % self.fb_a)
        if self.fb_b > self.b_max:
            p.append("fb_b %d > b_max %.0f: the fb state overflows int32 at |x| = 12000" % (self.fb_b, self.b_max))
        for nm in ("sum_clamp", "t_clamp"):
            if getattr(self, nm) > 32767:
                p.append("%s > 32767: ld.hu compare / ld.h assign sign defect" % nm)
        if max(self.map_y) > 32767:
            p.append("map Y > 32767: mulh is signed")
        for nm in ("G_same", "G_opp"):
            if max(getattr(self, nm)[1]) * 255 > 65535:
                p.append("%s Y*255 > 65535: the &0xFFFF wraps" % nm)
        if max(self.taperB[1]) * max(self.taperD[1]) > 65535:
            p.append("taper F1*F2 > 65535: the &0xFFFF wraps")
        if not (0 <= self.lag_a <= 1023):
            p.append("lag_a outside 0..1023")
        for nm in ("kp_x", "kd_x", "map_x"):
            X = getattr(self, nm)
            if any(X[i + 1] < X[i] for i in range(len(X) - 1)):
                p.append("%s not non-decreasing" % nm)
        if len(self.kp_x) != 5 or len(self.kd_x) != 4 or len(self.map_x) != 10:
            p.append("knot counts are fixed by code (Kp 5, Kd 4, map 10)")
        if not (0 <= self.e_shift <= 31):
            p.append("e_shift is a 5-bit immediate")
        if self.idx_clamp > 255:
            p.append("idx is a byte")
        return p

    def edit_class(self, base):
        """which edit class a candidate needs relative to `base`: 'cal-only', 'opcode' (fb_op / e_shift), or both."""
        d = self.diff(base)
        ops = {k for k in d if k in ("fb_op", "e_shift")}
        return ("opcode+cal" if len(d) > len(ops) else "opcode") if ops else ("cal-only" if d else "identical")

    def diff(self, other):
        a, b = asdict(self), asdict(other)
        return {k: (b[k], a[k]) for k in a if k not in ("name", "image_sha256") and a[k] != b[k]}


def lerp_table(X, Y, n=256):
    """the firmware's integer LERP walk (golden model lkas_rate_lerp: flat outside, trunc-toward-zero divide) for x=0..n-1."""
    import eps_lkas_chain_model as M
    X, Y = [int(v) for v in X], [int(v) for v in Y]
    return np.array([M.lkas_rate_lerp(X, Y, i) for i in range(n)], np.int64)


# ======================================================================================================================
# SECTION 2 -- the lane: byte-exact, batch, int64 with an int32 guard
# ======================================================================================================================
class Lane:
    """a BATCH of B independent V294-class LKAS lanes (cells may differ per lane).

    Per 1 ms tick (census section 2; every line mirrors the golden model's lkas_fb_lag + lkas_rate_pid_tick):
      s_new = (a*s >> 10) + (b*x >> 10) ; r26 = clamp(s_new - s | s + s_new, +-C) ; s = s_new        0x28F86..0x28FBE
      E = (sp << e_shift) - r26                                                                          0x29D76/78
      I = clamp((I8>>3) + ((dbz(E>>5)*Ki)>>3), +-(Icl<<10)>>3) ; I8 = I<<3                               0x29D7C..0x2A190
      P = clamp((E*Kp[idx])>>8, +-Pcl)                                                                   0x29E36/3E
      D = clamp(((E - E_prev*)*Kd[idx])>>3, +-Dcl) ; E_prev = E  (* = E when |E_prev| > 768000)         0x29E5E..0x29F06
      S = clamp((m*((I>>7)+P+D))>>8, +-Scl)                                                              0x29F18..0x2A160
      o' = (la*o>>10) + (S*lb>>10) ; y = (o+o')>>5 ; o = o'                                              0x2A174..0x2A1AC
      T = clamp((sxh(y)*gain)>>15, +-Tcl)                                                                0x2A1E6..0x2A23C
    The guard raises Int32Overflow on any 32-bit product/sum leaving [-2^31, 2^31) and on |y| > 32767 (the sxh).
    Bails (|x| > 12000) mirror the firmware: r26 = 0, the PID skipped (I = 0, E_prev poisoned, S = 0 into the output lag),
    and the next tick restarts the fb state from 0 (the sentinel) -- the restart pulse.
    """

    def __init__(self, cells, B=None, guard=True):
        if isinstance(cells, Cells):
            cells = [cells] * (B or 1)
        self.cells = list(cells)
        B = len(self.cells)
        self.B = B
        self.guard = guard
        g = lambda k: np.array([getattr(c, k) for c in self.cells], np.int64)  # noqa: E731
        self.fa, self.fb, self.fcl = g("fb_a"), g("fb_b"), g("fb_clamp")
        self.diffop = np.array([c.fb_op == "diff" for c in self.cells])
        self.esh = g("e_shift")
        self.dcl, self.ki, self.db, self.pcl, self.scl = g("d_clamp"), g("ki"), g("deadband"), g("p_clamp"), g("sum_clamp")
        self.icl = (g("i_clamp") << 10) >> 3
        self.la, self.lb, self.gain, self.tcl = g("lag_a"), g("lag_b"), g("gain"), g("t_clamp")
        self.idxcl = g("idx_clamp")
        cache = {}

        def tab(X, Y):
            k = (tuple(int(v) for v in X), tuple(int(v) for v in Y))
            if k not in cache:
                cache[k] = lerp_table(*k)
            return cache[k]
        self.kp_tab = np.stack([tab(c.kp_x, c.kp_y) for c in self.cells])
        self.kd_tab = np.stack([tab(c.kd_x, c.kd_y) for c in self.cells])
        self.map_tab = np.stack([tab(c.map_x, c.map_y) for c in self.cells])
        self.Gs_tab = np.stack([tab(*c.G_same) for c in self.cells])
        self.Go_tab = np.stack([tab(*c.G_opp) for c in self.cells])
        self.tB_tab = np.stack([tab(*c.taperB) for c in self.cells])
        self.tD_tab = np.stack([tab(*c.taperD) for c in self.cells])
        self.rows = np.arange(B)
        self.any_i = bool(np.any(self.ki != 0))
        self.any_d = bool(np.any((self.dcl != 0) & (self.kd_tab.max(axis=1) != 0)))
        self.reset()

    def reset(self):
        B = self.B
        self.s = np.zeros(B, np.int64)
        self.restart = np.zeros(B, bool)
        self.I8 = np.zeros(B, np.int64)
        self.Eprev = np.full(B, 0x7FFFFFFF, np.int64)
        self.o = np.zeros(B, np.int64)
        self.n_bail = np.zeros(B, np.int64)
        self.last = {}

    def set_state(self, s=None, o=None, I8=None):
        if s is not None:
            self.s = np.asarray(s, np.int64).copy() * np.ones(self.B, np.int64)
        if o is not None:
            self.o = np.asarray(o, np.int64).copy() * np.ones(self.B, np.int64)
        if I8 is not None:
            self.I8 = np.asarray(I8, np.int64).copy() * np.ones(self.B, np.int64)

    def _chk(self, name, *arrs):
        for a in arrs:
            if a.size and (a.max() >= I32 or a.min() < -I32):
                j = int(np.argmax(np.abs(a)))
                raise Int32Overflow("int32 overflow at %s: %d (lane %d, %s)" % (name, int(a.flat[j]), j,
                                                                                  self.cells[j % self.B].name))

    # ---- the demand chain (per 100 Hz frame): 0xE4 handler -> idx, sign, taper
    def demand(self, wire, bar=None, dbar6=None):
        """wire: 0xE4 counts (+ right); bar: firmware torsion-bar counts (gp-0x682f = min(|bar>>5|, 254)); dbar6:
        gp-0x6830 (|delta filtered bar|>>6; None = 0 -> F1 = 255).  Returns (idx, sp in the march convention, m)."""
        wire = np.asarray(np.round(wire), np.int64) * np.ones(self.B, np.int64)
        bar = np.zeros(self.B, np.int64) if bar is None else np.asarray(np.round(bar), np.int64) * np.ones(self.B, np.int64)
        S = np.clip(-4 * wire, -0x4000, 0x4000)
        bar5 = np.minimum(np.abs(bar >> 5), 254)
        same = np.sign(S) == np.sign(bar)
        G = np.where(same, self.Gs_tab[self.rows, bar5], self.Go_tab[self.rows, bar5])
        prod = (((G * 255) & 0xFFFF) * S) >> 16
        v = np.clip(prod >> 6, -self.idxcl, self.idxcl)
        idx = np.abs(v)
        sgn_fw = np.where(v < 0, -1, 1)
        sp = -sgn_fw * self.map_tab[self.rows, idx]
        d6 = np.zeros(self.B, np.int64) if dbar6 is None else np.clip(np.asarray(dbar6, np.int64), 0, 255)
        F1 = self.tB_tab[self.rows, d6]
        F2 = self.tD_tab[self.rows, bar5]
        m = ((F1 * F2) & 0xFFFF) >> 8
        return idx, sp, m

    # ---- one 1 kHz tick
    def tick(self, x, sp, idx, m, keep=False):
        x = np.asarray(x, np.int64)
        bail = np.abs(x) > 12000
        s_old = np.where(self.restart, 0, self.s)
        p1 = self.fa * s_old
        xb = np.where(bail, 0, x)
        p2 = self.fb * xb
        if self.guard:
            self._chk("a*s (0x28F92 mul)", p1)
            self._chk("b*x (0x28F8E mul)", p2)
        s_new = (p1 >> 10) + (p2 >> 10)
        r26 = np.where(self.diffop, s_new - s_old, s_new + s_old)
        if self.guard:
            self._chk("s_new / r26 (0x28FA2/0x28FA4)", s_new, r26)
        r26 = np.clip(r26, -self.fcl, self.fcl)
        self.s = np.where(bail, self.s, s_new)
        self.restart = bail
        r26 = np.where(bail, 0, r26)
        E = (sp << self.esh) - r26
        if self.guard:
            self._chk("E (0x29D76 shl / 0x29D78 sub)", E)
        if self.any_i:
            e5 = E >> 5
            exc = np.where(e5 > self.db, e5 - self.db, np.where(e5 < -self.db, e5 + self.db, 0))
            p3 = exc * self.ki
            I = np.clip((self.I8 >> 3) + (p3 >> 3), -self.icl, self.icl)
            I8 = I << 3
            if self.guard:
                self._chk("exc*Ki (0x29DA8 mul) / 8*I (0x2A190)", p3, I8)
            self.I8 = np.where(bail, 0, I8)
            I = np.where(bail, 0, I)
        else:
            I = np.zeros(self.B, np.int64)
        kp = self.kp_tab[self.rows, idx]
        p4 = E * kp
        if self.guard:
            self._chk("E*Kp (0x29E36 mul)", p4)
        P = np.clip(p4 >> 8, -self.pcl, self.pcl)
        if self.any_d:
            kd = self.kd_tab[self.rows, idx]
            r27 = np.where(np.abs(self.Eprev) <= 768000, self.Eprev, E)
            dE = E - r27
            p5 = dE * kd
            if self.guard:
                self._chk("dE*Kd (0x29EE4 mul)", dE, p5)
            D = np.clip(p5 >> 3, -self.dcl, self.dcl)
        else:
            D = np.zeros(self.B, np.int64)
        self.Eprev = np.where(bail, 0x7FFFFFFF, E)
        Ssum = (I >> 7) + P + D
        p6 = m * Ssum
        if self.guard:
            self._chk("sum / taper*S (0x29F24, 0x2A0BE mul)", Ssum, p6)
        S = np.clip(p6 >> 8, -self.scl, self.scl)
        S = np.where(bail, 0, S)
        p7 = self.la * self.o
        p8 = S * self.lb
        if self.guard:
            self._chk("la*o / S*lb (output lag)", p7, p8)
        o2 = (p7 >> 10) + (p8 >> 10)
        y = (self.o + o2) >> 5
        self.o = o2
        if self.guard and y.size and np.abs(y).max() > 32767:
            raise Int32Overflow("y leaves the 16-bit sxh at 0x2A1EA: %d" % int(np.abs(y).max()))
        p9 = y * self.gain
        T = np.clip(p9 >> 15, -self.tcl, self.tcl)
        self.n_bail += bail
        if keep:
            self.last = dict(r26=r26, E=E, I=I, P=P, D=D, S=S, y=y, T=T)
        return T, r26

    # ---- convenience: open-loop march over a recorded x (1 kHz) and frame arrays (100 Hz)
    def march(self, x1k, sp100, idx100, m100, keep=()):
        n = x1k.shape[-1]
        x1k = np.atleast_2d(x1k)
        T = np.zeros((self.B, n), np.int64)
        K = {k: np.zeros((self.B, n), np.int64) for k in keep}
        for i in range(n):
            k = i // 10
            t, _ = self.tick(x1k[:, i] * np.ones(self.B, np.int64), np.atleast_1d(sp100[..., k]) * np.ones(self.B, np.int64),
                             np.atleast_1d(idx100[..., k]) * np.ones(self.B, np.int64),
                             np.atleast_1d(m100[..., k]) * np.ones(self.B, np.int64), keep=bool(keep))
            T[:, i] = t
            for kk in keep:
                K[kk][:, i] = self.last[kk]
        return (T, K) if keep else T


def surface(cells, idx=None, fb=0, m=254):
    """the DELIVERED SURFACE T(idx) at constant command and constant fb operand (golden model lkas_rate_pid_surface,
    marched from the cold-boot state).  Returns an int array over idx."""
    import eps_lkas_chain_model as M
    cal = golden_cal(cells)
    idx = range(0, cells.idx_clamp + 1) if idx is None else idx
    return np.array([M.lkas_rate_pid_surface(int(i), cal, fb=fb, taper=m)["T"] for i in idx])


def golden_cal(c):
    """the golden model's Calibration for a Cells (every PID field)."""
    import eps_lkas_chain_model as M
    return replace(M.Calibration(), fb_clamp=int(c.fb_clamp), fb_lag_a=int(c.fb_a), fb_lag_b=int(c.fb_b),
                   fb_op=c.fb_op, e_shift=int(c.e_shift), kp_x=tuple(int(v) for v in c.kp_x),
                   kp_y=tuple(int(v) for v in c.kp_y), kd_x=tuple(int(v) for v in c.kd_x),
                   kd_y=tuple(int(v) for v in c.kd_y), pid_d_clamp=int(c.d_clamp), pid_ki=int(c.ki),
                   pid_err_deadband=int(c.deadband), pid_i_clamp=int(c.i_clamp), pid_p_clamp=int(c.p_clamp),
                   sum_clamp=int(c.sum_clamp), out_lag_a=int(c.lag_a), out_lag_b=int(c.lag_b),
                   lkas_forward_gain=int(c.gain), out_clamp=int(c.t_clamp),
                   assist_map_x=tuple(int(v) for v in c.map_x), assist_map_y=tuple(int(v) for v in c.map_y))


# ======================================================================================================================
# SECTION 3 -- the plant family (v294_plant), kappa(angle), stress members, a batch stepper
# ======================================================================================================================
KAPPA_BINS = np.array([0.0, 5.0, 10.0, 20.0, 40.0, 80.0, 160.0, 400.0])
KAPPA_VALS = np.array([1.148, 1.151, 1.142, 1.125, 1.056, 0.978, 0.963])   # metric agent's 7-route table, bin mid-values


def _kappa_map():
    """W(theta_rack) with dW/dtheta = kappa(W), odd; kappa(|W|) piecewise-constant on the metric agent's bins
    (EVIDENCE: 0x14A angle change vs the integrated 0x18F rate, 7 routes, 4 builds).  Returns (rack grid, wheel grid)."""
    Wg = np.linspace(0.0, 500.0, 50001)
    kap = KAPPA_VALS[np.clip(np.searchsorted(KAPPA_BINS, Wg, side="right") - 1, 0, len(KAPPA_VALS) - 1)]
    th = np.concatenate([[0.0], np.cumsum(np.diff(Wg) / kap[:-1])])
    return th, Wg


_KM = None


def wheel_from_rack(th):
    global _KM
    if _KM is None:
        _KM = _kappa_map()
    a = np.abs(th)
    return np.sign(th) * np.interp(a, _KM[0], _KM[1])


def rack_from_wheel(W):
    global _KM
    if _KM is None:
        _KM = _kappa_map()
    return np.sign(W) * np.interp(np.abs(W), _KM[1], _KM[0])


def family(include_stress=True):
    """the v294_plant family + the harness's stress members.  Each is a speed-scheduled PlantFamilyMember; `kappa` and
    the two-mass modes are harness options on top (members carry them as attributes)."""
    import v294_plant as VP
    fam = VP.family()
    out = dict(fam)
    nom = fam["nominal"]
    out["J_0.3"] = replace(nom, name="J_0.3", J=np.full(len(nom.J), 0.3), note="nominal with J 0.3 (not refitted: stress)")
    if include_stress:
        out["mode13"] = nom.with_mode20(f2=13.0, zeta2=0.1, r2=0.2)
        out["mode13"].name = "mode13"
        out["mode20"] = nom.with_mode20(f2=20.0, zeta2=0.05, r2=0.2)
        out["mode20"].name = "mode20"
        out["mode20_lo"] = nom.with_mode20(f2=20.0, zeta2=0.02, r2=0.5)
        out["mode20_lo"].name = "mode20_lo"
        out["tau9"] = replace(nom, name="tau9", tau_ms=9, note="nominal, delay x1.5 of the 6 ms corner")
    for k in list(out):
        out[k].kappa = False
    out["nominal_kappa"] = replace(nom, name="nominal_kappa", note="nominal + kappa(angle) rack->wheel map (stress)")
    out["nominal_kappa"].kappa = True
    return out


class PlantBatch:
    """v294_plant.simulate's arithmetic, restructured as a per-tick stepper for a batch of B plants (possibly different
    members), so a closed loop can interleave the fork, the lane and the plant.  With kappa off it reproduces
    v294_plant.simulate to machine precision (gate H2a).  State in the plant's own angle (the fit's theta, + left)."""

    def __init__(self, members, th0, om0, c0=None, x_noise=0.0, seed=0):
        self.members = list(members)
        B = len(self.members)
        self.B = B
        self.th = np.asarray(th0, float).copy()
        self.om = np.asarray(om0, float).copy()
        self.two = np.array([m.f2 > 0 for m in self.members])
        self.thw, self.omw = self.th.copy(), self.om.copy()
        self.w = np.array([max(int(m.rate_win_ms), 1) for m in self.members])
        self.tau = np.array([int(m.tau_ms) for m in self.members])
        W = int(self.w.max())
        self.hist = np.zeros((B, W))
        for i in range(B):                       # back-filled along om0 (v294_plant: hist = th - om*(w - k)*1e-3)
            w = self.w[i]
            self.hist[i, :w] = self.th[i] - self.om[i] * (w - np.arange(w)) * 1e-3
        self.hp = np.zeros(B, int)
        TL = int(self.tau.max()) + 1
        self.Tbuf = np.zeros((B, TL))
        self.tp = np.zeros(B, int)
        self.c0 = np.zeros(B) if c0 is None else np.asarray(c0, float).copy()
        self.x_noise = x_noise
        self.rng = np.random.default_rng(seed)
        self.kappa = np.array([bool(getattr(m, "kappa", False)) for m in self.members])
        self.v_last = None
        self.x = np.zeros(B, np.int64)
        self.xr = np.zeros(B)

    def set_speed(self, v):
        v = np.asarray(v, float)
        if self.v_last is not None and np.array_equal(v, self.v_last):
            return
        self.v_last = v.copy()
        J, b, k, Fc, Fs, sat = (np.zeros(self.B) for _ in range(6))
        if not hasattr(self, "_groups"):
            g = {}
            for i, m in enumerate(self.members):
                g.setdefault(id(m), (m, []))[1].append(i)
            self._groups = [(m, np.array(r)) for m, r in g.values()]
        for m, rows in self._groups:
            a = m.arrays_at(v[rows])
            J[rows], b[rows], k[rows], Fc[rows], Fs[rows], sat[rows] = a["J"], a["b"], a["k"], a["Fc"], a["Fs"], a["sat"]
        self.J, self.b, self.k, self.Fc, self.Fs, self.sat = J, b, k, Fc, Fs, sat
        self.ksat = k * sat
        f2 = np.array([m.f2 for m in self.members])
        z2 = np.array([m.zeta2 for m in self.members])
        r2 = np.array([m.r2 for m in self.members])
        self.Jw = np.where(self.two, J * r2, 0.0)
        self.Jm = np.where(self.two, J - self.Jw, J)
        mu = np.where(self.two, self.Jm * np.maximum(self.Jw, 1e-12) / J, 0.0)
        self.Ktb = np.where(self.two, (2 * np.pi * f2) ** 2 * mu, 0.0)
        self.ctb = np.where(self.two, 2 * z2 * np.sqrt(self.Ktb * mu), 0.0)

    def sense(self):
        """the rate former at this tick: x = round(8*(th - th[n-w])/(w ms)) (+ optional white noise), saturated at 12000."""
        rows = np.arange(self.B)
        old = self.hist[rows, self.hp]
        xr = 8.0 * (self.th - old) / (self.w * DT)
        if self.x_noise:
            xr = xr + self.rng.normal(0.0, self.x_noise, self.B)
        self.xr = xr
        self.x = np.clip(np.round(xr), -12000, 12000).astype(np.int64)
        return self.x

    def step(self, T, d=None):
        """apply the delivered torque T (tap sign) written this tick; advance one tick (semi-implicit Euler, Karnopp)."""
        rows = np.arange(self.B)
        self.Tbuf[rows, self.tp] = T
        self.tp = (self.tp + 1) % (self.tau + 1)
        u = -self.Tbuf[rows, self.tp] + self.c0
        if d is not None:
            u = u + d
        th, om = self.th, self.om
        fnet = u - self.ksat * np.tanh(th / self.sat) - self.b * om
        if self.two.any():
            fnet = fnet - self.Ktb * (th - self.thw) - self.ctb * (om - self.omw)
        stuck = (om == 0.0) & (np.abs(fnet) <= self.Fs)
        fdir = np.where(om != 0.0, np.sign(om), np.sign(fnet))
        om_new = om + np.where(stuck, 0.0, (fnet - self.Fc * fdir) / self.Jm) * DT
        om_new[stuck | ((om != 0.0) & (np.sign(om_new) != np.sign(om)))] = 0.0
        if self.two.any():
            Jw = np.where(self.two, self.Jw, 1.0)
            self.omw = np.where(self.two, self.omw + (self.Ktb * (th - self.thw) + self.ctb * (om - self.omw)) / Jw * DT,
                                self.omw)
            self.thw = np.where(self.two, self.thw + self.omw * DT, self.thw)
        self.hist[rows, self.hp] = th
        self.hp = (self.hp + 1) % self.w
        self.om = om_new
        self.th = th + om_new * DT

    def wheel_angle(self):
        """the angle the 0x14A sensor reports (two-mass: the wheel side, as v294_plant records it), through kappa."""
        th = np.where(self.two, self.thw, self.th)
        return np.where(self.kappa, wheel_from_rack(th), th)


# ======================================================================================================================
# SECTION 4 -- the fork: a vectorised port of the generic LatControlTorque path as flown (r1), + the real code
# ======================================================================================================================
G_ACC = 9.81
ACCORD_SR_BP = np.array([0.0, 23.0, 31.0, 61.0, 76.0, 95.0, 116.0, 151.0, 178.0, 227.0, 236.0, 303.0, 380.0])
ACCORD_SR_V = np.array([16.88, 16.88, 16.88, 16.25, 15.97, 15.45, 15.03, 14.68, 14.45, 14.09, 14.25, 12.98, 12.31])


class ForkPort:
    """the r1 path of LatControlTorque (Dom 20d24ab79) for a batch, line for line (latcontrol_torque.py update(), generic
    branch; every Accord term off by the r1 toggles, so their code is not reached or is an exact pass-through) plus
    controlsd's VM update with the Accord SR map.  Proven equal to the real code by h3 (gate H3b).  Constants are read
    from the extracted fork source at construction, not retyped (except the SR map, asserted equal)."""

    def __init__(self, B, toggles, cp=None, dt=0.01):
        import fork_real as FK
        FK.setup()
        from openpilot.selfdrive.controls.lib import latcontrol_torque as LT
        from openpilot.selfdrive.controls.lib import latcontrol_vehicle_tunes as VT
        from opendbc.car.vehicle_model import VehicleModel, calc_slip_factor
        assert np.array_equal(ACCORD_SR_BP, VT.HONDA_ACCORD_STEER_RATIO_ANGLE_BP)
        assert np.array_equal(ACCORD_SR_V, VT.HONDA_ACCORD_STEER_RATIO_V)
        tg = toggles
        self.B, self.dt = B, dt
        self.kp = float(np.interp(0.0, tg["steerKp"][0], tg["steerKp"][1]))
        assert len(tg["steerKp"][0]) == 1, "the port assumes a flat SteerKP"
        self.ki = float(tg["accord_torque_ki"]) if float(tg.get("accord_torque_ki_high", 0.0)) <= 0 else None
        assert self.ki is not None, "the port assumes AccordTorqueKiHigh 0 (flat Ki)"
        for k, want in (("accord_rate_plant_ff", False), ("accord_error_notch_q", 0.0), ("accord_ref_filter", 0.0),
                        ("accord_turn_ff_taper", False), ("accord_dither", 0.0), ("nnff", False), ("nnff_lite", False),
                        ("flm_trial_applied", False), ("trailer_load_kg", 0.0)):
            assert tg.get(k, want) == want, "the port covers the r1 path only: %s = %r" % (k, tg.get(k))
        self.laf = float(np.float32(tg["latAccelFactor"]))
        self.fric = float(np.float32(tg["friction"]))
        self.sr_scale = min(max(float(tg["steerRatio"]) / VT.HONDA_ACCORD_STEER_RATIO_NOMINAL,
                                VT.HONDA_ACCORD_STEER_RATIO_LEVEL_MIN), VT.HONDA_ACCORD_STEER_RATIO_LEVEL_MAX)
        self.jerk_lp_hz = float(tg.get("accord_jerk_lp_hz", LT.LP_FILTER_CUTOFF_HZ))
        CP = FK.make_CP()
        VM = VehicleModel(CP)
        self.sf = calc_slip_factor(VM)
        self.chi, self.l = VM.chi, VM.l
        self.LT, self.VT = LT, VT
        self.buf_len = int(LT.LAT_ACCEL_REQUEST_BUFFER_SECONDS / dt)
        self.MIN_SPEED = LT.MIN_SPEED
        self.low_speed_reset = max(CP.minSteerSpeed, LT.MIN_LATERAL_CONTROL_SPEED)
        self.a_jerk = dt / (1.0 / (2.0 * np.pi * max(self.jerk_lp_hz, 0.1)) + dt)
        self.a_mrate = dt / (1 / (2 * np.pi * (LT.MAX_LAT_JERK_UP - 0.5)) + dt)
        grid = np.linspace(0.0, 40.0, 4001)
        thr_g = np.array([VT.get_standard_friction_threshold(float(v)) for v in grid])
        assert np.all(thr_g == thr_g[0]), "the friction threshold is not flat; the port needs it per speed"
        self.thr = float(thr_g[0])
        from openpilot.common.constants import ACCELERATION_DUE_TO_GRAVITY as G_OP
        from opendbc.car import ACCELERATION_DUE_TO_GRAVITY as G_DBC
        self.g_op, self.g_dbc = float(G_OP), float(G_DBC)
        self.reset()

    def reset(self):
        B = self.B
        self.buf = np.zeros((B, self.buf_len))
        self.head = 0                        # index of the NEXT write; buf[(head - d) % len] = the d-th most recent
        self.jx = np.zeros(B)
        self.mx = np.zeros(B)
        self.prev_meas = np.zeros(B)
        self.prev_des = np.zeros(B)
        self.i = np.zeros(B)
        self.prev_pressed = np.zeros(B, bool)
        self.p = np.zeros(B)
        self.f = np.zeros(B)

    def curvature(self, ang_rel_deg, v, roll):
        """-VM.calc_curvature(radians(angle - offset), v, roll) with sR = the Accord map at that angle x level."""
        sr = np.interp(np.abs(ang_rel_deg), ACCORD_SR_BP, ACCORD_SR_V) * self.sr_scale
        cf = (1. - self.chi) / (1. - self.sf * v ** 2) / self.l
        rc = (self.g_dbc * roll) / ((1 / self.sf) - v ** 2)
        return -((cf * np.radians(ang_rel_deg) / sr) + rc)

    def step(self, active, v, angle, pressed, ang_off, roll, des_curv, lat_delay, laf_off, steer_limited):
        """one 100 Hz frame for the batch; returns actuators.torque (+left) and the torqueState fields."""
        B = self.B
        dt = self.dt
        LT = self.LT
        active = np.asarray(active, bool) * np.ones(B, bool)
        v = np.asarray(v, float) * np.ones(B)
        meas = self.curvature(np.asarray(angle, float) - ang_off, v, roll) * v ** 2
        fut = des_curv * v ** 2
        laf_off = np.asarray(laf_off, np.float32).astype(float) * np.ones(B)
        out = np.zeros(B)
        # ---------------- inactive frames (latcontrol_torque.py lines 255-270)
        na = ~active
        # ---------------- active frames
        rel = self.prev_pressed & ~np.asarray(pressed, bool)
        self.i = np.where(active & rel, self.i * 0.8, self.i)
        fade = np.interp(v, LT.FF_ROLL_OFFSET_FADE_BP, LT.FF_ROLL_OFFSET_FADE_V)
        roll_comp = roll * self.g_op * fade
        delay_frames = np.clip(lat_delay / dt, 1, self.buf_len).astype(int) * np.ones(B, int)
        expected = self.buf[np.arange(B), (self.head - delay_frames) % self.buf_len] * v ** 2
        self.buf[:, self.head] = des_curv
        self.head = (self.head + 1) % self.buf_len
        raw_jerk = np.clip((fut - expected) / np.maximum(lat_delay, dt), -LT.MAX_LAT_JERK_UP, LT.MAX_LAT_JERK_UP)
        jx = (1. - self.a_jerk) * self.jx + self.a_jerk * raw_jerk
        jerk = np.clip(jx, -LT.MAX_LAT_JERK_UP, LT.MAX_LAT_JERK_UP)
        grav = fut - roll_comp
        setpoint = expected + jerk * lat_delay
        des_rate = (setpoint - self.prev_des) / dt
        unwind = (des_rate < LT.UNWIND_D_DES_THRESHOLD) & (np.abs(setpoint) < LT.UNWIND_LAT_ACCEL_NEAR_ZERO)
        mx = (1. - self.a_mrate) * self.mx + self.a_mrate * ((meas - self.prev_meas) / dt)
        lsf = (np.interp(v, LT.LOW_SPEED_X, LT.LOW_SPEED_Y) / np.maximum(v, self.MIN_SPEED)) ** 2
        error = setpoint - meas
        err_lsf = error * (1 + lsf / max(self.kp, 1e-3))
        ff = grav
        ff = ff - laf_off * fade
        thr = self.thr                                           # get_standard_friction_threshold == 0.30 at every speed
        sdz = np.interp(np.maximum(v, 0.0), LT.CENTER_CHATTER_JERK_DEADZONE_SPEED_BP, LT.CENTER_CHATTER_JERK_DEADZONE_SPEED_V)
        cw = np.interp(np.abs(setpoint), LT.CENTER_CHATTER_JERK_DEADZONE_LAT_ACCEL_BP, LT.CENTER_CHATTER_JERK_DEADZONE_LAT_ACCEL_V)
        fjdz = np.maximum(0.0, sdz * cw)
        fj = np.copysign(np.maximum(np.abs(jerk) - fjdz, 0.0), jerk)
        fl = self.fric * self.laf
        xf = err_lsf + LT.JERK_GAIN * fj
        ff = ff + 1.0 * np.interp(xf, [-thr, thr], [-fl, fl])  # get_friction (deadzone 0: apply_center_deadzone is identity)
        lowv = v < self.low_speed_reset
        i0 = np.where(lowv, 0.0, self.i)
        freeze = np.asarray(steer_limited, bool) | np.asarray(pressed, bool) | lowv | unwind
        # 🛑 the PID is fed `pid_log.error`, READ BACK from a capnp Float32 field (latcontrol_torque.py line 697:
        # self.pid.update(pid_log.error, ...)), so P and I see the float32-rounded error; friction saw the float64 one.
        e32 = err_lsf.astype(np.float32).astype(float)
        p = self.kp * e32
        pos, neg = 1.0 * self.laf, -1.0 * self.laf
        i_new = i0 + self.ki * (1.0 / (1 / dt)) * e32
        test = p + i_new + 0.0 + ff
        ub = np.where(test > pos, i0, pos)
        lb = np.where(test < neg, i0, neg)
        i_upd = np.where(freeze, i0, np.clip(i_new, lb, ub))
        ctrl = np.clip(p + i_upd + 0.0 + ff, neg, pos)
        otq = ctrl / self.laf
        # commit
        self.i = np.where(active, i_upd, 0.0)
        self.jx = np.where(active, jx, 0.0)
        self.mx = np.where(active, mx, 0.0)
        self.prev_meas = meas
        self.prev_des = np.where(active, setpoint, fut)
        self.p = np.where(active, p, 0.0)
        self.f = np.where(active, ff, 0.0)
        out = np.where(active, otq, 0.0)
        self.prev_pressed = np.asarray(pressed, bool) * np.ones(B, bool)
        return dict(torque=-out, p=self.p, i=self.i, f=self.f, output=-out, la_des=np.where(active, setpoint, 0.0),
                    la_act=meas, jerk=np.where(active, jerk, 0.0), error=np.where(active, err_lsf, 0.0))


def honda_limiter(cmd, last, delta=0.03):
    lim = np.clip(cmd, last - delta, last + delta)
    can = np.trunc(np.clip(-lim * 4096.0, -4096, 4096)).astype(np.int64)
    return lim, can


# ======================================================================================================================
# SECTION 5 -- the route: r71b chunks, warm-start states, the disturbance
# ======================================================================================================================
_ROUTE = None


def route():
    """r71b on the 100 Hz 0x18F frame axis (plib's cache: the byte-exact march, tap alignment) + the fork's logged
    inputs sampled at the same frames.  Cached in memory."""
    global _ROUTE
    if _ROUTE is not None:
        return _ROUTE
    import plib as P
    import r71b_cache as RC
    d = P.load()
    D = RC.load(with_raw=False)
    t = d["t"]
    ip = lambda ts: np.clip(np.searchsorted(ts, t, side="right") - 1, 0, len(ts) - 1)  # noqa: E731
    for k in ("cs_angle", "cs_rate", "cs_vego", "cs_pressed"):
        d[k + "_f"] = D[k][ip(D["cs_t"])]
    for k in ("ctl_des_curv", "ctl_la_act", "ctl_la_des", "ctl_p", "ctl_i", "ctl_f", "ctl_output", "ctl_active",
              "ctl_jerk_des", "ctl_error"):
        d[k + "_f"] = D[k][ip(D["ctl_t"])]
    d["lpar_off_f"] = D["lpar_off"][ip(D["lpar_t"])]
    d["lpar_roll_f"] = D["lpar_roll"][ip(D["lpar_t"])]
    d["ltp_off_f"] = D["ltp_off"][ip(D["ltp_t"])]
    d["delay_f"] = D["ldel_delay"][ip(D["ldel_t"])] + 0.1
    d["sd_active_f"] = D["sd_active"][ip(D["sd_t"])]
    d["cc_lat_active_f"] = D["cc_lat_active"][ip(D["cc_t"])]
    d["e4_f"] = D["e4_cmd"][ip(D["e4_t"])]
    d["co_torque_f"] = D["co_torque"][ip(D["co_t"])]
    d["toggles"] = D["meta"]["starpilot_toggles"]["first"]["toggles"]
    d["x18_f"] = -d["wire"]                           # the 0x18F rate in x counts (8/deg/s), + left
    _ROUTE = d
    return d


def route_chunks(min_s=10.0, max_s=60.0, bands=None, pre_s=1.5):
    """hands-off laterally-engaged runs (steeringPressed dilated +-0.5 s), cut into <= max_s chunks.  Each chunk is
    (a, b) frame indices on the route grid, with a warm-up of pre_s seconds before a available."""
    d = route()
    pressed = d["cs_pressed_f"] > 0.5
    k = np.ones(101)
    pbuf = np.convolve(pressed.astype(float), k, "same") > 0
    ho = d["eng"] & ~pbuf & (d["ctl_active_f"] > 0.5) & (d["cc_lat_active_f"] > 0.5)
    import plib as P
    out = []
    for a, b in P.runs(ho, int(min_s * 100)):
        a = max(a, int(pre_s * 100))
        n = b - a
        nch = int(math.ceil(n / (max_s * 100)))
        L = n // nch
        for j in range(nch):
            out.append((a + j * L, a + (j + 1) * L if j < nch - 1 else b))
    if bands is not None:
        vm = [(np.mean(d["v"][a:b])) for a, b in out]
        out = [c for c, vv in zip(out, vm) if any(lo <= vv < hi for _, lo, hi in bands)]
    return out


def chunk_c0(member, a, b, dist="c0"):
    """the constant (or low-passed) torque nuisance the plant needs on this chunk: mean over the chunk of
    J*al + b*om + spring(th) + Fc*sgn(om) - u, with u the byte-exact live march (plib), members' own parameters
    (the plant study's oe_lib per-window offset, EVIDENCE of its use there).  dist='lp' returns a 0.1 Hz low-passed
    time series (100 Hz) instead of a constant."""
    d = route()
    v = d["v"][a:b]
    ar = member.arrays_at(v)
    th, om = d["th"][a:b], d["om"][a:b]
    al = np.gradient(om) * 100.0
    spring = ar["k"] * ar["sat"] * np.tanh(th / ar["sat"])
    res = ar["J"] * al + ar["b"] * om + spring + ar["Fc"] * np.sign(om) - (-d["T_live"][a:b])
    if dist == "lp":
        bb, aa = signal.butter(1, 0.1 / 50.0)
        return signal.filtfilt(bb, aa, res)
    if dist == "full":
        return res                        # DISTURBANCE REPLAY: the drive's own residual under this member (100 Hz)
    return float(np.mean(res))


# ======================================================================================================================
# SECTION 6 -- the closed-loop engine
# ======================================================================================================================
@dataclass
class SimOpts:
    mode: str = "B"                 # "A" recorded command, "B" recorded planner demand through the fork
    pipe_ms: int = 22               # 0x14A sample -> 0xE4 effective at the EPS (20 ms measured to the bus + ~2 ms, BELIEF)
    x_noise: float = 1.93           # counts rms, white (plant study: standstill, not engaged)
    dist: str = "c0"                # "c0" per-chunk constant, "lp" 0.1 Hz residual, "none"
    probe: float = 0.0              # mode A: band-limited (0.3-8 Hz) exogenous command noise, as a fraction of cmd rms
    probe_seed: int = 7
    angle_q: float = 0.1            # 0x14A angle LSB, deg
    null_shadow: bool = True        # run a C = 0 twin of every lane on the same command -> the FF/trim split
    seed: int = 0
    real_fork: bool = False         # True: the real LatControlTorque (slow, one instance per lane)


def simulate(cells_list, members, chunks, opts=None, record_1k=False, progress=False):
    """closed-loop (or open-loop) simulation of every (cells, member, chunk) combination as ONE batch.
    cells_list: list of Cells; members: list of PlantFamilyMember; chunks: list of (a, b) route frames.
    Returns a dict of 100 Hz arrays shaped (n_cells, n_members, n_chunks, n_frames_max) + masks."""
    o = opts or SimOpts()
    d = route()
    cells_list = list(cells_list)
    members = list(members)
    combos = [(ci, mi, ki) for ci in range(len(cells_list)) for mi in range(len(members)) for ki in range(len(chunks))]
    B = len(combos)
    lens = np.array([chunks[k][1] - chunks[k][0] for _, _, k in combos])
    NF = int(lens.max())
    a0 = np.array([chunks[k][0] for _, _, k in combos])
    lane = Lane([cells_list[c] for c, _, _ in combos])
    shadow = Lane([cells_list[c].replace(fb_clamp=0, name="null") for c, _, _ in combos]) if o.null_shadow else None
    # plant initial state from the measured angle / rate at the chunk start
    mem_b = [members[m] for _, m, _ in combos]
    kap = np.array([bool(getattr(mm, "kappa", False)) for mm in mem_b])
    th0 = d["th"][a0]
    th0 = np.where(kap, rack_from_wheel(th0), th0)
    om0 = d["om"][a0]
    c0 = np.zeros(B)
    dlp = None
    if o.dist == "c0":
        c0 = np.array([chunk_c0(members[m], chunks[k][0], chunks[k][1]) for _, m, k in combos])
    elif o.dist in ("lp", "full"):
        dlp = np.zeros((B, NF))
        for j, (_, m, k) in enumerate(combos):
            s = chunk_c0(members[m], chunks[k][0], chunks[k][1], dist=o.dist)
            dlp[j, :len(s)] = s
            dlp[j, len(s):] = s[-1]
    plant = PlantBatch(mem_b, th0, om0, c0=c0, x_noise=o.x_noise, seed=o.seed)
    # lane states: WARM-UP of each lane with ITS OWN cells over the 1.5 s before the chunk, on the recorded 0xE4 command
    # and the recorded (up-sampled) 0x18F rate -- so a candidate starts in its own consistent fb / output-lag / I state,
    # not in V294's (which would inject a spurious restart-like transient at every chunk start).
    WL = 150
    x1k = d["x1k"]
    for L_ in ([lane] if shadow is None else [lane, shadow]):
        L_.reset()
        for kk in range(WL, 0, -1):
            fr = a0 - kk
            idx_w, sp_w, m_w = L_.demand(d["e4_f"][fr])
            for t_ in range(10):
                xi = np.clip(np.round(x1k[fr * 10 + t_]), -12000, 12000).astype(np.int64)
                L_.tick(xi, sp_w, idx_w, m_w)
    # exogenous series per lane (100 Hz), padded with the last value
    def ex(key):
        arr = np.zeros((B, NF))
        for j in range(B):
            s = d[key][a0[j]:a0[j] + lens[j]]
            arr[j, :lens[j]] = s
            arr[j, lens[j]:] = s[-1] if len(s) else 0
        return arr
    V = ex("cs_vego_f")
    CMD = ex("e4_f") if o.mode == "A" else None
    if o.mode == "A" and o.probe > 0:
        rng = np.random.default_rng(o.probe_seed)
        bb, aa = signal.butter(2, [0.3 / 50, 8.0 / 50], btype="band")
        for j in range(B):
            nz = signal.lfilter(bb, aa, rng.normal(size=NF))
            nz *= o.probe * np.std(CMD[j, :lens[j]]) / max(np.std(nz[:lens[j]]), 1e-9)
            CMD[j] = CMD[j] + nz
    fork = None
    if o.mode == "B":
        DES, ROLL, OFF, LOFF, DEL, SDA = ex("ctl_des_curv_f"), ex("lpar_roll_f"), ex("lpar_off_f"), ex("ltp_off_f"), \
            ex("delay_f"), ex("sd_active_f")
        tg = d["toggles"]
        fork = ForkPort(B, tg)
        reals = None
        if o.real_fork:
            import fork_real as FK
            reals = [FK.RealController(tg) for _ in range(B)]
            R_dev = np.zeros(B)
        # warm-up: replay the logged inputs over the pre-chunk window (the controller's filters and 1 s buffer), then
        # set the integrator to its logged value at the chunk start
        W = 150
        for kk in range(W, 0, -1):
            idx = a0 - kk
            args = (d["ctl_active_f"][idx] > 0.5, d["cs_vego_f"][idx], d["cs_angle_f"][idx], d["cs_pressed_f"][idx] > 0.5,
                    d["lpar_off_f"][idx], d["lpar_roll_f"][idx], d["ctl_des_curv_f"][idx], d["delay_f"][idx],
                    d["ltp_off_f"][idx], np.zeros(B, bool))
            fork.step(*args)
            if reals is not None:
                for j, rc in enumerate(reals):
                    rc.step(bool(args[0][j]), float(args[1][j]), float(args[2][j]), 0.0, bool(args[3][j]), float(args[4][j]),
                            float(args[5][j]), float(args[6][j]), float(args[7][j]), float(args[8][j]), False)
        fork.i = d["ctl_i_f"][a0 - 1].astype(float).copy()
        if reals is not None:
            for j, rc in enumerate(reals):
                rc.LaC.pid.i = float(fork.i[j])
        last_tq = d["co_torque_f"][a0 - 1].astype(float).copy()    # the Honda limiter's state (carOutput torque)
    # outputs
    R = {k: np.zeros((B, NF)) for k in ("ang", "rate18", "T", "T_null", "cmd", "la_act", "la_des", "p", "i", "f", "torque",
                                        "om", "x", "slew")}
    pipe = int(o.pipe_ms)
    T1k = np.zeros((B, NF * 10), np.int16) if record_1k else None
    qcmd = np.zeros((B, NF + 4))      # command queue by frame (effective at tick 10k + pipe)
    wire_eff = CMD[:, 0].copy() if o.mode == "A" else d["e4_f"][a0].astype(float)
    idx, sp, m = lane.demand(wire_eff)
    if shadow is not None:
        idx_n, sp_n, m_n = shadow.demand(wire_eff)
    steer_lim = np.zeros(B, bool)
    T = np.zeros(B, np.int64)
    Tn = np.zeros(B, np.int64)
    t_start = time.time()
    N = NF * 10
    k_last_cmd = -1
    for n in range(N):
        k = n // 10
        if n % 10 == 0:
            plant.set_speed(V[:, k])
            ang_w = plant.wheel_angle()
            ang_q = np.round(ang_w / o.angle_q) * o.angle_q
            R["ang"][:, k] = ang_q
            R["om"][:, k] = plant.om
            if o.mode == "B":
                r = fork.step(np.ones(B, bool), V[:, k], ang_q, np.zeros(B, bool), OFF[:, k], ROLL[:, k], DES[:, k],
                              DEL[:, k], LOFF[:, k], steer_lim)
                if reals is not None:          # the REAL controller drives the loop; the port shadows it on the same inputs
                    rr = [rc.step(True, float(V[j, k]), float(ang_q[j]), 0.0, False, float(OFF[j, k]), float(ROLL[j, k]),
                                  float(DES[j, k]), float(DEL[j, k]), float(LOFF[j, k]), bool(steer_lim[j]))
                          for j, rc in enumerate(reals)]
                    for kk in ("torque", "p", "i", "f", "la_des", "la_act", "output"):
                        rv = np.array([x_[kk] for x_ in rr])
                        R_dev = np.maximum(R_dev, np.abs(rv - r[kk]))
                        r[kk] = rv                    # the port's own state is NOT re-synchronised: deviations accumulate
                tq = r["torque"]
                lim, can = honda_limiter(tq, last_tq)
                R["slew"][:, k] = np.abs(tq - lim) > 1e-9
                steer_lim = np.where(SDA[:, k] > 0.5, np.abs(tq - lim) > 1e-2, steer_lim)
                last_tq = lim
                qcmd[:, k] = can
                for kk in ("la_act", "la_des", "p", "i", "f", "torque"):
                    R[kk][:, k] = r[kk]
            else:
                qcmd[:, k] = CMD[:, k]
        # the command computed at frame k becomes effective at tick 10k + pipe
        if (n - pipe) >= 0 and (n - pipe) % 10 == 0:
            kc = (n - pipe) // 10
            wire_eff = qcmd[:, kc]
            idx, sp, m = lane.demand(wire_eff)
            if shadow is not None:
                idx_n, sp_n, m_n = shadow.demand(wire_eff)
            k_last_cmd = kc
        x = plant.sense()
        xl = -x                                           # lane operand = +0x18F raw = -8*omega_left
        T, _ = lane.tick(xl, sp, idx, m)
        if shadow is not None:
            Tn, _ = shadow.tick(xl, sp_n, idx_n, m_n)
        plant.step(T.astype(float), None if dlp is None else dlp[:, k])
        if T1k is not None:
            T1k[:, n] = T
        if n % 10 == 9:
            R["T"][:, k] = T
            R["T_null"][:, k] = Tn
            R["cmd"][:, k] = wire_eff
            R["rate18"][:, k] = x / 8.0
            R["x"][:, k] = x
        if progress and n % 20000 == 0 and n:
            print("   sim %d/%d ticks  %.1f s" % (n, N, time.time() - t_start))
    R["lens"] = lens
    R["combos"] = combos
    R["a0"] = a0
    R["v"] = V
    R["la_plan"] = (ex("ctl_des_curv_f") * V ** 2) if o.mode == "B" else None
    R["runtime_s"] = time.time() - t_start
    R["opts"] = asdict(o)
    R["n_bail"] = lane.n_bail.copy()
    R["T1k"] = T1k
    if o.mode == "B" and o.real_fork:
        R["port_vs_real_maxdev"] = R_dev
    return R


# ======================================================================================================================
# SECTION 7 -- linear analysis: the inner return ratio, the controller gain, stress-mode damping, the outer loop
# ======================================================================================================================
def lane_ctf(c, f, m=254, kind="T"):
    """the lane's LINEAR transfer from the operand x (counts) to T (kind "T") or to P+D+I before the taper (kind "P"),
    at sp = 0, clamps ignored, deadband ignored (I = Ki*E/(32*8) per tick into the sum as I>>7).  1 kHz, exact z."""
    z = np.exp(2j * np.pi * np.asarray(f, float) * DT)
    zi = 1.0 / z
    a, b = c.fb_a / 1024.0, c.fb_b / 1024.0
    if c.fb_clamp == 0:
        R = 0.0 * z
    else:
        R = b * ((1 - zi) if c.fb_op == "diff" else (1 + zi)) / (1 - a * zi)
    E = -R
    kp = float(lerp_table(c.kp_x, c.kp_y)[0])
    kd = float(lerp_table(c.kd_x, c.kd_y)[0]) if c.d_clamp else 0.0
    P = kp / 256.0 * E
    D = kd / 8.0 * (1 - zi) * E
    I = (c.ki / (32.0 * 8.0 * 128.0)) * E / (1 - zi) if c.ki else 0.0 * z
    PID = P + D + I
    if kind == "P":
        return PID
    S = m / 256.0 * PID
    la, lb = c.lag_a / 1024.0, c.lag_b / 1024.0
    y = lb * (1 + zi) / (32.0 * (1 - la * zi)) * S
    return y * c.gain / 32768.0


def plant_theta_frf(p, f):
    """theta/u (deg per T count) of the linear plant incl. its transport delay (v294_plant.linear_frf / s)."""
    import v294_plant as VP
    s = 2j * np.pi * np.asarray(f, float)
    return VP.linear_frf(p, f) / s


def loop_frf(c, p, f, m=254):
    """the INNER return ratio L(f) = -8 * C_T(z) * RF(z) * ZOH * theta/u, with L = 0 for a muted operand; closed loop
    sensitivity 1/(1+L).  x_lane = -8*omega; the rate former RF = (1 - z^-w)/(w*dt); u = -T."""
    f = np.asarray(f, float)
    z = np.exp(2j * np.pi * f * DT)
    w = max(int(p.rate_win_ms), 1)
    RF = (1 - z ** (-w)) / (w * DT)
    zoh = np.exp(-1j * np.pi * f * DT) * np.sinc(f * DT)
    CT = lane_ctf(c, f, m)
    # u_c = -T = -CT * x_lane = -CT * (-8 * RF * theta) ; loop G = u_c/u = 8*CT*RF*zoh*Ptheta ; L = -G (1/(1+L) form).
    # Equivalently L = (T/omega) * s * Ptheta with T/omega = -8*CT*RF/s the census "opposing torque" (damping > 0).
    return -8.0 * CT * RF * zoh * plant_theta_frf(p, f)


def trim_T_per_omega(c, f, m=254, w=3):
    """the trim's opposing torque per deg/s of wheel rate, T/omega = -8 * C_T * RF/s (census c6 table's quantity:
    0 deg = pure damping, +90 = inertia).  The census quotes 1.86 at +13 deg at 2.5 Hz for V294 (second method)."""
    f = np.asarray(f, float)
    z = np.exp(2j * np.pi * f * DT)
    s = 2j * np.pi * f
    RF = (1 - z ** (-w)) / (w * DT)
    return -8.0 * lane_ctf(c, f, m) * RF / s


def margins(f, L):
    """crossovers (|L| = 1), phase margins, gain margins (at -180 deg), Ms = max|1/(1+L)|."""
    mag = np.abs(L)
    ph = np.unwrap(np.angle(L))
    out = dict(Ms=float(np.max(np.abs(1.0 / (1.0 + L)))), f_Ms=float(f[int(np.argmax(np.abs(1.0 / (1.0 + L))))]))
    xc = np.flatnonzero(np.diff(np.sign(mag - 1.0)) != 0)
    out["crossovers_hz"] = [float(f[i]) for i in xc]
    out["PM_deg"] = [float(180.0 + np.degrees(np.angle(L[i]))) for i in xc]
    pc = np.flatnonzero(np.diff(np.sign(np.sin(np.angle(L)))) != 0)
    gm = [(float(f[i]), float(1.0 / max(mag[i], 1e-12))) for i in pc if np.cos(np.angle(L[i])) < 0]
    out["GM"] = gm
    out["GM_min"] = min([g for _, g in gm], default=float("inf"))
    out["PM_min"] = min(out["PM_deg"], default=float("inf"))
    return out


def linear_modes(p, c, m=254):
    """exact 1 kHz linear poles of plant + lane (golden arithmetic without floors/clamps): v294_plant.linear_poles with
    the lane's fb pole/gain/Kp; the output lag and gain are the census values.  Only V294-structure lanes (diff operand,
    flat Kp, no I/D) are supported by that routine -- others return None."""
    import v294_plant as VP
    if c.fb_op != "diff" or c.ki or (c.d_clamp and any(c.kd_y)) or len(set(c.kp_y)) != 1 or c.fb_clamp == 0:
        if c.fb_clamp == 0:
            return VP.linear_poles(p, lane_on=False)[1]
        return None
    cells = dict(fb_a=c.fb_a, fb_b=c.fb_b, kp_Y=list(c.kp_y), e_shift=c.e_shift, lag_a=c.lag_a, lag_b=c.lag_b,
                 gain=c.gain)
    return VP.linear_poles(p, cells=cells, m=m)[1]


def mode_damping(p, c, band=(8.0, 40.0)):
    """the least-damped oscillatory closed-loop pair in `band` (a stress member's flexible mode): (f, zeta)."""
    md = linear_modes(p, c)
    if md is None:
        return (float("nan"), float("nan"))
    osc = [(f, z) for f, z, _ in md if band[0] < f < band[1]]
    return min(osc, key=lambda t: t[1]) if osc else (float("nan"), float("nan"))


# ======================================================================================================================
# SECTION 8 -- metrics (the same code on the drive and on the sim)
# ======================================================================================================================
def _bp(x, lo, hi, fs=100.0, order=2):
    b, a = signal.butter(order, [lo / (fs / 2), hi / (fs / 2)], btype="band")
    return signal.filtfilt(b, a, x) if len(x) > 3 * max(len(a), len(b)) * 3 else np.zeros_like(x)


def _trimmed(x, cut=100):
    return x[cut:-cut] if len(x) > 2 * cut + 10 else x[:0]


def drive_metrics(S, band_list=BANDS):
    """per speed band, from lists of per-chunk 100 Hz series S[name] = [arr per chunk] (the SAME code for sim and drive):
    tracking gain (S2's polyfit slope of la_act on la_plan), turn-hold (median la_act/la_plan at |plan| 0.8-1.5,
    |d plan/dt| < 0.5), integrator share (mean |i|/(|f|+|p|+|i|)), cmd rms, trim/FF rms ratio, wheel-rate rms in
    0.3-1 / 1-3 / 3-8 Hz, 1.6-3 Hz wheel-rate rms in hard turns, dwell-then-jump per minute (th 0.25), J-style lat-accel
    error rms 0.15-2.4 Hz, straight delivery (mean|act|/mean|plan| at |plan| < 0.4), exposure."""
    import v293_symptom_instruments as SI  # noqa: F401  (dwell detector below is its code, called directly)
    out = {}
    for nm, lo, hi in band_list:
        acc = {k: [] for k in ("plan", "act", "p", "i", "f", "cmd", "T", "Tn", "r_lo", "r_mid", "r_hi", "hard16", "je",
                               "dpl", "slew")}
        dw_n, dw_t = 0, 0.0
        tsec = 0.0
        for j in range(len(S["v"])):
            v = S["v"][j]
            mk = (v >= lo) & (v < hi)
            if mk.sum() < 100:
                continue
            tsec += mk.sum() / 100.0
            plan, act = S["la_plan"][j], S["la_act"][j]
            acc["plan"].append(plan[mk]); acc["act"].append(act[mk])
            dpl = np.gradient(plan) * 100.0
            acc["dpl"].append(dpl[mk])
            for k in ("p", "i", "f"):
                acc[k].append(S[k][j][mk])
            acc["cmd"].append(S["cmd"][j][mk])
            if "slew" in S:
                acc["slew"].append(S["slew"][j][mk])
            acc["T"].append(S["T"][j][mk]); acc["Tn"].append(S["T_null"][j][mk])
            r = S["rate"][j]
            cut = np.zeros(len(r), bool)
            cut[100:-100] = True
            mm = mk & cut
            for key, (flo, fhi) in (("r_lo", (0.3, 1.0)), ("r_mid", (1.0, 3.0)), ("r_hi", (3.0, 8.0))):
                acc[key].append(_bp(r, flo, fhi)[mm])
            hard = (np.abs(plan) >= 1.5) | (np.abs(S["ang"][j]) > 60)
            acc["hard16"].append(_bp(r, 1.6, 3.0)[mm & hard])
            e = plan - act
            acc["je"].append(_bp(e, 0.15, 2.4)[mm])
            # dwells (v293_symptom_instruments.dwells, th 0.25, runs >= 2 s)
            ker = np.ones(10) / 10.0
            for a, b in SI.runs_of(mk, 200):
                rs = np.convolve(np.abs(r[a:b]), ker, "same")
                dw_n += len(SI.runs_of(rs < 0.25, 20))
                dw_t += (b - a) / 100.0
        if tsec < 1.0:
            continue
        cat = {k: (np.concatenate(v) if v else np.zeros(0)) for k, v in acc.items()}
        res = dict(sec=tsec)
        pl, ac = cat["plan"], cat["act"]
        sel = np.abs(pl) > 0.3
        # pre-registered form (CRITERIA-HARNESS.md H4): slope over |plan| > 0.3 m/s^2; S2's own form (all frames) beside it
        res["track_gain"] = float(np.polyfit(pl[sel], ac[sel], 1)[0]) if sel.sum() > 200 else float("nan")
        res["track_gain_all"] = float(np.polyfit(pl, ac, 1)[0]) if len(pl) > 200 else float("nan")
        hm = (np.abs(pl) >= 0.8) & (np.abs(pl) < 1.5) & (np.abs(cat["dpl"]) < 0.5)
        res["turn_hold"] = float(np.median(ac[hm] / pl[hm])) if hm.sum() > 200 else float("nan")
        res["turn_hold_n"] = int(hm.sum())
        tot = np.abs(cat["f"]) + np.abs(cat["p"]) + np.abs(cat["i"]) + 1e-9
        res["i_share"] = float(np.mean(np.abs(cat["i"]) / tot)) if len(tot) else float("nan")
        res["cmd_rms"] = float(np.sqrt(np.mean(cat["cmd"] ** 2)))
        res["slew_share"] = float(np.mean(cat["slew"])) if len(cat["slew"]) else float("nan")
        trim = cat["T"] - cat["Tn"]
        res["trim_ff"] = float(np.sqrt(np.mean(trim ** 2)) / max(np.sqrt(np.mean(cat["Tn"] ** 2)), 1e-9))
        for key in ("r_lo", "r_mid", "r_hi"):
            res[key] = float(np.sqrt(np.mean(cat[key] ** 2))) if len(cat[key]) else float("nan")
        res["hard16"] = float(np.sqrt(np.mean(cat["hard16"] ** 2))) if len(cat["hard16"]) > 500 else float("nan")
        res["hard_sec"] = len(cat["hard16"]) / 100.0
        res["dwell_per_min"] = 60.0 * dw_n / dw_t if dw_t > 5 else float("nan")
        res["J_err"] = float(np.sqrt(np.mean(cat["je"] ** 2))) if len(cat["je"]) else float("nan")
        st = np.abs(pl) < 0.4
        res["straight_delivery"] = float(np.mean(np.abs(ac[st])) / max(np.mean(np.abs(pl[st])), 1e-9)) if st.sum() > 200 else float("nan")
        out[nm] = res
    return out


def drive_series_measured(chunks):
    """the drive's own series on the chunk frames (for the SAME drive_metrics code)."""
    d = route()
    S = {k: [] for k in ("v", "la_plan", "la_act", "p", "i", "f", "cmd", "T", "T_null", "rate", "ang")}
    for a, b in chunks:
        v = d["cs_vego_f"][a:b]
        S["v"].append(d["v"][a:b])
        S["la_plan"].append(d["ctl_des_curv_f"][a:b] * d["v"][a:b] ** 2)
        S["la_act"].append(d["ctl_la_act_f"][a:b])
        S["p"].append(d["ctl_p_f"][a:b]); S["i"].append(d["ctl_i_f"][a:b]); S["f"].append(d["ctl_f_f"][a:b])
        S["cmd"].append(d["e4_f"][a:b])
        S["T"].append(d["T_live"][a:b]); S["T_null"].append(d["T_null"][a:b])
        S["rate"].append(d["x18_f"][a:b] / 8.0)
        S["ang"].append(d["th"][a:b])
        co = d["co_torque_f"][a - 1:b]                  # the Honda limiter binds when the carOutput step equals 0.03
        S.setdefault("slew", []).append(np.abs(np.diff(co)) >= 0.0299)
    return S


def drive_series_sim(R, sel):
    """the sim's series for the combos in `sel` (list of batch rows)."""
    S = {k: [] for k in ("v", "la_plan", "la_act", "p", "i", "f", "cmd", "T", "T_null", "rate", "ang", "slew")}
    for j in sel:
        n = R["lens"][j]
        S["v"].append(R["v"][j, :n])
        S["la_plan"].append(R["la_plan"][j, :n] if R["la_plan"] is not None else np.zeros(n))
        S["la_act"].append(R["la_act"][j, :n])
        for k in ("p", "i", "f", "cmd", "T", "T_null", "ang", "slew"):
            S[k].append(R[k][j, :n])
        S["rate"].append(R["rate18"][j, :n])
    return S


HF_BANDS = ((5, 9), (9, 13), (13, 17), (17, 23), (23, 30))


def hf_content(T, fs=1000.0):
    """delivered-torque rms (T counts) in 5-9 / 9-13 / 13-17 / 17-23 / 23-30 Hz of a 1 kHz trace (zero-phase 4th-order
    Butterworth band-passes, 0.5 s trimmed each end)."""
    out = {}
    x = np.asarray(T, float)
    for lo, hi in HF_BANDS:
        b, a = signal.butter(2, [lo / (fs / 2), hi / (fs / 2)], btype="band")
        y = signal.filtfilt(b, a, x - x.mean())
        cut = int(0.5 * fs)
        out["%d-%d" % (lo, hi)] = float(np.sqrt(np.mean(y[cut:-cut] ** 2))) if len(y) > 3 * cut else float("nan")
    return out


# ======================================================================================================================
# SECTION 9 -- general linear tools: closed-loop modes for ANY cells, the outer loop, the FF path
# ======================================================================================================================
def closed_loop_modes(p, c, m=254, lane_on=True):
    """exact 1 kHz LINEAR closed loop of plant (rigid or two-mass, semi-implicit Euler as PlantBatch) + rate former + the
    lane for ANY cells (fb op sum/diff, I, D, any flat-at-idx-0 gains) + transport delay, at sp = 0 (clamps, floors and
    the dead band ignored).  Returns [(f Hz, zeta)] of the complex pairs (real poles as (0, zeta 1)).  Second method for
    V294-structure lanes: v294_plant.linear_poles (h5 checks they agree)."""
    kp = float(lerp_table(c.kp_x, c.kp_y)[0])
    kd = float(lerp_table(c.kd_x, c.kd_y)[0]) if (c.d_clamp and lane_on) else 0.0
    a, b = c.fb_a / 1024.0, c.fb_b / 1024.0
    la, lb, G = c.lag_a / 1024.0, c.lag_b / 1024.0, c.gain / 32768.0
    ki = c.ki / (8.0 * 32.0) if lane_on else 0.0
    on = lane_on and c.fb_clamp != 0
    w = max(int(p.rate_win_ms), 1)
    tau = int(p.tau_ms)
    two = p.f2 > 0
    if two:
        Jw = p.J * p.r2
        Jm = p.J - Jw
        mu = Jm * Jw / p.J
        K = (2 * np.pi * p.f2) ** 2 * mu
        cc = 2 * p.zeta2 * np.sqrt(K * mu)
    else:
        Jm = p.J
    ix = dict(th=0, om=1)
    k0 = 2
    if two:
        ix["thw"], ix["omw"] = 2, 3
        k0 = 4
    ix["h"] = k0
    ix["s"], ix["Ep"], ix["I"], ix["o"] = k0 + w, k0 + w + 1, k0 + w + 2, k0 + w + 3
    ix["T"] = k0 + w + 4
    N = ix["T"] + tau

    def step(z):
        th, om = z[0], z[1]
        hist = z[ix["h"]:ix["h"] + w]
        x = 8.0 * (th - hist[w - 1]) / (w * DT)
        s, Ep, I, o = z[ix["s"]], z[ix["Ep"]], z[ix["I"]], z[ix["o"]]
        if on:
            s_new = a * s + b * (-x)
            r26 = (s_new - s) if c.fb_op == "diff" else (s_new + s)
            E = -r26
        else:
            s_new, E = 0.0, 0.0                 # a muted operand: the fb state is decoupled -> eigenvalue 0, not 1
        I_new = (I + ki * E) if ki else 0.0     # Ki = 0: the accumulator is identically zero (decoupled)
        S = (m / 256.0) * (I_new / 128.0 + (kp / 256.0) * E + (kd / 8.0) * (E - Ep))
        o_new = la * o + lb * S
        T = G * (o + o_new) / 32.0
        Tq = z[ix["T"]:ix["T"] + tau]
        u = -(Tq[tau - 1] if tau > 0 else T)
        fnet = u - p.b * om - p.k * th
        zn = np.zeros(N)
        if two:
            thw, omw = z[ix["thw"]], z[ix["omw"]]
            fnet = fnet - K * (th - thw) - cc * (om - omw)
            omw_new = omw + DT * (K * (th - thw) + cc * (om - omw)) / Jw
            zn[ix["thw"]], zn[ix["omw"]] = thw + DT * omw_new, omw_new
        om_new = om + DT * fnet / Jm
        zn[0], zn[1] = th + DT * om_new, om_new
        zn[ix["h"]] = th
        zn[ix["h"] + 1:ix["h"] + w] = hist[:w - 1]
        zn[ix["s"]], zn[ix["Ep"]], zn[ix["I"]], zn[ix["o"]] = s_new, E, I_new, o_new
        if tau > 0:
            zn[ix["T"]] = T
            zn[ix["T"] + 1:ix["T"] + tau] = Tq[:tau - 1]
        return zn

    A = np.column_stack([step(e) for e in np.eye(N)])
    ev = np.linalg.eigvals(A)
    modes = []
    for zp in ev:
        if abs(zp) < 1e-9:
            continue
        s_ = np.log(zp) / DT
        f = abs(s_.imag) / (2 * np.pi)
        zeta = -s_.real / abs(s_) if abs(s_) > 0 else 1.0
        if s_.imag >= 0:
            modes.append((float(f), float(zeta)))
    modes.sort()
    return modes, float(np.max(np.abs(ev)))


def stress_damping(c, p, band):
    md, rho = closed_loop_modes(p, c)
    osc = [(f, z) for f, z in md if band[0] < f < band[1] and f > 0]
    return (min(osc, key=lambda t: t[1]) if osc else (float("nan"), float("nan"))), rho


def ff_tf(c, f, idx_op=60, m=254):
    """the FEEDFORWARD path wire count -> T (tap sign) as a linear transfer: small-signal map slope at idx_op, the
    e_shift, Kp (+ the Kd setpoint kick, + I on the command) at idx_op, taper m, output lag, gain.  1 kHz z; the 100 Hz
    command ZOH is a separate factor (outer_frf)."""
    z = np.exp(2j * np.pi * np.asarray(f, float) * DT)
    zi = 1 / z
    mt = lerp_table(c.map_x, c.map_y)
    i0, i1 = max(idx_op - 8, 0), min(idx_op + 8, c.idx_clamp)
    slope = (mt[i1] - mt[i0]) / float(i1 - i0)                          # sp counts per idx
    sp_per_wire = slope / WIRE_PER_IDX
    kp = float(lerp_table(c.kp_x, c.kp_y)[idx_op])
    kd = float(lerp_table(c.kd_x, c.kd_y)[idx_op]) if c.d_clamp else 0.0
    E = (2 ** c.e_shift) * sp_per_wire
    PID = (kp / 256.0 + kd / 8.0 * (1 - zi) + (c.ki / (8.0 * 32.0 * 128.0)) / (1 - zi)) * E
    S = m / 256.0 * PID
    y = (c.lag_b / 1024.0) * (1 + zi) / (32.0 * (1 - (c.lag_a / 1024.0) * zi)) * S
    return y * c.gain / 32768.0


def alpha_per_cmd(c, p, f, idx_op=60):
    """closed-form LINEAR wheel acceleration per 0xE4 count (+ right frame, deg/s^2 per count): FF path x plant with the
    inner trim loop closed: alpha_R/cmd = s^2 * Ptheta * ff_tf / (1 + L) (100 Hz ZOH of the command included)."""
    f = np.asarray(f, float)
    s = 2j * np.pi * f
    zoh100 = np.exp(-1j * np.pi * f * 0.01) * np.sinc(f * 0.01)
    L = loop_frf(c, p, f)
    return s ** 2 * plant_theta_frf(p, f) * ff_tf(c, f, idx_op) * zoh100 / (1 + L)


def outer_frf(c, p, v, f, relay=True, pipe_ms=22, idx_op=60, toggles=None):
    """the OUTER return ratio L_o(f) of the flown fork law (r1) around the EPS: meas -> e_lsf = -(1 + lsf/Kp)*meas ->
    Kp + Ki*dt/(1 - z100^-1) (+ the SteerFriction relay's small-signal slope friction*LAF/0.30 per m/s^2) -> /LAF ->
    wire = 4096 * u / LAF -> 100 Hz ZOH + pipe -> ff_tf -> plant with the inner trim loop -> theta -> meas =
    (cf(v)/sR) * v^2 * rad(theta) (fork frame).  Setpoint exogenous.  L_o > 0 at DC = negative feedback."""
    d = route() if toggles is None else None
    tg = toggles or d["toggles"]
    kp = float(tg["steerKp"][1][0])
    ki = float(tg["accord_torque_ki"])
    laf = float(tg["latAccelFactor"])
    fric = float(np.float32(tg["friction"]))
    f = np.asarray(f, float)
    s = 2j * np.pi * f
    z100 = np.exp(s * 0.01)
    lsf = (np.interp(v, [0, 10, 20, 30], [12, 10.5, 8, 5]) / max(v, 1.0)) ** 2
    Cf = (kp + ki * 0.01 / (1 - 1 / z100) + (fric * laf / 0.30 if relay else 0.0)) * (1 + lsf / kp)
    zoh100 = np.exp(-1j * np.pi * f * 0.01) * np.sinc(f * 0.01)
    pipe = np.exp(-s * pipe_ms * 1e-3)
    Lin = loop_frf(c, p, f)
    Pcl = plant_theta_frf(p, f) / (1 + Lin)
    import fork_real as FK
    VMc = _vm_consts()
    sr = 16.88 * (16.84 / 16.88)
    cf = (1. - VMc["chi"]) / (1. - VMc["sf"] * v ** 2) / VMc["l"]
    kla = cf / sr * v ** 2 * np.pi / 180.0
    return kla * Pcl * ff_tf(c, f, idx_op) * zoh100 * pipe * 4096.0 / laf * Cf


_VMC = None


def _vm_consts():
    global _VMC
    if _VMC is None:
        import fork_real as FK
        FK.setup()
        from opendbc.car.vehicle_model import VehicleModel, calc_slip_factor
        VM = VehicleModel(FK.make_CP())
        _VMC = dict(sf=calc_slip_factor(VM), chi=VM.chi, l=VM.l)
    return _VMC


# ======================================================================================================================
# SECTION 10 -- the metric blocks and score()
# ======================================================================================================================
def _bandavg(f, H, lo, hi):
    m = (f >= lo) & (f <= hi)
    return complex(np.mean(H[m])) if m.any() else complex("nan")


def gain_phase_fit(u, a, lo, hi, fs=100.0):
    """the metric agent's (b): alpha_B = a*u_B + b*H[u_B] (H = Hilbert quadrature) -> R2, |G|, phase (+ = alpha leads)."""
    ub, ab = _bp(u, lo, hi, fs), _bp(a, lo, hi, fs)
    cut = int(fs)
    ub, ab = ub[cut:-cut], ab[cut:-cut]
    if len(ub) < 50:
        return dict(R2=float("nan"), G=float("nan"), ph=float("nan"))
    hq = np.imag(signal.hilbert(ub))
    X = np.vstack([ub, hq]).T
    co, *_ = np.linalg.lstsq(X, ab, rcond=None)
    r = ab - X @ co
    R2 = 1 - np.sum(r ** 2) / max(np.sum((ab - ab.mean()) ** 2), 1e-30)
    return dict(R2=float(R2), G=float(np.hypot(*co)), ph=float(np.degrees(np.arctan2(-co[1], co[0]))))


def m_track_from_sim(R, probe_series=None):
    """M_TRACK on a mode-A sim: literal cmd -> alpha (wheel, + right frame, d/dt of the 0x18F-quantised rate) gain-phase
    fit per band, and (if the probe is given) the probe's own transfer (exogenous: coherence and |G|, phase per band)."""
    out = {}
    lit = {b: [] for b in ("0.3-1", "1-3", "3-8")}
    Hp = {}
    for j in range(len(R["lens"])):
        n = R["lens"][j]
        if n < 1000:
            continue
        cmd = R["cmd"][j, :n]
        al = -np.gradient(R["rate18"][j, :n]) * 100.0            # + right frame to match cmd
        for (b, lo, hi) in (("0.3-1", 0.3, 1.0), ("1-3", 1.0, 3.0), ("3-8", 3.0, 8.0)):
            lit[b].append(gain_phase_fit(cmd, al, lo, hi))
    for b in lit:
        L_ = [x for x in lit[b] if np.isfinite(x["R2"])]
        out["lit_" + b] = dict(R2=float(np.median([x["R2"] for x in L_])) if L_ else float("nan"),
                               G=float(np.median([x["G"] for x in L_])) if L_ else float("nan"),
                               ph=float(np.median([x["ph"] for x in L_])) if L_ else float("nan"))
    if probe_series is not None:
        Sxy, Sxx, Syy, f = 0, 0, 0, None
        for j in range(len(R["lens"])):
            n = R["lens"][j]
            if n < 1024:
                continue
            pz = probe_series[j, :n]
            al = -np.gradient(R["rate18"][j, :n]) * 100.0
            f, pxy = signal.csd(pz, al, fs=100.0, nperseg=512)
            _, pxx = signal.welch(pz, fs=100.0, nperseg=512)
            _, pyy = signal.welch(al, fs=100.0, nperseg=512)
            Sxy, Sxx, Syy = Sxy + pxy, Sxx + pxx, Syy + pyy
        H_ = Sxy / np.maximum(Sxx, 1e-30)
        coh = np.abs(Sxy) ** 2 / np.maximum(Sxx * Syy, 1e-30)
        for (b, lo, hi) in (("0.3-1", 0.3, 1.0), ("1-3", 1.0, 3.0), ("3-8", 3.0, 8.0)):
            h = _bandavg(f, H_, lo, hi)
            mm = (f >= lo) & (f <= hi)
            out["probe_" + b] = dict(G=float(abs(h)), ph=float(np.degrees(np.angle(h))), coh=float(np.mean(coh[mm])))
        Hp = dict(f=f, H=H_, coh=coh)
    return out, Hp


def amplitude_flatness(cells_list, members, v=12.0, amps=(30.0, 100.0, 300.0), secs=40.0, seed=11):
    """open-loop (no fork, no disturbance): a band-limited 1-3 Hz command of each rms amplitude about zero, through the
    lane and the plant at constant speed -> |alpha/cmd| (cross-spectral, 1-3 Hz).  Friction makes the small-amplitude
    gain lower (the drive's 0.37 vs 0.89 deg/s^2 per count); the ratio small/large is the flatness."""
    rng = np.random.default_rng(seed)
    NF = int(secs * 100)
    bb, aa = signal.butter(2, [1.0 / 50, 3.0 / 50], btype="band")
    base = signal.lfilter(bb, aa, rng.normal(size=NF))
    base /= np.std(base)
    combos = [(ci, mi, ai) for ci in range(len(cells_list)) for mi in range(len(members)) for ai in range(len(amps))]
    B = len(combos)
    lane = Lane([cells_list[c] for c, _, _ in combos])
    plant = PlantBatch([members[m] for _, m, _ in combos], np.zeros(B), np.zeros(B), x_noise=0.0)
    plant.set_speed(np.full(B, v))
    cmd = np.array([amps[a] * base for _, _, a in combos])
    rate = np.zeros((B, NF))
    for n in range(NF * 10):
        k = n // 10
        if n % 10 == 0:
            idx, sp, mm = lane.demand(cmd[:, k])
        x = plant.sense()
        T, _ = lane.tick(-x, sp, idx, mm)
        plant.step(T.astype(float))
        if n % 10 == 9:
            rate[:, k] = x / 8.0
    out = {}
    for j, (ci, mi, ai) in enumerate(combos):
        al = -np.gradient(rate[j]) * 100.0
        f, pxy = signal.csd(cmd[j, 200:], al[200:], fs=100.0, nperseg=512)
        _, pxx = signal.welch(cmd[j, 200:], fs=100.0, nperseg=512)
        g = _bandavg(f, pxy / np.maximum(pxx, 1e-30), 1.0, 3.0)
        out[(cells_list[ci].name, members[mi].name, amps[ai])] = float(abs(g))
    return out


def staircase_hf(cells_list, slew=123, secs=10.0):
    """the lane's response to the 100 Hz command staircase: a triangle wave of the command at the Honda slew cap
    (123 counts/frame) between -2000 and +2000, x = 0 (no wheel motion) -> delivered-torque rms per HF band (1 kHz)."""
    NF = int(secs * 100)
    tri = np.zeros(NF)
    v = 0.0
    up = True
    for k in range(NF):
        v = v + slew if up else v - slew
        if v >= 2000:
            up = False
        if v <= -2000:
            up = True
        tri[k] = v
    L = Lane(list(cells_list))
    B = L.B
    T = np.zeros((B, NF * 10))
    for n in range(NF * 10):
        k = n // 10
        if n % 10 == 0:
            idx, sp, m = L.demand(np.full(B, tri[k]))
        t, _ = L.tick(np.zeros(B, np.int64), sp, idx, m)
        T[:, n] = t
    return [hf_content(T[j]) for j in range(B)]


def restart_pulse(c, rates_dps=(10.0, 30.0, 100.0, 300.0)):
    """the fb-filter restart (sentinel -> s_old := 0 after a bail) at a steady wheel rate: peak |T| and the time |T|
    stays above 50 counts (lane only, sp = 0, x held; the worst case -- a real wheel would respond)."""
    out = {}
    for w_ in rates_dps:
        L = Lane([c])
        x = np.array([int(round(-8 * w_))], np.int64)
        L.s = np.array([(c.fb_b * x[0]) // max(1024 - c.fb_a, 1)], np.int64)     # the fixed point at constant x
        L.restart = np.array([True])
        T = []
        for _ in range(1500):
            t, _ = L.tick(x, np.zeros(1, np.int64), np.zeros(1, np.int64), np.full(1, 254, np.int64))
            T.append(int(t[0]))
        T = np.abs(np.array(T))
        out[w_] = dict(peak=int(T.max()), ms_above_50=int(np.sum(T > 50)))
    return out


def int32_margins(c):
    """static worst-case magnitudes of every 32-bit product (|x| = 12000 at the bail edge, clamps at their cells) and
    the margin 2^31/|value|.  < 1 = the firmware would wrap."""
    kp = max(c.kp_y); kd = max(c.kd_y) if c.d_clamp else 0
    s_max = c.fb_b * 12000.0 / max(1024 - c.fb_a, 1)
    E_max = (max(c.map_y) << c.e_shift) + c.fb_clamp
    icl = (c.i_clamp << 10) >> 3
    S_pre = icl / 128.0 * (1 if c.ki else 0) + c.p_clamp + c.d_clamp
    o_max = c.sum_clamp * c.lag_b / max(1024 - c.lag_a, 1)
    vals = {"a*s": c.fb_a * s_max, "b*x": c.fb_b * 12000.0, "E*Kp": E_max * kp, "dE*Kd": 2 * E_max * kd,
            "exc*Ki": (E_max / 32.0) * c.ki, "8*I": 8.0 * icl, "taper*S": 255.0 * S_pre,
            "la*o": c.lag_a * o_max, "S*lb": c.sum_clamp * c.lag_b, "y*gain": 2 * o_max / 32.0 * abs(c.gain)}
    return {k: dict(value=float(v), margin=float(I32 / v) if v else float("inf")) for k, v in vals.items()}


def m_safe(c):
    import eps_lkas_chain_model as M
    L = Lane([c])
    rails = {}
    for sgn in (1, -1):                                  # the rail: hold idx 240 for 20 s from cold (covers an I ramp)
        L.reset()
        sp = np.array([sgn * L.map_tab[0, c.idx_clamp]], np.int64)
        for _ in range(20000):
            t, _ = L.tick(np.zeros(1, np.int64), sp, np.array([c.idx_clamp]), np.full(1, 254, np.int64))
        rails[sgn] = int(t[0])
    Tm = max(abs(rails[1]), abs(rails[-1]))
    idx = np.arange(0, 201, 10)
    S = surface(c, idx)
    slope = float(np.polyfit(idx * WIRE_PER_IDX, S, 1)[0])
    capP = surface(c, [0], fb=c.fb_clamp)[0] if c.fb_clamp else 0
    capN = surface(c, [0], fb=-c.fb_clamp)[0] if c.fb_clamp else 0
    cap = max(abs(int(capP)), abs(int(capN)))
    cap_note = ("fb clamp C bounds the trim: cap = the surface at idx 0 with fb = +-C" if not c.ki else
                "Ki > 0: the I winds up on a held fb/command -- the zero-command torque is NOT bounded by C; the number is "
                "where the golden march's output-lag state first repeated (a LOWER bound); the I clamp bounds it at the rail")
    return dict(rail=int(Tm), rail_pos=rails[1], rail_neg=rails[-1], subrail_T_per_wire=slope, trim_cap_T=cap,
                trim_cap_pct_rail=100.0 * cap / max(Tm, 1), cap_note=cap_note,
                T_at_zero_cmd_max=cap, b=c.fb_b, b_max=float(c.b_max), b_over_bmax=c.fb_b / c.b_max,
                int32=int32_margins(c), restart=restart_pulse(c), problems=c.problems(),
                soft_eme="the lane alone cannot reach the 5120-5325 soft-EME band (|T| <= rail); the post-governor total "
                         "adds base assist under driver torque, which the harness does not model (BELIEF: ADV-V293 D1)")


DEFAULT_PLANTS = ("nominal", "b_lo", "F_hi", "J_hi", "light_b", "tau6")
STRESS_PLANTS = ("mode13", "mode20", "mode20_lo", "tau9", "J_hi2", "nominal_kappa")


def m_loop(c, fam, plants, speeds=(3.1, 8.0, 12.0, 17.0, 26.9)):
    fg = np.logspace(-1, np.log10(45.0), 1500)
    out = {}
    for nm in plants:
        for v in speeds:
            p = fam[nm].at(v)
            L = loop_frf(c, p, fg)
            mg = margins(fg, L)
            m13 = (fg > 1) & (fg < 3)
            m38 = (fg > 3) & (fg < 8)
            L15 = loop_frf(c, replace(p, tau_ms=int(round(p.tau_ms * 1.5))), fg)
            mg15 = margins(fg, L15)
            md, rho = closed_loop_modes(p, c)
            out[(nm, v)] = dict(L13=float(np.mean(np.abs(L[m13]))), L38=float(np.mean(np.abs(L[m38]))), Ms=mg["Ms"],
                                f_Ms=mg["f_Ms"], PM_min=mg["PM_min"], GM_min=mg["GM_min"], xover=mg["crossovers_hz"],
                                Ms_delay15=mg15["Ms"], GM_delay15=mg15["GM_min"], rho=rho,
                                # Ki on the DIFFERENCE operand conserves I + (Ki/256)*s: a neutral eigenvalue at 1 (to
                                # rounding) that is not an instability of the loop -- reported as "marginal"
                                stable=(True if rho < 1.0 - 1e-9 else ("marginal" if rho <= 1.0 + 1e-9 else False)),
                                modes=[(round(f, 2), round(z, 3)) for f, z in md if 0.2 < f < 45][:6])
    return out


def m_hf_linear(c, base, v282, fam):
    f = np.array([5, 9, 13, 17, 20, 23, 30], float)
    Cc, Cb, C2 = (np.abs(lane_ctf(x, f)) for x in (c, base, v282))
    Pc, Pb, P2 = (np.abs(lane_ctf(x, f, kind="P")) for x in (c, base, v282))
    out = dict(f=f.tolist(), T_per_x=Cc.tolist(), T_per_x_vs_V294=(Cc / np.maximum(Cb, 1e-12)).tolist(),
               P_per_x=Pc.tolist(), P_per_x_V294=Pb.tolist(), P_per_x_V282=P2.tolist())
    st = {}
    for nm, band in (("mode13", (8, 20)), ("mode20", (14, 30)), ("mode20_lo", (14, 30))):
        for v in (5.0, 12.0, 25.0):
            p = fam[nm].at(v)
            (fc, zc), rc = stress_damping(c, p, band)
            (fb_, zb), _ = stress_damping(base, p, band)
            (fo, zo), _ = stress_damping(c.replace(fb_clamp=0), p, band)
            st[(nm, v)] = dict(f=fc, zeta=zc, zeta_V294=zb, zeta_open=zo, rho=rc)
    out["stress_modes"] = st
    return out


def _probe_series(R, o):
    """re-create the mode-A probe exactly as simulate() injected it (same seed, same filter)."""
    rng = np.random.default_rng(o.probe_seed)
    bb, aa = signal.butter(2, [0.3 / 50, 8.0 / 50], btype="band")
    B, NF = R["cmd"].shape
    P = np.zeros((B, NF))
    d = route()
    for j in range(B):
        n = R["lens"][j]
        rec = d["e4_f"][R["a0"][j]:R["a0"][j] + n]
        nz = signal.lfilter(bb, aa, rng.normal(size=NF))
        nz *= o.probe * np.std(rec) / max(np.std(nz[:n]), 1e-9)
        P[j] = nz
    return P


def score(cells, plants=DEFAULT_PLANTS, bands="all", modes=("A", "B"), dists=("full", "lp"), quick=False,
          base=None, chunks=None, probe=0.10, verbose=True):
    """THE SCORING API.  Every designer calls this identically.  Returns a dict:
      meta     cells, diff vs V294, edit class, static problems, runtime
      M_SAFE   rail, sub-rail slope, trim cap (T and % rail), T at zero command, int32 margins, b/b_max, restart pulse
      M_LOOP   per (plant, speed): |L| 1-3 / 3-8 Hz, Ms, PM, GM, crossovers, Ms/GM at delay x1.5, closed-loop modes, stability
               -- on the scored plants AND the stress members
      M_HF     |T/x|, |P/x| 5-30 Hz vs V294 / V282; stress-mode damping vs V294 and open; staircase HF; (sim) delivered
               HF content in 5-9 ... 23-30 Hz, modes A and B, vs V294 in the same batch
      M_TRACK  closed-form alpha/cmd per plant (0.3-8 Hz); mode A literal gain-phase fits and the exogenous-probe transfer;
               amplitude flatness (small/large)
      M_DRIVE  mode B per band (both disturbance models): tracking gain, turn hold, straight delivery, J-style error,
               integrator share, cmd rms, trim/FF, wheel-rate bands, hard-turn 1.6-3 Hz, dwells/min, limit-cycle peak;
               outer-loop Ms / PM from outer_frf; V294 in the SAME batch so every number has its baseline beside it
    quick=True: M_SAFE + M_LOOP + M_HF(linear) + closed-form M_TRACK only (no simulation, ~1-3 s)."""
    t0 = time.time()
    fam = family()
    base = base or Cells.v294()
    v282 = Cells.v282()
    plist = [p for p in plants]
    res = dict(meta=dict(cells=asdict(cells), diff_vs_V294=cells.diff(base), edit_class=cells.edit_class(base),
                         problems=cells.problems(), plants=plist, harness_sha256=_self_sha()))
    res["M_SAFE"] = m_safe(cells)
    res["M_SAFE_V294"] = m_safe(base) if cells.diff(base) else res["M_SAFE"]
    res["M_LOOP"] = m_loop(cells, fam, tuple(plist) + tuple(p for p in STRESS_PLANTS if p not in plist))
    res["M_HF"] = m_hf_linear(cells, base, v282, fam)
    res["M_HF"]["staircase"] = dict(zip(("cand", "V294"), staircase_hf([cells, base])))
    fg = np.array([0.3, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0])
    res["M_TRACK"] = dict(closed_form={})
    for nm in plist:
        for v in (8.0, 12.0, 17.0, 26.9):
            p = fam[nm].at(v)
            a_c, a_b = alpha_per_cmd(cells, p, fg), alpha_per_cmd(base, p, fg)
            res["M_TRACK"]["closed_form"][(nm, v)] = dict(f=fg.tolist(), G=np.abs(a_c).tolist(),
                                                          ph=np.degrees(np.angle(a_c)).tolist(),
                                                          G_V294=np.abs(a_b).tolist())
    res["M_DRIVE"] = dict(outer={})
    for nm in plist:
        for v in (5.0, 8.0, 12.0, 17.0, 26.9):
            p = fam[nm].at(v)
            ff = np.logspace(-2, np.log10(20.0), 800)
            for relay in (True, False):
                Lo = outer_frf(cells, p, v, ff, relay=relay)
                mg = margins(ff, Lo)
                res["M_DRIVE"]["outer"][(nm, v, relay)] = dict(Ms=mg["Ms"], f_Ms=mg["f_Ms"], PM_min=mg["PM_min"],
                                                               GM_min=mg["GM_min"], xover=mg["crossovers_hz"],
                                                               T02=float(abs(Lo[np.argmin(abs(ff - 0.2))] /
                                                                             (1 + Lo[np.argmin(abs(ff - 0.2))]))))
    if quick:
        res["meta"]["runtime_s"] = time.time() - t0
        return res
    # ------------------------------------------------------------------ simulations (candidate + V294 in one batch)
    chunks = chunks or route_chunks()
    if bands != "all":
        dd = route()
        chunks = [ch for ch in chunks if any(lo <= np.mean(dd["v"][ch[0]:ch[1]]) < hi for nm_, lo, hi in BANDS if nm_ in bands)]
    members = [fam[p] for p in plist]
    same = not cells.diff(base)
    cl = [cells] if same else [cells, base]
    nC, nM, nK = len(cl), len(members), len(chunks)
    rows = lambda ci, mi: [ci * nM * nK + mi * nK + k for k in range(nK)]  # noqa: E731
    sims = {}
    if "A" in modes:
        # (1) the LITERAL metric and the HF content: the recorded command, the drive's own disturbance (dist full)
        oA = SimOpts(mode="A", dist="full")
        RA = simulate(cl, members, chunks, oA, record_1k=True)
        # (2) the ACTUATOR branch: the recorded command + an exogenous 0.3-8 Hz probe, dist lp (no HF road disturbance,
        #     which otherwise swamps a 10 % probe: coherence 0.02-0.3 under dist full)
        oP = SimOpts(mode="A", dist="lp", probe=probe)
        RP = simulate(cl, members, chunks, oP)
        PZ = _probe_series(RP, oP)
        sims["A"] = RA
        res["M_TRACK"]["modeA"] = {}
        res["M_HF"]["sim_A"] = {}
        for ci in range(nC):
            for mi, nm in enumerate(plist):
                rr = rows(ci, mi)
                sub = {k: RA[k][rr] for k in ("cmd", "rate18")}
                sub["lens"] = RA["lens"][rr]
                mt, _ = m_track_from_sim(sub)
                subp = {k: RP[k][rr] for k in ("cmd", "rate18")}
                subp["lens"] = RP["lens"][rr]
                mp, _ = m_track_from_sim(subp, PZ[rr])
                mt.update({k: v for k, v in mp.items() if k.startswith("probe")})
                res["M_TRACK"]["modeA"][(cl[ci].name if ci == 0 else "V294", nm)] = mt
                hf = [hf_content(RA["T1k"][j, :RA["lens"][j] * 10]) for j in rr]
                res["M_HF"]["sim_A"][(cl[ci].name if ci == 0 else "V294", nm)] = {
                    k: float(np.sqrt(np.mean([h[k] ** 2 for h in hf]))) for k in hf[0]}
        res["M_TRACK"]["flatness"] = amplitude_flatness(cl, members[:3] if nM > 3 else members)
    if "B" in modes:
        res["M_DRIVE"]["sim"] = {}
        res["M_HF"]["sim_B"] = {}
        for dist in dists:
            oB = SimOpts(mode="B", dist=dist)
            RB = simulate(cl, members, chunks, oB, record_1k=(dist == dists[0]))
            sims["B_" + dist] = RB
            for ci in range(nC):
                for mi, nm in enumerate(plist):
                    rr = rows(ci, mi)
                    dm = drive_metrics(drive_series_sim(RB, rr))
                    dm["limit_cycle"] = limit_cycle_peak(RB, rr)
                    res["M_DRIVE"]["sim"][(dist, cl[ci].name if ci == 0 else "V294", nm)] = dm
                    if RB["T1k"] is not None:
                        hf = [hf_content(RB["T1k"][j, :RB["lens"][j] * 10]) for j in rr]
                        res["M_HF"]["sim_B"][(dist, cl[ci].name if ci == 0 else "V294", nm)] = {
                            k: float(np.sqrt(np.mean([h[k] ** 2 for h in hf]))) for k in hf[0]}
            res["M_DRIVE"]["measured"] = drive_metrics(drive_series_measured(chunks))
    res["meta"]["runtime_s"] = time.time() - t0
    res["meta"]["n_chunks"] = len(chunks)
    res["meta"]["hash"] = score_hash(res)
    if verbose:
        print("score(): %s  %.1f s  hash %s" % (cells.name, res["meta"]["runtime_s"], res["meta"]["hash"][:16]))
    return res


def sweep_drive(cells_list, plants=("nominal", "light_b"), dists=("full", "lp"), chunks=None, include_v294=True):
    """M_DRIVE for MANY candidates in ONE batch per disturbance model (the fast path for a design sweep; score() is the
    full per-candidate report).  Returns {(dist, cells.name, plant): drive_metrics + limit_cycle}.  Give every
    candidate a distinct name (Cells.replace(name=...))."""
    fam = family()
    chunks = chunks or route_chunks()
    cl = list(cells_list) + ([Cells.v294()] if include_v294 else [])
    names = [c.name for c in cl]
    if len(set(names)) != len(names):
        raise ValueError("candidate names must be distinct: %s" % names)
    members = [fam[p] for p in plants]
    nM, nK = len(members), len(chunks)
    out = {}
    for dist in dists:
        R = simulate(cl, members, chunks, SimOpts(mode="B", dist=dist))
        for ci, c in enumerate(cl):
            for mi, p in enumerate(plants):
                rows = [ci * nM * nK + mi * nK + k for k in range(nK)]
                dm = drive_metrics(drive_series_sim(R, rows))
                dm["limit_cycle"] = limit_cycle_peak(R, rows)
                out[(dist, c.name, p)] = dm
    return out


def limit_cycle_peak(R, rows, lo=1.0, hi=5.0):
    """the strongest rate line in lo-hi Hz over the chunks (Welch 10.24 s, prominence dB above the log-log shoulder fit
    of v293r3_read.peak_in's form) -> (f, dB, rms deg/s in +-0.3 Hz).  1-5 Hz: where a loop-generated cycle sits (route
    71-old's 2.34 Hz); below 1 Hz the peak is ordinary steering.  Read it under dist 'lp' (the loop's own motion)."""
    Pw, f = 0, None
    for j in rows:
        n = R["lens"][j]
        if n < 1100:
            continue
        f, p = signal.welch(R["rate18"][j, :n] - np.mean(R["rate18"][j, :n]), fs=100.0, nperseg=1024)
        Pw = Pw + p
    if f is None:
        return dict(f=float("nan"), dB=float("nan"), rms=float("nan"))
    m = (f >= lo) & (f <= hi)
    k = np.flatnonzero(m)[int(np.argmax(Pw[m]))]
    sh = ((f >= lo * 0.5) & (f < lo)) | ((f > hi) & (f <= hi * 1.6))
    cfit = np.polyfit(np.log(f[sh]), np.log(Pw[sh] + 1e-30), 1)
    prom = 10 * np.log10(Pw[k] / np.exp(np.polyval(cfit, np.log(f[k]))))
    nb = (f >= f[k] - 0.3) & (f <= f[k] + 0.3)
    rms = np.sqrt(np.trapezoid(Pw[nb], f[nb]) / max(len(rows), 1))
    return dict(f=float(f[k]), dB=float(prom), rms=float(rms))


def to_jsonable(x):
    """score() dicts have tuple keys; this makes them JSON-safe (keys joined with '|')."""
    if isinstance(x, dict):
        return {("|".join(str(e) for e in k) if isinstance(k, tuple) else str(k)): to_jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [to_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


def _self_sha():
    return hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()


def score_hash(res):
    """a deterministic hash of the numeric content (for the H5 determinism check)."""
    def canon(x):
        if isinstance(x, dict):
            return {str(k): canon(v) for k, v in sorted(x.items(), key=lambda kv: str(kv[0]))}
        if isinstance(x, (list, tuple)):
            return [canon(v) for v in x]
        if isinstance(x, (float, np.floating)):
            return None if not np.isfinite(x) else float("%.12g" % x)
        if isinstance(x, (np.integer,)):
            return int(x)
        return x
    r = {k: v for k, v in res.items() if k != "meta"}
    return hashlib.sha256(json.dumps(canon(r), sort_keys=True).encode()).hexdigest()


def print_score(r, file=None):
    """a compact human-readable print of a score() dict."""
    pr = lambda *a: print(*a, file=file)  # noqa: E731
    m = r["meta"]
    pr("=" * 110)
    pr("SCORE %s   edit class %s   diff vs V294 %s" % (m["cells"]["name"], m["edit_class"], m["diff_vs_V294"]))
    pr("  static problems: %s" % (m["problems"] or "none"))
    s = r["M_SAFE"]
    pr("  M_SAFE rail +%d / %d | sub-rail %.4f T/wire | trim cap %d T (%.1f %% rail) | b %d / b_max %.0f | restart peak %s"
       % (s["rail_pos"], s["rail_neg"], s["subrail_T_per_wire"], s["trim_cap_T"], s["trim_cap_pct_rail"], s["b"], s["b_max"],
          {k: v["peak"] for k, v in s["restart"].items()}))
    pr("         int32 min margin %.2f (%s)" % min((v["margin"], k) for k, v in s["int32"].items()))
    pr("  M_LOOP (plant, v): |L|1-3  |L|3-8  Ms   PMmin  GMmin  Ms(delay x1.5)  stable  modes")
    for (nm, v), x in r["M_LOOP"].items():
        pr("     %-13s %4.1f  %5.2f  %5.2f  %5.2f  %5.0f  %6.1f  %5.2f  %s  %s" % (nm, v, x["L13"], x["L38"], x["Ms"], x["PM_min"],
                                                                        x["GM_min"], x["Ms_delay15"], x["stable"], x["modes"][:3]))
    h = r["M_HF"]
    pr("  M_HF |T/x| 5..30 Hz %s  (x V294 %s)" % (np.round(h["T_per_x"], 3).tolist(), np.round(h["T_per_x_vs_V294"], 2).tolist()))
    pr("       |P/x| 20 Hz: cand %.3f  V294 %.3f  V282 %.3f" % (h["P_per_x"][4], h["P_per_x_V294"][4], h["P_per_x_V282"][4]))
    for k, x in h["stress_modes"].items():
        pr("       %-10s v %4.1f: f %.1f Hz zeta %.3f (V294 %.3f, open %.3f)" % (k[0], k[1], x["f"], x["zeta"], x["zeta_V294"], x["zeta_open"]))
    pr("       staircase HF cand %s | V294 %s" % ({k: round(v, 2) for k, v in h["staircase"]["cand"].items()},
                                                 {k: round(v, 2) for k, v in h["staircase"]["V294"].items()}))
    for key in ("sim_A", "sim_B"):
        for k, x in h.get(key, {}).items():
            pr("       %s %s: %s" % (key, k, {kk: round(vv, 2) for kk, vv in x.items()}))
    t = r["M_TRACK"]
    for k, x in t["closed_form"].items():
        pr("  M_TRACK closed-form %-10s v %4.1f |alpha/cmd| @ %s Hz: %s (V294 %s)" % (k[0], k[1], x["f"], np.round(x["G"], 3).tolist(),
                                                                               np.round(x["G_V294"], 3).tolist()))
    for k, x in t.get("modeA", {}).items():
        pr("  M_TRACK mode A %s: %s" % (k, {kk: {a: round(b, 3) for a, b in vv.items()} for kk, vv in x.items()}))
    if "flatness" in t:
        pr("  M_TRACK flatness |alpha/cmd| 1-3 Hz by amplitude: %s" % {str(k): round(v, 3) for k, v in t["flatness"].items()})
    for k, x in r["M_DRIVE"]["outer"].items():
        pr("  M_DRIVE outer %-8s v %4.1f relay %-5s Ms %.2f@%.2f PM %.0f GM %.1f |T(0.2Hz)| %.3f" % (k[0], k[1], k[2], x["Ms"], x["f_Ms"],
                                                                                            x["PM_min"], x["GM_min"], x["T02"]))
    for k, x in r["M_DRIVE"].get("sim", {}).items():
        pr("  M_DRIVE sim %s:" % (k,))
        for b, y in x.items():
            if b == "limit_cycle":
                pr("       limit-cycle peak %.2f Hz %+.1f dB rms %.2f deg/s" % (y["f"], y["dB"], y["rms"]))
                continue
            pr("       %-6s %4.0fs track %.3f hold %.3f str %.2f J %.3f ish %.2f cmd %4.0f trim/FF %.3f rate %.2f/%.2f/%.2f hard %.2f dwell %.1f"
               % (b, y["sec"], y["track_gain"], y["turn_hold"], y["straight_delivery"], y["J_err"], y["i_share"], y["cmd_rms"],
                  y["trim_ff"], y["r_lo"], y["r_mid"], y["r_hi"], y["hard16"], y["dwell_per_min"]))
    pr("  runtime %.1f s   hash %s" % (m.get("runtime_s", float("nan")), m.get("hash", "-")))
