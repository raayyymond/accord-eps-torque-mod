# -*- coding: utf-8 -*-
r"""d1_r79.py -- ROUTE-79 COUNTERFACTUALS for D1's freeze / bound edits (open-loop replay on the measured wire).

ANALYSIS ONLY: reads the v280 wire cache + the V298 image (via v298_flight/m3_lane.py, whose lane is validated word-
for-word against the instrument's exact replay and whose primary replay = V298 arithmetic + dir-2 ramp + the torque
word leading 0x18F by 10 ticks, R2 0.928).  Writes out/d1_r79.{txt,json}.

THE RULES (per 1 kHz tick, the cave's ordered decision; tq = gp-0x4f60 signed, atq = gp-0x4f68, Ep = E', ab = gp-0x6abe):
  V298      hard atq > 512  |  opp: atq > 300 & (tq ^ Ep) < 0                          | A3 (cap 4096 at v <= 1382)
  D1a       hard atq > 1229 (opp clause made inert: its movea 300 -> 1229)              | A3
  D1a-c8k   D1a + A3 cap 4096 -> 8192 (= ICL: the cap clause inert)
  D1b       hard atq > 1229 | opp: atq > 300 & (tq ^ Ep) < 0 & NOT closing, closing = the wheel moves toward the
            setpoint faster than A0: Ep >= 0 ? ab + A0 < 0 : -ab + A0 < 0   (ab ~ -4.71 counts per deg/s, pol -1)
  D1b-c8k   D1b + cap 8192
  (+ diagnostic rows: the opposing threshold alone moved, the gate deadband A0 swept)
OPEN-LOOP CAVEAT (BELIEF): the replay feeds the RECORDED error to a different integrator; on the car the error would
change too.  It answers "how much integration a rule keeps on this drive" and "which rule the next drive's tap will
select" -- not the closed-loop torque.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import signal

T00 = time.time()
HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
sys.path.insert(0, str(AL / "v298_flight"))
import m3_lane as M  # noqa: E402
import m4_common as C4  # noqa: E402,F401
import m4_episodes as EP  # noqa: E402

OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
LINES, RES = [], {}


def pr(s=""):
    LINES.append(s)
    print(s, flush=True)


def r2(y, yh):
    ss = np.sum((y - y.mean()) ** 2)
    return float(1 - np.sum((y - yh) ** 2) / ss) if ss > 0 else float("nan")


def runs(mk):
    e = np.flatnonzero(np.diff(np.r_[0, mk.astype(int), 0]))
    return list(zip(e[::2], e[1::2]))


# ---------------------------------------------------------------------------------------------------------------- load
Cc = M.image_cells()
GL = M.glut(Cc["rows"])
W = M.load_wire()
th, cmd, tq, x, abe, vws = M.wire_inputs(W)
n = len(th)
t, v, eng = W["t"], W["vego"], W["eng"]
settled = eng & (W["tse"] >= 1.2)
nopress = ~W["pressed"]
r0, R = M.ramp_ticks(eng, Cc["ramp_in2"], Cc["ramp_out2"])
QS = 10
L = M.lane_terms(Cc, th, cmd, tq, x, abe, vws, eng, R, r0, GL, q_shift=QS)
F, m = L["F"], L["m"]
# gp-0x6abe per tick, the same construction as lane_terms (ticks 0..8 = frame k, tick 9 = frame k+1)
kn = np.minimum(F + 1, n - 1)
ab = np.empty((m, 10), np.int64)
ab[:, :9] = abe[F][:, None]
ab[:, 9] = abe[kn]
ab = M.FL.s16(ab.ravel())
pr(f"load + lane terms {time.time() - T00:.1f} s; frames {n}, marched {m}; engaged {eng.sum() / 100:.0f} s, "
   f"settled hands-off {(settled & nopress).sum() / 100:.0f} s, settled pressed {(settled & ~nopress).sum() / 100:.0f} s")

atq, hs, Ep, c4 = L["atq"], L["hs"], L["Ep"], L["c4"]
opp = (hs ^ Ep) < 0


def closing(A0):
    return np.where(Ep >= 0, ab + A0 < 0, -ab + A0 < 0)


def rule(hard, sgn=None, A0=None, still=None):
    c1 = atq > hard
    if sgn is None:
        return c1
    c2 = (np.abs(hs) > sgn) & opp & ~c1
    if A0 is not None:
        c2 &= ~closing(A0)
    if still is not None:                        # D1f: freeze on an opposing word only while the wheel is held still
        c2 &= np.abs(ab) <= still
    return c1 | c2


RULES = {
    "V298 (512 | opp300)": (rule(512, 300), 4096),
    "opp threshold only: 512 | opp700": (rule(512, 700), 4096),
    "hard 1229 | opp300 (no gate)": (rule(1229, 300), 4096),
    "D1a: hard 1229, opp inert": (rule(1229), 4096),
    "D1a-c8k": (rule(1229), 8192),
    "D1b: 1229 | opp300 & ~closing(A0 10)": (rule(1229, 300, 10), 4096),
    "D1b A0 0": (rule(1229, 300, 0), 4096),
    "D1b A0 24 (5 deg/s)": (rule(1229, 300, 24), 4096),
    "D1b-c8k": (rule(1229, 300, 10), 8192),
    "D1c: D1a hand rule + ASYM bound": (rule(1229), 4096, True),
    "D1f: 1229 | opp300 & |abe|<=10 + ASYM": (rule(1229, 300, still=10), 4096, True),
    "D1f W20 (4 deg/s) + ASYM": (rule(1229, 300, still=20), 4096, True),
}
RULES = {k: (v + (False,) if len(v) == 2 else v) for k, v in RULES.items()}

# ---------------------------------------------------------------------------- reaction-twist fit (input to d1_time.py)
b8, a8 = signal.butter(2, 8.0 / 50.0)
w_lp = signal.filtfilt(b8, a8, W["w18"])
alpha1 = np.gradient(w_lp) * 100.0
gp60 = -W["bar"]
mR = settled & nopress & np.isfinite(alpha1)
X = np.c_[alpha1[mR], w_lp[mR], np.tanh(w_lp[mR] / 2.0), W["ang"][mR], np.ones(mR.sum())]
bR, *_ = np.linalg.lstsq(X, gp60[mR], rcond=None)
res = gp60[mR] - X @ bR
ac1 = float(np.corrcoef(res[1:], res[:-1])[0, 1])
pr(f"reaction fit (settled, hands-off): J {bR[0]:.3f} b {bR[1]:.3f} Fc {bR[2]:.1f} k {bR[3]:.3f} c0 {bR[4]:.1f}; "
   f"R2 {r2(gp60[mR], X @ bR):.3f}; residual std {res.std():.0f} words, lag-1 autocorr (100 Hz) {ac1:.3f}")
RES["reaction"] = dict(J=bR[0], b=bR[1], Fc=bR[2], k=bR[3], c0=bR[4], res_std=float(res.std()), ac1=ac1)

# ---------------------------------------------------------------------------------- per-band freeze duty and discard
BANDS = (("<5", 0, 5), ("5-8", 5, 8), ("8-12.5", 8, 12.5), ("12.5-22", 12.5, 22), (">22", 22, 99), ("all", 0, 99))
run = L["run"]
inc_abs = np.abs(L["inc_exact"])
fr_v = np.repeat(v[F], 10)
fr_ho = np.repeat((settled & nopress)[F], 10)
fr_pr = np.repeat((settled & ~nopress)[F], 10)
pr("\nA. HAND-FREEZE per rule (1 kHz ticks; the 100 Hz word held 10 ticks, leading 0x18F by 10 ticks)")
pr("   duty = share of hands-off run ticks frozen by a hand rule; lost = |inc|-weighted share of commanded integration")
pr("   discarded by the hand rule (no A3: the refuter's form); tog = hand-freeze on/off transitions per minute;")
pr("   PRESSED = settled & steeringPressed (a real hand) -- the duty a safe rule must KEEP high there")
pr("   %-38s" % "rule" + "".join("%17s" % b[0] for b in BANDS) + "%12s" % "PRESSED")
pr("   %-38s" % "" + "".join("%17s" % "duty/lost/tog" for _ in BANDS) + "%12s" % "duty")
RES["A"] = {}
for nm, (fz, cap, asy) in RULES.items():
    row, outs = [], {}
    for bn, lo, hi in BANDS:
        mk = run & fr_ho & (fr_v >= lo) & (fr_v < hi)
        if mk.sum() < 1000:
            row.append("%17s" % "-")
            continue
        duty = fz[mk].mean()
        lost = inc_abs[mk & fz].sum() / max(inc_abs[mk].sum(), 1e-9)
        tr = np.count_nonzero((fz[1:] != fz[:-1]) & mk[1:] & mk[:-1])
        tog = tr / (mk.sum() / 60000.0)
        outs[bn] = dict(duty=float(duty), lost=float(lost), tog=float(tog))
        row.append("%17s" % ("%4.1f/%4.1f/%4.0f" % (100 * duty, 100 * lost, tog)))
    mp = run & fr_pr
    pdu = float(fz[mp].mean()) if mp.sum() else float("nan")
    outs["PRESSED"] = pdu
    RES["A"][nm] = outs
    pr("   %-38s" % nm + "".join(row) + "%11.1f%%" % (100 * pdu))

# ------------------------------------------------------------------------------- B. stall-surge near freeze toggles
pr("\nB. STALL-SURGE events (M4 detector, unmodified) near a hand-freeze TOGGLE (+-0.25 s) -- the refuter's D4 split,")
pr("   per rule, evaluated at 100 Hz on the wire (|word| = |bar|, sign(word) = -sign(bar), sign(E') = sign(err),")
pr("   closing = sign(w18) == sign(err) & |w18| > A0/4.712).  'lose' = V298-near events with no toggle of the rule")
pr("   within +-0.25 s (the events the freeze fix acts on; that the stall would then not occur is BELIEF -- the")
pr("   refuter's near/free contrast 80.7 vs 30.3 /min and the no-enrichment control on V282/V294 are the evidence)")
G = dict(W)
ss = EP.stall_surge(G, eng)
Rs = ss["R"]
bar, err, w18 = W["bar"], W["err"], W["w18"]
oppw = (np.sign(-bar) != np.sign(err)) & (err != 0)


def wire_rule(hard, sgn=None, A0=None):
    c1 = np.abs(bar) > hard
    if sgn is None:
        return c1
    c2 = (np.abs(bar) > sgn) & oppw & ~c1
    if A0 is not None:
        c2 &= ~((np.sign(w18) == np.sign(err)) & (np.abs(w18) > A0 / 4.712))
    return c1 | c2


def wire_still(hard, sgn, W):
    c1 = np.abs(bar) > hard
    return c1 | ((np.abs(bar) > sgn) & oppw & ~c1 & (np.abs(w18) <= W / 4.712))


WRULES = {"V298 (512 | opp300)": wire_rule(512, 300), "D1a: hard 1229, opp inert": wire_rule(1229),
          "D1f: 1229 | opp300 & |w|<=2.1 deg/s": wire_still(1229, 300, 10),
          "D1b: 1229 | opp300 & ~closing(A0 10)": wire_rule(1229, 300, 10),
          "hard 1229 | opp300 (no gate)": wire_rule(1229, 300)}
near0 = None
RES["B"] = {}
for nm, fz in WRULES.items():
    tog = np.r_[False, fz[1:] != fz[:-1]] & eng
    near = np.convolve(tog.astype(float), np.ones(51), "same") > 0
    if near0 is None:
        near0 = near
    out = {}
    for bn, lo, hi in (("0-5", 0, 5), ("5-10", 5, 10), ("10-20", 10, 20)):
        tb = ss["turn"] & (v >= lo) & (v < hi)
        sel = (v[Rs[:, 0]] >= lo) & (v[Rs[:, 0]] < hi)
        nr = near[Rs[:, 0]] & sel
        lost = near0[Rs[:, 0]] & ~near[Rs[:, 0]] & sel
        out[bn] = dict(turn_s=float(tb.sum() / 100), events=int(sel.sum()), near=int(nr.sum()),
                       near_share_of_turn=float((tb & near).sum() / max(tb.sum(), 1)), lose_toggle=int(lost.sum()),
                       tog_per_min_turn=float((tog & tb).sum() / max(tb.sum() / 6000, 1e-9)))
    RES["B"][nm] = out
    pr("   %-38s " % nm + " | ".join("%s: ev %d near %d (turn-time near %.0f%%) lose %d, tog %.0f/min" % (
        bn, o["events"], o["near"], 100 * o["near_share_of_turn"], o["lose_toggle"], o["tog_per_min_turn"])
        for bn, o in out.items()))

# --------------------------------------------------------------------------------------- C. replays (I recursion)
pr("\nC. REPLAYS (V298 lane arithmetic, the rule's freeze + A3 with the rule's cap; open loop on the recorded error)")
TT, Tt = W["T_t"], W["T"]
hob = np.abs(W["bar"]) < 500.0


def score(T100, extra=None, lag=None):
    lags = range(-2, 9) if lag is None else (lag,)
    best = None
    for L_ in lags:
        jj = np.clip(np.searchsorted(t, TT - L_ * 0.01, side="right") - 1, 0, n - 1)
        mb = (eng & hob & (W["tse"] >= 1.2))[jj] & np.isfinite(Tt)
        if extra is not None:
            mb &= extra[jj]
        if mb.sum() < 50:
            continue
        val = r2(Tt[mb] / 8.0, T100[jj[mb]] / 8.0)
        if best is None or val > best[1]:
            best = (L_, val, int(mb.sum()))
    return best


def bound_with_cap(cap, asym=False):
    th6 = L["th6"]
    vwm = np.repeat(np.clip(vws[F], 0, 12000), 10) & 0xFFFF
    sh = np.where(vwm <= 2880, 4, 6)
    opnd = np.where(asym & ((th6 ^ Ep) < 0), 0, np.abs(th6))         # D1c: inward I bounded by B alone
    b = M.FL.s32((opnd << sh) + 1250)
    return np.where((vwm <= 1382) & (b > cap), cap, b)


assert np.array_equal(bound_with_cap(4096), L["bound"])           # control: the cap form reproduces lane_terms' bound
REP = {}
hard_m = settled & nopress & ((np.abs(w_lp) >= 20) | (np.abs(alpha1) >= 100))
lo8 = v < 8.0
for nm, (fz, cap, asy) in RULES.items():
    Lr = dict(L)
    Lr["bound"] = bound_with_cap(cap, asy)
    Ia, a3s, clp, nev = M.i_recursion(Lr, fz | c4, a3=True, icl_s=Cc["icl"])
    T100 = M.output_T(Cc, Lr, Ia, n)
    REP[nm] = dict(T=T100, Ia=Ia, a3s=a3s)
    sc = score(T100)
    I4 = M.slot4(L, np.where(run, Ia >> 7, 0), n)
    tapr = np.abs(T100) / 8.0
    a3f = M.per_frame_frac(L, a3s & run, n)
    a3tog = np.count_nonzero((a3s[1:] != a3s[:-1]) & fr_ho[1:] & run[1:]) / (np.count_nonzero(fr_ho & run) / 60000.0)
    RES.setdefault("C", {})[nm] = dict(a3_tog_per_min=float(a3tog), lag=sc[0], r2=sc[1], tap_hard_p50=float(np.percentile(tapr[hard_m], 50)),
                                       tap_hard_p99=float(np.percentile(tapr[hard_m], 99)),
                                       tap_hard_lo8_p99=float(np.percentile(tapr[hard_m & lo8], 99)),
                                       tap_max=float(tapr[eng].max()),
                                       I_hard_p90=float(np.percentile(np.abs(I4[hard_m]), 90)),
                                       a3_frac_hard=float(a3f[hard_m].mean()))
    o = RES["C"][nm]
    pr("   %-38s R2 vs tap %.3f (lag %+d) | |replay tap| hands-off manoeuvres p50 %5.1f p99 %5.1f (<8 m/s p99 %5.1f),"
       " max %5.1f LSB | |I>>7| p90 %5.0f S | at A3 bound %4.1f%%, A3 toggles %4.0f/min" % (
           nm, o["r2"], o["lag"], o["tap_hard_p50"], o["tap_hard_p99"], o["tap_hard_lo8_p99"], o["tap_max"],
           o["I_hard_p90"], 100 * o["a3_frac_hard"], o["a3_tog_per_min"]))
jj0 = np.clip(np.searchsorted(t, TT, side="right") - 1, 0, n - 1)
mt = np.abs(Tt[eng[jj0] & np.isfinite(Tt)]) / 8.0
pr("   measured tap (engaged) p99 %.0f, max %.0f LSB; rail 307.6 LSB" % (np.percentile(mt, 99), mt.max()))

# ------------------------------------------------------------------ D. one-short-drive discriminator (30 s windows)
pr("\nD. ONE-SHORT-DRIVE DISCRIMINATOR: on r79 the TRUE rule is V298.  In each 30 s settled window, does the V298")
pr("   replay beat the D1 replay (R2 vs the tap, lag fixed at the pooled best)?  The next drive runs the same test the")
pr("   other way round: it says WHICH RULE RAN with zero firmware bytes (a model-selection instrument, like M3's).")
lagb = RES["C"]["V298 (512 | opp300)"]["lag"]
win = np.zeros(n, np.int64) - 1
k = 0
for a, b in runs(settled):
    for s0 in range(a, b - 2999, 3000):
        win[s0:s0 + 3000] = k
        k += 1
pr("   windows: %d" % k)
for alt in ("D1b: 1229 | opp300 & ~closing(A0 10)", "D1a: hard 1229, opp inert", "D1c: D1a hand rule + ASYM bound",
            "D1f: 1229 | opp300 & |abe|<=10 + ASYM"):
    d, dhard = [], []
    for w_ in range(k):
        ex = win == w_
        s1 = score(REP["V298 (512 | opp300)"]["T"], ex, lagb)
        s2 = score(REP[alt]["T"], ex, lagb)
        if s1 is None or s2 is None:
            continue
        d.append(s1[1] - s2[1])
        if (hard_m & ex).sum() >= 200:
            dhard.append(s1[1] - s2[1])
    d, dhard = np.array(d), np.array(dhard)
    RES.setdefault("D", {})[alt] = dict(n=int(len(d)), frac_true_wins=float(np.mean(d > 0)),
                                        frac_true_wins_by_002=float(np.mean(d > 0.02)), d_p50=float(np.median(d)),
                                        d_p10=float(np.percentile(d, 10)), n_manoeuvre=int(len(dhard)),
                                        frac_true_wins_manoeuvre=float(np.mean(dhard > 0)) if len(dhard) else None)
    o = RES["D"][alt]
    pr("   V298 vs %-38s: windows %d, true rule wins %.0f%% (by > 0.02: %.0f%%), dR2 p50 %+.3f p10 %+.3f; windows with"
       " >= 2 s of hands-off manoeuvre %d, true wins %s" % (
           alt, o["n"], 100 * o["frac_true_wins"], 100 * o["frac_true_wins_by_002"], o["d_p50"], o["d_p10"],
           o["n_manoeuvre"], "%.0f%%" % (100 * o["frac_true_wins_manoeuvre"]) if o["frac_true_wins_manoeuvre"] is not None else "-"))

pr(f"\nwall {time.time() - T00:.1f} s")
(OUT / "d1_r79.txt").write_text("\n".join(LINES), encoding="utf-8")
(OUT / "d1_r79.json").write_text(json.dumps(RES, indent=1, default=float), encoding="utf-8")
