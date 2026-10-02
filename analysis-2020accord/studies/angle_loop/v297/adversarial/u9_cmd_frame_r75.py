"""ADV UNIT-SCALE V297 -- command frame on an engaged route (r75 = V293 rev4, torque mode, fork commanding).
Which frame do 0xE4 raw and the 0x14A angle share, and which frame is carState? (the instrument's 'raw - 10*theta')."""
import numpy as np
z = np.load("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v280/r75_v293r4.npz")
t14, ang = z["t14"], z["ang"]; tcs, cs_ang = z["tcs"], z["cs_ang"]
te, cmd, req = z["te4"], z["cmd"], z["req"]; t18, tq = z["t18"], z["tq"]
def near(ts, t, v):
    i = np.clip(np.searchsorted(ts, t), 1, len(ts) - 1); i -= (t - ts[i - 1]) < (ts[i] - t); return v[i]
c_al = near(tcs, t14, cs_ang)
print("cache 'ang' vs carState angle: slope =", (np.sum(ang * c_al) / np.sum(c_al ** 2)).round(4), " corr", np.corrcoef(ang, c_al)[0, 1].round(5))
print("sample ang values:", ang[1000:1005], " cs:", c_al[1000:1005])
a_e = near(t14, te, ang); tq_e = near(t18, te, tq)
m = (req == 1) & (np.abs(tq_e) < 300) & (np.abs(cmd) > 100)
print("engaged hands-off frames:", m.sum())
print("corr(cmd, cache ang) =", np.corrcoef(cmd[m], a_e[m])[0, 1].round(3), " sign agree", np.mean(np.sign(cmd[m]) == np.sign(a_e[m])).round(3))
