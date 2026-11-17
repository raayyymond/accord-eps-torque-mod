import sys
R='C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/'
s=open(R+'other bins/39990-TVA-A340.bin','rb').read()
r3=open(R+'_v300_a340_REV3_plain_image.bin','rb').read()
r4=open(R+'_v300_a340_REV4_plain_image.bin','rb').read()
print(len(s),len(r3),len(r4))
def runs(a,b,lo=0x13000,hi=0x100000):
    out=[];i=lo
    while i<hi:
        if a[i]!=b[i]:
            j=i
            while j<hi and (a[j]!=b[j] or (j+1<hi and a[j+1]!=b[j+1] and j-i<64)) : j+=1
            out.append((i,j));i=j
        else:i+=1
    return out
print("REV4 vs REV3")
for lo,hi in runs(r3,r4): print(hex(lo),hex(hi),r3[lo:hi].hex(),'->',r4[lo:hi].hex())
print("REV4 vs stock runs",len(runs(s,r4)))
for lo,hi in runs(s,r4): print(hex(lo),hex(hi-lo))
