"""Mode-26 (ENGAGED, the live mode) damper surface: stock vs V74 vs V75.
dose = (FactorC(speed) * FactorE(rate)) >> 10, then ceiling-clamped.
Integer arithmetic mirrors the decompiled chain. speed/rate in raw counts.
column_deg_s = rate_counts / 4.7121 ; speed_kmh = speed_counts / 64.0
"""
def lerp(x, X, Y):
    if x <= X[0]: return Y[0]
    if x >= X[-1]: return Y[-1]
    for i in range(len(X)-1):
        if X[i] <= x <= X[i+1]:
            return Y[i] + (Y[i+1]-Y[i])*(x-X[i])//(X[i+1]-X[i])
    return Y[-1]

CX = [2240,3840,5120,8960]
EX = {"stock":[60,400,2500,4000], "V74":[12,400,2500,4000], "V75":[12,200,2500,4000]}
CY = {"stock":[0,234,429,908],    "V74":[429,234,429,908],  "V75":[566,234,429,908]}
EY = {"stock":[0,140,539,927],    "V74":[0,539,539,927],    "V75":[0,539,539,927]}
CEIL = 512

def dose(b, spd, rate):
    d = (lerp(spd, CX, CY[b]) * lerp(rate, EX[b], EY[b])) >> 10
    return min(d, CEIL), d

print("MODE 26 (ENGAGED) — damper output gp-0x6bd0 magnitude\n")
print(f"{'rate cnt':>9} {'deg/s':>7} | {'stock':>6} {'V74':>6} {'V75':>6} | {'V75/V74':>8} {'clip?':>6}")
print("-"*62)
for r in [0,6,12,25,50,99,150,200,300,400,600,1000,1555,2500,4000,6000]:
    row=[]
    for b in ("stock","V74","V75"):
        c,u = dose(b, 0, r); row.append((c,u))
    ratio = row[2][0]/row[1][0] if row[1][0] else float('inf')
    clip = "CLIP" if row[2][1] > CEIL else ""
    print(f"{r:>9} {r/4.7121:>7.1f} | {row[0][0]:>6} {row[1][0]:>6} {row[2][0]:>6} | {ratio:>8.2f} {clip:>6}")

print("\n(speed axis is flat below 2240 counts = 35 km/h, so every row above holds")
print(" for the ENTIRE 0 -> 35 km/h band, i.e. the whole stoplight-launch regime.)\n")

print("Incremental viscous gain d(out)/d(rate) in the low-rate segment [X0,X1]:")
for b in ("stock","V74","V75"):
    X,Y,C = EX[b], EY[b], CY[b][0]
    g = C*(Y[1]-Y[0])/(X[1]-X[0])/1024
    print(f"  {b:>5}: FactorC0={C:4d}  slope={Y[1]-Y[0]}/{X[1]-X[0]}  ->  {g:.4f} counts opposing per count of rate")

print("\nSpeed sweep at the symptom's own measured rate (99 counts = 21.0 deg/s):")
print(f"{'km/h':>6} | {'stock':>6} {'V74':>6} {'V75':>6}")
for kmh in [0,5,10,20,30,35,45,60,80,100,140]:
    s = int(kmh*64)
    print(f"{kmh:>6} | {dose('stock',s,99)[0]:>6} {dose('V74',s,99)[0]:>6} {dose('V75',s,99)[0]:>6}")
