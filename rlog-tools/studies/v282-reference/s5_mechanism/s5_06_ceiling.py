"""s5_06: what a 100 Hz fork-side feedback loop CAN do to the V293 wheel mode, through the round-trip delay.

Exact discrete-time analysis (no Pade): plant J th'' + b th' + k th = u, ZOH at dt = 0.01 s, the command delayed n frames
(n = round-trip / 10 ms), measured angle and rate used directly.  Controller  u_k = Kp (r - th_k) + Kd (r' - om_k)  (an angle PD /
rate loop; Kp = 0 is the fork's pure rate loop AccordRateLoopGain).  Closed-loop eigenvalues -> s = ln(z)/dt -> natural frequency
and damping ratio of every pole below 12 Hz.
For each speed (k = level-scaled hold slope at 0 deg, the level the s5_02 fit found), gains are gridded and scored ROBUSTLY:
the minimum damping ratio over the plant set J in {3.3e-5, 8e-5, 1.6e-4} x n in {4, 6, 9} frames x b in {3e-4, 7e-4, 1.5e-3}.
Reported: the best robust minimum zeta, the gains, the nominal (J 8e-5, n 6) wheel-mode zeta/frequency, the static stiffness
gain (1 + Kp/k), and the closed-loop -3 dB bandwidth of r -> theta.  Friction is NOT in this model: it is linear, sliding.
Reference: open loop (Kp = Kd = 0) and the V282 identified servo (s5_01): rate pole 11-16 Hz, no measurable delay.
"""
import json, math, sys
import numpy as np
from scipy.linalg import expm
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism')
import s5ctl as C  # noqa: E402

DT = 0.01
LEVEL_BP = [5.0, 11.5, 18.5, 26.0]; LEVEL_V = [1.0, 1.28, 1.44, 1.25]


def closed_loop(J, b, k, n, Kp, Kd):
    Ac = np.array([[0, 1], [-k / J, -b / J]]); Bc = np.array([[0], [1 / J]])
    M = expm(np.block([[Ac, Bc], [np.zeros((1, 3))]]) * DT)
    Ad, Bd = M[:2, :2], M[:2, 2:]
    N = 2 + n
    A = np.zeros((N, N))
    A[:2, :2] = Ad
    if n == 0:
        A[:2, :2] = Ad - Bd @ np.array([[Kp, Kd]])
    else:
        A[:2, 2 + n - 1:2 + n] = Bd                       # oldest queued command drives the plant
        for i in range(n - 1, 0, -1):
            A[2 + i, 2 + i - 1] = 1.0                      # shift queue
        A[2, 0] = -Kp; A[2, 1] = -Kd                       # newest command = -(Kp th + Kd om)
    B = np.zeros((N, 1)); B[2 if n else 0, 0] = 1.0 if n else 0.0
    if n == 0:
        B[:2] = Bd
    return A, B


def poles(A):
    z = np.linalg.eigvals(A)
    out = []
    for zz in z:
        if abs(zz) < 1e-9:
            continue
        s = np.log(zz) / DT
        wn = abs(s); zeta = -s.real / max(wn, 1e-9)
        if wn / (2 * math.pi) < 12:
            out.append((wn / (2 * math.pi), zeta))
    return out


def bandwidth(J, b, k, n, Kp, Kd):
    A, B = closed_loop(J, b, k, n, Kp, Kd)
    # reference enters as u += Kp r (static reference, rate reference = 0): input vector scaled by Kp; output theta
    Cm = np.zeros((1, A.shape[0])); Cm[0, 0] = 1
    f = np.logspace(-1.5, 1.2, 400); H = []
    for fh in f:
        z = np.exp(1j * 2 * math.pi * fh * DT)
        H.append((Cm @ np.linalg.solve(z * np.eye(A.shape[0]) - A, B))[0, 0])
    H = np.abs(np.array(H)); H = H / H[0]
    i = np.where(H < 1 / math.sqrt(2))[0]
    return float(f[i[0]]) if len(i) else float(f[-1]), float(H.max())


res = {}
PLANTS = [(J, bb, n) for J in (3.3e-5, 8e-5, 1.6e-4) for n in (4, 6, 9) for bb in (3e-4, 7e-4, 1.5e-3)]
for v in (5.0, 11.5, 18.5, 26.0):
    k = float(np.interp(v, C.HOLD_V_BP, C.HOLD_K_V)) * float(np.interp(v, LEVEL_BP, LEVEL_V))
    row = dict(k=k)
    ol = poles(closed_loop(8e-5, 7e-4, k, 6, 0.0, 0.0)[0])
    row['open_loop_nominal'] = sorted([(round(a, 2), round(z, 3)) for a, z in ol if z < 0.99])[:2]
    best = None
    for Kp in [0, 0.002, 0.005, 0.01, 0.02, 0.04]:
        for Kd in [0, 1e-4, 2e-4, 4e-4, 6e-4, 8e-4, 1e-3, 1.3e-3, 1.6e-3, 2e-3, 3e-3]:
            zmin = min(min((z for _, z in poles(closed_loop(J, bb, k, n, Kp, Kd)[0])), default=1.0) for J, bb, n in PLANTS)
            nom = poles(closed_loop(8e-5, 7e-4, k, 6, Kp, Kd)[0])
            znom = min((z for _, z in nom), default=1.0)
            cand = dict(Kp=Kp, Kd=Kd, zeta_robust_min=round(zmin, 3), zeta_nominal_min=round(znom, 3),
                        nominal_poles=sorted([(round(a, 2), round(z, 3)) for a, z in nom])[:3],
                        static_stiffness_x=round(1 + Kp / k, 2))
            row.setdefault('grid', []).append(cand)
            if zmin >= 0.15 and (best is None or (Kp / k, znom) > (best['Kp'] / k, best['zeta_nominal_min'])):
                best = cand
    if best:
        bw, pk = bandwidth(8e-5, 7e-4, k, 6, best['Kp'], best['Kd']) if best['Kp'] > 0 else (None, None)
        best['bw_hz_nominal'] = bw; best['T_peak'] = pk
    row['best_stiff_with_robust_zeta_ge_0.15'] = best
    # the best damping of the wheel mode available at all (robust), any Kp
    bz = max(row['grid'], key=lambda c: c['zeta_robust_min'])
    row['best_robust_damping'] = bz
    # the fork's flown rate loop: Kd = 1e-3 * min(1, 12/v), Kp = 0
    Kd_f = 1e-3 * min(1.0, 12.0 / v)
    row['fork_rate_loop'] = dict(Kd=Kd_f, nominal=sorted([(round(a, 2), round(z, 3)) for a, z in poles(closed_loop(8e-5, 7e-4, k, 6, 0, Kd_f)[0])])[:3],
                                 robust_min_zeta=round(min(min((z for _, z in poles(closed_loop(J, bb, k, n, 0, Kd_f)[0])), default=1.0) for J, bb, n in PLANTS), 3))
    res[v] = {kk: vv for kk, vv in row.items() if kk != 'grid'}
    res[v]['grid_zeta_robust_Kp0'] = [(c['Kd'], c['zeta_robust_min'], c['zeta_nominal_min']) for c in row['grid'] if c['Kp'] == 0]
    print(v, json.dumps(res[v]))
json.dump(res, open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism/s5_06_ceiling.json', 'w'), indent=1)
