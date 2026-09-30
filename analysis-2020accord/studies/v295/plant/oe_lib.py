# -*- coding: utf-8 -*-
"""oe_lib.py -- segments and the closed-loop REPLAY used by the output-error fit (p5) and the validation (p6).

A SEGMENT is <= 20 s (>= 4 s) of laterally engaged driving with the wheel NOT pressed (carState.steeringPressed 0) and
|bar| < 600 (the RELAXED hands-off mask; the kit's strict |bar| < 400 fragments this drive to 271 s in runs >= 8 s and
leaves NOTHING at 22+ m/s -- the strict mask is kept as a robustness row, strict=True), assigned to a speed band by its
mean speed.  Within each band, segments alternate FIT / HELD-OUT in time order (parity), so no frame is in both halves.

REPLAY (closed inner loop, no free signal from the drive except the command, the speed and the start state):
  the route's own 0xE4 command -> demand index / sign / fade (v293_flight_read, image cells) -> sp = sgn * LERP(map, idx)
  -> the byte-exact V294 lane (v294_plant.Lane294, == the golden model tick for tick) at 1 kHz -> T -> plant -> x -> lane.
  Start state: th, om from the wire at the segment's first frame; the lane's fb state at the fixed point of that x, its
  output-lag state at the march's T.  One nuisance per segment: c0, the constant torque offset (crown, bank, sensor
  offset) = mean(spring(th_meas) + b*om_meas + Fc*sgn(om_meas) - u_meas) over the segment -- stated wherever a score is.
  🛑 2026-09-30: the first version of both c0 functions had the SIGN INVERTED; every fit made before the fix is VOID.
Scores skip the first 0.5 s (start transient).
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import plib as P  # noqa: E402
import v294_plant as VP  # noqa: E402

SEG_S = 20.0
MIN_S = 4.0
SKIP = 50             # frames skipped at each segment start in every score (0.5 s)
BAR_RELAXED = 600.0


def band_of(v):
    for i, (nm, lo, hi) in enumerate(P.BANDS):
        if lo <= v < hi:
            return i
    return len(P.BANDS) - 1


def mask_relaxed(d):
    return d["eng"] & ~d["pressed"] & (np.abs(d["bar"]) < BAR_RELAXED)


def segments(d, seg_s=SEG_S, min_s=MIN_S, strict=False):
    ho = (d["ho"] if strict else mask_relaxed(d)) & (d["v"] > 0.3)
    segs = []
    for a, b in P.runs(ho, min_len=int(min_s * 100)):
        n = int(seg_s * 100)
        for s0 in range(a, b, n):
            s1 = min(s0 + n, b)
            if s1 - s0 >= int(min_s * 100):
                segs.append((s0, s1))
    out = []
    count = [0] * len(P.BANDS)
    for s0, s1 in segs:
        bi = band_of(float(np.mean(d["v"][s0:s1])))
        out.append(dict(a=s0, b=s1, band=bi, role="fit" if count[bi] % 2 == 0 else "held", vbar=float(np.mean(d["v"][s0:s1]))))
        count[bi] += 1
    return out


class Batch:
    """a padded batch of segments with every array the replay and the scores need."""

    def __init__(self, d, segs, cells):
        self.segs = segs
        self.B = len(segs)
        self.L = max(s["b"] - s["a"] for s in segs)
        L, B = self.L, self.B
        LERP = np.array([int(np.interp(i, cells["map_X"], cells["map_Y"])) for i in range(241)])
        self.cells = cells
        self.sp = np.zeros((B, L), np.int64)
        self.m = np.full((B, L), 254, np.int64)
        self.v = np.zeros((B, L))
        self.om = np.zeros((B, L))
        self.th = np.zeros((B, L))
        self.u = np.zeros((B, L))
        self.mask = np.zeros((B, L), bool)
        self.T0 = np.zeros(B)
        self.tap = []
        for i, s in enumerate(segs):
            a, b = s["a"], s["b"]
            n = b - a
            sl = slice(a, b)
            self.sp[i, :n] = d["sgn"][sl] * LERP[d["idx"][sl]]
            self.m[i, :n] = d["m"][sl]
            self.v[i, :n] = d["v"][sl]
            self.om[i, :n] = d["om"][sl]
            self.th[i, :n] = d["th"][sl]
            self.u[i, :n] = d["u"][sl]
            for arr in (self.sp, self.m, self.v, self.om, self.th, self.u):
                arr[i, n:] = arr[i, n - 1]
            self.mask[i, SKIP:n] = True
            self.T0[i] = d["T1k_live"][10 * a + d["dms"]] if 10 * a + d["dms"] >= 0 else 0.0
            jt = np.flatnonzero((d["j100"] >= a + SKIP) & (d["j100"] < b))
            self.tap.append((d["tick_tap"][jt] - 10 * a, d["T_tap"][jt]))

    def c0(self, member):
        """per-segment constant torque offset (T counts, + LEFT) from the MEASURED state at the member's parameters."""
        a = member.arrays_at(self.v)
        spring = a["k"] * a["sat"] * np.tanh(self.th / a["sat"])
        fr = a["Fc"] * np.sign(self.om) * (np.abs(self.om) > 0.5)
        # plant: J al + b om + spring + Ffric = u + c0   =>   c0 = mean(b om + spring + Ffric - u) (+ J al, ~0 on 20 s)
        # 🛑 FIXED 2026-09-30: the first version returned the NEGATIVE of this (every p5 fit before the fix is VOID)
        res = spring + a["b"] * self.om + fr - self.u
        return np.array([np.mean(res[i][self.mask[i]]) for i in range(self.B)])

    def replay(self, member, lane_kw=None, x_noise=None, c0=None):
        lane = VP.Lane294(self.cells, self.B, **(lane_kw or {}))
        x0 = np.round(-8.0 * self.om[:, 0]).astype(np.int64)          # march convention: the lane sees -x (= +wire)
        lane.init_state(x0, self.T0)
        c0 = self.c0(member) if c0 is None else c0
        out = VP.simulate(member, 10 * self.L, self.v, self.th[:, 0], self.om[:, 0], lane=lane, sp=self.sp, m=self.m,
                          c0=c0, x_noise=x_noise, record_every=1)
        return out, c0

    def scores(self, out, per_segment=False):
        """R^2 and NRMSE fit% of th (segment-demeaned), om, and T at the tap instants, pooled over the batch."""
        th_s = out["th"][:, ::10][:, :self.L]
        om_s = out["om"][:, ::10][:, :self.L]
        res = dict(th_e=[], th_y=[], om_e=[], om_y=[], T_e=[], T_y=[])
        for i in range(self.B):
            mk = self.mask[i]
            dth = th_s[i][mk] - self.th[i][mk]
            dth = dth - np.mean(dth)
            res["th_e"].append(dth)
            res["th_y"].append(self.th[i][mk] - np.mean(self.th[i][mk]))
            res["om_e"].append(om_s[i][mk] - self.om[i][mk])
            res["om_y"].append(self.om[i][mk] - np.mean(self.om[i][mk]))
            tk, Ty = self.tap[i]
            tk = np.clip(tk, 0, out["T"].shape[1] - 1)
            res["T_e"].append(P.quant(out["T"][i][tk]) - Ty)
            res["T_y"].append(Ty - np.mean(Ty))
        sc = {}
        for q in ("th", "om", "T"):
            e = np.concatenate(res[q + "_e"])
            y = np.concatenate(res[q + "_y"])
            sc[q + "_R2"] = float(1 - np.sum(e ** 2) / np.sum(y ** 2))
            sc[q + "_fit"] = float(100 * (1 - np.sqrt(np.sum(e ** 2)) / np.sqrt(np.sum(y ** 2))))
            sc[q + "_rms"] = float(np.sqrt(np.mean(e ** 2)))
        return sc

    def cost(self, out, sth, som):
        th_s = out["th"][:, ::10][:, :self.L]
        om_s = out["om"][:, ::10][:, :self.L]
        c = 0.0
        n = 0
        for i in range(self.B):
            mk = self.mask[i]
            dth = th_s[i][mk] - self.th[i][mk]
            dth = dth - np.mean(dth)
            c += np.sum((om_s[i][mk] - self.om[i][mk]) ** 2) / som ** 2 + np.sum(dth ** 2) / sth ** 2
            n += mk.sum()
        return c / max(n, 1)


def band_member(J, b, k, Fc, Fs, tau_ms=2, name="band"):
    n = len(VP.V_CENTRES)
    return VP.PlantFamilyMember(name, J=np.full(n, J), b=np.full(n, b), k=np.full(n, k), Fc=np.full(n, Fc),
                                Fs=np.full(n, Fs), tau_ms=tau_ms)


# ======================================================================================================================
# MULTIPLE SHOOTING: short windows, each started from the MEASURED state and the march's EXACT lane state
# ======================================================================================================================
WIN_S = 1.0


def windows(segs, win_s=WIN_S, d=None):
    """cut every (parent) segment into non-overlapping windows of win_s.  Each window keeps its PARENT's fit/held role
    (so held-out windows never share a parent with fit windows) but is banded by its OWN mean speed (a parent's mean speed
    mis-bands a hard-turn window at 6 m/s inside a 12 m/s parent -- found while debugging, 2026-09-30)."""
    _V = None if d is None else d["v"]
    out = []
    n = int(round(win_s * 100))
    for pid, s in enumerate(segs):
        for a in range(s["a"], s["b"] - n + 1, n):
            vb = float(np.mean(_V[a:a + n])) if _V is not None else s["vbar"]
            out.append(dict(a=a, b=a + n, band=band_of(vb), role=s["role"], parent=pid, pa=s["a"], pb=s["b"],
                            vbar=vb))
    return out


class WindowBatch(Batch):
    """a batch of equal-length windows.  Differences from Batch: the lane starts in the march's recorded state at the
    window's first tick (d["lane_sfb"], d["lane_o"]); c0 is the model's mean equation residual over the window widened by
    0.5 s each side (inside the parent segment); scores/cost are on om and on dth = th - th[start] (no demeaning),
    with nothing skipped (the start state is exact)."""

    def __init__(self, d, wins, cells):
        segs = [dict(a=w["a"], b=w["b"], band=w["band"], role=w["role"], vbar=w["vbar"]) for w in wins]
        super().__init__(d, segs, cells)
        self.mask[:, :] = False
        self.mask[:, 1:] = True
        self.sfb0 = np.array([d["lane_sfb"][w["a"]] for w in wins], np.int64)
        self.o0 = np.array([d["lane_o"][w["a"]] for w in wins], np.int64)
        self.parent = np.array([w["parent"] for w in wins])
        # the widened span for c0
        self.cw = []
        al = np.gradient(d["om"]) * 100.0
        self.bar = np.array([d["bar"][w["a"]:w["b"]] for w in wins], float)
        self.bar_gain = 0.0                      # g: motor-side input -g*bar (T counts per bar count); 0 = the rigid plant
        for w in wins:
            a0, b0 = max(w["pa"], w["a"] - 50), min(w["pb"], w["b"] + 50)
            self.cw.append(dict(u=d["u"][a0:b0], th=d["th"][a0:b0], om=d["om"][a0:b0], al=al[a0:b0], v=d["v"][a0:b0],
                                bar=d["bar"][a0:b0]))
        self.tap = []
        for w in wins:
            jt = np.flatnonzero((d["j100"] >= w["a"]) & (d["j100"] < w["b"]))
            self.tap.append((d["tick_tap"][jt] - 10 * w["a"], d["T_tap"][jt]))

    def c0(self, member):
        out = np.zeros(self.B)
        for i, cw in enumerate(self.cw):
            a = member.arrays_at(cw["v"])
            spring = a["k"] * a["sat"] * np.tanh(cw["th"] / a["sat"])
            fr = a["Fc"] * np.sign(cw["om"]) * (np.abs(cw["om"]) > 0.5)
            # c0 = mean(J al + b om + spring + Ffric - u + g bar)   (the plant: J al + ... = u + c0 - g bar)
            # 🛑 FIXED 2026-09-30: the first version had the sign inverted (every p5b fit before the fix is VOID)
            out[i] = np.mean(a["J"] * cw["al"] + a["b"] * cw["om"] + spring + fr - cw["u"] + self.bar_gain * cw.get("bar", 0.0))
        return out

    def replay(self, member, lane_kw=None, x_noise=None, c0=None):
        lane = VP.Lane294(self.cells, self.B, **(lane_kw or {}))
        lane.s = self.sfb0.copy()
        lane.o = self.o0.copy()
        c0 = self.c0(member) if c0 is None else c0
        dd = None
        if self.bar_gain:
            dd = -self.bar_gain * np.repeat(self.bar, 10, axis=1)       # the measured bar torque, ZOH to 1 kHz
        out = VP.simulate(member, 10 * self.L, self.v, self.th[:, 0], self.om[:, 0], lane=lane, sp=self.sp, m=self.m,
                          c0=c0, d=dd, x_noise=x_noise, record_every=1)
        return out, c0

    def _series(self, out):
        th_s = out["th"][:, 9::10][:, :self.L]          # the state at the END of each frame's 10 ticks = next frame
        om_s = out["om"][:, 9::10][:, :self.L]
        # compare sim state after frame j's ticks with the measured state at frame j+1
        return th_s[:, :-1], om_s[:, :-1], self.th[:, 1:], self.om[:, 1:]

    def scores(self, out, per_segment=False):
        ths, oms, thm, omm = self._series(out)
        dths, dthm = ths - self.th[:, :1], thm - self.th[:, :1]
        sc = {}
        for q, e, y in (("dth", dths - dthm, dthm), ("om", oms - omm, omm)):
            yc = y - y.mean(axis=1, keepdims=True)
            sc[q + "_R2"] = float(1 - np.sum(e ** 2) / np.sum(yc ** 2))
            sc[q + "_fit"] = float(100 * (1 - np.sqrt(np.sum(e ** 2)) / np.sqrt(np.sum(yc ** 2))))
            sc[q + "_rms"] = float(np.sqrt(np.mean(e ** 2)))
            # by horizon: 0-0.25 s, 0.25-0.5, 0.5-1
            L = e.shape[1]
            for nm, lo, hi in (("h025", 0, L // 4), ("h050", L // 4, L // 2), ("h100", L // 2, L)):
                sc["%s_%s_rms" % (q, nm)] = float(np.sqrt(np.mean(e[:, lo:hi] ** 2)))
        # om R2 against a NAIVE predictor (om held at its start value): skill of the plant over persistence
        naive = omm - self.om[:, :1]
        sc["om_skill_vs_hold"] = float(1 - np.sum((oms - omm) ** 2) / np.sum(naive ** 2))
        # tap
        Te, Ty = [], []
        for i in range(self.B):
            tk, T_ = self.tap[i]
            tk = np.clip(tk, 0, out["T"].shape[1] - 1)
            Te.append(P.quant(out["T"][i][tk]) - T_)
            Ty.append(T_ - T_.mean() if len(T_) else T_)
        Te, Ty = np.concatenate(Te), np.concatenate(Ty)
        sc["T_R2"] = float(1 - np.sum(Te ** 2) / np.sum(Ty ** 2))
        sc["T_rms"] = float(np.sqrt(np.mean(Te ** 2)))
        return sc

    def cost(self, out, sth, som):
        ths, oms, thm, omm = self._series(out)
        dths, dthm = ths - self.th[:, :1], thm - self.th[:, :1]
        return float(np.mean((oms - omm) ** 2) / som ** 2 + np.mean((dths - dthm) ** 2) / sth ** 2)
