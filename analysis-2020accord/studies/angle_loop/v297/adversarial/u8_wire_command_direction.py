"""ADV UNIT-SCALE V297 -- end-to-end sign of the 0xE4 command on the car (route 71b = V294, torque mode, fb clamp 0).
Firmware: sp69ae = clamp(-4*raw) (0x526CC..0x526F2); stock plant convention under test: +S -> +x (x = gp-0x6a56).
Wire: 0x18F rate field = -x (0x55C62..66); 0x14A angle field = -theta (0x40B04..18).
If +raw -> -sp -> -S -> -x, then corr(raw, 0x18F rate field) > 0 and raw has the sign of the 0x14A ANGLE FIELD's motion,
i.e. raw and the 0x14A field share the 'CAN reference' frame (positive = right), opposite to carState (positive = left).
0xE4 raw = BE s16 bytes 0-1 of openpilot's TX echo (bus 128). Window: |raw| > 100, |0x18F torque| < 300 (hands-off)."""
import numpy as np
z = np.load("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/_scratch/cache/75604b0a432fdc89_00000071--a7b8ba5d9d/can.npz")
def s16(d, i): v = (d[:, i].astype(np.int64) << 8) | d[:, i + 1]; return np.where(v >= 32768, v - 65536, v)
def srt(k): t = z[k + "_t"]; d = z[k + "_dat"]; o = np.argsort(t); return t[o], d[o]
te, de = srt("x0E4_b128"); raw = s16(de, 0)
t8, d8 = srt("x18F_b1"); tq, rt = s16(d8, 0), s16(d8, 2)
t4, d4 = srt("x14A_b1"); angf = s16(d4, 0)
def near(ts, t, v):
    i = np.clip(np.searchsorted(ts, t), 1, len(ts) - 1); i -= (t - ts[i - 1]) < (ts[i] - t); return v[i], np.abs(ts[i] - t)
r_al, dtr = near(te, t8, raw)
a_al, _ = near(t4, t8, angf)
m = (dtr < 0.02) & (np.abs(r_al) > 100) & (np.abs(tq) < 300)
print("n frames:", m.sum())
print("corr(raw, 0x18F rate field)  =", np.corrcoef(r_al[m], rt[m])[0, 1].round(3))
# lagged: command leads motion; use rate 0.15 s later
lag = 15
mm = m[:-lag]
print("corr(raw[t], rate field[t+0.15s]) =", np.corrcoef(r_al[:-lag][mm], rt[lag:][mm])[0, 1].round(3))
print("corr(raw, 0x14A angle field) =", np.corrcoef(r_al[m], a_al[m])[0, 1].round(3), "(command vs held angle, same CAN frame expected > 0)")
