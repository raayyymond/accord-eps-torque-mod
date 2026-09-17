"""ATTRIBUTION WITHOUT A FULL RECONSTRUCTION.

My earlier reconstruction failed (corr 0.74) because pid_log.f folds in the friction hysteresis,
the rate loop and the observer. But I do not need all of it. AccordHoldLevel is a PURE
MULTIPLICATIVE FACTOR on ONE term I can compute exactly from logged signals:

    hold(angle_des, v, level=True) = 1.45 * hold(angle_des, v, level=False)   at v >= 17.5 m/s

(verified: the level is np.interp-CLAMPED at the 17.5 knot, and highway angles are 1-5 deg against
a tanh saturation of 19.4-19.6 deg, so no saturation is in play.)

So the question reduces to: WHAT FRACTION of the band-limited commanded torque is the hold term?
If turning the level off removes (1 - 1/1.45) = 31% of that term, how far does the command move?

Measured over-delivery to explain: 1.275 (0.15-0.30 Hz), 1.333 (0.30-0.60 Hz).
"""
import math, sys, importlib.util
import numpy as np
from scipy import signal

sys.path.insert(0, "/home/user/starpilot")
spec = importlib.util.spec_from_file_location(
    "tunes", "/home/user/starpilot/selfdrive/controls/lib/latcontrol_vehicle_tunes.py")
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T)

CA = 'analysis-2020accord/_scratch/cache/tau/'
def load(f):
    D = np.load(CA + f, allow_pickle=True); t = D['t_cs']
    v = np.interp(t, D['t_cst'], D['vego'])
    return dict(t=t, FS=1.0/float(np.median(np.diff(t))), act=D['cs_active'].astype(bool), v=v,
                pr=np.interp(t, D['t_cst'], D['spress'])>0.5,
                sa=np.interp(t, D['t_cst'], D['sa_deg']),
                curv=D['cs_curv'], dcurv=D['cs_des_curv'], out=D['cs_out'], lad=D['cs_la_des'])
R = {'6c': load('r6c_rev64_ident.npz'), '6d': load('r6d_rev64_ident.npz')}
FS = R['6c']['FS']

print("="*98)
print("CONTROL 1: does the level really multiply the hold term by exactly 1.45 at highway speed?")
print("="*98)
for v in (17.5, 19.0, 23.0, 26.0, 30.0):
    for ang in (2.0, 5.0):
        on = T.get_honda_accord_hold_torque(ang, v, level=True)
        off = T.get_honda_accord_hold_torque(ang, v, level=False)
        print(f"   v={v:5.1f} ang={ang:4.1f}:  level_on/level_off = {on/off:.4f}   (sat={T.get_honda_accord_hold_sat_deg(v):.1f} deg)")

print()
print("="*98)
print("CONTROL 2: angle_des calibration -- regress measured angle on measured curvature per run")
print("="*98)
def angle_des_of(S):
    m = S['act'] & ~S['pr'] & (np.abs(S['curv']) > 1e-5)
    k = float(np.dot(S['curv'][m], S['sa'][m]) / np.dot(S['curv'][m], S['curv'][m]))
    r = float(np.corrcoef(S['curv'][m], S['sa'][m])[0, 1])
    return S['dcurv'] * k, k, r
for tag, S in R.items():
    _, k, r = angle_des_of(S)
    print(f"   {tag}: {k:8.1f} deg per (1/m)   |r| = {abs(r):.4f}   {'OK' if abs(r) > 0.9 else 'TOO WEAK'}")

def runs(S, vlo, ml):
    t = S['t']; m = S['act'] & ~S['pr'] & (S['v'] >= vlo); out = []; n, i = len(m), 0
    while i < n:
        if not m[i]: i += 1; continue
        j = i
        while j+1 < n and m[j+1] and (t[j+1]-t[j]) < 4.0/FS: j += 1
        if (j+1-i)/FS >= ml: out.append((i, j+1))
        i = j+1
    return out

print()
print("="*98)
print("THE TEST: in-phase share of the band-limited command carried by the hold term,")
print("and how far the command moves if AccordHoldLevel is turned off.")
print("="*98)
for name, f1, f2, meas in [('0.15-0.30 Hz', 0.15, 0.30, 1.275), ('0.30-0.60 Hz', 0.30, 0.60, 1.333)]:
    sos = signal.butter(4, [f1, f2], btype='band', fs=FS, output='sos')
    num_h = num_d = den = 0.0; secs = 0.0
    for tag, S in R.items():
        ad, _, _ = angle_des_of(S)
        for a, b in runs(S, 15.0, 30.0):
            v = S['v'][a:b]
            hon = np.array([T.get_honda_accord_hold_torque(float(x), float(vv), level=True)
                            for x, vv in zip(ad[a:b], v)])
            hoff = np.array([T.get_honda_accord_hold_torque(float(x), float(vv), level=False)
                             for x, vv in zip(ad[a:b], v)])
            # the controller's torque frame is the opposite sign of the +left hold frame
            u = signal.sosfiltfilt(sos, S['out'][a:b])
            H = signal.sosfiltfilt(sos, -hon)
            Dl = signal.sosfiltfilt(sos, -(hon - hoff))     # what the level adds
            e = int(3.0*FS)
            if len(u) <= 2*e + 50: continue
            u, H, Dl = u[e:-e], H[e:-e], Dl[e:-e]
            num_h += float(np.dot(H, u)); num_d += float(np.dot(Dl, u)); den += float(np.dot(u, u))
            secs += len(u)/FS
    share_h = num_h/den; share_d = num_d/den
    pred = meas * (1.0 - share_d)
    print(f"\n  {name}   ({secs:.0f} s of highway engaged)")
    print(f"     hold term, in-phase share of the command        : {share_h:6.3f}")
    print(f"     the LEVEL's part of it (what turning it off removes): {share_d:6.3f}")
    print(f"     measured over-delivery                          : {meas:6.3f}")
    print(f"     predicted with AccordHoldLevel OFF (open-loop)  : {pred:6.3f}")
    verdict = ('LEVEL EXPLAINS IT' if abs(pred-1.0) < 0.10 else
               'LEVEL OVER-CORRECTS' if pred < 0.90 else
               'LEVEL CANNOT EXPLAIN IT -- something else dominates')
    print(f"     -> {verdict}")

print()
print("  CAVEAT (bounds the claim): this is an OPEN-LOOP sensitivity. Removing feedforward raises")
print("  the tracking error, so P and I partially refill it; the true closed-loop change is SMALLER")
print("  in magnitude than the number above. That makes 'cannot explain it' a SAFE conclusion and")
print("  'explains it' an UPPER BOUND, not a confirmation.")
