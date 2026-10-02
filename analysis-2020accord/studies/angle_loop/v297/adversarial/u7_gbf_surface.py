"""ADV UNIT-SCALE V297 -- PRE-BUILD: the default C3B-F cave's G walk and the delivered gain surface, mirrored from the
Ghidra dry-run decode of the design hex (c3b_cave_C3B-F.hex, sha 9de9365fa952) overlaid on V295 in a decode-only program.
NOT credit for a V297 image (none exists). Integer-exact; each line cites the decoded instruction.

0xC4C04 ld.hu -0x6a5e,gp,r8      v (u16, 64 cts per km/h = 230.4 per m/s)
0xC4C08 mov 0xC4CB2,r9           table base (correctly linked: first byte after jmp [r6] @0xC4CB0)
0xC4C0E..0xC4C1A  v <= X0 (bh unsigned) -> G = G0
0xC4C1C..0xC4C28  walk: advance while v > X_{i+1} (bnh unsigned)
0xC4C2A..0xC4C3E  G = G_i + (((v - X_i) * S_i) >> 12)        (ld.h S_i signed, mul, sar 0xc)
0xC4C40/44        Ep = (E * G) >> 8
downstream (V295 code, Ghidra dry-run): P = clamp((Ep*Kp)>>8, +-[0xC61BC]) @0x29E34..0x29E5C ; S fade (254/256 hands-off)
T = S * 5346/32768 * (output-lag DC, 0.990 inherited from TRACE-2026-09-30-lkas-lane-hook... = BELIEF here)"""
import struct, hashlib
P = "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/angle_loop/c3/rev2B/c3b_cave_C3B-F.hex"
cave = bytes.fromhex(open(P).read().replace(" ", "").replace("\n", ""))
assert hashlib.sha256(cave).hexdigest()[:12] == "9de9365fa952"
base = 0xC4C00; tb = 0xC4CB2 - base
rows = [struct.unpack_from("<HHh", cave, tb + 6 * i) for i in range(7)]
print("GB-F rows from the hex:", rows)
def G_of(v):
    if not v > rows[0][0]: return rows[0][1]
    i = 0
    while v > rows[i + 1][0]: i += 1
    return rows[i][1] + (((v - rows[i][0]) * rows[i][2]) >> 12)
Gs = [G_of(v) for v in range(0, 65536)]
vmin = min(range(0, 32001), key=lambda v: Gs[v])
print(f"min G over v in [0,32000]: {Gs[vmin]} at v={vmin} ({vmin/230.4:.2f} m/s); max G {max(Gs[:32001])}")
print("any G < 512 in [0,32000]:", any(g < 512 for g in Gs[:32001]))
# linear-interp vs integer walk: worst floor error
worst = 0
for i in range(6):
    x0, g0, s0 = rows[i]; x1, g1, _ = rows[i + 1]
    if x1 == 0xFFFF: continue
    for v in range(x0, x1 + 1):
        lin = g0 + (g1 - g0) * (v - x0) / (x1 - x0); worst = max(worst, abs(Gs[v] - lin))
print(f"worst |integer walk - linear knot interpolation| = {worst:.2f} G-LSB")
Kp, SCL, PCL = 112, 15360, 15360
k_T = 5346 / 32768 * 254 / 256 * 0.990
print("\n m/s   v     G   Ep/0.1deg  P/deg  T/deg(T cts)  P-sat deg  T-rail(2461) deg")
for ms in [0, 3.1, 6.0, 8.0, 10.0, 11.75, 12.5, 15, 17.5, 22.2, 26.9, 35]:
    v = int(round(ms * 230.4)); G = Gs[v]
    e = 100                                   # 10.0 deg error, counts
    E = 16 * e; Ep = (E * G) >> 8; Pc = min((Ep * Kp) >> 8, PCL)
    Pdeg = Pc / 10.0; Tdeg = Pdeg * k_T
    print(f"{ms:5.2f} {v:5d} {G:5d} {16*G/256:9.2f} {Pdeg:7.1f} {Tdeg:10.2f} {PCL/(16*G/256*Kp/256)/10:10.1f} {2461/Tdeg:10.1f}")
# overflow census (operand bounds from bytes)
Emax = 4 * 16384 + 65535
print("\nOVERFLOW: |E| <=", Emax, " |E*Gmax| =", Emax * max(Gs[:32001]), "< 2^31:", Emax * max(Gs[:32001]) < 2**31)
Epmax = (Emax * max(Gs[:32001])) >> 8
print("  |Ep| <=", Epmax, " Ep*Kp =", Epmax * Kp, " (Ep>>5)*Ki40 =", (Epmax >> 5) * 40, " D: 12000*24 =", 12000 * 24)
print("  slope term worst |dx*S| =", max(abs((rows[i+1][0]-rows[i][0]) * rows[i][2]) for i in range(5)))
