import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import b_lib as B
import c1r2_members as M
# envelope = min gmax over ALL gated members (tier A thr45, tier B thr30) at each speed
NAMES = [(n,45.0) for n in M.TIER_A] + [(n,30.0) for n in M.TIER_B]
def env(v, kd, dmode):
    g=1e9; who=None
    for n,thr in NAMES:
        gg=B.gmax(n,v,thr,112,56,kd,dmode=dmode)
        if gg<g: g,who=gg,n
    return g,who
print("envelope G (min over full factorial) & Kp_eff=112*G/256, at the dip + highway.  held Kd20 vs fresh Kd28/Kd32")
print(f"{'v':>5s} | {'held20 G/Kp (bind)':28s} | {'fresh28 G/Kp (bind)':28s} | {'fresh32 G/Kp (bind)':28s}")
for v in (1.0,8.0,10.0,11.9,12.5,15.0,17.0,19.0,22.0,26.9):
    gh,wh=env(v,20,'held'); g28,w28=env(v,28,'fresh'); g32,w32=env(v,32,'fresh')
    print(f"{v:5.1f} | {gh:5d} {112*gh/256:5.0f} {wh[:14]:14s} | {g28:5d} {112*g28/256:5.0f} {w28[:14]:14s} | {g32:5d} {112*g32/256:5.0f} {w32[:14]:14s}")
