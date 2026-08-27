"""Verify (a) the 0xC63A0 damper-path weight claim and (b) the FactorE plateau, from raw bytes."""
import os, struct
R=r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord"
P={"stock":os.path.join(R,"stock_fw_dump","code.bin"),
   "V73":os.path.join(R,"_v73_plain_image.bin"),
   "V74":os.path.join(R,"_v74_engagedcols_x0_12_addonly_plain_image.bin"),
   "V75":os.path.join(R,"_v75_CY0.566-EX1.200_magprobe_plain_image.bin"),
   "V76":os.path.join(R,"_v76_gate_fb_arm5244_gateprobe_plain_image.bin")}
B={k:open(v,'rb').read() for k,v in P.items()}
u16=lambda b,a: struct.unpack_from('<H',b,a)[0]
s16=lambda b,a: struct.unpack_from('<h',b,a)[0]

print("=== (a) 0xC63A0 region, raw bytes + LE u16 ===")
for a in range(0xC6398, 0xC63AC, 2):
    vals={k:u16(B[k],a) for k in B}
    diff = "  <<< DIFFERS" if len(set(vals.values()))>1 else ""
    raw  = " ".join(f"{k}={B[k][a]:02x}{B[k][a+1]:02x}" for k in ("stock","V75"))
    print(f"  {a:#07x}  " + "  ".join(f"{k}={vals[k]:5d}" for k in B) + f"   [{raw}]{diff}")

print("\n=== (b) FactorE mode 26 @0xD780C : is there a FLAT PLATEAU? ===")
for k in ("stock","V73","V74","V75"):
    b=B[k]; a=0xD780C; n=u16(b,a)
    X=[s16(b,a+2+2*i) for i in range(n)]; Y=[s16(b,a+2+2*n+2*i) for i in range(n)]
    flat=[(X[i],X[i+1]) for i in range(n-1) if Y[i]==Y[i+1] and Y[i]!=0]
    print(f"  {k:5s} X={X} Y={Y}")
    print(f"        flat non-zero segment(s): {flat if flat else 'NONE — genuine ramp'}")
    if flat:
        lo,hi=flat[0]
        print(f"        => CONSTANT-MAGNITUDE (relay) band: rate {lo}..{hi} counts "
              f"= {lo/4.7121:.0f}..{hi/4.7121:.0f} deg/s")

print("\n=== (c) full byte diff stock->V74 and V74->V75 in [0xC6300,0xC6500) ===")
for lo,hi in [("stock","V74"),("V74","V75")]:
    d=[a for a in range(0xC6300,0xC6500) if B[lo][a]!=B[hi][a]]
    print(f"  {lo}->{hi}: {len(d)} differing bytes" + (f" at {[hex(x) for x in d]}" if d else " (none)"))
