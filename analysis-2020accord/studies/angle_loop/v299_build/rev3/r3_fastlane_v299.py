# -*- coding: utf-8 -*-
r"""r3_fastlane_v299.py -- the V299 rule in the drive read's byte-exact fast lane (rlog-tools/studies/angle_loop/
drive_read_fastlane.py: ARB_V299, arb_bound, static_freeze), and the checks that it is right.  ANALYSIS ONLY.

  snap   (run BEFORE the fast-lane edit) march C3B-P (= V298's lane) on route 79 with the stock (33,16) and the dir-2
         (328,66) ramps, DIRECTLY through FL.cand_lane (no replay cache), save T and the I log.
  check  (after the edit)
    K0  C3B-P outputs on r79 identical, word for word, to the snapshot (the V298 path did not move)          must be 0
    K1  the fast lane's V299 freeze predicate (static_freeze | the I-vs-arb_bound test, the cand_lane code) vs the
        spec mirror rev_h1.cave_rev2 (which H1 proved == the rev-2 BYTES, 0/4000 + 0/2941 + 0/2913) on random +
        edge cases (v-word 1381..1383 / 2879..2881, theta = 0, +-1, s16 extremes, |hand| 1228..1230, I at the bound)  must be 0
    N1  the same predicate vs cave_rev2 at rev-1 caps (4096 <= 1382 only)                                      must be > 0
    N2  the fast lane's V298 predicate (ARB_A3, thr 512, sgn 300) vs cave_rev2                                  must be > 0
    F1  route 79 (V298 flew): per-30-s-window R^2 of the tap vs the V299-rule replay and the V298-rule replay,
        dir-2 ramp, hands-off settled frames -- the instrument of the drive card's F1; on r79 V298 must win
usage: python r3_fastlane_v299.py snap|check   (< 30 s each)"""
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[4]
DR = KIT / "rlog-tools" / "studies" / "angle_loop"
sys.path.insert(0, str(DR))
sys.path.insert(0, str(HERE.parents[1] / "v299_design" / "revise"))
OUT = KIT / "_scratch" / "v299_REV3"
OUT.mkdir(parents=True, exist_ok=True)
SNAP = OUT / "fastlane_c3bp_r79_snapshot.npz"
ROUTE = "r79_a1f5d2_al"


def setup():
    import angle_loop_drive_read as D
    import drive_read_fastlane as FL
    import nl_sim as NS
    ST = D.load_score_time()
    C = D.replay_cands(ST)
    W = D.load_route(ROUTE, with_extras=False)
    return D, FL, NS, ST, C, W


def march(D, FL, NS, ST, c, W, ramp):
    th, cmd, tq, x, abe, vws = D.wire_inputs(W)
    p = FL.cand_params(c)
    r0, R = FL.ramp_ticks(W["eng"], *ramp)
    return FL.cand_lane(p, ST.glut(c.rows), NS.CAL, th, cmd, tq, x, abe, vws, np.asarray(W["eng"], bool), R, r0,
                        rec_I=True)


def snap():
    D, FL, NS, ST, C, W = setup()
    out = {}
    for ramp in ((33, 16), (328, 66)):
        T, I = march(D, FL, NS, ST, C["C3B-P"], W, ramp)
        out["T_%d" % ramp[0]], out["I_%d" % ramp[0]] = T, I
    np.savez_compressed(SNAP, **out)
    print("snapshot", SNAP, {k: int(np.abs(v).sum()) for k, v in out.items()})


def predicate(FL, p, th, Ep, v, hand, ramp, I8):
    """the cand_lane freeze decision for one tick, from the SAME helpers cand_lane calls."""
    fs = FL.static_freeze(p, hand, Ep, ramp)
    bd = FL.arb_bound(p["arb"], th, v & 0xFFFF, Ep) if p["arb"] is not None else None
    I = I8 >> 3                                              # the fast lane's I unit (I8 >> 3), as cand_lane
    sg = Ep >= 0
    wind = (np.where(sg, I >> 7, -(I >> 7)) >= bd) if bd is not None else np.zeros(len(th), bool)
    return fs | wind


def cases(N, seed):
    rng = np.random.default_rng(seed)
    th = rng.integers(-3000, 3001, N)
    th[: N // 20] = rng.choice([0, 1, -1, 32767, -32768, 255, -256], N // 20)
    Ep = rng.integers(-200000, 200001, N)
    Ep[N // 20: N // 10] = rng.choice([0, 1, -1], N // 10 - N // 20)
    v = rng.integers(0, 12001, N)
    v[N // 10: N // 2] = rng.choice([0, 1381, 1382, 1383, 2879, 2880, 2881, 4000], N // 2 - N // 10)
    hand = rng.integers(-3000, 3001, N)
    hand[: N // 8] = rng.choice([1228, 1229, 1230, -1229, -1230, 512, 513, 300, 301], N // 8)
    ramp = np.where(rng.random(N) < 0.85, 0x8000, rng.integers(0, 0x8000, N))
    I8 = rng.integers(-(8192 << 10), (8192 << 10) + 1, N)
    # a third of the cases put the integrator within a few S of the bound the mirror computes
    return th, Ep, v, hand, ramp, I8


def mirror(th, Ep, v, hand, ramp, I8, caps):
    import rev_h1 as H
    out = np.zeros(len(th), bool)
    for i in range(len(th)):
        # cave_rev2 recomputes E' = ((sp<<2) - r26) G >> 8: choose sp = 0, G = 256, r26 = -E' so E' is exact
        ex, *_ = H.cave_rev2(0, -int(Ep[i]) // 1, int(ramp[i]), 1, 0, int(v[i]), abs(int(hand[i])) & 0xFFFF,
                              int(th[i]), int(I8[i]), 256, caps=caps)
        out[i] = ex != H.NC.HOOK_RET
    return out


def check():
    T0 = time.perf_counter()
    D, FL, NS, ST, C, W = setup()
    # K0
    S = np.load(SNAP)
    k0 = 0
    for ramp in ((33, 16), (328, 66)):
        T, I = march(D, FL, NS, ST, C["C3B-P"], W, ramp)
        k0 += int(np.sum(T != S["T_%d" % ramp[0]]) + np.sum(I != S["I_%d" % ramp[0]]))
    print("K0 C3B-P (V298 lane) r79 words differing from the pre-edit snapshot: %d (must be 0)" % k0)
    # K1 / N1 / N2
    pV = FL.cand_params(FL.v299_cand(ST, C["C3B-P"]))
    p8 = FL.cand_params(C["C3B-P"])
    th, Ep, v, hand, ramp, I8 = cases(6000, 7)
    # bias a third of I8 onto the rev-2 bound +-2 S (sign-aligned with E')
    import rev_h1 as H  # noqa: F401
    bd = FL.arb_bound(pV["arb"], th, v & 0xFFFF, Ep)
    k = slice(0, 2000)
    sg = np.where(Ep[k] >= 0, 1, -1)
    I8[k] = sg * ((bd[k] + np.random.default_rng(3).integers(-2, 3, 2000)) << 10)
    I8[k] = np.clip(I8[k], -(8192 << 10), 8192 << 10)       # |I| <= ICL 8192 S always (Honda's clamp): a bound
    #   above ICL (theta near the s16 extremes at v > 2880) is unreachable and would wrap the mirror's s32 harness
    hand_s = hand.copy()
    fast = predicate(FL, pV, th, Ep, v, hand_s, ramp, I8)
    m2 = mirror(th, Ep, v, hand, ramp, I8, ((1382, 4096), (2880, 6144)))
    m1 = mirror(th, Ep, v, hand, ramp, I8, ((1382, 4096), (None, None)))
    f8 = predicate(FL, p8, th, Ep, v, hand_s, ramp, I8)
    print("K1 fast-lane V299 freeze vs cave_rev2 (rev-2 caps): %d / %d mismatches (must be 0); freezes %d, runs %d"
          % (int(np.sum(fast != m2)), len(th), int(fast.sum()), int((~fast).sum())))
    print("N1 fast-lane V299 vs cave_rev2 at rev-1 caps: %d mismatches (must be > 0)" % int(np.sum(fast != m1)))
    print("N2 fast-lane V298 rule vs cave_rev2: %d mismatches (must be > 0)" % int(np.sum(f8 != m2)))
    # F1 instrument on r79
    th_, cmd, tq, x, abe, vws = D.wire_inputs(W)
    eng = np.asarray(W["eng"], bool)
    r0, R = FL.ramp_ticks(eng, 328, 66)
    T8, _ = FL.cand_lane(p8, ST.glut(C["C3B-P"].rows), NS.CAL, th_, cmd, tq, x, abe, vws, eng, R, r0, rec_I=True)
    T9, _ = FL.cand_lane(pV, ST.glut(C["C3B-P"].rows), NS.CAL, th_, cmd, tq, x, abe, vws, eng, R, r0, rec_I=True)
    n = len(th_)
    base = (W["eng"] & W["handsoff"] & (W["tse"] >= D.THR["settle_s"]))[:n]
    j = np.clip(np.searchsorted(W["t"][:n], W["T_t"], side="right") - 1, 0, n - 1)
    m = base[j] & np.isfinite(W["T"])
    y = W["T"][m] / 8.0
    tt = W["T_t"][m]
    wid = ((tt - tt.min()) // 30.0).astype(int)
    rows = []
    for w in np.unique(wid):
        q = wid == w
        if q.sum() < 200:
            continue
        yy = y[q]
        ss = np.sum((yy - yy.mean()) ** 2)
        if ss <= 0:
            continue
        r = []
        for Tc in (T8, T9):
            yh = np.sign(Tc[j[m][q]]) * (np.abs(Tc[j[m][q]]) >> 3)
            r.append(1 - np.sum((yy - yh) ** 2) / ss)
        rows.append(r)
    rows = np.array(rows)
    d = rows[:, 0] - rows[:, 1]
    print("F1 instrument on r79 (V298 flew): %d windows; V298-rule wins %d/%d; dR2 (V298 - V299) p10 %.3f p50 %.3f; "
          "pooled R2 V298 %.3f V299 %.3f; frames where the two replays differ %.1f %%"
          % (len(rows), int((d > 0).sum()), len(rows), np.percentile(d, 10), np.median(d), rows[:, 0].mean(),
             rows[:, 1].mean(), 100.0 * np.mean(T8 != T9)))
    print("wall %.1f s" % (time.perf_counter() - T0))


if __name__ == "__main__":
    {"snap": snap, "check": check}[sys.argv[1]]()
