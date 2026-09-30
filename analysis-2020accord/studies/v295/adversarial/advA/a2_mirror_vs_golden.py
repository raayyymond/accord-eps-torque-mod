# -*- coding: utf-8 -*-
"""ADV-A a2: my mirror (advA_lane, from the Ghidra listing) vs the golden model (lkas_fb_lag + lkas_rate_pid_tick)
on >= 50,000 random ticks at the V295 cells read from the image (a1_cells.json), incl. r26-clamp binds, P binds,
bails (|x| > 12000 and invalid polarity), restarts, random taper, random ramp, random states.
Also: my LERP vs golden lkas_rate_lerp on all 241 idx for map/Kp/Kd."""
import json, os, random, sys
from dataclasses import replace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/model")
import advA_lane as A  # noqa: E402
import eps_lkas_chain_model as M  # noqa: E402

J = json.load(open(os.path.join(HERE, "a1_cells.json")))
c5 = J["v295"]


def golden_cal(c):
    return replace(M.Calibration(), fb_lag_a=c["fb_a"], fb_lag_b=c["fb_b"], fb_clamp=c["fb_clamp"], fb_op=c["fb_op"],
                   e_shift=c["e_shift"], pid_err_deadband=c["deadband"], pid_ki=c["ki"], pid_i_clamp=c["i_clamp"],
                   pid_p_clamp=c["p_clamp"], pid_d_clamp=c["d_clamp"], sum_clamp=c["sum_clamp_u"],
                   out_lag_a=c["lag_a"], out_lag_b=c["lag_b"], lkas_forward_gain=c["gain"], out_clamp=c["t_clamp_u"],
                   kp_x=tuple(c["kp_x"]), kp_y=tuple(c["kp_y"]), kd_x=tuple(c["kd_x"]), kd_y=tuple(c["kd_y"]),
                   assist_map_x=tuple(c["map_x"]), assist_map_y=tuple(c["map_y"]))


cal = golden_cal(c5)
assert cal.sum_notch is None
# ---- LERPs
bad = 0
for i in range(0, 241):
    for X, Y, gx, gy in ((c5["map_x"], c5["map_y"], cal.assist_map_x, cal.assist_map_y),
                         (c5["kp_x"], c5["kp_y"], cal.kp_x, cal.kp_y), (c5["kd_x"], c5["kd_y"], cal.kd_x, cal.kd_y)):
        if A.lerp(X, Y, i) != M.lkas_rate_lerp(gx, gy, i):
            bad += 1
print("LERP mirror vs golden over 241 idx x 3 tables: mismatches =", bad)

rng = random.Random(29530)
FIELDS = ("r26", "E", "P", "S", "y", "T")
n_ticks = n_cmp = 0
mism = []
stats = dict(unbound_live=0, bail=0, restart=0, r26_bind=0, P_bind=0, S_bind=0, T_bind=0, ramp_partial=0, taper_non254=0)
maxabs = dict(bx=0, as_=0, pp=0, mS=0, S_lb=0, la_o=0, y_ramp=0, y_gain=0)


def golden_tick(G, st, x, sp, idx, m, pol, ramp, bail):
    """golden model for one tick.  Non-bail: lkas_fb_lag (lane_live = sentinel == 1) + lkas_rate_pid_tick.
    Bail: the golden model has no bail API -> S = 0 into ITS lkas_output_lag, T by ITS formula, I/E_prev reset."""
    if bail:
        G["sent"] = 2
        st.pid_i_state = 0
        st.pid_prev_err_cell = 0x7FFFFFFF
        y = M.lkas_output_lag(0, st, cal)
        yr = M._signed16((y * st.pid_ramp) >> 15)
        T = max(-cal.out_clamp, min(cal.out_clamp, (yr * pol * M._signed16(cal.lkas_forward_gain)) >> 15))
        return dict(r26=0, E=None, P=None, S=0, y=y, T=T)
    live = G["sent"] == 1
    fb = M.lkas_fb_lag(x, st, cal, lane_live=live)
    G["sent"] = 1
    st.pid_ramp = ramp
    d = M.lkas_rate_pid_tick(sp, fb, idx, st, cal, pol=pol, taper=m)
    return dict(r26=fb, E=d["E"], P=d["P"], S=d["S"], y=d["y"], T=d["T"])


for seq in range(700):
    L = A.Lane(c5)
    st = M.EpsState()
    G = {"sent": 0}
    # random reachable initial states (identical in both)
    if rng.random() < 0.8:
        s0 = rng.randint(-969000, 969000); o0 = rng.randint(-240000, 240000)
        L.s = st.fb_lag_s = s0
        L.o = st.out_lag_s = o0
        sent = rng.choice((0, 1, 1, 1, 2))
        L.sent = G["sent"] = sent
    x = rng.randint(-12000, 12000)
    mode = rng.choice(("walk", "step", "sine", "const", "edge", "small", "slowsine", "small", "slowsine"))
    ramp = 0x8000 if rng.random() < 0.8 else rng.randint(1, 0x8000)
    st.pid_ramp = ramp
    if ramp != 0x8000:
        stats["ramp_partial"] += 1
    for k in range(200):
        if k % 10 == 0:
            idx = rng.randint(0, 240) if rng.random() < 0.9 else rng.choice((0, 240, 239, 12, 32))
            sign = rng.choice((1, -1))
            m = 254 if rng.random() < 0.7 else rng.randint(0, 255)
            pol = rng.choice((1, -1))
        if mode == "walk":
            x += rng.randint(-1500, 1500)
        elif mode == "step":
            if rng.random() < 0.05:
                x = rng.randint(-12000, 12000)
        elif mode == "sine":
            x = int(9000 * __import__("math").sin(2 * 3.14159 * (5 + seq % 25) * k / 1000.0))
        elif mode == "small":
            x += rng.randint(-60, 60)
        elif mode == "slowsine":
            x = int(3000 * __import__("math").sin(2 * 3.14159 * (0.5 + (seq % 7) * 0.4) * (k + seq * 37) / 1000.0))
        elif mode == "edge":
            x = rng.choice((12000, -12000, 11999, -11999, 12001, -12001, 0))
        x = max(-14000, min(14000, x))
        pol_eff = pol if rng.random() > 0.005 else 0            # rare invalid polarity -> bail
        bail = not (-12000 <= x <= 12000) or pol_eff == 0
        if bail:
            stats["bail"] += 1
        if (not bail) and L.sent != 1:
            stats["restart"] += 1
        if m != 254:
            stats["taper_non254"] += 1
        sp = L.sp_of(idx, sign)
        T_m = L.tick(x, sp, idx, m=m, pol=pol_eff if pol_eff else 1, ramp=ramp, valid=not bail)
        Lm = L.last
        g = golden_tick(G, st, x, sp, idx, m, pol_eff if pol_eff else 1, ramp, bail)
        n_ticks += 1
        mine = dict(r26=Lm["r26"], E=Lm.get("E"), P=Lm.get("P"), S=Lm["S"], y=Lm["y"], T=T_m)
        if bail:
            mine["E"] = mine["P"] = None
        for f in FIELDS:
            n_cmp += 1
            if mine[f] != g[f]:
                mism.append((seq, k, f, mine[f], g[f], x, idx, sign, m, pol_eff))
        # states
        for nm, a_, b_ in (("s", L.s, st.fb_lag_s), ("o", L.o, st.out_lag_s), ("I8", L.I8, st.pid_i_state),
                           ("Eprev", L.Eprev, st.pid_prev_err_cell)):
            n_cmp += 1
            if a_ != b_:
                mism.append((seq, k, "state_" + nm, a_, b_, x, idx, sign, m, pol_eff))
        if Lm.get("r26_raw") is not None and abs(Lm["r26_raw"]) > L.C:
            stats["r26_bind"] += 1
        if Lm.get("r26_raw") is not None and abs(Lm["r26_raw"]) <= L.C and Lm["r26"] != 0:
            stats["unbound_live"] += 1
        if Lm.get("P") is not None and abs(Lm["P"]) == L.pcl:
            stats["P_bind"] += 1
        if Lm.get("Ssum") is not None and abs((Lm["mS"]) >> 8) > L.scl_u:
            stats["S_bind"] += 1
        if abs(T_m) == L.tcl_u:
            stats["T_bind"] += 1
        for kk, src in (("bx", "bx"), ("as_", "as"), ("pp", "pp"), ("mS", "mS"), ("S_lb", "S_lb"), ("la_o", "la_o"),
                        ("y_ramp", "y_ramp"), ("y_gain", "y_gain")):
            if src in Lm and Lm[src] is not None:
                maxabs[kk] = max(maxabs[kk], abs(Lm[src]))

print("ticks %d, field/state comparisons %d, mismatches %d" % (n_ticks, n_cmp, len(mism)))
print("coverage:", stats)
print("max |32-bit product| seen (low word):", maxabs)
for r in mism[:20]:
    print("  MISMATCH", r)
