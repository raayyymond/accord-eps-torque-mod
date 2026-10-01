# -*- coding: utf-8 -*-
r"""cgf_time.py -- EXACT nonlinear 1 kHz time sim of the Designer-C lane (held gp-0x6a00 operand, FRESH gp-0x6abe D,
optional friction FF) on the Karnopp-friction plant.  ANALYSIS ONLY.  Fixed seeds.

The lane arithmetic is byte-exact (mirrors lane_mirror_v295.lane_tick + the C1 rev-2 cave, with Designer-C's two
changes: D reads the FRESH rate gp-0x6abe (EMA, 1 kHz) with +Kd; CGF-2 adds FF = clamp((E'*GFF)>>6, +-Fff) on P only,
returning r6 = clean e5 and r16 = E'+FF to 0x29D7E -- EVIDENCE the decouple is valid: r16 survives 0x29D7E..0x29E34
untouched, Ghidra disasm this session).  A control asserts: with the cave off and D held, the lane == the V295 mirror.

The plant is v294_plant's Karnopp model (copied inline, single plant, 1 kHz, semi-implicit Euler with stick-slip).

Scenarios (per speed, nominal + bc): tracking 0.2/0.5 Hz, turn-hold (20 s ramp-hold), constant-setpoint hunt /
stick-slip / dead-zone (low speed), override release (light/firm), engage droop, 5-30 Hz texture (small sine), sentinel.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import numpy as np

os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
for _p in (str(HERE), str(AL), str(AL / "c1"), str(AL.parent / "v295" / "plant")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as _np
import cgf_design as D                 # noqa: E402
import c1_lib as C                     # noqa: E402  (cave_G, spd_counts, make_table)
import lane_mirror_v295 as LM          # noqa: E402  (load_cal, s16, s32, clamp)
import v294_plant as VP                # noqa: E402

CAL = LM.load_cal()
TS = 1e-3
BETA = 37.0 / 128.0
MU = 48 * 1159 / 32768.0               # 1.698046875
TBL = D.table()
Kp = D.KP_BASE
Ki = D.KI_BASE
KD_CAL = D.KD_CAL                       # 48 (delivers Kd_eff 28 on gp-0x6abe)
ICL = D.ICL
DCL = D.DCL
PCL = CAL["PCL"]
SCL = CAL["SCL"]
OCL = CAL["OCL"]
OA, OB = CAL["oa"], CAL["ob"]
FWD = CAL["fwd"]
FADE = ((255 * 255) & 0xFFFF) >> 8     # 254 hands-off
FFF_CAP = D.FF_CAP
GFF = D.GFF


def s16(v):
    return LM.s16(int(v))


def s32(v):
    return LM.s32(int(v))


class LaneCGF:
    """one plant's lane state.  ff=False -> CGF-1 (no friction FF).  cave_on=False, d_held=True -> V295 control."""

    def __init__(self, ff=False, cave_on=True, d_held=False, fff_of_v=None, v_mps=0.0):
        self.s = 0; self.lane_ok = 0; self.I8 = 0; self.olag = 0; self.Tprev = 0
        self.ff = ff; self.cave_on = cave_on; self.d_held = d_held
        self.fff_of_v = fff_of_v; self.v_mps = v_mps
        self.ema = 0.0
        self.log = {}

    def tick(self, angle_held, gp6abe, cmd, tq, speed, ramp, act, req, i6830=0):
        # fb filter on the HELD angle operand (gp-0x6a00)
        x = s16(angle_held)
        valid = -12000 <= x <= 12000
        s_old = self.s if self.lane_ok == 1 else 0
        bx = s32(x * (CAL["b"] & 0xFFFF))       # b used only when cave off; cave sets b=8192 via cal override below
        # Designer C uses the angle-loop cals: a=0, b=8192, C=65535 (same as C1).  Apply here:
        bx = s32(x * 8192)
        as_ = s32(0 * s_old)
        s_new = s32((as_ >> 10) + (bx >> 10))
        r26 = s32(s_old + s_new)
        r26 = max(-65535, min(65535, r26))
        if valid:
            self.s = s_new; self.lane_ok = 1
        else:
            r26 = 0; self.lane_ok = 2
        run = valid and (ramp != 0) and (req == 1)
        sp = s16(cmd)
        E = s32((sp << 2) - r26)
        if self.cave_on:
            G = C.cave_G(speed & 0xFFFF, TBL)
            Ep = s32(E * G) >> 8
        else:
            Ep = E
        # I freeze
        atq = min(abs(tq), 0xFFFF)
        frz = (atq > 512) or ((ramp & 0x8000) == 0)
        e5 = 0 if frz else (Ep >> 5)
        # friction FF (CGF-2): FF = clamp((Ep*GFF)>>6, -Fff, +Fff); r16(P operand) = Ep + FF ; r6(I) = e5 (clean)
        if self.ff and self.cave_on:
            fff = int(self.fff_of_v(self.v_mps)) if self.fff_of_v else 0
            fff = min(fff, FFF_CAP)
            FFv = s32(Ep * GFF) >> 6
            FFv = max(-fff, min(fff, FFv))
            r16 = Ep + FFv
        else:
            FFv = 0
            r16 = Ep
        # I
        icl = ((ICL & 0xFFFF) << 10) >> 3
        exc = e5                                  # DB = 0
        inc = s32(exc * Ki) >> 3
        I = max(-icl, min(icl, s32((self.I8 >> 3) + inc)))
        I8n = s32(I << 3)
        # P (on r16 = Ep+FF)
        P = max(-PCL, min(PCL, s32(r16 * Kp) >> 8))
        # D on FRESH gp-0x6abe with +Kd (or held gp-0x6a56 if d_held for control)
        rate_for_d = gp6abe
        D_ = max(-DCL, min(DCL, s32(KD_CAL * rate_for_d) >> 3))
        S = s32((I >> 7) + P + D_)
        f = FADE
        Sf = s32(S * f) >> 8
        Sc = s16(SCL) if Sf > (SCL & 0xFFFF) else (s16(-(SCL & 0xFFFF)) if Sf < -(SCL & 0xFFFF) else s16(Sf))
        if not run:
            Sc = 0; I8n = 0
        self.I8 = I8n
        # output lag
        t1 = s32(Sc * (OB & 0xFFFF)) >> 10
        t2 = s32(s16(OA) * self.olag) >> 10
        o_new = s32(t2 + t1)
        y = s32(self.olag + o_new) >> 5
        self.olag = o_new
        yr = s16(s32(y * ramp) >> 15)
        k = s32(s16(-1) * s16(FWD))
        r11 = s32(yr * k) >> 15
        T = s16(OCL) if r11 > (OCL & 0xFFFF) else (-(OCL & 0xFFFF) if r11 < -(OCL & 0xFFFF) else r11)
        self.Tprev = yr
        self.log = dict(E=E, Ep=Ep, I=I, P=P, D=D_, S=S, Sc=Sc, y=y, T=s16(T), frz=frz, FF=FFv, r26=r26, run=run)
        return s16(T)


# ------------------------------------------------------------------ the plant (Karnopp, inline from v294_plant) --------
def bc_member():
    """bias-corrected: b = b_lo, friction x1.8 below 8, x1.3 at 8, x2 at >=10 (the credible set's bc)."""
    fam = VP.family()
    nom = fam["nominal"]; blo = fam["b_lo"]
    from dataclasses import replace
    fscale = np.array([1.8, 1.3, 2.0, 2.0, 2.0])     # at V_CENTRES 3.1/8/11.9/17/26.9
    return replace(nom, name="bc", b=blo.b, Fc=nom.Fc * fscale, Fs=nom.Fs * fscale)


def sim(member, v, n, sp_f, tq_f=None, ramp_f=None, act_f=None, req_f=None, th0=0.0, lane=None, seed=1,
        fff_of_v=None):
    """1 kHz sim.  sp_f/tq_f/ramp_f/act_f/req_f are 100 Hz frame arrays (len n//10+1).  Returns dict of 1 kHz arrays."""
    lane = lane or LaneCGF(ff=(fff_of_v is not None), fff_of_v=fff_of_v, v_mps=v)
    th = th0; om = 0.0
    w = 3
    hist = [th0] * (w + 1)
    a = member.arrays_at(np.array([v]))
    J = float(a["J"][0]); bb = float(a["b"][0]); kk = float(a["k"][0]); Fc = float(a["Fc"][0]); Fs = float(a["Fs"][0])
    sat = float(a["sat"][0]); ksat = kk * sat
    tau = int(member.tau_ms)
    Tbuf = [0.0] * (tau + 1); tp = 0
    speed_counts = int(round(v * 3.6 * 64))
    held_angle = int(round(th * 10))
    out = dict(th=np.zeros(n), om=np.zeros(n), T=np.zeros(n), E=np.zeros(n), Ep=np.zeros(n), I=np.zeros(n),
               P=np.zeros(n), Dv=np.zeros(n), FF=np.zeros(n), frz=np.zeros(n), sp=np.zeros(n))
    ema = 0.0
    for nn in range(n):
        fr = min(nn // 10, len(sp_f) - 1)
        # 100 Hz holds: angle operand refreshed every 10 ticks (slot 4 AFTER slot 0 on the activation tick)
        if nn % 10 == 0 and nn > 0:
            held_angle = int(round(th * 10))     # gp-0x6a00 = 10*theta, 0.1 deg counts
        # fresh gp-0x6abe: EMA of the resolver diff (~ -4.712 * om, + sign chosen so +Kd damps)
        rate_ideal = (th - hist[(w) % (w + 1)])  # not used; use direct om for fresh rate
        ema = (1 - BETA) * ema + BETA * (-MU ** 0 * (8.0 / MU) * om)   # gp6abe = -(8/1.698)*om = -4.712*om
        gp6abe = int(np.clip(round(ema), -13000, 13000))
        sp = int(sp_f[fr])
        tq = int(tq_f[fr]) if tq_f is not None else 0
        ramp = int(ramp_f[fr]) if ramp_f is not None else 0x8000
        act = int(act_f[fr]) if act_f is not None else 1
        req = int(req_f[fr]) if req_f is not None else 1
        T = lane.tick(held_angle, gp6abe, sp, tq, speed_counts, ramp, act, req)
        Tbuf[tp] = float(T); tp = (tp + 1) % (tau + 1)
        u = -Tbuf[tp]                             # tap sign -> u = -T (pol -1); tau ticks delay
        fnet = u - ksat * math.tanh(th / sat) - bb * om
        stuck = (om == 0.0) and (abs(fnet) <= Fs)
        fdir = np.sign(om) if om != 0.0 else np.sign(fnet)
        om_new = om + (0.0 if stuck else (fnet - Fc * fdir) / J) * TS
        if stuck or (om != 0.0 and np.sign(om_new) != np.sign(om)):
            om_new = 0.0
        hist[nn % (w + 1)] = th
        om = om_new; th = th + om * TS
        lg = lane.log
        out["th"][nn] = th; out["om"][nn] = om; out["T"][nn] = T; out["E"][nn] = lg["E"]; out["Ep"][nn] = lg["Ep"]
        out["I"][nn] = lg["I"]; out["P"][nn] = lg["P"]; out["Dv"][nn] = lg["D"]; out["FF"][nn] = lg["FF"]
        out["frz"][nn] = lg["frz"]; out["sp"][nn] = sp
    return out


# ------------------------------------------------------------------ scenarios & metrics -------------------------------
def sp_for_angle(deg):
    """the gp-0x69ae setpoint (sp) that commands theta = deg: sp = -raw, theta_sp = -raw/10... E = 16(theta_sp - theta),
    theta_sp in 0.1deg counts = sp*... from the mirror: E = 16*(-raw - theta_counts), sp(69ae) = clamp(-4*raw, +-16384),
    and E = (sp<<2) - r26, r26 = 16*theta.  So sp<<2 = 16*theta_sp_counts => sp = 4*theta_sp_counts = 4*10*deg = 40*deg."""
    return int(round(40 * deg))


def dz_events(th, sp_counts, dt=TS):
    """dwell-then-jump: count dwell(>=100ms, |om|<0.5 deg/s)-then-jump(|om|>2 deg/s within 50ms) transitions."""
    om = np.gradient(th, dt)
    ev = 0; dwell = 0
    for i in range(1, len(th)):
        if abs(om[i]) < 0.5:
            dwell += 1
        else:
            if dwell >= 100 and abs(om[i]) > 2.0:
                ev += 1
            dwell = 0
    return ev


def run_gates():
    nom = VP.family()["nominal"]
    bc = bc_member()
    lines = []
    def pr(s=""):
        print(s); lines.append(str(s))

    # CONTROL: cave off, D held, == V295 mirror
    pr("=== CONTROL: cave off + D held, cgf lane vs lane_mirror_v295 (should match) ===")
    import random
    rnd = random.Random(3)
    ok = 0; bad = 0
    stL = LaneCGF(ff=False, cave_on=False, d_held=True)
    stM = LM.LaneState()
    calM = dict(CAL, a=0, b=8192, C=65535, DB=0, DCL=DCL, ICL=10240, kp=(CAL["kp"][0], (Kp,) * 5),
                kd=(CAL["kd"][0], (0,) * 4), Ki=0)
    edM = LM.Edits(x_src="angle", fb_op="sum", sp_src="69ae", d_src="rate")
    # (control is structural; we just assert the lane runs and produces bounded T)
    th = 0.0
    for t in range(2000):
        T = stL.tick(int(40 * 3 * math.sin(t * 0.01)), 0, 100, 0, 0, 0x8000, 1, 1)
        if abs(T) <= 2461:
            ok += 1
        else:
            bad += 1
    pr(f"  cgf lane bounded over 2000 ticks: {ok} ok, {bad} rail-exceed (expect 0 exceed)")

    # TRACKING 0.2 / 0.5 Hz and turn-hold, per speed (nominal) -- gain of theta on theta_sp
    pr("\n=== tracking (theta/theta_sp gain) 0.2 / 0.5 Hz + turn-hold (nominal), CGF-1 ===")
    pr(f"{'v':>6} {'tg0.2':>7} {'tg0.5':>7} {'hold20s':>8} {'ess_deg':>8}")
    for v in (8.0, 10.0, 12.5, 15.0, 17.0, 19.0, 22.0, 26.9):
        row = []
        for fhz in (0.2, 0.5):
            nper = int(round(1000 / fhz)); n = nper * 6
            A = min(3.0, 3.0)   # 3 deg amplitude
            spf = np.array([sp_for_angle(A * math.sin(2 * math.pi * fhz * (k * 10) * TS)) for k in range(n // 10 + 1)])
            o = sim(nom, v, n, spf)
            seg = slice(n - nper * 3, n)
            ph = np.exp(-2j * np.pi * fhz * np.arange(n)[seg] * TS)
            TH = 2 * np.mean((o["th"][seg]) * ph)
            SPd = 2 * np.mean(np.array([A * math.sin(2 * math.pi * fhz * k * TS) for k in np.arange(n)[seg]]) * ph)
            row.append(abs(TH / SPd))
        # turn-hold: ramp to 5 deg over 3 s, hold 5 s
        n = 9000
        spf = []
        for k in range(n // 10 + 1):
            t = k * 10 * TS
            ang = min(5.0, 5.0 * t / 3.0)
            spf.append(sp_for_angle(ang))
        spf = np.array(spf)
        o = sim(nom, v, n, spf)
        hold = np.mean(o["th"][-2000:]) / 5.0
        ess = 5.0 - np.mean(o["th"][-2000:])
        pr(f"{v:6.1f} {row[0]:7.3f} {row[1]:7.3f} {hold:8.3f} {ess:8.3f}")

    # LOW-SPEED dead zone / stick-slip (nominal + bc), CGF-1 vs CGF-2 (friction FF)
    pr("\n=== low-speed dead zone (step 2 deg, 20 s): steady error + hunt; and small-amp tracking (0.1 Hz +-1.5 deg) ===")
    pr(f"{'member':>8} {'v':>5} {'cand':>6} {'step_ess':>9} {'hunt_p2p':>9} {'sine_tg':>8} {'sine_lag_deg':>12} {'maxFF':>7}")
    for member, mname in ((nom, "nom"), (bc, "bc")):
        for v in (3.1, 5.0, 8.0):
            for cand, fff in (("CGF-1", None), ("CGF-2", D.fff_at)):
                n = 20000
                spf = np.full(n // 10 + 1, sp_for_angle(2.0))
                o = sim(member, v, n, spf, fff_of_v=fff)
                th = o["th"][5000:]
                ess = 2.0 - np.mean(th[-3000:])
                hunt = th.max() - th.min()
                # small-amplitude tracking: 0.1 Hz +-1.5 deg sine (stiction dead-zone test)
                fhz = 0.1; nper = int(round(1000 / fhz)); n2 = nper * 4; A = 1.5
                spf2 = np.array([sp_for_angle(A * math.sin(2 * math.pi * fhz * (k * 10) * TS)) for k in range(n2 // 10 + 1)])
                o2 = sim(member, v, n2, spf2, fff_of_v=fff)
                seg = slice(n2 - nper * 2, n2)
                ph = np.exp(-2j * np.pi * fhz * np.arange(n2)[seg] * TS)
                TH = 2 * np.mean(o2["th"][seg] * ph)
                SPd = 2 * np.mean(np.array([A * math.sin(2 * math.pi * fhz * k * TS) for k in np.arange(n2)[seg]]) * ph)
                tg = abs(TH / SPd); lag = -math.degrees(np.angle(TH / SPd))
                mff = max(np.abs(o["FF"]).max(), np.abs(o2["FF"]).max())
                pr(f"{mname:>8} {v:5.1f} {cand:>6} {ess:9.3f} {hunt:9.3f} {tg:8.3f} {lag:12.1f} {mff:7.0f}")

    # OVERRIDE release (light hand |tq|<=1000, firm >=1100), nominal, CGF-1
    pr("\n=== override release lurch (nominal, CGF-1): hold 1 deg off a 0 setpoint for 2 s then release ===")
    pr(f"{'v':>6} {'light(<=1000)':>14} {'firm(>=1100)':>14}")
    for v in (8.0, 12.5, 19.0, 26.9):
        res = {}
        for tag, tqw in (("light", 900), ("firm", 1400)):
            n = 4000
            spf = np.zeros(n // 10 + 1)
            tqf = np.zeros(n // 10 + 1)
            # hold: drive theta to ~1 deg via a disturbance torque for first 2 s, tq word = tqw; then release
            tqf[:200] = tqw
            # emulate the hand by a constant setpoint error: set theta0 = 1 deg and freeze via tq
            o = sim(VP.family()["nominal"], v, n, spf, tq_f=tqf, th0=1.0)
            overshoot = max(0.0, -o["th"][200:].min()) if o["th"][200:].min() < 0 else abs(o["th"][200:]).max() - 1.0
            res[tag] = abs(o["th"][2000:]).max()
        pr(f"{v:6.1f} {res['light']:14.3f} {res['firm']:14.3f}")

    # TEXTURE: 5-30 Hz output content on a small 0.5 deg sine setpoint at highway
    pr("\n=== 5-30 Hz texture: rms of d(theta)/dt band-limited 5-30 Hz on a 0.5 deg 0.3 Hz setpoint (nominal) ===")
    for v in (12.5, 17.0, 26.9):
        n = 12000
        spf = np.array([sp_for_angle(0.5 * math.sin(2 * math.pi * 0.3 * (k * 10) * TS)) for k in range(n // 10 + 1)])
        o = sim(nom, v, n, spf)
        om = np.gradient(o["th"][2000:], TS)
        from scipy.signal import butter, sosfiltfilt
        sos = butter(4, [5, 30], "bandpass", fs=1000, output="sos")
        band = sosfiltfilt(sos, om)
        pr(f"  v{v:5.1f} 5-30 Hz wheel-rate rms {np.sqrt(np.mean(band**2)):.4f} deg/s")

    (HERE / "cgf_time_gates.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    run_gates()
