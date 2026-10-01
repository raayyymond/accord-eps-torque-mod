"""EXP F: CO-STEERING RELEASE -- in a held curve the driver adds a torque IN THE TURN DIRECTION (helping the lane, the
common hands-on case) for 2 s, then lets go.  The cave's bleed is sign-blind (|gp-0x4f68| > 1024 only), so a helping
hand drains the integrator that carries the curve's spring load; on release the wheel droops toward centre until I
recharges.  Hand = a pure torque d (T counts) = share * spring load; torque word tq scripted 900 (bleed off) or
1500 (bleed on); fork holds theta_sp."""
import sys, json
import numpy as np
import fric_lib as F
OUT = F.HERE.parents[3] / "_scratch" / "angle_loop" / "refute-friction"
fam = F.VP.family()
CASES = {5.0: 25.0, 8.0: 15.0, 12.5: 6.0, 19.0: 2.5, 26.0: 1.5}
TH, T1, T2 = 3.0, 5.0, 7.0
DUR = 11.0
cols = []
for v, A in CASES.items():
    p = fam["nominal"].at(v)
    load = p.k * p.sat * np.tanh(A / p.sat)
    for share in (0.5, 1.0):
        for tqa in (900, 1500):
            dval = share * load
            cols.append(dict(member="nominal", v=v, A=A, share=share, tqa=tqa,
                             ref=lambda t, A=A: float(np.interp(t, [0, 0.5, TH, 100], [0, 0, A, A])),
                             d=lambda t, dv=dval: dv * float(np.clip((t - T1) / 0.2, 0, 1)) if t < T2 else dv * float(np.clip(1 - (t - T2) / 0.05, 0, 1)),
                             tq=lambda t, a=tqa: a if T1 <= t < T2 else 0))
rec = F.run(cols, DUR, rec_I=True)
tt = np.arange(rec["th"].shape[0]) * 1e-3
print("  v    A   share  |tq| | I at release (T) | droop after release deg | overshoot during push | slips after")
res = []
for j, c in enumerate(cols):
    th = rec["th"][:, j].astype(float); sp = rec["sp"][:, j].astype(float); I = rec["I"][:, j].astype(float)
    w = tt >= T2
    e = (sp - th)[w]
    droop = e.max()
    ovs = (th - sp)[(tt >= T1) & (tt < T2)].max()
    Ir = I[int(T2 * 1000) - 2] * 5346 / 32768.0
    sl = F.slips(rec, T2, DUR)[j]
    res.append(dict(v=c["v"], share=c["share"], tq=c["tqa"], I_T=float(Ir), droop=float(droop), push_ovs=float(ovs), slips=int(sl)))
    print("%5.1f %5.1f  %3.1f  %5d | %6.0f | %6.2f | %6.2f | %d" % (c["v"], c["A"], c["share"], c["tqa"], Ir, droop, ovs, sl))
(OUT / "expF.json").write_text(json.dumps(res))
