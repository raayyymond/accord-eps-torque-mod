# -*- coding: utf-8 -*-
r"""angle_loop_controls.py -- SYNTHETIC POSITIVE / NEGATIVE CONTROLS for angle_loop_drive_read.py.

    python rlog-tools/studies/angle_loop/angle_loop_controls.py [all | verdict | stops | goal | friction | real]
                                                               [--members nominal,bc,b_lo*J_hi,F_hi]

ANALYSIS ONLY.  Builds no image, flashes nothing, sends nothing.  Writes only under _scratch/angle_loop/drive-read/.

WHY.  Every verdict the reader can print must have a DEMONSTRATED discrimination: a control that is the thing (and
must read LIVE / fire) and a control that is not (and must not), run through the SAME reader code path as a flight.
An instrument that passes everything measures nothing (the V293 flight-read's rule).

ENGINE.  panel2/score_time.py imported UNCHANGED -- its Karnopp plant on the r71b-identified family (members nominal,
bc, F_hi, b_lo*J_hi), 2 ms transport, the 100 Hz slot-4 hold of gp-0x6a00, the 0xE4 100 Hz cadence, the 1 kHz
gp-0x6abe EMA, and CandLane = the H1-validated lane (every candidate's cave hex executed against it).  The lane is
swapped per control:
   P0   C3B-P  = C3-rev2-P = the V296 design byte-for-byte (rev2 §1; score cave; the flight cave's op-skip is on the
               invalid-rate path only, never exercised by a valid wire)
   N1   V295 as flown: lane_mirror_v295.lane_tick (byte-exact, V295 image cells) fed the SAME fork angle setpoints
        (the "wrong image" / revert-without-fork-change case)
   N2   SKIP   the in-place set with the cave skipped (G = 256 flat, no A3 policy)
   N3   C3-P56 the refuted C3 (Ki 56, G-P48 table) -- the Ki-40 clause must reject it
   N4   kd34   C3-rev2-P with P2's Kd 34 -- the re-sized-D clause must reject it
   I1   kdneg  C3-rev2-P with Kd -48 (the fresh D's sign inverted = pol +1 on the D) -- R1 must fire
   I2   thneg  C3-rev2-P with the angle operand negated (positive angle feedback) -- R1 must fire
Stop-band detectors get their own controls (planted 5-30 Hz lines, a deliberately ringing lane, real V282/V294 drives
as false-alarm controls).  The wire is synthesised with the units/signs of the real buses (see the reader's docstring):
f14a = -gp-0x6a00, raw = -gp-0x69ae/4, 0x18F rate raw = -gp-0x6a56, bar = -gp-0x4f60, tap = T quantised to 8 at 50 Hz.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import angle_loop_drive_read as DR  # noqa: E402

SCR = DR.SCR / "controls"
SCR.mkdir(parents=True, exist_ok=True)
ST = DR.load_score_time()
NS = ST.NS
SPEEDS6 = (6.5, 9.0, 11.25, 13.75, 18.5, 25.0)        # one per BANDS_CP band
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(str(s))


# =====================================================================================================================
# LANE VARIANTS that need more than a Cand
# =====================================================================================================================
class InvAngleLane(ST.CandLane):
    """CandLane with the angle operand negated (x := -gp-0x6a00): positive angle feedback."""

    def tick(self, a6a00, x69, xheld, abe, cmd, tq, ramp, act, req, pol=-1):
        return super().tick(-np.asarray(a6a00), -np.asarray(x69), xheld, abe, cmd, tq, ramp, act, req, pol)


class V295Lane:
    """lane_mirror_v295.lane_tick per column (byte-exact V295, V295 image cells), CandLane's tick signature."""

    def __init__(self, cands, vw):
        import lane_mirror_v295 as LM
        self.LM = LM
        self.cal = LM.load_cal()
        self.ed = LM.Edits()
        self.B = len(cands)
        self.vw = np.asarray(vw, np.int64)
        self.st = [LM.LaneState() for _ in range(self.B)]
        self.wraps = 0
        self.n_frz = np.zeros(self.B, np.int64)
        self.n_run = np.ones(self.B, np.int64)
        self.log = {"I": np.zeros(self.B, np.int64)}

    def tick(self, a6a00, x69, xheld, abe, cmd, tq, ramp, act, req, pol=-1):
        ramp = np.broadcast_to(np.asarray(ramp, np.int64), (self.B,))
        tq = np.broadcast_to(np.asarray(tq, np.int64), (self.B,))
        out = np.zeros(self.B, np.int16)
        for j in range(self.B):
            out[j] = self.LM.lane_tick(self.st[j], self.cal, self.ed, rate=int(xheld[j]), angle=int(a6a00[j]),
                                       cmd69ae=int(cmd[j]), tq=int(tq[j]), speed=int(self.vw[j]), ramp=int(ramp[j]),
                                       act6806=int(act), req6805=int(req), pol=-1)
        return out


def cands():
    C = DR.replay_cands(ST)
    C["kdneg"] = ST.Cand("kdneg", "X", C["C3B-P"].rows, "fresh", -48, ki=40, icl=8192, arb=ST.ARB_A3, sgn_thr=300,
                         note="D sign inverted (pol +1 on the fresh D)")
    C["thneg"] = ST.Cand("thneg", "X", C["C3B-P"].rows, "fresh", 48, ki=40, icl=8192, arb=ST.ARB_A3, sgn_thr=300,
                         note="angle operand negated")
    C["nofrz"] = ST.Cand("nofrz", "X", C["C3B-P"].rows, "fresh", 48, ki=40, icl=8192, arb=None, sgn_thr=0,
                         thr=1 << 20, note="no freeze, no bound (the N1 negative)")
    for ki in (160, 400):
        C["ki%d" % ki] = ST.Cand("ki%d" % ki, "X", C["C3B-P"].rows, "fresh", 48, ki=ki, icl=8192, arb=None,
                                 note="Ki x%d (ring control)" % (ki // 40))
    C["g4"] = ST.Cand("g4", "X", tuple((x, min(4 * g, 0xFFFF), 4 * s) for x, g, s in C["C3B-P"].rows), "fresh", 48,
                      ki=40, icl=8192, arb=ST.ARB_A3, sgn_thr=300, note="G x4 (ring control)")
    C["V295"] = ST.Cand("V295", "V295", C["C3B-P"].rows, note="V295 lane (lane_mirror_v295)")
    C["z_A2"] = ST.Cand("z_A2", "X", C["C3B-P"].rows, "fresh", 48, ki=40, icl=8192, arb=ST.ARB_A3, sgn_thr=300,
                        note="raw 0 after the drop, A2 present")
    C["z_noA2"] = ST.Cand("z_noA2", "X", C["C3B-P"].rows, "fresh", 48, ki=40, icl=8192, arb=ST.ARB_A3, sgn_thr=300,
                          note="raw 0 after the drop, A2 absent (R7 positive)")
    C["noA2"] = ST.Cand("noA2", "X", C["C3B-P"].rows, "fresh", 48, ki=40, icl=8192, arb=ST.ARB_A3, sgn_thr=300,
                        note="C3-rev2-P with the stock run guard (A2 absent)")
    return C


class NoA2Lane(ST.CandLane):
    """C3-rev2-P WITHOUT the A2/B2 guard edit: Honda's stock run condition (ramp != 0 OR request), so the PID keeps
    running through the 2.048 s ramp-down after a request drop -- the A2 negative control."""

    def tick(self, a6a00, x69, xheld, abe, cmd, tq, ramp, act, req, pol=-1):
        r = np.asarray(ramp)
        req2 = np.where(r != 0, 1, req) if r.ndim else (1 if int(r) != 0 else req)
        return super().tick(a6a00, x69, xheld, abe, cmd, tq, ramp, act, req2, pol)


class ZeroCmdLane(ST.CandLane):
    """C3-rev2-P where the fork sends raw = 0 from the request drop on (SPEC C4: 'not allowed' -> raw 0); with
    stock=True the stock run guard is used as well (A2 absent) -> the lane servos toward 0 deg through the 2 s ramp:
    the R7 POSITIVE control.  stock=False (A2 present) is its negative."""
    stock = False

    def tick(self, a6a00, x69, xheld, abe, cmd, tq, ramp, act, req, pol=-1):
        r = np.asarray(ramp)
        if int(np.max(req)) == 0:
            cmd = np.zeros_like(np.asarray(cmd))
            if self.stock:
                req = np.where(r != 0, 1, 0)
        return super().tick(a6a00, x69, xheld, abe, cmd, tq, ramp, act, req, pol)


class ZeroCmdNoA2Lane(ZeroCmdLane):
    stock = True


LANE_KIND = {"thneg": InvAngleLane, "V295": V295Lane, "noA2": NoA2Lane, "z_A2": ZeroCmdLane,
             "z_noA2": ZeroCmdNoA2Lane}


# =====================================================================================================================
# THE SYNTHETIC DRIVE: ST.run (unchanged) per column, then the wire, then concatenated into one "drive"
# =====================================================================================================================
def path_ref(v, B, dur, seed):
    """a deterministic fork-like setpoint path: slow curves + corrections, amplitude scaled by the harness's own
    A_turn(v) (30 deg at 8 m/s ... 3 deg at 26 m/s), 0.02-0.8 Hz, smooth (the fork rate-limits)."""
    from scipy import signal
    rng = np.random.default_rng(seed)
    n = int(dur * 100) + 2
    slow = signal.sosfiltfilt(signal.butter(2, [0.02, 0.15], "bandpass", fs=100, output="sos"),
                              rng.normal(size=(n + 2000, B)), axis=0)[1000:1000 + n]
    corr = signal.sosfiltfilt(signal.butter(2, [0.15, 0.8], "bandpass", fs=100, output="sos"),
                              rng.normal(size=(n + 2000, B)), axis=0)[1000:1000 + n]
    A = np.array([ST.A_turn(x) for x in np.broadcast_to(v, (B,))])
    p = 0.55 * A * slow / slow.std(0) + 0.08 * A * corr / corr.std(0)
    ramp = np.clip(np.arange(n) / 150.0, 0, 1)[:, None]
    return p * ramp


def scn_path(cols, dur=32.0, seed=3, road=15.0, uext=None):
    B = len(cols)
    v = np.array([c["v"] for c in cols])
    P = path_ref(v, B, dur, seed)

    def ref(t):
        return P[min(int(t * 100), len(P) - 1)]
    # engaged from t = 0 THROUGH the ramp-in (mode 'relatch', +33/tick), as on the car -- not born at ramp 0x8000
    return ST.Scn(dur=dur, ref=ref, road=road, uext=uext, mode0="off", events=((0.0, "engage"),)), P


def run_cols(cols, scn, kind=None):
    """ST.run with the lane class swapped for this batch (restored after)."""
    orig = ST.CandLane
    try:
        if kind is not None:
            ST.CandLane = kind
        with contextlib.redirect_stdout(io.StringIO()):
            r = ST.run(cols, scn)
    finally:
        ST.CandLane = orig
    return r


def wire_of(r, j, v, scn=None, t_dis=None, seed=0, bar_noise=15.0):
    """the 100 Hz wire + 50 Hz tap of column j, with the real buses' units/signs."""
    rng = np.random.default_rng(1000 + seed + j)
    th1k, om1k, T1k, sp1k = r["th"][:, j].astype(float), r["om"][:, j].astype(float), r["T"][:, j].astype(int), \
        r["sp"][:, j].astype(int)
    n = len(th1k)
    k = np.arange(len(r["wire"]))
    tick = np.minimum(10 * k + 4, n - 1)
    gp6a00 = r["wire"][:, j].astype(float)
    ang = gp6a00 / 10.0
    raw = -(sp1k[tick] / 4.0)
    raw = np.where(np.abs(sp1k[tick]) >= 0x7FFF, 0, raw)
    # gp-0x6a56 = clamp(-((abe*48*1159)>>15)), abe = 1 kHz EMA (37/128) of s16(round(-4.712 * motor rate + noise))
    om_m = om1k / ST.FRAME.kappa(th1k)
    g = np.round(NS.ABE_PER * om_m + rng.normal(0, NS.N4F50, n)).astype(np.int64)
    st = np.zeros(n, np.int64)
    s = 0
    for i in range(n):
        s = s + (((int(g[i]) * 1024 - s) * 37) >> 7)
        st[i] = s
    abe = st >> 10
    x = np.clip(-((abe * 48 * 1159) >> 15), -12000, 12000)
    wire18 = -x[tick].astype(float)
    t = tick / 1000.0
    req = np.ones(len(k))
    if t_dis is not None:
        req = (t < t_dis).astype(float)
    tq = np.zeros(len(k))
    if scn is not None and scn.tq is not None:
        tq = np.array([float(np.asarray(scn.tq(tt, th1k[i], om1k[i]) * np.ones(r["th"].shape[1]))[j])
                       for tt, i in zip(t, tick)])
    bar = -tq + rng.normal(0, bar_noise, len(k))
    ti = np.arange(14, n, 20)
    T_t = ti / 1000.0
    T = np.sign(T1k[ti]) * (np.abs(T1k[ti]) >> 3) * 8.0
    return dict(t=t, ang=ang, raw=raw, req=req, sca=req.copy(), bar=bar, wire18=wire18, vego=np.full(len(k), v),
                T_t=T_t, T=T)


def concat(parts, gap_s=2.5):
    """one 'drive' from several engaged episodes, separated by disengaged gaps."""
    keys = ("ang", "raw", "req", "sca", "bar", "wire18", "vego")
    acc = {kk: [] for kk in keys + ("t",)}
    Tt, TT = [], []
    t0 = 0.0
    for p in parts:
        acc["t"].append(p["t"] + t0)
        for kk in keys:
            acc[kk].append(p[kk])
        Tt.append(p["T_t"] + t0); TT.append(p["T"])
        tend = p["t"][-1] + t0
        ng = int(gap_s * 100)
        tg = tend + 0.01 * np.arange(1, ng + 1)
        acc["t"].append(tg)
        for kk in keys:
            fill = 0.0 if kk in ("req", "sca", "raw", "bar", "wire18") else p[kk][-1]
            acc[kk].append(np.full(ng, fill))
        Tt.append(tg[::2]); TT.append(np.zeros(len(tg[::2])))
        t0 = tg[-1] + 0.01
    A = {kk: np.concatenate(v) for kk, v in acc.items()}
    return DR.make_wire(A["t"], A["ang"], A["raw"], A["req"], A["sca"], A["bar"], A["wire18"], A["vego"],
                        np.concatenate(Tt), np.concatenate(TT), meta=dict(source="synthetic"))


_CACHE = {}


def drive(cid, member, speeds=SPEEDS6, dur=32.0, seed=3, uext=None, road=15.0, tag=""):
    """a synthetic multi-band drive of one control lane on one plant member -> W."""
    key = (cid, member, tuple(speeds), dur, seed, tag)
    if key in _CACHE:
        return _CACHE[key]
    C = cands()
    c = C[cid]
    cols = [dict(cand=c, member=member, v=v) for v in speeds]
    scn, _ = scn_path(cols, dur=dur, seed=seed, road=road, uext=uext)
    r = run_cols(cols, scn, LANE_KIND.get(cid))
    parts = [wire_of(r, j, v, seed=seed) for j, v in enumerate(speeds)]
    W = concat(parts)
    W["meta"].update(name="%s/%s%s" % (cid, member, tag), cid=cid, member=member)
    _CACHE[key] = W
    return W


# =====================================================================================================================
# CONTROL SETS
# =====================================================================================================================
EXPECT = {"C3B-P": "LIVE", "V295": "NOT LIVE (wrong image / torque firmware)", "SKIP": "NOT LIVE (cave skipped)",
          "C3-P56": "LIVE but c_I/c_P out (Ki 56)", "C3B-P-kd34": "LIVE but c_D out (Kd 34)",
          "kdneg": "INVERTED", "thneg": "INVERTED"}


def verdict_controls(members, ids=("C3B-P", "V295", "SKIP", "C3-P56", "C3B-P-kd34", "kdneg", "thneg")):
    pr("=" * 110)
    pr("A. VERDICT CONTROLS -- one synthetic 6-band drive (6 x 32 s, hands-off, road noise 15 T rms) per lane x member")
    pr("   decision-bearing = the STRUCTURAL regression; the design's literal form beside it; the replay R2 per image")
    pr("=" * 110)
    rows = []
    for cid in ids:
        for m in members:
            t0 = time.time()
            W = drive(cid, m)
            comp = DR.components(W)
            Rs = DR.regress_struct(W, comp)
            rep = DR.replay(W)
            R = DR.regress(W)
            import pickle
            (SCR / "fits").mkdir(exist_ok=True)
            with open(SCR / "fits" / ("%s__%s.pkl" % (cid, m.replace("*", "x"))), "wb") as fh:
                pickle.dump(dict(Rs=Rs, rep=rep, R=R), fh)      # verdict logic can be re-applied without a rerun
            V = DR.verdict(Rs, rep=rep)
            VL = DR.verdict(R)
            P = Rs["pooled"]
            row = dict(cid=cid, member=m, expect=EXPECT.get(cid), verdict=V["verdict"], ratio=V["ratio"],
                       cD=V["cD"], cIcP=V["cIcP"], dip=V["dip"], hi=V["hi"], lag=Rs["lag_frames"],
                       abcd=[P.get(k) for k in "abcd"], r2=P.get("r2"),
                       sched=V["sched"], clauses=[(x, y) for x, y, _ in V["clauses"]],
                       literal=dict(verdict=VL["verdict"], ratio=VL["ratio"], cIcP=VL["cIcP"], cD=VL["cD"],
                                    dip=VL["dip"], hi=VL["hi"], clauses=[(x, y) for x, y, _ in VL["clauses"]]),
                       replay={k: (v.get("r2"), v.get("gain")) for k, v in rep.items()},
                       peakT=float(np.max(np.abs(W["T"])) / 8), secs=time.time() - t0)
            rows.append(row)
            pr("  %-11s %-10s -> %-40s (expect %s)" % (cid, m, V["verdict"], EXPECT.get(cid)))
            pr("      structural: a %.3f b %.3f c %.3f d %.3f R2 %.4f | ratio %6.3f  c_I/c_P %5.2f  c_D %6.3f  dip %5.2f"
               "  hi %5.2f  sched %s" % (P.get("a", np.nan), P.get("b", np.nan), P.get("c", np.nan),
                                         P.get("d", np.nan), P.get("r2", np.nan), V["ratio"], V["cIcP"], V["cD"],
                                         V["dip"], V["hi"], " ".join("%s %.2f" % (k, x) for k, x in V["sched"].items())))
            pr("      literal:    %-40s ratio %6.3f  c_I/c_P %5.2f  c_D %6.3f  dip %5.2f  hi %5.2f" % (
                VL["verdict"], VL["ratio"], VL["cIcP"], VL["cD"], VL["dip"], VL["hi"]))
            pr("      replay R2 (gain): %s   |tap|max %.0f LSB  [%.0f s]" % (
                "  ".join("%s %s (%s)" % (k, DR.f3(v.get("r2")), DR.f3(v.get("gain"), "%.2f")) for k, v in rep.items()),
                row["peakT"], row["secs"]))
            pr("      failed clauses: %s" % [x for x, y, _ in V["clauses"] if y is False and x.startswith("LIVE")])
    return rows


def a2_controls(members):
    pr("=" * 110)
    pr("B. A2 / R7 CONTROLS -- request drop at 3.0 s during a 0.5 A_turn hold (score_time 'dis'), per speed")
    pr("=" * 110)
    C = cands()
    out = []
    for cid in ("C3B-P", "noA2", "z_A2", "z_noA2", "V295"):
        for m in members[:2]:
            cols = [dict(cand=C[cid], member=m, v=v) for v in (6.5, 11.25, 18.5, 25.0)]
            scn, meta = ST.scenario("dis", cols)
            r = run_cols(cols, scn, LANE_KIND.get(cid))
            parts = [wire_of(r, j, c["v"], t_dis=3.0) for j, c in enumerate(cols)]
            W = concat(parts)
            A = DR.a2_r7(W)
            tq = [x["t_quiet"] for x in A["rows"]]
            pu = [x["t_push0"] for x in A["rows"]]
            pr("  %-7s %-10s drops %d  A2 pass %d  -> A2 %s  R7 %s   t_quiet %s   t_push0 %s" % (
                cid, m, A["n"], A["n_pass"], A["live"], A["r7"], [round(x, 2) for x in tq], [round(x, 2) for x in pu]))
            out.append(dict(cid=cid, member=m, live=A["live"], r7=A["r7"], t_quiet=tq, t_push=pu))
    # R7 needs the lane to be ALREADY pushing toward centre at the drop (Honda's sign-hold gate 0x2A198 zeroes a
    # sign reversal once STEER_CONTROL_ACTIVE = 0): the fork returns the setpoint from 0.5 A_turn to 0 over 0.3 s
    # starting at 2.0 s, and the request drops at 2.15 s, mid-return, with raw = 0 from then on (SPEC C4).
    pr("  -- R7: request drop MID-RETURN (lane pushing toward centre), raw = 0 after the drop")
    for cid in ("z_A2", "z_noA2"):
        for m in members[:2]:
            cols = [dict(cand=C[cid], member=m, v=v) for v in (6.5, 11.25, 18.5, 25.0)]
            Ah = np.array([0.5 * ST.A_turn(c["v"]) for c in cols])
            scn = ST.Scn(dur=5.5, ref=lambda t, Ah=Ah: Ah * np.interp(t, [0, 0.5, 1.5, 2.0, 2.3, 99],
                                                                      [0, 0, 1, 1, 0, 0]),
                         events=((2.15, "dis"),))
            r = run_cols(cols, scn, LANE_KIND.get(cid))
            W = concat([wire_of(r, j, c["v"], t_dis=2.15) for j, c in enumerate(cols)])
            A = DR.a2_r7(W)
            tq = [x["t_quiet"] for x in A["rows"]]
            pu = [x["t_push0"] for x in A["rows"]]
            im = [x["imp0"] for x in A["rows"]]
            pr("  %-7s %-10s drops %d  A2 pass %d  -> A2 %s  R7 %s   t_quiet %s   t_push0 %s  impulse0 %s LSB*s" % (
                cid, m, A["n"], A["n_pass"], A["live"], A["r7"], [round(x, 2) for x in tq], [round(x, 2) for x in pu],
                [round(x, 2) for x in im]))
            out.append(dict(cid=cid + "_ret", member=m, live=A["live"], r7=A["r7"], t_quiet=tq, t_push=pu, imp=im))
    return out


def stop_controls(members):
    pr("=" * 110)
    pr("C. STOP-BAND DETECTOR CONTROLS (R2 rail, R3* ring, R4 line, R6 error) on synthetic drives")
    pr("=" * 110)
    out = {}
    refs = {k: DR.ref_summary(k, with_presence=False) for k in DR.REFS_DEFAULT}
    for cid in ("C3B-P", "V295", "thneg", "kdneg", "ki160", "ki400", "g4"):
        for m in members[:2]:
            W = drive(cid, m)
            r2, r3, r6 = DR.r2_rail(W), DR.r3_ring(W), DR.r6_err(W)
            cen = DR.census2(W)
            r4 = DR.r4_2(cen, {k: v["census"] for k, v in refs.items()})
            ev = [(e["chan"], round(e["f0"], 2), round(e["amp_max"], 2), round(e["r_gm"], 2), round(e["narrow"], 2))
                  for e in r3["events"][:3]]
            pr("  %-7s %-10s R2 %-5s R3* %-5s (%2d) %s  R4 %-5s %s  R6 %-5s |tap|max %.0f" % (
                cid, m, r2["fire"], r3["fire"], r3["n"], ev, r4["fire"],
                [(round(n["f"], 1), round(n["excess_db"], 1)) for n in r4["new"]][:3], r6["fire"],
                np.max(np.abs(W["T"])) / 8))
            out[(cid, m)] = dict(r2=r2["fire"], r3=r3["fire"], r3n=r3["n"], r4=r4["fire"], r6=r6["fire"], ev=ev)
    # planted lines: a sinusoidal wheel torque on the P0 drive (the detector's sensitivity, not a lane claim)
    pr("  -- R4 planted-line sensitivity (C3B-P, nominal; sinusoidal external torque, T counts amplitude)")
    plant = []
    for f in (8.0, 14.0, 20.0, 26.0):
        for A in (2.0, 5.0, 10.0, 20.0):
            def uext(t, f=f, A=A):
                return A * math.sin(2 * math.pi * f * t)
            W = drive("C3B-P", "nominal", uext=uext, tag="_line%.0f_%.0f" % (f, A))
            cen = DR.census2(W)
            r4 = DR.r4_2(cen, {k: v["census"] for k, v in refs.items()})
            hit = [n for n in r4["new"] if abs(n["f"] - f) <= 0.6]
            ln = [n for n in cen["w18"]["lines"] if abs(n["f"] - f) <= 0.6]
            plant.append(dict(f=f, A=A, fire=bool(hit), line_db=(ln[0]["excess_db"] if ln else None),
                              amp=(ln[0]["amp"] if ln else None)))
            pr("     f %5.1f Hz  A %5.1f T  -> line %s  R4 new %s" % (
                f, A, ("%.1f dB amp %.3f deg/s" % (ln[0]["excess_db"], ln[0]["amp"])) if ln else "none", bool(hit)))
    out["planted"] = plant
    # R3* commanded-ring control: the fork itself weaves the setpoint (0.42 Hz, 3 deg, 20 s) -> REVIEW, not R3*;
    # the same weave through a ringing lane (ki400) must still fire on the lane's own ring
    pr("  -- R3* commanded-weave control (C3B-P / ki400, nominal, 9 m/s; setpoint = path + 3 deg sine at 0.42 Hz)")
    for cid in ("C3B-P", "ki400"):
        C = cands()
        cols = [dict(cand=C[cid], member="nominal", v=9.0)]
        scn, P_ = scn_path(cols, dur=32.0, seed=5)
        base = scn.ref

        def ref(t, base=base):
            return base(t) + (3.0 * math.sin(2 * math.pi * 0.42 * t) if 8.0 <= t < 28.0 else 0.0)
        scn.ref = ref
        r = run_cols(cols, scn)
        W = concat([wire_of(r, 0, 9.0)])
        r3 = DR.r3_ring(W)
        pr("     %-6s R3* fire %-5s n %d review %d  fire-events %s  review %s" % (
            cid, r3["fire"], r3["n"], r3["n_review"],
            [(e["chan"], round(e["f0"], 2), round(e["amp_max"], 2), e["commanded"], round(e["coh_cmd"], 2) if
              e["coh_cmd"] == e["coh_cmd"] else None) for e in r3["events"][:3]],
            [(e["chan"], round(e["f0"], 2), round(e["amp_max"], 2)) for e in r3["review"][:3]]))
        out["weave_" + cid] = dict(fire=r3["fire"], n=r3["n"], review=r3["n_review"])
    return out


def planted_real():
    """R4 sensitivity ON A REAL BACKGROUND: a sinusoid of known amplitude added to the engaged 0x18F rate (deg/s) of the
    V294 route r71b (and to its torque bar, in wire counts), then the census vs the V282 references r6c / r39 / r3a.
    A synthetic drive's spectrum is far quieter than a road's, so only a real background sizes the detection floor."""
    pr("=" * 110)
    pr("H. R4 PLANTED LINES ON A REAL BACKGROUND (r71b engaged rate / bar + a sinusoid; refs r6c, r39, r3a)")
    pr("=" * 110)
    W0 = DR.load_route("r71b_v294", with_extras=False)
    refs = {t: DR.census2(DR.load_route(t, with_extras=False)) for t in ("r6c", "r39", "r3a")}
    out = []
    tt = W0["t"]
    for chan, amps in (("w18", (0.25, 0.5, 1.0, 2.0)), ("bar", (5.0, 10.0, 20.0, 40.0))):
        for f in (8.8, 11.0, 14.0, 17.0, 26.0):
            for A in amps:
                W = dict(W0)
                W[chan] = W0[chan] + np.where(W0["eng"], A * np.sin(2 * np.pi * f * tt), 0.0)
                cen = {chan: DR.line_census(W, chan=chan)}
                r4 = DR.r4_new_lines(cen[chan], {k: v[chan] for k, v in refs.items()})
                hit = [n for n in r4["new"] if abs(n["f"] - f) <= 0.6]
                ln = [n for n in cen[chan]["lines"] if abs(n["f"] - f) <= 0.6]
                out.append(dict(chan=chan, f=f, A=A, fire=bool(hit), db=(ln[0]["excess_db"] if ln else None)))
                pr("  %-4s f %5.1f Hz  A %6.2f  -> line %-8s R4 new %s" % (
                    chan, f, A, ("%.1f dB" % ln[0]["excess_db"]) if ln else "none", bool(hit)))
    return out


def real_negative_controls():
    """the detectors on REAL historical drives (V282 r6c/r39/r3a, V294 r71b): R3* must not fire on genuine road and
    path content; R4 must not flag a V282 route against other V282 routes."""
    pr("=" * 110)
    pr("D. REAL-DRIVE FALSE-ALARM CONTROLS (V282 / V294 routes; the angle setpoint does not exist on them, so R3* runs on")
    pr("   the 0x14A angle and the 0x18F rate only)")
    pr("=" * 110)
    out = {}
    tags = ("r6c", "r39", "r3a", "r71b_v294")
    W = {t: DR.load_route(t, with_extras=False) for t in tags}
    cen = {t: DR.census2(W[t]) for t in tags}
    for t in tags:
        r3 = DR.r3_ring(W[t], chans=("theta", "w18"), use_cmd=False)
        others = {o: cen[o] for o in tags if o != t and o != "r71b_v294"} if t != "r71b_v294" else \
            {o: cen[o] for o in ("r6c", "r39", "r3a")}
        r4 = DR.r4_2(cen[t], others)
        eng_s = W[t]["eng"].sum() / 100.0
        pr("  %-10s engaged %6.0f s   R3* %-5s n %d %s" % (t, eng_s, r3["fire"], r3["n"], [
            (e["chan"], round(e["f0"], 2), round(e["amp_max"], 2), round(e["r_gm"], 2), round(e["narrow"], 2))
            for e in r3["events"][:4]]))
        pr("             R4 vs %s: %s  lines here w18 %s bar %s" % (
            list(others), [(n["chan"], round(n["f"], 1), round(n["excess_db"], 1)) for n in r4["new"]],
            [(round(n["f"], 1), round(n["excess_db"], 1)) for n in cen[t]["w18"]["lines"]][:8],
            [(round(n["f"], 1), round(n["excess_db"], 1)) for n in cen[t]["bar"]["lines"]][:8]))
        out[t] = dict(eng_s=float(eng_s), r3=r3["fire"], r3n=r3["n"], r3ev=r3["events"][:4],
                      r4=[(n["chan"], n["f"], n["excess_db"]) for n in r4["new"]])
    return out


def goal_controls():
    """the goal criteria on the r71b REAL PATHS replayed through C3B-P -- the reader's tracking/turn-hold/dwell code
    must reproduce the common time scorer's own numbers for C3B-P (rev2 §4: clean 0.987 / 0.981 / 0.997)."""
    pr("=" * 110)
    pr("E. GOAL-METRIC CONTROL -- r71b real paths (rr, clean) through C3B-P on 'nominal'; the reader vs the scorer")
    pr("=" * 110)
    C = cands()
    out = {}
    for cid in ("C3B-P", "SKIP"):
        cols = ST.columns("rr", "nominal", [C[cid]])
        scn, meta = ST.scenario("rr", cols)
        r = run_cols(cols, scn)
        m = ST.metrics("rr", meta, r, cols)
        parts = []
        for j, c in enumerate(cols):
            p = wire_of(r, j, c["v"])
            L = meta["lens"][j]
            parts.append({k: (v[:L] if hasattr(v, "__len__") and len(v) == len(p["t"]) else v) for k, v in p.items()})
            parts[-1]["T_t"], parts[-1]["T"] = p["T_t"][p["T_t"] <= p["t"][L - 1]], p["T"][p["T_t"] <= p["t"][L - 1]]
        W = concat(parts, gap_s=2.0)
        G = DR.tracking_and_hold(W)
        dj = DR.dwell_jump(W)
        # the scorer's own pooled slope per band, from its XY
        sc = {}
        for nm, lo, hi in DR.BANDS_GOAL:
            X = [x for x, c in zip(m["XY"][0], cols) if lo <= c["v"] < hi]
            Y = [y for y, c in zip(m["XY"][1], cols) if lo <= c["v"] < hi]
            if X:
                Xa, Ya = np.concatenate(X), np.concatenate(Y)
                sc[nm] = float(np.linalg.lstsq(np.vstack([Xa, np.ones_like(Xa)]).T, Ya, rcond=None)[0][0])
            H = [h[0] for hs, c in zip(m["holds"], cols) if lo <= c["v"] < hi for h in hs]
            sc[nm + "_hold_min"] = min(H) if H else np.nan
        sc["dj_total"] = float(np.sum(m["dj"]))
        pr("  %-6s reader: %s" % (cid, "  ".join("%s track %.3f hold_min %s (%.0f s)" % (
            k, v.get("track", np.nan), DR.f3(v.get("hold_min")), v.get("secs", 0)) for k, v in G.items())))
        pr("  %-6s scorer: %s ; dwell-jump events scorer %d vs reader %d" % (
            cid, "  ".join("%s %.3f/%s" % (nm, sc.get(nm, np.nan), DR.f3(sc.get(nm + "_hold_min")))
                           for nm, _, _ in DR.BANDS_GOAL), sc["dj_total"], sum(v["n"] for v in dj.values())))
        out[cid] = dict(reader=G, scorer=sc, dj_reader=sum(v["n"] for v in dj.values()))
    return out


def friction_controls():
    """Coulomb / breakaway estimates vs the plant's TRUE Fc / Fs (nl_sim.params) -- nominal vs bc (bc doubles the
    friction at >= 10 m/s).  The estimator must track the truth and the x2."""
    pr("=" * 110)
    pr("F. FRICTION CONTROLS -- the estimator vs the member's true Fc/Fs (T counts), C3B-P drives")
    pr("=" * 110)
    out = {}
    sp = (3.0, 6.5, 10.0, 15.0, 21.0, 27.0)
    for m in ("nominal", "bc", "F_hi"):
        W = drive("C3B-P", m, speeds=sp, tag="_fric", road=15.0)
        F = DR.friction(W)
        truth = {nm: NS.params(m, v)[4:6] for (nm, _, _), v in zip(DR.BANDS_FRIC, sp)}
        for nm, v in F.items():
            if v.get("ok"):
                pr("  %-8s %-7s Fc est %6.1f (true %5.1f)  breakaway p50 %6.1f (true Fs %5.1f)  n_break %d" % (
                    m, nm, v["Fc"], truth[nm][0], v["Fs_p50"], truth[nm][1], v["n_break"]))
            else:
                pr("  %-8s %-7s (not enough sliding: %s)" % (m, nm, v))
        out[m] = dict(est={k: (v.get("Fc"), v.get("Fs_p50")) for k, v in F.items()}, truth=truth)
    return out


def light_controls():
    """the opposing-hand freeze: a 3 s light hold (400 wire) outward and inward; C3B-P must keep the I flat, the
    no-freeze lane must ramp it."""
    pr("=" * 110)
    pr("G. LIGHT-HOLD CONTROLS -- 3 s hold at 400 (score_time ov3_lt400 = inward) + its outward mirror")
    pr("=" * 110)
    C = cands()
    out = []
    for cid in ("C3B-P", "nofrz"):
        for kind in ("inward", "outward"):
            cols = [dict(cand=C[cid], member="nominal", v=v) for v in (9.0, 13.75, 18.5)]
            scn, meta = ST.scenario("ov3_lt400", cols)
            if kind == "outward":
                B = len(cols)
                Ah = meta["Ah"]
                sg = np.sign(Ah)
                tg, tr, trel = 2.5, 0.3, 2.5 + 0.3 + 3.0
                scn.tq = lambda t, th, om, w=400.0: (sg * w * min(1.0, (t - tg) / tr)) if tg <= t < trel else 0.0 * sg

                def hand(t, Ah=Ah):
                    if not (int(round(tg * 1000)) <= int(round(t * 1000)) < int(round(trel * 1000))):
                        return None
                    fr = min(1.0, (t - tg) / tr)
                    return (np.full(B, 2000.0), np.full(B, 30.0), Ah * (1 + 0.6 * fr))
                scn.hand = hand
            r = run_cols(cols, scn)
            parts = [wire_of(r, j, c["v"], scn=scn) for j, c in enumerate(cols)]
            W = concat(parts)
            Wfit = drive("C3B-P", "nominal")
            R = DR.regress_struct(Wfit, DR.components(Wfit))
            LH = DR.light_holds(W, R, DR.components(W))
            for x in LH["rows"]:
                pr("  %-6s %-8s v %5.2f  detected %-8s dI %6.0f T [%s]  release overshoot %5.2f deg [%s]" % (
                    cid, kind, x["v"], x["kind"], x["dI_T"], "flat" if x["flat"] else "RAMPS", x["release_ovs"],
                    "pass" if x["ovs_pass"] else "FAIL"))
            out.append(dict(cid=cid, kind=kind, rows=LH["rows"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", nargs="?", default="all")
    ap.add_argument("--members", default="nominal,bc,b_lo*J_hi,F_hi")
    a = ap.parse_args()
    mem = a.members.split(",")
    res = {}
    t0 = time.time()
    if a.what in ("all", "verdict"):
        res["verdict"] = verdict_controls(mem)
    if a.what in ("all", "a2"):
        res["a2"] = a2_controls(mem)
    if a.what in ("all", "stops"):
        res["stops"] = {str(k): v for k, v in stop_controls(mem).items()}
    if a.what in ("all", "real"):
        res["real"] = real_negative_controls()
    if a.what in ("all", "goal"):
        res["goal"] = goal_controls()
    if a.what in ("all", "friction"):
        res["friction"] = friction_controls()
    if a.what in ("all", "planted"):
        res["planted"] = planted_real()
    if a.what in ("all", "light"):
        res["light"] = light_controls()
    pr("\n(%.0f s)" % (time.time() - t0))
    tag = a.what + ("" if a.members == "nominal,bc,b_lo*J_hi,F_hi" else "_" + a.members.replace("*", "x").replace(",", "+"))
    (SCR / ("controls_%s.json" % tag)).write_text(json.dumps(res, indent=1, default=DR._js))
    (SCR / ("controls_%s.txt" % tag)).write_text("\n".join(OUT), encoding="utf-8")
    pr("wrote %s" % (SCR / ("controls_%s.txt" % tag)))


if __name__ == "__main__":
    main()
