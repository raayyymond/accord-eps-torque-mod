from tpscan import *
s=open(R+'other bins/39990-TVA-A340.bin','rb').read()
tp=0xBF000
def tpcell(addr): return addr-tp
cells={'71d0':0xC61D0,'71d2':0xC61D2,'71d4':0xC61D4,'71ce':0xC61CE,'71cc':0xC61CC,'71c8':0xC61C8,'71c0':0xC61C0,'71c2':0xC61C2,'7504':0xC6504,'7505':0xC6505,'7506':0xC6506,'7507':0xC6507,'7c00':0xC6C00,'7c10':0xC6C10,'72f6':0xC62F6,'72f8':0xC62F8,'73f8':0xC63F8,'73fa':0xC63FA,'73fc':0xC63FC,'73fe':0xC63FE,'7e88':0xC6E88,'748a':0xC648A}
for k,c in cells.items():
    disp=c-tp
    print(k,hex(c))
    for base,reg in (('tp',5),):
        for h in scan(s,disp,reg): print('   ',*h)
    # byte-neighbour (odd) for byte cells
