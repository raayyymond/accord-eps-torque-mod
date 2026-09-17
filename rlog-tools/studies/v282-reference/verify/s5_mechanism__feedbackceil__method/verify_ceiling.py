"""Independent re-derivation of s5_06_ceiling.py's numbers, PLUS a check of whether the (J, b) grid it
uses is consistent with the actual plant identification (s5_02_plant_ident.json) done in the same study.

Re-implements closed_loop()/poles() from scratch (not imported) to catch implementation bugs independently.
"""
import json, math
import numpy as np
from scipy.linalg import expm

DT = 0.01

with open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism/s5_02_plant_ident.json') as f:
    IDENT = json.load(f)
with open('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s5_mechanism/s5_06_ceiling.json') as f:
    CEIL = json.load(f)

HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
LEVEL_BP = [5.0, 11.5, 18.5, 26.0]; LEVEL_V = [1.0, 1.28, 1.44, 1.25]


def closed_loop(J, b, k, n, Kp, Kd):
    """Independent re-implementation (state ordering/signs re-derived from the physics, not copied line-by-line)."""
    Ac = np.array([[0, 1], [-k / J, -b / J]]); Bc = np.array([[0], [1 / J]])
    M = expm(np.block([[Ac, Bc], [np.zeros((1, 3))]]) * DT)
    Ad, Bd = M[:2, :2], M[:2, 2:]
    if n == 0:
        A = Ad - Bd @ np.array([[Kp, Kd]])
        return A
    N = 2 + n
    A = np.zeros((N, N))
    A[:2, :2] = Ad
    A[:2, 2 + n - 1] = Bd[:, 0]
    for i in range(n - 1, 0, -1):
        A[2 + i, 2 + i - 1] = 1.0
    A[2, 0] = -Kp; A[2, 1] = -Kd
    return A


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


def k_of(v):
    return float(np.interp(v, HOLD_V_BP, HOLD_K_V)) * float(np.interp(v, LEVEL_BP, LEVEL_V))


print('=== STEP 1: reproduce s5_06 nominal (J=8e-5, b=7e-4) open-loop poles, cross-check against JSON ===')
for v in (5.0, 11.5, 18.5, 26.0):
    k = k_of(v)
    ol = poles(closed_loop(8e-5, 7e-4, k, 6, 0.0, 0.0))
    ol2 = sorted([(round(a, 2), round(z, 3)) for a, z in ol if z < 0.99])[:2]
    print(f'v={v}: k={k:.6f}  mine={ol2}  json={CEIL[str(v)]["open_loop_nominal"]}')

print()
print('=== STEP 2: reproduce the flown rate-loop (Kd = 1e-3*min(1,12/v)) nominal poles ===')
for v in (5.0, 11.5, 18.5, 26.0):
    k = k_of(v)
    Kd_f = 1e-3 * min(1.0, 12.0 / v)
    p = poles(closed_loop(8e-5, 7e-4, k, 6, 0.0, Kd_f))
    p2 = sorted([(round(a, 2), round(z, 3)) for a, z in p])[:3]
    print(f'v={v}: Kd={Kd_f:.6f}  mine={p2}  json={CEIL[str(v)]["fork_rate_loop"]["nominal"]}')

print()
print('=== STEP 3: the specific n=9 (90 ms) claim "3.31 Hz zeta 0.10 and 3.24 Hz zeta 0.17" ===')
for v in (11.5, 18.5):
    k = k_of(v)
    Kd_f = 1e-3 * min(1.0, 12.0 / v)
    p = poles(closed_loop(8e-5, 7e-4, k, 9, 0.0, Kd_f))
    p2 = sorted([(round(a, 2), round(z, 3)) for a, z in p])[:3]
    print(f'v={v} n=9: Kd={Kd_f:.6f}  poles={p2}')

print()
print('=== STEP 4: THE KEY CHECK -- does s5_06 J,b grid cover the s5_02 MEASURED plant identification? ===')
bins = {5.0: '3-8', 11.5: '8-15', 18.5: '15-22', 26.0: '22-40'}
grid_J = [3.3e-5, 8e-5, 1.6e-4]; grid_b = [3e-4, 7e-4, 1.5e-3]
for v, binname in bins.items():
    fit = IDENT[binname]
    print(f'v={v} (bin {binname}): MEASURED J={fit["J"]:.3e} (CI {fit["ci"]["J"][0]:.2e}-{fit["ci"]["J"][1]:.2e}) '
          f'b={fit["b"]:.3e} (CI {fit["ci"]["b"][0]:.2e}-{fit["ci"]["b"][1]:.2e})  '
          f's(stiffness scale)={fit["s"]:.3f}  measured mode_hz={fit["mode_hz"]:.3f}  measured zeta={fit["zeta"]:.4f}')
    print(f'    s5_06 grid J in {grid_J} (nominal 8e-5={"OUTSIDE" if not (fit["ci"]["J"][0]<=8e-5<=fit["ci"]["J"][1]) else "inside"} the 95% CI)  '
          f'grid b in {grid_b} (nominal 7e-4 {"OUTSIDE" if not (fit["ci"]["b"][0]<=7e-4<=fit["ci"]["b"][1]) else "inside"} the 95% CI)')

print()
print('=== STEP 5: recompute open-loop and flown-rate-loop poles using the ACTUAL MEASURED (J,b,k=s*HOLD_K_V) per bin ===')
for v, binname in bins.items():
    fit = IDENT[binname]
    J_m, b_m, s_m = fit['J'], fit['b'], fit['s']
    k_m = s_m * float(np.interp(v, HOLD_V_BP, HOLD_K_V))
    ol = poles(closed_loop(J_m, b_m, k_m, 6, 0.0, 0.0))
    ol2 = sorted([(round(a, 2), round(z, 3)) for a, z in ol if z < 0.995])[:2]
    Kd_f = 1e-3 * min(1.0, 12.0 / v)
    rl = poles(closed_loop(J_m, b_m, k_m, 6, 0.0, Kd_f))
    rl2 = sorted([(round(a, 2), round(z, 3)) for a, z in rl])[:3]
    print(f'v={v}: MEASURED-plant open-loop poles={ol2}   (s5_06 claimed {CEIL[str(v)]["open_loop_nominal"]})')
    print(f'         MEASURED-plant + flown rate loop poles={rl2}   (s5_06 claimed {CEIL[str(v)]["fork_rate_loop"]["nominal"]})')

print()
print('=== STEP 6: best_robust_damping / best_stiff numbers -- do they change with a grid re-centred on measured J? ===')
PLANTS_MEASURED = [(J, bb, n) for J in (1.4e-5, 2.8e-5, 6.3e-5) for n in (4, 6, 9) for bb in (-2e-4, 3e-4, 9e-4)]
for v, binname in bins.items():
    fit = IDENT[binname]
    k_m = fit['s'] * float(np.interp(v, HOLD_V_BP, HOLD_K_V))
    best = None
    for Kd in [0, 1e-4, 2e-4, 4e-4, 6e-4, 8e-4, 1e-3, 1.3e-3, 1.6e-3, 2e-3, 3e-3]:
        try:
            zmin = min(min((z for _, z in poles(closed_loop(J, bb, k_m, n, 0.0, Kd))), default=1.0) for J, bb, n in PLANTS_MEASURED)
        except Exception:
            zmin = float('nan')
        if best is None or zmin > best[1]:
            best = (Kd, zmin)
    print(f'v={v}: with a J,b GRID RE-CENTRED ON THE MEASURED FIT (J in 1.4e-5/2.8e-5/6.3e-5, b in -2e-4/3e-4/9e-4), '
          f'best robust-min-zeta Kd={best[0]}, zeta_robust_min={best[1]:.3f}   '
          f'(s5_06 original grid gave {CEIL[str(v)]["best_robust_damping"]})')
