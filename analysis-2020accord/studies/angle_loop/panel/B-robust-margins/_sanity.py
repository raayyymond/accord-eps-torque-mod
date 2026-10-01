import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import b_lib as B, c1_lib as C, stab_lin as S
tbl = C.c1_table()
print("rev2 r2 table (held D, Kp112 Ki56 Kd20) reproduced via b_lib.frf:")
for n in ('nominal','J_hi','b_q*J1.0','b_q*J_hi','b_q*J1.0+h10','b_lo*J_hi*tau6+h10'):
  for v in (1.0, 12.5, 17.0, 26.9):
    J,b,k,dt,ea = B.M.params(n, v); pl = S.rigid(J,b,k)
    c = B.ctl_at(v, tbl, 112, 56, 20, d=dt, extra_age=ea, G=C.G_at(v,tbl))
    m = B.margins(c, pl, 'held')
    print(f'  {n:20s} v{v:5.1f} G{c.G:5d} PM{m["pm"]:6.1f} GM{m["gm"]:5.1f} Ms{m["Ms"]:.2f} ncr{m["n_cross"]}')
print("Re(T/w)20 held vs fresh (Kd20, G at 27 m/s =2036):")
for dm in ('held','fresh'):
  for age in (0,10):
    print(f'  {dm:6s} age{age:2d}: Re20 = {B.re_t_over_w(112,56,20,2036,20,age=age,dmode=dm):+.3f}')
