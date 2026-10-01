import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import b_lib as B
V295_RE = {5:+2.630,7:+1.511,10:+0.422,13:-0.150,15:-0.370,17:-0.513,20:-0.633,25:-0.689}
fr=(5,7,10,13,15,17,20,25)
# worst (most negative) Re(T/w) over all speeds at the HIGHEST G in the table (highway, G~2036) dominates the D part's
# anti-damping; but Re(T/w) D-part is member/G independent except the P/I-part scales with G. Use the max highway G.
def worst_re(kd, dmode, G=2043, ema_hz=None):
    out={}
    for f in fr:
        out[f]=min(B.re_t_over_w(112,56,kd,G,f,d=2,age=a,dmode=dmode,ema_hz=ema_hz) for a in (0,10))
    return out
print("worst-over-age Re(T/w) [T/(deg/s)], G=2043 (highway).  V295 age0 for reference. rule: Re20 >= V295's(-0.633)")
print(f"{'cfg':26s}"+"".join(f"{f:>8d}Hz" for f in fr))
print(f"{'V295 age0':26s}"+"".join(f"{V295_RE[f]:+10.3f}" for f in fr))
for kd in (16,20,24,28,32,36,40,44):
  w=worst_re(kd,'held'); print(f"held Kd{kd:<3d}                "+"".join(f"{w[f]:+10.3f}" for f in fr)+("  <-20OK" if w[20]>=-0.633 else "  20FAIL"))
print()
for kd in (20,28,32,36,40,44,48,52):
  w=worst_re(kd,'fresh'); print(f"fresh Kd{kd:<3d}               "+"".join(f"{w[f]:+10.3f}" for f in fr)+("  <-20OK" if w[20]>=-0.633 else "  20FAIL"))
print()
for kd in (28,36,44):
  for ema in (40,30,20):
    w=worst_re(kd,'fresh_ema',ema_hz=ema); print(f"fresh_ema Kd{kd:<3d} {ema}Hz        "+"".join(f"{w[f]:+10.3f}" for f in fr)+("  <-20OK" if w[20]>=-0.633 else "  20FAIL"))
